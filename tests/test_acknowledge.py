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
This file test acknowledge.
The acknowledge notifications are tested in test_notifications
"""

import time
from .alignak_test import AlignakTest


class TestAcknowledges(AlignakTest):
    """
    This class test acknowledge
    """
    def setUp(self):
        super(TestAcknowledges, self).setUp()
        self.setup_with_file('cfg/cfg_default.cfg',
                             dispatching=True)

    def test_ack_host_sticky_ds_dh(self):
        """
        Test host acknowledge with sticky when Down soft -> Down hard -> up

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert not host.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host.state
        assert "SOFT" == host.state_type

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM;{1};{2};{3};{4};{5};{6}\n".\
            format(int(now), host.host_name, 2, 0, 1, 'dark vador', 'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host.state
        assert "SOFT" == host.state_type
        assert host.problem_has_been_acknowledged

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host.state
        assert "HARD" == host.state_type
        assert host.problem_has_been_acknowledged

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)
        assert "UP" == host.state
        assert "HARD" == host.state_type
        assert not host.problem_has_been_acknowledged

    def test_ack_host_sticky_us_uh_dh(self):
        """
        Test host acknowledge with sticky when Unreachable soft -> Unreachable hard -> Down hard
        -> up

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.notifications_enabled = False

        host_router = self._scheduler.hosts.find_by_name("test_router_0")
        host_router.checks_in_progress = []
        host_router.event_handler_enabled = False
        host_router.notifications_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [host_router, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert "UP" == host_router.state
        assert "HARD" == host_router.state_type
        assert "UP" == host.state
        assert "HARD" == host.state_type
        assert not host.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "SOFT" == host_router.state_type
        # Unchanged
        assert "UP" == host.state
        assert "HARD" == host.state_type

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "SOFT" == host_router.state_type
        # Unchanged
        assert "UP" == host.state
        assert "HARD" == host.state_type

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "HARD" == host_router.state_type
        # Goes unreachable hard
        assert "UNREACHABLE" == host.state
        assert "HARD" == host.state_type

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "HARD" == host_router.state_type
        # Unchanged
        assert "UNREACHABLE" == host.state
        assert "SOFT" == host.state_type

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM;{1};{2};{3};{4};{5};{6}\n". \
            format(int(now), host.host_name, 2, 0, 1, 'dark vador', 'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "HARD" == host_router.state_type
        assert "UNREACHABLE" == host.state
        assert "SOFT" == host.state_type
        assert host.problem_has_been_acknowledged

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "HARD" == host_router.state_type
        assert "UNREACHABLE" == host.state
        assert "HARD" == host.state_type
        assert host.problem_has_been_acknowledged

        self.scheduler_loop(1, [[host_router, 0, 'UP']])
        time.sleep(0.1)
        assert "UP" == host_router.state
        assert "HARD" == host_router.state_type
        assert "UNREACHABLE" == host.state
        assert "HARD" == host.state_type
        assert host.problem_has_been_acknowledged

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 0, 'UP']])
        time.sleep(0.1)
        assert "UP" == host_router.state
        assert "HARD" == host_router.state_type
        assert "DOWN" == host.state
        assert "HARD" == host.state_type
        assert host.problem_has_been_acknowledged

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)
        assert "UP" == host.state
        assert "HARD" == host.state_type
        assert not host.problem_has_been_acknowledged

    def test_ack_host_nosticky_ds_dh(self):
        """
        Test host acknowledge with no sticky when Down soft -> Down hard -> up

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert not host.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host.state
        assert "SOFT" == host.state_type

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM;{1};{2};{3};{4};{5};{6}\n". \
            format(int(now), host.host_name, 1, 0, 1, 'dark vador', 'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host.state
        assert "SOFT" == host.state_type
        assert host.problem_has_been_acknowledged

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host.state
        assert "HARD" == host.state_type
        assert host.problem_has_been_acknowledged

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)
        assert "UP" == host.state
        assert "HARD" == host.state_type
        assert not host.problem_has_been_acknowledged

    def test_ack_host_nosticky_us_uh_dh(self):
        """
        Test host acknowledge with no sticky when Unreachable soft -> Unreachable hard -> Down hard
        -> up

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.notifications_enabled = False

        host_router = self._scheduler.hosts.find_by_name("test_router_0")
        host_router.checks_in_progress = []
        host_router.event_handler_enabled = False
        host_router.notifications_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [host_router, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert "UP" == host_router.state
        assert "HARD" == host_router.state_type
        assert "UP" == host.state
        assert "HARD" == host.state_type
        assert not host.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "SOFT" == host_router.state_type
        # Unchanged
        assert "UP" == host.state
        assert "HARD" == host.state_type

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "SOFT" == host_router.state_type
        # Unchanged
        assert "UP" == host.state
        assert "HARD" == host.state_type

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "HARD" == host_router.state_type
        # Goes unreachable hard
        assert "UNREACHABLE" == host.state
        assert "HARD" == host.state_type

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "HARD" == host_router.state_type
        # Unchanged
        assert "UNREACHABLE" == host.state
        assert "SOFT" == host.state_type

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM;{1};{2};{3};{4};{5};{6}\n". \
            format(int(now), host.host_name, 1, 0, 1, 'dark vador', 'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "HARD" == host_router.state_type
        assert "UNREACHABLE" == host.state
        assert "SOFT" == host.state_type
        assert host.problem_has_been_acknowledged

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "HARD" == host_router.state_type
        assert "UNREACHABLE" == host.state
        assert "HARD" == host.state_type
        assert host.problem_has_been_acknowledged

        self.scheduler_loop(1, [[host_router, 0, 'UP']])
        time.sleep(0.1)
        assert "UP" == host_router.state
        assert "HARD" == host_router.state_type
        assert "UNREACHABLE" == host.state
        assert "HARD" == host.state_type
        assert host.problem_has_been_acknowledged

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 0, 'UP']])
        time.sleep(0.1)
        assert "UP" == host_router.state
        assert "HARD" == host_router.state_type
        assert "DOWN" == host.state
        assert "HARD" == host.state_type
        assert not host.problem_has_been_acknowledged

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)
        assert "UP" == host.state
        assert "HARD" == host.state_type
        assert not host.problem_has_been_acknowledged

    def test_ack_service_sticky_ws_wh_ch(self):
        """
        Test service acknowledge with sticky when Warning soft -> Warning hard -> Critical hard
        -> ok

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert not svc.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "WARNING" == svc.state
        assert "SOFT" == svc.state_type

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, svc.service_description, 2, 0, 1, 'dark vador',
                   'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "WARNING" == svc.state
        assert "SOFT" == svc.state_type
        assert svc.problem_has_been_acknowledged

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "WARNING" == svc.state
        assert "HARD" == svc.state_type
        assert svc.problem_has_been_acknowledged

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "CRITICAL" == svc.state
        assert "HARD" == svc.state_type
        assert svc.problem_has_been_acknowledged

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert "OK" == svc.state
        assert "HARD" == svc.state_type
        assert not svc.problem_has_been_acknowledged

    def test_ack_service_sticky_ws_ch(self):
        """
        Test service acknowledge with sticky when Warning soft -> Critical hard -> ok

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert not svc.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "WARNING" == svc.state
        assert "SOFT" == svc.state_type

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, svc.service_description, 2, 0, 1, 'dark vador',
                   'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "WARNING" == svc.state
        assert "SOFT" == svc.state_type
        assert svc.problem_has_been_acknowledged

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "CRITICAL" == svc.state
        assert "HARD" == svc.state_type
        assert svc.problem_has_been_acknowledged

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert "OK" == svc.state
        assert "HARD" == svc.state_type
        assert not svc.problem_has_been_acknowledged

    def test_ack_service_nosticky_ws_ch(self):
        """
        Test service acknowledge with sticky when Warning soft -> Critical hard -> ok

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert not svc.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "WARNING" == svc.state
        assert "SOFT" == svc.state_type

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n".\
            format(int(now), host.host_name, svc.service_description, 1, 0, 1, 'dark vador',
                   'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "WARNING" == svc.state
        assert "SOFT" == svc.state_type
        assert svc.problem_has_been_acknowledged

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "CRITICAL" == svc.state
        assert "HARD" == svc.state_type
        assert not svc.problem_has_been_acknowledged

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert "OK" == svc.state
        assert "HARD" == svc.state_type
        assert not svc.problem_has_been_acknowledged

    def test_ack_service_nosticky_ws_ch_early(self):
        """
        Test service acknowledge with sticky when first (on 3 attempts) Warning soft ->
        Critical hard -> ok

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert not svc.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "WARNING" == svc.state
        assert "SOFT" == svc.state_type

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, svc.service_description, 1, 0, 1, 'dark vador',
                   'normal process')
        self._scheduler.run_external_commands([cmd])
        assert svc.problem_has_been_acknowledged

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "CRITICAL" == svc.state
        assert "SOFT" == svc.state_type
        assert not svc.problem_has_been_acknowledged

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "CRITICAL" == svc.state
        assert "HARD" == svc.state_type
        assert not svc.problem_has_been_acknowledged

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert "OK" == svc.state
        assert "HARD" == svc.state_type
        assert not svc.problem_has_been_acknowledged

    def test_ack_service_sticky_ws_ok(self):
        """
        Test service acknowledge with sticky when Warning soft -> ok

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert not svc.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "WARNING" == svc.state
        assert "SOFT" == svc.state_type

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, svc.service_description, 2, 0, 1, 'dark vador',
                   'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert "OK" == svc.state
        assert "HARD" == svc.state_type
        assert not svc.problem_has_been_acknowledged

    def test_ack_service_nosticky_ws_ok(self):
        """
        Test service acknowledge with sticky when Warning soft -> ok

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert not svc.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "WARNING" == svc.state
        assert "SOFT" == svc.state_type

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, svc.service_description, 1, 0, 1, 'dark vador',
                   'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert "OK" == svc.state
        assert "HARD" == svc.state_type
        assert not svc.problem_has_been_acknowledged

    def test_ack_expire_service_nosticky_ch(self):
        """
        Test service acknowledge expire 2 seconds with sticky when Critical hard

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert not svc.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "CRITICAL" == svc.state
        assert "SOFT" == svc.state_type

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "CRITICAL" == svc.state
        assert "SOFT" == svc.state_type
        assert not svc.problem_has_been_acknowledged

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "CRITICAL" == svc.state
        assert "HARD" == svc.state_type
        assert not svc.problem_has_been_acknowledged

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM_EXPIRE;{1};{2};{3};{4};{5};{6};{7};{8}\n". \
            format(int(now), host.host_name, svc.service_description, 1, 0, 1, (now + 2), 'dark vador',
                   'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "CRITICAL" == svc.state
        assert "HARD" == svc.state_type
        assert svc.problem_has_been_acknowledged

        time.sleep(2.5)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "CRITICAL" == svc.state
        assert "HARD" == svc.state_type
        assert not svc.problem_has_been_acknowledged

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert "OK" == svc.state
        assert "HARD" == svc.state_type
        assert not svc.problem_has_been_acknowledged

    def test_ack_expire_host_nosticky_dh(self):
        """
        Test host acknowledge expire 2 seconds with no sticky when Down hard

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert not host.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host.state
        assert "SOFT" == host.state_type

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host.state
        assert "SOFT" == host.state_type
        assert not host.problem_has_been_acknowledged

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host.state
        assert "HARD" == host.state_type
        assert not host.problem_has_been_acknowledged

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM_EXPIRE;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, 1, 0, 1, (now + 2), 'dark vador', 'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host.state
        assert "HARD" == host.state_type
        assert host.problem_has_been_acknowledged

        time.sleep(2.5)
        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host.state
        assert "HARD" == host.state_type
        assert not host.problem_has_been_acknowledged

    def test_remove_ack_host_nosticky_dh(self):
        """
        Test remove host acknowledge with no sticky when Down hard

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert not host.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host.state
        assert "SOFT" == host.state_type

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM;{1};{2};{3};{4};{5};{6}\n". \
            format(int(now), host.host_name, 1, 0, 1, 'dark vador', 'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host.state
        assert "SOFT" == host.state_type
        assert host.problem_has_been_acknowledged

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host.state
        assert "HARD" == host.state_type
        assert host.problem_has_been_acknowledged

        now = time.time()
        cmd = "[{0}] REMOVE_HOST_ACKNOWLEDGEMENT;{1}\n". \
            format(int(now), host.host_name)
        self._scheduler.run_external_commands([cmd])

        assert not host.problem_has_been_acknowledged

    def test_remove_ack_service_nosticky_ch(self):
        """
        Test service acknowledge expire 2 seconds with sticky when Critical hard

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert not svc.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "CRITICAL" == svc.state
        assert "SOFT" == svc.state_type

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "CRITICAL" == svc.state
        assert "SOFT" == svc.state_type
        assert not svc.problem_has_been_acknowledged

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, svc.service_description, 1, 0, 1, 'dark vador',
                   'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "CRITICAL" == svc.state
        assert "HARD" == svc.state_type
        assert svc.problem_has_been_acknowledged

        now = time.time()
        cmd = "[{0}] REMOVE_SVC_ACKNOWLEDGEMENT;{1};{2}\n". \
            format(int(now), host.host_name, svc.service_description)
        self._scheduler.run_external_commands([cmd])

        assert not svc.problem_has_been_acknowledged
