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
"""
This file contains the tests for the internal metrics module
"""

import re
import pickle
import threading
from alignak.stats import *
from alignak.modulesmanager import ModulesManager
from alignak.brok import Brok

from .alignak_test import AlignakTest


class FakeCarbonServer(threading.Thread):
    def __init__(self, host='127.0.0.1', port=0):
        super(FakeCarbonServer, self).__init__()
        self.setDaemon(True)
        self.port = port
        self.cli_socks = []  # will retain the client socks here
        sock = self.sock = socket.socket()
        sock.settimeout(1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
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
            except socket.error:
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
        print("Fake carbon received: %s" % pickle.dumps(data))
        sock.close()


class TestMetricsSetup(AlignakTest):
    """
    This class tests the inner metrics module set-up
    """
    def setUp(self):
        super(TestMetricsSetup, self).setUp()

        # Log at DEBUG level
        self.set_unit_tests_logger_level()
        self.clear_logs()

        # Create a fake server
        self.fake_carbon = FakeCarbonServer(port=2004)

        if os.path.exists('/tmp/alignak-metrics.log'):
            os.remove('/tmp/alignak-metrics.log')

    def tearDown(self):
        super(TestMetricsSetup, self).tearDown()

        self.fake_carbon.stop()
        self.fake_carbon.join()

    def test_default_is_disabled(self):
        """ Test that default configuration is metrics disabled

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        # Default configuration do not enable the module
        assert True == self._scheduler.pushed_conf.process_performance_data
        assert self._scheduler.pushed_conf.host_perfdata_command is None
        assert self._scheduler.pushed_conf.service_perfdata_command is None
        assert self._scheduler.pushed_conf.host_perfdata_file == ''
        assert self._scheduler.pushed_conf.service_perfdata_file == ''

        assert self._broker_daemon.modules == []

    def test_inner_module_enabled(self):
        """ Test that inner metrics module may be enabled

        If configuration parameters host_perfdata_command or service_perfdata_command
        are declared and not empty and if process_performance_data is set, the inner metrics
        module is configured and enabled to push performance data to the Alignak configured
        StatsD / Graphite interface.

        :return: None
        """
        self.setup_with_file('cfg/cfg_metrics.cfg')

        # Specific configuration enables the module
        assert True == self._scheduler.pushed_conf.process_performance_data
        assert self._scheduler.pushed_conf.host_perfdata_file == 'go-hosts'
        assert self._scheduler.pushed_conf.service_perfdata_file == 'go-services'
        assert 1 == len(self._broker_daemon.modules)

        self.show_logs()

    def test_inner_module_configuration(self):
        """ Test that inner metrics module may be configured in Alignak configuration

        Withi this configuration, hosts/services cache is enabled and tested. Broks for
        unknown hosts/services are ignored.

        :return: None
        """
        self.setup_with_file('cfg/cfg_metrics.cfg', 'cfg/inner_metrics/alignak.ini')

        # Specific configuration enables the module
        assert True == self._scheduler.pushed_conf.process_performance_data
        assert self._scheduler.pushed_conf.host_perfdata_file == 'go-hosts'
        assert self._scheduler.pushed_conf.service_perfdata_file == 'go-services'
        assert 1 == len(self._broker_daemon.modules)

        self.show_logs()

        # The declared module instance
        my_module = self._broker_daemon.modules[0]
        print(my_module)
        # Generic stuff
        assert my_module.python_name == 'alignak.modules.inner_metrics'
        assert my_module.type == 'metrics'
        assert my_module.alias == 'inner-metrics'
        assert my_module.enabled is True

        # Specific stuff - the content of the configuration parameters
        # When the module is configured in Alignak configuration, it does not exist!
        # assert my_module.host_perfdata_file == 'go-hosts'
        # assert my_module.service_perfdata_file == 'go-services'

        self.clear_logs()

        # Module is not yet initialized, let's do it in place of the daemon.
        # Create the modules manager for a daemon type
        self.modules_manager = ModulesManager(self._broker_daemon)

        # Load an initialize the modules:
        #  - load python module
        #  - get module properties and instances
        self.modules_manager.load_and_init([my_module])

        self.show_logs()

        # Module is an internal one (no external process) in the broker daemon modules manager
        my_module = self._broker_daemon.modules_manager.instances[0]
        assert my_module.is_external is False

        # Known hosts/services cache is empty
        assert my_module.hosts_cache == {}
        assert my_module.services_cache == {}

        # When the broker daemon receives a Brok, it is propagated to the module

        # Host check result
        self.clear_logs()
        hcr = {
            "host_name": "srv001",

            "last_time_unreachable": 0,
            "last_problem_id": 0,
            "passive_check": False,
            "retry_interval": 1,
            "last_event_id": 0,
            "problem_has_been_acknowledged": False,
            "command_name": "pm-check_linux_host_alive",
            "last_state": "UP",
            "latency": 0.2317881584,
            "last_state_type": "HARD",
            "last_hard_state_change": 1444427108,
            "last_time_up": 0,
            "percent_state_change": 0.0,
            "state": "DOWN",
            "last_chk": 1444427104,
            "last_state_id": 0,
            "end_time": 0,
            "timeout": 0,
            "current_event_id": 10,
            "execution_time": 3.1496069431000002,
            "start_time": 0,
            "return_code": 2,
            "state_type": "SOFT",
            "output": "CRITICAL - Plugin timed out after 10 seconds",
            "in_checking": True,
            "early_timeout": 0,
            "in_scheduled_downtime": False,
            "attempt": 0,
            "state_type_id": 1,
            "acknowledgement_type": 1,
            "last_state_change": 1444427108.040841,
            "last_time_down": 1444427108,
            "instance_id": 0,
            "long_output": "",
            "current_problem_id": 0,
            "check_interval": 5,
            "state_id": 2,
            "has_been_checked": 1,
            "perf_data": "uptime=1200;rta=0.049000ms;2.000000;3.000000;0.000000 pl=0%;50;80;0"
        }
        b = Brok({'data': hcr, 'type': 'host_check_result'}, False)
        self._broker_daemon.manage_brok(b)
        self.show_logs()
        self.assert_log_count(1)
        self.assert_log_match("received host check result for an unknown host", 0)

        # Service check result
        self.clear_logs()
        scr = {
            "host_name": "srv001",
            "service_description": "ping",
            "command_name": "ping",

            "attempt": 1,
            "execution_time": 3.1496069431000002,
            "latency": 0.2317881584,
            "return_code": 2,
            "state": "OK",
            "state_type": "HARD",
            "state_id": 0,
            "state_type_id": 1,

            "output": "PING OK - Packet loss = 0%, RTA = 0.05 ms",
            "long_output": "Long output ...",
            "perf_data": "rta=0.049000ms;2.000000;3.000000;0.000000 pl=0%;50;80;0",

            "passive_check": False,

            "problem_has_been_acknowledged": False,
            "acknowledgement_type": 1,
            "in_scheduled_downtime": False,

            "last_chk": 1473597375,
            "last_state_change": 1444427108.147903,
            "last_state_id": 0,
            "last_state": "UNKNOWN",
            "last_state_type": "HARD",
            "last_hard_state_change": 0.0,
            "last_time_unknown": 0,
            "last_time_unreachable": 0,
            "last_time_critical": 1473597376,
            "last_time_warning": 0,
            "last_time_ok": 0,

            "retry_interval": 2,
            "percent_state_change": 4.1,
            "check_interval": 5,

            "in_checking": False,
            "early_timeout": 0,
            "instance_id": "3ac88dd0c1c04b37a5d181622e93b5bc",
            "current_event_id": 1,
            "last_event_id": 0,
            "current_problem_id": 1,
            "last_problem_id": 0,
            "timeout": 0,
            "has_been_checked": 1,
            "start_time": 0,
            "end_time": 0
        }
        b = Brok({'data': scr, 'type': 'service_check_result'}, False)
        self._broker_daemon.manage_brok(b)
        self.show_logs()
        self.assert_log_count(1)
        self.assert_log_match("received service check result for an unknown host", 0)

        # Initial host status
        self.clear_logs()
        hcr = {
            "host_name": "srv001",
        }
        b = Brok({'data': hcr, 'type': 'initial_host_status'}, False)
        self._broker_daemon.manage_brok(b)
        self.show_logs()
        # The module inner cache stored the host
        assert 'srv001' in my_module.hosts_cache
        assert my_module.hosts_cache['srv001'] == {}
        assert my_module.services_cache == {}

        # Initial service status
        self.clear_logs()
        hcr = {
            "host_name": "srv001",
            "service_description": "ping"
        }
        b = Brok({'data': hcr, 'type': 'initial_service_status'}, False)
        self._broker_daemon.manage_brok(b)
        self.show_logs()
        # The module inner cache stored the host
        assert 'srv001' in my_module.hosts_cache
        assert my_module.hosts_cache['srv001'] == {}
        assert 'srv001/ping' in my_module.services_cache
        assert my_module.services_cache['srv001/ping'] == {}

        # Now the host srv001 is known in the module, let's raise an host brok

        # Host check result
        self.clear_logs()
        hcr = {
            "host_name": "srv001",

            "last_time_unreachable": 0,
            "last_problem_id": 0,
            "passive_check": False,
            "retry_interval": 1,
            "last_event_id": 0,
            "problem_has_been_acknowledged": False,
            "command_name": "pm-check_linux_host_alive",
            "last_state": "UP",
            "latency": 0.2317881584,
            "last_state_type": "HARD",
            "last_hard_state_change": 1444427108,
            "last_time_up": 0,
            "percent_state_change": 0.0,
            "state": "DOWN",
            "last_chk": 1444427104,
            "last_state_id": 0,
            "end_time": 0,
            "timeout": 0,
            "current_event_id": 10,
            "execution_time": 3.1496069431000002,
            "start_time": 0,
            "return_code": 2,
            "state_type": "SOFT",
            "output": "CRITICAL - Plugin timed out after 10 seconds",
            "in_checking": True,
            "early_timeout": 0,
            "in_scheduled_downtime": False,
            "attempt": 0,
            "state_type_id": 1,
            "acknowledgement_type": 1,
            "last_state_change": 1444427108.040841,
            "last_time_down": 1444427108,
            "instance_id": 0,
            "long_output": "",
            "current_problem_id": 0,
            "check_interval": 5,
            "state_id": 2,
            "has_been_checked": 1,
            "perf_data": "uptime=1200;rta=0.049000ms;2.000000;3.000000;0.000000 pl=0%;50;80;0"
        }
        b = Brok({'data': hcr, 'type': 'host_check_result'}, False)
        self._broker_daemon.manage_brok(b)

        # 5 log events because the Graphite server do not respond!
        self.show_logs()
        # self.assert_any_log_match(re.escape('Exception: [Errno 111] Connection refused'))
        self.assert_log_count(0)

        # File output
        assert os.path.exists('/tmp/alignak-metrics.log')

    def test_inner_module_broks(self):
        """ Test that inner metrics module is managing broks with the default configuration

        :return: None
        """
        self.setup_with_file('cfg/cfg_metrics.cfg')

        # Specific configuration enables the module
        assert True == self._scheduler.pushed_conf.process_performance_data
        assert self._scheduler.pushed_conf.host_perfdata_file == 'go-hosts'
        assert self._scheduler.pushed_conf.service_perfdata_file == 'go-services'
        assert 1 == len(self._broker_daemon.modules)

        self.show_logs()

        # The declared module instance
        my_module = self._broker_daemon.modules[0]
        # Generic stuff
        assert my_module.python_name == 'alignak.modules.inner_metrics'
        assert my_module.type == 'metrics'
        assert my_module.alias == 'inner-metrics'
        assert my_module.enabled is True

        # Specific stuff - the content of the configuration parameters
        assert my_module.host_perfdata_file == 'go-hosts'
        assert my_module.service_perfdata_file == 'go-services'

        self.clear_logs()

        # Module is not yet initialized, let's do it in place of the daemon.
        # Create the modules manager for a daemon type
        self.modules_manager = ModulesManager(self._broker_daemon)

        # Load an initialize the modules:
        #  - load python module
        #  - get module properties and instances
        self.modules_manager.load_and_init([my_module])

        self.show_logs()

        # Module is an internal one (no external process) in the broker daemon modules manager
        my_module = self._broker_daemon.modules_manager.instances[0]
        assert my_module.is_external is False

        # Known hosts/services cache is empty
        assert my_module.hosts_cache == {}
        assert my_module.services_cache == {}

        # When the broker daemon receives a Brok, it is propagated to the module

        # Host check result
        self.clear_logs()
        hcr = {
            "host_name": "srv001",

            "last_time_unreachable": 0,
            "last_problem_id": 0,
            "passive_check": False,
            "retry_interval": 1,
            "last_event_id": 0,
            "problem_has_been_acknowledged": False,
            "command_name": "pm-check_linux_host_alive",
            "last_state": "UP",
            "latency": 0.2317881584,
            "last_state_type": "HARD",
            "last_hard_state_change": 1444427108,
            "last_time_up": 0,
            "percent_state_change": 0.0,
            "state": "DOWN",
            "last_chk": 1444427104,
            "last_state_id": 0,
            "end_time": 0,
            "timeout": 0,
            "current_event_id": 10,
            "execution_time": 3.1496069431000002,
            "start_time": 0,
            "return_code": 2,
            "state_type": "SOFT",
            "output": "CRITICAL - Plugin timed out after 10 seconds",
            "in_checking": True,
            "early_timeout": 0,
            "in_scheduled_downtime": False,
            "attempt": 0,
            "state_type_id": 1,
            "acknowledgement_type": 1,
            "last_state_change": 1444427108.040841,
            "last_time_down": 1444427108,
            "instance_id": 0,
            "long_output": "",
            "current_problem_id": 0,
            "check_interval": 5,
            "state_id": 2,
            "has_been_checked": 1,
            "perf_data": "uptime=1200;rta=0.049000ms;2.000000;3.000000;0.000000 pl=0%;50;80;0"
        }
        b = Brok({'data': hcr, 'type': 'host_check_result'}, False)
        self._broker_daemon.manage_brok(b)
        self.show_logs()
        self.assert_log_count(0)

        # Service check result
        self.clear_logs()
        scr = {
            "host_name": "srv001",
            "service_description": "ping",
            "command_name": "ping",

            "attempt": 1,
            "execution_time": 3.1496069431000002,
            "latency": 0.2317881584,
            "return_code": 2,
            "state": "OK",
            "state_type": "HARD",
            "state_id": 0,
            "state_type_id": 1,

            "output": "PING OK - Packet loss = 0%, RTA = 0.05 ms",
            "long_output": "Long output ...",
            "perf_data": "rta=0.049000ms;2.000000;3.000000;0.000000 pl=0%;50;80;0",

            "passive_check": False,

            "problem_has_been_acknowledged": False,
            "acknowledgement_type": 1,
            "in_scheduled_downtime": False,

            "last_chk": 1473597375,
            "last_state_change": 1444427108.147903,
            "last_state_id": 0,
            "last_state": "UNKNOWN",
            "last_state_type": "HARD",
            "last_hard_state_change": 0.0,
            "last_time_unknown": 0,
            "last_time_unreachable": 0,
            "last_time_critical": 1473597376,
            "last_time_warning": 0,
            "last_time_ok": 0,

            "retry_interval": 2,
            "percent_state_change": 4.1,
            "check_interval": 5,

            "in_checking": False,
            "early_timeout": 0,
            "instance_id": "3ac88dd0c1c04b37a5d181622e93b5bc",
            "current_event_id": 1,
            "last_event_id": 0,
            "current_problem_id": 1,
            "last_problem_id": 0,
            "timeout": 0,
            "has_been_checked": 1,
            "start_time": 0,
            "end_time": 0
        }
        b = Brok({'data': scr, 'type': 'service_check_result'}, False)
        self._broker_daemon.manage_brok(b)
        self.show_logs()
        self.assert_log_count(0)

        # Initial host status
        self.clear_logs()
        hcr = {
            "host_name": "srv001",
        }
        b = Brok({'data': hcr, 'type': 'initial_host_status'}, False)
        self._broker_daemon.manage_brok(b)
        self.show_logs()
        # The module inner cache stored the host
        assert 'srv001' in my_module.hosts_cache
        assert my_module.hosts_cache['srv001'] == {}
        assert my_module.services_cache == {}

        # Initial service status
        self.clear_logs()
        hcr = {
            "host_name": "srv001",
            "service_description": "ping"
        }
        b = Brok({'data': hcr, 'type': 'initial_service_status'}, False)
        self._broker_daemon.manage_brok(b)
        self.show_logs()
        # The module inner cache stored the host
        assert 'srv001' in my_module.hosts_cache
        assert my_module.hosts_cache['srv001'] == {}
        assert 'srv001/ping' in my_module.services_cache
        assert my_module.services_cache['srv001/ping'] == {}


class TestMetricsRun(AlignakTest):
    """
    This class tests the inner metrics module running
    """

    def setUp(self):
        super(TestMetricsRun, self).setUp()

        # Log at DEBUG level
        self.set_unit_tests_logger_level()

        # Create our own stats manager...
        # do not use the global object to restart with a fresh one on each test
        self.fake_carbon = FakeCarbonServer(host='localhost', port=2004)

    def tearDown(self):
        super(TestMetricsRun, self).tearDown()

        self.fake_carbon.stop()
        self.fake_carbon.join()

    def test_inner_module_checks_results(self):
        """ Test that inner metrics module is pushing data to Graphite

        :return: None
        """
        self.setup_with_file('cfg/cfg_metrics.cfg')
        # self.clear_logs()

        # Module is an internal one (no external process) in the broker daemon modules manager
        my_module = self._broker_daemon.modules_manager.instances[0]
        assert my_module.is_external is False
        my_module.metrics_flush_count = 1

        # When the broker daemon receives a Brok, it is propagated to the module

        # Host check result
        self.clear_logs()
        hcr = {
            "host_name": "srv001",

            "last_time_unreachable": 0,
            "last_problem_id": 0,
            "passive_check": False,
            "retry_interval": 1,
            "last_event_id": 0,
            "problem_has_been_acknowledged": False,
            "command_name": "pm-check_linux_host_alive",
            "last_state": "UP",
            "latency": 0.2317881584,
            "last_state_type": "HARD",
            "last_hard_state_change": 1444427108,
            "last_time_up": 0,
            "percent_state_change": 0.0,
            "state": "DOWN",
            "last_chk": 1444427104,
            "last_state_id": 0,
            "end_time": 0,
            "timeout": 0,
            "current_event_id": 10,
            "execution_time": 3.1496069431000002,
            "start_time": 0,
            "return_code": 2,
            "state_type": "SOFT",
            "output": "CRITICAL - Plugin timed out after 10 seconds",
            "in_checking": True,
            "early_timeout": 0,
            "in_scheduled_downtime": False,
            "attempt": 0,
            "state_type_id": 1,
            "acknowledgement_type": 1,
            "last_state_change": 1444427108.040841,
            "last_time_down": 1444427108,
            "instance_id": 0,
            "long_output": "",
            "current_problem_id": 0,
            "check_interval": 5,
            "state_id": 2,
            "has_been_checked": 1,
            "perf_data": "uptime=1200;rta=0.049000ms;2.000000;3.000000;0.000000 pl=0%;50;80;0"
        }
        b = Brok({'data': hcr, 'type': 'host_check_result'}, False)
        self._broker_daemon.manage_brok(b)
        self.show_logs()
        self.assert_log_count(0)

        # Service check result
        self.clear_logs()
        scr = {
            "host_name": "srv001",
            "service_description": "ping",
            "command_name": "ping",

            "attempt": 1,
            "execution_time": 3.1496069431000002,
            "latency": 0.2317881584,
            "return_code": 2,
            "state": "OK",
            "state_type": "HARD",
            "state_id": 0,
            "state_type_id": 1,

            "output": "PING OK - Packet loss = 0%, RTA = 0.05 ms",
            "long_output": "Long output ...",
            "perf_data": "rta=0.049000ms;2.000000;3.000000;0.000000 pl=0%;50;80;0",

            "passive_check": False,

            "problem_has_been_acknowledged": False,
            "acknowledgement_type": 1,
            "in_scheduled_downtime": False,

            "last_chk": 1473597375,
            "last_state_change": 1444427108.147903,
            "last_state_id": 0,
            "last_state": "UNKNOWN",
            "last_state_type": "HARD",
            "last_hard_state_change": 0.0,
            "last_time_unknown": 0,
            "last_time_unreachable": 0,
            "last_time_critical": 1473597376,
            "last_time_warning": 0,
            "last_time_ok": 0,

            "retry_interval": 2,
            "percent_state_change": 4.1,
            "check_interval": 5,

            "in_checking": False,
            "early_timeout": 0,
            "instance_id": "3ac88dd0c1c04b37a5d181622e93b5bc",
            "current_event_id": 1,
            "last_event_id": 0,
            "current_problem_id": 1,
            "last_problem_id": 0,
            "timeout": 0,
            "has_been_checked": 1,
            "start_time": 0,
            "end_time": 0
        }
        b = Brok({'data': scr, 'type': 'service_check_result'}, False)
        self._broker_daemon.manage_brok(b)
        self.show_logs()
        self.assert_log_count(0)
        print(my_module.my_metrics)
