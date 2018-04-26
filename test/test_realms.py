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
import os
import re
import shutil
from alignak_test import AlignakTest
import pytest


class TestRealms(AlignakTest):
    """
    This class test realms usage
    """
    def setUp(self):
        super(TestRealms, self).setUp()

    def test_no_defined_realm(self):
        """ Test configuration with no defined realm

        Load a configuration with no realm defined:
        - Alignak defines a default realm
        - All hosts with no realm defined are in this default realm

        :return: None
        """
        self.setup_with_file('cfg/realms/no_defined_realms.cfg', 'cfg/realms/no_defined_realms.ini')
        assert self.conf_is_correct
        self.show_logs()

        self.assert_any_log_match(re.escape("No realms defined, I am adding one as All"))
        self.assert_any_log_match(re.escape("No reactionner defined, I am adding one on 127.0.0.1:7800"))
        self.assert_any_log_match(re.escape("No poller defined, I am adding one on 127.0.0.1:7801"))
        self.assert_any_log_match(re.escape("No broker defined, I am adding one on 127.0.0.1:7802"))
        self.assert_any_log_match(re.escape("No receiver defined, I am adding one on 127.0.0.1:7803"))
        self.assert_any_log_match(re.escape("Tagging Default-Poller with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Broker with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Reactionner with realm All"))
        # self.assert_any_log_match(re.escape("Prepare dispatching for this realm"))

        # Only one realm in the configuration
        assert len(self._arbiter.conf.realms) == 1

        # All realm exists
        realm = self._arbiter.conf.realms.find_by_name("All")
        assert realm is not None
        assert realm.realm_name == 'All'
        assert realm.alias == 'Self created default realm'
        assert realm.default

        # All realm is the default realm
        default_realm = self._arbiter.conf.realms.get_default()
        assert realm == default_realm

        # Default realm does not exist anymore
        realm = self._arbiter.conf.realms.find_by_name("Default")
        assert realm is None

        # Hosts without realm definition are in the Default realm
        hosts = self._arbiter.conf.hosts
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
        self.setup_with_file('cfg/realms/no_defined_realms.cfg', 'cfg/realms/no_default_realm.ini')
        assert self.conf_is_correct
        self.show_logs()

        self.assert_any_log_match(re.escape("No realms defined, I am adding one as All"))
        self.assert_any_log_match(re.escape("No reactionner defined, I am adding one on 127.0.0.1:10000"))
        self.assert_any_log_match(re.escape("No poller defined, I am adding one on 127.0.0.1:10001"))
        self.assert_any_log_match(re.escape("No broker defined, I am adding one on 127.0.0.1:10002"))
        self.assert_any_log_match(re.escape("No receiver defined, I am adding one on 127.0.0.1:10003"))
        self.assert_any_log_match(re.escape("Tagging Default-Poller with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Broker with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Reactionner with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Receiver with realm All"))

        # Only one realm in the configuration
        assert len(self._arbiter.conf.realms) == 1

        # All realm exists
        realm = self._arbiter.conf.realms.find_by_name("All")
        assert realm is not None
        assert realm.realm_name == 'All'
        assert realm.alias == 'Self created default realm'
        assert realm.default

        # All realm is the default realm
        default_realm = self._arbiter.conf.realms.get_default()
        assert realm == default_realm

        # Default realm does not exist anymore
        realm = self._arbiter.conf.realms.find_by_name("Default")
        assert realm is None

        # Hosts without realm definition are in the Default realm
        hosts = self._arbiter.conf.hosts
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
        self.setup_with_file('cfg/realms/no_defined_daemons.cfg', 'cfg/realms/no_defined_daemons.ini')
        assert self.conf_is_correct
        self.show_logs()

        self.assert_any_log_match(re.escape("No realms defined, I am adding one as All"))
        self.assert_any_log_match(re.escape("No scheduler defined, I am adding one on 127.0.0.1:7800"))
        self.assert_any_log_match(re.escape("No reactionner defined, I am adding one on 127.0.0.1:7801"))
        self.assert_any_log_match(re.escape("No poller defined, I am adding one on 127.0.0.1:7802"))
        self.assert_any_log_match(re.escape("No broker defined, I am adding one on 127.0.0.1:7803"))
        self.assert_any_log_match(re.escape("No receiver defined, I am adding one on 127.0.0.1:7804"))
        self.assert_any_log_match(re.escape("Tagging Default-Poller with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Broker with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Reactionner with realm All"))
        self.assert_any_log_match(re.escape("Tagging Default-Scheduler with realm All"))
        # self.assert_any_log_match(re.escape("Prepare dispatching for this realm"))

        scheduler_link = self._arbiter.conf.schedulers.find_by_name('Default-Scheduler')
        assert scheduler_link is not None
        # Scheduler configuration is ok
        assert self._schedulers['Default-Scheduler'].pushed_conf.conf_is_correct

        # Broker, Poller, Reactionner named as in the configuration
        link = self._arbiter.conf.brokers.find_by_name('Default-Broker')
        assert link is not None
        link = self._arbiter.conf.pollers.find_by_name('Default-Poller')
        assert link is not None
        link = self._arbiter.conf.reactionners.find_by_name('Default-Reactionner')
        assert link is not None

        # Receiver - a default receiver got created
        assert self._arbiter.conf.receivers
        # link = self._arbiter.conf.receivers.find_by_name('Default-Receiver')
        # assert link is not None

        # Only one realm in the configuration
        assert len(self._arbiter.conf.realms) == 1

        # 'All' realm exists
        realm = self._arbiter.conf.realms.find_by_name("All")
        assert realm is not None
        assert realm.realm_name == 'All'
        assert realm.alias == 'Self created default realm'
        assert realm.default

        # 'All' realm is the default realm
        default_realm = self._arbiter.conf.realms.get_default()
        assert realm == default_realm

        # Default realm does not exist anymore
        realm = self._arbiter.conf.realms.find_by_name("Default")
        assert realm is None

        # Hosts without realm definition are in the Default realm
        hosts = self._arbiter.conf.hosts
        assert len(hosts) == 2
        for host in hosts:
            assert host.realm == default_realm.uuid
            assert host.realm_name == default_realm.get_name()

    def test_no_scheduler_in_realm(self):
        """ Test missing scheduler in realm
        A realm is defined but no scheduler, nor broker, nor poller exist for this realm

        :return: None
        """
        self.setup_with_file('cfg/realms/no_scheduler_in_realm.cfg')
        self.show_logs()
        assert self.conf_is_correct

        self.assert_any_log_match(re.escape("Adding a scheduler for the realm: Distant"))
        self.assert_any_log_match(re.escape("Adding a poller for the realm: Distant"))
        self.assert_any_log_match(re.escape("Adding a broker for the realm: Distant"))
        # self.assert_any_log_match(re.escape("Adding a reactionner for the realm: Distant"))
        # self.assert_any_log_match(re.escape("Adding a receiver for the realm: Distant"))
        self.assert_any_log_match(re.escape("All: (in/potential) (schedulers:1) (pollers:1/1) "
                                            "(reactionners:1/1) (brokers:2/2) (receivers:1/1)"))
        self.assert_any_log_match(re.escape("Distant: (in/potential) (schedulers:1) (pollers:1/1) "
                                            "(reactionners:0/0) (brokers:1/1) (receivers:0/0)"))

        assert "Some hosts exist in the realm 'Distant' " \
               "but no scheduler is defined for this realm" in self.configuration_warnings
        assert "Some hosts exist in the realm 'Distant' " \
               "but no poller is defined for this realm" in self.configuration_warnings

        # Scheduler added for the realm
        for link in self._arbiter.conf.schedulers:
            if link.name == 'scheduler-Distant':
                break
        else:
            assert False

        # Broker added for the realm
        for link in self._arbiter.conf.brokers:
            if link.name == 'broker-Distant':
                break
        else:
            assert False

        # Poller added for the realm
        for link in self._arbiter.conf.pollers:
            if link.name == 'poller-Distant':
                break
        else:
            assert False

        # # Reactionner added for the realm
        # for link in self._arbiter.conf.reactionners:
        #     if link.name == 'reactionner-Distant':
        #         break
        # else:
        #     assert False
        #
        # # Receiver added for the realm
        # for link in self._arbiter.conf.receivers:
        #     if link.name == 'receiver-Distant':
        #         break
        # else:
        #     assert False

    def test_no_broker_in_realm(self):
        """ Test missing broker in realm
        Test realms on each host

        :return: None
        """
        self.setup_with_file('cfg/realms/no_broker_in_realm.cfg', 'cfg/realms/no_broker_in_realm.ini')
        self.show_logs()
        assert self.conf_is_correct

        dist = self._arbiter.conf.realms.find_by_name("Distant")
        assert dist is not None
        sched = self._arbiter.conf.schedulers.find_by_name("scheduler-distant")
        assert sched is not None
        assert 0 == len(self._arbiter.conf.realms[sched.realm].potential_brokers)
        assert 0 == len(self._arbiter.conf.realms[sched.realm].potential_pollers)
        assert 0 == len(self._arbiter.conf.realms[sched.realm].potential_reactionners)
        assert 0 == len(self._arbiter.conf.realms[sched.realm].potential_receivers)

    def test_realm_host_assignation(self):
        """ Test host realm assignation
        Test realms on each host

        :return: None
        """
        self.setup_with_file('cfg/realms/several_realms.cfg', 'cfg/realms/several_realms.ini')
        self.show_configuration_logs()
        assert self.conf_is_correct

        for scheduler in self._schedulers:
            print("Scheduler: %s" % scheduler)
            if scheduler == 'Scheduler-1':
                sched_realm1 = self._schedulers[scheduler]
            elif scheduler == 'Scheduler-2':
                sched_realm2 = self._schedulers[scheduler]
        realm1 = self._arbiter.conf.realms.find_by_name('realm1')
        assert realm1 is not None
        realm2 = self._arbiter.conf.realms.find_by_name('realm2')
        assert realm2 is not None

        print(sched_realm1.pushed_conf.hosts)
        print(sched_realm2.pushed_conf.hosts)
        # find_by_name is not usable in a scheduler !
        # test_host_realm1 = sched_realm1.pushed_conf.hosts.find_by_name("test_host_realm1")
        # Host test_host_realm1 is in the realm 1 and not in the realm 2
        for host in sched_realm1.pushed_conf.hosts:
            if host.get_name() == 'test_host_realm1':
                assert realm1.uuid == host.realm
                break
        else:
            assert False

        for host in sched_realm2.pushed_conf.hosts:
            if host.get_name() == 'test_host_realm1':
                assert False
                break
        else:
            assert True

        # Host test_host_realm2 is in the realm 1 and not in the realm 2
        for host in sched_realm2.pushed_conf.hosts:
            if host.get_name() == 'test_host_realm2':
                assert realm2.uuid == host.realm
                break
        else:
            assert False

        for host in sched_realm1.pushed_conf.hosts:
            if host.get_name() == 'test_host_realm2':
                assert False
                break
        else:
            assert True

    def test_undefined_used_realm(self):
        """ Test undefined realm used in daemons

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/realms/use_undefined_realm.cfg')
        self.show_logs()
        assert not self.conf_is_correct
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in scheduler::Scheduler-distant is incorrect; "
        ))
        self.assert_any_cfg_log_match(re.escape(
            "The scheduler Scheduler-distant has an unknown realm 'Distant'"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "schedulers configuration is incorrect!"
        ))

    def test_realm_hostgroup_assignation(self):
        """ Test realm hostgroup assignation

        Check realm and hostgroup

        :return: None
        """
        self.setup_with_file('cfg/realms/several_realms.cfg', 'cfg/realms/several_realms.ini')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        # self.assertEqual(len(self.configuration_warnings), 1)

        # self.assert_any_cfg_log_match(
        #     "host test_host3_hg_realm2 is not in the same realm than its hostgroup in_realm2"
        # )

        # Check all daemons exist
        assert len(self._arbiter.conf.arbiters) == 1
        assert len(self._arbiter.conf.schedulers) == 2
        assert len(self._arbiter.conf.brokers) == 2
        assert len(self._arbiter.conf.pollers) == 2
        assert len(self._arbiter.conf.reactionners) == 1
        assert len(self._arbiter.conf.receivers) == 1

        for daemon in self._arbiter.conf.schedulers:
            assert daemon.get_name() in ['Scheduler-1', 'Scheduler-2']
            assert daemon.realm in self._arbiter.conf.realms

        for daemon in self._arbiter.conf.brokers:
            assert daemon.get_name() in ['Broker-1', 'Broker-2']
            assert daemon.realm in self._arbiter.conf.realms

        for daemon in self._arbiter.conf.pollers:
            assert daemon.get_name() in ['Poller-1', 'Poller-2']
            assert daemon.realm in self._arbiter.conf.realms

        for daemon in self._arbiter.conf.receivers:
            assert daemon.get_name() in ['receiver-master']
            assert daemon.realm in self._arbiter.conf.realms

        in_realm2 = self._schedulers['Scheduler-1'].hostgroups.find_by_name('in_realm2')
        realm1 = self._arbiter.conf.realms.find_by_name('realm1')
        assert realm1 is not None
        realm2 = self._arbiter.conf.realms.find_by_name('realm2')
        assert realm2 is not None

        sched_realm1 = self._schedulers['Scheduler-1']
        sched_realm2 = self._schedulers['Scheduler-2']

        # 1 and 2 are link to realm2 because they are in the hostgroup in_realm2
        test_host1_hg_realm2 = sched_realm2.pushed_conf.hosts.find_by_name("test_host1_hg_realm2")
        assert test_host1_hg_realm2 is not None
        assert realm2.uuid == test_host1_hg_realm2.realm
        assert in_realm2.get_name() in [sched_realm2.pushed_conf.hostgroups[hg].get_name() for hg in test_host1_hg_realm2.hostgroups]

        test_host2_hg_realm2 = sched_realm2.pushed_conf.hosts.find_by_name("test_host2_hg_realm2")
        assert test_host2_hg_realm2 is not None
        assert realm2.uuid == test_host2_hg_realm2.realm
        assert in_realm2.get_name() in [sched_realm2.pushed_conf.hostgroups[hg].get_name() for hg in test_host2_hg_realm2.hostgroups]

        test_host3_hg_realm2 = sched_realm2.pushed_conf.hosts.find_by_name("test_host3_hg_realm2")
        assert test_host3_hg_realm2 is None
        test_host3_hg_realm2 = sched_realm1.pushed_conf.hosts.find_by_name("test_host3_hg_realm2")
        assert test_host3_hg_realm2 is not None
        assert realm1.uuid == test_host3_hg_realm2.realm
        assert in_realm2.get_name() in [sched_realm2.pushed_conf.hostgroups[hg].get_name() for hg in test_host3_hg_realm2.hostgroups]

        hostgroup_realm2 = sched_realm1.pushed_conf.hostgroups.find_by_name("in_realm2")
        assert hostgroup_realm2 is not None
        hostgroup_realm2 = sched_realm2.pushed_conf.hostgroups.find_by_name("in_realm2")
        assert hostgroup_realm2 is not None

    def test_sub_realms(self):
        """ Test realm / sub-realm

        :return: None
        """
        self.setup_with_file('cfg/realms/sub_realms.cfg', 'cfg/realms/sub_realms.ini',
                             verbose=False)
        assert self.conf_is_correct

        print("Realms: %s" % self._arbiter.conf.realms)

        world = self._arbiter.conf.realms.find_by_name('World')
        assert world is not None
        europe = self._arbiter.conf.realms.find_by_name('Europe')
        assert europe is not None
        paris = self._arbiter.conf.realms.find_by_name('Paris')
        assert paris is not None

        # Get satellites of the World realm
        assert len(world.get_satellites_by_type('arbiter')) == 0
        assert len(world.get_satellites_by_type('scheduler')) == 1
        assert len(world.get_satellites_by_type('broker')) == 2
        assert len(world.get_satellites_by_type('poller')) == 1
        assert len(world.get_satellites_by_type('receiver')) == 1
        assert len(world.get_satellites_by_type('reactionner')) == 1

        # Get satellites of the Europe realm
        assert len(europe.get_satellites_by_type('arbiter')) == 0
        assert len(europe.get_satellites_by_type('scheduler')) == 1
        assert len(europe.get_satellites_by_type('broker')) == 1
        assert len(europe.get_satellites_by_type('poller')) == 0
        assert len(europe.get_satellites_by_type('receiver')) == 1
        assert len(europe.get_satellites_by_type('reactionner')) == 1

        # Get satellites of the Paris realm
        assert len(europe.get_satellites_by_type('arbiter')) == 0
        assert len(europe.get_satellites_by_type('scheduler')) == 1
        assert len(europe.get_satellites_by_type('broker')) == 1
        assert len(europe.get_satellites_by_type('poller')) == 0
        assert len(europe.get_satellites_by_type('receiver')) == 1
        assert len(europe.get_satellites_by_type('reactionner')) == 1

        assert europe.uuid in world.all_sub_members
        assert paris.uuid in europe.all_sub_members

    def test_sub_realms_assignations(self):
        """ Test realm / sub-realm for broker

        :return: None
        """
        self.setup_with_file('cfg/realms/sub_realms.cfg', 'cfg/realms/sub_realms.ini',
                             verbose=False)
        assert self.conf_is_correct

        print("Realms: %s" % self._arbiter.conf.realms)

        world = self._arbiter.conf.realms.find_by_name('World')
        assert world is not None
        europe = self._arbiter.conf.realms.find_by_name('Europe')
        assert europe is not None
        paris = self._arbiter.conf.realms.find_by_name('Paris')
        assert paris is not None
        # Get the broker in the realm level
        bworld = self._arbiter.conf.brokers.find_by_name('B-world')
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
        self.setup_with_file('cfg/realms/sub_realms_multi_levels.cfg',
                             'cfg/realms/sub_realms_multi_levels.ini',
                             verbose=False)
        assert self.conf_is_correct

        Osaka = self._arbiter.conf.realms.find_by_name('Osaka')
        assert Osaka is not None

        Tokyo = self._arbiter.conf.realms.find_by_name('Tokyo')
        assert Tokyo is not None

        Japan = self._arbiter.conf.realms.find_by_name('Japan')
        assert Japan is not None

        Asia = self._arbiter.conf.realms.find_by_name('Asia')
        assert Asia is not None

        Turin = self._arbiter.conf.realms.find_by_name('Turin')
        assert Turin is not None

        Roma = self._arbiter.conf.realms.find_by_name('Roma')
        assert Roma is not None

        Italy = self._arbiter.conf.realms.find_by_name('Italy')
        assert Italy is not None

        Lyon = self._arbiter.conf.realms.find_by_name('Lyon')
        assert Lyon is not None

        Paris = self._arbiter.conf.realms.find_by_name('Paris')
        assert Paris is not None

        France = self._arbiter.conf.realms.find_by_name('France')
        assert France is not None

        Europe = self._arbiter.conf.realms.find_by_name('Europe')
        assert Europe is not None

        World = self._arbiter.conf.realms.find_by_name('World')
        assert World is not None

        # Check members for each realm - members list is an ordered list!
        print("The World: %s" % (World))
        assert World.realm_members != [Europe.get_name(), Asia.get_name()]
        assert World.realm_members == [Asia.get_name(), Europe.get_name()]
        print("Asia: %s" % (Asia))
        assert Asia.realm_members == [Japan.get_name()]
        assert Japan.realm_members != [Tokyo.get_name(), Osaka.get_name()]
        assert Japan.realm_members == [Osaka.get_name(), Tokyo.get_name()]
        print("Europe: %s" % (Europe))
        assert Europe.realm_members == [France.get_name(), Italy.get_name()]
        assert Italy.realm_members == [Roma.get_name(), Turin.get_name()]
        assert France.realm_members == [Lyon.get_name(), Paris.get_name()]

        # Check all_sub_members for each realm - ordered lists!
        assert Lyon.all_sub_members == []
        assert Paris.all_sub_members == []
        assert France.all_sub_members == [Lyon.uuid, Paris.uuid]

        assert Turin.all_sub_members == []
        assert Roma.all_sub_members == []
        assert Italy.all_sub_members == [Roma.uuid, Turin.uuid]

        assert Osaka.all_sub_members == []
        assert Tokyo.all_sub_members == []
        assert Japan.all_sub_members == [Osaka.uuid, Tokyo.uuid]
        assert Asia.all_sub_members == [Japan.uuid, Osaka.uuid, Tokyo.uuid]

        assert Europe.all_sub_members == [France.uuid, Lyon.uuid, Paris.uuid,
                                          Italy.uuid, Roma.uuid, Turin.uuid]

        assert World.all_sub_members_names == [
            'Asia',
                'Japan', 'Osaka', 'Tokyo',
            'Europe',
                'France', 'Lyon', 'Paris',
                'Italy', 'Roma', 'Turin']
        assert World.all_sub_members == [
            Asia.uuid,
                Japan.uuid, Osaka.uuid, Tokyo.uuid,
            Europe.uuid,
                France.uuid, Lyon.uuid, Paris.uuid,
                Italy.uuid, Roma.uuid, Turin.uuid]

        # check satellites defined in each realms
        broker_uuid = self._arbiter.conf.brokers.find_by_name('broker-master').uuid
        poller_uuid = self._arbiter.conf.pollers.find_by_name('poller-master').uuid
        receiver_uuid = self._arbiter.conf.receivers.find_by_name('receiver-master').uuid
        reactionner_uuid = self._arbiter.conf.reactionners.find_by_name('reactionner-master').uuid

        for realm in [Osaka, Tokyo, Japan, Asia, Turin, Roma, Italy, Lyon, Paris, France, Europe, World]:
            print "Realm %s, brokers: %s" % (realm.realm_name, realm.brokers)
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

        assert set(France.brokers) == set([broker_uuid, self._arbiter.conf.brokers.find_by_name('broker-france').uuid])
        assert set(France.potential_brokers) == set([broker_uuid, self._arbiter.conf.brokers.find_by_name('broker-france').uuid])
        assert France.nb_brokers == 2

    def test_sub_realms_multi_levels_loop(self):
        """ Test realm / sub-realm / sub-sub-realms... with a loop, so exit with error message

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_realms_sub_multi_levels_loop.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()
