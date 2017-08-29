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
This file test the check_result brok
"""

import time
from alignak_test import AlignakTest
from alignak.misc.serialization import unserialize


class TestMonitoringLogs(AlignakTest):
    """
    This class test the check_result brok
    """

    def check(self, item, state_id, state, expected_logs):
        """

        :param item: concerned item
        :param state_id: state identifier
        :param state: state text
        :param expected_logs: expected monitoring logs
        :return:
        """
        self._sched.brokers['broker-master']['broks'] = {}
        self.scheduler_loop(1, [[item, state_id, state]])
        time.sleep(0.1)
        monitoring_logs = []
        for brok in self._sched.brokers['broker-master']['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        for log_level, log_message in expected_logs:
            assert (log_level, log_message) in monitoring_logs

        assert len(expected_logs) == len(monitoring_logs), monitoring_logs
        time.sleep(0.1)

    def test_logs_hosts(self):
        """ Test logs for active / passive checks for hosts

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_monitoring_logs.cfg')
        assert self.conf_is_correct


        self._sched = self.schedulers['scheduler-master'].sched

        host = self._sched.hosts.find_by_name("test_host_0")
        # Make notifications sent very quickly
        host.notification_interval = 10.0
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = True

        # Host active checks
        self.check(host, 0, 'Host is UP',
                   [(u'info', u'ACTIVE HOST CHECK: test_host_0;UP;HARD;1;Host is UP')])

        self.check(host, 0, 'Host is UP',
                   [(u'info', u'ACTIVE HOST CHECK: test_host_0;UP;HARD;1;Host is UP')])

        # Host goes DOWN / SOFT
        self.check(host, 2, 'Host is DOWN',
                   [(u'error', u'HOST ALERT: test_host_0;DOWN;SOFT;1;Host is DOWN'),
                    (u'error', u'HOST EVENT HANDLER: test_host_0;DOWN;SOFT;1;eventhandler'),
                    (u'error', u'ACTIVE HOST CHECK: test_host_0;DOWN;SOFT;1;Host is DOWN')])

        self.check(host, 2, 'Host is DOWN',
                   [(u'error', u'HOST EVENT HANDLER: test_host_0;DOWN;SOFT;2;eventhandler'),
                    (u'error', u'ACTIVE HOST CHECK: test_host_0;DOWN;SOFT;2;Host is DOWN'),
                    (u'error', u'HOST ALERT: test_host_0;DOWN;SOFT;2;Host is DOWN')])

        # Host goes DOWN / HARD
        self.check(host, 2, 'Host is DOWN',
                   [(u'error', u'ACTIVE HOST CHECK: test_host_0;DOWN;HARD;3;Host is DOWN'), (
                   u'error',
                   u'HOST NOTIFICATION: test_contact;test_host_0;DOWN;notify-host;Host is DOWN'),
                    (u'error', u'HOST ALERT: test_host_0;DOWN;HARD;3;Host is DOWN'),
                    (u'error', u'HOST EVENT HANDLER: test_host_0;DOWN;HARD;3;eventhandler')])

        # Host notification raised
        self.check(host, 2, 'Host is DOWN',
                   [(u'error', u'ACTIVE HOST CHECK: test_host_0;DOWN;HARD;3;Host is DOWN'), ])

        self.check(host, 2, 'Host is DOWN',
                   [(u'error', u'ACTIVE HOST CHECK: test_host_0;DOWN;HARD;3;Host is DOWN')])

        # Host goes UP / HARD
        # Get an host check, an alert and a notification
        self.check(host, 0, 'Host is UP',
                   [(u'info',
                     u'HOST NOTIFICATION: test_contact;test_host_0;UP;notify-host;Host is UP'),
                    (u'info', u'HOST EVENT HANDLER: test_host_0;UP;HARD;3;eventhandler'),
                    (u'info', u'HOST ALERT: test_host_0;UP;HARD;3;Host is UP'),
                    (u'info', u'ACTIVE HOST CHECK: test_host_0;UP;HARD;1;Host is UP')])

        self.check(host, 0, 'Host is UP',
                   [(u'info', u'ACTIVE HOST CHECK: test_host_0;UP;HARD;1;Host is UP')])

        self.check(host, 0, 'Host is UP',
                   [(u'info', u'ACTIVE HOST CHECK: test_host_0;UP;HARD;1;Host is UP')])

    def test_logs_services(self):
        """ Test logs for active / passive checks for hosts

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_monitoring_logs.cfg')
        assert self.conf_is_correct

        self._sched = self.schedulers['scheduler-master'].sched

        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = True

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        # Make notifications sent very quickly
        svc.notification_interval = 10.0
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = True

        # Get sure that host is UP
        self.check(host, 0, 'Host is UP',
                   [(u'info', u'ACTIVE HOST CHECK: test_host_0;UP;HARD;1;Host is UP')])

        # Service is ok
        self.check(svc, 0, 'Service is OK',
                   [(u'info',
                     u'ACTIVE SERVICE CHECK: test_host_0;test_ok_0;OK;HARD;1;'
                     u'Service is OK')])
        self.check(svc, 0, 'Service is OK',
                   [(u'info',
                     u'ACTIVE SERVICE CHECK: test_host_0;test_ok_0;OK;HARD;1;'
                     u'Service is OK')])

        # Service goes warning / SOFT
        self.check(svc, 1, 'Service is WARNING',
                   [(u'warning',
                     u'SERVICE EVENT HANDLER: test_host_0;test_ok_0;WARNING;SOFT;1;eventhandler'), (
                    u'warning',
                    u'SERVICE ALERT: test_host_0;test_ok_0;WARNING;SOFT;1;Service is WARNING'), (
                    u'warning',
                    u'ACTIVE SERVICE CHECK: test_host_0;test_ok_0;WARNING;SOFT;1;'
                    u'Service is WARNING')])

        # Service goes warning / HARD
        # Get a service check, an alert and a notification
        self.check(svc, 1, 'Service is WARNING',
                   [(u'warning',
                     u'ACTIVE SERVICE CHECK: test_host_0;test_ok_0;WARNING;HARD;2;'
                     u'Service is WARNING'),
                    (u'warning',
                     u'SERVICE ALERT: test_host_0;test_ok_0;WARNING;HARD;2;'
                     u'Service is WARNING'), (
                    u'warning',
                    u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;'
                    u'WARNING;notify-service;Service is WARNING'),
                    (u'warning',
                     u'SERVICE EVENT HANDLER: test_host_0;test_ok_0;WARNING;HARD;2;eventhandler')])

        # Service notification raised
        self.check(svc, 1, 'Service is WARNING',
                   [(u'warning',
                     u'ACTIVE SERVICE CHECK: test_host_0;test_ok_0;WARNING;HARD;2;'
                     u'Service is WARNING')])

        self.check(svc, 1, 'Service is WARNING',
                   [(u'warning',
                     u'ACTIVE SERVICE CHECK: test_host_0;test_ok_0;WARNING;HARD;2;'
                     u'Service is WARNING')])

        # Service goes OK
        self.check(svc, 0, 'Service is OK',
                   [(u'info',
                     u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;OK;notify-service;'
                     u'Service is OK'),
                    (u'info',
                     u'SERVICE EVENT HANDLER: test_host_0;test_ok_0;OK;HARD;2;eventhandler'), (
                    u'info',
                    u'ACTIVE SERVICE CHECK: test_host_0;test_ok_0;OK;HARD;1;Service is OK'),
                    (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;HARD;2;Service is OK')])

        self.check(svc, 0, 'Service is OK',
                   [(u'info',
                     u'ACTIVE SERVICE CHECK: test_host_0;test_ok_0;OK;HARD;1;Service is OK')])

        # Service goes CRITICAL
        self.check(svc, 2, 'Service is CRITICAL',
                   [(u'error',
                     u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Service is CRITICAL'), (
                    u'error',
                    u'SERVICE EVENT HANDLER: test_host_0;test_ok_0;CRITICAL;SOFT;1;eventhandler'), (
                    u'error',
                    u'ACTIVE SERVICE CHECK: test_host_0;test_ok_0;CRITICAL;SOFT;1;'
                    u'Service is CRITICAL')])

        self.check(svc, 2, 'Service is CRITICAL',
                   [(u'error',
                     u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;HARD;2;Service is CRITICAL'), (
                    u'error',
                    u'SERVICE EVENT HANDLER: test_host_0;test_ok_0;CRITICAL;HARD;2;eventhandler'), (
                    u'error',
                    u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;'
                    u'CRITICAL;notify-service;Service is CRITICAL'),
                    (u'error',
                     u'ACTIVE SERVICE CHECK: test_host_0;test_ok_0;CRITICAL;HARD;2;'
                     u'Service is CRITICAL')])

        # Service goes OK
        self.check(svc, 0, 'Service is OK',
                   [(u'info',
                     u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;'
                     u'OK;notify-service;Service is OK'),
                    (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;HARD;2;Service is OK'), (
                    u'info',
                    u'SERVICE EVENT HANDLER: test_host_0;test_ok_0;OK;HARD;2;eventhandler'), (
                    u'info',
                    u'ACTIVE SERVICE CHECK: test_host_0;test_ok_0;OK;HARD;1;Service is OK')])


        self.check(svc, 0, 'Service OK',
                   [(u'info', u'ACTIVE SERVICE CHECK: test_host_0;test_ok_0;OK;HARD;1;Service OK')])

    def test_logs_hosts_disabled(self):
        """ Test disabled logs for active / passive checks for hosts

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_monitoring_logs_disabled.cfg')
        assert self.conf_is_correct

        self._sched = self.schedulers['scheduler-master'].sched

        host = self._sched.hosts.find_by_name("test_host_0")
        # Make notifications sent very quickly
        host.notification_interval = 10.0
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = True

        #  Host active checks
        self.check(host, 0, 'Host is UP', [])

        self.check(host, 0, 'Host is UP', [])

        # Host goes DOWN / SOFT
        self.check(host, 2, 'Host is DOWN',
                   [(u'error', u'HOST ALERT: test_host_0;DOWN;SOFT;1;Host is DOWN')])

        self.check(host, 2, 'Host is DOWN',
                   [(u'error', u'HOST ALERT: test_host_0;DOWN;SOFT;2;Host is DOWN')])

        # Host goes DOWN / HARD
        self.check(host, 2, 'Host is DOWN',
                   [(u'error', u'HOST ALERT: test_host_0;DOWN;HARD;3;Host is DOWN')])

        # Host notification raised
        self.check(host, 2, 'Host is DOWN', [])

        self.check(host, 2, 'Host is DOWN', [])

        #  Host goes UP / HARD
        #  Get an host check, an alert and a notification
        self.check(host, 0, 'Host is UP',
                   [(u'info', u'HOST ALERT: test_host_0;UP;HARD;3;Host is UP')])

        self.check(host, 0, 'Host is UP', [])

        self.check(host, 0, 'Host is UP', [])

    def test_logs_services_disabled(self):
        """ Test disabled logs for active / passive checks for services

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_monitoring_logs_disabled.cfg')
        assert self.conf_is_correct

        self._sched = self.schedulers['scheduler-master'].sched

        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        # Make notifications sent very quickly
        svc.notification_interval = 10.0
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        #  Get sure that host is UP
        self.check(host, 0, 'Host is UP', [])

        # Service is ok
        self.check(svc, 0, 'Service is OK', [])
        self.check(svc, 0, 'Service is OK', [])

        #  Service goes warning / SOFT
        self.check(svc, 1, 'Service is WARNING',
                   [(u'warning',
                     u'SERVICE ALERT: test_host_0;test_ok_0;WARNING;SOFT;1;Service is WARNING')])

        #  Service goes warning / HARD
        # Get a service check, an alert and a notification
        self.check(svc, 1, 'Service is WARNING',
                   [(u'warning',
                     u'SERVICE ALERT: test_host_0;test_ok_0;WARNING;HARD;2;Service is WARNING')])

        # Service notification raised
        self.check(svc, 1, 'Service is WARNING', [])

        self.check(svc, 1, 'Service is WARNING', [])

        # Service goes OK
        self.check(svc, 0, 'Service is OK',
                   [(u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;HARD;2;Service is OK')])

        self.check(svc, 0, 'Service is OK', [])

        # Service goes CRITICAL
        self.check(svc, 2, 'Service is CRITICAL',
                   [(u'error',
                     u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Service is CRITICAL')])

        self.check(svc, 2, 'Service is CRITICAL',
                   [(u'error',
                     u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;HARD;2;Service is CRITICAL')])

        # Service goes OK
        self.check(svc, 0, 'Service is OK',
                   [(u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;HARD;2;Service is OK')])

        self.check(svc, 0, 'Service OK', [])

    def test_external_commands(self):
        """ Test logs for external commands

        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_monitoring_logs.cfg')
        assert self.conf_is_correct

        self._sched = self.schedulers['scheduler-master'].sched

        now = int(time.time())

        host = self._sched.hosts.find_by_name("test_host_0")

        # Receiver receives unknown host external command
        excmd = '[%d] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;1' % time.time()
        self._sched.run_external_command(excmd)
        self.external_command_loop()

        excmd = '[%d] CHANGE_RETRY_HOST_CHECK_INTERVAL;test_host_0;42' % now
        self._sched.run_external_command(excmd)
        self.external_command_loop()

        monitoring_logs = []
        for brok in self._sched.brokers['broker-master']['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        expected_logs = [
            (u'info',
             u'EXTERNAL COMMAND: [%s] CHANGE_RETRY_HOST_CHECK_INTERVAL;test_host_0;42' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;1' % now)
        ]
        for log_level, log_message in expected_logs:
            assert (log_level, log_message) in monitoring_logs

    def test_passive_checks_host(self):
        """ Test logs for external commands - passive host checks

        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_monitoring_logs.cfg')
        assert self.conf_is_correct

        self._sched = self.schedulers['scheduler-master'].sched

        # -----------------------------
        # Host part
        # -----------------------------
        # Get and configure host
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router which we depend of
        host.event_handler_enabled = False
        assert host is not None

        now = int(time.time())

        # Receive passive host check Down
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % now
        self._sched.run_external_command(excmd)
        self.external_command_loop()
        assert 'DOWN' == host.state
        assert 'SOFT' == host.state_type
        assert 'Host is dead' == host.output
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % now
        self._sched.run_external_command(excmd)
        self.external_command_loop()
        assert 'DOWN' == host.state
        assert 'SOFT' == host.state_type
        assert 'Host is dead' == host.output
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % now
        self._sched.run_external_command(excmd)
        self.external_command_loop()
        assert 'DOWN' == host.state
        assert 'HARD' == host.state_type
        assert 'Host is dead' == host.output

        # Extract monitoring logs
        monitoring_logs = []
        for brok in self._sched.brokers['broker-master']['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))
                print("Log (unicode: %s): %s" % (isinstance(data['message'], unicode), data['message']))

        # Passive host check log contains:
        # - host name,
        # - host status,
        # - output,
        # - performance data and
        # - long output
        # All are separated with a semi-colon
        expected_logs = [
            (u'info',
             u'EXTERNAL COMMAND: [%s] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % now),
            (u'warning',
             u'PASSIVE HOST CHECK: test_host_0;2;Host is dead;;'),
            (u'warning',
             u'PASSIVE HOST CHECK: test_host_0;2;Host is dead;;'),
            (u'warning',
             u'PASSIVE HOST CHECK: test_host_0;2;Host is dead;;'),
            (u'error',
             u'HOST ALERT: test_host_0;DOWN;SOFT;1;Host is dead'),
            (u'error',
             u'HOST ALERT: test_host_0;DOWN;SOFT;2;Host is dead'),
            (u'error',
             u'HOST ALERT: test_host_0;DOWN;HARD;3;Host is dead'),
            (u'error',
             u'HOST NOTIFICATION: test_contact;test_host_0;DOWN;notify-host;Host is dead')
        ]
        for log_level, log_message in expected_logs:
            print("Msg: %s" % log_message)
            assert (log_level, log_message) in monitoring_logs

    def test_passive_checks_service(self):
        """ Test logs for external commands - passive service checks

        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_monitoring_logs.cfg')
        assert self.conf_is_correct

        self._sched = self.schedulers['scheduler-master'].sched

        now = int(time.time())

        # -----------------------------
        # Service part
        # -----------------------------
        # Get host
        host = self._sched.hosts.find_by_name('test_host_0')
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.active_checks_enabled = True
        host.passive_checks_enabled = True
        assert host is not None

        # Get service
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.event_handler_enabled = False
        svc.active_checks_enabled = True
        svc.passive_checks_enabled = True
        assert svc is not None

        # Passive checks for host and service
        # ---------------------------------------------
        # Receive passive host check Up
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is UP' % time.time()
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()
        assert 'UP' == host.state
        assert 'Host is UP' == host.output

        # Service is going ok ...
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;0;' \
                'Service is OK|rtt=9999;5;10;0;10000' % now
        self._sched.run_external_command(excmd)
        self.external_command_loop()
        assert 'OK' == svc.state
        assert 'Service is OK' == svc.output
        assert 'rtt=9999;5;10;0;10000' == svc.perf_data

        # Service is going ok ... with long output
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;0;' \
                'Service is OK and have some special characters: àéèüäï' \
                '|rtt=9999;5;10;0;10000' \
                '\r\nLong output... also some specials: àéèüäï' % now
        self._sched.run_external_command(excmd)
        self.external_command_loop()
        assert 'OK' == svc.state
        assert u'Service is OK and have some special characters: àéèüäï' == svc.output
        assert 'rtt=9999;5;10;0;10000' == svc.perf_data
        assert u'Long output... also some specials: àéèüäï' == svc.long_output

        # Extract monitoring logs
        monitoring_logs = []
        for brok in self._sched.brokers['broker-master']['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))
                print("Log (unicode: %s): %s" % (isinstance(data['message'], unicode), data['message']))

        # Passive service check log contains:
        # - host name,
        # - host status,
        # - output,
        # - performance data and
        # - long output
        # All are separated with a semi-colon
        expected_logs = [
            (u'info',
             u'EXTERNAL COMMAND: [%s] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;0;'
             u'Service is OK|rtt=9999;5;10;0;10000' % now),
            (u'info',
             u'PASSIVE SERVICE CHECK: test_host_0;test_ok_0;0;Service is OK;;rtt=9999;5;10;0;10000'),

            (u'info',
             u'EXTERNAL COMMAND: [%s] PROCESS_SERVICE_CHECK_RESULT;test_host_0;test_ok_0;0;'
             u'Service is OK and have some special characters: àéèüäï'
             u'|rtt=9999;5;10;0;10000'
             u'\r\nLong output... also some specials: àéèüäï' % now),
            (u'info',
             u'PASSIVE SERVICE CHECK: test_host_0;test_ok_0;0;'
             u'Service is OK and have some special characters: àéèüäï;'
             u'Long output... also some specials: àéèüäï;'
             u'rtt=9999;5;10;0;10000')
        ]
        for log_level, log_message in expected_logs:
            print("Msg: %s" % log_message)
            assert (log_level, log_message) in monitoring_logs

    def test_special_external_commands(self):
        """ Test logs for special external commands
        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_monitoring_logs.cfg')
        assert self.conf_is_correct

        self._sched = self.schedulers['scheduler-master'].sched

        now = int(time.time())

        # RESTART_PROGRAM
        excmd = '[%d] RESTART_PROGRAM' % now
        self._sched.run_external_command(excmd)
        self.external_command_loop()
        self.assert_any_log_match('RESTART command : libexec/sleep_command.sh 3')

        # RELOAD_CONFIG
        excmd = '[%d] RELOAD_CONFIG' % now
        self._sched.run_external_command(excmd)
        self.external_command_loop()
        self.assert_any_log_match('RELOAD command : libexec/sleep_command.sh 2')

        # UNKNOWN COMMAND
        excmd = '[%d] UNKNOWN_COMMAND' % now
        self._sched.run_external_command(excmd)
        self.external_command_loop()
        # Malformed command
        excmd = '[%d] MALFORMED COMMAND' % now
        self._sched.run_external_command(excmd)
        self.external_command_loop()

        monitoring_logs = []
        for brok in self._sched.brokers['broker-master']['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        # The messages are echoed by the launched scripts
        expected_logs = [
            (u'info', u'I awoke after sleeping 3 seconds | sleep=3\n'),
            (u'info', u'I awoke after sleeping 2 seconds | sleep=2\n'),
            (u'error', u"Malformed command: '[%s] MALFORMED COMMAND'" % now),
            (u'error', u"Command '[%s] UNKNOWN_COMMAND' is not recognized, sorry" % now)
        ]
        for log_level, log_message in expected_logs:
            assert (log_level, log_message) in monitoring_logs

        # Now with disabled log of external commands
        self.setup_with_file('cfg/cfg_monitoring_logs_disabled.cfg')
        assert self.conf_is_correct

        self._sched = self.schedulers['scheduler-master'].sched

        # RESTART_PROGRAM
        excmd = '[%d] RESTART_PROGRAM' % int(time.time())
        self._sched.run_external_command(excmd)
        self.external_command_loop()
        self.assert_any_log_match('RESTART command : libexec/sleep_command.sh 3')

        # RELOAD_CONFIG
        excmd = '[%d] RELOAD_CONFIG' % int(time.time())
        self._sched.run_external_command(excmd)
        self.external_command_loop()
        self.assert_any_log_match('RELOAD command : libexec/sleep_command.sh 2')

        monitoring_logs = []
        for brok in self._sched.brokers['broker-master']['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        # No monitoring logs
        assert [] == monitoring_logs

    def test_timeperiod_transition_log(self):
        self.setup_with_file('cfg/cfg_default.cfg')
        self._sched = self.schedulers['scheduler-master'].sched

        tp = self._sched.timeperiods.find_by_name('24x7')

        self.assertIsNot(tp, None)

        data = unserialize(tp.check_and_log_activation_change().data)
        assert data['level'] == 'info'
        assert data['message'] == 'TIMEPERIOD TRANSITION: 24x7;-1;1'

        # Now make this tp unable to be active again by removing al it's daterange
        dr = tp.dateranges
        tp.dateranges = []
        data = unserialize(tp.check_and_log_activation_change().data)
        assert data['level'] == 'info'
        assert data['message'] == 'TIMEPERIOD TRANSITION: 24x7;1;0'

        # Ok, let get back to work
        tp.dateranges = dr
        data = unserialize(tp.check_and_log_activation_change().data)
        assert data['level'] == 'info'
        assert data['message'] == 'TIMEPERIOD TRANSITION: 24x7;0;1'