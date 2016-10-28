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
        self.setup_with_file('cfg/cfg_dispatcher_simple.cfg')
        self.assertEqual(1, len(self.arbiter.dispatcher.realms))
        for realm in self.arbiter.dispatcher.realms:
            self.assertEqual(1, len(realm.confs))
            for cfg in realm.confs.values():
                self.assertTrue(cfg.is_assigned)
        self.assertEqual(1, len(self.arbiter.dispatcher.schedulers))
        self.assertEqual(4, len(self.arbiter.dispatcher.satellites))
        for satellite in self.arbiter.dispatcher.satellites:
            self.assertNotEqual({}, satellite.cfg['schedulers'], satellite.get_name())
            self.assertEqual(1, len(satellite.cfg['schedulers']), 'must have 1 scheduler')

        # check if scheduler has right the 6 hosts
        self.assertEqual(6, len(self.schedulers['scheduler-master'].sched.hosts))

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
        self.assertEqual(1, len(self.arbiter.dispatcher.realms))
        for realm in self.arbiter.dispatcher.realms:
            self.assertEqual(2, len(realm.confs))
            for cfg in realm.confs.values():
                self.assertTrue(cfg.is_assigned)
        self.assertEqual(2, len(self.arbiter.dispatcher.schedulers))
        self.assertEqual(4, len(self.arbiter.dispatcher.satellites))
        # for satellite in self.arbiter.dispatcher.satellites:
        #     self.assertNotEqual({}, satellite.cfg['schedulers'], satellite.get_name())
        #     self.assertEqual(2, len(satellite.cfg['schedulers']),
        #                      'must have 2 schedulers in {0}'.format(satellite.get_name()))

        self.assertEqual(3, len(self.schedulers['scheduler-master'].sched.hosts))
        self.assertEqual(3, len(self.schedulers['scheduler-master2'].sched.hosts))

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
        self.assertEqual(1, len(self.arbiter.dispatcher.realms))
        for realm in self.arbiter.dispatcher.realms:
            self.assertEqual(1, len(realm.confs))
            for cfg in realm.confs.values():
                self.assertTrue(cfg.is_assigned)
        self.assertEqual(1, len(self.arbiter.dispatcher.schedulers))
        self.assertEqual(5, len(self.arbiter.dispatcher.satellites))
        for satellite in self.arbiter.dispatcher.satellites:
            self.assertNotEqual({}, satellite.cfg['schedulers'], satellite.get_name())
            self.assertEqual(1, len(satellite.cfg['schedulers']),
                             'must have 1 scheduler in {0}'.format(satellite.get_name()))

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
        self.setup_with_file('cfg/cfg_dispatcher_realm.cfg')
        self.assertEqual(2, len(self.arbiter.dispatcher.realms))
        for realm in self.arbiter.dispatcher.realms:
            self.assertEqual(1, len(realm.confs))
            for cfg in realm.confs.values():
                self.assertTrue(cfg.is_assigned)
        self.assertEqual(2, len(self.arbiter.dispatcher.schedulers))
        self.assertEqual(8, len(self.arbiter.dispatcher.satellites))

        self.assertSetEqual(set([4, 6]), set([len(self.schedulers['scheduler-master'].sched.hosts),
                                              len(self.schedulers['realm2scheduler-master'].sched.hosts)]))

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
        self.setup_with_file('cfg/cfg_dispatcher_realm_with_sub.cfg')
        self.assertEqual(3, len(self.arbiter.dispatcher.realms))
        for realm in self.arbiter.dispatcher.realms:
            self.assertEqual(1, len(realm.confs))
            for cfg in realm.confs.values():
                self.assertTrue(cfg.is_assigned)
        self.assertEqual(3, len(self.arbiter.dispatcher.schedulers))
        self.assertEqual(10, len(self.arbiter.dispatcher.satellites),
                         self.arbiter.dispatcher.satellites)

        for satellite in self.arbiter.dispatcher.satellites:
            if satellite.get_name() in ['poller-master', 'reactionner-master', 'broker-master']:
                self.assertNotEqual({}, satellite.cfg['schedulers'], satellite.get_name())
                self.assertEqual(2, len(satellite.cfg['schedulers']),
                                 'must have 2 schedulers in {0}'.format(satellite.get_name()))
            elif satellite.get_name() in ['realm3-poller-master', 'realm3-reactionner-master',
                                          'realm3-broker-master']:
                self.assertNotEqual({}, satellite.cfg['schedulers'], satellite.get_name())
                self.assertEqual(1, len(satellite.cfg['schedulers']),
                                 'must have 1 scheduler in {0}'.format(satellite.get_name()))

    def test_realms_with_sub_multi_scheduler(self):
        """ Test with 2 realms but some satellites are sub_realms + multi schedulers
        realm 1:
        * 2 scheduler
        * 1 receiver

        realm 2:
        * 3 scheduler
        * 1 receiver

        realm 1 + sub_realm:
        * 1 poller
        * 1 reactionner
        * 1 broker

        :return: None
        """
        pass

    def test_simple_scheduler_spare(self):
        """ Test simple but with spare of scheduler

        :return: None
        """
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

            self.assertEqual(2, len(self.arbiter.dispatcher.schedulers))
            self.assertEqual(4, len(self.arbiter.dispatcher.satellites))
            master_sched = None
            spare_sched = None
            for scheduler in self.arbiter.dispatcher.schedulers:
                if scheduler.get_name() == 'scheduler-master':
                    scheduler.is_sent = True
                    master_sched = scheduler
                else:
                    spare_sched = scheduler

            self.assertTrue(master_sched.ping)
            self.assertEqual(0, master_sched.attempt)
            self.assertTrue(spare_sched.ping)
            self.assertEqual(0, spare_sched.attempt)

        for satellite in self.arbiter.dispatcher.satellites:
            self.assertEqual(1, len(satellite.cfg['schedulers']))
            scheduler = satellite.cfg['schedulers'].itervalues().next()
            self.assertEqual('scheduler-master', scheduler['name'])

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

            self.assertTrue(master_sched.ping)
            self.assertEqual(1, master_sched.attempt)

            time.sleep(1)
            self.arbiter.dispatcher.check_alive()
            self.arbiter.dispatcher.check_dispatch()
            self.arbiter.dispatcher.prepare_dispatch()
            self.arbiter.dispatcher.dispatch()
            self.arbiter.dispatcher.check_bad_dispatch()

            self.assertTrue(master_sched.ping)
            self.assertEqual(2, master_sched.attempt)
            self.assertTrue(master_sched.alive)

            time.sleep(1)
            self.arbiter.dispatcher.check_alive()
            self.arbiter.dispatcher.check_dispatch()
            self.arbiter.dispatcher.prepare_dispatch()
            self.arbiter.dispatcher.dispatch()
            self.arbiter.dispatcher.check_bad_dispatch()

            self.assertFalse(master_sched.alive)

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

            self.assertFalse(send_conf_to_sched_master, 'Conf to scheduler master must not be sent'
                                                        'because it not alive')
            self.assertEqual(5, len(conf_sent))
            self.assertListEqual(['conf'], conf_sent['scheduler-spare'].keys())

            json_managed_spare = {}
            for satellite in self.arbiter.dispatcher.satellites:
                self.assertEqual(1, len(satellite.cfg['schedulers']))
                scheduler = satellite.cfg['schedulers'].itervalues().next()
                self.assertEqual('scheduler-spare', scheduler['name'])
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

            self.assertTrue(master_sched.ping)
            self.assertEqual(0, master_sched.attempt)

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

            self.assertEqual(set(['scheduler-master', 'broker', 'poller', 'reactionner',
                                  'receiver']),
                             set(conf_sent.keys()))

            for satellite in self.arbiter.dispatcher.satellites:
                self.assertEqual(1, len(satellite.cfg['schedulers']))
                scheduler = satellite.cfg['schedulers'].itervalues().next()
                self.assertEqual('scheduler-master', scheduler['name'])

    def test_arbiter_spare(self):
        """ Test with arbiter spare

        :return: None
        """
        with requests_mock.mock() as mockreq:
            mockreq.get('http://localhost:8770/ping', json='pong')
            mockreq.get('http://localhost:8770/what_i_managed', json='{}')
            mockreq.post('http://localhost:8770/put_conf', json='true')
            self.setup_with_file('cfg/cfg_dispatcher_arbiter_spare.cfg')
            self.arbiter.dispatcher.check_alive()
            for arb in self.arbiter.dispatcher.arbiters:
                # If not me and I'm a master
                if arb != self.arbiter.dispatcher.arbiter:
                    self.assertEqual(0, arb.attempt)
                    self.assertEqual({}, arb.managed_confs)

            self.arbiter.dispatcher.check_dispatch()
            # need time to have history filled
            time.sleep(2)
            history = mockreq.request_history
            history_index = 0
            for index, hist in enumerate(history):
                if hist.url == 'http://localhost:8770/put_conf':
                    history_index = index
            conf_received = history[history_index].json()
            self.assertListEqual(['conf'], conf_received.keys())
            spare_conf = unserialize(conf_received['conf'])
            # Test a property to be sure conf loaded correctly
            self.assertEqual(5, spare_conf.perfdata_timeout)
