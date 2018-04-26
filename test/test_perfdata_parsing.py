#!/usr/bin/env python
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

from alignak_test import AlignakTest


class TestPerfdataParsing(AlignakTest):
    """ Test performance data parsing """
    def setUp(self):
        super(TestPerfdataParsing, self).setUp()

    def test_perfdata_parsing(self):
        """ Test parsing performance data
        """
        # Get a metric from a string
        perf_data_string = 'ramused=90%;85;95;;'
        metric = Metric(perf_data_string)
        assert 'ramused' == metric.name
        assert 90 == metric.value
        assert '%' == metric.uom
        assert 85 == metric.warning
        assert 95 == metric.critical
        assert 0 == metric.min
        assert 100 == metric.max

        # Get only the first metric if several are present
        perf_data_string = 'ramused=1009MB;;;0;1982 ' \
                           'swapused=540MB;;;0;3827 ' \
                           'memused=1550MB;2973;3964;0;5810'
        metric = Metric(perf_data_string)
        assert 'ramused' == metric.name
        assert 1009 == metric.value
        assert 'MB' == metric.uom
        assert None == metric.warning
        assert None == metric.critical
        assert 0 == metric.min
        assert 1982 == metric.max

        # Get performance data from a string
        perf_data_string = 'ramused=1009MB;;;0;1982 ' \
                           'swapused=540MB;;;; ' \
                           'memused=90%'
        perf_data = PerfDatas(perf_data_string)
        # Get a metrics dictionary
        assert isinstance(perf_data.metrics, dict)
        assert 3 == len(perf_data)

        metric = perf_data['ramused']
        assert 'ramused' == metric.name
        assert 1009 == metric.value
        assert 'MB' == metric.uom
        assert None == metric.warning
        assert None == metric.critical
        assert 0 == metric.min
        assert 1982 == metric.max

        metric = perf_data['swapused']
        assert 'swapused' == metric.name
        assert 540 == metric.value
        assert 'MB' == metric.uom
        assert None == metric.warning
        assert None == metric.critical
        assert None == metric.min
        assert None == metric.max

        metric = perf_data['memused']
        assert 'memused' == metric.name
        assert 90 == metric.value
        assert '%' == metric.uom
        assert None == metric.warning
        assert None == metric.critical
        assert 0 == metric.min
        assert 100 == metric.max

    def test_perfdata_space_characters(self):
        """ Create a perfdata with name containing space
        """
        # Metrics name can contain space characters
        perf_data_string = "'Physical Memory Used'=12085620736Bytes; " \
                           "'Physical Memory Utilisation'=94%;80;90;"
        perf_data = PerfDatas(perf_data_string)
        # Get a metrics dictionary
        assert isinstance(perf_data.metrics, dict)
        assert 2 == len(perf_data)

        metric = perf_data['Physical Memory Used']
        assert 'Physical Memory Used' == metric.name
        assert 12085620736 == metric.value
        assert 'Bytes' == metric.uom
        assert None is metric.warning
        assert None is metric.critical
        assert None is metric.min
        assert None is metric.max

        metric = perf_data['Physical Memory Utilisation']
        assert 'Physical Memory Utilisation' == metric.name
        assert 94 == metric.value
        assert '%' == metric.uom
        assert 80 == metric.warning
        assert 90 == metric.critical
        assert 0 == metric.min
        assert 100 == metric.max

    def test_perfdata_special_characters(self):
        """ Create a perfdata with name containing special characters
        """
        # Metrics name can contain special characters
        perf_data_string = "'C: Space'=35.07GB; 'C: Utilisation'=87.7%;90;95;"
        perf_data = PerfDatas(perf_data_string)
        # Get a metrics dictionary
        assert isinstance(perf_data.metrics, dict)
        assert 2 == len(perf_data)

        metric = perf_data['C: Space']
        assert 'C: Space' == metric.name
        assert 35.07 == metric.value
        assert 'GB' == metric.uom
        assert None is metric.warning
        assert None is metric.critical
        assert None is metric.min
        assert None is metric.max

        metric = perf_data['C: Utilisation']
        assert 'C: Utilisation' == metric.name
        assert 87.7 == metric.value
        assert '%' == metric.uom
        assert 90 == metric.warning
        assert 95 == metric.critical
        assert 0 == metric.min
        assert 100 == metric.max

        # Metrics name can contain special characters
        perf_data_string = "'C: used'=13.06452GB;22.28832;25.2601;0;29.71777 " \
                           "'C: used %'=44%;75;85;0;100"
        perf_data = PerfDatas(perf_data_string)
        # Get a metrics dictionary
        assert isinstance(perf_data.metrics, dict)
        assert 2 == len(perf_data)

        metric = perf_data['C: used']
        assert 'C: used' == metric.name
        assert 13.06452 == metric.value
        assert 'GB' == metric.uom
        assert 22.28832 == metric.warning
        assert 25.2601 == metric.critical
        assert 0 is metric.min
        assert 29.71777 == metric.max

        metric = perf_data['C: used %']
        assert 'C: used %' == metric.name
        assert 44 == metric.value
        assert '%' == metric.uom
        assert 75 == metric.warning
        assert 85 == metric.critical
        assert 0 is metric.min
        assert 100 == metric.max

    def test_perfdata_floating_value(self):
        """ Create a perfdata with complex floating value
        """
        # Metrics value can contain complex floating value
        perf_data_string = "time_offset-192.168.0.1=-7.22636468709e-05s;1;2;0;;"
        perf_data = PerfDatas(perf_data_string)
        # Get a metrics dictionary
        assert isinstance(perf_data.metrics, dict)
        assert 1 == len(perf_data)

        metric = perf_data['time_offset-192.168.0.1']
        assert 'time_offset-192.168.0.1' == metric.name
        assert -7.22636468709e-05 == metric.value
        assert 's' == metric.uom
        assert 1 == metric.warning
        assert 2 == metric.critical
        assert 0 == metric.min
        assert None is metric.max

    def test_perfdata_accented_characters(self):
        """ Create a perfdata with accented characters
        """
        # Metrics name can contain accented and special characters
        perf_data_string = u"àéèï-192.168.0.1=-7.22636468709e-05s;1;2;0;;"
        perf_data = PerfDatas(perf_data_string)
        # Get a metrics dictionary
        assert isinstance(perf_data.metrics, dict)
        assert 1 == len(perf_data)

        metric = perf_data[u'àéèï-192.168.0.1']
        assert metric.name == u'àéèï-192.168.0.1'
        assert metric.value == -7.22636468709e-05
        assert metric.uom == 's'
        assert metric.warning == 1
        assert metric.critical == 2
        assert metric.min == 0
        assert metric.max == None

    def test_perfdata_empty_string(self):
        """ Create a perfdata from an empty string
        """
        perf_data_string = None
        perf_data = PerfDatas(perf_data_string)
        assert len(perf_data) == 0

        perf_data_string = ''
        perf_data = PerfDatas(perf_data_string)
        assert len(perf_data) == 0
