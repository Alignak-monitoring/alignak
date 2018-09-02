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
"""This module provide a specific HTTP interface for a Scheduler."""

import logging
import traceback
from collections import OrderedDict, Callable

import cherrypy

from alignak.http.generic_interface import GenericInterface
from alignak.misc.serialization import serialize, unserialize

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class SchedulerInterface(GenericInterface):
    """This module provide a specific HTTP interface for a Scheduler daemon."""

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
    def object(self, o_type, o_name=None):
        """Get an object from the scheduler.

        The result is a serialized object which is a Json structure containing:
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
        o_found = self._get_object(o_type=o_type, o_name=o_name)
        if not o_found:
            return {'_status': u'ERR', '_message': u'Required %s not found.' % o_type}
        return o_found

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def dump(self, o_name=None, details=False, raw=False):
        # pylint: disable=too-many-locals, too-many-branches
        """Dump an host (all hosts) from the scheduler.

        This gets the main host information from the scheduler. If details is set, then some
        more information are provided. This will not get all the host known attributes but only
        a reduced set that will inform about the host and its services status

        If raw is set the information are provided in two string lists formated as CSV strings.
        The first list element contains the hosts information and the second one contains the
        services information.

        If an host name is provided, this function will get only this host information, else
        all the scheduler hosts are returned.

        As an example (raw format):
        [
            [   # Host information
                "type;host;name;last_check;state_id;state;state_type;is_problem;is_impact;output",
                "BR_host;host;BR_host;1532451511;0;UP;HARD;False;False;Host assumed to be UP"
            ],
            [   # Services information
                "type;host;name;last_check;state_id;state;state_type;is_problem;is_impact;output",
                "BR_host;service;dummy_critical;1532451490;2;CRITICAL;SOFT;False;False;
                BR_host-dummy_critical-2",
                "BR_host;service;BR_Simple_And;0;0;OK;HARD;False;False;",
                "BR_host;service;dummy_unreachable;1532451501;4;UNREACHABLE;SOFT;False;False;
                BR_host-dummy_unreachable-4",
                "BR_host;service;dummy_no_output;1532451495;0;OK;HARD;False;False;
                Service internal check result: 0",
                "BR_host;service;dummy_unknown;1532451475;3;UNKNOWN;SOFT;False;False;
                BR_host-dummy_unknown-3",
                "BR_host;service;dummy_echo;1532451501;0;OK;HARD;False;False;",
                "BR_host;service;dummy_warning;1532451492;1;WARNING;SOFT;False;False;
                BR_host-dummy_warning-1",
                "BR_host;service;dummy_random;1532451496;2;CRITICAL;SOFT;False;False;
                Service internal check result: 2",
                "BR_host;service;dummy_ok;1532451492;0;OK;HARD;False;False;BR_host"
            ]
        ]

        As an example (json format):
        {
            is_impact: false,
            name: "BR_host",
            state: "UP",
            last_check: 1532451811,
            state_type: "HARD",
            host: "BR_host",
            output: "Host assumed to be UP",
            services: [
                {
                    is_impact: false,
                    name: "dummy_critical",
                    state: "CRITICAL",
                    last_check: 1532451790,
                    state_type: "HARD",
                    host: "BR_host",
                    output: "BR_host-dummy_critical-2",
                    state_id: 2,
                    type: "service",
                    is_problem: true
                },
                {
                    is_impact: true,
                    name: "BR_Simple_And",
                    state: "WARNING",
                    last_check: 1532451775,
                    state_type: "SOFT",
                    host: "BR_host",
                    output: "",
                    state_id: 1,
                    type: "service",
                    is_problem: false
                },
                ....
                ....
            },
            state_id: 0,
            type: "host",
            is_problem: false
        }

        :param o_name: searched host name (or uuid)
        :type o_name: str
        :param details: less or more details
        :type details: bool
        :param raw: json or raw text format
        :type raw: bool
        :return: list of host and services information
        :rtype: list
        """

        def get_host_info(host, services, details=False, raw=False):
            # pylint: disable=too-many-branches
            """Get the host information

            :return: None
            """
            __props__ = [
                'last_check', 'state_id', 'state', 'state_type', 'is_problem', 'is_impact', 'output'
            ]
            if details:
                __props__ = __props__ + [
                    'uuid', 'address', 'alias', 'business_impact', 'tags', 'customs', 'parents',
                    'long_output', 'perf_data',
                    'check_period', 'active_checks_enabled', 'passive_checks_enabled',
                    'check_freshness', 'freshness_threshold', 'freshness_state',
                    'get_overall_state', 'overall_state_id', 'state_id', 'state', 'state_type',
                    'passive_check', 'acknowledged', 'downtimed', 'next_check',
                    'last_time_up', 'last_time_down',
                    'last_time_ok', 'last_time_warning', 'last_time_critical',
                    'last_time_unknown', 'last_time_unreachable'
                ]

            host_data = OrderedDict({'type': 'host',
                                     'host': host.get_name(),
                                     'name': host.get_name()})
            __header__ = ['type', 'host', 'name']
            for key in __props__:
                if hasattr(host, key):
                    __header__.append(key)
                    if isinstance(getattr(host, key), Callable):
                        host_data[key] = getattr(host, key)(services)
                    elif isinstance(getattr(host, key), set):
                        host_data[key] = list(getattr(host, key))
                    else:
                        host_data[key] = getattr(host, key)
            if raw:
                host_data['_header_host'] = __header__

            host_data['services'] = []
            __header__ = ['type', 'host', 'name']
            for service in host.services:
                service = services[service]
                service_data = OrderedDict({'type': 'service',
                                            'host': host.get_name(),
                                            'name': service.get_name()})
                for key in __props__:
                    if hasattr(service, key):
                        if key not in __header__:
                            __header__.append(key)
                        if isinstance(getattr(service, key), Callable):
                            service_data[key] = getattr(services, key)()
                        elif isinstance(getattr(service, key), set):
                            service_data[key] = list(getattr(service, key))
                        else:
                            service_data[key] = getattr(service, key)
                host_data['services'].append(service_data)
            if raw:
                host_data['_header_service'] = __header__

            return host_data

        if details is not False:
            details = bool(details)
        if raw is not False:
            raw = bool(raw)

        ls = []
        try:
            hosts = self._get_objects('host')
            services = self._get_objects('service')
            if o_name is None:
                for host in hosts:
                    ls.append(get_host_info(host, services, details=details, raw=raw))
            else:
                # Perhaps we got an host uuid...
                host = hosts.find_by_name(o_name)
                if o_name in hosts:
                    host = hosts[o_name]

                if host:
                    ls.append(get_host_info(host, services, details=False, raw=raw))
        except Exception as exp:  # pylint: disable=broad-except
            return str(exp) + " / " + traceback.print_exc()

        if o_name and not host:
            return {'_status': u'ERR', '_message': u'Required host (%s) not found.' % o_name}

        if raw and ls:
            raw_ls_hosts = []
            _header_host = ['type', 'host', 'name']
            raw_ls_services = []
            _header_service = ['type', 'host', 'name']

            for item in ls:
                if len(item['_header_host']) > len(_header_host):
                    _header_host = item['_header_host']
                if len(item['_header_service']) > len(_header_service):
                    _header_service = item['_header_service']
                item.pop('_header_host')
                item.pop('_header_service')

                services = []
                if 'services' in item:
                    services = item.pop('services')
                    # Write host line
                    raw_ls_hosts.append(';'.join("%s" % val for val in list(item.values())))
                    for service in services:
                        raw_ls_services.append(
                            ';'.join("%s" % val for val in list(service.values())))
            raw_ls_hosts.insert(0, ';'.join(_header_host))
            raw_ls_services.insert(0, ';'.join(_header_service))

            return [raw_ls_hosts, raw_ls_services]

        return ls

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def monitoring_problems(self):
        """Get Alignak scheduler monitoring status

        Returns an object with the scheduler livesynthesis
        and the known problems

        :return: scheduler live synthesis
        :rtype: dict
        """
        if self.app.type != 'scheduler':
            return {'_status': u'ERR',
                    '_message': u"This service is only available for a scheduler daemon"}

        res = self.identity()
        res.update(self.app.get_monitoring_problems())
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
        """Ask the scheduler to drop its configuration and wait for a new one.

        This overrides the default method from GenericInterface

        :return: None
        """
        # Stop the scheduling loop
        self.app.sched.stop_scheduling()
        super(SchedulerInterface, self)._wait_new_conf()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def _initial_broks(self, broker_name):
        """Get initial_broks from the scheduler

        This is used by the brokers to prepare the initial status broks

        This do not send broks, it only makes scheduler internal processing. Then the broker
        must use the *_broks* API to get all the stuff

        :param broker_name: broker name, used to filter broks
        :type broker_name: str
        :return: None
        """
        with self.app.conf_lock:
            logger.info("A new broker just connected : %s", broker_name)
            return self.app.sched.fill_initial_broks(broker_name)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def _broks(self, broker_name):
        """Get the broks from a scheduler, used by brokers

        This is used by the brokers to get the broks list of a scheduler

        :param broker_name: broker name, used to filter broks
        :type broker_name: str
        :return: serialized brok list
        :rtype: dict
        """
        logger.debug("Getting broks for %s from the scheduler", broker_name)
        for broker_link in list(self.app.brokers.values()):
            if broker_name == broker_link.name:
                break
        else:
            logger.warning("Requesting broks for an unknown broker: %s", broker_name)
            return {}

        # Now get the broks for this specific broker
        with self.app.broks_lock:
            res = self.app.get_broks(broker_name)

        return serialize(res, True)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def _checks(self, do_checks=False, do_actions=False, poller_tags=None,
                reactionner_tags=None, worker_name='none', module_types=None):
        """Get checks from scheduler, used by poller or reactionner when they are
        in active mode (passive = False)

        This function is not intended for external use. Let the poller and reactionner
        manage all this stuff by themselves ;)

        :param do_checks: used for poller to get checks
        :type do_checks: bool
        :param do_actions: used for reactionner to get actions
        :type do_actions: bool
        :param poller_tags: poller tags to filter on this poller
        :type poller_tags: list
        :param reactionner_tags: reactionner tags to filter on this reactionner
        :type reactionner_tags: list
        :param worker_name: Worker name asking (so that the scheduler add it to actions objects)
        :type worker_name: str
        :param module_types: Module type to filter actions/checks
        :type module_types: list
        :return: serialized check/action list
        :rtype: str
        """
        if poller_tags is None:
            poller_tags = ['None']
        if reactionner_tags is None:
            reactionner_tags = ['None']
        if module_types is None:
            module_types = ['fork']
        do_checks = (do_checks == 'True')
        do_actions = (do_actions == 'True')
        res = self.app.sched.get_to_run_checks(do_checks, do_actions, poller_tags, reactionner_tags,
                                               worker_name, module_types)

        return serialize(res, True)

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def put_results(self):
        """Put results to scheduler, used by poller or reactionner when they are
        in active mode (passive = False)

        This function is not intended for external use. Let the poller and reactionner
        manage all this stuff by themselves ;)

        :param from: poller/reactionner identification
        :type from: str
        :param results: list of actions results
        :type results: list
        :return: True
        :rtype: bool
        """
        res = cherrypy.request.json
        who_sent = res['from']
        results = res['results']

        results = unserialize(results, no_load=True)
        if results:
            logger.debug("Got some results: %d results from %s", len(results), who_sent)
        else:
            logger.debug("-> no results")

        for result in results:
            logger.debug("-> result: %s", result)

            # Append to the scheduler result queue
            self.app.sched.waiting_results.put(result)

        return True

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def _run_external_commands(self):
        """Post external_commands to scheduler (from arbiter)
        Wrapper to to app.sched.run_external_commands method

        :return: None
        """
        commands = cherrypy.request.json
        with self.app.lock:
            self.app.sched.run_external_commands(commands['cmds'])

    def _get_objects(self, o_type):
        """Get an object list from the scheduler

        Returns None if the required object type (`o_type`) is not known or an exception is raised.
        Else returns the objects list

        :param o_type: searched object type
        :type o_type: str
        :return: objects list
        :rtype: alignak.objects.item.Items
        """
        if o_type not in [t for t in self.app.sched.pushed_conf.types_creations]:
            return None

        try:
            _, _, strclss, _, _ = self.app.sched.pushed_conf.types_creations[o_type]
            o_list = getattr(self.app.sched, strclss)
        except Exception:  # pylint: disable=broad-except
            return None

        return o_list

    def _get_object(self, o_type, o_name=None):
        """Get an object from the scheduler

        Returns None if the required object type (`o_type`) is not known.
        Else returns the serialized object if found. The object is searched first with
        o_name as its name and then with o_name as its uuid.

        :param o_type: searched object type
        :type o_type: str
        :param name: searched object name
        :type name: str
        :return: serialized object
        :rtype: str
        """
        try:
            o_found = None
            o_list = self._get_objects(o_type)
            if o_list:
                if o_name is None:
                    return serialize(o_list, True) if o_list else None
                # We expected a name...
                o_found = o_list.find_by_name(o_name)
                if not o_found:
                    # ... but perharps we got an object uuid
                    o_found = o_list[o_name]
        except Exception:  # pylint: disable=broad-except
            return None
        return serialize(o_found, True) if o_found else None
