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

from alignak_test import AlignakTest


class TestBusinessCorrelatorRecursive(AlignakTest):

    def setUp(self):
        self.setup_with_file('cfg/cfg_business_correlator_recursive.cfg')
        assert self.conf_is_correct
        self._sched = self._scheduler

    def test_recursive(self):
        """ BR - recursive do not break python
        """
        self.print_header()

        # Get the hosts
        host1 = self._sched.hosts.find_by_name("ht34-peret-2-dif0")
        host1.act_depend_of = []  # no host checks on critical check results
        host2 = self._sched.hosts.find_by_name("ht34-peret-2-dif1")
        host2.act_depend_of = []  # no host checks on critical check results

        hst_cor = self._sched.hosts.find_by_name("ht34-peret-2")
        hst_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple host...
        assert hst_cor.got_business_rule
        assert hst_cor.business_rule is not None
        bp_rule = hst_cor.business_rule

        self.scheduler_loop(3, [
            [host1, 2, 'DOWN | value1=1 value2=2'],
            [host2, 2, 'DOWN | rtt=10']
        ])

        assert 'DOWN' == host1.state
        assert 'HARD' == host1.state_type
        assert 'DOWN' == host2.state
        assert 'HARD' == host2.state_type

        # When all is ok, the BP rule state is 4: undetermined!
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 4 == state

if __name__ == '__main__':
    AlignakTest.main()
