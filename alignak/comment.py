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
    It contains data like author, type etc..
    """

    my_type = 'comment'
    properties = {
        'entry_time':
            IntegerProp(default=0),
        'entry_type':
            IntegerProp(),
        'author':
            StringProp(default=u'Alignak'),
        'comment':
            StringProp(default=u''),
        'comment_type':
            IntegerProp(),
        'source':
            IntegerProp(default=0),
        'expires':
            BoolProp(default=False),
        'ref':
            StringProp(default=u'unset'),
        'ref_type':
            StringProp(default=u'unset'),
    }

    def __init__(self, params, parsing=False):
        """Adds a comment to a particular service.

        :param ref: reference object (host / service)
        :type ref: alignak.object.schedulingitem.SchedulingItem
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
        :return: None
        """
        super(Comment, self).__init__(params, parsing)

        if not hasattr(self, 'entry_time'):
            self.entry_time = int(time.time())

        self.fill_default()

    def __str__(self):  # pragma: no cover
        return "Comment id=%s %s" % (self.uuid, self.comment)
