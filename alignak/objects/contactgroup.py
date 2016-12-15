# -*- coding: utf-8 -*-

#
# Copyright (C) 2015-2016: Alignak team, see AUTHORS.txt file for contributors
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

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Contactgroup(Itemgroup):
    """Class to manage a group of contacts
    A Contactgroup is used to manage a group of contacts
    """
    name_property = "contactgroup_name"
    members_property = "members"
    groupmembers_property = "contactgroup_members"
    my_type = 'contactgroup'

    properties = Itemgroup.properties.copy()
    properties.update({
        'contactgroup_name':
            StringProp(fill_brok=['full_status']),
        'contactgroup_members':
            ListProp(default=[], fill_brok=['full_status'], merging='join')
    })

    macros = {
        'CONTACTGROUPALIAS': 'alias',
        'CONTACTGROUPMEMBERS': 'get_members'
    }

    def get_contacts(self):
        """
        Get list of contacts of this group

        :return: list of contacts
        :rtype: list[alignak.objects.contact.Contact]
        """
        return self.get_members()

    def get_contactgroup_members(self):
        """
        Get list of groups members of this contactgroup

        :return: list of contacts
        :rtype: list
        """
        return self.get_group_members()

    def get_contacts_by_explosion(self, contactgroups, contacts):
        """
        Get direct contacts of this group and all contacts from the sub-groups
        Append sub-groups members to the members of this group

        :param contactgroups: Contactgroups object
        :type contactgroups: alignak.objects.contactgroup.Contactgroups
        :param contacts: contacts to explode
        :type contacts: alignak.objects.contact.Contacts
        :return: list of contact of this group
        :rtype: list[alignak.objects.contact.Contact]
        """
        # First we tag the group so it will not be exploded again if one of its members calls it
        self.already_exploded = True

        # Now the recursive part
        # recursion_tag is set to False for every group we explode
        # so if is True here, it must be a loop in the groups links... not GOOD!
        if self.recursion_tag:
            err = "[%s::%s] got a loop in %s definition" % \
                  (self.my_type, self.get_name(), self.groupmembers_property)
            self.configuration_errors.append(err)
            return self.get_members()

        # Ok, not in a loop, we tag it and continue
        self.recursion_tag = True

        group_members = self.get_group_members()
        for group_member in group_members:
            contactgroup = contactgroups.find_by_name(group_member)
            if contactgroup is not None:
                members_uuid = contactgroup.get_contacts_by_explosion(contactgroups, contacts)
                if members_uuid:
                    new_members = []
                    for member_uuid in members_uuid:
                        if member_uuid in contacts:
                            new_members.append(contacts[member_uuid])
                    self.add_members(new_members)

        return self.get_members()


class Contactgroups(Itemgroups):
    """Class to manage list of Contactgroup
    Contactgroups is used to regroup all Contactgroup

    """
    inner_class = Contactgroup

    def linkify(self, contacts):
        """Create link between objects::

        * contactgroups -> contacts

        :param contacts: contacts to link
        :type contacts: alignak.objects.contact.Contacts
        :return: None
        """
        self.linkify_contactgroup_by_contact(contacts)

    def linkify_contactgroup_by_contact(self, contacts):
        """Link the contacts with contactgroups

        :param contacts: realms object to link with
        :type contacts: alignak.objects.contact.Contacts
        :return: None
        """
        logger.debug("Linkify contactgroups and contacts")
        for contactgroup in self:
            members = contactgroup.get_contacts()
            logger.debug("- CG: %s, members: %s", contactgroup, members)

            # The new member list, in id
            new_members = []
            for member in members:
                member = member.strip()
                if member == '':  # void entry, skip this
                    continue
                elif member in contacts:
                    # We got a contact uuid
                    logger.debug("CG: %s, found a contact: %s", contactgroup, contacts[member])
                    new_members.append(member)

                    # Update the found contact contactgroups property and make it uniquified
                    # Note that it is a list of groups name
                    contacts[member].contactgroups.append(contactgroup.uuid)
                    contacts[member].contactgroups = list(set(contacts[member].contactgroups))
                else:
                    contact = contacts.find_by_name(member)
                    if contact is not None:
                        logger.debug("CG: %s, found a member: %s", contactgroup, member)
                        new_members.append(contact.uuid)

                        # Update the found contact contactgroups property and make it uniquified
                        contact.contactgroups.append(contactgroup.uuid)
                        contact.contactgroups = list(set(contact.contactgroups))
                    else:
                        # A not found contact is stored in unknown_members
                        contactgroup.add_unknown_member(member)

            if new_members:
                new_members = list(set(new_members))
                logger.debug("CG: %s, new members: %s", contactgroup, new_members)

                # We update the group members
                contactgroup.members = new_members

    def add_group_member(self, contact, contactgroup_name):
        """Add a contact to a contactgroup.
        If the contactgroup does not exist it is created

        :param contact: contact unique identifier
        :type contact: uuid
        :param contactgroup_name: contact group name
        :type contactgroup_name: str
        :return: None
        """
        contactgroup = self.find_by_name(contactgroup_name)
        if contactgroup is None:
            # Create the group if it does not yet exist
            contactgroup = Contactgroup({'contactgroup_name': contactgroup_name,
                                         'members': [contact.get_name()],
                                         'imported_from': 'inner'})
            self.add_item(contactgroup)
        else:
            contactgroup.add_member(contact)

    def explode(self, contacts):
        """
        Fill members with contactgroup_members

        :param contacts: contacts to explode
        :type contacts: alignak.objects.contact.Contacts
        :return:None
        """
        for contactgroup in self.items.values():
            for groupmember in contactgroup.get_group_members():
                group = self.find_by_name(groupmember)
                if group is None:
                    continue
                if group.already_exploded:
                    continue

                # get_contacts_by_explosion is a recursive function, so we must
                # tag the groups to avoid looping infinetely
                for groupmember in self.items.values():
                    groupmember.recursion_tag = False
                contactgroup.get_contacts_by_explosion(self, contacts)

        # Clean the recursion tag
        for group in self.items.values():
            if hasattr(group, 'recursion_tag'):
                del group.recursion_tag
