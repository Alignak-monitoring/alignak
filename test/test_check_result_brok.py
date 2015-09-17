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


from alignak_test import *


class Test_CheckResult_Brok(AlignakTest):

    cfg_file = 'etc/alignak_1r_1h_1s.cfg'

    expected_host_command_name = 'check-host-alive-parent'
    expected_svc_command_name = 'check_service'

    def setUp(self):
        self.setup_with_file([self.cfg_file])

    def test_host_check_result_brok_has_command_name(self):
        host = self.sched.hosts.find_by_name('test_host_0')
        res = {}
        host.fill_data_brok_from(res, 'check_result')
        self.assertIn('command_name', res)
        self.assertEqual(self.expected_host_command_name, res['command_name'])

    def test_service_check_result_brok_has_command_name(self):
        svc = self.sched.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_ok_0')
        res = {}
        svc.fill_data_brok_from(res, 'check_result')
        self.assertIn('command_name', res)
        self.assertEqual(self.expected_svc_command_name, res['command_name'])


class Test_CheckResult_Brok_Host_No_command(Test_CheckResult_Brok):

    cfg_file = 'etc/alignak_host_without_cmd.cfg'

    expected_host_command_name = "_internal_host_up"

if __name__ == "__main__":
    unittest.main()