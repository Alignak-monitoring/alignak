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
from alignak.property import ListProp
from alignak.log import logger


class Itemgroup(Item):
    """
    Class to manage a group of items
    An itemgroup is used to regroup items (group)
    """
    _id = 0

    properties = Item.properties.copy()
    properties.update({
        'members': ListProp(fill_brok=['full_status'], default=None, split_on_coma=True),
        # Alignak specific
        'unknown_members': ListProp(default=None),
    })

    def copy_shell(self):
        """
        Copy the groups properties EXCEPT the members.
        Members need to be fill after manually

        :return: Itemgroup object
        :rtype: object
        :return: None
        """
        cls = self.__class__
        old_id = cls._id
        new_i = cls()  # create a new group
        new_i._id = self._id  # with the same id
        cls._id = old_id  # Reset the Class counter

        # Copy all properties
        for prop in cls.properties:
            if prop is not 'members':
                if hasattr(self, prop):
                    val = getattr(self, prop)
                    setattr(new_i, prop, val)
        # but no members
        new_i.members = []
        return new_i

    def replace_members(self, members):
        """
        Replace members of itemgroup by new members list

        :param members: list of members
        :type members: list
        :return: None
        """
        self.members = members

    def fill_default(self):
        """
        Put property and it default value for properties not defined and not required

        :return: None
        """
        cls = self.__class__
        for prop, entry in cls.properties.items():
            if not hasattr(self, prop) and not entry.required:
                value = entry.default
                setattr(self, prop, value)

    def add_string_member(self, member):
        """
        Add new entry(member) to members list

        :param member: member name
        :type member: str
        :return: None
        """
        add_fun = list.extend if isinstance(member, list) else list.append
        if not hasattr(self, "members"):
            self.members = []
        add_fun(self.members, member)

    def add_string_unknown_member(self, member):
        """
        Add new entry(member) to unknown members list

        :param member: member name
        :type member: str
        :return: None
        """
        add_fun = list.extend if isinstance(member, list) else list.append
        if not self.unknown_members:
            self.unknown_members = []
        add_fun(self.unknown_members, member)

    def __iter__(self):
        return self.members.__iter__()

    def __delitem__(self, i):
        try:
            self.members.remove(i)
        except ValueError:
            pass

    def is_correct(self):
        """
        Check if a group is valid.
        Valid mean all members exists, so list of unknown_members is empty

        :return: True if group is correct, otherwise False
        :rtype: bool
        """
        res = True

        if self.unknown_members:
            for member in self.unknown_members:
                logger.error("[itemgroup::%s] as %s, got unknown member %s",
                             self.get_name(), self.__class__.my_type, member)
            res = False

        if self.configuration_errors != []:
            for err in self.configuration_errors:
                logger.error("[itemgroup] %s", err)
            res = False

        return res

    def has(self, prop):
        """
        Check if self have a property

        :param prop: property name
        :type prop: string
        :return: True if self has this attribute, otherwise False
        :rtype: bool
        """
        warnings.warn(
            "{s.__class__.__name__} is deprecated, please use "
            "`hasattr(your_object, attr)` instead. This has() method will "
            "be removed in a later version.".format(s=self),
            DeprecationWarning, stacklevel=2)
        return hasattr(self, prop)

    def get_initial_status_brok(self):
        """
        Get a brok with hostgroup info (like id, name)
        Members contain list of (id, host_name)

        :return:Brok object
        :rtype: object
        :return: None
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
        for i in self.members:
            # it look like lisp! ((( ..))), sorry....
            data['members'].append((i._id, i.get_name()))
        brok = Brok('initial_' + cls.my_type + '_status', data)
        return brok


class Itemgroups(Items):
    """
    Class to manage list of groups of items
    An itemgroups is used to regroup items group
    """

    def fill_default(self):
        """
        Put property and it default value for properties not defined and not required in
        each itemgroup

        :return: None
        """
        for i in self:
            i.fill_default()

    def add(self, itemgroup):
        """
        Add an item (itemgroup) to Itemgroups

        :param itemgroup: an item
        :type itemgroup: alignak.objects.itemgroup.Itemgroup
        :return: None
        """
        self.add_item(itemgroup)

    def get_members_by_name(self, gname):
        """
        Get members of groups have name in parameter

        :param gname: name of group
        :rtype gname: str
        :return: list of members
        :rtype: list
        """
        group = self.find_by_name(gname)
        if group is None:
            return []
        return getattr(group, 'members', [])
