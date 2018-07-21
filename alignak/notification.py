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
#     Frédéric Vachon, fredvac@gmail.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Jan Ulferts, jan.ulferts@xing.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Gerhard Lausser, gerhard.lausser@consol.de

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
"""This module provides Notification class.
Used to define monitoring notifications (email, contacts..)

"""
from six import string_types

from alignak.action import Action
from alignak.brok import Brok
from alignak.property import BoolProp, IntegerProp, StringProp, SetProp, ListProp
from alignak.autoslots import AutoSlots


class Notification(Action):  # pylint: disable=R0902
    """Notification class, inherits from action class. Used to notify contacts
     and execute notification command defined in configuration

    """

    # AutoSlots create the __slots__ with properties and
    # running_properties names
    __metaclass__ = AutoSlots

    my_type = 'notification'

    properties = Action.properties.copy()
    properties.update({
        'is_a':
            StringProp(default=u'notification'),
        'start_time':
            IntegerProp(default=0, fill_brok=['full_status']),
        'end_time':
            IntegerProp(default=0, fill_brok=['full_status']),
        'contact_name':
            StringProp(default=u'', fill_brok=['full_status']),
        'host_name':
            StringProp(default=u'', fill_brok=['full_status']),
        'service_description':
            StringProp(default=u'', fill_brok=['full_status']),
        'reason_type':
            IntegerProp(default=1, fill_brok=['full_status']),
        'state':
            IntegerProp(default=0, fill_brok=['full_status']),
        'ack_author':
            StringProp(default=u'', fill_brok=['full_status']),
        'ack_data':
            StringProp(default=u'', fill_brok=['full_status']),
        'escalated':
            BoolProp(default=False, fill_brok=['full_status']),
        'command_call':
            StringProp(default=None),
        'contact':
            StringProp(default=None),
        'notif_nb':
            IntegerProp(default=1),
        'command':
            StringProp(default=u'UNSET'),
        'enable_environment_macros':
            BoolProp(default=False),
        # Keep a list of currently active escalations
        'already_start_escalations':
            SetProp(default=set()),
        'type':
            StringProp(default=u'PROBLEM'),

        # For authored notifications (eg. downtime...)
        'author':
            StringProp(default=u'n/a', fill_brok=['full_status']),
        'author_name':
            StringProp(default=u'n/a', fill_brok=['full_status']),
        'author_alias':
            StringProp(default=u'n/a', fill_brok=['full_status']),
        'author_comment':
            StringProp(default=u'n/a', fill_brok=['full_status']),

        # All contacts that were notified
        'recipients':
            ListProp(default=[])
    })

    macros = {
        'NOTIFICATIONTYPE':             'type',
        'NOTIFICATIONRECIPIENTS':       'recipients',
        'NOTIFICATIONISESCALATED':      'escalated',
        'NOTIFICATIONAUTHOR':           'author',
        'NOTIFICATIONAUTHORNAME':       'author_name',
        'NOTIFICATIONAUTHORALIAS':      'author_alias',
        'NOTIFICATIONCOMMENT':          'author_comment',
        'NOTIFICATIONNUMBER':           'notif_nb',
        'NOTIFICATIONID':               'uuid',
        'HOSTNOTIFICATIONNUMBER':       'notif_nb',
        'HOSTNOTIFICATIONID':           'uuid',
        'SERVICENOTIFICATIONNUMBER':    'notif_nb',
        'SERVICENOTIFICATIONID':        'uuid'
    }

    def __init__(self, params=None, parsing=False):
        super(Notification, self).__init__(params, parsing=parsing)
        self.fill_default()

    def __str__(self):  # pragma: no cover
        return "Notification %s, item: %s, type: %s, status: %s, command:'%s'" \
               % (self.uuid, self.ref, self.type, self.status, self.command)

    def is_launchable(self, timestamp):
        """Check if this notification can be launched based on current time

        :param timestamp: time to compare
        :type timestamp: int
        :return: True if timestamp >= self.t_to_go, False otherwise
        :rtype: bool
        """
        if self.t_to_go is None:
            return False
        return timestamp >= self.t_to_go

    def is_administrative(self):
        """Check if this notification is "administrative"

        :return: True in type not in ('PROBLEM', 'RECOVERY'), False otherwise
        :rtype: bool
        """
        if self.type in ('PROBLEM', 'RECOVERY'):
            return False

        return True

    def get_return_from(self, notif):
        """Setter of exit_status and execution_time attributes

        :param notif: notification to get data from
        :type notif: alignak.notification.Notification
        :return: None
        """
        self.exit_status = notif.exit_status
        self.execution_time = notif.execution_time

    def fill_data_brok_from(self, data, brok_type):
        """Fill data with info of item by looking at brok_type
        in props of properties or running_properties

        :param data: data to fill
        :type data:
        :param brok_type: type of brok
        :type brok_type:
        :return: brok with wanted data
        :rtype: alignak.brok.Brok
        """
        cls = self.__class__
        # Now config properties
        for prop, entry in list(cls.properties.items()):
            if brok_type in entry.fill_brok:
                data[prop] = getattr(self, prop)

    def get_initial_status_brok(self):
        """Get a initial status brok

        :return: brok with wanted data
        :rtype: alignak.brok.Brok
        """
        data = {'uuid': self.uuid}
        self.fill_data_brok_from(data, 'full_status')
        return Brok({'type': 'notification_raise', 'data': data})

    def serialize(self):
        """This function serialize into a simple dict object.
        It is used when transferring data to other daemons over the network (http)

        Here we directly return all attributes

        :return: json representation of a Timeperiod
        :rtype: dict
        """
        res = super(Notification, self).serialize()

        if res['command_call'] is not None:
            if not isinstance(res['command_call'], string_types) and \
                    not isinstance(res['command_call'], dict):
                res['command_call'] = res['command_call'].serialize()
        return res
