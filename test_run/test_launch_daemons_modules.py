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
import time
import signal

import subprocess
from time import sleep
import shutil

from alignak_test import AlignakTest


class LaunchDaemons(AlignakTest):
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

    def tearDown(self):
        print("Test terminated!")

    def test_daemons_modules(self):
        """Running the Alignak daemons with the default ../etc configuration

        :return: None
        """
        self._run_daemons_modules(cfg_folder='../etc',
                                  tmp_folder='./run/test_launch_daemons_modules')

    def test_daemons_modules_1(self):
        """Running the Alignak daemons with a simple configuration

        :return: None
        """
        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cfg/run_daemons_1')

        # Currently it is the same as the default execution ... to be modified later.
        cfg_modules = {
            'arbiter': 'Example', 'scheduler': 'Example', 'broker': 'Example',
            'poller': 'Example', 'reactionner': 'Example', 'receiver': 'Example',
        }
        self._run_daemons_modules(cfg_folder=cfg_folder,
                                  tmp_folder='./run/test_launch_daemons_modules_1',
                                  cfg_modules=cfg_modules)

    def _run_daemons_modules(self, cfg_folder='../etc',
                             tmp_folder='./run/test_launch_daemons_modules',
                             cfg_modules=None):
        """Update the provided configuration with some informations on the run
        Run the Alignak daemons with configured modules

        :return: None
        """
        self.print_header()

        # copy etc config files in test/run/test_launch_daemons_modules and change folder
        # in the files for pid and log files
        if os.path.exists(tmp_folder):
            shutil.rmtree(tmp_folder)

        shutil.copytree(cfg_folder, tmp_folder)
        files = [tmp_folder + '/daemons/arbiterd.ini',
                 tmp_folder + '/daemons/brokerd.ini',
                 tmp_folder + '/daemons/pollerd.ini',
                 tmp_folder + '/daemons/reactionnerd.ini',
                 tmp_folder + '/daemons/receiverd.ini',
                 tmp_folder + '/daemons/schedulerd.ini',
                 tmp_folder + '/alignak.cfg',
                 tmp_folder + '/arbiter/daemons/arbiter-master.cfg',
                 tmp_folder + '/arbiter/daemons/broker-master.cfg',
                 tmp_folder + '/arbiter/daemons/poller-master.cfg',
                 tmp_folder + '/arbiter/daemons/reactionner-master.cfg',
                 tmp_folder + '/arbiter/daemons/receiver-master.cfg',
                 tmp_folder + '/arbiter/daemons/scheduler-master.cfg']
        replacements = {
            '/usr/local/var/run/alignak': '/tmp',
            '/usr/local/var/log/alignak': '/tmp',
        }
        for filename in files:
            lines = []
            with open(filename) as infile:
                for line in infile:
                    for src, target in replacements.iteritems():
                        line = line.replace(src, target)
                    lines.append(line)
            with open(filename, 'w') as outfile:
                for line in lines:
                    outfile.write(line)

        # declare modules in the daemons configuration
        if cfg_modules is None:
            shutil.copy('./cfg/default/mod-example.cfg', tmp_folder + '/arbiter/modules')
            cfg_modules = {
                'arbiter': 'Example', 'scheduler': 'Example', 'broker': 'Example',
                'poller': 'Example', 'reactionner': 'Example', 'receiver': 'Example',
            }

        print("Setting up daemons modules configuration...")
        for daemon in ['arbiter', 'scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            if daemon not in cfg_modules:
                continue

            filename = tmp_folder + '/arbiter/daemons/%s-master.cfg' % daemon
            replacements = {'modules': 'modules ' + cfg_modules[daemon]}
            lines = []
            with open(filename) as infile:
                for line in infile:
                    for src, target in replacements.iteritems():
                        line = line.replace(src, target)
                    lines.append(line)
            with open(filename, 'w') as outfile:
                for line in lines:
                    outfile.write(line)

        self.setup_with_file(tmp_folder + '/alignak.cfg')
        assert self.conf_is_correct

        print("Cleaning pid and log files...")
        for daemon in ['arbiter', 'scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            if os.path.exists('/tmp/%sd.pid' % daemon):
                os.remove('/tmp/%sd.pid' % daemon)
                print("- removed /tmp/%sd.pid" % daemon)
            if os.path.exists('/tmp/%sd.log' % daemon):
                os.remove('/tmp/%sd.log' % daemon)
                print("- removed /tmp/%sd.log" % daemon)

        print("Launching the daemons...")
        self.procs = {}
        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            args = ["../alignak/bin/alignak_%s.py" %daemon,
                    "-c", tmp_folder + "/daemons/%sd.ini" % daemon]
            self.procs[daemon] = \
                subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            sleep(0.1)
            print("- %s launched (pid=%d)" % (daemon, self.procs[daemon].pid))

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
            print("%s running (pid=%d)" % (name, self.procs[daemon].pid))

        # Let the daemons initialize ...
        sleep(3)

        print("Testing pid files and log files...")
        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            assert os.path.exists('/tmp/%sd.pid' % daemon), '/tmp/%sd.pid does not exist!' % daemon
            assert os.path.exists('/tmp/%sd.log' % daemon), '/tmp/%sd.log does not exist!' % daemon

        sleep(1)

        print("Launching arbiter...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-c", tmp_folder + "/daemons/arbiterd.ini",
                "-a", tmp_folder + "/alignak.cfg"]
        self.procs['arbiter'] = \
            subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', self.procs['arbiter'].pid))

        sleep(1)

        name = 'arbiter'
        print("Testing Arbiter start %s" % name)
        ret = self.procs[name].poll()
        if ret is not None:
            print("*** %s exited on start!" % (name))
            for line in iter(self.procs[name].stdout.readline, b''):
                print(">>> " + line.rstrip())
            for line in iter(self.procs[name].stderr.readline, b''):
                print(">>> " + line.rstrip())
        assert ret is None, "Daemon %s not started!" % name
        print("%s running (pid=%d)" % (name, self.procs[name].pid))

        sleep(1)

        print("Testing pid files and log files...")
        for daemon in ['arbiter']:
            assert os.path.exists('/tmp/%sd.pid' % daemon), '/tmp/%sd.pid does not exist!' % daemon
            assert os.path.exists('/tmp/%sd.log' % daemon), '/tmp/%sd.log does not exist!' % daemon

        # Let the arbiter build and dispatch its configuration
        sleep(5)

        print("Get module information from log files...")
        nb_errors = 0
        for daemon in ['arbiter', 'scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            assert os.path.exists('/tmp/%sd.log' % daemon), '/tmp/%sd.log does not exist!' % daemon
            daemon_errors = False
            print("-----\n%s log file\n-----\n" % daemon)
            with open('/tmp/%sd.log' % daemon) as f:
                for line in f:
                    if '***' in line:
                        print("Coverage log: %s" % line)
                    if 'Example' in line:
                        print("Example module log: %s" % line)
                    if 'WARNING' in line or daemon_errors:
                        print(line)
                    if 'ERROR' in line or 'CRITICAL' in line:
                        if not daemon_errors:
                            print(line[:-1])
                        daemon_errors = True
                        nb_errors += 1
        assert nb_errors == 0, "Error logs raised!"
        print("No error logs raised when daemons loaded the modules")

        print("Stopping the daemons...")
        for name, proc in self.procs.items():
            print("Asking %s to end..." % name)
            os.kill(self.procs[name].pid, signal.SIGTERM)

        time.sleep(1)

        for name, proc in self.procs.items():
            data = self._get_subproc_data(name)
            print("%s stdout:" % (name))
            for line in iter(proc.stdout.readline, b''):
                print(">>> " + line.rstrip())
            print("%s stderr:" % (name))
            for line in iter(proc.stderr.readline, b''):
                print(">>> " + line.rstrip())

        print("Daemons stopped")
