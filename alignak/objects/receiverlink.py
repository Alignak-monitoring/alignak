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
This module provide ReceiverLink and ReceiverLinks classes used to manage receivers
"""
import logging
from alignak.objects.satellitelink import SatelliteLink, SatelliteLinks
from alignak.property import BoolProp, IntegerProp, StringProp

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class ReceiverLink(SatelliteLink):
    """
    Class to manage the receiver information
    """
    my_type = 'receiver'
    properties = SatelliteLink.properties.copy()
    properties.update({
        'type':
            StringProp(default='receiver', fill_brok=['full_status']),
        'receiver_name':
            StringProp(default='', fill_brok=['full_status'], to_send=True),
        'port':
            IntegerProp(default=7772, fill_brok=['full_status']),
        'manage_sub_realms':
            BoolProp(default=False, fill_brok=['full_status']),
        'manage_arbiters':
            BoolProp(default=False, fill_brok=['full_status'], to_send=True),
        'accept_passive_unknown_check_results':
            BoolProp(default=False, fill_brok=['full_status'], to_send=True),
    })

    def register_to_my_realm(self):  # pragma: no cover, seems not to be used anywhere
        """
        Add this reactionner to the realm

        :return: None
        """
        self.realm.receivers.append(self)


class ReceiverLinks(SatelliteLinks):
    """
    Class to manage list of ReceiverLink.
    ReceiverLinks is used to regroup all receivers
    """
    name_property = "receiver_name"
    inner_class = ReceiverLink
