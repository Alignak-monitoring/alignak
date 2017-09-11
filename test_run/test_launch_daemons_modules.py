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

import psutil

import subprocess
from time import sleep
import shutil

import pytest
from alignak_test import AlignakTest


class LaunchDaemons(AlignakTest):
    def setUp(self):
        self.procs = {}

    def tearDown(self):
        print("Test terminated!")

    def kill_daemons(self):
        """Kill the running daemons

        :return:
        """
        print("Stopping the daemons...")
        start = time.time()
        for name, proc in self.procs.items():
            print("Asking %s (pid=%d) to end..." % (name, proc.pid))
            try:
                daemon_process = psutil.Process(proc.pid)
            except psutil.NoSuchProcess:
                print("not existing!")
                continue
            children = daemon_process.children(recursive=True)
            daemon_process.terminate()
            try:
                daemon_process.wait(10)
            except psutil.TimeoutExpired:
                print("timeout!")
            except psutil.NoSuchProcess:
                print("not existing!")
                pass
            for child in children:
                try:
                    print("Asking %s child (pid=%d) to end..." % (child.name(), child.pid))
                    child.terminate()
                except psutil.NoSuchProcess:
                    print("-> still dead: %s" % child)
                    pass
            gone, still_alive = psutil.wait_procs(children, timeout=10)
            for process in still_alive:
                try:
                    print("Killing %s (pid=%d)!" % (child.name(), child.pid))
                    process.kill()
                except psutil.NoSuchProcess:
                    pass
            print("%s terminated" % (name))
        print("Stopping daemons duration: %d seconds" % (time.time() - start))

    def _run_daemons_modules(self, cfg_folder='../etc',
                             tmp_folder='./run/test_launch_daemons_modules',
                             cfg_modules=None, runtime=5):
        """Update the provided configuration with some informations on the run
        Run the Alignak daemons with configured modules

        :return: None
        """
        self.print_header()

        # copy etc config files in test/run/test_launch_daemons_modules and change folder
        # in the files for pid and log files
        if os.path.exists(tmp_folder):
            shutil.rmtree(tmp_folder)

        shutil.copytree(cfg_folder, tmp_folder)
        files = [tmp_folder + '/daemons/arbiterd.ini',
                 tmp_folder + '/daemons/brokerd.ini',
                 tmp_folder + '/daemons/pollerd.ini',
                 tmp_folder + '/daemons/reactionnerd.ini',
                 tmp_folder + '/daemons/receiverd.ini',
                 tmp_folder + '/daemons/schedulerd.ini',
                 tmp_folder + '/alignak.cfg',
                 tmp_folder + '/arbiter/daemons/arbiter-master.cfg',
                 tmp_folder + '/arbiter/daemons/broker-master.cfg',
                 tmp_folder + '/arbiter/daemons/poller-master.cfg',
                 tmp_folder + '/arbiter/daemons/reactionner-master.cfg',
                 tmp_folder + '/arbiter/daemons/receiver-master.cfg',
                 tmp_folder + '/arbiter/daemons/scheduler-master.cfg']
        replacements = {
            '/usr/local/var/run/alignak': '/tmp',
            '/usr/local/var/log/alignak': '/tmp',
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

        # declare modules in the daemons configuration
        if cfg_modules is None:
            shutil.copy('./cfg/default/mod-example.cfg', tmp_folder + '/arbiter/modules')
            cfg_modules = {
                'arbiter': 'Example', 'scheduler': 'Example', 'broker': 'Example',
                'poller': 'Example', 'reactionner': 'Example', 'receiver': 'Example',
            }

        print("Setting up daemons modules configuration...")
        for daemon in ['arbiter', 'scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            if daemon not in cfg_modules:
                continue

            filename = tmp_folder + '/arbiter/daemons/%s-master.cfg' % daemon
            replacements = {'modules': 'modules ' + cfg_modules[daemon]}
            lines = []
            with open(filename) as infile:
                for line in infile:
                    for src, target in replacements.iteritems():
                        line = line.replace(src, target)
                    lines.append(line)
            with open(filename, 'w') as outfile:
                for line in lines:
                    outfile.write(line)

        self.setup_with_file(tmp_folder + '/alignak.cfg')
        assert self.conf_is_correct

        print("Cleaning pid and log files...")
        for daemon in ['arbiter', 'scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            if os.path.exists('/tmp/%sd.pid' % daemon):
                os.remove('/tmp/%sd.pid' % daemon)
                print("- removed /tmp/%sd.pid" % daemon)
            if os.path.exists('/tmp/%sd.log' % daemon):
                os.remove('/tmp/%sd.log' % daemon)
                print("- removed /tmp/%sd.log" % daemon)

        print("Launching the daemons...")
        self.procs = {}
        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            args = ["../alignak/bin/alignak_%s.py" %daemon,
                    "-c", tmp_folder + "/daemons/%sd.ini" % daemon]
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

        # Let the daemons initialize ...
        sleep(3)

        print("Testing that pid files and log files exist...")
        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            assert os.path.exists('/tmp/%sd.pid' % daemon), '/tmp/%sd.pid does not exist!' % daemon
            assert os.path.exists('/tmp/%sd.log' % daemon), '/tmp/%sd.log does not exist!' % daemon

        sleep(1)

        print("Launching arbiter...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-c", tmp_folder + "/daemons/arbiterd.ini",
                "-a", tmp_folder + "/alignak.cfg"]
        self.procs['arbiter'] = \
            subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', self.procs['arbiter'].pid))

        sleep(1)

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

        print("Testing that pid files and log files exist...")
        for daemon in ['arbiter']:
            assert os.path.exists('/tmp/%sd.pid' % daemon), '/tmp/%sd.pid does not exist!' % daemon
            assert os.path.exists('/tmp/%sd.log' % daemon), '/tmp/%sd.log does not exist!' % daemon

        # Let the arbiter build and dispatch its configuration
        sleep(runtime)

        print("Check if some errors were raised...")
        nb_errors = 0
        for daemon in ['arbiter', 'scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            assert os.path.exists('/tmp/%sd.log' % daemon), '/tmp/%sd.log does not exist!' % daemon
            daemon_errors = False
            print("-----\n%s log file\n-----\n" % daemon)
            with open('/tmp/%sd.log' % daemon) as f:
                for line in f:
                    if 'Example' in line:
                        print("Example module log: %s" % line)
                    if 'WARNING:' in line:
                        print(line[:-1])
                    if 'ERROR:' in line or 'CRITICAL:' in line:
                        print(line[:-1])
                        daemon_errors = True
                        nb_errors += 1
        return nb_errors

    def test_daemons_modules(self):
        """Running the Alignak daemons with a simple configuration using the Example daemon
        configured on all the default daemons

        :return: None
        """
        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cfg/run_daemons_1')

        # Currently it is the same as the default execution ... to be modified later.
        cfg_modules = {
            'arbiter': 'Example', 'scheduler': 'Example', 'broker': 'Example',
            'poller': 'Example', 'reactionner': 'Example', 'receiver': 'Example',
        }
        nb_errors = self._run_daemons_modules(cfg_folder=cfg_folder,
                                              tmp_folder='./run/test_launch_daemons_modules_1',
                                              cfg_modules=cfg_modules)
        assert nb_errors == 0, "Error logs raised!"
        print("No error logs raised when daemons started and loaded the modules")
        self.kill_daemons()

    @pytest.mark.skipif(sys.version_info[:2] < (2, 7), reason="Not available for Python < 2.7")
    def test_daemons_modules_logs(self):
        """Running the Alignak daemons with the monitoring logs module

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
        nb_errors = self._run_daemons_modules(cfg_folder, tmp_folder, cfg_modules, 10)
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
        self.kill_daemons()

    @pytest.mark.skipif(sys.version_info[:2] < (2, 7), reason="Not available for Python < 2.7")
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
        nb_errors = self._run_daemons_modules(cfg_folder, tmp_folder, cfg_modules, 10)
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

        self.kill_daemons()

        # Search for some specific logs in the broker daemon logs
        expected_logs = {
            'broker': [
                "[alignak.modulesmanager] Importing Python module 'alignak_module_logs' for logs...",
                "[alignak.modulesmanager] Module properties: {'daemons': ['broker'], 'phases': ['running'], 'type': 'logs', 'external': True}",
                "[alignak.modulesmanager] Imported 'alignak_module_logs' for logs",
                "[alignak.modulesmanager] Loaded Python module 'alignak_module_logs' (logs)",
                "[alignak.module] Give an instance of alignak_module_logs for alias: logs",
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
                        print("    %s" % line)
                    logs.append(line)

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
        nb_errors = self._run_daemons_modules(cfg_folder, tmp_folder, cfg_modules, 10)
        assert nb_errors == 0, "Error logs raised!"
        print("No error logs raised when daemons started and loaded the modules")

        # Search the WS module
        module_pid = None
        for proc in psutil.process_iter():
            if "module: web-services" in proc.name():
                print("Found WS module in the ps: %s (pid=%d)" % (proc.name(), proc.pid))
                module_pid = proc.pid
        assert module_pid is not None

        self.kill_daemons()

        # Search for some specific logs in the broker daemon logs
        expected_logs = {
            'receiver': [
                "[alignak.modulesmanager] Importing Python module 'alignak_module_ws' for web-services...",
                "[alignak.modulesmanager] Module properties: {'daemons': ['receiver'], 'phases': ['running'], 'type': 'web-services', 'external': True}",
                "[alignak.modulesmanager] Imported 'alignak_module_ws' for web-services",
                "[alignak.modulesmanager] Loaded Python module 'alignak_module_ws' (web-services)",
                "[alignak.module] Give an instance of alignak_module_ws for alias: web-services",
                "[alignak.module.web-services] Alignak host creation allowed: False",
                "[alignak.module.web-services] Alignak service creation allowed: False",
                "[alignak.module.web-services] Alignak external commands, set timestamp: True",
                "[alignak.module.web-services] Alignak Backend is not configured. Some module features will not be available.",
                "[alignak.module.web-services] Alignak Arbiter configuration: 127.0.0.1:7770",
                "[alignak.module.web-services] Alignak Arbiter polling period: 5",
                "[alignak.module.web-services] Alignak daemons get status period: 10",
                "[alignak.module.web-services] SSL is not enabled, this is not recommended. You should consider enabling SSL!",
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

    @pytest.mark.skipif(sys.version_info[:2] < (2, 7), reason="Not available for Python < 2.7")
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
        nb_errors = self._run_daemons_modules(cfg_folder, tmp_folder, cfg_modules, 10)

        # Search the WS module
        # module_pid = None
        # for proc in psutil.process_iter():
        #     if "module: web-services" in proc.name():
        #         print("Found WS module in the ps: %s (pid=%d)" % (proc.name(), proc.pid))
        #         module_pid = proc.pid
        # assert module_pid is not None

        self.kill_daemons()

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
                "[alignak.module] Give an instance of alignak_module_backend.arbiter for alias: backend_arbiter",
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
                "[alignak.module] Give an instance of alignak_module_backend.broker for alias: backend_broker",
                "[alignak.module.backend_broker] Number of processes used by backend client: 1",
                "[alignak.module.backend_broker] Alignak backend is not available for login. No backend connection, attempt: 1",
                "[alignak.module.backend_broker] Alignak backend connection is not available. Checking if livestate update is allowed is not possible.",
                "[alignak.modulesmanager] Trying to initialize module: backend_broker",
                "[alignak.daemon] I correctly loaded my modules: [backend_broker]",
            ],
            'scheduler': [
                "[alignak.modulesmanager] Importing Python module 'alignak_module_backend.scheduler' for backend_scheduler...",
                "[alignak.modulesmanager] Module properties: {'daemons': ['scheduler'], 'phases': ['running'], 'type': 'backend_scheduler', 'external': False}",
                "[alignak.modulesmanager] Imported 'alignak_module_backend.scheduler' for backend_scheduler",
                "[alignak.modulesmanager] Loaded Python module 'alignak_module_backend.scheduler' (backend_scheduler)",
                "[alignak.module] Give an instance of alignak_module_backend.scheduler for alias: backend_scheduler",
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
                        if "Alignak backend connection is not available. " not in line:
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
