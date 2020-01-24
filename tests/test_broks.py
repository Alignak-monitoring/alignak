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
This file test the check_result brok
"""

import copy
import time
from six import string_types
from .alignak_test import AlignakTest
from alignak.misc.serialization import serialize, unserialize
from alignak.external_command import ExternalCommand, ExternalCommandManager


class TestBroks(AlignakTest):
    """
    This class test several Brok creation
    """
    def setUp(self):
        super(TestBroks, self).setUp()
        self.setup_with_file('cfg/cfg_default.cfg', dispatching=True)
        self._main_broker.broks = []

    def test_brok_initial_status(self):
        """Test initial status broks
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        initial_broks_count = self._scheduler.fill_initial_broks('broker-master')
        print("fill_initial_broks got %s broks" % initial_broks_count)

        for broker_uuid in self._scheduler.my_daemon.brokers:
            broker = self._scheduler.my_daemon.brokers[broker_uuid]
            print("Broker: %s" % broker)
            for brok in broker.broks:
                print("-: %s" % brok)
                # Check the brok attributes
                assert hasattr(brok, 'uuid')
                assert hasattr(brok, 'creation_time')
                assert hasattr(brok, 'prepared')
                # Not yet prepared to get used, must call the prepare method!
                assert brok.prepared is False
                assert hasattr(brok, 'instance_id')
                assert hasattr(brok, 'type')
                assert hasattr(brok, 'data')
                # assert isinstance(brok.data, string_types)

    def test_unknown_check_result_brok(self):
        """ Unknown check results commands in broks
        """
        # unknown_host_check_result_brok
        excmd = '[1234567890] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is UP'
        expected = {
            'time_stamp': 1234567890, 'return_code': '2', 'host_name': 'test_host_0',
            'output': 'Host is UP', 'perf_data': None
        }
        brok = ExternalCommandManager.get_unknown_check_result_brok(excmd)
        print("Brok: %s" % brok)
        # the prepare method returns the brok data
        assert expected == brok.prepare()

        # unknown_host_check_result_brok with perfdata
        excmd = '[1234567890] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is UP|rtt=9999'
        expected = {
            'time_stamp': 1234567890, 'return_code': '2', 'host_name': 'test_host_0',
            'output': 'Host is UP', 'perf_data': 'rtt=9999'
        }
        brok = ExternalCommandManager.get_unknown_check_result_brok(excmd)
        assert expected == brok.prepare()

        # unknown_service_check_result_brok
        excmd = '[1234567890] PROCESS_HOST_CHECK_RESULT;host-checked;0;Everything OK'
        expected = {
            'time_stamp': 1234567890, 'return_code': '0', 'host_name': 'host-checked',
            'output': 'Everything OK', 'perf_data': None
        }
        brok = ExternalCommandManager.get_unknown_check_result_brok(excmd)
        assert expected == brok.prepare()

        # unknown_service_check_result_brok with perfdata
        excmd = '[1234567890] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;1;Service is WARNING|rtt=9999;5;10;0;10000'
        expected = {
            'host_name': 'test_host_0', 'time_stamp': 1234567890,
            'service_description': 'test_ok_0', 'return_code': '1',
            'output': 'Service is WARNING', 'perf_data': 'rtt=9999;5;10;0;10000'
        }
        brok = ExternalCommandManager.get_unknown_check_result_brok(excmd)
        assert expected == brok.prepare()

    def test_brok_checks_results(self):
        """Test broks checks results
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        # Make the host down soft then hard.
        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.scheduler_loop(2, [[host, 2, 'DOWN']])
        time.sleep(0.1)

        host_check_results = []
        service_check_results = []
        for brok in self._main_broker.broks:
            print("Brok %s: %s" % (brok.type, brok))
            # Check the brok attributes
            assert hasattr(brok, 'uuid')
            assert hasattr(brok, 'creation_time')
            assert hasattr(brok, 'prepared')
            # Not yet prepared to get used, must call the prepare method!
            assert brok.prepared is False
            assert hasattr(brok, 'instance_id')
            assert hasattr(brok, 'type')
            assert hasattr(brok, 'data')
            # assert isinstance(brok.data, string_types)

            if brok.type == 'host_check_result':
                host_check_results.append(brok)
            elif brok.type == 'service_check_result':
                service_check_results.append(brok)

        assert len(host_check_results) == 3
        assert len(service_check_results) == 1

        # Prepare the broks to get used...
        print("HCR: %s" % host_check_results[0])
        host_check_results[0].prepare()
        print("HCR: %s" % host_check_results[0])
        hdata = host_check_results[0].data
        # Now it is a dict
        assert isinstance(hdata, dict)

        assert hdata['state'] == 'DOWN'
        assert hdata['state_type'] == 'SOFT'

        print("SCR: %s" % service_check_results[0])
        service_check_results[0].prepare()
        print("SCR: %s" % service_check_results[0])
        sdata = service_check_results[0].data
        assert isinstance(hdata, dict)

        assert sdata['state'] == 'OK'
        assert sdata['state_type'] == 'HARD'

    def test_brok_get_events(self):
        """Test broks for events
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        # Make the host down soft then hard.
        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.scheduler_loop(2, [[host, 2, 'DOWN']])
        time.sleep(0.1)

        print("My events: %s" % self._scheduler_daemon.events)

        my_events = copy.deepcopy(self._scheduler_daemon.events)
        assert my_events != self._scheduler_daemon.events
        my_events2 = copy.copy(self._scheduler_daemon.events)
        assert my_events2 == self._scheduler_daemon.events

        for brok in self._scheduler_daemon.events:
            # Check the brok attributes
            assert hasattr(brok, 'uuid')
            assert hasattr(brok, 'creation_time')
            assert hasattr(brok, 'prepared')
            # Not yet prepared to get used, must call the prepare method!
            assert brok.prepared is False
            assert hasattr(brok, 'instance_id')
            assert hasattr(brok, 'type')
            assert hasattr(brok, 'data')
            # assert isinstance(brok.data, string_types)

            # Get an event from the brok
            ts, level, message = brok.get_event()
            assert brok.prepared is True
            assert isinstance(brok.data, dict)
            print("Event: %s / %s / %s" % (ts, level, message))

        print("My events: %s" % my_events)

        res = serialize(my_events, True)
        print("My events: %s" % res)
