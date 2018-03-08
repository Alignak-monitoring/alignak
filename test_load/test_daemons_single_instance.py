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
import psutil
import pytest

import subprocess
import time
from datetime import datetime
import shutil
from threading  import Thread

from alignak_test import AlignakTest

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()


class TestDaemonsSingleInstance(AlignakTest):
    def setUp(self):
        # Alignak logs actions and results
        # os.environ['TEST_LOG_ACTIONS'] = 'INFO'

        # Alignak logs alerts and notifications
        os.environ['TEST_LOG_ALERTS'] = 'WARNING'
        os.environ['TEST_LOG_NOTIFICATIONS'] = 'WARNING'

        # Alignak logs actions and results
        os.environ['TEST_LOG_LOOP'] = 'Yes'

        # Alignak do not run plugins but only simulate
        # os.environ['TEST_FAKE_ACTION'] = 'Yes'

        # Alignak scheduler self-monitoring - report statistics every 5 loop counts
        os.environ['TEST_LOG_MONITORING'] = ''

        # Declare environment to send stats to a file
        # os.environ['ALIGNAK_STATS_FILE'] = '/tmp/alignak.stats'
        # Those are the same as the default values:
        os.environ['ALIGNAK_STATS_FILE_LINE_FMT'] = '[#date#] #counter# #value# #uom#\n'
        os.environ['ALIGNAK_STATS_FILE_DATE_FMT'] = '%Y-%m-%d %H:%M:%S'

        self.procs = []

    def tearDown(self):
        # Let the daemons die...
        time.sleep(1)
        print("Test terminated!")

    def checkDaemonsLogsForErrors(self, daemons_list):
        """Check that the daemons log do not contain any ERROR log
        Print the WARNING and ERROR logs
        :return:
        """
        print("Get information from log files...")
        nb_errors = 0
        # Dump full arbiter log
        for daemon in ['arbiter']:
            assert os.path.exists('/tmp/%s.log' % daemon), '/tmp/%s.log does not exist!' % daemon
            print("-----\n%s log file\n-----\n" % daemon)
            with open('/tmp/%s.log' % daemon) as f:
                for line in f:
                    if 'ERROR:' in line or 'CRITICAL:' in line:
                        print(line[:-1])
                        nb_errors += 1
        # Filter other daemons log
        for daemon in daemons_list:
            assert os.path.exists('/tmp/%s.log' % daemon), '/tmp/%s.log does not exist!' % daemon
            daemon_errors = False
            print("-----\n%s log file\n-----\n" % daemon)
            with open('/tmp/%s.log' % daemon) as f:
                for line in f:
                    if 'WARNING:' in line or daemon_errors:
                        print(line[:-1])
                    if 'ERROR:' in line or 'CRITICAL:' in line:
                        print(line[:-1])
                        daemon_errors = True
                        nb_errors += 1
        if nb_errors == 0:
            print("No error logs raised when checking the daemons log")

        return nb_errors

    def checkDaemonsLogsForAlerts(self, daemons_list):
        """Check that the daemons log contain ALERT and NOTIFICATION logs
        Print the found logs
        :return:
        """
        nb_alerts = 0
        nb_notifications = 0
        nb_problems = 0
        # Filter other daemons log
        for daemon in daemons_list:
            print("-----\n%s log file\n-----\n" % daemon)
            with open('/tmp/%s.log' % daemon) as f:
                for line in f:
                    if 'SERVICE ALERT:' in line:
                        nb_alerts += 1
                        print(line[:-1])
                    if 'SERVICE NOTIFICATION:' in line:
                        nb_notifications += 1
                        print(line[:-1])
                    if 'actions never came back for the satellite' in line:
                        nb_problems += 1
                        print(line[:-1])
        print("Found: %d service alerts" % nb_alerts)
        print("Found: %d service notifications" % nb_notifications)
        print("Found: %d problems" % nb_problems)

        return nb_alerts, nb_notifications, nb_problems

    def prepare_alignak_configuration(self, cfg_folder, hosts_count=10):
        """Prepare the Alignak configuration
        :return: the count of errors raised in the log files
        """
        start = time.time()
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
        print("Preparing hosts configuration duration: %d seconds" % (time.time() - start))

    def kill_running_daemons(self):
        """Kill the running daemons

        :return:
        """
        print("Stopping the daemons...")
        start = time.time()
        for daemon in list(self.procs):
            proc = daemon['pid']
            name = daemon['name']
            print("Asking %s (pid=%d) to end..." % (name, proc.pid))
            try:
                daemon_process = psutil.Process(proc.pid)
            except psutil.NoSuchProcess:
                print("not existing!")
                continue
            children = daemon_process.children(recursive=True)
            daemon_process.terminate()
            try:
                daemon_process.wait(10)
            except psutil.TimeoutExpired:
                print("***** timeout 10 seconds...")
                daemon_process.kill()
            except psutil.NoSuchProcess:
                print("not existing!")
                pass
            # for child in children:
            #     try:
            #         print("Asking %s child (pid=%d) to end..." % (child.name(), child.pid))
            #         child.terminate()
            #     except psutil.NoSuchProcess:
            #         pass
            # gone, still_alive = psutil.wait_procs(children, timeout=10)
            # for process in still_alive:
            #     try:
            #         print("Killing %s (pid=%d)!" % (child.name(), child.pid))
            #         process.kill()
            #     except psutil.NoSuchProcess:
            #         pass
            print("%s terminated" % (name))
        print("Stopping daemons duration: %d seconds" % (time.time() - start))

    def run_and_check_alignak_daemons(self, cfg_folder, runtime=10, hosts_count=10):
        """Start and stop the Alignak daemons

        Let the daemons run for the number of seconds defined in the runtime parameter and
        then kill the required daemons (list in the spare_daemons parameter)

        Check that the run daemons did not raised any ERROR log

        :return: the count of errors raised in the log files
        """
        # Load and test the configuration
        self.setup_with_file(cfg_folder + '/alignak.cfg')
        assert self.conf_is_correct

        if os.path.exists("/tmp/checks.log"):
            os.remove('/tmp/checks.log')
            print("- removed /tmp/checks.log")

        if os.path.exists("/tmp/notifications.log"):
            os.remove('/tmp/notifications.log')
            print("- removed /tmp/notifications.log")

        self.procs = []
        daemons_list = ['poller-master', 'reactionner-master', 'receiver-master',
                        'broker-master', 'scheduler-master']

        print("Cleaning pid and log files...")
        for daemon in ['arbiter-master'] + daemons_list:
            if os.path.exists('./test_run/run/%s.pid' % daemon):
                os.remove('./test_run/run/%s.pid' % daemon)
                print("- removed ./test_run/run/%s.pid" % daemon)
            if os.path.exists('./test_run/log/%s.log' % daemon):
                os.remove('./test_run/log/%s.log' % daemon)
                print("- removed ./test_run/log/%s.log" % daemon)

        shutil.copy(cfg_folder + '/check_command.sh', '/tmp/check_command.sh')

        print("Launching the daemons...")
        start = time.time()
        for daemon in daemons_list:
            alignak_daemon = "../alignak/bin/alignak_%s.py" % daemon.split('-')[0]

            args = [alignak_daemon, "-e", cfg_folder + "/alignak.ini"]
            self.procs.append({
                'name': daemon,
                'pid': psutil.Popen(args)
            })
            print("%s: %s launched (pid=%d)" % (
                  datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S %Z"),
                  daemon, self.procs[-1]['pid'].pid))

        # Let the daemons start quietly...
        time.sleep(5)

        print("Launching arbiter...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-e", cfg_folder + "/alignak.ini",
                "-a", cfg_folder + "/alignak.cfg"]
        # Prepend the arbiter process into the list
        self.procs= [{
            'name': 'arbiter',
            'pid': psutil.Popen(args)
        }] + self.procs
        print("%s: %s launched (pid=%d)" % (
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S %Z"),
            'arbiter', self.procs[-1]['pid'].pid))

        time.sleep(1)

        print("Testing daemons start")
        for daemon in self.procs:
            proc = daemon['pid']
            name = daemon['name']
            ret = proc.poll()
            if ret is not None:
                print("*** %s exited on start!" % (name))
                for line in iter(proc.stdout.readline, b''):
                    print(">>> " + line.rstrip())
                for line in iter(proc.stderr.readline, b''):
                    print(">>> " + line.rstrip())
            daemon['started'] = ret
            print("- %s running (pid=%d)" % (name, self.procs[-1]['pid'].pid))
        print("Starting daemons duration: %d seconds" % (time.time() - start))
        for daemon in self.procs:
            started = daemon['started']
            if started is not None:
                self.kill_running_daemons()
                assert False

        # Let the arbiter build and dispatch its configuration
        # Let the schedulers get their configuration and run the first checks
        time.sleep(2)

        # Start a communication thread with the scheduler
        scheduler_stdout_queue = Queue()
        process = None
        for daemon in self.procs:
            name = daemon['name']
            if name == 'scheduler':
                process = daemon['pid']
                t = Thread(target=enqueue_output, args=(process.stdout, scheduler_stdout_queue))
                t.daemon = True  # thread dies with the program
                t.start()
                break

        duration = runtime
        while duration > 0:
            # read scheduler stdout without blocking
            try:
                line = scheduler_stdout_queue.get_nowait()
            except Empty:
                pass
            else:  # got line
                print(line[:-1])
            time.sleep(0.01)
            duration -= 0.01

        # Check daemons log
        errors_raised = self.checkDaemonsLogsForErrors(daemons_list)

        # Check daemons log for alerts and notifications
        alerts, notifications, problems = self.checkDaemonsLogsForAlerts(['scheduler'])
        print("Alerts: %d" % alerts)
        if alerts < 6 * hosts_count:
            print("***** Not enough alerts, expected: %d!" % 6 * hosts_count)
            errors_raised += 1
        print("Notifications: %d" % notifications)
        if notifications < 3 * hosts_count:
            print("***** Not enough notifications, expected: %d!" % 3 * hosts_count)
            errors_raised += 1
        print("Problems: %d" % problems)

        if not alerts or not notifications or problems:
            errors_raised += 1

        self.kill_running_daemons()

        return errors_raised

    @pytest.mark.skip("Only useful for local test - do not run on Travis build")
    def test_run_1_host_1mn(self):
        """Run Alignak with one host during 1 minute"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/default')
        hosts_count = 1
        self.prepare_alignak_configuration(cfg_folder, hosts_count)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 60, hosts_count)
        assert errors_raised == 0

    @pytest.mark.skip("Only useful for local test - do not run on Travis build")
    def test_run_1_host_5mn(self):
        """Run Alignak with one host during 5 minutes"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/default')
        hosts_count = 1
        self.prepare_alignak_configuration(cfg_folder, hosts_count)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 300, hosts_count)
        assert errors_raised == 0

    @pytest.mark.skip("Only useful for local test - do not run on Travis build")
    def test_run_1_host_15mn(self):
        """Run Alignak with one host during 15 minutes"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/default')
        hosts_count = 1
        self.prepare_alignak_configuration(cfg_folder, hosts_count)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 900, hosts_count)
        assert errors_raised == 0

    @pytest.mark.skip("Only useful for local test - do not run on Travis build")
    def test_run_10_host_5mn(self):
        """Run Alignak with 10 hosts during 5 minutes"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/default')
        hosts_count = 10
        self.prepare_alignak_configuration(cfg_folder, hosts_count)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 300, hosts_count)
        assert errors_raised == 0

    # @pytest.mark.skip("Only useful for local test - do not run on Travis build")
    def test_run_100_host_10mn(self):
        """Run Alignak with 100 hosts during 5 minutes"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/default')
        hosts_count = 100
        self.prepare_alignak_configuration(cfg_folder, hosts_count)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 300, hosts_count)
        assert errors_raised == 0

    @pytest.mark.skip("Too much load - do not run on Travis build")
    def test_run_1000_host_5mn(self):
        """Run Alignak with 1000 hosts during 5 minutes"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/default')
        hosts_count = 1000
        self.prepare_alignak_configuration(cfg_folder, hosts_count)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 300, hosts_count)
        assert errors_raised == 0

    @pytest.mark.skip("Too much load  - do not run on Travis build")
    def test_run_1000_host_15mn(self):
        """Run Alignak with 1000 hosts during 15 minutes"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/default')
        hosts_count = 1000
        self.prepare_alignak_configuration(cfg_folder, hosts_count)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 900, hosts_count)
        assert errors_raised == 0

    @pytest.mark.skip("Only useful for local test - do not run on Travis build")
    def test_passive_daemons_1_host_5mn(self):
        """Run Alignak with 1 host during 5 minutes - passive daemons"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/passive_daemons')
        hosts_count = 1
        self.prepare_alignak_configuration(cfg_folder, hosts_count)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 300, hosts_count)
        assert errors_raised == 0

    @pytest.mark.skip("Only useful for local test - do not run on Travis build")
    def test_passive_daemons_1_host_15mn(self):
        """Run Alignak with 1 host during 15 minutes - passive daemons"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/passive_daemons')
        hosts_count = 1
        self.prepare_alignak_configuration(cfg_folder, hosts_count)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 900, hosts_count)
        assert errors_raised == 0

    # @pytest.mark.skip("Only useful for local test - do not run on Travis build")
    def test_passive_daemons_100_host_5mn(self):
        """Run Alignak with 100 hosts during 5 minutes - passive daemons"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/passive_daemons')
        hosts_count = 100
        self.prepare_alignak_configuration(cfg_folder, hosts_count)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 300, hosts_count)
        assert errors_raised == 0

    @pytest.mark.skip("Too much load - do not run on Travis build")
    def test_passive_daemons_1000_host_10mn(self):
        """Run Alignak with 1000 hosts during 15 minutes - passive daemons"""

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  './cfg/passive_daemons')
        hosts_count = 1000
        self.prepare_alignak_configuration(cfg_folder, hosts_count)
        errors_raised = self.run_and_check_alignak_daemons(cfg_folder, 600, hosts_count)
        assert errors_raised == 0
