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
        """ Test with notifications disabled in service definition

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_nonotif.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
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

    def test_1_nonotif_enablewithcmd(self):
        """ Test notification disabled in service definition but enable after with external command

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_nonotif.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.1
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

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
        assert not svc.notifications_enabled

        now = int(time.time())
        cmd = "[{0}] ENABLE_SVC_NOTIFICATIONS;{1};{2}\n".format(now, svc.host_name,
                                                                svc.service_description)
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.external_command_loop()
        assert svc.notifications_enabled
        assert "HARD" == svc.state_type
        assert "CRITICAL" == svc.state
        time.sleep(0.2)
        self.scheduler_loop(2, [[svc, 2, 'CRITICAL']])
        assert "HARD" == svc.state_type
        assert "CRITICAL" == svc.state
        assert 1 == svc.current_notification_number, 'Critical HARD, must have 1 ' \
                                                             'notification'
        self.assert_actions_count(2)
        self.assert_actions_match(0, 'VOID', 'command')
        self.assert_actions_match(1, 'serviceoutput CRITICAL', 'command')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert 0 == svc.current_notification_number, 'Ok HARD, no notifications'
        self.assert_actions_count(2)
        self.assert_actions_match(0, 'serviceoutput CRITICAL', 'command')
        self.assert_actions_match(1, 'serviceoutput OK', 'command')

        self.assert_actions_count(2)
        self.assert_actions_match(0, 'serviceoutput CRITICAL', 'command')
        self.assert_actions_match(1, 'serviceoutput OK', 'command')

    def test_2_notifications(self):
        """ Test notifications sent in normal mode

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.01 # so it's 0.6 second
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.7)
        assert svc.current_notification_number == 0, 'All OK no notifications'
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.7)
        assert "SOFT" == svc.state_type
        assert svc.current_notification_number == 0, 'Critical SOFT, no notifications'
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.7)
        assert "HARD" == svc.state_type
        self.assert_actions_count(2)
        assert svc.current_notification_number == 1, 'Critical HARD, must have 1 ' \
                                                     'notification'

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.7)
        self.assert_actions_count(3)
        assert svc.current_notification_number == 2

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.7)
        self.assert_actions_count(4)
        assert svc.current_notification_number == 3

        now = time.time()
        cmd = "[%lu] DISABLE_CONTACT_SVC_NOTIFICATIONS;test_contact" % now
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.7)
        self.assert_actions_count(4)
        assert svc.current_notification_number == 3

        now = time.time()
        cmd = "[%lu] ENABLE_CONTACT_SVC_NOTIFICATIONS;test_contact" % now
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.7)
        self.assert_actions_count(5)
        assert svc.current_notification_number == 4

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.7)
        assert 0 == svc.current_notification_number
        self.assert_actions_count(6)

    def test_3_notifications(self):
        """ Test notifications of service states OK -> WARNING -> CRITICAL -> OK

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        time.sleep(0.1)
        assert 0 == svc.current_notification_number, 'All OK no notifications'
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "SOFT" == svc.state_type
        assert 0 == svc.current_notification_number, 'Warning SOFT, no notifications'
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        assert "HARD" == svc.state_type
        assert 1 == svc.current_notification_number, 'Warning HARD, must have 1 ' \
                                                             'notification'
        self.assert_actions_count(2)
        self.assert_actions_match(1, 'serviceoutput WARNING', 'command')

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        assert "HARD" == svc.state_type
        assert 2 == svc.current_notification_number, 'Critical HARD,  must have 2 ' \
                                                             'notification'
        self.assert_actions_count(3)
        self.assert_actions_match(0, 'serviceoutput WARNING', 'command')
        self.assert_actions_match(2, 'serviceoutput CRITICAL', 'command')

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert 0 == svc.current_notification_number
        self.assert_actions_count(3)
        self.assert_actions_match(2, 'serviceoutput OK', 'command')

    def test_4_notifications(self):
        """ Test notifications of service states OK -> CRITICAL -> WARNING -> OK

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

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
        assert 1 == svc.current_notification_number, 'Caritical HARD, must have 1 ' \
                                                             'notification'
        self.assert_actions_count(2)
        self.assert_actions_match(1, 'serviceoutput CRITICAL', 'command')

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        assert 3 == svc.current_notification_number, 'Warning HARD,  must have 3 ' \
                                                             'notification'
        self.assert_actions_count(4)
        self.assert_actions_match(0, 'serviceoutput CRITICAL', 'command')
        self.assert_actions_match(1, 'serviceoutput CRITICAL', 'command')
        self.assert_actions_match(2, 'VOID', 'command')
        self.assert_actions_match(3, 'serviceoutput WARNING', 'command')

    def test_notifications_with_delay(self):
        """ Test notifications with use property first_notification_delay

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        svc.notification_interval = 0.001  # and send immediately then
        svc.first_notification_delay = 0.1  # set 6s for first notification delay
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
        self.assert_actions_count(2)
        self.assert_actions_match(1, 'serviceoutput WARNING', 'command')
        assert svc.last_time_critical == 0
        assert svc.last_time_unknown == 0
        assert svc.last_time_warning > 0
        assert svc.last_time_ok > 0

        time.sleep(2)
        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        self.assert_actions_count(3)
        self.assert_actions_match(2, 'serviceoutput WARNING', 'command')

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
        self.assert_actions_count(5)
        self.assert_actions_match(4, 'serviceoutput CRITICAL', 'command')
        assert 5 == len(svc.notifications_in_progress)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(7)
        self.scheduler_loop(1, [[svc, 0, 'OK']])
        assert 0 == svc.current_notification_number
        self.assert_actions_count(5)

    def test_notifications_delay_recover_before_notif(self):
        """
        TODO: @ddurieux ?

        :return:
        """
        pass

    def test_notifications_outside_period(self):
        """ Test when we are not in notification_period, so do not send notifications

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False
        timeperiod = self.schedulers['scheduler-master'].sched.timeperiods.find_by_name('none')
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
        self.assert_actions_count(0)

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        time.sleep(0.1)
        assert 0 == svc.current_notification_number
        self.assert_actions_count(0)

    def test_notifications_ack(self):
        """ Test notifications not sent when an acknowledge is set

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

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
        assert 1 == svc.current_notification_number, 'Critical HARD, must have 1 ' \
                                                             'notification'
        self.show_actions()
        self.assert_actions_count(2)

        now = int(time.time())
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n".\
            format(now, svc.host_name, svc.service_description, 1, 0, 1, 'darth vader',
                   'normal process')
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        assert 1 == svc.current_notification_number, 'Critical HARD, must have 1 ' \
                                                             'notification'
        self.show_actions()
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        assert 1 == svc.current_notification_number, 'Critical HARD, must have 1 ' \
                                                             'notification'
        self.assert_actions_count(2)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        time.sleep(0.1)
        assert "HARD" == svc.state_type
        assert 2 == svc.current_notification_number, 'Warning HARD, must have 2 ' \
                                                             'notifications'
        self.assert_actions_count(3)

    def test_notifications_downtime(self):
        """ Test notifications not sent when a downtime is scheduled

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
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
        self.schedulers['scheduler-master'].sched.run_external_command(cmd)
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
