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
#     Guillaume Bour, guillaume@bour.cc
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     David Durieux, d.durieux@siprossii.com
#     Jean Gabes, naparuba@gmail.com
#     Romain Forlot, rforlot@yahoo.com

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

""" This python module contains the class BaseModule
that alignak modules will subclass
"""

import os
import signal
import time
import traceback
import re
from multiprocessing import Queue, Process
import warnings
import logging

from alignak.misc.common import setproctitle

logger = logging.getLogger(__name__)  # pylint: disable=C0103

# The `properties dict defines what the module can do and
# if it's an external module or not.
# pylint: disable=C0103
properties = {
    # name of the module type ; to distinguish between them:
    # retention, logs, configuration, livestate, ...
    'type': None,

    # is the module "external" (external means here a daemon module)?
    'external': True,

    # Possible configuration phases where the module is involved:
    'phases': ['configuration', 'late_configuration', 'running', 'retention'],
}


class BaseModule(object):
    """This is the base class for the Alignak modules.
    Modules can be used by the different Alignak daemons/services
    for different tasks.
    Example of task that a Alignak module can do:

    - load additional configuration objects.
    - recurrently save hosts/services status/perfdata
       information in different format.
    - ...
    """

    def __init__(self, mod_conf):
        """Instantiate a new module.
        There can be many instance of the same type.
        'mod_conf' is the module configuration object for this new module instance.
        """
        self.myconf = mod_conf
        self.alias = mod_conf.get_name()
        # Todo: disabled feature
        # We can have sub modules
        self.modules = getattr(mod_conf, 'modules', [])
        self.props = mod_conf.properties.copy()
        # TODO: choose between 'props' or 'properties'..
        self.interrupted = False
        self.properties = self.props
        self.is_external = self.props.get('external', False)
        # though a module defined with no phase is quite useless .
        self.phases = self.props.get('phases', [])
        self.phases.append(None)
        # the queue the module will receive data to manage
        self.to_q = None
        # the queue the module will put its result data
        self.from_q = None
        self.process = None
        self.illegal_char = re.compile(r'[^\w-]')
        self.init_try = 0
        # We want to know where we are load from? (broker, scheduler, etc)
        self.loaded_into = 'unknown'

    def init(self):  # pylint: disable=R0201
        """Handle this module "post" init ; just before it'll be started.
        Like just open necessaries file(s), database(s),
        or whatever the module will need.

        :return: True / False according to initialization succeeds or not
        :rtype: bool
        """
        return True

    def set_loaded_into(self, daemon_name):
        """Setter for loaded_into attribute
        Used to know what daemon has loaded this module

        :param daemon_name: value to set
        :type daemon_name: str
        :return: None
        """
        self.loaded_into = daemon_name

    def create_queues(self, manager=None):
        """
        Create the shared queues that will be used by alignak daemon
        process and this module process.
        But clear queues if they were already set before recreating new one.

        :param manager: Manager() object
        :type manager: None | object
        :return: None
        """
        # NB: actually this method is only referenced in the alignak tests,
        # but without the manager parameter set..
        # TODO: clarify all that (this manager+queues story) and continue clean-clean-clean
        self.clear_queues(manager)
        # If no Manager() object, go with classic Queue()
        if not manager:
            self.from_q = Queue()
            self.to_q = Queue()
        else:
            self.from_q = manager.Queue()
            self.to_q = manager.Queue()

    def clear_queues(self, manager):
        """Release the resources associated to the queues of this instance

        :param manager: Manager() object
        :type manager: None | object
        :return: None
        """
        for queue in (self.to_q, self.from_q):
            if queue is None:
                continue
            # If we got no manager, we direct call the clean
            if not manager:
                queue.close()
                queue.join_thread()
            # else:
            #    q._callmethod('close')
            #    q._callmethod('join_thread')
        self.to_q = self.from_q = None

    def start_module(self):
        """Wrapper for _main function.
        Catch and raise any exception occurring in the main function

        :return: None
        """
        try:
            self._main()
        except Exception as exp:
            logger.error('[%s] %s', self.alias, traceback.format_exc())
            raise exp

    def start(self, http_daemon=None):  # pylint: disable=W0613
        """Actually restart the process if the module is external
        Try first to stop the process and create a new Process instance
        with target start_module.
        Finally start process.

        :param http_daemon: Not used here but can be used in other modules
        :type http_daemon: None | object
        :return: None
        """

        if not self.is_external:
            return
        self.stop_process()
        logger.info("Starting external process for module %s...", self.alias)
        proc = Process(target=self.start_module, args=())

        # Under windows we should not call start() on an object that got
        # its process as object, so we remove it and we set it in a earlier
        # start
        try:
            del self.properties['process']
        except KeyError:
            pass

        proc.start()
        # We save the process data AFTER the fork()
        self.process = proc
        self.properties['process'] = proc  # TODO: temporary
        logger.info("%s is now started (pid=%d)", self.alias, proc.pid)

    def kill(self):
        """Sometime terminate() is not enough, we must "help"
        external modules to die...

        :return: None
        """

        logger.info("Killing external module (pid=%d) for module %s...",
                    self.process.pid, self.alias)
        if os.name == 'nt':
            self.process.terminate()
        else:
            # Ok, let him 1 second before really KILL IT
            os.kill(self.process.pid, signal.SIGTERM)
            time.sleep(1)
            # You do not let me another choice guy...
            if self.process.is_alive():
                os.kill(self.process.pid, signal.SIGKILL)
            logger.info("External module killed")

    def stop_process(self):
        """Request the module process to stop and release it

        :return: None
        """
        if self.process:
            logger.info("I'm stopping module %r (pid=%d)",
                        self.get_name(), self.process.pid)
            self.process.terminate()
            # Wait for 10 seconds before killing the process abruptly
            self.process.join(timeout=10)
            if self.process.is_alive():
                logger.warning("%r is still alive after normal kill, I help it to die",
                               self.get_name())
                self.kill()
                self.process.join(1)
                if self.process.is_alive():
                    logger.error("%r still alive after brutal kill, I leave it.",
                                 self.get_name())

            self.process = None

    def get_name(self):
        """Wrapper to access name attribute

        :return: module name
        :rtype: str
        """
        return self.alias

    def has(self, prop):
        """The classic has: do we have a prop or not?

        :param prop: property name
        :type prop: str
        :return: True if has a property, otherwise False
        :rtype: bool
        """
        warnings.warn(
            "{s.__class__.__name__} is deprecated, please use "
            "`hasattr(your_object, attr)` instead. This has() method will "
            "be removed in a later version.".format(s=self),
            DeprecationWarning, stacklevel=2)
        return hasattr(self, prop)

    def want_brok(self, b):  # pylint: disable=W0613,R0201
        """Generic function to check if the module need a specific brok
        In this case it is always True

        :param b: brok to check
        :type b: alignak.brok.Brok
        :return: True if the module wants the brok, False otherwise
        :rtype: bool
        """
        return True

    def manage_brok(self, brok):
        """Request the module to manage the given brok.
        There a lot of different possible broks to manage.

        :param brok:
        :type brok:
        :return:
        :rtype:
        """
        manage = getattr(self, 'manage_' + brok.type + '_brok', None)
        if manage:
            # Be sure the brok is prepared before call it
            brok.prepare()
            return manage(brok)

    def manage_signal(self, sig, frame):  # pylint: disable=W0613
        """Generic function to handle signals
        Set interrupted attribute to True and return

        :param sig: signal sent
        :type sig:
        :param frame: frame before catching signal
        :type frame:
        :return: None
        """
        logger.info("process %d received a signal: %s", os.getpid(), str(sig))
        self.interrupted = True

    def set_signal_handler(self, sigs=None):
        """Set the signal handler function (manage_signal)
        for sigs signals or signal.SIGINT and signal.SIGTERM if sigs is None

        :param sigs: signals to handle
        :type sigs:
        :return: None
        """
        if sigs is None:
            sigs = (signal.SIGINT, signal.SIGTERM)

        for sig in sigs:
            signal.signal(sig, self.manage_signal)

    set_exit_handler = set_signal_handler

    def do_stop(self):
        """Called just before the module will exit
        Put in this method all you need to cleanly
        release all open resources used by your module

        :return: None
        """
        pass

    def do_loop_turn(self):
        """For external modules only:
        implement in this method the body of you main loop

        :return: None
        """
        raise NotImplementedError()

    def set_proctitle(self, name):
        """Wrapper for setproctitle method

        :param name: module alias
        :type name: str
        :return: None
        """
        setproctitle("alignak-%s module: %s" % (self.loaded_into, name))

    def main(self):
        """
        Main function of BaseModule

        :return: None
        """
        logger.info("BaseModule.main() not defined in your %s", self.__class__)

    def _main(self):
        """module "main" method. Only used by external modules.

        :return: None
        """
        self.set_proctitle(self.alias)
        self.set_signal_handler()

        logger.info("Process for module %s is now running (pid=%d)", self.alias, os.getpid())

        # Will block here!
        self.main()
        self.do_stop()

        logger.info("Process for module %s is now exiting (pid=%d)", self.alias, os.getpid())

    # TODO: apparently some modules would uses "work" as the main method??
    work = _main
