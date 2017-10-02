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
from __future__ import print_function
import os
import re
import shutil
from alignak_test import AlignakTest
import pytest


class TestRealms(AlignakTest):
    """
    This class test realms usage
    """
    def test_no_defined_realm(self):
        """ Test configuration with no defined realm
        Load a configuration with no realm defined:
        - Alignak defines a default realm
        - All hosts with no realm defined are in this default realm

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/realms/no_defined_realms.cfg')
        assert self.conf_is_correct
        self.show_logs()

        self.assert_any_log_match(re.escape("No realms defined, I added one as All"))
        self.assert_any_log_match(re.escape("No poller defined, I add one at localhost:7771"))
        self.assert_any_log_match(re.escape("No reactionner defined, I add one at localhost:7769"))
        self.assert_any_log_match(re.escape("No broker defined, I add one at localhost:7772"))
        self.assert_any_log_match(re.escape("Tagging Default-Poller with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Broker with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Reactionner with realm All"))
        self.assert_any_log_match(re.escape("Prepare dispatching for this realm"))

        # Only one realm in the configuration
        assert len(self.arbiter.conf.realms) == 1

        # All realm exists
        realm = self.arbiter.conf.realms.find_by_name("All")
        assert realm is not None
        assert realm.realm_name == 'All'
        assert realm.alias == 'Self created default realm'
        assert realm.default

        # All realm is the default realm
        default_realm = self.arbiter.conf.realms.get_default()
        assert realm == default_realm

        # Default realm does not exist anymore
        realm = self.arbiter.conf.realms.find_by_name("Default")
        assert realm is None

        # Hosts without realm definition are in the Default realm
        hosts = self.arbiter.conf.hosts
        assert len(hosts) == 2
        for host in hosts:
            assert host.realm == default_realm.uuid
            assert host.realm_name == default_realm.get_name()

    def test_default_realm(self):
        """ Test configuration with no defined realm
        Load a configuration with no realm defined:
        - Alignak defines a default realm
        - All hosts with no realm defined are in this default realm

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/realms/two_default_realms.cfg')
        assert self.conf_is_correct
        self.show_logs()

        self.assert_any_log_match(re.escape("No realms defined, I added one as All"))
        self.assert_any_log_match(re.escape("No poller defined, I add one at localhost:7771"))
        self.assert_any_log_match(re.escape("No reactionner defined, I add one at localhost:7769"))
        self.assert_any_log_match(re.escape("No broker defined, I add one at localhost:7772"))
        self.assert_any_log_match(re.escape("Tagging Default-Poller with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Broker with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Reactionner with realm All"))
        self.assert_any_log_match(re.escape("Prepare dispatching for this realm"))

        # Only one realm in the configuration
        assert len(self.arbiter.conf.realms) == 1

        # All realm exists
        realm = self.arbiter.conf.realms.find_by_name("All")
        assert realm is not None
        assert realm.realm_name == 'All'
        assert realm.alias == 'Self created default realm'
        assert realm.default

        # All realm is the default realm
        default_realm = self.arbiter.conf.realms.get_default()
        assert realm == default_realm

        # Default realm does not exist anymore
        realm = self.arbiter.conf.realms.find_by_name("Default")
        assert realm is None

        # Hosts without realm definition are in the Default realm
        hosts = self.arbiter.conf.hosts
        assert len(hosts) == 2
        for host in hosts:
            assert host.realm == default_realm.uuid
            assert host.realm_name == default_realm.get_name()

    def test_no_defined_daemons(self):
        """ Test configuration with no defined daemons
        Load a configuration with no realm nor daemons defined:
        - Alignak defines a default realm
        - All hosts with no realm defined are in this default realm
        - Alignak defines default daemons

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/realms/no_defined_daemons.cfg')
        assert self.conf_is_correct
        self.show_logs()

        self.assert_any_log_match(re.escape("No realms defined, I added one as All"))
        self.assert_any_log_match(re.escape("No scheduler defined, I add one at localhost:7768"))
        self.assert_any_log_match(re.escape("No poller defined, I add one at localhost:7771"))
        self.assert_any_log_match(re.escape("No reactionner defined, I add one at localhost:7769"))
        self.assert_any_log_match(re.escape("No broker defined, I add one at localhost:7772"))
        self.assert_any_log_match(re.escape("Tagging Default-Poller with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Broker with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Reactionner with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Scheduler with realm All"))
        self.assert_any_log_match(re.escape("Prepare dispatching for this realm"))

        scheduler_link = self.arbiter.conf.schedulers.find_by_name('Default-Scheduler')
        assert scheduler_link is not None
        # Scheduler configuration is ok
        assert self.schedulers['Default-Scheduler'].sched.conf.conf_is_correct

        # Broker, Poller, Reactionner named as in the configuration
        link = self.arbiter.conf.brokers.find_by_name('Default-Broker')
        assert link is not None
        link = self.arbiter.conf.pollers.find_by_name('Default-Poller')
        assert link is not None
        link = self.arbiter.conf.reactionners.find_by_name('Default-Reactionner')
        assert link is not None

        # Receiver - no default receiver created
        assert not self.arbiter.conf.receivers
        # link = self.arbiter.conf.receivers.find_by_name('Default-Receiver')
        # assert link is not None

        # Only one realm in the configuration
        assert len(self.arbiter.conf.realms) == 1

        # 'All' realm exists
        realm = self.arbiter.conf.realms.find_by_name("All")
        assert realm is not None
        assert realm.realm_name == 'All'
        assert realm.alias == 'Self created default realm'
        assert realm.default

        # 'All' realm is the default realm
        default_realm = self.arbiter.conf.realms.get_default()
        assert realm == default_realm

        # Default realm does not exist anymore
        realm = self.arbiter.conf.realms.find_by_name("Default")
        assert realm is None

        # Hosts without realm definition are in the Default realm
        hosts = self.arbiter.conf.hosts
        assert len(hosts) == 2
        for host in hosts:
            assert host.realm == default_realm.uuid
            assert host.realm_name == default_realm.get_name()

    def test_no_scheduler_in_realm(self):
        """ Test missing scheduler in realm
        A realm is defined but no scheduler, nor broker, nor poller exist for this realm

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/realms/no_scheduler_in_realm.cfg')
        self.show_logs()
        assert self.conf_is_correct

        self.assert_any_log_match(re.escape("No scheduler defined, I add one at localhost:7768"))
        self.assert_any_log_match(re.escape("No poller defined, I add one at localhost:7771"))
        self.assert_any_log_match(re.escape("No reactionner defined, I add one at localhost:7769"))
        self.assert_any_log_match(re.escape("No scheduler defined, I add one at localhost:7768"))
        self.assert_any_log_match(re.escape("All: (in/potential) (schedulers:1) (pollers:1/1) "
                                            "(reactionners:1/1) (brokers:1/1) (receivers:0/0)"))
        self.assert_any_log_match(re.escape("Distant: (in/potential) (schedulers:1) (pollers:1/1) "
                                            "(reactionners:0/0) (brokers:1/1) (receivers:0/0)"))

        assert "Some hosts exist in the realm 'Distant' " \
               "but no scheduler is defined for this realm" in self.configuration_warnings
        assert "Some hosts exist in the realm 'Distant' " \
               "but no poller is defined for this realm" in self.configuration_warnings

        # Scheduler added for the realm
        self.assert_any_log_match(re.escape("Trying to add a scheduler for the realm: Distant"))
        scheduler_link = self.arbiter.conf.schedulers.find_by_name('Scheduler-Distant')
        assert scheduler_link is not None

        # Broker added for the realm
        self.assert_any_log_match(re.escape("Trying to add a broker for the realm: Distant"))
        broker_link = self.arbiter.conf.brokers.find_by_name('Broker-Distant')
        assert broker_link is not None

        # Poller added for the realm
        self.assert_any_log_match(re.escape("Trying to add a poller for the realm: Distant"))
        poller_link = self.arbiter.conf.pollers.find_by_name('Poller-Distant')
        assert poller_link is not None

    def test_no_broker_in_realm(self):
        """ Test missing broker in realm
        Test realms on each host

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/realms/no_broker_in_realm.cfg')
        self.show_logs()
        assert self.conf_is_correct

        dist = self.arbiter.conf.realms.find_by_name("Distant")
        assert dist is not None
        sched = self.arbiter.conf.schedulers.find_by_name("Scheduler-distant")
        assert sched is not None
        assert 0 == len(self.arbiter.conf.realms[sched.realm].potential_brokers)
        assert 0 == len(self.arbiter.conf.realms[sched.realm].potential_pollers)
        assert 0 == len(self.arbiter.conf.realms[sched.realm].potential_reactionners)
        assert 0 == len(self.arbiter.conf.realms[sched.realm].potential_receivers)

    def test_realm_host_assignation(self):
        """ Test host realm assignation
        Test realms on each host

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_realms.cfg')
        self.show_configuration_logs()
        assert self.conf_is_correct

        for scheduler in self.schedulers:
            if scheduler == 'Scheduler-1':
                sched_realm1 = self.schedulers[scheduler]
            elif scheduler == 'Scheduler-2':
                sched_realm2 = self.schedulers[scheduler]
        realm1 = self.arbiter.conf.realms.find_by_name('realm1')
        assert realm1 is not None
        realm2 = self.arbiter.conf.realms.find_by_name('realm2')
        assert realm2 is not None

        test_host_realm1 = sched_realm1.conf.hosts.find_by_name("test_host_realm1")
        assert test_host_realm1 is not None
        assert realm1.uuid == test_host_realm1.realm
        test_host_realm2 = sched_realm1.conf.hosts.find_by_name("test_host_realm2")
        assert test_host_realm2 is None

        test_host_realm2 = sched_realm2.conf.hosts.find_by_name("test_host_realm2")
        assert test_host_realm2 is not None
        assert realm2.uuid == test_host_realm2.realm
        test_host_realm1 = sched_realm2.conf.hosts.find_by_name("test_host_realm1")
        assert test_host_realm1 is None

    def test_undefined_used_realm(self):
        """ Test undefined realm used in daemons

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/realms/use_undefined_realm.cfg')
        self.show_logs()
        assert not self.conf_is_correct
        assert "Configuration in scheduler::Scheduler-distant is incorrect; " \
               "from: cfg/realms/use_undefined_realm.cfg:7" in \
                      self.configuration_errors
        assert "The scheduler Scheduler-distant got a unknown realm 'Distant'" in \
                      self.configuration_errors
        assert "schedulers configuration is incorrect!" in \
                      self.configuration_errors

    def test_realm_hostgroup_assignation(self):
        """ Test realm hostgroup assignation

        Check realm and hostgroup

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_realms.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        # self.assertEqual(len(self.configuration_warnings), 1)

        # self.assert_any_cfg_log_match(
        #     "host test_host3_hg_realm2 is not in the same realm than its hostgroup in_realm2"
        # )

        # Check all daemons exist
        assert len(self.arbiter.conf.arbiters) == 1
        assert len(self.arbiter.conf.schedulers) == 2
        assert len(self.arbiter.conf.brokers) == 2
        assert len(self.arbiter.conf.pollers) == 2
        assert len(self.arbiter.conf.reactionners) == 1
        assert len(self.arbiter.conf.receivers) == 0

        for daemon in self.arbiter.conf.schedulers:
            assert daemon.get_name() in ['Scheduler-1', 'Scheduler-2']
            assert daemon.realm in self.arbiter.conf.realms

        for daemon in self.arbiter.conf.brokers:
            assert daemon.get_name() in ['Broker-1', 'Broker-2']
            assert daemon.realm in self.arbiter.conf.realms

        for daemon in self.arbiter.conf.pollers:
            assert daemon.get_name() in ['Poller-1', 'Poller-2']
            assert daemon.realm in self.arbiter.conf.realms

        in_realm2 = self.schedulers['Scheduler-1'].sched.hostgroups.find_by_name('in_realm2')
        realm1 = self.arbiter.conf.realms.find_by_name('realm1')
        assert realm1 is not None
        realm2 = self.arbiter.conf.realms.find_by_name('realm2')
        assert realm2 is not None

        for scheduler in self.schedulers:
            if scheduler == 'Scheduler-1':
                sched_realm1 = self.schedulers[scheduler]
            elif scheduler == 'Scheduler-2':
                sched_realm2 = self.schedulers[scheduler]

        # 1 and 2 are link to realm2 because they are in the hostgroup in_realm2
        test_host1_hg_realm2 = sched_realm2.conf.hosts.find_by_name("test_host1_hg_realm2")
        assert test_host1_hg_realm2 is not None
        assert realm2.uuid == test_host1_hg_realm2.realm
        assert in_realm2.get_name() in [sched_realm2.conf.hostgroups[hg].get_name() for hg in test_host1_hg_realm2.hostgroups]

        test_host2_hg_realm2 = sched_realm2.conf.hosts.find_by_name("test_host2_hg_realm2")
        assert test_host2_hg_realm2 is not None
        assert realm2.uuid == test_host2_hg_realm2.realm
        assert in_realm2.get_name() in [sched_realm2.conf.hostgroups[hg].get_name() for hg in test_host2_hg_realm2.hostgroups]

        test_host3_hg_realm2 = sched_realm2.conf.hosts.find_by_name("test_host3_hg_realm2")
        assert test_host3_hg_realm2 is None
        test_host3_hg_realm2 = sched_realm1.conf.hosts.find_by_name("test_host3_hg_realm2")
        assert test_host3_hg_realm2 is not None
        assert realm1.uuid == test_host3_hg_realm2.realm
        assert in_realm2.get_name() in [sched_realm2.conf.hostgroups[hg].get_name() for hg in test_host3_hg_realm2.hostgroups]

        hostgroup_realm2 = sched_realm1.conf.hostgroups.find_by_name("in_realm2")
        assert hostgroup_realm2 is not None
        hostgroup_realm2 = sched_realm2.conf.hostgroups.find_by_name("in_realm2")
        assert hostgroup_realm2 is not None

    def test_sub_realms(self):
        """ Test realm / sub-realm

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_realms_sub.cfg')
        self.show_logs()
        assert self.conf_is_correct

        world = self.arbiter.conf.realms.find_by_name('World')
        assert world is not None
        europe = self.arbiter.conf.realms.find_by_name('Europe')
        assert europe is not None
        paris = self.arbiter.conf.realms.find_by_name('Paris')
        assert paris is not None

        # Get satellites of the world realm
        assert len(world.get_satellites_by_type('arbiter')) == 0
        assert len(world.get_satellites_by_type('scheduler')) == 1
        assert len(world.get_satellites_by_type('broker')) == 1
        assert len(world.get_satellites_by_type('poller')) == 1
        assert len(world.get_satellites_by_type('receiver')) == 0
        assert len(world.get_satellites_by_type('reactionner')) == 1

        # Get satellites of the europe realm
        assert len(europe.get_satellites_by_type('arbiter')) == 0
        assert len(europe.get_satellites_by_type('scheduler')) == 0
        assert len(europe.get_satellites_by_type('broker')) == 1
        assert len(europe.get_satellites_by_type('poller')) == 0
        assert len(europe.get_satellites_by_type('receiver')) == 0
        assert len(europe.get_satellites_by_type('reactionner')) == 0

        assert europe.uuid in world.all_sub_members
        assert paris.uuid in europe.all_sub_members

    def test_sub_realms_assignations(self):
        """ Test realm / sub-realm for broker

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_realms_sub.cfg')
        assert self.conf_is_correct

        world = self.arbiter.conf.realms.find_by_name('World')
        assert world is not None
        europe = self.arbiter.conf.realms.find_by_name('Europe')
        assert europe is not None
        paris = self.arbiter.conf.realms.find_by_name('Paris')
        assert paris is not None
        # Get the broker in the realm level
        bworld = self.arbiter.conf.brokers.find_by_name('B-world')
        assert bworld is not None

        # broker should be in the world level
        assert (bworld.uuid in world.potential_brokers) is True
        # in europe too
        assert (bworld.uuid in europe.potential_brokers) is True
        # and in paris too
        assert (bworld.uuid in paris.potential_brokers) is True

    def test_sub_realms_multi_levels(self):
        """ Test realm / sub-realm / sub-sub-realms...

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_realms_sub_multi_levels.cfg')
        assert self.conf_is_correct

        Osaka = self.arbiter.conf.realms.find_by_name('Osaka')
        assert Osaka is not None

        Tokyo = self.arbiter.conf.realms.find_by_name('Tokyo')
        assert Tokyo is not None

        Japan = self.arbiter.conf.realms.find_by_name('Japan')
        assert Japan is not None

        Asia = self.arbiter.conf.realms.find_by_name('Asia')
        assert Asia is not None

        Turin = self.arbiter.conf.realms.find_by_name('Turin')
        assert Turin is not None

        Rome = self.arbiter.conf.realms.find_by_name('Rome')
        assert Rome is not None

        Italy = self.arbiter.conf.realms.find_by_name('Italy')
        assert Italy is not None

        Lyon = self.arbiter.conf.realms.find_by_name('Lyon')
        assert Lyon is not None

        Paris = self.arbiter.conf.realms.find_by_name('Paris')
        assert Paris is not None

        France = self.arbiter.conf.realms.find_by_name('France')
        assert France is not None

        Europe = self.arbiter.conf.realms.find_by_name('Europe')
        assert Europe is not None

        World = self.arbiter.conf.realms.find_by_name('World')
        assert World is not None

        # check property all_sub_members
        assert Osaka.all_sub_members == []
        assert Tokyo.all_sub_members == []
        assert Japan.all_sub_members == [Tokyo.uuid,Osaka.uuid]
        assert Asia.all_sub_members == [Tokyo.uuid,Osaka.uuid,Japan.uuid]

        assert Turin.all_sub_members == []
        assert Rome.all_sub_members == []
        assert Italy.all_sub_members == [Rome.uuid,Turin.uuid]

        assert Lyon.all_sub_members == []
        assert Paris.all_sub_members == []
        assert France.all_sub_members == [Paris.uuid,Lyon.uuid]

        assert set(Europe.all_sub_members) == set([Paris.uuid,Lyon.uuid,France.uuid,Rome.uuid,Turin.uuid,Italy.uuid])

        assert set(World.all_sub_members) == set([Paris.uuid,Lyon.uuid,France.uuid,Rome.uuid,Turin.uuid,Italy.uuid,Europe.uuid,Tokyo.uuid,Osaka.uuid,Japan.uuid,Asia.uuid])

        # check satellites defined in each realms
        broker_uuid = self.brokers['broker-master'].uuid
        poller_uuid = self.pollers['poller-master'].uuid
        receiver_uuid = self.receivers['receiver-master'].uuid
        reactionner_uuid = self.reactionners['reactionner-master'].uuid

        for realm in [Osaka, Tokyo, Japan, Asia, Turin, Rome, Italy, Lyon, Paris, France, Europe, World]:
            print('Realm name: %s' % realm.realm_name)
            if realm.realm_name != 'France':
                assert realm.brokers == [broker_uuid]
                assert realm.potential_brokers == [broker_uuid]
                assert realm.nb_brokers == 1
            assert realm.pollers == [poller_uuid]
            assert realm.receivers == [receiver_uuid]
            assert realm.reactionners == [reactionner_uuid]
            assert realm.potential_pollers == [poller_uuid]
            assert realm.potential_receivers == [receiver_uuid]
            assert realm.potential_reactionners == [reactionner_uuid]

        assert set(France.brokers) == set([broker_uuid, self.brokers['broker-france'].uuid])
        assert set(France.potential_brokers) == set([broker_uuid, self.brokers['broker-france'].uuid])
        assert France.nb_brokers == 2

    def test_sub_realms_multi_levels_loop(self):
        """ Test realm / sub-realm / sub-sub-realms... with a loop, so exit with error message

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_realms_sub_multi_levels_loop.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()
