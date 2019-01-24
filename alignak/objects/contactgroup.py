# -*- coding: utf-8 -*-

#
# Copyright (C) 2015-2018: Alignak team, see AUTHORS.txt file for contributors
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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Guillaume Bour, guillaume@bour.cc
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Christophe Simon, geektophe@gmail.com
#     Romain Forlot, rforlot@yahoo.com

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

# Contactgroups are groups for contacts
# They are just used for the config read and explode by elements
"""
This module provide Contactgroup and Contactgroups class used to manage contact groups
"""
import logging
from alignak.objects.itemgroup import Itemgroup, Itemgroups

from alignak.property import StringProp, ListProp

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Contactgroup(Itemgroup):
    """Class to manage a group of contacts
    A Contactgroup is used to manage a group of contacts
    """
    my_type = 'contactgroup'
    members_property = "members"
    group_members_property = "contactgroup_members"

    properties = Itemgroup.properties.copy()
    properties.update({
        'contactgroup_name':
            StringProp(fill_brok=['full_status']),
        'alias':
            StringProp(default=u'', fill_brok=['full_status']),
        'contactgroup_members':
            ListProp(default=[], fill_brok=['full_status'], merging='join', split_on_comma=True)
    })

    macros = {
        'CONTACTGROUPNAME': 'contactgroup_name',
        'CONTACTGROUPALIAS': 'alias',
        'CONTACTGROUPMEMBERS': 'get_members',
        'CONTACTGROUPGROUPMEMBERS': 'get_contactgroup_members'
    }

    def get_name(self):
        """Get the group name"""
        return getattr(self, 'contactgroup_name', 'Unnamed')

    def get_contacts(self):
        """Get the contacts of the group

        :return: list of contacts
        :rtype: list[alignak.objects.contact.Contact]
        """
        return super(Contactgroup, self).get_members()

    def get_contactgroup_members(self):
        """Get the groups members of the group

        :return: list of contacts
        :rtype: list
        """
        return getattr(self, 'contactgroup_members', [])

    def get_contacts_by_explosion(self, contactgroups):
        # pylint: disable=access-member-before-definition
        """
        Get contacts of this group

        :param contactgroups: Contactgroups object, use to look for a specific one
        :type contactgroups: alignak.objects.contactgroup.Contactgroups
        :return: list of contact of this group
        :rtype: list[alignak.objects.contact.Contact]
        """
        # First we tag the hg so it will not be explode
        # if a son of it already call it
        self.already_exploded = True

        # Now the recursive part
        # rec_tag is set to False every CG we explode
        # so if True here, it must be a loop in HG
        # calls... not GOOD!
        if self.rec_tag:
            logger.error("[contactgroup::%s] got a loop in contactgroup definition",
                         self.get_name())
            if hasattr(self, 'members'):
                return self.members

            return ''
        # Ok, not a loop, we tag it and continue
        self.rec_tag = True

        cg_mbrs = self.get_contactgroup_members()
        for cg_mbr in cg_mbrs:
            contactgroup = contactgroups.find_by_name(cg_mbr.strip())
            if contactgroup is not None:
                value = contactgroup.get_contacts_by_explosion(contactgroups)
                if value is not None:
                    self.add_members(value)
        if hasattr(self, 'members'):
            return self.members

        return ''


class Contactgroups(Itemgroups):
    """Class to manage list of Contactgroup
    Contactgroups is used to regroup all Contactgroup

    """
    name_property = "contactgroup_name"
    inner_class = Contactgroup

    def add_member(self, contact_name, contactgroup_name):
        """Add a contact string to a contact member
        if the contact group do not exist, create it

        :param contact_name: contact name
        :type contact_name: str
        :param contactgroup_name: contact group name
        :type contactgroup_name: str
        :return: None
        """
        contactgroup = self.find_by_name(contactgroup_name)
        if not contactgroup:
            contactgroup = Contactgroup({'contactgroup_name': contactgroup_name,
                                         'alias': contactgroup_name,
                                         'members': contact_name})
            self.add_contactgroup(contactgroup)
        else:
            contactgroup.add_members(contact_name)

    def get_members_of_group(self, gname):
        """Get all members of a group which name is given in parameter

        :param gname: name of the group
        :type gname: str
        :return: list of contacts in the group
        :rtype: list[alignak.objects.contact.Contact]
        """
        contactgroup = self.find_by_name(gname)
        if contactgroup:
            return contactgroup.get_contacts()
        return []

    def add_contactgroup(self, contactgroup):
        """Wrapper for add_item method
        Add a contactgroup to the contactgroup list

        :param contactgroup: contact group to add
        :type contactgroup:
        :return: None
        """
        self.add_item(contactgroup)

    def linkify(self, contacts):
        """Create link between objects::

        * contactgroups -> contacts

        :param contacts: contacts to link
        :type contacts: alignak.objects.contact.Contacts
        :return: None
        """
        self.linkify_contactgroups_contacts(contacts)

    def linkify_contactgroups_contacts(self, contacts):
        """Link the contacts with contactgroups

        :param contacts: realms object to link with
        :type contacts: alignak.objects.contact.Contacts
        :return: None
        """
        for contactgroup in self:
            mbrs = contactgroup.get_contacts()

            # The new member list, in id
            new_mbrs = []
            for mbr in mbrs:
                mbr = mbr.strip()  # protect with strip at the beginning so don't care about spaces
                if mbr == '':  # void entry, skip this
                    continue
                member = contacts.find_by_name(mbr)
                # Maybe the contact is missing, if so, must be put in unknown_members
                if member is not None:
                    new_mbrs.append(member.uuid)
                else:
                    contactgroup.add_unknown_members(mbr)

            # Make members uniq
            new_mbrs = list(set(new_mbrs))

            # We find the id, we replace the names
            contactgroup.replace_members(new_mbrs)

    def explode(self):
        """
        Fill members with contactgroup_members

        :return:None
        """
        # We do not want a same hg to be explode again and again
        # so we tag it
        for tmp_cg in list(self.items.values()):
            tmp_cg.already_exploded = False

        for contactgroup in list(self.items.values()):
            if contactgroup.already_exploded:
                continue

            # get_contacts_by_explosion is a recursive
            # function, so we must tag hg so we do not loop
            for tmp_cg in list(self.items.values()):
                tmp_cg.rec_tag = False
            contactgroup.get_contacts_by_explosion(self)

        # We clean the tags
        for tmp_cg in list(self.items.values()):
            if hasattr(tmp_cg, 'rec_tag'):
                del tmp_cg.rec_tag
            del tmp_cg.already_exploded
