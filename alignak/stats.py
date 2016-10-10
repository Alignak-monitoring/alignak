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
#     Grégory Starck, g.starck@gmail.com
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr

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
"""This module provide export of Alignak metrics in a statsd format

"""
import socket
import logging

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Stats(object):
    """Stats class to export data into a statsd format

    """
    def __init__(self):
        self.name = ''
        self.type = ''
        self.stats = {}

        # Statsd daemon parameters
        self.statsd_sock = None
        self.statsd_addr = None

    def register(self, name, _type,
                 statsd_host='localhost', statsd_port=8125, statsd_prefix='alignak',
                 statsd_enabled=False):
        """Init statsd instance with real values

        :param name: daemon name
        :type name: str
        :param _type: daemon type
        :type _type:
        :param statsd_host: host to post data
        :type statsd_host: str
        :param statsd_port: port to post data
        :type statsd_port: int
        :param statsd_prefix: prefix to add to metric
        :type statsd_prefix: str
        :param statsd_enabled: bool to enable statsd
        :type statsd_enabled: bool
        :return: None
        """
        self.name = name
        self.type = _type

        # local statsd part
        self.statsd_host = statsd_host
        self.statsd_port = statsd_port
        self.statsd_prefix = statsd_prefix
        self.statsd_enabled = statsd_enabled

        if self.statsd_enabled:
            logger.info('Sending %s/%s daemon statistics to: %s:%s.%s',
                        self.type, self.name,
                        self.statsd_host, self.statsd_port, self.statsd_prefix)
            self.load_statsd()
        else:
            logger.info('Alignak internal statistics are disabled.')

    def load_statsd(self):
        """Create socket connection to statsd host

        :return: None
        """
        try:
            self.statsd_addr = (socket.gethostbyname(self.statsd_host), self.statsd_port)
            self.statsd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except (socket.error, socket.gaierror), exp:
            logger.error('Cannot create statsd socket: %s', exp)
            return

    def incr(self, key, value):
        """Increments a key with value

        :param key: key to edit
        :type key: str
        :param value: value to add
        :type value: int
        :return: None
        """
        _min, _max, number, _sum = self.stats.get(key, (None, None, 0, 0))
        number += 1
        _sum += value
        if _min is None or value < _min:
            _min = value
        if _max is None or value > _max:
            _max = value
        self.stats[key] = (_min, _max, number, _sum)

        # Manage local statsd part
        if self.statsd_sock and self.name:
            # beware, we are sending ms here, value is in s
            packet = '%s.%s.%s:%d|ms' % (self.statsd_prefix, self.name, key, value * 1000)
            try:
                self.statsd_sock.sendto(packet, self.statsd_addr)
            except (socket.error, socket.gaierror):
                pass  # cannot send? ok not a huge problem here and cannot
                # log because it will be far too verbose :p

# pylint: disable=C0103
statsmgr = Stats()
