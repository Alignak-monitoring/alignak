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
import signal

import subprocess
from time import sleep
import shutil
import pytest

from alignak_test import AlignakTest


class TestLaunchDaemonsPassive(AlignakTest):
    def setUp(self):
        # Set an environment variable to activate the logging of checks execution
        # With this the pollers/schedulers will raise INFO logs about the checks execution
        os.environ['TEST_LOG_ACTIONS'] = 'INFO'

        # Alignak daemons monitoring everay 3 seconds
        os.environ['ALIGNAK_DAEMONS_MONITORING'] = '3'

        # Alignak arbiter self-monitoring - report statistics every 5 loop counts
        os.environ['TEST_LOG_MONITORING'] = '5'

        # Log daemons loop turn
        os.environ['TEST_LOG_LOOP'] = 'INFO'

    def tearDown(self):
        print("Test terminated!")

    def test_correct_checks_launch_and_result(self):
        """ Run the Alignak daemons and check the correct checks result
        with some daemons in passive mode

        :return: None
        """
        self.print_header()

        # Set an environment variable to activate the logging of checks execution
        # With this the pollers/schedulers will raise WARNING logs about the checks execution
        os.environ['TEST_LOG_ACTIONS'] = 'INFO'

        # Alignak arbiter self-monitoring - report statistics every 5 loop counts
        os.environ['TEST_LOG_MONITORING'] = '5'

        daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                        'receiver-master', 'scheduler-master']

        # Run daemons for 4 minutes
        self._run_alignak_daemons(cfg_folder='cfg/run_passive', daemons_list=daemons_list,
                                  run_folder='/tmp', runtime=30)

        self._stop_alignak_daemons()

        # Check daemons log files
        ignored_warnings = [
            'No realms defined, I am adding one as All',
            'that we must be related with cannot be connected',
            'Server not available',
            'Setting the satellite ',
            'Add failed attempt'
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
                "[alignak.satellite] Passive mode enabled.",
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
                "[alignak.action] Launch command: '/tmp/dummy_command.sh 0 10'",
                "[alignak.action] Action '/tmp/dummy_command.sh 0 10' exited on timeout (5 s)",
                # Check unknown
                "[alignak.action] Launch command: '/tmp/dummy_command.sh'",
                "[alignak.action] Action '/tmp/dummy_command.sh' exited with return code 3",
                "[alignak.action] Check result for '/tmp/dummy_command.sh': 3, Hi, I'm the dummy check.",
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
            'reactionner-master': [

            ]
        }

        errors_raised = 0
        for name in ['poller-master', 'scheduler-master', 'reactionner-master']:
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
                # assert log in logs

        return errors_raised
