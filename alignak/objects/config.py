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

""" Config is the class to read, load and manipulate the user
 configuration. It read a main cfg (alignak.cfg) and get all informations
 from it. It create objects, make link between them, clean them, and cut
 them into independent parts. The main user of this is Arbiter, but schedulers
 use it too (but far less)"""
# pylint: disable=C0302
import re
import sys
import string
import os
import socket
import itertools
import time
import random
import tempfile
import uuid
import logging
from StringIO import StringIO
from multiprocessing import Process, Manager
import json

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
from alignak.objects.trigger import Trigger, Triggers
from alignak.objects.pack import Packs
from alignak.util import split_semicolon, sort_by_number_values
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


logger = logging.getLogger(__name__)  # pylint: disable=C0103

NO_LONGER_USED = ('This parameter is not longer take from the main file, but must be defined '
                  'in the status_dat broker module instead. But Alignak will create you one '
                  'if there are no present and use this parameter in it, so no worry.')
NOT_INTERESTING = 'We do not think such an option is interesting to manage.'
NOT_MANAGED = ('This Nagios legacy parameter is not managed by Alignak. Ignoring...')


class Config(Item):  # pylint: disable=R0904,R0902
    """Config is the class to read, load and manipulate the user
 configuration. It read a main cfg (alignak.cfg) and get all information
 from it. It create objects, make link between them, clean them, and cut
 them into independent parts. The main user of this is Arbiter, but schedulers
 use it too (but far less)

    """
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
    properties = {
        'program_start':
            IntegerProp(default=0),
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

        'passive_host_checks_enabled':
            BoolProp(default=True),
        'passive_service_checks_enabled':
            BoolProp(default=True),
        'active_host_checks_enabled':
            BoolProp(default=True),
        'active_service_checks_enabled':
            BoolProp(default=True),
        'event_handlers_enabled':
            BoolProp(default=True),
        'flap_detection_enabled':
            BoolProp(default=True),
        'notifications_enabled':
            BoolProp(default=True),
        'daemon_mode':
            BoolProp(default=True),
        # 'instance_name':
        #     StringProp(default=''),
        'instance_id':
            StringProp(default=''),
        'name':
            StringProp(default='Main configuration'),

        # Used for the PREFIX macro
        # Alignak prefix does not exist as for Nagios meaning.
        # It is better to set this value as an empty string rather than a meaningless information!
        'prefix':
            UnusedProp(text=NOT_MANAGED),

        # Used for the ALIGNAK macro
        # Alignak instance name is set as the arbiter name
        # if it is not defined in the configuration file
        'alignak_name':
            StringProp(default=''),

        # Used for the MAINCONFIGFILE macro
        'main_config_file':
            StringProp(default='/usr/local/etc/alignak/alignak.ini'),

        'config_base_dir':
            StringProp(default=''),  # will be set when we will load a file

        # Triggers directory
        'triggers_dir':
            StringProp(default=''),

        # Packs directory
        'packs_dir':
            StringProp(default=''),

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
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None), (Contact, None)]),

        # Service checks
        'execute_service_checks':
            BoolProp(default=True, class_inherit=[(Service, 'execute_checks')]),

        'accept_passive_service_checks':
            BoolProp(default=True, class_inherit=[(Service, 'accept_passive_checks')]),

        # Host checks
        'execute_host_checks':
            BoolProp(default=True, class_inherit=[(Host, 'execute_checks')]),

        'accept_passive_host_checks':
            BoolProp(default=True, class_inherit=[(Host, 'accept_passive_checks')]),

        # Enable event handlers
        'enable_event_handlers':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

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
            UnusedProp(text='another value than look always the file is useless, so we fix it.'),
        'command_file':
            StringProp(default=''),
        'external_command_buffer_slots':
            UnusedProp(text='We do not limit the external command slot.'),

        # Application updates checks
        'check_for_updates':
            UnusedProp(text='network administrators will never allow such communication between '
                            'server and the external world. Use your distribution packet manager '
                            'to know if updates are available or go to the '
                            'http://www.github.com/Alignak-monitoring/alignak website instead.'),

        'bare_update_checks':
            UnusedProp(text=None),

        # Inner status.dat self created module parameters
        'retain_state_information':
            UnusedProp(text='sorry, retain state information will not be implemented '
                            'because it is useless.'),

        'state_retention_file':
            StringProp(default=''),

        'retention_update_interval':
            IntegerProp(default=60),

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

        # Inner syslog self created module parameters
        'use_syslog':
            BoolProp(default=False),

        # Monitoring logs configuration
        'log_notifications':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

        'log_service_retries':
            BoolProp(default=True, class_inherit=[(Service, 'log_retries')]),

        'log_host_retries':
            BoolProp(default=True, class_inherit=[(Host, 'log_retries')]),

        'log_event_handlers':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

        'log_snapshots':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

        'log_flappings':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

        'log_initial_states':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

        'log_external_commands':
            BoolProp(default=True),

        'log_passive_checks':
            BoolProp(default=False),

        'log_active_checks':
            BoolProp(default=False),

        # Event handlers
        'global_host_event_handler':
            StringProp(default='', class_inherit=[(Host, 'global_event_handler')]),

        'global_service_event_handler':
            StringProp(default='', class_inherit=[(Service, 'global_event_handler')]),

        'sleep_time':
            UnusedProp(text='this deprecated option is useless in the alignak way of doing.'),

        'service_inter_check_delay_method':
            UnusedProp(text='This option is useless in the Alignak scheduling. '
                            'The only way is the smart way.'),

        'max_service_check_spread':
            IntegerProp(default=30, class_inherit=[(Service, 'max_check_spread')]),

        'service_interleave_factor':
            UnusedProp(text='This option is useless in the Alignak scheduling '
                            'because it use a random distribution for initial checks.'),

        'max_concurrent_checks':
            UnusedProp(text='Limiting the max concurrent checks is not helpful '
                            'to got a good running monitoring server.'),

        'check_result_reaper_frequency':
            UnusedProp(text='Alignak do not use reaper process.'),

        'max_check_result_reaper_time':
            UnusedProp(text='Alignak do not use reaper process.'),

        'check_result_path':
            UnusedProp(text='Alignak use in memory returns, not check results on flat file.'),

        'max_check_result_file_age':
            UnusedProp(text='Alignak do not use flat file check resultfiles.'),

        'host_inter_check_delay_method':
            UnusedProp(text='This option is unused in the Alignak scheduling because distribution '
                            'of the initial check is a random one.'),

        'max_host_check_spread':
            IntegerProp(default=30, class_inherit=[(Host, 'max_check_spread')]),

        'interval_length':
            IntegerProp(default=60, class_inherit=[(Host, None), (Service, None)]),

        'auto_reschedule_checks':
            BoolProp(managed=False, default=True),

        'auto_rescheduling_interval':
            IntegerProp(managed=False, default=1),

        'auto_rescheduling_window':
            IntegerProp(managed=False, default=180),

        'translate_passive_host_checks':
            UnusedProp(text='Alignak passive checks management makes this parameter unuseful.'),
            # BoolProp(managed=False, default=True),

        'passive_host_checks_are_soft':
            UnusedProp(text='Alignak passive checks management makes this parameter unuseful.'),
            # BoolProp(managed=False, default=True),

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
            UnusedProp(text='this option is deprecated because in alignak it is just an alias '
                            'for enable_environment_macros=False'),

        'free_child_process_memory':
            UnusedProp(text='this option is automatic in Python processes'),

        'child_processes_fork_twice':
            UnusedProp(text='fork twice is not used.'),

        'enable_environment_macros':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

        # Flapping management
        'enable_flap_detection':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

        'low_service_flap_threshold':
            IntegerProp(default=20, class_inherit=[(Service, 'global_low_flap_threshold')]),

        'high_service_flap_threshold':
            IntegerProp(default=30, class_inherit=[(Service, 'global_high_flap_threshold')]),

        'low_host_flap_threshold':
            IntegerProp(default=20, class_inherit=[(Host, 'global_low_flap_threshold')]),

        'high_host_flap_threshold':
            IntegerProp(default=30, class_inherit=[(Host, 'global_high_flap_threshold')]),

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
            StringProp(default='', class_inherit=[(Host, 'perfdata_file')]),

        'service_perfdata_file':
            StringProp(default='', class_inherit=[(Service, 'perfdata_file')]),

        'host_perfdata_file_template':
            StringProp(default='/tmp/host.perf', class_inherit=[(Host, 'perfdata_file_template')]),

        'service_perfdata_file_template':
            StringProp(default='/tmp/host.perf',
                       class_inherit=[(Service, 'perfdata_file_template')]),

        'host_perfdata_file_mode':
            CharProp(default='a', class_inherit=[(Host, 'perfdata_file_mode')]),

        'service_perfdata_file_mode':
            CharProp(default='a', class_inherit=[(Service, 'perfdata_file_mode')]),

        'host_perfdata_file_processing_interval':
            IntegerProp(managed=False, default=15),

        'service_perfdata_file_processing_interval':
            IntegerProp(managed=False, default=15),

        'host_perfdata_file_processing_command':
            StringProp(managed=False,
                       default='',
                       class_inherit=[(Host, 'perfdata_file_processing_command')]),

        'service_perfdata_file_processing_command':
            StringProp(managed=False, default=None),

        # Hosts/services orphanage check
        'check_for_orphaned_services':
            BoolProp(default=True, class_inherit=[(Service, 'check_for_orphaned')]),

        'check_for_orphaned_hosts':
            BoolProp(default=True, class_inherit=[(Host, 'check_for_orphaned')]),

        # Freshness checks
        'check_service_freshness':
            BoolProp(default=True, class_inherit=[(Service, 'global_check_freshness')]),

        'service_freshness_check_interval':
            IntegerProp(default=3600),

        'check_host_freshness':
            BoolProp(default=True, class_inherit=[(Host, 'global_check_freshness')]),

        'host_freshness_check_interval':
            IntegerProp(default=3600),

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

        'use_regexp_matching':
            BoolProp(managed=False,
                     default=False,
                     _help='If you got some host or service definition like prod*, '
                           'it will surely failed from now, sorry.'),
        'use_true_regexp_matching':
            BoolProp(managed=False, default=None),

        'admin_email':
            UnusedProp(text='sorry, not yet implemented.'),

        'admin_pager':
            UnusedProp(text='sorry, not yet implemented.'),

        'event_broker_options':
            UnusedProp(text='event broker are replaced by modules '
                            'with a real configuration template.'),
        'broker_module':
            StringProp(default=''),

        # Debug
        'debug_file':
            UnusedProp(text=None),

        'debug_level':
            UnusedProp(text=None),

        'debug_verbosity':
            UnusedProp(text=None),

        'max_debug_file_size':
            UnusedProp(text=None),

        'modified_attributes':
            IntegerProp(default=0L),

        'daemon_thread_pool_size':
            IntegerProp(default=8),

        'max_plugins_output_length':
            IntegerProp(default=8192, class_inherit=[(Host, None), (Service, None)]),

        'no_event_handlers_during_downtimes':
            BoolProp(default=False, class_inherit=[(Host, None), (Service, None)]),

        # Interval between cleaning queues pass
        'cleaning_queues_interval':
            IntegerProp(default=900),

        # Now for problem/impact states changes
        'enable_problem_impacts_states_change':
            BoolProp(default=False, class_inherit=[(Host, None), (Service, None)]),

        # More a running value in fact
        'resource_macros_names':
            ListProp(default=[]),

        'runners_timeout':
            IntegerProp(default=3600),

        # Self created daemons
        'daemons_log_folder':
            StringProp(default='/usr/local/var/log/alignak'),

        'daemons_initial_port':
            IntegerProp(default=7800),

        # # Local statsd daemon for collecting Alignak internal statistics
        # 'statsd_host':
        #     StringProp(default='localhost',
        #                class_inherit=[(SchedulerLink, None), (ReactionnerLink, None),
        #                               (BrokerLink, None), (PollerLink, None),
        #                               (ReceiverLink, None), (ArbiterLink, None)]),
        # 'statsd_port':
        #     IntegerProp(default=8125,
        #                 class_inherit=[(SchedulerLink, None), (ReactionnerLink, None),
        #                                (BrokerLink, None), (PollerLink, None),
        #                                (ReceiverLink, None), (ArbiterLink, None)]),
        # 'statsd_prefix': StringProp(default='alignak',
        #                             class_inherit=[(SchedulerLink, None), (ReactionnerLink, None),
        #                                            (BrokerLink, None), (PollerLink, None),
        #                                            (ReceiverLink, None), (ArbiterLink, None)]),
        # 'statsd_enabled': BoolProp(default=False,
        #                            class_inherit=[(SchedulerLink, None), (ReactionnerLink, None),
        #                                           (BrokerLink, None), (PollerLink, None),
        #                                           (ReceiverLink, None), (ArbiterLink, None)]),
    }

    macros = {
        'PREFIX':               '',
        'ALIGNAK':              'alignak_name',
        'MAINCONFIGFILE':       'main_config_file',
        'STATUSDATAFILE':       '',
        'COMMENTDATAFILE':      '',
        'DOWNTIMEDATAFILE':     '',
        'RETENTIONDATAFILE':    '',
        'OBJECTCACHEFILE':      '',
        'TEMPFILE':             '',
        'TEMPPATH':             '',
        'LOGFILE':              '',
        'RESOURCEFILE':         '',
        'COMMANDFILE':          'command_file',
        'HOSTPERFDATAFILE':     '',
        'SERVICEPERFDATAFILE':  '',
        'ADMINEMAIL':           '',
        'ADMINPAGER':           ''
        # 'USERn': '$USERn$' # Add at run time
    }

    # We create dict of objects
    # Dictionary: objects type: {Class of object, Class of objects list,
    # 'name of the Config property for the objects', True to create an intial index,
    # True if the property is clonable
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
        'trigger':
            (Trigger, Triggers, 'triggers', True, True),
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

        # if 'name' not in params:
        #     params['name'] = 'Main configuration'
        #
        # At deserialization, those are dictionaries
        # TODO: Separate parsing instance from recreated ones
        for prop in ['host_perfdata_command', 'service_perfdata_command',
                     'global_host_event_handler', 'global_service_event_handler']:
            if prop in params and isinstance(params[prop], dict):
                # We recreate the object
                setattr(self, prop, CommandCall(params[prop], parsing=parsing))
                # And remove prop, to prevent from being overridden
                del params[prop]

        for _, clss, strclss, _, _ in self.types_creations.values():
            if strclss in params and isinstance(params[strclss], dict):
                setattr(self, strclss, clss(params[strclss], parsing=parsing))
                del params[strclss]

        # for clss, prop in [(Triggers, 'triggers'), (Packs, 'packs')]:
        for clss, prop in [(Packs, 'packs')]:
            if prop in params and isinstance(params[prop], dict):
                setattr(self, prop, clss(params[prop], parsing=parsing))
                del params[prop]
            else:
                setattr(self, prop, clss({}))

        super(Config, self).__init__(params, parsing=parsing)
        self.params = {}
        self.resource_macros_names = []
        # By default the conf is correct and the warnings and errors lists are empty
        self.conf_is_correct = True
        self.configuration_warnings = []
        self.configuration_errors = []
        # We tag the conf with a magic_hash, a random value to
        # identify this conf
        random.seed(time.time())
        self.magic_hash = random.randint(1, 100000)
        self.triggers_dirs = []
        self.packs_dirs = []

        # Store daemons detected as missing during the configuration check
        self.missing_daemons = []

    def serialize(self):
        res = super(Config, self).serialize()
        # if hasattr(self, 'instance_id'):
        #     res['instance_id'] = self.instance_id
        # The following are not in properties so not in the dict
        for prop in ['triggers', 'packs', 'hosts',
                     'services', 'hostgroups', 'notificationways',
                     'checkmodulations', 'macromodulations', 'businessimpactmodulations',
                     'resultmodulations', 'contacts', 'contactgroups',
                     'servicegroups', 'timeperiods', 'commands',
                     'escalations',
                     'host_perfdata_command', 'service_perfdata_command',
                     'global_host_event_handler', 'global_service_event_handler']:
            if getattr(self, prop) in [None, 'None']:
                res[prop] = None
            else:
                res[prop] = getattr(self, prop).serialize()
        res['macros'] = self.macros
        return res

    def fill_resource_macros_names_macros(self):
        """ fill the macro dict will all value
        from self.resource_macros_names

        :return: None
        """
        properties = self.__class__.properties
        macros = self.__class__.macros
        for macro_name in self.resource_macros_names:
            properties['$' + macro_name + '$'] = StringProp(default='')
            macros[macro_name] = '$' + macro_name + '$'

    def clean_params(self, params):
        """Convert a list of parameters (key=value) into a dict

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
            elif elts[1] == '':
                self.add_error("the parameter %s is malformed! (no value after =)" % elts[0])
            else:
                clean_p[elts[0]] = elts[1]

        return clean_p

    def load_params(self, params):
        """Load parameters from main configuration file

        :param params: parameters list (converted right at the beginning)
        :type params:
        :return: None
        """
        clean_params = self.clean_params(params)

        logger.info("Alignak parameters:")
        for key, value in sorted(clean_params.items()):
            if key in self.properties:
                val = self.properties[key].pythonize(clean_params[key])
            elif key in self.running_properties:
                logger.warning("using a the running property %s in a config file", key)
                val = self.running_properties[key].pythonize(clean_params[key])
            elif key.startswith('$') or key in ['cfg_file', 'cfg_dir']:
                # it's a macro or a useless now param, we don't touch this
                val = value
            else:
                logger.debug("Guessing the property '%s' type because it "
                             "is not in %s object properties", key, self.__class__.__name__)
                val = ToGuessProp.pythonize(clean_params[key])

            setattr(self, key, val)
            logger.info("- %s = %s", key, val)
            # Maybe it's a variable as $USER$ or $ANOTHERVATRIABLE$
            # so look at the first character. If it's a $, it's a variable
            # and if it's end like it too
            if key[0] == '$' and key[-1] == '$':
                macro_name = key[1:-1]
                self.resource_macros_names.append(macro_name)

        # Change Nagios2 names to Nagios3 ones (before using them)
        self.old_properties_names_to_new()

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

    def read_config(self, files):  # pylint: disable=R0912
        """Read and parse main configuration files
        (specified with -c option to the Arbiter)
        and put them into a StringIO object

        :param files: list of file to read
        :type files: list
        :return: a buffer containing all files
        :rtype: str
        """
        # just a first pass to get the cfg_file and all files in a buf
        res = StringIO()

        if not self.read_config_silent:
            logger.info("Reading the configuration files...")
        for c_file in files:
            # We add a \n (or \r\n) to be sure config files are separated
            # if the previous does not finish with a line return
            res.write(os.linesep)
            res.write('# IMPORTEDFROM=%s' % (c_file) + os.linesep)
            if not self.read_config_silent:
                logger.info("- opening '%s' configuration file", c_file)
            try:
                # Open in Universal way for Windows, Mac, Linux-based systems
                file_d = open(c_file, 'rU')
                buf = file_d.readlines()
                file_d.close()
                # Update macro used properties
                self.config_base_dir = os.path.dirname(c_file)
                self.main_config_file = os.path.abspath(c_file)
            except IOError, exp:
                self.add_error("cannot open main file '%s' for reading: %s"
                               % (c_file, exp))
                continue

            for line in buf:
                line = line.decode('utf8', 'replace')
                res.write(line)
                if line.endswith('\n'):
                    line = line[:-1]
                line = line.strip()
                if re.search("^cfg_file", line) or re.search("^resource_file", line):
                    elts = line.split('=', 1)
                    if os.path.isabs(elts[1]):
                        cfg_file_name = elts[1]
                    else:
                        cfg_file_name = os.path.join(self.config_base_dir, elts[1])
                    cfg_file_name = cfg_file_name.strip()
                    try:
                        file_d = open(cfg_file_name, 'rU')
                        if not self.read_config_silent:
                            logger.info("- reading file '%s'", cfg_file_name)
                        res.write(os.linesep + '# IMPORTEDFROM=%s' % (cfg_file_name) + os.linesep)
                        res.write(file_d.read().decode('utf8', 'replace'))
                        # Be sure to add a line return so we won't mix files
                        res.write(os.linesep)
                        file_d.close()
                    except IOError, exp:
                        self.add_error("cannot open file '%s' for reading: %s"
                                       % (cfg_file_name, exp))
                elif re.search("^cfg_dir", line):
                    elts = line.split('=', 1)
                    if os.path.isabs(elts[1]):
                        cfg_dir_name = elts[1]
                    else:
                        cfg_dir_name = os.path.join(self.config_base_dir, elts[1])
                    # Ok, look if it's really a directory
                    if not os.path.isdir(cfg_dir_name):
                        self.add_error("cannot open directory '%s' for reading" %
                                       (cfg_dir_name))

                    # I will look later for .pack file into this directory :)
                    self.packs_dirs.append(cfg_dir_name)

                    # Now walk for it.
                    for root, _, walk_files in os.walk(cfg_dir_name, followlinks=True):
                        for found_file in walk_files:
                            if not re.search(r"\.cfg$", found_file):
                                continue
                            if not self.read_config_silent:
                                logger.info("  reading: %s", os.path.join(root, found_file))
                            try:
                                # Track the importation source
                                res.write(os.linesep + '# IMPORTEDFROM=%s' %
                                          (os.path.join(root, found_file)) + os.linesep)
                                # Read the file content to the buffer
                                file_d = open(os.path.join(root, found_file), 'rU')
                                res.write(file_d.read().decode('utf8', 'replace'))
                                # Be sure to separate files data
                                res.write(os.linesep)
                                file_d.close()
                            except IOError as exp:  # pragma: no cover, simple protection
                                self.add_error("cannot open file '%s' for reading: %s"
                                               % (os.path.join(root, c_file), exp))
                elif re.search("^triggers_dir", line):
                    elts = line.split('=', 1)
                    if os.path.isabs(elts[1]):
                        trig_dir_name = elts[1]
                    else:
                        trig_dir_name = os.path.join(self.config_base_dir, elts[1])
                    # Ok, look if it's really a directory
                    if not os.path.isdir(trig_dir_name):
                        self.add_error("cannot open triggers directory '%s' for reading"
                                       % (trig_dir_name))
                        continue
                    # Ok it's a valid one, I keep it
                    self.triggers_dirs.append(trig_dir_name)

        config = res.getvalue()
        res.close()
        return config

    def read_config_buf(self, buf):  # pylint: disable=R0912
        """The config buffer (previously returned by Config.read_config())

        :param buf: buffer containing all data from config files
        :type buf: str
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
        if not self.read_config_silent:
            logger.info("Parsing the configuration files...")
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
        lines = buf.split('\n')
        line_nb = 0  # Keep the line number for the file path
        filefrom = ''
        for line in lines:
            if line.startswith("# IMPORTEDFROM="):
                filefrom = line.split('=')[1]
                line_nb = 0  # reset the line number too
                continue

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

        # todo: this looks unuseful...
        # Maybe the type of the last element is unknown, declare it
        if tmp_type not in objectscfg:
            objectscfg[tmp_type] = []

        objectscfg[tmp_type].append(tmp)
        objects = {}

        self.load_params(params)
        # And then update our MACRO dict
        self.fill_resource_macros_names_macros()

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
                    objects[o_type].append(tmp_obj)

        return objects

    @staticmethod
    def add_ghost_objects(raw_objects):
        """Add fake command objects for internal processing ; bp_rule, _internal_host_up, _echo

        :param raw_objects: Raw config objects dict
        :type raw_objects: dict
        :return: raw_objects with 3 extras commands
        :rtype: dict
        """
        bp_rule = {
            'command_name': 'bp_rule',
            'command_line': 'bp_rule',
            'imported_from': 'alignak-self'
        }
        raw_objects['command'].append(bp_rule)
        host_up = {
            'command_name': '_internal_host_up',
            'command_line': '_internal_host_up',
            'imported_from': 'alignak-self'
        }
        raw_objects['command'].append(host_up)
        echo_obj = {
            'command_name': '_echo',
            'command_line': '_echo',
            'imported_from': 'alignak-self'
        }
        raw_objects['command'].append(echo_obj)

    def early_create_objects(self, raw_objects):
        """Create the objects needed for the post configuration file initialization

        :param raw_objects:  dict with all object with str values
        :type raw_objects: dict
        :return: None
        """
        types_creations = self.__class__.types_creations
        early_created_types = self.__class__.early_created_types

        for o_type in types_creations:
            if o_type in early_created_types:
                self.create_objects_for_type(raw_objects, o_type)

    def create_objects(self, raw_objects):
        """Create all the objects got after the post configuration file initialization

        :param raw_objects:  dict with all object with str values
        :type raw_objects: dict
        :return: None
        """
        types_creations = self.__class__.types_creations
        early_created_types = self.__class__.early_created_types

        # Before really creating the objects, we add some ghost
        # ones like the bp_rule for correlation
        self.add_ghost_objects(raw_objects)

        for o_type in types_creations:
            if o_type not in early_created_types:
                self.create_objects_for_type(raw_objects, o_type)

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
            for obj_cfg in raw_objects[o_type]:
                # We create the object
                lst.append(cls(obj_cfg))
        except KeyError:
            logger.debug("No %s objects in the raw configuration objects", o_type)

        # Create the objects list and set it in our properties
        setattr(self, prop, clss(lst, initial_index))

    def early_arbiter_linking(self):
        """ Prepare the arbiter for early operations

        :return: None
        """

        if not self.arbiters:
            logger.warning("There is no arbiter, I add one in localhost:7770")
            arb = ArbiterLink({'name': 'Default-Arbiter',
                               'host_name': socket.gethostname(),
                               'address': 'localhost', 'port': '7770',
                               'spare': '0'})
            self.arbiters = ArbiterLinks([arb])

        # First fill default
        self.arbiters.fill_default()
        self.modules.fill_default()

        self.arbiters.linkify(modules=self.modules)
        self.modules.linkify()

    def load_triggers(self):
        """Load all triggers .trig files from all triggers_dir

        :return: None
        """
        for path in self.triggers_dirs:
            self.triggers.load_file(path)

    def load_packs(self):  # pragma: no cover, not used, see #551
        """Load all packs .pack files from all packs_dirs

        :return: None
        """
        for path in self.packs_dirs:
            self.packs.load_file(path)

    def linkify_one_command_with_commands(self, commands, prop):
        """
        Link a command

        :param commands: object commands
        :type commands: object
        :param prop: property name
        :type prop: str
        :return: None
        """
        if hasattr(self, prop):
            command = getattr(self, prop).strip()
            if command != '':
                if hasattr(self, 'poller_tag'):
                    data = {"commands": commands, "call": command, "poller_tag": self.poller_tag}
                    cmdcall = CommandCall(data)
                elif hasattr(self, 'reactionner_tag'):
                    data = {"commands": commands, "call": command,
                            "reactionner_tag": self.reactionner_tag}
                    cmdcall = CommandCall(data)
                else:
                    cmdcall = CommandCall({"commands": commands, "call": command})
                setattr(self, prop, cmdcall)
            else:
                setattr(self, prop, None)

    def linkify(self):
        """ Make 'links' between elements, like a host got a services list
        with all it's services in it

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
                           self.triggers, self.checkmodulations,
                           self.macromodulations
                           )

        self.hostsextinfo.merge(self.hosts)

        # Do the simplify AFTER explode groups
        # link hostgroups with hosts
        self.hostgroups.linkify(self.hosts, self.realms)

        # link services with other objects
        self.services.linkify(self.hosts, self.commands,
                              self.timeperiods, self.contacts,
                              self.resultmodulations, self.businessimpactmodulations,
                              self.escalations, self.servicegroups,
                              self.triggers, self.checkmodulations,
                              self.macromodulations
                              )

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

        self.realms.linkify()

        # Link all satellite links with realms
        # self.arbiters.linkify(self.modules)
        self.schedulers.linkify(self.realms, self.modules)
        self.brokers.linkify(self.realms, self.modules)
        self.receivers.linkify(self.realms, self.modules)
        self.reactionners.linkify(self.realms, self.modules)
        self.pollers.linkify(self.realms, self.modules)

        # Ok, now update all realms with backlinks of satellites
        satellites = []
        satellites.extend(self.pollers)
        satellites.extend(self.reactionners)
        satellites.extend(self.receivers)
        satellites.extend(self.brokers)
        self.realms.prepare_for_satellites_conf(satellites)

    def clean(self):
        """Wrapper for calling the clean method of services attribute

        :return: None
        """
        logger.debug("Cleaning configuration objects before configuration sending:")
        types_creations = self.__class__.types_creations
        for o_type in types_creations:
            (_, _, inner_property, _, _) = types_creations[o_type]
            logger.debug("  . for %s", inner_property, )
            object = getattr(self, inner_property)
            object.clean()

    def warn_about_unmanaged_parameters(self):
        """used to raise warning if the user got parameter
        that we do not manage from now

        :return: None
        """
        properties = self.__class__.properties
        unmanaged = []
        for prop, entry in properties.items():
            if not entry.managed and hasattr(self, prop):
                if entry.help:
                    line = "%s: %s" % (prop, entry.help)
                else:
                    line = prop
                unmanaged.append(line)
        if unmanaged:
            logger.warning("The following parameter(s) are not currently managed.")

            for line in unmanaged:
                logger.info(line)

            logger.warning("Unmanaged configuration statements, do you really need it?"
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
        self.escalations.explode(self.hosts, self.hostgroups,
                                 self.contactgroups)

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

    def fill_default(self):
        """Fill objects properties with default value if necessary

        :return: None
        """
        logger.debug("Filling the unset properties with their default value:")
        # Fill default for config (self)
        super(Config, self).fill_default()

        types_creations = self.__class__.types_creations
        for o_type in types_creations:
            (cls, clss, inner_property, initial_index, clonable) = types_creations[o_type]
            # Not yet for the daemons links
            if inner_property in ['realms', 'arbiters', 'schedulers', 'reactionners',
                                  'pollers', 'brokers', 'receivers']:
                continue
            logger.debug("  . for %s", inner_property,)
            object = getattr(self, inner_property)
            object.fill_default()

        # We have all monitored elements, we can create a default realm if none is defined
        self.fill_default_realm()
        self.realms.fill_default()

        # Then we create missing satellites, so no other satellites will be created after
        self.fill_default_satellites()

        types_creations = self.__class__.types_creations
        for o_type in types_creations:
            (cls, clss, inner_property, initial_index, clonable) = types_creations[o_type]
            # Only for the daemons links
            if inner_property in ['schedulers', 'reactionners', 'pollers', 'brokers', 'receivers']:
                logger.debug("  . for %s", inner_property,)
                object = getattr(self, inner_property)
                object.fill_default()

        # Now fill some fields we can predict (like address for hosts)
        self.fill_predictive_missing_parameters()

    def fill_predictive_missing_parameters(self):
        """Wrapper for calling fill_predictive_missing_parameters method of hosts attribute
        Here is a special functions to fill some special
        properties that are not filled and should be like
        address for host (if not set, put host_name)

        :return: None
        """
        self.hosts.fill_predictive_missing_parameters()
        self.services.fill_predictive_missing_parameters()

    def fill_default_realm(self):
        """Check if a realm is defined, if not
        Create a new one (default) and tag everyone that do not have
        a realm prop to be put in this realm

        :return: None
        """
        if not self.realms:
            # Create a default realm so all hosts without realm will be link with it
            default = Realm({
                'realm_name': 'All', 'alias': 'Self created default realm', 'default': '1'
            })
            self.realms = Realms([default])
            logger.warning("No realms defined, I am adding one as %s", default.get_name())

        # Check that a default realm (and only one) is defined and get this default realm
        self.realms.get_default(check=True)

    def log_daemons_list(self):
        """Log Alignak daemons list

        :return:
        """
        daemons = [self.arbiters, self.schedulers, self.pollers, self.brokers,
                      self.reactionners, self.receivers]
        for daemons_list in daemons:
            if not daemons_list:
                logger.info("- %ss: None", daemons_list.inner_class.my_type)
            else:
                logger.info("- %ss: %s", daemons_list.inner_class.my_type,
                            ','.join([daemon.get_name() for daemon in daemons_list]))

    def fill_default_satellites(self):
        # pylint: disable=too-many-branches
        """If a satellite is missing, we add them in the localhost
        with defaults values

        :return: None
        """

        # Log all satellites list
        logger.info("Alignak configured daemons list:")
        self.log_daemons_list()

        # Get realms names and ids
        realms_names = []
        realms_names_ids = {}
        for realm in self.realms:
            realms_names.append(realm.get_name())
            realms_names_ids[realm.get_name()] = realm.uuid
        default_realm = self.realms.get_default()

        if not self.schedulers:
            logger.warning("No scheduler defined, I am adding one at localhost:7768")
            daemon = SchedulerLink({'name': 'Default-Scheduler',
                                    'address': 'localhost', 'port': '7768'})
            self.schedulers = SchedulerLinks([daemon])
        if not self.pollers:
            logger.warning("No poller defined, I am adding one at localhost:7771")
            poller = PollerLink({'name': 'Default-Poller',
                                 'address': 'localhost', 'port': '7771'})
            self.pollers = PollerLinks([poller])
        if not self.reactionners:
            logger.warning("No reactionner defined, I am adding one at localhost:7769")
            reactionner = ReactionnerLink({'name': 'Default-Reactionner',
                                           'address': 'localhost', 'port': '7769'})
            self.reactionners = ReactionnerLinks([reactionner])
        if not self.brokers:
            logger.warning("No broker defined, I am adding one at localhost:7772")
            broker = BrokerLink({'name': 'Default-Broker',
                                 'address': 'localhost', 'port': '7772',
                                 'manage_arbiters': '1'})
            self.brokers = BrokerLinks([broker])

        # Affect default realm to the satellites that do not have a defined realm
        satellites = [self.pollers, self.brokers, self.reactionners,
                      self.receivers, self.schedulers]
        for satellites_list in satellites:
            for satellite in satellites_list:
                if not hasattr(satellite, 'realm') or getattr(satellite, 'realm') == '':
                    satellite.realm = default_realm.get_name()
                    satellite.realm_name = default_realm.get_name()
                    logger.info("Tagging %s with realm %s", satellite.get_name(), satellite.realm)

        # Parse hosts for realms and set host in the default realm is no realm is set
        hosts_realms_names = set()
        for host in self.hosts:
            host_realm_name = getattr(host, 'realm', None)
            if host_realm_name is None or not host_realm_name:
                host.realm = default_realm.get_name()
                host.got_default_realm = True
            hosts_realms_names.add(host.realm)

        # Check that all daemons and realms are coherent (scheduler, broker, poller)
        satellites = [self.schedulers, self.pollers, self.brokers]
        for satellites_list in satellites:
            # Check that all schedulers and realms are coherent
            daemons_class = satellites_list.inner_class
            daemons_realms_names = set()
            for daemon in satellites_list:
                daemon_type = getattr(daemon, 'my_type', None)
                daemon_realm_name = getattr(daemon, 'realm', None)
                if daemon_realm_name is None:
                    logger.warning("The %s %s do not have a defined realm",
                                   daemon_type, daemon.get_name())
                    continue

                if daemon_realm_name not in realms_names:
                    logger.warning("The %s %s is affected to an unknown realm: '%s' (%s)",
                                   daemon_type, daemon.get_name(), daemon_realm_name, realms_names)
                    continue
                daemons_realms_names.add(daemon_realm_name)
                # If the daemon manges sub realms, include the sub realms
                print("Daemon Manage sub realms: %s: %s" % (daemon.name, getattr(daemon, 'manage_sub_realms', False)))
                if getattr(daemon, 'manage_sub_realms', False):
                    for realm in self.realms[realms_names_ids[daemon_realm_name]].all_sub_members:
                        daemons_realms_names.add(realm)

            if not hosts_realms_names.issubset(daemons_realms_names):
                for realm in hosts_realms_names.difference(daemons_realms_names):
                    self.add_warning("Some hosts exist in the realm '%s' but no %s is "
                                     "defined for this realm" % (realm, daemon_type))

                    # Add a self-generated daemon
                    logger.warning("Trying to add a %s for the realm: %s", daemon_type, realm)
                    new_daemon = daemons_class({
                        # 'daemon_name': '%s-%s' % (daemon_type.capitalize(), realm),
                        '%s_name' % daemon_type: '%s-%s' % (daemon_type.capitalize(), realm),
                        'realm': realm, 'spare': '0',
                        'address': 'localhost', 'port': self.daemons_initial_port,
                        'manage_sub_realms': '0', 'manage_arbiters': '0',
                    })
                    self.daemons_initial_port = self.daemons_initial_port + 1
                    self.missing_daemons.append(new_daemon)
                    self.add_warning("Added a %s in the realm '%s'" % (daemon_type, realm))
        # Now we have a list of the missing daemons, parse this list and
        # add the daemons to their respective list
        satellites = [self.schedulers, self.pollers, self.brokers]
        for satellites_list in satellites:
            daemons_class = satellites_list.inner_class
            for daemon in self.missing_daemons:
                if daemon.__class__ == daemons_class:
                    satellites_list.add_item(daemon)

        # Log all satellites list
        logger.info("Alignak definitive daemons list:")
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
        Also check the module_alias

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
                module = module.strip()
                # Ok, now look in modules...
                for mod in self.modules:
                    # try to see if this module is the good type
                    if getattr(mod, 'python_name', '').strip() == module_type.strip():
                        # if so, the good name?
                        if getattr(mod, 'module_alias', '').strip() == module:
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
        """ Check if modules exist for some of the old Nagios parameters.

        If no module of the required type is present, it alerts the user that the parameters will
        be ignored and the functions will be disabled, else it encourages the user to set the
        correct parameters in the installed modules.

        :return: None
        """
        # For status_dat
        if hasattr(self, 'status_file') and self.status_file != '' and \
                hasattr(self, 'object_cache_file') and self.object_cache_file != '':
            # Ok, the user wants retention, search for such a module
            if not self.got_broker_module_type_defined('retention'):
                msg = "Your configuration parameters '%s = %s' and '%s = %s' need to use an " \
                      "external module such as 'retention' but I did not found one!" % \
                      ('status_file', self.status_file,
                       'object_cache_file', self.object_cache_file)
                logger.error(msg)
                self.add_error(msg)
            else:
                msg = "Your configuration parameters '%s = %s' and '%s = %s' are deprecated " \
                      "and will be ignored. Please configure your external 'retention' module " \
                      "as expected." % \
                      ('status_file', self.status_file,
                       'object_cache_file', self.object_cache_file)
                logger.warning(msg)
                self.configuration_warnings.append(msg)

        # Now the log_file
        if hasattr(self, 'log_file') and self.log_file != '':
            # Ok, the user wants some monitoring logs
            if not self.got_broker_module_type_defined('logs'):
                msg = "Your configuration parameter '%s = %s' needs to use an external module " \
                      "such as 'logs' but I did not found one!" % \
                      ('log_file', self.log_file)
                logger.error(msg)
                self.add_error(msg)
            else:
                msg = "Your configuration parameters '%s = %s' are deprecated " \
                      "and will be ignored. Please configure your external 'logs' module " \
                      "as expected." % \
                      ('log_file', self.log_file)
                logger.warning(msg)
                self.configuration_warnings.append(msg)

        # Now the syslog facility
        if hasattr(self, 'use_syslog') and self.use_syslog:
            # Ok, the user want a syslog logging, why not after all
            if not self.got_broker_module_type_defined('logs'):
                msg = "Your configuration parameter '%s = %s' needs to use an external module " \
                      "such as 'logs' but I did not found one!" % \
                      ('use_syslog', self.use_syslog)
                logger.error(msg)
                self.add_error(msg)
            else:
                msg = "Your configuration parameters '%s = %s' are deprecated " \
                      "and will be ignored. Please configure your external 'logs' module " \
                      "as expected." % \
                      ('use_syslog', self.use_syslog)
                logger.warning(msg)
                self.configuration_warnings.append(msg)

        # Now the host_perfdata or service_perfdata module
        if hasattr(self, 'service_perfdata_file') and self.service_perfdata_file != '' or \
                hasattr(self, 'host_perfdata_file') and self.host_perfdata_file != '':
            # Ok, the user wants performance data, search for such a module
            if not self.got_broker_module_type_defined('perfdata'):
                msg = "Your configuration parameters '%s = %s' and '%s = %s' need to use an " \
                      "external module such as 'retention' but I did not found one!" % \
                      ('host_perfdata_file', self.host_perfdata_file,
                       'service_perfdata_file', self.service_perfdata_file)
                logger.error(msg)
                self.add_error(msg)
            else:
                msg = "Your configuration parameters '%s = %s' and '%s = %s' are deprecated " \
                      "and will be ignored. Please configure your external 'retention' module " \
                      "as expected." % \
                      ('host_perfdata_file', self.host_perfdata_file,
                       'service_perfdata_file', self.service_perfdata_file)
                logger.warning(msg)
                self.configuration_warnings.append(msg)

        # Now the old retention file module
        if hasattr(self, 'state_retention_file') and self.state_retention_file != '' and \
                hasattr(self, 'retention_update_interval') and self.retention_update_interval != 0:
            # Ok, the user wants livestate data retention, search for such a module
            if not self.got_scheduler_module_type_defined('retention'):
                msg = "Your configuration parameters '%s = %s' and '%s = %s' need to use an " \
                      "external module such as 'retention' but I did not found one!" % \
                      ('state_retention_file', self.state_retention_file,
                       'retention_update_interval', self.retention_update_interval)
                logger.error(msg)
                self.add_error(msg)
            else:
                msg = "Your configuration parameters '%s = %s' and '%s = %s' are deprecated " \
                      "and will be ignored. Please configure your external 'retention' module " \
                      "as expected." % \
                      ('state_retention_file', self.state_retention_file,
                       'retention_update_interval', self.retention_update_interval)
                logger.warning(msg)
                self.configuration_warnings.append(msg)

        # Now the command_file
        if hasattr(self, 'command_file') and self.command_file != '':
            # Ok, the user wants external commands file, search for such a module
            if not self.got_arbiter_module_type_defined('external_commands'):
                msg = "Your configuration parameter '%s = %s' needs to use an external module " \
                      "such as 'logs' but I did not found one!" % \
                      ('command_file', self.command_file)
                logger.error(msg)
                self.add_error(msg)
            else:
                msg = "Your configuration parameters '%s = %s' are deprecated " \
                      "and will be ignored. Please configure your external 'logs' module " \
                      "as expected." % \
                      ('command_file', self.command_file)
                logger.warning(msg)
                self.configuration_warnings.append(msg)

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
            self.configuration_warnings.append(msg)
            valid &= False
        return valid

    def is_correct(self):  # pylint: disable=R0912, too-many-statements, too-many-locals
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

        # If we got global performance data commands, they should be valid
        if self.host_perfdata_command and not self.host_perfdata_command.is_valid():
            msg = "[%s::%s] global host performance data command '%s' is invalid" \
                  % (self.my_type, self.get_name(), self.host_perfdata_command.command)
            self.add_error(msg)
            valid = False

        if self.service_perfdata_command and not self.service_perfdata_command.is_valid():
            msg = "[%s::%s] global service performance data command '%s' is invalid" \
                  % (self.my_type, self.get_name(), self.service_perfdata_command.command)
            self.add_error(msg)
            valid = False

        # for obj in ['hosts', 'hostgroups', 'contacts', 'contactgroups', 'notificationways',
        #             'escalations', 'services', 'servicegroups', 'timeperiods', 'commands',
        #             'hostsextinfo', 'servicesextinfo', 'checkmodulations', 'macromodulations',
        #             'realms', 'servicedependencies', 'hostdependencies', 'resultmodulations',
        #             'businessimpactmodulations', 'arbiters', 'schedulers', 'reactionners',
        #             'pollers', 'brokers', 'receivers']:
        for _, _, strclss, _, _ in self.types_creations.values():
            if strclss in ['hostescalations', 'serviceescalations']:
                logger.debug("Ignoring correctness check for '%s'...", strclss)
                continue

            if not self.read_config_silent:
                logger.info('Checking %s...', strclss)

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
                logger.error("%s configuration is incorrect!" % strclss)
            if checked_list.configuration_warnings:
                self.configuration_warnings += checked_list.configuration_warnings
                logger.warning("\t%s configuration warnings: %d, total: %d", strclss,
                               len(checked_list.configuration_warnings), len(self.configuration_warnings))

            if not self.read_config_silent:
                try:
                    dump_list = sorted(checked_list, key=lambda k: k.get_full_name())
                except AttributeError:  # pragma: no cover, simple protection
                    dump_list = checked_list

                # Dump at DEBUG level because some tests break with INFO level, and it is not
                # really necessary to have information about each object ;
                for cur_obj in dump_list:
                    logger.debug('\t%s', cur_obj.get_full_name())
                logger.info('\tChecked %d %s', len(checked_list), strclss)

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
        for lst in [self.services, self.hosts]:
            for item in lst:
                if item.got_business_rule:
                    e_ro = self.realms[item.realm]
                    # Something was wrong in the conf, will be raised elsewhere
                    if not e_ro:
                        continue
                    e_r = e_ro.realm_name
                    for elt_uuid in item.business_rule.list_all_elements():
                        if elt_uuid in self.hosts:
                            elt = self.hosts[elt_uuid]
                        else:
                            elt = self.services[elt_uuid]
                        r_o = self.realms[elt.realm]
                        # Something was wrong in the conf, will be raised elsewhere
                        if not r_o:
                            continue
                        elt_r = r_o.realm_name
                        if elt_r != e_r:
                            logger.error("Business_rule '%s' got hosts from another realm: %s",
                                         item.get_full_name(), elt_r)
                            self.add_error("Error: Business_rule '%s' got hosts from another "
                                           "realm: %s" % (item.get_full_name(), elt_r))
                            valid = False

        if self.configuration_errors:
            valid = False
            logger.error("********** Configuration errors:")
            for msg in self.configuration_errors:
                logger.error(msg)

        # If configuration error messages exist, then the configuration is not valid
        self.conf_is_correct = valid

    def explode_global_conf(self):
        """Explode parameters like cached_service_check_horizon in the
        Service class in a cached_check_horizon manner, o*hp commands etc

        :return: None
        """
        for cls, _, strclss, _, _ in self.types_creations.values():
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
            logger.info("Configuration warnings:")
            for msg in self.configuration_warnings:
                logger.info(msg)
        if self.configuration_errors:
            logger.info("Configuration errors:")
            for msg in self.configuration_errors:
                logger.info(msg)

    def create_packs(self):  # pylint: disable=R0915,R0914,R0912,W0613
        """Create packs of hosts and services (all dependencies are resolved)
        It create a graph. All hosts are connected to their
        parents, and hosts without parent are connected to host 'root'.
        services are linked to their host. Dependencies between hosts/services are managed.
        REF: doc/pack-creation.png

        :return: None
        """
        # We create a graph with host in nodes
        graph = Graph()
        graph.add_nodes(self.hosts.items.keys())

        # links will be used for relations between hosts
        links = set()

        # Now the relations
        for host in self.hosts:
            # Add parent relations
            for parent in host.parents:
                if parent:
                    links.add((parent, host.uuid))
            # Add the others dependencies
            for (dep, _, _, _) in host.act_depend_of:
                links.add((dep, host.uuid))
            for (dep, _, _, _, _) in host.chk_depend_of:
                links.add((dep, host.uuid))

        # For services: they are linked with their own host but we need
        # to have the hosts of the service dependency in the same pack too
        for serv in self.services:
            for (dep_id, _, _, _) in serv.act_depend_of:
                if dep_id in self.services:
                    dep = self.services[dep_id]
                else:
                    dep = self.hosts[dep_id]
                # I don't care about dep host: they are just the host
                # of the service...
                if hasattr(dep, 'host'):
                    links.add((dep.host, serv.host))
            # The other type of dep
            for (dep_id, _, _, _, _) in serv.chk_depend_of:
                if dep_id in self.services:
                    dep = self.services[dep_id]
                else:
                    dep = self.hosts[dep_id]
                links.add((dep.host, serv.host))

        # For host/service that are business based, we need to link them too
        for serv in [srv for srv in self.services if srv.got_business_rule]:
            for elem_uuid in serv.business_rule.list_all_elements():
                if elem_uuid in self.services:
                    elem = self.services[elem_uuid]
                    if elem.host != serv.host:  # do not a host with itself
                        links.add((elem.host, serv.host))
                else:  # it's already a host]
                    if elem_uuid != serv.host:
                        links.add((elem_uuid, serv.host))

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
            tmp_realms = set()
            for host_id in hosts_pack:
                host = self.hosts[host_id]
                if host.realm:
                    tmp_realms.add(host.realm)
            if len(tmp_realms) > 1:
                self.add_error("Error: the realm configuration of yours hosts is not good because "
                               "there is more than one realm in one pack (host relations):")
                for host_id in hosts_pack:
                    host = self.hosts[host_id]
                    if host.realm is None:
                        self.add_error(' -> the host %s do not have a realm' % host.get_name())
                    else:
                        # Do not use get_name for the realm because it is not an object but a
                        # string containing the not found realm name if the realm is not existing!
                        # As of it, it may raise an exception
                        self.add_error(' -> the host %s is in the realm %s' %
                                       (host.get_name(), host.realm_name))
            if len(tmp_realms) == 1:  # Ok, good
                realm = self.realms[tmp_realms.pop()]
                # Set the current hosts pack to its realm
                realm.packs.append(hosts_pack)
            elif not tmp_realms:  # Hum.. no realm value? So default Realm
                if default_realm is not None:
                    # Set the current hosts pack to the default realm
                    default_realm.packs.append(hosts_pack)
                else:
                    self.add_error("Error: some hosts do not have a realm and you did not "
                                   "defined a default realm!")
                    for host in hosts_pack:
                        self.add_error('    Impacted host: %s ' % host.get_name())

        # The load balancing is for a loop, so all
        # hosts of a realm (in a pack) will be dispatch
        # in the schedulers of this realm
        # REF: doc/pack-aggregation.png

        # Count the numbers of elements in all the realms, to compare it the total number of hosts
        nb_elements_all_realms = 0
        for realm in self.realms:
            packs = {}
            # create round-robin iterator for id of cfg
            # So dispatching is load balanced in a realm
            # but add a entry in the round-robin tourniquet for
            # every weight point schedulers (so Weight round robin)
            weight_list = []
            no_spare_schedulers = [s_id for s_id in realm.schedulers
                                   if not self.schedulers[s_id].spare]
            nb_schedulers = len(no_spare_schedulers)

            # Maybe there is no scheduler in the realm, it can be a
            # big problem if there are elements in packs
            nb_elements = 0
            for hosts_pack in realm.packs:
                nb_elements += len(hosts_pack)
                nb_elements_all_realms += len(hosts_pack)
            logger.info("Number of hosts in the realm %s: %d "
                        "(distributed in %d linked packs)",
                        realm.get_name(), nb_elements, len(realm.packs))

            if nb_schedulers == 0 and nb_elements != 0:
                self.add_error("The realm %s has hosts but no scheduler!" % realm.get_name())
                realm.packs = []  # Dumb pack
                continue

            packindex = 0
            packindices = {}
            for s_id in no_spare_schedulers:
                sched = self.schedulers[s_id]
                packindices[s_id] = packindex
                packindex += 1
                for i in xrange(0, sched.weight):
                    weight_list.append(s_id)

            round_robin = itertools.cycle(weight_list)

            # We must initialize nb_schedulers packs
            for i in xrange(0, nb_schedulers):
                packs[i] = []

            # Try to load the history association dict so we will try to
            # send the hosts in the same "pack"
            assoc = {}

            # Now we explode the numerous packs into reals packs:
            # we 'load balance' them in a round-robin way but with count number of hosts in
            # case have some packs with too many hosts and other with few
            realm.packs.sort(sort_by_number_values)
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
                        i = round_robin.next()
                    elif (len(packs[packindices[i]]) + len(hosts_pack)) >= pack_higher_hosts:
                        pack_higher_hosts = (len(packs[packindices[i]]) + len(hosts_pack))
                        i = round_robin.next()

                for host_id in hosts_pack:
                    host = self.hosts[host_id]
                    packs[packindices[i]].append(host_id)
                    assoc[host.get_name()] = i

            # Now in packs we have the number of packs [h1, h2, etc]
            # equal to the number of schedulers.
            realm.packs = packs

        for what in (self.contacts, self.hosts, self.services, self.commands):
            logger.info("Number of %s : %d", type(what).__name__, len(what))

        logger.info("Total number of hosts in all realms: %d", nb_elements_all_realms)
        if len(self.hosts) != nb_elements_all_realms:
            logger.warning("There are %d hosts defined, and %d hosts dispatched in the realms. "
                           "Some hosts have been ignored", len(self.hosts), nb_elements_all_realms)
            self.add_error("There are %d hosts defined, and %d hosts dispatched in the realms. "
                           "Some hosts have been "
                           "ignored" % (len(self.hosts), nb_elements_all_realms))

    def cut_into_parts(self):  # pylint: disable=R0912,R0914
        """Cut conf into part for scheduler dispatch.

        Basically it provides a set of host/services for each scheduler that
        have no dependencies between them

        :return: None
        """
        # I do not care about alive or not. User must have set a spare if he needed one
        nb_parts = sum(1 for s in self.schedulers if not s.spare)

        if nb_parts == 0:
            logger.warning("Splitting the configuration into parts but I found no scheduler. "
                           "Considering that one exist anyway...")
            nb_parts = 1

        # We create dummy configurations for schedulers:
        # they are clone of the master configuration but without hosts and
        # services (because they are splitted between these configurations)
        logger.info("Splitting the configuration into parts...")
        self.parts = {}
        for pack_index in xrange(0, nb_parts):
            self.parts[pack_index] = Config()

            # Now we copy all properties of conf into the new ones
            for prop, entry in Config.properties.items():
                # Only the one that are managed and used
                if entry.managed and not isinstance(entry, UnusedProp):
                    val = getattr(self, prop)
                    setattr(self.parts[pack_index], prop, val)

            # Set the cloned configuration name
            self.parts[pack_index].name = "%s (%d)" % (self.name, pack_index)
            logger.info("- cloning configuration: %s", self.parts[pack_index].name)

            # Copy the configuration objects lists. We need a deepcopy because each configuration
            # will have some new groups... but we keep the samme uuid
            self.parts[pack_index].uuid = uuid.uuid4().hex

            types_creations = self.__class__.types_creations
            for o_type in types_creations:
                (cls, clss, inner_property, initial_index, clonable) = types_creations[o_type]
                if not clonable:
                    logger.debug("  . do not clone: %s", inner_property)
                    # print("  . do not clone: %s" % (inner_property))
                    continue
                # todo: Indeed contactgroups should be managed like hostgroups...
                if inner_property in ['hostgroups', 'servicegroups']:
                    new_groups = []
                    for group in getattr(self, inner_property):
                        new_groups.append(group.copy_shell())
                    setattr(self.parts[pack_index], inner_property, clss(new_groups))
                elif inner_property in ['hosts', 'services']:
                    setattr(self.parts[pack_index], inner_property, clss([]))
                else:
                    setattr(self.parts[pack_index], inner_property, getattr(self, inner_property))
                logger.debug("  . cloned %s: %s -> %s", inner_property,
                             getattr(self, inner_property), getattr(self.parts[pack_index], inner_property))

            # The elements of the others conf will be tag here
            self.parts[pack_index].other_elements = {}

            # No scheduler has yet accepted the configuration
            self.parts[pack_index].is_assigned = False
            self.parts[pack_index].assigned_to = None
            self.parts[pack_index].push_flavor = 0
        # Once parts got created, the current configuration has some 'parts'
        # self.parts is the configuration splitted into parts for the schedulers

        # Just create packs. There can be numerous ones
        # In pack we've got hosts and service and packs are in the realms
        logger.debug("Creating packs for realms...")
        self.create_packs()
        # Once packs got created, all the realms have some 'packs'

        # We have packs for realms and elements into configurations, let's merge this...
        offset = 0
        for realm in self.realms:
            logger.debug("Realm: %s", realm)
            for pack_index in realm.packs:
                logger.debug(" - pack: %s / %s", pack_index, realm.packs[pack_index])
                part_uuid = self.parts[pack_index + offset].uuid
                for host_id in realm.packs[pack_index]:
                    host = self.hosts[host_id]
                    host.pack_id = pack_index
                    self.parts[pack_index + offset].hosts.add_item(host)
                    for service_id in host.services:
                        service = self.services[service_id]
                        self.parts[pack_index + offset].services.add_item(service)
                # Now the conf can be linked with the realm
                realm.parts.update({part_uuid: self.parts[pack_index + offset]})
                # realm.confs[pack_index + offset] = self.parts[pack_index + offset]
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
        for part_index in self.parts:
            for host in self.parts[part_index].hosts:
                for j in [j for j in self.parts if j != part_index]:  # So other than i
                    self.parts[part_index].other_elements[host.get_name()] = part_index

        # We tag conf with instance_id
        for part_index in self.parts:
            self.parts[part_index].instance_id = part_index
            random.seed(time.time())

    def prepare_for_sending(self):
        """Some properties are dangerous to be send like that
        like realms linked in hosts. Realms are too big to send (too linked)
        We are also pre-serializing the confs so the sending phase will
        be quicker.

        :return: None
        """
        logger.info('[arbiter] Serializing the configurations...')

        # Moved to the dispatcher...
        # # Serialize the configuration for all the realms
        # for realm in self.realms:
        #     for (index, part) in realm.parts.iteritems():
        #         logger.debug("- realm '%s' configuration (%d)", realm.get_name(), index)
        #         part_id = part.uuid
        #         realm.serialized_parts[part_id] = serialize(part)
        #
        # Now serialize the whole configuration, for sending to spare arbiters
        self.spare_arbiter_conf = serialize(self)

    def dump(self, dump_file=None):
        """Dump configuration to a file in a JSON format

        :param dump_file: the file to dump
        :type dump_file: file
        :return: None
        """
        config_dump = {}

        for _, _, category, _, _ in self.types_creations.values():
            try:
                objs = [jsonify_r(i) for i in getattr(self, category)]
            except TypeError:  # pragma: no cover, simple protection
                logger.warning("Dumping configuration, '%s' not present in the configuration",
                               category)
                continue
            except AttributeError:  # pragma: no cover, simple protection
                logger.warning("Dumping configuration, '%s' not present in the configuration",
                               category)
                continue

            container = getattr(self, category)
            if category == "services":
                objs = sorted(objs, key=lambda o: "%s/%s" %
                                                  (o["host_name"], o["service_description"]))
            elif hasattr(container, "name_property"):
                name_prop = container.name_property
                objs = sorted(objs, key=lambda o, prop=name_prop: getattr(o, prop, ''))
            config_dump[category] = objs

        if dump_file is None:
            temp_d = tempfile.gettempdir()
            path = os.path.join(temp_d, 'alignak-config-dump-%d' % time.time())
            dump_file = open(path, "wb")
            close = True
        else:
            close = False

        dump_file.write(json.dumps(config_dump, indent=4, separators=(',', ': '), sort_keys=True ))
        if close:
            dump_file.close()


def lazy():
    """Generate 256 User macros

    :return: None
    TODO: Should be removed
    """
    # let's compute the "USER" properties and macros..
    for i in xrange(1, 15):
        i = str(i)
        Config.properties['$USER' + str(i) + '$'] = StringProp(default='')
        Config.macros['USER' + str(i)] = '$USER' + i + '$'


lazy()
del lazy
