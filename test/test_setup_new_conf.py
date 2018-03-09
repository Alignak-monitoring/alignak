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
This file test load the new conf on each module
"""

import logging
import psutil
import requests_mock
from alignak_test import AlignakTest
from alignak.daemons.schedulerdaemon import Alignak as schedulerdaemon
from alignak.daemons.receiverdaemon import Receiver as receiverdaemon
from alignak.daemons.pollerdaemon import Poller as pollerdaemon
from alignak.daemons.brokerdaemon import Broker as brokerdaemon
from alignak.daemons.reactionnerdaemon import Reactionner as reactionnerdaemon


class TestSetupNewConf(AlignakTest):
    """
    This class will test load new conf for each modules (broker, scheduler...)

    """
    def setUp(self):
        super(TestSetupNewConf, self).setUp()

    def test_several_loads(self):
        """

        :return:
        """
        for count in range (0, 5):
            perfdatas = []
            my_process = psutil.Process()
            with my_process.oneshot():
                # perfdatas.append("num_threads=%d" % my_process.num_threads())
                # # perfdatas.append("num_ctx_switches=%d" % my_process.num_ctx_switches())
                # perfdatas.append("num_fds=%d" % my_process.num_fds())
                # # perfdatas.append("num_handles=%d" % my_process.num_handles())
                # perfdatas.append("create_time=%d" % my_process.create_time())
                # perfdatas.append("cpu_num=%d" % my_process.cpu_num())
                # perfdatas.append("cpu_usable=%d" % len(my_process.cpu_affinity()))
                perfdatas.append("cpu_percent=%.2f%%" % my_process.cpu_percent())

                # cpu_times_percent = my_process.cpu_times()
                # for key in cpu_times_percent._fields:
                #     perfdatas.append("cpu_%s_time=%.2fs" % (key,
                #                                             getattr(cpu_times_percent, key)))

                memory = my_process.memory_full_info()
                for key in memory._fields:
                    perfdatas.append("mem_%s=%db" % (key, getattr(memory, key)))

                print("Process pid=%s, cpu/memory|%s" %
                      (my_process.pid, " ".join(perfdatas)))

            self.test_conf_scheduler()

    def test_conf_scheduler(self):
        """ Test load new conf in scheduler

        :return: None
        """
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')

        args = {
            'env_file': self.env_filename,
            'alignak_name': 'my-alignak', 'daemon_name': 'unset',
        }
        scheduler_daemon = schedulerdaemon(**args)
        scheduler_daemon.load_modules_manager()

        scheduler_link = None
        for satellite in self._arbiter.dispatcher.schedulers:
            scheduler_link = satellite
            scheduler_daemon.new_conf = satellite.cfg
            break
        assert scheduler_link is not None

        scheduler_daemon.setup_new_conf()
        assert 1 == len(scheduler_daemon.modules)
        assert scheduler_daemon.modules[0].module_alias == 'Example'
        assert scheduler_daemon.modules[0].option_1 == 'foo'
        assert scheduler_daemon.modules[0].option_2 == 'bar'
        assert scheduler_daemon.modules[0].option_3 == 'foobar'
        for host in scheduler_daemon.sched.pushed_conf.hosts:
            print("Host: %s" % host)
        # Two hosts declared in the configuration
        # One host provided by the Example module loaded in the arbiter
        assert 3 == len(scheduler_daemon.sched.pushed_conf.hosts)
        assert len(scheduler_daemon.pollers) == 1
        assert len(scheduler_daemon.reactionners) == 1
        assert len(scheduler_daemon.brokers) == 1
        assert len(scheduler_daemon.schedulers) == 0
        if scheduler_link.manage_arbiters:
            assert len(scheduler_daemon.arbiters) == 1
        else:
            assert len(scheduler_daemon.arbiters) == 0
        assert len(scheduler_daemon.receivers) == 0

        # send new conf, so it's the second time. This to test the cleanup
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')
        scheduler_link = None
        for satellite in self._arbiter.dispatcher.schedulers:
            scheduler_link = satellite
            scheduler_daemon.new_conf = satellite.cfg
            break
        assert scheduler_link is not None

        scheduler_daemon.setup_new_conf()
        assert 1 == len(scheduler_daemon.modules)
        assert scheduler_daemon.modules[0].module_alias == 'Example'
        assert scheduler_daemon.modules[0].option_1 == 'foo'
        assert scheduler_daemon.modules[0].option_2 == 'bar'
        assert scheduler_daemon.modules[0].option_3 == 'foobar'
        for host in scheduler_daemon.sched.pushed_conf.hosts:
            print("Host: %s" % host)
        # Two hosts declared in the configuration
        # One host provided by the Example module loaded in the arbiter
        assert 3 == len(scheduler_daemon.sched.pushed_conf.hosts)
        assert len(scheduler_daemon.pollers) == 1
        assert len(scheduler_daemon.reactionners) == 1
        assert len(scheduler_daemon.brokers) == 1
        assert len(scheduler_daemon.schedulers) == 0
        if scheduler_link.manage_arbiters:
            assert len(scheduler_daemon.arbiters) == 1
        else:
            assert len(scheduler_daemon.arbiters) == 0
        assert len(scheduler_daemon.receivers) == 0

        # Stop launched modules
        scheduler_daemon.modules_manager.stop_all()

    def test_conf_receiver(self):
        """ Test load new conf in receiver

        :return: None
        """
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')

        args = {
            'env_file': self.env_filename,
            'alignak_name': 'my-alignak', 'daemon_name': 'unset',
        }
        receiv = receiverdaemon(**args)
        receiv.load_modules_manager()
        if hasattr(receiv, 'modules'):
            assert 0 == len(receiv.modules)

        for satellite in self._arbiter.dispatcher.satellites:
            if satellite.type == 'receiver':
                receiv.new_conf = satellite.cfg
        receiv.setup_new_conf()
        self.show_logs()
        assert 1 == len(receiv.modules)
        assert receiv.modules[0].module_alias == 'Example'
        assert receiv.modules[0].option_3 == 'foobar'
        # check get hosts
        # Two hosts declared in the configuration
        # On host provided by the Example module loaded in the arbiter
        assert len(receiv.hosts_schedulers) == 3
        assert len(receiv.schedulers) == 1

        # send new conf, so it's the second time. This test the cleanup
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')
        for satellite in self._arbiter.dispatcher.satellites:
            if satellite.type == 'receiver':
                receiv.new_conf = satellite.cfg
        receiv.setup_new_conf()
        assert len(receiv.schedulers) == 1

        # Stop launched modules
        receiv.modules_manager.stop_all()

    def test_conf_poller(self):
        """ Test load new conf in poller

        :return: None
        """
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')

        args = {
            'env_file': self.env_filename,
            'alignak_name': 'my-alignak', 'daemon_name': 'unset',
        }
        poller = pollerdaemon(**args)
        poller.load_modules_manager()
        if hasattr(poller, 'modules'):
            assert 0 == len(poller.modules)

        for satellite in self._arbiter.dispatcher.satellites:
            if satellite.type == 'poller':
                poller.new_conf = satellite.cfg
        poller.setup_new_conf()
        assert 1 == len(poller.modules)
        assert poller.modules[0].module_alias == 'Example'
        assert poller.modules[0].option_1 == 'foo'
        assert poller.modules[0].option_2 == 'bar'
        assert poller.modules[0].option_3 == 'foobar'
        assert len(poller.schedulers) == 1

        # send new conf, so it's the second time. This test the cleanup
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')
        for satellite in self._arbiter.dispatcher.satellites:
            if satellite.type == 'poller':
                poller.new_conf = satellite.cfg
        poller.setup_new_conf()
        assert len(poller.schedulers) == 1

        # Stop launched modules
        poller.modules_manager.stop_all()

    def test_conf_broker(self):
        """ Test load new conf in broker

        :return: None
        """
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')

        args = {
            'env_file': self.env_filename,
            'alignak_name': 'my-alignak', 'daemon_name': 'broker-master',
        }
        broker = brokerdaemon(**args)
        broker.load_modules_manager()
        assert 1 == len(broker.modules)

        broker_link = None
        for satellite in self._arbiter.dispatcher.satellites:
            if satellite.name == 'broker-master':
                broker_link = satellite
                broker.new_conf = satellite.cfg
                break
        assert broker_link is not None
        # Simulate the daemons HTTP interface (very simple simulation !)
        with requests_mock.mock() as mockreq:
            mockreq.get('http://127.0.0.1:7768/ping', json='pong')
            mockreq.get('http://127.0.0.1:7768/get_running_id', json=123456.123456)
            mockreq.get('http://127.0.0.1:7768/fill_initial_broks', json=[])
            mockreq.get('http://127.0.0.1:7768/get_managed_configurations', json={})
            
            broker.setup_new_conf()

            # Check modules received configuration
            assert 1 == len(broker.modules)
            print("Modules: %s" % broker.modules)
            print(" - : %s" % broker.modules[0].__dict__)
            assert broker.modules[0].module_alias == 'Example'
            assert broker.modules[0].option_1 == 'foo'
            assert broker.modules[0].option_2 == 'bar'
            assert broker.modules[0].option_3 == 'foobar'
            assert len(broker.schedulers) == 1
            if broker_link.manage_arbiters:
                assert len(broker.arbiters) == 1
            else:
                assert len(broker.arbiters) == 0
            assert len(broker.pollers) == 1
            assert len(broker.reactionners) == 1
            assert len(broker.receivers) == 1

        # send new conf, so it's the second time. This tests the cleanup
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')
        broker_link = None
        for satellite in self._arbiter.dispatcher.satellites:
            if satellite.type == 'broker':
                broker_link = satellite
                broker.new_conf = satellite.cfg
                break
        assert broker_link is not None

        # Simulate the daemons HTTP interface (very simple simulation !)
        with requests_mock.mock() as mockreq:
            mockreq.get('http://127.0.0.1:7768/ping', json='pong')
            mockreq.get('http://127.0.0.1:7768/get_running_id', json=123456.123456)
            mockreq.get('http://127.0.0.1:7768/fill_initial_broks', json=[])
            mockreq.get('http://127.0.0.1:7768/get_managed_configurations', json={})

            broker.setup_new_conf()
            assert len(broker.schedulers) == 1
            if broker_link.manage_arbiters:
                assert len(broker.arbiters) == 1
            else:
                assert len(broker.arbiters) == 0
            assert len(broker.pollers) == 1
            assert len(broker.reactionners) == 1
            assert len(broker.receivers) == 1

            # Stop launched modules
            broker.modules_manager.stop_all()

    def test_conf_reactionner(self):
        """ Test load new conf in reactionner

        :return: None
        """
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')

        args = {
            'env_file': self.env_filename,
            'alignak_name': 'my-alignak', 'daemon_name': 'unset',
        }
        reac = reactionnerdaemon(**args)
        reac.load_modules_manager()
        if hasattr(reac, 'modules'):
            assert 0 == len(reac.modules)

        for satellite in self._arbiter.dispatcher.satellites:
            if satellite.type == 'reactionner':
                reac.new_conf = satellite.cfg
        reac.setup_new_conf()
        assert 1 == len(reac.modules)
        assert reac.modules[0].module_alias == 'Example'
        assert reac.modules[0].option_1 == 'foo'
        assert reac.modules[0].option_2 == 'bar'
        assert reac.modules[0].option_3 == 'foobar'
        assert len(reac.schedulers) == 1

        # send new conf, so it's the second time. This test the cleanup
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')
        for satellite in self._arbiter.dispatcher.satellites:
            if satellite.type == 'reactionner':
                reac.new_conf = satellite.cfg
        reac.setup_new_conf()
        assert len(reac.schedulers) == 1

        # Stop launched modules
        reac.modules_manager.stop_all()
