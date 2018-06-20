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
#     aviau, alexandre.viau@savoirfairelinux.com
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Christophe Simon, geektophe@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr

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
"""
This module provide CheckModulation and CheckModulations classes used to describe
the modulation of a check command. Modulation occurs on a check period (Timeperiod)
"""
import uuid

from alignak.commandcall import CommandCall
from alignak.objects.item import Item
from alignak.objects.commandcallitem import CommandCallItems
from alignak.property import StringProp
from alignak.util import to_name_if_possible


class CheckModulation(Item):
    """CheckModulation class is simply a modulation of the check command (of a Host/Service)
    during a check_period.

    """
    my_type = 'checkmodulation'

    properties = Item.properties.copy()
    properties.update({
        'checkmodulation_name':
            StringProp(fill_brok=['full_status']),
        'check_command':
            StringProp(fill_brok=['full_status']),
        'check_period':
            StringProp(brok_transformation=to_name_if_possible, fill_brok=['full_status']),
    })

    running_properties = Item.running_properties.copy()

    special_properties = ('check_period',)

    macros = {}

    def __init__(self, params=None, parsing=True):
        if params is None:
            params = {}

        # At deserialization, thoses are dict
        # TODO: Separate parsing instance from recreated ones
        if 'check_command' in params and isinstance(params['check_command'], dict):
            # We recreate the object
            self.check_command = CommandCall(params['check_command'])
            # And remove prop, to prevent from being overridden
            del params['check_command']

        super(CheckModulation, self).__init__(params, parsing=parsing)

    def serialize(self):
        res = super(CheckModulation, self).serialize()
        res['check_command'] = None
        if getattr(self, 'check_command', None):
            res['check_command'] = self.check_command.serialize()
        return res

    def get_name(self):
        """Accessor to checkmodulation_name attribute

        :return: check modulation name
        :rtype: str
        """
        if hasattr(self, 'checkmodulation_name'):
            return self.checkmodulation_name
        return 'Unnamed'

    def get_check_command(self, timeperiods, t_to_go):
        """Get the check_command if we are in the check period modulation

        :param t_to_go: time to check if we are in the timeperiod
        :type t_to_go:
        :return: A check command if we are in the check period, None otherwise
        :rtype: alignak.objects.command.Command
        """
        if not self.check_period or timeperiods[self.check_period].is_time_valid(t_to_go):
            return self.check_command
        return None

    def is_correct(self):
        """Check if this object configuration is correct ::

        * Check our own specific properties
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """
        state = True

        # Internal checks before executing inherited function...
        if not hasattr(self, 'check_command'):
            msg = "[checkmodulation::%s] do not have any check_command defined" % (
                self.get_name()
            )
            self.add_error(msg)
            state = False
        else:
            if self.check_command is None:
                msg = "[checkmodulation::%s] a check_command is missing" % (self.get_name())
                self.add_error(msg)
                state = False
            if self.check_command and not self.check_command.is_valid():
                msg = "[checkmodulation::%s] a check_command is invalid" % (self.get_name())
                self.add_error(msg)
                state = False

        # Ok just put None as check_period, means 24x7
        if not hasattr(self, 'check_period'):
            self.check_period = None

        return super(CheckModulation, self).is_correct() and state


class CheckModulations(CommandCallItems):
    """CheckModulations class allowed to handle easily several CheckModulation objects

    """
    name_property = "checkmodulation_name"
    inner_class = CheckModulation

    def linkify(self, timeperiods, commands):
        """Replace check_period by real Timeperiod object into each CheckModulation
        Replace check_command by real Command object into each CheckModulation

        :param timeperiods: timeperiods to link to
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param commands: commands to link to
        :type commands: alignak.objects.command.Commands
        :return: None
        """
        self.linkify_with_timeperiods(timeperiods, 'check_period')
        self.linkify_one_command_with_commands(commands, 'check_command')

    def new_inner_member(self, name=None, params=None):
        """Create a CheckModulation object and add it to items

        :param name: CheckModulation name
        :type name: str
        :param params: parameters to init CheckModulation
        :type params: dict
        :return: None
        TODO: Remove this default mutable argument. Usually result in unexpected behavior
        """
        if name is None:
            name = 'Generated_checkmodulation_%s' % uuid.uuid4()

        if params is None:
            params = {}

        params['checkmodulation_name'] = name
        checkmodulation = CheckModulation(params)
        self.add_item(checkmodulation)
