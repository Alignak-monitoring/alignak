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

"""
This file test the StatsD interface
"""

import re
import socket
import threading

from alignak.brok import Brok

from alignak.stats import *

from alignak_test import AlignakTest


class FakeStatsdServer(threading.Thread):
    def __init__(self, port=0):
        super(FakeStatsdServer, self).__init__()
        self.setDaemon(True)
        self.port = port
        self.cli_socks = []  # will retain the client socks here
        sock = self.sock = socket.socket()
        sock.settimeout(1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', port))
        if not port:
            self.port = sock.getsockname()[1]
        sock.listen(0)
        self.running = True
        self.start()

    def stop(self):
        self.running = False
        self.sock.close()

    def run(self):
        while self.running:
            try:
                sock, addr = self.sock.accept()
            except socket.error as err:
                pass
            else:
                # so that we won't block indefinitely in handle_connection
                # in case the client doesn't send anything :
                sock.settimeout(3)
                self.cli_socks.append(sock)
                self.handle_connection(sock)
                self.cli_socks.remove(sock)

    def handle_connection(self, sock):
        data = sock.recv(4096)
        print("Received: %s", data)
        sock.close()


class TestStats(AlignakTest):
    """
    This class test the StatsD interface
    """

    def setUp(self):
        # Create our own stats manager...
        # do not use the global object to restart with a fresh one on each test
        self.statsmgr = Stats()
        self.fake_server = FakeStatsdServer(port=8125)

    def tearDown(self):
        self.fake_server.stop()
        self.fake_server.join()

    def test_statsmgr(self):
        """ Stats manager exists
        :return:
        """
        self.print_header()
        assert 'statsmgr' in globals()

    def test_statsmgr_register_disabled(self):
        """ Stats manager is registered as disabled
        :return:
        """
        self.print_header()

        # Setup a logger...
        self.setup_logger()
        self.clear_logs()

        # Register stats manager as disabled
        assert not self.statsmgr.register('arbiter-master', 'arbiter',
                                          statsd_host='localhost', statsd_port=8125,
                                          statsd_prefix='alignak', statsd_enabled=False)
        assert self.statsmgr.statsd_enabled is False
        assert self.statsmgr.broks_enabled is False
        assert self.statsmgr.statsd_sock is None
        assert self.statsmgr.statsd_addr is None
        self.assert_log_match(re.escape(
            'INFO: [alignak.stats] Alignak internal statistics are disabled.'
        ), 0)

    def test_statsmgr_register_disabled_broks(self):
        """ Stats manager is registered as disabled, but broks are enabled
        :return:
        """
        self.print_header()

        # Setup a logger...
        self.setup_logger()
        self.clear_logs()

        # Register stats manager as disabled
        assert not self.statsmgr.register('arbiter-master', 'arbiter',
                                          statsd_host='localhost', statsd_port=8125,
                                          statsd_prefix='alignak', statsd_enabled=False,
                                          broks_enabled=True)
        assert self.statsmgr.statsd_enabled is False
        assert self.statsmgr.broks_enabled is True
        assert self.statsmgr.statsd_sock is None
        assert self.statsmgr.statsd_addr is None
        self.assert_log_match(re.escape(
            'INFO: [alignak.stats] Alignak internal statistics are disabled.'
        ), 0)

    def test_statsmgr_register_enabled(self):
        """ Stats manager is registered as enabled
        :return:
        """
        self.print_header()

        # Setup a logger...
        self.setup_logger()
        self.clear_logs()

        # Register stats manager as enabled
        assert self.statsmgr.statsd_sock is None
        assert self.statsmgr.statsd_addr is None
        assert self.statsmgr.register('arbiter-master', 'arbiter',
                                          statsd_host='localhost', statsd_port=8125,
                                          statsd_prefix='alignak', statsd_enabled=True)
        assert self.statsmgr.statsd_enabled is True
        assert self.statsmgr.broks_enabled is False
        assert self.statsmgr.statsd_sock is not None
        assert self.statsmgr.statsd_addr is not None
        self.assert_log_match(re.escape(
            'INFO: [alignak.stats] Sending arbiter/arbiter-master daemon statistics '
            'to: localhost:8125, prefix: alignak'
        ), 0)
        self.assert_log_match(re.escape(
            'INFO: [alignak.stats] Trying to contact StatsD server...'
        ), 1)
        self.assert_log_match(re.escape(
            'INFO: [alignak.stats] StatsD server contacted'
        ), 2)

    def test_statsmgr_register_enabled_broks(self):
        """ Stats manager is registered as enabled and broks are enabled
        :return:
        """
        self.print_header()

        # Setup a logger...
        self.setup_logger()
        self.clear_logs()

        # Register stats manager as enabled
        assert self.statsmgr.statsd_sock is None
        assert self.statsmgr.statsd_addr is None
        assert self.statsmgr.register('arbiter-master', 'arbiter',
                                      statsd_host='localhost', statsd_port=8125,
                                      statsd_prefix='alignak', statsd_enabled=True,
                                      broks_enabled=True)
        assert self.statsmgr.statsd_enabled is True
        assert self.statsmgr.broks_enabled is True
        assert self.statsmgr.statsd_sock is not None
        assert self.statsmgr.statsd_addr is not None
        self.assert_log_match(re.escape(
            'INFO: [alignak.stats] Sending arbiter/arbiter-master daemon statistics '
            'to: localhost:8125, prefix: alignak'
        ), 0)
        self.assert_log_match(re.escape(
            'INFO: [alignak.stats] Trying to contact StatsD server...'
        ), 1)
        self.assert_log_match(re.escape(
            'INFO: [alignak.stats] StatsD server contacted'
        ), 2)

    def test_statsmgr_connect(self):
        """ Test connection in disabled mode
        :return:
        """
        self.print_header()

        # Setup a logger...
        self.setup_logger()
        self.clear_logs()

        # Register stats manager as disabled
        assert not self.statsmgr.register('arbiter-master', 'arbiter',
                                           statsd_host='localhost', statsd_port=8125,
                                           statsd_prefix='alignak', statsd_enabled=False)
        self.assert_log_match(re.escape(
            'INFO: [alignak.stats] Alignak internal statistics are disabled.'
        ), 0)

        # Connect to StatsD server
        assert self.statsmgr.statsd_sock is None
        assert self.statsmgr.statsd_addr is None
        # This method is not usually called directly, but it must refuse the connection
        # if it not enabled
        assert not self.statsmgr.load_statsd()
        assert self.statsmgr.statsd_sock is None
        assert self.statsmgr.statsd_addr is None
        self.assert_log_match(re.escape(
            'WARNING: [alignak.stats] StatsD is not enabled, connection is not allowed'
        ), 1)

    def test_statsmgr_connect_port_error(self):
        """ Test connection with a bad port
        :return:
        """
        self.print_header()

        # Setup a logger...
        self.setup_logger()
        self.clear_logs()

        # Register stats manager as enabled (another port than the default one)
        assert self.statsmgr.register('arbiter-master', 'arbiter',
                                          statsd_host='localhost', statsd_port=8888,
                                          statsd_prefix='alignak', statsd_enabled=True)
        self.assert_log_match(re.escape(
            'INFO: [alignak.stats] Sending arbiter/arbiter-master daemon statistics '
            'to: localhost:8888, prefix: alignak'
        ), 0)
        self.assert_log_match(re.escape(
            'INFO: [alignak.stats] Trying to contact StatsD server...'
        ), 1)
        self.assert_log_match(re.escape(
            'INFO: [alignak.stats] StatsD server contacted'
        ), 2)

        # "Connected" to StatsD server - even with a bad port number!
        self.assert_no_log_match('Cannot create StatsD socket')

    def test_statsmgr_timer(self):
        """ Test sending data for a timer
        :return:
        """
        self.print_header()

        # Setup a logger...
        self.setup_logger()
        self.clear_logs()

        # Register stats manager as enabled
        self.statsmgr.register('arbiter-master', 'arbiter',
                               statsd_host='localhost', statsd_port=8125,
                               statsd_prefix='alignak', statsd_enabled=True,
                               broks_enabled=True)

        assert self.statsmgr.stats == {}

        # Create a metric statistic
        brok = self.statsmgr.timer('test', 0)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count and sum
        assert self.statsmgr.stats['test'] == (0, 0, 1, 0)
        # self.assert_log_match(re.escape(
        #     'INFO: [alignak.stats] Sending data: alignak.arbiter-master.test:0|ms'
        # ), 3)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        assert brok.__dict__ == {'type': 'alignak_stat',
                                 'data': {
                                     'type': 'timer',
                                     'metric': 'alignak.arbiter-master.test',
                                     'value': 0, 'uom': 'ms'
                                 }}

        # Increment
        brok = self.statsmgr.timer('test', 1)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count (incremented) and sum
        assert self.statsmgr.stats['test'] == (0, 1, 2, 1)
        # self.assert_log_match(re.escape(
        #     'INFO: [alignak.stats] Sending data: alignak.arbiter-master.test:1000|ms'
        # ), 4)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        assert brok.__dict__ == {'type': 'alignak_stat',
                                 'data': {
                                     'type': 'timer',
                                     'metric': 'alignak.arbiter-master.test',
                                     'value': 1000, 'uom': 'ms'
                                 }}

        # Increment - the function is called 'incr' but it does not increment, it sets the value!
        brok = self.statsmgr.timer('test', 12)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count (incremented) and sum (increased)
        assert self.statsmgr.stats['test'] == (0, 12, 3, 13)
        # self.assert_log_match(re.escape(
        #     'INFO: [alignak.stats] Sending data: alignak.arbiter-master.test:1000|ms'
        # ), 5)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        assert brok.__dict__ == {'type': 'alignak_stat',
                                 'data': {
                                     'type': 'timer',
                                     'metric': 'alignak.arbiter-master.test',
                                     'value': 12000, 'uom': 'ms'
                                 }}

    def test_statsmgr_counter(self):
        """ Test sending data for a counter
        :return:
        """
        self.print_header()

        # Setup a logger...
        self.setup_logger()
        self.clear_logs()

        # Register stats manager as enabled
        self.statsmgr.register('arbiter-master', 'arbiter',
                               statsd_host='localhost', statsd_port=8125,
                               statsd_prefix='alignak', statsd_enabled=True,
                               broks_enabled=True)

        assert self.statsmgr.stats == {}

        # Create a metric statistic
        brok = self.statsmgr.counter('test', 0)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count and sum
        assert self.statsmgr.stats['test'] == (0, 0, 1, 0)
        # self.assert_log_match(re.escape(
        #     'INFO: [alignak.stats] Sending data: alignak.arbiter-master.test:0|ms'
        # ), 3)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        assert brok.__dict__ == {'type': 'alignak_stat',
                                 'data': {
                                     'type': 'counter',
                                     'metric': 'alignak.arbiter-master.test',
                                     'value': 0, 'uom': 'c'
                                 }}

        # Increment
        brok = self.statsmgr.counter('test', 1)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count (incremented) and sum
        assert self.statsmgr.stats['test'] == (0, 1, 2, 1)
        # self.assert_log_match(re.escape(
        #     'INFO: [alignak.stats] Sending data: alignak.arbiter-master.test:1000|ms'
        # ), 4)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        assert brok.__dict__ == {'type': 'alignak_stat',
                                 'data': {
                                     'type': 'counter',
                                     'metric': 'alignak.arbiter-master.test',
                                     'value': 1, 'uom': 'c'
                                 }}

        # Increment - the function is called 'incr' but it does not increment, it sets the value!
        brok = self.statsmgr.counter('test', 12)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count (incremented) and sum (increased)
        assert self.statsmgr.stats['test'] == (0, 12, 3, 13)
        # self.assert_log_match(re.escape(
        #     'INFO: [alignak.stats] Sending data: alignak.arbiter-master.test:1000|ms'
        # ), 5)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        assert brok.__dict__ == {'type': 'alignak_stat',
                                 'data': {
                                     'type': 'counter',
                                     'metric': 'alignak.arbiter-master.test',
                                     'value': 12, 'uom': 'c'
                                 }}

    def test_statsmgr_gauge(self):
        """ Test sending data for a gauge
        :return:
        """
        self.print_header()

        # Setup a logger...
        self.setup_logger()
        self.clear_logs()

        # Register stats manager as enabled
        self.statsmgr.register('arbiter-master', 'arbiter',
                               statsd_host='localhost', statsd_port=8125,
                               statsd_prefix='alignak', statsd_enabled=True,
                               broks_enabled=True)

        assert self.statsmgr.stats == {}

        # Create a metric statistic
        brok = self.statsmgr.gauge('test', 0)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count and sum
        assert self.statsmgr.stats['test'] == (0, 0, 1, 0)
        # self.assert_log_match(re.escape(
        #     'INFO: [alignak.stats] Sending data: alignak.arbiter-master.test:0|ms'
        # ), 3)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        assert brok.__dict__ == {'type': 'alignak_stat',
                                 'data': {
                                     'type': 'gauge',
                                     'metric': 'alignak.arbiter-master.test',
                                     'value': 0, 'uom': 'g'
                                 }}

        # Increment
        brok = self.statsmgr.gauge('test', 1)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count (incremented) and sum
        assert self.statsmgr.stats['test'] == (0, 1, 2, 1)
        # self.assert_log_match(re.escape(
        #     'INFO: [alignak.stats] Sending data: alignak.arbiter-master.test:1000|ms'
        # ), 4)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        assert brok.__dict__ == {'type': 'alignak_stat',
                                 'data': {
                                     'type': 'gauge',
                                     'metric': 'alignak.arbiter-master.test',
                                     'value': 1, 'uom': 'g'
                                 }}

        # Increment - the function is called 'incr' but it does not increment, it sets the value!
        brok = self.statsmgr.gauge('test', 12)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count (incremented) and sum (increased)
        assert self.statsmgr.stats['test'] == (0, 12, 3, 13)
        # self.assert_log_match(re.escape(
        #     'INFO: [alignak.stats] Sending data: alignak.arbiter-master.test:1000|ms'
        # ), 5)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        assert brok.__dict__ == {'type': 'alignak_stat',
                                 'data': {
                                     'type': 'gauge',
                                     'metric': 'alignak.arbiter-master.test',
                                     'value': 12, 'uom': 'g'
                                 }}
