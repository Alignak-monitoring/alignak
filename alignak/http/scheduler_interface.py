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
"""This module provide a specific HTTP interface for a SCheduler."""

import cherrypy
import base64
import cPickle
import zlib

from alignak.log import logger
from alignak.http.generic_interface import GenericInterface
from alignak.util import nighty_five_percent


class SchedulerInterface(GenericInterface):
    """This module provide a specific HTTP interface for a Scheduler."""

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_checks(self, do_checks=False, do_actions=False, poller_tags=['None'],
                   reactionner_tags=['None'], worker_name='none',
                   module_types=['fork']):
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
        :return: base64 zlib compress pickled check/action list
        :rtype: str
        """
        # print "We ask us checks"
        do_checks = (do_checks == 'True')
        do_actions = (do_actions == 'True')
        res = self.app.sched.get_to_run_checks(do_checks, do_actions, poller_tags, reactionner_tags,
                                               worker_name, module_types)
        # print "Sending %d checks" % len(res)
        self.app.sched.nb_checks_send += len(res)

        return base64.b64encode(zlib.compress(cPickle.dumps(res), 2))

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def put_results(self, results):
        """Put results to scheduler, used by poller and reactionners

        :param results: results to handle
        :type results:
        :return: True or ?? (if lock acquire fails)
        :rtype: bool
        """
        nb_received = len(results)
        self.app.sched.nb_check_received += nb_received
        if nb_received != 0:
            logger.debug("Received %d results", nb_received)
        for result in results:
            result.set_type_active()
        with self.app.sched.waiting_results_lock:
            self.app.sched.waiting_results.extend(results)

        # for c in results:
        # self.sched.put_results(c)
        return True

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_broks(self, bname):
        """Get checks from scheduler, used by brokers

        :param bname: broker name, used to filter broks
        :type bname: str
        :return: 64 zlib compress pickled brok list
        :rtype: str
        """
        # Maybe it was not registered as it should, if so,
        # do it for it
        if bname not in self.app.sched.brokers:
            self.fill_initial_broks(bname)

        # Now get the broks for this specific broker
        res = self.app.sched.get_broks(bname)
        # got only one global counter for broks
        self.app.sched.nb_broks_send += len(res)
        # we do not more have a full broks in queue
        self.app.sched.brokers[bname]['has_full_broks'] = False
        return base64.b64encode(zlib.compress(cPickle.dumps(res), 2))

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
            if bname not in self.app.brokers:
                logger.info("A new broker just connected : %s", bname)
                self.app.sched.brokers[bname] = {'broks': {}, 'has_full_broks': False}
            env = self.app.sched.brokers[bname]
            if not env['has_full_broks']:
                env['broks'].clear()
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

        res = sched.get_checks_status_counts()

        res = {
            'nb_scheduled': res['scheduled'],
            'nb_inpoller': res['inpoller'],
            'nb_zombies': res['zombie'],
            'nb_notifications': len(sched.actions)
        }

        # Spare schedulers do not have such properties
        if hasattr(sched, 'services'):
            # Get a overview of the latencies with just
            # a 95 percentile view, but lso min/max values
            latencies = [s.latency for s in sched.services]
            lat_avg, lat_min, lat_max = nighty_five_percent(latencies)
            res['latency'] = (0.0, 0.0, 0.0)
            if lat_avg:
                res['latency'] = (lat_avg, lat_min, lat_max)
        return res

    @cherrypy.expose
    def run_external_commands(self, cmds):
        """Post external_commands to scheduler (from arbiter)
        Wrapper to to app.sched.run_external_commands method

        :param cmds: external commands list ro run
        :type cmds: list
        :return: None
        """
        with self.app.lock:
            self.app.sched.run_external_commands(cmds)

    @cherrypy.expose
    def put_conf(self, conf):
        """Post conf to scheduler (from arbiter)

        :param conf: new configuration to load
        :type conf: dict
        :return: None
        """
        self.app.sched.die()
        super(SchedulerInterface, self).put_conf(conf)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def wait_new_conf(self):
        """Ask to scheduler to wait for new conf (HTTP GET from arbiter)

        :return: None
        """
        with self.app.conf_lock:
            logger.debug("Arbiter wants me to wait for a new configuration")
            self.app.sched.die()
            super(SchedulerInterface, self).wait_new_conf()
