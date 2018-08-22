#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2018: Alignak team, see AUTHORS.txt file for contributors
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
import logging

from alignak.brok import Brok

from alignak.stats import *

from .alignak_test import AlignakTest


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
        print("Starting fake StatsD server on %d" % port)
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
        print(("Fake StatsD received: %s", data))
        sock.close()


class FakeCarbonServer(threading.Thread):
    def __init__(self, port=0):
        super(FakeCarbonServer, self).__init__()
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
        print("Starting fake carbon server on %d" % port)
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
        print(("Fake carbon received: %s", data))
        sock.close()


class TestStatsD(AlignakTest):
    """
    This class test the StatsD interface
    """
    def setUp(self):
        super(TestStatsD, self).setUp()

        # Log at DEBUG level
        self.set_unit_tests_logger_level('INFO')
        self.show_logs()
        self.clear_logs()

        # Create our own stats manager...
        # do not use the global object to restart with a fresh one on each test
        self.statsmgr = Stats()
        self.fake_statsd = FakeStatsdServer(port=8125)

    def tearDown(self):
        self.fake_statsd.stop()
        self.fake_statsd.join()

    def test_statsmgr(self):
        """ Stats manager exists
        :return:
        """
        assert 'statsmgr' in globals()

    def test_statsmgr_register_disabled(self):
        """ Stats manager is registered as disabled
        :return:
        """
        # Register stats manager as disabled
        assert not self.statsmgr.register('arbiter-master', 'arbiter',
                                          statsd_host='localhost', statsd_port=8125,
                                          statsd_prefix='alignak', statsd_enabled=False)
        assert self.statsmgr.statsd_enabled is False
        assert self.statsmgr.broks_enabled is False
        assert self.statsmgr.statsd_sock is None

    def test_statsmgr_register_disabled_broks(self):
        """ Stats manager is registered as disabled, but broks are enabled
        :return:
        """
        # Register stats manager as disabled
        assert not self.statsmgr.register('arbiter-master', 'arbiter',
                                          statsd_host='localhost', statsd_port=8125,
                                          statsd_prefix='alignak', statsd_enabled=False,
                                          broks_enabled=True)
        assert self.statsmgr.statsd_enabled is False
        assert self.statsmgr.broks_enabled is True
        assert self.statsmgr.statsd_sock is None
        assert self.statsmgr.statsd_addr is None

    def test_statsmgr_register_enabled(self):
        """ Stats manager is registered as enabled
        :return:
        """
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

        index = 0
        self.assert_log_match(re.escape(
            'Sending arbiter-master statistics to: localhost:8125, prefix: alignak'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Trying to contact StatsD server...'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'StatsD server contacted'
        ), index)
        index += 1

    def test_statsmgr_register_enabled_broks(self):
        """ Stats manager is registered as enabled and broks are enabled
        :return:
        """
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

        index = 0
        self.assert_log_match(re.escape(
            'Sending arbiter-master statistics to: localhost:8125, prefix: alignak'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Trying to contact StatsD server...'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'StatsD server contacted'
        ), index)
        index += 1

    def test_statsmgr_connect(self):
        """ Test connection in disabled mode
        :return:
        """
        # Register stats manager as disabled
        assert not self.statsmgr.register('arbiter-master', 'arbiter',
                                           statsd_host='localhost', statsd_port=8125,
                                           statsd_prefix='alignak', statsd_enabled=False)

        # Connect to StatsD server
        assert self.statsmgr.statsd_sock is None
        assert self.statsmgr.statsd_addr is None
        # This method is not usually called directly, but it must refuse the connection
        # if it not enabled
        assert not self.statsmgr.load_statsd()
        assert self.statsmgr.statsd_sock is None
        assert self.statsmgr.statsd_addr is None

    def test_statsmgr_connect_port_error(self):
        """ Test connection with a bad port
        :return:
        """
        # Register stats manager as enabled (another port than the default one)
        assert self.statsmgr.register('arbiter-master', 'arbiter',
                                          statsd_host='localhost', statsd_port=8888,
                                          statsd_prefix='alignak', statsd_enabled=True)
        index = 0
        self.assert_log_match(re.escape(
            'Sending arbiter-master statistics to: localhost:8888, prefix: alignak'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Trying to contact StatsD server...'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'StatsD server contacted'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Alignak internal statistics are sent to StatsD.'
        ), index)
        index += 1

        # "Connected" to StatsD server - even with a bad port number!
        self.assert_no_log_match('Cannot create StatsD socket')

    def test_statsmgr_timer(self):
        """ Test sending data for a timer
        :return:
        """
        # Register stats manager as enabled
        self.statsmgr.register('arbiter-master', 'arbiter',
                               statsd_host='localhost', statsd_port=8125,
                               statsd_prefix='alignak', statsd_enabled=True,
                               broks_enabled=True)
        index = 0
        # # Only for Python > 2.7, DEBUG logs ...
        # if os.sys.version_info > (2, 7):
        #     index = 1
        self.show_logs()
        self.assert_log_match(re.escape(
            'Sending arbiter-master statistics to: localhost:8125, prefix: alignak'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Trying to contact StatsD server...'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'StatsD server contacted'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Alignak internal statistics are sent to StatsD.'
        ), index)
        index += 1

        assert self.statsmgr.stats == {}

        # Create a metric statistic
        brok = self.statsmgr.timer('test', 0)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count and sum
        assert self.statsmgr.stats['test'] == (0, 0, 1, 0)
        # self.assert_log_match(re.escape(
        #     'Sending data: alignak.arbiter-master.test:0|ms'
        # ), 3)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        brok.__dict__['data'].pop('ts')
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
        #     'Sending data: alignak.arbiter-master.test:1000|ms'
        # ), 4)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        brok.__dict__['data'].pop('ts')
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
        #     'Sending data: alignak.arbiter-master.test:1000|ms'
        # ), 5)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        brok.__dict__['data'].pop('ts')
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
        # Register stats manager as enabled
        self.statsmgr.register('broker-master', 'broker',
                               statsd_host='localhost', statsd_port=8125,
                               statsd_prefix='alignak', statsd_enabled=True,
                               broks_enabled=True)
        index = 0
        # # Only for Python > 2.7, DEBUG logs ...
        # if os.sys.version_info > (2, 7):
        #     index = 1
        self.show_logs()
        self.assert_log_match(re.escape(
            'Sending broker-master statistics to: localhost:8125, prefix: alignak'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Trying to contact StatsD server...'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'StatsD server contacted'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Alignak internal statistics are sent to StatsD.'
        ), index)
        index += 1

        assert self.statsmgr.stats == {}

        # Create a metric statistic
        brok = self.statsmgr.counter('test', 0)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count and sum
        assert self.statsmgr.stats['test'] == (0, 0, 1, 0)
        # self.assert_log_match(re.escape(
        #     'Sending data: alignak.arbiter-master.test:0|ms'
        # ), 3)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        brok.__dict__['data'].pop('ts')
        assert brok.__dict__ == {'type': 'alignak_stat',
                                 'data': {
                                     'type': 'counter',
                                     'metric': 'alignak.broker-master.test',
                                     'value': 0, 'uom': 'c'
                                 }}

        # Increment
        brok = self.statsmgr.counter('test', 1)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count (incremented) and sum
        assert self.statsmgr.stats['test'] == (0, 1, 2, 1)
        # self.assert_log_match(re.escape(
        #     'Sending data: alignak.arbiter-master.test:1000|ms'
        # ), 4)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        brok.__dict__['data'].pop('ts')
        assert brok.__dict__ == {'type': 'alignak_stat',
                                 'data': {
                                     'type': 'counter',
                                     'metric': 'alignak.broker-master.test',
                                     'value': 1, 'uom': 'c'
                                 }}

        # Increment - the function is called 'incr' but it does not increment, it sets the value!
        brok = self.statsmgr.counter('test', 12)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count (incremented) and sum (increased)
        assert self.statsmgr.stats['test'] == (0, 12, 3, 13)
        # self.assert_log_match(re.escape(
        #     'Sending data: alignak.arbiter-master.test:1000|ms'
        # ), 5)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        brok.__dict__['data'].pop('ts')
        assert brok.__dict__ == {'type': 'alignak_stat',
                                 'data': {
                                     'type': 'counter',
                                     'metric': 'alignak.broker-master.test',
                                     'value': 12, 'uom': 'c'
                                 }}

    def test_statsmgr_gauge(self):
        """ Test sending data for a gauge
        :return:
        """
        # Register stats manager as enabled
        self.statsmgr.register('arbiter-master', 'arbiter',
                               statsd_host='localhost', statsd_port=8125,
                               statsd_prefix='alignak', statsd_enabled=True,
                               broks_enabled=True)
        index = 0
        # # Only for Python > 2.7, DEBUG logs ...
        # if os.sys.version_info > (2, 7):
        #     index = 1
        self.show_logs()
        self.assert_log_match(re.escape(
            'Sending arbiter-master statistics to: localhost:8125, prefix: alignak'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Trying to contact StatsD server...'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'StatsD server contacted'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Alignak internal statistics are sent to StatsD.'
        ), index)
        index += 1

        assert self.statsmgr.stats == {}

        # Create a metric statistic
        brok = self.statsmgr.gauge('test', 0)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count and sum
        assert self.statsmgr.stats['test'] == (0, 0, 1, 0)
        # self.assert_log_match(re.escape(
        #     'Sending data: alignak.arbiter-master.test:0|ms'
        # ), 3)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        brok.__dict__['data'].pop('ts')
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
        #     'Sending data: alignak.arbiter-master.test:1000|ms'
        # ), 4)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        brok.__dict__['data'].pop('ts')
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
        #     'Sending data: alignak.arbiter-master.test:1000|ms'
        # ), 5)
        # Prepare brok and remove specific brok properties (for test purpose only...
        brok.prepare()
        brok.__dict__.pop('creation_time')
        brok.__dict__.pop('instance_id')
        brok.__dict__.pop('prepared')
        brok.__dict__.pop('uuid')
        brok.__dict__['data'].pop('ts')
        assert brok.__dict__ == {'type': 'alignak_stat',
                                 'data': {
                                     'type': 'gauge',
                                     'metric': 'alignak.arbiter-master.test',
                                     'value': 12, 'uom': 'g'
                                 }}


if os.sys.version_info > (2, 7):
    class TestCarbon(AlignakTest):
        """
        This class test the Graphite interface
        """
        def setUp(self):
            super(TestCarbon, self).setUp()

            # Log at DEBUG level
            self.set_unit_tests_logger_level()
            self.clear_logs()

            # Create our own stats manager...
            # do not use the global object to restart with a fresh one on each test
            self.statsmgr = Stats()
            self.fake_carbon = FakeCarbonServer(port=2003)

        def tearDown(self):
            self.fake_carbon.stop()
            self.fake_carbon.join()

        def test_statsmgr(self):
            """ Stats manager exists
            :return:
            """
            assert 'statsmgr' in globals()

        def test_statsmgr_register_disabled(self):
            """ Stats manager is registered as disabled
            :return:
            """
            # Register stats manager as disabled
            assert not self.statsmgr.connect('arbiter-master', 'arbiter',
                                             host='localhost', port=2003,
                                             prefix='alignak', enabled=False)
            assert self.statsmgr.statsd_enabled is False
            assert self.statsmgr.broks_enabled is False
            assert self.statsmgr.statsd_sock is None
            assert self.statsmgr.metrics_count == 0

        def test_statsmgr_register_disabled_broks(self):
            """ Stats manager is registered as disabled, but broks are enabled
            :return:
            """
            # Register stats manager as disabled
            assert not self.statsmgr.connect('arbiter-master', 'arbiter',
                                             host='localhost', port=2003,
                                             prefix='alignak', enabled=False,
                                             broks_enabled=True)
            assert self.statsmgr.statsd_enabled is False
            assert self.statsmgr.broks_enabled is True
            assert self.statsmgr.statsd_sock is None
            assert self.statsmgr.statsd_addr is None
            assert self.statsmgr.metrics_count == 0

        def test_statsmgr_register_enabled(self):
            """ Stats manager is registered as enabled
            :return:
            """
            # Register stats manager as enabled
            assert self.statsmgr.statsd_sock is None
            assert self.statsmgr.statsd_addr is None
            assert self.statsmgr.connect('arbiter-master', 'arbiter',
                                         host='localhost', port=2003,
                                         prefix='alignak', enabled=True)
            assert self.statsmgr.statsd_enabled is True
            assert self.statsmgr.broks_enabled is False
            assert self.statsmgr.carbon is not None
            assert self.statsmgr.metrics_count == 0

            index = 0
            self.assert_log_match(re.escape(
                'Graphite/carbon configuration for arbiter-master - localhost:2003, '
                'prefix: alignak, enabled: True, broks: False, file: None'
            ), index)
            index += 1
            self.assert_log_match(re.escape(
                'Sending arbiter-master statistics to: localhost:2003, prefix: alignak'
            ), index)

        def test_statsmgr_register_enabled_broks(self):
            """ Stats manager is registered as enabled and broks are enabled
            :return:
            """
            # Register stats manager as enabled
            assert self.statsmgr.statsd_sock is None
            assert self.statsmgr.statsd_addr is None
            assert self.statsmgr.connect('arbiter-master', 'arbiter',
                                         host='localhost', port=2003, prefix='alignak', enabled=True,
                                         broks_enabled=True)
            assert self.statsmgr.statsd_enabled is True
            assert self.statsmgr.broks_enabled is True
            assert self.statsmgr.carbon is not None
            assert self.statsmgr.metrics_count == 0

            index = 0
            self.assert_log_match(re.escape(
                'Graphite/carbon configuration for arbiter-master - localhost:2003, '
                'prefix: alignak, enabled: True, broks: True, file: None'
            ), index)
            index += 1
            self.assert_log_match(re.escape(
                'Sending arbiter-master statistics to: localhost:2003, prefix: alignak'
            ), index)

        def test_statsmgr_connect(self):
            """ Test connection in disabled mode
            :return:
            """
            # Register stats manager as disabled
            assert not self.statsmgr.connect('arbiter-master', 'arbiter',
                                             host='localhost', port=2003,
                                             prefix='alignak', enabled=False)

            # Connect to StatsD server
            assert self.statsmgr.statsd_sock is None
            assert self.statsmgr.statsd_addr is None
            # This method is not usually called directly, but it must refuse the connection
            # if it not enabled
            assert not self.statsmgr.load_statsd()
            assert self.statsmgr.statsd_sock is None
            assert self.statsmgr.statsd_addr is None
            assert self.statsmgr.metrics_count == 0

        def test_statsmgr_connect_port_error(self):
            """ Test connection with a bad port
            :return:
            """
            # Register stats manager as enabled (another port than the default one)
            assert self.statsmgr.connect('arbiter-master', 'arbiter',
                                         host='localhost', port=8888,
                                         prefix='alignak', enabled=True)
            index = 0
            self.assert_log_match(re.escape(
                'Graphite/carbon configuration for arbiter-master - localhost:8888, '
                'prefix: alignak, enabled: True, broks: False, file: None'
            ), index)
            index += 1
            self.assert_log_match(re.escape(
                'Sending arbiter-master statistics to: localhost:8888, prefix: alignak'
            ), index)
            index += 1
            self.assert_log_match(re.escape(
                'Alignak internal statistics will be sent to Graphite.'
            ), index)
            index += 1

        def test_statsmgr_timer(self):
            """ Test sending data for a timer
            :return:
            """
            # Register stats manager as enabled
            self.statsmgr.connect('arbiter-master', 'arbiter',
                                  host='localhost', port=2003, prefix='alignak', enabled=True,
                                  broks_enabled=True)
            assert self.statsmgr.metrics_count == 0

            index = 0
            self.assert_log_match(re.escape(
                'Graphite/carbon configuration for arbiter-master - localhost:2003, '
                'prefix: alignak, enabled: True, broks: True, file: None'
            ), index)
            index += 1
            self.assert_log_match(re.escape(
                'Sending arbiter-master statistics to: localhost:2003, prefix: alignak'
            ), index)
            index += 1
            self.assert_log_match(re.escape(
                'Alignak internal statistics will be sent to Graphite.'
            ), index)
            index += 1

            assert self.statsmgr.stats == {}

            # Create a metric statistic
            brok = self.statsmgr.timer('test', 0)
            assert len(self.statsmgr.stats) == 1
            # One more inner metric
            assert self.statsmgr.metrics_count == 1

            # Get min, max, count and sum
            assert self.statsmgr.stats['test'] == (0, 0, 1, 0)
            # self.assert_log_match(re.escape(
            #     'Sending data: alignak.arbiter-master.test:0|ms'
            # ), 3)
            # Prepare brok and remove specific brok properties (for test purpose only...
            brok.prepare()
            brok.__dict__.pop('creation_time')
            brok.__dict__.pop('instance_id')
            brok.__dict__.pop('prepared')
            brok.__dict__.pop('uuid')
            brok.__dict__['data'].pop('ts')
            assert brok.__dict__ == {'type': 'alignak_stat',
                                     'data': {
                                         'type': 'timer',
                                         'metric': 'alignak.arbiter-master.test',
                                         'value': 0, 'uom': 'ms'
                                     }}

            # Increment
            brok = self.statsmgr.timer('test', 1)
            assert len(self.statsmgr.stats) == 1
            # One more inner metric
            assert self.statsmgr.metrics_count == 2

            # Get min, max, count (incremented) and sum
            assert self.statsmgr.stats['test'] == (0, 1, 2, 1)
            # self.assert_log_match(re.escape(
            #     'Sending data: alignak.arbiter-master.test:1000|ms'
            # ), 4)
            # Prepare brok and remove specific brok properties (for test purpose only...
            brok.prepare()
            brok.__dict__.pop('creation_time')
            brok.__dict__.pop('instance_id')
            brok.__dict__.pop('prepared')
            brok.__dict__.pop('uuid')
            brok.__dict__['data'].pop('ts')
            assert brok.__dict__ == {'type': 'alignak_stat',
                                     'data': {
                                         'type': 'timer',
                                         'metric': 'alignak.arbiter-master.test',
                                         'value': 1000, 'uom': 'ms'
                                     }}

            # Increment - the function is called 'incr' but it does not increment, it sets the value!
            brok = self.statsmgr.timer('test', 12)
            assert len(self.statsmgr.stats) == 1
            # One more inner metric
            assert self.statsmgr.metrics_count == 3

            # Get min, max, count (incremented) and sum (increased)
            assert self.statsmgr.stats['test'] == (0, 12, 3, 13)
            # self.assert_log_match(re.escape(
            #     'Sending data: alignak.arbiter-master.test:1000|ms'
            # ), 5)
            # Prepare brok and remove specific brok properties (for test purpose only...
            brok.prepare()
            brok.__dict__.pop('creation_time')
            brok.__dict__.pop('instance_id')
            brok.__dict__.pop('prepared')
            brok.__dict__.pop('uuid')
            brok.__dict__['data'].pop('ts')
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
            # Register stats manager as enabled
            self.statsmgr.connect('broker-master', 'broker',
                                  host='localhost', port=2003, prefix='alignak', enabled=True,
                                  broks_enabled=True)
            index = 0
            self.assert_log_match(re.escape(
                'Graphite/carbon configuration for broker-master - localhost:2003, '
                'prefix: alignak, enabled: True, broks: True, file: None'
            ), index)
            index += 1
            self.assert_log_match(re.escape(
                'Sending broker-master statistics to: localhost:2003, prefix: alignak'
            ), index)
            index += 1
            self.assert_log_match(re.escape(
                'Alignak internal statistics will be sent to Graphite.'
            ), index)
            index += 1

            assert self.statsmgr.stats == {}

            # Create a metric statistic
            brok = self.statsmgr.counter('test', 0)
            assert len(self.statsmgr.stats) == 1
            # One more inner metric
            assert self.statsmgr.metrics_count == 1

            # Get min, max, count and sum
            assert self.statsmgr.stats['test'] == (0, 0, 1, 0)
            # self.assert_log_match(re.escape(
            #     'Sending data: alignak.arbiter-master.test:0|ms'
            # ), 3)
            # Prepare brok and remove specific brok properties (for test purpose only...
            brok.prepare()
            brok.__dict__.pop('creation_time')
            brok.__dict__.pop('instance_id')
            brok.__dict__.pop('prepared')
            brok.__dict__.pop('uuid')
            brok.__dict__['data'].pop('ts')
            assert brok.__dict__ == {'type': 'alignak_stat',
                                     'data': {
                                         'type': 'counter',
                                         'metric': 'alignak.broker-master.test',
                                         'value': 0, 'uom': 'c'
                                     }}

            # Increment
            brok = self.statsmgr.counter('test', 1)
            assert len(self.statsmgr.stats) == 1
            # One more inner metric
            assert self.statsmgr.metrics_count == 2

            # Get min, max, count (incremented) and sum
            assert self.statsmgr.stats['test'] == (0, 1, 2, 1)
            # self.assert_log_match(re.escape(
            #     'Sending data: alignak.arbiter-master.test:1000|ms'
            # ), 4)
            # Prepare brok and remove specific brok properties (for test purpose only...
            brok.prepare()
            brok.__dict__.pop('creation_time')
            brok.__dict__.pop('instance_id')
            brok.__dict__.pop('prepared')
            brok.__dict__.pop('uuid')
            brok.__dict__['data'].pop('ts')
            assert brok.__dict__ == {'type': 'alignak_stat',
                                     'data': {
                                         'type': 'counter',
                                         'metric': 'alignak.broker-master.test',
                                         'value': 1, 'uom': 'c'
                                     }}

            # Increment - the function is called 'incr' but it does not increment, it sets the value!
            brok = self.statsmgr.counter('test', 12)
            assert len(self.statsmgr.stats) == 1
            # Get min, max, count (incremented) and sum (increased)
            assert self.statsmgr.stats['test'] == (0, 12, 3, 13)
            # self.assert_log_match(re.escape(
            #     'Sending data: alignak.arbiter-master.test:1000|ms'
            # ), 5)
            # Prepare brok and remove specific brok properties (for test purpose only...
            brok.prepare()
            brok.__dict__.pop('creation_time')
            brok.__dict__.pop('instance_id')
            brok.__dict__.pop('prepared')
            brok.__dict__.pop('uuid')
            brok.__dict__['data'].pop('ts')
            assert brok.__dict__ == {'type': 'alignak_stat',
                                     'data': {
                                         'type': 'counter',
                                         'metric': 'alignak.broker-master.test',
                                         'value': 12, 'uom': 'c'
                                     }}

        def test_statsmgr_gauge(self):
            """ Test sending data for a gauge
            :return:
            """
            # Register stats manager as enabled
            self.statsmgr.connect('arbiter-master', 'arbiter',
                                  host='localhost', port=2003, prefix='alignak', enabled=True,
                                  broks_enabled=True)
            index = 0
            self.assert_log_match(re.escape(
                'Graphite/carbon configuration for arbiter-master - localhost:2003, '
                'prefix: alignak, enabled: True, broks: True, file: None'
            ), index)
            index += 1
            self.assert_log_match(re.escape(
                'Sending arbiter-master statistics to: localhost:2003, prefix: alignak'
            ), index)
            index += 1
            self.assert_log_match(re.escape(
                'Alignak internal statistics will be sent to Graphite.'
            ), index)
            index += 1

            assert self.statsmgr.stats == {}

            # Create a metric statistic
            brok = self.statsmgr.gauge('test', 0)
            assert len(self.statsmgr.stats) == 1
            # One more inner metric
            assert self.statsmgr.metrics_count == 1

            # Get min, max, count and sum
            assert self.statsmgr.stats['test'] == (0, 0, 1, 0)
            # self.assert_log_match(re.escape(
            #     'Sending data: alignak.arbiter-master.test:0|ms'
            # ), 3)
            # Prepare brok and remove specific brok properties (for test purpose only...
            brok.prepare()
            brok.__dict__.pop('creation_time')
            brok.__dict__.pop('instance_id')
            brok.__dict__.pop('prepared')
            brok.__dict__.pop('uuid')
            brok.__dict__['data'].pop('ts')
            assert brok.__dict__ == {'type': 'alignak_stat',
                                     'data': {
                                         'type': 'gauge',
                                         'metric': 'alignak.arbiter-master.test',
                                         'value': 0, 'uom': 'g'
                                     }}

            # Increment
            brok = self.statsmgr.gauge('test', 1)
            assert len(self.statsmgr.stats) == 1
            # One more inner metric
            assert self.statsmgr.metrics_count == 2

            # Get min, max, count (incremented) and sum
            assert self.statsmgr.stats['test'] == (0, 1, 2, 1)
            # self.assert_log_match(re.escape(
            #     'Sending data: alignak.arbiter-master.test:1000|ms'
            # ), 4)
            # Prepare brok and remove specific brok properties (for test purpose only...
            brok.prepare()
            brok.__dict__.pop('creation_time')
            brok.__dict__.pop('instance_id')
            brok.__dict__.pop('prepared')
            brok.__dict__.pop('uuid')
            brok.__dict__['data'].pop('ts')
            assert brok.__dict__ == {'type': 'alignak_stat',
                                     'data': {
                                         'type': 'gauge',
                                         'metric': 'alignak.arbiter-master.test',
                                         'value': 1, 'uom': 'g'
                                     }}

            # Increment - the function is called 'incr' but it does not increment, it sets the value!
            brok = self.statsmgr.gauge('test', 12)
            assert len(self.statsmgr.stats) == 1
            # One more inner metric
            assert self.statsmgr.metrics_count == 3

            # Get min, max, count (incremented) and sum (increased)
            assert self.statsmgr.stats['test'] == (0, 12, 3, 13)
            # self.assert_log_match(re.escape(
            #     'Sending data: alignak.arbiter-master.test:1000|ms'
            # ), 5)
            # Prepare brok and remove specific brok properties (for test purpose only...
            brok.prepare()
            brok.__dict__.pop('creation_time')
            brok.__dict__.pop('instance_id')
            brok.__dict__.pop('prepared')
            brok.__dict__.pop('uuid')
            brok.__dict__['data'].pop('ts')
            assert brok.__dict__ == {'type': 'alignak_stat',
                                     'data': {
                                         'type': 'gauge',
                                         'metric': 'alignak.arbiter-master.test',
                                         'value': 12, 'uom': 'g'
                                     }}

        def test_statsmgr_flush(self):
            """ Test sending several data at once to a Graphite server

            The stats manager do not send the metrics when it is configured for Graphite. It is needed
            to call the flush method periodically to send the stored metrics.

            :return:
            """
            # Register stats manager as enabled
            self.statsmgr.connect('arbiter-master', 'arbiter',
                                  host='localhost', port=2003, prefix='alignak', enabled=True)
            assert self.statsmgr.metrics_count == 0
            assert self.statsmgr.stats == {}
            self.clear_logs()

            # Flush but no metrics exist
            assert self.statsmgr.flush()

            self.clear_logs()

            # Create a timer metric
            self.statsmgr.timer('my_timer', 0)
            self.statsmgr.timer('my_timer', 1)
            self.statsmgr.timer('my_timer', 12)

            self.statsmgr.counter('my_counter', 3)

            self.statsmgr.gauge('my_gauge', 125)

            # 5 metrics stored
            assert self.statsmgr.metrics_count == 5

            assert self.statsmgr.flush()


class TestStatsFile(AlignakTest):
    """
    This class test the Alignak stats in a file
    """
    def setUp(self):

        super(TestStatsFile, self).setUp()

        # Log at DEBUG level
        self.set_unit_tests_logger_level()
        self.clear_logs()

        # Declare environment to send stats to a file
        os.environ['ALIGNAK_STATS_FILE'] = '/tmp/stats.alignak'
        # Those are the same as the default values:
        os.environ['ALIGNAK_STATS_FILE_LINE_FMT'] = '[#date#] #counter# #value# #uom#\n'
        os.environ['ALIGNAK_STATS_FILE_DATE_FMT'] = '%Y-%m-%d %H:%M:%S'

        # Create our stats manager...
        self.statsmgr = Stats()
        assert self.statsmgr.stats_file == '/tmp/stats.alignak'
        assert self.statsmgr.line_fmt == '[#date#] #counter# #value# #uom#\n'
        assert self.statsmgr.date_fmt == '%Y-%m-%d %H:%M:%S'

        self.line_count = 0
        if os.path.exists('/tmp/stats.alignak'):
            os.remove('/tmp/stats.alignak')

    def tearDown(self):
        self.statsmgr.file_d.close()

        print(("-----\n%s stats file\n-----\n" % '/tmp/stats.alignak'))
        try:
            hfile = open('/tmp/stats.alignak', 'r')
            lines = hfile.readlines()
            print(lines)
            hfile.close()
            assert self.line_count == len(lines)
        except OSError as exp:
            print(("Error: %s" % exp))
            assert False

    def test_statsmgr_timer_file(self):
        """ Test sending data for a timer
        :return:
        """
        # Register stats manager as enabled but no report to StatsD
        self.statsmgr.register('arbiter-master', 'arbiter',
                               statsd_enabled=True, statsd_host=None)
        index = 0
        self.assert_log_match(re.escape(
            'StatsD configuration for arbiter-master - None:8125, prefix: alignak, '
            'enabled: True, broks: False, file: /tmp/stats.alignak'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Alignak internal statistics are written in the file /tmp/stats.alignak'
        ), index)

        assert self.statsmgr.stats == {}

        # Create a metric statistic
        self.statsmgr.timer('test', 0)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count and sum
        assert self.statsmgr.stats['test'] == (0, 0, 1, 0)

        assert self.statsmgr.file_d is not None
        assert os.path.exists(self.statsmgr.stats_file)
        self.line_count += 1

        # Increment
        self.statsmgr.timer('test', 1)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count (incremented) and sum
        assert self.statsmgr.stats['test'] == (0, 1, 2, 1)
        self.line_count += 1

    def test_statsmgr_counter_file(self):
        """ Test sending data for a counter
        :return:
        """
        # Register stats manager as enabled but no report to StatsD
        self.statsmgr.register('arbiter-master', 'arbiter',
                               statsd_enabled=True, statsd_host=None)
        index = 0
        self.assert_log_match(re.escape(
            'StatsD configuration for arbiter-master - None:8125, prefix: alignak, '
            'enabled: True, broks: False, file: /tmp/stats.alignak'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Alignak internal statistics are written in the file /tmp/stats.alignak'
        ), index)

        assert self.statsmgr.stats == {}

        # Create a metric statistic
        self.statsmgr.counter('test', 0)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count and sum
        assert self.statsmgr.stats['test'] == (0, 0, 1, 0)
        self.line_count += 1

    def test_statsmgr_gauge_file(self):
        """ Test sending data for a gauge
        :return:
        """
        # Register stats manager as enabled
        self.statsmgr.register('arbiter-master', 'arbiter',
                               statsd_host='localhost', statsd_port=8125,
                               statsd_prefix='alignak', statsd_enabled=True,
                               broks_enabled=True)
        index = 0
        self.assert_log_match(re.escape(
            'StatsD configuration for arbiter-master - localhost:8125, prefix: alignak, '
            'enabled: True, broks: True, file: /tmp/stats.alignak'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Sending arbiter-master statistics to: localhost:8125, prefix: alignak'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Trying to contact StatsD server...'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'StatsD server contacted'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Alignak internal statistics are sent to StatsD.'
        ), index)
        index += 1
        self.assert_log_match(re.escape(
            'Alignak internal statistics are written in the file /tmp/stats.alignak'
        ), index)
        index += 1

        assert self.statsmgr.stats == {}

        # Create a metric statistic
        self.statsmgr.gauge('test', 0)
        assert len(self.statsmgr.stats) == 1
        # Get min, max, count and sum
        assert self.statsmgr.stats['test'] == (0, 0, 1, 0)
        self.line_count += 1
