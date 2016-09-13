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
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Grégory Starck, g.starck@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Jean Gabes, naparuba@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr

#  This file is part of Shinken.
#
#  Shinken is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Shinken is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Shinken.  If not, see <http://www.gnu.org/licenses/>.

"""
This file is used to test realms usage
"""
import time
from alignak_test import AlignakTest


class TestRealms(AlignakTest):
    """
    This class test realms usage
    """

    def test_realm_host_assignation(self):
        """
        Test realms on each host

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_realms.cfg')

        for scheduler in self.schedulers:
            if scheduler.sched.instance_name == 'blabla1':
                sched_realm1 = scheduler.sched
            elif scheduler.sched.instance_name == 'blabla2':
                sched_realm2 = scheduler.sched
        realm1 = self.arbiter.conf.realms.find_by_name('realm1')
        self.assertIsNotNone(realm1)
        realm2 = self.arbiter.conf.realms.find_by_name('realm2')
        self.assertIsNotNone(realm2)

        print(sched_realm1.hosts)
        print(sched_realm2.hosts)

        test_host_realm1 = sched_realm1.hosts.find_by_name("test_host_realm1")
        self.assertIsNotNone(test_host_realm1)
        self.assertEqual(realm1.uuid, test_host_realm1.realm)
        test_host_realm2 = sched_realm1.hosts.find_by_name("test_host_realm2")
        self.assertIsNone(test_host_realm2)

        test_host_realm2 = sched_realm2.hosts.find_by_name("test_host_realm2")
        self.assertIsNotNone(test_host_realm2)
        self.assertEqual(realm2.uuid, test_host_realm2.realm)
        test_host_realm1 = sched_realm2.hosts.find_by_name("test_host_realm1")
        self.assertIsNone(test_host_realm1)

    def test_realm_hostgroup_assignation(self):
        """
        Check realm and hostgroup

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_realms.cfg')

        in_realm2 = self.schedulers[0].sched.hostgroups.find_by_name('in_realm2')
        realm1 = self.arbiter.conf.realms.find_by_name('realm1')
        self.assertIsNotNone(realm1)
        realm2 = self.arbiter.conf.realms.find_by_name('realm2')
        self.assertIsNotNone(realm2)

        for scheduler in self.schedulers:
            if scheduler.sched.instance_name == 'blabla1':
                sched_realm1 = scheduler.sched
            elif scheduler.sched.instance_name == 'blabla2':
                sched_realm2 = scheduler.sched

        # 1 and 2 are link to realm2 because they are in the hostgroup in_realm2
        test_host1_hg_realm2 = sched_realm2.hosts.find_by_name("test_host1_hg_realm2")
        self.assertIsNotNone(test_host1_hg_realm2)
        self.assertEqual(realm2.uuid, test_host1_hg_realm2.realm)
        self.assertIn(in_realm2.get_name(), [sched_realm2.hostgroups[hg].get_name() for hg in test_host1_hg_realm2.hostgroups])

        test_host2_hg_realm2 = sched_realm2.hosts.find_by_name("test_host2_hg_realm2")
        self.assertIsNotNone(test_host2_hg_realm2)
        self.assertEqual(realm2.uuid, test_host2_hg_realm2.realm)
        self.assertIn(in_realm2.get_name(), [sched_realm2.hostgroups[hg].get_name() for hg in test_host2_hg_realm2.hostgroups])

        test_host3_hg_realm2 = sched_realm2.hosts.find_by_name("test_host3_hg_realm2")
        self.assertIsNone(test_host3_hg_realm2)
        test_host3_hg_realm2 = sched_realm1.hosts.find_by_name("test_host3_hg_realm2")
        self.assertIsNotNone(test_host3_hg_realm2)
        self.assertEqual(realm1.uuid, test_host3_hg_realm2.realm)
        self.assertIn(in_realm2.get_name(), [sched_realm2.hostgroups[hg].get_name() for hg in test_host3_hg_realm2.hostgroups])

        hostgroup_realm2 = sched_realm1.hostgroups.find_by_name("in_realm2")
        self.assertIsNotNone(hostgroup_realm2)
        hostgroup_realm2 = sched_realm2.hostgroups.find_by_name("in_realm2")
        self.assertIsNotNone(hostgroup_realm2)
        # TODO catch the warning in log when parse configuration

    def test_sub_realms_assignations(self):
        """
        Test realm / sub-realm for broker

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_realms_sub.cfg')

        world = self.arbiter.conf.realms.find_by_name('World')
        self.assertIsNot(world, None)
        europe = self.arbiter.conf.realms.find_by_name('Europe')
        self.assertIsNot(europe, None)
        paris = self.arbiter.conf.realms.find_by_name('Paris')
        self.assertIsNot(paris, None)
        # Get the broker in the realm level
        bworld = self.arbiter.conf.brokers.find_by_name('B-world')
        self.assertIsNot(bworld, None)

        # broker should be in the world level
        self.assertIs(bworld.uuid in world.potential_brokers, True)
        # in europe too
        self.assertIs(bworld.uuid in europe.potential_brokers, True)
        # and in paris too
        self.assertIs(bworld.uuid in paris.potential_brokers, True)
