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
This file tests the self monitoring features of the Alignak Arbiter
"""

import re
import time
import datetime
import pytest
import logging
import requests_mock
from freezegun import freeze_time
from .alignak_test import AlignakTest
from alignak.log import ALIGNAK_LOGGER_NAME
from alignak.misc.serialization import unserialize
from alignak.daemons.arbiterdaemon import Arbiter
from alignak.dispatcher import Dispatcher, DispatcherError


class TestMonitor(AlignakTest):
    """
    This class tests the dispatcher (distribute configuration to satellites)
    """
    def setUp(self):
        """Test starting"""
        super(TestMonitor, self).setUp()

        # Log at DEBUG level
        self.set_unit_tests_logger_level()

    def _monitoring(self, env_filename='tests/cfg/monitor/simple.ini', loops=3, multi_realms=False):
        """ monitoring process: prepare, check, dispatch

        This function realize all the monitoring operations:
        - load a monitoring configuration
        - prepare the monitoring
        - dispatch
        - check the correct monitoring, including:
            - check the configuration dispatched to the schedulers
            - check the configuration dispatched to the spare arbiter (if any)
        - run the check_reachable loop several times

        if multi_realms is True, the scheduler configuration received are not checked against
        the arbiter whole configuration. This would be really too complex to assert on this :(

        Schedulers must have a port number with 7768 (eg. 7768,17768,27768,...)

        Spare daemons must have a port number with 8770 (eg. 8770,18770,28770,...)

        :return: None
        """
        args = {
            'env_file': env_filename,
            'alignak_name': 'alignak-test', 'daemon_name': 'arbiter-master'
        }
        my_arbiter = Arbiter(**args)
        my_arbiter.setup_alignak_logger()

        # Clear logs
        self.clear_logs()

        # my_arbiter.load_modules_manager()
        my_arbiter.load_monitoring_config_file()
        assert my_arbiter.conf.conf_is_correct is True

        # #1 - Get a new dispatcher
        my_dispatcher = Dispatcher(my_arbiter.conf, my_arbiter.link_to_myself)
        my_arbiter.dispatcher = my_dispatcher
        print("*** All daemons WS: %s"
              % ["%s:%s" % (link.address, link.port)
                 for link in my_dispatcher.all_daemons_links])

        assert my_arbiter.alignak_monitor == "http://super_alignak:7773/ws"
        assert my_arbiter.alignak_monitor_username == 'admin'
        assert my_arbiter.alignak_monitor_password == 'admin'

        metrics = []
        for type in sorted(my_arbiter.conf.types_creations):
            _, _, strclss, _, _ = my_arbiter.conf.types_creations[type]
            if strclss in ['hostescalations', 'serviceescalations']:
                continue

            objects_list = getattr(my_arbiter.conf, strclss, [])
            metrics.append("'%s'=%d" % (strclss, len(objects_list)))

        # Simulate the daemons HTTP interface (very simple simulation !)
        with requests_mock.mock() as mr:
            mr.post('%s/login' % (my_arbiter.alignak_monitor),
                    json={
                        "_status": "OK",
                        "_result": ["1508507175582-c21a7d8e-ace0-47f2-9b10-280a17152c7c"]
                    })
            mr.patch('%s/host' % (my_arbiter.alignak_monitor),
                   json={
                       "_status": "OK",
                       "_result": ["1508507175582-c21a7d8e-ace0-47f2-9b10-280a17152c7c"]
                   })

            # Time warp 5 seconds - overpass the ping period...
            self.clear_logs()
            # frozen_datetime.tick(delta=datetime.timedelta(seconds=5))

            my_arbiter.get_alignak_status(details=False)

            self.show_logs()

            # Hack the requests history to check and simulate  the configuration pushed...
            history = mr.request_history
            for index, request in enumerate(history):
                # Check what is patched on /host ...
                if 'host' in request.url:
                    received = request.json()
                    print((index, request.url, received))

                    from pprint import pprint
                    pprint(received)

                    assert received['name'] == 'My Alignak'
                    assert received['livestate']['timestamp'] == 1519583400
                    assert received['livestate']['state'] == 'up'
                    assert received['livestate']['output'] == 'Some of my daemons are not reachable.'
                    for metric in metrics:
                        assert metric in received['livestate']['perf_data']
                    print(received['livestate']['long_output'])
                    # Long output is sorted by daemon name
                    assert received['livestate']['long_output'] == \
                           u'broker-master - daemon is not reachable.\n' \
                           u'poller-master - daemon is not reachable.\n' \
                           u'reactionner-master - daemon is not reachable.\n' \
                           u'receiver-master - daemon is not reachable.\n' \
                           u'scheduler-master - daemon is not reachable.'

                    for link in my_dispatcher.all_daemons_links:
                        assert link.name in [service['name'] for service in received['services']]

                    for service in received['services']:
                        assert 'name' in service
                        assert 'livestate' in service
                        assert 'timestamp' in service['livestate']
                        assert 'state' in service['livestate']
                        assert 'output' in service['livestate']
                        assert 'long_output' in service['livestate']
                        assert 'perf_data' in service['livestate']

    @freeze_time("2018-02-25 18:30:00")
    def test_monitoring_simple(self):
        """ Test the monitoring process: simple configuration

        :return: None
        """
        self._monitoring()

    @pytest.mark.skip("Only for local tests ... directly send information to a monitor host.")
    def test_real(self):
        args = {
            'env_file': os.path.join(self._test_dir, 'cfg/monitor/simple.ini'),
            'alignak_name': 'alignak-test', 'daemon_name': 'arbiter-master'
        }
        my_arbiter = Arbiter(**args)
        my_arbiter.setup_alignak_logger()

        # Clear logs
        self.clear_logs()

        my_arbiter.alignak_monitor = "http://alignak-mos-ws.kiosks.ipmfrance.com"
        my_arbiter.alignak_monitor_username = 'admin'
        my_arbiter.alignak_monitor_password = 'ipm-France2017'

        # my_arbiter.load_modules_manager()
        my_arbiter.load_monitoring_config_file()
        assert my_arbiter.conf.conf_is_correct is True

        # #1 - Get a new dispatcher
        my_dispatcher = Dispatcher(my_arbiter.conf, my_arbiter.link_to_myself)
        my_arbiter.dispatcher = my_dispatcher
        print("*** All daemons WS: %s"
              % ["%s:%s" % (link.address, link.port)
                 for link in my_dispatcher.all_daemons_links])

        my_arbiter.push_passive_check(details=False)

