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
"""This module provide a specific HTTP interface for a Arbiter."""

import time
import logging
import json
import cherrypy

from alignak.http.generic_interface import GenericInterface
from alignak.external_command import ExternalCommand

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class ArbiterInterface(GenericInterface):
    """Interface for HA Arbiter. The Slave/Master arbiter can get /push conf

    """
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def reload_configuration(self):
        """Ask to the arbiter to reload the monitored configuration

        Returns False if the arbiter is not a master arbiter

        :return: True if configuration reload is accepted
        """
        # If I'm the master, ignore the command and raise a log
        if not self.app.is_master:
            logger.warning("I received a request to reload the monitored configuration. "
                           "I am not the Master, ignore and continue to run.")
            return False

        logger.warning("I received a request to reload the monitored configuration.")
        if self.app.loading_configuration:
            logger.warning("I am still reloading the monitored configuration ;)")

        self.app.need_config_reload = True
        return True

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def backend_notification(self, event=None, parameters=None):
        """The Alignak backend raises an event to the Alignak arbiter
        -----
        Possible events are:
        - creation, for a realm or an host creation
        - deletion, for a realm or an host deletion

        Calls the reload configuration function if event is creation or deletion

        Else, nothing for the moment!

        :return: True / False if configuration reload is accepted or not
        """
        # request_parameters = cherrypy.request.json
        # event = request_parameters.get('event', event)
        # parameters = request_parameters.get('parameters', parameters)
        if event is None:
            data = cherrypy.request.json
            event = data.get('event', None)
        if parameters is None:
            data = cherrypy.request.json
            parameters = data.get('parameters', None)

        logger.warning("I got a backend notification: %s / %s", event, parameters)

        # For a configuration reload event...
        if event in ['creation', 'deletion']:
            # If I'm the master, ignore the command and raise a log
            if not self.app.is_master:
                message = "I received a request to reload the monitored configuration. " \
                          "I am not the Master arbiter, I ignore and continue to run."
                logger.warning(message)
                return {'_status': 'ERR', '_message': message}

            message = "I received a request to reload the monitored configuration."
            if self.app.loading_configuration:
                message += "I am still reloading the monitored configuration ;)"
            logger.warning(message)

            self.app.need_config_reload = True
            return {'_status': 'OK', '_message': message}

        return {'_status': 'OK', '_message': "No action to do"}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def command(self):
        """ Request to execute an external command
        :return:
        """
        if cherrypy.request.method != "POST":
            return {'_status': 'ERR', '_message': 'You must only POST on this endpoint.'}

        if cherrypy.request and not cherrypy.request.json:
            return {'_status': 'ERR', '_message': 'You must POST parameters on this endpoint.'}

        logger.debug("Post /command: %s", cherrypy.request.params)
        command = cherrypy.request.json.get('command', None)
        timestamp = cherrypy.request.json.get('timestamp', None)
        element = cherrypy.request.json.get('element', None)
        host = cherrypy.request.json.get('host', None)
        service = cherrypy.request.json.get('service', None)
        user = cherrypy.request.json.get('user', None)
        parameters = cherrypy.request.json.get('parameters', None)

        if not command:
            return {'_status': 'ERR', '_message': 'Missing command parameter'}

        command_line = command.upper()
        if timestamp:
            try:
                timestamp = int(timestamp)
            except ValueError:
                return {'_status': 'ERR', '_message': 'Timestamp must be an integer value'}
            command_line = '[%d] %s' % (timestamp, command_line)

        if host or service or user:
            if host:
                command_line = '%s;%s' % (command_line, host)
            if service:
                command_line = '%s;%s' % (command_line, service)
            if user:
                command_line = '%s;%s' % (command_line, user)
        elif element:
            if '/' in element:
                # Replace only the first /
                element = element.replace('/', ';', 1)
            command_line = '%s;%s' % (command_line, element)

        if parameters:
            command_line = '%s;%s' % (command_line, parameters)

        # Add a command to get managed
        logger.debug("Got an external command: %s", command_line)
        self.app.add(ExternalCommand(command_line))

        return {'_status': 'OK', '_message': "Got command: %s" % command_line}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def push_configuration(self, pushed_configuration=None):
        """HTTP POST to the arbiter with the new configuration (master arbiter sends
        its configuration to the spare arbiter)

        :param conf: serialized new configuration
        :type conf:
        :return: None
        """
        pushed_configuration = cherrypy.request.json
        self.app.must_run = False
        return super(ArbiterInterface, self).push_configuration(
            pushed_configuration=pushed_configuration['conf'])

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def do_not_run(self):
        """Master tells to its spare to not run (HTTP GET)
        A master arbiter will ignore this request

        :return: None
        """
        # If I'm the master, ignore the command and raise a log
        if self.app.is_master:
            logger.warning("Received message to not run. "
                           "I am the Master, ignore and continue to run.")
            return False

        # Else, I'm just a spare, so I listen to my master
        logger.debug("Received message to not run. I am the spare, stopping.")
        self.app.last_master_speak = time.time()
        self.app.must_run = False
        return True

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def wait_new_conf(self):
        """Ask the daemon to wait a new conf.
        Reset cur_conf to wait new one

        :return: None
        """
        with self.app.conf_lock:
            logger.warning("My master Arbiter wants me to wait for a new configuration.")
            self.app.cur_conf = {}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_satellites_list(self, daemon_type=''):
        """Get the satellite names sorted by type (HTTP GET)

        :param daemon_type: daemon type to filter
        :type daemon_type: str
        :return: dict with key *daemon_type* and value list of daemon name
        Example ::

         {'poller': ['Poller1', 'Poller2']}

        :rtype: dict
        """
        with self.app.conf_lock:
            res = {}

            for s_type in ['arbiter', 'scheduler', 'poller', 'reactionner', 'receiver', 'broker']:
                if daemon_type and daemon_type != s_type:
                    continue
                satellite_list = []
                res[s_type] = satellite_list
                for daemon_link in getattr(self.app.conf, s_type + 's', []):
                    satellite_list.append(daemon_link.name)
            return res

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_all_states(self):
        """Return all the data of satellites

        :return: dict containing satellites data
        Output looks like this ::

        {'arbiter' : [{'schedproperty1':'value1' ..}, {'pollerproperty1', 'value11' ..}, ..],
        'scheduler': [..],
        'poller': [..],
        'reactionner': [..],
        'receiver': [..],
         'broker: [..]'
        }

        :rtype: dict
        """
        res = {}
        for s_type in ['arbiter', 'scheduler', 'poller', 'reactionner', 'receiver',
                       'broker']:
            lst = []
            res[s_type] = lst
            for daemon in getattr(self.app.conf, s_type + 's'):
                cls = daemon.__class__
                env = {}
                all_props = [cls.properties, cls.running_properties]

                for props in all_props:
                    for prop in props:
                        if not hasattr(daemon, prop):
                            continue
                        if prop in ["realms", "conf", "con", "tags", "modules", "cfg",
                                    "broks", "cfg_to_manage"]:
                            continue
                        val = getattr(daemon, prop)
                        # give a try to a json able object
                        try:
                            json.dumps(val)
                            env[prop] = val
                        except TypeError as exp:
                            logger.warning('get_all_states, %s: %s', prop, str(exp))
                lst.append(env)
        return res

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_objects_properties(self, table):  # pylint: disable=no-self-use, unused-argument
        """'Dump all objects of the required type existing in the configuration:
            - hosts, services, contacts,
            - hostgroups, servicegroups, contactgroups
            - commands, timeperiods
            - ...

        :param table: table name
        :type table: str
        :return: list all properties of all objects
        :rtype: list
        """
        return {'message': "Deprecated in favor of the get_stats endpoint."}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def push_external_command(self, command=None):
        """HTTP POST to the arbiter with the new configuration (master arbiter sends
        its configuration to the spare arbiter)

        :param conf: serialized new configuration
        :type conf:
        :return: None
        """
        if command is None:
            data = cherrypy.request.json
            command = data['command']
        self.app.add(ExternalCommand(command))
        return True
