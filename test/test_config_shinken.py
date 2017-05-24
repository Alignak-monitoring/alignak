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
This file contains the test for the Alignak configuration checks
"""
import os
import re
import time
import unittest2
from alignak_test import AlignakTest
import pytest


class TestConfig(AlignakTest):
    """
    This class tests the configuration
    """

    def test_config_ok(self):
        """ Default configuration has no loading problems ...

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/_shinken/_main.cfg')
        assert self.conf_is_correct

        # No error messages
        print self.configuration_errors
        assert len(self.configuration_errors) == 0
        # No warning messages
        print self.configuration_warnings
        assert len(self.configuration_warnings) == 16
        assert self.configuration_warnings == [
            u'Guessing the property modules_dir type because it is not in Config object properties',
            u'Guessing the property ca_cert type because it is not in Config object properties',
            u'Guessing the property daemon_enabled type because it is not in Config object properties',
            u'Guessing the property lock_file type because it is not in Config object properties',
            u'Guessing the property server_cert type because it is not in Config object properties',
            u'Guessing the property workdir type because it is not in Config object properties',
            u'Guessing the property hard_ssl_name_check type because it is not in Config object properties',
            u'Guessing the property server_key type because it is not in Config object properties',
            u'Guessing the property http_backend type because it is not in Config object properties',
            u'Guessing the property local_log type because it is not in Config object properties',
            u'Guessing the property use_ssl type because it is not in Config object properties',
            u'Host graphite use/inherit from an unknown template: graphite ! from: cfg/_shinken/hosts/graphite.cfg:1',
            'Guessing the property hostgroup_name type because it is not in Escalation object properties',
            "Guessed the property hostgroup_name type as a <type 'unicode'>",
            u'Guessing the property direct_routing type because it is not in ReceiverLink object properties',
            u"Guessed the property direct_routing type as a <type 'unicode'>",
            # u"Some hosts exist in the realm 'France' but no broker is defined for this realm",
            # u"Added a broker in the realm 'France'",
        ]

        # Arbiter named as in the configuration
        assert self.arbiter.conf.conf_is_correct
        arbiter_link = self.arbiter.conf.arbiters.find_by_name('arbiter-master')
        assert arbiter_link is not None
        assert arbiter_link.configuration_errors == []
        assert arbiter_link.configuration_warnings == []

        # Scheduler named as in the configuration
        assert self.arbiter.conf.conf_is_correct
        scheduler_link = self.arbiter.conf.schedulers.find_by_name('scheduler-master')
        assert scheduler_link is not None
        # Scheduler configuration is ok
        assert self.schedulers['scheduler-master'].sched.conf.conf_is_correct

        # Broker, Poller, Reactionner named as in the configuration
        link = self.arbiter.conf.brokers.find_by_name('broker-master')
        assert link is not None
        link = self.arbiter.conf.pollers.find_by_name('poller-master')
        assert link is not None
        link = self.arbiter.conf.reactionners.find_by_name('reactionner-master')
        assert link is not None

        # Receiver - no default receiver created
        link = self.arbiter.conf.receivers.find_by_name('receiver-master')
        assert link is not None

        for item in self.arbiter.conf.commands:
            print("Command: %s" % item)
        assert len(self.arbiter.conf.commands) == 106

        for item in self.arbiter.conf.timeperiods:
            print("Timeperiod: %s" % item)
        assert len(self.arbiter.conf.timeperiods) == 4

        for item in self.arbiter.conf.contacts:
            print("Contact: %s" % item)
        assert len(self.arbiter.conf.contacts) == 7

        for item in self.arbiter.conf.contactgroups:
            print("Contacts group: %s" % item)
        assert len(self.arbiter.conf.contactgroups) == 3

        for item in self.arbiter.conf.hosts:
            print("Host: %s" % item)
        assert len(self.arbiter.conf.hosts) == 13

        for item in self.arbiter.conf.hostgroups:
            print("Hosts group: %s" % item)
        assert len(self.arbiter.conf.hostgroups) == 8

        for item in self.arbiter.conf.services:
            print("Service: %s" % item)
        assert len(self.arbiter.conf.services) == 94

        for item in self.arbiter.conf.servicegroups:
            print("Services group: %s" % item)
        assert len(self.arbiter.conf.servicegroups) == 5
