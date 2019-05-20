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
#     Jean Gabes, naparuba@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Sebastien Coavoux, s.coavoux@free.fr

#
# This file is used to test reading and processing of notification ways
#

import time
import copy
from alignak.objects.notificationway import NotificationWay
from .alignak_test import AlignakTest


class TestNotificationWay(AlignakTest):
    def setUp(self):
        super(TestNotificationWay, self).setUp()
        self.setup_with_file('cfg/cfg_notification_ways.cfg',
                             dispatching=True)
        assert self.conf_is_correct

    def test_create_nw(self):
        """ Test notification ways creation and check"""

        host_sms = self._scheduler.commands.find_by_name('notify-host-sms')

        service_sms = self._scheduler.notificationways.find_by_name('notify-service-sms')

        # Create a notification way with parameters
        parameters = {
            'definition_order': 100,
            'host_notification_commands': 'notify-host-sms',
            'host_notification_options': 'durfs',
            'host_notification_period': '24x7',
            'host_notifications_enabled': '1',
            'min_business_impact': 0,
            'notificationway_name': 'email_in_day',
            'register': True,
            'service_notification_commands': 'notify-service-sms',
            'service_notification_options': 'wucrf',
            'service_notification_period': '24x7',
            'service_notifications_enabled': '1',
            'use': ''
        }
        nw = NotificationWay(parameters)

        # And it will add an uuid
        parameters['uuid'] = nw.uuid
        # Those parameters are missing in the provided parameters but they will exist in the object
        parameters.update({
            # Transformed properties
            'host_notifications_enabled': True,
            'host_notification_commands': ['notify-host-sms'],
            'host_notification_options': ['durfs'],
            'service_notifications_enabled': True,
            'service_notification_commands': ['notify-service-sms'],
            'service_notification_options': ['wucrf'],
            'use': [],
            # Some more properties
            'imported_from': 'alignak-self',
            # 'name': '',
            'configuration_errors': [],
            'configuration_warnings': [],
            'customs': {},
            'plus': {},
            'tags': set([]),
            'downtimes': {},
            'conf_is_correct': True
        })
        # creation_time and log_actions will not be modified! They are set
        # only if they do not yet exist
        assert nw.__dict__ == parameters

    def test_correct_nw(self):
        """ Test check notification way is correct"""
        now = time.time()
        self.show_logs()

        # Get a NW
        email_in_day = self._scheduler.notificationways.find_by_name('email_in_day')
        saved_nw = email_in_day
        assert email_in_day.is_correct()

        # If no notifications enabled, it will be correct whatever else...
        from pprint import pprint

        test=copy.deepcopy(email_in_day)
        test.host_notification_options = ['n']
        test.service_notification_options = ['n']
        assert test.is_correct()

        test=copy.deepcopy(email_in_day)
        test.__dict__.pop('host_notification_commands')
        test.__dict__.pop('service_notification_commands')
        test.configuration_errors = []
        assert not test.is_correct()
        print(test.__dict__)
        assert test.configuration_errors == [
            '[notificationway::email_in_day] do not have any service_notification_commands defined',
            '[notificationway::email_in_day] do not have any host_notification_commands defined'
        ]

        test=copy.deepcopy(email_in_day)
        test.host_notification_period = None
        test.host_notification_commands = [None]
        test.service_notification_period = None
        test.service_notification_commands = [None]
        test.configuration_errors = []
        assert not test.is_correct()
        pprint(test.__dict__)
        assert '[notificationway::email_in_day] a service_notification_command is missing' \
               in test.configuration_errors
        assert '[notificationway::email_in_day] a host_notification_command is missing' \
               in test.configuration_errors
        assert '[notificationway::email_in_day] the service_notification_period is invalid' \
               in test.configuration_errors
        assert '[notificationway::email_in_day] the host_notification_period is invalid' \
               in test.configuration_errors

    def test_contact_nw(self):
        """ Test notification ways for a contact"""
        now = time.time()

        # Get the contact
        contact = self._scheduler.contacts.find_by_name("test_contact")

        print("All notification Way:")
        for nw in self._scheduler.notificationways:
            print("\t", nw.notificationway_name)
            assert nw.is_correct()
        # 3 defined NWs and 3 self created NWs
        assert len(self._scheduler.notificationways) == 6

        email_in_day = self._scheduler.notificationways.find_by_name('email_in_day')
        assert email_in_day.uuid in contact.notificationways

        sms_the_night = self._scheduler.notificationways.find_by_name('sms_the_night')
        assert sms_the_night.uuid in contact.notificationways

        # And check the criticity values
        assert 0 == email_in_day.min_business_impact
        assert 5 == sms_the_night.min_business_impact

        print("Contact '%s' notification way(s):" % contact.get_name())
        # 2 NWs for 'test_contact'
        assert len(contact.notificationways) == 2
        for nw_id in contact.notificationways:
            nw = self._scheduler.notificationways[nw_id]
            print("\t %s (or %s)" % (nw.notificationway_name, nw.get_name()))
            # Get host notifications commands
            for c in nw.host_notification_commands:
                print("\t\t", c.get_name())
            for c in nw.get_notification_commands('host'):
                print("\t\t", c.get_name())
            # Get service notifications commands
            for c in nw.service_notification_commands:
                print("\t\t", c.get_name())
            for c in nw.get_notification_commands('service'):
                print("\t\t", c.get_name())

        print("Contact '%s' commands:" % (contact.get_name()))
        # 2 commands for host notification (one from the NW and one contact defined)
        assert len(contact.host_notification_commands) == 2
        # 2 commands for service notification (one from the NW and one contact defined)
        assert len(contact.service_notification_commands) == 2
        # Get host notifications commands
        for c in contact.host_notification_commands:
            print("\t\tcontact host property:", c.get_name())
        for c in contact.get_notification_commands(self._scheduler.notificationways, 'host'):
            print("\t\tcontact host get_notification_commands:", c.get_name())
        # Get service notifications commands
        for c in contact.service_notification_commands:
            print("\t\tcontact service property:", c.get_name())
        for c in contact.get_notification_commands(self._scheduler.notificationways, 'service'):
            print("\t\tcontact service get_notification_commands:", c.get_name())

        contact_simple = self._scheduler.contacts.find_by_name("test_contact_simple")
        # It's the created notification way for this simple contact
        test_contact_simple_inner_notificationway = \
            self._scheduler.notificationways.find_by_name("test_contact_simple_inner_nw")
        print("Simple contact")
        for nw_id in contact_simple.notificationways:
            nw = self._scheduler.notificationways[nw_id]
            print("\t", nw.notificationway_name)
            for c in nw.service_notification_commands:
                print("\t\t", c.get_name())
        assert test_contact_simple_inner_notificationway.uuid in contact_simple.notificationways

        # we take as criticity a huge value from now
        huge_criticity = 5

        # Now all want* functions
        # First is ok with warning alerts
        assert email_in_day.want_service_notification(self._scheduler.timeperiods,
                                                      now, 'WARNING', 'PROBLEM',
                                                      huge_criticity) is True

        # But a SMS is now WAY for warning. When we sleep, we wake up for critical only guy!
        assert sms_the_night.want_service_notification(self._scheduler.timeperiods,
                                                       now, 'WARNING', 'PROBLEM',
                                                       huge_criticity) is False

        # Same with contacts now
        # First is ok for warning in the email_in_day nw
        assert contact.want_service_notification(self._scheduler.notificationways,
                                                 self._scheduler.timeperiods,
                                                 now, 'WARNING', 'PROBLEM', huge_criticity) is True
        # Simple is not ok for it
        assert contact_simple.want_service_notification(self._scheduler.notificationways,
                                                        self._scheduler.timeperiods,
                                                        now, 'WARNING', 'PROBLEM',
                                                        huge_criticity) is False

        # Then for host notification
        # First is ok for warning in the email_in_day nw
        assert contact.want_host_notification(self._scheduler.notificationways,
                                              self._scheduler.timeperiods,
                                              now, 'FLAPPING', 'PROBLEM', huge_criticity) is True
        # Simple is not ok for it
        assert contact_simple.want_host_notification(self._scheduler.notificationways,
                                                     self._scheduler.timeperiods,
                                                     now, 'FLAPPING', 'PROBLEM',
                                                     huge_criticity) is False

        # And now we check that we refuse SMS for a low level criticity
        # I do not want to be awaken by a dev server! When I sleep, I sleep!
        # (and my wife will kill me if I do...)

        # We take the EMAIL test because SMS got the night ony, so we
        # take a very low value for criticity here
        assert email_in_day.want_service_notification(self._scheduler.timeperiods,
                                                      now, 'WARNING', 'PROBLEM', -1) is False

        # Test the heritage for notification ways
        host_template = self._scheduler.hosts.find_by_name("test_host_contact_template")
        contact_template_1 = self._scheduler.contacts[host_template.contacts[0]]
        commands_contact_template_1 = contact_template_1.get_notification_commands(
            self._scheduler.notificationways,'host')
        contact_template_2 = self._scheduler.contacts[host_template.contacts[1]]
        commands_contact_template_2 = contact_template_2.get_notification_commands(
            self._scheduler.notificationways,'host')

        resp = sorted([sorted([command.get_name() for command in commands_contact_template_1]),
                       sorted([command.get_name() for command in commands_contact_template_2])])

        assert sorted([['notify-host', 'notify-host-work'],
                       ['notify-host-sms', 'notify-host-work']]) == resp

        contact_template_1 = self._scheduler.contacts[host_template.contacts[0]]
        commands_contact_template_1 = contact_template_1.get_notification_commands(
            self._scheduler.notificationways,'service')
        contact_template_2 = self._scheduler.contacts[host_template.contacts[1]]
        commands_contact_template_2 = contact_template_2.get_notification_commands(
            self._scheduler.notificationways,'service')
        resp = sorted([sorted([command.get_name() for command in commands_contact_template_1]),
                       sorted([command.get_name() for command in commands_contact_template_2])])

        assert sorted([['notify-service', 'notify-service-work'],
                       ['notify-service-sms', 'notify-service-work']]) == resp
