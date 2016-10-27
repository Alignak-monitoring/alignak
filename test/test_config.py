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


class TestConfig(AlignakTest):
    """
    This class tests the configuration
    """

    def test_config_ok(self):
        """ Default configuration has no loading problems ...

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        self.assertTrue(self.conf_is_correct)

        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

        # Arbiter named as in the configuration
        self.assertTrue(self.arbiter.conf.conf_is_correct)
        arbiter_link = self.arbiter.conf.arbiters.find_by_name('arbiter-master')
        self.assertIsNotNone(arbiter_link)
        self.assertListEqual(arbiter_link.configuration_errors, [])
        self.assertListEqual(arbiter_link.configuration_warnings, [])

        # Scheduler named as in the configuration
        self.assertTrue(self.arbiter.conf.conf_is_correct)
        scheduler_link = self.arbiter.conf.schedulers.find_by_name('scheduler-master')
        self.assertIsNotNone(scheduler_link)
        # Scheduler configuration is ok
        self.assertTrue(self.schedulers['scheduler-master'].sched.conf.conf_is_correct)

        # Broker, Poller, Reactionner named as in the configuration
        link = self.arbiter.conf.brokers.find_by_name('broker-master')
        self.assertIsNotNone(link)
        link = self.arbiter.conf.pollers.find_by_name('poller-master')
        self.assertIsNotNone(link)
        link = self.arbiter.conf.reactionners.find_by_name('reactionner-master')
        self.assertIsNotNone(link)

        # Receiver - no default receiver created
        link = self.arbiter.conf.receivers.find_by_name('receiver-master')
        self.assertIsNotNone(link)

    def test_config_conf_inner_properties(self):
        """ Default configuration has no loading problems ... and inner default proerties are
        correctly values

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        self.assertTrue(self.conf_is_correct)

        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

        # Arbiter configuration is correct
        self.assertTrue(self.arbiter.conf.conf_is_correct)

        # Configuration inner properties are valued
        self.assertEqual(self.arbiter.conf.prefix, '')
        self.assertEqual(self.arbiter.conf.main_config_file,
                         os.path.abspath('cfg/cfg_default.cfg'))
        self.assertEqual(self.arbiter.conf.config_base_dir, 'cfg')

    def test_config_ok_no_declared_daemons(self):
        """ Default configuration has no loading problems ... but no daemons are defined
        The arbiter will create default daemons except for the receiver.

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_config_simple.cfg')
        self.assertTrue(self.conf_is_correct)

        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

        # Arbiter named as Default
        self.assertTrue(self.arbiter.conf.conf_is_correct)
        arbiter_link = self.arbiter.conf.arbiters.find_by_name('Default-Arbiter')
        self.assertIsNotNone(arbiter_link)
        self.assertListEqual(arbiter_link.configuration_errors, [])
        self.assertListEqual(arbiter_link.configuration_warnings, [])

        # Scheduler named as Default
        link = self.arbiter.conf.schedulers.find_by_name('Default-Scheduler')
        self.assertIsNotNone(link)
        # Scheduler configuration is ok
        self.assertTrue(self.schedulers['Default-Scheduler'].sched.conf.conf_is_correct)

        # Broker, Poller, Reactionner named as Default
        link = self.arbiter.conf.brokers.find_by_name('Default-Broker')
        self.assertIsNotNone(link)
        link = self.arbiter.conf.pollers.find_by_name('Default-Poller')
        self.assertIsNotNone(link)
        link = self.arbiter.conf.reactionners.find_by_name('Default-Reactionner')
        self.assertIsNotNone(link)

        # Receiver - no default receiver created
        link = self.arbiter.conf.receivers.find_by_name('Default-Receiver')
        self.assertIsNone(link)

    def test_symlinks(self):
        """ Test a configuration with symlinks to files

        :return: None
        """
        if os.name == 'nt':
            return

        self.print_header()
        self.setup_with_file('cfg/conf_in_symlinks/alignak_conf_in_symlinks.cfg')

        svc = self.arbiter.conf.services.find_srv_by_name_and_hostname("test_host_0",
                                                                       "test_HIDDEN")
        self.assertIsNotNone(svc)

    def test_define_syntax(self):
        """ Test that define{} syntax is correctly checked: spaces, multi-lines, white-spaces
        do not raise any error ...

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/alignak_define_with_space.cfg')
        self.assertTrue(self.conf_is_correct)

        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name('spaced-host')
        self.assertIsNotNone(host)

    def test_definition_order(self):
        """ Test element definition order
        An element (host, service, ...) can be defined several times then the definition_order
        will be used to choose which definition is the to be used one...

        Here, the 'same_service' is defined 3 times but the 'general1' command one will be
        retained rather than other because have the lower definition_order ...

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/alignak_definition_order.cfg')
        self.assertTrue(self.conf_is_correct)

        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "myhost", "same_service")
        self.assertIsNotNone(svc)
        self.assertEqual('general1', svc.check_command.command.command_name)
        self.assertEqual(1, svc.definition_order)

    def test_service_not_hostname(self):
        """ Test the 'not hostname' syntax

        The service test_ok_0 is applied with a host_group on "test_host_0","test_host_1"
        but have a host_name with !"test_host_1" so it will only be attached to "test_host_0"

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/alignak_service_not_hostname.cfg')
        self.assertTrue(self.conf_is_correct)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        self.assertIsNotNone(host)
        self.assertTrue(host.is_correct())

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # Check that the service is attached to test_host_0
        self.assertIsNotNone(svc)
        self.assertTrue(svc.is_correct())

        # Check that the service is NOT attached to test_host_1
        svc_not = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_1", "test_ok_0")
        self.assertIsNone(svc_not)

    def test_service_inheritance(self):
        """ Test services inheritance
        Services are attached to hosts thanks to template inheritance

        SSH services are created from a template and attached to an host

        svc_inherited is created from a service template linked to an host template with a simple
        host declaration

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/alignak_service_description_inheritance.cfg')
        self.assertTrue(self.conf_is_correct)

        # Service linked to an host
        svc = self.schedulers['Default-Scheduler'].sched.services.find_srv_by_name_and_hostname(
            "MYHOST", "SSH")
        self.assertIsNotNone(svc)

        # Service linked to several hosts
        for hname in ["MYHOST2", "MYHOST3"]:
            svc = self.schedulers['Default-Scheduler'].sched.services.\
                find_srv_by_name_and_hostname(hname, "SSH")
            self.assertIsNotNone(svc)

        # Service template linked to an host template
        svc = self.schedulers['Default-Scheduler'].sched.services.find_srv_by_name_and_hostname(
            "test_host", "svc_inherited")
        self.assertIsNotNone(svc)
        self.assertEqual('check_ssh', svc.check_command.command.command_name)

    def test_service_with_no_host(self):
        """ A service not linked to any host raises an error

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/config/alignak_service_nohost.cfg')
        self.assertFalse(self.conf_is_correct)
        self.assertIn("Configuration in service::will_not_exist is incorrect; "
                      "from: cfg/config/alignak_service_nohost.cfg:1",
                      self.configuration_errors)
        self.assertIn("a service has been defined without host_name nor "
                      "hostgroup_name, from: cfg/config/alignak_service_nohost.cfg:1",
                      self.configuration_errors)
        self.assertIn("[service::will_not_exist] not bound to any host.",
                      self.configuration_errors)
        self.assertIn("[service::will_not_exist] no check_command",
                      self.configuration_errors)

        self.assertIn("Configuration in service::will_error is incorrect; "
                      "from: cfg/config/alignak_service_nohost.cfg:6",
                      self.configuration_errors)
        self.assertIn("[service::will_error] unknown host_name 'NOEXIST'",
                      self.configuration_errors)
        self.assertIn("[service::will_error] check_command 'None' invalid",
                      self.configuration_errors)

        self.assertIn("services configuration is incorrect!",
                      self.configuration_errors)

    def test_bad_template_use_itself(self):
        """ Detect a template that uses itself as a template

        This test host use template but template is itself

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_host_template_itself.cfg')
        self.assertFalse(self.conf_is_correct)
        # TODO, issue #344
        self.assertIn("Host bla use/inherits from itself ! "
                      "from: cfg/config/host_bad_template_itself.cfg:1",
                      self.configuration_errors)

    def test_use_undefined_template(self):
        """ Test unknown template detection for host and service

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_bad_undefined_template.cfg')
        self.assertTrue(self.conf_is_correct)

        # TODO, issue #344
        self.assertIn("Host test_host use/inherit from an unknown template: undefined_host ! "
                      "from: cfg/config/use_undefined_template.cfg:1",
                      self.configuration_warnings)
        self.assertIn("Service test_service use/inherit from an unknown template: "
                      "undefined_service ! from: cfg/config/use_undefined_template.cfg:6",
                      self.configuration_warnings)

    def test_broken_configuration(self):
        """ Configuration is not correct because of a wrong relative path in the main config file

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/config/alignak_broken_1.cfg')
        self.assertFalse(self.conf_is_correct)

        # Error messages
        self.assertEqual(len(self.configuration_errors), 2)
        self.assert_any_cfg_log_match(
            re.escape(
                "[config] cannot open config file 'cfg/config/etc/broken_1/minimal.cfg' for "
                "reading: [Errno 2] No such file or directory: "
                "u'cfg/config/etc/broken_1/minimal.cfg'"
            )
        )
        self.assert_any_cfg_log_match(
            re.escape(
                "[config] cannot open config file 'cfg/config/resource.cfg' for reading: "
                "[Errno 2] No such file or directory: u'cfg/config/resource.cfg'"
            )
        )

    def test_broken_configuration_2(self):
        """ Configuration is not correct because of a non-existing path

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/config/alignak_broken_2.cfg')
        self.assertFalse(self.conf_is_correct)

        # Error messages
        self.assertEqual(len(self.configuration_errors), 2)
        self.assert_any_cfg_log_match(
            re.escape(
                "[config] cannot open config dir 'cfg/config/not-existing-dir' for reading"
            )
        )
        self.assert_any_cfg_log_match(
            re.escape(
                "[config] cannot open config file 'cfg/config/resource.cfg' for reading: "
                "[Errno 2] No such file or directory: u'cfg/config/resource.cfg'"
            )
        )

    def test_bad_timeperiod(self):
        """ Test bad timeperiod configuration

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/config/alignak_bad_timeperiods.cfg')
        self.assertFalse(self.conf_is_correct)

        self.assert_any_cfg_log_match(
            re.escape(
                "[timeperiod::24x7_bad2] invalid entry 'satourday 00:00-24:00'"
            )
        )
        self.assert_any_cfg_log_match(
            re.escape(
                "[timeperiod::24x7_bad] invalid daterange"
            )
        )

        timeperiod = self.arbiter.conf.timeperiods.find_by_name("24x7")
        self.assertEqual(True, timeperiod.is_correct())
        timeperiod = self.arbiter.conf.timeperiods.find_by_name("24x7_bad")
        self.assertEqual(False, timeperiod.is_correct())
        timeperiod = self.arbiter.conf.timeperiods.find_by_name("24x7_bad2")
        self.assertEqual(False, timeperiod.is_correct())

    def test_bad_contact(self):
        """ Test a service with an unknown contact

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_contact_in_service.cfg')
        self.assertFalse(self.conf_is_correct)
        self.show_configuration_logs()

        # The service got a unknown contact. It should raise an error
        svc = self.arbiter.conf.services.find_srv_by_name_and_hostname("test_host_0",
                                                                       "test_ok_0_badcon")
        print "Contacts:", svc.contacts
        self.assertFalse(svc.is_correct())
        self.assert_any_cfg_log_match(
            "Configuration in service::test_ok_0_badcon is incorrect; from: "
            "cfg/config/service_bad_contact.cfg:1"
        )
        self.assert_any_cfg_log_match(
            "the contact 'IDONOTEXIST' defined for 'test_ok_0_badcon' is unknown"
        )

    def test_bad_notification_period(self):
        """ Configuration is not correct because of an unknown notification_period in a service

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_notificationperiod_in_service.cfg')
        self.assertFalse(self.conf_is_correct)
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in service::test_ok_0_badperiod is incorrect; from: "
            "cfg/config/service_bad_notification_period.cfg:1"
        )
        self.assert_any_cfg_log_match(
            "The notification_period of the service 'test_ok_0_badperiod' "
            "named 'IDONOTEXIST' is unknown!"
        )

    def test_bad_realm_conf(self):
        """ Configuration is not correct because of an unknown realm member in realm and
        an unknown realm in a host

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_realm_member.cfg')
        self.assertFalse(self.conf_is_correct)
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in host::test_host_realm3 is incorrect; from: "
            "cfg/config/host_bad_realm.cfg:31"
        )
        self.assert_any_cfg_log_match(
            r"the host test_host_realm3 got an invalid realm \(Realm3\)!"
        )
        self.assert_any_cfg_log_match(
            r"hosts configuration is incorrect!"
        )
        self.assert_any_cfg_log_match(
            "Configuration in realm::Realm1 is incorrect; from: cfg/config/realm_bad_member.cfg:5"
        )
        self.assert_any_cfg_log_match(
            r"\[realm::Realm1\] as realm, got unknown member 'UNKNOWNREALM'"
        )
        self.assert_any_cfg_log_match(
            "realms configuration is incorrect!"
        )
        self.assert_any_cfg_log_match(
            re.escape(
                "Error: Hosts exist in the realm <Realm \"name\"=u'Realm2' /> "
                "but no poller in this realm"
            )
        )
        self.assert_any_cfg_log_match(
            re.escape(
                "Error: Hosts exist in the realm <Realm \"name\"=u'Realm1' /> "
                "but no poller in this realm"
            )
        )
        self.assert_any_cfg_log_match(
            "Error: Hosts exist in the realm None but no poller in this realm"
        )
        self.assert_any_cfg_log_match(
            "Error : More than one realm are set to the default realm"
        )

    def test_business_rules_bad_realm_conf(self):
        """ Configuration is not correct because of a bad configuration in business rules realms

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/config/alignak_business_rules_bad_realm_conf.cfg')
        self.assertFalse(self.conf_is_correct)
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Error: Business_rule \'test_host_realm1/Test bad services BP rules\' "
            "got hosts from another realm: Realm2"
        )
        self.assert_any_cfg_log_match(
            r"Business_rule \'test_host_realm1/Test bad services BP rules complex\' "
            "got hosts from another realm: Realm2"
        )
        self.assert_any_cfg_log_match(
            r"Business_rule \'test_host_realm1/Test bad host BP rules\' "
            "got hosts from another realm: Realm2"
        )

    def test_bad_satellite_realm_conf(self):
        """ Configuration is not correct because a broker conf has an unknown realm

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_realm_in_broker.cfg')
        self.assertFalse(self.conf_is_correct)
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in broker::Broker-test is incorrect; from: "
            "cfg/config/broker_bad_realm.cfg:1"
        )
        self.assert_any_cfg_log_match(
            "The broker Broker-test got a unknown realm 'NoGood'"
        )

    def test_bad_service_interval(self):
        """ Configuration is not correct because of a bad check_interval in service

        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_check_interval_in_service.cfg')
        self.assertFalse(self.conf_is_correct)
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in service::fake svc1 is incorrect; from: "
            "cfg/config/service_bad_checkinterval.cfg:1"
        )
        self.assert_any_cfg_log_match(
            r"Error while pythonizing parameter \'check_interval\': "
            r"invalid literal for float\(\): 1,555"
        )

    def test_config_contacts(self):
        """ Test contacts configuration

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        self.assertTrue(self.conf_is_correct)

        contact = self.schedulers['scheduler-master'].sched.contacts.find_by_name('test_contact')
        self.assertEqual(contact.contact_name, 'test_contact')
        self.assertEqual(contact.email, 'nobody@localhost')
        self.assertEqual(contact.customs, {u'_VAR2': u'text', u'_VAR1': u'10'})

    def test_config_hosts(self):
        """ Test hosts initial states

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/host_config_all.cfg')
        self.assertTrue(self.conf_is_correct)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name('test_host_0')
        self.assertEqual('DOWN', host.state)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name('test_host_1')
        self.assertEqual('UNREACHABLE', host.state)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name('test_host_2')
        self.assertEqual('UP', host.state)

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name('test_host_3')
        self.assertEqual('UP', host.state)

    def test_config_hosts_names(self):
        """ Test hosts allowed hosts names:
            - Check that it is allowed to have a host with the "__ANTI-VIRG__"
            substring in its hostname
            - Check that the semicolon is a comment delimiter
            - Check that it is possible to have a host with a semicolon in its hostname:
               The consequences of this aren't tested. We try just to send a command but
               other programs which send commands probably don't escape the semicolon.

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/alignak_antivirg.cfg')
        self.assertTrue(self.conf_is_correct, "Configuration is not valid")

        # try to get the host
        # if it is not possible to get the host, it is probably because
        # "__ANTI-VIRG__" has been replaced by ";"
        hst = self.arbiter.conf.hosts.find_by_name('test__ANTI-VIRG___0')
        self.assertIsNotNone(hst, "host 'test__ANTI-VIRG___0' not found")
        self.assertTrue(hst.is_correct(), "config of host '%s' is not correct" % hst.get_name())

        # try to get the host
        hst = self.arbiter.conf.hosts.find_by_name('test_host_1')
        self.assertIsNotNone(hst, "host 'test_host_1' not found")
        self.assertTrue(hst.is_correct(), "config of host '%s' is not true" % (hst.get_name()))

        # try to get the host
        hst = self.arbiter.conf.hosts.find_by_name('test_host_2;with_semicolon')
        self.assertIsNotNone(hst, "host 'test_host_2;with_semicolon' not found")
        self.assertTrue(hst.is_correct(), "config of host '%s' is not true" % hst.get_name())

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name(
            "test_host_2;with_semicolon")
        self.assertIsNotNone(host, "host 'test_host_2;with_semicolon' not found")
        self.assertEqual('UP', host.state)

        # We can send a command by escaping the semicolon.
        command = r'[%lu] PROCESS_HOST_CHECK_RESULT;test_host_2\;with_semicolon;2;down' % (
            time.time())
        self.schedulers['scheduler-master'].sched.run_external_command(command)
        self.external_command_loop()
        self.assertEqual('DOWN', host.state)

    def test_config_services(self):
        """ Test services initial states
        :return: None
        """

        self.print_header()
        self.setup_with_file('cfg/config/service_config_all.cfg')

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_0')
        self.assertEqual('WARNING', svc.state)

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_1')
        self.assertEqual('UNKNOWN', svc.state)

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_2')
        self.assertEqual('CRITICAL', svc.state)

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_3')
        self.assertEqual('OK', svc.state)

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_4')
        self.assertEqual('OK', svc.state)

    def test_host_unreachable_values(self):
        """ Test unreachable value in:
        * flap_detection_options
        * notification_options
        * snapshot_criteria

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/host_unreachable.cfg')
        self.assertTrue(self.conf_is_correct)

        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

        host0 = self.arbiter.conf.hosts.find_by_name('host_A')
        host1 = self.arbiter.conf.hosts.find_by_name('host_B')
        self.assertEqual(['d', 'x', 'r', 'f', 's'], host0.notification_options)
        self.assertEqual(['o', 'd', 'x'], host0.flap_detection_options)
        self.assertEqual(['d', 'x'], host0.snapshot_criteria)
        # self.assertEqual('x', host0.initial_state)
        # self.assertEqual('x', host0.freshness_state)

        self.assertEqual(1, len(host0.act_depend_of_me))
        self.assertEqual(['d', 'x'], host0.act_depend_of_me[0][1])

        self.assertEqual(1, len(host0.chk_depend_of_me))
        self.assertEqual(['x'], host0.chk_depend_of_me[0][1])

        self.assertEqual(1, len(host1.act_depend_of))
        self.assertEqual(['d', 'x'], host1.act_depend_of[0][1])

        self.assertEqual(1, len(host1.chk_depend_of))
        self.assertEqual(['x'], host1.chk_depend_of[0][1])
