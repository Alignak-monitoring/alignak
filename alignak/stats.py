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
import threading
import time
import json
import hashlib
import base64
import socket

from alignak.log import logger
from alignak.http.client import HTTPClient, HTTPException


BLOCK_SIZE = 16


def pad(data):
    """Add data to fit BLOCK_SIZE

    :param data: initial data
    :return: data padded to fit BLOCK_SIZE
    """
    pad = BLOCK_SIZE - len(data) % BLOCK_SIZE
    return data + pad * chr(pad)


def unpad(padded):
    """Unpad data based on last char

    :param padded: padded data
    :return: unpadded data
    """
    pad = ord(padded[-1])
    return padded[:-pad]


class Stats(object):
    """Stats class to export data into a statsd format

    """
    def __init__(self):
        self.name = ''
        self.type = ''
        self.app = None
        self.stats = {}
        # There are two modes that are not exclusive
        # first the kernel mode
        self.api_key = ''
        self.secret = ''
        self.http_proxy = ''
        self.con = HTTPClient(uri='http://kernel.alignak.io')
        # then the statsd one
        self.statsd_sock = None
        self.statsd_addr = None

    def launch_reaper_thread(self):
        """Launch thread that collects data

        :return: None
        """
        self.reaper_thread = threading.Thread(None, target=self.reaper, name='stats-reaper')
        self.reaper_thread.daemon = True
        self.reaper_thread.start()

    def register(self, app, name, _type, api_key='', secret='', http_proxy='',
                 statsd_host='localhost', statsd_port=8125, statsd_prefix='alignak',
                 statsd_enabled=False):
        """Init statsd instance with real values

        :param app: application (arbiter, scheduler..)
        :type app: alignak.daemon.Daemon
        :param name: daemon name
        :type name: str
        :param _type: daemon type
        :type _type:
        :param api_key: api_key to post data
        :type api_key: str
        :param secret: secret to post data
        :type secret: str
        :param http_proxy: proxy http if necessary
        :type http_proxy: str
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
        self.app = app
        self.name = name
        self.type = _type
        # kernel.io part
        self.api_key = api_key
        self.secret = secret
        self.http_proxy = http_proxy
        # local statsd part
        self.statsd_host = statsd_host
        self.statsd_port = statsd_port
        self.statsd_prefix = statsd_prefix
        self.statsd_enabled = statsd_enabled

        if self.statsd_enabled:
            logger.debug('Loading statsd communication with %s:%s.%s',
                         self.statsd_host, self.statsd_port, self.statsd_prefix)
            self.load_statsd()

        # Also load the proxy if need
        self.con.set_proxy(self.http_proxy)

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
        :type v: int
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

        # Manage local statd part
        if self.statsd_sock and self.name:
            # beware, we are sending ms here, value is in s
            packet = '%s.%s.%s:%d|ms' % (self.statsd_prefix, self.name, key, value * 1000)
            try:
                self.statsd_sock.sendto(packet, self.statsd_addr)
            except (socket.error, socket.gaierror), exp:
                pass  # cannot send? ok not a huge problem here and cannot
                # log because it will be far too verbose :p

    def _encrypt(self, data):
        """Cypher data

        :param data: data to cypher
        :type data: str
        :return: cyphered data
        :rtype: str
        """
        md_hash = hashlib.md5()
        md_hash.update(self.secret)
        key = md_hash.hexdigest()

        md_hash = hashlib.md5()
        md_hash.update(self.secret + key)
        ivs = md_hash.hexdigest()

        data = pad(data)

        aes = AES.new(key, AES.MODE_CBC, ivs[:16])

        encrypted = aes.encrypt(data)
        return base64.urlsafe_b64encode(encrypted)

    def reaper(self):
        """Get data from daemon and send it to the statsd daemon

        :return: None
        """
        try:
            from Crypto.Cipher import AES
        except ImportError:
            logger.error('Cannot find python lib crypto: stats export is not available')
            AES = None  # pylint: disable=C0103

        while True:
            now = int(time.time())
            stats = self.stats
            self.stats = {}

            if len(stats) != 0:
                string = ', '.join(['%s:%s' % (key, v) for (key, v) in stats.iteritems()])
            # If we are not in an initializer daemon we skip, we cannot have a real name, it sucks
            # to find the data after this
            if not self.name or not self.api_key or not self.secret:
                time.sleep(60)
                continue

            metrics = []
            for (key, elem) in stats.iteritems():
                namekey = '%s.%s.%s' % (self.type, self.name, key)
                _min, _max, number, _sum = elem
                _avg = float(_sum) / number
                # nb can't be 0 here and _min_max can't be None too
                string = '%s.avg %f %d' % (namekey, _avg, now)
                metrics.append(string)
                string = '%s.min %f %d' % (namekey, _min, now)
                metrics.append(string)
                string = '%s.max %f %d' % (namekey, _max, now)
                metrics.append(string)
                string = '%s.count %f %d' % (namekey, number, now)
                metrics.append(string)

            # logger.debug('REAPER metrics to send %s (%d)' % (metrics, len(str(metrics))) )
            # get the inner data for the daemon
            struct = self.app.get_stats_struct()
            struct['metrics'].extend(metrics)
            # logger.debug('REAPER whole struct %s' % struct)
            j = json.dumps(struct)
            if AES is not None and self.secret != '':
                logger.debug('Stats PUT to kernel.alignak.io/api/v1/put/ with %s %s',
                             self.api_key,
                             self.secret)

                # assume a %16 length messagexs
                encrypted_text = self._encrypt(j)
                try:
                    self.con.put('/api/v1/put/?api_key=%s' % (self.api_key), encrypted_text)
                except HTTPException, exp:
                    logger.error('Stats REAPER cannot put to the metric server %s', exp)
            time.sleep(60)

# pylint: disable=C0103
statsmgr = Stats()
