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
#     Romain Forlot, rforlot@yahoo.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Jean Gabes, naparuba@gmail.com
#     Nicolas Dupeux, nicolas@dupeux.net
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
Helper functions for some filtering, like for user based
"""



def only_related_to(lst, user):
    """
    Get only user relevant items. The item needs the following attributes :
     contacts
     source_problems
     impacts
    :param lst: A list of items
    :param user: A contact defined in Alignak (casual string)
    :return: A list of items (unique values)
    """
    # if the user is an admin, show all
    if user.is_admin:
        return lst

    # Ok the user is a simple user, we should filter
    r = set()
    for i in lst:
        # Maybe the user is a direct contact
        if user in i.contacts:
            r.add(i)
            continue
        # TODO: add a notified_contact pass

        # Maybe it's a contact of a linked elements (source problems or impacts)
        is_find = False
        for s in i.source_problems:
            if user in s.contacts:
                r.add(i)
                is_find = True
        # Ok skip this object now
        if is_find:
            continue
        # Now impacts related maybe?
        for imp in i.impacts:
            if user in imp.contacts:
                r.add(i)

    return list(r)
