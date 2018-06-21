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
#     aviau, alexandre.viau@savoirfairelinux.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Jan Ulferts, jan.ulferts@xing.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Romain Forlot, rforlot@yahoo.com
#     Christophe SIMON, christophe.simon@dailymotion.com

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
This module provide Command class used to define external commands to
check if something is ok or not
"""

from alignak.objects.item import Item, Items
from alignak.property import StringProp, IntegerProp, BoolProp
from alignak.autoslots import AutoSlots


class Command(Item):
    """
    Class to manage a command
    A command is an external command that a poller module runs to
    check if something is ok or not
    """
    __metaclass__ = AutoSlots

    my_type = "command"

    properties = Item.properties.copy()
    properties.update({
        'command_name':
            StringProp(fill_brok=['full_status']),
        'command_line':
            StringProp(fill_brok=['full_status']),
        'poller_tag':
            StringProp(default=u'None'),
        'reactionner_tag':
            StringProp(default=u'None'),
        'module_type':
            StringProp(default=None),
        'timeout':
            IntegerProp(default=-1),
        'enable_environment_macros':
            BoolProp(default=False),
    })

    def __init__(self, params=None, parsing=True):

        if params is None:
            params = {}
        super(Command, self).__init__(params, parsing=parsing)

        if not hasattr(self, 'timeout'):
            self.timeout = -1

        if not hasattr(self, 'enable_environment_macros'):
            self.enable_environment_macros = False
        if not hasattr(self, 'poller_tag'):
            self.poller_tag = u'None'
        if not hasattr(self, 'reactionner_tag'):
            self.reactionner_tag = u'None'
        if not hasattr(self, 'module_type'):
            # If the command start with a _, set the module_type
            # as the name of the command, without the _
            if getattr(self, 'command_line', '').startswith('_'):
                # For an internal command...
                self.module_type = u'internal'
                # module_type = getattr(self, 'command_line', '').split(' ')[0]
                # # and we remove the first _
                # self.module_type = module_type[1:]
            # If no command starting with _, be fork :)
            else:
                self.module_type = u'fork'

    def get_name(self):
        """
        Get the name of the command

        :return: the command name string
        :rtype: str
        """
        return self.command_name

    def fill_data_brok_from(self, data, brok_type):
        """
        Add properties to data if fill_brok of these class properties
        is same as brok_type

        :param data: dictionnary of this command
        :type data: dict
        :param brok_type: type of brok
        :type brok_type: str
        :return: None
        """
        cls = self.__class__
        # Now config properties
        for prop, entry in list(cls.properties.items()):
            # Is this property intended for broking?
            # if 'fill_brok' in entry[prop]:
            if brok_type in entry.fill_brok:
                if hasattr(self, prop):
                    data[prop] = getattr(self, prop)
                # elif 'default' in entry[prop]:
                #    data[prop] = entry.default

    def is_correct(self):
        """Check if this object configuration is correct ::

        * Check our own specific properties
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """
        state = True

        # _internal_host_check is for having an host check result
        # without running a check plugin
        if self.command_name.startswith('_internal_host_check'):
            # Command line may contain: [state_id][;output]
            parameters = self.command_line.split(';')
            if len(parameters) < 2:
                self.command_name = "_internal_host_check;0;Host assumed to be UP"
                self.add_warning("[%s::%s] has no defined state nor output. Changed to %s"
                                 % (self.my_type, self.command_name, self.command_name))
            elif len(parameters) < 3:
                state = 3
                try:
                    state = int(parameters[1])
                except ValueError:
                    self.add_warning("[%s::%s] required a non integer state: %s. Using 3."
                                     % (self.my_type, self.command_name, parameters[1]))

                if state > 4:
                    self.add_warning("[%s::%s] required an impossible state: %d. Using 3."
                                     % (self.my_type, self.command_name, state))

                output = {0: "UP", 1: "DOWN", 2: "DOWN", 3: "UNKNOWN", 4: "UNREACHABLE", }[state]
                self.command_name = "_internal_host_check;Host assumed to be %s" % output

                self.add_warning("[%s::%s] has no defined output. Changed to %s"
                                 % (self.my_type, self.command_name, self.command_name))
            elif len(parameters) > 3:
                self.command_name = "%s;%s;%s" % (parameters[0], parameters[1], parameters[2])

                self.add_warning("[%s::%s] has too many parameters. Changed to %s"
                                 % (self.my_type, self.command_name, self.command_name))

        return super(Command, self).is_correct() and state


class Commands(Items):
    """
    Class to manage all commands
    A command is an external command the poller module run to
    see if something is ok or not
    """

    inner_class = Command
    name_property = "command_name"
