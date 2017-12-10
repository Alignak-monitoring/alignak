#!/usr/bin/env python
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

from collections import namedtuple
from alignak.util import alive_then_spare_then_deads, average_percentile
import unittest


class TestUnknownEventHandler(unittest.TestCase):

    def test_sort_alive_then_spare_then_deads(self):
        SmallSat = namedtuple("SmallSat", ["alive", "spare", "name"])

        sat_list = [SmallSat(alive=True, spare=False, name="001"),
                    SmallSat(alive=True, spare=True, name="002"),
                    SmallSat(alive=True, spare=True, name="003"),
                    SmallSat(alive=False, spare=True, name="004"),
                    SmallSat(alive=False, spare=False, name="005"),
                    SmallSat(alive=False, spare=False, name="006"),
                    SmallSat(alive=False, spare=True, name="007"),
                    SmallSat(alive=True, spare=False, name="008"),
                    SmallSat(alive=False, spare=False, name="009"),
                    SmallSat(alive=True, spare=True, name="010")]

        expected_sat_list = [SmallSat(alive=True, spare=False, name="001"),
                             SmallSat(alive=True, spare=False, name="008"),
                             SmallSat(alive=True, spare=True, name="002"),
                             SmallSat(alive=True, spare=True, name="003"),
                             SmallSat(alive=True, spare=True, name="010"),
                             SmallSat(alive=False, spare=True, name="004"),
                             SmallSat(alive=False, spare=False, name="005"),
                             SmallSat(alive=False, spare=False, name="006"),
                             SmallSat(alive=False, spare=True, name="007"),
                             SmallSat(alive=False, spare=False, name="009")]

        sat_list_ordered = alive_then_spare_then_deads(sat_list)

        assert expected_sat_list == sat_list_ordered, \
            "Function alive_then_spare_then_deads does not sort as excepted!"

    def test_average_percentile(self):
        my_values = [10, 8, 9, 7, 3, 11, 7, 13, 9, 10]
        lat_avg, lat_min, lat_max = average_percentile(my_values)
        assert 8.7 == lat_avg, 'Average'
        assert 4.8 == lat_min, 'Minimum'
        assert 12.1 == lat_max, 'Maximum'

if __name__ == '__main__':
    unittest.main()

