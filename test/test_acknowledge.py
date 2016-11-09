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
"""
This file test acknowledge.
The acknowledge notifications are tested in test_notifications
"""

import time
from alignak_test import AlignakTest


class TestAcknowledges(AlignakTest):
    """
    This class test acknowledge
    """

    def test_ack_host_sticky_ds_dh(self):
        """
        Test host acknowledge with sticky when Down soft -> Down hard -> up

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertFalse(host.problem_has_been_acknowledged)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("SOFT", host.state_type)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM;{1};{2};{3};{4};{5};{6}\n".\
            format(int(now), host.host_name, 2, 0, 1, 'darth vader', 'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("SOFT", host.state_type)
        self.assertTrue(host.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertTrue(host.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)
        self.assertEqual("UP", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertFalse(host.problem_has_been_acknowledged)

    def test_ack_host_sticky_us_uh_dh(self):
        """
        Test host acknowledge with sticky when Unreachable soft -> Unreachable hard -> Down hard
        -> up

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.notifications_enabled = False

        host_router = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_router_0")
        host_router.checks_in_progress = []
        host_router.event_handler_enabled = False
        host_router.notifications_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [host_router, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertFalse(host.problem_has_been_acknowledged)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host_router.state)
        self.assertEqual("SOFT", host_router.state_type)
        self.assertEqual("UP", host.state)
        self.assertEqual("HARD", host.state_type)

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host_router.state)
        self.assertEqual("SOFT", host_router.state_type)
        self.assertEqual("UP", host.state)
        self.assertEqual("HARD", host.state_type)

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host_router.state)
        self.assertEqual("HARD", host_router.state_type)
        self.assertEqual("UP", host.state)
        self.assertEqual("HARD", host.state_type)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host_router.state)
        self.assertEqual("HARD", host_router.state_type)
        self.assertEqual("UNREACHABLE", host.state)
        self.assertEqual("SOFT", host.state_type)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM;{1};{2};{3};{4};{5};{6}\n". \
            format(int(now), host.host_name, 2, 0, 1, 'darth vader', 'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host_router.state)
        self.assertEqual("HARD", host_router.state_type)
        self.assertEqual("UNREACHABLE", host.state)
        self.assertEqual("SOFT", host.state_type)
        self.assertTrue(host.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host_router.state)
        self.assertEqual("HARD", host_router.state_type)
        self.assertEqual("UNREACHABLE", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertTrue(host.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[host_router, 0, 'UP']])
        time.sleep(0.1)
        self.assertEqual("UP", host_router.state)
        self.assertEqual("HARD", host_router.state_type)
        self.assertEqual("UNREACHABLE", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertTrue(host.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 0, 'UP']])
        time.sleep(0.1)
        self.assertEqual("UP", host_router.state)
        self.assertEqual("HARD", host_router.state_type)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertTrue(host.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)
        self.assertEqual("UP", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertFalse(host.problem_has_been_acknowledged)

    def test_ack_host_nosticky_ds_dh(self):
        """
        Test host acknowledge with no sticky when Down soft -> Down hard -> up

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertFalse(host.problem_has_been_acknowledged)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("SOFT", host.state_type)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM;{1};{2};{3};{4};{5};{6}\n". \
            format(int(now), host.host_name, 1, 0, 1, 'darth vader', 'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("SOFT", host.state_type)
        self.assertTrue(host.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertTrue(host.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)
        self.assertEqual("UP", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertFalse(host.problem_has_been_acknowledged)

    def test_ack_host_nosticky_us_uh_dh(self):
        """
        Test host acknowledge with no sticky when Unreachable soft -> Unreachable hard -> Down hard
        -> up

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.notifications_enabled = False

        host_router = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_router_0")
        host_router.checks_in_progress = []
        host_router.event_handler_enabled = False
        host_router.notifications_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [host_router, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertFalse(host.problem_has_been_acknowledged)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host_router.state)
        self.assertEqual("SOFT", host_router.state_type)
        self.assertEqual("UP", host.state)
        self.assertEqual("HARD", host.state_type)

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host_router.state)
        self.assertEqual("SOFT", host_router.state_type)
        self.assertEqual("UP", host.state)
        self.assertEqual("HARD", host.state_type)

        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host_router.state)
        self.assertEqual("HARD", host_router.state_type)
        self.assertEqual("UP", host.state)
        self.assertEqual("HARD", host.state_type)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host_router.state)
        self.assertEqual("HARD", host_router.state_type)
        self.assertEqual("UNREACHABLE", host.state)
        self.assertEqual("SOFT", host.state_type)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM;{1};{2};{3};{4};{5};{6}\n". \
            format(int(now), host.host_name, 1, 0, 1, 'darth vader', 'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host_router.state)
        self.assertEqual("HARD", host_router.state_type)
        self.assertEqual("UNREACHABLE", host.state)
        self.assertEqual("SOFT", host.state_type)
        self.assertTrue(host.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host_router.state)
        self.assertEqual("HARD", host_router.state_type)
        self.assertEqual("UNREACHABLE", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertTrue(host.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[host_router, 0, 'UP']])
        time.sleep(0.1)
        self.assertEqual("UP", host_router.state)
        self.assertEqual("HARD", host_router.state_type)
        self.assertEqual("UNREACHABLE", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertTrue(host.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_router, 0, 'UP']])
        time.sleep(0.1)
        self.assertEqual("UP", host_router.state)
        self.assertEqual("HARD", host_router.state_type)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertFalse(host.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)
        self.assertEqual("UP", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertFalse(host.problem_has_been_acknowledged)

    def test_ack_service_sticky_ws_wh_ch(self):
        """
        Test service acknowledge with sticky when Warning soft -> Warning hard -> Critical hard
        -> ok

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertFalse(svc.problem_has_been_acknowledged)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual("WARNING", svc.state)
        self.assertEqual("SOFT", svc.state_type)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, svc.service_description, 2, 0, 1, 'darth vader',
                   'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual("WARNING", svc.state)
        self.assertEqual("SOFT", svc.state_type)
        self.assertTrue(svc.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual("WARNING", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertTrue(svc.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertTrue(svc.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual("OK", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertFalse(svc.problem_has_been_acknowledged)

    def test_ack_service_sticky_ws_ch(self):
        """
        Test service acknowledge with sticky when Warning soft -> Critical hard -> ok

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertFalse(svc.problem_has_been_acknowledged)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual("WARNING", svc.state)
        self.assertEqual("SOFT", svc.state_type)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, svc.service_description, 2, 0, 1, 'darth vader',
                   'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual("WARNING", svc.state)
        self.assertEqual("SOFT", svc.state_type)
        self.assertTrue(svc.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertTrue(svc.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual("OK", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertFalse(svc.problem_has_been_acknowledged)

    def test_ack_service_nosticky_ws_ch(self):
        """
        Test service acknowledge with sticky when Warning soft -> Critical hard -> ok

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertFalse(svc.problem_has_been_acknowledged)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual("WARNING", svc.state)
        self.assertEqual("SOFT", svc.state_type)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n".\
            format(int(now), host.host_name, svc.service_description, 1, 0, 1, 'darth vader',
                   'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual("WARNING", svc.state)
        self.assertEqual("SOFT", svc.state_type)
        self.assertTrue(svc.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertFalse(svc.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual("OK", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertFalse(svc.problem_has_been_acknowledged)

    def test_ack_service_nosticky_ws_ch_early(self):
        """
        Test service acknowledge with sticky when first (on 3 attempts) Warning soft ->
        Critical hard -> ok

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertFalse(svc.problem_has_been_acknowledged)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual("WARNING", svc.state)
        self.assertEqual("SOFT", svc.state_type)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, svc.service_description, 1, 0, 1, 'darth vader',
                   'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.assertTrue(svc.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual("SOFT", svc.state_type)
        self.assertFalse(svc.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertFalse(svc.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual("OK", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertFalse(svc.problem_has_been_acknowledged)

    def test_ack_service_sticky_ws_ok(self):
        """
        Test service acknowledge with sticky when Warning soft -> ok

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertFalse(svc.problem_has_been_acknowledged)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual("WARNING", svc.state)
        self.assertEqual("SOFT", svc.state_type)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, svc.service_description, 2, 0, 1, 'darth vader',
                   'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual("OK", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertFalse(svc.problem_has_been_acknowledged)

    def test_ack_service_nosticky_ws_ok(self):
        """
        Test service acknowledge with sticky when Warning soft -> ok

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertFalse(svc.problem_has_been_acknowledged)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual("WARNING", svc.state)
        self.assertEqual("SOFT", svc.state_type)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, svc.service_description, 1, 0, 1, 'darth vader',
                   'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual("OK", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertFalse(svc.problem_has_been_acknowledged)

    def test_ack_expire_service_nosticky_ch(self):
        """
        Test service acknowledge expire 2 seconds with sticky when Critical hard

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertFalse(svc.problem_has_been_acknowledged)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual("SOFT", svc.state_type)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual("SOFT", svc.state_type)
        self.assertFalse(svc.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertFalse(svc.problem_has_been_acknowledged)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM_EXPIRE;{1};{2};{3};{4};{5};{6};{7};{8}\n". \
            format(int(now), host.host_name, svc.service_description, 1, 0, 1, (now + 2), 'darth vader',
                   'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertTrue(svc.problem_has_been_acknowledged)

        time.sleep(2.5)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertFalse(svc.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual("OK", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertFalse(svc.problem_has_been_acknowledged)

    def test_ack_expire_host_nosticky_dh(self):
        """
        Test host acknowledge expire 2 seconds with no sticky when Down hard

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertFalse(host.problem_has_been_acknowledged)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("SOFT", host.state_type)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("SOFT", host.state_type)
        self.assertFalse(host.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertFalse(host.problem_has_been_acknowledged)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM_EXPIRE;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, 1, 0, 1, (now + 2), 'darth vader', 'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertTrue(host.problem_has_been_acknowledged)

        time.sleep(2.5)
        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertFalse(host.problem_has_been_acknowledged)

    def test_remove_ack_host_nosticky_dh(self):
        """
        Test remove host acknowledge with no sticky when Down hard

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertFalse(host.problem_has_been_acknowledged)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("SOFT", host.state_type)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM;{1};{2};{3};{4};{5};{6}\n". \
            format(int(now), host.host_name, 1, 0, 1, 'darth vader', 'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("SOFT", host.state_type)
        self.assertTrue(host.problem_has_been_acknowledged)

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("HARD", host.state_type)
        self.assertTrue(host.problem_has_been_acknowledged)

        now = time.time()
        cmd = "[{0}] REMOVE_HOST_ACKNOWLEDGEMENT;{1}\n". \
            format(int(now), host.host_name)
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.assertFalse(host.problem_has_been_acknowledged)

    def test_remove_ack_service_nosticky_ch(self):
        """
        Test service acknowledge expire 2 seconds with sticky when Critical hard

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertFalse(svc.problem_has_been_acknowledged)
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual("SOFT", svc.state_type)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual("SOFT", svc.state_type)
        self.assertFalse(svc.problem_has_been_acknowledged)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, svc.service_description, 1, 0, 1, 'darth vader',
                   'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertTrue(svc.problem_has_been_acknowledged)

        now = time.time()
        cmd = "[{0}] REMOVE_SVC_ACKNOWLEDGEMENT;{1};{2}\n". \
            format(int(now), host.host_name, svc.service_description)
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)

        self.assertFalse(svc.problem_has_been_acknowledged)
