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
"""
This file test the dispatcher (distribute configuration to satellites)
"""

import time
import requests_mock
from alignak_test import AlignakTest
from alignak.misc.serialization import unserialize


class TestDispatcher(AlignakTest):
    """
    This class test the dispatcher  (distribute configuration to satellites)
    """

    def test_simple(self):
        """ Simple test

        have one realm and:
        * 1 scheduler
        * 1 poller
        * 1 receiver
        * 1 reactionner
        * 1 broker

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dispatcher_simple.cfg')
        assert 1 == len(self.arbiter.dispatcher.realms)
        for realm in self.arbiter.dispatcher.realms:
            assert 1 == len(realm.confs)
            for cfg in realm.confs.values():
                assert cfg.is_assigned
        assert 1 == len(self.arbiter.dispatcher.schedulers)
        assert 4 == len(self.arbiter.dispatcher.satellites)
        for satellite in self.arbiter.dispatcher.satellites:
            assert {} != satellite.cfg['schedulers'], satellite.get_name()
            assert 1 == len(satellite.cfg['schedulers']), 'must have 1 scheduler'

        # check if scheduler has right the 6 hosts
        assert 6 == len(self.schedulers['scheduler-master'].sched.hosts)

    def test_simple_multi_schedulers(self):
        """ Simple test (one realm) but with multiple schedulers:
        * 2 scheduler
        * 1 poller
        * 1 receiver
        * 1 reactionner
        * 1 broker

        :return: None
        """
        self.setup_with_file('cfg/cfg_dispatcher_simple_multi_schedulers.cfg')
        assert 1 == len(self.arbiter.dispatcher.realms)
        for realm in self.arbiter.dispatcher.realms:
            assert 2 == len(realm.confs)
            for cfg in realm.confs.values():
                assert cfg.is_assigned
        assert 2 == len(self.arbiter.dispatcher.schedulers)
        assert 4 == len(self.arbiter.dispatcher.satellites)
        # for satellite in self.arbiter.dispatcher.satellites:
        #     self.assertNotEqual({}, satellite.cfg['schedulers'], satellite.get_name())
        #     self.assertEqual(2, len(satellite.cfg['schedulers']),
        #                      'must have 2 schedulers in {0}'.format(satellite.get_name()))

        assert 3 == len(self.schedulers['scheduler-master'].sched.hosts)
        assert 3 == len(self.schedulers['scheduler-master2'].sched.hosts)

    def test_simple_multi_pollers(self):
        """ Simple test (one realm) but with multiple pollers:
        * 1 scheduler
        * 2 poller
        * 1 receiver
        * 1 reactionner
        * 1 broker

        :return: None
        """
        self.setup_with_file('cfg/cfg_dispatcher_simple_multi_pollers.cfg')
        assert 1 == len(self.arbiter.dispatcher.realms)
        for realm in self.arbiter.dispatcher.realms:
            assert 1 == len(realm.confs)
            for cfg in realm.confs.values():
                assert cfg.is_assigned
        assert 1 == len(self.arbiter.dispatcher.schedulers)
        assert 5 == len(self.arbiter.dispatcher.satellites)
        for satellite in self.arbiter.dispatcher.satellites:
            assert {} != satellite.cfg['schedulers'], satellite.get_name()
            assert 1 == len(satellite.cfg['schedulers']), \
                             'must have 1 scheduler in {0}'.format(satellite.get_name())

    def test_realms(self):
        """ Test with 2 realms.
        realm 1:
        * 1 scheduler
        * 1 poller
        * 1 receiver
        * 1 reactionner
        * 1 broker

        realm 2:
        * 1 scheduler
        * 1 poller
        * 1 receiver
        * 1 reactionner
        * 1 broker

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dispatcher_realm.cfg')
        assert 2 == len(self.arbiter.dispatcher.realms)
        for realm in self.arbiter.dispatcher.realms:
            assert 1 == len(realm.confs)
            for cfg in realm.confs.values():
                assert cfg.is_assigned
        assert 2 == len(self.arbiter.dispatcher.schedulers)
        assert 8 == len(self.arbiter.dispatcher.satellites)

        assert set([4, 6]) == set([len(self.schedulers['scheduler-master'].sched.hosts),
                                              len(self.schedulers['realm2scheduler-master'].sched.hosts)])

        # for satellite in self.arbiter.dispatcher.satellites:
        #     self.assertNotEqual({}, satellite.cfg['schedulers'], satellite.get_name())
        #     self.assertEqual(1, len(satellite.cfg['schedulers']),
        #                      'must have 1 scheduler in {0}'.format(satellite.get_name()))

    def test_realms_with_sub(self):
        """ Test with 2 realms but some satellites are sub_realms:
            * All -> realm2
            * realm3

        realm All:
        * 1 scheduler
        * 1 receiver

        realm realm2:
        * 1 receiver
        * 1 scheduler
        * 1 poller

        realm All + realm2 (sub realm):
        * 1 broker
        * 1 poller
        * 1 reactionner

        realm realm3:
        * 1 receiver
        * 1 scheduler
        * 1 reactionner
        * 1 broker
        * 1 poller

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dispatcher_realm_with_sub.cfg')
        # Got 3 realms
        assert 3 == len(self.arbiter.dispatcher.realms)
        for realm in self.arbiter.dispatcher.realms:
            assert 1 == len(realm.confs)
            for cfg in realm.confs.values():
                assert cfg.is_assigned
        # 3 schedulers
        assert 3 == len(self.arbiter.dispatcher.schedulers)
        for satellite in self.arbiter.dispatcher.satellites:
            print("Satellite: %s" % (satellite))
        # 2 reactionners
        # 3 pollers
        # 3 receivers
        # 2 brokers
        assert 10 == len(self.arbiter.dispatcher.satellites), self.arbiter.dispatcher.satellites

        for satellite in self.arbiter.dispatcher.satellites:
            print("Satellite: %s, schedulers: %s" % (satellite, satellite.cfg['schedulers']))
            if satellite.get_name() in ['poller-master', 'reactionner-master', 'broker-master']:
                assert {} != satellite.cfg['schedulers'], satellite.get_name()
                assert 2 == len(satellite.cfg['schedulers']), \
                                 'must have 2 schedulers in {0}'.format(satellite.get_name())
            elif satellite.get_name() in ['realm3-poller-master', 'realm3-reactionner-master',
                                          'realm3-broker-master']:
                assert {} != satellite.cfg['schedulers'], satellite.get_name()
                assert 1 == len(satellite.cfg['schedulers']), \
                                 'must have 1 scheduler in {0}'.format(satellite.get_name())

    def test_realms_with_sub_multi_scheduler(self):
        """ Test with 3 realms but some satellites are sub_realms + multi schedulers
        realm All
           |----- realm All1
                     |----- realm All1a

        realm All:
        * 2 scheduler

        realm All1:
        * 3 scheduler

        realm All1a:
        * 2 scheduler

        realm All + sub_realm:
        * 1 poller
        * 1 reactionner
        * 1 broker
        * 1 receiver

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_dispatcher_realm_with_sub_multi_schedulers.cfg')
        self.show_logs()
        assert self.conf_is_correct

        for poller in self.pollers:
            print(poller)
        pollers = [self.pollers['poller-master'].uuid]
        reactionners = [self.reactionners['reactionner-master'].uuid]

        all_schedulers_uuid = []
        # test schedulers
        for name in ['scheduler-all-01', 'scheduler-all-02', 'scheduler-all1-01',
                     'scheduler-all1-02', 'scheduler-all1-03', 'scheduler-all1a-01',
                     'scheduler-all1a-02']:
            assert self.schedulers[name].sched.pollers.keys() == pollers
            assert self.schedulers[name].sched.reactionners.keys() == reactionners
            assert self.schedulers[name].sched.brokers.keys() == ['broker-master']
            all_schedulers_uuid.extend(self.schedulers[name].schedulers.keys())

        # schedulers of realm All
        gethosts = []
        assert len(self.schedulers['scheduler-all-01'].sched.hosts) == 3
        assert len(self.schedulers['scheduler-all-02'].sched.hosts) == 3
        for h in self.schedulers['scheduler-all-01'].sched.hosts:
            gethosts.append(h.host_name)
        for h in self.schedulers['scheduler-all-02'].sched.hosts:
            gethosts.append(h.host_name)
        assert set(gethosts) == set(['srv_001', 'srv_002', 'srv_003', 'srv_004', 'test_router_0', 'test_host_0'])

        # schedulers of realm All1
        gethosts = []
        assert len(self.schedulers['scheduler-all1-01'].sched.hosts) == 2
        assert len(self.schedulers['scheduler-all1-02'].sched.hosts) == 2
        assert len(self.schedulers['scheduler-all1-03'].sched.hosts) == 2
        for h in self.schedulers['scheduler-all1-01'].sched.hosts:
            gethosts.append(h.host_name)
        for h in self.schedulers['scheduler-all1-02'].sched.hosts:
            gethosts.append(h.host_name)
        for h in self.schedulers['scheduler-all1-03'].sched.hosts:
            gethosts.append(h.host_name)
        assert set(gethosts) == set(['srv_101', 'srv_102', 'srv_103', 'srv_104', 'srv_105', 'srv_106'])

        # schedulers of realm All1a
        gethosts = []
        assert len(self.schedulers['scheduler-all1a-01'].sched.hosts) == 2
        assert len(self.schedulers['scheduler-all1a-02'].sched.hosts) == 2
        for h in self.schedulers['scheduler-all1a-01'].sched.hosts:
            gethosts.append(h.host_name)
        for h in self.schedulers['scheduler-all1a-02'].sched.hosts:
            gethosts.append(h.host_name)
        assert set(gethosts) == set(['srv_201', 'srv_202', 'srv_203', 'srv_204'])

        # test the poller
        assert set(self.pollers['poller-master'].cfg['schedulers'].keys()) == set(all_schedulers_uuid)

        # test the receiver has all hosts of all realms (the 3 realms)
        assert set(self.receivers['receiver-master'].cfg['schedulers'].keys()) == set(all_schedulers_uuid)
        # test get all hosts
        hosts = []
        for sched in self.receivers['receiver-master'].cfg['schedulers'].values():
            hosts.extend(sched['hosts'])
        assert set(hosts) == set(['srv_001', 'srv_002', 'srv_003', 'srv_004', 'srv_101', 'srv_102',
                                 'srv_103', 'srv_104', 'srv_105', 'srv_106', 'srv_201', 'srv_202',
                                 'srv_203', 'srv_204', 'test_router_0', 'test_host_0'])

    def test_simple_scheduler_spare(self):
        """ Test simple but with spare of scheduler

        :return: None
        """
        self.print_header()
        with requests_mock.mock() as mockreq:
            for port in ['7768', '7772', '7771', '7769', '7773', '8002']:
                mockreq.get('http://localhost:%s/ping' % port, json='pong')

            self.setup_with_file('cfg/cfg_dispatcher_scheduler_spare.cfg')
            json_managed = {self.schedulers['scheduler-master'].conf.uuid:
                            self.schedulers['scheduler-master'].conf.push_flavor}
            for port in ['7768', '7772', '7771', '7769', '7773']:
                mockreq.get('http://localhost:%s/what_i_managed' % port, json=json_managed)
            mockreq.get('http://localhost:8002/what_i_managed', json='{}')

            self.arbiter.dispatcher.check_alive()
            self.arbiter.dispatcher.prepare_dispatch()
            self.arbiter.dispatcher.dispatch_ok = True

            assert 2 == len(self.arbiter.dispatcher.schedulers)
            assert 4 == len(self.arbiter.dispatcher.satellites)
            master_sched = None
            spare_sched = None
            for scheduler in self.arbiter.dispatcher.schedulers:
                if scheduler.get_name() == 'scheduler-master':
                    scheduler.is_sent = True
                    master_sched = scheduler
                else:
                    spare_sched = scheduler

            assert master_sched.ping
            assert 0 == master_sched.attempt
            assert spare_sched.ping
            assert 0 == spare_sched.attempt

        for satellite in self.arbiter.dispatcher.satellites:
            assert 1 == len(satellite.cfg['schedulers'])
            scheduler = satellite.cfg['schedulers'].itervalues().next()
            assert 'scheduler-master' == scheduler['name']

        # now simulate master sched down
        master_sched.check_interval = 1
        spare_sched.check_interval = 1
        for satellite in self.arbiter.dispatcher.receivers:
            satellite.check_interval = 1
        for satellite in self.arbiter.dispatcher.reactionners:
            satellite.check_interval = 1
        for satellite in self.arbiter.dispatcher.brokers:
            satellite.check_interval = 1
        for satellite in self.arbiter.dispatcher.pollers:
            satellite.check_interval = 1
        time.sleep(1)

        with requests_mock.mock() as mockreq:
            for port in ['7772', '7771', '7769', '7773', '8002']:
                mockreq.get('http://localhost:%s/ping' % port, json='pong')

            for port in ['7772', '7771', '7769', '7773']:
                mockreq.get('http://localhost:%s/what_i_managed' % port, json=json_managed)
            mockreq.get('http://localhost:8002/what_i_managed', json='{}')

            for port in ['7772', '7771', '7769', '7773', '8002']:
                mockreq.post('http://localhost:%s/put_conf' % port, json='true')

            self.arbiter.dispatcher.check_alive()
            self.arbiter.dispatcher.check_dispatch()
            self.arbiter.dispatcher.prepare_dispatch()
            self.arbiter.dispatcher.dispatch()
            self.arbiter.dispatcher.check_bad_dispatch()

            assert master_sched.ping
            assert 1 == master_sched.attempt

            time.sleep(1)
            self.arbiter.dispatcher.check_alive()
            self.arbiter.dispatcher.check_dispatch()
            self.arbiter.dispatcher.prepare_dispatch()
            self.arbiter.dispatcher.dispatch()
            self.arbiter.dispatcher.check_bad_dispatch()

            assert master_sched.ping
            assert 2 == master_sched.attempt
            assert master_sched.alive

            time.sleep(1)
            self.arbiter.dispatcher.check_alive()
            self.arbiter.dispatcher.check_dispatch()
            self.arbiter.dispatcher.prepare_dispatch()
            self.arbiter.dispatcher.dispatch()
            self.arbiter.dispatcher.check_bad_dispatch()

            assert not master_sched.alive

            history = mockreq.request_history
            send_conf_to_sched_master = False
            conf_sent = {}
            for index, hist in enumerate(history):
                if hist.url == 'http://localhost:7768/put_conf':
                    send_conf_to_sched_master = True
                elif hist.url == 'http://localhost:8002/put_conf':
                    conf_sent['scheduler-spare'] = hist.json()
                elif hist.url == 'http://localhost:7772/put_conf':
                    conf_sent['broker'] = hist.json()
                elif hist.url == 'http://localhost:7771/put_conf':
                    conf_sent['poller'] = hist.json()
                elif hist.url == 'http://localhost:7769/put_conf':
                    conf_sent['reactionner'] = hist.json()
                elif hist.url == 'http://localhost:7773/put_conf':
                    conf_sent['receiver'] = hist.json()

            assert not send_conf_to_sched_master, 'Conf to scheduler master must not be sent' \
                                                        'because it not alive'
            assert 5 == len(conf_sent)
            assert ['conf'] == conf_sent['scheduler-spare'].keys()

            json_managed_spare = {}
            for satellite in self.arbiter.dispatcher.satellites:
                assert 1 == len(satellite.cfg['schedulers'])
                scheduler = satellite.cfg['schedulers'].itervalues().next()
                assert 'scheduler-spare' == scheduler['name']
                json_managed_spare[scheduler['instance_id']] = scheduler['push_flavor']

        # return of the scheduler master
        print "*********** Return of the king / master ***********"
        with requests_mock.mock() as mockreq:
            for port in ['7768', '7772', '7771', '7769', '7773', '8002']:
                mockreq.get('http://localhost:%s/ping' % port, json='pong')

            mockreq.get('http://localhost:7768/what_i_managed', json=json_managed)
            for port in ['7772', '7771', '7769', '7773', '8002']:
                mockreq.get('http://localhost:%s/what_i_managed' % port, json=json_managed_spare)

            for port in ['7768', '7772', '7771', '7769', '7773', '8002']:
                mockreq.post('http://localhost:%s/put_conf' % port, json='true')

            time.sleep(1)
            self.arbiter.dispatcher.check_alive()
            self.arbiter.dispatcher.check_dispatch()
            self.arbiter.dispatcher.prepare_dispatch()
            self.arbiter.dispatcher.dispatch()
            self.arbiter.dispatcher.check_bad_dispatch()

            assert master_sched.ping
            assert 0 == master_sched.attempt

            history = mockreq.request_history
            conf_sent = {}
            for index, hist in enumerate(history):
                if hist.url == 'http://localhost:7768/put_conf':
                    conf_sent['scheduler-master'] = hist.json()
                elif hist.url == 'http://localhost:8002/put_conf':
                    conf_sent['scheduler-spare'] = hist.json()
                elif hist.url == 'http://localhost:7772/put_conf':
                    conf_sent['broker'] = hist.json()
                elif hist.url == 'http://localhost:7771/put_conf':
                    conf_sent['poller'] = hist.json()
                elif hist.url == 'http://localhost:7769/put_conf':
                    conf_sent['reactionner'] = hist.json()
                elif hist.url == 'http://localhost:7773/put_conf':
                    conf_sent['receiver'] = hist.json()

            assert set(['scheduler-master', 'broker', 'poller', 'reactionner',
                                  'receiver']) == \
                             set(conf_sent.keys())

            for satellite in self.arbiter.dispatcher.satellites:
                assert 1 == len(satellite.cfg['schedulers'])
                scheduler = satellite.cfg['schedulers'].itervalues().next()
                assert 'scheduler-master' == scheduler['name']

    def test_arbiter_spare(self):
        """ Test with arbiter spare

        :return: None
        """
        self.print_header()
        with requests_mock.mock() as mockreq:
            mockreq.get('http://localhost:8770/ping', json='pong')
            mockreq.get('http://localhost:8770/what_i_managed', json='{}')
            mockreq.post('http://localhost:8770/put_conf', json='true')
            self.setup_with_file('cfg/cfg_dispatcher_arbiter_spare.cfg')
            self.arbiter.dispatcher.check_alive()
            for arb in self.arbiter.dispatcher.arbiters:
                # If not me and I'm a master
                if arb != self.arbiter.dispatcher.arbiter:
                    assert 0 == arb.attempt
                    assert {} == arb.managed_confs

            self.arbiter.dispatcher.check_dispatch()
            # need time to have history filled
            time.sleep(2)
            history = mockreq.request_history
            history_index = 0
            for index, hist in enumerate(history):
                if hist.url == 'http://localhost:8770/put_conf':
                    history_index = index
            conf_received = history[history_index].json()
            assert ['conf'] == conf_received.keys()
            spare_conf = unserialize(conf_received['conf'])
            # Test a property to be sure conf loaded correctly
            assert 5 == spare_conf.perfdata_timeout
