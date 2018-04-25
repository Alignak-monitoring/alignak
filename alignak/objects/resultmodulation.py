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
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
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

# The resultmodulation class is used for in scheduler modulation of results
# like the return code or the output.
"""
This module provide Resultmodulation and Resultmodulations classes used to describe
the modulation of a check command. Modulation occurs on a modulation period (Timeperiod)
"""
import time

from alignak.objects.item import Item, Items

from alignak.property import StringProp, IntegerProp, IntListProp


class Resultmodulation(Item):
    """Resultmodulation class is simply a modulation of a check result exit code
    during a modulation_period.

    """
    my_type = 'resultmodulation'

    properties = Item.properties.copy()
    properties.update({
        'resultmodulation_name':
            StringProp(),
        'exit_codes_match':
            IntListProp(default=[]),
        'exit_code_modulation':
            IntegerProp(default=None),
        'modulation_period':
            StringProp(default=None),
    })

    special_properties = ('modulation_period',)

    def get_name(self):
        """Accessor to resultmodulation_name attribute

        :return: result modulation name
        :rtype: str
        """
        if hasattr(self, 'resultmodulation_name'):
            return self.resultmodulation_name
        return 'Unnamed'

    def is_active(self, timperiods):
        """
        Know if this result modulation is active now

        :return: True is we are in the period, otherwise False
        :rtype: bool
        """
        now = int(time.time())
        timperiod = timperiods[self.modulation_period]
        if not timperiod or timperiod.is_time_valid(now):
            return True
        return False

    def module_return(self, return_code, timeperiods):
        """Module the exit code if necessary ::

        * modulation_period is legit
        * exit_code_modulation
        * return_code in exit_codes_match

        :param return_code: actual code returned by the check
        :type return_code: int
        :return: return_code modulated if necessary (exit_code_modulation)
        :rtype: int
        """
        # Only if in modulation_period of modulation_period == None
        if self.is_active(timeperiods):
            # Try to change the exit code only if a new one is defined
            if self.exit_code_modulation is not None:
                # First with the exit_code_match
                if return_code in self.exit_codes_match:
                    return_code = self.exit_code_modulation

        return return_code


class Resultmodulations(Items):
    """Resultmodulations class allowed to handle easily several CheckModulation objects

    """
    name_property = "resultmodulation_name"
    inner_class = Resultmodulation

    def linkify(self, timeperiods):
        """Wrapper for linkify_rm_by_tp
        Replace check_period by real Timeperiod object into each Resultmodulation

        :param timeperiods: timeperiods to link to
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: None
        """
        self.linkify_with_timeperiods(timeperiods, 'modulation_period')
