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
import time
import signal

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


class DaemonsStartTest(AlignakTest):
    def _get_subproc_data(self, name):
        try:
            print("Polling %s" % name)
            if self.procs[name].poll():
                print("Killing %s..." % name)
                os.kill(self.procs[name].pid, signal.SIGKILL)
            print("%s terminated" % name)

        except Exception as err:
            print("Problem on terminate and wait subproc %s: %s" % (name, err))

    def setUp(self):
        # Set environment variable to ask code Coverage collection
        os.environ['COVERAGE_PROCESS_START'] = '.coveragerc'

        self.procs = {}

    def tearDown(self):
        print("Test terminated!")

    def test_arbiter_bad_configuration(self):
        """ Running the Alignak Arbiter with bad parameters

        :return:
        """
        # copy etc config files in test/cfg/run_test_launch_daemons and change folder
        # in the files for pid and log files
        if os.path.exists('./cfg/run_test_launch_daemons'):
            shutil.rmtree('./cfg/run_test_launch_daemons')

        shutil.copytree('../etc', './cfg/run_test_launch_daemons')
        files = ['cfg/run_test_launch_daemons/daemons/arbiterd.ini',
                 'cfg/run_test_launch_daemons/arbiter/daemons/arbiter-master.cfg']
        replacements = {
            '/usr/local/var/run/alignak': '/tmp',
            '/usr/local/var/log/alignak': '/tmp',
            '%(workdir)s': '/tmp',
            '%(logdir)s': '/tmp',
            '%(etcdir)s': '/tmp'
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

        print("Cleaning pid and log files...")
        for daemon in ['arbiter']:
            if os.path.exists('/tmp/%sd.pid' % daemon):
                os.remove('/tmp/%sd.pid' % daemon)
                print("- removed /tmp/%sd.pid" % daemon)
            if os.path.exists('/tmp/%sd.log' % daemon):
                os.remove('/tmp/%sd.log' % daemon)
                print("- removed /tmp/%sd.log" % daemon)

        print("Launching arbiter with bad configuration file...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-c", "cfg/run_test_launch_daemons/daemons/fake.ini",
                "-a", "cfg/run_test_launch_daemons/alignak.cfg"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        # Wait for arbiter parsing the configuration
        sleep(5)

        ret = arbiter.poll()
        self.assertIsNotNone(ret, "Arbiter is still running!")
        for line in iter(arbiter.stdout.readline, b''):
            print(">>> " + line.rstrip())
        for line in iter(arbiter.stderr.readline, b''):
            print(">>> " + line.rstrip())

    def test_arbiter_verify(self):
        """ Running the Alignak Arbiter in verify mode only

        :return:
        """
        # copy etc config files in test/cfg/run_test_launch_daemons and change folder
        # in the files for pid and log files
        if os.path.exists('./cfg/run_test_launch_daemons'):
            shutil.rmtree('./cfg/run_test_launch_daemons')

        shutil.copytree('../etc', './cfg/run_test_launch_daemons')
        files = ['cfg/run_test_launch_daemons/daemons/arbiterd.ini',
                 'cfg/run_test_launch_daemons/arbiter/daemons/arbiter-master.cfg']
        replacements = {
            '/usr/local/var/run/alignak': '/tmp',
            '/usr/local/var/log/alignak': '/tmp',
            '%(workdir)s': '/tmp',
            '%(logdir)s': '/tmp',
            '%(etcdir)s': '/tmp'
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

        print("Cleaning pid and log files...")
        for daemon in ['arbiter']:
            if os.path.exists('/tmp/%sd.pid' % daemon):
                os.remove('/tmp/%sd.pid' % daemon)
                print("- removed /tmp/%sd.pid" % daemon)
            if os.path.exists('/tmp/%sd.log' % daemon):
                os.remove('/tmp/%sd.log' % daemon)
                print("- removed /tmp/%sd.log" % daemon)

        print("Launching arbiter with bad configuration file...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-V",
                "-a", "cfg/run_test_launch_daemons/alignak.cfg"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        sleep(5)

        ret = arbiter.poll()
        self.assertIsNotNone(ret, "Arbiter still running!")
        print("*** Arbiter exited on start!")
        for line in iter(arbiter.stdout.readline, b''):
            print(">>> " + line.rstrip())
        for line in iter(arbiter.stderr.readline, b''):
            print(">>> " + line.rstrip())

    def test_daemons_outputs_no_ssl(self):
        """ Running all the Alignak daemons - no SSL

        :return:
        """
        self._run_daemons_and_test_api(ssl=False)

    def test_daemons_outputs_ssl(self):
        """ Running all the Alignak daemons - with SSL

        :return: None
        """
        # disable ssl warning
        requests.packages.urllib3.disable_warnings()
        self._run_daemons_and_test_api(ssl=True)

    def _run_daemons_and_test_api(self, ssl=False):
        """ Running all the Alignak daemons to check their correct launch and API

        :return:
        """
        req = requests.Session()

        # copy etc config files in test/cfg/run_test_launch_daemons and change folder
        # in the files for pid and log files
        if os.path.exists('./cfg/run_test_launch_daemons'):
            shutil.rmtree('./cfg/run_test_launch_daemons')

        shutil.copytree('../etc', './cfg/run_test_launch_daemons')
        files = ['cfg/run_test_launch_daemons/daemons/arbiterd.ini',
                 'cfg/run_test_launch_daemons/daemons/brokerd.ini',
                 'cfg/run_test_launch_daemons/daemons/pollerd.ini',
                 'cfg/run_test_launch_daemons/daemons/reactionnerd.ini',
                 'cfg/run_test_launch_daemons/daemons/receiverd.ini',
                 'cfg/run_test_launch_daemons/daemons/schedulerd.ini',
                 'cfg/run_test_launch_daemons/alignak.cfg',
                 'cfg/run_test_launch_daemons/arbiter/daemons/arbiter-master.cfg',
                 'cfg/run_test_launch_daemons/arbiter/daemons/broker-master.cfg',
                 'cfg/run_test_launch_daemons/arbiter/daemons/poller-master.cfg',
                 'cfg/run_test_launch_daemons/arbiter/daemons/reactionner-master.cfg',
                 'cfg/run_test_launch_daemons/arbiter/daemons/receiver-master.cfg',
                 'cfg/run_test_launch_daemons/arbiter/daemons/scheduler-master.cfg']
        replacements = {
            '/usr/local/var/run/alignak': '/tmp',
            '/usr/local/var/log/alignak': '/tmp',
            '%(workdir)s': '/tmp',
            '%(logdir)s': '/tmp',
            '%(etcdir)s': '/tmp'
        }
        if ssl:
            shutil.copy('./cfg/ssl/server.csr', '/tmp/')
            shutil.copy('./cfg/ssl/server.key', '/tmp/')
            shutil.copy('./cfg/ssl/server.pem', '/tmp/')
            # Set daemons configuration to use SSL
            print replacements
            replacements.update({
                'use_ssl=0': 'use_ssl=1',
                '#server_cert=': 'server_cert=',
                '#server_key=': 'server_key=',
                '#server_dh=': 'server_dh=',
                '#hard_ssl_name_check=0': 'hard_ssl_name_check=0',
                'certs/': '',
                'use_ssl	                0': 'use_ssl	                1'
            })
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

        print("Cleaning pid and log files...")
        for daemon in ['arbiter', 'scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            if os.path.exists('/tmp/%sd.pid' % daemon):
                os.remove('/tmp/%sd.pid' % daemon)
                print("- removed /tmp/%sd.pid" % daemon)
            if os.path.exists('/tmp/%sd.log' % daemon):
                os.remove('/tmp/%sd.log' % daemon)
                print("- removed /tmp/%sd.log" % daemon)

        print("Launching the daemons...")
        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            args = ["../alignak/bin/alignak_%s.py" %daemon,
                    "-c", "./cfg/run_test_launch_daemons/daemons/%sd.ini" % daemon]
            self.procs[daemon] = \
                subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            sleep(1)
            print("- %s launched (pid=%d)" % (daemon, self.procs[daemon].pid))

        sleep(1)

        print("Testing daemons start")
        for name, proc in self.procs.items():
            ret = proc.poll()
            if ret is not None:
                print("*** %s exited on start!" % (name))
                for line in iter(proc.stdout.readline, b''):
                    print(">>> " + line.rstrip())
                for line in iter(proc.stderr.readline, b''):
                    print(">>> " + line.rstrip())
            self.assertIsNone(ret, "Daemon %s not started!" % name)
            print("%s running (pid=%d)" % (name, self.procs[daemon].pid))

        # Let the daemons start ...
        sleep(5)

        print("Testing pid files and log files...")
        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            self.assertTrue(os.path.exists('/tmp/%sd.pid' % daemon), '/tmp/%sd.pid does not exist!' % daemon)
            self.assertTrue(os.path.exists('/tmp/%sd.log' % daemon), '/tmp/%sd.log does not exist!' % daemon)

        sleep(1)

        print("Launching arbiter...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-c", "cfg/run_test_launch_daemons/daemons/arbiterd.ini",
                "-a", "cfg/run_test_launch_daemons/alignak.cfg"]
        self.procs['arbiter'] = \
            subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', self.procs['arbiter'].pid))

        sleep(5)

        name = 'arbiter'
        print("Testing Arbiter start %s" % name)
        ret = self.procs[name].poll()
        if ret is not None:
            print("*** %s exited on start!" % (name))
            for line in iter(self.procs[name].stdout.readline, b''):
                print(">>> " + line.rstrip())
            for line in iter(self.procs[name].stderr.readline, b''):
                print(">>> " + line.rstrip())
        self.assertIsNone(ret, "Daemon %s not started!" % name)
        print("%s running (pid=%d)" % (name, self.procs[name].pid))

        sleep(1)

        print("Testing pid files and log files...")
        for daemon in ['arbiter']:
            self.assertTrue(os.path.exists('/tmp/%sd.pid' % daemon), '/tmp/%sd.pid does not exist!' % daemon)
            self.assertTrue(os.path.exists('/tmp/%sd.log' % daemon), '/tmp/%sd.log does not exist!' % daemon)

        # Let the arbiter build and dispatch its configuration
        sleep(5)

        http = 'http'
        if ssl:
            http = 'https'

        print("Testing ping")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/ping" % (http, port), verify=False)
            data = raw_data.json()
            self.assertEqual(data, 'pong', "Daemon %s  did not ping back!" % name)

        print("Testing ping with satellite SSL and client not SSL")
        if ssl:
            for name, port in satellite_map.items():
                raw_data = req.get("http://localhost:%s/ping" % port)
                self.assertEqual('The client sent a plain HTTP request, but this server '
                                 'only speaks HTTPS on this port.', raw_data.text)

        print("Testing get_satellite_list")
        raw_data = req.get("%s://localhost:%s/get_satellite_list" %
                           (http, satellite_map['arbiter']), verify=False)
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
            raw_data = req.get("%s://localhost:%s/have_conf" % (http, satellite_map[daemon]), verify=False)
            data = raw_data.json()
            self.assertTrue(data, "Daemon %s has no conf!" % daemon)
            # TODO: test with magic_hash

        print("Testing do_not_run")
        for daemon in ['arbiter', 'scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            raw_data = req.get("%s://localhost:%s/do_not_run" % (http, satellite_map[daemon]), verify=False)

        print("Testing api")
        name_to_interface = {'arbiter': ArbiterInterface,
                             'scheduler': SchedulerInterface,
                             'broker': BrokerInterface,
                             'poller': GenericInterface,
                             'reactionner': GenericInterface,
                             'receiver': ReceiverInterface}
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/api" % (http, port), verify=False)
            data = raw_data.json()
            expected_data = set(name_to_interface[name](None).api())
            self.assertIsInstance(data, list, "Data is not a list!")
            self.assertEqual(set(data), expected_data, "Daemon %s has a bad API!" % name)

        print("Testing api_full")
        name_to_interface = {'arbiter': ArbiterInterface,
                             'scheduler': SchedulerInterface,
                             'broker': BrokerInterface,
                             'poller': GenericInterface,
                             'reactionner': GenericInterface,
                             'receiver': ReceiverInterface}
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/api_full" % (http, port), verify=False)
            data = raw_data.json()

        # print("Testing get_checks on scheduler")
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
            raw_data = req.get("%s://localhost:%s/get_raw_stats" % (http, port), verify=False)
            data = raw_data.json()
            if name == 'broker':
                self.assertIsInstance(data, list, "Data is not a list!")
            else:
                self.assertIsInstance(data, dict, "Data is not a dict!")

        print("Testing what_i_managed")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/what_i_managed" % (http, port), verify=False)
            data = raw_data.json()
            self.assertIsInstance(data, dict, "Data is not a dict!")
            if name != 'arbiter':
                self.assertEqual(1, len(data), "The dict must have 1 key/value!")

        print("Testing get_external_commands")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/get_external_commands" % (http, port), verify=False)
            data = raw_data.json()
            self.assertIsInstance(data, list, "Data is not a list!")

        print("Testing get_log_level")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/get_log_level" % (http, port), verify=False)
            data = raw_data.json()
            self.assertIsInstance(data, unicode, "Data is not an unicode!")
            # TODO: seems level get not same tham defined in *d.ini files

        print("Testing get_all_states")
        raw_data = req.get("%s://localhost:%s/get_all_states" % (http, satellite_map['arbiter']), verify=False)
        data = raw_data.json()
        self.assertIsInstance(data, dict, "Data is not a dict!")
        for daemon_type in data:
            daemons = data[daemon_type]
            print("Got Alignak state for: %ss / %d instances" % (daemon_type, len(daemons)))
            for daemon in daemons:
                print(" - %s: %s", daemon['%s_name' % daemon_type], daemon['alive'])
                self.assertTrue(daemon['alive'])
                self.assertFalse('realm' in daemon)
                self.assertTrue('realm_name' in daemon)

        print("Testing get_running_id")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/get_running_id" % (http, port), verify=False)
            data = raw_data.json()
            self.assertIsInstance(data, unicode, "Data is not an unicode!")

        print("Testing fill_initial_broks")
        raw_data = req.get("%s://localhost:%s/fill_initial_broks" % (http, satellite_map['scheduler']), params={'bname': 'broker-master'}, verify=False)
        data = raw_data.json()
        self.assertIsNone(data, "Data must be None!")

        print("Testing get_broks")
        for name in ['scheduler', 'poller']:
            raw_data = req.get("%s://localhost:%s/get_broks" % (http, satellite_map[name]),
                               params={'bname': 'broker-master'}, verify=False)
            data = raw_data.json()
            self.assertIsInstance(data, dict, "Data is not a dict!")

        print("Testing get_returns")
        # get_return requested by scheduler to poller daemons
        for name in ['reactionner', 'receiver', 'poller']:
            raw_data = req.get("%s://localhost:%s/get_returns" % (http, satellite_map[name]), params={'sched_id': 0}, verify=False)
            data = raw_data.json()
            self.assertIsInstance(data, list, "Data is not a list!")

        print("Testing signals")
        for name, proc in self.procs.items():
            # SIGUSR1: memory dump
            self.procs[name].send_signal(signal.SIGUSR1)
            time.sleep(0.5)
            # SIGUSR2: objects dump
            self.procs[name].send_signal(signal.SIGUSR2)
            # SIGHUP: reload configuration
            self.procs[name].send_signal(signal.SIGUSR2)

            # Other signals is considered as a request to stop...

        for name, proc in self.procs.items():
            print("Asking %s to end..." % name)
            os.kill(self.procs[name].pid, signal.SIGTERM)

        time.sleep(1)

        for name, proc in self.procs.items():
            data = self._get_subproc_data(name)
            print("%s stdout:" % (name))
            for line in iter(proc.stdout.readline, b''):
                print(">>> " + line.rstrip())
            print("%s stderr:" % (name))
            for line in iter(proc.stderr.readline, b''):
                print(">>> " + line.rstrip())

        print("Done testing")
