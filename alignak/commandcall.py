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
from alignak.property import StringProp, BoolProp, IntegerProp, ListProp
from alignak.alignakobject import AlignakObject
from alignak.objects.command import Command


class CommandCall(AlignakObject):
    # pylint: disable=too-many-instance-attributes
    """This class is use when a service, contact or host define
    a command with args.
    """

    # AutoSlots create the __slots__ with properties and
    # running_properties names
    __metaclass__ = AutoSlots

    my_type = 'CommandCall'

    properties = {
        'call':
            StringProp(),
        'command':
            StringProp(),
        'poller_tag':
            StringProp(default=u'None'),
        'reactionner_tag':
            StringProp(default=u'None'),
        'module_type':
            StringProp(default=u'fork'),
        'valid':
            BoolProp(default=False),
        'args':
            ListProp(default=[]),
        'timeout':
            IntegerProp(default=-1),
        'late_relink_done':
            BoolProp(default=False),
        'enable_environment_macros':
            BoolProp(default=False),
    }

    def __init__(self, params, parsing=False):
        """
        A CommandCall may receive several commands in its parameters

        Thus, we must manage this specific configuration

        If no commands list is provided, the CommandCall is initialized with the provided
        paramters that also contain one Command. We must re-create a Command object and link
        this object to the CommandCall.

        :param params:
        :param parsing:
        """
        # We received one command
        if 'commands' not in params:
            # Create a base command call
            super(CommandCall, self).__init__(params, parsing=parsing)
            # Link the provided Alignak command with myself
            self.command = Command(params['command'], parsing=parsing)
            return

        # We received a commands list
        commands = params['commands']
        params.pop('commands')
        # Create a base command call
        super(CommandCall, self).__init__(params, parsing=parsing)

        # self.call = params['call']
        # self.enable_environment_macros = params.get('enable_environment_macros', False)
        # self.uuid = uuidmod.uuid4().hex
        self.timeout = -1
        command, self.args = self.get_command_and_args()
        self.command = commands.find_by_name(command)
        self.late_relink_done = False  # To do not relink again and again the same commandcall
        self.valid = self.command is not None
        if self.valid:
            # If the host/service do not give an override poller_tag, take
            # the one of the command
            self.poller_tag = params.get('poller_tag', u'None')  # from host/service
            self.reactionner_tag = params.get('reactionner_tag', u'None')
            self.module_type = self.command.module_type
            self.enable_environment_macros = self.command.enable_environment_macros
            self.timeout = int(self.command.timeout)
            if self.poller_tag == u'None':
                # from command if not set
                self.poller_tag = self.command.poller_tag
            # Same for reactionner tag
            if self.reactionner_tag == u'None':
                # from command if not set
                self.reactionner_tag = self.command.reactionner_tag

    def serialize(self):
        cls = self.__class__
        # id is not in *_properties
        res = {'uuid': self.uuid}
        for prop in cls.properties:
            if hasattr(self, prop):
                res[prop] = getattr(self, prop)

        res['command'] = None
        if self.command:
            res['command'] = self.command.serialize()
        return res

    def get_command_and_args(self):
        r"""We want to get the command and the args with ! splitting.
        but don't forget to protect against the \! to avoid splitting on them

        Remember: A Nagios-like command is command_name!arg1!arg2!...

        :return: None
        """

        # First protect
        p_call = self.call.replace(r'\!', '___PROTECT_EXCLAMATION___')
        tab = p_call.split('!')
        return tab[0].strip(), [s.replace('___PROTECT_EXCLAMATION___', '!') for s in tab[1:]]

    def is_valid(self):
        """Getter for valid attribute

        :return: True if object is valid, False otherwise
        :rtype: bool
        """
        return self.valid

    def __str__(self):  # pragma: no cover
        return str(self.__dict__)

    def get_name(self):
        """Getter for call attribute

        :return: call attribute
        :rtype: str
        """
        return self.call
