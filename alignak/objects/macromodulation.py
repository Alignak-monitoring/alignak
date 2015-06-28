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

from item import Item, Items
from alignak.property import StringProp
from alignak.util import to_name_if_possible
from alignak.log import logger


class MacroModulation(Item):
    """
    Class to manage a MacroModulation
    A MacroModulation is defined to change critical and warning level in some periods (like the
    night)
    """
    id = 1  # zero is always special in database, so we do not take risk here
    my_type = 'macromodulation'

    properties = Item.properties.copy()
    properties.update({
        'macromodulation_name': StringProp(fill_brok=['full_status']),
        'modulation_period': StringProp(brok_transformation=to_name_if_possible,
                                        fill_brok=['full_status']),
    })

    running_properties = Item.running_properties.copy()

    _special_properties = ('modulation_period',)

    macros = {}

    def get_name(self):
        """
        Get the name of the timeperiod

        :return: the timeperiod name string
        :rtype: str
        """
        return self.macromodulation_name

    def is_active(self):
        """
        Know if this macro is active for this correct period

        :return: True is we are in the period, else return False
        :rtype: bool
        """
        now = int(time.time())
        if not self.modulation_period or self.modulation_period.is_time_valid(now):
            return True
        return False

    def is_correct(self):
        """
        Check if the macromodulation is valid and have all properties defined

        :return: True if valide, else return False
        :rtype: bool
        """
        state = True
        cls = self.__class__

        # Raised all previously saw errors like unknown commands or timeperiods
        if self.configuration_errors != []:
            state = False
            for err in self.configuration_errors:
                logger.error("[item::%s] %s", self.get_name(), err)

        for prop, entry in cls.properties.items():
            if prop not in cls._special_properties:
                if not hasattr(self, prop) and entry.required:
                    logger.warning(
                        "[macromodulation::%s] %s property not set", self.get_name(), prop
                    )
                    state = False  # Bad boy...

        # Ok just put None as modulation_period, means 24x7
        if not hasattr(self, 'modulation_period'):
            self.modulation_period = None

        return state


class MacroModulations(Items):
    """
    Class to manage all MacroModulation
    """
    name_property = "macromodulation_name"
    inner_class = MacroModulation

    def linkify(self, timeperiods):
        """
        Link with timeperiod

        :param timeperiods: Timeperiod object
        :type timeperiods: object
        """
        self.linkify_with_timeperiods(timeperiods, 'modulation_period')
