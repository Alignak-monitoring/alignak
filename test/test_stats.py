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
#

"""
This file test the stats
"""

import time

from alignak_test import AlignakTest


class TestStats(AlignakTest):
    """
    This class test the stats
    """
    def setUp(self):
        super(TestStats, self).setUp()

    def test_average_latency(self):
        """ Test average latency

        :return: None
        """
        self.setup_with_file('cfg/cfg_stats.cfg')

        svc0 = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        svc1 = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_1")
        svc2 = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_2")
        svc3 = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_3")
        svc4 = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_4")
        svc5 = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_5")

        self.scheduler_loop(1, [[svc0, 0, 'OK'], [svc1, 0, 'OK'], [svc2, 0, 'OK'],
                                    [svc3, 0, 'OK'], [svc4, 0, 'OK'], [svc5, 0, 'OK']])

        now = time.time()

        svc0.latency = 0.96
        svc1.latency = 0.88
        svc2.latency = 0.92
        svc3.latency = 1.3
        svc4.latency = 0.95
        svc5.latency = 0.78

        svc0.last_chk = now-7
        svc1.last_chk = now-1
        svc2.last_chk = now
        svc3.last_chk = now-2
        svc4.last_chk = now-5
        svc5.last_chk = now-12

        self._scheduler.get_latency_average_percentile()

        reference = {
            'min': 0.89,
            'max': 1.23,
            'avg': 1.00,
        }

        assert reference['min'] == \
                         self._scheduler.stats['latency']['min']
        assert reference['max'] == \
                         self._scheduler.stats['latency']['max']
        assert reference['avg'] == \
                         self._scheduler.stats['latency']['avg']
