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
        self.setup_with_file('cfg/cfg_default.cfg')

        sched = schedulerdaemon('cfg/setup_new_conf/daemons/schedulerd.ini', False, False, False,
                                '/tmp/scheduler.log')
        sched.load_config_file()
        sched.load_modules_manager()
        if hasattr(sched, 'modules'):
            self.assertEqual(0, len(sched.modules))

        for scheduler in self.arbiter.dispatcher.schedulers:
            sched.new_conf = scheduler.conf_package
        sched.setup_new_conf()
        self.assertEqual(1, len(sched.modules))
        self.assertEqual(sched.modules[0].module_alias, 'Example')
        self.assertEqual(sched.modules[0].option_3, 'foobar')
        self.assertEqual(2, len(sched.conf.hosts))
        # Stop launched modules
        sched.modules_manager.stop_all()

    def test_conf_receiver(self):
        """ Test load new conf in receiver

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        receiv = receiverdaemon('cfg/setup_new_conf/daemons/receiverd.ini', False, False, False,
                                '/tmp/receiver.log')
        receiv.load_config_file()
        receiv.load_modules_manager()
        if hasattr(receiv, 'modules'):
            self.assertEqual(0, len(receiv.modules))

        for satellite in self.arbiter.dispatcher.satellites:
            if satellite.get_my_type() == 'receiver':
                receiv.new_conf = satellite.cfg
        receiv.setup_new_conf()
        self.assertEqual(1, len(receiv.modules))
        self.assertEqual(receiv.modules[0].module_alias, 'Example')
        self.assertEqual(receiv.modules[0].option_3, 'foobar')
        # check get hosts
        self.assertEqual(len(receiv.host_assoc), 2)
        # Stop launched modules
        receiv.modules_manager.stop_all()

    def test_conf_poller(self):
        """ Test load new conf in poller

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        poller = pollerdaemon('cfg/setup_new_conf/daemons/pollerd.ini', False, False, False,
                              '/tmp/poller.log')
        poller.load_config_file()
        poller.load_modules_manager()
        if hasattr(poller, 'modules'):
            self.assertEqual(0, len(poller.modules))

        for satellite in self.arbiter.dispatcher.satellites:
            if satellite.get_my_type() == 'poller':
                poller.new_conf = satellite.cfg
        poller.setup_new_conf()
        self.assertEqual(1, len(poller.new_modules_conf))
        self.assertEqual(poller.new_modules_conf[0].module_alias, 'Example')
        self.assertEqual(poller.new_modules_conf[0].option_3, 'foobar')
        # Stop launched modules
        poller.modules_manager.stop_all()

    def test_conf_broker(self):
        """ Test load new conf in broker

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        broker = brokerdaemon('cfg/setup_new_conf/daemons/brokerd.ini', False, False, False,
                              '/tmp/broker.log')
        broker.load_config_file()
        broker.load_modules_manager()
        if hasattr(broker, 'modules'):
            self.assertEqual(0, len(broker.modules))

        for satellite in self.arbiter.dispatcher.satellites:
            if satellite.get_my_type() == 'broker':
                broker.new_conf = satellite.cfg
        broker.setup_new_conf()
        self.assertEqual(1, len(broker.modules))
        self.assertEqual(broker.modules[0].module_alias, 'Example')
        self.assertEqual(broker.modules[0].option_3, 'foobar')
        # Stop launched modules
        broker.modules_manager.stop_all()

    def test_conf_reactionner(self):
        """ Test load new conf in reactionner

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        reac = reactionnerdaemon('cfg/setup_new_conf/daemons/reactionnerd.ini', False, False,
                                 False, '/tmp/reactionner.log')
        reac.load_config_file()
        reac.load_modules_manager()
        if hasattr(reac, 'modules'):
            self.assertEqual(0, len(reac.modules))

        for satellite in self.arbiter.dispatcher.satellites:
            if satellite.get_my_type() == 'reactionner':
                reac.new_conf = satellite.cfg
        reac.setup_new_conf()
        self.assertEqual(1, len(reac.new_modules_conf))
        self.assertEqual(reac.new_modules_conf[0].module_alias, 'Example')
        self.assertEqual(reac.new_modules_conf[0].option_3, 'foobar')
        # Stop launched modules
        reac.modules_manager.stop_all()
