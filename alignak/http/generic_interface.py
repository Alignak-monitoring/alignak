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
"""This module provide a generic HTTP interface for all satellites.
Any Alignak satellite have at least those functions exposed over network
See : http://cherrypy.readthedocs.org/en/latest/tutorials.html for Cherrypy basic HTPP apps.
"""
import base64
import cherrypy
import cPickle
import inspect
import logging
import random
import time
import zlib

from alignak.log import logger


class GenericInterface(object):
    """Interface for inter satellites communications"""

    def __init__(self, app):
        self.app = app
        self.start_time = int(time.time())

        self.running_id = "%d.%d" % (
            self.start_time, random.randint(0, 100000000)
        )

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def index(self):
        """Wrapper to call api from /

        :return: function list
        """
        return self.api()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def ping(self):
        """Test the connection to the daemon. Returns: pong

        :return: string 'pong'
        :rtype: str
        """
        return "pong"

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_start_time(self):
        """Get the start time of the daemon

        :return: start time
        :rtype: int
        """
        return self.start_time

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_running_id(self):
        """'Get the current running id of the daemon (scheduler)'

        :return: running_ig
        :rtype: int
        """
        return self.running_id

    @cherrypy.expose
    def put_conf(self, conf):
        """Send a new configuration to the daemon (internal)

        :param conf: new conf to send
        :return: None
        """
        with self.app.conf_lock:
            self.app.new_conf = conf  # Safer to lock this one also
    put_conf.method = 'post'

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def have_conf(self):
        """Get the daemon cur_conf state

        :return: boolean indicating if the daemon has a conf
        :rtype: bool
        """
        return self.app.cur_conf is not None

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def set_log_level(self, loglevel):
        """Set the current log level in [NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL, UNKNOWN]

        :param loglevel: a value in one of the above
        :type loglevel: str
        :return: None
        """
        return logger.setLevel(loglevel)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_log_level(self):
        """Get the current log level in [NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL, UNKNOWN]

        :return: current log level
        :rtype: str
        """
        return {logging.NOTSET: 'NOTSET',
                logging.DEBUG: 'DEBUG',
                logging.INFO: 'INFO',
                logging.WARNING: 'WARNING',
                logging.ERROR: 'ERROR',
                logging.CRITICAL: 'CRITICAL'}.get(logger.level, 'UNKNOWN')

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def api(self):
        """List the methods available on the daemon

        :return: a list of methods available
        :rtype: list
        """
        return [x[0]for x in inspect.getmembers(self, predicate=inspect.ismethod)
                if not x[0].startswith('__')]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def api_full(self):
        """List the api methods and their parameters

        :return: a list of methods and parameters
        :rtype: dict
        """
        full_api = {}
        for fun in self.api():
            full_api[fun] = {}
            full_api[fun][u"doc"] = getattr(self, fun).__doc__
            full_api[fun][u"args"] = {}

            spec = inspect.getargspec(getattr(self, fun))
            args = [a for a in spec.args if a != 'self']
            if spec.defaults:
                a_dict = dict(zip(args, spec.defaults))
            else:
                a_dict = dict(zip(args, (u"No default value",) * len(args)))

            full_api[fun][u"args"] = a_dict

        full_api[u"side_note"] = u"When posting data you have to zlib the whole content" \
                                 u"and cPickle value. Example : " \
                                 u"POST /set_log_level " \
                                 u"zlib.compress({'loglevel' : cPickle.dumps('INFO')})"

        return full_api

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def remove_from_conf(self, sched_id):
        """Remove a scheduler connection (internal)

        :param sched_id: scheduler id to remove
        :type sched_id: int
        :return: None
        """
        try:
            with self.app.conf_lock:
                del self.app.schedulers[sched_id]
        except KeyError:
            pass

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def what_i_managed(self):
        """Arbiter ask me which scheduler id I manage

        :return: managed configuration ids
        :rtype: dict
        """
        print "The arbiter asked me what I manage. It's %s", self.app.what_i_managed()
        logger.debug("The arbiter asked me what I manage. It's %s", self.app.what_i_managed())
        return self.app.what_i_managed()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def wait_new_conf(self):
        """Ask the daemon to drop its configuration and wait for a new one

        :return: None
        """
        with self.app.conf_lock:
            logger.debug("Arbiter wants me to wait for a new configuration")
            # Clear can occur while setting up a new conf and lead to error.
            self.app.schedulers.clear()
            self.app.cur_conf = None

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_external_commands(self):
        """Get the external commands from the daemon (internal)
        Use a lock for this call (not a global one, just for this method)

        :return: Pickled external command list
        :rtype: str
        """
        with self.app.external_commands_lock:
            cmds = self.app.get_external_commands()
            raw = cPickle.dumps(cmds)
        return raw

    @cherrypy.expose
    def push_actions(self, actions, sched_id):
        """Get new actions from scheduler(internal)

        :param actions: list of action to add
        :type actions: list
        :param sched_id: id of the scheduler sending actions
        :type sched_id: int
        :return:None
        """
        with self.app.lock:
            self.app.add_actions(actions, int(sched_id))
    push_actions.method = 'post'

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_returns(self, sched_id):
        """Get actions returns (serialized)
        for the scheduler with _id = sched_id

        :param sched_id: id of the scheduler
        :type sched_id: int
        :return: serialized list
        :rtype: str
        """
        with self.app.lock:
            # print "A scheduler ask me the returns", sched_id
            ret = self.app.get_return_for_passive(int(sched_id))
            # print "Send mack", len(ret), "returns"
            return cPickle.dumps(ret)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_broks(self, bname):
        """Get broks from the daemon

        :return: Brok list serialized and b64encoded
        :rtype: str
        """
        with self.app.lock:
            res = self.app.get_broks()
            return base64.b64encode(zlib.compress(cPickle.dumps(res), 2))

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_raw_stats(self):
        """Get raw stats from the daemon

        :return: daemon stats
        :rtype: dict
        """
        app = self.app
        res = {}

        for sched_id in app.schedulers:
            sched = app.schedulers[sched_id]
            lst = []
            res[sched_id] = lst
            for mod in app.q_by_mod:
                # In workers we've got actions send to queue - queue size
                for (q_id, queue) in app.q_by_mod[mod].items():
                    lst.append({
                        'scheduler_name': sched['name'],
                        'module': mod,
                        'queue_number': q_id,
                        'queue_size': queue.qsize(),
                        'return_queue_len': app.get_returns_queue_len()})
        return res
