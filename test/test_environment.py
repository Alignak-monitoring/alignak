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
"""
This file contains the test for the Alignak configuration checks
"""
import os
import re
import time
import unittest2
from alignak_test import AlignakTest
import pytest
from collections import OrderedDict

# from ConfigParser import ParsingError, InterpolationMissingOptionError
from alignak.bin.alignak_environment import AlignakConfigParser


class TestEnvironment(AlignakTest):
    """
    This class tests the environment (eg. main configuration) file
    """
    def setUp(self):
        super(TestEnvironment, self).setUp()

    def test_config_ko(self):
        """ Tests error in the configuration parser calling

        :return: None
        """
        # Configuration file name empty
        with pytest.raises(ValueError):
            args = {'<cfg_file>': None, '--verbose': True}
            self.alignak_env = AlignakConfigParser(args)
            self.alignak_env.parse()

        # Configuration file does not exist
        with pytest.raises(ValueError):
            # Get Alignak environment
            args = {'<cfg_file>': 'unexisting.file', '--verbose': True}
            self.alignak_env = AlignakConfigParser(args)
            self.alignak_env.parse()

    def test_config_ko_content(self):
        """ Configuration has some loading problems ...

        :return: None
        """
        # No defined sections
        configuration_file = os.path.join('./cfg/environment', 'alignak_no_sections.ini')

        # Configuration file does not exist
        with pytest.raises(ValueError):
            # Get Alignak environment
            args = {'<cfg_file>': configuration_file, '--verbose': True}
            self.alignak_env = AlignakConfigParser(args)
            self.alignak_env.parse()

        # --------------------
        # Syntax error
        configuration_file = os.path.join('./cfg/environment', 'alignak_section_syntax.ini')
        args = {'<cfg_file>': configuration_file, '--verbose': True}
        self.alignak_env = AlignakConfigParser(args)
        assert not self.alignak_env.parse()

        # --------------------
        # Interpolation error
        configuration_file = os.path.join('./cfg/environment', 'alignak_section_syntax2.ini')
        # Get Alignak environment
        args = {'<cfg_file>': configuration_file, '--verbose': True}
        self.alignak_env = AlignakConfigParser(args)
        assert not self.alignak_env.parse()

    def test_config_ok(self):
        """ Default shipped configuration has no loading problems ...

        :return: None
        """
        # Default shipped configuration file
        configuration_file = os.path.join('./cfg/environment', 'alignak_ok.ini')

        # Get Alignak environment
        args = {'<cfg_file>': configuration_file, '--verbose': True}
        self.alignak_env = AlignakConfigParser(args)
        assert self.alignak_env.parse()

        default_section = OrderedDict([
            ('_dist', '/tmp'),
            ('_dist_etc', '%(_dist)s/etc/alignak'),
            ('config_name', 'Alignak global configuration'),
            ('extra_config_name', 'extra')
        ])
        assert self.alignak_env.get_defaults() == default_section

        assert self.alignak_env.get_monitored_configuration() == {}

        arbiter_master = {
            '_dist': '/tmp',
            '_dist_etc': '/tmp/etc/alignak',
            'config_name': 'Alignak global configuration',
            'extra_config_name': 'extra',
            'imported_from': '/home/alignak/alignak/test/cfg/environment/alignak_ok.ini',
            'type': 'arbiter',
            'name': 'arbiter-master',
            'modules': 'web-services'
        }
        daemons = {
            'daemon.arbiter-master': arbiter_master,
            'daemon.arbiter-spare': {
                '_dist': '/tmp',
                '_dist_etc': '/tmp/etc/alignak',
                'config_name': 'Alignak global configuration',
                'extra_config_name': 'extra',
                'imported_from': '/home/alignak/alignak/test/cfg/environment/alignak_ok.ini',
                'type': 'arbiter',
                'name': 'arbiter-spare'
            },
            'daemon.poller-master': {
                '_dist': '/tmp',
                '_dist_etc': '/tmp/etc/alignak',
                'config_name': 'Alignak global configuration',
                'extra_config_name': 'extra',
                'imported_from': '/home/alignak/alignak/test/cfg/environment/alignak_ok.ini',
                'type': 'poller',
                'name': 'poller-master'
            }
        }
        assert self.alignak_env.get_daemons() == daemons
        assert self.alignak_env.get_daemons(daemon_name='unknown') == {}
        assert self.alignak_env.get_daemons(daemon_name='arbiter-master') == arbiter_master

        module_ws = {
            '_dist': '/tmp',
            '_dist_etc': '/tmp/etc/alignak',
            'config_name': 'Alignak global configuration',
            'extra_config_name': 'extra',
            'imported_from': '/home/alignak/alignak/test/cfg/environment/alignak_ok.ini',
            'python_name': 'alignak_module_ws',
            'type': 'web-services',
            'name': 'web-services',
            'extra_variable': 'extra'
        }
        modules = {
            'module.web-services': module_ws
        }
        assert self.alignak_env.get_modules() == modules
        assert self.alignak_env.get_modules(name='unknown') == {}
        assert self.alignak_env.get_modules(daemon_name='arbiter-master') == ['web-services']
        assert self.alignak_env.get_modules(daemon_name='arbiter-master', names_only=False) == [module_ws]
        assert self.alignak_env.get_modules(name='web-services') == module_ws
