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

from collections import namedtuple
from alignak.util import alive_then_spare_then_deads
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


if __name__ == '__main__':
    unittest.main()

