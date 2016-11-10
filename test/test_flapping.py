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
#     Jean Gabes, naparuba@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
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
 This file is used to test the flapping management
"""

from alignak.misc.serialization import unserialize
from alignak_test import AlignakTest, unittest


class TestFlapping(AlignakTest):
    """
    This class tests the flapping management
    """

    def setUp(self):
        self.setup_with_file('cfg/cfg_flapping.cfg')
        self.assertTrue(self.conf_is_correct)

        self._sched = self.schedulers['scheduler-master'].sched
        self._broker = self._sched.brokers['broker-master']

    def test_flapping(self):
        """

        :return:
        """
        # Get the hosts and services"
        host = self._sched.hosts.find_by_name("test_host_0")
        host.act_depend_of = []
        self.assertTrue(host.flap_detection_enabled)
        router = self._sched.hosts.find_by_name("test_router_0")
        router.act_depend_of = []
        self.assertTrue(router.flap_detection_enabled)
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.event_handler_enabled = False
        svc.act_depend_of = []
        # Force because the default configuration disables the flapping detection
        svc.flap_detection_enabled = True

        self.scheduler_loop(2, [
            [host, 0, 'UP | value1=1 value2=2'],
            [router, 0, 'UP | rtt=10'],
            [svc, 0, 'OK']
        ])
        self.assertEqual('UP', host.state)
        self.assertEqual('HARD', host.state_type)
        self.assertEqual('UP', router.state)
        self.assertEqual('HARD', router.state_type)
        self.assertEqual('OK', svc.state)
        self.assertEqual('HARD', svc.state_type)

        self.assertEqual(25, svc.low_flap_threshold)

        # Set the service as a problem
        self.scheduler_loop(3, [
            [svc, 2, 'Crit']
        ])
        self.assertEqual('CRITICAL', svc.state)
        self.assertEqual('HARD', svc.state_type)
        # Ok, now go in flap!
        for i in xrange(1, 10):
            self.scheduler_loop(1, [[svc, 0, 'Ok']])
            self.scheduler_loop(1, [[svc, 2, 'Crit']])

        # Should be in flapping state now
        self.assertTrue(svc.is_flapping)

        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in sorted(self._broker['broks'].itervalues(), key=lambda x: x.creation_time):
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        expected_logs = [
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;HARD;2;Crit'),
            (u'error', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;CRITICAL;'
                       u'notify-service;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;HARD;2;Ok'),
            (u'info', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;OK;'
                      u'notify-service;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE FLAPPING ALERT: test_host_0;test_ok_0;STARTED; '
                      u'Service appears to have started flapping (83.8% change >= 50.0% threshold)'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'info', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;'
                      u'FLAPPINGSTART (OK);notify-service;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
        ]
        for log_level, log_message in expected_logs:
            self.assertIn((log_level, log_message), monitoring_logs)

        # Now we put it as back :)
        # 10 is not enouth to get back as normal
        for i in xrange(1, 11):
            self.scheduler_loop(1, [[svc, 0, 'Ok']])
        self.assertTrue(svc.is_flapping)

        # 10 others can be good (near 4.1 %)
        for i in xrange(1, 11):
            self.scheduler_loop(1, [[svc, 0, 'Ok']])
        self.assertFalse(svc.is_flapping)


        # We got 'monitoring_log' broks for logging to the monitoring logs...
        monitoring_logs = []
        for brok in sorted(self._broker['broks'].itervalues(), key=lambda x: x.creation_time):
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))

        print("Logs: %s" % monitoring_logs)
        expected_logs = [
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;HARD;2;Crit'),
            (u'error', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;CRITICAL;'
                       u'notify-service;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;HARD;2;Ok'),
            (u'info', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;OK;'
                      u'notify-service;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE FLAPPING ALERT: test_host_0;test_ok_0;STARTED; '
                      u'Service appears to have started flapping '
                      u'(83.8% change >= 50.0% threshold)'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'info', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;'
                      u'FLAPPINGSTART (OK);notify-service;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE ALERT: test_host_0;test_ok_0;OK;SOFT;2;Ok'),
            (u'error', u'SERVICE ALERT: test_host_0;test_ok_0;CRITICAL;SOFT;1;Crit'),
            (u'info', u'SERVICE FLAPPING ALERT: test_host_0;test_ok_0;STOPPED; '
                      u'Service appears to have stopped flapping '
                      u'(21.5% change < 25.0% threshold)'),
            (u'info', u'SERVICE NOTIFICATION: test_contact;test_host_0;test_ok_0;'
                      u'FLAPPINGSTOP (OK);notify-service;Ok')
        ]
        for log_level, log_message in expected_logs:
            self.assertIn((log_level, log_message), monitoring_logs)


if __name__ == '__main__':
    unittest.main()
