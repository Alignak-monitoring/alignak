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

from alignak.objects import Hostgroup
from alignak_test import AlignakTest


class TestHostGroup(AlignakTest):
    """
    This class tests the hostgroups
    """

    def test_hostgroup(self):
        """
        Default configuration has no loading problems ... as of it hostgroups are parsed correctly
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        self.assertTrue(self.schedulers[0].conf.conf_is_correct)

class TestHostGroupMembers(AlignakTest):
    """
    This class tests the hostgroups
    """

    def test_hostgroup_members(self):
        """
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/hostgroup/alignak_hostgroup_members.cfg')
        self.assertTrue(self.schedulers[0].conf.conf_is_correct)

        #  Found a hostgroup named allhosts_and_groups
        hg = self.schedulers[0].sched.hostgroups.find_by_name("allhosts_and_groups")
        self.assertIsInstance(hg, Hostgroup)
        self.assertEqual(hg.get_name(), "allhosts_and_groups")

        self.assertEqual(
            len(self.schedulers[0].sched.hostgroups.get_members_by_name("allhosts_and_groups")),
            2
        )

        self.assertEqual(len(hg.get_hostgroup_members()), 5)

        self.assertEqual(len(hg.get_hosts()), 2)


class TestHostGroupNoHost(AlignakTest):

    def test_hostgroup_with_no_host(self):
        """
        Allow hostgroups with no hosts
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/hostgroup/alignak_hostgroup_no_host.cfg')
        self.assertTrue(self.schedulers[0].conf.conf_is_correct)

        # Found a hostgroup named void
        hg = self.schedulers[0].sched.hostgroups.find_by_name("void")
        self.assertIsInstance(hg, Hostgroup)
        self.assertEqual(hg.get_name(), "void")

        self.assertEqual(
            len(self.schedulers[0].sched.hostgroups.get_members_by_name("void")),
            0
        )

        self.assertEqual(len(hg.get_hostgroup_members()), 0)

        self.assertEqual(len(hg.get_hosts()), 0)


class TestHostGroupWithSpace(AlignakTest):

    def test_hostgroup_with_space(self):
        """
        Test that hostgroups can have a name with spaces
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        self.assertTrue(self.schedulers[0].conf.conf_is_correct)
        self.nb_hostgroups = len(self.schedulers[0].sched.hostgroups)

        self.setup_with_file('cfg/hostgroup/alignak_hostgroup_with_space.cfg')
        self.assertTrue(self.schedulers[0].conf.conf_is_correct)

        # Two more groups than the default configuration
        self.assertEqual(
            len(self.schedulers[0].sched.hostgroups), self.nb_hostgroups + 2
        )

        self.assertEqual(
            self.schedulers[0].sched.hostgroups.find_by_name("test_With Spaces").get_name(),
            "test_With Spaces"
        )
        self.assertIsNot(
            self.schedulers[0].sched.hostgroups.get_members_by_name(
                "test_With Spaces"
            ),
            []
        )

        self.assertEqual(
            self.schedulers[0].sched.hostgroups.find_by_name("test_With another Spaces").get_name(),
            "test_With another Spaces"
        )
        self.assertIsNot(
            self.schedulers[0].sched.hostgroups.get_members_by_name(
                "test_With another Spaces"
            ),
            []
        )
