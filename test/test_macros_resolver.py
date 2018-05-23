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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.macros_command
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.macros_command
#     Zoran Zaric, zz@zoranzaric.de
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

#
# This file is used to test reading and processing of config files
#

from .alignak_test import *
from alignak.macroresolver import MacroResolver
from alignak.commandcall import CommandCall


class MacroResolverTester(object):
    """Test without enabled environment macros"""
    def get_mr(self):
        """ Get an initialized macro resolver object """
        mr = MacroResolver()
        mr.init(self._scheduler.pushed_conf)
        return mr

    def get_hst_svc(self):
        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0"
        )
        hst = self._scheduler.hosts.find_by_name("test_host_0")
        return (svc, hst)

    def test_resolv_simple(self):
        """Test a simple macro resolution
        :return:
        """
        mr = self.get_mr()

        # This is a macro built from a variable
        result = mr.resolve_simple_macros_in_string("$ALIGNAK$", [], None, None, None)
        assert result == "My Alignak"

        # This is a macro built from a dynamic variable
        result = mr.resolve_simple_macros_in_string("$MAINCONFIGFILE$", [], None, None, None)
        assert result == "/home/alignak/alignak/test/cfg/alignak.ini"
        result = mr.resolve_simple_macros_in_string("$MAINCONFIGDIR$", [], None, None, None)
        assert result == "/home/alignak/alignak/test/cfg"

        # This is a deprecated macro -> n/a
        result = mr.resolve_simple_macros_in_string("$COMMENTDATAFILE$", [], None, None, None)
        assert result == "n/a"

        # This is a macro built from an Alignak variable - because the variable is prefixed with _
        result = mr.resolve_simple_macros_in_string("$_DIST$", [], None, None, None)
        assert result == "/tmp"
        # Alignak variable interpolated from %(var) is available as a macro
        result = mr.resolve_simple_macros_in_string("$_DIST_ETC$", [], None, None, None)
        assert result == "/tmp/etc/alignak"

        # Alignak "standard" variable is not available as a macro
        # Empty value ! todo: Perharps should be changed ?
        result = mr.resolve_simple_macros_in_string("$USER$", [], None, None, None)
        assert result == ""

    def test_resolv_simple_command(self):
        """Test a simple command resolution
        :return:
        """
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        macros_command = mr.resolve_command(svc.check_command, data,
                                 self._scheduler.macromodulations,
                                 self._scheduler.timeperiods)
        assert macros_command == "plugins/test_servicecheck.pl --type=ok --failchance=5% " \
                              "--previous-state=OK --state-duration=0 " \
                              "--total-critical-on-host=0 --total-warning-on-host=0 " \
                              "--hostname test_host_0 --servicedesc test_ok_0"

    def test_args_macro(self):
        """
        Test ARGn macros
        :return:
        """
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]

        # command_with_args is defined with 5 arguments as:
        # $PLUGINSDIR$/command -H $HOSTADDRESS$ -t 9 -u -c $ARG1$
        # -a $ARG2$ $ARG3$ $ARG4$ and the last is $ARG5$.

        # No arguments are provided - will be valued as empty strings
        dummy_call = "command_with_args"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert macros_command == \
                         'plugins/command -H 127.0.0.1 -t 9 -u -c  ' \
                         '-a    and the last is .'

        # Extra arguments are provided - will be ignored
        dummy_call = "command_with_args!arg_1!arg_2!arg_3!arg_4!arg_5!extra argument"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert macros_command == \
                         'plugins/command -H 127.0.0.1 -t 9 -u -c arg_1 ' \
                         '-a arg_2 arg_3 arg_4 and the last is arg_5.'

        # All arguments are provided
        dummy_call = "command_with_args!arg_1!arg_2!arg_3!arg_4!arg_5"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data,  self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert macros_command == \
                         'plugins/command -H 127.0.0.1 -t 9 -u -c arg_1 ' \
                         '-a arg_2 arg_3 arg_4 and the last is arg_5.'

    def test_datetime_macros(self):
        """ Test date / time macros: SHORTDATETIME, LONGDATETIME, DATE, TIME, ...

        :return:
        """
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        hst.state = 'UP'

        # Long and short datetime
        dummy_call = "special_macro!$LONGDATETIME$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        dummy_call = "special_macro!$SHORTDATETIME$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        dummy_call = "special_macro!$DATE$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        dummy_call = "special_macro!$TIME$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        dummy_call = "special_macro!$TIMET$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        # Do not check that the output of these macro is correct
        # because there is no specific macro code for those functions ;)

        # Process and event start time
        dummy_call = "special_macro!$PROCESSSTARTTIME$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing n/a' == macros_command
        dummy_call = "special_macro!$EVENTSTARTTIME$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing n/a' == macros_command

    def test_summary_macros(self):
        """ Test summary macros: TOTALHOSTSUP, TOTALHOSTDOWN, ...

        :return:
        """
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        hst.state = 'UP'

        # Number of hosts UP / DOWN / UNREACHABLE
        dummy_call = "special_macro!$TOTALHOSTSUP$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        # All 3 hosts are UP
        assert 'plugins/nothing 3' == macros_command
        dummy_call = "special_macro!$TOTALHOSTPROBLEMS$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command
        dummy_call = "special_macro!$TOTALHOSTPROBLEMSUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command

        # Now my host is DOWN and not yet handled
        hst.state = 'DOWN'
        hst.is_problem = True
        hst.problem_has_been_acknowledged = False
        dummy_call = "special_macro!$TOTALHOSTSDOWN$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command
        dummy_call = "special_macro!$TOTALHOSTSDOWNUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command
        # Now my host is DOWN but handled
        hst.problem_has_been_acknowledged = True
        dummy_call = "special_macro!$TOTALHOSTSDOWNUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command

        # Now my host is UNREACHABLE and not yet handled
        hst.state = 'UNREACHABLE'
        hst.is_problem = True
        hst.problem_has_been_acknowledged = False
        dummy_call = "special_macro!$TOTALHOSTSUNREACHABLE$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command
        dummy_call = "special_macro!$TOTALHOSTSUNREACHABLEUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command
        # Now my host is UNREACHABLE but handled
        hst.problem_has_been_acknowledged = True
        dummy_call = "special_macro!$TOTALHOSTSUNREACHABLEUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command

        # Now my host is DOWN and not yet handled
        hst.state = 'DOWN'
        hst.is_problem = True
        hst.problem_has_been_acknowledged = False
        dummy_call = "special_macro!$TOTALHOSTPROBLEMS$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command
        dummy_call = "special_macro!$TOTALHOSTPROBLEMSUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command

        # Now my host is UP and no more a problem
        hst.state = 'UP'
        hst.is_problem = False
        hst.problem_has_been_acknowledged = False
        dummy_call = "special_macro!$TOTALHOSTPROBLEMS$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command
        dummy_call = "special_macro!$TOTALHOSTPROBLEMSUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command

        # Number of services OK / WARNING / CRITICAL / UNKNOWN
        dummy_call = "special_macro!$TOTALSERVICESOK$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 2' == macros_command

        # Now my service is WARNING and not handled
        svc.state = 'WARNING'
        svc.is_problem = True
        svc.problem_has_been_acknowledged = False
        dummy_call = "special_macro!$TOTALSERVICESWARNING$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command
        dummy_call = "special_macro!$TOTALSERVICESWARNINGUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command
        # Now my service problem is handled
        svc.problem_has_been_acknowledged = True
        dummy_call = "special_macro!$TOTALSERVICESWARNINGUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command

        # Now my service is CRITICAL and not handled
        svc.state = 'CRITICAL'
        svc.is_problem = True
        svc.problem_has_been_acknowledged = False
        dummy_call = "special_macro!$TOTALSERVICESCRITICAL$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command
        dummy_call = "special_macro!$TOTALSERVICESCRITICALUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command
        # Now my service problem is handled
        svc.problem_has_been_acknowledged = True
        dummy_call = "special_macro!$TOTALSERVICESCRITICALUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command

        # Now my service is UNKNOWN and not handled
        svc.state = 'UNKNOWN'
        svc.is_problem = True
        svc.problem_has_been_acknowledged = False
        dummy_call = "special_macro!$TOTALSERVICESUNKNOWN$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command
        dummy_call = "special_macro!$TOTALSERVICESUNKNOWNUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command
        # Now my service problem is handled
        svc.problem_has_been_acknowledged = True
        dummy_call = "special_macro!$TOTALSERVICESUNKNOWNUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command

        # Now my service is WARNING and not handled
        svc.state = 'WARNING'
        svc.is_problem = True
        svc.problem_has_been_acknowledged = False
        dummy_call = "special_macro!$TOTALSERVICEPROBLEMS$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command
        dummy_call = "special_macro!$TOTALSERVICEPROBLEMSUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command

        # Now my service is OK and no more a problem
        svc.state = 'OK'
        svc.is_problem = False
        svc.problem_has_been_acknowledged = False
        dummy_call = "special_macro!$TOTALSERVICEPROBLEMS$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command
        dummy_call = "special_macro!$TOTALSERVICEPROBLEMSUNHANDLED$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command

    def test_special_macros_realm(self):
        """
        Call the resolver with a special macro HOSTREALM
        :return:
        """
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        hst.state = 'UP'
        dummy_call = "special_macro!$HOSTREALM$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        # Macro raised the default realm (All)
        assert 'plugins/nothing All' == macros_command

    def test_escape_macro(self):
        """
        Call the resolver with an empty macro ($$)
        :return:
        """
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        hst.state = 'UP'
        dummy_call = "special_macro!$$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        # Not a macro but $$ is transformed as $
        assert 'plugins/nothing $' == macros_command

    def test_unicode_macro(self):
        """
        Call the resolver with a unicode content
        :return:
        """
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]

        hst.state = 'UP'
        hst.output = u"На берегу пустынных волн"
        dummy_call = "special_macro!$HOSTOUTPUT$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        # Output is correctly restitued
        assert u'plugins/nothing На берегу пустынных волн' == macros_command


        hst.state = 'UP'
        hst.output = 'Père Noël'
        dummy_call = "special_macro!$HOSTOUTPUT$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        # Output is correctly restitued
        assert u'plugins/nothing Père Noël' == macros_command

        hst.state = 'UP'
        hst.output = 'Père Noël'
        dummy_call = "special_macro!$HOSTOUTPUT$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        # Output is correctly restitued
        assert u'plugins/nothing Père Noël' == macros_command

    def test_illegal_macro_output_chars(self):
        """ Check output macros are cleaned from illegal macro characters

        $HOSTOUTPUT$, $HOSTPERFDATA$, $HOSTACKAUTHOR$, $HOSTACKCOMMENT$,
        $SERVICEOUTPUT$, $SERVICEPERFDATA$, $SERVICEACKAUTHOR$, $SERVICEACKCOMMENT$
        """
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        illegal_macro_output_chars = \
            self._scheduler.pushed_conf.illegal_macro_output_chars
        print("Illegal macros caracters:", illegal_macro_output_chars)
        hst.output = 'fake output'
        dummy_call = "special_macro!$HOSTOUTPUT$"

        for c in illegal_macro_output_chars:
            hst.output = 'fake output' + c
            cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
            macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                                self._scheduler.timeperiods)
            print(macros_command)
            assert 'plugins/nothing fake output' == macros_command

    def test_env_macros(self):
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        data.append(self._arbiter.conf)

        env = mr.get_env_macros(data)
        assert env != {}
        assert 'test_host_0' == env['NAGIOS_HOSTNAME']
        assert 0.0 == env['NAGIOS_SERVICEPERCENTCHANGE']
        assert 'custvalue' == env['NAGIOS__SERVICECUSTNAME']
        assert 'gnulinux' == env['NAGIOS__HOSTOSTYPE']
        assert 'NAGIOS_USER1' not in env

    def test_resource_file(self):
        """
        Test macros defined in configuration files
        :return:
        """
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]

        # $USER1$ macro is defined as 'plugins' in the configuration file
        dummy_call = "special_macro!$USER1$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing plugins' == macros_command

        # $PLUGINSDIR$ macro is defined as $USER1$ in the configuration file
        dummy_call = "special_macro!$PLUGINSDIR$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing plugins' == macros_command

        # $INTERESTINGVARIABLE$ macro is defined as 'interesting_value' in the configuration file
        dummy_call = "special_macro!$INTERESTINGVARIABLE$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing interesting_value' == macros_command

        # Look for multiple = in lines, should split the first
        # and keep others in the macro value
        dummy_call = "special_macro!$ANOTHERVALUE$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing first=second' == macros_command

    def test_ondemand_macros(self):
        """Test on-demand macros
        :return:
        """
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        hst.state = 'UP'
        svc.state = 'UNKNOWN'

        # Get another service
        svc2 = self._scheduler.pushed_conf.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_another_service"
        )
        svc2.output = 'you should not pass'

        # Request a not existing macro
        dummy_call = "special_macro!$HOSTXXX:test_host_0$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing' == macros_command

        # Request a specific host state
        dummy_call = "special_macro!$HOSTSTATE:test_host_0$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing UP' == macros_command

        # Call with a void host name, means : myhost
        data = [hst]
        dummy_call = "special_macro!$HOSTSTATE:$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing UP' == macros_command

        # Now with a service, for our implicit host state
        data = [hst, svc]
        dummy_call = "special_macro!$HOSTSTATE:test_host_0$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing UP' == macros_command
                                                        
        # Now with a service, for our implicit host state (missing host ...)
        data = [hst, svc]
        dummy_call = "special_macro!$HOSTSTATE:$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing UP' == macros_command

        # Now call this data from our previous service - get service state
        data = [hst, svc2]
        dummy_call = "special_macro!$SERVICESTATE:test_host_0:test_another_service$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing OK' == macros_command

        # Now call this data from our previous service - get service output
        data = [hst, svc2]
        dummy_call = "special_macro!$SERVICEOUTPUT:test_host_0:test_another_service$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing you should not pass' == macros_command

        # Ok now with a host implicit way
        svc2.output = 'you should not pass'
        data = [hst, svc2]
        dummy_call = "special_macro!$SERVICEOUTPUT::test_another_service$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing you should not pass' == macros_command

    def test_host_macros(self):
        """Test host macros
        :return:
        """
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]

        # First group name
        dummy_call = "special_macro!$HOSTGROUPNAME$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert macros_command == 'plugins/nothing allhosts'

        # All group names
        dummy_call = "special_macro!$HOSTGROUPNAMES$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert macros_command == 'plugins/nothing allhosts,hostgroup_01,up'

        # First group alias
        dummy_call = "special_macro!$HOSTGROUPALIAS$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert macros_command == 'plugins/nothing All Hosts'

        # All group aliases
        dummy_call = "special_macro!$HOSTGROUPALIASES$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert macros_command == 'plugins/nothing All Hosts,All Up Hosts,hostgroup_alias_01'

    def test_host_count_services_macros(self):
        """Test services count for an hostmacros
        :return:
        """
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        hst.state = 'UP'

        # Get another service
        svc2 = self._scheduler.pushed_conf.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_another_service"
        )
        svc2.output = 'you should not pass'

        # Total
        svc.output = 'you should not pass'
        data = [hst, svc]
        dummy_call = "special_macro!$TOTALHOSTSERVICES$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 2' == macros_command

        # Services states
        svc.state_id = 0
        svc.state = 'OK'
        svc2.state_id = 1
        svc2.state = 'WARNING'

        # Ok
        svc.output = 'you should not pass'
        data = [hst, svc]
        dummy_call = "special_macro!$TOTALHOSTSERVICESOK$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command

        # Warning
        svc.output = 'you should not pass'
        data = [hst, svc]
        dummy_call = "special_macro!$TOTALHOSTSERVICESWARNING$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command

        # Critical
        svc.output = 'you should not pass'
        data = [hst, svc]
        dummy_call = "special_macro!$TOTALHOSTSERVICESCRITICAL$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command

        # Unknown
        svc.output = 'you should not pass'
        data = [hst, svc]
        dummy_call = "special_macro!$TOTALHOSTSERVICESUNKNOWN$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command

        # Unreachable
        svc.output = 'you should not pass'
        data = [hst, svc]
        dummy_call = "special_macro!$TOTALHOSTSERVICESUNREACHABLE$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command

        # Change states
        svc.state_id = 2
        svc.state = 'CRITICAL'
        svc2.state_id = 3
        svc2.state = 'UNKNOWN'

        # Ok
        svc.output = 'you should not pass'
        data = [hst, svc]
        dummy_call = "special_macro!$TOTALHOSTSERVICESOK$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command

        # Warning
        svc.output = 'you should not pass'
        data = [hst, svc]
        dummy_call = "special_macro!$TOTALHOSTSERVICESWARNING$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command

        # Critical
        svc.output = 'you should not pass'
        data = [hst, svc]
        dummy_call = "special_macro!$TOTALHOSTSERVICESCRITICAL$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command

        # Unknown
        svc.output = 'you should not pass'
        data = [hst, svc]
        dummy_call = "special_macro!$TOTALHOSTSERVICESUNKNOWN$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 1' == macros_command

        # Unreachable
        svc.output = 'you should not pass'
        data = [hst, svc]
        dummy_call = "special_macro!$TOTALHOSTSERVICESUNREACHABLE$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 0' == macros_command

    def test_contact_custom_macros(self):
        """
        Test on-demand macros with custom variables for contacts
        :return:
        """
        mr = self.get_mr()

        contact = self._scheduler.contacts.find_by_name("test_macro_contact")
        data = [contact]

        # Parse custom macro to get contact custom variables based upon a fixed value
        # contact has a custom variable defined as _custom1 = value
        dummy_call = "special_macro!$_CONTACTCUSTOM1$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing value' == macros_command

        # Parse custom macro to get service custom variables based upon another macro
        # host has a custom variable defined as _custom2 = $CONTACTNAME$
        dummy_call = "special_macro!$_CONTACTCUSTOM2$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing test_macro_contact' == macros_command

    def test_host_custom_macros(self):
        """
        Test on-demand macros with custom variables for hosts
        :return:
        """
        mr = self.get_mr()

        hst = self._scheduler.hosts.find_by_name("test_macro_host")
        # The host has custom variables, thus we may use them in a macro
        assert hst.customs is not []
        assert '_CUSTOM1' in hst.customs
        assert '_CUSTOM2' in hst.customs
        # Force declare an integer customs variable
        hst.customs['_CUSTOM3'] = 10
        print((hst.customs))
        data = [hst]

        # Parse custom macro to get host custom variables based upon a fixed value
        # host has a custom variable defined as _custom1 = value
        dummy_call = "special_macro!$_HOSTCUSTOM1$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing value' == macros_command

        # Parse custom macro to get host custom variables based upon another macro
        # host has a custom variable defined as _custom2 = $HOSTNAME$
        dummy_call = "special_macro!$_HOSTCUSTOM2$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing test_macro_host' == macros_command

        # Parse custom macro to get host custom variables based upon another macro
        # host has a custom variable defined as _custom2 = $HOSTNAME$
        dummy_call = "special_macro!$_HOSTCUSTOM3$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        print(("Command: %s" % macros_command))
        assert 'plugins/nothing 10' == macros_command

    def test_service_custom_macros(self):
        """
        Test on-demand macros with custom variables for services
        :return:
        """
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()

        # Get the second service
        svc2 = self._arbiter.conf.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_another_service"
        )
        data = [hst, svc2]

        # Parse custom macro to get service custom variables based upon a fixed value
        # special_macro is defined as: $USER1$/nothing $ARG1$
        dummy_call = "special_macro!$_SERVICECUSTOM1$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing value' == macros_command

        # Parse custom macro to get service custom variables based upon another macro
        dummy_call = "special_macro!$_SERVICECUSTOM2$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing test_host_0' == macros_command

    def test_hostadressX_macros(self):
        """
        Host addresses macros
        :return:
        """
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]

        # Ok sample host call
        dummy_call = "special_macro!$HOSTADDRESS$"
        cc = CommandCall({"commands": self._arbiter.conf.commands, "call": dummy_call})
        macros_command = mr.resolve_command(cc, data, self._scheduler.macromodulations,
                                            self._scheduler.timeperiods)
        assert 'plugins/nothing 127.0.0.1' == macros_command


class TestMacroResolverWithEnv(MacroResolverTester, AlignakTest):
    """Test without enabled environment macros"""

    def setUp(self):
        super(TestMacroResolverWithEnv, self).setUp()

        self.setup_with_file('cfg/cfg_macroresolver.cfg')
        assert self.conf_is_correct


class TestMacroResolverWithoutEnv(MacroResolverTester, AlignakTest):
    """Test without enabled environment macros"""

    def setUp(self):
        super(TestMacroResolverWithoutEnv, self).setUp()

        self.setup_with_file('cfg/cfg_macroresolver_environment.cfg')
        assert self.conf_is_correct
