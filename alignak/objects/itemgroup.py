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
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Christophe Simon, geektophe@gmail.com
#     Romain Forlot, rforlot@yahoo.com
#     Christophe SIMON, christophe.simon@dailymotion.com

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

# And itemgroup is like a item, but it's a group of items :)

"""
This module provide Itemgroup and Itemgroups class used to define group of items
"""
import warnings

from alignak.objects.item import Item, Items
from alignak.brok import Brok
from alignak.property import ListProp, DictProp


class Itemgroup(Item):
    """Class to manage a group of items

    An Itemgroup is used to group items together. It may contain members
    and sub-groups as group members

    As for other Item based objects, it defines `name_property`and `my_type` that
    will be overloaded by the inherited classes: hostgroup, ...

    The Itemgroups also defines some extra class properties:
    - members_class: to define the base class of the group items
    - members_property: for the configuration property used
    to specify the members of the group
    - groupmembers_property: for the configuration property used
    to specify the sub-groups of the group

    """
    name_property = "groupname"
    my_type = 'group'

    members_class = Item
    members_property = "members"
    groupmembers_property = "groupmembers"

    properties = Item.properties.copy()
    properties.update({
        # List of members names
        'members':
            ListProp(default=[], fill_brok=['full_status']),
    })

    running_properties = Item.running_properties.copy()
    running_properties.update({
        # Dictionary for members uuid/name relation
        'members_uuid':
            DictProp(default={}, fill_brok=['full_status']),
    })

    def __init__(self, params=None, parsing=True, debug=False):

        if params is None:
            params = {}
        super(Itemgroup, self).__init__(params, parsing=parsing, debug=debug)

        if parsing:
            # On creation, groups are not yet exploded (populated with their members)
            self.already_exploded = False
            # We need a list to store unknwon group members
            self.unknown_members = []

    def __str__(self):
        return '<%s %s, %s members, %d sub-groups />' % (
            self.__class__.__name__, self.get_name(),
            len(self.get_members()) if self.get_members() else 'no',
            len(self.get_group_members() if self.get_group_members() else 'no'))

    __repr__ = __str__

    def __iter__(self):
        return self.members.__iter__()

    def __delitem__(self, i):
        try:
            self.members.remove(i)
        except ValueError:
            pass

    def copy_shell(self):
        """
        Copy the groups properties EXCEPT the members.
        Members need to be fill after manually

        :return: Itemgroup object
        :rtype: object
        :return: None
        """
        cls = self.__class__
        new_group = cls()  # create a new group
        new_group.uuid = self.uuid  # with the same id

        # Copy all properties
        for prop in cls.properties:
            if prop is not 'members':
                if hasattr(self, prop):
                    setattr(new_group, prop, getattr(self, prop))
        # except the group members
        new_group.members = []
        return new_group

    def add_member(self, new_member):
        """
        Add a new member to the group

        :param new_member: member to append unique identifier
        :type new_member: str (uuid)
        :return: None
        """
        self.add_members([new_member])

    def add_members(self, new_members):
        """
        Add new members to members list

        :param new_members: members to append list
        :type new_members: list of Item objects
        :return: None
        """
        # Ignore empty list
        if not new_members:
            return

        for new_member in new_members:
            self.members_uuid.update({new_member.get_name(): new_member.uuid})
            if new_member.get_name() in self.get_members():
                continue
            self.members.append(new_member.get_name())

    def add_unknown_member(self, member):
        """
        Add new entry(member) to unknown members list

        :param member: member name
        :type member: str
        :return: None
        """
        # Ignore empty element...
        if not member:
            return
        if not hasattr(self, 'unknown_members'):
            setattr(self, 'unknown_members', [])
        self.unknown_members.append(member)

    def get_members(self, names=True):
        """
        Get members of this group. Returns a list of the members names

        If the parameter `names` is False, this function will return the members uuid

        :return: list of members
        :rtype: list[str]
        """
        members_property = getattr(self.__class__, "members_property", 'not_existing')
        # if not names:
        #     members_names = []
        #     print("Groups: %s" % self.members_uuid)
        #     for member in getattr(self, members_property, []):
        #         members_names.append(self.members_uuid[member])
        #     return members_names
        return getattr(self, members_property, [])

    def get_group_members(self):
        """
        Get groups members of this group

        :return: list of services
        :rtype: list | str
        """
        groupmembers_property = getattr(self.__class__, "groupmembers_property", 'not_existing')
        return getattr(self, groupmembers_property, [])

    def is_correct(self):
        """
        Check if a group is valid.
        Valid means that all members exist, so list of unknown_members is empty

        :return: True if group is correct, otherwise False
        :rtype: bool
        """

        if self.unknown_members:
            for member in self.unknown_members:
                self.add_error("[%s::%s] got an unknown member '%s'" %
                               (self.my_type, self.get_name(), member))

        return super(Itemgroup, self).is_correct() and self.conf_is_correct

    def get_initial_status_brok(self, items=None):  # pylint:disable=W0221
        """
        Get a brok with hostgroup info (like id, name)
        Members contain list of (id, host_name)

        :param items: monitoring items, used to recover members
        :type items: alignak.objects.item.Items
        :return:Brok object
        :rtype: object
        """
        cls = self.__class__
        data = {}
        # Now config properties
        for prop, entry in cls.properties.items():
            if entry.fill_brok != []:
                if hasattr(self, prop):
                    data[prop] = getattr(self, prop)
        # Here members is just a bunch of host, I need name in place
        data['members'] = []
        for m_id in self.members:
            member = items[m_id]
            # it look like lisp! ((( ..))), sorry....
            data['members'].append((member.uuid, member.get_name()))
        brok = Brok({'type': 'initial_' + cls.my_type + '_status', 'data': data})
        return brok


class Itemgroups(Items):
    """
    Class to manage list of groups of items
    An itemgroups is used to regroup items group
    """
    inner_class = Itemgroup

    def __str__(self):
        return '<%s, %d groups />' % (
            self.__class__.__name__, len(self))

    __repr__ = __str__

    def get_members_of(self, groupname, names=False):
        """
        Get members of a group

        Returns a list of the group members uuid. If nams parameter is True the list
        contains the names rather then the uuid.

        If the group is not found, returns None

        :param groupname: name of the group to get members
        :rtype groupname: str
        :param names: the returned list contains the names, else the uuids
        :rtype names: bool
        :return: list of members
        :rtype: list
        """
        group = self.find_by_name(groupname)
        if group is not None:
            # if names:
            #     for member in group.get_members():
            return group.get_members()
        return None
