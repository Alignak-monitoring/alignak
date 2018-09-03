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
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Jean-Claude Computing, jeanclaude.computing@gmail.com
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Romain Forlot, rforlot@yahoo.com

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
This module provide classes to handle performance data from monitoring plugin output
"""
import re
from alignak.util import to_best_int_float

PERFDATA_SPLIT_PATTERN = re.compile(r'([^=]+=\S+)')
# TODO: Improve this regex to not match strings like this:
# 'metric=45+e-456.56unit;50;80;0;45+-e45e-'
METRIC_PATTERN = \
    re.compile(
        r'^([^=]+)=([\d\.\-\+eE]+)([\w\/%]*)'
        r';?([\d\.\-\+eE:~@]+)?;?([\d\.\-\+eE:~@]+)?;?([\d\.\-\+eE]+)?;?([\d\.\-\+eE]+)?;?\s*'
    )


def guess_int_or_float(val):
    """Wrapper for Util.to_best_int_float
    Basically cast into float or int and compare value
    If they are equal then there is no coma so return integer

    :param val: value to cast
    :return: value casted into int, float or None
    :rtype: int | float | NoneType
    """
    try:
        return to_best_int_float(val)
    except (ValueError, TypeError):
        return None


class Metric(object):
    # pylint: disable=too-few-public-methods
    """
    Class providing a small abstraction for one metric of a Perfdatas class
    """
    def __init__(self, string):
        self.name = self.value = self.uom = \
            self.warning = self.critical = self.min = self.max = None
        string = string.strip()
        matches = METRIC_PATTERN.match(string)
        if matches:
            # Get the name but remove all ' in it
            self.name = matches.group(1).replace("'", "")
            self.value = guess_int_or_float(matches.group(2))
            self.uom = matches.group(3)
            self.warning = guess_int_or_float(matches.group(4))
            self.critical = guess_int_or_float(matches.group(5))
            self.min = guess_int_or_float(matches.group(6))
            self.max = guess_int_or_float(matches.group(7))
            if self.uom == '%':
                self.min = 0
                self.max = 100

    def __str__(self):  # pragma: no cover
        string = "%s=%s%s" % (self.name, self.value, self.uom)
        if self.warning:
            string += ";%s" % (self.warning)
        if self.critical:
            string += ";%s" % (self.critical)
        return string


class PerfDatas(object):
    # pylint: disable=too-few-public-methods
    """
    Class providing performance data extracted from a check output
    """
    def __init__(self, string):
        string = string or ''
        elts = PERFDATA_SPLIT_PATTERN.findall(string)
        elts = [e for e in elts if e != '']
        self.metrics = {}
        for elem in elts:
            metric = Metric(elem)
            if metric.name is not None:
                self.metrics[metric.name] = metric

    def __iter__(self):
        return iter(list(self.metrics.values()))

    def __len__(self):
        return len(self.metrics)

    def __getitem__(self, key):
        return self.metrics[key]

    def __contains__(self, key):
        return key in self.metrics
