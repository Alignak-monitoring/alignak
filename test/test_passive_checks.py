#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2015: Alignak team, see AUTHORS.txt file for contributors
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

from alignak_test import AlignakTest
import time


class TestPassiveChecks(AlignakTest):

    def test_0_start_freshness_on_start_alignak(self):
        """
        When start alignak, freshness period begin too instead are stale and so in edn of freshness

        :return: None
        """
        self.setup_with_file('cfg/cfg_passive_checks.cfg')
        self.scheduler.sched.update_recurrent_works_tick('check_freshness', 1)
        # Test if not schedule a check on passive service/host when start alignak.
        # So the freshness start (item.last_state_update) will begin with time.time() of start
        # Alignak
        host = self.scheduler.sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP']], False)
        time.sleep(0.1)

        self.assert_actions_count(0)
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')

    def test_1_freshness_state(self):
        """
        Test property right defined in item (host or service)

        :return: None
        """
        self.setup_with_file('cfg/cfg_passive_checks.cfg')
        self.scheduler.sched.update_recurrent_works_tick('check_freshness', 1)

        host = self.scheduler.sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        host_A = self.scheduler.sched.hosts.find_by_name("test_host_A")
        host_B = self.scheduler.sched.hosts.find_by_name("test_host_B")
        host_C = self.scheduler.sched.hosts.find_by_name("test_host_C")
        host_D = self.scheduler.sched.hosts.find_by_name("test_host_D")

        svc0 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_A", "test_ok_0")
        svc1 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_A", "test_ok_1")
        svc2 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_A", "test_ok_2")
        svc3 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_A", "test_ok_3")
        svc4 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_A", "test_ok_4")

        self.assertEqual("d", host_A.freshness_state)
        self.assertEqual("u", host_B.freshness_state)
        self.assertEqual("n", host_C.freshness_state)
        self.assertEqual("d", host_D.freshness_state)

        self.assertEqual("o", svc0.freshness_state)
        self.assertEqual("w", svc1.freshness_state)
        self.assertEqual("c", svc2.freshness_state)
        self.assertEqual("u", svc3.freshness_state)
        self.assertEqual("u", svc4.freshness_state)

    def test_2_freshness_expiration(self):
        """
        Test in end of freshness, item get the state of freshness_state and have output
        'Freshness period expired'

        :return: None
        """

        pass

