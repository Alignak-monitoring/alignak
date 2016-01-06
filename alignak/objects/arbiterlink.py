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
#     Grégory Starck, g.starck@gmail.com
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
This module provide ArbiterLink and ArbiterLinks classes used to manage link
with Arbiter daemon
"""

import socket

from alignak.objects.satellitelink import SatelliteLink, SatelliteLinks
from alignak.property import IntegerProp, StringProp
from alignak.http.client import HTTPEXCEPTIONS
from alignak.log import logger


class ArbiterLink(SatelliteLink):
    """
    Class to manage the link to Arbiter daemon.
    With it, arbiter can see if a Arbiter daemon is alive, and can send it new configuration
    """
    _id = 0
    my_type = 'arbiter'
    properties = SatelliteLink.properties.copy()
    properties.update({
        'arbiter_name':    StringProp(),
        'host_name':       StringProp(default=socket.gethostname()),
        'port':            IntegerProp(default=7770),
    })

    def get_config(self):
        """
        Get the config of the arbiter

        :return: the config
        :rtype: object
        """
        return self.con.get('get_config')

    def is_me(self, lookup_name):
        """
        Check if parameter name if same than name of this object

        :param lookup_name: name of arbiter to check
        :type lookup_name: str
        :return: true if parameter name if same than this name
        :rtype: bool
        """
        logger.info("And arbiter is launched with the hostname:%s "
                    "from an arbiter point of view of addr:%s", self.host_name, socket.getfqdn())
        if lookup_name:
            return lookup_name == self.get_name()
        else:
            return self.host_name == socket.getfqdn() or self.host_name == socket.gethostname()

    def give_satellite_cfg(self):
        """
        Get the config of this satellite

        :return: dictionary with information of the satellite
        :rtype: dict
        """
        return {'port': self.port, 'address': self.address, 'name': self.arbiter_name,
                'use_ssl': self.use_ssl, 'hard_ssl_name_check': self.hard_ssl_name_check}

    def do_not_run(self):
        """
        Check if satellite running or not
        If not, try to run

        :return: true if satellite not running
        :rtype: bool
        """
        if self.con is None:
            self.create_connection()
        try:
            self.con.get('do_not_run')
            return True
        except HTTPEXCEPTIONS, exp:
            self.con = None
            return False

    def get_all_states(self):
        """
        Get states of all satellites

        :return: list of all states
        :rtype: list | None
        """
        if self.con is None:
            self.create_connection()
        try:
            res = self.con.get('get_all_states')
            return res
        except HTTPEXCEPTIONS, exp:
            self.con = None
            return None

    def get_objects_properties(self, table, properties=[]):
        """
        Get properties of objects

        :param table: name of table
        :type table: str
        :param properties: list of properties
        :type properties: list
        :return: list of objects
        :rtype: list | None
        """
        if self.con is None:
            self.create_connection()
        try:
            print properties
            res = self.con.get('get_objects_properties', {'table': table, 'properties': properties})
            return res
        except HTTPEXCEPTIONS, exp:
            self.con = None
            return None


class ArbiterLinks(SatelliteLinks):
    """
    Class to manage list of ArbiterLink.
    ArbiterLinks is used to regroup all links with Arbiter daemon
    """
    name_property = "arbiter_name"
    inner_class = ArbiterLink

    def linkify(self, modules):
        """
        Link modules to Arbiter

        :param modules: list of modules
        :type modules: list
        :return: None
        """
        self.linkify_s_by_plug(modules)
