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
#     Grégory Starck, g.starck@gmail.com

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
This module provide PollerLink and PollerLinks classes used to manage link
between the modules Arbiter and Poller
"""

from alignak.objects.satellitelink import SatelliteLink, SatelliteLinks
from alignak.property import BoolProp, IntegerProp, StringProp, ListProp


class PollerLink(SatelliteLink):
    """
    Class to manage the link between Arbiter and Poller. With it, arbiter
    can see if a poller is alive, and can send it new configuration
    """
    id = 0
    my_type = 'poller'
    # To_send: send or not to satellite conf
    properties = SatelliteLink.properties.copy()
    properties.update({
        'poller_name':  StringProp(fill_brok=['full_status'], to_send=True),
        'port':         IntegerProp(default=7771, fill_brok=['full_status']),
        'min_workers':  IntegerProp(default=0, fill_brok=['full_status'], to_send=True),
        'max_workers':  IntegerProp(default=30, fill_brok=['full_status'], to_send=True),
        'processes_by_worker': IntegerProp(default=256, fill_brok=['full_status'], to_send=True),
        'poller_tags':  ListProp(default=['None'], to_send=True),
    })

    def register_to_my_realm(self):
        """
        Add this relation to the realm
        """
        self.realm.pollers.append(self)


class PollerLinks(SatelliteLinks):
    """
    Class to manage list of PollerLink.
    PollerLinks is used to regroup all links between the Arbiter and different Pollers
    """
    name_property = "poller_name"
    inner_class = PollerLink
