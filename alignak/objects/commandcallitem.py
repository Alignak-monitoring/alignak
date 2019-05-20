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
""" This module contains only a class for items objects that contains CommandCall objects.
"""

from alignak.objects.item import Items
from alignak.commandcall import CommandCall
from alignak.util import strip_and_uniq


class CommandCallItems(Items):
    """This class provide simple methods to linkify CommandCall object.
    Only object that have CommandCall attribute need those methods (so no need to define it in Item)

    """

    def linkify_with_commands(self, commands, prop, is_a_list=False):
        """
        Link a command to a property (check_command for example)

        :param is_a_list: True if the property contains a list of commands
        :type is_a_list: bool
        :param commands: commands object, the list of all known commands
        :type commands: alignak.objects.command.Commands
        :param prop: property name
        :type prop: str
        :return: None
        """
        for item in self:
            if not getattr(item, prop, None):
                # Set/force a non-existing command
                setattr(item, prop, None)
                continue

            command_name = getattr(item, prop, None)
            if not command_name:
                continue

            if not is_a_list:
                # Set a CommandCall for the command
                setattr(item, prop, self.create_commandcall(item, commands, command_name))
                continue

            setattr(item, prop, [])
            commands_list = command_name
            if not isinstance(commands_list, list):
                commands_list = [commands_list]

            # commands contains the configured commands list,
            # Something like: [check-host-alive-parent!up!$HOSTSTATE:test_router_0$}
            cmds_list = []
            for command_name in commands_list:
                cmds_list.append(self.create_commandcall(item, commands, command_name))

            setattr(item, prop, cmds_list)
            if not is_a_list:
                setattr(item, prop, cmds_list[0])

    @staticmethod
    def create_commandcall(item, commands, command_line):
        """
        Create CommandCall object with command

        :param item: an item concerned with the command
        :type item: alignak.objects.item.Item
        :param commands: all commands
        :type commands: alignak.objects.command.Commands
        :param command_line: a full command line (command and arguments)
        :type command_line: str
        :return: a commandCall object
        :rtype: alignak.objects.commandcallitem.CommandCall
        """
        cc = {
            'command_line': command_line.strip(),
            'commands': commands
        }

        if hasattr(item, 'enable_environment_macros'):
            cc['enable_environment_macros'] = item.enable_environment_macros
        if hasattr(item, 'poller_tag'):
            cc['poller_tag'] = item.poller_tag
        if hasattr(item, 'reactionner_tag'):
            cc['reactionner_tag'] = item.reactionner_tag

        # Force parsing for object creation
        return CommandCall(cc, parsing=True)
