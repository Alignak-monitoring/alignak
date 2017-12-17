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
"""This module provide a specific HTTP interface for a Scheduler."""

import logging
import cherrypy

from alignak.http.generic_interface import GenericInterface
from alignak.util import average_percentile
from alignak.misc.serialization import serialize, unserialize

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class SchedulerInterface(GenericInterface):
    """This module provide a specific HTTP interface for a Scheduler."""

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_checks(self, do_checks=False, do_actions=False, poller_tags=None,
                   reactionner_tags=None, worker_name='none',
                   module_types=None):
        """Get checks from scheduler, used by poller or reactionner (active ones)

        :param do_checks: used for poller to get checks
        :type do_checks: bool
        :param do_actions: used for reactionner to get actions
        :type do_actions: bool
        :param poller_tags: pollers tags to filter on this poller
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
        # self.app.sched.nb_checks_send += len(res)

        return serialize(res, True)

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def put_results(self):
        """Put results to scheduler, used by poller and reactionners

        :return: True or ?? (if lock acquire fails)
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
            # resultobj = unserialize(result, True)
            result.set_type_active()

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
    def get_broks(self, bname):
        """Get broks from scheduler, used by brokers

        :param bname: broker name, used to filter broks
        :type bname: str
        :return: serialized brok list
        :rtype: dict
        """
        # Maybe it was not registered as it should, if so,
        # do it for it
        if bname not in self.app.sched.brokers:
            self.fill_initial_broks(bname)
        elif not self.app.sched.brokers[bname]['initialized']:
            self.fill_initial_broks(bname)

        if bname not in self.app.sched.brokers:
            return {}

        # Now get the broks for this specific broker
        res = self.app.sched.get_broks(bname)

        # we do not more have a full broks in queue
        self.app.sched.brokers[bname]['has_full_broks'] = False
        return serialize(res, True)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def fill_initial_broks(self, bname):
        """Get initial_broks type broks from scheduler, used by brokers
        Do not send broks, only make scheduler internal processing

        :param bname: broker name, used to filter broks
        :type bname: str
        :return: None
        TODO: Maybe we should check_last time we did it to prevent DDoS
        """
        with self.app.conf_lock:
            if bname not in self.app.sched.brokers:
                return
            env = self.app.sched.brokers[bname]
            if not env['has_full_broks']:
                logger.info("A new broker just connected : %s", bname)
                # env['broks'].clear()
                self.app.sched.fill_initial_broks(bname, with_logs=True)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_raw_stats(self):
        """Get raw stats from the daemon::

        * nb_scheduled: number of scheduled checks (to launch in the future)
        * nb_inpoller: number of check take by the pollers
        * nb_zombies: number of zombie checks (should be close to zero)
        * nb_notifications: number of notifications+event handlers
        * latency: avg,min,max latency for the services (should be <10s)

        :return: stats for scheduler
        :rtype: dict
        """
        sched = self.app.sched

        res = {'counters': sched.counters}

        # Spare schedulers do not have such properties
        if hasattr(sched, 'services'):
            # Get a overview of the latencies with:
            #  * average
            #  * maximum (95 percentile)
            #  * minimum (5 percentile)
            latencies = [s.latency for s in sched.services]
            latencies.extend([s.latency for s in sched.hosts])
            lat_avg, lat_min, lat_max = average_percentile(latencies)
            res['latency_average'] = 0.0
            res['latency_minimum'] = 0.0
            res['latency_maximum'] = 0.0
            if lat_avg:
                res['latency_average'] = lat_avg
                res['latency_minimum'] = lat_min
                res['latency_maximum'] = lat_max
        return res

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
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def put_conf(self, conf=None):
        """Post conf to scheduler (from arbiter)

        :return: None
        """
        # Stop the current scheduling loop
        self.app.sched.stop_scheduling()
        conf = cherrypy.request.json
        super(SchedulerInterface, self).put_conf(conf['conf'])

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def wait_new_conf(self):
        """Ask to scheduler to wait for new conf (HTTP GET from arbiter)

        :return: None
        """
        with self.app.conf_lock:
            logger.warning("My Arbiter wants me to wait for a new configuration.")
            self.app.sched.stop_scheduling()
            super(SchedulerInterface, self).wait_new_conf()
