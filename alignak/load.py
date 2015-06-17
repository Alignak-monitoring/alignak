#!/usr/bin/env python
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


class Load:
    """This class is for having a easy Load calculation
    without having to send value at regular interval
    (but it's more efficient if you do this :) ) and without
    having a list or other stuff. It's just an object, an update and a get
    You can define m: the average for m minutes. The val is
    the initial value. It's better if it's 0 but you can choose.

    """

    def __init__(self, m=1, initial_value=0):
        self.exp = 0  # first exp
        self.m = m  # Number of minute of the avg
        self.last_update = 0  # last update of the value
        self.val = initial_value  # first value


    def update_load(self, new_val, forced_interval=None):
        """
        Update load with the new value
        :param new_val: value used to compute new load
        :type new_val: int
        :param forced_interval: boolean indicating if we force the interval for the value
        :type forced_interval: bool
        :return: None
        """
        # The first call do not change the value, just tag
        # the beginning of last_update
        # IF  we force : bail out all time thing
        if not forced_interval and self.last_update == 0:
            self.last_update = time.time()
            return
        now = time.time()
        try:
            if forced_interval:
                diff = forced_interval
            else:
                diff = now - self.last_update
            self.exp = 1 / math.exp(diff / (self.m * 60.0))
            self.val = new_val + self.exp * (self.val - new_val)
            self.last_update = now
        except OverflowError:  # if the time change without notice, we overflow :(
            pass
        except ZeroDivisionError:  # do not care
            pass

    def get_load(self):
        """
        Get actual load. val attribute accessor

        :return: the load value
        :rtype: int
        """
        return self.val


if __name__ == '__main__':
    l = Load()
    t = time.time()
    for i in xrange(1, 300):
        l.update_load(1)
        print '[', int(time.time() - t), ']', l.get_load(), l.exp
        time.sleep(5)
