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
        self.assertTrue(self.schedulers[0].conf.conf_is_correct)
        self.assertTrue(self.conf_is_correct)
        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_broken_configuration(self):
        """
        Configuration is not correct because of a wrong relative path in the main config file
        :return: None
        """
        self.print_header()
        with self.assertRaises(SystemExit):
            self.setup_with_file('cfg/config/alignak_broken_1.cfg')
        self.assertFalse(self.conf_is_correct)
        self.show_configuration_logs()

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
            "Configuration in service::test_ok_0_badcon is incorrect; from: "\
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
            "Configuration in service::test_ok_0_badperiod is incorrect; from: "\
            "cfg/config/../default/daemons/reactionner-master.cfg:42"
        )
        self.assert_any_cfg_log_match(
            "The notification_period of the service 'test_ok_0_badperiod' "\
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
            "the host test_host_realm2 is in the realm "
        )
        self.assert_any_cfg_log_match(
            "the host test_host_realm1 is in the realm "
        )
        self.assert_any_cfg_log_match(
            "the host test_host_realm3 is in the realm Realm3"
        )
        # self.assert_any_cfg_log_match(
        #     "The realm Realm2 has hosts but no scheduler!"
        # )
        self.assert_any_cfg_log_match(
            "There are 6 hosts defined, and 3 hosts dispatched in the realms. "
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

        cg = self.schedulers[0].sched.hosts.find_by_name('test_host_0')
        self.assertEqual('DOWN', cg.state)

        cg = self.schedulers[0].sched.hosts.find_by_name('test_host_1')
        self.assertEqual('UNREACHABLE', cg.state)

        cg = self.schedulers[0].sched.hosts.find_by_name('test_host_2')
        self.assertEqual('UP', cg.state)

        cg = self.schedulers[0].sched.hosts.find_by_name('test_host_3')
        self.assertEqual('UP', cg.state)

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

