#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016: Alignak team, see AUTHORS.txt file for contributors
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
from alignak_test import AlignakTest
from alignak.misc.serialization import unserialize


class TestBrokAckDowntime(AlignakTest):
    """
    This class test the acknowledge and downtime broks
    """

    def test_acknowledge_service(self):
        """Test broks when acknowledge

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), 'test_host_0', 'test_ok_0', 2, 0, 1, 'darth vader', 'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.scheduler_loop(3, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])

        brok_ack_raise = []
        brok_ack_expire = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master']['broks'].itervalues():
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
        self.schedulers['scheduler-master'].sched.brokers['broker-master']['broks'] = {}
        self.scheduler_loop(2, [[host, 0, 'UP'], [svc, 0, 'OK']])
        brok_ack_raise = []
        brok_ack_expire = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master']['broks'].itervalues():
            if brok.type == 'acknowledge_raise':
                brok_ack_raise.append(brok)
            elif brok.type == 'acknowledge_expire':
                brok_ack_expire.append(brok)

        assert len(brok_ack_raise) == 0
        assert len(brok_ack_expire) == 1

        hdata = unserialize(brok_ack_expire[0].data)
        assert hdata['host'] == 'test_host_0'
        assert hdata['service'] == 'test_ok_0'

        # Do same but end with external commands:
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), 'test_host_0', 'test_ok_0', 2, 0, 1, 'darth vader', 'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])
        self.schedulers['scheduler-master'].sched.brokers['broker-master']['broks'] = {}

        cmd = "[{0}] REMOVE_SVC_ACKNOWLEDGEMENT;{1};{2}\n". \
            format(int(now), 'test_host_0', 'test_ok_0')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])

        brok_ack_raise = []
        brok_ack_expire = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master']['broks'].itervalues():
            if brok.type == 'acknowledge_raise':
                brok_ack_raise.append(brok)
            elif brok.type == 'acknowledge_expire':
                brok_ack_expire.append(brok)

        assert len(brok_ack_raise) == 0
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

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0",
            "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM_EXPIRE;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), 'test_host_0', 1, 0, 1, (now + 2), 'darth vader', 'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.scheduler_loop(3, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])

        brok_ack = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master'][
            'broks'].itervalues():
            if brok.type == 'acknowledge_raise':
                brok_ack.append(brok)

        assert len(brok_ack) == 1

        hdata = unserialize(brok_ack[0].data)
        assert hdata['host'] == 'test_host_0'
        assert 'service' not in hdata

        # return host in UP mode, so the acknowledge will be removed by the scheduler
        self.schedulers['scheduler-master'].sched.brokers['broker-master']['broks'] = {}
        self.scheduler_loop(2, [[host, 0, 'UP'], [svc, 0, 'OK']])
        brok_ack_raise = []
        brok_ack_expire = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master']['broks'].itervalues():
            if brok.type == 'acknowledge_raise':
                brok_ack_raise.append(brok)
            elif brok.type == 'acknowledge_expire':
                brok_ack_expire.append(brok)

        assert len(brok_ack_raise) == 0
        assert len(brok_ack_expire) == 1

        hdata = unserialize(brok_ack_expire[0].data)
        assert hdata['host'] == 'test_host_0'
        assert 'service' not in hdata

        # Do same but end with external commands:
        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM_EXPIRE;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), 'test_host_0', 1, 0, 1, (now + 2), 'darth vader', 'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])

        self.schedulers['scheduler-master'].sched.brokers['broker-master']['broks'] = {}

        cmd = "[{0}] REMOVE_HOST_ACKNOWLEDGEMENT;{1}\n". \
            format(int(now), 'test_host_0')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.scheduler_loop(3, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])

        brok_ack_raise = []
        brok_ack_expire = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master']['broks'].itervalues():
            if brok.type == 'acknowledge_raise':
                brok_ack_raise.append(brok)
            elif brok.type == 'acknowledge_expire':
                brok_ack_expire.append(brok)

        assert len(brok_ack_raise) == 0
        assert len(brok_ack_expire) == 1

        hdata = unserialize(brok_ack_expire[0].data)
        assert hdata['host'] == 'test_host_0'
        assert 'service' not in hdata

    def test_fixed_downtime_service(self):
        """Test broks when downtime

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
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
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.external_command_loop()
        self.external_command_loop()

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master'][
            'broks'].itervalues():
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
        self.schedulers['scheduler-master'].sched.brokers['broker-master']['broks'] = {}
        time.sleep(5)
        self.scheduler_loop(2, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master'][
            'broks'].itervalues():
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

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
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
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.external_command_loop()
        self.external_command_loop()

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master'][
            'broks'].itervalues():
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
        self.schedulers['scheduler-master'].sched.brokers['broker-master']['broks'] = {}
        time.sleep(5)
        self.scheduler_loop(2, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master'][
            'broks'].itervalues():
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

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
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
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.scheduler_loop(2, [[host, 0, 'UP'], [svc, 0, 'OK']])

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master'][
            'broks'].itervalues():
            if brok.type == 'downtime_raise':
                brok_downtime_raise.append(brok)
            elif brok.type == 'downtime_expire':
                brok_downtime_expire.append(brok)

        assert len(brok_downtime_raise) == 0
        assert len(brok_downtime_expire) == 0

        time.sleep(1)
        self.scheduler_loop(3, [[host, 0, 'UP'], [svc, 2, 'CRITICAL']])

        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master'][
            'broks'].itervalues():
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

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP']])

        duration = 5
        now = int(time.time())
        # downtime valid for 5 seconds from now
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%d;%d;1;0;%d;" \
              "downtime author;downtime comment" % (now, now, now + duration, duration)
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.external_command_loop()

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master'][
            'broks'].itervalues():
            if brok.type == 'downtime_raise':
                brok_downtime_raise.append(brok)
            elif brok.type == 'downtime_expire':
                brok_downtime_expire.append(brok)

        assert len(brok_downtime_raise) == 1
        assert len(brok_downtime_expire) == 0

        # External command: delete all host downtime
        now = int(time.time())
        self.schedulers['scheduler-master'].sched.brokers['broker-master']['broks'] = {}
        cmd = '[%d] DEL_ALL_SVC_DOWNTIMES;test_host_0;test_ok_0' % now
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.external_command_loop()

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master'][
            'broks'].itervalues():
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

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP']])

        duration = 5
        now = int(time.time())
        # downtime valid for 5 seconds from now
        cmd = "[%lu] SCHEDULE_HOST_DOWNTIME;test_host_0;%d;%d;1;0;%d;" \
              "downtime author;downtime comment" % (now, now, now + duration, duration)
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.external_command_loop()

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master'][
            'broks'].itervalues():
            if brok.type == 'downtime_raise':
                brok_downtime_raise.append(brok)
            elif brok.type == 'downtime_expire':
                brok_downtime_expire.append(brok)

        assert len(brok_downtime_raise) == 1
        assert len(brok_downtime_expire) == 0

        # External command: delete all host downtime
        now = int(time.time())
        self.schedulers['scheduler-master'].sched.brokers['broker-master']['broks'] = {}
        cmd = '[%d] DEL_ALL_HOST_DOWNTIMES;test_host_0' % now
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.external_command_loop()

        brok_downtime_raise = []
        brok_downtime_expire = []
        for brok in self.schedulers['scheduler-master'].sched.brokers['broker-master'][
            'broks'].itervalues():
            if brok.type == 'downtime_raise':
                brok_downtime_raise.append(brok)
            elif brok.type == 'downtime_expire':
                brok_downtime_expire.append(brok)

        assert len(brok_downtime_raise) == 0
        assert len(brok_downtime_expire) == 1

        hdata = unserialize(brok_downtime_expire[0].data)
        assert hdata['host'] == 'test_host_0'
