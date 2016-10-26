#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2015: Alignak team, see AUTHORS.txt file for contributors
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
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
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

from alignak_test import *
from alignak.macroresolver import MacroResolver
from alignak.commandcall import CommandCall
from alignak.objects import Command


class TestMacroResolver(AlignakTest):
    # setUp is inherited from AlignakTest

    def setUp(self):
        self.maxDiff = None
        self.setup_with_file('cfg/macros/alignak_macroresolver.cfg')
        self.assertTrue(self.conf_is_correct)

    def get_mr(self):
        mr = MacroResolver()
        mr.init(self.arbiter.conf)
        return mr

    def get_hst_svc(self):
        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0"
        )
        hst = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        return (svc, hst)

    def test_resolv_simple(self):
        """
        Test a simple command resolution
        :return:
        """
        self.print_header()
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        com = mr.resolve_command(svc.check_command, data,
                                 self.schedulers['scheduler-master'].sched.macromodulations,
                                 self.schedulers['scheduler-master'].sched.timeperiods)
        self.assertEqual(com, "plugins/test_servicecheck.pl --type=ok --failchance=5% "
                              "--previous-state=OK --state-duration=0 "
                              "--total-critical-on-host=0 --total-warning-on-host=0 "
                              "--hostname test_host_0 --servicedesc test_ok_0")

    def test_special_macros(self):
        """
        Here call with a special macro TOTALHOSTSUP but call it as arg.
        So will need 2 pass in macro resolver at last to resolve it.
        :return:
        """
        self.print_header()
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        hst.state = 'UP'
        dummy_call = "special_macro!$TOTALHOSTSUP$"
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data, self.schedulers['scheduler-master'].sched.macromodulations, self.schedulers['scheduler-master'].sched.timeperiods)
        print com
        self.assertEqual('plugins/nothing 2', com)

    @unittest.skip("#352: realm_name is always empty for an host")
    def test_special_macros_realm(self):
        """
        Call the resolver with a special macro HOSTREALM
        :return:
        """
        self.print_header()
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        hst.state = 'UP'
        dummy_call = "special_macro!$HOSTREALM$"
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data, self.schedulers['scheduler-master'].sched.macromodulations, self.schedulers['scheduler-master'].sched.timeperiods)
        print com
        self.assertEqual('plugins/nothing Default', com)

    # For output macro we want to delete all illegal macro caracter
    def test_illegal_macro_output_chars(self):
        "$HOSTOUTPUT$, $HOSTPERFDATA$, $HOSTACKAUTHOR$, $HOSTACKCOMMENT$, $SERVICEOUTPUT$, $SERVICEPERFDATA$, $SERVICEACKAUTHOR$, and $SERVICEACKCOMMENT$ "
        self.print_header()
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        illegal_macro_output_chars = self.schedulers['scheduler-master'].sched.conf.illegal_macro_output_chars
        print "Illegal macros caracters:", illegal_macro_output_chars
        hst.output = 'monculcestdupoulet'
        dummy_call = "special_macro!$HOSTOUTPUT$"

        for c in illegal_macro_output_chars:
            hst.output = 'monculcestdupoulet' + c
            cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
            com = mr.resolve_command(cc, data, self.schedulers['scheduler-master'].sched.macromodulations, self.schedulers['scheduler-master'].sched.timeperiods)
            print com
            self.assertEqual('plugins/nothing monculcestdupoulet', com)

    def test_env_macros(self):
        self.print_header()
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        data.append(self.arbiter.conf)

        env = mr.get_env_macros(data)
        print "Env:", env        
        self.assertNotEqual(env, {})
        self.assertEqual('test_host_0', env['NAGIOS_HOSTNAME'])
        self.assertEqual('0.0', env['NAGIOS_SERVICEPERCENTCHANGE'])
        self.assertEqual('custvalue', env['NAGIOS__SERVICECUSTNAME'])
        self.assertEqual('gnulinux', env['NAGIOS__HOSTOSTYPE'])
        self.assertNotIn('NAGIOS_USER1', env)

    def test_resource_file(self):
        """
        Test macros defined in configuration files
        :return:
        """
        self.print_header()
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]

        # $USER1$ macro is defined as 'plugins' in the configuration file
        dummy_call = "special_macro!$USER1$"
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data, self.schedulers['scheduler-master'].sched.macromodulations, self.schedulers['scheduler-master'].sched.timeperiods)
        self.assertEqual('plugins/nothing plugins', com)

        # $INTERESTINGVARIABLE$ macro is defined as 'interesting_value' in the configuration file
        dummy_call = "special_macro!$INTERESTINGVARIABLE$"
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data, self.schedulers['scheduler-master'].sched.macromodulations, self.schedulers['scheduler-master'].sched.timeperiods)
        print "CUCU", com
        self.assertEqual('plugins/nothing interesting_value', com)

        # Look for multiple = in lines, should split the first
        # and keep others in the macro value
        dummy_call = "special_macro!$ANOTHERVALUE$"
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data, self.schedulers['scheduler-master'].sched.macromodulations, self.schedulers['scheduler-master'].sched.timeperiods)
        self.assertEqual('plugins/nothing first=second', com)

    def test_ondemand_macros(self):
        """
        Test on-demand macros
        :return:
        """
        self.print_header()
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]
        hst.state = 'UP'
        svc.state = 'UNKNOWN'

        # Request a specific host state
        dummy_call = "special_macro!$HOSTSTATE:test_host_0$"
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data,
                                 self.schedulers['scheduler-master'].sched.macromodulations,
                                 self.schedulers['scheduler-master'].sched.timeperiods)
        self.assertEqual('plugins/nothing UP', com)

        # Call with a void host name, means : myhost
        data = [hst]
        dummy_call = "special_macro!$HOSTSTATE:$"
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data,
                                 self.schedulers['scheduler-master'].sched.macromodulations,
                                 self.schedulers['scheduler-master'].sched.timeperiods)
        self.assertEqual('plugins/nothing UP', com)

        # Now with a service, for our implicit host state
        data = [hst, svc]
        dummy_call = "special_macro!$HOSTSTATE:test_host_0$"
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data,
                                 self.schedulers['scheduler-master'].sched.macromodulations,
                                 self.schedulers['scheduler-master'].sched.timeperiods)
        self.assertEqual('plugins/nothing UP', com)
                                                        
        # Now with a service, for our implicit host state (missing host ...)
        data = [hst, svc]
        dummy_call = "special_macro!$HOSTSTATE:$"
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data,
                                 self.schedulers['scheduler-master'].sched.macromodulations,
                                 self.schedulers['scheduler-master'].sched.timeperiods)
        self.assertEqual('plugins/nothing UP', com)

        # Now prepare another service
        svc2 = self.arbiter.conf.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_another_service"
        )
        svc2.output = 'you should not pass'

        # Now call this data from our previous service - get service state
        data = [hst, svc2]
        dummy_call = "special_macro!$SERVICESTATE:test_host_0:test_another_service$"
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data,
                                 self.schedulers['scheduler-master'].sched.macromodulations,
                                 self.schedulers['scheduler-master'].sched.timeperiods)
        self.assertEqual('plugins/nothing OK', com)

        # Now call this data from our previous service - get service output
        data = [hst, svc2]
        dummy_call = "special_macro!$SERVICEOUTPUT:test_host_0:test_another_service$"
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data,
                                 self.schedulers['scheduler-master'].sched.macromodulations,
                                 self.schedulers['scheduler-master'].sched.timeperiods)
        self.assertEqual('plugins/nothing you should not pass', com)

        # Ok now with a host implicit way
        svc2.output = 'you should not pass'
        data = [hst, svc2]
        dummy_call = "special_macro!$SERVICEOUTPUT::test_another_service$"
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data,
                                 self.schedulers['scheduler-master'].sched.macromodulations,
                                 self.schedulers['scheduler-master'].sched.timeperiods)
        self.assertEqual('plugins/nothing you should not pass', com)

    @unittest.skip("Seems to be broken...")
    def test_custom_macros(self):
        """
        Test on-demand macros with custom variables
        :return:
        """
        self.print_header()
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()

        # Get the second service
        svc2 = self.arbiter.conf.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_another_service"
        )
        data = [hst, svc2]

        # Parse custom macro to get service custom variables base upon a fixed value
        dummy_call = "special_macro!$_SERVICE_CUSTOM1$"
        # special_macro is defined as: $USER1$/nothing $ARG1$
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data,
                                 self.schedulers['scheduler-master'].sched.macromodulations,
                                 self.schedulers['scheduler-master'].sched.timeperiods)
        self.assertEqual('plugins/nothing value', com)

        # Parse custom macro to get service custom variables base upon another macro
        dummy_call = "special_macro!$_SERVICE_CUSTOM2$"
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data,
                                 self.schedulers['scheduler-master'].sched.macromodulations,
                                 self.schedulers['scheduler-master'].sched.timeperiods)
        self.assertEqual('plugins/nothing test_host_0', com)

    def test_hostadressX_macros(self):
        """
        Host addresses macros
        :return:
        """
        self.print_header()
        mr = self.get_mr()
        (svc, hst) = self.get_hst_svc()
        data = [hst, svc]

        # Ok sample host call
        dummy_call = "special_macro!$HOSTADDRESS$"
        cc = CommandCall({"commands": self.arbiter.conf.commands, "call": dummy_call})
        com = mr.resolve_command(cc, data, self.schedulers['scheduler-master'].sched.macromodulations, self.schedulers['scheduler-master'].sched.timeperiods)
        self.assertEqual('plugins/nothing 127.0.0.1', com)
