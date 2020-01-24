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
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Grégory Starck, g.starck@gmail.com
#     Frédéric Pégé, frederic.pege@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Christophe Simon, geektophe@gmail.com
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
"""This module provides NotificationWay and NotificationWays classes that
implements way of sending notifications. Basically used for parsing.

"""
import logging
from alignak.objects.item import Item
from alignak.objects.commandcallitem import CommandCallItems

from alignak.property import IntegerProp, StringProp, ListProp, FULL_STATUS
from alignak.commandcall import CommandCall

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class NotificationWay(Item):
    """NotificationWay class is used to implement way of sending notifications (command, periods..)

    """
    my_type = 'notificationway'
    my_name_property = "%s_name" % my_type

    properties = Item.properties.copy()
    properties.update({
        'notificationway_name':
            StringProp(fill_brok=[FULL_STATUS]),

        'host_notification_period':
            StringProp(fill_brok=[FULL_STATUS]),
        'service_notification_period':
            StringProp(fill_brok=[FULL_STATUS]),
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
    })

    running_properties = Item.running_properties.copy()

    # This tab is used to transform old parameters name into new ones
    # so from Nagios2 format, to Nagios3 ones.
    # Or Alignak deprecated names like criticity
    old_properties = {
        'min_criticity': 'min_business_impact',
    }

    macros = {}

    special_properties = ('service_notification_commands', 'host_notification_commands',
                          'service_notification_period', 'host_notification_period')

    def __init__(self, params, parsing=True):
        for prop in ['service_notification_commands', 'host_notification_commands']:
            if prop not in params or params[prop] is None:
                continue
            # if not parsing:
            #     # When deserialized, those are dict and we recreate the object
            #     print("nw: %s / %s" % (self, params[prop]))
            #     setattr(self, prop, [unserialize(elem) for elem in params[prop]])
            # else:
            #     new_list = [(CommandCall(elem, parsing=parsing) if isinstance(elem, dict) else
            #                  elem) for elem in params[prop]]
            #     # We recreate the object
            #     setattr(self, prop, new_list)
            #
            if not isinstance(params[prop], list):
                params[prop] = [params[prop]]
            setattr(self, prop, [(CommandCall(elem, parsing=parsing) if isinstance(elem, dict)
                                  else elem) for elem in params[prop]])

            # And remove prop, to prevent from being overridden
            del params[prop]

        super(NotificationWay, self).__init__(params, parsing=parsing)

    @property
    def host_notifications_enabled(self):
        """Notifications are enabled for the hosts

        This is True if 'n' is not existing in the notification options array

        :return: True if 'n' is not existing in the notification options array
        :rtype: bool
        """
        return 'n' not in getattr(self, 'host_notification_options', ['n'])

    @property
    def service_notifications_enabled(self):
        """Notifications are enabled for the services

        This is True if 'n' is not existing in the notification options array

        :return: True if 'n' is not existing in the notification options array
        :rtype: bool
        """
        return 'n' not in getattr(self, 'service_notification_options', ['n'])

    def serialize(self, no_json=True, printing=False):
        res = super(NotificationWay, self).serialize()

        res['service_notification_commands'] = \
            [elem.serialize(no_json=no_json, printing=printing)
             for elem in getattr(self, 'service_notification_commands')]

        res['host_notification_commands'] = \
            [elem.serialize(no_json=no_json, printing=printing)
             for elem in getattr(self, 'host_notification_commands')]

        return res

    def want_service_notification(self, timeperiods, timestamp, state, n_type, business_impact,
                                  cmd=None):
        # pylint: disable=too-many-return-statements
        """Check if notification options match the state of the service
        Notification is NOT wanted in ONE of the following case::

        * service notifications are disabled
        * cmd is not in service_notification_commands
        * business_impact < self.min_business_impact
        * service_notification_period is not valid
        * state does not match service_notification_options for problem, recovery and flapping
        * state does not match host_notification_options for downtime

        :param timeperiods: list of time periods
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
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
        :return: True if no condition is matched, otherwise False
        :rtype: bool
        """
        # If notification ways are not enabled for services
        if not self.service_notifications_enabled:
            return False

        # Maybe the command we ask for is not for us, but for another notification ways
        # on the same contact. If so, bail out
        if cmd and cmd not in self.service_notification_commands:
            return False

        # If the business_impact is not high enough, we bail out
        if business_impact < self.min_business_impact:
            return False

        notif_period = timeperiods[self.service_notification_period]
        in_notification_period = notif_period.is_time_valid(timestamp)
        if in_notification_period:
            short_states = {
                u'WARNING': 'w', u'UNKNOWN': 'u', u'CRITICAL': 'c', u'UNREACHABLE': 'x',
                u'RECOVERY': 'r', u'FLAPPING': 'f', u'DOWNTIME': 's'
            }
            if n_type == u'PROBLEM' and state in short_states:
                return short_states[state] in self.service_notification_options
            if n_type == u'RECOVERY' and n_type in short_states:
                return short_states[n_type] in self.service_notification_options
            if n_type == u'ACKNOWLEDGEMENT':
                return in_notification_period
            if n_type in (u'FLAPPINGSTART', u'FLAPPINGSTOP', u'FLAPPINGDISABLED'):
                return 'f' in self.service_notification_options
            if n_type in (u'DOWNTIMESTART', u'DOWNTIMEEND', u'DOWNTIMECANCELLED'):
                # No notification when a downtime was cancelled. Is that true??
                # According to the documentation we need to look at _host_ options
                return 's' in self.host_notification_options

        return False

    def want_host_notification(self, timeperiods, timestamp, state, n_type, business_impact,
                               cmd=None):
        # pylint: disable=too-many-return-statements
        """Check if notification options match the state of the host
        Notification is NOT wanted in ONE of the following case::

        * host notifications are disabled
        * cmd is not in host_notification_commands
        * business_impact < self.min_business_impact
        * host_notification_period is not valid
        * state does not match host_notification_options for problem, recovery, flapping and dt

        :param timeperiods: list of time periods
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
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
        :return: True if no condition is matched, otherwise False
        :rtype: bool
        """
        # If notification ways are not enabled for hosts
        if not self.host_notifications_enabled:
            return False

        # If the business_impact is not high enough, we bail out
        if business_impact < self.min_business_impact:
            return False

        # Maybe the command we ask for are not for us, but for another notification ways
        # on the same contact. If so, bail out
        if cmd and cmd not in self.host_notification_commands:
            return False

        notif_period = timeperiods[self.host_notification_period]
        in_notification_period = notif_period.is_time_valid(timestamp)
        if in_notification_period:
            short_states = {
                u'DOWN': 'd', u'UNREACHABLE': 'u', u'RECOVERY': 'r',
                u'FLAPPING': 'f', u'DOWNTIME': 's'
            }
            if n_type == u'PROBLEM' and state in short_states:
                return short_states[state] in self.host_notification_options
            if n_type == u'RECOVERY' and n_type in short_states:
                return short_states[n_type] in self.host_notification_options
            if n_type == u'ACKNOWLEDGEMENT':
                return in_notification_period
            if n_type in (u'FLAPPINGSTART', u'FLAPPINGSTOP', u'FLAPPINGDISABLED'):
                return 'f' in self.host_notification_options
            if n_type in (u'DOWNTIMESTART', u'DOWNTIMEEND', u'DOWNTIMECANCELLED'):
                return 's' in self.host_notification_options

        return False

    def get_notification_commands(self, o_type):
        """Get notification commands for object type

        :param o_type: object type (host or service)
        :type o_type: str
        :return: command list
        :rtype: list[alignak.objects.command.Command]
        """
        return getattr(self, o_type + '_notification_commands', []) or []

    def is_correct(self):
        # pylint: disable=too-many-branches
        """Check if this object configuration is correct ::

        * Check our own specific properties
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """
        # Internal checks before executing inherited function...

        # Service part
        if self.service_notifications_enabled:
            if getattr(self, 'service_notification_commands', None) is None:
                self.add_warning("do not have any service_notification_commands defined")
                self.service_notification_commands = []
            else:
                for cmd in self.service_notification_commands:
                    if cmd is None:
                        self.add_error("a service_notification_command is missing")
                    elif not cmd.is_valid():
                        self.add_error("a service_notification_command is invalid (%s)" % cmd)

        if getattr(self, 'service_notification_period', None) is None:
            self.add_error("the service_notification_period is invalid")

        # Now host part
        if self.host_notifications_enabled:
            if getattr(self, 'host_notification_commands', None) is None:
                self.add_warning("do not have any host_notification_commands defined")
                self.host_notification_commands = []
            else:
                for cmd in self.host_notification_commands:
                    if cmd is None:
                        self.add_error("a host_notification_command is missing")
                    elif not cmd.is_valid():
                        self.add_error("a host_notification_command is invalid (%s)" % cmd)

        if getattr(self, 'host_notification_period', None) is None:
            self.add_error("the host_notification_period is invalid")

        return super(NotificationWay, self).is_correct() and self.conf_is_correct


class NotificationWays(CommandCallItems):
    """NotificationWays manage a list of NotificationWay objects, used for parsing configuration

    """
    name_property = "notificationway_name"
    inner_class = NotificationWay

    def linkify(self, timeperiods, commands):
        """Create link between objects::

         * notificationways -> timeperiods
         * notificationways -> commands

        :param timeperiods: timeperiods to link
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param commands: commands to link
        :type commands: alignak.objects.command.Commands
        :return: None
        """
        self.linkify_with_timeperiods(timeperiods, 'service_notification_period')
        self.linkify_with_timeperiods(timeperiods, 'host_notification_period')
        self.linkify_with_commands(commands, 'service_notification_commands', is_a_list=True)
        self.linkify_with_commands(commands, 'host_notification_commands', is_a_list=True)
