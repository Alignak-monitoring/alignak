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
        # Initial command line in the configuration
        'command_line':
            StringProp(),
        # Command line split: name and arguments
        'command_name':
            StringProp(),
        'args':
            ListProp(default=[]),
        # alignak.objects.Command
        'command':
            StringProp(default=u''),
        'poller_tag':
            StringProp(default=u''),
        'reactionner_tag':
            StringProp(default=u''),
        'module_type':
            StringProp(default=u'fork'),
        'valid':
            BoolProp(default=True),
        'timeout':
            IntegerProp(default=-1),
        'enable_environment_macros':
            BoolProp(default=False),
    }

    # pylint: disable=too-many-branches
    def __init__(self, params, parsing=False):
        """
        Note: A CommandCall may receive 'commands' in its parameters; it is the whole
        known commands list in which the command must be found.

        If no commands list is provided, the CommandCall is initialized with the provided
        parameters that must contain one Command.

        :param params:
        """
        if params is None:
            params = {}

        if not parsing:
            # Deserialize an existing object
            # todo: Why not initializing the running properties in this case?
            super(CommandCall, self).__init__(params, parsing=parsing)
            return

        # List of known commands
        commands = None
        if 'commands' in params:
            commands = params.pop('commands')

        # Create a base command call
        super(CommandCall, self).__init__(params, parsing=parsing)

        if parsing:
            # Fill default object values from the properties
            self.fill_default()

            # fixme: why not inheriting from Item?
            # This is a minimum copy of the Item class initialization!
            for key in params:
                try:
                    if key in self.__class__.properties:
                        val = self.__class__.properties[key].pythonize(params[key])
                    else:
                        val = ToGuessProp().pythonize(params[key])
                except (PythonizeError, AttributeError, ValueError, TypeError) as exp:
                    raise PythonizeError("Error while pythonizing parameter '%s': %s" % (key, exp))

                setattr(self, key, val)

        # Get command and arguments
        self.command_name, self.args = self.get_command_and_args()

        # todo: remove this... 1/ unserialize should have handled and 2/ we should not even be here!
        if not parsing:
            # Link the provided Alignak command with myself
            self.command = unserialize(params['command'])

        # We received a commands list to search into...
        if commands:
            self.valid = False
            self.command = commands.find_by_name(self.command_name)
            if self.command is not None:
                # Found a declared command
                self.valid = True
                # Get the host/service poller/reactionner tag,
                # else the ones defined in the command
                if self.poller_tag in [None, 'None', '']:
                    self.poller_tag = self.command.poller_tag
                # Same for reactionner tag
                if self.reactionner_tag in [None, 'None', '']:
                    self.reactionner_tag = self.command.reactionner_tag

                self.module_type = self.command.module_type
                self.enable_environment_macros = self.command.enable_environment_macros
                self.timeout = int(self.command.timeout)

    def __str__(self):  # pragma: no cover
        return "<CommandCall %s, uuid=%s, command line: %s />" \
               % (self.get_name(), self.uuid, getattr(self, 'command_line', None))
    __repr__ = __str__

    def serialize(self, no_json=True, printing=False):
        # uuid is not in *_properties
        res = {'uuid': self.uuid}
        for prop in self.__class__.properties:
            try:
                res[prop] = serialize(getattr(self, prop),
                                      no_json=no_json, printing=printing)
            except AttributeError:
                pass
        # for prop in self.__class__.properties:
        #     if prop in ['command']:
        #         # Specific for the command (alignak.objects.command.Command object)
        #         res[prop] = serialize(getattr(self, prop),
        #                               no_json=no_json, printing=printing)
        #     elif hasattr(self, prop):
        #         res[prop] = getattr(self, prop)
        return res

    def get_command_and_args(self):
        """We want to get the command and the args with ! splitting.
        but don't forget to protect against the ! to avoid splitting on them

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
