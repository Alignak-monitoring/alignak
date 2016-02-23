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
        'is_a':             StringProp(default='check'),
        'state':            IntegerProp(default=0),
        'long_output':      StringProp(default=''),
        'depend_on':        ListProp(default=[]),
        'depend_on_me':     ListProp(default=[], split_on_coma=False),
        'perf_data':        StringProp(default=''),
        'check_type':       IntegerProp(default=0),
        'poller_tag':       StringProp(default='None'),
        'internal':         BoolProp(default=False),
        'from_trigger':     BoolProp(default=False),
        'dependency_check': BoolProp(default=False),
    })

    def copy_shell(self):
        """return a copy of the check but just what is important for execution
        So we remove the ref and all

        :return: a copy of check
        :rtype: object
        """
        # We create a dummy check with nothing in it, just defaults values
        return self.copy_shell__(Check({'_id': self._id}))

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
        """Check if the check can be launched

        :param timestamp: time to compare with t_to_go attribute
        :type timestamp: int
        :return: True if t > self.t_to_go, False otherwise
        :rtype: bool
        """
        return timestamp > self.t_to_go

    def __str__(self):
        return "Check %d status:%s command:%s ref:%s" % \
               (self._id, self.status, self.command, self.ref)

    def set_type_active(self):
        """Set check_type attribute to 0

        :return: None
        """
        self.check_type = 0

    def set_type_passive(self):
        """Set check_type attribute to 1

        :return: None
        """
        self.check_type = 1

    def is_dependent(self):
        """Getter for dependency_check attribute

        :return: True if this check was created for dependent one, False otherwise
        :rtype: bool
        """
        return self.dependency_check
