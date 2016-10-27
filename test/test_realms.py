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
#     Grégory Starck, g.starck@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
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

"""
This file is used to test realms usage
"""
import re
from alignak_test import AlignakTest


class TestRealms(AlignakTest):
    """
    This class test realms usage
    """

    def test_no_defined_realm(self):
        """ Test configuration with no definde realm
        Load a configuration with no realm defined:
        - Alignak defines a default realm
        - All hosts with no realm defined are in this default realm

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/realms/no_defined_realms.cfg')
        # self.logger.setLevel("INFO")  # We need Info level to assert on logs received
        # self.assertTrue(self.conf_is_correct)
        self.assertTrue(self.conf_is_correct)
        self.show_logs()
        # The following log line is not available in the test catched log, because too early
        # in the configuration load process
        # self.assert_any_log_match("WARNING: [Alignak] No realms defined, I add one as Default")
        self.assert_any_log_match(re.escape("Prepare dispatching for this realm"))

        # Only one realm in the configuration
        self.assertEqual(len(self.arbiter.conf.realms), 1)

        # All realm exists
        realm = self.arbiter.conf.realms.find_by_name("All")
        self.assertIsNotNone(realm)
        self.assertEqual(realm.realm_name, 'All')
        self.assertEqual(realm.alias, 'Self created default realm')
        self.assertTrue(realm.default)

        # All realm is the default realm
        default_realm = self.arbiter.conf.realms.get_default()
        self.assertEqual(realm, default_realm)

        # Default realm does not exist anymore
        realm = self.arbiter.conf.realms.find_by_name("Default")
        self.assertIsNone(realm)

        # Hosts without realm definition are in the Default realm
        hosts = self.arbiter.conf.hosts
        self.assertEqual(len(hosts), 2)
        for host in hosts:
            self.assertEqual(host.realm, default_realm.uuid)
            self.assertEqual(host.get_realm(), default_realm.get_name())

    def test_no_broker_in_realm_warning(self):
        """ Test missing broker in realm
        Test realms on each host

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/realms/no_broker_in_realm_warning.cfg')
        self.assertFalse(self.conf_is_correct)
        self.assertIn(u"Error: the scheduler Scheduler-distant got no broker in its realm or upper",
                      self.configuration_errors)

        dist = self.arbiter.conf.realms.find_by_name("Distant")
        self.assertIsNotNone(dist)
        sched = self.arbiter.conf.schedulers.find_by_name("Scheduler-distant")
        self.assertIsNotNone(sched)
        self.assertEqual(0, len(self.arbiter.conf.realms[sched.realm].potential_brokers))
        self.assertEqual(0, len(self.arbiter.conf.realms[sched.realm].potential_pollers))
        self.assertEqual(0, len(self.arbiter.conf.realms[sched.realm].potential_reactionners))
        self.assertEqual(0, len(self.arbiter.conf.realms[sched.realm].potential_receivers))

    def test_realm_host_assignation(self):
        """ Test host realm assignation
        Test realms on each host

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_realms.cfg')
        self.assertTrue(self.conf_is_correct)

        for scheduler in self.schedulers:
            print("Scheduler: %s: %s" % (scheduler, self.schedulers[scheduler]))
            if scheduler == 'Scheduler-1':
                sched_realm1 = self.schedulers[scheduler]
            elif scheduler == 'Scheduler-2':
                sched_realm2 = self.schedulers[scheduler]
        realm1 = self.arbiter.conf.realms.find_by_name('realm1')
        self.assertIsNotNone(realm1)
        realm2 = self.arbiter.conf.realms.find_by_name('realm2')
        self.assertIsNotNone(realm2)

        test_host_realm1 = sched_realm1.conf.hosts.find_by_name("test_host_realm1")
        self.assertIsNotNone(test_host_realm1)
        self.assertEqual(realm1.uuid, test_host_realm1.realm)
        test_host_realm2 = sched_realm1.conf.hosts.find_by_name("test_host_realm2")
        self.assertIsNone(test_host_realm2)

        test_host_realm2 = sched_realm2.conf.hosts.find_by_name("test_host_realm2")
        self.assertIsNotNone(test_host_realm2)
        self.assertEqual(realm2.uuid, test_host_realm2.realm)
        test_host_realm1 = sched_realm2.conf.hosts.find_by_name("test_host_realm1")
        self.assertIsNone(test_host_realm1)

    def test_realm_hostgroup_assignation(self):
        """ Test realm hostgroup assignation

        Check realm and hostgroup

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_realms.cfg')
        self.assertTrue(self.conf_is_correct)

        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        # self.assertEqual(len(self.configuration_warnings), 1)

        # self.assert_any_cfg_log_match(
        #     "host test_host3_hg_realm2 is not in the same realm than its hostgroup in_realm2"
        # )

        # Check all daemons exist
        self.assertEqual(len(self.arbiter.conf.arbiters), 1)
        self.assertEqual(len(self.arbiter.conf.schedulers), 2)
        self.assertEqual(len(self.arbiter.conf.brokers), 2)
        self.assertEqual(len(self.arbiter.conf.pollers), 2)
        self.assertEqual(len(self.arbiter.conf.reactionners), 1)
        self.assertEqual(len(self.arbiter.conf.receivers), 0)

        for daemon in self.arbiter.conf.schedulers:
            self.assertIn(daemon.get_name(), ['Scheduler-1', 'Scheduler-2'])
            self.assertIn(daemon.realm, self.arbiter.conf.realms)

        for daemon in self.arbiter.conf.brokers:
            self.assertIn(daemon.get_name(), ['Broker-1', 'Broker-2'])
            self.assertIn(daemon.realm, self.arbiter.conf.realms)

        for daemon in self.arbiter.conf.pollers:
            self.assertIn(daemon.get_name(), ['Poller-1', 'Poller-2'])
            self.assertIn(daemon.realm, self.arbiter.conf.realms)

        in_realm2 = self.schedulers['Scheduler-1'].sched.hostgroups.find_by_name('in_realm2')
        realm1 = self.arbiter.conf.realms.find_by_name('realm1')
        self.assertIsNotNone(realm1)
        realm2 = self.arbiter.conf.realms.find_by_name('realm2')
        self.assertIsNotNone(realm2)

        for scheduler in self.schedulers:
            if scheduler == 'Scheduler-1':
                sched_realm1 = self.schedulers[scheduler]
            elif scheduler == 'Scheduler-2':
                sched_realm2 = self.schedulers[scheduler]

        # 1 and 2 are link to realm2 because they are in the hostgroup in_realm2
        test_host1_hg_realm2 = sched_realm2.conf.hosts.find_by_name("test_host1_hg_realm2")
        self.assertIsNotNone(test_host1_hg_realm2)
        self.assertEqual(realm2.uuid, test_host1_hg_realm2.realm)
        self.assertIn(in_realm2.get_name(), [sched_realm2.conf.hostgroups[hg].get_name() for hg in test_host1_hg_realm2.hostgroups])

        test_host2_hg_realm2 = sched_realm2.conf.hosts.find_by_name("test_host2_hg_realm2")
        self.assertIsNotNone(test_host2_hg_realm2)
        self.assertEqual(realm2.uuid, test_host2_hg_realm2.realm)
        self.assertIn(in_realm2.get_name(), [sched_realm2.conf.hostgroups[hg].get_name() for hg in test_host2_hg_realm2.hostgroups])

        test_host3_hg_realm2 = sched_realm2.conf.hosts.find_by_name("test_host3_hg_realm2")
        self.assertIsNone(test_host3_hg_realm2)
        test_host3_hg_realm2 = sched_realm1.conf.hosts.find_by_name("test_host3_hg_realm2")
        self.assertIsNotNone(test_host3_hg_realm2)
        self.assertEqual(realm1.uuid, test_host3_hg_realm2.realm)
        self.assertIn(in_realm2.get_name(), [sched_realm2.conf.hostgroups[hg].get_name() for hg in test_host3_hg_realm2.hostgroups])

        hostgroup_realm2 = sched_realm1.conf.hostgroups.find_by_name("in_realm2")
        self.assertIsNotNone(hostgroup_realm2)
        hostgroup_realm2 = sched_realm2.conf.hostgroups.find_by_name("in_realm2")
        self.assertIsNotNone(hostgroup_realm2)

    def test_sub_realms_assignations(self):
        """ Test realm / sub-realm for broker

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_realms_sub.cfg')
        self.assertTrue(self.conf_is_correct)

        world = self.arbiter.conf.realms.find_by_name('World')
        self.assertIsNot(world, None)
        europe = self.arbiter.conf.realms.find_by_name('Europe')
        self.assertIsNot(europe, None)
        paris = self.arbiter.conf.realms.find_by_name('Paris')
        self.assertIsNot(paris, None)
        # Get the broker in the realm level
        bworld = self.arbiter.conf.brokers.find_by_name('B-world')
        self.assertIsNot(bworld, None)

        # broker should be in the world level
        self.assertIs(bworld.uuid in world.potential_brokers, True)
        # in europe too
        self.assertIs(bworld.uuid in europe.potential_brokers, True)
        # and in paris too
        self.assertIs(bworld.uuid in paris.potential_brokers, True)