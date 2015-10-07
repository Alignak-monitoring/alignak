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
import time

from alignak.action import Action
from alignak.brok import Brok
from alignak.property import BoolProp, IntegerProp, StringProp, FloatProp
from alignak.autoslots import AutoSlots


class Notification(Action):
    """Notification class, inherits from action class. Used to notify contacts
     and execute notification command defined in configuration

    """

    # AutoSlots create the __slots__ with properties and
    # running_properties names
    __metaclass__ = AutoSlots

    my_type = 'notification'

    properties = Action.properties.copy()
    properties.update({
        'is_a':                StringProp(default='notification'),
        'notification_type':   IntegerProp(default=0, fill_brok=['full_status']),
        'start_time':          IntegerProp(default=0, fill_brok=['full_status']),
        'end_time':            IntegerProp(default=0, fill_brok=['full_status']),
        'contact_name':        StringProp(default='', fill_brok=['full_status']),
        'host_name':           StringProp(default='', fill_brok=['full_status']),
        'service_description': StringProp(default='', fill_brok=['full_status']),
        'reason_type':         IntegerProp(default=0, fill_brok=['full_status']),
        'state':               IntegerProp(default=0, fill_brok=['full_status']),
        'output':              StringProp(default='', fill_brok=['full_status']),
        'ack_author':          StringProp(default='', fill_brok=['full_status']),
        'ack_data':            StringProp(default='', fill_brok=['full_status']),
        'escalated':           BoolProp(default=False, fill_brok=['full_status']),
        'contacts_notified':   IntegerProp(default=0, fill_brok=['full_status']),
        'command_call':        StringProp(default=None),
        'contact':             StringProp(default=None),
        'notif_nb':            IntegerProp(default=0),
        'status':              StringProp(default='scheduled'),
        'command':             StringProp(default=''),
        'sched_id':            IntegerProp(default=0),
        'timeout':             IntegerProp(default=10),
        'module_type':         StringProp(default='fork', fill_brok=['full_status']),
        'creation_time':       FloatProp(default=0),
        'enable_environment_macros': BoolProp(default=False),
        # Keep a list of currently active escalations
        'already_start_escalations':  StringProp(default=set()),
    })

    macros = {
        'NOTIFICATIONTYPE':         'type',
        'NOTIFICATIONRECIPIENTS':   'recipients',
        'NOTIFICATIONISESCALATED':  'escalated',
        'NOTIFICATIONAUTHOR':       'author',
        'NOTIFICATIONAUTHORNAME':   'author_name',
        'NOTIFICATIONAUTHORALIAS':  'author_alias',
        'NOTIFICATIONCOMMENT':      'comment',
        'HOSTNOTIFICATIONNUMBER':   'notif_nb',
        'HOSTNOTIFICATIONID':       '_id',
        'SERVICENOTIFICATIONNUMBER': 'notif_nb',
        'SERVICENOTIFICATIONID':    '_id'
    }

    def __init__(self, _type='PROBLEM', status='scheduled', command='UNSET',
                 command_call=None, ref=None, contact=None, t_to_go=0.0,
                 contact_name='', host_name='', service_description='',
                 reason_type=1, state=0, ack_author='', ack_data='',
                 escalated=False, contacts_notified=0,
                 start_time=0, end_time=0, notification_type=0, _id=None,
                 notif_nb=1, timeout=10, env={}, module_type='fork',
                 reactionner_tag='None', enable_environment_macros=False):

        self.is_a = 'notification'
        self.type = _type
        if _id is None:  # _id != None is for copy call only
            self._id = Action._id
            Action._id += 1
        self._in_timeout = False
        self.timeout = timeout
        self.status = status
        self.exit_status = 3
        self.command = command
        self.command_call = command_call
        self.output = None
        self.execution_time = 0.0
        self.u_time = 0.0  # user executon time
        self.s_time = 0.0  # system execution time

        self.ref = ref

        # Set host_name and description from the ref
        try:
            self.host_name = self.ref.host_name
        except Exception:
            self.host_name = host_name
        try:
            self.service_description = self.ref.service_description
        except Exception:
            self.service_description = service_description

        self.env = env
        self.module_type = module_type
        self.t_to_go = t_to_go
        self.notif_nb = notif_nb
        self.contact = contact

        # For brok part
        self.contact_name = contact_name
        self.reason_type = reason_type
        self.state = state
        self.ack_author = ack_author
        self.ack_data = ack_data
        self.escalated = escalated
        self.contacts_notified = contacts_notified
        self.start_time = start_time
        self.end_time = end_time
        self.notification_type = notification_type

        self.creation_time = time.time()
        self.worker = 'none'
        self.reactionner_tag = reactionner_tag
        self.already_start_escalations = set()
        self.enable_environment_macros = enable_environment_macros

    def copy_shell(self):
        """Get a copy o this notification with minimal values (default + id)

        :return: new notification
        :rtype: alignak.notification.Notification
        """
        # We create a dummy check with nothing in it, just defaults values
        return self.copy_shell__(Notification('', '', '', '', '', '', '', _id=self._id))

    def is_launchable(self, timestamp):
        """Check if this notification can be launched base on time

        :param timestamp: time to compare
        :type timestamp: int
        :return: True if timestamp >= self.t_to_go, False otherwise
        :rtype: bool
        """
        return timestamp >= self.t_to_go

    def is_administrative(self):
        """Check if this notification is "administrative"

        :return: True in type not in ('PROBLEM', 'RECOVERY'), False otherwise
        :rtype: bool
        """
        if self.type in ('PROBLEM', 'RECOVERY'):
            return False
        else:
            return True

    def __str__(self):
        return "Notification %d status:%s command:%s ref:%s t_to_go:%s" % \
               (self._id, self.status, self.command, getattr(self, 'ref', 'unknown'),
                time.asctime(time.localtime(self.t_to_go)))

    def get_id(self):
        """Getter to id attribute

        :return: notification id
        :rtype: int
        """
        return self._id

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
        for prop, entry in cls.properties.items():
            if brok_type in entry.fill_brok:
                data[prop] = getattr(self, prop)

    def get_initial_status_brok(self):
        """Get a initial status brok

        :return: brok with wanted data
        :rtype: alignak.brok.Brok
        """
        data = {'_id': self._id}

        self.fill_data_brok_from(data, 'full_status')
        brok = Brok('notification_raise', data)
        return brok

    def __getstate__(self):
        """Call by pickle for dataify the comment
        because we DO NOT WANT REF in this pickleisation!

        :return: dict containing notification data
        :rtype: dict
        """
        cls = self.__class__
        # id is not in *_properties
        res = {'_id': self._id}
        for prop in cls.properties:
            if hasattr(self, prop):
                res[prop] = getattr(self, prop)

        return res

    def __setstate__(self, state):
        """Inverted function of getstate

        :param state: state to restore
        :type state: dict
        :return: None
        """
        cls = self.__class__
        self._id = state['_id']
        for prop in cls.properties:
            if prop in state:
                setattr(self, prop, state[prop])
        # Hook for load of 0.4 notification: there were no
        # creation time, must put one
        if not hasattr(self, 'creation_time'):
            self.creation_time = time.time()
        if not hasattr(self, 'reactionner_tag'):
            self.reactionner_tag = 'None'
        if not hasattr(self, 'worker'):
            self.worker = 'none'
        if not getattr(self, 'module_type', None):
            self.module_type = 'fork'
        if not hasattr(self, 'already_start_escalations'):
            self.already_start_escalations = set()
        if not hasattr(self, 'execution_time'):
            self.execution_time = 0
        # s_time and u_time are added between 1.2 and 1.4
        if not hasattr(self, 'u_time'):
            self.u_time = 0.0
            self.s_time = 0.0
