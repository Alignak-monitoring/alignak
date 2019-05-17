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
"""
This file contains the test for the Alignak configuration checks. Indeed, it checks the
correctness of the monitored system configuration contained in the Nagios flat-files...
not the Alignak overall configuration defined in the alignak.ini!

 Almost all of these tests are using the self.setup_with_file function that is declared in
the AlignakTest class. This function will get the *cfg/alignak.ini* configuration file.

 This is because all the tests were written before the configuration refactoring and it makes
 it easier to use always the same alignak.ini file whereas only the objects configuration is
changing:)

"""
import os
import re
import time
import unittest2
from .alignak_test import AlignakTest
import pytest


class TestConfig(AlignakTest):
    """
    This class tests the configuration
    """
    def setUp(self):
        super(TestConfig, self).setUp()

    def test_config_ok(self):
        """ Default shipped configuration has no loading problems ...

        :return: None
        """
        self.setup_with_file(configuration_file='../etc/alignak.cfg',
                             env_file='./etc/alignak.ini',
                             dispatching=False)
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        # Arbiter named as in the configuration
        assert self._arbiter.conf.conf_is_correct
        arbiter_link = self._arbiter.conf.arbiters.find_by_name('arbiter-master')
        assert arbiter_link is not None
        assert not hasattr(arbiter_link, 'configuration_errors')
        assert not hasattr(arbiter_link, 'configuration_warnings')

        # Scheduler named as in the configuration
        assert self._arbiter.conf.conf_is_correct
        scheduler_link = self._arbiter.conf.schedulers.find_by_name('scheduler-master')
        assert scheduler_link is not None
        # # Scheduler configuration is ok
        # assert self._scheduler.pushed_conf.conf_is_correct

        # Broker, Poller, Reactionner named as in the configuration
        link = self._arbiter.conf.brokers.find_by_name('broker-master')
        assert link is not None
        link = self._arbiter.conf.pollers.find_by_name('poller-master')
        assert link is not None
        link = self._arbiter.conf.reactionners.find_by_name('reactionner-master')
        assert link is not None

        # Receiver - no default receiver created
        link = self._arbiter.conf.receivers.find_by_name('receiver-master')
        assert link is not None

    def test_config_ok_2(self):
        """ Default shipped configuration has no loading problems ... even when using the
        default shipped ini file

        :return: None
        """
        self.setup_with_file(configuration_file='../etc/alignak.cfg',
                             env_file='./etc/alignak.ini',
                             dispatching=False)
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        # Arbiter named as in the configuration
        assert self._arbiter.conf.conf_is_correct
        arbiter_link = self._arbiter.conf.arbiters.find_by_name('arbiter-master')
        assert arbiter_link is not None
        assert not hasattr(arbiter_link, 'configuration_errors')
        assert not hasattr(arbiter_link, 'configuration_warnings')

        # Scheduler named as in the configuration
        assert self._arbiter.conf.conf_is_correct
        scheduler_link = self._arbiter.conf.schedulers.find_by_name('scheduler-master')
        assert scheduler_link is not None
        # # Scheduler configuration is ok
        # assert self._scheduler.pushed_conf.conf_is_correct

        # Broker, Poller, Reactionner named as in the configuration
        link = self._arbiter.conf.brokers.find_by_name('broker-master')
        assert link is not None
        link = self._arbiter.conf.pollers.find_by_name('poller-master')
        assert link is not None
        link = self._arbiter.conf.reactionners.find_by_name('reactionner-master')
        assert link is not None

        # Receiver - no default receiver created
        link = self._arbiter.conf.receivers.find_by_name('receiver-master')
        assert link is not None

    def test_config_test_ok(self):
        """ Default test configuration has no loading problems ...

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        # Arbiter named as in the configuration
        assert self._arbiter.conf.conf_is_correct
        arbiter_link = self._arbiter.conf.arbiters.find_by_name('arbiter-master')
        assert arbiter_link is not None
        assert not hasattr(arbiter_link, 'configuration_errors')
        assert not hasattr(arbiter_link, 'configuration_warnings')

        # Scheduler named as in the configuration
        assert self._arbiter.conf.conf_is_correct
        scheduler_link = self._arbiter.conf.schedulers.find_by_name('scheduler-master')
        assert scheduler_link is not None
        # # Scheduler configuration is ok
        # assert self._scheduler.pushed_conf.conf_is_correct

        # Broker, Poller, Reactionner and Receiver named as in the configuration
        link = self._arbiter.conf.brokers.find_by_name('broker-master')
        assert link is not None
        link = self._arbiter.conf.pollers.find_by_name('poller-master')
        assert link is not None
        link = self._arbiter.conf.reactionners.find_by_name('reactionner-master')
        assert link is not None
        link = self._arbiter.conf.receivers.find_by_name('receiver-master')
        assert link is not None

    def test_host_name_pattern(self):
        """ Default test configuration has no loading problems ...

        :return: None
        """
        self.setup_with_file('cfg/config/host_name_pattern.cfg')
        assert self.conf_is_correct
        self.show_logs()

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        # Search hosts by name
        # From a patterned host:  test_[0-2], we have test_0, test_1 and test_2
        host = self._arbiter.conf.hosts.find_by_name('test_0')
        assert host is not None
        host = self._arbiter.conf.hosts.find_by_name('test_1')
        assert host is not None
        host = self._arbiter.conf.hosts.find_by_name('test_2')
        assert host is not None

        # From a patterned host:  test_[0-2-%02d], we have test_00, test_01 and test_02
        host = self._arbiter.conf.hosts.find_by_name('test_00')
        assert host is not None
        host = self._arbiter.conf.hosts.find_by_name('test_01')
        assert host is not None
        host = self._arbiter.conf.hosts.find_by_name('test_02')
        assert host is not None
        host = self._arbiter.conf.hosts.find_by_name('test_03')
        assert host is None

    def test_config_conf_inner_properties(self):
        """ Default configuration has no loading problems ...
        and inner default properties are correctly valued

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        # Arbiter configuration is correct
        assert self._arbiter.conf.conf_is_correct

        # Configuration inner properties are valued
        assert self._arbiter.conf.main_config_file == os.path.abspath('cfg/cfg_default.cfg')

        # Default Alignak name is the arbiter name but it may be set from the configuration
        assert self._arbiter.conf.alignak_name == 'My Alignak'
        assert self._arbiter.alignak_name == 'My Alignak'

        # Default Alignak daemons start/stop configuration
        # assert self._arbiter.conf.daemons_start_timeout == 1
        # Changed to 5 seconds for tests purpose
        assert self._arbiter.conf.daemons_start_timeout == 1
        assert self._arbiter.conf.daemons_stop_timeout == 10

    def test_config_conf_inner_properties_named_alignak(self):
        """ Default configuration with an alignak_name property

        :return: None
        """
        self.setup_with_file('cfg/cfg_default_alignak_name.cfg',
                             dispatching=True)
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        # Arbiter configuration is correct
        assert self._arbiter.conf.conf_is_correct

        # Alignak name is defined in the configuration (from the Nagios legacy)
        assert self._arbiter.conf.alignak_name == 'my_alignak'
        # Alignak name is defined in the arbiter (from the ini configuration file or
        # from the command line)
        # The value defined in the Cfg files takes precedence over the one in alignak.ini!
        # assert self._arbiter.alignak_name == 'My Alignak'
        assert self._arbiter.alignak_name == 'my_alignak'

        # Alignak name is defined in the configuration dispatched to the schedulers
        assert len(self._arbiter.dispatcher.schedulers) == 1
        for scheduler in self._arbiter.dispatcher.schedulers:
            assert 'alignak_name' in scheduler.cfg
            assert scheduler.cfg.get('alignak_name') == 'my_alignak'

        # Alignak name is defined in the configuration dispatched to the satellites
        assert len(self._arbiter.dispatcher.satellites) == 4
        for satellite in self._arbiter.dispatcher.satellites:
            assert 'alignak_name' in satellite.cfg
            assert satellite.cfg.get('alignak_name') == 'my_alignak'

    def test_config_ok_no_declared_daemons(self):
        """ Default configuration has no loading problems ... but no daemons are defined
        The arbiter will create default daemons except for the receiver.

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg', 'cfg/config/alignak-no-daemons.ini')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        # Arbiter named as Default
        assert self._arbiter.conf.conf_is_correct
        # Use the generic daemon name in the alignak.ini file!
        arbiter_link = self._arbiter.conf.arbiters.find_by_name('daemon')
        for arb in self._arbiter.conf.arbiters:
            print("Arbiters: %s" % arb.name)
        assert arbiter_link is not None
        assert not hasattr(arbiter_link, 'configuration_errors')
        assert not hasattr(arbiter_link, 'configuration_warnings')

        # Scheduler named as Default
        link = self._arbiter.conf.schedulers.find_by_name('Default-Scheduler')
        assert link is not None
        # # Scheduler configuration is ok
        # assert self._schedulers['Default-Scheduler'].pushed_conf.conf_is_correct

        # Broker, Poller, Reactionner and Receiver named as Default
        link = self._arbiter.conf.brokers.find_by_name('Default-Broker')
        assert link is not None
        link = self._arbiter.conf.pollers.find_by_name('Default-Poller')
        assert link is not None
        link = self._arbiter.conf.reactionners.find_by_name('Default-Reactionner')
        assert link is not None
        link = self._arbiter.conf.receivers.find_by_name('Default-Receiver')
        assert link is not None

    def test_symlinks(self):
        """ Test a configuration with symlinks to files

        :return: None
        """
        if os.name == 'nt':
            return

        self.setup_with_file('cfg/conf_in_symlinks/alignak_conf_in_symlinks.cfg')

        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname("test_host_0",
                                                                       "test_HIDDEN")
        assert svc is not None

    def test_define_syntax(self):
        """ Test that define{} syntax is correctly checked: spaces, multi-lines, white-spaces
        do not raise any error ...

        :return: None
        """
        self.setup_with_file('cfg/config/alignak_define_with_space.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        host = self._arbiter.conf.hosts.find_by_name('spaced-host')
        assert host is not None

    def test_plus_syntax(self):
        """ Test that plus (+) is not allowed for single value properties

        :return: None
        """
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
        assert len(self.configuration_warnings) == 1

    def test_underscore_syntax(self):
        """ Test that underscore (_) is not allowed for list value properties

        :return: None
        """
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
        assert len(self.configuration_warnings) == 1

    def test_definition_order(self):
        """ Test element definition order
        An element (host, service, ...) can be defined several times then the definition_order
        will be used to choose which definition is the to be used one...

        Here, the 'same_service' is defined 3 times but the 'general1' command one will be
        retained rather than other because have the lower definition_order ...

        :return: None
        """
        self.setup_with_file('cfg/config/alignak_definition_order.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname(
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
        self.setup_with_file('cfg/config/alignak_service_not_hostname.cfg')
        assert self.conf_is_correct

        host = self._arbiter.conf.hosts.find_by_name("test_host_0")
        assert host is not None
        assert host.is_correct()

        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # Check that the service is attached to test_host_0
        assert svc is not None
        assert svc.is_correct()

        # Check that the service is NOT attached to test_host_1
        svc_not = self._arbiter.conf.services.find_srv_by_name_and_hostname(
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
        self.setup_with_file('cfg/config/alignak_service_description_inheritance.cfg')
        assert self.conf_is_correct
        # self._sched = self._scheduler

        # Service linked to an host
        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname("MYHOST", "SSH")
        assert svc is not None

        # Service linked to several hosts
        for hname in ["MYHOST2", "MYHOST3"]:
            svc = self._arbiter.conf.services.find_srv_by_name_and_hostname(hname, "SSH")
            assert svc is not None

        # ---
        # Test services created because service template linked to host template
        # An host
        host = self._arbiter.conf.hosts.find_by_name("test_host")
        assert host is not None
        for service in host.services:
            if service in self._arbiter.conf.services:
                print(("Host service: %s" % (self._arbiter.conf.services[service])))
        assert len(host.services) == 3

        # Service template linked to an host template
        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname("test_host", "svc_inherited")
        assert svc is not None
        assert svc.uuid in host.services
        assert 'check_ssh' == svc.check_command.command.command_name
        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname("test_host", "svc_inherited2")
        assert svc is not None
        assert svc.uuid in host.services
        assert 'check_ssh' == svc.check_command.command.command_name

        # Another host
        host = self._arbiter.conf.hosts.find_by_name("test_host2")
        assert host is not None
        for service in host.services:
            if service in self._arbiter.conf.services:
                print(("Host service: %s" % (self._arbiter.conf.services[service])))
        assert len(host.services) == 3

        # Service template linked to an host template
        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname("test_host2", "svc_inherited")
        assert svc is not None
        assert svc.uuid in host.services
        assert 'check_ssh' == svc.check_command.command.command_name
        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname("test_host2", "svc_inherited2")
        assert svc is not None
        assert svc.uuid in host.services
        assert 'check_ssh' == svc.check_command.command.command_name

    def test_service_templating_inheritance(self):
        """ Test services inheritance
        Services are attached to hosts thanks to host/service template relation

        :return: None
        """
        self.setup_with_file('cfg/config/alignak_service_description_inheritance.cfg')
        assert self.conf_is_correct

        # An host
        host = self._arbiter.conf.hosts.find_by_name("test.host.A")
        assert host is not None

        # Service linked to hist host
        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname("test.host.A", "nsca_uptime")
        assert svc is not None
        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname("test.host.A", "nsca_cpu")
        assert svc is not None

    def test_service_with_no_host(self):
        """ A service not linked to any host raises an error

        :return: None
        """
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

        self.assert_any_cfg_log_match(re.escape(
            "Configuration in service::will_error is incorrect; "
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::will_error] unknown host_name 'NOEXIST'"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "[service::will_error] check_command 'None' invalid"
        ))

        self.assert_any_cfg_log_match(re.escape(
            "services configuration is incorrect!"
        ))

        # No existing services in the loaded configuration
        assert 0 == len(self._arbiter.conf.services.items)

    def test_bad_template_use_itself(self):
        """ Detect a template that uses itself as a template

        This test host use template but template is itself

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_host_template_itself.cfg')
        assert not self.conf_is_correct
        # TODO, issue #344
        self.assert_any_cfg_log_match(
            "Host bla use/inherits from itself !"
        )

    def test_use_undefined_template(self):
        """ Test unknown template detection for host and service

        :return: None
        """
        self.setup_with_file('cfg/cfg_bad_undefined_template.cfg')
        assert self.conf_is_correct

        # TODO, issue #344
        self.assert_any_cfg_log_match(
            "Host test_host use/inherit from an unknown template: undefined_host ! "
        )
        self.assert_any_cfg_log_match(
            "Service test_service use/inherit from an unknown template: undefined_service ! "
        )

    def test_broken_configuration(self):
        """ Configuration is not correct because of a wrong relative path in the main config file

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/alignak_broken_1.cfg')
        assert not self.conf_is_correct

        # Error messages
        assert len(self.configuration_errors) == 2
        u = 'u' if os.sys.version_info[:2] < (3, 0) else ''
        cwd = os.path.abspath(os.getcwd())
        self.assert_any_cfg_log_match(
            re.escape(
                "cannot open file '%s/cfg/config/etc/broken_1/minimal.cfg' "
                "for reading: [Errno 2] No such file or directory: "
                "%s'%s/cfg/config/etc/broken_1/minimal.cfg'" % (cwd, u, cwd)
            )
        )
        self.assert_any_cfg_log_match(
            re.escape(
                "cannot open file '%s/cfg/config/resource.cfg' "
                "for reading: [Errno 2] No such file or directory: "
                "%s'%s/cfg/config/resource.cfg'" % (cwd, u, cwd)
            )
        )

    def test_malformed_parameters(self):
        """ Configuration is not correct because of malformed parameters

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/bad_parameters_syntax.cfg')
        assert not self.conf_is_correct
        self.show_logs()

        # Warning / error messages
        # assert len(self.configuration_warnings) == 1
        # self.assert_any_cfg_log_match(re.escape(
        #     "the parameter parameter is ambiguous! No value after =, assuming an empty string"
        # ))
        assert len(self.configuration_errors) == 1
        self.assert_any_cfg_log_match(re.escape(
            "the parameter parameter2 is malformed! (no = sign)"
        ))

    def test_nagios_parameters(self):
        """Configuration has some old nagios parameters

        :return: None
        """
        # with pytest.raises(SystemExit):
        self.setup_with_file('cfg/config/deprecated_configuration.cfg')
        # assert not self.conf_is_correct
        self.show_logs()

        # Error messages - none because some deprecation warnings are better!
        assert len(self.configuration_errors) == 0
        assert len(self.configuration_warnings) == 11
        self.assert_any_cfg_log_match(re.escape(
            "The configuration parameters 'status_file = /tmp/status' and "
            "'object_cache_file = /tmp/cache' are deprecated and will be ignored. "
            "Please configure your external 'retention' module as expected."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "The configuration parameter 'log_file = /tmp/log' is deprecated and will be ignored. "
            "Please configure your external 'logs' module as expected."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "The configuration parameter 'use_syslog = True' is deprecated and will be ignored. "
            "Please configure your external 'logs' module as expected."
        ))
        # self.assert_any_cfg_log_match(re.escape(
        #     "The configuration parameters 'host_perfdata_file = /tmp/host_perf' "
        #     "and 'service_perfdata_file = /tmp/srv_perf' are deprecated and will be ignored. "
        #     "Please configure your external 'retention' module as expected."
        # ))
        # Alignak inner module for retention is now implemented!
        # self.assert_any_cfg_log_match(re.escape(
        #     "Your configuration parameters 'state_retention_file = /tmp/retention' "
        #     "and 'retention_update_interval = 10' need to use an "
        #     "external module such as 'retention' but I did not found one!"
        # ))
        self.assert_any_cfg_log_match(re.escape(
            "The configuration parameter 'command_file = /tmp/command' is deprecated and will "
            "be ignored. "
            "Please configure an external commands capable module as expected "
            "(eg external-commands, NSCA, or WS module may suit."
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
        self.setup_with_file('cfg/config/deprecated_configuration_warning.cfg')
        assert self.conf_is_correct
        self.show_logs()

        # Error messages
        assert len(self.configuration_errors) == 0

        # Warning messages
        assert len(self.configuration_warnings) == 6
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
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/alignak_broken_2.cfg')
        assert not self.conf_is_correct

        # Error messages
        assert len(self.configuration_errors) == 2
        u = 'u' if os.sys.version_info[:2] < (3, 0) else ''
        cwd = os.path.abspath(os.getcwd())
        self.assert_any_cfg_log_match(re.escape(
            u"cannot open directory '%s/cfg/config/not-existing-dir' for reading"
            % (cwd)
        ))
        self.assert_any_cfg_log_match(re.escape(
            "cannot open file '%s/cfg/config/resource.cfg' for reading: "
            "[Errno 2] No such file or directory: %s'%s/cfg/config/resource.cfg'"
            % (cwd, u, cwd)
        ))

    def test_bad_timeperiod(self):
        """ Test bad timeperiod configuration

        :return: None
        """
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

        timeperiod = self._arbiter.conf.timeperiods.find_by_name("24x7")
        assert True == timeperiod.is_correct()
        timeperiod = self._arbiter.conf.timeperiods.find_by_name("24x7_bad")
        assert False == timeperiod.is_correct()
        timeperiod = self._arbiter.conf.timeperiods.find_by_name("24x7_bad2")
        assert False == timeperiod.is_correct()

    def test_bad_contact(self):
        """ Test a service with an unknown contact

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_contact_in_service.cfg')
        assert not self.conf_is_correct

        # The service got a unknown contact. It should raise an error
        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname("test_host_0",
                                                                       "test_ok_0_badcon")
        print("Svc:", svc)
        print("Contacts:", svc.contacts)
        assert not svc.is_correct()
        self.assert_any_cfg_log_match(
            "Configuration in service::test_ok_0_badcon is incorrect; from: "
        )
        self.assert_any_cfg_log_match(
            "the contact 'IDONOTEXIST' defined for 'test_ok_0_badcon' is unknown"
        )

    def test_bad_notification_period(self):
        """ Configuration is not correct because of an unknown notification_period in a service

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_notificationperiod_in_service.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in service::test_ok_0_badperiod is incorrect; from: "
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

        To avoid such a problem, the realm containing an unknown member for this test must
        not be used in an host configuration :)

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_realm_member.cfg')
        assert not self.conf_is_correct
        self.show_logs()

        # Configuration warnings
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm1' but no poller is defined for this realm."))
        self.assert_any_cfg_log_match(re.escape(
            "Added a poller (poller-Realm1, http://127.0.0.1:7771/) for the realm 'Realm1'"))
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm2' but no poller is defined for this realm."))
        self.assert_any_cfg_log_match(re.escape(
            "Added a poller (poller-Realm2, http://127.0.0.1:7771/) for the realm 'Realm2'"))
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm1' but no broker is defined for this realm."))
        self.assert_any_cfg_log_match(re.escape(
            "Added a broker (broker-Realm1, http://127.0.0.1:7772/) for the realm 'Realm1'"))
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm2' but no broker is defined for this realm."))
        self.assert_any_cfg_log_match(re.escape(
            "Added a broker (broker-Realm2, http://127.0.0.1:7772/) for the realm 'Realm2'"))
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm1' but no reactionner is defined for this realm."))
        self.assert_any_cfg_log_match(re.escape(
            "Added a reactionner (reactionner-Realm1, http://127.0.0.1:7769/) for the realm 'Realm1'"))
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm2' but no reactionner is defined for this realm."))
        self.assert_any_cfg_log_match(re.escape(
            "Added a reactionner (reactionner-Realm2, http://127.0.0.1:7769/) for the realm 'Realm2'"))
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm1' but no receiver is defined for this realm."))
        self.assert_any_cfg_log_match(re.escape(
            "Added a receiver (receiver-Realm1, http://127.0.0.1:7773/) for the realm 'Realm1'"))
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm2' but no receiver is defined for this realm."))
        self.assert_any_cfg_log_match(re.escape(
            "Added a receiver (receiver-Realm2, http://127.0.0.1:7773/) for the realm 'Realm2'"))
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm1' but no scheduler is defined for this realm."))
        self.assert_any_cfg_log_match(re.escape(
            "Added a scheduler (scheduler-Realm1, http://127.0.0.1:7768/) for the realm 'Realm1'"))
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm2' but no scheduler is defined for this realm."))
        self.assert_any_cfg_log_match(re.escape(
            "Added a scheduler (scheduler-Realm2, http://127.0.0.1:7768/) for the realm 'Realm2'"))
        self.assert_any_cfg_log_match(re.escape(
            "More than one realm is defined as the default one: All,Realm1,Realm2,Realm4. I set All as the default realm."))

        # Configuration errors
        self.assert_any_cfg_log_match(re.escape(
            "The host 'test_host_realm3' is affected to an unknown realm: 'Realm3'"))
        # self.assert_any_cfg_log_match(re.escape(
        #     "the host test_host_realm3 got an invalid realm (Realm3)!"))
        # self.assert_any_cfg_log_match(re.escape(
        #     "in host::test_host_realm3 is incorrect; from: "))
        # self.assert_any_cfg_log_match(re.escape(
        #     "hosts configuration is incorrect!"))
        self.assert_any_cfg_log_match(re.escape(
            "[realm::Realm4] as realm, got unknown member 'UNKNOWN_REALM'"))
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in realm::Realm4 is incorrect; from: "))
        self.assert_any_cfg_log_match(re.escape(
            "realms configuration is incorrect!"))
        self.assert_any_cfg_log_match(re.escape(
            "Error: the realm configuration of your hosts is not correct because "
            "there is more than one realm in one pack (host relations):"))
        self.assert_any_cfg_log_match(re.escape(
            " -> the host test_host_realm1 is in the realm Realm1"))
        self.assert_any_cfg_log_match(re.escape(
            " -> the host test_host_realm3 is in the realm Realm3"))
        self.assert_any_cfg_log_match(re.escape(
            " -> the host test_host_realm2 is in the realm Realm2"))
        self.assert_any_cfg_log_match(re.escape(
            "There are 6 hosts defined, and 3 hosts dispatched in the realms. "
            "Some hosts have been ignored"))

    def test_business_rules_incorrect(self):
        """ Business rules use services which don't exist.
        We want the arbiter to output an error message and exit
        in a controlled manner.
        """
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
            "[service::bprule_invalid_regex]: Business rule uses invalid regex"
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
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/business_rules_bad_realm_conf.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

        assert len(self.configuration_warnings) == 6
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm2' but no poller is defined for this realm."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm2' but no broker is defined for this realm."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm2' but no reactionner is defined for this realm."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm2' but no receiver is defined for this realm."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm2' but no scheduler is defined for this realm."
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Some hosts exist in the realm 'Realm1' but no receiver is defined for this realm."
        ))

        assert len(self.configuration_errors) == 9
        self.assert_any_cfg_log_match(re.escape(
            "hostgroup up got the default realm but it has some hosts that are from different "
            "realms: "
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in hostgroup::up is incorrect; from:"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "hostgroup hostgroup_01 got the default realm but it has some hosts that are from "
            "different realms: "
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Configuration in hostgroup::hostgroup_01 is incorrect; from:"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "hostgroups configuration is incorrect!"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "Error: the realm configuration of your hosts is not correct because "
            "there is more than one realm in one pack (host relations):"
        ))
        self.assert_any_cfg_log_match(re.escape(
            " -> the host test_host_realm1 is in the realm Realm1"
        ))
        self.assert_any_cfg_log_match(re.escape(
            " -> the host test_host_realm2 is in the realm Realm2"
        ))
        self.assert_any_cfg_log_match(re.escape(
            "There are 4 hosts defined, and 2 hosts dispatched in the realms. "
            "Some hosts have been ignored"
        ))

    def test_bad_satellite_realm_conf(self):
        """ Configuration is not correct because a daemon configuration has an unknown realm

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_default.cfg', 'cfg/config/alignak-bad-realms.ini')
            self.show_logs()
        assert not self.conf_is_correct
        self.show_configuration_logs()

        self.assert_any_cfg_log_match("The poller 'poller-master' is affected to an unknown realm: '")
        self.assert_any_cfg_log_match("The broker 'broker-master' is affected to an unknown realm: '")
        self.assert_any_cfg_log_match("The reactionner 'reactionner-master' is affected to an unknown realm: '")
        self.assert_any_cfg_log_match("The receiver 'receiver-master' is affected to an unknown realm: '")
        self.assert_any_cfg_log_match("The scheduler 'scheduler-master' is affected to an unknown realm: '")
        self.assert_any_cfg_log_match("The realm All has 2 hosts but no scheduler!")

        self.assert_any_cfg_log_match("Some hosts exist in the realm 'All' but no poller is defined for this realm.")
        self.assert_any_cfg_log_match("Some hosts exist in the realm 'All' but no broker is defined for this realm.")
        self.assert_any_cfg_log_match("Some hosts exist in the realm 'All' but no reactionner is defined for this realm.")
        self.assert_any_cfg_log_match("Some hosts exist in the realm 'All' but no receiver is defined for this realm.")
        self.assert_any_cfg_log_match("Some hosts exist in the realm 'All' but no scheduler is defined for this realm.")

    def test_bad_service_interval(self):
        """ Configuration is not correct because of a bad check_interval in service

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_check_interval_in_service.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

        self.assert_any_cfg_log_match(
            "Configuration in service::fake svc1 is incorrect; from: "
        )
        self.assert_any_cfg_log_match(
            r"Error while pythonizing parameter \'check_interval\': "
        )

    def test_config_contacts(self):
        """ Test contacts configuration

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')
        assert self.conf_is_correct

        contact = self._arbiter.conf.contacts.find_by_name('test_contact')
        assert contact.contact_name == 'test_contact'
        assert contact.email == 'nobody@localhost'
        assert contact.customs == {'_VAR2': 'text', '_VAR1': '10'}

    def test_config_hosts(self):
        """ Test hosts initial states

        :return: None
        """
        self.setup_with_file('cfg/config/host_config_all.cfg')
        assert self.conf_is_correct

        host = self._arbiter.conf.hosts.find_by_name('test_host_000')
        assert 'DOWN' == host.state

        host = self._arbiter.conf.hosts.find_by_name('test_host_001')
        assert 'UNREACHABLE' == host.state

        host = self._arbiter.conf.hosts.find_by_name('test_host_002')
        assert 'UP' == host.state

        host = self._arbiter.conf.hosts.find_by_name('test_host_003')
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
        self.setup_with_file('cfg/config/alignak_antivirg.cfg',
                             dispatching=True)
        assert self.conf_is_correct, "Configuration is not valid"

        # try to get the host
        # if it is not possible to get the host, it is probably because
        # "__ANTI-VIRG__" has been replaced by ";"
        hst = self._arbiter.conf.hosts.find_by_name('test__ANTI-VIRG___0')
        assert hst is not None, "host 'test__ANTI-VIRG___0' not found"
        assert hst.is_correct(), "config of host '%s' is not correct" % hst.get_name()

        # try to get the host
        hst = self._arbiter.conf.hosts.find_by_name('test_host_1')
        assert hst is not None, "host 'test_host_1' not found"
        assert hst.is_correct(), "config of host '%s' is not true" % (hst.get_name())

        # try to get the host
        hst = self._arbiter.conf.hosts.find_by_name('test_host_2;with_semicolon')
        assert hst is not None, "host 'test_host_2;with_semicolon' not found"
        assert hst.is_correct(), "config of host '%s' is not true" % hst.get_name()

        host = self._arbiter.conf.hosts.find_by_name("test_host_2;with_semicolon")
        assert host is not None, "host 'test_host_2;with_semicolon' not found"
        # This host has no defined check_command, then it will always keep its initial state!
        assert host.initial_state == 'd'
        assert 'DOWN' == host.state

        # We can also send a command by escaping the semicolon.
        command = r'[%lu] PROCESS_HOST_CHECK_RESULT;test_host_2\;with_semicolon;0;I should be up' \
                  % (time.time())
        self._scheduler.run_external_commands([command])
        self.external_command_loop()
        assert 'DOWN' == host.state

    def test_config_hosts_default_check_command(self):
        """ Test hosts default check command
            - Check that an host without declared command uses the default _internal_host_up

        :return: None
        """
        self.setup_with_file('cfg/config/hosts_commands.cfg')
        self.show_logs()
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        command = self._arbiter.conf.commands.find_by_name('_internal_host_up')
        print(("Command: %s" % command))
        assert command

        host = self._arbiter.conf.hosts.find_by_name('test_host')
        assert host.check_command is None

    def test_config_services(self):
        """ Test services initial states
        :return: None
        """

        self.setup_with_file('cfg/config/service_config_all.cfg')

        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_0')
        assert 'WARNING' == svc.state

        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_1')
        assert 'UNKNOWN' == svc.state

        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_2')
        assert 'CRITICAL' == svc.state

        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_3')
        assert 'OK' == svc.state

        svc = self._arbiter.conf.services.find_srv_by_name_and_hostname(
            'test_host_0', 'test_service_4')
        assert 'OK' == svc.state

    def test_host_unreachable_values(self):
        """ Test unreachable value in:
        * flap_detection_options
        * notification_options
        * snapshot_criteria

        :return: None
        """
        self.setup_with_file('cfg/config/host_unreachable.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        host0 = self._arbiter.conf.hosts.find_by_name('host_A')
        host1 = self._arbiter.conf.hosts.find_by_name('host_B')
        # assert ['d', 'x', 'r', 'f', 's'] == host0.notification_options
        assert 5 == len(host0.notification_options)
        assert 'x' in host0.notification_options
        assert 's' in host0.notification_options
        assert 'r' in host0.notification_options
        assert 'd' in host0.notification_options
        assert 'f' in host0.notification_options
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
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/macros_modulation_broken.cfg')
        assert not self.conf_is_correct

        # MM without macro definition
        self.assert_any_cfg_log_match(
            "Configuration in macromodulation::MODULATION2 is incorrect; "
        )
        self.assert_any_cfg_log_match(
            "The modulation_period of the macromodulation 'MODULATION2' named '24x7' is unknown!"
        )
        self.assert_any_cfg_log_match(re.escape(
            "[macromodulation::MODULATION2] contains no macro definition"
        ))

        # MM without name
        self.assert_any_cfg_log_match(
            "Configuration in macromodulation::Unnamed is incorrect; "
        )
        self.assert_any_cfg_log_match(
            "a macromodulation item has been defined without macromodulation_name, "
        )
        self.assert_any_cfg_log_match(
            "The modulation_period of the macromodulation 'Unnamed' named '24x7' is unknown!"
        )
        self.assert_any_cfg_log_match(re.escape(
            "[macromodulation::Unnamed] macromodulation_name property is missing"
        ))
        self.assert_any_cfg_log_match(
            "macromodulations configuration is incorrect!"
        )

    def test_checks_modulation(self):
        """ Detect checks modulation configuration errors

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/checks_modulation_broken.cfg')
        assert not self.conf_is_correct

        # CM without check_command definition
        self.assert_any_cfg_log_match(
            "Configuration in checkmodulation::MODULATION is incorrect; "
        )
        self.assert_any_cfg_log_match(re.escape(
            "[checkmodulation::MODULATION] a check_command is missing"
        ))

        # MM without name
        self.assert_any_cfg_log_match(
             "Configuration in checkmodulation::Unnamed is incorrect; "
        )
        self.assert_any_cfg_log_match(
            "a checkmodulation item has been defined without checkmodulation_name, "
        )
        self.assert_any_cfg_log_match(
            "The check_period of the checkmodulation 'Unnamed' named '24x7' is unknown!"
        )
        self.assert_any_cfg_log_match(re.escape(
            "[checkmodulation::Unnamed] checkmodulation_name property is missing"
        ))
        self.assert_any_cfg_log_match(
             "checkmodulations configuration is incorrect!"
        )

    def test_business_impact__modulation(self):
        """ Detect business impact modulation configuration errors

        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/config/businesssimpact_modulation_broken.cfg')
        assert not self.conf_is_correct

        # MM without macro definition
        self.assert_any_cfg_log_match(
            "Configuration in businessimpactmodulation::CritMod is incorrect; "
        )
        self.assert_any_cfg_log_match(re.escape(
            "[businessimpactmodulation::CritMod] business_impact property is missing"
        ))

        # MM without name
        self.assert_any_cfg_log_match(
            "Configuration in businessimpactmodulation::Unnamed is incorrect; "
        )
        self.assert_any_cfg_log_match(
            "a businessimpactmodulation item has been defined without "
            "business_impact_modulation_name, from: "
        )
        self.assert_any_cfg_log_match(
            "The modulation_period of the businessimpactmodulation 'Unnamed' "
            "named '24x7' is unknown!"
        )
        self.assert_any_cfg_log_match(re.escape(
            "[businessimpactmodulation::Unnamed] business_impact_modulation_name "
        ))
        self.assert_any_cfg_log_match(re.escape(
            "businessimpactmodulations configuration is incorrect!"
        ))
