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
from alignak_test import unittest, AlignakTest


class TestPropertyOverride(AlignakTest):

    def setUp(self):
        self.setup_with_file('cfg/cfg_property_override.cfg')
        self.assertTrue(self.conf_is_correct)
        self._sched = self.schedulers['scheduler-master'].sched
        
    def test_service_property_override(self):
        """ Property override """
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
        self.assertIsNot(svc1, None)
        self.assertIsNot(svc2, None)
        self.assertIsNot(svc1proc1, None)
        self.assertIsNot(svc1proc2, None)
        self.assertIsNot(svc2proc1, None)
        self.assertIsNot(svc2proc2, None)
        self.assertIsNot(tp24x7, None)
        self.assertIsNot(tptest, None)
        self.assertIsNot(cgtest, None)
        self.assertIsNot(cgadm, None)
        self.assertIsNot(cmdsvc, None)
        self.assertIsNot(cmdtest, None)
        self.assertIsNot(svc12, None)
        self.assertIsNot(svc22, None)

        # Check non overriden properies value
        for svc in (svc1, svc1proc1, svc1proc2, svc2proc1, svc12):
            self.assertEqual(["test_contact"], svc.contact_groups)
            self.assertEqual(self._sched.timeperiods[tp24x7.uuid].get_name(),
                             self._sched.timeperiods[svc.maintenance_period].get_name())
            self.assertEqual(1, svc.retry_interval)
            self.assertIs(self._sched.commands[cmdsvc.uuid],
                          self._sched.commands[svc.check_command.command.uuid])
            self.assertEqual(["w","u","c","r","f","s"], svc.notification_options)
            self.assertIs(True, svc.notifications_enabled)

        # Check overriden properies value
        for svc in (svc2, svc2proc2, svc22):
            self.assertEqual(["admins"], svc.contact_groups)
            self.assertEqual(self._sched.timeperiods[tptest.uuid].get_name(),
                             self._sched.timeperiods[svc.maintenance_period].get_name())
            self.assertEqual(3, svc.retry_interval)
            self.assertIs(self._sched.commands[cmdtest.uuid],
                          self._sched.commands[svc.check_command.command.uuid])
            self.assertEqual(["c","r"], svc.notification_options)
            self.assertIs(False, svc.notifications_enabled)


class TestPropertyOverrideConfigBroken(AlignakTest):

    def test_service_property_override_errors(self):
        """ Property override broken """
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/cfg_property_override_broken.cfg')
        self.assertFalse(self.conf_is_correct)

        self.assertIn("Configuration in host::test_host_02 is incorrect; "
                      "from: cfg/default/daemons/reactionner-master.cfg:55",
                      self.configuration_errors)
        self.assertIn("Error: invalid service override syntax: fake value",
                      self.configuration_errors)
        self.assertIn("Error: trying to override property 'retry_interval' "
                      "on service 'fakesrv' but it's unknown for this host",
                      self.configuration_errors)
        self.assertIn("Error: trying to override 'host_name', a forbidden property "
                      "for service 'proc proc2'",
                      self.configuration_errors)
        self.assertIn("hosts configuration is incorrect!",
                      self.configuration_errors)


if __name__ == '__main__':
    unittest.main()
