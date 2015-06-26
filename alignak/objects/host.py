#!/usr/bin/env python
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
#     Httqm, fournet.matthieu@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Andreas Karfusehr, frescha@unitedseed.de
#     Andrew McGilvray, amcgilvray@kixeye.com
#     Hubert, hubert.santuz@gmail.com
#     François Lafont, flafdivers@free.fr
#     Arthur Gautier, superbaloo@superbaloo.net
#     Frédéric MOHIER, frederic.mohier@ipmfrance.com
#     Guillaume Bour, guillaume@bour.cc
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Jan Ulferts, jan.ulferts@xing.com
#     Grégory Starck, g.starck@gmail.com
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Demelziraptor, demelza@circularvale.com
#     Jean Gabes, naparuba@gmail.com
#     Christophe Simon, geektophe@gmail.com
#     Romain Forlot, rforlot@yahoo.com
#     Pradeep Jindal, praddyjindal@gmail.com

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

""" This is the main class for the Host. In fact it's mainly
about the configuration part. for the running one, it's better
to look at the schedulingitem class that manage all
scheduling/consume check smart things :)
"""

import time
import itertools

from item import Items
from schedulingitem import SchedulingItem

from alignak.autoslots import AutoSlots
from alignak.util import (format_t_into_dhms_format, to_hostnames_list, get_obj_name,
                          to_svc_hst_distinct_lists, to_list_string_of_names, to_list_of_names,
                          to_name_if_possible, strip_and_uniq)
from alignak.property import BoolProp, IntegerProp, FloatProp, CharProp, StringProp, ListProp
from alignak.graph import Graph
from alignak.macroresolver import MacroResolver
from alignak.eventhandler import EventHandler
from alignak.log import logger, naglog_result


class Host(SchedulingItem):
    """Host class implements monitoring concepts for host.
    For example it defines parents, check_interval, check_command  etc.
    """
    # AutoSlots create the __slots__ with properties and
    # running_properties names
    __metaclass__ = AutoSlots

    id = 1  # zero is reserved for host (primary node for parents)
    ok_up = 'UP'
    my_type = 'host'

    # if Host(or more generally Item) instances were created with all properties
    # having a default value set in the instance then we wouldn't need this:
    service_includes = service_excludes = []
    # though, as these 2 attributes are to be relatively low used it's not
    # that bad to have the default be defined only once here at the class level.

    # properties defined by configuration
    # *required: is required in conf
    # *default: default value if no set in conf
    # *pythonize: function to call when transforming string to python object
    # *fill_brok: if set, send to broker.
    #    there are two categories:
    #       full_status for initial and update status, check_result for check results
    # *no_slots: do not take this property for __slots__
    #  Only for the initial call
    # conf_send_preparation: if set, will pass the property to this function. It's used to "flatten"
    #  some dangerous properties like realms that are too 'linked' to be send like that.
    # brok_transformation: if set, will call the function with the value of the property
    #  the major times it will be to flatten the data (like realm_name instead of the realm object).
    properties = SchedulingItem.properties.copy()
    properties.update({
        'host_name':
            StringProp(fill_brok=['full_status', 'check_result', 'next_schedule']),
        'alias':
            StringProp(fill_brok=['full_status']),
        'display_name':
            StringProp(default='', fill_brok=['full_status']),
        'address':
            StringProp(fill_brok=['full_status']),
        'parents':
            ListProp(brok_transformation=to_hostnames_list, default=[],
                     fill_brok=['full_status'], merging='join', split_on_coma=True),
        'hostgroups':
            ListProp(brok_transformation=to_list_string_of_names, default=[],
                     fill_brok=['full_status'], merging='join', split_on_coma=True),
        'check_command':
            StringProp(default='_internal_host_up', fill_brok=['full_status']),
        'initial_state':
            CharProp(default='u', fill_brok=['full_status']),
        'max_check_attempts':
            IntegerProp(default=1, fill_brok=['full_status']),
        'check_interval':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result']),
        'retry_interval':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result']),
        'active_checks_enabled':
            BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'passive_checks_enabled':
            BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'check_period':
            StringProp(brok_transformation=to_name_if_possible, fill_brok=['full_status']),
        'obsess_over_host':
            BoolProp(default=False, fill_brok=['full_status'], retention=True),
        'check_freshness':
            BoolProp(default=False, fill_brok=['full_status']),
        'freshness_threshold':
            IntegerProp(default=0, fill_brok=['full_status']),
        'event_handler':
            StringProp(default='', fill_brok=['full_status']),
        'event_handler_enabled':
            BoolProp(default=False, fill_brok=['full_status']),
        'low_flap_threshold':
            IntegerProp(default=25, fill_brok=['full_status']),
        'high_flap_threshold':
            IntegerProp(default=50, fill_brok=['full_status']),
        'flap_detection_enabled':
            BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'flap_detection_options':
            ListProp(default=['o', 'd', 'u'], fill_brok=['full_status'],
                     merging='join', split_on_coma=True),
        'process_perf_data':
            BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'retain_status_information':
            BoolProp(default=True, fill_brok=['full_status']),
        'retain_nonstatus_information':
            BoolProp(default=True, fill_brok=['full_status']),
        'contacts':
            ListProp(default=[], brok_transformation=to_list_of_names,
                     fill_brok=['full_status'], merging='join', split_on_coma=True),
        'contact_groups':
            ListProp(default=[], fill_brok=['full_status'],
                     merging='join', split_on_coma=True),
        'notification_interval':
            IntegerProp(default=60, fill_brok=['full_status']),
        'first_notification_delay':
            IntegerProp(default=0, fill_brok=['full_status']),
        'notification_period':
            StringProp(brok_transformation=to_name_if_possible, fill_brok=['full_status']),
        'notification_options':
            ListProp(default=['d', 'u', 'r', 'f'], fill_brok=['full_status'],
                     merging='join', split_on_coma=True),
        'notifications_enabled':
            BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'stalking_options':
            ListProp(default=[''], fill_brok=['full_status']),
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
        'vrml_image':
            StringProp(default='', fill_brok=['full_status']),
        'statusmap_image':
            StringProp(default='', fill_brok=['full_status']),

        # No slots for this 2 because begin property by a number seems bad
        # it's stupid!
        '2d_coords':
            StringProp(default='', fill_brok=['full_status'], no_slots=True),
        '3d_coords':
            StringProp(default='', fill_brok=['full_status'], no_slots=True),
        'failure_prediction_enabled':
            BoolProp(default=False, fill_brok=['full_status']),

        # New to alignak
        # 'fill_brok' is ok because in scheduler it's already
        # a string from conf_send_preparation
        'realm':
            StringProp(default=None, fill_brok=['full_status'], conf_send_preparation=get_obj_name),
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
            StringProp(default='', brok_transformation=to_name_if_possible,
                       fill_brok=['full_status']),
        'time_to_orphanage':
            IntegerProp(default=300, fill_brok=['full_status']),
        'service_overrides':
            ListProp(default=[], merging='duplicate', split_on_coma=False),
        'service_excludes':
            ListProp(default=[], merging='duplicate', split_on_coma=True),
        'service_includes':
            ListProp(default=[], merging='duplicate', split_on_coma=True),
        'labels':
            StringProp(default=[], fill_brok=['full_status'], merging='join', split_on_coma=True),

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
            ListProp(default=[''], fill_brok=['full_status']),
        'business_rule_service_notification_options':
            ListProp(default=[''], fill_brok=['full_status']),

        # Business impact value
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

        # Our modulations. By defualt void, but will filled by an inner if need
        'checkmodulations':
            ListProp(default=[], fill_brok=['full_status'], merging='join'),
        'macromodulations':
            ListProp(default=[], merging='join'),

        # Custom views
        'custom_views':
            ListProp(default=[], fill_brok=['full_status'], merging='join'),

        # Snapshot part
        'snapshot_enabled':
            BoolProp(default=False),
        'snapshot_command':
            StringProp(default=''),
        'snapshot_period':
            StringProp(default=''),
        'snapshot_criteria':
            ListProp(default=['d', 'u'], fill_brok=['full_status'], merging='join'),
        'snapshot_interval':
            IntegerProp(default=5),
    })

    # properties set only for running purpose
    # retention: save/load this property from retention
    running_properties = SchedulingItem.running_properties.copy()
    running_properties.update({
        'modified_attributes':
            IntegerProp(default=0L, fill_brok=['full_status'], retention=True),
        'last_chk':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'next_chk':
            IntegerProp(default=0, fill_brok=['full_status', 'next_schedule'], retention=True),
        'in_checking':
            BoolProp(default=False, fill_brok=['full_status', 'check_result', 'next_schedule']),
        'in_maintenance':
            IntegerProp(default=None, fill_brok=['full_status'], retention=True),
        'latency':
            FloatProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'attempt':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'state':
            StringProp(default='PENDING', fill_brok=['full_status', 'check_result'],
                       retention=True),
        'state_id':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'state_type':
            StringProp(default='HARD', fill_brok=['full_status', 'check_result'], retention=True),
        'state_type_id':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'current_event_id':
            StringProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_event_id':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_state':
            StringProp(default='PENDING', fill_brok=['full_status', 'check_result'],
                       retention=True),
        'last_state_id':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_state_type':
            StringProp(default='HARD', fill_brok=['full_status', 'check_result'],  retention=True),
        'last_state_change':
            FloatProp(default=0.0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_hard_state_change':
            FloatProp(default=0.0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_hard_state':
            StringProp(default='PENDING', fill_brok=['full_status'], retention=True),
        'last_hard_state_id':
            IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'last_time_up':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_down':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_unreachable':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'duration_sec':
            IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'output':
            StringProp(default='', fill_brok=['full_status', 'check_result'], retention=True),
        'long_output':
            StringProp(default='', fill_brok=['full_status', 'check_result'], retention=True),
        'is_flapping':
            BoolProp(default=False, fill_brok=['full_status'], retention=True),
        'flapping_comment_id':
            IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        # No broks for _depend_of because of to much links to hosts/services
        # dependencies for actions like notif of event handler, so AFTER check return
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
            StringProp(default=0, fill_brok=['full_status'], retention=True),

        # no brok ,to much links
        'services':
            StringProp(default=[]),

        # No broks, it's just internal, and checks have too links
        'checks_in_progress':
            StringProp(default=[]),

        # No broks, it's just internal, and checks have too links
        'notifications_in_progress':
            StringProp(default={}, retention=True),

        'downtimes':
            StringProp(default=[], fill_brok=['full_status'], retention=True),

        'comments':
            StringProp(default=[], fill_brok=['full_status'], retention=True),

        'flapping_changes':
            StringProp(default=[], fill_brok=['full_status'], retention=True),

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

        'customs':
            StringProp(default={}, fill_brok=['full_status']),

        'got_default_realm':
            BoolProp(default=False),

        # use for having all contacts we have notified
        # Warning: for the notified_contacts retention save, we save only the names of the
        # contacts, and we should RELINK
        # them when we load it.
        'notified_contacts':
            StringProp(default=set(), retention=True, retention_preparation=to_list_of_names),

        'in_scheduled_downtime':
            BoolProp(default=False, fill_brok=['full_status', 'check_result'], retention=True),

        'in_scheduled_downtime_during_last_check':
            BoolProp(default=False, retention=True),

        # put here checks and notif raised
        'actions':
            StringProp(default=[]),

        # and here broks raised
        'broks':
            StringProp(default=[]),

        # For knowing with which elements we are in relation
        # of dep.
        # childs are the hosts that have US as parent, so
        # only a network dep
        'childs':
            StringProp(brok_transformation=to_hostnames_list, default=[],
                       fill_brok=['full_status']),

        # Here it's the elements we are depending on
        # so our parents as network relation, or a host
        # we are depending in a hostdependency
        # or even if we are business based.
        'parent_dependencies':
            StringProp(brok_transformation=to_svc_hst_distinct_lists, default=set(),
                       fill_brok=['full_status']),

        # Here it's the guys that depend on us. So it's the total
        # opposite of the parent_dependencies
        'child_dependencies':
            StringProp(brok_transformation=to_svc_hst_distinct_lists,
                       default=set(),
                       fill_brok=['full_status']),


        # Problem/impact part
        'is_problem':
            StringProp(default=False, fill_brok=['full_status']),

        'is_impact':
            StringProp(default=False, fill_brok=['full_status']),

        # the save value of our business_impact for "problems"
        'my_own_business_impact':
            IntegerProp(default=-1, fill_brok=['full_status']),

        # list of problems that make us an impact
        'source_problems':
            StringProp(brok_transformation=to_svc_hst_distinct_lists, default=[],
                       fill_brok=['full_status']),

        # list of the impact I'm the cause of
        'impacts':
            StringProp(brok_transformation=to_svc_hst_distinct_lists, default=[],
                       fill_brok=['full_status']),

        # keep a trace of the old state before being an impact
        'state_before_impact':
            StringProp(default='PENDING'),

        # keep a trace of the old state id before being an impact
        'state_id_before_impact':
            StringProp(default=0),

        # if the state change, we know so we do not revert it
        'state_changed_since_impact':
            StringProp(default=False),

        # BUSINESS CORRELATOR PART
        # Say if we are business based rule or not
        'got_business_rule':
            BoolProp(default=False, fill_brok=['full_status']),

        # Previously processed business rule (with macro expanded)
        'processed_business_rule':
            StringProp(default="", fill_brok=['full_status']),

        # Our Dependency node for the business rule
        'business_rule':
            StringProp(default=None),

        # Manage the unknown/unreach during hard state
        # From now its not really used
        'in_hard_unknown_reach_phase':
            BoolProp(default=False, retention=True),

        'was_in_hard_unknown_reach_phase':
            BoolProp(default=False, retention=True),

        'state_before_hard_unknown_reach_phase':
            StringProp(default='UP', retention=True),

        # Set if the element just change its father/son topology
        'topology_change':
            BoolProp(default=False, fill_brok=['full_status']),

        # Keep in mind our pack id after the cutting phase
        'pack_id':
            IntegerProp(default=-1),

        # Trigger list
        'triggers':
        StringProp(default=[]),

        # snapshots part
        'last_snapshot':  IntegerProp(default=0, fill_brok=['full_status'], retention=True),

        # Keep the string of the last command launched for this element
        'last_check_command': StringProp(default=''),
    })

    # Hosts macros and prop that give the information
    # the prop can be callable or not
    macros = {
        'HOSTNAME':          'host_name',
        'HOSTDISPLAYNAME':   'display_name',
        'HOSTALIAS':         'alias',
        'HOSTADDRESS':       'address',
        'HOSTSTATE':         'state',
        'HOSTSTATEID':       'state_id',
        'LASTHOSTSTATE':     'last_state',
        'LASTHOSTSTATEID':   'last_state_id',
        'HOSTSTATETYPE':     'state_type',
        'HOSTATTEMPT':       'attempt',
        'MAXHOSTATTEMPTS':   'max_check_attempts',
        'HOSTEVENTID':       'current_event_id',
        'LASTHOSTEVENTID':   'last_event_id',
        'HOSTPROBLEMID':     'current_problem_id',
        'LASTHOSTPROBLEMID': 'last_problem_id',
        'HOSTLATENCY':       'latency',
        'HOSTEXECUTIONTIME': 'execution_time',
        'HOSTDURATION':      'get_duration',
        'HOSTDURATIONSEC':   'get_duration_sec',
        'HOSTDOWNTIME':      'get_downtime',
        'HOSTPERCENTCHANGE': 'percent_state_change',
        'HOSTGROUPNAME':     'get_groupname',
        'HOSTGROUPNAMES':    'get_groupnames',
        'LASTHOSTCHECK':     'last_chk',
        'LASTHOSTSTATECHANGE': 'last_state_change',
        'LASTHOSTUP':        'last_time_up',
        'LASTHOSTDOWN':      'last_time_down',
        'LASTHOSTUNREACHABLE': 'last_time_unreachable',
        'HOSTOUTPUT':        'output',
        'LONGHOSTOUTPUT':    'long_output',
        'HOSTPERFDATA':      'perf_data',
        'LASTHOSTPERFDATA':  'last_perf_data',
        'HOSTCHECKCOMMAND':  'get_check_command',
        'HOSTACKAUTHOR':     'get_ack_author_name',
        'HOSTACKAUTHORNAME': 'get_ack_author_name',
        'HOSTACKAUTHORALIAS': 'get_ack_author_name',
        'HOSTACKCOMMENT':    'get_ack_comment',
        'HOSTACTIONURL':     'action_url',
        'HOSTNOTESURL':      'notes_url',
        'HOSTNOTES':         'notes',
        'HOSTREALM':         'get_realm',
        'TOTALHOSTSERVICES': 'get_total_services',
        'TOTALHOSTSERVICESOK': 'get_total_services_ok',
        'TOTALHOSTSERVICESWARNING': 'get_total_services_warning',
        'TOTALHOSTSERVICESUNKNOWN': 'get_total_services_unknown',
        'TOTALHOSTSERVICESCRITICAL': 'get_total_services_critical',
        'HOSTBUSINESSIMPACT':  'business_impact',
        # Business rules output formatting related macros
        'STATUS':            'get_status',
        'SHORTSTATUS':       'get_short_status',
        'FULLNAME':          'get_full_name',
    }

    # Manage ADDRESSX macros by adding them dynamically
    for _i in range(32):
        macros['HOSTADDRESS%d' % _i] = 'address%d' % _i

    # This tab is used to transform old parameters name into new ones
    # so from Nagios2 format, to Nagios3 ones.
    # Or Alignak deprecated names like criticity
    old_properties = {
        'normal_check_interval': 'check_interval',
        'retry_check_interval': 'retry_interval',
        'criticity': 'business_impact',
        'hostgroup': 'hostgroups',
        # 'criticitymodulations': 'business_impact_modulations',
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
        """Fill address with host_name if not already set

        :return: None
        """
        if hasattr(self, 'host_name') and not hasattr(self, 'address'):
            self.address = self.host_name
        if hasattr(self, 'host_name') and not hasattr(self, 'alias'):
            self.alias = self.host_name


    def is_correct(self):
        """Check if this host configuration is correct ::

        * All required parameter are specified
        * Go thought all configuration warnings and errors that could have been raised earlier

        :return: True if the configuration is correct, False otherwise
        :rtype: bool
        """
        state = True
        cls = self.__class__

        source = getattr(self, 'imported_from', 'unknown')

        special_properties = ['check_period', 'notification_interval',
                              'notification_period']
        for prop, entry in cls.properties.items():
            if prop not in special_properties:
                if not hasattr(self, prop) and entry.required:
                    logger.error("[host::%s] %s property not set", self.get_name(), prop)
                    state = False  # Bad boy...

        # Then look if we have some errors in the conf
        # Juts print warnings, but raise errors
        for err in self.configuration_warnings:
            logger.warning("[host::%s] %s", self.get_name(), err)

        # Raised all previously saw errors like unknown contacts and co
        if self.configuration_errors != []:
            state = False
            for err in self.configuration_errors:
                logger.error("[host::%s] %s", self.get_name(), err)

        if not hasattr(self, 'notification_period'):
            self.notification_period = None

        # Ok now we manage special cases...
        if self.notifications_enabled and self.contacts == []:
            logger.warning("The host %s has no contacts nor contact_groups in (%s)",
                           self.get_name(), source)

        if getattr(self, 'event_handler', None) and not self.event_handler.is_valid():
            logger.error("%s: my event_handler %s is invalid",
                         self.get_name(), self.event_handler.command)
            state = False

        if getattr(self, 'check_command', None) is None:
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
                        logger.error("[host::%s] %s", self.get_name(), bperror)
                    state = False

        if (not hasattr(self, 'notification_interval') and
                self.notifications_enabled is True):
            logger.error("%s: I've got no notification_interval but "
                         "I've got notifications enabled", self.get_name())
            state = False

        # if no check_period, means 24x7, like for services
        if not hasattr(self, 'check_period'):
            self.check_period = None

        if hasattr(self, 'host_name'):
            for c in cls.illegal_object_name_chars:
                if c in self.host_name:
                    logger.error("%s: My host_name got the character %s that is not allowed.",
                                 self.get_name(), c)
                    state = False

        return state


    def find_service_by_name(self, service_description):
        """Get a service object from this host

        :param service_description: service_description of the service we want
        :return: service with service.service_description == service_description
        :rtype: alignak.objects.service.Services
        """
        for s in self.services:
            if getattr(s, 'service_description', '__UNNAMED_SERVICE__') == service_description:
                return s
        return None


    def get_services(self):
        """Get all services for this host

        :return: list of services
        :rtype: list
        """
        return self.services


    def get_name(self):
        """Get the host name.
        Try several attributes before returning UNNAMED*

        :return: The name of the host
        :rtype: str
        """
        if not self.is_tpl():
            try:
                return self.host_name
            except AttributeError:  # outch, no hostname
                return 'UNNAMEDHOST'
        else:
            try:
                return self.name
            except AttributeError:  # outch, no name for this template
                return 'UNNAMEDHOSTTEMPLATE'


    def get_groupname(self):
        """Get alias of the host's hostgroup

        :return: host group name
        :rtype: str
        TODO: Clean this. It returns the last hostgroup encountered
        """
        groupname = ''
        for hg in self.hostgroups:
            # naglog_result('info', 'get_groupname : %s %s %s' % (hg.id, hg.alias, hg.get_name()))
            # groupname = "%s [%s]" % (hg.alias, hg.get_name())
            groupname = "%s" % (hg.alias)
        return groupname


    def get_groupnames(self):
        """Get aliases of the host's hostgroups

        :return: comma separated aliases of hostgroups
        :rtype: str
        """
        groupnames = ''
        for hg in self.hostgroups:
            # naglog_result('info', 'get_groupnames : %s' % (hg.get_name()))
            if groupnames == '':
                groupnames = hg.get_name()
            else:
                groupnames = "%s, %s" % (groupnames, hg.get_name())
        return groupnames


    def get_dbg_name(self):
        """Accessor to host_name attribute

        :return: host_name
        :rtype: str
        """
        return self.host_name


    def get_full_name(self):
        """Accessor to host_name attribute

        :return: host_name
        :rtype: str
        """
        return self.host_name


    def get_realm(self):
        """Accessor to realm attribute

        :return: realm object of host
        :rtype: alignak.objects.realm.Realm
        """
        return self.realm


    def get_hostgroups(self):
        """Accessor to hostgroups attribute

        :return: hostgroup list object of host
        :rtype: list
        """
        return self.hostgroups


    def get_host_tags(self):
        """Accessor to tags attribute

        :return: tag list  of host
        :rtype: list
        """
        return self.tags


    def is_linked_with_host(self, other):
        """Check if other is in act_depend_of host attribute

        :param other: other host to search
        :type other: alignak.objects.host.Host
        :return: True if other in act_depend_of list, False otherwise
        """
        for (h, status, type, timeperiod, inherits_parent) in self.act_depend_of:
            if h == other:
                return True
        return False


    def del_host_act_dependency(self, other):
        """Remove act_dependency between two hosts.

        :param other: other host we want to remove the dependency
        :type other: alignak.objects.host.Host
        :return: None
        TODO: Host object should not handle other host obj.
             We should call obj.del_* on both obj.
             This is 'Java' style
        """
        to_del = []
        # First we remove in my list
        for (h, status, type, timeperiod, inherits_parent) in self.act_depend_of:
            if h == other:
                to_del.append((h, status, type, timeperiod, inherits_parent))
        for t in to_del:
            self.act_depend_of.remove(t)

        # And now in the father part
        to_del = []
        for (h, status, type, timeperiod, inherits_parent) in other.act_depend_of_me:
            if h == self:
                to_del.append((h, status, type, timeperiod, inherits_parent))
        for t in to_del:
            other.act_depend_of_me.remove(t)

        # Remove in child/parents deps too
        # Me in father list
        other.child_dependencies.remove(self)
        # and father list in mine
        self.parent_dependencies.remove(other)


    def add_host_act_dependency(self, h, status, timeperiod, inherits_parent):
        """Add logical act_dependency between two hosts.

        :param h: other host we want to add the dependency
        :type h: alignak.objects.host.Host
        :param status: notification failure criteria, notification for a dependent host may vary
        :type status: list
        :param timeperiod: dependency period. Timeperiod for dependency may vary
        :type timeperiod: alignak.objects.timeperiod.Timeperiod
        :param inherits_parent: if this dep will inherit from parents (timeperiod, status)
        :type inherits_parent: bool
        :return: None
        TODO: Host object should not handle other host obj.
             We should call obj.add_* on both obj.
             This is 'Java' style
        TODO: Function seems to be asymmetric, (obj1.call1 , obj2.call1, obj2.call2)
        """
        # I add him in MY list
        self.act_depend_of.append((h, status, 'logic_dep', timeperiod, inherits_parent))
        # And I add me in it's list
        h.act_depend_of_me.append((self, status, 'logic_dep', timeperiod, inherits_parent))

        # And the parent/child dep lists too
        h.register_son_in_parent_child_dependencies(self)


    def add_business_rule_act_dependency(self, h, status, timeperiod, inherits_parent):
        """Add business act_dependency between two hosts.

        :param h: other host we want to add the dependency
        :type h: alignak.objects.host.Host
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
        # I only register so he know that I WILL be a impact
        self.act_depend_of_me.append((h, status, 'business_dep',
                                      timeperiod, inherits_parent))

        # And the parent/child dep lists too
        self.register_son_in_parent_child_dependencies(h)

    def add_host_chk_dependency(self, h, status, timeperiod, inherits_parent):
        """Add logic chk_dependency between two hosts.

        :param h: other host we want to add the dependency
        :type h: alignak.objects.host.Host
        :param status: notification failure criteria, notification for a dependent host may vary
        :type status: list
        :param timeperiod: dependency period. Timeperiod for dependency may vary
        :type timeperiod: alignak.objects.timeperiod.Timeperiod
        :param inherits_parent: if this dep will inherit from parents (timeperiod, status)
        :type inherits_parent: bool
        :return: None
        TODO: Function seems to be asymmetric, (obj1.call1 , obj2.call1, obj2.call2)
        """
        # I add him in MY list
        self.chk_depend_of.append((h, status, 'logic_dep', timeperiod, inherits_parent))
        # And I add me in it's list
        h.chk_depend_of_me.append((self, status, 'logic_dep', timeperiod, inherits_parent))

        # And we fill parent/childs dep for brok purpose
        # Here self depend on h
        h.register_son_in_parent_child_dependencies(self)


    def add_service_link(self, service):
        """Add a service to the service list of this host

        :param service: the service to add
        :type service: alignak.objects.service.Service
        :return: None
        """
        self.services.append(service)


    def __repr__(self):
        return '<Host host_name=%r name=%r use=%r />' % (
            getattr(self, 'host_name', None),
            getattr(self, 'name', None),
            getattr(self, 'use', None))

    __str__ = __repr__


    def is_excluded_for(self, service):
        ''' Check whether this host should have the passed service be "excluded" or "not included".

        An host can define service_includes and/or service_excludes directive to either
        white-list-only or black-list some services from itself.

        :type service: alignak.objects.service.Service
        '''
        return self.is_excluded_for_sdesc(service.service_description, service.is_tpl())

    def is_excluded_for_sdesc(self, sdesc, is_tpl=False):
        ''' Check whether this host should have the passed service *description*
            be "excluded" or "not included".
        '''
        if not is_tpl and self.service_includes:
            return sdesc not in self.service_includes
        if self.service_excludes:
            return sdesc in self.service_excludes
        return False

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
        """Set unreachable: all our parents are down
        Unreachable is different from down even if the state id is the same

        :return:None
        """
        now = time.time()
        self.state_id = 2
        self.state = 'UNREACHABLE'
        self.last_time_unreachable = int(now)


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
            # This flag will know if we override the impact state
            self.state_changed_since_impact = False
            self.state = 'UNREACHABLE'  # exit code UNDETERMINED
            self.state_id = 2


    def unset_impact_state(self):
        """Unset impact, only if impact state change is set in configuration

        :return: None
        """
        cls = self.__class__
        if cls.enable_problem_impacts_states_change and not self.state_changed_since_impact:
            self.state = self.state_before_impact
            self.state_id = self.state_id_before_impact


    def set_state_from_exit_status(self, status):
        """Set the state in UP, DOWN, or UNDETERMINED
        with the status of a check. Also update last_state

        :param status: integer between 0 and 3 (but not 1)
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
        # And only if we enable the impact state change
        cls = self.__class__
        if (cls.enable_problem_impacts_states_change and
                self.is_impact and
                not self.state_changed_since_impact):
            self.last_state = self.state_before_impact
        else:
            self.last_state = self.state
        # There is no 1 case because it should have been managed by the caller for a host
        # like the schedulingitem::consume method.
        if status == 0:
            self.state = 'UP'
            self.state_id = 0
            self.last_time_up = int(self.last_state_update)
            state_code = 'u'
        elif status in (2, 3):
            self.state = 'DOWN'
            self.state_id = 1
            self.last_time_down = int(self.last_state_update)
            state_code = 'd'
        else:
            self.state = 'DOWN'  # exit code UNDETERMINED
            self.state_id = 1
            self.last_time_down = int(self.last_state_update)
            state_code = 'd'
        if state_code in self.flap_detection_options:
            self.add_flapping_change(self.state != self.last_state)
        if self.state != self.last_state:
            self.last_state_change = self.last_state_update
        self.duration_sec = now - self.last_state_change


    def is_state(self, status):
        """Return if status match the current host status

        :param status: status to compare ( "o", "d", "u"). Usually comes from config files
        :type status: str
        :return: True if status <=> self.status, False otherwise
        """
        if status == self.state:
            return True
        # Now low status
        elif status == 'o' and self.state == 'UP':
            return True
        elif status == 'd' and self.state == 'DOWN':
            return True
        elif status == 'u' and self.state == 'UNREACHABLE':
            return True
        return False


    def last_time_non_ok_or_up(self):
        """Get the last time the host was in a non-OK state

        :return: self.last_time_down if self.last_time_down > self.last_time_up, 0 otherwise
        :rtype: bool
        """
        if self.last_time_down > self.last_time_up:
            last_time_non_up = self.last_time_down
        else:
            last_time_non_up = 0
        return last_time_non_up


    def raise_alert_log_entry(self):
        """Raise HOST ALERT entry (critical level)
        Format is : "HOST ALERT: *get_name()*;*state*;*state_type*;*attempt*;*output*"
        Example : "HOST ALERT: server;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        naglog_result('critical',
                      'HOST ALERT: %s;%s;%s;%d;%s' % (self.get_name(),
                                                      self.state, self.state_type,
                                                      self.attempt, self.output))


    def raise_initial_state(self):
        """Raise CURRENT HOST ALERT entry (info level)
        Format is : "CURRENT HOST STATE: *get_name()*;*state*;*state_type*;*attempt*;*output*"
        Example : "CURRENT HOST STATE: server;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        if self.__class__.log_initial_states:
            naglog_result('info',
                          'CURRENT HOST STATE: %s;%s;%s;%d;%s' % (self.get_name(),
                                                                  self.state, self.state_type,
                                                                  self.attempt, self.output))


    def raise_freshness_log_entry(self, t_stale_by, t_threshold):
        """Raise freshness alert entry (warning level)
        Format is : "The results of host '*get_name()*' are stale by *t_stale_by*
                     (threshold=*t_threshold*).  I'm forcing an immediate check of the host."
        Example : "Warning: The results of host 'Server' are stale by 0d 0h 0m 58s
                   (threshold=0d 1h 0m 0s). ..."

        :param t_stale_by: time in seconds the host has been in a stale state
        :param t_threshold: threshold (seconds) to trigger this log entry
        :return: None
        """
        logger.warning("The results of host '%s' are stale by %s "
                       "(threshold=%s).  I'm forcing an immediate check "
                       "of the host.",
                       self.get_name(),
                       format_t_into_dhms_format(t_stale_by),
                       format_t_into_dhms_format(t_threshold))


    def raise_notification_log_entry(self, n):
        """Raise HOST NOTIFICATION entry (critical level)
        Format is : "HOST NOTIFICATION: *contact.get_name()*;*self.get_name()*;*state*;
                     *command.get_name()*;*output*"
        Example : "HOST NOTIFICATION: superadmin;server;UP;notify-by-rss;no output"

        :param n: notification object created by host alert
        :type n: alignak.objects.notification.Notification
        :return: None
        """
        contact = n.contact
        command = n.command_call
        if n.type in ('DOWNTIMESTART', 'DOWNTIMEEND', 'CUSTOM',
                      'ACKNOWLEDGEMENT', 'FLAPPINGSTART', 'FLAPPINGSTOP',
                      'FLAPPINGDISABLED'):
            state = '%s (%s)' % (n.type, self.state)
        else:
            state = self.state
        if self.__class__.log_notifications:
            naglog_result('critical',
                          "HOST NOTIFICATION: %s;%s;%s;%s;%s" % (contact.get_name(),
                                                                 self.get_name(), state,
                                                                 command.get_name(), self.output))


    def raise_event_handler_log_entry(self, command):
        """Raise HOST EVENT HANDLER entry (critical level)
        Format is : "HOST EVENT HANDLER: *self.get_name()*;*state*;*state_type*;*attempt*;
                    *command.get_name()*"
        Example : "HOST EVENT HANDLER: server;UP;HARD;1;notify-by-rss"

        :param command: Handler launched
        :type command: alignak.objects.command.Command
        :return: None
        """
        if self.__class__.log_event_handlers:
            naglog_result('critical',
                          "HOST EVENT HANDLER: %s;%s;%s;%s;%s" % (self.get_name(),
                                                                  self.state, self.state_type,
                                                                  self.attempt, command.get_name()))


    def raise_snapshot_log_entry(self, command):
        """Raise HOST SNAPSHOT entry (critical level)
        Format is : "HOST SNAPSHOT: *self.get_name()*;*state*;*state_type*;*attempt*;
                    *command.get_name()*"
        Example : "HOST SNAPSHOT: server;UP;HARD;1;notify-by-rss"

        :param command: Snapshot command launched
        :type command: alignak.objects.command.Command
        :return: None
        """
        if self.__class__.log_event_handlers:
            naglog_result('critical',
                          "HOST SNAPSHOT: %s;%s;%s;%s;%s" % (self.get_name(),
                                                             self.state, self.state_type,
                                                             self.attempt, command.get_name()))


    def raise_flapping_start_log_entry(self, change_ratio, threshold):
        """Raise HOST FLAPPING ALERT START entry (critical level)
        Format is : "HOST FLAPPING ALERT: *self.get_name()*;STARTED;
                     Host appears to have started
                     flapping (*change_ratio*% change >= *threshold*% threshold)"
        Example : "HOST FLAPPING ALERT: server;STARTED;
                   Host appears to have started
                   flapping (50.6% change >= 50.0% threshold)"

        :param change_ratio: percent of changing state
        :param threshold: threshold (percent) to trigger this log entry
        :return: None
        """
        naglog_result('critical',
                      "HOST FLAPPING ALERT: %s;STARTED; "
                      "Host appears to have started flapping "
                      "(%.1f%% change >= %.1f%% threshold)"
                      % (self.get_name(), change_ratio, threshold))


    def raise_flapping_stop_log_entry(self, change_ratio, threshold):
        """Raise HOST FLAPPING ALERT STOPPED entry (critical level)
        Format is : "HOST FLAPPING ALERT: *self.get_name()*;STOPPED;
                     Host appears to have stopped
                     flapping (*change_ratio*% change < *threshold*% threshold)"
        Example : "HOST FLAPPING ALERT: server;STOPPED;
                   Host appears to have stopped
                   flapping (23.0% change < 25.0% threshold)"

        :param change_ratio: percent of changing state
        :param threshold: threshold (percent) to trigger this log entry
        :return: None
        """
        naglog_result('critical',
                      "HOST FLAPPING ALERT: %s;STOPPED; "
                      "Host appears to have stopped flapping "
                      "(%.1f%% change < %.1f%% threshold)"
                      % (self.get_name(), change_ratio, threshold))


    def raise_no_next_check_log_entry(self):
        """Raise no scheduled check entry (warning level)
        Format is : "I cannot schedule the check for the host 'get_name()*'
                    because there is not future valid time"
        Example : "I cannot schedule the check for the host 'Server'
                  because there is not future valid time"

        :return: None
        """
        logger.warning("I cannot schedule the check for the host '%s' "
                       "because there is not future valid time",
                       self.get_name())


    def raise_enter_downtime_log_entry(self):
        """Raise HOST DOWNTIME ALERT entry (critical level)
        Format is : "HOST DOWNTIME ALERT: *get_name()*;STARTED;
                    Host has entered a period of scheduled downtime"
        Example : "HOST DOWNTIME ALERT: test_host_0;STARTED;
                   Host has entered a period of scheduled downtime"

        :return: None
        """
        naglog_result('critical',
                      "HOST DOWNTIME ALERT: %s;STARTED; "
                      "Host has entered a period of scheduled downtime"
                      % (self.get_name()))


    def raise_exit_downtime_log_entry(self):
        """Raise HOST DOWNTIME ALERT entry (critical level)
        Format is : "HOST DOWNTIME ALERT: *get_name()*;STOPPED;
                     Host has entered a period of scheduled downtime"
        Example : "HOST DOWNTIME ALERT: test_host_0;STOPPED;
                   Host has entered a period of scheduled downtime"

        :return: None
        """
        naglog_result('critical',
                      "HOST DOWNTIME ALERT: %s;STOPPED; Host has "
                      "exited from a period of scheduled downtime"
                      % (self.get_name()))


    def raise_cancel_downtime_log_entry(self):
        """Raise HOST DOWNTIME ALERT entry (critical level)
        Format is : "HOST DOWNTIME ALERT: *get_name()*;CANCELLED;
                     Host has entered a period of scheduled downtime"
        Example : "HOST DOWNTIME ALERT: test_host_0;CANCELLED;
                   Host has entered a period of scheduled downtime"

        :return: None
        """
        naglog_result('critical',
                      "HOST DOWNTIME ALERT: %s;CANCELLED; "
                      "Scheduled downtime for host has been cancelled."
                      % (self.get_name()))


    def manage_stalking(self, c):
        """Check if the host need stalking or not (immediate recheck)
        If one stalking_options matches the exit_status ('o' <=> 0 ...) then stalk is needed
        Raise a log entry (info level) if stalk is needed

        :param c: finshed check (c.status == 'waitconsume')
        :type c: alignak.check.Check
        :return: None
        """
        need_stalk = False
        if c.status == 'waitconsume':
            if c.exit_status == 0 and 'o' in self.stalking_options:
                need_stalk = True
            elif c.exit_status == 1 and 'd' in self.stalking_options:
                need_stalk = True
            elif c.exit_status == 2 and 'd' in self.stalking_options:
                need_stalk = True
            elif c.exit_status == 3 and 'u' in self.stalking_options:
                need_stalk = True
            if c.output != self.output:
                need_stalk = False
        if need_stalk:
            logger.info("Stalking %s: %s", self.get_name(), self.output)


    def fill_parents_dependency(self):
        """Add network act_dependency for each parent of this host.
        This dependency is always effective (No timeperiod and all states) and inherits from parent

        :return: None
        TODO: Host object should not handle other host obj.
             We should call obj._fun_ on both obj.
             This is 'Java' style
        """
        for parent in self.parents:
            if parent is not None:
                # I add my parent in my list
                self.act_depend_of.append((parent, ['d', 'u', 's', 'f'], 'network_dep', None, True))

                # And I register myself in my parent list too
                parent.register_child(self)

                # And add the parent/child dep filling too, for broking
                parent.register_son_in_parent_child_dependencies(self)


    def register_child(self, child):
        """Add a child to child list

        :param child: host to add
        :type child: alignak.objects.host.Host
        :return: None
        """
        # We've got 2 list: a list for our child
        # where we just put the pointer, it's just for broking
        # and another with all data, useful for 'running' part
        self.childs.append(child)
        self.act_depend_of_me.append((child, ['d', 'u', 's', 'f'], 'network_dep', None, True))


    def get_data_for_checks(self):
        """Return the host itself in a single member list

        :return: list containing a single host (this one)
        :rtype: list
        TODO: This function seems useless. Why not do [h] directly instead of h.fun()
        """
        return [self]


    def get_data_for_event_handler(self):
        """Return the host itself in a single member list

        :return: list containing a single host (this one)
        :rtype: list
        TODO: This function seems useless. Why not do [h] directly instead of h.fun()
        """
        return [self]


    def get_data_for_notifications(self, contact, n):
        """Return the host itself, the contact and the notification in a list

        :param contact: The contact to return
        :param n: the notification to return
        :return: list containing a the host and the given parameter
        :rtype: list
        TODO: This function seems useless. Why not do [h, c, n] directly instead of h.fun(c,n)
        """
        return [self, contact, n]


    def notification_is_blocked_by_contact(self, n, contact):
        """Check if the notification is blocked by this contact.

        :param n: notification created earlier
        :type n: alignak.notification.Notification
        :param contact: contact we want to notify
        :type n: alignak.objects.contact.Contact
        :return: True if the notification is blocked, False otherwise
        :rtype: bool
        TODO: We should do contact.func(h.attr1, n.attr2 ..)before
        instead of calling it here with self.attr1
        """
        return not contact.want_host_notification(self.last_chk, self.state, n.type,
                                                  self.business_impact, n.command_call)


    def get_duration_sec(self):
        """Get duration in seconds. (cast it before returning)

        :return: duration in seconds
        :rtype: int
        """
        return str(int(self.duration_sec))


    def get_duration(self):
        """Get duration formatted
        Format is : "HHh MMm SSs"
        Example : "10h 20m 40s"

        :return: Formatted duration
        :rtype: str
        """
        m, s = divmod(self.duration_sec, 60)
        h, m = divmod(m, 60)
        return "%02dh %02dm %02ds" % (h, m, s)


    def notification_is_blocked_by_item(self, type, t_wished=None):
        """Check if a notification is blocked the host.
        Conditions are ONE of the following::

        * enable_notification is False (global)
        * not in a notification_period
        * notifications_enable is False (local)
        * notification_options is 'n' or matches the state ('DOWN' <=> 'd' ...)
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

        :param type: notification type
        :param t_wished: the time we sould like to notify the host (mostly now)
        :return: True if ONE of the above condition was met, False otherwise
        """
        if t_wished is None:
            t_wished = time.time()

        # TODO
        # forced notification -> false
        # custom notification -> false

        # Block if notifications are program-wide disabled
        if not self.enable_notifications:
            return True

        # Does the notification period allow sending out this notification?
        if (self.notification_period is not None and
                not self.notification_period.is_time_valid(t_wished)):
            return True

        # Block if notifications are disabled for this host
        if not self.notifications_enabled:
            return True

        # Block if the current status is in the notification_options d,u,r,f,s
        if 'n' in self.notification_options:
            return True

        if type in ('PROBLEM', 'RECOVERY'):
            if self.state == 'DOWN' and 'd' not in self.notification_options:
                return True
            if self.state == 'UP' and 'r' not in self.notification_options:
                return True
            if self.state == 'UNREACHABLE' and 'u' not in self.notification_options:
                return True
        if (type in ('FLAPPINGSTART', 'FLAPPINGSTOP', 'FLAPPINGDISABLED')
                and 'f' not in self.notification_options):
            return True
        if (type in ('DOWNTIMESTART', 'DOWNTIMEEND', 'DOWNTIMECANCELLED')
                and 's' not in self.notification_options):
            return True

        # Acknowledgements make no sense when the status is ok/up
        if type == 'ACKNOWLEDGEMENT':
            if self.state == self.ok_up:
                return True

        # Flapping
        if type in ('FLAPPINGSTART', 'FLAPPINGSTOP', 'FLAPPINGDISABLED'):
            # TODO block if not notify_on_flapping
            if self.scheduled_downtime_depth > 0:
                return True

        # When in deep downtime, only allow end-of-downtime notifications
        # In depth 1 the downtime just started and can be notified
        if self.scheduled_downtime_depth > 1 and type not in ('DOWNTIMEEND', 'DOWNTIMECANCELLED'):
            return True

        # Block if in a scheduled downtime and a problem arises
        if self.scheduled_downtime_depth > 0 and type in ('PROBLEM', 'RECOVERY'):
            return True

        # Block if the status is SOFT
        if self.state_type == 'SOFT' and type == 'PROBLEM':
            return True

        # Block if the problem has already been acknowledged
        if self.problem_has_been_acknowledged and type != 'ACKNOWLEDGEMENT':
            return True

        # Block if flapping
        if self.is_flapping and type not in ('FLAPPINGSTART', 'FLAPPINGSTOP', 'FLAPPINGDISABLED'):
            return True

        # Block if business rule smart notifications is enabled and all its
        # childs have been acknowledged or are under downtime.
        if self.got_business_rule is True \
                and self.business_rule_smart_notifications is True \
                and self.business_rule_notification_is_blocked() is True \
                and type == 'PROBLEM':
            return True

        return False


    def get_obsessive_compulsive_processor_command(self):
        """Create action for obsessive compulsive commands if such option is enabled

        :return: None
        """
        cls = self.__class__
        if not cls.obsess_over or not self.obsess_over_host:
            return
        m = MacroResolver()
        data = self.get_data_for_event_handler()
        cmd = m.resolve_command(cls.ochp_command, data)
        e = EventHandler(cmd, timeout=cls.ochp_timeout)

        # ok we can put it in our temp action queue
        self.actions.append(e)

    def get_total_services(self):
        """Get the number of services for this host

        :return: service list length
        :rtype: str
        """
        return str(len(self.services))

    def _tot_services_by_state(self, state):
        """Get the number of service in the specified state

        :param state: state to filter service
        :return: number of service with s.state_id == state
        :rtype: int
        """
        return str(sum(1 for s in self.services
                       if s.state_id == state))

    get_total_services_ok = lambda s: s._tot_services_by_state(0)
    get_total_services_warning = lambda s: s._tot_services_by_state(1)
    get_total_services_critical = lambda s: s._tot_services_by_state(2)
    get_total_services_unknown = lambda s: s._tot_services_by_state(3)

    def get_ack_author_name(self):
        """Get the author of the acknowledgement

        :return: author
        :rtype: str
        TODO: use getattr(self.acknowledgement, "author", '') instead
        """
        if self.acknowledgement is None:
            return ''
        return self.acknowledgement.author


    def get_ack_comment(self):
        """Get the comment of the acknowledgement

        :return: comment
        :rtype: str
        TODO: use getattr(self.acknowledgement, "comment", '') instead
        """
        if self.acknowledgement is None:
            return ''
        return self.acknowledgement.comment


    def get_check_command(self):
        """Wrapper to get the name of the check_command attribute

        :return: check_command name
        :rtype: str
        """
        return self.check_command.get_name()

    def get_short_status(self):
        """Get the short status of this host

        :return: "U", "D", "N" or "n/a" based on host state_id or business_rule state
        :rtype: str
        """
        mapping = {
            0: "U",
            1: "D",
            2: "N",
        }
        if self.got_business_rule:
            return mapping.get(self.business_rule.get_state(), "n/a")
        else:
            return mapping.get(self.state_id, "n/a")

    def get_status(self):
        """Get the status of this host

        :return: "UP", "DOWN", "UNREACHABLE" or "n/a" based on host state_id or business_rule state
        :rtype: str
        """
        if self.got_business_rule:
            mapping = {
                0: "UP",
                1: "DOWN",
                2: "UNREACHABLE",
            }
            return mapping.get(self.business_rule.get_state(), "n/a")
        else:
            return self.state

    def get_downtime(self):
        """Accessor to scheduled_downtime_depth attribue

        :return: scheduled downtime depth
        :rtype: str
        """
        return str(self.scheduled_downtime_depth)


class Hosts(Items):
    """Class for the hosts lists. It's mainly for configuration

    """
    name_property = "host_name"  # use for the search by name
    inner_class = Host  # use for know what is in items


    # Create link between elements:
    # hosts -> timeperiods
    # hosts -> hosts (parents, etc)
    # hosts -> commands (check_command)
    # hosts -> contacts
    def linkify(self, timeperiods=None, commands=None, contacts=None, realms=None,
                resultmodulations=None, businessimpactmodulations=None, escalations=None,
                hostgroups=None, triggers=None, checkmodulations=None, macromodulations=None):
        """Create link between objects::

         * hosts -> timeperiods
         * hosts -> hosts (parents, etc)
         * hosts -> commands (check_command)
         * hosts -> contacts

        :param timeperiods: timeperiods to link
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param commands: commands to link
        :type commands: alignak.objects.command.Commands
        :param contacts: contacts to link
        :type contacts: alignak.objects.contact.Contacts
        :param realms: realms to link
        :type realms: alignak.objects.realm.Realms
        :param resultmodulations: resultmodulations to link
        :type resultmodulations: alignak.objects.resultmodulation.Resultmodulations
        :param businessimpactmodulations: businessimpactmodulations to link
        :type businessimpactmodulations:
              alignak.objects.businessimpactmodulation.Businessimpactmodulations
        :param escalations: escalations to link
        :type escalations: alignak.objects.escalation.Escalations
        :param hostgroups: escalations to link
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
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
        self.linkify_h_by_h()
        self.linkify_h_by_hg(hostgroups)
        self.linkify_one_command_with_commands(commands, 'check_command')
        self.linkify_one_command_with_commands(commands, 'event_handler')
        self.linkify_one_command_with_commands(commands, 'snapshot_command')

        self.linkify_with_contacts(contacts)
        self.linkify_h_by_realms(realms)
        self.linkify_with_resultmodulations(resultmodulations)
        self.linkify_with_business_impact_modulations(businessimpactmodulations)
        # WARNING: all escalations will not be link here
        # (just the escalation here, not serviceesca or hostesca).
        # This last one will be link in escalations linkify.
        self.linkify_with_escalations(escalations)
        self.linkify_with_triggers(triggers)
        self.linkify_with_checkmodulations(checkmodulations)
        self.linkify_with_macromodulations(macromodulations)


    def fill_predictive_missing_parameters(self):
        """Loop on hosts and call Host.fill_predictive_missing_parameters()

        :return: None
        """
        for h in self:
            h.fill_predictive_missing_parameters()

    def linkify_h_by_h(self):
        """Link hosts with their parents

        :return: None
        """
        for h in self:
            parents = h.parents
            # The new member list
            new_parents = []
            for parent in parents:
                parent = parent.strip()
                p = self.find_by_name(parent)
                if p is not None:
                    new_parents.append(p)
                else:
                    err = "the parent '%s' on host '%s' is unknown!" % (parent, h.get_name())
                    self.configuration_warnings.append(err)
            # print "Me,", h.host_name, "define my parents", new_parents
            # We find the id, we replace the names
            h.parents = new_parents


    def linkify_h_by_realms(self, realms):
        """Link hosts with realms

        :param realms: realms object to link with
        :type realms: alignak.objects.realm.Realms
        :return: None
        """
        default_realm = None
        for r in realms:
            if getattr(r, 'default', False):
                default_realm = r
        # if default_realm is None:
        #    print "Error: there is no default realm defined!"
        for h in self:
            if h.realm is not None:
                p = realms.find_by_name(h.realm.strip())
                if p is None:
                    err = "the host %s got an invalid realm (%s)!" % (h.get_name(), h.realm)
                    h.configuration_errors.append(err)
                h.realm = p
            else:
                # print("Notice: applying default realm %s to host %s"
                #       % (default_realm.get_name(), h.get_name()))
                h.realm = default_realm
                h.got_default_realm = True


    def linkify_h_by_hg(self, hostgroups):
        """Link hosts with hostgroups

        :param realms: realms object to link with
        :type realms: alignak.objects.hostgroup.Hostgroups
        :return: None
        """
        # Register host in the hostgroups
        for h in self:
            new_hostgroups = []
            if hasattr(h, 'hostgroups') and h.hostgroups != []:
                hgs = [n.strip() for n in h.hostgroups if n.strip()]
                for hg_name in hgs:
                    # TODO: should an unknown hostgroup raise an error ?
                    hg = hostgroups.find_by_name(hg_name)
                    if hg is not None:
                        new_hostgroups.append(hg)
                    else:
                        err = ("the hostgroup '%s' of the host '%s' is "
                               "unknown" % (hg_name, h.host_name))
                        h.configuration_errors.append(err)
            h.hostgroups = new_hostgroups


    def explode(self, hostgroups, contactgroups, triggers):
        """Explode hosts, hostrgroups and triggers::

        * Add triggers source to host triggers
        * Add contact from contactgroups to host contacts
        * Add host into their hostgroups as hostgroup members

        :param hostgroups: Hostgroups to explode
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :param contactgroups: Contactgorups to explode
        :type contactgroups: alignak.objects.contactgroup.Contactgroups
        :param triggers: Triggers to explode
        :type triggers: alignak.objects.trigger.Triggers
        :return:
        """

        # items::explode_trigger_string_into_triggers
        self.explode_trigger_string_into_triggers(triggers)

        for t in self.templates.itervalues():
            # items::explode_contact_groups_into_contacts
            # take all contacts from our contact_groups into our contact property
            self.explode_contact_groups_into_contacts(t, contactgroups)

        # Register host in the hostgroups
        for h in self:
            # items::explode_contact_groups_into_contacts
            # take all contacts from our contact_groups into our contact property
            self.explode_contact_groups_into_contacts(h, contactgroups)

            if hasattr(h, 'host_name') and hasattr(h, 'hostgroups'):
                hname = h.host_name
                for hg in h.hostgroups:
                    hostgroups.add_member(hname, hg.strip())

    def apply_dependencies(self):
        """Loop on hosts and call Host.fill_parents_dependency()

        :return: None
        """
        for h in self:
            h.fill_parents_dependency()

    def find_hosts_that_use_template(self, tpl_name):
        """

        :param tpl_name: the template name we filter or
        :return: list of the host_name of the hosts that got the template tpl_name in tags
        :rtype: list[str]
        """
        return [h.host_name for h in self if tpl_name in h.tags if hasattr(h, "host_name")]

    def create_business_rules(self, hosts, services):
        """
        Loop on hosts and call Host.create_business_rules(hosts, services)


        :param hosts: hosts to link to
        :type hosts: alignak.objects.host.Hosts
        :param services: services to link to
        :type services: alignak.objects.service.Services
        :return: None
        """
        for h in self:
            h.create_business_rules(hosts, services)

    def create_business_rules_dependencies(self):
        """Loop on hosts and call Host.create_business_rules_dependencies()

        :return: None
        """
        for h in self:
            h.create_business_rules_dependencies()
