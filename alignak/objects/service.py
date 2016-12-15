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
# pylint: disable=C0302
# pylint: disable=R0904
import logging
import time
import re
import warnings

from alignak.objects.schedulingitem import SchedulingItem, SchedulingItems

from alignak.autoslots import AutoSlots
from alignak.util import (
    strip_and_uniq,
    format_t_into_dhms_format,
    generate_key_value_sequences,
    is_complex_expr,
    KeyValueSyntaxError)
from alignak.property import BoolProp, IntegerProp, StringProp, ListProp, CharProp
from alignak.log import make_monitoring_log

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Service(SchedulingItem):
    """Service class implements monitoring concepts for service.
    For example it defines parents, check_interval, check_command  etc.
    """
    # AutoSlots create the __slots__ with properties and
    # running_properties names
    __metaclass__ = AutoSlots

    # only used by (un)index_item (via 'name_property')
    name_property = 'unique_key'
    # used by item class for format specific value like for Broks
    my_type = 'service'

    # The host and service do not have the same 0 value, now yes :)
    ok_up = 'OK'

    properties = SchedulingItem.properties.copy()
    properties.update({
        'host_name':
            StringProp(fill_brok=['full_status', 'check_result', 'next_schedule'], special=True),
        'hostgroup_name':
            StringProp(default='', fill_brok=['full_status'], merging='join',
                       special=True),
        'service_description':
            StringProp(fill_brok=['full_status', 'check_result', 'next_schedule']),
        'servicegroups':
            ListProp(default=[], fill_brok=['full_status'], merging='join'),
        'is_volatile':
            BoolProp(default=False, fill_brok=['full_status']),
        'obsess_over_service':
            BoolProp(default=False, fill_brok=['full_status'], retention=True),
        'flap_detection_options':
            ListProp(default=['o', 'w', 'c', 'u', 'x'], fill_brok=['full_status']),
        'notification_options':
            ListProp(default=['w', 'u', 'c', 'r', 'f', 's', 'x'], fill_brok=['full_status']),
        'parallelize_check':
            BoolProp(default=True, fill_brok=['full_status']),
        'merge_host_contacts':
            BoolProp(default=False, fill_brok=['full_status']),

        'host_dependency_enabled':
            BoolProp(default=True, fill_brok=['full_status']),

        'freshness_state':
            CharProp(default='x', fill_brok=['full_status']),

        # Easy Service dep definition
        'service_dependencies':
            ListProp(default=[], merging='join', keep_empty=True),

        # service generator
        'duplicate_foreach':
            StringProp(default=''),
        'default_value':
            StringProp(default=''),

        # UI aggregation
        'aggregation':
            StringProp(default='', fill_brok=['full_status']),
        'snapshot_criteria':
            ListProp(default=['w', 'c', 'u', 'x'], fill_brok=['full_status'], merging='join'),
    })

    # properties used in the running state
    running_properties = SchedulingItem.running_properties.copy()
    running_properties.update({
        'state':
            StringProp(default='OK',
                       fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_ok':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_warning':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_critical':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_unknown':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'host':
            StringProp(default=None),
        'state_before_hard_unknown_reach_phase': StringProp(default='OK', retention=True),



    })

    # Mapping between Macros and properties (can be prop or a function)
    macros = SchedulingItem.macros.copy()
    macros.update({
        'SERVICEDESC': 'service_description',
        'SERVICEDISPLAYNAME': 'display_name',
        'SERVICESTATE': 'state',
        'SERVICESTATEID': 'state_id',
        'LASTSERVICESTATE': 'last_state',
        'LASTSERVICESTATEID': 'last_state_id',
        'SERVICESTATETYPE': 'state_type',
        'SERVICEATTEMPT': 'attempt',
        'MAXSERVICEATTEMPTS': 'max_check_attempts',
        'SERVICEISVOLATILE': 'is_volatile',
        'SERVICEEVENTID': 'current_event_id',
        'LASTSERVICEEVENTID': 'last_event_id',
        'SERVICEPROBLEMID': 'current_problem_id',
        'LASTSERVICEPROBLEMID': 'last_problem_id',
        'SERVICELATENCY': 'latency',
        'SERVICEEXECUTIONTIME': 'execution_time',
        'SERVICEDURATION': 'get_duration',
        'SERVICEDURATIONSEC': 'get_duration_sec',
        'SERVICEDOWNTIME': 'get_downtime',
        'SERVICEPERCENTCHANGE': 'percent_state_change',
        'SERVICEGROUPNAME': ('get_groupname', ['servicegroups']),
        'SERVICEGROUPNAMES': ('get_groupnames', ['servicegroups']),
        'LASTSERVICECHECK': 'last_chk',
        'LASTSERVICESTATECHANGE': 'last_state_change',
        'LASTSERVICEOK': 'last_time_ok',
        'LASTSERVICEWARNING': 'last_time_warning',
        'LASTSERVICEUNKNOWN': 'last_time_unknown',
        'LASTSERVICECRITICAL': 'last_time_critical',
        'SERVICEOUTPUT': 'output',
        'LONGSERVICEOUTPUT': 'long_output',
        'SERVICEPERFDATA': 'perf_data',
        'LASTSERVICEPERFDATA': 'last_perf_data',
        'SERVICECHECKCOMMAND': 'get_check_command',
        'SERVICESNAPSHOTCOMMAND': 'get_snapshot_command',
        'SERVICEACKAUTHOR': 'get_ack_author_name',
        'SERVICEACKAUTHORNAME': 'get_ack_author_name',
        'SERVICEACKAUTHORALIAS': 'get_ack_author_name',
        'SERVICEACKCOMMENT': 'get_ack_comment',
        'SERVICEACTIONURL': 'action_url',
        'SERVICENOTESURL': 'notes_url',
        'SERVICENOTES': 'notes',
        'SERVICEBUSINESSIMPACT': 'business_impact',
    })

    # This tab is used to transform old parameters name into new ones
    # so from Nagios2 format, to Nagios3 ones.
    # Or Alignak deprecated names like criticity
    old_properties = SchedulingItem.old_properties.copy()
    old_properties.update({
        'hostgroup': 'hostgroup_name',
        'hostgroups': 'hostgroup_name',
    })

    def __init__(self, params=None, parsing=True, debug=False):
        """Initialize a Service object

        :param debug: print debug information about the object properties
        :param params: parameters used to create the object
        :param parsing: if True, initial creation, else, object unserialization
        """
        if debug:
            print('Service __init__: %s, %d properties' %
                  (self.__class__, len(self.properties)))
            print('Service __init__: %s, properties list: %s' %
                  (self.__class__, [key for key in self.properties]))

        super(Service, self).__init__(params, parsing=parsing, debug=debug)

        if debug:
            print('Service __init__: %s, %d attributes' %
                  (self.__class__, len(self.__dict__)))
            print('Service __init__: %s, attributes list: %s' %
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
        """Define state with initial_state

        :return: None
        """
        if self.initial_state == 'w':
            self.state = 'WARNING'
        elif self.initial_state == 'u':
            self.state = 'UNKNOWN'
        elif self.initial_state == 'c':
            self.state = 'CRITICAL'
        elif self.initial_state == 'x':
            self.state = 'UNREACHABLE'

    @property
    def unique_key(self):
        """Unique key for this service

        :return: Tuple with host_name and service_description
        :rtype: tuple
        """
        return (getattr(self, 'host_name', 'unknown'),
                getattr(self, 'service_description', 'unknown'))

    @unique_key.setter
    def unique_key(self, unique_key):
        """Setter for unique_key attribute

        Only used for unnamed services, set the same value in host_name and service_description

        :param unique_key: value to set
        :return: None
        """
        self.host_name = unique_key
        self.service_description = unique_key

    def get_servicegroups(self):
        """Accessor to servicegroups attribute

        :return: servicegroup list object of host
        :rtype: list
        """
        return self.servicegroups

    def get_groupname(self, groups):
        """Get name of the service's first servicegroup

        :return: the first service group name
        :rtype: str
        """
        groupname = ''
        for group_id in self.servicegroups:
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
        for group_id in self.servicegroups:
            group = groups[group_id]
            if group:
                groupnames.append(group.get_name())

        return ','.join(sorted(groupnames))

    def get_name(self):
        """Get the name of the service (host_name/service_description)

        :return: service name (as service_description)
        :rtype: str
        """
        if self.is_tpl():
            return getattr(self, 'name', "unnamed")
        return "%s/%s" % (getattr(self, 'host_name', 'unnamed'),
                          getattr(self, 'service_description', 'unnamed'))

    def get_fullname(self):
        """Get the full name of the service (host_name / service_description)

        :return: service name (as service_description)
        :rtype: str
        """
        return self.get_name()

    def get_hostgroups(self, hosts):
        """Wrapper to access hostgroups attribute of host attribute

        :return: service hostgroups (host one)
        :rtype: alignak.objects.hostgroup.Hostgroups
        """
        return hosts[self.host].hostgroups

    def get_host_tags(self, hosts):
        """Wrapper to access tags attribute of host attribute

        :return: service tags (host one)
        :rtype: alignak.objects.tag.Tags
        """
        return hosts[self.host].tags

    def get_service_tags(self):
        """Accessor to tags attribute

        :return: service tags
        :rtype: alignak.objects.tag.Tags
        """
        return self.tags

    def is_correct(self):
        """Check if this object configuration is correct ::

        * Check our own specific properties
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """
        if getattr(self, 'service_description', ''):
            for char in self.__class__.illegal_object_name_chars:
                if char in self.service_description:
                    self.add_error("[%s::%s] service_description got an illegal character: %s" %
                                   (self.my_type, self.service_description, char))

            if not self.host_name or self.host_name == '':
                self.add_error("[%s::%s] not bound to any host." %
                               (self.my_type, self.service_description))
            elif self.host is None:
                self.add_error("[%s::%s] unknown host_name '%s'" %
                               (self.my_type, self.service_description, self.host_name))

        if not getattr(self, 'check_command', None):
            self.add_error("[%s::%s] has no check_command" %
                           (self.my_type, self.get_name()))

        return super(Service, self).is_correct() and self.conf_is_correct

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

    def set_state_from_exit_status(self, status, notif_period, hosts, services):
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
            # Now we add a value, we update the is_flapping prop
            self.update_flapping(notif_period, hosts, services)
        if self.state != self.last_state:
            self.last_state_change = self.last_state_update

        self.duration_sec = now - self.last_state_change

    def is_state(self, status):
        """Return if status match the current service status

        :param status: status to compare ( "o", "c", "w", "u", "x"). Usually comes from config files
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
        elif status == 'x' and self.state == 'UNREACHABLE':
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

    def raise_check_result(self):
        """Raise ACTIVE CHECK RESULT entry
        Example : "ACTIVE SERVICE CHECK: server;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        log_level = 'info'
        if self.state in ['WARNING', 'UNREACHABLE']:
            log_level = 'warning'
        elif self.state == 'CRITICAL':
            log_level = 'error'
        brok = make_monitoring_log(
            log_level, 'ACTIVE SERVICE CHECK: %s;%s;%s;%s;%d;%s' % (
                self.host_name, self.service_description,
                self.state, self.state_type,
                self.attempt, self.output
            )
        )
        self.broks.append(brok)

    def raise_alert_log_entry(self):
        """Raise SERVICE ALERT entry
        Format is : "SERVICE ALERT: *host.get_name()*;*get_name()*;*state*;*state_type*;*attempt*
                    ;*output*"
        Example : "SERVICE ALERT: server;Load;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        log_level = 'info'
        if self.state == 'WARNING':
            log_level = 'warning'
        if self.state == 'CRITICAL':
            log_level = 'error'
        brok = make_monitoring_log(
            log_level, 'SERVICE ALERT: %s;%s;%s;%s;%d;%s' % (
                self.host_name, self.service_description,
                self.state, self.state_type,
                self.attempt, self.output
            )
        )
        self.broks.append(brok)

    def raise_initial_state(self):
        """Raise SERVICE HOST ALERT entry (info level)
        Format is : "SERVICE HOST STATE: *host.get_name()*;*get_name()*;*state*;*state_type*
                    ;*attempt*;*output*"
        Example : "SERVICE HOST STATE: server;Load;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        log_level = 'info'
        if self.state == 'WARNING':
            log_level = 'warning'
        if self.state == 'CRITICAL':
            log_level = 'error'
        if self.__class__.log_initial_states:
            brok = make_monitoring_log(
                log_level, 'CURRENT SERVICE STATE: %s;%s;%s;%s;%d;%s' % (
                    self.host_name, self.service_description,
                    self.state, self.state_type,
                    self.attempt, self.output
                )
            )
            self.broks.append(brok)

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
        logger.warning("The freshness period of service '%s' on host '%s' is expired "
                       "by %s (threshold=%s). I'm forcing the state to freshness state (%s).",
                       self.service_description, self.host_name,
                       format_t_into_dhms_format(t_stale_by),
                       format_t_into_dhms_format(t_threshold),
                       self.freshness_state)

    def raise_notification_log_entry(self, notif, contact, host_ref):
        """Raise SERVICE NOTIFICATION entry (critical level)
        Format is : "SERVICE NOTIFICATION: *contact.get_name()*;*host_name*;*service_description*
                    ;*state*;*command.get_name()*;*output*"
        Example : "SERVICE NOTIFICATION: superadmin;server;Load;UP;notify-by-rss;no output"

        :param notif: notification object created by service alert
        :type notif: alignak.objects.notification.Notification
        :return: None
        """
        if not self.__class__.log_notifications:
            return

        log_level = 'info'
        command = notif.command_call
        if notif.type in ('DOWNTIMESTART', 'DOWNTIMEEND', 'DOWNTIMECANCELLED',
                          'CUSTOM', 'ACKNOWLEDGEMENT', 'FLAPPINGSTART',
                          'FLAPPINGSTOP', 'FLAPPINGDISABLED'):
            state = '%s (%s)' % (notif.type, self.state)
        else:
            state = self.state
            if self.state == 'WARNING':
                log_level = 'warning'
            if self.state == 'CRITICAL':
                log_level = 'error'

        brok = make_monitoring_log(
            log_level, "SERVICE NOTIFICATION: %s;%s;%s;%s;%s;%s" % (
                contact.get_name(),
                host_ref.get_name(), self.service_description, state,
                command.get_name(), self.output
            )
        )
        self.broks.append(brok)

    def raise_event_handler_log_entry(self, command):
        """Raise SERVICE EVENT HANDLER entry (critical level)
        Format is : "SERVICE EVENT HANDLER: *host_name*;*service_description*;*state*;*state_type*
                    ;*attempt*;*command.get_name()*"
        Example : "SERVICE EVENT HANDLER: server;Load;UP;HARD;1;notify-by-rss"

        :param command: Handler launched
        :type command: alignak.objects.command.Command
        :return: None
        """
        if not self.__class__.log_event_handlers:
            return

        log_level = 'info'
        if self.state == 'WARNING':
            log_level = 'warning'
        if self.state == 'CRITICAL':
            log_level = 'error'
        brok = make_monitoring_log(
            log_level, "SERVICE EVENT HANDLER: %s;%s;%s;%s;%s;%s" % (
                self.host_name, self.service_description,
                self.state, self.state_type,
                self.attempt, command.get_name()
            )
        )
        self.broks.append(brok)

    def raise_snapshot_log_entry(self, command):
        """Raise SERVICE SNAPSHOT entry (critical level)
        Format is : "SERVICE SNAPSHOT: *host_name*;*service_description*;*state*;*state_type*;
                    *attempt*;*command.get_name()*"
        Example : "SERVICE SNAPSHOT: server;Load;UP;HARD;1;notify-by-rss"

        :param command: Snapshot command launched
        :type command: alignak.objects.command.Command
        :return: None
        """
        if not self.__class__.log_snapshots:
            return

        log_level = 'info'
        if self.state == 'WARNING':
            log_level = 'warning'
        if self.state == 'CRITICAL':
            log_level = 'error'
        brok = make_monitoring_log(
            log_level, "SERVICE SNAPSHOT: %s;%s;%s;%s;%s;%s" % (
                self.host_name, self.service_description,
                self.state, self.state_type,
                self.attempt, command.get_name()
            )
        )
        self.broks.append(brok)

    def raise_flapping_start_log_entry(self, change_ratio, threshold):
        """Raise SERVICE FLAPPING ALERT START entry (critical level)
        Format is : "SERVICE FLAPPING ALERT: *host_name*;*service_description*;STARTED;
                     Service appears to have started
                     flapping (*change_ratio*% change >= *threshold*% threshold)"
        Example : "SERVICE FLAPPING ALERT: server;Load;STARTED;
                   Service appears to have started
                   flapping (50.6% change >= 50.0% threshold)"

        :param change_ratio: percent of changing state
        :param threshold: threshold (percent) to trigger this log entry
        :return: None
        """
        if not self.__class__.log_flappings:
            return

        brok = make_monitoring_log(
            'info', "SERVICE FLAPPING ALERT: %s;%s;STARTED; "
                    "Service appears to have started flapping "
                    "(%.1f%% change >= %.1f%% threshold)" %
                    (self.host_name, self.service_description, change_ratio, threshold)
        )
        self.broks.append(brok)

    def raise_flapping_stop_log_entry(self, change_ratio, threshold):
        """Raise SERVICE FLAPPING ALERT STOPPED entry (critical level)
        Format is : "SERVICE FLAPPING ALERT: *host_name*;*service_description*;STOPPED;
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
        if not self.__class__.log_flappings:
            return

        brok = make_monitoring_log(
            'info', "SERVICE FLAPPING ALERT: %s;%s;STOPPED; "
                    "Service appears to have stopped flapping "
                    "(%.1f%% change < %.1f%% threshold)" %
                    (self.host_name, self.service_description, change_ratio, threshold)
        )
        self.broks.append(brok)

    def raise_no_next_check_log_entry(self):
        """Raise no scheduled check entry (warning level)
        Format is : "I cannot schedule the check for the service '*get_name()*'
                    on host '*host_name*' because there is not future valid time"
        Example : "I cannot schedule the check for the service 'Load' on host 'Server'
                  because there is not future valid time"

        :return: None
        """
        logger.warning("I cannot schedule the check for the service '%s' on "
                       "host '%s' because there is not future valid time",
                       self.service_description, self.host_name)

    def raise_enter_downtime_log_entry(self):
        """Raise SERVICE DOWNTIME ALERT entry (critical level)
        Format is : "SERVICE DOWNTIME ALERT: *host_name*;*get_name()*;STARTED;
                    Service has entered a period of scheduled downtime"
        Example : "SERVICE DOWNTIME ALERT: test_host_0;Load;STARTED;
                   Service has entered a period of scheduled downtime"

        :return: None
        """
        brok = make_monitoring_log(
            'info', "SERVICE DOWNTIME ALERT: %s;%s;STARTED; "
                    "Service has entered a period of scheduled downtime" %
                    (self.host_name, self.service_description)
        )
        self.broks.append(brok)

    def raise_exit_downtime_log_entry(self):
        """Raise SERVICE DOWNTIME ALERT entry (critical level)
        Format is : "SERVICE DOWNTIME ALERT: *host_name*;*get_name()*;STOPPED;
                    Service has entered a period of scheduled downtime"
        Example : "SERVICE DOWNTIME ALERT: test_host_0;Load;STOPPED;
                   Service has entered a period of scheduled downtime"

        :return: None
        """
        brok = make_monitoring_log(
            'info', "SERVICE DOWNTIME ALERT: %s;%s;STOPPED; Service "
                    "has exited from a period of scheduled downtime" %
                    (self.host_name, self.service_description)
        )
        self.broks.append(brok)

    def raise_cancel_downtime_log_entry(self):
        """Raise SERVICE DOWNTIME ALERT entry (critical level)
        Format is : "SERVICE DOWNTIME ALERT: *host_name*;*get_name()*;CANCELLED;
                    Service has entered a period of scheduled downtime"
        Example : "SERVICE DOWNTIME ALERT: test_host_0;Load;CANCELLED;
                   Service has entered a period of scheduled downtime"

        :return: None
        """
        brok = make_monitoring_log(
            'info', "SERVICE DOWNTIME ALERT: %s;%s;CANCELLED; "
                    "Scheduled downtime for service has been cancelled." %
                    (self.host_name, self.service_description)
        )
        self.broks.append(brok)

    def manage_stalking(self, check):
        """Check if the service need stalking or not (immediate recheck)
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
        return not contact.want_service_notification(notifways, timeperiods, cdowntimes,
                                                     self.last_chk,
                                                     self.state, notif.type, self.business_impact,
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

    def get_snapshot_command(self):
        """Wrapper to get the name of the snapshot_command attribute

        :return: snapshot_command name
        :rtype: str
        """
        return self.snapshot_command.get_name()

    # pylint: disable=R0916
    def notification_is_blocked_by_item(self, notification_period, hosts, services,
                                        n_type, t_wished=None):
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
        host = hosts[self.host]
        if t_wished is None:
            t_wished = time.time()

        #  TODO
        # forced notification
        # pass if this is a custom notification

        # Block if notifications are program-wide disabled
        # Block if notifications are disabled for this service
        # Block if out of the notification period
        # Block if no notifications in the notification_options
        if not self.enable_notifications or \
                not self.notifications_enabled or \
                (notification_period is not None and not
                    notification_period.is_time_valid(t_wished)) or \
                'n' in self.notification_options:
            logger.debug("Service: %s, notification %s sending is blocked by globals",
                         self.get_name(), n_type)
            return True

        # Block if the current status is not in the notification_options w,u,c,r,f,s,x
        if n_type in ('PROBLEM', 'RECOVERY') and (
            self.state == 'UNKNOWN' and 'u' not in self.notification_options or
            self.state == 'WARNING' and 'w' not in self.notification_options or
            self.state == 'CRITICAL' and 'c' not in self.notification_options or
            self.state == 'OK' and 'r' not in self.notification_options or
            self.state == 'UNREACHABLE' and 'x' not in self.notification_options
        ):  # pylint: disable=R0911
            logger.debug("Service: %s, notification %s sending is blocked by options",
                         self.get_name(), n_type)
            return True
        if (n_type in ('FLAPPINGSTART', 'FLAPPINGSTOP', 'FLAPPINGDISABLED') and
                'f' not in self.notification_options):
            logger.debug("Service: %s, notification %s sending is blocked by options",
                         self.get_name(), n_type)
            return True
        if (n_type in ('DOWNTIMESTART', 'DOWNTIMEEND', 'DOWNTIMECANCELLED') and
                's' not in self.notification_options):
            logger.debug("Service: %s, notification %s sending is blocked by options",
                         self.get_name(), n_type)
            return True

        # Acknowledgements make no sense when the status is ok/up
        # Block if host is in a scheduled downtime
        if n_type == 'ACKNOWLEDGEMENT' and self.state == self.ok_up or \
                host.scheduled_downtime_depth > 0:
            logger.debug("Service: %s, notification %s sending is blocked by status",
                         self.get_name(), n_type)
            return True

        # When in downtime, only allow end-of-downtime notifications
        if self.scheduled_downtime_depth > 1 and n_type not in ('DOWNTIMEEND', 'DOWNTIMECANCELLED'):
            logger.debug("Service: %s, notification %s sending is blocked by downtime",
                         self.get_name(), n_type)
            return True

        # Block if in a scheduled downtime and a problem arises, or flapping event
        if self.scheduled_downtime_depth > 0 and n_type in \
                ('PROBLEM', 'RECOVERY', 'FLAPPINGSTART', 'FLAPPINGSTOP', 'FLAPPINGDISABLED'):
            logger.debug("Service: %s, notification %s sending is blocked by downtime",
                         self.get_name(), n_type)
            return True

        # Block if the status is SOFT
        # Block if the problem has already been acknowledged
        # Block if flapping
        # Block if host is down
        if self.state_type == 'SOFT' and n_type == 'PROBLEM' or \
                self.problem_has_been_acknowledged and n_type != 'ACKNOWLEDGEMENT' or \
                self.is_flapping and n_type not in ('FLAPPINGSTART',
                                                    'FLAPPINGSTOP',
                                                    'FLAPPINGDISABLED') or \
                host.state != host.ok_up:
            logger.debug("Service: %s, notification %s sending is blocked by soft state, "
                         "acknowledged, flapping or host DOWN", self.get_name(), n_type)
            return True

        # Block if business rule smart notifications is enabled and all its
        # children have been acknowledged or are under downtime.
        if self.got_business_rule is True \
                and self.business_rule_smart_notifications is True \
                and self.business_rule_notification_is_blocked(hosts, services) is True \
                and n_type == 'PROBLEM':
            logger.debug("Service: %s, notification %s sending is blocked by business rules",
                         self.get_name(), n_type)
            return True

        return False

    def get_short_status(self, hosts, services):
        """Get the short status of this host

        :return: "O", "W", "C", "U', or "n/a" based on service state_id or business_rule state
        :rtype: str
        """
        mapping = {
            0: "O",
            1: "W",
            2: "C",
            3: "U",
            4: "N",
        }
        if self.got_business_rule:
            return mapping.get(self.business_rule.get_state(hosts, services), "n/a")
        else:
            return mapping.get(self.state_id, "n/a")

    def get_status(self, hosts, services):
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

    def register_service_dependencies(self, servicedependencies):
        """
        Registers a service dependencies.

        :param servicedependencies: The servicedependencies container
        :type servicedependencies:
        :return: None
        """
        # We explode service_dependencies into Servicedependency
        # We just create serviceDep with goods values (as STRING!),
        # the link pass will be done after
        sdeps = [d.strip() for d in getattr(self, "service_dependencies", [])]

        # %2=0 are for hosts, !=0 are for service_description
        i = 0
        host_name = ''
        for elt in sdeps:
            if i % 2 == 0:  # host
                host_name = elt
            else:  # description
                desc = elt
                # we can register it (service) (depend on) -> (host_name, desc)
                # If we do not have enough data for service, it'service no use
                if hasattr(self, 'service_description') and hasattr(self, 'host_name'):
                    if not host_name:
                        host_name = self.host_name
                    servicedependencies.add_service_dependency(self.host_name,
                                                               self.service_description,
                                                               host_name, desc)
            i += 1


class Services(SchedulingItems):
    """Class for the services lists. It's mainly for configuration

    """
    inner_class = Service

    def add_item(self, item, index=True):
        """
        Adds a service into the `items` container.

        This specific implementation checks that the service is defined with correct attributes:
        `host_name` or `hostgroup_name` and `service_description`.

        Note that Services should not be indexed before their host_name/service_description
        is known. when this function is called they should not!

        :param item: The item to add
        :type item:
        :param index: Flag indicating if the item should be indexed
        :type index: bool
        :return: None
        """
        host_name = getattr(item, 'host_name', '')
        hostgroup_name = getattr(item, 'hostgroup_name', '')
        service_description = getattr(item, 'service_description', '')

        if not host_name and not hostgroup_name:
            # Only set a warning because the missing fields may be in the template
            item.add_error("a %s has been defined without host_name nor hostgroup_name, from: %s" %
                           (self.inner_class.my_type, item.imported_from))
        if not service_description:
            # Only set a warning because the missing fields may be in the template
            item.add_error("a %s has been defined without service_description, from: %s" %
                           (self.inner_class.my_type, item.imported_from), is_warning=True)

        if index is True:
            warnings.warn("Services are indexed on creation. This is not a prudent solution "
                          "because services are not yet exploded with hosts, hostgroups, ...",
                          DeprecationWarning, stacklevel=2)
            item = self.index_item(item)

        self.items[item.uuid] = item

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

    def find_srv_by_name_and_hostname(self, host_name, service_description):
        """Get a specific service based on a host_name and service_description

        :param host_name: host name linked to needed service
        :type host_name: str
        :param service_description:  service name we need
        :type service_description: str
        :return: the service found or None
        :rtype: alignak.objects.service.Service
        """
        return self.find_by_name("%s/%s" % (host_name, service_description))

    def linkify(self, hosts, commands, timeperiods, contacts,  # pylint: disable=R0913
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
        self.linkify_service_by_host(hosts)
        self.linkify_service_by_servicegroup(servicegroups)
        self.linkify_one_command_with_commands(commands, 'check_command')
        self.linkify_one_command_with_commands(commands, 'event_handler')
        self.linkify_one_command_with_commands(commands, 'snapshot_command')
        self.linkify_with_contacts(contacts)
        self.linkify_with_resultmodulations(resultmodulations)
        self.linkify_with_business_impact_modulations(businessimpactmodulations)
        # WARNING: all escalations will not be linked here
        # (only the escalations, not serviceescalations or hostescalations).
        # This last one will be linked in escalations linkify.
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
        overriding_regexp = re.compile(r'^([^,]+),([^\s]+)\s+(.*)$')

        # We're only looking for hosts having service overrides defined
        overriding_hosts = [h for h in hosts if getattr(h, 'service_overrides', None)]
        for host in overriding_hosts:
            if isinstance(host.service_overrides, list):
                service_overrides = host.service_overrides
            else:
                service_overrides = [host.service_overrides]

            for overriden_services in service_overrides:
                # Checks service override syntax
                match = overriding_regexp.search(overriden_services)
                if match is None:
                    host.add_error("invalid service override syntax: %s"
                                   % overriden_services)
                    continue

                service_description, prop, value = match.groups()
                # Search for corresponding service
                service = self.find_srv_by_name_and_hostname(host.get_name(), service_description)
                if service is None:
                    host.add_error("trying to override property '%s' on service '%s' but this "
                                   "service is unknown for this host" % (prop, service_description))
                    continue

                # Check if overriding is allowed
                excludes = ['host_name', 'service_description', 'use',
                            'servicegroups', 'trigger_name']
                if prop in excludes:
                    host.add_error("trying to override '%s', overriding forbidden property "
                                   "for service '%s'" % (prop, service_description))
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

    def linkify_service_by_host(self, hosts):
        """Link services with their parent host

        :param hosts: Hosts to look for simple host
        :type hosts: alignak.objects.host.Hosts
        :return: None
        """
        for service in self:
            logger.debug("Linkify service / host: '%s'", service)
            # If we do not have a host_name, we set it as
            # a template element to delete. (like Nagios)
            if getattr(service, 'host_name', None) is None:
                service.host = None
                service.realm = None
                continue

            # The new member list, with uuid
            host = hosts.find_by_name(service.host_name)
            # Let the host know we are his service
            if host is not None:
                service.host = host.uuid
                service.realm = host.realm
                host.add_service_link(service.uuid)
            else:
                service.add_error("the service '%s' got an unknown host_name" %
                                  (service.get_name()), is_warning=True)

    def linkify_service_by_servicegroup(self, servicegroups):
        """Link services with servicegroups

        :param servicegroups: Servicegroups
        :type servicegroups: alignak.objects.servicegroup.Servicegroups
        :return: None
        """
        for service in self:
            new_servicegroups = []
            if hasattr(service, 'servicegroups') and service.servicegroups:
                # Because services groups can be created because a service references
                # a not existing group or because a group exists in the configuration,
                # we can have an uuid or a name...
                for servicegroup_name in service.servicegroups:
                    if servicegroup_name in servicegroups:
                        # We got an uuid and already linked the item with its group
                        new_servicegroups.append(servicegroup_name)
                        continue

                    servicegroup = servicegroups.find_by_name(servicegroup_name)
                    if servicegroup is not None:
                        new_servicegroups.append(servicegroup.uuid)
                    else:
                        service.add_error("the servicegroup '%s' of the service '%s' is unknown" %
                                          (servicegroup_name, service.get_full_name()))

            service.servicegroups = new_servicegroups

    def apply_implicit_inheritance(self, hosts):
        """Apply implicit inheritance for special properties:

            * contacts, contact_groups, notification_interval , notification_period,
            * resultmodulations, business_impact_modulations,
            * escalations, poller_tag, reactionner_tag, check_period,
            * business_impact, maintenance_period

        So service will update its corresponding property from their host

        :param hosts: hosts list needed to look for a simple host
        :type hosts: alignak.objects.host.Hosts
        :return: None
        """
        for prop in ('contacts', 'contact_groups', 'notification_interval', 'notification_period',
                     'resultmodulations', 'business_impact_modulations',
                     'escalations', 'poller_tag', 'reactionner_tag', 'check_period',
                     'business_impact', 'maintenance_period'):
            for service in self:
                if not getattr(service, prop, None) and hasattr(service, 'host_name'):
                    host = hosts.find_by_name(service.host_name)
                    if host is not None and getattr(host, prop, None):
                        setattr(service, prop, getattr(host, prop))

    def apply_dependencies(self, hosts):
        """Wrapper to loop over services and call Service.fill_daddy_dependency()

        :return: None
        """
        for service in self:
            if service.host and service.host_dependency_enabled:
                host = hosts[service.host]
                if host.active_checks_enabled:
                    service.act_depend_of.append(
                        (service.host, ['d', 'x', 's', 'f'], '', True)
                    )
                    host.act_depend_of_me.append(
                        (service.uuid, ['d', 'x', 's', 'f'], '', True)
                    )
                    host.child_dependencies.add(service.uuid)
                    service.parent_dependencies.add(service.host)

    def clean(self):
        """Remove services without host object linked to

        :return: None
        """
        to_del = []
        for service in self:
            if not service.host:
                to_del.append(service.uuid)
        for service_uuid in to_del:
            del self.items[service_uuid]

    def explode_services_from_hosts(self, hosts, service, hostnames):
        """
        Explodes a service based on a list of hosts.

        :param hosts: The hosts container
        :type hosts:
        :param service: The base service to explode
        :type service:
        :param hostnames:  The host_name list to explode service on
        :type hostnames: str
        :return: None
        """
        # the list of our host_names if more than 1
        duplicate_for_hosts = []
        # the list of !host_name so we remove them after
        not_hosts = []
        for host_name in hostnames:
            host_name = host_name.strip()

            # If the name begins with a !, we put it in the NOT list
            if host_name.startswith('!'):
                not_hosts.append(host_name[1:])
            else:
                duplicate_for_hosts.append(host_name)

        # remove duplicate items from duplicate_for_hosts:
        duplicate_for_hosts = list(set(duplicate_for_hosts))

        # Ok now we clean the duplicate_for_hosts with all hosts of the NOT list
        for host_name in not_hosts:
            try:
                duplicate_for_hosts.remove(host_name)
            except IndexError:
                pass

        # Now we duplicate the service for all host_names
        for host_name in duplicate_for_hosts:
            host = hosts.find_by_name(host_name)
            if host is None:
                service.add_error("The hostname %s is unknown for the service %s!" %
                                  (host_name, service.get_name()))
                continue
            if host.is_excluded_for(service):
                continue
            new_service = service.copy()
            new_service.host_name = host_name
            self.add_item(new_service, index=True)

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

        # Creates real service instance
        new_service = service.copy()
        new_service.host_name = host_name
        new_service.register = 1
        self.add_item(new_service, index=True)
        return new_service

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
        host_name = getattr(service, "host_name", None)
        if not host_name:
            return

        # Now really create the services
        if is_complex_expr(host_name):
            hostnames = self.evaluate_hostgroup_expression(host_name.strip(), hosts,
                                                           hosts.templates, look_in='templates')
            for name in hostnames:
                self._local_create_service(hosts, name, service)
        else:
            hostnames = [n.strip() for n in host_name.split(',') if n.strip()]
            for host_name in hostnames:
                for name in hosts.find_hosts_that_use_template(host_name):
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
            err = 'Error: The hostname %s is unknown for the service %s!' % \
                  (hname, service.get_name())
            service.configuration_errors.append(err)
            return

        # Duplicate services
        for new_s in service.duplicate(host):
            if host.is_excluded_for(new_s):
                continue
            # Adds concrete instance
            self.add_item(new_s, index=True)

    def explode(self, hosts, hostgroups, contactgroups, servicegroups, servicedependencies):
        """
        Explodes services, from host, hostgroups, contactgroups, servicegroups and dependencies.

        We create new service if necessary (host groups and co)

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
        :return: None
        """
        logger.debug("Before services explosion")
        logger.debug(" - services templates: %s", self.templates)
        logger.debug(" - servics index: %s", self.name_to_item)
        logger.debug(" - services templates index: %s", self.name_to_template)

        # Because we are adding services in the dictionary, we can't just loop in it
        itemkeys = self.items.keys()
        for service_uuid in itemkeys:
            logger.debug(" - exploding service: %s", service_uuid)
            service = self.items[service_uuid]
            # items::explode_host_groups_into_hosts
            # Set all hosts from our hostgroup_name into our host_name property
            self.explode_host_groups_into_hosts(service, hosts, hostgroups)

            # items::explode_contact_groups_into_contacts
            # Set all contacts from our contact_groups into our contact property
            self.explode_contact_groups_into_contacts(service, contactgroups)

            hnames = getattr(service, "host_name", '')
            hnames = list(set([n.strip() for n in hnames.split(',') if n.strip()]))

            # We will duplicate if we have multiple host_name
            # or if we are a template (so a clean service)
            if len(hnames) == 1:
                # Now we can index our service because we have
                # a couple (host_name / service_description)!
                self.index_item(service)
            else:
                if len(hnames) >= 2:
                    self.explode_services_from_hosts(hosts, service, hnames)
                # Delete the current source service
                self.remove_item(service)

        for template in self.templates.values():
            self.explode_contact_groups_into_contacts(template, contactgroups)
            self.explode_services_from_templates(hosts, template)

        # Explode services that have a duplicate_foreach clause
        duplicates = [service.uuid for service in self if getattr(service, 'duplicate_foreach', '')]
        for service_id in duplicates:
            service = self.items[service_id]
            self.explode_services_duplicates(hosts, service)
            if not service.configuration_errors:
                self.remove_item(service)

        to_remove = []
        for service in self:
            host = hosts.find_by_name(service.host_name)
            if host and host.is_excluded_for(service):
                to_remove.append(service)
        for service in to_remove:
            self.remove_item(service)

        # Servicegroups property need to be fulfill for got the information
        # And then just register to this service_group
        for service in self:
            # Register service in the servicegroups
            if getattr(service, 'servicegroups', None) is not None:
                for servicegroup in service.servicegroups:
                    servicegroups.add_group_member(service, servicegroup)

            # Register service dependencies
            service.register_service_dependencies(servicedependencies)

    def fill_predictable_missing_parameters(self):
        """Loop on services and call Service.fill_predictable_missing_parameters()

        :return: None
        """
        for service in self:
            service.fill_predictable_missing_parameters()
