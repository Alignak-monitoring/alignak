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
#
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     xkilian, fmikus@acktomic.com
#     David Moreau Simard, dmsimard@iweb.com
#     Guillaume Bour, guillaume@bour.cc
#     aviau, alexandre.viau@savoirfairelinux.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Bruno Clermont, bruno.clermont@gmail.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Gerhard Lausser, gerhard.lausser@consol.de

#  This file is part of Shinken.
#
#  Shinken is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Shinken is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Shinken.  If not, see <http://www.gnu.org/licenses/>.

"""
This class is an interface for Reactionner and Poller daemons
A Reactionner listens to a port for the configuration from the Arbiter
The conf contains the schedulers where actionners will gather actions.

The Reactionner keeps on listening to the Arbiter

If Arbiter wants it to have a new conf, the satellite forgets the previous
 Schedulers (and actions into) and takes the new ones.
"""

import os
import copy
import logging
import time
import traceback
import threading

from queue import Empty, Full
from multiprocessing import Queue, active_children
import psutil

from alignak.http.generic_interface import GenericInterface

from alignak.misc.serialization import unserialize, AlignakClassLookupException
from alignak.property import BoolProp, IntegerProp, ListProp
from alignak.brok import Brok
from alignak.external_command import ExternalCommand

from alignak.action import ACT_STATUS_QUEUED
from alignak.message import Message
from alignak.worker import Worker
from alignak.daemon import Daemon
from alignak.stats import statsmgr
from alignak.check import Check  # pylint: disable=W0611
from alignak.objects.module import Module  # pylint: disable=W0611
from alignak.objects.satellitelink import SatelliteLink, LinkError

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class NotWorkerMod(Exception):
    """Class to tell that we are facing a non worker module
    but a standard one

    """
    pass


class BaseSatellite(Daemon):
    """Base Satellite class.
    Sub-classed by Alignak (scheduler), Broker and Satellite

    """
    properties = Daemon.properties.copy()

    def __init__(self, name, **kwargs):
        super(BaseSatellite, self).__init__(name, **kwargs)

        # Our schedulers and arbiters
        self.schedulers = {}
        self.arbiters = {}

        # Hosts / schedulers mapping
        self.hosts_schedulers = {}

        # Keep monitoring events so they can be eaten by the arbiter
        self.events = []
        self.events_lock = threading.RLock()

        # Now we create the interfaces
        self.http_interface = GenericInterface(self)

        # Can have a queue of external_commands given by modules
        # will be taken by arbiter to process
        self.external_commands = []
        self.external_commands_lock = threading.RLock()

    def get_managed_configurations(self):
        """Get the configurations managed by this satellite

        The configurations managed by a satellite is a list of the configuration attached to
        the schedulers related to the satellites. A broker linked to several schedulers
        will return the list of the configuration parts of its scheduler links.

        :return: a dict of scheduler links with instance_id as key and
        hash, push_flavor and configuration identifier as values
        :rtype: dict
        """
        res = {}
        for scheduler_link in list(self.schedulers.values()):
            res[scheduler_link.instance_id] = {
                'hash': scheduler_link.hash,
                'push_flavor': scheduler_link.push_flavor,
                'managed_conf_id': scheduler_link.managed_conf_id
            }
        logger.debug("Get managed configuration: %s", res)
        return res

    def get_scheduler_from_hostname(self, host_name):
        """Get scheduler linked to the given host_name

        :param host_name: host_name we want the scheduler from
        :type host_name: str
        :return: scheduler with id corresponding to the mapping table
        :rtype: dict
        """
        scheduler_uuid = self.hosts_schedulers.get(host_name, None)
        return self.schedulers.get(scheduler_uuid, None)

    def get_external_commands(self):
        """Get the external commands

        :return: External commands list
        :rtype: list
        """
        res = self.external_commands
        logger.debug("Get and clear external commands list: %s", res)
        self.external_commands = []
        return res

    def get_results_from_passive(self, scheduler_instance_id):
        """Get executed actions results from a passive satellite for a specific scheduler

        :param scheduler_instance_id: scheduler id
        :type scheduler_instance_id: int
        :return: Results list
        :rtype: list
        """
        # Do I know this scheduler?
        # logger.info("My schedulers: %s %s", self.schedulers, type(self.schedulers))
        if not self.schedulers:
            # Probably not yet configured ...
            logger.debug("I do not have any scheduler: %s", self.schedulers)
            return []

        scheduler_link = None
        for link in list(self.schedulers.values()):
            if scheduler_instance_id == link.instance_id:
                scheduler_link = link
                break
        else:
            logger.warning("I do not know this scheduler: %s", scheduler_instance_id)
            return []

        logger.debug("Get results for the scheduler: %s", scheduler_instance_id)
        ret, scheduler_link.wait_homerun = scheduler_link.wait_homerun, {}
        logger.debug("Results: %s" % (list(ret.values())) if ret else "No results available")

        return list(ret.values())

    def clean_previous_run(self):
        """Clean variables from previous configuration,
        such as schedulers, broks and external commands

        :return: None
        """
        # Clean all lists
        self.arbiters.clear()
        self.schedulers.clear()
        with self.external_commands_lock:
            self.external_commands = self.external_commands[:]

    def do_loop_turn(self):
        """Satellite main loop - not implemented for a BaseSatellite"""
        raise NotImplementedError()

    def setup_new_conf(self):
        # pylint: disable=too-many-locals, too-many-branches
        """Setup the new configuration received from Arbiter

        This function is the generic treatment needed for every Alignak daemon when it receivss
        a new configuration from the Arbiter:
        - save the new configuration
        - dump the main configuration elements
        - get its own configuration (self_conf)
        - get its name and update the process title
        - set the timezone if needed
        - register its statistics manager
        - get and configure its arbiters and schedulers relation

        Setting the self.new_conf as None is to indicate that the new configuration has been
        managed.

        Note: it is important to protect the configuration management thanks to a lock!

        :return: None
        """
        with self.conf_lock:
            # No more configuration now!
            self.have_conf = False

            logger.info("Received a new configuration (arbiters / schedulers)")

            # Clean our execution context
            self.clean_previous_run()

            # Check configuration is valid
            if '_status' in self.new_conf:
                logger.error(self.new_conf['_status'])
                self.cur_conf = {}

            # Get the new configuration
            self.cur_conf = self.new_conf
            # self_conf is our own configuration from the alignak environment
            self_conf = self.cur_conf['self_conf']

            logger.debug("Received a new configuration, containing:")
            for key in self.cur_conf:
                try:
                    logger.debug("- %s: %s", key, self.cur_conf[key])
                except UnicodeDecodeError:
                    logger.error("- %s: %s", key, self.cur_conf[key].decode('utf8', 'ignore'))
            logger.debug("satellite self configuration part: %s", self_conf)

            if 'satellites' not in self.cur_conf:
                self.cur_conf['satellites'] = []
            if 'modules' not in self.cur_conf:
                self.cur_conf['modules'] = []

            # Update Alignak name
            self.alignak_name = self.cur_conf['alignak_name']
            logger.info("My Alignak instance: %s", self.alignak_name)

            # This to indicate that the new configuration got managed...
            self.new_conf = {}

            # Set our timezone from arbiter
            use_timezone = self_conf.get('use_timezone', 'NOTSET')
            if use_timezone != 'NOTSET':
                logger.info("Setting our timezone to %s", use_timezone)
                os.environ['TZ'] = use_timezone
                time.tzset()

            # Now we create our arbiters and schedulers links
            for link_type in ['arbiters', 'schedulers']:
                if link_type not in self.cur_conf:
                    logger.error("Missing %s in the configuration!", link_type)
                    continue

                if link_type == 'schedulers' and self.type == 'scheduler':
                    # Do not do anything with my own link!
                    continue

                my_satellites = getattr(self, link_type, {})
                received_satellites = self.cur_conf[link_type]
                for link_uuid in received_satellites:
                    rs_conf = received_satellites[link_uuid]
                    logger.debug("- received %s - %s: %s", rs_conf['instance_id'],
                                 rs_conf['type'], rs_conf['name'])

                    # Must look if we already had a configuration and save our broks
                    already_got = rs_conf['instance_id'] in my_satellites
                    broks = []
                    actions = {}
                    wait_homerun = {}
                    external_commands = {}
                    running_id = 0
                    if already_got:
                        logger.warning("I already got: %s", rs_conf['instance_id'])
                        # Save some information
                        running_id = my_satellites[link_uuid].running_id
                        (broks, actions,
                         wait_homerun, external_commands) = \
                            my_satellites[link_uuid].get_and_clear_context()
                        # Delete the former link
                        del my_satellites[link_uuid]

                    # My new satellite link...
                    new_link = SatelliteLink.get_a_satellite_link(link_type[:-1],
                                                                  rs_conf)
                    my_satellites[new_link.uuid] = new_link
                    logger.info("I got a new %s satellite: %s", link_type[:-1], new_link)

                    new_link.running_id = running_id
                    new_link.external_commands = external_commands
                    new_link.broks = broks
                    new_link.wait_homerun = wait_homerun
                    new_link.actions = actions

                    # replacing satellite address and port by those defined in satellite_map
                    if new_link.name in self_conf.get('satellite_map', {}):
                        overriding = self_conf.get('satellite_map')[new_link.name]
                        # satellite = dict(satellite)  # make a copy
                        # new_link.update(self_conf.get('satellite_map', {})[new_link.name])
                        logger.warning("Do not override the configuration for: %s, with: %s. "
                                       "Please check whether this is necessary!",
                                       new_link.name, overriding)

            # For each scheduler, we received its managed hosts list
            self.hosts_schedulers = {}
            logger.debug("My arbiters: %s", self.arbiters)
            logger.debug("My schedulers: %s", self.schedulers)
            for link_uuid in self.schedulers:
                # We received the hosts names for each scheduler
                for host_name in self.schedulers[link_uuid].managed_hosts_names:
                    self.hosts_schedulers[host_name] = link_uuid

    def get_events(self):
        """Get event list from satellite

        :return: A copy of the events list
        :rtype: list
        """
        res = copy.copy(self.events)
        del self.events[:]
        return res

    def get_daemon_stats(self, details=False):
        """Increase the stats provided by the Daemon base class

        :return: stats dictionary
        :rtype: dict
        """
        # call the daemon one
        res = super(BaseSatellite, self).get_daemon_stats(details=details)

        counters = res['counters']
        counters['external-commands'] = len(self.external_commands)
        counters['satellites.arbiters'] = len(self.arbiters)
        counters['satellites.schedulers'] = len(self.schedulers)

        return res


class Satellite(BaseSatellite):  # pylint: disable=R0902
    """Satellite class.
    Sub-classed by Receiver, Reactionner and Poller

    """
    do_checks = False
    do_actions = False
    my_type = ''

    properties = BaseSatellite.properties.copy()
    properties.update({
        'passive':
            BoolProp(default=False),
        'max_plugins_output_length':
            IntegerProp(default=8192),
        'min_workers':
            IntegerProp(default=0, fill_brok=['full_status'], to_send=True),
        'max_workers':
            IntegerProp(default=0, fill_brok=['full_status'], to_send=True),
        'processes_by_worker':
            IntegerProp(default=256, fill_brok=['full_status'], to_send=True),
        'worker_polling_interval':
            IntegerProp(default=1, to_send=True),
        'poller_tags':
            ListProp(default=['None'], to_send=True),
        'reactionner_tags':
            ListProp(default=['None'], to_send=True),
    })

    def __init__(self, name, **kwargs):
        super(Satellite, self).__init__(name, **kwargs)

        # Move these properties to the base Daemon ?
        # todo: change this?
        # Keep broks so they can be eaten by a broker
        self.broks = []
        self.broks_lock = threading.RLock()

        # My active workers
        self.workers = {}

        # May be we are a passive daemon
        if self.passive:
            self.pre_log.append(("INFO", "Passive mode enabled."))

        # Our tags
        # ['None'] is the default tags
        if self.type in ['poller'] and self.poller_tags:
            self.pre_log.append(("INFO", "Poller tags: %s" % self.poller_tags))
        if self.type in ['reactionner'] and self.reactionner_tags:
            self.pre_log.append(("INFO", "Reactionner tags: %s" % self.reactionner_tags))

        # Now the limit part, 0 means the number of cpu of this machine :)
        cpu_count = psutil.cpu_count()
        # Do not use the logger in this function because it is not yet initialized...
        self.pre_log.append(("INFO",
                             "Detected %d CPUs" % cpu_count))
        if self.max_workers == 0:
            try:
                # Preserve one CPU if more than one detected
                self.max_workers = max(cpu_count - 1, 1)
            except NotImplementedError:  # pragma: no cover, simple protection
                self.max_workers = 1
        if self.min_workers == 0:
            try:
                self.min_workers = max(cpu_count - 1, 1)
            except NotImplementedError:  # pragma: no cover, simple protection
                self.min_workers = 1
        self.pre_log.append(("INFO",
                             "Using minimum %d workers, maximum %d workers, %d processes/worker"
                             % (self.min_workers, self.max_workers, self.processes_by_worker)))

        self.slave_q = None

        self.returns_queue = None
        self.q_by_mod = {}

        # Modules are only loaded one time
        self.have_modules = False

        # round robin queue ic
        self.rr_qid = 0

    def manage_action_return(self, action):
        """Manage action return from Workers
        We just put them into the corresponding sched
        and we clean unused properties like my_scheduler

        :param action: the action to manage
        :type action: alignak.action.Action
        :return: None
        """
        # Maybe our workers send us something else than an action
        # if so, just add this in other queues and return
        # todo: test a class instance
        if action.__class__.my_type not in ['check', 'notification', 'eventhandler']:
            self.add(action)
            return

        # Ok, it's a result. Get the concerned scheduler uuid
        scheduler_uuid = action.my_scheduler
        logger.debug("Got action return: %s / %s", scheduler_uuid, action.uuid)

        try:
            # Now that we know where to put the action result, we do not need any reference to
            # the scheduler nor the worker
            del action.my_scheduler
            del action.my_worker
        except AttributeError:  # pragma: no cover, simple protection
            logger.error("AttributeError Got action return: %s / %s", scheduler_uuid, action)

        # And we remove it from the actions queue of the scheduler too
        try:
            del self.schedulers[scheduler_uuid].actions[action.uuid]
        except KeyError as exp:
            logger.error("KeyError del scheduler action: %s / %s - %s",
                         scheduler_uuid, action.uuid, str(exp))

        # We tag it as "return wanted", and move it in the wait return queue
        try:
            self.schedulers[scheduler_uuid].wait_homerun[action.uuid] = action
        except KeyError:  # pragma: no cover, simple protection
            logger.error("KeyError Add home run action: %s / %s - %s",
                         scheduler_uuid, action.uuid, str(exp))

    def push_results(self):
        """Push the checks/actions results to our schedulers

        :return: None
        """
        # For all schedulers, we check for wait_homerun
        # and we send back results
        for scheduler_link_uuid in self.schedulers:
            scheduler_link = self.schedulers[scheduler_link_uuid]
            if not scheduler_link.active:
                logger.warning("My scheduler '%s' is not active currently", scheduler_link.name)
                continue

            if not scheduler_link.wait_homerun:
                # Nothing to push back...
                continue

            # NB: it's **mostly** safe for us to not use some lock around
            # this 'results' / sched['wait_homerun'].
            # Because it can only be modified (for adding new values) by the
            # same thread running this function (that is the main satellite
            # thread), and this occurs exactly in self.manage_action_return().
            # Another possibility is for the sched['wait_homerun'] to be
            # cleared within/by :
            # ISchedulers.get_results() -> Satelitte.get_return_for_passive()
            # This can so happen in an (http) client thread.
            results = scheduler_link.wait_homerun
            logger.debug("Pushing %d results to '%s'", len(results), scheduler_link.name)

            # So, at worst, some results would be received twice on the
            # scheduler level, which shouldn't be a problem given they are
            # indexed by their "action_id".

            scheduler_link.push_results(list(results.values()), self.name)
            results.clear()

    def create_and_launch_worker(self, module_name='fork'):
        """Create and launch a new worker, and put it into self.workers
         It can be mortal or not

        :param module_name: the module name related to the worker
                            default is "fork" for no module
                            Indeed, it is actually the module 'python_name'
        :type module_name: str
        :return: None
        """
        logger.info("Allocating new '%s' worker...", module_name)

        # If we are in the fork module, we do not specify a target
        target = None
        __warned = []
        if module_name == 'fork':
            target = None
        else:
            for module in self.modules_manager.instances:
                # First, see if the module name matches...
                if module.get_name() == module_name:
                    # ... and then if is a 'worker' module one or not
                    if not module.properties.get('worker_capable', False):
                        raise NotWorkerMod
                    target = module.work
            if target is None:
                if module_name not in __warned:
                    logger.warning("No target found for %s, NOT creating a worker for it...",
                                   module_name)
                    __warned.append(module_name)
                return
        # We give to the Worker the instance name of the daemon (eg. poller-master)
        # and not the daemon type (poller)
        queue = Queue()
        worker = Worker(module_name, queue, self.returns_queue, self.processes_by_worker,
                        max_plugins_output_length=self.max_plugins_output_length,
                        target=target, loaded_into=self.name)
        # worker.module_name = module_name
        # save this worker
        self.workers[worker.get_id()] = worker

        # And save the Queue of this worker, with key = worker id
        # self.q_by_mod[module_name][worker.uuid] = queue
        self.q_by_mod[module_name][worker.get_id()] = queue

        # Ok, all is good. Start it!
        worker.start()

        logger.info("Started '%s' worker: %s (pid=%d)",
                    module_name, worker.get_id(), worker.get_pid())

    def do_stop_workers(self):
        """Stop all workers

        :return: None
        """
        logger.info("Stopping all workers (%d)", len(self.workers))
        for worker in list(self.workers.values()):
            try:
                logger.info(" - stopping '%s'", worker.get_id())
                worker.terminate()
                worker.join(timeout=1)
                logger.info("stopped")
            # A already dead worker or in a worker
            except (AttributeError, AssertionError):
                pass
            except Exception as exp:  # pylint: disable=broad-except
                logger.error("exception: %s", str(exp))

    def do_stop(self):
        """Stop my workers and stop

        :return: None
        """
        self.do_stop_workers()

        super(Satellite, self).do_stop()

    def add(self, elt):
        """Generic function to add objects to the daemon internal lists.
        Manage Broks, External commands

        :param elt: object to add
        :type elt: alignak.AlignakObject
        :return: None
        """
        if isinstance(elt, Brok):
            # For brok, we tag the brok with our instance_id
            elt.instance_id = self.instance_id
            if elt.type == 'monitoring_log':
                # The brok is a monitoring event
                with self.events_lock:
                    self.events.append(elt)
                statsmgr.counter('events', 1)
            else:
                with self.broks_lock:
                    self.broks.append(elt)
            statsmgr.counter('broks.added', 1)
        elif isinstance(elt, ExternalCommand):
            logger.debug("Queuing an external command '%s'", str(elt.__dict__))
            with self.external_commands_lock:
                self.external_commands.append(elt)
            statsmgr.counter('external-commands.added', 1)

    def get_broks(self):
        """Get brok list from satellite

        :return: A copy of the broks list
        :rtype: list
        """
        res = copy.copy(self.broks)
        del self.broks[:]
        return res

    def check_and_del_zombie_workers(self):  # pragma: no cover, not with unit tests...
        # pylint: disable= not-callable
        """Check if worker are fine and kill them if not.
        Dispatch the actions in the worker to another one

        TODO: see if unit tests would allow to check this code?

        :return: None
        """
        # Active children make a join with everyone, useful :)
        # active_children()
        for p in active_children():
            logger.debug("got child: %s", p)

        w_to_del = []
        for worker in list(self.workers.values()):
            # If a worker goes down and we did not ask him, it's not
            # good: we can think that we have a worker and it's not True
            # So we del it
            logger.debug("checking if worker %s (pid=%d) is alive",
                         worker.get_id(), worker.get_pid())
            if not self.interrupted and not worker.is_alive():
                logger.warning("The worker %s (pid=%d) went down unexpectedly!",
                               worker.get_id(), worker.get_pid())
                # Terminate immediately
                worker.terminate()
                worker.join(timeout=1)
                w_to_del.append(worker.get_id())

        # OK, now really del workers from queues
        # And requeue the actions it was managed
        for worker_id in w_to_del:
            worker = self.workers[worker_id]

            # Del the queue of the module queue
            del self.q_by_mod[worker.module_name][worker.get_id()]

            for scheduler_uuid in self.schedulers:
                sched = self.schedulers[scheduler_uuid]
                for act in list(sched.actions.values()):
                    if act.status == ACT_STATUS_QUEUED and act.my_worker == worker_id:
                        # Got a check that will NEVER return if we do not restart it
                        self.assign_to_a_queue(act)

            # So now we can really forgot it
            del self.workers[worker_id]

    def adjust_worker_number_by_load(self):
        """Try to create the minimum workers specified in the configuration

        :return: None
        """
        if self.interrupted:
            logger.debug("Trying to adjust worker number. Ignoring because we are stopping.")
            return

        to_del = []
        logger.debug("checking worker count."
                     " Currently: %d workers, min per module : %d, max per module : %d",
                     len(self.workers), self.min_workers, self.max_workers)

        # I want at least min_workers by module then if I can, I add worker for load balancing
        for mod in self.q_by_mod:
            # At least min_workers
            todo = max(0, self.min_workers - len(self.q_by_mod[mod]))
            for _ in range(todo):
                try:
                    self.create_and_launch_worker(module_name=mod)
                # Maybe this modules is not a true worker one.
                # if so, just delete if from q_by_mod
                except NotWorkerMod:
                    to_del.append(mod)
                    break

        for mod in to_del:
            logger.warning("The module %s is not a worker one, I remove it from the worker list.",
                           mod)
            del self.q_by_mod[mod]
        # TODO: if len(workers) > 2*wish, maybe we can kill a worker?

    def _get_queue_for_the_action(self, action):
        """Find action queue for the action depending on the module.
        The id is found with action modulo on action id

        :param a: the action that need action queue to be assigned
        :type action: object
        :return: worker id and queue. (0, None) if no queue for the module_type
        :rtype: tuple
        """
        # get the module name, if not, take fork
        mod = getattr(action, 'module_type', 'fork')
        queues = list(self.q_by_mod[mod].items())

        # Maybe there is no more queue, it's very bad!
        if not queues:
            return (0, None)

        # if not get action round robin index to get action queue based
        # on the action id
        self.rr_qid = (self.rr_qid + 1) % len(queues)
        (worker_id, queue) = queues[self.rr_qid]

        # return the id of the worker (i), and its queue
        return (worker_id, queue)

    def add_actions(self, actions_list, scheduler_instance_id):
        """Add a list of actions to the satellite queues

        :param actions_list: Actions list to add
        :type actions_list: list
        :param scheduler_instance_id: sheduler link to assign the actions to
        :type scheduler_instance_id: SchedulerLink
        :return: None
        """
        # We check for new check in each schedulers and put the result in new_checks
        scheduler_link = None
        for scheduler_id in self.schedulers:
            logger.debug("Trying to add an action, scheduler: %s", self.schedulers[scheduler_id])
            if scheduler_instance_id == self.schedulers[scheduler_id].instance_id:
                scheduler_link = self.schedulers[scheduler_id]
                break
        else:
            logger.error("Trying to add actions from an unknwown scheduler: %s",
                         scheduler_instance_id)
            return
        if not scheduler_link:
            logger.error("Trying to add actions, but scheduler link is not found for: %s, "
                         "actions: %s", scheduler_instance_id, actions_list)
            return
        logger.debug("Found scheduler link: %s", scheduler_link)

        for action in actions_list:
            # First we look if the action is identified
            uuid = getattr(action, 'uuid', None)
            if uuid is None:
                try:
                    action = unserialize(action, no_load=True)
                    uuid = action.uuid
                except AlignakClassLookupException:
                    logger.error('Cannot un-serialize action: %s', action)
                    continue

            # If we already have this action, we are already working for it!
            if uuid in scheduler_link.actions:
                continue
            # Action is attached to a scheduler
            action.my_scheduler = scheduler_link.uuid
            scheduler_link.actions[action.uuid] = action
            self.assign_to_a_queue(action)

    def assign_to_a_queue(self, action):
        """Take an action and put it to a worker actions queue

        :param action: action to put
        :type action: alignak.action.Action
        :return: None
        """
        (worker_id, queue) = self._get_queue_for_the_action(action)
        if not worker_id:
            return

        # Tag the action as "in the worker i"
        action.my_worker = worker_id
        action.status = ACT_STATUS_QUEUED

        msg = Message(_type='Do', data=action, source=self.name)
        logger.debug("Queuing message: %s", msg)
        queue.put_nowait(msg)
        logger.debug("Queued")

    def get_new_actions(self):
        """ Wrapper function for do_get_new_actions
        For stats purpose

        :return: None
        TODO: Use a decorator for timing this function
        """
        try:
            _t0 = time.time()
            self.do_get_new_actions()
            statsmgr.timer('actions.got.time', time.time() - _t0)
        except RuntimeError:
            logger.error("Exception like issue #1007")

    def do_get_new_actions(self):
        """Get new actions from schedulers
        Create a Message and put into the module queue
        REF: doc/alignak-action-queues.png (1)

        :return: None
        """
        # Here are the differences between a poller and a reactionner:
        # Poller will only do checks,
        # Reactionner will do actions (notifications and event handlers)
        do_checks = self.__class__.do_checks
        do_actions = self.__class__.do_actions

        # We check and get the new actions to execute in each of our schedulers
        for scheduler_link_uuid in self.schedulers:
            scheduler_link = self.schedulers[scheduler_link_uuid]

            if not scheduler_link.active:
                logger.warning("My scheduler '%s' is not active currently", scheduler_link.name)
                continue

            logger.debug("get new actions, scheduler: %s", scheduler_link.name)

            # OK, go for it :)
            _t0 = time.time()
            actions = scheduler_link.get_actions({'do_checks': do_checks, 'do_actions': do_actions,
                                                  'poller_tags': self.poller_tags,
                                                  'reactionner_tags': self.reactionner_tags,
                                                  'worker_name': self.name,
                                                  'module_types': list(self.q_by_mod.keys())})
            if actions:
                logger.debug("Got %d actions from %s", len(actions), scheduler_link.name)
                # We 'tag' them with my_scheduler and put into queue for workers
                self.add_actions(actions, scheduler_link.instance_id)
                logger.debug("Got %d actions from %s in %s",
                             len(actions), scheduler_link.name, time.time() - _t0)
            statsmgr.gauge('actions.added.count.%s' % (scheduler_link.name), len(actions))

    def clean_previous_run(self):
        """Clean variables from previous configuration,
        such as schedulers, broks and external commands

        :return: None
        """
        # Execute the base class treatment...
        super(Satellite, self).clean_previous_run()

        # Clean my lists
        del self.broks[:]
        del self.events[:]

    def do_loop_turn(self):  # pylint: disable=too-many-branches
        """Satellite main loop::

        * Check and delete zombies actions / modules
        * Get returns from queues
        * Adjust worker number
        * Get new actions

        :return: None
        """
        # Try to see if one of my module is dead, and restart previously dead modules
        self.check_and_del_zombie_modules()

        # Also if some zombie workers exist...
        self.check_and_del_zombie_workers()

        # Call modules that manage a starting tick pass
        self.hook_point('tick')

        # Print stats for debug
        for _, sched in self.schedulers.items():
            for mod in self.q_by_mod:
                # In workers we've got actions sent to queue - queue size
                for (worker_id, queue) in list(self.q_by_mod[mod].items()):
                    try:
                        actions_count = queue.qsize()
                        results_count = self.returns_queue.qsize()
                        logger.debug("[%s][%s][%s] actions queued: %d, results queued: %d",
                                     sched.name, mod, worker_id, actions_count, results_count)
                        # Update the statistics
                        statsmgr.gauge('worker.%s.actions-queue-size' % worker_id,
                                       actions_count)
                        statsmgr.gauge('worker.%s.results-queue-size' % worker_id,
                                       results_count)
                    except (IOError, EOFError):
                        pass

        # todo temporaray deactivate all this stuff!
        # Before return or get new actions, see how we managed
        # the former ones: are they still in queue(s)? If so, we
        # must wait more or at least have more workers
        # wait_ratio = self.wait_ratio.get_load()
        # total_q = 0
        # try:
        #     for mod in self.q_by_mod:
        #         for queue in list(self.q_by_mod[mod].values()):
        #             total_q += queue.qsize()
        # except (IOError, EOFError):
        #     pass
        # if total_q != 0 and wait_ratio < 2 * self.worker_polling_interval:
        #     logger.debug("I decide to increase the wait ratio")
        #     self.wait_ratio.update_load(wait_ratio * 2)
        #     # self.wait_ratio.update_load(self.worker_polling_interval)
        # else:
        #     # Go to self.worker_polling_interval on normal run, if wait_ratio
        #     # was >2*self.worker_polling_interval,
        #     # it make it come near 2 because if < 2, go up :)
        #     self.wait_ratio.update_load(self.worker_polling_interval)
        # wait_ratio = self.wait_ratio.get_load()
        # statsmgr.timer('core.wait-ratio', wait_ratio)
        # if self.log_loop:
        #     logger.debug("[%s] wait ratio: %f", self.name, wait_ratio)

        # Maybe we do not have enough workers, we check for it
        # and launch the new ones if needed
        self.adjust_worker_number_by_load()

        # Manage all messages we've got in the last timeout
        # for queue in self.return_messages:
        try:
            logger.debug("[%s] manage action results: %d results",
                         self.name, self.returns_queue.qsize())
            while self.returns_queue.qsize():
                msg = self.returns_queue.get_nowait()
                if msg is None:
                    continue
                logger.debug("Got a message: %s", msg)
                if msg.get_type() == 'Done':
                    logger.debug("Got an action result: %s", msg.get_data())
                    self.manage_action_return(msg.get_data())
                    logger.debug("Managed action result")
                else:
                    logger.warning("Ignoring message of type: %s", msg.get_type())
        except Full:
            logger.warning("Returns queue is full")
        except Empty:
            logger.debug("Returns queue is empty")
        except (IOError, EOFError) as exp:
            logger.warning("My returns queue is no more available: %s", str(exp))
        except Exception as exp:  # pylint: disable=broad-except
            logger.error("Failed getting messages in returns queue: %s", str(exp))
            logger.error(traceback.format_exc())

        for _, sched in self.schedulers.items():
            if sched.wait_homerun:
                logger.debug("scheduler home run: %d results", len(sched.wait_homerun))

        if not self.passive:
            # If we are an active satellite, we do not initiate the check getting
            # and return
            try:
                # We send to our schedulers the results of all finished checks
                logger.debug("pushing results...")
                self.push_results()
            except LinkError as exp:
                logger.warning("Scheduler connection failed, I could not send my results!")

            try:
                # And we get the new actions from our schedulers
                logger.debug("getting new actions...")
                self.get_new_actions()
            except LinkError as exp:
                logger.warning("Scheduler connection failed, I could not get new actions!")

        # Get objects from our modules that are not Worker based
        if self.log_loop:
            logger.debug("[%s] get objects from queues", self.name)
        self.get_objects_from_from_queues()
        statsmgr.gauge('external-commands.count', len(self.external_commands))
        statsmgr.gauge('broks.count', len(self.broks))
        statsmgr.gauge('events.count', len(self.events))

    def do_post_daemon_init(self):
        """Do this satellite (poller or reactionner) post "daemonize" init

        :return: None
        """
        # We can open the Queue for fork AFTER
        self.q_by_mod['fork'] = {}

        # todo: check if this is always useful?
        self.returns_queue = Queue()

    def setup_new_conf(self):
        # pylint: disable=too-many-branches
        """Setup the new configuration received from Arbiter

        This function calls the base satellite treatment and manages the configuration needed
        for a simple satellite daemon that executes some actions (eg. poller or reactionner):
        - configure the passive mode
        - configure the workers
        - configure the tags
        - configure the modules

        :return: None
        """
        # Execute the base class treatment...
        super(Satellite, self).setup_new_conf()

        # ...then our own specific treatment!
        with self.conf_lock:
            logger.info("Received a new configuration")

            # self_conf is our own configuration from the alignak environment
            # self_conf = self.cur_conf['self_conf']

            # Now manage modules
            if not self.have_modules:
                try:
                    self.modules = unserialize(self.cur_conf['modules'], no_load=True)
                except AlignakClassLookupException as exp:  # pragma: no cover, simple protection
                    logger.error('Cannot un-serialize modules configuration '
                                 'received from arbiter: %s', exp)
                if self.modules:
                    logger.info("I received some modules configuration: %s", self.modules)
                    self.have_modules = True

                    for module in self.modules:
                        if module.name not in self.q_by_mod:
                            self.q_by_mod[module.name] = {}

                    self.do_load_modules(self.modules)
                    # and start external modules too
                    self.modules_manager.start_external_instances()
                else:
                    logger.info("I do not have modules")

            # Initialize connection with all our satellites
            logger.info("Initializing connection with my satellites:")
            my_satellites = self.get_links_of_type(s_type='')
            for satellite in list(my_satellites.values()):
                logger.info("- : %s/%s", satellite.type, satellite.name)
                if not self.daemon_connection_init(satellite):
                    logger.error("Satellite connection failed: %s", satellite)

        # Now I have a configuration!
        self.have_conf = True

    def get_daemon_stats(self, details=False):
        """Increase the stats provided by the Daemon base class

        :return: stats dictionary
        :rtype: dict
        """
        # call the daemon one
        res = super(Satellite, self).get_daemon_stats(details=details)

        counters = res['counters']
        counters['broks'] = len(self.broks)
        counters['events'] = len(self.events)
        counters['satellites.workers'] = len(self.workers)

        return res

    def main(self):
        """Main satellite function. Do init and then mainloop

        :return: None
        """
        try:
            # Start the daemon mode
            if not self.do_daemon_init_and_start():
                self.exit_on_error(message="Daemon initialization error", exit_code=3)

            self.do_post_daemon_init()

            # We wait for initial conf
            self.wait_for_initial_conf()
            if self.new_conf:
                # Setup the received configuration
                self.setup_new_conf()

                # Allocate Mortal Threads
                self.adjust_worker_number_by_load()

                # Now main loop
                self.do_main_loop()
                logger.info("Exited from the main loop.")

            self.request_stop()
        except Exception:  # pragma: no cover, this should never happen indeed ;)
            self.exit_on_exception(traceback.format_exc())
            raise
