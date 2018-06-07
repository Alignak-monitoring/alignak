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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Guillaume Bour, guillaume@bour.cc
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de

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
This module provide Worker class. It is used to spawn new processes in Poller and Reactionner
"""
import os
import time
import signal
import logging

from queue import Empty, Full
from multiprocessing import Process
from six import string_types

from alignak.action import ACT_STATUS_QUEUED, ACT_STATUS_LAUNCHED, \
    ACT_STATUS_DONE, ACT_STATUS_TIMEOUT
from alignak.message import Message
from alignak.misc.common import setproctitle, SIGNALS_TO_NAMES_DICT


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Worker(object):
    """This class is used for poller and reactionner to work.
    The worker is a process launch by theses process and read Message in a Queue
    (self.actions_queue)
    They launch the Check and then send the result in the Queue self.m (master)
    they can die if they do not do anything (param timeout)

    """
    # Auto generated identifiers
    _worker_ids = {}

    uuid = ''  # None
    _process = None
    _idletime = None
    _timeout = None

    # pylint: disable=too-many-arguments
    def __init__(self, module_name, actions_queue, returns_queue, processes_by_worker,
                 timeout=300, max_plugins_output_length=8192, target=None,
                 loaded_into='unknown'):
        """

        :param module_name:
        :param actions_queue:
        :param returns_queue:
        :param processes_by_worker: number of processes by worker
        :type processes_by_worker: int
        :param timeout:
        :type timeout: int
        :param max_plugins_output_length: max output lenght
        :type max_plugins_output_length: int
        :param target:
        :param loaded_into:
        """
        # Set our own identifier
        cls = self.__class__
        self.module_name = module_name
        if module_name not in cls._worker_ids:
            cls._worker_ids[module_name] = 1
        self._id = '%s_%d' % (module_name, cls._worker_ids[module_name])
        cls._worker_ids[module_name] += 1

        # Update the logger with the worker identifier
        global logger  # pylint: disable=invalid-name, global-statement
        logger = logging.getLogger(__name__ + '.' + self._id)  # pylint: disable=invalid-name

        self.actions_got = 0
        self.actions_launched = 0
        self.actions_finished = 0

        self.interrupted = False

        self._idletime = 0
        self._timeout = timeout
        self.processes_by_worker = processes_by_worker
        # By default, take our own code
        if target is None:
            target = self.work
        self._process = Process(target=self._prework,
                                args=(target, actions_queue, returns_queue))
        logger.debug("[%s] created a new process", self.get_id())
        # self.returns_queue = returns_queue
        self.max_plugins_output_length = max_plugins_output_length
        self.i_am_dying = False
        # Keep a trace where the worker is launched from (poller or reactionner?)
        self.loaded_into = loaded_into

    @staticmethod
    def _prework(real_work, *args):
        """Do the job...
        :param real_work: function to execute
        :param args: arguments
        :return:
        """
        real_work(*args)

    def get_module(self):
        """Accessor to get the worker module name

        :return: the worker module name
        :rtype: str
        """
        return self.module_name

    def get_id(self):
        """Accessor to get the worker identifier

        :return: the worker auto-generated identifier
        :rtype: str
        """
        return self._id

    def get_pid(self):
        """Accessor to get the worker process PID

        :return: the worker PID
        :rtype: int
        """
        return self._process.pid

    def start(self):
        """Start the worker. Wrapper for calling start method of the process attribute

        :return: None
        """
        self._process.start()

    def manage_signal(self, sig, frame):  # pylint: disable=unused-argument
        """Manage signals caught by the process but I do not do anything...
        our master daemon is managing our termination.

        :param sig: signal caught by daemon
        :type sig: str
        :param frame: current stack frame
        :type frame:
        :return: None
        """
        logger.info("worker '%s' (pid=%d) received a signal: %s",
                    self.get_id(), os.getpid(), SIGNALS_TO_NAMES_DICT[sig])
        # Do not do anything... our master daemon is managing our termination.
        self.interrupted = True

    def set_exit_handler(self):
        """Set the signal handler to manage_signal (defined in this class)
        Only set handlers for signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGUSR2

        :return: None
        """
        signal.signal(signal.SIGINT, self.manage_signal)
        signal.signal(signal.SIGTERM, self.manage_signal)
        signal.signal(signal.SIGHUP, self.manage_signal)
        signal.signal(signal.SIGQUIT, self.manage_signal)

    def terminate(self):
        """Wrapper for calling terminate method of the process attribute
        Also close queues (input and output) and terminate queues thread

        :return: None
        """
        # We can just terminate process, not threads
        self._process.terminate()
        # Is we are with a Manager() way
        # there should be not such functions
        # todo: what is this???
        # if hasattr(self.actions_queue, 'close'):
        #     self.actions_queue.close()
        #     self.actions_queue.join_thread()

    def join(self, timeout=None):
        """Wrapper for calling join method of the process attribute

        :param timeout: time to wait for the process to terminate
        :type timeout: int
        :return: None
        """
        self._process.join(timeout)

    def is_alive(self):
        """Wrapper for calling is_alive method of the process attribute

        :return: A boolean indicating if the process is alive
        :rtype: bool
        """
        return self._process.is_alive()

    def get_new_checks(self, queue, return_queue):
        """Get new checks if less than nb_checks_max
        If no new checks got and no check in queue, sleep for 1 sec
        REF: doc/alignak-action-queues.png (3)

        :return: None
        """
        try:
            logger.debug("get_new_checks: %s / %s", len(self.checks), self.processes_by_worker)
            while len(self.checks) < self.processes_by_worker:
                msg = queue.get_nowait()
                if msg is not None:
                    logger.debug("Got a message: %s", msg)
                    if msg.get_type() == 'Do':
                        logger.debug("Got an action: %s", msg.get_data())
                        self.checks.append(msg.get_data())
                        self.actions_got += 1
                    elif msg.get_type() == 'ping':
                        msg = Message(_type='pong', data='pong!', source=self._id)
                        logger.debug("Queuing message: %s", msg)
                        return_queue.put_nowait(msg)
                        logger.debug("Queued")
                    else:
                        logger.warning("Ignoring message of type: %s", msg.get_type())
        except Full:
            logger.warning("Actions queue is full")
        except Empty:
            logger.debug("Actions queue is empty")
            if not self.checks:
                self._idletime += 1
                time.sleep(0.5)
        # Maybe the Queue() has been deleted by our master ?
        except (IOError, EOFError) as exp:
            logger.warning("My actions queue is no more available: %s", str(exp))
            self.interrupted = True
        except Exception as exp:  # pylint: disable=broad-except
            logger.error("Failed getting messages in actions queue: %s", str(exp))

        logger.debug("get_new_checks exit")

    def launch_new_checks(self):
        """Launch checks that are in status
        REF: doc/alignak-action-queues.png (4)

        :return: None
        """
        # queue
        for chk in self.checks:
            if chk.status not in [ACT_STATUS_QUEUED]:
                continue
            logger.debug("Launch check: %s", chk.uuid)
            self._idletime = 0
            self.actions_launched += 1
            process = chk.execute()
            # Maybe we got a true big problem in the action launching
            if process == 'toomanyopenfiles':
                # We should die as soon as we return all checks
                logger.error("I am dying because of too many open files: %s", chk)
                self.i_am_dying = True
            else:
                if not isinstance(process, string_types):
                    logger.debug("Launched check: %s, pid=%d", chk.uuid, process.pid)

    def manage_finished_checks(self, queue):
        """Check the status of checks
        if done, return message finished :)
        REF: doc/alignak-action-queues.png (5)

        :return: None
        """
        to_del = []
        wait_time = 1.0
        now = time.time()
        logger.debug("--- manage finished checks")
        for action in self.checks:
            logger.debug("--- checking: last poll: %s, now: %s, wait_time: %s, action: %s",
                         action.last_poll, now, action.wait_time, action)
            if action.status == ACT_STATUS_LAUNCHED and action.last_poll < now - action.wait_time:
                action.check_finished(self.max_plugins_output_length)
                wait_time = min(wait_time, action.wait_time)
            # If action done, we can launch a new one
            if action.status in [ACT_STATUS_DONE, ACT_STATUS_TIMEOUT]:
                logger.debug("--- check done/timeout: %s", action.uuid)
                self.actions_finished += 1
                to_del.append(action)
                # We answer to the master
                try:
                    msg = Message(_type='Done', data=action, source=self._id)
                    logger.debug("Queuing message: %s", msg)
                    queue.put_nowait(msg)
                    logger.debug("Queued")
                except (IOError, EOFError) as exp:
                    logger.warning("My returns queue is no more available: %s", str(exp))
                    # sys.exit(2)
                except Exception as exp:  # pylint: disable=broad-except
                    logger.error("Failed putting messages in returns queue: %s", str(exp))
            else:
                logger.debug("--- not yet finished")

        for chk in to_del:
            logger.debug("--- delete check: %s", chk.uuid)
            self.checks.remove(chk)

        # Little sleep
        logger.debug("--- manage finished checks terminated, I will wait: %s", wait_time)
        time.sleep(wait_time)

    def check_for_system_time_change(self):  # pragma: no cover, hardly testable with unit tests...
        """Check if our system time change. If so, change our

        :return: 0 if the difference < 900, difference else
        :rtype: int
        """
        now = time.time()
        difference = now - self.t_each_loop

        # Now set the new value for the tick loop
        self.t_each_loop = now

        # If we have more than 15 min time change, we need to compensate it
        # todo: confirm that 15 minutes is a good choice...
        if abs(difference) > 900:  # pragma: no cover, not with unit tests...
            return difference

        return 0

    def work(self, actions_queue, returns_queue):  # pragma: no cover, not unit tests
        """Wrapper function for do_work in order to catch the exception
        to see the real work, look at do_work

        :param actions_queue: Global Queue Master->Slave
        :type actions_queue: Queue.Queue
        :param returns_queue: queue managed by manager
        :type returns_queue: Queue.Queue
        :return: None
        """
        try:
            logger.info("[%s] (pid=%d) starting my job...", self.get_id(), os.getpid())
            self.do_work(actions_queue, returns_queue)
            logger.info("[%s] (pid=%d) stopped", self.get_id(), os.getpid())
        # Catch any exception, log the exception and exit anyway
        except Exception as exp:  # pragma: no cover, this should never happen indeed ;)
            logger.error("[%s] exited with an unmanaged exception : %s", self._id, str(exp))
            logger.exception(exp)
            raise

    def do_work(self, actions_queue, returns_queue):  # pragma: no cover, unit tests
        """Main function of the worker.
        * Get checks
        * Launch new checks
        * Manage finished checks

        :param actions_queue: Global Queue Master->Slave
        :type actions_queue: Queue.Queue
        :param returns_queue: queue managed by manager
        :type returns_queue: Queue.Queue
        :return: None
        """
        # restore default signal handler for the workers:
        # signal.signal(signal.SIGTERM, signal.SIG_DFL)
        self.interrupted = False
        self.set_exit_handler()

        self.set_proctitle()

        timeout = 1.0
        self.checks = []
        self.t_each_loop = time.time()
        while True:
            begin = time.time()
            logger.debug("--- loop start: %s", begin)

            # If we are dying (big problem!) we do not
            # take new jobs, we just finished the current one
            if not self.i_am_dying:
                # REF: doc/alignak-action-queues.png (3)
                self.get_new_checks(actions_queue, returns_queue)
                # REF: doc/alignak-action-queues.png (4)
                self.launch_new_checks()
            # REF: doc/alignak-action-queues.png (5)
            self.manage_finished_checks(returns_queue)

            logger.debug("loop middle, %d checks", len(self.checks))

            # Maybe someone asked us to die, if so, do it :)
            if self.interrupted:
                logger.info("I die because someone asked ;)")
                break

            # Look if we are dying, and if we finish all current checks
            # if so, we really die, our master poller will launch a new
            # worker because we were too weak to manage our job :(
            if not self.checks and self.i_am_dying:
                logger.warning("I die because I cannot do my job as I should "
                               "(too many open files?)... forgive me please.")
                break

            # Manage a possible time change (our avant will be change with the diff)
            diff = self.check_for_system_time_change()
            begin += diff
            logger.debug("loop check timechange: %s", diff)

            timeout -= time.time() - begin
            if timeout < 0:
                timeout = 1.0

            logger.debug("idle: %ss, checks: %d, actions (got: %d, launched: %d, finished: %d)",
                         self._idletime, len(self.checks),
                         self.actions_got, self.actions_launched, self.actions_finished)

            logger.debug("+++ loop stop: timeout = %s", timeout)

    def set_proctitle(self):  # pragma: no cover, not with unit tests
        """Set the proctitle of this worker for readability purpose

        :return: None
        """
        setproctitle("alignak-%s worker %s" % (self.loaded_into, self._id))
