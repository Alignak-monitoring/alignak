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
import uuid
import warnings

from alignak.misc.serialization import serialize, unserialize, AlignakClassLookupException


class Brok(object):
    """A Brok is a piece of information exported by Alignak to the Broker.
    Broker can do whatever he wants with it.

    Broks types:
    - log (deprecated)
    - monitoring_log

    - notification_raise
    - acknowledge_raise
    - downtime_raise
    - acknowledge_expire
    - downtime_expire

    - initial_host_status, initial_service_status, initial_contact_status
    - initial_broks_done

    - host_retention_status, service_retention_status, contact_retention_status

    - update_host_status, update_service_status, initial_contact_status
    - host_check_result, service_check_result
    - host_next_schedule, service_next_scheduler
    - host_snapshot, service_snapshot
    - unknown_host_check_result, unknown_service_check_result

    - program_status
    - clean_all_my_instance_id

    - new_conf
    """
    my_type = 'brok'

    def __init__(self, params, parsing=True):
        if not parsing:
            if params is None:
                return
            for key, value in params.iteritems():
                setattr(self, key, value)

            if not hasattr(self, 'uuid'):
                self.uuid = uuid.uuid4().hex
            return
        self.uuid = params.get('uuid', uuid.uuid4().hex)
        self.type = params['type']
        self.instance_id = params.get('instance_id', None)
        # Again need to behave differently when un-serializing
        if 'uuid' in params:
            self.data = params['data']
        else:
            self.data = serialize(params['data'])
        self.prepared = params.get('prepared', False)
        self.creation_time = params.get('creation_time', time.time())

    def serialize(self):
        """This function serialize into a simple dict object.
        It is used when transferring data to other daemons over the network (http)

        Here we directly return all attributes

        :return: json representation of a Brok
        :rtype: dict
        """
        return {"type": self.type, "instance_id": self.instance_id, "data": self.data,
                "prepared": self.prepared, "creation_time": self.creation_time, "uuid": self.uuid}

    def __str__(self):
        return str(self.__dict__) + '\n'

    @property
    def id(self):  # pylint: disable=C0103
        """Getter for id, raise deprecation warning
        :return: self.uuid
        """
        warnings.warn("Access to deprecated attribute id %s class" % self.__class__,
                      DeprecationWarning, stacklevel=2)
        return self.uuid

    @id.setter
    def id(self, value):  # pylint: disable=C0103
        """Setter for id, raise deprecation warning
        :param value: value to set
        :return: None
        """
        warnings.warn("Access to deprecated attribute id of %s class" % self.__class__,
                      DeprecationWarning, stacklevel=2)
        self.uuid = value

    def prepare(self):
        """Un-serialize data from data attribute and add instance_id key if necessary

        :return: None
        """
        # Maybe the brok is a old daemon one or was already prepared
        # if so, the data is already ok
        if hasattr(self, 'prepared') and not self.prepared:
            try:
                self.data = unserialize(self.data)
            except AlignakClassLookupException:
                raise
            if self.instance_id:
                self.data['instance_id'] = self.instance_id
        self.prepared = True
