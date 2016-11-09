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

    This class allows to send metrics to a StatsD server using UDP datagrams.
    Same behavior as::

        echo "foo:1|c" | nc -u -w0 127.0.0.1 8125

    """
    def __init__(self):
        # Our daemon type and name
        self.name = ''
        self.type = ''

        # Our known statistics
        self.stats = {}

        # local statsd part
        self.statsd_host = None
        self.statsd_port = None
        self.statsd_prefix = None
        self.statsd_enabled = None

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
            logger.info('Sending %s/%s daemon statistics to: %s:%s, prefix: %s',
                        self.type, self.name,
                        self.statsd_host, self.statsd_port, self.statsd_prefix)
            self.load_statsd()
        else:
            logger.info('Alignak internal statistics are disabled.')

        return self.statsd_enabled

    def load_statsd(self):
        """Create socket connection to statsd host

        Note that because of the UDP protocol used by StatsD, if no server is listening the
        socket connection will be accepted anyway :)

        :return: True if socket got created else False and an exception log is raised
        """
        if not self.statsd_enabled:
            logger.warning('StatsD is not enabled, connection is not allowed')
            return False

        try:
            logger.info('Trying to contact StatsD server...')
            self.statsd_addr = (socket.gethostbyname(self.statsd_host), self.statsd_port)
            self.statsd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except (socket.error, socket.gaierror) as exp:
            logger.exception('Cannot create StatsD socket: %s', exp)
            return False
        except Exception as exp:  # pylint: disable=broad-except
            logger.exception('Cannot create StatsD socket (other): %s', exp)
            return False

        logger.info('StatsD server contacted')
        return True

    def incr(self, key, value):
        """Increments a key with value

        If the key does not exist is is created

        :param key: key to edit
        :type key: str
        :param value: value to add
        :type value: int
        :return: True if the metric got sent, else False if not sent
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
        if self.statsd_enabled and self.statsd_sock:
            # beware, we are sending ms here, value is in s
            packet = '%s.%s.%s:%d|ms' % (self.statsd_prefix, self.name, key, value * 1000)
            # Do not log because it is spamming the log file, but leave this code in place
            # for it may be restored easily for if more tests are necessary... ;)
            # logger.info("Sending data: %s", packet)
            try:
                self.statsd_sock.sendto(packet, self.statsd_addr)
            except (socket.error, socket.gaierror):
                pass
                # cannot send? ok not a huge problem here and we cannot
                # log because it will be far too verbose :p
            return True

        return False

# pylint: disable=C0103
statsmgr = Stats()
