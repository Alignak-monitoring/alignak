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
from .alignak_test import AlignakTest
import pytest


class TestRealms(AlignakTest):
    """
    This class test realms usage
    """
    def setUp(self):
        super(TestRealms, self).setUp()
        self.set_unit_tests_logger_level('INFO')

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
        self.assert_any_log_match(re.escape("No reactionner defined, I am adding one on 127.0.0.1:10000"))
        self.assert_any_log_match(re.escape("No poller defined, I am adding one on 127.0.0.1:10001"))
        self.assert_any_log_match(re.escape("No broker defined, I am adding one on 127.0.0.1:10002"))
        self.assert_any_log_match(re.escape("No receiver defined, I am adding one on 127.0.0.1:10003"))

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

        self.assert_any_log_match(re.escape("No reactionner defined, I am adding one on 127.0.0.1:10000"))
        self.assert_any_log_match(re.escape("No poller defined, I am adding one on 127.0.0.1:10001"))
        self.assert_any_log_match(re.escape("No broker defined, I am adding one on 127.0.0.1:10002"))
        self.assert_any_log_match(re.escape("No receiver defined, I am adding one on 127.0.0.1:10003"))

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
        self.setup_with_file('cfg/realms/no_defined_daemons.cfg',
                             'cfg/realms/no_defined_daemons.ini', verbose=True)
        assert self.conf_is_correct
        self.show_logs()

        self.assert_any_log_match(re.escape("No scheduler defined, I am adding one on 127.0.0.1:10000"))
        self.assert_any_log_match(re.escape("No reactionner defined, I am adding one on 127.0.0.1:10001"))
        self.assert_any_log_match(re.escape("No poller defined, I am adding one on 127.0.0.1:10002"))
        self.assert_any_log_match(re.escape("No broker defined, I am adding one on 127.0.0.1:10003"))
        self.assert_any_log_match(re.escape("No receiver defined, I am adding one on 127.0.0.1:10004"))
        # self.assert_any_log_match(re.escape("Tagging Default-Poller with realm All"))
        # self.assert_any_log_match(re.escape("Tagging Default-Broker with realm All"))
        # self.assert_any_log_match(re.escape("Tagging Default-Reactionner with realm All"))
        # self.assert_any_log_match(re.escape("Tagging Default-Scheduler with realm All"))
        # self.assert_any_log_match(re.escape("Prepare dispatching for this realm"))

        scheduler_link = self._arbiter.conf.schedulers.find_by_name('Default-Scheduler')
        assert scheduler_link is not None
        # # Scheduler configuration is ok
        # assert self._schedulers['Default-Scheduler'].pushed_conf.conf_is_correct

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
        assert realm.alias == ''
        assert realm.default

        # 'All' realm is the default realm
        default_realm = self._arbiter.conf.realms.get_default()
        assert realm == default_realm

        # Default realm does not exist anymore
        realm = self._arbiter.conf.realms.find_by_name("Default")
        assert realm is None

        # Hosts without realm definition are in the Default realm
        hosts = self._arbiter.conf.hosts
        assert len(hosts) == 4
        for host in hosts:
            assert host.realm == default_realm.uuid
            assert host.realm_name == default_realm.get_name()

    def test_no_scheduler_in_realm(self):
        """ Test missing scheduler in realm
        A realm is defined but no scheduler, nor broker, nor poller exist for this realm

        Configuration is not correct

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/realms/no_scheduler_in_realm.cfg')
        self.show_logs()
        assert not self.conf_is_correct

    def test_no_scheduler_in_realm_self_add(self):
        """ Test missing scheduler in realm, self add a scheduler
        A realm is defined but no scheduler, nor broker, nor poller exist for this realm

        :return: None
        """
        self.setup_with_file('cfg/realms/no_scheduler_in_realm_self_add.cfg')
        self.show_logs()
        assert self.conf_is_correct

        self.assert_any_log_match(re.escape("Adding a scheduler for the realm: Distant"))
        self.assert_any_log_match(re.escape("Adding a poller for the realm: Distant"))
        # self.assert_any_log_match(re.escape("Adding a broker for the realm: Distant"))
        self.assert_any_log_match(re.escape("Adding a reactionner for the realm: Distant"))
        self.assert_any_log_match(re.escape("Adding a receiver for the realm: Distant"))
        self.assert_any_log_match(re.escape("Realm All: (in/potential) (schedulers:1/0) "
                                            "(pollers:1/0) (reactionners:1/0) (brokers:1/0) "
                                            "(receivers:1/0)"))
        self.assert_any_log_match(re.escape("Realm Distant: (in/potential) (schedulers:1/0) "
                                            "(pollers:1/0) (reactionners:1/0) (brokers:1/0) "
                                            "(receivers:1/0)"))

        assert "[config::Alignak global configuration] Some hosts exist in the realm 'Distant' " \
               "but no scheduler is defined for this realm." in self.configuration_warnings
        assert "[config::Alignak global configuration] Some hosts exist in the realm 'Distant' " \
               "but no reactionner is defined for this realm." in self.configuration_warnings
        assert "[config::Alignak global configuration] Some hosts exist in the realm 'Distant' " \
               "but no receiver is defined for this realm." in self.configuration_warnings
        assert "[config::Alignak global configuration] Some hosts exist in the realm 'Distant' " \
               "but no scheduler is defined for this realm." in self.configuration_warnings

        # Scheduler added for the realm
        for link in self._arbiter.conf.schedulers:
            print("Arbiter scheduler: %s" % link)
            if link.name == 'scheduler-Distant':
                break
        else:
            assert False

        # Broker added for the realm
        for link in self._arbiter.conf.brokers:
            print("Arbiter broker: %s" % link)
            if link.name == 'Broker-distant':
                break
        else:
            assert False

        # Poller added for the realm
        for link in self._arbiter.conf.pollers:
            if link.name == 'poller-Distant':
                break
        else:
            assert False

        # Reactionner added for the realm
        for link in self._arbiter.conf.reactionners:
            if link.name == 'reactionner-Distant':
                break
        else:
            assert False

        # Receiver added for the realm
        for link in self._arbiter.conf.receivers:
            if link.name == 'receiver-Distant':
                break
        else:
            assert False

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
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/realms/several_realms.cfg', 'cfg/realms/several_realms.ini')
        self.show_logs()
        assert not self.conf_is_correct

        self.assert_any_cfg_log_match(re.escape(
            "[hostgroup::in_realm2] Configuration is incorrect; "
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[hostgroup::in_realm2] host test_host3_hg_realm2 (realm: realm1) is not in "
            "the same realm than its hostgroup in_realm2 (realm: realm2)"
        ))

        # self.assert_any_cfg_log_match(re.escape(
        #     "hostgroup in_realm2 got the default realm but it has some hosts that are from different realms"
        # ))

        # Some error messages
        assert len(self.configuration_errors) == 3

        realm1 = self._arbiter.conf.realms.find_by_name('realm1')
        assert realm1 is not None
        realm2 = self._arbiter.conf.realms.find_by_name('realm2')
        assert realm2 is not None

        host = self._arbiter.conf.hosts.find_by_name('test_host_realm1')
        assert realm1.uuid == host.realm

        host = self._arbiter.conf.hosts.find_by_name('test_host_realm2')
        assert realm2.uuid == host.realm

    def test_undefined_used_realm(self):
        """ Test undefined realm used in daemons

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/realms/use_undefined_realm.cfg')
        self.show_logs()
        assert not self.conf_is_correct
        self.assert_any_cfg_log_match(re.escape(
            "The scheduler 'Scheduler-distant' is affected to an unknown realm: 'Distant'"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "The host 'bad_host' is affected to an unknown realm: 'Distant'"
        ))

    def test_realm_hostgroup_assignation(self):
        """ Test realm hostgroup assignation

        Check realm and hostgroup

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/realms/several_realms.cfg', 'cfg/realms/several_realms.ini')
        self.show_logs()
        assert not self.conf_is_correct

        self.assert_any_cfg_log_match(re.escape(
            "[hostgroup::in_realm2] Configuration is incorrect; "
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[hostgroup::in_realm2] host test_host3_hg_realm2 (realm: realm1) is not "
            "in the same realm than its hostgroup in_realm2 (realm: realm2)"
        ))

        # self.assert_any_cfg_log_match(re.escape(
        #     "hostgroup in_realm2 got the default realm but it has some hosts that are from different realms: None and realm1. The realm cannot be adjusted!"
        # ))

        # Some error messages
        assert len(self.configuration_errors) == 3

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

        # Hostgroup in_realm2
        in_realm2 = self._arbiter.conf.hostgroups.find_by_name('in_realm2')

        # Realms
        realm1 = self._arbiter.conf.realms.find_by_name('realm1')
        assert realm1 is not None
        realm2 = self._arbiter.conf.realms.find_by_name('realm2')
        assert realm2 is not None

        host = self._arbiter.conf.hosts.find_by_name('test_host_realm1')
        assert realm1.uuid == host.realm

        host = self._arbiter.conf.hosts.find_by_name('test_host_realm2')
        assert realm2.uuid == host.realm

        # test_host1 and test_host2 are linked to realm2 because they are in the hostgroup in_realm2
        test_host1_hg_realm2 = self._arbiter.conf.hosts.find_by_name("test_host1_hg_realm2")
        assert test_host1_hg_realm2 is not None
        assert realm2.uuid == test_host1_hg_realm2.realm
        assert in_realm2.get_name() in [self._arbiter.conf.hostgroups[hg].get_name() for hg in test_host1_hg_realm2.hostgroups]

        test_host2_hg_realm2 = self._arbiter.conf.hosts.find_by_name("test_host2_hg_realm2")
        assert test_host2_hg_realm2 is not None
        assert realm2.uuid == test_host2_hg_realm2.realm
        assert in_realm2.get_name() in [self._arbiter.conf.hostgroups[hg].get_name() for hg in test_host2_hg_realm2.hostgroups]

        # test_host3 is linked to realm1 but its hostgroup in realm2!
        test_host3_hg_realm2 = self._arbiter.conf.hosts.find_by_name("test_host3_hg_realm2")
        assert test_host3_hg_realm2 is not None
        assert realm1.uuid == test_host3_hg_realm2.realm
        assert in_realm2.get_name() in [self._arbiter.conf.hostgroups[hg].get_name() for hg in test_host3_hg_realm2.hostgroups]

    def test_sub_realms(self):
        """ Test realm / sub-realm

        All main daemons are in the realm World and manage the sub-realms except for the poller!
        A second broker exist in the realm World and a receiver exist in the realm Paris

        :return: None
        """
        self.setup_with_file('cfg/realms/sub_realms.cfg', 'cfg/realms/sub_realms.ini',
                             verbose=False, dispatching=True)
        assert self.conf_is_correct

        print("Realms: %s" % self._arbiter.conf.realms)

        world = self._arbiter.conf.realms.find_by_name('World')
        print(world)
        assert world is not None
        europe = self._arbiter.conf.realms.find_by_name('Europe')
        assert europe is not None
        paris = self._arbiter.conf.realms.find_by_name('Paris')
        assert paris is not None

        # Get satellites of the World realm
        assert len(world.get_satellites_by_type('arbiter')) == 0
        satellites = world.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "arbiter")
        assert len(satellites) == 0
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(world.get_satellites_by_type('scheduler')) == 1
        satellites = world.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "scheduler")
        assert len(satellites) == 1
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(world.get_satellites_by_type('broker')) == 2
        satellites = world.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "broker")
        assert len(satellites) == 2
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(world.get_satellites_by_type('poller')) == 1
        satellites = world.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "poller")
        assert len(satellites) == 1
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(world.get_satellites_by_type('receiver')) == 1
        satellites = world.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "receiver")
        assert len(satellites) == 1
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(world.get_satellites_by_type('reactionner')) == 1
        satellites = world.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "reactionner")
        assert len(satellites) == 1
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        # Get satellites of the Europe realm
        assert europe.uuid in world.all_sub_members
        assert len(europe.get_satellites_by_type('arbiter')) == 0
        satellites = europe.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "arbiter")
        assert len(satellites) == 0
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(europe.get_satellites_by_type('scheduler')) == 1
        satellites = europe.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "scheduler")
        assert len(satellites) == 1
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(europe.get_satellites_by_type('broker')) == 0
        satellites = europe.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "broker")
        assert len(satellites) == 1
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(europe.get_satellites_by_type('poller')) == 0
        satellites = europe.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "poller")
        assert len(satellites) == 0     # Because the master poller is not managing sub-realms! Else it should be 1
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(europe.get_satellites_by_type('receiver')) == 0
        satellites = europe.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "receiver")
        assert len(satellites) == 1
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(europe.get_satellites_by_type('reactionner')) == 0
        satellites = europe.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "reactionner")
        assert len(satellites) == 1
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))


        # Get satellites of the Paris realm
        assert paris.uuid in europe.all_sub_members
        assert len(paris.get_satellites_by_type('arbiter')) == 0
        satellites = paris.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "arbiter")
        assert len(satellites) == 0
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(paris.get_satellites_by_type('scheduler')) == 1
        satellites = paris.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "scheduler")
        assert len(satellites) == 1
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(paris.get_satellites_by_type('broker')) == 0
        satellites = paris.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "broker")
        assert len(satellites) == 1
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(paris.get_satellites_by_type('poller')) == 0
        satellites = paris.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "poller")
        assert len(satellites) == 0     # Because the master poller is not managing sub-realms! Else it should be 1
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(paris.get_satellites_by_type('receiver')) == 1
        satellites = paris.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "receiver")
        assert len(satellites) == 1
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

        assert len(paris.get_satellites_by_type('reactionner')) == 0
        satellites = paris.get_potential_satellites_by_type(self._arbiter.dispatcher.all_daemons_links, "reactionner")
        assert len(satellites) == 1
        for sat_link in satellites:
            print("%s / %s" % (sat_link.type, sat_link.name))

    def test_sub_realms_assignations(self):
        """ Test realm / sub-realm assignation

        Realms:
            World (default)
            -> Europe
                -> Paris

        Satellites:
            arbiter-master, manage_sub_realms=1
            scheduler-master, manage_sub_realms=1
            poller-master, manage_sub_realms=0
            reactionner-master, manage_sub_realms=1
            broker-master, manage_sub_realms=0
            broker-B-world, manage_sub_realms=1
            receiver-master, manage_sub_realms=1

        One sub-realm brokers for the realm World : ok
        One "not sub-realm" broker for the default realm, should not disturb !
        On "not sub-realm" poller for the default realm, I should not have any poller
        for the sub realms !

        :return: None
        """
        self.setup_with_file('cfg/realms/sub_realms.cfg', 'cfg/realms/sub_realms.ini',
                             verbose=False)
        assert self.conf_is_correct

        print("Realms: \n%s" % self._arbiter.conf.realms)

        world = self._arbiter.conf.realms.find_by_name('World')
        assert world is not None
        europe = self._arbiter.conf.realms.find_by_name('Europe')
        assert europe is not None
        paris = self._arbiter.conf.realms.find_by_name('Paris')
        assert paris is not None

        # Get the B-world broker
        # This broker is defined in the realm World and it manages sub-realms
        bworld = self._arbiter.conf.brokers.find_by_name('broker-b')
        assert bworld is not None

        # broker should be in the world level
        assert (bworld.uuid in world.brokers) is True
        # in europe too
        assert (bworld.uuid in europe.potential_brokers) is True
        # and in paris too
        assert (bworld.uuid in paris.potential_brokers) is True

        # Get the master broker
        # This broker is defined in the realm World and it does not manage sub-realms!
        bmaster = self._arbiter.conf.brokers.find_by_name('broker-master')
        assert bmaster is not None

        # broker should be in the world level
        assert (bmaster.uuid in world.brokers) is True
        # but not in Europe !
        assert (bmaster.uuid not in europe.potential_brokers) is True
        # nor in paris!
        assert (bmaster.uuid not in paris.potential_brokers) is True

        # Get the master poller
        # This poller is defined in the realm World and it does not manage sub-realms
        sat = self._arbiter.conf.pollers.find_by_name('poller-master')
        assert sat is not None

        # poller should be in the world level
        assert (sat.uuid in world.pollers) is True
        # but not in Europe !
        assert (sat.uuid not in europe.potential_pollers) is True
        # nor in paris!
        assert (sat.uuid not in paris.potential_pollers) is True

        # Get the scheduler master that should be in all realms
        sat = self._arbiter.conf.schedulers.find_by_name('scheduler-master')
        assert (sat.uuid in world.schedulers) is True
        assert (sat.uuid in europe.potential_schedulers) is True
        assert (sat.uuid in paris.potential_schedulers) is True

        # Get the reactionner master that should be in all realms
        sat = self._arbiter.conf.reactionners.find_by_name('reactionner-master')
        assert (sat.uuid in world.reactionners) is True
        assert (sat.uuid in europe.potential_reactionners) is True
        assert (sat.uuid in paris.potential_reactionners) is True

        # Get the receiver master that should be in all realms
        sat = self._arbiter.conf.receivers.find_by_name('receiver-master')
        assert (sat.uuid in world.receivers) is True
        assert (sat.uuid in europe.potential_receivers) is True
        assert (sat.uuid in paris.potential_receivers) is True

    def test_sub_realms_multi_levels(self):
        """ Test realm / sub-realm / sub-sub-realms...

        Realms:
            World (default)
            + Asia
            ++ Japan
            +++ Tokyo
            +++ Osaka
            + Europe
            ++ Italy
            +++ Torino
            +++ Roma
            ++ France
            +++ Paris
            +++ Lyon
            World2 (also references Asia as a sub-realm)

        Satellites (declared):
            arbiter-master, manage_sub_realms=1
            scheduler-master, manage_sub_realms=1
            poller-master, manage_sub_realms=1
            reactionner-master, manage_sub_realms=1
            broker-master, manage_sub_realms=1
            receiver-master, manage_sub_realms=1

            broker-france, manage_sub_realms=0 -> realm France
            scheduler-france, manage_sub_realms=0 -> realm France

        TODO: this test raises some error logs because of missing schedulers but the
        configuration is accepted and looks correct! Note that this configuration is
        a bit complicated and ambiguous!!!
        :return: None
        """
        self.setup_with_file('cfg/realms/sub_realms_multi_levels.cfg',
                             'cfg/realms/sub_realms_multi_levels.ini',
                             verbose=False)
        assert self.conf_is_correct
        self.show_logs()

        print("Realms: \n%s " % self._arbiter.conf.realms)

        Osaka = self._arbiter.conf.realms.find_by_name('Osaka')
        assert Osaka is not None

        Tokyo = self._arbiter.conf.realms.find_by_name('Tokyo')
        assert Tokyo is not None

        Japan = self._arbiter.conf.realms.find_by_name('Japan')
        assert Japan is not None

        Asia = self._arbiter.conf.realms.find_by_name('Asia')
        assert Asia is not None

        Torino = self._arbiter.conf.realms.find_by_name('Torino')
        assert Torino is not None

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
        print(("The World: %s" % (World)))
        assert World.realm_members != [Europe.get_name(), Asia.get_name()]
        assert World.realm_members == [Asia.get_name(), Europe.get_name()]
        print(("Asia: %s" % (Asia)))
        assert Asia.realm_members == [Japan.get_name()]
        assert Japan.realm_members != [Tokyo.get_name(), Osaka.get_name()]
        assert Japan.realm_members == [Osaka.get_name(), Tokyo.get_name()]
        print(("Europe: %s" % (Europe)))
        assert Europe.realm_members == [France.get_name(), Italy.get_name()]
        assert Italy.realm_members == [Roma.get_name(), Torino.get_name()]
        assert France.realm_members == [Lyon.get_name(), Paris.get_name()]

        # Check all_sub_members for each realm - ordered lists!
        assert Lyon.all_sub_members == []
        assert Paris.all_sub_members == []
        assert France.all_sub_members == [Lyon.uuid, Paris.uuid]

        assert Torino.all_sub_members == []
        assert Roma.all_sub_members == []
        assert Italy.all_sub_members == [Roma.uuid, Torino.uuid]

        assert Osaka.all_sub_members == []
        assert Tokyo.all_sub_members == []
        assert Japan.all_sub_members == [Osaka.uuid, Tokyo.uuid]
        assert Asia.all_sub_members == [Japan.uuid, Osaka.uuid, Tokyo.uuid]

        assert Europe.all_sub_members == [France.uuid, Lyon.uuid, Paris.uuid,
                                          Italy.uuid, Roma.uuid, Torino.uuid]

        assert World.all_sub_members_names == [
            'Asia',
                'Japan', 'Osaka', 'Tokyo',
            'Europe',
                'France', 'Lyon', 'Paris',
                'Italy', 'Roma', 'Torino']
        assert World.all_sub_members == [
            Asia.uuid,
                Japan.uuid, Osaka.uuid, Tokyo.uuid,
            Europe.uuid,
                France.uuid, Lyon.uuid, Paris.uuid,
                Italy.uuid, Roma.uuid, Torino.uuid]


        # Check satellites defined in each realms
        poller_uuid = self._arbiter.conf.pollers.find_by_name('poller-master').uuid
        receiver_uuid = self._arbiter.conf.receivers.find_by_name('receiver-master').uuid
        reactionner_uuid = self._arbiter.conf.reactionners.find_by_name('reactionner-master').uuid
        scheduler_uuid = self._arbiter.conf.schedulers.find_by_name('scheduler-master').uuid
        broker_uuid = self._arbiter.conf.brokers.find_by_name('broker-master').uuid
        # Specific France realm satellites
        scheduler_france1_uuid = self._arbiter.conf.schedulers.find_by_name('scheduler-france1').uuid
        scheduler_france2_uuid = self._arbiter.conf.schedulers.find_by_name('scheduler-france2').uuid
        broker_france_uuid = self._arbiter.conf.brokers.find_by_name('broker-france').uuid

        for broker in self._arbiter.conf.brokers:
            print("Broker: %s" % (broker))

        # World has some satellites
        for realm in [World]:
            assert realm.pollers == [poller_uuid]
            assert realm.receivers == [receiver_uuid]
            assert realm.reactionners == [reactionner_uuid]
            assert realm.schedulers == [scheduler_uuid]
            assert realm.brokers == [broker_uuid]

            assert realm.potential_brokers == []
            assert realm.potential_schedulers == []
            assert realm.potential_pollers == []
            assert realm.potential_receivers == []
            assert realm.potential_reactionners == []

        # These realms have some potential satellites but no direct ones
        for realm in [Europe, Italy, Roma, Torino, Asia, Japan, Osaka, Tokyo]:
            assert realm.brokers == []
            assert realm.schedulers == []
            assert realm.pollers == []
            assert realm.receivers == []
            assert realm.reactionners == []

            assert realm.potential_pollers == [poller_uuid]
            assert realm.potential_receivers == [receiver_uuid]
            assert realm.potential_reactionners == [reactionner_uuid]
            assert realm.potential_schedulers == [scheduler_uuid]
            assert realm.potential_brokers == [broker_uuid]

        # France has some direct satellites
        for realm in [France]:
            assert realm.brokers == [broker_france_uuid]
            assert scheduler_france1_uuid in realm.schedulers
            assert scheduler_france2_uuid in realm.schedulers
            assert len(realm.schedulers) == 2
            assert realm.pollers == []
            assert realm.receivers == []
            assert realm.reactionners == []

            assert realm.potential_pollers == [poller_uuid]
            assert realm.potential_receivers == [receiver_uuid]
            assert realm.potential_reactionners == [reactionner_uuid]
            assert realm.potential_schedulers == [scheduler_uuid]
            assert realm.potential_brokers == [broker_uuid]

        # France sub-realms have some potential satellites
        for realm in [Paris, Lyon]:
            assert realm.brokers == []
            assert realm.schedulers == []
            assert realm.pollers == []
            assert realm.receivers == []
            assert realm.reactionners == []

            assert realm.potential_pollers == [poller_uuid]
            assert realm.potential_receivers == [receiver_uuid]
            assert realm.potential_reactionners == [reactionner_uuid]
            assert scheduler_uuid in realm.potential_schedulers
            assert scheduler_france2_uuid in realm.potential_schedulers
            assert scheduler_france2_uuid in realm.potential_schedulers
            assert len(realm.potential_schedulers) == 3
            assert broker_uuid in realm.potential_brokers
            # assert broker_france_uuid in realm.potential_brokers
            assert len(realm.potential_brokers) == 1

    def test_sub_realms_multi_levels_loop(self):
        """ Test realm / sub-realm / sub-sub-realms... with a loop, so exit with error message

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_realms_sub_multi_levels_loop.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()
