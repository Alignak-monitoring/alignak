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
from Queue import Empty
from multiprocessing import Process, Queue

import os
import time
import sys
import signal
import traceback
import uuid
import cStringIO
import logging

from alignak.misc.common import setproctitle

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Worker(object):
    """This class is used for poller and reactionner to work.
    The worker is a process launch by theses process and read Message in a Queue
    (self.s) (slave)
    They launch the Check and then send the result in the Queue self.m (master)
    they can die if they do not do anything (param timeout)

    """

    uuid = ''  # None
    _process = None
    _mortal = None
    _idletime = None
    _timeout = None
    _control_q = None

    def __init__(self, _id, slave_q, returns_queue, processes_by_worker,  # pylint: disable=W0613
                 mortal=True, timeout=300, max_plugins_output_length=8192, target=None,
                 loaded_into='unknown', http_daemon=None):
        self.uuid = uuid.uuid4().hex

        self.interrupted = False

        self._mortal = mortal
        self._idletime = 0
        self._timeout = timeout
        self.slave_q = None
        self.processes_by_worker = processes_by_worker
        self._control_q = Queue()  # Private Control queue for the Worker
        # By default, take our own code
        if target is None:
            target = self.work
        self._process = Process(target=self._prework,
                                args=(target, slave_q, returns_queue, self._control_q))
        self.returns_queue = returns_queue
        self.max_plugins_output_length = max_plugins_output_length
        self.i_am_dying = False
        # Keep a trace where the worker is launched from (poller or reactionner?)
        self.loaded_into = loaded_into
        if os.name != 'nt':
            self.http_daemon = http_daemon
        else:  # windows forker do not like serialize http/lock
            self.http_daemon = None

    @staticmethod
    def _prework(real_work, *args):
        """
        Do the job...
        :param real_work: function to execute
        :param args: arguments
        :return:
        """
        real_work(*args)

    def is_mortal(self):
        """
        Accessor to _mortal attribute

        :return: A boolean indicating if the worker is mortal or not.
        :rtype: bool
        """
        return self._mortal

    def start(self):
        """
        Start the worker. Wrapper for calling start method of the process attribute

        :return: None
        """
        self._process.start()

    def terminate(self):
        """
        Wrapper for calling terminate method of the process attribute
        Also close queues (input and output) and terminate queues thread

        :return: None
        """
        # We can just terminate process, not threads
        self._process.terminate()
        # Is we are with a Manager() way
        # there should be not such functions
        if hasattr(self._control_q, 'close'):
            self._control_q.close()
            self._control_q.join_thread()
        if hasattr(self.slave_q, 'close'):
            self.slave_q.close()
            self.slave_q.join_thread()

    def join(self, timeout=None):
        """
         Wrapper for calling join method of the process attribute

        :param timeout: time to wait for the process to terminate
        :type timeout: int
        :return: None
        """
        self._process.join(timeout)

    def is_alive(self):
        """
        Wrapper for calling is_alive method of the process attribute

        :return: A boolean indicating if the process is alive
        :rtype: bool
        """
        return self._process.is_alive()

    def is_killable(self):
        """
        Determine whether a process is killable :

        * process is mortal
        * idletime > timeout

        :return: a boolean indicating if it is killable
        :rtype: bool
        """
        return self._mortal and self._idletime > self._timeout

    def add_idletime(self, amount):
        """
        Increment idletime

        :param amount: time to increment in seconds
        :type amount: int
        :return: None
        """
        self._idletime += amount

    def reset_idle(self):
        """
        Reset idletime (set to 0)

        :return: None
        """
        self._idletime = 0

    def send_message(self, msg):
        """
        Wrapper for calling put method of the _control_q attribute

        :param msg: the message to put in queue
        :type msg: str
        :return: None
        """
        self._control_q.put(msg)

    def set_zombie(self):
        """
        Set the process as zombie (mortal to False)

        :return:None
        """
        self._mortal = False

    def get_new_checks(self):
        """
        Get new checks if less than nb_checks_max
        If no new checks got and no check in queue, sleep for 1 sec
        REF: doc/alignak-action-queues.png (3)

        :return: None
        """
        try:
            while len(self.checks) < self.processes_by_worker:
                msg = self.slave_q.get(block=False)
                if msg is not None:
                    self.checks.append(msg.get_data())
        except Empty:
            if len(self.checks) == 0:
                self._idletime += 1
                time.sleep(1)
        # Maybe the Queue() has been deleted by our master ?
        except EOFError:  # pragma: no cover, hardly testable with unit tests...
            logger.warning("[%s] My queue is no more available", self.uuid)
            self.interrupted = True
            return
        # Maybe the Queue() is not available, if so, just return
        # get back to work :)
        except IOError:  # pragma: no cover, hardly testable with unit tests...
            logger.warning("[%s] My queue is not available", self.uuid)
            return

    def launch_new_checks(self):
        """
        Launch checks that are in status
        REF: doc/alignak-action-queues.png (4)

        :return: None
        """
        # queue
        for chk in self.checks:
            if chk.status == 'queue':
                self._idletime = 0
                res = chk.execute()
                # Maybe we got a true big problem in the action launching
                if res == 'toomanyopenfiles':
                    # We should die as soon as we return all checks
                    logger.error("[%s] I am dying because of too many open files %s ... ",
                                 self.uuid, chk)
                    self.i_am_dying = True

    def manage_finished_checks(self):
        """
        Check the status of checks
        if done, return message finished :)
        REF: doc/alignak-action-queues.png (5)

        :return: None
        """
        to_del = []
        wait_time = 1
        now = time.time()
        for action in self.checks:
            if action.status == 'launched' and action.last_poll < now - action.wait_time:
                action.check_finished(self.max_plugins_output_length)
                wait_time = min(wait_time, action.wait_time)
                # If action done, we can launch a new one
            if action.status in ('done', 'timeout'):
                to_del.append(action)
                # We answer to the master
                # msg = Message(_id=self.uuid, _type='Result', data=action)
                try:
                    self.returns_queue.put(action)
                except IOError, exp:  # pragma: no cover, hardly testable with unit tests...
                    logger.error("[%s] Exiting: %s", self.uuid, exp)
                    sys.exit(2)

        # Little sleep
        self.wait_time = wait_time

        for chk in to_del:
            self.checks.remove(chk)

        # Little sleep
        time.sleep(wait_time)

    def check_for_system_time_change(self):  # pragma: no cover, hardly testable with unit tests...
        """
        Check if our system time change. If so, change our

        :return: 0 if the difference < 900, difference else
        :rtype: int
        """
        now = time.time()
        difference = now - self.t_each_loop

        # Now set the new value for the tick loop
        self.t_each_loop = now

        # return the diff if it need, of just 0
        if abs(difference) > 900:
            return difference
        else:
            return 0

    def work(self, slave_q, returns_queue, control_q):  # pragma: no cover, not with unit tests
        """
        Wrapper function for work in order to catch the exception
        to see the real work, look at do_work

        :param slave_q: Global Queue Master->Slave
        :type slave_q: Queue.Queue
        :param returns_queue: queue managed by manager
        :type returns_queue: Queue.Queue
        :param control_q: Control Queue for the worker
        :type control_q: Queue.Queue
        :return: None
        """
        try:
            self.do_work(slave_q, returns_queue, control_q)
        # Catch any exception, try to print it and exit anyway
        except Exception:
            output = cStringIO.StringIO()
            traceback.print_exc(file=output)
            logger.error("[%s] exit with an unmanaged exception : %s",
                         self.uuid, output.getvalue())
            output.close()
            # Ok I die now
            raise

    def do_work(self, slave_q, returns_queue, control_q):  # pragma: no cover, not with unit tests
        """
        Main function of the worker.
        * Get checks
        * Launch new checks
        * Manage finished checks

        :param slave_q: Global Queue Master->Slave
        :type slave_q: Queue.Queue
        :param returns_queue: queue managed by manager
        :type returns_queue: Queue.Queue
        :param control_q: Control Queue for the worker
        :type control_q: Queue.Queue
        :return: None
        """
        # restore default signal handler for the workers:
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

        self.set_proctitle()

        timeout = 1.0
        self.checks = []
        self.returns_queue = returns_queue
        self.slave_q = slave_q
        self.t_each_loop = time.time()
        while True:
            begin = time.time()

            # If we are dying (big problem!) we do not
            # take new jobs, we just finished the current one
            if not self.i_am_dying:
                # REF: doc/alignak-action-queues.png (3)
                self.get_new_checks()
                # REF: doc/alignak-action-queues.png (4)
                self.launch_new_checks()
            # REF: doc/alignak-action-queues.png (5)
            self.manage_finished_checks()

            # Now get order from master
            # Todo: does our master reaaly send this kind of message? Not found it anywhere!
            try:
                cmsg = control_q.get(block=False)
                if cmsg.get_type() == 'Die':
                    logger.warning("[%s] Dad say we are dying...", self.uuid)
                    break
            except Exception:  # pylint: disable=W0703
                pass

            # Maybe we ask us to die, if so, do it :)
            if self.interrupted:
                logger.warning("[%s] I die because someone asked ;)", self.uuid)
                break

            # Look if we are dying, and if we finish all current checks
            # if so, we really die, our master poller will launch a new
            # worker because we were too weak to manage our job :(
            if len(self.checks) == 0 and self.i_am_dying:
                logger.warning("[%s] I die because I cannot do my job as I should "
                               "(too many open files?)... forgive me please.", self.uuid)
                break

            # Manage a possible time change (our avant will be change with the diff)
            diff = self.check_for_system_time_change()
            begin += diff

            timeout -= time.time() - begin
            if timeout < 0:
                timeout = 1.0

    def set_proctitle(self):  # pragma: no cover, not with unit tests
        """
        Set the proctitle of this worker for readability purpose

        :return: None
        """
        setproctitle("alignak-%s worker" % self.loaded_into)
