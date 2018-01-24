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

    def test_start_freshness_on_alignak_start(self):
        """ When alignak starts, freshness period also starts
        instead are stale and so in end of freshness

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_passive_checks.cfg')
        assert self.conf_is_correct

        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'check_freshness': 1})

        # Test if not schedule a check on passive service/host when start alignak.
        # So the freshness start (item.last_state_update) will begin with time.time() of start
        # Alignak
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)

        self.assert_actions_count(0)
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')

    def test_freshness_state(self):
        """ Test that freshness_state property is correctly defined in item (host or service)

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_passive_checks.cfg')
        assert self.conf_is_correct

        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'check_freshness': 1})

        print("Global passive checks parameters:")
        print(" - accept_passive_host_checks: %s" %
              (self.arbiter.conf.accept_passive_host_checks))
        assert self.arbiter.conf.accept_passive_host_checks is True
        print(" - accept_passive_service_checks: %s" %
              (self.arbiter.conf.accept_passive_service_checks))
        assert self.arbiter.conf.accept_passive_service_checks is True

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        host_a = self._scheduler.hosts.find_by_name("test_host_A")
        host_b = self._scheduler.hosts.find_by_name("test_host_B")
        host_c = self._scheduler.hosts.find_by_name("test_host_C")
        host_d = self._scheduler.hosts.find_by_name("test_host_D")
        host_e = self._scheduler.hosts.find_by_name("test_host_E")

        assert "d" == host_a.freshness_state
        # Even if u is set in the configuration file, get "x"
        assert "x" == host_b.freshness_state
        assert "o" == host_c.freshness_state
        # New "x" value defined for this host
        assert "x" == host_d.freshness_state
        # "x" as default value
        assert "x" == host_e.freshness_state

        svc0 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_0")
        svc1 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_1")
        svc2 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_2")
        svc3 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_3")
        svc4 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_4")
        svc5 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_5")

        assert "o" == svc0.freshness_state
        assert "w" == svc1.freshness_state
        assert "c" == svc2.freshness_state
        assert "u" == svc3.freshness_state
        assert "x" == svc4.freshness_state
        assert "x" == svc5.freshness_state

    def test_freshness_expiration(self):
        """ When freshness period expires, set freshness state and output

        Test that on freshness period expiry, the item gets the freshness_state and its
        output is 'Freshness period expired' and that no check is scheduled to check
        the item (host / service)

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_passive_checks.cfg')
        assert self.conf_is_correct

        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'check_freshness': 1})

        host_a = self._scheduler.hosts.find_by_name("test_host_A")
        host_b = self._scheduler.hosts.find_by_name("test_host_B")
        host_c = self._scheduler.hosts.find_by_name("test_host_C")
        host_d = self._scheduler.hosts.find_by_name("test_host_D")
        host_e = self._scheduler.hosts.find_by_name("test_host_E")

        assert "d" == host_a.freshness_state
        assert "x" == host_b.freshness_state
        assert "o" == host_c.freshness_state
        assert "x" == host_d.freshness_state
        assert "x" == host_e.freshness_state

        # Set last state update in the past...
        host_a.last_state_update = int(time.time()) - 10000
        host_b.last_state_update = int(time.time()) - 10000
        host_c.last_state_update = int(time.time()) - 10000
        host_d.last_state_update = int(time.time()) - 10000
        host_e.last_state_update = int(time.time()) - 10000

        svc0 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_0")
        svc1 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_1")
        svc2 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_2")
        svc3 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_3")
        svc4 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_4")
        svc5 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_5")

        assert "o" == svc0.freshness_state
        assert "w" == svc1.freshness_state
        assert "c" == svc2.freshness_state
        assert "u" == svc3.freshness_state
        assert "x" == svc4.freshness_state
        assert "x" == svc5.freshness_state

        # Set last state update in the past...
        svc0.last_state_update = int(time.time()) - 10000
        svc1.last_state_update = int(time.time()) - 10000
        svc2.last_state_update = int(time.time()) - 10000
        svc3.last_state_update = int(time.time()) - 10000
        svc4.last_state_update = int(time.time()) - 10000
        svc5.last_state_update = int(time.time()) - 10000

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        # Set the host UP - this will run the scheduler loop to check for freshness
        expiry_date = time.strftime("%Y-%m-%d %H:%M:%S %Z")
        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.01)

        assert "OK" == svc0.state
        assert "WARNING" == svc1.state
        assert "CRITICAL" == svc2.state
        assert "UNKNOWN" == svc3.state
        assert "UNREACHABLE" == svc4.state
        assert "UNREACHABLE" == svc5.state

        assert "DOWN" == host_a.state
        assert "UNREACHABLE" == host_b.state
        assert "UP" == host_c.state
        assert "UNREACHABLE" == host_d.state
        assert "UNREACHABLE" == host_e.state

        items = [svc0, svc1, svc2, svc3, svc4, host_a, host_b, host_c, host_d]
        for item in items:
            assert "Freshness period expired: %s" % expiry_date == item.output

        self.assert_actions_count(0)    # No raised notifications
        self.assert_checks_count(2)  # test_host_0 and test_router_0
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')

    def test_freshness_disabled(self):
        """ When freshness is disabled for hosts or service, no state change

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_passive_checks.cfg')
        assert self.conf_is_correct

        self._scheduler.conf.check_host_freshness = False
        self._scheduler.conf.check_service_freshness = False

        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'check_freshness': 1})

        host_a = self._scheduler.hosts.find_by_name("test_host_A")
        host_b = self._scheduler.hosts.find_by_name("test_host_B")
        host_c = self._scheduler.hosts.find_by_name("test_host_C")
        host_d = self._scheduler.hosts.find_by_name("test_host_D")
        host_e = self._scheduler.hosts.find_by_name("test_host_E")

        assert "d" == host_a.freshness_state
        assert "x" == host_b.freshness_state
        assert "o" == host_c.freshness_state
        assert "x" == host_d.freshness_state
        assert "x" == host_e.freshness_state

        # Set last state update in the past...
        host_a.last_state_update = int(time.time()) - 10000
        host_b.last_state_update = int(time.time()) - 10000
        host_c.last_state_update = int(time.time()) - 10000
        host_d.last_state_update = int(time.time()) - 10000
        host_e.last_state_update = int(time.time()) - 10000

        svc0 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_0")
        svc1 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_1")
        svc2 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_2")
        svc3 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_3")
        svc4 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_4")
        svc5 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_A", "test_svc_5")

        assert "o" == svc0.freshness_state
        assert "w" == svc1.freshness_state
        assert "c" == svc2.freshness_state
        assert "u" == svc3.freshness_state
        assert "x" == svc4.freshness_state
        assert "x" == svc5.freshness_state

        # Set last state update in the past...
        svc0.last_state_update = int(time.time()) - 10000
        svc1.last_state_update = int(time.time()) - 10000
        svc2.last_state_update = int(time.time()) - 10000
        svc3.last_state_update = int(time.time()) - 10000
        svc4.last_state_update = int(time.time()) - 10000
        svc5.last_state_update = int(time.time()) - 10000

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        # Set the host UP - this will run the scheduler loop to check for freshness
        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)

        # Default state remains
        assert "OK" == svc0.state
        assert "OK" == svc1.state
        assert "OK" == svc2.state
        assert "OK" == svc3.state
        assert "OK" == svc4.state
        assert "OK" == svc5.state

        # Default state remains
        assert "UP" == host_a.state
        assert "UP" == host_b.state
        assert "UP" == host_c.state
        assert "UP" == host_d.state
        assert "UP" == host_e.state

    def test_freshness_default_threshold(self):
        """ Host/service get the global freshness threshold if they do not define one

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_passive_checks.cfg')
        assert self.conf_is_correct

        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'check_freshness': 1})

        host_f = self._scheduler.hosts.find_by_name("test_host_F")

        assert "x" == host_f.freshness_state
        assert 3600 == host_f.freshness_threshold

        svc6 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_F", "test_svc_6")

        assert "x" == svc6.freshness_state
        assert 3600 == svc6.freshness_threshold

    def test_freshness_expiration_repeat(self):
        """ We test the running property freshness_expired to know if we are in
        expiration freshness or not

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_passive_checks.cfg')
        self.clear_logs()
        assert self.conf_is_correct

        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'check_freshness': 1})

        host_b = self._scheduler.hosts.find_by_name("test_host_B")

        assert "x" == host_b.freshness_state
        # Check attempts
        assert 0 == host_b.attempt
        assert 5 == host_b.max_check_attempts

        # Force freshness threshold and latency
        host_b.freshness_threshold = 1
        host_b.__class__.additional_freshness_latency = 1

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        print("Host: state: %s/%s, last state update: %s" % (host_b.state_type, host_b.state, host_b.last_state_update))

        assert 0 == self.manage_freshness_check(1)
        print("Host: state: %s/%s, last state update: %s" % (host_b.state_type, host_b.state, host_b.last_state_update))
        # We are still ok...
        assert "UP" == host_b.state
        assert "HARD" == host_b.state_type
        assert False == host_b.freshness_expired
        # Wait for more than freshness threshold + latency...
        time.sleep(3)

        assert 1 == self.manage_freshness_check(1)
        print("Host: state: %s/%s, last state update: %s" % (host_b.state_type, host_b.state, host_b.last_state_update))
        assert "UNREACHABLE" == host_b.state
        assert "SOFT" == host_b.state_type
        assert False == host_b.freshness_expired
        assert 1 == host_b.attempt

        time.sleep(1)
        assert 1 == self.manage_freshness_check(1)
        print("Host: state: %s/%s, last state update: %s" % (host_b.state_type, host_b.state, host_b.last_state_update))
        assert "UNREACHABLE" == host_b.state
        assert "SOFT" == host_b.state_type
        assert False == host_b.freshness_expired
        assert 2 == host_b.attempt

        time.sleep(1)
        assert 1 == self.manage_freshness_check(1)
        print("Host: state: %s/%s, last state update: %s" % (host_b.state_type, host_b.state, host_b.last_state_update))
        assert "UNREACHABLE" == host_b.state
        assert "SOFT" == host_b.state_type
        assert False == host_b.freshness_expired
        assert 3 == host_b.attempt

        time.sleep(1)
        assert 1 == self.manage_freshness_check(1)
        print("Host: state: %s/%s, last state update: %s" % (host_b.state_type, host_b.state, host_b.last_state_update))
        assert "UNREACHABLE" == host_b.state
        assert "SOFT" == host_b.state_type
        assert False == host_b.freshness_expired
        assert 4 == host_b.attempt

        time.sleep(1)
        assert 1 == self.manage_freshness_check(1)
        assert "UNREACHABLE" == host_b.state
        assert "HARD" == host_b.state_type
        assert True == host_b.is_max_attempts()
        assert True == host_b.freshness_expired
        assert 5 == host_b.attempt

        # Then no more change for this host !
        time.sleep(1)
        assert 0 == self.manage_freshness_check(1)
        assert "UNREACHABLE" == host_b.state
        assert "HARD" == host_b.state_type
        assert True == host_b.is_max_attempts()
        assert True == host_b.freshness_expired
        assert 5 == host_b.attempt
        self.show_checks()

        time.sleep(1)
        assert 0 == self.manage_freshness_check(1)
        assert "UNREACHABLE" == host_b.state
        assert "HARD" == host_b.state_type
        assert True == host_b.is_max_attempts()
        assert True == host_b.freshness_expired
        assert 5 == host_b.attempt

        self.show_logs()

        # The freshness log is raised for each check attempt
        assert len(self.get_log_match("alignak.objects.schedulingitem] The freshness period of host 'test_host_B'")) == 5
        # [1512800594] WARNING: [alignak.objects.schedulingitem] The freshness period of host 'test_host_B' is expired by 0d 0h 0m 1s (threshold=0d 0h 0m 1s + 1s). Attempt: 1 / 5. I'm forcing the state to freshness state (x / SOFT).
        # [1512800595] WARNING: [alignak.objects.schedulingitem] The freshness period of host 'test_host_B' is expired by 0d 0h 0m 2s (threshold=0d 0h 0m 1s + 1s). Attempt: 2 / 5. I'm forcing the state to freshness state (x / SOFT).
        # [1512800596] WARNING: [alignak.objects.schedulingitem] The freshness period of host 'test_host_B' is expired by 0d 0h 0m 3s (threshold=0d 0h 0m 1s + 1s). Attempt: 3 / 5. I'm forcing the state to freshness state (x / SOFT).
        # [1512800597] WARNING: [alignak.objects.schedulingitem] The freshness period of host 'test_host_B' is expired by 0d 0h 0m 4s (threshold=0d 0h 0m 1s + 1s). Attempt: 4 / 5. I'm forcing the state to freshness state (x / SOFT).
        # [1512800598] WARNING: [alignak.objects.schedulingitem] The freshness period of host 'test_host_B' is expired by 0d 0h 0m 5s (threshold=0d 0h 0m 1s + 1s). Attempt: 5 / 5. I'm forcing the state to freshness state (x / HARD).

        assert len(self.get_log_match("Attempt: 1 / 5. ")) == 1
        assert len(self.get_log_match("Attempt: 2 / 5. ")) == 1
        assert len(self.get_log_match("Attempt: 3 / 5. ")) == 1
        assert len(self.get_log_match("Attempt: 4 / 5. ")) == 1
        assert len(self.get_log_match("Attempt: 5 / 5. ")) == 1

        # Now receive check_result (passive), so we must be outside of freshness_expired
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_B;0;Host is UP' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert 'UP' == host_b.state
        assert 'Host is UP' == host_b.output
        assert False == host_b.freshness_expired
