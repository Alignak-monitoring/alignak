#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2018: Alignak team, see AUTHORS.txt file for contributors
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

import psutil

import subprocess
from time import sleep
import shutil

import pytest
from alignak_test import AlignakTest


class TestLaunchDaemonsModules(AlignakTest):
    def setUp(self):
        super(TestLaunchDaemonsModules, self).setUp()

        # copy the default shipped configuration files in /tmp/etc and change the root folder
        # used by the daemons for pid and log files in the alignak.ini file
        if os.path.exists('/tmp/etc/alignak'):
            shutil.rmtree('/tmp/etc/alignak')

        if os.path.exists('/tmp/alignak.log'):
            os.remove('/tmp/alignak.log')

        if os.path.exists('/tmp/monitoring-logs.log'):
            os.remove('/tmp/monitoring-logs.log')

        print("Preparing configuration...")
        shutil.copytree('../etc', '/tmp/etc/alignak')
        files = ['/tmp/etc/alignak/alignak.ini']
        replacements = {
            '_dist=/usr/local/': '_dist=/tmp'
        }
        self._files_update(files, replacements)

        # Clean the former existing pid and log files
        print("Cleaning pid and log files...")
        for daemon in ['arbiter-master', 'scheduler-master', 'broker-master',
                       'poller-master', 'reactionner-master', 'receiver-master']:
            if os.path.exists('/tmp/var/run/%s.pid' % daemon):
                os.remove('/tmp/var/run/%s.pid' % daemon)
            if os.path.exists('/tmp/var/log/%s.log' % daemon):
                os.remove('/tmp/var/log/%s.log' % daemon)

    def tearDown(self):
        print("Test terminated!")

    def test_daemons_modules(self):
        """Running the Alignak daemons with a simple configuration using the Example daemon
        configured on all the default daemons

        :return: None
        """
        daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                        'receiver-master', 'scheduler-master']

        self._run_alignak_daemons(cfg_folder='cfg/run_daemons_1', daemons_list=daemons_list,
                                  run_folder='/tmp', runtime=10)

        self._stop_alignak_daemons()

        # Check daemons log files
        ignored_warnings = [
            'No realms defined,',
            'Did not get any',
            'notifications are enabled but no contacts',
            'hosts configuration warnings',
            'The module Example is not a worker one',
            'Add failed attempt for ',
            'is still living after a normal kill',
            # Sometimes not killed during the test because of SIGTERM
            'did not stopped, trying to kill',
            'My Arbiter wants me to wait for a new configuration'
        ]
        (errors_raised, warnings_raised) = \
            self._check_daemons_log_for_errors(daemons_list, ignored_warnings=ignored_warnings)

        # self.kill_daemons()
        assert errors_raised == 0, "Error logs raised!"
        print("No unexpected error logs raised by the daemons")

        assert warnings_raised == 0, "Warning logs raised!"
        print("No unexpected warning logs raised by the daemons")

    # @pytest.mark.skipif(sys.version_info[:2] < (2, 7), reason="Not available for Python < 2.7")
    @pytest.mark.skip("No real interest for Alignak testings...")
    def test_daemons_modules_logs(self):
        """Running the Alignak daemons with the monitoring logs module

        :return: None
        """
        if os.path.exists('/tmp/monitoring-logs.log'):
            os.remove('/tmp/monitoring-logs.log')

        daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                        'receiver-master', 'scheduler-master']

        self._run_alignak_daemons(cfg_folder='cfg/run_daemons_logs',
                                  daemons_list=daemons_list,
                                  run_folder='/tmp', runtime=30, arbiter_only=True)

        self._stop_alignak_daemons()

        # Check daemons log files
        ignored_warnings = [
            'Alignak Backend is not configured. Some module features will not be available.',
            'defined logger configuration file '
            # 'Error on backend login: ',
            # 'Alignak backend is currently not available',
            # 'Exception: BackendException raised with code 1000',
            # 'Response: '
        ]
        ignored_errors = [
            # 'Error on backend login: ',
            # 'Configured user account is not allowed for this module'
        ]
        (errors_raised, warnings_raised) = \
            self._check_daemons_log_for_errors(daemons_list, ignored_warnings=ignored_warnings,
                                               ignored_errors=ignored_errors)

        # self.kill_daemons()
        assert errors_raised == 0, "Error logs raised!"
        print("No unexpected error logs raised by the daemons")

        assert warnings_raised == 0, "Warning logs raised!"
        print("No unexpected warning logs raised by the daemons")

        assert os.path.exists('/tmp/monitoring-logs.log'), '/tmp/monitoring-logs.log does not exist!'
        count = 0
        print("Monitoring logs:")
        with open('/tmp/monitoring-logs.log') as f:
            for line in f:
                print("- : %s" % line)
                count += 1
        """
        [1496076886] INFO: CURRENT HOST STATE: localhost;UP;HARD;0;
        [1496076886] INFO: TIMEPERIOD TRANSITION: 24x7;-1;1
        [1496076886] INFO: TIMEPERIOD TRANSITION: workhours;-1;1
        """
        assert count >= 2

    # @pytest.mark.skipif(sys.version_info[:2] < (2, 7), reason="Not available for Python < 2.7")
    @pytest.mark.skip("No real interest for Alignak testings...")
    def test_daemons_modules_logs_restart_module(self):
        """Running the Alignak daemons with the monitoring logs module - stop and restart the module

        :return: None
        """
        if os.path.exists('/tmp/monitoring-logs.log'):
            os.remove('/tmp/monitoring-logs.log')

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'cfg/run_daemons_logs')
        tmp_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'run/test_launch_daemons_modules_logs')

        # Currently it is the same as the default execution ... to be modified later.
        cfg_modules = {
            'arbiter': '', 'scheduler': '', 'broker': 'logs',
            'poller': '', 'reactionner': '', 'receiver': ''
        }
        nb_errors = self._run_alignak_daemons_modules(cfg_folder, tmp_folder, cfg_modules, 10)
        assert nb_errors == 0, "Error logs raised!"
        print("No error logs raised when daemons started and loaded the modules")

        assert os.path.exists('/tmp/monitoring-logs.log'), '/tmp/monitoring-logs.log does not exist!'
        count = 0
        print("Monitoring logs:")
        with open('/tmp/monitoring-logs.log') as f:
            for line in f:
                print("- : %s" % line)
                count += 1
        """
        [1496076886] INFO: CURRENT HOST STATE: localhost;UP;HARD;0;
        [1496076886] INFO: TIMEPERIOD TRANSITION: 24x7;-1;1
        [1496076886] INFO: TIMEPERIOD TRANSITION: workhours;-1;1
        """
        assert count >= 2

        # Kill the logs module
        module_pid = None
        for proc in psutil.process_iter():
            if "module: logs" in proc.name():
                print("Found logs module in the ps: %s (pid=%d)" % (proc.name(), proc.pid))
                module_pid = proc.pid
        assert module_pid is not None

        print("Asking pid=%d to end..." % (module_pid))
        daemon_process = psutil.Process(module_pid)
        daemon_process.terminate()
        try:
            daemon_process.wait(10)
        except psutil.TimeoutExpired:
            assert False, "Timeout!"
        except psutil.NoSuchProcess:
            print("not existing!")
            pass

        # Wait for the module to restart
        time.sleep(5)

        # self._kill_alignak_daemons()

        # Search for some specific logs in the broker daemon logs
        expected_logs = {
            'broker': [
                "[alignak.modulesmanager] Importing Python module 'alignak_module_logs' for logs...",
                "[alignak.modulesmanager] Module properties: {'daemons': ['broker'], 'phases': ['running'], 'type': 'logs', 'external': True}",
                "[alignak.modulesmanager] Imported 'alignak_module_logs' for logs",
                "[alignak.modulesmanager] Loaded Python module 'alignak_module_logs' (logs)",
                # "[alignak.module] Give an instance of alignak_module_logs for alias: logs",
                "[alignak.module.logs] logger default configuration:",
                "[alignak.module.logs]  - rotating logs in /tmp/monitoring-logs.log",
                "[alignak.module.logs]  - log level: 20",
                "[alignak.module.logs]  - rotation every 1 midnight, keeping 365 files",
                "[alignak.basemodule] Process for module logs received a signal: 15",
                "[alignak.module.logs] stopping...",
                "[alignak.module.logs] stopped",
                "[alignak.modulesmanager] The external module logs died unexpectedly!",
                "[alignak.modulesmanager] Setting the module logs to restart",
                "[alignak.basemodule] Starting external process for module logs..."
            ]
        }

        errors_raised = 0
        travis_run = 'TRAVIS' in os.environ
        for name in ['broker']:
            assert os.path.exists('/tmp/%sd.log' % name), '/tmp/%sd.log does not exist!' % name
            print("-----\n%s log file\n" % name)
            with open('/tmp/%sd.log' % name) as f:
                lines = f.readlines()
                logs = []
                for line in lines:
                    # Catches WARNING and ERROR logs
                    if 'WARNING' in line:
                        line = line.split('WARNING: ')
                        line = line[1]
                        line = line.strip()
                        print("--- %s" % line[:-1])
                    if 'ERROR' in line:
                        if "The external module logs died unexpectedly!" not in line:
                            errors_raised += 1
                        line = line.split('ERROR: ')
                        line = line[1]
                        line = line.strip()
                        print("*** %s" % line[:-1])
                    # Catches INFO logs
                    if 'INFO' in line:
                        line = line.split('INFO: ')
                        line = line[1]
                        line = line.strip()
                        if not travis_run:
                            print("    %s" % line)
                    logs.append(line)

            if not travis_run:
                print(logs)
            for log in expected_logs[name]:
                print("Last checked log %s: %s" % (name, log))
                assert log in logs, logs

        # Still only two logs
        assert os.path.exists('/tmp/monitoring-logs.log'), '/tmp/monitoring-logs.log does not exist!'
        count = 0
        print("Monitoring logs:")
        with open('/tmp/monitoring-logs.log') as f:
            for line in f:
                print("- : %s" % line)
                count += 1
        """
        [1496076886] INFO: CURRENT HOST STATE: localhost;UP;HARD;0;
        [1496076886] INFO: TIMEPERIOD TRANSITION: 24x7;-1;1
        [1496076886] INFO: TIMEPERIOD TRANSITION: workhours;-1;1
        """
        assert count >= 2

    # @pytest.mark.skipif(sys.version_info[:2] < (2, 7), reason="Not available for Python < 2.7")
    @pytest.mark.skip("No real interest for Alignak testings...")
    def test_daemons_modules_ws(self):
        """Running the Alignak daemons with the Web services module

        :return: None
        """
        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'cfg/run_daemons_ws')
        tmp_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'run/test_launch_daemons_modules_ws')

        # Currently it is the same as the default execution ... to be modified later.
        cfg_modules = {
            'arbiter': '', 'scheduler': '', 'broker': '',
            'poller': '', 'reactionner': '', 'receiver': 'web-services'
        }
        nb_errors = self._run_alignk_daemons_modules(cfg_folder, tmp_folder, cfg_modules, 10)
        assert nb_errors == 0, "Error logs raised!"
        print("No error logs raised when daemons started and loaded the modules")

        # Search the WS module
        module_pid = None
        for proc in psutil.process_iter():
            if "module: web-services" in proc.name():
                print("Found WS module in the ps: %s (pid=%d)" % (proc.name(), proc.pid))
                module_pid = proc.pid
        assert module_pid is not None

        self._stop_alignak_daemons()

        # Search for some specific logs in the broker daemon logs
        expected_logs = {
            'receiver': [
                "[alignak.modulesmanager] Importing Python module 'alignak_module_ws' for web-services...",
                "[alignak.modulesmanager] Module properties: {'daemons': ['receiver'], 'phases': ['running'], 'type': 'web-services', 'external': True}",
                "[alignak.modulesmanager] Imported 'alignak_module_ws' for web-services",
                "[alignak.modulesmanager] Loaded Python module 'alignak_module_ws' (web-services)",
                # "[alignak.module] Give an instance of alignak_module_ws for alias: web-services",
                # "[alignak.module.web-services] Alignak host creation allowed: False",
                # "[alignak.module.web-services] Alignak service creation allowed: False",
                # "[alignak.module.web-services] Alignak external commands, set timestamp: True",
                # "[alignak.module.web-services] Alignak Backend is not configured. Some module features will not be available.",
                # "[alignak.module.web-services] Alignak Arbiter configuration: 127.0.0.1:7770",
                # "[alignak.module.web-services] Alignak Arbiter polling period: 5",
                # "[alignak.module.web-services] Alignak daemons get status period: 10",
                # "[alignak.module.web-services] SSL is not enabled, this is not recommended. You should consider enabling SSL!",
                "[alignak.daemon] I correctly loaded my modules: [web-services]",
                # On arbiter stop:
                # "[alignak.module.web-services] Alignak arbiter is currently not available.",

                "[alignak.modulesmanager] Request external process to stop for web-services",
                "[alignak.basemodule] I'm stopping module u'web-services' (pid=%d)" % module_pid,
                "[alignak.modulesmanager] External process stopped.",
                "[alignak.daemon] Stopped receiver-master."
            ]
        }

        errors_raised = 0
        for name in ['receiver']:
            assert os.path.exists('/tmp/%sd.log' % name), '/tmp/%sd.log does not exist!' % name
            print("-----\n%s log file\n" % name)
            with open('/tmp/%sd.log' % name) as f:
                lines = f.readlines()
                logs = []
                for line in lines:
                    # Catches WARNING and ERROR logs
                    if 'WARNING' in line:
                        line = line.split('WARNING: ')
                        line = line[1]
                        line = line.strip()
                        print("--- %s" % line[:-1])
                    if 'ERROR' in line:
                        print("*** %s" % line[:-1])
                        if "The external module logs died unexpectedly!" not in line:
                            errors_raised += 1
                        line = line.split('ERROR: ')
                        line = line[1]
                        line = line.strip()
                    # Catches INFO logs
                    if 'INFO' in line:
                        line = line.split('INFO: ')
                        line = line[1]
                        line = line.strip()
                        print("    %s" % line)
                    logs.append(line)

            for log in logs:
                print("...%s" % log)
            for log in expected_logs[name]:
                print("Last checked log %s: %s" % (name, log))
                assert log in logs, logs

    # @pytest.mark.skipif(sys.version_info[:2] < (2, 7), reason="Not available for Python < 2.7")
    @pytest.mark.skip("No real interest for Alignak testings...")
    def test_daemons_modules_ws_logs(self):
        """Running the Alignak daemons with the Web services and Logs modules

        :return: None
        """
        if os.path.exists('/tmp/monitoring-logs.log'):
            os.remove('/tmp/monitoring-logs.log')

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'cfg/run_daemons_ws_logs')
        tmp_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'run/test_launch_daemons_modules_ws_logs')

        # Currently it is the same as the default execution ... to be modified later.
        cfg_modules = {
            'arbiter': '', 'scheduler': '', 'broker': 'logs',
            'poller': '', 'reactionner': '', 'receiver': 'web-services'
        }
        nb_errors = self._run_daemons_modules(cfg_folder, tmp_folder, cfg_modules, 10)
        assert nb_errors == 0, "Error logs raised!"
        print("No error logs raised when daemons started and loaded the modules")

        # Search the modules
        modules_pids = {}
        for proc in psutil.process_iter():
            if "module: web-services" in proc.name():
                print("Found WS module in the ps: %s (pid=%d)" % (proc.name(), proc.pid))
                modules_pids['ws'] = proc.pid
            if "module: logs" in proc.name():
                print("Found logs module in the ps: %s (pid=%d)" % (proc.name(), proc.pid))
                modules_pids['logs'] = proc.pid
        assert len(modules_pids) == 2

        assert os.path.exists('/tmp/monitoring-logs.log'), '/tmp/monitoring-logs.log does not exist!'
        count = 0
        print("Monitoring logs:")
        with open('/tmp/monitoring-logs.log') as f:
            for line in f:
                print("- : %s" % line)
                count += 1
        """
        [1496076886] INFO: CURRENT HOST STATE: localhost;UP;HARD;0;
        [1496076886] INFO: TIMEPERIOD TRANSITION: 24x7;-1;1
        [1496076886] INFO: TIMEPERIOD TRANSITION: workhours;-1;1
        """
        assert count >= 2
        self.kill_daemons()

        # Search for some specific logs in the broker daemon logs
        expected_logs = {
            'receiver': [
                "[alignak.modulesmanager] Importing Python module 'alignak_module_ws' for web-services...",
                "[alignak.modulesmanager] Module properties: {'daemons': ['receiver'], 'phases': ['running'], 'type': 'web-services', 'external': True}",
                "[alignak.modulesmanager] Imported 'alignak_module_ws' for web-services",
                "[alignak.modulesmanager] Loaded Python module 'alignak_module_ws' (web-services)",
                # "[alignak.module] Give an instance of alignak_module_ws for alias: web-services",
                # "[alignak.module.web-services] Alignak host creation allowed: False",
                # "[alignak.module.web-services] Alignak service creation allowed: False",
                # "[alignak.module.web-services] Alignak external commands, set timestamp: True",
                # "[alignak.module.web-services] Alignak Backend is not configured. Some module features will not be available.",
                # "[alignak.module.web-services] Alignak Arbiter configuration: 127.0.0.1:7770",
                # "[alignak.module.web-services] Alignak Arbiter polling period: 5",
                # "[alignak.module.web-services] Alignak daemons get status period: 10",
                # "[alignak.module.web-services] SSL is not enabled, this is not recommended. You should consider enabling SSL!",
                "[alignak.daemon] I correctly loaded my modules: [web-services]",
                # On arbiter stop:
                # "[alignak.module.web-services] Alignak arbiter is currently not available.",

                "[alignak.modulesmanager] Request external process to stop for web-services",
                "[alignak.basemodule] I'm stopping module u'web-services' (pid=%d)" % modules_pids['ws'],
                "[alignak.modulesmanager] External process stopped.",
                "[alignak.daemon] Stopped receiver-master."
            ],
            'broker': [
                "[alignak.modulesmanager] Importing Python module 'alignak_module_logs' for logs...",
                "[alignak.modulesmanager] Module properties: {'daemons': ['broker'], 'phases': ['running'], 'type': 'logs', 'external': True}",
                "[alignak.modulesmanager] Imported 'alignak_module_logs' for logs",
                "[alignak.modulesmanager] Loaded Python module 'alignak_module_logs' (logs)",
                # "[alignak.module] Give an instance of alignak_module_logs for alias: logs",
                "[alignak.module.logs] logger default configuration:",
                "[alignak.module.logs]  - rotating logs in /tmp/monitoring-logs.log",
                "[alignak.module.logs]  - log level: 10",
                "[alignak.module.logs]  - rotation every 1 midnight, keeping 365 files",
                "[alignak.module.logs] Alignak Backend is not configured. Some module features will not be available.",
                "[alignak.daemon] I correctly loaded my modules: [logs]",
                # On arbiter stop:
                # "[alignak.module.web-services] Alignak arbiter is currently not available.",

                "[alignak.modulesmanager] Request external process to stop for logs",
                "[alignak.basemodule] I'm stopping module u'logs' (pid=%d)" % modules_pids['logs'],
                "[alignak.modulesmanager] External process stopped.",
                "[alignak.daemon] Stopped broker-master."
            ]
        }

        errors_raised = 0
        for name in ['receiver', 'broker']:
            assert os.path.exists('/tmp/%sd.log' % name), '/tmp/%sd.log does not exist!' % name
            print("-----\n%s log file\n" % name)
            with open('/tmp/%sd.log' % name) as f:
                lines = f.readlines()
                logs = []
                for line in lines:
                    # Catches WARNING and ERROR logs
                    if 'WARNING' in line:
                        line = line.split('WARNING: ')
                        line = line[1]
                        line = line.strip()
                        print("--- %s" % line[:-1])
                    if 'ERROR' in line:
                        print("*** %s" % line[:-1])
                        errors_raised += 1
                        line = line.split('ERROR: ')
                        line = line[1]
                        line = line.strip()
                    # Catches INFO logs
                    if 'INFO' in line:
                        line = line.split('INFO: ')
                        line = line[1]
                        line = line.strip()
                        print("    %s" % line)
                    logs.append(line)

            for log in logs:
                print("...%s" % log)
            for log in expected_logs[name]:
                print("Last checked log %s: %s" % (name, log))
                assert log in logs, logs

    # @pytest.mark.skipif(sys.version_info[:2] < (2, 7), reason="Not available for Python < 2.7")
    @pytest.mark.skip("No real interest for Alignak testings...")
    def test_daemons_modules_backend(self):
        """Running the Alignak daemons with the backend modules - backend is not running so
        all modules are in error

        :return: None
        """
        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'cfg/run_daemons_backend')
        tmp_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'run/test_launch_daemons_modules_backend')

        # Currently it is the same as the default execution ... to be modified later.
        cfg_modules = {
            'arbiter': 'backend_arbiter', 'scheduler': 'backend_scheduler',
            'broker': 'backend_broker',
            'poller': '', 'reactionner': '', 'receiver': ''
        }
        nb_errors = self._run_alignk_daemons_modules(cfg_folder, tmp_folder, cfg_modules, 20)

        # Search the WS module
        # module_pid = None
        # for proc in psutil.process_iter():
        #     if "module: web-services" in proc.name():
        #         print("Found WS module in the ps: %s (pid=%d)" % (proc.name(), proc.pid))
        #         module_pid = proc.pid
        # assert module_pid is not None

        self._kill_alignak_daemons()

        assert nb_errors >= 3, "Error logs raised!"
        # 1 for the arbiter
        # 1 for the broker
        # 3 for the scheduler
        print("Expected error logs raised when daemons started and loaded the modules")

        # Search for some specific logs in the broker daemon logs
        expected_logs = {
            'arbiter': [
                "[alignak.modulesmanager] Importing Python module 'alignak_module_backend.arbiter' for backend_arbiter...",
                "[alignak.modulesmanager] Module properties: {'daemons': ['arbiter'], 'phases': ['configuration'], 'type': 'backend_arbiter', 'external': False}",
                "[alignak.modulesmanager] Imported 'alignak_module_backend.arbiter' for backend_arbiter",
                "[alignak.modulesmanager] Loaded Python module 'alignak_module_backend.arbiter' (backend_arbiter)",
                # "[alignak.module] Give an instance of alignak_module_backend.arbiter for alias: backend_arbiter",
                "[alignak.module.backend_arbiter] Number of processes used by backend client: 1",
                "[alignak.module.backend_arbiter] Alignak backend is not available for login. No backend connection, attempt: 1",
                "[alignak.module.backend_arbiter] Alignak backend is not available for login. No backend connection, attempt: 2",
                "[alignak.module.backend_arbiter] Alignak backend is not available for login. No backend connection, attempt: 3",
                "[alignak.module.backend_arbiter] bypass objects loading when Arbiter is in verify mode: False",
                "[alignak.module.backend_arbiter] configuration reload check period: 5 minutes",
                "[alignak.module.backend_arbiter] actions check period: 15 seconds",
                "[alignak.module.backend_arbiter] daemons state update period: 60 seconds",
                "[alignak.modulesmanager] Trying to initialize module: backend_arbiter",
                "[alignak.daemon] I correctly loaded my modules: [backend_arbiter]",
                "[alignak.daemons.arbiterdaemon] Getting Alignak global configuration from module 'backend_arbiter'",
                "[alignak.module.backend_arbiter] Alignak backend connection is not available. Skipping Alignak configuration load and provide an empty configuration to the Arbiter.",
                "[alignak.module.backend_arbiter] Alignak backend connection is not available. Skipping objects load and provide an empty list to the Arbiter."
            ],
            'broker': [
                "[alignak.modulesmanager] Importing Python module 'alignak_module_backend.broker' for backend_broker...",
                "[alignak.modulesmanager] Module properties: {'daemons': ['broker'], 'type': 'backend_broker', 'external': True}",
                "[alignak.modulesmanager] Imported 'alignak_module_backend.broker' for backend_broker",
                "[alignak.modulesmanager] Loaded Python module 'alignak_module_backend.broker' (backend_broker)",
                # "[alignak.module] Give an instance of alignak_module_backend.broker for alias: backend_broker",
                "[alignak.module.backend_broker] Number of processes used by backend client: 1",
                # "[alignak.module.backend_broker] Error on backend login: ",
                "[alignak.module.backend_broker] Configured user account is not allowed for this module",
                "[alignak.daemon] I correctly loaded my modules: [backend_broker]",
                "[alignak.modulesmanager] Trying to initialize module: backend_broker",
            ],
            'scheduler': [
                "[alignak.modulesmanager] Importing Python module 'alignak_module_backend.scheduler' for backend_scheduler...",
                "[alignak.modulesmanager] Module properties: {'daemons': ['scheduler'], 'phases': ['running'], 'type': 'backend_scheduler', 'external': False}",
                "[alignak.modulesmanager] Imported 'alignak_module_backend.scheduler' for backend_scheduler",
                "[alignak.modulesmanager] Loaded Python module 'alignak_module_backend.scheduler' (backend_scheduler)",
                # "[alignak.module] Give an instance of alignak_module_backend.scheduler for alias: backend_scheduler",
                "[alignak.module.backend_scheduler] Number of processes used by backend client: 1",
                "[alignak.module.backend_scheduler] Alignak backend is not available for login. No backend connection, attempt: 1",
                "[alignak.modulesmanager] Trying to initialize module: backend_scheduler",
                "[alignak.daemon] I correctly loaded my modules: [backend_scheduler]",
            ]
        }

        errors_raised = 0
        for name in ['arbiter', 'broker', 'scheduler']:
            assert os.path.exists('/tmp/%sd.log' % name), '/tmp/%sd.log does not exist!' % name
            print("-----\n%s log file\n" % name)
            with open('/tmp/%sd.log' % name) as f:
                lines = f.readlines()
                logs = []
                for line in lines:
                    # Catches WARNING and ERROR logs
                    if 'WARNING:' in line:
                        line = line.split('WARNING: ')
                        line = line[1]
                        line = line.strip()
                        print("--- %s" % line[:-1])
                    if 'ERROR:' in line:
                        print("*** %s" % line[:-1])
                        if "Error on backend login:" not in line \
                            and "Configured user account is not allowed for this module" not in line \
                            and "Alignak backend connection is not available. " not in line:
                            errors_raised += 1
                        line = line.split('ERROR: ')
                        line = line[1]
                        line = line.strip()
                    # Catches INFO logs
                    if 'INFO:' in line:
                        line = line.split('INFO: ')
                        line = line[1]
                        line = line.strip()
                        print("    %s" % line)
                    logs.append(line)

            for log in logs:
                print("...%s" % log)
            for log in expected_logs[name]:
                print("Last checked log %s: %s" % (name, log))
                assert log in logs, logs
        assert errors_raised == 0
