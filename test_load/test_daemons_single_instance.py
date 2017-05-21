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

import os
import signal

import subprocess
from time import time, sleep
import shutil
import pytest

from alignak_test import AlignakTest


class TestDaemonsSingleInstance(AlignakTest):
    def _get_subproc_data(self, name):
        try:
            print("Polling %s" % name)
            if self.procs[name].poll():
                print("Killing %s..." % name)
                os.kill(self.procs[name].pid, signal.SIGKILL)
            print("%s terminated" % name)

        except Exception as err:
            print("Problem on terminate and wait subproc %s: %s" % (name, err))

    def setUp(self):
        os.environ['TEST_LOG_ACTIONS'] = 'WARNING'
        self.procs = {}

    def checkDaemonsLogsForErrors(self, daemons_list):
        """
        Check that the daemons all started correctly and that they got their configuration
        :return:
        """
        print("Get information from log files...")
        nb_errors = 0
        for daemon in ['arbiter'] + daemons_list:
            assert os.path.exists('/tmp/%s.log' % daemon), '/tmp/%s.log does not exist!' % daemon
            daemon_errors = False
            print("-----\n%s log file\n-----\n" % daemon)
            with open('/tmp/%s.log' % daemon) as f:
                for line in f:
                    if 'WARNING' in line or daemon_errors:
                        print(line[:-1])
                    if 'ERROR' in line or 'CRITICAL' in line:
                        if not daemon_errors:
                            print(line[:-1])
                        daemon_errors = True
                        nb_errors += 1
        print("No error logs raised when checking the daemons log")

        return nb_errors

    def tearDown(self):
        print("Test terminated!")

    def prepare_alignak_configuration(self, cfg_folder, hosts_count=10):
        """Prepare the Alignak configuration
        :return: the count of errors raised in the log files
        """
        start = time()
        filename = cfg_folder + '/test-templates/host.tpl'
        if os.path.exists(filename):
            file = open(filename, "r")
            host_pattern = file.read()

            hosts = ""
            for index in range(hosts_count):
                hosts = hosts + (host_pattern % index) + "\n"

            filename = cfg_folder + '/arbiter/objects/hosts/hosts.cfg'
            if os.path.exists(filename):
                os.remove(filename)
            with open(filename, 'w') as outfile:
                outfile.write(hosts)
        end = time()
        print("Time to prepare configuration: %d seconds" % (end - start))

    def run_and_check_alignak_daemons(self, cfg_folder, runtime=10):
        """Start and stop the Alignak daemons

        Let the daemons run for the number of seconds defined in the runtime parameter and
        then kill the required daemons (list in the spare_daemons parameter)

        Check that the run daemons did not raised any ERROR log

        :return: the count of errors raised in the log files
        """
        # Load and test the configuration
        self.setup_with_file(cfg_folder + '/alignak.cfg')
        assert self.conf_is_correct

        self.procs = {}
        daemons_list = ['broker', 'poller', 'reactionner', 'receiver', 'scheduler']

        print("Cleaning pid and log files...")
        for daemon in ['arbiter'] + daemons_list:
            if os.path.exists('/tmp/%s.pid' % daemon):
                os.remove('/tmp/%s.pid' % daemon)
                print("- removed /tmp/%s.pid" % daemon)
            if os.path.exists('/tmp/%s.log' % daemon):
                os.remove('/tmp/%s.log' % daemon)
                print("- removed /tmp/%s.log" % daemon)

        shutil.copy(cfg_folder + '/dummy_command.sh', '/tmp/dummy_command.sh')

        print("Launching the daemons...")
        start = time()
        for daemon in daemons_list:
            alignak_daemon = "../alignak/bin/alignak_%s.py" % daemon.split('-')[0]

            args = [alignak_daemon, "-c", cfg_folder + "/daemons/%s.ini" % daemon]
            self.procs[daemon] = \
                subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("- %s launched (pid=%d)" % (daemon, self.procs[daemon].pid))

        # Let the daemons start quietly...
        sleep(1)

        print("Launching master arbiter...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-c", cfg_folder + "/daemons/arbiter.ini",
                "-a", cfg_folder + "/alignak.cfg"]
        self.procs['arbiter-master'] = \
            subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("- %s launched (pid=%d)" % ('arbiter-master', self.procs['arbiter-master'].pid))

        sleep(1)

        print("Testing daemons start")
        for name, proc in self.procs.items():
            ret = proc.poll()
            if ret is not None:
                print("*** %s exited on start!" % (name))
                for line in iter(proc.stdout.readline, b''):
                    print(">>> " + line.rstrip())
                for line in iter(proc.stderr.readline, b''):
                    print(">>> " + line.rstrip())
            assert ret is None, "Daemon %s not started!" % name
            print("- %s running (pid=%d)" % (name, self.procs[daemon].pid))
        end = time()
        print("Time to start the daemons: %d seconds" % (end - start))

        # Let the arbiter build and dispatch its configuration
        # Let the schedulers get their configuration and run the first checks
        sleep(runtime)

        # Check daemons start and run
        errors_raised = self.checkDaemonsLogsForErrors(daemons_list)

        print("Stopping the daemons...")
        start = time()
        for name, proc in self.procs.items():
            print("Asking %s to end..." % name)
            os.kill(self.procs[name].pid, signal.SIGTERM)
        end = time()
        print("Time to stop the daemons: %d seconds" % (end - start))

        return errors_raised

    def test_run_1_host_5mn(self):
        """Run Alignak with one host during 5 minutes"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/default')
        self.prepare_alignak_configuration(cfg_folder, 2)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 300)
        assert errors_raised == 0

    def test_run_10_host_5mn(self):
        """Run Alignak with 10 hosts during 5 minutes"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/default')
        self.prepare_alignak_configuration(cfg_folder, 10)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 300)
        assert errors_raised == 0

    def test_run_100_host_5mn(self):
        """Run Alignak with 100 hosts during 5 minutes"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/default')
        self.prepare_alignak_configuration(cfg_folder, 50)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 600)
        assert errors_raised == 0

    def test_run_1000_host_15mn(self):
        """Run Alignak with 1000 host during 15 minutes"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/default')
        self.prepare_alignak_configuration(cfg_folder, 1000)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 300)
        assert errors_raised == 0
