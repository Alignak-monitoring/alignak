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
import json
import unittest2
import pytest
import importlib
from pprint import pprint

from .alignak_test import AlignakTest

from alignak.objects.config import Config
from alignak.objects.contact import Contact
from alignak.objects.host import Host
from alignak.misc.serialization import serialize, unserialize


class TestConfigClassBase(AlignakTest):
    """
    This class tests the Config object initialization
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

        # Fresh initialized configuration
        alignak_cfg = Config({})
        assert alignak_cfg.magic_hash
        next_instance_id = "Config_%s" % Config._next_id
        # assert str(alignak_cfg) == '<Config Config_1 - unknown />'

        # Another fresh initialized configuration
        alignak_cfg = Config({})
        assert alignak_cfg.magic_hash
        # Config instance_id incremented!
        assert next_instance_id == alignak_cfg.instance_id
        # assert str(alignak_cfg) == '<Config Config_2 - unknown />'
        pprint(alignak_cfg.macros)

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
            'STATUSDATAFILE': '',
            'RETENTION_FILE': 'state_retention_file'
        }
        # The 64 "USER" macros.
        for i in range(1, 65):
            expected_macros['USER%d' % i] = '$USER%d$' % i
        assert alignak_cfg.macros == expected_macros

        # After several tests execution the Config object got imported several times and
        # has several python references. The properties object containing the macros is a
        # class object and has thus been updated because some configurations got loaded.
        # Because of this, a pure assertion is only valid when the test is the first one executed!
        compare_macros = {}
        for macro in list(alignak_cfg.macros.items()):
            compare_macros[macro[0]] = macro[1]
            # print(macro)
            # if macro[0] not in [
            #     'DIST', 'DIST_BIN', 'DIST_ETC', 'DIST_LOG', 'DIST_RUN', 'DIST_VAR',
            #     'VAR', 'RUN', 'ETC', 'BIN', 'USER', 'GROUP', 'LIBEXEC', 'LOG',
            #     'NAGIOSPLUGINSDIR', 'PLUGINSDIR', ''
            # ]:
            #     compare_macros[macro[0]] = macro[1]
        assert compare_macros == expected_macros
        assert alignak_cfg.macros == expected_macros

        # # Macro properties are not yet existing!
        # for macro in alignak_cfg.macros:
        #     print("Macro: %s" % macro)
        #     assert getattr(alignak_cfg, '$%s$' % macro, None) is None, \
        #         "Macro: %s property is still existing!" % ('$%s$' % macro)
        # -----------------------------------------------------------------------------------------

        # -----------------------------------------------------------------------------------------
        # Configuration parsing part
        # ---
        # Read and parse the legacy configuration files, do not provide environment file name
        legacy_cfg_files = ['../etc/alignak.cfg']
        raw_objects = alignak_cfg.read_config_buf(
            alignak_cfg.read_legacy_cfg_files(legacy_cfg_files)
        )
        assert isinstance(raw_objects, dict)
        for daemon_type in ['arbiter', 'broker', 'poller', 'reactionner', 'receiver', 'scheduler']:
            assert daemon_type in raw_objects
        # Make sure we got all the managed objects type
        for o_type in alignak_cfg.types_creations:
            assert o_type in raw_objects, 'Did not found %s in configuration object' % o_type
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
            # 'DIST': '$DIST$',
            # 'DIST_BIN': '$DIST_BIN$',
            # 'DIST_ETC': '$DIST_ETC$',
            # 'DIST_LOG': '$DIST_LOG$',
            # 'DIST_RUN': '$DIST_RUN$',
            # 'DIST_VAR': '$DIST_VAR$',
            # 'BIN': '$BIN$',
            # 'ETC': '$ETC$',
            # 'GROUP': '$GROUP$',
            # 'LIBEXEC': '$LIBEXEC$',
            # 'LOG': '$LOG$',
            # 'NAGIOSPLUGINSDIR': '',
            # 'PLUGINSDIR': '$',
            # 'RUN': '$RUN$',
            # 'USER': '$USER$',
            # 'USER1': '$NAGIOSPLUGINSDIR$',
            # 'VAR': '$VAR$'
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

    def test_config_serialization(self):
        """Test the object initialization and base features"""
        # ---
        # print("Reference to Config: %s" % sys.getrefcount(Config))
        # mod = importlib.import_module("alignak.objects.config")
        # importlib.reload(mod)
        # #
        # # importlib.reload('alignak.objects.config')
        # print("Reference to Config: %s" % sys.getrefcount(Config))

        # Fresh initialized configuration
        alignak_cfg = Config({})
        assert alignak_cfg.magic_hash

        # No objects still exist in the attributes
        for _, _, category, _, _ in list(alignak_cfg.types_creations.values()):
            assert getattr(alignak_cfg, category, None) is None

        # Read and parse the legacy configuration files, do not provide environment file name
        legacy_cfg_files = [
            os.path.join(self._test_dir, '../etc/alignak.cfg')
        ]
        raw_objects = alignak_cfg.read_legacy_cfg_files(legacy_cfg_files)
        raw_objects = alignak_cfg.read_config_buf(raw_objects)

        # Create objects for arbiters and modules
        alignak_cfg.early_create_objects(raw_objects)

        # Only arbiters and modules objects exist in the attributes
        for _, _, category, _, _ in list(alignak_cfg.types_creations.values()):
            if category in ['arbiters', 'modules']:
                assert getattr(alignak_cfg, category, None) is not None
            else:
                assert getattr(alignak_cfg, category, None) is None

        # Create objects for all the configuration
        alignak_cfg.create_objects(raw_objects)

        # Now all objects exist in the attributes
        print("After parsing files:")
        for _, _, category, _, _ in list(alignak_cfg.types_creations.values()):
            assert getattr(alignak_cfg, category, None) is not None
            print("- %s %s" % (len(getattr(alignak_cfg, category)) if getattr(alignak_cfg, category) else 'no', category))

        # Create Template links
        alignak_cfg.linkify_templates()

        # All inheritances
        alignak_cfg.apply_inheritance()

        # Explode between types
        alignak_cfg.explode()

        # Implicit inheritance for services
        alignak_cfg.apply_implicit_inheritance()

        # Fill default values for all the configuration objects
        alignak_cfg.fill_default_configuration()

        # Remove templates from config
        # Do not remove anymore!
        # alignak_cfg.remove_templates()

        # Overrides specific service instances properties
        alignak_cfg.override_properties()

        # Linkify objects to each other
        alignak_cfg.linkify()

        # applying dependencies
        alignak_cfg.apply_dependencies()

        # Raise warning about currently unmanaged parameters
        alignak_cfg.warn_about_unmanaged_parameters()

        # Explode global configuration parameters into Classes
        alignak_cfg.explode_global_conf()

        # set our own timezone and propagate it to other satellites
        alignak_cfg.propagate_timezone_option()

        # Look for business rules, and create the dep tree
        alignak_cfg.create_business_rules()
        # And link them
        alignak_cfg.create_business_rules_dependencies()

        # Now all objects exist in the attributes
        print("After objects creation:")
        for _, _, category, _, _ in list(alignak_cfg.types_creations.values()):
            assert getattr(alignak_cfg, category, None) is not None
            # Store and print the items length
            setattr(self, 'len_' + category, len(getattr(alignak_cfg, category)))
            print("- %s %s" % (len(getattr(alignak_cfg, category)) if getattr(alignak_cfg, category) else 'no', category))

            for item in getattr(alignak_cfg, category):
                # Cleanable properties are still existing in the objects
                for prop in ['imported_from', 'use', 'plus', 'register', 'definition_order',
                             'configuration_warnings', 'configuration_errors']:
                    assert hasattr(item, prop)

        assert alignak_cfg
        assert alignak_cfg.is_correct()
        assert alignak_cfg.conf_is_correct
        print("Errors: ", alignak_cfg.show_errors())

        alignak_cfg.dump(dump_file_name='/tmp/dumped_configuration.json')
        dump = alignak_cfg.dump()
        # pprint(dump)

        # Configuration cleaning
        alignak_cfg.clean()

        # Now all objects exist in the attributes
        print("After objects cleaning:")
        for _, _, category, _, _ in list(alignak_cfg.types_creations.values()):
            assert getattr(alignak_cfg, category, None) is not None
            for item in getattr(alignak_cfg, category):
                # Cleanable properties are still existing in the objects
                for prop in ['imported_from', 'use', 'plus', 'definition_order',
                             'configuration_warnings', 'configuration_errors']:
                    assert not hasattr(item, prop)

        # --- Contacts
        # Serialize to send to another daemon
        print("Contacts: %s" % alignak_cfg.contacts)
        for contact in alignak_cfg.contacts.templates:
            print("- %s" % (alignak_cfg.contacts.templates[contact]))
        for contact in alignak_cfg.contacts.items:
            print("- %s" % (alignak_cfg.contacts.items[contact]))
        res = serialize(alignak_cfg.contacts, no_json=True, printing=False)
        print("Serialized contacts: %s" % res)
        # pprint(res)

        # Un-serialize when received by a daemon
        result = unserialize(res, printing=False)
        print("Unserialized: %s" % result)
        assert len(result.templates) == 1
        for uuid in result.templates:
            contact = result.templates[uuid]
            print("- %s" % contact)
            assert isinstance(contact, Contact)
            assert contact.__class__.my_type == "contact"
            assert contact.is_a_template() is True
            assert contact.get_name() in ['generic-contact']
        assert len(result.items) == 2
        for uuid in result.items:
            contact = result.items[uuid]
            print("- %s" % contact)
            assert isinstance(contact, Contact)
            assert contact.__class__.my_type == "contact"
            assert contact.is_a_template() is False
            assert contact.get_name() in ['guest', 'admin']

        # --- Hosts
        # Serialize to send to another daemon
        print("Hosts: %s" % alignak_cfg.hosts)
        for host in alignak_cfg.hosts.templates:
            print("- %s" % (alignak_cfg.hosts.templates[host]))
        for host in alignak_cfg.hosts.items:
            print("- %s" % (alignak_cfg.hosts.items[host]))
        res = serialize(alignak_cfg.hosts, no_json=True, printing=False)
        print("Serialized hosts: %s" % res)
        # pprint(res)

        # Un-serialize when received by a daemon
        result = unserialize(res, printing=False)
        print("Unserialized: %s" % result)
        assert len(result.templates) == 9
        for uuid in result.templates:
            host = result.templates[uuid]
            print("- %s" % host)
            assert isinstance(host, Host)
            assert host.__class__.my_type == "host"
            assert host.is_a_template() is True
            assert host.get_name() in ['generic-host', 'test-host', 'passive-host',
                                       'no-importance', 'qualification', 'normal', 'important', 'production',
                                       'top-for-business']
        assert len(result.items) == 48
        for uuid in result.items:
            host = result.items[uuid]
            print("- %s" % host)
            assert isinstance(host, Host)
            assert host.__class__.my_type == "host"
            assert host.is_a_template() is False
            # assert host.get_name() in ['guest', 'admin']

        # Serialization and hashing
        s_conf_part = serialize(alignak_cfg)
        # pprint(s_conf_part)
        # Update, remove this
        # try:
        #     s_conf_part = s_conf_part.encode('utf-8')
        # except UnicodeDecodeError:
        #     pass

        # Not a JSON object but a dict!
        # data = json.loads(s_conf_part)
        data = s_conf_part
        assert '__sys_python_module__' in data
        assert data['__sys_python_module__'] == "alignak.objects.config.Config"
        assert 'content' in data
        assert isinstance(data['content'], dict)

        # print("Serialization content: ")
        # pprint(data['content'])

        for prop in ['host_perfdata_command', 'service_perfdata_command',
                     'host_perfdata_file_processing_command',
                     'service_perfdata_file_processing_command',
                     'global_host_event_handler', 'global_service_event_handler']:
            assert prop in data['content']
            # If a command is set, then:
            # assert '__sys_python_module__' in data['content'][prop]
            # assert data['content'][prop]['__sys_python_module__'] == "alignak.commandcall.CommandCall"
            # but the default configuration used in this test do not define any command!

        # Now all objects exist in the attributes
        print("After objects unserialization:")
        for _, TheItems, category, _, _ in list(alignak_cfg.types_creations.values()):
            print("- %s" % category)
            if category in ['arbiters', 'schedulers', 'brokers',
                            'pollers', 'reactionners', 'receivers']:
                continue
            assert category in data['content']
            # pprint(data['content'][category])

            objects = unserialize(data['content'][category], printing=False)
            # pprint(objects)
            assert isinstance(objects, TheItems)
            print("- %s %s (saved: %s)" % (len(objects) if objects else 'no', category, getattr(self, 'len_' + category)))

            # assert 'items' in objects
            # assert 'templates' in objects
            #
            # Store and print the items length
            assert len(objects) == getattr(self, 'len_' + category)
            # print("- %s %s" % (len(objects) if objects else 'no', category))

        # Create a Config from unserialization (no file parsing)
        new_cfg = Config(data['content'], parsing=False)

        # unserialize(s_conf_part)
        # assert isinstance(s_conf_part,str)

        # for _, _, category, _, _ in list(alignak_cfg.types_creations.values()):
        #     print("Monitored object class: '%s'" % category)
        #     assert getattr(alignak_cfg, category, None) is not None
        #
        # pprint(alignak_cfg)
        # for _, _, category, _, _ in list(alignak_cfg.types_creations.values()):
        #     print("Monitored object class: '%s'" % category)
        #     try:
        #         objs = [jsonify_r(i) for i in getattr(alignak_cfg, category)]
        #     except (TypeError, AttributeError):  # pragma: no cover, simple protection
        #         logger.warning("Dumping configuration, '%s' not present in the configuration",
        #                        category)
        #         continue
        #
        #     pprint(objs)

