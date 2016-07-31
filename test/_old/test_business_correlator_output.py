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
#     Christophe Simon, geektophe@gmail.com
#     Grégory Starck, g.starck@gmail.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     Sebastien Coavoux, s.coavoux@free.fr
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

#
# This file is used to test business rules output based on template expansion.
#

import time
from alignak_test import AlignakTest
from alignak.macroresolver import MacroResolver


class TestBusinesscorrelOutput(AlignakTest):

    def setUp(self):
        """
        Import configurations files when run each test

        :return: None
        """
        self.setup_with_file('cfg/cfg_business_correlator_output.cfg')

    def test_bprule_empty_output(self):
        """
        No checks run, so business rule is empty

        :return: None
        """
        svc = self.scheduler.sched.services.find_srv_by_name_and_hostname("dummy",
                                                                          "empty_bp_rule_output")
        self.assertTrue(svc.got_business_rule)
        self.assertIsNot(svc.business_rule, None)
        self.assertEqual("", svc.get_business_rule_output(self.scheduler.sched.hosts,
                                                              self.scheduler.sched.macromodulations,
                                                              self.scheduler.sched.timeperiods))


    def test_bprule_output(self):
        """
        Test output of business rules
        bprule: test_host_01,srv1 & test_host_02,srv2 & test_host_03,srv3 & test_host_04

        :return: None
        """
        svc = self.scheduler.sched.services.find_srv_by_name_and_hostname(
            "dummy", "formatted_bp_rule_output")
        self.assertTrue(svc.got_business_rule)
        self.assertIsNot(svc.business_rule, None)
        self.assertEqual("$STATUS$ $([$STATUS$: $FULLNAME$] )$", svc.business_rule_output_template)

        svc1 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc2 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc3 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_03", "srv3")
        host4 = self.scheduler.sched.hosts.find_by_name("test_host_04")

        self.scheduler_loop(2, [
            [svc1, 0, 'OK test_host_01/srv1'],
            [svc2, 1, 'WARNING test_host_02/srv2'],
            [svc3, 2, 'CRITICAL test_host_03/srv3'],
            [host4, 2, 'DOWN test_host_04']
        ])

        #time.sleep(61)
        self.scheduler_loop(1, [
            [svc1, 0, 'OK test_host_01/srv1'],
            [svc2, 1, 'WARNING test_host_02/srv2'],
            [svc3, 2, 'CRITICAL test_host_03/srv3'],
            [host4, 2, 'DOWN test_host_04']
        ])

        # Performs checks
        output = svc.output
        print("*********************")
        print(output)
        self.assertGreater(output.find("[WARNING: test_host_02/srv2]"), 0)
        self.assertGreater(output.find("[CRITICAL: test_host_03/srv3]"), 0)
        self.assertGreater(output.find("[DOWN: test_host_04]"), 0)
        # Should not display OK state checks
        self.assertEqual(-1, output.find("[OK: test_host_01/srv1]") )
        self.assertTrue(output.startswith("CRITICAL"))









    def test_bprule_expand_template_macros(self):
        svc_cor = self.scheduler.sched.services.find_srv_by_name_and_hostname("dummy", "formatted_bp_rule_output")
        self.assertIs(True, svc_cor.got_business_rule)
        self.assertIsNot(svc_cor.business_rule, None)

        svc1 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc2 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc3 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_03", "srv3")
        hst4 = self.scheduler.sched.hosts.find_by_name("test_host_04")

        for i in range(2):
            self.scheduler_loop(1, [
                [svc1, 0, 'OK test_host_01/srv1'],
                [svc2, 1, 'WARNING test_host_02/srv2'],
                [svc3, 2, 'CRITICAL test_host_03/srv3'],
                [hst4, 2, 'DOWN test_host_04']])

        time.sleep(61)
        self.scheduler.sched.manage_internal_checks()
        self.scheduler.sched.consume_results()

        # Performs checks
        m = MacroResolver()
        template = "$STATUS$,$SHORTSTATUS$,$HOSTNAME$,$SERVICEDESC$,$FULLNAME$"
        host = self.scheduler.sched.hosts[svc1.host]
        data = [host, svc1]
        output = m.resolve_simple_macros_in_string(template, data, self.scheduler.sched.macromodulations, self.scheduler.sched.timeperiods)
        self.assertEqual("OK,O,test_host_01,srv1,test_host_01/srv1", output)
        host = self.scheduler.sched.hosts[svc2.host]
        data = [host, svc2]
        output = m.resolve_simple_macros_in_string(template, data, self.scheduler.sched.macromodulations, self.scheduler.sched.timeperiods)
        self.assertEqual("WARNING,W,test_host_02,srv2,test_host_02/srv2", output)
        host = self.scheduler.sched.hosts[svc3.host]
        data = [host, svc3]
        output = m.resolve_simple_macros_in_string(template, data, self.scheduler.sched.macromodulations, self.scheduler.sched.timeperiods)
        self.assertEqual("CRITICAL,C,test_host_03,srv3,test_host_03/srv3", output)
        data = [hst4]
        output = m.resolve_simple_macros_in_string(template, data, self.scheduler.sched.macromodulations, self.scheduler.sched.timeperiods)
        self.assertEqual("DOWN,D,test_host_04,,test_host_04", output)
        host = self.scheduler.sched.hosts[svc_cor.host]
        data = [host, svc_cor]
        output = m.resolve_simple_macros_in_string(template, data, self.scheduler.sched.macromodulations, self.scheduler.sched.timeperiods)
        self.assertEqual("CRITICAL,C,dummy,formatted_bp_rule_output,dummy/formatted_bp_rule_output", output)








    def test_bprule_xof_one_critical_output(self):
        svc_cor = self.scheduler.sched.services.find_srv_by_name_and_hostname("dummy", "formatted_bp_rule_xof_output")
        self.assertIs(True, svc_cor.got_business_rule)
        self.assertIsNot(svc_cor.business_rule, None)
        self.assertEqual("$STATUS$ $([$STATUS$: $FULLNAME$] )$", svc_cor.business_rule_output_template)

        svc1 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc2 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc3 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_03", "srv3")
        hst4 = self.scheduler.sched.hosts.find_by_name("test_host_04")

        for i in range(2):
            self.scheduler_loop(1, [
                [svc1, 0, 'OK test_host_01/srv1'],
                [svc2, 0, 'OK test_host_02/srv2'],
                [svc3, 2, 'CRITICAL test_host_03/srv3'],
                [hst4, 0, 'UP test_host_04']])

        time.sleep(61)
        self.scheduler.sched.manage_internal_checks()
        self.scheduler.sched.consume_results()

        # Performs checks
        self.assertEqual(0, svc_cor.business_rule.get_state())
        self.assertEqual("OK [CRITICAL: test_host_03/srv3]", svc_cor.output)

    def test_bprule_xof_all_ok_output(self):
        svc_cor = self.scheduler.sched.services.find_srv_by_name_and_hostname("dummy", "formatted_bp_rule_xof_output")
        self.assertIs(True, svc_cor.got_business_rule)
        self.assertIsNot(svc_cor.business_rule, None)
        self.assertEqual("$STATUS$ $([$STATUS$: $FULLNAME$] )$", svc_cor.business_rule_output_template)

        svc1 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc2 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc3 = self.scheduler.sched.services.find_srv_by_name_and_hostname("test_host_03", "srv3")
        hst4 = self.scheduler.sched.hosts.find_by_name("test_host_04")

        for i in range(2):
            self.scheduler_loop(1, [
                [svc1, 0, 'OK test_host_01/srv1'],
                [svc2, 0, 'OK test_host_02/srv2'],
                [svc3, 0, 'OK test_host_03/srv3'],
                [hst4, 0, 'UP test_host_04']])

        time.sleep(61)
        self.scheduler.sched.manage_internal_checks()
        self.scheduler.sched.consume_results()

        # Performs checks
        self.assertEqual(0, svc_cor.business_rule.get_state())
        self.assertEqual("OK all checks were successful.", svc_cor.output)
