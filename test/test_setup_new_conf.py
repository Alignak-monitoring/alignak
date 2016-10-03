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
"""
This file test load the new conf on each module
"""

import sys
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
        """
        Test load new conf in scheduler

        :return: None
        """
        # Configuration received by scheduler, so give to scheduler to load it
        sys.path.append('cfg/setup_new_conf/modules/schedulerexample.py')

        sched = schedulerdaemon('cfg/setup_new_conf/daemons/schedulerd.ini', False, False, False,
                                '/tmp/scheduler.log')
        sched.load_config_file()
        sched.load_modules_manager()
        if hasattr(sched, 'modules'):
            self.assertEqual(0, len(sched.modules))

        conf_dict = open('cfg/setup_new_conf/scheduler_new_conf.dict', 'r').read()
        sched.new_conf = eval(conf_dict)
        sched.setup_new_conf()
        self.assertEqual(1, len(sched.modules))
        self.assertEqual(sched.modules[0].module_alias, 'schedulerexample')
        self.assertEqual(sched.modules[0].myvar, 'tataouine')
        self.assertEqual(10, len(sched.conf.hosts))

    def test_conf_receiver(self):
        """
        Test load new conf in receiver

        :return: None
        """
        sys.path.append('cfg/setup_new_conf/modules/receiverexample.py')

        receiv = receiverdaemon('cfg/setup_new_conf/daemons/receiverd.ini', False, False, False,
                                '/tmp/receiver.log')
        receiv.load_config_file()
        receiv.load_modules_manager()
        if hasattr(receiv, 'modules'):
            self.assertEqual(0, len(receiv.modules))

        conf_dict = open('cfg/setup_new_conf/receiver_new_conf.dict', 'r').read()
        receiv.new_conf = eval(conf_dict)
        receiv.setup_new_conf()
        self.assertEqual(1, len(receiv.modules))
        self.assertEqual(receiv.modules[0].module_alias, 'receiverexample')
        self.assertEqual(receiv.modules[0].myvar, 'coruscant')
        # check get hosts
        self.assertGreater(len(receiv.host_assoc), 2)

    def test_conf_poller(self):
        """
        Test load new conf in poller

        :return: None
        """
        sys.path.append('cfg/setup_new_conf/modules/pollerexample.py')

        poller = pollerdaemon('cfg/setup_new_conf/daemons/pollerd.ini', False, False, False,
                              '/tmp/poller.log')
        poller.load_config_file()
        poller.load_modules_manager()
        if hasattr(poller, 'modules'):
            self.assertEqual(0, len(poller.modules))

        conf_dict = open('cfg/setup_new_conf/poller_new_conf.dict', 'r').read()
        poller.new_conf = eval(conf_dict)
        poller.setup_new_conf()
        self.assertEqual(1, len(poller.new_modules_conf))
        self.assertEqual(poller.new_modules_conf[0].module_alias, 'pollerexample')
        self.assertEqual(poller.new_modules_conf[0].myvar, 'dagobah')

    def test_conf_broker(self):
        """
        Test load new conf in broker

        :return: None
        """
        sys.path.append('cfg/setup_new_conf/modules/brokerexample.py')

        broker = brokerdaemon('cfg/setup_new_conf/daemons/brokerd.ini', False, False, False,
                              '/tmp/broker.log')
        broker.load_config_file()
        broker.load_modules_manager()
        if hasattr(broker, 'modules'):
            self.assertEqual(0, len(broker.modules))

        conf_dict = open('cfg/setup_new_conf/broker_new_conf.dict', 'r').read()
        broker.new_conf = eval(conf_dict)
        broker.setup_new_conf()
        self.assertEqual(1, len(broker.modules))
        self.assertEqual(broker.modules[0].module_alias, 'brokerexample')
        self.assertEqual(broker.modules[0].myvar, 'hoth')

    def test_conf_reactionner(self):
        """
        Test load new conf in reactionner

        :return: None
        """
        sys.path.append('cfg/setup_new_conf/modules/reactionnerexample.py')

        reac = reactionnerdaemon('cfg/setup_new_conf/daemons/reactionnerd.ini', False, False,
                                 False, '/tmp/reactionner.log')
        reac.load_config_file()
        reac.load_modules_manager()
        if hasattr(reac, 'modules'):
            self.assertEqual(0, len(reac.modules))

        conf_dict = open('cfg/setup_new_conf/reactionner_new_conf.dict', 'r').read()
        reac.new_conf = eval(conf_dict)
        reac.setup_new_conf()
        self.assertEqual(1, len(reac.new_modules_conf))
        self.assertEqual(reac.new_modules_conf[0].module_alias, 'reactionnerexample')
        self.assertEqual(reac.new_modules_conf[0].myvar, 'naboo')
