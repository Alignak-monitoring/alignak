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
"""This module provide a specific HTTP interface for a Broker."""
import logging
import cherrypy

from alignak.http.generic_interface import GenericInterface
from alignak.misc.serialization import unserialize

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class BrokerInterface(GenericInterface):
    """This class provides specific HTTP functions for the Broker daemons."""

    #####
    #   ___           _                                   _                     _
    #  |_ _|  _ __   | |_    ___   _ __   _ __     __ _  | |     ___    _ __   | |  _   _
    #   | |  | '_ \  | __|  / _ \ | '__| | '_ \   / _` | | |    / _ \  | '_ \  | | | | | |
    #   | |  | | | | | |_  |  __/ | |    | | | | | (_| | | |   | (_) | | | | | | | | |_| |
    #  |___| |_| |_|  \__|  \___| |_|    |_| |_|  \__,_| |_|    \___/  |_| |_| |_|  \__, |
    #                                                                               |___/
    #####

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def _push_broks(self):
        """Push the provided broks objects to the broker daemon

        Only used on a Broker daemon by the Arbiter

        :param: broks
        :type: list
        :return: None
        """
        data = cherrypy.request.json
        with self.app.arbiter_broks_lock:
            logger.debug("Pushing %d broks", len(data['broks']))
            self.app.arbiter_broks.extend([unserialize(elem, True) for elem in data['broks']])
