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
#     Nicolas Dupeux, nicolas@dupeux.net
#     Jan Ulferts, jan.ulferts@xing.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
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
"""This modules provide CommandCall class which is a abstraction for dealing with command line
(resolve macro, parse commands etc)

"""
from alignak.autoslots import AutoSlots
from alignak.property import StringProp, BoolProp, IntegerProp


class DummyCommandCall(object):
    """Ok, slots are fun: you cannot set the __autoslots__
     on the same class you use, fun isn't it? So we define*
     a dummy useless class to get such :)

    TODO: Remove this class and use __slots__ properly
    """
    pass


class CommandCall(DummyCommandCall):
    """This class is use when a service, contact or host define
    a command with args.
    """
    # AutoSlots create the __slots__ with properties and
    # running_properties names
    __metaclass__ = AutoSlots

    # __slots__ = ('_id', 'call', 'command', 'valid', 'args', 'poller_tag',
    #              'reactionner_tag', 'module_type', '__dict__')
    _id = 0
    my_type = 'CommandCall'

    properties = {
        'call':            StringProp(),
        'command':         StringProp(),
        'poller_tag':      StringProp(default='None'),
        'reactionner_tag': StringProp(default='None'),
        'module_type':     StringProp(default='fork'),
        'valid':           BoolProp(default=False),
        'args':            StringProp(default=[]),
        'timeout':         IntegerProp(default=-1),
        'late_relink_done': BoolProp(default=False),
        'enable_environment_macros': BoolProp(default=False),
    }

    def __init__(self, commands, call, poller_tag='None',
                 reactionner_tag='None', enable_environment_macros=0):
        self._id = self.__class__._id
        self.__class__._id += 1
        self.call = call
        self.timeout = -1
        # Now split by ! and get command and args
        self.get_command_and_args()
        self.command = commands.find_by_name(self.command.strip())
        self.late_relink_done = False  # To do not relink again and again the same commandcall
        if self.command is not None:
            self.valid = True
        else:
            self.valid = False
        if self.valid:
            # If the host/service do not give an override poller_tag, take
            # the one of the command
            self.poller_tag = poller_tag  # from host/service
            self.reactionner_tag = reactionner_tag
            self.module_type = self.command.module_type
            self.enable_environment_macros = self.command.enable_environment_macros
            self.timeout = int(self.command.timeout)
            if self.valid and poller_tag is 'None':
                # from command if not set
                self.poller_tag = self.command.poller_tag
            # Same for reactionner tag
            if self.valid and reactionner_tag is 'None':
                # from command if not set
                self.reactionner_tag = self.command.reactionner_tag

    def get_command_and_args(self):
        r"""We want to get the command and the args with ! splitting.
        but don't forget to protect against the \! to do not split them

        :return: None
        """

        # First protect
        p_call = self.call.replace(r'\!', '___PROTECT_EXCLAMATION___')
        tab = p_call.split('!')
        self.command = tab[0]
        # Reverse the protection
        self.args = [s.replace('___PROTECT_EXCLAMATION___', '!')
                     for s in tab[1:]]

    def is_valid(self):
        """Getter for valid attribute

        :return: True if object is valid, False otherwise
        :rtype: bool
        """
        return self.valid

    def __str__(self):
        return str(self.__dict__)

    def get_name(self):
        """Getter for call attribute

        :return: call attribute
        :rtype: str
        """
        return self.call

    def __getstate__(self):
        """Call by pickle to dataify the comment
        because we DO NOT WANT REF in this pickleisation!

        :return: dictionary with properties
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

        :return: None
        """
        cls = self.__class__
        # We move during 1.0 to a dict state
        # but retention file from 0.8 was tuple
        if isinstance(state, tuple):
            self.__setstate_pre_1_0__(state)
            return

        self._id = state['_id']
        for prop in cls.properties:
            if prop in state:
                setattr(self, prop, state[prop])

    def __setstate_pre_1_0__(self, state):
        """In 1.0 we move to a dict save. Before, it was
        a tuple save, like
        ({'_id': 11}, {'poller_tag': 'None', 'reactionner_tag': 'None',
        'command_line': u'/usr/local/nagios/bin/rss-multiuser',
        'module_type': 'fork', 'command_name': u'notify-by-rss'})

        :param state: state dictionary
        :type state: dict
        :return: None
        TODO: Clean this
        """
        for d_state in state:
            for key, val in d_state.items():
                setattr(self, key, val)
