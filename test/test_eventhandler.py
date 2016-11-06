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
#

"""
This file test all cases of eventhandler
"""

import time

from alignak_test import AlignakTest


class TestEventhandler(AlignakTest):
    """
    This class test the eventhandler
    """

    def test_ok_critical_ok(self):
        """ Test event handler scenario 1:
        * check OK              OK HARD
        * check CRITICAL x4     CRITICAL SOFT x1 then CRITICAL HARD
        * check OK x2           OK HARD

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.enable_notifications = False
        svc.notification_interval = 0

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'test_eventhandler.pl CRITICAL SOFT', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(2)
        self.assert_actions_match(0, 'test_eventhandler.pl CRITICAL SOFT', 'command')
        self.assert_actions_match(1, 'test_eventhandler.pl CRITICAL HARD', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(3)
        self.assert_actions_match(0, 'test_eventhandler.pl CRITICAL SOFT', 'command')
        self.assert_actions_match(1, 'test_eventhandler.pl CRITICAL HARD', 'command')
        self.assert_actions_match(2, 'test_eventhandler.pl OK HARD', 'command')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(3)

    def test_ok_warning_ok(self):
        """ Test event handler scenario 2:
        * check OK              OK HARD
        * check WARNING x4      WARNING SOFT x1 then WARNING HARD
        * check OK x2           OK HARD

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.enable_notifications = False
        svc.notification_interval = 0

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'test_eventhandler.pl WARNING SOFT', 'command')

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assert_actions_count(2)
        self.assert_actions_match(0, 'test_eventhandler.pl WARNING SOFT', 'command')
        self.assert_actions_match(1, 'test_eventhandler.pl WARNING HARD', 'command')

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(3)
        self.assert_actions_match(0, 'test_eventhandler.pl WARNING SOFT', 'command')
        self.assert_actions_match(1, 'test_eventhandler.pl WARNING HARD', 'command')
        self.assert_actions_match(2, 'test_eventhandler.pl OK HARD', 'command')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(3)

    def test_ok_warning_critical_ok(self):
        """ Test event handler scenario 3:
        * check OK              OK HARD
        * check WARNING x4      WARNING SOFT x1 then WARNING HARD
        * check CRITICAL x4     CRITICAL HARD
        * check OK x2           OK HARD

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.enable_notifications = False
        svc.notification_interval = 0

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "SOFT" == svc.state_type
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'test_eventhandler.pl WARNING SOFT', 'command')

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        self.assert_actions_count(2)
        self.assert_actions_match(0, 'test_eventhandler.pl WARNING SOFT', 'command')
        self.assert_actions_match(1, 'test_eventhandler.pl WARNING HARD', 'command')

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        self.assert_actions_count(3)
        self.assert_actions_match(0, 'test_eventhandler.pl WARNING SOFT', 'command')
        self.assert_actions_match(1, 'test_eventhandler.pl WARNING HARD', 'command')
        self.assert_actions_match(2, 'test_eventhandler.pl CRITICAL HARD', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(3)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(3)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(3)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        self.assert_actions_count(4)
        self.assert_actions_match(0, 'test_eventhandler.pl WARNING SOFT', 'command')
        self.assert_actions_match(1, 'test_eventhandler.pl WARNING HARD', 'command')
        self.assert_actions_match(2, 'test_eventhandler.pl CRITICAL HARD', 'command')
        self.assert_actions_match(3, 'test_eventhandler.pl OK HARD', 'command')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(4)

    def test_ok_warning_s_critical_h_ok(self):
        """ Test event handler scenario 4:
        * check OK              OK HARD
        * check WARNING         WARNING SOFT
        * check CRITICAL x2     CRITICAL HARD
        * check OK x2           OK HARD

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.enable_notifications = False
        svc.notification_interval = 0

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "SOFT" == svc.state_type
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'test_eventhandler.pl WARNING SOFT', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        self.assert_actions_count(2)
        self.assert_actions_match(0, 'test_eventhandler.pl WARNING SOFT', 'command')
        self.assert_actions_match(1, 'test_eventhandler.pl CRITICAL HARD', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        self.assert_actions_count(3)
        self.assert_actions_match(0, 'test_eventhandler.pl WARNING SOFT', 'command')
        self.assert_actions_match(1, 'test_eventhandler.pl CRITICAL HARD', 'command')
        self.assert_actions_match(2, 'test_eventhandler.pl OK HARD', 'command')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(3)

    def test_ok_critical_s_warning_h_ok(self):
        """ Test event handler scenario 5:
        * check OK              OK HARD
        * check CRITICAL        CRITICAL SOFT
        * check WARNING x2      WARNING HARD
        * check OK x2           OK HARD

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.enable_notifications = False
        svc.notification_interval = 0

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "SOFT" == svc.state_type
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'test_eventhandler.pl CRITICAL SOFT', 'command')

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        self.assert_actions_count(2)
        self.assert_actions_match(0, 'test_eventhandler.pl CRITICAL SOFT', 'command')
        self.assert_actions_match(1, 'test_eventhandler.pl WARNING HARD', 'command')

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        self.assert_actions_count(3)
        self.assert_actions_match(0, 'test_eventhandler.pl CRITICAL SOFT', 'command')
        self.assert_actions_match(1, 'test_eventhandler.pl WARNING HARD', 'command')
        self.assert_actions_match(2, 'test_eventhandler.pl OK HARD', 'command')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(3)

    def test_ok_critical_s_warning_h_warning_h_ok(self):
        """ Test event handler scenario 6:
        * check OK              OK HARD
        * check CRITICAL        CRITICAL SOFT
        * check WARNING x2      WARNING HARD
        * check CRITICAL        CRITICAL HARD
        * check OK x2           OK HARD

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.enable_notifications = False
        svc.notification_interval = 0

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "SOFT" == svc.state_type
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'test_eventhandler.pl CRITICAL SOFT', 'command')

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        self.assert_actions_count(2)
        self.assert_actions_match(0, 'test_eventhandler.pl CRITICAL SOFT', 'command')
        self.assert_actions_match(1, 'test_eventhandler.pl WARNING HARD', 'command')

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        self.assert_actions_count(3)
        self.assert_actions_match(0, 'test_eventhandler.pl CRITICAL SOFT', 'command')
        self.assert_actions_match(1, 'test_eventhandler.pl WARNING HARD', 'command')
        self.assert_actions_match(2, 'test_eventhandler.pl CRITICAL HARD', 'command')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        self.assert_actions_count(4)
        self.assert_actions_match(0, 'test_eventhandler.pl CRITICAL SOFT', 'command')
        self.assert_actions_match(1, 'test_eventhandler.pl WARNING HARD', 'command')
        self.assert_actions_match(2, 'test_eventhandler.pl CRITICAL HARD', 'command')
        self.assert_actions_match(3, 'test_eventhandler.pl OK HARD', 'command')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(4)
