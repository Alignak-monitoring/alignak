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

    def linkify_one_command_with_commands(self, commands, prop):
        """
        Link a command to a property (check_command for example)

        :param commands: commands object
        :type commands: alignak.objects.command.Commands
        :param prop: property name
        :type prop: str
        :return: None
        """
        for i in self:
            if hasattr(i, prop):
                command = getattr(i, prop).strip()
                if command != '':
                    cmdcall = self.create_commandcall(i, commands, command)

                    # TODO: catch None?
                    setattr(i, prop, cmdcall)
                else:
                    setattr(i, prop, None)

    def linkify_command_list_with_commands(self, commands, prop):
        """
        Link a command list (commands with , between) in real CommandCalls

        :param commands: commands object
        :type commands: alignak.objects.command.Commands
        :param prop: property name
        :type prop: str
        :return: None
        """
        for i in self:
            if hasattr(i, prop):
                coms = strip_and_uniq(getattr(i, prop))
                com_list = []
                for com in coms:
                    if com != '':
                        cmdcall = self.create_commandcall(i, commands, com)
                        # TODO: catch None?
                        com_list.append(cmdcall)
                    else:  # TODO: catch?
                        pass
                setattr(i, prop, com_list)

    @staticmethod
    def create_commandcall(prop, commands, command):
        """
        Create commandCall object with command

        :param prop: property
        :type prop: str
        :param commands: all commands
        :type commands: alignak.objects.command.Commands
        :param command: a command object
        :type command: str
        :return: a commandCall object
        :rtype: object
        """
        comandcall = dict(commands=commands, call=command)
        if hasattr(prop, 'enable_environment_macros'):
            comandcall['enable_environment_macros'] = prop.enable_environment_macros

        if hasattr(prop, 'poller_tag'):
            comandcall['poller_tag'] = prop.poller_tag
        elif hasattr(prop, 'reactionner_tag'):
            comandcall['reactionner_tag'] = prop.reactionner_tag

        return CommandCall(comandcall)
