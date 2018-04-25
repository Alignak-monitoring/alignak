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
"""
This module provide a simple abstraction for load computation in satellite
"""
import time
import math


class Load(object):
    """This class is for having a easy Load calculation
    without having to send value at regular interval
    (but it's more efficient if you do this :) ) and without
    having a list or other stuff. It's just an object, an update and a get
    You can define mins: the average for mins minutes. The val is
    the initial value. It's better if it's 0 but you can choose.

    """

    def __init__(self, mins=1, initial_value=0):
        self.exp = 0  # first exp
        self.mins = mins  # Number of minute of the avg
        self.last_update = 0  # last update of the value
        self.load = initial_value  # first value

    def update_load(self, sleep_time):
        """Update load with the new value

        :param sleep_time: value used to compute new load
        :type sleep_time: int
        :return: None
        """
        # The first call do not change the value, just tag the beginning of last_update
        # IF  we force : bail out all time thing
        if not self.last_update:
            self.last_update = time.time()
            return

        now = time.time()
        try:
            difference = now - self.last_update
            self.exp = 1 / math.exp(difference / (self.mins * 60.0))

            self.load = sleep_time + self.exp * (self.load - sleep_time)
            self.last_update = now
        except OverflowError:  # if the time change without notice, we overflow :(
            pass
        except ZeroDivisionError:  # do not care
            pass

    def get_load(self):
        """Get actual load. val attribute accessor

        :return: the load value
        :rtype: int
        """
        return self.load
