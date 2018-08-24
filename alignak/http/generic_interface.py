# -*- coding: utf-8 -*-
#
# Because almost all functions are called as web services, no self use in the functions
# pylint: disable=no-self-use

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
"""This module provide a generic HTTP interface for all satellites.

Any Alignak satellite have at least these functions exposed over network
See : http://cherrypy.readthedocs.org/en/latest/tutorials.html for Cherrypy basic HTTP apps.

All the _ prefixed functions are for internal use only and they will not be documented
in the /api endpoint.
"""
import inspect
import logging
import random
import time
import cherrypy

from alignak.log import ALIGNAK_LOGGER_NAME
from alignak.misc.serialization import serialize

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class GenericInterface(object):
    """Interface for inter satellites communications"""

    def __init__(self, app):
        self.app = app
        self.start_time = int(time.time())

        # Set a running identifier that will change if the attached daemon is restarted
        self.running_id = "%d.%d" % (
            self.start_time, random.randint(0, 100000000)
        )

    #####
    #   _____                                           _
    #  | ____| __  __  _ __     ___    ___    ___    __| |
    #  |  _|   \ \/ / | '_ \   / _ \  / __|  / _ \  / _` |
    #  | |___   >  <  | |_) | | (_) | \__ \ |  __/ | (_| |
    #  |_____| /_/\_\ | .__/   \___/  |___/  \___|  \__,_|
    #                 |_|
    #####

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def index(self):
        """Wrapper to call api from /

        This will return the daemon identity and main information

        :return: function list
        """
        return self.identity()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def identity(self):
        """Get the daemon identity

        This will return an object containing some properties:
        - alignak: the Alignak instance name
        - version: the Alignak version
        - type: the daemon type
        - name: the daemon name

        :return: daemon identity
        :rtype: dict
        """
        res = self.app.get_id()
        res.update({"start_time": self.start_time})
        res.update({"running_id": self.running_id})
        return res

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def api(self):
        """List the methods available on the daemon Web service interface

        :return: a list of methods and parameters
        :rtype: dict
        """
        functions = [x[0]for x in inspect.getmembers(self, predicate=inspect.ismethod)
                     if not x[0].startswith('_')]

        full_api = {
            'doc': u"When posting data you have to use the JSON format.",
            'api': []
        }
        my_daemon_type = "%s" % getattr(self.app, 'type', 'unknown')
        my_address = getattr(self.app, 'host_name', getattr(self.app, 'name', 'unknown'))
        if getattr(self.app, 'address', '127.0.0.1') not in ['127.0.0.1']:
            # If an address is explicitely specified, I must use it!
            my_address = self.app.address
        for fun in functions:
            endpoint = {
                'daemon': my_daemon_type,
                'name': fun,
                'doc': getattr(self, fun).__doc__,
                'uri': '%s://%s:%s/%s' % (getattr(self.app, 'scheme', 'http'),
                                          my_address,
                                          self.app.port, fun),
                'args': {}
            }

            try:
                spec = inspect.getfullargspec(getattr(self, fun))
            except Exception:  # pylint: disable=broad-except
                # pylint: disable=deprecated-method
                spec = inspect.getargspec(getattr(self, fun))
            args = [a for a in spec.args if a not in ('self', 'cls')]
            if spec.defaults:
                a_dict = dict(list(zip(args, spec.defaults)))
            else:
                a_dict = dict(list(zip(args, ("No default value",) * len(args))))

            endpoint["args"] = a_dict
            full_api['api'].append(endpoint)

        return full_api

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def stop_request(self, stop_now='0'):
        """Request the daemon to stop

        If `stop_now` is set to '1' the daemon will stop now. Else, the daemon
        will enter the stop wait mode. In this mode the daemon stops its activity and
        waits until it receives a new `stop_now` request to stop really.

        :param stop_now: stop now or go to stop wait mode
        :type stop_now: bool
        :return: None
        """
        self.app.interrupted = (stop_now == '1')
        self.app.will_stop = True

        return True

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_log_level(self):
        """Get the current daemon log level

        Returns an object with the daemon identity and a `log_level` property.

        running_id
        :return: current log level
        :rtype: str
        """
        level_names = {
            logging.DEBUG: 'DEBUG', logging.INFO: 'INFO', logging.WARNING: 'WARNING',
            logging.ERROR: 'ERROR', logging.CRITICAL: 'CRITICAL'
        }
        alignak_logger = logging.getLogger(ALIGNAK_LOGGER_NAME)

        res = self.identity()
        res.update({"log_level": alignak_logger.getEffectiveLevel(),
                    "log_level_name": level_names[alignak_logger.getEffectiveLevel()]})
        return res

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def set_log_level(self, log_level=None):
        """Set the current log level for the daemon

        The `log_level` parameter must be in [DEBUG, INFO, WARNING, ERROR, CRITICAL]

        In case of any error, this function returns an object containing some properties:
        '_status': 'ERR' because of the error
        `_message`: some more explanations about the error

        Else, this function returns True

        :param log_level: a value in one of the above
        :type log_level: str
        :return: see above
        :rtype: dict
        """
        if log_level is None:
            log_level = cherrypy.request.json['log_level']

        if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            return {'_status': u'ERR',
                    '_message': u"Required log level is not allowed: %s" % log_level}

        alignak_logger = logging.getLogger(ALIGNAK_LOGGER_NAME)
        alignak_logger.setLevel(log_level)
        return self.get_log_level()
    set_log_level.method = 'post'

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def managed_configurations(self):
        """Get the arbiter configuration managed by the daemon

        For an arbiter daemon, it returns an empty object

        For all other daemons it returns a dictionary formated list of the scheduler
        links managed by the daemon:
        {
            'instance_id': {
                'hash': ,
                'push_flavor': ,
                'managed_conf_id':
            }
        }

        If a daemon returns an empty list, it means that it has not yet received its configuration
        from the arbiter.

        :return: managed configuration
        :rtype: list
        """
        return self.app.get_managed_configurations()

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def stats(self, details=False):
        """Get statistics and information from the daemon

        Returns an object with the daemon identity, the daemon start_time
        and some extra properties depending upon the daemon type.

        All daemons provide these ones:
        - program_start: the Alignak start timestamp
        - spare: to indicate if the daemon is a spare one
        - load: the daemon load
        - modules: the daemon modules information
        - counters: the specific daemon counters

        :param details: Details are required (different from 0)
        :type details str

        :return: daemon stats
        :rtype: dict
        """
        if details is not False:
            details = bool(details)
        res = self.identity()
        res.update(self.app.get_daemon_stats(details=details))
        return res

    #####
    #   ___           _                                   _                     _
    #  |_ _|  _ __   | |_    ___   _ __   _ __     __ _  | |     ___    _ __   | |  _   _
    #   | |  | '_ \  | __|  / _ \ | '__| | '_ \   / _` | | |    / _ \  | '_ \  | | | | | |
    #   | |  | | | | | |_  |  __/ | |    | | | | | (_| | | |   | (_) | | | | | | | | |_| |
    #  |___| |_| |_|  \__|  \___| |_|    |_| |_|  \__,_| |_|    \___/  |_| |_| |_|  \__, |
    #                                                                               |___/
    #####

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def _wait_new_conf(self):
        """Ask the daemon to drop its configuration and wait for a new one

        :return: None
        """
        with self.app.conf_lock:
            logger.debug("My Arbiter wants me to wait for a new configuration.")
            # Clear can occur while setting up a new conf and lead to error.
            self.app.schedulers.clear()
            self.app.cur_conf = {}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def _push_configuration(self, pushed_configuration=None):
        """Send a new configuration to the daemon

        This function is not intended for external use. It is quite complex to
        build a configuration for a daemon and it is the arbiter dispatcher job ;)

        :param pushed_configuration: new conf to send
        :return: None
        """
        if pushed_configuration is None:
            confs = cherrypy.request.json
            pushed_configuration = confs['conf']
        # It is safer to lock this part
        with self.app.conf_lock:
            self.app.new_conf = pushed_configuration
            return True
    _push_configuration.method = 'post'

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def _have_conf(self, magic_hash=None):
        """Get the daemon current configuration state

        If the daemon has received a configuration from its arbiter, this will
        return True

        If a `magic_hash` is provided it is compared with the one included in the
        daemon configuration and this function returns True only if they match!

        :return: boolean indicating if the daemon has a configuration
        :rtype: bool
        """
        self.app.have_conf = getattr(self.app, 'cur_conf', None) not in [None, {}]
        if magic_hash is not None:
            # Beware, we got an str in entry, not an int
            magic_hash = int(magic_hash)
            # I've got a conf and a good one
            return self.app.have_conf and self.app.cur_conf.magic_hash == magic_hash

        return self.app.have_conf

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def _push_actions(self):
        """Push actions to the poller/reactionner

        This function is used by the scheduler to send the actions to get executed to
        the poller/reactionner

        {'actions': actions, 'instance_id': scheduler_instance_id}

        :return:None
        """
        data = cherrypy.request.json
        with self.app.lock:
            self.app.add_actions(data['actions'], data['scheduler_instance_id'])
    _push_actions.method = 'post'

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def _external_commands(self):
        """Get the external commands from the daemon

        Use a lock for this function to protect

        :return: serialized external command list
        :rtype: str
        """
        res = []
        with self.app.external_commands_lock:
            for cmd in self.app.get_external_commands():
                res.append(cmd.serialize())
        return res

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def _results(self, scheduler_instance_id):
        """Get the results of the executed actions for the scheduler which instance id is provided

        Calling this method for daemons that are not configured as passive do not make sense.
        Indeed, this service should only be exposed on poller and reactionner daemons.

        :param scheduler_instance_id: instance id of the scheduler
        :type scheduler_instance_id: string
        :return: serialized list
        :rtype: str
        """
        with self.app.lock:
            res = self.app.get_results_from_passive(scheduler_instance_id)
        return serialize(res, True)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def _broks(self, broker_name):  # pylint: disable=unused-argument
        """Get the broks from the daemon

        This is used by the brokers to get the broks list of a daemon

        :return: Brok list serialized
        :rtype: dict
        """
        with self.app.broks_lock:
            res = self.app.get_broks()
        return serialize(res, True)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def _events(self):
        """Get the monitoring events from the daemon

        This is used by the arbiter to get the monitoring events from all its satellites

        :return: Events list serialized
        :rtype: list
        """
        with self.app.events_lock:
            res = self.app.get_events()
        return serialize(res, True)
