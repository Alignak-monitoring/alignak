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
"""
This file test the SSL on daemons
"""

import subprocess
from time import sleep
import requests
import shutil
from alignak_test import AlignakTest


class TestSsl(AlignakTest):
    """
    This class test the SSL on daemons
    """
    def _get_subproc_data(self, name):
        try:
            print("Try to end %s" % name)
            self.procs[name].send_signal(2)
            self.procs[name].send_signal(15)
            self.procs[name].wait()
        except Exception as err:
            print("prob on terminate and wait subproc %s: %s" % (name, err))
        data = {}
        data['out'] = self.procs[name].stdout.read()
        data['err'] = self.procs[name].stderr.read()
        data['rc'] = self.procs[name].returncode
        return data

    def setUp(self):
        # openssl genrsa -passout pass:wazabi -out certificate_test.key 2048
        # openssl req -new -x509 -days 3650 -key certificate_test.key -out certificate_test.csr
        # openssl dhparam -out dhparams.pem 2048
        shutil.copytree('certificate_test*', '/tmp/')
        shutil.copytree('dhparams.pem', '/tmp/')
        self.procs = {}
        self.ssl_installed = True
        try:
            from OpenSSL import SSL
        except ImportError:
            self.ssl_installed = False
            print "Install pyopenssl"
            subprocess.call(["sudo", "pip", "install", "--upgrade", "pyopenssl"])

    def tearDown(self):
        for name, proc in self.procs.items():
            if proc:
                self._get_subproc_data(name)  # so to terminate / wait it..
        if not self.ssl_installed:
            subprocess.call(["sudo", "pip", "uninstall", "pyopenssl"])

    def test_ssl_satellites(self):
        """
        Test satellites with SSL certificate

        :return: None
        """
        self.print_header()

        files = ['cfg/ssl/arbiterd.ini',
                 'cfg/ssl/brokerd.ini', 'cfg/ssl/pollerd.ini',
                 'cfg/ssl/reactionnerd.ini', 'cfg/ssl/receiverd.ini',
                 'cfg/ssl/schedulerd.ini', 'cfg/ssl/alignak.cfg']

        self.procs = {}
        satellite_map = {'arbiter': '7770',
                         'scheduler': '7768',
                         'broker': '7772',
                         'poller': '7771',
                         'reactionner': '7769',
                         'receiver': '7773'
                         }

        for daemon in ['scheduler', 'broker', 'poller', 'reactionner', 'receiver']:
            args = ["../alignak/bin/alignak_%s.py" %daemon,
                    "-c", "cfg/ssl/%sd.ini" % daemon]
            self.procs[daemon] = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        args = ["../alignak/bin/alignak_arbiter.py",
                "-c", "cfg/ssl/arbiterd.ini",
                "-a", "cfg/ssl/alignak.cfg"]
        self.procs['arbiter'] = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        sleep(8)
        req = requests.Session()

        print("Testing start")
        for name, proc in self.procs.items():
            ret = proc.poll()
            if ret is not None:
                print(proc.stdout.read())
                print(proc.stderr.read())
            self.assertIsNone(ret, "Daemon %s not started!" % name)

        print("Testing ping")
        for name, port in satellite_map.items():
            raw_data = req.get("http://localhost:%s/ping" % port)
            self.assertEqual('The client sent a plain HTTP request, but this server only speaks HTTPS on this port.', raw_data.text)

            raw_data = req.get("https://localhost:%s/ping" % port, verify=False)
            data = raw_data.json()
            self.assertEqual(data, 'pong', "Daemon %s  did not ping back!" % name)

        # get_all_states
        raw_data = req.get("https://localhost:%s/get_all_states" % satellite_map['arbiter'])
        states = raw_data.json()
        for name, _ in satellite_map.items():
            self.assertTrue(states[name][0]['alive'])
