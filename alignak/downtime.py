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
#     xkilian, fmikus@acktomic.com
#     Romain LE DISEZ, romain.git@ledisez.net
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
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
"""This modules provides Downtime class, used to implements downtime monitoring concept.
See detailed concepts below

"""
import datetime
import time
import warnings
from alignak.comment import Comment
from alignak.property import BoolProp, IntegerProp, StringProp
from alignak.brok import Brok
from alignak.log import logger


class Downtime:
    """ Schedules downtime for a specified service. If the "fixed" argument is set
    to one (1), downtime will start and end at the times specified by the
    "start" and "end" arguments.
    Otherwise, downtime will begin between the "start" and "end" times and last
    for "duration" seconds. The "start" and "end" arguments are specified
    in time_t format (seconds since the UNIX epoch). The specified service
    downtime can be triggered by another downtime entry if the "trigger_id"
    is set to the ID of another scheduled downtime entry.
    Set the "trigger_id" argument to zero (0) if the downtime for the
    specified service should not be triggered by another downtime entry.

    """
    _id = 1

    # Just to list the properties we will send as pickle
    # so to others daemons, so all but NOT REF
    properties = {
        'activate_me': StringProp(default=[]),
        'entry_time': IntegerProp(default=0, fill_brok=['full_status']),
        'fixed': BoolProp(default=True, fill_brok=['full_status']),
        'start_time': IntegerProp(default=0, fill_brok=['full_status']),
        'duration': IntegerProp(default=0, fill_brok=['full_status']),
        'trigger_id': IntegerProp(default=0),
        'end_time': IntegerProp(default=0, fill_brok=['full_status']),
        'real_end_time': IntegerProp(default=0),
        'author': StringProp(default='', fill_brok=['full_status']),
        'comment': StringProp(default=''),
        'is_in_effect': BoolProp(default=False),
        'has_been_triggered': BoolProp(default=False),
        'can_be_deleted': BoolProp(default=False),

        # TODO: find a very good way to handle the downtime "ref".
        # ref must effectively not be in properties because it points
        # onto a real object.
        # 'ref': None
    }

    def __init__(self, ref, start_time, end_time, fixed, trigger_id, duration, author, comment):
        now = datetime.datetime.now()
        self._id = int(time.mktime(now.timetuple()) * 1e6 + now.microsecond)
        self.__class__._id = self._id + 1
        self.ref = ref  # pointer to srv or host we are apply
        self.activate_me = []  # The other downtimes i need to activate
        self.entry_time = int(time.time())
        self.fixed = fixed
        self.start_time = start_time
        self.duration = duration
        self.trigger_id = trigger_id
        if self.trigger_id != 0:  # triggered plus fixed makes no sense
            self.fixed = False
        self.end_time = end_time
        if fixed:
            self.duration = end_time - start_time
        # This is important for flexible downtimes. Here start_time and
        # end_time mean: in this time interval it is possible to trigger
        # the beginning of the downtime which lasts for duration.
        # Later, when a non-ok event happens, real_end_time will be
        # recalculated from now+duration
        # end_time will be displayed in the web interface, but real_end_time
        # is used internally
        self.real_end_time = end_time
        self.author = author
        self.comment = comment
        self.is_in_effect = False
        # fixed: start_time has been reached,
        # flexible: non-ok checkresult

        self.has_been_triggered = False  # another downtime has triggered me
        self.can_be_deleted = False
        self.add_automatic_comment()

    def __str__(self):
        if self.is_in_effect is True:
            active = "active"
        else:
            active = "inactive"
        if self.fixed is True:
            d_type = "fixed"
        else:
            d_type = "flexible"
        return "%s %s Downtime id=%d %s - %s" % (
            active, d_type, self._id, time.ctime(self.start_time), time.ctime(self.end_time))

    @property
    def id(self):  # pylint: disable=C0103
        """Getter for id, raise deprecation warning

        :return: self._id
        """
        warnings.warn("Access to deprecated attribute id %s Item class" % self.__class__,
                      DeprecationWarning, stacklevel=2)
        return self._id

    @id.setter
    def id(self, value):  # pylint: disable=C0103
        """Setter for id, raise deprecation warning

        :param value: value to set
        :return: None
        """
        warnings.warn("Access to deprecated attribute id of %s class" % self.__class__,
                      DeprecationWarning, stacklevel=2)
        self._id = value

    def trigger_me(self, other_downtime):
        """Wrapper to activate_me.append function
        Used to add another downtime to activate

        :param other_downtime: other downtime to activate/cancel
        :type other_downtime:
        :return: None
        """
        self.activate_me.append(other_downtime)

    def in_scheduled_downtime(self):
        """Getter for is_in_effect attribute

        :return: True if downtime is in effect, False otherwise
        :rtype: bool
        """
        return self.is_in_effect

    def enter(self):
        """Set ref in scheduled downtime and raise downtime log entry (start)

        :return: [], always
        :rtype: list
        TODO: res is useless
        """
        res = []
        self.is_in_effect = True
        if self.fixed is False:
            now = time.time()
            self.real_end_time = now + self.duration
        if self.ref.scheduled_downtime_depth == 0:
            self.ref.raise_enter_downtime_log_entry()
            self.ref.create_notifications('DOWNTIMESTART')
        self.ref.scheduled_downtime_depth += 1
        self.ref.in_scheduled_downtime = True
        for downtime in self.activate_me:
            res.extend(downtime.enter())
        return res

    def exit(self):
        """Remove ref in scheduled downtime and raise downtime log entry (exit)

        :return: [], always | None
        :rtype: list
        TODO: res is useless
        """
        res = []
        if self.is_in_effect is True:
            # This was a fixed or a flexible+triggered downtime
            self.is_in_effect = False
            self.ref.scheduled_downtime_depth -= 1
            if self.ref.scheduled_downtime_depth == 0:
                self.ref.raise_exit_downtime_log_entry()
                self.ref.create_notifications('DOWNTIMEEND')
                self.ref.in_scheduled_downtime = False
        else:
            # This was probably a flexible downtime which was not triggered
            # In this case it silently disappears
            pass
        self.del_automatic_comment()
        self.can_be_deleted = True
        # when a downtime ends and the service was critical
        # a notification is sent with the next critical check
        # So we should set a flag here which signals consume_result
        # to send a notification
        self.ref.in_scheduled_downtime_during_last_check = True
        return res

    def cancel(self):
        """Remove ref in scheduled downtime and raise downtime log entry (cancel)

        :return: [], always
        :rtype: list
        TODO: res is useless
        """
        res = []
        self.is_in_effect = False
        self.ref.scheduled_downtime_depth -= 1
        if self.ref.scheduled_downtime_depth == 0:
            self.ref.raise_cancel_downtime_log_entry()
            self.ref.in_scheduled_downtime = False
        self.del_automatic_comment()
        self.can_be_deleted = True
        self.ref.in_scheduled_downtime_during_last_check = True
        # Nagios does not notify on canceled downtimes
        # res.extend(self.ref.create_notifications('DOWNTIMECANCELLED'))
        # Also cancel other downtimes triggered by me
        for downtime in self.activate_me:
            res.extend(downtime.cancel())
        return res

    def add_automatic_comment(self):
        """Add comment on ref for downtime

        :return: None
        """
        if self.fixed is True:
            text = (
                "This %s has been scheduled for fixed downtime from %s to %s. "
                "Notifications for the %s will not be sent out during that time period." % (
                    self.ref.my_type,
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.start_time)),
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.end_time)),
                    self.ref.my_type)
            )
        else:
            hours, remainder = divmod(self.duration, 3600)
            minutes, seconds = divmod(remainder, 60)
            text = ("This %s has been scheduled for flexible downtime starting between %s and %s "
                    "and lasting for a period of %d hours and %d minutes. "
                    "Notifications for the %s will not be sent out during that time period." % (
                        self.ref.my_type,
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.start_time)),
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.end_time)),
                        hours, minutes, self.ref.my_type)
                    )
        if self.ref.my_type == 'host':
            comment_type = 1
        else:
            comment_type = 2
        comm = Comment(self.ref, False, "(Nagios Process)", text, comment_type, 2, 0, False, 0)
        self.comment_id = comm._id
        self.extra_comment = comm
        self.ref.add_comment(comm)

    def del_automatic_comment(self):
        """Remove automatic comment on ref previously created

        :return: None
        """
        # Extra comment can be None if we load it from a old version of Alignak
        # TODO: remove it in a future version when every one got upgrade
        if self.extra_comment is not None:
            self.extra_comment.can_be_deleted = True
        # self.ref.del_comment(self.comment_id)

    def fill_data_brok_from(self, data, brok_type):
        """Fill data with info of item by looking at brok_type
        in props of properties or running_properties

        :param data: data to fill
        :type data:
        :param brok_type: type of brok
        :type brok_type: str
        :return: None
        TODO: Duplicate from Notification.fill_data_brok_from
        """
        cls = self.__class__
        # Now config properties
        for prop, entry in cls.properties.items():
            if hasattr(prop, 'fill_brok'):
                if brok_type in entry['fill_brok']:
                    data[prop] = getattr(self, prop)

    def get_initial_status_brok(self):
        """Get a initial status brok

        :return: brok with wanted data
        :rtype: alignak.brok.Brok
        TODO: Duplicate from Notification.fill_data_brok_from
        """
        data = {'_id': self._id}

        self.fill_data_brok_from(data, 'full_status')
        brok = Brok('downtime_raise', data)
        return brok

    def __getstate__(self):
        """Call by pickle for dataify the comment
        because we DO NOT WANT REF in this pickleisation!

        :return: dict containing notification data
        :rtype: dict
        TODO: REMOVE THIS
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
        TODO: REMOVE THIS
        """
        cls = self.__class__

        # Maybe it's not a dict but a list like in the old 0.4 format
        # so we should call the 0.4 function for it
        if isinstance(state, list):
            self.__setstate_deprecated__(state)
            return

        self._id = state['_id']
        for prop in cls.properties:
            if prop in state:
                setattr(self, prop, state[prop])

        if self._id >= cls._id:
            cls._id = self._id + 1

    def __setstate_deprecated__(self, state):
        """In 1.0 we move to a dict save.

        :param state: it's the state
        :type state: dict
        :return: None
        TODO: REMOVE THIS"""
        cls = self.__class__
        # Check if the len of this state is like the previous,
        # if not, we will do errors!
        # -1 because of the '_id' prop
        if len(cls.properties) != (len(state) - 1):
            logger.info("Passing downtime")
            return

        self._id = state.pop()
        for prop in cls.properties:
            val = state.pop()
            setattr(self, prop, val)
        if self._id >= cls._id:
            cls._id = self._id + 1
