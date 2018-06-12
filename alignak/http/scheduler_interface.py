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
import cherrypy

from alignak.http.generic_interface import GenericInterface
from alignak.misc.serialization import serialize, unserialize

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class SchedulerInterface(GenericInterface):
    """This module provide a specific HTTP interface for a Scheduler."""

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_checks(self, do_checks=False, do_actions=False, poller_tags=None,
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
        # Count actions got by the poller/reactionner
        if do_checks:
            self.app.nb_pulled_checks += len(res)
        if do_actions:
            self.app.nb_pulled_actions += len(res)

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
        self.app.sched.nb_checks_results += len(results)

        for result in results:
            logger.debug("-> result: %s", result)

            # Update scheduler counters
            self.app.sched.counters[result.is_a]["total"]["results"]["total"] += 1
            if result.status not in \
                    self.app.sched.counters[result.is_a]["total"]["results"]:
                self.app.sched.counters[result.is_a]["total"]["results"][result.status] = 0
            self.app.sched.counters[result.is_a]["total"]["results"][result.status] += 1
            self.app.sched.counters[result.is_a]["active"]["results"]["total"] += 1
            if result.status not in \
                    self.app.sched.counters[result.is_a]["active"]["results"]:
                self.app.sched.counters[result.is_a]["active"]["results"][result.status] = 0
            self.app.sched.counters[result.is_a]["active"]["results"][result.status] += 1

            # Append to the scheduler result queue
            self.app.sched.waiting_results.put(result)

        return True

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_broks(self, broker_name):
        """Get the broks from a scheduler, used by brokers

        This is used by the brokers to get the broks list of a scheduler

        :param broker_name: broker name, used to filter broks
        :type broker_name: str
        :return: serialized brok list
        :rtype: dict
        """
        logger.debug("Getting broks for %s from the scheduler", broker_name)
        for broker_link in self.app.brokers.values():
            if broker_name in [broker_link.name]:
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
    def fill_initial_broks(self, broker_name):
        """Get initial_broks from the scheduler

        This is used by the brokers to prepare the initial status broks

        This do not send broks, it only makes scheduler internal processing. Then the broker
        must use the *get_broks* API to get all the stuff

        :param broker_name: broker name, used to filter broks
        :type broker_name: str
        :return: None
        """
        with self.app.conf_lock:
            logger.info("A new broker just connected : %s", broker_name)
            return self.app.sched.fill_initial_broks(broker_name, with_logs=True)

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def run_external_commands(self):
        """Post external_commands to scheduler (from arbiter)
        Wrapper to to app.sched.run_external_commands method

        :return: None
        """
        commands = cherrypy.request.json
        with self.app.lock:
            self.app.sched.run_external_commands(commands['cmds'])

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def wait_new_conf(self):
        """Ask the scheduler to drop its configuration and wait for a new one

        :return: None
        """
        # Stop the scheduling loop
        self.app.sched.stop_scheduling()
        super(SchedulerInterface, self).wait_new_conf()

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

    def _get_object(self, o_type, name='None'):
        """Get an object from the scheduler

        Returns None if the required object type (`o_type`) is not known.
        Else returns the serialized object if found

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
                o_found = o_list.find_by_name(name)
                if not o_found:
                    o_found = o_list[name]
        except Exception:  # pylint: disable=broad-except
            return None
        return serialize(o_found, True) if o_found else None

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_host(self, host_name='None'):
        """Get host configuration from the scheduler, used mainly by the receiver

        :param host_name: searched host name
        :type host_name: str
        :return: serialized host information
        :rtype: str
        """
        return self._get_object('host', name=host_name)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_hostgroup(self, hostgroup_name='None'):
        """Get hostgroup configuration from the scheduler, used mainly by the receiver

        :param hostgroup_name: searched host name
        :type hostgroup_name: str
        :return: serialized hostgroup information
        :rtype: str
        """
        return self._get_object('hostgroup', name=hostgroup_name)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_realm(self, realm_name='None'):
        """Get realm configuration from the scheduler, used mainly by the receiver

        :param realm_name: searched host name
        :type realm_name: str
        :return: serialized host information
        :rtype: str
        """
        return self._get_object('realm', name=realm_name)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_monitoring_problems(self):
        """Get Alignak scheduler monitoring status

        Returns an object with the scheduler livesynthesis
        and the known problems

        :return: scheduler live synthesis
        :rtype: dict
        """
        if self.app.type != 'scheduler':
            return {'_status': u'ERR',
                    '_message': u"This service is only available for a scheduler daemon"}

        res = self.get_id()
        res.update(self.get_start_time())
        res.update(self.app.get_monitoring_problems())
        return res
