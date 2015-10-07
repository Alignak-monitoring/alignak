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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com

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
"""This module provides ContactDowntime class which implement downtime for contact

"""
import time
from alignak.log import logger


class ContactDowntime:
    """ContactDowntime class allows a contact to be in downtime. During this time
    the contact won't get notifications

    """
    _id = 1

    # Just to list the properties we will send as pickle
    # so to others daemons, so all but NOT REF
    properties = {
        # 'activate_me':  None,
        # 'entry_time':   None,
        # 'fixed':        None,
        'start_time':   None,
        # 'duration':     None,
        # 'trigger_id':   None,
        'end_time':     None,
        # 'real_end_time': None,
        'author':       None,
        'comment':      None,
        'is_in_effect': None,
        # 'has_been_triggered': None,
        'can_be_deleted': None,
    }

    # Schedule a contact downtime. It's far more easy than a host/service
    # one because we got a beginning, and an end. That's all for running.
    # got also an author and a comment for logging purpose.
    def __init__(self, ref, start_time, end_time, author, comment):
        self._id = self.__class__._id
        self.__class__._id += 1
        self.ref = ref  # pointer to srv or host we are apply
        self.start_time = start_time
        self.end_time = end_time
        self.author = author
        self.comment = comment
        self.is_in_effect = False
        self.can_be_deleted = False
        # self.add_automatic_comment()

    def check_activation(self):
        """Enter or exit downtime if necessary

        :return: None
        """
        now = time.time()
        was_is_in_effect = self.is_in_effect
        self.is_in_effect = (self.start_time <= now <= self.end_time)
        logger.info("CHECK ACTIVATION:%s", self.is_in_effect)

        # Raise a log entry when we get in the downtime
        if not was_is_in_effect and self.is_in_effect:
            self.enter()

        # Same for exit purpose
        if was_is_in_effect and not self.is_in_effect:
            self.exit()

    def in_scheduled_downtime(self):
        """Getter for is_in_effect attribute

        :return: True if downtime is active, False otherwise
        :rtype: bool
        """
        return self.is_in_effect

    def enter(self):
        """Wrapper to call raise_enter_downtime_log_entry for ref (host/service)

        :return: None
        """
        self.ref.raise_enter_downtime_log_entry()

    def exit(self):
        """Wrapper to call raise_exit_downtime_log_entry for ref (host/service)
        set can_be_deleted to True

        :return: None
        """
        self.ref.raise_exit_downtime_log_entry()
        self.can_be_deleted = True

    def cancel(self):
        """Wrapper to call raise_cancel_downtime_log_entry for ref (host/service)
        set can_be_deleted to True
        set is_in_effect to False

        :return: None
        """
        self.is_in_effect = False
        self.ref.raise_cancel_downtime_log_entry()
        self.can_be_deleted = True

    def __getstate__(self):
        """Call by pickle to dataify the comment
        because we DO NOT WANT REF in this pickleisation!

        :return: data pickled
        :rtype: list
        """
        # print "Asking a getstate for a downtime on", self.ref.get_dbg_name()
        cls = self.__class__
        # id is not in *_properties
        res = [self._id]
        for prop in cls.properties:
            res.append(getattr(self, prop))
        # We reverse because we want to recreate
        # By check at properties in the same order
        res.reverse()
        return res

    def __setstate__(self, state):
        """Inverted function of getstate

        :param state: state to set
        :type state: list
        :return: None
        """
        cls = self.__class__
        self._id = state.pop()
        for prop in cls.properties:
            val = state.pop()
            setattr(self, prop, val)
        if self._id >= cls._id:
            cls._id = self._id + 1
