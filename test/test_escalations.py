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
from alignak.misc.serialization import unserialize
from alignak.objects.escalation import Escalation
from alignak.objects.serviceescalation import Serviceescalation

from alignak_test import AlignakTest, unittest, time_hacker

class TestEscalations(AlignakTest):
    """
    This class tests for escalations
    """
    def setUp(self):
        """
        For each test load and check the configuration
        :return: None
        """
        self.print_header()
        self.setup_with_file('./cfg/cfg_escalations.cfg')
        assert self.conf_is_correct

        # Our scheduler
        self._sched = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._sched.brokers['broker-master']

        # No error messages
        assert len(self.configuration_errors) == 0
        # Some warnings are emitted for information...
        self.show_configuration_logs()
        # assert len(self.configuration_warnings) == 5

        time_hacker.set_real_time()

    def check_monitoring_logs(self, expected_logs, dump=False):
        """

        :param expected_logs: expected monitoring logs
        :param dump: True to print out the monitoring logs
        :return:
        """
        # Our scheduler
        self._sched = self.schedulers['scheduler-master'].sched
        # Our broker
        self._broker = self._sched.brokers['broker-master']

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in sorted(self._broker['broks'].itervalues(), key=lambda x: x.creation_time):
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))
        if dump:
            print("Monitoring logs: %s" % monitoring_logs)

        for log_level, log_message in expected_logs:
            assert (log_level, log_message) in monitoring_logs

        assert len(expected_logs) == len(monitoring_logs), monitoring_logs

    def test_wildcard_in_service_description(self):
        """ Test wildcards in service description """
        self.print_header()

        self_generated = [e for e in self._sched.conf.escalations
                          if e.escalation_name.startswith('Generated-ServiceEscalation-')]
        host_services = self._sched.services.find_srvs_by_hostname("test_host_0_esc")

        # Todo: confirm this assertion
        # We only found one, but there are 3 services for this host ... perharps normal?
        assert 1 == len(self_generated)
        assert 3 == len(host_services)

        # We must find at least one self generated escalation in our host services
        for svc in host_services:
            print("Service: %s" % self._sched.services[svc])
            assert self_generated[0].uuid in self._sched.services[svc].escalations

    def test_simple_escalation(self):
        """ Test a simple escalation (NAGIOS legacy) """
        self.print_header()

        # Get host and services
        host = self._sched.hosts.find_by_name("test_host_0_esc")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0_esc",
                                                                 "test_svc_esc")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # ignore the host
        svc.event_handler_enabled = False
        # The service has 3 defined escalations: 2 in services and 1 global
        assert 3 == len(svc.escalations)

        # Service escalation levels
        # Generated service escalation has a name based upon SE uuid ... too hard to get it simply:)
        # self_generated = self._sched.escalations.find_by_name('Generated-ServiceEscalation-%s-%s')
        # self.assertIsNotNone(self_generated)
        # self.assertIs(self_generated, Serviceescalation)
        # self.assertIn(self_generated.uuid, svc.escalations)

        tolevel2 = self._sched.escalations.find_by_name('ToLevel2')
        assert tolevel2 is not None
        # Todo: do not match any of both assertions ... wtf?
        # self.assertIs(tolevel2, Serviceescalation)
        # self.assertIs(tolevel2, Escalation)
        assert tolevel2.uuid in svc.escalations

        tolevel3 = self._sched.escalations.find_by_name('ToLevel3')
        assert tolevel3 is not None
        # Todo: do not match any of both assertions ... wtf?
        # self.assertIs(tolevel3, Serviceescalation)
        # self.assertIs(tolevel3, Escalation)
        assert tolevel3.uuid in svc.escalations

        # To make tests quicker we make notifications sent very quickly
        svc.notification_interval = 0.001

        #--------------------------------------------------------------
        # initialize host/service state
        #--------------------------------------------------------------
        self.scheduler_loop(1, [
            [host, 0, 'UP'], [svc, 0, 'OK']
        ])
        assert "HARD" == host.state_type
        assert "UP" == host.state
        assert 0 == host.current_notification_number

        assert "HARD" == svc.state_type
        assert "OK" == svc.state
        assert 0 == svc.current_notification_number

        # Service goes to CRITICAL/SOFT
        self.scheduler_loop(1, [[svc, 2, 'BAD']])
        assert "SOFT" == svc.state_type
        assert "CRITICAL" == svc.state
        # No notification...
        assert 0 == svc.current_notification_number

        # ---
        # 1/
        # ---
        # Service goes to CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 2, 'BAD']])
        assert "HARD" == svc.state_type
        assert "CRITICAL" == svc.state
        # Service notification number must be 1
        assert 1 == svc.current_notification_number
        cnn = svc.current_notification_number

        # We did not yet got an escalated notification
        assert 0 == len([n.escalated for n in self._sched.actions.values() if n.escalated])

        # We should have had 2 ALERT and a NOTIFICATION to the service defined contact
        # We also have a notification to level1 contact which is a contact defined for the host
        expected_logs = [
            (u'error', u'SERVICE ALERT: test_host_0_esc;test_svc_esc;CRITICAL;SOFT;1;BAD'),
            (u'error', u'SERVICE ALERT: test_host_0_esc;test_svc_esc;CRITICAL;HARD;2;BAD'),
            (u'error', u'SERVICE NOTIFICATION: test_contact;test_host_0_esc;test_svc_esc;'
                       u'CRITICAL;notify-service;BAD'),
            (u'error', u'SERVICE NOTIFICATION: level1;test_host_0_esc;test_svc_esc;'
                       u'CRITICAL;notify-service;BAD')
        ]
        self.check_monitoring_logs(expected_logs)

        # ---
        # 2/
        # ---
        # Service is still CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 2, 'BAD']])

        # Service notification number increased
        assert 2 == svc.current_notification_number

        # We got an escalated notification
        assert 1 == len([n.escalated for n in self._sched.actions.values() if n.escalated])

        # Now also notified to the level2
        expected_logs += [
            (u'error', u'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc;'
                       u'CRITICAL;notify-service;BAD')
        ]
        self.check_monitoring_logs(expected_logs)

        # ---
        # 3/
        # ---
        # Service is still CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 2, 'BAD']])

        # Service notification number increased
        assert 3 == svc.current_notification_number

        # We got one more escalated notification
        assert 2 == len([n.escalated for n in self._sched.actions.values() if n.escalated])
        expected_logs += [
            (u'error', u'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc;'
                       u'CRITICAL;notify-service;BAD')
        ]
        self.check_monitoring_logs(expected_logs)

        # ---
        # 4/
        # ---
        # Service is still CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 2, 'BAD']])

        # Service notification number increased
        assert 4 == svc.current_notification_number

        # We got one more escalated notification
        assert 3 == len([n.escalated for n in self._sched.actions.values() if n.escalated])
        expected_logs += [
            (u'error', u'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc;'
                       u'CRITICAL;notify-service;BAD')
        ]
        self.check_monitoring_logs(expected_logs)

        # ---
        # 5/
        # ---
        # Service is still CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 2, 'BAD']])

        # Service notification number increased
        assert 5 == svc.current_notification_number

        # We got one more escalated notification
        assert 4 == len([n.escalated for n in self._sched.actions.values() if n.escalated])
        expected_logs += [
            (u'error', u'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc;'
                       u'CRITICAL;notify-service;BAD'),
        ]
        self.check_monitoring_logs(expected_logs)

        # ---
        # 6/
        # ---
        # Service is still CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 2, 'BAD']])

        # Service notification number increased
        assert 6 == svc.current_notification_number

        # We got one more escalated notification but we notified level 3 !
        assert 5 == len([n.escalated for n in self._sched.actions.values() if n.escalated])
        expected_logs += [
            (u'error', u'SERVICE NOTIFICATION: level3;test_host_0_esc;test_svc_esc;'
                       u'CRITICAL;notify-service;BAD')
        ]
        self.check_monitoring_logs(expected_logs)

        # ---
        # 7/
        # ---
        # Now we send 10 more alerts and we are still always notifying only level3
        for i in range(10):
            # Service is still CRITICAL/HARD
            time.sleep(.2)
            self.scheduler_loop(1, [[svc, 2, 'BAD']])

            # Service notification number increased
            assert 7 + i == svc.current_notification_number

            # We got one more escalated notification
            assert 6 + i == \
                             len([n.escalated for n in
                                  self._sched.actions.values() if n.escalated])
            expected_logs += [
                (u'error', u'SERVICE NOTIFICATION: level3;test_host_0_esc;test_svc_esc;'
                           u'CRITICAL;notify-service;BAD')
            ]
            self.check_monitoring_logs(expected_logs)

        # ---
        # 8/
        # ---
        # The service recovers, all the notified contact will be contacted
        self.scheduler_loop(2, [[svc, 0, 'OK']])
        expected_logs += [
            (u'info', u'SERVICE ALERT: test_host_0_esc;test_svc_esc;OK;HARD;2;OK'),
            (u'info', u'SERVICE NOTIFICATION: test_contact;test_host_0_esc;test_svc_esc;'
                      u'OK;notify-service;OK'),
            (u'info', u'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc;'
                      u'OK;notify-service;OK'),
            (u'info', u'SERVICE NOTIFICATION: level1;test_host_0_esc;test_svc_esc;'
                      u'OK;notify-service;OK'),
            (u'info', u'SERVICE NOTIFICATION: level3;test_host_0_esc;test_svc_esc;'
                      u'OK;notify-service;OK')
        ]
        self.check_monitoring_logs(expected_logs)

    def test_time_based_escalation(self):
        """ Time based escalations """
        self.print_header()

        # Get host and services
        host = self._sched.hosts.find_by_name("test_host_0_esc")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0_esc",
                                                                 "test_svc_esc_time")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # ignore the host
        svc.event_handler_enabled = False
        # The service has 3 defined escalations:
        assert 3 == len(svc.escalations)

        # Service escalation levels
        # Generated service escalation has a name based upon SE uuid ... too hard to get it simply:)
        # self_generated = self._sched.escalations.find_by_name('Generated-ServiceEscalation-%s-%s')
        # self.assertIsNotNone(self_generated)
        # self.assertIs(self_generated, Serviceescalation)
        # self.assertIn(self_generated.uuid, svc.escalations)

        tolevel2 = self._sched.escalations.find_by_name('ToLevel2-time')
        assert tolevel2 is not None
        # Todo: do not match any of both assertions ... wtf?
        # self.assertIs(tolevel2, Serviceescalation)
        # self.assertIs(tolevel2, Escalation)
        assert tolevel2.uuid in svc.escalations

        tolevel3 = self._sched.escalations.find_by_name('ToLevel3-time')
        assert tolevel3 is not None
        # Todo: do not match any of both assertions ... wtf?
        # self.assertIs(tolevel3, Serviceescalation)
        # self.assertIs(tolevel3, Escalation)
        assert tolevel3.uuid in svc.escalations

        # To make tests quicker we make notifications sent very quickly
        svc.notification_interval = 0.001

        #--------------------------------------------------------------
        # initialize host/service state
        #--------------------------------------------------------------
        self.scheduler_loop(1, [
            [host, 0, 'UP'], [svc, 0, 'OK']
        ])
        assert "HARD" == host.state_type
        assert "UP" == host.state
        assert 0 == host.current_notification_number

        assert "HARD" == svc.state_type
        assert "OK" == svc.state
        assert 0 == svc.current_notification_number

        # Service goes to CRITICAL/SOFT
        self.scheduler_loop(1, [[svc, 2, 'BAD']])
        assert "SOFT" == svc.state_type
        assert "CRITICAL" == svc.state
        # No notification...
        assert 0 == svc.current_notification_number

        # ---
        # 1/
        # ---
        # Service goes to CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 2, 'BAD']])
        assert "HARD" == svc.state_type
        assert "CRITICAL" == svc.state
        # Service notification number must be 1
        assert 1 == svc.current_notification_number
        cnn = svc.current_notification_number

        # We did not yet got an escalated notification
        assert 0 == len([n.escalated for n in self._sched.actions.values() if n.escalated])

        # We should have had 2 ALERT and a NOTIFICATION to the service defined contact
        # We also have a notification to level1 contact which is a contact defined for the host
        expected_logs = [
            (u'error', u'SERVICE ALERT: test_host_0_esc;test_svc_esc_time;CRITICAL;SOFT;1;BAD'),
            (u'error', u'SERVICE ALERT: test_host_0_esc;test_svc_esc_time;CRITICAL;HARD;2;BAD'),
            (u'error', u'SERVICE NOTIFICATION: test_contact;test_host_0_esc;test_svc_esc_time;'
                       u'CRITICAL;notify-service;BAD'),
            (u'error', u'SERVICE NOTIFICATION: level1;test_host_0_esc;test_svc_esc_time;'
                       u'CRITICAL;notify-service;BAD')
        ]
        self.check_monitoring_logs(expected_logs)

        # ---
        # time warp :)
        # ---
        # For the test, we hack the notification value because we do not want to wait 1 hour!
        for n in svc.notifications_in_progress.values():
            # We say that it's already 3600 seconds since the last notification
            svc.notification_interval = 3600
            # and we say that there is still 1 hour since the notification creation
            # so it will say the notification time is huge, and it will escalade
            n.creation_time = n.creation_time - 3600

        # ---
        # 2/
        # ---
        # Service is still CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 2, 'BAD']])

        # Service notification number increased
        assert 2 == svc.current_notification_number

        # Todo: check if it should be ok - test_contact notification is considered escalated.
        # We got 2 escalated notifications!
        assert 2 == len([n.escalated for n in self._sched.actions.values() if n.escalated])

        # Now also notified to the level2 and a second notification to the service defined contact
        expected_logs += [
            (u'error', u'SERVICE NOTIFICATION: test_contact;test_host_0_esc;test_svc_esc_time;'
                       u'CRITICAL;notify-service;BAD'),
            (u'error', u'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc_time;'
                       u'CRITICAL;notify-service;BAD')
        ]
        self.check_monitoring_logs(expected_logs)

        # ---
        # time warp :)
        # ---
        # For the test, we hack the notification value because we do not want to wait 1 hour!
        for n in svc.notifications_in_progress.values():
            # Notifications must be raised now...
            n.t_to_go = time.time()

        # ---
        # 3/
        # ---
        # Service is still CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 2, 'BAD']])

        # Service notification number increased
        assert 3 == svc.current_notification_number

        # We got 2 more escalated notification
        assert 4 == len([n.escalated for n in self._sched.actions.values() if n.escalated])
        expected_logs += [
            (u'error', u'SERVICE NOTIFICATION: test_contact;test_host_0_esc;test_svc_esc_time;'
                       u'CRITICAL;notify-service;BAD'),
            (u'error', u'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc_time;'
                       u'CRITICAL;notify-service;BAD')
        ]
        self.check_monitoring_logs(expected_logs)

        # ---
        # time warp :)
        # ---
        # Now we go for level3, so again we say: he, in fact we start one hour earlyer,
        # so the total notification duration is near 2 hour, so we will raise level3
        for n in svc.notifications_in_progress.values():
            # We say that it's already 3600 seconds since the last notification
            n.t_to_go = time.time()
            n.creation_time = n.creation_time - 3600

        # ---
        # 4/
        # ---
        # Service is still CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 2, 'BAD']])

        # Service notification number increased
        assert 4 == svc.current_notification_number

        # We got one more escalated notification
        assert 5 == len([n.escalated for n in self._sched.actions.values() if n.escalated])
        expected_logs += [
            (u'error', u'SERVICE NOTIFICATION: level3;test_host_0_esc;test_svc_esc_time;'
                       u'CRITICAL;notify-service;BAD')
        ]
        self.check_monitoring_logs(expected_logs)

        # ---
        # 5/
        # ---
        # Now we send 10 more alerts and we are still always notifying only level3
        for i in range(10):
            # And still a time warp :)
            for n in svc.notifications_in_progress.values():
                # We say that it's already 3600 seconds since the last notification
                n.t_to_go = time.time()

            # Service is still CRITICAL/HARD
            time.sleep(.1)
            self.scheduler_loop(1, [[svc, 2, 'BAD']])

            # Service notification number increased
            assert 5 + i == svc.current_notification_number

            # We got one more escalated notification
            assert 6 + i == \
                             len([n.escalated for n in
                                  self._sched.actions.values() if n.escalated])
            expected_logs += [
                (u'error', u'SERVICE NOTIFICATION: level3;test_host_0_esc;test_svc_esc_time;'
                           u'CRITICAL;notify-service;BAD')
            ]
            self.check_monitoring_logs(expected_logs)

        # ---
        # 6/
        # ---
        # The service recovers, all the notified contact will be contacted
        self.scheduler_loop(2, [[svc, 0, 'OK']])
        expected_logs += [
            (u'info', u'SERVICE ALERT: test_host_0_esc;test_svc_esc_time;OK;HARD;2;OK'),
            (u'info', u'SERVICE NOTIFICATION: test_contact;test_host_0_esc;test_svc_esc_time;'
                      u'OK;notify-service;OK'),
            (u'info', u'SERVICE NOTIFICATION: level2;test_host_0_esc;test_svc_esc_time;'
                      u'OK;notify-service;OK'),
            (u'info', u'SERVICE NOTIFICATION: level1;test_host_0_esc;test_svc_esc_time;'
                      u'OK;notify-service;OK'),
            (u'info', u'SERVICE NOTIFICATION: level3;test_host_0_esc;test_svc_esc_time;'
                      u'OK;notify-service;OK')
        ]
        self.check_monitoring_logs(expected_logs)


if __name__ == '__main__':
    unittest.main()
