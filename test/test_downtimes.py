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

import time
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
        self.assertTrue(self.conf_is_correct)
        
        # Our scheduler
        self._sched = self.schedulers['scheduler-master'].sched

        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_schedule_fixed_svc_downtime(self):
        """ Schedule a fixed downtime for a service """
        self.print_header()

        # Get the service
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        # Not any downtime yet !
        self.assertEqual(svc.downtimes, [])
        # Get service scheduled downtime depth
        self.assertEqual(svc.scheduled_downtime_depth, 0)
        # No current notifications
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
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
        self.assertEqual(len(svc.downtimes), 1)
        downtime_id = svc.downtimes[0]
        self.assertIn(downtime_id, self._sched.downtimes)
        downtime = self._sched.downtimes[downtime_id]
        self.assertEqual(downtime.comment, "downtime comment")
        self.assertEqual(downtime.author, "downtime author")
        self.assertEqual(downtime.start_time, now)
        self.assertEqual(downtime.end_time, now + duration)
        self.assertEqual(downtime.duration, duration)
        # Fixed
        self.assertTrue(downtime.fixed)
        # Already active
        self.assertTrue(downtime.is_in_effect)
        # Cannot be deleted
        self.assertFalse(downtime.can_be_deleted)
        self.assertEqual(downtime.trigger_id, "0")
        # Get service scheduled downtime depth
        scheduled_downtime_depth = svc.scheduled_downtime_depth
        self.assertEqual(svc.scheduled_downtime_depth, 1)

        self.assertEqual(0, svc.current_notification_number, 'Should not have any notification')
        # Notification: downtime start
        self.assert_actions_count(1)
        # The downtime started
        self.assert_actions_match(0, '/notifier.pl', 'command')
        self.assert_actions_match(0, 'DOWNTIMESTART', 'type')
        self.assert_actions_match(0, 'scheduled', 'status')

        # The downtime also exist in our scheduler
        self.assertEqual(1, len(self._sched.downtimes))
        self.assertIn(svc.downtimes[0], self._sched.downtimes)
        self.assertTrue(self._sched.downtimes[svc.downtimes[0]].fixed)
        self.assertTrue(self._sched.downtimes[svc.downtimes[0]].is_in_effect)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].can_be_deleted)

        # A comment exist in our scheduler and in our service
        self.assertEqual(1, len(self._sched.comments))
        self.assertEqual(1, len(svc.comments))
        self.assertIn(svc.comments[0], self._sched.comments)
        self.assertEqual(self._sched.comments[svc.comments[0]].uuid,
                         self._sched.downtimes[svc.downtimes[0]].comment_id)

        # Make the service be OK after a while
        # time.sleep(1)
        self.scheduler_loop(2, [[svc, 0, 'OK']])
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual("OK", svc.state)

        self.assertEqual(0, svc.current_notification_number, 'Should not have any notification')
        # Still only 1
        self.assert_actions_count(1)

        # The downtime still exist in our scheduler and in our service
        self.assertEqual(1, len(self._sched.downtimes))
        self.assertEqual(1, len(svc.downtimes))
        self.assertIn(svc.downtimes[0], self._sched.downtimes)
        # The service is currently in a downtime period
        self.assertTrue(svc.in_scheduled_downtime)
        self.assertTrue(self._sched.downtimes[svc.downtimes[0]].fixed)
        self.assertTrue(self._sched.downtimes[svc.downtimes[0]].is_in_effect)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].can_be_deleted)

        # Make the service be CRITICAL/SOFT
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        self.assertEqual("SOFT", svc.state_type)
        self.assertEqual("CRITICAL", svc.state)

        self.assertEqual(0, svc.current_notification_number, 'Should not have any notification')
        # Still only 1
        self.assert_actions_count(1)

        self.assertEqual(1, len(self._sched.downtimes))
        self.assertEqual(1, len(svc.downtimes))
        self.assertIn(svc.downtimes[0], self._sched.downtimes)
        # The service is still in a downtime period
        self.assertTrue(svc.in_scheduled_downtime)
        self.assertTrue(self._sched.downtimes[svc.downtimes[0]].fixed)
        self.assertTrue(self._sched.downtimes[svc.downtimes[0]].is_in_effect)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].can_be_deleted)

        # Make the service be CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(1, [[svc, 2, 'BAD']])
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual("CRITICAL", svc.state)

        self.assertEqual(0, svc.current_notification_number, 'Should not have any notification')
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

        self.assertEqual(1, len(self._sched.downtimes))
        self.assertEqual(1, len(svc.downtimes))
        self.assertIn(svc.downtimes[0], self._sched.downtimes)
        # The service is still in a downtime period
        self.assertTrue(svc.in_scheduled_downtime)
        self.assertTrue(self._sched.downtimes[svc.downtimes[0]].fixed)
        self.assertTrue(self._sched.downtimes[svc.downtimes[0]].is_in_effect)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].can_be_deleted)

        # Wait for a while, the service is back to OK but after the downtime expiry time
        time.sleep(5)
        self.scheduler_loop(2, [[svc, 0, 'OK']])
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual("OK", svc.state)

        # No more downtime for the service nor the scheduler
        self.assertEqual(0, len(self._sched.downtimes))
        self.assertEqual(0, len(svc.downtimes))
        # The service is not anymore in a scheduled downtime period
        self.assertFalse(svc.in_scheduled_downtime)
        self.assertLess(svc.scheduled_downtime_depth, scheduled_downtime_depth)
        # No more comment for the service nor the scheduler
        self.assertEqual(0, len(self._sched.comments))
        self.assertEqual(0, len(svc.comments))

        self.assertEqual(0, svc.current_notification_number, 'Should not have any notification')
        # Now 4 actions because the service is no more a problem and the downtime ended
        self.show_actions()
        self.assert_actions_count(4)
        # The downtime started
        self.assert_actions_match(0, '/notifier.pl', 'command')
        self.assert_actions_match(0, 'DOWNTIMESTART', 'type')
        self.assert_actions_match(0, 'scheduled', 'status')
        # The service is now a problem...
        self.assert_actions_match(1, '/notifier.pl', 'command')
        self.assert_actions_match(1, 'PROBLEM', 'type')
        self.assert_actions_match(1, 'scheduled', 'status')
        # The downtime ended
        self.assert_actions_match(2, '/notifier.pl', 'command')
        self.assert_actions_match(2, 'DOWNTIMEEND', 'type')
        self.assert_actions_match(2, 'scheduled', 'status')
        # The service is now a problem...
        self.assert_actions_match(3, '/notifier.pl', 'command')
        self.assert_actions_match(3, 'RECOVERY', 'type')
        self.assert_actions_match(3, 'scheduled', 'status')

        # Clear actions
        self.clear_actions()

        # Make the service be CRITICAL/HARD
        time.sleep(1)
        self.scheduler_loop(2, [[svc, 2, 'BAD']])
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual("CRITICAL", svc.state)

        # 2 actions because the service is a problem and a notification is raised
        self.show_actions()
        self.assert_actions_count(2)

        # The service is now a problem...
        # A problem notification is now raised...
        self.assert_actions_match(0, 'VOID', 'command')
        self.assert_actions_match(0, 'PROBLEM', 'type')
        self.assert_actions_match(0, 'scheduled', 'status')
        self.assert_actions_match(1, 'notification', 'is_a')
        self.assert_actions_match(1, '/notifier.pl', 'command')
        self.assert_actions_match(1, 'PROBLEM', 'type')
        self.assert_actions_match(1, 'scheduled', 'status')

    def test_schedule_flexible_svc_downtime(self):
        """ Schedule a flexible downtime for a service """
        self.print_header()

        # Get the service
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        # Not any downtime yet !
        self.assertEqual(svc.downtimes, [])
        # Get service scheduled downtime depth
        self.assertEqual(svc.scheduled_downtime_depth, 0)
        # No current notifications
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
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
        self.assertEqual(len(svc.downtimes), 1)
        downtime_id = svc.downtimes[0]
        self.assertIn(downtime_id, self._sched.downtimes)
        downtime = self._sched.downtimes[downtime_id]
        self.assertEqual(downtime.comment, "downtime comment")
        self.assertEqual(downtime.author, "downtime author")
        self.assertEqual(downtime.start_time, now)
        self.assertEqual(downtime.end_time, now + 3600)
        self.assertEqual(downtime.duration, duration)
        # Not fixed
        self.assertFalse(downtime.fixed)
        # Not yet active
        self.assertFalse(downtime.is_in_effect)
        # Cannot be deleted
        self.assertFalse(downtime.can_be_deleted)
        self.assertEqual(downtime.trigger_id, "0")
        # Get service scheduled downtime depth -> 0 no downtime
        scheduled_downtime_depth = svc.scheduled_downtime_depth
        self.assertEqual(svc.scheduled_downtime_depth, 0)

        self.assertEqual(0, svc.current_notification_number, 'Should not have any notification')
        # No notifications, downtime did not started !
        self.assert_actions_count(0)

        # The downtime also exist in our scheduler
        self.assertEqual(1, len(self._sched.downtimes))
        self.assertIn(svc.downtimes[0], self._sched.downtimes)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].fixed)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].is_in_effect)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].can_be_deleted)

        # A comment exist in our scheduler and in our service
        self.assertEqual(1, len(self._sched.comments))
        self.assertEqual(1, len(svc.comments))
        self.assertIn(svc.comments[0], self._sched.comments)
        self.assertEqual(self._sched.comments[svc.comments[0]].uuid,
                         self._sched.downtimes[svc.downtimes[0]].comment_id)

        #----------------------------------------------------------------
        # run the service and return an OK status
        # check if the downtime is still inactive
        #----------------------------------------------------------------
        self.scheduler_loop(2, [[svc, 0, 'OK']])
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual("OK", svc.state)
        self.assertEqual(1, len(self._sched.downtimes))
        self.assertEqual(1, len(svc.downtimes))
        self.assertIn(svc.downtimes[0], self._sched.downtimes)
        self.assertFalse(svc.in_scheduled_downtime)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].fixed)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].is_in_effect)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].can_be_deleted)

        # No notifications, downtime did not started !
        self.assertEqual(0, svc.current_notification_number, 'Should not have any notification')
        self.assert_actions_count(0)

        time.sleep(1)
        #----------------------------------------------------------------
        # run the service to get a soft critical status
        # check if the downtime is still inactive
        #----------------------------------------------------------------
        self.scheduler_loop(1, [[svc, 2, 'BAD']])
        self.assertEqual("SOFT", svc.state_type)
        self.assertEqual("CRITICAL", svc.state)
        self.assertEqual(1, len(self._sched.downtimes))
        self.assertEqual(1, len(svc.downtimes))
        self.assertIn(svc.downtimes[0], self._sched.downtimes)
        self.assertFalse(svc.in_scheduled_downtime)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].fixed)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].is_in_effect)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].can_be_deleted)

        # No notifications, downtime did not started !
        self.assertEqual(0, svc.current_notification_number, 'Should not have any notification')
        self.assert_actions_count(0)

        time.sleep(1)
        #----------------------------------------------------------------
        # run the service again to get a hard critical status
        # check if the downtime is active now
        #----------------------------------------------------------------
        self.scheduler_loop(1, [[svc, 2, 'BAD']])
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual("CRITICAL", svc.state)
        time.sleep(1)
        self.assertEqual(1, len(self._sched.downtimes))
        self.assertEqual(1, len(svc.downtimes))
        self.assertIn(svc.downtimes[0], self._sched.downtimes)
        # TODO: should be True, no? Remains False because it is flexible?
        # self.assertTrue(svc.in_scheduled_downtime)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].fixed)
        # TODO: should be True, no? Remains False because it is flexible?
        # self.assertTrue(self._sched.downtimes[svc.downtimes[0]].is_in_effect)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].can_be_deleted)

        # 2 actions because the service is a problem and the downtime started
        self.assert_actions_count(2)
        # The downtime started
        self.assert_actions_match(0, '/notifier.pl', 'command')
        self.assert_actions_match(0, 'DOWNTIMESTART', 'type')
        self.assert_actions_match(0, 'scheduled', 'status')
        # The service is now a problem...
        self.assert_actions_match(1, 'VOID', 'command')
        self.assert_actions_match(1, 'PROBLEM', 'type')
        self.assert_actions_match(1, 'scheduled', 'status')

        #----------------------------------------------------------------
        # cancel the downtime
        # check if the downtime is inactive now and can be deleted
        #----------------------------------------------------------------
        scheduled_downtime_depth = svc.scheduled_downtime_depth
        cmd = "[%lu] DEL_SVC_DOWNTIME;%s" % (now, self._sched.downtimes[svc.downtimes[0]].uuid)
        self._sched.run_external_command(cmd)
        self.external_command_loop()
        self.assertEqual(1, len(self._sched.downtimes))
        self.assertEqual(1, len(svc.downtimes))
        self.assertFalse(svc.in_scheduled_downtime)
        self.assertLess(svc.scheduled_downtime_depth, scheduled_downtime_depth)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].fixed)
        self.assertFalse(self._sched.downtimes[svc.downtimes[0]].is_in_effect)
        self.assertTrue(self._sched.downtimes[svc.downtimes[0]].can_be_deleted)
        self.assertEqual(1, len(self._sched.comments))
        self.assertEqual(1, len(svc.comments))
        time.sleep(1)
        #----------------------------------------------------------------
        # run the service again with a critical status
        # the downtime must have disappeared
        # a notification must be sent
        #----------------------------------------------------------------
        self.scheduler_loop(1, [[svc, 2, 'BAD']])
        self.assertEqual(0, len(self._sched.downtimes))
        self.assertEqual(0, len(svc.downtimes))
        self.assertEqual(0, len(self._sched.comments))
        self.assertEqual(0, len(svc.comments))
        self.show_logs()
        self.show_actions()

    def test_schedule_fixed_host_downtime(self):
        self.print_header()
        # schedule a 2-minute downtime
        # downtime must be active
        # consume a good result, sleep for a minute
        # downtime must be active
        # consume a bad result
        # downtime must be active
        # no notification must be found in broks
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        print "test_schedule_fixed_host_downtime initialized"
        self.show_logs()
        self.show_actions()
        self.assertEqual(0, self.count_logs())
        self.assertEqual(0, self.count_actions())
        #----------------------------------------------------------------
        # schedule a downtime of 10 minutes for the host
        #----------------------------------------------------------------
        duration = 600
        now = time.time()
        # fixed downtime valid for the next 10 minutes
        cmd = "[%lu] SCHEDULE_HOST_DOWNTIME;test_host_0;%d;%d;1;;%d;downtime author;downtime comment" % (now, now, now + duration, duration)

        self._sched.run_external_command(cmd)
        self._sched.update_downtimes_and_comments()
        print "Launch scheduler loop"
        self.scheduler_loop(1, [], do_sleep=False)  # push the downtime notification
        self.show_actions()
        print "Launch worker loop"
        #self.worker_loop()
        self.show_actions()
        print "After both launchs"
        time.sleep(20)
        #----------------------------------------------------------------
        # check if a downtime object exists (scheduler and host)
        #----------------------------------------------------------------
        self.assertEqual(1, len(self._sched.downtimes))
        self.assertEqual(1, len(host.downtimes))
        self.assertIn(host.downtimes[0], self._sched.downtimes)
        self.assertTrue(self._sched.downtimes[host.downtimes[0]].fixed)
        self.assertTrue(self._sched.downtimes[host.downtimes[0]].is_in_effect)
        self.assertFalse(self._sched.downtimes[host.downtimes[0]].can_be_deleted)
        self.assertEqual(1, len(self._sched.comments))
        self.assertEqual(1, len(host.comments))
        self.assertIn(host.comments[0], self._sched.comments)
        self.assertEqual(self._sched.comments[host.comments[0]].uuid, self._sched.downtimes[host.downtimes[0]].comment_id)
        self.show_logs()
        self.show_actions()
        print "*****************************************************************************************************************************************************************Log matching:", self.get_log_match("STARTED*")
        self.show_actions()
        self.assertEqual(2, self.count_logs())    # start downt, notif downt
        print self.count_actions() # notif" down is removed, so only donwtime
        self.assertEqual(1, self.count_actions())
        self.scheduler_loop(1, [], do_sleep=False)
        self.show_logs()
        self.show_actions()
        
        self.assertEqual(2, self.count_logs())    # start downt, notif downt
        self.clear_logs()
        self.clear_actions()
        #----------------------------------------------------------------
        # send the host to a hard DOWN state
        # check log messages, (no) notifications and eventhandlers
        #----------------------------------------------------------------
        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        self.show_logs()
        self.show_actions()
        self.assertEqual(2, self.count_logs())    # soft1, evt1
        self.assertEqual(1, self.count_actions())  # evt1
        self.clear_logs()
        #--
        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        self.show_logs()
        self.show_actions()
        self.assertEqual(2, self.count_logs())    # soft2, evt2
        self.assertEqual(1, self.count_actions())  # evt2
        self.clear_logs()
        #--
        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        self.show_logs()
        self.show_actions()
        self.assertEqual(2, self.count_logs())    # hard3, evt3
        self.assertEqual(2, self.count_actions())  # evt3, notif"
        self.clear_logs()
        #--
        # we have a notification, but this is blocked. it will stay in
        # the actions queue because we have a notification_interval.
        # it's called notif" because it is a master notification
        print "DBG: host", host.state, host.state_type
        self.scheduler_loop(1, [[host, 2, 'DOWN']], do_sleep=True)
        print "DBG2: host", host.state, host.state_type
        self.show_logs()
        self.show_actions()
        self.assertEqual(0, self.count_logs())     #
        self.assertEqual(1, self.count_actions())  # notif"
        self.clear_logs()
        #----------------------------------------------------------------
        # the host comes UP again
        # check log messages, (no) notifications and eventhandlers
        # a (recovery) notification was created, but has been blocked.
        # should be a zombie, but was deteleted
        #----------------------------------------------------------------
        self.scheduler_loop(1, [[host, 0, 'UP']], do_sleep=True)
        self.show_logs()
        self.show_actions()
        self.assertEqual(2, self.count_logs())    # hard3ok, evtok
        self.assertEqual(1, self.count_actions())  # evtok, notif"
        self.clear_logs()
        self.clear_actions()

    def test_schedule_fixed_host_downtime_with_service(self):
        self.print_header()
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        host.notification_interval = 0
        svc.notification_interval = 0
        self.show_logs()
        self.show_actions()
        self.assertEqual(0, self.count_logs())
        self.assertEqual(0, self.count_actions())
        #----------------------------------------------------------------
        # schedule a downtime of 10 minutes for the host
        #----------------------------------------------------------------
        duration = 600
        now = time.time()
        cmd = "[%lu] SCHEDULE_HOST_DOWNTIME;test_host_0;%d;%d;1;;%d;downtime author;downtime comment" % (now, now, now + duration, duration)
        self._sched.run_external_command(cmd)
        self._sched.update_downtimes_and_comments()
        self.scheduler_loop(1, [], do_sleep=False)  # push the downtime notification
        #self.worker_loop() # push the downtime notification
        time.sleep(10)
        #----------------------------------------------------------------
        # check if a downtime object exists (scheduler and host)
        # check the start downtime notification
        #----------------------------------------------------------------
        self.assertEqual(1, len(self._sched.downtimes))
        self.assertEqual(1, len(host.downtimes))
        self.assertTrue(host.in_scheduled_downtime)
        self.assertIn(host.downtimes[0], self._sched.downtimes)
        self.assertTrue(self._sched.downtimes[host.downtimes[0]].fixed)
        self.assertTrue(self._sched.downtimes[host.downtimes[0]].is_in_effect)
        self.assertFalse(self._sched.downtimes[host.downtimes[0]].can_be_deleted)
        self.assertEqual(1, len(self._sched.comments))
        self.assertEqual(1, len(host.comments))
        self.assertIn(host.comments[0], self._sched.comments)
        self.assertEqual(self._sched.comments[host.comments[0]].uuid, self._sched.downtimes[host.downtimes[0]].comment_id)
        self.scheduler_loop(4, [[host, 2, 'DOWN']], do_sleep=True)
        self.show_logs()
        self.show_actions()
        self.assertEqual(8, self.count_logs())    # start downt, notif downt, soft1, evt1, soft 2, evt2, hard 3, evt3
        self.clear_logs()
        self.clear_actions()
        #----------------------------------------------------------------
        # now the service becomes critical
        # check that the host has a downtime, _not_ the service
        # check logs, (no) notifications and eventhandlers
        #----------------------------------------------------------------
        print "now the service goes critical"
        self.scheduler_loop(4, [[svc, 2, 'CRITICAL']], do_sleep=True)
        self.assertEqual(1, len(self._sched.downtimes))
        self.assertEqual(0, len(svc.downtimes))
        self.assertFalse(svc.in_scheduled_downtime)
        self.assertTrue(self._sched.find_item_by_id(svc.host).in_scheduled_downtime)
        self.show_logs()
        self.show_actions()
        # soft 1, evt1, hard 2, evt2
        self.assertEqual(4, self.count_logs())
        self.clear_logs()
        self.clear_actions()
        #----------------------------------------------------------------
        # the host comes UP again
        # check log messages, (no) notifications and eventhandlers
        #----------------------------------------------------------------
        print "now the host comes up"
        self.scheduler_loop(2, [[host, 0, 'UP']], do_sleep=True)
        self.show_logs()
        self.show_actions()
        # hard 3, eventhandler
        self.assertEqual(2, self.count_logs())    # up, evt
        self.clear_logs()
        self.clear_actions()
        #----------------------------------------------------------------
        # the service becomes OK again
        # check log messages, (no) notifications and eventhandlers
        # check if the stop downtime notification is the only one
        #----------------------------------------------------------------
        self.scheduler_loop(2, [[host, 0, 'UP']], do_sleep=True)
        self.assertEqual(0, len(self._sched.downtimes))
        self.assertEqual(0, len(host.downtimes))
        self.assertFalse(host.in_scheduled_downtime)
        self.show_logs()
        self.show_actions()
        self.assert_log_match(1, 'HOST DOWNTIME ALERT.*STOPPED')
        self.clear_logs()
        self.clear_actions()
        # todo
        # checks return 1=warn. this means normally up
        # set use_aggressive_host_checking which treats warn as down

        # send host into downtime
        # run service checks with result critical
        # host exits downtime
        # does the service send a notification like when it exts a svc dt?
        # check for notifications

        # host is down and in downtime. what about service eventhandlers?

    def test_notification_after_cancel_flexible_svc_downtime(self):
        # schedule flexible downtime
        # good check
        # bad check -> SOFT;1
        #  eventhandler SOFT;1
        # bad check -> HARD;2
        #  downtime alert
        #  eventhandler HARD;2
        # cancel downtime
        # bad check -> HARD;2
        #  notification critical
        #
        pass

if __name__ == '__main__':
    unittest.main()
