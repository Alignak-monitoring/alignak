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

    def setUp(self):
        super(TestContactGroup, self).setUp()

    def test_contactgroup(self):
        """ Default configuration has no loading problems ... as of it contactgroups are parsed
        correctly
        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')
        assert self.conf_is_correct

    def test_look_for_alias(self):
        """ Default configuration has no loading problems ... as of it contactgroups are parsed
        correctly
        :return: None
        """
        self.setup_with_file('cfg/contactgroup/alignak_groups_with_no_alias.cfg')
        assert self.conf_is_correct

        #  Find a contactgroup named NOALIAS
        cg = self._scheduler.contactgroups.find_by_name("NOALIAS")
        assert isinstance(cg, Contactgroup)
        assert cg.get_name() == "NOALIAS"
        assert cg.alias == "NOALIAS"

    def test_contactgroup_members(self):
        """ Test if members are linked from group

        :return: None
        """
        self.setup_with_file('cfg/contactgroup/alignak_contactgroup_members.cfg')
        assert self.conf_is_correct

        #  Found a contactgroup named allhosts_and_groups
        cg = self._scheduler.contactgroups.find_by_name(
            "allcontacts_and_groups"
        )
        assert isinstance(cg, Contactgroup)
        assert cg.get_name() == "allcontacts_and_groups"

        assert len(self._scheduler.contactgroups.get_members_by_name(
                "allcontacts_and_groups"
            )) == \
            2

        assert len(cg.get_contacts()) == 2
        for cid in cg.get_contacts():
            contact = self._scheduler.contacts[cid]
            print(contact)
            if contact.get_name() == "test_contact":
                assert contact.get_groupname() == "another_contact_test"
                assert contact.get_groupnames() == "another_contact_test"
            # This should match but there is a problem currently
            # Todo: fix this cross reference between contacts and contactgroups
            # Ongoing PR ...
            # if contact.get_name() == "test_contact_2":
            #     self.assertEqual(contact.get_groupname(), "allcontacts_and_groups")
            #     self.assertEqual(contact.get_groupnames(), "allcontacts_and_groups")

        assert len(cg.get_contactgroup_members()) == 1

    def test_members_contactgroup(self):
        """ Test if group is linked from the member
        :return: None
        """
        self.setup_with_file('cfg/contactgroup/alignak_contactgroup_members.cfg')
        assert self.conf_is_correct

        #  Found a contactgroup named allhosts_and_groups
        cg = self._scheduler.contactgroups.find_by_name("allcontacts_and_groups")
        assert isinstance(cg, Contactgroup)
        assert cg.get_name() == "allcontacts_and_groups"

        assert len(self._scheduler.contactgroups.get_members_by_name(
                "allcontacts_and_groups"
            )) == \
            2

        assert len(cg.get_contacts()) == 2
        print("List contactgroup contacts:")
        for contact_id in cg.members:
            contact = self._scheduler.contacts[contact_id]
            print("Contact: %s" % contact)
            assert isinstance(contact, Contact)

            if contact.get_name() == 'test_ok_0':
                assert len(contact.get_contactgroups()) == 4
                for group_id in contact.contactgroups:
                    group = self._scheduler.contactgroups[group_id]
                    print("Group: %s" % group)
                    assert group.get_name() in [
                        'ok', 'contactgroup_01', 'contactgroup_02', 'allcontacts_and_groups'
                    ]

        assert len(cg.get_contactgroup_members()) == 1
        print("List contactgroup groups:")
        for group in cg.get_contactgroup_members():
            print("Group: %s" % group)
            assert group in [
                'test_contact'
            ]

    def test_contactgroup_with_no_contact(self):
        """ Allow contactgroups with no hosts
        :return: None
        """
        self.setup_with_file('cfg/contactgroup/alignak_contactgroup_no_contact.cfg')
        assert self.conf_is_correct

        assert len(self._scheduler.contactgroups) == \
            3

        for group in self._scheduler.contactgroups:
            # contactgroups property returns an object list ... unlike the hostgroups property
            # of an host group ...
            # group = self._scheduler.contactgroups[group_id]
            print("Group: %s" % group)

        # Found a contactgroup named void
        cg = self._scheduler.contactgroups.find_by_name("void")
        print("cg: %s" % cg)
        assert isinstance(cg, Contactgroup)
        assert cg.get_name() == "void"

        assert len(self._scheduler.contactgroups.get_members_by_name("void")) == \
            0

        print("Contacts: %s" % cg.get_contactgroup_members())
        assert len(cg.get_contactgroup_members()) == 0

        print("Contacts: %s" % cg.get_contacts())
        assert len(cg.get_contacts()) == 0

    def test_contactgroup_with_space(self):
        """ Test that contactgroups can have a name with spaces
        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')
        assert self.conf_is_correct
        self.nb_contactgroups = len(self._scheduler.contactgroups)

        self.setup_with_file('cfg/contactgroup/alignak_contactgroup_with_space.cfg')
        assert self.conf_is_correct

        # Two more groups than the default configuration
        assert len(self._scheduler.contactgroups) == self.nb_contactgroups + 1

        assert self._scheduler.contactgroups.find_by_name("test_With Spaces").get_name() == \
            "test_With Spaces"
        assert self._scheduler.contactgroups.get_members_by_name(
                "test_With Spaces"
            ) is not \
            []

    def _dump_host(self, h):
        print "Dumping host", h.get_name()
        print h.contact_groups
        for c in h.contacts:
            print "->", self._scheduler.contacts[c].get_name()

    def _dump_svc(self, s):
        print "Dumping Service", s.get_name()
        print "  contact_groups : %s " % s.contact_groups
        for c in s.contacts:
            print "->", self._scheduler.contacts[c].get_name()

    def test_contactgroups_plus_inheritance(self):
        """ Test that contactgroups correclty manage inheritance
        :return: None
        """
        self.setup_with_file('cfg/contactgroup/alignak_contactgroups_plus_inheritance.cfg')
        assert self.conf_is_correct

        host0 = self._scheduler.hosts.find_by_name("test_host_0")
        # HOST 1 should have 2 group of contacts
        # WARNING, it's a string, not the real objects!
        self._dump_host(host0)

        assert "test_contact_1" in \
            [self._scheduler.contacts[c].get_name() for c in host0.contacts]
        assert "test_contact_2" in \
            [self._scheduler.contacts[c].get_name() for c in host0.contacts]

        host2 = self._scheduler.hosts.find_by_name("test_host_2")
        self._dump_host(host2)
        assert "test_contact_1" in \
            [self._scheduler.contacts[c].get_name() for c in host2.contacts]

        host3 = self._scheduler.hosts.find_by_name("test_host_3")
        self._dump_host(host3)
        assert "test_contact_1" in \
            [self._scheduler.contacts[c].get_name() for c in host3.contacts]
        assert "test_contact_2" in \
            [self._scheduler.contacts[c].get_name() for c in host3.contacts]

        host4 = self._scheduler.hosts.find_by_name("test_host_4")
        self._dump_host(host4)
        assert "test_contact_1" in \
            [self._scheduler.contacts[c].get_name() for c in host4.contacts]

        host5 = self._scheduler.hosts.find_by_name("test_host_5")
        self._dump_host(host5)
        assert "test_contact_1" in \
            [self._scheduler.contacts[c].get_name() for c in host5.contacts]
        assert "test_contact_2" in \
            [self._scheduler.contacts[c].get_name() for c in host5.contacts]

        host6 = self._scheduler.hosts.find_by_name("test_host_6")
        self._dump_host(host6)
        assert "test_contact_1" in \
            [self._scheduler.contacts[c].get_name() for c in host6.contacts]
        assert "test_contact_2" in \
            [self._scheduler.contacts[c].get_name() for c in host6.contacts]

        # Now Let's check service inheritance

        svc1 = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "svc_tmplA"
        )
        self._dump_svc(svc1)
        assert "test_contact_1" in \
            [self._scheduler.contacts[c].get_name() for c in svc1.contacts]

        svc2 = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "svc_tmplB"
        )
        self._dump_svc(svc2)
        assert "test_contact_2" in \
            [self._scheduler.contacts[c].get_name() for c in svc2.contacts]

        svc3 = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "svc_tmplA_tmplB"
        )
        assert "test_contact_1" in \
            [self._scheduler.contacts[c].get_name() for c in svc3.contacts]
        assert "test_contact_2" in \
            [self._scheduler.contacts[c].get_name() for c in svc3.contacts]
        self._dump_svc(svc3)
