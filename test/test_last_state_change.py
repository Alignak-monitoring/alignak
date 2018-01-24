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
"""
This file test the last_state_change in many cases
"""

import time
from alignak_test import AlignakTest


class TestHostsvcLastStateChange(AlignakTest):
    """
    This class test acknowledge
    """

    def test_host(self):
        """ Test the last_state_change of host

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.2)
        assert host.last_state_change == 0

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.2)
        assert host.last_state_change == 0

        before = time.time()
        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        after = time.time()
        time.sleep(0.2)
        assert host.last_state_change != 0
        assert host.last_state_change > before
        assert host.last_state_change < after
        reference_time = host.last_state_change

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.2)
        assert host.last_state_change == reference_time

        before = time.time()
        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.2)
        assert host.last_state_change != reference_time
        assert host.last_state_change > before

    def test_host_unreachable(self):
        """ Test last_state_change in unreachable mode (in host)

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

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
        assert not host.problem_has_been_acknowledged
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "SOFT" == host_router.state_type
        assert "UP" == host.state
        assert "HARD" == host.state_type

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "SOFT" == host_router.state_type
        assert "UP" == host.state
        assert "HARD" == host.state_type

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        assert "DOWN" == host_router.state
        assert "HARD" == host_router.state_type
        assert "UP" == host.state
        assert "HARD" == host.state_type

        before = time.time()
        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        after = time.time()
        time.sleep(0.2)
        assert "DOWN" == host_router.state
        assert "HARD" == host_router.state_type
        assert "UNREACHABLE" == host.state
        assert "SOFT" == host.state_type

        assert host.last_state_change != 0
        assert host.last_state_change > before
        assert host.last_state_change < after
        reference_time = host.last_state_change

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.2)
        assert "UNREACHABLE" == host.state
        assert "UNREACHABLE" == host.last_state
        assert host.last_state_change == reference_time

        before = time.time()
        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.2)
        assert host.last_state_change != reference_time
        assert host.last_state_change > before

    def test_service(self):
        """ Test the last_state_change of service

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.2)
        assert svc.last_state_change == 0

        before = time.time()
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        after = time.time()
        time.sleep(0.2)
        assert svc.last_state_change != 0
        assert svc.last_state_change > before
        assert svc.last_state_change < after
        reference_time = svc.last_state_change

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.2)
        assert svc.last_state_change == reference_time

        before = time.time()
        self.scheduler_loop(1, [[svc, 0, 'UP']])
        time.sleep(0.2)
        assert svc.last_state_change != reference_time
        assert svc.last_state_change > before
