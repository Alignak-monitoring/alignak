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
from alignak_test import AlignakTest
import pytest


class TestPropertyOverride(AlignakTest):

    def setUp(self):
        self.setup_with_file('cfg/cfg_property_override.cfg')
        assert self.conf_is_correct
        self._sched = self._scheduler
        
    def test_service_property_override(self):
        """ Property override """
        self.print_header()

        svc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv-svc")
        svc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv-svc")
        svc1proc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "proc proc1")
        svc1proc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "proc proc2")
        svc2proc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "proc proc1")
        svc2proc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "proc proc2")
        tp24x7 = self._sched.timeperiods.find_by_name("24x7")
        tp_none = self._sched.timeperiods.find_by_name("none")
        tptest = self._sched.timeperiods.find_by_name("testperiod")
        cgtest = self._sched.contactgroups.find_by_name("test_contact")
        cgadm = self._sched.contactgroups.find_by_name("admins")
        cmdsvc = self._sched.commands.find_by_name("check_service")
        cmdtest = self._sched.commands.find_by_name("dummy_command")
        svc12 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv-svc2")
        svc22 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv-svc2")

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
            assert self._sched.timeperiods[tp24x7.uuid].get_name() == \
                             self._sched.timeperiods[svc.maintenance_period].get_name()
            assert 1 == svc.retry_interval
            assert self._sched.commands[cmdsvc.uuid] is \
                          self._sched.commands[svc.check_command.command.uuid]
            assert ["w","u","c","r","f","s"] == svc.notification_options
            assert True is svc.notifications_enabled

        # Check overriden properies value
        for svc in (svc2, svc2proc2, svc22):
            assert ["admins"] == svc.contact_groups
            assert self._sched.timeperiods[tptest.uuid].get_name() == \
                             self._sched.timeperiods[svc.maintenance_period].get_name()
            assert 3 == svc.retry_interval
            assert self._sched.commands[cmdtest.uuid] is \
                          self._sched.commands[svc.check_command.command.uuid]
            assert ["c","r"] == svc.notification_options
            assert False is svc.notifications_enabled


class TestPropertyOverrideConfigBroken(AlignakTest):

    def test_service_property_override_errors(self):
        """ Property override broken """
        self.print_header()

        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_property_override_broken.cfg')
        assert not self.conf_is_correct

        self.assert_any_cfg_log_match(
            "Configuration in host::test_host_02 is incorrect;")
        self.assert_any_cfg_log_match(
            "Error: invalid service override syntax: fake value")
        self.assert_any_cfg_log_match(
            "Error: trying to override property 'retry_interval' on service "
            "'fakesrv' but it's unknown for this host")
        self.assert_any_cfg_log_match(
            "Error: trying to override 'host_name', a forbidden property for service 'proc proc2'")
        self.assert_any_cfg_log_match(
            "hosts configuration is incorrect!")


if __name__ == '__main__':
    AlignakTest.main()
