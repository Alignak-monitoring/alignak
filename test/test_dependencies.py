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
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)
        self.assertEqual(len(self.configuration_errors), 0)
        self.assertEqual(len(self.configuration_warnings), 0)

        # test_host_00 -> test_router_00
        test_host_00 = self.arbiter.conf.hosts.find_by_name("test_host_00")
        self.assertEqual(1, len(test_host_00.act_depend_of))
        for (host, _, n_type, _, _) in test_host_00.act_depend_of:
            self.assertEqual('network_dep', n_type)
            self.assertEqual(self.arbiter.conf.hosts[host].host_name, 'test_router_00')

        # test test_host_00.test_ok_1 -> test_host_00
        # test test_host_00.test_ok_1 -> test_host_00.test_ok_0
        svc = self.arbiter.conf.services.find_srv_by_name_and_hostname("test_host_00",
                                                                              "test_ok_1")
        for (dep_id, _, n_type, _, _) in svc.act_depend_of:
            if n_type == 'network_dep':
                self.assertEqual(self.arbiter.conf.hosts[dep_id].host_name, 'test_host_00')
            elif n_type == 'logic_dep':
                self.assertEqual(self.arbiter.conf.services[dep_id].service_description,
                                 'test_ok_0')

        # test test_host_C -> test_host_A
        # test test_host_C -> test_host_B
        test_host_c = self.arbiter.conf.hosts.find_by_name("test_host_C")
        self.assertEqual(2, len(test_host_c.act_depend_of))
        hosts = []
        for (host, _, n_type, _, _) in test_host_c.act_depend_of:
            hosts.append(self.arbiter.conf.hosts[host].host_name)
            self.assertEqual('logic_dep', n_type)
        self.assertItemsEqual(hosts, ['test_host_A', 'test_host_B'])

        # test test_host_E -> test_host_D
        test_host_e = self.arbiter.conf.hosts.find_by_name("test_host_E")
        self.assertEqual(1, len(test_host_e.act_depend_of))
        for (host, _, _, _, _) in test_host_e.act_depend_of:
            self.assertEqual(self.arbiter.conf.hosts[host].host_name, 'test_host_D')

        # test test_host_11.test_parent_svc -> test_host_11.test_son_svc
        svc = self.arbiter.conf.services.find_srv_by_name_and_hostname("test_host_11",
                                                                              "test_parent_svc")
        for (dep_id, _, n_type, _, _) in svc.act_depend_of:
            if n_type == 'network_dep':
                self.assertEqual(self.arbiter.conf.hosts[dep_id].host_name, 'test_host_11')
            elif n_type == 'logic_dep':
                self.assertEqual(self.arbiter.conf.services[dep_id].service_description,
                                 'test_son_svc')

        # test test_host_11.test_ok_1 -> test_host_11.test_ok_0
        svc = self.arbiter.conf.services.find_srv_by_name_and_hostname("test_host_11",
                                                                              "test_ok_1")
        for (dep_id, _, n_type, _, _) in svc.act_depend_of:
            if n_type == 'network_dep':
                self.assertEqual(self.arbiter.conf.hosts[dep_id].host_name, 'test_host_11')
            elif n_type == 'logic_dep':
                self.assertEqual(self.arbiter.conf.services[dep_id].service_description,
                                 'test_ok_0')

    def test_conf_notright1(self):
        """
        Test that the arbiter raises an error when have an orphan dependency in config files
        in hostdependency, dependent_host_name is unknown

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/dependencies/cfg_dependencies_bad1.cfg')
        self.assertEqual(len(self.configuration_errors), 4)
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_conf_notright2(self):
        """
        Test that the arbiter raises an error when we have an orphan dependency in config files
        in hostdependency, host_name unknown

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/dependencies/cfg_dependencies_bad2.cfg')
        # TODO: improve test
        self.assertEqual(len(self.configuration_errors), 4)
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_conf_notright3(self):
        """
        Test that the arbiter raises an error when we have an orphan dependency in config files
        in host definition, the parent is unknown

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/dependencies/cfg_dependencies_bad3.cfg')
        self.assertEqual(len(self.configuration_errors), 2)
        self.assertEqual(len(self.configuration_warnings), 8)

    def test_conf_notright4(self):
        """
        Test that the arbiter raises an error when have an orphan dependency in config files
        in servicedependency, dependent_service_description is unknown

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/dependencies/cfg_dependencies_bad4.cfg')
        self.assertEqual(len(self.configuration_errors), 2)
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_conf_notright5(self):
        """
        Test that the arbiter raises an error when have an orphan dependency in config files
        in servicedependency, dependent_host_name is unknown

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/dependencies/cfg_dependencies_bad5.cfg')
        self.assertEqual(len(self.configuration_errors), 2)
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_conf_notright6(self):
        """
        Test that the arbiter raises an error when have an orphan dependency in config files
        in servicedependency, host_name unknown

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/dependencies/cfg_dependencies_bad6.cfg')
        self.assertEqual(len(self.configuration_errors), 2)
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_conf_notright7(self):
        """
        Test that the arbiter raises an error when have an orphan dependency in config files
        in servicedependency, service_description unknown

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/dependencies/cfg_dependencies_bad7.cfg')
        # Service test_ok_0_notknown not found for 2 hosts.
        self.assertEqual(len(self.configuration_errors), 3)
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_service_host_case_1(self):
        """
        Test dependency (checks and notifications) between the service and the host (case 1)

        08:00:00 check_host OK HARD
        08:01:30 check_service CRITICAL SOFT
        => host check planned

        08:02:30 check_service CRITICAL HARD

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)
        # delete schedule
        del self.schedulers['scheduler-master'].sched.recurrent_works[1]

        host = self.arbiter.conf.hosts.find_by_name("test_host_00")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        svc = self.arbiter.conf.services.find_srv_by_name_and_hostname("test_host_00",
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
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)

        host_00 = self.arbiter.conf.hosts.find_by_name("test_host_00")
        host_00.checks_in_progress = []
        host_00.event_handler_enabled = False

        router_00 = self.arbiter.conf.hosts.find_by_name("test_router_00")
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
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)
        # delete schedule
        del self.schedulers['scheduler-master'].sched.recurrent_works[1]

        router_00 = self.arbiter.conf.hosts.find_by_name("test_router_00")
        router_00.checks_in_progress = []
        router_00.event_handler_enabled = False

        host = self.arbiter.conf.hosts.find_by_name("test_host_00")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        svc = self.arbiter.conf.services.find_srv_by_name_and_hostname("test_host_00",
                                                                              "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.event_handler_enabled = False

        # Host is UP
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)

        # Service is CRITICAL
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("SOFT", svc.state_type)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual(0, svc.current_notification_number, 'Critical SOFT, no notifications')
        self.assert_actions_count(0)
        # New host check
        self.assert_checks_count(1)
        self.show_checks()
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_host_00', 'command')

        # Host is DOWN
        self.scheduler_loop(1, [[host, 2, 'DOWN']], reset_checks=True)
        time.sleep(0.1)
        # New dependent host check
        self.assert_checks_count(1)
        self.show_checks()
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_00', 'command')

        # Router is DOWN
        self.scheduler_loop(1, [[router_00, 2, 'DOWN']], False)
        time.sleep(0.1)
        # New router check
        self.assert_checks_count(1)
        self.show_checks()
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_00', 'command')

    def test_hostdep_withno_depname(self):
        """
        Test for host dependency dispatched on all hosts of an hostgroup
        1st solution: define a specific property (Shinken)
        2nd solution: define an hostgroup_name and do not define a dependent_hostgroup_name
        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/dependencies/hostdep_through_hostgroup.cfg')
        self.assertTrue(self.conf_is_correct)

        host0 = self.arbiter.conf.hosts.find_by_name("test_host_0")
        self.assertIsNotNone(host0)
        host1 = self.arbiter.conf.hosts.find_by_name("test_host_1")
        self.assertIsNotNone(host1)

        # Should got a link between host and h2
        self.assertGreater(len(host1.act_depend_of), 0)
        l = host1.act_depend_of[0]
        h = l[0]  # the host that h2 depend on
        self.assertIs(host0.uuid, h)

    def test_multi_services(self):
        """
        Test when have multiple services dependency the host

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)
        # delete schedule
        del self.schedulers['scheduler-master'].sched.recurrent_works[1]

        host = self.arbiter.conf.hosts.find_by_name("test_host_00")
        host.checks_in_progress = []
        host.event_handler_enabled = False

        svc1 = self.arbiter.conf.services.find_srv_by_name_and_hostname("test_host_00",
                                                                               "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc1.notification_interval = 0.001
        svc1.checks_in_progress = []
        svc1.event_handler_enabled = False

        svc2 = self.arbiter.conf.services.find_srv_by_name_and_hostname(
            "test_host_00", "test_ok_0_disbld_hst_dep")
        # To make tests quicker we make notifications send very quickly
        svc2.notification_interval = 0.001
        svc2.checks_in_progress = []
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
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)

        self.schedulers['scheduler-master'].sched.update_recurrent_works_tick('check_freshness', 1)

        host = self.arbiter.conf.hosts.find_by_name("test_host_E")
        svc = self.arbiter.conf.services.find_srv_by_name_and_hostname("test_host_E",
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
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)

        self.schedulers['scheduler-master'].sched.update_recurrent_works_tick('check_freshness', 1)

        host = self.arbiter.conf.hosts.find_by_name("test_host_00")
        svc = self.arbiter.conf.services.find_srv_by_name_and_hostname("test_host_00",
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
        self.print_header()
        self.setup_with_file('cfg/cfg_dependencies.cfg')
        self.assertTrue(self.conf_is_correct)

        # delete schedule
        del self.schedulers['scheduler-master'].sched.recurrent_works[1]

        host_00 = self.arbiter.conf.hosts.find_by_name("test_host_00")
        host_00.checks_in_progress = []
        host_00.event_handler_enabled = False

        host_11 = self.arbiter.conf.hosts.find_by_name("test_host_11")
        host_11.checks_in_progress = []
        host_11.event_handler_enabled = False

        router_00 = self.arbiter.conf.hosts.find_by_name("test_router_00")
        router_00.checks_in_progress = []
        router_00.event_handler_enabled = False

        self.scheduler_loop(1, [[host_00, 0, 'UP'], [host_11, 0, 'UP'], [router_00, 0, 'UP']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host_00, 0, 'UP'], [host_11, 0, 'UP'], [router_00, 0, 'UP']])
        time.sleep(0.1)
        self.assertEqual("HARD", host_00.state_type)
        self.assertEqual("UP", host_00.state)
        self.assertEqual("HARD", host_11.state_type)
        self.assertEqual("UP", host_11.state)
        self.assertEqual("HARD", router_00.state_type)
        self.assertEqual("UP", router_00.state)

        self.scheduler_loop(1, [[host_00, 2, 'DOWN'], [host_11, 2, 'DOWN']])
        time.sleep(0.1)
        # Check the parent of each DOWN host
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_00', 'command')
        self.assert_checks_match(1, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_router_00', 'command')

    def test_explodehostgroup(self):
        """
        Test for service dependencies dispatched on all hosts of an hostgroup
        1st solution: define a specific property (Shinken)
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

    def test_implicithostgroups(self):
        """
        All hosts in the hostgroup get the service dependencies. An host in the group can have
        its own services dependencies

        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/dependencies/servicedependency_implicit_hostgroup.cfg')
        self.assertTrue(self.conf_is_correct)

        # Services on host_0
        svc = self.schedulers['scheduler-master'].sched.services.\
            find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
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


        # TODO: check if it should be!
        # SNMP on the router is in the dependencies of POSFIX of the host ?
        # self.assertIn(svc_snmp2.uuid, [c[0] for c in svc_postfix.act_depend_of])
        self.assertIn(svc_snmp.uuid, [c[0] for c in svc_postfix.act_depend_of])
        # TODO: check if it should be!
        # SNMP on the router is in the dependencies of POSTIF on the host ?
        # self.assertIn(svc_snmp2.uuid, [c[0] for c in svc_cpu.act_depend_of])
        self.assertIn(svc_snmp.uuid, [c[0] for c in svc_cpu.act_depend_of])

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

    def test_complex_servicedependency(self):
        """
        All hosts in the hostgroup get the service dependencies. An host in the group can have
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
