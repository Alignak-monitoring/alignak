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

""" This file is used to test variables of host config """

from alignak_test import *


class TestConfigHost(AlignakTest):
    def setUp(self):
        self.setup_with_file(['etc/host_config_all.cfg'])

    def test_initial_state_down(self):
        cg = self.sched.hosts.find_by_name('test_host_0')
        self.assertEqual('DOWN', cg.state)

    def test_initial_state_unreachable(self):
        cg = self.sched.hosts.find_by_name('test_host_1')
        self.assertEqual('UNREACHABLE', cg.state)

    def test_initial_state_ok(self):
        cg = self.sched.hosts.find_by_name('test_host_2')
        self.assertEqual('UP', cg.state)

    def test_initial_state_nodefined(self):
        cg = self.sched.hosts.find_by_name('test_host_3')
        self.assertEqual('UP', cg.state)


if __name__ == '__main__':
    unittest.main()
