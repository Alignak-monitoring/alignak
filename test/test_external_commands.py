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
import re
import time
import datetime
import pytest
from freezegun import freeze_time

from alignak_test import AlignakTest
from alignak_test import ExternalCommandManager
from alignak.misc.common import DICT_MODATTR
from alignak.misc.serialization import unserialize
from alignak.external_command import ExternalCommand


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
        assert self.conf_is_correct
        self.show_logs()

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        # Set / reset as default applyer for external commands
        self.ecm_mode = 'applyer'

    def test__command_syntax_receiver(self):
        self.ecm_mode = 'receiver'
        self._command_syntax()

    def test__command_syntax_dispatcher(self):
        self.ecm_mode = 'dispatcher'
        self._command_syntax()

    def test__command_syntax_applyer(self):
        self.ecm_mode = 'applyer'
        self._command_syntax()

    def _command_syntax(self):
        """ External command parsing - named as test__ to be the first executed test :)
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        now = int(time.time())

        # ---
        # Lowercase command is allowed
        self.clear_logs()
        self._broker['broks'] = {}
        excmd = '[%d] command' % (now)
        res = self.manage_external_command(excmd)
        # Resolve command result is None because the command is not recognized
        assert res is None
        self.assert_any_log_match(
            re.escape("WARNING: [alignak.external_command] External command 'command' "
                      "is not recognized, sorry")
        )

        # ---
        # Some commands are not implemented
        self.clear_logs()
        self._broker['broks'] = {}
        excmd = '[%d] shutdown_program' % (now)
        res = self.manage_external_command(excmd)
        if self.ecm_mode == 'applyer':
            self.assert_any_log_match(
                re.escape("WARNING: [alignak.external_command] The external command "
                          "'SHUTDOWN_PROGRAM' is not currently implemented in Alignak.")
            )
        else:
            # Resolve command result is not None because the command is recognized
            print("Result (mode=%s): %s" % (self.ecm_mode, res))
            assert res is not None

        # ---
        # Command may not have a timestamp
        self.clear_logs()
        self._broker['broks'] = {}
        excmd = 'shutdown_program'
        res = self.manage_external_command(excmd)
        if self.ecm_mode == 'applyer':
            self.assert_any_log_match(
                re.escape("WARNING: [alignak.external_command] The external command "
                          "'SHUTDOWN_PROGRAM' is not currently implemented in Alignak.")
            )
        else:
            # Resolve command result is not None because the command is recognized
            print("Result (mode=%s): %s" % (self.ecm_mode, res))
            assert res is not None

        # ---
        # Timestamp must be an integer
        self.clear_logs()
        self._broker['broks'] = {}
        excmd = '[fake] shutdown_program'
        res = self.manage_external_command(excmd)
        # Resolve command result is not None because the command is recognized
        assert res is None
        self.assert_any_log_match(
            re.escape("WARNING: [alignak.external_command] Malformed command "
                      "'[fake] shutdown_program'")
        )

        # ---
        # Malformed command
        self.clear_logs()
        self._broker['broks'] = {}
        excmd = '[%d] MALFORMED COMMAND' % now
        res = self.manage_external_command(excmd)
        assert res is None
        if self.ecm_mode == 'applyer':
            # We get 'monitoring_log' broks for logging to the monitoring logs...
            broks = [b for b in self._broker['broks'].values()
                     if b.type == 'monitoring_log']
            assert len(broks) == 1
        # ...and some logs
        self.assert_any_log_match("Malformed command")
        self.assert_any_log_match('MALFORMED COMMAND')
        self.assert_any_log_match("Malformed command exception: too many values to unpack")

        # ---
        # Malformed command
        self.clear_logs()
        self._broker['broks'] = {}
        excmd = '[%d] ADD_HOST_COMMENT;test_host_0;1;qdsqd' % now
        res = self.manage_external_command(excmd)
        if self.ecm_mode == 'applyer':
            # We get an 'monitoring_log' brok for logging to the monitoring logs...
            broks = [b for b in self._broker['broks'].values()
                     if b.type == 'monitoring_log']
            assert len(broks) == 1
            # ...and some logs
            self.assert_any_log_match("Sorry, the arguments for the command")

        # ---
        # Unknown command
        self.clear_logs()
        self._broker['broks'] = {}
        excmd = '[%d] UNKNOWN_COMMAND' % now
        res = self.manage_external_command(excmd)
        if self.ecm_mode == 'applyer':
            # We get an 'monitoring_log' brok for logging to the monitoring logs...
            broks = [b for b in self._broker['broks'].values()
                     if b.type == 'monitoring_log']
            assert len(broks) == 1
            # ...and some logs
            self.assert_any_log_match("External command 'unknown_command' is not recognized, sorry")
        else:
            # Resolve command result is not None because the command is recognized
            print("Result unknown command (mode=%s): %s" % (self.ecm_mode, res))
            assert res is None

        #  ---
        # External command: unknown host
        self.clear_logs()
        self._broker['broks'] = {}
        excmd = '[%d] DISABLE_HOST_CHECK;not_found_host' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        if self.ecm_mode == 'applyer':
            # No 'monitoring_log' brok
            broks = [b for b in self._broker['broks'].values()
                     if b.type == 'monitoring_log']
            assert len(broks) == 0
            # ...but an unknown check result brok is raised...
            # todo: do not know how to catch this brok here :/
            # broks = [b for b in self._broker['broks'].values()
            #          if b.type == 'unknown_host_check_result']
            # assert len(broks) == 1
            # ...and a warning log!
            self.assert_any_log_match("A command was received for the host 'not_found_host', "
                                      "but the host could not be found!")
        else:
            # Resolve command result is not None because the command is recognized
            print("Result host check command (mode=%s): %s" % (self.ecm_mode, res))
            assert res is None

        # Now test different types of commands
        # -----
        # Get an host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        assert host is not None

        # Get a service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        assert svc.customs is not None

        # and a contact...
        contact = self._scheduler.contacts[host.contacts[0]]
        assert contact is not None
        assert contact.contact_name == "test_contact"

        #  ---
        # A global host command
        assert self._scheduler.external_commands_manager.conf.check_host_freshness
        now = time.time()
        excmd = '[%d] DISABLE_HOST_FRESHNESS_CHECKS' % now
        res = self.manage_external_command(excmd)
        print("Result (mode=%s): %s" % (self.ecm_mode, res))
        if self.ecm_mode == 'applyer':
            # Command is supposed to be managed
            assert res is None
        else:
            # Command is to be managed by another daemon
            assert res == {'cmd': '[%d] DISABLE_HOST_FRESHNESS_CHECKS' % now, 'global': True}

        #  ---
        # A specific host command
        assert host.notifications_enabled
        assert svc.notifications_enabled

        self.clear_logs()
        self._broker['broks'] = {}
        excmd = '[%d] DISABLE_HOST_NOTIFICATIONS;test_host_0' % time.time()
        res = self.manage_external_command(excmd)
        print("Result (mode=%s): %s" % (self.ecm_mode, res))
        self.show_logs()
        # Command is supposed to be managed
        assert res is None

    def test_several_commands(self):
        """ External command management - several commands at once
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # Clear logs and broks
        self.clear_logs()
        self._broker['broks'] = {}

        now = int(time.time())

        # Clear logs and broks
        self.clear_logs()
        self._broker['broks'] = {}

        # Unknown command
        excmds = []
        excmds.append('[%d] DISABLE_EVENT_HANDLERS' % time.time())
        excmds.append('[%d] ENABLE_EVENT_HANDLERS' % time.time())

        # Call the scheduler method to run several commands at once
        self._scheduler.run_external_commands(excmds)
        self.external_command_loop()
        # We get an 'monitoring_log' brok for logging to the monitoring logs...
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert len(broks) == 2

    def test_change_and_reset_host_modattr(self):
        """ Change and reset modified attributes for an host
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")

        # ---
        # External command: change host attribute
        excmd = '[%d] CHANGE_HOST_MODATTR;test_host_0;1' % time.time()
        self.manage_external_command(excmd)
        # Notifications are now disabled
        assert not getattr(host, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute)
        assert 1 == host.modified_attributes

        # External command: change host attribute
        excmd = '[%d] CHANGE_HOST_MODATTR;test_host_0;1' % time.time()
        self.manage_external_command(excmd)
        # Notifications are now enabled
        assert getattr(host, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute)
        assert 0 == host.modified_attributes

        # ---
        # External command: change host attribute (non boolean attribute)
        excmd = '[%d] CHANGE_HOST_MODATTR;test_host_0;65536' % time.time()
        self.manage_external_command(excmd)
        # Notifications are now disabled
        assert 65536 == host.modified_attributes

        # External command: change host attribute
        excmd = '[%d] CHANGE_HOST_MODATTR;test_host_0;65536' % time.time()
        self.manage_external_command(excmd)
        # Notifications are now enabled
        assert 0 == host.modified_attributes

        # ---
        # External command: change host attribute (several attributes in one command)
        excmd = '[%d] CHANGE_HOST_MODATTR;test_host_0;3' % time.time()
        self.manage_external_command(excmd)
        # Notifications are now disabled
        assert not getattr(host, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute)
        # Active checks are now disabled
        assert not getattr(host, DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].attribute)
        assert 3 == host.modified_attributes

        # External command: change host attribute (several attributes in one command)
        excmd = '[%d] CHANGE_HOST_MODATTR;test_host_0;3' % time.time()
        self.manage_external_command(excmd)
        # Notifications are now enabled
        assert getattr(host, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute)
        # Active checks are now enabled
        assert getattr(host, DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].attribute)
        assert 0 == host.modified_attributes

    def test_change_and_reset_service_modattr(self):
        """  Change and reset modified attributes for a service
        :return: None 
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")

        # ---
        # External command: change service attribute
        excmd = '[%d] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;1' % time.time()
        self.manage_external_command(excmd)
        # Notifications are now disabled
        assert not getattr(svc, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute)
        assert 1 == svc.modified_attributes

        # External command: change service attribute
        excmd = '[%d] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;1' % time.time()
        self.manage_external_command(excmd)
        # Notifications are now enabled
        assert getattr(svc, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute)
        assert 0 == svc.modified_attributes

        # ---
        # External command: change service attribute (non boolean attribute)
        excmd = '[%d] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;65536' % time.time()
        self.manage_external_command(excmd)
        # Notifications are now disabled
        assert 65536 == svc.modified_attributes

        # External command: change service attribute
        excmd = '[%d] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;65536' % time.time()
        self.manage_external_command(excmd)
        # Notifications are now enabled
        assert 0 == svc.modified_attributes

        # ---
        # External command: change service attribute (several attributes in one command)
        excmd = '[%d] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;3' % time.time()
        self.manage_external_command(excmd)
        # Notifications are now disabled
        assert not getattr(svc, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute)
        # Active checks are now disabled
        assert not getattr(svc, DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].attribute)
        assert 3 == svc.modified_attributes

        # External command: change service attribute (several attributes in one command)
        excmd = '[%d] CHANGE_SVC_MODATTR;test_host_0;test_ok_0;3' % time.time()
        self.manage_external_command(excmd)
        # Notifications are now enabled
        assert getattr(svc, DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].attribute)
        # Active checks are now enabled
        assert getattr(svc, DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].attribute)
        assert 0 == svc.modified_attributes

    def test_change_and_reset_contact_modattr(self):
        """  Change an Noned reset modified attributes for a contact
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # A contact...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        contact = self._scheduler.contacts[host.contacts[0]]
        assert contact is not None
        assert contact.contact_name == "test_contact"

        # ---
        # External command: change contact attribute
        excmd = '[%d] CHANGE_CONTACT_MODATTR;test_contact;1' % time.time()
        self.manage_external_command(excmd)
        assert 1 == contact.modified_attributes

        # External command: change contact attribute
        excmd = '[%d] CHANGE_CONTACT_MODATTR;test_contact;1' % time.time()
        self.manage_external_command(excmd)
        # No toggle
        assert 1 == contact.modified_attributes

        # ---
        # External command: change contact attribute
        assert 0 == contact.modified_host_attributes
        excmd = '[%d] CHANGE_CONTACT_MODHATTR;test_contact;1' % time.time()
        self.manage_external_command(excmd)
        assert 1 == contact.modified_host_attributes

        # External command: change contact attribute
        excmd = '[%d] CHANGE_CONTACT_MODHATTR;test_contact;1' % time.time()
        self.manage_external_command(excmd)
        # No toggle
        assert 1 == contact.modified_host_attributes

        # ---
        # External command: change contact attribute
        assert 0 == contact.modified_service_attributes
        excmd = '[%d] CHANGE_CONTACT_MODSATTR;test_contact;1' % time.time()
        self.manage_external_command(excmd)
        assert 1 == contact.modified_service_attributes

        # External command: change contact attribute
        excmd = '[%d] CHANGE_CONTACT_MODSATTR;test_contact;1' % time.time()
        self.manage_external_command(excmd)
        # No toggle
        assert 1 == contact.modified_service_attributes

        # Note that the value is simply stored and not controled in any way ...

    def test_change_host_attributes(self):
        """ Change host attributes

        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # A TP...
        tp = self._scheduler.timeperiods.find_by_name("24x7")
        assert tp.timeperiod_name == "24x7"
        tp2 = self._scheduler.timeperiods.find_by_name("none")
        assert tp2.timeperiod_name == "none"

        # A command...
        command = self._scheduler.commands.find_by_name("check-host-alive")
        assert command.command_name == "check-host-alive"
        command2 = self._scheduler.commands.find_by_name("check-host-alive-parent")
        assert command2.command_name == "check-host-alive-parent"

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        assert host.customs is not None
        assert host.get_check_command() == \
                         "check-host-alive-parent!up!$HOSTSTATE:test_router_0$"
        assert host.customs['_OSLICENSE'] == 'gpl'
        assert host.customs['_OSTYPE'] == 'gnulinux'
        # Todo: check if it is normal ... host.check_period is the TP uuid and not an object!
        assert host.check_period == tp.uuid

        # A contact...
        contact = self._scheduler.contacts[host.contacts[0]]
        assert contact is not None
        assert contact.contact_name == "test_contact"
        # Todo: check if it is normal ... contact.host_notification_period is the TP name
        # and not an object!
        assert contact.host_notification_period == tp.timeperiod_name
        assert contact.service_notification_period == tp.timeperiod_name

        #  ---
        # External command: change check command
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_HOST_CHECK_COMMAND;test_host_0;check-host-alive' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert host.get_check_command() == "check-host-alive"
        assert 512 == host.modified_attributes

        #  ---
        # External command: change check period
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_HOST_CHECK_TIMEPERIOD;test_host_0;none' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Todo: now, check period is an object and no more a TP uuid!
        assert host.check_period == tp2
        assert 16384 == host.modified_attributes

        #  ---
        # External command: change event handler
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_HOST_EVENT_HANDLER;test_host_0;check-host-alive' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert host.get_check_command() == "check-host-alive"
        assert 256 == host.modified_attributes

        #  ---
        # External command: change snapshot command
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_HOST_SNAPSHOT_COMMAND;test_host_0;check-host-alive' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert host.get_snapshot_command() == "check-host-alive"
        assert 256 == host.modified_attributes

        #  ---
        # External command: max host check attempts
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_MAX_HOST_CHECK_ATTEMPTS;test_host_0;5' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert getattr(host, DICT_MODATTR["MODATTR_MAX_CHECK_ATTEMPTS"].attribute) == 5
        assert 4096 == host.modified_attributes

        #  ---
        # External command: retry host check interval
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_NORMAL_HOST_CHECK_INTERVAL;test_host_0;21' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert getattr(host, DICT_MODATTR["MODATTR_NORMAL_CHECK_INTERVAL"].attribute) == 21
        assert 1024 == host.modified_attributes

        #  ---
        # External command: retry host check interval
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_RETRY_HOST_CHECK_INTERVAL;test_host_0;42' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert getattr(host, DICT_MODATTR["MODATTR_RETRY_CHECK_INTERVAL"].attribute) == 42
        assert 2048 == host.modified_attributes

        #  ---
        # External command: change host custom var - undefined variable
        host.modified_attributes = 0
        # Not existing
        assert '_UNDEFINED' not in host.customs
        excmd = '[%d] CHANGE_CUSTOM_HOST_VAR;test_host_0;_UNDEFINED;other' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Not existing
        assert '_UNDEFINED' not in host.customs
        assert 0 == host.modified_attributes

        # External command: change host custom var
        host.modified_attributes = 0
        excmd = '[%d] CHANGE_CUSTOM_HOST_VAR;test_host_0;_OSLICENSE;other' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert host.customs['_OSLICENSE'] == 'other'
        assert 32768 == host.modified_attributes

        #  ---
        # External command: delay host first notification
        host.modified_attributes = 0
        assert host.first_notification_delay == 0
        excmd = '[%d] DELAY_HOST_NOTIFICATION;test_host_0;10' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert host.first_notification_delay == 10

    def test_change_service_attributes(self):
        """Change service attributes

        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # A TP...
        tp = self._scheduler.timeperiods.find_by_name("24x7")
        assert tp.timeperiod_name == "24x7"
        tp2 = self._scheduler.timeperiods.find_by_name("none")
        assert tp2.timeperiod_name == "none"

        # A command...
        command = self._scheduler.commands.find_by_name("check-host-alive")
        assert command.command_name == "check-host-alive"
        command2 = self._scheduler.commands.find_by_name("check-host-alive-parent")
        assert command2.command_name == "check-host-alive-parent"

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        assert host.customs is not None
        assert host.get_check_command() == \
                         "check-host-alive-parent!up!$HOSTSTATE:test_router_0$"
        assert host.customs['_OSLICENSE'] == 'gpl'
        assert host.customs['_OSTYPE'] == 'gnulinux'
        # Todo: check if it is normal ... host.check_period is the TP uuid and not an object!
        assert host.check_period == tp.uuid

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        assert svc is not None
        assert svc.get_check_command() == "check_service!ok"
        assert svc.customs['_CUSTNAME'] == 'custvalue'
        # Todo: check if it is normal ... host.check_period is the TP uuid and not an object!
        assert svc.check_period == tp.uuid

        # A contact...
        contact = self._scheduler.contacts[host.contacts[0]]
        assert contact is not None
        assert contact.contact_name == "test_contact"
        # Todo: check if it is normal ... contact.host_notification_period is the TP name
        # and not an object!
        assert contact.host_notification_period == tp.timeperiod_name
        assert contact.service_notification_period == tp.timeperiod_name

        #  ---
        # External command: change check command
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_SVC_CHECK_COMMAND;test_host_0;test_ok_0;check-host-alive' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert svc.get_check_command() == "check-host-alive"
        assert 512 == svc.modified_attributes

        #  ---
        # External command: change notification period
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_SVC_NOTIFICATION_TIMEPERIOD;test_host_0;test_ok_0;none' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Todo: now, check period is an object and no more a TP uuid!
        assert svc.notification_period == tp2
        assert 65536 == svc.modified_attributes

        #  ---
        # External command: change check period
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_SVC_CHECK_TIMEPERIOD;test_host_0;test_ok_0;none' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Todo: now, check period is an object and no more a TP uuid!
        assert svc.check_period == tp2
        assert 16384 == svc.modified_attributes

        #  ---
        # External command: change event handler
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_SVC_EVENT_HANDLER;test_host_0;test_ok_0;check-host-alive' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert svc.get_check_command() == "check-host-alive"
        assert 256 == svc.modified_attributes

        #  ---
        # External command: change snapshot command
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_SVC_SNAPSHOT_COMMAND;test_host_0;test_ok_0;check-host-alive' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert svc.get_snapshot_command() == "check-host-alive"
        assert 256 == svc.modified_attributes

        #  ---
        # External command: max service check attempts
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_MAX_SVC_CHECK_ATTEMPTS;test_host_0;test_ok_0;5' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert getattr(svc, DICT_MODATTR["MODATTR_MAX_CHECK_ATTEMPTS"].attribute) == 5
        assert 4096 == svc.modified_attributes

        #  ---
        # External command: retry service check interval
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_NORMAL_SVC_CHECK_INTERVAL;test_host_0;test_ok_0;21' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert getattr(svc, DICT_MODATTR["MODATTR_NORMAL_CHECK_INTERVAL"].attribute) == 21
        assert 1024 == svc.modified_attributes

        #  ---
        # External command: retry service check interval
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_RETRY_SVC_CHECK_INTERVAL;test_host_0;test_ok_0;42' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert getattr(svc, DICT_MODATTR["MODATTR_RETRY_CHECK_INTERVAL"].attribute) == 42
        assert 2048 == svc.modified_attributes

        #  ---
        # External command: change service custom var - undefined variable
        svc.modified_attributes = 0
        # Not existing
        assert '_UNDEFINED' not in svc.customs
        excmd = '[%d] CHANGE_CUSTOM_SVC_VAR;test_host_0;test_ok_0;_UNDEFINED;other' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Not existing
        assert '_UNDEFINED' not in svc.customs
        assert 0 == svc.modified_attributes

        # External command: change service custom var
        svc.modified_attributes = 0
        excmd = '[%d] CHANGE_CUSTOM_SVC_VAR;test_host_0;test_ok_0;_CUSTNAME;other' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert svc.customs['_CUSTNAME'] == 'other'
        assert 32768 == svc.modified_attributes

        #  ---
        # External command: delay service first notification
        svc.modified_attributes = 0
        assert svc.first_notification_delay == 0
        excmd = '[%d] DELAY_SVC_NOTIFICATION;test_host_0;test_ok_0;10' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert svc.first_notification_delay == 10

    def test_change_contact_attributes(self):
        """ Change contact attributes
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # A TP...
        tp = self._scheduler.timeperiods.find_by_name("24x7")
        assert tp.timeperiod_name == "24x7"
        tp2 = self._scheduler.timeperiods.find_by_name("none")
        assert tp2.timeperiod_name == "none"

        # A contact...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        contact = self._scheduler.contacts[host.contacts[0]]
        assert contact is not None
        assert contact.contact_name == "test_contact"
        # Todo: check if it is normal ... contact.host_notification_period is the TP name
        # and not an object!
        assert contact.host_notification_period == tp.timeperiod_name
        assert contact.service_notification_period == tp.timeperiod_name
        # Issue #487: no customs for contacts ...
        assert contact.customs is not None
        assert contact.customs['_VAR1'] == '10'
        assert contact.customs['_VAR2'] == 'text'

        # ---
        # External command: change contact attribute
        contact.modified_host_attributes = 0
        excmd = '[%d] CHANGE_CONTACT_HOST_NOTIFICATION_TIMEPERIOD;test_contact;none' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Todo: now, TP is an object and no more a TP name!
        assert contact.host_notification_period == tp2
        assert 65536 == contact.modified_host_attributes

        # ---
        # External command: change contact attribute
        contact.modified_service_attributes = 0
        excmd = '[%d] CHANGE_CONTACT_SVC_NOTIFICATION_TIMEPERIOD;test_contact;none' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Todo: now, TP is an object and no more a TP name!
        assert contact.service_notification_period == tp2
        assert 65536 == contact.modified_service_attributes

        #  ---
        # External command: change service custom var - undefined variable
        contact.modified_attributes = 0
        # Not existing
        assert '_UNDEFINED' not in contact.customs
        excmd = '[%d] CHANGE_CUSTOM_CONTACT_VAR;test_host_0;test_ok_0;_UNDEFINED;other' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        # Not existing
        assert '_UNDEFINED' not in contact.customs
        assert 0 == contact.modified_attributes

        # External command: change contact custom var
        # Issue #487: no customs for contacts ...
        contact.modified_attributes = 0
        excmd = '[%d] CHANGE_CUSTOM_CONTACT_VAR;test_contact;_VAR1;20' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert contact.customs['_VAR1'] == '20'
        assert 32768 == contact.modified_attributes

    @freeze_time("2017-06-01 18:30:00")
    def test_host_comments(self):
        """ Test the comments for hosts
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        assert host.customs is not None
        assert host.get_check_command() == \
                         "check-host-alive-parent!up!$HOSTSTATE:test_router_0$"
        assert host.customs['_OSLICENSE'] == 'gpl'
        assert host.customs['_OSTYPE'] == 'gnulinux'
        assert host.comments == {}

        now = int(time.time())

        #  ---
        # External command: add an host comment
        assert host.comments == {}
        excmd = '[%d] ADD_HOST_COMMENT;test_host_0;1;test_contact;My comment' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(host.comments) == 1
        comment = host.comments.values()[0]
        assert comment.comment == "My comment"
        assert comment.author == "test_contact"

        #  ---
        # External command: add another host comment
        excmd = '[%d] ADD_HOST_COMMENT;test_host_0;1;test_contact;My comment 2' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(host.comments) == 2

        #  ---
        # External command: yet another host comment
        excmd = '[%d] ADD_HOST_COMMENT;test_host_0;1;test_contact;' \
                'My accented é"{|:âàç comment' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(host.comments) == 3

        #  ---
        # External command: delete an host comment (unknown comment)
        excmd = '[%d] DEL_HOST_COMMENT;qsdqszerzerzd' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        assert len(host.comments) == 3

        #  ---
        # External command: delete an host comment
        excmd = '[%d] DEL_HOST_COMMENT;%s' % (now, list(host.comments)[0])
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        assert len(host.comments) == 2

        #  ---
        # External command: delete all host comment
        excmd = '[%d] DEL_ALL_HOST_COMMENTS;test_host_0' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(host.comments) == 0

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in self._broker['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        expected_logs = [
            (u'info',
             u'EXTERNAL COMMAND: [%s] ADD_HOST_COMMENT;'
             u'test_host_0;1;test_contact;My comment' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] ADD_HOST_COMMENT;'
             u'test_host_0;1;test_contact;My comment 2' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] ADD_HOST_COMMENT;'
             u'test_host_0;1;test_contact;My accented é"{|:âàç comment' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] DEL_HOST_COMMENT;qsdqszerzerzd' % now),
            (u'warning',
             u'DEL_HOST_COMMENT: comment id: qsdqszerzerzd does not exist and cannot be deleted.'),
            (u'info',
             u'EXTERNAL COMMAND: [%s] DEL_ALL_HOST_COMMENTS;test_host_0' % now),
        ]
        for log_level, log_message in expected_logs:
            print("Last checked log %s: %s" % (log_level, log_message))
            assert (log_level, log_message) in monitoring_logs

    @freeze_time("2017-06-01 18:30:00")
    def test_service_comments(self):
        """ Test the comments for services
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        assert svc.customs is not None
        assert svc.get_check_command() == "check_service!ok"
        assert svc.customs['_CUSTNAME'] == 'custvalue'
        assert svc.comments == {}

        now = int(time.time())

        #  ---
        # External command: add an host comment
        assert svc.comments == {}
        excmd = '[%d] ADD_SVC_COMMENT;test_host_0;test_ok_0;1;test_contact;My comment' \
                % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(svc.comments) == 1
        comment = svc.comments.values()[0]
        assert comment.comment == "My comment"
        assert comment.author == "test_contact"

        #  ---
        # External command: add another host comment
        excmd = '[%d] ADD_SVC_COMMENT;test_host_0;test_ok_0;1;test_contact;My comment 2' \
                % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(svc.comments) == 2

        #  ---
        # External command: yet another host comment
        excmd = '[%d] ADD_SVC_COMMENT;test_host_0;test_ok_0;1;test_contact;My accented ' \
                'é"{|:âàç comment' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(svc.comments) == 3

        #  ---
        # External command: delete an host comment (unknown comment)
        excmd = '[%d] DEL_SVC_COMMENT;qsdqszerzerzd' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        assert len(svc.comments) == 3

        #  ---
        # External command: delete an host comment
        excmd = '[%d] DEL_SVC_COMMENT;%s' % (now, list(svc.comments)[0])
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        assert len(svc.comments) == 2

        #  ---
        # External command: delete all host comment
        excmd = '[%d] DEL_ALL_SVC_COMMENTS;test_host_0;test_ok_0' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(svc.comments) == 0

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in self._broker['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        expected_logs = [
            (u'info',
             u'EXTERNAL COMMAND: [%s] ADD_SVC_COMMENT;'
             u'test_host_0;test_ok_0;1;test_contact;My comment' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] ADD_SVC_COMMENT;'
             u'test_host_0;test_ok_0;1;test_contact;My comment 2' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] ADD_SVC_COMMENT;'
             u'test_host_0;test_ok_0;1;test_contact;My accented é"{|:âàç comment' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] DEL_SVC_COMMENT;qsdqszerzerzd' % now),
            (u'warning',
             u'DEL_SVC_COMMENT: comment id: qsdqszerzerzd does not exist and cannot be deleted.'),
            (u'info',
             u'EXTERNAL COMMAND: [%s] DEL_ALL_SVC_COMMENTS;test_host_0;test_ok_0' % now),
        ]
        for log_level, log_message in expected_logs:
            print("Last checked log %s: %s" % (log_level, log_message))
            assert (log_level, log_message) in monitoring_logs

    @freeze_time("2017-06-01 18:30:00")
    def test_host_acknowledges(self):
        """ Test the acknowledges for hosts
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # Get host
        host = self._scheduler.hosts.find_by_name('test_host_0')
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.active_checks_enabled = True
        host.passive_checks_enabled = True
        print("Host: %s - state: %s/%s" % (host, host.state_type, host.state))
        assert host is not None

        # Get dependent host
        router = self._scheduler.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.event_handler_enabled = False
        router.active_checks_enabled = True
        router.passive_checks_enabled = True
        print("Router: %s - state: %s/%s" % (router, router.state_type, router.state))
        assert router is not None

        now = int(time.time())

        # Passive checks for hosts - special case
        # ---------------------------------------------
        # Host is DOWN
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_router_0;2;Host is DOWN' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.show_checks()
        self.assert_checks_count(2)
        # Host check and service may happen in any order... because launched almost simultaneously!
        self.assert_any_check_match('test_hostcheck.pl', 'command')
        self.assert_any_check_match('hostname test_host_0', 'command')
        self.assert_any_check_match('test_servicecheck.pl', 'command')
        self.assert_any_check_match('hostname test_host_0', 'command')
        self.assert_any_check_match('servicedesc test_ok_0', 'command')
        assert 'DOWN' == router.state
        assert u'Host is DOWN' == router.output
        assert False == router.problem_has_been_acknowledged

        # Acknowledge router
        excmd = '[%d] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;Big brother;test' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        assert 'DOWN' == router.state
        assert True == router.problem_has_been_acknowledged

        # Remove acknowledge router
        excmd = '[%d] REMOVE_HOST_ACKNOWLEDGEMENT;test_router_0' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        print "Host state", router.state, router.problem_has_been_acknowledged
        assert 'DOWN' == router.state
        assert False == router.problem_has_been_acknowledged

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in self._broker['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))
        print(monitoring_logs)

        expected_logs = [
            (u'info', u'EXTERNAL COMMAND: [%s] PROCESS_HOST_CHECK_RESULT;test_router_0;2;'
                      u'Host is DOWN' % (now)),
            (u'info', u'EXTERNAL COMMAND: [%s] ACKNOWLEDGE_HOST_PROBLEM;test_router_0;2;1;1;'
                      u'Big brother;test' % (now)),
            (u'info', u'HOST ACKNOWLEDGE ALERT: test_router_0;STARTED; '
                      u'Host problem has been acknowledged'),
            (u'info', u'HOST NOTIFICATION: test_contact;test_router_0;ACKNOWLEDGEMENT (DOWN);'
                      u'notify-host;Host is DOWN'),
            (u'info', u'EXTERNAL COMMAND: [%s] REMOVE_HOST_ACKNOWLEDGEMENT;test_router_0' % now),
            (u'info', u'HOST ACKNOWLEDGE ALERT: test_router_0;EXPIRED; '
                      u'Host problem acknowledge expired')
        ]
        for log_level, log_message in expected_logs:
            print("Last checked log %s: %s" % (log_level, log_message))
            assert (log_level, log_message) in monitoring_logs

    @freeze_time("2017-06-01 18:30:00")
    def test_service_acknowledges(self):
        """ Test the acknowledges for services
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # Get host
        host = self._scheduler.hosts.find_by_name('test_host_0')
        host.checks_in_progress = []
        host.event_handler_enabled = False
        host.active_checks_enabled = True
        host.passive_checks_enabled = True
        print("Host: %s - state: %s/%s" % (host, host.state_type, host.state))
        assert host is not None

        # Get dependent host
        router = self._scheduler.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.event_handler_enabled = False
        router.active_checks_enabled = True
        router.passive_checks_enabled = True
        print("Router: %s - state: %s/%s" % (router, router.state_type, router.state))
        assert router is not None

        # Get service
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.event_handler_enabled = False
        svc.active_checks_enabled = True
        svc.passive_checks_enabled = True
        assert svc is not None
        print("Service: %s - state: %s/%s" % (svc, svc.state_type, svc.state))

        now = int(time.time())

        # Passive checks for services
        # ---------------------------------------------
        # Receive passive service check Warning
        excmd = '[%d] PROCESS_SERVICE_CHECK_RESULT;' \
                'test_host_0;test_ok_0;1;Service is WARNING' % now
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [[host, 0, 'Host is UP']])
        assert 'WARNING' == svc.state
        assert 'Service is WARNING' == svc.output
        assert False == svc.problem_has_been_acknowledged

        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;' \
                'test_host_0;test_ok_0;2;1;1;Big brother;Acknowledge service' % now
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()
        assert 'WARNING' == svc.state
        assert True == svc.problem_has_been_acknowledged

        # Remove acknowledge service
        excmd = '[%d] REMOVE_SVC_ACKNOWLEDGEMENT;test_host_0;test_ok_0' % now
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()
        assert 'WARNING' == svc.state
        assert False == svc.problem_has_been_acknowledged

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in self._broker['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        expected_logs = [
            (u'info', u'EXTERNAL COMMAND: [%s] PROCESS_SERVICE_CHECK_RESULT;'
                      u'test_host_0;test_ok_0;1;Service is WARNING' % now),
            (u'warning', u'SERVICE ALERT: test_host_0;test_ok_0;WARNING;SOFT;1;Service is WARNING'),
            (u'info', u'SERVICE ACKNOWLEDGE ALERT: test_host_0;test_ok_0;STARTED; '
                      u'Service problem has been acknowledged'),
            (u'info', u'EXTERNAL COMMAND: [%s] ACKNOWLEDGE_SVC_PROBLEM;'
                      u'test_host_0;test_ok_0;2;1;1;Big brother;Acknowledge service' % now),
            (u'info', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;'
                      u'ACKNOWLEDGEMENT (WARNING);notify-service;Service is WARNING'),
            (u'info', u'EXTERNAL COMMAND: [%s] REMOVE_SVC_ACKNOWLEDGEMENT;'
                      u'test_host_0;test_ok_0' % now),
            (u'info', u'SERVICE ACKNOWLEDGE ALERT: test_host_0;test_ok_0;EXPIRED; '
                      u'Service problem acknowledge expired')
        ]
        for log_level, log_message in expected_logs:
            print("Last checked log %s: %s" % (log_level, log_message))
            assert (log_level, log_message) in monitoring_logs

    @freeze_time("2017-06-01 18:30:00")
    def test_host_downtimes_host_up(self):
        """ Test the downtime for hosts - host is UP
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.act_depend_of = []  # ignore the host which we depend of
        host.checks_in_progress = []
        host.event_handler_enabled = False
        assert host.downtimes == {}

        # Its service
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # ignore the host which we depend of
        svc.event_handler_enabled = False

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2017, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime
            now = int(time.time())

            # ---------------------------------------------
            # Receive passive host check Host is up and alive
            excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is alive' % now
            self.schedulers['scheduler-master'].sched.run_external_command(excmd)
            self.external_command_loop()
            assert 'UP' == host.state
            assert 'HARD' == host.state_type
            assert 'Host is alive' == host.output

            #  ---
            # External command: add an host downtime
            assert host.downtimes == {}
            # Host is not currently a problem
            assert False == host.is_problem
            assert False == host.problem_has_been_acknowledged
            # Host service is not currently a problem
            assert False == svc.is_problem
            assert False == svc.problem_has_been_acknowledged
            excmd = '[%d] SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;1200;' \
                    'test_contact;My first downtime' % (now, now, now + 2)
            self._scheduler.run_external_command(excmd)
            self.external_command_loop()
            # Host is still not a problem - the downtime do not change anything to this
            # because no acknowledge has been set in this case
            assert False == host.is_problem
            assert False == host.problem_has_been_acknowledged
            # Host service is neither impacted
            assert False == svc.is_problem
            assert False == svc.problem_has_been_acknowledged
            assert len(host.downtimes) == 1
            downtime = host.downtimes.values()[0]
            assert downtime.comment == "My first downtime"
            assert downtime.author == "test_contact"
            assert downtime.start_time == now
            assert downtime.end_time == now + 2
            assert downtime.duration == 2
            assert downtime.fixed == True
            assert downtime.trigger_id == "0"

            # Time warp 1 second
            frozen_datetime.tick()

            self.external_command_loop()
            # Notification: downtime start only...
            self.assert_actions_count(1)
            # The downtime started
            self.assert_actions_match(0, '/notifier.pl', 'command')
            self.assert_actions_match(0, 'DOWNTIMESTART', 'type')
            self.assert_actions_match(0, 'scheduled', 'status')

            # Time warp 2 seconds
            frozen_datetime.tick()
            frozen_datetime.tick()

            self.external_command_loop()
            # Notification: downtime start and end
            self.show_actions()
            self.assert_actions_count(2)
            # The downtime started
            self.assert_actions_match(0, '/notifier.pl', 'command')
            self.assert_actions_match(0, 'DOWNTIMESTART', 'type')
            self.assert_actions_match(0, 'scheduled', 'status')
            # The downtime stopped
            self.assert_actions_match(1, '/notifier.pl', 'command')
            self.assert_actions_match(1, 'DOWNTIMEEND', 'type')
            self.assert_actions_match(1, 'scheduled', 'status')

            # Clear actions
            self.clear_actions()
            self.show_actions()
            time.sleep(1)

            # We got 'monitoring_log' broks for logging to the monitoring logs...
            monitoring_logs = []
            for brok in self._broker['broks'].itervalues():
                if brok.type == 'monitoring_log':
                    data = unserialize(brok.data)
                    monitoring_logs.append((data['level'], data['message']))

            expected_logs = [
                # Host UP
                (u'info',
                 u'EXTERNAL COMMAND: [%s] '
                 u'PROCESS_HOST_CHECK_RESULT;test_host_0;0;Host is alive' % now),

                # First downtime
                (u'info',
                 u'EXTERNAL COMMAND: [%s] '
                 u'SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;1200;test_contact;My first downtime'
                 % (now, now, now + 2)),

                (u'info',
                 u'HOST DOWNTIME ALERT: test_host_0;STARTED; '
                 u'Host has entered a period of scheduled downtime'),
                (u'info',
                 u'HOST NOTIFICATION: test_contact;test_host_0;'
                 u'DOWNTIMESTART (UP);notify-host;Host is alive'),
                (u'info',
                 u'HOST DOWNTIME ALERT: test_host_0;STOPPED; '
                 u'Host has exited from a period of scheduled downtime'),
                (u'info',
                 u'HOST NOTIFICATION: test_contact;test_host_0;'
                 u'DOWNTIMEEND (UP);notify-host;Host is alive'),
            ]
            for log_level, log_message in expected_logs:
                print("Last checked log %s: %s" % (log_level, log_message))
                assert (log_level, log_message) in monitoring_logs

    def test_host_downtimes_host_down(self):
        """ Test the downtime for hosts - host is DOWN
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.act_depend_of = []  # ignore the host which we depend of
        host.checks_in_progress = []
        host.event_handler_enabled = False
        assert host.downtimes == {}

        # Its service
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # ignore the host which we depend of
        svc.event_handler_enabled = False

        # Freeze the time !
        initial_datetime = datetime.datetime(year=2017, month=6, day=1,
                                             hour=18, minute=30, second=0)
        with freeze_time(initial_datetime) as frozen_datetime:
            assert frozen_datetime() == initial_datetime
            now = int(time.time())

            # Passive checks for hosts
            # ---------------------------------------------
            # Receive passive host check Down
            excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % time.time()
            self.schedulers['scheduler-master'].sched.run_external_command(excmd)
            self.external_command_loop()
            assert 'DOWN' == host.state
            assert 'SOFT' == host.state_type
            assert 'Host is dead' == host.output
            excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % time.time()
            self.schedulers['scheduler-master'].sched.run_external_command(excmd)
            self.external_command_loop()
            assert 'DOWN' == host.state
            assert 'SOFT' == host.state_type
            assert 'Host is dead' == host.output
            excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % time.time()
            self.schedulers['scheduler-master'].sched.run_external_command(excmd)
            self.external_command_loop()
            assert 'DOWN' == host.state
            assert 'HARD' == host.state_type
            assert 'Host is dead' == host.output

            # Time warp 1 second
            frozen_datetime.tick()

            self.external_command_loop()
            # Host problem only...
            self.show_actions()
            self.assert_actions_count(2)
            # The host problem is notified
            self.assert_actions_match(0, 'notifier.pl --hostname test_host_0 --notificationtype PROBLEM --hoststate DOWN --hostoutput Host is dead ', 'command')
            self.assert_actions_match(0, 'NOTIFICATIONTYPE=PROBLEM, NOTIFICATIONRECIPIENTS=test_contact, NOTIFICATIONISESCALATED=False, NOTIFICATIONAUTHOR=n/a, NOTIFICATIONAUTHORNAME=n/a, NOTIFICATIONAUTHORALIAS=n/a, NOTIFICATIONCOMMENT=n/a, HOSTNOTIFICATIONNUMBER=1, SERVICENOTIFICATIONNUMBER=1', 'command')

            self.assert_actions_match(1, 'VOID', 'command')

            #  ---
            # The host is now a problem...
            assert True == host.is_problem
            # and the problem is not yet acknowledged
            assert False == host.problem_has_been_acknowledged
            # Simulate that the host service is also a problem
            svc.is_problem = True
            svc.problem_has_been_acknowledged = False
            svc.state_id = 2
            svc.state = 'CRITICAL'
            # External command: add an host downtime
            excmd = '[%d] SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;1200;' \
                    'test_contact;My first downtime' % (now, now + 2, now + 10)
            self._scheduler.run_external_command(excmd)
            self.external_command_loop()

            assert len(host.downtimes) == 1
            downtime = host.downtimes.values()[0]
            assert downtime.comment == "My first downtime"
            assert downtime.author == "test_contact"
            assert downtime.start_time == now + 2
            assert downtime.end_time == now + 10
            assert downtime.duration == 8
            assert downtime.fixed == True
            assert downtime.trigger_id == "0"

            # Time warp 1 second
            frozen_datetime.tick()
            self.external_command_loop()

            # Host problem only...
            self.show_actions()
            self.assert_actions_count(3)
            # The host problem is notified
            self.assert_actions_match(0, 'notifier.pl --hostname test_host_0 --notificationtype PROBLEM --hoststate DOWN --hostoutput Host is dead ', 'command')
            self.assert_actions_match(0, 'NOTIFICATIONTYPE=PROBLEM, NOTIFICATIONRECIPIENTS=test_contact, NOTIFICATIONISESCALATED=False, NOTIFICATIONAUTHOR=n/a, NOTIFICATIONAUTHORNAME=n/a, NOTIFICATIONAUTHORALIAS=n/a, NOTIFICATIONCOMMENT=n/a, HOSTNOTIFICATIONNUMBER=1, SERVICENOTIFICATIONNUMBER=1', 'command')
            # And the downtime
            self.assert_actions_match(1, 'notifier.pl --hostname test_host_0 --notificationtype DOWNTIMESTART --hoststate DOWN --hostoutput Host is dead ', 'command')
            self.assert_actions_match(1, 'NOTIFICATIONTYPE=DOWNTIMESTART, NOTIFICATIONRECIPIENTS=test_contact, NOTIFICATIONISESCALATED=False, NOTIFICATIONAUTHOR=test_contact, NOTIFICATIONAUTHORNAME=Not available, NOTIFICATIONAUTHORALIAS=Not available, NOTIFICATIONCOMMENT=My first downtime, HOSTNOTIFICATIONNUMBER=1, SERVICENOTIFICATIONNUMBER=1', 'command')

            self.assert_actions_match(2, 'VOID', 'command')

            # Let the downtime start...
            # Time warp 10 seconds
            frozen_datetime.tick(delta=datetime.timedelta(seconds=10))
            self.external_command_loop()

            # Notification: downtime start and end
            self.show_actions()
            # Host problem and acknowledgement only...
            self.assert_actions_count(4)
            # The host problem is notified
            self.assert_actions_match(0, 'notifier.pl --hostname test_host_0 --notificationtype PROBLEM --hoststate DOWN --hostoutput Host is dead ', 'command')
            self.assert_actions_match(0, 'NOTIFICATIONTYPE=PROBLEM, NOTIFICATIONRECIPIENTS=test_contact, NOTIFICATIONISESCALATED=False, NOTIFICATIONAUTHOR=n/a, NOTIFICATIONAUTHORNAME=n/a, NOTIFICATIONAUTHORALIAS=n/a, NOTIFICATIONCOMMENT=n/a, HOSTNOTIFICATIONNUMBER=1, SERVICENOTIFICATIONNUMBER=1', 'command')
            # And the downtime
            self.assert_actions_match(1, 'notifier.pl --hostname test_host_0 --notificationtype DOWNTIMESTART --hoststate DOWN --hostoutput Host is dead ', 'command')
            self.assert_actions_match(1, 'NOTIFICATIONTYPE=DOWNTIMESTART, NOTIFICATIONRECIPIENTS=test_contact, NOTIFICATIONISESCALATED=False, NOTIFICATIONAUTHOR=test_contact, NOTIFICATIONAUTHORNAME=Not available, NOTIFICATIONAUTHORALIAS=Not available, NOTIFICATIONCOMMENT=My first downtime, HOSTNOTIFICATIONNUMBER=1, SERVICENOTIFICATIONNUMBER=1', 'command')

            # And the downtime end
            self.assert_actions_match(2, 'notifier.pl --hostname test_host_0 --notificationtype DOWNTIMEEND --hoststate DOWN --hostoutput Host is dead ', 'command')
            self.assert_actions_match(2, 'NOTIFICATIONTYPE=DOWNTIMEEND, NOTIFICATIONRECIPIENTS=test_contact, NOTIFICATIONISESCALATED=False, NOTIFICATIONAUTHOR=test_contact, NOTIFICATIONAUTHORNAME=Not available, NOTIFICATIONAUTHORALIAS=Not available, NOTIFICATIONCOMMENT=My first downtime, HOSTNOTIFICATIONNUMBER=1, SERVICENOTIFICATIONNUMBER=1', 'command')

            self.assert_actions_match(3, 'VOID', 'command')

            # Clear actions
            self.clear_actions()
            self.show_actions()

            # Time warp 1 second
            frozen_datetime.tick()

            # We got 'monitoring_log' broks for logging to the monitoring logs...
            monitoring_logs = []
            for brok in self._broker['broks'].itervalues():
                if brok.type == 'monitoring_log':
                    data = unserialize(brok.data)
                    monitoring_logs.append((data['level'], data['message']))

            expected_logs = [
                (u'info',
                 u'EXTERNAL COMMAND: [%s] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % now),
                (u'info',
                 u'EXTERNAL COMMAND: [%s] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % now),
                (u'info',
                 u'EXTERNAL COMMAND: [%s] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % now),

                (u'error', u'HOST ALERT: test_host_0;DOWN;SOFT;1;Host is dead'),
                (u'error', u'HOST ALERT: test_host_0;DOWN;SOFT;2;Host is dead'),
                (u'error', u'HOST ALERT: test_host_0;DOWN;HARD;3;Host is dead'),
                (u'error', u'HOST NOTIFICATION: test_contact;test_host_0;DOWN;'
                           u'notify-host;Host is dead'),

                (u'info',
                 u'EXTERNAL COMMAND: [%s] SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;'
                 u'1200;test_contact;My first downtime'
                 % (now, now + 2, now + 10)),

                # Host acknowledgement notifications are blocked by the downtime state of the host
                # (u'info',
                #  u'HOST NOTIFICATION: test_contact;test_host_0;ACKNOWLEDGEMENT (DOWN);'
                #  u'notify-host;Host is dead'),

                # (u'info',
                #  u'HOST ACKNOWLEDGE ALERT: test_host_0;STARTED; Host problem has been acknowledged'),
                # (u'info',
                #  u'SERVICE ACKNOWLEDGE ALERT: test_host_0;test_ok_0;STARTED; '
                #  u'Service problem has been acknowledged'),

                (u'info',
                 u'HOST DOWNTIME ALERT: test_host_0;STARTED; '
                 u'Host has entered a period of scheduled downtime'),
                (u'info',
                 u'HOST DOWNTIME ALERT: test_host_0;STOPPED; '
                 u'Host has exited from a period of scheduled downtime'),
            ]

            for log_level, log_message in expected_logs:
                print("Last checked log %s: %s" % (log_level, log_message))
                assert (log_level, log_message) in monitoring_logs

    def test_host_downtimes_host_delete(self):
        """ Test the downtime for hosts - host is DOWN
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.act_depend_of = []  # ignore the host which we depend of
        host.checks_in_progress = []
        host.event_handler_enabled = False
        assert host.downtimes == {}

        # Its service
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # ignore the host which we depend of
        svc.event_handler_enabled = False

        now = int(time.time())

        # Passive checks for hosts
        # ---------------------------------------------
        # Receive passive host check Down
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % time.time()
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()
        assert 'DOWN' == host.state
        assert 'SOFT' == host.state_type
        assert 'Host is dead' == host.output
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % time.time()
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()
        assert 'DOWN' == host.state
        assert 'SOFT' == host.state_type
        assert 'Host is dead' == host.output
        excmd = '[%d] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % time.time()
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()
        assert 'DOWN' == host.state
        assert 'HARD' == host.state_type
        assert 'Host is dead' == host.output

        #  ---
        # External command: add another host downtime
        # Simulate that the host is now a problem but the downtime starts in some seconds
        host.is_problem = True
        host.problem_has_been_acknowledged = False
        # Host service is now a problem
        svc.is_problem = True
        svc.problem_has_been_acknowledged = False
        svc.state_id = 2
        svc.state = 'CRITICAL'
        # and the problem is not acknowledged
        assert False == host.problem_has_been_acknowledged
        excmd = '[%d] SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;1200;' \
                'test_contact;My first downtime' % (now, now+2, now + 4)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()

        # Host is a problem -
        assert True == host.is_problem
        assert False == host.problem_has_been_acknowledged
        # Host service is neither impacted
        assert True == svc.is_problem
        assert False == svc.problem_has_been_acknowledged
        assert len(host.downtimes) == 1
        downtime = host.downtimes.values()[0]
        assert downtime.comment == "My first downtime"
        assert downtime.author == "test_contact"
        assert downtime.start_time == now + 2
        assert downtime.end_time == now + 4
        assert downtime.duration == 2
        assert downtime.fixed == True
        assert downtime.trigger_id == "0"

        time.sleep(1)
        self.external_command_loop()

        #  ---
        # External command: yet another host downtime
        excmd = '[%d] SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;1200;test_contact;' \
                'My accented é"{|:âàç downtime' % (now, now + 180, now + 360)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(host.downtimes) == 2

        #  ---
        # External command: delete an host downtime (unknown downtime)
        excmd = '[%d] DEL_HOST_DOWNTIME;qsdqszerzerzd' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        assert len(host.downtimes) == 2

        #  ---
        # External command: delete an host downtime
        downtime = host.downtimes.values()[0]
        excmd = '[%d] DEL_HOST_DOWNTIME;%s' % (now, downtime.uuid)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        assert len(host.downtimes) == 1

        #  ---
        # External command: delete all host downtime
        excmd = '[%d] DEL_ALL_HOST_DOWNTIMES;test_host_0' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(host.downtimes) == 0

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in self._broker['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        print(monitoring_logs)
        expected_logs = [
            (u'info',
             u'EXTERNAL COMMAND: [%s] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % now),
            (u'info',
             u'EXTERNAL COMMAND: [%s] PROCESS_HOST_CHECK_RESULT;test_host_0;2;Host is dead' % now),

            (u'error',
             u'HOST ALERT: test_host_0;DOWN;SOFT;1;Host is dead'),
            (u'error',
             u'HOST ALERT: test_host_0;DOWN;SOFT;2;Host is dead'),
            (u'error',
             u'HOST ALERT: test_host_0;DOWN;HARD;3;Host is dead'),

            (u'error',
             u'HOST NOTIFICATION: test_contact;test_host_0;DOWN;notify-host;Host is dead'),

            (u'info',
             u'EXTERNAL COMMAND: [%s] '
             u'SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;1200;test_contact;My first downtime'
             % (now, now + 2, now + 4)),
            (u'info',
             u'EXTERNAL COMMAND: '
             u'[%s] SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;1200;'
             u'test_contact;My accented é"{|:âàç downtime'
             % (now, now + 180, now + 360)),

            (u'info',
             u'EXTERNAL COMMAND: [%s] DEL_HOST_DOWNTIME;qsdqszerzerzd' % now),
            (u'warning',
             u'DEL_HOST_DOWNTIME: downtime_id id: qsdqszerzerzd '
             u'does not exist and cannot be deleted.'),

            (u'info',
             u'EXTERNAL COMMAND: [%s] DEL_HOST_DOWNTIME;%s' % (now, downtime.uuid)),
            (u'info',
             u'EXTERNAL COMMAND: [%s] DEL_ALL_HOST_DOWNTIMES;test_host_0' % now),
        ]

        for log_level, log_message in expected_logs:
            print log_message
            assert (log_level, log_message) in monitoring_logs

    def test_service_downtimes(self):
        """ Test the downtimes for services
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        assert svc.customs is not None
        assert svc.get_check_command() == "check_service!ok"
        assert svc.customs['_CUSTNAME'] == 'custvalue'
        assert svc.comments == {}

        now = int(time.time())
        
        #  ---
        # External command: add a service downtime
        assert svc.downtimes == {}
        excmd = '[%d] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%s;%s;1;0;1200;' \
                'test_contact;My downtime' % (now, now + 120, now + 1200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(svc.downtimes) == 1
        downtime_id = list(svc.downtimes)[0]
        downtime = svc.downtimes.values()[0]
        assert downtime.comment == "My downtime"
        assert downtime.author == "test_contact"
        assert downtime.start_time == now + 120
        assert downtime.end_time == now + 1200
        assert downtime.duration == 1080
        assert downtime.fixed == True
        assert downtime.trigger_id == "0"

        #  ---
        # External command: add another service downtime
        excmd = '[%d] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%s;%s;1;0;1200;' \
                'test_contact;My downtime 2' % (now, now + 1120, now + 11200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(svc.downtimes) == 2

        #  ---
        # External command: yet another service downtime
        excmd = '[%d] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%s;%s;1;0;1200;test_contact;' \
                'My accented é"{|:âàç downtime' % (now, now + 2120, now + 21200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(svc.downtimes) == 3

        #  ---
        # External command: delete a service downtime (unknown downtime)
        excmd = '[%d] DEL_SVC_DOWNTIME;qsdqszerzerzd' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        assert len(svc.downtimes) == 3

        #  ---
        # External command: delete a service downtime
        excmd = '[%d] DEL_SVC_DOWNTIME;%s' % (now, downtime_id)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        assert len(svc.downtimes) == 2

        #  ---
        # External command: delete all service downtime
        excmd = '[%d] DEL_ALL_SVC_DOWNTIMES;test_host_0;test_ok_0' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(svc.downtimes) == 0
    
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
            assert (log_level, log_message) in monitoring_logs

    def test_contact_downtimes(self):
        """ Test the downtime for hosts
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host and a contact...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        contact = self._scheduler.contacts[host.contacts[0]]
        assert contact is not None
        assert contact.contact_name == "test_contact"

        now = int(time.time())

        #  ---
        # External command: add a contact downtime
        assert host.downtimes == {}
        now = int(time.time())
        excmd = '[%d] SCHEDULE_CONTACT_DOWNTIME;test_contact;%s;%s;test_contact;My downtime' \
                % (now, now + 120, now + 1200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(contact.downtimes) == 1
        downtime_id = list(contact.downtimes)[0]
        downtime = contact.downtimes[downtime_id]
        assert downtime.comment == "My downtime"
        assert downtime.author == "test_contact"
        assert downtime.start_time == now + 120
        assert downtime.end_time == now + 1200

        #  ---
        # External command: add another contact downtime
        excmd = '[%d] SCHEDULE_CONTACT_DOWNTIME;test_contact;%s;%s;test_contact;My downtime 2' \
                % (now, now + 1120, now + 11200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(contact.downtimes) == 2

        #  ---
        # External command: yet another contact downtime
        excmd = '[%d] SCHEDULE_CONTACT_DOWNTIME;test_contact;%s;%s;test_contact;' \
                'My accented é"{|:âàç downtime' % (now, now + 2120, now + 21200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(contact.downtimes) == 3

        #  ---
        # External command: delete a contact downtime (unknown downtime)
        excmd = '[%d] DEL_CONTACT_DOWNTIME;qsdqszerzerzd' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        assert len(contact.downtimes) == 3

        #  ---
        # External command: delete an host downtime
        excmd = '[%d] DEL_CONTACT_DOWNTIME;%s' % (now, downtime_id)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        self.scheduler_loop(1, [])
        assert len(contact.downtimes) == 2

        #  ---
        # External command: delete all host downtime
        excmd = '[%d] DEL_ALL_CONTACT_DOWNTIMES;test_contact' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(contact.downtimes) == 0

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
            assert (log_level, log_message) in monitoring_logs

    def test_contactgroup(self):
        """ Test the commands for contacts groups
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # A contact...
        contact = self._scheduler.contacts.find_by_name("test_contact")
        assert contact is not None

        # A contactgroup ...
        contactgroup = self._scheduler.contactgroups.find_by_name("test_contact")
        assert contactgroup is not None
        
        #  ---
        # External command: disable / enable notifications for a contacts group
        excmd = '[%d] DISABLE_CONTACTGROUP_HOST_NOTIFICATIONS;test_contact' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for contact_id in contactgroup.get_contacts():
            assert not self._scheduler.contacts[contact_id].host_notifications_enabled
        excmd = '[%d] ENABLE_CONTACTGROUP_HOST_NOTIFICATIONS;test_contact' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for contact_id in contactgroup.get_contacts():
            assert self._scheduler.contacts[contact_id].host_notifications_enabled

        #  ---
        # External command: disable / enable passive checks for a contacts group
        excmd = '[%d] DISABLE_CONTACTGROUP_SVC_NOTIFICATIONS;test_contact' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for contact_id in contactgroup.get_contacts():
            assert not self._scheduler.contacts[contact_id].service_notifications_enabled
        excmd = '[%d] ENABLE_CONTACTGROUP_SVC_NOTIFICATIONS;test_contact' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for contact_id in contactgroup.get_contacts():
            assert self._scheduler.contacts[contact_id].service_notifications_enabled

    def test_hostgroup(self):
        """ Test the commands for hosts groups
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        assert host is not None

        # An hostrgoup...
        hostgroup = self._scheduler.hostgroups.find_by_name("allhosts")
        assert hostgroup is not None

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        assert svc is not None

        now = int(time.time())
        
        #  ---
        # External command: disable /enable checks for an hostgroup (hosts)
        excmd = '[%d] DISABLE_HOSTGROUP_HOST_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            assert not self._scheduler.hosts[host_id].active_checks_enabled
        excmd = '[%d] ENABLE_HOSTGROUP_HOST_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            assert self._scheduler.hosts[host_id].active_checks_enabled

        #  ---
        # External command: disable / enable notifications for an hostgroup (hosts)
        excmd = '[%d] DISABLE_HOSTGROUP_HOST_NOTIFICATIONS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            assert not self._scheduler.hosts[host_id].notifications_enabled
        excmd = '[%d] ENABLE_HOSTGROUP_HOST_NOTIFICATIONS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            assert self._scheduler.hosts[host_id].notifications_enabled

        #  ---
        # External command: disable / enable passive checks for an hostgroup (hosts)
        excmd = '[%d] DISABLE_HOSTGROUP_PASSIVE_HOST_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            assert not self._scheduler.hosts[host_id].passive_checks_enabled
        excmd = '[%d] ENABLE_HOSTGROUP_PASSIVE_HOST_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            assert self._scheduler.hosts[host_id].passive_checks_enabled

        #  ---
        # External command: disable / enable passive checks for an hostgroup (services)
        excmd = '[%d] DISABLE_HOSTGROUP_PASSIVE_SVC_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            if host_id in self._scheduler.hosts:
                for service_id in self._scheduler.hosts[host_id].services:
                    assert not self._scheduler.services[service_id].passive_checks_enabled
        excmd = '[%d] ENABLE_HOSTGROUP_PASSIVE_SVC_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            if host_id in self._scheduler.hosts:
                for service_id in self._scheduler.hosts[host_id].services:
                    assert self._scheduler.services[service_id].passive_checks_enabled

        #  ---
        # External command: disable checks for an hostgroup (services)
        excmd = '[%d] DISABLE_HOSTGROUP_SVC_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            if host_id in self._scheduler.hosts:
                for service_id in self._scheduler.hosts[host_id].services:
                    assert not self._scheduler.services[service_id].active_checks_enabled
        excmd = '[%d] ENABLE_HOSTGROUP_SVC_CHECKS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            if host_id in self._scheduler.hosts:
                for service_id in self._scheduler.hosts[host_id].services:
                    assert self._scheduler.services[service_id].active_checks_enabled

        #  ---
        # External command: disable notifications for an hostgroup (services)
        excmd = '[%d] DISABLE_HOSTGROUP_SVC_NOTIFICATIONS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            if host_id in self._scheduler.hosts:
                for service_id in self._scheduler.hosts[host_id].services:
                    assert not self._scheduler.services[service_id].notifications_enabled
        excmd = '[%d] ENABLE_HOSTGROUP_SVC_NOTIFICATIONS;allhosts' % now
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for host_id in hostgroup.get_hosts():
            if host_id in self._scheduler.hosts:
                for service_id in self._scheduler.hosts[host_id].services:
                    assert self._scheduler.services[service_id].notifications_enabled
    
        #  ---
        # External command: add an host downtime
        assert host.downtimes == {}
        excmd = '[%d] SCHEDULE_HOSTGROUP_HOST_DOWNTIME;allhosts;%s;%s;1;0;1200;' \
                'test_contact;My downtime' \
                % (now, now + 120, now + 1200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(host.downtimes) == 1
        for host_id in hostgroup.get_hosts():
            host = self._scheduler.hosts[host_id]
            downtime_id = list(host.downtimes)[0]
            downtime = host.downtimes.values()[0]
            assert downtime.comment == "My downtime"
            assert downtime.author == "test_contact"
            assert downtime.start_time == now + 120
            assert downtime.end_time == now + 1200
            assert downtime.duration == 1080
            assert downtime.fixed == True
            assert downtime.trigger_id == "0"

        #  ---
        # External command: add an host downtime
        excmd = '[%d] SCHEDULE_HOSTGROUP_SVC_DOWNTIME;allhosts;%s;%s;1;0;1200;' \
                'test_contact;My downtime' \
                % (now, now + 120, now + 1200)
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert len(host.downtimes) == 1
        for host_id in hostgroup.get_hosts():
            host = self._scheduler.hosts[host_id]
            for service_id in host.services:
                service = self._scheduler.services[service_id]
                downtime_id = list(host.downtimes)[0]
                downtime = host.downtimes.values()[0]
                assert downtime.comment == "My downtime"
                assert downtime.author == "test_contact"
                assert downtime.start_time == now + 120
                assert downtime.end_time == now + 1200
                assert downtime.duration == 1080
                assert downtime.fixed == True
                assert downtime.trigger_id == "0"

    def test_host(self):
        """ Test the commands for hosts
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        assert host is not None

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        assert svc.customs is not None

        #  ---
        # External command: disable / enable checks
        assert host.active_checks_enabled
        assert host.passive_checks_enabled
        assert svc.passive_checks_enabled

        excmd = '[%d] DISABLE_HOST_CHECK;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not host.active_checks_enabled
        # Not changed!
        assert host.passive_checks_enabled

        excmd = '[%d] ENABLE_HOST_CHECK;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert host.active_checks_enabled
        assert host.passive_checks_enabled

        excmd = '[%d] DISABLE_HOST_SVC_CHECKS;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not svc.active_checks_enabled
        # Not changed!
        assert svc.passive_checks_enabled

        excmd = '[%d] ENABLE_HOST_SVC_CHECKS;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert svc.active_checks_enabled
        assert svc.passive_checks_enabled

        #  ---
        # External command: disable / enable checks
        assert host.event_handler_enabled

        excmd = '[%d] DISABLE_HOST_EVENT_HANDLER;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not host.event_handler_enabled

        excmd = '[%d] ENABLE_HOST_EVENT_HANDLER;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert host.event_handler_enabled

        #  ---
        # External command: disable / enable notifications
        assert host.notifications_enabled
        assert svc.notifications_enabled

        excmd = '[%d] DISABLE_HOST_NOTIFICATIONS;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not host.notifications_enabled

        excmd = '[%d] ENABLE_HOST_NOTIFICATIONS;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert host.notifications_enabled

        excmd = '[%d] DISABLE_HOST_SVC_NOTIFICATIONS;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not svc.notifications_enabled

        excmd = '[%d] ENABLE_HOST_SVC_NOTIFICATIONS;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert svc.notifications_enabled

        #  ---
        # External command: disable / enable checks
        assert host.flap_detection_enabled

        excmd = '[%d] DISABLE_HOST_FLAP_DETECTION;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not host.flap_detection_enabled

        excmd = '[%d] ENABLE_HOST_FLAP_DETECTION;test_host_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert host.flap_detection_enabled

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
        """ Test global hosts commands
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        #  ---
        # External command: disable / enable freshness checks for all hosts
        assert self._scheduler.external_commands_manager.conf.check_host_freshness
        excmd = '[%d] DISABLE_HOST_FRESHNESS_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not self._scheduler.external_commands_manager.conf.check_host_freshness

        excmd = '[%d] ENABLE_HOST_FRESHNESS_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert self._scheduler.external_commands_manager.conf.check_host_freshness

    def test_servicegroup(self):
        """
        Test the commands for hosts groups
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        assert host is not None

        # A servicegroup...
        servicegroup = self._scheduler.servicegroups.find_by_name("ok")
        assert servicegroup is not None

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        assert svc is not None

        #  ---
        # External command: disable /enable checks for an servicegroup (hosts)
        excmd = '[%d] DISABLE_SERVICEGROUP_HOST_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            host_id = self._scheduler.services[service_id].host
            assert not self._scheduler.hosts[host_id].active_checks_enabled
        excmd = '[%d] ENABLE_SERVICEGROUP_HOST_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            host_id = self._scheduler.services[service_id].host
            assert self._scheduler.hosts[host_id].active_checks_enabled

        #  ---
        # External command: disable / enable notifications for an servicegroup (hosts)
        excmd = '[%d] DISABLE_SERVICEGROUP_HOST_NOTIFICATIONS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            host_id = self._scheduler.services[service_id].host
            assert not self._scheduler.hosts[host_id].notifications_enabled
        excmd = '[%d] ENABLE_SERVICEGROUP_HOST_NOTIFICATIONS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            host_id = self._scheduler.services[service_id].host
            assert self._scheduler.hosts[host_id].notifications_enabled

        #  ---
        # External command: disable / enable passive checks for an servicegroup (hosts)
        excmd = '[%d] DISABLE_SERVICEGROUP_PASSIVE_HOST_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            host_id = self._scheduler.services[service_id].host
            assert not self._scheduler.hosts[host_id].passive_checks_enabled
        excmd = '[%d] ENABLE_SERVICEGROUP_PASSIVE_HOST_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            host_id = self._scheduler.services[service_id].host
            assert self._scheduler.hosts[host_id].passive_checks_enabled

        #  ---
        # External command: disable / enable passive checks for an servicegroup (services)
        excmd = '[%d] DISABLE_SERVICEGROUP_PASSIVE_SVC_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            assert not self._scheduler.services[service_id].passive_checks_enabled
        excmd = '[%d] ENABLE_SERVICEGROUP_PASSIVE_SVC_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            assert self._scheduler.services[service_id].passive_checks_enabled

        #  ---
        # External command: disable checks for an servicegroup (services)
        excmd = '[%d] DISABLE_SERVICEGROUP_SVC_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            assert not self._scheduler.services[service_id].active_checks_enabled
        excmd = '[%d] ENABLE_SERVICEGROUP_SVC_CHECKS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            assert self._scheduler.services[service_id].active_checks_enabled

        #  ---
        # External command: disable notifications for an servicegroup (services)
        excmd = '[%d] DISABLE_SERVICEGROUP_SVC_NOTIFICATIONS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            assert not self._scheduler.services[service_id].notifications_enabled
        excmd = '[%d] ENABLE_SERVICEGROUP_SVC_NOTIFICATIONS;ok' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        for service_id in servicegroup.get_services():
            assert self._scheduler.services[service_id].notifications_enabled

    def test_service(self):
        """
        Test the commands for services
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._scheduler.brokers['broker-master']

        # An host...
        host = self._scheduler.hosts.find_by_name("test_host_0")
        assert host is not None

        # A service...
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        assert svc.customs is not None

        #  ---
        # External command: disable / enable checks
        assert svc.active_checks_enabled
        assert svc.passive_checks_enabled
        assert svc.passive_checks_enabled

        excmd = '[%d] DISABLE_SVC_CHECK;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not svc.active_checks_enabled
        # Not changed!
        assert svc.passive_checks_enabled

        excmd = '[%d] ENABLE_SVC_CHECK;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert svc.active_checks_enabled
        assert svc.passive_checks_enabled

        #  ---
        # External command: disable / enable checks
        assert svc.event_handler_enabled

        excmd = '[%d] DISABLE_SVC_EVENT_HANDLER;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not svc.event_handler_enabled

        excmd = '[%d] ENABLE_SVC_EVENT_HANDLER;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert svc.event_handler_enabled

        #  ---
        # External command: disable / enable notifications
        assert svc.notifications_enabled
        assert svc.notifications_enabled

        excmd = '[%d] DISABLE_SVC_NOTIFICATIONS;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not svc.notifications_enabled

        excmd = '[%d] ENABLE_SVC_NOTIFICATIONS;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert svc.notifications_enabled

        #  ---
        # External command: disable / enable checks
        assert not svc.flap_detection_enabled

        excmd = '[%d] ENABLE_SVC_FLAP_DETECTION;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert svc.flap_detection_enabled

        excmd = '[%d] DISABLE_SVC_FLAP_DETECTION;test_host_0;test_ok_0' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not svc.flap_detection_enabled

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
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        #  ---
        # External command: disable / enable freshness checks for all services
        assert self._scheduler.external_commands_manager.conf.check_service_freshness
        excmd = '[%d] DISABLE_SERVICE_FRESHNESS_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not self._scheduler.external_commands_manager.conf.check_service_freshness

        excmd = '[%d] ENABLE_SERVICE_FRESHNESS_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert self._scheduler.external_commands_manager.conf.check_service_freshness

    def test_global_commands(self):
        """
        Test global hosts commands
        :return: None
        """
        # Our scheduler
        self._scheduler = self.schedulers['scheduler-master'].sched

        #  ---
        # External command: disable / enable performance data for all hosts
        assert self._scheduler.external_commands_manager.conf.enable_flap_detection
        excmd = '[%d] DISABLE_FLAP_DETECTION' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not self._scheduler.external_commands_manager.conf.enable_flap_detection

        excmd = '[%d] ENABLE_FLAP_DETECTION' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert self._scheduler.external_commands_manager.conf.enable_flap_detection

        #  ---
        # External command: disable / enable performance data for all hosts
        assert self._scheduler.external_commands_manager.conf.process_performance_data
        excmd = '[%d] DISABLE_PERFORMANCE_DATA' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not self._scheduler.external_commands_manager.conf.process_performance_data

        excmd = '[%d] ENABLE_PERFORMANCE_DATA' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert self._scheduler.external_commands_manager.conf.process_performance_data

        #  ---
        # External command: disable / enable global ent handers
        assert self._scheduler.external_commands_manager.conf.enable_notifications
        excmd = '[%d] DISABLE_NOTIFICATIONS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not self._scheduler.external_commands_manager.conf.enable_notifications

        self._scheduler.external_commands_manager.conf.modified_attributes = 0
        excmd = '[%d] ENABLE_NOTIFICATIONS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert self._scheduler.external_commands_manager.conf.enable_notifications

        #  ---
        # External command: disable / enable global ent handers
        assert self._scheduler.external_commands_manager.conf.enable_event_handlers
        excmd = '[%d] DISABLE_EVENT_HANDLERS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not self._scheduler.external_commands_manager.conf.enable_event_handlers

        self._scheduler.external_commands_manager.conf.modified_attributes = 0
        excmd = '[%d] ENABLE_EVENT_HANDLERS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert self._scheduler.external_commands_manager.conf.enable_event_handlers

        #  ---
        # External command: disable / enable global active hosts checks
        assert self._scheduler.external_commands_manager.conf.execute_host_checks
        excmd = '[%d] STOP_EXECUTING_HOST_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not self._scheduler.external_commands_manager.conf.execute_host_checks

        self._scheduler.external_commands_manager.conf.modified_attributes = 0
        excmd = '[%d] START_EXECUTING_HOST_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert self._scheduler.external_commands_manager.conf.execute_host_checks

        #  ---
        # External command: disable / enable global active services checks
        assert self._scheduler.external_commands_manager.conf.execute_service_checks
        excmd = '[%d] STOP_EXECUTING_SVC_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not self._scheduler.external_commands_manager.conf.execute_service_checks

        self._scheduler.external_commands_manager.conf.modified_attributes = 0
        excmd = '[%d] START_EXECUTING_SVC_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert self._scheduler.external_commands_manager.conf.execute_service_checks

        #  ---
        # External command: disable / enable global passive hosts checks
        assert self._scheduler.external_commands_manager.conf.accept_passive_host_checks
        excmd = '[%d] STOP_ACCEPTING_PASSIVE_HOST_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not self._scheduler.external_commands_manager.conf.accept_passive_host_checks

        self._scheduler.external_commands_manager.conf.modified_attributes = 0
        excmd = '[%d] START_ACCEPTING_PASSIVE_HOST_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert self._scheduler.external_commands_manager.conf.accept_passive_host_checks

        #  ---
        # External command: disable / enable global passive services checks
        assert self._scheduler.external_commands_manager.conf.accept_passive_service_checks
        excmd = '[%d] STOP_ACCEPTING_PASSIVE_SVC_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert not self._scheduler.external_commands_manager.conf.accept_passive_service_checks

        self._scheduler.external_commands_manager.conf.modified_attributes = 0
        excmd = '[%d] START_ACCEPTING_PASSIVE_SVC_CHECKS' % time.time()
        self._scheduler.run_external_command(excmd)
        self.external_command_loop()
        assert self._scheduler.external_commands_manager.conf.accept_passive_service_checks

    def test_special_commands(self):
        """
        Test the special external commands
        :return: None
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
            assert (log_level, log_message) in monitoring_logs

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
            assert (log_level, log_message) in monitoring_logs

        # Todo: we should also test those Alignak specific commands:
        # del_host_dependency,
        # add_simple_host_dependency,
        # add_simple_poller

    def test_not_implemented(self):
        """ Test the not implemented external commands
        :return: None
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
            assert (log_level, log_message) in monitoring_logs

        # Clear broks
        self._broker['broks'] = {}
        now = int(time.time())
        excmd = '[%d] SET_HOST_NOTIFICATION_NUMBER;test_host_0;0' % (now)
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)

        # Clear broks
        self._broker['broks'] = {}
        now = int(time.time())
        excmd = '[%d] SET_SVC_NOTIFICATION_NUMBER;test_host_0;test_ok_0;1' % (now)
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)

        # Clear broks
        self._broker['broks'] = {}
        now = int(time.time())
        excmd = '[%d] SEND_CUSTOM_HOST_NOTIFICATION;test_host_0;100;' \
                'test_contact;My notification' % (now)
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)

        # Clear broks
        self._broker['broks'] = {}
        now = int(time.time())
        excmd = '[%d] SEND_CUSTOM_SVC_NOTIFICATION;test_host_0;test_ok_0;100;' \
                'test_contact;My notification' % (now)
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)

        # Clear broks
        self._broker['broks'] = {}
        now = int(time.time())
        excmd = '[%d] SCHEDULE_AND_PROPAGATE_HOST_DOWNTIME;test_host_0;%s;%s;' \
                '1;0;1200;test_contact;My downtime' % (now, now + 120, now + 1200)
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)

        # Clear broks
        self._broker['broks'] = {}
        now = int(time.time())
        excmd = '[%d] SCHEDULE_AND_PROPAGATE_TRIGGERED_HOST_DOWNTIME;test_host_0;%s;%s;' \
                '1;0;1200;test_contact;My downtime' % (now, now + 120, now + 1200)
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] SAVE_STATE_INFORMATION' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] READ_STATE_INFORMATION' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] PROCESS_FILE;file;1' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] ENABLE_HOST_AND_CHILD_NOTIFICATIONS;test_host_0' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] DISABLE_HOST_AND_CHILD_NOTIFICATIONS;test_host_0' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] DISABLE_ALL_NOTIFICATIONS_BEYOND_HOST;test_host_0' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] ENABLE_ALL_NOTIFICATIONS_BEYOND_HOST;test_host_0' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] CHANGE_GLOBAL_HOST_EVENT_HANDLER;check-host-alive' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)

        # Clear broks
        self._broker['broks'] = {}
        excmd = '[%d] CHANGE_GLOBAL_SVC_EVENT_HANDLER;check-host-alive' % int(time.time())
        self._scheduler.run_external_command(excmd)
        self.assert_any_log_match('is not currently implemented in Alignak')
        broks = [b for b in self._broker['broks'].values()
                 if b.type == 'monitoring_log']
        assert 2 == len(broks)
