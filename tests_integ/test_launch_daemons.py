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
import configparser

import subprocess
import threading
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


class TestLaunchDaemons(AlignakTest):
    def setUp(self):
        super(TestLaunchDaemons, self).setUp()

        self.cfg_folder = '/tmp/alignak'
        self._prepare_configuration(copy=True, cfg_folder=self.cfg_folder)

        files = ['%s/etc/alignak.ini' % self.cfg_folder,
                 '%s/etc/alignak.d/daemons.ini' % self.cfg_folder,
                 '%s/etc/alignak.d/modules.ini' % self.cfg_folder]
        try:
            cfg = configparser.ConfigParser()
            cfg.read(files)

            cfg.set('alignak-configuration', 'launch_missing_daemons', '1')
            cfg.set('daemon.arbiter-master', 'alignak_launched', '1')
            cfg.set('daemon.scheduler-master', 'alignak_launched', '1')
            cfg.set('daemon.poller-master', 'alignak_launched', '1')
            cfg.set('daemon.reactionner-master', 'alignak_launched', '1')
            cfg.set('daemon.receiver-master', 'alignak_launched', '1')
            cfg.set('daemon.broker-master', 'alignak_launched', '1')

            with open('%s/etc/alignak.ini' % self.cfg_folder, "w") as modified:
                cfg.write(modified)
        except Exception as exp:
            print("* parsing error in config file: %s" % exp)
            assert False

    def tearDown(self):
        # Restore the default test logger configuration
        if 'ALIGNAK_LOGGER_CONFIGURATION' in os.environ:
            del os.environ['ALIGNAK_LOGGER_CONFIGURATION']

        print("Test terminated!")

    def test_arbiter_missing_parameters(self):
        """ Running the Alignak Arbiter with missing command line parameters

        :return:
        """
        print("Launching arbiter with missing parameters...")
        args = ["../alignak/bin/alignak_arbiter.py"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        # Waiting for arbiter to parse the configuration
        sleep(3)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %d" % ret)
        assert ret is not None, "Arbiter is still running!"
        stderr = arbiter.stderr.read()
        print(stderr)
        assert b"usage: alignak_arbiter.py" in stderr
        # Arbiter process must exit with a return code == 2
        assert ret == 2

    def test_arbiter_no_environment(self):
        """ Running the Alignak Arbiter without environment file

        :return:
        """
        print("Launching arbiter without environment file...")
        args = ["../alignak/bin/alignak_arbiter.py"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        # Waiting for arbiter to parse the configuration
        sleep(3)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %d" % ret)
        assert ret is not None, "Arbiter is still running!"
        stdout = arbiter.stdout.read()
        print(stdout)
        stderr = arbiter.stderr.read()
        print(stderr)
        assert b"usage: alignak_arbiter.py" in stderr
        # Arbiter process must exit with a return code == 2
        assert ret == 2

    # @pytest.mark.skip("To be re-activated with spare mode")
    def test_arbiter_class_no_environment(self):
        """ Instantiate the Alignak Arbiter class without environment file

        :return:
        """
        from alignak.daemons.arbiterdaemon import Arbiter
        print("Instantiate arbiter without environment file...")
        # Using values that are usually provided by the command line parameters
        args = {
            'env_file': '',
            'alignak_name': 'alignak-test',
            'daemon_name': 'arbiter-master',
            'log_filename': '/tmp/arbiter.log',
            'legacy_cfg_files': ['../etc/alignak.cfg']
        }
        # Exception because the logger configuration file does not exist
        self.arbiter = Arbiter(**args)

        print("Arbiter: %s" % self.arbiter)
        assert self.arbiter.env_filename == ''
        assert self.arbiter.legacy_cfg_files == [os.path.abspath('../etc/alignak.cfg')]

        # Configure the logger
        self.arbiter.log_level = 'ERROR'
        self.arbiter.setup_alignak_logger()

        # Setup our modules manager
        # self.arbiter.load_modules_manager()

        # Load and initialize the arbiter configuration
        # This to check that the configuration is correct!
        self.arbiter.load_monitoring_config_file()

    def test_arbiter_class_env_default(self):
        """ Instantiate the Alignak Arbiter class without legacy cfg files
        :return:
        """
        # Unset legacy configuration files
        files = ['%s/etc/alignak.ini' % self.cfg_folder]
        try:
            cfg = configparser.ConfigParser()
            cfg.read(files)

            # Nagios legacy files - not configured
            cfg.set('alignak-configuration', 'cfg', '')

            with open('%s/etc/alignak.ini' % self.cfg_folder, "w") as modified:
                cfg.write(modified)
        except Exception as exp:
            print("* parsing error in config file: %s" % exp)
            assert False

        from alignak.daemons.arbiterdaemon import Arbiter
        print("Instantiate arbiter with default environment file...")
        # Using values that are usually provided by the command line parameters
        args = {
            'env_file': "/tmp/alignak/etc/alignak.ini",
            'daemon_name': 'arbiter-master'
        }
        self.arbiter = Arbiter(**args)

        print("Arbiter: %s" % (self.arbiter))
        print("Arbiter: %s" % (self.arbiter.__dict__))
        assert self.arbiter.env_filename == '/tmp/alignak/etc/alignak.ini'
        assert self.arbiter.legacy_cfg_files == []
        assert len(self.arbiter.legacy_cfg_files) == 0

        # Configure the logger
        self.arbiter.log_level = 'INFO'
        self.arbiter.setup_alignak_logger()

        # Setup our modules manager
        # self.arbiter.load_modules_manager()

        # Load and initialize the arbiter configuration
        # This to check that the configuration is correct!
        self.arbiter.load_monitoring_config_file()
        # No legacy files found
        assert len(self.arbiter.legacy_cfg_files) == 0

    def test_arbiter_unexisting_environment(self):
        """ Running the Alignak Arbiter with a not existing environment file

        :return:
        """
        print("Launching arbiter with a not existing environment file...")
        args = ["../alignak/bin/alignak_arbiter.py", "-e", "/tmp/etc/unexisting.ini"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        # Waiting for arbiter to parse the configuration
        sleep(3)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %d" % ret)
        assert ret is not None, "Arbiter is still running!"
        stdout = arbiter.stdout.read()
        print(stdout)
        assert b"Daemon 'arbiter-master' did not correctly read " \
               b"Alignak environment file: /tmp/etc/unexisting.ini" in stdout
        # Arbiter process must exit with a return code == 1
        assert ret == 99

    def test_arbiter_no_monitoring_configuration(self):
        """ Running the Alignak Arbiter with no monitoring configuration defined -
        no legacy cfg files

        :return:
        """
        print("Launching arbiter with no monitoring configuration...")

        # Unset legacy configuration files
        files = ['%s/etc/alignak.ini' % self.cfg_folder]
        try:
            cfg = configparser.ConfigParser()
            cfg.read(files)

            # Nagios legacy files - not configured
            cfg.set('alignak-configuration', 'cfg', '')

            with open('%s/etc/alignak.ini' % self.cfg_folder, "w") as modified:
                cfg.write(modified)
        except Exception as exp:
            print("* parsing error in config file: %s" % exp)
            assert False

        args = ["../alignak/bin/alignak_arbiter.py", "-e", '%s/etc/alignak.ini' % self.cfg_folder]
        ret = self._run_command_with_timeout(args, 30)

        errors = 0
        ok = False
        with open('/tmp/alignak/log/arbiter-master.log') as f:
            for line in f:
                if 'total number of hosts in all realms: 0' in line:
                    ok = True
        assert errors == 0
        assert ok

    def test_arbiter_unexisting_monitoring_configuration(self):
        """ Running the Alignak Arbiter with a not existing monitoring configuration file

        :return:
        """
        print("Launching arbiter with no monitoring configuration...")

        files = ['%s/etc/alignak.ini' % self.cfg_folder]
        try:
            cfg = configparser.ConfigParser()
            cfg.read(files)

            # Nagios legacy files
            cfg.set('alignak-configuration', 'cfg', '%(etcdir)s/alignak-missing.cfg')

            with open('%s/etc/alignak.ini' % self.cfg_folder, "w") as modified:
                cfg.write(modified)
        except Exception as exp:
            print("* parsing error in config file: %s" % exp)
            assert False

        args = ["../alignak/bin/alignak_arbiter.py", "-e", '%s/etc/alignak.ini' % self.cfg_folder]
        ret = self._run_command_with_timeout(args, 20)

        errors = 0
        ok = False
        with open('/tmp/alignak/log/arbiter-master.log') as f:
            for line in f:
                if 'WARNING:' in line and "cannot open main file '/tmp/alignak/etc/alignak-missing.cfg' for reading" in line:
                    ok = True
                if 'ERROR:' in line or 'CRITICAL:' in line:
                    print("*** %s" % line.rstrip())
                    errors = errors + 1
        # Arbiter process must exit with a return code == 0 and no errors
        assert errors == 2
        # Arbiter process must exit with a return code == 1
        assert ret == 1
        assert ok

    def test_arbiter_bad_configuration(self):
        """ Running the Alignak Arbiter with bad monitoring configuration (unknown sub directory)

        :return:
        """
        print("Launching arbiter with a bad monitoring configuration...")

        files = ['%s/etc/alignak.ini' % self.cfg_folder]
        try:
            cfg = configparser.ConfigParser()
            cfg.read(files)

            # Nagios legacy files
            cfg.set('alignak-configuration', 'cfg', '%(etcdir)s/alignak.cfg')

            with open('%s/etc/alignak.ini' % self.cfg_folder, "w") as modified:
                cfg.write(modified)
        except Exception as exp:
            print("* parsing error in config file: %s" % exp)
            assert False

        # Update configuration with a bad file name
        files = ['%s/etc/alignak.cfg' % self.cfg_folder]
        replacements = {
            'cfg_dir=arbiter/templates': 'cfg_dir=unexisting/objects/realms'
        }
        self._files_update(files, replacements)

        args = ["../alignak/bin/alignak_arbiter.py", "-e", '%s/etc/alignak.ini' % self.cfg_folder]
        ret = self._run_command_with_timeout(args, 20)

        errors = 0
        ok = False
        with open('/tmp/alignak/log/arbiter-master.log') as f:
            for line in f:
                if 'ERROR:' in line and "*** One or more problems were encountered while " \
                                        "processing the configuration (first check)..." in line:
                    ok = True
                if 'ERROR:' in line or 'CRITICAL:' in line:
                    print("*** %s" % line.rstrip())
                    errors = errors + 1
        # Arbiter process must exit with a return code == 0 and no errors
        assert errors == 2
        # Arbiter process must exit with a return code == 1
        assert ret == 1
        assert ok

    def test_arbiter_i_am_not_configured(self):
        """ Running the Alignak Arbiter with missing arbiter configuration

        :return:
        """
        print("Launching arbiter with a missing arbiter configuration...")

        # Current working directory for the default log file!
        if os.path.exists('%s/my-arbiter-name.log' % os.getcwd()):
            os.remove('%s/my-arbiter-name.log' % os.getcwd())

        args = ["../alignak/bin/alignak_arbiter.py",
                "-e", '%s/etc/alignak.ini' % self.cfg_folder,
                "-n", "my-arbiter-name"]
        ret = self._run_command_with_timeout(args, 20)

        errors = 0
        ok = False
        # Note the log filename!
        with open('%s/my-arbiter-name.log' % os.getcwd()) as f:
            for line in f:
                if "I cannot find my own configuration (my-arbiter-name)" in line:
                    ok = True
                if 'ERROR:' in line or 'CRITICAL:' in line:
                    print("*** %s" % line.rstrip())
                    errors = errors + 1
        # Arbiter process must exit with a return code == 0 and no errors
        assert errors == 2
        # Arbiter process must exit with a return code == 1
        assert ret == 1
        assert ok

    def test_arbiter_verify(self):
        """ Running the Alignak Arbiter in verify mode only with the default shipped configuration

        :return:
        """
        # Set a specific logger configuration - do not use the default test configuration
        os.environ['ALIGNAK_LOGGER_CONFIGURATION'] = \
            os.path.abspath('./etc/warning_alignak-logger.json')
        print("Logger configuration file is: %s" % os.environ['ALIGNAK_LOGGER_CONFIGURATION'])

        print("Launching arbiter in verification mode...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-e", '%s/etc/alignak.ini' % self.cfg_folder,
                "-V"]
        ret = self._run_command_with_timeout(args, 20)

        errors = 0
        specific_log = False
        info_log = False
        with open('/tmp/alignak/log/arbiter-master.log') as f:
            for line in f:
                if 'INFO:' in line:
                    info_log = True
                    if 'Arbiter is in configuration check mode' in line:
                        specific_log = True
                if 'ERROR:' in line or 'CRITICAL:' in line:
                    print("*** %s" % line.rstrip())
                    errors = errors + 1
        # Arbiter process must exit with a return code == 0 and no errors
        # Arbiter changed the log level to INFO because of the verify mode
        assert specific_log is True
        assert info_log is True
        assert errors == 0
        assert ret == 0

    def test_arbiter_parameters_pid(self):
        """ Run the Alignak Arbiter with some parameters - set a pid file

        :return:
        """
        # All the default configuration files are in /tmp/etc

        print("Launching arbiter with forced PID file...")
        if os.path.exists('/tmp/arbiter.pid'):
            os.remove('/tmp/arbiter.pid')

        args = ["../alignak/bin/alignak_arbiter.py", "-e", '%s/etc/alignak.ini' % self.cfg_folder, "-V",
                "--pid_file", "/tmp/arbiter.pid"]
        ret = self._run_command_with_timeout(args, 20)

        # The arbiter unlinks the pid file - I cannot assert it exists!
        # assert os.path.exists('/tmp/arbiter.pid')

        errors = 0
        # ok = False
        with open('/tmp/alignak/log/arbiter-master.log') as f:
            for line in f:
                # if 'Unlinking /tmp/arbiter.pid' in line:
                #     ok = True
                if 'ERROR:' in line or 'CRITICAL:' in line:
                    print("*** %s" % line.rstrip())
                    errors = errors + 1
        # Arbiter process must exit with a return code == 0 and no errors
        assert errors == 0
        assert ret == 0
        # assert ok

    def test_arbiter_parameters_log(self):
        """ Run the Alignak Arbiter with some parameters - log file name
        Log file name and log level may be specified on the command line
        :return:
        """
        # All the default configuration files are in /tmp/etc
        print("Launching arbiter with forced log file...")
        if os.path.exists('/tmp/arbiter.log'):
            os.remove('/tmp/arbiter.log')

        args = ["../alignak/bin/alignak_arbiter.py", "-e", '%s/etc/alignak.ini' % self.cfg_folder,
                "-V", "-vv",
                "--log_level", "INFO", "--log_file", "/tmp/arbiter.log"]
        ret = self._run_command_with_timeout(args, 20)

        # Log file created because of the -V option
        assert os.path.exists("/tmp/arbiter.log")

        errors = 0
        with open('/tmp/arbiter.log') as f:
            for line in f:
                if 'ERROR:' in line or 'CRITICAL:' in line:
                    print("*** %s" % line.rstrip())
                    errors = errors + 1
        # Arbiter process must exit with a return code == 0 and no errors
        assert errors == 0
        assert ret == 0

    @pytest.mark.skip("To be re-activated with spare mode")
    def test_arbiter_spare_missing_configuration(self):
        """ Run the Alignak Arbiter in spare mode - missing spare configuration

        :return:
        """
        print("Launching arbiter in spare mode...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-a", cfg_folder + "/alignak.cfg",
                "-c", cfg_folder + "/daemons/arbiterd.ini",
                "-n", "arbiter-spare"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        sleep(5)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %s" % ret)
        assert ret is not None, "Arbiter is still running!"
        # Arbiter process must exit with a return code == 1
        assert ret == 1

    @pytest.mark.skip("To be re-activated with spare mode")
    def test_arbiter_spare(self):
        """ Run the Alignak Arbiter in spare mode - missing spare configuration

        :return:
        """
        print("Launching arbiter in spare mode...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-a", cfg_folder + "/alignak.cfg",
                "-c", cfg_folder + "/daemons/arbiterd.ini",
                "-n", "arbiter-spare"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        ret = arbiter.poll()
        # Arbiter must still be running ... it is still trying to dispatch the configuration!
        assert ret is None, "Arbiter exited!"

        sleep(5)

        # Arbiter never stops trying to send its configuration! We must kill it...

        print("Asking arbiter to end...")
        os.kill(arbiter.pid, signal.SIGTERM)

        ret = arbiter.poll()
        print("*** Arbiter exited on kill, no return code!")
        assert ret is None, "Arbiter is still running!"
        # No ERRORS because the daemons are not alive !
        ok = 0
        for line in iter(arbiter.stdout.readline, b''):
            print(">>> %s" % line.rstrip())
            if b'INFO:' in line:
                # I must find this line
                if b'[alignak.daemons.arbiterdaemon] I found myself in the configuration: arbiter-spare' in line:
                    ok += 1
                # and this one also
                if b'[alignak.daemons.arbiterdaemon] I am a spare Arbiter: arbiter-spare' in line:
                    ok += 1
                if b'I am not the master arbiter, I stop parsing the configuration' in line:
                    ok += 1
                if b'Waiting for master...' in line:
                    ok += 1
                if b'Waiting for master death' in line:
                    ok += 1
                assert b'CRITICAL:' not in line
        for line in iter(arbiter.stderr.readline, b''):
            print("*** %s" % line.rstrip())
            if sys.version_info > (2, 7):
                assert False, "stderr output!"
        assert ok == 5

    def test_arbiter_normal(self):
        """ Running the Alignak Arbiter - normal verbosity
        Expects log at the WARNING level - depends upon the logger configuration file
        :return:
        """
        self._arbiter(verbosity=None)

    def test_arbiter_verbose(self):
        """ Running the Alignak Arbiter - normal verbosity
        Expects log at the INFO level
        :return:
        """
        self._arbiter(verbosity='--verbose')

    def test_arbiter_verbose2(self):
        self._arbiter(verbosity='-v')

    def test_arbiter_very_verbose(self):
        """ Running the Alignak Arbiter - very verbose
        Expects log at the DEBUG level
        :return:
        """
        self._arbiter(verbosity='--debug')

    def test_arbiter_very_verbose2(self):
        self._arbiter(verbosity='-vv')

    def _arbiter(self, verbosity=None, log_file=None):
        """ Running the Alignak Arbiter with a specific verbosity

        :return:
        """
        # Set a specific logger configuration - do not use the default test configuration
        # to use the default shipped configuration
        os.environ['ALIGNAK_LOGGER_CONFIGURATION'] = \
            os.path.abspath('./etc/warning_alignak-logger.json')
        print("Logger configuration file is: %s" % os.environ['ALIGNAK_LOGGER_CONFIGURATION'])

        print("Launching arbiter ...")
        args = ["../alignak/bin/alignak_arbiter.py",
                "-n", "arbiter-master", "-e", '%s/etc/alignak.ini' % self.cfg_folder]
        if verbosity:
            args.append(verbosity)
        arbiter = subprocess.Popen(args)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        # Wait for the arbiter to get started
        time.sleep(5)

        # This function will request the arbiter daemon to stop
        self._stop_alignak_daemons(request_stop_uri='http://127.0.0.1:7770')

        errors = 0
        info_log = False
        debug_log = False
        with open('/tmp/alignak/log/arbiter-master.log') as f:
            for line in f:
                if 'DEBUG:' in line:
                    debug_log = True
                if 'INFO:' in line:
                    info_log = True
                if 'ERROR:' in line or 'CRITICAL:' in line:
                    print("*** %s" % line.rstrip())
                    errors = errors + 1

        # arbiter process may exit with no errors!
        # assert errors == 0
        # Arbiter changed the log level to INFO because of the verify mode
        if verbosity in ['-v', '--verbose']:
            assert info_log is True
        # Arbiter changed the log level to DEBUG because of the verify mode
        if verbosity in ['-vv', '--debug']:
            assert debug_log is True

    def test_broker(self):
        """ Running the Alignak Broker

        :return:
        """
        print("Launching broker ...")
        args = ["../alignak/bin/alignak_broker.py", "-n", "broker-master", "-e", '%s/etc/alignak.ini' % self.cfg_folder]
        broker = subprocess.Popen(args)
        print("%s launched (pid=%d)" % ('broker', broker.pid))

        # Wait for the broker to get started
        time.sleep(2)

        # This function will request the arbiter daemon to stop
        self._stop_alignak_daemons(request_stop_uri='http://127.0.0.1:7772')

        errors = 0
        with open('/tmp/alignak/log/broker-master.log') as f:
            for line in f:
                if 'ERROR:' in line or 'CRITICAL:' in line:
                    print("*** %s" % line.rstrip())
                    errors = errors + 1
        # broker process must exit with no errors
        assert errors == 0

    def test_poller(self):
        """ Running the Alignak poller

        :return:
        """
        print("Launching poller ...")
        args = ["../alignak/bin/alignak_poller.py", "-n", "poller-master", "-e", '%s/etc/alignak.ini' % self.cfg_folder]
        poller = subprocess.Popen(args)
        print("%s launched (pid=%d)" % ('poller', poller.pid))

        # Wait for the poller to get started
        time.sleep(2)

        # This function will request the arbiter daemon to stop
        self._stop_alignak_daemons(request_stop_uri='http://127.0.0.1:7771')

        errors = 0
        with open('/tmp/alignak/log/poller-master.log') as f:
            for line in f:
                if 'ERROR:' in line or 'CRITICAL:' in line:
                    print("*** %s" % line.rstrip())
                    errors = errors + 1
        # poller process must exit with a return code == 0 and no errors
        assert errors == 0

    def test_reactionner(self):
        """ Running the Alignak reactionner

        :return:
        """
        print("Launching reactionner ...")
        args = ["../alignak/bin/alignak_reactionner.py", "-n", "reactionner-master", "-e", '%s/etc/alignak.ini' % self.cfg_folder]
        reactionner = subprocess.Popen(args)
        print("%s launched (pid=%d)" % ('reactionner', reactionner.pid))

        # Wait for the reactionner to get started
        time.sleep(2)

        # This function will request the arbiter daemon to stop
        self._stop_alignak_daemons(request_stop_uri='http://127.0.0.1:7769')

        errors = 0
        with open('/tmp/alignak/log/reactionner-master.log') as f:
            for line in f:
                if 'ERROR:' in line or 'CRITICAL:' in line:
                    print("*** %s" % line.rstrip())
                    errors = errors + 1
        # reactionner process must exit with a return code == 0 and no errors
        assert errors == 0

    def test_receiver(self):
        """ Running the Alignak receiver

        :return:
        """
        print("Launching receiver ...")
        args = ["../alignak/bin/alignak_receiver.py", "-n", "receiver-master", "-e", '%s/etc/alignak.ini' % self.cfg_folder]
        receiver = subprocess.Popen(args)
        print("%s launched (pid=%d)" % ('receiver', receiver.pid))

        # Wait for the receiver to get started
        time.sleep(2)

        # This function will request the arbiter daemon to stop
        self._stop_alignak_daemons(request_stop_uri='http://127.0.0.1:7773')

        errors = 0
        with open('/tmp/alignak/log/receiver-master.log') as f:
            for line in f:
                if 'ERROR:' in line or 'CRITICAL:' in line:
                    print("*** %s" % line.rstrip())
                    errors = errors + 1
        # receiver process must exit with a return code == 0 and no errors
        assert errors == 0

    def test_scheduler(self):
        """ Running the Alignak scheduler

        :return:
        """
        print("Launching scheduler ...")

        args = ["../alignak/bin/alignak_scheduler.py", "-n", "scheduler-master",
                "-e", '%s/etc/alignak.ini' % self.cfg_folder]
        scheduler = subprocess.Popen(args)
        print("%s launched (pid=%d)" % ('scheduler', scheduler.pid))

        # Wait for the scheduler to get started
        time.sleep(2)

        # This function will request the arbiter daemon to stop
        self._stop_alignak_daemons(request_stop_uri='http://127.0.0.1:7768')

        errors = 0
        with open('/tmp/alignak/log/scheduler-master.log') as f:
            for line in f:
                if 'ERROR:' in line or 'CRITICAL:' in line:
                    print("*** %s" % line.rstrip())
                    errors = errors + 1
        # scheduler process must exit with a return code == 0 and no errors
        assert errors == 0
