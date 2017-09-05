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
import pytest


class TestConfig(AlignakTest):
    """
    This class tests the configuration
    """

    def test_config_ok(self):
        """ Default shipped configuration has no loading problems ...

        :return: None
        """
        self.print_header()
        self.setup_with_file('../etc/alignak.cfg')
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

    def test_config_test_ok(self):
        """ Default test configuration has no loading problems ...

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

        # Broker, Poller, Reactionner and Receiver named as in the configuration
        link = self.arbiter.conf.brokers.find_by_name('broker-master')
        assert link is not None
        link = self.arbiter.conf.pollers.find_by_name('poller-master')
        assert link is not None
        link = self.arbiter.conf.reactionners.find_by_name('reactionner-master')
        assert link is not None
        link = self.arbiter.conf.receivers.find_by_name('receiver-master')
        assert link is not None

    def test_config_conf_inner_properties(self):
        """ Default configuration has no loading problems ... and inner default proerties are
        correctly valued

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
        assert self.arbiter.conf.main_config_file == os.path.abspath('cfg/cfg_default.cfg')
        assert self.arbiter.conf.config_base_dir == 'cfg'
        # Default Alignak name is the arbiter name
        assert self.arbiter.conf.alignak_name == 'arbiter-master'

    def test_config_conf_inner_properties(self):
        """ Default configuration with an alignak_name property

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default_alignak_name.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        # Arbiter configuration is correct
        assert self.arbiter.conf.conf_is_correct

        # Alignak name is defined in the arbiter
        assert self.arbiter.conf.alignak_name == 'my_alignak'
        assert self.arbiter.alignak_name == 'my_alignak'

        # Alignak name is defined in the configuration dispatched to the schedulers
        assert len(self.arbiter.dispatcher.schedulers) == 1
        for scheduler in self.arbiter.dispatcher.schedulers:
            assert 'alignak_name' in scheduler.conf_package
            assert scheduler.conf_package.get('alignak_name') == 'my_alignak'

        # Alignak name is defined in the configuration dispatched to the satellites
        assert len(self.arbiter.dispatcher.satellites) == 4
        for satellite in self.arbiter.dispatcher.satellites:
            print(satellite.cfg)
            assert 'alignak_name' in satellite.cfg
            assert satellite.cfg.get('alignak_name') == 'my_alignak'

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
        link = self.arbiter.conf.reactionners.find_by_name('Default-Reactionner')
        assert link is not None

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

    def test_plus_syntax(self):
        """ Test that plus (+) is not allowed for single value properties

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/host_bad_plus_syntax.cfg')
        self.show_logs()
        assert not self.conf_is_correct

        self.assert_any_cfg_log_match(re.escape(
            "Configuration in host::test_host_1 is incorrect"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "A + value for a single string (display_name) is not handled"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "hosts configuration is incorrect!"
        ))
        assert len(self.configuration_errors) == 3
        assert len(self.configuration_warnings) == 2

    def test_underscore_syntax(self):
        """ Test that underscore (_) is not allowed for list value properties

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/host_macro_is_a_list.cfg')
        self.show_logs()
        assert not self.conf_is_correct

        self.assert_any_cfg_log_match(re.escape(
            "Configuration in host::test_host_1 is incorrect"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "A + value for a single string (_macro_list_plus) is not handled"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "hosts configuration is incorrect!"
        ))
        assert len(self.configuration_errors) == 3
        assert len(self.configuration_warnings) == 2

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
        assert 'general1' == svc.check_command.command.command_name
        assert 1 == svc.definition_order

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
        self._sched = self.schedulers['scheduler-master'].sched

        # Service linked to an host
        svc = self._sched.services.find_srv_by_name_and_hostname("MYHOST", "SSH")
        assert svc is not None

        # Service linked to several hosts
        for hname in ["MYHOST2", "MYHOST3"]:
            svc = self._sched.services.find_srv_by_name_and_hostname(hname, "SSH")
            assert svc is not None

        # ---
        # Test services created because service template linked to host template
        # An host
        host = self._sched.hosts.find_by_name("test_host")
        assert host is not None
        for service in host.services:
            if service in self._sched.services:
                print("Host service: %s" % (self._sched.services[service]))
        assert len(host.services) == 3

        # Service template linked to an host template
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host", "svc_inherited")
        assert svc is not None
        assert svc.uuid in host.services
        assert 'check_ssh' == svc.check_command.command.command_name
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host", "svc_inherited2")
        assert svc is not None
        assert svc.uuid in host.services
        assert 'check_ssh' == svc.check_command.command.command_name

        # Another host
        host = self._sched.hosts.find_by_name("test_host2")
        assert host is not None
        for service in host.services:
            if service in self._sched.services:
                print("Host service: %s" % (self._sched.services[service]))
        assert len(host.services) == 3

        # Service template linked to an host template
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host2", "svc_inherited")
        assert svc is not None
        assert svc.uuid in host.services
        assert 'check_ssh' == svc.check_command.command.command_name
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host2", "svc_inherited2")
        assert svc is not None
        assert svc.uuid in host.services
        assert 'check_ssh' == svc.check_command.command.command_name

    def test_service_templating_inheritance(self):
        """ Test services inheritance
        Services are attached to hosts thanks to host/service template relation

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/alignak_service_description_inheritance.cfg')
        assert self.conf_is_correct
        self._sched = self.schedulers['scheduler-master'].sched

        # An host
        host = self._sched.hosts.find_by_name("test.host.A")
        assert host is not None

        # Service linked to hist host
        svc = self._sched.services.find_srv_by_name_and_hostname("test.host.A", "nsca_uptime")
        assert svc is not None
        svc = self._sched.services.find_srv_by_name_and_hostname("test.host.A", "nsca_cpu")
        assert svc is not None

    def test_service_with_no_host(self):
        """ A service not linked to any host raises an error

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/alignak_service_nohost.cfg')
        assert not self.conf_is_correct
        # assert "Configuration in service::will_not_exist is incorrect; " \
        #               "from: cfg/config/alignak_service_nohost.cfg:1" in \
        #               self.configuration_errors
        # assert "a service has been defined without host_name nor " \
        #               "hostgroup_name, from: cfg/config/alignak_service_nohost.cfg:1" in \
        #               self.configuration_errors
        # assert "[service::will_not_exist] not bound to any host." in \
        #               self.configuration_errors
        # assert "[service::will_not_exist] no check_command" in \
        #               self.configuration_errors

        assert "Configuration in service::will_error is incorrect; " \
                      "from: cfg/config/alignak_service_nohost.cfg:6" in \
                      self.configuration_errors
        assert "[service::will_error] unknown host_name 'NOEXIST'" in \
                      self.configuration_errors
        assert "[service::will_error] check_command 'None' invalid" in \
                      self.configuration_errors

        assert "services configuration is incorrect!" in \
                      self.configuration_errors

        # No existing services in the loaded configuration
        assert 0 == len(self.arbiter.conf.services.items)

    def test_bad_template_use_itself(self):
        """ Detect a template that uses itself as a template

        This test host use template but template is itself

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_host_template_itself.cfg')
        assert not self.conf_is_correct
        # TODO, issue #344
        assert "Host bla use/inherits from itself ! " \
                      "from: cfg/config/host_bad_template_itself.cfg:1" in \
                      self.configuration_errors

    def test_use_undefined_template(self):
        """ Test unknown template detection for host and service

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_bad_undefined_template.cfg')
        assert self.conf_is_correct

        # TODO, issue #344
        assert "Host test_host use/inherit from an unknown template: undefined_host ! " \
                      "from: cfg/config/use_undefined_template.cfg:1" in \
                      self.configuration_warnings
        assert "Service test_service use/inherit from an unknown template: " \
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

    def test_malformed_parameters(self):
        """ Configuration is not correct because of malformed parameters

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/bad_parameters_syntax.cfg')
        assert not self.conf_is_correct
        self.show_logs()

        # Error messages
        assert len(self.configuration_errors) == 2
        self.assert_any_cfg_log_match(re.escape(
            "the parameter parameter2 is malformed! (no = sign)"
        ))

    def test_nagios_parameters(self):
        """Configuration has some old nagios parameters

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/deprecated_configuration.cfg')
        assert not self.conf_is_correct
        self.show_logs()

        # Error messages
        assert len(self.configuration_errors) == 6
        self.assert_any_cfg_log_match(re.escape(
            "Your configuration parameters 'status_file = /tmp/status' and "
            "'object_cache_file = /tmp/cache' need to use an external module such "
            "as 'retention' but I did not found one!"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Your configuration parameter 'log_file = /tmp/log' needs to use an "
            "external module such as 'logs' but I did not found one!"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Your configuration parameter 'use_syslog = True' needs to use an "
            "external module such as 'logs' but I did not found one!"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Your configuration parameters 'host_perfdata_file = /tmp/host_perf' "
            "and 'service_perfdata_file = /tmp/srv_perf' need to use an "
            "external module such as 'retention' but I did not found one!"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Your configuration parameters 'state_retention_file = /tmp/retention' "
            "and 'retention_update_interval = 10' need to use an "
            "external module such as 'retention' but I did not found one!"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Your configuration parameter 'command_file = /tmp/command' needs to use an "
            "external module such as 'logs' but I did not found one!"
        ))

        # Warning messages
        assert len(self.configuration_warnings) == 11
        self.assert_any_cfg_log_match(re.escape(
            "Guessing the property failure_prediction_enabled type because "
            "it is not in Config object properties"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Guessing the property obsess_over_hosts type because "
            "it is not in Config object properties"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Guessing the property ochp_command type because "
            "it is not in Config object properties"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Guessing the property obsess_over_services type because "
            "it is not in Config object properties"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Guessing the property ocsp_command type because "
            "it is not in Config object properties"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "use_regexp_matching parameter is not managed."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "ochp_command parameter is not managed."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "obsess_over_hosts parameter is not managed."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "ocsp_command parameter is not managed."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "obsess_over_services parameter is not managed."
        ))

    def test_nagios_parameters_2(self):
        """Configuration has some old nagios parameters - some are not raising a configuration error

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/deprecated_configuration_warning.cfg')
        assert self.conf_is_correct
        self.show_logs()

        # Error messages
        assert len(self.configuration_errors) == 0

        # Warning messages
        assert len(self.configuration_warnings) == 11
        self.assert_any_cfg_log_match(re.escape(
            "Guessing the property failure_prediction_enabled type because "
            "it is not in Config object properties"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Guessing the property obsess_over_hosts type because "
            "it is not in Config object properties"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Guessing the property ochp_command type because "
            "it is not in Config object properties"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Guessing the property obsess_over_services type because "
            "it is not in Config object properties"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Guessing the property ocsp_command type because "
            "it is not in Config object properties"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "failure_prediction_enabled parameter is not managed."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "use_regexp_matching parameter is not managed."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "ochp_command parameter is not managed."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "obsess_over_hosts parameter is not managed."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "ocsp_command parameter is not managed."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "obsess_over_services parameter is not managed."
        ))

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
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_notificationperiod_in_service.cfg')
        assert not self.conf_is_correct
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

        This test do not always pass! This problem is due to the unordered configuration reading.
        Sometimes, the hosts are parsed before the realms and sometimes the realms are parsed
        before the hosts.

        According to the order in which errors are detected, the reported error messages are not
        the same!

        To avoid such a problem, the relma containing an unknown member for this test must
        not be used in an host configuration :)

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_realm_member.cfg')
        assert not self.conf_is_correct
        self.show_logs()

        # Configuration warnings
        # self.assert_any_cfg_log_match(re.escape(
        #     u"Some hosts exist in the realm 'Realm1' but no scheduler is defined for this realm"))
        # self.assert_any_cfg_log_match(re.escape(
        #     u"Added a scheduler in the realm 'Realm1'"))
        self.assert_any_cfg_log_match(re.escape(
            u"Some hosts exist in the realm 'Realm3' but no scheduler is defined for this realm"))
        self.assert_any_cfg_log_match(re.escape(
            u"Added a scheduler in the realm 'Realm3'"))
        self.assert_any_cfg_log_match(re.escape(
            u"Some hosts exist in the realm 'Realm2' but no scheduler is defined for this realm"))
        self.assert_any_cfg_log_match(re.escape(
            u"Added a scheduler in the realm 'Realm2'"))
        # self.assert_any_cfg_log_match(re.escape(
        #     u"Some hosts exist in the realm 'Realm1' but no poller is defined for this realm"))
        # self.assert_any_cfg_log_match(re.escape(
        #     u"Added a poller in the realm 'Realm1'"))
        self.assert_any_cfg_log_match(re.escape(
            u"Some hosts exist in the realm 'Realm3' but no poller is defined for this realm"))
        self.assert_any_cfg_log_match(re.escape(
            u"Added a poller in the realm 'Realm3'"))
        self.assert_any_cfg_log_match(re.escape(
            u"Some hosts exist in the realm 'Realm2' but no poller is defined for this realm"))
        self.assert_any_cfg_log_match(re.escape(
            u"Added a poller in the realm 'Realm2'"))
        # self.assert_any_cfg_log_match(re.escape(
        #     u"Some hosts exist in the realm 'Realm1' but no broker is defined for this realm"))
        # self.assert_any_cfg_log_match(re.escape(
        #     u"Added a broker in the realm 'Realm1'"))
        self.assert_any_cfg_log_match(re.escape(
            u"Some hosts exist in the realm 'Realm3' but no broker is defined for this realm"))
        self.assert_any_cfg_log_match(re.escape(
            u"Added a broker in the realm 'Realm3'"))
        self.assert_any_cfg_log_match(re.escape(
            u"Some hosts exist in the realm 'Realm2' but no broker is defined for this realm"))
        self.assert_any_cfg_log_match(re.escape(
            u"Added a broker in the realm 'Realm2'"))

        # Configuration errors
        self.assert_any_cfg_log_match(re.escape(
            'More than one realm is defined as the default one: All,Realm1,Realm2,Realm4. '
            'I set All as the temporary default realm.'))
        self.assert_any_cfg_log_match(re.escape(
            u'Configuration in host::test_host_realm3 is incorrect; '
            u'from: cfg/config/host_bad_realm.cfg:31'))
        self.assert_any_cfg_log_match(re.escape(
            u'the host test_host_realm3 got an invalid realm (Realm3)!'))
        self.assert_any_cfg_log_match(re.escape(
            'hosts configuration is incorrect!'))
        self.assert_any_cfg_log_match(re.escape(
            u'Configuration in realm::Realm4 is incorrect; '
            u'from: cfg/config/realm_bad_member.cfg:19'))
        self.assert_any_cfg_log_match(re.escape(
            u"[realm::Realm4] as realm, got unknown member 'UNKNOWN_HOST'"))
        self.assert_any_cfg_log_match(re.escape(
            'realms configuration is incorrect!'))
        self.assert_any_cfg_log_match(re.escape(
            u'Configuration in scheduler::Scheduler-Realm3 is incorrect; from: unknown'))
        self.assert_any_cfg_log_match(re.escape(
            u"The scheduler Scheduler-Realm3 got a unknown realm 'Realm3'"))
        self.assert_any_cfg_log_match(re.escape(
            'schedulers configuration is incorrect!'))
        self.assert_any_cfg_log_match(re.escape(
            u'Configuration in poller::Poller-Realm3 is incorrect; from: unknown'))
        self.assert_any_cfg_log_match(re.escape(
            u"The poller Poller-Realm3 got a unknown realm 'Realm3'"))
        self.assert_any_cfg_log_match(re.escape(
            'pollers configuration is incorrect!'))
        self.assert_any_cfg_log_match(re.escape(
            u'Configuration in broker::Broker-Realm3 is incorrect; from: unknown'))
        self.assert_any_cfg_log_match(re.escape(
            u"The broker Broker-Realm3 got a unknown realm 'Realm3'"))
        self.assert_any_cfg_log_match(re.escape(
            'brokers configuration is incorrect!'))

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
            "Configuration in service::Simple_1Of_1unk_host is incorrect; "
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::Simple_1Of_1unk_host] business_rule invalid"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::Simple_1Of_1unk_host]: Business rule uses unknown host test_host_9"
        ))

        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::Simple_1Of_1unk_svc is incorrect; "
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::Simple_1Of_1unk_svc] business_rule invalid"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::Simple_1Of_1unk_svc]: Business rule uses unknown service test_host_0/db3"
        ))

        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::ERP_unk_svc is incorrect; "
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::ERP_unk_svc] business_rule invalid"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::ERP_unk_svc]: Business rule uses unknown service test_host_0/web100"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::ERP_unk_svc]: Business rule uses unknown service test_host_0/lvs100"
        ))

        self.assert_any_cfg_log_match(re.escape(
            "services configuration is incorrect!"
        ))

    def test_business_rules_hostgroup_expansion_errors(self):
        """ Configuration is not correct  because of a bad syntax in BR hostgroup expansion """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/business_correlator_expand_expression_broken.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::bprule_invalid_regex is incorrect; "
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::bprule_invalid_regex] business_rule invalid"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::bprule_invalid_regex]: Business rule uses invalid regex "
            "r:test_host_0[,srv1: unexpected end of regular expression"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::bprule_empty_regex is incorrect; "
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::bprule_empty_regex] business_rule invalid"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::bprule_empty_regex]: Business rule got an empty result "
            "for pattern r:fake,srv1"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::bprule_unkonwn_service is incorrect; "
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::bprule_unkonwn_service] business_rule invalid"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::bprule_unkonwn_service]: Business rule got an empty result "
            "for pattern g:hostgroup_01,srv3"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::bprule_unkonwn_hostgroup is incorrect; "
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::bprule_unkonwn_hostgroup] business_rule invalid"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::bprule_unkonwn_hostgroup]: Business rule got an empty result "
            "for pattern g:hostgroup_03,srv1"
        ))

        self.assert_any_cfg_log_match(re.escape(
            "services configuration is incorrect!"
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

    def test_bad_satellite_broker_realm_conf(self):
        """ Configuration is not correct because a broker conf has an unknown realm

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_realm_in_broker.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in broker::Broker-test is incorrect; "
            "from: cfg/config/bad_realm_broker.cfg:1"
        )
        self.assert_any_cfg_log_match(
            "The broker Broker-test got a unknown realm 'NoGood'"
        )
        self.assert_any_cfg_log_match(
            "brokers configuration is incorrect!"
        )

    def test_bad_satellite_poller_realm_conf(self):
        """ Configuration is not correct because a broker conf has an unknown realm

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_realm_in_poller.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in poller::Poller-test is incorrect; "
            "from: cfg/config/bad_realm_poller.cfg:1"
        )
        self.assert_any_cfg_log_match(
            "The poller Poller-test got a unknown realm 'NoGood'"
        )
        self.assert_any_cfg_log_match(
            "pollers configuration is incorrect!"
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

    def test_config_hosts_default_check_command(self):
        """ Test hosts default check command
            - Check that an host without declared command uses the default _internal_host_up

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/config/hosts_commands.cfg')
        self.show_logs()
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        command = self.arbiter.conf.commands.find_by_name('_internal_host_up')
        print("Command: %s" % command)
        assert command

        host = self.arbiter.conf.hosts.find_by_name('test_host')
        assert '_internal_host_up' == host.check_command.get_name()

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
        # No warning messages
        assert len(self.configuration_warnings) == 0

        host0 = self.arbiter.conf.hosts.find_by_name('host_A')
        host1 = self.arbiter.conf.hosts.find_by_name('host_B')
        assert ['d', 'x', 'r', 'f', 's'] == host0.notification_options
        assert ['o', 'd', 'x'] == host0.flap_detection_options
        assert ['d', 'x'] == host0.snapshot_criteria
        # self.assertEqual('x', host0.initial_state)
        # self.assertEqual('x', host0.freshness_state)

        assert 1 == len(host0.act_depend_of_me)
        assert ['d', 'x'] == host0.act_depend_of_me[0][1]

        assert 1 == len(host0.chk_depend_of_me)
        assert ['x'] == host0.chk_depend_of_me[0][1]

        assert 1 == len(host1.act_depend_of)
        assert ['d', 'x'] == host1.act_depend_of[0][1]

        assert 1 == len(host1.chk_depend_of)
        assert ['x'] == host1.chk_depend_of[0][1]

    def test_macro_modulation(self):
        """ Detect macro modulation configuration errors

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/macros_modulation_broken.cfg')
        assert not self.conf_is_correct

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
        assert "Configuration in macromodulation::Unnamed is incorrect; " \
                      "from: cfg/config/macros_modulation_broken.cfg:3" in \
                      self.configuration_errors
        assert "a macromodulation item has been defined without macromodulation_name, " \
                      "from: cfg/config/macros_modulation_broken.cfg:3" in \
                      self.configuration_errors
        assert "The modulation_period of the macromodulation 'Unnamed' " \
                      "named '24x7' is unknown!" in \
                      self.configuration_errors
        assert "[macromodulation::Unnamed] macromodulation_name property is missing" in \
                  self.configuration_errors
        assert "macromodulations configuration is incorrect!" in \
                  self.configuration_errors

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
        assert "checkmodulations configuration is incorrect!" in \
                      self.configuration_errors

    def test_business_impact__modulation(self):
        """ Detect business impact modulation configuration errors

        :return: None
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/businesssimpact_modulation_broken.cfg')
        assert not self.conf_is_correct

        # MM without macro definition
        assert "Configuration in businessimpactmodulation::CritMod is incorrect; " \
                      "from: cfg/config/businesssimpact_modulation_broken.cfg:10" in \
                      self.configuration_errors
        assert "[businessimpactmodulation::CritMod] business_impact property is missing" in \
                      self.configuration_errors

        # MM without name
        assert "Configuration in businessimpactmodulation::Unnamed is incorrect; " \
                      "from: cfg/config/businesssimpact_modulation_broken.cfg:2" in \
                      self.configuration_errors
        assert "a businessimpactmodulation item has been defined without " \
                      "business_impact_modulation_name, from: " \
                      "cfg/config/businesssimpact_modulation_broken.cfg:2" in \
                      self.configuration_errors
        assert "The modulation_period of the businessimpactmodulation 'Unnamed' " \
                      "named '24x7' is unknown!" in \
                      self.configuration_errors
        assert "[businessimpactmodulation::Unnamed] business_impact_modulation_name " \
                      "property is missing" in \
                      self.configuration_errors
        assert "businessimpactmodulations configuration is incorrect!" in \
                      self.configuration_errors
