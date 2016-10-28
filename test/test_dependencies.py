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
This file test the dependencies between services, hosts
"""

import time
from copy import copy
from nose.tools import nottest
from alignak_test import AlignakTest


class TestDependencies(AlignakTest):
    """
    This class test dependencies between services, hosts

    This is how name the tests:

    * test_u_<function_name>: unit test for a function
    * test_c_*: test configuration
    * test_a_*: test with only active checks
    * test_p_*: test with only passive checks
    * test_ap_*: test with both active and passive checks
    * test_*_s_*: test simple dependencies (2 dependencies)
    * test_*_m_*: test complex dependencies (> 2 dependencies)
    * test_*_h_*: test with hostgroups
    """

    def test_u_is_enable_action_dependent(self):
        """ Test the function is_enable_action_dependent in SchedulingItem

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)
        self.assertEqual(len(self.configuration_errors), 0)
        self.assertEqual(len(self.configuration_warnings), 0)
        hosts = self.schedulers['scheduler-master'].sched.hosts
        services = self.schedulers['scheduler-master'].sched.services

        # a. 1 dep host
        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        router = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_router_0")

        self.assertEqual(1, len(host.act_depend_of))
        self.assertEqual(router.uuid, host.act_depend_of[0][0])

        host.act_depend_of[0][1] = ['d', 'x']
        for state in ['o', 'UP']:
            router.state = state
            self.assertTrue(host.is_enable_action_dependent(hosts, services))
        for state in ['d', 'DOWN', 'x', 'UNREACHABLE']:
            router.state = state
            self.assertFalse(host.is_enable_action_dependent(hosts, services))

        host.act_depend_of[0][1] = ['n']
        for state in ['o', 'UP', 'd', 'DOWN', 'x', 'UNREACHABLE']:
            router.state = state
            self.assertTrue(host.is_enable_action_dependent(hosts, services))

        host.act_depend_of[0][1] = ['d', 'n']
        for state in ['o', 'UP', 'd', 'DOWN', 'x', 'UNREACHABLE']:
            router.state = state
            self.assertTrue(host.is_enable_action_dependent(hosts, services))

        # b. 3 dep
        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        router = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_router_0")
        router_00 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_router_00")
        host_00 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_00")

        self.assertEqual(1, len(host.act_depend_of))
        self.assertEqual(router.uuid, host.act_depend_of[0][0])
        # add dependencies
        ado = copy(host.act_depend_of[0])
        ado[0] = router_00.uuid
        host.act_depend_of.append(ado)
        ado = copy(host.act_depend_of[0])
        ado[0] = host_00.uuid
        host.act_depend_of.append(ado)
        self.assertEqual(3, len(host.act_depend_of))
        self.assertEqual(router.uuid, host.act_depend_of[0][0])
        self.assertEqual(router_00.uuid, host.act_depend_of[1][0])
        self.assertEqual(host_00.uuid, host.act_depend_of[2][0])

        host.act_depend_of[0][1] = ['d', 'x']
        host.act_depend_of[1][1] = ['d', 'x']
        host.act_depend_of[2][1] = ['d', 'x']
        for rstate in ['o', 'UP']:
            router.state = rstate
            for r00state in ['o', 'UP', 'd', 'DOWN', 'x', 'UNREACHABLE']:
                router_00.state = r00state
                for hstate in ['o', 'UP', 'd', 'DOWN', 'x', 'UNREACHABLE']:
                    host_00.state = hstate
                    self.assertTrue(host.is_enable_action_dependent(hosts, services))
        for rstate in ['d', 'DOWN', 'x', 'UNREACHABLE']:
            router.state = rstate
            for r00state in ['o', 'UP']:
                router_00.state = r00state
                for hstate in ['o', 'UP', 'd', 'DOWN', 'x', 'UNREACHABLE']:
                    host_00.state = hstate
                    self.assertTrue(host.is_enable_action_dependent(hosts, services))
            for r00state in ['d', 'DOWN', 'x', 'UNREACHABLE']:
                router_00.state = r00state
                for hstate in ['o', 'UP']:
                    host_00.state = hstate
                    self.assertTrue(host.is_enable_action_dependent(hosts, services))
                for hstate in ['d', 'DOWN', 'x', 'UNREACHABLE']:
                    host_00.state = hstate
                    self.assertFalse(host.is_enable_action_dependent(hosts, services))

        host.act_depend_of[1][1] = ['n']
        for rstate in ['o', 'UP', 'd', 'DOWN', 'x', 'UNREACHABLE']:
            router.state = rstate
            for r00state in ['o', 'UP', 'd', 'DOWN', 'x', 'UNREACHABLE']:
                router_00.state = r00state
                for hstate in ['o', 'UP', 'd', 'DOWN', 'x', 'UNREACHABLE']:
                    host_00.state = hstate
                    self.assertTrue(host.is_enable_action_dependent(hosts, services))

        host.act_depend_of[1][1] = ['d', 'n']
        for rstate in ['o', 'UP', 'd', 'DOWN', 'x', 'UNREACHABLE']:
            router.state = rstate
            for r00state in ['o', 'UP', 'd', 'DOWN', 'x', 'UNREACHABLE']:
                router_00.state = r00state
                for hstate in ['o', 'UP', 'd', 'DOWN', 'x', 'UNREACHABLE']:
                    host_00.state = hstate
                    self.assertTrue(host.is_enable_action_dependent(hosts, services))

    def test_u_check_and_set_unreachability(self):
        """ Test the function check_and_set_unreachability in SchedulingItem

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)
        self.assertEqual(len(self.configuration_errors), 0)
        self.assertEqual(len(self.configuration_warnings), 0)
        hosts = self.schedulers['scheduler-master'].sched.hosts
        services = self.schedulers['scheduler-master'].sched.services

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        router = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_router_0")
        router_00 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_router_00")
        host_00 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_00")

        self.assertEqual(1, len(host.act_depend_of))
        self.assertEqual(router.uuid, host.act_depend_of[0][0])
        # add dependencies
        ado = copy(host.act_depend_of[0])
        ado[0] = router_00.uuid
        host.act_depend_of.append(ado)
        ado = copy(host.act_depend_of[0])
        ado[0] = host_00.uuid
        host.act_depend_of.append(ado)
        self.assertEqual(3, len(host.act_depend_of))
        self.assertEqual(router.uuid, host.act_depend_of[0][0])
        self.assertEqual(router_00.uuid, host.act_depend_of[1][0])
        self.assertEqual(host_00.uuid, host.act_depend_of[2][0])

        for rstate in ['o', 'UP']:
            router.state = rstate
            for r00state in ['o', 'UP', 'd', 'DOWN', 'x', 'UNREACHABLE']:
                router_00.state = r00state
                for hstate in ['o', 'UP', 'd', 'DOWN', 'x', 'UNREACHABLE']:
                    host_00.state = hstate
                    host.state = 'UP'
                    host.check_and_set_unreachability(hosts, services)
                    self.assertEqual('UP', host.state)
        for rstate in ['d', 'DOWN', 'x', 'UNREACHABLE']:
            router.state = rstate
            for r00state in ['o', 'UP']:
                router_00.state = r00state
                for hstate in ['o', 'UP', 'd', 'DOWN', 'x', 'UNREACHABLE']:
                    host_00.state = hstate
                    host.state = 'UP'
                    host.check_and_set_unreachability(hosts, services)
                    self.assertEqual('UP', host.state)
            for r00state in ['d', 'DOWN', 'x', 'UNREACHABLE']:
                router_00.state = r00state
                for hstate in ['o', 'UP']:
                    host_00.state = hstate
                    host.state = 'UP'
                    host.check_and_set_unreachability(hosts, services)
                    self.assertEqual('UP', host.state)
                for hstate in ['d', 'DOWN', 'x', 'UNREACHABLE']:
                    host_00.state = hstate
                    host.state = 'UP'
                    host.check_and_set_unreachability(hosts, services)
                    self.assertEqual('UNREACHABLE', host.state)

    def test_c_dependencies(self):
        """ Test dependencies correctly loaded from config files

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)
        self.assertEqual(len(self.configuration_errors), 0)
        self.assertEqual(len(self.configuration_warnings), 0)

        # test_host_00 -> test_router_00
        test_host_00 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_00")
        self.assertEqual(1, len(test_host_00.act_depend_of))
        for (host, _, _, _) in test_host_00.act_depend_of:
            self.assertEqual(self.schedulers['scheduler-master'].sched.hosts[host].host_name,
                             'test_router_00')

        # test test_host_00.test_ok_1 -> test_host_00
        # test test_host_00.test_ok_1 -> test_host_00.test_ok_0
        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_00", "test_ok_1")
        for (dep_id, _, _, _) in svc.act_depend_of:
            if dep_id in self.schedulers['scheduler-master'].sched.hosts:
                self.assertEqual(self.schedulers['scheduler-master'].sched.hosts[dep_id].host_name,
                                 'test_host_00')
            else:
                self.assertEqual(self.schedulers['scheduler-master'].sched.services[dep_id].service_description,
                                 'test_ok_0')

        # test test_host_C -> test_host_A
        # test test_host_C -> test_host_B
        test_host_c = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_C")
        self.assertEqual(2, len(test_host_c.act_depend_of))
        hosts = []
        for (host, _, _, _) in test_host_c.act_depend_of:
            hosts.append(self.schedulers['scheduler-master'].sched.hosts[host].host_name)
        self.assertItemsEqual(hosts, ['test_host_A', 'test_host_B'])

        # test test_host_E -> test_host_D
        test_host_e = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_E")
        self.assertEqual(1, len(test_host_e.act_depend_of))
        for (host, _, _, _) in test_host_e.act_depend_of:
            self.assertEqual(self.schedulers['scheduler-master'].sched.hosts[host].host_name,
                             'test_host_D')

        # test test_host_11.test_parent_svc -> test_host_11.test_son_svc
        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_11", "test_parent_svc")
        for (dep_id, _, _, _) in svc.act_depend_of:
            if dep_id in self.schedulers['scheduler-master'].sched.hosts:
                self.assertEqual(self.schedulers['scheduler-master'].sched.hosts[dep_id].host_name,
                                 'test_host_11')
            else:
                self.assertEqual(self.schedulers['scheduler-master'].sched.services[dep_id].service_description,
                                 'test_son_svc')

        # test test_host_11.test_ok_1 -> test_host_11.test_ok_0
        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_11", "test_ok_1")
        for (dep_id, _, _, _) in svc.act_depend_of:
            if dep_id in self.schedulers['scheduler-master'].sched.hosts:
                self.assertEqual(self.schedulers['scheduler-master'].sched.hosts[dep_id].host_name,
                                 'test_host_11')
            else:
                self.assertEqual(self.schedulers['scheduler-master'].sched.services[dep_id].service_description,
                                 'test_ok_0')

    def test_c_host_passive_service_active(self):
        """ Test host passive and service active

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies_conf.cfg')
        self.assertTrue(self.conf_is_correct)
        self.assertEqual(len(self.configuration_errors), 0)
        self.assertEqual(len(self.configuration_warnings), 0)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("host_P")
        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "host_P", "service_A")
        self.assertEqual(0, len(svc.act_depend_of))

    def test_c_host_passive_service_passive(self):
        """ Test host passive and service passive

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies_conf.cfg')
        self.assertTrue(self.conf_is_correct)
        self.assertEqual(len(self.configuration_errors), 0)
        self.assertEqual(len(self.configuration_warnings), 0)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("host_P")
        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "host_P", "service_P")
        self.assertEqual(0, len(svc.act_depend_of))

    def test_c_host_active_service_passive(self):
        """ Test host active and service passive

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies_conf.cfg')
        self.assertTrue(self.conf_is_correct)
        self.assertEqual(len(self.configuration_errors), 0)
        self.assertEqual(len(self.configuration_warnings), 0)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("host_A")
        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "host_A", "service_P")
        self.assertEqual(1, len(svc.act_depend_of))
        self.assertEqual(host.uuid, svc.act_depend_of[0][0])

    def test_c_host_active_on_host_passive(self):
        """ Test host active on host active

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies_conf.cfg')
        self.assertTrue(self.conf_is_correct)
        self.assertEqual(len(self.configuration_errors), 0)
        self.assertEqual(len(self.configuration_warnings), 0)

        host0 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("host_P_0")
        host1 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("host_A_P")
        self.assertEqual(0, len(host1.act_depend_of))

    def test_c_host_passive_on_host_active(self):
        """ Test host passive on host active

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies_conf.cfg')
        self.assertTrue(self.conf_is_correct)
        self.assertEqual(len(self.configuration_errors), 0)
        self.assertEqual(len(self.configuration_warnings), 0)

        host0 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("host_A_0")
        host1 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("host_P_A")
        self.assertEqual(1, len(host1.act_depend_of))
        self.assertEqual(host0.uuid, host1.act_depend_of[0][0])

    def test_c_host_passive_on_host_passive(self):
        """ Test host passive on host passive

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies_conf.cfg')
        self.assertTrue(self.conf_is_correct)
        self.assertEqual(len(self.configuration_errors), 0)
        self.assertEqual(len(self.configuration_warnings), 0)

        host0 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("host_P_0")
        host1 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("host_P_P")
        self.assertEqual(0, len(host1.act_depend_of))

    def test_c_options_x(self):
        """ Test conf for 'x' (UNREACHABLE) in act_depend_of

        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies_conf.cfg')

        self.assertTrue(self.conf_is_correct)
        self.assertEqual(len(self.configuration_errors), 0)
        self.assertEqual(len(self.configuration_warnings), 0)

        host0 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("host_o_A")
        host1 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("host_o_B")
        self.assertEqual(1, len(host1.act_depend_of))
        self.assertEqual(host0.uuid, host1.act_depend_of[0][0])
        self.assertEqual(['d', 'x'], host1.act_depend_of[0][1])

    def test_c_notright1(self):
        """ Test that the arbiter raises an error when have an orphan dependency in config files
        in hostdependency, dependent_host_name is unknown

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/dependencies/cfg_dependencies_bad1.cfg')
        self.assertEqual(len(self.configuration_errors), 4)
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_c_notright2(self):
        """ Test that the arbiter raises an error when we have an orphan dependency in config files
        in hostdependency, host_name unknown

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/dependencies/cfg_dependencies_bad2.cfg')
        # TODO: improve test
        self.assertEqual(len(self.configuration_errors), 4)
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_c_notright3(self):
        """ Test that the arbiter raises an error when we have an orphan dependency in config files
        in host definition, the parent is unknown

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/dependencies/cfg_dependencies_bad3.cfg')
        self.assertEqual(len(self.configuration_errors), 2)
        self.assertEqual(len(self.configuration_warnings), 8)

    def test_c_notright4(self):
        """ Test that the arbiter raises an error when have an orphan dependency in config files
        in servicedependency, dependent_service_description is unknown

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/dependencies/cfg_dependencies_bad4.cfg')
        self.assertEqual(len(self.configuration_errors), 2)
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_c_notright5(self):
        """ Test that the arbiter raises an error when have an orphan dependency in config files
        in servicedependency, dependent_host_name is unknown

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/dependencies/cfg_dependencies_bad5.cfg')
        self.assertEqual(len(self.configuration_errors), 2)
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_c_notright6(self):
        """ Test that the arbiter raises an error when have an orphan dependency in config files
        in servicedependency, host_name unknown

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/dependencies/cfg_dependencies_bad6.cfg')
        self.assertEqual(len(self.configuration_errors), 2)
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_c_notright7(self):
        """ Test that the arbiter raises an error when have an orphan dependency in config files
        in servicedependency, service_description unknown

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/dependencies/cfg_dependencies_bad7.cfg')
        # Service test_ok_0_notknown not found for 2 hosts.
        self.assertEqual(len(self.configuration_errors), 3)
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_a_s_service_host_up(self):
        """ Test dependency (checks and notifications) between the service and the host (case 1)

        08:00:00 check_host OK HARD
        08:01:30 check_service (CRITICAL)
           => host check planned

        08:02:30 check_host OK HARD
        08:02:30 check_service CRITICAL HARD

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_00")
        host.checks_in_progress = []
        host.max_check_attempts = 1
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_00", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.max_check_attempts = 1
        svc.checks_in_progress = []
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)
        self.assert_checks_count(10)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual("OK", svc.state)
        self.assert_actions_count(0)
        self.assertEqual(0, svc.current_notification_number, 'Critical HARD, but check first host')

        # previous 10 + 2 checks: 1 for svc in waitdep and 1 scheduled for
        # test_host_00 (parent/dependent)
        self.assert_checks_count(12)
        self.assert_checks_match(10, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(10, 'hostname test_host_00', 'command')
        self.assert_checks_match(10, 'scheduled', 'status')
        self.assert_checks_match(11, 'waitdep', 'status')

        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual(1, svc.current_notification_number, 'Critical HARD')
        self.assert_actions_count(2)
        self.assert_actions_match(0, 'VOID', 'command')
        self.assert_actions_match(1, 'servicedesc test_ok_0', 'command')
        self.assert_checks_count(10)

    def test_a_s_service_host_down(self):
        """ Test dependency (checks and notifications) between the service and the host (case 2)

        08:00:00 check_host OK HARD
        08:01:30 check_service (CRITICAL)
           => host check planned

        08:02:30 check_host DOWN HARD
        08:02:30 check_service CRITICAL HARD

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_00")
        host.checks_in_progress = []
        host.max_check_attempts = 1
        host.act_depend_of = []
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_00", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.max_check_attempts = 1
        svc.checks_in_progress = []
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)
        self.assert_checks_count(10)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual("OK", svc.state)
        self.assert_actions_count(0)
        self.assertEqual(0, svc.current_notification_number, 'Critical HARD, but check first host')

        # previous 10 + 2 checks: 1 for svc in waitdep and 1 scheduled for
        # test_host_00 (parent/dependent)
        self.assert_checks_count(12)
        self.assert_checks_match(10, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(10, 'hostname test_host_00', 'command')
        self.assert_checks_match(10, 'scheduled', 'status')
        self.assert_checks_match(11, 'waitdep', 'status')

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual("UNREACHABLE", svc.state)
        self.assertEqual(0, svc.current_notification_number, 'No notif, unreachable HARD')
        self.assertEqual(1, host.current_notification_number, '1 notif, down HARD')
        self.assert_actions_count(1)
        self.assert_actions_match(0, '--hostname test_host_00 --notificationtype PROBLEM --hoststate DOWN', 'command')
        self.assert_checks_count(10)

        # test service keep in UNREACHABLE
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("UNREACHABLE", svc.state)

    def test_a_s_host_host(self):
        """ Test the dependency between 2 hosts
        08:00:00 check_host OK HARD
        08:01:30 check_host (CRITICAL)
           => router check planned

        08:02:30 check_router OK HARD
        08:02:30 check_host CRITICAL HARD

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)

        host_00 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_00")
        host_00.checks_in_progress = []
        host_00.max_check_attempts = 1
        host_00.event_handler_enabled = False

        router_00 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_router_00")
        router_00.checks_in_progress = []
        router_00.max_check_attempts = 1
        router_00.event_handler_enabled = False

        self.scheduler_loop(1, [[host_00, 0, 'UP'], [router_00, 0, 'UP']])
        time.sleep(0.1)
        self.assert_actions_count(0)
        self.assert_checks_count(10)

        self.scheduler_loop(1, [[host_00, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("UP", host_00.state)
        self.assertEqual("UP", router_00.state)
        self.assert_actions_count(0)
        self.assert_checks_count(12)
        # self.assert_checks_match(10, 'test_hostcheck.pl', 'command')
        # self.assert_checks_match(10, 'hostname test_host_00', 'command')
        # self.assert_checks_match(10, 'waitdep', 'status')
        # self.assert_checks_match(11, 'scheduled', 'status')

        self.scheduler_loop(1, [[router_00, 0, 'UP']])
        time.sleep(0.1)
        self.assertEqual("DOWN", host_00.state)
        self.assertEqual("UP", router_00.state)
        self.assertEqual(1, host_00.current_notification_number, 'Critical HARD')
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'hostname test_host_00', 'command')
        self.assert_checks_count(10)

    def test_a_m_service_host_host_up(self):
        """ Test the dependencies between service -> host -> host
        08:00:00 check_host OK HARD
        08:00:00 check_router OK HARD
        08:01:30 check_service (CRITICAL)
           => host check planned
        08:02:30 check_host (CRITICAL HARD)
           => router check planned

        08:02:30 check_router UP HARD
        08:02:30 check_host CRITICAL HARD
        08:02:30 check_service CRITICAL HARD

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)

        router_00 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_router_00")
        router_00.checks_in_progress = []
        router_00.max_check_attempts = 1
        router_00.event_handler_enabled = False

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_00")
        host.checks_in_progress = []
        host.max_check_attempts = 1
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_00", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.max_check_attempts = 1
        svc.event_handler_enabled = False

        # Host is UP
        self.scheduler_loop(1, [[router_00, 0, 'UP'], [host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual("UP", router_00.state)
        self.assertEqual("UP", host.state)
        self.assertEqual("OK", svc.state)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assertEqual(0, host.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)
        self.assert_checks_count(9)

        # Service is CRITICAL
        print "====================== svc CRITICAL ==================="
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("UP", router_00.state)
        self.assertEqual("UP", host.state)
        self.assertEqual("OK", svc.state)
        self.assertEqual(0, svc.current_notification_number, 'No notifications')
        self.assert_actions_count(0)
        # New host check
        self.assert_checks_count(12)
        self.show_checks()

        # Host is DOWN
        print "====================== host DOWN ==================="
        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("UP", router_00.state)
        self.assertEqual("UP", host.state)
        self.assertEqual("OK", svc.state)
        self.assertEqual(0, svc.current_notification_number, 'No notifications')
        self.assertEqual(0, host.current_notification_number, 'No notifications')
        self.assert_actions_count(0)
        self.assert_checks_count(12)
        self.show_checks()

        # Router is UP
        print "====================== router UP ==================="
        self.scheduler_loop(1, [[router_00, 0, 'UP']])
        time.sleep(0.1)
        self.show_checks()
        self.assertEqual("UP", router_00.state)
        self.assertEqual("DOWN", host.state)
        self.assertEqual("UNREACHABLE", svc.state)
        self.assertEqual(0, svc.current_notification_number, 'No notifications')
        self.assertEqual(1, host.current_notification_number, '1 host notification')
        self.assert_checks_count(9)
        self.show_checks()
        self.assert_actions_count(1)
        self.show_actions()
        self.assert_actions_match(0, 'notifier.pl --hostname test_host_00 --notificationtype PROBLEM --hoststate DOWN', 'command')

    def test_a_m_service_host_host_critical(self):
        """ Test the dependencies between service -> host -> host
        08:00:00 check_host OK HARD
        08:00:00 check_router OK HARD
        08:01:30 check_service (CRITICAL)
           => host check planned
        08:02:30 check_host (CRITICAL HARD)
           => router check planned

        08:02:30 check_router CRITICAL HARD
        08:02:30 check_host CRITICAL HARD
        08:02:30 check_service CRITICAL HARD

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)

        router_00 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_router_00")
        router_00.checks_in_progress = []
        router_00.max_check_attempts = 1
        router_00.event_handler_enabled = False

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_00")
        host.checks_in_progress = []
        host.max_check_attempts = 1
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_00", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.max_check_attempts = 1
        svc.event_handler_enabled = False

        # Host is UP
        self.scheduler_loop(1, [[router_00, 0, 'UP'], [host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual("UP", router_00.state)
        self.assertEqual("UP", host.state)
        self.assertEqual("OK", svc.state)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assertEqual(0, host.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)
        self.assert_checks_count(9)

        # Service is CRITICAL
        print "====================== svc CRITICAL ==================="
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("UP", router_00.state)
        self.assertEqual("UP", host.state)
        self.assertEqual("OK", svc.state)
        self.assertEqual(0, svc.current_notification_number, 'No notifications')
        self.assert_actions_count(0)
        # New host check
        self.assert_checks_count(12)
        self.show_checks()

        # Host is DOWN
        print "====================== host DOWN ==================="
        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        self.assertEqual("UP", router_00.state)
        self.assertEqual("UP", host.state)
        self.assertEqual("OK", svc.state)
        self.assertEqual(0, svc.current_notification_number, 'No notifications')
        self.assertEqual(0, host.current_notification_number, 'No notifications')
        self.assertEqual(0, router_00.current_notification_number, 'No notifications')
        self.assert_actions_count(0)
        self.assert_checks_count(12)
        self.show_checks()

        # Router is UP
        print "====================== router DOWN ==================="
        self.scheduler_loop(1, [[router_00, 2, 'DOWN']])
        time.sleep(0.1)
        self.show_checks()
        self.assertEqual("DOWN", router_00.state)
        self.assertEqual("UNREACHABLE", host.state)
        self.assertEqual("UNREACHABLE", svc.state)
        self.assertEqual(0, svc.current_notification_number, 'No notifications')
        self.assertEqual(0, host.current_notification_number, 'No notification')
        self.assertEqual(1, router_00.current_notification_number, '1 host notifications')
        self.assert_checks_count(9)
        self.show_checks()
        self.assert_actions_count(1)
        self.show_actions()
        self.assert_actions_match(0, 'notifier.pl --hostname test_router_00 --notificationtype PROBLEM --hoststate DOWN', 'command')

    def test_a_m_services(self):
        """ Test when multiple services dependency the host

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_00")
        host.checks_in_progress = []
        host.max_check_attempts = 1
        host.event_handler_enabled = False

        svc1 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_00", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc1.notification_interval = 20
        svc1.checks_in_progress = []
        svc1.max_check_attempts = 1
        svc1.event_handler_enabled = False

        svc2 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_00", "test_ok_1")
        # To make tests quicker we make notifications send very quickly
        svc2.notification_interval = 20
        svc2.checks_in_progress = []
        svc2.max_check_attempts = 1
        svc2.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc1, 0, 'OK'], [svc2, 0, 'OK']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc1, 0, 'OK'], [svc2, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc1.state_type)
        self.assertEqual("OK", svc1.state)
        self.assertEqual("HARD", svc2.state_type)
        self.assertEqual("OK", svc2.state)
        self.assertEqual("HARD", host.state_type)
        self.assertEqual("UP", host.state)
        self.assert_actions_count(0)
        self.assert_checks_count(9)

        print "====================== svc1 && svc2 CRITICAL ==================="
        self.scheduler_loop(1, [[svc1, 2, 'CRITICAL'], [svc2, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(0)
        self.assert_checks_count(12)
        self.assertEqual("UP", host.state)
        self.assertEqual("OK", svc1.state)
        self.assertEqual("OK", svc2.state)
        self.assert_checks_match(9, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(9, 'hostname test_host_00', 'command')

        print "====================== host UP ==================="
        self.scheduler_loop(1, [[host, 0, 'UP']])
        time.sleep(0.1)
        self.assertEqual("UP", host.state)
        self.assertEqual("CRITICAL", svc1.state)
        self.assertEqual("CRITICAL", svc2.state)
        self.show_actions()
        self.assertEqual(0, host.current_notification_number, 'No notifications')
        self.assertEqual(1, svc1.current_notification_number, '1 notification')
        self.assertEqual(1, svc2.current_notification_number, '1 notification')
        self.assert_actions_count(4)
        self.assert_actions_match(0, 'VOID', 'command')
        self.assert_actions_match(1, 'VOID', 'command')

        actions = sorted(self.schedulers['scheduler-master'].sched.actions.values(), key=lambda x: x.creation_time)
        num = 0
        commands = []
        for action in actions:
            if num > 1:
                commands.append(action.command)
            num += 1

        if 'servicedesc test_ok_0' in commands[0]:
            self.assert_actions_match(2, 'hostname test_host_00 --servicedesc test_ok_0', 'command')
            self.assert_actions_match(3, 'hostname test_host_00 --servicedesc test_ok_1', 'command')
        else:
            self.assert_actions_match(3, 'hostname test_host_00 --servicedesc test_ok_0', 'command')
            self.assert_actions_match(2, 'hostname test_host_00 --servicedesc test_ok_1', 'command')

    def test_p_s_service_not_check_passive_host(self):
        """ Test passive service critical not check the dependent host (passive)

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)

        self.schedulers['scheduler-master'].sched.update_recurrent_works_tick('check_freshness', 1)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_E")
        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_E", "test_ok_0")

        self.assertEqual(0, len(svc.act_depend_of))

        # it's passive, create check manually
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_E;0;Host is UP' % time.time()
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_E;test_ok_0;0;Service is OK' % time.time()
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()
        time.sleep(0.1)
        self.assertEqual("UP", host.state)
        self.assertEqual("OK", svc.state)

        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_E;test_ok_0;2;Service is CRITICAL' % time.time()
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual("UP", host.state)
        self.assertEqual("CRITICAL", svc.state)
        self.assert_actions_count(0)
        self.assert_checks_count(12)

    def test_ap_s_passive_service_check_active_host(self):
        """ Test passive service critical check the dependent host (active)

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies_conf.cfg')
        self.assertTrue(self.conf_is_correct)

        self.schedulers['scheduler-master'].sched.update_recurrent_works_tick('check_freshness', 1)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("host_A")
        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "host_A", "service_P")

        self.assertEqual(1, len(svc.act_depend_of))

        self.scheduler_loop(1, [[host, 0, 'UP']])
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;host_A;service_P;0;Service is OK' % time.time()
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()
        time.sleep(0.1)
        self.assertEqual("UP", host.state)
        self.assertEqual("OK", svc.state)

        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;host_A;service_P;2;Service is CRITICAL' % time.time()
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual("UP", host.state)
        self.assertEqual("OK", svc.state)
        self.assert_actions_count(0)
        self.assert_checks_count(11)
        # checks_logs=[[[
        # 	0 = creation: 1477557942.18, is_a: check, type: , status: scheduled, planned: 1477557954, command: /tmp/dependencies/plugins/test_hostcheck.pl --type=down --failchance=2% --previous-state=UP --state-duration=0 --hostname host_A_P
        # 	1 = creation: 1477557942.19, is_a: check, type: , status: scheduled, planned: 1477557944, command: /tmp/dependencies/plugins/test_hostcheck.pl --type=down --failchance=2% --previous-state=UP --state-duration=0 --hostname host_o_B
        # 	2 = creation: 1477557942.19, is_a: check, type: , status: scheduled, planned: 1477557949, command: /tmp/dependencies/plugins/test_hostcheck.pl --type=flap --failchance=2% --previous-state=UP --state-duration=0 --hostname test_router_0
        # 	3 = creation: 1477557942.19, is_a: check, type: , status: scheduled, planned: 1477557945, command: /tmp/dependencies/plugins/test_hostcheck.pl --type=down --failchance=2% --previous-state=UP --state-duration=0 --hostname host_A_0
        # 	4 = creation: 1477557942.2, is_a: check, type: , status: scheduled, planned: 1477557994, command: /tmp/dependencies/plugins/test_hostcheck.pl --type=down --failchance=2% --previous-state=UP --state-duration=0 --hostname host_o_A
        # 	5 = creation: 1477557942.2, is_a: check, type: , status: scheduled, planned: 1477557951, command: /tmp/dependencies/plugins/test_hostcheck.pl --type=up --failchance=2% --previous-state=UP --state-duration=0 --parent-state=UP --hostname test_host_0
        # 	6 = creation: 1477557942.21, is_a: check, type: , status: scheduled, planned: 1477557974, command: /tmp/dependencies/plugins/test_servicecheck.pl --type=ok --failchance=5% --previous-state=OK --state-duration=0 --total-critical-on-host=0 --total-warning-on-host=0 --hostname test_host_0 --servicedesc test_ok_0
        # 	7 = creation: 1477557942.21, is_a: check, type: , status: scheduled, planned: 1477557946, command: /tmp/dependencies/plugins/test_servicecheck.pl --type=ok --failchance=5% --previous-state=OK --state-duration=0 --total-critical-on-host=0 --total-warning-on-host=0 --hostname host_P --servicedesc service_A
        # 	8 = creation: 1477557942.21, is_a: check, type: , status: scheduled, planned: 1477557980, command: /tmp/dependencies/plugins/test_servicecheck.pl --type=ok --failchance=5% --previous-state=OK --state-duration=0 --total-critical-on-host=0 --total-warning-on-host=0 --hostname host_A --servicedesc service_A
        # 	9 = creation: 1477557942.24, is_a: check, type: , status: scheduled, planned: 1477557995, command: /tmp/dependencies/plugins/test_hostcheck.pl --type=down --failchance=2% --previous-state=UP --state-duration=1477557942 --hostname host_A
        # 	10 = creation: 1477557942.37, is_a: check, type: , status: waitdep, planned: 1477557942.36, command: /tmp/dependencies/plugins/test_servicecheck.pl --type=ok --failchance=5% --previous-state=OK --state-duration=1477557942 --total-critical-on-host=0 --total-warning-on-host=0 --hostname host_A --servicedesc service_P
        # ]]]
        self.assert_checks_match(10, 'waitdep', 'status')

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        self.assertEqual("DOWN", host.state)
        self.assertEqual("UNREACHABLE", svc.state)

    def test_c_h_hostdep_withno_depname(self):
        """ Test for host dependency dispatched on all hosts of an hostgroup
        1st solution: define a specific property
        2nd solution: define an hostgroup_name and do not define a dependent_hostgroup_name
        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/dependencies/hostdep_through_hostgroup.cfg')
        self.assertTrue(self.conf_is_correct)

        host0 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        self.assertIsNotNone(host0)
        host1 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_1")
        self.assertIsNotNone(host1)

        # Should got a link between host1 and host0 + link between host1 and router
        self.assertEqual(len(host1.act_depend_of), 2)
        l = host1.act_depend_of[0]
        h = l[0]  # the host that host1 depend on
        self.assertEqual(host0.uuid, h)

    def test_c_h_explodehostgroup(self):
        """ Test for service dependencies dispatched on all hosts of an hostgroup
        1st solution: define a specific property
        2nd solution: define an hostgroup_name and do not define a dependent_hostgroup_name
        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/dependencies/servicedependency_explode_hostgroup.cfg')
        self.assertTrue(self.conf_is_correct)


        # First version: explode_hostgroup property defined
        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_router_0", "SNMP"
        )
        self.assertEqual(len(svc.act_depend_of_me), 2)
        dependent_services = []
        for service in svc.act_depend_of_me:
            dependent_services.append(service[0])

        service_dependencies = []
        service_dependency_postfix = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("test_router_0", "POSTFIX")
        service_dependencies.append(service_dependency_postfix.uuid)
        service_dependency_cpu = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("test_router_0", "CPU")
        service_dependencies.append(service_dependency_cpu.uuid)

        self.assertEqual(set(service_dependencies), set(dependent_services))


        # Second version: hostgroup_name and no dependent_hostgroup_name property defined
        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_router_0", "SNMP"
        )
        self.assertEqual(len(svc.act_depend_of_me), 2)
        dependent_services = []
        for service in svc.act_depend_of_me:
            dependent_services.append(service[0])

        service_dependencies = []
        service_dependency_postfix = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("test_router_0", "POSTFIX")
        service_dependencies.append(service_dependency_postfix.uuid)
        service_dependency_cpu = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("test_router_0", "CPU")
        service_dependencies.append(service_dependency_cpu.uuid)

        self.assertEqual(set(service_dependencies), set(dependent_services))

    def test_c_h_implicithostgroups(self):
        """ All hosts in the hostgroup get the service dependencies. An host in the group can have
        its own services dependencies

        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/dependencies/servicedependency_implicit_hostgroup.cfg')
        self.assertTrue(self.conf_is_correct)

        # Services on host_0
        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        self.assertIsNotNone(svc)

        svc_snmp = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("test_host_0", "SNMP")
        self.assertIsNotNone(svc_snmp)
        svc_postfix = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("test_host_0", "POSTFIX")
        self.assertIsNotNone(svc_postfix)
        svc_cpu = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("test_host_0", "CPU")
        self.assertIsNotNone(svc_cpu)

        # Service on router_0
        svc_snmp2 = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("test_router_0", "SNMP")
        self.assertIsNot(svc_snmp2, None)

        svc_postfix2 = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("test_router_0", "POSTFIX")
        self.assertIsNotNone(svc_postfix2)

        # SNMP on the host is in the dependencies of POSTFIX of the host
        self.assertIn(svc_snmp.uuid, [c[0] for c in svc_postfix.act_depend_of])
        # SNMP on the router is in the dependencies of POSTFIX of the router
        self.assertIn(svc_snmp2.uuid, [c[0] for c in svc_postfix2.act_depend_of])

        # host_0 also has its SSH services and dependencies ...
        svc_postfix = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("test_host_0", "POSTFIX_BYSSH")
        self.assertIsNot(svc_postfix, None)

        svc_ssh = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("test_host_0", "SSH")
        self.assertIsNot(svc_ssh, None)

        svc_cpu = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("test_host_0", "CPU_BYSSH")
        self.assertIsNot(svc_cpu, None)

        self.assertIn(svc_ssh.uuid, [c[0] for c in svc_postfix.act_depend_of])
        self.assertIn(svc_ssh.uuid, [c[0] for c in svc_cpu.act_depend_of])

    @nottest
    # Todo: test this @durieux
    def test_complex_servicedependency(self):
        """ All hosts in the hostgroup get the service dependencies. An host in the group can have
        its own services dependencies

        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/dependencies/servicedependency_complex.cfg')
        self.assertTrue(self.conf_is_correct)

        for s in self.schedulers['scheduler-master'].sched.services:
            print s.get_full_name()

        NRPE = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("myspecifichost", "NRPE")
        self.assertIsNotNone(NRPE)
        Load = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("myspecifichost", "Load")
        self.assertIsNotNone(Load)

        # Direct service dependency definition is valid ...
        self.assertIn(NRPE.uuid, [e[0] for e in Load.act_depend_of])
