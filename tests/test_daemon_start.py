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



import os
import sys
import time
import socket
import tempfile
import shutil

import logging

import psutil

from .alignak_test import AlignakTest

from alignak.version import VERSION
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

except ImportError as exp:  # Like in nt system
    # temporary workaround:
    def get_cur_user():
        return os.getlogin()

    def get_cur_group():
        return os.getlogin()


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

        # This to allow using a reference configuration if needed,
        # and to make some tests easier to set-up
        print("Preparing default configuration...")
        # if os.path.exists('/tmp/etc/alignak'):
        #     shutil.rmtree('/tmp/etc/alignak')

        # shutil.copytree('../etc', '/tmp/etc/alignak')
        # files = ['/tmp/etc/alignak/alignak.ini']
        # replacements = {
        #     '_dist=/usr/local/': '_dist=/tmp',
        #     ';is_daemon=0': 'is_daemon=0'
        # }
        # self._files_update(files, replacements)
        # print("Prepared")

        print("Env: %s, daemon: %s, daemonize: %s, replace: %s, debug: %s"
              % (alignak_environment, self.daemon_name, is_daemon, do_replace, debug_file))
        args = {
            'env_file': alignak_environment,
            'alignak_name': 'my-alignak', 'daemon_name': self.daemon_name,
            'is_daemon': is_daemon, 'do_replace': do_replace,
            'config_file': None, 'debug': debug_file is not None, 'debug_file': debug_file,
        }
        return cls(**args)

    def get_daemon(self, is_daemon=False, do_replace=False, free_port=True, debug_file=None):
        """

        :param free_port: get a free port (True) or use the configuration defined port (False)
        :return:
        """

        print("Get daemon...")
        daemon = self.create_daemon(is_daemon, do_replace, debug_file)
        print("Got: %s" % daemon)
        return daemon

    def start_daemon(self, daemon):
        """
        Start the daemon
        :param daemon:
        :return:
        """
        print("Starting daemon: %s" % daemon.name)
        # daemon.load_modules_manager()
        # daemon.do_load_modules([])
        daemon.do_daemon_init_and_start(set_proc_title=False)
        print("Started: %s" % daemon.name)

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
        print("Stopped")

    @pytest.mark.skip("Not easily testable with CherryPy ... "
                      "by the way this will mainly test Cherrypy ;)")
    def test_config_and_start_and_stop_debug(self):
        """ Test configuration loaded, daemon started and stopped - daemon in debug mode

        :return:
        """
        # Start normally with debug file
        self.test_config_and_start_and_stop(debug_file='/tmp/debug-daemon.log')

    @pytest.mark.skip("Not easily testable with CherryPy ... "
                      "by the way this will mainly test Cherrypy ;)")
    def test_config_and_start_and_stop(self, debug_file=None):
        """ Test configuration loaded, daemon started and stopped

        :return:
        """
        # Start normally
        daemon = self.get_daemon(debug_file=debug_file)
        print("Got daemon: %s" % daemon)
        if debug_file:
            assert daemon.debug is True
        else:
            assert daemon.debug_file == None
        assert daemon.pid_filename == os.path.abspath('/tmp/var/run/alignak/%s.pid' % daemon.name)
        save_pid_fname = daemon.pid_filename
        # assert daemon.log_filename == os.path.abspath('./cfg/daemons/log/%s.log' % daemon.name)
        assert daemon.log_filename == ''    # Because logs are defined in the logger configuration

        # Start the daemon
        self.start_daemon(daemon)

        # Check PID file
        assert os.path.exists(daemon.pid_filename)

        time.sleep(5)

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
        # assert daemon.log_filename == os.path.abspath('./cfg/daemons/log/%s.log' % daemon.name)
        assert daemon.log_filename == ''    # Because logs are defined in the logger configuration

        # Update working dir to use temporary
        daemon.workdir = tempfile.mkdtemp()
        daemon.pid_filename = os.path.join(daemon.workdir, "daemon.pid")

        # Start the daemon
        self.start_daemon(daemon)
        assert os.path.exists(daemon.pid_filename)

        time.sleep(5)

        #  Stop the daemon
        self.stop_daemon(daemon)
        assert not os.path.exists(daemon.pid_filename)

    @pytest.mark.skip("Not easily testable with CherryPy ... "
                      "by the way this will mainly test Cherrypy ;)")
    def test_config_and_replace_and_stop(self):
        """ Test configuration loaded, daemon started, replaced and stopped

        :return:
        """
        # # Start normally
        daemon = self.get_daemon(is_daemon=False, do_replace=False, free_port=False)
        assert daemon.debug_file == None
        assert daemon.pid_filename == os.path.abspath('/tmp/var/run/alignak/%s.pid' % daemon.name)
        # assert daemon.log_filename == os.path.abspath('./cfg/daemons/log/%s.log' % daemon.name)
        assert daemon.log_filename == ''    # Because logs are defined in the logger configuration

        # Start the daemon
        self.start_daemon(daemon)
        # Get PID
        assert os.path.exists(daemon.pid_filename)
        fpid = open(daemon.pid_filename, 'r+')
        pid_var = fpid.readline().strip(' \r\n')
        print("Daemon's pid: %s" % pid_var)

        # Get daemon statistics
        stats = daemon.get_daemon_stats()
        print("Daemon: %s" % daemon.__dict__)
        assert 'alignak' in stats
        assert 'version' in stats
        assert 'name' in stats
        assert 'type' in stats
        assert stats['name'] == daemon.name
        assert stats['type'] == daemon.type
        assert 'spare' in stats
        assert 'program_start' in stats
        assert 'modules' in stats
        assert 'metrics' in stats

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
        assert daemon.pid_filename == os.path.abspath('/tmp/var/run/alignak/%s.pid' % daemon.name)
        # assert daemon.log_filename == os.path.abspath('./cfg/daemons/log/%s.log' % daemon.name)
        assert daemon.log_filename == ''    # Because logs are defined in the logger configuration

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
        daemon = self.get_daemon()
        daemon.workdir = tempfile.mkdtemp()
        daemon.pid_filename = os.path.abspath(os.path.join('/DONOTEXISTS', "daemon.pid"))

        with pytest.raises(SystemExit):
            rc = self.start_daemon(daemon)
            assert rc == 1
        # Stop the daemon
        self.stop_daemon(daemon)

    def test_bad_workdir(self):
        """ Test bad working directory

        :return:
        """
        daemon = self.get_daemon()
        daemon.workdir = '/DONOTEXISTS'

        with pytest.raises(SystemExit):
            rc = self.start_daemon(daemon)
            assert rc == 1
        # Stop the daemon
        self.stop_daemon(daemon)

    def test_logger(self):
        """ Test logger setup

        :return:
        """
        self.clear_logs()

        daemon = self.get_daemon()
        assert daemon.pid_filename == os.path.abspath('%s/%s.pid' % (daemon.workdir, daemon.name))
        # assert daemon.log_filename == os.path.abspath('./cfg/daemons/log/%s.log' % daemon.name)
        assert daemon.log_filename == ''    # Because logs are defined in the logger configuration

        # Do not reload the configuration file (avoid replacing modified properties for the test...)
        daemon.setup_alignak_logger()
        daemon.debug = True

        self.show_logs()

        # The daemon log file is set by the logger configuration ... if it did not exist
        # an exception should have been raised!
        # Stop the daemon
        self.stop_daemon(daemon)

    def test_daemon_header(self):
        """ Test daemon header

        :return:
        """
        daemon = self.get_daemon()
        expected_result = [
            u"-----",
            u"   █████╗ ██╗     ██╗ ██████╗ ███╗   ██╗ █████╗ ██╗  ██╗",
            u"  ██╔══██╗██║     ██║██╔════╝ ████╗  ██║██╔══██╗██║ ██╔╝",
            u"  ███████║██║     ██║██║  ███╗██╔██╗ ██║███████║█████╔╝ ",
            u"  ██╔══██║██║     ██║██║   ██║██║╚██╗██║██╔══██║██╔═██╗ ",
            u"  ██║  ██║███████╗██║╚██████╔╝██║ ╚████║██║  ██║██║  ██╗",
            u"  ╚═╝  ╚═╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝",
            u"-----",
            u"Alignak %s - %s daemon" % (VERSION, daemon.name),
            u"Copyright (c) 2015-2019: Alignak Team",
            u"License: AGPL",
            u"-----",
            u"Python: %s" % sys.version,
            u"-----",
            u"My pid: %s" % daemon.pid
        ]
        assert daemon.get_header()[:10] == expected_result

    def test_daemon_environment(self):
        """ Test daemon environment variables

        :return:
        """
        os.environ['ALIGNAK_USER'] = 'alignak'
        os.environ['ALIGNAK_GROUP'] = 'alignak'
        daemon = self.get_daemon()
        assert daemon.user == 'alignak'
        assert daemon.group == 'alignak'
        del os.environ['ALIGNAK_USER']
        del os.environ['ALIGNAK_GROUP']

    @pytest.mark.skip("Not easily testable with CherryPy ... "
                      "by the way this will mainly test Cherrypy ;)")
    def test_port_not_free(self):
        """ Test HTTP port not free detection

        :return:
        """
        print("Testing port not free ... mypid=%d" % (os.getpid()))
        d1 = self.get_daemon()
        d2 = self.get_daemon()

        d1.workdir = tempfile.mkdtemp()
        d1.pid_filename = os.path.abspath(os.path.join(d1.workdir, "daemon.pid"))
        # d1.host = "127.0.0.1"  # Force all interfaces
        print("Listening on: %s:%s" % (d1.host, d1.port))

        self.start_daemon(d1)
        time.sleep(5)
        print("PID file: %s" % d1.pid_filename)
        assert os.path.exists(d1.pid_filename)

        # # Trying to open the daemon used port...
        # sock = socket.socket()
        # try:
        #     sock.bind((d1.host, d1.port))
        #     print("Socket: %s" % sock.getsockname()[1])
        # except socket.error as exp:
        #     print("Error: %s" % exp)
        # else:
        #     sock.close()
        #     assert False, "The socket should not be available!"

        # so that second daemon will not see first started one:
        time.sleep(1)
        os.unlink(d1.pid_filename)


        d2.workdir = d1.workdir
        d2.pid_filename = d1.pid_filename
        d2.host = "127.0.0.1"  # Force all interfaces
        # Use the same port as the first daemon
        d2.port = d1.port

        self.start_daemon(d2)
        time.sleep(5)
        # Stop the daemon
        d2.do_stop()
        time.sleep(1)

        # Stop the daemon
        d1.do_stop()
        time.sleep(1)

    @pytest.mark.skip("Not easily testable with CherryPy ... "
                      "by the way this will mainly test Cherrypy ;)")
    def test_daemon_run(self):
        """ Test daemon start run

        :return:
        """
        print("Get daemon... !!!")
        d1 = self.get_daemon()
        print("Daemon: %s" % d1)
        # d1.workdir = tempfile.mkdtemp()
        # d1.pid_filename = os.path.abspath(os.path.join(d1.workdir, "daemon.pid"))

        print("Listening on: %s:%s" % (d1.host, d1.port))
        self.start_daemon(d1)
        # time.sleep(1)
        # try:
        #     print("pid file: %s (%s)" % (d1.pid_filename, os.getpid()))
        # except Exception as exp:
        #     print("Exception: %s" % exp)
        # assert os.path.exists(d1.pid_filename)
        # print("Cherrypy: %s" % (d1.http_daemon.cherrypy_thread))
        # # print("Cherrypy: %s (%s)" % (d1.http_daemon.cherrypy_thread, d1.http_daemon.cherrypy_thread.__dict__))
        #
        # time.sleep(5)
        #
        # # Get daemon statistics
        # stats = d1.get_daemon_stats()
        # print("Daemon stats: %s" % stats)
        # These properties are only provided by the Web interface
        # assert 'alignak' in stats
        # assert 'version' in stats
        # assert 'name' in stats
        # assert 'type' in stats
        # assert stats['name'] == d1.name
        # assert stats['type'] == d1.type
        # assert 'spare' in stats
        # assert 'program_start' in stats
        # assert 'modules' in stats
        # assert 'metrics' in stats
        #
        # time.sleep(1)
        #
        # # Stop the daemon
        # # d1.do_stop()
        time.sleep(1)
        #  Stop the daemon
        self.stop_daemon(d1)

#############################################################################

class Test_Broker_Start(template_Daemon_Start, AlignakTest):
    def setUp(self):
        super(Test_Broker_Start, self).setUp()

    daemon_cls = Broker
    daemon_name = 'my_broker'


class Test_Scheduler_Start(template_Daemon_Start, AlignakTest):
    def setUp(self):
        super(Test_Scheduler_Start, self).setUp()

    daemon_cls = Alignak
    daemon_name = 'my_scheduler'


class Test_Poller_Start(template_Daemon_Start, AlignakTest):
    def setUp(self):
        super(Test_Poller_Start, self).setUp()

    daemon_cls = Poller
    daemon_name = 'my_poller'


class Test_Reactionner_Start(template_Daemon_Start, AlignakTest):
    def setUp(self):
        super(Test_Reactionner_Start, self).setUp()

    daemon_cls = Reactionner
    daemon_name = 'my_reactionner'


class Test_Receiver_Start(template_Daemon_Start, AlignakTest):
    def setUp(self):
        super(Test_Receiver_Start, self).setUp()

    daemon_cls = Receiver
    daemon_name = 'my_receiver'


class Test_Arbiter_Start(template_Daemon_Start, AlignakTest):
    def setUp(self):
        super(Test_Arbiter_Start, self).setUp()

    daemon_cls = Arbiter
    daemon_name = 'my_arbiter'
