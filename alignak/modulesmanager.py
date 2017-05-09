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
import traceback
import cStringIO

import importlib


from alignak.basemodule import BaseModule

# Initialization test period
MODULE_INIT_PERIOD = 5

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class ModulesManager(object):
    """This class is used to manage modules and call callback"""

    def __init__(self, daemon_type, sync_manager, max_queue_size=0):
        self.daemon_type = daemon_type
        self.daemon_name = daemon_type
        self.modules_assoc = []
        self.instances = []
        self.to_restart = []
        self.max_queue_size = max_queue_size
        self.sync_manager = sync_manager

        # By default the modules configuration is correct and the
        # warnings and errors lists are empty
        self.configuration_is_correct = True
        self.configuration_warnings = []
        self.configuration_errors = []

        logger.debug("Created a module manager for '%s'", self.daemon_type)

    def set_daemon_name(self, daemon_name):
        """
        Set the daemon name of the daemon which this manager is attached to
        and propagate this daemon name to our managed modules

        :param daemon_name:
        :return:
        """
        self.daemon_name = daemon_name
        for instance in self.instances:
            instance.set_loaded_into(daemon_name)

    def set_modules(self, modules):
        """Setter for modules and allowed_type attributes
        Allowed type attribute is set based on module type in modules arg

        :param modules: value to set to module
        :type modules:
        :return: None
        """
        self.modules = modules

    def set_max_queue_size(self, max_queue_size):
        """Setter for max_queue_size attribute

        :param max_queue_size: value to set
        :type max_queue_size: int
        :return: None
        """
        self.max_queue_size = max_queue_size

    def load_and_init(self, modules):
        """Import, instantiate & "init" the modules we manage

        :param modules: list of the managed modules
        :return: None
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
            logger.info("Importing Python module '%s' for %s...",
                        module.python_name, module.module_alias)
            try:
                python_module = importlib.import_module(module.python_name)

                # Check existing module properties
                # Todo: check all mandatory properties
                if not hasattr(python_module, 'properties'):  # pragma: no cover
                    self.configuration_errors.append(
                        "Module %s is missing a 'properties' dictionary" % module.python_name
                    )
                    raise AttributeError
                logger.info("Module properties: %s", getattr(python_module, 'properties'))

                # Check existing module get_instance method
                if not hasattr(python_module, 'get_instance') or \
                        not callable(getattr(python_module, 'get_instance')):  # pragma: no cover
                    self.configuration_errors.append(
                        "Module %s is missing a 'get_instance' function" % module.python_name
                    )
                    raise AttributeError

                self.modules_assoc.append((module, python_module))
                logger.info("Imported '%s' for %s", module.python_name, module.module_alias)
            except ImportError as exp:  # pragma: no cover, simple protection
                self.configuration_errors.append(
                    "Module %s (%s) can't be loaded, Python importation error: %s" %
                    (module.python_name, module.module_alias, str(exp))
                )
            except AttributeError:  # pragma: no cover, simple protection
                self.configuration_errors.append(
                    "Module %s (%s) can't be loaded, module configuration" %
                    (module.python_name, module.module_alias)
                )
            else:
                logger.info("Loaded Python module '%s' (%s)",
                            module.python_name, module.module_alias)

    def try_instance_init(self, instance, late_start=False):
        """Try to "initialize" the given module instance.

        :param instance: instance to init
        :type instance: object
        :param late_start: If late_start, don't look for last_init_try
        :type late_start: bool
        :return: True on successful init. False if instance init method raised any Exception.
        :rtype: bool
        """
        result = False
        try:
            logger.info("Trying to initialize module: %s", instance.get_name())
            instance.init_try += 1
            # Maybe it's a retry
            if not late_start and instance.init_try > 1:
                # Do not try until too frequently, or it's too loopy
                if instance.last_init_try > time.time() - MODULE_INIT_PERIOD:
                    return False
            instance.last_init_try = time.time()

            # If it's an external module, create/update Queues()
            if instance.is_external:
                instance.create_queues(self.sync_manager)

            # The module instance init function says if initialization is ok
            result = instance.init()
        except Exception as exp:  # pylint: disable=W0703
            # pragma: no cover, simple protection
            self.configuration_errors.append(
                "The module instance %s raised an exception on initialization: %s, I remove it!" %
                (instance.get_name(), str(exp))
            )
            logger.error("The instance %s raised an exception on initialization: %s, I remove it!",
                         instance.get_name(), str(exp))
            output = cStringIO.StringIO()
            traceback.print_exc(file=output)
            logger.error("Traceback of the exception: %s", output.getvalue())
            output.close()
            return False

        return result

    def clear_instances(self, insts=None):
        """Request to "remove" the given instances list or all if not provided

        :param insts: instances to remove (all if None)
        :type insts:
        :return: None
        """
        if insts is None:
            insts = self.instances[:]  # have to make a copy of the list
        for i in insts:
            self.remove_instance(i)

    def set_to_restart(self, inst):
        """Put an instance to the restart queue

        :param inst: instance to restart
        :type inst: object
        :return: None
        """
        self.to_restart.append(inst)

    def get_instances(self):
        """Create, init and then returns the list of module instances that the caller needs.
        If an instance can't be created or init'ed then only log is done.
        That instance is skipped. The previous modules instance(s), if any, are all cleaned.

        Arbiter call this method with start_external=False

        :return: module instances list
        :rtype: list
        """
        self.clear_instances()

        for (mod_conf, module) in self.modules_assoc:
            mod_conf.properties = module.properties.copy()
            try:
                instance = module.get_instance(mod_conf)
                if not isinstance(instance, BaseModule):  # pragma: no cover, simple protection
                    self.configuration_errors.append(
                        "Module %s instance is not a BaseModule instance: %s" %
                        (module.module_alias, type(instance))
                    )

                if instance.modules and len(instance.modules) > 0:
                    self.configuration_warnings.append(
                        "Module %s instance defines some sub-modules. "
                        "This feature is not currently supported" % (module.module_alias)
                    )
                    raise AttributeError
            except Exception as exp:  # pylint: disable=W0703
                # pragma: no cover, simple protection
                logger.error("The module %s raised an exception on loading, I remove it!",
                             mod_conf.get_name())
                logger.exception("Exception: %s", exp)
                self.configuration_errors.append(
                    "The module %s raised an exception on loading: %s, I remove it!" %
                    (mod_conf.get_name(), str(exp))
                )
            else:
                # Give the module the data to which daemon/module it is loaded into
                instance.set_loaded_into(self.daemon_name)
                self.instances.append(instance)

        for instance in self.instances:
            # External instances are not initialized now, but only when they are started
            if not instance.is_external and not self.try_instance_init(instance):
                # If the init failed, we put in in the restart queue
                logger.warning("The module '%s' failed to initialize, "
                               "I will try to restart it later", instance.get_name())
                self.to_restart.append(instance)

        return self.instances

    def start_external_instances(self, late_start=False):
        """Launch external instances that are load correctly

        :param late_start: If late_start, don't look for last_init_try
        :type late_start: bool
        :return: None
        """
        for inst in [inst for inst in self.instances if inst.is_external]:
            # But maybe the init failed a bit, so bypass this ones from now
            if not self.try_instance_init(inst, late_start=late_start):
                logger.warning("The module '%s' failed to init, I will try to restart it later",
                               inst.get_name())
                self.to_restart.append(inst)
                continue

            # ok, init succeed
            logger.info("Starting external module %s", inst.get_name())
            inst.start()

    def remove_instance(self, inst):
        """Request to cleanly remove the given instance.
        If instance is external also shutdown it cleanly

        :param inst: instance to remove
        :type inst: object
        :return: None
        """
        # External instances need to be close before (process + queues)
        if inst.is_external:
            logger.info("Request external process to stop for %s", inst.get_name())
            inst.stop_process()
            logger.info("External process stopped.")

        inst.clear_queues(self.sync_manager)

        # Then do not listen anymore about it
        self.instances.remove(inst)

    def check_alive_instances(self):
        """Check alive instances.
        If not, log error and try to restart it

        :return: None
        """
        # Only for external
        for inst in self.instances:
            if inst not in self.to_restart:
                if inst.is_external and inst.process is not None and not inst.process.is_alive():
                    logger.error("The external module %s died unexpectedly!", inst.get_name())
                    logger.info("Setting the module %s to restart", inst.get_name())
                    # We clean its queues, they are no more useful
                    inst.clear_queues(self.sync_manager)
                    self.to_restart.append(inst)
                    # Ok, no need to look at queue size now
                    continue

                # Now look for man queue size. If above value, the module should got a huge problem
                # and so bailout. It's not a perfect solution, more a watchdog
                # If max_queue_size is 0, don't check this
                if self.max_queue_size == 0:
                    continue
                # Ok, go launch the dog!
                queue_size = 0
                try:
                    queue_size = inst.to_q.qsize()
                except Exception:  # pylint: disable=W0703
                    pass
                if queue_size > self.max_queue_size:
                    logger.error("The external module %s got a too high brok queue size (%s > %s)!",
                                 inst.get_name(), queue_size, self.max_queue_size)
                    logger.info("Setting the module %s to restart", inst.get_name())
                    # We clean its queues, they are no more useful
                    inst.clear_queues(self.sync_manager)
                    self.to_restart.append(inst)

    def try_to_restart_deads(self):
        """Try to reinit and restart dead instances

        :return: None
        """
        to_restart = self.to_restart[:]
        del self.to_restart[:]
        for inst in to_restart:
            logger.debug("I should try to reinit %s", inst.get_name())

            if self.try_instance_init(inst):
                logger.debug("Good, I try to restart %s", inst.get_name())
                # If it's an external, it will start it
                inst.start()
                # Ok it's good now :)
            else:
                self.to_restart.append(inst)

    def get_internal_instances(self, phase=None):
        """Get a list of internal instances (in a specific phase)

        If phase is None, return all internal instances whtever the phase

        :param phase: phase to filter (never used)
        :type phase:
        :return: internal instances list
        :rtype: list
        """
        if phase is None:
            return [inst for inst in self.instances if not inst.is_external]

        return [inst
                for inst in self.instances
                if not inst.is_external and phase in inst.phases and
                inst not in self.to_restart]

    def get_external_instances(self, phase=None):
        """Get a list of external instances (in a specific phase)

        If phase is None, return all external instances whtever the phase

        :param phase: phase to filter (never used)
        :type phase:
        :return: external instances list
        :rtype: list
        """
        if phase is None:
            return [inst for inst in self.instances if inst.is_external]

        return [inst
                for inst in self.instances
                if inst.is_external and phase in inst.phases and
                inst not in self.to_restart]

    def get_external_to_queues(self):
        """Get a list of queue to external instances

        :return: queue list
        :rtype: list
        """
        return [inst.to_q
                for inst in self.instances
                if inst.is_external and inst not in self.to_restart]

    def get_external_from_queues(self):
        """Get a list of queue from external instances

        :return: queue list
        :rtype: list
        """
        return [inst.from_q
                for inst in self.instances
                if inst.is_external and inst not in self.to_restart]

    def stop_all(self):
        """Stop all module instances

        :return: None
        """
        # Ask internal to quit if they can
        for inst in self.get_internal_instances():
            if hasattr(inst, 'quit') and callable(inst.quit):
                inst.quit()

        self.clear_instances([inst for inst in self.instances if inst.is_external])
