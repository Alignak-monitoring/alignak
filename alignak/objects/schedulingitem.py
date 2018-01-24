# -*- coding: utf-8 -*-

#
# Copyright (C) 2015-2017: Alignak team, see AUTHORS.txt file for contributors
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
#     Sebastien Coavoux, s.coavoux@free.fr
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Frédéric MOHIER, frederic.mohier@ipmfrance.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     Pradeep Jindal, praddyjindal@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Jan Ulferts, jan.ulferts@xing.com
#     Grégory Starck, g.starck@gmail.com
#     Arthur Gautier, superbaloo@superbaloo.net
#     Jean-Claude Computing, jeanclaude.computing@gmail.com
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Romain Forlot, rforlot@yahoo.com
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

""" This class is a common one for service/host. Here you
will find all scheduling related functions, like the schedule
or the consume_check. It's a very important class!
"""
# pylint: disable=C0302
# pylint: disable=R0904
import os
import re
import random
import time
import datetime
import traceback
import logging

from alignak.objects.item import Item
from alignak.objects.commandcallitem import CommandCallItems
from alignak.dependencynode import DependencyNode

from alignak.check import Check
from alignak.property import (BoolProp, IntegerProp, FloatProp, SetProp,
                              CharProp, StringProp, ListProp, DictProp)
from alignak.util import from_set_to_list, get_obj_name, \
    format_t_into_dhms_format
from alignak.notification import Notification
from alignak.macroresolver import MacroResolver
from alignak.eventhandler import EventHandler
from alignak.dependencynode import DependencyNodeFactory
from alignak.acknowledge import Acknowledge
from alignak.comment import Comment
from alignak.commandcall import CommandCall

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class SchedulingItem(Item):  # pylint: disable=R0902
    """SchedulingItem class provide method for Scheduler to handle Service or Host objects

    """

    # global counters used for [current|last]_[host|service]_[event|problem]_id
    current_event_id = 0
    current_problem_id = 0

    properties = Item.properties.copy()
    properties.update({
        'uuid':
            StringProp(),
        'display_name':
            StringProp(default='', fill_brok=['full_status']),
        'initial_state':
            CharProp(default='o', fill_brok=['full_status']),
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
            StringProp(fill_brok=['full_status'], special=True),
        # Set a default freshness threshold not 0 if parameter is missing
        # and check_freshness is enabled
        'check_freshness':
            BoolProp(default=False, fill_brok=['full_status']),
        'freshness_threshold':
            IntegerProp(default=-1, fill_brok=['full_status']),

        'event_handler':
            StringProp(default='', fill_brok=['full_status']),
        'event_handler_enabled':
            BoolProp(default=False, fill_brok=['full_status'], retention=True),
        'low_flap_threshold':
            IntegerProp(default=25, fill_brok=['full_status']),
        'high_flap_threshold':
            IntegerProp(default=50, fill_brok=['full_status']),
        'flap_detection_enabled':
            BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'process_perf_data':
            BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'retain_status_information':
            BoolProp(default=True, fill_brok=['full_status']),
        'retain_nonstatus_information':
            BoolProp(default=True, fill_brok=['full_status']),
        'contacts':
            ListProp(default=[],
                     fill_brok=['full_status'], merging='join', split_on_coma=True),
        'contact_groups':
            ListProp(default=[], fill_brok=['full_status'],
                     merging='join', split_on_coma=True),
        'notification_interval':
            IntegerProp(default=60, fill_brok=['full_status'], special=True),
        'first_notification_delay':
            IntegerProp(default=0, fill_brok=['full_status']),
        'notification_period':
            StringProp(fill_brok=['full_status'],
                       special=True),
        'notifications_enabled':
            BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'stalking_options':
            ListProp(default=[], fill_brok=['full_status'], merging='join'),
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
                       fill_brok=['full_status']),
        'time_to_orphanage':
            IntegerProp(default=300, fill_brok=['full_status']),

        'labels':
            ListProp(default=[], fill_brok=['full_status'], merging='join',
                     split_on_coma=True),

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
            ListProp(default=[], fill_brok=['full_status'], split_on_coma=True),
        'business_rule_service_notification_options':
            ListProp(default=[], fill_brok=['full_status'], split_on_coma=True),
        # Business_Impact value
        'business_impact':
            IntegerProp(default=2, fill_brok=['full_status']),

        # Load some triggers
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

        # Snapshot part
        'snapshot_enabled':
            BoolProp(default=False),
        'snapshot_command':
            StringProp(default=''),
        'snapshot_period':
            StringProp(default=''),
        'snapshot_interval':
            IntegerProp(default=5),

        'realm':
            StringProp(default='', fill_brok=['full_status']),
    })

    running_properties = Item.running_properties.copy()
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
            IntegerProp(default=-1, fill_brok=['full_status'], retention=True),
        'latency':
            FloatProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'attempt':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
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
        'state_type':
            StringProp(default='HARD', fill_brok=['full_status', 'check_result'], retention=True),
        'state_type_id':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'duration_sec':
            IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'output':
            StringProp(default='', fill_brok=['full_status', 'check_result'], retention=True),
        'long_output':
            StringProp(default='', fill_brok=['full_status', 'check_result'], retention=True),
        'is_flapping':
            BoolProp(default=False, fill_brok=['full_status'], retention=True),
        #  dependencies for actions like notification or event handler,
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
        'checks_in_progress':
            ListProp(default=[]),
        # no broks because notifications are too linked
        'notifications_in_progress':
            DictProp(default={}, retention=True),
        'comments':
            DictProp(default={}, fill_brok=['full_status'], retention=True),
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
            DictProp(default={}, fill_brok=['full_status']),
        # Warning: for the notified_contacts retention save,
        # we save only the names of the contacts, and we should RELINK
        # them when we load it.
        # use for having all contacts we have notified
        'notified_contacts':
            SetProp(default=set(), retention=True, retention_preparation=from_set_to_list),
        'in_scheduled_downtime':
            BoolProp(default=False, fill_brok=['full_status', 'check_result'], retention=True),
        'in_scheduled_downtime_during_last_check':
            BoolProp(default=False, retention=True),
        'actions':
            ListProp(default=[]),  # put here checks and notif raised
        'broks':
            ListProp(default=[]),  # and here broks raised

        # Problem/impact part
        'is_problem':
            BoolProp(default=False, fill_brok=['full_status']),
        'is_impact':
            BoolProp(default=False, fill_brok=['full_status']),
        # the save value of our business_impact for "problems"
        'my_own_business_impact':
            IntegerProp(default=-1, fill_brok=['full_status']),
        # list of problems that make us an impact
        'source_problems':
            ListProp(default=[], fill_brok=['full_status']),
        # list of the impact I'm the cause of
        'impacts':
            ListProp(default=[], fill_brok=['full_status']),
        # keep a trace of the old state before being an impact
        'state_before_impact':
            StringProp(default='PENDING'),
        # keep a trace of the old state id before being an impact
        'state_id_before_impact':
            IntegerProp(default=0),
        # if the state change, we know so we do not revert it
        'state_changed_since_impact':
            BoolProp(default=False),
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
        # Here it's the elements we are depending on
        # so our parents as network relation, or a host
        # we are depending in a hostdependency
        # or even if we are business based.
        'parent_dependencies':
            SetProp(default=set(), fill_brok=['full_status']),
        # Here it's the guys that depend on us. So it's the total
        # opposite of the parent_dependencies
        'child_dependencies':
            SetProp(default=set(), fill_brok=['full_status']),
        # Manage the unknown/unreachable during hard state
        'in_hard_unknown_reach_phase':
            BoolProp(default=False, retention=True),
        'was_in_hard_unknown_reach_phase':
            BoolProp(default=False, retention=True),
        # Set if the element just change its father/son topology
        'topology_change':
            BoolProp(default=False, fill_brok=['full_status']),
        # Trigger list
        'triggers':
            ListProp(default=[]),
        # snapshots part
        'last_snapshot':
            IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        # Keep the string of the last command launched for this element
        'last_check_command':
            StringProp(default=''),
        # Define if we are in the freshness expiration period
        'freshness_expired':
            BoolProp(default=False, fill_brok=['full_status'], retention=True),
        # Store if the freshness log got raised
        'freshness_log_raised':
            BoolProp(default=False, retention=True),
    })

    macros = {
        # Business rules output formatting related macros
        'STATUS': ('get_status', ['hosts', 'services']),
        'SHORTSTATUS': ('get_short_status', ['hosts', 'services']),
        'FULLNAME': 'get_full_name',
    }

    old_properties = {
        'normal_check_interval': 'check_interval',
        'retry_check_interval': 'retry_interval',
        'criticity': 'business_impact',
    }

    special_properties = []

    def __init__(self, params=None, parsing=True):
        if params is None:
            params = {}

        if self.__class__.my_type == 'host':
            self.convert_conf_for_unreachable(params)

        # At deserialization, thoses are dict
        # TODO: Separate parsing instance from recreated ones
        for prop in ['check_command', 'event_handler', 'snapshot_command']:
            if prop in params and isinstance(params[prop], dict):
                # We recreate the object
                setattr(self, prop, CommandCall(params[prop], parsing=parsing))
                # And remove prop, to prevent from being overridden
                del params[prop]
        if 'business_rule' in params and isinstance(params['business_rule'], dict):
            self.business_rule = DependencyNode(params['business_rule'])
            del params['business_rule']
        if 'acknowledgement' in params and isinstance(params['acknowledgement'], dict):
            self.acknowledgement = Acknowledge(params['acknowledgement'])
        super(SchedulingItem, self).__init__(params, parsing=parsing)

    def serialize(self):
        res = super(SchedulingItem, self).serialize()

        for prop in ['check_command', 'event_handler', 'snapshot_command', 'business_rule',
                     'acknowledgement']:
            if getattr(self, prop) is None:
                res[prop] = None
            else:
                res[prop] = getattr(self, prop).serialize()

        return res

    def change_check_command(self, command_params):
        """

        :param command_params: command parameters
        :type command_params: dict
        :return:
        """
        setattr(self, 'check_command', CommandCall(command_params))

    def change_event_handler(self, command_params):
        """

        :param command_params: command parameters
        :type command_params: dict
        :return:
        """
        setattr(self, 'event_handler', CommandCall(command_params))

    def change_snapshot_command(self, command_params):
        """

        :param command_params: command parameters
        :type command_params: dict
        :return:
        """
        setattr(self, 'snapshot_command', CommandCall(command_params))

    def linkify_with_triggers(self, triggers):
        """
        Link with triggers

        :param triggers: Triggers object
        :type triggers: alignak.objects.trigger.Triggers
        :return: None
        """
        # Get our trigger string and trigger names in the same list
        self.triggers.extend([self.trigger_name])

        new_triggers = []
        for tname in self.triggers:
            if tname == '':
                continue
            trigger = triggers.find_by_name(tname)
            if trigger:
                setattr(trigger, 'trigger_broker_raise_enabled', self.trigger_broker_raise_enabled)
                new_triggers.append(trigger.uuid)
            else:
                self.add_error("the %s %s has an unknown trigger_name '%s'"
                               % (self.__class__.my_type, self.get_full_name(), tname))
        self.triggers = new_triggers

    def add_flapping_change(self, sample):
        """Add a flapping sample and keep cls.flap_history samples

        :param sample: Sample to add
        :type sample: bool
        :return: None
        """
        cls = self.__class__

        # If this element is not in flapping check, or
        # the flapping is globally disable, bailout
        if not self.flap_detection_enabled or not cls.enable_flap_detection:
            return

        self.flapping_changes.append(sample)

        # Keep just 20 changes (global flap_history value)
        flap_history = cls.flap_history

        if len(self.flapping_changes) > flap_history:
            self.flapping_changes.pop(0)

    def update_flapping(self, notif_period, hosts, services):
        """Compute the sample list (self.flapping_changes) and determine
        whether the host/service is flapping or not

        :param notif_period: notification period object for this host/service
        :type notif_period: alignak.object.timeperiod.Timeperiod
        :param hosts: Hosts objects, used to create notification if necessary
        :type hosts: alignak.objects.host.Hosts
        :param services: Services objects, used to create notification if necessary
        :type services: alignak.objects.service.Services
        :return: None
        :rtype: Nonetype
        """
        flap_history = self.__class__.flap_history
        # We compute the flapping change in %
        res = 0.0
        i = 0
        for has_changed in self.flapping_changes:
            i += 1
            if has_changed:
                res += i * (1.2 - 0.8) / flap_history + 0.8
        res = res / flap_history
        res *= 100

        # We can update our value
        self.percent_state_change = res

        # Look if we are full in our states, because if not
        # the value is not accurate
        is_full = len(self.flapping_changes) >= flap_history

        # Now we get the low_flap_threshold and high_flap_threshold values
        # They can be from self, or class
        (low_flap_threshold, high_flap_threshold) = (self.low_flap_threshold,
                                                     self.high_flap_threshold)
        # TODO: no more useful because a default value is defined, but is it really correct?
        if low_flap_threshold == -1:  # pragma: no cover, never used
            cls = self.__class__
            low_flap_threshold = cls.global_low_flap_threshold
        if high_flap_threshold == -1:  # pragma: no cover, never used
            cls = self.__class__
            high_flap_threshold = cls.global_high_flap_threshold

        # Now we check is flapping change, but only if we got enough
        # states to look at the value accuracy
        if self.is_flapping and res < low_flap_threshold and is_full:
            self.is_flapping = False
            # We also raise a log entry
            self.raise_flapping_stop_log_entry(res, low_flap_threshold)
            # and a notification
            self.remove_in_progress_notifications_master()
            self.create_notifications('FLAPPINGSTOP', notif_period, hosts, services)
            # And update our status for modules
            has_changed = self.get_update_status_brok()
            self.broks.append(has_changed)

        if not self.is_flapping and res >= high_flap_threshold and is_full:
            self.is_flapping = True
            # We also raise a log entry
            self.raise_flapping_start_log_entry(res, high_flap_threshold)
            # and a notification
            self.remove_in_progress_notifications_master()
            self.create_notifications('FLAPPINGSTART', notif_period, hosts, services)
            # And update our status for modules
            has_changed = self.get_update_status_brok()
            self.broks.append(has_changed)

    def add_attempt(self):
        """Add an attempt when a object is a non-ok state

        :return: None
        """
        self.attempt += 1
        self.attempt = min(self.attempt, self.max_check_attempts)

    def is_max_attempts(self):
        """Check if max check attempt is reached

        :return: True if self.attempt >= self.max_check_attempts, otherwise False
        :rtype: bool
        """
        return self.attempt >= self.max_check_attempts

    def do_check_freshness(self, hosts, services, timeperiods, macromodulations, checkmodulations,
                           checks):
        # pylint: disable=too-many-nested-blocks
        """Check freshness and schedule a check now if necessary.

        This function is called by the scheduler if Alignak is configured to check the freshness.

        It is called for hosts that have the freshness check enabled if they are only
        passively checked.

        It is called for services that have the freshness check enabled if they are only
        passively checked and if their depending host is not in a freshness expired state
        (freshness_expiry = True).

        A log is raised when the freshess expiry is detected and the item is set as
        freshness_expiry.

        :param hosts: hosts objects, used to launch checks
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects, used launch checks
        :type services: alignak.objects.service.Services
        :param timeperiods: Timeperiods objects, used to get check_period
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param macromodulations: Macro modulations objects, used in commands (notif, check)
        :type macromodulations: alignak.objects.macromodulation.Macromodulations
        :param checkmodulations: Checkmodulations objects, used to change check command if necessary
        :type checkmodulations: alignak.objects.checkmodulation.Checkmodulations
        :param checks: checks dict, used to get checks_in_progress for the object
        :type checks: dict
        :return: A check or None
        :rtype: None | object
        """
        now = time.time()
        # Before, check if class (host or service) have check_freshness OK
        # Then check if item want freshness, then check freshness
        cls = self.__class__
        if not self.in_checking and self.freshness_threshold != 0:
            logger.debug("Checking freshness for %s, last state update: %s, now: %s.",
                         self.get_full_name(), self.last_state_update, now)
            # If we never check this item, we begin the freshness period
            if self.last_state_update == 0.0:
                self.last_state_update = now
            if self.last_state_update < now - \
                    (self.freshness_threshold + cls.additional_freshness_latency):
                # Do not create a check if the item is already freshness_expired...
                if not self.freshness_expired:
                    timeperiod = timeperiods[self.check_period]
                    if timeperiod is None or timeperiod.is_time_valid(now):
                        # Create a new check for the scheduler
                        chk = self.launch_check(now, hosts, services, timeperiods,
                                                macromodulations, checkmodulations, checks)
                        expiry_date = time.strftime("%Y-%m-%d %H:%M:%S %Z")
                        chk.output = "Freshness period expired: %s" % expiry_date
                        chk.set_type_passive()
                        chk.freshness_expired = True
                        if self.my_type == 'host':
                            if self.freshness_state == 'o':
                                chk.exit_status = 0
                            elif self.freshness_state == 'd':
                                chk.exit_status = 2
                            elif self.freshness_state in ['u', 'x']:
                                chk.exit_status = 4
                        else:
                            if self.freshness_state == 'o':
                                chk.exit_status = 0
                            elif self.freshness_state == 'w':
                                chk.exit_status = 1
                            elif self.freshness_state == 'c':
                                chk.exit_status = 2
                            elif self.freshness_state == 'u':
                                chk.exit_status = 3
                            elif self.freshness_state == 'x':
                                chk.exit_status = 4

                        return chk
                    else:
                        logger.debug("Ignored freshness check for %s, because "
                                     "we are not in the check period.", self.get_full_name())
        return None

    def set_myself_as_problem(self, hosts, services, timeperiods, bi_modulations):
        """ Raise all impact from my error. I'm setting myself
        as a problem, and I register myself as this in all
        hosts/services that depend_on_me. So they are now my
        impacts

        :param hosts: hosts objects, used to get impacts
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects, used to get impacts
        :type services: alignak.objects.service.Services
        :param timeperiods: Timeperiods objects, used to get act_depend_of_me timeperiod
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param bi_modulations: business impact modulations objects
        :type bi_modulations: alignak.object.businessimpactmodulation.Businessimpactmodulations
        :return: None
        """
        now = time.time()

        self.is_problem = True
        # we should warn potentials impact of our problem
        # and they should be cool to register them so I've got
        # my impacts list
        impacts = list(self.impacts)
        for (impact_id, status, timeperiod_id, _) in self.act_depend_of_me:
            # Check if the status is ok for impact
            if impact_id in hosts:
                impact = hosts[impact_id]
            elif impact_id in services:
                impact = services[impact_id]
            else:
                logger.warning("Problem with my impacts: %s", self)
            timeperiod = timeperiods[timeperiod_id]
            for stat in status:
                if self.is_state(stat):
                    # now check if we should bailout because of a
                    # not good timeperiod for dep
                    if timeperiod is None or timeperiod.is_time_valid(now):
                        new_impacts = impact.register_a_problem(self, hosts, services, timeperiods,
                                                                bi_modulations)
                        impacts.extend(new_impacts)

        # Only update impacts and create new brok if impacts changed.
        s_impacts = set(impacts)
        if s_impacts == set(self.impacts):
            return
        self.impacts = list(s_impacts)

        # We can update our business_impact value now
        self.update_business_impact_value(hosts, services, timeperiods, bi_modulations)

        # And we register a new broks for update status
        brok = self.get_update_status_brok()
        self.broks.append(brok)

    def update_business_impact_value(self, hosts, services, timeperiods, bi_modulations):
        """We update our 'business_impact' value with the max of
        the impacts business_impact if we got impacts. And save our 'configuration'
        business_impact if we do not have do it before
        If we do not have impacts, we revert our value

        :param hosts: hosts objects, used to get impacts
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects, used to get impacts
        :type services: alignak.objects.service.Services
        :param timeperiods: Timeperiods objects, used to get modulation_period
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param bi_modulations: business impact modulations objects
        :type bi_modulations: alignak.object.businessimpactmodulation.Businessimpactmodulations
        :return: None
        TODO: SchedulingItem object should not handle other schedulingitem obj.
              We should call obj.register* on both obj.
              This is 'Java' style
        """
        # First save our business_impact if not already do
        if self.my_own_business_impact == -1:
            self.my_own_business_impact = self.business_impact

        # We look at our crit modulations. If one apply, we take apply it
        # and it's done
        in_modulation = False
        for impactmod_id in self.business_impact_modulations:
            now = time.time()
            impactmod = bi_modulations[impactmod_id]
            period = timeperiods[impactmod.modulation_period]
            if period is None or period.is_time_valid(now):
                self.business_impact = impactmod.business_impact
                in_modulation = True
                # We apply the first available, that's all
                break

        # If we truly have impacts, we get the max business_impact
        # if it's huge than ourselves
        if self.impacts:
            bp_impacts = [hosts[elem].business_impact for elem in self.impacts if elem in hosts]
            bp_impacts.extend([services[elem].business_impact for elem in self.impacts
                               if elem in services])
            self.business_impact = max(self.business_impact, max(bp_impacts))
            return

        # If we are not a problem, we setup our own_crit if we are not in a
        # modulation period
        if self.my_own_business_impact != -1 and not in_modulation:
            self.business_impact = self.my_own_business_impact

    def no_more_a_problem(self, hosts, services, timeperiods, bi_modulations):
        """Remove this objects as an impact for other schedulingitem.

        :param hosts: hosts objects, used to get impacts
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects, used to get impacts
        :type services: alignak.objects.service.Services
        :param timeperiods: Timeperiods objects, used for update_business_impact_value
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param bi_modulations: business impact modulation are used when setting myself as problem
        :type bi_modulations: alignak.object.businessimpactmodulation.Businessimpactmodulations
        :return: None
        TODO: SchedulingItem object should not handle other schedulingitem obj.
              We should call obj.register* on both obj.
              This is 'Java' style
        """
        was_pb = self.is_problem
        if self.is_problem:
            self.is_problem = False

            # we warn impacts that we are no more a problem
            for impact_id in self.impacts:
                if impact_id in hosts:
                    impact = hosts[impact_id]
                else:
                    impact = services[impact_id]
                impact.deregister_a_problem(self)

            # we can just drop our impacts list
            self.impacts = []

        # We update our business_impact value, it's not a huge thing :)
        self.update_business_impact_value(hosts, services, timeperiods, bi_modulations)

        # If we were a problem, we say to everyone
        # our new status, with good business_impact value
        if was_pb:
            # And we register a new broks for update status
            brok = self.get_update_status_brok()
            self.broks.append(brok)

    def register_a_problem(self, prob, hosts, services, timeperiods, bi_modulations):
        """Call recursively by potentials impacts so they
        update their source_problems list. But do not
        go below if the problem is not a real one for me
        like If I've got multiple parents for examples

        :param prob: problem to register
        :type prob: alignak.objects.schedulingitem.SchedulingItem
        :param hosts: hosts objects, used to get object in act_depend_of_me
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects, used to get object in act_depend_of_me
        :type services: alignak.objects.service.Services
        :param timeperiods: Timeperiods objects, used for all kind of timeperiod (notif, check)
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param bi_modulations: business impact modulation are used when setting myself as problem
        :type bi_modulations: alignak.object.businessimpactmodulation.Businessimpactmodulations
        :return: list of host/service that are impacts
        :rtype: list[alignak.objects.schedulingitem.SchedulingItem]
        TODO: SchedulingItem object should not handle other schedulingitem obj.
              We should call obj.register* on both obj.
              This is 'Java' style
        """
        # Maybe we already have this problem? If so, bailout too
        if prob.uuid in self.source_problems:
            return []

        now = time.time()
        was_an_impact = self.is_impact
        # Our father already look of he impacts us. So if we are here,
        # it's that we really are impacted
        self.is_impact = True

        impacts = []
        # Ok, if we are impacted, we can add it in our
        # problem list
        # TODO: remove this unused check
        if self.is_impact:
            # Maybe I was a problem myself, now I can say: not my fault!
            if self.is_problem:
                self.no_more_a_problem(hosts, services, timeperiods, bi_modulations)

            # Ok, we are now an impact, we should take the good state
            # but only when we just go in impact state
            if not was_an_impact:
                self.set_impact_state()

            # Ok now we can be a simple impact
            impacts.append(self.uuid)
            if prob.uuid not in self.source_problems:
                self.source_problems.append(prob.uuid)
            # we should send this problem to all potential impact that
            # depend on us
            for (impact_id, status, timeperiod_id, _) in self.act_depend_of_me:
                # Check if the status is ok for impact
                if impact_id in hosts:
                    impact = hosts[impact_id]
                else:
                    impact = services[impact_id]
                timeperiod = timeperiods[timeperiod_id]
                for stat in status:
                    if self.is_state(stat):
                        # now check if we should bailout because of a
                        # not good timeperiod for dep
                        if timeperiod is None or timeperiod.is_time_valid(now):
                            new_impacts = impact.register_a_problem(prob, hosts,
                                                                    services, timeperiods,
                                                                    bi_modulations)
                            impacts.extend(new_impacts)

            # And we register a new broks for update status
            brok = self.get_update_status_brok()
            self.broks.append(brok)

        # now we return all impacts (can be void of course)
        return impacts

    def deregister_a_problem(self, prob):
        """Remove the problem from our problems list
        and check if we are still 'impacted'

        :param prob: problem to remove
        :type prob: alignak.objects.schedulingitem.SchedulingItem
        :return: None
        """
        self.source_problems.remove(prob.uuid)

        # For know if we are still an impact, maybe our dependencies
        # are not aware of the remove of the impact state because it's not ordered
        # so we can just look at if we still have some problem in our list
        if not self.source_problems:
            self.is_impact = False
            # No more an impact, we can unset the impact state
            self.unset_impact_state()

        # And we register a new broks for update status
        brok = self.get_update_status_brok()
        self.broks.append(brok)

    def is_enable_action_dependent(self, hosts, services):
        """
        Check if dependencies states match dependencies statuses
        This basically means that a dependency is in a bad state and
        it can explain this object state.

        :param hosts: hosts objects, used to get object in act_depend_of
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects,  used to get object in act_depend_of
        :type services: alignak.objects.service.Services
        :return: True if all dependencies matches the status, false otherwise
        :rtype: bool
        """
        # Use to know if notification is raise or not
        enable_notif = False
        for (dep_id, status, _, _) in self.act_depend_of:
            if 'n' in status:
                enable_notif = True
            else:
                if dep_id in hosts:
                    dep = hosts[dep_id]
                else:
                    dep = services[dep_id]
                p_is_down = False
                dep_match = [dep.is_state(stat) for stat in status]
                # check if the parent match a case, so he is down
                if True in dep_match:
                    p_is_down = True
                if not p_is_down:
                    enable_notif = True
        return enable_notif

    def check_and_set_unreachability(self, hosts, services):
        """
        Check if all dependencies are down, if yes set this object
        as unreachable.

        :param hosts: hosts objects, used to get object in act_depend_of
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects,  used to get object in act_depend_of
        :type services: alignak.objects.service.Services
        :return: None
        """
        parent_is_down = []
        for (dep_id, _, _, _) in self.act_depend_of:
            if dep_id in hosts:
                dep = hosts[dep_id]
            else:
                dep = services[dep_id]
            if dep.state in ['d', 'DOWN', 'c', 'CRITICAL', 'u', 'UNKNOWN', 'x', 'UNREACHABLE']:
                parent_is_down.append(True)
            else:
                parent_is_down.append(False)
        if False in parent_is_down:
            return
        # all parents down
        self.set_unreachable()

    def do_i_raise_dependency(self, status, inherit_parents, hosts, services, timeperiods):
        """Check if this object or one of its dependency state (chk dependencies) match the status

        :param status: state list where dependency matters (notification failure criteria)
        :type status: list
        :param inherit_parents: recurse over parents
        :type inherit_parents: bool
        :param hosts: hosts objects, used to raise dependency check
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects, used to raise dependency check
        :type services: alignak.objects.service.Services
        :param timeperiods: Timeperiods objects, used for all kind of timeperiod (notif, check)
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: True if one state matched the status list, otherwise False
        :rtype: bool
        """
        # Do I raise dep?
        for stat in status:
            if self.is_state(stat):
                return True

        # If we do not inherit parent, we have no reason to be blocking
        if not inherit_parents:
            return False

        # Ok, I do not raise dep, but my dep maybe raise me
        now = time.time()
        for (dep_id, dep_status, _, timeperiod_id, inh_parent) in self.chk_depend_of:
            if dep_id in hosts:
                dep = hosts[dep_id]
            else:
                dep = services[dep_id]
            timeperiod = timeperiods[timeperiod_id]
            if dep.do_i_raise_dependency(dep_status, inh_parent, hosts, services, timeperiods):
                if timeperiod is None or timeperiod.is_time_valid(now):
                    return True

        # No, I really do not raise...
        return False

    def is_no_check_dependent(self, hosts, services, timeperiods):
        """Check if there is some host/service that this object depend on
        has a state in the status list .

        :param hosts: hosts objects, used to raise dependency check
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects, used to raise dependency check
        :type services: alignak.objects.service.Services
        :param timeperiods: Timeperiods objects, used for all kind of timeperiod (notif, check)
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: True if this object has a check dependency, otherwise False
        :rtype: bool
        """
        now = time.time()
        for (dep_id, status, _, timeperiod_id, inh_parent) in self.chk_depend_of:
            timeperiod = timeperiods[timeperiod_id]
            if timeperiod is None or timeperiod.is_time_valid(now):
                if dep_id in hosts:
                    dep = hosts[dep_id]
                else:
                    dep = services[dep_id]
                if dep.do_i_raise_dependency(status, inh_parent, hosts, services, timeperiods):
                    return True
        return False

    def raise_dependencies_check(self, ref_check, hosts, services, timeperiods, macromodulations,
                                 checkmodulations, checks):
        """Get checks that we depend on if EVERY following conditions is met::

        * timeperiod is valid
        * dep.last_state_update < now - cls.cached_check_horizon (check of dependency is "old")

        :param ref_check: Check we want to get dependency from
        :type ref_check: alignak.check.Check
        :param hosts: hosts objects, used for almost every operation
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects, used for almost every operation
        :type services: alignak.objects.service.Services
        :param timeperiods: Timeperiods objects, used for all kind of timeperiod (notif, check)
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param macromodulations: Macro modulations objects, used in commands (notif, check)
        :type macromodulations: alignak.objects.macromodulation.Macromodulations
        :param checkmodulations: Checkmodulations objects, used to change check command if necessary
        :type checkmodulations: alignak.objects.checkmodulation.Checkmodulations
        :param checks: checks dict, used to get checks_in_progress for the object
        :type checks: dict
        :return: check created and check in_checking
        :rtype: dict
        """
        now = time.time()
        cls = self.__class__
        new_checks = []
        checking_checks = []
        for (dep_id, _, timeperiod_id, _) in self.act_depend_of:
            if dep_id in hosts:
                dep_item = hosts[dep_id]
            else:
                dep_item = services[dep_id]
            timeperiod = timeperiods[timeperiod_id]
            # If the dep_item timeperiod is not valid, do not raise the dep,
            # None=everytime
            if timeperiod is None or timeperiod.is_time_valid(now):
                # if the update is 'fresh', do not raise dep,
                # cached_check_horizon = cached_service_check_horizon for service
                if dep_item.last_state_update < now - cls.cached_check_horizon:
                    # Do not launch the check if it depends on a passive check of if a check
                    # is yet planned
                    if dep_item.active_checks_enabled:
                        if not dep_item.in_checking:
                            newchk = dep_item.launch_check(now, hosts, services, timeperiods,
                                                           macromodulations, checkmodulations,
                                                           checks, ref_check, dependent=True)
                            if newchk is not None:
                                new_checks.append(newchk)
                        else:
                            if dep_item.checks_in_progress:
                                check_uuid = dep_item.checks_in_progress[0]
                                checks[check_uuid].depend_on_me.append(ref_check)
                                checking_checks.append(check_uuid)
        return {'new': new_checks, 'checking': checking_checks}

    def schedule(self, hosts, services, timeperiods, macromodulations, checkmodulations,
                 checks, force=False, force_time=None):
        """Main scheduling function
        If a check is in progress, or active check are disabled, do not schedule a check.
        The check interval change with HARD state::

        * SOFT: retry_interval
        * HARD: check_interval

        The first scheduling is evenly distributed, so all checks
        are not launched at the same time.


        :param hosts: hosts objects, used for almost every operation
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects, used for almost every operation
        :type services: alignak.objects.service.Services
        :param timeperiods: Timeperiods objects, used for all kind of timeperiod (notif, check)
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param macromodulations: Macro modulations objects, used in commands (notif, check)
        :type macromodulations: alignak.objects.macromodulation.Macromodulations
        :param checkmodulations: Checkmodulations objects, used to change check command if necessary
        :type checkmodulations: alignak.objects.checkmodulation.Checkmodulations
        :param checks: checks dict, used to get checks_in_progress for the object
        :type checks: dict
        :param force: tell if we forced this object to schedule a check
        :type force: bool
        :param force_time: time we would like the check to be scheduled
        :type force_time: None | int
        :return: None
        """
        # if last_chk == 0 put in a random way so all checks
        # are not in the same time

        # next_chk il already set, do not change
        # unless we force the check or the time
        if self.in_checking and not (force or force_time):
            return None

        cls = self.__class__
        # if no active check and no force, no check
        if (not self.active_checks_enabled or not cls.execute_checks) and not force:
            return None

        now = time.time()

        # If check_interval is 0, we should not add it for a service
        # but suppose a 5min sched for hosts
        if self.check_interval == 0 and not force:
            if cls.my_type == 'service':
                return None
            else:  # host
                self.check_interval = 300 / cls.interval_length

        # Interval change is in a HARD state or not
        # If the retry is 0, take the normal value
        if self.state_type == 'HARD' or self.retry_interval == 0:
            interval = self.check_interval * cls.interval_length
        else:  # TODO: if no retry_interval?
            interval = self.retry_interval * cls.interval_length

        # Determine when a new check (randomize and distribute next check time)
        # or recurring check should happen.
        if self.next_chk == 0:
            # At the start, we cannot have an interval more than cls.max_check_spread
            # is service_max_check_spread or host_max_check_spread in config
            interval = min(interval, cls.max_check_spread * cls.interval_length)
            time_add = interval * random.uniform(0.0, 1.0)
        else:
            time_add = interval

        # Do the actual Scheduling now

        # If not force_time, try to schedule
        if force_time is None:

            check_period = timeperiods[self.check_period]

            # Do not calculate next_chk based on current time, but
            # based on the last check execution time.
            # Important for consistency of data for trending.
            if self.next_chk == 0 or self.next_chk is None:
                self.next_chk = now

            # If the neck_chk is already in the future, do not touch it.
            # But if ==0, means was 0 in fact, schedule it too
            if self.next_chk <= now:
                # maybe we do not have a check_period, if so, take always good (24x7)
                if check_period:
                    self.next_chk = check_period.get_next_valid_time_from_t(
                        self.next_chk + time_add
                    )
                else:
                    self.next_chk = int(self.next_chk + time_add)

            # Maybe we load next_chk from retention and  the
            # value of the next_chk is still the past even
            # after add an interval
            if self.next_chk < now:
                interval = min(interval, cls.max_check_spread * cls.interval_length)
                time_add = interval * random.uniform(0.0, 1.0)

                # if we got a check period, use it, if now, use now
                if check_period:
                    self.next_chk = check_period.get_next_valid_time_from_t(now + time_add)
                else:
                    self.next_chk = int(now + time_add)
            # else: keep the self.next_chk value in the future
        else:
            self.next_chk = int(force_time)

        # If next time is None, do not go
        if self.next_chk is None:
            # Nagios do not raise it, I'm wondering if we should
            return None

        logger.debug("-> schedule: %s / %s (interval: %d, added: %d)",
                     self.get_full_name(),
                     datetime.datetime.fromtimestamp(self.next_chk).strftime('%Y-%m-%d %H:%M:%S'),
                     interval, time_add)
        # Get the command to launch, and put it in queue
        return self.launch_check(self.next_chk, hosts, services, timeperiods, macromodulations,
                                 checkmodulations, checks, force=force)

    def compensate_system_time_change(self, difference):  # pragma: no cover,
        # not with unit tests
        """If a system time change occurs we have to update
        properties time related to reflect change

        :param difference: difference between new time and old time
        :type difference:
        :return: None
        """
        # We only need to change some value
        for prop in ('last_notification', 'last_state_change', 'last_hard_state_change'):
            val = getattr(self, prop)  # current value
            # Do not go below 1970 :)
            val = max(0, val + difference)  # diff may be negative
            setattr(self, prop, val)

    def disable_active_checks(self, checks):
        """Disable active checks for this host/service
        Update check in progress with current object information

        :param checks: Checks object, to change all checks in progress
        :type checks: alignak.objects.check.Checks
        :return: None
        """
        self.active_checks_enabled = False
        for chk_id in self.checks_in_progress:
            chk = checks[chk_id]
            chk.status = 'waitconsume'
            chk.exit_status = self.state_id
            chk.output = self.output
            chk.check_time = time.time()
            chk.execution_time = 0
            chk.perf_data = self.perf_data

    def remove_in_progress_check(self, check):
        """Remove check from check in progress

        :param check: Check to remove
        :type check: alignak.objects.check.Check
        :return: None
        """
        # The check is consumed, update the in_checking properties
        if check in self.checks_in_progress:
            self.checks_in_progress.remove(check)
        self.update_in_checking()

    def update_in_checking(self):
        """Update in_checking attribute.
        Object is in checking if we have checks in check_in_progress list

        :return: None
        """
        self.in_checking = (len(self.checks_in_progress) != 0)

    def remove_in_progress_notification(self, notif):
        """
        Remove a notification and mark them as zombie

        :param notif: the notification to remove
        :type notif:
        :return: None
        """
        if notif.uuid in self.notifications_in_progress:
            notif.status = 'zombie'
            del self.notifications_in_progress[notif.uuid]

    def remove_in_progress_notifications(self):
        """Remove all notifications from notifications_in_progress

        :return:None
        """
        for notif in self.notifications_in_progress.values():
            self.remove_in_progress_notification(notif)

    def remove_in_progress_notifications_master(self):
        """Remove only the master notifications

        :return: None
        """
        for notif in self.notifications_in_progress.values():
            if notif.is_a == 'notification' and not notif.contact:
                self.remove_in_progress_notification(notif)

    def get_event_handlers(self, hosts, macromodulations, timeperiods, ext_cmd=False):
        """Raise event handlers if NONE of the following conditions is met::

        * externalcmd is False and event_handlers are disabled (globally or locally)
        * externalcmd is False and object is in scheduled dowtime and no event handlers in downtime
        * self.event_handler and cls.global_event_handler are None

        :param hosts: hosts objects, used to get data for macros
        :type hosts: alignak.objects.host.Hosts
        :param macromodulations: Macro modulations objects, used in commands (notif, check)
        :type macromodulations: alignak.objects.macromodulation.Macromodulations
        :param timeperiods: Timeperiods objects, used for macros evaluation
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param ext_cmd: tells if this function was called when handling an external_command.
        :type ext_cmd: bool
        :return: None
        """
        cls = self.__class__

        # The external command always pass
        # if not, only if we enable them (auto launch)
        if not ext_cmd and (not self.event_handler_enabled or not cls.enable_event_handlers):
            logger.debug("Event handler is disabled for %s", self.get_full_name())
            return

        # If we do not force and we are in downtime, bailout
        # if the no_event_handlers_during_downtimes is 1 in conf
        if not ext_cmd and self.in_scheduled_downtime and cls.no_event_handlers_during_downtimes:
            logger.debug("Event handler wilkl not be launched. "
                         "The item %s is in a scheduled downtime", self.get_full_name())
            return

        if self.event_handler is not None:
            event_handler = self.event_handler
        elif cls.global_event_handler is not None:
            event_handler = cls.global_event_handler
        else:
            return

        data = [self]
        if getattr(self, "host", None):
            data = [hosts[self.host], self]

        macroresolver = MacroResolver()
        cmd = macroresolver.resolve_command(event_handler, data, macromodulations, timeperiods)

        event_h = EventHandler({'command': cmd, 'timeout': cls.event_handler_timeout,
                               'ref': self.uuid, 'reactionner_tag': event_handler.reactionner_tag})
        self.raise_event_handler_log_entry(event_handler)

        # ok we can put it in our temp action queue
        self.actions.append(event_h)

    def get_snapshot(self, hosts, macromodulations, timeperiods):  # pragma: no cover, not yet!
        """
        Raise snapshot event handlers if NONE of the following conditions is met::

        * snapshot_command is None
        * snapshot_enabled is disabled
        * snapshot_criteria does not matches current state
        * last_snapshot > now - snapshot_interval * interval_length (previous snapshot too early)
        * snapshot_period is not valid

        :param hosts: hosts objects, used to get data for macros
        :type hosts: alignak.objects.host.Hosts
        :param macromodulations: Macro modulations objects, used in commands (notif, check)
        :type macromodulations: alignak.objects.macromodulation.Macromodulations
        :param timeperiods: Timeperiods objects, used for snapshot period and macros evaluation
        :type timeperiods: alignak.objects.timeperiod.Timeperiods

        :return: None
        """
        # We should have a snapshot_command, to be enabled and of course
        # in the good time and state :D
        if self.snapshot_command is None:
            return

        if not self.snapshot_enabled:
            return

        # look at if one state is matching the criteria
        boolmap = [self.is_state(s) for s in self.snapshot_criteria]
        if True not in boolmap:
            return

        # Time based checks now, we should be in the period and not too far
        # from the last_snapshot
        now = int(time.time())
        cls = self.__class__
        if self.last_snapshot > now - self.snapshot_interval * cls.interval_length:  # too close
            return

        # no period means 24x7 :)
        timeperiod = timeperiods[self.snapshot_period]
        if timeperiod is not None and not timeperiod.is_time_valid(now):
            return

        cls = self.__class__
        macroresolver = MacroResolver()
        if getattr(self, "host", None):
            data = [hosts[self.host], self]
        else:
            data = [self]
        cmd = macroresolver.resolve_command(self.snapshot_command, data, macromodulations,
                                            timeperiods)
        reac_tag = self.snapshot_command.reactionner_tag
        event_h = EventHandler({'command': cmd, 'timeout': cls.event_handler_timeout,
                               'ref': self.uuid, 'reactionner_tag': reac_tag, 'is_snapshot': True})
        self.raise_snapshot_log_entry(self.snapshot_command)

        # we save the time we launch the snap
        self.last_snapshot = now

        # ok we can put it in our temp action queue
        self.actions.append(event_h)

    def check_for_flexible_downtime(self, timeperiods, hosts, services):
        """Enter in a downtime if necessary and raise start notification
        When a non Ok state occurs we try to raise a flexible downtime.

        :param timeperiods: Timeperiods objects, used for downtime period
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param hosts: hosts objects, used to enter downtime
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects, used to enter downtime
        :type services: alignak.objects.service.Services
        :return: None
        """
        status_updated = False
        for downtime_id in self.downtimes:
            downtime = self.downtimes[downtime_id]
            # Activate flexible downtimes (do not activate triggered downtimes)
            # Note: only activate if we are between downtime start and end time!
            if not downtime.fixed and not downtime.is_in_effect and \
                    downtime.start_time <= self.last_chk and \
                    downtime.end_time >= self.last_chk and \
                    self.state_id != 0 and downtime.trigger_id in ['', '0']:
                # returns downtimestart notifications
                self.broks.extend(downtime.enter(timeperiods, hosts, services))
                status_updated = True
        if status_updated is True:
            self.broks.append(self.get_update_status_brok())

    def update_hard_unknown_phase_state(self):
        """Update in_hard_unknown_reach_phase attribute and
        was_in_hard_unknown_reach_phase
        UNKNOWN during a HARD state are not so important, and they should
         not raise notif about it

        :return: None
        """
        self.was_in_hard_unknown_reach_phase = self.in_hard_unknown_reach_phase

        # We do not care about SOFT state at all
        # and we are sure we are no more in such a phase
        if self.state_type != 'HARD' or self.last_state_type != 'HARD':
            self.in_hard_unknown_reach_phase = False

        # So if we are not in already in such a phase, we check for
        # a start or not. So here we are sure to be in a HARD/HARD following
        # state
        if not self.in_hard_unknown_reach_phase:
            if self.state == 'UNKNOWN' and self.last_state != 'UNKNOWN' \
                    or self.state == 'UNREACHABLE' and self.last_state != 'UNREACHABLE':
                self.in_hard_unknown_reach_phase = True
                # We also backup with which state we was before enter this phase
                self.state_before_hard_unknown_reach_phase = self.last_state
                return
        else:
            # if we were already in such a phase, look for its end
            if self.state != 'UNKNOWN' and self.state != 'UNREACHABLE':
                self.in_hard_unknown_reach_phase = False

        # If we just exit the phase, look if we exit with a different state
        # than we enter or not. If so, lie and say we were not in such phase
        # because we need so to raise a new notif
        if not self.in_hard_unknown_reach_phase and self.was_in_hard_unknown_reach_phase:
            if self.state != self.state_before_hard_unknown_reach_phase:
                self.was_in_hard_unknown_reach_phase = False

    def consume_result(self, chk, notif_period, hosts,
                       services, timeperiods, macromodulations, checkmodulations, bi_modulations,
                       res_modulations, triggers, checks):
        # pylint: disable=R0915,R0912,R0913,E1101
        """Consume a check return and send action in return
        main function of reaction of checks like raise notifications

        Special cases::

        * is_flapping: immediate notif when problem
        * is_in_scheduled_downtime: no notification
        * is_volatile: notif immediately (service only)

        Basically go through all cases (combination of last_state, current_state, attempt number)
        and do necessary actions (add attempt, raise notification., change state type.)

        :param chk: check to handle
        :type chk: alignak.objects.check.Check
        :param notif_period: notification period for this host/service
        :type notif_period: alignak.objects.timeperiod.Timeperiod
        :param hosts: hosts objects, used for almost every operation
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects, used for almost every operation
        :type services: alignak.objects.service.Services
        :param timeperiods: Timeperiods objects, used for all kind of timeperiod (notif, check)
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param macromodulations: Macro modulations objects, used in commands (notif, check)
        :type macromodulations: alignak.objects.macromodulation.Macromodulations
        :param checkmodulations: Checkmodulations objects, used to change check command if necessary
        :type checkmodulations: alignak.objects.checkmodulation.Checkmodulations
        :param bi_modulations: business impact modulation are used when setting myself as problem
        :type bi_modulations: alignak.object.businessimpactmodulation.Businessimpactmodulations
        :param res_modulations: result modulation are used to change the ouput of a check
        :type res_modulations: alignak.object.resultmodulation.Resultmodulations
        :param triggers: triggers objects, also used to change the output/status of a check, or more
        :type triggers: alignak.objects.trigger.Triggers
        :param checks: checks dict, used to get checks_in_progress for the object
        :type checks: dict
        :return: Dependent checks
        :rtype list[alignak.check.Check]
        """
        ok_up = self.__class__.ok_up  # OK for service, UP for host
        now = int(time.time())
        if not chk.freshness_expired:
            self.freshness_expired = False

        if 'TEST_LOG_ACTIONS' in os.environ:
            if os.environ['TEST_LOG_ACTIONS'] == 'WARNING':
                logger.warning("Got check result: %d for '%s'",
                               chk.exit_status, self.get_full_name())
            else:
                logger.info("Got check result: %d for '%s'",
                            chk.exit_status, self.get_full_name())

        # ============ MANAGE THE CHECK ============ #
        # Not OK, waitconsume and have dependencies, put this check in waitdep, create if
        # necessary the check of dependent items and nothing else ;)
        if chk.exit_status != 0 and chk.status == 'waitconsume' and self.act_depend_of:
            chk.status = 'waitdep'
            # Make sure the check know about his dep
            # C is my check, and he wants dependencies
            deps_checks = self.raise_dependencies_check(chk, hosts, services, timeperiods,
                                                        macromodulations, checkmodulations,
                                                        checks)
            # Get checks_id of dep
            for check in deps_checks['new']:
                chk.depend_on.append(check.uuid)
            for check_uuid in deps_checks['checking']:
                chk.depend_on.append(check_uuid)
            # we must wait dependent check checked and consumed
            return deps_checks['new']

        # Protect against bad type output
        # if str, go in unicode
        if isinstance(chk.output, str):
            chk.output = chk.output.decode('utf8', 'ignore')
            chk.long_output = chk.long_output.decode('utf8', 'ignore')

        if isinstance(chk.perf_data, str):
            chk.perf_data = chk.perf_data.decode('utf8', 'ignore')

        # We check for stalking if necessary
        # so if check is here
        self.manage_stalking(chk)

        # ============ UPDATE ITEM INFORMATION ============ #

        # Latency can be <0 is we get a check from the retention file
        # so if <0, set 0
        try:
            self.latency = max(0, chk.check_time - chk.t_to_go)
        except TypeError:  # pragma: no cover, simple protection
            pass

        # Ok, the first check is done
        self.has_been_checked = 1

        # Now get data from check
        self.execution_time = chk.execution_time
        self.u_time = chk.u_time
        self.s_time = chk.s_time
        self.last_chk = int(chk.check_time)
        self.output = chk.output
        self.long_output = chk.long_output
        # self.check_type = chk.check_type  # 0 => Active check, 1 => passive check
        if self.__class__.process_performance_data and self.process_perf_data:
            self.last_perf_data = self.perf_data
            self.perf_data = chk.perf_data

        # Before setting state, modulate them
        for resultmod_id in self.resultmodulations:
            resultmod = res_modulations[resultmod_id]
            if resultmod is not None:
                chk.exit_status = resultmod.module_return(chk.exit_status, timeperiods)

        if not chk.freshness_expired:
            # Only update the last state date if not in freshness expiry
            self.last_state_update = time.time()
            if chk.exit_status == 1 and self.__class__.my_type == 'host':
                chk.exit_status = 2

        self.set_state_from_exit_status(chk.exit_status, notif_period, hosts, services)

        self.last_state_type = self.state_type
        self.return_code = chk.exit_status

        # we change the state, do whatever we are or not in
        # an impact mode, we can put it
        self.state_changed_since_impact = True

        # The check is consumed, update the in_checking properties
        self.remove_in_progress_check(chk.uuid)

        # Used to know if a notification is raised or not
        enable_action = True

        if chk.status == 'waitdep':
            # Check dependencies
            enable_action = self.is_enable_action_dependent(hosts, services)
            # If all dependencies not ok, define item as UNREACHABLE
            self.check_and_set_unreachability(hosts, services)

        if chk.status in ['waitconsume', 'waitdep']:
            # check waiting consume or waiting result of dependencies
            if chk.depend_on_me != []:
                # one or more checks wait this check  (dependency)
                chk.status = 'havetoresolvedep'
            else:
                # the check go in zombie state to be removed later
                chk.status = 'zombie'

        # print("Check: %s / %s / %s" % (chk.exit_status, self.last_state, self.get_full_name()))
        # from UP/OK/PENDING
        # to UP/OK
        if chk.exit_status == 0 and self.last_state in (ok_up, 'PENDING'):
            self.unacknowledge_problem()
            # action in return can be notification or other checks (dependencies)
            if (self.state_type == 'SOFT') and self.last_state != 'PENDING':
                if self.is_max_attempts() and self.state_type == 'SOFT':
                    self.state_type = 'HARD'
                else:
                    self.state_type = 'SOFT'
            else:
                self.attempt = 1
                self.state_type = 'HARD'

        # from WARNING/CRITICAL/UNKNOWN/UNREACHABLE/DOWN
        # to UP/OK
        elif chk.exit_status == 0 and self.last_state not in (ok_up, 'PENDING'):
            self.unacknowledge_problem()
            if self.state_type == 'SOFT':
                # previous check in SOFT
                if not chk.is_dependent():
                    self.add_attempt()
                self.raise_alert_log_entry()
                # Eventhandler gets OK;SOFT;++attempt, no notification needed
                self.get_event_handlers(hosts, macromodulations, timeperiods)
                # Now we are UP/OK HARD
                self.state_type = 'HARD'
                self.attempt = 1
            elif self.state_type == 'HARD':
                # previous check in HARD
                self.raise_alert_log_entry()
                # Eventhandler and notifications get OK;HARD;maxattempts
                # Ok, so current notifications are not needed, we 'zombie' them
                self.remove_in_progress_notifications_master()
                if enable_action:
                    self.create_notifications('RECOVERY', notif_period, hosts, services)
                self.get_event_handlers(hosts, macromodulations, timeperiods)
                # We stay in HARD
                self.attempt = 1

                # I'm no more a problem if I was one
                self.no_more_a_problem(hosts, services, timeperiods, bi_modulations)

        # Volatile part
        # Only for service
        elif chk.exit_status != 0 and getattr(self, 'is_volatile', False):
            # There are no repeated attempts, so the first non-ok results
            # in a hard state
            self.attempt = 1
            self.state_type = 'HARD'
            # status != 0 so add a log entry (before actions that can also raise log
            # it is smarter to log error before notification)
            self.raise_alert_log_entry()
            self.check_for_flexible_downtime(timeperiods, hosts, services)
            self.remove_in_progress_notifications_master()
            if enable_action:
                self.create_notifications('PROBLEM', notif_period, hosts, services)
            # Ok, event handlers here too
            self.get_event_handlers(hosts, macromodulations, timeperiods)

            # PROBLEM/IMPACT
            # I'm a problem only if I'm the root problem,
            if enable_action:
                self.set_myself_as_problem(hosts, services, timeperiods, bi_modulations)

        # from UP/OK
        # to WARNING/CRITICAL/UNKNOWN/UNREACHABLE/DOWN
        elif chk.exit_status != 0 and self.last_state in (ok_up, 'PENDING'):
            if self.is_max_attempts():
                # Now we are in HARD
                self.state_type = 'HARD'
                self.raise_alert_log_entry()
                self.remove_in_progress_notifications_master()
                self.check_for_flexible_downtime(timeperiods, hosts, services)
                if enable_action:
                    self.create_notifications('PROBLEM', notif_period, hosts, services)
                # Oh? This is the typical go for a event handler :)
                self.get_event_handlers(hosts, macromodulations, timeperiods)

                # PROBLEM/IMPACT
                # I'm a problem only if I'm the root problem,
                if enable_action:
                    self.set_myself_as_problem(hosts, services, timeperiods, bi_modulations)

            else:
                # This is the first NON-OK result. Initiate the SOFT-sequence
                # Also launch the event handler, he might fix it.
                self.attempt = 1
                self.state_type = 'SOFT'
                self.raise_alert_log_entry()
                self.get_event_handlers(hosts, macromodulations, timeperiods)

        # from WARNING/CRITICAL/UNKNOWN/UNREACHABLE/DOWN
        # to WARNING/CRITICAL/UNKNOWN/UNREACHABLE/DOWN
        elif chk.exit_status != 0 and self.last_state != ok_up:
            if self.state_type == 'SOFT':
                if not chk.is_dependent():
                    self.add_attempt()
                # Cases where go:
                #  * warning soft => critical hard
                #  * warning soft => critical soft
                if self.state != self.last_state:
                    self.unacknowledge_problem_if_not_sticky()
                if self.is_max_attempts():
                    # Ok here is when we just go to the hard state
                    self.state_type = 'HARD'
                    self.raise_alert_log_entry()
                    self.remove_in_progress_notifications_master()
                    self.check_for_flexible_downtime(timeperiods, hosts, services)
                    if enable_action:
                        self.create_notifications('PROBLEM', notif_period, hosts, services)
                    # So event handlers here too
                    self.get_event_handlers(hosts, macromodulations, timeperiods)

                    # PROBLEM/IMPACT
                    # I'm a problem only if I'm the root problem,
                    if enable_action:
                        self.set_myself_as_problem(hosts, services, timeperiods, bi_modulations)

                else:
                    self.raise_alert_log_entry()
                    # eventhandler is launched each time during the soft state
                    self.get_event_handlers(hosts, macromodulations, timeperiods)

            else:
                # Send notifications whenever the state has changed. (W -> C)
                # but not if the current state is UNKNOWN (hard C-> hard U -> hard C should
                # not restart notifications)
                if self.state != self.last_state:
                    self.update_hard_unknown_phase_state()
                    if not self.in_hard_unknown_reach_phase and not \
                            self.was_in_hard_unknown_reach_phase:
                        self.unacknowledge_problem_if_not_sticky()
                        self.raise_alert_log_entry()
                        self.remove_in_progress_notifications_master()
                        if enable_action:
                            self.create_notifications('PROBLEM', notif_period, hosts, services)
                        self.get_event_handlers(hosts, macromodulations, timeperiods)

                elif self.in_scheduled_downtime_during_last_check is True:
                    # during the last check i was in a downtime. but now
                    # the status is still critical and notifications
                    # are possible again. send an alert immediately
                    self.remove_in_progress_notifications_master()
                    if enable_action:
                        self.create_notifications('PROBLEM', notif_period, hosts, services)

                # PROBLEM/IMPACT
                # Forces problem/impact registration even if no state change
                # was detected as we may have a non OK state restored from
                # retention data. This way, we rebuild problem/impact hierarchy.
                # I'm a problem only if I'm the root problem,
                if enable_action:
                    self.set_myself_as_problem(hosts, services, timeperiods, bi_modulations)

                # case no notification exist but notifications are enabled (for example, we
                # enable notifications with external command)
                if enable_action and self.notifications_enabled and \
                        self.current_notification_number == 0:
                    self.remove_in_progress_notifications_master()
                    self.create_notifications('PROBLEM', notif_period, hosts, services)

        self.update_hard_unknown_phase_state()
        # Reset this flag. If it was true, actions were already taken
        self.in_scheduled_downtime_during_last_check = False

        # now is the time to update state_type_id
        # and our last_hard_state
        if self.state_type == 'HARD':
            self.state_type_id = 1
            self.last_hard_state = self.state
            self.last_hard_state_id = self.state_id
        else:
            self.state_type_id = 0

        # Fill last_hard_state_change to now
        # if we just change from SOFT->HARD or
        # in HARD we change of state (Warning->critical, or critical->ok, etc etc)
        if self.state_type == 'HARD' and \
                (self.last_state_type == 'SOFT' or self.last_state != self.state):
            self.last_hard_state_change = int(time.time())

            # If the check is a freshness one, set freshness as expired
            if chk.freshness_expired:
                self.freshness_expired = True

        # update event/problem-counters
        self.update_event_and_problem_id()

        # Raise a log if freshness check expired
        if chk.freshness_expired:
            self.raise_freshness_log_entry(int(now - self.last_state_update -
                                               self.freshness_threshold))

        # if self.freshness_expired and not self.freshness_log_raised:
        #     self.raise_freshness_log_entry(int(now - self.last_state_update -
        #                                        self.freshness_threshold))

        # Now launch trigger if needed.
        # If it's from a trigger raised check, do not raise a new one
        if not chk.from_trigger:
            self.eval_triggers(triggers)
        if chk.from_trigger or not chk.from_trigger and \
                sum(1 for t in self.triggers
                    if triggers[t].trigger_broker_raise_enabled) == 0:
            self.broks.append(self.get_check_result_brok())

        self.get_perfdata_command(hosts, macromodulations, timeperiods)
        # Also snapshot if need :)
        self.get_snapshot(hosts, macromodulations, timeperiods)
        return []

    def update_event_and_problem_id(self):
        """Update current_event_id and current_problem_id
        Those attributes are used for macros (SERVICEPROBLEMID ...)

        :return: None
        """
        ok_up = self.__class__.ok_up  # OK for service, UP for host
        if (self.state != self.last_state and self.last_state != 'PENDING' or
                self.state != ok_up and self.last_state == 'PENDING'):
            SchedulingItem.current_event_id += 1
            self.last_event_id = self.current_event_id
            self.current_event_id = SchedulingItem.current_event_id
            # now the problem_id
            if self.state != ok_up and self.last_state == 'PENDING':
                # broken ever since i can remember
                SchedulingItem.current_problem_id += 1
                self.last_problem_id = self.current_problem_id
                self.current_problem_id = SchedulingItem.current_problem_id
            elif self.state != ok_up and self.last_state != ok_up:
                # State transitions between non-OK states
                # (e.g. WARNING to CRITICAL) do not cause
                # this problem id to increase.
                pass
            elif self.state == ok_up:
                # If the service is currently in an OK state,
                # this macro will be set to zero (0).
                self.last_problem_id = self.current_problem_id
                self.current_problem_id = 0
            else:
                # Every time a service (or host) transitions from
                # an OK or UP state to a problem state, a global
                # problem ID number is incremented by one (1).
                SchedulingItem.current_problem_id += 1
                self.last_problem_id = self.current_problem_id
                self.current_problem_id = SchedulingItem.current_problem_id

    def prepare_notification_for_sending(self, notif, contact, macromodulations, timeperiods,
                                         host_ref):
        """Used by scheduler when a notification is ok to be sent (to reactionner).
        Here we update the command with status of now, and we add the contact to set of
        contact we notified. And we raise the log entry

        :param notif: notification to send
        :type notif: alignak.objects.notification.Notification
        :param macromodulations: Macro modulations objects, used in the notification command
        :type macromodulations: alignak.objects.macromodulation.Macromodulations
        :param timeperiods: Timeperiods objects, used to get modulation period
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param host_ref: reference host (used for a service)
        :type host_ref: alignak.object.host.Host
        :return: None
        """
        if notif.status == 'inpoller':
            self.update_notification_command(notif, contact, macromodulations, timeperiods,
                                             host_ref)
            self.notified_contacts.add(contact.uuid)
            self.raise_notification_log_entry(notif, contact, host_ref)

    def update_notification_command(self, notif, contact, macromodulations, timeperiods,
                                    host_ref=None):
        """Update the notification command by resolving Macros
        And because we are just launching the notification, we can say
        that this contact has been notified

        :param notif: notification to send
        :type notif: alignak.objects.notification.Notification
        :param contact: contact for this host/service
        :type contact: alignak.object.contact.Contact
        :param macromodulations: Macro modulations objects, used in the notification command
        :type macromodulations: alignak.objects.macromodulation.Macromodulations
        :param timeperiods: Timeperiods objects, used to get modulation period
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param host_ref: reference host (used for a service)
        :type host_ref: alignak.object.host.Host
        :return: None
        """
        cls = self.__class__
        macrosolver = MacroResolver()
        data = [self, contact, notif]
        if host_ref:
            data.append(host_ref)
        notif.command = macrosolver.resolve_command(notif.command_call, data, macromodulations,
                                                    timeperiods)
        if cls.enable_environment_macros or notif.enable_environment_macros:
            notif.env = macrosolver.get_env_macros(data)

    def is_escalable(self, notif, escalations, timeperiods):
        """Check if a notification can be escalated.
        Basically call is_eligible for each escalation

        :param notif: notification we would like to escalate
        :type notif: alignak.objects.notification.Notification
        :param escalations: Esclations objects, used to get escalation objects (period)
        :type escalations: alignak.objects.escalation.Escalations
        :param timeperiods: Timeperiods objects, used to get escalation period
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: True if notification can be escalated, otherwise False
        :rtype: bool
        """
        cls = self.__class__

        # We search since when we are in notification for escalations
        # that are based on time
        in_notif_time = time.time() - notif.creation_time

        # Check is an escalation match the current_notification_number
        for escal_id in self.escalations:
            escal = escalations[escal_id]
            escal_period = timeperiods[escal.escalation_period]
            if escal.is_eligible(notif.t_to_go, self.state, notif.notif_nb,
                                 in_notif_time, cls.interval_length, escal_period):
                return True

        return False

    def get_next_notification_time(self, notif, escalations, timeperiods):
        """Get the next notification time for a notification
        Take the standard notification_interval or ask for our escalation
        if one of them need a smaller value to escalade

        :param notif: Notification we need time
        :type notif: alignak.objects.notification.Notification
        :param escalations: Esclations objects, used to get escalation objects (interval, period)
        :type escalations: alignak.objects.escalation.Escalations
        :param timeperiods: Timeperiods objects, used to get escalation period
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: Timestamp of next notification
        :rtype: int
        """
        res = None
        now = time.time()
        cls = self.__class__

        # Look at the minimum notification interval
        notification_interval = self.notification_interval
        # and then look for currently active notifications, and take notification_interval
        # if filled and less than the self value
        in_notif_time = time.time() - notif.creation_time
        for escal_id in self.escalations:
            escal = escalations[escal_id]
            escal_period = timeperiods[escal.escalation_period]
            if escal.is_eligible(notif.t_to_go, self.state, notif.notif_nb,
                                 in_notif_time, cls.interval_length, escal_period):
                if escal.notification_interval != -1 and \
                        escal.notification_interval < notification_interval:
                    notification_interval = escal.notification_interval

        # So take the by default time
        std_time = notif.t_to_go + notification_interval * cls.interval_length

        # Maybe the notification comes from retention data and
        # next notification alert is in the past
        # if so let use the now value instead
        if std_time < now:
            std_time = now + notification_interval * cls.interval_length

        # standard time is a good one
        res = std_time

        creation_time = notif.creation_time
        in_notif_time = now - notif.creation_time

        for escal_id in self.escalations:
            escal = escalations[escal_id]
            # If the escalation was already raised, we do not look for a new "early start"
            if escal.get_name() not in notif.already_start_escalations:
                escal_period = timeperiods[escal.escalation_period]
                next_t = escal.get_next_notif_time(std_time, self.state,
                                                   creation_time, cls.interval_length, escal_period)
                # If we got a real result (time base escalation), we add it
                if next_t is not None and now < next_t < res:
                    res = next_t

        # And we take the minimum of this result. Can be standard or escalation asked
        return res

    def get_escalable_contacts(self, notif, escalations, timeperiods):
        """Get all contacts (uniq) from eligible escalations

        :param notif: Notification to get data from (notif number...)
        :type notif: alignak.objects.notification.Notification
        :param escalations: Esclations objects, used to get escalation objects (contact, period)
        :type escalations: alignak.objects.escalation.Escalations
        :param timeperiods: Timeperiods objects, used to get escalation period
        :type timeperiods: alignak.objects.timeperiod.Timeperiods

        :return: Contact uuid list that can be notified for escalation
        :rtype: list
        """
        cls = self.__class__

        # We search since when we are in notification for escalations
        # that are based on this time
        in_notif_time = time.time() - notif.creation_time

        contacts = set()
        for escal_id in self.escalations:
            escal = escalations[escal_id]
            escal_period = timeperiods[escal.escalation_period]
            if escal.is_eligible(notif.t_to_go, self.state, notif.notif_nb,
                                 in_notif_time, cls.interval_length, escal_period):
                contacts.update(escal.contacts)
                # And we tag this escalations as started now
                notif.already_start_escalations.add(escal.get_name())

        return list(contacts)

    def create_notifications(self, n_type, notification_period, hosts, services,
                             t_wished=None, author_data=None):
        """Create a "master" notification here, which will later
        (immediately before the reactionner gets it) be split up
        in many "child" notifications, one for each contact.

        :param n_type: notification type ("PROBLEM", "RECOVERY" ...)
        :type n_type: str
        :param notification_period: notification period for this host/service
        :type notification_period: alignak.objects.timeperiod.Timeperiod
        :param hosts: hosts objects, used to check if a notif is blocked
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects, used to check if a notif is blocked
        :type services: alignak.objects.service.Services
        :param t_wished: time we want to notify
        :type t_wished: int
        :param author_data: notification author data (eg. for a downtime notification)
        :type author_data: dict (containing author, author_name ad a comment)
        :return: None
        """
        cls = self.__class__
        # t_wished==None for the first notification launch after consume
        # here we must look at the self.notification_period
        if t_wished is None:
            now = int(time.time())
            t_wished = now
            # if first notification, we must add first_notification_delay
            if self.current_notification_number == 0 and n_type == 'PROBLEM':
                last_time_non_ok_or_up = self.last_time_non_ok_or_up()
                if last_time_non_ok_or_up == 0:
                    # this happens at initial
                    t_wished = now + self.first_notification_delay * cls.interval_length
                else:
                    t_wished = last_time_non_ok_or_up + \
                        self.first_notification_delay * cls.interval_length
            if notification_period is None:
                new_t = now
            else:
                new_t = notification_period.get_next_valid_time_from_t(t_wished)
        else:
            # We follow our order
            new_t = t_wished

        if self.notification_is_blocked_by_item(notification_period, hosts, services,
                                                n_type, t_wished=t_wished,
                                                ) and \
                self.first_notification_delay == 0 and self.notification_interval == 0:
            # If notifications are blocked on the host/service level somehow
            # and repeated notifications are not configured,
            # we can silently drop this one
            return
        if n_type == 'PROBLEM':
            # Create the notification with an incremented notification_number.
            # The current_notification_number  of the item itself will only
            # be incremented when this notification (or its children)
            # have actually be sent.
            next_notif_nb = self.current_notification_number + 1
        elif n_type == 'RECOVERY':
            # Recovery resets the notification counter to zero
            self.current_notification_number = 0
            next_notif_nb = self.current_notification_number
        else:
            # downtime/flap/etc do not change the notification number
            next_notif_nb = self.current_notification_number

        data = {
            'type': n_type,
            'command': 'VOID',
            'ref': self.uuid,
            't_to_go': new_t,
            'timeout': cls.notification_timeout,
            'notif_nb': next_notif_nb,
            'host_name': getattr(self, 'host_name', ''),
            'service_description': getattr(self, 'service_description', ''),
        }
        if author_data and n_type in ['DOWNTIMESTART', 'DOWNTIMEEND']:
            data.update(author_data)

        notif = Notification(data)
        logger.debug("Created a %s notification: %s", self.my_type, n_type)

        # Keep a trace in our notifications queue
        self.notifications_in_progress[notif.uuid] = notif
        # and put it in the temp queue for scheduler
        self.actions.append(notif)

    def scatter_notification(self, notif, contacts, notifways, timeperiods, macromodulations,
                             escalations, host_ref=None):
        """In create_notifications we created a notification "template". When it's
        time to hand it over to the reactionner, this master notification needs
        to be split in several child notifications, one for each contact
        To be more exact, one for each contact who is willing to accept
        notifications of this type and at this time

        :param notif: Notification to scatter
        :type notif: alignak.objects.notification.Notification
        :param contacts: Contacts objects, used to retreive contact for this object
        :type contacts: alignak.objects.contact.Contacts
        :param notifways: Notificationway objects, used to get notific commands
        :type notifways: alignak.object.notificationway.Notificationways
        :param timeperiods: Timeperiods objects, used to check if notif are allowed at this time
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param macromodulations: Macro modulations objects, used in the notification command
        :type macromodulations: alignak.objects.macromodulation.Macromodulations
        :param escalations: Esclations objects, used to get escalated contacts
        :type escalations: alignak.objects.escalation.Escalations
        :param host_ref: reference host (used for a service)
        :type host_ref: alignak.object.host.Host

        :return: child notifications
        :rtype: list[alignak.objects.notification.Notification]
        """
        cls = self.__class__
        childnotifications = []
        escalated = False
        if notif.contact:
            # only master notifications can be split up
            return []
        if notif.type == 'RECOVERY':
            if self.first_notification_delay != 0 and not self.notified_contacts:
                # Recovered during first_notification_delay. No notifications
                # have been sent yet, so we keep quiet
                notif_contacts = []
            else:
                # The old way. Only send recover notifications to those contacts
                # who also got problem notifications
                notif_contacts = [c_id for c_id in self.notified_contacts]
            self.notified_contacts.clear()
        else:
            # Check is an escalation match. If yes, get all contacts from escalations
            if self.is_escalable(notif, escalations, timeperiods):
                notif_contacts = self.get_escalable_contacts(notif, escalations, timeperiods)
                escalated = True
            # else take normal contacts
            else:
                # notif_contacts = [contacts[c_id] for c_id in self.contacts]
                notif_contacts = self.contacts

        for contact_id in notif_contacts:
            contact = contacts[contact_id]
            # We do not want to notify again a contact with notification interval == 0
            # if has been already notified except if the item hard state changed!
            # This can happen when a service exits a downtime and it is still in
            # critical/warning (and not acknowledge)
            if notif.type == "PROBLEM" and \
                    self.notification_interval == 0 \
                    and self.state_type == 'HARD' and self.last_state_type == self.state_type \
                    and self.state == self.last_state \
                    and contact.uuid in self.notified_contacts:
                # Do not send notification
                continue
            # Get the property name for notification commands, like
            # service_notification_commands for service
            notif_commands = contact.get_notification_commands(notifways, cls.my_type)

            for cmd in notif_commands:
                # Get the notification recipients list
                recipients = ','.join([contacts[c_uuid].contact_name for c_uuid in notif_contacts])
                data = {
                    'type': notif.type,
                    'command': 'VOID',
                    'command_call': cmd,
                    'ref': self.uuid,
                    'contact': contact.uuid,
                    'contact_name': contact.contact_name,
                    'recipients': recipients,
                    't_to_go': notif.t_to_go,
                    'escalated': escalated,
                    'timeout': cls.notification_timeout,
                    'notif_nb': notif.notif_nb,
                    'reactionner_tag': cmd.reactionner_tag,
                    'enable_environment_macros': cmd.enable_environment_macros,
                    'host_name': getattr(self, 'host_name', ''),
                    'service_description': getattr(self, 'service_description', ''),
                    'author': notif.author,
                    'author_name': notif.author_name,
                    'author_alias': notif.author_alias,
                    'author_comment': notif.author_comment
                }
                child_n = Notification(data)
                if not self.notification_is_blocked_by_contact(notifways, timeperiods, child_n,
                                                               contact):
                    # Update the notification with fresh status information
                    # of the item. Example: during the notification_delay
                    # the status of a service may have changed from WARNING to CRITICAL
                    self.update_notification_command(child_n, contact, macromodulations,
                                                     timeperiods, host_ref)
                    self.raise_notification_log_entry(child_n, contact, host_ref)
                    self.notifications_in_progress[child_n.uuid] = child_n
                    childnotifications.append(child_n)

                    if notif.type == 'PROBLEM':
                        # Remember the contacts. We might need them later in the
                        # recovery code some lines above
                        self.notified_contacts.add(contact.uuid)

        return childnotifications

    def launch_check(self, timestamp, hosts, services, timeperiods,  # pylint: disable=R0913
                     macromodulations, checkmodulations, checks, ref_check=None, force=False,
                     dependent=False):
        """Launch a check (command)

        :param timestamp:
        :type timestamp: int
        :param checkmodulations: Checkmodulations objects, used to change check command if necessary
        :type checkmodulations: alignak.objects.checkmodulation.Checkmodulations
        :param ref_check:
        :type ref_check:
        :param force:
        :type force: bool
        :param dependent:
        :type dependent: bool
        :return: None or alignak.check.Check
        :rtype: None | alignak.check.Check
        """
        chk = None
        cls = self.__class__

        # Look if we are in check or not
        self.update_in_checking()

        # the check is being forced, so we just replace next_chk time by now
        if force and self.in_checking:
            now = time.time()
            c_in_progress = checks[self.checks_in_progress[0]]
            c_in_progress.t_to_go = now
            return c_in_progress

        # If I'm already in checking, Why launch a new check?
        # If ref_check_id is not None , this is a dependency_ check
        # If none, it might be a forced check, so OK, I do a new

        # Dependency check, we have to create a new check that will be launched only once (now)
        # Otherwise it will delay the next real check. this can lead to an infinite SOFT state.
        if not force and (self.in_checking and ref_check is not None):

            c_in_progress = checks[self.checks_in_progress[0]]

            # c_in_progress has almost everything we need but we cant copy.deepcopy() it
            # we need another c.uuid
            data = {
                'command': c_in_progress.command,
                'timeout': c_in_progress.timeout,
                'poller_tag': c_in_progress.poller_tag,
                'env': c_in_progress.env,
                'module_type': c_in_progress.module_type,
                't_to_go': timestamp,
                'depend_on_me': [ref_check],
                'ref': self.uuid,
                'ref_type': self.my_type,
                'dependency_check': True,
                'internal': self.got_business_rule or c_in_progress.command.startswith('_')
            }
            chk = Check(data)

            self.actions.append(chk)
            return chk

        if force or (not self.is_no_check_dependent(hosts, services, timeperiods)):
            # Fred : passive only checked host dependency
            if dependent and self.my_type == 'host' and \
                    self.passive_checks_enabled and not self.active_checks_enabled:
                logger.debug("Host check is for a host that is only passively "
                             "checked (%s), do not launch the check !", self.host_name)
                return None

            # By default we will use our default check_command
            check_command = self.check_command
            # But if a checkway is available, use this one instead.
            # Take the first available
            for chkmod_id in self.checkmodulations:
                chkmod = checkmodulations[chkmod_id]
                c_cw = chkmod.get_check_command(timeperiods, timestamp)
                if c_cw:
                    check_command = c_cw
                    break

            # Get the command to launch
            macroresolver = MacroResolver()
            if hasattr(self, 'host'):
                macrodata = [hosts[self.host], self]
            else:
                macrodata = [self]
            command_line = macroresolver.resolve_command(check_command, macrodata, macromodulations,
                                                         timeperiods)

            # remember it, for pure debugging purpose
            self.last_check_command = command_line

            # By default env is void
            env = {}

            # And get all environment variables only if needed
            if cls.enable_environment_macros or check_command.enable_environment_macros:
                env = macroresolver.get_env_macros(macrodata)

            # By default we take the global timeout, but we use the command one if it
            # define it (by default it's -1)
            timeout = cls.check_timeout
            if check_command.timeout != -1:
                timeout = check_command.timeout

            # Make the Check object and put the service in checking
            # Make the check inherit poller_tag from the command
            # And reactionner_tag too
            data = {
                'command': command_line,
                'timeout': timeout,
                'poller_tag': check_command.poller_tag,
                'env': env,
                'module_type': check_command.module_type,
                't_to_go': timestamp,
                'depend_on_me': [ref_check] if ref_check else [],
                'ref': self.uuid,
                'ref_type': self.my_type,
                'internal': self.got_business_rule or command_line.startswith('_')
            }
            chk = Check(data)

            self.checks_in_progress.append(chk.uuid)

        self.update_in_checking()

        # We need to put this new check in our actions queue
        # so scheduler can take it
        if chk is not None:
            self.actions.append(chk)
            return chk
        # None mean I already take it into account
        return None

    def get_time_to_orphanage(self):
        """Get time to orphanage ::

        * 0 : don't check for orphans
        * non zero : number of secs that can pass before marking the check an orphan.

        :return: integer with the meaning explained above
        :rtype: int
        """
        # if disabled program-wide, disable it
        if not self.check_for_orphaned:
            return 0
        # otherwise, check what my local conf says
        if self.time_to_orphanage <= 0:
            return 0
        return self.time_to_orphanage

    def get_perfdata_command(self, hosts, macromodulations, timeperiods):
        """Add event_handler to process performance data if necessary (not disabled)

        :param macromodulations: Macro modulations objects, used in commands (notif, check)
        :type macromodulations: alignak.objects.macromodulation.Macromodulations
        :return: None
        """
        cls = self.__class__
        if not cls.process_performance_data or not self.process_perf_data:
            return

        if cls.perfdata_command is not None:
            macroresolver = MacroResolver()
            if getattr(self, "host", None):
                data = [hosts[self.host], self]
            else:
                data = [self]
            cmd = macroresolver.resolve_command(cls.perfdata_command, data, macromodulations,
                                                timeperiods)
            reactionner_tag = cls.perfdata_command.reactionner_tag
            event_h = EventHandler({'command': cmd, 'timeout': cls.perfdata_timeout,
                                   'ref': self.uuid, 'reactionner_tag': reactionner_tag})

            # ok we can put it in our temp action queue
            self.actions.append(event_h)

    def create_business_rules(self, hosts, services, hostgroups, servicegroups,
                              macromodulations, timeperiods, running=False):
        """Create business rules if necessary (cmd contains bp_rule)

        :param hosts: Hosts object to look for objects
        :type hosts: alignak.objects.host.Hosts
        :param services: Services object to look for objects
        :type services: alignak.objects.service.Services
        :param running: flag used in eval_cor_pattern function
        :type running: bool
        :return: None
        """
        cmdcall = getattr(self, 'check_command', None)

        # If we do not have a command, we bailout
        if cmdcall is None:
            return

        # we get our based command, like
        # check_tcp!80 -> check_tcp
        cmd = cmdcall.call
        elts = cmd.split('!')
        base_cmd = elts[0]

        # If it's bp_rule, we got a rule :)
        if base_cmd == 'bp_rule':
            self.got_business_rule = True
            rule = ''
            if len(elts) >= 2:
                rule = '!'.join(elts[1:])
            # Only (re-)evaluate the business rule if it has never been
            # evaluated before, or it contains a macro.
            if re.match(r"\$[\w\d_-]+\$", rule) or self.business_rule is None:
                if hasattr(self, 'host'):
                    data = [hosts[self.host], self]
                else:
                    data = [self]
                macroresolver = MacroResolver()
                rule = macroresolver.resolve_simple_macros_in_string(rule, data,
                                                                     macromodulations,
                                                                     timeperiods)
                prev = getattr(self, "processed_business_rule", "")

                if rule == prev:
                    # Business rule did not change (no macro was modulated)
                    return

                fact = DependencyNodeFactory(self)
                node = fact.eval_cor_pattern(rule, hosts, services,
                                             hostgroups, servicegroups, running)
                self.processed_business_rule = rule
                self.business_rule = node

    def get_business_rule_output(self, hosts, services, macromodulations, timeperiods):
        """
        Returns a status string for business rules based items formatted
        using business_rule_output_template attribute as template.

        The template may embed output formatting for itself, and for its child
        (dependant) itmes. Childs format string is expanded into the $( and )$,
        using the string between brackets as format string.

        Any business rule based item or child macros may be used. In addition,
        the $STATUS$, $SHORTSTATUS$ and $FULLNAME$ macro which name is common
        to hosts and services may be used to ease template writing.

        Caution: only children in state not OK are displayed.

        Example:
          A business rule with a format string looking like
              "$STATUS$ [ $($TATUS$: $HOSTNAME$,$SERVICEDESC$ )$ ]"
          Would return
              "CRITICAL [ CRITICAL: host1,srv1 WARNING: host2,srv2  ]"

        :param hosts: Hosts object to look for objects
        :type hosts: alignak.objects.host.Hosts
        :param services: Services object to look for objects
        :type services: alignak.objects.service.Services
        :param macromodulations: Macromodulations object to look for objects
        :type macromodulations: alignak.objects.macromodulation.Macromodulations
        :param timeperiods: Timeperiods object to look for objects
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: status for business rules
        :rtype: str
        """
        got_business_rule = getattr(self, 'got_business_rule', False)
        # Checks that the service is a business rule.
        if got_business_rule is False or self.business_rule is None:
            return ""
        # Checks that the business rule has a format specified.
        output_template = self.business_rule_output_template
        if not output_template:
            return ""
        macroresolver = MacroResolver()

        # Extracts children template strings
        elts = re.findall(r"\$\((.*)\)\$", output_template)
        if not elts:
            child_template_string = ""
        else:
            child_template_string = elts[0]

        # Processes child services output
        children_output = ""
        ok_count = 0
        # Expands child items format string macros.
        items = self.business_rule.list_all_elements()
        for item_uuid in items:
            if item_uuid in hosts:
                item = hosts[item_uuid]
            elif item_uuid in services:
                item = services[item_uuid]

            # Do not display children in OK state
            if item.last_hard_state_id == 0:
                ok_count += 1
                continue
            if hasattr(item, 'host'):
                data = [hosts[item.host], item]
            else:
                data = [item]
            children_output += macroresolver.resolve_simple_macros_in_string(child_template_string,
                                                                             data,
                                                                             macromodulations,
                                                                             timeperiods)

        if ok_count == len(items):
            children_output = "all checks were successful."

        # Replaces children output string
        template_string = re.sub(r"\$\(.*\)\$", children_output, output_template)
        if hasattr(self, 'host'):
            data = [hosts[self.host], self]
        else:
            data = [self]
        output = macroresolver.resolve_simple_macros_in_string(template_string, data,
                                                               macromodulations, timeperiods)
        return output.strip()

    def business_rule_notification_is_blocked(self, hosts, services):
        """Process business rule notifications behaviour. If all problems have
        been acknowledged, no notifications should be sent if state is not OK.
        By default, downtimes are ignored, unless explicitly told to be treated
        as acknowledgements through with the business_rule_downtime_as_ack set.

        :return: True if all source problem are acknowledged, otherwise False
        :rtype: bool
        """
        # Walks through problems to check if all items in non ok are
        # acknowledged or in downtime period.
        acknowledged = 0
        for src_prob_id in self.source_problems:
            if src_prob_id in hosts:
                src_prob = hosts[src_prob_id]
            else:
                src_prob = services[src_prob_id]
            if src_prob.last_hard_state_id != 0:
                if src_prob.problem_has_been_acknowledged:
                    # Problem hast been acknowledged
                    acknowledged += 1
                # Only check problems under downtime if we are
                # explicitly told to do so.
                elif self.business_rule_downtime_as_ack is True:
                    if src_prob.scheduled_downtime_depth > 0:
                        # Problem is under downtime, and downtimes should be
                        # treated as acknowledgements
                        acknowledged += 1
                    elif hasattr(src_prob, "host") and \
                            hosts[src_prob.host].scheduled_downtime_depth > 0:
                        # Host is under downtime, and downtimes should be
                        # treated as acknowledgements
                        acknowledged += 1

        return acknowledged == len(self.source_problems)

    def manage_internal_check(self, hosts, services, check, hostgroups, servicegroups,
                              macromodulations, timeperiods):
        """Manage internal commands such as ::

        * bp_rule
        * _internal_host_up
        * _echo

        :param hosts: Used to create business rules
        :type hosts: alignak.objects.host.Hosts
        :param services: Used to create business rules
        :type services: alignak.objects.service.Services
        :param check: internal check to manage
        :type check: alignak.objects.check.Check
        :return: None
        """
        if check.command.startswith('bp_'):
            try:
                # Re evaluate the business rule to take into account macro
                # modulation.
                # Caution: We consider the that the macro modulation did not
                # change business rule dependency tree. Only Xof: values should
                # be modified by modulation.
                self.create_business_rules(hosts, services, hostgroups, servicegroups,
                                           macromodulations, timeperiods, running=True)
                state = self.business_rule.get_state(hosts, services)
                check.output = self.get_business_rule_output(hosts, services,
                                                             macromodulations, timeperiods)
                if 'TEST_LOG_ACTIONS' in os.environ:
                    if os.environ['TEST_LOG_ACTIONS'] == 'WARNING':
                        logger.warning("Resolved BR for '%s', output: %s",
                                       self.get_full_name(), check.output)
                    else:
                        logger.info("Resolved BR for '%s', output: %s",
                                    self.get_full_name(), check.output)

            except Exception, err:  # pylint: disable=W0703
                # Notifies the error, and return an UNKNOWN state.
                check.output = "Error while re-evaluating business rule: %s" % err
                logger.debug("[%s] Error while re-evaluating business rule:\n%s",
                             self.get_name(), traceback.format_exc())
                state = 3
        # _internal_host_up is for putting host as UP
        elif check.command == '_internal_host_up':
            state = 0
            check.execution_time = 0
            check.output = 'Host assumed to be UP'
            if 'TEST_LOG_ACTIONS' in os.environ:
                if os.environ['TEST_LOG_ACTIONS'] == 'WARNING':
                    logger.warning("Set host %s as UP (internal check)", self.get_full_name())
                else:
                    logger.info("Set host %s as UP (internal check)", self.get_full_name())

        # Echo is just putting the same state again
        elif check.command == '_echo':
            state = self.state_id
            check.execution_time = 0
            check.output = self.output
            if 'TEST_LOG_ACTIONS' in os.environ:
                if os.environ['TEST_LOG_ACTIONS'] == 'WARNING':
                    logger.warning("Echo the current state (%s - %d) for %s ",
                                   self.state, self.state_id, self.get_full_name())
                else:
                    logger.info("Echo the current state (%s - %d) for %s ",
                                self.state, self.state_id, self.get_full_name())

        check.long_output = check.output
        check.check_time = time.time()
        check.exit_status = state

    def eval_triggers(self, triggers):
        """Launch triggers

        :param triggers: triggers objects, also used to change the output/status of a check, or more
        :type triggers: alignak.objects.trigger.Triggers
        :return: None
        """
        for t in triggers:
            print("t: %s" % t)
        for t in self.triggers:
            print("self t: %s" % t)
        for trigger_id in triggers:
            print("trigger: %s" % trigger_id)
            trigger = triggers[trigger_id]
            try:
                trigger.eval(self)
            # pylint: disable=W0703
            except Exception:  # pragma: no cover, simple protection
                logger.error("We got an exception from a trigger on %s for %s",
                             self.get_full_name().decode('utf8', 'ignore'),
                             str(traceback.format_exc()))

    def fill_data_brok_from(self, data, brok_type):
        """Fill data brok dependent on the brok_type

        :param data: data to fill
        :type data: dict
        :param brok_type: brok type
        :type: str
        :return: None
        """
        super(SchedulingItem, self).fill_data_brok_from(data, brok_type)
        # workaround/easy trick to have the command_name of this
        # SchedulingItem in its check_result brok
        if brok_type == 'check_result':
            data['command_name'] = self.check_command.command.command_name

    def acknowledge_problem(self, notification_period, hosts, services, sticky, notify, author,
                            comment, end_time=0):
        """
        Add an acknowledge

        :param sticky: acknowledge will be always present is host return in UP state
        :type sticky: integer
        :param notify: if to 1, send a notification
        :type notify: integer
        :param author: name of the author or the acknowledge
        :type author: str
        :param comment: comment (description) of the acknowledge
        :type comment: str
        :param end_time: end (timeout) of this acknowledge in seconds(timestamp) (0 to never end)
        :type end_time: int
        :return: None | alignak.comment.Comment
        """
        comm = None
        logger.debug("Acknowledge requested for %s %s.", self.my_type, self.get_name())

        if self.state != self.ok_up:
            # case have yet an acknowledge
            if self.problem_has_been_acknowledged and self.acknowledgement:
                self.del_comment(getattr(self.acknowledgement, 'comment_id', None))

            if notify:
                self.create_notifications('ACKNOWLEDGEMENT',
                                          notification_period, hosts, services)

            self.problem_has_been_acknowledged = True
            sticky = sticky == 2

            data = {'ref': self.uuid, 'sticky': sticky, 'author': author, 'comment': comment,
                    'end_time': end_time, 'notify': notify}
            ack = Acknowledge(data)
            self.acknowledgement = ack
            if self.my_type == 'host':
                comment_type = 1
                self.broks.append(self.acknowledgement.get_raise_brok(self.get_name()))
            else:
                comment_type = 2
                self.broks.append(self.acknowledgement.get_raise_brok(self.host_name,
                                                                      self.get_name()))
            data = {
                'author': author, 'comment': comment, 'comment_type': comment_type, 'entry_type': 4,
                'source': 0, 'expires': False, 'ref': self.uuid
            }
            comm = Comment(data)
            self.acknowledgement.comment_id = comm.uuid
            self.comments[comm.uuid] = comm
            self.broks.append(self.get_update_status_brok())
            self.raise_acknowledge_log_entry()
        else:
            logger.debug("Acknowledge requested for %s %s but element state is OK/UP.",
                         self.my_type, self.get_name())

        # For an host, acknowledge all its services that are problems
        if self.my_type == 'host':
            for service_uuid in self.services:
                if service_uuid not in services:
                    continue
                services[service_uuid].acknowledge_problem(notification_period,
                                                           hosts, services, sticky, notify,
                                                           author, comment, end_time)
        return comm

    def check_for_expire_acknowledge(self):
        """
        If have acknowledge and is expired, delete it

        :return: None
        """
        if (self.acknowledgement and
                self.acknowledgement.end_time != 0 and
                self.acknowledgement.end_time < time.time()):
            self.unacknowledge_problem()

    def unacknowledge_problem(self):
        """
        Remove the acknowledge, reset the flag. The comment is deleted

        :return: None
        """
        if self.problem_has_been_acknowledged:
            logger.debug("[item::%s] deleting acknowledge of %s",
                         self.get_name(),
                         self.get_full_name())
            self.problem_has_been_acknowledged = False
            if self.my_type == 'host':
                self.broks.append(self.acknowledgement.get_expire_brok(self.get_name()))
            else:
                self.broks.append(self.acknowledgement.get_expire_brok(self.host_name,
                                                                       self.get_name()))

            # delete the comment of the item related with the acknowledge
            if hasattr(self.acknowledgement, 'comment_id') and \
                    self.acknowledgement.comment_id in self.comments:
                del self.comments[self.acknowledgement.comment_id]

            # Should not be deleted, a None is Good
            self.acknowledgement = None
            self.broks.append(self.get_update_status_brok())
            self.raise_unacknowledge_log_entry()

    def unacknowledge_problem_if_not_sticky(self):
        """
        Remove the acknowledge if it is not sticky

        :return: None
        """
        if hasattr(self, 'acknowledgement') and self.acknowledgement is not None:
            if not self.acknowledgement.sticky:
                self.unacknowledge_problem()

    def raise_check_result(self):  # pragma: no cover, base function
        """Raise ACTIVE CHECK RESULT entry
        Function defined in inherited objects (Host and Service)

        :return: None
        """
        pass

    def raise_alert_log_entry(self):  # pragma: no cover, base function
        """Raise ALERT entry
        Function defined in inherited objects (Host and Service)

        :return: None
        """
        pass

    def raise_acknowledge_log_entry(self):  # pragma: no cover, base function
        """Raise ACKNOWLEDGE STARTED entry
        Function defined in inherited objects (Host and Service)

        :return: None
        """
        pass

    def raise_unacknowledge_log_entry(self):  # pragma: no cover, base function
        """Raise ACKNOWLEDGE STOPPED entry
        Function defined in inherited objects (Host and Service)

        :return: None
        """
        pass

    def is_state(self, status):  # pragma: no cover, base function
        """Return if status match the current item status

        :param status: status to compare. Usually comes from config files
        :type status: str
        :return: True
        :rtype: bool
        """
        pass

    def raise_freshness_log_entry(self, t_stale_by):
        """Raise freshness alert entry (warning level)

        Example : "The freshness period of host 'host_name' is expired
                   by 0d 0h 17m 6s (threshold=0d 1h 0m 0s).
                   Attempt: 1 / 1.
                   I'm forcing the state to freshness state (d / HARD)"

        :param t_stale_by: time in seconds the host has been in a stale state
        :type t_stale_by: int
        :return: None
        """
        logger.warning("The freshness period of %s '%s' is expired by %s "
                       "(threshold=%s + %ss). Attempt: %s / %s. "
                       "I'm forcing the state to freshness state (%s / %s).",
                       self.my_type, self.get_name(),
                       format_t_into_dhms_format(t_stale_by),
                       format_t_into_dhms_format(self.freshness_threshold),
                       self.additional_freshness_latency,
                       self.attempt, self.max_check_attempts,
                       self.freshness_state, self.state_type)

    def raise_snapshot_log_entry(self, command):  # pragma: no cover, base function
        """Raise item SNAPSHOT entry (critical level)
        Format is : "ITEM SNAPSHOT: *self.get_name()*;*state*;*state_type*;*attempt*;
                    *command.get_name()*"
        Example : "HOST SNAPSHOT: server;UP;HARD;1;notify-by-rss"

        :param command: Snapshot command launched
        :type command: alignak.objects.command.Command
        :return: None
        """
        pass

    def raise_flapping_start_log_entry(self, change_ratio, threshold):  # pragma: no cover,
        # base function
        """Raise FLAPPING ALERT START entry (critical level)

        :param change_ratio: percent of changing state
        :type change_ratio: float
        :param threshold: threshold (percent) to trigger this log entry
        :type threshold: float
        :return: None
        """
        pass

    def raise_event_handler_log_entry(self, command):  # pragma: no cover, base function
        """Raise EVENT HANDLER entry (critical level)

        :param command: Handler launched
        :type command: alignak.objects.command.Command
        :return: None
        """
        pass

    def raise_flapping_stop_log_entry(self, change_ratio, threshold):  # pragma: no cover,
        # base function
        """Raise FLAPPING ALERT STOPPED entry (critical level)

        :param change_ratio: percent of changing state
        :type change_ratio: float
        :param threshold: threshold (percent) to trigger this log entry
        :type threshold: float
        :return: None
        """
        pass

    def raise_notification_log_entry(self, notif, contact, host_ref):  # pragma: no cover,
        # base function
        """Raise NOTIFICATION entry (critical level)
        :param notif: notification object created by service alert
        :type notif: alignak.objects.notification.Notification
        :return: None
        """
        pass

    def get_data_for_checks(self):  # pragma: no cover, base function
        """Get data for a check

        :return: list containing the service and the linked host
        :rtype: list
        """
        pass

    def get_data_for_event_handler(self):  # pragma: no cover, base function
        """Get data for an event handler

        :return: list containing a single item (this one)
        :rtype: list
        """
        pass

    def get_data_for_notifications(self, contact, notif):  # pragma: no cover, base function
        """Get data for a notification

        :param contact: The contact to return
        :type contact:
        :param notif: the notification to return
        :type notif:
        :return: list
        :rtype: list
        """
        pass

    def set_impact_state(self):
        """We just go an impact, so we go unreachable
        But only if we enable this state change in the conf

        :return: None
        """
        cls = self.__class__
        if cls.enable_problem_impacts_states_change:
            # Track the old state (problem occured before a new check)
            self.state_before_impact = self.state
            self.state_id_before_impact = self.state_id
            # This flag will know if we override the impact state
            self.state_changed_since_impact = False
            self.state = 'UNREACHABLE'  # exit code UNDETERMINED
            self.state_id = 4

    def unset_impact_state(self):
        """Unset impact, only if impact state change is set in configuration

        :return: None
        """
        cls = self.__class__
        if cls.enable_problem_impacts_states_change and not self.state_changed_since_impact:
            self.state = self.state_before_impact
            self.state_id = self.state_id_before_impact

    def last_time_non_ok_or_up(self):  # pragma: no cover, base function
        """Get the last time the item was in a non-OK state

        :return: return 0
        :rtype: int
        """
        pass

    def set_unreachable(self):
        """Set unreachable: all our parents (dependencies) are not ok
        Unreachable is different from down/critical

        :return:None
        """
        now = time.time()
        self.state_id = 4
        self.state = 'UNREACHABLE'
        self.last_time_unreachable = int(now)

    def manage_stalking(self, check):  # pragma: no cover, base function
        """Check if the item need stalking or not (immediate recheck)

        :param check: finished check (check.status == 'waitconsume')
        :type check: alignak.check.Check
        :return: None
        """
        pass

    def set_state_from_exit_status(self, status, notif_period, hosts, services):
        """Set the state with the status of a check. Also update last_state

        :param status: integer between 0 and 3
        :type status: int
        :param hosts: hosts objects, used for almost every operation
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects, used for almost every operation
        :type services: alignak.objects.service.Services
        :return: None
        """
        pass

    def notification_is_blocked_by_item(self, notification_period, hosts, services, n_type,
                                        t_wished=None):  # pragma: no cover, base function
        """Check if a notification is blocked by item

        :param n_type: notification type
        :type n_type:
        :param t_wished: the time we should like to notify the host (mostly now)
        :type t_wished: float
        :return: True if ONE of the above condition was met, otherwise False
        :rtype: bool
        """
        pass

    def notification_is_blocked_by_contact(self, notifways, timeperiods, notif,
                                           contact):  # pragma: no cover, base function
        """Check if the notification is blocked by this contact.

        :param notif: notification created earlier
        :type notif: alignak.notification.Notification
        :param contact: contact we want to notify
        :type notif: alignak.objects.contact.Contact
        :return: True if the notification is blocked, False otherwise
        :rtype: bool
        """
        pass

    def is_correct(self):
        """
        Check if this object configuration is correct ::

        * Check our own specific properties
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """
        state = True

        if hasattr(self, 'trigger') and getattr(self, 'trigger', None):
            msg = "[%s::%s] 'trigger' property is not allowed" % (self.my_type, self.get_name())
            self.configuration_warnings.append(msg)

        # If no notif period, set it to None, mean 24x7
        if not hasattr(self, 'notification_period'):
            self.notification_period = None

        # If we got an event handler, it should be valid
        if getattr(self, 'event_handler', None) and not self.event_handler.is_valid():
            msg = "[%s::%s] event_handler '%s' is invalid" \
                  % (self.my_type, self.get_name(), self.event_handler.command)
            self.add_error(msg)
            state = False

        if not hasattr(self, 'check_command'):
            msg = "[%s::%s] no check_command" % (self.my_type, self.get_name())
            self.add_error(msg)
            state = False
        # Ok got a command, but maybe it's invalid
        else:
            if not self.check_command.is_valid():
                msg = "[%s::%s] check_command '%s' invalid" % (self.my_type, self.get_name(),
                                                               self.check_command.command)
                self.add_error(msg)
                state = False
            if self.got_business_rule:
                if not self.business_rule.is_valid():
                    msg = "[%s::%s] business_rule invalid" % (
                        self.my_type, self.get_name()
                    )
                    self.add_error(msg)
                    for bperror in self.business_rule.configuration_errors:
                        msg = "[%s::%s]: %s" % (self.my_type, self.get_name(), bperror)
                        self.add_error(msg)
                    state = False

        if not hasattr(self, 'notification_interval') \
                and self.notifications_enabled is True:  # pragma: no cover, should never happen
            msg = "[%s::%s] no notification_interval but notifications enabled" % (
                self.my_type, self.get_name()
            )
            self.add_error(msg)
            state = False

        # if no check_period, means 24x7, like for services
        if not hasattr(self, 'check_period'):
            self.check_period = None

        state = super(SchedulingItem, self).is_correct()
        return state


class SchedulingItems(CommandCallItems):
    """Class to handle schedulingitems. It's mainly for configuration

    """

    def find_by_filter(self, filters, all_items):
        """
        Find items by filters

        :param filters: list of filters
        :type filters: list
        :param all_items: monitoring items
        :type: dict
        :return: list of items
        :rtype: list
        """
        items = []
        for i in self:
            failed = False
            if hasattr(i, "host"):
                all_items["service"] = i
            else:
                all_items["host"] = i
            for filt in filters:
                if not filt(all_items):
                    failed = True
                    break
            if failed is False:
                items.append(i)
        return items

    def add_act_dependency(self, son_id, parent_id, notif_failure_criteria, dep_period,
                           inherits_parents):
        """
        Add a logical dependency for actions between two hosts or services.

        :param son_id: uuid of son host
        :type son_id: str
        :param parent_id: uuid of parent host
        :type parent_id: str
        :param notif_failure_criteria: notification failure criteria,
        notification for a dependent host may vary
        :type notif_failure_criteria: list
        :param dep_period: dependency period. Timeperiod for dependency may vary
        :type dep_period: str | None
        :param inherits_parents: if this dep will inherit from parents (timeperiod, status)
        :type inherits_parents: bool
        :return:
        """
        if son_id in self:
            son = self[son_id]
        else:
            msg = "Dependency son (%s) unknown, configuration error" % son_id
            self.add_error(msg)
        parent = self[parent_id]
        son.act_depend_of.append((parent_id, notif_failure_criteria, dep_period, inherits_parents))
        parent.act_depend_of_me.append((son_id, notif_failure_criteria, dep_period,
                                        inherits_parents))

        # TODO: Is it necessary? We already have this info in act_depend_* attributes
        son.parent_dependencies.add(parent_id)
        parent.child_dependencies.add(son_id)

    def del_act_dependency(self, son_id, parent_id):  # pragma: no cover, not yet tested
        """Remove act_dependency between two hosts or services.

        TODO: do we really intend to remove dynamically ?

        :param son_id: uuid of son host/service
        :type son_id: str
        :param parent_id: uuid of parent host/service
        :type parent_id: str
        :return: None
        """
        son = self[son_id]
        parent = self[parent_id]
        to_del = []
        # First we remove in my list
        for (host, status, timeperiod, inherits_parent) in son.act_depend_of:
            if host == parent_id:
                to_del.append((host, status, timeperiod, inherits_parent))
        for tup in to_del:
            son.act_depend_of.remove(tup)

        # And now in the father part
        to_del = []
        for (host, status, timeperiod, inherits_parent) in parent.act_depend_of_me:
            if host == son_id:
                to_del.append((host, status, timeperiod, inherits_parent))
        for tup in to_del:
            parent.act_depend_of_me.remove(tup)

        # Remove in child/parents dependencies too
        # Me in father list
        parent.child_dependencies.remove(son_id)
        # and father list in mine
        son.parent_dependencies.remove(parent_id)

    def add_chk_dependency(self, son_id, parent_id, notif_failure_criteria, dep_period,
                           inherits_parents):
        """
        Add a logical dependency for checks between two hosts or services.

        :param son_id: uuid of son host/service
        :type son_id: str
        :param parent_id: uuid of parent host/service
        :type parent_id: str
        :param notif_failure_criteria: notification failure criteria,
        notification for a dependent host may vary
        :type notif_failure_criteria: list
        :param dep_period: dependency period. Timeperiod for dependency may vary
        :type dep_period: str
        :param inherits_parents: if this dep will inherit from parents (timeperiod, status)
        :type inherits_parents: bool
        :return:
        """
        son = self[son_id]
        parent = self[parent_id]
        son.chk_depend_of.append((parent_id, notif_failure_criteria, 'logic_dep', dep_period,
                                  inherits_parents))
        parent.chk_depend_of_me.append((son_id, notif_failure_criteria, 'logic_dep', dep_period,
                                        inherits_parents))

        # TODO: Is it necessary? We already have this info in act_depend_* attributes
        son.parent_dependencies.add(parent_id)
        parent.child_dependencies.add(son_id)

    def create_business_rules(self, hosts, services, hostgroups, servicegroups,
                              macromodulations, timeperiods):
        """
        Loop on hosts or services and call SchedulingItem.create_business_rules

        :param hosts: hosts to link to
        :type hosts: alignak.objects.host.Hosts
        :param services: services to link to
        :type services: alignak.objects.service.Services
        :param hostgroups: hostgroups to link to
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :param servicegroups: servicegroups to link to
        :type servicegroups: alignak.objects.servicegroup.Servicegroups
        :param macromodulations: macromodulations to link to
        :type macromodulations: alignak.objects.macromodulation.Macromodulations
        :param timeperiods: timeperiods to link to
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: None
        """
        for item in self:
            item.create_business_rules(hosts, services, hostgroups,
                                       servicegroups, macromodulations, timeperiods)

    def linkify_with_triggers(self, triggers):
        """
        Link triggers

        :param triggers: triggers object
        :type triggers: alignak.objects.trigger.Triggers
        :return: None
        """
        for i in self:
            i.linkify_with_triggers(triggers)
