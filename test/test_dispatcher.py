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
"""
This file tests the dispatcher (distribute configuration to satellites)
"""

import os
import re
import time
import datetime
import pytest
import logging
import requests_mock
from freezegun import freeze_time
from alignak_test import AlignakTest
from alignak.log import ALIGNAK_LOGGER_NAME
from alignak.misc.serialization import unserialize
from alignak.daemons.arbiterdaemon import Arbiter
from alignak.dispatcher import Dispatcher, DispatcherError


class TestDispatcher(AlignakTest):
    """
    This class tests the dispatcher (distribute configuration to satellites)
    """
    def setUp(self):
        """Test starting"""
        super(TestDispatcher, self).setUp()

        # Log at DEBUG level
        self.set_debug_log()

    def _dispatching(self, env_filename='cfg/dispatcher/simple.ini', loops=3, multi_realms=False):
        """ Dispatching process: prepare, check, dispatch

        This function realize all the dispatching operations:
        - load a monitoring configuration
        - prepare the dispatching
        - dispatch
        - check the correct dispatching, including:
            - check the configuration dispatched to the schedulers
            - check the configuration dispatched to the spare arbiter (if any)
        - run the check_reachable loop several times

        if multi_realms is True, the scheduler configuration received are not checked against
        the arbiter whole configuration. This would be really too complex to assert on this :(

        Schedulers must have a port number with 7768 (eg. 7768,17768,27768,...)

        Spare daemons must have a port number with 8770 (eg. 8770,18770,28770,...)

        :return: None
        """
        args = {
            'env_file': env_filename, 'alignak_name': 'alignak-test', 'daemon_name': 'arbiter-master'
        }
        my_arbiter = Arbiter(**args)
        my_arbiter.setup_alignak_logger()

        # Clear logs
        self.clear_logs()

        my_arbiter.load_modules_manager()
        my_arbiter.load_monitoring_config_file()
        assert my_arbiter.conf.conf_is_correct is True
        # logging.getLogger('alignak').setLevel(logging.DEBUG)

        objects_map = {}
        for _, _, strclss, _, _ in my_arbiter.conf.types_creations.values():
            if strclss in ['hostescalations', 'serviceescalations']:
                continue

            objects_list = getattr(my_arbiter.conf, strclss, [])
            objects_map[strclss] = {'count': len(objects_list), 'str': str(objects_list)}
            # print("Got %d %s: %s" % (len(objects_list), strclss, objects_list))

        # Freeze the time !
        initial_datetime = datetime.datetime.now()
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime

            # #1 - Get a new dispatcher
            my_dispatcher = Dispatcher(my_arbiter.conf, my_arbiter.link_to_myself)
            print("*** All daemons WS: %s"
                  % ["%s:%s" % (link.address, link.port)
                     for link in my_dispatcher.all_daemons_links])

            assert my_dispatcher.dispatch_ok is False
            assert my_dispatcher.new_to_dispatch is False
            assert my_dispatcher.first_dispatch_done is False

            self.assert_any_log_match(re.escape("Dispatcher arbiters/satellites map:"))
            for link in my_dispatcher.all_daemons_links:
                self.assert_any_log_match(re.escape(" - %s: %s" % (link.name, link.uri)))

            # Simulate the daemons HTTP interface (very simple simulation !)
            with requests_mock.mock() as mr:
                for link in my_dispatcher.all_daemons_links:
                    mr.get('http://%s:%s/ping' % (link.address, link.port),
                           json='pong')
                    mr.get('http://%s:%s/get_running_id' % (link.address, link.port),
                           json=123456.123456)
                    mr.get('http://%s:%s/wait_new_conf' % (link.address, link.port),
                           json=True)
                    mr.get('http://%s:%s/fill_initial_broks' % (link.address, link.port),
                           json=[])
                    mr.post('http://%s:%s/push_configuration' % (link.address, link.port),
                            json=True)
                    mr.get('http://%s:%s/get_managed_configurations' % (link.address, link.port),
                           json=link.cfg_managed)
                    mr.get('http://%s:%s/do_not_run' % (link.address, link.port),
                           json=True)

                for link in my_dispatcher.all_daemons_links:
                    # print("Satellite: %s / %s" % (link, link.cfg_to_manage))
                    assert not link.hash
                    assert not link.push_flavor
                    assert not link.cfg_to_manage
                    assert not link.cfg_managed

                # #2 - Initialize connection with all our satellites
                for satellite in my_dispatcher.all_daemons_links:
                    assert my_arbiter.daemon_connection_init(satellite)
                # All links have a running identifier
                for link in my_dispatcher.all_daemons_links:
                    if link == my_dispatcher.arbiter_link:
                        continue
                    assert link.running_id == 123456.123456
                    self.assert_any_log_match(re.escape(
                        "got the running identifier for %s %s" % (link.type, link.name)
                    ))

                # #3 - Check reachable - a configuration is not yet prepared,
                # so only check reachable state
                my_dispatcher.check_reachable()
                assert my_dispatcher.dispatch_ok is False
                assert my_dispatcher.first_dispatch_done is False
                assert my_dispatcher.new_to_dispatch is False
                # Not yet configured ...
                for link in my_dispatcher.all_daemons_links:
                    if link == my_dispatcher.arbiter_link:
                        continue
                    self.assert_any_log_match(re.escape(
                        "The %s %s do not have a configuration" % (link.type, link.name)
                    ))

                # #3 - Check reachable - daemons got pinged too early...
                my_dispatcher.check_reachable()
                assert my_dispatcher.dispatch_ok is False
                assert my_dispatcher.first_dispatch_done is False
                assert my_dispatcher.new_to_dispatch is False
                # Only for Python > 2.7, DEBUG logs ...
                if os.sys.version_info > (2, 7):
                    for link in my_dispatcher.all_daemons_links:
                        if link == my_dispatcher.arbiter_link:
                            continue
                        self.assert_any_log_match(re.escape(
                            "Too early to ping %s" % (link.name)
                        ))
                self.assert_no_log_match(re.escape(
                    "Dispatcher, those daemons are not configured: "
                    "reactionner-master,poller-master,broker-master,receiver-master,"
                    "scheduler-master"
                    ", and a configuration is ready to dispatch, run the dispatching..."
                ))

                # Time warp 5 seconds - overpass the ping period...
                self.clear_logs()
                frozen_datetime.tick(delta=datetime.timedelta(seconds=5))

                # #3 - Check reachable - daemons provide their configuration
                my_dispatcher.check_reachable()
                assert my_dispatcher.dispatch_ok is False
                assert my_dispatcher.first_dispatch_done is False
                assert my_dispatcher.new_to_dispatch is False
                # Only for Python > 2.7, DEBUG logs ...
                if os.sys.version_info > (2, 7):
                    # Still not configured ...
                    for link in my_dispatcher.all_daemons_links:
                        if link == my_dispatcher.arbiter_link:
                            continue
                        self.assert_any_log_match(re.escape(
                            "My (%s) fresh managed configuration: {}" % link.name
                        ))

                # #4 - Prepare dispatching
                assert my_dispatcher.new_to_dispatch is False
                my_dispatcher.prepare_dispatch()
                assert my_dispatcher.dispatch_ok is False
                assert my_dispatcher.first_dispatch_done is False
                assert my_dispatcher.new_to_dispatch is True

                self.assert_any_log_match(re.escape(
                    "All configuration parts are assigned to schedulers and their satellites :)"
                ))
                # All links have a hash, push_flavor and cfg_to_manage
                for link in my_dispatcher.all_daemons_links:
                    print("Link: %s" % link)
                    assert getattr(link, 'hash', None) is not None
                    assert getattr(link, 'push_flavor', None) is not None
                    assert getattr(link, 'cfg_to_manage', None) is not None
                    assert not link.cfg_managed  # Not yet

                # #5 - Check reachable - a configuration is prepared,
                # this will force the daemons communication, no need for a time warp ;)
                my_dispatcher.check_reachable()
                # Only for Python > 2.7, DEBUG logs ...
                if os.sys.version_info > (2, 7):
                    for link in my_dispatcher.all_daemons_links:
                        if link == my_dispatcher.arbiter_link:
                            continue
                        self.assert_any_log_match(re.escape(
                            "My (%s) fresh managed configuration: {}" % link.name
                        ))

                self.assert_any_log_match(re.escape(
                    "Dispatcher, those daemons are not configured:"))
                self.assert_any_log_match(re.escape(
                    ", and a configuration is ready to dispatch, run the dispatching..."))

                self.assert_any_log_match(re.escape(
                    "Trying to send configuration to the satellites..."))
                for link in my_dispatcher.all_daemons_links:
                    if link == my_dispatcher.arbiter_link:
                        continue
                    self.assert_any_log_match(re.escape(
                        "Sending configuration to the %s %s" % (link.type, link.name)))
                    self.assert_any_log_match(re.escape(
                        "Configuration sent to the %s %s" % (link.type, link.name)))

                # As of now the configuration is prepared and was dispatched to the daemons !
                # Configuration already dispatched!
                with pytest.raises(DispatcherError):
                    my_dispatcher.dispatch()
                self.show_logs()

                # Hack the requests history to check and simulate  the configuration pushed...
                history = mr.request_history
                for index, request in enumerate(history):
                    if 'push_configuration' in request.url:
                        received = request.json()
                        print(index, request.url, received)
                        assert ['conf'] == received.keys()
                        conf = received['conf']

                        from pprint import pprint
                        pprint(conf)
                        assert 'alignak_name' in conf
                        assert conf['alignak_name'] == 'My Alignak'

                        assert 'self_conf' in conf
                        assert conf['self_conf']
                        i_am = None
                        for link in my_dispatcher.all_daemons_links:
                            if link.type == conf['self_conf']['type'] \
                                    and link.name == conf['self_conf']['name']:
                                i_am = link
                                break
                        else:
                            assert False
                        print("I am: %s" % i_am)
                        print("I have: %s" % conf)

                        # All links have a hash, push_flavor and cfg_to_manage
                        assert 'hash' in conf
                        assert 'managed_conf_id' in conf

                        assert 'arbiters' in conf
                        if conf['self_conf']['manage_arbiters']:
                            # All the known arbiters
                            assert conf['arbiters'].keys() == [arbiter_link.uuid for arbiter_link
                                                               in my_dispatcher.arbiters]
                        else:
                            assert conf['arbiters'] == {}

                        assert 'schedulers' in conf
                        # Hack for the managed configurations
                        link.cfg_managed = {}
                        for scheduler_link in conf['schedulers'].values():
                            link.cfg_managed[scheduler_link['instance_id']] = {
                                'hash': scheduler_link['hash'],
                                'push_flavor': scheduler_link['push_flavor'],
                                'managed_conf_id': scheduler_link['managed_conf_id']
                            }
                        print("Managed: %s" % link.cfg_managed)

                        assert 'modules' in conf
                        assert conf['modules'] == []

                        # Spare arbiter specific
                        if '8770/push_configuration' in request.url:
                            # Spare arbiter receives all the monitored configuration
                            assert 'whole_conf' in conf
                            # String serialized configuration
                            assert isinstance(conf['whole_conf'], basestring)
                            managed_conf_part = unserialize(conf['whole_conf'])
                            # Test a property to be sure conf loaded correctly
                            assert managed_conf_part.instance_id == conf['managed_conf_id']

                            # The spare arbiter got the same objects count as the master arbiter prepared!
                            for _, _, strclss, _, _ in managed_conf_part.types_creations.values():
                                # These elements are not included in the serialized configuration!
                                if strclss in ['hostescalations', 'serviceescalations',
                                               'arbiters', 'schedulers', 'brokers',
                                               'pollers', 'reactionners', 'receivers', 'realms',
                                               'modules', 'hostsextinfo', 'servicesextinfo',
                                               'hostdependencies', 'servicedependencies']:
                                    continue

                                objects_list = getattr(managed_conf_part, strclss, [])
                                # print("Got %d %s: %s" % (len(objects_list), strclss, objects_list))
                                # Count and string dup are the same !
                                assert len(objects_list) == objects_map[strclss]['count']
                                assert str(objects_list) == objects_map[strclss]['str']

                        # Scheduler specific
                        elif '7768/push_configuration' in request.url:
                            assert 'conf_part' in conf
                            # String serialized configuration
                            assert isinstance(conf['conf_part'], basestring)
                            managed_conf_part = unserialize(conf['conf_part'])
                            # Test a property to be sure conf loaded correctly
                            assert managed_conf_part.instance_id == conf['managed_conf_id']

                            # Hack for the managed configurations
                            link.cfg_managed = {
                                conf['instance_id']: {
                                    'hash': conf['hash'],
                                    'push_flavor': conf['push_flavor'],
                                    'managed_conf_id': conf['managed_conf_id']
                                }
                            }
                            print("Managed: %s" % link.cfg_managed)

                            # The scheduler got the same objects count as the arbiter prepared!
                            for _, _, strclss, _, _ in managed_conf_part.types_creations.values():
                                # These elements are not included in the serialized configuration!
                                if strclss in ['hostescalations', 'serviceescalations',
                                               'arbiters', 'schedulers', 'brokers',
                                               'pollers', 'reactionners', 'receivers', 'realms',
                                               'modules', 'hostsextinfo', 'servicesextinfo',
                                               'hostdependencies', 'servicedependencies']:
                                    continue

                                objects_list = getattr(managed_conf_part, strclss, [])
                                # print("Got %d %s: %s" % (len(objects_list), strclss, objects_list))
                                if not multi_realms:
                                    # Count and string dump are the same !
                                    assert len(objects_list) == objects_map[strclss]['count']
                                    assert str(objects_list) == objects_map[strclss]['str']

                        else:
                            # Satellites
                            assert 'conf_part' not in conf
                            assert 'see_my_schedulers' == conf['managed_conf_id']

                for link in my_dispatcher.all_daemons_links:
                    mr.get('http://%s:%s/get_managed_configurations' % (link.address, link.port),
                           json=link.cfg_managed)

                print("Check dispatching")
                self.clear_logs()
                assert my_dispatcher.check_dispatch() is True

                for loop_count in range(0, loops):
                    for tw in range(0, 4):
                        # Time warp 1 second
                        frozen_datetime.tick(delta=datetime.timedelta(seconds=1))

                        print("Check reachable %s" % tw)
                        self.clear_logs()
                        my_dispatcher.check_reachable()
                        # Only for Python > 2.7, DEBUG logs ...
                        if os.sys.version_info > (2, 7):
                            for link in my_dispatcher.all_daemons_links:
                                if link == my_dispatcher.arbiter_link:
                                    continue
                                self.assert_any_log_match(re.escape(
                                    "Too early to ping %s" % (link.name)
                                ))

                    # Time warp 1 second
                    frozen_datetime.tick(delta=datetime.timedelta(seconds=1))

                    print("Check reachable response")
                    self.clear_logs()
                    my_dispatcher.check_reachable()
                    for link in my_dispatcher.all_daemons_links:
                        if link == my_dispatcher.arbiter_link:
                            continue
                        self.assert_any_log_match(re.escape(
                            "My (%s) fresh managed configuration: %s"
                            % (link.name, link.cfg_managed)
                        ))

    def test_bad_init(self):
        """ Test that:
        - bad configuration
        - two master arbiters
        are not correct and raise an exception!

        :return: None
        """
        args = {
            'env_file': 'cfg/dispatcher/two_master_arbiters.ini',
            'alignak_name': 'alignak-test', 'daemon_name': 'arbiter-master'
        }
        self.my_arbiter = Arbiter(**args)

        # Get a new dispatcher - raise an exception
        with pytest.raises(DispatcherError):
            Dispatcher(None, self.my_arbiter.link_to_myself)

        # Get a new dispatcher - raise an exception
        with pytest.raises(DispatcherError):
            Dispatcher(self.my_arbiter.conf, None)

        # Prepare the Alignak configuration
        self.my_arbiter.load_modules_manager()
        self.my_arbiter.load_monitoring_config_file()
        assert self.my_arbiter.conf.conf_is_correct is True

        # Get a new dispatcher - raise an exception (two master arbiters)
        with pytest.raises(DispatcherError):
            Dispatcher(self.my_arbiter.conf, self.my_arbiter.link_to_myself)

    def test_dispatching_simple(self):
        """ Test the dispatching process: simple configuration

        :return: None
        """
        self._dispatching()

    def test_dispatching_multiple_schedulers(self):
        """ Test the dispatching process: 1 realm, 2 schedulers

        :return: None
        """
        self._dispatching('cfg/dispatcher/simple_multi_schedulers.ini', multi_realms=True)

    def test_dispatching_multiple_pollers(self):
        """ Test the dispatching process: 1 realm, 2 pollers

        :return: None
        """
        self._dispatching('cfg/dispatcher/simple_multi_pollers.ini')

    def test_dispatching_multiple_realms(self):
        """ Test the dispatching process: 2 realms, all daemons duplicated

        :return: None
        """
        self._dispatching('cfg/dispatcher/2-realms.ini', multi_realms=True)

    def test_dispatching_multiple_realms_sub_realms(self):
        """ Test the dispatching process: 2 realms, some daemons are sub_realms managers

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
        self._dispatching('cfg/dispatcher/realms_with_sub_realms.ini', multi_realms=True)

    def test_dispatching_multiple_realms_sub_realms_multi_schedulers(self):
        """ Test the dispatching process: 2 realms, some daemons are sub_realms managers and
        we have several schedulers. daemons with (+) are manage_sub_realms=1

        realm All (6 hosts):
        * 2 schedulers (+)

        realm All / All1 (6 hosts):
        * 3 schedulers (+)

        realm All / All1 / All1a (4 hosts):
        * 2 schedulers (+)

        :return: None
        """
        self._dispatching('cfg/dispatcher/realms_with_sub_realms_multi_schedulers.ini',
                          multi_realms=True)

    def test_dispatching_spare_arbiter(self):
        """ Test the dispatching process: 1 realm, 1 spare arbiter

        :return: None
        """
        self._dispatching('cfg/dispatcher/spare_arbiter.ini')

    @pytest.mark.skip("Currently disabled - spare feature - and whatever this test seems broken!")
    def test_simple_scheduler_spare(self):
        """ Test simple but with spare of scheduler

        :return: None
        """
        with requests_mock.mock() as mockreq:
            for port in ['7768', '7772', '7771', '7769', '7773', '8002']:
                mockreq.get('http://localhost:%s/ping' % port, json='pong')

            self.setup_with_file('cfg/dispatcher/simple.cfg')
            self.show_logs()
            json_managed = {self._scheduler_daemon.conf.uuid:
                            self._scheduler_daemon.conf.push_flavor}
            for port in ['7768', '7772', '7771', '7769', '7773']:
                mockreq.get('http://localhost:%s/what_i_managed' % port, json=json_managed)
            mockreq.get('http://localhost:8002/what_i_managed', json='{}')

            self._arbiter.dispatcher.check_reachable()
            self._arbiter.dispatcher.prepare_dispatch()
            self._arbiter.dispatcher.dispatch_ok = True

            assert 2 == len(self._arbiter.dispatcher.schedulers)
            assert 4 == len(self._arbiter.dispatcher.satellites)
            master_sched = None
            spare_sched = None
            for scheduler in self._arbiter.dispatcher.schedulers:
                if scheduler.get_name() == 'scheduler-master':
                    scheduler.is_sent = True
                    master_sched = scheduler
                else:
                    spare_sched = scheduler

            assert master_sched.ping
            assert 1 == master_sched.attempt
            assert spare_sched.ping
            assert 0 == spare_sched.attempt

        for satellite in self._arbiter.dispatcher.satellites:
            assert 1 == len(satellite.cfg['schedulers'])
            scheduler = satellite.cfg['schedulers'].itervalues().next()
            assert 'scheduler-master' == scheduler['name']

        # now simulate master sched down
        master_sched.check_interval = 1
        spare_sched.check_interval = 1
        for satellite in self._arbiter.dispatcher.receivers:
            satellite.check_interval = 1
        for satellite in self._arbiter.dispatcher.reactionners:
            satellite.check_interval = 1
        for satellite in self._arbiter.dispatcher.brokers:
            satellite.check_interval = 1
        for satellite in self._arbiter.dispatcher.pollers:
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

            self._arbiter.dispatcher.check_reachable()
            self._arbiter.dispatcher.check_dispatch()
            self._arbiter.dispatcher.prepare_dispatch()
            self._arbiter.dispatcher.dispatch()
            self._arbiter.dispatcher.check_bad_dispatch()

            assert master_sched.ping
            assert 2 == master_sched.attempt

            time.sleep(1)
            self._arbiter.dispatcher.check_reachable()
            self._arbiter.dispatcher.check_dispatch()
            self._arbiter.dispatcher.prepare_dispatch()
            self._arbiter.dispatcher.dispatch()
            self._arbiter.dispatcher.check_bad_dispatch()

            assert master_sched.ping
            assert 3 == master_sched.attempt
            # assert master_sched.alive
            #
            # time.sleep(1)
            # self.arbiter.dispatcher.check_alive()
            # self.arbiter.dispatcher.check_dispatch()
            # self.arbiter.dispatcher.prepare_dispatch()
            # self.arbiter.dispatcher.dispatch()
            # self.arbiter.dispatcher.check_bad_dispatch()

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
                                                        'because it is not alive'
            self.show_logs()
            assert 5 == len(conf_sent)
            assert ['conf'] == conf_sent['scheduler-spare'].keys()

            json_managed_spare = {}
            for satellite in self._arbiter.dispatcher.satellites:
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
            self._arbiter.dispatcher.check_reachable()
            self._arbiter.dispatcher.check_dispatch()
            self._arbiter.dispatcher.prepare_dispatch()
            self._arbiter.dispatcher.dispatch()
            self._arbiter.dispatcher.check_bad_dispatch()

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

            for satellite in self._arbiter.dispatcher.satellites:
                assert 1 == len(satellite.cfg['schedulers'])
                scheduler = satellite.cfg['schedulers'].itervalues().next()
                assert 'scheduler-master' == scheduler['name']
