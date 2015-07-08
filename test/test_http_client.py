from __future__ import print_function

import sys
from threading import Thread
import mock

from alignak import daemon
from alignak.http_client import HTTPClient
from alignak.http_daemon import HTTPDaemon

from alignak_test import unittest
from alignak_tst_utils import get_free_port


class Interface(daemon.Interface):
    # subclass daemon.Interface but we can even define custom methods here:
    # say:

    def get_method(self, a, b, c=1):
        return a, b, c

    def put_method(self, a, b=3):
        return a, b
    put_method.method = 'put'

    def post_method(self, a, b=3):
        return a, b
    post_method.method = 'post'


class Test_Alignak_Http_Client(unittest.TestCase):

    http_backend = 'wsgiref'  # ho well

    def __init__(self, *a, **kw):
        super(Test_Alignak_Http_Client, self).__init__(*a, **kw)
        # some resources which must be initialized prior anything:
        self.__server = None
        self.__thread = None
        # for eventual use in tearDown:

    def tearDown(self):
        if self.__server:
            self.__server.request_stop()
        if self.__thread:
            # wait up to 5 secs for the http main thread:
            self.__thread.join(15)
            if self.__thread.isAlive():
                print("warn: http thread still alive", file=sys.stderr)
                try:
                    self.__thread._Thread__stop()
                except Exception:
                    pass
        self.__thread = None
        self.__server = None

    def setUp(self):
        addr = '127.0.0.1'
        port = self.__port = get_free_port()
        try:
            self.__client = HTTPClient(addr, port)
            self.__client.timeout = 2000
            self.__client.data_timeout = 20000
            self.__server = HTTPDaemon(addr, port,
                http_backend=self.http_backend,
                use_ssl=False, ca_cert=None, ssl_key=None, ssl_cert=None,
                hard_ssl_name_check=False, daemon_thread_pool_size=4
            )
            self.__mocked_app = mock.MagicMock()
            self.__dispatcher = Interface(self.__mocked_app)
            self.__server.register(self.__dispatcher)
            self.__thread = Thread(target=self._run_http_server)
            self.__thread.daemon = True
            self.__thread.start()
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

    @unittest.skipIf(True, "Getting method not allowed from bottle apparently.. "
                           "anyway this method isn't used by anything but to upload "
                           "stats to kernel.io."
                           "So that doesn't matter actually.")
    def test_put(self):
        cli = self.__client
        rsp = cli.put('put_method', data=dict(a=1, b=2))
        self.assertEqual("don't know", rsp)


class Test_Alignak_Http_Client_With_CherrPy_Backend(Test_Alignak_Http_Client):

    http_backend = 'cherrypy'  # ho well


if __name__ == '__main__':
    unittest.main()
