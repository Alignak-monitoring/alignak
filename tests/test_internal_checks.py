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
"""
This file test internal checks
"""

import os
import time
import json
import logging
import datetime
from pprint import pprint
from freezegun import freeze_time

from .alignak_test import AlignakTest
from alignak.log import ALIGNAK_LOGGER_NAME, CollectorHandler


class TestInternalChecks(AlignakTest):
    """
    This class test internal checks
    """
    def setUp(self):
        super(TestInternalChecks, self).setUp()
        os.environ['ALIGNAK_LOG_CHECKS'] = '1'

    def tearDown(self):
        del os.environ['ALIGNAK_LOG_CHECKS']

    def test_internal_checks(self):
        """ Test many internal checks

        :return: None
        """
        self._run_internal_checks(perf_data=False)

    def test_internal_checks_perf_data(self):
        """ Test many internal checks with some random performance data

        :return: None
        """
        self._run_internal_checks(perf_data=True)

    def _run_internal_checks(self, perf_data=False):
        """ Test many internal checks

        :return: None
        """
        # Set environment variables that define a [0 - N] random range for the performance data
        if perf_data:
            os.environ['ALIGNAK_INTERNAL_HOST_PERFDATA'] = '5'
            os.environ['ALIGNAK_INTERNAL_SERVICE_PERFDATA'] = '5'
        else:
            if 'ALIGNAK_INTERNAL_HOST_PERFDATA' in os.environ:
                del os.environ['ALIGNAK_INTERNAL_HOST_PERFDATA']
            if 'ALIGNAK_INTERNAL_SERVICE_PERFDATA' in os.environ:
                del os.environ['ALIGNAK_INTERNAL_SERVICE_PERFDATA']

        self.setup_with_file('cfg/cfg_internal_checks.cfg')
        assert self.conf_is_correct

        assert self._scheduler.pushed_conf.log_active_checks is True

        host = self._scheduler.hosts.find_by_name("host_6")
        assert host.check_interval == 5     # 5 minutes!

        assert host.state == 'UP'
        assert host.state_id == 0

        assert host.last_state == 'PENDING'
        assert host.last_state_id == 0
        assert host.last_state_change == 0
        assert host.last_state_update == 0

        assert host.last_hard_state == 'PENDING'
        assert host.last_hard_state_id == 0
        assert host.last_hard_state_change == 0

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2018, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime

            # 1527877800
            now = time.time()

            self.scheduler_loop(1)
            time.sleep(0.1)
            self.show_checks()

            print("Checks list:")
            checks = list(self._scheduler.checks.values())
            for check in checks:
                if check.command.startswith("/test"):
                    continue
                # pprint(check.__dict__)
                print("%s: %s" % (datetime.datetime.utcfromtimestamp(check.t_to_go).strftime('%Y-%m-%d %H:%M:%S'), check.command))
                assert check.creation_time == now
                assert check.t_to_go >= now
                assert check.t_to_go <= now + (5 * 60)

            print("-----\nChecks execution:")
            self.clear_logs()
            checks_count = len(checks)
            # Simulate checks for one quarter
            for second in range(0, 1200):
                # Time warp 1 second
                frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
                self.scheduler_loop(1)
                if (second % 300) == 0:
                    print("5 minutes later...")
            print("-----")

        print("Checks list:")
        checks = list(self._scheduler.checks.values())
        for check in checks:
            if check.command.startswith("/test"):
                continue
            print("Check: %s" % check)
            print("%s: %s - %s" % (datetime.datetime.utcfromtimestamp(check.t_to_go).strftime('%Y-%m-%d %H:%M:%S'), check.command, check.perf_data))

            if check.command.startswith('_internal') and check.status not in ['scheduled']:
                if perf_data:
                    assert check.perf_data != ''
                else:
                    assert check.perf_data == ''

        # The Alignak log contain checks log thanks to the ALIGNAK_LOG_CHECKS env variable!
        # self.show_logs()
        # self.show_events()

        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for handler in logger_.handlers:
            if not isinstance(handler, CollectorHandler):
                continue
            for log in handler.collector:
                if 'DEBUG:' in log:
                    continue

                if 'next check for ' in log:
                    continue

                # Always UP
                if 'Internal check: host_0 ' in log:
                    assert '--ALC-- Internal check: host_0 - _internal_host_check;0;I am always Up' in log
                    continue
                if 'check result for host_0,' in log:
                    assert '--ALC-- check result for host_0, exit: 0, output: I am always Up' in log
                    continue

                # Always UNREACHABLE
                if 'Internal check: host_1 ' in log:
                    assert '--ALC-- Internal check: host_1 - _internal_host_check;1;I am always Down' in log
                    continue
                if 'check result for host_1,' in log:
                    assert '--ALC-- check result for host_1, exit: 1, output: I am always Down' in log
                    continue

                # Always DOWN
                if 'Internal check: host_2 ' in log:
                    assert '--ALC-- Internal check: host_2 - _internal_host_check;2;I am always Down' in log
                    continue
                if 'check result for host_2,' in log:
                    assert '--ALC-- check result for host_2, exit: 2, output: I am always Down' in log
                    continue

                # Always UNKNOWN
                if 'Internal check: host_3 ' in log:
                    assert '--ALC-- Internal check: host_3 - _internal_host_check;3;I am always Unknown' in log
                    continue
                if 'check result for host_3,' in log:
                    assert '--ALC-- check result for host_3, exit: 3, output: I am always Unknown' in log
                    continue

                # Always UNREACHABLE
                if 'Internal check: host_4 ' in log:
                    assert '--ALC-- Internal check: host_4 - _internal_host_check;4;I am always Unreachable' in log
                    continue
                if 'check result for host_4,' in log:
                    assert '--ALC-- check result for host_4, exit: 4, output: I am always Unreachable' in log
                    continue

                # Output built by Alignak
                if 'Internal check: host_5 ' in log:
                    assert '--ALC-- Internal check: host_5 - _internal_host_check;0;' in log
                    continue
                if 'check result for host_5,' in log:
                    assert '--ALC-- check result for host_5, exit: 0, output: Host internal check result: 0' in log
                    continue

                # Random exit code
                if 'Internal check: host_6 ' in log:
                    assert '--ALC-- Internal check: host_6 - _internal_host_check;0,2;' in log
                    continue
                if 'check result for host_6,' in log:
                    assert \
                        ('--ALC-- check result for host_6, exit: 0, output: Host internal check result: 0' in log) or \
                        ('--ALC-- check result for host_6, exit: 1, output: Host internal check result: 1' in log) or \
                        ('--ALC-- check result for host_6, exit: 2, output: Host internal check result: 2' in log) or \
                        ('--ALC-- check result for host_6, exit: 3, output: Host internal check result: 3' in log)
                    continue
