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
from alignak_test import AlignakTest

from alignak.http.generic_interface import GenericInterface
from alignak.http.receiver_interface import ReceiverInterface
from alignak.http.arbiter_interface import ArbiterInterface
from alignak.http.scheduler_interface import SchedulerInterface
from alignak.http.broker_interface import BrokerInterface


class TestLaunchDaemons(AlignakTest):
    def setUp(self):
        super(TestLaunchDaemons, self).setUp()

        # copy the default shipped configuration files in /tmp/etc and change the root folder
        # used by the daemons for pid and log files in the alignak.ini file
        if os.path.exists('/tmp/etc/alignak'):
            shutil.rmtree('/tmp/etc/alignak')

        if os.path.exists('/tmp/alignak.log'):
            os.remove('/tmp/alignak.log')

        if os.path.exists('/tmp/monitoring-logs.log'):
            os.remove('/tmp/monitoring-logs.log')

        print("Preparing configuration...")
        shutil.copytree('../etc', '/tmp/etc/alignak')
        files = ['/tmp/etc/alignak/alignak.ini']
        replacements = {
            '_dist=/usr/local/': '_dist=/tmp',
            'user=alignak': ';user=alignak',
            'group=alignak': ';group=alignak'
        }
        self._files_update(files, replacements)

        # Clean the former existing pid and log files
        print("Cleaning pid and log files...")
        for daemon in ['arbiter-master', 'scheduler-master', 'broker-master',
                       'poller-master', 'reactionner-master', 'receiver-master']:
            if os.path.exists('/tmp/var/run/%s.pid' % daemon):
                os.remove('/tmp/var/run/%s.pid' % daemon)
            if os.path.exists('/tmp/var/log/%s.log' % daemon):
                os.remove('/tmp/var/log/%s.log' % daemon)

    def tearDown(self):
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
        assert "usage: alignak_arbiter.py" in stderr
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
        assert "usage: alignak_arbiter.py" in stderr
        # Arbiter process must exit with a return code == 2
        assert ret == 2

    def test_arbiter_class_no_environment(self):
        """ Instantiate the Alignak Arbiter class without environment file

        :return:
        """
        from alignak.daemons.arbiterdaemon import Arbiter
        print("Instantiate arbiter without environment file...")
        # Using values that are usually provided by the command line parameters
        args = {
            'env_file': '',
            'alignak_name': 'alignak-test', 'daemon_name': 'arbiter-master',
            'monitoring_files': ['../etc/alignak.cfg']
        }
        self.arbiter = Arbiter(**args)

        print("Arbiter: %s" % (self.arbiter))
        assert self.arbiter.env_filename == ''
        assert self.arbiter.monitoring_config_files == [os.path.abspath('../etc/alignak.cfg')]

        # Configure the logger
        self.arbiter.log_level = 'ERROR'
        self.arbiter.setup_alignak_logger()

        # Setup our modules manager
        self.arbiter.load_modules_manager()

        # Load and initialize the arbiter configuration
        # This to check that the configuration is correct!
        self.arbiter.load_monitoring_config_file()

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
        assert "Daemon \'arbiter-master\' is started with an environment file: " \
               "/tmp/etc/unexisting.ini\n* required configuration file does not " \
               "exist: /tmp/etc/unexisting.ini" in stdout
        # Arbiter process must exit with a return code == 1
        assert ret == 1

    def test_arbiter_no_monitoring_configuration(self):
        """ Running the Alignak Arbiter with no monitoring configuration file

        :return:
        """
        print("Launching arbiter with no monitoring configuration...")

        # Update configuration with a bad file name
        files = ['/tmp/etc/alignak/alignak.ini']
        replacements = {
            ';CFG=%(etcdir)s/alignak.cfg': 'CFG='
        }
        self._files_update(files, replacements)

        args = ["../alignak/bin/alignak_arbiter.py", "-e", "/tmp/etc/alignak/alignak.ini"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        # Waiting for arbiter to parse the configuration
        sleep(60)

        ret = arbiter.poll()
        assert ret is not None, "Arbiter is still running!"
        print("*** Arbiter exited with code: %d" % ret)
        stdout = arbiter.stdout.read()
        assert "Daemon 'arbiter-master' is started with an environment " \
               "file: /tmp/etc/alignak/alignak.ini" in stdout
        stderr = arbiter.stderr.read()
        print(stderr)
        # assert "The Alignak environment file is not existing or do not " \
        #        "define any monitoring configuration files. " \
        #        "The arbiter can not start correctly." in stderr
        # Arbiter process must exit with a return code == 4
        assert ret == 4

    def test_arbiter_unexisting_monitoring_configuration(self):
        """ Running the Alignak Arbiter with a not existing monitoring configuration file

        :return:
        """
        print("Launching arbiter with no monitoring configuration...")

        # Update configuration with a bad file name
        files = ['/tmp/etc/alignak/alignak.ini']
        replacements = {
            ';CFG=%(etcdir)s/alignak.cfg': 'CFG=%(etcdir)s/alignak.cfg',
            # ';log_cherrypy=1': 'log_cherrypy=1'
        }
        self._files_update(files, replacements)

        args = ["../alignak/bin/alignak_arbiter.py", "-e", "/tmp/etc/alignak/alignak.ini"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        # Waiting for arbiter to parse the configuration and try a dispatch
        sleep(15)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %s" % ret)
        errors = False
        stderr = False
        for line in iter(arbiter.stdout.readline, b''):
            if 'ERROR' in line:
                print("*** " + line.rstrip())
                errors = True
            assert 'CRITICAL' not in line
        for line in iter(arbiter.stderr.readline, b''):
            print("*** " + line.rstrip())
            stderr = True

        # Arbiter process must exit with a return code == 1
        # assert ret == 4
        # No error messages be sent to stderr but in the log
        # Cherrypy
        if os.sys.version_info > (2, 7):
            assert not stderr
        # Errors must exist in the logs
        assert errors

    def test_arbiter_bad_configuration(self):
        """ Running the Alignak Arbiter with bad monitoring configuration (unknown sub directory)

        :return:
        """
        print("Launching arbiter with a bad monitoring configuration...")

        # Update monitoring configuration file name
        files = ['/tmp/etc/alignak/alignak.ini']
        replacements = {
            ';CFG=%(etcdir)s/alignak.cfg': 'CFG=%(etcdir)s/alignak.cfg',
            ';log_cherrypy=1': 'log_cherrypy=1'
        }
        self._files_update(files, replacements)

        # Update configuration with a bad file name
        files = ['/tmp/etc/alignak/alignak.cfg']
        replacements = {
            'cfg_dir=arbiter/objects/realms': 'cfg_dir=unexisting/objects/realms'
        }
        self._files_update(files, replacements)

        args = ["../alignak/bin/alignak_arbiter.py", "-e", "/tmp/etc/alignak/alignak.ini"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        # Waiting for arbiter to parse the configuration
        sleep(30)

        ret = arbiter.poll()
        assert ret is not None, "Arbiter is still running!"
        print("*** Arbiter exited with code: %s" % ret)
        # Arbiter process must exit with a return code == 1
        assert ret == 1
        errors = False
        stderr = False
        for line in iter(arbiter.stdout.readline, b''):
            if 'ERROR: ' in line:
                print("*** " + line.rstrip())
                errors = True
            assert 'CRITICAL' not in line
        for line in iter(arbiter.stderr.readline, b''):
            print("*** " + line.rstrip())
            stderr = True

        # No error message sent to stderr but in the logger
        # Some message may be raised by the cherrypy engine...
        # assert not stderr
        # Errors must exist in the logs
        assert errors

    def test_arbiter_i_am_not_configured(self):
        """ Running the Alignak Arbiter with missing arbiter configuration

        :return:
        """
        print("Launching arbiter with a missing arbiter configuration...")

        # Update monitoring configuration file name
        files = ['/tmp/etc/alignak/alignak.ini']
        replacements = {
            ';CFG=%(etcdir)s/alignak.cfg': 'CFG=%(etcdir)s/alignak.cfg',
            ';log_cherrypy=1': 'log_cherrypy=1'
        }
        self._files_update(files, replacements)

        args = ["../alignak/bin/alignak_arbiter.py", "-e", "/tmp/etc/alignak/alignak.ini", "-n", "my-arbiter-name"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        # Waiting for arbiter to parse the configuration
        sleep(3)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %d" % ret)
        assert ret is not None, "Arbiter is still running!"
        stdout = arbiter.stdout.read()
        stderr = arbiter.stderr.read()
        assert "I cannot find my own configuration (my-arbiter-name)" in stdout
        # Arbiter process must exit with a return code == 1
        assert ret == 1

    def test_arbiter_verify(self):
        """ Running the Alignak Arbiter in verify mode only with the default shipped configuration

        :return:
        """
        print("Launching arbiter with configuration file...")
        args = ["../alignak/bin/alignak_arbiter.py", "-e", "/tmp/etc/alignak/alignak.ini", "-V"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        sleep(5)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %s" % ret)
        assert ret is not None, "Arbiter is still running!"
        errors = 0
        for line in iter(arbiter.stdout.readline, b''):
            print(">>> " + line.rstrip())
            if 'ERROR' in line:
                errors = errors + 1
            if 'CRITICAL' in line:
                errors = errors + 1
        for line in iter(arbiter.stderr.readline, b''):
            print("*** " + line.rstrip())
            # if sys.version_info > (2, 7):
            #     assert False, "stderr output!"
        # Arbiter process must exit with a return code == 0 and no errors
        assert errors == 0
        assert ret == 0

    def test_arbiter_parameters(self):
        """ Run the Alignak Arbiter with some parameters - pid file

        :return:
        """
        # All the default configuration files are in /tmp/etc

        print("Launching arbiter with forced PID file...")
        args = ["../alignak/bin/alignak_arbiter.py", "-e", "/tmp/etc/alignak/alignak.ini", "-V",
                "--pid_file", "/tmp/arbiter.pid"]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        sleep(5)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %s" % ret)
        assert ret is not None, "Arbiter is still running!"
        ok = False
        errors = 0
        for line in iter(arbiter.stdout.readline, b''):
            print(">>> " + line.rstrip())
            if "Daemon 'arbiter-master' is started with an " \
               "overridden pid file: /tmp/arbiter.pid" in line:
                ok = True
            if 'ERROR' in line:
                errors = errors + 1
            if 'CRITICAL' in line:
                errors = errors + 1
        for line in iter(arbiter.stderr.readline, b''):
            print("*** " + line.rstrip())
            # if sys.version_info > (2, 7):
            #     assert False, "stderr output!"
        # Arbiter process must exit with a return code == 0 and no errors
        assert errors == 0
        assert ret == 0
        assert ok

        # assert not os.path.exists("/tmp/arbiter.log")

        # Not able to test that the file exists because the daemon unlinks the file on exit
        # and no log exit with the pid filename
        # assert os.path.exists("/tmp/arbiter.pid")

    def test_arbiter_parameters_log(self):
        """ Run the Alignak Arbiter with some parameters - log file name

        :return:
        """
        # All the default configuration files are in /tmp/etc

        print("Launching arbiter with forced log file...")
        args = ["../alignak/bin/alignak_arbiter.py", "-e", "/tmp/etc/alignak/alignak.ini", "-V",
                "--log_file", "/tmp/arbiter.log",
                ]
        arbiter = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("%s launched (pid=%d)" % ('arbiter', arbiter.pid))

        sleep(5)

        ret = arbiter.poll()
        print("*** Arbiter exited with code: %s" % ret)
        assert ret is not None, "Arbiter is still running!"
        ok = False
        errors = 0
        for line in iter(arbiter.stdout.readline, b''):
            print(">>> " + line.rstrip())
            if "Daemon 'arbiter-master' is started with an " \
               "overridden log file: /tmp/arbiter.log" in line:
                ok = True
            if 'ERROR' in line:
                errors = errors + 1
            if 'CRITICAL' in line:
                errors = errors + 1
        for line in iter(arbiter.stderr.readline, b''):
            print("*** " + line.rstrip())
            # if sys.version_info > (2, 7):
            #     assert False, "stderr output!"
        # Arbiter process must exit with a return code == 0 and no errors
        assert errors == 0
        assert ret == 0
        assert ok

        assert os.path.exists("/tmp/arbiter.log")
        # assert os.path.exists("/tmp/arbiter.pid")

    @pytest.mark.skip("To be re-activated with spare mode")
    def test_arbiter_spare_missing_configuration(self):
        """ Run the Alignak Arbiter in spare mode - missing spare configuration

        :return:
        """
        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'run/test_launch_daemons')
        # copy etc config files in test/run/test_launch_daemons and change folder
        # in the files for pid and log files
        if os.path.exists(cfg_folder):
            shutil.rmtree(cfg_folder)

        shutil.copytree('../etc', cfg_folder)
        files = [cfg_folder + '/daemons/arbiterd.ini',
                 cfg_folder + '/arbiter/daemons/arbiter-master.cfg']
        replacements = {
            '/usr/local/var/run/alignak': '/tmp',
            '/usr/local/var/log/alignak': '/tmp',
            '/usr/local/etc/alignak': '/tmp',
            'arbiterd.log': 'arbiter-spare-configuration.log',
        }
        self._files_update(files, replacements)

        print("Cleaning pid and log files...")
        for daemon in ['arbiter']:
            if os.path.exists('/tmp/%sd.pid' % daemon):
                os.remove('/tmp/%sd.pid' % daemon)
                print("- removed /tmp/%sd.pid" % daemon)
            if os.path.exists('/tmp/%sd.log' % daemon):
                os.remove('/tmp/%sd.log' % daemon)
                print("- removed /tmp/%sd.log" % daemon)

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
        # copy etc config files in test/run/test_launch_daemons and change folder
        # in the files for pid and log files
        cfg_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'run/test_launch_daemons')
        if os.path.exists(cfg_folder):
            shutil.rmtree(cfg_folder)

        shutil.copytree('../etc', cfg_folder)
        files = [cfg_folder + '/daemons/arbiterd.ini',
                 cfg_folder + '/arbiter/daemons/arbiter-master.cfg']
        replacements = {
            '/usr/local/var/run/alignak': '/tmp',
            '/usr/local/var/log/alignak': '/tmp',
            '/usr/local/etc/alignak': '/tmp',
            'arbiterd.log': 'arbiter-spare.log',
            'arbiter-master': 'arbiter-spare',
            'spare                   0': 'spare                   1'
        }
        self._files_update(files, replacements)

        print("Cleaning pid and log files...")
        for daemon in ['arbiter']:
            if os.path.exists('/tmp/%sd.pid' % daemon):
                os.remove('/tmp/%sd.pid' % daemon)
                print("- removed /tmp/%sd.pid" % daemon)
            if os.path.exists('/tmp/%sd.log' % daemon):
                os.remove('/tmp/%sd.log' % daemon)
                print("- removed /tmp/%sd.log" % daemon)

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
            print(">>> " + line.rstrip())
            if 'INFO:' in line:
                # I must find this line
                if '[alignak.daemons.arbiterdaemon] I found myself in the configuration: arbiter-spare' in line:
                    ok += 1
                # and this one also
                if '[alignak.daemons.arbiterdaemon] I am a spare Arbiter: arbiter-spare' in line:
                    ok += 1
                if 'I am not the master arbiter, I stop parsing the configuration' in line:
                    ok += 1
                if 'Waiting for master...' in line:
                    ok += 1
                if 'Waiting for master death' in line:
                    ok += 1
                assert 'CRITICAL:' not in line
        for line in iter(arbiter.stderr.readline, b''):
            print("*** " + line.rstrip())
            if sys.version_info > (2, 7):
                assert False, "stderr output!"
        assert ok == 5
