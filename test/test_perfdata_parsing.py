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
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Sebastien Coavoux, s.coavoux@free.fr
#     aviau, alexandre.viau@savoirfairelinux.com
#     Grégory Starck, g.starck@gmail.com
#     Jean-Claude Computing, jeanclaude.computing@gmail.com
#     Jean Gabes, naparuba@gmail.com

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
This file is used to test reading and processing of config files
"""

from alignak.misc.perfdata import Metric, PerfDatas

from alignak_test import AlignakTest, unittest


class TestPerfdataParsing(AlignakTest):
    """ Test performance data parsing """

    def test_perfdata_parsing(self):
        """ Test parsing performance data
        """
        self.print_header()

        # Get a metric from a string
        perf_data_string = 'ramused=90%;85;95;;'
        metric = Metric(perf_data_string)
        self.assertEqual('ramused', metric.name)
        self.assertEqual(90, metric.value)
        self.assertEqual('%', metric.uom)
        self.assertEqual(85, metric.warning)
        self.assertEqual(95, metric.critical)
        self.assertEqual(0, metric.min)
        self.assertEqual(100, metric.max)

        # Get only the first metric if several are present
        perf_data_string = 'ramused=1009MB;;;0;1982 ' \
                           'swapused=540MB;;;0;3827 ' \
                           'memused=1550MB;2973;3964;0;5810'
        metric = Metric(perf_data_string)
        self.assertEqual('ramused', metric.name)
        self.assertEqual(1009, metric.value)
        self.assertEqual('MB', metric.uom)
        self.assertEqual(None, metric.warning)
        self.assertEqual(None, metric.critical)
        self.assertEqual(0, metric.min)
        self.assertEqual(1982, metric.max)

        # Get performance data from a string
        perf_data_string = 'ramused=1009MB;;;0;1982 ' \
                           'swapused=540MB;;;; ' \
                           'memused=90%'
        perf_data = PerfDatas(perf_data_string)
        # Get a metrics dictionary
        self.assertIsInstance(perf_data.metrics, dict)
        self.assertEqual(3, len(perf_data))

        metric = perf_data['ramused']
        self.assertEqual('ramused', metric.name)
        self.assertEqual(1009, metric.value)
        self.assertEqual('MB', metric.uom)
        self.assertEqual(None, metric.warning)
        self.assertEqual(None, metric.critical)
        self.assertEqual(0, metric.min)
        self.assertEqual(1982, metric.max)

        metric = perf_data['swapused']
        self.assertEqual('swapused', metric.name)
        self.assertEqual(540, metric.value)
        self.assertEqual('MB', metric.uom)
        self.assertEqual(None, metric.warning)
        self.assertEqual(None, metric.critical)
        self.assertEqual(None, metric.min)
        self.assertEqual(None, metric.max)

        metric = perf_data['memused']
        self.assertEqual('memused', metric.name)
        self.assertEqual(90, metric.value)
        self.assertEqual('%', metric.uom)
        self.assertEqual(None, metric.warning)
        self.assertEqual(None, metric.critical)
        self.assertEqual(0, metric.min)
        self.assertEqual(100, metric.max)

    def test_perfdata_space_characters(self):
        """ Create a perfdata with name containing space
        """
        self.print_header()

        # Metrics name can contain space characters
        perf_data_string = "'Physical Memory Used'=12085620736Bytes; " \
                           "'Physical Memory Utilisation'=94%;80;90;"
        perf_data = PerfDatas(perf_data_string)
        # Get a metrics dictionary
        self.assertIsInstance(perf_data.metrics, dict)
        self.assertEqual(2, len(perf_data))

        metric = perf_data['Physical Memory Used']
        self.assertEqual('Physical Memory Used', metric.name)
        self.assertEqual(12085620736, metric.value)
        self.assertEqual('Bytes', metric.uom)
        self.assertIs(None, metric.warning)
        self.assertIs(None, metric.critical)
        self.assertIs(None, metric.min)
        self.assertIs(None, metric.max)

        metric = perf_data['Physical Memory Utilisation']
        self.assertEqual('Physical Memory Utilisation', metric.name)
        self.assertEqual(94, metric.value)
        self.assertEqual('%', metric.uom)
        self.assertEqual(80, metric.warning)
        self.assertEqual(90, metric.critical)
        self.assertEqual(0, metric.min)
        self.assertEqual(100, metric.max)

    def test_perfdata_special_characters(self):
        """ Create a perfdata with name containing special characters
        """
        self.print_header()

        # Metrics name can contain special characters
        perf_data_string = "'C: Space'=35.07GB; 'C: Utilisation'=87.7%;90;95;"
        perf_data = PerfDatas(perf_data_string)
        # Get a metrics dictionary
        self.assertIsInstance(perf_data.metrics, dict)
        self.assertEqual(2, len(perf_data))

        metric = perf_data['C: Space']
        self.assertEqual('C: Space', metric.name)
        self.assertEqual(35.07, metric.value)
        self.assertEqual('GB', metric.uom)
        self.assertIs(None, metric.warning)
        self.assertIs(None, metric.critical)
        self.assertIs(None, metric.min)
        self.assertIs(None, metric.max)

        metric = perf_data['C: Utilisation']
        self.assertEqual('C: Utilisation', metric.name)
        self.assertEqual(87.7, metric.value)
        self.assertEqual('%', metric.uom)
        self.assertEqual(90, metric.warning)
        self.assertEqual(95, metric.critical)
        self.assertEqual(0, metric.min)
        self.assertEqual(100, metric.max)

    def test_perfdata_floating_value(self):
        """ Create a perfdata with complex floating value
        """
        self.print_header()

        # Metrics value can contain complex floating value
        perf_data_string = "time_offset-192.168.0.1=-7.22636468709e-05s;1;2;0;;"
        perf_data = PerfDatas(perf_data_string)
        # Get a metrics dictionary
        self.assertIsInstance(perf_data.metrics, dict)
        self.assertEqual(1, len(perf_data))

        metric = perf_data['time_offset-192.168.0.1']
        self.assertEqual('time_offset-192.168.0.1', metric.name)
        self.assertEqual(-7.22636468709e-05, metric.value)
        self.assertEqual('s', metric.uom)
        self.assertEqual(1, metric.warning)
        self.assertEqual(2, metric.critical)
        self.assertEqual(0, metric.min)
        self.assertIs(None, metric.max)

    def test_perfdata_accented_characters(self):
        """ Create a perfdata with accented characters
        """
        self.print_header()

        # Metrics name can contain accented and special characters
        perf_data_string = u"àéèï-192.168.0.1=-7.22636468709e-05s;1;2;0;;"
        perf_data = PerfDatas(perf_data_string)
        # Get a metrics dictionary
        self.assertIsInstance(perf_data.metrics, dict)
        self.assertEqual(1, len(perf_data))

        metric = perf_data[u'àéèï-192.168.0.1']
        self.assertEqual(metric.name, u'àéèï-192.168.0.1')
        self.assertEqual(metric.value, -7.22636468709e-05)
        self.assertEqual(metric.uom, 's')
        self.assertEqual(metric.warning, 1)
        self.assertEqual(metric.critical, 2)
        self.assertEqual(metric.min, 0)
        self.assertEqual(metric.max, None)

    def test_perfdata_empty_string(self):
        """ Create a perfdata from an empty string
        """
        self.print_header()

        perf_data_string = None
        perf_data = PerfDatas(perf_data_string)
        self.assertEqual(len(perf_data), 0)

        perf_data_string = ''
        perf_data = PerfDatas(perf_data_string)
        self.assertEqual(len(perf_data), 0)


if __name__ == '__main__':
    unittest.main()
