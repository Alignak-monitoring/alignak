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
#     David Moreau Simard, dmsimard@iweb.com
#     Frédéric Vachon, fredvac@gmail.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
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
"""This module provides HTTPClient class. Used by daemon to connect to HTTP servers (other daemons)

"""
import cPickle
import json
import warnings
import zlib

import requests


from alignak.log import logger


class HTTPException(Exception):
    """Simple HTTP Exception

    """
    pass


HTTPEXCEPTIONS = (HTTPException,)


class HTTPClient(object):
    """HTTPClient class use python request to communicate over HTTP
    Basically used to get / post to other daemons

    """
    def __init__(self, address='', port=0, use_ssl=False, timeout=3,
                 data_timeout=120, uri='', strong_ssl=False, proxy=''):
        self.address = address
        self.port = port
        self.timeout = timeout
        self.data_timeout = data_timeout
        self.use_ssl = use_ssl
        self.strong_ssl = strong_ssl
        if not uri:
            protocol = "https" if use_ssl else "http"
            uri = "%s://%s:%s/" % (protocol, self.address, self.port)
        self.uri = uri
        self._requests_con = requests.Session()
        self.set_proxy(proxy)

    @property
    def con(self):
        """Deprecated properrty of HTTPClient

        :return: connection
        :rtype: object
        """
        warnings.warn("HTTPClient.con is deprecated attribute, "
                      "please use HTTPClient.connection instead.",
                      DeprecationWarning, stacklevel=2)
        return self.connection

    @property
    def connection(self):
        """Get connection attribute

        :return:
        :rtype:
        """
        return self._requests_con

    def make_uri(self, path):
        """Create uri from path

        :param path: path to make uri
        :type path: str
        :return: self.uri + path
        :rtype: str
        """
        return '%s%s' % (self.uri, path)

    def make_timeout(self, wait):
        """Get timeout depending on wait time

        :param wait: wait is short or long (else)
        :type wait: int
        :return: self.timeout if wait is short, self.data_timeout otherwise
        :rtype: int
        """
        return self.timeout if wait == 'short' else self.data_timeout

    def set_proxy(self, proxy):
        """Set HTTP proxy

        :param proxy: proxy url
        :type proxy: str
        :return: None
        """
        if proxy:
            logger.debug('PROXY SETTING PROXY %s', proxy)
            self._requests_con.proxies = {
                'http': proxy,
                'https': proxy,
            }

    def get(self, path, args={}, wait='short'):
        """Do a GET HTTP request

        :param path: path to do the request
        :type path: str
        :param args: args to add in the request
        :type args: dict
        :param wait: timeout policy (short / long)
        :type wait: int
        :return: None
        """
        uri = self.make_uri(path)
        timeout = self.make_timeout(wait)
        try:
            rsp = self._requests_con.get(uri, params=args, timeout=timeout, verify=self.strong_ssl)
            if rsp.status_code != 200:
                raise Exception('HTTP GET not OK: %s ; text=%r' % (rsp.status_code, rsp.text))
            return rsp.json()
        except Exception as err:
            raise HTTPException('Request error to %s: %s' % (uri, err))

    def post(self, path, args, wait='short'):
        """Do a POST HTTP request

        :param path: path to do the request
        :type path: str
        :param args: args to add in the request
        :type args: dict
        :param wait: timeout policy (short / long)
        :type wait: int
        :return: Content of the HTTP response if server returned 200
        :rtype: str
        """
        uri = self.make_uri(path)
        timeout = self.make_timeout(wait)
        for (key, value) in args.iteritems():
            args[key] = cPickle.dumps(value)
        try:
            headers = {'content-type': 'application/zlib'}
            args = zlib.compress(json.dumps(args, ensure_ascii=False), 2)
            rsp = self._requests_con.post(uri, data=args, timeout=timeout, verify=self.strong_ssl,
                                          headers=headers)
            if rsp.status_code != 200:
                raise Exception("HTTP POST not OK: %s ; text=%r" % (rsp.status_code, rsp.text))
        except Exception as err:
            raise HTTPException('Request error to %s: %s' % (uri, err))
        return rsp.content

    def put(self, path, data, wait='short'):
        """Do a PUT HTTP request

        :param path: path to do the request
        :type path: str
        :param data: data to send in the request
        :type data:
        :param args: args to add in the request
        :type args:
        :param wait: timeout policy (short / long)
        :type wait: int
        :return: Content of the HTTP response if server returned 200
        :rtype: str
        """
        uri = self.make_uri(path)
        timeout = self.make_timeout(wait)
        try:
            rsp = self._requests_con.put(uri, data, timeout=timeout, verify=self.strong_ssl)
            if rsp.status_code != 200:
                raise Exception('HTTP PUT not OK: %s ; text=%r' % (rsp.status_code, rsp.text))
        except Exception as err:
            raise HTTPException('Request error to %s: %s' % (uri, err))
        return rsp.content
