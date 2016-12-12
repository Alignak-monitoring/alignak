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
from alignak.alignakobject import AlignakObject
from alignak.property import StringProp, BoolProp, IntegerProp


class Comment(AlignakObject):
    """Comment class implements comments for monitoring purpose.
    It contains data like author, type, expire_time, persistent etc..
    """

    properties = AlignakObject.properties.copy()
    properties.update({
        'entry_time':
            IntegerProp(default=0),
        'persistent':
            BoolProp(),
        'author':
            StringProp(default='(Alignak)'),
        'comment':
            StringProp(default='Automatic Comment'),
        'comment_type':
            IntegerProp(),
        'entry_type':
            IntegerProp(),
        'source':
            IntegerProp(),
        'expires':
            BoolProp(),
        'expire_time':
            IntegerProp(),
        'can_be_deleted':
            BoolProp(default=False),
        'ref':
            StringProp(default='')
    })

    def __init__(self, params):
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

                          * 1 <=>USER_COMMENT
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
        if 'uuid' not in params:
            super(Comment, self).__init__(params)
            self.fill_default(which_properties="properties")

        # Update my properties with provided parameters
        for prop in self.__class__.properties:
            if prop in params:
                setattr(self, prop, params[prop])

        if 'uuid' not in params:
            # Comment creation
            if self.entry_time == 0:
                self.entry_time = int(time.time())

    def __str__(self):
        return "Comment id=%s, '%s'" % (self.uuid, self.comment)
