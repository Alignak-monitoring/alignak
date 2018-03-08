# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2017: Alignak team, see AUTHORS.txt file for contributors
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
import logging
import socket

from alignak.objects.satellitelink import SatelliteLink, SatelliteLinks
from alignak.property import IntegerProp, StringProp
from alignak.http.client import HTTPClientException, HTTPClientConnectionException, \
    HTTPClientTimeoutException

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class ArbiterLink(SatelliteLink):
    """
    Class to manage the link to Arbiter daemon.
    With it, arbiter can see if a Arbiter daemon is alive, and can send it new configuration
    """
    my_type = 'arbiter'
    properties = SatelliteLink.properties.copy()
    properties.update({
        'type':
            StringProp(default='arbiter', fill_brok=['full_status']),
        'arbiter_name':
            StringProp(default='', fill_brok=['full_status']),
        'host_name':
            StringProp(default=socket.gethostname()),
        'port':
            IntegerProp(default=7770),
    })

    def is_me(self):  # pragma: no cover, seems not to be used anywhere
        """Check if parameter name if same than name of this object

        TODO: is it useful?

        :return: true if parameter name if same than this name
        :rtype: bool
        """
        logger.info("And arbiter is launched with the hostname:%s "
                    "from an arbiter point of view of addr:%s", self.host_name, socket.getfqdn())
        return self.host_name == socket.getfqdn() or self.host_name == socket.gethostname()

    def give_satellite_cfg(self):
        """
        Get configuration of the Arbiter satellite

        :return: dictionary of link information
        :rtype: dict
        """
        return super(ArbiterLink, self).give_satellite_cfg()

    def do_not_run(self):
        """Check if satellite running or not
        If not, try to run

        :return: true if satellite not running
        :rtype: bool
        """
        logger.debug("[%s] do_not_run", self.name)

        if not self.reachable or not self.ping():
            logger.warning("Not reachable for do_not_run: %s", self.name)
            return []

        try:
            self.con.get('do_not_run')
            return True
        except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection error when "
                                          "sending do not run: %s" % str(exp))
            self.set_dead()
        except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection timeout when "
                                          "sending do not run: %s" % str(exp))
        except HTTPClientException as exp:
            self.add_failed_check_attempt("Error when "
                                          "sending do not run: %s" % str(exp))

        return False

    def get_all_states(self):  # pragma: no cover, seems not to be used anywhere
        """Get states of all satellites

        TODO: is it useful?

        :return: list of all states
        :rtype: list | None
        """
        logger.debug("[%s] get_all_states", self.get_name())

        if not self.reachable or not self.ping():
            logger.warning("Not reachable for get_all_states: %s", self.name)
            return []

        try:
            return self.con.get('get_all_states')
        except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection error when "
                                          "getting all states: %s" % str(exp))
            self.set_dead()
        except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection timeout when "
                                          "getting all states: %s" % str(exp))
        except HTTPClientException as exp:
            self.add_failed_check_attempt("Error when "
                                          "getting all states: %s" % str(exp))

        return None

    def get_objects_properties(self, table, properties=None):  # pragma: no cover,
        # seems not to be used anywhere
        """Get properties of objects

        :param table: name of table
        :type table: str
        :param properties: list of properties
        :type properties: list
        :return: list of objects
        :rtype: list | None
        """
        logger.debug("[%s] get_objects_properties", self.name)

        if not self.reachable or not self.ping():
            logger.warning("Not reachable for get_all_states: %s", self.name)
            return []

        if properties is None:
            properties = []

        try:
            return self.con.get('get_objects_properties', {'table': table,
                                                           'properties': properties})
        except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection error when "
                                          "getting object properties: %s" % str(exp))
            self.set_dead()
        except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection timeout when "
                                          "getting object properties: %s" % str(exp))
        except HTTPClientException as exp:
            self.add_failed_check_attempt("Error when "
                                          "getting object properties: %s" % str(exp))

        return None


class ArbiterLinks(SatelliteLinks):
    """
    Class to manage list of ArbiterLink.
    ArbiterLinks is used to regroup all links with Arbiter daemon
    """
    name_property = "arbiter_name"
    inner_class = ArbiterLink

    def linkify(self, realms=None, modules=None):
        """Link modules to Arbiter

        # TODO: why having this specific method?
        Because of this, Arbiters do not link with realms!

        :param realms: Realm object list (always None for an arbiter)
        :type realms: list
        :param modules: list of modules
        :type modules: list
        :return: None
        """
        logger.debug("Linkify %s with %s", self, modules)
        self.linkify_s_by_module(modules)
