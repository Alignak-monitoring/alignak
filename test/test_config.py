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
#

"""
This file test all cases of eventhandler
"""

import time

from alignak_test import AlignakTest


class TestConfig(AlignakTest):
    """
    This class tests the configuration
    """

    def test_config_ok(self):
        """
        Default configuration has no loading problems ...
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        self.assertTrue(self.schedulers[0].conf.conf_is_correct)
        self.assertTrue(self.conf_is_correct)
        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_config_ko_1(self):
        """
        Configuration is not correct because of a wrong relative path in the main config file
        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/config/alignak_broken_1.cfg')
        self.assertFalse(self.conf_is_correct)
        self.show_configuration_logs()

    def test_config_hosts(self):
        """
        Test hosts initial states
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/host_config_all.cfg')

        cg = self.schedulers[0].sched.hosts.find_by_name('test_host_0')
        self.assertEqual('DOWN', cg.state)

        cg = self.schedulers[0].sched.hosts.find_by_name('test_host_1')
        self.assertEqual('UNREACHABLE', cg.state)

        cg = self.schedulers[0].sched.hosts.find_by_name('test_host_2')
        self.assertEqual('UP', cg.state)

        cg = self.schedulers[0].sched.hosts.find_by_name('test_host_3')
        self.assertEqual('UP', cg.state)

    def test_config_services(self):
        """
        Test services initial states
        :return: None
        """

        self.print_header()
        self.setup_with_file('cfg/config/service_config_all.cfg')

        cg = self.schedulers[0].sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_0')
        self.assertEqual('WARNING', cg.state)

        cg = self.schedulers[0].sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_1')
        self.assertEqual('UNKNOWN', cg.state)

        cg = self.schedulers[0].sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_2')
        self.assertEqual('CRITICAL', cg.state)

        cg = self.schedulers[0].sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_3')
        self.assertEqual('OK', cg.state)

        cg = self.schedulers[0].sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_4')
        self.assertEqual('OK', cg.state)

