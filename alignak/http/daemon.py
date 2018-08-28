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
"""This module provide the HTTP daemon for Alignak inter daemon communication.
It is mostly based on Cherrypy
"""
import socket
import logging

import cherrypy
# We need this to keep default processors in cherrypy
from cherrypy._cpreqbody import process_urlencoded, process_multipart, process_multipart_form_data
# load global helper objects for logs and stats computation
from alignak.http.cherrypy_extend import zlib_processor


# Check if PyOpenSSL is installed
# pylint: disable=unused-import
PYOPENSSL = True
try:
    from OpenSSL import SSL
    from OpenSSL import crypto
except ImportError:
    PYOPENSSL = False


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class PortNotFree(Exception):
    """Exception raised when port is already used by another application"""
    pass


class HTTPDaemon(object):
    """HTTP Server class. Mostly based on Cherrypy
    It uses CherryPyWSGIServer and daemon http_interface as Application
    """
    # pylint: disable=too-many-arguments, unused-argument
    def __init__(self, host, port, http_interface, use_ssl, ca_cert,
                 ssl_key, ssl_cert, server_dh, thread_pool_size, log_file=None, icon_file=None):
        """
        Initialize HTTP daemon

        :param host: host address
        :param port: listening port
        :param http_interface:
        :param use_ssl:
        :param ca_cert:
        :param ssl_key:
        :param ssl_cert:
        :param thread_pool_size:
        :param log_file: if set, the log file for Cherrypy log
        :param icon_file: if set, the favicon file to use
        """
        self.port = port
        self.host = host
        self.use_ssl = use_ssl

        # # Make sure that the host ip/name is propely encoded for CherryPy
        # try:
        #     self.host = self.host.encode('utf-8')
        # except Exception as exp:
        #     pass
        # logger.warning("self.host: %s (%s)", self.host, type(self.host))
        #
        self.uri = '%s://%s:%s' % ('https' if self.use_ssl else 'http', self.host, self.port)
        logger.debug("Configured HTTP server on %s, %d threads", self.uri, thread_pool_size)

        # This application config overrides the default processors
        # so we put them back in case we need them
        config = {
            '/': {
                'request.body.processors': {'application/x-www-form-urlencoded': process_urlencoded,
                                            'multipart/form-data': process_multipart_form_data,
                                            'multipart': process_multipart,
                                            'application/zlib': zlib_processor},
                'tools.gzip.on': True,
                'tools.gzip.mime_types': ['text/*', 'application/json'],

                'tools.response_headers.on': True,
                'tools.response_headers.headers': [('Access-Control-Allow-Origin', '*')],

                'tools.staticfile.on': True if icon_file else False,
                'tools.staticfile.filename': icon_file
            }
        }

        # For embedding into a WSGI server
        # cherrypy.config.update({'environment': 'embedded'})

        # Configure HTTP server
        # Available parameters (see https://github.com/cherrypy/cherrypy/
        # blob/master/cherrypy/_cpserver.py) for more information if needed.
        # - socket_queue_size
        cherrypy.config.update({'engine.autoreload.on': False,
                                'server.thread_pool': thread_pool_size,
                                'server.socket_host': str(self.host),
                                'server.socket_port': self.port})

        # Default is to disable CherryPy logging
        cherrypy.config.update({'log.screen': False,
                                'log.access_file': '',
                                'log.error_file': ''})
        if log_file:
            # Log into the provided log file
            cherrypy.config.update({'log.screen': True,
                                    'log.access_file': str(log_file),
                                    'log.error_file': str(log_file)})
            cherrypy.log.access_log.setLevel(logging.DEBUG)
            cherrypy.log.error_log.setLevel(logging.DEBUG)
            cherrypy.log("CherryPy logging: %s" % (log_file))

        if use_ssl:
            # Configure SSL server certificate and private key
            # Parameters:
            # ssl_context = None
            #   When using PyOpenSSL, an instance of SSL.Context.
            # ssl_certificate = None
            #   The filename of the SSL certificate to use.
            # ssl_certificate_chain = None
            #   When using PyOpenSSL, the certificate chain to pass to
            # Context.load_verify_locations.
            # ssl_private_key = None
            #   The filename of the private key to use with SSL.
            # ssl_ciphers = None
            # The ciphers list of SSL.
            cherrypy.config.update({'server.ssl_certificate': ssl_cert,
                                    'server.ssl_private_key': ssl_key})
            cherrypy.log("Using PyOpenSSL: %s" % (PYOPENSSL))
            if not PYOPENSSL:
                # Use CherryPy built-in module if PyOpenSSL is not installed
                cherrypy.config.update({'server.ssl_module': 'builtin'})
            cherrypy.log("Using SSL certificate: %s" % (ssl_cert))
            cherrypy.log("Using SSL private key: %s" % (ssl_key))
            if ca_cert:
                cherrypy.config.update({'server.ssl_certificate_chain': ca_cert})
                cherrypy.log("Using SSL CA certificate: %s" % ca_cert)

        # Mount the main application (an Alignak daemon interface)
        cherrypy.tree.mount(http_interface, '/', config)

    def run(self):
        """Wrapper to start the CherryPy server

        This function throws a PortNotFree exception if any socket error is raised.

        :return: None
        """
        def _started_callback():
            """Callback function when Cherrypy Engine is started"""
            cherrypy.log("CherryPy engine started and listening...")

        self.cherrypy_thread = None
        try:
            cherrypy.log("Starting CherryPy engine on %s" % (self.uri))
            self.cherrypy_thread = cherrypy.engine.start_with_callback(_started_callback)
            cherrypy.engine.block()
            cherrypy.log("Exited from the engine block")
        except socket.error as exp:
            raise PortNotFree("Error: Sorry, the HTTP server did not started correctly: error: %s"
                              % (str(exp)))

    def stop(self):  # pylint: disable=no-self-use
        """Wrapper to stop the CherryPy server

        :return: None
        """
        cherrypy.log("Stopping CherryPy engine (current state: %s)..." % cherrypy.engine.state)
        try:
            cherrypy.engine.exit()
        except RuntimeWarning:
            pass
        except SystemExit:
            cherrypy.log('SystemExit raised: shutting down bus')
        cherrypy.log("Stopped")
