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
#     aviau, alexandre.viau@savoirfairelinux.com
#     Jean Gabes, naparuba@gmail.com
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
This module provide MacroModulation and MacroModulations classes used to change critical and
warning level in some periods (like the night)
"""

import time

from alignak.objects.item import Item, Items
from alignak.property import StringProp, DictProp
from alignak.util import to_name_if_possible


class MacroModulation(Item):
    """
    Class to manage a MacroModulation
    A MacroModulation is defined to change critical and warning level in some periods (like the
    night)
    """
    name_property = "macromodulation_name"
    my_type = 'macromodulation'

    properties = Item.properties.copy()
    properties.update({
        'macromodulation_name':
            StringProp(fill_brok=['full_status']),
        'modulation_period':
            StringProp(brok_transformation=to_name_if_possible, fill_brok=['full_status']),
    })

    running_properties = Item.running_properties.copy()
    running_properties.update({
        'customs':
            DictProp(default={}, fill_brok=['full_status']),
    })

    special_properties = ('modulation_period',)

    macros = {}

    def is_active(self, timperiods):
        """
        Know if this macro is active for this correct period

        :return: True is we are in the period, otherwise False
        :rtype: bool
        """
        now = int(time.time())
        timperiod = timperiods[self.modulation_period]
        if not timperiod or timperiod.is_time_valid(now):
            return True
        return False

    def is_correct(self):
        """
        Check if this object configuration is correct ::

        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """

        # Ok just put None as modulation_period, means 24x7
        if not hasattr(self, 'modulation_period'):
            self.modulation_period = None

        if not hasattr(self, 'customs') or not self.customs:
            self.add_error("[macromodulation::%s] contains no macro definition" %
                           (self.get_name()))

        return super(MacroModulation, self).is_correct() and self.conf_is_correct


class MacroModulations(Items):
    """
    Class to manage all MacroModulation
    """
    inner_class = MacroModulation

    def linkify(self, timeperiods):
        """
        Link with timeperiod

        :param timeperiods: Timeperiod object
        :type timeperiods: object
        :return: None
        """
        self.linkify_with_timeperiods(timeperiods, 'modulation_period')
