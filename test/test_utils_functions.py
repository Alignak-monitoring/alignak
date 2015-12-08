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

import numpy as np
from collections import namedtuple
from alignak.util import alive_then_spare_then_deads, average_percentile
from alignak_test import unittest


class TestUnknownEventHandler(unittest.TestCase):

    def test_sort_alive_then_spare_then_deads(self):
        SmallSat = namedtuple("SmallSat", ["alive", "spare"])

        sat_list = [SmallSat(alive=True, spare=False),
                    SmallSat(alive=True, spare=True),
                    SmallSat(alive=True, spare=True),
                    SmallSat(alive=False, spare=True),
                    SmallSat(alive=False, spare=False),
                    SmallSat(alive=False, spare=False),
                    SmallSat(alive=False, spare=True),
                    SmallSat(alive=True, spare=False),
                    SmallSat(alive=False, spare=False),
                    SmallSat(alive=True, spare=True)]

        expected_sat_list = [SmallSat(alive=True, spare=False),
                             SmallSat(alive=True, spare=False),
                             SmallSat(alive=True, spare=True),
                             SmallSat(alive=True, spare=True),
                             SmallSat(alive=True, spare=True)]

        sat_list.sort(alive_then_spare_then_deads)

        self.assertListEqual(sat_list[:5], expected_sat_list,
                            "Function alive_then_spare_then_deads does not sort as exepcted!")

    def test_average_percentile(self):
        my_values = [10, 8, 9, 7, 3, 11, 7, 13, 9, 10]
        lat_avg, lat_min, lat_max = average_percentile(my_values)
        self.assertEqual(8.7, lat_avg, 'Average')
        self.assertEqual(4.8, lat_min, 'Minimum')
        self.assertEqual(12.1, lat_max, 'Maximum')

if __name__ == '__main__':
    unittest.main()

