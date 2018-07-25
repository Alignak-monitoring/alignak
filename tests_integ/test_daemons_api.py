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

from pprint import pprint

import subprocess
from time import sleep
import requests
import shutil
import psutil
import configparser

import pytest
from .alignak_test import AlignakTest

from alignak.misc.serialization import unserialize
from alignak.objects.host import Host
from alignak.objects.hostgroup import Hostgroup, Hostgroups
from alignak.objects.service import Service
from alignak.objects.realm import Realm
from alignak.http.generic_interface import GenericInterface
from alignak.http.arbiter_interface import ArbiterInterface
from alignak.http.scheduler_interface import SchedulerInterface
from alignak.http.broker_interface import BrokerInterface
from alignak.log import set_log_level


class TestDaemonsApi(AlignakTest):
    """Test the daemons HTTP API"""
    def setUp(self):
        # Set an environment variable to change the default period of activity log (every 60 loops)
        os.environ['ALIGNAK_LOG_ACTIVITY'] = '1'

        # Set an environment variable to activate the logging of system cpu, memory and disk
        os.environ['ALIGNAK_DAEMON_MONITORING'] = '2'

        # Set an environment variable to activate the logging of checks execution
        # With this the pollers/schedulers will raise INFO logs about the checks execution
        os.environ['ALIGNAK_LOG_ACTIONS'] = 'WARNING'

        super(TestDaemonsApi, self).setUp()

    def tearDown(self):
        del os.environ['ALIGNAK_LOG_ACTIVITY']
        del os.environ['ALIGNAK_DAEMON_MONITORING']
        del os.environ['ALIGNAK_LOG_ACTIONS']

        print("Test terminated!")

    def _prepare_my_configuration(self, daemons_list=None, remove_daemons=None,
                                  cfg_dir=None, realms=None):
        self.cfg_folder = '/tmp/alignak'
        if os.path.exists(self.cfg_folder):
            shutil.rmtree(self.cfg_folder)
        if realms is None:
            realms = ['All']
        if cfg_dir is None:
            cfg_dir = 'default_many_hosts'
        hosts_count = 10
        if remove_daemons is None:
            remove_daemons = []
        if daemons_list is None:
            daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                            'receiver-master', 'scheduler-master']

        # Default shipped configuration preparation
        self._prepare_configuration(copy=True, cfg_folder=self.cfg_folder)

        # Specific daemon load configuration preparation
        if os.path.exists('./cfg/%s/alignak.cfg' % cfg_dir):
            shutil.copy('./cfg/%s/alignak.cfg' % cfg_dir, '%s/etc' % self.cfg_folder)
        if os.path.exists('%s/etc/arbiter' % self.cfg_folder):
            shutil.rmtree('%s/etc/arbiter' % self.cfg_folder)
        shutil.copytree('./cfg/%s/arbiter' % cfg_dir, '%s/etc/arbiter' % self.cfg_folder)

        self._prepare_hosts_configuration(cfg_folder='%s/etc/arbiter/objects/hosts' % self.cfg_folder,
                                          hosts_count=hosts_count, target_file_name='hosts.cfg',
                                          realms=realms)

        # Some script commands must be copied in the test folder
        if os.path.exists('./libexec/check_command.sh'):
            shutil.copy('./libexec/check_command.sh', '%s/check_command.sh' % self.cfg_folder)

        # Update the default configuration files
        files = ['%s/etc/alignak.ini' % self.cfg_folder]
        try:
            cfg = configparser.ConfigParser()
            cfg.read(files)

            cfg.set('alignak-configuration', 'launch_missing_daemons', '1')

            cfg.set('alignak-configuration', 'daemons_check_period', '5')
            cfg.set('alignak-configuration', 'daemons_stop_timeout', '3')
            cfg.set('alignak-configuration', 'daemons_start_timeout', '1')
            cfg.set('alignak-configuration', 'daemons_new_conf_timeout', '1')
            cfg.set('alignak-configuration', 'daemons_dispatch_timeout', '1')
            cfg.set('alignak-configuration', 'min_workers', '1')
            cfg.set('alignak-configuration', 'max_workers', '1')

            cfg.set('alignak-configuration', 'log_cherrypy', '1')

            # A macro for the check script directory
            cfg.set('alignak-configuration', '_EXEC_DIR', self.cfg_folder)

            for daemon in daemons_list:
                if cfg.has_section('daemon.%s' % daemon):
                    cfg.set('daemon.%s' % daemon, 'alignak_launched', '1')
            for daemon in remove_daemons:
                if cfg.has_section('daemon.%s' % daemon):
                    print("Remove daemon: %s" % daemon)
                    cfg.remove_section('daemon.%s' % daemon)

            if os.path.exists('%s/etc/alignak.d' % self.cfg_folder):
                print("- removing %s/etc/alignak.d" % self.cfg_folder)
                shutil.rmtree('%s/etc/alignak.d' % self.cfg_folder)

            with open('%s/etc/alignak.ini' % self.cfg_folder, "w") as modified:
                cfg.write(modified)
        except Exception as exp:
            print("* parsing error in config file: %s" % exp)
            assert False

    def test_daemons_api_no_ssl(self):
        """ Running all the Alignak daemons - no SSL

        :return:
        """
        self._prepare_my_configuration()
        self._run_daemons_and_test_api(ssl=False)

    @pytest.mark.skip("See #986 - SSL is broken with test files!")
    def test_daemons_api_ssl(self):
        """ Running all the Alignak daemons - with SSL

        :return: None
        """
        # disable ssl warning
        # requests.packages.urllib3.disable_warnings()

        self._prepare_my_configuration()

        # Update the default configuration files
        files = ['%s/etc/alignak.ini' % self.cfg_folder]
        try:
            cfg = configparser.ConfigParser()
            cfg.read(files)

            cfg.set('alignak-configuration', 'use_ssl', '1')

            cfg.set('alignak-configuration', 'server_cert', '%s/etc/certs/certificate_test.csr' % self.cfg_folder)
            cfg.set('alignak-configuration', 'server_key', '%s/etc/certs/certificate_test.key' % self.cfg_folder)
            # cfg.set('alignak-configuration', 'ca_cert', '%s/etc/certs/dhparams.pem' % self.cfg_folder)

            with open('%s/etc/alignak.ini' % self.cfg_folder, "w") as modified:
                cfg.write(modified)
        except Exception as exp:
            print("* parsing error in config file: %s" % exp)
            assert False

        self._run_daemons_and_test_api(ssl=True)

    def _run_daemons_and_test_api(self, ssl=False):
        """ Running all the Alignak daemons to check their correct launch and API responses

        This test concerns only the main API features ...

        :return:
        """
        satellite_map = {
            'arbiter': '7770', 'scheduler': '7768', 'broker': '7772',
            'poller': '7771', 'reactionner': '7769', 'receiver': '7773'
        }

        daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                        'receiver-master', 'scheduler-master']

        self._run_alignak_daemons(cfg_folder=self.cfg_folder,
                                  daemons_list=daemons_list, runtime=5)

        scheme = 'http'
        if ssl:
            scheme = 'https'

        req = requests.Session()

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
        doc.append("")
        for name in sorted(satellite_map):
            port = satellite_map[name]
            print("%s, getting api..." % name)
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

            # expected_data = set(name_to_interface[name](None).api())
            # assert set(data) == expected_data, "Daemon %s has a bad API!" % name
        print('\n'.join(doc))

        rst_write = None
        rst_file = "daemons_api.rst"
        if os.path.exists("../doc/source/api"):
            rst_write = "../doc/source/api/%s" % rst_file
        if os.path.exists("../../alignak-doc/source/07_alignak_features/api"):
            rst_write = "../../alignak-doc/source/07_alignak_features/api/%s" % rst_file
        if rst_write:
            # with open(rst_write, mode='wt', encoding='utf-8') as out:
            with open(rst_write, mode='wt') as out:
                out.write('\n'.join(doc))
        # -----

        # -----
        print("Testing identity")
        for name, port in list(satellite_map.items()):
            raw_data = req.get("%s://localhost:%s/identity" % (scheme, port), verify=False)
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
            assert 'start_time' in data
            # +
            assert 'running_id' in data
        # -----

        # -----
        print("Testing satellites_list")
        # Arbiter only
        raw_data = req.get("%s://localhost:%s/satellites_list" %
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
        print("Testing alignak status")
        # Arbiter only
        raw_data = req.get("%s://localhost:%s/status" %
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
            with open(rst_write, mode='wt') as out:
            # with open(rst_write, mode='wt', encoding='utf-8') as out:
                out.write('\n'.join(doc))
        # -----

        # -----
        print("Testing stats")

        doc = []
        doc.append(".. _alignak_features/daemons_stats:")
        doc.append(".. Built from the test_daemons_api.py unit test last run!")
        doc.append("")
        doc.append("==========================")
        doc.append("Alignak daemons statistics")
        doc.append("==========================")
        for name, port in list(satellite_map.items()):
            print("- for %s" % (name))
            raw_data = req.get("%s://localhost:%s/stats" % (scheme, port), verify=False)
            print("Got /stats: %s" % raw_data.content)
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
                print("Livestate: %s" % livestate)
                l = {
                    'daemons': {'reactionner-master': 1, 'poller-master': 1, 'broker-master': 1,
                                'receiver-master': 1, 'scheduler-master': 1},
                    'state': 1, 'timestamp': 1531487166,
                    'output': 'warning because some daemons are not reachable.'}
                assert "timestamp" in livestate
                assert "state" in livestate
                assert "output" in livestate
                assert "daemons" in livestate
                for daemon_state in livestate['daemons']:
                    assert livestate['daemons'][daemon_state] == 0
                    # assert daemon_state in satellite_map.keys()

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
            # with open(rst_write, mode='wt', encoding='utf-8') as out:
            with open(rst_write, mode='wt') as out:
                out.write('\n'.join(doc))

        print("Testing stats (detailed)")
        for name, port in list(satellite_map.items()):
            print("- for %s" % (name))
            raw_data = req.get("%s://localhost:%s/stats?details=1" % (scheme, port), verify=False)
            print("Got /stats?details=1: %s" % raw_data.content)
            assert raw_data.status_code == 200
            # print("%s, my stats: %s" % (name, raw_data.text))
            data = raw_data.json()
            print("%s, my stats (detailed): %s" % (name, json.dumps(data)))
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
            raw_data = req.get("%s://localhost:%s/_have_conf" % (scheme, satellite_map[daemon]), verify=False)
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
        raw_data = req.get("%s://localhost:%s/_do_not_run" %
                           (scheme, satellite_map['arbiter']), verify=False)
        assert raw_data.status_code == 200
        data = raw_data.json()
        print("%s, do_not_run: %s" % (name, data))
        # Arbiter master returns False, spare returns True
        assert data == {'_message': 'Received message to not run. I am the Master arbiter, '
                                    'ignore and continue to run.', '_status': 'ERR'}
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
        print("Testing managed_configurations")
        for name, port in list(satellite_map.items()):
            print("%s, what I manage?" % (name))
            raw_data = req.get("%s://localhost:%s/managed_configurations" % (scheme, port), verify=False)
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
        print("Testing _external_commands")
        for name, port in list(satellite_map.items()):
            raw_data = req.get("%s://localhost:%s/_external_commands" % (scheme, port), verify=False)
            assert raw_data.status_code == 200
            print("%s _external_commands, got (raw): %s" % (name, raw_data.content))
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
            # Initially forced the INFO log level
            assert data['log_level'] == 20
            assert data['log_level_name'] == 'INFO'

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
            # if name in ['arbiter']:
            #     continue
            raw_data = req.get("%s://localhost:%s/get_log_level" % (scheme, port), verify=False)
            data = raw_data.json()
            print("%s, log level: %s" % (name, data))
            assert data['log_level'] == 10

        print("Resetting log level")
        for name, port in list(satellite_map.items()):
            raw_data = req.post("%s://localhost:%s/set_log_level" % (scheme, port),
                                data=json.dumps({'log_level': 'INFO'}),
                                headers={'Content-Type': 'application/json'},
                                verify=False)
            print("%s, raw_data: %s" % (name, raw_data.text))
            data = raw_data.json()
            print("%s, log level set as : %s" % (name, data))
            assert data['log_level'] == 20
            assert data['log_level_name'] == 'INFO'
        # -----

        # -----
        print("Testing satellites_configuration")
        # Arbiter only
        raw_data = req.get("%s://localhost:%s/satellites_configuration" %
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
        print("Testing _initial_broks")
        # Scheduler only
        raw_data = req.get("%s://localhost:%s/_initial_broks" %
                           (scheme, satellite_map['scheduler']),
                           params={'broker_name': 'broker-master'}, verify=False)
        assert raw_data.status_code == 200
        print("_initial_broks, raw_data: %s" % (raw_data.text))
        data = raw_data.json()
        assert data == 0, "Data must be 0 - no broks!"
        # -----

        # -----
        print("Testing _broks")
        # All except the arbiter and the broker itself!
        for name, port in list(satellite_map.items()):
            if name in ['arbiter', 'broker']:
                continue
            raw_data = req.get("%s://localhost:%s/_broks" % (scheme, port),
                               params={'broker_name': 'broker-master'}, verify=False)
            assert raw_data.status_code == 200
            print("%s, get_broks raw_data: %s" % (name, raw_data.text))
            data = raw_data.json()
            print("%s, broks: %s" % (name, data))
            assert isinstance(data, list), "Data is not a list!"
        # -----

        # -----
        print("Testing _events")
        # All except the arbiter and the broker itself!
        for name, port in list(satellite_map.items()):
            if name in ['arbiter', 'broker']:
                continue
            raw_data = req.get("%s://localhost:%s/_events" % (scheme, port),
                               verify=False)
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
            raw_data = req.get("%s://localhost:%s/_results" %
                               (scheme, satellite_map[name]),
                               params={'scheduler_instance_id': 'XxX'}, verify=False)
            assert raw_data.status_code == 200
            print("%s, get_returns raw_data: %s" % (name, raw_data.text))
            data = raw_data.json()
            assert isinstance(data, list), "Data is not a list!"

        for name in ['poller']:
            raw_data = req.get("%s://localhost:%s/_results" %
                               (scheme, satellite_map[name]),
                               params={'scheduler_instance_id': 'XxX'}, verify=False)
            assert raw_data.status_code == 200
            data = raw_data.json()
            assert isinstance(data, list), "Data is not a list!"
        # -----

        # -----
        print("Testing signals")
        daemon_count = 0
        for daemon in ['broker', 'poller', 'reactionner', 'receiver', 'scheduler', 'arbiter']:
            for proc in psutil.process_iter():
                if 'alignak' in proc.name() and daemon in proc.name():
                    # SIGUSR1: memory dump
                    print("%s, send signal SIGUSR1" % (name))
                    proc.send_signal(signal.SIGUSR1)
                    time.sleep(1.0)
                    # SIGUSR2: objects dump
                    print("%s, send signal SIGUSR2" % (name))
                    proc.send_signal(signal.SIGUSR2)
                    time.sleep(1.0)
                    # SIGHUP: reload configuration
                    # proc.send_signal(signal.SIGHUP)
                    # time.sleep(1.0)
                    # Other signals is considered as a request to stop...
                    daemon_count += 1
        # 14 because all the daemons are forked at least once ;)
        # todo: The test strategy should be updated to send signals only to the concerned daemons!
        # assert daemon_count == 14
        # -----

        # # This function will only send a SIGTERM to the arbiter daemon
        # self._stop_alignak_daemons(arbiter_only=True)
        #
        # The arbiter daemon will then request its satellites to stop...
        # this is the same as the following code:
        print("Testing stop_request - tell the daemons we will stop soon...")
        for name, port in satellite_map.items():
            if name in ['arbiter']:
                continue
            raw_data = req.get("%s://localhost:%s/stop_request?stop_now=0" % (scheme, port),
                               params={'stop_now': False}, verify=False)
            data = raw_data.json()
            assert data is True

        time.sleep(2)
        print("Testing stop_request - tell the daemons they must stop now!")
        for name, port in satellite_map.items():
            if name in ['arbiter']:
                continue
            raw_data = req.get("%s://localhost:%s/stop_request?stop_now=1" % (scheme, port),
                               params={'stop_now': True}, verify=False)
            data = raw_data.json()
            assert data is True

    def test_daemons_configuration(self):
        """ Running all the Alignak daemons to check their correct configuration

        Tests for the configuration dispatch API

        :return:
        """
        self._prepare_my_configuration()
        self._run_daemons_and_configure(ssl=False)

    def test_daemons_configuration_no_receiver(self):
        """ Running all the Alignak daemons to check their correct configuration

        Do not include any receiver in the daemons list

        :return:
        """
        daemons_list=['broker-master', 'poller-master', 'reactionner-master', 'scheduler-master']
        self._prepare_my_configuration(daemons_list=daemons_list,
                                       remove_daemons=['receiver-master'])
        self._run_daemons_and_configure(ssl=False, daemons_list=daemons_list)

    def _run_daemons_and_configure(self, ssl=False, daemons_list=None):
        """ Running all the Alignak daemons to check their correct launch and API

        Tests for the configuration dispatch API

        :return:
        """
        full_satellite_map = {
            'arbiter': '7770', 'scheduler': '7768', 'broker': '7772',
            'poller': '7771', 'reactionner': '7769', 'receiver': '7773'
        }

        if daemons_list is None:
            daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                            'receiver-master', 'scheduler-master']

        satellite_map = {'arbiter': '7770'}
        for sat in full_satellite_map:
            if "%s-master" % sat in daemons_list:
                satellite_map[sat] = full_satellite_map[sat]

        print("Satellites map: %s" % satellite_map)
        self._run_alignak_daemons(cfg_folder=self.cfg_folder, daemons_list=daemons_list, runtime=5,
                                  update_configuration=False)

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
            raw_data = req.get("%s://localhost:%s/identity" % (scheme, port), verify=False)
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
            raw_data = req.get("%s://localhost:%s/_have_conf" % (scheme, port), verify=False)
            print("have_conf %s, got (raw): %s" % (name, raw_data))
            data = raw_data.json()
            print("%s, have_conf: %s" % (name, data))
            assert data == True, "Daemon %s should have a conf!" % name

        # -----
        # 3/ ask to wait for a new configuration
        print("--- wait_new_conf")
        for name, port in list(satellite_map.items()):
            if name == 'arbiter-master':
                continue
            raw_data = req.get("%s://localhost:%s/_wait_new_conf" % (scheme, port), verify=False)
            print("wait_new_conf %s, got (raw): %s" % (name, raw_data))
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
            raw_data = req.get("%s://localhost:%s/_have_conf" % (scheme, port), verify=False)
            print("have_conf %s, got (raw): %s" % (name, raw_data))
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

    def test_get_objects_from_scheduler(self):
        """ Running all the Alignak daemons - get host and other objects
        from the scheduler

        :return:
        """
        self._prepare_my_configuration()
        self._get_objects('http://localhost:7768')

    def test_get_objects_from_arbiter(self):
        """ Running all the Alignak daemons - get host and other objects
        from the arbiter

        :return:
        """
        self._prepare_my_configuration()
        self._get_objects('http://localhost:7770')

    def _get_objects(self, endpoint):
        """ Running all the Alignak daemons - get host and other objects
        from the scheduler or from the arbiter

        :return:
        """
        cfg_folder = '/tmp/alignak'
        cfg_dir = 'default_many_hosts'
        hosts_count = 10
        daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                        'receiver-master', 'scheduler-master']
        satellite_map = {
            'arbiter': '7770', 'scheduler': '7768', 'broker': '7772',
            'poller': '7771', 'reactionner': '7769', 'receiver': '7773'
        }

        # Default shipped configuration preparation
        self._prepare_configuration(copy=True, cfg_folder=cfg_folder)

        # Specific daemon load configuration preparation
        if os.path.exists('./cfg/%s/alignak.cfg' % cfg_dir):
            shutil.copy('./cfg/%s/alignak.cfg' % cfg_dir, '%s/etc' % cfg_folder)
        if os.path.exists('%s/etc/arbiter' % cfg_folder):
            shutil.rmtree('%s/etc/arbiter' % cfg_folder)
        shutil.copytree('./cfg/%s/arbiter' % cfg_dir, '%s/etc/arbiter' % cfg_folder)

        self._prepare_hosts_configuration(cfg_folder='%s/etc/arbiter/objects/hosts' % cfg_folder,
                                          hosts_count=hosts_count, target_file_name='hosts.cfg')

        # Some script commands must be copied in the test folder
        if os.path.exists('./libexec/check_command.sh'):
            shutil.copy('./libexec/check_command.sh', '%s/check_command.sh' % cfg_folder)

        # Update the default configuration files
        files = ['%s/etc/alignak.ini' % cfg_folder]
        try:
            cfg = configparser.ConfigParser()
            cfg.read(files)

            cfg.set('alignak-configuration', 'launch_missing_daemons', '1')

            # cfg.set('alignak-configuration', 'daemons_start_timeout', '15')
            # cfg.set('alignak-configuration', 'daemons_dispatch_timeout', '15')
            #
            # A macro for the check script directory
            cfg.set('alignak-configuration', '_EXEC_DIR', cfg_folder)
            for daemon in daemons_list:
                if cfg.has_section('daemon.%s' % daemon):
                    cfg.set('daemon.%s' % daemon, 'alignak_launched', '1')

            with open('%s/etc/alignak.ini' % cfg_folder, "w") as modified:
                cfg.write(modified)
        except Exception as exp:
            print("* parsing error in config file: %s" % exp)
            assert False

        # Run daemons for the required duration
        self._run_alignak_daemons(cfg_folder='/tmp/alignak',
                                  daemons_list=daemons_list,
                                  run_folder='/tmp/alignak', runtime=5,
                                  # verbose=True
                                  )

        # Here the daemons got started by the arbiter and the arbiter dispatched a configuration
        # We will ask to wait for a new configuration

        # -----
        # 1/ get the running identifier (confirm the daemon is running)
        req = requests.Session()
        print("--- get_running_id")
        for name, port in list(satellite_map.items()):
            raw_data = req.get("http://localhost:%s/identity" % port, verify=False)
            assert raw_data.status_code == 200
            data = raw_data.json()
            assert "running_id" in data
            print("%s, my running id: %s" % (name, data['running_id']))
        # -----

        # -----
        # 2/ ask for a managed host.
        # The scheduler has a service to get some objects information. This may be used to know if
        # an host exist in Alignak and to get its configuration and state

        # Only for the scheduler and arbiter daemons

        # ---
        # Get an unknown type object
        # Query parameter
        raw_data = req.get("%s/object?o_type=unknown" % endpoint)
        print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
        assert raw_data.status_code == 200
        object = unserialize(raw_data.json(), True)
        # => error message
        assert object == {'_message': 'Required unknown not found.', '_status': 'ERR'}

        # Get an unknown object
        # Query parameter
        raw_data = req.get("%s/object?o_type=realm&o_name=unknown_realm" % endpoint)
        print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
        assert raw_data.status_code == 200
        object = unserialize(raw_data.json(), True)
        assert object == {'_message': 'Required realm not found.', '_status': 'ERR'}

        # Get an unknown realm
        raw_data = req.get("%s/object/realm/unknown_realm" % endpoint)
        print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
        assert raw_data.status_code == 200
        object = unserialize(raw_data.json(), True)
        assert object == {'_message': 'Required realm not found.', '_status': 'ERR'}

        # Get an unknown realm - case sensitivity!
        raw_data = req.get("%s/object/realm/all" % endpoint)
        print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
        assert raw_data.status_code == 200
        object = unserialize(raw_data.json(), True)
        assert object == {'_message': 'Required realm not found.', '_status': 'ERR'}

        # Get a known realm
        raw_data = req.get("%s/object/realm/All" % endpoint)
        print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
        assert raw_data.status_code == 200
        # # It should be this:
        # object = raw_data.json()
        # object = object['content']
        # print("Got object: %s" % object['realm_name'])
        # assert object['realm_name'] == 'All'
        # # but the scheduler seem to not have received any realm !
        # # todo: investigate this!

        # Get a known host
        raw_data = req.get("%s/object/host/localhost" % endpoint)
        print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
        assert raw_data.status_code == 200
        object = raw_data.json()
        print("Got object: %s" % object['content']['host_name'])
        assert object['content']['host_name'] == 'localhost'

        # Get a known host from its uuid
        raw_data = req.get("%s/object/host/%s" % (endpoint, object['content']['uuid']))
        print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
        assert raw_data.status_code == 200
        object = raw_data.json()
        print("Got object: %s" % object['content']['host_name'])
        assert object['content']['host_name'] == 'localhost'

        # ---
        # Get all hostgroups
        raw_data = req.get("%s/object/hostgroup" % endpoint)
        print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
        assert raw_data.status_code == 200
        object = raw_data.json()
        groups = unserialize(object, True)
        assert groups.__class__ == Hostgroups
        for group in groups:
            print("Group: %s" % group.get_name())
            assert group.__class__ == Hostgroup

        # ---
        # Get a hostgroup
        raw_data = req.get("%s/object/hostgroup/allhosts" % endpoint)
        print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
        assert raw_data.status_code == 200
        object = raw_data.json()
        print("Got hostgroup: %s / %s" % (type(object), object['content']['hostgroup_name']))
        assert object['content']['hostgroup_name'] == 'allhosts'
        group = unserialize(object, True)
        assert group.__class__ == Hostgroup
        assert group.get_name() == 'allhosts'

        # ---
        # Get all hosts from the hostgroup
        for m in group.members:
            raw_data = req.get("%s/object/host/%s" % (endpoint, m))
            print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
            assert raw_data.status_code == 200
            member = raw_data.json()
            group_host = unserialize(member, True)
            assert group_host.__class__ == Host
            print("- group member: %s" % group_host.get_name())

            # ---
            # Get all the services from the host
            for s in group_host.child_dependencies:
                print("Get host: %s/%s" % (group_host.get_name(), s))
                raw_data = req.get("%s/object/service/%s" % (endpoint, s))
                print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
                assert raw_data.status_code == 200
                member = raw_data.json()
                host_service = unserialize(member, True)
                assert host_service.__class__ == Service
                print("  . service: %s" % host_service.get_full_name())

        # ---
        # Get some host dump (raw mode will return a list of CSV text strings with a header line)
        raw_data = req.get("%s/dump?raw=1" % endpoint)
        print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
        assert raw_data.status_code == 200
        res = raw_data.json()
        print("Got raw hosts dump %s: %s / %s" % (endpoint, type(res), res))
        if endpoint == 'http://localhost:7770':
            # Arbiter groups data in a schedulers dict ...
            for sched in res:
                print("Scheduler: %s" % sched)
                sched = res[sched]
                # First list item is for hosts
                hosts_list = sched[0]
                print(hosts_list)
                print(hosts_list[0])
                print(hosts_list[1])
                assert hosts_list[0] == 'type;host;name;last_check;state_id;state;state_type;is_problem;is_impact;output'
                # Second list item is for services
                services_list = sched[1]
                print(services_list[0])
                print(services_list[1])
                # Only type;host;name
                assert services_list[0] in ['type;host;name', 'type;host;name;last_check;state_id;state;state_type;is_problem;is_impact;output']
        else:
            assert len(res) == 2
            # First list item is for hosts
            hosts_list = res[0]
            print(hosts_list[0])
            print(hosts_list[1])
            assert 'type;host;name;last_check;state_id;state;state_type;is_problem;is_impact;output' == hosts_list[0]
            # Second list item is for services
            services_list = res[1]
            print(services_list[0])
            print(services_list[1])
            assert 'type;host;name;last_check;state_id;state;state_type;is_problem;is_impact;output' == services_list[0]


        # With more details
        raw_data = req.get("%s/dump?raw=1&details=1" % endpoint)
        print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
        assert raw_data.status_code == 200
        res = raw_data.json()
        print("Got raw detailed hosts dump (%s): %s / %s" % (endpoint, type(res), res))
        if endpoint == 'http://localhost:7770':
            # Arbiter groups data in a schedulers dict ...
            for sched in res:
                print("Scheduler: %s" % sched)
                sched = res[sched]
                # First list item is for hosts
                hosts_list = sched[0]
                print(hosts_list[0])
                print(hosts_list[1])
                assert hosts_list[0].startswith('type;host;name;last_check;state_id;state;state_type;is_problem;is_impact;output;uuid')
                # Second list item is for services
                services_list = sched[1]
                print(services_list[0])
                print(services_list[1])
                assert services_list[0].startswith('type;host;name;last_check;state_id;state;state_type;is_problem;is_impact;output;uuid')
        else:
            assert len(res) == 2
            # First list item is for hosts
            hosts_list = res[0]
            print(hosts_list[0])
            print(hosts_list[1])
            assert hosts_list[0].startswith('type;host;name;last_check;state_id;state;state_type;is_problem;is_impact;output;uuid')
            # Second list item is for services
            services_list = res[1]
            print(services_list[0])
            print(services_list[1])
            assert services_list[0].startswith('type;host;name;last_check;state_id;state;state_type;is_problem;is_impact;output;uuid')

        # Get some host dump, json mode
        raw_data = req.get("%s/dump" % endpoint)
        print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
        assert raw_data.status_code == 200
        res = raw_data.json()
        print("Got hosts dump: %s / %s" % (type(res), res))
        if endpoint == 'http://localhost:7770':
            # Arbiter groups data in a schedulers dict ...
            for sched in res:
                print("Scheduler: %s" % sched)
                hosts_list = res[sched]
                assert len(hosts_list) > 1
                for host in hosts_list:
                    assert 'name' in host
                    assert 'last_check' in host
                    assert 'state_id' in host
                    assert 'state_type' in host
                    assert 'state' in host
                    assert 'output' in host
                    assert 'is_problem' in host
                    assert 'is_impact' in host
                    assert 'services' in host
        else:
            hosts_list = res
            assert len(hosts_list) > 1
            for host in hosts_list:
                assert 'name' in host
                assert 'last_check' in host
                assert 'state_id' in host
                assert 'state_type' in host
                assert 'state' in host
                assert 'output' in host
                assert 'is_problem' in host
                assert 'is_impact' in host
                assert 'services' in host

        # With more details
        raw_data = req.get("%s/dump?details=1" % endpoint)
        print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
        assert raw_data.status_code == 200
        res = raw_data.json()
        print("Got hosts dump: %s / %s" % (type(res), res))
        if endpoint == 'http://localhost:7770':
            # Arbiter groups data in a schedulers dict ...
            for sched in res:
                print("Scheduler: %s" % sched)
                hosts_list = res[sched]
                assert len(hosts_list) > 1
                for host in hosts_list:
                    assert 'name' in host
                    assert 'last_check' in host
                    assert 'state_id' in host
                    assert 'state_type' in host
                    assert 'state' in host
                    assert 'output' in host
                    assert 'is_problem' in host
                    assert 'is_impact' in host
                    assert 'services' in host
                    # More information than without details:)
                    assert 'acknowledged' in host
                    assert 'downtimed' in host
                    assert 'next_check' in host
                    assert 'long_output' in host
                    assert 'perf_data' in host
        else:
            hosts_list = res
            assert len(hosts_list) > 1
            for host in hosts_list:
                assert 'name' in host
                assert 'last_check' in host
                assert 'state_id' in host
                assert 'state_type' in host
                assert 'state' in host
                assert 'output' in host
                assert 'is_problem' in host
                assert 'is_impact' in host
                assert 'services' in host
                # More information than without details:)
                assert 'acknowledged' in host
                assert 'downtimed' in host
                assert 'next_check' in host
                assert 'long_output' in host
                assert 'perf_data' in host

        self._stop_alignak_daemons(request_stop_uri='http://127.0.0.1:7770')

    def test_get_external_commands(self):
        """ Running all the Alignak daemons - get external commands

        :return:
        """
        satellite_map = {
            'arbiter': '7770', 'scheduler': '7768', 'broker': '7772',
            'poller': '7771', 'reactionner': '7769', 'receiver': '7773'
        }

        daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                        'receiver-master', 'scheduler-master']
        self._prepare_my_configuration(daemons_list=daemons_list)

        self._run_alignak_daemons(cfg_folder=self.cfg_folder,
                                  daemons_list=daemons_list, runtime=5)

        req = requests.Session()

        # Here the daemons got started by the arbiter and the arbiter dispatched a configuration
        # We will ask to wait for a new configuration

        # -----
        # 1/ get the running identifier (confirm the daemon is running)
        print("--- get_running_id")
        for name, port in list(satellite_map.items()):
            raw_data = req.get("http://localhost:%s/identity" % port, verify=False)
            assert raw_data.status_code == 200
            print("Got (raw): %s" % raw_data)
            data = raw_data.json()
            assert "running_id" in data
            print("%s, my running id: %s" % (name, data['running_id']))
        # -----

        # -----
        # 2/ notify an external command to the arbiter (as the receiver does).
        raw_data = req.post("http://localhost:7770/_push_external_command",
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

        raw_data = req.get("http://localhost:7770/_external_commands")
        assert raw_data.status_code == 200
        print("%s _external_commands, got (raw): %s" % (name, raw_data))
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
                                'command': 'process_host_check_result;Host_name;0;I am alive!'
                            }),
                            headers={'Content-Type': 'application/json'},
                            verify=False)
        print("command, got (raw): %s" % (raw_data.content))
        assert raw_data.status_code == 200
        data = raw_data.json()
        print("Got: %s" % data)
        assert data['_status'] == 'OK'
        # Note the uppercase for the command, not for the parameters...
        assert data['_message'] == 'Got command: PROCESS_HOST_CHECK_RESULT;Host_name;0;I am alive!'
        assert data['command'] == 'PROCESS_HOST_CHECK_RESULT;Host_name;0;I am alive!'

        raw_data = req.get("http://localhost:7770/_external_commands")
        assert raw_data.status_code == 200
        print("%s _external_commands, got (raw): %s" % (name, raw_data))
        data = raw_data.json()
        print("---Got: %s" % data)
        assert len(data) == 1
        assert 'creation_timestamp' in data[0]
        assert data[0]['cmd_line'] == 'PROCESS_HOST_CHECK_RESULT;Host_name;0;I am alive!'
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

        raw_data = req.get("http://localhost:7770/_external_commands")
        assert raw_data.status_code == 200
        print("%s _external_commands, got (raw): %s" % (name, raw_data))
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
            raw_data = req.get("http://localhost:%s/_external_commands" % port, verify=False)
            assert raw_data.status_code == 200
            print("%s _external_commands, got (raw): %s" % (name, raw_data))
            data = raw_data.json()
            print("Got: %s" % data)
            # External commands got consumed by the daemons - not always all !
            # May be 0 but it seems that sometimes 5 are remaining
            assert len(data) in [0, 5]

        # This function will only send a SIGTERM to the arbiter daemon
        self._stop_alignak_daemons(request_stop_uri='http://127.0.0.1:7770')

    def _get_stats(self, req, satellite_map, details, run=False):
        """Get and check daemons statistics"""
        problems = []

        print("--- stats")
        for name, port in list(satellite_map.items()):
            print("- for %s" % (name))
            raw_data = req.get("http://localhost:%s/stats%s" % (port, '?details=1' if details else ''), verify=False)
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

            # Scheduler specific information
            if name in ['scheduler']:
                assert "livesynthesis" in data
                livesynthesis = data['livesynthesis']
                print("%s, my livesynthesis: %s" % (name, livesynthesis))
                if not run:
                    assert livesynthesis["hosts_total"] == 13
                    assert livesynthesis["hosts_up_hard"] == 13
                    assert livesynthesis["services_total"] == 100
                    assert livesynthesis["services_ok_hard"] == 100

                # Detailed information!
                if details:
                    assert "commands" in data
                    commands = data['commands']
                    print("%s, my commands: %s" % (name, commands))

                    assert "problems" in data
                    problems = data['problems']
                    print("%s, my problems: %s" % (name, problems))
                    if run:
                        assert len(problems) > 0
                        for problem in problems:
                            problem = problems[problem]
                            print("A problem: %s" % (problem))
                            assert "host" in problem
                            assert "service" in problem
                            assert "output" in problem
                            assert "state" in problem
                            assert "state_type" in problem
                            assert "last_state" in problem
                            assert "last_state_type" in problem
                            assert "last_hard_state" in problem
                            assert "last_state_update" in problem
                            assert "last_state_change" in problem
                            assert "last_hard_state_change" in problem

            # Arbiter specific information
            if name in ['arbiter']:
                assert "livestate" in data
                livestate = data['livestate']
                assert "timestamp" in livestate
                assert "state" in livestate
                assert "output" in livestate
                assert "daemons" in livestate
                for daemon_state in livestate['daemons']:
                    assert livestate['daemons'][daemon_state] == 0
                print("%s, my livestate: %s" % (name, livestate))

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
                print("%s, my daemons state: %s" % (name, daemons_state))

                # Detailed information!
                if details:
                    assert "monitoring_objects" in data
                    monitoring_objects = data['monitoring_objects']
                    assert "hosts" in monitoring_objects
                    assert "items" in monitoring_objects["hosts"]
                    assert "count" in monitoring_objects["hosts"]
                    assert monitoring_objects["hosts"]["count"] == 13
                    assert "services" in monitoring_objects
                    assert "items" in monitoring_objects["services"]
                    assert "count" in monitoring_objects["services"]
                    assert monitoring_objects["services"]["count"] == 100
                    for o_type in monitoring_objects:
                        print("%s, my %s: %d items" % (name, o_type, monitoring_objects[o_type]["count"]))
                        assert monitoring_objects[o_type]["count"] == len(monitoring_objects[o_type]["items"])

        return problems

    def test_get_stats(self):
        """ Running all the Alignak daemons - get daemons statistics

        :return:
        """
        satellite_map = {
            'arbiter': '7770', 'scheduler': '7768', 'broker': '7772',
            'poller': '7771', 'reactionner': '7769', 'receiver': '7773'
        }

        daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                        'receiver-master', 'scheduler-master']
        self._prepare_my_configuration(daemons_list=daemons_list)

        self._run_alignak_daemons(cfg_folder=self.cfg_folder, arbiter_only=True,
                                  daemons_list=daemons_list, runtime=5, update_configuration=False)

        req = requests.Session()

        # Here the daemons got started by the arbiter and the arbiter dispatched a configuration

        # -----
        # 1/ get the running identifier (confirm the daemon is running)
        print("--- get_running_id")
        for name, port in list(satellite_map.items()):
            raw_data = req.get("http://localhost:%s/identity" % port, verify=False)
            assert raw_data.status_code == 200
            print("Got (raw): %s" % raw_data)
            data = raw_data.json()
            assert "running_id" in data
            print("%s, my running id: %s" % (name, data['running_id']))
        # -----

        # -----
        # 1/ get Alignak overall problems
        print("--- get monitoring problems")
        raw_data = req.get("http://localhost:7770/monitoring_problems")
        print("Alignak problems: %s" % (raw_data.text))
        assert raw_data.status_code == 200
        data = raw_data.json()
        assert 'alignak' in data
        assert 'type' in data
        assert 'name' in data
        assert 'version' in data

        # No problems exist for the scheduler master!
        assert 'problems' in data
        # assert 'scheduler-master' in data['problems']
        # assert '_freshness' in data['problems']['scheduler-master']
        # assert 'problems' in data['problems']['scheduler-master']
        # assert data['problems']['scheduler-master']['problems'] == {}

        # -----
        # 2/ get the daemons statistics - no details
        self._get_stats(req, satellite_map, False)

        time.sleep(1)

        # -----
        # 3/ once again, get the daemons statistics - with more details
        self._get_stats(req, satellite_map, True)

        # Sleep some seconds for some checks to execute
        time.sleep(120)

        # -----
        # 4/ once again, get the daemons statistics - with more details
        problems = self._get_stats(req, satellite_map, True, run=True)
        print("Problems: %s" % problems)

        time.sleep(1)

        # -----
        # 4/ get Alignak log
        print("--- get events log")
        raw_data = req.get("http://localhost:7770/events_log")
        print("Alignak events log: %s" % (raw_data.text))
        assert raw_data.status_code == 200
        data = raw_data.json()

        # -----
        # 5/ get Alignak overall problems
        print("--- get monitoring problems")
        raw_data = req.get("http://localhost:7770/monitoring_problems")
        print("Alignak problems: %s" % (raw_data.text))
        assert raw_data.status_code == 200
        data = raw_data.json()
        assert 'alignak' in data
        assert 'type' in data
        assert 'name' in data
        assert 'version' in data

        # Now, some problems exist for the scheduler master!
        assert 'problems' in data
        assert '_freshness' in data
        assert 'scheduler-master' in data['problems']
        assert 'problems' in data['problems']['scheduler-master']
        # I have some problems
        assert len(data['problems']['scheduler-master']) > 0
        for problem in data['problems']['scheduler-master']['problems']:
            problem = data['problems']['scheduler-master']['problems'][problem]
            print("A problem: %s" % (problem))

        # 5bis/ get Alignak scheduler problems
        print("--- get monitoring problems")
        raw_data = req.get("http://localhost:7768/monitoring_problems")
        print("Alignak problems: %s" % (raw_data.text))
        assert raw_data.status_code == 200
        data2 = raw_data.json()
        assert 'alignak' in data2
        assert 'type' in data2
        assert 'name' in data2
        assert 'version' in data2
        assert 'start_time' in data2

        doc = []
        doc.append(".. _alignak_features/monitoring_problems:")
        doc.append("")
        doc.append(".. Built from the test_daemons_api.py unit test last run!")
        doc.append("")
        doc.append("===========================")
        doc.append("Alignak monitoring problems")
        doc.append("===========================")
        doc.append("")
        doc.append("On a scheduler endpoint: ``/monitoring_problems``")
        doc.append("")
        doc.append("::")
        doc.append("")
        doc.append("    %s" % json.dumps(data2, sort_keys=True, indent=4))
        doc.append("")
        doc.append("On the arbiter endpoint: ``/monitoring_problems``")
        doc.append("")
        doc.append("::")
        doc.append("")
        doc.append("    %s" % json.dumps(data, sort_keys=True, indent=4))
        doc.append("")
        doc.append("")

        rst_write = None
        rst_file = "alignak_monitoring_problems.rst"
        if os.path.exists("../doc/source/api"):
            rst_write = "../doc/source/api/%s" % rst_file
        if os.path.exists("../../alignak-doc/source/07_alignak_features/api"):
            rst_write = "../../alignak-doc/source/07_alignak_features/api/%s" % rst_file
        if rst_write:
            with open(rst_write, mode='wt') as out:
                # with open(rst_write, mode='wt', encoding='utf-8') as out:
                out.write('\n'.join(doc))
        # -----

        # -----
        # 6/ get Alignak overall live synthesis
        print("--- get livesynthesis")
        raw_data = req.get("http://localhost:7770/livesynthesis")
        print("Alignak livesynthesis: %s" % (raw_data.text))
        assert raw_data.status_code == 200
        data = raw_data.json()
        assert 'alignak' in data
        assert 'type' in data
        assert 'name' in data
        assert 'version' in data
        assert 'start_time' in data

        # Now, some problems exist for the scheduler master!
        assert 'livesynthesis' in data
        assert '_overall' in data['livesynthesis']
        assert 'scheduler-master' in data['livesynthesis']
        assert '_freshness' in data['livesynthesis']['scheduler-master']
        assert 'livesynthesis' in data['livesynthesis']['scheduler-master']
        livesynthesis = data['livesynthesis']['scheduler-master']['livesynthesis']
        print("LS: %s" % livesynthesis)

        doc = []
        doc.append(".. _alignak_features/livesynthesis:")
        doc.append("")
        doc.append(".. Built from the test_daemons_api.py unit test last run!")
        doc.append("")
        doc.append("=====================")
        doc.append("Alignak livesynthesis")
        doc.append("=====================")
        doc.append("")
        doc.append("")
        doc.append("On the arbiter endpoint: ``/livesynthesis``")
        doc.append("")
        doc.append("::")
        doc.append("")
        doc.append("    %s" % json.dumps(data, sort_keys=True, indent=4))
        doc.append("")
        doc.append("")

        rst_write = None
        rst_file = "alignak_livesynthesis.rst"
        if os.path.exists("../doc/source/api"):
            rst_write = "../doc/source/api/%s" % rst_file
        if os.path.exists("../../alignak-doc/source/07_alignak_features/api"):
            rst_write = "../../alignak-doc/source/07_alignak_features/api/%s" % rst_file
        if rst_write:
            with open(rst_write, mode='wt') as out:
                # with open(rst_write, mode='wt', encoding='utf-8') as out:
                out.write('\n'.join(doc))
        # -----

        # -----
        # 7/ get Alignak log
        print("--- get events log")
        raw_data = req.get("http://localhost:7770/events_log")
        print("Alignak events log: %s" % (raw_data.text))
        assert raw_data.status_code == 200
        data = raw_data.json()
        for log in data:
            print(log)

        # This function will request the arbiter daemon to stop
        self._stop_alignak_daemons(request_stop_uri='http://127.0.0.1:7770')

    def test_get_realms(self):
        """ Running all the Alignak daemons - get realmss organization

        :return:
        """
        satellite_map = {
            'arbiter': '7770', 'scheduler': '7768', 'broker': '7772',
            'poller': '7771', 'reactionner': '7769', 'receiver': '7773'
        }

        daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                        'receiver-master', 'scheduler-master']
        self._prepare_my_configuration(daemons_list=daemons_list, cfg_dir='default_multi_realms',
                                       realms=['All', 'Europe', 'Asia', 'France', 'Japan'])

        self._run_alignak_daemons(cfg_folder=self.cfg_folder, arbiter_only=True,
                                  daemons_list=daemons_list, runtime=5, update_configuration=False)

        req = requests.Session()

        # Here the daemons got started by the arbiter and the arbiter dispatched a configuration

        # -----
        # 1/ get the running identifier (confirm the daemon is running)
        print("--- get_running_id")
        for name, port in list(satellite_map.items()):
            raw_data = req.get("http://localhost:%s/identity" % port, verify=False)
            assert raw_data.status_code == 200
            print("Got (raw): %s" % raw_data)
            data = raw_data.json()
            assert "running_id" in data
            print("%s, my running id: %s" % (name, data['running_id']))
        # -----

        # -----
        # 2/ get Alignak realms
        print("--- get realms")
        raw_data = req.get("http://localhost:7770/realms")
        print("Alignak realms: %s" % (raw_data.text))
        assert raw_data.status_code == 200
        data = raw_data.json()
        assert 'All' in data
        assert data['All']['name'] == 'All'
        assert data['All']['level'] == 0
        assert len(data['All']["hosts"]) == 11
        assert len(data['All']["hostgroups"]) == 4
        assert 'satellites' in data['All']
        assert 'children' in data['All']

        assert 'Europe' in data['All']['children']
        assert data['All']['children']['Europe']['level'] == 1

        assert 'Asia' in data['All']['children']
        assert data['All']['children']['Asia']['level'] == 1

        # This function will request the arbiter daemon to stop
        self._stop_alignak_daemons(request_stop_uri='http://127.0.0.1:7770')
