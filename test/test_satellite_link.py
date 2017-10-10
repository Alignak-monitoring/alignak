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

from alignak_test import AlignakTest
from alignak.objects.arbiterlink import ArbiterLink
from alignak.objects.schedulerlink import SchedulerLink
from alignak.objects.brokerlink import BrokerLink
from alignak.objects.reactionnerlink import ReactionnerLink
from alignak.objects.receiverlink import ReceiverLink
from alignak.objects.pollerlink import PollerLink


class template_DaemonLink_get_name():
    def get_link(self):
        cls = self.daemon_link
        return cls({})

    def test_get_name(self):
        link = self.get_link()
        print("Link: %s / %s" % (type(link), link.__dict__))
        link.fill_default()

        print("Name: %s / %s" % (link.type, link.get_name()))
        print("Config: %s" % (link.give_satellite_cfg()))
        print("Config: %s" % (link.have_conf()))
        assert False == link.have_conf()
        try:
            self.assertEqual("Unnamed {0}".format(self.daemon_link.my_type), link.get_name())
        except AttributeError:
            self.assertTrue(False, "get_name should not raise AttributeError")


class Test_ArbiterLink_get_name(template_DaemonLink_get_name, AlignakTest):
    """Test satellite link arbiter"""
    daemon_link = ArbiterLink


class Test_SchedulerLink_get_name(template_DaemonLink_get_name, AlignakTest):
    """Test satellite link scheduler"""
    daemon_link = SchedulerLink


class Test_BrokerLink_get_name(template_DaemonLink_get_name, AlignakTest):
    """Test satellite link broker"""
    daemon_link = BrokerLink


class Test_ReactionnerLink_get_name(template_DaemonLink_get_name, AlignakTest):
    """Test satellite link reactionner"""
    daemon_link = ReactionnerLink


class Test_ReceiverLink_get_name(template_DaemonLink_get_name, AlignakTest):
    """Test satellite link receiver"""
    daemon_link = ReceiverLink


class Test_PollerLink_get_name(template_DaemonLink_get_name, AlignakTest):
    """Test satellite link poller"""
    daemon_link = PollerLink


if __name__ == '__main__':
    AlignakTest.main()
