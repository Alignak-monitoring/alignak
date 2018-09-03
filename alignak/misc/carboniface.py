#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
External source code - note that all the methods in this class are not used by Alignak!
"""


# pylint: skip-file
from future.standard_library import install_aliases
install_aliases()

import socket
import pickle
import random
import time
import struct
import threading
from urllib.request import urlopen, Request

"""
Get it here: https://gist.github.com/otger/6606437#file-carboniface-py
"""


class CarbonIface(object):

    def __init__(self, host, port, event_url=None):
        """Initialize Carbon Interface.
        host: host where the carbon daemon is running
        port: port where carbon daemon is listening for pickle protocol on host
        event_url: web app url where events can be added. It must be provided if add_event(...)
                   is to be used. Otherwise an exception by urllib2 will raise
        """
        self.host = host
        self.port = port
        self.event_url = event_url
        self.__data = []
        self.__data_lock = threading.Lock()

    def add_data(self, metric, value, ts=None):
        """
        Add data to queue

        :param metric: the metric name
        :type metric: str
        :param value: the value of data
        :type value: int
        :param ts: the timestamp
        :type ts: int | None
        :return: True if added successfully, otherwise False
        :rtype: bool
        """
        if not ts:
            ts = time.time()
        if self.__data_lock.acquire():
            self.__data.append((metric, (ts, value)))
            self.__data_lock.release()
            return True
        return False

    def add_data_dict(self, dd):  # pragma: no cover - never used...
        """
        dd must be a dictionary where keys are the metric name,
        each key contains a dictionary which at least must have 'value' key (optionally 'ts')

        dd = {'experiment1.subsystem.block.metric1': {'value': 12.3, 'ts': 1379491605.55},
              'experiment1.subsystem.block.metric2': {'value': 1.35},
             ...}
        """
        if self.__data_lock.acquire():
            for k, v in list(dd.items()):
                ts = v.get('ts', time.time())
                value = v.get('value')
                self.__data.append((k, (ts, value)))
            self.__data_lock.release()
            return True
        return False

    def add_data_list(self, dl):  # pragma: no cover - never used...
        """
        dl must be a list of tuples like:
        dl = [('metricname', (timestamp, value)),
              ('metricname', (timestamp, value)),
              ...]
        """
        if self.__data_lock.acquire():
            self.__data.extend(dl)
            self.__data_lock.release()
            return True
        return False

    def send_data(self, data=None):
        """If data is empty, current buffer is sent. Otherwise data must be like:
        data = [('metricname', (timestamp, value)),
              ('metricname', (timestamp, value)),
              ...]
        """
        save_in_error = False
        if not data:
            if self.__data_lock.acquire():
                data = self.__data
                self.__data = []
                save_in_error = True
                self.__data_lock.release()
            else:
                return False
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        payload = pickle.dumps(data, protocol=2)
        header = struct.pack("!L", len(payload))
        message = header + payload
        s.settimeout(1)
        s.connect((self.host, self.port))
        try:
            s.send(message)
        except:
            # log.exception('Error when sending data to carbon')
            if save_in_error:
                self.__data.extend(data)
            return False
        else:
            # log.debug('Sent data to {host}:{port}: {0} metrics, {1} bytes'.format(len(data),
            #   len(message), host = self.host, port=self.port))
            return True
        finally:
            s.close()

    def add_event(self, what, data=None, tags=None, when=None):  # pragma: no cover - never used...
        """


        :param what:
        :param data:
        :param tags:
        :param when:
        :return:
        """
        if not when:
            when = time.time()
        postdata = '{{"what":"{0}", "when":{1}'.format(what, when)
        if data:
            postdata += ', "data":"{0}"'.format(str(data))
        if tags:
            postdata += ', "tags": "{0}"'.format(str(tags))
        postdata += '}'
        req = Request(self.url_post_event)
        req.add_data(postdata)

        try:
            urlopen(req)
        except Exception as _:
            # log.exception('Error when sending event to carbon')
            pass


if __name__ == '__main__':  # pragma: no cover - never used this way...
    c_host = ''
    c_port = 2004
    c_event_url = None

    data = []
    for el in range(10):
        data.append(('test.cryogenics.temperature{0}'.format(el), (time.time(),
                                                                   300 * random.random())))

    def keep_updating():
        global data
        global carbon
        t = threading.Timer(1, keep_updating)
        data = [(
                x[0], (
                    time.time(),
                    x[1][1] + ((-1)**random.randint(1, 2)) * random.random()
                )
            ) for x in data]
        carbon.send_data(data)
        rnd = random.random()
        if rnd > 0.85:
            carbon.add_event(what='Random event', data=str(rnd), tags='random, test',
                             when=time.time())
        t.start()
    carbon = CarbonIface(c_host, c_port, c_event_url)
    keep_updating()
