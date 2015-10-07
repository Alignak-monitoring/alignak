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
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
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
"""This module provide Comment class, used to attach comments to hosts / services"""
import time
import warnings


class Comment:
    """Comment class implements comments for monitoring purpose.
    It contains data like author, type, expire_time, persistent etc..
    """
    _id = 1

    properties = {
        'entry_time':   None,
        'persistent':   None,
        'author':       None,
        'comment':      None,
        'comment_type': None,
        'entry_type':   None,
        'source':       None,
        'expires':      None,
        'expire_time':  None,
        'can_be_deleted': None,

        # TODO: find a very good way to handle the downtime "ref".
        # ref must effectively not be in properties because it points
        # onto a real object.
        # 'ref':  None
    }

    def __init__(self, ref, persistent, author, comment, comment_type, entry_type, source, expires,
                 expire_time):
        """Adds a comment to a particular service. If the "persistent" field
        is set to zero (0), the comment will be deleted the next time
        Alignak is restarted. Otherwise, the comment will persist
        across program restarts until it is deleted manually.

        :param ref: reference object (host / service)
        :type ref: alignak.object.schedulingitem.SchedulingItem
        :param persistent: comment is persistent or not (stay after reboot)
        :type persistent: bool
        :param author: Author of this comment
        :type author: str
        :param comment: text comment itself
        :type comment: str
        :param comment_type: comment type ::

                            * 1 <=> HOST_COMMENT
                            * 2 <=> SERVICE_COMMENT

        :type comment_type: int
        :param entry_type: type of entry linked to this comment ::

                          * 1 <=> USER_COMMENT
                          * 2 <=>DOWNTIME_COMMENT
                          * 3 <=>FLAPPING_COMMENT
                          * 4 <=>ACKNOWLEDGEMENT_COMMENT

        :type entry_type: int
        :param source: source of this comment ::

                      * 0 <=> COMMENTSOURCE_INTERNAL
                      * 1 <=> COMMENTSOURCE_EXTERNAL

        :type source: int
        :param expires: comment expires or not
        :type expires: bool
        :param expire_time: time of expiration
        :type expire_time: int
        :return: None
        """
        self._id = self.__class__._id
        self.__class__._id += 1
        self.ref = ref  # pointer to srv or host we are apply
        self.entry_time = int(time.time())
        self.persistent = persistent
        self.author = author
        self.comment = comment
        # Now the hidden attributes
        # HOST_COMMENT=1,SERVICE_COMMENT=2
        self.comment_type = comment_type
        # USER_COMMENT=1,DOWNTIME_COMMENT=2,FLAPPING_COMMENT=3,ACKNOWLEDGEMENT_COMMENT=4
        self.entry_type = entry_type
        # COMMENTSOURCE_INTERNAL=0,COMMENTSOURCE_EXTERNAL=1
        self.source = source
        self.expires = expires
        self.expire_time = expire_time
        self.can_be_deleted = False

    def __str__(self):
        return "Comment id=%d %s" % (self._id, self.comment)

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

    def __getstate__(self):
        """Call by pickle to dataify the comment
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
        """Inverted function of getstate

        :param state: it's the state
        :type state: dict
        :return: None
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

        # to prevent from duplicating id in comments:
        if self._id >= cls._id:
            cls._id = self._id + 1

    def __setstate_deprecated__(self, state):
        """In 1.0 we move to a dict save.

        :param state: it's the state
        :type state: dict
        :return: None
        """
        cls = self.__class__
        # Check if the len of this state is like the previous,
        # if not, we will do errors!
        # -1 because of the '_id' prop
        if len(cls.properties) != (len(state) - 1):
            self.debug("Passing comment")
            return

        self._id = state.pop()
        for prop in cls.properties:
            val = state.pop()
            setattr(self, prop, val)
        if self._id >= cls._id:
            cls._id = self._id + 1
