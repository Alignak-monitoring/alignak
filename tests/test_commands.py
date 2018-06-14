#!/usr/bin/env python
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

from .alignak_test import AlignakTest

from alignak.commandcall import CommandCall
from alignak.objects import Command, Commands


class TestCommand(AlignakTest):
    """
    This class tests the commands
    """

    def setUp(self):
        super(TestCommand, self).setUp()

        self.setup_with_file('cfg/cfg_commands.cfg', verbose=False)
        assert self.conf_is_correct

        # Our scheduler
        self._sched = self._scheduler

    def test_css_in_commands(self):
        """ Test CSS and HTML in command """
        pass

        # The test is implicit because the configuration got loaded!

    def test_semi_colon_in_commands(self):
        """Test semi-colon in commands """
        # Our scheduler
        self._sched = self._scheduler

        # Get the hosts and services"
        host = self._sched.hosts.find_by_name("test_host_0")
        assert host is not None
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "svc_semi_colon")
        assert svc is not None

        svc.get_event_handlers(self._sched.hosts, self._sched.macromodulations,
                               self._sched.timeperiods)
        assert len(svc.actions) == 1
        for action in svc.actions:
            assert action.is_a == 'eventhandler'
            assert action.command == '/test_eventhandler.pl sudo -s pkill toto ; cd /my/path && ./exec'

    def test_spaces_in_commands(self):
        """Test spaces in commands """
        # Our scheduler
        self._sched = self._scheduler

        # Get the hosts and services"
        host = self._sched.hosts.find_by_name("test_host_0")
        assert host is not None
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "svc_spaces")
        assert svc is not None

        # Schedule checks
        svc.schedule(self._sched.hosts, self._sched.services, self._sched.timeperiods,
                     self._sched.macromodulations, self._sched.checkmodulations, self._sched.checks)
        assert len(svc.actions) == 1
        for action in svc.actions:
            assert action.is_a == 'check'
            assert action.command == '/check_snmp_int.pl -H 127.0.0.1 -C public ' \
                                     '-n "Nortel Ethernet Routing Switch 5530-24TFD ' \
                                     'Module - Port 2          " ' \
                                     '-r -f -k -Y -B -w "90000,90000" -c "120000,120000"'
            # Run checks now
            action.t_to_go = 0

        # the scheduler need to get this new checks in its own queues
        self._sched.get_new_actions()
        untagged_checks = self._sched.get_to_run_checks(True, False, poller_tags=['None'])
        assert len(untagged_checks) == 1
        for check in untagged_checks:
            assert check.is_a == 'check'
            assert check.command == '/check_snmp_int.pl -H 127.0.0.1 -C public ' \
                                    '-n "Nortel Ethernet Routing Switch 5530-24TFD ' \
                                    'Module - Port 2          " ' \
                                    '-r -f -k -Y -B -w "90000,90000" -c "120000,120000"'

    def test_command_no_parameters(self):
        """ Test command without parameters

        :return: None
        """
        # No parameters
        c = Command()
        # No command_name nor command_line attribute exist!
        # Todo: __init__ may raise an exception because of this, no?
        assert getattr(c, 'command_name', None) is None
        assert getattr(c, 'command_line', None) is None

        assert c.poller_tag == 'None'
        assert c.reactionner_tag == 'None'
        assert c.timeout == -1
        assert c.module_type == 'fork'
        assert c.enable_environment_macros == False

        b = c.get_initial_status_brok()
        assert 'initial_command_status' == b.type
        assert 'command_name' not in b.data
        assert 'command_line' not in b.data

    def test_command_with_tags(self):
        """ Test command with poller/reactionner tag

        :return: None
        """
        # Get a command
        c = self._sched.commands.find_by_name("command_poller_tag")
        assert c is not None
        assert c.poller_tag == 'tag1'
        assert c.reactionner_tag == 'None'

        # Get a command
        c = self._sched.commands.find_by_name("command_reactionner_tag")
        assert c is not None
        assert c.poller_tag == 'None'
        assert c.reactionner_tag == 'tag2'

    def test_command_internal_host_up(self):
        """ Test internal command _internal_host_up

        :return: None
        """
        t = {
            'command_name': '_internal_host_up',
            'command_line': '_internal_host_up'
        }
        c = Command(t)

        assert c.command_name == '_internal_host_up'
        assert c.get_name() == '_internal_host_up'
        assert c.command_line == '_internal_host_up'

        assert c.poller_tag == 'None'
        assert c.reactionner_tag == 'None'
        assert c.timeout == -1
        # Module type is the command name without the '_' prefix
        assert c.module_type == 'internal'
        assert c.enable_environment_macros == False

        b = c.get_initial_status_brok()
        assert 'initial_command_status' == b.type
        assert 'command_name' in b.data
        assert 'command_line' in b.data

    def test_command_internal_echo(self):
        """ Test internal command _echo

        :return: None
        """
        t = {
            'command_name': '_echo',
            'command_line': '_echo'
        }
        c = Command(t)

        assert c.command_name == '_echo'
        assert c.get_name() == '_echo'
        assert c.command_line == '_echo'

        assert c.poller_tag == 'None'
        assert c.reactionner_tag == 'None'
        assert c.timeout == -1
        # Module type is the command name without the '_' prefix
        assert c.module_type == 'internal'
        assert c.enable_environment_macros == False

        b = c.get_initial_status_brok()
        assert 'initial_command_status' == b.type
        assert 'command_name' in b.data
        assert 'command_line' in b.data

    def test_command_build(self):
        """ Test command build

        :return: None
        """
        t = {
            'command_name': 'check_command_test',
            'command_line': '/tmp/dummy_command.sh $ARG1$ $ARG2$',
            'module_type': 'nrpe-booster',
            'poller_tag': 'DMZ',
            'reactionner_tag': 'REAC'
        }
        c = Command(t)

        assert c.command_name == 'check_command_test'
        assert c.get_name() == 'check_command_test'
        assert c.command_line == '/tmp/dummy_command.sh $ARG1$ $ARG2$'

        assert c.poller_tag == 'DMZ'
        assert c.reactionner_tag == 'REAC'
        assert c.timeout == -1
        assert c.module_type == 'nrpe-booster'
        assert c.enable_environment_macros == False

        b = c.get_initial_status_brok()
        assert 'initial_command_status' == b.type
        assert 'command_name' in b.data
        assert 'command_line' in b.data

    def test_commands_pack(self):
        """ Test commands pack build

        :return: None
        """
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
        assert True == cc.is_valid()
        assert c == cc.command
        assert 'DMZ' == cc.poller_tag
        assert 'REAC' == cc.reactionner_tag
