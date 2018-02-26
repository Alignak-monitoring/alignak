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

#
# This file is used to test reading and processing of config files
#
import time
import ujson
import pytest
from alignak_test import AlignakTest
from alignak.external_command import ExternalCommand, ExternalCommandManager
from alignak.daemons.receiverdaemon import Receiver


class TestExternalCommandsPassiveChecks(AlignakTest):
    """
    This class tests the external commands for passive checks
    """
    def setUp(self):
        super(TestExternalCommandsPassiveChecks, self).setUp()

        self.setup_with_file('cfg/cfg_external_commands.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        self.show_configuration_logs()
        assert len(self.configuration_warnings) == 0

    def test_passive_checks_active_passive(self):
        """ Test passive host/service checks as external commands

        Hosts and services are active/passive checks enabled
        :return:
        """
        # Get host
        host = self._scheduler.hosts.find_by_name('test_host_0')
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.active_checks_enabled = True
        host.passive_checks_enabled = True
        print("Host: %s - state: %s/%s" % (host, host.state_type, host.state))
        assert host is not None

        # Get dependent host
        router = self._scheduler.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.event_handler_enabled = False
        router.active_checks_enabled = True
        router.passive_checks_enabled = True
        print("Router: %s - state: %s/%s" % (router, router.state_type, router.state))
        assert router is not None

        # Get service
        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # ignore the host which we depend of
        svc.event_handler_enabled = False
        svc.active_checks_enabled = True
        svc.passive_checks_enabled = True
        assert svc is not None
        print("Service: %s - state: %s/%s" % (svc, svc.state_type, svc.state))

        # Active checks to set an initial state
        # ---------------------------------------------
        # Set host as UP and its service as CRITICAL
        self.scheduler_loop(1, [[host, 0, 'Host is UP | value1=1 value2=2']])
        self.assert_checks_count(2)
        self.show_checks()
        # Prepared a check for the service and the router
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assert_checks_match(1, 'servicedesc test_ok_0', 'command')
        assert 'UP' == host.state
        assert 'HARD' == host.state_type

        self.scheduler_loop(1, [[svc, 2, 'Service is CRITICAL | value1=0 value2=0']])
        self.assert_checks_count(2)
        self.show_checks()
        # Prepared a check for the host and the router
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        assert 'CRITICAL' == svc.state
        assert 'SOFT' == svc.state_type

        # Passive checks for hosts
        # ---------------------------------------------
        # Receive passive host check Down
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is UP' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        self.scheduler_loop(1, [[router, 0, 'Host is UP']])
        assert 'DOWN' == host.state
        assert 'Host is UP' == host.output

        # Receive passive host check Unreachable
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;1;Host is Unreachable' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        self.scheduler_loop(1, [[router, 0, 'Host is UP']])
        assert 'DOWN' == host.state
        assert 'Host is Unreachable' == host.output

        # Receive passive host check Up
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'UP' == host.state
        assert 'Host is UP' == host.output

        # Passive checks with performance data
        # ---------------------------------------------
        # Now with performance data
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP|rtt=9999' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'UP' == host.state
        assert 'Host is UP' == host.output
        assert 'rtt=9999' == host.perf_data

        # Now with full-blown performance data. Here we have to watch out:
        # Is a ";" a separator for the external command or is it
        # part of the performance data?
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP|rtt=9999;5;10;0;10000' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'UP' == host.state
        assert 'Host is UP' == host.output
        assert 'rtt=9999;5;10;0;10000' == host.perf_data

        # Passive checks for services
        # ---------------------------------------------
        # Receive passive service check Warning
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;1;Service is WARNING' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'WARNING' == svc.state
        assert 'Service is WARNING' == svc.output
        assert False == svc.problem_has_been_acknowledged

        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;Acknowledge service' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'WARNING' == svc.state
        assert True == svc.problem_has_been_acknowledged

        # Remove acknowledge service
        excmd = '[%d] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'WARNING' == svc.state
        assert False == svc.problem_has_been_acknowledged

        # Receive passive service check Critical
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;2;Service is CRITICAL' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'CRITICAL' == svc.state
        assert 'Service is CRITICAL' == svc.output
        assert False == svc.problem_has_been_acknowledged

        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;Acknowledge service' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'CRITICAL' == svc.state
        assert True == svc.problem_has_been_acknowledged

        # Service is going ok ...
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;0;Service is OK' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'OK' == svc.state
        assert 'Service is OK' == svc.output
        # Acknowledge disappeared because service went OK
        assert False == svc.problem_has_been_acknowledged

        # Passive checks for hosts - special case
        # ---------------------------------------------
        # With timestamp in the past (before the last host check time!)
        # The check is ignored because too late in the past
        self.scheduler_loop(1, [[router, 0, 'Router is UP']])
        router_last_check = router.last_chk
        past = router_last_check - 30
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Router is Down' % past
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        # Router did not changed state!
        assert 'UP' == router.state
        assert 'Router is UP' == router.output
        router_last_check = router.last_chk

        # With timestamp in the past (- 1 seconds)
        # The check is accepted because it is equal or after the last host check
        time.sleep(2)
        past = router_last_check
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Router is Down' % past
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        # Router changed state!
        assert 'DOWN' == router.state
        assert 'Router is Down' == router.output
        assert router.last_chk == past

        # Now with crappy characters, like é
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Output contains crappy ' \
                'characters  èàçé   and spaces|rtt=9999' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'DOWN' == router.state
        assert u'Output contains crappy characters  èàçé   and spaces' == router.output
        assert 'rtt=9999' == router.perf_data
        assert False == router.problem_has_been_acknowledged

        # Now with utf-8 encoded data
        excmd = u'[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Output contains crappy ' \
                u'characters  èàçé   and spaces|rtt=9999' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'DOWN' == router.state
        assert u'Output contains crappy characters  èàçé   and spaces' == router.output
        assert 'rtt=9999' == router.perf_data
        assert False == router.problem_has_been_acknowledged

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        assert 'DOWN' == router.state
        assert True == router.problem_has_been_acknowledged

        # Remove acknowledge router
        excmd = '[%d] REMOVE_HOST_ACKNOWLEDGEMENT;test_router_0' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        assert 'DOWN' == router.state
        assert False == router.problem_has_been_acknowledged

        # Router is Down
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Router is Down' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'DOWN' == router.state
        assert 'Router is Down' == router.output

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        assert 'DOWN' == router.state
        assert True == router.problem_has_been_acknowledged

        # Router is now Up
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;0;Router is Up' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'UP' == router.state
        assert 'Router is Up' == router.output
        # Acknowledge disappeared because host went OK
        assert False == router.problem_has_been_acknowledged

    def test_passive_checks_only_passively_checked(self):
        """ Test passive host/service checks as external commands

        Hosts and services are only passive checks enabled
        :return:
        """
        # Get host
        host = self._scheduler.hosts.find_by_name('test_host_0')
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.active_checks_enabled = True
        host.passive_checks_enabled = True
        print("Host: %s - state: %s/%s" % (host, host.state_type, host.state))
        assert host is not None

        # Get dependent host
        router = self._scheduler.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.event_handler_enabled = False
        router.active_checks_enabled = True
        router.passive_checks_enabled = True
        print("Router: %s - state: %s/%s" % (router, router.state_type, router.state))
        assert router is not None

        # Get service
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.event_handler_enabled = False
        svc.active_checks_enabled = True
        svc.passive_checks_enabled = True
        assert svc is not None
        print("Service: %s - state: %s/%s" % (svc, svc.state_type, svc.state))


        # Passive checks for hosts
        # ---------------------------------------------
        # Receive passive host check Down
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is DOWN' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        self.scheduler_loop(1, [[router, 0, 'Host is UP']])
        assert 'DOWN' == host.state
        assert 'Host is DOWN' == host.output

        # Receive passive host check Unreachable
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;1;Host is Unreachable' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        self.scheduler_loop(1, [[router, 0, 'Router is UP']])
        assert 'DOWN' == host.state
        assert 'Host is Unreachable' == host.output
        router_last_check = router.last_chk

        # Receive passive host check Up
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'UP' == host.state
        assert 'Host is UP' == host.output

        # Passive checks with performance data
        # ---------------------------------------------
        # Now with performance data
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP|rtt=9999' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'UP' == host.state
        assert 'Host is UP' == host.output
        assert 'rtt=9999' == host.perf_data

        # Now with full-blown performance data. Here we have to watch out:
        # Is a ";" a separator for the external command or is it
        # part of the performance data?
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP|rtt=9999;5;10;0;10000' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'UP' == host.state
        assert 'Host is UP' == host.output
        assert 'rtt=9999;5;10;0;10000' == host.perf_data

        # Passive checks for services
        # ---------------------------------------------
        # Receive passive service check Warning
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;1;' \
                'Service is WARNING' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        self.scheduler_loop(1, [[host, 0, 'Host is UP']])
        assert 'WARNING' == svc.state
        assert 'Service is WARNING' == svc.output
        assert False == svc.problem_has_been_acknowledged

        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;' \
                'Acknowledge service' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'WARNING' == svc.state
        assert True == svc.problem_has_been_acknowledged

        # Remove acknowledge service
        excmd = '[%d] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'WARNING' == svc.state
        assert False == svc.problem_has_been_acknowledged

        # Receive passive service check Critical
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;2;' \
                'Service is CRITICAL' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        self.scheduler_loop(1, [[host, 0, 'Host is UP']])
        assert 'CRITICAL' == svc.state
        assert 'Service is CRITICAL' == svc.output
        assert False == svc.problem_has_been_acknowledged

        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;' \
                'Acknowledge service' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'CRITICAL' == svc.state
        assert True == svc.problem_has_been_acknowledged

        # Service is going ok ...
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;0;' \
                'Service is OK|rtt=9999;5;10;0;10000' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'OK' == svc.state
        assert 'Service is OK' == svc.output
        assert 'rtt=9999;5;10;0;10000' == svc.perf_data
        # Acknowledge disappeared because service went OK
        assert False == svc.problem_has_been_acknowledged

        # Passive checks for hosts - special case
        # ---------------------------------------------
        # With timestamp in the past (before the last host check time!)
        # The check is ignored because too late in the past
        past = router_last_check - 30
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Router is Down' % past
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'UP' == router.state
        assert 'Router is UP' == router.output

        # With timestamp in the past (- 1 seconds)
        # The check is accepted because it is equal or after the last host check
        time.sleep(2)
        past = router_last_check
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Router is Down' % past
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'DOWN' == router.state
        assert 'Router is Down' == router.output
        assert router.last_chk == past

        # With timestamp in the past (- 3600 seconds)
        # The check is not be accepted
        very_past = int(time.time() - 3600)
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;0;Router is Up' % very_past
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        # Router do not change state!
        assert 'DOWN' == router.state
        assert 'Router is Down' == router.output
        assert router.last_chk == past

        # Now with crappy characters, like é
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Output contains crappy ' \
                'character  èàçé   and spaces|rtt=9999' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'DOWN' == router.state
        assert u'Output contains crappy character  èàçé   and spaces' == router.output
        assert 'rtt=9999' == router.perf_data
        assert False == router.problem_has_been_acknowledged

        # Now with utf-8 data
        excmd = u'[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Output contains crappy ' \
                u'characters  èàçé   and spaces|rtt=9999' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'DOWN' == router.state
        assert u'Output contains crappy characters  èàçé   and spaces' == router.output
        assert 'rtt=9999' == router.perf_data
        assert False == router.problem_has_been_acknowledged

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        assert 'DOWN' == router.state
        assert True == router.problem_has_been_acknowledged

        # Remove acknowledge router
        excmd = '[%d] REMOVE_HOST_ACKNOWLEDGEMENT;test_router_0' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        assert 'DOWN' == router.state
        assert False == router.problem_has_been_acknowledged

        # Router is Down
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Router is Down' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'DOWN' == router.state
        assert 'Router is Down' == router.output
        # TODO: to be confirmed ... host should be unreachable because of its dependency with router
        # self.assertEqual('DOWN', host.state)
        # self.assertEqual('Router is Down', router.output)
        # self.assertEqual(router.last_chk, past)

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        assert 'DOWN' == router.state
        assert True == router.problem_has_been_acknowledged

        # Router is now Up
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;0;Router is Up' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'UP' == router.state
        assert 'Router is Up' == router.output
        # Acknowledge disappeared because host went OK
        assert False == router.problem_has_been_acknowledged

    @pytest.mark.skip("Currently disabled - to be refactored!")
    def test_unknown_check_result_command_scheduler(self):
        """ Unknown check results commands managed by the scheduler
        :return:
        """
        # ----- first part
        # -----
        # Our scheduler External Commands Manager DOES ACCEPT unknown passive checks...
        # self._scheduler.cur_conf.accept_passive_unknown_check_results = True
        self._scheduler.external_commands_manager.accept_passive_unknown_check_results = True

        # Clear logs and broks
        self.clear_logs()
        self._main_broker.broks = {}
        # The scheduler receives a known host but unknown service service_check_result
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;unknownservice;1;' \
                'Service is WARNING|rtt=9999;5;10;0;10000' % time.time()
        self._scheduler.run_external_commands([excmd])

        # We get an 'unknown_service_check_result'...
        broks = []
        # Broks from my scheduler brokers
        for broker_link_uuid in self._scheduler.my_daemon.brokers:
            broks.extend([b for b in self._scheduler.my_daemon.brokers[broker_link_uuid].values()])

        for b in broks:
            print("Brok: %s" % b)

        broks = [b for b in broks if b.type == 'unknown_service_check_result']
        assert len(broks) == 1
        # ...but no logs
        assert 0 == self.count_logs()

        # Clear logs and broks
        self.clear_logs()
        self._main_broker.broks = {}
        # The scheduler receives and unknown host and service service_check_result
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;unknownhost;unknownservice;1;' \
                'Service is WARNING|rtt=9999;5;10;0;10000' % time.time()
        self._scheduler.run_external_commands([excmd])

        # We get an 'unknown_service_check_result'...
        broks = [b for b in self._main_broker.broks.values()
                 if b.type == 'unknown_service_check_result']
        assert len(broks) == 1
        # ...but no logs
        assert 0 == self.count_logs()

        # Clear logs and broks
        self.clear_logs()
        self._main_broker.broks = {}
        # The scheduler receives an unknown host host_check_result
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;unknownhost;' \
                '1;Host is UP|rtt=9999;5;10;0;10000' % time.time()
        self._scheduler.run_external_commands([excmd])
        # A brok...
        broks = [b for b in self._main_broker.broks.values()
                 if b.type == 'unknown_host_check_result']
        assert len(broks) == 1
        # ...but no logs
        assert 0 == self.count_logs()

        # ----- second part
        # Our scheduler External Commands Manager DOES NOT ACCEPT unknown passive checks...
        # self._scheduler.cur_conf.accept_passive_unknown_check_results = False
        self._scheduler.external_commands_manager.accept_passive_unknown_check_results = False

        # Clear logs and broks
        self.clear_logs()
        self._main_broker.broks = {}
        # The scheduler receives a known host but unknown service service_check_result
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;unknownservice;1;' \
                'Service is WARNING|rtt=9999;5;10;0;10000' % time.time()
        self._scheduler.run_external_commands([excmd])

        # No brok...
        broks = [b for b in self._main_broker.broks.values()
                 if b.type == 'unknown_service_check_result']
        assert len(broks) == 0

        # ...but a log
        self.show_logs()
        self.assert_log_match(
            'A command was received for the service .* on host .*, '
            'but the service could not be found!')

        # Clear logs and broks
        self.clear_logs()
        self._main_broker.broks = {}
        # The scheduler receives an unknown host and service service_check_result
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;unknownhost;unknownservice;1;' \
                'Service is WARNING|rtt=9999;5;10;0;10000' % time.time()
        self._scheduler.run_external_commands([excmd])

        # No brok...
        broks = [b for b in self._main_broker.broks.values()
                 if b.type == 'unknown_service_check_result']
        assert len(broks) == 0

        # ...but a log
        self.show_logs()
        self.assert_log_match(
            'A command was received for the service .* on host .*, '
            'but the service could not be found!')

        # Clear logs and broks
        self.clear_logs()
        self._main_broker.broks = {}
        # The scheduler receives an unknown host host_check_result
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;unknownhost;' \
                '1;Host is UP|rtt=9999;5;10;0;10000' % time.time()
        self._scheduler.run_external_commands([excmd])

        # No brok...
        broks = [b for b in self._main_broker.broks.values()
                 if b.type == 'unknown_host_check_result']
        assert len(broks) == 0

        # ...but a log
        self.show_logs()
        self.assert_log_match(
            'A command was received for the host .*, '
            'but the host could not be found!')

    @pytest.mark.skip("Currently disabled - to be refactored!")
    def test_unknown_check_result_command_receiver(self):
        """ Unknown check results commands managed by the receiver
        :return:
        """
        # ----- first part
        # Our receiver External Commands Manager DOES ACCEPT unknown passive checks...
        # This is to replace the normal setup_new_conf ...
        self._receiver.accept_passive_unknown_check_results = True
        # Now create the external commands manager
        # We are a receiver: our role is to get and dispatch commands to the schedulers
        self._receiver.external_commands_manager = \
            ExternalCommandManager(None, 'receiver', self._receiver_daemon,
                                   self._receiver.accept_passive_unknown_check_results)

        # Clear logs and broks
        self.clear_logs()
        self._main_broker.broks = {}
        # The receiver receives an unknown service external command
        excmd = ExternalCommand('[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;unknownservice;'
                                '1;Service is WARNING|rtt=9999;5;10;0;10000' % time.time())
        # This will simply push te commands to the schedulers ...
        self._receiver_daemon.unprocessed_external_commands.append(excmd)
        self._receiver_daemon.push_external_commands_to_schedulers()

        self.external_command_loop()
        broks = []
        # Broks from my scheduler brokers
        for broker_link_uuid in self._scheduler.my_daemon.brokers:
            print("Broker: %s" % self._scheduler.my_daemon.brokers[broker_link_uuid])
            broks.extend([b for b in self._scheduler.my_daemon.brokers[broker_link_uuid].broks.values()])
        for b in broks:
            print("Brok: %s" % b)

        # for brok in sorted(self._main_broker.broks.values(), key=lambda x: x.creation_time):
        #     print("Brok: %s" % brok)

        for brok in sorted(self._receiver_daemon.broks.values(), key=lambda x: x.creation_time):
            print("--Brok: %s" % brok)

        broks = [b for b in broks if b.type == 'unknown_service_check_result']
        assert len(broks) == 1
        # ...but no logs!
        self.show_logs()
        self.assert_no_log_match('Passive check result was received for host .*, '
                                 'but the host could not be found!')

        # ----- second part
        # Our receiver External Commands Manager DOES NOT ACCEPT unknown passive checks...
        # This is to replace the normal setup_new_conf ...
        self._receiver.accept_passive_unknown_check_results = False
        self._receiver.external_commands_manager.accept_passive_unknown_check_results = False

        # Clear logs and broks
        self.clear_logs()
        self._main_broker.broks = {}
        # The receiver receives an unknown service external command
        excmd = ExternalCommand('[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;unknownservice;'
                                '1;Service is WARNING|rtt=9999;5;10;0;10000' % time.time())
        self._receiver.unprocessed_external_commands.append(excmd)
        self._receiver.push_external_commands_to_schedulers()
        # No brok...
        broks = [b for b in self._main_broker.broks.values()
                 if b.type == 'unknown_service_check_result']
        assert len(broks) == 0
        # ...but a log
        self.show_logs()
        self.assert_any_log_match("External command was received for host 'test_host_0', "
                                  "but the host could not be found!")

    def test_unknown_check_result_brok(self):
        """ Unknown check results commands in broks
        :return:
        """
        # unknown_host_check_result_brok
        excmd = '[1234567890] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is UP'
        expected = {'time_stamp': 1234567890, 'return_code': '2', 'host_name': 'test_host_0',
                    'output': 'Host is UP', 'perf_data': None}
        result = ujson.loads(ExternalCommandManager.get_unknown_check_result_brok(excmd).data)
        assert expected == result

        # unknown_host_check_result_brok with perfdata
        excmd = '[1234567890] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is UP|rtt=9999'
        expected = {'time_stamp': 1234567890, 'return_code': '2', 'host_name': 'test_host_0',
                    'output': 'Host is UP', 'perf_data': 'rtt=9999'}
        result = ujson.loads(ExternalCommandManager.get_unknown_check_result_brok(excmd).data)
        assert expected == result

        # unknown_service_check_result_brok
        excmd = '[1234567890] PROCESS_HOST_CHECK_RESULT;host-checked;0;Everything OK'
        expected = {'time_stamp': 1234567890, 'return_code': '0', 'host_name': 'host-checked',
                    'output': 'Everything OK', 'perf_data': None}
        result = ujson.loads(ExternalCommandManager.get_unknown_check_result_brok(excmd).data)
        assert expected == result

        # unknown_service_check_result_brok with perfdata
        excmd = '[1234567890] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;1;Service is WARNING|rtt=9999;5;10;0;10000'
        expected = {'host_name': 'test_host_0', 'time_stamp': 1234567890,
                    'service_description': 'test_ok_0', 'return_code': '1',
                    'output': 'Service is WARNING', 'perf_data': 'rtt=9999;5;10;0;10000'}
        result = ujson.loads(ExternalCommandManager.get_unknown_check_result_brok(excmd).data)
        assert expected == result

    def test_services_acknowledge(self):
        """ Test services acknowledge
        :return:
        """
        # Get host
        host = self._scheduler.hosts.find_by_name('test_host_0')
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.active_checks_enabled = True
        host.passive_checks_enabled = True
        print("Host: %s - state: %s/%s" % (host, host.state_type, host.state))
        assert host is not None
    
        # Get dependent host
        router = self._scheduler.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.event_handler_enabled = False
        router.active_checks_enabled = True
        router.passive_checks_enabled = True
        print("Router: %s - state: %s/%s" % (router, router.state_type, router.state))
        assert router is not None

        # Get service
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.event_handler_enabled = False
        svc.active_checks_enabled = True
        svc.passive_checks_enabled = True
        assert svc is not None
        print("Service: %s - state: %s/%s" % (svc, svc.state_type, svc.state))
    
        # Passive checks for services
        # ---------------------------------------------
        # Receive passive service check Warning
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;1;Service is WARNING' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        self.scheduler_loop(1, [[host, 0, 'Host is UP']])
        assert 'WARNING' == svc.state
        assert 'Service is WARNING' == svc.output
        assert False == svc.problem_has_been_acknowledged
    
        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;Acknowledge service' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'WARNING' == svc.state
        assert True == svc.problem_has_been_acknowledged

        # Add a comment
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;Acknowledge service' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'WARNING' == svc.state
        assert True == svc.problem_has_been_acknowledged

        # Remove acknowledge service
        excmd = '[%d] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'WARNING' == svc.state
        assert False == svc.problem_has_been_acknowledged
    
        # Receive passive service check Critical
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;2;Service is CRITICAL' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        self.scheduler_loop(1, [[host, 0, 'Host is UP']])
        assert 'CRITICAL' == svc.state
        assert 'Service is CRITICAL' == svc.output
        assert False == svc.problem_has_been_acknowledged
    
        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;Acknowledge service' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'CRITICAL' == svc.state
        assert True == svc.problem_has_been_acknowledged
    
        # Service is going ok ...
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;0;Service is OK' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'OK' == svc.state
        assert 'Service is OK' == svc.output
        # Acknowledge disappeared because service went OK
        assert False == svc.problem_has_been_acknowledged

    def test_hosts_checks(self):
        """ Test hosts checks
        :return:
        """
        # Get host
        host = self._scheduler.hosts.find_by_name('test_host_0')
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router which we depend of
        host.event_handler_enabled = False
        print("Host: %s - state: %s/%s" % (host, host.state_type, host.state))
        assert host is not None

        # Get dependent host
        router = self._scheduler.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.event_handler_enabled = False
        print("Router: %s - state: %s/%s" % (router, router.state_type, router.state))
        assert router is not None

        # Get service
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.event_handler_enabled = False
        svc.active_checks_enabled = True
        svc.passive_checks_enabled = True
        assert svc is not None
        print("Service: %s - state: %s/%s" % (svc, svc.state_type, svc.state))

        # Passive checks for hosts - active only checks
        # ------------------------------------------------
        host.active_checks_enabled = True
        host.passive_checks_enabled = False     # Disabled
        router.active_checks_enabled = True
        router.passive_checks_enabled = False   # Disabled
        # Host is DOWN
        # Set active host as DOWN
        self.scheduler_loop(1, [[host, 2, 'Host is DOWN']])
        # excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is DOWN' % int(time.time())
        # self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        # self.external_command_loop()
        # New checks: test host, dependent host and service (because active checks are enabled)
        self.assert_checks_count(2)
        self.show_checks()
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        assert 'DOWN' == host.state
        assert u'Host is DOWN' == host.output
        assert False == host.problem_has_been_acknowledged

        # Host is UP
        # Set active host as DOWN
        self.scheduler_loop(1, [[host, 0, 'Host is UP']])
        # excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP' % int(time.time())
        # self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        # self.external_command_loop()
        # New checks: test dependent host and service (because active checks are enabled)
        self.show_checks()
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        assert 'UP' == host.state
        assert u'Host is UP' == host.output
        assert False == host.problem_has_been_acknowledged

        # Passive checks for hosts - active/passive checks
        # ------------------------------------------------
        host.active_checks_enabled = True
        host.passive_checks_enabled = True
        router.active_checks_enabled = True
        router.passive_checks_enabled = True
        # Host is DOWN
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is DOWN' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        # New checks: test dependent host and service (because active checks are enabled)
        self.show_checks()
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assert_checks_match(1, 'servicedesc test_ok_0', 'command')
        assert 'DOWN' == host.state
        assert u'Host is DOWN' == host.output
        assert False == host.problem_has_been_acknowledged

        # Host is UP
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        # New checks: test dependent host and service (because active checks are enabled)
        self.show_checks()
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assert_checks_match(1, 'servicedesc test_ok_0', 'command')
        assert 'UP' == host.state
        assert u'Host is UP' == host.output
        assert False == host.problem_has_been_acknowledged

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
        self._scheduler.run_external_commands([excmd])
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
        assert 'DOWN' == host.state
        assert u'Host is DOWN' == host.output
        assert False == host.problem_has_been_acknowledged

        # Host is UP
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        # New checks: test dependent host and service (because active checks are enabled)
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assert_checks_match(1, 'servicedesc test_ok_0', 'command')
        assert 'UP' == host.state
        assert u'Host is UP' == host.output
        assert False == host.problem_has_been_acknowledged

    def test_hosts_acknowledge(self):
        """ Test hosts acknowledge
        :return:
        """
        # Get host
        host = self._scheduler.hosts.find_by_name('test_host_0')
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.active_checks_enabled = True
        host.passive_checks_enabled = True
        print("Host: %s - state: %s/%s" % (host, host.state_type, host.state))
        assert host is not None

        # Get dependent host
        router = self._scheduler.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.event_handler_enabled = False
        router.active_checks_enabled = True
        router.passive_checks_enabled = True
        print("Router: %s - state: %s/%s" % (router, router.state_type, router.state))
        assert router is not None

        # Get service
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.event_handler_enabled = False
        svc.active_checks_enabled = True
        svc.passive_checks_enabled = True
        assert svc is not None
        print("Service: %s - state: %s/%s" % (svc, svc.state_type, svc.state))

        # Passive checks for hosts - special case
        # ---------------------------------------------
        # Host is DOWN
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Host is DOWN' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        self.show_checks()
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_host_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assert_checks_match(1, 'servicedesc test_ok_0', 'command')
        assert 'DOWN' == router.state
        assert u'Host is DOWN' == router.output
        assert False == router.problem_has_been_acknowledged

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        assert 'DOWN' == router.state
        assert True == router.problem_has_been_acknowledged
    
        # Remove acknowledge router
        excmd = '[%d] REMOVE_HOST_ACKNOWLEDGEMENT;test_router_0' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        assert 'DOWN' == router.state
        assert False == router.problem_has_been_acknowledged

        # Host is DOWN
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Host is DOWN' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'DOWN' == router.state
        assert u'Host is DOWN' == router.output
        assert False == router.problem_has_been_acknowledged

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        assert 'DOWN' == router.state
        assert True == router.problem_has_been_acknowledged

        # Remove acknowledge router
        excmd = '[%d] REMOVE_HOST_ACKNOWLEDGEMENT;test_router_0' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        assert 'DOWN' == router.state
        assert False == router.problem_has_been_acknowledged

        # Router is Down
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Router is Down' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'DOWN' == router.state
        assert 'Router is Down' == router.output

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        assert 'DOWN' == router.state
        assert True == router.problem_has_been_acknowledged

        # Router is now Up
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;0;Router is Up' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        assert 'UP' == router.state
        assert 'Router is Up' == router.output
        # Acknowledge disappeared because host went OK
        assert False == router.problem_has_been_acknowledged

    def test_hosts_services_acknowledge(self):
        """ Test hosts with some attached services acknowledge
        :return:
        """
        # Get host
        host = self._scheduler.hosts.find_by_name('test_host_0')
        host.checks_in_progress = []
        host.act_depend_of = []
        host.event_handler_enabled = False
        host.active_checks_enabled = True
        host.passive_checks_enabled = True
        print("Host: %s - state: %s/%s" % (host, host.state_type, host.state))
        assert host is not None

        # Get service
        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0",
            "test_ok_0")
        svc.checks_in_progress = []
        svc.event_handler_enabled = False
        svc.active_checks_enabled = True
        svc.passive_checks_enabled = True
        assert svc is not None
        print("Service: %s - state: %s/%s" % (svc, svc.state_type, svc.state))

        # Passive checks for the host and its service
        # ---------------------------------------------
        # Service is WARNING
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;1;Service is WARNING' % time.time()
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        self.scheduler_loop(1, [[host, 0, 'Host is UP']])
        assert 'WARNING' == svc.state
        assert 'Service is WARNING' == svc.output
        # The service is not acknowledged
        assert False == svc.problem_has_been_acknowledged

        # Host is DOWN
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is DOWN' % int(time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        self.show_checks()
        self.assert_checks_count(2)
        self.assert_checks_match(0, 'test_hostcheck.pl', 'command')
        self.assert_checks_match(0, 'hostname test_router_0', 'command')
        self.assert_checks_match(1, 'test_servicecheck.pl', 'command')
        self.assert_checks_match(1, 'hostname test_host_0', 'command')
        self.assert_checks_match(1, 'servicedesc test_ok_0', 'command')
        assert 'DOWN' == host.state
        assert u'Host is DOWN' == host.output
        assert False == host.problem_has_been_acknowledged

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_host_0;2;1;1;Big brother;test' % int(
            time.time())
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        print "Host state", host.state, host.problem_has_been_acknowledged
        assert 'DOWN' == host.state
        assert True == host.problem_has_been_acknowledged

        print "Service state", svc.state, svc.problem_has_been_acknowledged
        assert 'WARNING' == svc.state
        # The service has also been acknowledged!
        assert True == svc.problem_has_been_acknowledged
