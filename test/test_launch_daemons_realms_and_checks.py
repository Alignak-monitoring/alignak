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
import signal

import subprocess
from time import sleep
import shutil

from alignak_test import AlignakTest


class TestLaunchDaemonsRealms(AlignakTest):
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

    def tearDown(self):
        print("Test terminated!")

    def run_and_check_alignak_daemons(self, runtime=10):
        """ Run the Alignak daemons for a 3 realms configuration

        Let the daemons run for the number of seconds defined in the runtime parameter

        Check that the run daemons did not raised any ERROR log

        :return: None
        """
        self.print_header()

        # Load and test the configuration
        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cfg/run_realms')

        self.setup_with_file(cfg_folder + '/alignak.cfg')
        assert self.conf_is_correct

        self.procs = {}
        daemons_list = ['broker-master', 'broker-north', 'broker-south',
                        'poller-master', 'poller-north', 'poller-south',
                        'reactionner-master',
                        'receiver-master', 'receiver-north',
                        'scheduler-master', 'scheduler-north', 'scheduler-south',]

        print("Cleaning pid and log files...")
        for daemon in ['arbiter-master'] + daemons_list:
            if os.path.exists('/tmp/%s.pid' % daemon):
                os.remove('/tmp/%s.pid' % daemon)
                print("- removed /tmp/%s.pid" % daemon)
            if os.path.exists('/tmp/%s.log' % daemon):
                os.remove('/tmp/%s.log' % daemon)
                print("- removed /tmp/%s.log" % daemon)

        shutil.copy(cfg_folder + '/dummy_command.sh', '/tmp/dummy_command.sh')

        print("Launching the daemons...")
        for daemon in daemons_list:
            alignak_daemon = "../alignak/bin/alignak_%s.py" % daemon.split('-')[0]

            args = [alignak_daemon, "-n", daemon, "-e", cfg_folder + "/alignak.ini"]
            self.procs[daemon] = \
                subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
            print("- %s running (pid=%d)" % (name, self.procs[daemon].pid))

        # Let the daemons start ...
        sleep(1)

        print("Launching arbiter...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-n", "arbiter-master",
                "-e", cfg_folder + "/alignak.ini"]
        self.procs['arbiter'] = \
            subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("- %s launched (pid=%d)" % ('arbiter', self.procs['arbiter'].pid))

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
        assert ret is None, "Daemon %s not started!" % name
        print("- %s running (pid=%d)" % (name, self.procs[name].pid))

        # Let the arbiter build and dispatch its configuration
        # Let the schedulers get their configuration and run the first checks
        sleep(runtime)

        print("Get information from log files...")
        nb_errors = 0
        nb_warning = 0
        for daemon in ['arbiter-master'] + daemons_list:
            assert os.path.exists('/tmp/%s.log' % daemon), '/tmp/%s.log does not exist!' % daemon
            daemon_errors = False
            print("-----\n%s log file\n-----\n" % daemon)
            with open('/tmp/%s.log' % daemon) as f:
                for line in f:
                    if 'WARNING' in line or daemon_errors:
                        print(line[:-1])
                        if daemon == 'arbiter-master' \
                                and 'Cannot call the additional groups setting ' not in line:
                            nb_warning += 1
                    if 'ERROR' in line or 'CRITICAL' in line:
                        if not daemon_errors:
                            print(line[:-1])
                        daemon_errors = True
                        nb_errors += 1
        assert nb_errors == 0, "Error logs raised!"
        print("No error logs raised when daemons loaded the modules")

        assert nb_warning == 0, "Warning logs raised!"

        print("Stopping the daemons...")
        for name, proc in self.procs.items():
            print("Asking %s to end..." % name)
            os.kill(self.procs[name].pid, signal.SIGTERM)

    def test_daemons_realms(self):
        """ Running the Alignak daemons for a 3 realms configuration

        :return: None
        """
        self.print_header()

        self.run_and_check_alignak_daemons()

    def test_correct_checks_launch_and_result(self):
        """ Run the Alignak daemons and check the correct checks result

        :return: None
        """
        self.print_header()

        # Set an environment variable to activate the logging of checks execution
        # With this the pollers/schedulers will raise INFO logs about the checks execution
        os.environ['TEST_LOG_ACTIONS'] = 'INFO'

        # Run daemons for 2 minutes
        self.run_and_check_alignak_daemons(120)

        # Expected logs from the daemons
        expected_logs = {
            'poller-master': [
                # Check Ok
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 0'",
                "[alignak.action] Action '/tmp/dummy_command.sh 0' exited with return code 0",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 0': 0, Hi, I'm the dummy check.",
                # Check unknown
                "[alignak.action] Launch command: '/tmp/dummy_command.sh'",
                "[alignak.action] Action '/tmp/dummy_command.sh' exited with return code 3",
                "[alignak.action] Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
                # Check warning
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 1'",
                "[alignak.action] Action '/tmp/dummy_command.sh 1' exited with return code 1",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 1': 1, Hi, I'm the dummy check.",
                # Check critical
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 2'",
                "[alignak.action] Action '/tmp/dummy_command.sh 2' exited with return code 2",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 2': 2, Hi, I'm the dummy check.",
                # Check timeout
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 0 12'",
                "[alignak.action] Action '/tmp/dummy_command.sh 0 12' exited on timeout (5 s)",
                # Check unknown
                "[alignak.action] Launch command: '/tmp/dummy_command.sh'",
                "[alignak.action] Action '/tmp/dummy_command.sh' exited with return code 3",
                "[alignak.action] Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
            ],
            'poller-north': [
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 0'",
                "[alignak.action] Action '/tmp/dummy_command.sh 0' exited with return code 0",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 0': 0, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 1'",
                "[alignak.action] Action '/tmp/dummy_command.sh 1' exited with return code 1",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 1': 1, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 2'",
                "[alignak.action] Action '/tmp/dummy_command.sh 2' exited with return code 2",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 2': 2, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 0 10'",
                "[alignak.action] Action '/tmp/dummy_command.sh 0 10' exited on timeout (5 s)",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh'",
                "[alignak.action] Action '/tmp/dummy_command.sh' exited with return code 3",
                "[alignak.action] Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
            ],
            'poller-south': [
                "[alignak.action] Launch command: '/tmp/dummy_command.sh'",
                "[alignak.action] Action '/tmp/dummy_command.sh' exited with return code 3",
                "[alignak.action] Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 1'",
                "[alignak.action] Action '/tmp/dummy_command.sh 1' exited with return code 1",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 1': 1, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 0'",
                "[alignak.action] Action '/tmp/dummy_command.sh 0' exited with return code 0",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 0': 0, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 2'",
                "[alignak.action] Action '/tmp/dummy_command.sh 2' exited with return code 2",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 2': 2, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 0 10'",
                "[alignak.action] Action '/tmp/dummy_command.sh 0 10' exited on timeout (5 s)",
            ],
            'scheduler-master': [
                # Internal host check
                # "[alignak.objects.schedulingitem] Set host localhost as UP (internal check)",
                # Check ok
                "[alignak.objects.schedulingitem] Got check result: 0 for 'alignak-all-00/dummy_ok'",
                # Check warning
                "[alignak.objects.schedulingitem] Got check result: 1 for 'alignak-all-00/dummy_warning'",
                # Check critical
                "[alignak.objects.schedulingitem] Got check result: 2 for 'alignak-all-00/dummy_critical'",
                # Check unknown
                "[alignak.objects.schedulingitem] Got check result: 3 for 'alignak-all-00/dummy_unknown'",
                # Check time
                "[alignak.objects.schedulingitem] Got check result: 2 for 'alignak-all-00/dummy_timeout'",
                # Echo internal command
                "[alignak.objects.schedulingitem] Echo the current state (OK - 0) for alignak-all-00/dummy_echo"
            ],
            'scheduler-north': [
                "[alignak.objects.schedulingitem] Got check result: 0 for 'alignak-north-00/dummy_ok'",
                "[alignak.objects.schedulingitem] Got check result: 1 for 'alignak-north-00/dummy_warning'",
                "[alignak.objects.schedulingitem] Got check result: 2 for 'alignak-north-00/dummy_critical'",
                "[alignak.objects.schedulingitem] Got check result: 3 for 'alignak-north-00/dummy_unknown'",
                "[alignak.objects.schedulingitem] Got check result: 2 for 'alignak-north-00/dummy_timeout'",
                "[alignak.objects.schedulingitem] Echo the current state (OK - 0) for alignak-north-00/dummy_echo"
            ],
            'scheduler-south': [
                "[alignak.objects.schedulingitem] Got check result: 0 for 'alignak-south-00/dummy_ok'",
                "[alignak.objects.schedulingitem] Got check result: 1 for 'alignak-south-00/dummy_warning'",
                "[alignak.objects.schedulingitem] Got check result: 2 for 'alignak-south-00/dummy_critical'",
                "[alignak.objects.schedulingitem] Got check result: 3 for 'alignak-south-00/dummy_unknown'",
                "[alignak.objects.schedulingitem] Got check result: 2 for 'alignak-south-00/dummy_timeout'",
                "[alignak.objects.schedulingitem] Echo the current state (OK - 0) for alignak-south-00/dummy_echo"
            ]
        }

        errors_raised = 0
        for name in ['poller-master', 'poller-north', 'poller-south',
                     'scheduler-master', 'scheduler-north', 'scheduler-south']:
            assert os.path.exists('/tmp/%s.log' % name), '/tmp/%s.log does not exist!' % name
            print("-----\n%s log file\n" % name)
            with open('/tmp/%s.log' % name) as f:
                lines = f.readlines()
                logs = []
                for line in lines:
                    # Catches WARNING and ERROR logs
                    if 'WARNING:' in line:
                        print("line: %s" % line)
                    if 'ERROR:' in line or 'CRITICAL:' in line:
                        errors_raised += 1
                        print("error: %s" % line)
                    # Catches INFO logs
                    if 'INFO:' in line:
                        line = line.split('INFO: ')
                        line = line[1]
                        line = line.strip()
                        print("line: %s" % line)
                        logs.append(line)

            for log in expected_logs[name]:
                print("Last checked log %s: %s" % (name, log))
                assert log in logs

