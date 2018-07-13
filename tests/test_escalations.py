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
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Jean Gabes, naparuba@gmail.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     Grégory Starck, g.starck@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Sebastien Coavoux, s.coavoux@free.fr

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

"""
 This file is used to test escalations.
"""

import time
import datetime
from freezegun import freeze_time
from alignak.misc.serialization import unserialize
from alignak.objects.escalation import Escalation
from alignak.objects.serviceescalation import Serviceescalation

from .alignak_test import AlignakTest

class TestEscalations(AlignakTest):
    """
    This class tests for escalations
    """
    def setUp(self):
        super(TestEscalations, self).setUp()

        self.setup_with_file('./cfg/cfg_escalations.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

    def test_wildcard_in_service_description(self):
        """ Test wildcards in service description """
        self_generated = [e for e in self._scheduler.pushed_conf.escalations
                          if e.escalation_name.startswith('Generated-SE-')]
        host_services = self._scheduler.services.find_srvs_by_hostname("test_host_0_esc")

        # Todo: confirm this assertion
        # We only found one, but there are 3 services for this host ... perharps normal?
        assert 1 == len(self_generated)
        assert 3 == len(host_services)

        # We must find at least one self generated escalation in our host services
        for svc in host_services:
            print(("Service: %s" % self._scheduler.services[svc]))
            assert self_generated[0].uuid in self._scheduler.services[svc].escalations

    def test_simple_escalation(self):
        """ Test a simple escalation (NAGIOS legacy) """
        del self._main_broker.broks[:]

        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'tick_manage_internal_checks': 10})

        # Get host and services
        host = self._scheduler.hosts.find_by_name("test_host_0_esc")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0_esc",
                                                                     "test_svc_esc")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # ignore the host
        svc.event_handler_enabled = False
        # The service has 3 defined escalations:
        assert 3 == len(svc.escalations)

        # Service escalation levels
        # Generated service escalation has a name based upon SE uuid ... too hard to get it simply:)
        # self_generated = self._scheduler.escalations.find_by_name('Generated-ServiceEscalation-%s-%s')
        # self.assertIsNotNone(self_generated)
        # self.assertIs(self_generated, Serviceescalation)
        # self.assertIn(self_generated.uuid, svc.escalations)

        tolevel2 = self._scheduler.escalations.find_by_name('ToLevel2')
        assert tolevel2 is not None
        self.assertIsInstance(tolevel2, Escalation)
        assert tolevel2.uuid in svc.escalations

        tolevel3 = self._scheduler.escalations.find_by_name('ToLevel3')
        assert tolevel3 is not None
        self.assertIsInstance(tolevel3, Escalation)
        assert tolevel3.uuid in svc.escalations

        # 1 notification pet minute
        svc.notification_interval = 1

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2018, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime

            #--------------------------------------------------------------
            # initialize host/service state
            #--------------------------------------------------------------
            self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
            assert "HARD" == host.state_type
            assert "UP" == host.state
            assert 0 == host.current_notification_number

            assert "HARD" == svc.state_type
            assert "OK" == svc.state
            assert 0 == svc.current_notification_number

            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))

            # Service goes to CRITICAL/SOFT
            self.scheduler_loop(1, [[svc, 2, 'BAD']])
            assert "SOFT" == svc.state_type
            assert "CRITICAL" == svc.state
            # No notification...
            assert 0 == svc.current_notification_number

            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))
            # ---
            # 1/
            # ---
            # Service goes to CRITICAL/HARD
            self.scheduler_loop(1, [[svc, 2, 'BAD']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "HARD" == svc.state_type
            assert "CRITICAL" == svc.state
            # Service notification number must be 1
            assert 1 == svc.current_notification_number
            cnn = svc.current_notification_number

            # We did not yet got an escalated notification
            assert 0 == len([n.escalated for n in list(self._scheduler.actions.values()) if n.escalated])

            # We should have had 2 ALERT and a NOTIFICATION to the service defined contact
            # We also have a notification to level1 contact which is a contact defined for the host
            expected_logs = [
                ('info',
                 'ACTIVE HOST CHECK: test_host_0_esc;UP;0;UP'),
                ('info',
                 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc;OK;0;OK'),
                ('error',
                 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc;CRITICAL;1;BAD'),
                ('error',
                 'SERVICE ALERT: test_host_0_esc;test_svc_esc;CRITICAL;SOFT;1;BAD'),
                ('error',
                 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc;CRITICAL;1;BAD'),
                ('error',
                 'SERVICE ALERT: test_host_0_esc;test_svc_esc;CRITICAL;HARD;2;BAD'),
                ('error',
                 'SERVICE NOTIFICATION: test_contact;test_host_0_esc;test_svc_esc;CRITICAL;1;notify-service;BAD'),
                ('error',
                 'SERVICE NOTIFICATION: level1;test_host_0_esc;test_svc_esc;CRITICAL;1;notify-service;BAD'),
            ]
            self.check_monitoring_events_log(expected_logs, dump=True)

            # ---
            # 2/
            # ---
            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))
            # Service is now CRITICAL/HARD
            self.scheduler_loop(1, [[svc, 2, 'BAD']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)

            # Service notification number increased
            assert 2 == svc.current_notification_number

            # We got an escalated notification
            assert 1 == len([n.escalated for n in list(self._scheduler.actions.values()) if n.escalated])

            # Now also notified to the level2
            expected_logs += [
                ('error',
                 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc;CRITICAL;2;BAD'),
                ('error',
                 'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc;CRITICAL;2;notify-service;BAD')
            ]
            self.check_monitoring_events_log(expected_logs)

            # ---
            # 3/
            # ---
            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))
            # Service is still CRITICAL/HARD
            self.scheduler_loop(1, [[svc, 2, 'BAD']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)

            # Service notification number increased
            assert 3 == svc.current_notification_number

            # We got one more escalated notification
            assert 2 == len([n.escalated for n in list(self._scheduler.actions.values()) if n.escalated])
            expected_logs += [
                ('error', 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc;CRITICAL;2;BAD'),
                ('error', 'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc;'
                           'CRITICAL;3;notify-service;BAD')
            ]
            self.check_monitoring_events_log(expected_logs)

            # ---
            # 4/
            # ---
            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))
            # Service is still CRITICAL/HARD
            self.scheduler_loop(1, [[svc, 2, 'BAD']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)

            # Service notification number increased
            assert 4 == svc.current_notification_number

            # We got one more escalated notification
            assert 3 == len([n.escalated for n in list(self._scheduler.actions.values()) if n.escalated])
            expected_logs += [
                ('error', 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc;CRITICAL;2;BAD'),
                ('error', 'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc;'
                           'CRITICAL;4;notify-service;BAD')
            ]
            self.check_monitoring_events_log(expected_logs)

            # ---
            # 5/
            # ---
            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))
            # Service is still CRITICAL/HARD
            self.scheduler_loop(1, [[svc, 2, 'BAD']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)

            # Service notification number increased
            assert 5 == svc.current_notification_number

            # We got one more escalated notification
            assert 4 == len([n.escalated for n in list(self._scheduler.actions.values()) if n.escalated])
            expected_logs += [
                ('error', 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc;CRITICAL;2;BAD'),
                ('error', 'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc;'
                           'CRITICAL;4;notify-service;BAD'),
            ]
            self.check_monitoring_events_log(expected_logs)

            # ---
            # 6/
            # ---
            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))
            # Service is still CRITICAL/HARD
            self.scheduler_loop(1, [[svc, 2, 'BAD']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)

            # Service notification number increased
            assert 6 == svc.current_notification_number

            # We got one more escalated notification but we notified level 3 !
            assert 5 == len([n.escalated for n in list(self._scheduler.actions.values()) if n.escalated])
            expected_logs += [
                ('error', 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc;CRITICAL;2;BAD'),
                ('error', 'SERVICE NOTIFICATION: level3;test_host_0_esc;test_svc_esc;'
                           'CRITICAL;5;notify-service;BAD')
            ]
            self.check_monitoring_events_log(expected_logs)

            # ---
            # 7/
            # ---
            # Now we send 10 more alerts and we are still always notifying only level3
            for i in range(10):
                # Time warp
                frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))
                # Service is still CRITICAL/HARD
                # time.sleep(.2)
                self.scheduler_loop(1, [[svc, 2, 'BAD']])
                # The notifications are created to be launched in the next second when they happen !
                # Time warp 1 second
                frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
                self.scheduler_loop(1)

                # Service notification number increased
                assert 7 + i == svc.current_notification_number

                # We got one more escalated notification
                assert 6 + i == \
                                 len([n.escalated for n in
                                      list(self._scheduler.actions.values()) if n.escalated])
                expected_logs += [
                    ('error', 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc;CRITICAL;2;BAD'),
                    ('error', 'SERVICE NOTIFICATION: level3;test_host_0_esc;test_svc_esc;'
                               'CRITICAL;%d;notify-service;BAD' % (7 + i))
                ]
                self.check_monitoring_events_log(expected_logs)

            # ---
            # 8/
            # ---
            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))
            # The service recovers, all the notified contact will be contacted
            self.scheduler_loop(2, [[svc, 0, 'OK']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            expected_logs += [
                ('info', 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc;OK;2;OK'),
                ('info', 'SERVICE ALERT: test_host_0_esc;test_svc_esc;OK;HARD;2;OK'),
                ('info', 'SERVICE NOTIFICATION: test_contact;test_host_0_esc;test_svc_esc;'
                          'OK;0;notify-service;OK'),
                ('info', 'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc;'
                          'OK;0;notify-service;OK'),
                ('info', 'SERVICE NOTIFICATION: level1;test_host_0_esc;test_svc_esc;'
                          'OK;0;notify-service;OK'),
                ('info', 'SERVICE NOTIFICATION: level3;test_host_0_esc;test_svc_esc;'
                          'OK;0;notify-service;OK'),
                ('info', 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc;OK;1;OK')
            ]
            self.check_monitoring_events_log(expected_logs)

    def test_time_based_escalation(self):
        """ Time based escalations """
        del self._main_broker.broks[:]

        self._scheduler.pushed_conf.tick_manage_internal_checks = 7200
        self._scheduler.update_recurrent_works_tick({'tick_manage_internal_checks': 7200})

        # Get host and services
        host = self._scheduler.hosts.find_by_name("test_host_0_esc")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the default router
        host.passive_checks_enabled = False
        print("Host check: %s / %s / %s / %s"
              % (host.active_checks_enabled, host.passive_checks_enabled,
                 host.check_freshness, host.freshness_threshold))
        host.check_interval = 7200
        host.retry_interval = 7200
        print("Host check: %s / %s / %s"
              % (host.check_period, host.check_interval, host.retry_interval))
        print("Host check command: %s" % (host.check_command))
        host.notification_interval = 1200
        print("Host notifications: %s / %s / %s"
              % (host.notification_interval, host.notification_period, host.notification_options))

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0_esc",
                                                                     "test_svc_esc_time")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # ignore the host
        svc.event_handler_enabled = False
        # The service has 3 defined escalations:
        assert 3 == len(svc.escalations)

        # Service escalation levels
        # Generated service escalation has a name based upon SE uuid ... too hard to get it simply:)
        # self_generated = self._scheduler.escalations.find_by_name('Generated-ServiceEscalation-%s-%s')
        # self.assertIsNotNone(self_generated)
        # self.assertIs(self_generated, Serviceescalation)
        # self.assertIn(self_generated.uuid, svc.escalations)

        tolevel2 = self._scheduler.escalations.find_by_name('ToLevel2-time')
        assert tolevel2 is not None
        print("Esc: %s / %s" % (type(tolevel2), tolevel2))
        self.assertIsInstance(tolevel2, Escalation)
        assert tolevel2.uuid in svc.escalations

        tolevel3 = self._scheduler.escalations.find_by_name('ToLevel3-time')
        assert tolevel3 is not None
        self.assertIsInstance(tolevel3, Escalation)
        assert tolevel3.uuid in svc.escalations

        # 1 notification per minute
        svc.notification_interval = 1

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2018, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime

            #--------------------------------------------------------------
            # initialize host/service state
            #--------------------------------------------------------------
            self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
            assert "HARD" == host.state_type
            assert "UP" == host.state
            assert 0 == host.current_notification_number

            assert "HARD" == svc.state_type
            assert "OK" == svc.state
            assert 0 == svc.current_notification_number

            # We should have had 2 ALERT and a NOTIFICATION to the service defined contact
            # We also have a notification to level1 contact which is a contact defined for the host
            expected_logs = [
                ('info',
                 'ACTIVE HOST CHECK: test_host_0_esc;UP;0;UP'),
                ('info',
                 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc_time;OK;0;OK'),
            ]
            self.check_monitoring_events_log(expected_logs)

            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))

            # Service goes to CRITICAL/SOFT
            self.scheduler_loop(1, [[svc, 2, 'BAD']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "SOFT" == svc.state_type
            assert "CRITICAL" == svc.state
            # No notification...
            assert 0 == svc.current_notification_number

            # We should have had 2 ALERT and a NOTIFICATION to the service defined contact
            # We also have a notification to level1 contact which is a contact defined for the host
            expected_logs += [
                ('error',
                 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc_time;CRITICAL;1;BAD'),
                ('error',
                 'SERVICE ALERT: test_host_0_esc;test_svc_esc_time;CRITICAL;SOFT;1;BAD')
            ]
            self.check_monitoring_events_log(expected_logs)

            # ---
            # 1/
            # ---
            # Service goes to CRITICAL/HARD
            time.sleep(1)
            self.scheduler_loop(1, [[svc, 2, 'BAD']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "HARD" == svc.state_type
            assert "CRITICAL" == svc.state
            # Service notification number must be 1
            assert 1 == svc.current_notification_number
            cnn = svc.current_notification_number

            # We did not yet got an escalated notification
            assert 0 == len([n.escalated for n in list(self._scheduler.actions.values()) if n.escalated])

            # We should have had 2 ALERT and a NOTIFICATION to the service defined contact
            # We also have a notification to level1 contact which is a contact defined for the host
            expected_logs += [
                ('error',
                 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc_time;CRITICAL;1;BAD'),
                ('error',
                 'SERVICE ALERT: test_host_0_esc;test_svc_esc_time;CRITICAL;SOFT;1;BAD'),
                ('error',
                 'SERVICE NOTIFICATION: level1;test_host_0_esc;test_svc_esc_time;CRITICAL;1;notify-service;BAD'),
                ('error',
                 'SERVICE NOTIFICATION: test_contact;test_host_0_esc;test_svc_esc_time;CRITICAL;1;notify-service;BAD'),
            ]
            self.check_monitoring_events_log(expected_logs)

            # ---
            # time warp ... 5 minutes later !
            # ---
            frozen_datetime.tick(delta=datetime.timedelta(minutes=5, seconds=1))

            # ---
            # 2/
            # ---
            # Service is still CRITICAL/HARD
            self.scheduler_loop(1, [[svc, 2, 'BAD']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)

            # Service notification number increased
            assert 2 == svc.current_notification_number

            # We got 1 escalated notification
            assert 1 == len([n.escalated for n in list(self._scheduler.actions.values()) if n.escalated])

            # Now also notified to the level2
            expected_logs += [
                ('error',
                 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc_time;CRITICAL;2;BAD'),
                # ('info',
                #  'ACTIVE HOST CHECK: test_host_0_esc;UP;HARD;1;Host assumed to be UP'),
                ('error',
                 'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc_time;CRITICAL;2;notify-service;BAD'),
            ]
            self.check_monitoring_events_log(expected_logs)

            # ---
            # time warp ... 5 minutes later !
            # ---
            frozen_datetime.tick(delta=datetime.timedelta(minutes=5, seconds=1))

            # ---
            # 3/
            # ---
            # Service is still CRITICAL/HARD
            self.scheduler_loop(1, [[svc, 2, 'BAD']])
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)

            # Service notification number increased
            assert 3 == svc.current_notification_number

            # We got 1 more escalated notification
            assert 2 == len([n.escalated for n in list(self._scheduler.actions.values()) if n.escalated])
            expected_logs += [
                ('error',
                 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc_time;CRITICAL;2;BAD'),
                ('error',
                 'SERVICE NOTIFICATION: level3;test_host_0_esc;test_svc_esc_time;CRITICAL;3;notify-service;BAD'),
            ]
            self.check_monitoring_events_log(expected_logs)

            # ---
            # time warp ... 5 minutes later !
            # ---
            frozen_datetime.tick(delta=datetime.timedelta(minutes=5, seconds=1))

            # ---
            # 4/
            # ---
            # Service is still CRITICAL/HARD
            self.scheduler_loop(1, [[svc, 2, 'BAD']])
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)

            # Service notification number increased
            assert 4 == svc.current_notification_number

            # We got one more escalated notification
            assert 3 == len([n.escalated for n in list(self._scheduler.actions.values()) if n.escalated])
            expected_logs += [
                ('error', 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc_time;CRITICAL;2;BAD'),
                ('error', 'SERVICE NOTIFICATION: level3;test_host_0_esc;test_svc_esc_time;'
                          'CRITICAL;3;notify-service;BAD'),
                # ('info',
                #  'ACTIVE HOST CHECK: test_host_0_esc;UP;HARD;1;Host assumed to be UP'),
            ]
            self.check_monitoring_events_log(expected_logs)

            # ---
            # 5/
            # ---
            # Now we send 10 more alerts and we are still always notifying only level3
            for i in range(10):
                # ---
                # time warp ... 5 minutes later !
                # ---
                frozen_datetime.tick(delta=datetime.timedelta(minutes=5, seconds=1))

                # Service is still CRITICAL/HARD
                self.scheduler_loop(1, [[svc, 2, 'BAD']])
                # Time warp 1 second
                frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
                self.scheduler_loop(1)

                # Service notification number increased
                assert 5 + i == svc.current_notification_number

                # We got one more escalated notification
                assert 4 + i == len([n.escalated for n in
                                     list(self._scheduler.actions.values()) if n.escalated])
                expected_logs += [
                    ('error',
                     'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc_time;CRITICAL;2;BAD'),
                    ('error',
                     'SERVICE NOTIFICATION: level3;test_host_0_esc;test_svc_esc_time;'
                     'CRITICAL;%d;notify-service;BAD' % (5 + i)),
                ]
                self.check_monitoring_events_log(expected_logs)

            # ---
            # 6/ 1 hour later!
            # ---
            # ---
            # time warp ... 5 minutes later !
            # ---
            frozen_datetime.tick(delta=datetime.timedelta(minutes=60))

            # Service is still CRITICAL/HARD
            self.scheduler_loop(1, [[svc, 2, 'BAD']])
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)

            # Service notification number increased
            assert 15 == svc.current_notification_number

            # We got one more escalated notification
            assert 15 == len([n.escalated for n in
                              list(self._scheduler.actions.values()) if n.escalated])
            expected_logs += [
                ('error',
                 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc_time;CRITICAL;2;BAD'),
                ('error',
                 'SERVICE NOTIFICATION: all_services_1_hour;test_host_0_esc;test_svc_esc_time;'
                 'CRITICAL;15;notify-service;BAD'),
                ('error',
                 'SERVICE NOTIFICATION: level3;test_host_0_esc;test_svc_esc_time;'
                 'CRITICAL;15;notify-service;BAD'),
            ]
            self.check_monitoring_events_log(expected_logs)

            # ---
            # 7/
            # ---
            # ---
            # time warp ... 5 minutes later !
            # ---
            frozen_datetime.tick(delta=datetime.timedelta(minutes=5, seconds=1))

            # The service recovers, all the notified contact will be contacted
            self.scheduler_loop(1, [[svc, 0, 'OK']])
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            expected_logs += [
                ('info',
                 'ACTIVE SERVICE CHECK: test_host_0_esc;test_svc_esc_time;OK;2;OK'),
                ('info',
                 'SERVICE ALERT: test_host_0_esc;test_svc_esc_time;OK;HARD;2;OK'),
                ('info',
                 'SERVICE NOTIFICATION: all_services_1_hour;test_host_0_esc;test_svc_esc_time;'
                 'OK;0;notify-service;OK'),
                ('info',
                 'SERVICE NOTIFICATION: test_contact;test_host_0_esc;test_svc_esc_time;'
                 'OK;0;notify-service;OK'),
                ('info',
                 'SERVICE NOTIFICATION: level3;test_host_0_esc;test_svc_esc_time;'
                 'OK;0;notify-service;OK'),
                ('info',
                 'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc_time;'
                 'OK;0;notify-service;OK'),
                ('info',
                 'SERVICE NOTIFICATION: level1;test_host_0_esc;test_svc_esc_time;'
                 'OK;0;notify-service;OK')
            ]
            self.check_monitoring_events_log(expected_logs)
