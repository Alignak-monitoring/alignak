#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016: Alignak team, see AUTHORS.txt file for contributors
#
# This file is part of Alignak.
#
# Alignak is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Alignak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Alignak.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import subprocess
from time import sleep
import requests
import shutil

from alignak_test import unittest
from alignak_test import AlignakTest

from alignak.http.generic_interface import GenericInterface
from alignak.http.receiver_interface import ReceiverInterface
from alignak.http.arbiter_interface import ArbiterInterface
from alignak.http.scheduler_interface import SchedulerInterface
from alignak.http.broker_interface import BrokerInterface


class fullTest(AlignakTest):
    def _get_subproc_data(self, name):
        try:
            print("Try to end %s" % name)
            self.procs[name].send_signal(2)
            self.procs[name].send_signal(15)
            self.procs[name].wait()
        except Exception as err:
            print("prob on terminate and wait subproc %s: %s" % (name, err))
        data = {}
        data['out'] = self.procs[name].stdout.read()
        data['err'] = self.procs[name].stderr.read()
        data['rc'] = self.procs[name].returncode
        return data

    def setUp(self):
        self.procs = {}

    def tearDown(self):
        for name, proc in self.procs.items():
            if proc:
                self._get_subproc_data(name)  # so to terminate / wait it..

    def test_daemons_outputs(self):
        """ Running all the Alignak daemons to check their correct launch

        :return:
        """

        os.environ['COVERAGE_PROCESS_START'] = '.coverage.rc'

        req = requests.Session()

        # copy etc config files in test/cfg/full and change folder in files for run and log of
        # alignak
        if os.path.exists('./cfg/full'):
            shutil.rmtree('./cfg/full')
        shutil.copytree('../etc', './cfg/full')
        files = ['cfg/full/daemons/arbiterd.ini',
                 'cfg/full/daemons/brokerd.ini', 'cfg/full/daemons/pollerd.ini',
                 'cfg/full/daemons/reactionnerd.ini', 'cfg/full/daemons/receiverd.ini',
                 'cfg/full/daemons/schedulerd.ini', 'cfg/full/alignak.cfg']
        replacements = {
            '/usr/local/var/run/alignak': '/tmp',
            '/usr/local/var/log/alignak': '/tmp',
            '%(workdir)s': '/tmp',
            '%(logdir)s': '/tmp'
        }
        for filename in files:
            lines = []
            with open(filename) as infile:
                for line in infile:
                    for src, target in replacements.iteritems():
                        line = line.replace(src, target)
                    lines.append(line)
            with open(filename, 'w') as outfile:
                for line in lines:
                    outfile.write(line)

        self.procs = {}
        satellite_map = {
            'arbiter': '7770', 'scheduler': '7768', 'broker': '7772',
            'poller': '7771', 'reactionner': '7769', 'receiver': '7773'
        }

        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            args = ["../alignak/bin/alignak_%s.py" %daemon,
                    "-c", "cfg/full/daemons/%sd.ini" % daemon]
            self.procs[daemon] = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        args = ["../alignak/bin/alignak_arbiter.py",
                "-c", "cfg/full/daemons/arbiterd.ini",
                "-a", "cfg/full/alignak.cfg"]
        self.procs['arbiter'] = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        sleep(8)

        print("Testing start")
        for name, proc in self.procs.items():
            ret = proc.poll()
            if ret is not None:
                print(proc.stdout.read())
                print(proc.stderr.read())
            self.assertIsNone(ret, "Daemon %s not started!" % name)

        print("Testing pid files and log files...")
        for daemon in ['arbiter', 'scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            self.assertTrue(os.path.exists('/tmp/%sd.log' % daemon))
            self.assertTrue(os.path.exists('/tmp/%sd.pid' % daemon))

        print("Testing get_satellite_list")
        raw_data = req.get("http://localhost:%s/get_satellite_list" % satellite_map['arbiter'])
        expected_data ={"reactionner": ["reactionner-master"],
                               "broker": ["broker-master"],
                               "arbiter": ["arbiter-master"],
                               "scheduler": ["scheduler-master"],
                               "receiver": ["receiver-master"],
                               "poller": ["poller-master"]}
        data = raw_data.json()
        self.assertIsInstance(data, dict, "Data is not a dict!")
        for k, v in expected_data.iteritems():
            self.assertEqual(set(data[k]), set(v))

        print("Testing have_conf")
        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            raw_data = req.get("http://localhost:%s/have_conf" % satellite_map[daemon])
            data = raw_data.json()
            self.assertEqual(data, True, "Daemon %s has no conf!" % daemon)
            # TODO: test with magic_hash

        print("Testing ping")
        for name, port in satellite_map.items():
            raw_data = req.get("http://localhost:%s/ping" % port)
            data = raw_data.json()
            self.assertEqual(data, 'pong', "Daemon %s  did not ping back!" % name)

        print("Testing api")
        name_to_interface = {'arbiter': ArbiterInterface,
                             'scheduler': SchedulerInterface,
                             'broker': BrokerInterface,
                             'poller': GenericInterface,
                             'reactionner': GenericInterface,
                             'receiver': ReceiverInterface}
        for name, port in satellite_map.items():
            raw_data = req.get("http://localhost:%s/api" % port)
            data = raw_data.json()
            expected_data = set(name_to_interface[name](None).api())
            self.assertIsInstance(data, list, "Data is not a list!")
            self.assertEqual(set(data), expected_data, "Daemon %s has a bad API!" % name)

        print("Testing get_checks on scheduler")
        # TODO: if have poller running, the poller will get the checks before us
        #
        # We need to sleep 10s to be sure the first check can be launched now (check_interval = 5)
        # sleep(4)
        # raw_data = req.get("http://localhost:%s/get_checks" % satellite_map['scheduler'], params={'do_checks': True})
        # data = unserialize(raw_data.json(), True)
        # self.assertIsInstance(data, list, "Data is not a list!")
        # self.assertNotEqual(len(data), 0, "List is empty!")
        # for elem in data:
        #     self.assertIsInstance(elem, Check, "One elem of the list is not a Check!")

        print("Testing get_raw_stats")
        for name, port in satellite_map.items():
            raw_data = req.get("http://localhost:%s/get_raw_stats" % port)
            data = raw_data.json()
            if name == 'broker':
                self.assertIsInstance(data, list, "Data is not a list!")
            else:
                self.assertIsInstance(data, dict, "Data is not a dict!")

        print("Testing what_i_managed")
        for name, port in satellite_map.items():
            raw_data = req.get("http://localhost:%s/what_i_managed" % port)
            data = raw_data.json()
            self.assertIsInstance(data, dict, "Data is not a dict!")
            if name != 'arbiter':
                self.assertEqual(1, len(data), "The dict must have 1 key/value!")

        print("Testing get_external_commands")
        for name, port in satellite_map.items():
            raw_data = req.get("http://localhost:%s/get_external_commands" % port)
            data = raw_data.json()
            self.assertIsInstance(data, list, "Data is not a list!")

        print("Testing get_log_level")
        for name, port in satellite_map.items():
            raw_data = req.get("http://localhost:%s/get_log_level" % port)
            data = raw_data.json()
            self.assertIsInstance(data, unicode, "Data is not an unicode!")
            # TODO: seems level get not same tham defined in *d.ini files

        print("Testing get_all_states")
        raw_data = req.get("http://localhost:%s/get_all_states" % satellite_map['arbiter'])
        data = raw_data.json()
        self.assertIsInstance(data, dict, "Data is not a dict!")

        print("Testing get_running_id")
        for name, port in satellite_map.items():
            raw_data = req.get("http://localhost:%s/get_running_id" % port)
            data = raw_data.json()
            self.assertIsInstance(data, unicode, "Data is not an unicode!")

        print("Testing fill_initial_broks")
        raw_data = req.get("http://localhost:%s/fill_initial_broks" % satellite_map['scheduler'], params={'bname': 'broker-master'})
        data = raw_data.json()
        self.assertIsNone(data, "Data must be None!")

        print("Testing get_broks")
        for name in ['scheduler', 'poller']:
            raw_data = req.get("http://localhost:%s/get_broks" % satellite_map[name],
                               params={'bname': 'broker-master'})
            data = raw_data.json()
            self.assertIsInstance(data, dict, "Data is not a dict!")

        print("Testing get_returns")
        # get_return requested by scheduler to poller daemons
        for name in ['reactionner', 'receiver', 'poller']:
            raw_data = req.get("http://localhost:%s/get_returns" % satellite_map[name], params={'sched_id': 0})
            data = raw_data.json()
            self.assertIsInstance(data, list, "Data is not a list!")


        print("Done testing")


if __name__ == '__main__':
    unittest.main()
