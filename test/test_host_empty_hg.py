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


from alignak_test import *


class TestHostEmptyHg(AlignakTest):

    def setUp(self):
        self.setup_with_file('etc/alignak_host_empty_hg.cfg')


    def test_host_empty_hg(self):
        self.assertTrue(self.sched.conf.is_correct)
        host = self.sched.hosts.find_by_name("test_host_empty_hg")
        self.assertEqual(host.hostgroups, [])

if __name__ == '__main__':
    unittest.main()