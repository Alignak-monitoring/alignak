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
This file test the initial state of  hosts and services
"""

from alignak_test import AlignakTest


class TestInitialState(AlignakTest):
    """
    This class test the initial state of  hosts and services
    """

    def test_initial_state(self):
        """
        Test initial state of hosts and services

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_initial_state.cfg')

        host = self.schedulers[0].sched.hosts.find_by_name("test_is_0")
        self.assertEqual(host.state, 'UP')

        host = self.schedulers[0].sched.hosts.find_by_name("test_is_1")
        self.assertEqual(host.state, 'DOWN')

        host = self.schedulers[0].sched.hosts.find_by_name("test_is_2")
        self.assertEqual(host.state, 'UNREACHABLE')

        host = self.schedulers[0].sched.hosts.find_by_name("test_is_3")
        self.assertEqual(host.state, 'UP')

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_is_0",
                                                                              "test_is_0")
        self.assertEqual(svc.state, 'OK')

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_is_0",
                                                                              "test_is_1")
        self.assertEqual(svc.state, 'OK')

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_is_0",
                                                                              "test_is_2")
        self.assertEqual(svc.state, 'WARNING')

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_is_0",
                                                                              "test_is_3")
        self.assertEqual(svc.state, 'CRITICAL')

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_is_0",
                                                                              "test_is_4")
        self.assertEqual(svc.state, 'UNKNOWN')
