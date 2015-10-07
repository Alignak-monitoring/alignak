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
"""This module provide a specific HTTP interface for a Receiver."""

import cherrypy
from alignak.http.generic_interface import GenericInterface


class ReceiverInterface(GenericInterface):
    """This class provides specific HTTP functions for Receiver."""

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_raw_stats(self):
        """Get raw stats from the daemon::

        * command_buffer_size: external command buffer size

        :return: external command length
        :rtype: dict
        """
        app = self.app  # TODO: remove this and use self directly...
        res = {'command_buffer_size': len(app.external_commands)}
        return res

    @cherrypy.expose
    def push_host_names(self, sched_id, hnames):
        """Push hostname/scheduler links
        Use by the receivers to got the host names managed by the schedulers

        :param sched_id: scheduler_id that manages hnames
        :type sched_id: int
        :param hnames: host names list
        :type hnames: list
        :return: None
        """
        with self.app.lock:
            self.app.push_host_names(sched_id, hnames)  # To int that
