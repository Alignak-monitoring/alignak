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

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class ArbiterInterface(GenericInterface):
    """Interface for HA Arbiter. The Slave/Master arbiter can get /push conf

    """
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def reload_configuration(self):
        """Ask to the arbiter to reload the monitored configuration

        In case of any error, this function returns an object containing some properties:
        '_status': 'ERR' because of the error
        `_message`: some more explanations about the error

        :return: True if configuration reload is accepted
        """
        # If I'm the master, ignore the command and raise a log
        if not self.app.is_master:
            message = u"I received a request to reload the monitored configuration. " \
                      u"I am not the Master arbiter, I ignore and continue to run."
            logger.warning(message)
            return {'_status': u'ERR', '_message': message}

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

        In case of any error, this function returns an object containing some properties:
        '_status': 'ERR' because of the error
        `_message`: some more explanations about the error

        The `_status` field is 'OK' with an according `_message` to explain what the Arbiter
        will do depending upon the notification.

        :return: dict
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
                message = u"I received a request to reload the monitored configuration. " \
                          u"I am not the Master arbiter, I ignore and continue to run."
                logger.warning(message)
                return {'_status': u'ERR', '_message': message}

            message = "I received a request to reload the monitored configuration."
            if self.app.loading_configuration:
                message += "I am still reloading the monitored configuration ;)"
            logger.warning(message)

            self.app.need_config_reload = True
            return {'_status': u'OK', '_message': message}

        return {'_status': u'OK', '_message': u"No action to do"}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def command(self, command=None):
        """ Request to execute an external command

        Allowed parameters are:
        `command`: mandatory parameter containing the whole command line or only the command name

        `timestamp`: optional parameter containing the timestamp. If not present, the
        current timestamp is added in the command line

        `element`: the targeted element that will be appended after the command name (`command`).
        If element contains a '/' character it is split to make an host and service.

        `host`, `service` or `user`: the targeted host, service or user. Takes precedence over
        the `element` to target a specific element

        `parameters`: the parameter that will be appended after all the arguments

        In case of any error, this function returns an object containing some properties:
        '_status': 'ERR' because of the error
        `_message`: some more explanations about the error

        The `_status` field is 'OK' with an according `_message` to explain what the Arbiter
        will do depending upon the notification. The `command` property contains the formatted
        external command.

        :return: dict
        """
        if cherrypy.request.method != "POST":
            return {'_status': u'ERR', '_message': u'You must only POST on this endpoint.'}

        if cherrypy.request and not cherrypy.request.json:
            return {'_status': u'ERR', '_message': u'You must POST parameters on this endpoint.'}

        logger.debug("Post /command: %s", cherrypy.request.params)
        command = cherrypy.request.json.get('command', None)
        timestamp = cherrypy.request.json.get('timestamp', None)
        element = cherrypy.request.json.get('element', None)
        host = cherrypy.request.json.get('host', None)
        service = cherrypy.request.json.get('service', None)
        user = cherrypy.request.json.get('user', None)
        parameters = cherrypy.request.json.get('parameters', None)

        if not command:
            return {'_status': u'ERR', '_message': u'Missing command parameter'}

        command_line = command.upper()
        if timestamp:
            try:
                timestamp = int(timestamp)
            except ValueError:
                return {'_status': u'ERR', '_message': u'Timestamp must be an integer value'}
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
        logger.warning("Got an external command: %s", command_line)
        self.app.add(ExternalCommand(command_line))

        return {'_status': u'OK',
                '_message': u"Got command: %s" % command_line,
                'command': command_line}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def push_configuration(self, pushed_configuration=None):
        """Send a new configuration to the daemon

        Used by the master arbiter to send its configuration to a spare arbiter

        This function is not intended for external use. It is quite complex to
        build a configuration for a daemon and it is the arbter dispatcher job ;)

        :param pushed_configuration: new conf to send
        :return: None
        """
        pushed_configuration = cherrypy.request.json
        self.app.must_run = False
        return super(ArbiterInterface, self).push_configuration(
            pushed_configuration=pushed_configuration['conf'])

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def do_not_run(self):
        """The master arbiter tells to its spare arbiters to not run.

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
        """Ask the daemon to drop its configuration and wait for a new one

        :return: None
        """
        with self.app.conf_lock:
            logger.warning("My master Arbiter wants me to wait for a new configuration.")
            self.app.cur_conf = {}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_alignak_status(self, details=False):
        """Get the overall alignak status

        Returns a list of the satellites as in:
        {
            'scheduler': ['Scheduler1']
            'poller': ['Poller1', 'Poller2']
            ...
        }

        :param details: Details are required (different from 0)
        :type details str

        :return: dict with key *daemon_type* and value list of daemon name
        :rtype: dict
        """
        if details is not False:
            details = bool(details)

        return self.app.push_passive_check(details=details)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_satellites_list(self, daemon_type=''):
        """Get the arbiter satellite names sorted by type

        Returns a list of the satellites as in:
        {
            'scheduler': ['Scheduler1']
            'poller': ['Poller1', 'Poller2']
            ...
        }

        If a specific daemon type is requested, the list is reduced to this unique daemon type.

        :param daemon_type: daemon type to filter
        :type daemon_type: str
        :return: dict with key *daemon_type* and value list of daemon name
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
    def get_satellites_configuration(self):
        """Return all the configuration data of satellites

        :return: dict containing satellites data
        Output looks like this ::

        {'arbiter' : [{'property1':'value1' ..}, {'property2', 'value11' ..}, ..],
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
        return {'_status': u'ERR',
                '_message': u"Deprecated in favor of the get_stats endpoint."}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def push_external_command(self, command=None):
        """Only to maintain ascending compatibility... this function uses the inner
        *command* endpoint.

        :param command: Alignak external command
        :type command: string
        :return: None
        """
        return self.command(command=command)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_monitoring_problems(self):
        """Get Alignak detailed monitoring status

        This will return an object containing the properties of the `get_id`, plus a `problems`
        object which contains 2 properties for each known scheduler:
        - _freshness, which is the timestamp when the provided data were fetched
        - problems, which is an object with the scheduler known problems:

        {
            ...

            "problems": {
                "scheduler-master": {
                    "_freshness": 1528903945,
                    "problems": {
                        "fdfc986d-4ab4-4562-9d2f-4346832745e6": {
                            "last_state": "CRITICAL",
                            "service": "dummy_critical",
                            "last_state_type": "SOFT",
                            "last_state_update": 1528902442,
                            "last_hard_state": "CRITICAL",
                            "last_hard_state_change": 1528902442,
                            "last_state_change": 1528902381,
                            "state": "CRITICAL",
                            "state_type": "HARD",
                            "host": "host-all-8",
                            "output": "Hi, checking host-all-8/dummy_critical -> exit=2"
                        },
                        "2445f2a3-2a3b-4b13-96ed-4cfb60790e7e": {
                            "last_state": "WARNING",
                            "service": "dummy_warning",
                            "last_state_type": "SOFT",
                            "last_state_update": 1528902463,
                            "last_hard_state": "WARNING",
                            "last_hard_state_change": 1528902463,
                            "last_state_change": 1528902400,
                            "state": "WARNING",
                            "state_type": "HARD",
                            "host": "host-all-6",
                            "output": "Hi, checking host-all-6/dummy_warning -> exit=1"
                        },
                        ...
                    }
                }
            }
        }

        :return: schedulers live synthesis list
        :rtype: dict
        """
        res = self.get_id()
        res.update(self.get_start_time())
        res.update(self.app.get_monitoring_problems())
        return res

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_livesynthesis(self):
        """Get Alignak live synthesis

        This will return an object containing the properties of the `get_id`, plus a `livesynthesis`
        object which contains 2 properties for each known scheduler:
        - _freshness, which is the timestamp when the provided data were fetched
        - livesynthesis, which is an object with the scheduler live synthesis.

        An `_overall` fake scheduler is also contained in the schedulers list to provide the
        cumulated live synthesis. Before sending the results, the arbiter sums-up all its
        schedulers live synthesis counters in the `_overall` live synthesis.

        {
            ...

            "livesynthesis": {
                "_overall": {
                    "_freshness": 1528947526,
                    "livesynthesis": {
                        "hosts_total": 11,
                        "hosts_not_monitored": 0,
                        "hosts_up_hard": 11,
                        "hosts_up_soft": 0,
                        "hosts_down_hard": 0,
                        "hosts_down_soft": 0,
                        "hosts_unreachable_hard": 0,
                        "hosts_unreachable_soft": 0,
                        "hosts_flapping": 0,
                        "hosts_acknowledged": 0,
                        "hosts_in_downtime": 0,
                        "services_total": 100,
                        "services_not_monitored": 0,
                        "services_ok_hard": 70,
                        "services_ok_soft": 0,
                        "services_warning_hard": 4,
                        "services_warning_soft": 6,
                        "services_critical_hard": 6,
                        "services_critical_soft": 4,
                        "services_unknown_hard": 3,
                        "services_unknown_soft": 7,
                        "services_unreachable_hard": 0,
                        "services_unreachable_soft": 0,
                        "services_flapping": 0,
                        "services_acknowledged": 0,
                        "services_in_downtime": 0
                        }
                    }
                },
                "scheduler-master": {
                    "_freshness": 1528947522,
                    "livesynthesis": {
                        "hosts_total": 11,
                        "hosts_not_monitored": 0,
                        "hosts_up_hard": 11,
                        "hosts_up_soft": 0,
                        "hosts_down_hard": 0,
                        "hosts_down_soft": 0,
                        "hosts_unreachable_hard": 0,
                        "hosts_unreachable_soft": 0,
                        "hosts_flapping": 0,
                        "hosts_acknowledged": 0,
                        "hosts_in_downtime": 0,
                        "services_total": 100,
                        "services_not_monitored": 0,
                        "services_ok_hard": 70,
                        "services_ok_soft": 0,
                        "services_warning_hard": 4,
                        "services_warning_soft": 6,
                        "services_critical_hard": 6,
                        "services_critical_soft": 4,
                        "services_unknown_hard": 3,
                        "services_unknown_soft": 7,
                        "services_unreachable_hard": 0,
                        "services_unreachable_soft": 0,
                        "services_flapping": 0,
                        "services_acknowledged": 0,
                        "services_in_downtime": 0
                        }
                    }
                }
            }
        }

        :return: scheduler live synthesis
        :rtype: dict
        """
        res = self.get_id()
        res.update(self.get_start_time())
        res.update(self.app.get_livesynthesis())
        return res
