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
#     aviau, alexandre.viau@savoirfairelinux.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Gerhard Lausser, gerhard.lausser@consol.de

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
"""This module provides EventHandler class, used when hosts or services reach a bad state.

"""
import time

from alignak.action import Action
from alignak.property import IntegerProp, StringProp, BoolProp
from alignak.autoslots import AutoSlots


class EventHandler(Action):
    """Notification class, inherits from action class. Used to execute action
    when a host or a service is in a bad state

    """
    # AutoSlots create the __slots__ with properties and
    # running_properties names
    __metaclass__ = AutoSlots

    my_type = 'eventhandler'

    properties = Action.properties.copy()
    properties.update({
        'is_a':
            StringProp(default='eventhandler'),
        'long_output':
            StringProp(default=''),
        'perf_data':
            StringProp(default=''),
        'sched_id':
            IntegerProp(default=0),
        'is_snapshot':
            BoolProp(default=False),
    })

    def __init__(self, params=None, parsing=True):
        super(EventHandler, self).__init__(params, parsing=parsing)
        self.t_to_go = time.time()

    def get_return_from(self, e_handler):
        """Setter of the following attributes::

        * exit_status
        * output
        * long_output
        * check_time
        * execution_time
        * perf_data

        :param e_handler: event handler to get data from
        :type e_handler: alignak.eventhandler.EventHandler
        :return: None
        """
        for prop in ['exit_status', 'output', 'long_output', 'check_time', 'execution_time',
                     'perf_data']:
            setattr(self, prop, getattr(e_handler, prop))

    def get_outputs(self, out, max_plugins_output_length):
        """Setter of output attribute

        :param out: new output
        :type out:
        :param max_plugins_output_length: not use
        :type max_plugins_output_length:
        :return: None
        """
        self.output = out

    def is_launchable(self, timestamp):
        """Check if this event handler can be launched base on time

        :param timestamp: time to compare
        :type timestamp: int
        :return: True if t >= self.t_to_go, False otherwise
        :rtype: bool
        TODO: Duplicate from Notification.is_launchable
        """
        return timestamp >= self.t_to_go

    def __str__(self):
        return "Check %s status:%s command:%s" % (self.uuid, self.status, self.command)
