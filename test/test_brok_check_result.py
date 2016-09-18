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
This file test the check_result brok
"""

import time
from alignak_test import AlignakTest
from alignak.misc.serialization import unserialize


class TestBrokCheckResult(AlignakTest):
    """
    This class test the check_result brok
    """

    def test_conf_dependencies(self):
        """
        Test dependencies right loaded from config files

        :return: None
        """
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

        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 0, 'OK']])
        time.sleep(0.1)
        host_check_results = []
        service_check_results = []
        for brok in self.schedulers[0].sched.broks.itervalues():
            if brok.type == 'host_check_result':
                host_check_results.append(brok)
            elif brok.type == 'service_check_result':
                service_check_results.append(brok)

        self.assertEqual(len(host_check_results), 1)
        self.assertEqual(len(service_check_results), 1)

        hdata = unserialize(host_check_results[0].data)
        self.assertEqual(hdata['state'], 'DOWN')
        self.assertEqual(hdata['state_type'], 'SOFT')

        sdata = unserialize(service_check_results[0].data)
        self.assertEqual(sdata['state'], 'OK')
        self.assertEqual(sdata['state_type'], 'HARD')
