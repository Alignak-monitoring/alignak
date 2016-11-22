# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016: Alignak team, see AUTHORS.txt file for contributors
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
(one a timeout)

If Arbiter wants it to have a new conf, the satellite forgets the previous
 Schedulers (and actions into) and takes the new ones.
"""

from multiprocessing import active_children, cpu_count

import os
import copy
import logging
import time
import traceback
import threading

from alignak.http.client import HTTPClient, HTTPEXCEPTIONS
from alignak.http.generic_interface import GenericInterface

from alignak.misc.serialization import unserialize, AlignakClassLookupException

from alignak.message import Message
from alignak.worker import Worker
from alignak.load import Load
from alignak.daemon import Daemon
from alignak.stats import statsmgr
from alignak.check import Check  # pylint: disable=W0611
from alignak.objects.module import Module  # pylint: disable=W0611

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class NotWorkerMod(Exception):
    """Class to tell that we are facing a non worker module
    but a standard one

    """
    pass


class BaseSatellite(Daemon):
    """Base Satellite class.
    Subclassed by Alignak (scheduler), Broker and Satellite

    """

    def __init__(self, name, config_file, is_daemon, do_replace, debug, debug_file):
        super(BaseSatellite, self).__init__(name, config_file, is_daemon,
                                            do_replace, debug, debug_file)
        # Ours schedulers
        self.schedulers = {}

        # Now we create the interfaces
        self.http_interface = GenericInterface(self)

        # Can have a queue of external_commands given by modules
        # will be taken by arbiter to process
        self.external_commands = []
        self.external_commands_lock = threading.RLock()

    def watch_for_new_conf(self, timeout):
        """Triggered by Arbiter get to make the satellite wait new conf
        Timeout is short is (1.0 or 0)

        :param timeout: timeout to wait
        :type timeout: float
        :return: None
        TODO: Clean this, handle return a tuple and it is not used
        """
        self.handle_requests(timeout)

    def what_i_managed(self):
        """Get the managed configuration by this satellite

        :return: a dict of scheduler id as key and push_flavor as values
        :rtype: dict
"""
        res = {}
        for (key, val) in self.schedulers.iteritems():
            res[key] = val['push_flavor']
        return res

    def get_external_commands(self):
        """Get the external commands

        :return: External commands list
        :rtype: list
        """
        res = self.external_commands
        self.external_commands = []
        return res

    def do_loop_turn(self):
        """Abstract method for satellite loop turn.
        It must be overridden by class inheriting from Daemon

        :return: None
        """
        raise NotImplementedError()

    def get_previous_sched_id(self, conf, sched_id):
        """Check if we received a conf from this sched before.
        Base on the scheduler id and the name/host/port tuple

        :param conf: configuration to check
        :type conf: dict
        :param sched_id: scheduler id of the conf received
        :type sched_id: str
        :return: previous sched_id if we already received a conf from this scheduler
        :rtype: str
        """
        old_sched_id = ''
        name = conf['name']
        address = conf['address']
        port = conf['port']
        # We can already got this conf id, but with another address

        if sched_id in self.schedulers and address == self.schedulers[sched_id]['address'] and \
                port == self.schedulers[sched_id]['port']:
            old_sched_id = sched_id

        # Check if it not a arbiter reload
        similar_ids = [k for k, s in self.schedulers.iteritems()
                       if (s['name'], s['address'], s['port']) == (name, address, port)]

        if similar_ids:
            old_sched_id = similar_ids[0]  # Only one match actually

        return old_sched_id


class Satellite(BaseSatellite):  # pylint: disable=R0902
    """Satellite class.
    Subclassed by Receiver, Reactionner and Poller

    """
    do_checks = False
    do_actions = False
    my_type = ''

    def __init__(self, name, config_file, is_daemon, do_replace, debug, debug_file):

        super(Satellite, self).__init__(name, config_file, is_daemon, do_replace,
                                        debug, debug_file)

        # Keep broks so they can be eaten by a broker
        self.broks = {}

        self.workers = {}   # dict of active workers

        # Init stats like Load for workers
        self.wait_ratio = Load(initial_value=1)

        self.slave_q = None

        self.returns_queue = None
        self.q_by_mod = {}

        # round robin queue ic
        self.rr_qid = 0

    def pynag_con_init(self, _id):
        """Wrapped function for do_pynag_con_init

        :param _id: scheduler _id to connect to
        :type _id: int
        :return: scheduler connection object or None
        :rtype: alignak.http.client.HTTPClient
        """
        _t0 = time.time()
        res = self.do_pynag_con_init(_id)
        statsmgr.incr('con-init.scheduler', time.time() - _t0)
        return res

    def do_pynag_con_init(self, s_id):
        """Initialize a connection with scheduler having 'uuid'
        Return the new connection to the scheduler if it succeeded,
            else: any error OR sched is inactive: return None.
        NB: if sched is inactive then None is directly returned.


        :param s_id: scheduler s_id to connect to
        :type s_id: int
        :return: scheduler connection object or None
        :rtype: alignak.http.client.HTTPClient
        """
        sched = self.schedulers[s_id]
        if not sched['active']:
            return

        sname = sched['name']
        uri = sched['uri']
        running_id = sched['running_id']
        timeout = sched['timeout']
        data_timeout = sched['data_timeout']
        logger.info("[%s] Init connection with %s at %s (%ss,%ss)",
                    self.name, sname, uri, timeout, data_timeout)

        try:
            sch_con = sched['con'] = HTTPClient(
                uri=uri, strong_ssl=sched['hard_ssl_name_check'],
                timeout=timeout, data_timeout=data_timeout)
        except HTTPEXCEPTIONS, exp:
            logger.warning("[%s] Scheduler %s is not initialized or has network problem: %s",
                           self.name, sname, str(exp))
            sched['con'] = None
            return

        # timeout of 3s by default (short one)
        # and get the running s_id
        try:
            new_run_id = sch_con.get('get_running_id')
            new_run_id = float(new_run_id)
        except (HTTPEXCEPTIONS, KeyError), exp:
            logger.warning("[%s] Scheduler %s is not initialized or has network problem: %s",
                           self.name, sname, str(exp))
            sched['con'] = None
            return

        # The schedulers have been restarted: it has a new run_id.
        # So we clear all verifications, they are obsolete now.
        if sched['running_id'] != 0 and new_run_id != running_id:
            logger.info("[%s] The running id of the scheduler %s changed, "
                        "we must clear its actions",
                        self.name, sname)
            sched['wait_homerun'].clear()
        sched['running_id'] = new_run_id
        logger.info("[%s] Connection OK with scheduler %s", self.name, sname)
        return sch_con

    def manage_action_return(self, action):
        """Manage action return from Workers
        We just put them into the corresponding sched
        and we clean unused properties like sched_id

        :param action: the action to manage
        :type action: alignak.action.Action
        :return: None
        """
        # Maybe our workers end us something else than an action
        # if so, just add this in other queues and return
        cls_type = action.__class__.my_type
        if cls_type not in ['check', 'notification', 'eventhandler']:
            self.add(action)
            return

        # Ok, it's a result. We get it, and fill verifs of the good sched_id
        sched_id = action.sched_id

        # Now we now where to put action, we do not need sched_id anymore
        del action.sched_id

        # Unset the tag of the worker_id too
        try:
            del action.worker_id
        except AttributeError:
            pass

        # And we remove it from the actions queue of the scheduler too
        try:
            del self.schedulers[sched_id]['actions'][action.uuid]
        except KeyError:
            pass
        # We tag it as "return wanted", and move it in the wait return queue
        # Stop, if it is "timeout" we need this information later
        # in the scheduler
        # action.status = 'waitforhomerun'
        try:
            self.schedulers[sched_id]['wait_homerun'][action.uuid] = action
        except KeyError:
            pass

    def manage_returns(self):
        """ Wrapper function of do_manage_returns()

        :return: None
        TODO: Use a decorator for stat
        """
        _t0 = time.time()
        self.do_manage_returns()
        statsmgr.incr('core.manage-returns', time.time() - _t0)

    def do_manage_returns(self):
        """Manage the checks and then
        send a HTTP request to schedulers (POST /put_results)
        REF: doc/alignak-action-queues.png (6)

        :return: None
        """
        # For all schedulers, we check for wait_homerun
        # and we send back results
        for sched_id, sched in self.schedulers.iteritems():
            if not sched['active']:
                continue
            results = sched['wait_homerun']
            # NB: it's **mostly** safe for us to not use some lock around
            # this 'results' / sched['wait_homerun'].
            # Because it can only be modified (for adding new values) by the
            # same thread running this function (that is the main satellite
            # thread), and this occurs exactly in self.manage_action_return().
            # Another possibility is for the sched['wait_homerun'] to be
            # cleared within/by :
            # ISchedulers.get_returns() -> Satelitte.get_return_for_passive()
            # This can so happen in an (http) client thread.
            if not results:
                return
            # So, at worst, some results would be received twice on the
            # scheduler level, which shouldn't be a problem given they are
            # indexed by their "action_id".

            send_ok = False
            try:
                con = sched.get('con')
                if con is None:  # None = not initialized
                    con = self.pynag_con_init(sched_id)
                if con:
                    con.post('put_results',
                             {'results': results.values()})
                    send_ok = True
            except HTTPEXCEPTIONS as err:
                logger.error('Could not send results to scheduler %s : %s',
                             sched['name'], err)
            except Exception as err:
                logger.exception("Unhandled exception trying to send results "
                                 "to scheduler %s: %s", sched['name'], err)
                raise
            finally:
                if send_ok:
                    results.clear()
                else:  # if - and only if - send was not ok,
                    # then "de-init" the sched connection:
                    sched['con'] = None

    def get_return_for_passive(self, sched_id):
        """Get returns of passive actions for a specific scheduler

        :param sched_id: scheduler id
        :type sched_id: int
        :return: Action list
        :rtype: list
        """
        # I do not know this scheduler?
        sched = self.schedulers.get(sched_id)
        if sched is None:
            logger.debug("I do not know this scheduler: %s", sched_id)
            return []

        ret, sched['wait_homerun'] = sched['wait_homerun'], {}

        logger.debug("Preparing to return %s results", len(ret))

        return ret.values()

    def create_and_launch_worker(self, module_name='fork', mortal=True,  # pylint: disable=W0102
                                 __warned=set()):
        """Create and launch a new worker, and put it into self.workers
         It can be mortal or not

        :param module_name: the module name related to the worker
                            default is "fork" for no module
                            Indeed, it is actually the module 'python_name'
        :type module_name: str
        :param mortal: make the Worker mortal or not. Default True
        :type mortal: bool
        :param __warned: Remember the module we warned about.
                         This param is a tuple and as it is only init once (the default value)
                         we use this python behavior that make this set grows with module_name
                         not found on previous call
        :type __warned: set
        :return: None
        """
        # create the input queue of this worker
        try:
            queue = self.sync_manager.Queue()
        # If we got no /dev/shm on linux-based system, we can got problem here.
        # Must raise with a good message
        except OSError, exp:
            # We look for the "Function not implemented" under Linux
            if exp.errno == 38 and os.name == 'posix':
                logger.critical("Got an exception (%s). If you are under Linux, "
                                "please check that your /dev/shm directory exists and"
                                " is read-write.", str(exp))
            raise

        # If we are in the fork module, we do not specify a target
        target = None
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
                    logger.warning("No target found for %s, NOT creating a worker for it..",
                                   module_name)
                    __warned.add(module_name)
                return
        # We want to give to the Worker the name of the daemon (poller or reactionner)
        cls_name = self.__class__.__name__.lower()
        worker = Worker(1, queue, self.returns_queue, self.processes_by_worker,
                        mortal=mortal, max_plugins_output_length=self.max_plugins_output_length,
                        target=target, loaded_into=cls_name, http_daemon=self.http_daemon)
        worker.module_name = module_name
        # save this worker
        self.workers[worker.uuid] = worker

        # And save the Queue of this worker, with key = worker id
        self.q_by_mod[module_name][worker.uuid] = queue
        logger.info("[%s] Allocating new %s Worker: %s", self.name, module_name, worker.uuid)

        # Ok, all is good. Start it!
        worker.start()

    def do_stop(self):
        """Stop all workers modules and sockets

        :return: None
        """
        logger.info("[%s] Stopping all workers", self.name)
        for worker in self.workers.values():
            try:
                worker.terminate()
                worker.join(timeout=1)
            # A already dead worker or in a worker
            except (AttributeError, AssertionError):
                pass
        super(Satellite, self).do_stop()

    def add(self, elt):
        """Add an object to the satellite one
        Handles brok and externalcommand

        :param elt: object to add
        :type elt: object
        :return: None
        """
        cls_type = elt.__class__.my_type
        if cls_type == 'brok':
            # For brok, we TAG brok with our instance_id
            elt.instance_id = 0
            self.broks[elt.uuid] = elt
            return
        elif cls_type == 'externalcommand':
            logger.debug("Queuing an external command '%s'", str(elt.__dict__))
            with self.external_commands_lock:
                self.external_commands.append(elt)

    def get_broks(self):
        """Get brok list from satellite

        :return: A copy of the Brok list
        :rtype: list
        """
        res = copy.copy(self.broks)
        self.broks.clear()
        return res

    def check_and_del_zombie_workers(self):
        """Check if worker are fine and kill them if not.
        Dispatch the actions in the worker to another one

        :return: None
        """
        # Active children make a join with everyone, useful :)
        active_children()

        w_to_del = []
        for worker in self.workers.values():
            # If a worker goes down and we did not ask him, it's not
            # good: we can think that we have a worker and it's not True
            # So we del it
            if not worker.is_alive():
                logger.warning("[%s] The worker %s goes down unexpectedly!", self.name, worker.uuid)
                # Terminate immediately
                worker.terminate()
                worker.join(timeout=1)
                w_to_del.append(worker.uuid)

        # OK, now really del workers from queues
        # And requeue the actions it was managed
        for w_id in w_to_del:
            worker = self.workers[w_id]

            # Del the queue of the module queue
            del self.q_by_mod[worker.module_name][worker.uuid]

            for sched_id in self.schedulers:
                sched = self.schedulers[sched_id]
                for act in sched['actions'].values():
                    if act.status == 'queue' and act.worker_id == w_id:
                        # Got a check that will NEVER return if we do not
                        # restart it
                        self.assign_to_a_queue(act)

            # So now we can really forgot it
            del self.workers[w_id]

    def adjust_worker_number_by_load(self):
        """Try to create the minimum workers specified in the configuration

        :return: None
        """
        to_del = []
        logger.debug("[%s] Trying to adjust worker number."
                     " Actual number : %d, min per module : %d, max per module : %d",
                     self.name, len(self.workers), self.min_workers, self.max_workers)

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
            logger.debug("[%s] The module %s is not a worker one, "
                         "I remove it from the worker list", self.name, mod)
            del self.q_by_mod[mod]
        # TODO: if len(workers) > 2*wish, maybe we can kill a worker?

    def _got_queue_from_action(self, action):
        """Find action queue for the action depending on the module.
        The id is found with action modulo on action id

        :param a: the action that need action queue to be assigned
        :type action: object
        :return: worker id and queue. (0, None) if no queue for the module_type
        :rtype: tuple
        """
        # get the module name, if not, take fork
        mod = getattr(action, 'module_type', 'fork')
        queues = self.q_by_mod[mod].items()

        # Maybe there is no more queue, it's very bad!
        if len(queues) == 0:
            return (0, None)

        # if not get action round robin index to get action queue based
        # on the action id
        self.rr_qid = (self.rr_qid + 1) % len(queues)
        (index, queue) = queues[self.rr_qid]

        # return the id of the worker (i), and its queue
        return (index, queue)

    def add_actions(self, lst, sched_id):
        """Add a list of actions to the satellite queues

        :param lst: Action list
        :type lst: list
        :param sched_id: sheduler id to assign to
        :type sched_id: int
        :return: None
        """
        for act in lst:
            # First we look if we do not already have it, if so
            # do nothing, we are already working!
            if act.uuid in self.schedulers[sched_id]['actions']:
                continue
            act.sched_id = sched_id
            act.status = 'queue'
            self.assign_to_a_queue(act)

    def assign_to_a_queue(self, action):
        """Take an action and put it to action queue

        :param action: action to put
        :type action: alignak.action.Action
        :return: None
        """
        msg = Message(_id=0, _type='Do', data=action)
        (index, queue) = self._got_queue_from_action(action)
        # Tag the action as "in the worker i"
        action.worker_id = index
        if queue is not None:
            queue.put(msg)

    def get_new_actions(self):
        """ Wrapper function for do_get_new_actions
        For stats purpose

        :return: None
        TODO: Use a decorator
        """
        _t0 = time.time()
        self.do_get_new_actions()
        statsmgr.incr('core.get-new-actions', time.time() - _t0)

    def do_get_new_actions(self):
        """Get new actions from schedulers
        Create a Message and put into the module queue
        REF: doc/alignak-action-queues.png (1)

        :return: None
        """
        # Here are the differences between a
        # poller and a reactionner:
        # Poller will only do checks,
        # reactionner do actions (notif + event handlers)
        do_checks = self.__class__.do_checks
        do_actions = self.__class__.do_actions

        # We check for new check in each schedulers and put the result in new_checks
        for sched_id in self.schedulers:
            sched = self.schedulers[sched_id]
            # If sched is not active, I do not try return
            if not sched['active']:
                continue

            try:
                try:
                    con = sched['con']
                except KeyError:
                    con = None
                if con is not None:  # None = not initialized
                    # OK, go for it :)
                    tmp = con.get('get_checks', {
                        'do_checks': do_checks, 'do_actions': do_actions,
                        'poller_tags': self.poller_tags,
                        'reactionner_tags': self.reactionner_tags,
                        'worker_name': self.name,
                        'module_types': self.q_by_mod.keys()
                    },
                        wait='long')
                    # Explicit serialization
                    tmp = unserialize(tmp, True)
                    logger.debug("Ask actions to %s, got %d", sched_id, len(tmp))
                    # We 'tag' them with sched_id and put into queue for workers
                    # REF: doc/alignak-action-queues.png (2)
                    self.add_actions(tmp, sched_id)
                else:  # no con? make the connection
                    self.pynag_con_init(sched_id)
            # Ok, con is unknown, so we create it
            # Or maybe is the connection lost, we recreate it
            except (HTTPEXCEPTIONS, KeyError), exp:
                logger.exception('get_new_actions HTTP exception:: %s', exp)
                self.pynag_con_init(sched_id)
            # scheduler must not be initialized
            # or scheduler must not have checks
            except AttributeError, exp:
                logger.exception('get_new_actions attribute exception:: %s', exp)
            # Bad data received
            except AlignakClassLookupException as exp:
                logger.error('Cannot un-serialize actions received: %s', exp)
            # What the F**k? We do not know what happened,
            # log the error message if possible.
            except Exception, exp:
                logger.exception('A satellite raised an unknown exception:: %s', exp)
                raise

    def get_returns_queue_len(self):
        """Wrapper for returns_queue.qsize method. Return queue length

        :return: queue length
        :rtype: int
        """
        return self.returns_queue.qsize()

    def get_returns_queue_item(self):
        """Wrapper for returns_queue.get method. Return an queue element

        :return: queue Message
        :rtype: alignak.message.Message
        """
        return self.returns_queue.get()

    def clean_previous_run(self):
        """Clean variables from previous configuration,
        such as schedulers, broks and external commands

        :return: None
        """
        # Clean all lists
        self.schedulers.clear()
        self.broks.clear()
        with self.external_commands_lock:
            self.external_commands = self.external_commands[:]

    def do_loop_turn(self):
        """Satellite main loop::

        * Setup new conf if necessary
        * Watch for new conf
        * Check and delete zombies actions / modules
        * Get returns from queues
        * Adjust worker number
        * Get new actions

        :return: None
        """
        logger.debug("Loop turn")
        # Maybe the arbiter ask us to wait for a new conf
        # If true, we must restart all...
        if self.cur_conf is None:
            # Clean previous run from useless objects
            # and close modules
            self.clean_previous_run()

            self.wait_for_initial_conf()
            # we may have been interrupted or so; then
            # just return from this loop turn
            if not self.new_conf:
                return
            self.setup_new_conf()

        # Now we check if arbiter speak to us.
        # If so, we listen to it
        # When it push a conf, we reinit connections
        # Sleep in waiting a new conf :)
        # TODO: manage the diff again.
        while self.timeout > 0:
            begin = time.time()
            self.watch_for_new_conf(self.timeout)
            end = time.time()
            if self.new_conf:
                self.setup_new_conf()
            self.timeout = self.timeout - (end - begin)

        logger.debug(" ======================== ")

        self.timeout = self.polling_interval

        # Check if zombies workers are among us :)
        # If so: KILL THEM ALL!!!
        self.check_and_del_zombie_workers()

        # But also modules
        self.check_and_del_zombie_modules()

        # Print stats for debug
        for sched_id in self.schedulers:
            sched = self.schedulers[sched_id]
            for mod in self.q_by_mod:
                # In workers we've got actions send to queue - queue size
                for (index, queue) in self.q_by_mod[mod].items():
                    logger.debug("[%s][%s][%s] Stats: Workers:%s (Queued:%d TotalReturnWait:%d)",
                                 sched_id, sched['name'], mod,
                                 index, queue.qsize(), self.get_returns_queue_len())
                    # also update the stats module
                    statsmgr.incr('core.worker-%s.queue-size' % mod, queue.qsize())

        # Before return or get new actions, see how we manage
        # old ones: are they still in queue (s)? If True, we
        # must wait more or at least have more workers
        wait_ratio = self.wait_ratio.get_load()
        total_q = 0
        for mod in self.q_by_mod:
            for queue in self.q_by_mod[mod].values():
                total_q += queue.qsize()
        if total_q != 0 and wait_ratio < 2 * self.polling_interval:
            logger.debug("I decide to up wait ratio")
            self.wait_ratio.update_load(wait_ratio * 2)
            # self.wait_ratio.update_load(self.polling_interval)
        else:
            # Go to self.polling_interval on normal run, if wait_ratio
            # was >2*self.polling_interval,
            # it make it come near 2 because if < 2, go up :)
            self.wait_ratio.update_load(self.polling_interval)
        wait_ratio = self.wait_ratio.get_load()
        logger.debug("Wait ratio: %f", wait_ratio)
        statsmgr.incr('core.wait-ratio', wait_ratio)

        # We can wait more than 1s if needed,
        # no more than 5s, but no less than 1
        timeout = self.timeout * wait_ratio
        timeout = max(self.polling_interval, timeout)
        self.timeout = min(5 * self.polling_interval, timeout)
        statsmgr.incr('core.timeout', wait_ratio)

        # Maybe we do not have enough workers, we check for it
        # and launch the new ones if needed
        self.adjust_worker_number_by_load()

        # Manage all messages we've got in the last timeout
        # for queue in self.return_messages:
        while self.get_returns_queue_len() != 0:
            self.manage_action_return(self.get_returns_queue_item())

        # If we are passive, we do not initiate the check getting
        # and return
        if not self.passive:
            # Now we can get new actions from schedulers
            self.get_new_actions()

            # We send all finished checks
            # REF: doc/alignak-action-queues.png (6)
            self.manage_returns()

        # Get objects from our modules that are not worker based
        self.get_objects_from_from_queues()

        # Say to modules it's a new tick :)
        self.hook_point('tick')

    def do_post_daemon_init(self):
        """Do this satellite (poller or reactionner) post "daemonize" init

        :return: None
        """
        # self.s = Queue() # Global Master -> Slave
        # We can open the Queue for fork AFTER
        self.q_by_mod['fork'] = {}

        self.returns_queue = self.sync_manager.Queue()

        # For multiprocess things, we should not have
        # socket timeouts.
        import socket
        socket.setdefaulttimeout(None)

    def setup_new_conf(self):  # pylint: disable=R0915,R0912
        """Setup new conf received from Arbiter

        :return: None
        """
        with self.conf_lock:
            conf = self.new_conf
            logger.debug("Sending us a configuration %s", conf)
            self.new_conf = None
            self.cur_conf = conf
            g_conf = conf['global']

            # Got our name from the globals
            if 'poller_name' in g_conf:
                name = g_conf['poller_name']
            elif 'reactionner_name' in g_conf:
                name = g_conf['reactionner_name']
            else:
                name = 'Unnamed satellite'
            self.name = name
            # Set my own process title
            self.set_proctitle(self.name)

            # local statsd
            self.statsd_host = g_conf['statsd_host']
            self.statsd_port = g_conf['statsd_port']
            self.statsd_prefix = g_conf['statsd_prefix']
            self.statsd_enabled = g_conf['statsd_enabled']

            # we got a name, we can now say it to our statsmgr
            if 'poller_name' in g_conf:
                statsmgr.register(self.name, 'poller',
                                  statsd_host=self.statsd_host, statsd_port=self.statsd_port,
                                  statsd_prefix=self.statsd_prefix,
                                  statsd_enabled=self.statsd_enabled)
            else:
                statsmgr.register(self.name, 'reactionner',
                                  statsd_prefix=self.statsd_prefix,
                                  statsd_enabled=self.statsd_enabled)

            self.passive = g_conf['passive']
            if self.passive:
                logger.info("Passive mode enabled.")

            # If we've got something in the schedulers, we do not want it anymore
            for sched_id in conf['schedulers']:

                old_sched_id = self.get_previous_sched_id(conf['schedulers'][sched_id], sched_id)

                if old_sched_id:
                    logger.info("We already got the conf %s (%s)", old_sched_id, name)
                    wait_homerun = self.schedulers[old_sched_id]['wait_homerun']
                    actions = self.schedulers[old_sched_id]['actions']
                    del self.schedulers[old_sched_id]

                sched = conf['schedulers'][sched_id]
                self.schedulers[sched_id] = sched

                if sched['name'] in g_conf['satellitemap']:
                    sched.update(g_conf['satellitemap'][sched['name']])
                proto = 'http'
                if sched['use_ssl']:
                    proto = 'https'
                uri = '%s://%s:%s/' % (proto, sched['address'], sched['port'])

                self.schedulers[sched_id]['uri'] = uri
                if old_sched_id:
                    self.schedulers[sched_id]['wait_homerun'] = wait_homerun
                    self.schedulers[sched_id]['actions'] = actions
                else:
                    self.schedulers[sched_id]['wait_homerun'] = {}
                    self.schedulers[sched_id]['actions'] = {}
                self.schedulers[sched_id]['running_id'] = 0
                self.schedulers[sched_id]['active'] = sched['active']
                self.schedulers[sched_id]['timeout'] = sched['timeout']
                self.schedulers[sched_id]['data_timeout'] = sched['data_timeout']

                # Do not connect if we are a passive satellite
                if not self.passive and not old_sched_id:
                    # And then we connect to it :)
                    self.pynag_con_init(sched_id)

            logger.debug("We have our schedulers: %s", self.schedulers)
            logger.info("We have our schedulers:")
            for daemon in self.schedulers.values():
                logger.info(" - %s ", daemon['name'])

            # Now the limit part, 0 mean: number of cpu of this machine :)
            # if not available, use 4 (modern hardware)
            self.max_workers = g_conf['max_workers']
            if self.max_workers == 0:
                try:
                    self.max_workers = cpu_count()
                except NotImplementedError:
                    self.max_workers = 4
            logger.info("Using max workers: %s", self.max_workers)
            self.min_workers = g_conf['min_workers']
            if self.min_workers == 0:
                try:
                    self.min_workers = cpu_count()
                except NotImplementedError:
                    self.min_workers = 4
            logger.info("Using min workers: %s", self.min_workers)

            self.processes_by_worker = g_conf['processes_by_worker']
            self.polling_interval = g_conf['polling_interval']
            self.timeout = self.polling_interval

            # Now set tags
            # ['None'] is the default tags
            self.poller_tags = g_conf.get('poller_tags', ['None'])
            self.reactionner_tags = g_conf.get('reactionner_tags', ['None'])
            self.max_plugins_output_length = g_conf.get('max_plugins_output_length', 8192)

            # Set our giving timezone from arbiter
            use_timezone = g_conf['use_timezone']
            if use_timezone != 'NOTSET':
                logger.info("Setting our timezone to %s", use_timezone)
                os.environ['TZ'] = use_timezone
                time.tzset()

            # Now manage modules
            # TODO: check how to better handle this with modules_manager..
            mods = unserialize(g_conf['modules'], True)
            self.new_modules_conf = []
            for module in mods:
                # If we already got it, bypass
                if module.get_name() not in self.q_by_mod:
                    logger.info("Add module object: %s", module)
                    logger.debug("Add module object %s", str(module))
                    self.new_modules_conf.append(module)
                    logger.info("Got module: %s ", module.get_name())
                    self.q_by_mod[module.get_name()] = {}

    def get_stats_struct(self):
        """Get state of modules and create a scheme for stats data of daemon
        This may be overridden in subclasses

        :return: A dict with the following structure
        ::

           { 'metrics': ['%s.%s.external-commands.queue %d %d'],
             'version': VERSION,
             'name': self.name,
             'type': _type,
             'passive': self.passive,
             'modules':
                         {'internal': {'name': "MYMODULE1", 'state': 'ok'},
                         {'external': {'name': "MYMODULE2", 'state': 'stopped'},
                        ]
           }

        :rtype: dict
        """
        now = int(time.time())
        # call the daemon one
        res = super(Satellite, self).get_stats_struct()
        _type = self.__class__.my_type
        res.update({'name': self.name, 'type': _type})
        # The receiver do not have a passive prop
        if hasattr(self, 'passive'):
            res['passive'] = self.passive
        metrics = res['metrics']
        # metrics specific
        metrics.append('%s.%s.external-commands.queue %d %d' % (
            _type, self.name, len(self.external_commands), now))

        return res

    def main(self):
        """Main satellite function. Do init and then mainloop

        :return: None
        """
        try:
            self.setup_alignak_logger()

            # Look if we are enabled or not. If ok, start the daemon mode
            self.look_for_early_exit()
            self.do_daemon_init_and_start()

            self.do_post_daemon_init()

            self.load_modules_manager()

            # We wait for initial conf
            self.wait_for_initial_conf()
            if not self.new_conf:  # we must have either big problem or was requested to shutdown
                return
            self.setup_new_conf()

            # We can load our modules now
            self.do_load_modules(self.new_modules_conf)
            # And even start external ones
            self.modules_manager.start_external_instances()

            # Allocate Mortal Threads
            for _ in xrange(1, self.min_workers):
                to_del = []
                for mod in self.q_by_mod:
                    try:
                        self.create_and_launch_worker(module_name=mod)
                    # Maybe this modules is not a true worker one.
                    # if so, just delete if from q_by_mod
                    except NotWorkerMod:
                        to_del.append(mod)

                for mod in to_del:
                    logger.debug("The module %s is not a worker one, "
                                 "I remove it from the worker list", mod)
                    del self.q_by_mod[mod]

            # Now main loop
            self.do_mainloop()
        except Exception:
            self.print_unrecoverable(traceback.format_exc())
            raise
