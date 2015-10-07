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
#     Jonathan GAULUPEAU, jonathan@gaulupeau.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     GAULUPEAU Jonathan, jo.gaulupeau@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
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

"""
Helper functions for some sorting
"""


def hst_srv_sort(s01, s02):
    """
    Sort host and service by impact then state then name

    :param s01: A host or service to compare
    :type s01: alignak.objects.schedulingitem.SchedulingItem
    :param s02: Another host or service to compare
    :type s02: alignak.objects.schedulingitem.SchedulingItem
    :return:
      * -1 if s01 > s02
      * 0 if s01 == s02 (not true)
      * 1 if s01 < s02
    :rtype: int
    """
    if s01.business_impact > s02.business_impact:
        return -1
    if s02.business_impact > s01.business_impact:
        return 1

    # Ok, we compute a importance value so
    # For host, the order is UP, UNREACH, DOWN
    # For service: OK, UNKNOWN, WARNING, CRIT
    # And DOWN is before CRITICAL (potential more impact)
    tab = {'host': {0: 0, 1: 4, 2: 1},
           'service': {0: 0, 1: 2, 2: 3, 3: 1}
           }
    state1 = tab[s01.__class__.my_type].get(s01.state_id, 0)
    state2 = tab[s02.__class__.my_type].get(s02.state_id, 0)
    # ok, here, same business_impact
    # Compare warn and crit state
    if state1 > state2:
        return -1
    if state2 > state1:
        return 1

    # Ok, so by name...
    if s01.get_full_name() > s02.get_full_name():
        return 1
    else:
        return -1


def worse_first(s01, s02):
    """
    Sort host and service by state then impact then name

    :param s01: A host or service to compare
    :type s01: alignak.objects.schedulingitem.SchedulingItem
    :param s02: Another host or service to compare
    :type s02: alignak.objects.schedulingitem.SchedulingItem
    :return:
      * -1 if s01 > s02
      * 0 if s01 == s02 (not true)
      * 1 if s01 < s02
    :rtype: int
    """
    # Ok, we compute a importance value so
    # For host, the order is UP, UNREACH, DOWN
    # For service: OK, UNKNOWN, WARNING, CRIT
    # And DOWN is before CRITICAL (potential more impact)
    tab = {'host': {0: 0, 1: 4, 2: 1},
           'service': {0: 0, 1: 2, 2: 3, 3: 1}
           }
    state1 = tab[s01.__class__.my_type].get(s01.state_id, 0)
    state2 = tab[s02.__class__.my_type].get(s02.state_id, 0)

    # ok, here, same business_impact
    # Compare warn and crit state
    if state1 > state2:
        return -1
    if state2 > state1:
        return 1

    # Same? ok by business impact
    if s01.business_impact > s02.business_impact:
        return -1
    if s02.business_impact > s01.business_impact:
        return 1

    # Ok, so by name...
    # Ok, so by name...
    if s01.get_full_name() > s02.get_full_name():
        return -1
    else:
        return 1


def last_state_change_earlier(s01, s02):
    """
    Sort host and service by last_state_change

    :param s01: A host or service to compare
    :type s01: alignak.objects.schedulingitem.SchedulingItem
    :param s02: Another host or service to compare
    :type s02: alignak.objects.schedulingitem.SchedulingItem
    :return:
      * -1 if s01 > s02
      * 0 if s01 == s02 (not true)
      * 1 if s01 < s02
    :rtype: int
    """
    # ok, here, same business_impact
    # Compare warn and crit state
    if s01.last_state_change > s02.last_state_change:
        return -1
    if s01.last_state_change < s02.last_state_change:
        return 1

    return 0
