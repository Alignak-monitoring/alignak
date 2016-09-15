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

"""
This file contains the test for the Alignak configuration checks
"""
import os
import re
import time
from alignak_test import AlignakTest


class TestConfig(AlignakTest):
    """
    This class tests the configuration
    """
    def test_config_ok(self):
        """
        Default configuration has no loading problems ...
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        self.assertTrue(self.conf_is_correct)

        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

        # Arbiter is named as in the configuration
        self.assertTrue(self.arbiter.conf.conf_is_correct)
        arbiter_link = self.arbiter.conf.arbiters.find_by_name('arbiter-master')
        self.assertIsNotNone(arbiter_link)
        self.assertListEqual(arbiter_link.configuration_errors, [])
        self.assertListEqual(arbiter_link.configuration_warnings, [])

        # Schedulers
        self.assertTrue(self.arbiter.conf.conf_is_correct)
        scheduler_link= self.arbiter.conf.schedulers.find_by_name('scheduler-master')
        self.assertIsNotNone(scheduler_link)
        # Scheduler configuration is ok
        self.assertTrue(self.schedulers[0].conf.conf_is_correct)

        # Broker, Poller, Reactionner
        link = self.arbiter.conf.brokers.find_by_name('broker-master')
        self.assertIsNotNone(link)
        link = self.arbiter.conf.pollers.find_by_name('poller-master')
        self.assertIsNotNone(link)
        link = self.arbiter.conf.reactionners.find_by_name('reactionner-master')
        self.assertIsNotNone(link)

        # Receiver - no default receiver created
        link = self.arbiter.conf.receivers.find_by_name('receiver-master')
        self.assertIsNotNone(link)

    def test_config_ok_no_declared_daemons(self):
        """
        Default configuration has no loading problems ... but no daemons are defined
        The arbiter will create default daemons except or the receiver.
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/host_config_simple.cfg')
        self.assertTrue(self.conf_is_correct)

        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

        # Arbiter is named as Default
        self.assertTrue(self.arbiter.conf.conf_is_correct)
        arbiter_link = self.arbiter.conf.arbiters.find_by_name('Default-Arbiter')
        self.assertIsNotNone(arbiter_link)
        self.assertListEqual(arbiter_link.configuration_errors, [])
        self.assertListEqual(arbiter_link.configuration_warnings, [])

        # Schedulers
        link= self.arbiter.conf.schedulers.find_by_name('Default-Scheduler')
        self.assertIsNotNone(link)
        # Scheduler configuration is ok
        self.assertTrue(self.schedulers[0].conf.conf_is_correct)

        # Broker, Poller, Reactionner
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
        if os.name == 'nt':
            return

        self.print_header()
        self.setup_with_file('cfg/conf_in_symlinks/alignak_conf_in_symlinks.cfg')

        svc = self.arbiter.conf.services.find_srv_by_name_and_hostname("test_host_0", "test_HIDDEN")
        self.assertIsNotNone(svc)

    def test_bad_template_use_itself(self):
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/config/bad_template_use_itself.cfg')
        self.assertFalse(self.conf_is_correct)
        self.assertIn(u"Host u'bla' use/inherits from itself ! Imported from: "
                      u"cfg/config/../default/daemons/reactionner-master.cfg:42",
                      self.arbiter.conf.hosts.configuration_errors)

    def test_bad_host_use_undefined_template(self):
        self.print_header()
        self.setup_with_file('cfg/config/bad_host_use_undefined_template.cfg')
        self.assertTrue(self.conf_is_correct)
        self.assertIn(u"[host::bla] no contacts nor contact_groups property",
                  self.arbiter.conf.hosts.configuration_warnings)
        self.assertIn(u"Host u'bla' use/inherit from an unknown template (u'undefined') ! "
                  u"Imported from: cfg/config/bad_host_use_undefined_template.cfg:2",
                  self.arbiter.conf.hosts.configuration_warnings)

    def test_broken_configuration(self):
        """
        Configuration is not correct because of a wrong relative path in the main config file
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
                "[config] cannot open config file 'cfg/config/etc/broken_1/minimal.cfg' for reading: "
                "[Errno 2] No such file or directory: u'cfg/config/etc/broken_1/minimal.cfg'"
            )
        )
        self.assert_any_cfg_log_match(
            re.escape(
                "[config] cannot open config file 'cfg/config/resource.cfg' for reading: "
                "[Errno 2] No such file or directory: u'cfg/config/resource.cfg'"
            )
        )

    def test_bad_template_use_itself(self):
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/config/bad_template_use_itself.cfg')
        self.assertFalse(self.conf_is_correct)

        self.assert_any_cfg_log_match(
            re.escape(
                "Host u'bla' use/inherits from itself ! "
                "Imported from: cfg/config/bad_template_use_itself.cfg:1"
            )
        )

    def test_bad_host_use_undefined_template(self):
        self.print_header()
        self.setup_with_file('cfg/config/bad_host_use_undefined_template.cfg')
        self.assertTrue(self.conf_is_correct)
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            re.escape(
                "[host::bla] no contacts nor contact_groups property"
            )
        )
        self.assert_any_cfg_log_match(
            re.escape(
                "Host u'bla' use/inherit from an unknown template (u'undefined') ! "
                "Imported from: cfg/config/bad_host_use_undefined_template.cfg:2"
            )
        )

    def test_bad_timeperiod(self):
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

        tp = self.arbiter.conf.timeperiods.find_by_name("24x7")
        self.assertEqual(True, tp.is_correct())
        tp = self.arbiter.conf.timeperiods.find_by_name("24x7_bad")
        self.assertEqual(False, tp.is_correct())

    def test_bad_contact(self):
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/config/alignak_bad_contact_call.cfg')
        self.assertFalse(self.conf_is_correct)
        self.show_configuration_logs()

        # The service got a unknow contact. It should raise an error
        svc = self.arbiter.conf.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0_badcon")
        print "Contacts:", svc.contacts
        self.assertFalse(svc.is_correct())
        self.assert_any_cfg_log_match(
            "Configuration in service::test_ok_0_badcon is incorrect; from: " \
            "cfg/config/../default/daemons/reactionner-master.cfg:42"
        )
        self.assert_any_cfg_log_match(
            "the contact 'IDONOTEXIST' defined for 'test_ok_0_badcon' is unknown"
        )

    def test_bad_notification_period(self):
        """
        Config is not correct because of an unknown notification_period
        :return:
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/config/alignak_bad_notification_period.cfg')
        self.assertFalse(self.conf_is_correct)
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in service::test_ok_0_badperiod is incorrect; from: " \
            "cfg/config/../default/daemons/reactionner-master.cfg:42"
        )
        self.assert_any_cfg_log_match(
            "The notification_period of the service 'test_ok_0_badperiod' " \
            "named 'IDONOTEXIST' is unknown!"
        )

    def test_bad_realm_conf(self):
        """
        Config is not correct because of an unknown notification_period
        :return:
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/config/alignak_bad_realm_conf.cfg')
        self.assertFalse(self.conf_is_correct)
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in host::test_host_realm3 is incorrect; from: "
            "cfg/config/../default/daemons/reactionner-master.cfg:90"
        )
        self.assert_any_cfg_log_match(
            "the host test_host_realm3 got an invalid realm \(Realm3\)!"
        )
        self.assert_any_cfg_log_match(
            "Configuration in realm::Realm1 is incorrect; from: cfg/config/../default/daemons/reactionner-master.cfg:47"
        )
        self.assert_any_cfg_log_match(
            "\[realm::Realm1\] as realm, got unknown member 'UNKNOWNREALM'"
        )
        self.assert_any_cfg_log_match(
            "Error : More than one realm are set to the default realm"
        )
        self.assert_any_cfg_log_match(
            "Error: the realm configuration of yours hosts is not good because there is more "
            "than one realm in one pack \(host relations\):"
        )
        self.assert_any_cfg_log_match(
            "the host test_host_realm2 is in the realm Realm2"
        )
        self.assert_any_cfg_log_match(
            "the host test_host_realm1 is in the realm Realm1"
        )
        self.assert_any_cfg_log_match(
            "the host test_host_realm3 do not have a realm"
        )
        # self.assert_any_cfg_log_match(
        #     "The realm Realm2 has hosts but no scheduler!"
        # )
        self.assert_any_cfg_log_match(
            "There are 6 hosts defined, and 3 hosts dispatched in the realms. "
            "Some hosts have been ignored"
        )

    def test_business_rules_bad_realm_conf(self):
        """
        Config is not correct because of bad configuration in BR realms
        :return:
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
            "Business_rule \'test_host_realm1/Test bad services BP rules complex'\ "
            "got hosts from another realm: Realm2"
        )
        self.assert_any_cfg_log_match(
            "Business_rule \'test_host_realm1/Test bad services BP rules complex\' "
            "got hosts from another realm: Realm2"
        )
        self.assert_any_cfg_log_match(
            "Business_rule \'test_host_realm1/Test bad host BP rules\' "
            "got hosts from another realm: Realm2"
        )
        self.assert_any_cfg_log_match(
            "Error: the realm configuration of yours hosts is not good because there is more "
            "than one realm in one pack \(host relations\):"
        )
        self.assert_any_cfg_log_match(
            "the host test_host_realm2 is in the realm "
        )
        self.assert_any_cfg_log_match(
            "the host test_host_realm1 is in the realm "
        )
        self.assert_any_cfg_log_match(
            "There are 4 hosts defined, and 2 hosts dispatched in the realms. "
            "Some hosts have been ignored"
        )

    def test_bad_satellite_realm_conf(self):
        """
        Config is not correct because of an unknown notification_period
        :return:
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/config/alignak_bad_sat_realm_conf.cfg')
        self.assertFalse(self.conf_is_correct)
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in broker::Broker-test is incorrect; from: "
            "cfg/config/../default/daemons/reactionner-master.cfg:42"
        )
        self.assert_any_cfg_log_match(
            "The broker Broker-test got a unknown realm 'NoGood'"
        )

    def test_bad_service_interval(self):
        """
        Config is not correct because of a bad service interval configuration
        :return:
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/config/alignak_bad_service_interval.cfg')
        self.assertFalse(self.conf_is_correct)
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in service::fake svc1 is incorrect; from: "
            "cfg/config/../default/daemons/reactionner-master.cfg:50"
        )
        self.assert_any_cfg_log_match(
            "Error while pythonizing parameter \'check_interval\': "
            "invalid literal for float\(\): 1,555"
        )

    def test_config_hosts(self):
        """
        Test hosts initial states
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/host_config_all.cfg')
        self.assertTrue(self.conf_is_correct)

        cg = self.schedulers[0].sched.hosts.find_by_name('test_host_0')
        self.assertEqual('DOWN', cg.state)

        cg = self.schedulers[0].sched.hosts.find_by_name('test_host_1')
        self.assertEqual('UNREACHABLE', cg.state)

        cg = self.schedulers[0].sched.hosts.find_by_name('test_host_2')
        self.assertEqual('UP', cg.state)

        cg = self.schedulers[0].sched.hosts.find_by_name('test_host_3')
        self.assertEqual('UP', cg.state)

    def test_config_hosts_names(self):
        """
        Test hosts allowed hosts names:
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

        # We can send a command by escaping the semicolon.
        command = '[%lu] PROCESS_HOST_CHECK_RESULT;test_host_2\;with_semicolon;2;down' % (
            time.time())
        self.schedulers[0].sched.run_external_command(command)

        # can need 2 run for get the consum (I don't know why)
        self.scheduler_loop(1, [])
        self.scheduler_loop(1, [])

    def test_config_services(self):
        """
        Test services initial states
        :return: None
        """

        self.print_header()
        self.setup_with_file('cfg/config/service_config_all.cfg')

        cg = self.schedulers[0].sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_0')
        self.assertEqual('WARNING', cg.state)

        cg = self.schedulers[0].sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_1')
        self.assertEqual('UNKNOWN', cg.state)

        cg = self.schedulers[0].sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_2')
        self.assertEqual('CRITICAL', cg.state)

        cg = self.schedulers[0].sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_3')
        self.assertEqual('OK', cg.state)

        cg = self.schedulers[0].sched.services.find_srv_by_name_and_hostname('test_host_0', 'test_service_4')
        self.assertEqual('OK', cg.state)

