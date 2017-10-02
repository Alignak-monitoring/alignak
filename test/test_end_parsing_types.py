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
"""
This file is used to test properties types after config loaded and parsed
"""
from __future__ import print_function
import logging
from alignak_test import AlignakTest
from alignak.property import UnusedProp, StringProp, IntegerProp, \
    BoolProp, CharProp, DictProp, FloatProp, ListProp, AddrProp, ToGuessProp
from alignak.check import Check
from alignak.notification import Notification
from alignak.eventhandler import EventHandler
from alignak.objects.command import Command
from alignak.objects.timeperiod import Timeperiod
from alignak.objects.item import Items

logger = logging.getLogger(__name__)

class TestEndParsingType(AlignakTest):
    """
    This class test properties types after config loaded and parsed
    """

    def check_object_property(self, obj, prop):
        """ Check the property of an object

        :param obj: object reference
        :type obj: object
        :param prop: property name
        :type prop: str
        :return: None
        """
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
            assert isinstance(value, obj_expected_type), \
                                  "The %s attr/property of %s object isn't a %s: %s, value=%r" % \
                                  (prop, obj, obj_expected_type, value.__class__, value)

    @staticmethod
    def map_type(obj):
        """ Detect type of a property

        :param obj: get type of object
        :type obj: object
        :return: instance type
        """
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

    def check_objects_from(self, container):
        """ Check properties of an alignak item

        :param container: object / alignak item
        :type container: object
        :return: None
        """
        assert isinstance(container, Items)
        for obj in container:
            for prop in obj.properties:
                self.check_object_property(obj, prop)

    def test_types(self):  # pylint: disable=R0912
        """ Test properties types

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        for objects in (self.arbiter.conf.arbiters, self.arbiter.conf.contacts,
                        self.arbiter.conf.notificationways, self.arbiter.conf.hosts):
            self.check_objects_from(objects)

        print("== test Check() ==")
        check = Check({'status': 'OK', 'command': 'check_ping', 'ref': 0, 't_to_go': 10.0})
        for prop in check.properties:
            if hasattr(check, prop):
                value = getattr(check, prop)
                # We should get ride of None, maybe use the "neutral" value for type
                if prop not in ['ref']:  # TODO : clean this
                    if value is not None:
                        print("TESTING %s with value %s" % (prop, value))
                        assert isinstance(value, self.map_type(check.properties[prop]))
                    else:
                        print("Skipping %s " % prop)

        print("== test Notification() ==")
        notification = Notification()
        for prop in notification.properties:
            if hasattr(notification, prop):
                value = getattr(notification, prop)
                # We should get ride of None, maybe use the "neutral" value for type
                if prop not in ['already_start_escalations']:  # TODO : clean this
                    if value is not None:
                        print("TESTING %s with value %s" % (prop, value))
                        assert isinstance(value, self.map_type(notification.properties[prop]))
                    else:
                        print("Skipping %s " % prop)

        print("== test EventHandler() ==")
        eventhandler = EventHandler({})
        for prop in eventhandler.properties:
            if hasattr(eventhandler, prop):
                value = getattr(eventhandler, prop)
                # We should get ride of None, maybe use the "neutral" value for type
                if prop not in ['jjjj']:  # TODO : clean this
                    if value is not None:
                        print("TESTING %s with value %s" % (prop, value))
                        assert isinstance(value, self.map_type(eventhandler.properties[prop]))
                    else:
                        print("Skipping %s " % prop)

        print("== test Timeperiod() ==")
        timeperiod = Timeperiod()
        for prop in timeperiod.properties:
            if hasattr(timeperiod, prop):
                value = getattr(timeperiod, prop)
                # We should get ride of None, maybe use the "neutral" value for type
                if value is not None:
                    print("TESTING %s with value %s" % (prop, value))
                    assert isinstance(value, self.map_type(timeperiod.properties[prop]))
                else:
                    print("Skipping %s " % prop)

        print("== test Command() ==")
        command = Command({})
        for prop in command.properties:
            if hasattr(command, prop):
                value = getattr(command, prop)
                # We should get ride of None, maybe use the "neutral" value for type
                if value is not None:
                    print("TESTING %s with value %s" % (prop, value))
                    assert isinstance(value, self.map_type(command.properties[prop]))
                else:
                    print("Skipping %s " % prop)
