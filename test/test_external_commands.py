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
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Frédéric MOHIER, frederic.mohier@ipmfrance.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Gerhard Lausser, gerhard.lausser@consol.de

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
# This file is used to test reading and processing of config files
#
import time
import unittest2 as unittest
from alignak_test import AlignakTest, time_hacker
from alignak.misc.common import DICT_MODATTR
from alignak.misc.serialization import unserialize


class TestExternalCommands(AlignakTest):
    """
    This class tests the external commands
    """
    def setUp(self):
        """
        For each test load and check the configuration
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_external_commands.cfg')
        self.assertTrue(self.conf_is_correct)

        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

        time_hacker.set_real_time()

    def test_change_and_reset_host_modattr(self):
        """
        Change and reset modified attributes for an host
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")

        # ---
        # External command: change host attribute
        excmd = '[%d] CHANGE_HOST_MODATTR;test_host_0;1' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Notifications are now disabled
        self.assertFalse(getattr(host, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute))
        self.assertEqual(1, host.modified_attributes)

        # External command: change host attribute
        excmd = '[%d] CHANGE_HOST_MODATTR;test_host_0;1' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Notifications are now enabled
        self.assertTrue(getattr(host, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute))
        self.assertEqual(0, host.modified_attributes)

        # ---
        # External command: change host attribute (non boolean attribute)
        excmd = '[%d] CHANGE_HOST_MODATTR;test_host_0;65536' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Notifications are now disabled
        self.assertEqual(65536, host.modified_attributes)

        # External command: change host attribute
        excmd = '[%d] CHANGE_HOST_MODATTR;test_host_0;65536' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Notifications are now enabled
        self.assertEqual(0, host.modified_attributes)

        # ---
        # External command: change host attribute (several attributes in one command)
        excmd = '[%d] CHANGE_HOST_MODATTR;test_host_0;3' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Notifications are now disabled
        self.assertFalse(getattr(host, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute))
        # Active checks are now disabled
        self.assertFalse(getattr(host, DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].attribute))
        self.assertEqual(3, host.modified_attributes)

        # External command: change host attribute (several attributes in one command)
        excmd = '[%d] CHANGE_HOST_MODATTR;test_host_0;3' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Notifications are now enabled
        self.assertTrue(getattr(host, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute))
        # Active checks are now enabled
        self.assertTrue(getattr(host, DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].attribute))
        self.assertEqual(0, host.modified_attributes)

    def test_change_and_reset_service_modattr(self):
        """
        Change and reset modified attributes for a service
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")

        # ---
        # External command: change service attribute
        excmd = '[%d] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;1' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Notifications are now disabled
        self.assertFalse(getattr(svc, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute))
        self.assertEqual(1, svc.modified_attributes)

        # External command: change service attribute
        excmd = '[%d] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;1' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Notifications are now enabled
        self.assertTrue(getattr(svc, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute))
        self.assertEqual(0, svc.modified_attributes)

        # ---
        # External command: change service attribute (non boolean attribute)
        excmd = '[%d] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;65536' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Notifications are now disabled
        self.assertEqual(65536, svc.modified_attributes)

        # External command: change service attribute
        excmd = '[%d] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;65536' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Notifications are now enabled
        self.assertEqual(0, svc.modified_attributes)

        # ---
        # External command: change service attribute (several attributes in one command)
        excmd = '[%d] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;3' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Notifications are now disabled
        self.assertFalse(getattr(svc, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute))
        # Active checks are now disabled
        self.assertFalse(getattr(svc, DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].attribute))
        self.assertEqual(3, svc.modified_attributes)

        # External command: change service attribute (several attributes in one command)
        excmd = '[%d] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;3' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Notifications are now enabled
        self.assertTrue(getattr(svc, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute))
        # Active checks are now enabled
        self.assertTrue(getattr(svc, DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].attribute))
        self.assertEqual(0, svc.modified_attributes)

    def test_change_and_reset_contact_modattr(self):
        """
        Change and reset modified attributes for a contact
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # A contact...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        contact = self._scheduler.contacts[host.contacts[0]]
        self.assertIsNotNone(contact)
        self.assertEqual(contact.contact_name, "test_contact")

        # ---
        # External command: change contact attribute
        excmd = '[%d] CHANGE_CONTACT_MODATTR;test_contact;1' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(1, contact.modified_attributes)

        # External command: change contact attribute
        excmd = '[%d] CHANGE_CONTACT_MODATTR;test_contact;1' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # No toggle
        self.assertEqual(1, contact.modified_attributes)

        # ---
        # External command: change contact attribute
        self.assertEqual(0, contact.modified_host_attributes)
        excmd = '[%d] CHANGE_CONTACT_MODHATTR;test_contact;1' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(1, contact.modified_host_attributes)

        # External command: change contact attribute
        excmd = '[%d] CHANGE_CONTACT_MODHATTR;test_contact;1' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # No toggle
        self.assertEqual(1, contact.modified_host_attributes)

        # ---
        # External command: change contact attribute
        self.assertEqual(0, contact.modified_service_attributes)
        excmd = '[%d] CHANGE_CONTACT_MODSATTR;test_contact;1' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(1, contact.modified_service_attributes)

        # External command: change contact attribute
        excmd = '[%d] CHANGE_CONTACT_MODSATTR;test_contact;1' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # No toggle
        self.assertEqual(1, contact.modified_service_attributes)

        # Note that the value is simply stored and not controled in any way ...

    def test_change_host_attributes(self):
        """

        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # A TP...
        tp = self._scheduler.timeperiods.find_by_name("24x7")
        self.assertEqual(tp.timeperiod_name, "24x7")
        tp2 = self._scheduler.timeperiods.find_by_name("none")
        self.assertEqual(tp2.timeperiod_name, "none")

        # A command...
        command = self._scheduler.commands.find_by_name("check-host-alive")
        self.assertEqual(command.command_name, "check-host-alive")
        command2 = self._scheduler.commands.find_by_name("check-host-alive-parent")
        self.assertEqual(command2.command_name, "check-host-alive-parent")

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        self.assertIsNotNone(host.customs)
        self.assertEqual(host.get_check_command(),
                         "check-host-alive-parent!up!$HOSTSTATE:test_router_0$")
        self.assertEqual(host.customs['_OSLICENSE'], 'gpl')
        self.assertEqual(host.customs['_OSTYPE'], 'gnulinux')
        # Todo: check if it is normal ... host.check_period is the TP uuid and not an object!
        self.assertEqual(host.check_period, tp.uuid)

        # A contact...
        contact = self._scheduler.contacts[host.contacts[0]]
        self.assertIsNotNone(contact)
        self.assertEqual(contact.contact_name, "test_contact")
        # Todo: check if it is normal ... contact.host_notification_period is the TP name
        # and not an object!
        self.assertEqual(contact.host_notification_period, tp.timeperiod_name)
        self.assertEqual(contact.service_notification_period, tp.timeperiod_name)

        #  ---
        # External command: change check command
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_HOST_CHECK_COMMAND;test_host_0;check-host-alive' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(host.get_check_command(), "check-host-alive")
        self.assertEqual(512, host.modified_attributes)

        #  ---
        # External command: change check period
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_HOST_CHECK_TIMEPERIOD;test_host_0;none' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Todo: now, check period is an object and no more a TP uuid!
        self.assertEqual(host.check_period, tp2)
        self.assertEqual(16384, host.modified_attributes)

        #  ---
        # External command: change event handler
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_HOST_EVENT_HANDLER;test_host_0;check-host-alive' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(host.get_check_command(), "check-host-alive")
        self.assertEqual(256, host.modified_attributes)

        #  ---
        # External command: max host check attempts
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_MAX_HOST_CHECK_ATTEMPTS;test_host_0;5' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(getattr(host, DICT_MODATTR["MODATTR_MAX_CHECK_ATTEMPTS"].attribute), 5)
        self.assertEqual(4096, host.modified_attributes)

        #  ---
        # External command: retry host check interval
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_NORMAL_HOST_CHECK_INTERVAL;test_host_0;21' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(getattr(host, DICT_MODATTR["MODATTR_NORMAL_CHECK_INTERVAL"].attribute), 21)
        self.assertEqual(1024, host.modified_attributes)

        #  ---
        # External command: retry host check interval
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_RETRY_HOST_CHECK_INTERVAL;test_host_0;42' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(getattr(host, DICT_MODATTR["MODATTR_RETRY_CHECK_INTERVAL"].attribute), 42)
        self.assertEqual(2048, host.modified_attributes)

        #  ---
        # External command: change host custom var
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_CUSTOM_HOST_VAR;test_host_0;_OSLICENSE;other' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(host.customs['_OSLICENSE'], 'other')
        self.assertEqual(32768, host.modified_attributes)

        #  ---
        # External command: delay host first notification
        host.modified_attributes = 0
        self.assertEqual(host.first_notification_delay, 0)
        excmd = '[%d] DELAY_HOST_NOTIFICATION;test_host_0;10' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(host.first_notification_delay, 10)

    def test_change_service_attributes(self):
        """

        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # A TP...
        tp = self._scheduler.timeperiods.find_by_name("24x7")
        self.assertEqual(tp.timeperiod_name, "24x7")
        tp2 = self._scheduler.timeperiods.find_by_name("none")
        self.assertEqual(tp2.timeperiod_name, "none")

        # A command...
        command = self._scheduler.commands.find_by_name("check-host-alive")
        self.assertEqual(command.command_name, "check-host-alive")
        command2 = self._scheduler.commands.find_by_name("check-host-alive-parent")
        self.assertEqual(command2.command_name, "check-host-alive-parent")

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        self.assertIsNotNone(host.customs)
        self.assertEqual(host.get_check_command(),
                         "check-host-alive-parent!up!$HOSTSTATE:test_router_0$")
        self.assertEqual(host.customs['_OSLICENSE'], 'gpl')
        self.assertEqual(host.customs['_OSTYPE'], 'gnulinux')
        # Todo: check if it is normal ... host.check_period is the TP uuid and not an object!
        self.assertEqual(host.check_period, tp.uuid)

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        self.assertIsNotNone(svc)
        self.assertEqual(svc.get_check_command(), "check_service!ok")
        self.assertEqual(svc.customs['_CUSTNAME'], 'custvalue')
        # Todo: check if it is normal ... host.check_period is the TP uuid and not an object!
        self.assertEqual(svc.check_period, tp.uuid)

        # A contact...
        contact = self._scheduler.contacts[host.contacts[0]]
        self.assertIsNotNone(contact)
        self.assertEqual(contact.contact_name, "test_contact")
        # Todo: check if it is normal ... contact.host_notification_period is the TP name
        # and not an object!
        self.assertEqual(contact.host_notification_period, tp.timeperiod_name)
        self.assertEqual(contact.service_notification_period, tp.timeperiod_name)

        #  ---
        # External command: change check command
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_SVC_CHECK_COMMAND;test_host_0;test_ok_0;check-host-alive' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(svc.get_check_command(), "check-host-alive")
        self.assertEqual(512, svc.modified_attributes)

        #  ---
        # External command: change notification period
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_SVC_NOTIFICATION_TIMEPERIOD;test_host_0;test_ok_0;none' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Todo: now, check period is an object and no more a TP uuid!
        self.assertEqual(svc.notification_period, tp2)
        self.assertEqual(65536, svc.modified_attributes)

        #  ---
        # External command: change check period
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_SVC_CHECK_TIMEPERIOD;test_host_0;test_ok_0;none' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Todo: now, check period is an object and no more a TP uuid!
        self.assertEqual(svc.check_period, tp2)
        self.assertEqual(16384, svc.modified_attributes)

        #  ---
        # External command: change event handler
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_SVC_EVENT_HANDLER;test_host_0;test_ok_0;check-host-alive' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(svc.get_check_command(), "check-host-alive")
        self.assertEqual(256, svc.modified_attributes)

        #  ---
        # External command: max host check attempts
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_MAX_SVC_CHECK_ATTEMPTS;test_host_0;test_ok_0;5' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(getattr(svc, DICT_MODATTR["MODATTR_MAX_CHECK_ATTEMPTS"].attribute), 5)
        self.assertEqual(4096, svc.modified_attributes)

        #  ---
        # External command: retry host check interval
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_NORMAL_SVC_CHECK_INTERVAL;test_host_0;test_ok_0;21' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(getattr(svc, DICT_MODATTR["MODATTR_NORMAL_CHECK_INTERVAL"].attribute), 21)
        self.assertEqual(1024, svc.modified_attributes)

        #  ---
        # External command: retry host check interval
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_RETRY_SVC_CHECK_INTERVAL;test_host_0;test_ok_0;42' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(getattr(svc, DICT_MODATTR["MODATTR_RETRY_CHECK_INTERVAL"].attribute), 42)
        self.assertEqual(2048, svc.modified_attributes)

        #  ---
        # External command: change host custom var
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_CUSTOM_SVC_VAR;test_host_0;test_ok_0;_CUSTNAME;other' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(svc.customs['_CUSTNAME'], 'other')
        self.assertEqual(32768, svc.modified_attributes)

        #  ---
        # External command: delay host first notification
        svc.modified_attributes = 0
        self.assertEqual(svc.first_notification_delay, 0)
        excmd = '[%d] DELAY_SVC_NOTIFICATION;test_host_0;test_ok_0;10' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(svc.first_notification_delay, 10)

    def test_change_contact_attributes(self):
        """
        Change contact attributes
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # A TP...
        tp = self._scheduler.timeperiods.find_by_name("24x7")
        self.assertEqual(tp.timeperiod_name, "24x7")
        tp2 = self._scheduler.timeperiods.find_by_name("none")
        self.assertEqual(tp2.timeperiod_name, "none")

        # A contact...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        contact = self._scheduler.contacts[host.contacts[0]]
        self.assertIsNotNone(contact)
        self.assertEqual(contact.contact_name, "test_contact")
        # Todo: check if it is normal ... contact.host_notification_period is the TP name
        # and not an object!
        self.assertEqual(contact.host_notification_period, tp.timeperiod_name)
        self.assertEqual(contact.service_notification_period, tp.timeperiod_name)
        # Issue #487: no customs for contacts ...
        self.assertIsNotNone(contact.customs)
        self.assertEqual(contact.customs['_VAR1'], '10')
        self.assertEqual(contact.customs['_VAR2'], 'text')

        # ---
        # External command: change contact attribute
        contact.modified_host_attributes = 0
        excmd = '[%d] CHANGE_CONTACT_HOST_NOTIFICATION_TIMEPERIOD;test_contact;none' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Todo: now, TP is an object and no more a TP name!
        self.assertEqual(contact.host_notification_period, tp2)
        self.assertEqual(65536, contact.modified_host_attributes)

        # ---
        # External command: change contact attribute
        contact.modified_service_attributes = 0
        excmd = '[%d] CHANGE_CONTACT_SVC_NOTIFICATION_TIMEPERIOD;test_contact;none' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Todo: now, TP is an object and no more a TP name!
        self.assertEqual(contact.service_notification_period, tp2)
        self.assertEqual(65536, contact.modified_service_attributes)

        #  ---
        # External command: change contact custom var
        # Issue #487: no customs for contacts ...
        contact.modified_attributes = 0
        excmd = '[%d] CHANGE_CUSTOM_CONTACT_VAR;test_contact;_VAR1;20' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(contact.customs['_VAR1'], '20')
        self.assertEqual(32768, contact.modified_attributes)

    def test_host_comments(self):
        """
        Test the comments for hosts
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        self.assertIsNotNone(host.customs)
        self.assertEqual(host.get_check_command(),
                         "check-host-alive-parent!up!$HOSTSTATE:test_router_0$")
        self.assertEqual(host.customs['_OSLICENSE'], 'gpl')
        self.assertEqual(host.customs['_OSTYPE'], 'gnulinux')
        self.assertEqual(host.comments, [])

        now = int(time.time())

        #  ---
        # External command: add an host comment
        self.assertEqual(host.comments, [])
        excmd = '[%d] ADD_HOST_COMMENT;test_host_0;1;test_contact;My comment' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(host.comments), 1)
        comment_id = host.comments[0]
        self.assertIn(comment_id, self._scheduler.comments)
        comment = self._scheduler.comments[comment_id]
        self.assertEqual(comment.comment, "My comment")
        self.assertEqual(comment.author, "test_contact")
        self.assertTrue(comment.persistent)

        #  ---
        # External command: add another host comment
        excmd = '[%d] ADD_HOST_COMMENT;test_host_0;1;test_contact;My comment 2' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(self._scheduler.comments), 2)
        self.assertEqual(len(host.comments), 2)
        for comment in host.comments:
            self.assertIn(comment, self._scheduler.comments)

        #  ---
        # External command: yet another host comment
        excmd = '[%d] ADD_HOST_COMMENT;test_host_0;1;test_contact;' \
                'My accented é"{|:âàç comment' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(self._scheduler.comments), 3)
        self.assertEqual(len(host.comments), 3)
        for comment in host.comments:
            self.assertIn(comment, self._scheduler.comments)

        #  ---
        # External command: delete an host comment (unknown comment)
        excmd = '[%d] DEL_HOST_COMMENT;qsdqszerzerzd' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        self.assertEqual(len(self._scheduler.comments), 3)
        self.assertEqual(len(host.comments), 3)
        for comment in host.comments:
            self.assertIn(comment, self._scheduler.comments)

        #  ---
        # External command: delete an host comment
        excmd = '[%d] DEL_HOST_COMMENT;%s' % (now, host.comments[0])
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        self.assertEqual(len(self._scheduler.comments), 2)
        self.assertEqual(len(host.comments), 2)
        for comment in host.comments:
            self.assertIn(comment, self._scheduler.comments)

        #  ---
        # External command: delete all host comment
        excmd = '[%d] DEL_ALL_HOST_COMMENTS;test_host_0' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(host.comments), 0)

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in self._broker['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        expected_logs = [
            (u'info',
             u'EXTERNAL COMMAND: [%s] ADD_HOST_COMMENT;test_host_0;1;test_contact;My comment' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] ADD_HOST_COMMENT;test_host_0;1;test_contact;My comment 2' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] ADD_HOST_COMMENT;test_host_0;1;test_contact;My accented é"{|:âàç comment' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] DEL_HOST_COMMENT;qsdqszerzerzd' % now),
            (u'warning',
             u'DEL_HOST_COMMENT: comment id: qsdqszerzerzd does not exist and cannot be deleted.'),
            (u'info',
             u'EXTERNAL COMMAND: [%s] DEL_ALL_HOST_COMMENTS;test_host_0' % now),
        ]
        for log_level, log_message in expected_logs:
            self.assertIn((log_level, log_message), monitoring_logs)

    def test_service_comments(self):
        """
        Test the comments for services
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        self.assertIsNotNone(svc.customs)
        self.assertEqual(svc.get_check_command(), "check_service!ok")
        self.assertEqual(svc.customs['_CUSTNAME'], 'custvalue')
        self.assertEqual(svc.comments, [])

        now= int(time.time())

        #  ---
        # External command: add an host comment
        self.assertEqual(svc.comments, [])
        excmd = '[%d] ADD_SVC_COMMENT;test_host_0;test_ok_0;1;test_contact;My comment' \
                % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(svc.comments), 1)
        comment_id = svc.comments[0]
        self.assertIn(comment_id, self._scheduler.comments)
        comment = self._scheduler.comments[comment_id]
        self.assertEqual(comment.comment, "My comment")
        self.assertEqual(comment.author, "test_contact")
        self.assertTrue(comment.persistent)

        #  ---
        # External command: add another host comment
        excmd = '[%d] ADD_SVC_COMMENT;test_host_0;test_ok_0;1;test_contact;My comment 2' \
                % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(self._scheduler.comments), 2)
        self.assertEqual(len(svc.comments), 2)
        for comment in svc.comments:
            self.assertIn(comment, self._scheduler.comments)

        #  ---
        # External command: yet another host comment
        excmd = '[%d] ADD_SVC_COMMENT;test_host_0;test_ok_0;1;test_contact;My accented ' \
                'é"{|:âàç comment' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(self._scheduler.comments), 3)
        self.assertEqual(len(svc.comments), 3)
        for comment in svc.comments:
            self.assertIn(comment, self._scheduler.comments)

        #  ---
        # External command: delete an host comment (unknown comment)
        excmd = '[%d] DEL_SVC_COMMENT;qsdqszerzerzd' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        self.assertEqual(len(self._scheduler.comments), 3)
        self.assertEqual(len(svc.comments), 3)
        for comment in svc.comments:
            self.assertIn(comment, self._scheduler.comments)

        #  ---
        # External command: delete an host comment
        excmd = '[%d] DEL_SVC_COMMENT;%s' % (now, svc.comments[0])
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        self.assertEqual(len(self._scheduler.comments), 2)
        self.assertEqual(len(svc.comments), 2)
        for comment in svc.comments:
            self.assertIn(comment, self._scheduler.comments)

        #  ---
        # External command: delete all host comment
        excmd = '[%d] DEL_ALL_SVC_COMMENTS;test_host_0;test_ok_0' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(svc.comments), 0)

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in self._broker['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        expected_logs = [
            (u'info',
             u'EXTERNAL COMMAND: [%s] ADD_SVC_COMMENT;test_host_0;test_ok_0;1;test_contact;My comment' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] ADD_SVC_COMMENT;test_host_0;test_ok_0;1;test_contact;My comment 2' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] ADD_SVC_COMMENT;test_host_0;test_ok_0;1;test_contact;My accented é"{|:âàç comment' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] DEL_SVC_COMMENT;qsdqszerzerzd' % now),
            (u'warning',
             u'DEL_SVC_COMMENT: comment id: qsdqszerzerzd does not exist and cannot be deleted.'),
            (u'info',
             u'EXTERNAL COMMAND: [%s] DEL_ALL_SVC_COMMENTS;test_host_0;test_ok_0' % now),
        ]
        for log_level, log_message in expected_logs:
            self.assertIn((log_level, log_message), monitoring_logs)

    def test_host_downtimes(self):
        """
        Test the downtime for hosts
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        self.assertIsNotNone(host.customs)
        self.assertEqual(host.get_check_command(),
                         "check-host-alive-parent!up!$HOSTSTATE:test_router_0$")
        self.assertEqual(host.customs['_OSLICENSE'], 'gpl')
        self.assertEqual(host.customs['_OSTYPE'], 'gnulinux')
        self.assertEqual(host.downtimes, [])

        now= int(time.time())

        #  ---
        # External command: add an host downtime
        self.assertEqual(host.downtimes, [])
        excmd = '[%d] SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;1200;test_contact;My downtime' \
                % (now, now + 120, now + 1200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(host.downtimes), 1)
        downtime_id = host.downtimes[0]
        self.assertIn(downtime_id, self._scheduler.downtimes)
        downtime = self._scheduler.downtimes[downtime_id]
        self.assertEqual(downtime.comment, "My downtime")
        self.assertEqual(downtime.author, "test_contact")
        self.assertEqual(downtime.start_time, now + 120)
        self.assertEqual(downtime.end_time, now + 1200)
        self.assertEqual(downtime.duration, 1080)
        self.assertEqual(downtime.fixed, True)
        self.assertEqual(downtime.trigger_id, "0")

        #  ---
        # External command: add another host downtime
        excmd = '[%d] SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;1200;test_contact;My downtime 2' \
                % (now, now + 1120, now + 11200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(self._scheduler.downtimes), 2)
        self.assertEqual(len(host.downtimes), 2)
        for downtime in host.downtimes:
            self.assertIn(downtime, self._scheduler.downtimes)

        #  ---
        # External command: yet another host downtime
        excmd = '[%d] SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;1200;test_contact;' \
                'My accented é"{|:âàç downtime' % (now, now + 2120, now + 21200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(self._scheduler.downtimes), 3)
        self.assertEqual(len(host.downtimes), 3)
        for downtime in host.downtimes:
            self.assertIn(downtime, self._scheduler.downtimes)

        #  ---
        # External command: delete an host downtime (unknown downtime)
        excmd = '[%d] DEL_HOST_DOWNTIME;qsdqszerzerzd' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        self.assertEqual(len(self._scheduler.downtimes), 3)
        self.assertEqual(len(host.downtimes), 3)
        for downtime in host.downtimes:
            self.assertIn(downtime, self._scheduler.downtimes)

        #  ---
        # External command: delete an host downtime
        excmd = '[%d] DEL_HOST_DOWNTIME;%s' % (now, downtime_id)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        self.assertEqual(len(self._scheduler.downtimes), 2)
        self.assertEqual(len(host.downtimes), 2)
        for downtime in host.downtimes:
            self.assertIn(downtime, self._scheduler.downtimes)

        #  ---
        # External command: delete all host downtime
        excmd = '[%d] DEL_ALL_HOST_DOWNTIMES;test_host_0' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(host.downtimes), 0)

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in self._broker['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        expected_logs = [
            (u'info', u'EXTERNAL COMMAND: [%s] SCHEDULE_HOST_DOWNTIME;test_host_0;'
                      u'%s;%s;1;0;1200;test_contact;My downtime' % (now, now + 120, now + 1200)),
            (u'info', u'EXTERNAL COMMAND: [%s] SCHEDULE_HOST_DOWNTIME;test_host_0;'
                      u'%s;%s;1;0;1200;test_contact;My downtime 2' % (now, now + 1120, now + 11200)),
            (u'info', u'EXTERNAL COMMAND: [%s] SCHEDULE_HOST_DOWNTIME;test_host_0;'
                      u'%s;%s;1;0;1200;test_contact;My accented é"{|:âàç downtime' % (now, now + 2120, now + 21200)),
            (u'info', u'EXTERNAL COMMAND: [%s] DEL_HOST_DOWNTIME;qsdqszerzerzd' % now),
            (u'warning', u'DEL_HOST_DOWNTIME: downtime_id id: qsdqszerzerzd does '
                         u'not exist and cannot be deleted.'),
            (u'info', u'EXTERNAL COMMAND: [%s] DEL_HOST_DOWNTIME;%s' % (now, downtime_id)),
            (u'info', u'EXTERNAL COMMAND: [%s] DEL_ALL_HOST_DOWNTIMES;test_host_0' % now),
        ]
        for log_level, log_message in expected_logs:
            self.assertIn((log_level, log_message), monitoring_logs)

    def test_service_downtimes(self):
        """
        Test the downtime for hosts
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        self.assertIsNotNone(svc.customs)
        self.assertEqual(svc.get_check_command(), "check_service!ok")
        self.assertEqual(svc.customs['_CUSTNAME'], 'custvalue')
        self.assertEqual(svc.comments, [])

        now = int(time.time())
        
        #  ---
        # External command: add an host downtime
        self.assertEqual(svc.downtimes, [])
        excmd = '[%d] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%s;%s;1;0;1200;' \
                'test_contact;My downtime' % (now, now + 120, now + 1200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(svc.downtimes), 1)
        downtime_id = svc.downtimes[0]
        self.assertIn(downtime_id, self._scheduler.downtimes)
        downtime = self._scheduler.downtimes[downtime_id]
        self.assertEqual(downtime.comment, "My downtime")
        self.assertEqual(downtime.author, "test_contact")
        self.assertEqual(downtime.start_time, now + 120)
        self.assertEqual(downtime.end_time, now + 1200)
        self.assertEqual(downtime.duration, 1080)
        self.assertEqual(downtime.fixed, True)
        self.assertEqual(downtime.trigger_id, "0")

        #  ---
        # External command: add another host downtime
        excmd = '[%d] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%s;%s;1;0;1200;' \
                'test_contact;My downtime 2' % (now, now + 1120, now + 11200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(self._scheduler.downtimes), 2)
        self.assertEqual(len(svc.downtimes), 2)
        for downtime in svc.downtimes:
            self.assertIn(downtime, self._scheduler.downtimes)

        #  ---
        # External command: yet another host downtime
        excmd = '[%d] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%s;%s;1;0;1200;test_contact;' \
                'My accented é"{|:âàç downtime' % (now, now + 2120, now + 21200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(self._scheduler.downtimes), 3)
        self.assertEqual(len(svc.downtimes), 3)
        for downtime in svc.downtimes:
            self.assertIn(downtime, self._scheduler.downtimes)

        #  ---
        # External command: delete an host downtime (unknown downtime)
        excmd = '[%d] DEL_SVC_DOWNTIME;qsdqszerzerzd' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        self.assertEqual(len(self._scheduler.downtimes), 3)
        self.assertEqual(len(svc.downtimes), 3)
        for downtime in svc.downtimes:
            self.assertIn(downtime, self._scheduler.downtimes)

        #  ---
        # External command: delete an host downtime
        excmd = '[%d] DEL_SVC_DOWNTIME;%s' % (now, downtime_id)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        self.assertEqual(len(self._scheduler.downtimes), 2)
        self.assertEqual(len(svc.downtimes), 2)
        for downtime in svc.downtimes:
            self.assertIn(downtime, self._scheduler.downtimes)

        #  ---
        # External command: delete all host downtime
        excmd = '[%d] DEL_ALL_SVC_DOWNTIMES;test_host_0;test_ok_0' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(svc.downtimes), 0)
    
        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in self._broker['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))
    
        expected_logs = [
            (u'info', u'EXTERNAL COMMAND: [%s] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;'
                      u'%s;%s;1;0;1200;test_contact;My downtime' % (now, now + 120, now + 1200)),
            (u'info', u'EXTERNAL COMMAND: [%s] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;'
                      u'%s;%s;1;0;1200;test_contact;My downtime 2' % (now, now + 1120, now + 11200)),
            (u'info', u'EXTERNAL COMMAND: [%s] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;'
                      u'%s;%s;1;0;1200;test_contact;My accented é"{|:âàç downtime' % (
             now, now + 2120, now + 21200)),
            (u'info', u'EXTERNAL COMMAND: [%s] DEL_SVC_DOWNTIME;qsdqszerzerzd' % now),
            (u'warning', u'DEL_SVC_DOWNTIME: downtime_id id: qsdqszerzerzd does '
                         u'not exist and cannot be deleted.'),
            (u'info', u'EXTERNAL COMMAND: [%s] DEL_SVC_DOWNTIME;%s' % (now, downtime_id)),
            (u'info', u'EXTERNAL COMMAND: [%s] DEL_ALL_SVC_DOWNTIMES;test_host_0;test_ok_0' % now),
        ]
        for log_level, log_message in expected_logs:
            self.assertIn((log_level, log_message), monitoring_logs)

    # @unittest.skip("Bug when raising contact downtimes!")
    def test_contact_downtimes(self):
        """
        Test the downtime for hosts
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host and a contact...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        contact = self._scheduler.contacts[host.contacts[0]]
        self.assertIsNotNone(contact)
        self.assertEqual(contact.contact_name, "test_contact")

        now= int(time.time())

        #  ---
        # External command: add a contact downtime
        self.assertEqual(host.downtimes, [])
        now = int(time.time())
        excmd = '[%d] SCHEDULE_CONTACT_DOWNTIME;test_contact;%s;%s;test_contact;My downtime' \
                % (now, now + 120, now + 1200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(contact.downtimes), 1)
        downtime_id = contact.downtimes[0]
        self.assertIn(downtime_id, self._scheduler.contact_downtimes)
        downtime = self._scheduler.contact_downtimes[downtime_id]
        self.assertEqual(downtime.comment, "My downtime")
        self.assertEqual(downtime.author, "test_contact")
        self.assertEqual(downtime.start_time, now + 120)
        self.assertEqual(downtime.end_time, now + 1200)

        #  ---
        # External command: add another contact downtime
        excmd = '[%d] SCHEDULE_CONTACT_DOWNTIME;test_contact;%s;%s;test_contact;My downtime 2' \
                % (now, now + 1120, now + 11200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(self._scheduler.contact_downtimes), 2)
        self.assertEqual(len(contact.downtimes), 2)
        for downtime in contact.downtimes:
            self.assertIn(downtime, self._scheduler.contact_downtimes)

        #  ---
        # External command: yet another contact downtime
        excmd = '[%d] SCHEDULE_CONTACT_DOWNTIME;test_contact;%s;%s;test_contact;' \
                'My accented é"{|:âàç downtime' % (now, now + 2120, now + 21200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(self._scheduler.contact_downtimes), 3)
        self.assertEqual(len(contact.downtimes), 3)
        for downtime in contact.downtimes:
            self.assertIn(downtime, self._scheduler.contact_downtimes)

        #  ---
        # External command: delete a contact downtime (unknown downtime)
        excmd = '[%d] DEL_CONTACT_DOWNTIME;qsdqszerzerzd' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        self.assertEqual(len(self._scheduler.contact_downtimes), 3)
        self.assertEqual(len(contact.downtimes), 3)
        for downtime in contact.downtimes:
            self.assertIn(downtime, self._scheduler.contact_downtimes)

        #  ---
        # External command: delete an host downtime
        excmd = '[%d] DEL_CONTACT_DOWNTIME;%s' % (time.time(), contact.downtimes[0])
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        self.assertEqual(len(self._scheduler.contact_downtimes), 2)
        self.assertEqual(len(contact.downtimes), 2)
        for downtime in contact.downtimes:
            self.assertIn(downtime, self._scheduler.contact_downtimes)

        #  ---
        # External command: delete all host downtime
        excmd = '[%d] DEL_ALL_CONTACT_DOWNTIMES;test_contact' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(contact.downtimes), 0)

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in self._broker['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        expected_logs = [
            (u'info', u'EXTERNAL COMMAND: [%s] SCHEDULE_CONTACT_DOWNTIME;test_contact;'
                      u'%s;%s;test_contact;My downtime' % (now, now + 120, now + 1200)),
            (u'info', u'EXTERNAL COMMAND: [%s] SCHEDULE_CONTACT_DOWNTIME;test_contact;'
                      u'%s;%s;test_contact;My downtime 2' % (now, now + 1120, now + 11200)),
            (u'info', u'EXTERNAL COMMAND: [%s] SCHEDULE_CONTACT_DOWNTIME;test_contact;'
                      u'%s;%s;test_contact;My accented é"{|:âàç downtime' % (
             now, now + 2120, now + 21200)),
            (u'info', u'EXTERNAL COMMAND: [%s] DEL_CONTACT_DOWNTIME;qsdqszerzerzd' % now),
            (u'warning', u'DEL_CONTACT_DOWNTIME: downtime_id id: qsdqszerzerzd does '
                         u'not exist and cannot be deleted.'),
            (u'info', u'EXTERNAL COMMAND: [%s] DEL_CONTACT_DOWNTIME;%s' % (now, downtime_id)),
            (u'info', u'EXTERNAL COMMAND: [%s] DEL_ALL_CONTACT_DOWNTIMES;test_contact' % now),
        ]
        for log_level, log_message in expected_logs:
            self.assertIn((log_level, log_message), monitoring_logs)

    def test_contactgroup(self):
        """
        Test the commands for contacts groups
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # A contact...
        contact = self._scheduler.contacts.find_by_name("test_contact")
        self.assertIsNotNone(contact)

        # A contactgroup ...
        contactgroup = self._scheduler.contactgroups.find_by_name("test_contact")
        self.assertIsNotNone(contactgroup)
        
        #  ---
        # External command: disable / enable notifications for a contacts group
        excmd = '[%d] DISABLE_CONTACTGROUP_HOST_NOTIFICATIONS;test_contact' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for contact_id in contactgroup.get_contacts():
            self.assertFalse(self._scheduler.contacts[contact_id].host_notifications_enabled)
        excmd = '[%d] ENABLE_CONTACTGROUP_HOST_NOTIFICATIONS;test_contact' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for contact_id in contactgroup.get_contacts():
            self.assertTrue(self._scheduler.contacts[contact_id].host_notifications_enabled)

        #  ---
        # External command: disable / enable passive checks for a contacts group
        excmd = '[%d] DISABLE_CONTACTGROUP_SVC_NOTIFICATIONS;test_contact' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for contact_id in contactgroup.get_contacts():
            self.assertFalse(self._scheduler.contacts[contact_id].service_notifications_enabled)
        excmd = '[%d] ENABLE_CONTACTGROUP_SVC_NOTIFICATIONS;test_contact' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for contact_id in contactgroup.get_contacts():
            self.assertTrue(self._scheduler.contacts[contact_id].service_notifications_enabled)

    def test_hostgroup(self):
        """
        Test the commands for hosts groups
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        self.assertIsNotNone(host)

        # An hostrgoup...
        hostgroup = self._scheduler.hostgroups.find_by_name("allhosts")
        self.assertIsNotNone(hostgroup)

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        self.assertIsNotNone(svc)

        now = int(time.time())
        
        #  ---
        # External command: disable /enable checks for an hostgroup (hosts)
        excmd = '[%d] DISABLE_HOSTGROUP_HOST_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            self.assertFalse(self._scheduler.hosts[host_id].active_checks_enabled)
        excmd = '[%d] ENABLE_HOSTGROUP_HOST_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            self.assertTrue(self._scheduler.hosts[host_id].active_checks_enabled)

        #  ---
        # External command: disable / enable notifications for an hostgroup (hosts)
        excmd = '[%d] DISABLE_HOSTGROUP_HOST_NOTIFICATIONS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            self.assertFalse(self._scheduler.hosts[host_id].notifications_enabled)
        excmd = '[%d] ENABLE_HOSTGROUP_HOST_NOTIFICATIONS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            self.assertTrue(self._scheduler.hosts[host_id].notifications_enabled)

        #  ---
        # External command: disable / enable passive checks for an hostgroup (hosts)
        excmd = '[%d] DISABLE_HOSTGROUP_PASSIVE_HOST_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            self.assertFalse(self._scheduler.hosts[host_id].passive_checks_enabled)
        excmd = '[%d] ENABLE_HOSTGROUP_PASSIVE_HOST_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            self.assertTrue(self._scheduler.hosts[host_id].passive_checks_enabled)

        #  ---
        # External command: disable / enable passive checks for an hostgroup (services)
        excmd = '[%d] DISABLE_HOSTGROUP_PASSIVE_SVC_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            if host_id in self._scheduler.hosts:
                for service_id in self._scheduler.hosts[host_id].services:
                    self.assertFalse(self._scheduler.services[service_id].passive_checks_enabled)
        excmd = '[%d] ENABLE_HOSTGROUP_PASSIVE_SVC_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            if host_id in self._scheduler.hosts:
                for service_id in self._scheduler.hosts[host_id].services:
                    self.assertTrue(self._scheduler.services[service_id].passive_checks_enabled)

        #  ---
        # External command: disable checks for an hostgroup (services)
        excmd = '[%d] DISABLE_HOSTGROUP_SVC_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            if host_id in self._scheduler.hosts:
                for service_id in self._scheduler.hosts[host_id].services:
                    self.assertFalse(self._scheduler.services[service_id].active_checks_enabled)
        excmd = '[%d] ENABLE_HOSTGROUP_SVC_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            if host_id in self._scheduler.hosts:
                for service_id in self._scheduler.hosts[host_id].services:
                    self.assertTrue(self._scheduler.services[service_id].active_checks_enabled)

        #  ---
        # External command: disable notifications for an hostgroup (services)
        excmd = '[%d] DISABLE_HOSTGROUP_SVC_NOTIFICATIONS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            if host_id in self._scheduler.hosts:
                for service_id in self._scheduler.hosts[host_id].services:
                    self.assertFalse(self._scheduler.services[service_id].notifications_enabled)
        excmd = '[%d] ENABLE_HOSTGROUP_SVC_NOTIFICATIONS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            if host_id in self._scheduler.hosts:
                for service_id in self._scheduler.hosts[host_id].services:
                    self.assertTrue(self._scheduler.services[service_id].notifications_enabled)
    
        #  ---
        # External command: add an host downtime
        self.assertEqual(host.downtimes, [])
        excmd = '[%d] SCHEDULE_HOSTGROUP_HOST_DOWNTIME;allhosts;%s;%s;1;0;1200;' \
                'test_contact;My downtime' \
                % (now, now + 120, now + 1200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(host.downtimes), 1)
        for host_id in hostgroup.get_hosts():
            host = self._scheduler.hosts[host_id]
            downtime_id = host.downtimes[0]
            self.assertIn(downtime_id, self._scheduler.downtimes)
            downtime = self._scheduler.downtimes[downtime_id]
            self.assertEqual(downtime.comment, "My downtime")
            self.assertEqual(downtime.author, "test_contact")
            self.assertEqual(downtime.start_time, now + 120)
            self.assertEqual(downtime.end_time, now + 1200)
            self.assertEqual(downtime.duration, 1080)
            self.assertEqual(downtime.fixed, True)
            self.assertEqual(downtime.trigger_id, "0")

        #  ---
        # External command: add an host downtime
        excmd = '[%d] SCHEDULE_HOSTGROUP_SVC_DOWNTIME;allhosts;%s;%s;1;0;1200;' \
                'test_contact;My downtime' \
                % (now, now + 120, now + 1200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertEqual(len(host.downtimes), 1)
        for host_id in hostgroup.get_hosts():
            host = self._scheduler.hosts[host_id]
            for service_id in host.services:
                service = self._scheduler.services[service_id]
                downtime_id = host.downtimes[0]
                self.assertIn(downtime_id, self._scheduler.downtimes)
                downtime = self._scheduler.downtimes[downtime_id]
                self.assertEqual(downtime.comment, "My downtime")
                self.assertEqual(downtime.author, "test_contact")
                self.assertEqual(downtime.start_time, now + 120)
                self.assertEqual(downtime.end_time, now + 1200)
                self.assertEqual(downtime.duration, 1080)
                self.assertEqual(downtime.fixed, True)
                self.assertEqual(downtime.trigger_id, "0")

    def test_host(self):
        """
        Test the commands for hosts
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        self.assertIsNotNone(host)

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        self.assertIsNotNone(svc.customs)

        #  ---
        # External command: disable / enable checks
        self.assertTrue(host.active_checks_enabled)
        self.assertTrue(host.passive_checks_enabled)
        self.assertTrue(svc.passive_checks_enabled)

        excmd = '[%d] DISABLE_HOST_CHECK;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(host.active_checks_enabled)
        # Not changed!
        self.assertTrue(host.passive_checks_enabled)

        excmd = '[%d] ENABLE_HOST_CHECK;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(host.active_checks_enabled)
        self.assertTrue(host.passive_checks_enabled)

        excmd = '[%d] DISABLE_HOST_SVC_CHECKS;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(svc.active_checks_enabled)
        # Not changed!
        self.assertTrue(svc.passive_checks_enabled)

        excmd = '[%d] ENABLE_HOST_SVC_CHECKS;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(svc.active_checks_enabled)
        self.assertTrue(svc.passive_checks_enabled)

        #  ---
        # External command: disable / enable checks
        self.assertTrue(host.event_handler_enabled)

        excmd = '[%d] DISABLE_HOST_EVENT_HANDLER;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(host.event_handler_enabled)

        excmd = '[%d] ENABLE_HOST_EVENT_HANDLER;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(host.event_handler_enabled)

        #  ---
        # External command: disable / enable notifications
        self.assertTrue(host.notifications_enabled)
        self.assertTrue(svc.notifications_enabled)

        excmd = '[%d] DISABLE_HOST_NOTIFICATIONS;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(host.notifications_enabled)

        excmd = '[%d] ENABLE_HOST_NOTIFICATIONS;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(host.notifications_enabled)

        excmd = '[%d] DISABLE_HOST_SVC_NOTIFICATIONS;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(svc.notifications_enabled)

        excmd = '[%d] ENABLE_HOST_SVC_NOTIFICATIONS;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(svc.notifications_enabled)

        #  ---
        # External command: disable / enable checks
        self.assertFalse(host.obsess_over_host)

        excmd = '[%d] START_OBSESSING_OVER_HOST;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(host.obsess_over_host)

        excmd = '[%d] STOP_OBSESSING_OVER_HOST;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(host.obsess_over_host)

        #  ---
        # External command: disable / enable checks
        self.assertTrue(host.flap_detection_enabled)

        excmd = '[%d] DISABLE_HOST_FLAP_DETECTION;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(host.flap_detection_enabled)

        excmd = '[%d] ENABLE_HOST_FLAP_DETECTION;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(host.flap_detection_enabled)

        #  ---
        # External command: schedule host check
        excmd = '[%d] SCHEDULE_FORCED_HOST_CHECK;test_host_0;1000' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        excmd = '[%d] SCHEDULE_FORCED_HOST_SVC_CHECKS;test_host_0;1000' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        excmd = '[%d] SCHEDULE_HOST_CHECK;test_host_0;1000' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()

        #  ---
        # External command: schedule host services checks
        excmd = '[%d] SCHEDULE_HOST_SVC_CHECKS;test_host_0;1000' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()

        #  ---
        # External command: launch service event handler
        excmd = '[%d] LAUNCH_HOST_EVENT_HANDLER;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()

    def test_global_host_commands(self):
        """
        Test global hosts commands
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        #  ---
        # External command: disable / enable freshness checks for all hosts
        self.assertTrue(self._scheduler.external_commands_manager.conf.check_host_freshness)
        excmd = '[%d] DISABLE_HOST_FRESHNESS_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(self._scheduler.external_commands_manager.conf.check_host_freshness)

        excmd = '[%d] ENABLE_HOST_FRESHNESS_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(self._scheduler.external_commands_manager.conf.check_host_freshness)

    def test_servicegroup(self):
        """
        Test the commands for hosts groups
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        self.assertIsNotNone(host)

        # A servicegroup...
        servicegroup = self._scheduler.servicegroups.find_by_name("ok")
        self.assertIsNotNone(servicegroup)

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        self.assertIsNotNone(svc)

        #  ---
        # External command: disable /enable checks for an servicegroup (hosts)
        excmd = '[%d] DISABLE_SERVICEGROUP_HOST_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            host_id = self._scheduler.services[service_id].host
            self.assertFalse(self._scheduler.hosts[host_id].active_checks_enabled)
        excmd = '[%d] ENABLE_SERVICEGROUP_HOST_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            host_id = self._scheduler.services[service_id].host
            self.assertTrue(self._scheduler.hosts[host_id].active_checks_enabled)

        #  ---
        # External command: disable / enable notifications for an servicegroup (hosts)
        excmd = '[%d] DISABLE_SERVICEGROUP_HOST_NOTIFICATIONS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            host_id = self._scheduler.services[service_id].host
            self.assertFalse(self._scheduler.hosts[host_id].notifications_enabled)
        excmd = '[%d] ENABLE_SERVICEGROUP_HOST_NOTIFICATIONS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            host_id = self._scheduler.services[service_id].host
            self.assertTrue(self._scheduler.hosts[host_id].notifications_enabled)

        #  ---
        # External command: disable / enable passive checks for an servicegroup (hosts)
        excmd = '[%d] DISABLE_SERVICEGROUP_PASSIVE_HOST_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            host_id = self._scheduler.services[service_id].host
            self.assertFalse(self._scheduler.hosts[host_id].passive_checks_enabled)
        excmd = '[%d] ENABLE_SERVICEGROUP_PASSIVE_HOST_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            host_id = self._scheduler.services[service_id].host
            self.assertTrue(self._scheduler.hosts[host_id].passive_checks_enabled)

        #  ---
        # External command: disable / enable passive checks for an servicegroup (services)
        excmd = '[%d] DISABLE_SERVICEGROUP_PASSIVE_SVC_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            self.assertFalse(self._scheduler.services[service_id].passive_checks_enabled)
        excmd = '[%d] ENABLE_SERVICEGROUP_PASSIVE_SVC_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            self.assertTrue(self._scheduler.services[service_id].passive_checks_enabled)

        #  ---
        # External command: disable checks for an servicegroup (services)
        excmd = '[%d] DISABLE_SERVICEGROUP_SVC_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            self.assertFalse(self._scheduler.services[service_id].active_checks_enabled)
        excmd = '[%d] ENABLE_SERVICEGROUP_SVC_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            self.assertTrue(self._scheduler.services[service_id].active_checks_enabled)

        #  ---
        # External command: disable notifications for an servicegroup (services)
        excmd = '[%d] DISABLE_SERVICEGROUP_SVC_NOTIFICATIONS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            self.assertFalse(self._scheduler.services[service_id].notifications_enabled)
        excmd = '[%d] ENABLE_SERVICEGROUP_SVC_NOTIFICATIONS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            self.assertTrue(self._scheduler.services[service_id].notifications_enabled)

    def test_service(self):
        """
        Test the commands for services
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        self.assertIsNotNone(host)

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        self.assertIsNotNone(svc.customs)

        #  ---
        # External command: disable / enable checks
        self.assertTrue(svc.active_checks_enabled)
        self.assertTrue(svc.passive_checks_enabled)
        self.assertTrue(svc.passive_checks_enabled)

        excmd = '[%d] DISABLE_SVC_CHECK;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(svc.active_checks_enabled)
        # Not changed!
        self.assertTrue(svc.passive_checks_enabled)

        excmd = '[%d] ENABLE_SVC_CHECK;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(svc.active_checks_enabled)
        self.assertTrue(svc.passive_checks_enabled)

        #  ---
        # External command: disable / enable checks
        self.assertTrue(svc.event_handler_enabled)

        excmd = '[%d] DISABLE_SVC_EVENT_HANDLER;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(svc.event_handler_enabled)

        excmd = '[%d] ENABLE_SVC_EVENT_HANDLER;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(svc.event_handler_enabled)

        #  ---
        # External command: disable / enable notifications
        self.assertTrue(svc.notifications_enabled)
        self.assertTrue(svc.notifications_enabled)

        excmd = '[%d] DISABLE_SVC_NOTIFICATIONS;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(svc.notifications_enabled)

        excmd = '[%d] ENABLE_SVC_NOTIFICATIONS;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(svc.notifications_enabled)

        #  ---
        # External command: disable / enable checks
        self.assertTrue(svc.obsess_over_service)

        excmd = '[%d] STOP_OBSESSING_OVER_SVC;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(svc.obsess_over_service)

        excmd = '[%d] START_OBSESSING_OVER_SVC;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(svc.obsess_over_service)

        #  ---
        # External command: disable / enable checks
        self.assertFalse(svc.flap_detection_enabled)

        excmd = '[%d] ENABLE_SVC_FLAP_DETECTION;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(svc.flap_detection_enabled)

        excmd = '[%d] DISABLE_SVC_FLAP_DETECTION;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(svc.flap_detection_enabled)

        #  ---
        # External command: schedule service check
        excmd = '[%d] SCHEDULE_FORCED_SVC_CHECK;test_host_0;test_ok_0;1000' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        excmd = '[%d] SCHEDULE_SVC_CHECK;test_host_0;test_ok_0;1000' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()

        #  ---
        # External command: launch service event handler
        excmd = '[%d] LAUNCH_SVC_EVENT_HANDLER;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()

    def test_global_service_commands(self):
        """
        Test global hosts commands
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        #  ---
        # External command: disable / enable freshness checks for all services
        self.assertTrue(self._scheduler.external_commands_manager.conf.check_service_freshness)
        excmd = '[%d] DISABLE_SERVICE_FRESHNESS_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(self._scheduler.external_commands_manager.conf.check_service_freshness)

        excmd = '[%d] ENABLE_SERVICE_FRESHNESS_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(self._scheduler.external_commands_manager.conf.check_service_freshness)

    def test_global_commands(self):
        """
        Test global hosts commands
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        #  ---
        # External command: disable / enable performance data for all hosts
        self.assertTrue(self._scheduler.external_commands_manager.conf.enable_flap_detection)
        excmd = '[%d] DISABLE_FLAP_DETECTION' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(self._scheduler.external_commands_manager.conf.enable_flap_detection)

        excmd = '[%d] ENABLE_FLAP_DETECTION' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(self._scheduler.external_commands_manager.conf.enable_flap_detection)

        #  ---
        # External command: disable / enable performance data for all hosts
        self.assertTrue(self._scheduler.external_commands_manager.conf.process_performance_data)
        excmd = '[%d] DISABLE_PERFORMANCE_DATA' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(self._scheduler.external_commands_manager.conf.process_performance_data)

        excmd = '[%d] ENABLE_PERFORMANCE_DATA' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(self._scheduler.external_commands_manager.conf.process_performance_data)

        #  ---
        # External command: disable / enable global ent handers
        self.assertTrue(self._scheduler.external_commands_manager.conf.enable_notifications)
        excmd = '[%d] DISABLE_NOTIFICATIONS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(self._scheduler.external_commands_manager.conf.enable_notifications)

        self._scheduler.external_commands_manager.conf.modified_attributes = 0
        excmd = '[%d] ENABLE_NOTIFICATIONS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(self._scheduler.external_commands_manager.conf.enable_notifications)

        #  ---
        # External command: disable / enable global ent handers
        self.assertTrue(self._scheduler.external_commands_manager.conf.enable_event_handlers)
        excmd = '[%d] DISABLE_EVENT_HANDLERS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(self._scheduler.external_commands_manager.conf.enable_event_handlers)

        self._scheduler.external_commands_manager.conf.modified_attributes = 0
        excmd = '[%d] ENABLE_EVENT_HANDLERS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(self._scheduler.external_commands_manager.conf.enable_event_handlers)

        #  ---
        # External command: disable / enable global active hosts checks
        self.assertTrue(self._scheduler.external_commands_manager.conf.execute_host_checks)
        excmd = '[%d] STOP_EXECUTING_HOST_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(self._scheduler.external_commands_manager.conf.execute_host_checks)

        self._scheduler.external_commands_manager.conf.modified_attributes = 0
        excmd = '[%d] START_EXECUTING_HOST_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(self._scheduler.external_commands_manager.conf.execute_host_checks)

        #  ---
        # External command: disable / enable global active services checks
        self.assertTrue(self._scheduler.external_commands_manager.conf.execute_service_checks)
        excmd = '[%d] STOP_EXECUTING_SVC_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(self._scheduler.external_commands_manager.conf.execute_service_checks)

        self._scheduler.external_commands_manager.conf.modified_attributes = 0
        excmd = '[%d] START_EXECUTING_SVC_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(self._scheduler.external_commands_manager.conf.execute_service_checks)

        #  ---
        # External command: disable / enable global passive hosts checks
        self.assertTrue(self._scheduler.external_commands_manager.conf.accept_passive_host_checks)
        excmd = '[%d] STOP_ACCEPTING_PASSIVE_HOST_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(self._scheduler.external_commands_manager.conf.accept_passive_host_checks)

        self._scheduler.external_commands_manager.conf.modified_attributes = 0
        excmd = '[%d] START_ACCEPTING_PASSIVE_HOST_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(self._scheduler.external_commands_manager.conf.accept_passive_host_checks)

        #  ---
        # External command: disable / enable global passive services checks
        self.assertTrue(self._scheduler.external_commands_manager.conf.accept_passive_service_checks)
        excmd = '[%d] STOP_ACCEPTING_PASSIVE_SVC_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(self._scheduler.external_commands_manager.conf.accept_passive_service_checks)

        self._scheduler.external_commands_manager.conf.modified_attributes = 0
        excmd = '[%d] START_ACCEPTING_PASSIVE_SVC_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(self._scheduler.external_commands_manager.conf.accept_passive_service_checks)

        #  ---
        # External command: disable / enable global obsessing hosts checks
        self.assertFalse(self._scheduler.external_commands_manager.conf.obsess_over_hosts)
        excmd = '[%d] START_OBSESSING_OVER_HOST_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(self._scheduler.external_commands_manager.conf.obsess_over_hosts)
        excmd = '[%d] STOP_OBSESSING_OVER_HOST_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(self._scheduler.external_commands_manager.conf.obsess_over_hosts)

        #  ---
        # External command: disable / enable global obsessing hosts checks
        self.assertFalse(self._scheduler.external_commands_manager.conf.obsess_over_services)
        self._scheduler.external_commands_manager.conf.modified_attributes = 0
        excmd = '[%d] START_OBSESSING_OVER_SVC_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertTrue(self._scheduler.external_commands_manager.conf.obsess_over_services)
        self.assertEqual(self._scheduler.external_commands_manager.conf.modified_attributes, 128)
        excmd = '[%d] STOP_OBSESSING_OVER_SVC_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assertFalse(self._scheduler.external_commands_manager.conf.obsess_over_services)
        self.assertEqual(self._scheduler.external_commands_manager.conf.modified_attributes, 128)

    def test_unknown_bad_command(self):
        """
        Test if unknown commands are detected and banned
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # Clear logs and broks
        self.clear_logs()
        self._broker['broks'] = {}

        # Malformed command
        excmd = '[%d] MALFORMED COMMAND' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # We get an 'monitoring_log' brok for logging to the monitoring logs...
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(len(broks), 1)
        # ...but no logs
        self.assert_any_log_match("Malformed command")
        self.assert_any_log_match('MALFORMED COMMAND')
        self.assert_any_log_match("Malformed command exception: too many values to unpack")

        # Clear logs and broks
        self.clear_logs()
        self._broker['broks'] = {}

        # Malformed command
        excmd = '[%d] ADD_HOST_COMMENT;test_host_0;1' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # We get an 'monitoring_log' brok for logging to the monitoring logs...
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(len(broks), 1)
        # ...but no logs
        self.assert_any_log_match("Sorry, the arguments for the command")

        # Clear logs and broks
        self.clear_logs()
        self._broker['broks'] = {}

        # Unknown command
        excmd = '[%d] UNKNOWN_COMMAND' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # We get an 'monitoring_log' brok for logging to the monitoring logs...
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(len(broks), 1)
        # ...but no logs
        self.assert_any_log_match("External command 'unknown_command' is not recognized, sorry")

    def test_special_commands(self):
        """
        Test the special external commands
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # Clear logs and broks
        self.clear_logs()
        self._broker['broks'] = {}

        now = int(time.time())

        # RESTART_PROGRAM
        excmd = '[%d] RESTART_PROGRAM' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assert_any_log_match('RESTART command : libexec/sleep_command.sh 3')
        # There is no log made by the script because the command is a shell script !
        # self.assert_any_log_match('I awoke after sleeping 3 seconds')
        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in self._broker['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        expected_logs = [
            (u'info', u'EXTERNAL COMMAND: [%s] RESTART_PROGRAM' % (now)),
            (u'info', u'I awoke after sleeping 3 seconds | sleep=3\n')
        ]
        for log_level, log_message in expected_logs:
            self.assertIn((log_level, log_message), monitoring_logs)

        # Clear logs and broks
        self.clear_logs()
        self._broker['broks'] = {}

        # RELOAD_CONFIG
        excmd = '[%d] RELOAD_CONFIG' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.assert_any_log_match('RELOAD command : libexec/sleep_command.sh 2')
        # There is no log made by the script because the command is a shell script !
        # self.assert_any_log_match('I awoke after sleeping 2 seconds')
        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in self._broker['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        expected_logs = [
            (u'info', u'EXTERNAL COMMAND: [%s] RELOAD_CONFIG' % (now)),
            (u'info', u'I awoke after sleeping 2 seconds | sleep=2\n')
        ]
        for log_level, log_message in expected_logs:
            self.assertIn((log_level, log_message), monitoring_logs)

        # Todo: we should also test those Alignak specific commands:
        # del_host_dependency,
        # add_simple_host_dependency,
        # add_simple_poller

    def test_not_implemented(self):
        """
        Test the not implemented external commands
        :return:
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # Clear logs and broks
        self.clear_logs()
        self._broker['broks'] = {}

        now = int(time.time())

        excmd = '[%d] SHUTDOWN_PROGRAM' % (now)
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in self._broker['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        expected_logs = [
            (u'info', u'EXTERNAL COMMAND: [%s] SHUTDOWN_PROGRAM' % (now)),
            (u'warning', u'SHUTDOWN_PROGRAM: this command is not implemented!')
        ]
        for log_level, log_message in expected_logs:
            self.assertIn((log_level, log_message), monitoring_logs)

        # Clear broks
        self._broker['broks'] = {}
        now = int(time.time())
        excmd = '[%d] SET_HOST_NOTIFICATION_NUMBER;test_host_0;0' % (now)
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))

        # Clear broks
        self._broker['broks'] = {}
        now = int(time.time())
        excmd = '[%d] SET_SVC_NOTIFICATION_NUMBER;test_host_0;test_ok_0;1' % (now)
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))

        # Clear broks
        self._broker['broks'] = {}
        now = int(time.time())
        excmd = '[%d] SEND_CUSTOM_HOST_NOTIFICATION;test_host_0;100;' \
                'test_contact;My notification' % (now)
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))

        # Clear broks
        self._broker['broks'] = {}
        now = int(time.time())
        excmd = '[%d] SEND_CUSTOM_SVC_NOTIFICATION;test_host_0;test_ok_0;100;' \
                'test_contact;My notification' % (now)
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))

        # Clear broks
        self._broker['broks'] = {}
        now = int(time.time())
        excmd = '[%d] SCHEDULE_AND_PROPAGATE_HOST_DOWNTIME;test_host_0;%s;%s;' \
                '1;0;1200;test_contact;My downtime' % (now, now + 120, now + 1200)
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))

        # Clear broks
        self._broker['broks'] = {}
        now = int(time.time())
        excmd = '[%d] SCHEDULE_AND_PROPAGATE_TRIGGERED_HOST_DOWNTIME;test_host_0;%s;%s;' \
                '1;0;1200;test_contact;My downtime' % (now, now + 120, now + 1200)
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] SAVE_STATE_INFORMATION' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] READ_STATE_INFORMATION' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] PROCESS_FILE;file;1' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] ENABLE_HOST_AND_CHILD_NOTIFICATIONS;test_host_0' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] DISABLE_HOST_AND_CHILD_NOTIFICATIONS;test_host_0' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] DISABLE_ALL_NOTIFICATIONS_BEYOND_HOST;test_host_0' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] ENABLE_ALL_NOTIFICATIONS_BEYOND_HOST;test_host_0' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] CHANGE_GLOBAL_HOST_EVENT_HANDLER;check-host-alive' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] CHANGE_GLOBAL_SVC_EVENT_HANDLER;check-host-alive' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        self.assertEqual(2, len(broks))
