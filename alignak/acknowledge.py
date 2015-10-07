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
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de

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
"""This module provides Acknowledge class that
implements acknowledgment for notification. Basically used for parsing.

"""


class Acknowledge:
    """
    Allows you to acknowledge the current problem for the specified service.
    By acknowledging the current problem, future notifications (for the same
    servicestate) are disabled.
    """
    _id = 1

    # Just to list the properties we will send as pickle
    # so to others daemons, all but NOT REF
    properties = {
        '_id': None,
        'sticky': None,
        'notify': None,
        'end_time': None,
        'author': None,
        'comment': None,
    }
    # If the "sticky" option is set to one (1), the acknowledgement
    # will remain until the service returns to an OK state. Otherwise
    # the acknowledgement will automatically be removed when the
    # service changes state. In this case Web interfaces set a value
    # of (2).
    #
    # If the "notify" option is set to one (1), a notification will be
    # sent out to contacts indicating that the current service problem
    # has been acknowledged.
    #
    # <WTF??>
    # If the "persistent" option is set to one (1), the comment
    # associated with the acknowledgement will survive across restarts
    # of the Alignak process. If not, the comment will be deleted the
    # next time Alignak restarts. "persistent" not only means "survive
    # restarts", but also
    #
    # => End of comment Missing!!
    # </WTF??>

    def __init__(self, ref, sticky, notify, persistent,
                 author, comment, end_time=0):
        self._id = self.__class__._id
        self.__class__._id += 1
        self.ref = ref  # pointer to srv or host we are applied
        self.sticky = sticky
        self.notify = notify
        self.end_time = end_time
        self.author = author
        self.comment = comment

    def __getstate__(self):
        """Call by pickle for dataify the acknowledge
        because we DO NOT WANT REF in this pickleisation!

        :return: dictionary of properties
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
        """
        Inversed function of getstate

        :param state: it's the state
        :type state: dict
        :return: None
        """
        cls = self.__class__
        self._id = state['_id']
        for prop in cls.properties:
            if prop in state:
                setattr(self, prop, state[prop])
        # If load a old ack, set the end_time to 0 which refers to infinite
        if not hasattr(self, 'end_time'):
            self.end_time = 0
