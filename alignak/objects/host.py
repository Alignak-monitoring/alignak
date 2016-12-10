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
import logging

from alignak.objects.schedulingitem import SchedulingItem, SchedulingItems

from alignak.autoslots import AutoSlots
from alignak.util import format_t_into_dhms_format
from alignak.property import BoolProp, IntegerProp, StringProp, ListProp, CharProp
from alignak.log import make_monitoring_log

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Host(SchedulingItem):  # pylint: disable=R0904
    """Host class implements monitoring concepts for host.
    For example it defines parents, check_interval, check_command  etc.
    """
    # AutoSlots metaclass create the __slots__ with properties and running_properties names
    # __metaclass__ = AutoSlots

    name_property = "host_name"
    my_type = 'host'

    # The host and service do not have the same 0 value, now yes :)
    ok_up = 'UP'

    properties = SchedulingItem.properties.copy()
    properties.update({
        'host_name':
            StringProp(fill_brok=['full_status', 'check_result', 'next_schedule']),
        'address':
            StringProp(fill_brok=['full_status'], default=''),
        'address6':
            StringProp(fill_brok=['full_status'], default=''),
        'parents':
            ListProp(default=[], fill_brok=['full_status'], merging='join'),
        'hostgroups':
            ListProp(default=[], fill_brok=['full_status'], merging='join'),
        'obsess_over_host':
            BoolProp(default=False, fill_brok=['full_status'], retention=True),
        'flap_detection_options':
            ListProp(default=['o', 'd', 'x'], fill_brok=['full_status'],
                     merging='join'),
        'notification_options':
            ListProp(default=['d', 'x', 'r', 'f', 's'], fill_brok=['full_status'], merging='join'),
        'vrml_image':
            StringProp(default='', fill_brok=['full_status']),
        'statusmap_image':
            StringProp(default='', fill_brok=['full_status']),
        # State the host will be set to if the freshness_threshold is raised
        'freshness_state':
            CharProp(default='d', fill_brok=['full_status']),

        # No slots for this 2 because properties beginning by a number seems bad
        # it's stupid!
        '2d_coords':
            StringProp(default='', fill_brok=['full_status'], no_slots=True),
        '3d_coords':
            StringProp(default='', fill_brok=['full_status'], no_slots=True),
        # New to alignak
        # 'fill_brok' is ok because in scheduler it's already
        # a string from conf_send_preparation
        'service_overrides':
            ListProp(default=[], merging='duplicate', split_on_coma=False),
        'service_excludes':
            ListProp(default=[], merging='duplicate'),
        'service_includes':
            ListProp(default=[], merging='duplicate'),
        'snapshot_criteria':
            ListProp(default=['d', 'x'], fill_brok=['full_status'], merging='join'),
    })

    # properties set only for running purpose
    # retention: save/load this property from retention
    running_properties = SchedulingItem.running_properties.copy()
    running_properties.update({
        'state':
            StringProp(default='UP', fill_brok=['full_status', 'check_result'],
                       retention=True),
        'last_time_up':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_down':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_unreachable':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),

        'services':
            ListProp(default=[]),
        'realm_name':
            StringProp(default=''),
        'got_default_realm':
            BoolProp(default=False),

        'state_before_hard_unknown_reach_phase':
            StringProp(default='UP', retention=True),

        # Keep in mind our pack id after the cutting phase
        'pack_id':
            IntegerProp(default=-1),
    })

    # Hosts macros and prop that give the information
    # the prop can be callable or not
    macros = SchedulingItem.macros.copy()
    macros.update({
        'HOSTNAME': 'host_name',
        'HOSTDISPLAYNAME': 'display_name',
        'HOSTALIAS': 'alias',
        'HOSTADDRESS': 'address',
        'HOSTSTATE': 'state',
        'HOSTSTATEID': 'state_id',
        'LASTHOSTSTATE': 'last_state',
        'LASTHOSTSTATEID': 'last_state_id',
        'HOSTSTATETYPE': 'state_type',
        'HOSTATTEMPT': 'attempt',
        'MAXHOSTATTEMPTS': 'max_check_attempts',
        'HOSTEVENTID': 'current_event_id',
        'LASTHOSTEVENTID': 'last_event_id',
        'HOSTPROBLEMID': 'current_problem_id',
        'LASTHOSTPROBLEMID': 'last_problem_id',
        'HOSTLATENCY': 'latency',
        'HOSTEXECUTIONTIME': 'execution_time',
        'HOSTDURATION': 'get_duration',
        'HOSTDURATIONSEC': 'get_duration_sec',
        'HOSTDOWNTIME': 'get_downtime',
        'HOSTPERCENTCHANGE': 'percent_state_change',
        'HOSTGROUPNAME': ('get_groupname', ['hostgroups']),
        'HOSTGROUPNAMES': ('get_groupnames', ['hostgroups']),
        'LASTHOSTCHECK': 'last_chk',
        'LASTHOSTSTATECHANGE': 'last_state_change',
        'LASTHOSTUP': 'last_time_up',
        'LASTHOSTDOWN': 'last_time_down',
        'LASTHOSTUNREACHABLE': 'last_time_unreachable',
        'HOSTOUTPUT': 'output',
        'LONGHOSTOUTPUT': 'long_output',
        'HOSTPERFDATA': 'perf_data',
        'LASTHOSTPERFDATA': 'last_perf_data',
        'HOSTCHECKCOMMAND': 'get_check_command',
        'HOSTSNAPSHOTCOMMAND': 'get_snapshot_command',
        'HOSTACKAUTHOR': 'get_ack_author_name',
        'HOSTACKAUTHORNAME': 'get_ack_author_name',
        'HOSTACKAUTHORALIAS': 'get_ack_author_name',
        'HOSTACKCOMMENT': 'get_ack_comment',
        'HOSTACTIONURL': 'action_url',
        'HOSTNOTESURL': 'notes_url',
        'HOSTNOTES': 'notes',
        'HOSTREALM': 'realm_name',
        'TOTALHOSTSERVICES': 'get_total_services',
        'TOTALHOSTSERVICESOK': ('get_total_services_ok', ['services']),
        'TOTALHOSTSERVICESWARNING': ('get_total_services_warning', ['services']),
        'TOTALHOSTSERVICESUNKNOWN': ('get_total_services_unknown', ['services']),
        'TOTALHOSTSERVICESCRITICAL': ('get_total_services_critical', ['services']),
        'HOSTBUSINESSIMPACT': 'business_impact',
    })
    # Todo: really unuseful ... should be removed, but let's discuss!
    # Currently, this breaks the macro resolver because the corresponding properties do not exit!
    # Manage ADDRESSX macros by adding them dynamically
    # for i in range(32):
    #     macros['HOSTADDRESS%d' % i] = 'address%d' % i

    # This tab is used to transform old parameters name into new ones
    # so from Nagios2 format, to Nagios3 ones.
    # Or Alignak deprecated names like criticity
    old_properties = SchedulingItem.old_properties.copy()
    old_properties.update({
        'hostgroup': 'hostgroups',
    })

    def __init__(self, params=None, parsing=True, debug=False):
        """Initialize an Host object

        :param debug: print debug information about the object properties
        :param params: parameters used to create the object
        :param parsing: if True, initial creation, else, object unserialization
        """
        if debug:
            print('Host __init__: %s, %d properties' %
                  (self.__class__, len(self.properties)))
            print('Host __init__: %s, properties list: %s' %
                  (self.__class__, [key for key in self.properties]))

        super(Host, self).__init__(params, parsing=parsing, debug=debug)

        # Update unreachable state
        for prop in ['flap_detection_options', 'notification_options',
                     'snapshot_criteria', 'stalking_options']:
            if hasattr(self, prop):
                setattr(self, prop, [p.replace('u', u'x') for p in getattr(self, prop)])

        for prop in ['initial_state', 'freshness_state']:
            if hasattr(self, prop) and getattr(self, prop) == 'u':
                setattr(self, prop, 'x')

        if debug:
            print('Host __init__: %s, %d attributes' %
                  (self.__class__, len(self.__dict__)))
            print('Host __init__: %s, attributes list: %s' %
                  (self.__class__, [key for key in self.__dict__]))

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

    def fill_predictable_missing_parameters(self):
        """Fill address with host_name if not already set
        and define state with initial_state

        :return: None
        """
        if hasattr(self, 'host_name') and not getattr(self, 'address', ''):
            self.address = self.host_name

        if self.initial_state == 'd':
            self.state = 'DOWN'
        elif self.initial_state == 'x' or self.initial_state == 'u':
            self.state = 'UNREACHABLE'

    def is_correct(self):
        """Check if this object configuration is correct ::

        * Check our own specific properties
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """

        # Internal checks before executing inherited function...
        cls = self.__class__
        if hasattr(self, 'host_name'):
            for char in cls.illegal_object_name_chars:
                if char in self.host_name:
                    self.add_error("[%s::%s] host_name got an illegal character: %s" %
                                   (self.my_type, self.get_name(), char))

        if not getattr(self, 'check_command', None):
            self.add_error("[%s::%s] has no check_command, it will always be considered as UP" %
                           (self.my_type, self.get_name()), is_warning=True)

        return super(Host, self).is_correct() and self.conf_is_correct

    def get_services(self):
        """Get all services for this host

        :return: list of services
        :rtype: list
        """
        return self.services

    def get_groupname(self, groups):
        """Get name of the host's first hostgroup

        :return: the first host group name
        :rtype: str
        """
        groupname = ''
        for group_id in self.hostgroups:
            group = groups[group_id]
            if group:
                groupname = "%s" % (group.alias)
                return groupname
        return groupname

    def get_groupnames(self, groups):
        """Get list of the item's groups names

        :return: comma separated alphabetically ordered string list
        :rtype: str
        """
        groupnames = []
        for group_id in self.hostgroups:
            group = groups[group_id]
            if group:
                groupnames.append(group.get_name())

        return ','.join(sorted(groupnames))

    def get_hostgroups(self):
        """Accessor to hostgroups attribute

        :return: hostgroup list object of host
        :rtype: list
        """
        return self.hostgroups

    def get_host_tags(self):
        """Accessor to tags attribute

        :return: tag list of host
        :rtype: list
        """
        return self.tags

    # def get_realm_name(self):
    #     """Accessor to realm attribute
    #     :return: realm object of host
    #     :rtype: alignak.objects.realm.Realm
    #     """
    #     return self.realm_name
    #
    def is_linked_with_host(self, other):
        """Check if other is in act_depend_of host attribute

        :param other: other host to search
        :type other: alignak.objects.host.Host
        :return: True if other in act_depend_of list, otherwise False
        :rtype: bool
        """
        for (host, _, _, _) in self.act_depend_of:
            if host == other:
                return True
        return False

    def add_service_link(self, service):
        """Add a service to the service list of this host

        :param service: the uuid of the service to add
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
        """Check whether this host should have the passed service be "excluded" or "not included".

        An host can define service_includes and/or service_excludes directive to either
        white-list-only or black-list some services from itself.

        :param service:
        :type service: alignak.objects.service.Service
        :return: True if is excluded, otherwise False
        :rtype: bool
        """
        return self.is_excluded_for_sdesc(
            getattr(service, 'service_description', None), service.is_tpl()
        )

    def is_excluded_for_sdesc(self, sdesc, is_tpl=False):
        """ Check whether this host should have the passed service *description*
            be "excluded" or "not included".

        :param sdesc: service description
        :type sdesc:
        :param is_tpl: True if service is template, otherwise False
        :type is_tpl: bool
        :return: True if service description excluded, otherwise False
        :rtype: bool
        """
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

    def set_state_from_exit_status(self, status, notif_period, hosts, services):
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
            # Now we add a value, we update the is_flapping prop
            self.update_flapping(notif_period, hosts, services)

        if self.state != self.last_state and \
                not (self.state == "DOWN" and self.last_state == "UNREACHABLE"):
            self.last_state_change = self.last_state_update
        self.duration_sec = now - self.last_state_change

    def is_state(self, status):
        """Return if status match the current host status

        :param status: status to compare ( "o", "d", "x"). Usually comes from config files
        :type status: str
        :return: True if status <=> self.status, otherwise False
        :rtype: bool
        """
        if status == self.state:
            return True
        # Now low status
        elif status == 'o' and self.state == 'UP':
            return True
        elif status == 'd' and self.state == 'DOWN':
            return True
        elif status == 'x' and self.state == 'UNREACHABLE':
            return True
        return False

    def last_time_non_ok_or_up(self):
        """Get the last time the host was in a non-OK state

        :return: self.last_time_down if self.last_time_down > self.last_time_up, 0 otherwise
        :rtype: int
        """
        if self.last_time_down > self.last_time_up:
            last_time_non_up = self.last_time_down
        else:
            last_time_non_up = 0
        return last_time_non_up

    def raise_check_result(self):
        """Raise ACTIVE CHECK RESULT entry
        Example : "ACTIVE HOST CHECK: server;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        log_level = 'info'
        if self.state == 'DOWN':
            log_level = 'error'
        elif self.state == 'UNREACHABLE':
            log_level = 'warning'
        brok = make_monitoring_log(
            log_level, 'ACTIVE HOST CHECK: %s;%s;%s;%d;%s' % (
                self.get_name(), self.state, self.state_type, self.attempt, self.output
            )
        )
        self.broks.append(brok)

    def raise_alert_log_entry(self):
        """Raise HOST ALERT entry
        Format is : "HOST ALERT: *get_name()*;*state*;*state_type*;*attempt*;*output*"
        Example : "HOST ALERT: server;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        log_level = 'info'
        if self.state == 'DOWN':
            log_level = 'error'
        if self.state == 'UNREACHABLE':
            log_level = 'warning'
        brok = make_monitoring_log(
            log_level, 'HOST ALERT: %s;%s;%s;%d;%s' % (
                self.get_name(), self.state, self.state_type, self.attempt, self.output
            )
        )
        self.broks.append(brok)

    def raise_initial_state(self):
        """Raise CURRENT HOST ALERT entry (info level)
        Format is : "CURRENT HOST STATE: *get_name()*;*state*;*state_type*;*attempt*;*output*"
        Example : "CURRENT HOST STATE: server;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        log_level = 'info'
        if self.state == 'DOWN':
            log_level = 'error'
        if self.state == 'UNREACHABLE':
            log_level = 'warning'
        if self.__class__.log_initial_states:
            brok = make_monitoring_log(
                log_level, 'CURRENT HOST STATE: %s;%s;%s;%d;%s' % (
                    self.get_name(), self.state, self.state_type, self.attempt, self.output
                )
            )
            self.broks.append(brok)

    def raise_freshness_log_entry(self, t_stale_by, t_threshold):
        """Raise freshness alert entry (warning level)
        Format is : "The results of host '*get_name()*' are stale by *t_stale_by*
                     (threshold=*t_threshold*).  I'm forcing an immediate check of the host."
        Example : "Warning: The results of host 'Server' are stale by 0d 0h 0m 58s
                   (threshold=0d 1h 0m 0s). ..."

        :param t_stale_by: time in seconds the host has been in a stale state
        :type t_stale_by: int
        :param t_threshold: threshold (seconds) to trigger this log entry
        :type t_threshold: int
        :return: None
        """
        logger.warning("The freshness period of host '%s' is expired by %s "
                       "(threshold=%s).  I'm forcing the state to freshness state (%s).",
                       self.get_name(),
                       format_t_into_dhms_format(t_stale_by),
                       format_t_into_dhms_format(t_threshold),
                       self.freshness_state)

    def raise_notification_log_entry(self, notif, contact, host_ref=None):
        """Raise HOST NOTIFICATION entry (critical level)
        Format is : "HOST NOTIFICATION: *contact.get_name()*;*self.get_name()*;*state*;
                     *command.get_name()*;*output*"
        Example : "HOST NOTIFICATION: superadmin;server;UP;notify-by-rss;no output"

        :param notif: notification object created by host alert
        :type notif: alignak.objects.notification.Notification
        :return: None
        """
        if not self.__class__.log_notifications:
            return

        log_level = 'info'
        command = notif.command_call
        if notif.type in ('DOWNTIMESTART', 'DOWNTIMEEND', 'CUSTOM',
                          'ACKNOWLEDGEMENT', 'FLAPPINGSTART', 'FLAPPINGSTOP',
                          'FLAPPINGDISABLED'):
            state = '%s (%s)' % (notif.type, self.state)
        else:
            state = self.state
            if self.state == 'UNREACHABLE':
                log_level = 'warning'
            if self.state == 'DOWN':
                log_level = 'error'

        brok = make_monitoring_log(
            log_level, "HOST NOTIFICATION: %s;%s;%s;%s;%s" % (
                contact.get_name(), self.get_name(), state, command.get_name(), self.output
            )
        )
        self.broks.append(brok)

    def raise_event_handler_log_entry(self, command):
        """Raise HOST EVENT HANDLER entry (critical level)
        Format is : "HOST EVENT HANDLER: *self.get_name()*;*state*;*state_type*;*attempt*;
                    *command.get_name()*"
        Example : "HOST EVENT HANDLER: server;UP;HARD;1;notify-by-rss"

        :param command: Handler launched
        :type command: alignak.objects.command.Command
        :return: None
        """
        if not self.__class__.log_event_handlers:
            return

        log_level = 'info'
        if self.state == 'UNREACHABLE':
            log_level = 'warning'
        if self.state == 'DOWN':
            log_level = 'error'
        brok = make_monitoring_log(
            log_level, "HOST EVENT HANDLER: %s;%s;%s;%s;%s" % (
                self.get_name(), self.state, self.state_type, self.attempt, command.get_name()
            )
        )
        self.broks.append(brok)

    def raise_snapshot_log_entry(self, command):
        """Raise HOST SNAPSHOT entry (critical level)
        Format is : "HOST SNAPSHOT: *self.get_name()*;*state*;*state_type*;*attempt*;
                    *command.get_name()*"
        Example : "HOST SNAPSHOT: server;UP;HARD;1;notify-by-rss"

        :param command: Snapshot command launched
        :type command: alignak.objects.command.Command
        :return: None
        """
        if not self.__class__.log_snapshots:
            return

        log_level = 'info'
        if self.state == 'UNREACHABLE':
            log_level = 'warning'
        if self.state == 'DOWN':
            log_level = 'error'
        brok = make_monitoring_log(
            log_level, "HOST SNAPSHOT: %s;%s;%s;%s;%s" % (
                self.get_name(), self.state, self.state_type, self.attempt, command.get_name()
            )
        )
        self.broks.append(brok)

    def raise_flapping_start_log_entry(self, change_ratio, threshold):
        """Raise HOST FLAPPING ALERT START entry (critical level)
        Format is : "HOST FLAPPING ALERT: *self.get_name()*;STARTED;
                     Host appears to have started
                     flapping (*change_ratio*% change >= *threshold*% threshold)"
        Example : "HOST FLAPPING ALERT: server;STARTED;
                   Host appears to have started
                   flapping (50.6% change >= 50.0% threshold)"

        :param change_ratio: percent of changing state
        :type change_ratio: float
        :param threshold: threshold (percent) to trigger this log entry
        :type threshold: float
        :return: None
        """
        if not self.__class__.log_flappings:
            return

        brok = make_monitoring_log(
            'info', "HOST FLAPPING ALERT: %s;STARTED; Host appears to have started flapping "
                    "(%.1f%% change >= %.1f%% threshold)" %
                    (self.get_name(), change_ratio, threshold)
        )
        self.broks.append(brok)

    def raise_flapping_stop_log_entry(self, change_ratio, threshold):
        """Raise HOST FLAPPING ALERT STOPPED entry (critical level)
        Format is : "HOST FLAPPING ALERT: *self.get_name()*;STOPPED;
                     Host appears to have stopped
                     flapping (*change_ratio*% change < *threshold*% threshold)"
        Example : "HOST FLAPPING ALERT: server;STOPPED;
                   Host appears to have stopped
                   flapping (23.0% change < 25.0% threshold)"

        :param change_ratio: percent of changing state
        :type change_ratio: float
        :param threshold: threshold (percent) to trigger this log entry
        :type threshold: float
        :return: None
        """
        if not self.__class__.log_flappings:
            return

        brok = make_monitoring_log(
            'info', "HOST FLAPPING ALERT: %s;STOPPED; Host appears to have stopped flapping "
                    "(%.1f%% change < %.1f%% threshold)" %
                    (self.get_name(), change_ratio, threshold)
        )
        self.broks.append(brok)

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
        brok = make_monitoring_log(
            'info', "HOST DOWNTIME ALERT: %s;STARTED; "
                    "Host has entered a period of scheduled downtime" % (self.get_name())
        )
        self.broks.append(brok)

    def raise_exit_downtime_log_entry(self):
        """Raise HOST DOWNTIME ALERT entry (critical level)
        Format is : "HOST DOWNTIME ALERT: *get_name()*;STOPPED;
                     Host has entered a period of scheduled downtime"
        Example : "HOST DOWNTIME ALERT: test_host_0;STOPPED;
                   Host has entered a period of scheduled downtime"

        :return: None
        """
        brok = make_monitoring_log(
            'info', "HOST DOWNTIME ALERT: %s;STOPPED; "
                    "Host has exited from a period of scheduled downtime" % (self.get_name())
        )
        self.broks.append(brok)

    def raise_cancel_downtime_log_entry(self):
        """Raise HOST DOWNTIME ALERT entry (critical level)
        Format is : "HOST DOWNTIME ALERT: *get_name()*;CANCELLED;
                     Host has entered a period of scheduled downtime"
        Example : "HOST DOWNTIME ALERT: test_host_0;CANCELLED;
                   Host has entered a period of scheduled downtime"

        :return: None
        """
        brok = make_monitoring_log(
            'info', "HOST DOWNTIME ALERT: %s;CANCELLED; "
                    "Scheduled downtime for host has been cancelled." % (self.get_name())
        )
        self.broks.append(brok)

    def manage_stalking(self, check):
        """Check if the host need stalking or not (immediate recheck)
        If one stalking_options matches the exit_status ('o' <=> 0 ...) then stalk is needed
        Raise a log entry (info level) if stalk is needed

        :param check: finished check (check.status == 'waitconsume')
        :type check: alignak.check.Check
        :return: None
        """
        need_stalk = False
        if check.status == 'waitconsume':
            if check.exit_status == 0 and 'o' in self.stalking_options:
                need_stalk = True
            elif check.exit_status == 1 and 'd' in self.stalking_options:
                need_stalk = True
            elif check.exit_status == 2 and 'd' in self.stalking_options:
                need_stalk = True
            if check.output != self.output:
                need_stalk = False
        if need_stalk:
            logger.info("Stalking %s: %s", self.get_name(), self.output)

    def get_data_for_checks(self):
        """Get data for a check

        :return: list containing a single host (this one)
        :rtype: list
        """
        return [self]

    def get_data_for_event_handler(self):
        """Get data for an event handler

        :return: list containing a single host (this one)
        :rtype: list
        """
        return [self]

    def get_data_for_notifications(self, contact, notif):
        """Get data for a notification

        :param contact: The contact to return
        :type contact:
        :param notif: the notification to return
        :type notif:
        :return: list containing a the host and the given parameters
        :rtype: list
        """
        return [self, contact, notif]

    def notification_is_blocked_by_contact(self, notifways, timeperiods, cdowntimes,
                                           notif, contact):
        """Check if the notification is blocked by this contact.

        :param notif: notification created earlier
        :type notif: alignak.notification.Notification
        :param contact: contact we want to notify
        :type notif: alignak.objects.contact.Contact
        :return: True if the notification is blocked, False otherwise
        :rtype: bool
        """
        return not contact.want_host_notification(notifways, timeperiods,
                                                  self.last_chk, self.state, notif.type,
                                                  self.business_impact, notif.command_call)

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
        """
        mins, secs = divmod(self.duration_sec, 60)
        hours, mins = divmod(mins, 60)
        return "%02dh %02dm %02ds" % (hours, mins, secs)

    def notification_is_blocked_by_item(self, notification_period, hosts, services,
                                        n_type, t_wished=None):
        """Check if a notification is blocked by the host.
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

        :param n_type: notification type
        :type n_type:
        :param t_wished: the time we should like to notify the host (mostly now)
        :type t_wished: float
        :return: True if ONE of the above condition was met, otherwise False
        :rtype: bool
        TODO: Refactor this, a lot of code duplication with Service.notification_is_blocked_by_item
        """
        if t_wished is None:
            t_wished = time.time()

        # TODO
        # forced notification -> false
        # custom notification -> false

        # Block if notifications are program-wide disabled
        # Block if notifications are disabled for this host
        # Block if the current status is in the notification_options d,u,r,f,s
        # Does the notification period allow sending out this notification?
        if not self.enable_notifications or \
                not self.notifications_enabled or \
                'n' in self.notification_options or \
                (notification_period is not None and
                 not notification_period.is_time_valid(t_wished)):
            logger.debug("Host: %s, notification %s sending is blocked by globals",
                         self.get_name(), n_type)
            return True

        if n_type in ('PROBLEM', 'RECOVERY') and (
                self.state == 'DOWN' and 'd' not in self.notification_options or
                self.state == 'UP' and 'r' not in self.notification_options or
                self.state == 'UNREACHABLE' and 'x' not in self.notification_options):
            logger.debug("Host: %s, notification %s sending is blocked by options",
                         self.get_name(), n_type)
            return True
        if (n_type in ('FLAPPINGSTART', 'FLAPPINGSTOP', 'FLAPPINGDISABLED') and
                'f' not in self.notification_options):
            logger.debug("Host: %s, notification %s sending is blocked by options",
                         n_type, self.get_name())
            return True
        if (n_type in ('DOWNTIMESTART', 'DOWNTIMEEND', 'DOWNTIMECANCELLED') and
                's' not in self.notification_options):
            logger.debug("Host: %s, notification %s sending is blocked by options",
                         self.get_name(), n_type)
            return True

        # Acknowledgements make no sense when the status is ok/up
        # Flapping
        # TODO block if not notify_on_flapping
        if (n_type in ('FLAPPINGSTART', 'FLAPPINGSTOP', 'FLAPPINGDISABLED') and
                self.scheduled_downtime_depth > 0) or \
                n_type == 'ACKNOWLEDGEMENT' and self.state == self.ok_up:
            logger.debug("Host: %s, notification %s sending is blocked by downtime",
                         self.get_name(), n_type)
            return True

        # When in deep downtime, only allow end-of-downtime notifications
        # In depth 1 the downtime just started and can be notified
        if self.scheduled_downtime_depth > 1 and n_type not in ('DOWNTIMEEND', 'DOWNTIMECANCELLED'):
            logger.debug("Host: %s, notification %s sending is blocked by downtime",
                         self.get_name(), n_type)
            return True

        # Block if in a scheduled downtime and a problem arises
        if self.scheduled_downtime_depth > 0 and n_type in ('PROBLEM', 'RECOVERY'):
            logger.debug("Host: %s, notification %s sending is blocked by downtime",
                         self.get_name(), n_type)
            return True

        # Block if the status is SOFT
        # Block if the problem has already been acknowledged
        if self.state_type == 'SOFT' and n_type == 'PROBLEM' or \
                self.problem_has_been_acknowledged and n_type != 'ACKNOWLEDGEMENT':
            logger.debug("Host: %s, notification %s sending is blocked by soft state "
                         "or acknowledged", self.get_name(), n_type)
            return True

        # Block if flapping
        if self.is_flapping and n_type not in ('FLAPPINGSTART', 'FLAPPINGSTOP', 'FLAPPINGDISABLED'):
            logger.debug("Host: %s, notification %s sending is blocked by flapping",
                         self.get_name(), n_type)
            return True

        # Block if business rule smart notifications is enabled and all its
        # children have been acknowledged or are under downtime.
        if self.got_business_rule is True \
                and self.business_rule_smart_notifications is True \
                and self.business_rule_notification_is_blocked(hosts, services) is True \
                and n_type == 'PROBLEM':
            logger.debug("Host: %s, notification %s sending is blocked by business rules",
                         self.get_name(), n_type)
            return True

        return False

    def get_total_services(self):
        """Get the number of services for this host

        :return: service list length
        :rtype: str
        """
        return str(len(self.services))

    def _tot_services_by_state(self, services, state):
        """Get the number of service in the specified state

        :param state: state to filter service
        :type state:
        :return: number of service with s.state_id == state
        :rtype: int
        """
        return str(sum(1 for s in self.services
                       if services[s].state_id == state))

    def get_total_services_ok(self, services):
        """
        Get number of services ok

        :param services:
        :type services:
        :return: Number of services
        :rtype: int
        """
        return self._tot_services_by_state(services, 0)

    def get_total_services_warning(self, services):
        """
        Get number of services warning

        :param services:
        :type services:
        :return: Number of services
        :rtype: int
        """
        return self._tot_services_by_state(services, 1)

    def get_total_services_critical(self, services):
        """
        Get number of services critical

        :param services:
        :type services:
        :return: Number of services
        :rtype: int
        """
        return self._tot_services_by_state(services, 2)

    def get_total_services_unknown(self, services):
        """
        Get number of services unknown

        :param services:
        :type services:
        :return: Number of services
        :rtype: int
        """
        return self._tot_services_by_state(services, 3)

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

    def get_snapshot_command(self):
        """Wrapper to get the name of the snapshot_command attribute

        :return: snapshot_command name
        :rtype: str
        """
        return self.snapshot_command.get_name()

    def get_short_status(self, hosts, services):
        """Get the short status of this host

        :return: "U", "D", "N" or "n/a" based on host state_id or business_rule state
        :rtype: str
        """
        mapping = {
            0: "U",
            1: "D",
            4: "N",
        }
        if self.got_business_rule:
            return mapping.get(self.business_rule.get_state(hosts, services), "n/a")
        else:
            return mapping.get(self.state_id, "n/a")

    def get_status(self, hosts, services):
        """Get the status of this host

        :return: "UP", "DOWN", "UNREACHABLE" or "n/a" based on host state_id or business_rule state
        :rtype: str
        """
        if self.got_business_rule:
            mapping = {
                0: "UP",
                1: "DOWN",
                4: "UNREACHABLE",
            }
            return mapping.get(self.business_rule.get_state(hosts, services), "n/a")
        else:
            return self.state

    def get_downtime(self):
        """Accessor to scheduled_downtime_depth attribute

        :return: scheduled downtime depth
        :rtype: str
        TODO: Move to util or SchedulingItem class
        """
        return str(self.scheduled_downtime_depth)


class Hosts(SchedulingItems):
    """Class for the hosts lists. It's mainly for configuration

    """
    inner_class = Host

    def linkify(self, timeperiods=None, commands=None, contacts=None,  # pylint: disable=R0913
                realms=None, resultmodulations=None, businessimpactmodulations=None,
                escalations=None, hostgroups=None, triggers=None,
                checkmodulations=None, macromodulations=None):
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
        :param hostgroups: hostgroups to link
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
        self.linkify_host_by_host()
        self.linkify_host_by_hostgroup(hostgroups)
        self.linkify_one_command_with_commands(commands, 'check_command')
        self.linkify_one_command_with_commands(commands, 'event_handler')
        self.linkify_one_command_with_commands(commands, 'snapshot_command')

        self.linkify_with_contacts(contacts)
        self.linkify_host_by_realm(realms)
        self.linkify_with_resultmodulations(resultmodulations)
        self.linkify_with_business_impact_modulations(businessimpactmodulations)
        # WARNING: all escalations will not be linked here
        # (only the escalations, not serviceescalations or hostescalations).
        # This last one will be linked in escalations linkify.
        self.linkify_with_escalations(escalations)
        self.linkify_with_triggers(triggers)
        self.linkify_with_checkmodulations(checkmodulations)
        self.linkify_with_macromodulations(macromodulations)

    def fill_predictable_missing_parameters(self):
        """Loop on hosts and call Host.fill_predictable_missing_parameters()

        :return: None
        """
        for host in self:
            host.fill_predictable_missing_parameters()

    def linkify_host_by_host(self):
        """Link hosts with their parents

        :return: None
        """
        for host in self:
            parents = host.parents
            # The new member list
            new_parents = []
            for parent in parents:
                parent_object = self.find_by_name(parent)
                if parent_object is not None:
                    new_parents.append(parent_object.uuid)
                else:
                    host.add_error("the parent '%s' for the host '%s' is unknown!" %
                                   (parent, host.get_name()))

            # We find the id, we replace the names
            host.parents = new_parents

    def linkify_host_by_realm(self, realms):
        """Link hosts with realms

        :param realms: realms object to link with
        :type realms: alignak.objects.realm.Realms
        :return: None
        """
        default_realm = realms.get_default()
        for host in self:
            if host.realm:
                realm = realms.find_by_name(host.realm.strip())
                if realm is None:
                    host.add_error("the host %s got an invalid realm (%s)!" %
                                   (host.get_name(), host.realm))
                    # This to avoid having an host.realm as a string name
                    # Todo: should be simplified, no?
                    host.realm_name = host.realm
                    host.realm = None
                else:
                    host.realm = realm.uuid
                    host.realm_name = realm.get_name()  # Needed for the specific $HOSTREALM$ macro
            else:
                # Applying default realm to an host
                host.realm = default_realm.uuid if default_realm else ''
                host.realm_name = default_realm.get_name() if default_realm else ''
                host.got_default_realm = True

    def linkify_host_by_hostgroup(self, hostgroups):
        """Link hosts with hostgroups

        :param hostgroups: hostgroups object to link with
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :return: None
        """
        # Register host in the hostgroups
        for host in self:
            new_hostgroups = []
            if hasattr(host, 'hostgroups') and host.hostgroups:
                # Because hosts groups can be created because an host references
                # a not existing group or because a group exists in the configuration,
                # we can have an uuid or a name...
                for hostgroup_name in host.hostgroups:
                    if hostgroup_name in hostgroups:
                        # We got an uuid and already linked the item with its group
                        new_hostgroups.append(hostgroup_name)
                        continue

                    hostgroup = hostgroups.find_by_name(hostgroup_name)
                    if hostgroup is not None:
                        new_hostgroups.append(hostgroup.uuid)
                    else:
                        host.add_error("the hostgroup '%s' of the host '%s' is unknown" %
                                       (hostgroup_name, host.host_name))

            host.hostgroups = list(set(new_hostgroups))

    def explode(self, hostgroups, contactgroups):
        """Explode hosts with hostgroups, contactgroups::

        * Add contact from contactgroups to host contacts
        * Add host into their hostgroups as hostgroup members

        :param hostgroups: Hostgroups to explode
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :param contactgroups: Contactgorups to explode
        :type contactgroups: alignak.objects.contactgroup.Contactgroups
        :return: None
        """
        for template in self.templates.itervalues():
            # Set contacts from the contacts groups into our contacts
            self.explode_contact_groups_into_contacts(template, contactgroups)

        for host in self:
            # Set contacts from the contacts groups into our contacts
            self.explode_contact_groups_into_contacts(host, contactgroups)

            # Register host in the hostgroups
            if getattr(host, 'hostgroups', None) is not None:
                for hostgroup in host.hostgroups:
                    hostgroups.add_group_member(host, hostgroup)

    def apply_dependencies(self):
        """Loop on hosts and register dependency between parent and son

        call Host.fill_parents_dependency()

        :return: None
        """
        for host in self:
            for parent_id in host.parents:
                if parent_id is None:
                    continue
                parent = self[parent_id]
                if parent.active_checks_enabled:
                    # Add parent in the list
                    host.act_depend_of.append((parent_id, ['d', 'x', 's', 'f'], '', True))

                    # Add child in the parent
                    parent.act_depend_of_me.append((host.uuid, ['d', 'x', 's', 'f'], '', True))

                    # And add the parent/child dep filling too, for broking
                    parent.child_dependencies.add(host.uuid)
                    host.parent_dependencies.add(parent_id)

    def find_hosts_that_use_template(self, tpl_name):
        """Find hosts that use the template defined in argument tpl_name

        :param tpl_name: the template name we filter or
        :type tpl_name: str
        :return: list of the host_name of the hosts that got the template tpl_name in tags
        :rtype: list[str]
        """
        return [h.host_name for h in self if tpl_name in h.tags if hasattr(h, "host_name")]

    def is_correct(self):
        """Check if the hosts list configuration is correct ::

        * check if any loop exists in each host dependencies
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """
        state = True

        # Internal checks before executing inherited function...
        loop = self.no_loop_in_parents("self", "parents")
        if len(loop) > 0:
            self.add_error("Loop detected while checking hosts ")
            state = False
            for uuid, item in self.items.iteritems():
                for elem in loop:
                    if elem == uuid:
                        state = False
                        self.add_error("Host %s is parent in dependency defined in %s" %
                                       (item.get_name(), item.imported_from))
                    elif elem in item.parents:
                        state = False
                        self.add_error("Host %s is child in dependency defined in %s" %
                                       (self[elem].get_name(), self[elem].imported_from))

        return super(Hosts, self).is_correct() and state
