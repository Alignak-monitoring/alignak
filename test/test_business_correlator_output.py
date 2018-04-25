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
from .alignak_test import AlignakTest
from alignak.macroresolver import MacroResolver


class TestBusinesscorrelOutput(AlignakTest):

    def setUp(self):
        super(TestBusinesscorrelOutput, self).setUp()
        self.setup_with_file('cfg/cfg_business_correlator_output.cfg')
        assert self.conf_is_correct
        self._sched = self._scheduler

    def launch_internal_check(self, svc_br):
        """ Launch an internal check for the business rule service provided """
        # Launch an internal check
        now = time.time()
        self._sched.add(svc_br.launch_check(now - 1, self._sched.hosts, self._sched.services,
                                            self._sched.timeperiods, self._sched.macromodulations,
                                            self._sched.checkmodulations, self._sched.checks))
        c = svc_br.actions[0]
        assert True == c.internal
        assert c.is_launchable(now)

        # ask the scheduler to launch this check
        # and ask 2 loops: one to launch the check
        # and another to get the result
        self.scheduler_loop(2, [])

        # We should not have the check anymore
        assert 0 == len(svc_br.actions)

    def test_bprule_empty_output(self):
        """ BR - empty output """
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy",
                                                                     "empty_bp_rule_output")
        assert True is svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        assert "" == svc_cor.get_business_rule_output(self._sched.hosts,
                                                              self._sched.services,
                                                              self._sched.macromodulations,
                                                              self._sched.timeperiods)

    def test_bprule_expand_template_macros(self):
        """ BR - expand template macros"""
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy",
                                                                     "formatted_bp_rule_output")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        assert svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        assert "$STATUS$ $([$STATUS$: $FULLNAME$] )$" == \
                         svc_cor.business_rule_output_template

        svc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc1.act_depend_of = []  # no host checks on critical check results
        svc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc2.act_depend_of = []  # no host checks on critical check results
        svc3 = self._sched.services.find_srv_by_name_and_hostname("test_host_03", "srv3")
        svc3.act_depend_of = []  # no host checks on critical check results
        hst4 = self._sched.hosts.find_by_name("test_host_04")
        hst4.act_depend_of = []  # no host checks on critical check results

        self.scheduler_loop(3, [
            [svc1, 0, 'OK test_host_01/srv1'],
            [svc2, 1, 'WARNING test_host_02/srv2'],
            [svc3, 2, 'CRITICAL test_host_03/srv3'],
            [hst4, 2, 'DOWN test_host_04']])
        assert 'OK' == svc1.state
        assert 'HARD' == svc1.state_type
        assert 'WARNING' == svc2.state
        assert 'HARD' == svc2.state_type
        assert 'CRITICAL' == svc3.state
        assert 'HARD' == svc3.state_type
        assert 'DOWN' == hst4.state
        assert 'HARD' == hst4.state_type

        time.sleep(1)

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # Performs checks
        m = MacroResolver()
        template = "$STATUS$,$SHORTSTATUS$,$HOSTNAME$,$SERVICEDESC$,$FULLNAME$"
        host = self._sched.hosts[svc1.host]
        data = [host, svc1]
        output = m.resolve_simple_macros_in_string(template, data,
                                                   self._sched.macromodulations,
                                                   self._sched.timeperiods)
        assert "OK,O,test_host_01,srv1,test_host_01/srv1" == output
        host = self._sched.hosts[svc2.host]
        data = [host, svc2]
        output = m.resolve_simple_macros_in_string(template, data,
                                                   self._sched.macromodulations,
                                                   self._sched.timeperiods)
        assert "WARNING,W,test_host_02,srv2,test_host_02/srv2" == output
        host = self._sched.hosts[svc3.host]
        data = [host, svc3]
        output = m.resolve_simple_macros_in_string(template, data,
                                                   self._sched.macromodulations,
                                                   self._sched.timeperiods)
        assert "CRITICAL,C,test_host_03,srv3,test_host_03/srv3" == output
        data = [hst4]
        output = m.resolve_simple_macros_in_string(template, data,
                                                   self._sched.macromodulations,
                                                   self._sched.timeperiods)
        assert "DOWN,D,test_host_04,,test_host_04" == output
        host = self._sched.hosts[svc_cor.host]
        data = [host, svc_cor]
        output = m.resolve_simple_macros_in_string(template, data,
                                                   self._sched.macromodulations,
                                                   self._sched.timeperiods)
        assert "CRITICAL,C,dummy,formatted_bp_rule_output,dummy/formatted_bp_rule_output" == \
                         output

    def test_bprule_output(self):
        """ BR - output """
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy",
                                                                     "formatted_bp_rule_output")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        assert svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        assert "$STATUS$ $([$STATUS$: $FULLNAME$] )$" == \
                         svc_cor.business_rule_output_template

        svc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc1.act_depend_of = []  # no host checks on critical check results
        svc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc2.act_depend_of = []  # no host checks on critical check results
        svc3 = self._sched.services.find_srv_by_name_and_hostname("test_host_03", "srv3")
        svc3.act_depend_of = []  # no host checks on critical check results
        hst4 = self._sched.hosts.find_by_name("test_host_04")
        hst4.act_depend_of = []  # no host checks on critical check results

        self.scheduler_loop(3, [
            [svc1, 0, 'OK test_host_01/srv1'],
            [svc2, 1, 'WARNING test_host_02/srv2'],
            [svc3, 2, 'CRITICAL test_host_03/srv3'],
            [hst4, 2, 'DOWN test_host_04']])
        assert 'OK' == svc1.state
        assert 'HARD' == svc1.state_type
        assert 'WARNING' == svc2.state
        assert 'HARD' == svc2.state_type
        assert 'CRITICAL' == svc3.state
        assert 'HARD' == svc3.state_type
        assert 'DOWN' == hst4.state
        assert 'HARD' == hst4.state_type

        time.sleep(1)

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # Performs checks
        output = svc_cor.output
        print(("BR output: %s" % output))
        assert output.find("[WARNING: test_host_02/srv2]") > 0
        assert output.find("[CRITICAL: test_host_03/srv3]") > 0
        assert output.find("[DOWN: test_host_04]") > 0

        # Should not display OK state checks
        assert -1 == output.find("[OK: test_host_01/srv1]")
        assert output.startswith("CRITICAL")

    def test_bprule_xof_one_critical_output(self):
        """ BR 3 of: - one CRITICAL output """
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy",
                                                                     "formatted_bp_rule_xof_output")
        assert True is svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        assert "$STATUS$ $([$STATUS$: $FULLNAME$] )$" == \
                         svc_cor.business_rule_output_template

        svc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc1.act_depend_of = []  # no host checks on critical check results
        svc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc2.act_depend_of = []  # no host checks on critical check results
        svc3 = self._sched.services.find_srv_by_name_and_hostname("test_host_03", "srv3")
        svc3.act_depend_of = []  # no host checks on critical check results
        hst4 = self._sched.hosts.find_by_name("test_host_04")
        hst4.act_depend_of = []  # no host checks on critical check results

        self.scheduler_loop(3, [
            [svc1, 0, 'OK test_host_01/srv1'],
            [svc2, 0, 'OK test_host_02/srv2'],
            [svc3, 2, 'CRITICAL test_host_03/srv3'],
            [hst4, 0, 'UP test_host_04']])
        assert 'OK' == svc1.state
        assert 'HARD' == svc1.state_type
        assert 'OK' == svc2.state
        assert 'HARD' == svc2.state_type
        assert 'CRITICAL' == svc3.state
        assert 'HARD' == svc3.state_type
        assert 'UP' == hst4.state
        assert 'HARD' == hst4.state_type

        time.sleep(1)

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # Performs checks
        assert 0 == svc_cor.business_rule.get_state(self._sched.hosts,
                                                            self._sched.services)
        assert "OK [CRITICAL: test_host_03/srv3]" == svc_cor.output

    def test_bprule_xof_all_ok_output(self):
        """ BR - 3 of: all OK output """
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy",
                                                                     "formatted_bp_rule_xof_output")
        assert True is svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        assert "$STATUS$ $([$STATUS$: $FULLNAME$] )$" == \
                         svc_cor.business_rule_output_template

        svc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc1.act_depend_of = []  # no host checks on critical check results
        svc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc2.act_depend_of = []  # no host checks on critical check results
        svc3 = self._sched.services.find_srv_by_name_and_hostname("test_host_03", "srv3")
        svc3.act_depend_of = []  # no host checks on critical check results
        hst4 = self._sched.hosts.find_by_name("test_host_04")
        hst4.act_depend_of = []  # no host checks on critical check results

        self.scheduler_loop(3, [
            [svc1, 0, 'OK test_host_01/srv1'],
            [svc2, 0, 'OK test_host_02/srv2'],
            [svc3, 0, 'OK test_host_03/srv3'],
            [hst4, 0, 'UP test_host_04']])
        assert 'OK' == svc1.state
        assert 'HARD' == svc1.state_type
        assert 'OK' == svc2.state
        assert 'HARD' == svc2.state_type
        assert 'OK' == svc3.state
        assert 'HARD' == svc3.state_type
        assert 'UP' == hst4.state
        assert 'HARD' == hst4.state_type

        time.sleep(1)

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # Performs checks
        assert 0 == svc_cor.business_rule.get_state(self._sched.hosts,
                                                            self._sched.services)
        assert "OK all checks were successful." == svc_cor.output


if __name__ == '__main__':
    AlignakTest.main()
