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
        self.setup_with_file('cfg/alignak_full_run_realms/alignak.cfg')
        assert self.conf_is_correct

        self.procs = {}
        daemons_list = ['broker', 'broker-north', 'broker-south',
                        'poller', 'poller-north', 'poller-south',
                        'reactionner',
                        'receiver', 'receiver-north',
                        'scheduler', 'scheduler-north', 'scheduler-south',]

        print("Cleaning pid and log files...")
        for daemon in ['arbiter'] + daemons_list:
            if os.path.exists('/tmp/%s.pid' % daemon):
                os.remove('/tmp/%s.pid' % daemon)
                print("- removed /tmp/%s.pid" % daemon)
            if os.path.exists('/tmp/%s.log' % daemon):
                os.remove('/tmp/%s.log' % daemon)
                print("- removed /tmp/%s.log" % daemon)

        shutil.copy('./cfg/alignak_full_run_realms/dummy_command.sh', '/tmp/dummy_command.sh')

        print("Launching the daemons...")
        for daemon in daemons_list:
            alignak_daemon = "../alignak/bin/alignak_%s.py" % daemon.split('-')[0]

            args = [alignak_daemon, "-c", "./cfg/alignak_full_run_realms/daemons/%s.ini" % daemon]
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
                "-c", "cfg/alignak_full_run_realms/daemons/arbiter.ini",
                "-a", "cfg/alignak_full_run_realms/alignak.cfg"]
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
        for daemon in ['arbiter'] + daemons_list:
            assert os.path.exists('/tmp/%s.log' % daemon), '/tmp/%s.log does not exist!' % daemon
            daemon_errors = False
            print("-----\n%s log file\n-----\n" % daemon)
            with open('/tmp/%s.log' % daemon) as f:
                for line in f:
                    if 'WARNING' in line or daemon_errors:
                        print(line)
                    if 'ERROR' in line or 'CRITICAL' in line:
                        if not daemon_errors:
                            print(line[:-1])
                        daemon_errors = True
                        nb_errors += 1
        assert nb_errors == 0, "Error logs raised!"
        print("No error logs raised when daemons loaded the modules")

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
        # With this the pollers/schedulers will raise WARNING logs about the checks execution
        os.environ['TEST_LOG_ACTIONS'] = 'Yes'

        # Run deamons for 2 minutes
        self.run_and_check_alignak_daemons(120)

        # Expected WARNING logs from the daemons
        initgroups = 'initgroups'
        if sys.version_info < (2, 7):
            initgroups = 'setgroups'
        expected_logs = {
            'poller': [
                "[alignak.daemon] Cannot call the additional groups setting with %s (Operation not permitted)" % initgroups,
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 0'",
                "[alignak.action] Check for '/tmp/dummy_command.sh 0' exited with return code 0",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 0': 0, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh'",
                "[alignak.action] Check for '/tmp/dummy_command.sh' exited with return code 3",
                "[alignak.action] Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 1'",
                "[alignak.action] Check for '/tmp/dummy_command.sh 1' exited with return code 1",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 1': 1, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 2'",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 0 10'",
                "[alignak.action] Check for '/tmp/dummy_command.sh 2' exited with return code 2",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 2': 2, Hi, I'm the dummy check.",
                "[alignak.action] Check for '/tmp/dummy_command.sh 0 10' exited on timeout (5 s)",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh'",
                "[alignak.action] Check for '/tmp/dummy_command.sh' exited with return code 3",
                "[alignak.action] Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
            ],
            'poller-north': [
                "[alignak.daemon] Cannot call the additional groups setting with %s (Operation not permitted)" % initgroups,
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 0'",
                "[alignak.action] Check for '/tmp/dummy_command.sh 0' exited with return code 0",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 0': 0, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 1'",
                "[alignak.action] Check for '/tmp/dummy_command.sh 1' exited with return code 1",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 1': 1, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 2'",
                "[alignak.action] Check for '/tmp/dummy_command.sh 2' exited with return code 2",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 2': 2, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 0 10'",
                "[alignak.action] Check for '/tmp/dummy_command.sh 0 10' exited on timeout (5 s)",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh'",
                "[alignak.action] Check for '/tmp/dummy_command.sh' exited with return code 3",
                "[alignak.action] Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
            ],
            'poller-south': [
                "[alignak.daemon] Cannot call the additional groups setting with %s (Operation not permitted)" % initgroups,
                "[alignak.action] Launch command: '/tmp/dummy_command.sh'",
                "[alignak.action] Check for '/tmp/dummy_command.sh' exited with return code 3",
                "[alignak.action] Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 1'",
                "[alignak.action] Check for '/tmp/dummy_command.sh 1' exited with return code 1",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 1': 1, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 0'",
                "[alignak.action] Check for '/tmp/dummy_command.sh 0' exited with return code 0",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 0': 0, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 2'",
                "[alignak.action] Check for '/tmp/dummy_command.sh 2' exited with return code 2",
                "[alignak.action] Check result for '/tmp/dummy_command.sh 2': 2, Hi, I'm the dummy check.",
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 0 10'",
                "[alignak.action] Check for '/tmp/dummy_command.sh 0 10' exited on timeout (5 s)",
            ],
            'scheduler': [
                "[alignak.daemon] Cannot call the additional groups setting with %s (Operation not permitted)" % initgroups,
                "[alignak.scheduler] Timeout raised for '/tmp/dummy_command.sh 0 10' (check command for the service 'alignak-all-00/dummy_timeout'), check status code: 2, execution time: 5 seconds"
            ],
            'scheduler-north': [
                "[alignak.daemon] Cannot call the additional groups setting with %s (Operation not permitted)" % initgroups,
                "[alignak.scheduler] Timeout raised for '/tmp/dummy_command.sh 0 10' (check command for the service 'alignak-north-00/dummy_timeout'), check status code: 2, execution time: 5 seconds"
            ],
            'scheduler-south': [
                "[alignak.daemon] Cannot call the additional groups setting with %s (Operation not permitted)" % initgroups,
                "[alignak.scheduler] Timeout raised for '/tmp/dummy_command.sh 0 10' (check command for the service 'alignak-south-00/dummy_timeout'), check status code: 2, execution time: 5 seconds"
            ]
        }
        logs = {}

        for name in ['poller', 'poller-north', 'poller-south',
                     'scheduler', 'scheduler-north', 'scheduler-south']:
            assert os.path.exists('/tmp/%s.log' % name), '/tmp/%s.log does not exist!' % name
            logs[name] = []
            print("-----\n%s log file\n" % name)
            with open('/tmp/%s.log' % name) as f:
                for line in f:
                    # Catches only the WARNING logs
                    if 'WARNING' in line:
                        # ansi_escape.sub('', line)
                        line = line.split('WARNING: ')
                        line = line[1]
                        line = line.strip()
                        # Remove the leading ": "
                        logs[name].append(line)
                        print(">>> " + line)

            for log in expected_logs[name]:
                assert log in logs[name]

