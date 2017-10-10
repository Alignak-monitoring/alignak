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
import sys
import time
import signal
import json

import subprocess
from time import sleep
import requests
import shutil
import psutil

import pytest
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
        self.procs = {}

        # copy the default shipped configuration files in /tmp/etc and change the root folder
        # used by the daemons for pid and log files in the alignak-realm2.ini file
        if os.path.exists('/tmp/etc'):
            shutil.rmtree('/tmp/etc')

        print("Preparing configuration...")
        shutil.copytree('../etc', '/tmp/etc')
        files = ['/tmp/etc/alignak-realm2.ini']
        replacements = {
            '_dist=/usr/local/': '_dist=/tmp'
        }
        self._files_update(files, replacements)

        # Clean the former existing pid and log files
        print("Cleaning pid and log files...")
        for daemon in ['arbiter-master', 'scheduler-master', 'broker-master',
                       'poller-master', 'reactionner-master', 'receiver-master']:
            if os.path.exists('/tmp/run/%s.pid' % daemon):
                os.remove('/tmp/run/%s.pid' % daemon)
            if os.path.exists('/tmp/log/%s.log' % daemon):
                os.remove('/tmp/log/%s.log' % daemon)

    def tearDown(self):
        print("Test terminated!")

    def test_arbiter_unexisting_environment(self):
        """ Running the Alignak Arbiter with a not existing environment file

        :return:
        """
        print("Launching arbiter with a not existing environment file...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-e", "/tmp/etc/unexisting.ini"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        # Waiting for arbiter to parse the configuration
        sleep(3)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %d" % ret)
        assert ret is not None, "Arbiter is still running!"
        stdout = arbiter.stdout.read()
        assert "Daemon 'arbiter-master' is started with an environment " \
               "file: /tmp/etc/unexisting.ini" in stdout
        stderr = arbiter.stderr.read()
        assert "The Alignak environment file is not existing or do not " \
               "define any monitoring configuration files. " \
               "The arbiter can not start correctly." in stderr
        # Arbiter process must exit with a return code == 1
        assert ret == 1

    def test_arbiter_no_monitoring_configuration(self):
        """ Running the Alignak Arbiter with no monitoring configuration file

        :return:
        """
        print("Launching arbiter with no monitoring configuration...")

        # Update configuration with a bad file name
        files = ['/tmp/etc/alignak-realm2.ini']
        replacements = {
            'CFG=%(etcdir)s/alignak.cfg': 'CFG='
        }
        self._files_update(files, replacements)

        args = ["../alignak/bin/alignak_arbiter.py",
                "-e", "/tmp/etc/alignak-realm2.ini"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        # Waiting for arbiter to parse the configuration
        sleep(3)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %d" % ret)
        assert ret is not None, "Arbiter is still running!"
        stdout = arbiter.stdout.read()
        assert "Daemon 'arbiter-master' is started with an environment " \
               "file: /tmp/etc/alignak-realm2.ini" in stdout
        stderr = arbiter.stderr.read()
        print(stderr)
        assert "The Alignak environment file is not existing or do not " \
               "define any monitoring configuration files. " \
               "The arbiter can not start correctly." in stderr
        # Arbiter process must exit with a return code == 1
        assert ret == 1

    def test_arbiter_unexisting_monitoring_configuration(self):
        """ Running the Alignak Arbiter with a not existing monitoring configuration file

        :return:
        """
        print("Launching arbiter with no monitoring configuration...")

        # Update configuration with a bad file name
        files = ['/tmp/etc/alignak-realm2.ini']
        replacements = {
            'CFG=%(etcdir)s/alignak.cfg': 'CFG=%(etcdir)s/unexisting.cfg'
        }
        self._files_update(files, replacements)

        args = ["../alignak/bin/alignak_arbiter.py",
                "-e", "/tmp/etc/alignak-realm2.ini"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        # Waiting for arbiter to parse the configuration
        sleep(3)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %d" % ret)
        errors = False
        stderr = False
        for line in iter(arbiter.stdout.readline, b''):
            if 'ERROR' in line:
                print("*** " + line.rstrip())
                errors = True
            assert 'CRITICAL' not in line
        for line in iter(arbiter.stderr.readline, b''):
            print("*** " + line.rstrip())
            stderr = True

        # Arbiter process must exit with a return code == 1
        assert ret == 1
        # Error message must be sent to stderr
        assert stderr
        # Errors must exist in the logs
        assert errors

    def test_arbiter_bad_configuration(self):
        """ Running the Alignak Arbiter with bad monitoring configuration (unknown sub directory)

        :return:
        """
        print("Launching arbiter with a bad monitoring configuration...")

        # Update configuration with a bad file name
        files = ['/tmp/etc/alignak.cfg']
        replacements = {
            'cfg_dir=arbiter/objects/realms': 'cfg_dir=unexisting/objects/realms'
        }
        self._files_update(files, replacements)

        args = ["../alignak/bin/alignak_arbiter.py",
                "-e", "/tmp/etc/alignak-realm2.ini"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        # Waiting for arbiter to parse the configuration
        sleep(3)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %d" % ret)
        assert ret is not None, "Arbiter is still running!"
        # Arbiter process must exit with a return code == 1
        assert ret == 1
        errors = False
        stderr = False
        for line in iter(arbiter.stdout.readline, b''):
            if 'ERROR' in line:
                print("*** " + line.rstrip())
                errors = True
            assert 'CRITICAL' not in line
        for line in iter(arbiter.stderr.readline, b''):
            print("*** " + line.rstrip())
            stderr = True

        # Error message must be sent to stderr
        assert stderr
        # Errors must exist in the logs
        assert errors

    def test_arbiter_verify(self):
        """ Running the Alignak Arbiter in verify mode only with the default shipped configuration

        :return:
        """
        print("Launching arbiter with configuration file...")
        args = ["../alignak/bin/alignak_arbiter.py", "-V", "-e", "/tmp/etc/alignak-realm2.ini"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        sleep(5)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %s" % ret)
        assert ret is not None, "Arbiter is still running!"
        errors = 0
        for line in iter(arbiter.stdout.readline, b''):
            print(">>> " + line.rstrip())
            if 'ERROR' in line:
                errors = errors + 1
            if 'CRITICAL' in line:
                errors = errors + 1
        for line in iter(arbiter.stderr.readline, b''):
            print("*** " + line.rstrip())
            # if sys.version_info > (2, 7):
            #     assert False, "stderr output!"
        # Arbiter process must exit with a return code == 0 and no errors
        assert errors == 0
        assert ret == 0

    def test_arbiter_no_daemons(self):
        """ Run the Alignak Arbiter with other daemons missing

        :return:
        """
        # All the default configuration files are in /tmp/etc

        print("Launching arbiter with bad configuration file...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-e", "/tmp/etc/alignak-realm2.ini"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        sleep(5)

        ret = arbiter.poll()
        # Arbiter must still be running ... it is still trying to dispatch the configuration!
        for line in iter(arbiter.stdout.readline, b''):
            print(">>> " + line.rstrip())
        assert ret is None, "Arbiter exited!"

        sleep(10)

        # Arbiter never stops trying to send its configuration! We must kill it...

        print("Asking arbiter to end...")
        os.kill(arbiter.pid, signal.SIGTERM)

        ret = arbiter.poll()
        print("*** Arbiter exited on kill, no return code!")
        assert ret is None, "Arbiter is still running!"
        ok = True
        for line in iter(arbiter.stdout.readline, b''):
            print(">>> " + line.rstrip())
            if 'WARNING:' in line:
                ok = False
                # Only WARNING because of missing daemons...
                if 'Cannot call the additional groups setting ' in line:
                    ok = True
                if 'Connection failed ' in line:
                    ok = True
                if 'Connection timeout ' in line:
                    ok = True
                if 'Not reachable for ' in line:
                    ok = True
                if 'Add failed attempt ' in line:
                    ok = True
                if 'Server is not available' in line:
                    ok = True
                if 'Missing satellite ' in line:
                    ok = True
                if 'Setting the satellite ' in line:
                    ok = True
                if 'Configuration sending error ' in line:
                    ok = True
                if 'There are no alive schedulers in this realm!' in line:
                    ok = True
                if 'All schedulers configurations are not dispatched, 1 are missing':
                    ok = True
                assert ok
            if 'ERROR:' in line:
                # Only ERROR because of configuration sending failures...
                if 'Connection does not exist!' not in line and 'Error when pinging: ' not in line and 'Failed sending configuration for ' not in line:
                    ok = False
            if 'CRITICAL:' in line:
                ok = False
        assert ok
        ok = True
        for line in iter(arbiter.stderr.readline, b''):
            ok = False
            print("*** " + line.rstrip())
        if not ok and sys.version_info > (2, 7):
            assert False, "stderr output!"

    @pytest.mark.skip("To be re-activated with spare mode")
    def test_arbiter_spare_missing_configuration(self):
        """ Run the Alignak Arbiter in spare mode - missing spare configuration

        :return:
        """
        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'run/test_launch_daemons')
        # copy etc config files in test/run/test_launch_daemons and change folder
        # in the files for pid and log files
        if os.path.exists(cfg_folder):
            shutil.rmtree(cfg_folder)

        shutil.copytree('../etc', cfg_folder)
        files = [cfg_folder + '/daemons/arbiterd.ini',
                 cfg_folder + '/arbiter/daemons/arbiter-master.cfg']
        replacements = {
            '/usr/local/var/run/alignak': '/tmp',
            '/usr/local/var/log/alignak': '/tmp',
            '/usr/local/etc/alignak': '/tmp',
            'arbiterd.log': 'arbiter-spare-configuration.log',
        }
        self._files_update(files, replacements)

        print("Cleaning pid and log files...")
        for daemon in ['arbiter']:
            if os.path.exists('/tmp/%sd.pid' % daemon):
                os.remove('/tmp/%sd.pid' % daemon)
                print("- removed /tmp/%sd.pid" % daemon)
            if os.path.exists('/tmp/%sd.log' % daemon):
                os.remove('/tmp/%sd.log' % daemon)
                print("- removed /tmp/%sd.log" % daemon)

        print("Launching arbiter in spare mode...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-a", cfg_folder + "/alignak.cfg",
                "-c", cfg_folder + "/daemons/arbiterd.ini",
                "-n", "arbiter-spare"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        sleep(5)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %s" % ret)
        assert ret is not None, "Arbiter is still running!"
        # Arbiter process must exit with a return code == 1
        assert ret == 1

    @pytest.mark.skip("To be re-activated with spare mode")
    def test_arbiter_spare(self):
        """ Run the Alignak Arbiter in spare mode - missing spare configuration

        :return:
        """
        # copy etc config files in test/run/test_launch_daemons and change folder
        # in the files for pid and log files
        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'run/test_launch_daemons')
        if os.path.exists(cfg_folder):
            shutil.rmtree(cfg_folder)

        shutil.copytree('../etc', cfg_folder)
        files = [cfg_folder + '/daemons/arbiterd.ini',
                 cfg_folder + '/arbiter/daemons/arbiter-master.cfg']
        replacements = {
            '/usr/local/var/run/alignak': '/tmp',
            '/usr/local/var/log/alignak': '/tmp',
            '/usr/local/etc/alignak': '/tmp',
            'arbiterd.log': 'arbiter-spare.log',
            'arbiter-master': 'arbiter-spare',
            'spare                   0': 'spare                   1'
        }
        self._files_update(files, replacements)

        print("Cleaning pid and log files...")
        for daemon in ['arbiter']:
            if os.path.exists('/tmp/%sd.pid' % daemon):
                os.remove('/tmp/%sd.pid' % daemon)
                print("- removed /tmp/%sd.pid" % daemon)
            if os.path.exists('/tmp/%sd.log' % daemon):
                os.remove('/tmp/%sd.log' % daemon)
                print("- removed /tmp/%sd.log" % daemon)

        print("Launching arbiter in spare mode...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-a", cfg_folder + "/alignak.cfg",
                "-c", cfg_folder + "/daemons/arbiterd.ini",
                "-n", "arbiter-spare"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        ret = arbiter.poll()
        # Arbiter must still be running ... it is still trying to dispatch the configuration!
        assert ret is None, "Arbiter exited!"

        sleep(5)

        # Arbiter never stops trying to send its configuration! We must kill it...

        print("Asking arbiter to end...")
        os.kill(arbiter.pid, signal.SIGTERM)

        ret = arbiter.poll()
        print("*** Arbiter exited on kill, no return code!")
        assert ret is None, "Arbiter is still running!"
        # No ERRORS because the daemons are not alive !
        ok = 0
        for line in iter(arbiter.stdout.readline, b''):
            print(">>> " + line.rstrip())
            if 'INFO:' in line:
                # I must find this line
                if '[alignak.daemons.arbiterdaemon] I found myself in the configuration: arbiter-spare' in line:
                    ok += 1
                # and this one also
                if '[alignak.daemons.arbiterdaemon] I am a spare Arbiter: arbiter-spare' in line:
                    ok += 1
                if 'I am not the master arbiter, I stop parsing the configuration' in line:
                    ok += 1
                if 'Waiting for master...' in line:
                    ok += 1
                if 'Waiting for master death' in line:
                    ok += 1
                assert 'CRITICAL:' not in line
        for line in iter(arbiter.stderr.readline, b''):
            print("*** " + line.rstrip())
            if sys.version_info > (2, 7):
                assert False, "stderr output!"
        assert ok == 5

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
        # Set an environment variable to change the default period of activity log (every 600 loops)
        os.environ['ALIGNAK_ACTIVITY_LOG'] = '2'

        req = requests.Session()

        # Set an environment variable to activate the logging of system cpu, memory and disk
        os.environ['ALIGNAK_DAEMONS_MONITORING'] = '2'

        cfg_folder = './run/test_launch_daemons'
        if os.path.exists(cfg_folder):
            shutil.rmtree(cfg_folder)

        shutil.copytree('../etc', cfg_folder)
        files = []
        # files = [cfg_folder + '/daemons/arbiterd.ini',
        #          cfg_folder + '/daemons/brokerd.ini',
        #          cfg_folder + '/daemons/pollerd.ini',
        #          cfg_folder + '/daemons/reactionnerd.ini',
        #          cfg_folder + '/daemons/receiverd.ini',
        #          cfg_folder + '/daemons/schedulerd.ini',
        #          cfg_folder + '/alignak.cfg',
        #          cfg_folder + '/arbiter/daemons/arbiter-master.cfg',
        #          cfg_folder + '/arbiter/daemons/broker-master.cfg',
        #          cfg_folder + '/arbiter/daemons/poller-master.cfg',
        #          cfg_folder + '/arbiter/daemons/reactionner-master.cfg',
        #          cfg_folder + '/arbiter/daemons/receiver-master.cfg',
        #          cfg_folder + '/arbiter/daemons/scheduler-master.cfg']
        replacements = {
            # '/usr/local/var/run/alignak': '/tmp',
            # '/usr/local/var/log/alignak': '/tmp',
            # '/usr/local/etc/alignak': '/tmp'
        }
        if ssl:
            shutil.copy('./cfg/ssl/server.crt', '/tmp/')
            shutil.copy('./cfg/ssl/server.key', '/tmp/')
            shutil.copy('./cfg/ssl/server.pem', '/tmp/')
            # Set daemons configuration to use SSL
            replacements.update({
                'use_ssl=0': 'use_ssl=1',
                '#server_cert=': 'server_cert=',
                '#server_key=': 'server_key=',
                '#server_dh=': 'server_dh=',
                '#hard_ssl_name_check=0': 'hard_ssl_name_check=0',
                'certs/': '',
                'use_ssl	                0': 'use_ssl	                1'
            })
        self._files_update(files, replacements)

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
                    "-c", cfg_folder + "/daemons/%sd.ini" % daemon]
            self.procs[daemon] = \
                subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            sleep(0.1)
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
            assert ret is None, "Daemon %s not started!" % name
            print("%s running (pid=%d)" % (name, self.procs[daemon].pid))

        # Let the daemons start ...
        sleep(2)

        print("Testing pid files and log files...")
        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            assert os.path.exists('/tmp/%sd.pid' % daemon), '/tmp/%sd.pid does not exist!' % daemon
            assert os.path.exists('/tmp/%sd.log' % daemon), '/tmp/%sd.log does not exist!' % daemon

        sleep(1)

        print("Launching arbiter...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-c", cfg_folder + "/daemons/arbiterd.ini",
                "-a", cfg_folder + "/alignak.cfg"]
        self.procs['arbiter'] = \
            subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', self.procs['arbiter'].pid))

        sleep(2)

        name = 'arbiter'
        print("Testing Arbiter start %s" % name)
        ret = self.procs[name].poll()
        if ret is not None:
            print("*** %s exited on start!" % (name))
            for line in iter(self.procs[name].stdout.readline, b''):
                print(">>> " + line.rstrip())
            for line in iter(self.procs[name].stderr.readline, b''):
                print(">>> " + line.rstrip())
        assert ret is None, "Daemon %s not started!" % name
        print("%s running (pid=%d)" % (name, self.procs[name].pid))

        sleep(1)

        print("Testing pid files and log files...")
        for daemon in ['arbiter']:
            assert os.path.exists('/tmp/%sd.pid' % daemon), '/tmp/%sd.pid does not exist!' % daemon
            assert os.path.exists('/tmp/%sd.log' % daemon), '/tmp/%sd.log does not exist!' % daemon

        # Let the arbiter build and dispatch its configuration
        sleep(5)

        http = 'http'
        if ssl:
            http = 'https'

        print("Testing ping")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/ping" % (http, port), verify=False)
            data = raw_data.json()
            assert data == 'pong', "Daemon %s  did not ping back!" % name

        if ssl:
            print("Testing ping with satellite SSL and client not SSL")
            for name, port in satellite_map.items():
                raw_data = req.get("http://localhost:%s/ping" % port)
                assert 'The client sent a plain HTTP request, but this server ' \
                                 'only speaks HTTPS on this port.' == raw_data.text

        print("Testing get_satellite_list")
        # Arbiter only
        raw_data = req.get("%s://localhost:%s/get_satellite_list" %
                           (http, satellite_map['arbiter']), verify=False)
        expected_data = {"reactionner": ["reactionner-master"],
                         "broker": ["broker-master"],
                         "arbiter": ["arbiter-master"],
                         "scheduler": ["scheduler-master"],
                         "receiver": ["receiver-master"],
                         "poller": ["poller-master"]}
        data = raw_data.json()
        assert isinstance(data, dict), "Data is not a dict!"
        for k, v in expected_data.iteritems():
            assert set(data[k]) == set(v)

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
            assert set(data) == expected_data, "Daemon %s has a bad API!" % name

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
            expected_data = set(name_to_interface[name](None).api_full())
            assert set(data) == expected_data, "Daemon %s has a bad API!" % name

        print("Testing get_running_id")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/get_running_id" % (http, port), verify=False)
            data = raw_data.json()
            print("%s, my running id: %s" % (name, data))
            assert isinstance(data, unicode), "Data is not an unicode!"

        # print("Testing wait_new_conf")
        # # Except Arbiter (not spare)
        # for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
        #     raw_data = req.get("%s://localhost:%s/wait_new_conf" % (http, satellite_map[daemon]), verify=False)
        #     data = raw_data.json()
        #     assert data == None

        print("Testing have_conf")
        # Except Arbiter (not spare)
        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            raw_data = req.get("%s://localhost:%s/have_conf" % (http, satellite_map[daemon]), verify=False)
            data = raw_data.json()
            print("%s, have_conf: %s" % (daemon, data))
            assert data == True, "Daemon %s should have a conf!" % daemon

            # raw_data = req.get("%s://localhost:%s/have_conf?magic_hash=1234567890" % (http, satellite_map[daemon]), verify=False)
            # data = raw_data.json()
            # print("%s, have_conf: %s" % (daemon, data))
            # assert data == False, "Daemon %s should not accept the magic hash!" % daemon

        print("Testing do_not_run")
        # Arbiter only
        raw_data = req.get("%s://localhost:%s/do_not_run" %
                           (http, satellite_map['arbiter']), verify=False)
        data = raw_data.json()
        print("%s, do_not_run: %s" % (name, data))
        # Arbiter master returns False, spare returns True
        assert data is False

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
            print("%s, raw stats: %s" % (name, data))
            assert isinstance(data, dict), "Data is not a dict!"

            if name in ['reactionner', 'poller']:
                scheduler_id = "XxX"
                for sched_uuid in data:
                    print("- scheduler: %s / %s" % (sched_uuid, data))
                    scheduler_id = sched_uuid
                    assert 'scheduler_name' in data[sched_uuid][0]
                    assert 'module' in data[sched_uuid][0]
                    assert 'worker' in data[sched_uuid][0]
                    assert 'worker_queue_size' in data[sched_uuid][0]
                    assert 'return_queue_size' in data[sched_uuid][0]
                print("Got a scheduler uuid: %s" % scheduler_id)
                assert scheduler_id != "XxX"

            if name in ['arbiter']:
                assert data == {}

            if name in ['broker']:
                assert 'modules_count' in data

            if name in ['scheduler']:
                assert 'latency_average' in data
                assert 'latency_maximum' in data
                assert 'latency_minimum' in data
                assert 'counters' in data

            if name in ['receiver']:
                assert data == {"command_buffer_size": 0}

        print("Testing what_i_managed")
        for name, port in satellite_map.items():
            print("%s, what I manage?" % (name))
            raw_data = req.get("%s://localhost:%s/what_i_managed" % (http, port), verify=False)
            data = raw_data.json()
            print("%s, what I manage: %s" % (name, data))
            assert isinstance(data, dict), "Data is not a dict!"
            if name != 'arbiter':
                assert 1 == len(data), "The dict must have 1 key/value!"
            else:
                assert 0 == len(data), "The dict must be empty!"

        print("Testing get_external_commands")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/get_external_commands" % (http, port), verify=False)
            data = raw_data.json()
            assert isinstance(data, list), "Data is not a list!"

        print("Testing get_log_level")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/get_log_level" % (http, port), verify=False)
            data = raw_data.json()
            print("%s, log level: %s" % (name, data))
            assert data == 'INFO'

        print("Testing set_log_level")
        for name, port in satellite_map.items():
            raw_data = req.post("%s://localhost:%s/set_log_level" % (http, port),
                                data=json.dumps({'loglevel': 'DEBUG'}),
                                headers={'Content-Type': 'application/json'},
                                verify=False)
            data = raw_data.json()
            print("%s, log level set as : %s" % (name, data))
            assert data == 'DEBUG'

        print("Testing get_log_level")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/get_log_level" % (http, port), verify=False)
            data = raw_data.json()
            print("%s, log level: %s" % (name, data))
            if sys.version_info < (2, 7):
                assert data == 'UNKNOWN' # Cannot get log level with python 2.6
            else:
                assert data == 'DEBUG'

        print("Testing get_all_states")
        # Arbiter only
        raw_data = req.get("%s://localhost:%s/get_all_states" %
                           (http, satellite_map['arbiter']), verify=False)
        data = raw_data.json()
        assert isinstance(data, dict), "Data is not a dict!"
        for daemon_type in data:
            daemons = data[daemon_type]
            print("Got Alignak state for: %ss / %d instances" % (daemon_type, len(daemons)))
            for daemon in daemons:
                print(" - %s: %s", daemon['%s_name' % daemon_type], daemon['alive'])
                print(" - %s: %s", daemon['%s_name' % daemon_type], daemon)
                assert daemon['alive']
                assert 'realms' not in daemon
                assert 'confs' not in daemon
                assert 'tags' not in daemon
                assert 'con' not in daemon
                assert 'realm_name' in daemon

        print("Testing get_objects_properties")
        for object in ['host', 'service', 'contact',
                       'hostgroup', 'servicegroup', 'contactgroup',
                       'command', 'timeperiod',
                       'notificationway', 'escalation',
                       'checkmodulation', 'macromodulation', 'resultmodulation',
                       'businessimpactmodulation'
                       'hostdependencie', 'servicedependencie',
                       'realm',
                       'arbiter', 'scheduler', 'poller', 'broker', 'reactionner', 'receiver']:
            # Arbiter only
            raw_data = req.get("%s://localhost:%s/get_objects_properties" %
                               (http, satellite_map['arbiter']),
                               params={'table': '%ss' % object}, verify=False)
            data = raw_data.json()
            assert isinstance(data, list), "Data is not a list!"
            for element in data:
                assert isinstance(element, dict), "Object data is not a dict!"
                print("%s: %s" % (object, element['%s_name' % object]))

        print("Testing fill_initial_broks")
        # Scheduler only
        raw_data = req.get("%s://localhost:%s/fill_initial_broks" %
                           (http, satellite_map['scheduler']),
                           params={'bname': 'broker-master'}, verify=False)
        data = raw_data.json()
        assert data is None, "Data must be None!"

        print("Testing get_broks")
        # Scheduler and poller only
        for name in ['scheduler', 'poller']:
            raw_data = req.get("%s://localhost:%s/get_broks" % (http, satellite_map[name]),
                               params={'bname': 'broker-master'}, verify=False)
            data = raw_data.json()
            print("%s, broks: %s" % (name, data))
            assert isinstance(data, dict), "Data is not a dict!"

        print("Testing get_returns")
        # get_return requested by scheduler to potential passive daemons
        for name in ['reactionner', 'poller']:
            raw_data = req.get("%s://localhost:%s/get_returns" %
                               (http, satellite_map[name]), params={'sched_id': scheduler_id}, verify=False)
            data = raw_data.json()
            assert isinstance(data, list), "Data is not a list!"

        print("Testing signals")
        for name, proc in self.procs.items():
            # SIGUSR1: memory dump
            self.procs[name].send_signal(signal.SIGUSR1)
            time.sleep(0.5)
            # SIGUSR2: objects dump
            self.procs[name].send_signal(signal.SIGUSR2)
            # SIGHUP: reload configuration
            # self.procs[name].send_signal(signal.SIGHUP)

            # Other signals is considered as a request to stop...

        # self.kill_running_daemons()
        for name, proc in self.procs.items():
            print("Asking %s to end..." % name)
            os.kill(self.procs[name].pid, signal.SIGTERM)

        time.sleep(1)

        for name, proc in self.procs.items():
            self._get_subproc_data(name)
            debug_log = False
            error_log = False
            print("%s stdout:" % (name))
            for line in iter(proc.stdout.readline, b''):
                if 'DEBUG:' in line:
                    debug_log = True
                if 'ERROR:' in line:
                    error_log = True
                print(">>> " + line.rstrip())
            print("%s stderr:" % (name))
            for line in iter(proc.stderr.readline, b''):
                print("*** " + line.rstrip())
            # The log contain some DEBUG log
            if sys.version_info >= (2, 7):
                assert debug_log # Cannot set/get log level with python 2.6
            # The log do not contain any ERROR log
            assert not error_log

        print("Done testing")
