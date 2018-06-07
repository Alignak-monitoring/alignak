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
"""
Test Alignak inner modules : plain-old Nagios legacy compatibility
"""

import re
import os
import shutil
import time
import logging
import configparser
from alignak.log import ALIGNAK_LOGGER_NAME
from .alignak_test import AlignakTest, CollectorHandler
from alignak.modulesmanager import ModulesManager, MODULE_INIT_PERIOD
from alignak.objects.module import Module
import pytest

class TestInnerModules(AlignakTest):
    """
    This class contains the tests for the Alignak inner defined modules
    """
    def setUp(self):
        super(TestInnerModules, self).setUp()
        self.set_unit_tests_logger_level('INFO')

    def test_module_inner_retention_legacy_cfg(self):
        """ Test the inner retention module

        Configured in Nagios cfg file
        """
        self._module_inner_retention()


    def test_module_inner_retention_alignak_ini(self):
        """ Test the inner retention module

        Configured in alignak.ini file
        """
        self._module_inner_retention()


    def _module_inner_retention(self, legacy_cfg=False):
        """ Test the inner retention module

        Module is self-created when a Nagios retention parameter is detected

        This module implements the `load_retention` and `save_retention` scheduler hooks

        :return:
        """
        self.cfg_folder = '/tmp/alignak'
        cfg_dir = 'default_many_hosts'
        hosts_count = 10
        realms = ['All']

        #  Default shipped configuration preparation
        self._prepare_configuration(copy=True, cfg_folder=self.cfg_folder)

        # Specific daemon load configuration preparation
        if os.path.exists('./cfg/%s/alignak.cfg' % cfg_dir):
            shutil.copy('./cfg/%s/alignak.cfg' % cfg_dir, '%s/etc' % self.cfg_folder)
        if os.path.exists('%s/etc/arbiter' % self.cfg_folder):
            shutil.rmtree('%s/etc/arbiter' % self.cfg_folder)
        shutil.copytree('./cfg/%s/arbiter' % cfg_dir, '%s/etc/arbiter' % self.cfg_folder)

        self._prepare_hosts_configuration(cfg_folder='%s/etc/arbiter/objects/hosts'
                                                     % self.cfg_folder,
                                          hosts_count=hosts_count, target_file_name='hosts.cfg',
                                          realms=realms)

        # Update the default configuration files
        files = ['%s/etc/alignak.ini' % self.cfg_folder]
        try:
            cfg = configparser.ConfigParser()
            cfg.read(files)

            # Define Nagios state retention module configuration parameter
            if not legacy_cfg:
                cfg.set('alignak-configuration', 'retain_state_information', '1')
                cfg.set('alignak-configuration', 'state_retention_file',
                        '%s/retention.json' % self.cfg_folder)

            # # Define the inner retention module
            # Not necessary to defined a odule but it may also be done!
            # cfg.set('daemon.scheduler-master', 'modules', 'inner-retention')
            #
            # # Define Alignak inner module configuration
            # cfg.add_section('module.inner-retention')
            # cfg.set('module.inner-retention', 'name', 'inner-retention')
            # cfg.set('module.inner-retention', 'type', 'retention')
            # cfg.set('module.inner-retention', 'python_name', 'alignak.modules.retention')

            with open('%s/etc/alignak.ini' % self.cfg_folder, "w") as modified:
                cfg.write(modified)
        except Exception as exp:
            print("* parsing error in config file: %s" % exp)
            assert False

        # # Define Nagios state retention module configuration parameter
        if legacy_cfg:
            with open('%s/etc/alignak.cfg' % self.cfg_folder, "a") as modified:
                modified.write("retain_state_information=1\n\nstate_retention_file=/tmp/retention.json")

        self.setup_with_file(env_file='%s/etc/alignak.ini' % self.cfg_folder)
        assert self.conf_is_correct
        self.show_configuration_logs()

        # No scheduler modules created
        modules = [m.module_alias for m in self._scheduler_daemon.modules]
        assert modules == ['inner-retention']
        modules = [m.name for m in self._scheduler_daemon.modules]
        assert modules == ['inner-retention']

        # Loading module logs
        self.assert_any_log_match(re.escape(
            u"Importing Python module 'alignak.modules.inner_retention' for inner-retention..."
        ))
        self.assert_any_log_match(re.escape(
            u"Imported 'alignak.modules.inner_retention' for inner-retention"
        ))
        self.assert_any_log_match(re.escape(
            u"Give an instance of alignak.modules.inner_retention for alias: inner-retention"
        ))
        self.assert_any_log_match(re.escape(
            u"I correctly loaded my modules: [inner-retention]"
        ))

        # Load retention - file is not yet existing!
        self.clear_logs()
        self._scheduler.hook_point('load_retention')
        self.show_logs()

        # Save retention
        self.clear_logs()
        self._scheduler.hook_point('save_retention')
        self.show_logs()
        assert os.path.exists('/tmp/alignak/retention.json')
        with open('/tmp/alignak/retention.json', "r") as fd:
            response = json.load(fd)

        # Load retention - file is now existing
        self.clear_logs()
        self._scheduler.hook_point('load_retention')
        self.show_logs()
