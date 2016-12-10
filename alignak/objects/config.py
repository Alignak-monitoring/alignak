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
import logging
import warnings
from StringIO import StringIO
from multiprocessing import Process, Manager
import json

from alignak.misc.serialization import serialize, unserialize

from alignak.commandcall import CommandCall
from alignak.objects.item import Item
from alignak.objects.timeperiod import Timeperiod, Timeperiods
from alignak.objects.service import Service, Services
from alignak.objects.command import Command, Commands
from alignak.objects.commandcallitem import CommandCallItems
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
from alignak.objects.trigger import Triggers
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
    properties = Item.properties.copy()
    properties.update({
        # Define a name for the configuration
        'name':
            StringProp(default='Monitoring configuration'),

        # Used for the PREFIX macro
        # Alignak prefix does not axist as for Nagios meaning.
        # It is better to set this value as an empty string rather than an meaningless information!
        'prefix':
            StringProp(default=''),

        # Used for the MAINCONFIGFILE macro
        'main_config_file':
            StringProp(default='/usr/local/etc/alignak/alignak.cfg'),

        'config_base_dir':
            StringProp(default=''),  # will be set when we will load a file

        'triggers_dir':
            StringProp(default=''),

        'packs_dir':
            StringProp(default=''),

        # Inner objects cache file for Nagios CGI
        'object_cache_file':
            UnusedProp(text=NO_LONGER_USED),

        'precached_object_file':
            UnusedProp(text='Alignak does not use precached_object_files. Skipping.'),

        'resource_file':
            StringProp(default='/tmp/resources.txt'),

        'temp_file':
            UnusedProp(text='Temporary files are not used in the alignak architecture. Skipping'),

        # Inner retention self created module parameter
        'status_file':
            UnusedProp(text=NO_LONGER_USED),

        'status_update_interval':
            UnusedProp(text=NO_LONGER_USED),

        'enable_notifications':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None), (Contact, None)]),

        'execute_service_checks':
            BoolProp(default=True, class_inherit=[(Service, 'execute_checks')]),

        'accept_passive_service_checks':
            BoolProp(default=True, class_inherit=[(Service, 'accept_passive_checks')]),

        'execute_host_checks':
            BoolProp(default=True, class_inherit=[(Host, 'execute_checks')]),

        'accept_passive_host_checks':
            BoolProp(default=True, class_inherit=[(Host, 'accept_passive_checks')]),

        'enable_event_handlers':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

        # Inner log self created module parameter
        'log_file':
            UnusedProp(text=NO_LONGER_USED),
        'log_rotation_method':
            CharProp(default='d'),
        'log_archive_path':
            StringProp(default='/usr/local/alignak/var/log/archives'),

        # Inner external commands self created module parameter
        'check_external_commands':
            BoolProp(default=True),
        'command_check_interval':
            UnusedProp(text='another value than look always the file is useless, so we fix it.'),
        'command_file':
            StringProp(default=''),
        'external_command_buffer_slots':
            UnusedProp(text='We do not limit the external command slot.'),

        'check_for_updates':
            UnusedProp(text='network administrators will never allow such communication between '
                            'server and the external world. Use your distribution packet manager '
                            'to know if updates are available or go to the '
                            'http://www.github.com/Alignak-monitoring/alignak website instead.'),

        'bare_update_checks':
            UnusedProp(text=None),

        'retain_state_information':
            UnusedProp(text='sorry, retain state information will not be implemented '
                            'because it is useless.'),

        # Inner status.dat self created module parameters
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

        # Todo: not used anywhere in the source code
        'translate_passive_host_checks':
            BoolProp(managed=False, default=True),

        'passive_host_checks_are_soft':
            BoolProp(managed=False, default=False),

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
            UnusedProp(text='fork twice is not use.'),

        'enable_environment_macros':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

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

        # Todo: not used anywhere in the source code
        'soft_state_dependencies':
            BoolProp(managed=False, default=False),

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

        'ocsp_timeout':
            IntegerProp(default=15, class_inherit=[(Service, None)]),

        'ochp_timeout':
            IntegerProp(default=15, class_inherit=[(Host, None)]),

        'perfdata_timeout':
            IntegerProp(default=5, class_inherit=[(Host, None), (Service, None)]),

        # Todo: Is it still of any interest to keep this Nagios distributed feature?
        'obsess_over_services':
            BoolProp(default=False, class_inherit=[(Service, 'obsess_over')]),

        'ocsp_command':
            StringProp(default='', class_inherit=[(Service, None)]),

        'obsess_over_hosts':
            BoolProp(default=False, class_inherit=[(Host, 'obsess_over')]),

        'ochp_command':
            StringProp(default='', class_inherit=[(Host, None)]),

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

        # Todo: not used anywhere in the source code
        'check_for_orphaned_services':
            BoolProp(default=True, class_inherit=[(Service, 'check_for_orphaned')]),

        # Todo: not used anywhere in the source code
        'check_for_orphaned_hosts':
            BoolProp(default=True, class_inherit=[(Host, 'check_for_orphaned')]),

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

        'use_regexp_matching':
            BoolProp(managed=False,
                     default=False,
                     _help='If you go some host or service definition like prod*, '
                           'it will surely failed from now, sorry.'),
        'use_true_regexp_matching':
            BoolProp(managed=False, default=False),

        'admin_email':
            UnusedProp(text='sorry, not yet implemented.'),

        'admin_pager':
            UnusedProp(text='sorry, not yet implemented.'),

        'event_broker_options':
            UnusedProp(text='event broker are replaced by modules '
                            'with a real configuration template.'),
        'broker_module':
            StringProp(default=''),

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

        'flap_history':
            IntegerProp(default=20, class_inherit=[(Host, None), (Service, None)]),

        'max_plugins_output_length':
            IntegerProp(default=8192, class_inherit=[(Host, None), (Service, None)]),

        'no_event_handlers_during_downtimes':
            BoolProp(default=False, class_inherit=[(Host, None), (Service, None)]),

        # Interval between cleaning queues pass
        'cleaning_queues_interval':
            IntegerProp(default=900),

        # Enable or not the notice about old Nagios parameters
        'disable_old_nagios_parameters_whining':
            BoolProp(default=False),

        # Now for problem/impact states changes
        'enable_problem_impacts_states_change':
            BoolProp(default=False, class_inherit=[(Host, None), (Service, None)]),

        # More a running value in fact
        'resource_macros_names':
            ListProp(default=[]),

        'runners_timeout':
            IntegerProp(default=3600),

        # pack_distribution_file is for keeping a distribution history
        # of the host distribution in the several "packs" so a same
        # scheduler will have more change of getting the same host
        'pack_distribution_file':
            StringProp(default='pack_distribution.dat'),

        # Large env tweaks
        'use_multiprocesses_serializer':
            BoolProp(default=False),

        # Local statsd daemon for collecting Alignak internal statistics
        'statsd_host':
            StringProp(default='localhost',
                       class_inherit=[(SchedulerLink, None), (ReactionnerLink, None),
                                      (BrokerLink, None), (PollerLink, None),
                                      (ReceiverLink, None), (ArbiterLink, None)]),
        'statsd_port':
            IntegerProp(default=8125,
                        class_inherit=[(SchedulerLink, None), (ReactionnerLink, None),
                                       (BrokerLink, None), (PollerLink, None),
                                       (ReceiverLink, None), (ArbiterLink, None)]),
        'statsd_prefix': StringProp(default='alignak',
                                    class_inherit=[(SchedulerLink, None), (ReactionnerLink, None),
                                                   (BrokerLink, None), (PollerLink, None),
                                                   (ReceiverLink, None), (ArbiterLink, None)]),
        'statsd_enabled': BoolProp(default=False,
                                   class_inherit=[(SchedulerLink, None), (ReactionnerLink, None),
                                                  (BrokerLink, None), (PollerLink, None),
                                                  (ReceiverLink, None), (ArbiterLink, None)]),
    })

    macros = {
        'PREFIX': 'prefix',
        'MAINCONFIGFILE': 'main_config_file',
        'STATUSDATAFILE': '',
        'COMMENTDATAFILE': '',
        'DOWNTIMEDATAFILE': '',
        'RETENTIONDATAFILE': '',
        'OBJECTCACHEFILE': '',
        'TEMPFILE': '',
        'TEMPPATH': '',
        'LOGFILE': '',
        'RESOURCEFILE': '',
        'COMMANDFILE': 'command_file',
        'HOSTPERFDATAFILE': '',
        'SERVICEPERFDATAFILE': '',
        'ADMINEMAIL': '',
        'ADMINPAGER': ''
        # 'USERn': '$USERn$' # Add at run time
    }

    # Dict of the objects to create from the configuration:
    # Type: 'name in objects': {
    #   Class of object,
    #   Class of objects list,
    #   'property used for the objects list in the config'
    #   True to index the objects in the list, False else
    # }
    types_creations = {
        'timeperiod':
            (Timeperiod, Timeperiods, 'timeperiods', True),
        'command':
            (Command, Commands, 'commands', True),
        'escalation':
            (Escalation, Escalations, 'escalations', True),
        'host':
            (Host, Hosts, 'hosts', True),
        'hostextinfo':
            (HostExtInfo, HostsExtInfo, 'hostsextinfo', True),
        'hostgroup':
            (Hostgroup, Hostgroups, 'hostgroups', True),
        'hostdependency':
            (Hostdependency, Hostdependencies, 'hostdependencies', True),
        'hostescalation':
            (Hostescalation, Hostescalations, 'hostescalations', False),
        'service':
            (Service, Services, 'services', False),  # Do not index services on creation
        'serviceextinfo':
            (ServiceExtInfo, ServicesExtInfo, 'servicesextinfo', True),
        'servicegroup':
            (Servicegroup, Servicegroups, 'servicegroups', True),
        'servicedependency':
            (Servicedependency, Servicedependencies, 'servicedependencies', True),
        'serviceescalation':
            (Serviceescalation, Serviceescalations, 'serviceescalations', False),
        'contact':
            (Contact, Contacts, 'contacts', True),
        'contactgroup':
            (Contactgroup, Contactgroups, 'contactgroups', True),
        'notificationway':
            (NotificationWay, NotificationWays, 'notificationways', True),
        'checkmodulation':
            (CheckModulation, CheckModulations, 'checkmodulations', True),
        'macromodulation':
            (MacroModulation, MacroModulations, 'macromodulations', True),
        'resultmodulation':
            (Resultmodulation, Resultmodulations, 'resultmodulations', True),
        'businessimpactmodulation':
            (Businessimpactmodulation, Businessimpactmodulations,
             'businessimpactmodulations', True),
        'realm':
            (Realm, Realms, 'realms', True),
        'arbiter':
            (ArbiterLink, ArbiterLinks, 'arbiters', True),
        'scheduler':
            (SchedulerLink, SchedulerLinks, 'schedulers', True),
        'reactionner':
            (ReactionnerLink, ReactionnerLinks, 'reactionners', True),
        'broker':
            (BrokerLink, BrokerLinks, 'brokers', True),
        'receiver':
            (ReceiverLink, ReceiverLinks, 'receivers', True),
        'poller':
            (PollerLink, PollerLinks, 'pollers', True),
        'module':
            (Module, Modules, 'modules', True),
    }

    # This tab is used to transform old parameters name into new ones
    # so from Nagios2 format, to Nagios3 ones
    old_properties = {
        'nagios_user': 'alignak_user',
        'nagios_group': 'alignak_group'
    }

    read_config_silent = False

    # Objects created early in the configuration process
    early_created_types = ['arbiter', 'module']

    configuration_types = ['void', 'timeperiod', 'command', 'contactgroup', 'hostgroup',
                           'contact', 'notificationway', 'checkmodulation',
                           'macromodulation', 'host', 'service', 'servicegroup',
                           'servicedependency', 'hostdependency', 'arbiter', 'scheduler',
                           'reactionner', 'broker', 'receiver', 'poller', 'realm', 'module',
                           'resultmodulation', 'escalation', 'serviceescalation', 'hostescalation',
                           'businessimpactmodulation', 'hostextinfo', 'serviceextinfo']

    def __init__(self, params=None, parsing=True):
        super(Config, self).__init__(params, parsing=parsing)

        if params is None:
            params = {}

        if parsing:
            # # By default the conf is correct and the warnings and errors lists are empty
            # self.conf_is_correct = True
            #
            # We tag the conf with a magic_hash (random value)
            random.seed(time.time())
            self.magic_hash = random.randint(1, 100000)

            # Resource macros
            self.resource_macros_names = []
            # Triggers
            self.triggers_dirs = []
            self.triggers = Triggers([])
            # Packs
            self.packs_dirs = []
            self.packs = Packs([])

            self.parts = {}

            self.is_assigned = False
            self.assigned_to = None

            self.push_flavor = False
        else:
            # At deserialization, those are dict
            for prop in ['ocsp_command', 'ochp_command',
                         'host_perfdata_command', 'service_perfdata_command',
                         'global_host_event_handler', 'global_service_event_handler']:
                if prop in params and isinstance(params[prop], dict):
                    # We recreate the object
                    setattr(self, prop, CommandCall(params[prop], parsing=parsing))

            # Restore some properties from the parameters
            for obj_class, list_class, prop, _ in self.types_creations.values():
                logger.debug("Restoring configuration parameters: %s (%s)", prop, list_class)
                if prop in params and params[prop]:
                    setattr(self, prop, list_class(params[prop], parsing=parsing))
                else:
                    setattr(self, prop, list_class({}, parsing=parsing))
                logger.debug("Restored configuration parameters: %s", prop)

            for clss, prop in [(Triggers, 'triggers'), (Packs, 'packs')]:
                if prop in params and isinstance(params[prop], dict):
                    setattr(self, prop, clss(params[prop], parsing=parsing))

            for prop in ['conf_is_correct', 'magic_hash', 'parts',
                         'is_assigned', 'assigned_to', 'push_flavor']:
                if prop in params:
                    # We restore if it exists in the parameters
                    setattr(self, prop, params[prop])

    def serialize(self):
        """
        Serialize the whole monitoring configuration. This is to build a configuration that
        will be sent to the spare arbiter.
        :return:
        """
        saved_magic_hash = self.magic_hash
        res = super(Config, self).serialize()

        # Special properties to serialize
        res['macros'] = self.macros
        res['magic_hash'] = saved_magic_hash
        if hasattr(self, 'instance_id'):
            res['instance_id'] = self.instance_id
        if hasattr(self, 'confs'):
            res['confs'] = self.confs

        for prop in ['conf_is_correct', 'magic_hash', 'parts',
                     'is_assigned', 'assigned_to', 'push_flavor']:
            res[prop] = getattr(self, prop)

        for prop in ['ocsp_command', 'ochp_command',
                     'host_perfdata_command', 'service_perfdata_command',
                     'global_host_event_handler', 'global_service_event_handler']:
            if getattr(self, prop, None) is None:
                res[prop] = None
            else:
                res[prop] = getattr(self, prop).serialize()

        for _, _, prop, _ in self.types_creations.values():
            if getattr(self, prop, None) is None:
                res[prop] = None
            else:
                # Serialize the list of objects
                res[prop] = getattr(self, prop).serialize()

        for prop in ['triggers', 'packs']:
            if getattr(self, prop, None) is None:
                res[prop] = None
            else:
                res[prop] = getattr(self, prop).serialize()

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

        for key, value in clean_params.items():

            if key in self.properties:
                val = self.properties[key].pythonize(clean_params[key])
            elif key in self.running_properties:
                logger.warning("using a the running property %s in a config file", key)
                val = self.running_properties[key].pythonize(clean_params[key])
            elif key.startswith('$') or key in ['cfg_file', 'cfg_dir']:
                # it's a macro or a useless now param, we don't touch this
                val = value
            else:
                msg = "Guessing the property %s type because it is not in %s object properties" % (
                    key, self.__class__.__name__
                )
                self.configuration_warnings.append(msg)
                logger.warning(msg)
                val = ToGuessProp.pythonize(clean_params[key])

            setattr(self, key, val)
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

        for c_file in files:
            # We add a \n (or \r\n) to be sure config files are separated
            # if the previous does not finish with a line return
            res.write(os.linesep)
            res.write('# IMPORTEDFROM=%s' % (c_file) + os.linesep)
            if not self.read_config_silent:
                logger.info("[config] opening '%s' configuration file", c_file)
            try:
                # Open in Universal way for Windows, Mac, Linux-based systems
                file_d = open(c_file, 'rU')
                buf = file_d.readlines()
                file_d.close()
                self.config_base_dir = os.path.dirname(c_file)
                # Update macro used properties
                self.main_config_file = os.path.abspath(c_file)
            except IOError, exp:
                self.add_error("[config] cannot open main config file '%s' for reading: %s" %
                               (c_file, exp))
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
                            logger.info("Processing object config file '%s'", cfg_file_name)
                        res.write(os.linesep + '# IMPORTEDFROM=%s' % (cfg_file_name) + os.linesep)
                        res.write(file_d.read().decode('utf8', 'replace'))
                        # Be sure to add a line return so we won't mix files
                        res.write(os.linesep)
                        file_d.close()
                    except IOError, exp:
                        self.add_error("[config] cannot open config file '%s' for reading: %s" %
                                       (cfg_file_name, exp))
                elif re.search("^cfg_dir", line):
                    elts = line.split('=', 1)
                    if os.path.isabs(elts[1]):
                        cfg_dir_name = elts[1]
                    else:
                        cfg_dir_name = os.path.join(self.config_base_dir, elts[1])
                    # Ok, look if it's really a directory
                    if not os.path.isdir(cfg_dir_name):
                        self.add_error("[config] cannot open config dir '%s' for reading" %
                                       (cfg_dir_name))

                    # Look for .pack file into it :)
                    self.packs_dirs.append(cfg_dir_name)

                    # Now walk for it.
                    for root, _, files in os.walk(cfg_dir_name, followlinks=True):
                        for c_file in files:
                            if not re.search(r"\.cfg$", c_file):
                                continue
                            if not self.read_config_silent:
                                logger.info("Processing object config file '%s'",
                                            os.path.join(root, c_file))
                            try:
                                res.write(os.linesep + '# IMPORTEDFROM=%s' %
                                          (os.path.join(root, c_file)) + os.linesep)
                                file_d = open(os.path.join(root, c_file), 'rU')
                                res.write(file_d.read().decode('utf8', 'replace'))
                                # Be sure to separate files data
                                res.write(os.linesep)
                                file_d.close()
                            except IOError, exp:
                                self.add_error("[config] cannot open config file "
                                               "'%s' for reading: %s" %
                                               (os.path.join(root, c_file), exp))
                elif re.search("^triggers_dir", line):
                    elts = line.split('=', 1)
                    if os.path.isabs(elts[1]):
                        trig_dir_name = elts[1]
                    else:
                        trig_dir_name = os.path.join(self.config_base_dir, elts[1])
                    # Ok, look if it's really a directory
                    if not os.path.isdir(trig_dir_name):
                        self.add_error("[config] cannot open triggers dir '%s' for reading" %
                                       (trig_dir_name))
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
        params = []
        objectscfg = {}
        types = self.__class__.configuration_types
        for o_type in types:
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

    def create_objects(self, raw_objects):
        """Create real 'objects' from dictionaries of property/value

        :param raw_objects:  dictionary with all objects with string values
        :type raw_objects: dict
        :return: None
        """
        # some types are already created at this time
        early_created_types = self.__class__.early_created_types

        # Before really creating the objects, we add
        # ghost ones like the bp_rule for correlation
        self.add_ghost_objects(raw_objects)

        for object_type in self.__class__.types_creations:
            if object_type not in early_created_types:
                self.create_objects_for_type(raw_objects, object_type)

    def create_objects_for_type(self, raw_objects, object_type):
        """Generic function to create object of the type object_type

        :param raw_objects: Raw object we need to instantiate objects
        :type raw_objects: dict
        :param object_type: the object type we want to create
        :type object_type: object
        :return: None
        """
        # Ex: the above code do for timeperiods:
        # timeperiods = []
        # for timeperiodcfg in objects['timeperiod']:
        #    t = Timeperiod(timeperiodcfg)
        #    t.clean()
        #    timeperiods.append(t)
        # self.timeperiods = Timeperiods(timeperiods)

        (obj_class, list_class, prop, initial_indexation) = \
            self.__class__.types_creations[object_type]
        logger.debug("Create objects for: %s, configuration property: %s", object_type, prop)

        # List to store created objects
        objects_list = []
        for object_configuration in raw_objects[object_type]:
            # Create an object of the required type
            new_object = obj_class(object_configuration)
            # Todo: Still of any interest?
            # Change Nagios2 names to Nagios3 ones (before using them)
            new_object.old_properties_names_to_new()
            objects_list.append(new_object)

        # We create the objects list object and we set it in our own properties
        setattr(self, prop, list_class(objects_list, initial_indexation))

    def early_arbiter_linking(self):
        """ Prepare the arbiter for early operations

        :return: None
        """
        logger.debug("Arbiters in the configuration: %s", self.arbiters)
        if not hasattr(self, 'arbiters') or not self.arbiters:
            logger.warning("There is no arbiter, I add one in localhost:7770")
            arb = ArbiterLink({'arbiter_name': 'Default-Arbiter',
                               'host_name': socket.gethostname(),
                               'address': 'localhost', 'port': '7770',
                               'spare': '0'})
            self.arbiters = ArbiterLinks([arb])

        # First fill default
        self.arbiters.fill_default()
        self.modules.fill_default()

        self.arbiters.linkify(self.modules)
        self.modules.linkify()

    def load_triggers(self):
        """Load all triggers .trig files from all triggers_dir

        :return: None
        """
        for path in self.triggers_dirs:
            logger.debug("Loading triggers from: %s", path)
            self.triggers.load_file(path)

    def load_packs(self):
        """Load all packs .pack files from all packs_dirs

        :return: None
        """
        for path in self.packs_dirs:
            logger.debug("Loading packs from: %s", path)
            self.packs.load_file(path)

    def linkify_one_command_with_commands(self, commands, command_name):
        """
        Link a command

        :param commands: object commands
        :type commands: object
        :param command_name: property name for the command
        :type command_name: str
        :return: None
        """
        # Alert about using this method that is no more useful
        warnings.warn("Using Config::linkify_one_command_with_commands for %s" % command_name,
                      DeprecationWarning, stacklevel=2)

    def linkify(self):
        """ Make 'links' between elements, like a host got a services list
        with all it's services in it

        :return: None
        """
        # This simply defines an hosts attributes in the services list
        self.services.optimize_service_search(self.hosts)

        # First linkify myself with global commands thanks to the CommandCallItems
        cc = CommandCallItems([self])
        cc.linkify_one_command_with_commands(self.commands, 'ocsp_command')
        cc.linkify_one_command_with_commands(self.commands, 'ochp_command')
        cc.linkify_one_command_with_commands(self.commands, 'host_perfdata_command')
        cc.linkify_one_command_with_commands(self.commands, 'service_perfdata_command')
        cc.linkify_one_command_with_commands(self.commands, 'global_host_event_handler')
        cc.linkify_one_command_with_commands(self.commands, 'global_service_event_handler')

        # link hosts with the other objects
        self.hosts.linkify(self.timeperiods, self.commands,
                           self.contacts, self.realms,
                           self.resultmodulations, self.businessimpactmodulations,
                           self.escalations, self.hostgroups,
                           self.triggers, self.checkmodulations,
                           self.macromodulations
                           )
        # Todo: to be removed (extinfo)
        self.hostsextinfo.merge(self.hosts)

        # Do the simplify AFTER explode groups
        # link hostgroups with hosts
        self.hostgroups.linkify(self.hosts, self.realms)

        # link services with the other objects
        self.services.linkify(self.hosts, self.commands,
                              self.timeperiods, self.contacts,
                              self.resultmodulations, self.businessimpactmodulations,
                              self.escalations, self.servicegroups,
                              self.triggers, self.checkmodulations,
                              self.macromodulations
                              )
        # Todo: to be removed (extinfo)
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

        # link contacts with timeperiods, commands and contactgroups
        self.contacts.linkify(self.commands, self.notificationways, self.contactgroups)

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

        # Link all daemons links with realms
        self.schedulers.linkify(self.realms, self.modules)
        self.brokers.linkify(self.realms, self.modules)
        self.receivers.linkify(self.realms, self.modules)
        self.reactionners.linkify(self.realms, self.modules)
        self.pollers.linkify(self.realms, self.modules)

        # Ok, now update all realms with backlinks of satellites
        self.realms.prepare_for_satellites_conf((self.reactionners, self.pollers,
                                                 self.brokers, self.receivers))

    def clean(self):
        """Wrapper for calling the clean method of services attribute

        :return: None
        """
        self.services.clean()

    def prepare_for_sending(self):
        """Some properties are dangerous to be send like that
        like realms linked in hosts. Realms are too big to send (too linked)
        We are also pre-serializing the confs so the sending phase will
        be quicker.

        :return: None
        """
        logger.info('Prepare the configuration sending')

        # Alert about using this method that is no more useful
        warnings.warn("Using Config::prepare_for_sending, still useful?",
                      DeprecationWarning, stacklevel=2)

        # Preparing hosts and hostgroups for sending. Some properties
        # should be "flatten" before sent, like .realm object that should
        # be changed into names
        self.hosts.prepare_for_sending()
        self.hostgroups.prepare_for_sending()

        # There are two ways of configuration serializing
        # One if to use the serial way, the other is with use_multiprocesses_serializer
        # to call to sub-workers to do the job.
        # TODO : enable on windows? I'm not sure it will work, must give a test
        if os.name == 'nt' or not self.use_multiprocesses_serializer:
            logger.info('Using the default serialization pass')
            for realm in self.realms:
                for realm_conf in realm.confs.values():
                    # Remember to protect the local conf hostgroups too!
                    realm_conf.hostgroups.prepare_for_sending()
                    logger.info("Serializing the '%s' realm configuration", realm.get_name())
                    start = time.time()
                    conf_id = realm_conf.uuid
                    realm.serialized_confs[conf_id] = serialize(realm_conf)
                    logger.info("Serialized the '%s' realm configuration: %s seconds (length: %s)",
                                realm.get_name(), time.time() - start,
                                len(realm.serialized_confs[conf_id]))

            # Now serialize the whole conf, for easy and quick spare master send
            start = time.time()
            logger.info("Serializing the global configuration, uuid: %s, #%s",
                        self.uuid, self.magic_hash)
            self.whole_conf_pack_magic_hash = self.magic_hash
            self.whole_conf_pack = serialize(self)
            logger.info("Serialized the global configuration, #%s, %s seconds (length: %s)",
                        self.magic_hash, time.time() - start, len(self.whole_conf_pack))

        else:  # pragma: no cover, not used currently (see #606)
            # Todo: #606, what was it done for?
            logger.info('Using the multiprocessing serialization pass')

            # We ask a manager to manage the communication with our children
            manager = Manager()
            # The list will got all the strings from the children
            child_q = manager.list()
            for realm in self.realms:
                processes = []
                for realm_conf in realm.confs.values():
                    def serialize_config(comm_q, rname, cid, conf):
                        """Serialized config. Used in subprocesses to serialize all config faster

                        :param comm_q: Queue to communicate
                        :param rname: realm name
                        :param cid: configuration id
                        :param conf: configuration to serialize
                        :return: None (put in queue)
                        """
                        # Remember to protect the local conf hostgroups too!
                        conf.hostgroups.prepare_for_sending()
                        logger.debug('[%s] Serializing the configuration %d', rname, cid)
                        t00 = time.time()
                        res = serialize(conf)
                        logger.debug("[config] time to serialize the conf %s:%s is %s (size:%s)",
                                     rname, cid, time.time() - t00, len(res))
                        comm_q.append((cid, res))

                    # Prepare a sub-process that will manage the serialize computation
                    proc = Process(target=serialize_config,
                                   name="serializer-%s-%d" % (realm.get_name(), i),
                                   args=(child_q, realm.get_name(), i, realm_conf))
                    proc.start()
                    processes.append((i, proc))

                # Here all sub-processes are launched for this realm, now wait for them to finish
                while len(processes) != 0:
                    to_del = []
                    for (i, proc) in processes:
                        if proc.exitcode is not None:
                            to_del.append((i, proc))
                            # remember to join() so the children can die
                            proc.join()
                    for (i, proc) in to_del:
                        logger.debug("The sub process %s is done with the return code %d",
                                     proc.name, proc.exitcode)
                        processes.remove((i, proc))
                    # Don't be too quick to poll!
                    time.sleep(0.1)

                # Check if we got the good number of configuration,
                #  maybe one of the children got problems?
                if len(child_q) != len(realm.confs):
                    logger.error("Something goes wrong in the configuration serializations, "
                                 "please restart Alignak Arbiter")
                    sys.exit(2)
                # Now get the serialized configuration and saved them into self
                for (i, cfg) in child_q:
                    realm.serialized_confs[cfg.uuid] = cfg

            # Now serialize the whole configuration into one big serialized object,
            # for the arbiter spares
            whole_queue = manager.list()
            t00 = time.time()

            def create_whole_conf_pack(whole_queue, self):
                """The function that just compute the whole conf serialize string, but n a children
                """
                logger.debug("[config] sub processing the whole configuration pack creation")
                whole_queue.append(serialize(self))
                logger.debug("[config] sub processing the whole configuration pack creation "
                             "finished")
            # Go for it
            proc = Process(target=create_whole_conf_pack,
                           args=(whole_queue, self),
                           name='serializer-whole-configuration')
            proc.start()
            # Wait for it to die
            while proc.exitcode is None:
                time.sleep(0.1)
            proc.join()
            # Maybe we don't have our result?
            if len(whole_queue) != 1:
                logger.error("Something goes wrong in the whole configuration pack creation, "
                             "please restart Alignak Arbiter")
                sys.exit(2)

            # Get it and save it
            self.whole_conf_pack = whole_queue.pop()
            logger.debug("[config] time to serialize the global conf : %s (size:%s)",
                         time.time() - t00, len(self.whole_conf_pack))

            # Shutdown the manager, the sub-process should be gone now
            manager.shutdown()

    def notice_about_useless_parameters(self):
        """Used to warn about useless parameter and print why it's not use.

        :return: None
        """
        if not self.disable_old_nagios_parameters_whining:
            properties = self.__class__.properties
            for prop, entry in properties.items():
                if isinstance(entry, UnusedProp):
                    logger.warning("The parameter %s is useless and can be removed "
                                   "from the configuration (Reason: %s)", prop, entry.text)

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
        if len(unmanaged) != 0:
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
        # First elements, then groups
        self.contacts.explode(self.contactgroups, self.notificationways)
        self.contactgroups.explode(self.contacts)

        self.hosts.explode(self.hostgroups, self.contactgroups)
        self.hostgroups.explode(self.hosts)

        self.services.explode(self.hosts, self.hostgroups, self.contactgroups,
                              self.servicegroups, self.servicedependencies)
        self.servicegroups.explode(self.services)

        self.timeperiods.explode()

        self.hostdependencies.explode(self.hostgroups)

        self.servicedependencies.explode(self.hostgroups)

        # Serviceescalations and hostescalations will create new escalations
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
        # Todo: check if it is really necessary... the Item __init__ function fills the
        # default values after the parameters got parsed...
        # Apply inheritance for all the managed objects
        for _, _, prop, _ in self.types_creations.values():
            if getattr(self, prop, None) is not None:
                # Fill the missing properties with their default values
                getattr(self, prop).apply_inheritance()

        # # inheritance properties by template
        # self.hosts.apply_inheritance()
        # self.contacts.apply_inheritance()
        # self.services.apply_inheritance()
        # self.servicedependencies.apply_inheritance()
        # self.hostdependencies.apply_inheritance()
        # self.timeperiods.apply_inheritance()
        # self.hostsextinfo.apply_inheritance()
        # self.servicesextinfo.apply_inheritance()
        #
        # # Now escalations too
        # self.serviceescalations.apply_inheritance()
        # self.hostescalations.apply_inheritance()
        # self.escalations.apply_inheritance()

    def apply_implicit_inheritance(self):
        """Wrapper for calling apply_implicit_inheritance method of services attributes
        Implicit inheritance is between host and service (like notification parameters etc)

        :return:None
        """
        self.services.apply_implicit_inheritance(self.hosts)

    def set_default_values(self):
        """Fill objects properties with default value if necessary

        :return: None
        """
        # Fill default for config (self)
        # Todo: not necessary... the Item __init__ function fills the default missing properties
        # super(Config, self).fill_default()

        # First create missing satellites, so that no other satellites will
        # be created after this point
        self.fill_default_satellites()
        # now we have all elements, so we can create a default
        # realm if needed and it will be tagged to satellites that do
        # not have a realm
        self.fill_default_realm()

        # Todo: check if it is really necessary... the Item __init__ function fills the
        # default values after the parameters got parsed...
        for _, _, prop, _ in self.types_creations.values():
            if getattr(self, prop, None) is not None:
                # Fill the missing properties with their default values
                getattr(self, prop).fill_default()

                # Fill the predictable missing properties (host_name for hosts, initial_state, ...)
                if hasattr(getattr(self, prop), 'fill_predictable_missing_parameters'):
                    getattr(self, prop).fill_predictable_missing_parameters()

    def fill_default_realm(self):
        """Check if a realm is defined, if not
        Create a new one (default) and tag everyone that do not have
        a realm prop to be put in this realm

        Todo: perharps we should check if some realms exist that one
        of them is defined as the default realm

        :return: None
        """
        if not hasattr(self, 'realms') or not self.realms:
            logger.warning("No realms defined, I add a default one as 'All'")
            # Create a default realm (default=1) so all hosts without an explicit realm
            # will be linked with this default realm
            default_realm = Realm({
                'realm_name': 'All', 'alias': 'Self created default realm', 'default': '1'
            })
            self.realms = Realms([default_realm])

            for satellites in [self.pollers, self.brokers, self.reactionners,
                               self.receivers, self.schedulers]:
                for satellite in satellites:
                    if not hasattr(satellite, 'realm'):
                        satellite.realm = 'All'
                        satellite.realm_name = 'All'
                        logger.info("Tagging %s with realm %s",
                                    satellite.get_name(), default_realm.get_name())

    def fill_default_satellites(self):
        """If a satellite type is missing, we add it in the current configuration
        with defaults values

        Todo: see what to do with this function!
        When dispatching the configuration through the realms, this function is called for
        each realm configuration and, as such, it creates unneeded satellites in the realms!

        Obviously, this function was not intended to be used in a realm configuration
        to be dispatched :/

        For the moment, only create scheduler, broker and poller if they do not exist in the
        current configuration!

        :return: None
        """
        if not hasattr(self, 'schedulers') or not self.schedulers:
            logger.warning("No scheduler defined, I add one at localhost:7768")
            scheduler = SchedulerLink({'scheduler_name': 'Default-Scheduler',
                                       'address': 'localhost', 'port': '7768'})
            self.schedulers = SchedulerLinks([scheduler])
        if not hasattr(self, 'pollers') or not self.pollers:
            logger.warning("No poller defined, I add one at localhost:7771")
            poller = PollerLink({'poller_name': 'Default-Poller',
                                 'address': 'localhost', 'port': '7771'})
            self.pollers = PollerLinks([poller])
        # if not hasattr(self, 'reactionners') or not self.reactionners:
        #     logger.warning("No reactionner defined, I add one at localhost:7769")
        #     reactionner = ReactionnerLink({'reactionner_name': 'Default-Reactionner',
        #                                    'address': 'localhost', 'port': '7769'})
        #     self.reactionners = ReactionnerLinks([reactionner])
        # if not hasattr(self, 'receivers') or not self.receivers:
        #     logger.warning("No receiver defined, I add one at localhost:7773")
        #     receiver = ReceiverLink({'receiver_name': 'Default-Receiver',
        #                                    'address': 'localhost', 'port': '7773'})
        #     self.receivers = ReceiverLinks([receiver])
        if not hasattr(self, 'brokers') or not self.brokers:
            logger.warning("No broker defined, I add one at localhost:7772")
            broker = BrokerLink({'broker_name': 'Default-Broker',
                                 'address': 'localhost', 'port': '7772',
                                 'manage_arbiters': '1'})
            self.brokers = BrokerLinks([broker])

    def got_broker_module_type_defined(self, module_type):
        """Check if a module type is defined in one of the brokers

        :param module_type: module type to search for
        :type module_type: str
        :return: True if mod_type is found else False
        :rtype: bool
        """
        for broker in self.brokers:
            for module in broker.modules:
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
        for scheduler in self.schedulers:
            for module in scheduler.modules:
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
                # So look at what the arbiter tries to call as module
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
        if hasattr(self, 'status_file') and self.status_file and \
                hasattr(self, 'object_cache_file') and self.object_cache_file != '':
            # Ok, the user wants retention, search for such a module
            if not self.got_broker_module_type_defined('retention'):
                self.add_error("Your configuration parameters '%s = %s' and '%s = %s' need to use "
                               "an external module such as 'retention' but I did not found one!"
                               % ('status_file', self.status_file,
                                  'object_cache_file', self.object_cache_file))
            else:
                self.add_error("Your configuration parameters '%s = %s' and '%s = %s' are "
                               "deprecated and will be ignored. Please configure your external "
                               "'retention' module as expected."
                               % ('status_file', self.status_file,
                                  'object_cache_file', self.object_cache_file),
                               is_warning=True)

        # Now the log_file
        if hasattr(self, 'log_file') and self.log_file:
            # Ok, the user wants some monitoring logs
            if not self.got_broker_module_type_defined('logs'):
                self.add_error("Your configuration parameter '%s = %s' needs to use an external "
                               "module such as 'logs' but I did not found one!" %
                               ('log_file', self.log_file))
            else:
                self.add_error("Your configuration parameters '%s = %s' are deprecated "
                               "and will be ignored. Please configure your external 'logs' module "
                               "as expected." % ('log_file', self.log_file),
                               is_warning=True)

        # Now the syslog facility
        if hasattr(self, 'use_syslog') and self.use_syslog:
            # Ok, the user want a syslog logging, why not after all
            if not self.got_broker_module_type_defined('logs'):
                self.add_error("Your configuration parameter '%s = %s' needs to use an external "
                               "module such as 'logs' but I did not found one!" %
                               ('use_syslog', self.use_syslog))
            else:
                self.add_error("Your configuration parameters '%s = %s' are deprecated "
                               "and will be ignored. Please configure your external 'logs' "
                               "module as expected." % ('use_syslog', self.use_syslog),
                               is_warning=True)

        # Now the host_perfdata or service_perfdata module
        if hasattr(self, 'service_perfdata_file') and self.service_perfdata_file or \
                hasattr(self, 'host_perfdata_file') and self.host_perfdata_file:
            # Ok, the user wants performance data, search for such a module
            if not self.got_broker_module_type_defined('perfdata'):
                self.add_error("Your configuration parameters '%s = %s' and '%s = %s' need to use "
                               "an external module such as 'retention' but I did not found one!"
                               % ('host_perfdata_file', self.host_perfdata_file,
                                  'service_perfdata_file', self.service_perfdata_file))
            else:
                self.add_error("Your configuration parameters '%s = %s' and '%s = %s' are "
                               "deprecated and will be ignored. Please configure your external "
                               "'retention' module as expected."
                               % ('host_perfdata_file', self.host_perfdata_file,
                                  'service_perfdata_file', self.service_perfdata_file),
                               is_warning=True)

        # Now the old retention file module
        if hasattr(self, 'state_retention_file') and self.state_retention_file and \
                hasattr(self, 'retention_update_interval') and self.retention_update_interval != 0:
            # Ok, the user wants livestate data retention, search for such a module
            if not self.got_scheduler_module_type_defined('retention'):
                self.add_error("Your configuration parameters '%s = %s' and '%s = %s' need to use "
                               "an external module such as 'retention' but I did not found one!"
                               % ('state_retention_file', self.state_retention_file,
                                  'retention_update_interval', self.retention_update_interval))
            else:
                self.add_error("Your configuration parameters '%s = %s' and '%s = %s' are "
                               "deprecated and will be ignored. Please configure your external "
                               "'retention' module as expected."
                               % ('state_retention_file', self.state_retention_file,
                                  'retention_update_interval', self.retention_update_interval),
                               is_warning=True)

        # Now the command_file
        if hasattr(self, 'command_file') and self.command_file:
            # Ok, the user wants external commands file, search for such a module
            if not self.got_arbiter_module_type_defined('external_commands'):
                self.add_error("Your configuration parameter '%s = %s' needs to use an "
                               "external module such as 'logs' but I did not found one!"
                               % ('command_file', self.command_file))
            else:
                self.add_error("Your configuration parameters '%s = %s' are deprecated "
                               "and will be ignored. Please configure your external 'logs' "
                               "module as expected." % ('command_file', self.command_file),
                               is_warning=True)

    def propagate_timezone_option(self):
        """Set our timezone value and give it too to unset satellites

        :return: None
        """
        if self.use_timezone != '':
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
        # Linkify templates for all the managed objects
        for _, _, prop, _ in self.types_creations.values():
            if getattr(self, prop, None) is not None:
                # Fill the missing properties with their default values
                getattr(self, prop).linkify_templates()
        # self.hosts.linkify_templates()
        # self.contacts.linkify_templates()
        # self.services.linkify_templates()
        # self.servicedependencies.linkify_templates()
        # self.hostdependencies.linkify_templates()
        # self.timeperiods.linkify_templates()
        # self.hostsextinfo.linkify_templates()
        # self.servicesextinfo.linkify_templates()
        # self.escalations.linkify_templates()
        # # But also old srv and host escalations
        # self.serviceescalations.linkify_templates()
        # self.hostescalations.linkify_templates()

    def check_error_on_hard_unmanaged_parameters(self):
        """Some parameters are just not managed like O*HP commands  and regexp capabilities

        :return: True if we encounter an error, otherwise False
        :rtype: bool
        """
        valid = True
        if self.use_regexp_matching:
            logger.error("use_regexp_matching parameter is not managed.")
            valid &= False
        # if self.ochp_command != '':
        #      logger.error("ochp_command parameter is not managed.")
        #      r &= False
        # if self.ocsp_command != '':
        #      logger.error("ocsp_command parameter is not managed.")
        #      r &= False
        return valid

    def is_correct(self):  # pylint: disable=R0912, too-many-statements
        """Check if all elements arre corrects for a good configuration

        :return: True if the configuration is correct else False
        :rtype: bool
        """
        # Assume we are ok. Hope we will still be ok at the end...
        valid = True

        logger.info('Running pre-flight check on configuration data, initial state: %s',
                    self.conf_is_correct)

        # Globally unmanaged parameters
        if not self.read_config_silent:
            logger.info('Checking global parameters...')
        if not self.check_error_on_hard_unmanaged_parameters():
            self.add_error("Global parameters check failed")

        for obj in ['hosts', 'hostgroups', 'contacts', 'contactgroups', 'notificationways',
                    'escalations', 'services', 'servicegroups', 'timeperiods', 'commands',
                    'hostsextinfo', 'servicesextinfo', 'checkmodulations', 'macromodulations',
                    'realms', 'servicedependencies', 'hostdependencies', 'resultmodulations',
                    'businessimpactmodulations', 'arbiters', 'schedulers', 'reactionners',
                    'pollers', 'brokers', 'receivers', ]:
            if not self.read_config_silent:
                logger.info('Checking %s...', obj)

            try:
                cur = getattr(self, obj)
            except AttributeError:
                logger.info("\t%s are not present in the configuration", obj)
                continue

            if not cur.is_correct():
                if not self.read_config_silent:
                    logger.info('Checked %s, configuration is incorrect!', obj)
                self.add_error("%s configuration is incorrect:" % obj)

            # Cumulate my objects configuration messages
            if cur.configuration_errors:
                self.add_errors(cur.configuration_errors)
            if cur.configuration_warnings:
                self.add_errors(cur.configuration_warnings, is_warning=True)

            if not self.read_config_silent:
                logger.info('\tChecked %d %s', len(cur), obj)

        # Look that all scheduler got a broker that will take brok.
        # If not, raise an Error
        for scheduler in self.schedulers:
            if scheduler.realm:
                if len(self.realms[scheduler.realm].potential_brokers) == 0:
                    self.add_error("The scheduler %s got no broker in its realm or upper" %
                                   scheduler.get_name())

        # Check that for each poller_tag of a host, a poller exists with this tag
        hosts_tags = set()
        hosts_realms = set()
        services_tags = set()
        pollers_tags = set()
        pollers_realms = set()
        for host in self.hosts:
            hosts_tags.add(host.poller_tag)
            hosts_realms.add(self.realms[host.realm])
        for service in self.services:
            services_tags.add(service.poller_tag)
        for poller in self.pollers:
            for tag in poller.poller_tags:
                pollers_tags.add(tag)
            pollers_realms.add(self.realms[poller.realm])
        if not pollers_tags:
            pollers_tags = set(['None'])

        if not hosts_realms.issubset(pollers_realms):
            for realm in hosts_realms.difference(pollers_realms):
                self.add_error("Hosts exist in the realm %s but there is no poller "
                               "in this realm" % (realm.realm_name if realm else 'All'))

        if not hosts_tags.issubset(pollers_tags):
            for tag in hosts_tags.difference(pollers_tags):
                self.add_error("Hosts exist with the poller_tag '%s' but no poller "
                               "got this tag" % tag)

        if not services_tags.issubset(pollers_tags):
            for tag in services_tags.difference(pollers_tags):
                self.add_error("Services exist with the poller_tag '%s' but no poller "
                               "got this tag" % tag)

        # Check that all hosts involved in business rules are from the same realm
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
                            self.add_error("Business_rule '%s' got hosts from another "
                                           "realm: %s" % (item.get_name(), elt_r))

        if sum(1 for realm in self.realms if hasattr(realm, 'default') and realm.default) > 1:
            self.add_error("More than one realm are set to the default realm")

        if self.configuration_errors and len(self.configuration_errors):
            valid = False
            logger.error("********** Configuration errors:")
            for msg in self.configuration_errors:
                logger.error(msg)

        # If configuration error messages exist, then the configuration is not valid
        self.conf_is_correct = valid

        logger.info('Running pre-flight check on configuration data, final state: %s',
                    self.conf_is_correct)
        return self.conf_is_correct

    def explode_global_conf(self):
        """Explode parameters like cached_service_check_horizon in the
        Service class in a cached_check_horizon manner, o*hp commands etc

        :return: None
        """
        clss = [Service, Host, Contact, SchedulerLink,
                PollerLink, ReactionnerLink, BrokerLink,
                ReceiverLink, ArbiterLink, HostExtInfo]
        for cls in clss:
            cls.load_global_conf(self)

    def remove_templates(self):
        """Clean useless elements like templates because they are not needed anymore

        :return: None
        """
        for _, _, prop, _ in self.types_creations.values():
            if getattr(self, prop, None) is not None:
                # Fill the missing properties with their default values
                getattr(self, prop).remove_templates()

    def show_errors(self):
        """
        Loop over configuration warnings and log them as INFO log
        Loop over configuration errors and log them as INFO log

        Note that the warnings and errors are logged on the fly during the configuration parsing.
        It is not necessary to log as WARNING and ERROR in this function which is used as a sum-up
        on the end of configuration parsing when an error has been detected.

        :return:  None
        """
        if self.configuration_warnings and len(self.configuration_warnings):
            logger.info("Configuration warnings:")
            for msg in self.configuration_warnings:
                logger.info(msg)
        if self.configuration_errors and len(self.configuration_errors):
            logger.info("Configuration errors:")
            for msg in self.configuration_errors:
                logger.info(msg)

    def create_packs(self, nb_packs):  # pylint: disable=R0915,R0914,R0912,W0613
        """Create packs of hosts and services (all dependencies are resolved)
        It creates a graph.

        All hosts are connected to their parents, and hosts without parent are connected
        to a fake 'root' host.
        services are linked to the hosts. Dependencies are managed
        REF: doc/pack-creation.png
        TODO : Check why nb_packs is not used.

        :param nb_packs: the number of packs to create (number of scheduler basically)
        :type nb_packs: int
        :return: None
        """
        # We create a graph with hosts uuid in nodes
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

        # For services: they are linked with their own host but we also need
        # to have the hosts of service dependencies in the same pack
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
            # The other type of dependencies
            for (dep_id, _, _, _, _) in service.chk_depend_of:
                if dep_id in self.services:
                    dep = self.services[dep_id]
                else:
                    dep = self.hosts[dep_id]
                links.add((dep.host, service.host))

        # For host/service that are business rules based, we also need to link them
        for service in [srv for srv in self.services if srv.got_business_rule]:
            for elem_uuid in service.business_rule.list_all_elements():
                if elem_uuid in self.services:
                    elem = self.services[elem_uuid]
                    if elem.host != service.host:  # do not link a host with itself
                        links.add((elem.host, service.host))
                else:  # it's already a host]
                    if elem_uuid != service.host:
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

        # Now we create links in the graph. With links which is a set
        # we are sure to call the less add_edge
        for (dep, host) in links:
            graph.add_edge(dep, host)
            graph.add_edge(host, dep)

        # Now We find the default realm
        default_realm = self.realms.get_default()

        # Access_list from a node if all nodes that are connected
        # with it: it's a list of ours mini_packs
        # Now we look if all elements of all packs have the
        # same realm. If not, not good!
        for pack in graph.get_accessibility_packs():
            tmp_realms = set()
            for elt_id in pack:
                elt = self.hosts[elt_id]
                if elt.realm:
                    tmp_realms.add(elt.realm)
            if len(tmp_realms) > 1:
                self.add_error("the realm configuration of yours hosts is not good because "
                               "there is more than one realm in one pack (host relations):")
                for host_id in pack:
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
                realm = self.realms[tmp_realms.pop()]  # There is just one element
                realm.packs.append(pack)
            elif len(tmp_realms) == 0:  # Hum.. no realm value? So default Realm
                if default_realm is not None:
                    default_realm.packs.append(pack)
                else:
                    self.add_error("some hosts do not have a realm and you "
                                   "did not defined a default realm!")
                    for host in pack:
                        self.add_error(' - impacted host: %s ' % host.get_name())

        # The load balancing is for a loop, so all
        # hosts of a realm (in a pack) will be dispatched
        # to the schedulers of this realm
        # REF: doc/pack-aggregation.png

        # Count the number of elements in all the realms, to compare it the total number of hosts
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
            for pack in realm.packs:
                nb_elements += len(pack)
                nb_elements_all_realms += len(pack)
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

            # We must have nb_schedulers packs
            for i in xrange(0, nb_schedulers):
                packs[i] = []

            # Try to load the history association dict so we will try to
            # send the hosts in the same "pack"
            assoc = {}

            # Now we explode the numerous packs into nb_packs reals packs:
            # we 'load balance' them in a round-robin way but with count number of hosts in
            # case have some packs with too many hosts and other with few
            realm.packs.sort(sort_by_number_values)
            pack_higher_hosts = 0
            for pack in realm.packs:
                valid_value = False
                old_pack = -1
                for elt_id in pack:
                    elt = self.hosts[elt_id]
                    old_i = assoc.get(elt.get_name(), -1)
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
                    elif (len(packs[packindices[i]]) + len(pack)) >= pack_higher_hosts:
                        pack_higher_hosts = (len(packs[packindices[i]]) + len(pack))
                        i = round_robin.next()

                for elt_id in pack:
                    elt = self.hosts[elt_id]
                    packs[packindices[i]].append(elt_id)
                    assoc[elt.get_name()] = i

            # Now in packs we have the number of packs [h1, h2, etc]
            # equal to the number of schedulers.
            realm.packs = packs  # pylint: disable=R0204

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
        """Cut the global configuration into parts for scheduler dispatching.

        Basically it provides a set of host/services for each scheduler that
        have no dependencies between them

        The global configuration is splitted into several parts (as many as
        defined schedulers), except for hosts and services (and hostgroups /
        servicegroups)

        Then each newly created configuration has some hosts / services affected

        :return:None
        """
        # I do not care about alive or not. User must have set a spare if he needs it
        nb_parts = sum(1 for s in self.schedulers if not s.spare)
        if nb_parts == 0:
            nb_parts = 1

        logger.info("Splitting configuration into parts")

        # We create dummy configurations for schedulers:
        # they are clone of the master configuration but without hosts and services
        # (because they are dispatched between these configurations)
        self.confs = {}
        for index in xrange(0, nb_parts):
            current_conf = self.confs[index] = Config({'name': "part-%d" % index})
            logger.debug("Creating a new configuration: %s", current_conf)

            # Now we copy all properties of a configuration into the newly created
            for prop, entry in Config.properties.items():
                if prop in ['uuid', 'name']:
                    # Do not change uuid nor configuration name
                    continue
                if entry.managed and not isinstance(entry, UnusedProp):
                    setattr(current_conf, prop, getattr(self, prop))

            # we need a deepcopy because each conf
            # will have new hostgroups

            # current_conf.uuid = uuid.uuid4().hex
            current_conf.commands = self.commands
            current_conf.timeperiods = self.timeperiods
            current_conf.notificationways = self.notificationways
            current_conf.checkmodulations = self.checkmodulations
            current_conf.macromodulations = self.macromodulations
            current_conf.businessimpactmodulations = self.businessimpactmodulations
            current_conf.resultmodulations = self.resultmodulations
            current_conf.contacts = self.contacts
            current_conf.triggers = self.triggers
            current_conf.escalations = self.escalations

            # Todo: why contactgroups are different from hostgroups and servicegroups?
            current_conf.contactgroups = self.contactgroups

            # Create hostgroups with the same objects, but without members
            new_hostgroups = Hostgroups([])
            for copy_hostgroup in self.hostgroups:
                new_hostgroups.add_item(copy_hostgroup.copy_shell())
            current_conf.hostgroups = new_hostgroups
            # Create servicegroups with the same objects, but without members
            new_servicegroups = Servicegroups([])
            for copy_servicegroup in self.servicegroups:
                new_servicegroups.add_item(copy_servicegroup.copy_shell())
            current_conf.servicegroups = new_servicegroups

            # Create hosts and services classes
            current_conf.hosts = Hosts([])
            current_conf.services = Services([])

            # The elements of the others conf will be tag here
            current_conf.other_elements = {}
            # No scheduler has yet accepted the configuration
            current_conf.is_assigned = False
            logger.debug("Created a new configuration: %s", current_conf)

        logger.info("Creating packs for realms")

        # Just create packs. There can be numerous ones
        # In pack we've got hosts and service
        # packs are in the realms
        # REF: doc/pack-creation.png
        self.create_packs(nb_parts)

        # We've got all big packs and get elements into configurations
        # REF: doc/pack-aggregation.png
        offset = 0
        for realm in self.realms:
            for pack_id in realm.packs:
                for host_uuid in realm.packs[pack_id]:
                    host = self.hosts[host_uuid]
                    host.pack_id = pack_id
                    self.confs[pack_id + offset].hosts.add_item(host)
                    for service_uuid in host.services:
                        service = self.services[service_uuid]
                        self.confs[pack_id + offset].services.add_item(service)
                # Now the conf can be linked to the realm
                realm.confs[pack_id + offset] = self.confs[pack_id + offset]
            offset += len(realm.packs)
            del realm.packs

        # We've nearly have hosts and services. Now we want REALS hosts (Class)
        # And we want groups too
        for index in self.confs:
            current_conf = self.confs[index]

            # Fill host groups
            for initial_hostgroup in self.hostgroups:
                copy_hostgroup = current_conf.hostgroups.find_by_name(initial_hostgroup.get_name())
                for host_uuid in initial_hostgroup.get_members():
                    if host_uuid in current_conf.hosts:
                        copy_hostgroup.members.append(host_uuid)

            # And also relink the hosts with the new hostgroups
            for host in current_conf.hosts:
                initial_hostgroups = host.hostgroups
                new_hostgroups = []
                for hostgroup_uuid in initial_hostgroups:
                    ohg = self.hostgroups[hostgroup_uuid]
                    nhg = current_conf.hostgroups.find_by_name(ohg.get_name())
                    new_hostgroups.append(nhg.uuid)
                host.hostgroups = new_hostgroups

            # Fill servicegroup
            for initial_servicegroup in self.servicegroups:
                copy_servicegroup = current_conf.servicegroups.find_by_name(
                    initial_servicegroup.get_name())
                for service_uuid in initial_servicegroup.get_members():
                    if service_uuid in current_conf.services:
                        copy_servicegroup.members.append(service_uuid)

            # And also relink the services with the new servicegroups
            for service in current_conf.services:
                initial_servicegroups = service.servicegroups
                new_servicegroups = []
                for servicegroup_uuid in initial_servicegroups:
                    osg = self.servicegroups[servicegroup_uuid]
                    nsg = current_conf.servicegroups.find_by_name(osg.get_name())
                    new_servicegroups.append(nsg.uuid)
                service.servicegroups = new_servicegroups

        # Now we fill other_elements by host (services are already with their respective hosts)
        # so they are not tagged)
        for index in self.confs:
            for host in self.confs[index].hosts:
                for j in [j for j in self.confs if j != index]:  # So other than i
                    self.confs[index].other_elements[host.get_name()] = index

        # We tag conf with instance_id
        for index in self.confs:
            self.confs[index].instance_id = index
            random.seed(time.time())

    def dump(self, dfile=None):
        """Dump configuration to a file in a JSON format

        :param dfile: the file to dump
        :type dfile: file
        :return: None
        """
        dmp = {}

        for category in ("hosts",
                         "hostgroups",
                         "hostdependencies",
                         "contactgroups",
                         "contacts",
                         "notificationways",
                         "checkmodulations",
                         "macromodulations",
                         "servicegroups",
                         "services",
                         "servicedependencies",
                         "resultmodulations",
                         "businessimpactmodulations",
                         "escalations",
                         "arbiters",
                         "brokers",
                         "pollers",
                         "reactionners",
                         "receivers",
                         "schedulers",
                         "realms",
                         ):
            try:
                objs = [jsonify_r(i) for i in getattr(self, category)]
            except TypeError:
                logger.warning("Dumping configuration, '%s' not present in the configuration",
                               category)
                continue
            except AttributeError:
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
            dmp[category] = objs

        if dfile is None:
            temp_d = tempfile.gettempdir()
            path = os.path.join(temp_d, 'alignak-config-dump-%d' % time.time())
            dfile = open(path, "wb")
            close = True
        else:
            close = False
        dfile.write(
            json.dumps(
                dmp,
                indent=4,
                separators=(',', ': '),
                sort_keys=True
            )
        )
        if close is True:
            dfile.close()


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
