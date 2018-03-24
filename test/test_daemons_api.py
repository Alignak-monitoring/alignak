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

import os
import sys
import time
import signal
import json

import subprocess
from time import sleep
import requests
import shutil
import psutil

import pytest
from alignak_test import AlignakTest

from alignak.misc.serialization import unserialize
from alignak.objects.host import Host
from alignak.http.generic_interface import GenericInterface
from alignak.http.receiver_interface import ReceiverInterface
from alignak.http.arbiter_interface import ArbiterInterface
from alignak.http.scheduler_interface import SchedulerInterface
from alignak.http.broker_interface import BrokerInterface


class TestDaemonsApi(AlignakTest):
    """Test the daemons HTTP API"""
    def setUp(self):
        # Set an environment variable to change the default period of activity log (every 60 loops)
        os.environ['ALIGNAK_ACTIVITY_LOG'] = '60'

        # Set an environment variable to activate the logging of system cpu, memory and disk
        os.environ['ALIGNAK_DAEMON_MONITORING'] = '2'

        # This function will stop all the running daemons (if any ...)
        self._stop_alignak_daemons(arbiter_only=False)

        super(TestDaemonsApi, self).setUp()

        # copy the default shipped configuration files in /tmp/etc and change the root folder
        # used by the daemons for pid and log files in the alignak.ini file
        if os.path.exists('/tmp/etc/alignak'):
            shutil.rmtree('/tmp/etc/alignak')

        if os.path.exists('/tmp/alignak.log'):
            os.remove('/tmp/alignak.log')

        if os.path.exists('/tmp/monitoring-logs.log'):
            os.remove('/tmp/monitoring-logs.log')

        print("Preparing configuration...")
        shutil.copytree('../etc', '/tmp/etc/alignak')
        files = ['/tmp/etc/alignak/alignak.ini']
        replacements = {
            '_dist=/usr/local/': '_dist=/tmp'
        }
        self._files_update(files, replacements)

        # Clean the former existing pid and log files
        print("Cleaning pid and log files...")
        for daemon in ['arbiter-master', 'scheduler-master', 'broker-master',
                       'poller-master', 'reactionner-master', 'receiver-master']:
            if os.path.exists('/tmp/var/run/%s.pid' % daemon):
                os.remove('/tmp/var/run/%s.pid' % daemon)
            if os.path.exists('/tmp/var/log/%s.log' % daemon):
                os.remove('/tmp/var/log/%s.log' % daemon)

    def tearDown(self):
        # Set an environment variable to change the default period of activity log (every 60 loops)
        os.environ['ALIGNAK_ACTIVITY_LOG'] = ''

        # Set an environment variable to activate the logging of system cpu, memory and disk
        os.environ['ALIGNAK_DAEMON_MONITORING'] = ''

        print("Test terminated!")

    def test_daemons_api_no_ssl(self):
        """ Running all the Alignak daemons - no SSL

        :return:
        """
        self._run_daemons_and_test_api(ssl=False)

    @pytest.mark.skip("See #986 - SSL is broken with test files!")
    def test_daemons_api_ssl(self):
        """ Running all the Alignak daemons - with SSL

        :return: None
        """
        # disable ssl warning
        # requests.packages.urllib3.disable_warnings()
        self._run_daemons_and_test_api(ssl=True)

    def _run_daemons_and_test_api(self, ssl=False):
        """ Running all the Alignak daemons to check their correct launch and API responses

        This test concerns only the main API features ...

        :return:
        """
        req = requests.Session()


        print("Clean former run...")
        cfg_folder = os.path.abspath('./run/test_launch_daemons')
        if os.path.exists(cfg_folder):
            shutil.rmtree(cfg_folder)

        print("Copy run configuration (../etc) to %s..." % cfg_folder)
        # Copy the default Alignak shipped configuration to the run directory
        shutil.copytree('../etc', cfg_folder)

        # Update monitoring configuration parameters
        files = ['%s/alignak.ini' % cfg_folder]
        replacements = {
            '_dist=/usr/local/': '_dist=%s' % cfg_folder,
            '%(_dist)s/bin': cfg_folder,
            '%(_dist)s/etc/alignak': cfg_folder,
            '%(_dist)s/var/lib/alignak': cfg_folder,
            '%(_dist)s/var/run/alignak': cfg_folder,
            '%(_dist)s/var/log/alignak': cfg_folder,

            ';CFG=%(etcdir)s/alignak.cfg': 'CFG=%s/alignak.cfg' % cfg_folder,
            # ';log_cherrypy=1': 'log_cherrypy=1',

            'polling_interval=5': '',
            'daemons_check_period=5': '',
            'daemons_stop_timeout=10': 'daemons_stop_timeout=5',
            ';daemons_start_timeout=0': 'daemons_start_timeout=5',
            ';daemons_dispatch_timeout=0': 'daemons_dispatch_timeout=0',

            'user=alignak': ';user=alignak',
            'group=alignak': ';group=alignak',

            ';alignak_launched=1': 'alignak_launched=1',
            ';is_daemon=1': 'is_daemon=0'
        }
        self._files_update(files, replacements)

        if ssl:
            if os.path.exists('/%s/certs' % cfg_folder):
                shutil.rmtree('/%s/certs' % cfg_folder)
            shutil.copytree('./cfg/ssl', '/%s/certs' % cfg_folder)
            # Set daemons configuration to use SSL
            replacements.update({
                'use_ssl=0': 'use_ssl=1',

                ';address=127.0.0.1': 'address=localhost',

                # Fresh test built keys
                ';server_cert=%(etcdir)s/certs/server.crt':
                    'server_cert=%(etcdir)s/certs/server.crt',          # Uncommented
                ';server_key=%(etcdir)s/certs/server.key':
                    'server_key=%(etcdir)s/certs/server.key',           # Uncommented
                ';server_dh=%(etcdir)s/certs/server.pem':
                    ';server_dh=%(etcdir)s/certs/server-dh.pem',        # Unchanged
                ';ca_cert=%(etcdir)s/certs/ca.pem':
                    ';ca_cert=%(etcdir)s/certs/server-ca.pem',          # Unchanged

                # Not used!
                # '#hard_ssl_name_check=0': 'hard_ssl_name_check=0',
            })
        self._files_update(files, replacements)

        satellite_map = {
            'arbiter': '7770', 'scheduler': '7768', 'broker': '7772',
            'poller': '7771', 'reactionner': '7769', 'receiver': '7773'
        }

        daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                        'receiver-master', 'scheduler-master']

        self._run_alignak_daemons(cfg_folder=cfg_folder,
                                  daemons_list=daemons_list, runtime=5)

        scheme = 'http'
        if ssl:
            scheme = 'https'

        # -----
        print("Testing ping")
        for name, port in satellite_map.items():
            if name == 'arbiter':   # No self ping!
                continue
            print("- ping %s: %s://localhost:%s/ping" % (name, scheme, port))
            raw_data = req.get("%s://localhost:%s/ping" % (scheme, port), verify=False)
            data = raw_data.json()
            assert data == 'pong', "Daemon %s  did not ping back!" % name

        if ssl:
            print("Testing ping with satellite SSL and client not SSL")
            for name, port in satellite_map.items():
                raw_data = req.get("http://localhost:%s/ping" % port)
                assert 'The client sent a plain HTTP request, but this server ' \
                                 'only speaks HTTPS on this port.' == raw_data.text
        # -----

        # -----
        print("Testing get_satellite_list")
        # Arbiter only
        raw_data = req.get("%s://localhost:%s/get_satellite_list" %
                           (scheme, satellite_map['arbiter']), verify=False)
        expected_data = {"reactionner": ["reactionner-master"],
                         "broker": ["broker-master"],
                         "arbiter": ["arbiter-master"],
                         "scheduler": ["scheduler-master"],
                         "receiver": ["receiver-master"],
                         "poller": ["poller-master"]}
        data = raw_data.json()
        print("Satellites: %s" % data)
        assert isinstance(data, dict), "Data is not a dict!"
        for k, v in expected_data.iteritems():
            assert set(data[k]) == set(v)
        # -----

        # -----
        print("Testing api")
        name_to_interface = {'arbiter': ArbiterInterface,
                             'scheduler': SchedulerInterface,
                             'broker': BrokerInterface,
                             'poller': GenericInterface,
                             'reactionner': GenericInterface,
                             'receiver': ReceiverInterface}
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/api" % (scheme, port), verify=False)
            data = raw_data.json()
            expected_data = set(name_to_interface[name](None).api())
            assert set(data) == expected_data, "Daemon %s has a bad API!" % name

        print("Testing api_full")
        name_to_interface = {'arbiter': ArbiterInterface,
                             'scheduler': SchedulerInterface,
                             'broker': BrokerInterface,
                             'poller': GenericInterface,
                             'reactionner': GenericInterface,
                             'receiver': ReceiverInterface}
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/api_full" % (scheme, port), verify=False)
            data = raw_data.json()
            expected_data = set(name_to_interface[name](None).api_full())
            assert set(data) == expected_data, "Daemon %s has a bad API!" % name
        # -----

        # -----
        print("Testing get_id")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/get_id" % (scheme, port), verify=False)
            data = raw_data.json()
            print("%s, my id: %s" % (name, data))
            assert isinstance(data, dict), "Data is not a dict!"
            assert 'alignak' in data
            assert 'type' in data
            assert 'name' in data
            assert 'version' in data
        # -----

        # -----
        print("Testing get_start_time")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/get_start_time" % (scheme, port), verify=False)
            data = raw_data.json()
            print("%s, my start time: %s" % (name, data))
            # assert isinstance(data, unicode), "Data is not an unicode!"
        # -----

        # -----
        print("Testing get_running_id")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/get_running_id" % (scheme, port), verify=False)
            data = raw_data.json()
            print("%s, my running id: %s" % (name, data))
            assert isinstance(data, unicode), "Data is not an unicode!"
        # -----

        print("Testing get_stats")
        for name, port in satellite_map.items():
            print("- for %s" % (name))
            raw_data = req.get("%s://localhost:%s/get_stats" % (scheme, port), verify=False)
            # print("%s, my stats: %s" % (name, raw_data.text))
            data = raw_data.json()
            print("%s, my stats: %s" % (name, data))
            # Too complex to check all this stuff
            # expected = {
            #     "alignak": "My Alignak", "type": "arbiter", "name": "Default-arbiter",
            #     "version": "1.0.0",
            #     "metrics": [
            #         "arbiter.Default-arbiter.external-commands.queue 0 1514205096"
            #     ],
            #
            #     "modules": {"internal": {}, "external": {}},
            #
            #     "monitoring_objects": {
            #         "servicesextinfo": {"count": 0},
            #         "businessimpactmodulations": {"count": 0},
            #         "hostgroups": {"count": 0},
            #         "escalations": {"count": 0},
            #         "schedulers": {"count": 1},
            #         "hostsextinfo": {"count": 0},
            #         "contacts": {"count": 0},
            #         "servicedependencies": {"count": 0},
            #         "resultmodulations": {"count": 0},
            #         "servicegroups": {"count": 0},
            #         "pollers": {"count": 1},
            #         "arbiters": {"count": 1},
            #         "receivers": {"count": 1},
            #         "macromodulations": {"count": 0},
            #         "reactionners": {"count": 1},
            #         "contactgroups": {"count": 0},
            #         "brokers": {"count": 1},
            #         "realms": {"count": 1},
            #         "services": {"count": 0},
            #         "commands": {"count": 4},
            #         "notificationways": {"count": 0},
            #         "timeperiods": {"count": 1},
            #         "modules": {"count": 0},
            #         "checkmodulations": {"count": 0},
            #         "hosts": {"count": 2},
            #         "hostdependencies": {"count": 0}
            #     }
            # }
            # assert expected == data, "Data is not an unicode!"

        # print("Testing wait_new_conf")
        # # Except Arbiter (not spare)
        # for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
        #     raw_data = req.get("%s://localhost:%s/wait_new_conf" % (http, satellite_map[daemon]), verify=False)
        #     data = raw_data.json()
        #     assert data == None

        print("Testing have_conf")
        # Except Arbiter (not spare)
        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            raw_data = req.get("%s://localhost:%s/have_conf" % (scheme, satellite_map[daemon]), verify=False)
            data = raw_data.json()
            print("%s, have_conf: %s" % (daemon, data))
            assert data == True, "Daemon %s should have a conf!" % daemon

            # raw_data = req.get("%s://localhost:%s/have_conf?magic_hash=1234567890" % (http, satellite_map[daemon]), verify=False)
            # data = raw_data.json()
            # print("%s, have_conf: %s" % (daemon, data))
            # assert data == False, "Daemon %s should not accept the magic hash!" % daemon

        print("Testing do_not_run")
        # Arbiter only
        raw_data = req.get("%s://localhost:%s/do_not_run" %
                           (scheme, satellite_map['arbiter']), verify=False)
        data = raw_data.json()
        print("%s, do_not_run: %s" % (name, data))
        # Arbiter master returns False, spare returns True
        assert data is False

        # print("Testing get_checks on scheduler")
        # TODO: if have poller running, the poller will get the checks before us
        #
        # We need to sleep 10s to be sure the first check can be launched now (check_interval = 5)
        # sleep(4)
        # raw_data = req.get("http://localhost:%s/get_checks" % satellite_map['scheduler'], params={'do_checks': True})
        # data = unserialize(raw_data.json(), True)
        # self.assertIsInstance(data, list, "Data is not a list!")
        # self.assertNotEqual(len(data), 0, "List is empty!")
        # for elem in data:
        #     self.assertIsInstance(elem, Check, "One elem of the list is not a Check!")

        # Todo: refactor this - not used currently
        print("Testing get_raw_stats")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/get_raw_stats" % (scheme, port), verify=False)
            # print("- %s, get_raw_stats raw data: %s" % (name, raw_data.text))
            data = raw_data.json()
            print("- %s, raw stats: %s" % (name, data))
            assert isinstance(data, dict), "Data is not a dict!"

            if name in ['reactionner']:
                scheduler_reactionner_id = "XxX"
                for sched_uuid in data:
                    print("- scheduler: %s / %s" % (sched_uuid, data))
                    scheduler_reactionner_id = sched_uuid
                    assert 'scheduler_instance_id' in data[sched_uuid][0]
                    scheduler_reactionner_id = data[sched_uuid][0]['scheduler_instance_id']
                    assert 'scheduler_name' in data[sched_uuid][0]
                    assert 'module' in data[sched_uuid][0]
                    assert 'worker' in data[sched_uuid][0]
                    assert 'worker_queue_size' in data[sched_uuid][0]
                    assert 'return_queue_size' in data[sched_uuid][0]
                print("- -> got a scheduler uuid: %s" % scheduler_reactionner_id)
                assert scheduler_reactionner_id != "XxX"

            if name in ['poller']:
                scheduler_poller_id = "XxX"
                for sched_uuid in data:
                    print("- scheduler: %s / %s" % (sched_uuid, data))
                    scheduler_poller_id = sched_uuid
                    assert 'scheduler_instance_id' in data[sched_uuid][0]
                    scheduler_poller_id = data[sched_uuid][0]['scheduler_instance_id']
                    assert 'scheduler_name' in data[sched_uuid][0]
                    assert 'module' in data[sched_uuid][0]
                    assert 'worker' in data[sched_uuid][0]
                    assert 'worker_queue_size' in data[sched_uuid][0]
                    assert 'return_queue_size' in data[sched_uuid][0]
                print("- -> got a scheduler uuid: %s" % scheduler_poller_id)
                assert scheduler_poller_id != "XxX"

            if name in ['arbiter']:
                assert data == {}

            if name in ['broker']:
                assert 'modules_count' in data

            if name in ['scheduler']:
                assert 'latency_average' in data
                assert 'latency_maximum' in data
                assert 'latency_minimum' in data
                assert 'counters' in data

            if name in ['receiver']:
                assert data == {"command_buffer_size": 0}

        print("Testing get_managed_configurations")
        for name, port in satellite_map.items():
            print("%s, what I manage?" % (name))
            raw_data = req.get("%s://localhost:%s/get_managed_configurations" % (scheme, port), verify=False)
            data = raw_data.json()
            print("%s, what I manage: %s" % (name, data))
            assert isinstance(data, dict), "Data is not a dict!"
            if name != 'arbiter':
                assert 1 == len(data), "The dict must have 1 key/value!"
                for sat_id in data:
                    assert 'hash' in data[sat_id]
                    assert 'push_flavor' in data[sat_id]
                    assert 'managed_conf_id' in data[sat_id]
            else:
                assert 0 == len(data), "The dict must be empty!"

        print("Testing get_external_commands")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/get_external_commands" % (scheme, port), verify=False)
            print("%s, raw_data: %s" % (name, raw_data.text))
            data = raw_data.json()
            assert isinstance(data, list), "Data is not a list!"

        if sys.version_info[:2] != (2, 6):
            # -----
            # Log level
            print("Testing get_log_level")
            for name, port in satellite_map.items():
                raw_data = req.get("%s://localhost:%s/get_log_level" % (scheme, port), verify=False)
                data = raw_data.json()
                print("%s, log level: %s" % (name, data))
                assert data['log_level'] == 20

            # todo: currently not fully functional ! Looks like it breaks the arbiter damon !
            print("Testing set_log_level")
            for name, port in satellite_map.items():
                raw_data = req.post("%s://localhost:%s/set_log_level" % (scheme, port),
                                    data=json.dumps({'log_level': 'DEBUG'}),
                                    headers={'Content-Type': 'application/json'},
                                    verify=False)
                print("%s, raw_data: %s" % (name, raw_data.text))
                data = raw_data.json()
                print("%s, log level set as : %s" % (name, data))
                if name in ['arbiter']:
                    assert data == {"message": "Changing the arbiter log level is not supported: DEBUG"}
                else:
                    assert data == 'DEBUG'

            print("Testing get_log_level")
            for name, port in satellite_map.items():
                if name in ['arbiter']:
                    continue
                raw_data = req.get("%s://localhost:%s/get_log_level" % (scheme, port), verify=False)
                data = raw_data.json()
                print("%s, log level: %s" % (name, data))
                if name in ['arbiter']:
                    assert data['log_level'] == 20
                else:
                    assert data['log_level'] == 10
            # -----

        print("Testing get_all_states")
        # Arbiter only
        raw_data = req.get("%s://localhost:%s/get_all_states" %
                           (scheme, satellite_map['arbiter']), verify=False)
        data = raw_data.json()
        assert isinstance(data, dict), "Data is not a dict!"
        for daemon_type in data:
            daemons = data[daemon_type]
            print("Got Alignak state for: %ss / %d instances" % (daemon_type, len(daemons)))
            for daemon in daemons:
                print(" - %s: %s", daemon['%s_name' % daemon_type], daemon['alive'])
                print(" - %s: %s", daemon['%s_name' % daemon_type], daemon)
                assert daemon['alive']
                assert 'realms' not in daemon
                assert 'confs' not in daemon
                assert 'tags' not in daemon
                assert 'con' not in daemon
                assert 'realm_name' in daemon

        # todo: deprecate this! or not ?
        print("Testing get_objects_properties")
        for object in ['host', 'service', 'contact',
                       'hostgroup', 'servicegroup', 'contactgroup',
                       'command', 'timeperiod',
                       'notificationway', 'escalation',
                       'checkmodulation', 'macromodulation', 'resultmodulation',
                       'businessimpactmodulation'
                       'hostdependencie', 'servicedependencie',
                       'realm',
                       'arbiter', 'scheduler', 'poller', 'broker', 'reactionner', 'receiver']:
            # Arbiter only
            raw_data = req.get("%s://localhost:%s/get_objects_properties" %
                               (scheme, satellite_map['arbiter']),
                               params={'table': '%ss' % object}, verify=False)
            data = raw_data.json()
            assert data == {'message': "Deprecated in favor of the get_stats endpoint."}

        print("Testing fill_initial_broks")
        # Scheduler only
        raw_data = req.get("%s://localhost:%s/fill_initial_broks" %
                           (scheme, satellite_map['scheduler']),
                           params={'broker_name': 'broker-master'}, verify=False)
        print("fill_initial_broks, raw_data: %s" % (raw_data.text))
        data = raw_data.json()
        assert data == 0, "Data must be 0 - no broks!"

        # -----
        print("Testing get_broks")
        # All except the arbiter and the broker itself!
        for name, port in satellite_map.items():
            if name in ['arbiter', 'broker']:
                continue
            raw_data = req.get("%s://localhost:%s/get_broks" % (scheme, port),
                               params={'broker_name': 'broker-master'}, verify=False)
            print("%s, get_broks raw_data: %s" % (name, raw_data.text))
            data = raw_data.json()
            print("%s, broks: %s" % (name, data))
            assert isinstance(data, dict), "Data is not a dict!"
        # -----

        # -----
        print("Testing get_returns")
        # get_return requested by a scheduler to a potential passive daemons
        for name in ['reactionner']:
            raw_data = req.get("%s://localhost:%s/get_returns" %
                               (scheme, satellite_map[name]),
                               params={'scheduler_instance_id': scheduler_reactionner_id}, verify=False)
            print("%s, get_returns raw_data: %s" % (name, raw_data.text))
            data = raw_data.json()
            assert isinstance(data, list), "Data is not a list!"

        for name in ['poller']:
            raw_data = req.get("%s://localhost:%s/get_returns" %
                               (scheme, satellite_map[name]),
                               params={'scheduler_instance_id': scheduler_poller_id}, verify=False)
            data = raw_data.json()
            assert isinstance(data, list), "Data is not a list!"
        # -----

        print("Testing signals")
        for name, proc in self.procs.items():
            # SIGUSR1: memory dump
            print("%s, send signal SIGUSR1" % (name))
            self.procs[name].send_signal(signal.SIGUSR1)
            time.sleep(1.0)
            # SIGUSR2: objects dump
            print("%s, send signal SIGUSR2" % (name))
            self.procs[name].send_signal(signal.SIGUSR2)
            time.sleep(1.0)
            # SIGHUP: reload configuration
            # self.procs[name].send_signal(signal.SIGHUP)
            # time.sleep(1.0)
            # Other signals is considered as a request to stop...

        # This function will only send a SIGTERM to the arbiter daemon
        self._stop_alignak_daemons(arbiter_only=True)

        # The arbiter daemon will then request its satellites to stop...
        # this is the same as the following code:
        # print("Testing stop_request - tell the daemons we will stop soon...")
        # for name, port in satellite_map.items():
        #     if name in ['arbiter']:
        #         continue
        #     raw_data = req.get("%s://localhost:%s/stop_request?stop_now=" % (scheme, port),
        #                        params={'stop_now': False}, verify=False)
        #     data = raw_data.json()
        #     assert data is True
        #
        # time.sleep(2)
        # print("Testing stop_request - tell the daemons they must stop now!")
        # for name, port in satellite_map.items():
        #     if name in ['arbiter']:
        #         continue
        #     raw_data = req.get("%s://localhost:%s/stop_request?stop_now=" % (scheme, port),
        #                        params={'stop_now': True}, verify=False)
        #     data = raw_data.json()
        #     assert data is True

    def test_daemons_configuration(self):
        """ Running all the Alignak daemons to check their correct configuration

        Tests for the configuration dispatch API

        :return:
        """
        self._run_daemons_and_configure(ssl=False)

    def _run_daemons_and_configure(self, ssl=False):
        """ Running all the Alignak daemons to check their correct launch and API

        Tests for the configuration dispatch API

        :return:
        """
        print("Clean former run...")
        cfg_folder = os.path.abspath('./run/test_launch_daemons')
        if os.path.exists(cfg_folder):
            shutil.rmtree(cfg_folder)

        print("Copy run configuration (../etc) to %s..." % cfg_folder)
        # Copy the default Alignak shipped configuration to the run directory
        shutil.copytree('../etc', cfg_folder)

        # Update monitoring configuration parameters
        files = ['%s/alignak.ini' % cfg_folder]
        replacements = {
            '_dist=/usr/local/': '_dist=%s' % cfg_folder,
            '%(_dist)s/bin': cfg_folder,
            '%(_dist)s/etc/alignak': cfg_folder,
            '%(_dist)s/var/lib/alignak': cfg_folder,
            '%(_dist)s/var/run/alignak': cfg_folder,
            '%(_dist)s/var/log/alignak': cfg_folder,

            ';CFG=%(etcdir)s/alignak.cfg': 'CFG=%s/alignak.cfg' % cfg_folder,
            # ';log_cherrypy=1': 'log_cherrypy=1',

            'polling_interval=5': '',
            'daemons_check_period=5': '',
            'daemons_stop_timeout=10': 'daemons_stop_timeout=5',
            ';daemons_start_timeout=0': 'daemons_start_timeout=5',
            ';daemons_dispatch_timeout=0': 'daemons_dispatch_timeout=0',

            'user=alignak': ';user=alignak',
            'group=alignak': ';group=alignak',

            ';alignak_launched=1': 'alignak_launched=1',
            ';is_daemon=1': 'is_daemon=0'
        }
        self._files_update(files, replacements)

        satellite_map = {
            'arbiter': '7770', 'scheduler': '7768', 'broker': '7772',
            'poller': '7771', 'reactionner': '7769', 'receiver': '7773'
        }

        daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                        'receiver-master', 'scheduler-master']

        self._run_alignak_daemons(cfg_folder=cfg_folder,
                                  daemons_list=daemons_list, runtime=5)

        scheme = 'http'
        if ssl:
            scheme = 'https'

        req = requests.Session()

        # Here the daemons got started by the arbiter and the arbiter dispatched a configuration
        # We will ask to wait for a new configuration

        # -----
        # 1/ get the running identifier (confirm the daemon is running)
        print("--- get_running_id")
        for name, port in satellite_map.items():
            raw_data = req.get("%s://localhost:%s/get_running_id" % (scheme, port), verify=False)
            print("Got (raw): %s" % raw_data)
            data = raw_data.json()
            print("%s, my running id: %s" % (name, data))
            assert isinstance(data, unicode), "Data is not an unicode!"
        # -----

        # -----
        # 2/ ask if have a configuration - must have one!
        print("--- have_conf")
        # Except Arbiter (not spare)
        for name, port in satellite_map.items():
            if name == 'arbiter-master':
                continue
            raw_data = req.get("%s://localhost:%s/have_conf" % (scheme, port), verify=False)
            print("have_conf, got (raw): %s" % raw_data)
            data = raw_data.json()
            print("%s, have_conf: %s" % (name, data))
            assert data == True, "Daemon %s should have a conf!" % name

        # -----
        # 3/ ask to wait for a new configuration
        print("--- wait_new_conf")
        for name, port in satellite_map.items():
            if name == 'arbiter-master':
                continue
            raw_data = req.get("%s://localhost:%s/wait_new_conf" % (scheme, port), verify=False)
            print("wait_new_conf, got (raw): %s" % raw_data)
            data = raw_data.json()
            assert data == None
        # -----

        # -----
        # 4/ ask if have a configuration - must not have
        print("--- have_conf")
        # Except Arbiter (not spare)
        for name, port in satellite_map.items():
            if name == 'arbiter-master':
                continue
            raw_data = req.get("%s://localhost:%s/have_conf" % (scheme, port), verify=False)
            print("have_conf, got (raw): %s" % raw_data)
            data = raw_data.json()
            print("%s, have_conf: %s" % (name, data))
            assert data == False, "Daemon %s should not have a conf!" % name

        # This function will only send a SIGTERM to the arbiter daemon
        # self._stop_alignak_daemons(arbiter_only=True)
        time.sleep(2)

        # The arbiter daemon will then request its satellites to stop...
        # this is the same as the following code:
        print("Testing stop_request - tell the daemons we will stop soon...")
        for name, port in satellite_map.items():
            if name in ['arbiter']:
                continue
            raw_data = req.get("%s://localhost:%s/stop_request?stop_now=" % (scheme, port),
                               params={'stop_now': False}, verify=False)
            data = raw_data.json()
            assert data is True

        time.sleep(2)
        print("Testing stop_request - tell the daemons they must stop now!")
        for name, port in satellite_map.items():
            if name in ['arbiter']:
                continue
            raw_data = req.get("%s://localhost:%s/stop_request?stop_now=" % (scheme, port),
                               params={'stop_now': True}, verify=False)
            data = raw_data.json()
            assert data is True

    def test_get_host(self):
        """ Running all the Alignak daemons - get host from the scheduler

        :return:
        """
        print("Clean former run...")
        cfg_folder = os.path.abspath('./run/test_launch_daemons')
        if os.path.exists(cfg_folder):
            shutil.rmtree(cfg_folder)

        print("Copy run configuration (../etc) to %s..." % cfg_folder)
        # Copy the default Alignak shipped configuration to the run directory
        shutil.copytree('../etc', cfg_folder)

        # Update monitoring configuration parameters
        files = ['%s/alignak.ini' % cfg_folder]
        replacements = {
            '_dist=/usr/local/': '_dist=%s' % cfg_folder,
            '%(_dist)s/bin': cfg_folder,
            '%(_dist)s/etc/alignak': cfg_folder,
            '%(_dist)s/var/lib/alignak': cfg_folder,
            '%(_dist)s/var/run/alignak': cfg_folder,
            '%(_dist)s/var/log/alignak': cfg_folder,

            ';CFG=%(etcdir)s/alignak.cfg': 'CFG=%s/alignak.cfg' % cfg_folder,
            # ';log_cherrypy=1': 'log_cherrypy=1',

            'polling_interval=5': '',
            'daemons_check_period=5': '',
            'daemons_stop_timeout=10': 'daemons_stop_timeout=5',
            ';daemons_start_timeout=0': 'daemons_start_timeout=5',
            ';daemons_dispatch_timeout=0': 'daemons_dispatch_timeout=0',

            'user=alignak': ';user=alignak',
            'group=alignak': ';group=alignak',

            ';alignak_launched=1': 'alignak_launched=1',
            ';is_daemon=1': 'is_daemon=0'
        }
        self._files_update(files, replacements)

        satellite_map = {
            'arbiter': '7770', 'scheduler': '7768', 'broker': '7772',
            'poller': '7771', 'reactionner': '7769', 'receiver': '7773'
        }

        daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                        'receiver-master', 'scheduler-master']

        self._run_alignak_daemons(cfg_folder=cfg_folder,
                                  daemons_list=daemons_list, runtime=5)

        req = requests.Session()

        # Here the daemons got started by the arbiter and the arbiter dispatched a configuration
        # We will ask to wait for a new configuration

        # -----
        # 1/ get the running identifier (confirm the daemon is running)
        print("--- get_running_id")
        for name, port in satellite_map.items():
            raw_data = req.get("http://localhost:%s/get_running_id" % port, verify=False)
            print("Got (raw): %s" % raw_data)
            data = raw_data.json()
            print("%s, my running id: %s" % (name, data))
            assert isinstance(data, unicode), "Data is not an unicode!"
        # -----

        # -----
        # 2/ ask for a managed host.
        # The scheduler has a service to get an host information. This may be used to know if
        # an host exist in Alignak and to get its configuration and state

        # Only Scheduler daemon
        raw_data = req.get("http://localhost:7768/get_host?host_name=localhost", verify=False)
        print("get_host, got (raw): %s" % raw_data)
        host = unserialize(raw_data.json(), True)
        print("Got: %s" % host)
        assert host.__class__ == Host
        assert host.get_name() == 'localhost'

        raw_data = req.get("http://localhost:7768/get_host?host_name=unknown_host", verify=False)
        print("get_host, got (raw): %s" % raw_data)
        host = unserialize(raw_data.json(), True)
        print("Got: %s" % host)
        assert host is None

        # This function will only send a SIGTERM to the arbiter daemon
        self._stop_alignak_daemons(arbiter_only=True)
