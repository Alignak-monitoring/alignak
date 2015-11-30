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

import time
import traceback
import cStringIO

import importlib


from alignak.basemodule import BaseModule
from alignak.log import logger


class ModulesManager(object):
    """This class is use to manage modules and call callback"""

    def __init__(self, modules_type, manager, max_queue_size=0):
        self.modules_type = modules_type
        self.modules_assoc = []
        self.instances = []
        self.to_restart = []
        self.max_queue_size = max_queue_size
        self.manager = manager

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

    def load_and_init(self, mod_confs):
        """Import, instanciate & "init" the modules we have been requested

        :return: None
        """
        self.load(mod_confs)
        self.get_instances()

    @staticmethod
    def find_module_properties_and_get_instance(module, mod_name):
        """
        Get properties and get_instance of a module

        :param module: module object
        :type module: object
        :param mod_name: Name of the module
        :type mod_name: str
        :return: None
        """
        try:
            module.properties
            module.get_instance
        except AttributeError:
            pass
        else:
            # good module style
            return
        submod = importlib.import_module('.module', mod_name)
        # old style:
        module.properties = submod.properties
        module.get_instance = submod.get_instance

    def load(self, mod_confs):
        """
        Try to import the requested modules ; put the imported modules in self.imported_modules.
        """
        # Now we want to find in theses modules the ones we are looking for
        del self.modules_assoc[:]
        for mod_conf in mod_confs:
            try:
                module = importlib.import_module(mod_conf.python_name)
                self.find_module_properties_and_get_instance(module, mod_conf.python_name)
                self.modules_assoc.append((mod_conf, module))
            except ImportError:
                logger.warning("Module %s (%s) can't be loaded, not found", mod_conf.python_name,
                               mod_conf.module_alias)
            except AttributeError:
                logger.warning("Module %s (%s) can't be loaded because attributes errors",
                               mod_conf.python_name, mod_conf.module_alias)

    def try_instance_init(self, inst, late_start=False):
        """Try to "init" the given module instance.

        :param inst: instance to init
        :type inst: object
        :param late_start: If late_start, don't look for last_init_try
        :type late_start: bool
        :return: True on successful init. False if instance init method raised any Exception.
        :rtype: bool
        """
        try:
            logger.info("Trying to init module: %s", inst.get_name())
            inst.init_try += 1
            # Maybe it's a retry
            if not late_start and inst.init_try > 1:
                # Do not try until 5 sec, or it's too loopy
                if inst.last_init_try > time.time() - 5:
                    return False
            inst.last_init_try = time.time()

            # If it's an external, create/update Queues()
            if inst.is_external:
                inst.create_queues(self.manager)

            inst.init()
        except Exception, err:
            logger.error("The instance %s raised an exception %s, I remove it!",
                         inst.get_name(), str(err))
            output = cStringIO.StringIO()
            traceback.print_exc(file=output)
            logger.error("Back trace of this remove: %s", output.getvalue())
            output.close()
            return False
        return True

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
                inst = module.get_instance(mod_conf)
                if not isinstance(inst, BaseModule):
                    raise TypeError('Returned instance is not of type BaseModule (%s) !'
                                    % type(inst))
            except Exception as err:
                logger.error("The module %s raised an exception %s, I remove it! traceback=%s",
                             mod_conf.get_name(), err, traceback.format_exc())
            else:
                # Give the module the data to which module it is load from
                inst.set_loaded_into(self.modules_type)
                self.instances.append(inst)

        for inst in self.instances:
            # External are not init now, but only when they are started
            if not inst.is_external and not self.try_instance_init(inst):
                # If the init failed, we put in in the restart queue
                logger.warning("The module '%s' failed to init, I will try to restart it later",
                               inst.get_name())
                self.to_restart.append(inst)

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
            logger.debug("Ask stop process for %s", inst.get_name())
            inst.stop_process()
            logger.debug("Stop process done")

        inst.clear_queues(self.manager)

        # Then do not listen anymore about it
        self.instances.remove(inst)

    def check_alive_instances(self):
        """Check alive isntances.
        If not, log error and  try to restart it

        :return: None
        """
        # Only for external
        for inst in self.instances:
            if inst not in self.to_restart:
                if inst.is_external and not inst.process.is_alive():
                    logger.error("The external module %s goes down unexpectedly!", inst.get_name())
                    logger.info("Setting the module %s to restart", inst.get_name())
                    # We clean its queues, they are no more useful
                    inst.clear_queues(self.manager)
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
                except Exception, exp:
                    pass
                if queue_size > self.max_queue_size:
                    logger.error("The external module %s got a too high brok queue size (%s > %s)!",
                                 inst.get_name(), queue_size, self.max_queue_size)
                    logger.info("Setting the module %s to restart", inst.get_name())
                    # We clean its queues, they are no more useful
                    inst.clear_queues(self.manager)
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

        :param phase: phase to filter (never used)
        :type phase:
        :return: internal instances list
        :rtype: list
        """
        return [inst
                for inst in self.instances
                if not inst.is_external and phase in inst.phases
                and inst not in self.to_restart]

    def get_external_instances(self, phase=None):
        """Get a list of external instances (in a specific phase)

        :param phase: phase to filter (never used)
        :type phase:
        :return: external instances list
        :rtype: list
        """
        return [inst
                for inst in self.instances
                if inst.is_external and phase in inst.phases
                and inst not in self.to_restart]

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
