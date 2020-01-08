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
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Christophe Simon, geektophe@gmail.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe SIMON, christophe.simon@dailymotion.com

#  This file is part of Shinken.
#
#  Shinken is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Shinken is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Shinken.  If not, see <http://www.gnu.org/licenses/>.

#
# This file is used to test object properties overriding.
#

import re
from .alignak_test import AlignakTest
import pytest


class TestPropertyOverride(AlignakTest):

    def setUp(self):
        super(TestPropertyOverride, self).setUp()
        self.setup_with_file('cfg/cfg_property_override.cfg')
        assert self.conf_is_correct
        self._sched = self._scheduler

    def test_service_property_override(self):
        """ Property override """
        svc1 = self._arbiter.conf.services.find_srv_by_name_and_hostname("test_host_01", "srv-svc")
        svc2 = self._arbiter.conf.services.find_srv_by_name_and_hostname("test_host_02", "srv-svc")
        svc1proc1 = self._arbiter.conf.services.find_srv_by_name_and_hostname("test_host_01", "proc proc1")
        svc1proc2 = self._arbiter.conf.services.find_srv_by_name_and_hostname("test_host_01", "proc proc2")
        svc2proc1 = self._arbiter.conf.services.find_srv_by_name_and_hostname("test_host_02", "proc proc1")
        svc2proc2 = self._arbiter.conf.services.find_srv_by_name_and_hostname("test_host_02", "proc proc2")
        tp24x7 = self._arbiter.conf.timeperiods.find_by_name("24x7")
        tp_none = self._arbiter.conf.timeperiods.find_by_name("none")
        tptest = self._arbiter.conf.timeperiods.find_by_name("testperiod")
        cgtest = self._arbiter.conf.contactgroups.find_by_name("test_contact")
        cgadm = self._arbiter.conf.contactgroups.find_by_name("admins")
        cmdsvc = self._arbiter.conf.commands.find_by_name("check_service")
        cmdtest = self._arbiter.conf.commands.find_by_name("dummy_command")
        svc12 = self._arbiter.conf.services.find_srv_by_name_and_hostname("test_host_01", "srv-svc2")
        svc22 = self._arbiter.conf.services.find_srv_by_name_and_hostname("test_host_02", "srv-svc2")

        # Checks we got the objects we need
        assert svc1 is not None
        assert svc2 is not None
        assert svc1proc1 is not None
        assert svc1proc2 is not None
        assert svc2proc1 is not None
        assert svc2proc2 is not None
        assert tp24x7 is not None
        assert tptest is not None
        assert cgtest is not None
        assert cgadm is not None
        assert cmdsvc is not None
        assert cmdtest is not None
        assert svc12 is not None
        assert svc22 is not None

        # Check non overriden properies value
        for svc in (svc1, svc1proc1, svc1proc2, svc2proc1, svc12):
            assert ["test_contact"] == svc.contact_groups
            assert self._arbiter.conf.timeperiods[tp24x7.uuid].get_name() == \
                   self._arbiter.conf.timeperiods[svc.maintenance_period].get_name()
            assert 1 == svc.retry_interval
            assert self._arbiter.conf.commands[cmdsvc.uuid] is \
                   self._arbiter.conf.commands[svc.check_command.command.uuid]
            # The list may not be in this order!
            # assert ["w", "u", "x", "c", "r", "f", "s"] == svc.notification_options
            assert 7 == len(svc.notification_options)
            assert 'x' in svc.notification_options
            assert 'f' in svc.notification_options
            assert 'u' in svc.notification_options
            assert 'r' in svc.notification_options
            assert 's' in svc.notification_options
            assert 'w' in svc.notification_options
            assert 'c' in svc.notification_options
            assert True is svc.notifications_enabled

        # Check overriden properies value
        for svc in (svc2, svc2proc2, svc22):
            assert ["admins"] == svc.contact_groups
            assert self._arbiter.conf.timeperiods[tptest.uuid].get_name() == \
                   self._arbiter.conf.timeperiods[svc.maintenance_period].get_name()
            assert 3 == svc.retry_interval
            assert self._arbiter.conf.commands[cmdtest.uuid] is \
                   self._arbiter.conf.commands[svc.check_command.command.uuid]
            assert ["c","r"] == svc.notification_options
            assert False is svc.notifications_enabled


class TestPropertyOverrideConfigBroken(AlignakTest):

    def setUp(self):
        super(TestPropertyOverrideConfigBroken, self).setUp()

    def test_service_property_override_errors(self):
        """ Property override broken """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_property_override_broken.cfg')
        assert not self.conf_is_correct

        self.assert_any_cfg_log_match(re.escape(
            "[host::test_host_02] Configuration is incorrect;"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[host::test_host_02] invalid service override syntax: fake value"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[host::test_host_02] trying to override property 'retry_interval' on service "
            "'fakesrv' but it's unknown for this host"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[host::test_host_02] trying to override 'host_name', a forbidden property for service 'proc proc2'"
        ))
        self.assert_any_cfg_log_match(
            "hosts configuration is incorrect!")
