# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2017: Alignak team, see AUTHORS.txt file for contributors
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
"""This module provide the HTTP daemon for Alignak inter daemon communication.
It is mostly based on Cherrypy
"""
import socket
import logging

import cherrypy
from cherrypy.wsgiserver import CherryPyWSGIServer
# We need this to keep default processors in cherrypy
from cherrypy._cpreqbody import process_urlencoded, process_multipart, process_multipart_form_data

from OpenSSL import SSL, crypto
from cherrypy.wsgiserver.ssl_pyopenssl import pyOpenSSLAdapter  # pylint: disable=C0412

# load global helper objects for logs and stats computation
from alignak.http.cherrypy_extend import zlib_processor

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Pyopenssl(pyOpenSSLAdapter):
    """
    Use own ssl adapter to modify ciphers. This will disable vulnerabilities ;)
    """

    def __init__(self, certificate, private_key, certificate_chain=None, dhparam=None):
        """
        Add init because need get the dhparam

        :param certificate:
        :param private_key:
        :param certificate_chain:
        :param dhparam:
        """
        super(Pyopenssl, self).__init__(certificate, private_key, certificate_chain)
        self.dhparam = dhparam

    def get_context(self):
        """Return an SSL.Context from self attributes."""
        cont = SSL.Context(SSL.SSLv23_METHOD)

        # override:
        ciphers = (
            'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
            'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:'
            '!eNULL:!MD5:!DSS:!RC4:!SSLv2'
        )
        cont.set_options(SSL.OP_NO_COMPRESSION | SSL.OP_SINGLE_DH_USE | SSL.OP_NO_SSLv2 |
                         SSL.OP_NO_SSLv3)
        cont.set_cipher_list(ciphers)
        if self.dhparam is not None:
            cont.load_tmp_dh(self.dhparam)
            cont.set_tmp_ecdh(crypto.get_elliptic_curve('prime256v1'))
        # end override

            cont.use_privatekey_file(self.private_key)
        if self.certificate_chain:
            cont.load_verify_locations(self.certificate_chain)
        cont.use_certificate_file(self.certificate)
        return cont


class PortNotFree(Exception):
    """Exception raised when port is already used by another application"""
    pass


class HTTPDaemon(object):
    """HTTP Server class. Mostly based on Cherrypy
    It uses CherryPyWSGIServer and daemon http_interface as Application
    """
    def __init__(self, host, port, http_interface, use_ssl, ca_cert,
                 ssl_key, ssl_cert, server_dh, daemon_thread_pool_size):
        """
        Initialize HTTP daemon

        :param host: host address
        :param port: listening port
        :param http_interface:
        :param use_ssl:
        :param ca_cert:
        :param ssl_key:
        :param ssl_cert:
        :param daemon_thread_pool_size:
        """
        # Port = 0 means "I don't want HTTP server"
        if port == 0:
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        if result == 0:
            msg = "Error: Sorry, the port %s/%d is not free" % (host, port)
            raise PortNotFree(msg)

        self.port = port
        self.host = host
        self.srv = None

        self.use_ssl = use_ssl

        protocol = 'http'
        if use_ssl:
            protocol = 'https'
        self.uri = '%s://%s:%s' % (protocol, self.host, self.port)
        logger.info("Opening HTTP socket at %s", self.uri)

        # This config override default processors so we put them back in case we need them
        config = {
            '/': {
                'request.body.processors': {'application/x-www-form-urlencoded': process_urlencoded,
                                            'multipart/form-data': process_multipart_form_data,
                                            'multipart': process_multipart,
                                            'application/zlib': zlib_processor},
                'tools.gzip.on': True,
                'tools.gzip.mime_types': ['text/*', 'application/json']
            }
        }
        # disable console logging of cherrypy when not in DEBUG
        cherrypy.log.screen = True
        if getattr(logger, 'level') != logging.DEBUG:
            cherrypy.log.screen = False
            cherrypy.log.access_file = ''
            cherrypy.log.error_file = ''

        if use_ssl:
            CherryPyWSGIServer.ssl_adapter = Pyopenssl(ssl_cert, ssl_key, ca_cert, server_dh)

        self.srv = CherryPyWSGIServer((host, port),
                                      cherrypy.Application(http_interface, "/", config),
                                      numthreads=daemon_thread_pool_size, shutdown_timeout=1,
                                      request_queue_size=30)

    def run(self):
        """Wrapper to start http daemon server

        :return: None
        """
        try:
            self.srv.start()
        except socket.error, exp:
            msg = "Error: Sorry, the port %d is not free: %s" % (self.port, str(exp))
            raise PortNotFree(msg)

    def request_stop(self):
        """Wrapper to stop http daemon server

        :return: None
        """
        if self.srv:
            self.srv.stop()
