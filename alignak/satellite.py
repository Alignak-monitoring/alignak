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

from Queue import Empty, Full
from multiprocessing import Queue, active_children, cpu_count

import os
import copy
import logging
import time
import traceback
import threading

from alignak.http.client import HTTPClient, HTTPClientException, HTTPClientConnectionException
from alignak.http.client import HTTPClientTimeoutException
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

    def __init__(self, name, config_file, is_daemon, do_replace, debug, debug_file,
                 port, local_log):
        super(BaseSatellite, self).__init__(name, config_file, is_daemon, do_replace, debug,
                                            debug_file, port, local_log)
        # Ours schedulers
        self.schedulers = {}

        # Now we create the interfaces
        self.http_interface = GenericInterface(self)

        # Can have a queue of external_commands given by modules
        # will be taken by arbiter to process
        self.external_commands = []
        self.external_commands_lock = threading.RLock()

    def do_loop_turn(self):
        """Abstract method for daemon loop turn.
        Inherited from Daemon, must be overriden by the inheriting class.

        :return: None
        """
        raise NotImplementedError()

    def watch_for_new_conf(self, timeout=0):
        """Check if a new configuration was sent to the daemon

        This function is called on each daemon loop turn. Basically it is a sleep...

        :param timeout: timeout to wait. Default is no wait time.
        :type timeout: float
        :return: None
        """
        self.make_a_pause(timeout=timeout)

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

    @staticmethod
    def is_connection_try_too_close(link, delay=5):
        """Check if last_connection has been made very recently

        :param link: connection with an Alignak daemon
        :type link: list
        :delay link: minimum delay between two connections
        :type dealay: int
        :return: True if last connection has been made less than `delay` seconds
        :rtype: bool
        """
        if time.time() - link['last_connection'] < delay:
            return True
        return False

    def get_links_from_type(self, s_type):
        """Return the `s_type` satellite list (eg. schedulers), else None

        :param s_type: name of object
        :type s_type: str
        :return: return the object linked
        :rtype: alignak.objects.satellitelink.SatelliteLinks
        """
        satellites = {
            'arbiter': getattr(self, 'arbiters', None),
            'scheduler': getattr(self, 'schedulers', None),
            'broker': getattr(self, 'brokers', None),
            'poller': getattr(self, 'pollers', None),
            'reactionner': getattr(self, 'reactionners', None),
            'receiver': getattr(self, 'receivers', None)
        }
        if s_type in satellites:
            return satellites[s_type]

        return None

    def daemon_connection_init(self, s_id, s_type='scheduler'):
        """Wrapper function for the real function do_
        Only for timing the connection

        This function returns True if the connection is initialized,
        else False if a problem occured

        :param s_id: id
        :type s_id: int
        :param s_type: type of item
        :type s_type: str
        :return: the same as do_daemon_connection_init returns
        """
        _t0 = time.time()
        res = self.do_daemon_connection_init(s_id, s_type)
        statsmgr.timer('con-init.%s' % s_type, time.time() - _t0)
        return res

    def do_daemon_connection_init(self, s_id, s_type='scheduler'):
        # pylint: disable=too-many-return-statements
        """Initialize a connection with the `s_type` daemon identified with 's_id'.

        Initialize the connection (HTTP client) to the daemon and get its running identifier.
        Returns True if it succeeds else if any error occur or the daemon is inactive
        it returns False.

        NB: if the daemon is configured as passive, or if it is an scheduler that is
        inactive then it returns False without trying a connection.

        :param s_id: scheduler s_id to connect to
        :type s_id: int
        :param s_type: 'scheduler', else daemon type
        :type s_type: str
        :return: True if the connection is established
        """
        logger.debug("do_daemon_connection_init: %s %s", s_type, s_id)
        # Get the appropriate links list...
        links = self.get_links_from_type(s_type)
        if links is None:
            logger.critical("Unknown type '%s' for the connection!", s_type)
            return False
        # ... and check if required link exist in this list.
        if s_id not in links:
            logger.warning("Unknown identifier '%s' for the %s connection!", s_id, s_type)
            return False

        link = links[s_id]

        # We do not want to initiate the connections to the passive
        # daemons (eg. pollers, reactionners)
        if hasattr(link, 'passive') and link['passive']:
            logger.error("Do not initialize connection with '%s' "
                         "because it is configured as passive", link['name'])
            return False

        # todo: perharps check this for any daemon connection? Not only for a scheduler one...
        if s_type == 'scheduler':
            # If the link is a scheduler and it is not active, I do not try to init
            # it is just useless
            if not link['active']:
                logger.warning("Scheduler '%s' is not active, "
                               "do not initalize its connection!", link['name'])
                return False

        logger.info("Initializing connection with %s (%s), attempt: %d / %d",
                    link['name'], s_id, link['connection_attempt'], link['max_failed_connections'])

        # # If we try to connect too much, we slow down our connection tries...
        # if self.is_connection_try_too_close(link, delay=5):
        #     logger.info("Too close connection retry, postponed")
        #     return False

        # Get timeout for the daemon link (default defined in the satellite link...)
        timeout = link['timeout']
        data_timeout = link['data_timeout']

        # Ok, we now update our last connection attempt
        link['last_connection'] = time.time()
        # and we increment the number of connection attempts
        link['connection_attempt'] += 1

        running_id = link['running_id']

        # Create the HTTP client for the connection
        try:
            link['con'] = HTTPClient(uri=link['uri'],
                                     strong_ssl=link['hard_ssl_name_check'],
                                     timeout=timeout, data_timeout=data_timeout)
        # Creating an HTTP client connection with requests do not raise any exception at all!
        except Exception as exp:  # pylint: disable=broad-except
            #  pragma: no cover, simple protection
            logger.error("[%s] HTTPClient exception: %s", link['name'], str(exp))
            link['con'] = None
            return False

        # Get the connection running identifier - first client / server communication
        try:
            logger.debug("[%s] Getting running identifier from '%s'", self.name, link['name'])
            _t0 = time.time()
            new_running_id = link['con'].get('get_running_id')
            statsmgr.timer('con-get-running-id.%s' % s_type, time.time() - _t0)
            new_running_id = float(new_running_id)

            # If the daemon has been restarted: it has a new running_id.
            # So we clear all verifications, they are obsolete now.
            if new_running_id != running_id:
                logger.info("[%s] The running id of the %s %s changed (%s -> %s), "
                            "we must clear its actions",
                            self.name, s_type, link['name'], running_id, new_running_id)
                if hasattr(link, 'wait_homerun'):
                    link['wait_homerun'].clear()
                if hasattr(link, 'broks'):
                    link['broks'].clear()

            # Ok all is done, we can save this new running identifier
            link['running_id'] = new_running_id
        except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
            logger.warning("Connection error with the %s '%s' when getting running id",
                           s_type, link['name'])
            link['con'] = None
            return False
        except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
            logger.warning("Connection timeout with the %s '%s' when getting running id",
                           s_type, link['name'])
            link['con'] = None
            return False
        except HTTPClientException as exp:  # pragma: no cover, simple protection
            logger.error("Error with the %s '%s' when getting running id: %s",
                         s_type, link['name'], str(exp))
            link['con'] = None
            return False

        # If I am a broker and I reconnect to my scheduler
        # pylint: disable=E1101
        if self.daemon_type == 'broker' and s_type == 'scheduler':
            logger.info("[%s] Asking initial broks from '%s'", self.name, link['name'])
            try:
                _t0 = time.time()
                link['con'].get('fill_initial_broks', {'bname': self.name}, wait='long')
                statsmgr.timer('con-fill-initial-broks.%s' % s_type, time.time() - _t0)
            except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
                logger.warning("Connection error with the %s '%s' when getting initial broks",
                               s_type, link['name'])
                link['con'] = None
                return False
            except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
                logger.warning("Connection timeout with the %s '%s' when getting initial broks",
                               s_type, link['name'])
                link['con'] = None
                return False
            except HTTPClientException as exp:  # pragma: no cover, simple protection
                logger.error("Error with the %s '%s' when getting initial broks: %s",
                             s_type, link['name'], str(exp))
                link['con'] = None
                return False

        # Here, everything is ok, the connection was established and
        # we got the daemon running identifier!
        link['connection_attempt'] = 0
        logger.info("Connection OK with the %s: %s", s_type, link['name'])
        return True

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

    def __init__(self, name, config_file, is_daemon, do_replace, debug, debug_file,
                 port, local_log):

        super(Satellite, self).__init__(name, config_file, is_daemon, do_replace,
                                        debug, debug_file, port, local_log)

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

    def manage_action_return(self, action):
        """Manage action return from Workers
        We just put them into the corresponding sched
        and we clean unused properties like sched_id

        :param action: the action to manage
        :type action: alignak.action.Action
        :return: None
        """
        # Maybe our workers send us something else than an action
        # if so, just add this in other queues and return
        cls_type = action.__class__.my_type
        if cls_type not in ['check', 'notification', 'eventhandler']:
            self.add(action)
            return

        # Ok, it's a result. We get it, and fill verifs of the good sched_id
        sched_id = action.sched_id
        logger.debug("Got action return: %s / %s", sched_id, action.uuid)

        try:
            # Now that we know where to put the action result, we do not need sched_id anymore
            # Unset the tag of the worker_id too
            del action.sched_id
            del action.worker_id
        except AttributeError:  # pragma: no cover, simple protection
            logger.error("AttributeError Got action return: %s / %s", sched_id, action)

        # And we remove it from the actions queue of the scheduler too
        try:
            del self.schedulers[sched_id]['actions'][action.uuid]
        except KeyError as exp:
            logger.error("KeyError del scheduler action: %s / %s - %s",
                         sched_id, action.uuid, str(exp))

        # We tag it as "return wanted", and move it in the wait return queue
        try:
            self.schedulers[sched_id]['wait_homerun'][action.uuid] = action
        except KeyError:  # pragma: no cover, simple protection
            logger.error("KeyError Add home run action: %s / %s - %s",
                         sched_id, action.uuid, str(exp))

    def manage_returns(self):
        """ Wrapper function of do_manage_returns()

        :return: None
        TODO: Use a decorator for stat
        """
        _t0 = time.time()
        self.do_manage_returns()
        statsmgr.timer('core.manage-returns', time.time() - _t0)

    def do_manage_returns(self):
        """Manage the checks and then
        send a HTTP request to schedulers (POST /put_results)
        REF: doc/alignak-action-queues.png (6)

        :return: None
        """
        # For all schedulers, we check for wait_homerun
        # and we send back results
        for sched_id in self.schedulers:
            sched = self.schedulers[sched_id]
            # todo: perharps a warning log here?
            if not sched['active']:
                logger.debug("My scheduler '%s' is not active currently", sched['name'])
                continue
            # NB: it's **mostly** safe for us to not use some lock around
            # this 'results' / sched['wait_homerun'].
            # Because it can only be modified (for adding new values) by the
            # same thread running this function (that is the main satellite
            # thread), and this occurs exactly in self.manage_action_return().
            # Another possibility is for the sched['wait_homerun'] to be
            # cleared within/by :
            # ISchedulers.get_returns() -> Satelitte.get_return_for_passive()
            # This can so happen in an (http) client thread.
            results = sched['wait_homerun']
            if not results:
                continue
            # So, at worst, some results would be received twice on the
            # scheduler level, which shouldn't be a problem given they are
            # indexed by their "action_id".

            if sched['con'] is None:
                if not self.daemon_connection_init(sched_id, s_type='scheduler'):
                    if sched['connection_attempt'] <= sched['max_failed_connections']:
                        logger.warning("The connection for the scheduler '%s' cannot be "
                                       "established, it is not possible to send results to "
                                       "this scheduler.", sched['name'])
                    else:
                        logger.error("The connection for the scheduler '%s' cannot be "
                                     "established, it is not possible to send results to "
                                     "this scheduler.", sched['name'])
                    continue
            logger.debug("manage returns, scheduler: %s", sched['name'])

            try:
                sched['con'].post('put_results', {'from': self.name, 'results': results.values()})
                results.clear()
            except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
                logger.warning("Connection error with the scheduler '%s' when managing returns",
                               sched['name'])
                sched['con'] = None
            except HTTPClientTimeoutException as exp:
                logger.warning("Connection timeout with the scheduler '%s' "
                               "when putting results: %s", sched['name'], str(exp))
                sched['con'] = None
            except HTTPClientException as exp:  # pragma: no cover, simple protection
                logger.error("Error with the scheduler '%s' when putting results: %s",
                             sched['name'], str(exp))
                sched['con'] = None
            except Exception as err:  # pragma: no cover, simple protection
                logger.exception("Unhandled exception trying to send results "
                                 "to scheduler %s: %s", sched['name'], err)
                sched['con'] = None
                raise

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
            logger.warning("I do not know this scheduler: %s / %s", sched_id, self.schedulers)
            return []

        ret, sched['wait_homerun'] = sched['wait_homerun'], {}
        logger.debug("Results: %s" % (ret.values()) if ret else "No results available")

        return ret.values()

    def create_and_launch_worker(self, module_name='fork'):
        """Create and launch a new worker, and put it into self.workers
         It can be mortal or not

        :param module_name: the module name related to the worker
                            default is "fork" for no module
                            Indeed, it is actually the module 'python_name'
        :type module_name: str
        :return: None
        """
        logger.info("[%s] Allocating new '%s' worker...", self.name, module_name)

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

        logger.info("[%s] Started '%s' worker: %s (pid=%d)",
                    self.name, module_name, worker.get_id(), worker.get_pid())

    def do_stop(self):
        """Stop all workers

        :return: None
        """
        logger.info("[%s] Stopping all workers (%d)", self.name, len(self.workers))
        for worker in self.workers.values():
            try:
                logger.info("[%s] - stopping '%s'", self.name, worker.get_id())
                worker.terminate()
                worker.join(timeout=1)
                logger.info("[%s] - stopped", self.name)
            # A already dead worker or in a worker
            except (AttributeError, AssertionError):
                pass
            except Exception as exp:  # pylint: disable=broad-except
                logger.error("[%s] exception: %s", self.name, str(exp))

        super(Satellite, self).do_stop()

    def add(self, elt):  # pragma: no cover, is it useful?
        """Add an object to the satellite one
        Handles brok and externalcommand

        TODO: confirm that this method is useful. It seems that it is always overloaded ...

        :param elt: object to add
        :type elt: object
        :return: None
        """
        cls_type = elt.__class__.my_type
        if cls_type == 'brok':
            # For brok, we TAG brok with our instance_id
            elt.instance_id = self.instance_id
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

    def check_and_del_zombie_workers(self):  # pragma: no cover, not with unit tests...
        """Check if worker are fine and kill them if not.
        Dispatch the actions in the worker to another one

        TODO: see if unit tests would allow to check this code?

        :return: None
        """
        # Active children make a join with everyone, useful :)
        active_children()

        w_to_del = []
        for worker in self.workers.values():
            # If a worker goes down and we did not ask him, it's not
            # good: we can think that we have a worker and it's not True
            # So we del it
            logger.debug("[%s] checking if worker %s (pid=%d) is alive",
                         self.name, worker.get_id(), worker.get_pid())
            if not self.interrupted and not worker.is_alive():
                logger.warning("[%s] The worker %s (pid=%d) went down unexpectedly!",
                               self.name, worker.get_id(), worker.get_pid())
                # Terminate immediately
                worker.terminate()
                worker.join(timeout=1)
                w_to_del.append(worker.get_id())

        # OK, now really del workers from queues
        # And requeue the actions it was managed
        for w_id in w_to_del:
            worker = self.workers[w_id]

            # Del the queue of the module queue
            del self.q_by_mod[worker.module_name][worker.get_id()]

            for sched_id in self.schedulers:
                sched = self.schedulers[sched_id]
                for act in sched['actions'].values():
                    if act.status == 'queue' and act.worker_id == w_id:
                        # Got a check that will NEVER return if we do not restart it
                        self.assign_to_a_queue(act)

            # So now we can really forgot it
            del self.workers[w_id]

    def adjust_worker_number_by_load(self):
        """Try to create the minimum workers specified in the configuration

        :return: None
        """
        if self.interrupted:
            logger.debug("[%s] Trying to adjust worker number. Ignoring because we are stopping.",
                         self.name)
            return

        to_del = []
        logger.debug("[%s] checking worker count."
                     " Currently: %d workers, min per module : %d, max per module : %d",
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
            logger.warning("[%s] The module %s is not a worker one, "
                           "I remove it from the worker list.", self.name, mod)
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
        queues = self.q_by_mod[mod].items()

        # Maybe there is no more queue, it's very bad!
        if not queues:
            return (0, None)

        # if not get action round robin index to get action queue based
        # on the action id
        self.rr_qid = (self.rr_qid + 1) % len(queues)
        (worker_id, queue) = queues[self.rr_qid]

        # return the id of the worker (i), and its queue
        return (worker_id, queue)

    def add_actions(self, actions_list, sched_id):
        """Add a list of actions to the satellite queues

        :param actions_list: Actions list to add
        :type actions_list: list
        :param sched_id: sheduler id to assign to
        :type sched_id: int
        :return: None
        """
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
            if uuid in self.schedulers[sched_id]['actions']:
                continue
            # Action is attached to a scheduler
            action.sched_id = sched_id
            self.schedulers[sched_id]['actions'][action.uuid] = action
            self.assign_to_a_queue(action)
            logger.debug("Added action %s to a worker queue", action.uuid)

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
        action.worker_id = worker_id
        action.status = 'queue'

        msg = Message(_type='Do', data=action, source=self.name)
        logger.debug("Queuing message: %s", msg)
        queue.put_nowait(msg)
        logger.debug("Queued")

    def get_new_actions(self):
        """ Wrapper function for do_get_new_actions
        For stats purpose

        :return: None
        TODO: Use a decorator
        """
        _t0 = time.time()
        self.do_get_new_actions()
        statsmgr.timer('core.get-new-actions', time.time() - _t0)

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
        for sched_id, sched in self.schedulers.iteritems():
            if not sched['active']:
                logger.debug("My scheduler '%s' is not active currently", sched['name'])
                continue

            if sched['con'] is None:
                if not self.daemon_connection_init(sched_id, s_type='scheduler'):
                    if sched['connection_attempt'] <= sched['max_failed_connections']:
                        logger.warning("The connection for the scheduler '%s' cannot be "
                                       "established, it is not possible to get checks from "
                                       "this scheduler.", sched['name'])
                    else:
                        logger.error("The connection for the scheduler '%s' cannot be "
                                     "established, it is not possible to get checks from "
                                     "this scheduler.", sched['name'])
                    continue
            logger.debug("get new actions, scheduler: %s", sched['name'])

            try:
                # OK, go for it :)
                tmp = sched['con'].get('get_checks', {
                    'do_checks': do_checks, 'do_actions': do_actions,
                    'poller_tags': self.poller_tags,
                    'reactionner_tags': self.reactionner_tags,
                    'worker_name': self.name,
                    'module_types': self.q_by_mod.keys()
                }, wait='long')
                # Explicit serialization
                tmp = unserialize(tmp, True)
                if tmp:
                    logger.debug("Got %d actions from %s", len(tmp), sched['name'])
                    # We 'tag' them with sched_id and put into queue for workers
                    self.add_actions(tmp, sched_id)
            except HTTPClientConnectionException as exp:
                logger.warning("Connection error with the scheduler '%s' when getting checks",
                               sched['name'])
                sched['con'] = None
            except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
                logger.warning("Connection timeout with the scheduler '%s' "
                               "when getting checks: %s", sched['name'], str(exp))
                sched['con'] = None
            except HTTPClientException as exp:  # pragma: no cover, simple protection
                logger.error("Error with the scheduler '%s' when getting checks: %s",
                             sched['name'], str(exp))
                sched['con'] = None
            # scheduler must not be initialized
            # or scheduler must not have checks
            except AttributeError as exp:  # pragma: no cover, simple protection
                logger.exception('get_new_actions attribute exception:: %s', exp)
            # Bad data received
            except AlignakClassLookupException as exp:  # pragma: no cover, simple protection
                logger.error('Cannot un-serialize actions received: %s', exp)
            # What the F**k? We do not know what happened,
            # log the error message if possible.
            except Exception as exp:  # pragma: no cover, simple protection
                logger.exception("A satellite raised an unknown exception (%s): %s", type(exp), exp)
                raise

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
        # Maybe the arbiter ask us to wait for a new conf
        # If true, we must restart all...
        if self.cur_conf is None:
            # Clean previous run from useless objects and close modules
            self.clean_previous_run()

            self.wait_for_initial_conf()
            # we may have been interrupted or so; then
            # just return from this loop turn
            if not self.new_conf:
                return
            self.setup_new_conf()

        # Now we check if we received a new configuration
        logger.debug("loop pause: %s", self.timeout)

        _t0 = time.time()
        self.watch_for_new_conf(self.timeout)
        statsmgr.timer('core.paused-loop', time.time() - _t0)
        if self.new_conf:
            self.setup_new_conf()

        # Check if zombies workers are among us :)
        # If so: KILL THEM ALL!!!
        self.check_and_del_zombie_workers()

        # And also modules
        self.check_and_del_zombie_modules()

        # Print stats for debug
        for _, sched in self.schedulers.iteritems():
            for mod in self.q_by_mod:
                # In workers we've got actions sent to queue - queue size
                for (worker_id, queue) in self.q_by_mod[mod].items():
                    try:
                        actions_count = queue.qsize()
                        results_count = self.returns_queue.qsize()
                        logger.debug("[%s][%s][%s] actions queued: %d, results queued: %d",
                                     sched['name'], mod, worker_id, actions_count, results_count)
                        # Update the statistics
                        statsmgr.gauge('core.worker-%s.actions-queue-size' % worker_id,
                                       actions_count)
                        statsmgr.gauge('core.worker-%s.results-queue-size' % worker_id,
                                       results_count)
                    except (IOError, EOFError):
                        pass

        # # Before return or get new actions, see how we managed
        # # the former ones: are they still in queue(s)? If so, we
        # # must wait more or at least have more workers
        # wait_ratio = self.wait_ratio.get_load()
        # total_q = 0
        # try:
        #     for mod in self.q_by_mod:
        #         for queue in self.q_by_mod[mod].values():
        #             total_q += queue.qsize()
        # except (IOError, EOFError):
        #     pass
        # if total_q != 0 and wait_ratio < 2 * self.polling_interval:
        #     logger.debug("I decide to increase the wait ratio")
        #     self.wait_ratio.update_load(wait_ratio * 2)
        #     # self.wait_ratio.update_load(self.polling_interval)
        # else:
        #     # Go to self.polling_interval on normal run, if wait_ratio
        #     # was >2*self.polling_interval,
        #     # it make it come near 2 because if < 2, go up :)
        #     self.wait_ratio.update_load(self.polling_interval)
        # wait_ratio = self.wait_ratio.get_load()
        # statsmgr.timer('core.wait-ratio', wait_ratio)
        # if self.log_loop:
        #     logger.debug("[%s] wait ratio: %f", self.name, wait_ratio)

        # # We can wait more than 1s if needed, no more than 5s, but no less than 1s
        # timeout = self.timeout * wait_ratio
        # timeout = max(self.polling_interval, timeout)
        # self.timeout = min(5 * self.polling_interval, timeout)
        # statsmgr.timer('core.pause-loop', self.timeout)

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
                if msg is not None:
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
        except Exception as exp:  # pylint: disable=W0703
            logger.error("Failed getting messages in returns queue: %s", str(exp))

        for _, sched in self.schedulers.iteritems():
            logger.debug("[%s] scheduler home run: %d results",
                         self.name, len(sched['wait_homerun']))

        # If we are passive, we do not initiate the check getting
        # and return
        if not self.passive:
            # We send all finished checks
            self.manage_returns()

            # Now we can get new actions from schedulers
            self.get_new_actions()

        # Get objects from our modules that are not Worker based
        if self.log_loop:
            logger.debug("[%s] get objects from queues", self.name)
        self.get_objects_from_from_queues()
        statsmgr.timer('core.get-objects-from-queues', time.time() - _t0)
        statsmgr.gauge('got.external-commands', len(self.external_commands))
        statsmgr.gauge('got.broks', len(self.broks))

        # Say to modules it's a new tick :)
        self.hook_point('tick')

    def do_post_daemon_init(self):
        """Do this satellite (poller or reactionner) post "daemonize" init

        :return: None
        """
        # self.s = Queue() # Global Master -> Slave
        # We can open the Queue for fork AFTER
        self.q_by_mod['fork'] = {}

        # self.returns_queue = self.sync_manager.Queue()
        self.returns_queue = Queue()

        # # For multiprocess things, we should not have
        # # socket timeouts.
        # import socket
        # socket.setdefaulttimeout(None)

    def setup_new_conf(self):  # pylint: disable=R0915,R0912
        """Setup new conf received from Arbiter

        :return: None
        """
        with self.conf_lock:
            self.clean_previous_run()
            conf = self.new_conf
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

            logger.info("[%s] Received a new configuration, containing:", self.name)
            for key in conf:
                logger.info("[%s] - %s", self.name, key)
            logger.debug("[%s] global configuration part: %s", self.name, conf['global'])

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
                                  statsd_host=self.statsd_host, statsd_port=self.statsd_port,
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
                self.schedulers[sched_id]['con'] = None
                self.schedulers[sched_id]['last_connection'] = 0
                self.schedulers[sched_id]['connection_attempt'] = 0
                self.schedulers[sched_id]['max_failed_connections'] = 3
                #
                # # Do not connect if we are a passive satellite
                # if not self.passive and not old_sched_id:
                #     # And then we connect to it :)
                #     self.pynag_con_init(sched_id)

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
                except NotImplementedError:  # pragma: no cover, simple protection
                    self.max_workers = 4
            self.min_workers = g_conf['min_workers']
            if self.min_workers == 0:
                try:
                    self.min_workers = cpu_count()
                except NotImplementedError:  # pragma: no cover, simple protection
                    self.min_workers = 4
            logger.info("Using minimum %d workers, maximum %d workers",
                        self.min_workers, self.max_workers)

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

            # todo:
            # This function returns False if some problem is detected during initialization
            # (eg. communication port not free)
            # Perharps we should stop the initialization process and exit?
            if not self.do_daemon_init_and_start():
                return

            self.do_post_daemon_init()

            self.load_modules_manager(self.name)

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
            self.adjust_worker_number_by_load()

            # Now main loop
            self.do_mainloop()
        except Exception:
            self.print_unrecoverable(traceback.format_exc())
            raise
