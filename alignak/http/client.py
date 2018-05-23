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
import logging
import requests
from requests.adapters import HTTPAdapter

from alignak.misc.serialization import serialize

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class HTTPClientException(Exception):
    """Simple HTTP Exception - raised for all requests exception except for a timeout"""
    pass


class HTTPClientDataException(Exception):  # pragma: no cover, hopefully never raised
    """HTTP Data Exception - raised when the HTTP response is not OK (200)

    Its attribute are:
    - rsp_code: the HTTP response code,
    - rsp_text: the HTTP response bodyeout.
    """
    def __init__(self, rsp_code, rsp_text, uri):
        # Call the base class constructor with the parameters it needs
        super(HTTPClientDataException, self).__init__()

        self.code = rsp_code
        self.text = rsp_text
        self.uri = uri
        self.msg = "Bad server response for %s: %s - %s" % (self.uri, self.code, self.text)

    def __str__(self):  # pragma: no cover
        """Exception to String"""
        return self.msg


class HTTPClientTimeoutException(Exception):  # pragma: no cover, not with unit tests
    """HTTP Timeout Exception - raised when no response issued by the server in the specified
    time frame.
    This specific exception is raised when a requests Timeout exception is catched.

    Its attribute are:
    - uri: the requested URI,
    - timeout: the duration of the timeout.
    """
    def __init__(self, timeout, uri):
        # Call the base class constructor with the parameters it needs
        super(HTTPClientTimeoutException, self).__init__()

        self.timeout = timeout
        self.uri = uri

    def __str__(self):  # pragma: no cover
        """Exception to String"""
        return "Request timeout (%d seconds) for %s" % (self.timeout, self.uri)


class HTTPClientConnectionException(Exception):
    """HTTP Connection Exception - raised when connection fails with the server.
    This specific exception is raised when a connection exception is catched.

    Its attribute are:
    - uri: the requested URI,
    - msg: the exception message
    """
    def __init__(self, uri, msg):
        # Call the base class constructor with the parameters it needs
        super(HTTPClientConnectionException, self).__init__()

        self.uri = uri
        self.msg = msg

    def __str__(self):  # pragma: no cover
        """Exception to String"""
        return "Server not available: %s - %s" % (self.uri, self.msg)


class HTTPClient(object):
    """HTTPClient class use python request to communicate over HTTP
    Basically used to get / post to other daemons

    """
    def __init__(self, address='', port=0, use_ssl=False, short_timeout=3,
                 long_timeout=120, uri='', strong_ssl=False, proxy=''):
        # pylint: disable=too-many-arguments
        self.address = address
        self.port = port
        self.short_timeout = short_timeout
        self.long_timeout = long_timeout
        self.use_ssl = use_ssl
        self.strong_ssl = strong_ssl
        if not uri:
            protocol = "https" if use_ssl else "http"
            uri = "%s://%s:%s/" % (protocol, self.address, self.port)
        self.uri = uri

        self._requests_con = requests.Session()
        # self.session = requests.Session()
        self._requests_con.header = {'Content-Type': 'application/json'}

        # Requests HTTP adapters
        http_adapter = HTTPAdapter(max_retries=3)
        https_adapter = HTTPAdapter(max_retries=3)
        self._requests_con.mount('http://', http_adapter)
        self._requests_con.mount('https://', https_adapter)

        self.set_proxy(proxy)

    def make_uri(self, path):
        """Create uri from path

        :param path: path to make uri
        :type path: str
        :return: self.uri + path
        :rtype: str
        """
        return '%s%s' % (self.uri, path)

    def make_timeout(self, wait):
        """Get short_timeout depending on wait time

        :param wait: wait for a long timeout
        :type wait: bool
        :return: self.short_timeout if wait is short, self.long_timeout otherwise
        :rtype: int
        """
        return self.short_timeout if not wait else self.long_timeout

    def set_proxy(self, proxy):  # pragma: no cover, not with unit tests
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

    def get(self, path, args=None, wait=False):
        """GET an HTTP request to a daemon

        :param path: path to do the request
        :type path: str
        :param args: args to add in the request
        :type args: dict
        :param wait: True for a long timeout
        :type wait: bool
        :return: None
        """
        if args is None:
            args = {}
        uri = self.make_uri(path)
        timeout = self.make_timeout(wait)
        try:
            logger.debug("get: %s, timeout: %s, params: %s", uri, timeout, args)
            rsp = self._requests_con.get(uri, params=args, timeout=timeout, verify=self.strong_ssl)
            logger.debug("got: %d - %s", rsp.status_code, rsp.text)
            if rsp.status_code != 200:
                raise HTTPClientDataException(rsp.status_code, rsp.text, uri)
            return rsp.json()
        except (requests.Timeout, requests.ConnectTimeout):
            raise HTTPClientTimeoutException(timeout, uri)
        except requests.ConnectionError as exp:
            raise HTTPClientConnectionException(uri, exp.args[0])
        except Exception as exp:
            raise HTTPClientException('Request error to %s: %s' % (uri, exp))

    def post(self, path, args, wait=False):
        """POST an HTTP request to a daemon

        :param path: path to do the request
        :type path: str
        :param args: args to add in the request
        :type args: dict
        :param wait: True for a long timeout
        :type wait: bool
        :return: Content of the HTTP response if server returned 200
        :rtype: str
        """
        uri = self.make_uri(path)
        timeout = self.make_timeout(wait)
        for (key, value) in list(args.items()):
            args[key] = serialize(value, True)
        try:
            logger.debug("post: %s, timeout: %s, params: %s", uri, timeout, args)
            rsp = self._requests_con.post(uri, json=args, timeout=timeout, verify=self.strong_ssl)
            logger.debug("got: %d - %s", rsp.status_code, rsp.text)
            if rsp.status_code != 200:
                raise HTTPClientDataException(rsp.status_code, rsp.text, uri)
            return rsp.content
        except (requests.Timeout, requests.ConnectTimeout):
            raise HTTPClientTimeoutException(timeout, uri)
        except requests.ConnectionError as exp:
            raise HTTPClientConnectionException(uri, exp.args[0])
        except Exception as exp:
            raise HTTPClientException('Request error to %s: %s' % (uri, exp))

    def put(self, path, args, wait=False):  # pragma: no cover, looks never used!
        # todo: remove this because it looks never used anywhere...
        """PUT and HTTP request to a daemon

        :param path: path to do the request
        :type path: str
        :param args: data to send in the request
        :type args:
        :return: Content of the HTTP response if server returned 200
        :rtype: str
        """
        uri = self.make_uri(path)
        timeout = self.make_timeout(wait)
        try:
            logger.debug("put: %s, timeout: %s, params: %s", uri, timeout, args)
            rsp = self._requests_con.put(uri, args, timeout=timeout, verify=self.strong_ssl)
            logger.debug("got: %d - %s", rsp.status_code, rsp.text)
            if rsp.status_code != 200:
                raise HTTPClientDataException(rsp.status_code, rsp.text, uri)
            return rsp.content
        except (requests.Timeout, requests.ConnectTimeout):
            raise HTTPClientTimeoutException(timeout, uri)
        except requests.ConnectionError as exp:
            raise HTTPClientConnectionException(uri, exp.args[0])
        except Exception as exp:
            raise HTTPClientException('Request error to %s: %s' % (uri, exp))
