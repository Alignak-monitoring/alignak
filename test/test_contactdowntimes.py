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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
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

#
# This file is used to test host- and service-downtimes.
#

import time
import datetime
from freezegun import freeze_time
from .alignak_test import AlignakTest


class TestContactDowntime(AlignakTest):
    """
    This class test downtime for contacts
    """

    def setUp(self):
        super(TestContactDowntime, self).setUp()
        self.setup_with_file("cfg/cfg_default.cfg")
        self._sched = self._scheduler

    def test_contact_downtime(self):
        """
        Test contact downtime and brok creation associated
        """
        # schedule a 2-minute downtime
        # downtime must be active
        # consume a good result, sleep for a minute
        # downtime must be active
        # consume a bad result
        # downtime must be active
        # no notification must be found in broks
        duration = 600
        now = time.time()
        # downtime valid for the next 2 minutes
        test_contact = self._sched.contacts.find_by_name('test_contact')
        cmd = "[%lu] SCHEDULE_CONTACT_DOWNTIME;test_contact;%d;%d;lausser;blablub" % (now, now, now + duration)
        self._sched.run_external_commands([cmd])
        self.external_command_loop()

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        # Change the notif interval, so we can notify as soon as we want
        svc.notification_interval = 0.001

        host = self._sched.hosts.find_by_name("test_host_0")
        host.act_depend_of = []  # ignore the router

        #time.sleep(20)
        # We loop, the downtime will be checked and activated
        self.scheduler_loop(1, [[svc, 0, 'OK'], [host, 0, 'UP']])

        self.assert_any_brok_match('CONTACT DOWNTIME ALERT.*;STARTED')

        print("downtime was scheduled. check its activity and the comment\n"*5)
        self.assertEqual(1, len(test_contact.downtimes))

        downtime = list(test_contact.downtimes.values())[0]
        assert downtime.is_in_effect
        assert not downtime.can_be_deleted

        # Ok, we define the downtime like we should, now look at if it does the job: do not
        # raise notif during a downtime for this contact
        self.scheduler_loop(3, [[svc, 2, 'CRITICAL']])

        # We should NOT see any service notification
        self.assert_no_brok_match('SERVICE NOTIFICATION.*;CRITICAL')

        # Now we short the downtime a lot so it will be stop at now + 1 sec.
        downtime.end_time = time.time() + 1

        time.sleep(2)

        # We invalidate it with a scheduler loop
        self.scheduler_loop(1, [])

        # So we should be out now, with a log
        self.assert_any_brok_match('CONTACT DOWNTIME ALERT.*;STOPPED')

        print("\n\nDowntime was ended. Check it is really stopped")
        self.assertEqual(0, len(test_contact.downtimes))

        for n in list(svc.notifications_in_progress.values()):
            print("NOTIF", n, n.t_to_go, time.time())

        # Now we want this contact to be really notify!
        # Ok, we define the downtime like we should, now look at if it does the job: do not
        # raise notif during a downtime for this contact
        time.sleep(1)
        self.scheduler_loop(3, [[svc, 2, 'CRITICAL']])
        self.assert_any_brok_match('SERVICE NOTIFICATION.*;CRITICAL')

        for n in list(svc.notifications_in_progress.values()):
            print("NOTIF", n, n.t_to_go, time.time(), time.time() - n.t_to_go)


    def test_contact_downtime_and_cancel(self):
        # schedule a 2-minute downtime
        # downtime must be active
        # consume a good result, sleep for a minute
        # downtime must be active
        # consume a bad result
        # downtime must be active
        # no notification must be found in broks

        host = self._sched.hosts.find_by_name("test_host_0")
        host.act_depend_of = []  # ignore the router

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        # Change the notif interval, so we can notify as soon as we want
        # Not 0 because it will disable the notifications
        svc.notification_interval = 0.001

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2018, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime

            now = time.time()
            duration = 600

            # downtime valid for the next 2 minutes
            test_contact = self._sched.contacts.find_by_name('test_contact')
            cmd = "[%lu] SCHEDULE_CONTACT_DOWNTIME;test_contact;%d;%d;me;blablabla" \
                  % (now, now, now + duration)
            self._sched.run_external_commands([cmd])

            # We loop, the downtime wil be check and activate
            self.scheduler_loop(1, [[svc, 0, 'OK'], [host, 0, 'UP']])

            self.assert_any_brok_match('CONTACT DOWNTIME ALERT.*;STARTED')

            print("downtime was scheduled. check its activity and the comment")
            assert len(test_contact.downtimes) == 1

            downtime = list(test_contact.downtimes.values())[0]
            assert downtime.is_in_effect
            assert not downtime.can_be_deleted

            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1))

            # Ok, we define the downtime like we should, now look at if it does the job: do not
            # raise notifications during a downtime for this contact
            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            frozen_datetime.tick(delta=datetime.timedelta(seconds=5))

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            frozen_datetime.tick(delta=datetime.timedelta(seconds=5))

            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            frozen_datetime.tick(delta=datetime.timedelta(seconds=5))

            # We should NOT see any service notification
            self.assert_no_brok_match('SERVICE NOTIFICATION.*;CRITICAL')

            # Time warp
            frozen_datetime.tick(delta=datetime.timedelta(minutes=1))

            downtime_id = list(test_contact.downtimes)[0]
            # OK, Now we cancel this downtime, we do not need it anymore
            cmd = "[%lu] DEL_CONTACT_DOWNTIME;%s" % (now, downtime_id)
            self._sched.run_external_commands([cmd])

            # We check if the downtime is tag as to remove
            assert downtime.can_be_deleted

            # We really delete it
            self.scheduler_loop(1, [])

            # So we should be out now, with a log
            self.assert_any_brok_match('CONTACT DOWNTIME ALERT.*;CANCELLED')

            print("Downtime was cancelled")
            assert len(test_contact.downtimes) == 0

            time.sleep(1)
            # Now we want this contact to be really notified
            self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            self.show_actions()
            # 2 because it is the second notification, the 1st one was hidden by the downtime !
            assert 2 == svc.current_notification_number, 'CRITICAL HARD, but no notifications !'

            # Time warp 5 minutes
            frozen_datetime.tick(delta=datetime.timedelta(minutes=5))

            # The service recovers
            self.scheduler_loop(1, [[svc, 0, 'OK']])
            # The notifications are created to be launched in the next second when they happen !
            # Time warp 1 second
            frozen_datetime.tick(delta=datetime.timedelta(seconds=1))
            self.scheduler_loop(1)
            assert 0 == svc.current_notification_number, 'Ok HARD, no notifications'

            self.assert_any_brok_match('SERVICE NOTIFICATION.*;OK')

            self.assert_any_brok_match('SERVICE NOTIFICATION.*;CRITICAL')
