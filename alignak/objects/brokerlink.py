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
This module provide BrokerLink and BrokerLinks classes used to manage brokers
"""

from alignak.objects.satellitelink import SatelliteLink, SatelliteLinks
from alignak.property import IntegerProp, StringProp, BoolProp


class BrokerLink(SatelliteLink):
    """
    Class to manage the broker information
    """
    my_type = 'broker'
    properties = SatelliteLink.properties.copy()
    properties.update({
        'type':
            StringProp(default=u'broker', fill_brok=['full_status'], to_send=True),
        'broker_name':
            StringProp(default='', fill_brok=['full_status']),
        'port':
            IntegerProp(default=7772, fill_brok=['full_status'], to_send=True),
        'initialized':
            BoolProp(default=False, fill_brok=['full_status'], to_send=True),
    })

    def prepare_for_conf(self):
        """Initialize the pushed configuration dictionary
        with the inner properties that are to be propagated to the satellite link.

        :return: None
        """
        super(BrokerLink, self).prepare_for_conf()

        self.cfg.update({
            'satellites': {
                'receivers': {},
                'pollers': {},
                'reactionners': {}
            }
        })


class BrokerLinks(SatelliteLinks):
    """
    Class to manage list of BrokerLink.
    BrokerLinks is used to regroup all brokers
    """
    name_property = "broker_name"
    inner_class = BrokerLink
