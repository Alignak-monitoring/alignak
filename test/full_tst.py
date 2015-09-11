#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2015: Alignak team, see AUTHORS.txt file for contributors
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

import subprocess
import json
from time import sleep
import urllib

import base64
import zlib
import cPickle
from alignak_test import unittest

from alignak.http.generic_interface import GenericInterface
from alignak.http.receiver_interface import ReceiverInterface
from alignak.http.arbiter_interface import ArbiterInterface
from alignak.http.scheduler_interface import SchedulerInterface
from alignak.http.broker_interface import BrokerInterface
from alignak.check import Check

class fullTest(unittest.TestCase):
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

    def tearDown(self):
        for name, proc in self.procs.items():
            if proc:
                self._get_subproc_data(name)  # so to terminate / wait it..

    def test_daemons_outputs(self):

        self.procs = {}
        satellite_map = {'arbiter': '7770',
                         'scheduler': '7768',
                         'broker': '7772',
                         'poller': '7771',
                         'reactionner': '7769',
                         'receiver': '7773'
                         }

        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            args = ["../alignak/bin/alignak_%s.py" %daemon, "-c", "etc/full_test/%sd.ini" % daemon]
            self.procs[daemon] = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        args = ["../alignak/bin/alignak_arbiter.py", "-c", "etc/full_test/alignak.cfg"]
        self.procs['arbiter'] = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        sleep(3)

        print("Testing start")
        for name, proc in self.procs.items():
            ret = proc.poll()
            if ret is not None:
                print(proc.stdout.read())
                print(proc.stderr.read())
            self.assertIsNone(ret, "Daemon %s not started!" % name)

        print("Testing sat list")
        data = urllib.urlopen("http://127.0.0.1:%s/get_satellite_list" % satellite_map['arbiter']).read()
        self.assertEqual(data, '{"reactionner": ["reactionner-master"], '
                               '"broker": ["broker-master"], '
                               '"arbiter": ["arbiter-master"], '
                               '"scheduler": ["scheduler-master"], '
                               '"receiver": ["receiver-1"], '
                               '"poller": ["poller-fail", "poller-master"]}')

        print("Testing have_conf")
        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            data = urllib.urlopen("http://127.0.0.1:%s/have_conf" % satellite_map[daemon]).read()
            self.assertEqual(data, "true", "Daemon %s has no conf!" % daemon)

        print("Testing ping")
        for name, port in satellite_map.items():
            data = urllib.urlopen("http://127.0.0.1:%s/ping" % port).read()
            self.assertEqual(data, '"pong"', "Daemon %s  did not ping back!" % name)

        print("Testing API")
        for name, port in satellite_map.items():
            data = urllib.urlopen("http://127.0.0.1:%s/api" % port).read()
            name_to_interface = {'arbiter': ArbiterInterface,
                                 'scheduler': SchedulerInterface,
                                 'broker': BrokerInterface,
                                 'poller': GenericInterface,
                                 'reactionner': GenericInterface,
                                 'receiver': ReceiverInterface}
            expected_data = set(name_to_interface[name](None).api())
            self.assertEqual(set(json.loads(data)), expected_data, "Daemon %s has a bad API!" % name)

        print("Test get check on scheduler")
        # We need to sleep 10s to be sure the first check can be launched now (check_interval = 5)
        sleep(4)
        raw_data = urllib.urlopen("http://127.0.0.1:%s/get_checks?do_checks=True&poller_tags=['TestPollerTag']" % satellite_map['scheduler']).read()
        data = cPickle.loads(zlib.decompress(base64.b64decode(raw_data)))
        self.assertIsInstance(data, list, "Data is not a list!")
        self.assertNotEqual(len(data), 0, "List is empty!")
        for elem in data:
            self.assertIsInstance(elem, Check, "One elem of the list is not a Check!")

        print("Done testing")
        #os.kill(self.arb_proc.pid, signal.SIGHUP)  # This should log with debug level the Relaod Conf
        #os.kill(self.arb_proc.pid, signal.SIGINT)  # This should kill the proc
        #data = self._get_subproc_data()
        #self.assertRegexpMatches(data['out'], "Reloading configuration")


if __name__ == '__main__':
    unittest.main()

