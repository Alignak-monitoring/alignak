# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines
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
"""This module provides a specific HTTP interface for a Arbiter."""

import time
import logging
import json
import cherrypy

from alignak.http.generic_interface import GenericInterface
from alignak.util import split_semicolon
from alignak.external_command import ExternalCommand

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

GRAFANA_TARGETS = ['events_log', 'problems_log']


class ArbiterInterface(GenericInterface):
    """This module provide a specific HTTP interface for an Arbiter daemon."""

    #####
    #   _____                                           _
    #  | ____| __  __  _ __     ___    ___    ___    __| |
    #  |  _|   \ \/ / | '_ \   / _ \  / __|  / _ \  / _` |
    #  | |___   >  <  | |_) | | (_) | \__ \ |  __/ | (_| |
    #  |_____| /_/\_\ | .__/   \___/  |___/  \___|  \__,_|
    #                 |_|
    #####

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def reload_configuration(self):
        """Ask to the arbiter to reload the monitored configuration

        **Note** tha the arbiter will not reload its main configuration file (eg. alignak.ini)
        but it will reload the monitored objects from the Nagios legacy files or from the
        Alignak backend!

        In case of any error, this function returns an object containing some properties:
        '_status': 'ERR' because of the error
        `_message`: some more explanations about the error

        :return: True if configuration reload is accepted
        """
        # If I'm not the master arbiter, ignore the command and raise a log
        if not self.app.is_master:
            message = u"I received a request to reload the monitored configuration. " \
                      u"I am not the Master arbiter, I ignore and continue to run."
            logger.warning(message)
            return {'_status': u'ERR', '_message': message}

        message = "I received a request to reload the monitored configuration"
        if self.app.loading_configuration:
            message = message + "and I am still reloading the monitored configuration ;)"
        else:
            self.app.need_config_reload = True
        logger.warning(message)

        return {'_status': u'OK', '_message': message}

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
    def command(self, command=None,
                timestamp=None, element=None, host=None, service=None, user=None, parameters=None):
        # pylint: disable=too-many-branches
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

        When using this endpoint with the HTTP GET method, the semi colons that are commonly used
        to separate the parameters must be replace with %3B! This because the ; is an accepted
        URL query parameters separator...

        Indeed, the recommended way of using this endpoint is to use the HTTP POST method.

        In case of any error, this function returns an object containing some properties:
        '_status': 'ERR' because of the error
        `_message`: some more explanations about the error

        The `_status` field is 'OK' with an according `_message` to explain what the Arbiter
        will do depending upon the notification. The `command` property contains the formatted
        external command.

        :return: dict
        """
        if cherrypy.request.method in ["POST"]:
            if not cherrypy.request.json:
                return {'_status': u'ERR',
                        '_message': u'You must POST parameters on this endpoint.'}

        if command is None:
            try:
                command = cherrypy.request.json.get('command', None)
                timestamp = cherrypy.request.json.get('timestamp', None)
                element = cherrypy.request.json.get('element', None)
                host = cherrypy.request.json.get('host', None)
                service = cherrypy.request.json.get('service', None)
                user = cherrypy.request.json.get('user', None)
                parameters = cherrypy.request.json.get('parameters', None)
            except AttributeError:
                return {'_status': u'ERR', '_message': u'Missing command parameters'}

        if not command:
            return {'_status': u'ERR', '_message': u'Missing command parameter'}

        fields = split_semicolon(command)
        command_line = command.replace(fields[0], fields[0].upper())
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
    @cherrypy.tools.json_out()
    def problems(self):
        """Alias for monitoring_problems"""
        return self.monitoring_problems

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def monitoring_problems(self):
        """Get Alignak detailed monitoring status

        This will return an object containing the properties of the `identity`, plus a `problems`
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
        res = self.identity()
        res['problems'] = {}
        for scheduler_link in self.app.conf.schedulers:
            sched_res = scheduler_link.con.get('monitoring_problems', wait=True)
            res['problems'][scheduler_link.name] = {}
            if '_freshness' in sched_res:
                res['problems'][scheduler_link.name].update({'_freshness': sched_res['_freshness']})
            if 'problems' in sched_res:
                res['problems'][scheduler_link.name].update({'problems': sched_res['problems']})
        res['_freshness'] = int(time.time())

        return res

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def livesynthesis(self):
        """Get Alignak live synthesis

        This will return an object containing the properties of the `identity`, plus a
        `livesynthesis`
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
                        "hosts_problems": 0,
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
                        "services_problems": 0,
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
                        "hosts_problems": 0,
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
                        "services_problems": 0,
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
        res = self.identity()
        res.update(self.app.get_livesynthesis())
        return res

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def object(self, o_type, o_name=None):
        """Get a monitored object from the arbiter.

        Indeed, the arbiter requires the object from its schedulers. It will iterate in
        its schedulers list until a matching object is found. Else it will return a Json
        structure containing _status and _message properties.

        When found, the result is a serialized object which is a Json structure containing:
        - content: the serialized object content
        - __sys_python_module__: the python class of the returned object

        The Alignak unserialize function of the alignak.misc.serialization package allows
        to restore the initial object.

        .. code-block:: python

            from alignak.misc.serialization import unserialize
            from alignak.objects.hostgroup import Hostgroup
            raw_data = req.get("http://127.0.0.1:7768/object/hostgroup/allhosts")
            print("Got: %s / %s" % (raw_data.status_code, raw_data.content))
            assert raw_data.status_code == 200
            object = raw_data.json()
            group = unserialize(object, True)
            assert group.__class__ == Hostgroup
            assert group.get_name() == 'allhosts'

        As an example:
        {
            "__sys_python_module__": "alignak.objects.hostgroup.Hostgroup",
            "content": {
                "uuid": "32248642-97dd-4f39-aaa2-5120112a765d",
                "name": "",
                "hostgroup_name": "allhosts",
                "use": [],
                "tags": [],
                "alias": "All Hosts",
                "notes": "",
                "definition_order": 100,
                "register": true,
                "unknown_members": [],
                "notes_url": "",
                "action_url": "",

                "imported_from": "unknown",
                "conf_is_correct": true,
                "configuration_errors": [],
                "configuration_warnings": [],
                "realm": "",
                "downtimes": {},
                "hostgroup_members": [],
                "members": [
                    "553d47bc-27aa-426c-a664-49c4c0c4a249",
                    "f88093ca-e61b-43ff-a41e-613f7ad2cea2",
                    "df1e2e13-552d-43de-ad2a-fe80ad4ba979",
                    "d3d667dd-f583-4668-9f44-22ef3dcb53ad"
                ]
            }
        }

        :param o_type: searched object type
        :type o_type: str
        :param o_name: searched object name (or uuid)
        :type o_name: str
        :return: serialized object information
        :rtype: str
        """
        for scheduler_link in self.app.conf.schedulers:
            sched_res = scheduler_link.con.get('object', {'o_type': o_type, 'o_name': o_name},
                                               wait=True)
            if isinstance(sched_res, dict) and 'content' in sched_res:
                return sched_res
        return {'_status': u'ERR', '_message': u'Required %s not found.' % o_type}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def dump(self, o_name=None, details=False, raw=False):
        """Dump an host (all hosts) from the arbiter.

        The arbiter will get the host (all hosts) information from all its schedulers.

        This gets the main host information from the scheduler. If details is set, then some
        more information are provided. This will not get all the host known attributes but only
        a reduced set that will inform about the host and its services status

        If raw is set the information are provided in two string lists formated as CSV strings.
        The first list element contains the hosts information and the second one contains the
        services information.

        If an host name is provided, this function will get only this host information, else
        all the scheduler hosts are returned.

        As an example (in raw format):
        {
            scheduler-master-3: [
                [
                    "type;host;name;last_check;state_id;state;state_type;is_problem;
                    is_impact;output",
                    "localhost;host;localhost;1532451740;0;UP;HARD;False;False;
                    Host assumed to be UP",
                    "host_2;host;host_2;1532451988;1;DOWN;HARD;True;False;I am always Down"
                ],
                [
                    "type;host;name",
                    "host_2;service;dummy_no_output;1532451981;0;OK;HARD;False;True;
                    Service internal check result: 0",
                    "host_2;service;dummy_warning;1532451960;4;UNREACHABLE;HARD;False;True;
                    host_2-dummy_warning-1",
                    "host_2;service;dummy_unreachable;1532451987;4;UNREACHABLE;HARD;False;True;
                    host_2-dummy_unreachable-4",
                    "host_2;service;dummy_random;1532451949;4;UNREACHABLE;HARD;False;True;
                    Service internal check result: 2",
                    "host_2;service;dummy_ok;1532452002;0;OK;HARD;False;True;host_2",
                    "host_2;service;dummy_critical;1532451953;4;UNREACHABLE;HARD;False;True;
                    host_2-dummy_critical-2",
                    "host_2;service;dummy_unknown;1532451945;4;UNREACHABLE;HARD;False;True;
                    host_2-dummy_unknown-3",
                    "host_2;service;dummy_echo;1532451973;4;UNREACHABLE;HARD;False;True;"
                ]
            ],
            scheduler-master-2: [
            [
                "type;host;name;last_check;state_id;state;state_type;is_problem;is_impact;output",
                "host_0;host;host_0;1532451993;0;UP;HARD;False;False;I am always Up",
                "BR_host;host;BR_host;1532451991;0;UP;HARD;False;False;Host assumed to be UP"
            ],
            [
                "type;host;name;last_check;state_id;state;state_type;is_problem;is_impact;output",
                "host_0;service;dummy_no_output;1532451970;0;OK;HARD;False;False;
                Service internal check result: 0",
                "host_0;service;dummy_unknown;1532451964;3;UNKNOWN;HARD;True;False;
                host_0-dummy_unknown-3",
                "host_0;service;dummy_random;1532451991;1;WARNING;HARD;True;False;
                Service internal check result: 1",
                "host_0;service;dummy_warning;1532451945;1;WARNING;HARD;True;False;
                host_0-dummy_warning-1",
                "host_0;service;dummy_unreachable;1532451986;4;UNREACHABLE;HARD;True;False;
                host_0-dummy_unreachable-4",
                "host_0;service;dummy_ok;1532452012;0;OK;HARD;False;False;host_0",
                "host_0;service;dummy_critical;1532451987;2;CRITICAL;HARD;True;False;
                host_0-dummy_critical-2",
                "host_0;service;dummy_echo;1532451963;0;OK;HARD;False;False;",
                "BR_host;service;dummy_critical;1532451970;2;CRITICAL;HARD;True;False;
                BR_host-dummy_critical-2",
                "BR_host;service;BR_Simple_And;1532451895;1;WARNING;HARD;True;True;",
                "BR_host;service;dummy_unreachable;1532451981;4;UNREACHABLE;HARD;True;False;
                BR_host-dummy_unreachable-4",
                "BR_host;service;dummy_no_output;1532451975;0;OK;HARD;False;False;
                Service internal check result: 0",
                "BR_host;service;dummy_unknown;1532451955;3;UNKNOWN;HARD;True;False;
                BR_host-dummy_unknown-3",
                "BR_host;service;dummy_echo;1532451981;0;OK;HARD;False;False;",
                "BR_host;service;dummy_warning;1532451972;1;WARNING;HARD;True;False;
                BR_host-dummy_warning-1",
                "BR_host;service;dummy_random;1532451976;4;UNREACHABLE;HARD;True;False;
                Service internal check result: 4",
                "BR_host;service;dummy_ok;1532451972;0;OK;HARD;False;False;BR_host"
            ]
        ],
        ...

        More information are available in the scheduler correponding API endpoint.

        :param o_type: searched object type
        :type o_type: str
        :param o_name: searched object name (or uuid)
        :type o_name: str
        :return: serialized object information
        :rtype: str
        """
        if details is not False:
            details = bool(details)
        if raw is not False:
            raw = bool(raw)

        res = {}
        for scheduler_link in self.app.conf.schedulers:
            sched_res = scheduler_link.con.get('dump', {'o_name': o_name,
                                                        'details': '1' if details else '',
                                                        'raw': '1' if raw else ''},
                                               wait=True)
            if isinstance(sched_res, dict) and \
                    '_status' in sched_res and sched_res['_status'] == 'ERR':
                continue
            res[scheduler_link.name] = sched_res
        return res

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def status(self, details=False):
        """Get the overall alignak status

        Returns a list of the satellites as in:
        {
            services: [
                {
                    livestate: {
                        perf_data: "",
                        timestamp: 1532106561,
                        state: "ok",
                        long_output: "",
                        output: "all daemons are up and running."
                    },
                    name: "arbiter-master"
                },
                {
                    livestate: {
                        name: "poller_poller-master",
                        timestamp: 1532106561,
                        long_output: "Realm: (True). Listening on: http://127.0.0.1:7771/",
                        state: "ok",
                        output: "daemon is alive and reachable.",
                        perf_data: "last_check=1532106560.17"
                    },
                    name: "poller-master"
                },
                ...
                ...
            ],
            variables: { },
            livestate: {
                timestamp: 1532106561,
                long_output: "broker-master - daemon is alive and reachable.
                poller-master - daemon is alive and reachable.
                reactionner-master - daemon is alive and reachable.
                receiver-master - daemon is alive and reachable.
                receiver-nsca - daemon is alive and reachable.
                scheduler-master - daemon is alive and reachable.
                scheduler-master-2 - daemon is alive and reachable.
                scheduler-master-3 - daemon is alive and reachable.",
                state: "up",
                output: "All my daemons are up and running.",
                perf_data: "
                    'servicesextinfo'=0 'businessimpactmodulations'=0 'hostgroups'=2
                    'resultmodulations'=0 'escalations'=0 'schedulers'=3 'hostsextinfo'=0
                    'contacts'=2 'servicedependencies'=0 'servicegroups'=1 'pollers'=1
                    'arbiters'=1 'receivers'=2 'macromodulations'=0 'reactionners'=1
                    'contactgroups'=2 'brokers'=1 'realms'=3 'services'=32 'commands'=11
                    'notificationways'=2 'timeperiods'=4 'modules'=0 'checkmodulations'=0
                    'hosts'=6 'hostdependencies'=0"
            },
            name: "My Alignak",
            template: {
                notes: "",
                alias: "My Alignak",
                _templates: [
                    "alignak",
                    "important"
                ],
                active_checks_enabled: false,
                passive_checks_enabled: true
            }
        }

        :param details: Details are required (different from 0)
        :type details bool

        :return: dict with key *daemon_type* and value list of daemon name
        :rtype: dict
        """
        if details is not False:
            details = bool(details)

        return self.app.get_alignak_status(details=details)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def events_log(self, details=False):
        """Get the most recent Alignak events

        The arbiter maintains a list of the most recent Alignak events. This endpoint
        provides this list.

        The default format is:
        [
            "2018-07-23 15:14:43 - E - SERVICE NOTIFICATION: guest;host_0;dummy_random;CRITICAL;1;
            notify-service-by-log;Service internal check result: 2",
            "2018-07-23 15:14:43 - E - SERVICE NOTIFICATION: admin;host_0;dummy_random;CRITICAL;1;
            notify-service-by-log;Service internal check result: 2",
            "2018-07-23 15:14:42 - E - SERVICE ALERT: host_0;dummy_critical;CRITICAL;SOFT;1;
            host_0-dummy_critical-2",
            "2018-07-23 15:14:42 - E - SERVICE ALERT: host_0;dummy_random;CRITICAL;HARD;2;
            Service internal check result: 2",
            "2018-07-23 15:14:42 - I - SERVICE ALERT: host_0;dummy_unknown;UNKNOWN;HARD;2;
            host_0-dummy_unknown-3"
        ]

        If you request on this endpoint with the *details* parameter (whatever its value...),
        you will get a detailed JSON output:
        [
            {
                timestamp: 1535517701.1817362,
                date: "2018-07-23 15:16:35",
                message: "SERVICE ALERT: host_11;dummy_echo;UNREACHABLE;HARD;2;",
                level: "info"
            },
            {
                timestamp: 1535517701.1817362,
                date: "2018-07-23 15:16:32",
                message: "SERVICE NOTIFICATION: guest;host_0;dummy_random;OK;0;
                        notify-service-by-log;Service internal check result: 0",
                level: "info"
            },
            {
                timestamp: 1535517701.1817362,
                date: "2018-07-23 15:16:32",
                message: "SERVICE NOTIFICATION: admin;host_0;dummy_random;OK;0;
                        notify-service-by-log;Service internal check result: 0",
                level: "info"
            },
            {
                timestamp: 1535517701.1817362,
                date: "2018-07-23 15:16:32",
                message: "SERVICE ALERT: host_0;dummy_random;OK;HARD;2;
                        Service internal check result: 0",
                level: "info"
            },
            {
                timestamp: 1535517701.1817362,
                date: "2018-07-23 15:16:19",
                message: "SERVICE ALERT: host_11;dummy_random;OK;HARD;2;
                        Service internal check result: 0",
                level: "info"
            }
        ]

        In this example, only the 5 most recent events are provided whereas the default value is
        to provide the 100 last events. This default counter may be changed thanks to the
        ``events_log_count`` configuration variable or
        ``ALIGNAK_EVENTS_LOG_COUNT`` environment variable.

        The date format may also be changed thanks to the ``events_date_format`` configuration
        variable.

        :return: list of the most recent events
        :rtype: list
        """
        res = []
        for log in reversed(self.app.recent_events):
            if details:
                # Exposes the full object
                res.append(log)
            else:
                res.append("%s - %s - %s"
                           % (log['date'], log['level'][0].upper(), log['message']))
        return res

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def satellites_list(self, daemon_type=''):
        """Get the arbiter satellite names sorted by type

        Returns a list of the satellites as in:
        {
            reactionner: [
                "reactionner-master"
            ],
            broker: [
                "broker-master"
            ],
            arbiter: [
                "arbiter-master"
            ],
            scheduler: [
                "scheduler-master-3",
                "scheduler-master",
                "scheduler-master-2"
            ],
            receiver: [
                "receiver-nsca",
                "receiver-master"
            ],
            poller: [
                "poller-master"
            ]
        }

        If a specific daemon type is requested, the list is reduced to this unique daemon type:
        {
            scheduler: [
                "scheduler-master-3",
                "scheduler-master",
                "scheduler-master-2"
            ]
        }

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
    def realms(self, details=False):
        """Return the realms / satellites configuration

        Returns an object containing the hierarchical realms configuration with the main
        information about each realm:
        {
            All: {
                satellites: {
                    pollers: [
                        "poller-master"
                    ],
                    reactionners: [
                        "reactionner-master"
                    ],
                    schedulers: [
                        "scheduler-master", "scheduler-master-3", "scheduler-master-2"
                    ],
                    brokers: [
                    "broker-master"
                    ],
                    receivers: [
                    "receiver-master", "receiver-nsca"
                    ]
                },
                children: { },
                name: "All",
                members: [
                    "host_1", "host_0", "host_3", "host_2", "host_11", "localhost"
                ],
                level: 0
            },
            North: {
                ...
            }
        }

        Sub realms defined inside a realm are provided in the `children` property of their
        parent realm and they contain the same information as their parent..
        The `members` realm contain the list of the hosts members of the realm.

        If ``details`` is required, each realm will contain more information about each satellite
        involved in the realm management:
        {
            All: {
                satellites: {
                    pollers: [
                        {
                            passive: false,
                            name: "poller-master",
                            livestate_output: "poller/poller-master is up and running.",
                            reachable: true,
                            uri: "http://127.0.0.1:7771/",
                            alive: true,
                            realm_name: "All",
                            manage_sub_realms: true,
                            spare: false,
                            polling_interval: 5,
                            configuration_sent: true,
                            active: true,
                            livestate: 0,
                            max_check_attempts: 3,
                            last_check: 1532242300.593074,
                            type: "poller"
                        }
                    ],
                    reactionners: [
                        {
                            passive: false,
                            name: "reactionner-master",
                            livestate_output: "reactionner/reactionner-master is up and running.",
                            reachable: true,
                            uri: "http://127.0.0.1:7769/",
                            alive: true,
                            realm_name: "All",
                            manage_sub_realms: true,
                            spare: false,
                            polling_interval: 5,
                            configuration_sent: true,
                            active: true,
                            livestate: 0,
                            max_check_attempts: 3,
                            last_check: 1532242300.587762,
                            type: "reactionner"
                        }
                    ]

        :return: dict containing realms / satellites
        :rtype: dict
        """
        def get_realm_info(realm, realms, satellites, details=False):
            """Get the realm and its children information

            :return: None
            """
            res = {
                "name": realm.get_name(),
                "level": realm.level,
                "hosts": realm.members,
                "hostgroups": realm.group_members,
                "children": {},
                "satellites": {
                }
            }
            for child in realm.realm_members:
                child = realms.find_by_name(child)
                if not child:
                    continue
                realm_infos = get_realm_info(child, realms, satellites, details=details)
                res['children'][child.get_name()] = realm_infos

            for sat_type in ['scheduler', 'reactionner', 'broker', 'receiver', 'poller']:
                res["satellites"][sat_type + 's'] = []

                sats = realm.get_potential_satellites_by_type(satellites, sat_type)
                for sat in sats:
                    if details:
                        res["satellites"][sat_type + 's'][sat.name] = sat.give_satellite_json()
                    else:
                        res["satellites"][sat_type + 's'].append(sat.name)

            return res

        if details is not False:
            details = bool(details)

        # Report our daemons states, but only if a dispatcher and the configuration is loaded
        if not getattr(self.app, 'dispatcher', None) or not getattr(self.app, 'conf', None):
            return {'_status': u'ERR', '_message': "Not yet available. Please come back later."}

        res = {}
        higher_realms = [realm for realm in self.app.conf.realms if realm.level == 0]
        for realm in higher_realms:
            res[realm.get_name()] = get_realm_info(realm, self.app.conf.realms,
                                                   self.app.dispatcher.all_daemons_links)

        return res

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def system(self, details=False):
        """Return the realms / satellites configuration

        Returns an object containing the hierarchical realms configuration with the main
        information about each realm:
        {
            All: {
                satellites: {
                    pollers: [
                        "poller-master"
                    ],
                    reactionners: [
                        "reactionner-master"
                    ],
                    schedulers: [
                        "scheduler-master", "scheduler-master-3", "scheduler-master-2"
                    ],
                    brokers: [
                    "broker-master"
                    ],
                    receivers: [
                    "receiver-master", "receiver-nsca"
                    ]
                },
                children: { },
                name: "All",
                members: [
                    "host_1", "host_0", "host_3", "host_2", "host_11", "localhost"
                ],
                level: 0
            },
            North: {
                ...
            }
        }

        Sub realms defined inside a realm are provided in the `children` property of their
        parent realm and they contain the same information as their parent..
        The `members` realm contain the list of the hosts members of the realm.

        If ``details`` is required, each realm will contain more information about each satellite
        involved in the realm management:
        {
            All: {
                satellites: {
                    pollers: [
                        {
                            passive: false,
                            name: "poller-master",
                            livestate_output: "poller/poller-master is up and running.",
                            reachable: true,
                            uri: "http://127.0.0.1:7771/",
                            alive: true,
                            realm_name: "All",
                            manage_sub_realms: true,
                            spare: false,
                            polling_interval: 5,
                            configuration_sent: true,
                            active: true,
                            livestate: 0,
                            max_check_attempts: 3,
                            last_check: 1532242300.593074,
                            type: "poller"
                        }
                    ],
                    reactionners: [
                        {
                            passive: false,
                            name: "reactionner-master",
                            livestate_output: "reactionner/reactionner-master is up and running.",
                            reachable: true,
                            uri: "http://127.0.0.1:7769/",
                            alive: true,
                            realm_name: "All",
                            manage_sub_realms: true,
                            spare: false,
                            polling_interval: 5,
                            configuration_sent: true,
                            active: true,
                            livestate: 0,
                            max_check_attempts: 3,
                            last_check: 1532242300.587762,
                            type: "reactionner"
                        }
                    ]

        :return: dict containing realms / satellites
        :rtype: dict
        """
        def get_realm_info(realm, realms, satellites, details=False):
            """Get the realm and its children information

            :return: None
            """
            res = {
                "name": realm.get_name(),
                "level": realm.level,
                "hosts": realm.members,
                "groups": realm.group_members,
                "children": {},
                "satellites": {
                }
            }
            for child in realm.realm_members:
                child = realms.find_by_name(child)
                if not child:
                    continue
                realm_infos = get_realm_info(child, realms, satellites, details=details)
                res['children'][child.get_name()] = realm_infos

            for sat_type in ['scheduler', 'reactionner', 'broker', 'receiver', 'poller']:
                res["satellites"][sat_type + 's'] = []

                sats = realm.get_potential_satellites_by_type(satellites, sat_type)
                for sat in sats:
                    if details:
                        res["satellites"][sat_type + 's'][sat.name] = sat.give_satellite_json()
                    else:
                        res["satellites"][sat_type + 's'].append(sat.name)

            return res

        if details is not False:
            details = bool(details)

        # Report our daemons states, but only if a dispatcher and the configuration is loaded
        if not getattr(self.app, 'dispatcher', None) or not getattr(self.app, 'conf', None):
            return {'_status': u'ERR', '_message': "Not yet available. Please come back later."}

        res = {}
        higher_realms = [realm for realm in self.app.conf.realms if realm.level == 0]
        for realm in higher_realms:
            res[realm.get_name()] = get_realm_info(realm, self.app.conf.realms,
                                                   self.app.dispatcher.all_daemons_links)

        return res

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def satellites_configuration(self):
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
                            logger.warning('satellites_configuration, %s: %s', prop, str(exp))
                lst.append(env)
        return res

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def external_commands(self):
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

    #####
    #    ____                   __
    #   / ___|  _ __    __ _   / _|   __ _   _ __     __ _
    #  | |  _  | '__|  / _` | | |_   / _` | | '_ \   / _` |
    #  | |_| | | |    | (_| | |  _| | (_| | | | | | | (_| |
    #   \____| |_|     \__,_| |_|    \__,_| |_| |_|  \__,_|
    #
    #####

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def search(self):  # pylint: disable=no-self-use
        """
        Request available queries

        Posted data: {u'target': u''}

        Return the list of available target queries

        :return: See upper comment
        :rtype: list
        """
        logger.debug("Grafana search... %s", cherrypy.request.method)
        if cherrypy.request.method == 'OPTIONS':
            cherrypy.response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PATCH,PUT,DELETE'
            cherrypy.response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
            cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
            cherrypy.request.handler = None
            return {}

        if getattr(cherrypy.request, 'json', None):
            logger.debug("Posted data: %s", cherrypy.request.json)

        logger.debug("Grafana search returns: %s", GRAFANA_TARGETS)
        return GRAFANA_TARGETS

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def query(self):
        """
        Request object passed to datasource.query function:

        {
            'timezone': 'browser',
            'panelId': 38,
            'range': {
                'from': '2018-08-29T02:38:09.633Z',
                'to': '2018-08-29T03:38:09.633Z',
                'raw': {'from': 'now-1h', 'to': 'now'}
            },
            'rangeRaw': {'from': 'now-1h', 'to': 'now'},
            'interval': '10s',
            'intervalMs': 10000,
            'targets': [
                {
                    'target': 'problems', 'refId': 'A', 'type': 'table'}
            ],
            'format': 'json',
            'maxDataPoints': 314,
            'scopedVars': {
                '__interval': {'text': '10s', 'value': '10s'},
                '__interval_ms': {'text': 10000, 'value': 10000}
            }
        }

        Only the first target is considered. If several targets are required, an error is raised.

        The target is a string that is searched in the target_queries dictionary. If found
        the corresponding query is executed and the result is returned.

        Table response from datasource.query. An array of:

        [
          {
            "type": "table",
            "columns": [
              {
                "text": "Time",
                "type": "time",
                "sort": true,
                "desc": true,
              },
              {
                "text": "mean",
              },
              {
                "text": "sum",
              }
            ],
            "rows": [
              [
                1457425380000,
                null,
                null
              ],
              [
                1457425370000,
                1002.76215352,
                1002.76215352
              ],
            ]
          }
        ]
        :return: See upper comment
        :rtype: list
        """
        logger.debug("Grafana query... %s", cherrypy.request.method)
        if cherrypy.request.method == 'OPTIONS':
            cherrypy.response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PATCH,PUT,DELETE'
            cherrypy.response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
            cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
            cherrypy.request.handler = None
            return {}

        if getattr(cherrypy.request, 'json', None):
            posted_data = cherrypy.request.json
            logger.debug("Posted data: %s", cherrypy.request.json)

        targets = None
        target = None
        try:
            targets = posted_data.get("targets")
            assert targets
            assert len(targets) == 1
            target = targets[0].get("target")
        except Exception as exp:  # pylint: disable=broad-except
            cherrypy.response.status = 409
            return {'_status': u'ERR', '_message': u'Request error: %s.' % exp}

        resp = []
        if target in ['events_log']:
            resp = [{
                "type": "table",
                "columns": [
                    {
                        "text": "Time",
                        "type": "time",
                        "sort": True,
                        "desc": True
                    },
                    {
                        "text": "Severity",
                        "type": "integer"
                    },
                    {
                        "text": "Message",
                        "type": "string"
                    }
                ],
                "rows": []
            }]

            severity = {
                "info": 0,
                'warning': 1,
                'error': 2,
                'critical': 3
            }
            for log in reversed(self.app.recent_events):
                # 0 for the first required target
                # timestamp must be precise on ms for Grafana
                resp[0]['rows'].append([log['timestamp'] * 1000,
                                        severity.get(log['level'].lower(), 3), log['message']])

        if target in ['problems_log']:
            resp = [{
                "type": "table",
                "columns": [
                    {
                        "text": "Raised",
                        "type": "time",
                        "sort": True,
                        "desc": True
                    },
                    {
                        "text": "Severity",
                        "type": "integer"
                    },
                    {
                        "text": "Host",
                        "type": "string"
                    },
                    {
                        "text": "Service",
                        "type": "string"
                    },
                    {
                        "text": "State",
                        "type": "integer"
                    },
                    {
                        "text": "Output",
                        "type": "string"
                    }
                ],
                "rows": []
            }]

            severity = {
                "up": 0,
                'down': 2,
                'ok': 0,
                'warning': 1,
                'critical': 2
            }

            problems = {}
            for scheduler_link in self.app.conf.schedulers:
                sched_res = scheduler_link.con.get('monitoring_problems', wait=True)
                if 'problems' in sched_res:
                    problems.update(sched_res['problems'])

            # todo: add a sorting
            for problem_uuid in problems:
                log = problems[problem_uuid]

                # 0 for the first required target
                resp[0]['rows'].append([log['last_hard_state_change'] * 1000,
                                        severity.get(log['state'].lower(), 3),
                                        log['host'], log['service'], log['state'], log['output']])

        return resp

    #####
    #      _      _   _                           _
    #     / \    | | (_)   __ _   _ __     __ _  | | __
    #    / _ \   | | | |  / _` | | '_ \   / _` | | |/ /
    #   / ___ \  | | | | | (_| | | | | | | (_| | |   <
    #  /_/   \_\ |_| |_|  \__, | |_| |_|  \__,_| |_|\_\
    #                     |___/
    #####
    def _build_host_livestate(self, host_name, livestate):
        # pylint: disable=no-self-use, too-many-locals
        """Build and notify the external command for an host livestate

        PROCESS_HOST_CHECK_RESULT;<host_name>;<status_code>;<plugin_output>

        :param host_name: the concerned host name
        :param livestate: livestate dictionary
        :return: external command line
        """
        state = livestate.get('state', 'UP').upper()
        output = livestate.get('output', '')
        long_output = livestate.get('long_output', '')
        perf_data = livestate.get('perf_data', '')
        try:
            timestamp = int(livestate.get('timestamp', 'ABC'))
        except ValueError:
            timestamp = None

        host_state_to_id = {
            "UP": 0,
            "DOWN": 1,
            "UNREACHABLE": 2
        }
        parameters = '%s;%s' % (host_state_to_id.get(state, 3), output)
        if long_output and perf_data:
            parameters = '%s|%s\n%s' % (parameters, perf_data, long_output)
        elif long_output:
            parameters = '%s\n%s' % (parameters, long_output)
        elif perf_data:
            parameters = '%s|%s' % (parameters, perf_data)

        command_line = 'PROCESS_HOST_CHECK_RESULT;%s;%s' % (host_name, parameters)
        if timestamp is not None:
            command_line = '[%d] %s' % (timestamp, command_line)
        else:
            command_line = '[%d] %s' % (int(time.time()), command_line)

        return command_line

    def _build_service_livestate(self, host_name, service_name, livestate):
        # pylint: disable=no-self-use, too-many-locals
        """Build and notify the external command for a service livestate

        PROCESS_SERVICE_CHECK_RESULT;<host_name>;<service_description>;<return_code>;<plugin_output>

        Create and post a logcheckresult to the backend for the livestate

        :param host_name: the concerned host name
        :param service_name: the concerned service name
        :param livestate: livestate dictionary
        :return: external command line
        """
        state = livestate.get('state', 'OK').upper()
        output = livestate.get('output', '')
        long_output = livestate.get('long_output', '')
        perf_data = livestate.get('perf_data', '')
        try:
            timestamp = int(livestate.get('timestamp', 'ABC'))
        except ValueError:
            timestamp = None

        service_state_to_id = {
            "OK": 0,
            "WARNING": 1,
            "CRITICAL": 2,
            "UNKNOWN": 3,
            "UNREACHABLE": 4
        }
        parameters = '%s;%s' % (service_state_to_id.get(state, 3), output)
        if long_output and perf_data:
            parameters = '%s|%s\n%s' % (parameters, perf_data, long_output)
        elif long_output:
            parameters = '%s\n%s' % (parameters, long_output)
        elif perf_data:
            parameters = '%s|%s' % (parameters, perf_data)

        command_line = 'PROCESS_SERVICE_CHECK_RESULT;%s;%s;%s' % \
                       (host_name, service_name, parameters)
        if timestamp is not None:
            command_line = '[%d] %s' % (timestamp, command_line)
        else:
            command_line = '[%d] %s' % (int(time.time()), command_line)

        return command_line

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def host(self):
        # pylint: disable=too-many-branches
        """Get a passive checks for an host and its services

        This function builds the external commands corresponding to the host and services
        provided information

        :param host_name: host name
        :param data: dictionary of the host properties to be modified
        :return: command line
        """
        logger.debug("Host status...")
        if cherrypy.request.method not in ["PATCH", "POST"]:
            cherrypy.response.status = 405
            return {'_status': 'ERR',
                    '_error': 'You must only PATCH or POST on this endpoint.'}

        # Update an host
        # ---
        if not cherrypy.request.json:
            return {'_status': 'ERR',
                    '_error': 'You must send parameters on this endpoint.'}

        host_name = None
        if cherrypy.request.json.get('name', None) is not None:
            host_name = cherrypy.request.json.get('name', None)

        if not host_name:
            return {'_status': 'ERR',
                    '_error': 'Missing targeted host name.'}

        # Get provided data
        # ---
        logger.debug("Posted data: %s", cherrypy.request.json)

        # Check if the host exist in Alignak
        # ---
        # todo: Not mandatory but it would be clean...

        # Prepare response
        # ---
        ws_result = {'_status': 'OK',
                     '_result': ['%s is alive :)' % host_name],
                     '_issues': []}

        # Manage the host livestate
        # ---
        # Alert on unordered livestate if several information exist
        now = int(time.time())
        livestate = cherrypy.request.json.get('livestate', None)
        if not livestate:
            # Create an host live state command
            livestate = {'state': "UP"}
        if not isinstance(livestate, list):
            livestate = [livestate]

        last_ts = 0
        for ls in livestate:
            if ls.get('state', None) is None:
                ws_result['_issues'].append("Missing state for the host '%s' livestate, "
                                            "assuming host is UP!" % host_name)
                ls['state'] = 'UP'

            # Tag our own timestamp
            ls['_ws_timestamp'] = now
            try:
                timestamp = int(ls.get('timestamp', 'ABC'))
                if timestamp < last_ts:
                    logger.info("Got unordered timestamp for the host '%s'. "
                                "The Alignak scheduler may not handle the check result!",
                                host_name)
                last_ts = timestamp
            except ValueError:
                pass

        for ls in livestate:
            state = ls.get('state').upper()
            if state not in ['UP', 'DOWN', 'UNREACHABLE']:
                ws_result['_issues'].append("Host state should be UP, DOWN or UNREACHABLE"
                                            ", and not '%s'." % (state))
            else:
                # Create an host live state command
                command = self._build_host_livestate(host_name, ls)
                ws_result['_result'].append("Raised: %s" % command)
                # Notify the external command to our Arbiter daemon
                self.app.add(ExternalCommand(command))

        services = cherrypy.request.json.get('services', None)
        if not services:
            return ws_result

        for service in services:
            service_name = service.get('name', None)
            if service_name is None:
                ws_result['_issues'].append("A service does not have a 'name' property")
                continue

            livestate = service.get('livestate', None)
            if not livestate:
                # Create a service live state command
                livestate = {'state': "OK"}
            if not isinstance(livestate, list):
                livestate = [livestate]

            last_ts = 0
            for ls in livestate:
                if ls.get('state', None) is None:
                    ws_result['_issues'].append("Missing state for the service %s/%s livestate, "
                                                "assuming service is OK!"
                                                % (host_name, service_name))
                    ls['state'] = 'OK'

                # Tag our own timestamp
                ls['_ws_timestamp'] = now
                try:
                    timestamp = int(ls.get('timestamp', 'ABC'))
                    if timestamp < last_ts:
                        logger.info("Got unordered timestamp for the service: %s/%s. "
                                    "The Alignak scheduler may not handle the check result!",
                                    host_name, service_name)
                    last_ts = timestamp
                except ValueError:
                    pass

            for ls in livestate:
                state = ls.get('state').upper()
                if state not in ['OK', 'WARNING', 'CRITICAL', 'UNKNOWN', 'UNREACHABLE']:
                    ws_result['_issues'].append("Service %s/%s state must be OK, WARNING, "
                                                "CRITICAL, UNKNOWN or UNREACHABLE, and not %s."
                                                % (host_name, service_name, state))
                else:
                    # Create a service live state command
                    command = self._build_service_livestate(host_name, service_name, ls)
                    ws_result['_result'].append("Raised: %s" % command)
                    # Notify the external command to our Arbiter daemon
                    self.app.add(ExternalCommand(command))

        return ws_result

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

        This overrides the default method from GenericInterface

        :return: None
        """
        with self.app.conf_lock:
            logger.warning("My master Arbiter wants me to wait for a new configuration.")
            self.app.cur_conf = {}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def _push_configuration(self, pushed_configuration=None):
        """Send a new configuration to the daemon

        This overrides the default method from GenericInterface

        Used by the master arbiter to send its configuration to a spare arbiter

        This function is not intended for external use. It is quite complex to
        build a configuration for a daemon and it is the arbter dispatcher job ;)

        :param pushed_configuration: new conf to send
        :return: None
        """
        pushed_configuration = cherrypy.request.json
        self.app.must_run = False
        return super(ArbiterInterface, self)._push_configuration(
            pushed_configuration=pushed_configuration['conf'])

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def _do_not_run(self):
        """The master arbiter tells to its spare arbiters to not run.

        A master arbiter will ignore this request and it will return an object
        containing some properties:
        '_status': 'ERR' because of the error
        `_message`: some more explanations about the error

        :return: None
        """
        # If I'm the master, ignore the command and raise a log
        if self.app.is_master:
            message = "Received message to not run. " \
                      "I am the Master arbiter, ignore and continue to run."
            logger.warning(message)
            return {'_status': u'ERR', '_message': message}

        # Else, I'm just a spare, so I listen to my master
        logger.debug("Received message to not run. I am the spare, stopping.")
        self.app.last_master_speak = time.time()
        self.app.must_run = False
        return {'_status': u'OK', '_message': message}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def _push_external_command(self, command=None):
        """Only to maintain ascending compatibility... this function uses the inner
        *command* endpoint.

        :param command: Alignak external command
        :type command: string
        :return: None
        """
        return self.command(command=command)
