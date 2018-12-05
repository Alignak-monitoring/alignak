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
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     xkilian, fmikus@acktomic.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Squiz, squiz@squiz.confais.org
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Romain Forlot, rforlot@yahoo.com
#     Dessai.Imrane, dessai.imrane@gmail.com
#     Frédéric Pégé, frederic.pege@gmail.com
#     Alexander Springer, alex.spri@gmail.com
#     Guillaume Bour, guillaume@bour.cc
#     Jan Ulferts, jan.ulferts@xing.com
#     Grégory Starck, g.starck@gmail.com
#     Thibault Cohen, titilambert@gmail.com
#     Christophe Simon, geektophe@gmail.com
#     Arthur Gautier, superbaloo@superbaloo.net
#     t0xicCode, xavier@openconcept.ca
#     Andreas Paul, xorpaul@gmail.com
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
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

""" Config is the class that reads, loads and manipulates the main Alignak monitored objects
 configuration. It reads the Nagios legacy configuration files (cfg files ) and gets all
 informations from these files.

 It creates the monitored objects (eg. hosts, contacts, ...), creates links between them,
 check them, clean them, and cut them into independent parts.

 The main user of this Config class is the Arbiter daemon when it loads the configuration and
 dispatches to the other daemons.
"""
# pylint: disable=C0302
import re
import string
import os
import socket
import itertools
import time
import random
import tempfile
import logging
from io import StringIO
import json

from alignak.alignakobject import get_a_new_object_id
from alignak.misc.serialization import serialize

from alignak.commandcall import CommandCall
from alignak.objects.item import Item
from alignak.objects.timeperiod import Timeperiod, Timeperiods
from alignak.objects.service import Service, Services
from alignak.objects.command import Command, Commands
from alignak.objects.resultmodulation import Resultmodulation, Resultmodulations
from alignak.objects.businessimpactmodulation import Businessimpactmodulation, \
    Businessimpactmodulations
from alignak.objects.escalation import Escalation, Escalations
from alignak.objects.serviceescalation import Serviceescalation, Serviceescalations
from alignak.objects.hostescalation import Hostescalation, Hostescalations
from alignak.objects.host import Host, Hosts
from alignak.objects.hostgroup import Hostgroup, Hostgroups
from alignak.objects.realm import Realm, Realms
from alignak.objects.contact import Contact, Contacts
from alignak.objects.contactgroup import Contactgroup, Contactgroups
from alignak.objects.notificationway import NotificationWay, NotificationWays
from alignak.objects.checkmodulation import CheckModulation, CheckModulations
from alignak.objects.macromodulation import MacroModulation, MacroModulations
from alignak.objects.servicegroup import Servicegroup, Servicegroups
from alignak.objects.servicedependency import Servicedependency, Servicedependencies
from alignak.objects.hostdependency import Hostdependency, Hostdependencies
from alignak.objects.module import Module, Modules
from alignak.objects.hostextinfo import HostExtInfo, HostsExtInfo
from alignak.objects.serviceextinfo import ServiceExtInfo, ServicesExtInfo
# from alignak.objects.trigger import Trigger, Triggers
# from alignak.objects.pack import Packs
from alignak.util import split_semicolon
from alignak.objects.arbiterlink import ArbiterLink, ArbiterLinks
from alignak.objects.schedulerlink import SchedulerLink, SchedulerLinks
from alignak.objects.reactionnerlink import ReactionnerLink, ReactionnerLinks
from alignak.objects.brokerlink import BrokerLink, BrokerLinks
from alignak.objects.receiverlink import ReceiverLink, ReceiverLinks
from alignak.objects.pollerlink import PollerLink, PollerLinks
from alignak.graph import Graph
from alignak.property import (UnusedProp, BoolProp, IntegerProp, CharProp,
                              StringProp, ListProp, ToGuessProp)
from alignak.util import jsonify_r


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

NO_LONGER_USED = (u'This parameter is not longer take from the main file, but must be defined '
                  u'in the status_dat broker module instead. But Alignak will create you one '
                  u'if there are no present and use this parameter in it, so no worry.')
NOT_INTERESTING = u'We do not think such an option is interesting to manage.'
NOT_MANAGED = (u'This Nagios legacy parameter is not managed by Alignak. Ignoring...')


class Config(Item):  # pylint: disable=R0904,R0902
    """Config is the class that reads, loads and manipulates the main Alignak monitored objects
 configuration. It reads the Nagios legacy configuration files (cfg files ) and gets all
 informations from these files.

 It creates the monitored objects (eg. hosts, contacts, ...), creates links between them,
 check them, clean them, and cut them into independent parts.

 The main user of this Config class is the Arbiter daemon when it loads the configuration and
 dispatches to the other daemons."""
    # Next value used for auto generated instance_id
    _next_id = 1

    cache_path = "objects.cache"
    my_type = "config"

    # Properties:
    # *required: if True, there is not default, and the config must put them
    # *default: if not set, take this value
    # *pythonize: function call to
    # *class_inherit: (Service, 'blabla'): must set this property to the
    #  Service class with name blabla
    #  if (Service, None): must set this property to the Service class with
    #  same name
    # *unused: just to warn the user that the option he use is no more used
    #  in Alignak
    # *usage_text: if present, will print it to explain why it's no more useful
    # ---
    # All the properties with 'full_status' in the fill_brok will be include in the
    # 'program_status' and 'update_program_status' broks.
    # ---
    """Configuration properties:
    """
    properties = {
        # -----
        # Included in the program status brok raised for the scheduler live state
        # -----
        # Used for the ALIGNAK macro
        # Alignak instance name is set as the arbiter name
        # if it is not defined in the configuration file
        'alignak_name':
            StringProp(default=u''),
        'alignak_env':
            ListProp(default=[]),

        # Configuration identification - instance id and name
        'instance_id':
            StringProp(default=u''),
        'config_name':
            StringProp(default=u'Main configuration'),

        'program_start':
            IntegerProp(default=0, fill_brok=['program_status']),
        'last_alive':
            IntegerProp(default=0),
        'last_log_rotation':
            IntegerProp(default=0),
        'last_command_check':
            IntegerProp(default=0),
        'pid':
            IntegerProp(default=0),
        'is_running':
            BoolProp(default=True),

        'modified_host_attributes':
            IntegerProp(default=0),
        'modified_service_attributes':
            IntegerProp(default=0),

        'daemon_mode':
            BoolProp(default=True),
        # -----

        # 'passive_host_checks_enabled':
        #     BoolProp(default=True, fill_brok=['full_status']),
        # 'passive_service_checks_enabled':
        #     BoolProp(default=True, fill_brok=['full_status']),
        # 'active_host_checks_enabled':
        #     BoolProp(default=True, fill_brok=['full_status']),
        # 'active_service_checks_enabled':
        #     BoolProp(default=True, fill_brok=['full_status']),
        'event_handlers_enabled':
            BoolProp(default=True, fill_brok=['full_status']),
        # 'flap_detection_enabled':
        #     BoolProp(default=True, fill_brok=['full_status']),
        # 'notifications_enabled':
        #     BoolProp(default=True, fill_brok=['full_status']),

        # Used for the MAINCONFIGFILE, CONFIGFILES and CONFIGBASEDIR macros
        # will be set when we will load a file
        'config_files':
            ListProp(default=[]),
        'main_config_file':
            StringProp(default=u''),
        'config_base_dir':
            StringProp(default=u''),

        # # Triggers directory
        # 'triggers_dir':
        #     UnusedProp(text=NOT_MANAGED),

        # Packs directory
        'packs_dir':
            UnusedProp(text=NOT_MANAGED),

        # Inner objects cache file for Nagios CGI
        'object_cache_file':
            UnusedProp(text=NOT_MANAGED),

        'precached_object_file':
            UnusedProp(text=NOT_MANAGED),

        # Unused Nagios configuration parameter
        'resource_file':
            UnusedProp(text=NOT_MANAGED),

        # Unused Nagios configuration parameter
        'temp_file':
            UnusedProp(text=NOT_MANAGED),
        'temp_path':
            UnusedProp(text=NOT_MANAGED),

        # Inner retention self created module parameter
        'status_file':
            UnusedProp(text=NO_LONGER_USED),

        'status_update_interval':
            UnusedProp(text=NO_LONGER_USED),

        # Enable the notifications
        'enable_notifications':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Host, None), (Service, None), (Contact, None)]),

        # Service checks
        'execute_service_checks':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Service, 'execute_checks')]),

        'accept_passive_service_checks':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Service, 'accept_passive_checks')]),

        # Host checks
        'execute_host_checks':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Host, 'execute_checks')]),

        'accept_passive_host_checks':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Host, 'accept_passive_checks')]),

        # Accept passive checks for unknown host/service
        'accept_passive_unknown_check_results':
            BoolProp(default=True, fill_brok=['full_status']),

        # Enable event handlers
        'enable_event_handlers':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Host, None), (Service, None)]),

        # Inner log self created module parameter
        'log_file':
            UnusedProp(text=NOT_MANAGED),
        'log_rotation_method':
            UnusedProp(text=NOT_MANAGED),
        'log_archive_path':
            UnusedProp(text=NOT_MANAGED),

        # Inner external commands self created module parameter
        'check_external_commands':
            BoolProp(default=True),
        'command_check_interval':
            UnusedProp(text=u'Alignak will always check for external commands. '
                            u'This configuration value is useless.'),
        'command_file':
            StringProp(default=u''),
        'external_command_buffer_slots':
            UnusedProp(text=u'Alignak do not limit the external commands slot.'),

        # Application updates checks
        'check_for_updates':
            UnusedProp(text=u'network administrators will never allow such communication between '
                            u'server and the external world. Use your distribution packet manager '
                            u'to know if updates are available or go to the '
                            u'http://www.github.com/Alignak-monitoring/alignak website instead.'),

        'bare_update_checks':
            UnusedProp(text=None),

        # -----
        # Inner state retention module parameters
        'retain_state_information':
            BoolProp(default=True),

        'state_retention_file':
            StringProp(default=u''),

        'retention_update_interval':
            IntegerProp(default=0),

        'use_retained_program_state':
            UnusedProp(text=NOT_INTERESTING),

        'use_retained_scheduling_info':
            UnusedProp(text=NOT_INTERESTING),

        'retained_host_attribute_mask':
            UnusedProp(text=NOT_INTERESTING),

        'retained_service_attribute_mask':
            UnusedProp(text=NOT_INTERESTING),

        'retained_process_host_attribute_mask':
            UnusedProp(text=NOT_INTERESTING),

        'retained_process_service_attribute_mask':
            UnusedProp(text=NOT_INTERESTING),

        'retained_contact_host_attribute_mask':
            UnusedProp(text=NOT_INTERESTING),

        'retained_contact_service_attribute_mask':
            UnusedProp(text=NOT_INTERESTING),
        # -----

        # Inner syslog self created module parameters
        'use_syslog':
            BoolProp(default=False),

        # Monitoring logs (Alignak events log) configuration
        'events_date_format':
            StringProp(default='%Y-%m-%d %H:%M:%S'),

        'events_log_count':
            IntegerProp(default=100),

        'log_notifications':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Host, None), (Service, None)]),

        'log_alerts':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Host, None), (Service, None)]),

        'log_acknowledgements':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Host, None), (Service, None)]),

        'log_downtimes':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Host, None), (Service, None)]),

        'log_event_handlers':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Host, None), (Service, None)]),

        'log_snapshots':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Host, None), (Service, None)]),

        'log_flappings':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Host, None), (Service, None)]),

        'log_initial_states':
            BoolProp(default=False, fill_brok=['full_status'],
                     class_inherit=[(Host, None), (Service, None)]),

        'log_external_commands':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Host, None), (Service, None)]),

        'log_passive_checks':
            BoolProp(default=False, fill_brok=['full_status'],
                     class_inherit=[(Host, None), (Service, None)]),

        'log_active_checks':
            BoolProp(default=False, fill_brok=['full_status'],
                     class_inherit=[(Host, None), (Service, None)]),

        'log_alignak_checks':
            BoolProp(default=False, fill_brok=['full_status']),

        # Global event handlers
        'global_host_event_handler':
            StringProp(default='', fill_brok=['full_status'],
                       class_inherit=[(Host, 'global_event_handler')]),

        'global_service_event_handler':
            StringProp(default='', fill_brok=['full_status'],
                       class_inherit=[(Service, 'global_event_handler')]),

        'sleep_time':
            UnusedProp(text=u'This deprecated option is useless in the alignak way of doing.'),

        'service_inter_check_delay_method':
            UnusedProp(text=u'This option is useless in the Alignak scheduling. '
                            'The only way is the smart way.'),

        'max_service_check_spread':
            IntegerProp(default=5, class_inherit=[(Service, 'max_check_spread')]),

        'service_interleave_factor':
            UnusedProp(text=u'This option is useless in the Alignak scheduling '
                            'because it use a random distribution for initial checks.'),

        'max_concurrent_checks':
            UnusedProp(text=u'Limiting the max concurrent checks is not helpful '
                            'to got a good running monitoring server.'),

        'check_result_reaper_frequency':
            UnusedProp(text=u'Alignak do not use reaper process.'),

        'max_check_result_reaper_time':
            UnusedProp(text=u'Alignak do not use reaper process.'),

        'check_result_path':
            UnusedProp(text=u'Alignak use in memory returns, not check results on flat file.'),

        'max_check_result_file_age':
            UnusedProp(text=u'Alignak do not use flat file check resultfiles.'),

        'host_inter_check_delay_method':
            UnusedProp(text=u'This option is unused in the Alignak scheduling because distribution '
                            'of the initial check is a random one.'),

        'max_host_check_spread':
            IntegerProp(default=5, class_inherit=[(Host, 'max_check_spread')]),

        'interval_length':
            IntegerProp(default=60, fill_brok=['full_status'],
                        class_inherit=[(Host, None), (Service, None)]),

        'auto_reschedule_checks':
            BoolProp(managed=False, default=True),

        'auto_rescheduling_interval':
            IntegerProp(managed=False, default=1),

        'auto_rescheduling_window':
            IntegerProp(managed=False, default=180),

        'translate_passive_host_checks':
            UnusedProp(text=u'Alignak passive checks management makes this parameter unuseful.'),

        'passive_host_checks_are_soft':
            UnusedProp(text=u'Alignak passive checks management makes this parameter unuseful.'),

        # Todo: not used anywhere in the source code
        'enable_predictive_host_dependency_checks':
            BoolProp(managed=False,
                     default=True,
                     class_inherit=[(Host, 'enable_predictive_dependency_checks')]),

        # Todo: not used anywhere in the source code
        'enable_predictive_service_dependency_checks':
            BoolProp(managed=False, default=True),

        # Todo: not used anywhere in the source code
        'cached_host_check_horizon':
            IntegerProp(default=0, class_inherit=[(Host, 'cached_check_horizon')]),

        # Todo: not used anywhere in the source code
        'cached_service_check_horizon':
            IntegerProp(default=0, class_inherit=[(Service, 'cached_check_horizon')]),

        'use_large_installation_tweaks':
            UnusedProp(text=u'this option is deprecated because in alignak it is just an alias '
                            u'for enable_environment_macros=False'),

        'free_child_process_memory':
            UnusedProp(text=u'this option is automatic in Python processes'),

        'child_processes_fork_twice':
            UnusedProp(text=u'fork twice is not used.'),

        'enable_environment_macros':
            BoolProp(default=False, class_inherit=[(Host, None), (Service, None)]),

        # Flapping management
        'enable_flap_detection':
            BoolProp(default=True, fill_brok=['full_status'],
                     class_inherit=[(Host, None), (Service, None)]),

        'low_service_flap_threshold':
            IntegerProp(default=20, fill_brok=['full_status'],
                        class_inherit=[(Service, 'global_low_flap_threshold')]),

        'high_service_flap_threshold':
            IntegerProp(default=30, fill_brok=['full_status'],
                        class_inherit=[(Service, 'global_high_flap_threshold')]),

        'low_host_flap_threshold':
            IntegerProp(default=20, fill_brok=['full_status'],
                        class_inherit=[(Host, 'global_low_flap_threshold')]),

        'high_host_flap_threshold':
            IntegerProp(default=30, fill_brok=['full_status'],
                        class_inherit=[(Host, 'global_high_flap_threshold')]),

        'flap_history':
            IntegerProp(default=20, class_inherit=[(Host, None), (Service, None)]),

        # Todo: not used anywhere in the source code
        'soft_state_dependencies':
            BoolProp(managed=False, default=False),

        # Check timeout
        'service_check_timeout':
            IntegerProp(default=60, class_inherit=[(Service, 'check_timeout')]),

        'host_check_timeout':
            IntegerProp(default=30, class_inherit=[(Host, 'check_timeout')]),

        'timeout_exit_status':
            IntegerProp(default=2),

        'event_handler_timeout':
            IntegerProp(default=30, class_inherit=[(Host, None), (Service, None)]),

        'notification_timeout':
            IntegerProp(default=30, class_inherit=[(Host, None), (Service, None)]),

        # Performance data management
        'perfdata_timeout':
            IntegerProp(default=5, class_inherit=[(Host, None), (Service, None)]),

        'process_performance_data':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

        'host_perfdata_command':
            StringProp(default='', class_inherit=[(Host, 'perfdata_command')]),

        'service_perfdata_command':
            StringProp(default='', class_inherit=[(Service, 'perfdata_command')]),

        # Inner perfdata self created module parameters
        'host_perfdata_file':
            StringProp(default=''),

        'service_perfdata_file':
            StringProp(default=''),

        'host_perfdata_file_template':
            StringProp(managed=False, default='/tmp/host.perf',
                       _help='Smartly replaced with the Alignak inner metrics feature or backend.'),

        'service_perfdata_file_template':
            StringProp(managed=False, default='/tmp/host.perf',
                       _help='Smartly replaced with the Alignak '
                             'inner metrics feature or backend.'),

        'host_perfdata_file_mode':
            CharProp(managed=False, default='a',
                     _help='Smartly replaced with the Alignak '
                           'inner metrics feature or backend.'),

        'service_perfdata_file_mode':
            CharProp(managed=False, default='a',
                     _help='Smartly replaced with the Alignak inner metrics feature or backend.'),

        'host_perfdata_file_processing_interval':
            IntegerProp(managed=False, default=15,
                        _help='Smartly replaced with the Alignak '
                              'inner metrics feature or backend.'),

        'service_perfdata_file_processing_interval':
            IntegerProp(managed=False, default=15,
                        _help='Smartly replaced with the Alignak '
                              'inner metrics feature or backend.'),

        'host_perfdata_file_processing_command':
            StringProp(managed=False, default=None,
                       _help='Smartly replaced with the Alignak inner metrics feature or backend.'),

        'service_perfdata_file_processing_command':
            StringProp(managed=False, default=None,
                       _help='Smartly replaced with the Alignak inner metrics feature or backend.'),

        # Hosts/services orphanage check
        'check_for_orphaned_services':
            BoolProp(default=True, class_inherit=[(Service, 'check_for_orphaned')]),

        'check_for_orphaned_hosts':
            BoolProp(default=True, class_inherit=[(Host, 'check_for_orphaned')]),

        # Freshness checks
        'check_service_freshness':
            BoolProp(default=True, class_inherit=[(Service, 'global_check_freshness')]),

        'service_freshness_check_interval':
            IntegerProp(default=60),

        'check_host_freshness':
            BoolProp(default=True, class_inherit=[(Host, 'global_check_freshness')]),

        'host_freshness_check_interval':
            IntegerProp(default=60),

        'additional_freshness_latency':
            IntegerProp(default=15, class_inherit=[(Host, None), (Service, None)]),

        'enable_embedded_perl':
            BoolProp(managed=False,
                     default=True,
                     _help='It will surely never be managed, '
                           'but it should not be useful with poller performances.'),
        'use_embedded_perl_implicitly':
            BoolProp(managed=False, default=False),

        # Todo: not used anywhere in the source code
        'date_format':
            StringProp(managed=False, default=None),

        'use_timezone':
            StringProp(default='', class_inherit=[(Host, None), (Service, None), (Contact, None)]),

        'illegal_object_name_chars':
            StringProp(default="""`~!$%^&*"|'<>?,()=""",
                       class_inherit=[(Host, None), (Service, None),
                                      (Contact, None), (HostExtInfo, None)]),

        'illegal_macro_output_chars':
            StringProp(default='',
                       class_inherit=[(Host, None), (Service, None), (Contact, None)]),
        'env_variables_prefix':
            StringProp(default='ALIGNAK_'),

        'use_regexp_matching':
            BoolProp(managed=False,
                     default=False,
                     _help='If you have some host or service definition like prod*, '
                           'it will surely fail from now, sorry.'),
        'use_true_regexp_matching':
            BoolProp(managed=False, default=None),

        'admin_email':
            UnusedProp(text=u'sorry, not yet implemented.'),

        'admin_pager':
            UnusedProp(text=u'sorry, not yet implemented.'),

        'event_broker_options':
            UnusedProp(text=u'event broker are replaced by modules '
                            'with a real configuration template.'),
        'broker_module':
            StringProp(default=''),

        'modified_attributes':
            IntegerProp(default=0),

        'daemon_thread_pool_size':
            IntegerProp(default=8),

        'max_plugins_output_length':
            IntegerProp(default=8192, class_inherit=[(Host, None), (Service, None)]),

        'no_event_handlers_during_downtimes':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

        # Interval between cleaning queues pass
        'cleaning_queues_interval':
            IntegerProp(default=900),

        # Now for problem/impact states changes
        'enable_problem_impacts_states_change':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

        # More a running value indeed - the macros catched in the parsed configuration
        'resource_macros_names':
            ListProp(default=[]),

        'runners_timeout':
            IntegerProp(default=3600),

        # Self created daemons configuration
        'launch_missing_daemons':
            BoolProp(default=False),

        'daemons_arguments':
            StringProp(default=''),

        'daemons_log_folder':
            StringProp(default='/usr/local/var/log/alignak'),

        'daemons_initial_port':
            IntegerProp(default=10000),

        # Kill launched daemons on communication failure
        'daemons_failure_kill':
            BoolProp(default=True),

        'daemons_check_period':
            IntegerProp(default=5),

        'daemons_start_timeout':
            IntegerProp(default=1),

        'daemons_new_conf_timeout':
            IntegerProp(default=1),

        'daemons_dispatch_timeout':
            IntegerProp(default=5),

        'daemons_stop_timeout':
            IntegerProp(default=5),
    }

    macros = {
        'ALIGNAK': 'alignak_name',
        'ALIGNAK_CONFIG': 'alignak_env',
        'CONFIGFILES': 'config_files',
        'MAINCONFIGFILE': 'main_config_file',
        'MAINCONFIGDIR': 'config_base_dir',
        'RETENTION_FILE': 'state_retention_file',
        # The following one are Nagios specific features...
        'STATUSDATAFILE': '',
        'COMMENTDATAFILE': '',
        'DOWNTIMEDATAFILE': '',
        'RETENTIONDATAFILE': '',
        'OBJECTCACHEFILE': '',
        'TEMPFILE': '',
        'TEMPPATH': '',
        'LOGFILE': '',
        'RESOURCEFILE': '',
        'COMMANDFILE': '',
        'HOSTPERFDATAFILE': '',
        'SERVICEPERFDATAFILE': '',
        'ADMINEMAIL': '',
        'ADMINPAGER': ''
    }

    # To create dict of objects from the raw objects got from files or backend
    # Dictionary: objects type: {
    #   Class of object,
    #   Class of objects list,
    #   'name of the Config property for the objects',
    #   True to create an intial index,
    #   True if the property is clonable
    # }
    types_creations = {
        'timeperiod':
            (Timeperiod, Timeperiods, 'timeperiods', True, True),
        'service':
            (Service, Services, 'services', False, True),
        'servicegroup':
            (Servicegroup, Servicegroups, 'servicegroups', True, True),
        'command':
            (Command, Commands, 'commands', True, True),
        'host':
            (Host, Hosts, 'hosts', True, True),
        'hostgroup':
            (Hostgroup, Hostgroups, 'hostgroups', True, True),
        'contact':
            (Contact, Contacts, 'contacts', True, True),
        'contactgroup':
            (Contactgroup, Contactgroups, 'contactgroups', True, True),
        'notificationway':
            (NotificationWay, NotificationWays, 'notificationways', True, True),
        'checkmodulation':
            (CheckModulation, CheckModulations, 'checkmodulations', True, True),
        'macromodulation':
            (MacroModulation, MacroModulations, 'macromodulations', True, True),
        'servicedependency':
            (Servicedependency, Servicedependencies, 'servicedependencies', True, True),
        'hostdependency':
            (Hostdependency, Hostdependencies, 'hostdependencies', True, True),
        'arbiter':
            (ArbiterLink, ArbiterLinks, 'arbiters', True, False),
        'scheduler':
            (SchedulerLink, SchedulerLinks, 'schedulers', True, False),
        'reactionner':
            (ReactionnerLink, ReactionnerLinks, 'reactionners', True, False),
        'broker':
            (BrokerLink, BrokerLinks, 'brokers', True, False),
        'receiver':
            (ReceiverLink, ReceiverLinks, 'receivers', True, False),
        'poller':
            (PollerLink, PollerLinks, 'pollers', True, False),
        'realm':
            (Realm, Realms, 'realms', True, False),
        'module':
            (Module, Modules, 'modules', True, False),
        'resultmodulation':
            (Resultmodulation, Resultmodulations, 'resultmodulations', True, True),
        'businessimpactmodulation':
            (Businessimpactmodulation, Businessimpactmodulations,
             'businessimpactmodulations', True, True),
        'escalation':
            (Escalation, Escalations, 'escalations', True, True),
        'serviceescalation':
            (Serviceescalation, Serviceescalations, 'serviceescalations', False, False),
        'hostescalation':
            (Hostescalation, Hostescalations, 'hostescalations', False, False),
        'hostextinfo':
            (HostExtInfo, HostsExtInfo, 'hostsextinfo', True, False),
        'serviceextinfo':
            (ServiceExtInfo, ServicesExtInfo, 'servicesextinfo', True, False),
    }

    # This tab is used to transform old parameters name into new ones
    # so from Nagios2 format, to Nagios3 ones
    old_properties = {
        'nagios_user':  'alignak_user',
        'nagios_group': 'alignak_group'
    }

    read_config_silent = False

    early_created_types = ['arbiter', 'module']

    configuration_types = ['void', 'timeperiod', 'command',
                           'realm',
                           'host', 'hostgroup', 'hostdependency', 'hostextinfo',
                           'service', 'servicegroup', 'servicedependency', 'serviceextinfo',
                           'contact', 'contactgroup',
                           'notificationway', 'escalation', 'serviceescalation', 'hostescalation',
                           'checkmodulation', 'macromodulation', 'resultmodulation',
                           'businessimpactmodulation',
                           'arbiter', 'scheduler', 'reactionner', 'broker', 'receiver', 'poller',
                           'module']

    def __init__(self, params=None, parsing=True):
        if params is None:
            params = {}

        if parsing:
            # Create a new configuration identifier
            self.instance_id = u'%s_%d' % (self.__class__.__name__, self.__class__._next_id)
            self.__class__._next_id += 1

            # let's compute the "USER" properties and macros..
            for i in range(1, 65):
                if '$USER%d$' % i in self.__class__.properties:
                    continue
                self.__class__.macros['USER%d' % i] = '$USER%s$' % i
                self.__class__.properties['$USER%d$' % i] = StringProp(default='')

            # Fill all the configuration properties with their default values
            self.fill_default()
        elif 'instance_id' not in params:
            logger.error("When not parsing a configuration, an instance_id "
                         "must exist in the provided parameters for a configuration!")
        else:
            self.instance_id = params['instance_id']

        # At deserialization, those are dictionaries
        # TODO: Separate parsing instance from recreated ones
        for prop in ['host_perfdata_command', 'service_perfdata_command',
                     'global_host_event_handler', 'global_service_event_handler']:
            if prop in params and isinstance(params[prop], dict):
                # We recreate the object
                setattr(self, prop, CommandCall(params[prop], parsing=parsing))
                # And remove prop, to prevent from being overridden
                del params[prop]

        for _, clss, strclss, _, _ in list(self.types_creations.values()):
            if strclss in params and isinstance(params[strclss], dict):
                setattr(self, strclss, clss(params[strclss], parsing=parsing))
                del params[strclss]

        super(Config, self).__init__(params, parsing=parsing)
        self.params = {}
        self.resource_macros_names = []

        # The configuration files I read
        self.my_cfg_files = []

        # By default the conf is correct and the warnings and errors lists are empty
        self.conf_is_correct = True
        self.configuration_warnings = []
        self.configuration_errors = []

        # We tag the conf with a magic_hash, a random value to
        # identify this conf
        random.seed(time.time())
        self.magic_hash = random.randint(1, 100000)

        # Store daemons detected as missing during the configuration check
        self.missing_daemons = []

    def __repr__(self):  # pragma: no cover
        return '<%s %s - %s />' % (self.__class__.__name__, self.instance_id,
                                   getattr(self, 'config_name', 'unknown'))
    __str__ = __repr__

    def serialize(self):
        res = super(Config, self).serialize()

        # The following are not in properties so not in the dict
        for prop in ['hosts', 'services', 'hostgroups', 'notificationways',
                     'checkmodulations', 'macromodulations', 'businessimpactmodulations',
                     'resultmodulations', 'contacts', 'contactgroups',
                     'servicegroups', 'timeperiods', 'commands',
                     'escalations',
                     'host_perfdata_command', 'service_perfdata_command',
                     'global_host_event_handler', 'global_service_event_handler']:
            if getattr(self, prop, None) in [None, '', 'None']:
                res[prop] = None
            else:
                res[prop] = getattr(self, prop).serialize()
        res['macros'] = self.macros
        return res

    def clean_params(self, params):
        """Convert a list of parameters (key=value) into a dict

        This function is used to transform Nagios (or ini) like formated parameters (key=value)
        to a dictionary.

        :param params: parameters list
        :type params: list
        :return: dict with key and value. Log error if malformed
        :rtype: dict
        """
        clean_p = {}
        for elt in params:
            elts = elt.split('=', 1)
            if len(elts) == 1:  # error, there is no = !
                self.add_error("the parameter %s is malformed! (no = sign)" % elts[0])
            else:
                if elts[1] == '':
                    self.add_warning("the parameter %s is ambiguous! "
                                     "No value after =, assuming an empty string" % elts[0])
                clean_p[elts[0]] = elts[1]

        return clean_p

    def load_params(self, params):
        """Load parameters from main configuration file

        :param params: parameters list (converted right at the beginning)
        :type params:
        :return: None
        """
        logger.debug("Alignak parameters:")
        for key, value in sorted(self.clean_params(params).items()):
            update_attribute = None

            # Maybe it's a variable as $USER$ or $ANOTHERVARIABLE$
            # so look at the first character. If it's a $, it is a macro variable
            # if it ends with $ too
            if key[0] == '$' and key[-1] == '$':
                key = key[1:-1]
                # Update the macros list
                if key not in self.__class__.macros:
                    logger.debug("New macro %s: %s - %s", self, key, value)
                self.__class__.macros[key] = '$%s$' % key
                key = '$%s$' % key

                logger.debug("- macro %s", key)
                update_attribute = value
                # Create a new property to store the macro value
                if isinstance(value, list):
                    self.__class__.properties[key] = ListProp(default=value)
                else:
                    self.__class__.properties[key] = StringProp(default=value)
            elif key in self.properties:
                update_attribute = self.properties[key].pythonize(value)
            elif key in self.running_properties:
                logger.warning("using a the running property %s in a config file", key)
                update_attribute = self.running_properties[key].pythonize(value)
            elif key.startswith('$') or key in ['cfg_file', 'cfg_dir']:
                # it's a macro or a useless now param, we don't touch this
                update_attribute = value
            else:
                logger.debug("Guessing the property '%s' type because it "
                             "is not in %s object properties", key, self.__class__.__name__)
                update_attribute = ToGuessProp().pythonize(value)

            if update_attribute is not None:
                setattr(self, key, update_attribute)
                logger.debug("- update %s = %s", key, update_attribute)

        # Change Nagios2 names to Nagios3 ones (before using them)
        self.old_properties_names_to_new()

        # Fill default for myself - new properties entry becomes a self attribute
        self.fill_default()

    @staticmethod
    def _cut_line(line):
        """Split the line on whitespaces and remove empty chunks

        :param line: the line to split
        :type line: str
        :return: list of strings
        :rtype: list
        """
        # punct = '"#$%&\'()*+/<=>?@[\\]^`{|}~'
        if re.search("([\t\n\r]+|[\x0b\x0c ]{3,})+", line):
            tmp = re.split("([\t\n\r]+|[\x0b\x0c ]{3,})+", line, 1)
        else:
            tmp = re.split("[" + string.whitespace + "]+", line, 1)
        res = [elt.strip() for elt in tmp if elt.strip() != '']
        return res

    def read_legacy_cfg_files(self, cfg_files, alignak_env_files=None):
        # pylint: disable=too-many-nested-blocks,too-many-statements
        # pylint: disable=too-many-branches, too-many-locals
        """Read and parse the Nagios legacy configuration files
        and store their content into a StringIO object which content
        will be returned as the function result

        :param cfg_files: list of file to read
        :type cfg_files: list
        :param alignak_env_files: name of the alignak environment file
        :type alignak_env_files: list
        :return: a buffer containing all files
        :rtype: str
        """
        cfg_buffer = ''
        if not cfg_files:
            return cfg_buffer

        # Update configuration with the first legacy configuration file name and path
        # This will update macro properties
        self.alignak_env = 'n/a'
        if alignak_env_files is not None:
            self.alignak_env = alignak_env_files
            if not isinstance(alignak_env_files, list):
                self.alignak_env = [os.path.abspath(alignak_env_files)]
            else:
                self.alignak_env = [os.path.abspath(f) for f in alignak_env_files]
        self.main_config_file = os.path.abspath(cfg_files[0])
        self.config_base_dir = os.path.dirname(self.main_config_file)

        # Universal newline mode (all new lines are managed internally)
        res = StringIO(u"# Configuration cfg_files buffer", newline=None)

        if not self.read_config_silent and cfg_files:
            logger.info("Reading the configuration cfg_files...")

        # A first pass to get all the configuration cfg_files in a buffer
        for cfg_file in cfg_files:
            # Make sure the configuration cfg_files are not repeated...
            if os.path.abspath(cfg_file) in self.my_cfg_files:
                logger.warning("- ignoring repeated file: %s", os.path.abspath(cfg_file))
                continue
            self.my_cfg_files.append(os.path.abspath(cfg_file))

            # File header
            res.write(u"\n")
            res.write(u"# imported_from=%s" % cfg_file)
            res.write(u"\n")

            if not self.read_config_silent:
                logger.info("- opening '%s' configuration file", cfg_file)
            try:
                # Open in Universal way for Windows, Mac, Linux-based systems
                file_d = open(cfg_file, 'r')
                buf = file_d.readlines()
                file_d.close()
            except IOError as exp:
                self.add_error("cannot open main file '%s' for reading: %s" % (cfg_file, exp))
                continue

            for line in buf:
                try:
                    line = line.decode('utf8', 'replace')
                except AttributeError:
                    # Python 3 will raise an exception because the line is still unicode
                    pass

                line = line.strip()
                res.write(line)
                res.write(u"\n")

                if (re.search("^cfg_file", line) or re.search("^resource_file", line)) \
                        and '=' in line:
                    elts = line.split('=', 1)
                    if os.path.isabs(elts[1]):
                        cfg_file_name = elts[1]
                    else:
                        cfg_file_name = os.path.join(self.config_base_dir, elts[1])
                    cfg_file_name = cfg_file_name.strip()
                    cfg_file_name = os.path.abspath(cfg_file_name)

                    # Make sure the configuration cfg_files are not repeated...
                    if cfg_file_name in self.my_cfg_files:
                        logger.warning("- ignoring repeated file: %s", cfg_file_name)
                    else:
                        self.my_cfg_files.append(cfg_file_name)

                        if not self.read_config_silent:
                            logger.info("  reading: %s", cfg_file_name)

                        try:
                            # Read the file content to the buffer
                            file_d = open(cfg_file_name, 'r')

                            # File header
                            res.write(u"\n")
                            res.write(u"# imported_from=%s" % cfg_file_name)
                            res.write(u"\n")

                            content = file_d.read()
                            try:
                                content = content.decode('utf8', 'replace')
                            except AttributeError:
                                # Python 3 will raise an exception
                                pass
                            res.write(content)
                            res.write(u"\n")
                            file_d.close()
                        except IOError as exp:
                            self.add_error(u"cannot open file '%s' for reading: %s"
                                           % (cfg_file_name, exp))
                elif re.search("^cfg_dir", line) and '=' in line:
                    elts = line.split('=', 1)
                    if os.path.isabs(elts[1]):
                        cfg_dir_name = elts[1]
                    else:
                        cfg_dir_name = os.path.join(self.config_base_dir, elts[1])
                    # Ok, look if it's really a directory
                    if not os.path.isdir(cfg_dir_name):
                        self.add_error(u"cannot open directory '%s' for reading" % cfg_dir_name)
                        continue

                    # Now walk for it.
                    for root, _, walk_files in os.walk(cfg_dir_name, followlinks=True):
                        for found_file in walk_files:
                            if not re.search(r"\.cfg$", found_file):
                                continue

                            cfg_file_name = os.path.join(root, found_file)
                            # Make sure the configuration cfg_files are not repeated...
                            if os.path.abspath(cfg_file_name) in self.my_cfg_files:
                                logger.warning("- ignoring repeated file: %s", cfg_file_name)
                            else:
                                self.my_cfg_files.append(cfg_file_name)

                                if not self.read_config_silent:
                                    logger.info("  reading: %s", cfg_file_name)

                                try:
                                    # Read the file content to the buffer
                                    file_d = open(cfg_file_name, 'r')

                                    # File header
                                    res.write(u"\n")
                                    res.write(u"# imported_from=%s" % cfg_file_name)
                                    res.write(u"\n")

                                    content = file_d.read()
                                    try:
                                        content = content.decode('utf8', 'replace')
                                    except AttributeError:
                                        # Python 3 will raise an exception
                                        pass
                                    res.write(content)
                                    res.write(u"\n")
                                    file_d.close()
                                except IOError as exp:
                                    self.add_error(u"cannot open file '%s' for reading: %s"
                                                   % (cfg_file_name, exp))

        cfg_buffer = res.getvalue()
        res.close()

        return cfg_buffer

    def read_config_buf(self, cfg_buffer):
        # pylint: disable=too-many-locals, too-many-branches
        """The legacy configuration buffer (previously returned by Config.read_config())

        If the buffer is empty, it will return an empty dictionary else it will return a
        dictionary containing dictionary items tha tmay be used to create Alignak
        objects

        :param cfg_buffer: buffer containing all data from config files
        :type cfg_buffer: str
        :return: dict of alignak objects with the following structure ::
        { type1 : [{key: value, ..}, {..}],
          type2 : [ ... ]
        }

        Example ::

        { 'host' : [{'host_name': 'myhostname', ..}, {..}],
          'service' : [ ... ]
        }

        Values are all str for now. It is pythonized at object creation

        :rtype: dict
        """
        objects = {}
        if not self.read_config_silent:
            if cfg_buffer:
                logger.info("Parsing the legacy configuration files...")
            else:
                logger.info("No legacy configuration files.")
                return objects

        params = []
        objectscfg = {}
        for o_type in self.__class__.configuration_types:
            objectscfg[o_type] = []

        tmp = []
        tmp_type = 'void'
        in_define = False
        almost_in_define = False
        continuation_line = False
        tmp_line = ''
        lines = cfg_buffer.split('\n')
        line_nb = 0  # Keep the line number for the file path
        filefrom = ''
        for line in lines:
            if line.startswith("# imported_from="):
                filefrom = line.split('=')[1]
                line_nb = 0  # reset the line number too
                if not self.read_config_silent:
                    logger.debug("#####\n# file: %s", filefrom)
                continue
            if not self.read_config_silent:
                logger.debug("- %d: %s", line_nb, line)

            line_nb += 1
            # Remove comments
            line = split_semicolon(line)[0].strip()

            # A backslash means, there is more to come
            if re.search(r"\\\s*$", line) is not None:
                continuation_line = True
                line = re.sub(r"\\\s*$", "", line)
                line = re.sub(r"^\s+", " ", line)
                tmp_line += line
                continue
            elif continuation_line:
                # Now the continuation line is complete
                line = re.sub(r"^\s+", "", line)
                line = tmp_line + line
                tmp_line = ''
                continuation_line = False

            # } alone in a line means stop the object reading
            if re.search(r"^\s*}\s*$", line) is not None:
                in_define = False

            # { alone in a line can mean start object reading
            if re.search(r"^\s*\{\s*$", line) is not None and almost_in_define:
                almost_in_define = False
                in_define = True
                continue

            if re.search(r"^\s*#|^\s*$|^\s*}", line) is not None:
                pass
            # A define must be catched and the type saved
            # The old entry must be saved before
            elif re.search("^define", line) is not None:
                if re.search(r".*\{.*$", line) is not None:  # pylint: disable=R0102
                    in_define = True
                else:
                    almost_in_define = True

                if tmp_type not in objectscfg:
                    objectscfg[tmp_type] = []
                objectscfg[tmp_type].append(tmp)
                tmp = []
                tmp.append("imported_from %s:%s" % (filefrom, line_nb))
                # Get new type
                elts = re.split(r'\s', line)
                # Maybe there was space before and after the type
                # so we must get all and strip it
                tmp_type = ' '.join(elts[1:]).strip()
                tmp_type = tmp_type.split('{')[0].strip()
            else:
                if in_define:
                    tmp.append(line)
                else:
                    params.append(line)

        # Maybe the type of the last element is unknown, declare it
        if tmp_type not in objectscfg:
            objectscfg[tmp_type] = []
        objectscfg[tmp_type].append(tmp)

        # Check and load the parameters
        self.load_params(params)

        for o_type in objectscfg:
            objects[o_type] = []
            for items in objectscfg[o_type]:
                tmp_obj = {}
                for line in items:
                    elts = self._cut_line(line)
                    if elts == []:
                        continue
                    prop = elts[0]
                    if prop not in tmp_obj:
                        tmp_obj[prop] = []
                    value = ' '.join(elts[1:])
                    tmp_obj[prop].append(value)
                if tmp_obj != {}:
                    # Create a new object
                    objects[o_type].append(tmp_obj)

        return objects

    @staticmethod
    def add_self_defined_objects(raw_objects):
        """Add self defined command objects for internal processing ;
        bp_rule, _internal_host_up, _echo, _internal_host_check, _interna_service_check

        :param raw_objects: Raw config objects dict
        :type raw_objects: dict
        :return: raw_objects with some more commands
        :rtype: dict
        """
        logger.info("- creating internally defined commands...")
        if 'command' not in raw_objects:
            raw_objects['command'] = []
        # Business rule
        raw_objects['command'].append({
            'command_name': 'bp_rule',
            'command_line': 'bp_rule',
            'imported_from': 'alignak-self'
        })
        # Internal host checks
        raw_objects['command'].append({
            'command_name': '_internal_host_up',
            'command_line': '_internal_host_up',
            'imported_from': 'alignak-self'
        })
        raw_objects['command'].append({
            'command_name': '_internal_host_check',
            # Command line must contain: state_id;output
            'command_line': '_internal_host_check;$ARG1$;$ARG2$',
            'imported_from': 'alignak-self'
        })
        # Internal service check
        raw_objects['command'].append({
            'command_name': '_echo',
            'command_line': '_echo',
            'imported_from': 'alignak-self'
        })
        raw_objects['command'].append({
            'command_name': '_internal_service_check',
            # Command line must contain: state_id;output
            'command_line': '_internal_service_check;$ARG1$;$ARG2$',
            'imported_from': 'alignak-self'
        })

    def early_create_objects(self, raw_objects):
        """Create the objects needed for the post configuration file initialization

        :param raw_objects:  dict with all object with str values
        :type raw_objects: dict
        :return: None
        """
        types_creations = self.__class__.types_creations
        early_created_types = self.__class__.early_created_types

        logger.info("Creating objects...")
        for o_type in sorted(types_creations):
            if o_type in early_created_types:
                self.create_objects_for_type(raw_objects, o_type)
        logger.info("Done")

    def create_objects(self, raw_objects):
        """Create all the objects got after the post configuration file initialization

        :param raw_objects:  dict with all object with str values
        :type raw_objects: dict
        :return: None
        """
        types_creations = self.__class__.types_creations
        early_created_types = self.__class__.early_created_types

        logger.info("Creating objects...")

        # Before really creating the objects, we add some ghost
        # ones like the bp_rule for correlation
        self.add_self_defined_objects(raw_objects)

        for o_type in sorted(types_creations):
            if o_type not in early_created_types:
                self.create_objects_for_type(raw_objects, o_type)
        logger.info("Done")

    def create_objects_for_type(self, raw_objects, o_type):
        """Generic function to create objects regarding the o_type

        This function create real Alignak objects from the raw data got from the configuration.

        :param raw_objects: Raw objects
        :type raw_objects: dict
        :param o_type: the object type we want to create
        :type o_type: object
        :return: None
        """

        # Ex: the above code do for timeperiods:
        # timeperiods = []
        # for timeperiodcfg in objects['timeperiod']:
        #    t = Timeperiod(timeperiodcfg)
        #    timeperiods.append(t)
        # self.timeperiods = Timeperiods(timeperiods)

        types_creations = self.__class__.types_creations
        (cls, clss, prop, initial_index, _) = types_creations[o_type]

        # List to store the created objects
        lst = []
        try:
            logger.info("- creating '%s' objects", o_type)
            for obj_cfg in raw_objects[o_type]:
                # We create the object
                my_object = cls(obj_cfg)
                # and append it to the list
                lst.append(my_object)
            if not lst:
                logger.info("  none.")
        except KeyError:
            logger.info("  no %s objects in the configuration", o_type)

        # Create the objects list and set it in our properties
        setattr(self, prop, clss(lst, initial_index))

    def early_arbiter_linking(self, arbiter_name, params):
        """ Prepare the arbiter for early operations

        :param arbiter_name: default arbiter name if no arbiter exist in the configuration
        :type arbiter_name: str
        :return: None
        """

        if not self.arbiters:
            params.update({
                'name': arbiter_name, 'arbiter_name': arbiter_name,
                'host_name': socket.gethostname(),
                'address': '127.0.0.1', 'port': 7770,
                'spare': '0'
            })
            logger.warning("There is no arbiter, I add myself (%s) reachable on %s:%d",
                           arbiter_name, params['address'], params['port'])
            arb = ArbiterLink(params, parsing=True)
            self.arbiters = ArbiterLinks([arb])

        # First fill default
        self.arbiters.fill_default()
        self.modules.fill_default()

        self.arbiters.linkify(modules=self.modules)
        self.modules.linkify()

    def linkify_one_command_with_commands(self, commands, prop):
        """
        Link a command

        :param commands: object commands
        :type commands: object
        :param prop: property name
        :type prop: str
        :return: None
        """

        if not hasattr(self, prop):
            return

        command = getattr(self, prop).strip()
        if not command:
            setattr(self, prop, None)
            return

        data = {"commands": commands, "call": command}
        if hasattr(self, 'poller_tag'):
            data.update({"poller_tag": self.poller_tag})
        if hasattr(self, 'reactionner_tag'):
            data.update({"reactionner_tag": self.reactionner_tag})

        setattr(self, prop, CommandCall(data))

    def linkify(self):
        """ Make 'links' between elements, like a host got a services list
        with all its services in it

        :return: None
        """

        self.services.optimize_service_search(self.hosts)

        # First linkify myself like for some global commands
        self.linkify_one_command_with_commands(self.commands, 'host_perfdata_command')
        self.linkify_one_command_with_commands(self.commands, 'service_perfdata_command')
        self.linkify_one_command_with_commands(self.commands, 'global_host_event_handler')
        self.linkify_one_command_with_commands(self.commands, 'global_service_event_handler')

        # link hosts with timeperiods and commands
        self.hosts.linkify(self.timeperiods, self.commands,
                           self.contacts, self.realms,
                           self.resultmodulations, self.businessimpactmodulations,
                           self.escalations, self.hostgroups,
                           self.checkmodulations, self.macromodulations)

        self.hostsextinfo.merge(self.hosts)

        # Do the simplify AFTER explode groups
        # link hostgroups with hosts
        self.hostgroups.linkify(self.hosts, self.realms)

        # link services with other objects
        self.services.linkify(self.hosts, self.commands,
                              self.timeperiods, self.contacts,
                              self.resultmodulations, self.businessimpactmodulations,
                              self.escalations, self.servicegroups,
                              self.checkmodulations, self.macromodulations)

        self.servicesextinfo.merge(self.services)

        # link servicegroups members with services
        self.servicegroups.linkify(self.hosts, self.services)

        # link notificationways with timeperiods and commands
        self.notificationways.linkify(self.timeperiods, self.commands)

        # link notificationways with timeperiods and commands
        self.checkmodulations.linkify(self.timeperiods, self.commands)

        # Link with timeperiods
        self.macromodulations.linkify(self.timeperiods)

        # link contacgroups with contacts
        self.contactgroups.linkify(self.contacts)

        # link contacts with timeperiods and commands
        self.contacts.linkify(self.commands, self.notificationways)

        # link timeperiods with timeperiods (exclude part)
        self.timeperiods.linkify()

        self.servicedependencies.linkify(self.hosts, self.services,
                                         self.timeperiods)

        self.hostdependencies.linkify(self.hosts, self.timeperiods)
        self.resultmodulations.linkify(self.timeperiods)

        self.businessimpactmodulations.linkify(self.timeperiods)

        self.escalations.linkify(self.timeperiods, self.contacts,
                                 self.services, self.hosts)

        # Link all satellite links with modules
        self.schedulers.linkify(self.modules)
        self.brokers.linkify(self.modules)
        self.receivers.linkify(self.modules)
        self.reactionners.linkify(self.modules)
        self.pollers.linkify(self.modules)

        # Ok, now update all realms with back links of satellites
        satellites = {}
        for sat in self.schedulers:
            satellites[sat.uuid] = sat
        for sat in self.pollers:
            satellites[sat.uuid] = sat
        for sat in self.reactionners:
            satellites[sat.uuid] = sat
        for sat in self.receivers:
            satellites[sat.uuid] = sat
        for sat in self.brokers:
            satellites[sat.uuid] = sat
        self.realms.prepare_satellites(satellites)

    def clean(self):
        """Wrapper for calling the clean method of services attribute

        :return: None
        """
        logger.debug("Cleaning configuration objects before configuration sending:")
        types_creations = self.__class__.types_creations
        for o_type in types_creations:
            (_, _, inner_property, _, _) = types_creations[o_type]
            logger.debug("  . for %s", inner_property, )
            inner_object = getattr(self, inner_property)
            inner_object.clean()

    def warn_about_unmanaged_parameters(self):
        """used to raise warning if the user got parameter
        that we do not manage from now

        :return: None
        """
        properties = self.__class__.properties
        unmanaged = []
        for prop, entry in list(properties.items()):
            if not entry.managed and hasattr(self, prop):
                if entry.help:
                    line = "%s: %s" % (prop, entry.help)
                else:
                    line = prop
                unmanaged.append(line)
        if unmanaged:
            logger.warning("The following Nagios legacy parameter(s) are not currently "
                           "managed by Alignak:")

            for line in unmanaged:
                logger.warning('- %s', line)

            logger.warning("Those are unmanaged configuration statements, do you really need it? "
                           "Create an issue on the Alignak repository or submit a pull "
                           "request: http://www.github.com/Alignak-monitoring/alignak")

    def override_properties(self):
        """Wrapper for calling override_properties method of services attribute

        :return:
        """
        self.services.override_properties(self.hosts)

    def explode(self):
        """Use to fill groups values on hosts and create new services
        (for host group ones)

        :return: None
        """
        # first elements, after groups
        self.contacts.explode(self.contactgroups, self.notificationways)
        self.contactgroups.explode()

        self.hosts.explode(self.hostgroups, self.contactgroups)

        self.hostgroups.explode()

        self.services.explode(self.hosts, self.hostgroups, self.contactgroups,
                              self.servicegroups, self.servicedependencies)
        self.servicegroups.explode()

        self.timeperiods.explode()

        self.hostdependencies.explode(self.hostgroups)

        self.servicedependencies.explode(self.hostgroups)

        # Serviceescalations hostescalations will create new escalations
        self.serviceescalations.explode(self.escalations)
        self.hostescalations.explode(self.escalations)
        self.escalations.explode(self.hosts, self.hostgroups, self.contactgroups)

        # Now the architecture part
        self.realms.explode()

    def apply_dependencies(self):
        """Creates dependencies links between elements.

        :return: None
        """
        self.hosts.apply_dependencies()
        self.services.apply_dependencies(self.hosts)

    def apply_inheritance(self):
        """Apply inheritance over templates
        Template can be used in the following objects::

        * hosts
        * contacts
        * services
        * servicedependencies
        * hostdependencies
        * timeperiods
        * hostsextinfo
        * servicesextinfo
        * serviceescalations
        * hostescalations
        * escalations

        :return: None
        """
        # inheritance properties by template
        self.hosts.apply_inheritance()
        self.contacts.apply_inheritance()
        self.services.apply_inheritance()
        self.servicedependencies.apply_inheritance()
        self.hostdependencies.apply_inheritance()
        # Also timeperiods
        self.timeperiods.apply_inheritance()
        # Also "Hostextinfo"
        self.hostsextinfo.apply_inheritance()
        # Also "Serviceextinfo"
        self.servicesextinfo.apply_inheritance()

        # Now escalations too
        self.serviceescalations.apply_inheritance()
        self.hostescalations.apply_inheritance()
        self.escalations.apply_inheritance()

    def apply_implicit_inheritance(self):
        """Wrapper for calling apply_implicit_inheritance method of services attributes
        Implicit inheritance is between host and service (like notification parameters etc)

        :return:None
        """
        self.services.apply_implicit_inheritance(self.hosts)

    def fill_default_configuration(self):
        """Fill objects properties with default value if necessary

        :return: None
        """
        logger.debug("Filling the unset properties with their default value:")

        types_creations = self.__class__.types_creations
        for o_type in types_creations:
            (_, _, inner_property, _, _) = types_creations[o_type]
            # Not yet for the realms and daemons links
            if inner_property in ['realms', 'arbiters', 'schedulers', 'reactionners',
                                  'pollers', 'brokers', 'receivers']:
                continue
            logger.debug("  . for %s", inner_property,)
            inner_object = getattr(self, inner_property, None)
            if inner_object is None:
                logger.debug("No %s to fill with default values", inner_property)
                continue
            inner_object.fill_default()

        # We have all monitored elements, we can create a default realm if none is defined
        if getattr(self, 'realms', None) is not None:
            self.fill_default_realm()
            self.realms.fill_default()

            # Then we create missing satellites, so no other satellites will be created after
            self.fill_default_satellites(self.launch_missing_daemons)

        types_creations = self.__class__.types_creations
        for o_type in types_creations:
            (_, _, inner_property, _, _) = types_creations[o_type]
            if getattr(self, inner_property, None) is None:
                logger.debug("No %s to fill with default values", inner_property)
                continue
            # Only for the daemons links
            if inner_property in ['schedulers', 'reactionners', 'pollers', 'brokers', 'receivers']:
                logger.debug("  . for %s", inner_property,)
                inner_object = getattr(self, inner_property)
                inner_object.fill_default()

        # Now fill some fields we can predict (like address for hosts)
        self.hosts.fill_predictive_missing_parameters()
        self.services.fill_predictive_missing_parameters()

    def fill_default_realm(self):
        """Check if a realm is defined, if not
        Create a new one (default) and tag everyone that do not have
        a realm prop to be put in this realm

        :return: None
        """
        if not getattr(self, 'realms', None):
            # Create a default realm so all hosts without realm will be linked with it
            default = Realm({
                'realm_name': u'All', 'alias': u'Self created default realm', 'default': '1'
            })
            self.realms = Realms([default])
            logger.warning("No realms defined, I am adding one as %s", default.get_name())

        # Check that a default realm (and only one) is defined and get this default realm
        self.realms.fill_default()

    def log_daemons_list(self):
        """Log Alignak daemons list

        :return:
        """
        daemons = [self.arbiters, self.schedulers, self.pollers,
                   self.brokers, self.reactionners, self.receivers]
        for daemons_list in daemons:
            if not daemons_list:
                logger.debug("- %ss: None", daemons_list.inner_class.my_type)
            else:
                logger.debug("- %ss: %s", daemons_list.inner_class.my_type,
                             ','.join([daemon.get_name() for daemon in daemons_list]))

    def fill_default_satellites(self, alignak_launched=False):
        # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        """If a required satellite is missing in the configuration, we create a new satellite
        on localhost with some default values

        :param alignak_launched: created daemons are to be launched or not
        :type alignak_launched: bool
        :return: None
        """

        # Log all satellites list
        logger.debug("Alignak configured daemons list:")
        self.log_daemons_list()

        # We must create relations betweens the realms first. This is necessary to have
        # an accurate map of the situation!
        self.realms.linkify()
        self.realms.get_default(check=True)

        # Get list of known realms
        # realms_names = [realm.get_name() for realm in self.realms]

        # Create one instance of each satellite type if it does not exist...
        if not self.schedulers:
            logger.warning("No scheduler defined, I am adding one on 127.0.0.1:%d",
                           self.daemons_initial_port)
            satellite = SchedulerLink({'type': 'scheduler', 'name': 'Default-Scheduler',
                                       'realm': self.realms.default.get_name(),
                                       'alignak_launched': alignak_launched,
                                       'missing_daemon': True,
                                       'spare': '0', 'manage_sub_realms': '0',
                                       'address': '127.0.0.1', 'port': self.daemons_initial_port})
            self.daemons_initial_port = self.daemons_initial_port + 1
            self.schedulers = SchedulerLinks([satellite])
            self.missing_daemons.append(satellite)
        if not self.reactionners:
            logger.warning("No reactionner defined, I am adding one on 127.0.0.1:%d",
                           self.daemons_initial_port)
            satellite = ReactionnerLink({'type': 'reactionner', 'name': 'Default-Reactionner',
                                         'realm': self.realms.default.get_name(),
                                         'alignak_launched': alignak_launched,
                                         'missing_daemon': True,
                                         'spare': '0', 'manage_sub_realms': '0',
                                         'address': '127.0.0.1', 'port': self.daemons_initial_port})
            self.daemons_initial_port = self.daemons_initial_port + 1
            self.reactionners = ReactionnerLinks([satellite])
            self.missing_daemons.append(satellite)
        if not self.pollers:
            logger.warning("No poller defined, I am adding one on 127.0.0.1:%d",
                           self.daemons_initial_port)
            satellite = PollerLink({'type': 'poller', 'name': 'Default-Poller',
                                    'realm': self.realms.default.get_name(),
                                    'alignak_launched': alignak_launched,
                                    'missing_daemon': True,
                                    'spare': '0', 'manage_sub_realms': '0',
                                    'address': '127.0.0.1', 'port': self.daemons_initial_port})
            self.daemons_initial_port = self.daemons_initial_port + 1
            self.pollers = PollerLinks([satellite])
            self.missing_daemons.append(satellite)
        if not self.brokers:
            logger.warning("No broker defined, I am adding one on 127.0.0.1:%d",
                           self.daemons_initial_port)
            satellite = BrokerLink({'type': 'broker', 'name': 'Default-Broker',
                                    'realm': self.realms.default.get_name(),
                                    'alignak_launched': alignak_launched,
                                    'missing_daemon': True,
                                    'spare': '0', 'manage_sub_realms': '0',
                                    'address': '127.0.0.1', 'port': self.daemons_initial_port})
            self.daemons_initial_port = self.daemons_initial_port + 1
            self.brokers = BrokerLinks([satellite])
            self.missing_daemons.append(satellite)
        if not self.receivers:
            logger.warning("No receiver defined, I am adding one on 127.0.0.1:%d",
                           self.daemons_initial_port)
            satellite = ReceiverLink({'type': 'receiver', 'name': 'Default-Receiver',
                                      'alignak_launched': alignak_launched,
                                      'missing_daemon': True,
                                      'spare': '0', 'manage_sub_realms': '0',
                                      'address': '127.0.0.1', 'port': self.daemons_initial_port})
            self.daemons_initial_port = self.daemons_initial_port + 1
            self.receivers = ReceiverLinks([satellite])
            self.missing_daemons.append(satellite)

        # Assign default realm to the satellites that do not have a defined realm
        for satellites_list in [self.pollers, self.brokers, self.reactionners,
                                self.receivers, self.schedulers]:
            for satellite in satellites_list:
                # Here the 'realm' property is not yet a real realm object uuid ...
                # but still a realm name! Make it a realm uuid
                if not getattr(satellite, 'realm', None):
                    satellite.realm = self.realms.default.get_name()
                sat_realm = self.realms.find_by_name(satellite.realm)
                if not sat_realm:
                    self.add_error("The %s '%s' is affected to an unknown realm: '%s'"
                                   % (satellite.type, satellite.name, satellite.realm))
                    continue

                # satellite.realm_name = sat_realm.get_name()
                logger.info("Tagging satellite '%s' with realm %s", satellite.name, satellite.realm)
                satellite.realm = sat_realm.uuid
                satellite.realm_name = sat_realm.get_name()

                # Alert for spare daemons
                if getattr(satellite, 'spare', False):
                    self.add_warning("The %s '%s' is declared as a spare daemon. "
                                     "Spare mode is not yet implemented and it will be ignored."
                                     % (satellite.type, satellite.name))
                    continue

                # Alert for non active daemons
                if not getattr(satellite, 'active', False):
                    self.add_warning("The %s '%s' is declared as a non active daemon. "
                                     "It will be ignored."
                                     % (satellite.type, satellite.name))
                    continue

                # And tell the realm that it knows the satellite
                realm_satellites = getattr(sat_realm, '%ss' % satellite.type)
                if satellite.uuid not in realm_satellites:
                    realm_satellites.append(satellite.uuid)

                # If the satellite manages sub realms...
                # We update the "potential_" satellites that may be used for this realm
                if satellite.manage_sub_realms:
                    for realm_uuid in sat_realm.all_sub_members:
                        logger.debug("Linkify %s '%s' with realm %s",
                                     satellite.type, satellite.name,
                                     self.realms[realm_uuid].get_name())
                        realm_satellites = getattr(self.realms[realm_uuid],
                                                   'potential_%ss' % satellite.type)
                        if satellite.uuid not in realm_satellites:
                            realm_satellites.append(satellite.uuid)

        # Parse hosts for realms and set host in the default realm if no realm is set
        hosts_realms_names = set()
        logger.debug("Hosts realm configuration:")
        for host in self.hosts:
            if not getattr(host, 'realm', None):
                # todo: perharps checking hostgroups realm (if any) to set an hostgroup realm
                # rather than the default realm
                logger.debug("Host: %s, realm: %s, hostgroups: %s",
                             host.get_name(), host.realm, host.hostgroups)
                host.realm = self.realms.default.get_name()
                host.got_default_realm = True
            host_realm = self.realms.find_by_name(host.realm)
            if not host_realm:
                self.add_error("The host '%s' is affected to an unknown realm: '%s'"
                               % (host.get_name(), host.realm))
                continue
            host.realm_name = host_realm.get_name()
            host_realm.add_members(host.get_name())
            logger.debug("- tagging host '%s' with realm %s", host.get_name(), host.realm_name)
            hosts_realms_names.add(host.realm_name)

            logger.debug(" - %s: realm %s, active %s, passive %s",
                         host.get_name(), host_realm.get_name(),
                         host.active_checks_enabled, host.passive_checks_enabled)
            host_realm.passively_checked_hosts = \
                host_realm.passively_checked_hosts or host.passive_checks_enabled
            host_realm.actively_checked_hosts = \
                host_realm.actively_checked_hosts or host.passive_checks_enabled
            hosts_realms_names.add(host.realm)

        # Parse hostgroups for realms and set hostgroup in the default realm if no realm is set
        hostgroups_realms_names = set()
        logger.debug("Hostgroups realm configuration:")
        for hostgroup in self.hostgroups:
            if not getattr(hostgroup, 'realm', None):
                hostgroup.realm = self.realms.default.get_name()
                hostgroup.got_default_realm = True
            hostgroup_realm = self.realms.find_by_name(hostgroup.realm)
            if not hostgroup_realm:
                self.add_error("The hostgroup '%s' is affected to an unknown realm: '%s'"
                               % (hostgroup.get_name(), hostgroup.realm))
                continue
            hostgroup.realm_name = hostgroup_realm.get_name()
            hostgroup_realm.add_group_members(hostgroup.get_name())
            logger.debug("- tagging hostgroup '%s' with realm %s",
                         hostgroup.get_name(), hostgroup.realm_name)
            hostgroups_realms_names.add(hostgroup.realm_name)

        # Check that all daemons and realms are coherent
        for satellites_list in [self.pollers, self.brokers, self.reactionners,
                                self.receivers, self.schedulers]:
            sat_class = satellites_list.inner_class
            # Collect the names of all the realms that are managed by all the satellites
            sat_realms_names = set()
            for satellite in satellites_list:
                for realm in self.realms:
                    realm_satellites = getattr(realm, '%ss' % satellite.type)
                    realm_potential_satellites = getattr(realm, 'potential_%ss' % satellite.type)
                    if satellite.uuid in realm_satellites or \
                            satellite.uuid in realm_potential_satellites:
                        sat_realms_names.add(realm.get_name())

            if not hosts_realms_names.issubset(sat_realms_names):
                # Check if a daemon is able to manage the concerned hosts...
                for realm_name in hosts_realms_names.difference(sat_realms_names):
                    realm = self.realms.find_by_name(realm_name)

                    self.add_warning("Some hosts exist in the realm '%s' but no %s is "
                                     "defined for this realm." % (realm_name, sat_class.my_type))

                    if not alignak_launched:
                        continue

                    # Add a self-generated daemon
                    logger.warning("Adding a %s for the realm: %s", satellite.type, realm_name)
                    new_daemon = sat_class({
                        'type': satellite.type, 'name': '%s-%s' % (satellite.type, realm_name),
                        'alignak_launched': True, 'missing_daemon': True,
                        'realm': realm.uuid, 'manage_sub_realms': '0', 'spare': '0',
                        'address': '127.0.0.1', 'port': self.daemons_initial_port
                    })
                    satellites_list.add_item(new_daemon)

                    # And tell the realm that it knows the satellite
                    realm_satellites = getattr(realm, '%ss' % satellite.type)
                    if new_daemon.uuid not in realm_satellites:
                        realm_satellites.append(new_daemon.uuid)

                    self.add_warning("Added a %s (%s, %s) for the realm '%s'"
                                     % (satellite.type, '%s-%s' % (satellite.type, realm_name),
                                        satellite.uri, realm_name))
                    self.daemons_initial_port = self.daemons_initial_port + 1
                    self.missing_daemons.append(new_daemon)

        logger.debug("Realms hosts configuration:")
        for realm in self.realms:
            logger.debug("Realm: %s, actively checked hosts %s, passively checked hosts %s",
                         realm.get_name(), realm.actively_checked_hosts,
                         realm.passively_checked_hosts)
            logger.info("Realm: %s, hosts: %s, groups: %s",
                        realm.get_name(), realm.members, realm.group_members)

        # Log all satellites list
        logger.debug("Alignak definitive daemons list:")
        self.log_daemons_list()

    def got_broker_module_type_defined(self, module_type):
        """Check if a module type is defined in one of the brokers

        :param module_type: module type to search for
        :type module_type: str
        :return: True if mod_type is found else False
        :rtype: bool
        """
        for broker_link in self.brokers:
            for module in broker_link.modules:
                if module.is_a_module(module_type):
                    return True
        return False

    def got_scheduler_module_type_defined(self, module_type):
        """Check if a module type is defined in one of the schedulers

        :param module_type: module type to search for
        :type module_type: str
        :return: True if mod_type is found else False
        :rtype: bool
        TODO: Factorize it with got_broker_module_type_defined
        """
        for scheduler_link in self.schedulers:
            for module in scheduler_link.modules:
                if module.is_a_module(module_type):
                    return True
        return False

    def got_arbiter_module_type_defined(self, module_type):
        """Check if a module type is defined in one of the arbiters
        Also check the module name

        :param module_type: module type to search for
        :type module_type: str
        :return: True if mod_type is found else False
        :rtype: bool
        TODO: Factorize it with got_broker_module_type_defined:
        """
        for arbiter in self.arbiters:
            # Do like the linkify will do after....
            for module in getattr(arbiter, 'modules', []):
                # So look at what the arbiter try to call as module
                module_name = module.get_name()
                # Ok, now look in modules...
                for mod in self.modules:
                    # try to see if this module is the good type
                    if getattr(mod, 'python_name', '').strip() == module_type.strip():
                        # if so, the good name?
                        if getattr(mod, 'name', '').strip() == module_name:
                            return True
        return False

    def create_business_rules(self):
        """Create business rules for hosts and services

        :return: None
        """
        self.hosts.create_business_rules(self.hosts, self.services,
                                         self.hostgroups, self.servicegroups,
                                         self.macromodulations, self.timeperiods)
        self.services.create_business_rules(self.hosts, self.services,
                                            self.hostgroups, self.servicegroups,
                                            self.macromodulations, self.timeperiods)

    def create_business_rules_dependencies(self):
        """Create business rules dependencies for hosts and services

        :return: None
        """

        for item in itertools.chain(self.hosts, self.services):
            if not item.got_business_rule:
                continue

            bp_items = item.business_rule.list_all_elements()
            for bp_item_uuid in bp_items:
                if bp_item_uuid in self.hosts:
                    bp_item = self.hosts[bp_item_uuid]
                    notif_options = item.business_rule_host_notification_options
                else:  # We have a service
                    bp_item = self.services[bp_item_uuid]
                    notif_options = item.business_rule_service_notification_options

                if notif_options:
                    bp_item.notification_options = notif_options

                bp_item.act_depend_of_me.append((item.uuid, ['d', 'u', 's', 'f', 'c', 'w', 'x'],
                                                 '', True))

                # TODO: Is it necessary? We already have this info in act_depend_* attributes
                item.parent_dependencies.add(bp_item.uuid)
                bp_item.child_dependencies.add(item.uuid)

    def hack_old_nagios_parameters(self):
        # pylint: disable=too-many-branches
        """ Check if modules exist for some of the Nagios legacy parameters.

        If no module of the required type is present, it alerts the user that the parameters will
        be ignored and the functions will be disabled, else it encourages the user to set the
        correct parameters in the installed modules.

        Note that some errors are raised if some parameters are used and no module is found
        to manage the corresponding feature.

        TODO: clean this part of the configuration checking! Nagios ascending compatibility!

        :return: modules list
        :rtype: list
        """
        modules = []
        # For status_dat
        if getattr(self, 'status_file', None) and getattr(self, 'object_cache_file', None):
            msg = "The configuration parameters '%s = %s' and '%s = %s' are deprecated " \
                  "and will be ignored. Please configure your external 'retention' module " \
                  "as expected." % \
                  ('status_file', self.status_file,
                   'object_cache_file', self.object_cache_file)
            logger.warning(msg)
            self.add_warning(msg)

        # Now the log_file
        if getattr(self, 'log_file', None):
            msg = "The configuration parameter '%s = %s' is deprecated " \
                  "and will be ignored. Please configure your external 'logs' module " \
                  "as expected." % \
                  ('log_file', self.log_file)
            logger.warning(msg)
            self.add_warning(msg)

        # Now the syslog facility
        if getattr(self, 'use_syslog', None):
            msg = "The configuration parameter '%s = %s' is deprecated " \
                  "and will be ignored. Please configure your external 'logs' module " \
                  "as expected." % \
                  ('use_syslog', self.use_syslog)
            logger.warning(msg)
            self.add_warning(msg)

        # Now the host_perfdata or service_perfdata module
        if getattr(self, 'service_perfdata_file', None) or \
                getattr(self, 'host_perfdata_file', None):
            msg = "The configuration parameters '%s = %s' and '%s = %s' are Nagios legacy " \
                  "parameters. Alignak will use its inner 'metrics' module " \
                  "to match the expected behavior." \
                  % ('host_perfdata_file', self.host_perfdata_file,
                     'service_perfdata_file', self.service_perfdata_file)
            logger.warning(msg)
            self.add_warning(msg)
            mod_configuration = {
                'name': 'inner-metrics',
                'type': 'metrics',
                'python_name': 'alignak.modules.inner_metrics',
                'imported_from': 'inner',
                'enabled': True
            }
            if getattr(self, 'host_perfdata_file', None):
                mod_configuration['host_perfdata_file'] = \
                    getattr(self, 'host_perfdata_file')
            if getattr(self, 'service_perfdata_file', None):
                mod_configuration['service_perfdata_file'] = \
                    getattr(self, 'service_perfdata_file')
            logger.debug("inner metrics module, configuration: %s", mod_configuration)

            modules.append((
                'broker', mod_configuration
            ))

        # Now the Nagios legacy retention file module
        if hasattr(self, 'retain_state_information') and self.retain_state_information:
            # Do not raise a warning log for this, only an information
            msg = "The configuration parameter '%s = %s' is a Nagios legacy " \
                  "parameter. Alignak will use its inner 'retention' module " \
                  "to match the expected behavior." \
                  % ('retain_state_information', self.retain_state_information)
            logger.info(msg)
            # self.add_warning(msg)
            mod_configuration = {
                'name': 'inner-retention',
                'type': 'retention',
                'python_name': 'alignak.modules.inner_retention',
                'imported_from': 'inner',
                'enabled': True
            }
            if getattr(self, 'state_retention_file', None) is not None:
                mod_configuration['retention_file'] = getattr(self, 'state_retention_file')
            if getattr(self, 'state_retention_dir', None) is not None:
                mod_configuration['retention_dir'] = getattr(self, 'state_retention_dir')
            if getattr(self, 'retention_update_interval', None):
                self.tick_update_retention = int(self.retention_update_interval) * 60
                mod_configuration['retention_period'] = int(self.retention_update_interval) * 60
            logger.debug("inner retention module, configuration: %s", mod_configuration)

            modules.append((
                'scheduler', mod_configuration
            ))

        # Now the command_file
        if hasattr(self, 'command_file') and getattr(self, 'command_file'):
            msg = "The configuration parameter '%s = %s' is deprecated " \
                  "and will be ignored. Please configure an external commands capable " \
                  "module as expected (eg external-commands, NSCA, or WS module may suit." \
                  % ('command_file', self.command_file)
            logger.warning(msg)
            self.add_warning(msg)

        return modules

    def propagate_timezone_option(self):
        """Set our timezone value and give it too to unset satellites

        :return: None
        """
        if self.use_timezone:
            # first apply myself
            os.environ['TZ'] = self.use_timezone
            time.tzset()

            tab = [self.schedulers, self.pollers, self.brokers, self.receivers, self.reactionners]
            for sat_list in tab:
                for sat in sat_list:
                    if sat.use_timezone == 'NOTSET':
                        setattr(sat, 'use_timezone', self.use_timezone)

    def linkify_templates(self):
        """ Like for normal object, we link templates with each others

        :return: None
        """
        self.hosts.linkify_templates()
        self.contacts.linkify_templates()
        self.services.linkify_templates()
        self.servicedependencies.linkify_templates()
        self.hostdependencies.linkify_templates()
        self.timeperiods.linkify_templates()
        self.hostsextinfo.linkify_templates()
        self.servicesextinfo.linkify_templates()
        self.escalations.linkify_templates()
        # But also old srv and host escalations
        self.serviceescalations.linkify_templates()
        self.hostescalations.linkify_templates()

    def check_error_on_hard_unmanaged_parameters(self):
        """Some parameters are just not managed like O*HP commands  and regexp capabilities

        :return: True if we encounter an error, otherwise False
        :rtype: bool
        """
        valid = True
        if self.use_regexp_matching:
            msg = "use_regexp_matching parameter is not managed."
            logger.warning(msg)
            self.add_warning(msg)
            valid &= False
        if getattr(self, 'failure_prediction_enabled', None):
            msg = "failure_prediction_enabled parameter is not managed."
            logger.warning(msg)
            self.add_warning(msg)
            valid &= False
        if getattr(self, 'obsess_over_hosts', None):
            msg = "obsess_over_hosts parameter is not managed."
            logger.warning(msg)
            self.add_warning(msg)
            valid &= False
        if getattr(self, 'ochp_command', None):
            msg = "ochp_command parameter is not managed."
            logger.warning(msg)
            self.add_warning(msg)
            valid &= False
        if getattr(self, 'ochp_timeout', None):
            msg = "ochp_timeout parameter is not managed."
            logger.warning(msg)
            self.add_warning(msg)
            valid &= False
        if getattr(self, 'obsess_over_services', None):
            msg = "obsess_over_services parameter is not managed."
            logger.warning(msg)
            self.add_warning(msg)
            valid &= False
        if getattr(self, 'ocsp_command', None):
            msg = "ocsp_command parameter is not managed."
            logger.warning(msg)
            self.add_warning(msg)
            valid &= False
        if getattr(self, 'ocsp_timeout', None):
            msg = "ocsp_timeout parameter is not managed."
            logger.warning(msg)
            self.add_warning(msg)
            valid &= False
        return valid

    def is_correct(self):  # pylint: disable=too-many-branches, too-many-statements, too-many-locals
        """Check if all elements got a good configuration

        :return: True if the configuration is correct else False
        :rtype: bool
        """
        logger.info('Running pre-flight check on configuration data, initial state: %s',
                    self.conf_is_correct)
        valid = self.conf_is_correct

        # Check if alignak_name is defined
        if not self.alignak_name:
            logger.info('Alignak name is not defined, using the main arbiter name...')
            for arbiter in self.arbiters:
                if not arbiter.spare:
                    self.alignak_name = arbiter.name
                    break
        logger.info('Alignak name is: %s', self.alignak_name)

        # Globally unmanaged parameters
        if not self.read_config_silent:
            logger.info('Checking global parameters...')

        # Old Nagios legacy unmanaged parameters
        self.check_error_on_hard_unmanaged_parameters()

        # If we got global event handlers, they should be valid
        if self.global_host_event_handler and not self.global_host_event_handler.is_valid():
            msg = "[%s::%s] global host event_handler '%s' is invalid" \
                  % (self.my_type, self.get_name(), self.global_host_event_handler.command)
            self.add_error(msg)
            valid = False

        if self.global_service_event_handler and not self.global_service_event_handler .is_valid():
            msg = "[%s::%s] global service event_handler '%s' is invalid" \
                  % (self.my_type, self.get_name(), self.global_service_event_handler .command)
            self.add_error(msg)
            valid = False

        if not self.read_config_silent:
            logger.info('Checked')

        if not self.read_config_silent:
            logger.info('Checking monitoring configuration...')

        classes = [strclss for _, _, strclss, _, _ in list(self.types_creations.values())]
        for strclss in sorted(classes):
            if strclss in ['hostescalations', 'serviceescalations']:
                logger.debug("Ignoring correctness check for '%s'...", strclss)
                continue

            if not self.read_config_silent:
                logger.info('- checking %s...', strclss)

            try:
                checked_list = getattr(self, strclss)
            except AttributeError:  # pragma: no cover, simple protection
                logger.info("\t%s are not present in the configuration", strclss)
                continue

            if not checked_list.is_correct():
                if not self.read_config_silent:
                    logger.info('Checked %s, configuration is incorrect!', strclss)

                valid = False
                self.configuration_errors += checked_list.configuration_errors
                self.add_error("%s configuration is incorrect!" % strclss)
                logger.error("%s configuration is incorrect!", strclss)
            if checked_list.configuration_warnings:
                self.configuration_warnings += checked_list.configuration_warnings
                logger.info("    %d warning(s), total: %d",
                            len(checked_list.configuration_warnings),
                            len(self.configuration_warnings))

            if not self.read_config_silent:
                try:
                    dump_list = sorted(checked_list, key=lambda k: k.get_name())
                except AttributeError:  # pragma: no cover, simple protection
                    dump_list = checked_list

                # Dump at DEBUG level because some tests break with INFO level, and it is not
                # really necessary to have information about each object ;
                for cur_obj in dump_list:
                    if strclss == 'services':
                        logger.debug('  %s', cur_obj.get_full_name())
                    else:
                        logger.debug('  %s', cur_obj.get_name())
                if checked_list:
                    logger.info('  checked %d', len(checked_list))
                else:
                    logger.info('  none')

        if not self.read_config_silent:
            logger.info('Checked')

        # Parse hosts and services for tags and realms
        hosts_tag = set()
        services_tag = set()
        for host in self.hosts:
            hosts_tag.add(host.poller_tag)
        for service in self.services:
            services_tag.add(service.poller_tag)

        # Check that for each poller_tag of a host, a poller exists with this tag
        pollers_tag = set()
        for poller in self.pollers:
            for tag in poller.poller_tags:
                pollers_tag.add(tag)

        if not hosts_tag.issubset(pollers_tag):
            for tag in hosts_tag.difference(pollers_tag):
                self.add_error("Error: some hosts have the poller_tag %s but no poller "
                               "has this tag" % tag)
                valid = False
        if not services_tag.issubset(pollers_tag):
            for tag in services_tag.difference(pollers_tag):
                self.add_error("some services have the poller_tag %s but no poller "
                               "has this tag" % tag)
                valid = False

        # Check that all hosts involved in business_rules are from the same realm
        for item in self.hosts:
            if not item.got_business_rule:
                continue

            realm = self.realms[item.realm]
            if not realm:
                # Something was wrong in the conf, will be raised elsewhere
                continue

            for elt_uuid in item.business_rule.list_all_elements():
                if elt_uuid not in self.hosts:
                    # An error or a service element
                    continue

                host = self.hosts[elt_uuid]
                if host.realm not in self.realms:
                    # Something was wrong in the conf, will be raised elsewhere
                    continue

                host_realm = self.realms[host.realm]
                if host_realm.get_name() != realm.get_name():
                    logger.error("Business_rule '%s' got some hosts from another realm: %s",
                                 item.get_full_name(), host_realm.get_name())
                    self.add_error("Error: Business_rule '%s' got hosts from another "
                                   "realm: %s" % (item.get_full_name(), host_realm.get_name()))
                    valid = False

        # for lst in [self.services, self.hosts]:
        #     for item in lst:
        #         if item.got_business_rule:
        #             e_ro = self.realms[item.realm]
        #             # Something was wrong in the conf, will be raised elsewhere
        #             if not e_ro:
        #                 continue
        #             e_r = e_ro.realm_name
        #             for elt_uuid in item.business_rule.list_all_elements():
        #                 if elt_uuid in self.hosts:
        #                     elt = self.hosts[elt_uuid]
        #                 else:
        #                     elt = self.services[elt_uuid]
        #                 r_o = self.realms[elt.realm]
        #                 # Something was wrong in the conf, will be raised elsewhere
        #                 if not r_o:
        #                     continue
        #                 elt_r = r_o.realm_name
        #                 if elt_r != e_r:
        #                     logger.error("Business_rule '%s' got hosts from another realm: %s",
        #                                  item.get_full_name(), elt_r)
        #                     self.add_error("Error: Business_rule '%s' got hosts from another "
        #                                    "realm: %s" % (item.get_full_name(), elt_r))
        #                     valid = False

        if self.configuration_errors:
            valid = False
            logger.error("Configuration errors:")
            for msg in self.configuration_errors:
                logger.error(msg)

        # If configuration error messages exist, then the configuration is not valid
        self.conf_is_correct = valid

    def explode_global_conf(self):
        """Explode parameters like cached_service_check_horizon in the
        Service class in a cached_check_horizon manner, o*hp commands etc

        :return: None
        """
        for cls, _, strclss, _, _ in list(self.types_creations.values()):
            logger.debug("Applying global conf for the class '%s'...", strclss)
            cls.load_global_conf(self)

    def remove_templates(self):
        """Clean useless elements like templates because they are not needed anymore

        :return: None
        """
        self.hosts.remove_templates()
        self.contacts.remove_templates()
        self.services.remove_templates()
        self.servicedependencies.remove_templates()
        self.hostdependencies.remove_templates()
        self.timeperiods.remove_templates()

    def show_errors(self):
        """
        Loop over configuration warnings and log them as INFO log
        Loop over configuration errors and log them as INFO log

        Note that the warnings and errors are logged on the fly during the configuration parsing.
        It is not necessary to log as WARNING and ERROR in this function which is used as a sum-up
        on the end of configuration parsing when an error has been detected.

        :return:  None
        """
        if self.configuration_warnings:
            logger.warning("Configuration warnings:")
            for msg in self.configuration_warnings:
                logger.warning(msg)
        if self.configuration_errors:
            logger.warning("Configuration errors:")
            for msg in self.configuration_errors:
                logger.warning(msg)

    def create_packs(self):
        # pylint: disable=too-many-statements,too-many-locals,too-many-branches, unused-argument
        """Create packs of hosts and services (all dependencies are resolved)
        It create a graph. All hosts are connected to their
        parents, and hosts without parent are connected to host 'root'.
        services are linked to their host. Dependencies between hosts/services are managed.
        REF: doc/pack-creation.png

        :return: None
        """
        logger.info("- creating hosts packs for the realms:")

        # We create a graph with host in nodes
        graph = Graph()
        graph.add_nodes(list(self.hosts.items.keys()))

        # links will be used for relations between hosts
        links = set()

        # Now the relations
        for host in self.hosts:
            # Add parent relations
            for parent in getattr(host, 'parents', []):
                if parent:
                    links.add((parent, host.uuid))
            # Add the others dependencies
            for (dep, _, _, _) in host.act_depend_of:
                links.add((dep, host.uuid))
            for (dep, _, _, _, _) in host.chk_depend_of:
                links.add((dep, host.uuid))

        # For services: they are linked with their own host but we need
        # to have the hosts of the service dependency in the same pack too
        for service in self.services:
            for (dep_id, _, _, _) in service.act_depend_of:
                if dep_id in self.services:
                    dep = self.services[dep_id]
                else:
                    dep = self.hosts[dep_id]
                # I don't care about dep host: they are just the host
                # of the service...
                if hasattr(dep, 'host'):
                    links.add((dep.host, service.host))
            # The other type of dep
            for (dep_id, _, _, _, _) in service.chk_depend_of:
                if dep_id in self.services:
                    dep = self.services[dep_id]
                else:
                    dep = self.hosts[dep_id]
                links.add((dep.host, service.host))

        # For host/service that are business based, we need to link them too
        for service in [srv for srv in self.services if srv.got_business_rule]:
            for elem_uuid in service.business_rule.list_all_elements():
                if elem_uuid in self.services:
                    elem = self.services[elem_uuid]
                    if elem.host != service.host:  # do not link a host with itself
                        links.add((elem.host, service.host))
                else:  # it's already a host but only if it is in the known hosts list!
                    if elem_uuid in self.hosts and elem_uuid != service.host:
                        links.add((elem_uuid, service.host))

        # Same for hosts of course
        for host in [hst for hst in self.hosts if hst.got_business_rule]:
            for elem_uuid in host.business_rule.list_all_elements():
                if elem_uuid in self.services:  # if it's a service
                    elem = self.services[elem_uuid]
                    if elem.host != host.uuid:
                        links.add((elem.host, host.uuid))
                else:  # e is a host
                    if elem_uuid != host.uuid:
                        links.add((elem_uuid, host.uuid))

        # Now we create links in the graph. With links (set)
        # We are sure to call the less add_edge
        for (dep, host) in links:
            graph.add_edge(dep, host)
            graph.add_edge(host, dep)

        # Now We find the default realm
        default_realm = self.realms.get_default()

        # Access_list from a node il all nodes that are connected
        # with it: it's a list of ours mini_packs
        # Now we look if all elements of all packs have the
        # same realm. If not, not good!
        for hosts_pack in graph.get_accessibility_packs():
            passively_checked_hosts = False
            actively_checked_hosts = False
            tmp_realms = set()
            logger.debug(" - host pack hosts:")
            for host_id in hosts_pack:
                host = self.hosts[host_id]
                logger.debug("  - %s", host.get_name())
                passively_checked_hosts = passively_checked_hosts or host.passive_checks_enabled
                actively_checked_hosts = actively_checked_hosts or host.active_checks_enabled
                if host.realm:
                    tmp_realms.add(host.realm)
            if len(tmp_realms) > 1:
                self.add_error("Error: the realm configuration of your hosts is not correct "
                               "because there is more than one realm in one pack (host relations):")
                for host_id in hosts_pack:
                    host = self.hosts[host_id]
                    if not host.realm:
                        self.add_error(' -> the host %s do not have a realm' % host.get_name())
                    else:
                        # Do not use get_name for the realm because it is not an object but a
                        # string containing the not found realm name if the realm is not existing!
                        # As of it, it may raise an exception
                        if host.realm not in self.realms:
                            self.add_error(' -> the host %s is in the realm %s' %
                                           (host.get_name(), host.realm))
                        else:
                            host_realm = self.realms[host.realm]
                            self.add_error(' -> the host %s is in the realm %s' %
                                           (host.get_name(), host_realm.get_name()))
            if len(tmp_realms) == 1:  # Ok, good
                tmp_realm = tmp_realms.pop()
                if tmp_realm in self.realms:
                    realm = self.realms[tmp_realm]
                else:
                    realm = self.realms.find_by_name(tmp_realm)
                if not realm:
                    self.add_error(' -> some hosts are in an unknown realm %s!' % tmp_realm)
                else:
                    # Set the current hosts pack to its realm
                    logger.debug(" - append pack %s to realm %s", hosts_pack, realm.get_name())
                    realm.packs.append(hosts_pack)
                    # Set if the realm only has passively or actively checked hosts...
                    realm.passively_checked_hosts = passively_checked_hosts
                    realm.actively_checked_hosts = actively_checked_hosts
            elif not tmp_realms:  # Hum... no realm value? So default Realm
                if default_realm is not None:
                    # Set the current hosts pack to the default realm
                    default_realm.packs.append(hosts_pack)
                else:
                    self.add_error("Error: some hosts do not have a realm and you did not "
                                   "defined a default realm!")
                    for host in hosts_pack:
                        self.add_error('    Impacted host: %s ' % host.get_name())

        # The load balancing is for a loop, so all
        # hosts of a realm (in a pack) will be dispatched
        # to the schedulers of this realm
        # REF: doc/pack-aggregation.png

        # Count the numbers of elements in all the realms,
        # to compare with the total number of hosts
        nb_elements_all_realms = 0
        for realm in self.realms:
            packs = {}
            # create round-robin iterator for id of cfg
            # So dispatching is load balanced in a realm
            # but add a entry in the round-robin tourniquet for
            # every weight point schedulers (so Weight round robin)
            weight_list = []
            no_spare_schedulers = realm.schedulers
            if not no_spare_schedulers:
                if realm.potential_schedulers:
                    no_spare_schedulers = [realm.potential_schedulers[0]]
            nb_schedulers = len(no_spare_schedulers)
            if nb_schedulers:
                logger.info("  %d scheduler(s) for the realm %s", nb_schedulers, realm.get_name())
            else:
                logger.warning("  no scheduler for the realm %s", realm.get_name())

            # Maybe there is no scheduler in the realm, it can be a
            # big problem if there are elements in packs
            nb_elements = 0
            for hosts_pack in realm.packs:
                nb_elements += len(hosts_pack)
                nb_elements_all_realms += len(hosts_pack)
            realm.hosts_count = nb_elements
            if nb_elements:
                if not nb_schedulers:
                    self.add_error("The realm %s has %d hosts but no scheduler!"
                                   % (realm.get_name(), nb_elements))
                    realm.packs = []  # Dumb pack
                    continue

                logger.info("  %d hosts in the realm %s, distributed in %d linked packs",
                            nb_elements, realm.get_name(), len(realm.packs))
            else:
                logger.info("  no hosts in the realm %s", realm.get_name())

            # Create a relation between a pack and each scheduler in the realm
            packindex = 0
            packindices = {}
            for s_id in no_spare_schedulers:
                scheduler = self.schedulers[s_id]
                logger.debug("  scheduler: %s", scheduler.instance_id)
                packindices[s_id] = packindex
                packindex += 1
                for i in range(0, scheduler.weight):
                    weight_list.append(s_id)
            logger.debug("  pack indices: %s", packindices)
            # packindices is indexed with the scheduler id and contains
            # the configuration part number to get used: sched1:0, sched2: 1, ...

            round_robin = itertools.cycle(weight_list)

            # We must initialize nb_schedulers packs
            for i in range(0, nb_schedulers):
                packs[i] = []

            # Try to load the history association dict so we will try to
            # send the hosts in the same "pack"
            assoc = {}

            # Now we explode the numerous packs into reals packs:
            # we 'load balance' them in a round-robin way but with count number of hosts in
            # case have some packs with too many hosts and other with few
            realm.packs.sort(reverse=True)
            pack_higher_hosts = 0
            for hosts_pack in realm.packs:
                valid_value = False
                old_pack = -1
                for host_id in hosts_pack:
                    host = self.hosts[host_id]
                    old_i = assoc.get(host.get_name(), -1)
                    # Maybe it's a new, if so, don't count it
                    if old_i == -1:
                        continue
                    # Maybe it is the first we look at, if so, take it's value
                    if old_pack == -1 and old_i != -1:
                        old_pack = old_i
                        valid_value = True
                        continue
                    if old_i == old_pack:
                        valid_value = True
                    if old_i != old_pack:
                        valid_value = False
                # If it's a valid sub pack and the pack id really exist, use it!
                if valid_value and old_pack in packindices:
                    i = old_pack
                else:
                    if isinstance(i, int):
                        i = next(round_robin)
                    elif (len(packs[packindices[i]]) + len(hosts_pack)) >= pack_higher_hosts:
                        pack_higher_hosts = (len(packs[packindices[i]]) + len(hosts_pack))
                        i = next(round_robin)

                for host_id in hosts_pack:
                    host = self.hosts[host_id]
                    packs[packindices[i]].append(host_id)
                    assoc[host.get_name()] = i

            # Now packs is a dictionary indexed with the configuration part
            # number and containing the list of hosts
            realm.packs = packs

        logger.info("  total number of hosts in all realms: %d", nb_elements_all_realms)
        if len(self.hosts) != nb_elements_all_realms:
            logger.warning("There are %d hosts defined, and %d hosts dispatched in the realms. "
                           "Some hosts have been ignored", len(self.hosts), nb_elements_all_realms)
            self.add_error("There are %d hosts defined, and %d hosts dispatched in the realms. "
                           "Some hosts have been "
                           "ignored" % (len(self.hosts), nb_elements_all_realms))

    def cut_into_parts(self):
        # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        """Cut conf into part for scheduler dispatch.

        Basically it provides a set of host/services for each scheduler that
        have no dependencies between them

        :return: None
        """
        # User must have set a spare if he needed one
        logger.info("Splitting the configuration into parts:")
        nb_parts = 0
        for realm in self.realms:
            no_spare_schedulers = realm.schedulers
            if not no_spare_schedulers:
                if realm.potential_schedulers:
                    no_spare_schedulers = [realm.potential_schedulers[0]]
            nb_schedulers = len(no_spare_schedulers)
            nb_parts += nb_schedulers
            if nb_schedulers:
                logger.info("  %d scheduler(s) for the realm %s", nb_schedulers, realm.get_name())
            else:
                logger.warning("  no scheduler for the realm %s", realm.get_name())

        if nb_parts == 0:
            nb_parts = 1

        # We create dummy configurations for schedulers:
        # they are clone of the master configuration but without hosts and
        # services (because they are splitted between these configurations)
        logger.info("Splitting the configuration into %d parts...", nb_parts)
        self.parts = {}
        for part_index in range(0, nb_parts):
            self.parts[part_index] = Config()

            # Now we copy all properties of conf into the new ones
            for prop, entry in sorted(list(Config.properties.items())):
                # Do not copy the configuration instance id nor name!
                if prop in ['instance_id', 'config_name']:
                    continue
                # Only the one that are managed and used
                if entry.managed and not isinstance(entry, UnusedProp):
                    val = getattr(self, prop, None)
                    setattr(self.parts[part_index], prop, val)

            # Set the cloned configuration name
            self.parts[part_index].config_name = "%s (%d)" % (self.config_name, part_index)
            logger.debug("- cloning configuration: %s -> %s",
                         self.parts[part_index].config_name, self.parts[part_index])

            # Copy the configuration objects lists. We need a deepcopy because each configuration
            # will have some new groups... but we create a new uuid
            self.parts[part_index].uuid = get_a_new_object_id()

            types_creations = self.__class__.types_creations
            for o_type in types_creations:
                (_, clss, inner_property, _, clonable) = types_creations[o_type]
                if not clonable:
                    logger.debug("  . do not clone: %s", inner_property)
                    continue
                # todo: Indeed contactgroups should be managed like hostgroups...
                if inner_property in ['hostgroups', 'servicegroups']:
                    new_groups = []
                    for group in getattr(self, inner_property):
                        new_groups.append(group.copy_shell())
                    setattr(self.parts[part_index], inner_property, clss(new_groups))
                elif inner_property in ['hosts', 'services']:
                    setattr(self.parts[part_index], inner_property, clss([]))
                else:
                    setattr(self.parts[part_index], inner_property, getattr(self, inner_property))
                logger.debug("  . cloned %s: %s -> %s", inner_property,
                             getattr(self, inner_property),
                             getattr(self.parts[part_index], inner_property))

            # The elements of the others conf will be tag here
            self.parts[part_index].other_elements = {}

            # No scheduler has yet accepted the configuration
            self.parts[part_index].is_assigned = False
            self.parts[part_index].scheduler_link = None
            self.parts[part_index].push_flavor = ''
        # Once parts got created, the current configuration has some 'parts'
        # self.parts is the configuration split into parts for the schedulers

        # Just create packs. There can be numerous ones
        # In pack we've got hosts and service and packs are in the realms
        logger.debug("Creating packs for realms...")
        self.create_packs()
        # Once packs got created, all the realms have some 'packs'

        logger.info("Realms:")
        for realm in self.realms:
            logger.info(" - realm: %s", realm)
            for idx in realm.packs:
                logger.info("   - pack: %s / %d hosts (%s)",
                            idx, len(realm.packs[idx]), ','.join([self.hosts[host_id].get_name()
                                                                  for host_id in realm.packs[idx]]))

        # We have packs for realms and elements into configurations, let's merge this...
        logger.info("Realms:")
        offset = 0
        for realm in self.realms:
            logger.info(" Realm: %s", realm)
            for idx in realm.packs:
                logger.info(" - pack: %s / %d hosts", idx, len(realm.packs[idx]))
                if not realm.packs[idx]:
                    logger.info(" - no hosts are declared in this realm pack.")
                    # continue
                try:
                    instance_id = self.parts[idx + offset].instance_id
                    for host_id in realm.packs[idx]:
                        host = self.hosts[host_id]
                        self.parts[idx + offset].hosts.add_item(host)
                        for service_id in host.services:
                            service = self.services[service_id]
                            self.parts[idx + offset].services.add_item(service)
                    # Now the conf can be linked with the realm
                    realm.parts.update({instance_id: self.parts[idx + offset]})
                    # offset += 1
                except KeyError:
                    logger.info(" - no configuration part is affected "
                                "because of mismatching hosts packs / schedulers count. "
                                "Probably too much schedulers for the hosts count!")

            offset += len(realm.packs)
            del realm.packs

        # We've nearly have hosts and services. Now we want real hosts (Class)
        # And we want groups too
        for part_index in self.parts:
            cfg = self.parts[part_index]

            # Fill host groups
            for ori_hg in self.hostgroups:
                hostgroup = cfg.hostgroups.find_by_name(ori_hg.get_name())
                mbrs_id = []
                for host in ori_hg.members:
                    if host != '':
                        mbrs_id.append(host)
                for host in cfg.hosts:
                    if host.uuid in mbrs_id:
                        hostgroup.members.append(host.uuid)

            # And also relink the hosts with the valid hostgroups
            for host in cfg.hosts:
                orig_hgs = host.hostgroups
                nhgs = []
                for ohg_id in orig_hgs:
                    ohg = self.hostgroups[ohg_id]
                    nhg = cfg.hostgroups.find_by_name(ohg.get_name())
                    nhgs.append(nhg.uuid)
                host.hostgroups = nhgs

            # Fill servicegroup
            for ori_sg in self.servicegroups:
                servicegroup = cfg.servicegroups.find_by_name(ori_sg.get_name())
                mbrs = ori_sg.members
                mbrs_id = []
                for service in mbrs:
                    if service != '':
                        mbrs_id.append(service)
                for service in cfg.services:
                    if service.uuid in mbrs_id:
                        servicegroup.members.append(service.uuid)

            # And also relink the services with the valid servicegroups
            for host in cfg.services:
                orig_hgs = host.servicegroups
                nhgs = []
                for ohg_id in orig_hgs:
                    ohg = self.servicegroups[ohg_id]
                    nhg = cfg.servicegroups.find_by_name(ohg.get_name())
                    nhgs.append(nhg.uuid)
                host.servicegroups = nhgs

        # Now we fill other_elements by host (service are with their host
        # so they are not tagged)
        logger.info("Configuration parts:")
        for part_index in self.parts:
            for host in self.parts[part_index].hosts:
                for j in [j for j in self.parts if j != part_index]:  # So other than i
                    self.parts[part_index].other_elements[host.get_name()] = part_index
            logger.info("- part: %d - %s, %d hosts", part_index, self.parts[part_index],
                        len(self.parts[part_index].hosts))

    def prepare_for_sending(self):
        """The configuration needs to be serialized before being sent to a spare arbiter

        :return: None
        """
        if [arbiter_link for arbiter_link in self.arbiters if arbiter_link.spare]:
            logger.info('Serializing the configuration for my spare arbiter...')

            # Now serialize the whole configuration, for sending to spare arbiters
            self.spare_arbiter_conf = serialize(self)

    def dump(self, dump_file_name=None):
        """Dump configuration to a file in a JSON format

        :param dump_file_name: the file to dump configuration to
        :type dump_file_name: str
        :return: None
        """
        config_dump = {}

        for _, _, category, _, _ in list(self.types_creations.values()):
            try:
                objs = [jsonify_r(i) for i in getattr(self, category)]
            except (TypeError, AttributeError):  # pragma: no cover, simple protection
                logger.warning("Dumping configuration, '%s' not present in the configuration",
                               category)
                continue

            container = getattr(self, category)
            if category == "services":
                objs = sorted(objs,
                              key=lambda o: "%s/%s" % (o["host_name"], o["service_description"]))
            elif hasattr(container, "name_property"):
                name_prop = container.name_property
                objs = sorted(objs, key=lambda o, prop=name_prop: getattr(o, prop, ''))
            config_dump[category] = objs

        if not dump_file_name:
            dump_file_name = os.path.join(tempfile.gettempdir(),
                                          'alignak-%s-cfg-dump-%d.json'
                                          % (self.name, int(time.time())))
        try:
            logger.info('Dumping configuration to: %s', dump_file_name)
            fd = open(dump_file_name, "w")
            fd.write(json.dumps(config_dump, indent=4, separators=(',', ': '), sort_keys=True))
            fd.close()
            logger.info('Dumped')
        except (OSError, IndexError) as exp:  # pragma: no cover, should never happen...
            logger.critical("Error when dumping configuration to %s: %s", dump_file_name, str(exp))
