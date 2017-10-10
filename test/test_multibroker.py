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

"""
This file test the multibroker in schedulers
"""

import requests_mock
from alignak.http.scheduler_interface import SchedulerInterface
from alignak_test import AlignakTest


class TestMultibroker(AlignakTest):
    """
    This class test the multibroker in schedulers
    """
    def test_multibroker_onesched(self):
        """ Test with 2 brokers and 1 scheduler

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_multi_broker_one_scheduler.cfg')

        mysched = self._scheduler_daemon

        assert 2 == len(mysched.sched.brokers)

        # create broks
        host = mysched.sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = mysched.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        assert 2 == len(mysched.sched.brokers)
        bmaster = len(mysched.sched.brokers['broker-master']['broks'])
        bmaster2 = len(mysched.sched.brokers['broker-master2']['broks'])

        sched_interface = SchedulerInterface(mysched)
        # Test broker-master connect to scheduler
        res = sched_interface.get_broks('broker-master')
        assert (bmaster + 2) > len(mysched.sched.brokers['broker-master']['broks'])
        assert 0 == len(mysched.sched.brokers['broker-master']['broks'])

        # Test broker-master2 connect to scheduler
        res = sched_interface.get_broks('broker-master2')
        assert (bmaster2 + 2) > len(mysched.sched.brokers['broker-master2']['broks'])
        assert 0 == len(mysched.sched.brokers['broker-master2']['broks'])

        # Test broker-master3 connect to scheduler (broker unknown)
        res = sched_interface.get_broks('broker-master3')
        assert {} == res
        assert 2 == len(mysched.sched.brokers)

        # Re-get broks
        res = sched_interface.get_broks('broker-master')
        res = sched_interface.get_broks('broker-master2')

        # new broks
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        assert len(mysched.sched.brokers['broker-master']['broks']) > 1
        self.assertItemsEqual(mysched.sched.brokers['broker-master']['broks'].keys(),
                              mysched.sched.brokers['broker-master2']['broks'].keys())

    def test_multibroker_multisched(self):
        """ Test with 2 brokers and 2 schedulers

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_multi_broker_multi_scheduler.cfg')

        assert 2 == len(self.schedulers)
        mysched1 = self._scheduler_daemon
        mysched2 = self.schedulers['scheduler-master2']
        print(self.schedulers)

        if len(self._scheduler.hosts) == 2:
            mysched1 = self._scheduler_daemon
            mysched2 = self.schedulers['scheduler-master2']
        else:
            mysched2 = self._scheduler_daemon
            mysched1 = self.schedulers['scheduler-master2']

        host1 = mysched1.sched.hosts.find_by_name("test_host_0")
        host1.checks_in_progress = []
        host1.act_depend_of = []  # ignore the router

        svc1 = mysched1.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc1.checks_in_progress = []
        svc1.act_depend_of = []  # no hostchecks on critical checkresults

        host2 = mysched2.sched.hosts.find_by_name("test_host_1")
        host2.checks_in_progress = []

        # create broks in each scheduler
        self.scheduler_loop(1, [[host1, 0, 'UP'], [svc1, 0, 'OK']], mysched1.sched)
        self.scheduler_loop(1, [[host2, 0, 'UP']], mysched2.sched)

        assert 2 == len(mysched1.sched.brokers)
        assert 2 == len(mysched2.sched.brokers)

        sched1bmaster = len(mysched1.sched.brokers['broker-master']['broks'])
        sched1bmaster2 = len(mysched1.sched.brokers['broker-master2']['broks'])

        sched2bmaster = len(mysched1.sched.brokers['broker-master']['broks'])
        sched2bmaster2 = len(mysched1.sched.brokers['broker-master2']['broks'])

        assert sched1bmaster > 2
        assert sched2bmaster > 2

        assert sched1bmaster == sched1bmaster2
        assert sched2bmaster == sched2bmaster2

        # check dispatcher send right info to brokers
        with requests_mock.mock() as mockreq:
            for port in ['7772', '10772']:
                mockreq.post('http://localhost:%s/put_conf' % port, json='true')

            self.arbiter.dispatcher.dispatch()
            self.assert_any_log_match('Configuration sent to broker broker-master')
            self.assert_any_log_match('Configuration sent to broker broker-master2')

            history = mockreq.request_history
            print("History: %s" % history)
            for index, hist in enumerate(history):
                print("- : %s" % (hist.url))
                if hist.url == 'http://127.0.0.1:7772/put_conf':
                    broker_conf = hist.json()
                elif hist.url == 'http://localhost:10772/put_conf':
                    broker2_conf = hist.json()

            assert 2 == len(broker_conf['conf']['schedulers'])
            assert 2 == len(broker2_conf['conf']['schedulers'])

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
        self.print_header()
        self.setup_with_file('cfg/cfg_multi_broker_multi_sched_realms.cfg')

        # test right brokers sent to right schedulers
        smaster = self._scheduler_daemon
        smaster_n = self.schedulers['scheduler-masterN']
        smaster_s = self.schedulers['scheduler-masterS']

        assert smaster.sched.brokers.keys() == ['broker-master']
        self.assertItemsEqual(smaster_n.sched.brokers.keys(), ['broker-master', 'broker-masterN'])
        assert smaster_s.sched.brokers.keys() == ['broker-master']

        brokermaster = None
        for sat in self.arbiter.dispatcher.satellites:
            if getattr(sat, 'broker_name', '') == 'broker-master':
                brokermaster = sat

        assert brokermaster is not None
        self.assertItemsEqual([smaster.sched.conf.uuid, smaster_n.sched.conf.uuid,
                               smaster_s.sched.conf.uuid], brokermaster.cfg['schedulers'])

        pass