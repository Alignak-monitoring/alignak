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
from time import sleep
import shutil
import pytest

from alignak_test import AlignakTest


class TestLaunchDaemonsSpare(AlignakTest):
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
        self.procs = {}

    def checkDaemonsLogsForErrors(self, daemons_list):
        """
        Check that the daemons all started correctly and that they got their configuration
        :return:
        """
        print("Get information from log files...")
        nb_errors = 0
        # @mohierf: Not yet a spare arbiter
        # for daemon in ['arbiter-master', 'arbiter-spare'] + daemons_list:
        for daemon in ['arbiter-master'] + daemons_list:
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
        print("No error logs raised when daemons loaded the modules")

        return nb_errors

    def tearDown(self):
        print("Test terminated!")

    def run_and_check_alignak_daemons(self, runtime=10, spare_daemons= []):
        """ Run the Alignak daemons for a spare configuration

        Let the daemons run for the number of seconds defined in the runtime parameter and
        then kill the required daemons (list in the spare_daemons parameter)

        Check that the run daemons did not raised any ERROR log

        :return: None
        """
        # Load and test the configuration
        self.setup_with_file('cfg/alignak_full_run_spare/alignak.cfg')
        assert self.conf_is_correct

        self.procs = {}
        daemons_list = ['broker', 'broker-spare',
                        'poller', 'poller-spare',
                        'reactionner', 'reactionner-spare',
                        'receiver', 'receiver-spare',
                        'scheduler', 'scheduler-spare']

        print("Cleaning pid and log files...")
        for daemon in ['arbiter-master', 'arbiter-spare'] + daemons_list:
            if os.path.exists('/tmp/%s.pid' % daemon):
                os.remove('/tmp/%s.pid' % daemon)
                print("- removed /tmp/%s.pid" % daemon)
            if os.path.exists('/tmp/%s.log' % daemon):
                os.remove('/tmp/%s.log' % daemon)
                print("- removed /tmp/%s.log" % daemon)

        shutil.copy('./cfg/alignak_full_run_spare/dummy_command.sh', '/tmp/dummy_command.sh')

        print("Launching the daemons...")
        for daemon in daemons_list:
            alignak_daemon = "../alignak/bin/alignak_%s.py" % daemon.split('-')[0]

            args = [alignak_daemon, "-c", "./cfg/alignak_full_run_spare/daemons/%s.ini" % daemon]
            self.procs[daemon] = \
                subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("- %s launched (pid=%d)" % (daemon, self.procs[daemon].pid))

        # Let the daemons start ...
        sleep(1)

        # @mohierf: Not yet a spare arbiter
        # print("Launching spare arbiter...")
        # # Note the -n parameter in the comand line arguments!
        # args = ["../alignak/bin/alignak_arbiter.py",
        #         "-c", "cfg/alignak_full_run_spare/daemons/arbiter-spare.ini",
        #         "-a", "cfg/alignak_full_run_spare/alignak.cfg",
        #         "-n", "arbiter-spare"]
        # self.procs['arbiter-spare'] = \
        #     subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # print("- %s launched (pid=%d)" % ('arbiter-spare', self.procs['arbiter-spare'].pid))

        print("Launching master arbiter...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-c", "cfg/alignak_full_run_spare/daemons/arbiter.ini",
                "-a", "cfg/alignak_full_run_spare/alignak.cfg"]
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

        # Let the arbiter build and dispatch its configuration
        # Let the schedulers get their configuration and run the first checks
        sleep(runtime)

        # Test with poller
        # Kill the master poller
        print("Killing master poller...")
        os.kill(self.procs['poller'].pid, signal.SIGTERM)

        # Wait a while for the spare poller to be activated
        # 3 attempts, 5 seconds each
        sleep(60)

        # Test with scheduler
        # # Kill the master scheduler
        # print("Killing master scheduler...")
        # os.kill(self.procs['scheduler'].pid, signal.SIGTERM)
        #
        # # Wait a while for the spare scheduler to be activated
        # # 3 attempts, 5 seconds each
        # sleep(20)

        # Test with arbiter
        # @mohierf: Not yet a spare arbiter
        # # Kill the master arbiter
        # print("Killing master arbiter...")
        # os.kill(self.procs['arbiter-master'].pid, signal.SIGTERM)
        #
        # # Wait a while for the spare arbiter to detect that master is dead
        # # 3 attempts, 5 seconds each
        # sleep(20)
        #
        # print("Launching master arbiter...")
        # args = ["../alignak/bin/alignak_arbiter.py",
        #         "-c", "cfg/alignak_full_run_spare/daemons/arbiter.ini",
        #         "-a", "cfg/alignak_full_run_spare/alignak.cfg"]
        # self.procs['arbiter-master'] = \
        #     subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # print("- %s launched (pid=%d)" % ('arbiter-master', self.procs['arbiter-master'].pid))
        #
        # # Wait a while for the spare arbiter detect that master is back
        # sleep(runtime)

        # Check daemons start and run
        errors_raised = self.checkDaemonsLogsForErrors(daemons_list)

        print("Stopping the daemons...")
        for name, proc in self.procs.items():
            print("Asking %s to end..." % name)
            os.kill(self.procs[name].pid, signal.SIGTERM)

        assert errors_raised == 0, "Some error logs were raised!"

    def test_daemons_spare(self):
        """ Running the Alignak daemons for a spare configuration

        :return: None
        """
        self.print_header()

        self.run_and_check_alignak_daemons()
