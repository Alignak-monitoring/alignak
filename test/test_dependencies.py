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
from alignak_test import AlignakTest


class TestDependencies(AlignakTest):
    """
    This class test dependencies between services, hosts
    """

    def test_conf_dependencies(self):
        """
        Test dependencies right loaded from config files

        :return: None
        """
        self.setup_with_file('cfg/cfg_dependencies.cfg')

        # test_host_00 -> test_router_00
        test_host_00 = self.schedulers[0].sched.hosts.find_by_name("test_host_00")
        self.assertEqual(1, len(test_host_00.act_depend_of))
        for (host, _, n_type, _, _) in test_host_00.act_depend_of:
            self.assertEqual('network_dep', n_type)
            self.assertEqual(self.schedulers[0].sched.hosts[host].host_name, 'test_router_00')

        # test test_host_00.test_ok_1 -> test_host_00
        # test test_host_00.test_ok_1 -> test_host_00.test_ok_0
        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_00",
                                                                          "test_ok_1")
        for (dep_id, status, n_type, _, _) in svc.act_depend_of:
            if n_type == 'network_dep':
                self.assertEqual(self.schedulers[0].sched.hosts[dep_id].host_name, 'test_host_00')
            elif n_type == 'logic_dep':
                self.assertEqual(self.schedulers[0].sched.services[dep_id].service_description,
                                 'test_ok_0')

        # test test_host_C -> test_host_A
        # test test_host_C -> test_host_B
        test_host_c = self.schedulers[0].sched.hosts.find_by_name("test_host_C")
        self.assertEqual(2, len(test_host_c.act_depend_of))
        hosts = []
        for (host, _, n_type, _, _) in test_host_c.act_depend_of:
            hosts.append(self.schedulers[0].sched.hosts[host].host_name)
            self.assertEqual('logic_dep', n_type)
        self.assertItemsEqual(hosts, ['test_host_A', 'test_host_B'])

        # test test_host_E -> test_host_D
        test_host_e = self.schedulers[0].sched.hosts.find_by_name("test_host_E")
        self.assertEqual(1, len(test_host_e.act_depend_of))
        for (host, _, _, _, _) in test_host_e.act_depend_of:
            self.assertEqual(self.schedulers[0].sched.hosts[host].host_name, 'test_host_D')

        # test test_host_11.test_parent_svc -> test_host_11.test_son_svc
        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_11",
                                                                          "test_parent_svc")
        for (dep_id, status, n_type, _, _) in svc.act_depend_of:
            if n_type == 'network_dep':
                self.assertEqual(self.schedulers[0].sched.hosts[dep_id].host_name, 'test_host_11')
            elif n_type == 'logic_dep':
                self.assertEqual(self.schedulers[0].sched.services[dep_id].service_description,
                                 'test_son_svc')

        # test test_host_11.test_ok_1 -> test_host_11.test_ok_0
        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_11",
                                                                          "test_ok_1")
        for (dep_id, status, n_type, _, _) in svc.act_depend_of:
            if n_type == 'network_dep':
                self.assertEqual(self.schedulers[0].sched.hosts[dep_id].host_name, 'test_host_11')
            elif n_type == 'logic_dep':
                self.assertEqual(self.schedulers[0].sched.services[dep_id].service_description,
                                 'test_ok_0')

    def test_conf_notright1(self):
        """
        Test arbiter give an error when have an orphan dependency in config files
        in hostdependency dependent_host_name unknown

        :return: None
        """
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/cfg_dependencies_bad1.cfg')

    def test_conf_notright2(self):
        """
        Test arbiter give an error when have an orphan dependency in config files
        in hostdependency host_name unknown

        :return: None
        """
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/cfg_dependencies_bad2.cfg')

    def test_conf_notright3(self):
        """
        Test arbiter give an error when have an orphan dependency in config files
        in host definition, parent unknown

        :return: None
        """
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/cfg_dependencies_bad3.cfg')

    def test_conf_notright4(self):
        """
        Test arbiter give an error when have an orphan dependency in config files
        in servicedependency, dependent_service_description unknown

        :return: None
        """
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/cfg_dependencies_bad4.cfg')

    def test_conf_notright5(self):
        """
        Test arbiter give an error when have an orphan dependency in config files
        in servicedependency, dependent_host_name unknown

        :return: None
        """
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/cfg_dependencies_bad5.cfg')

    def test_conf_notright6(self):
        """
        Test arbiter give an error when have an orphan dependency in config files
        in servicedependency, host_name unknown

        :return: None
        """
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/cfg_dependencies_bad6.cfg')

    def test_conf_notright7(self):
        """
        Test arbiter give an error when have an orphan dependency in config files
        in servicedependency, service_description unknown

        :return: None
        """
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/cfg_dependencies_bad7.cfg')

    def test_service_host_case_1(self):
        """
        Test dependency (checks and notifications) between the service and the host (case 1)

        08:00:00 check_host OK HARD
        08:01:30 check_service CRITICAL SOFT
        => host check planned

        08:02:30 check_service CRITICAL HARD

        :return: None
        """
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        # delete schedule
        del self.schedulers[0].sched.recurrent_works[1]

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_00")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_00",
                                                                          "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("SOFT", svc.state_type)
        self.assertEqual(0, svc.current_notification_number, 'Critical SOFT, no notifications')
        self.assert_actions_count(0)
        self.assert_checks_count(1)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_host_00', 'command')

    def test_host_host(self):
        """
        Test the dependency between 2 hosts

        :return: None
        """
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        # delete schedule
        del self.schedulers[0].sched.recurrent_works[1]

        host_00 = self.schedulers[0].sched.hosts.find_by_name("test_host_00")
        host_00.checks_in_progress = []
        host_00.event_handler_enabled = False

        router_00 = self.schedulers[0].sched.hosts.find_by_name("test_router_00")
        router_00.checks_in_progress = []
        router_00.event_handler_enabled = False

        self.scheduler_loop(1, [[host_00, 0, 'UP'], [router_00, 0, 'UP']])
        time.sleep(0.1)
        self.assert_actions_count(0)
        self.assert_checks_count(0)

        self.scheduler_loop(1, [[host_00, 2, 'DOWN']])
        time.sleep(0.1)
        self.assert_actions_count(0)
        self.assert_checks_count(1)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_00', 'command')

    def test_service_host_host(self):
        """
        Test the dependencies between host -> host -> host

        :return: None
        """
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        # delete schedule
        del self.schedulers[0].sched.recurrent_works[1]

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_00")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_00",
                                                                          "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("SOFT", svc.state_type)
        self.assertEqual(0, svc.current_notification_number, 'Critical SOFT, no notifications')
        self.assert_actions_count(0)
        self.assert_checks_count(1)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_host_00', 'command')

        self.scheduler_loop(1, [[host, 2, 'DOWN']], False)
        time.sleep(0.1)
        self.assert_checks_count(1)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_00', 'command')

        router_00 = self.schedulers[0].sched.hosts.find_by_name("test_router_00")
        self.scheduler_loop(1, [[router_00, 2, 'DOWN']], False)
        time.sleep(0.1)
        self.assert_checks_count(0)

    def test_multi_services(self):
        """
        Test when have multiple services dependency the host

        :return: None
        """
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        # delete schedule
        del self.schedulers[0].sched.recurrent_works[1]

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_00")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        svc1 = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_00",
                                                                           "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc1.notification_interval = 0.001
        svc1.checks_in_progress = []
        svc1.event_handler_enabled = False

        svc2 = self.schedulers[0].sched.services.find_srv_by_name_and_hostname(
            "test_host_00", "test_ok_0_disbld_hst_dep")
        # To make tests quicker we make notifications send very quickly
        svc2.notification_interval = 0.001
        svc2.checks_in_progress = []
        svc2.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc1, 0, 'OK'], [svc2, 0, 'OK']], False)
        time.sleep(0.1)
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc1, 0, 'OK'], [svc2, 0, 'OK']], False)
        time.sleep(0.1)
        self.assertEqual("HARD", svc1.state_type)
        self.assertEqual("OK", svc1.state)
        self.assertEqual("HARD", svc2.state_type)
        self.assertEqual("OK", svc2.state)
        self.assertEqual("HARD", host.state_type)
        self.assertEqual("UP", host.state)
        self.assert_actions_count(0)
        self.assert_checks_count(0)

        self.scheduler_loop(1, [[svc1, 2, 'CRITICAL'], [svc2, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(0)
        self.assert_checks_count(1)
        self.assertEqual("UP", host.state)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_host_00', 'command')

    def test_passive_service_not_check_passive_host(self):
        """
        Test passive service critical not check the dependent host (passive)

        :return: None
        """
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.schedulers[0].sched.update_recurrent_works_tick('check_freshness', 1)

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_E")
        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_E",
                                                                          "test_ok_0")

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])

        time.sleep(0.1)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']], False)
        self.assert_actions_count(0)
        self.assert_checks_count(0)

    def test_passive_service_check_active_host(self):
        """
        Test passive service critical check the dependent host (active)

        :return: None
        """
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.schedulers[0].sched.update_recurrent_works_tick('check_freshness', 1)

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_00")
        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_00",
                                                                          "test_passive_0")

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])

        time.sleep(0.1)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']], False)
        self.assert_actions_count(0)
        self.assert_checks_count(1)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_host_00', 'command')

    def test_multi_hosts(self):
        """
        Test when have multiple hosts dependency the host
        test_host_00 and test_host_11 depends on test_router_0

        :return: None
        """
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        # delete schedule
        del self.schedulers[0].sched.recurrent_works[1]

        host_00 = self.schedulers[0].sched.hosts.find_by_name("test_host_00")
        host_00.checks_in_progress = []
        host_00.event_handler_enabled = False

        host_11 = self.schedulers[0].sched.hosts.find_by_name("test_host_11")
        host_11.checks_in_progress = []
        host_11.event_handler_enabled = False

        router_00 = self.schedulers[0].sched.hosts.find_by_name("test_router_00")
        router_00.checks_in_progress = []
        router_00.event_handler_enabled = False

        self.scheduler_loop(1, [[host_00, 0, 'UP'], [host_11, 0, 'UP'], [router_00, 0, 'UP']],
                            False)
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_00, 0, 'UP'], [host_11, 0, 'UP'], [router_00, 0, 'UP']],
                            False)
        time.sleep(0.1)
        self.assertEqual("HARD", host_00.state_type)
        self.assertEqual("UP", host_00.state)
        self.assertEqual("HARD", host_11.state_type)
        self.assertEqual("UP", host_11.state)
        self.assertEqual("HARD", router_00.state_type)
        self.assertEqual("UP", router_00.state)

        self.scheduler_loop(1, [[host_00, 2, 'DOWN'], [host_11, 2, 'DOWN']], False)
        time.sleep(0.1)
        self.assert_checks_count(1)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_00', 'command')
