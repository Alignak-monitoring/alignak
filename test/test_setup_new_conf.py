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
This file test load the new conf on each module
"""

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
    def test_conf_scheduler(self):
        """ Test load new conf in scheduler

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')

        args = {
            'env_file': self.env_filename,
            'alignak_name': 'my-alignak', 'daemon_name': 'unset',
        }
        sched = schedulerdaemon(**args)
        sched.load_modules_manager()

        scheduler_link = None
        for satellite in self.arbiter.dispatcher.schedulers:
            scheduler_link = satellite
            sched.new_conf = satellite.cfg
            break
        assert scheduler_link is not None

        sched.setup_new_conf()
        assert 1 == len(sched.modules)
        assert sched.modules[0].module_alias == 'Example'
        assert sched.modules[0].option_1 == 'foo'
        assert sched.modules[0].option_2 == 'bar'
        assert sched.modules[0].option_3 == 'foobar'
        for host in sched.conf.hosts:
            print("Host: %s" % host)
        # Two hosts declared in the configuration
        # One host provided by the Example module loaded in the arbiter
        assert 3 == len(sched.conf.hosts)
        assert len(sched.pollers) == 1
        assert len(sched.reactionners) == 1
        assert len(sched.brokers) == 1
        assert len(sched.schedulers) == 1
        if scheduler_link.manage_arbiters:
            assert len(sched.arbiters) == 1
        else:
            assert len(sched.arbiters) == 0
        assert len(sched.receivers) == 0

        # send new conf, so it's the second time. This test the cleanup
        self.setup_with_file('cfg/cfg_default_with_modules.cfg')
        scheduler_link = None
        for satellite in self.arbiter.dispatcher.schedulers:
            scheduler_link = satellite
            sched.new_conf = satellite.cfg
            break
        assert scheduler_link is not None

        sched.setup_new_conf()
        assert 1 == len(sched.modules)
        assert sched.modules[0].module_alias == 'Example'
        assert sched.modules[0].option_1 == 'foo'
        assert sched.modules[0].option_2 == 'bar'
        assert sched.modules[0].option_3 == 'foobar'
        for host in sched.conf.hosts:
            print("Host: %s" % host)
        # Two hosts declared in the configuration
        # One host provided by the Example module loaded in the arbiter
        assert 3 == len(sched.conf.hosts)
        assert len(sched.pollers) == 1
        assert len(sched.reactionners) == 1
        assert len(sched.brokers) == 1
        assert len(sched.schedulers) == 1
        if scheduler_link.manage_arbiters:
            assert len(sched.arbiters) == 1
        else:
            assert len(sched.arbiters) == 0
        assert len(sched.receivers) == 0

        # Stop launched modules
        sched.modules_manager.stop_all()

    def test_conf_receiver(self):
        """ Test load new conf in receiver

        :return: None
        """
        self.print_header()
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

        for satellite in self.arbiter.dispatcher.satellites:
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
        assert len(receiv.host_assoc) == 3
        assert len(receiv.schedulers) == 1

        # send new conf, so it's the second time. This test the cleanup
        self.setup_with_file('cfg/cfg_default_with_modules.cfg')
        for satellite in self.arbiter.dispatcher.satellites:
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
        self.print_header()
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

        for satellite in self.arbiter.dispatcher.satellites:
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
        self.setup_with_file('cfg/cfg_default_with_modules.cfg')
        for satellite in self.arbiter.dispatcher.satellites:
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
        self.print_header()
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')

        args = {
            'env_file': self.env_filename,
            'alignak_name': 'my-alignak', 'daemon_name': 'broker-test',
        }
        broker = brokerdaemon(**args)
        broker.load_modules_manager()
        assert 0 == len(broker.modules)

        broker_link = None
        for satellite in self.arbiter.dispatcher.satellites:
            if satellite.type == 'broker':
                broker_link = satellite
                broker.new_conf = satellite.cfg
                break
        assert broker_link is not None
        broker.setup_new_conf()
        assert 1 == len(broker.modules)
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
        assert len(broker.receivers) == 0

        # send new conf, so it's the second time. This tests the cleanup
        self.setup_with_file('cfg/cfg_default_with_modules.cfg')
        broker_link = None
        for satellite in self.arbiter.dispatcher.satellites:
            if satellite.type == 'broker':
                broker_link = satellite
                broker.new_conf = satellite.cfg
                break
        assert broker_link is not None
        broker.setup_new_conf()
        assert len(broker.schedulers) == 1
        if broker_link.manage_arbiters:
            assert len(broker.arbiters) == 1
        else:
            assert len(broker.arbiters) == 0
        assert len(broker.pollers) == 1
        assert len(broker.reactionners) == 1
        assert len(broker.receivers) == 0

        # Stop launched modules
        broker.modules_manager.stop_all()

    def test_conf_reactionner(self):
        """ Test load new conf in reactionner

        :return: None
        """
        self.print_header()
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

        for satellite in self.arbiter.dispatcher.satellites:
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
        self.setup_with_file('cfg/cfg_default_with_modules.cfg')
        for satellite in self.arbiter.dispatcher.satellites:
            if satellite.type == 'reactionner':
                reac.new_conf = satellite.cfg
        reac.setup_new_conf()
        assert len(reac.schedulers) == 1

        # Stop launched modules
        reac.modules_manager.stop_all()
