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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
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

import time
from alignak.dependencynode import DependencyNode

from alignak_test import AlignakTest, unittest


class TestBusinessCorrelator(AlignakTest):

    def setUp(self):
        self.setup_with_file('cfg/cfg_business_correlator.cfg')
        self.assertTrue(self.conf_is_correct)
        self._sched = self.schedulers['scheduler-master'].sched

    def test_br_creation(self):
        """ BR - check creation of a simple services OR (db1 OR db2)

        :return:
        """
        self.print_header()

        # Get the hosts
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore its parent
        router = self._sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = []  # ignore its parent

        # Get the services
        svc_db1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db1")
        # Not a BR, a simple service
        self.assertFalse(svc_db1.got_business_rule)
        self.assertIsNone(svc_db1.business_rule)

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        # Not a BR, a simple service
        self.assertFalse(svc_db2.got_business_rule)
        self.assertIsNone(svc_db2.business_rule)

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "Simple_Or")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        self.assertTrue(svc_cor.got_business_rule)
        self.assertIsNotNone(svc_cor.business_rule)

        svc_cor2 = self.arbiter.conf.services.find_srv_by_name_and_hostname("test_host_0", "Simple_Or")
        # Is a Business Rule, not a simple service...
        self.assertTrue(svc_cor2.got_business_rule)
        self.assertIsNotNone(svc_cor2.business_rule)

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1 and svc_db2
        # and db1 and db2 should be parents of svc_cor
        self.assertIn(svc_cor.uuid, svc_db1.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_db2.child_dependencies)
        self.assertIn(svc_db1.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_db2.uuid, svc_cor.parent_dependencies)

        # Get the BR associated with svc_cor
        # The BR command is: bp_rule!test_host_0,db1|test_host_0,db2
        bp_rule = svc_cor.business_rule
        self.assertIsInstance(bp_rule, DependencyNode)
        print("BR scheduler: %s" % bp_rule)

        # Get the BR associated with svc_cor
        # The BR command is: bp_rule!test_host_0,db1|test_host_0,db2
        bp_rule_arbiter = svc_cor2.business_rule
        self.assertIsInstance(bp_rule_arbiter, DependencyNode)
        print("BR arbiter: %s" % bp_rule_arbiter)

        # Get the BR elements list
        self.assertIsInstance(bp_rule.list_all_elements(), list)
        self.assertEqual(len(bp_rule.list_all_elements()), 2)

        self.assertEqual(bp_rule.operand, '|')
        self.assertEqual(bp_rule.of_values, ('2', '2', '2'))
        self.assertEqual(bp_rule.not_value, False)
        self.assertEqual(bp_rule.is_of_mul, False)
        self.assertIsNotNone(bp_rule.sons)

        # We've got 2 sons for the BR which are 2 dependency nodes
        # Each dependency node has a son which is the service
        self.assertEqual(2, len(bp_rule.sons))

        # First son is linked to a service and we have its uuid
        son = bp_rule.sons[0]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db1.uuid)

        # Second son is also a service
        son = bp_rule.sons[1]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db2.uuid)

    def test_simple_or_business_correlator(self):
        """ BR - try a simple services OR (db1 OR db2)

        bp_rule!test_host_0,db1|test_host_0,db2

        :return:
        """
        self.print_header()

        # Get the hosts
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore its parent
        router = self._sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = []  # ignore its parent

        # Get the services
        svc_db1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db1")
        svc_db1.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db1.got_business_rule)
        self.assertIsNone(svc_db1.business_rule)

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db2.got_business_rule)
        self.assertIsNone(svc_db2.business_rule)

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "Simple_Or")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        self.assertTrue(svc_cor.got_business_rule)
        self.assertIsNotNone(svc_cor.business_rule)

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1 and svc_db2
        # and db1 and db2 should be parents of svc_cor
        self.assertIn(svc_cor.uuid, svc_db1.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_db2.child_dependencies)
        self.assertIn(svc_db1.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_db2.uuid, svc_cor.parent_dependencies)

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        self.assertEqual(bp_rule.operand, '|')
        self.assertEqual(bp_rule.of_values, ('2', '2', '2'))
        self.assertEqual(bp_rule.not_value, False)
        self.assertEqual(bp_rule.is_of_mul, False)
        self.assertIsNotNone(bp_rule.sons)
        self.assertEqual(2, len(bp_rule.sons))

        # First son is linked to a service and we have its uuid
        son = bp_rule.sons[0]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db1.uuid)

        # Second son is also a service
        son = bp_rule.sons[1]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db2.uuid)

        # Now start working on the states
        self.scheduler_loop(1, [
            [svc_db1, 0, 'OK | rtt=10'],
            [svc_db2, 0, 'OK | value1=1 value2=2']
        ])
        self.assertEqual('OK', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual('OK', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)

        # -----
        # OK or OK -> OK
        # -----
        # When all is ok, the BP rule state is 0
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we set the db1 as soft/CRITICAL
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db1.state)
        self.assertEqual('SOFT', svc_db1.state_type)
        self.assertEqual(0, svc_db1.last_hard_state_id)

        # The business rule must still be 0 - only hard states are considered
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual(2, svc_db1.last_hard_state_id)

        # -----
        # OK or CRITICAL -> OK
        # -----
        # The rule must still be a 0 (or inside)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we also set db2 as CRITICAL/HARD... byebye 0 :)
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual(2, svc_db2.last_hard_state_id)

        # -----
        # CRITICAL or CRITICAL -> CRITICAL
        # -----
        # And now the state of the rule must be 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(2, state)

        # And If we set one WARNING?
        self.scheduler_loop(2, [
            [svc_db2, 1, 'WARNING | value1=1 value2=2']
        ])
        self.assertEqual('WARNING', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual(1, svc_db2.last_hard_state_id)

        # -----
        # WARNING or CRITICAL -> WARNING
        # -----
        # Must be WARNING (better no 0 value)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(1, state)

    def test_simple_or_business_correlator_with_schedule(self):
        """ BR - try a simple services OR (db1 OR db2) with internal checks

        bp_rule!test_host_0,db1|test_host_0,db2

        :return:
        """
        self.print_header()

        # Get the hosts
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore its parent
        router = self._sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = []  # ignore its parent

        # Get the services
        svc_db1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db1")
        svc_db1.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db1.got_business_rule)
        self.assertIsNone(svc_db1.business_rule)

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db2.got_business_rule)
        self.assertIsNone(svc_db2.business_rule)

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "Simple_Or")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        self.assertTrue(svc_cor.got_business_rule)
        self.assertIsNotNone(svc_cor.business_rule)

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1 and svc_db2
        # and db1 and db2 should be parents of svc_cor
        self.assertIn(svc_cor.uuid, svc_db1.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_db2.child_dependencies)
        self.assertIn(svc_db1.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_db2.uuid, svc_cor.parent_dependencies)

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        self.assertEqual(bp_rule.operand, '|')
        self.assertEqual(bp_rule.of_values, ('2', '2', '2'))
        self.assertEqual(bp_rule.not_value, False)
        self.assertEqual(bp_rule.is_of_mul, False)
        self.assertIsNotNone(bp_rule.sons)
        self.assertEqual(2, len(bp_rule.sons))

        # First son is linked to a service and we have its uuid
        son = bp_rule.sons[0]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db1.uuid)

        # Second son is also a service
        son = bp_rule.sons[1]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db2.uuid)

        # Now start working on the states
        self.scheduler_loop(1, [
            [svc_db1, 0, 'OK | rtt=10'],
            [svc_db2, 0, 'OK | value1=1 value2=2']
        ])
        self.assertEqual('OK', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual('OK', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)

        # -----
        # OK or OK -> OK
        # -----
        # When all is ok, the BP rule state is 0
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        self.assertEqual('OK', svc_cor.state)
        self.assertEqual('HARD', svc_cor.state_type)
        self.assertEqual(0, svc_cor.last_hard_state_id)

        # Now we set the db1 as soft/CRITICAL
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db1.state)
        self.assertEqual('SOFT', svc_db1.state_type)
        self.assertEqual(0, svc_db1.last_hard_state_id)

        # The business rule must still be 0
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        self.assertEqual('OK', svc_cor.state)
        self.assertEqual('HARD', svc_cor.state_type)
        self.assertEqual(0, svc_cor.last_hard_state_id)

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual(2, svc_db1.last_hard_state_id)

        # The rule must still be a 0 (or inside)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        self.assertEqual('OK', svc_cor.state)
        self.assertEqual('HARD', svc_cor.state_type)
        self.assertEqual(0, svc_cor.last_hard_state_id)

        # Now we also set db2 as CRITICAL/HARD... byebye 0 :)
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual(2, svc_db2.last_hard_state_id)

        # And now the state of the rule must be 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(2, state)

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        self.assertEqual('CRITICAL', svc_cor.state)
        self.assertEqual('SOFT', svc_cor.state_type)
        self.assertEqual(0, svc_cor.last_hard_state_id)

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        self.assertEqual('CRITICAL', svc_cor.state)
        self.assertEqual('HARD', svc_cor.state_type)
        self.assertEqual(2, svc_cor.last_hard_state_id)

        # And If we set one WARNING?
        self.scheduler_loop(2, [
            [svc_db2, 1, 'WARNING | value1=1 value2=2']
        ])
        self.assertEqual('WARNING', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual(1, svc_db2.last_hard_state_id)

        # Must be WARNING (better no 0 value)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(1, state)

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        self.assertEqual('WARNING', svc_cor.state)
        self.assertEqual('HARD', svc_cor.state_type)
        self.assertEqual(1, svc_cor.last_hard_state_id)

        # Assert that Simple_Or Is an impact of the problem db2
        self.assertIn(svc_cor.uuid, svc_db2.impacts)
        # and db1 too
        self.assertIn(svc_cor.uuid, svc_db1.impacts)

    def test_simple_or_not_business_correlator(self):
        """ BR - try a simple services OR (db1 OR NOT db2)

        bp_rule!test_host_0,db1|!test_host_0,db2

        :return:
        """
        self.print_header()

        # Get the hosts
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore its parent
        router = self._sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = []  # ignore its parent

        # Get the services
        svc_db1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db1")
        svc_db1.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db1.got_business_rule)
        self.assertIsNone(svc_db1.business_rule)

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db2.got_business_rule)
        self.assertIsNone(svc_db2.business_rule)

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "Simple_Or_not")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        self.assertTrue(svc_cor.got_business_rule)
        self.assertIsNotNone(svc_cor.business_rule)

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1 and svc_db2
        # and db1 and db2 should be parents of svc_cor
        self.assertIn(svc_cor.uuid, svc_db1.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_db2.child_dependencies)
        self.assertIn(svc_db1.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_db2.uuid, svc_cor.parent_dependencies)

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        self.assertEqual(bp_rule.operand, '|')
        self.assertEqual(bp_rule.of_values, ('2', '2', '2'))
        self.assertEqual(bp_rule.not_value, False)
        self.assertEqual(bp_rule.is_of_mul, False)
        self.assertIsNotNone(bp_rule.sons)
        self.assertEqual(2, len(bp_rule.sons))

        # First son is linked to a service and we have its uuid
        son = bp_rule.sons[0]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db1.uuid)

        # Second son is also a service
        son = bp_rule.sons[1]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        # This service is NOT valued
        self.assertEqual(son.not_value, True)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db2.uuid)

        # Now start working on the states
        self.scheduler_loop(1, [
            [svc_db1, 0, 'OK | rtt=10'],
            [svc_db2, 0, 'OK | value1=1 value2=2']
        ])
        self.assertEqual('OK', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual('OK', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)

        # -----
        # OK or NOT OK -> OK
        # -----
        # When all is ok, the BP rule state is 0
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we set the db1 as soft/CRITICAL
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db1.state)
        self.assertEqual('SOFT', svc_db1.state_type)
        self.assertEqual(0, svc_db1.last_hard_state_id)

        # The business rule must still be 0 - only hard states are considered
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual(2, svc_db1.last_hard_state_id)

        # -----
        # CRITICAL or NOT OK -> CRITICAL
        # -----
        # The rule must still be a 0 (or inside)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(2, state)

        # Now we also set db2 as CRITICAL/HARD... byebye 0 :)
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual(2, svc_db2.last_hard_state_id)

        # -----
        # CRITICAL or NOT CRITICAL -> OK
        # -----
        # And now the state of the rule must be 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # And If we set one WARNING?
        self.scheduler_loop(2, [
            [svc_db2, 1, 'WARNING | value1=1 value2=2']
        ])
        self.assertEqual('WARNING', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual(1, svc_db2.last_hard_state_id)

        # -----
        # WARNING or NOT CRITICAL -> WARNING
        # -----
        # Must be WARNING (better no 0 value)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(1, state)

    def test_simple_and_business_correlator(self):
        """ BR - try a simple services AND (db1 AND db2)

        bp_rule!test_host_0,db1&test_host_0,db2

        :return:
        """
        self.print_header()

        # Get the hosts
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore its parent
        router = self._sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = []  # ignore its parent

        # Get the services
        svc_db1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db1")
        svc_db1.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db1.got_business_rule)
        self.assertIsNone(svc_db1.business_rule)

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db2.got_business_rule)
        self.assertIsNone(svc_db2.business_rule)

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                     "Simple_And")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        self.assertTrue(svc_cor.got_business_rule)
        self.assertIsNotNone(svc_cor.business_rule)

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1 and svc_db2
        # and db1 and db2 should be parents of svc_cor
        self.assertIn(svc_cor.uuid, svc_db1.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_db2.child_dependencies)
        self.assertIn(svc_db1.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_db2.uuid, svc_cor.parent_dependencies)

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        self.assertEqual(bp_rule.operand, '&')
        self.assertEqual(bp_rule.of_values, ('2', '2', '2'))
        self.assertEqual(bp_rule.not_value, False)
        self.assertEqual(bp_rule.is_of_mul, False)
        self.assertIsNotNone(bp_rule.sons)
        self.assertEqual(2, len(bp_rule.sons))

        # First son is linked to a service and we have its uuid
        son = bp_rule.sons[0]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db1.uuid)

        # Second son is also a service
        son = bp_rule.sons[1]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db2.uuid)

        # Now start working on the states
        self.scheduler_loop(1, [
            [svc_db1, 0, 'OK | rtt=10'],
            [svc_db2, 0, 'OK | value1=1 value2=2'] 
        ])
        self.assertEqual('OK', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual('OK', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)

        # -----
        # OK and OK -> OK
        # -----
        # When all is ok, the BP rule state is 0
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we set the db1 as soft/CRITICAL
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db1.state)
        self.assertEqual('SOFT', svc_db1.state_type)
        self.assertEqual(0, svc_db1.last_hard_state_id)

        # The business rule must still be 0 because we want HARD states
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(2, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual(2, svc_db1.last_hard_state_id)

        # -----
        # OK and CRITICAL -> CRITICAL
        # -----
        # The rule must go CRITICAL
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(2, state)

        # Now we set db2 as WARNING/HARD...
        self.scheduler_loop(2, [
            [svc_db2, 1, 'WARNING | value1=1 value2=2']
        ])
        self.assertEqual('WARNING', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual(1, svc_db2.last_hard_state_id)

        # -----
        # WARNING and CRITICAL -> CRITICAL
        # -----
        # The state of the rule remains 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(2, state)

        # And If we set one WARNING too?
        self.scheduler_loop(2, [
            [svc_db1, 1, 'WARNING | value1=1 value2=2']
        ])
        self.assertEqual('WARNING', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual(1, svc_db1.last_hard_state_id)

        # -----
        # WARNING and WARNING -> WARNING
        # -----
        # Must be WARNING (worse no 0 value for both)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(1, state)

    def test_simple_and_not_business_correlator(self):
        """ BR - try a simple services AND NOT (db1 AND NOT db2)

        bp_rule!test_host_0,db1&!test_host_0,db2
        """
        self.print_header()

        # Get the hosts
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore its parent
        router = self._sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = []  # ignore its parent

        # Get the services
        svc_db1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db1")
        svc_db1.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db1.got_business_rule)
        self.assertIsNone(svc_db1.business_rule)

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db2.got_business_rule)
        self.assertIsNone(svc_db2.business_rule)

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                     "Simple_And_not")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        self.assertTrue(svc_cor.got_business_rule)
        self.assertIsNotNone(svc_cor.business_rule)

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1 and svc_db2
        # and db1 and db2 should be parents of svc_cor
        self.assertIn(svc_cor.uuid, svc_db1.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_db2.child_dependencies)
        self.assertIn(svc_db1.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_db2.uuid, svc_cor.parent_dependencies)

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        self.assertEqual(bp_rule.operand, '&')
        self.assertEqual(bp_rule.of_values, ('2', '2', '2'))
        # Not value remains False because one service is NOT ... but the BR is not NON
        self.assertEqual(bp_rule.not_value, False)
        self.assertEqual(bp_rule.is_of_mul, False)
        self.assertIsNotNone(bp_rule.sons)
        self.assertEqual(2, len(bp_rule.sons))

        # First son is linked to a service and we have its uuid
        son = bp_rule.sons[0]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db1.uuid)

        # Second son is also a service
        son = bp_rule.sons[1]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        # This service is NOT valued
        self.assertEqual(son.not_value, True)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db2.uuid)

        # Now start working on the states
        self.scheduler_loop(2, [
            [svc_db1, 0, 'OK | value1=1 value2=2'],
            [svc_db2, 2, 'CRITICAL | rtt=10']
        ])
        self.assertEqual('OK', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual('CRITICAL', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)

        # -----
        # OK and not CRITICAL -> OK
        # -----
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we set the db1 as soft/CRITICAL
        self.scheduler_loop(1, [[svc_db1, 2, 'CRITICAL | value1=1 value2=2']])
        self.assertEqual('CRITICAL', svc_db1.state)
        self.assertEqual('SOFT', svc_db1.state_type)
        self.assertEqual(0, svc_db1.last_hard_state_id)

        # The business rule must still be 0
        # becase we want HARD states
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(1, [[svc_db1, 2, 'CRITICAL | value1=1 value2=2']])
        self.assertEqual('CRITICAL', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual(2, svc_db1.last_hard_state_id)

        # -----
        # CRITICAL and not CRITICAL -> CRITICAL
        # -----
        # The rule must go CRITICAL
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(2, state)

        # Now we also set db2 as WARNING/HARD...
        self.scheduler_loop(2, [[svc_db2, 1, 'WARNING | value1=1 value2=2']])
        self.assertEqual('WARNING', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual(1, svc_db2.last_hard_state_id)

        # -----
        # CRITICAL and not WARNING -> CRITICAL
        # -----
        # And now the state of the rule must be 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(2, state)

        # And If we set one WARNING too?
        self.scheduler_loop(2, [[svc_db1, 1, 'WARNING | value1=1 value2=2']])
        self.assertEqual('WARNING', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual(1, svc_db1.last_hard_state_id)

        # -----
        # WARNING and not CRITICAL -> WARNING
        # -----
        # Must be WARNING (worse no 0 value for both)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(1, state)

        # Now try to get ok in both place, should be bad :)
        self.scheduler_loop(2, [[svc_db1, 0, 'OK | value1=1 value2=2'], [svc_db2, 0, 'OK | value1=1 value2=2']])
        self.assertEqual('OK', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual(0, svc_db1.last_hard_state_id)
        self.assertEqual('OK', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual(0, svc_db2.last_hard_state_id)

        # -----
        # OK and not OK -> CRITICAL
        # -----
        # Must be CRITICAL (ok and not ok IS no OK :) )
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(2, state)

    def test_simple_1of_business_correlator(self):
        """ BR - simple 1of: db1 OR/AND db2

        bp_rule!1 of: test_host_0,db1|test_host_0,db2
        """
        self.run_simple_1of_business_correlator()

    def test_simple_1of_neg_business_correlator(self):
        """ BR - simple -1of: db1 OR/AND db2

        bp_rule!-1 of: test_host_0,db1|test_host_0,db2
        """
        self.run_simple_1of_business_correlator(with_neg=True)

    def test_simple_1of_pct_business_correlator(self):
        """ BR - simple 50%of: db1 OR/AND db2

        bp_rule!50% of: test_host_0,db1|test_host_0,db2
        """
        self.run_simple_1of_business_correlator(with_pct=True)

    def test_simple_1of_pct_neg_business_correlator(self):
        """ BR - simple -50%of: db1 OR/AND db2

        bp_rule!-50% of: test_host_0,db1|test_host_0,db2
        """
        self.run_simple_1of_business_correlator(with_pct=True, with_neg=True)

    def run_simple_1of_business_correlator(self, with_pct=False, with_neg=False):
        """

        :param with_pct: True if a percentage is set
        :param with_neg: True if a negation is set
        :return:
        """
        self.print_header()

        # Get the hosts
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore its parent
        router = self._sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = []  # ignore its parent

        # Get the services
        svc_db1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db1")
        svc_db1.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db1.got_business_rule)
        self.assertIsNone(svc_db1.business_rule)

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db2.got_business_rule)
        self.assertIsNone(svc_db2.business_rule)

        if with_pct is True:
            if with_neg is True:
                svc_cor = self._sched.services.find_srv_by_name_and_hostname(
                        "test_host_0", "Simple_1Of_pct_neg")
            else:
                svc_cor = self._sched.services.find_srv_by_name_and_hostname(
                        "test_host_0", "Simple_1Of_pct")
        else:
            if with_neg is True:
                svc_cor = self._sched.services.find_srv_by_name_and_hostname(
                        "test_host_0", "Simple_1Of_neg")
            else:
                svc_cor = self._sched.services.find_srv_by_name_and_hostname(
                        "test_host_0", "Simple_1Of")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        self.assertTrue(svc_cor.got_business_rule)
        self.assertIsNotNone(svc_cor.business_rule)

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1 and svc_db2
        # and db1 and db2 should be parents of svc_cor
        self.assertIn(svc_cor.uuid, svc_db1.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_db2.child_dependencies)
        self.assertIn(svc_db1.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_db2.uuid, svc_cor.parent_dependencies)

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        self.assertEqual(bp_rule.operand, 'of:')
        # Simple 1of: so in fact a triple ('1','2','2') (1of and MAX,MAX
        if with_pct is True:
            if with_neg is True:
                self.assertEqual(('-50%', '2', '2'), bp_rule.of_values)
            else:
                self.assertEqual(('50%', '2', '2'), bp_rule.of_values)
        else:
            if with_neg is True:
                self.assertEqual(('-1', '2', '2'), bp_rule.of_values)
            else:
                self.assertEqual(('1', '2', '2'), bp_rule.of_values)
        self.assertEqual(bp_rule.not_value, False)
        self.assertEqual(bp_rule.is_of_mul, False)
        self.assertIsNotNone(bp_rule.sons)
        self.assertEqual(2, len(bp_rule.sons))

        # We've got 2 sons for the BR which are 2 dependency nodes
        # Each dependency node has a son which is the service
        self.assertEqual(2, len(bp_rule.sons))

        # First son is linked to a service and we have its uuid
        son = bp_rule.sons[0]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db1.uuid)

        # Second son is also a service
        son = bp_rule.sons[1]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db2.uuid)

        # Now start working on the states
        self.scheduler_loop(1, [
            [svc_db1, 0, 'OK | rtt=10'],
            [svc_db2, 0, 'OK | value1=1 value2=2']
        ])
        self.assertEqual('OK', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual('OK', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)

        # -----
        # OK 1of OK -> OK
        # -----
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we set the db1 as soft/CRITICAL
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db1.state)
        self.assertEqual('SOFT', svc_db1.state_type)
        self.assertEqual(0, svc_db1.last_hard_state_id)

        # The business rule must still be 0
        # becase we want HARD states
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual(2, svc_db1.last_hard_state_id)

        # -----
        # OK 1of CRITICAL -> OK
        # -----
        # The rule still be OK
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we also set db2 as CRITICAL/HARD...
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual(2, svc_db2.last_hard_state_id)

        # -----
        # CRITICAL 1of CRITICAL -> CRITICAL
        # -----
        # And now the state of the rule must be 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(2, state)

        # And If we set one WARNING now?
        self.scheduler_loop(2, [[svc_db1, 1, 'WARNING | value1=1 value2=2']])
        self.assertEqual('WARNING', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual(1, svc_db1.last_hard_state_id)

        # -----
        # CRITICAL 1of WARNING -> WARNING
        # -----
        # Must be WARNING (worse no 0 value for both, like for AND rule)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(1, state)

    def test_simple_1of_business_correlator_with_hosts(self):
        """ BR - simple 1of: test_router_0 OR/AND test_host_0"""
        self.run_simple_1of_business_correlator_with_hosts()

    def test_simple_1of_neg_business_correlator_with_hosts(self):
        """ BR - -1of: test_router_0 OR/AND test_host_0 """
        self.run_simple_1of_business_correlator_with_hosts(with_neg=True)

    def test_simple_1of_pct_business_correlator_with_hosts(self):
        """ BR - simple 50%of: test_router_0 OR/AND test_host_0 """
        self.run_simple_1of_business_correlator_with_hosts(with_pct=True)

    def test_simple_1of_pct_neg_business_correlator_with_hosts(self):
        """ BR - simple -50%of: test_router_0 OR/AND test_host_0 """
        self.run_simple_1of_business_correlator_with_hosts(with_pct=True, with_neg=True)

    def run_simple_1of_business_correlator_with_hosts(self, with_pct=False, with_neg=False):
        """

        :param with_pct: True if a percentage is set
        :param with_neg: True if a negation is set
        :return:
        """
        self.print_header()

        # Get the hosts
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore its parent
        router = self._sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = []  # ignore its parent

        if with_pct is True:
            if with_neg is True:
                svc_cor = self._sched.services.find_srv_by_name_and_hostname(
                        "test_host_0", "Simple_1Of_with_host_pct_neg")
            else:
                svc_cor = self._sched.services.find_srv_by_name_and_hostname(
                        "test_host_0", "Simple_1Of_with_host_pct")
        else:
            if with_neg is True:
                svc_cor = self._sched.services.find_srv_by_name_and_hostname(
                        "test_host_0", "Simple_1Of_with_host_neg")
            else:
                svc_cor = self._sched.services.find_srv_by_name_and_hostname(
                        "test_host_0", "Simple_1Of_with_host")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        self.assertTrue(svc_cor.got_business_rule)
        self.assertIsNotNone(svc_cor.business_rule)

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        self.assertEqual(bp_rule.operand, 'of:')
        # Simple 1of: so in fact a triple ('1','2','2') (1of and MAX,MAX
        if with_pct is True:
            if with_neg is True:
                self.assertEqual(('-50%', '2', '2'), bp_rule.of_values)
            else:
                self.assertEqual(('50%', '2', '2'), bp_rule.of_values)
        else:
            if with_neg is True:
                self.assertEqual(('-1', '2', '2'), bp_rule.of_values)
            else:
                self.assertEqual(('1', '2', '2'), bp_rule.of_values)

        sons = bp_rule.sons
        print "Sons,", sons
        # We've got 2 sons, 2 services nodes
        self.assertEqual(2, len(sons))
        self.assertEqual('host', sons[0].operand)
        self.assertEqual(host.uuid, sons[0].sons[0])
        self.assertEqual('host', sons[1].operand)
        self.assertEqual(router.uuid, sons[1].sons[0])

    def test_dep_node_list_elements(self):
        """ BR - list all elements

        :return:
        """
        svc_db1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db1")
        self.assertEqual(False, svc_db1.got_business_rule)
        self.assertIs(None, svc_db1.business_rule)
        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        self.assertEqual(False, svc_db2.got_business_rule)
        self.assertIs(None, svc_db2.business_rule)
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "Simple_Or")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        self.assertEqual(True, svc_cor.got_business_rule)
        self.assertIsNot(svc_cor.business_rule, None)
        bp_rule = svc_cor.business_rule
        self.assertEqual('|', bp_rule.operand)

        print "All elements", bp_rule.list_all_elements()
        all_elements = bp_rule.list_all_elements()

        self.assertEqual(2, len(all_elements))
        self.assertIn(svc_db2.uuid, all_elements)
        self.assertIn(svc_db1.uuid, all_elements)

    def test_full_erp_rule_with_schedule(self):
        """ Full ERP rule with real checks scheduled

        bp_rule!(test_host_0,db1|test_host_0,db2) & (test_host_0,web1|test_host_0,web2)
         & (test_host_0,lvs1|test_host_0,lvs2) 

        :return:
        """
        self.print_header()

        now = time.time()
        
        # Get the hosts
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        router = self._sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = []  # ignore the router

        # Get the services
        svc_db1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db1")
        svc_db1.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db1.got_business_rule)
        self.assertIsNone(svc_db1.business_rule)

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db2.got_business_rule)
        self.assertIsNone(svc_db2.business_rule)

        svc_web1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "web1")
        svc_web1.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_web1.got_business_rule)
        self.assertIsNone(svc_web1.business_rule)
        
        svc_web2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "web2")
        svc_web2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_web2.got_business_rule)
        self.assertIsNone(svc_web2.business_rule)

        svc_lvs1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "lvs1")
        svc_lvs1.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_lvs1.got_business_rule)
        self.assertIsNone(svc_lvs1.business_rule)

        svc_lvs2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "lvs2")
        svc_lvs2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_lvs2.got_business_rule)
        self.assertIsNone(svc_lvs2.business_rule)

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "ERP")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        self.assertEqual(True, svc_cor.got_business_rule)
        self.assertIsNot(svc_cor.business_rule, None)
        bp_rule = svc_cor.business_rule
        self.assertEqual('&', bp_rule.operand)

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1, svc_db2, ...
        # and they should be parents of svc_cor
        self.assertIn(svc_cor.uuid, svc_db1.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_db2.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_web1.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_web2.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_lvs1.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_lvs2.child_dependencies)

        self.assertIn(svc_db1.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_db2.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_web1.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_web2.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_lvs1.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_lvs2.uuid, svc_cor.parent_dependencies)

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        self.assertEqual(bp_rule.operand, '&')
        self.assertEqual(bp_rule.of_values, ('3', '3', '3'))
        self.assertEqual(bp_rule.not_value, False)
        self.assertEqual(bp_rule.is_of_mul, False)
        self.assertIsNotNone(bp_rule.sons)
        self.assertEqual(3, len(bp_rule.sons))

        # First son is an OR rule for the DB node
        db_node = bp_rule.sons[0]
        self.assertIsInstance(db_node, DependencyNode)
        self.assertEqual(db_node.operand, '|')
        self.assertEqual(db_node.of_values, ('2', '2', '2'))
        self.assertEqual(db_node.not_value, False)
        self.assertIsNotNone(db_node.sons)
        self.assertIsNot(db_node.sons, [])
        self.assertEqual(2, len(db_node.sons))

        # First son of DB node is linked to a service and we have its uuid
        son = db_node.sons[0]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db1.uuid)

        # Second son of DB node is also a service
        son = db_node.sons[1]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db2.uuid)

        # Second son is an OR rule for the Web node
        web_node = bp_rule.sons[1]
        self.assertIsInstance(web_node, DependencyNode)
        self.assertEqual(web_node.operand, '|')
        self.assertEqual(web_node.of_values, ('2', '2', '2'))
        self.assertEqual(web_node.not_value, False)
        self.assertIsNotNone(web_node.sons)
        self.assertIsNot(web_node.sons, [])
        self.assertEqual(2, len(web_node.sons))

        # First son of Web node is linked to a service and we have its uuid
        son = web_node.sons[0]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_web1.uuid)

        # Second son of Web node is also a service
        son = web_node.sons[1]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_web2.uuid)

        # First son is an OR rule for the LVS node
        lvs_node = bp_rule.sons[2]
        self.assertIsInstance(lvs_node, DependencyNode)
        self.assertEqual(lvs_node.operand, '|')
        self.assertEqual(lvs_node.of_values, ('2', '2', '2'))
        self.assertEqual(lvs_node.not_value, False)
        self.assertIsNotNone(lvs_node.sons)
        self.assertIsNot(lvs_node.sons, [])
        self.assertEqual(2, len(lvs_node.sons))

        # First son of LVS node is linked to a service and we have its uuid
        son = lvs_node.sons[0]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_lvs1.uuid)

        # Second son of LVS node is also a service
        son = lvs_node.sons[1]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_lvs2.uuid)

        # Now start working on the states
        self.scheduler_loop(1, [
            [svc_db1, 0, 'OK'],
            [svc_db2, 0, 'OK'],
            [svc_web1, 0, 'OK'],
            [svc_web2, 0, 'OK'],
            [svc_lvs1, 0, 'OK'],
            [svc_lvs2, 0, 'OK'],
        ])
        self.assertEqual('OK', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual('OK', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual('OK', svc_web1.state)
        self.assertEqual('HARD', svc_web1.state_type)
        self.assertEqual('OK', svc_web2.state)
        self.assertEqual('HARD', svc_web2.state_type)
        self.assertEqual('OK', svc_lvs1.state)
        self.assertEqual('HARD', svc_lvs1.state_type)
        self.assertEqual('OK', svc_lvs2.state)
        self.assertEqual('HARD', svc_lvs2.state_type)

        # -----
        # OK and OK and OK -> OK
        # -----
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        self.assertEqual('OK', svc_cor.state)
        self.assertEqual('HARD', svc_cor.state_type)
        self.assertEqual(0, svc_cor.last_hard_state_id)

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(2, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual(2, svc_db1.last_hard_state_id)

        # -----
        # OK and OK and OK -> OK
        # 1st OK because OK or CRITICAL -> OK
        # -----
        # The rule must still be a 0 (or inside)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        print "ERP: Look at svc_cor state", svc_cor.state
        # What is the svc_cor state now?
        self.assertEqual('OK', svc_cor.state)
        self.assertEqual('HARD', svc_cor.state_type)
        self.assertEqual(0, svc_cor.last_hard_state_id)

        # Now we also set db2 as CRITICAL/HARD... byebye 0 :)
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual(2, svc_db2.last_hard_state_id)

        # -----
        # CRITICAL and OK and OK -> CRITICAL
        # 1st CRITICAL because CRITICAL or CRITICAL -> CRITICAL
        # -----
        # And now the state of the rule must be 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(2, state)

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        # And now we must be CRITICAL/SOFT
        self.assertEqual('CRITICAL', svc_cor.state)
        self.assertEqual('SOFT', svc_cor.state_type)
        self.assertEqual(0, svc_cor.last_hard_state_id)

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        # And now we must be CRITICAL/HARD
        self.assertEqual('CRITICAL', svc_cor.state)
        self.assertEqual('HARD', svc_cor.state_type)
        self.assertEqual(2, svc_cor.last_hard_state_id)

        # And If we set one WARNING?
        self.scheduler_loop(2, [
            [svc_db2, 1, 'WARNING | value1=1 value2=2']
        ])
        self.assertEqual('WARNING', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual(1, svc_db2.last_hard_state_id)

        # -----
        # WARNING and OK and OK -> WARNING
        # 1st WARNING because WARNING or CRITICAL -> WARNING
        # -----
        # Must be WARNING (better no 0 value)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(1, state)

        # And in a HARD
        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        self.assertEqual('WARNING', svc_cor.state)
        self.assertEqual('HARD', svc_cor.state_type)
        self.assertEqual(1, svc_cor.last_hard_state_id)

        # Assert that ERP Is an impact of the problem db2
        self.assertIn(svc_cor.uuid, svc_db2.impacts)
        # and db1 too
        self.assertIn(svc_cor.uuid, svc_db1.impacts)

        # And now all is green :)
        self.scheduler_loop(2, [
            [svc_db1, 0, 'OK'],
            [svc_db2, 0, 'OK'],
        ])

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        self.assertEqual('OK', svc_cor.state)
        self.assertEqual('HARD', svc_cor.state_type)
        self.assertEqual(0, svc_cor.last_hard_state_id)

        # And no more in impact
        self.assertNotIn(svc_cor, svc_db2.impacts)
        self.assertNotIn(svc_cor, svc_db1.impacts)

        # And what if we set 2 service from distant rule CRITICAL?
        # ERP should be still OK
        self.scheduler_loop(2, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2'],
            [svc_web1, 2, 'CRITICAL | value1=1 value2=2'],
            [svc_lvs1, 2, 'CRITICAL | value1=1 value2=2']
        ])

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # -----
        # OK and OK and OK -> OK
        # All OK because OK or CRITICAL -> OK
        # -----
        # What is the svc_cor state now?
        self.assertEqual('OK', svc_cor.state)
        self.assertEqual('HARD', svc_cor.state_type)
        self.assertEqual(0, svc_cor.last_hard_state_id)

    def test_complex_ABCof_business_correlator(self):
        """ BR - complex -bp_rule!5,1,1 of: test_host_0,A|test_host_0,B|test_host_0,C|
        test_host_0,D|test_host_0,E """
        self.run_complex_ABCof_business_correlator(with_pct=False)

    def test_complex_ABCof_pct_business_correlator(self):
        """ BR - complex bp_rule!100%,20%,20% of: test_host_0,A|test_host_0,B|test_host_0,C|
        test_host_0,D|test_host_0,E """
        self.run_complex_ABCof_business_correlator(with_pct=True)

    def run_complex_ABCof_business_correlator(self, with_pct=False):
        """

        :param with_pct: True if a percentage is set
        :return:
        """
        self.print_header()

        # Get the hosts
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore its parent
        router = self._sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = []  # ignore its parent

        # Get the services
        A = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "A")
        self.assertEqual(False, A.got_business_rule)
        self.assertIs(None, A.business_rule)
        A.act_depend_of = []
        B = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "B")
        self.assertEqual(False, B.got_business_rule)
        self.assertIs(None, B.business_rule)
        B.act_depend_of = []
        C = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "C")
        self.assertEqual(False, C.got_business_rule)
        self.assertIs(None, C.business_rule)
        C.act_depend_of = []
        D = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "D")
        self.assertEqual(False, D.got_business_rule)
        self.assertIs(None, D.business_rule)
        D.act_depend_of = []
        E = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "E")
        self.assertEqual(False, E.got_business_rule)
        self.assertIs(None, E.business_rule)
        E.act_depend_of = []

        if with_pct == False:
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                         "Complex_ABCOf")
        else:
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                         "Complex_ABCOf_pct")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        self.assertTrue(svc_cor.got_business_rule)
        self.assertIsNotNone(svc_cor.business_rule)

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        self.assertEqual(bp_rule.operand, 'of:')
        if with_pct == False:
            self.assertEqual(('5', '1', '1'), bp_rule.of_values)
        else:
            self.assertEqual(('100%', '20%', '20%'), bp_rule.of_values)
        self.assertEqual(bp_rule.is_of_mul, True)
        self.assertIsNotNone(bp_rule.sons)
        self.assertEqual(5, len(bp_rule.sons))

        # We've got 5 sons for the BR which are 5 dependency nodes
        # Each dependency node has a son which is the service
        sons = bp_rule.sons
        self.assertEqual('service', sons[0].operand)
        self.assertEqual(A.uuid, sons[0].sons[0])
        self.assertEqual('service', sons[1].operand)
        self.assertEqual(B.uuid, sons[1].sons[0])
        self.assertEqual('service', sons[2].operand)
        self.assertEqual(C.uuid, sons[2].sons[0])
        self.assertEqual('service', sons[3].operand)
        self.assertEqual(D.uuid, sons[3].sons[0])
        self.assertEqual('service', sons[4].operand)
        self.assertEqual(E.uuid, sons[4].sons[0])

        # Now start working on the states
        self.scheduler_loop(1, [
            [A, 0, 'OK'], [B, 0, 'OK'], [C, 0, 'OK'], [D, 0, 'OK'], [E, 0, 'OK']
        ])
        self.assertEqual('OK', A.state)
        self.assertEqual('HARD', A.state_type)
        self.assertEqual('OK', B.state)
        self.assertEqual('HARD', B.state_type)
        self.assertEqual('OK', C.state)
        self.assertEqual('HARD', C.state_type)
        self.assertEqual('OK', D.state)
        self.assertEqual('HARD', D.state_type)
        self.assertEqual('OK', E.state)
        self.assertEqual('HARD', E.state_type)

        # -----
        # All OK with a 5,1,1 of: -> OK
        # -----
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we set the A as CRITICAL/HARD
        self.scheduler_loop(2, [[A, 2, 'CRITICAL']])
        self.assertEqual('CRITICAL', A.state)
        self.assertEqual('HARD', A.state_type)
        self.assertEqual(2, A.last_hard_state_id)

        # -----
        # All OK except 1 with 5,1,1 of: -> CRITICAL
        # -----
        # The rule is 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(2, state)

        # Now we also set B as CRITICAL/HARD...
        self.scheduler_loop(2, [[B, 2, 'CRITICAL']])
        self.assertEqual('CRITICAL', B.state)
        self.assertEqual('HARD', B.state_type)
        self.assertEqual(2, B.last_hard_state_id)

        # -----
        # All OK except 2 with 5,1,1 of: -> CRITICAL
        # -----
        # The state of the rule remains 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(2, state)

        # And If we set A and B WARNING now?
        self.scheduler_loop(2, [[A, 1, 'WARNING'], [B, 1, 'WARNING']])
        self.assertEqual('WARNING', A.state)
        self.assertEqual('HARD', A.state_type)
        self.assertEqual(1, A.last_hard_state_id)
        self.assertEqual('WARNING', B.state)
        self.assertEqual('HARD', B.state_type)
        self.assertEqual(1, B.last_hard_state_id)

        # -----
        # All OK except 2 WARNING with 5,1,1 of: -> WARNING
        # -----
        # Must be WARNING (worse no 0 value for both, like for AND rule)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        print "state", state
        self.assertEqual(1, state)

        # Ok now more fun, with changing of_values and states

        ### W O O O O
        # 4 of: -> Ok (we got 4 OK, and not 4 warn or crit, so it's OK)
        # 5,1,1 -> Warning (at least one warning, and no crit -> warning)
        # 5,2,1 -> OK (we want warning only if we got 2 bad states, so not here)
        # Set one as WARNING and all others as OK
        self.scheduler_loop(1, [
            [A, 1, 'WARNING'], [B, 0, 'OK'], [C, 0, 'OK'], [D, 0, 'OK'], [E, 0, 'OK']
        ])
        # 4 of: -> 4,5,5
        if with_pct == False:
            bp_rule.of_values = ('4', '5', '5')
        else:
            bp_rule.of_values = ('80%', '100%', '100%')
        bp_rule.is_of_mul = False
        # -----
        # All OK except 1 with 4of: -> OK
        # -----
        self.assertEqual(0, bp_rule.get_state(self._sched.hosts, self._sched.services))

        # 5,1,1
        if with_pct == False:
            bp_rule.of_values = ('5', '1', '1')
        else:
            bp_rule.of_values = ('100%', '20%', '20%')
        bp_rule.is_of_mul = True
        self.assertEqual(1, bp_rule.get_state(self._sched.hosts, self._sched.services))

        # 5,2,1
        if with_pct == False:
            bp_rule.of_values = ('5', '2', '1')
        else:
            bp_rule.of_values = ('100%', '40%', '20%')
        bp_rule.is_of_mul = True
        self.assertEqual(0, bp_rule.get_state(self._sched.hosts, self._sched.services))

        ###* W C O O O
        # 4 of: -> Crtitical (not 4 ok, so we take the worse state, the critical)
        # 4,1,1 -> Critical (2 states raise the waring, but on raise critical, so worse state is critical)
        self.scheduler_loop(2, [[A, 1, 'WARNING'], [B, 2, 'Crit']])
        # 4 of: -> 4,5,5
        if with_pct == False:
            bp_rule.of_values = ('4', '5', '5')
        else:
            bp_rule.of_values = ('80%', '100%', '100%')
        bp_rule.is_of_mul = False
        self.assertEqual(2, bp_rule.get_state(self._sched.hosts, self._sched.services))
        # 4,1,1
        if with_pct == False:
            bp_rule.of_values = ('4', '1', '1')
        else:
            bp_rule.of_values = ('40%', '20%', '20%')
        bp_rule.is_of_mul = True
        self.assertEqual(2, bp_rule.get_state(self._sched.hosts, self._sched.services))

        ##* W C C O O
        # * 2 of: OK
        # * 4,1,1 -> Critical (same as before)
        # * 4,1,3 -> warning (the warning rule is raised, but the critical is not)
        self.scheduler_loop(2, [[A, 1, 'WARNING'], [B, 2, 'Crit'], [C, 2, 'Crit']])
        # * 2 of: 2,5,5
        if with_pct == False:
            bp_rule.of_values = ('2', '5', '5')
        else:
            bp_rule.of_values = ('40%', '100%', '100%')
        bp_rule.is_of_mul = False
        self.assertEqual(0, bp_rule.get_state(self._sched.hosts, self._sched.services))
        # * 4,1,1
        if with_pct == False:
            bp_rule.of_values = ('4', '1', '1')
        else:
            bp_rule.of_values = ('80%', '20%', '20%')
        bp_rule.is_of_mul = True
        self.assertEqual(2, bp_rule.get_state(self._sched.hosts, self._sched.services))
        # * 4,1,3
        if with_pct == False:
            bp_rule.of_values = ('4', '1', '3')
        else:
            bp_rule.of_values = ('80%', '20%', '60%')
        bp_rule.is_of_mul = True
        self.assertEqual(1, bp_rule.get_state(self._sched.hosts, self._sched.services))

    # We will try a simple db1 OR db2
    def test_multi_layers(self):
        """ BR - multi-levels rule

        bp_rule!(test_host_0,db1| (test_host_0,db2 & (test_host_0,lvs1|test_host_0,lvs2) ) )
        & test_router_0
        :return:
        """
        self.print_header()

        # Get the hosts
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore its parent
        router = self._sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = []  # ignore its parent

        # Get the services
        svc_db1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db1")
        svc_db1.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db1.got_business_rule)
        self.assertIsNone(svc_db1.business_rule)

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_db2.got_business_rule)
        self.assertIsNone(svc_db2.business_rule)

        svc_lvs1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "lvs1")
        svc_lvs1.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_lvs1.got_business_rule)
        self.assertIsNone(svc_lvs1.business_rule)

        svc_lvs2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "lvs2")
        svc_lvs2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        self.assertFalse(svc_lvs2.got_business_rule)
        self.assertIsNone(svc_lvs2.business_rule)

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "Multi_levels")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        self.assertEqual(True, svc_cor.got_business_rule)
        self.assertIsNot(svc_cor.business_rule, None)
        bp_rule = svc_cor.business_rule
        self.assertEqual('&', bp_rule.operand)

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1, svc_db2, ...
        # and they should be parents of svc_cor
        self.assertIn(svc_cor.uuid, svc_db1.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_db2.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_lvs1.child_dependencies)
        self.assertIn(svc_cor.uuid, svc_lvs2.child_dependencies)

        self.assertIn(svc_db1.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_db2.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_lvs1.uuid, svc_cor.parent_dependencies)
        self.assertIn(svc_lvs2.uuid, svc_cor.parent_dependencies)

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        self.assertEqual(bp_rule.operand, '&')
        self.assertEqual(bp_rule.of_values, ('2', '2', '2'))
        self.assertEqual(bp_rule.not_value, False)
        self.assertEqual(bp_rule.is_of_mul, False)
        self.assertIsNotNone(bp_rule.sons)
        self.assertEqual(2, len(bp_rule.sons))

        # First son is an OR rule
        first_node = bp_rule.sons[0]
        self.assertIsInstance(first_node, DependencyNode)
        self.assertEqual(first_node.operand, '|')
        self.assertEqual(first_node.of_values, ('2', '2', '2'))
        self.assertEqual(first_node.not_value, False)
        self.assertIsNotNone(first_node.sons)
        self.assertIsNot(first_node.sons, [])
        self.assertEqual(2, len(first_node.sons))

        # First son of the node is linked to a service and we have its uuid
        son = first_node.sons[0]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db1.uuid)

        # Second son of the node is also a rule (AND)
        son = first_node.sons[1]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, '&')
        self.assertEqual(son.of_values, ('2', '2', '2'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertIsInstance(son.sons[0], DependencyNode)

        # Second node is a rule
        second_node = son
        self.assertIsInstance(second_node, DependencyNode)
        self.assertEqual(second_node.operand, '&')
        self.assertEqual(second_node.of_values, ('2', '2', '2'))
        self.assertEqual(second_node.not_value, False)
        self.assertIsNotNone(second_node.sons)
        self.assertIsNot(second_node.sons, [])
        self.assertIsInstance(son.sons[0], DependencyNode)

        # First son of the node is linked to a service and we have its uuid
        son = second_node.sons[0]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_db2.uuid)

        # Second son of the node is also a rule (OR)
        son = second_node.sons[1]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, '|')
        self.assertEqual(son.of_values, ('2', '2', '2'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertIsInstance(son.sons[0], DependencyNode)

        # Third node is a rule
        third_node = son
        self.assertIsInstance(third_node, DependencyNode)
        self.assertEqual(third_node.operand, '|')
        self.assertEqual(third_node.of_values, ('2', '2', '2'))
        self.assertEqual(third_node.not_value, False)
        self.assertIsNotNone(third_node.sons)
        self.assertIsNot(third_node.sons, [])
        self.assertIsInstance(son.sons[0], DependencyNode)

        # First son of the node is linked to a service and we have its uuid
        son = third_node.sons[0]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_lvs1.uuid)

        # Second son of the node is also a rule (OR)
        son = third_node.sons[1]
        self.assertIsInstance(son, DependencyNode)
        self.assertEqual(son.operand, 'service')
        self.assertEqual(son.of_values, ('0', '0', '0'))
        self.assertEqual(son.not_value, False)
        self.assertIsNotNone(son.sons)
        self.assertIsNot(son.sons, [])
        self.assertEqual(son.sons[0], svc_lvs2.uuid)

        # Now start working on the states
        self.scheduler_loop(1, [
            [svc_db1, 0, 'OK | rtt=10'],
            [svc_db2, 0, 'OK | value1=1 value2=2'],
            [svc_lvs1, 0, 'OK'],
            [svc_lvs2, 0, 'OK'],
            [host, 0, 'UP'],
            [router, 0, 'UP']
        ])
        self.assertEqual('OK', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual('OK', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual('OK', svc_lvs1.state)
        self.assertEqual('HARD', svc_lvs1.state_type)
        self.assertEqual('OK', svc_lvs2.state)
        self.assertEqual('HARD', svc_lvs2.state_type)

        # All is green, the rule should be green too
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(2, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db1.state)
        self.assertEqual('HARD', svc_db1.state_type)
        self.assertEqual(2, svc_db1.last_hard_state_id)

        # The rule must still be a 0 (OR inside)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we also set db2 as CRITICAL/HARD...
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        self.assertEqual('CRITICAL', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual(2, svc_db2.last_hard_state_id)

        # And now the state of the rule must be 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(2, state)

        # And If we set one WARNING?
        self.scheduler_loop(2, [
            [svc_db2, 1, 'WARNING | value1=1 value2=2']
        ])
        self.assertEqual('WARNING', svc_db2.state)
        self.assertEqual('HARD', svc_db2.state_type)
        self.assertEqual(1, svc_db2.last_hard_state_id)

        # Must be WARNING (better no 0 value)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(1, state)

        # We should got now svc_db2 and svc_db1 as root problems
        self.assertIn(svc_db1.uuid, svc_cor.source_problems)
        self.assertIn(svc_db2.uuid, svc_cor.source_problems)

        # What about now with the router in DOWN state?
        self.scheduler_loop(5, [[router, 2, 'DOWN']])
        self.assertEqual('DOWN', router.state)
        self.assertEqual('HARD', router.state_type)
        self.assertEqual(1, router.last_hard_state_id)

        # Must be CRITICAL (CRITICAL VERSUS DOWN -> DOWN)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(2, state)

        # Now our root problem is router
        self.assertIn(router.uuid, svc_cor.source_problems)

    # We will try a strange rule that ask UP&UP -> DOWN&DONW-> OK
    def test_darthelmet_rule(self):
        #
        # Config is not correct because of a wrong relative path
        # in the main config file
        #
        print "Get the hosts and services"
        now = time.time()
        host = self._sched.hosts.find_by_name("test_darthelmet")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        A = self._sched.hosts.find_by_name("test_darthelmet_A")
        B = self._sched.hosts.find_by_name("test_darthelmet_B")

        self.assertEqual(True, host.got_business_rule)
        self.assertIsNot(host.business_rule, None)
        bp_rule = host.business_rule
        self.assertEqual('|', bp_rule.operand)

        # Now state working on the states
        self.scheduler_loop(3, [[host, 0, 'UP'], [A, 0, 'UP'], [B, 0, 'UP'] ] )
        self.assertEqual('UP', host.state)
        self.assertEqual('HARD', host.state_type)
        self.assertEqual('UP', A.state)
        self.assertEqual('HARD', A.state_type)

        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        print "WTF0", state
        self.assertEqual(0, state)

        # Now we set the A as soft/DOWN
        self.scheduler_loop(1, [[A, 2, 'DOWN']])
        self.assertEqual('DOWN', A.state)
        self.assertEqual('SOFT', A.state_type)
        self.assertEqual(0, A.last_hard_state_id)

        # The business rule must still be 0
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # Now we get A DOWN/HARD
        self.scheduler_loop(3, [[A, 2, 'DOWN']])
        self.assertEqual('DOWN', A.state)
        self.assertEqual('HARD', A.state_type)
        self.assertEqual(1, A.last_hard_state_id)

        # The rule must still be a 2 (or inside)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        print "WFT", state
        self.assertEqual(2, state)

        # Now we also set B as DOWN/HARD, should get back to 0!
        self.scheduler_loop(3, [[B, 2, 'DOWN']])
        self.assertEqual('DOWN', B.state)
        self.assertEqual('HARD', B.state_type)
        self.assertEqual(1, B.last_hard_state_id)

        # And now the state of the rule must be 0 again! (strange rule isn't it?)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)
