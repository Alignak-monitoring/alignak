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
from alignak.alignakobject import AlignakObject
from alignak.misc.serialization import serialize, unserialize
from alignak.property import (StringProp, BoolProp, IntegerProp, ListProp, ToGuessProp,
                              PythonizeError)


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
        # Initial command line lie in the configuration
        'command_line':
            StringProp(),
        # Command line split: name and arguments
        'command_name':
            StringProp(),
        'args':
            ListProp(default=[]),
        # alignak.objects.Command
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
        'timeout':
            IntegerProp(default=-1),
        'enable_environment_macros':
            BoolProp(default=False),
    }

    def __init__(self, params, parsing=False):
        """
        Note: A CommandCall may receive 'commands' in its parameters; it is the whole
        known commands list in which the command must be found.

        If no commands list is provided, the CommandCall is initialized with the provided
        parameters that must contain one Command.

        :param params:
        """
        self.command_line = None

        commands = None
        if 'commands' in params:
            commands = params.pop('commands')

        # Create a base command call
        super(CommandCall, self).__init__(params, parsing=False)

        for key in params:
            # We want to create instance of object with the good type.
            # Here we've just parsed config files so everything is a string or a list.
            # We use the pythonize method to get the good type.
            try:
                if key in self.properties:
                    val = self.properties[key].pythonize(params[key])
                else:
                    val = ToGuessProp().pythonize(params[key])
            except (PythonizeError, AttributeError, ValueError, TypeError) as exp:
                raise PythonizeError("Error while pythonizing parameter '%s': %s" % (key, exp))

            setattr(self, key, val)

        # Get command and arguments
        self.command_name, self.args = self.get_command_and_args()

        if parsing:
            # We received a commands list to search into...
            self.command = commands.find_by_name(self.command_name)
            self.valid = self.command is not None
            if self.valid:
                # Get the host/service poller/reactionner tag, else the ones defined in the command
                if self.poller_tag in [None, 'None']:
                    self.poller_tag = self.command.poller_tag
                # Same for reactionner tag
                if self.reactionner_tag in [None, 'None']:
                    self.reactionner_tag = self.command.reactionner_tag

                self.module_type = self.command.module_type
                self.enable_environment_macros = self.command.enable_environment_macros
                self.timeout = int(self.command.timeout)
        else:
            # Link the provided Alignak command with myself
            unserialize(params['command'])
            self.command = unserialize(params['command'])

    def __str__(self):
        return '<CC %s, uuid=%s, command line: %s />' \
               % (self.get_name(), self.uuid, getattr(self, 'command_line', None))
    __repr__ = __str__

    def serialize(self):
        # uuid is not in *_properties
        res = {'uuid': self.uuid}
        for prop in self.__class__.properties:
            if hasattr(self, prop):
                res[prop] = getattr(self, prop)

        res['command'] = None
        if self.command:
            res['command'] = serialize(self.command)
        # print("serialize: %s" % (res))
        return res

    def get_command_and_args(self):
        r"""We want to get the command and the args with ! splitting.
        but don't forget to protect against the \! to avoid splitting on them

        Remember: A Nagios-like command is command_name!arg1!arg2!...

        :return: None
        """

        # First protect
        tab = self.command_line.replace(r'\!', '___PROTECT_EXCLAMATION___').split('!')
        return tab[0].strip(), [s.replace('___PROTECT_EXCLAMATION___', '!') for s in tab[1:]]

    def is_valid(self):
        """Getter for valid attribute

        :return: True if object is valid, False otherwise
        :rtype: bool
        """
        return self.valid

    def get_name(self):
        """Getter for command name attribute

        :return: command name
        :rtype: str
        """
        return getattr(self, 'command_name', 'Unset')
