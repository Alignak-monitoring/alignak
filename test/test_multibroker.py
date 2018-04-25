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

"""
This file test the multibroker in schedulers
"""
import time
import pytest
import requests_mock
from alignak.misc.serialization import unserialize, get_alignak_class
from alignak.http.scheduler_interface import SchedulerInterface
from .alignak_test import AlignakTest


class TestMultibroker(AlignakTest):
    """
    This class test the multibroker in schedulers
    """
    def setUp(self):
        super(TestMultibroker, self).setUp()

    def test_multibroker_onesched(self):
        """ Test with 2 brokers and 1 scheduler

        :return: None
        """
        self.setup_with_file('cfg/multibroker/cfg_multi_broker_one_scheduler.cfg')

        my_scheduler = self._scheduler

        assert 2 == len(my_scheduler.my_daemon.brokers)

        # create broks
        host = my_scheduler.pushed_conf.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = my_scheduler.pushed_conf.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no raised host check on critical service check result
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])

        # Count broks in each broker
        broker_broks_count = {}
        broker1_link_uuid = None
        broker2_link_uuid = None
        for broker_link_uuid in my_scheduler.my_daemon.brokers:
            if my_scheduler.my_daemon.brokers[broker_link_uuid].name == 'broker-master':
                broker1_link_uuid = broker_link_uuid
            else:
                broker2_link_uuid = broker_link_uuid
            broker_broks_count[my_scheduler.my_daemon.brokers[broker_link_uuid].name] = 0
            print(("Broker %s:" % (my_scheduler.my_daemon.brokers[broker_link_uuid])))
            for brok in my_scheduler.my_daemon.brokers[broker_link_uuid].broks:
                broker_broks_count[my_scheduler.my_daemon.brokers[broker_link_uuid].name] += 1
                print(("- %s: %s"
                      % (brok, my_scheduler.my_daemon.brokers[broker_link_uuid].broks[brok])))

        # Same list of broks in the two brokers
        self.assertItemsEqual(my_scheduler.my_daemon.brokers[broker1_link_uuid].broks,
                              my_scheduler.my_daemon.brokers[broker2_link_uuid].broks)


        # Scheduler HTTP interface
        sched_interface = SchedulerInterface(my_scheduler.my_daemon)

        # Test broker-master that gets its broks from the scheduler
        # Get the scheduler broks to be sent ...
        to_send = [b for b in list(my_scheduler.my_daemon.brokers[broker1_link_uuid].broks.values())
                   if getattr(b, 'sent_to_externals', False)]
        for brok in to_send:
            print(("- %s" % (brok)))
        assert 6 == len(to_send)

        broks_list = sched_interface.get_broks('broker-master')
        broks_list = unserialize(broks_list, True)
        assert 6 == len(broks_list)
        assert broker_broks_count['broker-master'] == len(broks_list)

        # No more broks to get
        # Get the scheduler broks to be sent ...
        to_send = [b for b in list(my_scheduler.my_daemon.brokers[broker1_link_uuid].broks.values())
                   if getattr(b, 'sent_to_externals', False)]
        for brok in to_send:
            print(("- %s" % (brok)))
        assert 0 == len(to_send), "Still some broks to be sent!"



        # Test broker-master 2 that gets its broks from the scheduler
        # Get the scheduler broks to be sent ...
        to_send = [b for b in list(my_scheduler.my_daemon.brokers[broker2_link_uuid].broks.values())
                   if getattr(b, 'sent_to_externals', False)]
        for brok in to_send:
            print(("- %s" % (brok)))
        assert 6 == len(to_send)

        broks_list = sched_interface.get_broks('broker-master2')
        broks_list = unserialize(broks_list, True)
        assert 6 == len(broks_list)
        assert broker_broks_count['broker-master2'] == len(broks_list)

        # No more broks to get
        # Get the scheduler broks to be sent ...
        to_send = [b for b in list(my_scheduler.my_daemon.brokers[broker2_link_uuid].broks.values())
                   if getattr(b, 'sent_to_externals', False)]
        for brok in to_send:
            print(("- %s" % (brok)))
        assert 0 == len(to_send), "Still some broks to be sent!"

        # Test unknown broker that gets its broks from the scheduler
        broks_list = sched_interface.get_broks('broker-unknown')
        broks_list = unserialize(broks_list, True)
        assert 0 == len(broks_list)

        # Re-get broks
        # Test broker-master that gets its broks from the scheduler
        broks_list = sched_interface.get_broks('broker-master')
        broks_list = unserialize(broks_list, True)
        # No broks !
        assert 0 == len(broks_list)

        # Test broker-master 2 that gets its broks from the scheduler
        broks_list = sched_interface.get_broks('broker-master2')
        broks_list = unserialize(broks_list, True)
        # No broks !
        assert 0 == len(broks_list)

        # Some new broks
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])

        # Same list of broks in the two brokers
        self.assertItemsEqual(my_scheduler.my_daemon.brokers[broker1_link_uuid].broks,
                              my_scheduler.my_daemon.brokers[broker2_link_uuid].broks)
        assert len(my_scheduler.my_daemon.brokers[broker1_link_uuid].broks) > 1
        assert len(my_scheduler.my_daemon.brokers[broker2_link_uuid].broks) > 1

    def test_multibroker_multisched(self):
        """ Test with 2 brokers and 2 schedulers

        :return: None
        """
        self.setup_with_file('cfg/multibroker/cfg_multi_broker_multi_scheduler.cfg')
        self.clear_logs()

        assert 2 == len(self.schedulers)
        my_first_scheduler = self._schedulers['scheduler-master']
        my_second_scheduler = self._schedulers['scheduler-master2']
        print(("Sched #1 %d hosts: %s" % (len(my_first_scheduler.hosts), my_first_scheduler.hosts)))
        print(("Sched #2 %d hosts: %s" % (len(my_second_scheduler.hosts), my_second_scheduler.hosts)))
        #
        if len(my_first_scheduler.hosts) == 1:
            my_first_scheduler = self._schedulers['scheduler-master2']
            my_second_scheduler = self._schedulers['scheduler-master']

        # Two brokers in first scheduler
        print(("Sched #1 brokers: %s" % my_first_scheduler.my_daemon.brokers))
        assert 2 == len(my_first_scheduler.my_daemon.brokers)
        sched1_first_broker = None
        for broker_uuid in my_first_scheduler.my_daemon.brokers:
            broker = my_first_scheduler.my_daemon.brokers[broker_uuid]
            if broker.name == 'broker-master':
                sched1_first_broker = broker
                break
        else:
            assert False, "Scheduler 1 - No broker master link!"
        sched1_second_broker = None
        for broker_uuid in my_second_scheduler.my_daemon.brokers:
            broker = my_second_scheduler.my_daemon.brokers[broker_uuid]
            if broker.name == 'broker-master2':
                sched1_second_broker = broker
                break
        else:
            assert False, "Scheduler 1 - No broker master 2 link!"

        # Two brokers in second scheduler
        print(("Sched #2 brokers: %s" % my_second_scheduler.my_daemon.brokers))
        assert 2 == len(my_second_scheduler.my_daemon.brokers)
        sched2_first_broker = None
        for broker_uuid in my_second_scheduler.my_daemon.brokers:
            broker = my_second_scheduler.my_daemon.brokers[broker_uuid]
            if broker.name == 'broker-master':
                sched2_first_broker = broker
                break
        else:
            assert False, "Scheduler 2 - No broker master link!"
        sched2_second_broker = None
        for broker_uuid in my_second_scheduler.my_daemon.brokers:
            broker = my_second_scheduler.my_daemon.brokers[broker_uuid]
            if broker.name == 'broker-master2':
                sched2_second_broker = broker
                break
        else:
            assert False, "Scheduler 2 - No broker master 2 link!"

        # ---
        # Find hosts and services in my schedulers
        host1 = my_first_scheduler.hosts.find_by_name("test_host_0")
        host1.checks_in_progress = []
        host1.act_depend_of = []  # ignore the router

        svc1 = my_first_scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc1.checks_in_progress = []
        svc1.act_depend_of = []  # no hostchecks on critical checkresults

        host2 = my_second_scheduler.hosts.find_by_name("test_host_1")
        host2.checks_in_progress = []

        # ---
        # Create broks in the first scheduler
        self.scheduler_loop(1, [[host1, 0, 'UP'], [svc1, 0, 'OK']], my_first_scheduler)
        time.sleep(0.1)

        # ---
        # Check raised broks in the first scheduler brokers
        # 6 broks: new_conf, host_next_schedule (router), host_next_schedule (host),
        # service_next_schedule, host_check_result, service_check_result
        ref_broks_count = 6
        # Count broks in each broker
        broker_broks_count = {}
        for broker_link_uuid in my_first_scheduler.my_daemon.brokers:
            broker_broks_count[broker_link_uuid] = 0
            print(("Broker %s:" % (my_first_scheduler.my_daemon.brokers[broker_link_uuid])))
            for brok in my_first_scheduler.my_daemon.brokers[broker_link_uuid].broks:
                broker_broks_count[broker_link_uuid] += 1
                print(("- %s: %s" % (brok, my_first_scheduler.my_daemon.brokers[broker_link_uuid].broks[brok])))

        for broker_link_uuid in my_first_scheduler.my_daemon.brokers:
            assert broker_broks_count[broker_link_uuid] == ref_broks_count

        # ---
        # Create broks in the second scheduler
        self.scheduler_loop(1, [[host2, 0, 'UP']], my_second_scheduler)
        time.sleep(0.1)

        # ---
        # Check raised broks in the second scheduler brokers
        # 6 broks: new_conf, host_next_schedule (host), host_check_result
        ref_broks_count = 3
        # Count broks in each broker
        broker_broks_count = {}
        for broker_link_uuid in my_second_scheduler.my_daemon.brokers:
            broker_broks_count[broker_link_uuid] = 0
            print(("Broker %s:" % (my_second_scheduler.my_daemon.brokers[broker_link_uuid])))
            for brok in my_second_scheduler.my_daemon.brokers[broker_link_uuid].broks:
                broker_broks_count[broker_link_uuid] += 1
                print(("- %s: %s" % (brok, my_second_scheduler.my_daemon.brokers[broker_link_uuid].broks[brok])))

        for broker_link_uuid in my_second_scheduler.my_daemon.brokers:
            assert broker_broks_count[broker_link_uuid] == ref_broks_count

    @pytest.mark.skip("Temporary disabled...")
    def test_multibroker_multisched_realms(self):
        """ Test with realms / sub-realms

        All + sub (north + south):
          * broker-master
          * poller-masterAll


        All:
          * scheduler-master
          * poller-master


        North:
           * scheduler-masterN
           * broker-masterN


        South:
           * scheduler-masterS


        :return: None
        """
        self.setup_with_file('cfg/multibroker/cfg_multi_broker_multi_sched_realms.cfg',
                             'cfg/multibroker/alignak-multi_broker_multi_sched_realms.ini')

        # test right brokers sent to right schedulers
        smaster = self._schedulers['scheduler-master']
        smaster_n = self._schedulers['scheduler-masterN']
        smaster_s = self._schedulers['scheduler-masterS']

        # Brokers of each scheduler
        for broker_link_uuid in smaster.my_daemon.brokers:
            assert smaster.my_daemon.brokers[broker_link_uuid].name == 'broker-master'
        assert 1 == len(smaster.my_daemon.brokers)

        for broker_link_uuid in smaster_s.my_daemon.brokers:
            assert smaster_s.my_daemon.brokers[broker_link_uuid].name =='broker-master'
        assert 1 == len(smaster_s.my_daemon.brokers)

        for broker_link_uuid in smaster_n.my_daemon.brokers:
            assert smaster_n.my_daemon.brokers[broker_link_uuid].name in ['broker-master',
                                                                          'broker-masterN']
        assert 2 == len(smaster_n.my_daemon.brokers)

        brokermaster = None
        for sat in self._arbiter.dispatcher.satellites:
            if getattr(sat, 'broker_name', '') == 'broker-master':
                brokermaster = sat
