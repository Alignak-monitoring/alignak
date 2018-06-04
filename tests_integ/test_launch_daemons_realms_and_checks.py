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
import re
import sys
import signal

import pytest
import configparser

import subprocess
from time import sleep
import shutil

from .alignak_test import AlignakTest


class TestLaunchDaemonsRealms(AlignakTest):
    def setUp(self):
        super(TestLaunchDaemonsRealms, self).setUp()

        # Set an environment variable to activate the logging of checks execution
        # With this the pollers/schedulers will raise INFO logs about the checks execution
        os.environ['ALIGNAK_LOG_ACTIONS'] = 'WARNING'

        # Set an environment variable to change the default period of activity log (every 60 loops)
        os.environ['ALIGNAK_LOG_ACTIVITY'] = '60'

        # Alignak daemons monitoring everay 3 seconds
        os.environ['ALIGNAK_DAEMON_MONITORING'] = '3'

        # Alignak arbiter self-monitoring - report statistics every 5 loop counts
        os.environ['ALIGNAK_SYSTEM_MONITORING'] = '5'

        # Log daemons loop turn
        os.environ['ALIGNAK_LOG_LOOP'] = 'INFO'

    def tearDown(self):
        print("Test terminated!")

    # def test_daemons_realms(self):
    #     """ Running the Alignak daemons for a 3 realms configuration - several daemons
    #     for the realms
    #
    #     :return: None
    #     """
    #     daemons_list = ['broker-master', 'broker-north', 'broker-south',
    #                     'poller-master', 'poller-north', 'poller-south',
    #                     'reactionner-master',
    #                     'receiver-master', 'receiver-north',
    #                     'scheduler-master', 'scheduler-north', 'scheduler-south',]
    #
    #     self._run_alignak_daemons(cfg_folder='cfg/run_realms',
    #                               daemons_list=daemons_list,
    #                               run_folder='/tmp', runtime=30)
    #
    #     self._stop_alignak_daemons(arbiter_only=True)
    #
    #     # Check daemons log files
    #     ignored_warnings = [
    #         # # todo: Temporary: because of unordered daemon stop !
    #         # 'that we must be related with cannot be connected',
    #         # 'Exception: Server not available',
    #         # 'Setting the satellite ',
    #         # 'Add failed attempt',
    #
    #         # Sometimes not killed during the test because of SIGTERM
    #         # u'did not stopped, trying to kill'
    #
    #         # Configuration check
    #         u"Configuration warnings",
    #         u"the parameter $DIST_BIN$ is ambiguous! No value after =, assuming an empty string",
    #
    #         # Configuration dispatching
    #         u"The arbiter pushed a new configuration...",
    #
    #         u'Timeout raised for ',
    #         u'spent too much time:',
    #         u'Launch command',
    #         u'Check result',
    #         u'Performance data',
    #         u'Action',
    #         u'Got check result',
    #         u'Echo the current state',
    #         u'Set host',
    #     ]
    #     ignored_errors = [
    #     ]
    #     (errors_raised, warnings_raised) = \
    #         self._check_daemons_log_for_errors(daemons_list,
    #                                            ignored_warnings=ignored_warnings,
    #                                            ignored_errors=ignored_errors)
    #
    #     assert errors_raised == 0, "Error logs raised!"
    #     print("No unexpected error logs raised by the daemons")
    #
    #     assert warnings_raised == 0, "Warning logs raised!"
    #     print("No unexpected warning logs raised by the daemons")
    #
    # def test_daemons_realms_2(self):
    #     """ Running the Alignak daemons for a 3 realms configuration - only some daemons
    #     that manage sub realms
    #
    #     :return: None
    #     """
    #     daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
    #                     'receiver-master', 'scheduler-master']
    #
    #     self._run_alignak_daemons(cfg_folder='cfg/run_realms_manage_sub_realms',
    #                               daemons_list=daemons_list,
    #                               run_folder='/tmp/alignak', runtime=30)
    #
    #     self._stop_alignak_daemons()
    #
    #     # Check daemons log files
    #     ignored_warnings = [
    #         # # todo: Temporary: because of unordered daemon stop !
    #         # 'that we must be related with cannot be connected',
    #         # 'Exception: Server not available',
    #         # 'Setting the satellite ',
    #         # 'Add failed attempt',
    #
    #         # Sometimes not killed during the test because of SIGTERM
    #         # u'did not stopped, trying to kill'
    #
    #         # Configuration check
    #         u"Configuration warnings",
    #         u"the parameter $DIST_BIN$ is ambiguous! No value after =, assuming an empty string",
    #
    #         # Configuration dispatching
    #         u"My Arbiter wants me to wait for a new configuration",
    #         u"The arbiter pushed a new configuration...",
    #
    #         u'Timeout raised for ',
    #         u'spent too much time:',
    #         u'Launch command',
    #         u'Check result',
    #         u'Performance data',
    #         u'Action',
    #         u'Got check result',
    #         u'Echo the current state',
    #         u'Set host',
    #     ]
    #     ignored_errors = [
    #     ]
    #     (errors_raised, warnings_raised) = \
    #         self._check_daemons_log_for_errors(daemons_list,
    #                                            ignored_warnings=ignored_warnings,
    #                                            ignored_errors=ignored_errors)
    #
    #     assert errors_raised == 0, "Error logs raised!"
    #     print("No unexpected error logs raised by the daemons")
    #
    #     assert warnings_raised == 0, "Warning logs raised!"
    #     print("No unexpected warning logs raised by the daemons")
    #
    def test_checks_active_satellites(self):
        """ Run the Alignak daemons and check the correct checks result and notifications
        with some pollers / reactionners in active mode

        :return: None
        """
        self._run_checks(passive=False, hosts_count=10, duration=60, cfg_dir='default_many_hosts')

    def test_checks_active_satellites_multi_realms(self):
        """ Run the Alignak daemons and check the correct checks result and notifications
        with some pollers / reactionners in active mode

        Several realms (All, North and South) with 10 hosts in each realm

        :return: None
        """
        self._run_checks(passive=False, hosts_count=10, duration=60, cfg_dir='default_realms',
                         more_daemons = ['broker-North', 'broker-South',
                                         'poller-North', 'poller-South',
                                         # 'receiver-North',
                                         'scheduler-North', 'scheduler-South'],
                         realms = ['All', 'North', 'South'])

    def test_checks_passive_satellites(self):
        """ Run the Alignak daemons and check the correct checks result and notifications
        with some pollers / reactionners in passive mode

        The scheduler pushes the actions to execute to pollers / reactionners and
        get the results from the pollers/reactionners

        :return: None
        """
        self._run_checks(passive=True, hosts_count=10, duration=60, cfg_dir='default_many_hosts')

    def test_checks_passive_satellites_multi_realms(self):
        """ Run the Alignak daemons and check the correct checks result and notifications
        with some pollers / reactionners in passive mode

        The scheduler pushes the actions to execute to pollers / reactionners and
        get the results from the pollers/reactionners

        Several realms (All, North and South) with 10 hosts in each realm

        :return: None
        """
        self._run_checks(passive=True, hosts_count=10, duration=120, cfg_dir='default_realms',
                         more_daemons = ['broker-North', 'broker-South',
                                         'poller-North', 'poller-South',
                                         # 'receiver-North',
                                         'scheduler-North', 'scheduler-South'],
                         realms = ['All', 'North', 'South'])

    def _run_checks(self, passive=True, duration=60, hosts_count=10, cfg_dir='default_many_hosts',
                    more_daemons=None, realms=None):
        """ Run the Alignak daemons and check the correct checks result and notifications
        with some pollers / reactionners in active or passive mode

        :return: None
        """
        self.cfg_folder = '/tmp/alignak'
        daemons_list = ['broker-master', 'poller-master', 'reactionner-master',
                        'receiver-master', 'scheduler-master']
        if realms is None:
            realms = ['All']
        if more_daemons is not None:
            daemons_list += more_daemons
        print("Daemons: %s" % daemons_list)

        # Default shipped configuration preparation
        self._prepare_configuration(copy=True, cfg_folder=self.cfg_folder)

        # Specific daemon load configuration preparation
        if os.path.exists('./cfg/%s/alignak.cfg' % cfg_dir):
            shutil.copy('./cfg/%s/alignak.cfg' % cfg_dir, '%s/etc' % self.cfg_folder)
        if os.path.exists('%s/etc/arbiter' % self.cfg_folder):
            shutil.rmtree('%s/etc/arbiter' % self.cfg_folder)
        shutil.copytree('./cfg/%s/arbiter' % cfg_dir, '%s/etc/arbiter' % self.cfg_folder)

        self._prepare_hosts_configuration(cfg_folder='%s/etc/arbiter/objects/hosts'
                                                     % self.cfg_folder,
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

            cfg.set('alignak-configuration', 'daemons_start_timeout', '15')
            cfg.set('alignak-configuration', 'daemons_dispatch_timeout', '15')

            # A macro for the check script directory
            cfg.set('alignak-configuration', '_EXEC_DIR', self.cfg_folder)
            for daemon in daemons_list:
                if cfg.has_section('daemon.%s' % daemon):
                    cfg.set('daemon.%s' % daemon, 'alignak_launched', '1')

            # Poller and reactionner daemons are in active mode - default mode!
            if passive:
                cfg.set('daemon.poller-master', 'passive', '1')
                cfg.set('daemon.reactionner-master', 'passive', '1')

            with open('%s/etc/alignak.ini' % self.cfg_folder, "w") as modified:
                cfg.write(modified)
        except Exception as exp:
            print("* parsing error in config file: %s" % exp)
            assert False

        run = True
        if run:
            # Run daemons for the required duration
            self._run_alignak_daemons(cfg_folder='/tmp/alignak',
                                      daemons_list=daemons_list,
                                      run_folder='/tmp/alignak', runtime=duration)

            self._stop_alignak_daemons()

        # Check daemons log files
        ignored_warnings = [
            # Configuration check
            u"Configuration warnings",
            u"the parameter $DIST_BIN$ is ambiguous! No value after =, assuming an empty string",
            u"No realms defined, I am adding one as All",

            # Daemons not existing
            u"Some hosts exist in the realm ",
            u"Adding a scheduler",
            u"Added a scheduler",
            u"Adding a poller",
            u"Added a poller",
            u"Adding a broker",
            u"Added a broker",

            # Configuration dispatching
            u"The arbiter pushed a new configuration...",

            # Action execution log
            u'Timeout raised for ',
            u'spent too much time:',
            u'Launch command',
            u'Check result',
            u'Performance data',
            u'Action',
            u'Got check result',
            u'Echo the current state',
            u'Set host',
            u'Check to run:'
        ]
        ignored_errors = [
            # 'Error on backend login: ',
            # 'Configured user account is not allowed for this module'
        ]
        (errors_raised, warnings_raised) = \
            self._check_daemons_log_for_errors(daemons_list, run_folder='/tmp/alignak',
                                               ignored_warnings=ignored_warnings,
                                               ignored_errors=ignored_errors,
                                               dump_all=False)

        assert errors_raised == 0, "Error logs raised!"
        print("No unexpected error logs raised by the daemons")

        assert warnings_raised == 0, "Warning logs raised!"
        print("No unexpected warning logs raised by the daemons")

        # Expected logs from the daemons
        expected_logs = {
            'poller-master': [
                # Check launch
                "Launch command: '%s/check_command.sh " % self.cfg_folder,
                "Action '%s/check_command.sh " % self.cfg_folder,
                "Check result for '%s/check_command.sh " % self.cfg_folder,
                "Performance data for '%s/check_command.sh " % self.cfg_folder,
            ],
            'scheduler-master': [
                # Internal host check
                "Set host localhost as UP (internal check)",
            ],
            'reactionner-master': [
                "Launch command: '/usr/bin/printf ",
                "Action '/usr/bin/printf "
            ]
        }
        service_checks = {}
        # Store services information for localhost
        service_checks["localhost"] = {
            "host-check": {"launch": 0, "run": 0, "exit": 0, "result": 0}
        }
        for realm in realms:
            for index in range(hosts_count):
                # Store services information for each host
                service_checks["host-%s-%d" % (realm.lower(), index)] = {
                    "host-check": {"launch": 0, "run": 0, "exit": 0, "result": 0}
                }
                for service in ["dummy_echo",
                                "dummy_unknown", "dummy_ok", "dummy_warning",
                                "dummy_critical", "dummy_timeout",
                                "extra-1", "extra-2", "extra-3", "extra-4"]:
                    # Store services information for each host service
                    service_checks["host-%s-%d" % (realm.lower(), index)][service] = {
                        "launch": 0, "run": 0, "exit": 0, "result": 0
                    }

                    # Poller log about the host check and services check
                    if service not in ['dummy_echo']:
                        # No internal check for the poller
                        expected_logs['poller-master'].append("host-%s-%d host-check" % (realm.lower(), index))
                        expected_logs['poller-master'].append("host-%s-%d %s" % (realm.lower(), index, service))

                    # Scheduler log about the host check and services check
                    expected_logs['scheduler-master'].append("check_command.sh host-%s-%d %s" % (realm.lower(), index, service))
                    expected_logs['scheduler-master'].append("Internal check: host-%s-%d/dummy_echo" % (realm.lower(), index))

                    # Reactionner log faulty services check
                    if service in ["dummy_warning", "dummy_critical"]:
                        expected_logs['reactionner-master'].append("host-%s-%d/%s" % (realm.lower(), index, service))

        errors_raised = 0
        scheduler_count = 0
        poller_count = 0
        travis_run = 'TRAVIS' in os.environ
        # Poller log:
        # run = "Launch command: '/tmp/check_command.sh host-1 dummy_critical 2'"
        # get = "Check result for '/tmp/check_command.sh host-1 dummy_critical 2': 2, Hi, checking host-1/dummy_critical -> exit=2"

        # Scheduler log
        # launch = "Check to run: Check 3d5bd56a-fb91-4e83-b54c-c103b4a00fd5 active, item: b2b25d87-b8f1-439c-bb35-986b229eced4, status: in_poller, command:'/tmp/check_command.sh host-9 dummy_critical 2'"
        # result = "Got check result: 2 for host-4/dummy_critical"

        for daemon in daemons_list:
            if not daemon.startswith('scheduler'):
                continue
            assert os.path.exists('/tmp/alignak/log/%s.log' % daemon), '/tmp/alignak/log/%s.log does not exist!' % daemon
            print(("-----\n%s log file\n" % daemon))
            with open('/tmp/alignak/log/%s.log' % daemon) as f:
                lines = f.readlines()
                logs = []
                for line in lines:
                    # Catches WARNING logs
                    if 'WARNING:' in line:
                        # Catch warning for actions execution
                        line = line.split('WARNING: ')
                        line = line[1]
                        line = line.strip()
                        line = line.split('] ')
                        try:
                            line = line[1]
                            line = line.strip()
                            if not travis_run:
                                print(("-ok-: %s" % line))
                        except IndexError:
                            if not travis_run:
                                print("***line: %s" % line)

                        launch_search = re.search("command:'/tmp/alignak/check_command.sh ([A-Za-z0-9-_]+) ([A-Za-z0-9-_]+)", line, re.IGNORECASE)
                        if launch_search:
                            host = launch_search.group(1)
                            service = launch_search.group(2)
                            print("Service check launch: %s / %s" % (host, service))
                            service_checks[host][service]['launch'] += 1

                        result_search = re.search("Got check result: (.) for ([A-Za-z0-9-_]+)/([A-Za-z0-9-_]+)", line, re.IGNORECASE)
                        if result_search:
                            host = result_search.group(2)
                            service = result_search.group(3)
                            exit_code = result_search.group(1)
                            print("Service check result: %s / %s - %s" % (host, service, exit_code))
                            service_checks[host][service]['result'] += 1
                        else:
                            result_search = re.search("Got check result: (.) for ([A-Za-z0-9-_]+)$", line, re.IGNORECASE)
                            if result_search:
                                host = result_search.group(2)
                                service = "host-check"
                                exit_code = result_search.group(1)
                                print("Service check result: %s / %s - %s" % (host, service, exit_code))
                                service_checks[host][service]['result'] += 1

        for daemon in daemons_list:
            if not daemon.startswith('poller'):
                continue
            assert os.path.exists('/tmp/alignak/log/%s.log' % daemon), '/tmp/alignak/log/%s.log does not exist!' % daemon
            print(("-----\n%s log file\n" % daemon))
            with open('/tmp/alignak/log/%s.log' % daemon) as f:
                lines = f.readlines()
                logs = []
                for line in lines:
                    # Catches WARNING and ERROR logs
                    if 'WARNING:' in line:
                        # Catch warning for actions execution
                        line = line.split('WARNING: ')
                        line = line[1]
                        line = line.strip()
                        line = line.split('] ')
                        try:
                            line = line[1]
                            line = line.strip()
                            # if not travis_run:
                            #     print(("-ok-: %s" % line))
                        except IndexError:
                            if not travis_run:
                                print("***line: %s" % line)

                        run_search = re.search("Launch command: '/tmp/alignak/check_command.sh ([A-Za-z0-9-_]+) ([A-Za-z0-9-_]+)", line, re.IGNORECASE)
                        if run_search:
                            host = run_search.group(1)
                            service = run_search.group(2)
                            print("Service check run: %s / %s" % (host, service))
                            service_checks[host][service]['run'] += 1

                        exit_search = re.search("Check result for '/tmp/alignak/check_command.sh ([A-Za-z0-9-_]+) ([A-Za-z0-9-_]+) (.)", line, re.IGNORECASE)
                        if exit_search:
                            host = exit_search.group(1)
                            service = exit_search.group(2)
                            exit_code = exit_search.group(3)
                            print("Service check exit: %s / %s - %s" % (host, service, exit_code))
                            service_checks[host][service]['exit'] += 1

        print("Service checks")
        for host in sorted(service_checks):
            print("Host: %s" % host)
            for service in service_checks[host]:
                svc_counts = service_checks[host][service]
                print("- %s: %s" % (service, svc_counts))
                if svc_counts['launch'] != svc_counts['result']:
                    print("*****")
                if svc_counts['run'] != svc_counts['exit']:
                    print("*****")
                # assert svc_counts['launch'] >= svc_counts['result'], svc_counts
                # assert svc_counts['run'] >= svc_counts['exit'], svc_counts
