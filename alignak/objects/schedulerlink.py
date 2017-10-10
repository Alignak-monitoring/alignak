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
This module provide SchedulerLink and SchedulerLinks classes used to manage schedulers
"""
import logging
from alignak.objects.satellitelink import SatelliteLink, SatelliteLinks
from alignak.property import BoolProp, IntegerProp, StringProp, DictProp

from alignak.http.client import HTTPClientException, HTTPClientConnectionException, \
    HTTPClientTimeoutException

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class SchedulerLink(SatelliteLink):
    """
    Class to manage the scheduler information
    """

    # Ok we lie a little here because we are a mere link in fact
    my_type = 'scheduler'

    properties = SatelliteLink.properties.copy()
    properties.update({
        'type':
            StringProp(default='scheduler', fill_brok=['full_status']),
        'scheduler_name':
            StringProp(default='', fill_brok=['full_status'], to_send=True),
        'port':
            IntegerProp(default=7768, fill_brok=['full_status']),
        'weight':
            IntegerProp(default=1, fill_brok=['full_status']),
        'skip_initial_broks':
            BoolProp(default=False, fill_brok=['full_status']),
        'accept_passive_unknown_check_results':
            BoolProp(default=False, fill_brok=['full_status']),
    })

    running_properties = SatelliteLink.running_properties.copy()
    running_properties.update({
        'conf':
            StringProp(default=None),
        'cfg':
            DictProp(default={}),
        'need_conf':
            StringProp(default=True),
        'external_commands':
            StringProp(default=[]),
        'push_flavor':
            IntegerProp(default=0),
    })

    def register_to_my_realm(self):  # pragma: no cover, seems not to be used anywhere
        """
        Add this reactionner to the realm

        :return: None
        """
        self.realm.schedulers.append(self)

    def give_satellite_cfg(self):
        """
        Get configuration of the scheduler satellite

        :return: dictionary of link information
        :rtype: dict
        """
        res = super(SchedulerLink, self).give_satellite_cfg()
        res.update({
            'active': self.conf is not None, 'push_flavor': self.push_flavor
        })
        return res

    def get_override_configuration(self):
        """
        Some parameters can give as 'overridden parameters' like use_timezone
        so they will be mixed (in the scheduler) with the standard conf sent by the arbiter

        :return: dictionary of properties
        :rtype: dict
        """
        res = {}
        properties = self.__class__.properties
        for prop, entry in properties.items():
            if entry.override:
                res[prop] = getattr(self, prop)
        return res


class SchedulerLinks(SatelliteLinks):
    """Please Add a Docstring to describe the class here"""

    name_property = "scheduler_name"
    inner_class = SchedulerLink
