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
#     Frédéric Vachon, fredvac@gmail.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
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
"""This module provides ModulesManager class. Used to load modules in Alignak

"""
import logging
import time

import importlib
import collections

from alignak.basemodule import BaseModule

# Initialization test period (5 seconds)
MODULE_INIT_PERIOD = 5

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class ModulesManager(object):
    """This class is used to manage modules and call callback"""

    def __init__(self, daemon):
        """

        :param daemon: the daemon for which modules manager is created
        :type daemon: alignak.Daemon
        """
        self.daemon = daemon
        self.daemon_type = daemon.type
        self.daemon_name = daemon.name
        self.modules = {}
        self.modules_assoc = []
        self.instances = []
        self.to_restart = []

        # By default the modules configuration is correct and the
        # warnings and errors lists are empty
        self.configuration_is_correct = True
        self.configuration_warnings = []
        self.configuration_errors = []

        logger.debug("Created a module manager for '%s'", self.daemon_name)

    def set_daemon_name(self, daemon_name):
        """Set the daemon name of the daemon which this manager is attached to
        and propagate this daemon name to our managed modules

        :param daemon_name:
        :return:
        """
        self.daemon_name = daemon_name
        for instance in self.instances:
            instance.set_loaded_into(daemon_name)

    def load_and_init(self, modules):
        """Import, instantiate & "init" the modules we manage

        :param modules: list of the managed modules
        :return: True if no errors
        """
        self.load(modules)
        self.get_instances()

        return len(self.configuration_errors) == 0

    def load(self, modules):
        """Load Python modules and check their usability

        :param modules: list of the modules that must be loaded
        :return:
        """
        self.modules_assoc = []
        for module in modules:
            if not module.enabled:
                logger.info("Module %s is declared but not enabled", module.name)
                # Store in our modules list but do not try to load
                # Probably someone else will load this module later...
                self.modules[module.uuid] = module
                continue
            logger.info("Importing Python module '%s' for %s...", module.python_name, module.name)
            try:
                python_module = importlib.import_module(module.python_name)

                # Check existing module properties
                # Todo: check all mandatory properties
                if not hasattr(python_module, 'properties'):  # pragma: no cover
                    self.configuration_errors.append("Module %s is missing a 'properties' "
                                                     "dictionary" % module.python_name)
                    raise AttributeError
                logger.info("Module properties: %s", getattr(python_module, 'properties'))

                # Check existing module get_instance method
                if not hasattr(python_module, 'get_instance') or \
                        not isinstance(getattr(python_module, 'get_instance'),
                                       collections.Callable):  # pragma: no cover
                    self.configuration_errors.append("Module %s is missing a 'get_instance' "
                                                     "function" % module.python_name)
                    raise AttributeError

                self.modules_assoc.append((module, python_module))
                logger.info("Imported '%s' for %s", module.python_name, module.name)
            except ImportError as exp:  # pragma: no cover, simple protection
                self.configuration_errors.append("Module %s (%s) can't be loaded, Python "
                                                 "importation error: %s" % (module.python_name,
                                                                            module.name,
                                                                            str(exp)))
            except AttributeError:  # pragma: no cover, simple protection
                self.configuration_errors.append("Module %s (%s) can't be loaded, "
                                                 "module configuration" % (module.python_name,
                                                                           module.name))
            else:
                logger.info("Loaded Python module '%s' (%s)", module.python_name, module.name)

    def try_instance_init(self, instance, late_start=False):
        """Try to "initialize" the given module instance.

        :param instance: instance to init
        :type instance: object
        :param late_start: If late_start, don't look for last_init_try
        :type late_start: bool
        :return: True on successful init. False if instance init method raised any Exception.
        :rtype: bool
        """
        try:
            instance.init_try += 1
            # Maybe it's a retry
            if not late_start and instance.init_try > 1:
                # Do not try until too frequently, or it's too loopy
                if instance.last_init_try > time.time() - MODULE_INIT_PERIOD:
                    logger.info("Too early to retry initialization, retry period is %d seconds",
                                MODULE_INIT_PERIOD)
                    # logger.info("%s / %s", instance.last_init_try, time.time())
                    return False
            instance.last_init_try = time.time()

            logger.info("Trying to initialize module: %s", instance.name)

            # If it's an external module, create/update Queues()
            if instance.is_external:
                instance.create_queues(self.daemon.sync_manager)

            # The module instance init function says if initialization is ok
            if not instance.init():
                logger.warning("Module %s initialisation failed.", instance.name)
                return False
        except Exception as exp:  # pylint: disable=broad-except
            # pragma: no cover, simple protection
            msg = "The module instance %s raised an exception " \
                  "on initialization: %s, I remove it!" % (instance.name, str(exp))
            self.configuration_errors.append(msg)
            logger.error(msg)
            logger.exception(exp)
            return False

        return True

    def clear_instances(self, instances=None):
        """Request to "remove" the given instances list or all if not provided

        :param instances: instances to remove (all instances are removed if None)
        :type instances:
        :return: None
        """
        if instances is None:
            instances = self.instances[:]  # have to make a copy of the list
        for instance in instances:
            self.remove_instance(instance)

    def set_to_restart(self, instance):
        """Put an instance to the restart queue

        :param instance: instance to restart
        :type instance: object
        :return: None
        """
        self.to_restart.append(instance)
        if instance.is_external:
            instance.proc = None

    def get_instances(self):
        """Create, init and then returns the list of module instances that the caller needs.

        This method is called once the Python modules are loaded to initialize the modules.

        If an instance can't be created or initialized then only log is doneand that
        instance is skipped. The previous modules instance(s), if any, are all cleaned.

        :return: module instances list
        :rtype: list
        """
        self.clear_instances()

        for (alignak_module, python_module) in self.modules_assoc:
            alignak_module.properties = python_module.properties.copy()
            alignak_module.my_daemon = self.daemon
            logger.info("Alignak starting module '%s'", alignak_module.get_name())
            if getattr(alignak_module, 'modules', None):
                modules = []
                for module_uuid in alignak_module.modules:
                    if module_uuid in self.modules:
                        modules.append(self.modules[module_uuid])
                alignak_module.modules = modules
            logger.debug("Module '%s', parameters: %s",
                         alignak_module.get_name(), alignak_module.__dict__)
            try:
                instance = python_module.get_instance(alignak_module)
                if not isinstance(instance, BaseModule):  # pragma: no cover, simple protection
                    self.configuration_errors.append("Module %s instance is not a "
                                                     "BaseModule instance: %s"
                                                     % (alignak_module.get_name(),
                                                        type(instance)))
                    raise AttributeError
            # pragma: no cover, simple protection
            except Exception as exp:  # pylint: disable=broad-except
                logger.error("The module %s raised an exception on loading, I remove it!",
                             alignak_module.get_name())
                logger.exception("Exception: %s", exp)
                self.configuration_errors.append("The module %s raised an exception on "
                                                 "loading: %s, I remove it!"
                                                 % (alignak_module.get_name(), str(exp)))
            else:
                # Give the module the data to which daemon/module it is loaded into
                instance.set_loaded_into(self.daemon.name)
                self.instances.append(instance)

        for instance in self.instances:
            # External instances are not initialized now, but only when they are started
            if not instance.is_external and not self.try_instance_init(instance):
                # If the init failed, we put in in the restart queue
                logger.warning("The module '%s' failed to initialize, "
                               "I will try to restart it later", instance.name)
                self.set_to_restart(instance)

        return self.instances

    def start_external_instances(self, late_start=False):
        """Launch external instances that are load correctly

        :param late_start: If late_start, don't look for last_init_try
        :type late_start: bool
        :return: None
        """
        for instance in [i for i in self.instances if i.is_external]:
            # But maybe the init failed a bit, so bypass this ones from now
            if not self.try_instance_init(instance, late_start=late_start):
                logger.warning("The module '%s' failed to init, I will try to restart it later",
                               instance.name)
                self.set_to_restart(instance)
                continue

            # ok, init succeed
            logger.info("Starting external module %s", instance.name)
            instance.start()

    def remove_instance(self, instance):
        """Request to cleanly remove the given instance.
        If instance is external also shutdown it cleanly

        :param instance: instance to remove
        :type instance: object
        :return: None
        """
        # External instances need to be close before (process + queues)
        if instance.is_external:
            logger.info("Request external process to stop for %s", instance.name)
            instance.stop_process()
            logger.info("External process stopped.")

        instance.clear_queues(self.daemon.sync_manager)

        # Then do not listen anymore about it
        self.instances.remove(instance)

    def check_alive_instances(self):
        """Check alive instances.
        If not, log error and try to restart it

        :return: None
        """
        # Only for external
        for instance in self.instances:
            if instance in self.to_restart:
                continue

            if instance.is_external and instance.process and not instance.process.is_alive():
                logger.error("The external module %s died unexpectedly!", instance.name)
                logger.info("Setting the module %s to restart", instance.name)
                # We clean its queues, they are no more useful
                instance.clear_queues(self.daemon.sync_manager)
                self.set_to_restart(instance)
                # Ok, no need to look at queue size now
                continue

            # Now look for maximum queue size. If above the defined value, the module may have
            # a huge problem and so bailout. It's not a perfect solution, more a watchdog
            # If max_queue_size is 0, don't check this
            if self.daemon.max_queue_size == 0:
                continue

            # Check for module queue size
            queue_size = 0
            try:
                queue_size = instance.to_q.qsize()
            except Exception:  # pylint: disable=broad-except
                pass
            if queue_size > self.daemon.max_queue_size:
                logger.error("The module %s has a too important queue size (%s > %s max)!",
                             instance.name, queue_size, self.daemon.max_queue_size)
                logger.info("Setting the module %s to restart", instance.name)
                # We clean its queues, they are no more useful
                instance.clear_queues(self.daemon.sync_manager)
                self.set_to_restart(instance)

    def try_to_restart_deads(self):
        """Try to reinit and restart dead instances

        :return: None
        """
        to_restart = self.to_restart[:]
        del self.to_restart[:]

        for instance in to_restart:
            logger.warning("Trying to restart module: %s", instance.name)

            if self.try_instance_init(instance):
                logger.warning("Restarting %s...", instance.name)
                # Because it is a restart, clean the module inner process reference
                instance.process = None
                # If it's an external module, it will start the process
                instance.start()
                # Ok it's good now :)
            else:
                # Will retry later...
                self.to_restart.append(instance)

    def get_internal_instances(self, phase=None):
        """Get a list of internal instances (in a specific phase)

        If phase is None, return all internal instances whtever the phase

        :param phase: phase to filter (never used)
        :type phase:
        :return: internal instances list
        :rtype: list
        """
        if phase is None:
            return [instance for instance in self.instances if not instance.is_external]

        return [instance for instance in self.instances
                if not instance.is_external and phase in instance.phases and
                instance not in self.to_restart]

    def get_external_instances(self, phase=None):
        """Get a list of external instances (in a specific phase)

        If phase is None, return all external instances whtever the phase

        :param phase: phase to filter (never used)
        :type phase:
        :return: external instances list
        :rtype: list
        """
        if phase is None:
            return [instance for instance in self.instances if instance.is_external]

        return [instance for instance in self.instances
                if instance.is_external and phase in instance.phases and
                instance not in self.to_restart]

    def stop_all(self):
        """Stop all module instances

        :return: None
        """
        logger.info('Shutting down modules...')
        # Ask internal to quit if they can
        for instance in self.get_internal_instances():
            if hasattr(instance, 'quit') and isinstance(instance.quit, collections.Callable):
                instance.quit()

        self.clear_instances([instance for instance in self.instances if instance.is_external])
