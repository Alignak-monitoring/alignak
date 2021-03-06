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
This file test notifications
"""

import time
import copy
import pytest
import datetime
from freezegun import freeze_time
from .alignak_test import AlignakTest


class TestNotifications(AlignakTest):
    """
    This class test notifications
    """
    def setUp(self):
        super(TestNotifications, self).setUp()

    def test_0_nonotif(self):
        """ Test with notifications disabled in service definition

        :return: None
        """
        self.setup_with_file('cfg/cfg_nonotif.cfg',
                             dispatching=True)

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert 0 == svc.current_notification_number, 'All OK no notifications'
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "SOFT" == svc.state_type
        assert 0 == svc.current_notification_number, 'Critical SOFT, no notifications'
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        assert 0 == svc.current_notification_number, 'Critical HARD, no notifications'
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'VOID', 'command')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert 0 == svc.current_notification_number, 'Ok HARD, no notifications'
        self.assert_actions_count(0)

    def test_1_nonotif_enable_with_extcmd(self):
        """ Test notification disabled in service definition but enabled later
        with an external command

        :return: None
        """
        self.setup_with_file('cfg/cfg_nonotif.cfg',
                             dispatching=True)

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")

        # notification_interval is in minute, configure to have one per minute
        svc.notification_interval = 1

        # No notifications enabled by configuration!
        assert not svc.notifications_enabled
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2018, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime

            self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert 0 == host.current_notification_number, 'Raised a notification!'
            assert 0 == svc.current_notification_number, 'Raised a notification!'

            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "SOFT" == svc.state_type
            assert 0 == svc.current_notification_number, \
                'Critical SOFT, should not have notification!'
            self.assert_actions_count(0)

            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            assert "HARD" == svc.state_type
            assert 0 == svc.current_notification_number, \
                'Critical HARD, but have a notification whereas it is disabled!'

            # No raised notification !
            self.show_actions()
            # Raised only a master notification!
            self.assert_actions_count(1)

            # External command to enable the notifications for the service
            now = int(time.time())
            cmd = "[{0}] ENABLE_SVC_NOTIFICATIONS;{1};{2}\n".format(now, svc.host_name,
                                                                    svc.service_description)
            self._scheduler.run_external_commands([cmd])
            self.external_command_loop()
            assert svc.notifications_enabled
            assert "HARD" == svc.state_type
            assert "CRITICAL" == svc.state

            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)

            # Notification !
            self.show_actions()
            assert 1 == svc.current_notification_number, \
                'Critical HARD, must have 1 notification'
            self.assert_actions_count(2)
            self.assert_actions_match(0, 'serviceoutput CRITICAL', 'command')
            self.assert_actions_match(1, 'VOID', 'command')

            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))

            # The service recovers
            self.scheduler_loop(1, [[svc, 0, 'OK']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert 0 == svc.current_notification_number, 'Ok HARD, no notifications'
            self.assert_actions_count(2)
            self.assert_actions_match(0, 'serviceoutput CRITICAL', 'command')
            self.assert_actions_match(1, 'serviceoutput OK', 'command')

    def test_1_notifications_service_with_no_contacts(self):
        """ Test notifications are sent to host contacts for a service with no defined contacts

        :return: None
        """
        self.setup_with_file('cfg/cfg_nonotif.cfg',
                             dispatching=True)

        host = self._scheduler.hosts.find_by_name("test_host_contact")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        print("Host: %s" % host)
        print("Host contacts groups: %s" % host.contact_groups)
        print("Host contacts: %s" % host.contacts)
        assert host.contacts != []
        assert host.notifications_enabled

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_contact",
                                                                     "test_no_contacts")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False
        print("Service: %s" % svc)
        print("Service contacts: %s" % svc.contacts)
        # The service has inherited the host contacts !
        assert svc.contacts == host.contacts
        assert svc.notifications_enabled

        # notification_interval is in minute, configure to have one per minute
        svc.notification_interval = 1

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2018, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime

            self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert 0 == svc.current_notification_number, 'All OK no notifications'
            self.assert_actions_count(0)

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "SOFT" == svc.state_type
            assert 0 == svc.current_notification_number, 'Critical SOFT, no notifications'
            self.assert_actions_count(0)

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "HARD" == svc.state_type
            assert "CRITICAL" == svc.state
            assert 1 == svc.current_notification_number, 'Critical HARD, must have 1 notification'
            self.show_actions()
            self.assert_actions_count(2)
            self.assert_actions_match(1, 'VOID', 'command')
            self.assert_actions_match(1, 'PROBLEM', 'type')
            self.assert_actions_match(0, 'PROBLEM', 'type')
            self.assert_actions_match(0, '/notifier.pl --hostname test_host_contact --servicedesc test_no_contacts '
                                         '--notificationtype PROBLEM --servicestate CRITICAL --serviceoutput CRITICAL ', 'command')
            self.assert_actions_match(0, '--serviceattempt 2 --servicestatetype HARD', 'command')
            self.assert_actions_match(0, 'NOTIFICATIONTYPE=PROBLEM, '
                                         'NOTIFICATIONRECIPIENTS=test_contact, '
                                         'NOTIFICATIONISESCALATED=False, '
                                         'NOTIFICATIONAUTHOR=n/a, '
                                         'NOTIFICATIONAUTHORNAME=n/a, '
                                         'NOTIFICATIONAUTHORALIAS=n/a, '
                                         'NOTIFICATIONCOMMENT=n/a, '
                                         'HOSTNOTIFICATIONNUMBER=1, '
                                         'SERVICENOTIFICATIONNUMBER=1, ', 'command')

            # Time warp 1 minute
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            self.show_actions()
            self.assert_actions_count(3)
            self.assert_actions_match(2, 'VOID', 'command')
            self.assert_actions_match(2, 'PROBLEM', 'type')
            self.assert_actions_match(1, 'PROBLEM', 'type')
            self.assert_actions_match(1, '/notifier.pl --hostname test_host_contact --servicedesc test_no_contacts '
                                         '--notificationtype PROBLEM --servicestate CRITICAL --serviceoutput CRITICAL ', 'command')
            self.assert_actions_match(1, '--serviceattempt 2 --servicestatetype HARD', 'command')
            self.assert_actions_match(1, 'HOSTNOTIFICATIONNUMBER=2, SERVICENOTIFICATIONNUMBER=2, ', 'command')
            self.assert_actions_match(0, 'PROBLEM', 'type')
            self.assert_actions_match(0, '/notifier.pl --hostname test_host_contact --servicedesc test_no_contacts '
                                         '--notificationtype PROBLEM --servicestate CRITICAL --serviceoutput CRITICAL ', 'command')
            self.assert_actions_match(0, '--serviceattempt 2 --servicestatetype HARD', 'command')
            self.assert_actions_match(0, 'HOSTNOTIFICATIONNUMBER=1, SERVICENOTIFICATIONNUMBER=1, ', 'command')

            self.scheduler_loop(1, [[svc, 0, 'OK']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "HARD" == svc.state_type
            assert "OK" == svc.state
            assert 0 == svc.current_notification_number, 'Ok HARD, no notifications'

            # 1st notification for service critical
            self.show_actions()
            self.assert_actions_match(0, 'PROBLEM', 'type')
            self.assert_actions_match(0, 'notifier.pl --hostname test_host_contact --servicedesc test_no_contacts '
                                         '--notificationtype PROBLEM --servicestate CRITICAL --serviceoutput CRITICAL', 'command')
            self.assert_actions_match(0, 'HOSTNOTIFICATIONNUMBER=1, SERVICENOTIFICATIONNUMBER=1', 'command')

            # 2nd notification for service recovery
            self.assert_actions_match(1, 'PROBLEM', 'type')
            self.assert_actions_match(1, 'notifier.pl --hostname test_host_contact --servicedesc test_no_contacts '
                                         '--notificationtype PROBLEM --servicestate CRITICAL --serviceoutput CRITICAL', 'command')
            self.assert_actions_match(1, 'HOSTNOTIFICATIONNUMBER=2, SERVICENOTIFICATIONNUMBER=2', 'command')

            # 2nd notification for service recovery
            self.assert_actions_match(2, 'RECOVERY', 'type')
            self.assert_actions_match(2, 'notifier.pl --hostname test_host_contact --servicedesc test_no_contacts '
                                         '--notificationtype RECOVERY --servicestate OK --serviceoutput OK', 'command')
            self.assert_actions_match(2, 'HOSTNOTIFICATIONNUMBER=0, SERVICENOTIFICATIONNUMBER=0', 'command')

    def test_2_notifications(self):
        """ Test notifications sent in normal mode

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg',
                             dispatching=True)

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        # notification_interval is in minute, configure to have one per minute
        svc.notification_interval = 1

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2018, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime

            self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert svc.current_notification_number == 0, 'All OK no notifications'
            self.assert_actions_count(0)

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "SOFT" == svc.state_type
            assert svc.current_notification_number == 0, 'Critical SOFT, no notifications'
            self.assert_actions_count(0)

            # create master notification + create first notification
            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])

            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)

            assert "HARD" == svc.state_type
            # 2 actions
            # * 1 - VOID = notification master
            # * 2 - notifier.pl to test_contact
            self.show_actions()
            self.assert_actions_count(2)
            assert svc.current_notification_number == 1, 'Critical HARD, must have 1 notification'

            # no changes, because we do not need yet to create a second notification
            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "HARD" == svc.state_type
            self.assert_actions_count(2)

            # Time warp 1 minute 1 second
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))

            # notification #2
            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            self.assert_actions_count(3)
            assert svc.current_notification_number == 2

            # Time warp 1 minute 1 second
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))

            # notification #3
            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            self.assert_actions_count(4)
            assert svc.current_notification_number == 3

            # Time warp 10 seconds
            frozen_datetime.tick(delta=datetime.timedelta(seconds=10))

            # Too soon for a new one
            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            self.assert_actions_count(4)
            assert svc.current_notification_number == 3

            # Simulate the first notification is sent ...
            self.show_actions()
            actions = sorted(list(self._scheduler.actions.values()), key=lambda x: x.creation_time)
            action = copy.copy(actions[1])
            action.exit_status = 0
            action.status = 'launched'
            # and return to the scheduler
            self._scheduler.waiting_results.put(action)

            # re-loop scheduler to manage this
            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # One less notification ... because sent !
            self.assert_actions_count(3)
            # But still the same notification number
            assert svc.current_notification_number == 3

            # Disable the contact notification
            # -----
            cmd = "[%lu] DISABLE_CONTACT_SVC_NOTIFICATIONS;test_contact" % time.time()
            self._scheduler.run_external_commands([cmd])

            # Time warp 1 minute 1 second
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            # Not one more notification ...
            self.assert_actions_count(3)
            assert svc.current_notification_number == 3

            # Time warp 1 minute 1 second
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            # Not one more notification ...
            self.assert_actions_count(3)
            assert svc.current_notification_number == 3

            # Enable the contact notification
            # -----
            cmd = "[%lu] ENABLE_CONTACT_SVC_NOTIFICATIONS;test_contact" % time.time()
            self._scheduler.run_external_commands([cmd])

            # Time warp 1 minute 1 second
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))

            # 2 loop turns this time ...
            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)

            self.assert_actions_count(4)
            assert svc.current_notification_number == 4

            self.show_actions()
            # 1st notification for service critical => sent !
            # self.assert_actions_match(0, 'notifier.pl --hostname test_host_0 --servicedesc test_ok_0 --notificationtype PROBLEM --servicestate CRITICAL --serviceoutput CRITICAL', 'command')
            # self.assert_actions_match(0, 'HOSTNOTIFICATIONNUMBER=1, SERVICENOTIFICATIONNUMBER=1', 'command')

            # 2nd notification for service critical
            self.assert_actions_match(0, 'notifier.pl --hostname test_host_0 --servicedesc test_ok_0 --notificationtype PROBLEM --servicestate CRITICAL --serviceoutput CRITICAL', 'command')
            self.assert_actions_match(0, 'HOSTNOTIFICATIONNUMBER=2, SERVICENOTIFICATIONNUMBER=2', 'command')

            # 3rd notification for service critical
            self.assert_actions_match(1, 'notifier.pl --hostname test_host_0 --servicedesc test_ok_0 --notificationtype PROBLEM --servicestate CRITICAL --serviceoutput CRITICAL', 'command')
            self.assert_actions_match(1, 'HOSTNOTIFICATIONNUMBER=3, SERVICENOTIFICATIONNUMBER=3', 'command')

            # 4th notification for service critical
            self.assert_actions_match(2, 'notifier.pl --hostname test_host_0 --servicedesc test_ok_0 --notificationtype PROBLEM --servicestate CRITICAL --serviceoutput CRITICAL', 'command')
            self.assert_actions_match(2, 'HOSTNOTIFICATIONNUMBER=4, SERVICENOTIFICATIONNUMBER=4', 'command')


            self.scheduler_loop(1, [[svc, 0, 'OK']])

            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)

            # The service recovered, the current notification number is reset !
            assert svc.current_notification_number == 0

            # Actions count did not changed because:
            # 1/ a new recovery notification is created
            # 2/ the master problem notification is removed
            self.assert_actions_count(4)
            self.show_actions()

            # 1st recovery notification for service recovery
            self.assert_actions_match(3, 'notifier.pl --hostname test_host_0 --servicedesc test_ok_0 --notificationtype RECOVERY --servicestate OK --serviceoutput OK', 'command')
            self.assert_actions_match(3, 'NOTIFICATIONTYPE=RECOVERY', 'command')
            self.assert_actions_match(3, 'HOSTNOTIFICATIONNUMBER=0, SERVICENOTIFICATIONNUMBER=0', 'command')

    def test_3_notifications(self):
        """ Test notifications of service states OK -> WARNING -> CRITICAL -> OK

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg',
                             dispatching=True)

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        # notification_interval is in minute, configure to have one per minute
        svc.notification_interval = 1

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2018, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime

            self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
            time.sleep(0.1)
            assert 0 == svc.current_notification_number, 'All OK no notifications'
            self.assert_actions_count(0)

            self.scheduler_loop(1, [[svc, 1, 'WARNING']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "SOFT" == svc.state_type
            assert 0 == svc.current_notification_number, 'Warning SOFT, no notifications'
            self.assert_actions_count(0)

            self.scheduler_loop(1, [[svc, 1, 'WARNING']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "WARNING" == svc.state
            assert "HARD" == svc.state_type
            assert 1 == svc.current_notification_number, 'Warning HARD, must have 1 notification'
            self.assert_actions_count(2)
            self.show_actions()
            self.assert_actions_match(0, 'serviceoutput WARNING', 'command')
            self.assert_actions_match(1, 'VOID', 'command')
            print(("Last hard state: %s" % svc.last_hard_state))
            assert "WARNING" == svc.last_hard_state

            # Time warp 5 minutes
            frozen_datetime.tick(delta=datetime.timedelta(minutes=5))

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "CRITICAL" == svc.state
            assert "HARD" == svc.state_type
            assert "CRITICAL" == svc.last_hard_state
            assert 2 == svc.current_notification_number, 'Critical HARD,  must have 2 notifications'
            self.assert_actions_count(3)
            self.show_actions()
            self.assert_actions_match(0,
                                      '--notificationtype PROBLEM --servicestate WARNING',
                                      'command')
            self.assert_actions_match(1,
                                      '--notificationtype PROBLEM --servicestate CRITICAL',
                                      'command')
            self.assert_actions_match(2,
                                      'VOID',
                                      'command')

            self.scheduler_loop(1, [[svc, 0, 'OK']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert 0 == svc.current_notification_number
            self.show_actions()
            self.assert_actions_count(3)
            self.assert_actions_match(0,
                                      '--notificationtype PROBLEM --servicestate WARNING',
                                      'command')
            self.assert_actions_match(1,
                                      '--notificationtype PROBLEM --servicestate CRITICAL',
                                      'command')
            self.assert_actions_match(2,
                                      '--notificationtype RECOVERY --servicestate OK',
                                      'command')

    def test_4_notifications(self):
        """ Test notifications of service states OK -> CRITICAL -> WARNING -> OK

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg',
                             dispatching=True)

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send quickly (6 second)
        svc.notification_interval = 0.1
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        # notification_interval is in minute, configure to have one per minute
        svc.notification_interval = 1

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2018, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime

            self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert 0 == svc.current_notification_number, 'All OK no notifications'
            self.assert_actions_count(0)

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "SOFT" == svc.state_type
            assert 0 == svc.current_notification_number, 'Critical SOFT, no notifications'
            self.assert_actions_count(0)

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "HARD" == svc.state_type
            assert 1 == svc.current_notification_number, 'Critical HARD, must have 1 ' \
                                                                 'notification'
            self.assert_actions_count(2)
            self.show_actions()
            self.assert_actions_match(0,
                                      '--notificationtype PROBLEM --servicestate CRITICAL',
                                      'command')
            self.assert_actions_match(1,
                                      'VOID',
                                      'command')

            # Time warp 5 minutes
            frozen_datetime.tick(delta=datetime.timedelta(minutes=5))

            self.scheduler_loop(1, [[svc, 1, 'WARNING']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "HARD" == svc.state_type
            assert 2 == svc.current_notification_number, 'Warning HARD,  must have 3 ' \
                                                                 'notification'
            self.show_actions()
            self.assert_actions_match(0,
                                      '--notificationtype PROBLEM --servicestate CRITICAL',
                                      'command')
            self.assert_actions_match(1,
                                      '--notificationtype PROBLEM --servicestate WARNING',
                                      'command')
            self.assert_actions_match(2,
                                      'VOID',
                                      'command')

    def test_notifications_passive_host(self):
        """ Test notifications for passively check hosts

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg',
                             dispatching=True)

        # Check freshness on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'tick_check_freshness': 1})

        # Get host
        host = self._scheduler.hosts.find_by_name('test_host_0')
        host.act_depend_of = []  # ignore the router
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.active_checks_enabled = False
        host.passive_checks_enabled = True
        host.check_freshness = True
        host.max_check_attempts = 1
        host.freshness_threshold = 1800
        host.freshness_state = 'd'
        print(("Host: %s - state: %s/%s, freshness: %s / %s, attempts: %s" % (
            host, host.state_type, host.state, host.check_freshness, host.freshness_threshold,
            host.max_check_attempts)))
        print(("Host: %s - state: %s/%s, last state update: %s" % (
            host, host.state_type, host.state, host.last_state_update)))
        assert host is not None

        # Get service
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.event_handler_enabled = False
        svc.active_checks_enabled = False
        svc.passive_checks_enabled = True
        svc.check_freshness = True
        svc.freshness_threshold = 120
        assert svc is not None
        print(("Service: %s - state: %s/%s, freshness: %s / %s" % (svc, svc.state_type, svc.state,
                                                                  svc.check_freshness,
                                                                  svc.freshness_threshold)))

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2017, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime

            self.external_command_loop()
            time.sleep(0.1)
            # Freshness ok !
            assert not host.freshness_expired
            assert "UP" == host.state
            assert "HARD" == host.state_type
            assert host.attempt == 0
            assert host.max_check_attempts == 1
            assert host.current_notification_number == 0, 'All OK no notifications'
            self.assert_actions_count(0)
            print(("Host: %s - state: %s/%s, last state update: %s" % (
                host, host.state_type, host.state, host.last_state_update)))

            # Time warp 1 hour
            frozen_datetime.tick(delta=datetime.timedelta(hours=1))

            self.manage_freshness_check(1)
            self.show_logs()

            # Time warp 10 seconds
            frozen_datetime.tick(delta=datetime.timedelta(seconds=10))

            # Check freshness on each scheduler tick
            self._scheduler.update_recurrent_works_tick({'tick_check_freshness': 1})
            self.manage_freshness_check(1)
            self.show_logs()
            time.sleep(0.1)
            # Freshness expired !
            assert host.freshness_expired
            assert "DOWN" == host.state
            assert "HARD" == host.state_type
            assert host.attempt == 1
            assert host.max_check_attempts == 1
            assert host.is_max_attempts()
            assert host.current_notification_number == 1, 'Raised a notification'
            self.assert_actions_count(2)
            print(("Host: %s - state: %s/%s, last state update: %s" % (
                host, host.state_type, host.state, host.last_state_update)))

            # Time warp 1 hour
            frozen_datetime.tick(delta=datetime.timedelta(hours=1))

            self.external_command_loop()
            time.sleep(0.1)
            assert host.freshness_expired
            assert "DOWN" == host.state
            assert "HARD" == host.state_type
            # Perharps that attempt should have been incremented?
            assert host.attempt == 1
            assert host.max_check_attempts == 1
            assert host.is_max_attempts()
            # Notification for the host and the service
            assert host.current_notification_number == 2, 'We should have 2 notifications'
            self.show_actions()
            self.show_logs()

            # 2 actions
            # * 1 - VOID = notification master
            # * 2 - notifier.pl to test_contact
            # * 3 - notifier.pl to test_contact
            self.assert_actions_count(3)

    def test_notifications_with_delay(self):
        """ Test notifications with use property first_notification_delay

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg',
                             dispatching=True)

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        svc.first_notification_delay = 0.1  # set 6s for first notification delay
        svc.notification_interval = 0.1 / 6  # and send immediately then (1 second)
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no host_checks on critical check_results
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert 0 == svc.current_notification_number

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        self.assert_actions_count(0)
        time.sleep(0.1)
        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        assert "HARD" == svc.state_type
        self.assert_actions_count(1)
        time.sleep(7)
        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        self.show_actions()
        self.assert_actions_count(2)
        self.assert_actions_match(0, 'serviceoutput WARNING', 'command')
        self.assert_actions_match(0, 'HOSTNOTIFICATIONNUMBER=1, SERVICENOTIFICATIONNUMBER=1', 'command')
        self.assert_actions_match(1, 'VOID', 'command')
        assert svc.last_time_critical == 0
        assert svc.last_time_unknown == 0
        assert svc.last_time_warning > 0
        assert svc.last_time_ok > 0

        time.sleep(2)
        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        self.show_actions()
        self.assert_actions_count(3)
        self.assert_actions_match(0, 'serviceoutput WARNING', 'command')
        self.assert_actions_match(0, 'HOSTNOTIFICATIONNUMBER=1, SERVICENOTIFICATIONNUMBER=1', 'command')
        # One more notification!
        self.assert_actions_match(1, 'serviceoutput WARNING', 'command')
        self.assert_actions_match(1, 'HOSTNOTIFICATIONNUMBER=2, SERVICENOTIFICATIONNUMBER=2', 'command')
        self.assert_actions_match(2, 'VOID', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        assert 3 == svc.current_notification_number
        self.assert_actions_count(4)
        assert svc.last_time_unknown == 0
        assert svc.last_time_warning > 0
        assert svc.last_time_critical > 0
        assert svc.last_time_ok > 0
        time.sleep(7)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        assert 4 == svc.current_notification_number
        self.show_actions()
        self.assert_actions_count(5)
        self.assert_actions_match(0, 'serviceoutput WARNING', 'command')
        self.assert_actions_match(0, 'HOSTNOTIFICATIONNUMBER=1, SERVICENOTIFICATIONNUMBER=1', 'command')
        self.assert_actions_match(1, 'serviceoutput WARNING', 'command')
        self.assert_actions_match(1, 'HOSTNOTIFICATIONNUMBER=2, SERVICENOTIFICATIONNUMBER=2', 'command')
        # One more notification!
        self.assert_actions_match(2, 'serviceoutput CRITICAL', 'command')
        self.assert_actions_match(2, 'HOSTNOTIFICATIONNUMBER=3, SERVICENOTIFICATIONNUMBER=3', 'command')
        self.assert_actions_match(3, 'serviceoutput CRITICAL', 'command')
        self.assert_actions_match(3, 'HOSTNOTIFICATIONNUMBER=4, SERVICENOTIFICATIONNUMBER=4', 'command')
        self.assert_actions_match(4, 'VOID', 'command')
        assert 5 == len(svc.notifications_in_progress)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(7)
        self.scheduler_loop(1, [[svc, 0, 'OK']])
        assert 0 == svc.current_notification_number
        self.assert_actions_count(5)

    def test_notifications_outside_period(self):
        """ Test when we are not in notification_period, so do not send notifications

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg',
                             dispatching=True)

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly (1 second)
        svc.notification_interval = 0.1 / 6
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False
        timeperiod = self._scheduler.timeperiods.find_by_name('none')
        svc.notification_period = timeperiod.uuid

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert 0 == svc.current_notification_number, 'All OK no notifications'
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "SOFT" == svc.state_type
        assert 0 == svc.current_notification_number, 'Critical SOFT, no notifications'
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        assert 0 == svc.current_notification_number, 'Critical HARD, no notifications'
        # Only a master notification but no real one!
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'VOID', 'command')
        self.assert_actions_match(0, 'PROBLEM', 'type')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert 0 == svc.current_notification_number
        self.show_actions()
        # Only a master notification but no real one!
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'VOID', 'command')
        self.assert_actions_match(0, 'RECOVERY', 'type')

    def test_notifications_ack(self):
        """ Test notifications not sent when an acknowledge is set

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg',
                             dispatching=True)

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly (1 second)
        svc.notification_interval = 0.1 / 6
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2018, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime

            self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert 0 == svc.current_notification_number, 'All OK no notifications'
            self.assert_actions_count(0)

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "SOFT" == svc.state_type
            assert 0 == svc.current_notification_number, 'Critical SOFT, no notifications'
            self.assert_actions_count(0)

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "HARD" == svc.state_type
            assert 1 == svc.current_notification_number, \
                'Critical HARD, must have 1 notification'
            self.show_actions()
            self.assert_actions_count(2)
            self.assert_actions_match(0,
                                      '--notificationtype PROBLEM --servicestate CRITICAL',
                                      'command')
            self.assert_actions_match(1,
                                      'VOID',
                                      'command')

            # Time warp 5 minutes
            frozen_datetime.tick(delta=datetime.timedelta(minutes=5))

            now = int(time.time())
            cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n".\
                format(now, svc.host_name, svc.service_description, 1, 1, 1, 'darth vader',
                       'normal process')
            self._scheduler.run_external_commands([cmd])
            self.scheduler_loop(1)
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "HARD" == svc.state_type
            assert 1 == svc.current_notification_number, \
                'Critical HARD and ack, but must have 1 notification'
            self.show_actions()
            self.assert_actions_count(3)
            self.assert_actions_match(0,
                                      '--notificationtype PROBLEM --servicestate CRITICAL',
                                      'command')
            self.assert_actions_match(1,
                                      '--notificationtype ACKNOWLEDGEMENT',
                                      'command')
            self.assert_actions_match(2,
                                      'VOID',
                                      'command')

            # Time warp 5 minutes
            frozen_datetime.tick(delta=datetime.timedelta(minutes=5))

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            self.scheduler_loop(1)
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "HARD" == svc.state_type
            assert 1 == svc.current_notification_number, \
                'Critical HARD, must have 1 notification'
            self.assert_actions_count(3)

            # Time warp 5 minutes
            frozen_datetime.tick(delta=datetime.timedelta(minutes=5))

            self.scheduler_loop(1, [[svc, 1, 'WARNING']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "HARD" == svc.state_type
            assert 3 == svc.current_notification_number, \
                'Warning HARD, must have 3 notifications'
            self.show_actions()
            # TODO: 2 warning notifications raised ! Looks strange !!!! But seems correct...
            self.assert_actions_count(5)
            self.assert_actions_match(0,
                                      '--notificationtype PROBLEM --servicestate CRITICAL',
                                      'command')
            self.assert_actions_match(1,
                                      '--notificationtype ACKNOWLEDGEMENT',
                                      'command')
            self.assert_actions_match(2,
                                      '--notificationtype PROBLEM --servicestate WARNING',
                                      'command')
            self.assert_actions_match(3,
                                      '--notificationtype PROBLEM --servicestate WARNING',
                                      'command')
            self.assert_actions_match(4,
                                      'VOID',
                                      'command')

    def test_notifications_downtime(self):
        """ Test notifications not sent when a downtime is scheduled

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg',
                             dispatching=True)

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly (1 second)
        svc.notification_interval = 0.1 / 6
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert 0 == svc.current_notification_number, 'All OK no notifications'
        self.assert_actions_count(0)

        now = int(time.time())
        cmd = "[{0}] SCHEDULE_SVC_DOWNTIME;{1};{2};{3};{4};{5};{6};{7};{8};{9}\n".\
            format(now, svc.host_name, svc.service_description, now, (now + 1000), 1, 0, 0,
                   'darth vader', 'add downtime for maintenance')
        self._scheduler.run_external_commands([cmd])
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "SOFT" == svc.state_type
        assert "CRITICAL" == svc.state
        assert 0 == svc.current_notification_number, 'Critical SOFT, no notifications'
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'serviceoutput OK', 'command')
        self.assert_actions_match(0, 'notificationtype DOWNTIMESTART', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        assert 0 == svc.current_notification_number, 'Critical HARD, no notifications'
        self.assert_actions_count(2)
        self.assert_actions_match(1, 'VOID', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert 0 == svc.current_notification_number
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'serviceoutput OK', 'command')
        self.assert_actions_match(0, 'notificationtype DOWNTIMESTART', 'command')

    def test_notifications_no_renotify(self):
        """ Test notifications sent only once if configured for this

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg',
                             dispatching=True)

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        # To make notifications not being re-sent, set this to 0
        svc.notification_interval = 0
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2018, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime

            self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
            time.sleep(1)
            assert svc.current_notification_number == 0, 'All OK no notifications'
            self.assert_actions_count(0)

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            time.sleep(1)
            assert "SOFT" == svc.state_type
            assert svc.current_notification_number == 0, 'Critical SOFT, no notifications'
            self.assert_actions_count(0)

            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1, seconds=1))

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert "HARD" == svc.state_type
            self.assert_actions_count(1)
            assert svc.current_notification_number == 1, 'Critical HARD, must have 1 ' \
                                                         'notification'
            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            # No re-notification!
            self.assert_actions_count(1)
            assert svc.current_notification_number == 1

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            # No re-notification!
            self.assert_actions_count(1)
            assert svc.current_notification_number == 1

            self.show_actions()
            # 1st notification for service critical
            self.assert_actions_match(
                0, 'notifier.pl --hostname test_host_0 --servicedesc test_ok_0 '
                   '--notificationtype PROBLEM --servicestate CRITICAL --serviceoutput CRITICAL',
                'command')
            self.assert_actions_match(
                0, 'NOTIFICATIONTYPE=PROBLEM, NOTIFICATIONRECIPIENTS=test_contact, '
                   'NOTIFICATIONISESCALATED=False, NOTIFICATIONAUTHOR=n/a, '
                   'NOTIFICATIONAUTHORNAME=n/a, NOTIFICATIONAUTHORALIAS=n/a, '
                   'NOTIFICATIONCOMMENT=n/a, HOSTNOTIFICATIONNUMBER=1, '
                   'SERVICENOTIFICATIONNUMBER=1',
                'command')

