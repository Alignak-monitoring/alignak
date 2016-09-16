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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Frédéric MOHIER, frederic.mohier@ipmfrance.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
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
from alignak_test import AlignakTest, time_hacker
from alignak.external_command import ExternalCommandManager
from alignak.misc.common import DICT_MODATTR
import time
import ujson
import unittest2 as unittest
from alignak_test import AlignakTest, time_hacker
from alignak.external_command import ExternalCommand, ExternalCommandManager
from alignak.misc.common import DICT_MODATTR
from alignak.daemons.receiverdaemon import Receiver


class TestExternalCommands(AlignakTest):
    """
    This class tests the external commands
    """
    def setUp(self):
        """
        For each test load and check the configuration
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_external_commands.cfg')
        self.assertTrue(self.conf_is_correct)

        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

        time_hacker.set_real_time()

    def send_cmd(self, line):
        s = '[%d] %s\n' % (int(time.time()), line)
        print "Writing %s in %s" % (s, self.conf.command_file)
        fd = open(self.conf.command_file, 'wb')
        fd.write(s)
        fd.close()

    def test_change_and_reset_modattr(self):
        # Receiver receives unknown host external command
        excmd = '[%d] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;1' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)

        for i in self.schedulers[0].sched.recurrent_works:
            (name, fun, nb_ticks) = self.schedulers[0].sched.recurrent_works[i]
            if nb_ticks == 1:
                fun()

        svc = self.schedulers[0].sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        self.assertEqual(1, svc.modified_attributes)
        self.assertFalse(getattr(svc, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute))

    # @unittest.skip("Temporary disabled")
    def test_change_retry_host_check_interval(self):
        excmd = '[%d] CHANGE_RETRY_HOST_CHECK_INTERVAL;test_host_0;42' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)

        for i in self.schedulers[0].sched.recurrent_works:
            (name, fun, nb_ticks) = self.schedulers[0].sched.recurrent_works[i]
            if nb_ticks == 1:
                fun()

        host = self.schedulers[0].sched.hosts.find_by_name("test_host_0")

        self.assertEqual(2048, host.modified_attributes)
        self.assertEqual(getattr(host, DICT_MODATTR["MODATTR_RETRY_CHECK_INTERVAL"].attribute), 42)
        self.assert_no_log_match("A command was received for service.*")

    def test_special_commands(self):
        # RESTART_PROGRAM
        excmd = '[%d] RESTART_PROGRAM' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assert_any_log_match('RESTART')
        self.assert_any_log_match('I awoke after sleeping 3 seconds')

        # RELOAD_CONFIG
        excmd = '[%d] RELOAD_CONFIG' % int(time.time())
        self.schedulers[0].sched.run_external_command(excmd)
        self.external_command_loop()
        self.assert_any_log_match('RELOAD')
        self.assert_any_log_match('I awoke after sleeping 2 seconds')

        # Show recent logs
        self.show_logs()

