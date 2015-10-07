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
        'is_a':           StringProp(default='eventhandler'),
        'long_output':    StringProp(default=''),
        'perf_data':      StringProp(default=''),
        'sched_id':       IntegerProp(default=0),
        'timeout':        IntegerProp(default=10),
        'command':        StringProp(default=''),
        'is_snapshot':    BoolProp(default=False),
    })

    # _id = 0  #Is common to Actions
    def __init__(self, command, _id=None, ref=None, timeout=10, env={},
                 module_type='fork', reactionner_tag='None', is_snapshot=False):
        self.is_a = 'eventhandler'
        self.type = ''
        self.status = 'scheduled'
        if _id is None:  # id != None is for copy call only
            self._id = Action._id
            Action._id += 1
        self.ref = ref
        self._in_timeout = False
        self.timeout = timeout
        self.exit_status = 3
        self.command = command
        self.output = ''
        self.long_output = ''
        self.t_to_go = time.time()
        self.check_time = 0
        self.execution_time = 0.0
        self.u_time = 0.0
        self.s_time = 0.0
        self.perf_data = ''
        self.env = {}
        self.module_type = module_type
        self.worker = 'none'
        self.reactionner_tag = reactionner_tag
        self.is_snapshot = is_snapshot

    def copy_shell(self):
        """Get a copy o this event handler with minimal values (default, id, is snapshot)

        :return: new event handler
        :rtype: alignak.eventhandler.EventHandler
        """
        # We create a dummy check with nothing in it, just defaults values
        return self.copy_shell__(EventHandler('', _id=self._id, is_snapshot=self.is_snapshot))

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
        self.exit_status = e_handler.exit_status
        self.output = e_handler.output
        self.long_output = getattr(e_handler, 'long_output', '')
        self.check_time = e_handler.check_time
        self.execution_time = getattr(e_handler, 'execution_time', 0.0)
        self.perf_data = getattr(e_handler, 'perf_data', '')

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
        return "Check %d status:%s command:%s" % (self._id, self.status, self.command)

    def get_id(self):
        """Getter to id attribute

        :return: event handler id
        :rtype: int
        TODO: Duplicate from Notification.get_id
        """
        return self._id

    def __getstate__(self):
        """Call by pickle for dataify the comment
        because we DO NOT WANT REF in this pickleisation!

        :return: dict containing notification data
        :rtype: dict
        """
        cls = self.__class__
        # id is not in *_properties
        res = {'_id': self._id}
        for prop in cls.properties:
            if hasattr(self, prop):
                res[prop] = getattr(self, prop)

        return res

    def __setstate__(self, state):
        """Inverted function of getstate

        :param state: state to restore
        :type state: dict
        :return: None
        """
        cls = self.__class__
        self._id = state['_id']
        for prop in cls.properties:
            if prop in state:
                setattr(self, prop, state[prop])
        if not hasattr(self, 'worker'):
            self.worker = 'none'
        if not getattr(self, 'module_type', None):
            self.module_type = 'fork'
        # s_time and u_time are added between 1.2 and 1.4
        if not hasattr(self, 'u_time'):
            self.u_time = 0
            self.s_time = 0
