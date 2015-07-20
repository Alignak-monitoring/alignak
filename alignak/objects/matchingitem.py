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
 This is a utility class for factorizing matching functions for
 discovery runners and rules.
"""

import re

from alignak.objects.item import Item


class MatchingItem(Item):
    """
    MatchingItem class provide function for regular expression matching
    """

    def is_matching(self, key, value, look_in='matches'):
        """Try to see if the key,value is matching one or
        our rule.

        :param key: key to find in dict
        :type key:
        :param value: value to find at dict[key]
        :type value:
        :param look_in: the attribute dict to look in (matches or not_matches)
        :type look_in: str
        :return: True if  dict[key] match in value, otherwise False
        :rtype: bool
        """
        if look_in == 'matches':
            d = self.matches
        else:
            d = self.not_matches
        # If we do not even have the key, we bailout
        if not key.strip() in d:
            return False

        # Get my matching pattern
        m = d[key]
        if ',' in m:
            matchings = [mt.strip() for mt in m.split(',')]
        else:
            matchings = [m]

        # Split the value by , too
        values = value.split(',')
        for m in matchings:
            for v in values:
                print "Try to match", m, v
                # Maybe m is a list, if so should check one values
                if isinstance(m, list):
                    for _m in m:
                        if re.search(_m, v):
                            return True
                else:
                    if re.search(m, v):
                        return True
        return False

    def is_matching_disco_datas(self, datas):
        """Check if data match one of our matching attribute (matches or not_matches)

        :param datas: data to parse
        :type datas:
        :return: True if we match one pattern in matches and no pattern in not_matches,
                 otherwise False
        :rtype: bool
        """
        # If we got not data, no way we can match
        if len(datas) == 0:
            return False

        # First we look if it's possible to match
        # we must match All self.matches things
        for m in self.matches:
            # print "Compare to", m
            match_one = False
            for (k, v) in datas.iteritems():
                # We found at least one of our match key
                if m == k:
                    if self.is_matching(k, v):
                        # print "Got matching with", m, k, v
                        match_one = True
                        continue
            if not match_one:
                # It match none
                # print "Match none, False"
                return False
        # print "It's possible to be OK"

        # And now look if ANY of not_matches is reach. If so
        # it's False
        for m in self.not_matches:
            # print "Compare to NOT", m
            match_one = False
            for (k, v) in datas.iteritems():
                # print "K,V", k,v
                # We found at least one of our match key
                if m == k:
                    # print "Go loop"
                    if self.is_matching(k, v, look_in='not_matches'):
                        # print "Got matching with", m, k, v
                        match_one = True
                        continue
            if match_one:
                # print "I match one, I quit"
                return False

        # Ok we match ALL rules in self.matches
        # and NONE of self.not_matches, we can go :)
        return True
