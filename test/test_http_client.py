from __future__ import print_function
import time
import socket
from multiprocessing import Process
import os

import cherrypy
import mock

from alignak.http.generic_interface import GenericInterface
from alignak.http.client import HTTPClient
from alignak.http.daemon import HTTPDaemon
from alignak_test import unittest
from alignak_tst_utils import get_free_port


class Interface(GenericInterface):
    # subclass daemon.Interface but we can even define custom methods here:
    # say:

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_method(self, a, b, c=1):
        return a, b, c

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def put_method(self, a, b=3):
        return a, b

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def post_method(self, a, b=3):
        return a, b


class Test_Alignak_Http_Client(unittest.TestCase):


    def __init__(self, *a, **kw):
        super(Test_Alignak_Http_Client, self).__init__(*a, **kw)
        # some resources which must be initialized prior anything:
        self.__server = None
        self.__process = None
        # for eventual use in tearDown:

    def tearDown(self):
        if self.__server:
            self.__server.request_stop()
        if self.__process:
            # wait up to 5 secs for the http main thread:
            self.__process.terminate()
            while self.__process.is_alive():
#                print("warn: http proc still alive", file=sys.stderr)
                try:
                    os.kill(self.__process.pid, 9)
                except Exception:
                    pass
                time.sleep(1)
        self.__process = None
        self.__server = None

    def setUp(self):
        addr = '127.0.0.1'
        port = self.__port = get_free_port()
        try:
            self.__client = HTTPClient(addr, port)
            self.__client.timeout = 2000
            self.__client.data_timeout = 20000

            self.__mocked_app = mock.MagicMock()
            self.__dispatcher = Interface(self.__mocked_app)
            self.__server = HTTPDaemon(addr, port,
                http_interface=self.__dispatcher,
                use_ssl=False, ca_cert=None, ssl_key=None, ssl_cert=None,
                daemon_thread_pool_size=4
            )

            #self.__server.register(self.__dispatcher)
            self.__process = Process(target=self._run_http_server)
            self.__process.start()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            while True:
                try:
                    if sock.connect_ex((addr, port)) == 0:
#                        print("http_server started", file=sys.stderr)
                        break
                except:
                    pass
#                print("Waiting http_server", file=sys.stderr)
                time.sleep(1)
            else:
                raise Exception()
        except:  # nosetest doesn't call tearDown if setUp raise something,
            # but I want to be really clean, so:
            self.tearDown()
            raise

    def _run_http_server(self):
        server = self.__server
        if server is None:
            return
        server.run()

    def test_ping(self):
        cli = self.__client
        self.assertEqual('pong', cli.get('ping'))

    def test_get(self):
        cli = self.__client
        # what ! ??
        self.assertEqual([u'1', u'2', 1], cli.get('get_method', dict(a=1, b=2)))
        self.assertEqual([u'2', u'3', u'4'], cli.get('get_method', dict(a=2, b=3, c=4)))

    def test_post(self):
        cli = self.__client
        rsp = cli.post('post_method', args=dict(a=1, b=2))
        # ho weeelllllll...
        # by get method (above) you get a list, a list of str/bytes or eventually not..
        # because what's got in the get method ran by the http daemon are the serialized values.
        # But by post method you get an str/bytes object (of a list)..
        self.assertEqual('[1, 2]', rsp)

    def test_put(self):
        cli = self.__client
        rsp = cli.put('put_method', data=dict(a=1, b=2))
        self.assertEqual('["1", "2"]', rsp)


if __name__ == '__main__':
    unittest.main()
