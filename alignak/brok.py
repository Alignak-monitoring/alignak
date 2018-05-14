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
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de

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
"""Brok module provide Brok class which is basically event for Alignak.
Brok are filled depending on their type (check_result, initial_state ...)

"""
import time
from datetime import datetime

from alignak.alignakobject import get_a_new_object_id
from alignak.misc.serialization import serialize, unserialize, AlignakClassLookupException


class Brok(object):
    """A Brok is a piece of information exported by Alignak to the Broker.
    Broker can do whatever he wants with it.

    Broks types:
    - log
    - monitoring_log

    - notification_raise
    - acknowledge_raise
    - downtime_raise
    - acknowledge_expire
    - downtime_expire
    - initial_host_status, initial_service_status, initial_contact_status
    - initial_broks_done

    - update_host_status, update_service_status, initial_contact_status
    - host_check_result, service_check_result
    - host_next_schedule, service_next_scheduler
    - host_snapshot, service_snapshot
    - unknown_host_check_result, unknown_service_check_result

    - program_status, initial program status
    - update_program_status, program status updated (raised on each scheduler loop)
    - clean_all_my_instance_id

    - new_conf
    """
    my_type = 'brok'

    def __init__(self, params, parsing=True):
        # pylint: disable=unused-argument
        """
        :param params: initialization parameters
        :type params: dict
        :param parsing: not used but necessary for serialization/unserialization
        :type parsing: bool
        """
        self.uuid = params.get('uuid', get_a_new_object_id())
        self.prepared = params.get('prepared', False)
        self.creation_time = params.get('creation_time', time.time())
        self.type = params.get('type', u'unknown')
        self.instance_id = params.get('instance_id', None)

        # Need to behave differently when un-serializing
        if 'uuid' in params:
            self.data = params['data']
        else:
            self.data = serialize(params['data'])

    def __repr__(self):  # pragma: no cover
        ct = datetime.fromtimestamp(self.creation_time).strftime("%Y-%m-%d %H:%M:%S.%f")
        return "Brok %s (%s) '%s': %s" % (self.uuid, ct, self.type, self.data)
    __str__ = __repr__

    def serialize(self):
        """This function serialize into a simple dict object.
        It is used when transferring data to other daemons over the network (http)

        Here we directly return all attributes

        :return: json representation of a Brok
        :rtype: dict
        """
        return {
            "uuid": self.uuid, "type": self.type, "instance_id": self.instance_id,
            "prepared": self.prepared, "creation_time": self.creation_time,
            "data": self.data
        }

    def prepare(self):
        """Un-serialize data from data attribute and add instance_id key if necessary

        :return: None
        """
        # Maybe the brok is a old daemon one or was already prepared
        # if so, the data is already ok
        if hasattr(self, 'prepared') and not self.prepared:
            try:
                self.data = unserialize(self.data)
            except AlignakClassLookupException:  # pragma: no cover, should never happen...
                raise
            if self.instance_id:
                self.data['instance_id'] = self.instance_id
        self.prepared = True
