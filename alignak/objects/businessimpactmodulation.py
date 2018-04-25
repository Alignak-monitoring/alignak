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
#     Sebastien Coavoux, s.coavoux@free.fr
#     david hannequin, david.hannequin@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Thibault Cohen, titilambert@gmail.com
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
This module provide Businessimpactmodulation and Businessimpactmodulations classes used to describe
the modulation of a business impact. Modulation occurs on a modulation period (Timeperiod)
"""

from alignak.objects.item import Item, Items

from alignak.property import StringProp, IntegerProp


class Businessimpactmodulation(Item):
    """Businessimpactmodulation class is simply a modulation of the business impact value
    (of a Host/Service) during a modulation period.
    """
    my_type = 'businessimpactmodulation'

    properties = Item.properties.copy()
    properties.update({
        'business_impact_modulation_name':
            StringProp(),
        'business_impact':
            IntegerProp(),
        'modulation_period':
            StringProp(default=''),
    })

    def __init__(self, params=None, parsing=True):
        super(Businessimpactmodulation, self).__init__(params, parsing=parsing)

        # Ok just put None as modulation_period, means 24x7
        if not hasattr(self, 'modulation_period'):
            self.modulation_period = '24x7'

    def get_name(self):
        """Accessor to business_impact_modulation_name attribute

        :return: business impact modulation name
        :rtype: str
        """
        if hasattr(self, 'business_impact_modulation_name'):
            return self.business_impact_modulation_name
        return 'Unnamed'


class Businessimpactmodulations(Items):
    """Businessimpactmodulations class allowed to handle easily
       several Businessimpactmodulation objects

    """
    name_property = "business_impact_modulation_name"
    inner_class = Businessimpactmodulation

    def linkify(self, timeperiods):
        """Wrapper for Businessimpactmodulations.linkify_cm_by_tp(timeperiods)

        :param timeperiods: timeperiods to link to
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: None
        """
        self.linkify_with_timeperiods(timeperiods, 'modulation_period')
