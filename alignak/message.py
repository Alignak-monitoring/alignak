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
#     Jean Gabes, naparuba@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Sebastien Coavoux, s.coavoux@free.fr

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
"""This module provides Message class. Used for communication between daemon process (with queues)

"""


class Message(object):
    """This is a simple message class for communications between actionners and workers"""

    # Auto generated identifiers
    _id = 0

    my_type = 'message'
    _type = None
    _data = None
    _from = None

    def __init__(self, _type, data=None, source=None):
        cls = self.__class__
        self._id = cls._id
        cls._id += 1

        self._type = _type
        self._data = data
        self._source = source

    def get_type(self):
        """Getter of _type attribute

        :return: Message type
        :rtype: str
        """
        return self._type

    def get_data(self):
        """Getter of _data attribute

        :return: Message data
        :rtype: str
        """
        return self._data

    def get_source(self):
        """Getter of _source attribute

        :return: Message from (actionner/worker name)
        :rtype: str
        """
        return self._source

    def __str__(self):  # pragma: no cover
        """String representation of message

        :return: source - id, type: %s, data: %s
        :rtype: str
        """
        return "%s - %s, type: %s, data: %s" % (self._source, self._id, self._type, self._data)
