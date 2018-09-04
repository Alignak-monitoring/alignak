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
import os
import logging
import time
import re

from alignak.objects.schedulingitem import SchedulingItem, SchedulingItems

from alignak.autoslots import AutoSlots
from alignak.util import (
    strip_and_uniq,
    generate_key_value_sequences,
    is_complex_expr,
    KeyValueSyntaxError)
from alignak.property import BoolProp, IntegerProp, StringProp, ListProp, CharProp
from alignak.log import make_monitoring_log

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Service(SchedulingItem):
    """Service class implements monitoring concepts for service.
    For example it defines parents, check_interval, check_command  etc.
    """
    # AutoSlots create the __slots__ with properties and
    # running_properties names
    __metaclass__ = AutoSlots

    # The host and service do not have the same 0 value, now yes :)
    ok_up = u'OK'
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
        'alias':
            StringProp(default=u'', fill_brok=['full_status']),
        'host_name':
            StringProp(fill_brok=['full_status', 'check_result', 'next_schedule'], special=True),
        'hostgroup_name':
            StringProp(default='', fill_brok=['full_status'], merging='join', special=True),
        'service_description':
            StringProp(fill_brok=['full_status', 'check_result', 'next_schedule']),
        'servicegroups':
            ListProp(default=[], fill_brok=['full_status'], merging='join'),
        'is_volatile':
            BoolProp(default=False, fill_brok=['full_status']),
        'check_command':
            StringProp(fill_brok=['full_status']),
        'flap_detection_options':
            ListProp(default=['o', 'w', 'c', 'u', 'x'], fill_brok=['full_status'],
                     split_on_comma=True),
        'notification_options':
            ListProp(default=['w', 'u', 'c', 'r', 'f', 's', 'x'],
                     fill_brok=['full_status'], split_on_comma=True),
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
            ListProp(default=[], merging='join', split_on_comma=True, keep_empty=True),

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
            StringProp(default=u'OK',
                       fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_ok':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_warning':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_critical':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_unknown':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_unreachable':
            IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'host':
            StringProp(default=None),
        'state_before_hard_unknown_reach_phase': StringProp(default=u'OK', retention=True),
    })

    special_properties = (
        'service_description'
    )

    # Mapping between Macros and properties (can be prop or a function)
    macros = SchedulingItem.macros.copy()
    macros.update({
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
        'SERVICEGROUPNAME':       ('get_groupname', ['servicegroups']),
        'SERVICEGROUPNAMES':      ('get_groupnames', ['servicegroups']),
        'LASTSERVICECHECK':       'last_chk',
        'LASTSERVICESTATECHANGE': 'last_state_change',
        'LASTSERVICEOK':          'last_time_ok',
        'LASTSERVICEWARNING':     'last_time_warning',
        'LASTSERVICEUNKNOWN':     'last_time_unknown',
        'LASTSERVICEUNREACHABLE': 'last_time_unreachable',
        'LASTSERVICECRITICAL':    'last_time_critical',
        'SERVICEOUTPUT':          'output',
        'LONGSERVICEOUTPUT':      'long_output',
        'SERVICEPERFDATA':        'perf_data',
        'LASTSERVICEPERFDATA':    'last_perf_data',
        'SERVICECHECKCOMMAND':    'get_check_command',
        'SERVICESNAPSHOTCOMMAND': 'get_snapshot_command',
        'SERVICEACKAUTHOR':       'get_ack_author_name',
        'SERVICEACKAUTHORNAME':   'get_ack_author_name',
        'SERVICEACKAUTHORALIAS':  'get_ack_author_name',
        'SERVICEACKCOMMENT':      'get_ack_comment',
        'SERVICEACTIONURL':       'action_url',
        'SERVICENOTESURL':        'notes_url',
        'SERVICENOTES':           'notes',
        'SERVICEBUSINESSIMPACT':  'business_impact',
    })

    # This tab is used to transform old parameters name into new ones
    # so from Nagios2 format, to Nagios3 ones.
    # Or Alignak deprecated names like criticity
    old_properties = SchedulingItem.old_properties.copy()
    old_properties.update({
        'hostgroup':    'hostgroup_name',
        'hostgroups':    'hostgroup_name',
    })

    def __str__(self):  # pragma: no cover
        return '<Service %s, uuid=%s, %s (%s), use: %s />' \
               % (self.get_full_name(), self.uuid, self.state, self.state_type,
                  getattr(self, 'use', None))
    __repr__ = __str__

    @property
    def realm(self):
        """Get the service realm... indeed it is the service's host one!"""
        if not getattr(self, 'host', None):
            return None
        return self.host.realm

    @property
    def overall_state_id(self):
        """Get the service overall state.

        The service overall state identifier is the service status including:
        - the monitored state
        - the acknowledged state
        - the downtime state

        The overall state is (prioritized):
        - a service is not monitored (5)
        - a service critical or unreachable (4)
        - a service warning or unknown (3)
        - a service downtimed (2)
        - a service acknowledged (1)
        - a service ok (0)

        *Note* that services in unknown state are considered as warning, and unreachable ones
        are considered as critical!

        Also note that the service state is considered only for HARD state type!

        """
        overall_state = 0
        if not self.monitored:
            overall_state = 5
        elif self.acknowledged:
            overall_state = 1
        elif self.downtimed:
            overall_state = 2
        elif self.state_type == 'HARD':
            if self.state == 'WARNING':
                overall_state = 3
            elif self.state == 'CRITICAL':
                overall_state = 4
            elif self.state == 'UNKNOWN':
                overall_state = 3
            elif self.state == 'UNREACHABLE':
                overall_state = 4

        return overall_state

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
            self.state = u'WARNING'
        elif self.initial_state == 'u':
            self.state = u'UNKNOWN'
        elif self.initial_state == 'c':
            self.state = u'CRITICAL'
        elif self.initial_state == 'x':
            self.state = u'UNREACHABLE'

    @property
    def unique_key(self):  # actually only used for (un)indexitem() via name_property..
        """Unique key for this service

        :return: Tuple with host_name and service_description
        :rtype: tuple
        """
        return self.host_name, self.service_description

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

    def get_full_name(self):
        """Get the full name for debugging (host_name/service_description)

        :return: service full name
        :rtype: str
        """
        if self.is_tpl():
            return "tpl-%s/%s" % (getattr(self, 'host_name', 'XxX'), self.name)
        if hasattr(self, 'host_name') and hasattr(self, 'service_description'):
            return "%s/%s" % (self.host_name, self.service_description)
        return 'UNKNOWN-SERVICE'

    def get_servicegroups(self):
        """Accessor to servicegroups attribute

        :return: servicegroup list object of host
        :rtype: list
        """
        return self.servicegroups

    def get_groupnames(self, sgs):
        """Get servicegroups list

        :return: comma separated list of servicegroups
        :rtype: str
        """
        return ','.join([sgs[sg].get_name() for sg in self.servicegroups])

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
        state = True
        cls = self.__class__

        hname = getattr(self, 'host_name', '')
        hgname = getattr(self, 'hostgroup_name', '')
        sdesc = getattr(self, 'service_description', '')

        if not sdesc:
            self.add_error("a %s has been defined without service_description, from: %s"
                           % (cls, self.imported_from))
        elif not hname:
            self.add_error("[%s::%s] not bound to any host."
                           % (self.my_type, self.get_name()))
        elif not hname and not hgname:
            self.add_error("a %s has been defined without host_name nor "
                           "hostgroup_name, from: %s" % (self.my_type, self.imported_from))
        elif self.host is None:
            self.add_error("[%s::%s] unknown host_name '%s'"
                           % (self.my_type, self.get_name(), self.host_name))

        # Set display_name if needed
        if not getattr(self, 'display_name', ''):
            self.display_name = "%s/%s" % (hname, sdesc)

        for char in cls.illegal_object_name_chars:
            if char not in self.service_description:
                continue

            self.add_error("[%s::%s] service_description got an illegal character: %s"
                           % (self.my_type, self.get_name(), char))

        return super(Service, self).is_correct() and state

    def duplicate(self, host):
        # pylint: disable=too-many-locals
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
            host.add_error(err)
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
        """Set the state in UP, WARNING, CRITICAL, UNKNOWN or UNREACHABLE
        according to the status of a check result.

        :param status: integer between 0 and 4
        :type status: int
        :return: None
        """
        now = time.time()

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

        # The last times are kept as integer values rather than float... no need for ms!
        if status == 0:
            self.state = u'OK'
            self.state_id = 0
            self.last_time_ok = int(self.last_state_update)
            # self.last_time_ok = self.last_state_update
            state_code = 'o'
        elif status == 1:
            self.state = u'WARNING'
            self.state_id = 1
            self.last_time_warning = int(self.last_state_update)
            # self.last_time_warning = self.last_state_update
            state_code = 'w'
        elif status == 2:
            self.state = u'CRITICAL'
            self.state_id = 2
            self.last_time_critical = int(self.last_state_update)
            # self.last_time_critical = self.last_state_update
            state_code = 'c'
        elif status == 3:
            self.state = u'UNKNOWN'
            self.state_id = 3
            self.last_time_unknown = int(self.last_state_update)
            # self.last_time_unknown = self.last_state_update
            state_code = 'u'
        elif status == 4:
            self.state = u'UNREACHABLE'
            self.state_id = 4
            self.last_time_unreachable = int(self.last_state_update)
            # self.last_time_unreachable = self.last_state_update
            state_code = 'x'
        else:
            self.state = u'CRITICAL'  # exit code UNDETERMINED
            self.state_id = 2
            self.last_time_critical = int(self.last_state_update)
            # self.last_time_critical = self.last_state_update
            state_code = 'c'

        if state_code in self.flap_detection_options:
            self.add_flapping_change(self.state != self.last_state)
            # Now we add a value, we update the is_flapping prop
            self.update_flapping(notif_period, hosts, services)
        if self.state != self.last_state:
            self.last_state_change = self.last_state_update

        self.duration_sec = now - self.last_state_change

    def is_state(self, status):
        # pylint: disable=too-many-return-statements
        """Return True if status match the current service status

        :param status: status to compare ( "o", "c", "w", "u", "x"). Usually comes from config files
        :type status: str
        :return: True if status <=> self.status, otherwise False
        :rtype: bool
        """
        if status == self.state:
            return True
        # Now low status
        if status == 'o' and self.state == u'OK':
            return True
        if status == 'c' and self.state == u'CRITICAL':
            return True
        if status == 'w' and self.state == u'WARNING':
            return True
        if status == 'u' and self.state == u'UNKNOWN':
            return True
        if status == 'x' and self.state == u'UNREACHABLE':
            return True
        return False

    def last_time_non_ok_or_up(self):
        """Get the last time the service was in a non-OK state

        :return: the nearest last time the service was not ok
        :rtype: int
        """
        non_ok_times = [x for x in [self.last_time_warning,
                                    self.last_time_critical,
                                    self.last_time_unknown]
                        if x > self.last_time_ok]
        if not non_ok_times:
            last_time_non_ok = 0  # todo: program_start would be better?
        else:
            last_time_non_ok = min(non_ok_times)
        return last_time_non_ok

    def raise_check_result(self):
        """Raise ACTIVE CHECK RESULT entry
        Example : "ACTIVE SERVICE CHECK: server;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        if not self.__class__.log_active_checks:
            return

        log_level = 'info'
        if self.state in [u'WARNING', u'UNREACHABLE']:
            log_level = 'warning'
        elif self.state == u'CRITICAL':
            log_level = 'error'
        brok = make_monitoring_log(
            log_level, 'ACTIVE SERVICE CHECK: %s;%s;%s;%d;%s' % (self.host_name, self.get_name(),
                                                                 self.state, self.attempt,
                                                                 self.output)
        )
        self.broks.append(brok)

    def raise_alert_log_entry(self):
        """Raise SERVICE ALERT entry
        Format is : "SERVICE ALERT: *host.get_name()*;*get_name()*;*state*;*state_type*;*attempt*
                    ;*output*"
        Example : "SERVICE ALERT: server;Load;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        if self.__class__.log_alerts:
            log_level = 'info'
            if self.state == 'WARNING':
                log_level = 'warning'
            if self.state == 'CRITICAL':
                log_level = 'error'
            brok = make_monitoring_log(
                log_level, 'SERVICE ALERT: %s;%s;%s;%s;%d;%s' % (
                    self.host_name, self.get_name(),
                    self.state, self.state_type,
                    self.attempt, self.output
                )
            )
            self.broks.append(brok)

        if 'ALIGNAK_LOG_ALERTS' in os.environ:
            if os.environ['ALIGNAK_LOG_ALERTS'] == 'WARNING':
                logger.warning('SERVICE ALERT: %s;%s;%s;%s;%d;%s', self.host_name, self.get_name(),
                               self.state, self.state_type, self.attempt, self.output)
            else:
                logger.info('SERVICE ALERT: %s;%s;%s;%s;%d;%s', self.host_name, self.get_name(),
                            self.state, self.state_type, self.attempt, self.output)

    def raise_initial_state(self):
        """Raise SERVICE HOST ALERT entry (info level)
        Format is : "SERVICE HOST STATE: *host.get_name()*;*get_name()*;*state*;*state_type*
                    ;*attempt*;*output*"
        Example : "SERVICE HOST STATE: server;Load;DOWN;HARD;1;I don't know what to say..."

        :return: None
        """
        if not self.__class__.log_initial_states:
            return

        log_level = 'info'
        if self.state in ['WARNING', 'UNREACHABLE']:
            log_level = 'warning'
        if self.state in ['CRITICAL', 'UNKNOWN']:
            log_level = 'error'
        brok = make_monitoring_log(
            log_level, 'CURRENT SERVICE STATE: %s;%s;%s;%s;%d;%s' % (
                self.host_name, self.get_name(),
                self.state, self.state_type,
                self.attempt, self.output
            )
        )
        self.broks.append(brok)

    def raise_notification_log_entry(self, notif, contact, host_ref):
        """Raise SERVICE NOTIFICATION entry (critical level)
        Format is : "SERVICE NOTIFICATION: *contact.get_name()*;*host_name*;*self.get_name()*
                    ;*state*;*command.get_name()*;*output*"
        Example : "SERVICE NOTIFICATION: superadmin;server;Load;UP;notify-by-rss;no output"

        :param notif: notification object created by service alert
        :type notif: alignak.objects.notification.Notification
        :return: None
        """
        if self.__class__.log_notifications:
            log_level = 'info'
            command = notif.command_call
            if notif.type in [u'DOWNTIMESTART', u'DOWNTIMEEND', u'DOWNTIMECANCELLED',
                              u'CUSTOM', u'ACKNOWLEDGEMENT',
                              u'FLAPPINGSTART', u'FLAPPINGSTOP', u'FLAPPINGDISABLED']:
                state = '%s (%s)' % (notif.type, self.state)
            else:
                state = self.state
                if self.state == 'WARNING':
                    log_level = 'warning'
                if self.state == 'CRITICAL':
                    log_level = 'error'

            brok = make_monitoring_log(
                log_level, "SERVICE NOTIFICATION: %s;%s;%s;%s;%s;%s;%s" % (
                    contact.get_name(), host_ref.get_name(), self.get_name(), state,
                    notif.notif_nb, command.get_name(), self.output
                )
            )
            self.broks.append(brok)

        if 'ALIGNAK_LOG_NOTIFICATIONS' in os.environ:
            if os.environ['ALIGNAK_LOG_NOTIFICATIONS'] == 'WARNING':
                logger.warning("SERVICE NOTIFICATION: %s;%s;%s;%s;%s;%s;%s",
                               contact.get_name(), host_ref.get_name(), self.get_name(), state,
                               notif.notif_nb, command.get_name(), self.output)
            else:
                logger.info("SERVICE NOTIFICATION: %s;%s;%s;%s;%s;%s;%s",
                            contact.get_name(), host_ref.get_name(), self.get_name(), state,
                            notif.notif_nb, command.get_name(), self.output)

    def raise_event_handler_log_entry(self, command):
        """Raise SERVICE EVENT HANDLER entry (critical level)
        Format is : "SERVICE EVENT HANDLER: *host_name*;*self.get_name()*;*state*;*state_type*
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
                self.host_name, self.get_name(),
                self.state, self.state_type,
                self.attempt, command.get_name()
            )
        )
        self.broks.append(brok)

    def raise_snapshot_log_entry(self, command):
        """Raise SERVICE SNAPSHOT entry (critical level)
        Format is : "SERVICE SNAPSHOT: *host_name*;*self.get_name()*;*state*;*state_type*;
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
                self.host_name, self.get_name(),
                self.state, self.state_type,
                self.attempt, command.get_name()
            )
        )
        self.broks.append(brok)

    def raise_flapping_start_log_entry(self, change_ratio, threshold):
        """Raise SERVICE FLAPPING ALERT START entry (critical level)
        Format is : "SERVICE FLAPPING ALERT: *host_name*;*self.get_name()*;STARTED;
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
            'info',
            "SERVICE FLAPPING ALERT: %s;%s;STARTED; Service appears to have "
            "started flapping (%.1f%% change >= %.1f%% threshold)"
            % (self.host_name, self.get_name(), change_ratio, threshold)
        )
        self.broks.append(brok)

    def raise_flapping_stop_log_entry(self, change_ratio, threshold):
        """Raise SERVICE FLAPPING ALERT STOPPED entry (critical level)
        Format is : "SERVICE FLAPPING ALERT: *host_name*;*self.get_name()*;STOPPED;
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
            'info',
            "SERVICE FLAPPING ALERT: %s;%s;STOPPED; Service appears to have "
            "stopped flapping (%.1f%% change < %.1f%% threshold)"
            % (self.host_name, self.get_name(), change_ratio, threshold)
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
                       self.get_name(), self.host_name)

    def raise_acknowledge_log_entry(self):
        """Raise SERVICE ACKNOWLEDGE STARTED entry (critical level)

        :return: None
        """
        if not self.__class__.log_acknowledgements:
            return

        brok = make_monitoring_log(
            'info',
            "SERVICE ACKNOWLEDGE ALERT: %s;%s;STARTED; Service problem has been acknowledged"
            % (self.host_name, self.get_name())
        )
        self.broks.append(brok)

    def raise_unacknowledge_log_entry(self):
        """Raise SERVICE ACKNOWLEDGE STOPPED entry (critical level)

        :return: None
        """
        if not self.__class__.log_acknowledgements:
            return

        brok = make_monitoring_log(
            'info',
            "SERVICE ACKNOWLEDGE ALERT: %s;%s;EXPIRED; Service problem acknowledge expired"
            % (self.host_name, self.get_name())
        )
        self.broks.append(brok)

    def raise_enter_downtime_log_entry(self):
        """Raise SERVICE DOWNTIME ALERT entry (critical level)
        Format is : "SERVICE DOWNTIME ALERT: *host_name*;*get_name()*;STARTED;
                    Service has entered a period of scheduled downtime"
        Example : "SERVICE DOWNTIME ALERT: test_host_0;Load;STARTED;
                   Service has entered a period of scheduled downtime"

        :return: None
        """
        if not self.__class__.log_downtimes:
            return

        brok = make_monitoring_log(
            'info',
            "SERVICE DOWNTIME ALERT: %s;%s;STARTED; "
            "Service has entered a period of scheduled downtime"
            % (self.host_name, self.get_name())
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
        if not self.__class__.log_downtimes:
            return

        brok = make_monitoring_log(
            'info',
            "SERVICE DOWNTIME ALERT: %s;%s;STOPPED; Service "
            "has exited from a period of scheduled downtime"
            % (self.host_name, self.get_name())
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
        if not self.__class__.log_downtimes:
            return

        brok = make_monitoring_log(
            'info',
            "SERVICE DOWNTIME ALERT: %s;%s;CANCELLED; "
            "Scheduled downtime for service has been cancelled."
            % (self.host_name, self.get_name())
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
        if check.status == u'waitconsume':
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

    def notification_is_blocked_by_contact(self, notifways, timeperiods, notif, contact):
        """Check if the notification is blocked by this contact.

        :param notifways: concerned notification ways
        :type notifways: alignak.objects.notificationway.NotificationWays
        :param timeperiods: concerned timeperiods
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param notif: notification created earlier
        :type notif: alignak.notification.Notification
        :param contact: contact we want to notify
        :type contact: alignak.objects.contact.Contact
        :return: True if the notification is blocked, False otherwise
        :rtype: bool
        """
        return not contact.want_service_notification(notifways, timeperiods,
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
    def is_blocking_notifications(self, notification_period, hosts, services, n_type, t_wished):
        # pylint: disable=too-many-return-statements
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
        TODO: Refactor this, a lot of code duplication with Host.is_blocking_notifications
        """
        logger.debug("Checking if a service %s (%s) notification is blocked...",
                     self.get_full_name(), self.state)
        host = hosts[self.host]
        if t_wished is None:
            t_wished = time.time()

        #  TODO
        # forced notification
        # pass if this is a custom notification

        # Block if notifications are program-wide disabled
        # Block if notifications are disabled for this service
        # Block if the current status is in the notification_options w,u,c,r,f,s
        if not self.enable_notifications or \
                not self.notifications_enabled or \
                'n' in self.notification_options:
            logger.debug("Service: %s, notification %s sending is blocked by configuration",
                         self.get_name(), n_type)
            return True

        # Does the notification period allow sending out this notification?
        if notification_period is not None and not notification_period.is_time_valid(t_wished):
            logger.debug("Service: %s, notification %s sending is blocked by globals",
                         self.get_name(), n_type)
            return True

        if n_type in (u'PROBLEM', u'RECOVERY') and (
                self.state == u'UNKNOWN' and 'u' not in self.notification_options or
                self.state == u'WARNING' and 'w' not in self.notification_options or
                self.state == u'CRITICAL' and 'c' not in self.notification_options or
                self.state == u'OK' and 'r' not in self.notification_options or
                self.state == u'UNREACHABLE' and 'x' not in self.notification_options):
            logger.debug("Service: %s, notification %s sending is blocked by options: %s",
                         self.get_name(), n_type, self.notification_options)
            return True

        if (n_type in [u'FLAPPINGSTART', u'FLAPPINGSTOP', u'FLAPPINGDISABLED'] and
                'f' not in self.notification_options):
            logger.debug("Service: %s, notification %s sending is blocked by options: %s",
                         n_type, self.get_full_name(), self.notification_options)
            return True
        if (n_type in [u'DOWNTIMESTART', u'DOWNTIMEEND', u'DOWNTIMECANCELLED'] and
                's' not in self.notification_options):
            logger.debug("Service: %s, notification %s sending is blocked by options: %s",
                         n_type, self.get_full_name(), self.notification_options)
            return True

        # Acknowledgements make no sense when the status is ok/up
        if n_type in [u'ACKNOWLEDGEMENT'] and self.state == self.ok_up:
            logger.debug("Host: %s, notification %s sending is blocked by current state",
                         self.get_name(), n_type)
            return True

        # Block if host is in a scheduled downtime
        if host.scheduled_downtime_depth > 0:
            logger.debug("Service: %s, notification %s sending is blocked by downtime",
                         self.get_name(), n_type)
            return True

        # When in deep downtime, only allow end-of-downtime notifications
        # In depth 1 the downtime just started and can be notified
        if self.scheduled_downtime_depth > 1 and n_type not in (u'DOWNTIMEEND',
                                                                u'DOWNTIMECANCELLED'):
            logger.debug("Service: %s, notification %s sending is blocked by deep downtime",
                         self.get_name(), n_type)
            return True

        # Block if in a scheduled downtime and a problem arises, or flapping event
        if self.scheduled_downtime_depth > 0 and n_type in \
                [u'PROBLEM', u'RECOVERY', u'ACKNOWLEDGEMENT',
                 u'FLAPPINGSTART', u'FLAPPINGSTOP', u'FLAPPINGDISABLED']:
            logger.debug("Service: %s, notification %s sending is blocked by downtime",
                         self.get_name(), n_type)
            return True

        # Block if the status is SOFT
        # Block if the problem has already been acknowledged
        # Block if flapping
        # Block if host is down
        if self.state_type == u'SOFT' and n_type == u'PROBLEM' or \
                self.problem_has_been_acknowledged and n_type != u'ACKNOWLEDGEMENT' or \
                self.is_flapping and n_type not in [u'FLAPPINGSTART',
                                                    u'FLAPPINGSTOP',
                                                    u'FLAPPINGDISABLED'] or \
                host.state != host.ok_up:
            logger.debug("Service: %s, notification %s sending is blocked by soft state, "
                         "acknowledgement, flapping or host DOWN", self.get_name(), n_type)
            return True

        # Block if business rule smart notifications is enabled and all its
        # children have been acknowledged or are under downtime.
        if self.got_business_rule is True \
                and self.business_rule_smart_notifications is True \
                and self.business_rule_notification_is_blocked(hosts, services) is True \
                and n_type == u'PROBLEM':
            logger.debug("Service: %s, notification %s sending is blocked by business rules",
                         self.get_name(), n_type)
            return True

        logger.debug("Service: %s, notification %s sending is not blocked", self.get_name(), n_type)
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

        return mapping.get(self.state_id, "n/a")

    def get_status(self, hosts, services):
        """Get the status of this host

        :return: "OK", "WARNING", "CRITICAL", "UNKNOWN" or "n/a" based on
                 service state_id or business_rule state
        :rtype: str
        """

        if self.got_business_rule:
            mapping = {
                0: u'OK',
                1: u'WARNING',
                2: u'CRITICAL',
                3: u'UNKNOWN',
                4: u'UNREACHABLE',
            }
            return mapping.get(self.business_rule.get_state(hosts, services), "n/a")

        return self.state

    def get_downtime(self):
        """Accessor to scheduled_downtime_depth attribute

        :return: scheduled downtime depth
        :rtype: str
        TODO: Move to util or SchedulingItem class
        """
        return str(self.scheduled_downtime_depth)


class Services(SchedulingItems):
    """Class for the services lists. It's mainly for configuration

    """
    name_property = 'unique_key'  # only used by (un)indexitem (via 'name_property')
    inner_class = Service  # use for know what is in items

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
        sdesc = getattr(tpl, 'service_description', '')
        hname = getattr(tpl, 'host_name', '')
        logger.debug("Adding a %s template: host_name: %s, name: %s, service_description: %s",
                     objcls, hname, name, sdesc)
        if not name and not hname:
            msg = "a %s template has been defined without name nor host_name. from: %s" \
                  % (objcls, tpl.imported_from)
            tpl.add_error(msg)
        elif not name and not sdesc:
            msg = "a %s template has been defined without name nor service_description. from: %s" \
                  % (objcls, tpl.imported_from)
            tpl.add_error(msg)
        elif not name:
            # If name is not defined, use the host_name_service_description as name (fix #791)
            setattr(tpl, 'name', "%s_%s" % (hname, sdesc))
            tpl = self.index_template(tpl)
        elif name:
            tpl = self.index_template(tpl)
        self.templates[tpl.uuid] = tpl
        logger.debug('\tAdded service template #%d %s', len(self.templates), tpl)

    def apply_inheritance(self):
        """ For all items and templates inherit properties and custom
            variables.

        :return: None
        """
        super(Services, self).apply_inheritance()

        # add_item only ensure we can build a key for services later (after explode)
        for item in list(self.items.values()):
            self.add_item(item, False)

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

    def linkify(self, hosts, commands, timeperiods, contacts,  # pylint: disable=R0913
                resultmodulations, businessimpactmodulations, escalations,
                servicegroups, checkmodulations, macromodulations):
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
                    host.add_error("Error: invalid service override syntax: %s" % ovr)
                    continue
                sdescr, prop, value = match.groups()
                # Looks for corresponding service
                service = self.find_srv_by_name_and_hostname(getattr(host, "host_name", ""), sdescr)
                if service is None:
                    host.add_error("Error: trying to override property '%s' on service '%s' "
                                   "but it's unknown for this host" % (prop, sdescr))
                    continue
                # Checks if override is allowed
                excludes = ['host_name', 'service_description', 'use',
                            'servicegroups', 'trigger_name']
                if prop in excludes:
                    host.add_error("Error: trying to override '%s', "
                                   "a forbidden property for service '%s'" % (prop, sdescr))
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
                # Let the host know we are his service
                if hst is not None:
                    serv.host = hst.uuid
                    hst.add_service_link(serv.uuid)
                else:  # Ok, the host do not exists!
                    err = "Warning: the service '%s' got an invalid host_name '%s'" % \
                          (serv.get_name(), hst_name)
                    serv.configuration_warnings.append(err)
                    continue
            except AttributeError:
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
                        new_servicegroups.append(servicegroup.uuid)
                    else:
                        err = "Error: the servicegroup '%s' of the service '%s' is unknown" %\
                              (sg_name, serv.get_dbg_name())
                        serv.add_error(err)
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
                if hasattr(serv, 'host_name') and not getattr(serv, prop, None):
                    host = hosts.find_by_name(serv.host_name)
                    if host is not None and hasattr(host, prop):
                        logger.debug("Implicit inheritance for %s/%s: %s = %s",
                                     serv.host_name, serv, prop, getattr(host, prop))
                        setattr(serv, prop, getattr(host, prop))

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

        Note that this should not happen!

        :return: None
        """
        to_del = []
        for serv in self:
            if not serv.host:
                to_del.append(serv.uuid)
        for service_uuid in to_del:
            del self.items[service_uuid]

    def explode_services_from_hosts(self, hosts, service, hnames):
        """
        Explodes a service based on a list of hosts.

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
                err = 'Error: The hostname %s is unknown for the service %s!' \
                      % (hname, service.get_name())
                service.add_error(err)
                continue
            if host.is_excluded_for(service):
                continue
            new_s = service.copy()
            new_s.host_name = hname
            self.add_item(new_s)

    # pylint: disable=inconsistent-return-statements
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
            return None
        # Creates concrete instance
        new_s = service.copy()
        new_s.host_name = host_name
        new_s.register = 1
        self.add_item(new_s)
        return new_s

    def explode_services_from_templates(self, hosts, service):
        """
        Explodes services from templates. All hosts holding the specified
        templates are bound with the service.

        :param hosts: The hosts container.
        :type hosts: alignak.objects.host.Hosts
        :param service: The service to explode.
        :type service: alignak.objects.service.Service
        :return: None
        """
        hname = getattr(service, "host_name", None)
        if not hname:
            return

        logger.debug("Explode services from templates: %s", hname)
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
            service.add_error('Error: The hostname %s is unknown for the service %s!'
                              % (hname, service.get_name()))
            return

        # Duplicate services
        for new_s in service.duplicate(host):
            if host.is_excluded_for(new_s):
                continue
            # Adds concrete instance
            self.add_item(new_s)

    @staticmethod
    def register_service_into_servicegroups(service, servicegroups):
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

    @staticmethod
    def register_service_dependencies(service, servicedependencies):
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
    def explode(self, hosts, hostgroups, contactgroups, servicegroups, servicedependencies):
        # pylint: disable=too-many-locals
        """
        Explodes services, from host, hostgroups, contactgroups, servicegroups and dependencies.

        :param hosts: The hosts container
        :type hosts: [alignak.object.host.Host]
        :param hostgroups: The hosts goups container
        :type hostgroups: [alignak.object.hostgroup.Hostgroup]
        :param contactgroups: The contacts goups container
        :type contactgroups: [alignak.object.contactgroup.Contactgroup]
        :param servicegroups: The services goups container
        :type servicegroups: [alignak.object.servicegroup.Servicegroup]
        :param servicedependencies: The services dependencies container
        :type servicedependencies: [alignak.object.servicedependency.Servicedependency]
        :return: None
        """
        # Then for every service create a copy of the service with just the host
        # because we are adding services, we can't just loop in it
        itemkeys = list(self.items.keys())
        for s_id in itemkeys:
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
                # Delete expanded source service, even if some errors exist
                self.remove_item(serv)

        for s_id in self.templates:
            template = self.templates[s_id]
            self.explode_contact_groups_into_contacts(template, contactgroups)
            self.explode_services_from_templates(hosts, template)

        # Explode services that have a duplicate_foreach clause
        duplicates = [serv.uuid for serv in self if getattr(serv, 'duplicate_foreach', '')]
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

        # Servicegroups property need to be fulfill for got the information
        # And then just register to this service_group
        for serv in self:
            self.register_service_into_servicegroups(serv, servicegroups)
            self.register_service_dependencies(serv, servicedependencies)

    def fill_predictive_missing_parameters(self):
        """Loop on services and call Service.fill_predictive_missing_parameters()

        :return: None
        """
        for service in self:
            service.fill_predictive_missing_parameters()
