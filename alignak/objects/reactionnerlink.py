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
This module provide ReactionnerLink and ReactionnerLinks classes used to manage reactionners
"""

from alignak.objects.satellitelink import SatelliteLink, SatelliteLinks
from alignak.property import IntegerProp, StringProp, ListProp


class ReactionnerLink(SatelliteLink):
    """
    Class to manage the reactionner information
    """
    my_type = 'reactionner'
    properties = SatelliteLink.properties.copy()
    properties.update({
        'type':
            StringProp(default='reactionner', fill_brok=['full_status'], to_send=True),
        'reactionner_name':
            StringProp(default='', fill_brok=['full_status']),
        'port':
            IntegerProp(default=7769, fill_brok=['full_status'], to_send=True),
        # 'min_workers':
        #     IntegerProp(default=1, fill_brok=['full_status'], to_send=True),
        # 'max_workers':
        #     IntegerProp(default=30, fill_brok=['full_status'], to_send=True),
        # 'processes_by_worker':
        #     IntegerProp(default=256, fill_brok=['full_status'], to_send=True),
        # 'worker_polling_interval':
        #     IntegerProp(default=1, to_send=True),
        'reactionner_tags':
            ListProp(default=['None'], to_send=True),
    })


class ReactionnerLinks(SatelliteLinks):  # (Items):
    """
    Class to manage list of ReactionnerLink.
    ReactionnerLinks is used to regroup all reactionners
    """
    name_property = "reactionner_name"
    inner_class = ReactionnerLink
