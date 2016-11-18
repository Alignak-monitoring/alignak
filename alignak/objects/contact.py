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
from alignak.objects.item import Item
from alignak.objects.notificationway import NotificationWay
from alignak.objects.commandcallitem import CommandCallItems

from alignak.util import strip_and_uniq
from alignak.property import BoolProp, IntegerProp, StringProp, ListProp, DictProp
from alignak.log import make_monitoring_log
from alignak.commandcall import CommandCall

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Contact(Item):
    """Host class implements monitoring concepts for contact.
    For example it defines host_notification_period, service_notification_period etc.
    """
    name_property = "contact_name"
    my_type = 'contact'

    properties = Item.properties.copy()
    properties.update({
        'contact_name':
            StringProp(fill_brok=['full_status']),
        'contactgroups':
            ListProp(default=[], fill_brok=['full_status']),
        # Todo: define default parameters for contact notifications
        'host_notifications_enabled':
            BoolProp(default=True, fill_brok=['full_status']),
        'service_notifications_enabled':
            BoolProp(default=True, fill_brok=['full_status']),
        'host_notification_period':
            StringProp(fill_brok=['full_status']),
        'service_notification_period':
            StringProp(fill_brok=['full_status']),
        'host_notification_options':
            ListProp(default=[''], fill_brok=['full_status']),
        'service_notification_options':
            ListProp(default=[''], fill_brok=['full_status']),
        # To be consistent with notificationway object attributes
        'host_notification_commands':
            ListProp(default=[], fill_brok=['full_status']),
        'service_notification_commands':
            ListProp(default=[], fill_brok=['full_status']),
        'min_business_impact':
            IntegerProp(default=0, fill_brok=['full_status']),
        'email':
            StringProp(default='none', fill_brok=['full_status']),
        'pager':
            StringProp(default='none', fill_brok=['full_status']),
        'address1':
            StringProp(default='none', fill_brok=['full_status']),
        'address2':
            StringProp(default='none', fill_brok=['full_status']),
        'address3':
            StringProp(default='none', fill_brok=['full_status']),
        'address4':
            StringProp(default='none', fill_brok=['full_status']),
        'address5':
            StringProp(default='none', fill_brok=['full_status']),
        'address6':
            StringProp(default='none', fill_brok=['full_status']),
        'notificationways':
            ListProp(default=[], fill_brok=['full_status']),
        # WebUI only information
        # Todo: remove this!
        'password':
            StringProp(default='NOPASSWORDSET', fill_brok=['full_status']),
        'can_submit_commands':
            BoolProp(default=False, fill_brok=['full_status']),
        'is_admin':
            BoolProp(default=False, fill_brok=['full_status']),
        'expert':
            BoolProp(default=False, fill_brok=['full_status']),
    })

    running_properties = Item.running_properties.copy()
    running_properties.update({
        'modified_attributes':
            IntegerProp(default=0L, fill_brok=['full_status'], retention=True),
        'modified_host_attributes':
            IntegerProp(default=0L, fill_brok=['full_status'], retention=True),
        'modified_service_attributes':
            IntegerProp(default=0L, fill_brok=['full_status'], retention=True),
        'in_scheduled_downtime':
            BoolProp(default=False, fill_brok=['full_status', 'check_result'], retention=True),
        'broks':
            ListProp(default=[]),  # and here broks raised
        'downtimes':
            ListProp(default=[], fill_brok=['full_status'], retention=True),
        'customs':
            DictProp(default={}, fill_brok=['full_status']),
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
        'CONTACTGROUPNAME': ('get_groupname', ['contactgroups']),
        'CONTACTGROUPNAMES': ('get_groupnames', ['contactgroups'])
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

    def __init__(self, params=None, parsing=True, debug=False):

        if params is None:
            params = {}
        super(Contact, self).__init__(params, parsing=parsing, debug=debug)
        # Fill default values
        super(Contact, self).fill_default()

        # At deserialization, those are dict
        # TODO: Separate parsing instance from recreated ones
        for prop in ['service_notification_commands', 'host_notification_commands']:
            if prop in params and isinstance(params[prop], list) and len(params[prop]) > 0 \
                    and isinstance(params[prop][0], dict):
                new_list = [CommandCall(elem, parsing=parsing) for elem in params[prop]]
                # We recreate the object
                setattr(self, prop, new_list)
                # And remove prop, to prevent from being overridden
                del params[prop]

    def serialize(self):
        res = super(Contact, self).serialize()

        for prop in ['service_notification_commands', 'host_notification_commands']:
            if getattr(self, prop) is None:
                res[prop] = None
            else:
                res[prop] = [elem.serialize() for elem in getattr(self, prop)]

        return res

    def get_groupname(self, groups):
        """Get name of the contact's first contactgroup

        :return: the first contact group name
        :rtype: str
        """
        groupname = ''
        for group_id in self.contactgroups:
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
        for group_id in self.contactgroups:
            group = groups[group_id]
            if group:
                groupnames.append(group.get_name())

        return ','.join(sorted(groupnames))

    def want_service_notification(self, notifways, timeperiods, downtimes,
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
            downtime = downtimes[downtime_id]
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

    def get_notification_commands(self, notifways, n_type):
        """Get notification commands for object type

        :param n_type: object type (host or service)
        :type n_type: object
        :return: command list
        :rtype: list[alignak.objects.command.Command]
        """
        res = []
        # service_notification_commands for service
        notif_commands_prop = n_type + '_notification_commands'
        for notifway_id in self.notificationways:
            notifway = notifways[notifway_id]
            res.extend(getattr(notifway, notif_commands_prop))
        return res

    def is_correct(self):
        """Check if this object configuration is correct ::

        * Check our own specific properties
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """

        # Internal checks before executing inherited function...

        # There is a case where there is no nw: when there is not special_prop defined
        # at all!!
        if self.notificationways == []:
            for prop in self.special_properties:
                if not hasattr(self, prop):
                    self.add_error("[contact::%s] %s property is missing" %
                                   (self.get_name(), prop))

        if hasattr(self, 'contact_name'):
            for char in self.__class__.illegal_object_name_chars:
                if char in self.contact_name:
                    self.add_error("[contact::%s] %s character not allowed in contact_name" %
                                   (self.get_name(), char))
        else:
            if hasattr(self, 'alias'):  # take the alias if we miss the contact_name
                self.contact_name = self.alias

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

    def linkify(self, commands, notificationways, contactgroups):
        """Create link between objects::

         * contacts -> notificationways

        :param notificationways: notificationways to link
        :type notificationways: alignak.objects.notificationway.Notificationways
        :return: None
        TODO: Clean this function
        """
        self.linkify_contact_by_contactgroup(contactgroups)
        self.linkify_with_notificationways(notificationways)
        self.linkify_command_list_with_commands(commands, 'service_notification_commands')
        self.linkify_command_list_with_commands(commands, 'host_notification_commands')

    def linkify_contact_by_contactgroup(self, contactgroups):
        """Link contacts with contactgroups

        :param contactgroups: contactgroups
        :type contactgroups: alignak.objects.contactgroup.contactgroups
        :return: None
        """
        for contact in self:
            new_contactgroups = []
            if hasattr(contact, 'contactgroups') and contact.contactgroups:
                # Because contacts groups can be created because a contact references
                # a not existing group or because a group exists in the configuration,
                # we can have an uuid or a name...
                for contactgroup_name in contact.contactgroups:
                    if contactgroup_name in contactgroups:
                        # We got an uuid and already linked the item with its group
                        new_contactgroups.append(contactgroup_name)
                        continue

                    contactgroup = contactgroups.find_by_name(contactgroup_name)
                    if contactgroup is not None:
                        new_contactgroups.append(contactgroup.uuid)
                    else:
                        contact.add_error("the contactgroup '%s' of the contact '%s' is unknown" %
                                          (contactgroup_name, contact.get_full_name()))

            contact.contactgroups = list(set(new_contactgroups))

    def linkify_with_notificationways(self, notificationways):
        """Link contacts with notification ways

        :param notificationways: notificationways object to link with
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

        # Register ourselves into the contactsgroups we are in
        for contact in self:
            if getattr(contact, 'contactgroups', None) is not None:
                for contactgroup in contact.contactgroups:
                    contactgroups.add_group_member(contact, contactgroup.strip())

        # Now create a notification way with the simple parameter of the
        # contacts
        for contact in self:
            need_notificationway = False
            params = {}
            for param in Contact.simple_way_parameters:
                if hasattr(contact, param):
                    need_notificationway = True
                    params[param] = getattr(contact, param)
                elif contact.properties[param].has_default:  # put a default text value
                    # Remove the value and put a default value
                    setattr(contact, param, contact.properties[param].default)

            if need_notificationway:
                params.update({
                    'notificationway_name': contact.get_name() + '_inner_notificationway'
                })
                notificationway = NotificationWay(params)
                notificationway.fill_default()
                notificationways.add_item(notificationway)

                if not hasattr(contact, 'notificationways'):
                    contact.notificationways = [notificationway.get_name()]
                else:
                    contact.notificationways.append(notificationway.get_name())
