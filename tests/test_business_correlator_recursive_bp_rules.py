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
# This file is used to test reading and processing of config files
#

from .alignak_test import AlignakTest


class TestBusinessCorrelatorRecursive(AlignakTest):

    def setUp(self):
        super(TestBusinessCorrelatorRecursive, self).setUp()
        self.setup_with_file('cfg/cfg_business_correlator_recursive.cfg')
        assert self.conf_is_correct
        self._sched = self._scheduler

    def test_recursive(self):
        """ BR - recursive do not break python

            ht34-peret-2-dif0, son of ht34-peret-2
            ht34-peret-2-dif1, son of ht34-peret-2

            ht34-peret-2 host state is 2,1,1 of (fid0 | dif1)
        """
        # Get the standard hosts
        host_dif0 = self._sched.hosts.find_by_name("ht34-peret-2-dif0")
        host_dif0.act_depend_of = []  # no host checks on critical check results
        host_dif1 = self._sched.hosts.find_by_name("ht34-peret-2-dif1")
        host_dif1.act_depend_of = []  # no host checks on critical check results

        # Get the BR main host - not a real host but a BR one...
        host_main = self._sched.hosts.find_by_name("ht34-peret-2")
        host_main.act_depend_of = []  # no host checks on critical check results
        host_main.__class__.enable_problem_impacts_states_change = False

        # Is a Business Rule, not a simple host...
        assert host_main.got_business_rule
        assert host_main.business_rule is not None
        bp_rule = host_main.business_rule
        print(("Host BR: %s" % bp_rule))
        # Host BR:
        # "Op:None Val:(u'1', u'1', u'1') Sons:['
        #   "Op:of: Val:(u'2', u'1', u'1') Sons:['
        #       "Op:host Val:(u'0', u'0', u'0') Sons:['c832bb0ad22c4700b16697cccbb6b782'] IsNot:False",
        #       "Op:host Val:(u'0', u'0', u'0') Sons:['596b9f36d1e94848ab145e3b43464645'] IsNot:False"
        #   '] IsNot:False"
        # '] IsNot:False"

        self.scheduler_loop(3, [
            [host_dif0, 2, 'DOWN | value1=1 value2=2'],
            [host_dif1, 2, 'DOWN | rtt=10']
        ])
        print(("Host dif-0 state: %s / %s" % (host_dif0.state_type, host_dif0.state)))
        print(("Host dif-1 state: %s / %s" % (host_dif1.state_type, host_dif1.state)))
        assert 'DOWN' == host_dif0.state
        assert 'HARD' == host_dif0.state_type
        assert 'DOWN' == host_dif1.state
        assert 'HARD' == host_dif1.state_type

        # When all is ok, the BP rule state is 4: undetermined!
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 4 == state
