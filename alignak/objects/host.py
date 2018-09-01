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
# pylint: disable=too-many-lines

import os
import time
import logging

from alignak.objects.schedulingitem import SchedulingItem, SchedulingItems

# from alignak.util import brok_last_time
from alignak.autoslots import AutoSlots
from alignak.property import BoolProp, IntegerProp, StringProp, ListProp, CharProp
from alignak.log import make_monitoring_log

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Host(SchedulingItem):  # pylint: disable=R0904
    """Host class implements monitoring concepts for host.
    For example it defines parents, check_interval, check_command  etc.
    """
    # AutoSlots create the __slots__ with properties and
    # running_properties names
    __metaclass__ = AutoSlots

    ok_up = u'UP'
    my_type = 'host'

    # if Host(or more generally Item) instances were created with all properties
    # having a default value set in the instance then we wouldn't need this:
    service_includes = service_excludes = []
    # though, as these 2 attributes are to be relatively low used it's not
    # that bad to have the default be defined only once here at the class level.

    properties = SchedulingItem.properties.copy()
    properties.update({
        'host_name':
            StringProp(fill_brok=['full_status', 'check_result', 'next_schedule']),
        'alias':
            StringProp(default=u'', fill_brok=['full_status']),
        'address':
            StringProp(fill_brok=['full_status']),
        'address6':
            StringProp(fill_brok=['full_status'], default=''),
        'parents':
            ListProp(default=[],
                     fill_brok=['full_status'], merging='join', split_on_comma=True),
        'hostgroups':
            ListProp(default=[],
                     fill_brok=['full_status'], merging='join', split_on_comma=True),
        'check_command':
            StringProp(default='', fill_brok=['full_status']),
        'flap_detection_options':
            ListProp(default=['o', 'd', 'x'], fill_brok=['full_status'],
                     merging='join', split_on_comma=True),
        'notification_options':
            ListProp(default=['d', 'x', 'r', 'f'], fill_brok=['full_status'],
                     merging='join', split_on_comma=True),
        'vrml_image':
            StringProp(default=u'', fill_brok=['full_status']),
        'statusmap_image':
            StringProp(default=u'', fill_brok=['full_status']),
        'freshness_state':
            CharProp(default='x', fill_brok=['full_status']),

        # No slots for this 2 because begin property by a number seems bad
        # it's stupid!
        '2d_coords':
            StringProp(default=u'', fill_brok=['full_status'], no_slots=True),
        '3d_coords':
            StringProp(default=u'', fill_brok=['full_status'], no_slots=True),
        # New to alignak
        # 'fill_brok' is ok because in scheduler it's already
        # a string from conf_send_preparation
        'service_overrides':
            ListProp(default=[], merging='duplicate', split_on_comma=False),
        'service_excludes':
            ListProp(default=[], merging='duplicate', split_on_comma=True),
        'service_includes':
            ListProp(default=[], merging='duplicate', split_on_comma=True),
        'snapshot_criteria':
            ListProp(default=['d', 'x'], fill_brok=['full_status'], merging='join'),

        # Realm stuff
        'realm':
            StringProp(default=u'', fill_brok=['full_status']),
    })

    # properties set only for running purpose
    # retention: save/load this property from retention
    running_properties = SchedulingItem.running_properties.copy()
    running_properties.update({
        'state':
            StringProp(default=u'UP', fill_brok=['full_status', 'check_result'],
                       retention=True),
        'last_time_up':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_down':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_unreachable':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),

        # Our services
        'services':
            StringProp(default=[]),

        # Realm stuff
        'realm_name':
            StringProp(default=u'', fill_brok=['full_status']),
        'got_default_realm':
            BoolProp(default=False),

        'state_before_hard_unknown_reach_phase':
            StringProp(default=u'UP', retention=True),
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
        'HOSTGROUPALIAS': ('get_groupalias', ['hostgroups']),
        'HOSTGROUPALIASES': ('get_groupaliases', ['hostgroups']),
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
        'TOTALHOSTSERVICESCRITICAL': ('get_total_services_critical', ['services']),
        'TOTALHOSTSERVICESUNKNOWN': ('get_total_services_unknown', ['services']),
        'TOTALHOSTSERVICESUNREACHABLE': ('get_total_services_unreachable', ['services']),
        'HOSTBUSINESSIMPACT':  'business_impact',
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

    def __init__(self, params=None, parsing=True):
        # Must convert the unreachable properties to manage the new 'x' option value
        self.convert_conf_for_unreachable(params=params)
        super(Host, self).__init__(params, parsing=parsing)

    def __str__(self):  # pragma: no cover
        return '<Host %s, uuid=%s, %s (%s), realm: %s, use: %s />' \
               % (self.get_full_name(), self.uuid, self.state, self.state_type,
                  getattr(self, 'realm', 'Unset'), getattr(self, 'use', None))
    __repr__ = __str__

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

    @staticmethod
    def convert_conf_for_unreachable(params):
        """
        The 'u' state for UNREACHABLE has been rewritten in 'x' in:
        * flap_detection_options
        * notification_options
        * snapshot_criteria

        So convert value from config file to keep compatibility with Nagios

        :param params: parameters of the host before put in properties
        :type params: dict
        :return: None
        """
        if params is None:
            return

        for prop in ['flap_detection_options', 'notification_options',
                     'snapshot_criteria', 'stalking_options']:
            if prop in params:
                params[prop] = [p.replace('u', 'x') for p in params[prop]]

        if 'initial_state' in params and \
                (params['initial_state'] == 'u' or params['initial_state'] == ['u']):
            params['initial_state'] = 'x'

        if 'freshness_state' in params and \
                (params['freshness_state'] == 'u' or params['freshness_state'] == ['u']):
            params['freshness_state'] = 'x'

    def fill_predictive_missing_parameters(self):
        """Fill address with host_name if not already set
        and define state with initial_state

        :return: None
        """
        if hasattr(self, 'host_name') and not hasattr(self, 'address'):
            self.address = self.host_name
        if hasattr(self, 'host_name') and not hasattr(self, 'alias'):
            self.alias = self.host_name
        if self.initial_state == 'd':
            self.state = 'DOWN'
        elif self.initial_state == 'x':
            self.state = 'UNREACHABLE'

    def is_correct(self):
        """Check if this object configuration is correct ::

        * Check our own specific properties
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """
        state = True

        # Internal checks before executing inherited function...
        cls = self.__class__
        if hasattr(self, 'host_name'):
            for char in cls.illegal_object_name_chars:
                if char in self.host_name:
                    self.add_error("[%s::%s] host_name contains an illegal character: %s"
                                   % (self.my_type, self.get_name(), char))
                    state = False

        # Fred: do not alert about missing check_command for an host... this because 1/ it is
        # very verbose if hosts are not checked and 2/ because it is the Nagios default behavior
        # if not self.check_command:
        #     self.add_warning("[%s::%s] has no defined check command"
        #                      % (self.my_type, self.get_name()))

        if self.notifications_enabled and not self.contacts:
            self.add_warning("[%s::%s] notifications are enabled but no contacts nor "
                             "contact_groups property is defined for this host"
                             % (self.my_type, self.get_name()))

        return super(Host, self).is_correct() and state

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

    def get_full_name(self):
        """Accessor to host_name attribute

        :return: host_name
        :rtype: str
        """
        if self.is_tpl():
            return "tpl-%s" % (self.name)
        return getattr(self, 'host_name', 'unnamed')

    def get_groupname(self, hostgroups):
        """Get name of the first host's hostgroup (alphabetic sort)

        :return: host group name
        :rtype: str
        TODO: Clean this. It returns the first hostgroup (alphabetic sort)
        """
        group_names = self.get_groupnames(hostgroups).split(',')
        return group_names[0]

    def get_groupalias(self, hostgroups):
        """Get alias of the first host's hostgroup (alphabetic sort on group alias)

        :return: host group alias
        :rtype: str
        TODO: Clean this. It returns the first hostgroup alias (alphabetic sort)
        """
        group_aliases = self.get_groupaliases(hostgroups).split(',')
        return group_aliases[0]

    def get_groupnames(self, hostgroups):
        """Get names of the host's hostgroups

        :return: comma separated names of hostgroups alphabetically sorted
        :rtype: str
        """
        group_names = []
        for hostgroup_id in self.hostgroups:
            hostgroup = hostgroups[hostgroup_id]
            group_names.append(hostgroup.get_name())
        return ','.join(sorted(group_names))

    def get_groupaliases(self, hostgroups):
        """Get aliases of the host's hostgroups

        :return: comma separated aliases of hostgroups alphabetically sorted
        :rtype: str
        """
        group_aliases = []
        for hostgroup_id in self.hostgroups:
            hostgroup = hostgroups[hostgroup_id]
            group_aliases.append(hostgroup.alias)
        return ','.join(sorted(group_aliases))

    def get_hostgroups(self):
        """Accessor to hostgroups attribute

        :return: hostgroup list object of host
        :rtype: list
        """
        return self.hostgroups

    def add_service_link(self, service):
        """Add a service to the service list of this host

        :param service: the service to add
        :type service: alignak.objects.service.Service
        :return: None
        """
        self.services.append(service)

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
        """Set the state in UP, DOWN, or UNREACHABLE according to the status of a check result.

        :param status: integer between 0 and 3 (but not 1)
        :type status: int
        :return: None
        """
        now = time.time()

        # we should put in last_state the good last state:
        # if not just change the state by an problem/impact
        # we can take current state. But if it's the case, the
        # real old state is self.state_before_impact (it's the TRUE
        # state in fact)
        # And only if we enable the impact state change
        cls = self.__class__
        if (cls.enable_problem_impacts_states_change and
                self.is_impact and not self.state_changed_since_impact):
            self.last_state = self.state_before_impact
        else:
            self.last_state = self.state

        # There is no 1 case because it should have been managed by the caller for a host
        # like the schedulingitem::consume method.
        if status == 0:
            self.state = u'UP'
            self.state_id = 0
            self.last_time_up = int(self.last_state_update)
            # self.last_time_up = self.last_state_update
            state_code = 'u'
        elif status in (2, 3):
            self.state = u'DOWN'
            self.state_id = 1
            self.last_time_down = int(self.last_state_update)
            # self.last_time_down = self.last_state_update
            state_code = 'd'
        elif status == 4:
            self.state = u'UNREACHABLE'
            self.state_id = 4
            self.last_time_unreachable = int(self.last_state_update)
            # self.last_time_unreachable = self.last_state_update
            state_code = 'x'
        else:
            self.state = u'DOWN'  # exit code UNDETERMINED
            self.state_id = 1
            # self.last_time_down = int(self.last_state_update)
            self.last_time_down = self.last_state_update
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
        if status == 'o' and self.state == u'UP':
            return True
        if status == 'd' and self.state == u'DOWN':
            return True
        if status in ['u', 'x'] and self.state == u'UNREACHABLE':
            return True
        return False

    def last_time_non_ok_or_up(self):
        """Get the last time the host was in a non-OK state

        :return: self.last_time_down if self.last_time_down > self.last_time_up, 0 otherwise
        :rtype: int
        """
        non_ok_times = [x for x in [self.last_time_down]
                        if x > self.last_time_up]
        if not non_ok_times:
            last_time_non_ok = 0  # todo: program_start would be better?
        else:
            last_time_non_ok = min(non_ok_times)
        return last_time_non_ok

    def raise_check_result(self):
        """Raise ACTIVE CHECK RESULT entry
        Example : "ACTIVE HOST CHECK: server;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        if not self.__class__.log_active_checks:
            return

        log_level = 'info'
        if self.state == 'DOWN':
            log_level = 'error'
        elif self.state == 'UNREACHABLE':
            log_level = 'warning'
        brok = make_monitoring_log(
            log_level, 'ACTIVE HOST CHECK: %s;%s;%d;%s' % (self.get_name(), self.state,
                                                           self.attempt, self.output)
        )
        self.broks.append(brok)

    def raise_alert_log_entry(self):
        """Raise HOST ALERT entry
        Format is : "HOST ALERT: *get_name()*;*state*;*state_type*;*attempt*;*output*"
        Example : "HOST ALERT: server;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        if self.__class__.log_alerts:
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

        if 'ALIGNAK_LOG_ALERTS' in os.environ:
            if os.environ['ALIGNAK_LOG_ALERTS'] == 'WARNING':
                logger.warning('HOST ALERT: %s;%s;%s;%d;%s', self.get_name(), self.state,
                               self.state_type, self.attempt, self.output)
            else:
                logger.info('HOST ALERT: %s;%s;%s;%d;%s', self.get_name(), self.state,
                            self.state_type, self.attempt, self.output)

    def raise_initial_state(self):
        """Raise CURRENT HOST ALERT entry (info level)
        Format is : "CURRENT HOST STATE: *get_name()*;*state*;*state_type*;*attempt*;*output*"
        Example : "CURRENT HOST STATE: server;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        if not self.__class__.log_initial_states:
            return

        log_level = 'info'
        if self.state == 'DOWN':
            log_level = 'error'
        if self.state == 'UNREACHABLE':
            log_level = 'warning'
        brok = make_monitoring_log(
            log_level, 'CURRENT HOST STATE: %s;%s;%s;%d;%s' % (
                self.get_name(), self.state, self.state_type, self.attempt, self.output
            )
        )
        self.broks.append(brok)

    def raise_notification_log_entry(self, notif, contact, host_ref=None):
        """Raise HOST NOTIFICATION entry (critical level)
        Format is : "HOST NOTIFICATION: *contact.get_name()*;*self.get_name()*;*state*;
                     *command.get_name()*;*output*"
        Example : "HOST NOTIFICATION: superadmin;server;UP;notify-by-rss;no output"

        :param notif: notification object created by host alert
        :type notif: alignak.objects.notification.Notification
        :return: None
        """
        if self.__class__.log_notifications:
            log_level = 'info'
            command = notif.command_call
            if notif.type in (u'DOWNTIMESTART', u'DOWNTIMEEND', u'DOWNTIMECANCELLED',
                              u'CUSTOM', u'ACKNOWLEDGEMENT',
                              u'FLAPPINGSTART', u'FLAPPINGSTOP', u'FLAPPINGDISABLED'):
                state = '%s (%s)' % (notif.type, self.state)
            else:
                state = self.state
                if self.state == 'UNREACHABLE':
                    log_level = 'warning'
                if self.state == 'DOWN':
                    log_level = 'error'

            brok = make_monitoring_log(
                log_level, "HOST NOTIFICATION: %s;%s;%s;%s;%s;%s" % (
                    contact.get_name(), self.get_name(), state,
                    notif.notif_nb, command.get_name(), self.output
                )
            )
            self.broks.append(brok)

        if 'ALIGNAK_LOG_NOTIFICATIONS' in os.environ:
            if os.environ['ALIGNAK_LOG_NOTIFICATIONS'] == 'WARNING':
                logger.warning("HOST NOTIFICATION: %s;%s;%s;%s;%s;%s",
                               contact.get_name(), self.get_name(), state,
                               notif.notif_nb, command.get_name(), self.output)
            else:
                logger.info("HOST NOTIFICATION: %s;%s;%s;%s;%s;%s",
                            contact.get_name(), self.get_name(), state,
                            notif.notif_nb, command.get_name(), self.output)

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
            'info',
            "HOST FLAPPING ALERT: %s;STARTED; Host appears to have started "
            "flapping (%.1f%% change >= %.1f%% threshold)"
            % (self.get_name(), change_ratio, threshold)
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
            'info',
            "HOST FLAPPING ALERT: %s;STOPPED; Host appears to have stopped flapping "
            "(%.1f%% change < %.1f%% threshold)"
            % (self.get_name(), change_ratio, threshold)
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

    def raise_acknowledge_log_entry(self):
        """Raise HOST ACKNOWLEDGE ALERT entry (critical level)

        :return: None
        """
        if not self.__class__.log_acknowledgements:
            return

        brok = make_monitoring_log(
            'info', "HOST ACKNOWLEDGE ALERT: %s;STARTED; "
                    "Host problem has been acknowledged" % self.get_name()
        )
        self.broks.append(brok)

    def raise_unacknowledge_log_entry(self):
        """Raise HOST ACKNOWLEDGE STOPPED entry (critical level)

        :return: None
        """
        if not self.__class__.log_acknowledgements:
            return

        brok = make_monitoring_log(
            'info', "HOST ACKNOWLEDGE ALERT: %s;EXPIRED; "
                    "Host problem acknowledge expired" % self.get_name()
        )
        self.broks.append(brok)

    def raise_enter_downtime_log_entry(self):
        """Raise HOST DOWNTIME ALERT entry (critical level)
        Format is : "HOST DOWNTIME ALERT: *get_name()*;STARTED;
                    Host has entered a period of scheduled downtime"
        Example : "HOST DOWNTIME ALERT: test_host_0;STARTED;
                   Host has entered a period of scheduled downtime"

        :return: None
        """
        if not self.__class__.log_downtimes:
            return

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
        if not self.__class__.log_downtimes:
            return

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
        if not self.__class__.log_downtimes:
            return

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
        if check.status == u'waitconsume':
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

    def notification_is_blocked_by_contact(self, notifways, timeperiods, notif, contact):
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

    def is_blocking_notifications(self, notification_period, hosts, services, n_type, t_wished):
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-return-statements, too-many-boolean-expressions
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
        TODO: Refactor this, a lot of code duplication with Service.is_blocking_notifications
        """
        logger.debug("Checking if a host %s (%s) notification is blocked...",
                     self.get_name(), self.state)
        if t_wished is None:
            t_wished = time.time()

        # TODO
        # forced notification -> false
        # custom notification -> false

        # Block if notifications are program-wide disabled
        # Block if notifications are disabled for this host
        # Block if the current status is in the notification_options d,u,r,f,s
        if not self.enable_notifications or \
                not self.notifications_enabled or \
                'n' in self.notification_options:
            logger.debug("Host: %s, notification %s sending is blocked by globals",
                         self.get_name(), n_type)
            return True

        # Does the notification period allow sending out this notification?
        if notification_period is not None and not notification_period.is_time_valid(t_wished):
            logger.debug("Host: %s, notification %s sending is blocked by globals",
                         self.get_name(), n_type)
            return True

        if n_type in (u'PROBLEM', u'RECOVERY') and (
                self.state == u'DOWN' and 'd' not in self.notification_options or
                self.state == u'UP' and 'r' not in self.notification_options or
                self.state == u'UNREACHABLE' and 'x' not in self.notification_options):
            logger.debug("Host: %s, notification %s sending is blocked by options",
                         self.get_name(), n_type)
            return True

        if (n_type in (u'FLAPPINGSTART', u'FLAPPINGSTOP', u'FLAPPINGDISABLED') and
                'f' not in self.notification_options):
            logger.debug("Host: %s, notification %s sending is blocked by options",
                         n_type, self.get_name())
            return True

        if (n_type in (u'DOWNTIMESTART', u'DOWNTIMEEND', u'DOWNTIMECANCELLED') and
                's' not in self.notification_options):
            logger.debug("Host: %s, notification %s sending is blocked by options",
                         n_type, self.get_name())
            return True

        # Flapping notifications are blocked when in scheduled downtime
        if (n_type in (u'FLAPPINGSTART', u'FLAPPINGSTOP', u'FLAPPINGDISABLED') and
                self.scheduled_downtime_depth > 0):
            logger.debug("Host: %s, notification %s sending is blocked by downtime",
                         self.get_name(), n_type)
            return True

        # Acknowledgements make no sense when the status is ok/up
        if n_type == u'ACKNOWLEDGEMENT' and self.state == self.ok_up:
            logger.debug("Host: %s, notification %s sending is blocked by current state",
                         self.get_name(), n_type)
            return True

        # When in deep downtime, only allow end-of-downtime notifications
        # In depth 1 the downtime just started and can be notified
        if self.scheduled_downtime_depth > 1 and n_type not in (u'DOWNTIMEEND',
                                                                u'DOWNTIMECANCELLED'):
            logger.debug("Host: %s, notification %s sending is blocked by deep downtime",
                         self.get_name(), n_type)
            return True

        # Block if in a scheduled downtime and a problem arises
        if self.scheduled_downtime_depth > 0 and \
                n_type in (u'PROBLEM', u'RECOVERY', u'ACKNOWLEDGEMENT'):
            logger.debug("Host: %s, notification %s sending is blocked by downtime",
                         self.get_name(), n_type)
            return True

        # Block if the status is SOFT
        if self.state_type == u'SOFT' and n_type == u'PROBLEM':
            logger.debug("Host: %s, notification %s sending is blocked by soft state",
                         self.get_name(), n_type)
            return True

        # Block if the problem has already been acknowledged
        if self.problem_has_been_acknowledged and n_type not in (u'ACKNOWLEDGEMENT',
                                                                 u'DOWNTIMESTART',
                                                                 u'DOWNTIMEEND',
                                                                 u'DOWNTIMECANCELLED'):
            logger.debug("Host: %s, notification %s sending is blocked by acknowledged",
                         self.get_name(), n_type)
            return True

        # Block if flapping
        if self.is_flapping and n_type not in (u'FLAPPINGSTART',
                                               u'FLAPPINGSTOP',
                                               u'FLAPPINGDISABLED'):
            logger.debug("Host: %s, notification %s sending is blocked by flapping",
                         self.get_name(), n_type)
            return True

        # Block if business rule smart notifications is enabled and all its
        # children have been acknowledged or are under downtime.
        if self.got_business_rule is True \
                and self.business_rule_smart_notifications is True \
                and self.business_rule_notification_is_blocked(hosts, services) is True \
                and n_type == u'PROBLEM':
            logger.debug("Host: %s, notification %s sending is blocked by business rules",
                         self.get_name(), n_type)
            return True

        logger.debug("Host: %s, notification %s sending is not blocked", self.get_name(), n_type)
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
        """Get number of services ok

        :param services:
        :type services:
        :return: Number of services
        :rtype: int
        """
        return self._tot_services_by_state(services, 0)

    def get_total_services_warning(self, services):
        """Get number of services warning

        :param services:
        :type services:
        :return: Number of services
        :rtype: int
        """
        return self._tot_services_by_state(services, 1)

    def get_total_services_critical(self, services):
        """Get number of services critical

        :param services:
        :type services:
        :return: Number of services
        :rtype: int
        """
        return self._tot_services_by_state(services, 2)

    def get_total_services_unknown(self, services):
        """Get number of services unknown

        :param services:
        :type services:
        :return: Number of services
        :rtype: int
        """
        return self._tot_services_by_state(services, 3)

    def get_total_services_unreachable(self, services):
        """Get number of services unreachable

        :param services:
        :type services:
        :return: Number of services
        :rtype: int
        """
        return self._tot_services_by_state(services, 4)

    def get_ack_author_name(self):
        """Get the author of the acknowledgement

        :return: author
        :rtype: str
        """
        if self.acknowledgement is None:
            return ''
        return getattr(self.acknowledgement, "author", '')

    def get_ack_comment(self):
        """Get the comment of the acknowledgement

        :return: comment
        :rtype: str
        """
        if self.acknowledgement is None:
            return ''
        return getattr(self.acknowledgement, "comment", '')

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

    def get_downtime(self):
        """Accessor to scheduled_downtime_depth attribute

        :return: scheduled downtime depth
        :rtype: str
        """
        return str(self.scheduled_downtime_depth)

    def get_short_status(self, hosts, services):
        """Get the short status of this host

        :return: "U", "D", "X" or "n/a" based on host state_id or business_rule state
        :rtype: str
        """
        mapping = {
            0: "U",
            1: "D",
            4: "X",
        }
        if self.got_business_rule:
            return mapping.get(self.business_rule.get_state(hosts, services), "n/a")

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

        return self.state

    def get_overall_state(self, services):
        """Get the host overall state including the host self status
        and the status of its services

        Compute the host overall state identifier, including:
        - the acknowledged state
        - the downtime state

        The host overall state is (prioritized):
        - an host not monitored (5)
        - an host down (4)
        - an host unreachable (3)
        - an host downtimed (2)
        - an host acknowledged (1)
        - an host up (0)

        If the host overall state is <= 2, then the host overall state is the maximum value
        of the host overall state and all the host services overall states.

        The overall state of an host is:
        - 0 if the host is UP and all its services are OK
        - 1 if the host is DOWN or UNREACHABLE and acknowledged or
            at least one of its services is acknowledged and
            no other services are WARNING or CRITICAL
        - 2 if the host is DOWN or UNREACHABLE and in a scheduled downtime or
            at least one of its services is in a scheduled downtime and no
            other services are WARNING or CRITICAL
        - 3 if the host is UNREACHABLE or
            at least one of its services is WARNING
        - 4 if the host is DOWN or
            at least one of its services is CRITICAL
        - 5 if the host is not monitored

        :param services: a list of known services
        :type services: alignak.objects.service.Services

        :return: the host overall state
        :rtype: int
        """
        overall_state = 0

        if not self.monitored:
            overall_state = 5
        elif self.acknowledged:
            overall_state = 1
        elif self.downtimed:
            overall_state = 2
        elif self.state_type == 'HARD':
            if self.state == 'UNREACHABLE':
                overall_state = 3
            elif self.state == 'DOWN':
                overall_state = 4

        # Only consider the hosts services state if all is ok (or almost...)
        if overall_state <= 2:
            for service in self.services:
                if service in services:
                    service = services[service]
                    # Only for monitored services
                    if service.overall_state_id < 5:
                        overall_state = max(overall_state, service.overall_state_id)

        return overall_state


class Hosts(SchedulingItems):
    """Class for the hosts lists. It's mainly for configuration

    """
    name_property = "host_name"
    inner_class = Host

    def linkify(self, timeperiods=None, commands=None, contacts=None,  # pylint: disable=R0913
                realms=None, resultmodulations=None, businessimpactmodulations=None,
                escalations=None, hostgroups=None,
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
        # No more necessary
        self.linkify_h_by_realms(realms)
        self.linkify_with_resultmodulations(resultmodulations)
        self.linkify_with_business_impact_modulations(businessimpactmodulations)
        # WARNING: all escalations will not be link here
        # (just the escalation here, not serviceesca or hostesca).
        # This last one will be link in escalations linkify.
        self.linkify_with_escalations(escalations)
        self.linkify_with_checkmodulations(checkmodulations)
        self.linkify_with_macromodulations(macromodulations)

    def fill_predictive_missing_parameters(self):
        """Loop on hosts and call Host.fill_predictive_missing_parameters()

        :return: None
        """
        for host in self:
            host.fill_predictive_missing_parameters()

    def linkify_h_by_h(self):
        """Link hosts with their parents

        :return: None
        """
        for host in self:
            # The new member list
            new_parents = []
            for parent in getattr(host, 'parents', []):
                parent = parent.strip()
                o_parent = self.find_by_name(parent)
                if o_parent is not None:
                    new_parents.append(o_parent.uuid)
                else:
                    err = "the parent '%s' for the host '%s' is unknown!" % (parent,
                                                                             host.get_name())
                    self.add_error(err)
            # We find the id, we replace the names
            host.parents = new_parents

    def linkify_h_by_realms(self, realms):
        """Link hosts with realms

        :param realms: realms object to link with
        :type realms: alignak.objects.realm.Realms
        :return: None
        """
        default_realm = realms.get_default()
        for host in self:
            if not getattr(host, 'realm', None):
                # Applying default realm to an host
                host.realm = default_realm.uuid if default_realm else ''
                host.realm_name = default_realm.get_name() if default_realm else ''
                host.got_default_realm = True

            if host.realm not in realms:
                realm = realms.find_by_name(host.realm)
                if not realm:
                    continue
                host.realm = realm.uuid
            else:
                realm = realms[host.realm]

    def linkify_h_by_hg(self, hostgroups):
        """Link hosts with hostgroups

        :param hostgroups: hostgroups object to link with
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :return: None
        """
        # Register host in the hostgroups
        for host in self:
            new_hostgroups = []
            if hasattr(host, 'hostgroups') and host.hostgroups != []:
                hgs = [n.strip() for n in host.hostgroups if n.strip()]
                for hg_name in hgs:
                    # TODO: should an unknown hostgroup raise an error ?
                    hostgroup = hostgroups.find_by_name(hg_name)
                    if hostgroup is not None:
                        new_hostgroups.append(hostgroup.uuid)
                    else:
                        err = ("the hostgroup '%s' of the host '%s' is "
                               "unknown" % (hg_name, host.host_name))
                        host.add_error(err)
            host.hostgroups = new_hostgroups

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
        for template in list(self.templates.values()):
            # items::explode_contact_groups_into_contacts
            # take all contacts from our contact_groups into our contact property
            self.explode_contact_groups_into_contacts(template, contactgroups)

        # Register host in the hostgroups
        for host in self:
            # items::explode_contact_groups_into_contacts
            # take all contacts from our contact_groups into our contact property
            self.explode_contact_groups_into_contacts(host, contactgroups)

            if hasattr(host, 'host_name') and hasattr(host, 'hostgroups'):
                hname = host.host_name
                for hostgroup in host.hostgroups:
                    hostgroups.add_member(hname, hostgroup.strip())

    def apply_dependencies(self):
        """Loop on hosts and register dependency between parent and son

        call Host.fill_parents_dependency()

        :return: None
        """
        for host in self:
            for parent_id in getattr(host, 'parents', []):
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
        if loop:
            self.add_error("Loop detected while checking hosts")
            state = False
            for uuid, item in list(self.items.items()):
                for elem in loop:
                    if elem == uuid:
                        self.add_error("Host %s is parent in dependency defined in %s"
                                       % (item.get_name(), item.imported_from))
                    elif elem in item.parents:
                        self.add_error("Host %s is child in dependency defined in %s"
                                       % (self[elem].get_name(), self[elem].imported_from))

        return super(Hosts, self).is_correct() and state
