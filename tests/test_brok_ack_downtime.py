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
This file test the acknowledge and downtime broks
"""

import time
from .alignak_test import AlignakTest
from alignak.misc.serialization import unserialize


class TestBrokAckDowntime(AlignakTest):
    """
    This class test the acknowledge and downtime broks
    """
    def setUp(self):
        super(TestBrokAckDowntime, self).setUp()

    def test_acknowledge_service(self):
        """Test broks when acknowledge

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self._main_broker.broks = []

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), 'test_host_0', 'test_ok_0', 2, 0, 1, 'darth vader', 'normal process')
        self._scheduler.run_external_commands([cmd])
        self.scheduler_loop(3, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])

        brok_ack_raise = []
        brok_ack_expire = []
        for brok in self._main_broker.broks:
            print("Brok: %s" % brok)
            if brok.type == 'acknowledge_raise':
                brok_ack_raise.append(brok)
            elif brok.type == 'acknowledge_expire':
                brok_ack_expire.append(brok)

        assert len(brok_ack_raise) == 1
        assert len(brok_ack_expire) == 0

        hdata = unserialize(brok_ack_raise[0].data)
        assert hdata['host'] == 'test_host_0'
        assert hdata['service'] == 'test_ok_0'
        assert hdata['comment'] == 'normal process'

        # return service in OK mode, so the acknowledge will be removed by the scheduler
        self._main_broker.broks = []
        self.scheduler_loop(2, [[host, 0, 'UP'], [svc, 0, 'OK']])
        brok_ack_raise = []
        brok_ack_expire = []
        for brok in self._main_broker.broks:
            if brok.type == 'acknowledge_raise':
                brok_ack_raise.append(brok)
            elif brok.type == 'acknowledge_expire':
                brok_ack_expire.append(brok)

        assert len(brok_ack_raise) == 0
        assert len(brok_ack_expire) == 1

        hdata = unserialize(brok_ack_expire[0].data)
        assert hdata['host'] == 'test_host_0'
        assert hdata['service'] == 'test_ok_0'

        # Do the same but remove acknowledge  with external commands:
        self._main_broker.broks = []
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), 'test_host_0', 'test_ok_0', 2, 0, 1, 'darth vader', 'normal process')
        self._scheduler.run_external_commands([cmd])
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])

        cmd = "[{0}] REMOVE_SVC_ACKNOWLEDGEMENT;{1};{2}\n". \
            format(int(now), 'test_host_0', 'test_ok_0')
        self._scheduler.run_external_commands([cmd])
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])

        brok_ack_raise = []
        brok_ack_expire = []
        for brok in self._main_broker.broks:
            print(("Brok: %s" % brok))
            if brok.type == 'acknowledge_raise':
                brok_ack_raise.append(brok)
            elif brok.type == 'acknowledge_expire':
                brok_ack_expire.append(brok)

        assert len(brok_ack_raise) == 1
        assert len(brok_ack_expire) == 1

        hdata = unserialize(brok_ack_expire[0].data)
        assert hdata['host'] == 'test_host_0'
        assert hdata['service'] == 'test_ok_0'
        assert hdata['comment'] == 'normal process'

    def test_acknowledge_host(self):
        """Test broks when acknowledge

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        self._main_broker.broks = []

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM_EXPIRE;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), 'test_host_0', 1, 0, 1, (now + 2), 'darth vader', 'normal process')
        self._scheduler.run_external_commands([cmd])
        self.external_command_loop(2)
        # self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])

        brok_ack = []
        print("Broker uuid: %s" % self._main_broker.uuid)
        print("Broker broks: %s" % self._main_broker.broks)
        for brok in self._main_broker.broks:
            print("Broker brok: %s" % brok)
            if brok.type == 'acknowledge_raise':
                print("Brok: %s" % brok)
                brok_ack.append(brok)

        print("***Scheduler: %s" % self._scheduler)
        print("***Scheduler daemon: %s" % self._scheduler.my_daemon)
        print("***Scheduler daemon brokers: %s" % self._scheduler.my_daemon.brokers)
        for broker_link_uuid in self._scheduler.my_daemon.brokers:
            print("*** %s - broks: %s" % (broker_link_uuid, self._scheduler.my_daemon.brokers[broker_link_uuid].broks))

        # Got one brok for the host ack and one brok for the service ack
        assert len(brok_ack) == 2

        host_brok = False
        service_brok = False
        hdata = unserialize(brok_ack[0].data)
        assert hdata['host'] == 'test_host_0'
        if 'service' in hdata:
            assert hdata['service'] == 'test_ok_0'
            service_brok = True
        else:
            host_brok = True

        hdata = unserialize(brok_ack[1].data)
        assert hdata['host'] == 'test_host_0'
        if 'service' in hdata:
            assert hdata['service'] == 'test_ok_0'
            service_brok = True
        else:
            host_brok = True

        assert host_brok and service_brok

        # return host in UP mode, so the acknowledge will be removed by the scheduler
        self._main_broker.broks = []
        self.scheduler_loop(2, [[host, 0, 'UP'], [svc, 0, 'OK']])
        brok_ack_raise = []
        brok_ack_expire = []
        for brok in self._main_broker.broks:
            if brok.type == 'acknowledge_raise':
                brok_ack_raise.append(brok)
            elif brok.type == 'acknowledge_expire':
                brok_ack_expire.append(brok)

        assert len(brok_ack_raise) == 0
        assert len(brok_ack_expire) == 2

        host_brok = False
        service_brok = False
        hdata = unserialize(brok_ack_expire[0].data)
        assert hdata['host'] == 'test_host_0'
        if 'service' in hdata:
            assert hdata['service'] == 'test_ok_0'
            service_brok = True
        else:
            host_brok = True

        hdata = unserialize(brok_ack_expire[1].data)
        assert hdata['host'] == 'test_host_0'
        if 'service' in hdata:
            assert hdata['service'] == 'test_ok_0'
            service_brok = True
        else:
            host_brok = True

        assert host_brok and service_brok

        # Do the same but remove acknowledge with external commands:
        self._main_broker.broks = []
        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM_EXPIRE;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), 'test_host_0', 1, 0, 1, (now + 2), 'darth vader', 'normal process')
        self._scheduler.run_external_commands([cmd])
        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])

        cmd = "[{0}] REMOVE_HOST_ACKNOWLEDGEMENT;{1}\n". \
            format(int(now), 'test_host_0')
        self._scheduler.run_external_commands([cmd])
        self.scheduler_loop(3, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])

        brok_ack_raise = []
        brok_ack_expire = []
        for brok in self._main_broker.broks:
            print("Brok: %s" % brok)
            if brok.type == 'acknowledge_raise':
                brok_ack_raise.append(brok)
            elif brok.type == 'acknowledge_expire':
                brok_ack_expire.append(brok)

        assert len(brok_ack_raise) == 2
        assert len(brok_ack_expire) == 1

        hdata = unserialize(brok_ack_expire[0].data)
        assert hdata['host'] == 'test_host_0'
        assert 'service' not in hdata

    def test_fixed_downtime_service(self):
        """Test broks when downtime

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        self._main_broker.broks = []

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0",
            "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        # schedule a 5 seconds downtime
        duration = 5
        now = int(time.time())
        # downtime valid for 5 seconds from now
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%d;%d;1;0;%d;" \
              "downtime author;downtime comment" % (now, now, now + duration, duration)
        self._scheduler.run_external_commands([cmd])
        self.external_command_loop()
        self.external_command_loop()

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self._main_broker.broks:
            if brok.type == 'downtime_raise':
                brok_downtime_raise.append(brok)
            elif brok.type == 'downtime_expire':
                brok_downtime_expire.append(brok)

        assert len(brok_downtime_raise) == 1
        assert len(brok_downtime_expire) == 0

        hdata = unserialize(brok_downtime_raise[0].data)
        assert hdata['host'] == 'test_host_0'
        assert hdata['service'] == 'test_ok_0'
        assert hdata['comment'] == 'downtime comment'

        # expire downtime
        self._main_broker.broks = []
        time.sleep(5)
        self.scheduler_loop(2, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self._main_broker.broks:
            if brok.type == 'downtime_raise':
                brok_downtime_raise.append(brok)
            elif brok.type == 'downtime_expire':
                brok_downtime_expire.append(brok)

        assert len(brok_downtime_raise) == 0
        assert len(brok_downtime_expire) == 1

        hdata = unserialize(brok_downtime_expire[0].data)
        assert hdata['host'] == 'test_host_0'
        assert hdata['service'] == 'test_ok_0'
        assert hdata['comment'] == 'downtime comment'

    def test_fixed_downtime_host(self):
        """Test broks when downtime

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        self._main_broker.broks = []

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0",
            "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        # schedule a 5 seconds downtime
        duration = 5
        now = int(time.time())
        # downtime valid for 5 seconds from now
        cmd = "[%lu] SCHEDULE_HOST_DOWNTIME;test_host_0;%d;%d;1;0;%d;" \
              "downtime author;downtime comment" % (now, now, now + duration, duration)
        self._scheduler.run_external_commands([cmd])
        self.external_command_loop()
        self.external_command_loop()

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self._main_broker.broks:
            if brok.type == 'downtime_raise':
                brok_downtime_raise.append(brok)
            elif brok.type == 'downtime_expire':
                brok_downtime_expire.append(brok)

        assert len(brok_downtime_raise) == 1
        assert len(brok_downtime_expire) == 0

        hdata = unserialize(brok_downtime_raise[0].data)
        assert hdata['host'] == 'test_host_0'
        assert 'service' not in hdata

        # expire downtime
        self._main_broker.broks = []
        time.sleep(5)
        self.scheduler_loop(2, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self._main_broker.broks:
            if brok.type == 'downtime_raise':
                brok_downtime_raise.append(brok)
            elif brok.type == 'downtime_expire':
                brok_downtime_expire.append(brok)

        assert len(brok_downtime_raise) == 0
        assert len(brok_downtime_expire) == 1

        hdata = unserialize(brok_downtime_expire[0].data)
        assert hdata['host'] == 'test_host_0'
        assert 'service' not in hdata

    def test_flexible_downtime_service(self):
        """Test broks when downtime

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        self._main_broker.broks = []

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0",
            "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)

        # schedule a 5 seconds downtime
        duration = 5
        now = int(time.time())
        # downtime valid for 5 seconds from now
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%d;%d;0;0;%d;" \
              "downtime author;downtime comment" % (now, now, now + 3600, duration)
        self._scheduler.run_external_commands([cmd])
        self.scheduler_loop(2, [[host, 0, 'UP'], [svc, 0, 'OK']])

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self._main_broker.broks:
            if brok.type == 'downtime_raise':
                brok_downtime_raise.append(brok)
            elif brok.type == 'downtime_expire':
                brok_downtime_expire.append(brok)

        assert len(brok_downtime_raise) == 0
        assert len(brok_downtime_expire) == 0

        time.sleep(1)
        self._main_broker.broks = []
        self.scheduler_loop(3, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])

        for brok in self._main_broker.broks:
            if brok.type == 'downtime_raise':
                brok_downtime_raise.append(brok)
            elif brok.type == 'downtime_expire':
                brok_downtime_expire.append(brok)

        assert len(brok_downtime_raise) == 1
        assert len(brok_downtime_expire) == 0

        hdata = unserialize(brok_downtime_raise[0].data)
        assert hdata['host'] == 'test_host_0'
        assert hdata['service'] == 'test_ok_0'

    def test_cancel_service(self):
        """Test broks when cancel downtime

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        self._main_broker.broks = []

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP']])

        duration = 5
        now = int(time.time())
        # downtime valid for 5 seconds from now
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%d;%d;1;0;%d;" \
              "downtime author;downtime comment" % (now, now, now + duration, duration)
        self._scheduler.run_external_commands([cmd])
        self.external_command_loop()

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self._main_broker.broks:
            if brok.type == 'downtime_raise':
                brok_downtime_raise.append(brok)
            elif brok.type == 'downtime_expire':
                brok_downtime_expire.append(brok)

        assert len(brok_downtime_raise) == 1
        assert len(brok_downtime_expire) == 0

        # External command: delete all host downtime
        now = int(time.time())
        self._main_broker.broks = []
        cmd = '[%d] DEL_ALL_SVC_DOWNTIMES;test_host_0;test_ok_0' % now
        self._scheduler.run_external_commands([cmd])
        self.external_command_loop()

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self._main_broker.broks:
            if brok.type == 'downtime_raise':
                brok_downtime_raise.append(brok)
            elif brok.type == 'downtime_expire':
                brok_downtime_expire.append(brok)

        assert len(brok_downtime_raise) == 0
        assert len(brok_downtime_expire) == 1

        hdata = unserialize(brok_downtime_expire[0].data)
        assert hdata['host'] == 'test_host_0'
        assert hdata['service'] == 'test_ok_0'

    def test_cancel_host(self):
        """Test broks when cancel downtime

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        self._main_broker.broks = []

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP']])

        duration = 5
        now = int(time.time())
        # downtime valid for 5 seconds from now
        cmd = "[%lu] SCHEDULE_HOST_DOWNTIME;test_host_0;%d;%d;1;0;%d;" \
              "downtime author;downtime comment" % (now, now, now + duration, duration)
        self._scheduler.run_external_commands([cmd])
        self.external_command_loop()

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self._main_broker.broks:
            if brok.type == 'downtime_raise':
                brok_downtime_raise.append(brok)
            elif brok.type == 'downtime_expire':
                brok_downtime_expire.append(brok)

        assert len(brok_downtime_raise) == 1
        assert len(brok_downtime_expire) == 0

        # External command: delete all host downtime
        now = int(time.time())
        self._main_broker.broks = []
        cmd = '[%d] DEL_ALL_HOST_DOWNTIMES;test_host_0' % now
        self._scheduler.run_external_commands([cmd])
        self.external_command_loop()

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self._main_broker.broks:
            if brok.type == 'downtime_raise':
                brok_downtime_raise.append(brok)
            elif brok.type == 'downtime_expire':
                brok_downtime_expire.append(brok)

        assert len(brok_downtime_raise) == 0
        assert len(brok_downtime_expire) == 1

        hdata = unserialize(brok_downtime_expire[0].data)
        assert hdata['host'] == 'test_host_0'
