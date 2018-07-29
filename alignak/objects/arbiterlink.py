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
from alignak.property import IntegerProp, StringProp, FloatProp
from alignak.http.client import HTTPClientException, HTTPClientConnectionException, \
    HTTPClientTimeoutException

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class ArbiterLink(SatelliteLink):
    """
    Class to manage the link to Arbiter daemon.
    With it, a master arbiter can communicate with  a spare Arbiter daemon
    """
    my_type = 'arbiter'
    properties = SatelliteLink.properties.copy()
    properties.update({
        'type':
            StringProp(default=u'arbiter', fill_brok=['full_status'], to_send=True),
        'arbiter_name':
            StringProp(default='', fill_brok=['full_status']),
        'host_name':
            StringProp(default=socket.gethostname(), to_send=True),
        'port':
            IntegerProp(default=7770, to_send=True),
        'last_master_speak':
            FloatProp(default=0.0)
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

    def do_not_run(self):
        """Check if satellite running or not
        If not, try to run

        :return: true if satellite not running
        :rtype: bool
        """
        logger.debug("[%s] do_not_run", self.name)

        try:
            self.con.get('_do_not_run')
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


class ArbiterLinks(SatelliteLinks):
    """
    Class to manage list of ArbiterLink.
    ArbiterLinks is used to regroup all links with Arbiter daemon
    """
    name_property = "arbiter_name"
    inner_class = ArbiterLink

    def linkify(self, modules=None):
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
