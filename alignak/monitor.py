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
"""This module group the Alignak self monitoring features.

Currently, it contains an Alignak Web Service client used to report Alignak status
to an external monitoring application

"""

import logging

import requests
from requests import RequestException
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class MonitorConnection(object):
    """Base class for Alignak Web Services client connection"""

    def __init__(self, endpoint='http://127.0.0.1:7773/ws'):
        if endpoint.endswith('/'):  # pragma: no cover - test url is complying ...
            self.url_endpoint_root = endpoint[0:-1]
        else:
            self.url_endpoint_root = endpoint

        self.session = requests.Session()
        self.session.header = {'Content-Type': 'application/json'}

        # Requests HTTP adapters
        http_adapter = HTTPAdapter(max_retries=3)
        https_adapter = HTTPAdapter(max_retries=3)
        self.session.mount('http://', http_adapter)
        self.session.mount('https://', https_adapter)

        self.authenticated = False
        self._token = None
        self.timeout = None

        logger.info("Alignak monitor, endpoint: %s", self.url_endpoint_root)

    def __repr__(self):  # pragma: no cover
        return '<WS report to %r, authenticated: %r />' \
               % (self.url_endpoint_root, self.authenticated)
    __str__ = __repr__

    def get_url(self, endpoint):
        """
        Returns the formated full URL endpoint
        :param endpoint: str. the relative endpoint to access
        :return: str
        """
        return "%s/%s" % (self.url_endpoint_root, endpoint)

    def get_response(self, method, endpoint, headers=None, json=None, params=None, data=None):
        # pylint: disable=too-many-arguments
        """
        Returns the response from the requested endpoint with the requested method
        :param method: str. one of the methods accepted by Requests ('POST', 'GET', ...)
        :param endpoint: str. the relative endpoint to access
        :param params: (optional) Dictionary or bytes to be sent in the query string
        for the :class:`Request`.
        :param data: (optional) Dictionary, bytes, or file-like object to send in the body
        of the :class:`Request`.
        :param json: (optional) json to send in the body of the :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
        :return: Requests.response
        """
        logger.debug("Parameters for get_response:")
        logger.debug("\t - endpoint: %s", endpoint)
        logger.debug("\t - method: %s", method)
        logger.debug("\t - headers: %s", headers)
        logger.debug("\t - json: %s", json)
        logger.debug("\t - params: %s", params)
        logger.debug("\t - data: %s", data)

        url = self.get_url(endpoint)

        # First stage. Errors are connection errors (timeout, no session, ...)
        try:
            response = self.session.request(method=method, url=url, headers=headers, json=json,
                                            params=params, data=data, timeout=self.timeout)
            logger.debug("response headers: %s", response.headers)
            logger.debug("response content: %s", response.content)
        except RequestException as exp:
            response = {"_status": "ERR",
                        "_error": {"message": exp},
                        "_issues": {"message": exp}}

        return response

    @staticmethod
    def decode(response):
        """
        Decodes and returns the response as JSON (dict) or raise BackendException
        :param response: requests.response object
        :return: dict
        """

        # Second stage. Errors are backend errors (bad login, bad url, ...)
        try:
            response.raise_for_status()
        except requests.HTTPError as exp:
            response = {"_status": "ERR",
                        "_error": {"message": exp, "code": response.status_code},
                        "_issues": {"message": exp, "code": response.status_code}}
            return response
        else:
            return response.json()

    def set_token(self, token):
        """
        Set token in authentification for next requests
        :param token: str. token to set in auth. If None, reinit auth
        """
        if token:
            auth = HTTPBasicAuth(token, '')
            self._token = token
            self.authenticated = True
            self.session.auth = auth
            logger.debug("Using session token: %s", token)
        else:
            self._token = None
            self.authenticated = False
            self.session.auth = None
            logger.debug("Session token/auth reinitialised")

    def get_token(self):
        """Get the stored backend token"""
        return self._token

    token = property(get_token, set_token)

    def login(self, username, password):
        """
        Log into the WS interface and get the authentication token

        if login is:
        - accepted, returns True
        - refused, returns False

        In case of any error, raises a BackendException

        :param username: login name
        :type username: str
        :param password: password
        :type password: str
        :param generate: Can have these values: enabled | force | disabled
        :type generate: str
        :return: return True if authentication is successfull, otherwise False
        :rtype: bool
        """
        logger.debug("login for: %s", username)

        # Configured as not authenticated WS
        if not username and not password:
            self.set_token(token=None)
            return False

        if not username or not password:
            logger.error("Username or password cannot be None!")
            self.set_token(token=None)
            return False

        endpoint = 'login'
        json = {'username': username, 'password': password}
        response = self.get_response(method='POST', endpoint=endpoint, json=json)
        if response.status_code == 401:
            logger.error("Access denied to %s", self.url_endpoint_root)
            self.set_token(token=None)
            return False

        resp = self.decode(response=response)

        if 'token' in resp:
            self.set_token(token=resp['token'])
            return True

        return False  # pragma: no cover - unreachable ...

    def logout(self):
        """
        Logout from the backend

        :return: return True if logout is successfull, otherwise False
        :rtype: bool
        """
        logger.debug("request backend logout")
        if not self.authenticated:
            logger.warning("Unnecessary logout ...")
            return True

        endpoint = 'logout'

        _ = self.get_response(method='POST', endpoint=endpoint)

        self.session.close()
        self.set_token(token=None)

        return True

    def get(self, endpoint, params=None):
        """
        Get items or item in alignak backend

        If an error occurs, a BackendException is raised.

        This method builds a response as a dictionary that always contains: _items and _status::

            {
                u'_items': [
                    ...
                ],
                u'_status': u'OK'
            }

        :param endpoint: endpoint (API URL) relative from root endpoint
        :type endpoint: str
        :param params: parameters for the backend API
        :type params: dict
        :return: dictionary as specified upper
        :rtype: dict
        """
        response = self.get_response(method='GET', endpoint=endpoint, params=params)

        resp = self.decode(response=response)
        if '_status' not in resp:  # pragma: no cover - need specific backend tests
            resp['_status'] = u'OK'  # TODO: Sure??

        return resp

    def post(self, endpoint, data, files=None, headers=None):
        # pylint: disable=unused-argument
        """
        Create a new item

        :param endpoint: endpoint (API URL)
        :type endpoint: str
        :param data: properties of item to create
        :type data: dict
        :param files: Not used. To be implemented
        :type files: None
        :param headers: headers (example: Content-Type)
        :type headers: dict
        :return: response (creation information)
        :rtype: dict
        """
        # We let Requests encode data to json
        response = self.get_response(method='POST', endpoint=endpoint, json=data, headers=headers)

        resp = self.decode(response=response)

        return resp

    def patch(self, endpoint, data):
        """
        Method to update an item

        The headers must include an If-Match containing the object _etag.
            headers = {'If-Match': contact_etag}

        The data dictionary contain the fields that must be modified.

        If the patching fails because the _etag object do not match with the provided one, a
        BackendException is raised with code = 412.

        If inception is True, this method makes e new get request on the endpoint to refresh the
        _etag and then a new patch is called.

        If an HTTP 412 error occurs, a BackendException is raised. This exception is:
        - code: 412
        - message: response content
        - response: backend response

        All other HTTP error raises a BackendException.
        If some _issues are provided by the backend, this exception is:
        - code: HTTP error code
        - message: response content
        - response: JSON encoded backend response (including '_issues' dictionary ...)

        If no _issues are provided and an _error is signaled by the backend, this exception is:
        - code: backend error code
        - message: backend error message
        - response: JSON encoded backend response

        :param endpoint: endpoint (API URL)
        :type endpoint: str
        :param data: properties of item to update
        :type data: dict
        :param headers: headers (example: Content-Type). 'If-Match' required
        :type headers: dict
        :param inception: if True tries to get the last _etag
        :type inception: bool
        :return: dictionary containing patch response from the backend
        :rtype: dict
        """
        response = self.get_response(method='PATCH', endpoint=endpoint, json=data,
                                     headers={'Content-Type': 'application/json'})

        if response.status_code == 200:
            return self.decode(response=response)

        return response
