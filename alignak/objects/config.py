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

import re
import sys
import string
import os
import socket
import itertools
import time
import random
import cPickle
import tempfile
from StringIO import StringIO
from multiprocessing import Process, Manager
import json

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
from alignak.util import split_semicolon
from alignak.objects.arbiterlink import ArbiterLink, ArbiterLinks
from alignak.objects.schedulerlink import SchedulerLink, SchedulerLinks
from alignak.objects.reactionnerlink import ReactionnerLink, ReactionnerLinks
from alignak.objects.brokerlink import BrokerLink, BrokerLinks
from alignak.objects.receiverlink import ReceiverLink, ReceiverLinks
from alignak.objects.pollerlink import PollerLink, PollerLinks
from alignak.graph import Graph
from alignak.log import logger
from alignak.property import (UnusedProp, BoolProp, IntegerProp, CharProp,
                              StringProp, LogLevelProp, ListProp, ToGuessProp)
from alignak.daemon import get_cur_user, get_cur_group
from alignak.util import jsonify_r


NO_LONGER_USED = ('This parameter is not longer take from the main file, but must be defined '
                  'in the status_dat broker module instead. But Alignak will create you one '
                  'if there are no present and use this parameter in it, so no worry.')
NOT_INTERESTING = 'We do not think such an option is interesting to manage.'


class Config(Item):
    """Config is the class to read, load and manipulate the user
 configuration. It read a main cfg (alignak.cfg) and get all informations
 from it. It create objects, make link between them, clean them, and cut
 them into independent parts. The main user of this is Arbiter, but schedulers
 use it too (but far less)

    """
    cache_path = "objects.cache"
    my_type = "config"
    _id = 1

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
        'prefix':
            StringProp(default='/usr/local/alignak/'),

        'workdir':
            StringProp(default='/var/run/alignak/'),

        'config_base_dir':
            StringProp(default=''),  # will be set when we will load a file

        'modules_dir':
            StringProp(default='/var/lib/alignak/modules'),

        'use_local_log':
            BoolProp(default=True),

        'log_level':
            LogLevelProp(default='WARNING'),


        'local_log':
            StringProp(default='/var/log/alignak/arbiterd.log'),

        'log_file':
            UnusedProp(text=NO_LONGER_USED),

        'object_cache_file':
            UnusedProp(text=NO_LONGER_USED),

        'precached_object_file':
            UnusedProp(text='Alignak does not use precached_object_files. Skipping.'),

        'resource_file':
            StringProp(default='/tmp/resources.txt'),

        'temp_file':
            UnusedProp(text='Temporary files are not used in the alignak architecture. Skipping'),

        'status_file':
            UnusedProp(text=NO_LONGER_USED),

        'status_update_interval':
            UnusedProp(text=NO_LONGER_USED),

        'alignak_user':
            StringProp(default=get_cur_user()),

        'alignak_group':
            StringProp(default=get_cur_group()),

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

        'log_rotation_method':
            CharProp(default='d'),

        'log_archive_path':
            StringProp(default='/usr/local/alignak/var/archives'),
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

        'lock_file':
            StringProp(default='/var/run/alignak/arbiterd.pid'),

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

        'use_syslog':
            BoolProp(default=False),

        'log_notifications':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

        'log_service_retries':
            BoolProp(default=True, class_inherit=[(Service, 'log_retries')]),

        'log_host_retries':
            BoolProp(default=True, class_inherit=[(Host, 'log_retries')]),

        'log_event_handlers':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

        'log_initial_states':
            BoolProp(default=True, class_inherit=[(Host, None), (Service, None)]),

        'log_external_commands':
            BoolProp(default=True),

        'log_passive_checks':
            BoolProp(default=True),

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

        'use_aggressive_host_checking':
            BoolProp(default=False, class_inherit=[(Host, None)]),

        'translate_passive_host_checks':
            BoolProp(managed=False, default=True),

        'passive_host_checks_are_soft':
            BoolProp(managed=False, default=True),

        'enable_predictive_host_dependency_checks':
            BoolProp(managed=False,
                     default=True,
                     class_inherit=[(Host, 'enable_predictive_dependency_checks')]),

        'enable_predictive_service_dependency_checks':
            BoolProp(managed=False, default=True),

        'cached_host_check_horizon':
            IntegerProp(default=0, class_inherit=[(Host, 'cached_check_horizon')]),


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

        'check_for_orphaned_services':
            BoolProp(default=True, class_inherit=[(Service, 'check_for_orphaned')]),

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
        # '$USERn$: {'required':False, 'default':''} # Add at run in __init__

        # ALIGNAK SPECIFIC
        'idontcareaboutsecurity':
            BoolProp(default=False),

        'daemon_enabled':
            BoolProp(default=True),  # Put to 0 to disable the arbiter to run

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

        # SSL PART
        # global boolean for know if we use ssl or not
        'use_ssl':
            BoolProp(default=False,
                     class_inherit=[(SchedulerLink, None), (ReactionnerLink, None),
                                    (BrokerLink, None), (PollerLink, None),
                                    (ReceiverLink, None), (ArbiterLink, None)]),
        'ca_cert':
            StringProp(default='etc/certs/ca.pem'),

        'server_cert':
            StringProp(default='etc/certs/server.cert'),

        'server_key':
            StringProp(default='etc/certs/server.key'),

        'hard_ssl_name_check':
            BoolProp(default=False),

        # Log format
        'human_timestamp_log':
            BoolProp(default=False),

        'runners_timeout':
            IntegerProp(default=3600),

        # pack_distribution_file is for keeping a distribution history
        # of the host distribution in the several "packs" so a same
        # scheduler will have more change of getting the same host
        'pack_distribution_file':
            StringProp(default='pack_distribution.dat'),

        # WEBUI part
        'webui_lock_file':
            StringProp(default='webui.pid'),

        'webui_port':
            IntegerProp(default=8080),

        'webui_host':
            StringProp(default='0.0.0.0'),

        # Large env tweacks
        'use_multiprocesses_serializer':
            BoolProp(default=False),

        # About alignak.io part
        'api_key':
            StringProp(default='',
                       class_inherit=[(SchedulerLink, None), (ReactionnerLink, None),
                                      (BrokerLink, None), (PollerLink, None),
                                      (ReceiverLink, None), (ArbiterLink, None)]),
        'secret':
            StringProp(default='',
                       class_inherit=[(SchedulerLink, None), (ReactionnerLink, None),
                                      (BrokerLink, None), (PollerLink, None),
                                      (ReceiverLink, None), (ArbiterLink, None)]),
        'http_proxy':
            StringProp(default='',
                       class_inherit=[(SchedulerLink, None), (ReactionnerLink, None),
                                      (BrokerLink, None), (PollerLink, None),
                                      (ReceiverLink, None), (ArbiterLink, None)]),

        # and local statsd one
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
        'MAINCONFIGFILE':       '',
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
        'nagios_group': 'alignak_group',
        'modulesdir': 'modules_dir',
    }

    read_config_silent = 0

    early_created_types = ['arbiter', 'module']

    configuration_types = ['void', 'timeperiod', 'command', 'contactgroup', 'hostgroup',
                           'contact', 'notificationway', 'checkmodulation',
                           'macromodulation', 'host', 'service', 'servicegroup',
                           'servicedependency', 'hostdependency', 'arbiter', 'scheduler',
                           'reactionner', 'broker', 'receiver', 'poller', 'realm', 'module',
                           'resultmodulation', 'escalation', 'serviceescalation', 'hostescalation',
                           'businessimpactmodulation', 'hostextinfo', 'serviceextinfo']

    def __init__(self):
        super(Config, self).__init__()
        self.params = {}
        self.resource_macros_names = []
        # By default the conf is correct
        self.conf_is_correct = True
        # We tag the conf with a magic_hash, a random value to
        # idify this conf
        random.seed(time.time())
        self.magic_hash = random.randint(1, 100000)
        self.configuration_errors = []
        self.triggers_dirs = []
        self.triggers = Triggers({})
        self.packs_dirs = []
        self.packs = Packs({})

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
                self.conf_is_correct = False
                logger.error("[config] the parameter %s is malformed! (no = sign)", elts[0])
            elif elts[1] == '':
                self.conf_is_correct = False
                logger.error("[config] the parameter %s is malformed! (no value after =)", elts[0])
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
                logger.warning("Guessing the property %s type because it is not in "
                               "%s object properties", key, self.__class__.__name__)
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

    def _cut_line(self, line):
        """Split the line on withespaces and remove empty chunks

        :param line: the line to split
        :type line: str
        :return: list of strings
        :rtype: list
        """
        # punct = '"#$%&\'()*+/<=>?@[\\]^`{|}~'
        tmp = re.split("[" + string.whitespace + "]+", line, 1)
        res = [elt for elt in tmp if elt != '']
        return res

    def read_config(self, files):
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
            if self.read_config_silent == 0:
                logger.info("[config] opening '%s' configuration file", c_file)
            try:
                # Open in Universal way for Windows, Mac, Linux-based systems
                file_d = open(c_file, 'rU')
                buf = file_d.readlines()
                file_d.close()
                self.config_base_dir = os.path.dirname(c_file)
            except IOError, exp:
                logger.error("[config] cannot open config file '%s' for reading: %s", c_file, exp)
                # The configuration is invalid because we have a bad file!
                self.conf_is_correct = False
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
                        if self.read_config_silent == 0:
                            logger.info("Processing object config file '%s'", cfg_file_name)
                        res.write(os.linesep + '# IMPORTEDFROM=%s' % (cfg_file_name) + os.linesep)
                        res.write(file_d.read().decode('utf8', 'replace'))
                        # Be sure to add a line return so we won't mix files
                        res.write(os.linesep)
                        file_d.close()
                    except IOError, exp:
                        logger.error("Cannot open config file '%s' for reading: %s",
                                     cfg_file_name, exp)
                        # The configuration is invalid because we have a bad file!
                        self.conf_is_correct = False
                elif re.search("^cfg_dir", line):
                    elts = line.split('=', 1)
                    if os.path.isabs(elts[1]):
                        cfg_dir_name = elts[1]
                    else:
                        cfg_dir_name = os.path.join(self.config_base_dir, elts[1])
                    # Ok, look if it's really a directory
                    if not os.path.isdir(cfg_dir_name):
                        logger.error("Cannot open config dir '%s' for reading", cfg_dir_name)
                        self.conf_is_correct = False

                    # Look for .pack file into it :)
                    self.packs_dirs.append(cfg_dir_name)

                    # Now walk for it.
                    for root, dirs, files in os.walk(cfg_dir_name, followlinks=True):
                        for c_file in files:
                            if re.search(r"\.cfg$", c_file):
                                if self.read_config_silent == 0:
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
                                    logger.error("Cannot open config file '%s' for reading: %s",
                                                 os.path.join(root, c_file), exp)
                                    # The configuration is invalid
                                    # because we have a bad file!
                                    self.conf_is_correct = False
                elif re.search("^triggers_dir", line):
                    elts = line.split('=', 1)
                    if os.path.isabs(elts[1]):
                        trig_dir_name = elts[1]
                    else:
                        trig_dir_name = os.path.join(self.config_base_dir, elts[1])
                    # Ok, look if it's really a directory
                    if not os.path.isdir(trig_dir_name):
                        logger.error("Cannot open triggers dir '%s' for reading", trig_dir_name)
                        self.conf_is_correct = False
                        continue
                    # Ok it's a valid one, I keep it
                    self.triggers_dirs.append(trig_dir_name)

        config = res.getvalue()
        res.close()
        return config

#        self.read_config_buf(res)

    def read_config_buf(self, buf):
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
            # A define must be catch and the type save
            # The old entry must be save before
            elif re.search("^define", line) is not None:
                if re.search(r".*\{.*$", line) is not None:
                    in_define = True
                else:
                    almost_in_define = True

                if tmp_type not in objectscfg:
                    objectscfg[tmp_type] = []
                objectscfg[tmp_type].append(tmp)
                tmp = []
                tmp.append("imported_from " + filefrom + ':%d' % line_nb)
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

        # print "Params", params
        self.load_params(params)
        # And then update our MACRO dict
        self.fill_resource_macros_names_macros()

        for o_type in objectscfg:
            objects[o_type] = []
            for items in objectscfg[o_type]:
                tmp = {}
                for line in items:
                    elts = self._cut_line(line)
                    if elts == []:
                        continue
                    prop = elts[0]
                    if prop not in tmp:
                        tmp[prop] = []
                    value = ' '.join(elts[1:])
                    tmp[prop].append(value)
                if tmp != {}:
                    objects[o_type].append(tmp)

        return objects

    def add_ghost_objects(self, raw_objects):
        """Add fake command objects for internal processing ; bp_rule, _internal_host_up, _echo

        :param raw_objects: Raw config objects dict
        :type raw_objects: dict
        :return: raw_objects with 3 extras commands
        :rtype: dict
        """
        bp_rule = {'command_name': 'bp_rule', 'command_line': 'bp_rule'}
        raw_objects['command'].append(bp_rule)
        host_up = {'command_name': '_internal_host_up', 'command_line': '_internal_host_up'}
        raw_objects['command'].append(host_up)
        echo_obj = {'command_name': '_echo', 'command_line': '_echo'}
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
        :type type: object
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

        # Should look at hacking command_file module first
        self.hack_old_nagios_parameters_for_arbiter()

        # First fill default
        self.arbiters.fill_default()
        self.modules.fill_default()

        # print "****************** Linkify ******************"
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

        # print "Hosts"
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
        # print "Hostgroups"
        # link hostgroups with hosts
        self.hostgroups.linkify(self.hosts, self.realms)

        # print "Services"
        # link services with other objects
        self.services.linkify(self.hosts, self.commands,
                              self.timeperiods, self.contacts,
                              self.resultmodulations, self.businessimpactmodulations,
                              self.escalations, self.servicegroups,
                              self.triggers, self.checkmodulations,
                              self.macromodulations
                              )

        self.servicesextinfo.merge(self.services)

        # print "Service groups"
        # link servicegroups members with services
        self.servicegroups.linkify(self.hosts, self.services)

        # link notificationways with timeperiods and commands
        self.notificationways.linkify(self.timeperiods, self.commands)

        # link notificationways with timeperiods and commands
        self.checkmodulations.linkify(self.timeperiods, self.commands)

        # Link with timeperiods
        self.macromodulations.linkify(self.timeperiods)

        # print "Contactgroups"
        # link contacgroups with contacts
        self.contactgroups.linkify(self.contacts)

        # print "Contacts"
        # link contacts with timeperiods and commands
        self.contacts.linkify(self.timeperiods, self.commands,
                              self.notificationways)

        # print "Timeperiods"
        # link timeperiods with timeperiods (exclude part)
        self.timeperiods.linkify()

        # print "Servicedependency"
        self.servicedependencies.linkify(self.hosts, self.services,
                                         self.timeperiods)

        # print "Hostdependency"
        self.hostdependencies.linkify(self.hosts, self.timeperiods)
        # print "Resultmodulations"
        self.resultmodulations.linkify(self.timeperiods)

        self.businessimpactmodulations.linkify(self.timeperiods)

        # print "Escalations"
        self.escalations.linkify(self.timeperiods, self.contacts,
                                 self.services, self.hosts)

        # print "Realms"
        self.realms.linkify()

        # print "Schedulers and satellites"
        # Link all links with realms
        # self.arbiters.linkify(self.modules)
        self.schedulers.linkify(self.realms, self.modules)
        self.brokers.linkify(self.realms, self.modules)
        self.receivers.linkify(self.realms, self.modules)
        self.reactionners.linkify(self.realms, self.modules)
        self.pollers.linkify(self.realms, self.modules)

        # Ok, now update all realms with backlinks of
        # satellites
        self.realms.prepare_for_satellites_conf()

    def remove_exclusions(self):
        """Removes service exceptions based on host configuration

        :return:None
        """
        return self.services.remove_exclusions(self.hosts)

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
        # to call to sub-wrokers to do the job.
        # TODO : enable on windows? I'm not sure it will work, must give a test
        if os.name == 'nt' or not self.use_multiprocesses_serializer:
            logger.info('Using the default serialization pass')
            for realm in self.realms:
                for (i, conf) in realm.confs.iteritems():
                    # Remember to protect the local conf hostgroups too!
                    conf.hostgroups.prepare_for_sending()
                    logger.debug('[%s] Serializing the configuration %d', realm.get_name(), i)
                    t00 = time.time()
                    realm.serialized_confs[i] = cPickle.dumps(conf, 0)  # cPickle.HIGHEST_PROTOCOL)
                    logger.debug("[config] time to serialize the conf %s:%s is %s (size:%s)",
                                 realm.get_name(), i, time.time() - t00,
                                 len(realm.serialized_confs[i]))
                    logger.debug("PICKLE LEN : %d", len(realm.serialized_confs[i]))
            # Now pickle the whole conf, for easy and quick spare send
            t00 = time.time()
            whole_conf_pack = cPickle.dumps(self, cPickle.HIGHEST_PROTOCOL)
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
                        """Pickle the config. Used in subprocesses to pickle all config faster

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
                        res = cPickle.dumps(conf, cPickle.HIGHEST_PROTOCOL)
                        logger.debug("[config] time to serialize the conf %s:%s is %s (size:%s)",
                                     rname, cid, time.time() - t00, len(res))
                        comm_q.append((cid, res))

                    # Prepare a sub-process that will manage the pickle computation
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
                #  maybe one of the cildren got problems?
                if len(child_q) != len(realm.confs):
                    logger.error("Something goes wrong in the configuration serializations, "
                                 "please restart Alignak Arbiter")
                    sys.exit(2)
                # Now get the serialized configuration and saved them into self
                for (i, cfg) in child_q:
                    realm.serialized_confs[i] = cfg

            # Now pickle the whole configuration into one big pickle object, for the arbiter spares
            whole_queue = manager.list()
            t00 = time.time()

            def create_whole_conf_pack(whole_queue, self):
                """The function that just compute the whole conf pickle string, but n a children
                """
                logger.debug("[config] sub processing the whole configuration pack creation")
                whole_queue.append(cPickle.dumps(self, cPickle.HIGHEST_PROTOCOL))
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
            mailing_list_uri = "https://lists.sourceforge.net/lists/listinfo/alignak-devel"
            logger.warning("The following parameter(s) are not currently managed.")

            for line in unmanaged:
                logger.info(line)

            logger.warning("Unmanaged configuration statement, do you really need it?"
                           "Ask for it on the developer mailinglist %s or submit a pull "
                           "request on the Alignak github ", mailing_list_uri)

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
        # print "Contacts"
        self.contacts.explode(self.contactgroups, self.notificationways)
        # print "Contactgroups"
        self.contactgroups.explode()

        # print "Hosts"
        self.hosts.explode(self.hostgroups, self.contactgroups, self.triggers)

        # print "Hostgroups"
        self.hostgroups.explode()

        # print "Services"
        # print "Initially got nb of services: %d" % len(self.services.items)
        self.services.explode(self.hosts, self.hostgroups, self.contactgroups,
                              self.servicegroups, self.servicedependencies,
                              self.triggers)
        # print "finally got nb of services: %d" % len(self.services.items)
        # print "Servicegroups"
        self.servicegroups.explode()

        # print "Timeperiods"
        self.timeperiods.explode()

        self.hostdependencies.explode(self.hostgroups)

        # print "Servicedependency"
        self.servicedependencies.explode(self.hostgroups)

        # Serviceescalations hostescalations will create new escalations
        self.serviceescalations.explode(self.escalations)
        self.hostescalations.explode(self.escalations)
        self.escalations.explode(self.hosts, self.hostgroups,
                                 self.contactgroups)

        # Now the architecture part
        # print "Realms"
        self.realms.explode()

    def apply_dependencies(self):
        """Creates dependencies links between elements.

        :return: None
        """
        self.hosts.apply_dependencies()
        self.services.apply_dependencies()

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
        # print "Hosts"
        self.hosts.apply_inheritance()
        # print "Contacts"
        self.contacts.apply_inheritance()
        # print "Services"
        self.services.apply_inheritance()
        # print "Servicedependencies"
        self.servicedependencies.apply_inheritance()
        # print "Hostdependencies"
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
        # print "Services"
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
            default = Realm({'realm_name': 'Default', 'default': '1'})
            self.realms = Realms([default])
            logger.warning("No realms defined, I add one at %s", default.get_name())
            lists = [self.pollers, self.brokers, self.reactionners, self.receivers, self.schedulers]
            for lst in lists:
                for elt in lst:
                    if not hasattr(elt, 'realm'):
                        elt.realm = 'Default'
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

    def got_broker_module_type_defined(self, mod_type):
        """Check if a module type is defined in one of the brokers

        :param mod_type: module type to search
        :type mod_type: str
        :return: True if mod_type is found else False
        :rtype: bool
        """
        for broker in self.brokers:
            for module in broker.modules:
                if hasattr(module, 'module_type') and module.module_type == mod_type:
                    return True
        return False

    def got_scheduler_module_type_defined(self, mod_type):
        """Check if a module type is defined in one of the schedulers

        :param mod_type: module type to search
        :type mod_type: str
        :return: True if mod_type is found else False
        :rtype: bool
        TODO: Factorize it with got_broker_module_type_defined
        """
        for scheduler in self.schedulers:
            for module in scheduler.modules:
                if hasattr(module, 'module_type') and module.module_type == mod_type:
                    return True
        return False

    def got_arbiter_module_type_defined(self, mod_type):
        """Check if a module type is defined in one of the arbiters
        Also check the module_name

        :param mod_type: module type to search
        :type mod_type: str
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
                    if getattr(mod, 'module_type', '').strip() == mod_type.strip():
                        # if so, the good name?
                        if getattr(mod, 'module_name', '').strip() == module:
                            return True
        return False

    def create_business_rules(self):
        """Create business rules for hosts and services

        :return: None
        """
        self.hosts.create_business_rules(self.hosts, self.services)
        self.services.create_business_rules(self.hosts, self.services)

    def create_business_rules_dependencies(self):
        """Create business rules dependencies for hosts and services

        :return: None
        """
        self.hosts.create_business_rules_dependencies()
        self.services.create_business_rules_dependencies()

    def hack_old_nagios_parameters(self):
        """ Create some 'modules' from all nagios parameters if they are set and
        the modules are not created

        :return: None
        """
        # We list all modules we will add to brokers
        mod_to_add = []
        mod_to_add_to_schedulers = []

        # For status_dat
        if (hasattr(self, 'status_file') and
                self.status_file != '' and
                hasattr(self, 'object_cache_file')):
            # Ok, the user put such a value, we must look
            # if he forget to put a module for Brokers
            got_status_dat_module = self.got_broker_module_type_defined('status_dat')

            # We need to create the module on the fly?
            if not got_status_dat_module:
                data = {'object_cache_file': self.object_cache_file,
                        'status_file': self.status_file,
                        'module_name': 'Status-Dat-Autogenerated',
                        'module_type': 'status_dat'}
                mod = Module(data)
                mod.status_update_interval = getattr(self, 'status_update_interval', 15)
                mod_to_add.append(mod)

        # Now the log_file
        if hasattr(self, 'log_file') and self.log_file != '':
            # Ok, the user put such a value, we must look
            # if he forget to put a module for Brokers
            got_simple_log_module = self.got_broker_module_type_defined('simple_log')

            # We need to create the module on the fly?
            if not got_simple_log_module:
                data = {'module_type': 'simple_log', 'path': self.log_file,
                        'archive_path': self.log_archive_path,
                        'module_name': 'Simple-log-Autogenerated'}
                mod = Module(data)
                mod_to_add.append(mod)

        # Now the syslog facility
        if self.use_syslog:
            # Ok, the user want a syslog logging, why not after all
            got_syslog_module = self.got_broker_module_type_defined('syslog')

            # We need to create the module on the fly?
            if not got_syslog_module:
                data = {'module_type': 'syslog',
                        'module_name': 'Syslog-Autogenerated'}
                mod = Module(data)
                mod_to_add.append(mod)

        # Now the service_perfdata module
        if self.service_perfdata_file != '':
            # Ok, we've got a path for a service perfdata file
            got_service_perfdata_module = self.got_broker_module_type_defined('service_perfdata')

            # We need to create the module on the fly?
            if not got_service_perfdata_module:
                data = {'module_type': 'service_perfdata',
                        'module_name': 'Service-Perfdata-Autogenerated',
                        'path': self.service_perfdata_file,
                        'mode': self.service_perfdata_file_mode,
                        'template': self.service_perfdata_file_template}
                mod = Module(data)
                mod_to_add.append(mod)

        # Now the old retention file module
        if self.state_retention_file != '' and self.retention_update_interval != 0:
            # Ok, we've got a old retention file
            got_retention_file_module = \
                self.got_scheduler_module_type_defined('nagios_retention_file')

            # We need to create the module on the fly?
            if not got_retention_file_module:
                data = {'module_type': 'nagios_retention_file',
                        'module_name': 'Nagios-Retention-File-Autogenerated',
                        'path': self.state_retention_file}
                mod = Module(data)
                mod_to_add_to_schedulers.append(mod)

        # Now the host_perfdata module
        if self.host_perfdata_file != '':
            # Ok, we've got a path for a host perfdata file
            got_host_perfdata_module = self.got_broker_module_type_defined('host_perfdata')

            # We need to create the module on the fly?
            if not got_host_perfdata_module:
                data = {'module_type': 'host_perfdata',
                        'module_name': 'Host-Perfdata-Autogenerated',
                        'path': self.host_perfdata_file, 'mode': self.host_perfdata_file_mode,
                        'template': self.host_perfdata_file_template}
                mod = Module(data)
                mod_to_add.append(mod)

        # We add them to the brokers if we need it
        if mod_to_add != []:
            logger.warning("I autogenerated some Broker modules, please look at your configuration")
            for module in mod_to_add:
                logger.warning("The module %s is autogenerated", module.module_name)
                for broker in self.brokers:
                    broker.modules.append(module)

        # Then for schedulers
        if mod_to_add_to_schedulers != []:
            logger.warning("I autogenerated some Scheduler modules, "
                           "please look at your configuration")
            for module in mod_to_add_to_schedulers:
                logger.warning("The module %s is autogenerated", module.module_name)
                for scheduler in self.schedulers:
                    scheduler.modules.append(module)

    def hack_old_nagios_parameters_for_arbiter(self):
        """ Create some 'modules' from all nagios parameters if they are set and
        the modules are not created
        This one is only for arbiter

        :return: None
        TODO: Factorize with hack_old_nagios_parameters"""
        # We list all modules we will add to arbiters
        mod_to_add = []

        # For command_file
        if getattr(self, 'command_file', '') != '':
            # Ok, the user put such a value, we must look
            # if he forget to put a module for arbiters
            got_named_pipe_module = self.got_arbiter_module_type_defined('named_pipe')

            # We need to create the module on the fly?
            if not got_named_pipe_module:
                data = {'command_file': self.command_file,
                        'module_name': 'NamedPipe-Autogenerated',
                        'module_type': 'named_pipe'}
                mod = Module(data)
                mod_to_add.append((mod, data))

        # We add them to the brokers if we need it
        if mod_to_add != []:
            logger.warning("I autogenerated some Arbiter modules, "
                           "please look at your configuration")
            for (mod, data) in mod_to_add:
                logger.warning("Module %s was autogenerated", data['module_name'])
                for arb in self.arbiters:
                    arb.modules = getattr(arb, 'modules', []) + [data['module_name']]
                self.modules.add_item(mod)

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

    def is_correct(self):
        """Check if all elements got a good configuration

        :return: True if the configuration is correct else False
        :rtype: bool
        """
        logger.info('Running pre-flight check on configuration data...')
        valid = self.conf_is_correct

        # Globally unmanaged parameters
        if self.read_config_silent == 0:
            logger.info('Checking global parameters...')
        if not self.check_error_on_hard_unmanaged_parameters():
            valid = False
            logger.error("Check global parameters failed")

        for obj in ('hosts', 'hostgroups', 'contacts', 'contactgroups', 'notificationways',
                    'escalations', 'services', 'servicegroups', 'timeperiods', 'commands',
                    'hostsextinfo', 'servicesextinfo', 'checkmodulations', 'macromodulations',
                    'realms'):
            if self.read_config_silent == 0:
                logger.info('Checking %s...', obj)

            cur = getattr(self, obj)
            if not cur.is_correct():
                valid = False
                logger.error("\t%s conf incorrect!!", obj)
            if self.read_config_silent == 0:
                logger.info('\tChecked %d %s', len(cur), obj)

        # Hosts got a special check for loops
        if not self.hosts.no_loop_in_parents("self", "parents"):
            valid = False
            logger.error("Hosts: detected loop in parents ; conf incorrect")

        for obj in ('servicedependencies', 'hostdependencies', 'arbiters', 'schedulers',
                    'reactionners', 'pollers', 'brokers', 'receivers', 'resultmodulations',
                    'businessimpactmodulations'):
            try:
                cur = getattr(self, obj)
            except AttributeError:
                continue
            if self.read_config_silent == 0:
                logger.info('Checking %s...', obj)
            if not cur.is_correct():
                valid = False
                logger.error("\t%s conf incorrect!!", obj)
            if self.read_config_silent == 0:
                logger.info('\tChecked %d %s', len(cur), obj)

        # Look that all scheduler got a broker that will take brok.
        # If there are no, raise an Error
        for scheduler in self.schedulers:
            rea = scheduler.realm
            if rea:
                if len(rea.potential_brokers) == 0:
                    logger.error("The scheduler %s got no broker in its realm or upper",
                                 scheduler.get_name())
                    self.add_error("Error: the scheduler %s got no broker in its realm "
                                   "or upper" % scheduler.get_name())
                    valid = False

        # Check that for each poller_tag of a host, a poller exists with this tag
        # TODO: need to check that poller are in the good realm too
        hosts_tag = set()
        services_tag = set()
        pollers_tag = set()
        for host in self.hosts:
            hosts_tag.add(host.poller_tag)
        for scheduler in self.services:
            services_tag.add(scheduler.poller_tag)
        for poller in self.pollers:
            for tag in poller.poller_tags:
                pollers_tag.add(tag)
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
                    e_ro = item.get_realm()
                    # Something was wrong in the conf, will be raised elsewhere
                    if not e_ro:
                        continue
                    e_r = e_ro.realm_name
                    for elt in item.business_rule.list_all_elements():
                        r_o = elt.get_realm()
                        # Something was wrong in the conf, will be raised elsewhere
                        if not r_o:
                            continue
                        elt_r = elt.get_realm().realm_name
                        if not elt_r == e_r:
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

        :param txt: Text error
        :type txt: str
        :return: None
        """
        err = txt
        self.configuration_errors.append(err)

        self.conf_is_correct = False

    def show_errors(self):
        """Loop over configuration_errors and log them

        :return:  None
        """
        for err in self.configuration_errors:
            logger.error(err)

    def create_packs(self, nb_packs):
        """Create packs of hosts and services (all dependencies are resolved)
        It create a graph. All hosts are connected to their
        parents, and hosts without parent are connected to host 'root'.
        services are link to the host. Dependencies are managed
        REF: doc/pack-creation.pn

        :param nb_packs: the number of packs to create (number of scheduler basically)
        :type nb_packs: int
        :return: None
        """
        # We create a graph with host in nodes
        graph = Graph()
        graph.add_nodes(self.hosts)

        # links will be used for relations between hosts
        links = set()

        # Now the relations
        for host in self.hosts:
            # Add parent relations
            for parent in host.parents:
                if parent is not None:
                    links.add((parent, host))
            # Add the others dependencies
            for (dep, tmp, tmp2, tmp3, tmp4) in host.act_depend_of:
                links.add((dep, host))
            for (dep, tmp, tmp2, tmp3, tmp4) in host.chk_depend_of:
                links.add((dep, host))

        # For services: they are link with their own host but we need
        # To have the hosts of service dep in the same pack too
        for serv in self.services:
            for (dep, tmp, tmp2, tmp3, tmp4) in serv.act_depend_of:
                # I don't care about dep host: they are just the host
                # of the service...
                if hasattr(dep, 'host'):
                    links.add((dep.host, serv.host))
            # The other type of dep
            for (dep, tmp, tmp2, tmp3, tmp4) in serv.chk_depend_of:
                links.add((dep.host, serv.host))

        # For host/service that are business based, we need to
        # link them too
        for serv in [serv for serv in self.services if serv.got_business_rule]:
            for elem in serv.business_rule.list_all_elements():
                if hasattr(elem, 'host'):  # if it's a service
                    if elem.host != serv.host:  # do not a host with itself
                        links.add((elem.host, serv.host))
                else:  # it's already a host
                    if elem != serv.host:
                        links.add((elem, serv.host))

        # Same for hosts of course
        for host in [host for host in self.hosts if host.got_business_rule]:
            for elem in host.business_rule.list_all_elements():
                if hasattr(elem, 'host'):  # if it's a service
                    if elem.host != host:
                        links.add((elem.host, host))
                else:  # e is a host
                    if elem != host:
                        links.add((elem, host))

        # Now we create links in the graph. With links (set)
        # We are sure to call the less add_edge
        for (dep, host) in links:
            graph.add_edge(dep, host)
            graph.add_edge(host, dep)

        # Access_list from a node il all nodes that are connected
        # with it: it's a list of ours mini_packs
        tmp_packs = graph.get_accessibility_packs()

        # Now We find the default realm
        default_realm = None
        for realm in self.realms:
            if hasattr(realm, 'default') and realm.default:
                default_realm = realm

        # Now we look if all elements of all packs have the
        # same realm. If not, not good!
        for pack in tmp_packs:
            tmp_realms = set()
            for elt in pack:
                if elt.realm is not None:
                    tmp_realms.add(elt.realm)
            if len(tmp_realms) > 1:
                self.add_error("Error: the realm configuration of yours hosts is not good "
                               "because there a more than one realm in one pack (host relations):")
                for host in pack:
                    if host.realm is None:
                        err = '   the host %s do not have a realm' % host.get_name()
                        self.add_error(err)
                    else:
                        err = '   the host %s is in the realm %s' % (host.get_name(),
                                                                     host.realm.get_name())
                        self.add_error(err)
            if len(tmp_realms) == 1:  # Ok, good
                realm = tmp_realms.pop()  # There is just one element
                realm.packs.append(pack)
            elif len(tmp_realms) == 0:  # Hum.. no realm value? So default Realm
                if default_realm is not None:
                    default_realm.packs.append(pack)
                else:
                    err = ("Error: some hosts do not have a realm and you do not "
                           "defined a default realm!")
                    self.add_error(err)
                    for host in pack:
                        err = '    Impacted host: %s ' % host.get_name()
                        self.add_error(err)

        # The load balancing is for a loop, so all
        # hosts of a realm (in a pack) will be dispatch
        # in the schedulers of this realm
        # REF: doc/pack-agregation.png

        # Count the numbers of elements in all the realms, to compare it the total number of hosts
        nb_elements_all_realms = 0
        for realm in self.realms:
            # print "Load balancing realm", r.get_name()
            packs = {}
            # create roundrobin iterator for id of cfg
            # So dispatching is loadbalanced in a realm
            # but add a entry in the roundrobin tourniquet for
            # every weight point schedulers (so Weight round robin)
            weight_list = []
            no_spare_schedulers = [serv for serv in realm.schedulers if not serv.spare]
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
            for serv in no_spare_schedulers:
                packindices[serv._id] = packindex
                packindex += 1
                for i in xrange(0, serv.weight):
                    weight_list.append(serv._id)

            round_robin = itertools.cycle(weight_list)

            # We must have nb_schedulers packs
            for i in xrange(0, nb_schedulers):
                packs[i] = []

            # Try to load the history association dict so we will try to
            # send the hosts in the same "pack"
            assoc = {}

            # Now we explode the numerous packs into nb_packs reals packs:
            # we 'load balance' them in a roundrobin way
            for pack in realm.packs:
                valid_value = False
                old_pack = -1
                for elt in pack:
                    # print 'Look for host', elt.get_name(), 'in assoc'
                    old_i = assoc.get(elt.get_name(), -1)
                    # print 'Founded in ASSOC: ', elt.get_name(),old_i
                    # Maybe it's a new, if so, don't count it
                    if old_i == -1:
                        continue
                    # Maybe it is the first we look at, if so, take it's value
                    if old_pack == -1 and old_i != -1:
                        # print 'First value set', elt.get_name(), old_i
                        old_pack = old_i
                        valid_value = True
                        continue
                    if old_i == old_pack:
                        # print 'I found a match between elements', old_i
                        valid_value = True
                    if old_i != old_pack:
                        # print 'Outch found a change sorry', old_i, old_pack
                        valid_value = False
                # print 'Is valid?', elt.get_name(), valid_value, old_pack
                i = None
                # If it's a valid sub pack and the pack id really exist, use it!
                if valid_value and old_pack in packindices:
                    # print 'Use a old id for pack', old_pack, [h.get_name() for h in pack]
                    i = old_pack
                else:  # take a new one
                    # print 'take a new id for pack', [h.get_name() for h in pack]
                    i = round_robin.next()

                for elt in pack:
                    # print 'We got the element', elt.get_full_name(), ' in pack', i, packindices
                    packs[packindices[i]].append(elt)
                    assoc[elt.get_name()] = i

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

    def cut_into_parts(self):
        """Cut conf into part for scheduler dispatch.
        Basically it provide a set of host/services for each scheduler that
        have no dependencies between them

        :return:None
        """
        # print "Scheduler configured:", self.schedulers
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
            # print "Create Conf:", i, '/', nb_parts -1
            cur_conf = self.confs[i] = Config()

            # Now we copy all properties of conf into the new ones
            for prop, entry in Config.properties.items():
                if entry.managed and not isinstance(entry, UnusedProp):
                    val = getattr(self, prop)
                    setattr(cur_conf, prop, val)
                    # print "Copy", prop, val

            # we need a deepcopy because each conf
            # will have new hostgroups
            cur_conf._id = i
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
            cur_conf.contactgroups = self.contactgroups
            cur_conf.contacts = self.contacts
            cur_conf.triggers = self.triggers
            # Create hostgroups with just the name and same id, but no members
            new_servicegroups = []
            for servicegroup in self.servicegroups:
                new_servicegroups.append(servicegroup.copy_shell())
            cur_conf.servicegroups = Servicegroups(new_servicegroups)
            cur_conf.hosts = []  # will be fill after
            cur_conf.services = []  # will be fill after
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
        # REF: doc/pack-agregation.png
        offset = 0
        for realm in self.realms:
            for i in realm.packs:
                pack = realm.packs[i]
                for host in pack:
                    host.pack_id = i
                    self.confs[i + offset].hosts.append(host)
                    for serv in host.services:
                        self.confs[i + offset].services.append(serv)
                # Now the conf can be link in the realm
                realm.confs[i + offset] = self.confs[i + offset]
            offset += len(realm.packs)
            del realm.packs

        # We've nearly have hosts and services. Now we want REALS hosts (Class)
        # And we want groups too
        # print "Finishing packs"
        for i in self.confs:
            # print "Finishing pack Nb:", i
            cfg = self.confs[i]

            # Create ours classes
            cfg.hosts = Hosts(cfg.hosts)
            cfg.services = Services(cfg.services)
            # Fill host groups
            for ori_hg in self.hostgroups:
                hostgroup = cfg.hostgroups.find_by_name(ori_hg.get_name())
                mbrs = ori_hg.members
                mbrs_id = []
                for host in mbrs:
                    if host is not None:
                        mbrs_id.append(host._id)
                for host in cfg.hosts:
                    if host._id in mbrs_id:
                        hostgroup.members.append(host)

            # And also relink the hosts with the valid hostgroups
            for host in cfg.hosts:
                orig_hgs = host.hostgroups
                nhgs = []
                for ohg in orig_hgs:
                    nhg = cfg.hostgroups.find_by_name(ohg.get_name())
                    nhgs.append(nhg)
                host.hostgroups = nhgs

            # Fill servicegroup
            for ori_sg in self.servicegroups:
                servicegroup = cfg.servicegroups.find_by_name(ori_sg.get_name())
                mbrs = ori_sg.members
                mbrs_id = []
                for serv in mbrs:
                    if serv is not None:
                        mbrs_id.append(serv._id)
                for serv in cfg.services:
                    if serv._id in mbrs_id:
                        servicegroup.members.append(serv)

            # And also relink the services with the valid servicegroups
            for host in cfg.services:
                orig_hgs = host.servicegroups
                nhgs = []
                for ohg in orig_hgs:
                    nhg = cfg.servicegroups.find_by_name(ohg.get_name())
                    nhgs.append(nhg)
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

    def dump(self, f=None):
        """Dump configuration to a file in a JSON format

        :param f: the file to dump
        :type f: file
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
                         "schedulers",
                         "realms",
                         ):
            objs = [jsonify_r(i) for i in getattr(self, category)]
            container = getattr(self, category)
            if category == "services":
                objs = sorted(objs, key=lambda o: "%s/%s" %
                              (o["host_name"], o["service_description"]))
            elif hasattr(container, "name_property"):
                name_prop = container.name_property
                objs = sorted(objs, key=lambda o, prop=name_prop: getattr(o, prop, ''))
            dmp[category] = objs

        if f is None:
            temp_d = tempfile.gettempdir()
            path = os.path.join(temp_d, 'alignak-config-dump-%d' % time.time())
            f = open(path, "wb")
            close = True
        else:
            close = False
        f.write(
            json.dumps(
                dmp,
                indent=4,
                separators=(',', ': '),
                sort_keys=True
            )
        )
        if close is True:
            f.close()


def lazy():
    """Generate 256 User macros

    :return: None
    TODO: Should be removed
    """
    # let's compute the "USER" properties and macros..
    for i in xrange(1, 256):
        i = str(i)
        Config.properties['$USER' + str(i) + '$'] = StringProp(default='')
        Config.macros['USER' + str(i)] = '$USER' + i + '$'

lazy()
del lazy
