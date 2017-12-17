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
"""This module provide a generic HTTP interface for all satellites.
Any Alignak satellite have at least those functions exposed over network
See : http://cherrypy.readthedocs.org/en/latest/tutorials.html for Cherrypy basic HTTP apps.
"""
import inspect
import logging
import random
import time
import cherrypy

from alignak.misc.serialization import serialize

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class GenericInterface(object):
    """Interface for inter satellites communications"""

    def __init__(self, app):
        self.app = app
        self.start_time = int(time.time())

        # Set a running identifier that will change if the attached daemon is restarted
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
    def ping(self):  # pylint: disable=R0201
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
        """Get the current running identifier of the daemon

        :return: running_ig
        :rtype: int
        """
        return self.running_id

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def put_conf(self, conf=None):
        """Send a new configuration to the daemon (internal)

        :param conf: new conf to send
        :return: None
        """
        if conf is None:
            confs = cherrypy.request.json
            conf = confs['conf']
        with self.app.conf_lock:
            self.app.new_conf = conf  # Safer to lock this one also
    put_conf.method = 'post'

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def have_conf(self, magic_hash=None):  # pylint: disable=W0613
        """Get the daemon cur_conf state

        :return: boolean indicating if the daemon has a conf
        :rtype: bool
        """
        if magic_hash is not None:
            # Beware, we got an str in entry, not an int
            magic_hash = int(magic_hash)
            # I've got a conf and a good one
            return self.app.cur_conf and self.app.cur_conf.magic_hash == magic_hash

        return getattr(self.app, 'cur_conf', None) is not None

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def set_log_level(self, loglevel=None):  # pylint: disable=R0201
        """Set the current log level in [NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL, UNKNOWN]

        :param loglevel: a value in one of the above
        :type loglevel: str
        :return: None
        """
        if loglevel is None:
            parameters = cherrypy.request.json
            loglevel = parameters['loglevel']
        alignak_logger = logging.getLogger("alignak")
        alignak_logger.setLevel(loglevel)
        return loglevel
    set_log_level.method = 'post'

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_log_level(self):  # pylint: disable=R0201
        """Get the current log level in [NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL, UNKNOWN]

        TODO: I am quite sure that this function does not return
        the real log level of the current daemon :(
        :return: current log level
        :rtype: str
        """
        alignak_logger = logging.getLogger("alignak")
        return {logging.NOTSET: 'NOTSET',
                logging.DEBUG: 'DEBUG',
                logging.INFO: 'INFO',
                logging.WARNING: 'WARNING',
                logging.ERROR: 'ERROR',
                logging.CRITICAL: 'CRITICAL'}.get(alignak_logger.getEffectiveLevel(), 'UNKNOWN')

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

        full_api[u"side_note"] = u"When posting data you have to serialize value. Example : " \
                                 u"POST /set_log_level " \
                                 u"{'loglevel' : serialize('INFO')}"

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
        return self.app.what_i_managed()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def wait_new_conf(self):
        """Ask the daemon to drop its configuration and wait for a new one

        :return: None
        """
        with self.app.conf_lock:
            logger.warning("My Arbiter wants me to wait for a new configuration.")
            # Clear can occur while setting up a new conf and lead to error.
            self.app.schedulers.clear()
            self.app.cur_conf = None

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_external_commands(self):
        """Get the external commands from the daemon (internal)
        Use a lock for this call (not a global one, just for this method)

        :return: serialized external command list
        :rtype: str
        """
        if hasattr(self.app, 'external_commands_lock'):
            with self.app.external_commands_lock:
                cmds = self.app.get_external_commands()
                raw = serialize(cmds, True)
        else:
            raw = []
        return raw

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def push_actions(self):
        """Get new actions from scheduler(internal)

        :return:None
        """
        results = cherrypy.request.json
        with self.app.lock:
            self.app.add_actions(results['actions'], results['sched_id'])
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
            ret = self.app.get_return_for_passive(sched_id)
            return serialize(ret, True)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_broks(self, bname):  # pylint: disable=W0613
        """Get broks from the daemon

        :return: Brok list serialized
        :rtype: dict
        """
        with self.app.lock:
            res = self.app.get_broks()

        return serialize(res, True)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_raw_stats(self):
        """Get raw stats from the daemon

        :return: daemon stats
        :rtype: dict
        """
        app = self.app
        res = {}

        if hasattr(app, 'schedulers'):
            try:
                # Get queue stats
                for sched_id, sched in app.schedulers.iteritems():
                    lst = []
                    res[sched_id] = lst
                    for mod in app.q_by_mod:
                        # In workers we've got actions sent to queue - queue size
                        for (worker_id, queue) in app.q_by_mod[mod].items():
                            try:
                                lst.append({
                                    'scheduler_name': sched['name'],
                                    'module': mod,
                                    'worker': worker_id,
                                    'worker_queue_size': queue.qsize(),
                                    'return_queue_size': app.returns_queue.qsize()})
                            except (IOError, EOFError):
                                pass

            except Exception:  # pylint: disable=broad-except
                pass

        return res
