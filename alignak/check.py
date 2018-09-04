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
#     aviau, alexandre.viau@savoirfairelinux.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Zoran Zaric, zz@zoranzaric.de
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Olivier Hanesse, olivier.hanesse@gmail.com
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
"""This module provides Check class which is a simple abstraction for monitoring checks

"""
from alignak.action import Action
from alignak.property import BoolProp, IntegerProp, ListProp
from alignak.property import StringProp


class Check(Action):  # pylint: disable=R0902
    """Check class implements monitoring concepts of checks :(status, state, output)
    Check instance are used to store monitoring plugins data (exit status, output)
    and used by schedule to raise alert, reschedule check etc.

    """
    # AutoSlots create the __slots__ with properties and
    # running_properties names

    # FIXME : re-enable AutoSlots if possible
    # __metaclass__ = AutoSlots

    my_type = 'check'

    properties = Action.properties.copy()
    properties.update({
        'is_a':
            StringProp(default=u'check'),
        'state':
            IntegerProp(default=0),
        'depend_on':
            ListProp(default=[]),
        'depend_on_me':
            ListProp(default=[], split_on_comma=False),
        'passive_check':
            BoolProp(default=False),
        'freshness_expiry_check':
            BoolProp(default=False),
        'poller_tag':
            StringProp(default=u'None'),
        'dependency_check':
            BoolProp(default=False),
    })

    def __init__(self, params=None, parsing=False):
        super(Check, self).__init__(params, parsing=parsing)

        if self.command.startswith('_'):
            self.internal = True

    def __str__(self):  # pragma: no cover
        return "Check %s %s, item: %s, status: %s, command:'%s'" % \
               (self.uuid, "active" if not self.passive_check else "passive",
                self.ref, self.status, self.command)

    def get_return_from(self, check):
        """Update check data from action (notification for instance)

        :param check: action to get data from
        :type check: alignak.action.Action
        :return: None
        """
        for prop in ['exit_status', 'output', 'long_output', 'check_time', 'execution_time',
                     'perf_data', 'u_time', 's_time']:
            setattr(self, prop, getattr(check, prop))

    def is_launchable(self, timestamp):
        """Check if this check can be launched based on current time

        :param timestamp: time to compare
        :type timestamp: int
        :return: True if timestamp >= self.t_to_go, False otherwise
        :rtype: bool
        """
        if self.t_to_go is None:
            return False
        return timestamp >= self.t_to_go

    def set_type_active(self):
        """Set this check as an active one (indeed, not passive)

        :return: None
        """
        self.passive_check = False

    def set_type_passive(self):
        """Set this check as a passive one

        :return: None
        """
        self.passive_check = True

    def is_dependent(self):
        """Getter for dependency_check attribute

        :return: True if this check was created for a dependent one, False otherwise
        :rtype: bool
        """
        return self.dependency_check

    def serialize(self):
        """This function serializes into a simple dict object.

        The only usage is to send to poller, and it does not need to have the
        depend_on and depend_on_me properties.

        :return: json representation of a Check
        :rtype: dict
        """
        res = super(Check, self).serialize()
        if 'depend_on' in res:
            del res['depend_on']
        if 'depend_on_me' in res:
            del res['depend_on_me']
        return res
