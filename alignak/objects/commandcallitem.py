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
""" This module contains only a class for items objects that contains CommandCall objects.
"""

import logging

from alignak.objects.item import Items
from alignak.commandcall import CommandCall

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class CommandCallItems(Items):
    """This class provides simple methods to linkify CommandCall object.
    Only object that have CommandCall attribute need those methods (so no need to define it in Item)

    Todo: this class do not have any inner_class like all other classes inheriting from Items ...
    this may probably cause some problems because of missing indexation ... we may probably create
    a fake CommandCallItem class ... to be confirmed!

    """

    def linkify_one_command_with_commands(self, commands, command_name):
        """
        Link a command to a property (check_command for example)

        :param commands: commands object
        :type commands: alignak.objects.command.Commands
        :param command_name: property name for the command
        :type command_name: str
        :return: None
        """
        for item in self:
            if getattr(item, command_name, None) is not None:
                command = getattr(item, command_name)
                if command != '':
                    cmdcall = self.create_commandcall(item, commands, command)

                    setattr(item, command_name, cmdcall)
                else:
                    logger.debug("Command definition not found for: %s / %s"
                                 % (item, command_name))
                    if item.my_type == 'host' and command_name == 'check_command':
                        cmdcall = self.create_commandcall(item, commands, '_internal_host_up')
                        setattr(item, command_name, cmdcall)
                    else:
                        # Undefined command
                        setattr(item, command_name, None)

    def linkify_command_list_with_commands(self, commands, commands_name_list):
        """
        Link a command list (commands with , between) in real CommandCalls

        :param commands: commands object
        :type commands: alignak.objects.command.Commands
        :param commands_name_list: property name for the commands
        :type commands_name_list: str
        :return: None
        """
        for item in self:
            if hasattr(item, commands_name_list):
                commands_list = []
                for command_name in set(getattr(item, commands_name_list)):
                    if command_name != '':
                        cmdcall = self.create_commandcall(item, commands, command_name)
                        commands_list.append(cmdcall)
                setattr(item, commands_name_list, commands_list)

    def create_commandcall(self, item, commands, command):
        """
        Create commandCall object with command for an item

        :param item: item to link the comand with (host, service, ...)
        :type item: str
        :param commands: all commands
        :type commands: alignak.objects.command.Commands
        :param command: a command object
        :type command: str
        :return: a commandCall object
        :rtype: object
        """
        # Todo: a command really needs to have a commands list? What for?
        command_params = {
            'commands': commands,
            'call': command,
            'enable_environment_macros': getattr(item, 'enable_environment_macros', False),
            'reactionner_tag': getattr(item, 'reactionner_tag', ''),
            'poller_tag': getattr(item, 'poller_tag', ''),
            'module_type': getattr(item, 'module_type', ''),
        }

        return CommandCall(command_params)
