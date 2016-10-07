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
#     colourmeamused, colourmeamused@noreply.com
#     Jean Gabes, naparuba@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr

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
# This test checks that sslv3 is disabled when SSL is used with a
# cherrypy backend to secure against the Poodle vulnerability (https://poodlebleed.com)

import subprocess
from time import sleep

import httplib
import ssl
try:
    import OpenSSL
except ImportError:
    OpenSSL = None
from alignak_test import *

import alignak.log as alignak_log

from alignak.daemons.schedulerdaemon import Alignak
from alignak.daemons.arbiterdaemon import Arbiter

daemons_config = {
    Alignak:      "etc/test_sslv3_disabled/schedulerd.ini",
    Arbiter:    ["etc/test_sslv3_disabled/alignak.cfg"]
}


class testSchedulerInit(AlignakTest):
    def setUp(self):
        time_hacker.set_real_time()

    def create_daemon(self):
        cls = Alignak
        return cls(daemons_config[cls], False, True, False, None)
    @unittest.skipIf(OpenSSL is None, "Test requires OpenSSL")
    def test_scheduler_init(self):

        alignak_log.local_log = None  # otherwise get some "trashs" logs..
        d = self.create_daemon()

        d.load_config_file()

        d.do_daemon_init_and_start(fake=True)
        d.load_modules_manager()

        # Launch an arbiter so that the scheduler get a conf and init
        subprocess.Popen(["../alignak/bin/alignak_arbiter.py", "-c", daemons_config[Arbiter][0], "-d"])
        if not hasattr(ssl, 'SSLContext'):
            print 'BAD ssl version for testing, bailing out'
            return

        # ssl.PROTOCOL_SSLv3 attribute will be remove in ssl
        # 3 is TLS1.0
        ctx = ssl.SSLContext(3)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.conn = httplib.HTTPSConnection("localhost:9998", context=ctx)
        self.assertRaises(socket.error, self.conn.connect)
        try:
            self.conn.connect()
        except socket.error as e:
            self.assertEqual(e.errno, 104)

        sleep(2)
        pid = int(file("tmp/arbiterd.pid").read())
        print ("KILLING %d" % pid)*50
        os.kill(int(file("tmp/arbiterd.pid").read()), 2)
        d.do_stop()


if __name__ == '__main__':
    unittest.main()
