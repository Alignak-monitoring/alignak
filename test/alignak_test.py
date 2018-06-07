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

"""
    This file contains classes and utilities for Alignak tests modules
"""

import os
import sys
import signal
import time
import string
import re
import locale
import traceback

import requests
import configparser

from six import string_types

import shutil
import psutil
import subprocess
import threading

from copy import deepcopy

import unittest2

import logging
from logging import Handler, Formatter
from logging.handlers import TimedRotatingFileHandler

import requests_mock

import alignak
from alignak.log import setup_logger, ALIGNAK_LOGGER_NAME, ColorStreamHandler, CollectorHandler
from alignak.bin.alignak_environment import AlignakConfigParser
from alignak.objects.config import Config
from alignak.objects.command import Command
from alignak.objects.module import Module

from alignak.dispatcher import Dispatcher
from alignak.scheduler import Scheduler
from alignak.macroresolver import MacroResolver
from alignak.external_command import ExternalCommandManager, ExternalCommand
from alignak.check import Check
from alignak.message import Message
from alignak.misc.serialization import serialize, unserialize
from alignak.objects.arbiterlink import ArbiterLink
from alignak.objects.schedulerlink import SchedulerLink
from alignak.objects.pollerlink import PollerLink
from alignak.objects.reactionnerlink import ReactionnerLink
from alignak.objects.brokerlink import BrokerLink
from alignak.objects.satellitelink import SatelliteLink
from alignak.notification import Notification
from alignak.modulesmanager import ModulesManager
from alignak.basemodule import BaseModule

from alignak.brok import Brok
from alignak.misc.common import DICT_MODATTR

from alignak.daemons.schedulerdaemon import Alignak
from alignak.daemons.brokerdaemon import Broker
from alignak.daemons.arbiterdaemon import Arbiter
from alignak.daemons.receiverdaemon import Receiver

class AlignakTest(unittest2.TestCase):

    if sys.version_info < (2, 7):
        def assertRegex(self, *args, **kwargs):
            return self.assertRegex(*args, **kwargs)

    def setUp(self):
        """All tests initialization:
        - output test identifier
        - setup test logger
        - track running Alignak daemons
        - output system cpu/memory
        """
        self.my_pid = os.getpid()

        print("\n" + self.id())
        print("-" * 80)
        print("Test current working directory: %s" % (os.getcwd()))

        # Configure Alignak logger with test configuration
        logger_configuration_file = os.path.join(os.getcwd(), './etc/alignak-logger.json')
        print("Logger configuration: %s" % logger_configuration_file)
        try:
            os.makedirs('/tmp/monitoring-log')
        except OSError as exp:
            pass
        self.former_log_level = None
        setup_logger(logger_configuration_file, log_dir=None, process_name='', log_file='')
        self.logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        self.logger_.warning("Test: %s", self.id())

        # To make sure that no running daemon exist
        print("Checking Alignak running daemons...")
        running_daemons = False
        for daemon in ['broker', 'poller', 'reactionner', 'receiver', 'scheduler', 'arbiter']:
            for proc in psutil.process_iter():
                if 'alignak' in proc.name() and daemon in proc.name():
                    running_daemons = True
        if running_daemons:
            self._stop_alignak_daemons(arbiter_only=False)
            # assert False, "*** Found a running Alignak daemon: %s" % (proc.name())

        print("System information:")
        perfdatas = []
        cpu_count = psutil.cpu_count()
        perfdatas.append("'cpu_count'=%d" % cpu_count)

        cpu_percents = psutil.cpu_percent(percpu=True)
        cpu = 1
        for percent in cpu_percents:
            perfdatas.append("'cpu_%d_percent'=%.2f%%" % (cpu, percent))
            cpu += 1
        print("-> cpu: %s" % " ".join(perfdatas))

        perfdatas = []
        virtual_memory = psutil.virtual_memory()
        for key in virtual_memory._fields:
            if 'percent' in key:
                perfdatas.append("'mem_percent_used_%s'=%.2f%%"
                                 % (key, getattr(virtual_memory, key)))

        swap_memory = psutil.swap_memory()
        for key in swap_memory._fields:
            if 'percent' in key:
                perfdatas.append("'swap_used_%s'=%.2f%%"
                                 % (key, getattr(swap_memory, key)))

        print("-> memory: %s" % " ".join(perfdatas))
        print(("-" * 80) + "\n")

    def tearDown(self):
        """Test ending:
        - restore initial log level if it got changed
        """
        # Clear Alignak unit tests log list
        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for handler in logger_.handlers:
            if getattr(handler, '_name', None) == 'unit_tests':
                print("Log handler %s, stored %d logs" % (handler._name, len(handler.collector)))
                handler.collector = []
                # Restore the collector logger log level
                if self.former_log_level:
                    handler.level = self.former_log_level
                break

    def set_unit_tests_logger_level(self, log_level=logging.DEBUG):
        """Set the test logger at the provided level -
        useful for some tests that check debug log
        """
        # Change the logger and its hadlers log level
        print("Set unit_tests logger: %s" % log_level)
        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        logger_.setLevel(log_level)
        for handler in logger_.handlers:
            print("- handler: %s" % handler)
            handler.setLevel(log_level)
            if getattr(handler, '_name', None) == 'unit_tests':
                self.former_log_level = handler.level
                handler.setLevel(log_level)
                print("Unit tests handler is set at debug!")
                # break

    def _prepare_hosts_configuration(self, cfg_folder, hosts_count=10,
                                     target_file_name=None, realms=None):
        """Prepare the Alignak configuration
        :return: the count of errors raised in the log files
        """
        start = time.time()
        if realms is None:
            realms = ['All']
        filename = cfg_folder + '/test-templates/host.tpl'
        if os.path.exists(filename):
            with open(filename, "r") as pattern_file:
                host_pattern = pattern_file.read()
                host_pattern = host_pattern.decode('utf-8')
        else:
            host_pattern = """
define host {
    use                     test-host
    contact_groups          admins
    host_name               host-%s-%s
    address                 127.0.0.1
    realm                   %s
}
"""

        hosts = ""
        hosts_set = 0
        for realm in realms:
            for index in range(hosts_count):
                hosts = hosts + (host_pattern % (realm.lower(), index, realm)) + "\n"
                hosts_set += 1

        filename = os.path.join(cfg_folder, 'many_hosts_%d.cfg' % hosts_count)
        if target_file_name is not None:
            filename = os.path.join(cfg_folder, target_file_name)
        if os.path.exists(filename):
            os.remove(filename)
        with open(filename, 'w') as outfile:
            outfile.write(hosts)

        print("Prepared a configuration with %d hosts, duration: %d seconds"
              % (hosts_set, (time.time() - start)))

    def _prepare_configuration(self, copy=True, cfg_folder='/tmp/alignak', daemons_list=None):
        if daemons_list is None:
            daemons_list = ['arbiter-master', 'scheduler-master', 'broker-master',
                            'poller-master', 'reactionner-master', 'receiver-master']

        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), cfg_folder)

        # Copy the default Alignak shipped configuration to the run directory
        if copy:
            print("Copy default configuration (../etc) to %s..." % cfg_folder)
            if os.path.exists('%s/etc' % cfg_folder):
                shutil.rmtree('%s/etc' % cfg_folder)
            shutil.copytree('../etc', '%s/etc' % cfg_folder)

        # Load and update the configuration
        for f in ['alignak.log', 'monitoring-logs.log', 'monitoring-log/monitoring-logs.log']:
            if os.path.exists('%s/log/%s' % (cfg_folder, f)):
                os.remove('%s/log/%s' % (cfg_folder, f))

        # Clean the former existing pid and log files
        print("Cleaning pid and log files...")
        for daemon in daemons_list:
            if os.path.exists('%s/run/%s.pid' % (cfg_folder, daemon)):
                print("- removing pid %s/run/%s.pid" % (cfg_folder, daemon))
                os.remove('%s/run/%s.pid' % (cfg_folder, daemon))
            if os.path.exists('%s/log/%s.log' % (cfg_folder, daemon)):
                print("- removing log %s/log/%s.log" % (cfg_folder, daemon))
                os.remove('%s/log/%s.log' % (cfg_folder, daemon))

        # Update monitoring configuration parameters
        files = ['%s/etc/alignak.ini' % cfg_folder,
                 '%s/etc/alignak.d/daemons.ini' % cfg_folder,
                 '%s/etc/alignak.d/modules.ini' % cfg_folder]
        print("Configuration files: %s" % files)
        # Update monitoring configuration file variables
        try:
            cfg = configparser.ConfigParser()
            cfg.read(files)

            # Configuration directories
            cfg.set('DEFAULT', '_dist', cfg_folder)
            # Do not set a specific bin directory to use the default Alignak one
            cfg.set('DEFAULT', '_dist_BIN', '')
            cfg.set('DEFAULT', '_dist_ETC', '%s/etc' % cfg_folder)
            cfg.set('DEFAULT', '_dist_VAR', '%s/var' % cfg_folder)
            cfg.set('DEFAULT', '_dist_RUN', '%s/run' % cfg_folder)
            cfg.set('DEFAULT', '_dist_LOG', '%s/log' % cfg_folder)

            # Nagios legacy files
            cfg.set('alignak-configuration', 'cfg', '%s/etc/alignak.cfg' % cfg_folder)

            # Daemons launching and check
            cfg.set('alignak-configuration', 'polling_interval', '1')
            cfg.set('alignak-configuration', 'daemons_check_period', '1')
            cfg.set('alignak-configuration', 'daemons_stop_timeout', '10')
            cfg.set('alignak-configuration', 'daemons_start_timeout', '1')
            cfg.set('alignak-configuration', 'daemons_new_conf_timeout', '1')
            cfg.set('alignak-configuration', 'daemons_dispatch_timeout', '1')

            # Poller/reactionner workers count limited to 1
            cfg.set('alignak-configuration', 'min_workers', '1')
            cfg.set('alignak-configuration', 'max_workers', '1')

            with open('%s/etc/alignak.ini' % cfg_folder, "w") as modified:
                cfg.write(modified)
        except Exception as exp:
            print("* parsing error in config file: %s" % exp)
            assert False

    def _files_update(self, files, replacements):
        """Update files content with the defined replacements

        :param files: list of files to parse and replace
        :param replacements: list of values to replace
        :return:
        """
        for filename in files:
            lines = []
            with open(filename) as infile:
                for line in infile:
                    for src, target in replacements.items():
                        line = line.replace(src, target)
                    lines.append(line)
            with open(filename, 'w') as outfile:
                for line in lines:
                    outfile.write(line)

    def _stop_alignak_daemons(self, arbiter_only=True, request_stop_uri=''):
        """ Stop the Alignak daemons started formerly

        If request_stop is not set, the this function will try so stop the daemons with the
        /stop_request API, else it will directly send a kill signal.

        If some alignak- daemons are still running after the kill, force kill them.

        :return: None
        """

        print("Stopping the daemons...")
        start = time.time()
        if request_stop_uri:
            req = requests.Session()
            raw_data = req.get("%s/stop_request" % request_stop_uri, params={'stop_now': '1'})
            data = raw_data.json()

            # Let the process 20 seconds to exit
            time.sleep(20)

            no_daemons = True
            for daemon in ['broker', 'poller', 'reactionner', 'receiver', 'scheduler', 'arbiter']:
                for proc in psutil.process_iter():
                    try:
                        if daemon not in proc.name():
                            continue
                        if getattr(self, 'my_pid', None) and proc.pid == self.my_pid:
                            continue

                        print("- ***** remaining %s / %s" % (proc.name(), proc.status()))
                        if proc.status() == 'running':
                            no_daemons = False
                    except psutil.NoSuchProcess:
                        print("not existing!")
                        continue
                    except psutil.TimeoutExpired:
                        print("***** timeout 10 seconds, force-killing the daemon...")
            # Do not assert because some processes are sometimes zombies that are
            # removed by the Python GC
            # assert no_daemons
            return

        if getattr(self, 'procs', None):
            for name, proc in list(self.procs.items()):
                if arbiter_only and name not in ['arbiter-master']:
                    continue
                if proc.pid == self.my_pid:
                    print("- do not kill myself!")
                    continue
                print("Asking %s (pid=%d) to end..." % (name, proc.pid))
                try:
                    daemon_process = psutil.Process(proc.pid)
                except psutil.NoSuchProcess:
                    print("not existing!")
                    continue
                # children = daemon_process.children(recursive=True)
                daemon_process.terminate()
                try:
                    # The default arbiter / daemons stopping process is 30 seconds graceful ... so
                    # not really compatible with this default delay. The test must update the
                    # default delay or set a shorter delay than the default one
                    daemon_process.wait(10)
                except psutil.TimeoutExpired:
                    print("***** stopping timeout 10 seconds, force-killing the daemon...")
                    daemon_process.kill()
                except psutil.NoSuchProcess:
                    print("not existing!")
                    pass
                print("%s terminated" % (name))
            print("Stopping daemons duration: %d seconds" % (time.time() - start))

        time.sleep(1.0)

        print("Killing remaining processes...")
        for daemon in ['broker', 'poller', 'reactionner', 'receiver', 'scheduler', 'arbiter']:
            for proc in psutil.process_iter():
                try:
                    if daemon not in proc.name():
                        continue
                    if getattr(self, 'my_pid', None) and proc.pid == self.my_pid:
                        continue

                    print("- killing %s" % (proc.name()))
                    daemon_process = psutil.Process(proc.pid)
                    daemon_process.terminate()
                    daemon_process.wait(10)
                except psutil.NoSuchProcess:
                    print("not existing!")
                    continue
                except psutil.TimeoutExpired:
                    print("***** timeout 10 seconds, force-killing the daemon...")
                    daemon_process.kill()

    def _run_command_with_timeout(self, cmd, timeout_sec):
        """Execute `cmd` in a subprocess and enforce timeout `timeout_sec` seconds.

        Return subprocess exit code on natural completion of the subprocess.
        Returns None if timeout expires before subprocess completes."""
        start = time.time()
        proc = subprocess.Popen(cmd)
        print("%s launched (pid=%d)" % (cmd, proc.pid))
        timer = threading.Timer(timeout_sec, proc.kill)
        timer.start()
        proc.communicate()
        if timer.is_alive():
            # Process completed naturally - cancel timer and return exit code
            timer.cancel()
            print("-> exited with %s after %.2d seconds" % (proc.returncode, time.time() - start))
            return proc.returncode
        # Process killed by timer - raise exception
        print('Process #%d killed after %f seconds' % (proc.pid, timeout_sec))
        return None

    def _run_alignak_daemons(self, cfg_folder='/tmp/alignak', runtime=30,
                             daemons_list=None, spare_daemons=[], piped=False, run_folder='',
                             arbiter_only=True, update_configuration=True):
        """ Run the Alignak daemons for a passive configuration

        Let the daemons run for the number of seconds defined in the runtime parameter and
        then kill the required daemons (list in the spare_daemons parameter)

        Check that the run daemons did not raised any ERROR log

        :return: None
        """
        if daemons_list is None:
            daemons_list = [
                'scheduler-master', 'broker-master',
                'poller-master', 'reactionner-master', 'receiver-master'
            ]
        # Load and test the configuration
        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), cfg_folder)
        if not run_folder:
            run_folder = cfg_folder
        print("Running Alignak daemons, cfg_folder: %s, run_folder: %s" % (cfg_folder, run_folder))

        for f in ['alignak.log', 'monitoring-logs.log', 'monitoring-log/monitoring-logs.log']:
            if os.path.exists('%s/log/%s' % (cfg_folder, f)):
                os.remove('%s/log/%s' % (cfg_folder, f))

        # Clean the former existing pid and log files
        print("Cleaning pid and log files...")
        for daemon in daemons_list + ['arbiter-master']:
            if os.path.exists('%s/run/%s.pid' % (run_folder, daemon)):
                print("- removing pid %s/run/%s.pid" % (run_folder, daemon))
                os.remove('%s/run/%s.pid' % (run_folder, daemon))
            if os.path.exists('%s/log/%s.log' % (run_folder, daemon)):
                print("- removing log %s/log/%s.log" % (run_folder, daemon))
                os.remove('%s/log/%s.log' % (run_folder, daemon))

        # Update monitoring configuration parameters
        if update_configuration:
            files = ['%s/etc/alignak.ini' % cfg_folder,
                     '%s/etc/alignak.d/daemons.ini' % cfg_folder,
                     '%s/etc/alignak.d/modules.ini' % cfg_folder]
            print("Configuration files: %s" % files)
            # Update monitoring configuration file variables
            try:
                cfg = configparser.ConfigParser()
                cfg.read(files)

                # Configuration directories
                cfg.set('DEFAULT', '_dist', cfg_folder)
                # Do not set a specific bin directory to use the default Alignak one
                cfg.set('DEFAULT', '_dist_BIN', '')
                cfg.set('DEFAULT', '_dist_ETC', '%s/etc' % cfg_folder)
                cfg.set('DEFAULT', '_dist_VAR', '%s/var' % run_folder)
                cfg.set('DEFAULT', '_dist_RUN', '%s/run' % run_folder)
                cfg.set('DEFAULT', '_dist_LOG', '%s/log' % run_folder)

                # Nagios legacy files
                cfg.set('alignak-configuration', 'cfg', '%s/etc/alignak.cfg' % cfg_folder)

                # Daemons launching and check
                cfg.set('alignak-configuration', 'polling_interval', '1')
                cfg.set('alignak-configuration', 'daemons_check_period', '1')
                cfg.set('alignak-configuration', 'daemons_stop_timeout', '20')
                cfg.set('alignak-configuration', 'daemons_start_timeout', '5')
                cfg.set('alignak-configuration', 'daemons_new_conf_timeout', '1')
                cfg.set('alignak-configuration', 'daemons_dispatch_timeout', '1')

                # Poller/reactionner workers count limited to 1
                cfg.set('alignak-configuration', 'min_workers', '1')
                cfg.set('alignak-configuration', 'max_workers', '1')

                with open('%s/etc/alignak.ini' % cfg_folder, "w") as modified:
                    cfg.write(modified)
            except Exception as exp:
                print("* parsing error in config file: %s" % exp)
                assert False

        # If some Alignak daemons are still running...
        self._stop_alignak_daemons()

        # # # Some script commands may exist in the test folder ...
        # if os.path.exists(cfg_folder + '/dummy_command.sh'):
        #     shutil.copy(cfg_folder + '/dummy_command.sh', '/tmp/dummy_command.sh')
        #
        print("Launching the daemons...")
        self.procs = {}
        for name in daemons_list + ['arbiter-master']:
            if arbiter_only and name not in ['arbiter-master']:
                continue
            args = ["../alignak/bin/alignak_%s.py" % name.split('-')[0], "-n", name,
                    "-e", "%s/etc/alignak.ini" % cfg_folder]
            print("- %s arguments: %s" % (name, args))
            if piped:
                print("- capturing stdout/stderr" % name)
                self.procs[name] = \
                    subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                self.procs[name] = subprocess.Popen(args)

            time.sleep(0.1)
            print("- %s launched (pid=%d)" % (name, self.procs[name].pid))

        time.sleep(3)

        print("Testing daemons start")
        for name, proc in list(self.procs.items()):
            ret = proc.poll()
            if ret is not None:
                print("*** %s exited on start!" % (name))
                if os.path.exists("/tmp/alignak.log"):
                    with open("/tmp/alignak.log") as f:
                        for line in f:
                            print("xxx %s" % line)

                if os.path.exists("%s/log/arbiter-master.log" % cfg_folder):
                    with open("%s/log/arbiter-master.log" % cfg_folder) as f:
                        for line in f:
                            print("... %s" % line)

                if proc.stdout:
                    for line in iter(proc.stdout.readline, b''):
                        print(">>> " + str(line).rstrip())
                else:
                    print("No stdout!")
                if proc.stderr:
                    for line in iter(proc.stderr.readline, b''):
                        print(">>> " + str(line).rstrip())
                else:
                    print("No stderr!")
            assert ret is None, "Daemon %s not started!" % name
            print("%s running (pid=%d)" % (name, self.procs[name].pid))

        # Let the daemons start ...
        time.sleep(3)

        print("Testing pid files and log files...")
        for name in daemons_list + ['arbiter-master']:
            if arbiter_only and name not in ['arbiter-master']:
                continue
            print("- %s for %s" % ('%s/run/%s.pid' % (run_folder, name), name))
            # Some times pid and log files may not exist ...
            if not os.path.exists('%s/run/%s.pid' % (run_folder, name)):
                print('%s/run/%s.pid does not exist!' % (run_folder, name))
            print("- %s for %s" % ('%s/log/%s.log' % (run_folder, name), name))
            if not os.path.exists('%s/log/%s.log' % (run_folder, name)):
                print('%s/log/%s.log does not exist!' % (run_folder, name))

        time.sleep(1)

        # Let the arbiter build and dispatch its configuration
        # Let the schedulers get their configuration and run the first checks
        time.sleep(runtime)

    def _check_daemons_log_for_errors(self, daemons_list, run_folder='/tmp/alignak',
                                      ignored_warnings=None, ignored_errors=None, dump_all=True):
        """
        Check that the daemons all started correctly and that they got their configuration
        ignored_warnings and ignored_errors are lists of strings that make a WARNING or ERROR log
        not to be considered as a warning or error

        :return:
        """
        print("Get information from log files...")
        travis_run = 'TRAVIS' in os.environ

        if ignored_warnings is None:
            ignored_warnings = []
        ignored_warnings.extend([
            u'Cannot call the additional groups setting ',
            u'loop exceeded the maximum expected',
            u'ignoring repeated file'
        ])
        nb_errors = 0
        nb_warnings = 0
        for daemon in ['arbiter-master'] + daemons_list:
            assert os.path.exists("/%s/log/%s.log" % (run_folder, daemon)), '/%s/log/%s.log does not exist!' % (run_folder, daemon)
            daemon_errors = False
            print("-----\n%s log file: %s\n-----\n" % (daemon,
                                                       '/%s/log/%s.log' % (run_folder, daemon)))
            with open('/%s/log/%s.log' % (run_folder, daemon)) as f:
                for line in f:
                    if 'WARNING: ' in line or daemon_errors:
                        if dump_all and not travis_run:
                            print(line[:-1])
                        for ignore_line in ignored_warnings:
                            if ignore_line in line:
                                break
                        else:
                            nb_warnings += 1
                            print("-W-" + line[:-1])
                    if 'ERROR: ' in line or 'CRITICAL: ' in line:
                        if dump_all and not daemon_errors:
                            print(line[:-1])
                        for ignore_line in ignored_errors:
                            if ignore_line in line:
                                break
                        else:
                            nb_errors += 1
                            print("*E*" + line[:-1])
                        if nb_errors > 0:
                            daemon_errors = True

        return (nb_errors, nb_warnings)

    def setup_with_file(self, configuration_file=None, env_file=None,
                        verbose=False, unit_test=True):
        """
        Load alignak with the provided configuration and environment files

        If verbose is True the envirnment loading is printed out on the console.

        If the configuration loading fails, a SystemExit exception is raised to the caller.

        The conf_is_correct property indicates if the configuration loading succeeded or failed.

        The configuration errors property contains a list of the error message that are normally
        logged as ERROR by the arbiter.

        If unit_test is True it will simulate the dispatcher configuration sending
        to the declared satellites in the configuration. Set to False if you intend to run
        real daemons that will receive their configuration!

        :param configuration_file: path + file name of the main configuration file
        :type configuration_file: str
        :param env_file: path + file name of the alignak environment file
        :type env_file: str
        :param verbose: load Alignak environment in verbose mode (defaults True)
        :type verbose: bool
        :return: None
        """
        self.broks = []

        # Our own satellites lists ...
        self.arbiters = {}
        self.schedulers = {}
        self.brokers = {}
        self.pollers = {}
        self.receivers = {}
        self.reactionners = {}

        # Our own schedulers lists ...
        # Indexed on the scheduler name
        self._schedulers = {}

        # The main arbiter and scheduler daemons
        self._arbiter = None
        self._scheduler_daemon = None
        self._scheduler = None
        self.conf_is_correct = False
        self.configuration_warnings = []
        self.configuration_errors = []

        # # This to allow using a reference configuration if needed,
        # # and to make some tests easier to set-up
        # print("Preparing default configuration...")
        # if os.path.exists('/tmp/etc/alignak'):
        #     shutil.rmtree('/tmp/etc/alignak')
        #
        # if os.path.exists('../etc'):
        #     shutil.copytree('../etc', '/tmp/etc/alignak')
        #     cfg_folder = '/tmp/etc/alignak'
        #     files = ['%s/alignak.ini' % cfg_folder,
        #              '%s/alignak.d/daemons.ini' % cfg_folder,
        #              '%s/alignak.d/modules.ini' % cfg_folder,
        #              '%s/alignak-logger.json' % cfg_folder]
        #     replacements = {
        #         '_dist=/usr/local/': '_dist=/tmp',
        #         'user=alignak': ';user=alignak',
        #         'group=alignak': ';group=alignak'
        #
        #     }
        #     self._files_update(files, replacements)
        # print("Prepared")

        # Initialize the Arbiter with no daemon configuration file
        assert configuration_file or env_file

        current_dir = os.getcwd()
        configuration_dir = current_dir
        print("Current directory: %s" % current_dir)
        if configuration_file:
            configuration_dir = os.path.dirname(configuration_file)
            print("Test configuration directory: %s, file: %s"
                  % (os.path.abspath(configuration_dir), configuration_file))
        else:
            configuration_dir = os.path.dirname(env_file)
            print("Test configuration directory: %s, file: %s"
                  % (os.path.abspath(configuration_dir), env_file))

        self.env_filename = None
        if env_file is not None:
            self.env_filename = env_file
        else:
            self.env_filename = os.path.join(configuration_dir, 'alignak.ini')
            print("env filename: %s" % os.path.join(configuration_dir, 'alignak.ini'))
            print("env filename: %s" % os.path.join(current_dir, './etc/alignak.ini'))
            if os.path.exists(os.path.join(configuration_dir, 'alignak.ini')):
                # alignak.ini in the same directory as the legacy configuration file
                self.env_filename = os.path.join(configuration_dir, 'alignak.ini')
            elif os.path.exists(os.path.join(current_dir, './etc/alignak.ini')):
                # alignak.ini in the test/etc directory
                self.env_filename = os.path.join(current_dir, './etc/alignak.ini')
            else:
                print("No Alignak configuration file found for the test: %s!" % self.env_filename)
                raise SystemExit("No Alignak configuration file found for the test!")

        self.env_filename = os.path.abspath(self.env_filename)
        print("Found Alignak environment file: %s" % self.env_filename)

        # Get Alignak environment
        args = {'<cfg_file>': self.env_filename, '--verbose': verbose}
        self.alignak_env = AlignakConfigParser(args)
        self.alignak_env.parse()

        arbiter_cfg = None
        for daemon_section, daemon_cfg in list(self.alignak_env.get_daemons().items()):
            if daemon_cfg['type'] == 'arbiter':
                arbiter_cfg = daemon_cfg

        arbiter_name = 'Default-Arbiter'
        if arbiter_cfg:
            arbiter_name = arbiter_cfg['name']

        # Using default values that are usually provided by the command line parameters
        args = {
            'alignak_name': 'alignak-test', 'daemon_name': arbiter_name,
            'env_file': self.env_filename
        }
        if configuration_file:
            args.update({
                'legacy_cfg_files': [configuration_file]
            })
        self._arbiter = Arbiter(**args)

        try:
            # Configure the logger
            # self._arbiter.debug = True
            self._arbiter.setup_alignak_logger()

            # Setup our modules manager
            self._arbiter.load_modules_manager()

            # Load and initialize the arbiter configuration
            self._arbiter.load_monitoring_config_file()

            # If this assertion does not match, then there is a bug in the arbiter :)
            self.assertTrue(self._arbiter.conf.conf_is_correct)
            self.conf_is_correct = True
            self.configuration_warnings = self._arbiter.conf.configuration_warnings
            self.configuration_errors = self._arbiter.conf.configuration_errors
        except SystemExit:
            self.configuration_warnings = self._arbiter.conf.configuration_warnings
            self.configuration_errors = self._arbiter.conf.configuration_errors
            self.show_configuration_logs()
            self.show_logs()
            raise

        # Prepare the configuration dispatching
        for arbiter_link in self._arbiter.conf.arbiters:
            if arbiter_link.get_name() == self._arbiter.arbiter_name:
                self._arbiter.link_to_myself = arbiter_link
            assert arbiter_link is not None, "There is no arbiter link in the configuration!"

        if not unit_test:
            return

        # Prepare the configuration dispatching
        self._arbiter.dispatcher = Dispatcher(self._arbiter.conf, self._arbiter.link_to_myself)
        self._arbiter.dispatcher.prepare_dispatch()

        # Create an Arbiter external commands manager in dispatcher mode
        self._arbiter.external_commands_manager = ExternalCommandManager(self._arbiter.conf,
                                                                         'dispatcher',
                                                                         self._arbiter,
                                                                         accept_unknown=True)

        print("All daemons WS: %s" % ["%s:%s" % (link.address, link.port) for link in self._arbiter.dispatcher.all_daemons_links])

        # Simulate the daemons HTTP interface (very simple simulation !)
        with requests_mock.mock() as mr:
            for link in self._arbiter.dispatcher.all_daemons_links:
                mr.get('http://%s:%s/ping' % (link.address, link.port), json='pong')
                mr.get('http://%s:%s/get_running_id' % (link.address, link.port),
                       json={"running_id": 123456.123456})
                mr.get('http://%s:%s/wait_new_conf' % (link.address, link.port), json=True)
                mr.post('http://%s:%s/push_configuration' % (link.address, link.port), json=True)
                mr.get('http://%s:%s/fill_initial_broks' % (link.address, link.port), json=[])
                mr.get('http://%s:%s/get_managed_configurations' % (link.address, link.port), json={})

            self._arbiter.dispatcher.check_reachable(test=True)
            self._arbiter.dispatcher.check_dispatch()
            print("-----\nConfiguration got dispatched.")

            # Check that all the daemons links got a configuration
            for sat_type in ('arbiters', 'schedulers', 'reactionners',
                             'brokers', 'receivers', 'pollers'):
                if verbose:
                    print("- for %s:" % (sat_type))
                for sat_link in getattr(self._arbiter.dispatcher, sat_type):
                    if verbose:
                        print(" - %s" % (sat_link))
                    pushed_configuration = getattr(sat_link, 'unit_test_pushed_configuration', None)
                    if pushed_configuration:
                        if verbose:
                            print("   pushed configuration, contains:")
                            for key in pushed_configuration:
                                print("   . %s = %s" % (key, pushed_configuration[key]))
                    # Update the test class satellites lists
                    getattr(self, sat_type).update({sat_link.name: pushed_configuration})
                if verbose:
                    print("- my %s: %s" % (sat_type, list(getattr(self, sat_type).keys())))

            self.eca = None
            # Initialize a Scheduler daemon
            for scheduler in self._arbiter.dispatcher.schedulers:
                print("-----\nGot a scheduler: %s (%s)" % (scheduler.name, scheduler))
                # Simulate the scheduler daemon start
                args = {
                    'env_file': self.env_filename, 'daemon_name': scheduler.name,
                }
                self._scheduler_daemon = Alignak(**args)
                self._scheduler_daemon.load_modules_manager()

                # Simulate the scheduler daemon receiving the configuration from its arbiter
                pushed_configuration = scheduler.unit_test_pushed_configuration
                self._scheduler_daemon.new_conf = pushed_configuration
                self._scheduler_daemon.setup_new_conf()
                assert self._scheduler_daemon.new_conf == {}
                self._schedulers[scheduler.name] = self._scheduler_daemon.sched

                # Store the last scheduler object to get used in some other functions!
                # this is the real scheduler, not the scheduler daemon!
                self._scheduler = self._scheduler_daemon.sched
                self._scheduler.my_daemon = self._scheduler_daemon
                print("Got a default scheduler: %s\n-----" % self._scheduler)

            # Initialize a Broker daemon
            for broker in self._arbiter.dispatcher.brokers:
                print("-----\nGot a broker: %s (%s)" % (broker.name, broker))
                # Simulate the broker daemon start
                args = {
                    'env_file': self.env_filename, 'daemon_name': broker.name,
                }
                self._broker_daemon = Broker(**args)
                self._broker_daemon.load_modules_manager()

                # Simulate the scheduler daemon receiving the configuration from its arbiter
                pushed_configuration = broker.unit_test_pushed_configuration
                self._broker_daemon.new_conf = pushed_configuration
                self._broker_daemon.setup_new_conf()
                assert self._broker_daemon.new_conf == {}
                print("Got a default broker daemon: %s\n-----" % self._broker_daemon)

            # Get my first broker link
            self._main_broker = None
            if self._scheduler.my_daemon.brokers:
                self._main_broker = [b for b in list(self._scheduler.my_daemon.brokers.values())][0]
            print("Main broker: %s" % self._main_broker)

            # Initialize a Receiver daemon
            self._receiver = None
            for receiver in self._arbiter.dispatcher.receivers:
                print("-----\nGot a receiver: %s (%s)" % (receiver.name, receiver))
                # Simulate the receiver daemon start
                args = {
                    'env_file': self.env_filename, 'daemon_name': receiver.name,
                }
                self._receiver_daemon = Receiver(**args)
                self._receiver_daemon.load_modules_manager()

                # Simulate the scheduler daemon receiving the configuration from its arbiter
                pushed_configuration = receiver.unit_test_pushed_configuration
                self._receiver_daemon.new_conf = pushed_configuration
                self._receiver_daemon.setup_new_conf()
                assert self._receiver_daemon.new_conf == {}
                self._receiver = receiver
                print("Got a default receiver: %s\n-----" % self._receiver)

                # for scheduler in self._receiver_daemon.schedulers.values():
                #     scheduler.my_daemon = self._receiver_daemon

        self.ecm_mode = 'applyer'

        # Now we create an external commands manager in receiver mode
        self.ecr = None
        if self._receiver:
            self.ecr = ExternalCommandManager(None, 'receiver', self._receiver_daemon,
                                              accept_unknown=True)
            self._receiver.external_commands_manager = self.ecr

        # and an external commands manager in dispatcher mode for the arbiter
        self.ecd = ExternalCommandManager(self._arbiter.conf, 'dispatcher', self._arbiter,
                                          accept_unknown=True)

        self._arbiter.modules_manager.stop_all()
        self._broker_daemon.modules_manager.stop_all()
        self._scheduler_daemon.modules_manager.stop_all()
        self._receiver_daemon.modules_manager.stop_all()

    def fake_check(self, ref, exit_status, output="OK"):
        """
        Simulate a check execution and result
        :param ref: host/service concerned by the check
        :param exit_status: check exit status code (0, 1, ...).
               If set to None, the check is simply scheduled but not "executed"
        :param output: check output (output + perf data)
        :return:
        """

        now = time.time()
        check = ref.schedule(self._scheduler.hosts,
                             self._scheduler.services,
                             self._scheduler.timeperiods,
                             self._scheduler.macromodulations,
                             self._scheduler.checkmodulations,
                             self._scheduler.checks,
                             force=True, force_time=None)
        # now the check is scheduled and we get it in the action queue
        self._scheduler.add(check)  # check is now in sched.checks[]

        # Allows to force check scheduling without setting its status nor output.
        # Useful for manual business rules rescheduling, for instance.
        if exit_status is None:
            return

        # fake execution
        check.check_time = now

        # and lie about when we will launch it because
        # if not, the schedule call for ref
        # will not really reschedule it because there
        # is a valid value in the future
        ref.next_chk = now - 0.5

        # Max plugin output is default to 8192
        check.get_outputs(output, 8192)
        check.exit_status = exit_status
        check.execution_time = 0.001
        check.status = 'waitconsume'

        # Put the check result in the waiting results for the scheduler ...
        self._scheduler.waiting_results.put(check)

    def scheduler_loop(self, count, items=None, scheduler=None):
        """
        Manage scheduler actions

        :param count: number of loop turns to run
        :type count: int
        :param items: list of list [[object, exist_status, output]]
        :type items: list
        :param scheduler: The scheduler
        :type scheduler: None | object
        :return: None
        """
        if scheduler is None:
            scheduler = self._scheduler

        if items is None:
            items = []

        macroresolver = MacroResolver()
        macroresolver.init(scheduler.my_daemon.sched.pushed_conf)

        for num in range(count):
            # print("Scheduler loop turn: %s" % num)
            for (item, exit_status, output) in items:
                # print("- item checks creation turn: %s" % item)
                if len(item.checks_in_progress) == 0:
                    # A first full scheduler loop turn to create the checks
                    # if they do not yet exist!
                    for i in scheduler.recurrent_works:
                        (name, fun, nb_ticks) = scheduler.recurrent_works[i]
                        if nb_ticks == 1:
                            try:
                                # print(" . %s ...running." % name)
                                fun()
                            except Exception as exp:
                                print("Exception: %s\n%s" % (exp, traceback.format_exc()))

                    # else:
                        #     print(" . %s ...ignoring, period: %d" % (name, nb_ticks))
                else:
                    print("Check is still in progress for %s" % (item.get_full_name()))
                self.assertGreater(len(item.checks_in_progress), 0)
                chk = scheduler.checks[item.checks_in_progress[0]]
                chk.set_type_active()
                chk.check_time = time.time()
                chk.wait_time = 0.0001
                chk.last_poll = chk.check_time
                chk.output = output
                chk.exit_status = exit_status
                scheduler.waiting_results.put(chk)

            # print("-----\n- results fetching turn:")
            for i in scheduler.recurrent_works:
                (name, fun, nb_ticks) = scheduler.recurrent_works[i]
                if nb_ticks == 1:
                    try:
                        # print(" . %s ...running." % name)
                        fun()
                    except Exception as exp:
                        print("Exception: %s\n%s" % (exp, traceback.format_exc()))
                # else:
                #     print(" . %s ...ignoring, period: %d" % (name, nb_ticks))
        self.assert_no_log_match("External command Brok could not be sent to any daemon!")

    def manage_freshness_check(self, count=1, mysched=None):
        """Run the scheduler loop for freshness_check

        :param count: number of scheduler loop turns
        :type count: int
        :param mysched: a specific scheduler to get used
        :type mysched: None | object
        :return: n/a
        """
        checks = []
        for num in range(count):
            for i in self._scheduler.recurrent_works:
                (name, fun, nb_ticks) = self._scheduler.recurrent_works[i]
                if nb_ticks == 1:
                    fun()
                if name == 'check_freshness':
                    checks = sorted(list(self._scheduler.checks.values()),
                                    key=lambda x: x.creation_time)
                    checks = [chk for chk in checks if chk.freshness_expiry_check]
        return len(checks)

    def manage_external_command(self, external_command, run=True):
        """Manage an external command.

        :return: result of external command resolution
        """
        res = None
        ext_cmd = ExternalCommand(external_command)
        if self.ecm_mode == 'applyer':
            res = None
            self._scheduler.run_external_commands([external_command])
            self.external_command_loop()
        if self.ecm_mode == 'dispatcher':
            res = self.ecd.resolve_command(ext_cmd)
            if res and run:
                self._arbiter.broks = []
                self._arbiter.add(ext_cmd)
                self._arbiter.push_external_commands_to_schedulers()
        if self.ecm_mode == 'receiver':
            res = self.ecr.resolve_command(ext_cmd)
            if res and run:
                self._receiver_daemon.broks = []
                self._receiver_daemon.add(ext_cmd)
                # self._receiver_daemon.push_external_commands_to_schedulers()
                # # Our scheduler
                # self._scheduler = self.schedulers['scheduler-master'].sched
                # Give broks to our broker
                for brok in self._receiver_daemon.broks:
                    print("Brok receiver: %s" % brok)
                    self._broker_daemon.external_broks.append(brok)
        return res

    def external_command_loop(self, count=1):
        """Execute the scheduler actions for external commands.

        The scheduler is not an ECM 'dispatcher' but an 'applyer' ... so this function is on
        the external command execution side of the problem.

        :return:
        """
        self.scheduler_loop(count=count)
        # macroresolver = MacroResolver()
        # macroresolver.init(self._scheduler.my_daemon.sched.pushed_conf)
        #
        # print("*** Scheduler external command loop turn:")
        # for i in self._scheduler.recurrent_works:
        #     (name, fun, nb_ticks) = self._scheduler.recurrent_works[i]
        #     if nb_ticks == 1:
        #         # print(" . %s ...running." % name)
        #         fun()
        #     else:
        #         print(" . %s ...ignoring, period: %d" % (name, nb_ticks))
        # self.assert_no_log_match("External command Brok could not be sent to any daemon!")

    def worker_loop(self, verbose=True):
        self._scheduler.delete_zombie_checks()
        self._scheduler.delete_zombie_actions()
        checks = self._scheduler.get_to_run_checks(True, False, worker_name='tester')
        actions = self._scheduler.get_to_run_checks(False, True, worker_name='tester')
        if verbose is True:
            self.show_actions()
        for a in actions:
            a.status = u'in_poller'
            a.check_time = time.time()
            a.exit_status = 0
            self._scheduler.put_results(a)
        if verbose is True:
            self.show_actions()

    def launch_internal_check(self, svc_br):
        """ Launch an internal check for the business rule service provided """
        # Launch an internal check
        now = time.time()
        self._scheduler.add(svc_br.launch_check(now - 1,
                                                self._scheduler.hosts,
                                                self._scheduler.services,
                                                self._scheduler.timeperiods,
                                                self._scheduler.macromodulations,
                                                self._scheduler.checkmodulations,
                                                self._scheduler.checks))
        c = svc_br.actions[0]
        self.assertEqual(True, c.internal)
        self.assertTrue(c.is_launchable(now))

        # ask the scheduler to launch this check
        # and ask 2 loops: one to launch the check
        # and another to get the result
        self.scheduler_loop(2, [])

        # We should not have the check anymore
        self.assertEqual(0, len(svc_br.actions))

    def show_logs(self):
        """Show logs. Get logs collected by the unit tests collector handler and print them"""
        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for handler in logger_.handlers:
            if isinstance(handler, CollectorHandler):
                print("--- logs <<<----------------------------------")
                for log in handler.collector:
                    self.safe_print(log)
                print("--- logs >>>----------------------------------")
                break
        else:
            assert False, "Alignak test Logger is not initialized correctly!"

    def show_actions(self):
        """"Show the inner actions"""
        macroresolver = MacroResolver()
        macroresolver.init(self._scheduler_daemon.sched.pushed_conf)

        print("--- Scheduler: %s" % self._scheduler.my_daemon.name)
        print("--- actions >>>")
        actions = sorted(list(self._scheduler.actions.values()), key=lambda x: (x.t_to_go, x.creation_time))
        for action in actions:
            print("Time to launch action: %s, creation: %s, now: %s" % (action.t_to_go, action.creation_time, time.time()))
            if action.is_a == 'notification':
                item = self._scheduler.find_item_by_id(action.ref)
                if item.my_type == "host":
                    ref = "host: %s" % item.get_name()
                else:
                    hst = self._scheduler.find_item_by_id(item.host)
                    ref = "svc: %s/%s" % (hst.get_name(), item.get_name())
                print("NOTIFICATION %s (%s - %s) [%s], created: %s for '%s': %s"
                      % (action.type, action.uuid, action.status, ref,
                         time.asctime(time.localtime(action.t_to_go)),
                         action.contact_name, action.command))
            elif action.is_a == 'eventhandler':
                print("EVENTHANDLER:", action)
            else:
                print("ACTION:", action)
        print("<<< actions ---")

    def show_checks(self):
        """
        Show checks from the scheduler
        :return:
        """
        print("--- Scheduler: %s" % self._scheduler.my_daemon.name)
        print("--- checks >>>")
        checks = sorted(list(self._scheduler.checks.values()), key=lambda x: x.creation_time)
        for check in checks:
            print("- %s" % check)
        print("<<< checks ---")

    def show_and_clear_actions(self):
        self.show_actions()
        self.clear_actions()

    def count_logs(self):
        """Count the logs collected by the unit tests collector handler and print them"""
        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for handler in logger_.handlers:
            if isinstance(handler, CollectorHandler):
                return len(handler.collector)
        else:
            assert False, "Alignak test Logger is not initialized correctly!"

    def count_actions(self):
        """
        Count the actions in the scheduler's actions.

        @verified
        :return:
        """
        return len(list(self._scheduler.actions.values()))

    def clear_logs(self):
        """
        Remove all the logs stored in the logs collector

        @verified
        :return:
        """
        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for handler in logger_.handlers:
            if isinstance(handler, CollectorHandler):
                handler.collector = []
                break
        else:
            assert False, "Alignak test Logger is not initialized correctly!"

    def clear_actions(self):
        """
        Clear the actions in the scheduler's actions.

        :return:
        """
        self._scheduler.actions = {}

    def clear_checks(self):
        """
        Clear the checks in the scheduler's checks.

        :return:
        """
        self._scheduler.checks = {}

    def check_monitoring_logs(self, expected_logs, dump=True):
        """
        Get the monitoring_log broks and check that they match with the expected_logs provided

        :param expected_logs: expected monitoring logs
        :param dump: True to print out the monitoring logs
        :return:
        """
        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        if dump:
            print("Monitoring logs: ")
        # Sort broks by ascending uuid
        index = 0
        for brok in sorted(self._main_broker.broks, key=lambda x: x.creation_time):
            if brok.type not in ['monitoring_log']:
                continue

            data = unserialize(brok.data)
            monitoring_logs.append((data['level'], data['message']))
            if dump:
                print("- %s" % brok)
                # print("- %d: %s - %s: %s" % (index, brok.creation_time,
                #                              data['level'], data['message']))
                index+=1

        for log_level, log_message in expected_logs:
            assert (log_level, log_message) in monitoring_logs, "Not found :%s" % log_message

        assert len(expected_logs) == len(monitoring_logs), "Length do not match: %d" \
                                                           % len(monitoring_logs)

    def assert_actions_count(self, number):
        """
        Check the number of actions

        :param number: number of actions we must have
        :type number: int
        :return: None
        """
        actions = []
        # I do this because sort take too times
        if number != len(self._scheduler.actions):
            actions = sorted(list(self._scheduler.actions.values()), key=lambda x: x.creation_time)
        self.assertEqual(number, len(self._scheduler.actions),
                         "Not found expected number of actions:\nactions_logs=[[[\n%s\n]]]" %
                         ('\n'.join('\t%s = creation: %s, is_a: %s, type: %s, status: %s, '
                                    'planned: %s, command: %s' %
                                    (idx, b.creation_time, b.is_a, b.type,
                                     b.status, b.t_to_go, b.command)
                                    for idx, b in enumerate(sorted(self._scheduler.actions.values(),
                                                                   key=lambda x: (x.creation_time,
                                                                                  x.t_to_go))))))

    def assert_actions_match(self, index, pattern, field):
        """
        Check if pattern verified in field(property) name of the action with index in action list

        @verified

        :param index: index in the actions list. If index is -1, all the actions in the list are
        searched for a matching pattern
        :type index: int
        :param pattern: pattern to verify is in the action
        :type pattern: str
        :param field: name of the field (property) of the action
        :type field: str
        :return: None
        """
        regex = re.compile(pattern)
        actions = sorted(self._scheduler.actions.values(), key=lambda x: (x.t_to_go, x.creation_time))
        if index != -1:
            myaction = actions[index]
            self.assertTrue(regex.search(getattr(myaction, field)),
                            "Not found a matching pattern in actions:\n"
                            "index=%s field=%s pattern=%r\n"
                            "action_line=creation: %s, is_a: %s, type: %s, "
                            "status: %s, planned: %s, command: %s" % (
                                index, field, pattern, myaction.creation_time, myaction.is_a,
                                myaction.type, myaction.status, myaction.t_to_go, myaction.command))
            return

        for myaction in actions:
            if regex.search(getattr(myaction, field)):
                return

        self.assertTrue(False,
                        "Not found a matching pattern in actions:\nfield=%s pattern=%r\n" %
                        (field, pattern))

    def assert_log_count(self, number):
        """
        Check the number of log

        :param number: number of logs we must have
        :type number: int
        :return: None
        """
        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for handler in logger_.handlers:
            if isinstance(handler, CollectorHandler):
                self.assertEqual(number, len(handler.collector),
                                 "Not found expected number of logs: %s vs %s"
                                 % (number, len(handler.collector)))
                break
        else:
            assert False, "Alignak test Logger is not initialized correctly!"

    def assert_log_match(self, pattern, index=None):
        """
        Search if the log with the index number has the pattern in the Arbiter logs.

        If index is None, then all the collected logs are searched for the pattern

        Logs numbering starts from 0 (the oldest stored log line)

        This function assert on the search result. As of it, if no log is found with th search
        criteria an assertion is raised and the test stops on error.

        :param pattern: string to search in log
        :type pattern: str
        :param index: index number
        :type index: int
        :return: None
        """
        self.assertIsNotNone(pattern, "Searched pattern can not be None!")

        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for handler in logger_.handlers:
            if not isinstance(handler, CollectorHandler):
                continue
            regex = re.compile(pattern)

            log_num = 0
            found = False
            for log in handler.collector:
                if index is None:
                    if regex.search(log):
                        found = True
                        break
                elif index == log_num:
                    if regex.search(log):
                        found = True
                        break
                log_num += 1

            self.assertTrue(found,
                            "Not found a matching log line in logs:\nindex=%s pattern=%r\n"
                            "logs=[[[\n%s\n]]]"
                            % (index, pattern, '\n'.join('\t%s=%s' % (idx, b.strip())
                                                         for idx, b in
                                                         enumerate(handler.collector))))
            break
        else:
            assert False, "Alignak test Logger is not initialized correctly!"

    def assert_checks_count(self, number):
        """
        Check the number of actions

        @verified

        :param number: number of actions we must have
        :type number: int
        :return: None
        """
        checks = sorted(list(self._scheduler.checks.values()), key=lambda x: x.creation_time)
        self.assertEqual(number, len(checks),
                         "Not found expected number of checks:\nchecks_logs=[[[\n%s\n]]]" %
                         ('\n'.join('\t%s = creation: %s, is_a: %s, type: %s, status: %s, planned: %s, '
                                    'command: %s' %
                                    (idx, b.creation_time, b.is_a, b.type, b.status, b.t_to_go, b.command)
                                    for idx, b in enumerate(checks))))

    def assert_checks_match(self, index, pattern, field):
        """
        Check if pattern verified in field(property) name of the check with index in check list

        @verified

        :param index: index number of checks list
        :type index: int
        :param pattern: pattern to verify is in the check
        :type pattern: str
        :param field: name of the field (property) of the check
        :type field: str
        :return: None
        """
        regex = re.compile(pattern)
        checks = sorted(list(self._scheduler.checks.values()), key=lambda x: x.creation_time)
        mycheck = checks[index]
        self.assertTrue(regex.search(getattr(mycheck, field)),
                        "Not found a matching pattern in checks:\nindex=%s field=%s pattern=%r\n"
                        "check_line=creation: %s, is_a: %s, type: %s, status: %s, planned: %s, "
                        "command: %s" % (
                            index, field, pattern, mycheck.creation_time, mycheck.is_a,
                            mycheck.type, mycheck.status, mycheck.t_to_go, mycheck.command))

    def _any_check_match(self, pattern, field, assert_not):
        """
        Search if any check matches the requested pattern

        @verified
        :param pattern:
        :param field to search with pattern:
        :param assert_not:
        :return:
        """
        regex = re.compile(pattern)
        checks = sorted(list(self._scheduler.checks.values()), key=lambda x: x.creation_time)
        for check in checks:
            if re.search(regex, getattr(check, field)):
                self.assertTrue(not assert_not,
                                "Found check:\nfield=%s pattern=%r\n"
                                "check_line=creation: %s, is_a: %s, type: %s, status: %s, "
                                "planned: %s, command: %s" % (
                                    field, pattern, check.creation_time, check.is_a,
                                    check.type, check.status, check.t_to_go, check.command)
                                )
                return
        self.assertTrue(assert_not, "No matching check found:\n"
                                    "pattern = %r\n" "checks = %r" % (pattern, checks))

    def assert_any_check_match(self, pattern, field):
        """
        Assert if any check matches the pattern

        @verified
        :param pattern:
        :param field to search with pattern:
        :return:
        """
        self._any_check_match(pattern, field, assert_not=False)

    def assert_no_check_match(self, pattern, field):
        """
        Assert if no check matches the pattern

        @verified
        :param pattern:
        :param field to search with pattern:
        :return:
        """
        self._any_check_match(pattern, field, assert_not=True)

    def _any_log_match(self, pattern, assert_not):
        """
        Search if any log in the Arbiter logs matches the requested pattern
        If 'scheduler' is True, then uses the scheduler's broks list.

        @verified
        :param pattern:
        :param assert_not:
        :return:
        """
        self.assertIsNotNone(pattern, "Searched pattern can not be None!")

        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for handler in logger_.handlers:
            if not isinstance(handler, CollectorHandler):
                continue

            # print("-----\nParsing collector handler log events...")
            # print("Searching for: %s (%s)" % (pattern, type(pattern)))
            try:
                regex = re.compile(pattern, re.ASCII)
            except AttributeError:
                regex = re.compile(pattern)

            for log in handler.collector:
                if re.search(regex, log):
                    # print("# found: %s" % (log))
                    self.assertTrue(
                        not assert_not,
                        "Found matching log line, pattern: %r\nlog: %r" % (pattern, log)
                    )
                    break
            else:
                # # Dump all known log events for analysis
                # for log in handler.collector:
                #     print(". %s (%s)" % (repr(log), type(log)))
                self.assertTrue(assert_not,
                                "No matching log line found, pattern: %r\n" % pattern)
            break
        else:
            assert False, "Alignak test Logger is not initialized correctly!"

    def assert_any_log_match(self, pattern):
        """Assert if any of the collected log matches the pattern

        :param pattern:
        :return:
        """
        self._any_log_match(pattern, assert_not=False)

    def assert_no_log_match(self, pattern):
        """Assert if no collected log matches the pattern

        :param pattern:
        :return:
        """
        self._any_log_match(pattern, assert_not=True)

    def _any_brok_match(self, pattern, level, assert_not):
        """
        Search if any brok message in the Scheduler broks matches the requested pattern and
        requested level

        @verified
        :param pattern:
        :param assert_not:
        :return:
        """
        regex = re.compile(pattern)

        my_broker = [b for b in list(self._scheduler.my_daemon.brokers.values())][0]

        monitoring_logs = []
        print("Broker broks: %s" % my_broker.broks)
        for brok in my_broker.broks:
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))
                if re.search(regex, data['message']) and (level is None or data['level'] == level):
                    self.assertTrue(not assert_not, "Found matching brok:\n"
                                    "pattern = %r\nbrok message = %r" % (pattern, data['message']))
                    return

        self.assertTrue(assert_not, "No matching brok found:\n"
                                    "pattern = %r\n" "brok message = %r" % (pattern,
                                                                            monitoring_logs))

    def assert_any_brok_match(self, pattern, level=None):
        """
        Search if any brok message in the Scheduler broks matches the requested pattern and
        requested level

        @verified
        :param pattern:
        :param scheduler:
        :return:
        """
        self._any_brok_match(pattern, level, assert_not=False)

    def assert_no_brok_match(self, pattern, level=None):
        """
        Search if no brok message in the Scheduler broks matches the requested pattern and
        requested level

        @verified
        :param pattern:
        :param scheduler:
        :return:
        """
        self._any_brok_match(pattern, level, assert_not=True)

    def get_log_match(self, pattern):
        """Get the collected logs matching the provided pattern"""
        self.assertIsNotNone(pattern, "Searched pattern can not be None!")

        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for handler in logger_.handlers:
            if isinstance(handler, CollectorHandler):
                regex = re.compile(pattern)
                res = []
                for log in handler.collector:
                    if re.search(regex, log):
                        res.append(log)
                return res
        else:
            assert False, "Alignak test Logger is not initialized correctly!"

    def show_configuration_logs(self):
        """
        Prints the configuration logs

        @verified
        :return:
        """
        print("Configuration warnings:")
        for msg in self.configuration_warnings:
            print(" - %s" % msg)
        print("Configuration errors:")
        for msg in self.configuration_errors:
            print(" - %s" % msg)

    def _any_cfg_log_match(self, pattern, assert_not):
        """
        Search a pattern in configuration log (warning and error)

        @verified
        :param pattern:
        :return:
        """
        regex = re.compile(pattern)

        cfg_logs = self.configuration_warnings + self.configuration_errors

        for log in cfg_logs:
            if re.search(regex, log):
                self.assertTrue(not assert_not,
                                "Found matching log line:\n"
                                "pattern = %r\nlog = %r" % (pattern, log))
                return

        self.assertTrue(assert_not, "No matching log line found:\n"
                                    "pattern = %r\n" "logs = %r" % (pattern, cfg_logs))

    def assert_any_cfg_log_match(self, pattern):
        """
        Assert if any configuration log matches the pattern

        @verified
        :param pattern:
        :return:
        """
        self._any_cfg_log_match(pattern, assert_not=False)

    def assert_no_cfg_log_match(self, pattern):
        """
        Assert if no configuration log matches the pattern

        @verified
        :param pattern:
        :return:
        """
        self._any_cfg_log_match(pattern, assert_not=True)

    def guess_sys_stdout_encoding(self):
        ''' Return the best guessed encoding to be used for printing on sys.stdout. '''
        return (
               getattr(sys.stdout, 'encoding', None)
            or getattr(sys.__stdout__, 'encoding', None)
            or locale.getpreferredencoding()
            or sys.getdefaultencoding()
            or 'ascii'
        )

    def safe_print(self, *args, **kw):
        """" "print" args to sys.stdout,
        If some of the args aren't unicode then convert them first to unicode,
            using keyword argument 'in_encoding' if provided (else default to UTF8)
            and replacing bad encoded bytes.
        Write to stdout using 'out_encoding' if provided else best guessed encoding,
            doing xmlcharrefreplace on errors.
        """
        in_bytes_encoding = kw.pop('in_encoding', 'UTF-8')
        out_encoding = kw.pop('out_encoding', self.guess_sys_stdout_encoding())
        if kw:
            raise ValueError('unhandled named/keyword argument(s): %r' % kw)
        #
        make_in_data_gen = lambda: ( a if isinstance(a, string_types) else str(a) for a in args )

        possible_codings = ( out_encoding, )
        if out_encoding != 'ascii':
            possible_codings += ( 'ascii', )

        for coding in possible_codings:
            data = ' '.join(make_in_data_gen()).encode(coding, 'xmlcharrefreplace')
            try:
                sys.stdout.write(data)
                break
            except UnicodeError as err:
                # there might still have some problem with the underlying sys.stdout.
                # it might be a StringIO whose content could be decoded/encoded in this same process
                # and have encode/decode errors because we could have guessed a bad encoding with it.
                # in such case fallback on 'ascii'
                if coding == 'ascii':
                    raise
                sys.stderr.write('Error on write to sys.stdout with %s encoding: err=%s\nTrying with ascii' % (
                    coding, err))
        sys.stdout.write(b'\n')
