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
import logging

from alignak.alignakobject import AlignakObject
from alignak.property import BoolProp, IntegerProp, StringProp

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class ContactDowntime(AlignakObject):
    """ContactDowntime class allows a contact to be in downtime. During this time
    the contact won't get notifications

    """

    properties = {
        'start_time':
            IntegerProp(default=0, fill_brok=['full_status']),
        'end_time':
            IntegerProp(default=0, fill_brok=['full_status']),
        'author':
            StringProp(default=u'', fill_brok=['full_status']),
        'comment':
            StringProp(default=u''),
        'is_in_effect':
            BoolProp(default=False),
        'can_be_deleted':
            BoolProp(default=False),
        'ref':
            StringProp(default=u''),

    }

    # Schedule a contact downtime. It's far more easy than a host/service
    # one because we got a beginning, and an end. That's all for running.
    # got also an author and a comment for logging purpose.
    def __init__(self, params, parsing=False):
        super(ContactDowntime, self).__init__(params, parsing=parsing)

        self.fill_default()

    def check_activation(self, contacts):
        """Enter or exit downtime if necessary

        :return: None
        """
        now = time.time()
        was_is_in_effect = self.is_in_effect
        self.is_in_effect = (self.start_time <= now <= self.end_time)

        # Raise a log entry when we get in the downtime
        if not was_is_in_effect and self.is_in_effect:
            self.enter(contacts)

        # Same for exit purpose
        if was_is_in_effect and not self.is_in_effect:
            self.exit(contacts)

    def in_scheduled_downtime(self):
        """Getter for is_in_effect attribute

        :return: True if downtime is active, False otherwise
        :rtype: bool
        """
        return self.is_in_effect

    def enter(self, contacts):
        """Wrapper to call raise_enter_downtime_log_entry for ref (host/service)

        :return: None
        """
        contact = contacts[self.ref]
        contact.raise_enter_downtime_log_entry()

    def exit(self, contacts):
        """Wrapper to call raise_exit_downtime_log_entry for ref (host/service)
        set can_be_deleted to True

        :return: None
        """
        contact = contacts[self.ref]
        contact.raise_exit_downtime_log_entry()
        self.can_be_deleted = True

    def cancel(self, contacts):
        """Wrapper to call raise_cancel_downtime_log_entry for ref (host/service)
        set can_be_deleted to True
        set is_in_effect to False

        :return: None
        """
        self.is_in_effect = False
        contact = contacts[self.ref]
        contact.raise_cancel_downtime_log_entry()
        self.can_be_deleted = True
