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
import signal

import pytest

import subprocess
from time import sleep
import shutil

from alignak_test import AlignakTest


class TestLaunchDaemonsRealms(AlignakTest):
    def setUp(self):
        super(TestLaunchDaemonsRealms, self).setUp()

        # Set an environment variable to activate the logging of checks execution
        # With this the pollers/schedulers will raise INFO logs about the checks execution
        os.environ['TEST_LOG_ACTIONS'] = 'WARNING'

        # Set an environment variable to change the default period of activity log (every 60 loops)
        os.environ['ALIGNAK_ACTIVITY_LOG'] = '60'

        # Alignak daemons monitoring everay 3 seconds
        os.environ['ALIGNAK_DAEMON_MONITORING'] = '3'

        # Alignak arbiter self-monitoring - report statistics every 5 loop counts
        os.environ['ALIGNAK_SYSTEM_MONITORING'] = '5'

        # Log daemons loop turn
        os.environ['TEST_LOG_LOOP'] = 'INFO'

    def tearDown(self):
        print("Test terminated!")

    def test_daemons_realms(self):
        """ Running the Alignak daemons for a 3 realms configuration - several daemons
        for the realms

        :return: None
        """
        daemons_list = ['broker-master', 'broker-north', 'broker-south',
                        'poller-master', 'poller-north', 'poller-south',
                        'reactionner-master',
                        'receiver-master', 'receiver-north',
                        'scheduler-master', 'scheduler-north', 'scheduler-south',]

        self._run_alignak_daemons(cfg_folder='cfg/run_realms',
                                  daemons_list=daemons_list,
                                  run_folder='/tmp', runtime=30)

        self._stop_alignak_daemons(arbiter_only=True)

        # Check daemons log files
        ignored_warnings = [
            'Timeout raised for ',
            'spent too much time:',
            # todo: Temporary: because of unordered daemon stop !
            'that we must be related with cannot be connected',
            'Exception: Server not available',
            'Setting the satellite ',
            'Add failed attempt',
            'Launch command',
            'Check result',
            'Performance data',
            'Action',
            'Got check result',
            'Echo the current state',
            'Set host',
            'did not stopped, trying to kill'
        ]
        ignored_errors = [
        ]
        (errors_raised, warnings_raised) = \
            self._check_daemons_log_for_errors(daemons_list,
                                               ignored_warnings=ignored_warnings,
                                               ignored_errors=ignored_errors)

        assert errors_raised == 0, "Error logs raised!"
        print("No unexpected error logs raised by the daemons")

        assert warnings_raised == 0, "Warning logs raised!"
        print("No unexpected warning logs raised by the daemons")

    def test_daemons_realms_2(self):
        """ Running the Alignak daemons for a 3 realms configuration - only some daemons
        that manage sub realms

        :return: None
        """
        daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                        'receiver-master', 'scheduler-master']

        self._run_alignak_daemons(cfg_folder='cfg/run_realms_manage_sub_realms',
                                  daemons_list=daemons_list,
                                  run_folder='/tmp', runtime=30)

        self._stop_alignak_daemons()

        # Check daemons log files
        ignored_warnings = [
            'Timeout raised for ',
            'spent too much time:',
            # todo: Temporary: because of unordered daemon stop !
            'that we must be related with cannot be connected',
            'Exception: Server not available',
            'Setting the satellite ',
            'Add failed attempt',
            'Launch command',
            'Check result',
            'Performance data',
            'Action',
            'Got check result',
            'Echo the current state',
            'Set host',
            'did not stopped, trying to kill'
        ]
        ignored_errors = [
        ]
        (errors_raised, warnings_raised) = \
            self._check_daemons_log_for_errors(daemons_list,
                                               ignored_warnings=ignored_warnings,
                                               ignored_errors=ignored_errors)

        assert errors_raised == 0, "Error logs raised!"
        print("No unexpected error logs raised by the daemons")

        assert warnings_raised == 0, "Warning logs raised!"
        print("No unexpected warning logs raised by the daemons")

    def test_correct_checks_launch_and_result(self):
        """ Run the Alignak daemons and check the correct checks result

        :return: None
        """
        daemons_list = ['broker-master', 'broker-north', 'broker-south',
                        'poller-master', 'poller-north', 'poller-south',
                        'reactionner-master',
                        'receiver-master', 'receiver-north',
                        'scheduler-master', 'scheduler-north', 'scheduler-south',]

        # Run daemons for 4 minutes
        self._run_alignak_daemons(cfg_folder='cfg/run_realms',
                                  daemons_list=daemons_list,
                                  run_folder='/tmp', runtime=240)

        self._stop_alignak_daemons()

        # Check daemons log files
        ignored_warnings = [
            # todo: Temporary: because of unordered daemon stop !
            'that we must be related with cannot be connected',
            'Exception: Server not available',
            'Setting the satellite ',
            'Add failed attempt',
            # Action execution log
            'Timeout raised for ',
            'spent too much time:',
            'Launch command',
            'Check result',
            'Performance data',
            'Action',
            'Got check result',
            'Echo the current state',
            'Set host',
            # Sometimes not killed during the test because of SIGTERM
            'did not stopped, trying to kill'
        ]
        ignored_errors = [
        ]
        (errors_raised, warnings_raised) = \
            self._check_daemons_log_for_errors(daemons_list,
                                               ignored_warnings=ignored_warnings,
                                               ignored_errors=ignored_errors)

        assert errors_raised == 0, "Error logs raised!"
        print("No unexpected error logs raised by the daemons")

        assert warnings_raised == 0, "Warning logs raised!"
        print("No unexpected warning logs raised by the daemons")

        # Expected logs from the daemons
        expected_logs = {
            'poller-master': [
                # Check Ok
                "Launch command: '/tmp/dummy_command.sh 0'",
                "Action '/tmp/dummy_command.sh 0' exited with return code 0",
                "Check result for '/tmp/dummy_command.sh 0': 0, Hi, I'm the dummy check.",
                # Check unknown
                "Launch command: '/tmp/dummy_command.sh'",
                "Action '/tmp/dummy_command.sh' exited with return code 3",
                "Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
                # Check warning
                "Launch command: '/tmp/dummy_command.sh 1'",
                "Action '/tmp/dummy_command.sh 1' exited with return code 1",
                "Check result for '/tmp/dummy_command.sh 1': 1, Hi, I'm the dummy check.",
                # Check critical
                "Launch command: '/tmp/dummy_command.sh 2'",
                "Action '/tmp/dummy_command.sh 2' exited with return code 2",
                "Check result for '/tmp/dummy_command.sh 2': 2, Hi, I'm the dummy check.",
                # Check timeout
                "Launch command: '/tmp/dummy_command.sh 0 12'",
                "Action '/tmp/dummy_command.sh 0 12' exited on timeout (5 s)",
                # Check unknown
                "Launch command: '/tmp/dummy_command.sh'",
                "Action '/tmp/dummy_command.sh' exited with return code 3",
                "Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
            ],
            'poller-north': [
                "Launch command: '/tmp/dummy_command.sh 0'",
                "Action '/tmp/dummy_command.sh 0' exited with return code 0",
                "Check result for '/tmp/dummy_command.sh 0': 0, Hi, I'm the dummy check.",
                "Launch command: '/tmp/dummy_command.sh 1'",
                "Action '/tmp/dummy_command.sh 1' exited with return code 1",
                "Check result for '/tmp/dummy_command.sh 1': 1, Hi, I'm the dummy check.",
                "Launch command: '/tmp/dummy_command.sh 2'",
                "Action '/tmp/dummy_command.sh 2' exited with return code 2",
                "Check result for '/tmp/dummy_command.sh 2': 2, Hi, I'm the dummy check.",
                "Launch command: '/tmp/dummy_command.sh 0 10'",
                "Action '/tmp/dummy_command.sh 0 10' exited on timeout (5 s)",
                "Launch command: '/tmp/dummy_command.sh'",
                "Action '/tmp/dummy_command.sh' exited with return code 3",
                "Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
            ],
            'poller-south': [
                "Launch command: '/tmp/dummy_command.sh'",
                "Action '/tmp/dummy_command.sh' exited with return code 3",
                "Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
                "Launch command: '/tmp/dummy_command.sh 1'",
                "Action '/tmp/dummy_command.sh 1' exited with return code 1",
                "Check result for '/tmp/dummy_command.sh 1': 1, Hi, I'm the dummy check.",
                "Launch command: '/tmp/dummy_command.sh 0'",
                "Action '/tmp/dummy_command.sh 0' exited with return code 0",
                "Check result for '/tmp/dummy_command.sh 0': 0, Hi, I'm the dummy check.",
                "Launch command: '/tmp/dummy_command.sh 2'",
                "Action '/tmp/dummy_command.sh 2' exited with return code 2",
                "Check result for '/tmp/dummy_command.sh 2': 2, Hi, I'm the dummy check.",
                "Launch command: '/tmp/dummy_command.sh 0 10'",
                "Action '/tmp/dummy_command.sh 0 10' exited on timeout (5 s)",
            ],
            'scheduler-master': [
                # Internal host check
                # "Set host localhost as UP (internal check)",
                # Check ok
                "Got check result: 0 for 'alignak-all-00/dummy_ok'",
                # Check warning
                "Got check result: 1 for 'alignak-all-00/dummy_warning'",
                # Check critical
                "Got check result: 2 for 'alignak-all-00/dummy_critical'",
                # Check unknown
                "Got check result: 3 for 'alignak-all-00/dummy_unknown'",
                # Check time
                "Got check result: 2 for 'alignak-all-00/dummy_timeout'",
                # Echo internal command
                "Echo the current state (OK - 0) for alignak-all-00/dummy_echo"
            ],
            'scheduler-north': [
                "Got check result: 0 for 'alignak-north-00/dummy_ok'",
                "Got check result: 1 for 'alignak-north-00/dummy_warning'",
                "Got check result: 2 for 'alignak-north-00/dummy_critical'",
                "Got check result: 3 for 'alignak-north-00/dummy_unknown'",
                "Got check result: 2 for 'alignak-north-00/dummy_timeout'",
                "Echo the current state (OK - 0) for alignak-north-00/dummy_echo"
            ],
            'scheduler-south': [
                "Got check result: 0 for 'alignak-south-00/dummy_ok'",
                "Got check result: 1 for 'alignak-south-00/dummy_warning'",
                "Got check result: 2 for 'alignak-south-00/dummy_critical'",
                "Got check result: 3 for 'alignak-south-00/dummy_unknown'",
                "Got check result: 2 for 'alignak-south-00/dummy_timeout'",
                "Echo the current state (OK - 0) for alignak-south-00/dummy_echo"
            ]
        }

        errors_raised = 0
        travis_run = 'TRAVIS' in os.environ
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
                        # Catch warning for actions execution
                        line = line.split('WARNING: ')
                        line = line[1]
                        line = line.strip()
                        line = line.split('] ')
                        try:
                            line = line[1]
                            line = line.strip()
                            if not travis_run:
                                print("-ok-: %s" % line)
                        except IndexError:
                            if not travis_run:
                                print("***line: %s" % line)
                        logs.append(line)
                    if 'ERROR:' in line or 'CRITICAL:' in line:
                        errors_raised += 1
                        print("-KO-%d: %s" % (errors_raised, line))
                    # Catches INFO logs
                    if 'INFO:' in line:
                        if not travis_run:
                            print("line: %s" % line)

            for log in expected_logs[name]:
                print("Last checked log %s: %s" % (name, log))
                assert log in logs

    def test_correct_checks_launch_and_result_passive(self):
        """ Run the Alignak daemons and check the correct checks result
        with some daemons in passive mode

        :return: None
        """
        daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                        'receiver-master', 'scheduler-master']

        # Run daemons for 4 minutes
        self._run_alignak_daemons(cfg_folder='cfg/run_passive',
                                  daemons_list=daemons_list,
                                  run_folder='/tmp', runtime=240)

        self._stop_alignak_daemons()

        # Check daemons log files
        ignored_warnings = [
            'No realms defined, I am adding one as All',
            # todo: Temporary: because of unordered daemon stop !
            'that we must be related with cannot be connected',
            'Exception: Server not available',
            'Setting the satellite ',
            'Add failed attempt',
            # Action execution log
            'Timeout raised for ',
            'spent too much time:',
            'Launch command',
            'Check result',
            'Performance data',
            'Action',
            'Got check result',
            'Echo the current state',
            'Set host',
            # Sometimes not killed during the test because of SIGTERM
            'did not stopped, trying to kill'
        ]
        ignored_errors = [
            # 'Error on backend login: ',
            # 'Configured user account is not allowed for this module'
        ]
        (errors_raised, warnings_raised) = \
            self._check_daemons_log_for_errors(daemons_list, ignored_warnings=ignored_warnings,
                                               ignored_errors=ignored_errors)

        assert errors_raised == 0, "Error logs raised!"
        print("No unexpected error logs raised by the daemons")

        assert warnings_raised == 0, "Warning logs raised!"
        print("No unexpected warning logs raised by the daemons")

        # Expected logs from the daemons
        expected_logs = {
            'poller-master': [
                # Check Ok
                "Launch command: '/tmp/dummy_command.sh 0'",
                "Action '/tmp/dummy_command.sh 0' exited with return code 0",
                "Check result for '/tmp/dummy_command.sh 0': 0, Hi, I'm the dummy check.",
                # Check unknown
                "Launch command: '/tmp/dummy_command.sh'",
                "Action '/tmp/dummy_command.sh' exited with return code 3",
                "Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
                # Check warning
                "Launch command: '/tmp/dummy_command.sh 1'",
                "Action '/tmp/dummy_command.sh 1' exited with return code 1",
                "Check result for '/tmp/dummy_command.sh 1': 1, Hi, I'm the dummy check.",
                # Check critical
                "Launch command: '/tmp/dummy_command.sh 2'",
                "Action '/tmp/dummy_command.sh 2' exited with return code 2",
                "Check result for '/tmp/dummy_command.sh 2': 2, Hi, I'm the dummy check.",
                # Check timeout
                "Launch command: '/tmp/dummy_command.sh 0 10'",
                "Action '/tmp/dummy_command.sh 0 10' exited on timeout (5 s)",
                # Check unknown
                "Launch command: '/tmp/dummy_command.sh'",
                "Action '/tmp/dummy_command.sh' exited with return code 3",
                "Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
            ],
            'scheduler-master': [
                # Internal host check
                # "[alignak.objects.schedulingitem] Set host localhost as UP (internal check)",
                # Check ok
                "Got check result: 0 for 'alignak-all-00/dummy_ok'",
                # Check warning
                "Got check result: 1 for 'alignak-all-00/dummy_warning'",
                # Check critical
                "Got check result: 2 for 'alignak-all-00/dummy_critical'",
                # Check unknown
                "Got check result: 3 for 'alignak-all-00/dummy_unknown'",
                # Check time
                "Got check result: 2 for 'alignak-all-00/dummy_timeout'",
                # Echo internal command
                "Echo the current state (OK - 0) for alignak-all-00/dummy_echo"
            ],
            'reactionner-master': [

            ]
        }

        errors_raised = 0
        travis_run = 'TRAVIS' in os.environ
        for name in ['poller-master', 'scheduler-master']:
            assert os.path.exists('/tmp/%s.log' % name), '/tmp/%s.log does not exist!' % name
            print("-----\n%s log file\n" % name)
            with open('/tmp/%s.log' % name) as f:
                lines = f.readlines()
                logs = []
                for line in lines:
                    # Catches WARNING and ERROR logs
                    if 'WARNING:' in line:
                        # Catch warning for actions execution
                        line = line.split('WARNING: ')
                        line = line[1]
                        line = line.strip()
                        line = line.split('] ')
                        try:
                            line = line[1]
                            line = line.strip()
                            if not travis_run:
                                print("-ok-: %s" % line)
                        except IndexError:
                            if not travis_run:
                                print("***line: %s" % line)
                        logs.append(line)
                    if 'ERROR:' in line or 'CRITICAL:' in line:
                        errors_raised += 1
                        print("-KO-%d: %s" % (errors_raised, line))
                    # Catches INFO logs
                    if 'INFO:' in line:
                        if not travis_run:
                            print("    : %s" % line)

            for log in expected_logs[name]:
                print("Last checked log %s: %s" % (name, log))
                assert log in logs
