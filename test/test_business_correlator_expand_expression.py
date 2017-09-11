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
#     aviau, alexandre.viau@savoirfairelinux.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
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
# This file is used to test hostgroups and regex expressions expansion in
# business rules.
#

import time

from alignak_test import (
    unittest,
    AlignakTest,
)

# Set this variable False to disable profiling test
PROFILE_BP_RULE_RE_PROCESSING = False


class TestBusinessCorrelatorExpand(AlignakTest):

    def setUp(self):
        self.setup_with_file('cfg/cfg_business_correlator_expression.cfg')
        assert self.conf_is_correct
        self._sched = self.schedulers['scheduler-master'].sched

    def test_hostgroup_expansion_bprule_simple_host_srv(self):
        """ BR expansion - simple host/service """
        for name in ("bprule_00", "bprule_01", "bprule_02", "bprule_03",
                     "bprule_04", "bprule_05", "bprule_06"):
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", name)
            assert True is svc_cor.got_business_rule
            assert svc_cor.business_rule is not None
            bp_rule = svc_cor.business_rule
            assert '&' == bp_rule.operand
            assert False is bp_rule.not_value
            assert ('2', '2', '2') == bp_rule.of_values

            srv1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
            srv2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv1")

            sons = bp_rule.sons
            assert 2 == len(sons)
            assert 'service' == sons[0].operand
            assert 'service' == sons[1].operand

            assert srv1.uuid in (sons[0].sons[0], sons[1].sons[0])
            assert srv2.uuid in (sons[0].sons[0], sons[1].sons[0])

    def test_hostgroup_expansion_bprule_simple_xof_host_srv(self):
        """ BR expansion - simple X of:"""
        for name in ("bprule_10", "bprule_11", "bprule_12", "bprule_13",
                     "bprule_14", "bprule_15", "bprule_16", "bprule_17"):
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", name)
            assert True is svc_cor.got_business_rule
            assert svc_cor.business_rule is not None
            bp_rule = svc_cor.business_rule
            assert 'of:' == bp_rule.operand
            assert False is bp_rule.not_value
            assert ('1', '2', '2') == bp_rule.of_values

            srv1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
            srv2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv1")

            sons = bp_rule.sons
            assert 2 == len(sons)
            assert 'service' == sons[0].operand
            assert 'service' == sons[1].operand

            assert srv1.uuid in (sons[0].sons[0], sons[1].sons[0])
            assert srv2.uuid in (sons[0].sons[0], sons[1].sons[0])

    def test_hostgroup_expansion_bprule_combined_and(self):
        """ BR expansion - combined AND """
        for name in ("bprule_20", "bprule_21", "bprule_22", "bprule_23",
                     "bprule_24", "bprule_25", "bprule_26"):
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", name)
            assert True is svc_cor.got_business_rule
            assert svc_cor.business_rule is not None
            bp_rule = svc_cor.business_rule
            assert '&' == bp_rule.operand
            assert False is bp_rule.not_value
            assert ('2', '2', '2') == bp_rule.of_values

            sons = bp_rule.sons
            assert 2 == len(sons)

            for son in sons:
                assert '&' == son.operand
                assert False is son.not_value
                assert ('2', '2', '2') == son.of_values
                assert 2 == len(son.sons)
                assert 'service' == son.sons[0].operand
                assert 'service' == son.sons[1].operand

            hst1_srv1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
            hst2_srv1 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv1")
            hst1_srv2 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv2")
            hst2_srv2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")

            assert hst1_srv1.uuid in (sons[0].sons[0].sons[0], sons[0].sons[1].sons[0])
            assert hst2_srv1.uuid in (sons[0].sons[0].sons[0], sons[0].sons[1].sons[0])
            assert hst1_srv2.uuid in (sons[1].sons[0].sons[0], sons[1].sons[1].sons[0])
            assert hst2_srv2.uuid in (sons[1].sons[0].sons[0], sons[1].sons[1].sons[0])

    def test_hostgroup_expansion_bprule_combined_or(self):
        """ BR expansion - combined OR """
        for name in ("bprule_30", "bprule_31", "bprule_32", "bprule_33",
                     "bprule_34", "bprule_35", "bprule_36"):
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", name)
            assert True is svc_cor.got_business_rule
            assert svc_cor.business_rule is not None
            bp_rule = svc_cor.business_rule
            assert '|' == bp_rule.operand
            assert False is bp_rule.not_value
            assert ('2', '2', '2') == bp_rule.of_values

            sons = bp_rule.sons
            assert 2 == len(sons)

            for son in sons:
                assert '&' == son.operand
                assert False is son.not_value
                assert ('2', '2', '2') == son.of_values
                assert 2 == len(son.sons)
                assert 'service' == son.sons[0].operand
                assert 'service' == son.sons[1].operand

            hst1_srv1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
            hst2_srv1 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv1")
            hst1_srv2 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv2")
            hst2_srv2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")

            assert hst1_srv1.uuid in (sons[0].sons[0].sons[0], sons[0].sons[1].sons[0])
            assert hst2_srv1.uuid in (sons[0].sons[0].sons[0], sons[0].sons[1].sons[0])
            assert hst1_srv2.uuid in (sons[1].sons[0].sons[0], sons[1].sons[1].sons[0])
            assert hst2_srv2.uuid in (sons[1].sons[0].sons[0], sons[1].sons[1].sons[0])

    def test_hostgroup_expansion_bprule_simple_hosts(self):
        """ BR expansion - simple hosts """
        for name in ("bprule_40", "bprule_41", "bprule_42", "bprule_43"):
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", name)
            assert True is svc_cor.got_business_rule
            assert svc_cor.business_rule is not None
            bp_rule = svc_cor.business_rule
            assert '&' == bp_rule.operand
            assert False is bp_rule.not_value
            assert ('2', '2', '2') == bp_rule.of_values

            hst1 = self._sched.hosts.find_by_name("test_host_01")
            hst2 = self._sched.hosts.find_by_name("test_host_02")

            sons = bp_rule.sons
            assert 2 == len(sons)
            assert 'host' == sons[0].operand
            assert 'host' == sons[1].operand

            assert hst1.uuid in (sons[0].sons[0], sons[1].sons[0])
            assert hst2.uuid in (sons[0].sons[0], sons[1].sons[0])

    def test_hostgroup_expansion_bprule_xof_hosts(self):
        """ BR expansion - X of: hosts """
        for name in ("bprule_50", "bprule_51", "bprule_52", "bprule_53", "bprule_54"):
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", name)
            assert True is svc_cor.got_business_rule
            assert svc_cor.business_rule is not None
            bp_rule = svc_cor.business_rule
            assert 'of:' == bp_rule.operand
            assert False is bp_rule.not_value
            assert ('1', '2', '2') == bp_rule.of_values

            hst1 = self._sched.hosts.find_by_name("test_host_01")
            hst2 = self._sched.hosts.find_by_name("test_host_02")

            sons = bp_rule.sons
            assert 2 == len(sons)
            assert 'host' == sons[0].operand
            assert 'host' == sons[1].operand

            assert hst1.uuid in (sons[0].sons[0], sons[1].sons[0])
            assert hst2.uuid in (sons[0].sons[0], sons[1].sons[0])

    def test_hostgroup_expansion_bprule_same_host_srv(self):
        """ BR expansion - sale host/service """
        for name in ("bprule_60", "bprule_61"):
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_01", name)
            assert True is svc_cor.got_business_rule
            assert svc_cor.business_rule is not None
            bp_rule = svc_cor.business_rule
            assert '&' == bp_rule.operand
            assert False is bp_rule.not_value
            assert ('2', '2', '2') == bp_rule.of_values

            srv1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
            srv2 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv2")

            sons = bp_rule.sons
            assert 2 == len(sons)
            assert 'service' == sons[0].operand
            assert 'service' == sons[1].operand

            assert srv1.uuid in (sons[0].sons[0], sons[1].sons[0])
            assert srv2.uuid in (sons[0].sons[0], sons[1].sons[0])

    def test_hostgroup_expansion_bprule_xof_same_host_srv(self):
        """ BR expansion - X of: same host/service """
        for name in ("bprule_70", "bprule_71"):
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_01", name)
            assert True is svc_cor.got_business_rule
            assert svc_cor.business_rule is not None
            bp_rule = svc_cor.business_rule
            assert 'of:' == bp_rule.operand
            assert False is bp_rule.not_value
            assert ('1', '2', '2') == bp_rule.of_values

            srv1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
            srv2 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv2")

            sons = bp_rule.sons
            assert 2 == len(sons)
            assert 'service' == sons[0].operand
            assert 'service' == sons[1].operand

            assert srv1.uuid in (sons[0].sons[0], sons[1].sons[0])
            assert srv2.uuid in (sons[0].sons[0], sons[1].sons[0])

    def test_macro_expansion_bprule_no_macro(self):
        """ BR expansion - no macro """
        # Tests macro expansion
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", "bprule_no_macro")
        assert True is svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        assert "1 of: test_host_01,srv1 & test_host_02,srv2" == svc_cor.processed_business_rule
        bp_rule = svc_cor.business_rule
        assert 'of:' == bp_rule.operand
        assert ('1', '2', '2') == bp_rule.of_values

        svc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc1.act_depend_of = []  # no host checks on critical check results
        svc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc2.act_depend_of = []  # no host checks on critical check results

        # Setting dependent services status
        self.scheduler_loop(1, [
            [svc1, 0, 'UP | value1=1 value2=2'],
            [svc2, 0, 'UP | value1=1 value2=2']])

        assert 'OK' == svc1.state
        assert 'HARD' == svc1.state_type
        assert 'OK' == svc2.state
        assert 'HARD' == svc2.state_type

        self.scheduler_loop(2, [
            [svc1, 2, 'CRITICAL | value1=1 value2=2']
        ])

        assert 'CRITICAL' == svc1.state
        assert 'HARD' == svc1.state_type

        # Forces business rule evaluation.
        self.scheduler_loop(2, [
            [svc_cor, None, None]
        ])

        # Business rule should not have been re-evaluated (no macro in the
        # bp_rule)
        assert bp_rule is svc_cor.business_rule
        bp_rule = svc_cor.business_rule
        assert 0 == bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == svc_cor.last_hard_state_id

    def test_macro_expansion_bprule_macro_expand(self):
        """ BR expansion - macro expansion """
        # Tests macro expansion
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", "bprule_macro_expand")
        assert True is svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        assert "1 of: test_host_01,srv1 & test_host_02,srv2" == svc_cor.processed_business_rule
        bp_rule = svc_cor.business_rule
        assert 'of:' == bp_rule.operand
        assert ('1', '2', '2') == bp_rule.of_values

        svc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc1.act_depend_of = []  # no host checks on critical check results
        svc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc2.act_depend_of = []  # no host checks on critical check results

        # Setting dependent services status
        self.scheduler_loop(1, [
            [svc1, 0, 'UP | value1=1 value2=2'],
            [svc2, 0, 'UP | value1=1 value2=2']])

        assert 'OK' == svc1.state
        assert 'HARD' == svc1.state_type
        assert 'OK' == svc2.state
        assert 'HARD' == svc2.state_type

        self.scheduler_loop(2, [
            [svc1, 2, 'CRITICAL | value1=1 value2=2']
        ])

        assert 'CRITICAL' == svc1.state
        assert 'HARD' == svc1.state_type

        # Forces business rule evaluation.
        self.scheduler_loop(2, [
            [svc_cor, None, None]
        ])

        # Business rule should not have been re-evaluated (macro did not change
        # value)
        assert bp_rule is svc_cor.business_rule
        bp_rule = svc_cor.business_rule
        assert 0 == bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == svc_cor.last_hard_state_id

    def test_macro_expansion_bprule_macro_modulated(self):
        """ BR expansion - macro modulated """
        # Tests macro modulation
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy_modulated", "bprule_macro_modulated")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        assert True is svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        assert "2 of: test_host_01,srv1 & test_host_02,srv2" == svc_cor.processed_business_rule
        bp_rule = svc_cor.business_rule
        assert 'of:' == bp_rule.operand
        assert ('2', '2', '2') == bp_rule.of_values

        svc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc1.act_depend_of = []  # no host checks on critical check results
        svc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc2.act_depend_of = []  # no host checks on critical check results

        # Setting dependent services status
        self.scheduler_loop(2, [
            [svc1, 0, 'UP | value1=1 value2=2'],
            [svc2, 0, 'UP | value1=1 value2=2']
        ])
        assert 'OK' == svc1.state
        assert 'HARD' == svc1.state_type
        assert 'OK' == svc2.state
        assert 'HARD' == svc2.state_type

        self.scheduler_loop(2, [
            [svc1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc1.state
        assert 'HARD' == svc1.state_type

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # Business rule should not have been re-evaluated (macro did not change
        # value)
        assert bp_rule is svc_cor.business_rule
        bp_rule = svc_cor.business_rule
        assert 2 == bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == svc_cor.last_hard_state_id

        # Get macro modulation value and change its value
        mod = self._sched.macromodulations.find_by_name("xof_modulation")
        mod.customs['_XOF'] = '1'

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        assert "1 of: test_host_01,srv1 & test_host_02,srv2" == svc_cor.processed_business_rule
        assert svc_cor.business_rule is not bp_rule
        bp_rule = svc_cor.business_rule
        assert 'of:' == bp_rule.operand
        assert ('1', '2', '2') == bp_rule.of_values
        assert 0 == bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == svc_cor.last_hard_state_id

        # Tests wrongly written macro modulation (inserts invalid string)
        mod.customs['_XOF'] = 'fake'

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # Business rule should have been re-evaluated (macro was modulated)
        assert bp_rule is svc_cor.business_rule
        assert 3 == svc_cor.last_hard_state_id
        assert svc_cor.output.startswith("Error while re-evaluating business rule")

    def test_macro_expansion_bprule_macro_profile(self):
        """ BR expansion - macro profile """
        if PROFILE_BP_RULE_RE_PROCESSING is False:
            return

        import cProfile as profile

        svc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")

        # Setting dependent services status
        self.scheduler_loop(1, [
            [svc1, 0, 'UP | value1=1 value2=2'],
            [svc2, 0, 'UP | value1=1 value2=2']
        ])

        assert 'OK' == svc1.state
        assert 'HARD' == svc1.state_type
        assert 'OK' == svc2.state
        assert 'HARD' == svc2.state_type

        self.scheduler_loop(1, [[svc1, 2, 'CRITICAL | value1=1 value2=2']], verbose=False)

        assert 'CRITICAL' == svc1.state
        assert 'HARD' == svc1.state_type

        print "Profiling without macro"

        def profile_bp_rule_without_macro():
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", "bprule_no_macro")
            for i in range(1000):
                self.scheduler_loop(2, [
                    [svc_cor, None, None]
                ])

        profile.runctx('profile_bp_rule_without_macro()', globals(), locals())

        print "Profiling with macro"

        def profile_bp_rule_macro_expand():
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", "bprule_macro_expand")
            for i in range(1000):
                self.scheduler_loop(2, [
                    [svc_cor, None, None]
                ])

        profile.runctx('profile_bp_rule_macro_expand()', globals(), locals())

        print "Profiling with macro modulation"

        def profile_bp_rule_macro_modulated():
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy_modulated", "bprule_macro_modulated")
            for i in range(1000):
                self.scheduler_loop(2, [
                    [svc_cor, None, None]
                ])

        profile.runctx('profile_bp_rule_macro_modulated()', globals(), locals())


if __name__ == '__main__':
    unittest.main()
