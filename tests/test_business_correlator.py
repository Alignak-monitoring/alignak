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

from .alignak_test import AlignakTest


class TestBusinessCorrelator(AlignakTest):

    def setUp(self):
        super(TestBusinessCorrelator, self).setUp()
        self.setup_with_file('cfg/cfg_business_correlator.cfg',
                             dispatching=True)
        assert self.conf_is_correct
        self._sched = self._scheduler

    def launch_internal_check(self, svc_br):
        """ Launch an internal check for the business rule service provided """
        # Launch an internal check
        now = time.time()
        self._sched.add(svc_br.launch_check(
            now - 1, self._sched.hosts, self._sched.services,
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

    def test_br_creation(self):
        """ BR - check creation of a simple services OR (db1 OR db2)

        :return:
        """
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
        assert not svc_db1.got_business_rule
        assert svc_db1.business_rule is None

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        # Not a BR, a simple service
        assert not svc_db2.got_business_rule
        assert svc_db2.business_rule is None

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "Simple_Or")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        assert svc_cor.got_business_rule
        assert svc_cor.business_rule is not None

        svc_cor2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "Simple_Or")
        # Is a Business Rule, not a simple service...
        assert svc_cor2.got_business_rule
        assert svc_cor2.business_rule is not None

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1 and svc_db2
        # and db1 and db2 should be parents of svc_cor
        assert svc_cor.uuid in svc_db1.child_dependencies
        assert svc_cor.uuid in svc_db2.child_dependencies
        assert svc_db1.uuid in svc_cor.parent_dependencies
        assert svc_db2.uuid in svc_cor.parent_dependencies

        # Get the BR associated with svc_cor
        # The BR command is: bp_rule!test_host_0,db1|test_host_0,db2
        bp_rule = svc_cor.business_rule
        assert isinstance(bp_rule, DependencyNode)
        print(("BR scheduler: %s" % bp_rule))

        # Get the BR associated with svc_cor
        # The BR command is: bp_rule!test_host_0,db1|test_host_0,db2
        bp_rule_arbiter = svc_cor2.business_rule
        assert isinstance(bp_rule_arbiter, DependencyNode)
        print(("BR arbiter: %s" % bp_rule_arbiter))

        # Get the BR elements list
        assert isinstance(bp_rule.list_all_elements(), list)
        assert len(bp_rule.list_all_elements()) == 2

        assert bp_rule.operand == '|'
        assert bp_rule.of_values == ('2', '2', '2')
        assert bp_rule.not_value == False
        assert bp_rule.is_of_mul == False
        assert bp_rule.sons is not None

        # We've got 2 sons for the BR which are 2 dependency nodes
        # Each dependency node has a son which is the service
        assert 2 == len(bp_rule.sons)

        # First son is linked to a service and we have its uuid
        son = bp_rule.sons[0]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db1.uuid

        # Second son is also a service
        son = bp_rule.sons[1]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db2.uuid

    def test_simple_or_business_correlator(self):
        """ BR - try a simple services OR (db1 OR db2)

        bp_rule!test_host_0,db1|test_host_0,db2

        :return:
        """
        now = time.time()

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
        assert not svc_db1.got_business_rule
        assert svc_db1.business_rule is None

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        assert not svc_db2.got_business_rule
        assert svc_db2.business_rule is None

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "Simple_Or")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        assert svc_cor.got_business_rule
        assert svc_cor.business_rule is not None

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1 and svc_db2
        # and db1 and db2 should be parents of svc_cor
        assert svc_cor.uuid in svc_db1.child_dependencies
        assert svc_cor.uuid in svc_db2.child_dependencies
        assert svc_db1.uuid in svc_cor.parent_dependencies
        assert svc_db2.uuid in svc_cor.parent_dependencies

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        assert bp_rule.operand == '|'
        assert bp_rule.of_values == ('2', '2', '2')
        assert bp_rule.not_value == False
        assert bp_rule.is_of_mul == False
        assert bp_rule.sons is not None
        assert 2 == len(bp_rule.sons)

        # First son is linked to a service and we have its uuid
        son = bp_rule.sons[0]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db1.uuid

        # Second son is also a service
        son = bp_rule.sons[1]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db2.uuid

        # Now start working on the states
        self.scheduler_loop(1, [
            [svc_db1, 0, 'OK | rtt=10'],
            [svc_db2, 0, 'OK | value1=1 value2=2']
        ])
        assert 'OK' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 'OK' == svc_db2.state
        assert 'HARD' == svc_db2.state_type

        # -----
        # OK or OK -> OK
        # -----
        # When all is ok, the BP rule state is 0
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we set the db1 as soft/CRITICAL
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db1.state
        assert 'SOFT' == svc_db1.state_type
        assert 0 == svc_db1.last_hard_state_id

        # The business rule must still be 0 - only hard states are considered
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 2 == svc_db1.last_hard_state_id

        # -----
        # CRITICAL or OK -> OK
        # -----
        # The rule must still be a 0 (or inside)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we also set db2 as CRITICAL/HARD... byebye 0 :)
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 2 == svc_db2.last_hard_state_id

        # -----
        # CRITICAL or CRITICAL -> CRITICAL
        # -----
        # And now the state of the rule must be 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # And If we set db2 to WARNING?
        self.scheduler_loop(2, [
            [svc_db2, 1, 'WARNING | value1=1 value2=2']
        ])
        assert 'WARNING' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 1 == svc_db2.last_hard_state_id

        # -----
        # CRITICAL or WARNING -> WARNING
        # -----
        # Must be WARNING (better no 0 value)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 1 == state

        # We acknowledge db2
        cmd = "[%lu] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;db2;2;1;1;lausser;blablub" % now
        self._sched.run_external_commands([cmd])
        assert True == svc_db2.problem_has_been_acknowledged

        # -----
        # CRITICAL or ACK(WARNING) -> OK
        # -----
        # Must be OK (ACK(WARNING) is OK)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # We unacknowledge then downtime db2
        duration = 300
        cmd = "[%lu] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;db2" % now
        self._sched.run_external_commands([cmd])
        assert False == svc_db2.problem_has_been_acknowledged

        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;db2;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self._sched.run_external_commands([cmd])
        self.scheduler_loop(1, [[svc_cor, None, None]])
        assert svc_db2.scheduled_downtime_depth > 0
        assert True == svc_db2.in_scheduled_downtime

        # -----
        # CRITICAL or DOWNTIME(WARNING) -> OK
        # -----
        # Must be OK (DOWNTIME(WARNING) is OK)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

    def test_simple_or_business_correlator_with_schedule(self):
        """ BR - try a simple services OR (db1 OR db2) with internal checks

        bp_rule!test_host_0,db1|test_host_0,db2

        :return:
        """
        now = time.time()

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
        assert not svc_db1.got_business_rule
        assert svc_db1.business_rule is None

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        assert not svc_db2.got_business_rule
        assert svc_db2.business_rule is None

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "Simple_Or")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        assert svc_cor.got_business_rule
        assert svc_cor.business_rule is not None

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1 and svc_db2
        # and db1 and db2 should be parents of svc_cor
        assert svc_cor.uuid in svc_db1.child_dependencies
        assert svc_cor.uuid in svc_db2.child_dependencies
        assert svc_db1.uuid in svc_cor.parent_dependencies
        assert svc_db2.uuid in svc_cor.parent_dependencies

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        assert bp_rule.operand == '|'
        assert bp_rule.of_values == ('2', '2', '2')
        assert bp_rule.not_value == False
        assert bp_rule.is_of_mul == False
        assert bp_rule.sons is not None
        assert 2 == len(bp_rule.sons)

        # First son is linked to a service and we have its uuid
        son = bp_rule.sons[0]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db1.uuid

        # Second son is also a service
        son = bp_rule.sons[1]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db2.uuid

        # Now start working on the states
        self.scheduler_loop(1, [
            [svc_db1, 0, 'OK | rtt=10'],
            [svc_db2, 0, 'OK | value1=1 value2=2']
        ])
        assert 'OK' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 'OK' == svc_db2.state
        assert 'HARD' == svc_db2.state_type

        # -----
        # OK or OK -> OK
        # -----
        # When all is ok, the BP rule state is 0
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        assert 'OK' == svc_cor.state
        assert 'HARD' == svc_cor.state_type
        assert 0 == svc_cor.last_hard_state_id

        # Now we set the db1 as soft/CRITICAL
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db1.state
        assert 'SOFT' == svc_db1.state_type
        assert 0 == svc_db1.last_hard_state_id

        # The business rule must still be 0
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        assert 'OK' == svc_cor.state
        assert 'HARD' == svc_cor.state_type
        assert 0 == svc_cor.last_hard_state_id

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 2 == svc_db1.last_hard_state_id

        # The rule must still be a 0 (or inside)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        assert 'OK' == svc_cor.state
        assert 'HARD' == svc_cor.state_type
        assert 0 == svc_cor.last_hard_state_id

        # Now we also set db2 as CRITICAL/HARD... byebye 0 :)
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 2 == svc_db2.last_hard_state_id

        # And now the state of the rule must be 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        assert 'CRITICAL' == svc_cor.state
        assert 'SOFT' == svc_cor.state_type
        assert 0 == svc_cor.last_hard_state_id

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        assert 'CRITICAL' == svc_cor.state
        assert 'HARD' == svc_cor.state_type
        assert 2 == svc_cor.last_hard_state_id

        # And If we set db2 to WARNING?
        self.scheduler_loop(2, [
            [svc_db2, 1, 'WARNING | value1=1 value2=2']
        ])
        assert 'WARNING' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 1 == svc_db2.last_hard_state_id

        # Must be WARNING (better no 0 value)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 1 == state

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        assert 'WARNING' == svc_cor.state
        assert 'HARD' == svc_cor.state_type
        assert 1 == svc_cor.last_hard_state_id

        # Assert that Simple_Or Is an impact of the problem db2
        assert svc_cor.uuid in svc_db2.impacts
        # and db1 too
        assert svc_cor.uuid in svc_db1.impacts

        # We acknowledge db2
        cmd = "[%lu] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;db2;2;1;1;lausser;blablub" % now
        self._sched.run_external_commands([cmd])
        assert True == svc_db2.problem_has_been_acknowledged

       # Must be OK
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

       # And in a HARD
       # Launch internal check"
        self.launch_internal_check(svc_cor)
        assert 'OK' == svc_cor.state
        assert'HARD' == svc_cor.state_type
        assert 0 == svc_cor.last_hard_state_id

        # db2 WARNING, db1 CRITICAL, we unacknowledge then downtime db2
        duration = 300
        cmd = "[%lu] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;db2" % now
        self._sched.run_external_commands([cmd])
        assert False == svc_db2.problem_has_been_acknowledged

        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;db2;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self._sched.run_external_commands([cmd])
        self.scheduler_loop(1, [[svc_cor, None, None]])
        assert svc_db2.scheduled_downtime_depth > 0
        assert True == svc_db2.in_scheduled_downtime

        # Must be OK
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # And in a HARD
        # Launch internal check
        self.launch_internal_check(svc_cor)
        assert 'OK' == svc_cor.state
        assert 'HARD'== svc_cor.state_type
        assert 0 == svc_cor.last_hard_state_id

    def test_simple_or_not_business_correlator(self):
        """ BR - try a simple services OR (db1 OR NOT db2)

        bp_rule!test_host_0,db1|!test_host_0,db2

        :return:
        """
        now = time.time()

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
        assert not svc_db1.got_business_rule
        assert svc_db1.business_rule is None

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        assert not svc_db2.got_business_rule
        assert svc_db2.business_rule is None

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "Simple_Or_not")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        assert svc_cor.got_business_rule
        assert svc_cor.business_rule is not None

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1 and svc_db2
        # and db1 and db2 should be parents of svc_cor
        assert svc_cor.uuid in svc_db1.child_dependencies
        assert svc_cor.uuid in svc_db2.child_dependencies
        assert svc_db1.uuid in svc_cor.parent_dependencies
        assert svc_db2.uuid in svc_cor.parent_dependencies

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        assert bp_rule.operand == '|'
        assert bp_rule.of_values == ('2', '2', '2')
        assert bp_rule.not_value == False
        assert bp_rule.is_of_mul == False
        assert bp_rule.sons is not None
        assert 2 == len(bp_rule.sons)

        # First son is linked to a service and we have its uuid
        son = bp_rule.sons[0]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db1.uuid

        # Second son is also a service
        son = bp_rule.sons[1]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        # This service is NOT valued
        assert son.not_value == True
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db2.uuid

        # Now start working on the states
        self.scheduler_loop(1, [
            [svc_db1, 0, 'OK | rtt=10'],
            [svc_db2, 0, 'OK | value1=1 value2=2']
        ])
        assert 'OK' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 'OK' == svc_db2.state
        assert 'HARD' == svc_db2.state_type

        # -----
        # OK or NOT OK -> OK
        # -----
        # When all is ok, the BP rule state is 0
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we set the db1 as soft/CRITICAL
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db1.state
        assert 'SOFT' == svc_db1.state_type
        assert 0 == svc_db1.last_hard_state_id

        # The business rule must still be 0 - only hard states are considered
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 2 == svc_db1.last_hard_state_id

        # -----
        # CRITICAL or NOT OK -> CRITICAL
        # -----
        # The rule must still be a 0 (or inside)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # Now we also set db2 as CRITICAL/HARD... byebye 0 :)
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 2 == svc_db2.last_hard_state_id

        # -----
        # CRITICAL or NOT CRITICAL -> OK
        # -----
        # And now the state of the rule must be 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # And If we set db2 WARNING?
        self.scheduler_loop(2, [
            [svc_db2, 1, 'WARNING | value1=1 value2=2']
        ])
        assert 'WARNING' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 1 == svc_db2.last_hard_state_id

        # -----
        # CRITICAL or NOT WARNING -> WARNING
        # -----
        # Must be WARNING (better no 0 value)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 1 == state

        # We acknowledge db2
        cmd = "[%lu] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;db2;2;1;1;lausser;blablub" % now
        self._sched.run_external_commands([cmd])
        assert True == svc_db2.problem_has_been_acknowledged

        # -----
        # CRITICAL or NOT ACK(WARNING) -> CRITICAL
        # -----
        # Must be WARNING (ACK(WARNING) is OK)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # We unacknowledge then downtime db2
        duration = 300
        cmd = "[%lu] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;db2" % now
        self._sched.run_external_commands([cmd])
        assert False == svc_db2.problem_has_been_acknowledged

        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;db2;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self._sched.run_external_commands([cmd])
        self.scheduler_loop(1, [[svc_cor, None, None]])
        assert svc_db2.scheduled_downtime_depth > 0
        assert True == svc_db2.in_scheduled_downtime

        # -----
        # CRITICAL or NOT DOWNTIME(WARNING) -> CRITICAL
        # -----
        # Must be CRITICAL (business_rule_downtime_as_ok -> DOWNTIME(WARNING) is OK)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

    def test_simple_and_business_correlator(self):
        """ BR - try a simple services AND (db1 AND db2)

        bp_rule!test_host_0,db1&test_host_0,db2

        :return:
        """
        now = time.time()

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
        assert not svc_db1.got_business_rule
        assert svc_db1.business_rule is None

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        assert not svc_db2.got_business_rule
        assert svc_db2.business_rule is None

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                     "Simple_And")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        assert svc_cor.got_business_rule
        assert svc_cor.business_rule is not None

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1 and svc_db2
        # and db1 and db2 should be parents of svc_cor
        assert svc_cor.uuid in svc_db1.child_dependencies
        assert svc_cor.uuid in svc_db2.child_dependencies
        assert svc_db1.uuid in svc_cor.parent_dependencies
        assert svc_db2.uuid in svc_cor.parent_dependencies

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        assert bp_rule.operand == '&'
        assert bp_rule.of_values == ('2', '2', '2')
        assert bp_rule.not_value == False
        assert bp_rule.is_of_mul == False
        assert bp_rule.sons is not None
        assert 2 == len(bp_rule.sons)

        # First son is linked to a service and we have its uuid
        son = bp_rule.sons[0]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db1.uuid

        # Second son is also a service
        son = bp_rule.sons[1]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db2.uuid

        # Now start working on the states
        self.scheduler_loop(1, [
            [svc_db1, 0, 'OK | rtt=10'],
            [svc_db2, 0, 'OK | value1=1 value2=2'] 
        ])
        assert 'OK' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 'OK' == svc_db2.state
        assert 'HARD' == svc_db2.state_type

        # -----
        # OK and OK -> OK
        # -----
        # When all is ok, the BP rule state is 0
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we set the db1 as soft/CRITICAL
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db1.state
        assert 'SOFT' == svc_db1.state_type
        assert 0 == svc_db1.last_hard_state_id

        # The business rule must still be 0 because we want HARD states
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(2, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 2 == svc_db1.last_hard_state_id

        # -----
        # CRITICAL and OK -> CRITICAL
        # -----
        # The rule must go CRITICAL
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # Now we set db2 as WARNING/HARD...
        self.scheduler_loop(2, [
            [svc_db2, 1, 'WARNING | value1=1 value2=2']
        ])
        assert 'WARNING' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 1 == svc_db2.last_hard_state_id

        # -----
        # CRITICAL and WARNING -> CRITICAL
        # -----
        # The state of the rule remains 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # And If we set db1 to WARNING too?
        self.scheduler_loop(2, [
            [svc_db1, 1, 'WARNING | value1=1 value2=2']
        ])
        assert 'WARNING' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 1 == svc_db1.last_hard_state_id

        # -----
        # WARNING and WARNING -> WARNING
        # -----
        # Must be WARNING (worse no 0 value for both)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 1 == state

         # We set db2 CRITICAL then we acknowledge it
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 2 == svc_db2.last_hard_state_id

        cmd = "[%lu] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;db2;2;1;1;lausser;blablub" % now
        self._sched.run_external_commands([cmd])
        assert True == svc_db2.problem_has_been_acknowledged

        # -----
        # WARNING and ACK(CRITICAL) -> WARNING
        # -----
        # Must be WARNING (ACK(CRITICAL) is OK)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 1 == state

        # We unacknowledge then downtime db2
        duration = 300
        cmd = "[%lu] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;db2" % now
        self._sched.run_external_commands([cmd])
        assert False == svc_db2.problem_has_been_acknowledged

        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;db2;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self._sched.run_external_commands([cmd])
        self.scheduler_loop(1, [[svc_cor, None, None]])
        assert svc_db2.scheduled_downtime_depth > 0
        assert True == svc_db2.in_scheduled_downtime

        # -----
        # WARNING and DOWNTIME(CRITICAL) -> WARNING
        # -----
        # Must be OK (DOWNTIME(CRITICAL) is OK)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 1 == state

    def test_simple_and_not_business_correlator(self):
        """ BR - try a simple services AND NOT (db1 AND NOT db2)

        bp_rule!test_host_0,db1&!test_host_0,db2
        """
        now = time.time()

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
        assert not svc_db1.got_business_rule
        assert svc_db1.business_rule is None

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        assert not svc_db2.got_business_rule
        assert svc_db2.business_rule is None

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                     "Simple_And_not")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        assert svc_cor.got_business_rule
        assert svc_cor.business_rule is not None

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1 and svc_db2
        # and db1 and db2 should be parents of svc_cor
        assert svc_cor.uuid in svc_db1.child_dependencies
        assert svc_cor.uuid in svc_db2.child_dependencies
        assert svc_db1.uuid in svc_cor.parent_dependencies
        assert svc_db2.uuid in svc_cor.parent_dependencies

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        assert bp_rule.operand == '&'
        assert bp_rule.of_values == ('2', '2', '2')
        # Not value remains False because one service is NOT ... but the BR is not NON
        assert bp_rule.not_value == False
        assert bp_rule.is_of_mul == False
        assert bp_rule.sons is not None
        assert 2 == len(bp_rule.sons)

        # First son is linked to a service and we have its uuid
        son = bp_rule.sons[0]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db1.uuid

        # Second son is also a service
        son = bp_rule.sons[1]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        # This service is NOT valued
        assert son.not_value == True
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db2.uuid

        # Now start working on the states
        self.scheduler_loop(2, [
            [svc_db1, 0, 'OK | value1=1 value2=2'],
            [svc_db2, 2, 'CRITICAL | rtt=10']
        ])
        assert 'OK' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 'CRITICAL' == svc_db2.state
        assert 'HARD' == svc_db2.state_type

        # -----
        # OK and not CRITICAL -> OK
        # -----
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we set the db1 as soft/CRITICAL
        self.scheduler_loop(1, [[svc_db1, 2, 'CRITICAL | value1=1 value2=2']])
        assert 'CRITICAL' == svc_db1.state
        assert 'SOFT' == svc_db1.state_type
        assert 0 == svc_db1.last_hard_state_id

        # The business rule must still be 0
        # becase we want HARD states
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(1, [[svc_db1, 2, 'CRITICAL | value1=1 value2=2']])
        assert 'CRITICAL' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 2 == svc_db1.last_hard_state_id

        # -----
        # CRITICAL and not CRITICAL -> CRITICAL
        # -----
        # The rule must go CRITICAL
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # Now we also set db2 as WARNING/HARD...
        self.scheduler_loop(2, [[svc_db2, 1, 'WARNING | value1=1 value2=2']])
        assert 'WARNING' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 1 == svc_db2.last_hard_state_id

        # -----
        # CRITICAL and not WARNING -> CRITICAL
        # -----
        # And now the state of the rule must be 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # And If we set db1 to WARNING too?
        self.scheduler_loop(2, [[svc_db1, 1, 'WARNING | value1=1 value2=2']])
        assert 'WARNING' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 1 == svc_db1.last_hard_state_id

        # -----
        # WARNING and not CRITICAL -> WARNING
        # -----
        # Must be WARNING (worse no 0 value for both)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 1 == state

        # Now try to get ok in both place, should be bad :)
        self.scheduler_loop(2, [[svc_db1, 0, 'OK | value1=1 value2=2'], [svc_db2, 0, 'OK | value1=1 value2=2']])
        assert 'OK' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 0 == svc_db1.last_hard_state_id
        assert 'OK' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 0 == svc_db2.last_hard_state_id

        # -----
        # OK and not OK -> CRITICAL
        # -----
        # Must be CRITICAL (ok and not ok IS no OK :) )
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # We set db2 CRITICAL then we acknowledge it
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 2 == svc_db2.last_hard_state_id

        cmd = "[%lu] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;db2;2;1;1;lausser;blablub" % now
        self._sched.run_external_commands([cmd])
        assert True == svc_db2.problem_has_been_acknowledged

        # -----
        # OK and not ACK(CRITICAL) -> CRITICAL
        # -----
        # Must be CRITICAL (ACK(CRITICAL) is OK)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # We unacknowledge then downtime db2
        duration = 300
        cmd = "[%lu] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;db2" % now
        self._sched.run_external_commands([cmd])
        assert False == svc_db2.problem_has_been_acknowledged

        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;db2;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self._sched.run_external_commands([cmd])
        self.scheduler_loop(1, [[svc_cor, None, None]])
        assert svc_db2.scheduled_downtime_depth > 0
        assert True == svc_db2.in_scheduled_downtime

        # -----
        # OK and not DOWNTIME(CRITICAL) -> CRITICAL
        # -----
        # Must be CRITICAL (DOWNTIME(CRITICAL) is OK)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

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
        now = time.time()

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
        assert not svc_db1.got_business_rule
        assert svc_db1.business_rule is None

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        assert not svc_db2.got_business_rule
        assert svc_db2.business_rule is None

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
        assert svc_cor.got_business_rule
        assert svc_cor.business_rule is not None

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1 and svc_db2
        # and db1 and db2 should be parents of svc_cor
        assert svc_cor.uuid in svc_db1.child_dependencies
        assert svc_cor.uuid in svc_db2.child_dependencies
        assert svc_db1.uuid in svc_cor.parent_dependencies
        assert svc_db2.uuid in svc_cor.parent_dependencies

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        assert bp_rule.operand == 'of:'
        # Simple 1of: so in fact a triple ('1','2','2') (1of and MAX,MAX
        if with_pct is True:
            if with_neg is True:
                assert ('-50%', '2', '2') == bp_rule.of_values
            else:
                assert ('50%', '2', '2') == bp_rule.of_values
        else:
            if with_neg is True:
                assert ('-1', '2', '2') == bp_rule.of_values
            else:
                assert ('1', '2', '2') == bp_rule.of_values
        assert bp_rule.not_value == False
        assert bp_rule.is_of_mul == False
        assert bp_rule.sons is not None
        assert 2 == len(bp_rule.sons)

        # We've got 2 sons for the BR which are 2 dependency nodes
        # Each dependency node has a son which is the service
        assert 2 == len(bp_rule.sons)

        # First son is linked to a service and we have its uuid
        son = bp_rule.sons[0]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db1.uuid

        # Second son is also a service
        son = bp_rule.sons[1]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db2.uuid

        # Now start working on the states
        self.scheduler_loop(1, [
            [svc_db1, 0, 'OK | rtt=10'],
            [svc_db2, 0, 'OK | value1=1 value2=2']
        ])
        assert 'OK' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 'OK' == svc_db2.state
        assert 'HARD' == svc_db2.state_type

        # -----
        # OK 1of OK -> OK
        # -----
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we set the db1 as soft/CRITICAL
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db1.state
        assert 'SOFT' == svc_db1.state_type
        assert 0 == svc_db1.last_hard_state_id

        # The business rule must still be 0
        # becase we want HARD states
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(1, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 2 == svc_db1.last_hard_state_id

        # -----
        # CRITCAL 1of OK -> OK
        # -----
        # The rule still be OK
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we also set db2 as CRITICAL/HARD...
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 2 == svc_db2.last_hard_state_id

        # -----
        # CRITICAL 1of CRITICAL -> CRITICAL
        # -----
        # And now the state of the rule must be 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # And If we set db1 WARNING now?
        self.scheduler_loop(2, [[svc_db1, 1, 'WARNING | value1=1 value2=2']])
        assert 'WARNING' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 1 == svc_db1.last_hard_state_id

        # -----
        # WARNING 1of CRITICAL -> WARNING
        # -----
        # Must be WARNING (worse no 0 value for both, like for AND rule)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 1 == state

        # We acknowledge bd2
        cmd = "[%lu] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;db2;2;1;1;lausser;blablub" % now
        self._sched.run_external_commands([cmd])
        assert True == svc_db2.problem_has_been_acknowledged

        # -----
        # WARNING 1of ACK(CRITICAL) -> OK
        # -----
        # Must be OK (ACK(CRITICAL) is OK)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # We unacknowledge then downtime db2
        duration = 300
        cmd = "[%lu] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;db2" % now
        self._sched.run_external_commands([cmd])
        assert False == svc_db2.problem_has_been_acknowledged

        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;db2;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self._sched.run_external_commands([cmd])
        self.scheduler_loop(1, [[svc_cor, None, None]])
        assert svc_db2.scheduled_downtime_depth > 0
        assert True == svc_db2.in_scheduled_downtime

        # -----
        # WARNING 1of DOWNTIME(CRITICAL) -> OK
        # -----
        # Must be OK (DOWNTIME(CRITICAL) is OK)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

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
        assert svc_cor.got_business_rule
        assert svc_cor.business_rule is not None

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        assert bp_rule.operand == 'of:'
        # Simple 1of: so in fact a triple ('1','2','2') (1of and MAX,MAX
        if with_pct is True:
            if with_neg is True:
                assert ('-50%', '2', '2') == bp_rule.of_values
            else:
                assert ('50%', '2', '2') == bp_rule.of_values
        else:
            if with_neg is True:
                assert ('-1', '2', '2') == bp_rule.of_values
            else:
                assert ('1', '2', '2') == bp_rule.of_values

        sons = bp_rule.sons
        print("Sons,", sons)
        # We've got 2 sons, 2 services nodes
        assert 2 == len(sons)
        assert 'host' == sons[0].operand
        assert host.uuid == sons[0].sons[0]
        assert 'host' == sons[1].operand
        assert router.uuid == sons[1].sons[0]

    def test_dep_node_list_elements(self):
        """ BR - list all elements

        :return:
        """
        svc_db1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db1")
        assert False == svc_db1.got_business_rule
        assert None is svc_db1.business_rule
        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        assert False == svc_db2.got_business_rule
        assert None is svc_db2.business_rule
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "Simple_Or")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        assert True == svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        bp_rule = svc_cor.business_rule
        assert '|' == bp_rule.operand

        print("All elements", bp_rule.list_all_elements())
        all_elements = bp_rule.list_all_elements()

        assert 2 == len(all_elements)
        assert svc_db2.uuid in all_elements
        assert svc_db1.uuid in all_elements

    def test_full_erp_rule_with_schedule(self):
        """ Full ERP rule with real checks scheduled

        bp_rule!(test_host_0,db1|test_host_0,db2) & (test_host_0,web1|test_host_0,web2)
         & (test_host_0,lvs1|test_host_0,lvs2) 

        :return:
        """
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
        assert not svc_db1.got_business_rule
        assert svc_db1.business_rule is None

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        assert not svc_db2.got_business_rule
        assert svc_db2.business_rule is None

        svc_web1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "web1")
        svc_web1.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        assert not svc_web1.got_business_rule
        assert svc_web1.business_rule is None
        
        svc_web2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "web2")
        svc_web2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        assert not svc_web2.got_business_rule
        assert svc_web2.business_rule is None

        svc_lvs1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "lvs1")
        svc_lvs1.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        assert not svc_lvs1.got_business_rule
        assert svc_lvs1.business_rule is None

        svc_lvs2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "lvs2")
        svc_lvs2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        assert not svc_lvs2.got_business_rule
        assert svc_lvs2.business_rule is None

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "ERP")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        assert True == svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        bp_rule = svc_cor.business_rule
        assert '&' == bp_rule.operand

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1, svc_db2, ...
        # and they should be parents of svc_cor
        assert svc_cor.uuid in svc_db1.child_dependencies
        assert svc_cor.uuid in svc_db2.child_dependencies
        assert svc_cor.uuid in svc_web1.child_dependencies
        assert svc_cor.uuid in svc_web2.child_dependencies
        assert svc_cor.uuid in svc_lvs1.child_dependencies
        assert svc_cor.uuid in svc_lvs2.child_dependencies

        assert svc_db1.uuid in svc_cor.parent_dependencies
        assert svc_db2.uuid in svc_cor.parent_dependencies
        assert svc_web1.uuid in svc_cor.parent_dependencies
        assert svc_web2.uuid in svc_cor.parent_dependencies
        assert svc_lvs1.uuid in svc_cor.parent_dependencies
        assert svc_lvs2.uuid in svc_cor.parent_dependencies

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        assert bp_rule.operand == '&'
        assert bp_rule.of_values == ('3', '3', '3')
        assert bp_rule.not_value == False
        assert bp_rule.is_of_mul == False
        assert bp_rule.sons is not None
        assert 3 == len(bp_rule.sons)

        # First son is an OR rule for the DB node
        db_node = bp_rule.sons[0]
        assert isinstance(db_node, DependencyNode)
        assert db_node.operand == '|'
        assert db_node.of_values == ('2', '2', '2')
        assert db_node.not_value == False
        assert db_node.sons is not None
        assert db_node.sons is not []
        assert 2 == len(db_node.sons)

        # First son of DB node is linked to a service and we have its uuid
        son = db_node.sons[0]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db1.uuid

        # Second son of DB node is also a service
        son = db_node.sons[1]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db2.uuid

        # Second son is an OR rule for the Web node
        web_node = bp_rule.sons[1]
        assert isinstance(web_node, DependencyNode)
        assert web_node.operand == '|'
        assert web_node.of_values == ('2', '2', '2')
        assert web_node.not_value == False
        assert web_node.sons is not None
        assert web_node.sons is not []
        assert 2 == len(web_node.sons)

        # First son of Web node is linked to a service and we have its uuid
        son = web_node.sons[0]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_web1.uuid

        # Second son of Web node is also a service
        son = web_node.sons[1]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_web2.uuid

        # First son is an OR rule for the LVS node
        lvs_node = bp_rule.sons[2]
        assert isinstance(lvs_node, DependencyNode)
        assert lvs_node.operand == '|'
        assert lvs_node.of_values == ('2', '2', '2')
        assert lvs_node.not_value == False
        assert lvs_node.sons is not None
        assert lvs_node.sons is not []
        assert 2 == len(lvs_node.sons)

        # First son of LVS node is linked to a service and we have its uuid
        son = lvs_node.sons[0]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_lvs1.uuid

        # Second son of LVS node is also a service
        son = lvs_node.sons[1]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_lvs2.uuid

        # Now start working on the states
        self.scheduler_loop(1, [
            [svc_db1, 0, 'OK'],
            [svc_db2, 0, 'OK'],
            [svc_web1, 0, 'OK'],
            [svc_web2, 0, 'OK'],
            [svc_lvs1, 0, 'OK'],
            [svc_lvs2, 0, 'OK'],
        ])
        assert 'OK' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 'OK' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 'OK' == svc_web1.state
        assert 'HARD' == svc_web1.state_type
        assert 'OK' == svc_web2.state
        assert 'HARD' == svc_web2.state_type
        assert 'OK' == svc_lvs1.state
        assert 'HARD' == svc_lvs1.state_type
        assert 'OK' == svc_lvs2.state
        assert 'HARD' == svc_lvs2.state_type

        # -----
        # (OK or OK) and (OK or OK) and (OK or OK) -> OK
        # -----
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        assert 'OK' == svc_cor.state
        assert 'HARD' == svc_cor.state_type
        assert 0 == svc_cor.last_hard_state_id

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(2, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 2 == svc_db1.last_hard_state_id

        # -----
        # (CRITICAL or OK) and (OK or OK) and (OK or OK) -> OK
        # 1st OK because OK or CRITICAL -> OK
        # -----
        # The rule must still be a 0 (or inside)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        print("ERP: Look at svc_cor state", svc_cor.state)
        # What is the svc_cor state now?
        assert 'OK' == svc_cor.state
        assert 'HARD' == svc_cor.state_type
        assert 0 == svc_cor.last_hard_state_id

        # Now we also set db2 as CRITICAL/HARD... byebye 0 :)
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 2 == svc_db2.last_hard_state_id

        # -----
        # (CRITICAL or CRITICAL) and (OK or OK) and (OK or OK) -> OK
        # 1st CRITICAL because CRITICAL or CRITICAL -> CRITICAL
        # -----
        # And now the state of the rule must be 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        # And now we must be CRITICAL/SOFT
        assert 'CRITICAL' == svc_cor.state
        assert 'SOFT' == svc_cor.state_type
        assert 0 == svc_cor.last_hard_state_id

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        # And now we must be CRITICAL/HARD
        assert 'CRITICAL' == svc_cor.state
        assert 'HARD' == svc_cor.state_type
        assert 2 == svc_cor.last_hard_state_id

        # And If we set db2 to WARNING?
        self.scheduler_loop(2, [
            [svc_db2, 1, 'WARNING | value1=1 value2=2']
        ])
        assert 'WARNING' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 1 == svc_db2.last_hard_state_id

        # -----
        # (CRITICAL or WARNING) and (OK or OK) and (OK or OK) -> OK
        # 1st WARNING because CRITICAL or WARNING -> WARNING
        # -----
        # Must be WARNING (better no 0 value)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 1 == state

        # And in a HARD
        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        assert 'WARNING' == svc_cor.state
        assert 'HARD' == svc_cor.state_type
        assert 1 == svc_cor.last_hard_state_id

        # Assert that ERP Is an impact of the problem db2
        assert svc_cor.uuid in svc_db2.impacts
        # and db1 too
        assert svc_cor.uuid in svc_db1.impacts

        # And now all is green :)
        self.scheduler_loop(2, [
            [svc_db1, 0, 'OK'],
            [svc_db2, 0, 'OK'],
        ])

        # Launch an internal check
        self.launch_internal_check(svc_cor)

        # What is the svc_cor state now?
        assert 'OK' == svc_cor.state
        assert 'HARD' == svc_cor.state_type
        assert 0 == svc_cor.last_hard_state_id

        # And no more in impact
        assert svc_cor not in svc_db2.impacts
        assert svc_cor not in svc_db1.impacts

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
        # (CRITICAL or OK) and (OK or OK) and (OK or OK) -> OK
        # All OK because CRITICAL or OK -> OK
        # -----
        # What is the svc_cor state now?
        assert 'OK' == svc_cor.state
        assert 'HARD' == svc_cor.state_type
        assert 0 == svc_cor.last_hard_state_id

        # We set bd 2 to CRITICAL and acknowledge it
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 2 == svc_db2.last_hard_state_id

        cmd = "[%lu] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;db2;2;1;1;lausser;blablub" % now
        self._sched.run_external_commands([cmd])
        assert True == svc_db2.problem_has_been_acknowledged

        # -----
        # (CRITICAL or ACK(CRITICAL)) and (OK or OK) and (OK or OK) -> OK
        # All OK because CRITICAL or ACK(CRITICAL) -> OK
        # -----
        # Must be OK
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # We unacknowledge then downtime db2
        duration = 300
        cmd = "[%lu] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;db2" % now
        self._sched.run_external_commands([cmd])
        assert False == svc_db2.problem_has_been_acknowledged

        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;db2;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self._sched.run_external_commands([cmd])
        self.scheduler_loop(1, [[svc_cor, None, None]])
        assert svc_db2.scheduled_downtime_depth > 0
        assert True == svc_db2.in_scheduled_downtime

        # -----
        # (CRITICAL or DOWNTIME(CRITICAL)) and (OK or OK) and (OK or OK) -> OK
        #  All OK because CRITICAL or DOWNTIME(CRITICAL) -> OK
        # -----
        # Must be OK
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

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
        now = time.time()

        # Get the hosts
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore its parent
        router = self._sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = []  # ignore its parent

        # Get the services
        A = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "A")
        assert False == A.got_business_rule
        assert None is A.business_rule
        A.act_depend_of = []
        B = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "B")
        assert False == B.got_business_rule
        assert None is B.business_rule
        B.act_depend_of = []
        C = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "C")
        assert False == C.got_business_rule
        assert None is C.business_rule
        C.act_depend_of = []
        D = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "D")
        assert False == D.got_business_rule
        assert None is D.business_rule
        D.act_depend_of = []
        E = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "E")
        assert False == E.got_business_rule
        assert None is E.business_rule
        E.act_depend_of = []

        if with_pct == False:
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                         "Complex_ABCOf")
        else:
            svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                         "Complex_ABCOf_pct")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        # Is a Business Rule, not a simple service...
        assert svc_cor.got_business_rule
        assert svc_cor.business_rule is not None

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        assert bp_rule.operand == 'of:'
        if with_pct == False:
            assert ('5', '1', '1') == bp_rule.of_values
        else:
            assert ('100%', '20%', '20%') == bp_rule.of_values
        assert bp_rule.is_of_mul == True
        assert bp_rule.sons is not None
        assert 5 == len(bp_rule.sons)

        # We've got 5 sons for the BR which are 5 dependency nodes
        # Each dependency node has a son which is the service
        sons = bp_rule.sons
        assert 'service' == sons[0].operand
        assert A.uuid == sons[0].sons[0]
        assert 'service' == sons[1].operand
        assert B.uuid == sons[1].sons[0]
        assert 'service' == sons[2].operand
        assert C.uuid == sons[2].sons[0]
        assert 'service' == sons[3].operand
        assert D.uuid == sons[3].sons[0]
        assert 'service' == sons[4].operand
        assert E.uuid == sons[4].sons[0]

        # Now start working on the states
        self.scheduler_loop(1, [
            [A, 0, 'OK'], [B, 0, 'OK'], [C, 0, 'OK'], [D, 0, 'OK'], [E, 0, 'OK']
        ])
        assert 'OK' == A.state
        assert 'HARD' == A.state_type
        assert 'OK' == B.state
        assert 'HARD' == B.state_type
        assert 'OK' == C.state
        assert 'HARD' == C.state_type
        assert 'OK' == D.state
        assert 'HARD' == D.state_type
        assert 'OK' == E.state
        assert 'HARD' == E.state_type

        # -----
        # All OK with a 5,1,1 of: -> OK
        # -----
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we set the A as CRITICAL/HARD
        self.scheduler_loop(2, [[A, 2, 'CRITICAL']])
        assert 'CRITICAL' == A.state
        assert 'HARD' == A.state_type
        assert 2 == A.last_hard_state_id

        # -----
        # All OK except 1 with 5,1,1 of: -> CRITICAL
        # -----
        # The rule is 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # Now we also set B as CRITICAL/HARD...
        self.scheduler_loop(2, [[B, 2, 'CRITICAL']])
        assert 'CRITICAL' == B.state
        assert 'HARD' == B.state_type
        assert 2 == B.last_hard_state_id

        # -----
        # All OK except 2 with 5,1,1 of: -> CRITICAL
        # -----
        # The state of the rule remains 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # And If we set A and B WARNING now?
        self.scheduler_loop(2, [[A, 1, 'WARNING'], [B, 1, 'WARNING']])
        assert 'WARNING' == A.state
        assert 'HARD' == A.state_type
        assert 1 == A.last_hard_state_id
        assert 'WARNING' == B.state
        assert 'HARD' == B.state_type
        assert 1 == B.last_hard_state_id

        # -----
        # All OK except 2 WARNING with 5,1,1 of: -> WARNING
        # -----
        # Must be WARNING (worse no 0 value for both, like for AND rule)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        print("state", state)
        assert 1 == state

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
        assert 0 == bp_rule.get_state(self._sched.hosts, self._sched.services)

        # 5,1,1
        if with_pct == False:
            bp_rule.of_values = ('5', '1', '1')
        else:
            bp_rule.of_values = ('100%', '20%', '20%')
        bp_rule.is_of_mul = True
        assert 1 == bp_rule.get_state(self._sched.hosts, self._sched.services)

        # 5,2,1
        if with_pct == False:
            bp_rule.of_values = ('5', '2', '1')
        else:
            bp_rule.of_values = ('100%', '40%', '20%')
        bp_rule.is_of_mul = True
        assert 0 == bp_rule.get_state(self._sched.hosts, self._sched.services)

        ###* W C O O O
        # 4 of: -> Critical (not 4 ok, so we take the worse state, the critical)
        # 4,1,1 -> Critical (2 states raise the waring, but on raise critical, so worse state is critical)
        self.scheduler_loop(2, [[A, 1, 'WARNING'], [B, 2, 'Crit']])
        # 4 of: -> 4,5,5
        if with_pct == False:
            bp_rule.of_values = ('4', '5', '5')
        else:
            bp_rule.of_values = ('80%', '100%', '100%')
        bp_rule.is_of_mul = False
        assert 2 == bp_rule.get_state(self._sched.hosts, self._sched.services)
        # 4,1,1
        if with_pct == False:
            bp_rule.of_values = ('4', '1', '1')
        else:
            bp_rule.of_values = ('40%', '20%', '20%')
        bp_rule.is_of_mul = True
        assert 2 == bp_rule.get_state(self._sched.hosts, self._sched.services)

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
        assert 0 == bp_rule.get_state(self._sched.hosts, self._sched.services)
        # * 4,1,1
        if with_pct == False:
            bp_rule.of_values = ('4', '1', '1')
        else:
            bp_rule.of_values = ('80%', '20%', '20%')
        bp_rule.is_of_mul = True
        assert 2 == bp_rule.get_state(self._sched.hosts, self._sched.services)
        # * 4,1,3
        if with_pct == False:
            bp_rule.of_values = ('4', '1', '3')
        else:
            bp_rule.of_values = ('80%', '20%', '60%')
        bp_rule.is_of_mul = True
        assert 1 == bp_rule.get_state(self._sched.hosts, self._sched.services)

        ##* W ACK(C) C O O
        # * 3 of: OK
        # * 4,1,1 -> Critical (same as before)
        # * 4,1,2 -> Warning
        cmd = "[%lu] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;B;2;1;1;lausser;blablub" % (now)
        self._sched.run_external_commands([cmd])

        if with_pct == False:
            bp_rule.of_values = ('3', '5', '5')
        else:
            bp_rule.of_values = ('60%', '100%', '100%')
        bp_rule.is_of_mul = False
        assert 0 == bp_rule.get_state(self._sched.hosts, self._sched.services)
        # * 4,1,1
        if with_pct == False:
            bp_rule.of_values = ('4', '1', '1')
        else:
            bp_rule.of_values = ('80%', '20%', '20%')
        bp_rule.is_of_mul = True
        assert 2 == bp_rule.get_state(self._sched.hosts, self._sched.services)
        # * 4,1,3
        if with_pct == False:
            bp_rule.of_values = ('4', '1', '2')
        else:
            bp_rule.of_values = ('80%', '20%', '40%')
        bp_rule.is_of_mul = True
        assert 1 == bp_rule.get_state(self._sched.hosts, self._sched.services)

        ##* W DOWNTIME(C) C O O
        # * 3 of: OK
        # * 4,1,1 -> Critical (same as before)
        # * 4,1,2 -> Warning
        duration = 300
        cmd = "[%lu] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;B" % now
        self._sched.run_external_commands([cmd])
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;B;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self._sched.run_external_commands([cmd])
        self.scheduler_loop(1, [[svc_cor, None, None]])
        if with_pct == False:
            bp_rule.of_values = ('3', '5', '5')
        else:
            bp_rule.of_values = ('60%', '100%', '100%')
        bp_rule.is_of_mul = False
        assert 0 == bp_rule.get_state(self._sched.hosts, self._sched.services)
        # * 4,1,1
        if with_pct == False:
            bp_rule.of_values = ('4', '1', '1')
        else:
            bp_rule.of_values = ('80%', '20%', '20%')
        bp_rule.is_of_mul = True
        assert 2 == bp_rule.get_state(self._sched.hosts, self._sched.services)
        # * 4,1,3
        if with_pct == False:
            bp_rule.of_values = ('4', '1', '2')
        else:
            bp_rule.of_values = ('80%', '20%', '40%')
        bp_rule.is_of_mul = True
        assert 1 == bp_rule.get_state(self._sched.hosts, self._sched.services)

    # We will try a simple db1 OR db2
    def test_multi_layers(self):
        """ BR - multi-levels rule

        bp_rule!(test_host_0,db1| (test_host_0,db2 & (test_host_0,lvs1|test_host_0,lvs2) ) )
        & test_router_0
        :return:
        """
        now = time.time()

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
        assert not svc_db1.got_business_rule
        assert svc_db1.business_rule is None

        svc_db2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "db2")
        svc_db2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        assert not svc_db2.got_business_rule
        assert svc_db2.business_rule is None

        svc_lvs1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "lvs1")
        svc_lvs1.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        assert not svc_lvs1.got_business_rule
        assert svc_lvs1.business_rule is None

        svc_lvs2 = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "lvs2")
        svc_lvs2.act_depend_of = []  # no host checks on critical check results
        # Not a BR, a simple service
        assert not svc_lvs2.got_business_rule
        assert svc_lvs2.business_rule is None

        svc_cor = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "Multi_levels")
        svc_cor.act_depend_of = []  # no host checks on critical check results
        assert True == svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        bp_rule = svc_cor.business_rule
        assert '&' == bp_rule.operand

        # We check for good parent/childs links
        # So svc_cor should be a son of svc_db1, svc_db2, ...
        # and they should be parents of svc_cor
        assert svc_cor.uuid in svc_db1.child_dependencies
        assert svc_cor.uuid in svc_db2.child_dependencies
        assert svc_cor.uuid in svc_lvs1.child_dependencies
        assert svc_cor.uuid in svc_lvs2.child_dependencies

        assert svc_db1.uuid in svc_cor.parent_dependencies
        assert svc_db2.uuid in svc_cor.parent_dependencies
        assert svc_lvs1.uuid in svc_cor.parent_dependencies
        assert svc_lvs2.uuid in svc_cor.parent_dependencies

        # Get the BR associated with svc_cor
        bp_rule = svc_cor.business_rule
        assert bp_rule.operand == '&'
        assert bp_rule.of_values == ('2', '2', '2')
        assert bp_rule.not_value == False
        assert bp_rule.is_of_mul == False
        assert bp_rule.sons is not None
        assert 2 == len(bp_rule.sons)

        # First son is an OR rule
        first_node = bp_rule.sons[0]
        assert isinstance(first_node, DependencyNode)
        assert first_node.operand == '|'
        assert first_node.of_values == ('2', '2', '2')
        assert first_node.not_value == False
        assert first_node.sons is not None
        assert first_node.sons is not []
        assert 2 == len(first_node.sons)

        # First son of the node is linked to a service and we have its uuid
        son = first_node.sons[0]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db1.uuid

        # Second son of the node is also a rule (AND)
        son = first_node.sons[1]
        assert isinstance(son, DependencyNode)
        assert son.operand == '&'
        assert son.of_values == ('2', '2', '2')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert isinstance(son.sons[0], DependencyNode)

        # Second node is a rule
        second_node = son
        assert isinstance(second_node, DependencyNode)
        assert second_node.operand == '&'
        assert second_node.of_values == ('2', '2', '2')
        assert second_node.not_value == False
        assert second_node.sons is not None
        assert second_node.sons is not []
        assert isinstance(son.sons[0], DependencyNode)

        # First son of the node is linked to a service and we have its uuid
        son = second_node.sons[0]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_db2.uuid

        # Second son of the node is also a rule (OR)
        son = second_node.sons[1]
        assert isinstance(son, DependencyNode)
        assert son.operand == '|'
        assert son.of_values == ('2', '2', '2')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert isinstance(son.sons[0], DependencyNode)

        # Third node is a rule
        third_node = son
        assert isinstance(third_node, DependencyNode)
        assert third_node.operand == '|'
        assert third_node.of_values == ('2', '2', '2')
        assert third_node.not_value == False
        assert third_node.sons is not None
        assert third_node.sons is not []
        assert isinstance(son.sons[0], DependencyNode)

        # First son of the node is linked to a service and we have its uuid
        son = third_node.sons[0]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_lvs1.uuid

        # Second son of the node is also a rule (OR)
        son = third_node.sons[1]
        assert isinstance(son, DependencyNode)
        assert son.operand == 'service'
        assert son.of_values == ('0', '0', '0')
        assert son.not_value == False
        assert son.sons is not None
        assert son.sons is not []
        assert son.sons[0] == svc_lvs2.uuid

        # Now start working on the states
        self.scheduler_loop(1, [
            [svc_db1, 0, 'OK | rtt=10'],
            [svc_db2, 0, 'OK | value1=1 value2=2'],
            [svc_lvs1, 0, 'OK'],
            [svc_lvs2, 0, 'OK'],
            [host, 0, 'UP'],
            [router, 0, 'UP']
        ])
        assert 'OK' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 'OK' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 'OK' == svc_lvs1.state
        assert 'HARD' == svc_lvs1.state_type
        assert 'OK' == svc_lvs2.state
        assert 'HARD' == svc_lvs2.state_type

        # All is green, the rule should be green too
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we get db1 CRITICAL/HARD
        self.scheduler_loop(2, [
            [svc_db1, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db1.state
        assert 'HARD' == svc_db1.state_type
        assert 2 == svc_db1.last_hard_state_id

        # The rule must still be a 0 (OR inside)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we also set db2 as CRITICAL/HARD...
        self.scheduler_loop(2, [
            [svc_db2, 2, 'CRITICAL | value1=1 value2=2']
        ])
        assert 'CRITICAL' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 2 == svc_db2.last_hard_state_id

        # And now the state of the rule must be 2
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # And If we set db2 to WARNING?
        self.scheduler_loop(2, [
            [svc_db2, 1, 'WARNING | value1=1 value2=2']
        ])
        assert 'WARNING' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 1 == svc_db2.last_hard_state_id

        # Must be WARNING (better no 0 value)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 1 == state

        # Acknowledge db2
        cmd = "[%lu] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;db2;2;1;1;lausser;blablub" % (now)
        self._sched.run_external_commands([cmd])
        assert True == svc_db2.problem_has_been_acknowledged

        # Must be OK
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Unacknowledge then downtime db2
        duration = 300
        cmd = "[%lu] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;db2" % now
        self._sched.run_external_commands([cmd])
        assert False == svc_db2.problem_has_been_acknowledged

        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;db2;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self._sched.run_external_commands([cmd])
        self.scheduler_loop(1, [[svc_cor, None, None]])
        assert svc_db2.scheduled_downtime_depth > 0

        assert True == svc_db2.in_scheduled_downtime
        assert 'WARNING' == svc_db2.state
        assert 'HARD' == svc_db2.state_type
        assert 1 == svc_db2.last_hard_state_id

        # Must be OK
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        self.assertEqual(0, state)

        # We should got now svc_db2 and svc_db1 as root problems
        assert svc_db1.uuid in svc_cor.source_problems
        assert svc_db2.uuid in svc_cor.source_problems

        # What about now with the router in DOWN state?
        self.scheduler_loop(5, [[router, 2, 'DOWN']])
        assert 'DOWN' == router.state
        assert 'HARD' == router.state_type
        assert 1 == router.last_hard_state_id

        # Must be CRITICAL (CRITICAL VERSUS DOWN -> DOWN)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 2 == state

        # Now our root problem is router
        assert router.uuid in svc_cor.source_problems

    # We will try a strange rule that ask UP&UP -> DOWN&DONW-> OK
    def test_darthelmet_rule(self):
        #
        # Config is not correct because of a wrong relative path
        # in the main config file
        #
        print("Get the hosts and services")
        now = time.time()
        host = self._sched.hosts.find_by_name("test_darthelmet")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        A = self._sched.hosts.find_by_name("test_darthelmet_A")
        B = self._sched.hosts.find_by_name("test_darthelmet_B")

        assert True == host.got_business_rule
        assert host.business_rule is not None
        bp_rule = host.business_rule
        assert '|' == bp_rule.operand

        # Now state working on the states
        self.scheduler_loop(3, [[host, 0, 'UP'], [A, 0, 'UP'], [B, 0, 'UP'] ] )
        assert 'UP' == host.state
        assert 'HARD' == host.state_type
        assert 'UP' == A.state
        assert 'HARD' == A.state_type

        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        print("WTF0", state)
        assert 0 == state

        # Now we set the A as soft/DOWN
        self.scheduler_loop(1, [[A, 2, 'DOWN']])
        assert 'DOWN' == A.state
        assert 'SOFT' == A.state_type
        assert 0 == A.last_hard_state_id

        # The business rule must still be 0
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # Now we get A DOWN/HARD
        self.scheduler_loop(3, [[A, 2, 'DOWN']])
        assert 'DOWN' == A.state
        assert 'HARD' == A.state_type
        assert 1 == A.last_hard_state_id

        # The rule must still be a 2 (or inside)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        print("WFT", state)
        assert 2 == state

        # Now we also set B as DOWN/HARD, should get back to 0!
        self.scheduler_loop(3, [[B, 2, 'DOWN']])
        assert 'DOWN' == B.state
        assert 'HARD' == B.state_type
        assert 1 == B.last_hard_state_id

        # And now the state of the rule must be 0 again! (strange rule isn't it?)
        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # We set B as UP and acknowledge A
        self.scheduler_loop(3, [[B, 0, 'UP']])
        assert 'UP' == B.state
        assert 'HARD' == B.state_type
        assert 0 == B.last_hard_state_id

        cmd = "[%lu] ACKNOWLEDGE_HOST_PROBLEM;test_darthelmet_A;1;1;0;lausser;blablub" % now
        self._sched.run_external_commands([cmd])
        assert 'DOWN' == A.state
        assert 'HARD' == A.state_type
        assert 1 == A.last_hard_state_id

        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state

        # We unacknowledge then downtime A
        duration = 300
        cmd = "[%lu] REMOVE_HOST_ACKNOWLEDGEMENT;test_darthelmet_A" % now
        self._sched.run_external_commands([cmd])

        cmd = "[%lu] SCHEDULE_HOST_DOWNTIME;test_darthelmet_A;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self._sched.run_external_commands([cmd])
        self.scheduler_loop(1, [[B, None, None]])
        assert 'DOWN' == A.state
        assert 'HARD' == A.state_type
        assert 1 == A.last_hard_state_id

        state = bp_rule.get_state(self._sched.hosts, self._sched.services)
        assert 0 == state