#!/usr/bin/env python
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
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Jean Gabes, naparuba@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
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

#
# This file is used to test commands
#

from alignak_test import unittest, AlignakTest

from alignak.commandcall import CommandCall
from alignak.objects import Command, Commands


class TestCommand(AlignakTest):
    """
    This class tests the commands
    """

    def test_command_no_parameters(self):
        """ Test command without parameters

        :return: None
        """
        self.print_header()

        # No parameters
        c = Command()
        # No command_name nor command_line attribute exist!
        # Todo: __init__ may raise an exception because of this, no?
        self.assertIsNone(getattr(c, 'command_name', None))
        self.assertIsNone(getattr(c, 'command_line', None))

        self.assertEqual(c.poller_tag, 'None')
        self.assertEqual(c.reactionner_tag, 'None')
        self.assertEqual(c.timeout, -1)
        self.assertEqual(c.module_type, 'fork')
        self.assertEqual(c.enable_environment_macros, False)

        b = c.get_initial_status_brok()
        self.assertEqual('initial_command_status', b.type)
        self.assertNotIn('command_name', b.data)
        self.assertNotIn('command_line', b.data)

    def test_command_internal(self):
        """ Test internal command

        :return: None
        """
        self.print_header()

        t = {
            'command_name': '_internal_host_up',
            'command_line': '_internal_host_up'
        }
        c = Command(t)

        self.assertEqual(c.command_name, '_internal_host_up')
        self.assertEqual(c.get_name(), '_internal_host_up')
        self.assertEqual(c.command_line, '_internal_host_up')

        self.assertEqual(c.poller_tag, 'None')
        self.assertEqual(c.reactionner_tag, 'None')
        self.assertEqual(c.timeout, -1)
        # Module type is the command name without the '_' prefix
        self.assertEqual(c.module_type, 'internal_host_up')
        self.assertEqual(c.enable_environment_macros, False)

        b = c.get_initial_status_brok()
        self.assertEqual('initial_command_status', b.type)
        self.assertIn('command_name', b.data)
        self.assertIn('command_line', b.data)

    def test_command_build(self):
        """ Test command build

        :return: None
        """
        self.print_header()

        t = {
            'command_name': 'check_command_test',
            'command_line': '/tmp/dummy_command.sh $ARG1$ $ARG2$',
            'module_type': 'nrpe-booster',
            'poller_tag': 'DMZ',
            'reactionner_tag': 'REAC'
        }
        c = Command(t)

        self.assertEqual(c.command_name, 'check_command_test')
        self.assertEqual(c.get_name(), 'check_command_test')
        self.assertEqual(c.command_line, '/tmp/dummy_command.sh $ARG1$ $ARG2$')

        self.assertEqual(c.poller_tag, 'DMZ')
        self.assertEqual(c.reactionner_tag, 'REAC')
        self.assertEqual(c.timeout, -1)
        self.assertEqual(c.module_type, 'nrpe-booster')
        self.assertEqual(c.enable_environment_macros, False)

        b = c.get_initial_status_brok()
        self.assertEqual('initial_command_status', b.type)
        self.assertIn('command_name', b.data)
        self.assertIn('command_line', b.data)

    def test_commands_pack(self):
        """ Test commands pack build

        :return: None
        """
        self.print_header()

        t = {
            'command_name': 'check_command_test',
            'command_line': '/tmp/dummy_command.sh $ARG1$ $ARG2$',
            'module_type': 'nrpe-booster',
            'poller_tag': 'DMZ',
            'reactionner_tag': 'REAC'
        }
        c = Command(t)

        # now create a commands packs
        cs = Commands([c])
        dummy_call = "check_command_test!titi!toto"
        cc = CommandCall({"commands": cs, "call": dummy_call})
        self.assertEqual(True, cc.is_valid())
        self.assertEqual(c, cc.command)
        self.assertEqual('DMZ', cc.poller_tag)
        self.assertEqual('REAC', cc.reactionner_tag)

if __name__ == '__main__':
    unittest.main()
