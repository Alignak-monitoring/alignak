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

import configparser

import pytest
from .alignak_test import AlignakTest

from alignak.http.generic_interface import GenericInterface
from alignak.http.arbiter_interface import ArbiterInterface
from alignak.http.scheduler_interface import SchedulerInterface
from alignak.http.broker_interface import BrokerInterface


class TestLaunchArbiter(AlignakTest):
    def setUp(self):
        super(TestLaunchArbiter, self).setUp()

        # Set an environment variable to change the default period of activity log (every 60 loops)
        os.environ['ALIGNAK_LOG_ACTIVITY'] = '1'

        self.cfg_folder = '/tmp/alignak'
        self._prepare_configuration(copy=True, cfg_folder=self.cfg_folder)

        self.req = requests.Session()

    def tearDown(self):
        print("Test terminated!")

    def _ping_daemons(self, daemon_names=None):
        # -----
        print("Pinging the daemons: %s" % (daemon_names if daemon_names else 'All'))
        satellite_map = {
            'arbiter': '7770', 'scheduler': '7768', 'broker': '7772',
            'poller': '7771', 'reactionner': '7769', 'receiver': '7773'
        }
        for name, port in list(satellite_map.items()):
            if daemon_names and name not in daemon_names:
                continue
            print("- pinging %s: http://127.0.0.1:%s/ping" % (name, port))
            raw_data = self.req.get("http://127.0.0.1:%s/ping" % (port))
            data = raw_data.json()
            assert data == 'pong', "Daemon %s  did not pong :(" % name
        # -----

    def _stop_daemons(self, daemon_names=None):
        # -----
        print("Stopping the daemons: %s" % daemon_names)
        satellite_map = {
            'arbiter': '7770', 'scheduler': '7768', 'broker': '7772',
            'poller': '7771', 'reactionner': '7769', 'receiver': '7773'
        }
        for name, port in list(satellite_map.items()):
            if daemon_names and name not in daemon_names:
                continue
            print("- stopping %s: http://127.0.0.1:%s/stop_request" % (name, port))
            raw_data = self.req.get("http://127.0.0.1:%s/stop_request?stop_now=0" % (port))
            data = raw_data.json()
            print("- response = %s" % data)
        time.sleep(3)
        for name, port in list(satellite_map.items()):
            if daemon_names and name not in daemon_names:
                continue
            print("- stopping %s: http://127.0.0.1:%s/stop_request" % (name, port))
            raw_data = self.req.get("http://127.0.0.1:%s/stop_request?stop_now=1" % (port))
            data = raw_data.json()
            print("- response = %s" % data)
        # -----

    def test_arbiter_no_daemons(self):
        """ Run the Alignak Arbiter - all the expected daemons are missing and are not launched

        :return:
        """
        self._run_arbiter_no_configured_daemons(False)

    def test_arbiter_no_daemons_launch(self):
        """ Run the Alignak Arbiter - all the expected daemons are missing and are launched

        :return:
        """
        self._run_arbiter_no_configured_daemons(True)

    def _run_arbiter_no_configured_daemons(self, alignak_launched):
        """ Run the Alignak Arbiter - all the expected daemons are missing

        If alignak_launched, the arbiter will launch the missing daemons

        :return:
        """
        # Copy the default Alignak shipped configuration to the run directory
        cfg_folder = '/tmp/alignak'
        print("Copy default configuration (../etc) to %s..." % cfg_folder)
        if os.path.exists('%s/etc' % cfg_folder):
            shutil.rmtree('%s/etc' % cfg_folder)
        shutil.copytree('../etc', '%s/etc' % cfg_folder)
        shutil.rmtree('%s/etc/alignak.d' % cfg_folder)

        files = ['%s/etc/alignak.ini' % cfg_folder,
                 '%s/etc/alignak.d/daemons.ini' % cfg_folder,
                 '%s/etc/alignak.d/modules.ini' % cfg_folder]
        try:
            cfg = configparser.ConfigParser()
            cfg.read(files)

            # Arbiter launches the daemons
            if alignak_launched:
                cfg.set('alignak-configuration', 'launch_missing_daemons', '1')
                # cfg.set('daemon.arbiter-master', 'alignak_launched', '1')
                # cfg.set('daemon.scheduler-master', 'alignak_launched', '1')
                # cfg.set('daemon.poller-master', 'alignak_launched', '1')
                # cfg.set('daemon.reactionner-master', 'alignak_launched', '1')
                # cfg.set('daemon.receiver-master', 'alignak_launched', '1')
                # cfg.set('daemon.broker-master', 'alignak_launched', '1')
            else:
                cfg.set('alignak-configuration', 'launch_missing_daemons', '0')
                # cfg.set('daemon.arbiter-master', 'alignak_launched', '0')
                # cfg.set('daemon.scheduler-master', 'alignak_launched', '0')
                # cfg.set('daemon.poller-master', 'alignak_launched', '0')
                # cfg.set('daemon.reactionner-master', 'alignak_launched', '0')
                # cfg.set('daemon.receiver-master', 'alignak_launched', '0')
                # cfg.set('daemon.broker-master', 'alignak_launched', '0')
            with open('%s/etc/alignak.ini' % cfg_folder, "w") as modified:
                cfg.write(modified)
        except Exception as exp:
            print("* parsing error in config file: %s" % exp)
            assert False

        self._run_alignak_daemons(cfg_folder=cfg_folder, arbiter_only=True, runtime=30)

        # The arbiter will have stopped!
        ret = self.procs['arbiter-master'].poll()
        if ret is None:
            print("*** Arbiter is still running.")
            # Stop the arbiter
            self.procs['arbiter-master'].kill()
            # raw_data = self.req.get("http://127.0.0.1:7770/stop_request?stop_now=1")
            # data = raw_data.json()
            # print("Stop response: %s")
            time.sleep(2)
        else:
            print("*** Arbiter exited with: %s" % ret)
            assert ret == 4

        expected_warnings = [
            u"- ignoring repeated file: /tmp/alignak/etc/arbiter/packs/resource.d/readme.cfg",
            u"Configuration warnings:",
            u"the parameter $DIST_BIN$ is ambiguous! No value after =, assuming an empty string",
            u"No Nagios-like legacy configuration files configured.",
            u"If you need some, edit the 'alignak.ini' configuration file to declare one or more 'cfg=' variables.",

            u"There is no arbiter, I add myself (arbiter-master) reachable on 127.0.0.1:7770",
            u"No realms defined, I am adding one as All",
            u"No scheduler defined, I am adding one on 127.0.0.1:7800",
            u"No reactionner defined, I am adding one on 127.0.0.1:7801",
            u"No poller defined, I am adding one on 127.0.0.1:7802",
            u"No broker defined, I am adding one on 127.0.0.1:7803",
            u"No receiver defined, I am adding one on 127.0.0.1:7804",
        ]
        if not alignak_launched:
            expected_warnings.extend([
                u"A daemon (reactionner/Default-Reactionner) that we must be related with cannot be connected: ",
                u"Setting the satellite Default-Reactionner as dead :(",
                u"Default-Reactionner is not alive for get_running_id",

                u"A daemon (poller/Default-Poller) that we must be related with cannot be connected: ",
                u"Setting the satellite Default-Poller as dead :(",
                u"Default-Poller is not alive for get_running_id",

                u"A daemon (broker/Default-Broker) that we must be related with cannot be connected: ",
                u"Setting the satellite Default-Broker as dead :(",
                u"Default-Broker is not alive for get_running_id",

                u"A daemon (receiver/Default-Receiver) that we must be related with cannot be connected: ",
                u"Setting the satellite Default-Receiver as dead :(",
                u"Default-Receiver is not alive for get_running_id",

                u"A daemon (scheduler/Default-Scheduler) that we must be related with cannot be connected: ",
                u"Setting the satellite Default-Scheduler as dead :(",
                u"Default-Scheduler is not alive for get_running_id",

                u"satellites connection #1 is not correct; let's give another chance after 1 seconds...",
                u"satellites connection #2 is not correct; let's give another chance after 1 seconds...",
                u"satellites connection #3 is not correct; let's give another chance after 1 seconds...",
            ])

        expected_errors = [
        ]
        if not alignak_launched:
            expected_errors = [
                u"All the daemons connections could not be established despite 3 tries! Sorry, I bail out!",
                u"Sorry, I bail out, exit code: 4"
            ]
        all_ok = True
        with open('/tmp/alignak/log/arbiter-master.log') as f:
            for line in f:
                if 'WARNING:' in line:
                    ok = False
                    # Only some WARNING log are accepted:
                    for l in expected_warnings:
                        if l in line:
                            ok = True
                            break
                    if ok:
                        print("... %s" % line.rstrip())
                    else:
                        print(">>> %s" % line.rstrip())
                        all_ok = False

                    # assert ok
                if 'ERROR:' in line:
                    ok = False
                    # Only some WARNING log are accepted:
                    for l in expected_errors:
                        if l in line:
                            ok = True
                            break
                    if ok:
                        print("... %s" % line.rstrip())
                    else:
                        print("*** %s" % line.rstrip())
                        all_ok = False
        assert all_ok

    def test_arbiter_daemons(self):
        """ Run the Alignak Arbiter - all the expected daemons are started by the arbiter
        and then the arbiter exits

        :return:
        """
        # All the default configuration files are in /tmp/alignak/etc
        # Update monitoring configuration file variables
        try:
            cfg = configparser.ConfigParser()
            cfg.read(['/tmp/alignak/etc/alignak.ini', '/tmp/alignak/etc/alignak.d/daemons.ini'])
            cfg.set('alignak-configuration', 'launch_missing_daemons', '1')
            cfg.set('alignak-configuration', 'polling_interval', '1')
            cfg.set('alignak-configuration', 'daemons_check_period', '5')
            cfg.set('alignak-configuration', 'daemons_stop_timeout', '3')
            cfg.set('alignak-configuration', 'daemons_start_timeout', '1')
            cfg.set('alignak-configuration', 'daemons_new_conf_timeout', '1')
            cfg.set('alignak-configuration', 'daemons_dispatch_timeout', '1')
            cfg.set('alignak-configuration', 'min_workers', '1')
            cfg.set('alignak-configuration', 'max_workers', '1')
            cfg.set('daemon.arbiter-master', 'alignak_launched', '1')
            cfg.set('daemon.scheduler-master', 'alignak_launched', '1')
            cfg.set('daemon.poller-master', 'alignak_launched', '1')
            cfg.set('daemon.reactionner-master', 'alignak_launched', '1')
            cfg.set('daemon.receiver-master', 'alignak_launched', '1')
            cfg.set('daemon.broker-master', 'alignak_launched', '1')
            with open('/tmp/alignak/etc/alignak.ini', "w") as modified:
                cfg.write(modified)
        except Exception as exp:
            print("* parsing error in config file: %s" % exp)
            assert False

        args = ["../alignak/bin/alignak_arbiter.py", "-e", "/tmp/alignak/etc/alignak.ini"]
        self.procs = {'arbiter-master': subprocess.Popen(args)}
        print("%s launched (pid=%d)" % ('arbiter', self.procs['arbiter-master'].pid))

        # Sleep some few seconds because of the time needed to start the processes,
        # poll them and declare as faulty !
        sleep(15)

        # The arbiter will NOT have stopped! It is still running
        ret = self.procs['arbiter-master'].poll()
        assert ret is None
        print("Started...")

        self._ping_daemons()

        # Sleep some few seconds to let the arbiter ping the daemons by itself
        sleep(60)

        self._ping_daemons()

        # This function will only send a SIGTERM to the arbiter daemon
        self._stop_daemons(['arbiter'])
        # self._stop_alignak_daemons(arbiter_only=True)
        with open('/tmp/alignak/log/arbiter-master.log') as f:
            for line in f:
                line = line.strip()
                print(line)
                if 'ERROR:' in line:
                    assert False, "Raised an error!"

    def test_arbiter_daemons_kill_one_daemon(self):
        """ Run the Alignak Arbiter - all the expected daemons are started by the arbiter
        and then a daemon is killed ... the arbiter kills all the remaining daemons
        after a while and then stops

        :return:
        """
        # All the default configuration files are in /tmp/alignak/etc
        # Update monitoring configuration file variables
        try:
            cfg = configparser.ConfigParser()
            cfg.read(['/tmp/alignak/etc/alignak.ini', '/tmp/alignak/etc/alignak.d/daemons.ini'])
            cfg.set('alignak-configuration', 'launch_missing_daemons', '1')
            cfg.set('alignak-configuration', 'polling_interval', '1')
            cfg.set('alignak-configuration', 'daemons_check_period', '1')
            cfg.set('alignak-configuration', 'daemons_stop_timeout', '1')
            cfg.set('alignak-configuration', 'daemons_start_timeout', '1')
            cfg.set('alignak-configuration', 'daemons_new_conf_timeout', '1')
            cfg.set('alignak-configuration', 'daemons_dispatch_timeout', '1')
            cfg.set('alignak-configuration', 'min_workers', '1')
            cfg.set('alignak-configuration', 'max_workers', '1')
            cfg.set('daemon.arbiter-master', 'alignak_launched', '1')
            cfg.set('daemon.scheduler-master', 'alignak_launched', '1')
            cfg.set('daemon.poller-master', 'alignak_launched', '1')
            cfg.set('daemon.reactionner-master', 'alignak_launched', '1')
            cfg.set('daemon.receiver-master', 'alignak_launched', '1')
            cfg.set('daemon.broker-master', 'alignak_launched', '1')
            with open('/tmp/alignak/etc/alignak.ini', "w") as modified:
                cfg.write(modified)
        except Exception as exp:
            print("* parsing error in config file: %s" % exp)
            assert False

        args = ["../alignak/bin/alignak_arbiter.py", "-e", "/tmp/alignak/etc/alignak.ini"]
        self.procs = {'arbiter-master': subprocess.Popen(args)}
        print("%s launched (pid=%d)" % ('arbiter', self.procs['arbiter-master'].pid))

        # Sleep some few seconds because of the time needed to start the processes,
        # poll them and declare as faulty !
        sleep(15)

        # The arbiter will NOT have stopped! It is still running
        ret = self.procs['arbiter-master'].poll()
        assert ret is None
        print("Started...")

        self._ping_daemons()

        print("Killing one daemon process...")
        self._stop_daemons(['receiver'])
        self._ping_daemons()
        sleep(2)

        sleep(30)

        self._stop_daemons(['arbiter'])
