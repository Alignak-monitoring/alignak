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

from alignak.http.generic_interface import GenericInterface
from alignak.http.arbiter_interface import ArbiterInterface
from alignak.http.scheduler_interface import SchedulerInterface
from alignak.http.broker_interface import BrokerInterface


class TestLaunchArbiter(AlignakTest):
    def setUp(self):
        super(TestLaunchArbiter, self).setUp()

        # copy the default shipped configuration files in /tmp/etc and change the root folder
        # used by the daemons for pid and log files in the alignak.ini file
        if os.path.exists('/tmp/etc/alignak'):
            shutil.rmtree('/tmp/etc/alignak')

        if os.path.exists('/tmp/var'):
            shutil.rmtree('/tmp/var')

        if os.path.exists('/tmp/alignak.log'):
            os.remove('/tmp/alignak.log')

        if os.path.exists('/tmp/monitoring-logs.log'):
            os.remove('/tmp/monitoring-logs.log')

        if os.path.exists('/tmp/monitoring-log/monitoring-logs.log'):
            os.remove('/tmp/monitoring-log/monitoring-logs.log')

        print("Preparing configuration...")
        shutil.copytree('../etc', '/tmp/etc/alignak')
        files = ['/tmp/etc/alignak/alignak.ini']
        replacements = {
            '_dist=/usr/local/': '_dist=/tmp',
            'user=alignak': ';user=alignak',
            'group=alignak': ';group=alignak',
            'bindir=%(_dist_BIN)s': 'bindir='
        }
        self._files_update(files, replacements)

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
            print("- pinging %s: http://localhost:%s/ping" % (name, port))
            raw_data = self.req.get("http://localhost:%s/ping" % (port))
            data = raw_data.json()
            assert data == 'pong', "Daemon %s  did not ping back!" % name
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
            print("- stopping %s: http://localhost:%s/stop_request" % (name, port))
            raw_data = self.req.get("http://localhost:%s/stop_request?stop_now=1" % (port))
            data = raw_data.json()
            print("- response = %s" % data)
        # -----

    def test_arbiter_no_daemons(self):
        """ Run the Alignak Arbiter - all the expected daemons are missing

        :return:
        """
        # All the default configuration files are in /tmp/etc

        # Update monitoring configuration file name
        files = ['/tmp/etc/alignak/alignak.ini']
        replacements = {
            ';CFG=%(etcdir)s/alignak.cfg': 'CFG=%(etcdir)s/alignak.cfg',
            # ';log_cherrypy=1': 'log_cherrypy=1'

            'polling_interval=5': 'polling_interval=1',
            'daemons_check_period=5': '',
            ';daemons_stop_timeout=30': 'daemons_stop_timeout=5',
            ';daemons_start_timeout=1': 'daemons_start_timeout=0',
            ';daemons_new_conf_timeout=1': 'daemons_new_conf_timeout=1',
            ';daemons_dispatch_timeout=5': 'daemons_dispatch_timeout=0',

            'user=alignak': ';user=alignak',
            'group=alignak': ';group=alignak',
            #
            # ';alignak_launched=1': 'alignak_launched=1',
            # ';is_daemon=1': 'is_daemon=0'
        }
        self._files_update(files, replacements)

        args = ["../alignak/bin/alignak_arbiter.py", "-e", "/tmp/etc/alignak/alignak.ini"]
        self.procs = {'arbiter-master': subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)}
        print("%s launched (pid=%d)" % ('arbiter', self.procs['arbiter-master'].pid))

        # Sleep some few seconds because of the time needed to start the processes,
        # poll them and declare as faulty !
        sleep(30)

        # The arbiter will have stopped!

        ret = self.procs['arbiter-master'].poll()
        print("*** Arbiter exited with: %s" % ret)
        assert ret == 4
        ok = True
        for line in iter(self.procs['arbiter-master'].stdout.readline, b''):
            if b'WARNING:' in line:
                ok = False
                # Only WARNING because of missing daemons...
                if b'that we must be related with cannot be connected' in line:
                    ok = True
                if b'Add failed attempt for' in line:
                    ok = True
                if b'as dead, too much failed attempts' in line:
                    ok = True
                # if b'Exception: Server not available:' in line:
                #     ok = True
                if b'as dead :(' in line:
                    ok = True
                if b'is not alive for' in line:
                    ok = True
                if b'ignoring repeated file: ' in line:
                    ok = True
                if b'directory did not exist' in line:
                    ok = True
                if b'Cannot call the additional groups setting with ' in line:
                    ok = True
                if b'- satellites connection #1 is not correct; ' in line:
                    ok = True
                if b'- satellites connection #2 is not correct; ' in line:
                    ok = True
                if b'- satellites connection #3 is not correct; ' in line:
                    ok = True
                if ok:
                    print("... %s" % line.rstrip())
                else:
                    print(">>> %s" % line.rstrip())

                assert ok
            if b'ERROR:' in line:
                ok = False
                # Only ERROR because of connection failure exit
                if b'All the daemons connections could not be established despite 3 tries! Sorry, I bail out!' in line:
                    ok = True
                if b'Sorry, I bail out, exit code: 4' in line:
                    ok = True

                print("*** %s" % line.rstrip())
                assert ok
        assert ok

    def test_arbiter_no_daemons_no_stop(self):
        """ Run the Alignak Arbiter - all the expected daemons are missing

        :return:
        """
        # All the default configuration files are in /tmp/etc

        # Update monitoring configuration file name
        files = ['/tmp/etc/alignak/alignak.ini']
        replacements = {
            ';CFG=%(etcdir)s/alignak.cfg': 'CFG=%(etcdir)s/alignak.cfg',
            # ';log_cherrypy=1': 'log_cherrypy=1'

            'polling_interval=5': 'polling_interval=1',
            # Do not kill/exit on communication failure
            ';daemons_failure_kill=1' : 'daemons_failure_kill=0',
            'daemons_check_period=5': '',
            'daemons_stop_timeout=10': 'daemons_stop_timeout=5',
            ';daemons_start_timeout=0': 'daemons_start_timeout=0',
            ';daemons_dispatch_timeout=0': 'daemons_dispatch_timeout=0',

            'user=alignak': ';user=alignak',
            'group=alignak': ';group=alignak',
            #
            # ';alignak_launched=1': 'alignak_launched=1',
            # ';is_daemon=1': 'is_daemon=0'
        }
        self._files_update(files, replacements)

        args = ["../alignak/bin/alignak_arbiter.py", "-e", "/tmp/etc/alignak/alignak.ini"]
        self.procs = {'arbiter-master': subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)}
        print("%s launched (pid=%d)" % ('arbiter', self.procs['arbiter-master'].pid))

        # Sleep some few seconds because of the time needed to start the processes,
        # poll them and declare as faulty !
        sleep(30)

        # The arbiter will have stopped!

        ret = self.procs['arbiter-master'].poll()
        print("*** Arbiter exited with: %s" % ret)
        assert ret == 4
        ok = True
        for line in iter(self.procs['arbiter-master'].stdout.readline, b''):
            if b'WARNING:' in line:
                ok = False
                # Only WARNING because of missing daemons...
                if b'that we must be related with cannot be connected' in line:
                    ok = True
                if b'Add failed attempt for' in line:
                    ok = True
                if b'as dead, too much failed attempts' in line:
                    ok = True
                # if b'Exception: Server not available:' in line:
                #     ok = True
                if b'as dead :(' in line:
                    ok = True
                if b'is not alive for' in line:
                    ok = True
                if b'ignoring repeated file: ' in line:
                    ok = True
                if b'directory did not exist' in line:
                    ok = True
                if b'Cannot call the additional groups setting with ' in line:
                    ok = True
                if b'- satellites connection #1 is not correct; ' in line:
                    ok = True
                if b'- satellites connection #2 is not correct; ' in line:
                    ok = True
                if b'- satellites connection #3 is not correct; ' in line:
                    ok = True
                if ok:
                    print("... %s" % line.rstrip())
                else:
                    print(">>> %s" % line.rstrip())

                assert ok
            if b'ERROR:' in line:
                ok = False
                # Only ERROR because of connection failure exit
                if b'All the daemons connections could not be established despite 3 tries! Sorry, I bail out!' in line:
                    ok = True
                if b'Sorry, I bail out, exit code: 4' in line:
                    ok = True

                print("*** %s" % line.rstrip())
                assert ok
        assert ok

    def test_arbiter_daemons(self):
        """ Run the Alignak Arbiter - all the expected daemons are started by the arbiter
        and then the arbiter exits

        :return:
        """
        # All the default configuration files are in /tmp/etc

        # Update monitoring configuration file name
        files = ['/tmp/etc/alignak/alignak.ini']
        replacements = {
            ';CFG=%(etcdir)s/alignak.cfg': 'CFG=%(etcdir)s/alignak.cfg',
            ';log_cherrypy=1': 'log_cherrypy=1',

            'polling_interval=5': 'polling_interval=1',
            'daemons_check_period=5': 'daemons_check_period=2',
            'daemons_stop_timeout=10': 'daemons_stop_timeout=5',
            ';daemons_start_timeout=0': 'daemons_start_timeout=0',
            ';daemons_dispatch_timeout=0': 'daemons_dispatch_timeout=0',

            'bindir=%(_dist_BIN)s': 'bindir=',

            'user=alignak': ';user=alignak',
            'group=alignak': ';group=alignak',
            #
            ';alignak_launched=1': 'alignak_launched=1',
            # ';is_daemon=1': 'is_daemon=0'
        }
        self._files_update(files, replacements)

        args = ["../alignak/bin/alignak_arbiter.py", "-e", "/tmp/etc/alignak/alignak.ini"]
        # self.procs = {'arbiter-master': subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)}
        fnull = open(os.devnull, 'w')
        self.procs = {'arbiter-master': subprocess.Popen(args, stdout=fnull, stderr=fnull)}
        print("%s launched (pid=%d)" % ('arbiter', self.procs['arbiter-master'].pid))

        # Sleep some few seconds because of the time needed to start the processes,
        # poll them and declare as faulty !
        sleep(10)

        # The arbiter will NOT have stopped! It is still running
        ret = self.procs['arbiter-master'].poll()
        assert ret is None
        print("Started...")

        self._ping_daemons()

        # Sleep some few seconds to let the arbiter ping the daemons by itself
        sleep(30)

        self._ping_daemons()

        # This function will only send a SIGTERM to the arbiter daemon
        # self._stop_daemons(['arbiter'])
        self._stop_alignak_daemons(arbiter_only=True)

    # @pytest.mark.skip("Skip for core dumped on Travis")
    def test_arbiter_daemons_kill_one_daemon(self):
        """ Run the Alignak Arbiter - all the expected daemons are started by the arbiter
        and then a daemon is killed ... the arbiter kills all the remaining daemons
        after a while and then stops

        :return:
        """
        # All the default configuration files are in /tmp/etc

        # Update monitoring configuration file name
        # Update monitoring configuration file name
        files = ['/tmp/etc/alignak/alignak.ini']
        replacements = {
            ';CFG=%(etcdir)s/alignak.cfg': 'CFG=%(etcdir)s/alignak.cfg',
            ';log_cherrypy=1': 'log_cherrypy=1',

            'polling_interval=5': 'polling_interval=1',
            'daemons_check_period=5': 'daemons_check_period=2',
            'daemons_stop_timeout=10': 'daemons_stop_timeout=5',
            ';daemons_start_timeout=0': 'daemons_start_timeout=0',
            ';daemons_dispatch_timeout=0': 'daemons_dispatch_timeout=0',

            'user=alignak': ';user=alignak',
            'group=alignak': ';group=alignak',
            #
            ';alignak_launched=1': 'alignak_launched=1',
            # ';is_daemon=1': 'is_daemon=0'
        }
        self._files_update(files, replacements)

        args = ["../alignak/bin/alignak_arbiter.py", "-e", "/tmp/etc/alignak/alignak.ini"]
        # self.procs = {'arbiter-master': subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)}
        fnull = open(os.devnull, 'w')
        self.procs = {'arbiter-master': subprocess.Popen(args, stdout=fnull, stderr=fnull)}
        print("%s launched (pid=%d)" % ('arbiter', self.procs['arbiter-master'].pid))

        # Sleep some few seconds because of the time needed to start the processes,
        # poll them and declare as faulty !
        sleep(15)

        # The arbiter will NOT have stopped! It is still running
        ret = self.procs['arbiter-master'].poll()
        assert ret is None
        print("Started...")

        self._ping_daemons()
        sleep(2)

        print("Killing one daemon process...")
        self._stop_daemons(['receiver'])
        self._ping_daemons()
        sleep(2)

        # for daemon in ['receiver']:
        #     for proc in psutil.process_iter():
        #         if daemon not in proc.name():
        #             continue
        #         if getattr(self, 'my_pid', None) and proc.pid == self.my_pid:
        #             continue
        #         print("- killing %s" % (proc.name()))
        #
        #         try:
        #             daemon_process = psutil.Process(proc.pid)
        #         except psutil.NoSuchProcess:
        #             print("not existing!")
        #             continue
        #
        #         os.kill(proc.pid, signal.SIGKILL)
        #         time.sleep(2)
        #         # daemon_process.terminate()
        #         try:
        #             daemon_process.wait(10)
        #         except psutil.TimeoutExpired:
        #             print("***** timeout 10 seconds, force-killing the daemon...")
        #             daemon_process.kill()

        # self._ping_daemons()
        # sleep(2)

        # Sleep some few seconds to let the arbiter manage the daemon failure
        sleep(30)

        # This function will only send a SIGTERM to the arbiter daemon
        # self._stop_daemons(['arbiter'])
        self._stop_alignak_daemons(arbiter_only=True)
