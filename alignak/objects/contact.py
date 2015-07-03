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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Guillaume Bour, guillaume@bour.cc
#     aviau, alexandre.viau@savoirfairelinux.com
#     Grégory Starck, g.starck@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
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
""" This module provide Contact and Contacts classes that
implements contact for notification. Basically used for parsing.
"""
from item import Item, Items

from alignak.util import strip_and_uniq
from alignak.property import BoolProp, IntegerProp, StringProp, ListProp
from alignak.log import logger, naglog_result

_special_properties = (
    'service_notification_commands', 'host_notification_commands',
    'service_notification_period', 'host_notification_period',
    'service_notification_options', 'host_notification_options',
    'host_notification_commands', 'contact_name'
)

_simple_way_parameters = (
    'service_notification_period', 'host_notification_period',
    'service_notification_options', 'host_notification_options',
    'service_notification_commands', 'host_notification_commands',
    'min_business_impact'
)


class Contact(Item):
    """Host class implements monitoring concepts for contact.
    For example it defines host_notification_period, service_notification_period etc.
    """
    id = 1  # zero is always special in database, so we do not take risk here
    my_type = 'contact'

    properties = Item.properties.copy()
    properties.update({
        'contact_name':     StringProp(fill_brok=['full_status']),
        'alias':            StringProp(default='none', fill_brok=['full_status']),
        'contactgroups':    ListProp(default=[], fill_brok=['full_status']),
        'host_notifications_enabled': BoolProp(default=True, fill_brok=['full_status']),
        'service_notifications_enabled': BoolProp(default=True, fill_brok=['full_status']),
        'host_notification_period': StringProp(fill_brok=['full_status']),
        'service_notification_period': StringProp(fill_brok=['full_status']),
        'host_notification_options': ListProp(default=[''], fill_brok=['full_status'],
                                              split_on_coma=True),
        'service_notification_options': ListProp(default=[''], fill_brok=['full_status'],
                                                 split_on_coma=True),
        # To be consistent with notificationway object attributes
        'host_notification_commands': ListProp(fill_brok=['full_status']),
        'service_notification_commands': ListProp(fill_brok=['full_status']),
        'min_business_impact':    IntegerProp(default=0, fill_brok=['full_status']),
        'email':            StringProp(default='none', fill_brok=['full_status']),
        'pager':            StringProp(default='none', fill_brok=['full_status']),
        'address1':         StringProp(default='none', fill_brok=['full_status']),
        'address2':         StringProp(default='none', fill_brok=['full_status']),
        'address3':        StringProp(default='none', fill_brok=['full_status']),
        'address4':         StringProp(default='none', fill_brok=['full_status']),
        'address5':         StringProp(default='none', fill_brok=['full_status']),
        'address6':         StringProp(default='none', fill_brok=['full_status']),
        'can_submit_commands': BoolProp(default=False, fill_brok=['full_status']),
        'is_admin':         BoolProp(default=False, fill_brok=['full_status']),
        'expert':           BoolProp(default=False, fill_brok=['full_status']),
        'retain_status_information': BoolProp(default=True, fill_brok=['full_status']),
        'notificationways': ListProp(default=[], fill_brok=['full_status']),
        'password':        StringProp(default='NOPASSWORDSET', fill_brok=['full_status']),
    })

    running_properties = Item.running_properties.copy()
    running_properties.update({
        'modified_attributes': IntegerProp(default=0L, fill_brok=['full_status'], retention=True),
        'downtimes': StringProp(default=[], fill_brok=['full_status'], retention=True),
    })

    # This tab is used to transform old parameters name into new ones
    # so from Nagios2 format, to Nagios3 ones.
    # Or Alignak deprecated names like criticity
    old_properties = {
        'min_criticity': 'min_business_impact',
    }

    macros = {
        'CONTACTNAME': 'contact_name',
        'CONTACTALIAS': 'alias',
        'CONTACTEMAIL': 'email',
        'CONTACTPAGER': 'pager',
        'CONTACTADDRESS1': 'address1',
        'CONTACTADDRESS2': 'address2',
        'CONTACTADDRESS3': 'address3',
        'CONTACTADDRESS4': 'address4',
        'CONTACTADDRESS5': 'address5',
        'CONTACTADDRESS6': 'address6',
        'CONTACTGROUPNAME': 'get_groupname',
        'CONTACTGROUPNAMES': 'get_groupnames'
    }

    def get_name(self):
        """Get contact name

        :return: contact name
        :rtype: str
        """
        try:
            return self.contact_name
        except AttributeError:
            return 'UnnamedContact'

    def want_service_notification(self, t, state, type, business_impact, cmd=None):
        """Check if notification options match the state of the service

        :param t: time we want to notify the contact (usually now)
        :type t: int
        :param state: host or service state ("WARNING", "CRITICAL" ..)
        :type state: str
        :param type: type of notification ("PROBLEM", "RECOVERY" ..)
        :type type: str
        :param business_impact: impact of this service
        :type business_impact: int
        :param cmd: command launch to notify the contact
        :type cmd: str
        :return: True if contact wants notification, False otherwise
        """
        if not self.service_notifications_enabled:
            return False

        # If we are in downtime, we do nto want notification
        for dt in self.downtimes:
            if dt.is_in_effect:
                return False

        # Now the rest is for sub notificationways. If one is OK, we are ok
        # We will filter in another phase
        for nw in self.notificationways:
            nw_b = nw.want_service_notification(t, state, type, business_impact, cmd)
            if nw_b:
                return True

        # Oh... no one is ok for it? so no, sorry
        return False

    def want_host_notification(self, t, state, type, business_impact, cmd=None):
        """Check if notification options match the state of the host

        :param t: time we want to notify the contact (usually now)
        :type t: int
        :param state: host or service state ("UP", "DOWN" ..)
        :type state: str
        :param type: type of notification ("PROBLEM", "RECOVERY" ..)
        :type type: str
        :param business_impact: impact of this host
        :type business_impact: int
        :param cmd: command launch to notify the contact
        :type cmd: str
        :return: True if contact wants notification, False otherwise
        """
        if not self.host_notifications_enabled:
            return False

        # If we are in downtime, we do nto want notification
        for dt in self.downtimes:
            if dt.is_in_effect:
                return False

        # Now it's all for sub notificationways. If one is OK, we are OK
        # We will filter in another phase
        for nw in self.notificationways:
            nw_b = nw.want_host_notification(t, state, type, business_impact, cmd)
            if nw_b:
                return True

        # Oh, nobody..so NO :)
        return False

    def get_notification_commands(self, type):
        """Get notification commands for object type

        :param type: object type (host or service)
        :return: command list
        :rtype: list[alignak.objects.command.Command]
        """
        r = []
        # service_notification_commands for service
        notif_commands_prop = type + '_notification_commands'
        for nw in self.notificationways:
            r.extend(getattr(nw, notif_commands_prop))
        return r

    def is_correct(self):
        """Check if this host configuration is correct ::

        * All required parameter are specified
        * Go through all configuration warnings and errors that could have been raised earlier

        :return: True if the configuration is correct, False otherwise
        :rtype: bool
        """
        state = True
        cls = self.__class__

        # All of the above are checks in the notificationways part
        for prop, entry in cls.properties.items():
            if prop not in _special_properties:
                if not hasattr(self, prop) and entry.required:
                    logger.error("[contact::%s] %s property not set", self.get_name(), prop)
                    state = False  # Bad boy...

        # There is a case where there is no nw: when there is not special_prop defined
        # at all!!
        if self.notificationways == []:
            for p in _special_properties:
                if not hasattr(self, p):
                    logger.error("[contact::%s] %s property is missing", self.get_name(), p)
                    state = False

        if hasattr(self, 'contact_name'):
            for c in cls.illegal_object_name_chars:
                if c in self.contact_name:
                    logger.error("[contact::%s] %s character not allowed in contact_name",
                                 self.get_name(), c)
                    state = False
        else:
            if hasattr(self, 'alias'):  # take the alias if we miss the contact_name
                self.contact_name = self.alias

        return state

    def raise_enter_downtime_log_entry(self):
        """Raise CONTACT DOWNTIME ALERT entry (info level)
        Format is : "CONTACT DOWNTIME ALERT: *get_name()*;STARTED;
                      Contact has entered a period of scheduled downtime"
        Example : "CONTACT DOWNTIME ALERT: test_contact;STARTED;
                    Contact has entered a period of scheduled downtime"

        :return: None
        """
        naglog_result('info', "CONTACT DOWNTIME ALERT: %s;STARTED; Contact has "
                      "entered a period of scheduled downtime" % self.get_name())

    def raise_exit_downtime_log_entry(self):
        """Raise CONTACT DOWNTIME ALERT entry (info level)
        Format is : "CONTACT DOWNTIME ALERT: *get_name()*;STOPPED;
                      Contact has entered a period of scheduled downtime"
        Example : "CONTACT DOWNTIME ALERT: test_contact;STOPPED;
                    Contact has entered a period of scheduled downtime"

        :return: None
        """
        naglog_result('info', "CONTACT DOWNTIME ALERT: %s;STOPPED; Contact has "
                      "exited from a period of scheduled downtime" % self.get_name())

    def raise_cancel_downtime_log_entry(self):
        """Raise CONTACT DOWNTIME ALERT entry (info level)
        Format is : "CONTACT DOWNTIME ALERT: *get_name()*;CANCELLED;
                      Contact has entered a period of scheduled downtime"
        Example : "CONTACT DOWNTIME ALERT: test_contact;CANCELLED;
                    Contact has entered a period of scheduled downtime"

        :return: None
        """
        naglog_result('info', "CONTACT DOWNTIME ALERT: %s;CANCELLED; Scheduled "
                      "downtime for contact has been cancelled." % self.get_name())


class Contacts(Items):
    """Contacts manage a list of Contacts objects, used for parsing configuration

    """
    name_property = "contact_name"
    inner_class = Contact

    def linkify(self, timeperiods, commands, notificationways):
        """Create link between objects::

         * contacts -> timeperiods
         * contacts -> commands
         * contacts -> notificationways

        :param timeperiods: timeperiods to link
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param commands: commands to link
        :type commands: alignak.objects.command.Commands
        :param notificationways: notificationways to link
        :type notificationways: alignak.objects.notificationway.Notificationways
        :return: None
        TODO: Clean this function
        """
        # self.linkify_with_timeperiods(timeperiods, 'service_notification_period')
        # self.linkify_with_timeperiods(timeperiods, 'host_notification_period')
        # self.linkify_command_list_with_commands(commands, 'service_notification_commands')
        # self.linkify_command_list_with_commands(commands, 'host_notification_commands')
        self.linkify_with_notificationways(notificationways)

    def linkify_with_notificationways(self, notificationways):
        """Link hosts with realms

        :param notificationways: notificationways object to link with
        :type notificationways: alignak.objects.notificationway.Notificationways
        :return: None
        """
        for i in self:
            if not hasattr(i, 'notificationways'):
                continue
            new_notificationways = []
            for nw_name in strip_and_uniq(i.notificationways):
                nw = notificationways.find_by_name(nw_name)
                if nw is not None:
                    new_notificationways.append(nw)
                else:
                    err = "The 'notificationways' of the %s '%s' named '%s' is unknown!" %\
                          (i.__class__.my_type, i.get_name(), nw_name)
                    i.configuration_errors.append(err)
            # Get the list, but first make elements uniq
            i.notificationways = list(set(new_notificationways))


    def explode(self, contactgroups, notificationways):
        """Explode all contact for each contactsgroup

        :param contactgroups: contactgroups to explode
        :type contactgroups: alignak.objects.contactgroup.Contactgroups
        :param notificationways: notificationways to explode
        :type notificationways: alignak.objects.notificationway.Notificationways
        :return:
        """
        # Contactgroups property need to be fullfill for got the informations
        self.apply_partial_inheritance('contactgroups')
        # _special properties maybe came from a template, so
        # import them before grok ourselves
        for prop in _special_properties:
            if prop == 'contact_name':
                continue
            self.apply_partial_inheritance(prop)

        # Register ourself into the contactsgroups we are in
        for c in self:
            if not (hasattr(c, 'contact_name') and hasattr(c, 'contactgroups')):
                continue
            for cg in c.contactgroups:
                contactgroups.add_member(c.contact_name, cg.strip())

        # Now create a notification way with the simple parameter of the
        # contacts
        for c in self:
            need_notificationway = False
            params = {}
            for p in _simple_way_parameters:
                if hasattr(c, p):
                    need_notificationway = True
                    params[p] = getattr(c, p)
                else:  # put a default text value
                    # Remove the value and put a default value
                    setattr(c, p, c.properties[p].default)

            if need_notificationway:
                # print "Create notif way with", params
                cname = getattr(c, 'contact_name', getattr(c, 'alias', ''))
                nw_name = cname + '_inner_notificationway'
                notificationways.new_inner_member(nw_name, params)

                if not hasattr(c, 'notificationways'):
                    c.notificationways = [nw_name]
                else:
                    c.notificationways.append(nw_name)
