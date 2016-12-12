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

from alignak.alignakobject import AlignakObject


class Acknowledge(AlignakObject):  # pylint: disable=R0903
    """
    Allows you to acknowledge the current problem for the specified service.
    By acknowledging the current problem, future notifications (for the same
    servicestate) are disabled.
    """

    properties = {
        'uuid': None,
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
    # If the "persistent" option is set to one (1), the comment
    # associated with the acknowledgement will survive across restarts
    # of the Alignak process. If not, the comment will be deleted the
    # next time Alignak restarts.

    def serialize(self, filtered_fields=None):
        """This function serialize into a simple dict object.
        It is used when transferring data to other daemons over the network (http)

        Here we directly return all attributes

        :return: json representation of a Acknowledge
        :rtype: dict
        """
        return {'uuid': self.uuid, 'ref': self.ref, 'sticky': self.sticky, 'notify': self.notify,
                'end_time': self.end_time, 'author': self.author, 'comment': self.comment,
                'persistent': self.persistent
                }
