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
#     Sebastien Coavoux, s.coavoux@free.fr
#     Guillaume Bour, guillaume@bour.cc
#     aviau, alexandre.viau@savoirfairelinux.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Andrew McGilvray, amcgilvray@kixeye.com
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Romain Forlot, rforlot@yahoo.com

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
"""This module provides Escalation and Escalations classes that
implements escalation for notification. Basically used for parsing.

"""
from alignak.objects.item import Item, Items

from alignak.util import strip_and_uniq
from alignak.property import BoolProp, IntegerProp, StringProp, ListProp


class Escalation(Item):
    """Escalation class is used to implement notification escalation

    """
    my_type = 'escalation'

    properties = Item.properties.copy()
    properties.update({
        'escalation_name':
            StringProp(),
        'host_name':
            StringProp(default=''),
        'hostgroup_name':
            StringProp(''),
        'service_description':
            StringProp(default=''),
        'first_notification':
            IntegerProp(),
        'last_notification':
            IntegerProp(),
        'first_notification_time':
            IntegerProp(),
        'last_notification_time':
            IntegerProp(),
        # As a default don't use the notification_interval defined in
        # the escalation, but the one defined in the object
        'notification_interval':
            IntegerProp(default=-1),
        'escalation_period':
            StringProp(default=''),
        'escalation_options':
            ListProp(default=['d', 'x', 'r', 'w', 'c'], split_on_comma=True),
        'contacts':
            ListProp(default=[], split_on_comma=True),
        'contact_groups':
            ListProp(default=[], split_on_comma=True),
    })

    running_properties = Item.running_properties.copy()
    running_properties.update({
        'time_based': BoolProp(default=False),
    })

    special_properties = ('contacts', 'contact_groups',
                          'first_notification_time', 'last_notification_time')
    special_properties_time_based = ('contacts', 'contact_groups',
                                     'first_notification', 'last_notification')

    def __init__(self, params=None, parsing=True):
        if params is None:
            params = {}

        for prop in ['escalation_options']:
            if prop in params:
                params[prop] = [p.replace('u', 'x') for p in params[prop]]
        super(Escalation, self).__init__(params, parsing=parsing)

    def get_name(self):
        """Accessor to escalation_name attribute

        :return: escalation name
        :rtype: str
        """
        return self.escalation_name

    def is_eligible(self, timestamp, status, notif_number, in_notif_time, interval, escal_period):
        # pylint: disable=too-many-return-statements
        """Check if the escalation is eligible (notification is escalated or not)

        Escalation is NOT eligible in ONE of the following condition is fulfilled::

        * escalation is not time based and notification number not in range
          [first_notification;last_notification] (if last_notif == 0, it's infinity)
        * escalation is time based and notification time not in range
          [first_notification_time;last_notification_time] (if last_notif_time == 0, it's infinity)
        * status does not matches escalation_options ('WARNING' <=> 'w' ...)
        * escalation_period is not legit for this time (now usually)

        :param timestamp: timestamp to check if timeperiod is valid
        :type timestamp: int
        :param status: item status (one of the small_states key)
        :type status: str
        :param notif_number: current notification number
        :type notif_number: int
        :param in_notif_time: current notification time
        :type in_notif_time: int
        :param interval: time interval length
        :type interval: int
        :return: True if no condition has been fulfilled, otherwise False
        :rtype: bool
        """
        short_states = {
            u'WARNING': 'w', u'UNKNOWN': 'u', u'CRITICAL': 'c',
            u'RECOVERY': 'r', u'FLAPPING': 'f', u'DOWNTIME': 's',
            u'DOWN': 'd', u'UNREACHABLE': 'x', u'OK': 'o', u'UP': 'o'
        }

        # If we are not time based, we check notification numbers:
        if not self.time_based:
            # Begin with the easy cases
            if notif_number < self.first_notification:
                return False

            # self.last_notification = 0 mean no end
            if self.last_notification and notif_number > self.last_notification:
                return False
        # Else we are time based, we must check for the good value
        else:
            # Begin with the easy cases
            if in_notif_time < self.first_notification_time * interval:
                return False

            if self.last_notification_time and \
                    in_notif_time > self.last_notification_time * interval:
                return False

        # If our status is not good, we bail out too
        if status in short_states and short_states[status] not in self.escalation_options:
            return False

        # Maybe the time is not in our escalation_period
        if escal_period is not None and not escal_period.is_time_valid(timestamp):
            return False

        # Ok, I do not see why not escalade. So it's True :)
        return True

    def get_next_notif_time(self, t_wished, status, creation_time, interval, escal_period):
        """Get the next notification time for the escalation
        Only legit for time based escalation

        :param t_wished: time we would like to send a new notification (usually now)
        :type t_wished:
        :param status: status of the host or service
        :type status:
        :param creation_time: time the notification was created
        :type creation_time:
        :param interval: time interval length
        :type interval: int
        :return: timestamp for next notification or None
        :rtype: int | None
        """
        short_states = {u'WARNING': 'w', u'UNKNOWN': 'u', u'CRITICAL': 'c',
                        u'RECOVERY': 'r', u'FLAPPING': 'f', u'DOWNTIME': 's',
                        u'DOWN': 'd', u'UNREACHABLE': 'u', u'OK': 'o', u'UP': 'o'}

        # If we are not time based, we bail out!
        if not self.time_based:
            return None

        # Check if we are valid
        if status in short_states and short_states[status] not in self.escalation_options:
            return None

        # Look for the min of our future validity
        start = self.first_notification_time * interval + creation_time

        # If we are after the classic next time, we are not asking for a smaller interval
        if start > t_wished:
            return None

        # Maybe the time we found is not a valid one....
        if escal_period is not None and not escal_period.is_time_valid(start):
            return None

        # Ok so I ask for my start as a possibility for the next notification time
        return start

    def is_correct(self):
        """Check if this object configuration is correct ::

        * Check our own specific properties
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """
        state = True

        # Internal checks before executing inherited function...

        # If we got the _time parameters, we are time based. Unless, we are not :)
        if hasattr(self, 'first_notification_time') or hasattr(self, 'last_notification_time'):
            self.time_based = True

        # Ok now we manage special cases...
        if not hasattr(self, 'contacts') and not hasattr(self, 'contact_groups'):
            self.add_error('%s: I do not have contacts nor contact_groups' % (self.get_name()))
            state = False

        # If time_based or not, we do not check all properties
        if self.time_based:
            if not hasattr(self, 'first_notification_time'):
                self.add_error('%s: I do not have first_notification_time' % (self.get_name()))
                state = False
            if not hasattr(self, 'last_notification_time'):
                self.add_error('%s: I do not have last_notification_time' % (self.get_name()))
                state = False
        else:  # we check classical properties
            if not hasattr(self, 'first_notification'):
                self.add_error('%s: I do not have first_notification' % (self.get_name()))
                state = False
            if not hasattr(self, 'last_notification'):
                self.add_error('%s: I do not have last_notification' % (self.get_name()))
                state = False

        # Change the special_properties definition according to time_based ...
        save_special_properties = self.special_properties
        if self.time_based:
            self.special_properties = self.special_properties_time_based

        state_parent = super(Escalation, self).is_correct()

        if self.time_based:
            self.special_properties = save_special_properties

        return state_parent and state


class Escalations(Items):
    """Escalations manage a list of Escalation objects, used for parsing configuration

    """
    name_property = "escalation_name"
    inner_class = Escalation

    def linkify(self, timeperiods, contacts, services, hosts):
        """Create link between objects::

         * escalation -> host
         * escalation -> service
         * escalation -> timeperiods
         * escalation -> contact

        :param timeperiods: timeperiods to link
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param contacts: contacts to link
        :type contacts: alignak.objects.contact.Contacts
        :param services: services to link
        :type services: alignak.objects.service.Services
        :param hosts: hosts to link
        :type hosts: alignak.objects.host.Hosts
        :return: None
        """
        self.linkify_with_timeperiods(timeperiods, 'escalation_period')
        self.linkify_with_contacts(contacts)
        self.linkify_es_by_s(services)
        self.linkify_es_by_h(hosts)

    def add_escalation(self, escalation):
        """Wrapper for add_item method

        :param escalation: escalation to add to item dict
        :type escalation: alignak.objects.escalation.Escalation
        :return: None
        """
        self.add_item(escalation)

    def linkify_es_by_s(self, services):
        """Add each escalation object into service.escalation attribute

        :param services: service list, used to look for a specific service
        :type services: alignak.objects.service.Services
        :return: None
        """
        for escalation in self:
            # If no host, no hope of having a service
            if not hasattr(escalation, 'host_name'):
                continue

            es_hname, sdesc = escalation.host_name, escalation.service_description
            if not es_hname.strip() or not sdesc.strip():
                continue

            for hname in strip_and_uniq(es_hname.split(',')):
                if sdesc.strip() == '*':
                    slist = services.find_srvs_by_hostname(hname)
                    if slist is not None:
                        slist = [services[serv] for serv in slist]
                        for serv in slist:
                            serv.escalations.append(escalation.uuid)
                else:
                    for sname in strip_and_uniq(sdesc.split(',')):
                        serv = services.find_srv_by_name_and_hostname(hname, sname)
                        if serv is not None:
                            serv.escalations.append(escalation.uuid)

    def linkify_es_by_h(self, hosts):
        """Add each escalation object into host.escalation attribute

        :param hosts: host list, used to look for a specific host
        :type hosts: alignak.objects.host.Hosts
        :return: None
        """
        for escal in self:
            # If no host, no hope of having a service
            if (not hasattr(escal, 'host_name') or escal.host_name.strip() == '' or
                    (hasattr(escal, 'service_description')
                     and escal.service_description.strip() != '')):
                continue
            # I must be NOT a escalation on for service
            for hname in strip_and_uniq(escal.host_name.split(',')):
                host = hosts.find_by_name(hname)
                if host is not None:
                    host.escalations.append(escal.uuid)

    def explode(self, hosts, hostgroups, contactgroups):
        """Loop over all escalation and explode hostsgroups in host
        and contactgroups in contacts

        Call Item.explode_host_groups_into_hosts and Item.explode_contact_groups_into_contacts

        :param hosts: host list to explode
        :type hosts: alignak.objects.host.Hosts
        :param hostgroups: hostgroup list to explode
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :param contactgroups: contactgroup list to explode
        :type contactgroups: alignak.objects.contactgroup.Contactgroups
        :return: None
        """
        for i in self:
            # items::explode_host_groups_into_hosts
            # take all hosts from our hostgroup_name into our host_name property
            self.explode_host_groups_into_hosts(i, hosts, hostgroups)

            # items::explode_contact_groups_into_contacts
            # take all contacts from our contact_groups into our contact property
            self.explode_contact_groups_into_contacts(i, contactgroups)
