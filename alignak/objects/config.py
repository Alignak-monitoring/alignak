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
    properties = {
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

        'translate_passive_host_checks':
            UnusedProp(text='Alignak passive checks management make this parameter unuseful.'),
            # BoolProp(managed=False, default=True),

        'passive_host_checks_are_soft':
            UnusedProp(text='Alignak passive checks management make this parameter unuseful.'),
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
                     _help='If you go some host or service definition like prod*, '
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
    }

    macros = {
        'PREFIX':               'prefix',
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
    # Type: 'name in objects': {Class of object, Class of objects,
    # 'property for self for the objects(config)'
    types_creations = {
        'timeperiod':
            (Timeperiod, Timeperiods, 'timeperiods', True),
        'service':
            (Service, Services, 'services', False),
        'servicegroup':
            (Servicegroup, Servicegroups, 'servicegroups', True),
        'command':
            (Command, Commands, 'commands', True),
        'host':
            (Host, Hosts, 'hosts', True),
        'hostgroup':
            (Hostgroup, Hostgroups, 'hostgroups', True),
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
        'servicedependency':
            (Servicedependency, Servicedependencies, 'servicedependencies', True),
        'hostdependency':
            (Hostdependency, Hostdependencies, 'hostdependencies', True),
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
        'realm':
            (Realm, Realms, 'realms', True),
        'module':
            (Module, Modules, 'modules', True),
        'resultmodulation':
            (Resultmodulation, Resultmodulations, 'resultmodulations', True),
        'businessimpactmodulation':
            (Businessimpactmodulation, Businessimpactmodulations,
             'businessimpactmodulations', True),
        'escalation':
            (Escalation, Escalations, 'escalations', True),
        'serviceescalation':
            (Serviceescalation, Serviceescalations, 'serviceescalations', False),
        'hostescalation':
            (Hostescalation, Hostescalations, 'hostescalations', False),
        'hostextinfo':
            (HostExtInfo, HostsExtInfo, 'hostsextinfo', True),
        'serviceextinfo':
            (ServiceExtInfo, ServicesExtInfo, 'servicesextinfo', True),
    }

    # This tab is used to transform old parameters name into new ones
    # so from Nagios2 format, to Nagios3 ones
    old_properties = {
        'nagios_user':  'alignak_user',
        'nagios_group': 'alignak_group'
    }

    read_config_silent = False

    early_created_types = ['arbiter', 'module']

    configuration_types = ['void', 'timeperiod', 'command', 'contactgroup', 'hostgroup',
                           'contact', 'notificationway', 'checkmodulation',
                           'macromodulation', 'host', 'service', 'servicegroup',
                           'servicedependency', 'hostdependency', 'arbiter', 'scheduler',
                           'reactionner', 'broker', 'receiver', 'poller', 'realm', 'module',
                           'resultmodulation', 'escalation', 'serviceescalation', 'hostescalation',
                           'businessimpactmodulation', 'hostextinfo', 'serviceextinfo']

    def __init__(self, params=None, parsing=True):
        if params is None:
            params = {}

        # At deserialization, thoses are dict
        # TODO: Separate parsing instance from recreated ones
        for prop in ['ocsp_command', 'ochp_command',
                     'host_perfdata_command', 'service_perfdata_command',
                     'global_host_event_handler', 'global_service_event_handler']:
            if prop in params and isinstance(params[prop], dict):
                # We recreate the object
                setattr(self, prop, CommandCall(params[prop], parsing=parsing))
                # And remove prop, to prevent from being overridden
                del params[prop]

        for _, clss, strclss, _ in self.types_creations.values():
            if strclss in params and isinstance(params[strclss], dict):
                setattr(self, strclss, clss(params[strclss], parsing=parsing))
                del params[strclss]

        for clss, prop in [(Triggers, 'triggers'), (Packs, 'packs')]:
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

    def serialize(self):
        res = super(Config, self).serialize()
        if hasattr(self, 'instance_id'):
            res['instance_id'] = self.instance_id
        # The following are not in properties so not in the dict
        for prop in ['triggers', 'packs', 'hosts',
                     'services', 'hostgroups', 'notificationways',
                     'checkmodulations', 'macromodulations', 'businessimpactmodulations',
                     'resultmodulations', 'contacts', 'contactgroups',
                     'servicegroups', 'timeperiods', 'commands',
                     'escalations', 'ocsp_command', 'ochp_command',
                     'host_perfdata_command', 'service_perfdata_command',
                     'global_host_event_handler', 'global_service_event_handler']:
            if getattr(self, prop) is None:
                res[prop] = None
            else:
                res[prop] = getattr(self, prop).serialize()
        res['macros'] = self.macros
        return res

    def get_name(self):
        """Get config name

        :return: Hard-coded value 'global configuration file'
        :rtype: str
        """
        return 'global configuration file'

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
                msg = "[config] cannot open main config file '%s' for reading: %s" % (c_file, exp)
                self.add_error(msg)
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
                        msg = "[config] cannot open config file '%s' for reading: %s" % (
                            cfg_file_name, exp
                        )
                        self.add_error(msg)
                elif re.search("^cfg_dir", line):
                    elts = line.split('=', 1)
                    if os.path.isabs(elts[1]):
                        cfg_dir_name = elts[1]
                    else:
                        cfg_dir_name = os.path.join(self.config_base_dir, elts[1])
                    # Ok, look if it's really a directory
                    if not os.path.isdir(cfg_dir_name):
                        msg = "[config] cannot open config dir '%s' for reading" % \
                              (cfg_dir_name)
                        self.add_error(msg)

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
                                msg = "[config] cannot open config file '%s' for reading: %s" % \
                                      (os.path.join(root, c_file), exp)
                                self.add_error(msg)
                elif re.search("^triggers_dir", line):
                    elts = line.split('=', 1)
                    if os.path.isabs(elts[1]):
                        trig_dir_name = elts[1]
                    else:
                        trig_dir_name = os.path.join(self.config_base_dir, elts[1])
                    # Ok, look if it's really a directory
                    if not os.path.isdir(trig_dir_name):
                        msg = "[config] cannot open triggers dir '%s' for reading" % \
                              (trig_dir_name)
                        self.add_error(msg)
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
        """Create real 'object' from dicts of prop/value

        :param raw_objects:  dict with all object with str values
        :type raw_objects: dict
        :return: None
        """
        types_creations = self.__class__.types_creations

        # some types are already created in this time
        early_created_types = self.__class__.early_created_types

        # Before really create the objects, we add
        # ghost ones like the bp_rule for correlation
        self.add_ghost_objects(raw_objects)

        for o_type in types_creations:
            if o_type not in early_created_types:
                self.create_objects_for_type(raw_objects, o_type)

    def create_objects_for_type(self, raw_objects, o_type):
        """Generic function to create object regarding the o_type

        :param raw_objects: Raw object we need to instantiate objects
        :type raw_objects: dict
        :param o_type: the object type we want to create
        :type o_type: object
        :return: None
        """
        types_creations = self.__class__.types_creations
        # Ex: the above code do for timeperiods:
        # timeperiods = []
        # for timeperiodcfg in objects['timeperiod']:
        #    t = Timeperiod(timeperiodcfg)
        #    t.clean()
        #    timeperiods.append(t)
        # self.timeperiods = Timeperiods(timeperiods)

        (cls, clss, prop, initial_index) = types_creations[o_type]
        # List where we put objects
        lst = []
        for obj_cfg in raw_objects[o_type]:
            # We create the object
            obj = cls(obj_cfg)
            # Change Nagios2 names to Nagios3 ones (before using them)
            obj.old_properties_names_to_new()
            lst.append(obj)
        # we create the objects Class and we set it in prop
        setattr(self, prop, clss(lst, initial_index))

    def early_arbiter_linking(self):
        """ Prepare the arbiter for early operations

        :return: None
        """

        if len(self.arbiters) == 0:
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
            self.triggers.load_file(path)

    def load_packs(self):
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
        self.linkify_one_command_with_commands(self.commands, 'ocsp_command')
        self.linkify_one_command_with_commands(self.commands, 'ochp_command')
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

        # Link all links with realms
        # self.arbiters.linkify(self.modules)
        self.schedulers.linkify(self.realms, self.modules)
        self.brokers.linkify(self.realms, self.modules)
        self.receivers.linkify(self.realms, self.modules)
        self.reactionners.linkify(self.realms, self.modules)
        self.pollers.linkify(self.realms, self.modules)

        # Ok, now update all realms with backlinks of
        # satellites
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
        # Preparing hosts and hostgroups for sending. Some properties
        # should be "flatten" before sent, like .realm object that should
        # be changed into names
        self.hosts.prepare_for_sending()
        self.hostgroups.prepare_for_sending()
        t01 = time.time()
        logger.info('[Arbiter] Serializing the configurations...')

        # There are two ways of configuration serializing
        # One if to use the serial way, the other is with use_multiprocesses_serializer
        # to call to sub-workers to do the job.
        # TODO : enable on windows? I'm not sure it will work, must give a test
        if os.name == 'nt' or not self.use_multiprocesses_serializer:
            logger.info('Using the default serialization pass')
            for realm in self.realms:
                for (i, conf) in realm.confs.iteritems():
                    # Remember to protect the local conf hostgroups too!
                    conf.hostgroups.prepare_for_sending()
                    logger.debug('[%s] Serializing the configuration %d', realm.get_name(), i)
                    t00 = time.time()
                    conf_id = conf.uuid
                    realm.serialized_confs[conf_id] = serialize(conf)
                    logger.debug("[config] time to serialize the conf %s:%s is %s (size:%s)",
                                 realm.get_name(), i, time.time() - t00,
                                 len(realm.serialized_confs[conf_id]))
                    logger.debug("SERIALIZE LEN : %d", len(realm.serialized_confs[conf_id]))
            # Now serialize the whole conf, for easy and quick spare send
            t00 = time.time()
            whole_conf_pack = serialize(self)
            logger.debug("[config] time to serialize the global conf : %s (size:%s)",
                         time.time() - t00, len(whole_conf_pack))
            self.whole_conf_pack = whole_conf_pack
            logger.debug("[config]serializing total: %s", (time.time() - t01))

        else:
            logger.info('Using the multiprocessing serialization pass')
            t01 = time.time()

            # We ask a manager to manage the communication with our children
            manager = Manager()
            # The list will got all the strings from the children
            child_q = manager.list()
            for realm in self.realms:
                processes = []
                for (i, conf) in realm.confs.iteritems():
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
                                   args=(child_q, realm.get_name(), i, conf))
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
        # Fill default for config (self)
        super(Config, self).fill_default()
        self.hosts.fill_default()
        self.hostgroups.fill_default()
        self.contacts.fill_default()
        self.contactgroups.fill_default()
        self.notificationways.fill_default()
        self.checkmodulations.fill_default()
        self.macromodulations.fill_default()
        self.services.fill_default()
        self.servicegroups.fill_default()
        self.resultmodulations.fill_default()
        self.businessimpactmodulations.fill_default()
        self.hostsextinfo.fill_default()
        self.servicesextinfo.fill_default()

        # Now escalations
        self.escalations.fill_default()

        # Also fill default of host/servicedep objects
        self.servicedependencies.fill_default()
        self.hostdependencies.fill_default()

        # first we create missing sat, so no other sat will
        # be created after this point
        self.fill_default_satellites()
        # now we have all elements, we can create a default
        # realm if need and it will be tagged to sat that do
        # not have an realm
        self.fill_default_realm()
        self.realms.fill_default()  # also put default inside the realms themselves
        self.reactionners.fill_default()
        self.pollers.fill_default()
        self.brokers.fill_default()
        self.receivers.fill_default()
        self.schedulers.fill_default()

        # The arbiters are already done.
        # self.arbiters.fill_default()

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
        if len(self.realms) == 0:
            # Create a default realm with default value =1
            # so all hosts without realm will be link with it
            default = Realm({
                'realm_name': 'All', 'alias': 'Self created default realm', 'default': '1'
            })
            self.realms = Realms([default])
            logger.warning("No realms defined, I add one at %s", default.get_name())
            lists = [self.pollers, self.brokers, self.reactionners, self.receivers, self.schedulers]
            for lst in lists:
                for elt in lst:
                    if not hasattr(elt, 'realm'):
                        elt.realm = 'All'
                        elt.realm_name = 'All'
                        logger.info("Tagging %s with realm %s", elt.get_name(), default.get_name())

    def fill_default_satellites(self):
        """If a satellite is missing, we add them in the localhost
        with defaults values

        :return: None
        """
        if len(self.schedulers) == 0:
            logger.warning("No scheduler defined, I add one at localhost:7768")
            scheduler = SchedulerLink({'scheduler_name': 'Default-Scheduler',
                                       'address': 'localhost', 'port': '7768'})
            self.schedulers = SchedulerLinks([scheduler])
        if len(self.pollers) == 0:
            logger.warning("No poller defined, I add one at localhost:7771")
            poller = PollerLink({'poller_name': 'Default-Poller',
                                 'address': 'localhost', 'port': '7771'})
            self.pollers = PollerLinks([poller])
        if len(self.reactionners) == 0:
            logger.warning("No reactionner defined, I add one at localhost:7769")
            reactionner = ReactionnerLink({'reactionner_name': 'Default-Reactionner',
                                           'address': 'localhost', 'port': '7769'})
            self.reactionners = ReactionnerLinks([reactionner])
        if len(self.brokers) == 0:
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
                self.configuration_errors.append(msg)
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
                self.configuration_errors.append(msg)
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
                self.configuration_errors.append(msg)
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
                self.configuration_errors.append(msg)
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
                self.configuration_errors.append(msg)
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
                self.configuration_errors.append(msg)
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
        """Check if all elements got a good configuration

        :return: True if the configuration is correct else False
        :rtype: bool
        """
        logger.info(
            'Running pre-flight check on configuration data, initial state: %s',
            self.conf_is_correct
        )
        valid = self.conf_is_correct

        # Globally unmanaged parameters
        if not self.read_config_silent:
            logger.info('Checking global parameters...')
        if not self.check_error_on_hard_unmanaged_parameters():
            valid = False
            self.add_error("Check global parameters failed")

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

                valid = False
                self.configuration_errors += cur.configuration_errors
                msg = "%s configuration is incorrect!" % obj
                self.configuration_errors.append(msg)
                logger.error(msg)
            if cur.configuration_warnings:
                self.configuration_warnings += cur.configuration_warnings
                logger.warning("\t%s configuration warnings: %d, total: %d", obj,
                               len(cur.configuration_warnings), len(self.configuration_warnings))

            if not self.read_config_silent:
                logger.info('\tChecked %d %s', len(cur), obj)

        # Look that all scheduler got a broker that will take brok.
        # If not, raise an Error
        for scheduler in self.schedulers:
            if scheduler.realm:
                if len(self.realms[scheduler.realm].potential_brokers) == 0:
                    logger.error(
                        "The scheduler %s got no broker in its realm or upper",
                        scheduler.get_name()
                    )
                    self.add_error(
                        "Error: the scheduler %s got no broker "
                        "in its realm or upper" % scheduler.get_name()
                    )
                    valid = False

        # Check that for each poller_tag of a host, a poller exists with this tag
        hosts_tag = set()
        hosts_realms = set()
        services_tag = set()
        pollers_tag = set()
        pollers_realms = set()
        for host in self.hosts:
            hosts_tag.add(host.poller_tag)
            hosts_realms.add(self.realms[host.realm])
        for service in self.services:
            services_tag.add(service.poller_tag)
        for poller in self.pollers:
            for tag in poller.poller_tags:
                pollers_tag.add(tag)
            pollers_realms.add(self.realms[poller.realm])

        if not hosts_realms.issubset(pollers_realms):
            for realm in hosts_realms.difference(pollers_realms):
                logger.error("Hosts exist in the realm %s but no poller in this realm",
                             realm.realm_name if realm else 'unknown')
                self.add_error("Error: Hosts exist in the realm %s but no poller "
                               "in this realm" % (realm.realm_name if realm else 'All'))
                valid = False

        if not hosts_tag.issubset(pollers_tag):
            for tag in hosts_tag.difference(pollers_tag):
                logger.error("Hosts exist with poller_tag %s but no poller got this tag", tag)
                self.add_error("Error: hosts exist with poller_tag %s but no poller "
                               "got this tag" % tag)
                valid = False
        if not services_tag.issubset(pollers_tag):
            for tag in services_tag.difference(pollers_tag):
                logger.error("Services exist with poller_tag %s but no poller got this tag", tag)
                self.add_error("Error: services exist with poller_tag %s but no poller "
                               "got this tag" % tag)
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

        if sum(1 for realm in self.realms
               if hasattr(realm, 'default') and realm.default) > 1:
            err = "Error : More than one realm are set to the default realm"
            logger.error(err)
            self.add_error(err)
            valid = False

        if self.configuration_errors and len(self.configuration_errors):
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
        clss = [Service, Host, Contact, SchedulerLink,
                PollerLink, ReactionnerLink, BrokerLink,
                ReceiverLink, ArbiterLink, HostExtInfo]
        for cls in clss:
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

    def add_error(self, txt):
        """Add an error in the configuration error list so we can print them
         all in one place

         Set the configuration as not valid

        :param txt: Text error
        :type txt: str
        :return: None
        """
        self.configuration_errors.append(txt)
        self.conf_is_correct = False

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
        It create a graph. All hosts are connected to their
        parents, and hosts without parent are connected to host 'root'.
        services are link to the host. Dependencies are managed
        REF: doc/pack-creation.png
        TODO : Check why np_packs is not used.

        :param nb_packs: the number of packs to create (number of scheduler basically)
        :type nb_packs: int
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

        # For services: they are link with their own host but we need
        # To have the hosts of service dep in the same pack too
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

        # For host/service that are business based, we need to
        # link them too
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
        for pack in graph.get_accessibility_packs():
            tmp_realms = set()
            for elt_id in pack:
                elt = self.hosts[elt_id]
                if elt.realm:
                    tmp_realms.add(elt.realm)
            if len(tmp_realms) > 1:
                self.add_error("Error: the realm configuration of yours hosts is not good because "
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
                    self.add_error("Error: some hosts do not have a realm and you did not "
                                   "defined a default realm!")
                    for host in pack:
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

            # Maybe there is no scheduler in the realm, it's can be a
            # big problem if there are elements in packs
            nb_elements = 0
            for pack in realm.packs:
                nb_elements += len(pack)
                nb_elements_all_realms += len(pack)
            logger.info("Number of hosts in the realm %s: %d "
                        "(distributed in %d linked packs)",
                        realm.get_name(), nb_elements, len(realm.packs))

            if nb_schedulers == 0 and nb_elements != 0:
                err = "The realm %s has hosts but no scheduler!" % realm.get_name()
                self.add_error(err)
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
        """Cut conf into part for scheduler dispatch.
        Basically it provide a set of host/services for each scheduler that
        have no dependencies between them

        :return:None
        """
        # I do not care about alive or not. User must have set a spare if need it
        nb_parts = sum(1 for s in self.schedulers
                       if not s.spare)

        if nb_parts == 0:
            nb_parts = 1

        # We create dummy configurations for schedulers:
        # they are clone of the master
        # conf but without hosts and services (because they are dispatched between
        # theses configurations)
        self.confs = {}
        for i in xrange(0, nb_parts):
            cur_conf = self.confs[i] = Config()

            # Now we copy all properties of conf into the new ones
            for prop, entry in Config.properties.items():
                if entry.managed and not isinstance(entry, UnusedProp):
                    val = getattr(self, prop)
                    setattr(cur_conf, prop, val)

            # we need a deepcopy because each conf
            # will have new hostgroups
            cur_conf.uuid = uuid.uuid4().hex
            cur_conf.commands = self.commands
            cur_conf.timeperiods = self.timeperiods
            # Create hostgroups with just the name and same id, but no members
            new_hostgroups = []
            for hostgroup in self.hostgroups:
                new_hostgroups.append(hostgroup.copy_shell())
            cur_conf.hostgroups = Hostgroups(new_hostgroups)
            cur_conf.notificationways = self.notificationways
            cur_conf.checkmodulations = self.checkmodulations
            cur_conf.macromodulations = self.macromodulations
            cur_conf.businessimpactmodulations = self.businessimpactmodulations
            cur_conf.resultmodulations = self.resultmodulations
            cur_conf.contactgroups = self.contactgroups
            cur_conf.contacts = self.contacts
            cur_conf.triggers = self.triggers
            cur_conf.escalations = self.escalations
            # Create hostgroups with just the name and same id, but no members
            new_servicegroups = []
            for servicegroup in self.servicegroups:
                new_servicegroups.append(servicegroup.copy_shell())
            cur_conf.servicegroups = Servicegroups(new_servicegroups)
            # Create ours classes
            cur_conf.hosts = Hosts([])
            cur_conf.services = Services([])

            # The elements of the others conf will be tag here
            cur_conf.other_elements = {}
            # if a scheduler have accepted the conf
            cur_conf.is_assigned = False

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
            for i in realm.packs:
                for host_id in realm.packs[i]:
                    host = self.hosts[host_id]
                    host.pack_id = i
                    self.confs[i + offset].hosts.add_item(host)
                    for serv_id in host.services:
                        serv = self.services[serv_id]
                        self.confs[i + offset].services.add_item(serv)
                # Now the conf can be link in the realm
                realm.confs[i + offset] = self.confs[i + offset]
            offset += len(realm.packs)
            del realm.packs

        # We've nearly have hosts and services. Now we want REALS hosts (Class)
        # And we want groups too
        for i in self.confs:
            cfg = self.confs[i]

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
                for serv in mbrs:
                    if serv != '':
                        mbrs_id.append(serv)
                for serv in cfg.services:
                    if serv.uuid in mbrs_id:
                        servicegroup.members.append(serv.uuid)

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
        for i in self.confs:
            for host in self.confs[i].hosts:
                for j in [j for j in self.confs if j != i]:  # So other than i
                    self.confs[i].other_elements[host.get_name()] = i

        # We tag conf with instance_id
        for i in self.confs:
            self.confs[i].instance_id = i
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
