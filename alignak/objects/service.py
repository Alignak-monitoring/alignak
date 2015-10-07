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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Andreas Karfusehr, frescha@unitedseed.de
#     aviau, alexandre.viau@savoirfairelinux.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     François Lafont, flafdivers@free.fr
#     Sebastien Coavoux, s.coavoux@free.fr
#     Demelziraptor, demelza@circularvale.com
#     Jean Gabes, naparuba@gmail.com
#     Romain Forlot, rforlot@yahoo.com
#     Arthur Gautier, superbaloo@superbaloo.net
#     Frédéric MOHIER, frederic.mohier@ipmfrance.com
#     Frédéric Pégé, frederic.pege@gmail.com
#     Guillaume Bour, guillaume@bour.cc
#     Jean-Charles, jean-charles.delon@matricscom.eu
#     Jan Ulferts, jan.ulferts@xing.com
#     Grégory Starck, g.starck@gmail.com
#     Andrew McGilvray, amcgilvray@kixeye.com
#     Christophe Simon, geektophe@gmail.com
#     Pradeep Jindal, praddyjindal@gmail.com
#     Hubert, hubert.santuz@gmail.com
#     Alexander Springer, alex.spri@gmail.com
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

""" This Class is the service one, s it manage all service specific thing.
If you look at the scheduling part, look at the scheduling item class"""

import time
import re
import itertools


from alignak.objects.item import Items
from alignak.objects.schedulingitem import SchedulingItem

from alignak.autoslots import AutoSlots
from alignak.util import (
    strip_and_uniq,
    format_t_into_dhms_format,
    to_svc_hst_distinct_lists,
    generate_key_value_sequences,
    to_list_string_of_names,
    to_list_of_names,
    to_name_if_possible,
    is_complex_expr,
    KeyValueSyntaxError)
from alignak.property import BoolProp, IntegerProp, FloatProp,\
    CharProp, StringProp, ListProp, DictProp
from alignak.macroresolver import MacroResolver
from alignak.eventhandler import EventHandler
from alignak.log import logger, naglog_result


class Service(SchedulingItem):
    """Service class implements monitoring concepts for service.
    For example it defines parents, check_interval, check_command  etc.
    """
    # AutoSlots create the __slots__ with properties and
    # running_properties names
    __metaclass__ = AutoSlots

    # Every service have a unique ID, and 0 is always special in
    # database and co...
    _id = 1
    # The host and service do not have the same 0 value, now yes :)
    ok_up = 'OK'
    # used by item class for format specific value like for Broks
    my_type = 'service'

    # properties defined by configuration
    # required: is required in conf
    # default: default value if no set in conf
    # pythonize: function to call when transforming string to python object
    # fill_brok: if set, send to broker. there are two categories:
    #  full_status for initial and update status, check_result for check results
    # no_slots: do not take this property for __slots__
    properties = SchedulingItem.properties.copy()
    properties.update({
        'host_name':
            StringProp(fill_brok=['full_status', 'check_result', 'next_schedule']),
        'hostgroup_name':
            StringProp(default='', fill_brok=['full_status'], merging='join'),
        'service_description':
            StringProp(fill_brok=['full_status', 'check_result', 'next_schedule']),
        'display_name':
            StringProp(default='', fill_brok=['full_status']),
        'servicegroups':
            ListProp(default=[], fill_brok=['full_status'],
                     brok_transformation=to_list_string_of_names, merging='join'),
        'is_volatile':
            BoolProp(default=False, fill_brok=['full_status']),
        'check_command':
            StringProp(fill_brok=['full_status']),
        'initial_state':
            CharProp(default='o', fill_brok=['full_status']),
        'max_check_attempts':
            IntegerProp(default=1, fill_brok=['full_status']),
        'check_interval':
            IntegerProp(fill_brok=['full_status', 'check_result']),
        'retry_interval':
            IntegerProp(fill_brok=['full_status', 'check_result']),
        'active_checks_enabled':
            BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'passive_checks_enabled':
            BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'check_period':
            StringProp(brok_transformation=to_name_if_possible, fill_brok=['full_status']),
        'obsess_over_service':
            BoolProp(default=False, fill_brok=['full_status'], retention=True),
        'check_freshness':
            BoolProp(default=False, fill_brok=['full_status']),
        'freshness_threshold':
            IntegerProp(default=0, fill_brok=['full_status']),
        'event_handler':
            StringProp(default='', fill_brok=['full_status']),
        'event_handler_enabled':
            BoolProp(default=False, fill_brok=['full_status'], retention=True),
        'low_flap_threshold':
            IntegerProp(default=-1, fill_brok=['full_status']),
        'high_flap_threshold':
            IntegerProp(default=-1, fill_brok=['full_status']),
        'flap_detection_enabled':
            BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'flap_detection_options':
            ListProp(default=['o', 'w', 'c', 'u'], fill_brok=['full_status'], split_on_coma=True),
        'process_perf_data':
            BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'retain_status_information':
            BoolProp(default=True, fill_brok=['full_status']),
        'retain_nonstatus_information':
            BoolProp(default=True, fill_brok=['full_status']),
        'notification_interval':
            IntegerProp(default=60, fill_brok=['full_status']),
        'first_notification_delay':
            IntegerProp(default=0, fill_brok=['full_status']),
        'notification_period':
            StringProp(brok_transformation=to_name_if_possible, fill_brok=['full_status']),
        'notification_options':
            ListProp(default=['w', 'u', 'c', 'r', 'f', 's'],
                     fill_brok=['full_status'], split_on_coma=True),
        'notifications_enabled':
            BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'contacts':
            ListProp(default=[], brok_transformation=to_list_of_names,
                     fill_brok=['full_status'], merging='join'),
        'contact_groups':
            ListProp(default=[], fill_brok=['full_status'], merging='join'),
        'stalking_options':
            ListProp(default=[''], fill_brok=['full_status'], merging='join'),
        'notes':
            StringProp(default='', fill_brok=['full_status']),
        'notes_url':
            StringProp(default='', fill_brok=['full_status']),
        'action_url':
            StringProp(default='', fill_brok=['full_status']),
        'icon_image':
            StringProp(default='', fill_brok=['full_status']),
        'icon_image_alt':
            StringProp(default='', fill_brok=['full_status']),
        'icon_set':
            StringProp(default='', fill_brok=['full_status']),
        'failure_prediction_enabled':
            BoolProp(default=False, fill_brok=['full_status']),
        'parallelize_check':
            BoolProp(default=True, fill_brok=['full_status']),

        # Alignak specific
        'poller_tag':
            StringProp(default='None'),
        'reactionner_tag':
            StringProp(default='None'),
        'resultmodulations':
            ListProp(default=[], merging='join'),
        'business_impact_modulations':
            ListProp(default=[], merging='join'),
        'escalations':
            ListProp(default=[], fill_brok=['full_status'], merging='join', split_on_coma=True),
        'maintenance_period':
            StringProp(default='',
                       brok_transformation=to_name_if_possible, fill_brok=['full_status']),
        'time_to_orphanage':
            IntegerProp(default=300, fill_brok=['full_status']),
        'merge_host_contacts':
            BoolProp(default=False, fill_brok=['full_status']),
        'labels':
            ListProp(default=[], fill_brok=['full_status'], merging='join'),
        'host_dependency_enabled':
            BoolProp(default=True, fill_brok=['full_status']),

        # BUSINESS CORRELATOR PART
        # Business rules output format template
        'business_rule_output_template':
            StringProp(default='', fill_brok=['full_status']),
        # Business rules notifications mode
        'business_rule_smart_notifications':
            BoolProp(default=False, fill_brok=['full_status']),
        # Treat downtimes as acknowledgements in smart notifications
        'business_rule_downtime_as_ack':
            BoolProp(default=False, fill_brok=['full_status']),
        # Enforces child nodes notification options
        'business_rule_host_notification_options':
            ListProp(default=None, fill_brok=['full_status'], split_on_coma=True),
        'business_rule_service_notification_options':
            ListProp(default=None, fill_brok=['full_status'], split_on_coma=True),

        # Easy Service dep definition
        'service_dependencies':  # TODO: find a way to brok it?
            ListProp(default=None, merging='join', split_on_coma=True, keep_empty=True),

        # service generator
        'duplicate_foreach':
            StringProp(default=''),
        'default_value':
            StringProp(default=''),

        # Business_Impact value
        'business_impact':
            IntegerProp(default=2, fill_brok=['full_status']),

        # Load some triggers
        'trigger':
            StringProp(default=''),
        'trigger_name':
            StringProp(default=''),
        'trigger_broker_raise_enabled':
            BoolProp(default=False),

        # Trending
        'trending_policies':
            ListProp(default=[], fill_brok=['full_status'], merging='join'),

        # Our check ways. By defualt void, but will filled by an inner if need
        'checkmodulations':
            ListProp(default=[], fill_brok=['full_status'], merging='join'),
        'macromodulations':
            ListProp(default=[], merging='join'),

        # Custom views
        'custom_views':
            ListProp(default=[], fill_brok=['full_status'], merging='join'),

        # UI aggregation
        'aggregation':
            StringProp(default='', fill_brok=['full_status']),

        # Snapshot part
        'snapshot_enabled':
            BoolProp(default=False),
        'snapshot_command':
            StringProp(default=''),
        'snapshot_period':
            StringProp(default=''),
        'snapshot_criteria':
            ListProp(default=['w', 'c', 'u'], fill_brok=['full_status'], merging='join'),
        'snapshot_interval':
            IntegerProp(default=5),

    })

    # properties used in the running state
    running_properties = SchedulingItem.running_properties.copy()
    running_properties.update({
        'modified_attributes':
            IntegerProp(default=0L, fill_brok=['full_status'], retention=True),
        'last_chk':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'next_chk':
            IntegerProp(default=0, fill_brok=['full_status', 'next_schedule'], retention=True),
        'in_checking':
            BoolProp(default=False,
                     fill_brok=['full_status', 'check_result', 'next_schedule'], retention=True),
        'in_maintenance':
            IntegerProp(default=None, fill_brok=['full_status'], retention=True),
        'latency':
            FloatProp(default=0, fill_brok=['full_status', 'check_result'], retention=True,),
        'attempt':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'state':
            StringProp(default='OK',
                       fill_brok=['full_status', 'check_result'], retention=True),
        'state_id':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'current_event_id':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_event_id':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_state':
            StringProp(default='PENDING',
                       fill_brok=['full_status', 'check_result'], retention=True),
        'last_state_type':
            StringProp(default='HARD', fill_brok=['full_status', 'check_result'], retention=True),
        'last_state_id':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_state_change':
            FloatProp(default=0.0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_hard_state_change':
            FloatProp(default=0.0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_hard_state':
            StringProp(default='PENDING', fill_brok=['full_status'], retention=True),
        'last_hard_state_id':
            IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'last_time_ok':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_warning':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_critical':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_unknown':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'duration_sec':
            IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'state_type':
            StringProp(default='HARD', fill_brok=['full_status', 'check_result'], retention=True),
        'state_type_id':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'output':
            StringProp(default='', fill_brok=['full_status', 'check_result'], retention=True),
        'long_output':
            StringProp(default='', fill_brok=['full_status', 'check_result'], retention=True),
        'is_flapping':
            BoolProp(default=False, fill_brok=['full_status'], retention=True),
        #  dependencies for actions like notif of event handler,
        # so AFTER check return
        'act_depend_of':
            ListProp(default=[]),
        # dependencies for checks raise, so BEFORE checks
        'chk_depend_of':
            ListProp(default=[]),
        # elements that depend of me, so the reverse than just upper
        'act_depend_of_me':
            ListProp(default=[]),
        # elements that depend of me
        'chk_depend_of_me':
            ListProp(default=[]),

        'last_state_update':
            FloatProp(default=0.0, fill_brok=['full_status'], retention=True),
        # no brok because checks are too linked
        'checks_in_progress':
            ListProp(default=[]),
        # no broks because notifications are too linked
        'notifications_in_progress': DictProp(default={}, retention=True),
        'downtimes':
            ListProp(default=[], fill_brok=['full_status'], retention=True),
        'comments':
            ListProp(default=[], fill_brok=['full_status'], retention=True),
        'flapping_changes':
            ListProp(default=[], fill_brok=['full_status'], retention=True),
        'flapping_comment_id':
            IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'percent_state_change':
            FloatProp(default=0.0, fill_brok=['full_status', 'check_result'], retention=True),
        'problem_has_been_acknowledged':
            BoolProp(default=False, fill_brok=['full_status', 'check_result'], retention=True),
        'acknowledgement':
            StringProp(default=None, retention=True),
        'acknowledgement_type':
            IntegerProp(default=1, fill_brok=['full_status', 'check_result'], retention=True),
        'check_type':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'has_been_checked':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'should_be_scheduled':
            IntegerProp(default=1, fill_brok=['full_status'], retention=True),
        'last_problem_id':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'current_problem_id':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'execution_time':
            FloatProp(default=0.0, fill_brok=['full_status', 'check_result'], retention=True),
        'u_time':
            FloatProp(default=0.0),
        's_time':
            FloatProp(default=0.0),
        'last_notification':
            FloatProp(default=0.0, fill_brok=['full_status'], retention=True),
        'current_notification_number':
            IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'current_notification_id':
            IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'check_flapping_recovery_notification':
            BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'scheduled_downtime_depth':
            IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'pending_flex_downtime':
            IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'timeout':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'start_time':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'end_time':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'early_timeout':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'return_code':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'perf_data':
            StringProp(default='', fill_brok=['full_status', 'check_result'], retention=True),
        'last_perf_data':
            StringProp(default='', retention=True),
        'host':
            StringProp(default=None),
        'customs':
            DictProp(default={}, fill_brok=['full_status']),
        # Warning: for the notified_contacts retention save,
        # we save only the names of the contacts, and we should RELINK
        # them when we load it.
        # use for having all contacts we have notified
        'notified_contacts':  ListProp(default=set(),
                                       retention=True,
                                       retention_preparation=to_list_of_names),
        'in_scheduled_downtime': BoolProp(
            default=False, fill_brok=['full_status', 'check_result'], retention=True),
        'in_scheduled_downtime_during_last_check': BoolProp(default=False, retention=True),
        'actions':            ListProp(default=[]),  # put here checks and notif raised
        'broks':              ListProp(default=[]),  # and here broks raised


        # Problem/impact part
        'is_problem':         BoolProp(default=False, fill_brok=['full_status']),
        'is_impact':          BoolProp(default=False, fill_brok=['full_status']),
        # the save value of our business_impact for "problems"
        'my_own_business_impact':   IntegerProp(default=-1, fill_brok=['full_status']),
        # list of problems that make us an impact
        'source_problems':    ListProp(default=[],
                                       fill_brok=['full_status'],
                                       brok_transformation=to_svc_hst_distinct_lists),
        # list of the impact I'm the cause of
        'impacts':            ListProp(default=[],
                                       fill_brok=['full_status'],
                                       brok_transformation=to_svc_hst_distinct_lists),
        # keep a trace of the old state before being an impact
        'state_before_impact': StringProp(default='PENDING'),
        # keep a trace of the old state id before being an impact
        'state_id_before_impact': IntegerProp(default=0),
        # if the state change, we know so we do not revert it
        'state_changed_since_impact': BoolProp(default=False),

        # BUSINESS CORRELATOR PART
        # Say if we are business based rule or not
        'got_business_rule': BoolProp(default=False, fill_brok=['full_status']),
        # Previously processed business rule (with macro expanded)
        'processed_business_rule': StringProp(default="", fill_brok=['full_status']),
        # Our Dependency node for the business rule
        'business_rule': StringProp(default=None),


        # Here it's the elements we are depending on
        # so our parents as network relation, or a host
        # we are depending in a hostdependency
        # or even if we are business based.
        'parent_dependencies': StringProp(default=set(),
                                          brok_transformation=to_svc_hst_distinct_lists,
                                          fill_brok=['full_status']),
        # Here it's the guys that depend on us. So it's the total
        # opposite of the parent_dependencies
        'child_dependencies': StringProp(brok_transformation=to_svc_hst_distinct_lists,
                                         default=set(), fill_brok=['full_status']),

        # Manage the unknown/unreach during hard state
        'in_hard_unknown_reach_phase': BoolProp(default=False, retention=True),
        'was_in_hard_unknown_reach_phase': BoolProp(default=False, retention=True),
        'state_before_hard_unknown_reach_phase': StringProp(default='OK', retention=True),

        # Set if the element just change its father/son topology
        'topology_change': BoolProp(default=False, fill_brok=['full_status']),

        # Trigger list
        'triggers': ListProp(default=[]),

        # snapshots part
        'last_snapshot':  IntegerProp(default=0, fill_brok=['full_status'], retention=True),

        # Keep the string of the last command launched for this element
        'last_check_command': StringProp(default=''),

    })

    # Mapping between Macros and properties (can be prop or a function)
    macros = {
        'SERVICEDESC':            'service_description',
        'SERVICEDISPLAYNAME':     'display_name',
        'SERVICESTATE':           'state',
        'SERVICESTATEID':         'state_id',
        'LASTSERVICESTATE':       'last_state',
        'LASTSERVICESTATEID':     'last_state_id',
        'SERVICESTATETYPE':       'state_type',
        'SERVICEATTEMPT':         'attempt',
        'MAXSERVICEATTEMPTS':     'max_check_attempts',
        'SERVICEISVOLATILE':      'is_volatile',
        'SERVICEEVENTID':         'current_event_id',
        'LASTSERVICEEVENTID':     'last_event_id',
        'SERVICEPROBLEMID':       'current_problem_id',
        'LASTSERVICEPROBLEMID':   'last_problem_id',
        'SERVICELATENCY':         'latency',
        'SERVICEEXECUTIONTIME':   'execution_time',
        'SERVICEDURATION':        'get_duration',
        'SERVICEDURATIONSEC':     'get_duration_sec',
        'SERVICEDOWNTIME':        'get_downtime',
        'SERVICEPERCENTCHANGE':   'percent_state_change',
        'SERVICEGROUPNAME':       'get_groupname',
        'SERVICEGROUPNAMES':      'get_groupnames',
        'LASTSERVICECHECK':       'last_chk',
        'LASTSERVICESTATECHANGE': 'last_state_change',
        'LASTSERVICEOK':          'last_time_ok',
        'LASTSERVICEWARNING':     'last_time_warning',
        'LASTSERVICEUNKNOWN':     'last_time_unknown',
        'LASTSERVICECRITICAL':    'last_time_critical',
        'SERVICEOUTPUT':          'output',
        'LONGSERVICEOUTPUT':      'long_output',
        'SERVICEPERFDATA':        'perf_data',
        'LASTSERVICEPERFDATA':    'last_perf_data',
        'SERVICECHECKCOMMAND':    'get_check_command',
        'SERVICEACKAUTHOR':       'get_ack_author_name',
        'SERVICEACKAUTHORNAME':   'get_ack_author_name',
        'SERVICEACKAUTHORALIAS':  'get_ack_author_name',
        'SERVICEACKCOMMENT':      'get_ack_comment',
        'SERVICEACTIONURL':       'action_url',
        'SERVICENOTESURL':        'notes_url',
        'SERVICENOTES':           'notes',
        'SERVICEBUSINESSIMPACT':  'business_impact',
        # Business rules output formatting related macros
        'STATUS':                 'get_status',
        'SHORTSTATUS':            'get_short_status',
        'FULLNAME':               'get_full_name',
    }

    # This tab is used to transform old parameters name into new ones
    # so from Nagios2 format, to Nagios3 ones.
    # Or Alignak deprecated names like criticity
    old_properties = {
        'normal_check_interval':    'check_interval',
        'retry_check_interval':    'retry_interval',
        'criticity':    'business_impact',
        'hostgroup':    'hostgroup_name',
        'hostgroups':    'hostgroup_name',
        # 'criticitymodulations':    'business_impact_modulations',
    }

#######
#                   __ _                       _   _
#                  / _(_)                     | | (_)
#   ___ ___  _ __ | |_ _  __ _ _   _ _ __ __ _| |_ _  ___  _ __
#  / __/ _ \| '_ \|  _| |/ _` | | | | '__/ _` | __| |/ _ \| '_ \
# | (_| (_) | | | | | | | (_| | |_| | | | (_| | |_| | (_) | | | |
#  \___\___/|_| |_|_| |_|\__, |\__,_|_|  \__,_|\__|_|\___/|_| |_|
#                         __/ |
#                        |___/
######

    def fill_predictive_missing_parameters(self):
        """define state with initial_state

        :return: None
        """
        if self.initial_state == 'w':
            self.state = 'WARNING'
        elif self.initial_state == 'u':
            self.state = 'UNKNOWN'
        elif self.initial_state == 'c':
            self.state = 'CRITICAL'

    def __repr__(self):
        return '<Service host_name=%r desc=%r name=%r use=%r />' % (
            getattr(self, 'host_name', None),
            getattr(self, 'service_description', None),
            getattr(self, 'name', None),
            getattr(self, 'use', None)
        )
    __str__ = __repr__

    @property
    def unique_key(self):  # actually only used for (un)indexitem() via name_property..
        """Unique key for this service

        :return: Tuple with host_name and service_description
        :rtype: tuple
        """
        return (self.host_name, self.service_description)

    @property
    def display_name(self):
        """Display_name if defined, else service_description

        :return: service description or service display_name
        :rtype: str
        """
        display_name = getattr(self, '_display_name', None)
        if not display_name:
            return self.service_description
        return display_name

    @display_name.setter
    def display_name(self, display_name):
        """Setter for display_name attribute

        :param display_name: value to set
        :return: None
        """
        self._display_name = display_name

    def get_name(self):
        """Accessor to service_description attribute or name if first not defined

        :return: service name
        :rtype: str
        """
        if hasattr(self, 'service_description'):
            return self.service_description
        if hasattr(self, 'name'):
            return self.name
        return 'SERVICE-DESCRIPTION-MISSING'

    def get_groupnames(self):
        """Get servicegroups list

        :return: comma separated list of servicegroups
        :rtype: str
        """
        return ','.join([sg.get_name() for sg in self.servicegroups])

    def get_dbg_name(self):
        """Get the full name for debugging (host_name/service_description)

        :return: service full name
        :rtype: str
        TODO: Remove this function
        """
        return "%s/%s" % (self.host.host_name, self.service_description)

    def get_full_name(self):
        """Get the full name for debugging (host_name/service_description)

        :return: service full name
        :rtype: str
        """
        if self.host and hasattr(self.host, 'host_name') and hasattr(self, 'service_description'):
            return "%s/%s" % (self.host.host_name, self.service_description)
        return 'UNKNOWN-SERVICE'

    def get_realm(self):
        """Wrapper to access get_realm method of host attribute

        :return: service realm (host one)
        :rtype: None | alignak.objects.realm.Realm
        """
        if self.host is None:
            return None
        return self.host.get_realm()

    def get_hostgroups(self):
        """Wrapper to access hostgroups attribute of host attribute

        :return: service hostgroups (host one)
        :rtype: alignak.objects.hostgroup.Hostgroups
        """
        return self.host.hostgroups

    def get_host_tags(self):
        """Wrapper to access tags attribute of host attribute

        :return: service tags (host one)
        :rtype: alignak.objects.tag.Tags
        """
        return self.host.tags

    def get_service_tags(self):
        """Accessor to tags attribute

        :return: service tags
        :rtype: alignak.objects.tag.Tags
        """
        return self.tags

    def is_correct(self):
        """Check if this host configuration is correct ::

        * All required parameter are specified
        * Go through all configuration warnings and errors that could have been raised earlier

        :return: True if the configuration is correct, False otherwise
        :rtype: bool
        """
        state = True
        cls = self.__class__

        source = getattr(self, 'imported_from', 'unknown')

        desc = getattr(self, 'service_description', 'unnamed')
        hname = getattr(self, 'host_name', 'unnamed')

        special_properties = ('check_period', 'notification_interval', 'host_name',
                              'hostgroup_name', 'notification_period')

        for prop, entry in cls.properties.items():
            if prop not in special_properties:
                if not hasattr(self, prop) and entry.required:
                    logger.error("The service %s on host '%s' does not have %s", desc, hname, prop)
                    state = False  # Bad boy...

        # Then look if we have some errors in the conf
        # Juts print warnings, but raise errors
        for err in self.configuration_warnings:
            logger.warning("[service::%s] %s", desc, err)

        # Raised all previously saw errors like unknown contacts and co
        if self.configuration_errors != []:
            state = False
            for err in self.configuration_errors:
                logger.error("[service::%s] %s", self.get_full_name(), err)

        # If no notif period, set it to None, mean 24x7
        if not hasattr(self, 'notification_period'):
            self.notification_period = None

        # Ok now we manage special cases...
        if self.notifications_enabled and self.contacts == []:
            logger.warning("The service '%s' in the host '%s' does not have "
                           "contacts nor contact_groups in '%s'", desc, hname, source)

        # Set display_name if need
        if getattr(self, 'display_name', '') == '':
            self.display_name = getattr(self, 'service_description', '')

        # If we got an event handler, it should be valid
        if getattr(self, 'event_handler', None) and not self.event_handler.is_valid():
            logger.error("%s: my event_handler %s is invalid",
                         self.get_name(), self.event_handler.command)
            state = False

        if not hasattr(self, 'check_command'):
            logger.error("%s: I've got no check_command", self.get_name())
            state = False
        # Ok got a command, but maybe it's invalid
        else:
            if not self.check_command.is_valid():
                logger.error("%s: my check_command %s is invalid",
                             self.get_name(), self.check_command.command)
                state = False
            if self.got_business_rule:
                if not self.business_rule.is_valid():
                    logger.error("%s: my business rule is invalid", self.get_name(),)
                    for bperror in self.business_rule.configuration_errors:
                        logger.error("%s: %s", self.get_name(), bperror)
                    state = False
        if not hasattr(self, 'notification_interval') \
                and self.notifications_enabled is True:
            logger.error("%s: I've got no notification_interval but "
                         "I've got notifications enabled", self.get_name())
            state = False
        if not self.host_name:
            logger.error("The service '%s' is not bound do any host.", desc)
            state = False
        elif self.host is None:
            logger.error("The service '%s' got an unknown host_name '%s'.", desc, self.host_name)
            state = False

        if not hasattr(self, 'check_period'):
            self.check_period = None
        if hasattr(self, 'service_description'):
            for char in cls.illegal_object_name_chars:
                if char in self.service_description:
                    logger.error("%s: My service_description got the "
                                 "character %s that is not allowed.", self.get_name(), char)
                    state = False
        return state

    # TODO: implement "not host dependent" feature.
    def fill_daddy_dependency(self):
        """Add network act_dependency for host

        :return:None
        TODO: Host object should not handle other host obj.
              We should call obj.add_* on both obj.
              This is 'Java' style
        """
        #  Depend of host, all status, is a networkdep
        # and do not have timeperiod, and follow parents dep
        if self.host is not None and self.host_dependency_enabled:
            # I add the dep in MY list
            self.act_depend_of.append(
                (self.host, ['d', 'u', 's', 'f'], 'network_dep', None, True)
            )
            # I add the dep in Daddy list
            self.host.act_depend_of_me.append(
                (self, ['d', 'u', 's', 'f'], 'network_dep', None, True)
            )

            # And the parent/child dep lists too
            self.host.register_son_in_parent_child_dependencies(self)

    def add_service_act_dependency(self, srv, status, timeperiod, inherits_parent):
        """Add logical act_dependency between two services.

        :param srv: other service we want to add the dependency
        :type srv: alignak.objects.service.Service
        :param status: notification failure criteria, notification for a dependent host may vary
        :type status: list
        :param timeperiod: dependency period. Timeperiod for dependency may vary
        :type timeperiod: alignak.objects.timeperiod.Timeperiod
        :param inherits_parent: if this dep will inherit from parents (timeperiod, status)
        :type inherits_parent: bool
        :return: None
        TODO: Service object should not handle other host obj.
             We should call obj.add_* on both obj.
             This is 'Java' style
        TODO: Function seems to be asymmetric, (obj1.call1 , obj2.call1, obj2.call2)
        TODO: Looks like srv is a str when called. I bet it's a mistake.
        """
        # first I add the other the I depend on in MY list
        self.act_depend_of.append((srv, status, 'logic_dep', timeperiod, inherits_parent))
        # then I register myself in the other service dep list
        srv.act_depend_of_me.append((self, status, 'logic_dep', timeperiod, inherits_parent))

        # And the parent/child dep lists too
        srv.register_son_in_parent_child_dependencies(self)

    def add_business_rule_act_dependency(self, srv, status, timeperiod, inherits_parent):
        """Add business act_dependency between two services.

        :param srv: other service we want to add the dependency
        :type srv: alignak.objects.service.Service
        :param status: notification failure criteria, notification for a dependent host may vary
        :type status: list
        :param timeperiod: dependency period. Timeperiod for dependency may vary
        :type timeperiod: alignak.objects.timeperiod.Timeperiod
        :param inherits_parent: if this dep will inherit from parents (timeperiod, status)
        :type inherits_parent: bool
        :return: None
        TODO: Function seems to be asymmetric, (obj1.call1 , obj2.call1, obj2.call2)
        """
        # I only register so he know that I WILL be a impact
        self.act_depend_of_me.append((srv, status, 'business_dep',
                                      timeperiod, inherits_parent))

        # And the parent/child dep lists too
        self.register_son_in_parent_child_dependencies(srv)

    def add_service_chk_dependency(self, srv, status, timeperiod, inherits_parent):
        """Add logic chk_dependency between two services.

        :param srv: other service we want to add the dependency
        :type srv: alignak.objects.service.Service
        :param status: notification failure criteria, notification for a dependent host may vary
        :type status: list
        :param timeperiod: dependency period. Timeperiod for dependency may vary
        :type timeperiod: alignak.objects.timeperiod.Timeperiod
        :param inherits_parent: if this dep will inherit from parents (timeperiod, status)
        :type inherits_parent: bool
        :return: None
        TODO: Function seems to be asymmetric, (obj1.call1 , obj2.call1, obj2.call2)
        """
        # first I add the other the I depend on in MY list
        self.chk_depend_of.append((srv, status, 'logic_dep', timeperiod, inherits_parent))
        # then I register myself in the other service dep list
        srv.chk_depend_of_me.append(
            (self, status, 'logic_dep', timeperiod, inherits_parent)
        )

        # And the parent/child dep lists too
        srv.register_son_in_parent_child_dependencies(self)

    def duplicate(self, host):
        """For a given host, look for all copy we must create for for_each property

        :param host: alignak host object
        :type host: alignak.objects.host.Host
        :return: list
        :rtype: list
        """

        duplicates = []

        # In macro, it's all in UPPER case
        prop = self.duplicate_foreach.strip().upper()
        if prop not in host.customs:  # If I do not have the property, we bail out
            return duplicates

        # Get the list entry, and the not one if there is one
        entry = host.customs[prop]
        # Look at the list of the key we do NOT want maybe,
        # for _disks it will be _!disks
        not_entry = host.customs.get('_' + '!' + prop[1:], '').split(',')
        not_keys = strip_and_uniq(not_entry)

        default_value = getattr(self, 'default_value', '')
        # Transform the generator string to a list
        # Missing values are filled with the default value
        try:
            key_values = tuple(generate_key_value_sequences(entry, default_value))
        except KeyValueSyntaxError as exc:
            fmt_dict = {
                'prop': self.duplicate_foreach,
                'host': host.get_name(),
                'svc': self.service_description,
                'entry': entry,
                'exc': exc,
            }
            err = (
                "The custom property %(prop)r of the "
                "host %(host)r is not a valid entry for a service generator: %(exc)s, "
                "with entry=%(entry)r") % fmt_dict
            logger.warning(err)
            host.configuration_errors.append(err)
            return duplicates

        for key_value in key_values:
            key = key_value['KEY']
            # Maybe this key is in the NOT list, if so, skip it
            if key in not_keys:
                continue
            new_s = self.copy()
            new_s.host_name = host.get_name()
            if self.is_tpl():  # if template, the new one is not
                new_s.register = 1
            for key in key_value:
                if key == 'KEY':
                    if hasattr(self, 'service_description'):
                        # We want to change all illegal chars to a _ sign.
                        # We can't use class.illegal_obj_char
                        # because in the "explode" phase, we do not have access to this data! :(
                        safe_key_value = re.sub(r'[' + "`~!$%^&*\"|'<>?,()=" + ']+', '_',
                                                key_value[key])
                        new_s.service_description = self.service_description.replace(
                            '$' + key + '$', safe_key_value
                        )
                # Here is a list of property where we will expand the $KEY$ by the value
                _the_expandables = ['check_command', 'aggregation', 'event_handler']
                for prop in _the_expandables:
                    if hasattr(self, prop):
                        # here we can replace VALUE, VALUE1, VALUE2,...
                        setattr(new_s, prop, getattr(new_s, prop).replace('$' + key + '$',
                                                                          key_value[key]))
                if hasattr(self, 'service_dependencies'):
                    for i, servicedep in enumerate(new_s.service_dependencies):
                        new_s.service_dependencies[i] = servicedep.replace(
                            '$' + key + '$', key_value[key]
                        )
            # And then add in our list this new service
            duplicates.append(new_s)

        return duplicates

#####
#                         _
#                        (_)
#  _ __ _   _ _ __  _ __  _ _ __   __ _
# | '__| | | | '_ \| '_ \| | '_ \ / _` |
# | |  | |_| | | | | | | | | | | | (_| |
# |_|   \__,_|_| |_|_| |_|_|_| |_|\__, |
#                                  __/ |
#                                 |___/
####

    def set_unreachable(self):
        """Does nothing. Unreachable means nothing for a service

        :return: None
        """
        pass

    def set_impact_state(self):
        """We just go an impact, so we go unreachable
        But only if we enable this state change in the conf

        :return: None
        """
        cls = self.__class__
        if cls.enable_problem_impacts_states_change:
            # Keep a trace of the old state (problem came back before
            # a new checks)
            self.state_before_impact = self.state
            self.state_id_before_impact = self.state_id
            # this flag will know if we override the impact state
            self.state_changed_since_impact = False
            self.state = 'UNKNOWN'  # exit code UNDETERMINED
            self.state_id = 3

    def unset_impact_state(self):
        """Unset impact, only if impact state change is set in configuration

        :return: None
        """
        cls = self.__class__
        if cls.enable_problem_impacts_states_change and not self.state_changed_since_impact:
            self.state = self.state_before_impact
            self.state_id = self.state_id_before_impact

    def set_state_from_exit_status(self, status):
        """Set the state in UP, WARNING, CRITICAL or UNKNOWN
        with the status of a check. Also update last_state

        :param status: integer between 0 and 3
        :type status: int
        :return: None
        """
        now = time.time()
        self.last_state_update = now

        # we should put in last_state the good last state:
        # if not just change the state by an problem/impact
        # we can take current state. But if it's the case, the
        # real old state is self.state_before_impact (it's the TRUE
        # state in fact)
        # but only if the global conf have enable the impact state change
        cls = self.__class__
        if cls.enable_problem_impacts_states_change \
                and self.is_impact \
                and not self.state_changed_since_impact:
            self.last_state = self.state_before_impact
        else:  # standard case
            self.last_state = self.state

        if status == 0:
            self.state = 'OK'
            self.state_id = 0
            self.last_time_ok = int(self.last_state_update)
            state_code = 'o'
        elif status == 1:
            self.state = 'WARNING'
            self.state_id = 1
            self.last_time_warning = int(self.last_state_update)
            state_code = 'w'
        elif status == 2:
            self.state = 'CRITICAL'
            self.state_id = 2
            self.last_time_critical = int(self.last_state_update)
            state_code = 'c'
        elif status == 3:
            self.state = 'UNKNOWN'
            self.state_id = 3
            self.last_time_unknown = int(self.last_state_update)
            state_code = 'u'
        else:
            self.state = 'CRITICAL'  # exit code UNDETERMINED
            self.state_id = 2
            self.last_time_critical = int(self.last_state_update)
            state_code = 'c'

        if state_code in self.flap_detection_options:
            self.add_flapping_change(self.state != self.last_state)

        if self.state != self.last_state:
            self.last_state_change = self.last_state_update

        self.duration_sec = now - self.last_state_change

    def is_state(self, status):
        """Return if status match the current service status

        :param status: status to compare ( "o", "c", "w", "u"). Usually comes from config files
        :type status: str
        :return: True if status <=> self.status, otherwise False
        :rtype: bool
        """
        if status == self.state:
            return True
        # Now low status
        elif status == 'o' and self.state == 'OK':
            return True
        elif status == 'c' and self.state == 'CRITICAL':
            return True
        elif status == 'w' and self.state == 'WARNING':
            return True
        elif status == 'u' and self.state == 'UNKNOWN':
            return True
        return False

    def last_time_non_ok_or_up(self):
        """Get the last time the service was in a non-OK state

        :return: self.last_time_down if self.last_time_down > self.last_time_up, otherwise 0
        :rtype: int
        """
        non_ok_times = [x for x in [self.last_time_warning,
                                    self.last_time_critical,
                                    self.last_time_unknown]
                        if x > self.last_time_ok]
        if len(non_ok_times) == 0:
            last_time_non_ok = 0  # program_start would be better
        else:
            last_time_non_ok = min(non_ok_times)
        return last_time_non_ok

    def raise_alert_log_entry(self):
        """Raise SERVICE ALERT entry (critical level)
        Format is : "SERVICE ALERT: *host.get_name()*;*get_name()*;*state*;*state_type*;*attempt*
                    ;*output*"
        Example : "SERVICE ALERT: server;Load;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        naglog_result('critical', 'SERVICE ALERT: %s;%s;%s;%s;%d;%s'
                                  % (self.host.get_name(), self.get_name(),
                                     self.state, self.state_type,
                                     self.attempt, self.output))

    def raise_initial_state(self):
        """Raise SERVICE HOST ALERT entry (info level)
        Format is : "SERVICE HOST STATE: *host.get_name()*;*get_name()*;*state*;*state_type*
                    ;*attempt*;*output*"
        Example : "SERVICE HOST STATE: server;Load;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        if self.__class__.log_initial_states:
            naglog_result('info', 'CURRENT SERVICE STATE: %s;%s;%s;%s;%d;%s'
                                  % (self.host.get_name(), self.get_name(),
                                     self.state, self.state_type, self.attempt, self.output))

    def raise_freshness_log_entry(self, t_stale_by, t_threshold):
        """Raise freshness alert entry (warning level)
        Format is : "The results of service '*get_name()*' on host '*host.get_name()*'
                    are stale by *t_stale_by* (threshold=*t_threshold*).
                    I'm forcing an immediate check of the service."
        Example : "Warning: The results of service 'Load' on host 'Server' are stale by 0d 0h 0m 58s
                   (threshold=0d 1h 0m 0s). ..."

        :param t_stale_by: time in seconds the service has been in a stale state
        :type t_stale_by: int
        :param t_threshold: threshold (seconds) to trigger this log entry
        :type t_threshold: int
        :return: None
        """
        logger.warning("The results of service '%s' on host '%s' are stale "
                       "by %s (threshold=%s).  I'm forcing an immediate check "
                       "of the service.",
                       self.get_name(), self.host.get_name(),
                       format_t_into_dhms_format(t_stale_by),
                       format_t_into_dhms_format(t_threshold))

    def raise_notification_log_entry(self, notif):
        """Raise SERVICE NOTIFICATION entry (critical level)
        Format is : "SERVICE NOTIFICATION: *contact.get_name()*;*host.get_name()*;*self.get_name()*
                    ;*state*;*command.get_name()*;*output*"
        Example : "SERVICE NOTIFICATION: superadmin;server;Load;UP;notify-by-rss;no output"

        :param notif: notification object created by service alert
        :type notif: alignak.objects.notification.Notification
        :return: None
        """
        contact = notif.contact
        command = notif.command_call
        if notif.type in ('DOWNTIMESTART', 'DOWNTIMEEND', 'DOWNTIMECANCELLED',
                          'CUSTOM', 'ACKNOWLEDGEMENT', 'FLAPPINGSTART',
                          'FLAPPINGSTOP', 'FLAPPINGDISABLED'):
            state = '%s (%s)' % (notif.type, self.state)
        else:
            state = self.state
        if self.__class__.log_notifications:
            naglog_result('critical', "SERVICE NOTIFICATION: %s;%s;%s;%s;%s;%s"
                                      % (contact.get_name(),
                                         self.host.get_name(), self.get_name(), state,
                                         command.get_name(), self.output))

    def raise_event_handler_log_entry(self, command):
        """Raise SERVICE EVENT HANDLER entry (critical level)
        Format is : "SERVICE EVENT HANDLER: *host.get_name()*;*self.get_name()*;*state*;*state_type*
                    ;*attempt*;*command.get_name()*"
        Example : "SERVICE EVENT HANDLER: server;Load;UP;HARD;1;notify-by-rss"

        :param command: Handler launched
        :type command: alignak.objects.command.Command
        :return: None
        """
        if self.__class__.log_event_handlers:
            naglog_result('critical', "SERVICE EVENT HANDLER: %s;%s;%s;%s;%s;%s"
                                      % (self.host.get_name(), self.get_name(),
                                         self.state, self.state_type,
                                         self.attempt, command.get_name()))

    def raise_snapshot_log_entry(self, command):
        """Raise SERVICE SNAPSHOT entry (critical level)
        Format is : "SERVICE SNAPSHOT: *host.get_name()*;*self.get_name()*;*state*;*state_type*;
                    *attempt*;*command.get_name()*"
        Example : "SERVICE SNAPSHOT: server;Load;UP;HARD;1;notify-by-rss"

        :param command: Snapshot command launched
        :type command: alignak.objects.command.Command
        :return: None
        """
        if self.__class__.log_event_handlers:
            naglog_result('critical', "SERVICE SNAPSHOT: %s;%s;%s;%s;%s;%s"
                          % (self.host.get_name(), self.get_name(),
                             self.state, self.state_type, self.attempt, command.get_name()))

    def raise_flapping_start_log_entry(self, change_ratio, threshold):
        """Raise SERVICE FLAPPING ALERT START entry (critical level)
        Format is : "SERVICE FLAPPING ALERT: *host.get_name()*;*self.get_name()*;STARTED;
                     Service appears to have started
                     flapping (*change_ratio*% change >= *threshold*% threshold)"
        Example : "SERVICE FLAPPING ALERT: server;Load;STARTED;
                   Service appears to have started
                   flapping (50.6% change >= 50.0% threshold)"

        :param change_ratio: percent of changing state
        :param threshold: threshold (percent) to trigger this log entry
        :return: None
        """
        naglog_result('critical', "SERVICE FLAPPING ALERT: %s;%s;STARTED; "
                                  "Service appears to have started flapping "
                                  "(%.1f%% change >= %.1f%% threshold)"
                                  % (self.host.get_name(), self.get_name(),
                                     change_ratio, threshold))

    def raise_flapping_stop_log_entry(self, change_ratio, threshold):
        """Raise SERVICE FLAPPING ALERT STOPPED entry (critical level)
        Format is : "SERVICE FLAPPING ALERT: *host.get_name()*;*self.get_name()*;STOPPED;
                     Service appears to have started
                     flapping (*change_ratio*% change >= *threshold*% threshold)"
        Example : "SERVICE FLAPPING ALERT: server;Load;STOPPED;
                   Service appears to have started
                   flapping (50.6% change >= 50.0% threshold)"

        :param change_ratio: percent of changing state
        :type change_ratio: float
        :param threshold: threshold (percent) to trigger this log entry
        :type threshold: float
        :return: None
        """
        naglog_result('critical', "SERVICE FLAPPING ALERT: %s;%s;STOPPED; "
                                  "Service appears to have stopped flapping "
                                  "(%.1f%% change < %.1f%% threshold)"
                                  % (self.host.get_name(), self.get_name(),
                                     change_ratio, threshold))

    def raise_no_next_check_log_entry(self):
        """Raise no scheduled check entry (warning level)
        Format is : "I cannot schedule the check for the service '*get_name()*'
                    on host '*host.get_name()*' because there is not future valid time"
        Example : "I cannot schedule the check for the service 'Load' on host 'Server'
                  because there is not future valid time"

        :return: None
        """
        logger.warning("I cannot schedule the check for the service '%s' on "
                       "host '%s' because there is not future valid time",
                       self.get_name(), self.host.get_name())

    def raise_enter_downtime_log_entry(self):
        """Raise SERVICE DOWNTIME ALERT entry (critical level)
        Format is : "SERVICE DOWNTIME ALERT: *host.get_name()*;*get_name()*;STARTED;
                    Service has entered a period of scheduled downtime"
        Example : "SERVICE DOWNTIME ALERT: test_host_0;Load;STARTED;
                   Service has entered a period of scheduled downtime"

        :return: None
        """
        naglog_result('critical', "SERVICE DOWNTIME ALERT: %s;%s;STARTED; "
                                  "Service has entered a period of scheduled "
                                  "downtime" % (self.host.get_name(), self.get_name()))

    def raise_exit_downtime_log_entry(self):
        """Raise SERVICE DOWNTIME ALERT entry (critical level)
        Format is : "SERVICE DOWNTIME ALERT: *host.get_name()*;*get_name()*;STOPPED;
                    Service has entered a period of scheduled downtime"
        Example : "SERVICE DOWNTIME ALERT: test_host_0;Load;STOPPED;
                   Service has entered a period of scheduled downtime"

        :return: None
        """
        naglog_result('critical', "SERVICE DOWNTIME ALERT: %s;%s;STOPPED; Service "
                                  "has exited from a period of scheduled downtime"
                      % (self.host.get_name(), self.get_name()))

    def raise_cancel_downtime_log_entry(self):
        """Raise SERVICE DOWNTIME ALERT entry (critical level)
        Format is : "SERVICE DOWNTIME ALERT: *host.get_name()*;*get_name()*;CANCELLED;
                    Service has entered a period of scheduled downtime"
        Example : "SERVICE DOWNTIME ALERT: test_host_0;Load;CANCELLED;
                   Service has entered a period of scheduled downtime"

        :return: None
        """
        naglog_result(
            'critical', "SERVICE DOWNTIME ALERT: %s;%s;CANCELLED; "
                        "Scheduled downtime for service has been cancelled."
            % (self.host.get_name(), self.get_name()))

    def manage_stalking(self, check):
        """Check if the service need stalking or not (immediate recheck)
        If one stalking_options matches the exit_status ('o' <=> 0 ...) then stalk is needed
        Raise a log entry (info level) if stalk is needed

        :param check: finshed check (check.status == 'waitconsume')
        :type check: alignak.check.Check
        :return: None
        """
        need_stalk = False
        if check.status == 'waitconsume':
            if check.exit_status == 0 and 'o' in self.stalking_options:
                need_stalk = True
            elif check.exit_status == 1 and 'w' in self.stalking_options:
                need_stalk = True
            elif check.exit_status == 2 and 'check' in self.stalking_options:
                need_stalk = True
            elif check.exit_status == 3 and 'u' in self.stalking_options:
                need_stalk = True

            if check.output == self.output:
                need_stalk = False
        if need_stalk:
            logger.info("Stalking %s: %s", self.get_name(), check.output)

    def get_data_for_checks(self):
        """Get data for a check

        :return: list containing the service and the linked host
        :rtype: list
        """
        return [self.host, self]

    def get_data_for_event_handler(self):
        """Get data for an event handler

        :return: list containing the service and the linked host
        :rtype: list
        """
        return [self.host, self]

    def get_data_for_notifications(self, contact, notif):
        """Get data for a notification

        :param contact: The contact to return
        :type contact:
        :param notif: the notification to return
        :type notif:
        :return: list containing the service, the host and the given parameters
        :rtype: list
        """
        return [self.host, self, contact, notif]

    def notification_is_blocked_by_contact(self, notif, contact):
        """Check if the notification is blocked by this contact.

        :param notif: notification created earlier
        :type notif: alignak.notification.Notification
        :param contact: contact we want to notify
        :type notif: alignak.objects.contact.Contact
        :return: True if the notification is blocked, False otherwise
        :rtype: bool
        """
        return not contact.want_service_notification(self.last_chk, self.state,
                                                     notif.type, self.business_impact,
                                                     notif.command_call)

    def get_duration_sec(self):
        """Get duration in seconds. (cast it before returning)

        :return: duration in seconds
        :rtype: int
        TODO: Move to util or SchedulingItem class
        """
        return str(int(self.duration_sec))

    def get_duration(self):
        """Get duration formatted
        Format is : "HHh MMm SSs"
        Example : "10h 20m 40s"

        :return: Formatted duration
        :rtype: str
        TODO: Move to util or SchedulingItem class
        """
        mins, secs = divmod(self.duration_sec, 60)
        hours, mins = divmod(mins, 60)
        return "%02dh %02dm %02ds" % (hours, mins, secs)

    def get_ack_author_name(self):
        """Get the author of the acknowledgement

        :return: author
        :rtype: str
        TODO: use getattr(self.acknowledgement, "author", '') instead
        TODO: Move to util or SchedulingItem class
        """
        if self.acknowledgement is None:
            return ''
        return self.acknowledgement.author

    def get_ack_comment(self):
        """Get the comment of the acknowledgement

        :return: comment
        :rtype: str
        TODO: use getattr(self.acknowledgement, "comment", '') instead
        TODO: Move to util or SchedulingItem class
        """
        if self.acknowledgement is None:
            return ''
        return self.acknowledgement.comment

    def get_check_command(self):
        """Wrapper to get the name of the check_command attribute

        :return: check_command name
        :rtype: str
        TODO: Move to util or SchedulingItem class
        """
        return self.check_command.get_name()

    def notification_is_blocked_by_item(self, n_type, t_wished=None):
        """Check if a notification is blocked by the service.
        Conditions are ONE of the following::

        * enable_notification is False (global)
        * not in a notification_period
        * notifications_enable is False (local)
        * notification_options is 'n' or matches the state ('UNKNOWN' <=> 'u' ...)
          (include flapping and downtimes)
        * state goes ok and type is 'ACKNOWLEDGEMENT' (no sense)
        * scheduled_downtime_depth > 0 and flapping (host is in downtime)
        * scheduled_downtime_depth > 1 and not downtime end (deep downtime)
        * scheduled_downtime_depth > 0 and problem or recovery (host is in downtime)
        * SOFT state of a problem (we raise notification ony on HARD state)
        * ACK notification when already ACK (don't raise again ACK)
        * not flapping notification in a flapping state
        * business rule smart notifications is enabled and all its children have been acknowledged
          or are under downtime
        * linked host is not up
        * linked host is in downtime

        :param n_type: notification type
        :type n_type:
        :param t_wished: the time we should like to notify the host (mostly now)
        :type t_wished: float
        :return: True if ONE of the above condition was met, otherwise False
        :rtype: bool
        TODO: Refactor this, a lot of code duplication with Host.notification_is_blocked_by_item
        """
        if t_wished is None:
            t_wished = time.time()

        #  TODO
        # forced notification
        # pass if this is a custom notification

        # Block if notifications are program-wide disabled
        if not self.enable_notifications:
            return True

        # Does the notification period allow sending out this notification?
        if self.notification_period is not None \
                and not self.notification_period.is_time_valid(t_wished):
            return True

        # Block if notifications are disabled for this service
        if not self.notifications_enabled:
            return True

        # Block if the current status is in the notification_options w,u,c,r,f,s
        if 'n' in self.notification_options:
            return True
        if n_type in ('PROBLEM', 'RECOVERY'):
            if self.state == 'UNKNOWN' and 'u' not in self.notification_options:
                return True
            if self.state == 'WARNING' and 'w' not in self.notification_options:
                return True
            if self.state == 'CRITICAL' and 'c' not in self.notification_options:
                return True
            if self.state == 'OK' and 'r' not in self.notification_options:
                return True
        if (n_type in ('FLAPPINGSTART', 'FLAPPINGSTOP', 'FLAPPINGDISABLED')
                and 'f' not in self.notification_options):
            return True
        if (n_type in ('DOWNTIMESTART', 'DOWNTIMEEND', 'DOWNTIMECANCELLED')
                and 's' not in self.notification_options):
            return True

        # Acknowledgements make no sense when the status is ok/up
        if n_type == 'ACKNOWLEDGEMENT':
            if self.state == self.ok_up:
                return True

        # When in downtime, only allow end-of-downtime notifications
        if self.scheduled_downtime_depth > 1 and n_type not in ('DOWNTIMEEND', 'DOWNTIMECANCELLED'):
            return True

        # Block if host is in a scheduled downtime
        if self.host.scheduled_downtime_depth > 0:
            return True

        # Block if in a scheduled downtime and a problem arises, or flapping event
        if self.scheduled_downtime_depth > 0 and n_type in \
                ('PROBLEM', 'RECOVERY', 'FLAPPINGSTART', 'FLAPPINGSTOP', 'FLAPPINGDISABLED'):
            return True

        # Block if the status is SOFT
        if self.state_type == 'SOFT' and n_type == 'PROBLEM':
            return True

        # Block if the problem has already been acknowledged
        if self.problem_has_been_acknowledged and n_type != 'ACKNOWLEDGEMENT':
            return True

        # Block if flapping
        if self.is_flapping and n_type not in ('FLAPPINGSTART', 'FLAPPINGSTOP', 'FLAPPINGDISABLED'):
            return True

        # Block if host is down
        if self.host.state != self.host.ok_up:
            return True

        # Block if business rule smart notifications is enabled and all its
        # childs have been acknowledged or are under downtime.
        if self.got_business_rule is True \
                and self.business_rule_smart_notifications is True \
                and self.business_rule_notification_is_blocked() is True \
                and n_type == 'PROBLEM':
            return True

        return False

    def get_obsessive_compulsive_processor_command(self):
        """Create action for obsessive compulsive commands if such option is enabled

        :return: None
        """
        cls = self.__class__
        if not cls.obsess_over or not self.obsess_over_service:
            return

        macroresolver = MacroResolver()
        data = self.get_data_for_event_handler()
        cmd = macroresolver.resolve_command(cls.ocsp_command, data)
        event_h = EventHandler(cmd, timeout=cls.ocsp_timeout)

        # ok we can put it in our temp action queue
        self.actions.append(event_h)

    def get_short_status(self):
        """Get the short status of this host

        :return: "O", "W", "C", "U', or "n/a" based on service state_id or business_rule state
        :rtype: str
        """
        mapping = {
            0: "O",
            1: "W",
            2: "C",
            3: "U",
        }
        if self.got_business_rule:
            return mapping.get(self.business_rule.get_state(), "n/a")
        else:
            return mapping.get(self.state_id, "n/a")

    def get_status(self):
        """Get the status of this host

        :return: "OK", "WARNING", "CRITICAL", "UNKNOWN" or "n/a" based on
                 service state_id or business_rule state
        :rtype: str
        """

        if self.got_business_rule:
            mapping = {
                0: "OK",
                1: "WARNING",
                2: "CRITICAL",
                3: "UNKNOWN",
            }
            return mapping.get(self.business_rule.get_state(), "n/a")
        else:
            return self.state

    def get_downtime(self):
        """Accessor to scheduled_downtime_depth attribue

        :return: scheduled downtime depth
        :rtype: str
        TODO: Move to util or SchedulingItem class
        """
        return str(self.scheduled_downtime_depth)


class Services(Items):
    """Class for the services lists. It's mainly for configuration

    """
    name_property = 'unique_key'  # only used by (un)indexitem (via 'name_property')
    inner_class = Service  # use for know what is in items

    def __init__(self, items, index_items=True):
        self.partial_services = {}
        self.name_to_partial = {}
        super(Services, self).__init__(items, index_items)

    def add_template(self, tpl):
        """
        Adds and index a template into the `templates` container.

        This implementation takes into account that a service has two naming
        attribute: `host_name` and `service_description`.

        :param tpl: The template to add
        :type tpl:
        :return: None
        """
        objcls = self.inner_class.my_type
        name = getattr(tpl, 'name', '')
        hname = getattr(tpl, 'host_name', '')
        if not name and not hname:
            mesg = "a %s template has been defined without name nor " \
                   "host_name%s" % (objcls, self.get_source(tpl))
            tpl.configuration_errors.append(mesg)
        elif name:
            tpl = self.index_template(tpl)
        self.templates[tpl._id] = tpl

    def add_item(self, item, index=True, was_partial=False):
        """
        Adds and index an item into the `items` container.

        This implementation takes into account that a service has two naming
        attribute: `host_name` and `service_description`.

        :param item: The item to add
        :type item:
        :param index: Flag indicating if the item should be indexed
        :type index: bool
        :param was_partial: True if was partial, otherwise False
        :type was_partial: bool
        :return: None
        """
        objcls = self.inner_class.my_type
        hname = getattr(item, 'host_name', '')
        hgname = getattr(item, 'hostgroup_name', '')
        sdesc = getattr(item, 'service_description', '')
        source = getattr(item, 'imported_from', 'unknown')
        if source:
            in_file = " in %s" % source
        else:
            in_file = ""
        if not hname and not hgname and not sdesc:
            mesg = "a %s has been defined without host_name nor " \
                   "hostgroups nor service_description%s" % (objcls, in_file)
            item.configuration_errors.append(mesg)
        elif not sdesc or sdesc and not hgname and not hname and not was_partial:
            self.add_partial_service(item, index, (objcls, hname, hgname, sdesc, in_file))
            return

        if index is True:
            item = self.index_item(item)
        self.items[item._id] = item

    def add_partial_service(self, item, index=True, var_tuple=tuple()):
        """Add a partial service.
        ie : A service that does not have service_description or host_name/host_group
        We have to index them differently and try to inherit from our template to get one
        of the previous parameter

        :param item: service to add
        :type item: alignak.objects.service.Service
        :param index: whether to index it or not. Not used
        :type index: bool
        :param var_tuple: tuple containing object class, host_name, hostgroup_name,
                          service_description and file it was parsed from (from logging purpose)
        :type var_tuple: tuple
        :return: None
        """
        if len(var_tuple) == 0:
            return

        objcls, hname, hgname, sdesc, in_file = var_tuple
        use = getattr(item, 'use', [])

        if use == []:
            mesg = "a %s has been defined without host_name nor " \
                   "hostgroups nor service_description and " \
                   "there is no use to create a unique key%s" % (objcls, in_file)
            item.configuration_errors.append(mesg)
            return

        use = ','.join(use)
        if sdesc:
            name = "::".join((sdesc, use))
        elif hname:
            name = "::".join((hname, use))
        else:
            name = "::".join((hgname, use))

        if name in self.name_to_partial:
            item = self.manage_conflict(item, name, partial=True)
        self.name_to_partial[name] = item

        self.partial_services[item._id] = item

    def apply_partial_inheritance(self, prop):
        """Apply partial inheritance. Because of partial services we need to
        override this function from SchedulingItem

        :param prop: property to inherit from
        :type prop: str
        :return: None
        """
        for i in itertools.chain(self.items.itervalues(),
                                 self.partial_services.itervalues(),
                                 self.templates.itervalues()):
            i.get_property_by_inheritance(prop)
            # If a "null" attribute was inherited, delete it
            try:
                if getattr(i, prop) == 'null':
                    delattr(i, prop)
            except AttributeError:
                pass

    def apply_inheritance(self):
        """ For all items and templates inherit properties and custom
            variables.

        :return: None
        """
        # We check for all Class properties if the host has it
        # if not, it check all host templates for a value
        cls = self.inner_class
        for prop in cls.properties:
            self.apply_partial_inheritance(prop)
        for i in itertools.chain(self.items.itervalues(),
                                 self.partial_services.itervalues(),
                                 self.templates.itervalues()):
            i.get_customs_properties_by_inheritance()

        for i in self.partial_services.itervalues():
            self.add_item(i, True, True)

        del self.partial_services
        del self.name_to_partial

    def linkify_templates(self):
        """Create link between objects

        :return: None
        """
        # First we create a list of all templates
        for i in itertools.chain(self.items.itervalues(),
                                 self.partial_services.itervalues(),
                                 self.templates.itervalues()):
            self.linkify_item_templates(i)
        for i in self:
            i.tags = self.get_all_tags(i)

    def find_srvs_by_hostname(self, host_name):
        """Get all services from a host based on a host_name

        :param host_name: the host name we want services
        :type host_name: str
        :return: list of services
        :rtype: list[alignak.objects.service.Service]
        """
        if hasattr(self, 'hosts'):
            host = self.hosts.find_by_name(host_name)
            if host is None:
                return None
            return host.get_services()
        return None

    def find_srv_by_name_and_hostname(self, host_name, sdescr):
        """Get a specific service based on a host_name and service_description

        :param host_name: host name linked to needed service
        :type host_name: str
        :param sdescr:  service name we need
        :type sdescr: str
        :return: the service found or None
        :rtype: alignak.objects.service.Service
        """
        key = (host_name, sdescr)
        return self.name_to_item.get(key, None)

    def linkify(self, hosts, commands, timeperiods, contacts,
                resultmodulations, businessimpactmodulations, escalations,
                servicegroups, triggers, checkmodulations, macromodulations):
        """Create link between objects::

         * service -> host
         * service -> command
         * service -> timeperiods
         * service -> contacts

        :param hosts: hosts to link
        :type hosts: alignak.objects.host.Hosts
        :param timeperiods: timeperiods to link
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param commands: commands to link
        :type commands: alignak.objects.command.Commands
        :param contacts: contacts to link
        :type contacts: alignak.objects.contact.Contacts
        :param resultmodulations: resultmodulations to link
        :type resultmodulations: alignak.objects.resultmodulation.Resultmodulations
        :param businessimpactmodulations: businessimpactmodulations to link
        :type businessimpactmodulations:
              alignak.objects.businessimpactmodulation.Businessimpactmodulations
        :param escalations: escalations to link
        :type escalations: alignak.objects.escalation.Escalations
        :param servicegroups: servicegroups to link
        :type servicegroups: alignak.objects.servicegroup.Servicegroups
        :param triggers: triggers to link
        :type triggers: alignak.objects.trigger.Triggers
        :param checkmodulations: checkmodulations to link
        :type checkmodulations: alignak.objects.checkmodulation.Checkmodulations
        :param macromodulations: macromodulations to link
        :type macromodulations:  alignak.objects.macromodulation.Macromodulations
        :return: None
        """
        self.linkify_with_timeperiods(timeperiods, 'notification_period')
        self.linkify_with_timeperiods(timeperiods, 'check_period')
        self.linkify_with_timeperiods(timeperiods, 'maintenance_period')
        self.linkify_with_timeperiods(timeperiods, 'snapshot_period')
        self.linkify_s_by_hst(hosts)
        self.linkify_s_by_sg(servicegroups)
        self.linkify_one_command_with_commands(commands, 'check_command')
        self.linkify_one_command_with_commands(commands, 'event_handler')
        self.linkify_one_command_with_commands(commands, 'snapshot_command')
        self.linkify_with_contacts(contacts)
        self.linkify_with_resultmodulations(resultmodulations)
        self.linkify_with_business_impact_modulations(businessimpactmodulations)
        # WARNING: all escalations will not be link here
        # (just the escalation here, not serviceesca or hostesca).
        # This last one will be link in escalations linkify.
        self.linkify_with_escalations(escalations)
        self.linkify_with_triggers(triggers)
        self.linkify_with_checkmodulations(checkmodulations)
        self.linkify_with_macromodulations(macromodulations)

    def override_properties(self, hosts):
        """Handle service_overrides property for hosts
        ie : override properties for relevant services

        :param hosts: hosts we need to apply override properties
        :type hosts: alignak.objects.host.Hosts
        :return: None
        """
        ovr_re = re.compile(r'^([^,]+),([^\s]+)\s+(.*)$')
        ovr_hosts = [h for h in hosts if getattr(h, 'service_overrides', None)]
        for host in ovr_hosts:
            # We're only looking for hosts having service overrides defined
            if isinstance(host.service_overrides, list):
                service_overrides = host.service_overrides
            else:
                service_overrides = [host.service_overrides]
            for ovr in service_overrides:
                # Checks service override syntax
                match = ovr_re.search(ovr)
                if match is None:
                    err = "Error: invalid service override syntax: %s" % ovr
                    host.configuration_errors.append(err)
                    continue
                sdescr, prop, value = match.groups()
                # Looks for corresponding service
                service = self.find_srv_by_name_and_hostname(
                    getattr(host, "host_name", ""), sdescr
                )
                if service is None:
                    err = "Error: trying to override property '%s' on service '%s' " \
                          "but it's unknown for this host" % (prop, sdescr)
                    host.configuration_errors.append(err)
                    continue
                # Checks if override is allowed
                excludes = ['host_name', 'service_description', 'use',
                            'servicegroups', 'trigger', 'trigger_name']
                if prop in excludes:
                    err = "Error: trying to override '%s', " \
                          "a forbidden property for service '%s'" % \
                          (prop, sdescr)
                    host.configuration_errors.append(err)
                    continue

                # Pythonize the value because here value is str.
                setattr(service, prop, service.properties[prop].pythonize(value))

    def optimize_service_search(self, hosts):
        """Setter for hosts attribute

        :param hosts: value to set
        :type hosts: alignak.objects.host.Hosts
        :return:
        """
        self.hosts = hosts

    def linkify_s_by_hst(self, hosts):
        """Link services with their parent host

        :param hosts: Hosts to look for simple host
        :type hosts: alignak.objects.host.Hosts
        :return: None
        """
        for serv in self:
            # If we do not have a host_name, we set it as
            # a template element to delete. (like Nagios)
            if not hasattr(serv, 'host_name'):
                serv.host = None
                continue
            try:
                hst_name = serv.host_name
                # The new member list, in id
                hst = hosts.find_by_name(hst_name)
                serv.host = hst
                # Let the host know we are his service
                if serv.host is not None:
                    hst.add_service_link(serv)
                else:  # Ok, the host do not exists!
                    err = "Warning: the service '%s' got an invalid host_name '%s'" % \
                          (self.get_name(), hst_name)
                    serv.configuration_warnings.append(err)
                    continue
            except AttributeError, exp:
                pass  # Will be catch at the is_correct moment

    def linkify_s_by_sg(self, servicegroups):
        """Link services with servicegroups

        :param servicegroups: Servicegroups
        :type servicegroups: alignak.objects.servicegroup.Servicegroups
        :return: None
        """
        for serv in self:
            new_servicegroups = []
            if hasattr(serv, 'servicegroups') and serv.servicegroups != '':
                for sg_name in serv.servicegroups:
                    sg_name = sg_name.strip()
                    servicegroup = servicegroups.find_by_name(sg_name)
                    if servicegroup is not None:
                        new_servicegroups.append(servicegroup)
                    else:
                        err = "Error: the servicegroup '%s' of the service '%s' is unknown" %\
                              (sg_name, serv.get_dbg_name())
                        serv.configuration_errors.append(err)
            serv.servicegroups = new_servicegroups

    def delete_services_by_id(self, ids):
        """Delete a list of services

        :param ids: ids list to delete
        :type ids: list
        :return: None
        """
        for s_id in ids:
            del self[s_id]

    def apply_implicit_inheritance(self, hosts):
        """Apply implicit inheritance for special properties:
        contact_groups, notification_interval , notification_period
        So service will take info from host if necessary

        :param hosts: hosts list needed to look for a simple host
        :type hosts: alignak.objects.host.Hosts
        :return: None
        """
        for prop in ('contacts', 'contact_groups', 'notification_interval',
                     'notification_period', 'resultmodulations', 'business_impact_modulations',
                     'escalations', 'poller_tag', 'reactionner_tag', 'check_period',
                     'business_impact', 'maintenance_period'):
            for serv in self:
                if not hasattr(serv, prop) and hasattr(serv, 'host_name'):
                    host = hosts.find_by_name(serv.host_name)
                    if host is not None and hasattr(host, prop):
                        setattr(serv, prop, getattr(host, prop))

    def apply_dependencies(self):
        """Wrapper to loop over services and call Service.fill_daddy_dependency()

        :return: None
        """
        for service in self:
            service.fill_daddy_dependency()

    def clean(self):
        """Remove services without host object linked to

        :return: None
        """
        to_del = []
        for serv in self:
            if not serv.host:
                to_del.append(serv._id)
        for sid in to_del:
            del self.items[sid]

    def explode_services_from_hosts(self, hosts, service, hnames):
        """
        Explodes a service based on a lis of hosts.

        :param hosts: The hosts container
        :type hosts:
        :param service: The base service to explode
        :type service:
        :param hnames:  The host_name list to explode service on
        :type hnames: str
        :return: None
        """
        duplicate_for_hosts = []  # get the list of our host_names if more than 1
        not_hosts = []  # the list of !host_name so we remove them after
        for hname in hnames:
            hname = hname.strip()

            # If the name begin with a !, we put it in
            # the not list
            if hname.startswith('!'):
                not_hosts.append(hname[1:])
            else:  # the standard list
                duplicate_for_hosts.append(hname)

        # remove duplicate items from duplicate_for_hosts:
        duplicate_for_hosts = list(set(duplicate_for_hosts))

        # Ok now we clean the duplicate_for_hosts with all hosts
        # of the not
        for hname in not_hosts:
            try:
                duplicate_for_hosts.remove(hname)
            except IndexError:
                pass

        # Now we duplicate the service for all host_names
        for hname in duplicate_for_hosts:
            host = hosts.find_by_name(hname)
            if host is None:
                err = 'Error: The hostname %service is unknown for the ' \
                      'service %service!' % (hname, service.get_name())
                service.configuration_errors.append(err)
                continue
            if host.is_excluded_for(service):
                continue
            new_s = service.copy()
            new_s.host_name = hname
            self.add_item(new_s)

    def _local_create_service(self, hosts, host_name, service):
        """Create a new service based on a host_name and service instance.

        :param hosts: The hosts items instance.
        :type hosts: alignak.objects.host.Hosts
        :param host_name: The host_name to create a new service.
        :type host_name: str
        :param service: The service to be used as template.
        :type service: Service
        :return: The new service created.
        :rtype: alignak.objects.service.Service
        """
        host = hosts.find_by_name(host_name.strip())
        if host.is_excluded_for(service):
            return
        # Creates concrete instance
        new_s = service.copy()
        new_s.host_name = host_name
        new_s.register = 1
        self.add_item(new_s)
        return new_s

    def explode_services_from_templates(self, hosts, service):
        """
        Explodes services from templates. All hosts holding the specified
        templates are bound the service.

        :param hosts: The hosts container.
        :type hosts: alignak.objects.host.Hosts
        :param service: The service to explode.
        :type service: alignak.objects.service.Service
        :return: None
        """
        hname = getattr(service, "host_name", None)
        if not hname:
            return

        # Now really create the services
        if is_complex_expr(hname):
            hnames = self.evaluate_hostgroup_expression(
                hname.strip(), hosts, hosts.templates, look_in='templates')
            for name in hnames:
                self._local_create_service(hosts, name, service)
        else:
            hnames = [n.strip() for n in hname.split(',') if n.strip()]
            for hname in hnames:
                for name in hosts.find_hosts_that_use_template(hname):
                    self._local_create_service(hosts, name, service)

    def explode_services_duplicates(self, hosts, service):
        """
        Explodes services holding a `duplicate_foreach` clause.

        :param hosts: The hosts container
        :type hosts: alignak.objects.host.Hosts
        :param service: The service to explode
        :type service: alignak.objects.service.Service
        """
        hname = getattr(service, "host_name", None)
        if hname is None:
            return

        # the generator case, we must create several new services
        # we must find our host, and get all key:value we need
        host = hosts.find_by_name(hname.strip())

        if host is None:
            err = 'Error: The hostname %service is unknown for the ' \
                  'service %service!' % (hname, service.get_name())
            service.configuration_errors.append(err)
            return

        # Duplicate services
        for new_s in service.duplicate(host):
            if host.is_excluded_for(new_s):
                continue
            # Adds concrete instance
            self.add_item(new_s)

    def register_service_into_servicegroups(self, service, servicegroups):
        """
        Registers a service into the service groups declared in its
        `servicegroups` attribute.

        :param service: The service to register
        :type service:
        :param servicegroups: The servicegroups container
        :type servicegroups:
        :return: None
        """
        if hasattr(service, 'service_description'):
            sname = service.service_description
            shname = getattr(service, 'host_name', '')
            if hasattr(service, 'servicegroups'):
                # Todo: See if we can remove this if
                if isinstance(service.servicegroups, list):
                    sgs = service.servicegroups
                else:
                    sgs = service.servicegroups.split(',')
                for servicegroup in sgs:
                    servicegroups.add_member([shname, sname], servicegroup.strip())

    def register_service_dependencies(self, service, servicedependencies):
        """
        Registers a service dependencies.

        :param service: The service to register
        :type service:
        :param servicedependencies: The servicedependencies container
        :type servicedependencies:
        :return: None
        """
        # We explode service_dependencies into Servicedependency
        # We just create serviceDep with goods values (as STRING!),
        # the link pass will be done after
        sdeps = [d.strip() for d in
                 getattr(service, "service_dependencies", [])]
        # %2=0 are for hosts, !=0 are for service_description
        i = 0
        hname = ''
        for elt in sdeps:
            if i % 2 == 0:  # host
                hname = elt
            else:  # description
                desc = elt
                # we can register it (service) (depend on) -> (hname, desc)
                # If we do not have enough data for service, it'service no use
                if hasattr(service, 'service_description') and hasattr(service, 'host_name'):
                    if hname == '':
                        hname = service.host_name
                    servicedependencies.add_service_dependency(
                        service.host_name, service.service_description, hname, desc)
            i += 1

    # We create new service if necessary (host groups and co)
    def explode(self, hosts, hostgroups, contactgroups,
                servicegroups, servicedependencies, triggers):
        """
        Explodes services, from host_name, hostgroup_name, and from templetes.

        :param hosts: The hosts container
        :type hosts:
        :param hostgroups: The hostgoups container
        :type hostgroups:
        :param contactgroups: The concactgoups container
        :type contactgroups:
        :param servicegroups: The servicegoups container
        :type servicegroups:
        :param servicedependencies: The servicedependencies container
        :type servicedependencies:
        :param triggers: The triggers container
        :type triggers:
        :return: None
        """
        # items::explode_trigger_string_into_triggers
        self.explode_trigger_string_into_triggers(triggers)

        # Then for every host create a copy of the service with just the host
        # because we are adding services, we can't just loop in it
        for s_id in self.items.keys():
            serv = self.items[s_id]
            # items::explode_host_groups_into_hosts
            # take all hosts from our hostgroup_name into our host_name property
            self.explode_host_groups_into_hosts(serv, hosts, hostgroups)

            # items::explode_contact_groups_into_contacts
            # take all contacts from our contact_groups into our contact property
            self.explode_contact_groups_into_contacts(serv, contactgroups)

            hnames = getattr(serv, "host_name", '')
            hnames = list(set([n.strip() for n in hnames.split(',') if n.strip()]))
            # hnames = strip_and_uniq(hnames)
            # We will duplicate if we have multiple host_name
            # or if we are a template (so a clean service)
            if len(hnames) == 1:
                self.index_item(serv)
            else:
                if len(hnames) >= 2:
                    self.explode_services_from_hosts(hosts, serv, hnames)
                # Delete expanded source service
                if not serv.configuration_errors:
                    self.remove_item(serv)

        for s_id in self.templates.keys():
            template = self.templates[s_id]
            self.explode_contact_groups_into_contacts(template, contactgroups)
            self.explode_services_from_templates(hosts, template)

        # Explode services that have a duplicate_foreach clause
        duplicates = [serv._id for serv in self if getattr(serv, 'duplicate_foreach', '')]
        for s_id in duplicates:
            serv = self.items[s_id]
            self.explode_services_duplicates(hosts, serv)
            if not serv.configuration_errors:
                self.remove_item(serv)

        to_remove = []
        for service in self:
            host = hosts.find_by_name(service.host_name)
            if host and host.is_excluded_for(service):
                to_remove.append(service)
        for service in to_remove:
            self.remove_item(service)

        # Servicegroups property need to be fullfill for got the informations
        # And then just register to this service_group
        for serv in self:
            self.register_service_into_servicegroups(serv, servicegroups)
            self.register_service_dependencies(serv, servicedependencies)

    def create_business_rules(self, hosts, services):
        """
        Loop on services and call Service.create_business_rules(hosts, services)


        :param hosts: hosts to link to
        :type hosts: alignak.objects.host.Hosts
        :param services: services to link to
        :type services: alignak.objects.service.Services
        :return: None
        TODO: Move this function into SchedulingItems class
        """
        for serv in self:
            serv.create_business_rules(hosts, services)

    def create_business_rules_dependencies(self):
        """Loop on services and call Service.create_business_rules_dependencies()

        :return: None
        TODO: Move this function into SchedulingItems class
        """
        for serv in self:
            serv.create_business_rules_dependencies()

    def fill_predictive_missing_parameters(self):
        """Loop on services and call Service.fill_predictive_missing_parameters()

        :return: None
        """
        for service in self:
            service.fill_predictive_missing_parameters()
