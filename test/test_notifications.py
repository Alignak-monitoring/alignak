#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2015: Alignak team, see AUTHORS.txt file for contributors
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
from alignak_test import AlignakTest


class TestNotifications(AlignakTest):
    """
    This class test notifications
    """

    def test_0_nonotif(self):
        """
        Test with notifications disabled in service definition

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_nonotif.cfg')

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("SOFT", svc.state_type)
        self.assertEqual(0, svc.current_notification_number, 'Critical SOFT, no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual(0, svc.current_notification_number, 'Critical HARD, no notifications')
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'VOID', 'command')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'Ok HARD, no notifications')
        self.assert_actions_count(0)

    def test_1_nonotif_enablewithcmd(self):
        """
        Test notification disabled in service definition but enable after with external command

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_nonotif.cfg')

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("SOFT", svc.state_type)
        self.assertEqual(0, svc.current_notification_number, 'Critical SOFT, no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual(0, svc.current_notification_number, 'Critical HARD, no notifications')
        self.assert_actions_count(1)

        now = int(time.time())
        cmd = "[{0}] ENABLE_SVC_NOTIFICATIONS;{1};{2}\n".format(now, svc.host_name,
                                                                svc.service_description)
        self.schedulers[0].sched.run_external_command(cmd)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual(1, svc.current_notification_number, 'Critical HARD, must have 1 '
                                                             'notification')
        self.assert_actions_count(2)
        self.assert_actions_match(0, 'VOID', 'command')
        self.assert_actions_match(1, 'serviceoutput CRITICAL', 'command')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'Ok HARD, no notifications')
        self.assert_actions_count(2)
        self.assert_actions_match(0, 'serviceoutput CRITICAL', 'command')
        self.assert_actions_match(1, 'serviceoutput OK', 'command')

    def test_2_notifications(self):
        """
        Test notifications sent in normal mode

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("SOFT", svc.state_type)
        self.assertEqual(0, svc.current_notification_number, 'Critical SOFT, no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual(1, svc.current_notification_number, 'Critical HARD, must have 1 '
                                                             'notification')
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual(svc.current_notification_number, 2)
        self.assert_actions_count(3)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual(svc.current_notification_number, 3)
        self.assert_actions_count(4)

        now = time.time()
        cmd = "[%lu] DISABLE_CONTACT_SVC_NOTIFICATIONS;test_contact" % now
        self.schedulers[0].sched.run_external_command(cmd)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual(svc.current_notification_number, 3)
        self.assert_actions_count(4)

        now = time.time()
        cmd = "[%lu] ENABLE_CONTACT_SVC_NOTIFICATIONS;test_contact" % now
        self.schedulers[0].sched.run_external_command(cmd)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual(svc.current_notification_number, 4)
        self.assert_actions_count(5)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number)
        self.assert_actions_count(5)

    def test_3_notifications(self):
        """
        Test notifications of service states OK -> WARNING -> CRITICAL -> OK

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual("SOFT", svc.state_type)
        self.assertEqual(0, svc.current_notification_number, 'Warning SOFT, no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual(1, svc.current_notification_number, 'Warning HARD, must have 1 '
                                                             'notification')
        self.assert_actions_count(2)
        self.assert_actions_match(1, 'serviceoutput WARNING', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual(2, svc.current_notification_number, 'Critical HARD,  must have 2 '
                                                             'notification')
        self.assert_actions_count(3)
        self.assert_actions_match(0, 'serviceoutput WARNING', 'command')
        self.assert_actions_match(2, 'serviceoutput CRITICAL', 'command')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number)
        self.assert_actions_count(3)
        self.assert_actions_match(2, 'serviceoutput OK', 'command')

    def test_4_notifications(self):
        """
        Test notifications of service states OK -> CRITICAL -> WARNING -> OK

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("SOFT", svc.state_type)
        self.assertEqual(0, svc.current_notification_number, 'Critical SOFT, no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual(1, svc.current_notification_number, 'Caritical HARD, must have 1 '
                                                             'notification')
        self.assert_actions_count(2)
        self.assert_actions_match(1, 'serviceoutput CRITICAL', 'command')

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual(2, svc.current_notification_number, 'Warning HARD,  must have 2 '
                                                             'notification')
        self.assert_actions_count(3)
        self.assert_actions_match(0, 'serviceoutput CRITICAL', 'command')
        self.assert_actions_match(2, 'serviceoutput WARNING', 'command')

    def test_notifications_with_delay(self):
        """
        Test notifications with use property first_notification_delay

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.notification_interval = 0.001  # and send immediately then
        svc.first_notification_delay = 0.1  # set 6s for first notification delay
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no host_checks on critical check_results
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        self.assert_actions_count(0)
        time.sleep(0.1)
        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        self.assertEqual("HARD", svc.state_type)
        self.assert_actions_count(1)
        time.sleep(7)
        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        self.assert_actions_count(2)
        self.assert_actions_match(1, 'serviceoutput WARNING', 'command')
        self.assertEqual(svc.last_time_critical, 0)
        self.assertEqual(svc.last_time_unknown, 0)
        self.assertGreater(svc.last_time_warning, 0)
        self.assertGreater(svc.last_time_ok, 0)

        time.sleep(2)
        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        self.assert_actions_count(3)
        self.assert_actions_match(2, 'serviceoutput WARNING', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        self.assertEqual(3, svc.current_notification_number)
        self.assert_actions_count(4)
        self.assertEqual(svc.last_time_unknown, 0)
        self.assertGreater(svc.last_time_warning, 0)
        self.assertGreater(svc.last_time_critical, 0)
        self.assertGreater(svc.last_time_ok, 0)
        time.sleep(7)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        self.assertEqual(4, svc.current_notification_number)
        self.assert_actions_count(5)
        self.assert_actions_match(4, 'serviceoutput CRITICAL', 'command')
        self.assertEqual(5, len(svc.notifications_in_progress))

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(7)
        self.scheduler_loop(1, [[svc, 0, 'OK']])
        self.assertEqual(0, svc.current_notification_number)
        self.assert_actions_count(5)

    def test_notifications_delay_recover_before_notif(self):
        """
        TODO

        :return:
        """
        pass

    def test_notifications_outside_period(self):
        """
        Test the case we are not in notification_period, so not send notifications

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False
        timeperiod = self.schedulers[0].sched.timeperiods.find_by_name('none')
        svc.notification_period = timeperiod.uuid

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("SOFT", svc.state_type)
        self.assertEqual(0, svc.current_notification_number, 'Critical SOFT, no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual(0, svc.current_notification_number, 'Critical HARD, no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number)
        self.assert_actions_count(0)

    def test_notifications_ack(self):
        """
        Test notifications not send when add an acknowledge

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("SOFT", svc.state_type)
        self.assertEqual(0, svc.current_notification_number, 'Critical SOFT, no notifications')
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual(1, svc.current_notification_number, 'Critical HARD, must have 1 '
                                                             'notification')
        self.assert_actions_count(2)

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n".\
            format(now, svc.host_name, svc.service_description, 1, 0, 1, 'darth vader',
                   'normal process')
        self.schedulers[0].sched.run_external_command(cmd)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual(1, svc.current_notification_number, 'Critical HARD, must have 1 '
                                                             'notification')
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual(1, svc.current_notification_number, 'Critical HARD, must have 1 '
                                                             'notification')
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual(2, svc.current_notification_number, 'Warning HARD, must have 2 '
                                                             'notifications')
        self.assert_actions_count(3)

    def test_notifications_downtime(self):
        """
        Test notifications not send when add a downtime

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number, 'All OK no notifications')
        self.assert_actions_count(0)

        now = time.time()
        cmd = "[{0}] SCHEDULE_SVC_DOWNTIME;{1};{2};{3};{4};{5};{6};{7};{8};{9}\n".\
            format(now, svc.host_name, svc.service_description, now, (now + 1000), 1, 0, 0,
                   'darth vader', 'add downtime for maintenance')
        self.schedulers[0].sched.run_external_command(cmd)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("SOFT", svc.state_type)
        self.assertEqual(0, svc.current_notification_number, 'Critical SOFT, no notifications')
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'serviceoutput CRITICAL', 'command')
        self.assert_actions_match(0, 'notificationtype DOWNTIMESTART', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assertEqual("HARD", svc.state_type)
        self.assertEqual(0, svc.current_notification_number, 'Critical HARD, no notifications')
        self.assert_actions_count(2)
        self.assert_actions_match(1, 'VOID', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        self.assertEqual(0, svc.current_notification_number)
        self.assert_actions_count(1)
        self.assert_actions_match(0, 'serviceoutput CRITICAL', 'command')
        self.assert_actions_match(0, 'notificationtype DOWNTIMESTART', 'command')
