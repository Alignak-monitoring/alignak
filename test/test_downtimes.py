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
#     Hartmut Goebel, h.goebel@goebel-consult.de
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

"""
 This file is used to test hosts and services downtimes.
"""

from six import itervalues
import time
from alignak.misc.serialization import unserialize
from alignak.downtime import Downtime

from alignak_test import AlignakTest, unittest

class TestDowntime(AlignakTest):
    """
    This class tests the downtimes
    """
    def setUp(self):
        """
        For each test load and check the configuration
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        assert self.conf_is_correct

        # Our scheduler
        self._sched = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._sched.brokers['broker-master']

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

    def test_create_downtime(self):
        """ Create a downtime object """
        self.print_header()

        now = int(time.time())

        # With common parameters
        data = {'ref': 'host.uuid', 'ref_type': 'host.my_type',
                'start_time': now, 'end_time': now + 5,
                'fixed': True, 'trigger_id': '',
                'duration': 0, 'author': 'me', 'comment': 'created by me!'}
        downtime = Downtime(data)

        expected = {'uuid': downtime.uuid}
        expected.update({
            # Provided parameters
            'ref': 'host.uuid',
            'ref_type': 'host.my_type',
            'start_time': now,
            'end_time': now + 5,
            'fixed': True,
            'author': 'me',
            'comment': 'created by me!',
            'trigger_id': '',
            'duration': 5.0,

            # Object created properties
            'can_be_deleted': False,
            'has_been_triggered': False,
            'is_in_effect': False,
            'activate_me': [],

            # Not defined but it would be better if it was
            # 'comment_id': '',

            'entry_time': downtime.entry_time,
            'real_end_time': downtime.end_time,
        })
        assert expected == downtime.__dict__

        assert str(downtime) == "inactive fixed Downtime id=%s %s - %s" \
                                % (downtime.uuid,
                                   time.ctime(downtime.start_time),
                                   time.ctime(downtime.end_time))

        # A serialized downtime is the same as the __dict__
        assert downtime.__dict__ == downtime.serialize()

        # Unserialize the serialized downtime
        unserialized_item = Downtime(params=downtime.serialize())
        assert downtime.__dict__ == unserialized_item.__dict__

    def test_schedule_fixed_svc_downtime(self):
        """ Schedule a fixed downtime for a service """
        self.print_header()

        # Get the service
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        # Not any downtime yet !
        assert svc.downtimes == {}
        # Get service scheduled downtime depth
        assert svc.scheduled_downtime_depth == 0
        # No current notifications
        assert 0 == svc.current_notification_number, 'All OK no notifications'
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.event_handler_enabled = False

        # Make the service be OK
        self.scheduler_loop(1, [[svc, 0, 'OK']])

        # schedule a 5 seconds downtime
        duration = 5
        now = int(time.time())
        # downtime valid for 5 seconds from now
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%d;%d;1;0;%d;" \
              "downtime author;downtime comment" % (now, now, now + duration, duration)
        self._sched.run_external_command(cmd)
        self.external_command_loop()
        # A downtime exist for the service
        assert len(svc.downtimes) == 1
        downtime = svc.downtimes.values()[0]
        assert downtime.comment == "downtime comment"
        assert downtime.author == "downtime author"
        assert downtime.start_time == now
        assert downtime.end_time == now + duration
        assert downtime.duration == duration
        # Fixed
        assert downtime.fixed
        # Already active
        assert downtime.is_in_effect
        # Cannot be deleted
        assert not downtime.can_be_deleted
        assert downtime.trigger_id == "0"
        # Get service scheduled downtime depth
        scheduled_downtime_depth = svc.scheduled_downtime_depth
        assert svc.scheduled_downtime_depth == 1

        assert 0 == svc.current_notification_number, 'Should not have any notification'
        # Notification: downtime start
        self.assert_actions_count(1)
        self.show_actions()
        # 1st notification for downtime start
        self.assert_actions_match(0, 'notifier.pl --hostname test_host_0 --servicedesc test_ok_0 --notificationtype DOWNTIMESTART --servicestate OK --serviceoutput OK', 'command')
        self.assert_actions_match(0, 'NOTIFICATIONTYPE=DOWNTIMESTART, NOTIFICATIONRECIPIENTS=test_contact, NOTIFICATIONISESCALATED=False, NOTIFICATIONAUTHOR=downtime author, NOTIFICATIONAUTHORNAME=Not available, NOTIFICATIONAUTHORALIAS=Not available, NOTIFICATIONCOMMENT=downtime comment, HOSTNOTIFICATIONNUMBER=0, SERVICENOTIFICATIONNUMBER=0', 'command')

        # A comment exist in our service
        assert 1 == len(svc.comments)

        # Make the service be OK after a while
        # time.sleep(1)
        self.scheduler_loop(2, [[svc, 0, 'OK']])
        assert "HARD" == svc.state_type
        assert "OK" == svc.state

        assert 0 == svc.current_notification_number, 'Should not have any notification'
        # Still only 1
        self.assert_actions_count(1)

        # The downtime still exist in our service
        assert 1 == len(svc.downtimes)
        # The service is currently in a downtime period
        assert svc.in_scheduled_downtime
        downtime = svc.downtimes.values()[0]

        assert downtime.fixed
        assert downtime.is_in_effect
        assert not downtime.can_be_deleted

        # Make the service be CRITICAL/SOFT
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        assert "SOFT" == svc.state_type
        assert "CRITICAL" == svc.state

        assert 0 == svc.current_notification_number, 'Should not have any notification'
        # Still only 1
        self.assert_actions_count(1)

        assert 1 == len(svc.downtimes)
        # The service is still in a downtime period
        assert svc.in_scheduled_downtime
        downtime = svc.downtimes.values()[0]
        assert downtime.fixed
        assert downtime.is_in_effect
        assert not downtime.can_be_deleted

        # Make the service be CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 2, 'BAD']])
        assert "HARD" == svc.state_type
        assert "CRITICAL" == svc.state

        assert 0 == svc.current_notification_number, 'Should not have any notification'
        # Now 2 actions because the service is a problem
        self.assert_actions_count(2)
        # The downtime started
        self.assert_actions_match(0, '/notifier.pl', 'command')
        self.assert_actions_match(0, 'DOWNTIMESTART', 'type')
        self.assert_actions_match(0, 'scheduled', 'status')
        # The service is now a problem...
        self.assert_actions_match(1, 'VOID', 'command')
        self.assert_actions_match(1, 'PROBLEM', 'type')
        self.assert_actions_match(1, 'scheduled', 'status')
        self.show_actions()

        assert 1 == len(svc.downtimes)
        # The service is still in a downtime period
        assert svc.in_scheduled_downtime
        downtime = svc.downtimes.values()[0]
        assert downtime.fixed
        assert downtime.is_in_effect
        assert not downtime.can_be_deleted

        # Wait for a while, the service is back to OK but after the downtime expiry time
        time.sleep(5)
        self.scheduler_loop(2, [[svc, 0, 'OK']])
        assert "HARD" == svc.state_type
        assert "OK" == svc.state

        # No more downtime for the service nor the scheduler
        assert 0 == len(svc.downtimes)
        # The service is not anymore in a scheduled downtime period
        assert not svc.in_scheduled_downtime
        assert svc.scheduled_downtime_depth < scheduled_downtime_depth
        # No more comment for the service
        assert 0 == len(svc.comments)

        assert 0 == svc.current_notification_number, 'Should not have any notification'
        # Now 4 actions because the service is no more a problem and the downtime ended
        self.show_actions()
        self.assert_actions_count(4)
        # 1st notification for downtime start
        self.assert_actions_match(0, 'notifier.pl --hostname test_host_0 --servicedesc test_ok_0 --notificationtype DOWNTIMESTART --servicestate OK --serviceoutput OK', 'command')
        self.assert_actions_match(0, 'NOTIFICATIONTYPE=DOWNTIMESTART, NOTIFICATIONRECIPIENTS=test_contact, NOTIFICATIONISESCALATED=False, NOTIFICATIONAUTHOR=downtime author, NOTIFICATIONAUTHORNAME=Not available, NOTIFICATIONAUTHORALIAS=Not available, NOTIFICATIONCOMMENT=downtime comment, HOSTNOTIFICATIONNUMBER=0, SERVICENOTIFICATIONNUMBER=0', 'command')
        # The service is now a problem...
        self.assert_actions_match(1, 'notifier.pl --hostname test_host_0 --servicedesc test_ok_0 --notificationtype PROBLEM --servicestate CRITICAL --serviceoutput BAD', 'command')
        self.assert_actions_match(1, 'PROBLEM', 'type')
        self.assert_actions_match(1, 'scheduled', 'status')
        # 1st notification for downtime start
        self.assert_actions_match(-1, 'notifier.pl --hostname test_host_0 --servicedesc test_ok_0 --notificationtype DOWNTIMEEND --servicestate CRITICAL --serviceoutput BAD', 'command')
        self.assert_actions_match(-1, 'NOTIFICATIONTYPE=DOWNTIMEEND, NOTIFICATIONRECIPIENTS=test_contact, NOTIFICATIONISESCALATED=False, NOTIFICATIONAUTHOR=downtime author, NOTIFICATIONAUTHORNAME=Not available, NOTIFICATIONAUTHORALIAS=Not available, NOTIFICATIONCOMMENT=downtime comment, HOSTNOTIFICATIONNUMBER=0, SERVICENOTIFICATIONNUMBER=0', 'command')
        # The service is no more a problem...
        self.assert_actions_match(-1, 'notifier.pl --hostname test_host_0 --servicedesc test_ok_0 --notificationtype RECOVERY --servicestate OK --serviceoutput OK', 'command')
        self.assert_actions_match(-1, 'RECOVERY', 'type')
        self.assert_actions_match(-1, 'scheduled', 'status')

        # Clear actions
        self.clear_actions()

        # Make the service be CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(2, [[svc, 2, 'BAD']])
        assert "HARD" == svc.state_type
        assert "CRITICAL" == svc.state

        # 2 actions because the service is a problem and a notification is raised
        self.show_actions()
        self.assert_actions_count(2)

        # The service is now a problem...
        # A problem notification is now raised...
        self.assert_actions_match(0, 'notification', 'is_a')
        self.assert_actions_match(0, '/notifier.pl', 'command')
        self.assert_actions_match(0, 'PROBLEM', 'type')
        self.assert_actions_match(0, 'scheduled', 'status')
        # VOID notification
        self.assert_actions_match(1, 'VOID', 'command')
        self.assert_actions_match(1, 'PROBLEM', 'type')
        self.assert_actions_match(1, 'scheduled', 'status')

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in sorted(itervalues(self._broker['broks']), key=lambda x: x.creation_time):
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        print("Monitoring logs: %s" % monitoring_logs)
        expected_logs = [
            (u'info', u'EXTERNAL COMMAND: [%s] SCHEDULE_SVC_DOWNTIME;test_host_0;'
                      u'test_ok_0;%s;%s;1;0;%s;downtime author;downtime comment' % (
                now, now, now + duration, duration)),
            (u'info', u'SERVICE DOWNTIME ALERT: test_host_0;test_ok_0;STARTED; '
                      u'Service has entered a period of scheduled downtime'),
            (u'info', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;'
                      u'DOWNTIMESTART (OK);notify-service;OK'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;CRITICAL'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;HARD;2;BAD'),
            (u'info', u'SERVICE DOWNTIME ALERT: test_host_0;test_ok_0;STOPPED; '
                      u'Service has exited from a period of scheduled downtime'),
            (u'info', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;'
                      u'DOWNTIMEEND (CRITICAL);notify-service;BAD'),
            (u'error', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;'
                       u'CRITICAL;notify-service;BAD'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;HARD;2;OK'),
            (u'info', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;OK;'
                      u'notify-service;OK'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;BAD'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;HARD;2;BAD'),
            (u'error', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;'
                       u'CRITICAL;notify-service;BAD')
        ]
        for log_level, log_message in expected_logs:
            assert (log_level, log_message) in monitoring_logs

    def test_schedule_flexible_svc_downtime(self):
        """ Schedule a flexible downtime for a service """
        self.print_header()

        # Get the service
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        # Not any downtime yet !
        assert svc.downtimes == {}
        # Get service scheduled downtime depth
        assert svc.scheduled_downtime_depth == 0
        # No current notifications
        assert 0 == svc.current_notification_number, 'All OK no notifications'
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.event_handler_enabled = False

        # Make the service be OK
        self.scheduler_loop(1, [[svc, 0, 'OK']])

        #----------------------------------------------------------------
        # schedule a flexible downtime of 5 seconds for the service
        # The downtime will start between now and now + 1 hour and it
        # will be active for 5 seconds
        #----------------------------------------------------------------
        duration = 5
        now = int(time.time())
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%d;%d;0;0;%d;" \
              "downtime author;downtime comment" % (now, now, now + 3600, duration)
        self._sched.run_external_command(cmd)
        self.external_command_loop()
        # A downtime exist for the service
        assert len(svc.downtimes) == 1
        downtime = svc.downtimes.values()[0]
        assert downtime.comment == "downtime comment"
        assert downtime.author == "downtime author"
        assert downtime.start_time == now
        assert downtime.end_time == now + 3600
        assert downtime.duration == duration
        # Not fixed
        assert not downtime.fixed
        # Not yet active
        assert not downtime.is_in_effect
        # Cannot be deleted
        assert not downtime.can_be_deleted
        assert downtime.trigger_id == "0"
        # Get service scheduled downtime depth -> 0 no downtime
        scheduled_downtime_depth = svc.scheduled_downtime_depth
        assert svc.scheduled_downtime_depth == 0

        assert 0 == svc.current_notification_number, 'Should not have any notification'
        # No notifications, downtime did not started !
        self.assert_actions_count(0)

        # A comment exist in our service
        assert 1 == len(svc.comments)

        #----------------------------------------------------------------
        # run the service and return an OK status
        # check if the downtime is still inactive
        #----------------------------------------------------------------
        self.scheduler_loop(2, [[svc, 0, 'OK']])
        assert "HARD" == svc.state_type
        assert "OK" == svc.state
        assert 1 == len(svc.downtimes)
        assert not svc.in_scheduled_downtime
        downtime = svc.downtimes.values()[0]
        assert not downtime.fixed
        assert not downtime.is_in_effect
        assert not downtime.can_be_deleted

        # No notifications, downtime did not started !
        assert 0 == svc.current_notification_number, 'Should not have any notification'
        self.assert_actions_count(0)

        time.sleep(1)
        #----------------------------------------------------------------
        # run the service to get a soft critical status
        # check if the downtime is still inactive
        #----------------------------------------------------------------
        self.scheduler_loop(1, [[svc, 2, 'BAD']])
        assert "SOFT" == svc.state_type
        assert "CRITICAL" == svc.state
        assert 1 == len(svc.downtimes)
        downtime = svc.downtimes.values()[0]
        assert not svc.in_scheduled_downtime
        assert not downtime.fixed
        assert not downtime.is_in_effect
        assert not downtime.can_be_deleted

        # No notifications, downtime did not started !
        assert 0 == svc.current_notification_number, 'Should not have any notification'
        self.assert_actions_count(0)

        time.sleep(1)
        #----------------------------------------------------------------
        # run the service again to get a hard critical status
        # check if the downtime is active now
        #----------------------------------------------------------------
        self.scheduler_loop(1, [[svc, 2, 'BAD']])
        assert "HARD" == svc.state_type
        assert "CRITICAL" == svc.state
        time.sleep(1)
        assert 1 == len(svc.downtimes)
        downtime = svc.downtimes.values()[0]
        assert svc.in_scheduled_downtime
        assert not downtime.fixed
        assert downtime.is_in_effect
        assert not downtime.can_be_deleted

        # 2 actions because the service is a problem and the downtime started
        self.assert_actions_count(2)
        # The downtime started
        self.assert_actions_match(-1, '/notifier.pl', 'command')
        self.assert_actions_match(-1, 'DOWNTIMESTART', 'type')
        self.assert_actions_match(-1, 'scheduled', 'status')
        # The service is now a problem... but no notification
        self.assert_actions_match(-1, 'VOID', 'command')
        self.assert_actions_match(-1, 'PROBLEM', 'type')
        self.assert_actions_match(-1, 'scheduled', 'status')

        # The downtime is now active
        assert downtime.is_in_effect
        # Get service scheduled downtime depth -> 0 no downtime
        scheduled_downtime_depth = svc.scheduled_downtime_depth
        assert svc.scheduled_downtime_depth == 1

        # Wait for a while, the service recovers
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 0, 'OK']])
        assert "HARD" == svc.state_type
        assert "OK" == svc.state

        # Wait for a while, the service is still CRITICAL but after the downtime expiry time
        time.sleep(5)
        self.scheduler_loop(2, [[svc, 2, 'BAD']])
        assert "HARD" == svc.state_type
        assert "CRITICAL" == svc.state

        # No more downtime for the service nor the scheduler
        assert 0 == len(svc.downtimes)
        # The service is not anymore in a scheduled downtime period
        assert not svc.in_scheduled_downtime
        assert svc.scheduled_downtime_depth < scheduled_downtime_depth
        # No more comment for the service
        assert 0 == len(svc.comments)

        # Now 4 actions because the service is no more a problem and the downtime ended
        self.show_actions()
        self.assert_actions_count(4)
        # The downtime started
        self.assert_actions_match(-1, '/notifier.pl', 'command')
        self.assert_actions_match(-1, 'DOWNTIMESTART', 'type')
        self.assert_actions_match(-1, 'scheduled', 'status')
        # The downtime ended
        self.assert_actions_match(-1, '/notifier.pl', 'command')
        self.assert_actions_match(-1, 'DOWNTIMEEND', 'type')
        self.assert_actions_match(-1, 'scheduled', 'status')
        # The service is now a problem... with no notification
        self.assert_actions_match(-1, 'VOID', 'command')
        self.assert_actions_match(-1, 'PROBLEM', 'type')
        self.assert_actions_match(-1, 'scheduled', 'status')
        # The service is now a problem... with a notification
        self.assert_actions_match(-1, '/notifier.pl', 'command')
        self.assert_actions_match(-1, 'PROBLEM', 'type')
        self.assert_actions_match(-1, 'scheduled', 'status')

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in sorted(itervalues(self._broker['broks']), key=lambda x: x.creation_time):
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        print("Monitoring logs: %s" % monitoring_logs)
        expected_logs = [
            (u'info', u'EXTERNAL COMMAND: [%s] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;'
                      u'%s;%s;0;0;%s;downtime author;downtime comment' % (
                now, now, now + 3600, duration)),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;BAD'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;HARD;2;BAD'),
            (u'info', u'SERVICE DOWNTIME ALERT: test_host_0;test_ok_0;STARTED; '
                      u'Service has entered a period of scheduled downtime'),
            (u'info', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;'
                      u'DOWNTIMESTART (CRITICAL);notify-service;BAD'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;HARD;2;OK'),
            (u'info', u'SERVICE DOWNTIME ALERT: test_host_0;test_ok_0;STOPPED; '
                      u'Service has exited from a period of scheduled downtime'),
            (u'info', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;'
                      u'DOWNTIMEEND (OK);notify-service;OK'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;BAD'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;HARD;2;BAD'),
            (u'error', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;'
                       u'CRITICAL;notify-service;BAD')
        ]
        for log_level, log_message in expected_logs:
            assert (log_level, log_message) in monitoring_logs

    def test_schedule_fixed_host_downtime(self):
        """ Schedule a fixed downtime for an host """
        self.print_header()

        # Get the host
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []
        assert host.enable_notifications
        assert host.notifications_enabled
        assert host.notification_period
        # Not any downtime yet !
        assert host.downtimes == {}
        # Get service scheduled downtime depth
        assert host.scheduled_downtime_depth == 0
        # No current notifications
        assert 0 == host.current_notification_number, 'All OK no notifications'
        # To make tests quicker we make notifications send very quickly
        host.notification_interval = 0.001
        host.event_handler_enabled = False

        # Make the host be OK
        self.scheduler_loop(1, [[host, 0, 'UP']])

        # schedule a 5 seconds downtime
        duration = 5
        now = int(time.time())
        # downtime valid for 5 seconds from now
        cmd = "[%lu] SCHEDULE_HOST_DOWNTIME;test_host_0;%d;%d;1;;%d;" \
              "downtime author;downtime comment" % (now, now, now + duration, duration)
        self._sched.run_external_command(cmd)
        self.external_command_loop()
        # A downtime exist for the host
        assert len(host.downtimes) == 1
        downtime = host.downtimes.values()[0]
        assert downtime.comment == "downtime comment"
        assert downtime.author == "downtime author"
        assert downtime.start_time == now
        assert downtime.end_time == now + duration
        assert downtime.duration == duration
        # Fixed
        assert downtime.fixed
        # Already active
        assert downtime.is_in_effect
        # Cannot be deleted
        assert not downtime.can_be_deleted
        assert downtime.trigger_id == ""
        # Get host scheduled downtime depth
        scheduled_downtime_depth = host.scheduled_downtime_depth
        assert host.scheduled_downtime_depth == 1

        assert 0 == host.current_notification_number, 'Should not have any notification'
        # Notification: downtime start
        self.assert_actions_count(1)
        # The downtime started
        self.show_actions()
        self.assert_actions_match(0, 'notifier.pl --hostname test_host_0 --notificationtype DOWNTIMESTART --hoststate UP --hostoutput UP', 'command')
        self.assert_actions_match(0, 'NOTIFICATIONTYPE=DOWNTIMESTART, NOTIFICATIONRECIPIENTS=test_contact, NOTIFICATIONISESCALATED=False, NOTIFICATIONAUTHOR=downtime author, NOTIFICATIONAUTHORNAME=Not available, NOTIFICATIONAUTHORALIAS=Not available, NOTIFICATIONCOMMENT=downtime comment, HOSTNOTIFICATIONNUMBER=0, SERVICENOTIFICATIONNUMBER=0', 'command')

        # A comment exists in our host
        assert 1 == len(host.comments)

        # Make the host be OK after a while
        # time.sleep(1)
        self.scheduler_loop(2, [[host, 0, 'UP']])
        assert "HARD" == host.state_type
        assert "UP" == host.state

        assert 0 == host.current_notification_number, 'Should not have any notification'
        # Still only 1
        self.assert_actions_count(1)

        # The downtime still exist in our host
        assert 1 == len(host.downtimes)
        downtime = host.downtimes.values()[0]
        # The host is currently in a downtime period
        assert host.in_scheduled_downtime
        assert downtime.fixed
        assert downtime.is_in_effect
        assert not downtime.can_be_deleted

        # Make the host be DOWN/SOFT
        time.sleep(1)
        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        assert "SOFT" == host.state_type
        assert "DOWN" == host.state

        assert 0 == host.current_notification_number, 'Should not have any notification'
        # Still only 1
        self.assert_actions_count(1)

        assert 1 == len(host.downtimes)
        downtime = host.downtimes.values()[0]
        # The host is still in a downtime period
        assert host.in_scheduled_downtime
        assert downtime.fixed
        assert downtime.is_in_effect
        assert not downtime.can_be_deleted

        # Make the host be DOWN/HARD
        time.sleep(1)
        self.scheduler_loop(2, [[host, 2, 'DOWN']])
        assert "HARD" == host.state_type
        assert "DOWN" == host.state

        assert 0 == host.current_notification_number, 'Should not have any notification'
        # Now 2 actions because the service is a problem
        self.assert_actions_count(2)
        # The downtime started
        self.assert_actions_match(0, '/notifier.pl', 'command')
        self.assert_actions_match(0, 'DOWNTIMESTART', 'type')
        self.assert_actions_match(0, 'scheduled', 'status')
        # The service is now a problem...
        self.assert_actions_match(1, 'VOID', 'command')
        self.assert_actions_match(1, 'PROBLEM', 'type')
        self.assert_actions_match(1, 'scheduled', 'status')

        assert 1 == len(host.downtimes)
        downtime = host.downtimes.values()[0]
        # The service is still in a downtime period
        assert host.in_scheduled_downtime
        assert downtime.fixed
        assert downtime.is_in_effect
        assert not downtime.can_be_deleted

        # Wait for a while, the service is back to OK but after the downtime expiry time
        time.sleep(5)
        self.scheduler_loop(2, [[host, 0, 'UP']])
        assert "HARD" == host.state_type
        assert "UP" == host.state

        # No more downtime for the service nor the scheduler
        assert 0 == len(host.downtimes)
        # The service is not anymore in a scheduled downtime period
        assert not host.in_scheduled_downtime
        assert host.scheduled_downtime_depth < scheduled_downtime_depth
        # No more comment for the host
        assert 0 == len(host.comments)

        assert 0 == host.current_notification_number, 'Should not have any notification'
        # Now 4 actions because the service is no more a problem and the downtime ended
        self.show_actions()
        self.assert_actions_count(4)
        # The downtime started
        self.assert_actions_match(0, 'notifier.pl --hostname test_host_0 --notificationtype DOWNTIMESTART --hoststate UP --hostoutput UP', 'command')
        self.assert_actions_match(0, 'NOTIFICATIONTYPE=DOWNTIMESTART, NOTIFICATIONRECIPIENTS=test_contact, NOTIFICATIONISESCALATED=False, NOTIFICATIONAUTHOR=downtime author, NOTIFICATIONAUTHORNAME=Not available, NOTIFICATIONAUTHORALIAS=Not available, NOTIFICATIONCOMMENT=downtime comment, HOSTNOTIFICATIONNUMBER=0, SERVICENOTIFICATIONNUMBER=0', 'command')
        # The host is now a problem...
        self.assert_actions_match(1, '/notifier.pl', 'command')
        self.assert_actions_match(1, 'PROBLEM', 'type')
        self.assert_actions_match(1, 'scheduled', 'status')
        # The downtime ended
        self.assert_actions_match(2, 'notifier.pl --hostname test_host_0 --notificationtype DOWNTIMEEND --hoststate DOWN --hostoutput DOWN', 'command')
        self.assert_actions_match(2, 'NOTIFICATIONTYPE=DOWNTIMEEND, NOTIFICATIONRECIPIENTS=test_contact, NOTIFICATIONISESCALATED=False, NOTIFICATIONAUTHOR=downtime author, NOTIFICATIONAUTHORNAME=Not available, NOTIFICATIONAUTHORALIAS=Not available, NOTIFICATIONCOMMENT=downtime comment, HOSTNOTIFICATIONNUMBER=0, SERVICENOTIFICATIONNUMBER=0', 'command')
        # The host is no more a problem...
        self.assert_actions_match(3, '/notifier.pl', 'command')
        self.assert_actions_match(3, 'RECOVERY', 'type')
        self.assert_actions_match(3, 'scheduled', 'status')

        # Clear actions
        self.clear_actions()

        # Make the host be DOWN/HARD
        time.sleep(1)
        self.scheduler_loop(3, [[host, 2, 'DOWN']])
        assert "HARD" == host.state_type
        assert "DOWN" == host.state

        # 2 actions because the host is a problem and a notification is raised
        self.show_actions()
        self.assert_actions_count(2)

        # The host is now a problem...
        # A problem notification is now raised...
        self.assert_actions_match(0, 'notification', 'is_a')
        self.assert_actions_match(0, '/notifier.pl', 'command')
        self.assert_actions_match(0, 'PROBLEM', 'type')
        self.assert_actions_match(0, 'scheduled', 'status')
        self.assert_actions_match(1, 'VOID', 'command')
        self.assert_actions_match(1, 'PROBLEM', 'type')
        self.assert_actions_match(1, 'scheduled', 'status')

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in sorted(itervalues(self._broker['broks']), key=lambda x: x.creation_time):
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        print("Monitoring logs: %s" % monitoring_logs)
        expected_logs = [
            (u'info', u'EXTERNAL COMMAND: [%s] SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;;%s;'
                      u'downtime author;downtime comment' % (
                now, now, now + duration, duration)),
            (u'info', u'HOST DOWNTIME ALERT: test_host_0;STARTED; '
                      u'Host has entered a period of scheduled downtime'),
            (u'info', u'HOST NOTIFICATION: test_contact;test_host_0;'
                      u'DOWNTIMESTART (UP);notify-host;UP'),
            (u'error', u'HOST ALERT: test_host_0;DOWN;SOFT;1;DOWN'),
            (u'error', u'HOST ALERT: test_host_0;DOWN;SOFT;2;DOWN'),
            (u'error', u'HOST ALERT: test_host_0;DOWN;HARD;3;DOWN'),
            (u'info', u'HOST DOWNTIME ALERT: test_host_0;STOPPED; '
                      u'Host has exited from a period of scheduled downtime'),
            (u'info', u'HOST NOTIFICATION: test_contact;test_host_0;'
                      u'DOWNTIMEEND (DOWN);notify-host;DOWN'),
            (u'error', u'HOST NOTIFICATION: test_contact;test_host_0;DOWN;notify-host;DOWN'),
            (u'info', u'HOST ALERT: test_host_0;UP;HARD;3;UP'),
            (u'info', u'HOST NOTIFICATION: test_contact;test_host_0;UP;notify-host;UP'),
            (u'error', u'HOST ALERT: test_host_0;DOWN;SOFT;1;DOWN'),
            (u'error', u'HOST ALERT: test_host_0;DOWN;SOFT;2;DOWN'),
            (u'error', u'HOST ALERT: test_host_0;DOWN;HARD;3;DOWN'),
            (u'error', u'HOST NOTIFICATION: test_contact;test_host_0;DOWN;notify-host;DOWN')
        ]
        for log_level, log_message in expected_logs:
            assert (log_level, log_message) in monitoring_logs

    def test_schedule_fixed_host_downtime_with_service(self):
        """ Schedule a downtime for an host - services changes are not notified """
        self.print_header()

        # Get the host
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []
        # Not any downtime yet !
        assert host.downtimes == {}
        # Get service scheduled downtime depth
        assert host.scheduled_downtime_depth == 0
        # No current notifications
        assert 0 == host.current_notification_number, 'All OK no notifications'
        # To make tests quicker we make notifications send very quickly
        host.notification_interval = 0.001
        host.event_handler_enabled = False

        # Get the service
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        # Not any downtime yet !
        assert svc.downtimes == {}
        # Get service scheduled downtime depth
        assert svc.scheduled_downtime_depth == 0
        # No current notifications
        assert 0 == svc.current_notification_number, 'All OK no notifications'
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.event_handler_enabled = False

        # Make the host and service be OK
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])

        # schedule a 5 seconds downtime
        duration = 5
        now = int(time.time())
        # downtime valid for 5 seconds from now
        cmd = "[%lu] SCHEDULE_HOST_DOWNTIME;test_host_0;%d;%d;1;;%d;" \
              "downtime author;downtime comment" % (now, now, now + duration, duration)
        self._sched.run_external_command(cmd)
        self.external_command_loop()
        # A downtime exist for the host
        assert len(host.downtimes) == 1
        downtime = host.downtimes.values()[0]
        assert downtime.comment == "downtime comment"
        assert downtime.author == "downtime author"
        assert downtime.start_time == now
        assert downtime.end_time == now + duration
        assert downtime.duration == duration
        # Fixed
        assert downtime.fixed
        # Already active
        assert downtime.is_in_effect
        # Cannot be deleted
        assert not downtime.can_be_deleted
        assert downtime.trigger_id == ""
        # Get host scheduled downtime depth
        scheduled_downtime_depth = host.scheduled_downtime_depth
        assert host.scheduled_downtime_depth == 1

        assert 0 == host.current_notification_number, 'Should not have any notification'
        # Notification: downtime start
        self.assert_actions_count(1)
        # The downtime started
        self.assert_actions_match(0, '/notifier.pl', 'command')
        self.assert_actions_match(0, 'DOWNTIMESTART', 'type')
        self.assert_actions_match(0, 'scheduled', 'status')

        # A comment exist in our host
        assert 1 == len(host.comments)

        # Make the host be DOWN/HARD
        time.sleep(1)
        self.scheduler_loop(3, [[host, 2, 'DOWN']])
        assert "HARD" == host.state_type
        assert "DOWN" == host.state

        assert 0 == host.current_notification_number, 'Should not have any notification'
        # Now 2 actions because the host is a problem
        self.assert_actions_count(2)
        # The downtime started
        self.assert_actions_match(0, '/notifier.pl', 'command')
        self.assert_actions_match(0, 'DOWNTIMESTART', 'type')
        self.assert_actions_match(0, 'scheduled', 'status')
        # The host is now a problem...
        self.assert_actions_match(1, 'VOID', 'command')
        self.assert_actions_match(1, 'PROBLEM', 'type')
        self.assert_actions_match(1, 'scheduled', 'status')

        # Make the service be CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(3, [[svc, 2, 'CRITICAL']])
        assert "HARD" == host.state_type
        assert "DOWN" == host.state
        assert "HARD" == svc.state_type
        assert "CRITICAL" == svc.state

        # Still only 1 downtime
        assert 1 == len(host.downtimes)
        # No downtime for the service
        assert 0 == len(svc.downtimes)
        assert not svc.in_scheduled_downtime
        # The host is still in a scheduled downtime
        assert self._sched.find_item_by_id(svc.host).in_scheduled_downtime

        assert 0 == host.current_notification_number, 'Should not have any notification'
        assert 0 == svc.current_notification_number, 'Should not have any notification'
        # Now 3 actions because the host and its service are problems
        self.assert_actions_count(3)
        # The downtime started
        self.assert_actions_match(0, '/notifier.pl', 'command')
        self.assert_actions_match(0, 'DOWNTIMESTART', 'type')
        self.assert_actions_match(0, 'scheduled', 'status')
        # The host is always a problem...
        self.assert_actions_match(1, 'VOID', 'command')
        self.assert_actions_match(1, 'PROBLEM', 'type')
        self.assert_actions_match(1, 'scheduled', 'status')
        # The service is now a problem...
        self.assert_actions_match(2, 'VOID', 'command')
        self.assert_actions_match(2, 'PROBLEM', 'type')
        self.assert_actions_match(2, 'scheduled', 'status')

        # Make the service be OK/HARD
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 0, 'OK']])
        assert "HARD" == host.state_type
        assert "DOWN" == host.state
        assert "HARD" == svc.state_type
        assert "OK" == svc.state

        # Make the host be UP/HARD
        time.sleep(1)
        self.scheduler_loop(1, [[host, 0, 'UP']])
        assert "HARD" == host.state_type
        assert "UP" == host.state
        assert "HARD" == svc.state_type
        assert "OK" == svc.state

        assert 0 == host.current_notification_number, 'Should not have any notification'
        assert 0 == svc.current_notification_number, 'Should not have any notification'

        # Only 1 action because the host downtime start
        self.assert_actions_count(1)
        # The downtime started
        self.assert_actions_match(0, '/notifier.pl', 'command')
        self.assert_actions_match(0, 'DOWNTIMESTART', 'type')
        self.assert_actions_match(0, 'scheduled', 'status')

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in sorted(itervalues(self._broker['broks']), key=lambda x: x.creation_time):
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        print("Monitoring logs: %s" % monitoring_logs)
        expected_logs = [
            (u'info', u'EXTERNAL COMMAND: [%s] SCHEDULE_HOST_DOWNTIME;test_host_0;'
                      u'%s;%s;1;;%s;downtime author;downtime comment' % (
                now, now, now + duration, duration)),
            (u'info', u'HOST DOWNTIME ALERT: test_host_0;STARTED; '
                      u'Host has entered a period of scheduled downtime'),
            (u'info', u'HOST NOTIFICATION: test_contact;test_host_0;DOWNTIMESTART (UP);notify-host;UP'),
            (u'error', u'HOST ALERT: test_host_0;DOWN;SOFT;1;DOWN'),
            (u'error', u'HOST ALERT: test_host_0;DOWN;SOFT;2;DOWN'),
            (u'error', u'HOST ALERT: test_host_0;DOWN;HARD;3;DOWN'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;CRITICAL'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;HARD;2;CRITICAL'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;HARD;2;OK'),
            (u'info', u'HOST ALERT: test_host_0;UP;HARD;3;UP')
        ]
        for log_level, log_message in expected_logs:
            assert (log_level, log_message) in monitoring_logs

if __name__ == '__main__':
    unittest.main()
