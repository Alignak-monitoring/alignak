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
"""
This file test unserialisation of data
"""

import pytest
from copy import copy
from pprint import pprint

from alignak_test import AlignakTest, unittest

from alignak.misc.serialization import serialize, unserialize
from alignak.alignakobject import AlignakObject

from alignak.objects.item import Item, Items
from alignak.objects.schedulingitem import SchedulingItem, SchedulingItems

from alignak.objects.command import Command, Commands
from alignak.commandcall import CommandCall
from alignak.objects.timeperiod import Timeperiod, Timeperiods
from alignak.objects.realm import Realm, Realms
from alignak.objects.notificationway import NotificationWay, NotificationWays

from alignak.objects.contact import Contact, Contacts
from alignak.objects.contactgroup import Contactgroup, Contactgroups
from alignak.objects.host import Host, Hosts
from alignak.objects.hostgroup import Hostgroup, Hostgroups
from alignak.objects.service import Service, Services
from alignak.objects.servicegroup import Servicegroup, Servicegroups
from alignak.objects.servicedependency import Servicedependency, Servicedependencies

from alignak.objects.businessimpactmodulation import Businessimpactmodulation, Businessimpactmodulations
from alignak.objects.checkmodulation import CheckModulation, CheckModulations
from alignak.objects.resultmodulation import Resultmodulation, Resultmodulations
from alignak.objects.macromodulation import MacroModulation, MacroModulations

from alignak.objects.escalation import Escalation, Escalations
from alignak.objects.trigger import Trigger, Triggers

from alignak.objects.config import Config


class TestUnserialize(AlignakTest):
    """
    This class test the unserialize process
    """
    def set_expected(self, obj):
        """Create a dictionary with default expected values for an object"""
        all_props = {}
        for key, value in getattr(obj, "running_properties", {}).iteritems():
            if value.has_default:
                # Make a copy for iterable properties
                if hasattr(value.default, '__iter__'):
                    all_props[key] = copy(value.default)
                else:
                    all_props[key] = value.default
            else:
                all_props[key] = value

        return all_props

    def get_commands(self):
        # Command initialization
        self.command1 = Command({'command_name': 'command1', 'use': 'command_tpl'}, parsing=True)
        self.command2 = Command({'command_name': 'command2', 'imported_from': 'file.cfg'})
        # Build a commands list
        self.commands_list = Commands([self.command1, self.command2])

        # Link to templates
        self.commands_list.linkify_templates()
        # Apply inheritance from templates
        self.commands_list.apply_inheritance()

    def get_timeperiods(self):
        # Contact initialization
        self.timeperiod1 = Timeperiod({'timeperiod_name': '24x7'}, parsing=True)
        assert not self.timeperiod1.is_tpl()

        # Build a timeperiods list
        self.timeperiods_list = Timeperiods([self.timeperiod1])

        # Link to templates
        self.timeperiods_list.linkify_templates()
        # Apply inheritance from templates
        self.timeperiods_list.apply_inheritance()

    def get_contacts(self):
        # Contact initialization
        self.contact1 = Contact({'contact_name': 'contact1'})
        self.contact2 = Contact({'contact_name': 'contact2',
                                 'contactgroups': 'contacts_group',
                                 'imported_from': 'file.cfg'})

        # Build a contacts list
        self.contacts_list = Contacts([self.contact1])

        # Contact group
        self.contacts_group = Contactgroup({'contactgroup_name': 'contacts_group',
                                            'members': 'contact1'})

        # Build a contacts groups list and a notification ways list
        self.notificationways_list = NotificationWays([])
        self.contactgroups_list = Contactgroups([self.contacts_group])

        # Create templates links
        self.contacts_list.linkify_templates()
        # Manage inheritance
        self.contacts_list.apply_inheritance()
        # Link all the contacts stuff
        self.contacts_list.explode(self.contactgroups_list, self.notificationways_list)
        # Remove templates
        self.contacts_list.remove_templates()

    def get_hosts(self):
        # Get standard objects
        self.get_contacts()
        self.get_timeperiods()
        self.get_commands()

        # Host initialization as a template
        self.tpl1 = Host({'name': 'host_tpl', 'check_command': '_internal_host_up', 'register': '0'})

        # Host initialization as depending upon the template
        self.host1 = Host({'host_name': 'host1', 'contacts': 'contact1', 'use': 'host_tpl'})
        # Independent Host
        self.host2 = Host({'host_name': 'host2', 'contacts': 'contact1', 'use': 'host_tpl'})

        # Build a hosts list with the 3 hosts
        self.hosts_list = Hosts([self.tpl1, self.host1, self.host2])

        # Relation Hosts / templates
        self.hosts_list.linkify_templates()

        # Manage inheritance
        self.hosts_list.apply_inheritance()
        # Explode
        self.hosts_list.explode(Hostgroups([]), self.contactgroups_list)
        # Remove templates
        self.hosts_list.remove_templates()

        # Link hosts with timeperiods, commands, ...
        self.hosts_list.linkify(self.timeperiods_list, self.commands_list, self.contacts_list,
                           Realms([]), Resultmodulations([]), Businessimpactmodulations([]),
                           Escalations([]), Hostgroups([]), Triggers([]),
                           CheckModulations([]), MacroModulations([]))

    def test_alignak_object(self):
        """ Test AlignakObject serialization

        :return: None
        """
        self.print_header()

        # AlignakObject initialization with no parameters
        # ---
        item = AlignakObject()
        print("AlignakObject: %s" % item.__dict__)
        # We get an object with an uuid (its only property)
        expected = {'uuid': item.uuid}
        assert expected == item.__dict__

        # Item self-serialize
        serialized_item = item.serialize()
        print("Serialized AlignakObject: %s" % serialized_item)
        # We should get a dictionary with object properties
        expected = {'uuid': item.uuid}
        assert expected == serialized_item

        # Item global object serialize
        serialized_item = serialize(item, no_dump=True)
        print("Serialized AlignakObject: %s" % serialized_item)
        # We should get a dictionary with the object class and a content property
        expected_global = {
            '__sys_python_module__': 'alignak.alignakobject.AlignakObject',
            'content': expected
        }
        assert expected_global == serialized_item
        # Same with a JSON string
        serialized_item = serialize(item, no_dump=False)
        expected_global = '{"content":{"uuid":"%s"},"__sys_python_module__":' \
                          '"alignak.alignakobject.AlignakObject"}' % item.uuid
        assert expected_global == serialized_item

        # AlignakObject initialization with parameters
        # ---
        item = AlignakObject({'foo': 'bar'})
        print("AlignakObject: %s" % item.__dict__)
        # We get an item with an uuid, its properties and the parameters
        expected = {'uuid': item.uuid, 'foo': 'bar'}
        assert expected == item.__dict__

        serialized_item = item.serialize()
        print("Serialized AlignakObject: %s" % serialized_item)
        # Note that parameters that are not defined in properties are filtered!
        # Parameters are not included in the serialization
        expected = {'uuid': item.uuid}
        assert expected == serialized_item

        # Item global object serialize
        serialized_item = serialize(item, no_dump=True)
        print("Serialized AlignakObject: %s" % serialized_item)
        expected_global = {
            '__sys_python_module__': 'alignak.alignakobject.AlignakObject',
            'content': expected
        }
        assert expected_global == serialized_item
        # Same with a JSON string
        serialized_item = serialize(item, no_dump=False)
        expected_global = '{"content":{"uuid":"%s"},"__sys_python_module__":' \
                          '"alignak.alignakobject.AlignakObject"}' % item.uuid
        assert expected_global == serialized_item

    def test_unserialize_alignak_object(self):
        """ Test AlignakObject unserialization

        :return: None
        """
        self.print_header()

        # AlignakObject with no parameters
        # ---
        item = AlignakObject()
        serialized_item = item.serialize()
        # We should get a dictionary with object properties, running_properties and macros
        expected = {'uuid': item.uuid}
        assert expected == serialized_item

        # Unserialize
        unserialized_item = AlignakObject(params=serialized_item, parsing=False)
        assert item == unserialized_item

        # AlignakObject with parameters
        # ---
        item2 = AlignakObject({'foo': 'bar'})
        serialized_item = item2.serialize()
        # Parameters not defined in the properties are not included in the serialization
        expected = {'uuid': item2.uuid}
        assert expected == serialized_item

        # Unserialize
        unserialized_item = AlignakObject(params=serialized_item, parsing=False)
        assert item2.uuid == unserialized_item.uuid
        assert hasattr(item2, 'foo')
        assert not hasattr(unserialized_item, 'foo')
        assert item2 != unserialized_item

    def test_item(self):
        """ Test Item creation / serialization / unserialization...

        :return: None
        """
        self.print_header()

        # Item initialization with no parameters (as default, parsing is True)
        # ---
        item = Item()
        # We get an object with an uuid and its properties and running properties
        # set with their default values
        expected = {'uuid': item.uuid}
        expected.update({
            # Properties
            'use': [], 'display_name': '',
            'definition_order': 100,
            'register': True, 'alias': '',
            'imported_from': 'unknown', 'name': 'unnamed',
            # Runing properties
            'conf_is_correct': True, 'configuration_errors': [], 'configuration_warnings': [],
            'tags': set([]), 'customs': {}, 'plus': {},
        })
        assert expected == item.__dict__
        # tags property is a set and not a list (even if it defined as default: [])
        # Thanks to Property.pythonize the default parameters !
        assert isinstance(item.tags, set)

        # Item is not a template
        assert not item.is_tpl()

        # Once is_correct got called, alias and display_name are
        # valued with the item name if they do no exist
        # As name is not defined, the default value 'unnamed' is used!
        assert item.is_correct()
        expected.update({'alias': item.get_name(), 'display_name': item.get_name()})
        assert expected == item.__dict__

        serialized_item = item.serialize()
        # We should get a dictionary with Item properties and running_properties
        # configuration_errors and configuration_warnings are filtered
        # tags which is a set is now a list
        expected = {
            'uuid': item.uuid,
            # Properties
            'use': [], 'display_name': 'unnamed',
            'definition_order': 100,
            'register': True, 'alias': 'unnamed',
            'imported_from': 'unknown', 'name': 'unnamed',
            # Runing properties
            # filtered!
            # 'configuration_errors': [], 'configuration_warnings': [],
            'conf_is_correct': True,
            # In the serialized data, tags is a list and not a set ...
            'tags': [],
            'customs': {}, 'plus': {},
        }
        assert expected == serialized_item

        # Unserialize the default base Item
        unserialized_item = Item(params=serialized_item, parsing=False)
        # Configuration warnings and errors are not serialized for an Item, as such
        # they cannot be restored when unserializing
        # Object inner properties also ...
        # So those are not present!
        unserialized_item.__dict__.update({
            'tags': set([])
        })
        assert item.__dict__ == unserialized_item.__dict__

        # Item global object serialize
        serialized_item = serialize(item, no_dump=True)
        # We should get a dictionary with Item properties, running_properties and macros
        # configuration_errors and configuration_warnings are filtered
        expected_global = {
            '__sys_python_module__': 'alignak.objects.item.Item',
            'content': expected
        }
        assert expected_global == serialized_item

        # --------------------------------------------------------------------------------------
        # Item initialization with some parameters
        # ---
        item = Item({'use': ['a', 'b'], 'name': 'named_item', 'extra': 'no_property'})
        # We get an object with an uuid and its properties and running properties
        # set with their default values
        expected = {'uuid': item.uuid}
        expected.update({
            # Properties
            'use': ['a', 'b'], 'display_name': '',
            'definition_order': 100,
            'register': True, 'alias': '',
            'imported_from': 'unknown', 'name': 'named_item',
            # Runing properties
            'conf_is_correct': True, 'configuration_errors': [],
            'configuration_warnings': [
                'Guessing the property extra type because it is not in Item object properties'
            ],
            'tags': set([]), 'customs': {}, 'plus': {},
            # Extra properties are also existing
            'extra': 'no_property'
        })
        assert expected == item.__dict__
        # tags property is a set and not a list (even if it defined as default: [])
        # Thanks to Property.pythonize the default parameters !
        assert isinstance(item.tags, set)

        # Item is not a template
        assert not item.is_tpl()

        # Once is_correct got called, alias and display_name are
        # valued with the item name if they do no exist
        # As name is not defined, the default value 'unnamed' is used!
        assert item.is_correct()
        expected.update({'alias': item.get_name(), 'display_name': item.get_name()})
        assert expected == item.__dict__

        serialized_item = item.serialize()
        # We should get a dictionary with Item properties and running_properties
        # configuration_errors and configuration_warnings are filtered
        # tags which is a set is now a list
        expected = {
            'uuid': item.uuid,
            # Properties
            'use': ['a', 'b'], 'display_name': 'named_item',
            'definition_order': 100,
            'register': True, 'alias': 'named_item',
            'imported_from': 'unknown', 'name': 'named_item',
            # Runing properties
            # filtered!
            # 'configuration_errors': [], 'configuration_warnings': [],
            'conf_is_correct': True,
            # In the serialized data, tags is a list and not a set ...
            'tags': [],
            'customs': {}, 'plus': {},
            # Extra properties are also existing
            'extra': 'no_property'
        }
        assert expected == serialized_item

        # Unserialize the default base Item
        unserialized_item = Item(params=serialized_item, parsing=False)
        # Configuration warnings and errors are not serialized for an Item, as such
        # they cannot be restored when unserializing but they are created as they exist
        # in the properties
        unserialized_item.__dict__.update({
            'configuration_errors': [],
            'configuration_warnings': [
                'Guessing the property extra type because it is not in Item object properties'
            ],
        })
        # Object inner properties also ...
        # So those are not present!
        # unserialized_item.__dict__.update({
        #     'tags': set([])
        # })
        assert item.__dict__ == unserialized_item.__dict__

        # Item global object serialize
        serialized_item = serialize(item, no_dump=True)
        # We should get a dictionary with Item properties, running_properties and macros
        # configuration_errors and configuration_warnings are filtered
        expected_global = {
            '__sys_python_module__': 'alignak.objects.item.Item',
            'content': expected
        }
        assert expected_global == serialized_item

    def test_items_list(self):
        """ Test Items creation / serialization / unserialization...

        :return: None
        """
        self.print_header()

        # Item initialization with no parameters
        item1 = Item()

        # Item initialization with no parameters
        item2 = Item()

        # Item initialization with parameters
        item3 = Item({'foo': 'bar', 'imported_from': 'file.cfg'}, debug=True)

        # Item initialization with parameters (item is detected as a template)
        item4 = Item({'name': 'item_tpl', 'register': '0'}, debug=True)

        # Build a list with the 3 items
        items_list = Items([item1, item2, item3, item4])
        # We get an objects list
        # Note that the items index is indexed with element uuid because Item is an element
        # that do not have a name property. As such, all items are `unnamed` ...
        expected = {
            'conf_is_correct': True, 'configuration_errors': [], 'configuration_warnings': [],
            # As objects are not named, internally use their uuid as name ...
            'name_to_item': {
                item1.uuid: item1,
                item2.uuid: item2,
                item3.uuid: item3,
            },
            'name_to_template': {
                'item_tpl': item4
            },
            'templates': {
                item4.uuid: item4
            },
            'items': {
                item1.uuid: item1,
                item2.uuid: item2,
                item3.uuid: item3,
            }
        }
        print("Items list: %s" % items_list)
        assert expected == items_list.__dict__

        serialized_items_list = items_list.serialize()
        # Only the items, the templates are not serialized...
        expected = {
            item1.uuid: item1.serialize(),
            item2.uuid: item2.serialize(),
            item3.uuid: item3.serialize(),
        }
        print("Serialized Item: %s" % serialized_items_list)
        assert expected == serialized_items_list

    @unittest.skip("Disabled because of AutoSlots in objects")
    def test_commands_list(self):
        """ Test Commands serialization / unserialization...

        :return: None
        """
        self.print_header()

        # Command initialization as a template
        tpl1 = Command({'name': 'command_tpl',
                        'command_line': 'command.sh', 'register': '0'},
                       parsing=True)
        assert tpl1.is_tpl()

        # Command initialization as depending upon the template
        command1 = Command({'command_name': 'command1', 'use': 'command_tpl'},
                           parsing=True)
        assert not command1.is_tpl()
        expected = {'uuid': command1.uuid}
        expected.update({
            # Item Properties
            'use': ['command_tpl'], 'display_name': '',
            'definition_order': 100,
            'register': True, 'alias': '',
            'imported_from': 'unknown', 'name': 'unnamed',
            # Item Runing properties
            'conf_is_correct': True, 'configuration_errors': [], 'configuration_warnings': [],
            'tags': set([]), 'customs': {}, 'plus': {},
            # Parameters
            'command_name': 'command1',
            # Not provided parameters are valued with the default values
            'command_line': '', 'poller_tag': 'None', 'reactionner_tag': 'None',
            'timeout': -1,
            'module_type': 'fork',
            'enable_environment_macros': False
        })
        assert expected == command1.__dict__

        # Independent command
        command2 = Command({'command_name': 'command2',
                            'command_line': '_internal_host_up',
                            'timeout': 10,
                            'imported_from': 'file.cfg'})
        assert not command2.is_tpl()
        # We get an item with an uuid, its properties, running properties and macros PLUS
        # the parameters and the inner defined properties
        expected = {'uuid': command2.uuid}
        expected.update({
            # Item Properties
            'use': [], 'display_name': '',
            'definition_order': 100,
            'register': True, 'alias': '',
            'imported_from': 'file.cfg', 'name': 'unnamed',
            # Item Runing properties
            'conf_is_correct': True, 'configuration_errors': [], 'configuration_warnings': [],
            'tags': set([]), 'customs': {}, 'plus': {},
            # Parameters
            'command_name': 'command2',
            # Not provided parameters are valued with the default values
            'command_line': '_internal_host_up', 'poller_tag': 'None', 'reactionner_tag': 'None',
            'timeout': 10,
            # Specific for internal commands...
            'module_type': 'internal',
            'enable_environment_macros': False
        })
        assert expected == command2.__dict__

        # Build a commands list with the 3 commands
        commands_list = Commands([tpl1, command1, command2])
        expected = {
            'conf_is_correct': True, 'configuration_errors': [], 'configuration_warnings': [],
            'name_to_item': {
                'command1': command1,
                'command2': command2
            },
            'name_to_template': {
                'command_tpl': tpl1
            },
            'templates': {
                tpl1.uuid: tpl1,
            },
            'items': {
                command1.uuid: command1,
                command2.uuid: command2,
            }
        }
        assert expected == commands_list.__dict__

        # No templates in the items list, only the real items
        serialized_commands_list = commands_list.serialize()
        expected = {
            command1.uuid: command1.serialize(),
            command2.uuid: command2.serialize(),
        }
        assert expected == serialized_commands_list

        # Relation commands / templates
        # This is not used by Alignak for Command objects but it is possible!
        commands_list.linkify_templates()
        assert command1.tags == ['command_tpl']
        assert command2.tags == []

        # Search in the list
        for command in commands_list:
            assert isinstance(command, Command)

        assert commands_list.find_by_name('command2') == command2
        assert commands_list.find_tpl_by_name('command_tpl') == tpl1

    def test_contacts_list(self):
        """ Test Contacts serialization / unserialization...

        :return: None
        """
        self.print_header()

        # Contact initialization as a template
        tpl1 = Contact({'name': 'contact_tpl',
                        'host_notifications_enabled': True,
                        'host_notification_period': '24x7',
                        'host_notification_options': ['r'],
                        'host_notification_commands': ['email'],
                        'register': '0'})
        assert tpl1.is_tpl()

        # Contact initialization as depending upon the template
        contact1 = Contact({'contact_name': 'contact1', 'use': 'contact_tpl'})
        assert not contact1.is_tpl()
        expected = {'uuid': contact1.uuid}
        expected.update({
            # Item Properties
            'use': ['contact_tpl'], 'display_name': '',
            'definition_order': 100,
            'register': True, 'alias': '',
            'imported_from': 'unknown', 'name': 'unnamed',
            # Item Runing properties
            'conf_is_correct': True, 'configuration_errors': [], 'configuration_warnings': [],
            'tags': set([]), 'customs': {}, 'plus': {},

            'contact_name': 'contact1',

            'modified_attributes': 0L,
            'modified_host_attributes': 0L, 'modified_service_attributes': 0L,

            'broks': [],
            'contactgroups': [],
            'in_scheduled_downtime': False,
            'downtimes': [],
            'notificationways': [],

            'host_notifications_enabled': True,
            # 'host_notification_period': '',
            'host_notification_options': [],
            'host_notification_commands': [],

            'service_notifications_enabled': True,
            # 'service_notification_period': '',
            'service_notification_options': [],
            'service_notification_commands': [],

            'min_business_impact': 0,

            'address2': 'none', 'address1': 'none', 'address3': 'none',
            'address4': 'none', 'address5': 'none', 'address6': 'none',
            'email': 'none', 'pager': 'none',
            # WebUI only properties!
            'expert': False, 'is_admin': False,
            'can_submit_commands': False,
            'password': 'NOPASSWORDSET',
        })
        assert expected == contact1.__dict__

        # Independent contact
        contact2 = Contact({'contact_name': 'contact2', 'imported_from': 'file.cfg'})
        assert not contact2.is_tpl()
        # We get an item with an uuid, its properties, running properties and macros PLUS
        # the parameters and the inner defined properties
        expected = {'uuid': contact2.uuid}
        expected.update({
            # Item Properties
            'use': [], 'display_name': '',
            'definition_order': 100,
            'register': True, 'alias': '',
            'imported_from': 'file.cfg', 'name': 'unnamed',
            # Item Runing properties
            'conf_is_correct': True, 'configuration_errors': [], 'configuration_warnings': [],
            'tags': set([]), 'customs': {}, 'plus': {},

            'contact_name': 'contact2',

            'modified_attributes': 0L,
            'modified_host_attributes': 0L, 'modified_service_attributes': 0L,

            'broks': [],
            'contactgroups': [],
            'in_scheduled_downtime': False,
            'downtimes': [],
            'notificationways': [],

            'host_notifications_enabled': True,
            # 'host_notification_period': '',
            'host_notification_options': [],
            'host_notification_commands': [],

            'service_notifications_enabled': True,
            # 'service_notification_period': '',
            'service_notification_options': [],
            'service_notification_commands': [],
            'min_business_impact': 0,

            'address2': 'none', 'address1': 'none', 'address3': 'none',
            'address4': 'none', 'address5': 'none', 'address6': 'none',
            'email': 'none', 'pager': 'none',
            # WebUI only properties!
            'expert': False, 'is_admin': False,
            'can_submit_commands': False,
            'password': 'NOPASSWORDSET',
        })
        assert expected == contact2.__dict__

        # Build a contacts list with the 3 contacts
        contacts_list = Contacts([tpl1, contact1, contact2])
        expected = {
            'conf_is_correct': True, 'configuration_errors': [], 'configuration_warnings': [],
            'name_to_item': {
                'contact1': contact1,
                'contact2': contact2
            },
            'name_to_template': {
                'contact_tpl': tpl1
            },
            'templates': {
                tpl1.uuid: tpl1,
            },
            'items': {
                contact1.uuid: contact1,
                contact2.uuid: contact2,
            }
        }
        print("Item: %s" % contacts_list)
        assert expected == contacts_list.__dict__

        # No templates in the items list, only the real items
        serialized_contacts_list = contacts_list.serialize()
        expected = {
            contact1.uuid: contact1.serialize(),
            contact2.uuid: contact2.serialize(),
        }
        print("Serialized Item: %s" % serialized_contacts_list)
        assert expected == serialized_contacts_list

        # Relation contacts / templates
        contacts_list.linkify_templates()
        assert contact1.tags == ['contact_tpl']
        assert contact2.tags == []

        # Apply inheritance from templates
        assert contact1.host_notifications_enabled is True
        # assert contact1.host_notification_period == ''
        assert contact1.host_notification_options == []
        assert contact1.host_notification_commands == []
        contacts_list.apply_inheritance()
        assert contact1.host_notifications_enabled is True
        # assert contact1.host_notification_period == '24x7'
        assert contact1.host_notification_options == ['r']
        assert contact1.host_notification_commands == ['email']

        # Search in the list
        for contact in contacts_list:
            assert isinstance(contact, Contact)

        assert contacts_list.find_by_name('contact2') == contact2
        assert contacts_list.find_tpl_by_name('contact_tpl') == tpl1

    def test_contacts_group(self):
        """ Test Contacts / Contacts groups serialization / unserialization...

        :return: None
        """
        self.print_header()

        # Get default contacts
        self.get_contacts()

        # Create templates links
        self.contactgroups_list.linkify_templates()
        # Manage inheritance
        self.contactgroups_list.apply_inheritance()
        # Link all the contacts stuff
        self.contactgroups_list.explode(self.contacts_list)
        # Set default values
        # self.contacts_list.fill_default()
        # Remove templates
        self.contactgroups_list.remove_templates()
        # Create objects links
        self.contactgroups_list.linkify(self.contacts_list)

        # Search in the lists (contacts / contacts groups)
        for contactgroup in self.contactgroups_list:
            assert isinstance(contactgroup, Contactgroup)
            print("Contacts group: %s" % contactgroup.__dict__)
        assert self.contactgroups_list.find_by_name('contacts_group') == self.contacts_group
        # Group members (groups)
        # assert self.contacts_group.contactgroup_members == []
        # Group members (contacts)
        assert self.contacts_group.members == [self.contact1.uuid]
        # assert self.contacts_group.unknown_members == []

        # Search in the lists (notification ways)
        for nw in self.notificationways_list:
            assert isinstance(nw, NotificationWay)
            print("NW: %s" % nw.__dict__)
        # Found empty notification ways (default created!)
        nw1 = self.notificationways_list.find_by_name('contact1_inner_notificationway')
        assert nw1.host_notifications_enabled == True
        assert nw1.host_notification_commands == []
        # assert nw1.host_notification_period == ''
        assert nw1.host_notification_options == []
        assert nw1.service_notifications_enabled == True
        assert nw1.service_notification_commands == []
        # assert nw1.service_notification_period == ''
        assert nw1.service_notification_options == []
        nw2 = self.notificationways_list.find_by_name('contact2_inner_notificationway')

        # Contacts notification ways
        assert self.contact1.notificationways == [nw1.get_name()]
        assert self.contact2.notificationways == []

        self.contacts_list.linkify_with_notificationways(self.notificationways_list)

        # Contacts notification ways
        assert self.contact1.notificationways == [nw1.uuid]
        assert self.contact2.notificationways == []

    def test_scheduling_item_list(self):
        """ Test SchedulingItem serialization / unserialization...

        :return: None
        """
        self.print_header()

        # SchedulingItem initialization
        sched_item1 = SchedulingItem(parsing=True, debug=True)
        assert not sched_item1.is_tpl()
        # We get an item with an uuid, its properties, running properties and macros PLUS
        # the parameters and the inner defined properties
        expected = {'uuid': sched_item1.uuid}
        expected.update({
            # Item Properties
            'use': [], 'display_name': '',
            'definition_order': 100,
            'register': True, 'alias': '',
            'imported_from': 'unknown', 'name': 'unnamed',
            # Item Runing properties
            'conf_is_correct': True, 'configuration_errors': [], 'configuration_warnings': [],
            'tags': set([]), 'customs': {}, 'plus': {},

            'acknowledgement': None,
            'acknowledgement_type': 1,
            'act_depend_of': [],
            'act_depend_of_me': [],
            'action_url': '',
            'actions': [],
            'active_checks_enabled': True,
            'attempt': 0,
            'broks': [],
            'business_impact': 2,
            'business_impact_modulations': [],
            'business_rule': None,
            'business_rule_downtime_as_ack': False,
            'business_rule_host_notification_options': [],
            'business_rule_output_template': '',
            'business_rule_service_notification_options': [],
            'business_rule_smart_notifications': False,
            'check_command': '',
            'check_flapping_recovery_notification': True,
            'check_freshness': False,
            'check_interval': 0,
            'check_period': '',
            'check_type': 0,
            'checkmodulations': [],
            'checks_in_progress': [],
            'child_dependencies': set([]),
            'chk_depend_of': [],
            'chk_depend_of_me': [],
            'comments': [],
            'contact_groups': [],
            'contacts': [],
            'current_notification_id': 0,
            'current_notification_number': 0,
            'custom_views': [],
            'downtimes': [],
            'duration_sec': 0,
            'early_timeout': 0,
            'end_time': 0,
            'escalations': [],
            'event_handler': '',
            'event_handler_enabled': False,
            'execution_time': 0.0,
            'failure_prediction_enabled': False,
            'first_notification_delay': 0,
            'flap_detection_enabled': True,
            'flapping_changes': [],
            'flapping_comment_id': 0,
            'freshness_threshold': 3600,
            'got_business_rule': False,
            'has_been_checked': 0,
            'high_flap_threshold': 50,
            'icon_image': '',
            'icon_image_alt': '',
            'icon_set': '',
            'impacts': [],
            'in_checking': False,
            'in_hard_unknown_reach_phase': False,
            'in_maintenance': -1,
            'in_scheduled_downtime': False,
            'in_scheduled_downtime_during_last_check': False,
            'initial_state': 'o',
            'is_flapping': False,
            'is_impact': False,
            'is_problem': False,
            'labels': [],
            'last_check_command': '',
            'last_chk': 0,
            'last_event_id': 0,
            'last_hard_state': 'PENDING',
            'last_hard_state_change': 0.0,
            'last_hard_state_id': 0,
            'last_notification': 0.0,
            'last_perf_data': '',
            'last_problem_id': 0,
            'last_snapshot': 0,
            'last_state': 'PENDING',
            'last_state_change': 0.0,
            'last_state_id': 0,
            'last_state_type': 'HARD',
            'last_state_update': 0.0,
            'latency': 0.0,
            'long_output': '',
            'low_flap_threshold': 25,
            'macromodulations': [],
            'maintenance_period': '',
            'max_check_attempts': 1,
            'modified_attributes': 0,
            'my_own_business_impact': -1,
            'next_chk': 0,
            'notes': '',
            'notes_url': '',
            'notification_interval': 60,
            'notifications_enabled': True,
            'notifications_in_progress': {},
            'notified_contacts': set([]),
            'output': '',
            'parent_dependencies': set([]),
            'passive_checks_enabled': True,
            'pending_flex_downtime': 0,
            'percent_state_change': 0.0,
            'perf_data': '',
            'poller_tag': 'None',
            'problem_has_been_acknowledged': False,
            'process_perf_data': True,
            'processed_business_rule': '',
            'reactionner_tag': 'None',
            'realm': '',
            'resultmodulations': [],
            'retry_interval': 0,
            'return_code': 0,
            's_time': 0.0,
            'scheduled_downtime_depth': 0,
            'should_be_scheduled': 1,
            'snapshot_command': None,
            'snapshot_enabled': False,
            'snapshot_interval': 5,
            'snapshot_period': None,
            'source_problems': [],
            'stalking_options': [],
            'start_time': 0,
            'state_before_impact': 'PENDING',
            'state_changed_since_impact': False,
            'state_id': 0,
            'state_id_before_impact': 0,
            'state_type': 'HARD',
            'state_type_id': 0,
            'time_to_orphanage': 300,
            'timeout': 0,
            'topology_change': False,
            'trending_policies': [],
            'trigger_broker_raise_enabled': False,
            'trigger_name': '',
            'triggers': [],
            'u_time': 0.0,
            'was_in_hard_unknown_reach_phase': False
        })
        # Those 2 running properties are not present!!! This is because it exist some class
        # variables that are used to globally set a number ... it is not probably important ;)
        # expected.update({'current_event_id': 0, 'current_problem_id': 0})
        assert expected == sched_item1.__dict__

        serialized_item = sched_item1.serialize()
        # Some specific variables are serialized as lists and not sets!
        expected.update({
            'child_dependencies': [], 'parent_dependencies': [], 'notified_contacts': [], 'tags': [],
            # Ignore those ignored 2 variables :/ see before!
            # 'current_event_id': 0, 'current_problem_id': 0
        })
        # Specific and inner properties are filtered
        serialized_item.update({
            'configuration_errors': [], 'configuration_warnings': [], 'customs': {}, 'plus': {},
            # 'check_command': None, 'current_event_id': 0, 'current_problem_id': 0
        })
        serialized_item.pop('current_event_id')
        serialized_item.pop('current_problem_id')
        # print("Serialized Item: %s" % serialized_item)
        assert expected == serialized_item

        # Unserialize the default base SchedulingItem
        unserialized_item = SchedulingItem(params=serialized_item, parsing=False)
        # Configuration warnings and errors are not serialized for an Item, as such
        # they cannot be restored when unserializing
        unserialized_item.__dict__.update({
            'configuration_errors': [], 'configuration_warnings': [],
            'child_dependencies': set([]), 'parent_dependencies': set([]), 'notified_contacts': set([])
        })
        assert sched_item1.__dict__ == unserialized_item.__dict__

        # Build a sched_items list
        sched_items_list = SchedulingItems([sched_item1])
        expected = {
            'conf_is_correct': True, 'configuration_errors': [], 'configuration_warnings': [],
            'name_to_item': {
                sched_item1.uuid: sched_item1,
            },
            'name_to_template': {
            },
            'templates': {
            },
            'items': {
                sched_item1.uuid: sched_item1,
            }
        }
        print("SchedulingItems list: %s" % sched_items_list)
        assert expected == sched_items_list.__dict__

        # No templates in the items list, only the real items
        serialized_sched_items_list = sched_items_list.serialize()
        expected = {
            sched_item1.uuid: sched_item1.serialize(),
        }
        assert expected == serialized_sched_items_list

    @unittest.skip("Disabled because of AutoSlots in objects")
    def test_hosts_list(self):
        """ Test Hosts serialization / unserialization...

        :return: None
        """
        self.print_header()

        # Host initialization as a template
        tpl1 = Host({'name': 'host_tpl', 'check_command': 'command1', 'register': '0'})
        assert tpl1.definition_order == 100
        assert tpl1.is_tpl()

        # Host initialization as depending upon the template
        host1 = Host({'host_name': 'host1', 'contacts': 'contact1', 'use': 'host_tpl'})
        # We get an item with an uuid, its properties, running properties and macros PLUS
        # the parameters and the inner defined properties
        expected = {'uuid': host1.uuid}
        expected.update({
            # Item Properties
            'use': ['host_tpl'], 'display_name': '',
            'definition_order': 100,
            'register': True, 'alias': '',
            'imported_from': 'unknown', 'name': 'unnamed',
            # Item Runing properties
            'conf_is_correct': True, 'configuration_errors': [], 'configuration_warnings': [],
            'tags': set([]), 'customs': {}, 'plus': {},

            'host_name': 'host1',

            '2d_coords': '',
            '3d_coords': '',
            'acknowledgement': None,
            'acknowledgement_type': 1,
            'act_depend_of': [],
            'act_depend_of_me': [],
            'action_url': '',
            'actions': [],
            'active_checks_enabled': True,
            'address': '',
            'address6': '',
            'attempt': 0,
            'broks': [],
            'business_impact': 2,
            'business_impact_modulations': [],
            'business_rule': None,
            'business_rule_downtime_as_ack': False,
            'business_rule_host_notification_options': [],
            'business_rule_output_template': '',
            'business_rule_service_notification_options': [],
            'business_rule_smart_notifications': False,
            'check_command': '',
            'check_period': '',
            'check_flapping_recovery_notification': True,
            'check_freshness': False,
            'check_interval': 0,
            'check_type': 0,
            'checkmodulations': [],
            'checks_in_progress': [],
            'child_dependencies': set([]),
            'chk_depend_of': [],
            'chk_depend_of_me': [],
            'comments': [],
            'contact_groups': [],
            'contacts': ['contact1'],
            'current_notification_id': 0,
            'current_notification_number': 0,
            'custom_views': [],
            'downtimes': [],
            'duration_sec': 0,
            'early_timeout': 0,
            'end_time': 0,
            'escalations': [],
            'event_handler': '',
            'event_handler_enabled': False,
            'execution_time': 0.0,
            'failure_prediction_enabled': False,
            'first_notification_delay': 0,
            'flap_detection_enabled': True,
            'flap_detection_options': [u'o', u'd', u'x'],
            'flapping_changes': [],
            'flapping_comment_id': 0,
            'freshness_state': 'd',
            'freshness_threshold': 3600,
            'got_business_rule': False,
            'got_default_realm': False,
            'has_been_checked': 0,
            'high_flap_threshold': 50,
            'hostgroups': [],
            'icon_image': '',
            'icon_image_alt': '',
            'icon_set': '',
            'impacts': [],
            'in_checking': False,
            'in_hard_unknown_reach_phase': False,
            'in_maintenance': -1,
            'in_scheduled_downtime': False,
            'in_scheduled_downtime_during_last_check': False,
            'initial_state': 'o',
            'is_flapping': False,
            'is_impact': False,
            'is_problem': False,
            'labels': [],
            'last_check_command': '',
            'last_chk': 0,
            'last_event_id': 0,
            'last_hard_state': 'PENDING',
            'last_hard_state_change': 0.0,
            'last_hard_state_id': 0,
            'last_notification': 0.0,
            'last_perf_data': '',
            'last_problem_id': 0,
            'last_snapshot': 0,
            'last_state': 'PENDING',
            'last_state_change': 0.0,
            'last_state_id': 0,
            'last_state_type': 'HARD',
            'last_state_update': 0.0,
            'last_time_down': 0,
            'last_time_unreachable': 0,
            'last_time_up': 0,
            'latency': 0.0,
            'long_output': '',
            'low_flap_threshold': 25,
            'macromodulations': [],
            'maintenance_period': '',
            'max_check_attempts': 1,
            'modified_attributes': 0,
            'my_own_business_impact': -1,
            'next_chk': 0,
            'notes': '',
            'notes_url': '',
            'notification_interval': 60,
            'notification_options': [u'd', u'x', u'r', u'f', u's'],
            'notifications_enabled': True,
            'notifications_in_progress': {},
            'notified_contacts': set([]),
            'obsess_over_host': False,
            'output': '',
            'pack_id': -1,
            'parent_dependencies': set([]),
            'parents': [],
            'passive_checks_enabled': True,
            'pending_flex_downtime': 0,
            'percent_state_change': 0.0,
            'perf_data': '',
            'poller_tag': 'None',
            'problem_has_been_acknowledged': False,
            'process_perf_data': True,
            'processed_business_rule': '',
            'reactionner_tag': 'None',
            'realm': '',
            'realm_name': '',
            'resultmodulations': [],
            'retry_interval': 0,
            'return_code': 0,
            's_time': 0.0,
            'scheduled_downtime_depth': 0,
            'service_overrides': [],
            'service_excludes': [],
            'service_includes': [],
            'services': [],
            'should_be_scheduled': 1,
            'snapshot_command': None,
            'snapshot_criteria': [u'd', u'x'],
            'snapshot_enabled': False,
            'snapshot_interval': 5,
            'snapshot_period': None,
            'source_problems': [],
            'stalking_options': [],
            'start_time': 0,
            'state': 'UP',
            'state_before_hard_unknown_reach_phase': 'UP',
            'state_before_impact': 'PENDING',
            'state_changed_since_impact': False,
            'state_id': 0,
            'state_id_before_impact': 0,
            'state_type': 'HARD',
            'state_type_id': 0,
            'statusmap_image': '',
            'time_to_orphanage': 300,
            'timeout': 0,
            'topology_change': False,
            'trending_policies': [],
            'trigger_broker_raise_enabled': False,
            'trigger_name': '',
            'triggers': [],
            'u_time': 0.0,
            'vrml_image': '',
            'was_in_hard_unknown_reach_phase': False
        })
        assert expected == host1.__dict__

        # Independent Host
        host2 = Host({'host_name': 'host2',
                      'contacts': 'contact1',
                      'check_command': '_internal_host_up',
                     'imported_from': 'file.cfg'})
        # We get an item with an uuid, its properties, running properties and macros PLUS
        # the parameters and the inner defined properties
        expected = {'uuid': host2.uuid}
        expected.update({
            # Item Properties
            'use': [], 'display_name': '',
            'definition_order': 100,
            'register': True, 'alias': '',
            'imported_from': 'file.cfg', 'name': 'unnamed',
            # Item Runing properties
            'conf_is_correct': True, 'configuration_errors': [], 'configuration_warnings': [],
            'tags': set([]), 'customs': {}, 'plus': {},

            'host_name': 'host2',

            '2d_coords': '',
            '3d_coords': '',
            'acknowledgement': None,
            'acknowledgement_type': 1,
            'act_depend_of': [],
            'act_depend_of_me': [],
            'action_url': '',
            'actions': [],
            'active_checks_enabled': True,
            'address': '',
            'address6': '',
            'attempt': 0,
            'broks': [],
            'business_impact': 2,
            'business_impact_modulations': [],
            'business_rule': None,
            'business_rule_downtime_as_ack': False,
            'business_rule_host_notification_options': [],
            'business_rule_output_template': '',
            'business_rule_service_notification_options': [],
            'business_rule_smart_notifications': False,
            'check_command': '_internal_host_up',
            'check_period': '',
            'check_flapping_recovery_notification': True,
            'check_freshness': False,
            'check_interval': 0,
            'check_type': 0,
            'checkmodulations': [],
            'checks_in_progress': [],
            'child_dependencies': set([]),
            'chk_depend_of': [],
            'chk_depend_of_me': [],
            'comments': [],
            'contact_groups': [],
            'contacts': ['contact1'],
            'current_notification_id': 0,
            'current_notification_number': 0,
            'custom_views': [],
            'downtimes': [],
            'duration_sec': 0,
            'early_timeout': 0,
            'end_time': 0,
            'escalations': [],
            'event_handler': '',
            'event_handler_enabled': False,
            'execution_time': 0.0,
            'failure_prediction_enabled': False,
            'first_notification_delay': 0,
            'flap_detection_enabled': True,
            'flap_detection_options': [u'o', u'd', u'x'],
            'flapping_changes': [],
            'flapping_comment_id': 0,
            'freshness_state': 'd',
            'freshness_threshold': 3600,
            'got_business_rule': False,
            'got_default_realm': False,
            'has_been_checked': 0,
            'high_flap_threshold': 50,
            'hostgroups': [],
            'icon_image': '',
            'icon_image_alt': '',
            'icon_set': '',
            'impacts': [],
            'in_checking': False,
            'in_hard_unknown_reach_phase': False,
            'in_maintenance': -1,
            'in_scheduled_downtime': False,
            'in_scheduled_downtime_during_last_check': False,
            'initial_state': 'o',
            'is_flapping': False,
            'is_impact': False,
            'is_problem': False,
            'labels': [],
            'last_check_command': '',
            'last_chk': 0,
            'last_event_id': 0,
            'last_hard_state': 'PENDING',
            'last_hard_state_change': 0.0,
            'last_hard_state_id': 0,
            'last_notification': 0.0,
            'last_perf_data': '',
            'last_problem_id': 0,
            'last_snapshot': 0,
            'last_state': 'PENDING',
            'last_state_change': 0.0,
            'last_state_id': 0,
            'last_state_type': 'HARD',
            'last_state_update': 0.0,
            'last_time_down': 0,
            'last_time_unreachable': 0,
            'last_time_up': 0,
            'latency': 0.0,
            'long_output': '',
            'low_flap_threshold': 25,
            'macromodulations': [],
            'maintenance_period': '',
            'max_check_attempts': 1,
            'modified_attributes': 0,
            'my_own_business_impact': -1,
            'next_chk': 0,
            'notes': '',
            'notes_url': '',
            'notification_interval': 60,
            'notification_options': [u'd', u'x', u'r', u'f', u's'],
            'notifications_enabled': True,
            'notifications_in_progress': {},
            'notified_contacts': set([]),
            'obsess_over_host': False,
            'output': '',
            'pack_id': -1,
            'parent_dependencies': set([]),
            'parents': [],
            'passive_checks_enabled': True,
            'pending_flex_downtime': 0,
            'percent_state_change': 0.0,
            'perf_data': '',
            'poller_tag': 'None',
            'problem_has_been_acknowledged': False,
            'process_perf_data': True,
            'processed_business_rule': '',
            'reactionner_tag': 'None',
            'realm': '',
            'realm_name': '',
            'resultmodulations': [],
            'retry_interval': 0,
            'return_code': 0,
            's_time': 0.0,
            'scheduled_downtime_depth': 0,
            'service_overrides': [],
            'service_excludes': [],
            'service_includes': [],
            'services': [],
            'should_be_scheduled': 1,
            'snapshot_command': None,
            'snapshot_criteria': [u'd', u'x'],
            'snapshot_enabled': False,
            'snapshot_interval': 5,
            'snapshot_period': None,
            'source_problems': [],
            'stalking_options': [],
            'start_time': 0,
            'state': 'UP',
            'state_before_hard_unknown_reach_phase': 'UP',
            'state_before_impact': 'PENDING',
            'state_changed_since_impact': False,
            'state_id': 0,
            'state_id_before_impact': 0,
            'state_type': 'HARD',
            'state_type_id': 0,
            'statusmap_image': '',
            'time_to_orphanage': 300,
            'timeout': 0,
            'topology_change': False,
            'trending_policies': [],
            'trigger_broker_raise_enabled': False,
            'trigger_name': '',
            'triggers': [],
            'u_time': 0.0,
            'vrml_image': '',
            'was_in_hard_unknown_reach_phase': False
        })
        assert expected == host2.__dict__

        # Build a hosts list with the 3 hosts
        hosts_list = Hosts([tpl1, host1, host2])
        expected = {
            'conf_is_correct': True, 'configuration_errors': [], 'configuration_warnings': [],
            'name_to_item': {
                'host1': host1,
                'host2': host2
            },
            'name_to_template': {
                'host_tpl': tpl1
            },
            'templates': {
                tpl1.uuid: tpl1,
            },
            'items': {
                host1.uuid: host1,
                host2.uuid: host2,
            }
        }
        print("Hosts list: %s" % hosts_list)
        assert expected == hosts_list.__dict__

        # No templates in the items list, only the real items
        serialized_hosts_list = hosts_list.serialize()
        expected = {
            host1.uuid: host1.serialize(),
            host2.uuid: host2.serialize(),
        }
        # print("Serialized hosts list: %s" % serialized_hosts_list)
        assert expected == serialized_hosts_list

        # Relation Hosts / templates
        hosts_list.linkify_templates()
        assert host1.tags == ['host_tpl']
        assert host2.tags == []

        # Get standard objects
        self.get_contacts()
        self.get_timeperiods()
        self.get_commands()

        # Search in the list
        for host in hosts_list:
            assert isinstance(host, Host)
        assert hosts_list.find_by_name('host1') == host1
        assert hosts_list.find_by_name('host2') == host2
        assert hosts_list.find_tpl_by_name('host_tpl') == tpl1

        # Host contacts, commands, ... still with default values and not yet linked!
        assert host1.contacts == ['contact1']
        assert host1.check_command == ''
        assert host2.check_command == '_internal_host_up'

        # Manage inheritance
        hosts_list.apply_inheritance()
        # Explode
        hosts_list.explode(Hostgroups([]), Contactgroups([]))
        # Set default values
        # hosts_list.fill_default()
        # Remove templates
        hosts_list.remove_templates()

        # Link hosts with timeperiods, commands, ...
        hosts_list.linkify(self.timeperiods_list, self.commands_list, self.contacts_list,
                           Realms([]), Resultmodulations([]), Businessimpactmodulations([]),
                           Escalations([]), Hostgroups([]), Triggers([]),
                           CheckModulations([]), MacroModulations([]))

        # Search in the list
        for host in hosts_list:
            assert isinstance(host, Host)
        assert hosts_list.find_by_name('host1') == host1
        assert hosts_list.find_by_name('host2') == host2
        assert hosts_list.find_tpl_by_name('host_tpl') == tpl1

        # Host contacts, commands, ...
        # Now we have real objects
        assert host1.contacts == [self.contact1.uuid]
        assert isinstance(host1.check_command, CommandCall)
        assert host1.check_command.command == self.command1
        assert isinstance(host2.check_command, CommandCall)
        assert host2.check_command.call == '_internal_host_up'

        # Search in the list
        for host in hosts_list:
            assert isinstance(host, Host)
        assert hosts_list.find_by_name('host1') == host1
        assert hosts_list.find_by_name('host2') == host2
        assert hosts_list.find_tpl_by_name('host_tpl') == tpl1

    @unittest.skip("Disabled because of AutoSlots in objects")
    def test_services_list(self):
        """ Test Hosts serialization / unserialization...

        :return: None
        """
        self.print_header()

        # Service initialization as a template
        tpl1 = Service({'name': 'service_tpl',
                        'check_command': 'command1',
                        'host_name': 'host1',
                        'register': '0'})
        assert tpl1.definition_order == 100
        assert tpl1.is_tpl()

        # Service initialization as depending upon the template
        service1 = Service({'service_description': 'service1',
                            'contacts': 'contact1',
                            'check_period': '24x7',
                            'use': 'service_tpl'})
        # We get an item with an uuid, its properties, running properties and macros PLUS
        # the parameters and the inner defined properties
        expected = {'uuid': service1.uuid}
        expected.update({
            # Item Properties
            'use': ['service_tpl'], 'display_name': '',
            'definition_order': 100,
            'register': True, 'alias': '',
            'imported_from': 'unknown', 'name': 'unnamed',
            # Item Runing properties
            'conf_is_correct': True, 'configuration_errors': [], 'configuration_warnings': [],
            'tags': set([]), 'customs': {}, 'plus': {},

            'service_description': 'service1',

            'acknowledgement': None,
            'acknowledgement_type': 1,
            'act_depend_of': [],
            'act_depend_of_me': [],
            'action_url': '',
            'actions': [],
            'active_checks_enabled': True,
            'aggregation': '',
            'attempt': 0,
            'broks': [],
            'business_impact': 2,
            'business_impact_modulations': [],
            'business_rule': None,
            'business_rule_downtime_as_ack': False,
            'business_rule_host_notification_options': [],
            'business_rule_output_template': '',
            'business_rule_service_notification_options': [],
            'business_rule_smart_notifications': False,
            'check_command': '',
            'check_flapping_recovery_notification': True,
            'check_freshness': False,
            'check_interval': 0,
            'check_period': '24x7',
            'check_type': 0,
            'checkmodulations': [],
            'checks_in_progress': [],
            'child_dependencies': set([]),
            'chk_depend_of': [],
            'chk_depend_of_me': [],
            'comments': [],
            'contact_groups': [],
            'contacts': ['contact1'],
            'current_notification_id': 0,
            'current_notification_number': 0,
            'custom_views': [],
            'default_value': '',
            'downtimes': [],
            'duplicate_foreach': '',
            'duration_sec': 0,
            'early_timeout': 0,
            'end_time': 0,
            'escalations': [],
            'event_handler': '',
            'event_handler_enabled': False,
            'execution_time': 0.0,
            'failure_prediction_enabled': False,
            'first_notification_delay': 0,
            'flap_detection_enabled': True,
            'flap_detection_options': ['o', 'w', 'c', 'u', 'x'],
            'flapping_changes': [],
            'flapping_comment_id': 0,
            'freshness_state': 'x',
            'freshness_threshold': 3600,
            'got_business_rule': False,
            'has_been_checked': 0,
            'high_flap_threshold': 50,
            'host': None,
            'host_dependency_enabled': True,
            'hostgroup_name': '',
            'icon_image': '',
            'icon_image_alt': '',
            'icon_set': '',
            'impacts': [],
            'in_checking': False,
            'in_hard_unknown_reach_phase': False,
            'in_maintenance': -1,
            'in_scheduled_downtime': False,
            'in_scheduled_downtime_during_last_check': False,
            'initial_state': 'o',
            'is_flapping': False,
            'is_impact': False,
            'is_problem': False,
            'is_volatile': False,
            'labels': [],
            'last_check_command': '',
            'last_chk': 0,
            'last_event_id': 0,
            'last_hard_state': 'PENDING',
            'last_hard_state_change': 0.0,
            'last_hard_state_id': 0,
            'last_notification': 0.0,
            'last_perf_data': '',
            'last_problem_id': 0,
            'last_snapshot': 0,
            'last_state': 'PENDING',
            'last_state_change': 0.0,
            'last_state_id': 0,
            'last_state_type': 'HARD',
            'last_state_update': 0.0,
            'last_time_critical': 0,
            'last_time_ok': 0,
            'last_time_unknown': 0,
            'last_time_warning': 0,
            'latency': 0.0,
            'long_output': '',
            'low_flap_threshold': 25,
            'macromodulations': [],
            'maintenance_period': '',
            'max_check_attempts': 1,
            'merge_host_contacts': False,
            'modified_attributes': 0,
            'my_own_business_impact': -1,
            'next_chk': 0,
            'notes': '',
            'notes_url': '',
            'notification_interval': 60,
            'notification_options': ['w', 'u', 'c', 'r', 'f', 's', 'x'],
            'notifications_enabled': True,
            'notifications_in_progress': {},
            'notified_contacts': set([]),
            'obsess_over_service': False,
            'output': '',
            'parallelize_check': True,
            'parent_dependencies': set([]),
            'passive_checks_enabled': True,
            'pending_flex_downtime': 0,
            'percent_state_change': 0.0,
            'perf_data': '',
            'poller_tag': 'None',
            'problem_has_been_acknowledged': False,
            'process_perf_data': True,
            'processed_business_rule': '',
            'reactionner_tag': 'None',
            'realm': '',
            'resultmodulations': [],
            'retry_interval': 0,
            'return_code': 0,
            's_time': 0.0,
            'scheduled_downtime_depth': 0,
            'service_dependencies': [],
            'servicegroups': [],
            'should_be_scheduled': 1,
            'snapshot_command': None,
            'snapshot_criteria': ['w', 'c', 'u', 'x'],
            'snapshot_enabled': False,
            'snapshot_interval': 5,
            'snapshot_period': None,
            'source_problems': [],
            'stalking_options': [],
            'start_time': 0,
            'state': 'OK',
            'state_before_hard_unknown_reach_phase': 'OK',
            'state_before_impact': 'PENDING',
            'state_changed_since_impact': False,
            'state_id': 0,
            'state_id_before_impact': 0,
            'state_type': 'HARD',
            'state_type_id': 0,
            'time_to_orphanage': 300,
            'timeout': 0,
            'topology_change': False,
            'trending_policies': [],
            'trigger_broker_raise_enabled': False,
            'trigger_name': '',
            'triggers': [],
            'u_time': 0.0,
            'was_in_hard_unknown_reach_phase': False
        })
        assert expected == service1.__dict__

        # Independent Service
        service2 = Service({'service_description': 'service2',
                            'check_period': '24x7',
                            'use': 'service_tpl',
                            'imported_from': 'file.cfg'})
        # We get an item with an uuid, its properties, running properties and macros PLUS
        # the parameters and the inner defined properties
        expected = {'uuid': service2.uuid}
        expected.update({
            # Item Properties
            'use': ['service_tpl'], 'display_name': '',
            'definition_order': 100,
            'register': True, 'alias': '',
            'imported_from': 'file.cfg', 'name': 'unnamed',
            # Item Runing properties
            'configuration_errors': [],
            'configuration_warnings': [],
            'tags': set([]), 'customs': {}, 'plus': {},

            'service_description': 'service2',

            'acknowledgement': None,
            'acknowledgement_type': 1,
            'act_depend_of': [],
            'act_depend_of_me': [],
            'action_url': '',
            'actions': [],
            'active_checks_enabled': True,
            'aggregation': '',
            'attempt': 0,
            'broks': [],
            'business_impact': 2,
            'business_impact_modulations': [],
            'business_rule': None,
            'business_rule_downtime_as_ack': False,
            'business_rule_host_notification_options': [],
            'business_rule_output_template': '',
            'business_rule_service_notification_options': [],
            'business_rule_smart_notifications': False,
            'check_command': '',
            'check_flapping_recovery_notification': True,
            'check_freshness': False,
            'check_interval': 0,
            'check_period': '24x7',
            'check_type': 0,
            'checkmodulations': [],
            'checks_in_progress': [],
            'child_dependencies': set([]),
            'chk_depend_of': [],
            'chk_depend_of_me': [],
            'comments': [],
            'contact_groups': [],
            'contacts': [],
            'current_notification_id': 0,
            'current_notification_number': 0,
            'custom_views': [],
            'default_value': '',
            'downtimes': [],
            'duplicate_foreach': '',
            'duration_sec': 0,
            'early_timeout': 0,
            'end_time': 0,
            'escalations': [],
            'event_handler': '',
            'event_handler_enabled': False,
            'execution_time': 0.0,
            'failure_prediction_enabled': False,
            'first_notification_delay': 0,
            'flap_detection_enabled': True,
            'flap_detection_options': ['o', 'w', 'c', 'u', 'x'],
            'flapping_changes': [],
            'flapping_comment_id': 0,
            'freshness_state': 'x',
            'freshness_threshold': 3600,
            'got_business_rule': False,
            'has_been_checked': 0,
            'high_flap_threshold': 50,
            'host': None,
            'host_dependency_enabled': True,
            'hostgroup_name': '',
            'icon_image': '',
            'icon_image_alt': '',
            'icon_set': '',
            'impacts': [],
            'in_checking': False,
            'in_hard_unknown_reach_phase': False,
            'in_maintenance': -1,
            'in_scheduled_downtime': False,
            'in_scheduled_downtime_during_last_check': False,
            'initial_state': 'o',
            'is_flapping': False,
            'is_impact': False,
            'is_problem': False,
            'is_volatile': False,
            'labels': [],
            'last_check_command': '',
            'last_chk': 0,
            'last_event_id': 0,
            'last_hard_state': 'PENDING',
            'last_hard_state_change': 0.0,
            'last_hard_state_id': 0,
            'last_notification': 0.0,
            'last_perf_data': '',
            'last_problem_id': 0,
            'last_snapshot': 0,
            'last_state': 'PENDING',
            'last_state_change': 0.0,
            'last_state_id': 0,
            'last_state_type': 'HARD',
            'last_state_update': 0.0,
            'last_time_critical': 0,
            'last_time_ok': 0,
            'last_time_unknown': 0,
            'last_time_warning': 0,
            'latency': 0.0,
            'long_output': '',
            'low_flap_threshold': 25,
            'macromodulations': [],
            'maintenance_period': '',
            'max_check_attempts': 1,
            'merge_host_contacts': False,
            'modified_attributes': 0,
            'my_own_business_impact': -1,
            'next_chk': 0,
            'notes': '',
            'notes_url': '',
            'notification_interval': 60,
            'notification_options': ['w', 'u', 'c', 'r', 'f', 's', 'x'],
            'notifications_enabled': True,
            'notifications_in_progress': {},
            'notified_contacts': set([]),
            'obsess_over_service': False,
            'output': '',
            'parallelize_check': True,
            'parent_dependencies': set([]),
            'passive_checks_enabled': True,
            'pending_flex_downtime': 0,
            'percent_state_change': 0.0,
            'perf_data': '',
            'poller_tag': 'None',
            'problem_has_been_acknowledged': False,
            'process_perf_data': True,
            'processed_business_rule': '',
            'reactionner_tag': 'None',
            'realm': '',
            'resultmodulations': [],
            'retry_interval': 0,
            'return_code': 0,
            's_time': 0.0,
            'scheduled_downtime_depth': 0,
            'service_dependencies': [],
            'servicegroups': [],
            'should_be_scheduled': 1,
            'snapshot_command': None,
            'snapshot_criteria': ['w', 'c', 'u', 'x'],
            'snapshot_enabled': False,
            'snapshot_interval': 5,
            'snapshot_period': None,
            'source_problems': [],
            'stalking_options': [],
            'start_time': 0,
            'state': 'OK',
            'state_before_hard_unknown_reach_phase': 'OK',
            'state_before_impact': 'PENDING',
            'state_changed_since_impact': False,
            'state_id': 0,
            'state_id_before_impact': 0,
            'state_type': 'HARD',
            'state_type_id': 0,
            'time_to_orphanage': 300,
            'timeout': 0,
            'topology_change': False,
            'trending_policies': [],
            'trigger_broker_raise_enabled': False,
            'trigger_name': '',
            'triggers': [],
            'u_time': 0.0,
            'was_in_hard_unknown_reach_phase': False
        })
        assert expected == service2.__dict__

        # Build a services list with the 3 services
        services_list = Services([tpl1, service1, service2])
        expected = {
            'configuration_errors': [], 'configuration_warnings': [],
            # Note the service name as a tuple (host_name, service_description)
            'name_to_item': {
                ('unnamed', 'service1'): service1,
                ('unnamed', 'service2'): service2
            },
            'name_to_template': {
                'service_tpl': tpl1
            },
            'templates': {
                tpl1.uuid: tpl1,
            },
            'items': {
                service1.uuid: service1,
                service2.uuid: service2,
            }
        }
        assert expected == services_list.__dict__

        # No templates in the items list, only the real items
        serialized_services_list = services_list.serialize()
        expected = {
            service1.uuid: service1.serialize(),
            service2.uuid: service2.serialize(),
        }
        # print("Serialized services list: %s" % serialized_services_list)
        assert expected == serialized_services_list

        # Search in the list
        for service in services_list:
            assert isinstance(service, Service)
        # An exception is raised if service name is not well formed as a tuple !
        with pytest.raises(NameError) as excinfo:
            assert services_list.find_by_name('service1') == service1
        assert 'Service name is a tuple with host_name and service_description' in str(excinfo.value)
        assert services_list.find_by_name(('unnamed', 'service1')) == service1
        assert services_list.find_by_name(('unnamed', 'service2')) == service2
        assert services_list.find_tpl_by_name('service_tpl') == tpl1

        # Get standard objects
        self.get_contacts()
        self.get_timeperiods()
        self.get_commands()
        self.get_hosts()

        # Relation Services / templates
        print("Services linkify templates...")
        services_list.linkify_templates()
        assert service1.get_templates() == ['service_tpl']
        assert service1.tags == ['service_tpl']
        assert service2.get_templates() == ['service_tpl']
        assert service2.tags == ['service_tpl']

        # Service contacts, commands, ... still with default values and not yet linked!
        assert service1.contacts == ['contact1']
        assert service1.check_command == None
        assert service2.contacts == []
        assert service2.check_command == None

        # Manage inheritance
        print("Services apply inheritance...")
        services_list.apply_inheritance()

        # Explode
        services_list.explode(self.hosts_list, Hostgroups([]), self.contacts_list,
                              Servicegroups([]), Servicedependencies([]))
        # Set default values
        # services_list.fill_default()

        # Implicit host inheritance
        services_list.apply_implicit_inheritance(self.hosts_list)

        # Remove templates
        services_list.remove_templates()

        # Link services with timeperiods, commands, ...
        services_list.linkify(self.hosts_list, self.commands_list, self.timeperiods_list,
                              self.contacts_list, Resultmodulations([]),
                              Businessimpactmodulations([]), Escalations([]), Servicegroups([]),
                              Triggers([]), CheckModulations([]), MacroModulations([]))

        # Search in the list
        for service in services_list:
            assert isinstance(service, Service)
        # Now services are linked to their host
        assert services_list.find_by_name(('host1', 'service1')) == service1
        assert services_list.find_by_name(('host1', 'service2')) == service2
        # And services link to the templates are not existing anymore
        assert services_list.find_by_name(('unnamed', 'service1')) is None
        assert services_list.find_by_name(('unnamed', 'service2')) is None
        assert services_list.find_tpl_by_name('service_tpl') == tpl1

        # Service contacts, commands, ...
        # Now we have real objects
        assert service1.contacts == [self.contact1.uuid]
        assert isinstance(service1.check_command, CommandCall)
        assert service1.check_command.command == self.command1
        assert isinstance(service2.check_command, CommandCall)
        assert service2.check_command.command == self.command1

        pprint(services_list.__dict__)

    def test_serialize_config(self):
        """ Test global configuration serialization / unserialization...

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        print("-----")
        serialized_config = self.arbiter.conf.serialize()

        # 1. Restore the configuration, without parsing
        # Recreate an object with its initialisaze method
        # new_conf = Config(serialized_config, parsing=False)

        # 2. Restore the configuration, as a daemon does it when it receives
        # its configuration from the arbiter
        new_conf = unserialize(serialized_config, True)
        print("-----")

        for cls, clss, prop, _ in self.arbiter.conf.types_creations.values():
            print("Compare: %s" % prop)
            initial_list = clss(getattr(self.arbiter.conf, prop), parsing=False)
            initial_list = sorted(initial_list, key=lambda k: k.uuid)

            new_list = clss(getattr(new_conf, clss), parsing=False)
            new_list = sorted(new_list, key=lambda k: k.uuid)

            assert len(initial_list) == len(new_list)
            for index in range(len(initial_list)):
                # print(" - object: %s" % initial_list[index])
                # print(" - object: %s" % new_list[index])
                # print("Properties: %s" % initial_list[index].properties)
                for prop in initial_list[index].properties:
                    assert getattr(initial_list[index], prop, None) == getattr(new_list[index], prop, None)
                    if getattr(initial_list[index], prop, None) is None:
                        print("  undefined property: %s" % (prop))

        for key, value in getattr(obj, "running_properties", {}).iteritems():
            if value.has_default:
                # Make a copy for iterable properties
                if hasattr(value.default, '__iter__'):
                    all_props[key] = copy(value.default)
                else:
                    all_props[key] = value.default
            else:
                all_props[key] = value

        for key, value in getattr(obj, "macros", {}).iteritems():
            all_props[key] = value

        return all_props

    def test_serialize_alignak_object(self):
        """ Test AlignakObject serialization / unserialization...

        :return: None
        """
        self.print_header()

        # AlignakObject initialization with no parameters (parsing parameter is ignored!)
        # ---
        item = AlignakObject()
        # We get an object with an uuid but without any properties
        expected = {'uuid': item.uuid}
        print("AlignakObject: %s" % item.__dict__)
        assert expected == item.__dict__

        # Item self-serialize
        serialized_item = item.serialize()
        # We should get a dictionary with object properties, running_properties and macros
        expected = {'uuid': item.uuid}
        print("Serialized AlignakObject: %s" % serialized_item)
        assert expected == serialized_item

        # Item global object serialize
        serialized_item = serialize(item, no_dump=True)
        # We should get a dictionary with Item properties, running_properties and macros
        # configuration_errors and configuration_warnings are filtered
        expected_global = {
            '__sys_python_module__': 'alignak.alignakobject.AlignakObject',
            'content': expected
        }
        print("Serialized AlignakObject: %s" % serialized_item)
        assert expected_global == serialized_item
        # Same with a JSON string
        serialized_item = serialize(item, no_dump=False)
        expected_global = '{"content":{"uuid":"%s"},"__sys_python_module__":"alignak.alignakobject.AlignakObject"}' % item.uuid
        assert expected_global == serialized_item

        # AlignakObject initialization with parameters
        # ---
        item = AlignakObject({'foo': 'bar'})
        # We get an item with an uuid, its properties and the parameters
        expected = {'uuid': item.uuid, 'foo': 'bar'}
        print("AlignakObject: %s" % item.__dict__)
        assert expected == item.__dict__

        serialized_item = item.serialize()
        # We should get a dictionary with Item properties, running_properties and macros
        # configuration_errors and configuration_warnings are filtered
        # Note that parameters that are not defined in properties, running_properties or macros
        # are filtered!
        expected = {'uuid': item.uuid}
        print("Serialized AlignakObject: %s" % serialized_item)
        assert expected == serialized_item

        # Item global object serialize
        serialized_item = serialize(item, no_dump=True)
        # We should get a dictionary with Item properties, running_properties and macros
        # configuration_errors and configuration_warnings are filtered
        expected_global = {
            '__sys_python_module__': 'alignak.alignakobject.AlignakObject',
            'content': expected
        }
        print("Serialized AlignakObject: %s" % serialized_item)
        assert expected_global == serialized_item
        # Same with a JSON string
        serialized_item = serialize(item, no_dump=False)
        expected_global = '{"content":{"uuid":"%s"},"__sys_python_module__":"alignak.alignakobject.AlignakObject"}' % item.uuid
        assert expected_global == serialized_item

    def test_serialize_item(self):
        """ Test Item serialization / unserialization...

        :return: None
        """
        self.print_header()

        # Item initialization with no parameters
        # parsing parameter is False so we only define default values and
        # restore serialized properties
        # ---
        item = Item(parsing=False)
        # We get an object with an uuid and its properties
        print("Item: %s" % item.__dict__)
        expected = {'uuid': item.uuid}
        expected.update(self.set_expected(item))
        expected.update({'tags': set([])})
        assert expected == item.__dict__

        serialized_item = item.serialize()
        # We should get a dictionary with Item properties, running_properties and macros
        # configuration_errors and configuration_warnings are filtered
        expected = {
            'customs': {}, 'plus': {},
            'uuid': item.uuid,
            'conf_is_correct': True, 'tags': []
        }
        assert expected == serialized_item

        # Item global object serialize
        serialized_item = serialize(item, no_dump=True)
        # We should get a dictionary with Item properties, running_properties and macros
        # configuration_errors and configuration_warnings are filtered
        expected_global = {
            '__sys_python_module__': 'alignak.objects.item.Item',
            'content': expected
        }
        print("Serialized AlignakObject: %s" % serialized_item)
        assert expected_global == serialized_item

        # Item initialization with no parameters
        # parsing parameter is True so we create default parameters and inner properties
        # ---
        item = Item(parsing=True)
        # We get an object with an uuid but without any properties
        print("Item: %s" % item.__dict__)
        expected = {'uuid': item.uuid}
        expected.update(self.set_expected(item))
        expected.update({
            'configuration_errors': [], 'use': [], 'display_name': '', 'definition_order': 100,
            'tags': set([]), 'name': 'unnamed', 'register': True, 'customs': {},
            'alias': '', 'plus': {}, 'configuration_warnings': [],
            'imported_from': 'unknown', 'conf_is_correct': True,
        'extra': '', 'foo': ''})
        assert expected == item.__dict__

        serialized_item = item.serialize()
        # We should get a dictionary with Item properties, running_properties and macros
        # configuration_errors and configuration_warnings are filtered
        expected = {'uuid': item.uuid}
        expected.update({
            'use': [], 'display_name': '', 'definition_order': 100, 'tags': [], 'name': 'unnamed',
            'register': True, 'customs': {}, 'alias': '', 'plus': {}, 'imported_from': 'unknown',
            'conf_is_correct': True, 'extra': '', 'foo': ''})
        print("Serialized Item: %s" % serialized_item)
        assert expected == serialized_item

        # Item global object serialize
        serialized_item = serialize(item, no_dump=True)
        # We should get a dictionary with Item properties, running_properties and macros
        # configuration_errors and configuration_warnings are filtered
        expected_global = {
            '__sys_python_module__': 'alignak.objects.item.Item',
            'content': expected
        }
        print("Serialized AlignakObject: %s" % serialized_item)
        assert expected_global == serialized_item

        # Item initialization with parameters
        # ---
        item = Item({'foo': 'bar', 'imported_from': 'file.cfg'})
        # We get an item with an uuid, its properties, running properties and macros PLUS
        # the parameters and the inner defined properties
        expected = {'uuid': item.uuid,
                    'conf_is_correct': True,
                    # Item properties:
                    'use': [],
                    'definition_order': 100, 'register': True,
                    'imported_from': 'file.cfg', 'name': 'unnamed',
                    'alias': '', 'display_name': '',
                    # Item running properties:
                    'configuration_errors': [],
                    'configuration_warnings': [],
                    'tags': set([]),
                    # Item self declared properties
                    'customs': {},
                    'plus': {},
                    # Item parameters
                    'extra': '',
                    'foo': 'bar',
                    }
        print("Item: %s" % item.__dict__)
        assert expected == item.__dict__

        serialized_item = item.serialize()
        # We should get a dictionary with Item properties, running_properties and macros
        # configuration_errors and configuration_warnings are filtered
        # Note that parameters that are not defined in properties, running_properties or macros
        # are not filtered. This because an Item object uses a ToGuessProp object for guessed
        # properties.
        expected = {'uuid': item.uuid}
        expected.update({
            'use': [], 'display_name': '', 'definition_order': 100, 'tags': [], 'name': 'unnamed',
            'register': True, 'customs': {}, 'alias': '', 'plus': {}, 'foo': 'bar', 'extra': '',
            'imported_from': 'file.cfg', 'conf_is_correct': True})
        print("Serialized Item: %s" % serialized_item)
        assert expected == serialized_item

        # Item global object serialize
        serialized_item = serialize(item, no_dump=True)
        # We should get a dictionary with Item properties, running_properties and macros
        # configuration_errors and configuration_warnings are filtered
        expected_global = {
            '__sys_python_module__': 'alignak.objects.item.Item',
            'content': expected
        }
        print("Serialized AlignakObject: %s" % serialized_item)
        assert expected_global == serialized_item

    def test_serialize_items_list(self):
        """ Test Items serialization / unserialization...

        :return: None
        """
        self.print_header()

        # Item initialization with no parameters
        item1 = Item(parsing=True)

        # Item initialization with no parameters
        item2 = Item(parsing=True)

        # Item initialization with parameters
        item3 = Item({'foo': 'bar', 'imported_from': 'file.cfg'})

        # Build a list with the 3 items
        items_list = Items([item1, item2, item3])
        expected = {
            'conf_is_correct': True,
            'configuration_errors': [], 'configuration_warnings': [],
            # Unnamed items are named with their uuid!
            'name_to_item': {
                item1.uuid: item1,
                item2.uuid: item2,
                item3.uuid: item3,
            },
            'name_to_template': {},
            'templates': {},
            'items': {
                item1.uuid: item1,
                item2.uuid: item2,
                item3.uuid: item3,
            }
        }
        assert expected == items_list.__dict__

        serialized_items_list = items_list.serialize()
        expected = {
            item1.uuid: item1.serialize(),
            item2.uuid: item2.serialize(),
            item3.uuid: item3.serialize(),
        }
        print("Serialized Item: %s" % serialized_items_list)
        assert expected == serialized_items_list

    def test_serialize_contacts_list(self):
        """ Test Contacts serialization / unserialization...

        :return: None
        """
        self.print_header()

        # Contact initialization as a template
        tpl1 = Contact({'name': 'contact_tpl', 'register': '0'}, parsing=True)
        assert tpl1.is_tpl()

        # Contact initialization as depending upon the template
        contact1 = Contact({'contact_name': 'contact1', 'use': 'contact_tpl'}, parsing=True)
        assert not contact1.is_tpl()
        expected = {'uuid': contact1.uuid}
        expected.update({
            'address1': 'none',
            'address2': 'none',
            'address3': 'none',
            'address4': 'none',
            'address5': 'none',
            'address6': 'none',
            'alias': '',
            'broks': [],
            'can_submit_commands': False,
            'conf_is_correct': True,
            'configuration_errors': [],
            'configuration_warnings': [],
            'contact_name': 'contact1',
            'contactgroups': [],
            'customs': {},
            'definition_order': 100,
            'display_name': '',
            'downtimes': [],
            'email': 'none',
            'expert': False,
            'host_notification_commands': [],
            'host_notification_options': [],
            'host_notifications_enabled': True,
            'imported_from': 'unknown',
            'in_scheduled_downtime': False,
            'is_admin': False,
            'min_business_impact': 0,
            'modified_attributes': 0,
            'modified_host_attributes': 0,
            'modified_service_attributes': 0,
            'name': 'unnamed',
            'notificationways': [],
            'pager': 'none',
            'password': 'NOPASSWORDSET',
            'plus': {},
            'register': True,
            'service_notification_commands': [],
            'service_notification_options': [],
            'service_notifications_enabled': True,
            'tags': set([]),
            'use': ['contact_tpl']})
        assert expected == contact1.__dict__

        # Independent contact
        contact2 = Contact({'contact_name': 'contact2', 'imported_from': 'file.cfg'})
        assert not contact2.is_tpl()

        # Build a contacts list with the 3 contacts
        contacts_list = Contacts([tpl1, contact1, contact2])
        expected = {
            'conf_is_correct': True,
            'configuration_errors': [], 'configuration_warnings': [],
            'name_to_item': {
                'contact1': contact1,
                'contact2': contact2
            },
            'name_to_template': {
                'contact_tpl': tpl1
            },
            'templates': {
                tpl1.uuid: tpl1,
            },
            'items': {
                contact1.uuid: contact1,
                contact2.uuid: contact2,
            }
        }
        print("Item: %s" % contacts_list)
        assert expected == contacts_list.__dict__

        # No templates in the items list, only the real items
        serialized_contacts_list = contacts_list.serialize()
        expected = {
            contact1.uuid: contact1.serialize(),
            contact2.uuid: contact2.serialize(),
        }
        print("Serialized Item: %s" % serialized_contacts_list)
        assert expected == serialized_contacts_list

        # Relation contacts / templates
        contacts_list.linkify_templates()
        assert contact1.tags == ['contact_tpl']
        assert contact2.tags == []

        # Search in the list
        for contact in contacts_list:
            assert isinstance(contact, Contact)
            print("Contact: %s" % contact)
        assert contacts_list.find_by_name('contact2') == contact2
        assert contacts_list.find_tpl_by_name('contact_tpl') == tpl1

    def test_serialize_contacts_group(self):
        """ Test Contacts / Contacts groups serialization / unserialization...

        :return: None
        """
        self.print_header()

        # Contact initialization as a template
        tpl1 = Contact({'name': 'contact_tpl', 'register': '0'}, parsing=True)
        assert tpl1.is_tpl()

        # Contact initialization as depending upon the template
        contact1 = Contact({'contact_name': 'contact1', 'use': 'contact_tpl'}, parsing=True)
        assert not contact1.is_tpl()
        assert contact1.notificationways == []

        # Independent contact in the contact group
        contact2 = Contact({'contact_name': 'contact2', 'contactgroups': 'contacts_group'})
        assert not contact2.is_tpl()
        assert contact2.notificationways == []

        # Build a contacts list with the 3 contacts
        contacts_list = Contacts([tpl1, contact1, contact2])
        expected = {  # Item properties:
            'conf_is_correct': True,
            'configuration_errors': [], 'configuration_warnings': [],
            'name_to_item': {
                'contact1': contact1,
                'contact2': contact2
            },
            'name_to_template': {
                'contact_tpl': tpl1
            },
            'templates': {
                tpl1.uuid: tpl1,
            },
            'items': {
                contact1.uuid: contact1,
                contact2.uuid: contact2,
            }}
        print("Item: %s" % contacts_list)
        assert expected == contacts_list.__dict__

        # Contact group initialization
        contacts_group = Contactgroup({'contactgroup_name': 'contacts_group'}, parsing=True)

        # Build a contacts groups list and a notification ways list
        notificationways_list = NotificationWays([])
        contactgroups_list = Contactgroups([contacts_group])

        # Link all the contacts stuff
        contacts_list.explode(contactgroups_list, notificationways_list)

        # Search in the lists (contacts / contacts groups)
        for contactgroup in contactgroups_list:
            assert isinstance(contactgroup, Contactgroup)
            print("Contacts group: %s" % contactgroup.__dict__)
        assert contactgroups_list.find_by_name('contacts_group') == contacts_group
        # Group members (groups)
        assert contacts_group.contactgroup_members == []
        # Group members (contacts)
        assert contacts_group.members == [contact2.get_name()]
        assert contacts_group.unknown_members == []

        # Search in the lists (notification ways)
        for nw in notificationways_list:
            assert isinstance(nw, NotificationWay)
            print("NW: %s" % nw.__dict__)
        # Found empty notification ways (default created!)
        nw1 = notificationways_list.find_by_name('contact1_inner_notificationway')
        assert nw1.host_notifications_enabled == True
        assert nw1.host_notification_commands == []
        # assert nw1.host_notification_period == ''
        assert nw1.host_notification_options == []
        assert nw1.service_notifications_enabled == True
        assert nw1.service_notification_commands == []
        # assert nw1.service_notification_period == ''
        assert nw1.service_notification_options == []
        nw2 = notificationways_list.find_by_name('contact2_inner_notificationway')

        # Contacts notification ways
        # Todo: each contact got all the NWs!
        assert contact1.notificationways == [nw1.get_name()]
        assert contact2.notificationways == [nw2.get_name()]

        contacts_list.linkify_with_notificationways(notificationways_list)

        # Contacts notification ways
        # Todo: each contact got all the NWs!
        assert contact1.notificationways == [nw1.uuid]
        assert contact2.notificationways == [nw2.uuid]

    @unittest.skip("Temporarily disabled...")
    def test_serialize_config(self):
        """ Test global configuration serialization / unserialization...

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        assert self.conf_is_correct

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

        print("-----")
        serialized_config = self.arbiter.conf.serialize()

        # 1. Restore the configuration, without parsing
        # Recreate an object with its initialisaze method
        # new_conf = Config(serialized_config, parsing=False)

        # 2. Restore the configuration, as a daemon does it when it receives
        # its configuration from the arbiter
        new_conf = unserialize(serialized_config, True)
        print("-----")

        for obj_class, list_class, prop, _ in self.arbiter.conf.types_creations.values():
            print("Compare: %s" % prop)
            initial_list = getattr(self.arbiter.conf, prop)
            initial_list = sorted(initial_list, key=lambda k: k.uuid)

            new_list = list_class(getattr(new_conf, prop, {}), parsing=False)
            new_list = sorted(new_list, key=lambda k: k.uuid)

            assert len(initial_list) == len(new_list)
            for index in range(len(initial_list)):
                # print(" - object: %s" % initial_list[index])
                # print(" - object: %s" % new_list[index])
                # print("Properties: %s" % initial_list[index].properties)
                for prop in initial_list[index].properties:
                    assert getattr(initial_list[index], prop, None) == getattr(new_list[index], prop, None)
                    if getattr(initial_list[index], prop, None) is None:
                        print("  undefined property: %s" % (prop))

    def test_unserialize_notif(self):
        """ Test unserialize notifications

        :return: None
        """
        var = '''
        {"98a76354619746fa8e6d2637a5ef94cb": {
            "content": {
                "reason_type": 1, "exit_status": 3, "creation_time":1468522950.2828259468,
                "command_call": {
                    "args": [], "call": "notify-service",
                    "command": {
                        "command_line": "$USER1$\/notifier.pl
                                         --hostname $HOSTNAME$
                                         --servicedesc $SERVICEDESC$
                                         --notificationtype $NOTIFICATIONTYPE$
                                         --servicestate $SERVICESTATE$
                                         --serviceoutput $SERVICEOUTPUT$
                                         --longdatetime $LONGDATETIME$
                                         --serviceattempt $SERVICEATTEMPT$
                                         --servicestatetype $SERVICESTATETYPE$",
                        "command_name": "notify-service",
                        "configuration_errors":[],
                        "configuration_warnings":[],
                        "enable_environment_macros": false,
                        "id": "487aa432ddf646079ec6c07803333eac",
                        "imported_from": "cfg\/default\/commands.cfg:14",
                        "macros":{}, "module_type": "fork", "my_type":"command",
                        "ok_up":"", "poller_tag": "None",
                        "properties":{
                            "use":{
                                "brok_transformation": null,
                                "class_inherit": [],
                                "conf_send_preparation": null,
                                "default":[],
                                "fill_brok":[],
                                "has_default":true,
                                "help":"",
                                "keep_empty":false,
                                "managed":true,
                                "merging":"uniq",
                                "no_slots":false,
                                "override":false,
                                "required":false,
                                "retention":false,
                                "retention_preparation":null,
                                "special":false,
                                "split_on_coma":true,
                                "to_send":false,
                                "unmanaged":false,
                                "unused":false},
                            "name":{
                                "brok_transformation":null,
                                "class_inherit":[],
                                "conf_send_preparation":null,
                                "default":"",
                                "fill_brok":[],
                                "has_default":true,
                                "help":"",
                                "keep_empty":false,
                                "managed":true,
                                "merging":"uniq",
                                "no_slots":false,
                                "override":false,
                                "required":false,
                                "retention":false,
                                "retention_preparation":null,
                                "special":false,
                                "split_on_coma":true,
                                "to_send":false,
                                "unmanaged":false,
                                "unused":false},
                            },
                        "reactionner_tag":"None",
                        "running_properties":{
                            "configuration_errors":{
                                "brok_transformation":null,
                                "class_inherit":[],
                                "conf_send_preparation":null,
                                "default":[],"fill_brok":[],
                                "has_default":true,"help":"","keep_empty":false,
                                "managed":true,"merging":"uniq","no_slots":false,"override":false,
                                "required":false,"retention":false,"retention_preparation":null,
                                "special":false,"split_on_coma":true,"to_send":false,
                                "unmanaged":false,"unused":false},
                            },
                        "tags":[],
                        "timeout":-1,
                        "uuid":"487aa432ddf646079ec6c07803333eac"},
                    "enable_environment_macros":false,
                    "late_relink_done":false,
                    "macros":{},
                    "module_type":"fork",
                    "my_type":"CommandCall",
                    "poller_tag":"None",
                    "properties":{},
                    "reactionner_tag":"None",
                    "timeout":-1,
                    "uuid":"cfcaf0fc232b4f59a7d8bb5bd1d83fef",
                    "valid":true},
                "escalated":false,
                "reactionner_tag":"None",
                "s_time":0.0,
                "notification_type":0,
                "contact_name":"test_contact",
                "type":"PROBLEM",
                "uuid":"98a76354619746fa8e6d2637a5ef94cb",
                "check_time":0,"ack_data":"",
                "state":0,"u_time":0.0,
                "env":{
                    "NAGIOS_SERVICEDOWNTIME":"0",
                    "NAGIOS_TOTALSERVICESUNKNOWN":"",
                    "NAGIOS_LONGHOSTOUTPUT":"",
                    "NAGIOS_HOSTDURATIONSEC":"1468522950",
                    "NAGIOS_HOSTDISPLAYNAME":"test_host_0",
                    },
                "notif_nb":1,"_in_timeout":false,"enable_environment_macros":false,
                "host_name":"test_host_0",
                "status":"scheduled",
                "execution_time":0.0,"start_time":0,"worker":"none","t_to_go":1468522950,
                "module_type":"fork","service_description":"test_ok_0","sched_id":0,"ack_author":"",
                "ref":"272e89c1de854bad85987a7583e6c46b",
                "is_a":"notification",
                "contact":"4e7c4076c372457694684bdd5ba47e94",
                "command":"\/notifier.pl --hostname test_host_0 --servicedesc test_ok_0
                          --notificationtype PROBLEM --servicestate CRITICAL
                          --serviceoutput CRITICAL --longdatetime Thu 14 Jul 21:02:30 CEST 2016
                          --serviceattempt 2 --servicestatetype HARD",
                "end_time":0,"timeout":30,"output":"",
                "already_start_escalations":[]},
            "__sys_python_module__":"alignak.notification.Notification"
            }
        }

        '''
        unserialize(var)
        assert True

    def test_unserialize_check(self):
        """ Test unserialize checks

        :return: None
        """
        var = '''
        {"content":
                   {"check_type":0,"exit_status":3,"creation_time":1469152287.6731250286,
                    "reactionner_tag":"None","s_time":0.0,
                    "uuid":"5f1b16fa809c43379822c7acfe789660","check_time":0,"long_output":"",
                    "state":0,"internal":false,"u_time":0.0,"env":{},"depend_on_me":[],
                    "ref":"1fe5184ea05d439eb045399d26ed3337","from_trigger":false,
                    "status":"scheduled","execution_time":0.0,"worker":"none","t_to_go":1469152290,
                    "module_type":"echo","_in_timeout":false,"dependency_check":false,"type":"",
                    "depend_on":[],"is_a":"check","poller_tag":"None","command":"_echo",
                    "timeout":30,"output":"","perf_data":""},
               "__sys_python_module__":"alignak.check.Check"
        }
        '''

        unserialize(var)
        assert True
