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
#  Copyright (C) 2012:
#     Hartmut Goebel <h.goebel@crazy-compilers.com>
#

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

"""
Test default values for item types.
"""


from alignak.property import UnusedProp, NONE_OBJECT
import alignak.daemon

# TODO: clean import *
from alignak_test import *
from alignak.property import *

class PropertiesTester(object):

    def test_unused_properties(self):
        self.print_header()

        item = self.item # shortcut
        for name in self.unused_props:
            assert name in item.properties, \
                          'property %r not found in %s' % (name, self.item.my_type)
            assert isinstance(item.properties[name], UnusedProp)

    def test_properties_without_default(self):
        self.print_header()

        item = self.item # shortcut
        for name in self.without_default:
            assert name in item.properties, \
                          'property %r not found in %s' % (name, self.item.my_type)
            assert isinstance(item.properties[name], ( ListProp, StringProp, IntegerProp )), \
                'property %r is not `ListProp` or `StringProp` but %r' % (name, item.properties[name])
            assert item.properties[name].required, 'property %r is required' % name

    def test_default_values(self):
        self.print_header()

        item = self.item # shortcut
        for name, value in self.properties.iteritems():
            assert name in item.properties, \
                          'property %r not found in %s' % (name, self.item.my_type)
            if hasattr(item.properties[name], 'default'):
                if item.properties[name].default != value:
                    print "%s, %s: %s, %s" % (name, value, item.properties[name].default, value)
                if not item.properties[name].unused:
                    assert item.properties[name].default == value

    def test_all_props_are_tested(self):
        self.print_header()

        item = self.item # shortcut
        prop_names = set(list(self.properties.keys()) + self.unused_props + self.without_default)

        for name in item.properties:
            if name.startswith('$') and name.endswith('$'):
                continue
            assert name in prop_names, \
                          'unknown property %r found' % name

class TestConfig(PropertiesTester, AlignakTest):

    unused_props = [
        'log_file', 'object_cache_file', 'precached_object_file',
        'temp_file', 'status_file', 'status_update_interval',
        'command_check_interval', 'external_command_buffer_slots',
        'check_for_updates', 'bare_update_checks',
        'retain_state_information', 'use_retained_program_state',
        'use_retained_scheduling_info',
        'retained_host_attribute_mask',
        'retained_service_attribute_mask',
        'retained_process_host_attribute_mask',
        'retained_process_service_attribute_mask',
        'retained_contact_host_attribute_mask',
        'retained_contact_service_attribute_mask', 'sleep_time',
        'service_inter_check_delay_method',
        'service_interleave_factor', 'max_concurrent_checks',
        'check_result_reaper_frequency',
        'max_check_result_reaper_time', 'check_result_path',
        'max_check_result_file_age', 'host_inter_check_delay_method',
        'free_child_process_memory', 'child_processes_fork_twice',
        'admin_email', 'admin_pager', 'event_broker_options',
        'debug_file', 'debug_level', 'debug_verbosity',
        'max_debug_file_size']

    without_default = []

    properties = dict([
        ('prefix', ''),
        ('config_base_dir', ''),
        ('triggers_dir', ''),
        ('packs_dir', ''),
        ('resource_file', '/tmp/resources.txt'),
        ('enable_notifications', True),
        ('execute_service_checks', True),
        ('accept_passive_service_checks', True),
        ('execute_host_checks', True),
        ('accept_passive_host_checks', True),
        ('enable_event_handlers', True),
        ('log_rotation_method', 'd'),
        ('log_archive_path', '/usr/local/alignak/var/log/archives'),
        ('check_external_commands', True),
        ('main_config_file', '/usr/local/etc/alignak/alignak.cfg'),
        ('command_file', ''),
        ('state_retention_file', ''),
        ('retention_update_interval', 60),
        ('use_syslog', False),
        ('log_notifications', True),
        ('log_snapshots', True),
        ('log_flappings', True),
        ('log_active_checks', False),
        ('log_service_retries', True),
        ('log_host_retries', True),
        ('log_event_handlers', True),
        ('log_initial_states', True),
        ('log_external_commands', True),
        ('log_passive_checks', False),
        ('global_host_event_handler', ''),
        ('global_service_event_handler', ''),
        ('max_service_check_spread', 30),
        ('max_host_check_spread', 30),
        ('interval_length', 60),
        ('auto_reschedule_checks', True),
        ('auto_rescheduling_interval', 1),
        ('auto_rescheduling_window', 180),
        ('translate_passive_host_checks', True),
        ('passive_host_checks_are_soft', False),
        ('enable_predictive_host_dependency_checks', True),
        ('enable_predictive_service_dependency_checks', True),
        ('cached_host_check_horizon', 0),
        ('cached_service_check_horizon', 0),
        ('use_large_installation_tweaks', '0'),
        ('enable_environment_macros', True),
        ('enable_flap_detection', True),
        ('low_service_flap_threshold', 20),
        ('high_service_flap_threshold', 30),
        ('low_host_flap_threshold', 20),
        ('high_host_flap_threshold', 30),
        ('soft_state_dependencies', False),
        ('service_check_timeout', 60),
        ('host_check_timeout', 30),
        ('event_handler_timeout', 30),
        ('notification_timeout', 30),
        ('ocsp_timeout', 15),
        ('ochp_timeout', 15),
        ('perfdata_timeout', 5),
        ('obsess_over_services', False),
        ('ocsp_command', ''),
        ('obsess_over_hosts', False),
        ('ochp_command', ''),
        ('process_performance_data', True),
        ('host_perfdata_command', ''),
        ('service_perfdata_command', ''),
        ('host_perfdata_file', ''),
        ('service_perfdata_file', ''),
        ('host_perfdata_file_template', '/tmp/host.perf'),
        ('service_perfdata_file_template', '/tmp/host.perf'),
        ('host_perfdata_file_mode', 'a'),
        ('service_perfdata_file_mode', 'a'),
        ('host_perfdata_file_processing_interval', 15),
        ('service_perfdata_file_processing_interval', 15),
        ('host_perfdata_file_processing_command', ''),
        ('service_perfdata_file_processing_command', None),
        ('check_for_orphaned_services', True),
        ('check_for_orphaned_hosts', True),
        ('check_service_freshness', True),
        ('service_freshness_check_interval', 3600),
        ('check_host_freshness', True),
        ('host_freshness_check_interval', 3600),
        ('additional_freshness_latency', 15),
        ('enable_embedded_perl', True),
        ('use_embedded_perl_implicitly', False),
        ('date_format', None),
        ('use_timezone', ''),
        ('illegal_object_name_chars', '`~!$%^&*"|\'<>?,()='),
        ('illegal_macro_output_chars', ''),
        ('use_regexp_matching', False),
        ('use_true_regexp_matching', None),
        ('broker_module', ''),
        ('modified_attributes', 0L),

        # Alignak specific
        ('flap_history', 20),
        ('max_plugins_output_length', 8192),
        ('no_event_handlers_during_downtimes', False),
        ('cleaning_queues_interval', 900),
        ('disable_old_nagios_parameters_whining', False),
        ('enable_problem_impacts_states_change', False),
        ('resource_macros_names', []),

        # Discovery part
        ('runners_timeout', 3600),
        ('pack_distribution_file', 'pack_distribution.dat'),

        ('use_multiprocesses_serializer', False),
        ('daemon_thread_pool_size', 8),
        ('timeout_exit_status', 2),

        # statsd part
        ('statsd_host', 'localhost'),
        ('statsd_port', 8125),
        ('statsd_prefix', 'alignak'),
        ('statsd_enabled', False),
        ])

    def setUp(self):
        from alignak.objects.config import Config
        self.item = Config()


class TestCommand(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = ['command_name', 'command_line']

    properties = dict([
        ('uuid', ''),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('poller_tag', 'None'),
        ('reactionner_tag', 'None'),
        ('module_type', None),
        ('timeout', -1),
        ('enable_environment_macros', False),
        ])

    def setUp(self):
        from alignak.objects.command import Command
        self.item = None
        self.item = Command(parsing=True)
        print self.item.properties


class TestContactgroup(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = ['contactgroup_name', 'alias']

    properties = dict([
        ('uuid', ''),
        ('members', None),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('unknown_members', []),
        ('contactgroup_members', []),
        ])

    def setUp(self):
        from alignak.objects.contactgroup import Contactgroup
        self.item = Contactgroup(parsing=True)


class TestContact(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = [
        'contact_name',
        ]

    properties = dict([
        ('uuid', ''),
        ('host_notification_commands', []),
        ('service_notification_commands', []),
        ('host_notification_period', ''),
        ('service_notification_period', ''),
        ('service_notification_options', ['']),
        ('host_notification_options', ['']),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('alias', 'none'),
        ('contactgroups', []),
        ('host_notifications_enabled', True),
        ('service_notifications_enabled', True),
        ('min_business_impact', 0),
        ('email', 'none'),
        ('pager', 'none'),
        ('address1', 'none'),
        ('address2', 'none'),
        ('address3', 'none'),
        ('address4', 'none'),
        ('address5', 'none'),
        ('address6', 'none'),
        ('can_submit_commands', False),
        ('is_admin', False),
        ('expert', False),
        ('retain_status_information', True),
        ('notificationways', []),
        ('password', 'NOPASSWORDSET'),
        ])

    def setUp(self):
        from alignak.objects.contact import Contact
        self.item = Contact(parsing=True)


class TestEscalation(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = ['escalation_name', 'first_notification', 'last_notification', 'first_notification_time', 'last_notification_time']

    properties = dict([
        ('uuid', ''),
        ('host_name', ''),
        ('service_description', ''),
        ('contact_groups', []),
        ('contacts', []),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('notification_interval', -1),
        ('escalation_period', ''),
        ('escalation_options', ['d','u','r','w','c']),
        ])

    def setUp(self):
        from alignak.objects.escalation import Escalation
        self.item = Escalation(parsing=True)


class TestHostdependency(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = ['dependent_host_name', 'host_name']

    properties = dict([
        ('uuid', ''),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('dependent_hostgroup_name', ''),
        ('hostgroup_name', ''),
        ('inherits_parent', False),
        ('execution_failure_criteria', ['n']),
        ('notification_failure_criteria', ['n']),
        ('dependency_period', ''),
        ])

    def setUp(self):
        from alignak.objects.hostdependency import Hostdependency
        self.item = Hostdependency(parsing=True)


class TestHostescalation(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = [
        'host_name', 'hostgroup_name',
        'first_notification', 'last_notification',
        'contacts', 'contact_groups',
        'first_notification_time', 'last_notification_time',
        ]

    properties = dict([
        ('uuid', ''),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('notification_interval', 30),
        ('escalation_period', ''),
        ('escalation_options', ['d','u','r','w','c']),
        ])

    def setUp(self):
        from alignak.objects.hostescalation import Hostescalation
        self.item = Hostescalation(parsing=True)


class TestHostextinfo(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = ['host_name']

    properties = dict([
        ('uuid', ''),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('notes', ''),
        ('notes_url', ''),
        ('icon_image', ''),
        ('icon_image_alt', ''),
        ('vrml_image', ''),
        ('statusmap_image', ''),
        ('2d_coords', ''),
        ('3d_coords', ''),
        ])

    def setUp(self):
        from alignak.objects.hostextinfo import HostExtInfo
        self.item = HostExtInfo(parsing=True)


class TestHostgroup(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = ['hostgroup_name', 'alias']

    properties = dict([
        ('uuid', ''),
        ('members', None),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('unknown_members', []),
        ('uuid', ''),
        ('notes', ''),
        ('notes_url', ''),
        ('action_url', ''),
        ('realm', ''),
        ('hostgroup_members', []),
        ])

    def setUp(self):
        from alignak.objects.hostgroup import Hostgroup
        self.item = Hostgroup(parsing=True)


class TestHost(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = [
        'uuid', 'host_name', 'alias', 'address',
        'check_period', 'notification_period']

    properties = dict([
        # ('uuid', ''),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('display_name', ''),
        ('address6', ''),
        ('parents', []),
        ('hostgroups', []),
        ('check_command', '_internal_host_up'),
        ('initial_state', 'o'),
        ('freshness_state', 'x'),
        ('check_interval', 0),
        ('max_check_attempts', 1),
        ('retry_interval', 0),
        ('active_checks_enabled', True),
        ('passive_checks_enabled', True),
        ('obsess_over_host', False),
        ('check_freshness', False),
        ('freshness_threshold', -1),
        ('event_handler', ''),
        ('event_handler_enabled', False),
        ('low_flap_threshold', 25),
        ('high_flap_threshold', 50),
        ('flap_detection_enabled', True),
        ('flap_detection_options', ['o','d','x']),
        ('process_perf_data', True),
        ('retain_status_information', True),
        ('retain_nonstatus_information', True),
        ('contacts', []),
        ('contact_groups', []),
        ('notification_interval', 60),
        ('first_notification_delay', 0),
        ('notification_options', ['d','x','r','f']),
        ('notifications_enabled', True),
        ('stalking_options', ['']),
        ('notes', ''),
        ('notes_url', ''),
        ('action_url', ''),
        ('icon_image', ''),
        ('icon_image_alt', ''),
        ('icon_set', ''),
        ('vrml_image', ''),
        ('statusmap_image', ''),
        ('2d_coords', ''),
        ('3d_coords', ''),
        ('failure_prediction_enabled', False),
        ('realm', ''),
        ('poller_tag', 'None'),
        ('reactionner_tag', 'None'),
        ('resultmodulations', []),
        ('business_impact_modulations', []),
        ('escalations', []),
        ('maintenance_period', ''),
        ('business_impact', 2),
        ('trigger_name', ''),
        ('trigger_broker_raise_enabled', False),
        ('time_to_orphanage', 300),
        ('trending_policies', []),
        ('checkmodulations', []),
        ('macromodulations', []),
        ('custom_views', []),
        ('service_overrides', []),
        ('service_excludes', []),
        ('service_includes', []),
        ('business_rule_output_template', ''),
        ('business_rule_smart_notifications', False),
        ('business_rule_downtime_as_ack', False),
        ('labels', []),
        ('snapshot_interval', 5),
        ('snapshot_command', ''),
        ('snapshot_enabled', False),
        ('snapshot_period', ''),
        ('snapshot_criteria', ['d','x']),
        ('business_rule_host_notification_options', []),
        ('business_rule_service_notification_options', []),
        ])

    def setUp(self):
        from alignak.objects.host import Host
        self.item = Host(parsing=True)


class TestModule(PropertiesTester, AlignakTest):

    unused_props = []
    # unused_props = ['option_1', 'option_2', 'option_3']

    without_default = ['module_alias', 'python_name']

    properties = dict([
        ('uuid', ''),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('module_types', ['']),
        ('modules', ['']),
        ])

    def setUp(self):
        from alignak.objects.module import Module

        self.item = Module(parsing=True)


    unused_props = []

    without_default = [
        'notificationway_name',
        'host_notification_period', 'service_notification_period',
        'host_notification_commands', 'service_notification_commands']

    properties = dict([
        ('uuid', ''),
        ('service_notification_options', ['']),
        ('host_notification_options', ['']),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('host_notifications_enabled', True),
        ('service_notifications_enabled', True),
        ('min_business_impact', 0),
        ])

    def setUp(self):
        from alignak.objects.notificationway import NotificationWay
        self.item = NotificationWay(parsing=True)


class TestPack(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = ['pack_name']

    properties = dict([
        ('uuid', ''),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ])

    def setUp(self):
        from alignak.objects.pack import Pack
        self.item = Pack(parsing=True)


class TestRealm(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = ['realm_name']

    properties = dict([
        ('uuid', ''),
        ('members', None),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('alias', ''),
        ('unknown_members', []),
        ('realm_members', []),
        ('higher_realms', []),
        ('default', False),
        ])

    def setUp(self):
        from alignak.objects.realm import Realm
        self.item = Realm(parsing=True)


class TestResultmodulation(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = ['resultmodulation_name']

    properties = dict([
        ('uuid', ''),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('exit_codes_match', []),
        ('exit_code_modulation', None),
        ('modulation_period', None),
        ])

    def setUp(self):
        from alignak.objects.resultmodulation import Resultmodulation
        self.item = Resultmodulation(parsing=True)


class TestServicedependency(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = ['dependent_host_name', 'dependent_service_description', 'host_name', 'service_description']

    properties = dict([
        ('uuid', ''),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('dependent_hostgroup_name', ''),
        ('hostgroup_name', ''),
        ('inherits_parent', False),
        ('execution_failure_criteria', ['n']),
        ('notification_failure_criteria', ['n']),
        ('dependency_period', ''),
        ('explode_hostgroup', False),
        ])

    def setUp(self):
        from alignak.objects.servicedependency import Servicedependency
        self.item = Servicedependency(parsing=True)


class TestServiceescalation(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = [
        'host_name', 'hostgroup_name',
        'service_description',
        'first_notification', 'last_notification',
        'contacts', 'contact_groups',
        'first_notification_time', 'last_notification_time']

    properties = dict([
        ('uuid', ''),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('notification_interval', 30),
        ('escalation_period', ''),
        ('escalation_options', ['d','u','r','w','c']),
        ])

    def setUp(self):
        from alignak.objects.serviceescalation import Serviceescalation
        self.item = Serviceescalation(parsing=True)


class TestServiceextinfo(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = ['host_name', 'service_description']

    properties = dict([
        ('uuid', ''),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('notes', ''),
        ('notes_url', ''),
        ('icon_image', ''),
        ('icon_image_alt', ''),
        ])

    def setUp(self):
        from alignak.objects.serviceextinfo import ServiceExtInfo
        self.item = ServiceExtInfo(parsing=True)


class TestServicegroup(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = ['servicegroup_name', 'alias']

    properties = dict([
        ('uuid', ''),
        ('members', None),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('unknown_members', []),
        ('uuid', ''),
        ('notes', ''),
        ('notes_url', ''),
        ('action_url', ''),
        ('servicegroup_members', []),
        ])

    def setUp(self):
        from alignak.objects.servicegroup import Servicegroup
        self.item = Servicegroup(parsing=True)


class TestService(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = [
        'uuid', 'host_name', 'service_description',
        'check_command', 'check_period', 'notification_period']

    properties = dict([
        # ('uuid', ''),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('max_check_attempts', 1),
        ('hostgroup_name', ''),
        ('display_name', ''),
        ('servicegroups', []),
        ('is_volatile', False),
        ('initial_state', 'o'),
        ('freshness_state', 'x'),
        ('active_checks_enabled', True),
        ('passive_checks_enabled', True),
        ('obsess_over_service', False),
        ('check_freshness', False),
        ('freshness_threshold', -1),
        ('event_handler', ''),
        ('event_handler_enabled', False),
        ('check_interval', 0),
        ('retry_interval', 0),
        ('low_flap_threshold', 25),
        ('high_flap_threshold', 50),
        ('flap_detection_enabled', True),
        ('flap_detection_options', ['o','w','c','u','x']),
        ('process_perf_data', True),
        ('retain_status_information', True),
        ('retain_nonstatus_information', True),
        ('notification_interval', 60),
        ('first_notification_delay', 0),
        ('notification_options', ['w','u','c','r','f','s', 'x']),
        ('notifications_enabled', True),
        ('contacts', []),
        ('contact_groups', []),
        ('stalking_options', ['']),
        ('notes', ''),
        ('notes_url', ''),
        ('action_url', ''),
        ('icon_image', ''),
        ('icon_image_alt', ''),
        ('icon_set', ''),
        ('failure_prediction_enabled', False),
        ('parallelize_check', True),
        ('poller_tag', 'None'),
        ('reactionner_tag', 'None'),
        ('resultmodulations', []),
        ('business_impact_modulations', []),
        ('escalations', []),
        ('maintenance_period', ''),
        ('duplicate_foreach', ''),
        ('default_value', ''),
        ('business_impact', 2),
        ('trigger_name', ''),
        ('trigger_broker_raise_enabled', False),
        ('time_to_orphanage', 300),
        ('trending_policies', []),
        ('checkmodulations', []),
        ('macromodulations', []),
        ('aggregation', ''),
        ('service_dependencies', []),
        ('custom_views', []),
        ('merge_host_contacts', False),
        ('business_rule_output_template', ''),
        ('business_rule_smart_notifications', False),
        ('business_rule_downtime_as_ack', False),
        ('labels', []),
        ('snapshot_interval', 5),
        ('snapshot_command', ''),
        ('snapshot_enabled', False),
        ('snapshot_period', ''),
        ('snapshot_criteria', ['w','c','u','x']),
        ('business_rule_host_notification_options', []),
        ('business_rule_service_notification_options', []),
        ('host_dependency_enabled', True),
        ('realm', ''),
        ])

    def setUp(self):
        from alignak.objects.service import Service
        self.item = Service(parsing=True)


class TestTimeperiod(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = ['timeperiod_name']

    properties = dict([
        ('uuid', ''),
        ('imported_from', 'unknown'),
        ('use', []),
        ('definition_order', 100),
        ('name', ''),
        ('alias', ''),
        ('register', True),
        ('dateranges', []),
        ('exclude', []),
        ('is_active', False),
        ('activated_once', False),
        ('unresolved', []),
        ('invalid_entries', [])
        ])

    def setUp(self):
        from alignak.objects.timeperiod import Timeperiod
        self.item = Timeperiod(parsing=True)


class TestTrigger(PropertiesTester, AlignakTest):

    unused_props = []

    without_default = ['trigger_name']

    properties = dict([
        ('uuid', ''),
        ('imported_from', 'unknown'),
        ('use', []),
        ('register', True),
        ('definition_order', 100),
        ('name', ''),
        ('code_src', ''),
        ])

    def setUp(self):
        from alignak.objects.trigger import Trigger
        self.item = Trigger(parsing=True)


if __name__ == '__main__':
    unittest.main()
