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
This file contains the test for the Alignak configuration checks
"""
import os
import re
import time
import unittest2
from .alignak_test import AlignakTest
import pytest


class TestConfigShinken(AlignakTest):
    """
    This class tests the configuration
    """
    def setUp(self):
        super(TestConfigShinken, self).setUp()

        self.set_unit_tests_logger_level()

    def test_config_ok(self):
        """ Default configuration has no loading problems ...

        :return: None
        """
        self.setup_with_file('cfg/_shinken/_main.cfg')
        self.show_logs()
        assert self.conf_is_correct

        # No error messages
        print(self.configuration_errors)
        assert len(self.configuration_errors) == 0
        # No warning messages
        print(self.configuration_warnings)
        assert len(self.configuration_warnings) == 3
        # l = [
        #     u"Some hosts exist in the realm 'France' but no broker is defined for this realm",
        #     u"Added a broker (broker-France, http://127.0.0.1:7772/) for the realm 'France'",
        #     u'Host graphite use/inherit from an unknown template: graphite ! from: /home/alignak/alignak/test/cfg/_shinken/hosts/graphite.cfg:1'
        # ]
        self.assert_any_cfg_log_match(
            "Host graphite use/inherit from an unknown template: graphite ! "
        )
        self.assert_any_cfg_log_match(
            "Some hosts exist in the realm 'France' but no broker is defined for this realm"
        )
        self.assert_any_cfg_log_match(re.escape(
            "Added a broker (broker-France, http://127.0.0.1:7772/) for the realm 'France'"
        ))

        # Arbiter named as in the configuration
        assert self._arbiter.conf.conf_is_correct
        arbiter_link = self._arbiter.conf.arbiters.find_by_name('arbiter-master')
        assert arbiter_link is not None
        assert arbiter_link.configuration_errors == []
        assert arbiter_link.configuration_warnings == []

        # Scheduler named as in the configuration
        assert self._arbiter.conf.conf_is_correct
        scheduler_link = self._arbiter.conf.schedulers.find_by_name('scheduler-master')
        assert scheduler_link is not None
        # Scheduler configuration is ok
        # Note tht it may happen that the configuration is not sent to the scheduler-master
        # assert self._scheduler.pushed_conf.conf_is_correct

        # Broker, Poller, Reactionner named as in the configuration
        link = self._arbiter.conf.brokers.find_by_name('broker-master')
        assert link is not None
        link = self._arbiter.conf.pollers.find_by_name('poller-master')
        assert link is not None
        link = self._arbiter.conf.reactionners.find_by_name('reactionner-master')
        assert link is not None

        # Receiver - no default receiver created
        link = self._arbiter.conf.receivers.find_by_name('receiver-master')
        assert link is not None

        for item in self._arbiter.conf.commands:
            print(("Command: %s" % item))
        assert len(self._arbiter.conf.commands) == 106

        for item in self._arbiter.conf.timeperiods:
            print(("Timeperiod: %s" % item))
        assert len(self._arbiter.conf.timeperiods) == 4

        for item in self._arbiter.conf.contacts:
            print(("Contact: %s" % item))
        assert len(self._arbiter.conf.contacts) == 7

        for item in self._arbiter.conf.contactgroups:
            print(("Contacts group: %s" % item))
        assert len(self._arbiter.conf.contactgroups) == 3

        for item in self._arbiter.conf.hosts:
            print(("Host: %s" % item))
        assert len(self._arbiter.conf.hosts) == 13

        for item in self._arbiter.conf.hostgroups:
            print(("Hosts group: %s" % item))
        assert len(self._arbiter.conf.hostgroups) == 8

        for item in self._arbiter.conf.services:
            print(("Service: %s" % item))
        assert len(self._arbiter.conf.services) == 94

        for item in self._arbiter.conf.servicegroups:
            print(("Services group: %s" % item))
        assert len(self._arbiter.conf.servicegroups) == 5
