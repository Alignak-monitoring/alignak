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

    def test_unknown_check_result_command_scheduler(self):
        # The scheduler accepts unknown passive checks...
        self.schedulers[0].sched.conf.accept_passive_unknown_check_results = True

        # Sched receives known host but unknown service service_check_result
        self.schedulers[0].sched.broks.clear()
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;unknownservice;1;' \
                'Service is Warning|rtt=9999;5;10;0;10000' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        # A brok...
        broks = [b for b in self.schedulers[0].sched.broks.values()
                 if b.type == 'unknown_service_check_result']
        self.assertTrue(len(broks) == 1)
        # ...but no logs
        self.assertEqual(0, self.count_logs(scheduler=True))

        # Sched receives unknown host and service service_check_result
        self.schedulers[0].sched.broks.clear()
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;unknownhost;unknownservice;1;' \
                'Service is Warning|rtt=9999;5;10;0;10000' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        # A brok...
        broks = [b for b in self.schedulers[0].sched.broks.values()
                 if b.type == 'unknown_service_check_result']
        self.assertTrue(len(broks) == 1)
        # ...but no logs
        self.assertEqual(0, self.count_logs(scheduler=True))

        # Sched receives unknown host host_check_result
        self.schedulers[0].sched.broks.clear()
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;unknownhost;' \
                '1;Host is Down|rtt=9999;5;10;0;10000' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        # A brok...
        broks = [b for b in self.schedulers[0].sched.broks.values()
                 if b.type == 'unknown_host_check_result']
        self.assertTrue(len(broks) == 1)
        # ...but no logs
        self.assertEqual(0, self.count_logs(scheduler=True))

        # -----------------------------------------------------------------------------------------
        # Now turn it off...
        self.schedulers[0].sched.conf.accept_passive_unknown_check_results = False

        # Sched receives known host but unknown service service_check_result
        self.schedulers[0].sched.broks.clear()
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;unknownservice;1;' \
                'Service is Warning|rtt=9999;5;10;0;10000' % time.time()
        self.schedulers[0].sched.run_external_command(excmd)
        # No brok...
        broks = [b for b in self.schedulers[0].sched.broks.values()
                 if b.type == 'unknown_service_check_result']
        self.assertTrue(len(broks) == 0)
        # ...but a log
        self.show_logs(scheduler=True)
        self.assert_log_match(1, 'A command was received for service .* '
                                 'on host .*, but the service could not be found!', scheduler=True)
        self.clear_logs(scheduler=True)

    def test_unknown_check_result_command_receiver(self):
        receiverdaemon = Receiver(None, False, False, False, None)
        receiverdaemon.direct_routing = True
        receiverdaemon.accept_passive_unknown_check_results = True

        # Receiver receives unknown host external command
        excmd = ExternalCommand('[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;unknownservice;'
                                '1;Service is Warning|rtt=9999;5;10;0;10000' % time.time())
        receiverdaemon.unprocessed_external_commands.append(excmd)
        receiverdaemon.push_external_commands_to_schedulers()
        # A brok...
        broks = [b for b in receiverdaemon.broks.values()
                 if b.type == 'unknown_service_check_result']
        self.assertEqual(len(broks), 1)
        # ...but no logs!
        self.show_logs(scheduler=True)
        self.assert_no_log_match('Passive check result was received for host .*, '
                                 'but the host could not be found!', scheduler=True)
        # self.assert_any_log_match('Receiver searching for a scheduler '
        #                           'for the external command ', scheduler=True)
        self.clear_logs(scheduler=True)

        # now turn it off...
        receiverdaemon.accept_passive_unknown_check_results = False

        excmd = ExternalCommand('[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;unknownservice;'
                                '1;Service is Warning|rtt=9999;5;10;0;10000' % time.time())
        receiverdaemon.unprocessed_external_commands.append(excmd)
        receiverdaemon.push_external_commands_to_schedulers()
        receiverdaemon.broks.clear()
        # No brok...
        broks = [b for b in receiverdaemon.broks.values()
                 if b.type == 'unknown_service_check_result']
        self.assertEqual(len(broks), 0)
        # ...but a log
        self.show_logs(scheduler=True)
        self.assert_any_log_match('Passive check result was received for host .*, '
                                 'but the host could not be found!', scheduler=True)
        # self.assert_any_log_match('Receiver searching for a scheduler '
        #                           'for the external command ', scheduler=True)
        self.clear_logs(scheduler=True)

    def test_unknown_check_result_brok(self):
        # unknown_host_check_result_brok
        excmd = '[1234567890] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is Down'
        expected = {'time_stamp': 1234567890, 'return_code': '2', 'host_name': 'test_host_0', 'output': 'Host is Down', 'perf_data': None}
        result = ujson.loads(ExternalCommandManager.get_unknown_check_result_brok(excmd).data)
        self.assertEqual(expected, result)

        # unknown_host_check_result_brok with perfdata
        excmd = '[1234567890] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is Down|rtt=9999'
        expected = {'time_stamp': 1234567890, 'return_code': '2', 'host_name': 'test_host_0', 'output': 'Host is Down', 'perf_data': 'rtt=9999'}
        result = ujson.loads(ExternalCommandManager.get_unknown_check_result_brok(excmd).data)
        self.assertEqual(expected, result)

        # unknown_service_check_result_brok
        excmd = '[1234567890] PROCESS_HOST_CHECK_RESULT;host-checked;0;Everything OK'
        expected = {'time_stamp': 1234567890, 'return_code': '0', 'host_name': 'host-checked', 'output': 'Everything OK', 'perf_data': None}
        result = ujson.loads(ExternalCommandManager.get_unknown_check_result_brok(excmd).data)
        self.assertEqual(expected, result)

        # unknown_service_check_result_brok with perfdata
        excmd = '[1234567890] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;1;Service is Warning|rtt=9999;5;10;0;10000'
        expected = {'host_name': 'test_host_0', 'time_stamp': 1234567890, 'service_description': 'test_ok_0', 'return_code': '1', 'output': 'Service is Warning', 'perf_data': 'rtt=9999;5;10;0;10000'}
        result = ujson.loads(ExternalCommandManager.get_unknown_check_result_brok(excmd).data)
        self.assertEqual(expected, result)

    # @unittest.skip("Temporary disabled")
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
