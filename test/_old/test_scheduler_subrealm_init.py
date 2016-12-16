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



import subprocess
from time import sleep

from alignak_test import *

import alignak.log as alignak_log

from alignak.daemons.schedulerdaemon import Alignak
from alignak.daemons.arbiterdaemon import Arbiter

daemons_config = {
    Alignak: "etc/test_scheduler_subrealm_init/schedulerd.ini",
    Arbiter: ["etc/test_scheduler_subrealm_init/alignak.cfg"]
}


class testSchedulerInit(AlignakTest):
    def setUp(self):
        time_hacker.set_real_time()
        self.arb_proc = None

    def create_daemon(self):
        cls = Alignak
        return cls(daemons_config[cls], False, True, False, None)

    def _get_subproc_data(self, proc):
        try:
            proc.terminate()  # make sure the proc has exited..
            proc.wait()
        except Exception as err:
            print("prob on terminate and wait subproc: %s" % err)
        data = {}
        data['out'] = proc.stdout.read()
        data['err'] = proc.stderr.read()
        data['rc'] = proc.returncode
        return data

    def tearDown(self):
        proc = self.arb_proc
        if proc:
            self._get_subproc_data(proc)  # so to terminate / wait it..

    def test_scheduler_subrealm_init(self):

        alignak_log.local_log = None  # otherwise get some "trashs" logs..
        sched = self.create_daemon()

        sched.load_config_file()

        sched.do_daemon_init_and_start(fake=True)
        sched.load_modules_manager('scheduler-name')

        # Launch an arbiter so that the scheduler get a conf and init
        args = ["../alignak/bin/alignak_arbiter.py", "-c", daemons_config[Arbiter][0]]
        proc = self.arb_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Ok, now the conf
        for i in range(20):
            sched.wait_for_initial_conf(timeout=1)
            if sched.new_conf:
                break
        self.assertTrue(sched.new_conf)

        sched.setup_new_conf()

         # Test receivers are init like pollers
        assert sched.reactionners != {}  # Previously this was {} for ever
        assert sched.reactionners.values()[0]['uri'] == 'http://localhost:7779/' # Test dummy value

        # I want a simple init
        sched.must_run = False
        sched.sched.must_run = False
        sched.sched.run()

        # "Clean" shutdown
        sleep(2)
        try:
            os.kill(int(open("tmp/arbiterd.pid").read()), 2)
            sched.do_stop()
        except Exception as err:
            data = self._get_subproc_data(proc)
            data.update(err=err)
            self.assertTrue(False,
                "Could not read pid file or so : %(err)s\n"
                "rc=%(rc)s\nstdout=%(out)s\nstderr=%(err)s" % data)

if __name__ == '__main__':
    unittest.main()
