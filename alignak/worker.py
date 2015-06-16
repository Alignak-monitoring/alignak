#!/usr/bin/env python
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

# In android, we should use threads, not process
is_android = True
try:
    import android
except ImportError:
    is_android = False

if not is_android:
    from multiprocessing import Process, Queue
else:
    from Queue import Queue
    from threading import Thread as Process

import os
import time
import sys
import signal
import traceback
import cStringIO


from alignak.log import logger
from alignak.misc.common import setproctitle

class Worker:
    """This class is used for poller and reactionner to work.
    The worker is a process launch by theses process and read Message in a Queue
    (self.s) (slave)
    They launch the Check and then send the result in the Queue self.m (master)
    they can die if they do not do anything (param timeout)

    """

    id = 0  # None
    _process = None
    _mortal = None
    _idletime = None
    _timeout = None
    _c = None

    def __init__(self, id, s, returns_queue, processes_by_worker, mortal=True, timeout=300,
                 max_plugins_output_length=8192, target=None, loaded_into='unknown',
                 http_daemon=None):
        self.id = self.__class__.id
        self.__class__.id += 1

        self._mortal = mortal
        self._idletime = 0
        self._timeout = timeout
        self.s = None
        self.processes_by_worker = processes_by_worker
        self._c = Queue()  # Private Control queue for the Worker
        # By default, take our own code
        if target is None:
            target = self.work
        self._process = Process(target=target, args=(s, returns_queue, self._c))
        self.returns_queue = returns_queue
        self.max_plugins_output_length = max_plugins_output_length
        self.i_am_dying = False
        # Keep a trace where the worker is launch from (poller or reactionner?)
        self.loaded_into = loaded_into
        if os.name != 'nt':
            self.http_daemon = http_daemon
        else:  # windows forker do not like pickle http/lock
            self.http_daemon = None

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
        if not is_android:
            self._process.terminate()
        # Is we are with a Manager() way
        # there should be not such functions
        if hasattr(self._c, 'close'):
            self._c.close()
            self._c.join_thread()
        if hasattr(self.s, 'close'):
            self.s.close()
            self.s.join_thread()

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

    def add_idletime(self, time):
        """
        Increment idletime

        :param time: time to increment in seconds
        :type time: int
        :return: None
        """
        self._idletime = self._idletime + time

    def reset_idle(self):
        """
        Reset idletime (set to 0)

        :return: None
        """
        self._idletime = 0

    def send_message(self, msg):
        """
        Wrapper for calling put method of the _c attribute

        :param msg: the message to put in queue
        :return: None
        """
        self._c.put(msg)

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
            while(len(self.checks) < self.processes_by_worker):
                # print "I", self.id, "wait for a message"
                msg = self.s.get(block=False)
                if msg is not None:
                    self.checks.append(msg.get_data())
                # print "I", self.id, "I've got a message!"
        except Empty, exp:
            if len(self.checks) == 0:
                self._idletime = self._idletime + 1
                time.sleep(1)
        # Maybe the Queue() is not available, if so, just return
        # get back to work :)
        except IOError, exp:
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
                r = chk.execute()
                # Maybe we got a true big problem in the
                # action launching
                if r == 'toomanyopenfiles':
                    # We should die as soon as we return all checks
                    logger.error("[%d] I am dying Too many open files %s ... ", self.id, chk)
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
                # msg = Message(id=self.id, type='Result', data=action)
                try:
                    self.returns_queue.put(action)
                except IOError, exp:
                    logger.error("[%d] Exiting: %s", self.id, exp)
                    sys.exit(2)

        # Little sleep
        self.wait_time = wait_time

        for chk in to_del:
            self.checks.remove(chk)

        # Little sleep
        time.sleep(wait_time)

    def check_for_system_time_change(self):
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


    def work(self, s, returns_queue, c):
        """
        Wrapper function for work in order to catch the exception
        to see the real work, look at do_work

        :param s: Global Queue Master->Slave
        :type s: Queue.Queue
        :param returns_queue: queue managed by manager
        :type returns_queue: Queue.Queue
        :param c: Control Queue for the worker
        :type c: Queue.Queue
        :return: None
        """
        try:
            self.do_work(s, returns_queue, c)
        # Catch any exception, try to print it and exit anyway
        except Exception, exp:
            output = cStringIO.StringIO()
            traceback.print_exc(file=output)
            logger.error("Worker '%d' exit with an unmanaged exception : %s",
                         self.id, output.getvalue())
            output.close()
            # Ok I die now
            raise


    def do_work(self, s, returns_queue, c):
        """
        Main function of the worker.
        * Get checks
        * Launch new checks
        * Manage finished checks

        :param s: Global Queue Master->Slave
        :type s: Queue.Queue
        :param returns_queue: queue managed by manager
        :type returns_queue: Queue.Queue
        :param c: Control Queue for the worker
        :type c: Queue.Queue
        :return: None
        """
        # restore default signal handler for the workers:
        # but on android, we are a thread, so don't do it
        if not is_android:
            signal.signal(signal.SIGTERM, signal.SIG_DFL)

        self.set_proctitle()

        print "I STOP THE http_daemon", self.http_daemon
        if self.http_daemon:
            self.http_daemon.close_sockets()

        timeout = 1.0
        self.checks = []
        self.returns_queue = returns_queue
        self.s = s
        self.t_each_loop = time.time()
        while True:
            begin = time.time()
            msg = None
            cmsg = None

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
            try:
                cmsg = c.get(block=False)
                if cmsg.get_type() == 'Die':
                    logger.debug("[%d] Dad say we are dying...", self.id)
                    break
            except Exception:
                pass

            # Look if we are dying, and if we finish all current checks
            # if so, we really die, our master poller will launch a new
            # worker because we were too weak to manage our job :(
            if len(self.checks) == 0 and self.i_am_dying:
                logger.warning("[%d] I DIE because I cannot do my job as I should"
                               "(too many open files?)... forgot me please.", self.id)
                break

            # Manage a possible time change (our avant will be change with the diff)
            diff = self.check_for_system_time_change()
            begin += diff

            timeout -= time.time() - begin
            if timeout < 0:
                timeout = 1.0

    def set_proctitle(self):
        """
        Set the proctitle of this worker for readability purpose

        :return: None
        """
        setproctitle("alignak-%s worker" % self.loaded_into)
