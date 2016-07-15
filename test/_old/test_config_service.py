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

""" This file is used to test variables of service config """

from alignak_test import *


class TestConfigService(AlignakTest):
    def setUp(self):
        self.setup_with_file(['etc/service_config_all.cfg'])

    def test_initial_state_warning(self):
        cg = self.sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_0')
        self.assertEqual('WARNING', cg.state)

    def test_initial_state_unknown(self):
        cg = self.sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_1')
        self.assertEqual('UNKNOWN', cg.state)

    def test_initial_state_critical(self):
        cg = self.sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_2')
        self.assertEqual('CRITICAL', cg.state)

    def test_initial_state_ok(self):
        cg = self.sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_3')
        self.assertEqual('OK', cg.state)

    def test_initial_state_notdefined(self):
        cg = self.sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_4')
        self.assertEqual('OK', cg.state)


if __name__ == '__main__':
    unittest.main()
