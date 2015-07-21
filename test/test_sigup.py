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

import subprocess
import signal
import os
from time import sleep
from alignak_test import unittest


class testSigHup(unittest.TestCase):
    def _get_subproc_data(self):
        try:
            self.arb_proc.terminate()  # make sure the proc has exited..
            self.arb_proc.wait()
        except Exception as err:
            print("prob on terminate and wait subproc: %s" % err)
        data = {}
        data['out'] = self.arb_proc.stdout.read()
        data['err'] = self.arb_proc.stderr.read()
        data['rc'] = self.arb_proc.returncode
        return data

    def tearDown(self):
        if self.arb_proc:
            self._get_subproc_data()  # so to terminate / wait it..

    def test_sighup_handle(self):

        args = ["../alignak/bin/alignak_arbiter.py", "-c", "etc/test_sighup/alignak.cfg"]
        self.arb_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        sleep(2)
        os.kill(self.arb_proc.pid, signal.SIGHUP)  # This should log with debug level the Relaod Conf
        os.kill(self.arb_proc.pid, signal.SIGINT)  # This should kill the proc
        data = self._get_subproc_data()
        self.assertRegexpMatches(data['out'], "Reloading configuration")


if __name__ == '__main__':
    unittest.main()

