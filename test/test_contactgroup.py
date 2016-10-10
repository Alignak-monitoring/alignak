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

from alignak.objects import Contact
from alignak.objects import Contactgroup
from alignak_test import AlignakTest


class TestContactGroup(AlignakTest):
    """
    This class tests the contactgroups
    """

    def test_contactgroup(self):
        """
        Default configuration has no loading problems ... as of it contactgroups are parsed
        correctly
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        self.assertTrue(self.schedulers['scheduler-master'].conf.conf_is_correct)

    def test_look_for_alias(self):
        """
        Default configuration has no loading problems ... as of it contactgroups are parsed correctly
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/contactgroup/alignak_groups_with_no_alias.cfg')
        self.assertTrue(self.schedulers['Default-Scheduler'].conf.conf_is_correct)

        #  Found a contactgroup named NOALIAS
        cg = self.schedulers['Default-Scheduler'].sched.contactgroups.find_by_name("NOALIAS")
        self.assertIsInstance(cg, Contactgroup)
        self.assertEqual(cg.get_name(), "NOALIAS")
        self.assertEqual(cg.alias, "NOALIAS")

    def test_contactgroup_members(self):
        """
        Test if members are linked from group

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/contactgroup/alignak_contactgroup_members.cfg')
        self.assertTrue(self.schedulers['scheduler-master'].conf.conf_is_correct)

        #  Found a contactgroup named allhosts_and_groups
        cg = self.schedulers['scheduler-master'].sched.contactgroups.find_by_name("allcontacts_and_groups")
        self.assertIsInstance(cg, Contactgroup)
        self.assertEqual(cg.get_name(), "allcontacts_and_groups")

        self.assertEqual(
            len(self.schedulers['scheduler-master'].sched.contactgroups.get_members_by_name("allcontacts_and_groups")),
            2
        )

        self.assertEqual(len(cg.get_contacts()), 2)

        self.assertEqual(len(cg.get_contactgroup_members()), 1)

    def test_members_contactgroup(self):
        """
        Test if group is linked from the member
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/contactgroup/alignak_contactgroup_members.cfg')
        self.assertTrue(self.schedulers['scheduler-master'].conf.conf_is_correct)

        #  Found a contactgroup named allhosts_and_groups
        cg = self.schedulers['scheduler-master'].sched.contactgroups.find_by_name("allcontacts_and_groups")
        self.assertIsInstance(cg, Contactgroup)
        self.assertEqual(cg.get_name(), "allcontacts_and_groups")

        self.assertEqual(
            len(self.schedulers['scheduler-master'].sched.contactgroups.get_members_by_name(
                "allcontacts_and_groups"
            )),
            2
        )

        self.assertEqual(len(cg.get_contacts()), 2)
        print("List contactgroup contacts:")
        for contact_id in cg.members:
            contact = self.schedulers['scheduler-master'].sched.contacts[contact_id]
            print("Contact: %s" % contact)
            self.assertIsInstance(contact, Contact)

            if contact.get_name() == 'test_ok_0':
                self.assertEqual(len(contact.get_contactgroups()), 4)
                for group_id in contact.contactgroups:
                    group = self.schedulers['scheduler-master'].sched.contactgroups[group_id]
                    print("Group: %s" % group)
                    self.assertIn(group.get_name(), [
                        'ok', 'contactgroup_01', 'contactgroup_02', 'allcontacts_and_groups'
                    ])

        self.assertEqual(len(cg.get_contactgroup_members()), 1)
        print("List contactgroup groups:")
        for group in cg.get_contactgroup_members():
            print("Group: %s" % group)
            self.assertIn(group, [
                'test_contact'
            ])

    def test_contactgroup_with_no_contact(self):
        """
        Allow contactgroups with no hosts
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/contactgroup/alignak_contactgroup_no_contact.cfg')
        self.assertTrue(self.schedulers['scheduler-master'].conf.conf_is_correct)

        self.assertEqual(
            len(self.schedulers['scheduler-master'].sched.contactgroups),
            3
        )

        for group in self.schedulers['scheduler-master'].sched.contactgroups:
            # contactgroups property returns an object list ... unlike the hostgroups property
            # of an host group ...
            # group = self.schedulers['scheduler-master'].sched.contactgroups[group_id]
            print("Group: %s" % group)

        # Found a contactgroup named void
        cg = self.schedulers['scheduler-master'].sched.contactgroups.find_by_name("void")
        print("cg: %s" % cg)
        self.assertIsInstance(cg, Contactgroup)
        self.assertEqual(cg.get_name(), "void")

        self.assertEqual(
            len(self.schedulers['scheduler-master'].sched.contactgroups.get_members_by_name("void")),
            0
        )

        print("Contacts: %s" % cg.get_contactgroup_members())
        self.assertEqual(len(cg.get_contactgroup_members()), 0)

        print("Contacts: %s" % cg.get_contacts())
        self.assertEqual(len(cg.get_contacts()), 0)

    def test_contactgroup_with_space(self):
        """
        Test that contactgroups can have a name with spaces
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        self.assertTrue(self.schedulers['scheduler-master'].conf.conf_is_correct)
        self.nb_contactgroups = len(self.schedulers['scheduler-master'].sched.contactgroups)

        self.setup_with_file('cfg/contactgroup/alignak_contactgroup_with_space.cfg')
        self.assertTrue(self.schedulers['scheduler-master'].conf.conf_is_correct)

        # Two more groups than the default configuration
        self.assertEqual(
            len(self.schedulers['scheduler-master'].sched.contactgroups), self.nb_contactgroups + 1
        )

        self.assertEqual(
            self.schedulers['scheduler-master'].sched.contactgroups.find_by_name("test_With Spaces").get_name(),
            "test_With Spaces"
        )
        self.assertIsNot(
            self.schedulers['scheduler-master'].sched.contactgroups.get_members_by_name(
                "test_With Spaces"
            ),
            []
        )

    def _dump_host(self, h):
        print "Dumping host", h.get_name()
        print h.contact_groups
        for c in h.contacts:
            print "->", self.schedulers['scheduler-master'].sched.contacts[c].get_name()

    def _dump_svc(self, s):
        print "Dumping Service", s.get_name()
        print "  contact_groups : %s " % s.contact_groups
        for c in s.contacts:
            print "->", self.schedulers['scheduler-master'].sched.contacts[c].get_name()

    def test_contactgroups_plus_inheritance(self):
        """
        Test that contactgroups correclty manage inheritance
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/contactgroup/alignak_contactgroups_plus_inheritance.cfg')
        self.assertTrue(self.schedulers['scheduler-master'].conf.conf_is_correct)

        host0 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        # HOST 1 should have 2 group of contacts
        # WARNING, it's a string, not the real objects!
        self._dump_host(host0)

        self.assertIn(
            "test_contact_1",
            [self.schedulers['scheduler-master'].sched.contacts[c].get_name() for c in host0.contacts]
        )
        self.assertIn(
            "test_contact_2",
            [self.schedulers['scheduler-master'].sched.contacts[c].get_name() for c in host0.contacts]
        )

        host2 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_2")
        self._dump_host(host2)
        self.assertIn(
            "test_contact_1",
            [self.schedulers['scheduler-master'].sched.contacts[c].get_name() for c in host2.contacts]
        )

        host3 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_3")
        self._dump_host(host3)
        self.assertIn(
            "test_contact_1",
            [self.schedulers['scheduler-master'].sched.contacts[c].get_name() for c in host3.contacts]
        )
        self.assertIn(
            "test_contact_2",
            [self.schedulers['scheduler-master'].sched.contacts[c].get_name() for c in host3.contacts]
        )

        host4 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_4")
        self._dump_host(host4)
        self.assertIn(
            "test_contact_1",
            [self.schedulers['scheduler-master'].sched.contacts[c].get_name() for c in host4.contacts]
        )

        host5 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_5")
        self._dump_host(host5)
        self.assertIn(
            "test_contact_1",
            [self.schedulers['scheduler-master'].sched.contacts[c].get_name() for c in host5.contacts]
        )
        self.assertIn(
            "test_contact_2",
            [self.schedulers['scheduler-master'].sched.contacts[c].get_name() for c in host5.contacts]
        )

        host6 = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_6")
        self._dump_host(host6)
        self.assertIn(
            "test_contact_1",
            [self.schedulers['scheduler-master'].sched.contacts[c].get_name() for c in host6.contacts]
        )
        self.assertIn(
            "test_contact_2",
            [self.schedulers['scheduler-master'].sched.contacts[c].get_name() for c in host6.contacts]
        )

        # Now Let's check service inheritance

        svc1 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "svc_tmplA"
        )
        self._dump_svc(svc1)
        self.assertIn(
            "test_contact_1",
            [self.schedulers['scheduler-master'].sched.contacts[c].get_name() for c in svc1.contacts]
        )

        svc2 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "svc_tmplB"
        )
        self._dump_svc(svc2)
        self.assertIn(
            "test_contact_2",
            [self.schedulers['scheduler-master'].sched.contacts[c].get_name() for c in svc2.contacts]
        )

        svc3 = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "svc_tmplA_tmplB"
        )
        self.assertIn(
            "test_contact_1",
            [self.schedulers['scheduler-master'].sched.contacts[c].get_name() for c in svc3.contacts]
        )
        self.assertIn(
            "test_contact_2",
            [self.schedulers['scheduler-master'].sched.contacts[c].get_name() for c in svc3.contacts]
        )
        self._dump_svc(svc3)
