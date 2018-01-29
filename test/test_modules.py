#!/usr/bin/env python
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
from alignak_test import AlignakTest
from alignak.modulesmanager import ModulesManager
from alignak.objects.module import Module
import pytest


class TestModules(AlignakTest):
    """
    This class contains the tests for the modules
    """

    def test_module_loading(self):
        """ Test arbiter, broker, ... detecting configured modules

        :return:
        """
        self.print_header()
        self.setup_with_file('./cfg/cfg_default_with_modules.cfg')
        assert self.conf_is_correct
        self.show_configuration_logs()

        # The only existing arbiter module is Example declared in the configuration
        modules = [m.module_alias for m in self.arbiter.myself.modules]
        assert modules == ['Example']

        # The only existing broker module is Example declared in the configuration
        modules = [m.module_alias for m in self.brokers['broker-master'].modules]
        assert modules == ['Example']

        # The only existing poller module is Example declared in the configuration
        modules = [m.module_alias for m in self.pollers['poller-master'].modules]
        assert modules == ['Example']

        # The only existing receiver module is Example declared in the configuration
        modules = [m.module_alias for m in self.receivers['receiver-master'].modules]
        assert modules == ['Example']

        # The only existing reactionner module is Example declared in the configuration
        modules = [m.module_alias for m in self.reactionners['reactionner-master'].modules]
        assert modules == ['Example']

        # No scheduler modules created
        modules = [m.module_alias for m in self.schedulers['scheduler-master'].modules]
        assert modules == ['Example']

        # Loading module logs
        self.assert_any_log_match(re.escape(
            "Importing Python module 'alignak_module_example' for Example..."
        ))
        self.assert_any_log_match(re.escape(
            "Module properties: {'daemons': ['arbiter', 'broker', 'scheduler', 'poller', "
            "'receiver', 'reactionner'], 'phases': ['configuration', 'late_configuration', "
            "'running', 'retention'], 'type': 'example', 'external': True}"
        ))
        self.assert_any_log_match(re.escape(
            "Imported 'alignak_module_example' for Example"
        ))
        self.assert_any_log_match(re.escape(
            "Give an instance of alignak_module_example for alias: Example"
        ))
        self.assert_any_log_match(re.escape(
            "I correctly loaded my modules: [Example]"
        ))

    def test_arbiter_configuration_module(self):
        """ Test arbiter configuration loading

        :return:
        """
        self.print_header()
        self.setup_with_file('./cfg/cfg_arbiter_configuration_module.cfg')
        assert self.conf_is_correct
        self.show_configuration_logs()
        self.show_logs()

        # The arbiter module is 'backend_arbiter' declared in the configuration
        modules = [m.module_alias for m in self.arbiter.myself.modules]
        assert modules == ['backend_arbiter']

    def test_missing_module_detection(self):
        """ Detect missing module configuration

        Alignak configuration parser detects that some modules are required because some
        specific parameters are included in the configuration files. If the modules are not
        present in the configuration, it logs warning message to alert the user about this!

        :return:
        """
        self.print_header()
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/modules/alignak_modules_nagios_parameters.cfg')
        assert not self.conf_is_correct
        self.show_configuration_logs()

        # Log missing module
        self.assert_any_log_match(
            re.escape(
                "Your configuration parameters 'status_file = /var/status.dat' and "
                "'object_cache_file = /var/status.dat' need to use an external module such "
                "as 'retention' but I did not found one!"
            )
        )
        self.assert_any_log_match(
            re.escape(
                "Your configuration parameter 'log_file = /test/file' needs to use an external "
                "module such as 'logs' but I did not found one!"
            )
        )
        self.assert_any_log_match(
            re.escape(
                "Your configuration parameter 'use_syslog = True' needs to use an external "
                "module such as 'logs' but I did not found one!"
            )
        )
        self.assert_any_log_match(
            re.escape(
                "Your configuration parameters 'host_perfdata_file = /test/file' and "
                "'service_perfdata_file = /test/file' need to use an external module such as "
                "'retention' but I did not found one!"
            )
        )
        self.assert_any_log_match(
            re.escape(
                "Your configuration parameters 'state_retention_file = /test/file' and "
                "'retention_update_interval = 100' need to use an external module such as "
                "'retention' but I did not found one!"
            )
        )
        self.assert_any_log_match(
            re.escape(
                "Your configuration parameter 'command_file = /var/alignak.cmd' needs to use "
                "an external module such as 'logs' but I did not found one!"
            )
        )

    def test_module_on_module(self):
        """ No module configuration for modules

        Check that the feature is detected as disabled
        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/modules/alignak_module_with_submodules.cfg')
        assert self.conf_is_correct
        self.show_configuration_logs()

        # No arbiter modules created
        modules = [m.module_alias for m in self.arbiter.myself.modules]
        assert modules == ['Example']

        # The only existing broker module is Example declared in the configuration
        modules = [m.module_alias for m in self.brokers['broker-master'].modules]
        assert modules == ['Example']

        # The only existing poller module is Example declared in the configuration
        modules = [m.module_alias for m in self.pollers['poller-master'].modules]
        assert modules == ['Example']

        # The only existing receiver module is Example declared in the configuration
        modules = [m.module_alias for m in self.receivers['receiver-master'].modules]
        assert modules == ['Example']

        # The only existing reactionner module is Example declared in the configuration
        modules = [m.module_alias for m in self.reactionners['reactionner-master'].modules]
        assert modules == ['Example']

        # No scheduler modules created
        modules = [m.module_alias for m in self.schedulers['scheduler-master'].modules]
        assert modules == ['Example']

    def test_modulemanager(self):
        """ Module manager manages its modules

        Test if the module manager manages correctly all the modules
        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default_with_modules.cfg')
        assert self.conf_is_correct

        # Create an Alignak module
        mod = Module({
            'module_alias': 'mod-example',
            'module_types': 'example',
            'python_name': 'alignak_module_example'
        })

        # Create the modules manager for a daemon type
        self.modulemanager = ModulesManager('receiver', None)

        # Load an initialize the modules:
        #  - load python module
        #  - get module properties and instances
        self.modulemanager.load_and_init([mod])

        # Loading module logs
        self.assert_any_log_match(re.escape(
            "Importing Python module 'alignak_module_example' for Example..."
        ))
        self.assert_any_log_match(re.escape(
            "Module properties: {'daemons': ['arbiter', 'broker', 'scheduler', 'poller', "
            "'receiver', 'reactionner'], 'phases': ['configuration', 'late_configuration', "
            "'running', 'retention'], 'type': 'example', 'external': True}"
        ))
        self.assert_any_log_match(re.escape(
            "Imported 'alignak_module_example' for Example"
        ))
        self.assert_any_log_match(re.escape(
            "Give an instance of alignak_module_example for alias: Example"
        ))
        self.assert_any_log_match(re.escape(
            "I correctly loaded my modules: [Example]"
        ))

        my_module = self.modulemanager.instances[0]
        assert my_module.is_external

        # Get list of not external modules
        assert [] == self.modulemanager.get_internal_instances()
        for phase in ['configuration', 'late_configuration', 'running', 'retention']:
            assert [] == self.modulemanager.get_internal_instances(phase)

        # Get list of external modules
        assert [my_module] == self.modulemanager.get_external_instances()
        for phase in ['configuration', 'late_configuration', 'running', 'retention']:
            assert [my_module] == self.modulemanager.get_external_instances(phase)

        # Start external modules
        self.modulemanager.start_external_instances()

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

        # Kill the external module (normal stop is .stop_process)
        my_module.kill()
        time.sleep(0.1)
        # Should be dead (not normally stopped...) but we still know a process for this module!
        assert my_module.process is not None

        # Stopping module logs
        self.assert_any_log_match(re.escape(
            "Killing external module "
        ))
        self.assert_any_log_match(re.escape(
            "External module killed"
        ))

        # Nothing special ...
        self.modulemanager.check_alive_instances()

        # Try to restart the dead modules
        self.modulemanager.try_to_restart_deads()

        # In fact it's too early, so it won't do it

        # Here the inst should still be dead
        assert not my_module.process.is_alive()

        # So we lie
        my_module.last_init_try = -5
        self.modulemanager.check_alive_instances()
        self.modulemanager.try_to_restart_deads()

        # In fact it's too early, so it won't do it

        # Here the inst should be alive again
        assert my_module.process.is_alive()

        # should be nothing more in to_restart of
        # the module manager
        assert [] == self.modulemanager.to_restart

        # Now we look for time restart so we kill it again
        my_module.kill()
        time.sleep(0.2)
        assert not my_module.process.is_alive()

        # Should be too early
        self.modulemanager.check_alive_instances()
        self.modulemanager.try_to_restart_deads()
        assert not my_module.process.is_alive()
        # We lie for the test again
        my_module.last_init_try = -5
        self.modulemanager.check_alive_instances()
        self.modulemanager.try_to_restart_deads()

        # Here the inst should be alive again
        assert my_module.process.is_alive()

        # And we clear all now
        self.modulemanager.stop_all()
        # Stopping module logs
        self.assert_any_log_match(re.escape(
            "I'm stopping module "
        ))

    def test_modulemanager_several_modules(self):
        """ Module manager manages its modules

        Test if the module manager manages correctly all the modules

        Configured with several modules
        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default_with_modules.cfg')
        assert self.conf_is_correct

        for mod in self.arbiter.conf.modules:
            print (mod.__dict__)

        # time_hacker.set_real_time()

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
        # Create the modules manager for a daemon type
        self.modulemanager = ModulesManager('receiver', None)

        # Load an initialize the modules:
        #  - load python module
        #  - get module properties and instances
        self.modulemanager.load_and_init([mod, mod2])
        self.show_logs()

        # Loading module logs
        self.assert_any_log_match(re.escape(
            "Importing Python module 'alignak_module_example' for mod-example..."
        ))
        self.assert_any_log_match(re.escape(
            "Importing Python module 'alignak_module_example' for mod-example-2..."
        ))
        self.assert_any_log_match(re.escape(
            "Module properties: {'daemons': ['arbiter', 'broker', 'scheduler', 'poller', "
            "'receiver', 'reactionner'], 'phases': ['configuration', 'late_configuration', "
            "'running', 'retention'], 'type': 'example', 'external': True}"
        ))
        self.assert_any_log_match(re.escape(
            "Imported 'alignak_module_example' for mod-example"
        ))
        self.assert_any_log_match(re.escape(
            "Imported 'alignak_module_example' for mod-example-2"
        ))
        self.assert_any_log_match(re.escape(
            "[alignak.module.mod-example] configuration, foo, bar, 1"
        ))
        self.assert_any_log_match(re.escape(
            "[alignak.module.mod-example-2] configuration, faa, bor, 1"
        ))

        my_module = self.modulemanager.instances[0]
        my_module2 = self.modulemanager.instances[1]
        assert my_module.is_external
        assert my_module2.is_external

        # Get list of not external modules
        assert [] == self.modulemanager.get_internal_instances()
        for phase in ['configuration', 'late_configuration', 'running', 'retention']:
            assert [] == self.modulemanager.get_internal_instances(phase)

        # Get list of external modules
        assert [my_module, my_module2] == self.modulemanager.get_external_instances()
        for phase in ['configuration', 'late_configuration', 'running', 'retention']:
            assert [my_module, my_module2] == self.modulemanager.get_external_instances(phase)

        # Start external modules
        self.modulemanager.start_external_instances()

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

        # Kill the external module (normal stop is .stop_process)
        my_module.kill()
        time.sleep(0.1)
        # Should be dead (not normally stopped...) but we still know a process for this module!
        assert my_module.process is not None

        # Stopping module logs
        self.assert_any_log_match(re.escape(
            "Killing external module "
        ))
        self.assert_any_log_match(re.escape(
            "External module killed"
        ))

        # Nothing special ...
        self.modulemanager.check_alive_instances()

        # Try to restart the dead modules
        self.modulemanager.try_to_restart_deads()

        # In fact it's too early, so it won't do it

        # Here the inst should still be dead
        assert not my_module.process.is_alive()

        # So we lie
        my_module.last_init_try = -5
        self.modulemanager.check_alive_instances()
        self.modulemanager.try_to_restart_deads()

        # In fact it's too early, so it won't do it

        # Here the inst should be alive again
        assert my_module.process.is_alive()

        # should be nothing more in to_restart of
        # the module manager
        assert [] == self.modulemanager.to_restart

        # Now we look for time restart so we kill it again
        my_module.kill()
        time.sleep(0.2)
        assert not my_module.process.is_alive()

        # Should be too early
        self.modulemanager.check_alive_instances()
        self.modulemanager.try_to_restart_deads()
        assert not my_module.process.is_alive()
        # We lie for the test again
        my_module.last_init_try = -5
        self.modulemanager.check_alive_instances()
        self.modulemanager.try_to_restart_deads()

        # Here the inst should be alive again
        assert my_module.process.is_alive()

        # And we clear all now
        self.modulemanager.stop_all()
        # Stopping module logs
        self.assert_any_log_match(re.escape(
            "I'm stopping module "
        ))
