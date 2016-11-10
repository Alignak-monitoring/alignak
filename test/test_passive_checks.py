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
This file test passive checks
"""

import time
from alignak_test import AlignakTest


class TestPassiveChecks(AlignakTest):
    """
    This class test passive checks of host and services
    """

    def test_0_start_freshness_on_start_alignak(self):
        """ When alignak starts, freshness period also begins
        instead are stale and so in end of freshness

        :return: None
        """
        self.setup_with_file('cfg/cfg_passive_checks.cfg')
        self.schedulers['scheduler-master'].sched.update_recurrent_works_tick('check_freshness', 1)
        # Test if not schedule a check on passive service/host when start alignak.
        # So the freshness start (item.last_state_update) will begin with time.time() of start
        # Alignak
        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)

        self.assert_actions_count(0)
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')

    def test_1_freshness_state(self):
        """ Test property correctly defined in item (host or service)

        :return: None
        """
        self.setup_with_file('cfg/cfg_passive_checks.cfg')
        self.schedulers['scheduler-master'].sched.update_recurrent_works_tick('check_freshness', 1)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        host_a = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_A")
        host_b = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_B")
        host_c = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_C")
        host_d = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_D")

        svc0 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_A", "test_ok_0")
        svc1 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_A", "test_ok_1")
        svc2 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_A", "test_ok_2")
        svc3 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_A", "test_ok_3")
        svc4 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_A", "test_ok_4")

        self.assertEqual("d", host_a.freshness_state)
        self.assertEqual("x", host_b.freshness_state)
        self.assertEqual("o", host_c.freshness_state)
        self.assertEqual("d", host_d.freshness_state)

        self.assertEqual("o", svc0.freshness_state)
        self.assertEqual("w", svc1.freshness_state)
        self.assertEqual("c", svc2.freshness_state)
        self.assertEqual("u", svc3.freshness_state)
        self.assertEqual("x", svc4.freshness_state)

    def test_2_freshness_expiration(self):
        """ When freshness period expires, set freshness state and output

        Test in end of freshness, item get the state of freshness_state and have output
        'Freshness period expired' and no check planned to check item (host / service)

        :return: None
        """
        self.setup_with_file('cfg/cfg_passive_checks.cfg')
        self.schedulers['scheduler-master'].sched.update_recurrent_works_tick('check_freshness', 1)

        host_a = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_A")
        host_b = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_B")
        host_c = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_C")
        host_d = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_D")

        host_a.last_state_update = int(time.time()) - 10000
        host_b.last_state_update = int(time.time()) - 10000
        host_c.last_state_update = int(time.time()) - 10000
        host_d.last_state_update = int(time.time()) - 10000

        svc0 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_A", "test_ok_0")
        svc1 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_A", "test_ok_1")
        svc2 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_A", "test_ok_2")
        svc3 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_A", "test_ok_3")
        svc4 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_A", "test_ok_4")

        svc0.last_state_update = int(time.time()) - 10000
        svc1.last_state_update = int(time.time()) - 10000
        svc2.last_state_update = int(time.time()) - 10000
        svc3.last_state_update = int(time.time()) - 10000
        svc4.last_state_update = int(time.time()) - 10000

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)

        self.assertEqual("OK", svc0.state)
        self.assertEqual("WARNING", svc1.state)
        self.assertEqual("CRITICAL", svc2.state)
        self.assertEqual("UNKNOWN", svc3.state)
        self.assertEqual("UNKNOWN", svc4.state)

        self.assertEqual("DOWN", host_a.state)
        self.assertEqual("DOWN", host_b.state)
        self.assertEqual("UP", host_c.state)
        self.assertEqual("DOWN", host_d.state)

        items = [svc0, svc1, svc2, svc3, svc4, host_a, host_b, host_c, host_d]
        for item in items:
            self.assertEqual("Freshness period expired", item.output)

        self.assert_actions_count(0)
        self.assert_checks_count(2)  # test_host_0 and test_router_0
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
