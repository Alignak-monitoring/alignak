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

from alignak.objects import Service
from alignak.objects import Servicegroup
from alignak_test import AlignakTest


class TestServiceGroup(AlignakTest):
    """
    This class tests the servicegroups
    """

    def test_servicegroup(self):
        """
        Default configuration has no loading problems ... as of it servicegroups are parsed
        correctly
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        self.assertTrue(self.schedulers['scheduler-master'].conf.conf_is_correct)

    def test_look_for_alias(self):
        """
        Default configuration has no loading problems ... as of it servicegroups are parsed correctly
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/servicegroup/alignak_groups_with_no_alias.cfg')
        self.assertTrue(self.schedulers['Default-Scheduler'].conf.conf_is_correct)

        #  Found a servicegroup named NOALIAS
        sg = self.schedulers['Default-Scheduler'].sched.servicegroups.find_by_name("NOALIAS")
        self.assertIsInstance(sg, Servicegroup)
        self.assertEqual(sg.get_name(), "NOALIAS")
        self.assertEqual(sg.alias, "NOALIAS")

    def test_servicegroup_members(self):
        """
        Test if members are linked from group

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/servicegroup/alignak_servicegroup_members.cfg')
        self.assertTrue(self.schedulers['scheduler-master'].conf.conf_is_correct)

        #  Found a servicegroup named allhosts_and_groups
        sg = self.schedulers['scheduler-master'].sched.servicegroups.find_by_name("allservices_and_groups")
        self.assertIsInstance(sg, Servicegroup)
        self.assertEqual(sg.get_name(), "allservices_and_groups")

        self.assertEqual(
            len(self.schedulers['scheduler-master'].sched.servicegroups.get_members_by_name("allservices_and_groups")),
            1
        )

        self.assertEqual(len(sg.get_services()), 1)

        self.assertEqual(len(sg.get_servicegroup_members()), 4)

    def test_members_servicegroup(self):
        """
        Test if group is linked from the member
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/servicegroup/alignak_servicegroup_members.cfg')
        self.assertTrue(self.schedulers['scheduler-master'].conf.conf_is_correct)

        #  Found a servicegroup named allhosts_and_groups
        sg = self.schedulers['scheduler-master'].sched.servicegroups.find_by_name("allservices_and_groups")
        self.assertIsInstance(sg, Servicegroup)
        self.assertEqual(sg.get_name(), "allservices_and_groups")

        self.assertEqual(
            len(self.schedulers['scheduler-master'].sched.servicegroups.get_members_by_name(
                "allservices_and_groups"
            )),
            1
        )

        self.assertEqual(len(sg.get_services()), 1)
        print("List servicegroup services:")
        for service_id in sg.members:
            service = self.schedulers['scheduler-master'].sched.services[service_id]
            print("Service: %s" % service)
            self.assertIsInstance(service, Service)

            if service.get_name() == 'test_ok_0':
                self.assertEqual(len(service.get_servicegroups()), 4)
                for group_id in service.servicegroups:
                    group = self.schedulers['scheduler-master'].sched.servicegroups[group_id]
                    print("Group: %s" % group)
                    self.assertIn(group.get_name(), [
                        'ok', 'servicegroup_01', 'servicegroup_02', 'allservices_and_groups'
                    ])

        self.assertEqual(len(sg.get_servicegroup_members()), 4)
        print("List servicegroup groups:")
        for group in sg.get_servicegroup_members():
            print("Group: %s" % group)
            self.assertIn(group, [
                'servicegroup_01', 'servicegroup_02', 'servicegroup_03', 'servicegroup_04'
            ])

    def test_servicegroup_with_no_service(self):
        """
        Allow servicegroups with no hosts
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/servicegroup/alignak_servicegroup_no_service.cfg')
        self.assertTrue(self.schedulers['scheduler-master'].conf.conf_is_correct)

        # Found a servicegroup named void
        sg = self.schedulers['scheduler-master'].sched.servicegroups.find_by_name("void")
        self.assertIsInstance(sg, Servicegroup)
        self.assertEqual(sg.get_name(), "void")

        self.assertEqual(
            len(self.schedulers['scheduler-master'].sched.servicegroups.get_members_by_name("void")),
            0
        )

        print("Services: %s" % sg.get_servicegroup_members())
        self.assertEqual(len(sg.get_servicegroup_members()), 0)

        print("Services: %s" % sg.get_services())
        self.assertEqual(len(sg.get_services()), 0)

    def test_servicegroup_with_space(self):
        """
        Test that servicegroups can have a name with spaces
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        self.assertTrue(self.schedulers['scheduler-master'].conf.conf_is_correct)
        self.nb_servicegroups = len(self.schedulers['scheduler-master'].sched.servicegroups)

        self.setup_with_file('cfg/servicegroup/alignak_servicegroup_with_space.cfg')
        self.assertTrue(self.schedulers['scheduler-master'].conf.conf_is_correct)

        # Two more groups than the default configuration
        self.assertEqual(
            len(self.schedulers['scheduler-master'].sched.servicegroups), self.nb_servicegroups + 2
        )

        self.assertEqual(
            self.schedulers['scheduler-master'].sched.servicegroups.find_by_name("test_With Spaces").get_name(),
            "test_With Spaces"
        )
        self.assertIsNot(
            self.schedulers['scheduler-master'].sched.servicegroups.get_members_by_name(
                "test_With Spaces"
            ),
            []
        )

        self.assertEqual(
            self.schedulers['scheduler-master'].sched.servicegroups.find_by_name("test_With another Spaces").get_name(),
            "test_With another Spaces"
        )
        self.assertIsNot(
            self.schedulers['scheduler-master'].sched.servicegroups.get_members_by_name(
                "test_With another Spaces"
            ),
            []
        )

    def test_servicegroups_generated(self):
        """
        Test that servicegroups can have a name with spaces
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/servicegroup/alignak_servicegroups_generated.cfg')
        self.assertTrue(self.schedulers['scheduler-master'].conf.conf_is_correct)
        self.nb_servicegroups = len(self.schedulers['scheduler-master'].sched.servicegroups)

        sgs = []
        for name in ["MYSVCGP", "MYSVCGP2", "MYSVCGP3", "MYSVCGP4"]:
            sg = self.schedulers['scheduler-master'].sched.servicegroups.find_by_name(name)
            self.assertIsNot(sg, None)
            sgs.append(sg)

        svc3 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("fake host", "fake svc3")
        svc4 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname("fake host", "fake svc4")
        self.assertIn(svc3.uuid, sgs[0].members)
        self.assertIn(svc3.uuid, sgs[1].members)
        self.assertIn(svc4.uuid, sgs[2].members)
        self.assertIn(svc4.uuid, sgs[3].members)

        self.assertIn(sgs[0].uuid, svc3.servicegroups)
        self.assertIn(sgs[1].uuid, svc3.servicegroups)
        self.assertIn(sgs[2].uuid, svc4.servicegroups)
        self.assertIn(sgs[3].uuid, svc4.servicegroups)
