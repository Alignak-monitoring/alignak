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
#

"""
This file test all cases of eventhandler
"""

import time
import pytest

from .alignak_test import AlignakTest

from alignak.misc.serialization import unserialize


class TestEventhandler(AlignakTest):
    """
    This class test the eventhandler
    """
    def setUp(self):
        super(TestEventhandler, self).setUp()

    def test_global_unknown_event_handler(self):
        """ Test global event handler unknown command

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_global_event_handlers_not_found.cfg')
        assert self.conf_is_correct is False
        self.show_configuration_logs()

    def test_global_event_handler(self):
        """ Test global event handler scenario 1:
        * check OK              OK HARD
        * check CRITICAL x4     CRITICAL SOFT x1 then CRITICAL HARD
        * check OK x2           OK HARD

        :return: None
        """
        self.setup_with_file('cfg/cfg_global_event_handlers.cfg')

        self._sched = self._scheduler

        host = self._sched.hosts.find_by_name("test_host_1")
        print(host.event_handler_enabled)
        assert host.event_handler_enabled is True
        print("host: %s" % host.event_handler)
        print("global: %s" % host.__class__.global_event_handler)
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._sched.services.find_srv_by_name_and_hostname(
            "test_host_1", "test_ok_0")
        assert svc.event_handler_enabled is True
        print("svc: %s" % svc.event_handler)
        print("global: %s" % svc.__class__.global_event_handler)
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
        self.assert_actions_match(0, 'test_global_service_eventhandler.pl CRITICAL SOFT', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(2)
        self.assert_actions_match(0, 'test_global_service_eventhandler.pl CRITICAL SOFT', 'command')
        self.assert_actions_match(1, 'test_global_service_eventhandler.pl CRITICAL HARD', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assert_actions_count(3)
        self.assert_actions_match(0, 'test_global_service_eventhandler.pl CRITICAL SOFT', 'command')
        self.assert_actions_match(1, 'test_global_service_eventhandler.pl CRITICAL HARD', 'command')
        self.assert_actions_match(2, 'test_global_service_eventhandler.pl OK HARD', 'command')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        # Do not change
        self.assert_actions_count(3)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.show_actions()
        self.assert_actions_count(4)
        self.assert_actions_match(0, 'test_global_service_eventhandler.pl CRITICAL SOFT', 'command')
        self.assert_actions_match(1, 'test_global_service_eventhandler.pl CRITICAL HARD', 'command')
        self.assert_actions_match(2, 'test_global_service_eventhandler.pl OK HARD', 'command')
        self.assert_actions_match(3, 'test_global_host_eventhandler.pl', 'command')

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)
        self.show_actions()
        self.assert_actions_count(5)
        self.assert_actions_match(0, 'test_global_service_eventhandler.pl CRITICAL SOFT', 'command')
        self.assert_actions_match(1, 'test_global_service_eventhandler.pl CRITICAL HARD', 'command')
        self.assert_actions_match(2, 'test_global_service_eventhandler.pl OK HARD', 'command')
        self.assert_actions_match(3, 'test_global_host_eventhandler.pl DOWN SOFT', 'command')
        self.assert_actions_match(4, 'test_global_host_eventhandler.pl UP SOFT', 'command')

        # Get my first broker link
        my_broker = [b for b in list(self._scheduler.my_daemon.brokers.values())][0]

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in sorted(list(my_broker.broks.values()), key=lambda x: x.creation_time):
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        print(monitoring_logs)
        expected_logs = [
            ('info', 'SERVICE ALERT: test_host_1;test_ok_0;OK;HARD;2;OK'),
            ('error', 'SERVICE ALERT: test_host_1;test_ok_0;CRITICAL;HARD;2;CRITICAL'),
            ('error', 'SERVICE EVENT HANDLER: test_host_1;test_ok_0;CRITICAL;SOFT;'
                       '1;global_service_eventhandler'),
            ('info', 'SERVICE EVENT HANDLER: test_host_1;test_ok_0;OK;HARD;'
                      '2;global_service_eventhandler'),
            ('error', 'SERVICE ALERT: test_host_1;test_ok_0;CRITICAL;SOFT;1;CRITICAL'),
            ('error', 'SERVICE EVENT HANDLER: test_host_1;test_ok_0;CRITICAL;HARD;'
                       '2;global_service_eventhandler'),
            ('error', 'HOST ALERT: test_host_1;DOWN;SOFT;1;DOWN'),
            ('error', 'HOST EVENT HANDLER: test_host_1;DOWN;SOFT;1;global_host_eventhandler'),
            ('info', 'HOST ALERT: test_host_1;UP;SOFT;2;UP'),
            ('info', 'HOST EVENT HANDLER: test_host_1;UP;SOFT;2;global_host_eventhandler')
        ]

        for log_level, log_message in expected_logs:
            print(log_message)
            assert (log_level, log_message) in monitoring_logs

    def test_ok_critical_ok(self):
        """ Test event handler scenario 1:
        * check OK              OK HARD
        * check CRITICAL x4     CRITICAL SOFT x1 then CRITICAL HARD
        * check OK x2           OK HARD

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
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
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
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
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
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
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
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
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
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
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
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
