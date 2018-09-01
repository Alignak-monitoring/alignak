#!/usr/bin/env python
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
#     aviau, alexandre.viau@savoirfairelinux.com
#     Grégory Starck, g.starck@gmail.com
#     Alexander Springer, alex.spri@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
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
Test Alignak modules manager
"""

import re
import time
import logging
from alignak.log import ALIGNAK_LOGGER_NAME
from .alignak_test import AlignakTest, CollectorHandler
from alignak.modulesmanager import ModulesManager, MODULE_INIT_PERIOD
from alignak.objects.module import Module
import pytest


class TestModules(AlignakTest):
    """
    This class contains the tests for the modules
    """
    def setUp(self):
        super(TestModules, self).setUp()
        self.set_unit_tests_logger_level('INFO')

    def test_module_loading(self):
        """ Test arbiter, broker, ... detecting configured modules

        :return:
        """
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')
        assert self.conf_is_correct
        self.show_configuration_logs()
        self.show_logs()

        # arbiter modules
        modules = [m.module_alias for m in self._arbiter.link_to_myself.modules]
        assert modules == ['Example']
        modules = [m.name for m in self._arbiter.link_to_myself.modules]
        assert modules == ['Example']

        # broker modules
        modules = [m.module_alias for m in self._broker_daemon.modules]
        assert modules == ['Example']
        modules = [m.name for m in self._broker_daemon.modules]
        assert modules == ['Example']

        # # The only existing poller module is Example declared in the configuration
        # modules = [m.module_alias for m in self.pollers['poller-master'].modules]
        # assert modules == ['Example']
        #
        # # The only existing receiver module is Example declared in the configuration
        # modules = [m.module_alias for m in self.receivers['receiver-master'].modules]
        # assert modules == ['Example']
        #
        # # The only existing reactionner module is Example declared in the configuration
        # modules = [m.module_alias for m in self.reactionners['reactionner-master'].modules]
        # assert modules == ['Example']

        # No scheduler modules created
        modules = [m.module_alias for m in self._scheduler_daemon.modules]
        assert modules == ['Example']
        modules = [m.name for m in self._scheduler_daemon.modules]
        assert modules == ['Example']

        self.show_logs()

        # Loading module logs
        self.assert_any_log_match(re.escape(
            u"Importing Python module 'alignak_module_example' for Example..."
        ))
        self.assert_any_log_match(re.escape(
            u"Imported 'alignak_module_example' for Example"
        ))
        self.assert_any_log_match(re.escape(
            u"Give an instance of alignak_module_example for alias: Example"
        ))
        self.assert_any_log_match(re.escape(
            u"I correctly loaded my modules: [Example]"
        ))

    def test_arbiter_configuration_module(self):
        """ Test arbiter configuration loading

        :return:
        """
        self.setup_with_file('./cfg/modules/arbiter_modules.cfg')
        assert self.conf_is_correct
        self.show_configuration_logs()
        self.show_logs()

        # The arbiter module is 'backend_arbiter' declared in the configuration
        modules = [m.module_alias for m in self._arbiter.link_to_myself.modules]
        assert modules == ['Example']

    def test_module_on_module(self):
        """ No module configuration for modules

        Check that the feature is detected as disabled
        :return:
        """
        self.setup_with_file('cfg/modules/alignak_module_with_submodules.cfg')
        assert self.conf_is_correct
        self.show_configuration_logs()

        # arbiter modules
        modules = [m.module_alias for m in self._arbiter.link_to_myself.modules]
        assert modules == ['Example']
        modules = [m.name for m in self._arbiter.link_to_myself.modules]
        assert modules == ['Example']

        # broker modules
        modules = [m.module_alias for m in self._broker_daemon.modules]
        assert modules == ['Example']
        modules = [m.name for m in self._broker_daemon.modules]
        assert modules == ['Example']

        # # The only existing poller module is Example declared in the configuration
        # modules = [m.module_alias for m in self.pollers['poller-master'].modules]
        # assert modules == ['Example']
        #
        # # The only existing receiver module is Example declared in the configuration
        # modules = [m.module_alias for m in self.receivers['receiver-master'].modules]
        # assert modules == ['Example']
        #
        # # The only existing reactionner module is Example declared in the configuration
        # modules = [m.module_alias for m in self.reactionners['reactionner-master'].modules]
        # assert modules == ['Example']

        # No scheduler modules created
        modules = [m.module_alias for m in self._scheduler_daemon.modules]
        assert modules == ['Example', 'inner-retention']
        modules = [m.name for m in self._scheduler_daemon.modules]
        assert modules == ['Example', 'inner-retention']

    def test_modulemanager_1(self):
        """ Module manager manages its modules - old form

        Test if the module manager manages correctly all the modules
        :return:
        """
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')
        assert self.conf_is_correct

        # Create an Alignak module
        mod = Module({
            'module_alias': 'mod-example',
            'module_types': 'example',
            'python_name': 'alignak_module_example'
        })
        self.run_modulemanager(mod)

    def test_modulemanager_2(self):
        """ Module manager manages its modules - new form

        Test if the module manager manages correctly all the modules
        :return:
        """
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')
        assert self.conf_is_correct

        # Create an Alignak module
        mod = Module({
            'name': 'mod-example',
            'type': 'example',
            'python_name': 'alignak_module_example'
        })
        self.run_modulemanager(mod)

    def run_modulemanager(self, mod):
        # Force the daemon SyncManager to None for unit tests!
        self._broker_daemon.sync_manager = None

        # Create the modules manager for a daemon type
        self.modules_manager = ModulesManager(self._broker_daemon)

        # Load an initialize the modules:
        #  - load python module
        #  - get module properties and instances
        self.modules_manager.load_and_init([mod])

        # Loading module logs
        self.assert_any_log_match(re.escape(
            "Importing Python module 'alignak_module_example' for mod-example..."
        ))
        self.assert_any_log_match(re.escape(
            "Imported 'alignak_module_example' for mod-example"
        ))
        self.assert_any_log_match(re.escape(
            "Give an instance of alignak_module_example for alias: mod-example"
        ))

        self.clear_logs()

        my_module = self.modules_manager.instances[0]
        assert my_module.is_external

        # Get list of not external modules
        assert [] == self.modules_manager.get_internal_instances()
        for phase in ['configuration', 'late_configuration', 'running', 'retention']:
            assert [] == self.modules_manager.get_internal_instances(phase)

        # Get list of external modules
        assert [my_module] == self.modules_manager.get_external_instances()
        for phase in ['configuration', 'late_configuration', 'running', 'retention']:
            assert [my_module] == self.modules_manager.get_external_instances(phase)

        # Start external modules
        self.modules_manager.start_external_instances()

        self.show_logs()

        # Starting external module logs
        idx = 0
        self.assert_log_match(re.escape(
            "Trying to initialize module: mod-example"
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "Test - Example in init"
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "Initialization of the example module"
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "Starting external module mod-example"
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "Starting external process for module mod-example"
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "mod-example is now started (pid="
        ), idx)
        idx += 1
        self.assert_log_count(6)

        # Check alive
        assert my_module.process is not None
        assert my_module.process.is_alive()

        self.clear_logs()
        # Check the alive module instances...
        self.modules_manager.check_alive_instances()
        # Try to restart the dead modules, if any
        self.modules_manager.try_to_restart_deads()
        self.assert_log_count(0)

        # Kill the external module (normal stop is .stop_process)
        self.clear_logs()
        my_module.kill()
        idx = 0
        self.assert_log_match(re.escape(
            "Killing external module "
        ), idx)
        idx += 1
        self.show_logs()

        # self.assert_log_match(re.escape(
        #     "mod-example is still living "
        # ), idx)
        # idx += 1
        # Specific case because sometimes the module is not killed within the expected 10s time
        normal_kill = True
        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for handler in logger_.handlers:
            if not isinstance(handler, CollectorHandler):
                continue
            regex = re.compile('mod-example is still living')

            log_num = 0
            found = False
            for log in handler.collector:
                if idx == log_num:
                    if regex.search(log):
                        idx += 1
                        normal_kill = False
                        break
                log_num += 1
            break

        self.assert_log_match(re.escape(
            "External module killed"
        ), idx)
        idx += 1
        self.assert_log_count(idx)

        # The module is dead (not normally stopped...) so this module inner
        # process reference is not None!
        assert my_module.process is not None

        # Check the alive module instances...
        self.clear_logs()
        idx = 0
        self.modules_manager.check_alive_instances()
        self.show_logs()
        self.assert_log_match(re.escape(
            "The external module mod-example died unexpectedly!"
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "Setting the module mod-example to restart"
        ), idx)
        self.assert_log_count(2)
        idx += 1

        if normal_kill:
            # Try to restart the dead modules, if any
            # Indeed, it's too early, so it won't do it
            self.clear_logs()
            idx = 0
            print("try init: %d" % my_module.init_try)
            self.modules_manager.try_to_restart_deads()
            self.show_logs()

            self.assert_log_match(re.escape(
                "Trying to restart module: mod-example"
            ), idx)
            idx += 1
            self.assert_log_match(re.escape(
                "Too early to retry initialization, retry period is %d seconds" % MODULE_INIT_PERIOD
            ), idx)
            idx += 1
            self.assert_log_count(2)

            # Here the module instance is still dead
            assert not my_module.process.is_alive()

            # Wait for a minimum delay
            time.sleep(MODULE_INIT_PERIOD + 1)

        # my_module.last_init_try = -5
        self.clear_logs()
        self.modules_manager.check_alive_instances()
        self.show_logs()
        self.assert_log_count(0)

        # Try to restart the dead modules, if any
        # Now it is time...
        self.clear_logs()
        idx = 0
        self.modules_manager.try_to_restart_deads()
        self.show_logs()
        self.assert_log_match(re.escape(
            "Trying to restart module: mod-example"
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "Trying to initialize module: mod-example"
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "Test - Example in init"
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "Initialization of the example module"
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "Restarting mod-example..."
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "Starting external process for module mod-example"
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "mod-example is now started (pid="
        ), idx)
        idx += 1
        self.assert_log_count(7)

        # Here the module instance should be alive again
        assert my_module.process.is_alive()

        # No more module to restart...
        assert [] == self.modules_manager.to_restart

        # And we clear all now
        self.clear_logs()
        idx = 0
        self.modules_manager.stop_all()
        self.show_logs()
        self.assert_log_match(re.escape(
            "Shutting down modules..."
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "Request external process to stop for mod-example"
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "I'm stopping module 'mod-example'"
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "Killing external module "
        ), idx)
        idx += 1

        # Specific case because sometimes the module is not killed within the expected 10s time
        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for handler in logger_.handlers:
            if not isinstance(handler, CollectorHandler):
                continue
            regex = re.compile('mod-example is still living')

            log_num = 0
            found = False
            for log in handler.collector:
                if idx == log_num:
                    if regex.search(log):
                        idx += 1
                        break
                log_num += 1
            break

        self.assert_log_match(re.escape(
            "External module killed"
        ), idx)
        idx += 1
        self.assert_log_match(re.escape(
            "External process stopped."
        ), idx)
        idx += 1
        # self.assert_log_count(6)

    def test_modulemanager_several_modules(self):
        """ Module manager manages its modules

        Test if the module manager manages correctly all the modules

        Configured with several modules
        :return:
        """
        self.setup_with_file('cfg/cfg_default_with_modules.cfg',
                             'cfg/default_with_modules/alignak.ini')
        assert self.conf_is_correct

        # for mod in self._arbiter.conf.modules:
        #     print (mod.__dict__)

        # Create an Alignak module
        mod = Module({
            'module_alias': 'mod-example',
            'module_types': 'example',
            'python_name': 'alignak_module_example',
            'option1': 'foo',
            'option2': 'bar',
            'option3': 1
        })
        mod2 = Module({
            'module_alias': 'mod-example-2',
            'module_types': 'example',
            'python_name': 'alignak_module_example',
            'option1': 'faa',
            'option2': 'bor',
            'option3': 1
        })

        # Force the daemon SyncManager to None for unit tests!
        self._broker_daemon.sync_manager = None
        # Create the modules manager for a daemon type
        self.modules_manager = ModulesManager(self._broker_daemon)
        print("Modules: %s" % self._broker_daemon.modules)

        # Load an initialize the modules:
        #  - load python module
        #  - get module properties and instances
        assert self.modules_manager.load_and_init([mod, mod2])
        print("I correctly loaded my modules: [%s]" % ','.join([inst.name for inst in
                                                                self.modules_manager.instances]))
        self.show_logs()

        self.assert_any_log_match(re.escape(
            "Importing Python module 'alignak_module_example' for mod-example..."
        ))
        self.assert_any_log_match(re.escape(
            "Imported 'alignak_module_example' for mod-example"
        ))
        self.assert_any_log_match(re.escape(
            "Loaded Python module 'alignak_module_example' (mod-example)"
        ))
        self.assert_any_log_match(re.escape(
            "Importing Python module 'alignak_module_example' for mod-example-2..."
        ))
        self.assert_any_log_match(re.escape(
            "Imported 'alignak_module_example' for mod-example-2"
        ))
        self.assert_any_log_match(re.escape(
            "Loaded Python module 'alignak_module_example' (mod-example-2)"
        ))
        self.assert_any_log_match(re.escape(
            "Give an instance of alignak_module_example for alias: mod-example"
        ))
        self.assert_any_log_match(re.escape(
            "configuration, foo, bar, 1"
        ))
        self.assert_any_log_match(re.escape(
            "Give an instance of alignak_module_example for alias: mod-example-2"
        ))
        self.assert_any_log_match(re.escape(
            "configuration, faa, bor, 1"
        ))
        # Loading module logs
        self.assert_any_log_match(re.escape(
            "Importing Python module 'alignak_module_example' for mod-example..."
        ))

        my_module = self.modules_manager.instances[0]
        my_module2 = self.modules_manager.instances[1]
        assert my_module.is_external
        assert my_module2.is_external

        # Get list of not external modules
        assert [] == self.modules_manager.get_internal_instances()
        for phase in ['configuration', 'late_configuration', 'running', 'retention']:
            assert [] == self.modules_manager.get_internal_instances(phase)

        # Get list of external modules
        assert [my_module, my_module2] == self.modules_manager.get_external_instances()
        for phase in ['configuration', 'late_configuration', 'running', 'retention']:
            assert [my_module, my_module2] == self.modules_manager.get_external_instances(phase)

        # Start external modules
        self.modules_manager.start_external_instances()
        self.modules_manager.start_external_instances()

        # Starting external module logs
        self.assert_any_log_match(re.escape(
            "Starting external module mod-example"
        ))
        self.assert_any_log_match(re.escape(
            "Starting external process for module mod-example"
        ))
        self.assert_any_log_match(re.escape(
            "mod-example is now started (pid="
        ))

        # Check alive
        assert my_module.process is not None
        assert my_module.process.is_alive()

        assert my_module2.process is not None
        assert my_module2.process.is_alive()

        # Kill the external module (normal stop is .stop_process)
        self.clear_logs()
        print("Killing a module")
        my_module.kill()
        time.sleep(0.1)
        self.show_logs()
        # Stopping module logs
        self.assert_any_log_match(re.escape(
            "Killing external module "
        ))
        self.assert_any_log_match(re.escape(
            "External module killed"
        ))
        # Should be dead (not normally stopped...) but we still know a process for this module!
        assert my_module.process is not None

        self.clear_logs()
        print("Killing another module")
        my_module2.kill()
        time.sleep(0.1)
        self.show_logs()
        # Stopping module logs
        self.assert_any_log_match(re.escape(
            "Killing external module "
        ))
        self.assert_any_log_match(re.escape(
            "External module killed"
        ))
        # Should be dead (not normally stopped...) but we still know a process for this module!
        assert my_module.process is not None

        # Nothing special ...
        self.clear_logs()
        self.modules_manager.check_alive_instances()

        # Try to restart the dead modules
        print("Trying to restart dead modules")
        # We lie on the last restart try time
        my_module.last_init_try = time.time()
        my_module2.last_init_try = time.time()
        self.modules_manager.try_to_restart_deads()
        self.show_logs()
        # In fact it's too early, so it won't do it

        # Here the module instances should still be dead
        assert not my_module.process.is_alive()
        assert not my_module2.process.is_alive()

        # We lie on the last restart try time
        my_module.last_init_try = 0
        my_module2.last_init_try = 0
        self.modules_manager.check_alive_instances()
        self.modules_manager.try_to_restart_deads()

        # Here the module instances should be alive again
        assert my_module.process.is_alive()
        assert my_module2.process.is_alive()

        # Kill the module again
        self.clear_logs()
        my_module.kill()
        self.show_logs()
        time.sleep(0.2)
        assert not my_module.process.is_alive()

        # And we clear all now
        self.modules_manager.stop_all()
        # Stopping module logs
        self.assert_any_log_match(re.escape(
            "I'm stopping module "
        ))
