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
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Frédéric MOHIER, frederic.mohier@ipmfrance.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Gerhard Lausser, gerhard.lausser@consol.de

#  This file is part of Shinken.
#
#  Shinken is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Shinken is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Shinken.  If not, see <http://www.gnu.org/licenses/>.

#
# This file is used to test reading and processing of config files
#
import time
import ujson
from alignak_test import AlignakTest, time_hacker
from alignak.external_command import ExternalCommand, ExternalCommandManager
from alignak.daemons.receiverdaemon import Receiver


class TestExternalCommandsPassiveChecks(AlignakTest):
    """
    This class tests the external commands
    """
    def setUp(self):
        """
        For each test load and check the configuration
        :return: None
        """
        self.setup_with_file('cfg/cfg_external_commands.cfg')
        self.assertTrue(self.conf_is_correct)

        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

        time_hacker.set_real_time()

    def test_passive_checks_active_passive(self):
        """
        Test passive host/service checks as external commands

        Hosts and services are active/passive checks enabled
        :return:
        """
        # Get host
        host = self.schedulers[0].sched.hosts.find_by_name('test_host_0')
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.active_checks_enabled = True
        host.passive_checks_enabled = True
        print("Host: %s - state: %s/%s" % (host, host.state_type, host.state))
        self.assertIsNotNone(host)

        # Get dependent host
        router = self.schedulers[0].sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.event_handler_enabled = False
        router.active_checks_enabled = True
        router.passive_checks_enabled = True
        print("Router: %s - state: %s/%s" % (router, router.state_type, router.state))
        self.assertIsNotNone(router)

        # Get service
        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.event_handler_enabled = False
        svc.active_checks_enabled = True
        svc.passive_checks_enabled = True
        self.assertIsNotNone(svc)
        print("Service: %s - state: %s/%s" % (svc, svc.state_type, svc.state))

        # Active checks to set an initial state
        # ---------------------------------------------
        # Set host as UP and its service as CRITICAL
        self.scheduler_loop_new(1, [[host, 0, 'Host is UP | value1=1 value2=2']])
        self.assert_checks_count(2)
        self.show_checks()
        # Prepared a check for the service and the router
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assert_checks_match(1, 'servicedesc test_ok_0', 'command')
        self.assertEqual('UP', host.state)
        self.assertEqual('HARD', host.state_type)

        self.scheduler_loop_new(1, [[svc, 2, 'Service is CRITICAL | value1=0 value2=0']])
        self.assert_checks_count(2)
        self.show_checks()
        # Prepared a check for the host and the router
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assertEqual('CRITICAL', svc.state)
        self.assertEqual('SOFT', svc.state_type)

        # Passive checks for hosts
        # ---------------------------------------------
        # Receive passive host check Down
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is UP' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('DOWN', host.state)
        self.assertEqual('Host is UP', host.output)

        # Receive passive host check Unreachable
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;1;Host is Unreachable' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        # Considerd as UP
        # TODO: to be explained!!!
        self.assertEqual('UP', host.state)
        self.assertEqual('Host is Unreachable', host.output)

        # Receive passive host check Up
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('UP', host.state)
        self.assertEqual('Host is UP', host.output)

        # Passive checks with performance data
        # ---------------------------------------------
        # Now with performance data
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP|rtt=9999' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('UP', host.state)
        self.assertEqual('Host is UP', host.output)
        self.assertEqual('rtt=9999', host.perf_data)

        # Now with full-blown performance data. Here we have to watch out:
        # Is a ";" a separator for the external command or is it
        # part of the performance data?
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP|rtt=9999;5;10;0;10000' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('UP', host.state)
        self.assertEqual('Host is UP', host.output)
        self.assertEqual('rtt=9999;5;10;0;10000', host.perf_data)

        # Passive checks for services
        # ---------------------------------------------
        # Receive passive service check Warning
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;1;Service is WARNING' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('WARNING', svc.state)
        self.assertEqual('Service is WARNING', svc.output)
        self.assertEqual(False, svc.problem_has_been_acknowledged)

        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;Acknowledge service' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('WARNING', svc.state)
        self.assertEqual(True, svc.problem_has_been_acknowledged)

        # Remove acknowledge service
        excmd = '[%d] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;test_ok_0' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('WARNING', svc.state)
        self.assertEqual(False, svc.problem_has_been_acknowledged)

        # Receive passive service check Critical
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;2;Service is CRITICAL' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('CRITICAL', svc.state)
        self.assertEqual('Service is CRITICAL', svc.output)
        self.assertEqual(False, svc.problem_has_been_acknowledged)

        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;Acknowledge service' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('CRITICAL', svc.state)
        self.assertEqual(True, svc.problem_has_been_acknowledged)

        # Service is going ok ...
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;0;Service is OK' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('OK', svc.state)
        self.assertEqual('Service is OK', svc.output)
        # Acknowledge disappeared because service went OK
        self.assertEqual(False, svc.problem_has_been_acknowledged)

        # Passive checks for hosts - special case
        # ---------------------------------------------
        # With timestamp in the past (- 30 seconds)
        # The check is accepted
        past = int(time.time() - 30)
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Router is Down' % past
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('DOWN', router.state)
        self.assertEqual('Router is Down', router.output)
        self.assertEqual(router.last_chk, past)

        # With timestamp in the past (- 3600 seconds)
        # The check is not be accepted
        very_past = int(time.time() - 3600)
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;0;Router is Up' % very_past
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        # Router do not change state!
        self.assertEqual('DOWN', router.state)
        self.assertEqual('Router is Down', router.output)
        self.assertEqual(router.last_chk, past)

        # Now with crappy characters, like é
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Output contains crappy character  èàçé   and spaces|rtt=9999' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('DOWN', router.state)
        self.assertEqual(u'Output contains crappy character  èàçé   and spaces', router.output)
        self.assertEqual('rtt=9999', router.perf_data)
        self.assertEqual(False, router.problem_has_been_acknowledged)

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        self.assertEqual('DOWN', router.state)
        self.assertEqual(True, router.problem_has_been_acknowledged)

        # Remove acknowledge router
        excmd = '[%d] REMOVE_HOST_ACKNOWLEDGEMENT;test_router_0' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        self.assertEqual('DOWN', router.state)
        self.assertEqual(False, router.problem_has_been_acknowledged)

        # Router is Down
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Router is Down' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('DOWN', router.state)
        self.assertEqual('Router is Down', router.output)
        # TODO: to be confirmed ... host should be unreachable because of its dependency with router
        # self.assertEqual('DOWN', host.state)
        # self.assertEqual('Router is Down', router.output)
        # self.assertEqual(router.last_chk, past)

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        self.assertEqual('DOWN', router.state)
        self.assertEqual(True, router.problem_has_been_acknowledged)

        # Router is now Up
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;0;Router is Up' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('UP', router.state)
        self.assertEqual('Router is Up', router.output)
        # Acknowledge disappeared because host went OK
        self.assertEqual(False, router.problem_has_been_acknowledged)

    def test_passive_checks_only_passively_checked(self):
        """
        Test passive host/service checks as external commands

        Hosts and services are only passive checks enabled
        :return:
        """
        # Get host
        host = self.schedulers[0].sched.hosts.find_by_name('test_host_0')
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.active_checks_enabled = True
        host.passive_checks_enabled = True
        print("Host: %s - state: %s/%s" % (host, host.state_type, host.state))
        self.assertIsNotNone(host)

        # Get dependent host
        router = self.schedulers[0].sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.event_handler_enabled = False
        router.active_checks_enabled = True
        router.passive_checks_enabled = True
        print("Router: %s - state: %s/%s" % (router, router.state_type, router.state))
        self.assertIsNotNone(router)

        # Get service
        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.event_handler_enabled = False
        svc.active_checks_enabled = True
        svc.passive_checks_enabled = True
        self.assertIsNotNone(svc)
        print("Service: %s - state: %s/%s" % (svc, svc.state_type, svc.state))


        # Passive checks for hosts
        # ---------------------------------------------
        # Receive passive host check Down
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is UP' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('DOWN', host.state)
        self.assertEqual('Host is UP', host.output)

        # Receive passive host check Unreachable
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;1;Host is Unreachable' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        # Considerd as UP
        # TODO: to be explained!!!
        self.assertEqual('UP', host.state)
        self.assertEqual('Host is Unreachable', host.output)

        # Receive passive host check Up
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('UP', host.state)
        self.assertEqual('Host is UP', host.output)

        # Passive checks with performance data
        # ---------------------------------------------
        # Now with performance data
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP|rtt=9999' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('UP', host.state)
        self.assertEqual('Host is UP', host.output)
        self.assertEqual('rtt=9999', host.perf_data)

        # Now with full-blown performance data. Here we have to watch out:
        # Is a ";" a separator for the external command or is it
        # part of the performance data?
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP|rtt=9999;5;10;0;10000' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('UP', host.state)
        self.assertEqual('Host is UP', host.output)
        self.assertEqual('rtt=9999;5;10;0;10000', host.perf_data)

        # Passive checks for services
        # ---------------------------------------------
        # Receive passive service check Warning
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;1;Service is WARNING' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('WARNING', svc.state)
        self.assertEqual('Service is WARNING', svc.output)
        self.assertEqual(False, svc.problem_has_been_acknowledged)

        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;Acknowledge service' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('WARNING', svc.state)
        self.assertEqual(True, svc.problem_has_been_acknowledged)

        # Remove acknowledge service
        excmd = '[%d] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;test_ok_0' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('WARNING', svc.state)
        self.assertEqual(False, svc.problem_has_been_acknowledged)

        # Receive passive service check Critical
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;2;Service is CRITICAL' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('CRITICAL', svc.state)
        self.assertEqual('Service is CRITICAL', svc.output)
        self.assertEqual(False, svc.problem_has_been_acknowledged)

        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;Acknowledge service' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('CRITICAL', svc.state)
        self.assertEqual(True, svc.problem_has_been_acknowledged)

        # Service is going ok ...
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;0;Service is OK|rtt=9999;5;10;0;10000' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('OK', svc.state)
        self.assertEqual('Service is OK', svc.output)
        self.assertEqual('rtt=9999;5;10;0;10000', svc.perf_data)
        # Acknowledge disappeared because service went OK
        self.assertEqual(False, svc.problem_has_been_acknowledged)

        # Passive checks for hosts - special case
        # ---------------------------------------------
        # With timestamp in the past (- 30 seconds)
        # The check is accepted
        past = int(time.time() - 30)
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Router is Down' % past
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('DOWN', router.state)
        self.assertEqual('Router is Down', router.output)
        self.assertEqual(router.last_chk, past)

        # With timestamp in the past (- 3600 seconds)
        # The check is not be accepted
        very_past = int(time.time() - 3600)
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;0;Router is Up' % very_past
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        # Router do not change state!
        self.assertEqual('DOWN', router.state)
        self.assertEqual('Router is Down', router.output)
        self.assertEqual(router.last_chk, past)

        # Now with crappy characters, like é
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Output contains crappy ' \
                'character  èàçé   and spaces|rtt=9999' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('DOWN', router.state)
        self.assertEqual(u'Output contains crappy character  èàçé   and spaces', router.output)
        self.assertEqual('rtt=9999', router.perf_data)
        self.assertEqual(False, router.problem_has_been_acknowledged)

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        self.assertEqual('DOWN', router.state)
        self.assertEqual(True, router.problem_has_been_acknowledged)

        # Remove acknowledge router
        excmd = '[%d] REMOVE_HOST_ACKNOWLEDGEMENT;test_router_0' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        self.assertEqual('DOWN', router.state)
        self.assertEqual(False, router.problem_has_been_acknowledged)

        # Router is Down
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Router is Down' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('DOWN', router.state)
        self.assertEqual('Router is Down', router.output)
        # TODO: to be confirmed ... host should be unreachable because of its dependency with router
        # self.assertEqual('DOWN', host.state)
        # self.assertEqual('Router is Down', router.output)
        # self.assertEqual(router.last_chk, past)

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        self.assertEqual('DOWN', router.state)
        self.assertEqual(True, router.problem_has_been_acknowledged)

        # Router is now Up
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;0;Router is Up' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('UP', router.state)
        self.assertEqual('Router is Up', router.output)
        # Acknowledge disappeared because host went OK
        self.assertEqual(False, router.problem_has_been_acknowledged)

    def test_unknown_check_result_command_scheduler(self):
        """
        Unknown check results commands managed by the scheduler
        :return:
        """
        # The scheduler accepts unknown passive checks...
        self.schedulers[0].sched.conf.accept_passive_unknown_check_results = True

        # Sched receives known host but unknown service service_check_result
        self.schedulers[0].sched.broks.clear()
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;unknownservice;1;' \
                'Service is WARNING|rtt=9999;5;10;0;10000' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        # A brok...
        broks = [b for b in self.schedulers[0].sched.broks.values()
                 if b.type == 'unknown_service_check_result']
        self.assertTrue(len(broks) == 1)
        # ...but no logs
        self.assertEqual(0, self.count_logs(scheduler=True))

        # Sched receives unknown host and service service_check_result
        self.schedulers[0].sched.broks.clear()
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;unknownhost;unknownservice;1;' \
                'Service is WARNING|rtt=9999;5;10;0;10000' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        # A brok...
        broks = [b for b in self.schedulers[0].sched.broks.values()
                 if b.type == 'unknown_service_check_result']
        self.assertTrue(len(broks) == 1)
        # ...but no logs
        self.assertEqual(0, self.count_logs(scheduler=True))

        # Sched receives unknown host host_check_result
        self.schedulers[0].sched.broks.clear()
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;unknownhost;' \
                '1;Host is UP|rtt=9999;5;10;0;10000' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        # A brok...
        broks = [b for b in self.schedulers[0].sched.broks.values()
                 if b.type == 'unknown_host_check_result']
        self.assertTrue(len(broks) == 1)
        # ...but no logs
        self.assertEqual(0, self.count_logs(scheduler=True))

        # -----------------------------------------------------------------------------------------
        # Now turn it off...
        self.schedulers[0].sched.conf.accept_passive_unknown_check_results = False

        # Sched receives known host but unknown service service_check_result
        self.schedulers[0].sched.broks.clear()
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;unknownservice;1;' \
                'Service is WARNING|rtt=9999;5;10;0;10000' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        # No brok...
        broks = [b for b in self.schedulers[0].sched.broks.values()
                 if b.type == 'unknown_service_check_result']
        self.assertTrue(len(broks) == 0)
        # ...but a log
        self.show_logs(scheduler=True)
        self.assert_log_match(1, 'A command was received for service .* '
                                 'on host .*, but the service could not be found!', scheduler=True)
        self.clear_logs(scheduler=True)

        # Sched receives unknown host and service service_check_result
        self.schedulers[0].sched.broks.clear()
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;unknownhost;unknownservice;1;' \
                'Service is WARNING|rtt=9999;5;10;0;10000' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        # No brok...
        broks = [b for b in self.schedulers[0].sched.broks.values()
                 if b.type == 'unknown_service_check_result']
        self.assertTrue(len(broks) == 0)
        # ...but a log
        self.show_logs(scheduler=True)
        self.assert_log_match(1, 'A command was received for service .* '
                                 'on host .*, but the service could not be found!', scheduler=True)
        self.clear_logs(scheduler=True)

        # Sched receives unknown host host_check_result
        self.schedulers[0].sched.broks.clear()
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;unknownhost;' \
                '1;Host is UP|rtt=9999;5;10;0;10000' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        # No brok...
        broks = [b for b in self.schedulers[0].sched.broks.values()
                 if b.type == 'unknown_host_check_result']
        self.assertTrue(len(broks) == 0)
        # ...but a log
        self.show_logs(scheduler=True)
        self.assert_log_match(1, 'A command was received for an host .*, '
                                 'but the host could not be found!', scheduler=True)
        self.clear_logs(scheduler=True)

    def test_unknown_check_result_command_receiver(self):
        """
        Unknown check results commands managed by the receiver
        :return:
        """
        receiverdaemon = Receiver(None, False, False, False, None)
        receiverdaemon.direct_routing = True
        receiverdaemon.accept_passive_unknown_check_results = True

        # Receiver receives unknown host external command
        excmd = ExternalCommand('[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;unknownservice;'
                                '1;Service is WARNING|rtt=9999;5;10;0;10000' % time.time())
        receiverdaemon.unprocessed_external_commands.append(excmd)
        receiverdaemon.push_external_commands_to_schedulers()
        # A brok...
        broks = [b for b in receiverdaemon.broks.values()
                 if b.type == 'unknown_service_check_result']
        self.assertEqual(len(broks), 1)
        # ...but no logs!
        self.show_logs(scheduler=True)
        self.assert_no_log_match('Passive check result was received for host .*, '
                                 'but the host could not be found!', scheduler=True)
        # self.assert_any_log_match('Receiver searching for a scheduler '
        #                           'for the external command ', scheduler=True)
        self.clear_logs(scheduler=True)

        # now turn it off...
        receiverdaemon.accept_passive_unknown_check_results = False

        excmd = ExternalCommand('[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;unknownservice;'
                                '1;Service is WARNING|rtt=9999;5;10;0;10000' % time.time())
        receiverdaemon.unprocessed_external_commands.append(excmd)
        receiverdaemon.push_external_commands_to_schedulers()
        receiverdaemon.broks.clear()
        # No brok...
        broks = [b for b in receiverdaemon.broks.values()
                 if b.type == 'unknown_service_check_result']
        self.assertEqual(len(broks), 0)
        # ...but a log
        self.show_logs(scheduler=True)
        self.assert_any_log_match('Passive check result was received for host .*, '
                                  'but the host could not be found!', scheduler=True)
        # self.assert_any_log_match('Receiver searching for a scheduler '
        #                           'for the external command ', scheduler=True)
        self.clear_logs(scheduler=True)

    def test_unknown_check_result_brok(self):
        """
        Unknown check results commands in broks
        :return:
        """
        # unknown_host_check_result_brok
        excmd = '[1234567890] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is UP'
        expected = {'time_stamp': 1234567890, 'return_code': '2', 'host_name': 'test_host_0',
                    'output': 'Host is UP', 'perf_data': None}
        result = ujson.loads(ExternalCommandManager.get_unknown_check_result_brok(excmd).data)
        self.assertEqual(expected, result)

        # unknown_host_check_result_brok with perfdata
        excmd = '[1234567890] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is UP|rtt=9999'
        expected = {'time_stamp': 1234567890, 'return_code': '2', 'host_name': 'test_host_0',
                    'output': 'Host is UP', 'perf_data': 'rtt=9999'}
        result = ujson.loads(ExternalCommandManager.get_unknown_check_result_brok(excmd).data)
        self.assertEqual(expected, result)

        # unknown_service_check_result_brok
        excmd = '[1234567890] PROCESS_HOST_CHECK_RESULT;host-checked;0;Everything OK'
        expected = {'time_stamp': 1234567890, 'return_code': '0', 'host_name': 'host-checked',
                    'output': 'Everything OK', 'perf_data': None}
        result = ujson.loads(ExternalCommandManager.get_unknown_check_result_brok(excmd).data)
        self.assertEqual(expected, result)

        # unknown_service_check_result_brok with perfdata
        excmd = '[1234567890] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;1;Service is WARNING|rtt=9999;5;10;0;10000'
        expected = {'host_name': 'test_host_0', 'time_stamp': 1234567890,
                    'service_description': 'test_ok_0', 'return_code': '1',
                    'output': 'Service is WARNING', 'perf_data': 'rtt=9999;5;10;0;10000'}
        result = ujson.loads(ExternalCommandManager.get_unknown_check_result_brok(excmd).data)
        self.assertEqual(expected, result)

    def test_services_acknowledge(self):
        """
        Test services acknowledge
        :return:
        """
        # Get host
        host = self.schedulers[0].sched.hosts.find_by_name('test_host_0')
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.active_checks_enabled = True
        host.passive_checks_enabled = True
        print("Host: %s - state: %s/%s" % (host, host.state_type, host.state))
        self.assertIsNotNone(host)
    
        # Get dependent host
        router = self.schedulers[0].sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.event_handler_enabled = False
        router.active_checks_enabled = True
        router.passive_checks_enabled = True
        print("Router: %s - state: %s/%s" % (router, router.state_type, router.state))
        self.assertIsNotNone(router)

        # Get service
        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.event_handler_enabled = False
        svc.active_checks_enabled = True
        svc.passive_checks_enabled = True
        self.assertIsNotNone(svc)
        print("Service: %s - state: %s/%s" % (svc, svc.state_type, svc.state))
    
        # Passive checks for services
        # ---------------------------------------------
        # Receive passive service check Warning
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;1;Service is WARNING' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('WARNING', svc.state)
        self.assertEqual('Service is WARNING', svc.output)
        self.assertEqual(False, svc.problem_has_been_acknowledged)
    
        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;Acknowledge service' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('WARNING', svc.state)
        self.assertEqual(True, svc.problem_has_been_acknowledged)

        # Add a comment
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;Acknowledge service' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('WARNING', svc.state)
        self.assertEqual(True, svc.problem_has_been_acknowledged)

        # Remove acknowledge service
        excmd = '[%d] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;test_ok_0' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('WARNING', svc.state)
        self.assertEqual(False, svc.problem_has_been_acknowledged)
    
        # Receive passive service check Critical
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;2;Service is CRITICAL' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('CRITICAL', svc.state)
        self.assertEqual('Service is CRITICAL', svc.output)
        self.assertEqual(False, svc.problem_has_been_acknowledged)
    
        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;Acknowledge service' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('CRITICAL', svc.state)
        self.assertEqual(True, svc.problem_has_been_acknowledged)
    
        # Service is going ok ...
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;0;Service is OK' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('OK', svc.state)
        self.assertEqual('Service is OK', svc.output)
        # Acknowledge disappeared because service went OK
        self.assertEqual(False, svc.problem_has_been_acknowledged)

    def test_hosts_checks(self):
        """
        Test hosts checks
        :return:
        """
        # Get host
        host = self.schedulers[0].sched.hosts.find_by_name('test_host_0')
        host.checks_in_progress = []
        host.event_handler_enabled = False
        print("Host: %s - state: %s/%s" % (host, host.state_type, host.state))
        self.assertIsNotNone(host)

        # Get dependent host
        router = self.schedulers[0].sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.event_handler_enabled = False
        print("Router: %s - state: %s/%s" % (router, router.state_type, router.state))
        self.assertIsNotNone(router)

        # Get service
        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.event_handler_enabled = False
        svc.active_checks_enabled = True
        svc.passive_checks_enabled = True
        self.assertIsNotNone(svc)
        print("Service: %s - state: %s/%s" % (svc, svc.state_type, svc.state))

        # Passive checks for hosts - active only checks
        # ------------------------------------------------
        host.active_checks_enabled = True
        host.passive_checks_enabled = False     # Disabled
        router.active_checks_enabled = True
        router.passive_checks_enabled = False   # Disabled
        # Host is DOWN
        # Set active host as DOWN
        self.scheduler_loop_new(1, [[host, 2, 'Host is DOWN']])
        # excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is DOWN' % int(time.time())
        # self.schedulers[0].sched.run_external_command(excmd)
        # self.external_command_loop()
        # New checks: test host, dependent host and service (because active checks are enabled)
        self.assert_checks_count(2)
        self.show_checks()
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assertEqual('DOWN', host.state)
        self.assertEqual(u'Host is DOWN', host.output)
        self.assertEqual(False, host.problem_has_been_acknowledged)

        # Host is UP
        # Set active host as DOWN
        self.scheduler_loop_new(1, [[host, 0, 'Host is UP']])
        # excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP' % int(time.time())
        # self.schedulers[0].sched.run_external_command(excmd)
        # self.external_command_loop()
        # New checks: test dependent host and service (because active checks are enabled)
        self.show_checks()
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assertEqual('UP', host.state)
        self.assertEqual(u'Host is UP', host.output)
        self.assertEqual(False, host.problem_has_been_acknowledged)

        # Passive checks for hosts - active/passive checks
        # ------------------------------------------------
        host.active_checks_enabled = True
        host.passive_checks_enabled = True
        router.active_checks_enabled = True
        router.passive_checks_enabled = True
        # Host is DOWN
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is DOWN' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        # New checks: test dependent host and service (because active checks are enabled)
        self.show_checks()
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assert_checks_match(1, 'servicedesc test_ok_0', 'command')
        self.assertEqual('DOWN', host.state)
        self.assertEqual(u'Host is DOWN', host.output)
        self.assertEqual(False, host.problem_has_been_acknowledged)

        # Host is UP
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        # New checks: test dependent host and service (because active checks are enabled)
        self.show_checks()
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assert_checks_match(1, 'servicedesc test_ok_0', 'command')
        self.assertEqual('UP', host.state)
        self.assertEqual(u'Host is UP', host.output)
        self.assertEqual(False, host.problem_has_been_acknowledged)

        # Passive checks for hosts - passive only checks
        # ------------------------------------------------
        # TODO: For hosts that are only passively checked, the scheduler should not create
        # new checks for the dependent services and should only create a check for an host
        # which we depend upon if this host is not only passively checked !
        # It does not seem logical to try checking actively elements that are passive only!
        host.active_checks_enabled = False      # Disabled
        host.passive_checks_enabled = True
        router.active_checks_enabled = False    # Disabled
        router.passive_checks_enabled = True
        # Host is DOWN
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is DOWN' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        # New checks: test dependent host and service (because active checks are enabled)
        # Should not have new checks scheduled because the host is only passively checked
        self.show_checks()
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assert_checks_match(1, 'servicedesc test_ok_0', 'command')
        self.assertEqual('DOWN', host.state)
        self.assertEqual(u'Host is DOWN', host.output)
        self.assertEqual(False, host.problem_has_been_acknowledged)

        # Host is UP
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        # New checks: test dependent host and service (because active checks are enabled)
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assert_checks_match(1, 'servicedesc test_ok_0', 'command')
        self.assertEqual('UP', host.state)
        self.assertEqual(u'Host is UP', host.output)
        self.assertEqual(False, host.problem_has_been_acknowledged)

    def test_hosts_acknowledge(self):
        """
        Test hosts acknowledge
        :return:
        """
        # Get host
        host = self.schedulers[0].sched.hosts.find_by_name('test_host_0')
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.active_checks_enabled = True
        host.passive_checks_enabled = True
        print("Host: %s - state: %s/%s" % (host, host.state_type, host.state))
        self.assertIsNotNone(host)

        # Get dependent host
        router = self.schedulers[0].sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.event_handler_enabled = False
        router.active_checks_enabled = True
        router.passive_checks_enabled = True
        print("Router: %s - state: %s/%s" % (router, router.state_type, router.state))
        self.assertIsNotNone(router)

        # Get service
        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.event_handler_enabled = False
        svc.active_checks_enabled = True
        svc.passive_checks_enabled = True
        self.assertIsNotNone(svc)
        print("Service: %s - state: %s/%s" % (svc, svc.state_type, svc.state))

        # Passive checks for hosts - special case
        # ---------------------------------------------
        # Host is DOWN
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Host is DOWN' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.show_checks()
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_host_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assert_checks_match(1, 'servicedesc test_ok_0', 'command')
        self.assertEqual('DOWN', router.state)
        self.assertEqual(u'Host is DOWN', router.output)
        self.assertEqual(False, router.problem_has_been_acknowledged)

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        self.assertEqual('DOWN', router.state)
        self.assertEqual(True, router.problem_has_been_acknowledged)
    
        # Remove acknowledge router
        excmd = '[%d] REMOVE_HOST_ACKNOWLEDGEMENT;test_router_0' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        self.assertEqual('DOWN', router.state)
        self.assertEqual(False, router.problem_has_been_acknowledged)

        # Host is DOWN
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Host is DOWN' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('DOWN', router.state)
        self.assertEqual(u'Host is DOWN', router.output)
        self.assertEqual(False, router.problem_has_been_acknowledged)

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        self.assertEqual('DOWN', router.state)
        self.assertEqual(True, router.problem_has_been_acknowledged)

        # Remove acknowledge router
        excmd = '[%d] REMOVE_HOST_ACKNOWLEDGEMENT;test_router_0' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        self.assertEqual('DOWN', router.state)
        self.assertEqual(False, router.problem_has_been_acknowledged)

        # Router is Down
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Router is Down' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('DOWN', router.state)
        self.assertEqual('Router is Down', router.output)

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        self.assertEqual('DOWN', router.state)
        self.assertEqual(True, router.problem_has_been_acknowledged)

        # Router is now Up
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;0;Router is Up' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual('UP', router.state)
        self.assertEqual('Router is Up', router.output)
        # Acknowledge disappeared because host went OK
        self.assertEqual(False, router.problem_has_been_acknowledged)
