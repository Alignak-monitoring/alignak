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
from alignak_test import AlignakTest, unittest
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
        self.setup_with_file('cfg/cfg_default.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

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

    def test_config_conf_inner_properties(self):
        """ Default configuration has no loading problems ... and inner default proerties are
        correctly values

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        # Arbiter configuration is correct
        assert self.arbiter.conf.conf_is_correct

        # Configuration inner properties are valued
        assert self.arbiter.conf.prefix == ''
        assert self.arbiter.conf.main_config_file == \
                         os.path.abspath('cfg/cfg_default.cfg')
        assert self.arbiter.conf.config_base_dir == 'cfg'

    def test_config_ok_no_declared_daemons(self):
        """ Default configuration has no loading problems ... but no daemons are defined
        The arbiter will create default daemons except for the receiver.

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_config_simple.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        # Arbiter named as Default
        assert self.arbiter.conf.conf_is_correct
        arbiter_link = self.arbiter.conf.arbiters.find_by_name('Default-Arbiter')
        assert arbiter_link is not None
        assert arbiter_link.configuration_errors == []
        assert arbiter_link.configuration_warnings == []

        # Scheduler named as Default
        link = self.arbiter.conf.schedulers.find_by_name('Default-Scheduler')
        assert link is not None
        # Scheduler configuration is ok
        assert self.schedulers['Default-Scheduler'].sched.conf.conf_is_correct

        # Broker, Poller, Reactionner named as Default
        link = self.arbiter.conf.brokers.find_by_name('Default-Broker')
        assert link is not None
        link = self.arbiter.conf.pollers.find_by_name('Default-Poller')
        assert link is not None
        # link = self.arbiter.conf.reactionners.find_by_name('Default-Reactionner')
        # assert link is not None

        # Receiver - no default receiver created
        link = self.arbiter.conf.receivers.find_by_name('Default-Receiver')
        assert link is None

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
        assert svc is not None

    def test_define_syntax(self):
        """ Test that define{} syntax is correctly checked: spaces, multi-lines, white-spaces
        do not raise any error ...

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/alignak_define_with_space.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name('spaced-host')
        assert host is not None

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
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "myhost", "same_service")
        assert svc is not None
        assert 1 == svc.definition_order
        assert 'general1' == svc.check_command.command.command_name

    def test_service_not_hostname(self):
        """ Test the 'not hostname' syntax

        The service test_ok_0 is applied with a host_group on "test_host_0","test_host_1"
        but have a host_name with !"test_host_1" so it will only be attached to "test_host_0"

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/alignak_service_not_hostname.cfg')
        assert self.conf_is_correct

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        assert host is not None
        assert host.is_correct()

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # Check that the service is attached to test_host_0
        assert svc is not None
        assert svc.is_correct()

        # Check that the service is NOT attached to test_host_1
        svc_not = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_1", "test_ok_0")
        assert svc_not is None

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
        assert self.conf_is_correct

        # Service linked to an host
        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "MYHOST", "SSH")
        assert svc is not None

        # Service linked to several hosts
        for hname in ["MYHOST2", "MYHOST3"]:
            svc = self.schedulers['scheduler-master'].sched.services.\
                find_srv_by_name_and_hostname(hname, "SSH")
            assert svc is not None

        # Service template linked to an host template
        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host", "svc_inherited")
        assert svc is not None
        assert 'check_ssh' == svc.check_command.command.command_name

    def test_service_with_no_host(self):
        """ A service not linked to any host raises an error

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/alignak_service_nohost.cfg')
        assert not self.conf_is_correct

        assert "the service 'NOEXIST/will_error' got an unknown host_name" in \
                      self.configuration_warnings

        assert "services configuration is incorrect:" in \
                      self.configuration_errors
        assert "[service::will_error] unknown host_name 'NOEXIST'" in \
                      self.configuration_errors
        assert "Configuration in service::NOEXIST/will_error is incorrect; " \
               "from: cfg/config/../default/daemons/reactionner-master.cfg:47" in \
               self.configuration_errors

    @unittest.skip("Temporary skipped because the error is no more raised!")
    def test_bad_template_use_itself(self):
        """ Detect a template that uses itself as a template

        This test that an host uses a template but this template is itself

        Note that this error is no more raised !

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_host_template_itself.cfg')
        assert not self.conf_is_correct
        # TODO, issue #344
        assert "host bla use/inherits from itself ! " \
               "from: cfg/config/host_bad_template_itself.cfg:1" in self.configuration_errors
        assert "hosts configuration is incorrect:" in self.configuration_errors

    def test_use_undefined_template(self):
        """ Test unknown template detection for host and service

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_bad_undefined_template.cfg')
        assert self.conf_is_correct
        self.show_configuration_logs()

        # TODO, issue #344
        assert "host test_host use/inherit from an unknown template: undefined_host ! " \
               "from: cfg/config/use_undefined_template.cfg:1" in \
                      self.configuration_warnings
        assert "service test_host/test_service use/inherit from an unknown template: " \
               "undefined_service ! from: cfg/config/use_undefined_template.cfg:6" in \
                      self.configuration_warnings

    def test_broken_configuration(self):
        """ Configuration is not correct because of a wrong relative path in the main config file

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/alignak_broken_1.cfg')
        assert not self.conf_is_correct

        # Error messages
        assert len(self.configuration_errors) == 2
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
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/alignak_broken_2.cfg')
        assert not self.conf_is_correct

        # Error messages
        assert len(self.configuration_errors) == 2
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
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/alignak_bad_timeperiods.cfg')
        assert not self.conf_is_correct

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
        assert True == timeperiod.is_correct()
        timeperiod = self.arbiter.conf.timeperiods.find_by_name("24x7_bad")
        assert False == timeperiod.is_correct()
        timeperiod = self.arbiter.conf.timeperiods.find_by_name("24x7_bad2")
        assert False == timeperiod.is_correct()

    def test_bad_contact(self):
        """ Test a service with an unknown contact

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_contact_in_service.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

        # The service got a unknown contact. It should raise an error
        svc = self.arbiter.conf.services.find_srv_by_name_and_hostname("test_host_0",
                                                                       "test_ok_0_badcon")
        print "Contacts:", svc.contacts
        assert not svc.is_correct()
        self.assert_any_cfg_log_match(
            "Configuration in service::test_host_0/test_ok_0_badcon "
            "is incorrect; from: cfg/config/service_bad_contact.cfg:1"
        )
        self.assert_any_cfg_log_match(
            "the contact 'IDONOTEXIST' defined for "
            "'test_host_0/test_ok_0_badcon' is unknown"
        )

    def test_bad_notification_period(self):
        """ Configuration is not correct because of an unknown notification_period in a service

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_notificationperiod_in_service.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in service::test_host_0/test_ok_0_badperiod is incorrect; from: "
            "cfg/config/service_bad_notification_period.cfg:1"
        )
        self.assert_any_cfg_log_match(
            "The notification_period of the service 'test_host_0/test_ok_0_badperiod' "
            "named 'IDONOTEXIST' is unknown!"
        )

    def test_bad_realm_conf(self):
        """ Configuration is not correct because of an unknown realm member in realm and
        an unknown realm in a host

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_realm_member.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in host::test_host_realm3 is incorrect; from: "
            "cfg/config/host_bad_realm.cfg:31"
        )
        self.assert_any_cfg_log_match(
            r"the host test_host_realm3 got an invalid realm \(Realm3\)!"
        )
        self.assert_any_cfg_log_match(
            r"hosts configuration is incorrect:"
        )
        self.assert_any_cfg_log_match(
            "Configuration in realm::Realm1 is incorrect; from: cfg/config/realm_bad_member.cfg:5"
        )
        self.assert_any_cfg_log_match(
            r"\[realm::Realm1\] got an unknown member \'UNKNOWNREALM\'"
        )
        self.assert_any_cfg_log_match(
            "realms configuration is incorrect:"
        )
        self.assert_any_cfg_log_match(
            re.escape(
                "Hosts exist in the realm Realm2 but there is no poller in this realm"
            )
        )
        self.assert_any_cfg_log_match(
            re.escape(
                "Hosts exist in the realm Realm1 but there is no poller in this realm"
            )
        )
        self.assert_any_cfg_log_match(
            "Hosts exist in the realm All but there is no poller in this realm"
        )
        self.assert_any_cfg_log_match(
            "More than one realm are set to the default realm"
        )

    def test_business_rules_incorrect(self):
        """ Business rules use services which don't exist.
        We want the arbiter to output an error message and exit
        in a controlled manner.
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/business_correlator_broken.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(re.escape(
            "services configuration is incorrect:",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::test_host_0/Simple_1Of_1unk_svc] business_rule is invalid",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::test_host_0/Simple_1Of_1unk_svc]: Business rule uses unknown "
            "service test_host_0/db3",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::test_host_0/Simple_1Of_1unk_svc is incorrect; "
            "from: cfg/config/../default/daemons/reactionner-master.cfg:128",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::test_host_0/Simple_1Of_1unk_host] business_rule is invalid",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::test_host_0/Simple_1Of_1unk_host]: Business rule uses "
            "unknown host test_host_9",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::test_host_0/Simple_1Of_1unk_host is incorrect; "
            "from: cfg/config/../default/daemons/reactionner-master.cfg:144",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::test_host_0/ERP_unk_svc] business_rule is invalid",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::test_host_0/ERP_unk_svc]: Business rule uses unknown "
            "service test_host_0/web100",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::test_host_0/ERP_unk_svc]: Business rule uses unknown service test_host_0/lvs100",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::test_host_0/ERP_unk_svc is incorrect; "
            "from: cfg/config/../default/daemons/reactionner-master.cfg:136",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::Will Miss hostname for this service] unknown host_name 'Dont expect to find this'",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::Dont expect to find this/Will Miss hostname "
            "for this service is incorrect; "
            "from: cfg/config/../default/daemons/reactionner-master.cfg:162",
        ))

    def test_business_rules_hostgroup_expansion_errors(self):
        """ Configuration is not correct  because of a bad syntax in BR hostgroup expansion """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/business_correlator_expand_expression_broken.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

        # Warnings
        self.assert_any_cfg_log_match(re.escape(
            "host test_host_02 use/inherit from an unknown template: tag1 ! "
            "from: cfg/config/../default/daemons/reactionner-master.cfg:58"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "host test_host_02 use/inherit from an unknown template: tag2 ! "
            "from: cfg/config/../default/daemons/reactionner-master.cfg:58"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "host test_host_01 use/inherit from an unknown template: tag1 ! "
            "from: cfg/config/../default/daemons/reactionner-master.cfg:49"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "host test_host_01 use/inherit from an unknown template: tag2 ! "
            "from: cfg/config/../default/daemons/reactionner-master.cfg:49"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "service dummy/bprule_invalid_regex use/inherit from an unknown template: "
            "generic-service_bcee_bcee ! "
            "from: cfg/config/../default/daemons/reactionner-master.cfg:142"
        ))
        
        # Errors
        self.assert_any_cfg_log_match(re.escape(
            "services configuration is incorrect:",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::dummy/bprule_empty_regex] business_rule is invalid",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::dummy/bprule_empty_regex]: Business rule got an empty "
            "result for pattern r:fake,srv1",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::dummy/bprule_empty_regex is incorrect; "
            "from: cfg/config/../default/daemons/reactionner-master.cfg:128",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::dummy/bprule_unkonwn_service] business_rule is invalid",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::dummy/bprule_unkonwn_service]: Business rule got an empty "
            "result for pattern g:hostgroup_01,srv3",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::dummy/bprule_unkonwn_service is incorrect; "
            "from: cfg/config/../default/daemons/reactionner-master.cfg:135",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::dummy/bprule_unkonwn_hostgroup] business_rule is invalid",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::dummy/bprule_unkonwn_hostgroup]: Business rule got an empty "
            "result for pattern g:hostgroup_03,srv1",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::dummy/bprule_unkonwn_hostgroup is incorrect; "
            "from: cfg/config/../default/daemons/reactionner-master.cfg:121",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::dummy/bprule_invalid_regex] business_rule is invalid",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::dummy/bprule_invalid_regex]: Business rule uses invalid "
            "regex r:test_host_0[,srv1: unexpected end of regular expression",
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::dummy/bprule_invalid_regex is incorrect; "
            "from: cfg/config/../default/daemons/reactionner-master.cfg:142"
        ))

    def test_business_rules_bad_realm_conf(self):
        """ Configuration is not correct because of a bad configuration in business rules realms

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/business_rules_bad_realm_conf.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

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
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_realm_in_broker.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "The broker Broker-test got a unknown realm 'NoGood'"
        )

    def test_bad_service_interval(self):
        """ Configuration is not correct because of a bad check_interval in service

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_check_interval_in_service.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in service::test_host_0/fake svc1 is incorrect; "
            "from: cfg/config/service_bad_checkinterval.cfg:1"
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
        assert self.conf_is_correct

        contact = self.schedulers['scheduler-master'].sched.contacts.find_by_name('test_contact')
        assert contact.contact_name == 'test_contact'
        assert contact.email == 'nobody@localhost'
        assert contact.customs == {u'_VAR2': u'text', u'_VAR1': u'10'}

    def test_config_hosts(self):
        """ Test hosts initial states

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/host_config_all.cfg')
        assert self.conf_is_correct

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name('test_host_000')
        assert 'DOWN' == host.state

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name('test_host_001')
        assert 'UNREACHABLE' == host.state

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name('test_host_002')
        assert 'UP' == host.state

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name('test_host_003')
        assert 'UP' == host.state

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
        assert self.conf_is_correct, "Configuration is not valid"

        # try to get the host
        # if it is not possible to get the host, it is probably because
        # "__ANTI-VIRG__" has been replaced by ";"
        hst = self.arbiter.conf.hosts.find_by_name('test__ANTI-VIRG___0')
        assert hst is not None, "host 'test__ANTI-VIRG___0' not found"
        assert hst.is_correct(), "config of host '%s' is not correct" % hst.get_name()

        # try to get the host
        hst = self.arbiter.conf.hosts.find_by_name('test_host_1')
        assert hst is not None, "host 'test_host_1' not found"
        assert hst.is_correct(), "config of host '%s' is not true" % (hst.get_name())

        # try to get the host
        hst = self.arbiter.conf.hosts.find_by_name('test_host_2;with_semicolon')
        assert hst is not None, "host 'test_host_2;with_semicolon' not found"
        assert hst.is_correct(), "config of host '%s' is not true" % hst.get_name()

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name(
            "test_host_2;with_semicolon")
        assert host is not None, "host 'test_host_2;with_semicolon' not found"
        assert 'UP' == host.state

        # We can send a command by escaping the semicolon.
        command = r'[%lu] PROCESS_HOST_CHECK_RESULT;test_host_2\;with_semicolon;2;down' % (
            time.time())
        self.schedulers['scheduler-master'].sched.run_external_command(command)
        self.external_command_loop()
        assert 'DOWN' == host.state

    def test_config_services(self):
        """ Test services initial states
        :return: None
        """

        self.print_header()
        self.setup_with_file('cfg/config/service_config_all.cfg')

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_0')
        assert 'WARNING' == svc.state

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_1')
        assert 'UNKNOWN' == svc.state

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_2')
        assert 'CRITICAL' == svc.state

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_3')
        assert 'OK' == svc.state

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_4')
        assert 'OK' == svc.state

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_5')
        assert 'UNREACHABLE' == svc.state

    def test_host_unreachable_values(self):
        """ Test unreachable value in:
        * flap_detection_options
        * notification_options
        * snapshot_criteria

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/host_unreachable.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # One warning message for host dependency ... A depends of B and they
        # both define an host_dependency;)
        assert len(self.configuration_warnings) == 1

        host_A = self.arbiter.conf.hosts.find_by_name('host_A')
        host_B = self.arbiter.conf.hosts.find_by_name('host_B')
        # Host template defines ['d', 'u', 'r', 'f', 's'] but, for host,'u' is replaced with 'x'
        assert ['d', 'x', 'r', 'f', 's'] == host_A.notification_options
        assert ['o', 'd', 'x'] == host_A.flap_detection_options
        assert ['d', 'x'] == host_A.snapshot_criteria
        assert 'o' == host_A.initial_state
        assert 'd' == host_A.freshness_state

        assert 1 == len(host_A.act_depend_of_me)
        assert ['d', 'x'] == host_A.act_depend_of_me[0][1]

        assert 1 == len(host_A.chk_depend_of_me)
        assert ['x'] == host_A.chk_depend_of_me[0][1]

        assert 1 == len(host_B.act_depend_of)
        assert ['d', 'x'] == host_B.act_depend_of[0][1]

        assert 1 == len(host_B.chk_depend_of)
        assert ['x'] == host_B.chk_depend_of[0][1]

    def test_macro_modulation(self):
        """ Detect macro modulation configuration errors

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/macros_modulation_broken.cfg')
        assert not self.conf_is_correct

        assert "macromodulations configuration is incorrect:" in self.configuration_errors

        # MM without macro definition
        assert "Configuration in macromodulation::MODULATION2 is incorrect; " \
               "from: cfg/config/macros_modulation_broken.cfg:10" in \
                      self.configuration_errors
        assert "The modulation_period of the macromodulation 'MODULATION2' " \
                      "named '24x7' is unknown!" in \
                      self.configuration_errors
        assert "[macromodulation::MODULATION2] contains no macro definition" in \
                      self.configuration_errors

        # MM without name
        assert "a macromodulation item has been defined without macromodulation_name, " \
               "from: cfg/config/macros_modulation_broken.cfg:3" in self.configuration_errors
        assert "The modulation_period of the macromodulation 'unnamed' " \
               "named '24x7' is unknown!" in self.configuration_errors
        assert "[macromodulation::unnamed] macromodulation_name property is missing" in \
                  self.configuration_errors
        assert "Configuration in macromodulation::unnamed is incorrect; " \
               "from: cfg/config/macros_modulation_broken.cfg:3" in self.configuration_errors

    def test_checks_modulation(self):
        """ Detect checks modulation configuration errors

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/checks_modulation_broken.cfg')
        assert not self.conf_is_correct

        # CM without check_command definition
        assert "Configuration in checkmodulation::MODULATION is incorrect; " \
                      "from: cfg/config/checks_modulation_broken.cfg:9" in \
                      self.configuration_errors
        assert "[checkmodulation::MODULATION] check_command property is missing" in \
                      self.configuration_errors

        # MM without name
        assert "Configuration in checkmodulation::Unnamed is incorrect; " \
                      "from: cfg/config/checks_modulation_broken.cfg:2" in \
                      self.configuration_errors
        assert "a checkmodulation item has been defined without checkmodulation_name, " \
                      "from: cfg/config/checks_modulation_broken.cfg:2" in \
                      self.configuration_errors
        assert "The check_period of the checkmodulation 'Unnamed' named '24x7' is unknown!" in \
                      self.configuration_errors
        assert "[checkmodulation::Unnamed] checkmodulation_name property is missing" in \
                      self.configuration_errors
        assert "checkmodulations configuration is incorrect:" in \
                      self.configuration_errors

    def test_business_impact__modulation(self):
        """ Detect business impact modulation configuration errors

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/businesssimpact_modulation_broken.cfg')
        assert not self.conf_is_correct

        # BI modulation without name definition
        assert "Configuration in businessimpactmodulation::Unnamed is incorrect; " \
                      "from: cfg/config/businesssimpact_modulation_broken.cfg:2" in \
                      self.configuration_errors
        assert "The modulation_period of the businessimpactmodulation 'Unnamed' " \
                      "named '24x7' is unknown!" in \
                      self.configuration_errors
        assert "businessimpactmodulations configuration is incorrect:" in \
                      self.configuration_errors

        # MM without name
        # assert "Configuration in businessimpactmodulation::Unnamed is incorrect; " \
        #               "from: cfg/config/businesssimpact_modulation_broken.cfg:2" in \
        #               self.configuration_errors
        # assert "a businessimpactmodulation item has been defined without " \
        #               "business_impact_modulation_name, from: " \
        #               "cfg/config/businesssimpact_modulation_broken.cfg:2" in \
        #               self.configuration_errors
        # assert "The modulation_period of the businessimpactmodulation 'Unnamed' " \
        #               "named '24x7' is unknown!" in \
        #               self.configuration_errors
        # assert "[businessimpactmodulation::Unnamed] business_impact_modulation_name " \
        #               "property is missing" in \
        #               self.configuration_errors
        # assert "businessimpactmodulations configuration is incorrect:" in \
        #               self.configuration_errors

    def test_checks_modulation(self):
        """ Detect checks modulation configuration errors

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/checks_modulation_broken.cfg')
        assert not self.conf_is_correct

        # CM without check_command definition
        assert "Configuration in checkmodulation::MODULATION is incorrect; " \
                      "from: cfg/config/checks_modulation_broken.cfg:9" in \
                      self.configuration_errors
        assert "[checkmodulation::Unnamed] a check_command is invalid" in \
                      self.configuration_errors

        # MM without name
        assert "Configuration in checkmodulation::Unnamed is incorrect; " \
                      "from: cfg/config/checks_modulation_broken.cfg:2" in \
                      self.configuration_errors
        assert "The check_period of the checkmodulation 'Unnamed' named '24x7' is unknown!" in \
                      self.configuration_errors
        assert "[checkmodulation::Unnamed] a check_command is invalid" in \
                      self.configuration_errors
        assert "checkmodulations configuration is incorrect:" in \
                      self.configuration_errors
