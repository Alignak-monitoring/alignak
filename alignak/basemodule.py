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
import traceback
import re
from multiprocessing import Queue, Process
import logging

from alignak.misc.common import setproctitle, SIGNALS_TO_NAMES_DICT

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

KILL_TIME = 10

# The `properties` dict defines what the module can do and
# if it's an external module or not.
# pylint: disable=invalid-name
properties = {
    # module type ; to distinguish between them:
    # retention, logs, configuration, livestate, ...
    'type': None,

    # is the module "external" (external means here a daemon module)?
    'external': True,

    # Possible configuration phases where the module is involved:
    'phases': ['configuration', 'late_configuration', 'running', 'retention'],
}


class BaseModule(object):
    # pylint: disable=too-many-instance-attributes
    """This is the base class for the Alignak modules.
    Modules can be used by the different Alignak daemons for different tasks.
    Example of task that an Alignak module can do:
    - load additional configuration objects.
    - recurrently save hosts/services status/perfdata information in different format.
    - ...
    """

    def __init__(self, mod_conf):
        """Instantiate a new module.

        There can be many instance of the same module.

        mod_conf is a dictionary that contains:
        - all the variables declared in the module configuration file
        - a 'properties' value that is the module properties as defined globally in this file
        - a 'my_daemon' property that is a reference to the Daemon object that loaded the module

        :param mod_conf: module configuration file as a dictionary
        :type mod_conf: dict
        """
        self.myconf = mod_conf
        self.name = mod_conf.get_name()
        self.my_daemon = getattr(mod_conf, 'my_daemon', None)

        self.props = mod_conf.properties.copy()
        # TODO: choose between 'props' or 'properties'..
        self.interrupted = False
        self.properties = self.props
        self.is_external = self.props.get('external', False)

        # though a module defined with no phase is quite useless .
        self.phases = self.props.get('phases', [])

        # the queue the module will receive data to manage
        self.to_q = None
        # the queue the module will put its result data
        self.from_q = None
        self.process = None
        self.illegal_char = re.compile(r'[^\w-]')
        # Initialization try count and time
        self.init_try = 0
        self.last_init_try = 0
        # We want to know where we are load from? (broker, scheduler, etc)
        self.loaded_into = 'unknown'

        # External module force kill delay - default is to wait for
        # 60 seconds before killing a module abruptly
        self.kill_delay = int(getattr(mod_conf, 'kill_delay', '60'))

        # Self module monitoring (cpu, memory)
        self.module_monitoring = False
        self.module_monitoring_period = 10
        if 'ALIGNAK_DAEMON_MONITORING' in os.environ:
            self.module_monitoring = True
            try:
                self.system_health_period = int(os.environ.get('ALIGNAK_DAEMON_MONITORING', '10'))
            except ValueError:  # pragma: no cover, simple protection
                pass
        if self.module_monitoring:
            print("Module self monitoring is enabled, reporting every %d loop count."
                  % self.module_monitoring_period)

    @property
    def alias(self):
        """Module name may be stored in an alias property
        Stay compatible with older modules interface
        """
        return self.name

    def get_name(self):
        """Wrapper to access name attribute

        :return: module name
        :rtype: str
        """
        return self.name

    def init(self):  # pylint: disable=no-self-use
        """Handle this module "post" init ; just before it'll be started.

        This function initializes the module instance. If False is returned, the modules manager
        will periodically retry an to initialize the module.
        If an exception is raised, the module will be definitely considered as dead :/

        This function must be present and return True for Alignak to consider the module as loaded
        and fully functional.

        :return: True / False according to initialization succeeded or not
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

        Note:
        If manager is None, then we are running the unit tests for the modules and
        we must create some queues for the external modules without a SyncManager

        :param manager: Manager() object
        :type manager: None | object
        :return: None
        """
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
            # If we got no manager, we directly call the clean
            if not manager:
                try:
                    queue.close()
                    queue.join_thread()
                except AttributeError:
                    pass
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
            logger.exception('%s', traceback.format_exc())
            raise Exception(exp)

    def start(self, http_daemon=None):  # pylint: disable=unused-argument
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

        if self.process:
            self.stop_process()
        logger.info("Starting external process for module %s...", self.name)
        proc = Process(target=self.start_module, args=(), group=None)

        # Under windows we should not call start() on an object that got its process
        # as an object, so we remove it and we set it in a earlier start
        try:
            del self.properties['process']
        except KeyError:
            pass

        proc.start()
        # We save the process data AFTER the fork()
        self.process = proc
        self.properties['process'] = proc
        logger.info("%s is now started (pid=%d)", self.name, proc.pid)

    def kill(self):
        """Sometime terminate() is not enough, we must "help"
        external modules to die...

        :return: None
        """

        logger.info("Killing external module (pid=%d) for module %s...",
                    self.process.pid, self.name)
        if os.name == 'nt':
            self.process.terminate()
        else:
            self.process.terminate()
            # Wait for 10 seconds before killing the process abruptly
            self.process.join(timeout=KILL_TIME)
            # You do not let me another choice guy...
            if self.process.is_alive():
                logger.warning("%s is still living %d seconds after a normal kill, "
                               "I help it to die", self.name, KILL_TIME)
                os.kill(self.process.pid, signal.SIGKILL)
                self.process.join(1)
                if self.process.is_alive():
                    logger.error("%s still living after brutal kill, I leave it.", self.name)
            logger.info("External module killed")

    def stop_process(self):
        """Request the module process to stop and release it

        :return: None
        """
        if not self.process:
            return

        logger.info("I'm stopping module %r (pid=%d)", self.name, self.process.pid)
        self.kill()
        # Clean inner process reference
        self.process = None

    def want_brok(self, b):  # pylint: disable=unused-argument,no-self-use
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
        There are a lot of different possible broks to manage. The list is defined
        in the Brok class.

        An internal module may redefine this function or, easier, define only the function
        for the brok it is interested with. Hence a module interested in the `service_check_result`
        broks will only need to define a function named as `manage_service_check_result_brok`

        :param brok:
        :type brok:
        :return:
        :rtype:
        """

        manage = getattr(self, 'manage_' + brok.type + '_brok', None)
        if not manage:
            return False

        # Be sure the brok is prepared before calling the function
        brok.prepare()
        return manage(brok)

    def manage_signal(self, sig, frame):  # pylint: disable=unused-argument
        """Generic function to handle signals

        Only called when the module process received SIGINT or SIGKILL.

        Set interrupted attribute to True, self.process to None and returns

        :param sig: signal sent
        :type sig:
        :param frame: frame before catching signal
        :type frame:
        :return: None
        """
        logger.info("received a signal: %s", SIGNALS_TO_NAMES_DICT[sig])

        if sig == signal.SIGHUP:
            # if SIGHUP, reload configuration in arbiter
            logger.info("Modules are not able to reload their configuration. "
                        "Stopping the module...")

        logger.info("Request to stop the module")
        self.interrupted = True
        # self.process = None

    def set_signal_handler(self, sigs=None):
        """Set the signal handler to manage_signal (defined in this class)

        Only set handlers for:
        - signal.SIGTERM, signal.SIGINT
        - signal.SIGUSR1, signal.SIGUSR2
        - signal.SIGHUP

        :return: None
        """
        if sigs is None:
            sigs = (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGUSR2, signal.SIGHUP)

        func = self.manage_signal
        if os.name == "nt":  # pragma: no cover, no Windows implementation currently
            try:
                import win32api
                win32api.SetConsoleCtrlHandler(func, True)
            except ImportError:
                version = ".".join([str(i) for i in os.sys.version_info[:2]])
                raise Exception("pywin32 not installed for Python " + version)
        else:
            for sig in sigs:
                signal.signal(sig, func)

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
        self.set_proctitle(self.name)
        self.set_signal_handler()

        logger.info("process for module %s is now running (pid=%d)", self.name, os.getpid())

        # Will block here!
        try:
            self.main()
        except (IOError, EOFError):
            pass
            # logger.warning('[%s] EOF exception: %s', self.name, traceback.format_exc())
        except Exception as exp:  # pylint: disable=broad-except
            logger.exception('main function exception: %s', exp)

        self.do_stop()

        logger.info("process for module %s is now exiting (pid=%d)", self.name, os.getpid())
        exit()

    # TODO: apparently some modules would uses "work" as the main method??
    work = _main
