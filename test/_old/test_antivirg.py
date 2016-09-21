#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*
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

from alignak_test import *

class TestConfig(AlignakTest):

    def setUp(self):
        # load the configuration from file
        self.setup_with_file(['etc/alignak_antivirg.cfg'])

    def test_hostname_antivirg(self):
        """Check that it is allowed to have a host with the "__ANTI-VIRG__" substring in its hostname"""

        # the global configuration must be valid
        self.assertTrue(self.conf.conf_is_correct)

        # try to get the host
        # if it is not possible to get the host, it is probably because
        # "__ANTI-VIRG__" has been replaced by ";"
        hst = self.conf.hosts.find_by_name('test__ANTI-VIRG___0')
        self.assertIsNotNone(hst, "host 'test__ANTI-VIRG___0' not found")

        # Check that the host has a valid configuration
        self.assertTrue(hst.is_correct(), "config of host '%s' is not true" % hst.get_name())

    def test_parsing_comment(self):
        """Check that the semicolon is a comment delimiter"""

        # the global configuration must be valid
        self.assertTrue(self.conf.conf_is_correct, "config is not correct")

        # try to get the host
        hst = self.conf.hosts.find_by_name('test_host_1')
        self.assertIsNotNone(hst, "host 'test_host_1' not found")

        # Check that the host has a valid configuration
        self.assertTrue(hst.is_correct(), "config of host '%s' is not true" % (hst.get_name()))

    def test_escaped_semicolon(self):
        """Check that it is possible to have a host with a semicolon in its hostname
           
           The consequences of this aren't tested. We try just to send a command but 
           I think that others programs which send commands don't think to escape 
           the semicolon.

        """

        # the global configuration must be valid
        self.assertTrue(self.conf.conf_is_correct)

        # try to get the host
        hst = self.conf.hosts.find_by_name('test_host_2;with_semicolon')
        self.assertIsNotNone(hst, "host 'test_host_2;with_semicolon' not found")

        # Check that the host has a valid configuration
        self.assertTrue(hst.is_correct(), "config of host '%s' is not true" % hst.get_name())

        # We can send a command by escaping the semicolon.


        command = '[%lu] PROCESS_HOST_CHECK_RESULT;test_host_2\;with_semicolon;2;down' % (time.time())
        self.sched.run_external_command(command)

        # can need 2 run for get the consum (I don't know why)
        self.scheduler_loop(1, [])
        self.scheduler_loop(1, [])

if '__main__' == __name__:
    unittest.main()

