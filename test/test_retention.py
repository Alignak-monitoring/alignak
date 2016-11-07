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
This file test retention
"""

import time
import json
from alignak_test import AlignakTest


class Testretention(AlignakTest):
    """
    This class test retention
    """

    def test_scheduler_retention(self):
        """ Test restore retention data

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

        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        now = time.time()
        # downtime host
        excmd = '[%d] SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;1200;test_contact;My downtime' \
                % (now, now + 120, now + 1200)
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()

        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;' \
                'Acknowledge service' % time.time()
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(True, svc.problem_has_been_acknowledged)

        comments = []
        for comm_uuid, comment in self.schedulers['scheduler-master'].sched.comments.iteritems():
            comments.append(comment.comment)

        retention = self.schedulers['scheduler-master'].sched.get_retention_data()

        self.assertIn('hosts', retention)
        self.assertIn('services', retention)
        self.assertEqual(len(retention['hosts']), 2)
        self.assertEqual(len(retention['services']), 1)

        # Test if can json.dumps (serialize)
        for hst in retention['hosts']:
            try:
                t = json.dumps(retention['hosts'][hst])
            except Exception as err:
                self.assertTrue(False, 'Json dumps impossible: %s' % str(err))
        for service in retention['services']:
            try:
                t = json.dumps(retention['services'][service])
            except Exception as err:
                self.assertTrue(False, 'Json dumps impossible: %s' % str(err))

        # Test after get retention not have broken something
        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        # ************** test the restoration of retention ************** #
        # new conf
        self.setup_with_file('cfg/cfg_default.cfg')
        hostn = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        hostn.checks_in_progress = []
        hostn.act_depend_of = []  # ignore the router
        hostn.event_handler_enabled = False

        svcn = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svcn.notification_interval = 0.001
        svcn.checks_in_progress = []
        svcn.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[hostn, 0, 'UP'], [svcn, 1, 'WARNING']])
        time.sleep(0.1)
        self.assertEqual(0, len(self.schedulers['scheduler-master'].sched.comments))
        self.assertEqual(0, len(hostn.notifications_in_progress))

        self.schedulers['scheduler-master'].sched.restore_retention_data(retention)

        self.assertEqual(hostn.last_state, 'DOWN')
        self.assertEqual(svcn.last_state, 'CRITICAL')

        self.assertNotEqual(host.uuid, hostn.uuid)

        # check downtime
        self.assertEqual(host.downtimes, hostn.downtimes)
        for down_uuid, downtime in self.schedulers['scheduler-master'].sched.downtimes.iteritems():
            self.assertEqual('My downtime', downtime.comment)

        # check notifications
        self.assertEqual(2, len(hostn.notifications_in_progress))
        for notif_uuid, notification in hostn.notifications_in_progress.iteritems():
            self.assertEqual(host.notifications_in_progress[notif_uuid].command,
                             notification.command)
            self.assertEqual(host.notifications_in_progress[notif_uuid].t_to_go,
                             notification.t_to_go)

        # check comments
        self.assertEqual(2, len(self.schedulers['scheduler-master'].sched.comments))
        commentsn = []
        for comm_uuid, comment in self.schedulers['scheduler-master'].sched.comments.iteritems():
            commentsn.append(comment.comment)
        self.assertEqual(comments, commentsn)

        # check notified_contacts
        self.assertIsInstance(hostn.notified_contacts, set)
        self.assertIsInstance(svcn.notified_contacts, set)
        self.assertEqual(set([self.schedulers['scheduler-master'].sched.contacts.find_by_name("test_contact")]),
                         hostn.notified_contacts)

        # acknowledge
        self.assertEqual(True, svcn.problem_has_been_acknowledged)

