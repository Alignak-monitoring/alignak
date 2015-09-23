#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2015: Alignak team, see AUTHORS.txt file for contributors
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
# This file is used to test reading and processing of config files
#

from __future__ import print_function

import os
import tempfile
import shutil

from alignak_tst_utils import get_free_port
from alignak_test import unittest

from alignak.daemon import InvalidPidFile, InvalidWorkDir
from alignak.daemons.pollerdaemon import Poller
from alignak.daemons.brokerdaemon import Broker
from alignak.daemons.schedulerdaemon import Alignak
from alignak.daemons.reactionnerdaemon import Reactionner
from alignak.daemons.arbiterdaemon import Arbiter
from alignak.http.daemon import PortNotFree
import time

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


daemons_config = {
    Broker:       "etc/core/daemons/brokerd.ini",
    Poller:       "etc/core/daemons/pollerd.ini",
    Reactionner:  "etc/core/daemons/reactionnerd.ini",
    Alignak:      "etc/core/daemons/schedulerd.ini",
    Arbiter:    ["etc/core/alignak.cfg"]
}

#############################################################################

class template_Daemon_Bad_Start():

    @classmethod
    def setUpClass(cls):
        #time_hacker.set_real_time()  # just to be sure..
        # the daemons startup code does actually a `chrdir`,
        # in Daemon.change_to_workdir,
        # so in order to be always safe, let's save the cwd when we are setup,
        # we'll chdir() to it in tearDown..
        cls._launch_dir = os.getcwd()

    @classmethod
    def tearDown(cls):
        os.chdir(cls._launch_dir)

    def get_login_and_group(self, p):
        try:
            p.user = get_cur_user()
            p.group = get_cur_group()
        except OSError:  # on some rare case, we can have a problem here
            # so bypass it and keep default value
            return

    def create_daemon(self):
        cls = self.daemon_cls
        return cls(daemons_config[cls], False, True, False, None, '')

    def get_daemon(self):

        #alignak_log.local_log = None  # otherwise get some "trashs" logs..
        d = self.create_daemon()

        # configuration is actually "relative" :
        # some config file reference others with a relative path (from THIS_DIR).
        # so any time we load it we have to make sure we are back at THIS_DIR:
        # THIS_DIR should also be equal to self._launch_dir, so use that:
        os.chdir(self._launch_dir)

        d.load_config_file()
        d.port = get_free_port()
        d.pidfile = "pidfile"
        self.get_login_and_group(d)
        return d

    def start_daemon(self, daemon):
        daemon.do_daemon_init_and_start(fake=True)

    def test_bad_piddir(self):
        print("Testing bad pidfile ...")
        d = self.get_daemon()
        d.workdir = tempfile.mkdtemp()
        d.pidfile = os.path.join('/DONOTEXISTS', "daemon.pid")


        with self.assertRaises(InvalidPidFile):
            self.start_daemon(d)
        d.do_stop()

        shutil.rmtree(d.workdir)

    def test_bad_workdir(self):
        print("Testing bad workdir ... mypid=%d" % (os.getpid()))
        d = self.get_daemon()
        d.workdir = '/DONOTEXISTS'
        with self.assertRaises(InvalidWorkDir):
            self.start_daemon(d)
        d.do_stop()

    def test_port_not_free(self):
        print("Testing port not free ... mypid=%d" % (os.getpid()))
        d1 = self.get_daemon()

        temp = tempfile.mkdtemp()
        d1.workdir = temp
        d1.host = "127.0.0.1"  # Force all interfaces

        self.start_daemon(d1)
        # so that second daemon will not see first started one:
        todel = os.path.join(temp, d1.pidfile)
        os.unlink(todel)

        d2 = self.get_daemon()
        d2.workdir = d1.workdir
        d2.host = "127.0.0.1"  # Force all interfaces
        d2.port = d1.http_daemon.port

        with self.assertRaises(PortNotFree):
            # Do start by hand because we don't want to run the thread.
            # PortNotFree will occur here not in the thread.
            d2.change_to_user_group()
            d2.change_to_workdir()
            d2.check_parallel_run()
            d2.setup_communication_daemon()
            d2.http_daemon_thread()


        d2.http_daemon.srv.ready = False
        time.sleep(1)
        d2.http_daemon.srv.requests.stop()
        d2.do_stop()

        d1.http_daemon.srv.ready = False
        time.sleep(1)
        d1.http_daemon.srv.requests.stop()
        d1.do_stop()

        shutil.rmtree(d1.workdir)

#############################################################################

class Test_Broker_Bad_Start(template_Daemon_Bad_Start, unittest.TestCase):
    daemon_cls = Broker


class Test_Scheduler_Bad_Start(template_Daemon_Bad_Start, unittest.TestCase):
    daemon_cls = Alignak


class Test_Poller_Bad_Start(template_Daemon_Bad_Start, unittest.TestCase):
    daemon_cls = Poller


class Test_Reactionner_Bad_Start(template_Daemon_Bad_Start, unittest.TestCase):
    daemon_cls = Reactionner


class Test_Arbiter_Bad_Start(template_Daemon_Bad_Start, unittest.TestCase):

    daemon_cls = Arbiter

    def create_daemon(self):
        """ arbiter is always a bit special .. """
        cls = self.daemon_cls
        return cls(daemons_config[cls], False, True, False, False, None, '')

#############################################################################

if __name__ == '__main__':
    unittest.main()
