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

import time
from .alignak_test import AlignakTest
from alignak.misc.serialization import unserialize


class TestBrokInitialStatus(AlignakTest):
    """
    This class test the initial status brok
    """
    def setUp(self):
        super(TestBrokInitialStatus, self).setUp()
        self.setup_with_file('cfg/cfg_default.cfg', dispatching=True)
        self._main_broker.broks = []

    def test_brok_initial_status(self):
        """Test initial status broks

        :return: None
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
                print("Brok %s: %s" % (brok.type, brok))
        # self.my_daemon.brokers[broker_link_uuid].broks.append(brok)

        # self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        # time.sleep(0.1)
        # host_check_results = []
        # service_check_results = []
        # for brok in self._main_broker.broks:
        #     print("Brok %s: %s" % (brok.type, brok))
        #
        #     # if brok.type == 'host_check_result':
        #     #     print(("Brok %s: %s" % (brok.type, brok)))
        #     #     host_check_results.append(brok)
        #     # elif brok.type == 'service_check_result':
        #     #     print(("Brok %s: %s" % (brok.type, brok)))
        #     #     service_check_results.append(brok)
        #
        # assert len(host_check_results) == 1
        # assert len(service_check_results) == 1
        #
        # hdata = unserialize(host_check_results[0].data)
        # assert hdata['state'] == 'DOWN'
        # assert hdata['state_type'] == 'SOFT'
        #
        # sdata = unserialize(service_check_results[0].data)
        # assert sdata['state'] == 'OK'
        # assert sdata['state_type'] == 'HARD'


class TestBrokCheckResult(AlignakTest):
    """
    This class test the check_result brok
    """
    def setUp(self):
        super(TestBrokCheckResult, self).setUp()
        self.setup_with_file('cfg/cfg_default.cfg',
                             dispatching=True)
        self._main_broker.broks = []

    def test_brok_checks_results(self):
        """Test broks checks results

        :return: None
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

        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 0, 'OK']])
        time.sleep(0.1)
        host_check_results = []
        service_check_results = []
        for brok in self._main_broker.broks:
            if brok.type == 'host_check_result':
                print(("Brok %s: %s" % (brok.type, brok)))
                host_check_results.append(brok)
            elif brok.type == 'service_check_result':
                print(("Brok %s: %s" % (brok.type, brok)))
                service_check_results.append(brok)

        assert len(host_check_results) == 1
        assert len(service_check_results) == 1

        hdata = unserialize(host_check_results[0].data)
        assert hdata['state'] == 'DOWN'
        assert hdata['state_type'] == 'SOFT'

        sdata = unserialize(service_check_results[0].data)
        assert sdata['state'] == 'OK'
        assert sdata['state_type'] == 'HARD'
