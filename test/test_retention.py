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
from alignak_test import AlignakTest


class Testretention(AlignakTest):
    """
    This class test retention
    """

    def test_scheduler_get_retention(self):
        """ Test get data for retention save

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

        retention = self.schedulers['scheduler-master'].sched.get_retention_data()

        self.assertIn('hosts', retention)
        self.assertIn('services', retention)
        self.assertEqual(len(retention['hosts']), 2)
        self.assertEqual(len(retention['services']), 1)

    def test_scheduler_load_retention(self):
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

        retention = self.schedulers['scheduler-master'].sched.get_retention_data()

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 1, 'WARNING']])
        time.sleep(0.1)

        self.schedulers['scheduler-master'].sched.restore_retention_data(retention)

        self.assertEqual(host.last_state, 'DOWN')
        self.assertEqual(svc.last_state, 'CRITICAL')

        self.assertIsInstance(host.notified_contacts, set)
        self.assertIsInstance(svc.notified_contacts, set)
