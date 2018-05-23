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
from .alignak_test import AlignakTest

from alignak.misc.serialization import unserialize
from alignak.objects.host import Host
from alignak.http.generic_interface import GenericInterface
from alignak.http.arbiter_interface import ArbiterInterface
from alignak.http.scheduler_interface import SchedulerInterface
from alignak.http.broker_interface import BrokerInterface
from alignak.log import set_log_level


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
        files = ['/tmp/etc/alignak/alignak.ini',
                 '/tmp/etc/alignak/alignak-logger.json']
        replacements = {
            '_dist=/usr/local/': '_dist=/tmp',
            '"level": "INFO"': '"level": "WARNING"'
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
        print("Clean former run...")
        cfg_folder = os.path.abspath('./run/test_launch_daemons')
        if os.path.exists(cfg_folder):
            shutil.rmtree(cfg_folder)

        print("Copy run configuration (../etc) to %s..." % cfg_folder)
        # Copy the default Alignak shipped configuration to the run directory
        shutil.copytree('../etc', cfg_folder)

        # Update monitoring configuration parameters
        files = ['%s/alignak.ini' % cfg_folder,
                 '%s/alignak-logger.json' % cfg_folder]
        replacements = {
            '_dist=/usr/local/': '_dist=%s' % cfg_folder,
            '%(_dist)s/bin': '',
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
            ';is_daemon=0': 'is_daemon=0',
            ';do_replace=0': 'do_replace=1',

            # '"level": "INFO"': '"level": "WARNING"'
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

        # -----
        print("Testing ping")
        for name, port in list(satellite_map.items()):
            if name == 'arbiter':   # No self ping!
                continue
            print("- ping %s: %s://localhost:%s/ping" % (name, scheme, port))
            raw_data = req.get("%s://localhost:%s/ping" % (scheme, port), verify=False)
            data = raw_data.json()
            assert data == 'pong', "Daemon %s  did not ping back!" % name

        if ssl:
            print("Testing ping with satellite SSL and client not SSL")
            for name, port in list(satellite_map.items()):
                raw_data = req.get("http://localhost:%s/ping" % port)
                assert 'The client sent a plain HTTP request, but this server ' \
                       'only speaks HTTPS on this port.' == raw_data.text
        # -----

        # -----
        print("Testing api...")
        name_to_interface = {'arbiter': ArbiterInterface,
                             'scheduler': SchedulerInterface,
                             'broker': BrokerInterface,
                             'poller': GenericInterface,
                             'reactionner': GenericInterface,
                             'receiver': GenericInterface}
        doc = []
        doc.append(".. _alignak_features/daemons_api:")
        doc.append("")
        doc.append(".. Built from the test_daemons_api.py unit test last run!")
        doc.append("")
        doc.append("===================")
        doc.append("Alignak daemons API")
        doc.append("===================")
        for name, port in list(satellite_map.items()):
            raw_data = req.get("%s://localhost:%s/api" % (scheme, port), verify=False)
            print("%s, api: %s" % (name, raw_data.text))
            assert raw_data.status_code == 200
            data = raw_data.json()
            print("API data: %s" % data)
            assert 'doc' in data
            assert 'api' in data
            doc.append("Daemon type: %s" % name)
            doc.append("-" * len("Daemon type: %s" % name))
            for endpoint in data['api']:
                assert 'name' in endpoint
                assert 'doc' in endpoint
                assert 'args' in endpoint
                doc.append("/%s" % endpoint['name'])
                doc.append("~" * len("/%s" % endpoint['name']))
                doc.append("")
                doc.append("Python source code documentation\n ::\n")
                doc.append("    %s" % endpoint['doc'])
                doc.append("")

            expected_data = set(name_to_interface[name](None).api())
            assert set(data) == expected_data, "Daemon %s has a bad API!" % name
        print('\n'.join(doc))

        rst_write = None
        rst_file = "daemons_api.rst"
        if os.path.exists("../doc/source/api"):
            rst_write = "../doc/source/api/%s" % rst_file
        if os.path.exists("../../alignak-doc/source/07_alignak_features/api"):
            rst_write = "../../alignak-doc/source/07_alignak_features/api/%s" % rst_file
        if rst_write:
            with open(rst_write, mode='wt', encoding='utf-8') as out:
                out.write('\n'.join(doc))
        # -----

        # -----
        print("Testing get_id")
        for name, port in list(satellite_map.items()):
            raw_data = req.get("%s://localhost:%s/get_id" % (scheme, port), verify=False)
            assert raw_data.status_code == 200
            data = raw_data.json()
            print("%s, my id: %s" % (name, json.dumps(data)))
            assert isinstance(data, dict), "Data is not a dict!"
            assert 'alignak' in data
            assert 'type' in data
            assert 'name' in data
            assert 'version' in data
        # -----

        # -----
        print("Testing get_start_time")
        for name, port in list(satellite_map.items()):
            raw_data = req.get("%s://localhost:%s/get_start_time" % (scheme, port), verify=False)
            assert raw_data.status_code == 200
            data = raw_data.json()
            print("%s, my start time: %s" % (name, data['start_time']))
            # Same as get_id
            assert 'alignak' in data
            assert 'type' in data
            assert 'name' in data
            assert 'version' in data
            # +
            assert 'start_time' in data
        # -----

        # -----
        print("Testing get_running_id")
        for name, port in list(satellite_map.items()):
            raw_data = req.get("%s://localhost:%s/get_running_id" % (scheme, port), verify=False)
            assert raw_data.status_code == 200
            data = raw_data.json()
            assert "running_id" in data
            print("%s, my running id: %s" % (name, data['running_id']))
            # Same as get_id
            assert 'alignak' in data
            assert 'type' in data
            assert 'name' in data
            assert 'version' in data
            # +
            assert 'running_id' in data
        # -----

        # -----
        print("Testing get_satellites_list")
        # Arbiter only
        raw_data = req.get("%s://localhost:%s/get_satellites_list" %
                           (scheme, satellite_map['arbiter']), verify=False)
        assert raw_data.status_code == 200
        expected_data = {"reactionner": ["reactionner-master"],
                         "broker": ["broker-master"],
                         "arbiter": ["arbiter-master"],
                         "scheduler": ["scheduler-master"],
                         "receiver": ["receiver-master"],
                         "poller": ["poller-master"]}
        data = raw_data.json()
        print("Satellites: %s" % json.dumps(data))
        assert isinstance(data, dict), "Data is not a dict!"
        for k, v in expected_data.items():
            assert set(data[k]) == set(v)
        # -----

        # -----
        print("Testing get_alignak_status")
        # Arbiter only
        raw_data = req.get("%s://localhost:%s/get_alignak_status" %
                           (scheme, satellite_map['arbiter']), verify=False)
        assert raw_data.status_code == 200
        data = raw_data.json()
        print("Overall status: %s" % json.dumps(data))
        assert "template" in data
        assert "livestate" in data
        assert "services" in data
        assert isinstance(data['services'], list)
        for service in data['services']:
            assert "name" in service
            assert service['name'] in ['arbiter-master', 'broker-master', 'poller-master',
                                       'scheduler-master', 'reactionner-master', 'receiver-master']
            assert "livestate" in service
            livestate = service['livestate']
            assert "timestamp" in livestate
            assert "state" in livestate
            assert "output" in livestate
            assert "long_output" in livestate
            assert "perf_data" in livestate

        doc = []
        doc.append(".. _alignak_features/alignak_status:")
        doc.append(".. Built from the test_daemons_api.py unit test last run!")
        doc.append("")
        doc.append("======================")
        doc.append("Alignak overall status")
        doc.append("======================")
        doc.append("An Alignak overall status example:")
        doc.append("")
        doc.append("::")
        doc.append("")
        doc.append("    %s" % json.dumps(data, sort_keys=True, indent=4))
        doc.append("")

        rst_write = None
        rst_file = "alignak_status.rst"
        if os.path.exists("../doc/source/api"):
            rst_write = "../doc/source/api/%s" % rst_file
        if os.path.exists("../../alignak-doc/source/07_alignak_features/api"):
            rst_write = "../../alignak-doc/source/07_alignak_features/api/%s" % rst_file
        if rst_write:
            with open(rst_write, mode='wt', encoding='utf-8') as out:
                out.write('\n'.join(doc))
        # -----

        # -----
        print("Testing get_stats")

        doc = []
        doc.append(".. _alignak_features/daemons_stats:")
        doc.append(".. Built from the test_daemons_api.py unit test last run!")
        doc.append("")
        doc.append("==========================")
        doc.append("Alignak daemons statistics")
        doc.append("==========================")
        for name, port in list(satellite_map.items()):
            print("- for %s" % (name))
            raw_data = req.get("%s://localhost:%s/get_stats" % (scheme, port), verify=False)
            print("%s, my stats: %s" % (name, raw_data.text))
            assert raw_data.status_code == 200
            data = raw_data.json()
            print("%s, my stats: %s" % (name, json.dumps(data)))

            doc.append("")
            doc.append("Daemon type: %s" % name)
            doc.append("-" * len("Daemon type: %s" % name))
            doc.append("")
            doc.append("A %s daemon statistics example:\n ::\n" % name)
            doc.append("    %s" % json.dumps(data, sort_keys=True, indent=4))
            doc.append("")

            # Same as start_time
            assert 'alignak' in data
            assert 'type' in data
            assert 'name' in data
            assert 'version' in data
            assert 'start_time' in data
            # +
            assert "program_start" in data
            assert "load" in data
            assert "metrics" in data    # To be deprecated...
            assert "modules" in data
            assert "counters" in data

            if name in ['arbiter']:
                assert "livestate" in data
                livestate = data['livestate']
                assert "timestamp" in livestate
                assert "state" in livestate
                assert "output" in livestate
                assert "daemons" in livestate
                for daemon_state in livestate['daemons']:
                    assert livestate['daemons'][daemon_state] == 0

                assert "daemons_states" in data
                daemons_state = data['daemons_states']
                for daemon_name in daemons_state:
                    daemon_state = daemons_state[daemon_name]
                    assert "type" in daemon_state
                    assert "name" in daemon_state
                    assert "realm_name" in daemon_state
                    assert "manage_sub_realms" in daemon_state
                    assert "uri" in daemon_state
                    assert "alive" in daemon_state
                    assert "passive" in daemon_state
                    assert "reachable" in daemon_state
                    assert "active" in daemon_state
                    assert "spare" in daemon_state
                    assert "polling_interval" in daemon_state
                    assert "configuration_sent" in daemon_state
                    assert "max_check_attempts" in daemon_state
                    assert "last_check" in daemon_state
                    assert "livestate" in daemon_state
                    assert "livestate_output" in daemon_state

        rst_write = None
        rst_file = "daemons_stats.rst"
        if os.path.exists("../doc/source/api"):
            rst_write = "../doc/source/api/%s" % rst_file
        if os.path.exists("../../alignak-doc/source/07_alignak_features/api"):
            rst_write = "../../alignak-doc/source/07_alignak_features/api/%s" % rst_file
        if rst_write:
            with open(rst_write, mode='wt', encoding='utf-8') as out:
                out.write('\n'.join(doc))

        print("Testing get_stats (detailed)")
        for name, port in list(satellite_map.items()):
            print("- for %s" % (name))
            raw_data = req.get("%s://localhost:%s/get_stats?details=1" % (scheme, port), verify=False)
            print("%s, my stats: %s" % (name, raw_data.text))
            assert raw_data.status_code == 200
            # print("%s, my stats: %s" % (name, raw_data.text))
            data = raw_data.json()
            print("%s, my stats: %s" % (name, json.dumps(data)))
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
        # -----

        # -----
        # print("Testing wait_new_conf")
        # # Except Arbiter (not spare)
        # for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
        #     raw_data = req.get("%s://localhost:%s/wait_new_conf" % (http, satellite_map[daemon]), verify=False)
        #     data = raw_data.json()
        #     assert data == None
        # -----

        # -----
        print("Testing have_conf")
        # Except Arbiter (not spare)
        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            raw_data = req.get("%s://localhost:%s/have_conf" % (scheme, satellite_map[daemon]), verify=False)
            assert raw_data.status_code == 200
            data = raw_data.json()
            print("%s, have_conf: %s" % (daemon, data))
            assert data == True, "Daemon %s should have a conf!" % daemon

            # raw_data = req.get("%s://localhost:%s/have_conf?magic_hash=1234567890" % (http, satellite_map[daemon]), verify=False)
            # data = raw_data.json()
            # print("%s, have_conf: %s" % (daemon, data))
            # assert data == False, "Daemon %s should not accept the magic hash!" % daemon
        # -----

        # -----
        print("Testing do_not_run")
        # Arbiter only
        raw_data = req.get("%s://localhost:%s/do_not_run" %
                           (scheme, satellite_map['arbiter']), verify=False)
        assert raw_data.status_code == 200
        data = raw_data.json()
        print("%s, do_not_run: %s" % (name, data))
        # Arbiter master returns False, spare returns True
        assert data is False
        # -----

        # -----
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

        # -----
        print("Testing get_managed_configurations")
        for name, port in list(satellite_map.items()):
            print("%s, what I manage?" % (name))
            raw_data = req.get("%s://localhost:%s/get_managed_configurations" % (scheme, port), verify=False)
            assert raw_data.status_code == 200
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
        # -----

        # -----
        print("Testing get_external_commands")
        for name, port in list(satellite_map.items()):
            raw_data = req.get("%s://localhost:%s/get_external_commands" % (scheme, port), verify=False)
            assert raw_data.status_code == 200
            print("%s get_external_commands, got (raw): %s" % (name, raw_data.content))
            data = raw_data.json()
            assert isinstance(data, list), "Data is not a list!"
        # -----

        # -----
        # Log level
        print("Testing get_log_level")
        for name, port in list(satellite_map.items()):
            raw_data = req.get("%s://localhost:%s/get_log_level" % (scheme, port), verify=False)
            print("%s, raw: %s" % (name, raw_data.content))
            data = raw_data.json()
            print("%s, log level: %s" % (name, data))
            # Initially forced the WARNING log level
            assert data['log_level'] == 30
            assert data['log_level_name'] == 'WARNING'

        # todo: currently not fully functional ! Looks like it breaks the arbiter damon !
        print("Testing set_log_level")
        for name, port in list(satellite_map.items()):
            raw_data = req.post("%s://localhost:%s/set_log_level" % (scheme, port),
                                data=json.dumps({'log_level': 'UNKNOWN'}),
                                headers={'Content-Type': 'application/json'}, verify=False)
            data = raw_data.json()
            assert data == {"_status": u"ERR",
                            "_message": u"Required log level is not allowed: UNKNOWN"}

            raw_data = req.post("%s://localhost:%s/set_log_level" % (scheme, port),
                                data=json.dumps({'log_level': 'DEBUG'}),
                                headers={'Content-Type': 'application/json'},
                                verify=False)
            print("%s, raw_data: %s" % (name, raw_data.text))
            data = raw_data.json()
            print("%s, log level set as : %s" % (name, data))
            assert data['log_level'] == 10
            assert data['log_level_name'] == 'DEBUG'

        print("Testing get_log_level")
        for name, port in list(satellite_map.items()):
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

        # -----
        print("Testing get_satellites_configuration")
        # Arbiter only
        raw_data = req.get("%s://localhost:%s/get_satellites_configuration" %
                           (scheme, satellite_map['arbiter']), verify=False)
        assert raw_data.status_code == 200
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
        # -----

        # -----
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
            assert raw_data.status_code == 200
            data = raw_data.json()
            assert data == {"_status": u"ERR",
                            "_message": u"Deprecated in favor of the get_stats endpoint."}
        # -----

        # -----
        print("Testing fill_initial_broks")
        # Scheduler only
        raw_data = req.get("%s://localhost:%s/fill_initial_broks" %
                           (scheme, satellite_map['scheduler']),
                           params={'broker_name': 'broker-master'}, verify=False)
        assert raw_data.status_code == 200
        print("fill_initial_broks, raw_data: %s" % (raw_data.text))
        data = raw_data.json()
        assert data == 0, "Data must be 0 - no broks!"
        # -----

        # -----
        print("Testing get_broks")
        # All except the arbiter and the broker itself!
        for name, port in list(satellite_map.items()):
            if name in ['arbiter', 'broker']:
                continue
            raw_data = req.get("%s://localhost:%s/get_broks" % (scheme, port),
                               params={'broker_name': 'broker-master'}, verify=False)
            assert raw_data.status_code == 200
            print("%s, get_broks raw_data: %s" % (name, raw_data.text))
            data = raw_data.json()
            print("%s, broks: %s" % (name, data))
            assert isinstance(data, list), "Data is not a list!"
        # -----

        # -----
        print("Testing get_returns")
        # get_return requested by a scheduler to a potential passive daemons
        for name in ['reactionner']:
            raw_data = req.get("%s://localhost:%s/get_results" %
                               (scheme, satellite_map[name]),
                               params={'scheduler_instance_id': 'XxX'}, verify=False)
            assert raw_data.status_code == 200
            print("%s, get_returns raw_data: %s" % (name, raw_data.text))
            data = raw_data.json()
            assert isinstance(data, list), "Data is not a list!"

        for name in ['poller']:
            raw_data = req.get("%s://localhost:%s/get_results" %
                               (scheme, satellite_map[name]),
                               params={'scheduler_instance_id': 'XxX'}, verify=False)
            assert raw_data.status_code == 200
            data = raw_data.json()
            assert isinstance(data, list), "Data is not a list!"
        # -----

        # -----
        print("Testing signals")
        for name, proc in list(self.procs.items()):
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
        # -----

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
        for name, port in list(satellite_map.items()):
            raw_data = req.get("%s://localhost:%s/get_running_id" % (scheme, port), verify=False)
            print("Got (raw): %s" % raw_data)
            data = raw_data.json()
            assert "running_id" in data
            print("%s, my running id: %s" % (name, data['running_id']))
        # -----

        # -----
        # 2/ ask if have a configuration - must have one!
        print("--- have_conf")
        # Except Arbiter (not spare)
        for name, port in list(satellite_map.items()):
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
        for name, port in list(satellite_map.items()):
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
        for name, port in list(satellite_map.items()):
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
        for name, port in list(satellite_map.items()):
            if name in ['arbiter']:
                continue
            raw_data = req.get("%s://localhost:%s/stop_request?stop_now=" % (scheme, port),
                               params={'stop_now': False}, verify=False)
            data = raw_data.json()
            assert data is True

        time.sleep(2)
        print("Testing stop_request - tell the daemons they must stop now!")
        for name, port in list(satellite_map.items()):
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
        for name, port in list(satellite_map.items()):
            raw_data = req.get("http://localhost:%s/get_running_id" % port, verify=False)
            assert raw_data.status_code == 200
            print("Got (raw): %s" % raw_data)
            data = raw_data.json()
            assert "running_id" in data
            print("%s, my running id: %s" % (name, data['running_id']))
        # -----

        # -----
        # 2/ ask for a managed host.
        # The scheduler has a service to get an host information. This may be used to know if
        # an host exist in Alignak and to get its configuration and state

        # Only Scheduler daemon
        raw_data = req.get("http://localhost:7768/get_host?host_name=localhost", verify=False)
        assert raw_data.status_code == 200
        print("get_host, got (raw): %s" % raw_data)
        host = unserialize(raw_data.json(), True)
        print("Got: %s" % host)
        assert host.__class__ == Host
        assert host.get_name() == 'localhost'

        raw_data = req.get("http://localhost:7768/get_host?host_name=unknown_host", verify=False)
        assert raw_data.status_code == 200
        print("get_host, got (raw): %s" % raw_data)
        host = unserialize(raw_data.json(), True)
        print("Got: %s" % host)
        assert host is None

        # This function will only send a SIGTERM to the arbiter daemon
        self._stop_alignak_daemons(arbiter_only=True)

    def test_get_external_commands(self):
        """ Running all the Alignak daemons - get external commands

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
        for name, port in list(satellite_map.items()):
            raw_data = req.get("http://localhost:%s/get_running_id" % port, verify=False)
            assert raw_data.status_code == 200
            print("Got (raw): %s" % raw_data)
            data = raw_data.json()
            assert "running_id" in data
            print("%s, my running id: %s" % (name, data['running_id']))
        # -----

        # -----
        # 2/ notify an external command to the arbiter (as the receiver does).
        raw_data = req.post("http://localhost:7770/push_external_command",
                            data=json.dumps({'command': 'disable_notifications'}),
                            headers={'Content-Type': 'application/json'},
                            verify=False)
        print("push_external_commands, got (raw): %s" % (raw_data.content))
        assert raw_data.status_code == 200
        data = raw_data.json()
        print("Got: %s" % data)
        assert data['_status'] == 'OK'
        assert data['_message'] == 'Got command: DISABLE_NOTIFICATIONS'
        assert data['command'] == 'DISABLE_NOTIFICATIONS'

        raw_data = req.get("http://localhost:7770/get_external_commands")
        assert raw_data.status_code == 200
        print("%s get_external_commands, got (raw): %s" % (name, raw_data))
        data = raw_data.json()
        print("---Got: %s" % data)
        assert len(data) == 1
        assert 'creation_timestamp' in data[0]
        assert data[0]['cmd_line'] == 'DISABLE_NOTIFICATIONS'
        assert data[0]['my_type'] == 'externalcommand'

        # -----
        # 3/ notify an external command to the arbiter (WS interface).
        # For an host
        raw_data = req.post("http://localhost:7770/command",
                            data=json.dumps({
                                'command': 'disable_passive_host_checks',
                                'element': 'host_name',
                                'parameters': 'p1;p2;p3'
                            }),
                            headers={'Content-Type': 'application/json'},
                            verify=False)
        print("command, got (raw): %s" % (raw_data.content))
        assert raw_data.status_code == 200
        data = raw_data.json()
        print("Got: %s" % data)
        assert data['_status'] == 'OK'
        assert data['_message'] == 'Got command: DISABLE_PASSIVE_HOST_CHECKS;host_name;p1;p2;p3'
        assert data['command'] == 'DISABLE_PASSIVE_HOST_CHECKS;host_name;p1;p2;p3'

        raw_data = req.get("http://localhost:7770/get_external_commands")
        assert raw_data.status_code == 200
        print("%s get_external_commands, got (raw): %s" % (name, raw_data))
        data = raw_data.json()
        print("---Got: %s" % data)
        assert len(data) == 1
        assert 'creation_timestamp' in data[0]
        assert data[0]['cmd_line'] == 'DISABLE_PASSIVE_HOST_CHECKS;host_name;p1;p2;p3'
        assert data[0]['my_type'] == 'externalcommand'

        raw_data = req.post("http://localhost:7770/command",
                            data=json.dumps({
                                'command': 'test',
                                'host': 'host_name',
                                'parameters': 'p1;p2;p3'
                            }),
                            headers={'Content-Type': 'application/json'},
                            verify=False)
        assert raw_data.status_code == 200
        data = raw_data.json()
        assert data['_status'] == 'OK'
        assert data['_message'] == 'Got command: TEST;host_name;p1;p2;p3'
        assert data['command'] == 'TEST;host_name;p1;p2;p3'

        # For a service
        raw_data = req.post("http://localhost:7770/command",
                            data=json.dumps({
                                'command': 'test',
                                'element': 'host_name/service',
                                'parameters': 'p1;p2;p3'
                            }),
                            headers={'Content-Type': 'application/json'},
                            verify=False)
        assert raw_data.status_code == 200
        data = raw_data.json()
        assert data['_status'] == 'OK'
        assert data['_message'] == 'Got command: TEST;host_name;service;p1;p2;p3'
        assert data['command'] == 'TEST;host_name;service;p1;p2;p3'

        raw_data = req.post("http://localhost:7770/command",
                            data=json.dumps({
                                'command': 'test',
                                'host': 'host_name',
                                'service': 'service',
                                'parameters': 'p1;p2;p3'
                            }),
                            headers={'Content-Type': 'application/json'},
                            verify=False)
        assert raw_data.status_code == 200
        data = raw_data.json()
        assert data['_status'] == 'OK'
        assert data['_message'] == 'Got command: TEST;host_name;service;p1;p2;p3'
        assert data['command'] == 'TEST;host_name;service;p1;p2;p3'

        # For a user
        raw_data = req.post("http://localhost:7770/command",
                            data=json.dumps({
                                'command': 'test',
                                'element': 'user_name',
                                'parameters': 'p1;p2;p3'
                            }),
                            headers={'Content-Type': 'application/json'},
                            verify=False)
        assert raw_data.status_code == 200
        data = raw_data.json()
        assert data['_status'] == 'OK'
        assert data['_message'] == 'Got command: TEST;user_name;p1;p2;p3'
        assert data['command'] == 'TEST;user_name;p1;p2;p3'

        raw_data = req.post("http://localhost:7770/command",
                            data=json.dumps({
                                'command': 'test',
                                'user': 'user_name',
                                'parameters': 'p1;p2;p3'
                            }),
                            headers={'Content-Type': 'application/json'},
                            verify=False)
        assert raw_data.status_code == 200
        data = raw_data.json()
        assert data['_status'] == 'OK'
        assert data['_message'] == 'Got command: TEST;user_name;p1;p2;p3'
        assert data['command'] == 'TEST;user_name;p1;p2;p3'

        time.sleep(5)

        # -----
        # Get external commands from all the daemons
        for name, port in list(satellite_map.items()):
            raw_data = req.get("http://localhost:%s/get_external_commands" % port, verify=False)
            assert raw_data.status_code == 200
            print("%s get_external_commands, got (raw): %s" % (name, raw_data))
            data = raw_data.json()
            print("Got: %s" % data)
            # External commands got consumed by the daemons - not always all !
            # May be 0 but it seems that 5 are remaining
            assert len(data) == 5
            # if name in 'arbiter':
            #     #         e = [
            #     #             {'my_type': 'externalcommand', 'cmd_line': 'TEST;host_name;service;p1;p2;p3', 'creation_timestamp': 1526479441.683431},
            #     #             {'my_type': 'externalcommand', 'cmd_line': 'TEST;user_name;p1;p2;p3', 'creation_timestamp': 1526479441.689507},
            #     #             {'my_type': 'externalcommand', 'cmd_line': 'TEST;user_name;p1;p2;p3', 'creation_timestamp': 1526479441.695691}
            #     #         ]
            #
            #     assert 'creation_timestamp' in data[0]
            #     assert data[0]['cmd_line'] == 'TEST;host_name;p1;p2;p3'
            #     assert data[0]['my_type'] == 'externalcommand'
            #     assert 'creation_timestamp' in data[1]
            #     assert data[1]['cmd_line'] == 'TEST;host_name;p1;p2;p3'
            #     assert data[1]['my_type'] == 'externalcommand'
            #     assert 'creation_timestamp' in data[2]
            #     assert data[2]['cmd_line'] == 'TEST;host_name;p1;p2;p3'
            #     assert data[2]['my_type'] == 'externalcommand'
            #     assert 'creation_timestamp' in data[3]
            #     assert data[3]['cmd_line'] == 'TEST;host_name;service;p1;p2;p3'
            #     assert data[3]['my_type'] == 'externalcommand'
            #     assert 'creation_timestamp' in data[4]
            #     assert data[4]['cmd_line'] == 'TEST;host_name;service;p1;p2;p3'
            #     assert data[4]['my_type'] == 'externalcommand'
            #     assert 'creation_timestamp' in data[5]
            #     assert data[5]['cmd_line'] == 'TEST;user_name;p1;p2;p3'
            #     assert data[5]['my_type'] == 'externalcommand'
            #     assert 'creation_timestamp' in data[6]
            #     assert data[6]['cmd_line'] == 'TEST;user_name;p1;p2;p3'
            #     assert data[6]['my_type'] == 'externalcommand'

        # This function will only send a SIGTERM to the arbiter daemon
        self._stop_alignak_daemons(arbiter_only=True)

    def test_get_stats(self):
        """ Running all the Alignak daemons - get daemons statistics

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

        # -----
        # 1/ get the running identifier (confirm the daemon is running)
        print("--- get_running_id")
        for name, port in list(satellite_map.items()):
            raw_data = req.get("http://localhost:%s/get_running_id" % port, verify=False)
            assert raw_data.status_code == 200
            print("Got (raw): %s" % raw_data)
            data = raw_data.json()
            assert "running_id" in data
            print("%s, my running id: %s" % (name, data['running_id']))
        # -----

        # -----
        # 2/ get the daemons statistics
        print("--- get_stats")
        for name, port in list(satellite_map.items()):
            print("- for %s" % (name))
            raw_data = req.get("http://localhost:%s/get_stats" % port, verify=False)
            print("%s, my stats: %s" % (name, raw_data.text))
            assert raw_data.status_code == 200
            data = raw_data.json()
            print("%s, my stats: %s" % (name, json.dumps(data)))

            # Same as start_time
            assert 'alignak' in data
            assert 'type' in data
            assert 'name' in data
            assert 'version' in data
            assert 'start_time' in data
            # +
            assert "program_start" in data
            assert "load" in data
            assert "metrics" in data    # To be deprecated...
            assert "modules" in data
            assert "counters" in data

            if name in ['arbiter']:
                assert "livestate" in data
                livestate = data['livestate']
                assert "timestamp" in livestate
                assert "state" in livestate
                assert "output" in livestate
                assert "daemons" in livestate
                for daemon_state in livestate['daemons']:
                    assert livestate['daemons'][daemon_state] == 0

                assert "daemons_states" in data
                daemons_state = data['daemons_states']
                for daemon_name in daemons_state:
                    daemon_state = daemons_state[daemon_name]
                    assert "type" in daemon_state
                    assert "name" in daemon_state
                    assert "realm_name" in daemon_state
                    assert "manage_sub_realms" in daemon_state
                    assert "uri" in daemon_state
                    assert "alive" in daemon_state
                    assert "passive" in daemon_state
                    assert "reachable" in daemon_state
                    assert "active" in daemon_state
                    assert "spare" in daemon_state
                    assert "polling_interval" in daemon_state
                    assert "configuration_sent" in daemon_state
                    assert "max_check_attempts" in daemon_state
                    assert "last_check" in daemon_state
                    assert "livestate" in daemon_state
                    assert "livestate_output" in daemon_state

        time.sleep(5)

        # -----
        # 3/ once again, get the daemons statistics
        print("--- get_stats")
        for name, port in list(satellite_map.items()):
            print("- for %s" % (name))
            raw_data = req.get("http://localhost:%s/get_stats" % port, verify=False)
            print("%s, my stats: %s" % (name, raw_data.text))
            assert raw_data.status_code == 200
            data = raw_data.json()
            print("%s, my stats: %s" % (name, json.dumps(data)))

            # Same as start_time
            assert 'alignak' in data
            assert 'type' in data
            assert 'name' in data
            assert 'version' in data
            assert 'start_time' in data
            # +
            assert "program_start" in data
            assert "load" in data
            assert "metrics" in data    # To be deprecated...
            assert "modules" in data
            assert "counters" in data

            if name in ['arbiter']:
                assert "livestate" in data
                livestate = data['livestate']
                assert "timestamp" in livestate
                assert "state" in livestate
                assert "output" in livestate
                assert "daemons" in livestate
                for daemon_state in livestate['daemons']:
                    assert livestate['daemons'][daemon_state] == 0

                assert "daemons_states" in data
                daemons_state = data['daemons_states']
                for daemon_name in daemons_state:
                    daemon_state = daemons_state[daemon_name]
                    assert "type" in daemon_state
                    assert "name" in daemon_state
                    assert "realm_name" in daemon_state
                    assert "manage_sub_realms" in daemon_state
                    assert "uri" in daemon_state
                    assert "alive" in daemon_state
                    assert "passive" in daemon_state
                    assert "reachable" in daemon_state
                    assert "active" in daemon_state
                    assert "spare" in daemon_state
                    assert "polling_interval" in daemon_state
                    assert "configuration_sent" in daemon_state
                    assert "max_check_attempts" in daemon_state
                    assert "last_check" in daemon_state
                    assert "livestate" in daemon_state
                    assert "livestate_output" in daemon_state

        # This function will only send a SIGTERM to the arbiter daemon
        self._stop_alignak_daemons(arbiter_only=True)
