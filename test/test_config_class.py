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
This file contains the test for the Alignak Config class

"""
import os
import re
import sys
import time
import unittest2
import pytest
import importlib

from .alignak_test import AlignakTest

from alignak.objects.config import Config

class TestConfigClassBase(AlignakTest):
    """
    This class tests the Config obhject initialization
    """
    def setUp(self):
        super(TestConfigClassBase, self).setUp()

    def test_config_ok(self):
        """Test the object initialization and base features"""
        # ---
        # print("Reference to Config: %s" % sys.getrefcount(Config))
        # mod = importlib.import_module("alignak.objects.config")
        # importlib.reload(mod)
        # #
        # # importlib.reload('alignak.objects.config')
        # print("Reference to Config: %s" % sys.getrefcount(Config))

        # Fresh initialized configuration
        alignak_cfg = Config()
        assert alignak_cfg.magic_hash
        next_instance_id = "Config_%s" % Config._next_id
        # assert str(alignak_cfg) == '<Config Config_1 - unknown />'

        # Another fresh initialized configuration
        alignak_cfg = Config()
        assert alignak_cfg.magic_hash
        # Config instance_id incremented!
        assert next_instance_id == alignak_cfg.instance_id
        # assert str(alignak_cfg) == '<Config Config_2 - unknown />'

        # -----------------------------------------------------------------------------------------
        # Macro part
        # ---
        # Macro list is yet defined but the values are not yet set
        expected_macros = {
            # Main Config objects macros
            'ALIGNAK': 'alignak_name',
            'ALIGNAK_CONFIG': 'alignak_env',

            'ADMINEMAIL': '',
            'ADMINPAGER': '',

            'MAINCONFIGDIR': 'config_base_dir',
            'CONFIGFILES': 'config_files',
            'MAINCONFIGFILE': 'main_config_file',

            'OBJECTCACHEFILE': '', 'COMMENTDATAFILE': '', 'TEMPPATH': '', 'SERVICEPERFDATAFILE': '',
            'RESOURCEFILE': '', 'COMMANDFILE': '', 'DOWNTIMEDATAFILE': '',
            'HOSTPERFDATAFILE': '', 'LOGFILE': '', 'TEMPFILE': '', 'RETENTIONDATAFILE': '',
            'STATUSDATAFILE': ''
        }
        # The 64 "USER" macros.
        for i in range(1, 63):
            expected_macros['USER%d' % i] = '$USER%d$' % i

        # After several tests execution the Config object got imported several times and
        # has several python references. The properties object containing the macros is a
        # class object and has thus been updated because some configurations got loaded.
        # Because of this, a pure assertion is only valid when the test is the first one executed!
        compare_macros = {}
        for macro in list(alignak_cfg.macros.items()):
            # print(macro)
            if macro[0] not in [
                '_DIST', '_DIST_BIN', '_DIST_ETC', '_DIST_LOG', '_DIST_RUN', '_DIST_VAR',
                'VAR', 'RUN', 'ETC', 'BIN', 'USER', 'GROUP', 'LIBEXEC', 'LOG',
                'NAGIOSPLUGINSDIR', 'PLUGINSDIR', ''
            ]:
                compare_macros[macro[0]] = macro[1]
        assert compare_macros == expected_macros

        # Macro properties are not yet existing!
        for macro in alignak_cfg.macros:
            assert getattr(alignak_cfg, '$%s$' % macro, None) is None, \
                "Macro: %s property is still existing!" % ('$%s$' % macro)
        # -----------------------------------------------------------------------------------------

        # -----------------------------------------------------------------------------------------
        # Configuration parsing part
        # ---
        # Read and parse the legacy configuration files, do not provide environement file name
        legacy_cfg_files = ['../etc/alignak.cfg']
        raw_objects = alignak_cfg.read_config_buf\
            (alignak_cfg.read_legacy_cfg_files(legacy_cfg_files))
        assert isinstance(raw_objects, dict)
        for daemon_type in ['arbiter', 'broker', 'poller', 'reactionner', 'receiver', 'scheduler']:
            assert daemon_type in raw_objects
        # Make sure we got all the managed objects type
        for o_type in alignak_cfg.types_creations:
            assert o_type in raw_objects, 'Did not found %s in configuration ojbect' % o_type
        assert alignak_cfg.alignak_env == 'n/a'

        # Same parser that stores the environment files names
        env_filename = '../etc/alignak.ini'
        # It should be a list
        env_filename = [os.path.abspath(env_filename)]
        # Read and parse the legacy configuration files, do not provide environement file name
        raw_objects = alignak_cfg.read_config_buf(
            alignak_cfg.read_legacy_cfg_files(legacy_cfg_files, env_filename)
        )
        assert alignak_cfg.alignak_env == env_filename

        # Same parser that stores a string (not list) environment file name
        # as an absolute file path in a list
        env_filename = '../etc/alignak.ini'
        # Read and parse the legacy configuration files, do not provide environement file name
        raw_objects = alignak_cfg.read_config_buf(
            alignak_cfg.read_legacy_cfg_files(legacy_cfg_files, env_filename)
        )
        assert alignak_cfg.alignak_env == [os.path.abspath(env_filename)]

        # Same parser that stores the environment file name as an absolute file path
        env_filename = '../etc/alignak.ini'
        # Read and parse the legacy configuration files, do not provide environement file name
        raw_objects = alignak_cfg.read_config_buf(
            alignak_cfg.read_legacy_cfg_files(legacy_cfg_files, env_filename)
        )
        assert alignak_cfg.alignak_env == [os.path.abspath(env_filename)]
        # -----------------------------------------------------------------------------------------

        # -----------------------------------------------------------------------------------------
        # Macro part
        # ---
        # The macros defined in the default loaded configuration
        expected_macros.update({
            '_DIST': '$_DIST$',
            '_DIST_BIN': '$_DIST_BIN$',
            '_DIST_ETC': '$_DIST_ETC$',
            '_DIST_LOG': '$_DIST_LOG$',
            '_DIST_RUN': '$_DIST_RUN$',
            '_DIST_VAR': '$_DIST_VAR$',
            'BIN': '$BIN$',
            'ETC': '$ETC$',
            'GROUP': '$GROUP$',
            'LIBEXEC': '$LIBEXEC$',
            'LOG': '$LOG$',
            'NAGIOSPLUGINSDIR': '',
            'PLUGINSDIR': '$',
            'RUN': '$RUN$',
            'USER': '$USER$',
            'USER1': '$NAGIOSPLUGINSDIR$',
            'VAR': '$VAR$'
        })
        assert sorted(alignak_cfg.macros) == sorted(expected_macros)
        assert alignak_cfg.resource_macros_names == []
        # Macro are not existing in the object attributes!
        for macro in alignak_cfg.macros:
            macro = alignak_cfg.macros[macro]
            assert getattr(alignak_cfg, '$%s$' % macro, None) is None, \
                "Macro: %s property is existing as an attribute!" % ('$%s$' % macro)
        # But as an attribute of the properties attribute!
        for macro in alignak_cfg.macros:
            macro = alignak_cfg.macros[macro]
            assert getattr(alignak_cfg.properties, '$%s$' % macro, None) is None, \
                "Macro: %s property is not existing as an attribute of properties!" % ('$%s$' % macro)
