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
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     xkilian, fmikus@acktomic.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de

#  This file is part of Shinken.
#
#  Shinken is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Shinken is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Shinken.  If not, see <http://www.gnu.org/licenses/>.

#
# This file is used to test the Alignak daemons start
#

from __future__ import print_function

import os
import time
import socket
import tempfile
import shutil

import logging

from alignak_test import AlignakTest

from alignak.version import VERSION
from alignak.daemon import InvalidPidFile, InvalidWorkingDir
from alignak.daemons.pollerdaemon import Poller
from alignak.daemons.brokerdaemon import Broker
from alignak.daemons.schedulerdaemon import Alignak
from alignak.daemons.reactionnerdaemon import Reactionner
from alignak.daemons.receiverdaemon import Receiver
from alignak.daemons.arbiterdaemon import Arbiter
import pytest

try:
    import pwd, grp
    from pwd import getpwnam
    from grp import getgrnam


    def get_cur_user():
        return pwd.getpwuid(os.getuid()).pw_name

    def get_cur_group():
        return grp.getgrgid(os.getgid()).gr_name

except ImportError, exp:  # Like in nt system
    # temporary workaround:
    def get_cur_user():
        return os.getlogin()

    def get_cur_group():
        return os.getlogin()


logger = logging.getLogger(__name__)  # pylint: disable=C0103

alignak_root = os.path.abspath("cfg/daemons")
alignak_config = os.path.abspath("cfg/daemons/alignak.cfg")
alignak_environment = os.path.abspath("cfg/daemons/alignak.ini")

#############################################################################

def get_free_port(on_ip='127.0.0.1'):
    """Get a free port for an IP address"""
    sock = socket.socket()
    try:
        sock.bind((on_ip, 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


class template_Daemon_Start():

    @classmethod
    def setUpClass(cls):
        # we'll chdir() to it in tearDown..
        cls._launch_dir = os.getcwd()

    @classmethod
    def tearDown(cls):
        os.chdir(cls._launch_dir)

    def get_login_and_group(self, daemon):
        try:
            daemon.user = get_cur_user()
            daemon.group = get_cur_group()
        except OSError:  # on some rare case, we can have a problem here
            # so bypass it and keep default value
            return

    def create_daemon(self, is_daemon=False, do_replace=False, debug_file=None):
        cls = self.daemon_cls
        args = {
            'env_file': alignak_environment,
            'alignak_name': 'my-alignak', 'daemon_name': self.daemon_name,
            'daemon_enabled': is_daemon, 'do_replace': do_replace,
            'config_file': None, 'debug': debug_file is not None, 'debug_file': debug_file,
            # 'local_log': None, 'port': None
        }
        return cls(**args)

    def get_daemon(self, is_daemon=False, do_replace=False, free_port=True, debug_file=None):
        """

        :param free_port: get a free port (True) or use the configuration defined port (False)
        :return:
        """

        daemon = self.create_daemon(is_daemon, do_replace, debug_file)

        # configuration may be "relative" :
        # some config file reference others with a relative path (from THIS_DIR).
        # so any time we load it we have to make sure we are back at THIS_DIR:
        # THIS_DIR should also be equal to self._launch_dir, so use that:
        os.chdir(self._launch_dir)

        # d.load_config_file()
        # Do not use the port in the configuration file, but get a free port
        if free_port:
            daemon.port = get_free_port()
        self.get_login_and_group(daemon)
        return daemon

    def start_daemon(self, daemon):
        """
        Start the daemon
        :param daemon:
        :return:
        """
        print("Starting daemon: %s" % daemon.name)
        daemon.load_modules_manager()
        daemon.do_load_modules([])
        daemon.do_daemon_init_and_start()

    def stop_daemon(self, daemon):
        """
        Stop the daemon
        :param daemon:
        :return:
        """
        # Do not call request_stop because it sys.exit ... and this stops the test!
        # daemon.request_stop()
        # Instead call the same code hereunder:
        print("Stopping daemon: %s" % daemon.name)
        daemon.unlink()
        daemon.do_stop()

    def test_debug_config_and_start_and_stop(self):
        """ Test configuration loaded, daemon started and stopped - daemon in debug mode

        :return:
        """
        # Start normally with debug file
        daemon = self.get_daemon(is_daemon=False, do_replace=False, free_port=False,
                            debug_file='/tmp/debug-daemon.log')
        assert daemon.debug is True
        assert daemon.debug_file == '/tmp/debug-daemon.log'
        assert daemon.pid_filename == os.path.abspath('%s.pid' % daemon.name)
        assert daemon.log_filename == os.path.abspath('%s.log' % daemon.name)

        # Start the daemon
        self.start_daemon(daemon)
        assert os.path.exists(daemon.pid_filename)
        # This assertion is False on Travis build :(
        # assert os.path.exists(d.debug_file)

        time.sleep(2)

        # Stop the daemon
        self.stop_daemon(daemon)
        assert not os.path.exists(daemon.pid_filename)

    def test_config_and_start_and_stop(self):
        """ Test configuration loaded, daemon started and stopped

        :return:
        """
        # Start normally
        daemon = self.get_daemon(is_daemon=False, do_replace=False, free_port=False)
        assert daemon.debug_file == None
        assert daemon.pid_filename == os.path.abspath('%s.pid' % daemon.name)
        save_pid_fname = daemon.pid_filename
        assert daemon.log_filename == os.path.abspath('%s.log' % daemon.name)

        # Start the daemon
        self.start_daemon(daemon)

        # Check PID
        assert os.path.exists(daemon.pid_filename)
        # Check log file
        assert os.path.exists(daemon.log_filename)

        time.sleep(2)

        # Stop the daemon and unlink the pid file
        self.stop_daemon(daemon)
        assert not os.path.exists(daemon.pid_filename)

        # Reset initial working dir
        os.chdir(self._launch_dir)

        # Start as a daemon and replace if still exists
        print("Cwd: %s" % self._launch_dir)
        daemon = self.get_daemon(is_daemon=False, do_replace=False, free_port=False)
        print("Cwd: %s" % self._launch_dir)
        # Use the same pid file
        assert daemon.pid_filename == save_pid_fname
        assert daemon.log_filename == os.path.abspath('%s.log' % daemon.name)

        # Update working dir to use temporary
        daemon.workdir = tempfile.mkdtemp()
        daemon.pid_filename = os.path.join(daemon.workdir, "daemon.pid")

        # Start the daemon
        self.start_daemon(daemon)
        assert os.path.exists(daemon.pid_filename)

        time.sleep(2)

        #  Stop the daemon
        self.stop_daemon(daemon)
        assert not os.path.exists(daemon.pid_filename)

    def test_config_and_replace_and_stop(self):
        """ Test configuration loaded, daemon started, replaced and stopped

        :return:
        """
        # # Start normally
        daemon = self.get_daemon(is_daemon=False, do_replace=False, free_port=False)
        assert daemon.debug_file == None
        assert daemon.pid_filename == os.path.abspath('%s.pid' % daemon.name)
        assert daemon.log_filename == os.path.abspath('%s.log' % daemon.name)

        # Setup logger
        daemon.setup_alignak_logger()

        # Start the daemon
        self.start_daemon(daemon)
        # Get PID
        assert os.path.exists(daemon.pid_filename)
        fpid = open(daemon.pid_filename, 'r+')
        pid_var = fpid.readline().strip(' \r\n')
        print("Daemon's pid: %s" % pid_var)
        # Check log file
        assert os.path.exists(daemon.log_filename)

        # Get daemon stratistics
        stats = daemon.get_stats_struct()
        print("Daemon: %s" % daemon.__dict__)
        assert 'metrics' in stats
        assert 'version' in stats
        assert 'name' in stats
        assert 'type' in stats
        assert stats['name'] == daemon.name
        assert stats['type'] == daemon.type
        assert 'modules' in stats

        time.sleep(2)

        # Stop the daemon, but do not unlink the pid file
        # self.stop_daemon(d)
        daemon.do_stop()
        assert os.path.exists(daemon.pid_filename)

        # Update log file information
        daemon.log_filename = os.path.abspath(os.path.join(daemon.logdir, daemon.name + ".log"))
        print("Daemon's logdir: %s" % daemon.logdir)
        print("Daemon's log: %s" % daemon.log_filename)

        # Do not reload the configuration file (avoid replacing modified properties for the test...)
        daemon.setup_alignak_logger()

        # Reset initial working dir
        os.chdir(self._launch_dir)

        # Start as a daemon and replace if still exists
        daemon = self.get_daemon(is_daemon=False, do_replace=True, free_port=False)
        assert daemon.pid_filename == os.path.abspath('%s.pid' % daemon.name)
        assert daemon.log_filename == os.path.abspath('%s.log' % daemon.name)

        # Update working dir to use temporary
        daemon.workdir = tempfile.mkdtemp()
        daemon.pid_filename = os.path.join(daemon.workdir, "daemon.pid")

        # Start the daemon
        self.start_daemon(daemon)
        assert os.path.exists(daemon.pid_filename)
        fpid = open(daemon.pid_filename, 'r+')
        pid_var = fpid.readline().strip(' \r\n')
        print("Daemon's (new) pid: %s" % pid_var)

        time.sleep(2)

        #  Stop the daemon
        self.stop_daemon(daemon)
        assert not os.path.exists(daemon.pid_filename)

    def test_bad_piddir(self):
        """ Test bad PID directory

        :return:
        """
        self.print_header()

        daemon = self.get_daemon()
        daemon.workdir = tempfile.mkdtemp()
        daemon.pid_filename = os.path.abspath(os.path.join('/DONOTEXISTS', "daemon.pid"))

        with pytest.raises(InvalidPidFile):
            self.start_daemon(daemon)
        daemon.do_stop()

    def test_bad_workdir(self):
        """ Test bad working directory

        :return:
        """
        self.print_header()

        daemon = self.get_daemon()
        daemon.workdir = '/DONOTEXISTS'

        with pytest.raises(InvalidWorkingDir):
            self.start_daemon(daemon)
        daemon.do_stop()

    def test_logger(self):
        """ Test logger setup

        :return:
        """
        self.print_header()

        daemon = self.get_daemon()
        print("Daemon: %s" % daemon)
        assert daemon.pid_filename == os.path.abspath('%s.pid' % daemon.name)
        assert daemon.log_filename == os.path.abspath('%s.log' % daemon.name)

        # # Update log file information
        # daemon.logdir = os.path.abspath('.')
        # daemon.log_filename = os.path.abspath('./test.log')

        # Do not reload the configuration file (avoid replacing modified properties for the test...)
        daemon.setup_alignak_logger()

        # Log file exists...
        assert os.path.exists(daemon.log_filename)

        with open(daemon.log_filename) as f:
            content = f.readlines()

    def test_daemon_header(self):
        """ Test daemon header

        :return:
        """
        self.print_header()

        daemon = self.get_daemon()
        expected_result = [
            "-----",
            "Alignak %s - %s daemon" % (VERSION, daemon.name),
            "Copyright (c) 2015-2017: Alignak Team",
            "License: AGPL",
            "-----",
            "My pid: %s" % daemon.pid,
            "My configuration: "
        ]
        assert daemon.get_header()[:7] == expected_result

    def test_trace_unrecoverable(self):
        """ Test unrecoverable trace

        :return:
        """
        self.print_header()

        self.daemon_cls.print_unrecoverable("test")

    def test_port_not_free(self):
        """ Test HTTP port not free detection

        :return:
        """
        self.print_header()

        print("Testing port not free ... mypid=%d" % (os.getpid()))
        d1 = self.get_daemon()

        print("PID file: %s" % d1.pid_filename)
        d1.workdir = tempfile.mkdtemp()
        d1.pid_filename = os.path.abspath(os.path.join(d1.workdir, "daemon.pid"))
        d1.host = "127.0.0.1"  # Force all interfaces

        self.start_daemon(d1)
        time.sleep(1)
        print("PID file: %s" % d1.pid_filename)
        assert os.path.exists(d1.pid_filename)

        # so that second daemon will not see first started one:
        os.unlink(d1.pid_filename)

        d2 = self.get_daemon()

        d2.workdir = d1.workdir
        d2.pid_filename = d1.pid_filename
        d2.host = "127.0.0.1"  # Force all interfaces
        d2.port = d1.http_daemon.port

        # Do start by hand because we don't want to run the thread.
        # PortNotFree will occur when setting up the HTTP communication daemon
        d2.change_to_user_group()
        d2.change_to_workdir()
        d2.check_parallel_run()
        assert not d2.setup_communication_daemon()

        # Stop the first daemon
        d1.http_daemon.srv.ready = False
        time.sleep(1)
        d1.http_daemon.srv.requests.stop()
        d1.do_stop()

        shutil.rmtree(d1.workdir)

#############################################################################

class Test_Broker_Start(template_Daemon_Start, AlignakTest):
    daemon_cls = Broker
    daemon_name = 'my_broker'


class Test_Scheduler_Start(template_Daemon_Start, AlignakTest):
    daemon_cls = Alignak
    daemon_name = 'my_scheduler'


class Test_Poller_Start(template_Daemon_Start, AlignakTest):
    daemon_cls = Poller
    daemon_name = 'my_poller'


class Test_Reactionner_Start(template_Daemon_Start, AlignakTest):
    daemon_cls = Reactionner
    daemon_name = 'my_reactionner'


class Test_Receiver_Start(template_Daemon_Start, AlignakTest):
    daemon_cls = Receiver
    daemon_name = 'my_receiver'


class Test_Arbiter_Start(template_Daemon_Start, AlignakTest):
    daemon_cls = Arbiter
    daemon_name = 'my_arbiter'

    def create_daemon(self, is_daemon=False, do_replace=False, debug_file=None):
        """ arbiter is always a bit special .. """
        cls = self.daemon_cls
        args = {
            'env_file': alignak_environment,
            'alignak_name': 'alignak-test', 'daemon_name': self.daemon_name,
            'daemon_enabled': is_daemon, 'do_replace': do_replace,
            # 'config_file': None, 'debug': True, 'debug_file': debug_file,
            'log_filename': None, 'port': None,
            'verify_only': False, 'monitoring_files': [alignak_config],
        }
        return cls(**args)

#############################################################################
