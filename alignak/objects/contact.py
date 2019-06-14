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
import logging
from alignak.misc.serialization import unserialize
from alignak.objects.item import Item
from alignak.objects.commandcallitem import CommandCallItems

from alignak.util import strip_and_uniq
from alignak.property import (BoolProp, IntegerProp, StringProp, ListProp,
                              DictProp, FULL_STATUS, CHECK_RESULT)
from alignak.log import make_monitoring_log
from alignak.objects.notificationway import NotificationWay

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Contact(Item):
    """Host class implements monitoring concepts for contact.
    For example it defines host_notification_period, service_notification_period etc.
    """
    my_type = 'contact'
    my_name_property = "%s_name" % my_type

    properties = Item.properties.copy()
    properties.update({
        'contact_name':
            StringProp(fill_brok=[FULL_STATUS]),
        'alias':
            StringProp(default=u'', fill_brok=[FULL_STATUS]),
        'contactgroups':
            ListProp(default=[], fill_brok=[FULL_STATUS]),

        # Those properties must be identical to the corresponding properties
        # of the Notificationway object
        'host_notifications_enabled':
            BoolProp(default=True, fill_brok=[FULL_STATUS]),
        'service_notifications_enabled':
            BoolProp(default=True, fill_brok=[FULL_STATUS]),
        'host_notification_period':
            StringProp(default='', fill_brok=[FULL_STATUS]),
        'service_notification_period':
            StringProp(default='', fill_brok=[FULL_STATUS]),
        'host_notification_options':
            ListProp(default=[], fill_brok=[FULL_STATUS], split_on_comma=True),
        'service_notification_options':
            ListProp(default=[], fill_brok=[FULL_STATUS], split_on_comma=True),
        'host_notification_commands':
            ListProp(default=[], fill_brok=[FULL_STATUS]),
        'service_notification_commands':
            ListProp(default=[], fill_brok=[FULL_STATUS]),
        'min_business_impact':
            IntegerProp(default=0, fill_brok=[FULL_STATUS]),

        'email':
            StringProp(default=u'none', fill_brok=[FULL_STATUS]),
        'pager':
            StringProp(default=u'none', fill_brok=[FULL_STATUS]),
        'address1':
            StringProp(default=u'none', fill_brok=[FULL_STATUS]),
        'address2':
            StringProp(default=u'none', fill_brok=[FULL_STATUS]),
        'address3':
            StringProp(default=u'none', fill_brok=[FULL_STATUS]),
        'address4':
            StringProp(default=u'none', fill_brok=[FULL_STATUS]),
        'address5':
            StringProp(default=u'none', fill_brok=[FULL_STATUS]),
        'address6':
            StringProp(default=u'none', fill_brok=[FULL_STATUS]),
        'can_submit_commands':
            BoolProp(default=False, fill_brok=[FULL_STATUS]),
        'is_admin':
            BoolProp(default=False, fill_brok=[FULL_STATUS]),
        'expert':
            BoolProp(default=False, fill_brok=[FULL_STATUS]),
        'retain_status_information':
            BoolProp(default=True, fill_brok=[FULL_STATUS]),
        'notificationways':
            ListProp(default=[], fill_brok=[FULL_STATUS]),
        'password':
            StringProp(default=u'NOPASSWORDSET', fill_brok=[FULL_STATUS]),
    })

    running_properties = Item.running_properties.copy()
    running_properties.update({
        'modified_attributes':
            IntegerProp(default=0, fill_brok=[FULL_STATUS], retention=True),
        'modified_host_attributes':
            IntegerProp(default=0, fill_brok=[FULL_STATUS], retention=True),
        'modified_service_attributes':
            IntegerProp(default=0, fill_brok=[FULL_STATUS], retention=True),
        'in_scheduled_downtime':
            BoolProp(default=False, fill_brok=[FULL_STATUS, CHECK_RESULT], retention=True),
        'broks':
            ListProp(default=[]),  # and here broks raised
        'customs':
            DictProp(default={}, fill_brok=[FULL_STATUS]),
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

    special_properties = (
        'service_notification_commands', 'host_notification_commands',
        'service_notification_period', 'host_notification_period',
        'service_notification_options', 'host_notification_options',
        'contact_name'
    )

    simple_way_parameters = (
        'service_notification_period', 'host_notification_period',
        'service_notification_options', 'host_notification_options',
        'service_notification_commands', 'host_notification_commands',
        'min_business_impact'
    )

    def __init__(self, params, parsing=True):
        # When deserialized, those are dict
        if not parsing:
            for prop in ['service_notification_commands', 'host_notification_commands']:
                if prop not in params:
                    continue

                # We recreate the list of objects
                new_list = [unserialize(elem, True) for elem in params[prop]]
                setattr(self, prop, new_list)
                # And remove prop, to prevent from being overridden
                del params[prop]

        super(Contact, self).__init__(params, parsing=parsing)

    def __str__(self):  # pragma: no cover
        return '<Contact%s %s, uuid=%s, use: %s />' \
               % (' template' if self.is_a_template() else '', self.get_full_name(), self.uuid,
                  getattr(self, 'use', None))
    __repr__ = __str__

    def get_full_name(self):
        """Get the full name of the contact

        :return: service full name
        :rtype: str
        """
        name = self.get_name()
        if getattr(self, 'display_name', None):
            name = "({}) {}".format(getattr(self, 'display_name'), name)
        elif getattr(self, 'alias', None) and getattr(self, 'alias', None) != 'none':
            name = "({}) {}".format(getattr(self, 'alias'), name)
        return name

    def get_groupname(self):
        """
        Get the first group name whose contact belongs to
        :return: group name
        :rtype: str
        """
        if self.contactgroups:
            return self.contactgroups[0]
        return 'Unknown'

    def get_groupnames(self):
        """
        Get all the groups name whose contact belongs to
        :return: comma separated list of the groups names
        :rtype: str
        """
        if self.contactgroups:
            return ', '.join(self.contactgroups)
        return 'Unknown'

    def want_service_notification(self, notifways, timeperiods,
                                  timestamp, state, n_type, business_impact, cmd=None):
        """Check if notification options match the state of the service

        :param timestamp: time we want to notify the contact (usually now)
        :type timestamp: int
        :param state: host or service state ("WARNING", "CRITICAL" ..)
        :type state: str
        :param n_type: type of notification ("PROBLEM", "RECOVERY" ..)
        :type n_type: str
        :param business_impact: impact of this service
        :type business_impact: int
        :param cmd: command launched to notify the contact
        :type cmd: str
        :return: True if contact wants notification, otherwise False
        :rtype: bool
        """
        if not self.service_notifications_enabled:
            return False

        # If we are in downtime, we do not want notification
        for downtime_id in self.downtimes:
            downtime = self.downtimes[downtime_id]
            if downtime.is_in_effect:
                self.in_scheduled_downtime = True
                return False
        self.in_scheduled_downtime = False

        # Now the rest is for sub notificationways. If one is OK, we are ok
        # We will filter in another phase
        for notifway_id in self.notificationways:
            notifway = notifways[notifway_id]
            nw_b = notifway.want_service_notification(timeperiods, timestamp,
                                                      state, n_type, business_impact, cmd)
            if nw_b:
                return True

        # Oh... no one is ok for it? so no, sorry
        return False

    def want_host_notification(self, notifways, timeperiods, timestamp, state, n_type,
                               business_impact, cmd=None):
        """Check if notification options match the state of the host

        :param timestamp: time we want to notify the contact (usually now)
        :type timestamp: int
        :param state: host or service state ("UP", "DOWN" ..)
        :type state: str
        :param n_type: type of notification ("PROBLEM", "RECOVERY" ..)
        :type n_type: str
        :param business_impact: impact of this host
        :type business_impact: int
        :param cmd: command launch to notify the contact
        :type cmd: str
        :return: True if contact wants notification, otherwise False
        :rtype: bool
        """
        if not self.host_notifications_enabled:
            return False

        # If we are in downtime, we do not want notification
        for downtime in self.downtimes:
            if downtime.is_in_effect:
                self.in_scheduled_downtime = True
                return False
        self.in_scheduled_downtime = False

        # Now it's all for sub notificationways. If one is OK, we are OK
        # We will filter in another phase
        for notifway_id in self.notificationways:
            notifway = notifways[notifway_id]
            nw_b = notifway.want_host_notification(timeperiods, timestamp,
                                                   state, n_type, business_impact, cmd)
            if nw_b:
                return True

        # Oh, nobody..so NO :)
        return False

    def get_notification_commands(self, notifways, n_type, command_name=False):
        """Get notification commands for object type

        :param notifways: list of alignak.objects.NotificationWay objects
        :type notifways: NotificationWays
        :param n_type: object type (host or service)
        :type n_type: string
        :param command_name: True to update the inner property with the name of the command,
                             False to update with the Command objects list
        :type command_name: bool
        :return: command list
        :rtype: list[alignak.objects.command.Command]
        """
        res = []

        for notifway_id in self.notificationways:
            notifway = notifways[notifway_id]
            res.extend(notifway.get_notification_commands(n_type))

        # Update inner notification commands property with command name or command
        if command_name:
            setattr(self, n_type + '_notification_commands', [c.get_name() for c in res])
        else:
            setattr(self, n_type + '_notification_commands', res)

        return res

    def is_correct(self):
        """Check if this object configuration is correct ::

        * Check our own specific properties
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """
        # Internal checks before executing inherited function...

        if not hasattr(self, 'contact_name'):
            if hasattr(self, 'alias'):
                # Use the alias if we miss the contact_name
                self.contact_name = self.alias

        # There is a case where there is no nw: when there is not special_prop defined
        # at all!!
        if not self.notificationways:
            for prop in self.special_properties:
                if not hasattr(self, prop):
                    self.add_error("[contact::%s] %s property is missing"
                                   % (self.get_name(), prop))

        for char in self.__class__.illegal_object_name_chars:
            if char not in self.contact_name:
                continue

            self.add_error("[contact::%s] %s character not allowed in contact_name"
                           % (self.get_name(), char))

        return super(Contact, self).is_correct() and self.conf_is_correct

    def raise_enter_downtime_log_entry(self):
        """Raise CONTACT DOWNTIME ALERT entry (info level)
        Format is : "CONTACT DOWNTIME ALERT: *get_name()*;STARTED;
                      Contact has entered a period of scheduled downtime"
        Example : "CONTACT DOWNTIME ALERT: test_contact;STARTED;
                    Contact has entered a period of scheduled downtime"

        :return: None
        """
        brok = make_monitoring_log(
            'info', "CONTACT DOWNTIME ALERT: %s;STARTED; "
                    "Contact has entered a period of scheduled downtime" % self.get_name()
        )
        self.broks.append(brok)

    def raise_exit_downtime_log_entry(self):
        """Raise CONTACT DOWNTIME ALERT entry (info level)
        Format is : "CONTACT DOWNTIME ALERT: *get_name()*;STOPPED;
                      Contact has entered a period of scheduled downtime"
        Example : "CONTACT DOWNTIME ALERT: test_contact;STOPPED;
                    Contact has entered a period of scheduled downtime"

        :return: None
        """
        brok = make_monitoring_log(
            'info', "CONTACT DOWNTIME ALERT: %s;STOPPED; "
                    "Contact has exited from a period of scheduled downtime" % self.get_name()
        )
        self.broks.append(brok)

    def raise_cancel_downtime_log_entry(self):
        """Raise CONTACT DOWNTIME ALERT entry (info level)
        Format is : "CONTACT DOWNTIME ALERT: *get_name()*;CANCELLED;
                      Contact has entered a period of scheduled downtime"
        Example : "CONTACT DOWNTIME ALERT: test_contact;CANCELLED;
                    Contact has entered a period of scheduled downtime"

        :return: None
        """
        brok = make_monitoring_log(
            'info', "CONTACT DOWNTIME ALERT: %s;CANCELLED; "
                    "Scheduled downtime for contact has been cancelled." % self.get_name()
        )
        self.broks.append(brok)


class Contacts(CommandCallItems):
    """Contacts manage a list of Contacts objects, used for parsing configuration

    """
    inner_class = Contact

    def linkify(self, commands, notificationways):
        """Create link between contacts and notification ways, and commands

        :param commands: commands to link with
        :type commands: alignak.objects.command.Commands

        :param notificationways: notificationways to link with
        :type notificationways: alignak.objects.notificationway.Notificationways
        :return: None
        """
        self.linkify_with_notificationways(notificationways)

        self.linkify_with_commands(commands, 'service_notification_commands', is_a_list=True)
        self.linkify_with_commands(commands, 'host_notification_commands', is_a_list=True)

    def linkify_with_notificationways(self, notificationways):
        """Link contacts with notification ways

        :param notificationways: notificationways to link with
        :type notificationways: alignak.objects.notificationway.Notificationways
        :return: None
        """
        for i in self:
            if not hasattr(i, 'notificationways'):
                continue

            new_notificationways = []
            for nw_name in strip_and_uniq(i.notificationways):
                notifway = notificationways.find_by_name(nw_name)
                if notifway is not None:
                    new_notificationways.append(notifway.uuid)
                else:
                    i.add_error("the notificationways named '%s' is unknown" % nw_name)
            # Get the list, but first make elements unique
            i.notificationways = list(set(new_notificationways))

            # Update the contact host/service notification commands properties
            i.get_notification_commands(notificationways, 'host', command_name=True)
            i.get_notification_commands(notificationways, 'service', command_name=True)

    def explode(self, contactgroups, notificationways):
        """Explode all contact for each contactsgroup

        :param contactgroups: contactgroups to explode
        :type contactgroups: alignak.objects.contactgroup.Contactgroups
        :param notificationways: notificationways to explode
        :type notificationways: alignak.objects.notificationway.Notificationways
        :return: None
        """
        # Contactgroups property need to be fulfill for got the information
        self.apply_partial_inheritance('contactgroups')

        # _special properties maybe came from a template, so
        # import them before grok ourselves
        for prop in Contact.special_properties:
            if prop == 'contact_name':
                continue
            self.apply_partial_inheritance(prop)

        # Register ourselves into the contacts groups we are in
        for contact in self:
            if not (hasattr(contact, 'contact_name') and hasattr(contact, 'contactgroups')):
                continue
            for contactgroup in contact.contactgroups:
                contactgroups.add_member(contact.contact_name, contactgroup.strip())

        # Now create a notification way with the simple parameter of the
        # contacts
        for contact in self:
            # Fill default values for all the properties
            contact.fill_default()

            # If some NW are still existing, do not create one more...
            # if hasattr(contact, 'notificationways') and getattr(contact, 'notificationways'):
            #     # The contact still has some defined NWs
            #     continue
            #
            add_nw = False
            params = {
                'notificationway_name': "%s_inner_nw" % contact.get_name()
            }
            for prop, entry in list(NotificationWay.properties.items()):
                if prop not in ['service_notification_period', 'host_notification_period',
                                'service_notification_options', 'host_notification_options',
                                'service_notification_commands', 'host_notification_commands',
                                'min_business_impact']:
                    continue
                if getattr(contact, prop, None) is not None:
                    params[prop] = getattr(contact, prop)
                    if entry.has_default and getattr(contact, prop) != entry.default:
                        # Add a NW if no default values
                        logger.debug("Contact %s, add a notification way because: %s = %s",
                                     contact.get_name(), prop, getattr(contact, prop))
                        add_nw = True

            if not add_nw:
                continue

            notificationways.add_item(NotificationWay(params, parsing=True))

            if not hasattr(contact, 'notificationways'):
                contact.notificationways = []

            contact.notificationways = list(contact.notificationways)
            contact.notificationways.append(params['notificationway_name'])
