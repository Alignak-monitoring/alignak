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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
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
"""This module provides Hostescalation and Hostescalations classes that
implements host escalation for notification. Basically used for parsing.

"""
import logging

from alignak.objects.item import Item, Items
from alignak.objects.escalation import Escalation

from alignak.property import IntegerProp, StringProp, ListProp

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Hostescalation(Item):
    """Hostescalation class is used to implement notification escalation for hosts

    TODO: Why this class does not inherit from alignak.objects.Escalation.
          Maybe we can merge it
    """
    name_property = "escalation_name"
    my_type = 'hostescalation'

    properties = Item.properties.copy()
    properties.update({
        'escalation_name':
            StringProp(),
        'host_name':
            StringProp(),
        'hostgroup_name':
            StringProp(default=''),
        'first_notification':
            IntegerProp(),
        'last_notification':
            IntegerProp(),
        'notification_interval':
            IntegerProp(default=30),  # like Nagios value
        'escalation_period':
            StringProp(default=''),
        'escalation_options':
            ListProp(default=['d', 'u', 'r', 'w', 'c']),
        'contacts':
            StringProp(),
        'contact_groups':
            StringProp(),
        'first_notification_time':
            IntegerProp(),
        'last_notification_time':
            IntegerProp(),
    })


class Hostescalations(Items):
    """Hostescalations manage a list of Hostescalation objects, used for parsing configuration

    """
    inner_class = Hostescalation

    def explode(self, escalations):
        """Create instance of Escalation for each HostEscalation object

        :param escalations: list of escalation, used to add new ones
        :type escalations: alignak.objects.escalation.Escalations
        :return: None
        """
        # Now we explode all escalations (host_name, hostgroup_name) to escalations
        for escalation in self:
            name = getattr(escalation, 'host_name', getattr(escalation, 'hostgroup_name', ''))
            escalation.escalation_name = 'Generated-HostEscalation-%s-%s' % (name, escalation.uuid)

            serialized = escalation.serialize()
            logger.debug("Host escalation: %s", serialized)
            escalations.add_item(Escalation(serialized))
