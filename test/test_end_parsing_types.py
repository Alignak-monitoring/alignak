#!/usr/bin/env python
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
#  Copyright (C) 2009-2015:
#     Sebastien Coavoux, s.coavoux@free.fr

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

#
# This file is used to test reading and processing of config files
#

import unittest2 as unittest

import string
from alignak.objects.item import Items

from alignak_test import time_hacker
from alignak.log import logger
from alignak.objects.config import Config
from alignak.brok import Brok
from alignak.external_command import ExternalCommand
from alignak.property import UnusedProp, StringProp, IntegerProp, \
    BoolProp, CharProp, DictProp, FloatProp, ListProp, AddrProp, ToGuessProp
from alignak.check import Check
from alignak.notification import Notification
from alignak.eventhandler import EventHandler
from alignak.objects.command import Command
from alignak.objects.timeperiod import Timeperiod


class TestEndParsingType(unittest.TestCase):

    def check_object_property(self, obj, prop):
        if prop in (
                'realm',  # Realm
                'check_period',    # CheckPeriod
                'check_command',  # CommandCall
                'event_handler',  # CommandCall
                'notification_period',  # Timeperiod
                'service_notification_period',  # Timeperiod
                'host_notification_period',  # Timeperiod
        ):
            # currently not supported / handled or badly parsed / decoded properties values..
            # TODO: consider to also handles them properly ..
            return
        value = getattr(obj, prop, None)
        if value is not None:
            obj_expected_type = self.map_type(obj.properties[prop])
            self.assertIsInstance(value, obj_expected_type,
                                  "The %s attr/property of %s object isn't a %s: %s, value=%r" %
                                  (prop, obj, obj_expected_type, value.__class__, value))

    def map_type(self, obj):
        # TODO: Replace all basestring with unicode when done in property.default attribute
        # TODO: Fix ToGuessProp as it may be a list.

        if isinstance(obj, ListProp):
            return list

        if isinstance(obj, StringProp):
            return basestring

        if isinstance(obj, UnusedProp):
            return basestring

        if isinstance(obj, BoolProp):
            return bool

        if isinstance(obj, IntegerProp):
            return int

        if isinstance(obj, FloatProp):
            return float

        if isinstance(obj, CharProp):
            return basestring

        if isinstance(obj, DictProp):
            return dict

        if isinstance(obj, AddrProp):
            return basestring

        if isinstance(obj, ToGuessProp):
            return basestring

    def print_header(self):
        print "\n" + "#" * 80 + "\n" + "#" + " " * 78 + "#"
        print "#" + string.center(self.id(), 78) + "#"
        print "#" + " " * 78 + "#\n" + "#" * 80 + "\n"

    def add(self, b):
        if isinstance(b, Brok):
            self.broks[b._id] = b
            return
        if isinstance(b, ExternalCommand):
            self.sched.run_external_command(b.cmd_line)

    def check_objects_from(self, container):
        self.assertIsInstance(container, Items)
        for obj in container:
            for prop in obj.properties:
                self.check_object_property(obj, prop)

    def test_types(self):
        path = 'etc/alignak_1r_1h_1s.cfg'
        time_hacker.set_my_time()
        self.print_header()
        # i am arbiter-like
        self.broks = {}
        self.me = None
        self.log = logger
        self.log.setLevel("INFO")
        self.log.load_obj(self)
        self.config_files = [path]
        self.conf = Config()
        buf = self.conf.read_config(self.config_files)
        raw_objects = self.conf.read_config_buf(buf)
        self.conf.create_objects_for_type(raw_objects, 'arbiter')
        self.conf.create_objects_for_type(raw_objects, 'module')
        self.conf.early_arbiter_linking()
        self.conf.create_objects(raw_objects)
        self.conf.instance_id = 0
        self.conf.instance_name = 'test'
        # Hack push_flavor, that is set by the dispatcher
        self.conf.push_flavor = 0
        self.conf.load_triggers()
        self.conf.linkify_templates()
        self.conf.apply_inheritance()
        self.conf.explode()

        self.conf.apply_implicit_inheritance()
        self.conf.fill_default()
        self.conf.remove_templates()

        self.conf.override_properties()
        self.conf.linkify()
        self.conf.apply_dependencies()
        self.conf.explode_global_conf()
        self.conf.propagate_timezone_option()
        self.conf.create_business_rules()
        self.conf.create_business_rules_dependencies()
        self.conf.is_correct()

        ###############

        for objects in (self.conf.arbiters, self.conf.contacts, self.conf.notificationways, self.conf.hosts):
            self.check_objects_from(objects)

        print "== test Check() =="
        check = Check('OK', 'check_ping', 0, 10.0)
        for prop in check.properties:
            if hasattr(check, prop):
                value = getattr(check, prop)
                # We should get ride of None, maybe use the "neutral" value for type
                if prop not in ['ref']: # TODO : clean this
                    if value is not None:
                        print("TESTING %s with value %s" % (prop, value))
                        self.assertIsInstance(value, self.map_type(check.properties[prop]))
                    else:
                        print("Skipping %s " % prop)

        print "== test Notification() =="
        notification = Notification()
        for prop in notification.properties:
            if hasattr(notification, prop):
                value = getattr(notification, prop)
                # We should get ride of None, maybe use the "neutral" value for type
                if prop not in ['already_start_escalations']: # TODO : clean this
                    if value is not None:
                        print("TESTING %s with value %s" % (prop, value))
                        self.assertIsInstance(value, self.map_type(notification.properties[prop]))
                    else:
                        print("Skipping %s " % prop)

        print "== test EventHandler() =="
        eventhandler = EventHandler('')
        for prop in eventhandler.properties:
            if hasattr(eventhandler, prop):
                value = getattr(eventhandler, prop)
                # We should get ride of None, maybe use the "neutral" value for type
                if prop not in ['jjjj']: # TODO : clean this
                    if value is not None:
                        print("TESTING %s with value %s" % (prop, value))
                        self.assertIsInstance(value, self.map_type(eventhandler.properties[prop]))
                    else:
                        print("Skipping %s " % prop)

        print "== test Timeperiod() =="
        timeperiod = Timeperiod()
        for prop in timeperiod.properties:
            if hasattr(timeperiod, prop):
                value = getattr(timeperiod, prop)
                # We should get ride of None, maybe use the "neutral" value for type
                if value is not None:
                    print("TESTING %s with value %s" % (prop, value))
                    self.assertIsInstance(value, self.map_type(timeperiod.properties[prop]))
                else:
                    print("Skipping %s " % prop)

        print "== test Command() =="
        command = Command({})
        for prop in command.properties:
            if hasattr(command, prop):
                value = getattr(command, prop)
                # We should get ride of None, maybe use the "neutral" value for type
                if value is not None:
                    print("TESTING %s with value %s" % (prop, value))
                    self.assertIsInstance(value, self.map_type(command.properties[prop]))
                else:
                    print("Skipping %s " % prop)



if __name__ == '__main__':
    unittest.main()
