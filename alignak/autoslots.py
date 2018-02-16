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
#     Grégory Starck, g.starck@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
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

"""The AutoSlots Class is a MetaClass: it manages how other classes
 are created (Classes, not instances of theses classes).
 Here it's role is to create the __slots__ list of the class with
 all properties of Class.properties and Class.running_properties
 so we do not have to add manually all properties to the __slots__
 list when we add a new entry"""


class AutoSlots(type):
    """AutoSlots inherit from type, it's compulsory for metaclass statement

    """

    def __new__(mcs, name, bases, dct):
        """Called when we create a new Class
        Some properties names are not allowed in __slots__ like 2d_coords of
        Host, so we must tag them in properties with no_slots

        :param mcs: AutoSlots
        :type mcs: object
        :param name: string of the Class (like Service)
        :type name: str
        :param bases: Classes of which Class inherits (like SchedulingItem)
        :type bases: object
        :param dct: new Class dict (like all method of Service)
        :type dct: object
        :return: new object
        :rtype: object
        """
        # Thanks to Bertrand Mathieu to the set idea
        slots = dct.get('__slots__', set())
        # Now get properties from properties and running_properties
        if 'properties' in dct:
            props = dct['properties']
            slots.update((p for p in props
                          if not props[p].no_slots))
        if 'running_properties' in dct:
            props = dct['running_properties']
            slots.update((p for p in props
                          if not props[p].no_slots))
        dct['__slots__'] = tuple(slots)
        return type.__new__(mcs, name, bases, dct)
