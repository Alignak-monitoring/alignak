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
This file contains the test for the freshness check feature
"""

import time
import datetime
from freezegun import freeze_time
from .alignak_test import AlignakTest


class TestPassiveChecks(AlignakTest):
    """
    This class test passive checks for host and services
    """
    def setUp(self):
        super(TestPassiveChecks, self).setUp()
        self.setup_with_file('cfg/cfg_passive_checks.cfg',
                             dispatching=True)
        self.clear_logs()
        assert self.conf_is_correct

    def test_start_freshness_on_alignak_start(self):
        """ When alignak starts, freshness period also starts
        instead are stale and so in end of freshness

        :return: None
        """
        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'tick_check_freshness': 1})

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
        assert self._arbiter.conf.host_freshness_check_interval == 60

        for h in self._scheduler.hosts:
            print(("Host %s: freshness check: %s (%d s), state: %s/%s, last state update: %s"
                  % (h.get_name(), h.check_freshness, h.freshness_threshold,
                     h.state_type, h.state, h.last_state_update)))

        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'tick_check_freshness': 1})

        print("Global passive checks parameters:")
        print((" - accept_passive_host_checks: %s"
              % self._arbiter.conf.accept_passive_host_checks))
        assert self._arbiter.conf.accept_passive_host_checks is True
        print((" - accept_passive_service_checks: %s"
              % self._arbiter.conf.accept_passive_service_checks))
        assert self._arbiter.conf.accept_passive_service_checks is True

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        host_a = self._scheduler.hosts.find_by_name("test_host_A")
        host_b = self._scheduler.hosts.find_by_name("test_host_B")
        host_c = self._scheduler.hosts.find_by_name("test_host_C")
        host_d = self._scheduler.hosts.find_by_name("test_host_D")
        host_e = self._scheduler.hosts.find_by_name("test_host_E")
        host_f = self._scheduler.hosts.find_by_name("test_host_F")

        assert "d" == host_a.freshness_state
        assert 2400 == host_a.freshness_threshold
        # Even if u is set in the configuration file, get "x"
        assert "x" == host_b.freshness_state
        assert 1800 == host_b.freshness_threshold
        assert "o" == host_c.freshness_state
        assert 3600 == host_c.freshness_threshold
        # New "x" value defined for this host
        assert "x" == host_d.freshness_state
        assert 3600 == host_d.freshness_threshold
        # "x" as default value
        assert "x" == host_e.freshness_state
        assert 3600 == host_e.freshness_threshold
        # "x" as default value - 1200 as default freshness threshold (global conf parameter)
        assert "x" == host_f.freshness_state
        assert 60 == host_f.freshness_threshold

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
        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'tick_check_freshness': 1})

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

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2018, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime

            now = int(time.time())

            # Set last state update in the past...
            host_a.last_state_update = now - 10000
            host_b.last_state_update = now - 10000
            host_c.last_state_update = now - 10000
            host_d.last_state_update = now - 10000
            host_e.last_state_update = now - 10000

            # Set last state update in the past...
            svc0.last_state_update = now - 10000
            svc1.last_state_update = now - 10000
            svc2.last_state_update = now - 10000
            svc3.last_state_update = now - 10000
            svc4.last_state_update = now - 10000
            svc5.last_state_update = now - 10000

            # expiry_date = time.strftime("%Y-%m-%d %H:%M:%S %Z")
            expiry_date = datetime.datetime.utcfromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S %Z")
            self.scheduler_loop(1, [[host, 0, 'UP']])

            # Time warp 5 seconds
            frozen_datetime.tick(delta=datetime.timedelta(seconds=5))

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
                print("%s / %s" % (item.get_name(), item.output))
            for item in items:
                # Some have already been checked twice ...
                if item.get_name() in ['test_host_C', 'test_svc_0']:
                    assert "Freshness period expired: %s, last updated: %s" \
                           % (expiry_date, expiry_date) == item.output
                else:
                    assert "Freshness period expired: %s" \
                           % (expiry_date) == item.output

            self.assert_actions_count(0)    # No raised notifications
            self.assert_checks_count(2)  # test_host_0 and test_router_0
            # Order is not guaranteed
            # self.assert_checks_match(0, 'hostname test_router_0', 'command')
            # self.assert_checks_match(1, 'hostname test_host_0', 'command')

    def test_freshness_disabled(self):
        """ When freshness is disabled for hosts or service, no state change

        :return: None
        """
        self._scheduler.pushed_conf.check_host_freshness = False
        self._scheduler.pushed_conf.check_service_freshness = False

        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'tick_check_freshness': 1})

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
        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'tick_check_freshness': 1})

        host_f = self._scheduler.hosts.find_by_name("test_host_F")

        assert "x" == host_f.freshness_state
        # Not defined, so default value (0) that is replaced with the global host_freshness_check_interval
        assert 60 == host_f.freshness_threshold

        svc6 = self._scheduler.services.find_srv_by_name_and_hostname("test_host_F", "test_svc_6")

        assert "x" == svc6.freshness_state
        # Not defined, so default value - default is 0 for no freshness check!
        assert 60 == svc6.freshness_threshold

    def test_freshness_expiration_repeat_host(self):
        """ We test the running property freshness_expired to know if we are in
        expiration freshness or not - test for an host

        :return: None
        """
        assert self._arbiter.conf.host_freshness_check_interval == 60

        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'tick_check_freshness': 1})

        for h in self._scheduler.hosts:
            print(("Host %s: freshness check: %s (%d s), state: %s/%s, last state update: %s"
                  % (h.get_name(), h.check_freshness, h.freshness_threshold, h.state_type, h.state, h.last_state_update)))
        host_f = self._scheduler.hosts.find_by_name("test_host_F")
        print(("Host F: state: %s/%s, last state update: %s" % (host_f.state_type, host_f.state, host_f.last_state_update)))
        print(host_f)

        host_b = self._scheduler.hosts.find_by_name("test_host_B")
        print(("Host B: state: %s/%s, last state update: %s" % (host_b.state_type, host_b.state, host_b.last_state_update)))
        print(host_b)

        assert "x" == host_b.freshness_state
        assert 1800 == host_b.freshness_threshold
        # Check attempts
        assert 0 == host_b.attempt
        assert 5 == host_b.max_check_attempts

        # Force freshness threshold and latency
        host_b.freshness_threshold = 1
        host_b.__class__.additional_freshness_latency = 1

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False
        print(("Host: state: %s/%s, last state update: %s" % (host_b.state_type, host_b.state, host_b.last_state_update)))

        assert 0 == self.manage_freshness_check(1)
        print(("Host: state: %s/%s, last state update: %s" % (host_b.state_type, host_b.state, host_b.last_state_update)))
        # We are still ok...
        assert "UP" == host_b.state
        assert "HARD" == host_b.state_type
        assert False == host_b.freshness_expired
        # Wait for more than freshness threshold + latency...
        time.sleep(3)

        checks_count = self.manage_freshness_check(1)
        assert 1 == checks_count
        print(("Host: state: %s/%s, last state update: %s" % (host_b.state_type, host_b.state, host_b.last_state_update)))
        assert "UNREACHABLE" == host_b.state
        assert "SOFT" == host_b.state_type
        assert False == host_b.freshness_expired
        assert 1 == host_b.attempt

        time.sleep(1)
        assert 1 == self.manage_freshness_check(1)
        print(("Host: state: %s/%s, last state update: %s" % (host_b.state_type, host_b.state, host_b.last_state_update)))
        assert "UNREACHABLE" == host_b.state
        assert "SOFT" == host_b.state_type
        assert False == host_b.freshness_expired
        assert 2 == host_b.attempt

        time.sleep(1)
        assert 1 == self.manage_freshness_check(1)
        print(("Host: state: %s/%s, last state update: %s" % (host_b.state_type, host_b.state, host_b.last_state_update)))
        assert "UNREACHABLE" == host_b.state
        assert "SOFT" == host_b.state_type
        assert False == host_b.freshness_expired
        assert 3 == host_b.attempt

        time.sleep(1)
        assert 1 == self.manage_freshness_check(1)
        print(("Host: state: %s/%s, last state update: %s" % (host_b.state_type, host_b.state, host_b.last_state_update)))
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
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'UP' == host_b.state
        assert 'Host is UP' == host_b.output
        assert False == host_b.freshness_expired

    def test_freshness_expiration_repeat_host_2(self):
        """ We test the running property freshness_expired to know if we are in
        expiration freshness or not - test for an host (bis)

        :return: None
        """
        assert self._arbiter.conf.host_freshness_check_interval == 60

        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'tick_check_freshness': 1})

        for h in self._scheduler.hosts:
            print(("Host %s: freshness check: %s (%d s), state: %s/%s, last state update: %s"
                  % (h.get_name(), h.check_freshness, h.freshness_threshold, h.state_type, h.state, h.last_state_update)))
        host_f = self._scheduler.hosts.find_by_name("test_host_F")
        print(("Host F: state: %s/%s, last state update: %s" % (host_f.state_type, host_f.state, host_f.last_state_update)))

        assert "x" == host_f.freshness_state
        assert 60 == host_f.freshness_threshold
        # Check attempts
        assert 0 == host_f.attempt
        assert 3 == host_f.max_check_attempts

        # Force freshness threshold and latency
        host_f.freshness_threshold = 1
        host_f.__class__.additional_freshness_latency = 1

        assert 0 == self.manage_freshness_check(1)
        print(("Host: state: %s/%s, last state update: %s" % (host_f.state_type, host_f.state, host_f.last_state_update)))
        # We are still ok...
        assert "UP" == host_f.state
        assert "HARD" == host_f.state_type
        assert False == host_f.freshness_expired
        # Wait for more than freshness threshold + latency...
        time.sleep(3)

        checks_count = self.manage_freshness_check(1)
        assert 1 == checks_count
        print(("Host: state: %s/%s, last state update: %s" % (host_f.state_type, host_f.state, host_f.last_state_update)))
        assert "UNREACHABLE" == host_f.state
        assert "SOFT" == host_f.state_type
        assert False == host_f.freshness_expired
        assert 1 == host_f.attempt

        time.sleep(1)
        assert 1 == self.manage_freshness_check(1)
        print(("Host: state: %s/%s, last state update: %s" % (host_f.state_type, host_f.state, host_f.last_state_update)))
        assert "UNREACHABLE" == host_f.state
        assert "SOFT" == host_f.state_type
        assert False == host_f.freshness_expired
        assert 2 == host_f.attempt

        time.sleep(1)
        assert 1 == self.manage_freshness_check(1)
        print(("Host: state: %s/%s, last state update: %s" % (host_f.state_type, host_f.state, host_f.last_state_update)))
        assert "UNREACHABLE" == host_f.state
        assert "HARD" == host_f.state_type
        assert True == host_f.freshness_expired
        assert 3 == host_f.attempt

        # Then no more change for this host !
        time.sleep(1)
        assert 0 == self.manage_freshness_check(1)
        assert "UNREACHABLE" == host_f.state
        assert "HARD" == host_f.state_type
        assert True == host_f.is_max_attempts()
        assert True == host_f.freshness_expired
        assert 3 == host_f.attempt
        self.show_checks()

        time.sleep(1)
        assert 0 == self.manage_freshness_check(1)
        assert "UNREACHABLE" == host_f.state
        assert "HARD" == host_f.state_type
        assert True == host_f.is_max_attempts()
        assert True == host_f.freshness_expired
        assert 3 == host_f.attempt

        self.show_logs()

        # The freshness log is raised for each check attempt
        assert len(self.get_log_match("alignak.objects.schedulingitem] The freshness period of host 'test_host_F'")) == 3

        assert len(self.get_log_match("Attempt: 1 / 3. ")) == 1
        assert len(self.get_log_match("Attempt: 2 / 3. ")) == 1
        assert len(self.get_log_match("Attempt: 3 / 3. ")) == 1

        # Now receive check_result (passive), so we must be outside of freshness_expired
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_F;0;Host is UP' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'UP' == host_f.state
        assert 'Host is UP' == host_f.output
        assert False == host_f.freshness_expired

    def test_freshness_expiration_repeat_service(self):
        """ We test the running property freshness_expired to know if we are in
        expiration freshness or not - test for a service
        - retry_interval is 1
        - max_check_attempts is 3

        This test runs with the services declare on test_host_F in the configuration

        :return: None
        """
        self._freshness_expiration_repeat_service('test_svc_6')

    def test_freshness_expiration_repeat_service_2(self):
        """ We test the running property freshness_expired to know if we are in
        expiration freshness or not - test for a service
        retry_interval is 0
        max_check_attempts is 2

        :return: None
        """
        self._freshness_expiration_repeat_service('test_svc_7', count=2)

    def test_freshness_expiration_repeat_service_3(self):
        """ We test the running property freshness_expired to know if we are in
        expiration freshness or not - test for a service
        retry_interval is 0
        max_check_attempts is 1

        :return: None
        """
        self._freshness_expiration_repeat_service('test_svc_8', count=1)

    def _freshness_expiration_repeat_service(self, svc_description, count=3):
        """ We test the running property freshness_expired to know if we are in
        expiration freshness or not - test for a service

        :return: None
        """
        assert self._arbiter.conf.service_freshness_check_interval == 60
        assert self._arbiter.conf.host_freshness_check_interval == 60

        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'tick_check_freshness': 1})

        for h in self._scheduler.hosts:
            print(("Host %s: freshness check: %s (%d s), state: %s/%s, last state update: %s"
                  % (h.get_name(), h.check_freshness, h.freshness_threshold, h.state_type, h.state, h.last_state_update)))
        host_f = self._scheduler.hosts.find_by_name("test_host_F")
        svc_f = None
        print(("Host F: state: %s/%s, last state update: %s" % (host_f.state_type, host_f.state, host_f.last_state_update)))
        for s in host_f.services:
            s = self._scheduler.services[s]
            if s.get_name() == svc_description:
                print(("Service %s: freshness check: %s (%d s), state: %s/%s, last state update: %s"
                      % (s.get_name(), s.check_freshness, s.freshness_threshold, s.state_type, s.state, s.last_state_update)))
                svc_f = s
                break
        assert svc_f is not None

        assert "x" == svc_f.freshness_state
        assert 60 == svc_f.freshness_threshold
        # Check attempts
        assert 0 == svc_f.attempt
        assert count == svc_f.max_check_attempts

        # Force freshness threshold and latency
        svc_f.freshness_threshold = 1
        svc_f.__class__.additional_freshness_latency = 1

        # Same as the scheduler list ;)
        services = [s for s in self._scheduler.services
                    if not self._scheduler.hosts[s.host].freshness_expired and
                    s.check_freshness and not s.freshness_expired and
                    s.passive_checks_enabled and not s.active_checks_enabled]
        print(("Freshness expired services: %d" % len(services)))
        # Some potential services to check for freshness
        services_count = len(services)

        assert 0 == self.manage_freshness_check(1)
        print(("Service %s: state: %s/%s, last state update: %s, attempt: %d / %d"
              % (svc_description, svc_f.state_type, svc_f.state, svc_f.last_state_update,
                 svc_f.attempt, svc_f.max_check_attempts)))
        # We are still ok...
        assert "OK" == svc_f.state
        assert "HARD" == svc_f.state_type
        assert False == svc_f.freshness_expired
        # Wait for more than freshness threshold + latency...
        time.sleep(3)

        for idx in range(1, count):
            assert 1 == self.manage_freshness_check()
            print(("Attempt %d: state: %s/%s, last state update: %s, attempt: %d / %d"
                  % (idx, svc_f.state_type, svc_f.state, svc_f.last_state_update,
                     svc_f.attempt, svc_f.max_check_attempts)))
            assert "UNREACHABLE" == svc_f.state
            assert "SOFT" == svc_f.state_type
            assert False == svc_f.freshness_expired
            assert svc_f.attempt == idx

            time.sleep(1)

        self.show_logs()

        # Last check loop must raise a freshness expired and max attempts is reached !
        assert 1 == self.manage_freshness_check()
        print(("Last attempt: state: %s/%s, last state update: %s, attempt: %d / %d"
              % (svc_f.state_type, svc_f.state, svc_f.last_state_update,
                 svc_f.attempt, svc_f.max_check_attempts)))
        assert "UNREACHABLE" == svc_f.state
        assert "HARD" == svc_f.state_type
        assert True == svc_f.is_max_attempts()
        assert True == svc_f.freshness_expired
        assert svc_f.attempt == count

        # assert 1 == self.manage_freshness_check(1)
        # print("Service: state: %s/%s, last state update: %s" % (svc_f.state_type, svc_f.state, svc_f.last_state_update))
        # assert "UNREACHABLE" == svc_f.state
        # assert "SOFT" == svc_f.state_type
        # assert False == svc_f.freshness_expired
        # assert 2 == svc_f.attempt
        # time.sleep(1)
        #
        # assert 1 == self.manage_freshness_check(1)
        # print("Service: state: %s/%s, last state update: %s" % (svc_f.state_type, svc_f.state, svc_f.last_state_update))
        # assert "UNREACHABLE" == svc_f.state
        # assert "HARD" == svc_f.state_type
        # assert True == svc_f.freshness_expired
        # assert 3 == svc_f.attempt

        # Same as the scheduler list ;)
        services = [s for s in self._scheduler.services
                    if not self._scheduler.hosts[s.host].freshness_expired and
                    s.check_freshness and not s.freshness_expired and
                    s.passive_checks_enabled and not s.active_checks_enabled]
        print(("Freshness expired services: %d" % len(services)))
        # One less service to check now !
        assert len(services) == services_count - 1

        # Then no more change for this service ... even if 5 more loops are run!
        for idx in range(1, 5):
            assert 0 == self.manage_freshness_check(1)
            assert "UNREACHABLE" == svc_f.state
            assert "HARD" == svc_f.state_type
            assert True == svc_f.is_max_attempts()
            assert True == svc_f.freshness_expired
            assert svc_f.attempt == count
            time.sleep(0.5)

        self.show_checks()
        self.show_logs()

        # The freshness log is raised for each check attempt
        assert len(self.get_log_match(
            "alignak.objects.schedulingitem] "
            "The freshness period of service 'test_host_F/%s'" % svc_description)) == count

        for idx in range(1, count+1):
            assert len(self.get_log_match("Attempt: %d / %d. "
                                          % (idx, svc_f.max_check_attempts))) == 1
        assert len(self.get_log_match("x / SOFT")) == count - 1
        assert len(self.get_log_match("x / HARD")) == 1

        # Now receive check_result (passive), so we must be outside of freshness_expired
        excmd = "[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_F;%s;0;Service is OK" \
                % (time.time(), svc_description)
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'OK' == svc_f.state
        assert "HARD" == svc_f.state_type
        assert 'Service is OK' == svc_f.output
        if count > 1:
            assert False == svc_f.is_max_attempts()
        else:
            assert True == svc_f.is_max_attempts()
        assert False == svc_f.freshness_expired
        assert svc_f.attempt == 1
