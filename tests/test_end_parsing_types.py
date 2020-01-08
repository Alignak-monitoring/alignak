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
import logging
from .alignak_test import AlignakTest
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
    def setUp(self):
        super(TestEndParsingType, self).setUp()

    def check_object_property(self, obj, prop):
        """ Check the property of an object

        :param obj: object reference
        :type obj: object
        :param prop: property name
        :type prop: str
        :return: None
        """
        value = getattr(obj, prop, None)
        if value is not None:
            obj_expected_type = self.map_type(obj.properties[prop])

            # These properties are pure bytes string
            if prop in ['uuid', 'hash', 'push_flavor', 'instance_id', 'host_name']:
                obj_expected_type = bytes

            # These properties are containing the name or uuid of other items!
            # Sometimes it is the name and sometimes it is the uuid!!!!!
            # host_name may be a bytes string (socket name) or a string (host dependency) !
            # address6 may be an IPv6 address or a contact address field!
            # todo: change this and then modify the test!
            if prop in ['host_name', 'address6', 'instance_id', 'push_flavor', 'hash',
                        'imported_from']:
                return
            if prop in ['realm', 'check_period', 'check_command', 'event_handler',
                        'snapshot_period', 'maintenance_period', 'notification_period',
                        'service_notification_period', 'host_notification_period']:
                return

            assert isinstance(value, obj_expected_type), \
                "The %s property isn't a %s: %s, value=%s, for: %s" \
                % (prop, obj_expected_type, value.__class__, value, obj)

    @staticmethod
    def map_type(obj):
        """ Detect type of a property

        :param obj: get type of object
        :type obj: object
        :return: instance type
        """
        if isinstance(obj, ListProp):
            return list

        if isinstance(obj, StringProp):
            try:
                return unicode
            except NameError:
                return str

        if isinstance(obj, UnusedProp):
            try:
                return unicode
            except NameError:
                return str

        if isinstance(obj, BoolProp):
            return bool

        if isinstance(obj, IntegerProp):
            return int

        if isinstance(obj, FloatProp):
            return float

        if isinstance(obj, CharProp):
            return str

        if isinstance(obj, DictProp):
            return dict

        if isinstance(obj, AddrProp):
            try:
                return unicode
            except NameError:
                return str

        if isinstance(obj, ToGuessProp):
            try:
                return unicode
            except NameError:
                return str

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
        self.setup_with_file('cfg/cfg_default.cfg')

        for objects in (self._arbiter.conf.arbiters, self._arbiter.conf.contacts,
                        self._arbiter.conf.notificationways, self._arbiter.conf.hosts):
            self.check_objects_from(objects)

        print("== test Check() ==")
        check = Check({'status': u'OK', 'command': u'check_ping', 'ref': 0, 't_to_go': 10.0})
        for prop in check.properties:
            if hasattr(check, prop):
                value = getattr(check, prop)
                if prop not in ['ref']:  # TODO : clean this
                    # We should get rid of None, maybe use the "neutral" value for type
                    if value is not None:
                        print("TESTING %s with value %s" % (prop, value))
                        obj_expected_type = self.map_type(check.properties[prop])
                        # These properties are pure bytes string
                        if prop in ['uuid']:
                            obj_expected_type = bytes

                        assert isinstance(value, obj_expected_type), \
                            "The %s attr/property of %s object isn't a %s: %s, value=%s" \
                            % (prop, check.properties, obj_expected_type, value.__class__, value)
                    else:
                        print("Skipping %s " % prop)

        print("== test Notification() ==")
        notification = Notification()
        for prop in notification.properties:
            if not hasattr(notification, prop):
                continue
            value = getattr(notification, prop)
            # We should get ride of None, maybe use the "neutral" value for type
            if prop not in ['already_start_escalations']:  # TODO : clean this
                if value is not None:
                    print("TESTING %s with value %s" % (prop, value))
                    obj_expected_type = self.map_type(notification.properties[prop])
                    # These properties are pure bytes string
                    if prop in ['uuid']:
                        obj_expected_type = bytes

                    assert isinstance(value, obj_expected_type), \
                        "The %s attr/property of %s object isn't a %s: %s, value=%s" \
                        % (prop, notification.properties, obj_expected_type, value.__class__, value)
                else:
                    print("Skipping %s " % prop)

        print("== test EventHandler() ==")
        eventhandler = EventHandler({})
        for prop in eventhandler.properties:
            if not hasattr(eventhandler, prop):
                continue
            value = getattr(eventhandler, prop)
            if value is not None:
                print("TESTING %s with value %s" % (prop, value))
                obj_expected_type = self.map_type(eventhandler.properties[prop])
                # These properties are pure bytes string
                if prop in ['uuid', 'command']:
                    obj_expected_type = bytes
                if prop in ['command']:
                    continue

                assert isinstance(value, obj_expected_type), \
                    "The '%s' attr/property of %s object isn't a %s: %s, value=%s" \
                    % (prop, eventhandler.properties, obj_expected_type, value.__class__, value)
            else:
                print("Skipping %s " % prop)

        print("== test Timeperiod() ==")
        timeperiod = Timeperiod({})
        for prop in timeperiod.properties:
            if not hasattr(timeperiod, prop):
                continue
            value = getattr(timeperiod, prop)
            # We should get ride of None, maybe use the "neutral" value for type
            if value is not None:
                print("TESTING %s with value %s" % (prop, value))
                obj_expected_type = self.map_type(timeperiod.properties[prop])
                # These properties are pure bytes string
                if prop in ['uuid']:
                    obj_expected_type = bytes

                assert isinstance(value, obj_expected_type), \
                    "The %s attr/property of %s object isn't a %s: %s, value=%s" \
                    % (prop, timeperiod.properties, obj_expected_type, value.__class__, value)
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
                    obj_expected_type = self.map_type(command.properties[prop])
                    # These properties are pure bytes string
                    if prop in ['uuid']:
                        obj_expected_type = bytes

                    assert isinstance(value, obj_expected_type), \
                        "The %s attr/property of %s object isn't a %s: %s, value=%s" \
                        % (prop, command.properties, obj_expected_type, value.__class__, value)
                else:
                    print("Skipping %s " % prop)
