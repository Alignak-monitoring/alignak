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
#     aviau, alexandre.viau@savoirfairelinux.com
#     Grégory Starck, g.starck@gmail.com
#     Christophe Simon, geektophe@gmail.com
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
# This file is used to test business rules smart notifications behaviour.
#

import time
from alignak_test import unittest, AlignakTest, time_hacker


class TestBusinesscorrelNotifications(AlignakTest):

    def setUp(self):
        self.setup_with_file('cfg/cfg_business_correlator_notifications.cfg')
        self._sched = self.schedulers['scheduler-master'].sched

    def test_bprule_standard_notifications(self):
        """BR standard notification"""
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", "bp_rule_default")
        svc_cor.act_depend_of = []
        assert svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        assert False is svc_cor.business_rule_smart_notifications
        assert svc_cor.notification_options == [u'c', u'f', u's', u'r', u'u', u'w', u'x']

        dummy = self._sched.hosts.find_by_name("dummy")
        svc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc1.act_depend_of = []  # ignore the host dependency
        svc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc2.act_depend_of = []  # ignore the host dependency
        assert svc2.notification_options == [u'c', u'f', u's', u'r', u'u', u'w', u'x']

        self.scheduler_loop(2, [
            [dummy, 0, 'UP dummy'],
            [svc1, 0, 'OK test_host_01/srv1'],
            [svc2, 2, 'CRITICAL test_host_02/srv2']])

        # svc2 is HARD/CRITICAL so it is now a problem
        assert svc2.is_problem
        # BR is critical
        assert 2 == svc_cor.business_rule.get_state(self._sched.hosts, self._sched.services)

        now = time.time()
        cmd = "[%lu] ACKNOWLEDGE_SVC_PROBLEM;test_host_02;srv2;2;1;1;lausser;blablub" % (now)
        self._sched.run_external_command(cmd)
        self.external_command_loop()
        assert svc2.problem_has_been_acknowledged
        # Service is still a problem
        assert svc2.is_problem
        # BR is critical
        assert 2 == svc_cor.business_rule.get_state(self._sched.hosts, self._sched.services)
        assert not svc_cor.is_problem
        assert not svc_cor.state == "CRITICAL"

        timeperiod = self._sched.timeperiods[svc2.notification_period]
        # svc2 blocks the notification sending because the problem has been acknowledged!
        assert svc2.notification_is_blocked_by_item(timeperiod, self._sched.hosts,
                                                    self._sched.services, 'PROBLEM')

        self.scheduler_loop(1, [[svc_cor, None, None]])
        self.scheduler_loop(1, [[svc_cor, None, None]])

        # BR is still critical
        assert 2 == svc_cor.business_rule.get_state(self._sched.hosts, self._sched.services)
        assert False is svc_cor.notification_is_blocked_by_item(timeperiod, self._sched.hosts,
                                                                self._sched.services, 'PROBLEM')

    def test_bprule_smart_notifications_ack(self):
        """BR smart notifications acknowledge"""
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", "bp_rule_smart_notif")
        svc_cor.act_depend_of = []
        assert True is svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        assert True is svc_cor.business_rule_smart_notifications

        dummy = self._sched.hosts.find_by_name("dummy")
        svc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc1.act_depend_of = []  # ignore the host dependency
        svc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc2.act_depend_of = []  # ignore the host dependency

        self.scheduler_loop(2, [
            [dummy, 0, 'UP dummy'],
            [svc1, 0, 'OK test_host_01/srv1'],
            [svc2, 2, 'CRITICAL test_host_02/srv2']])

        # HARD/CRITICAL so it is now a problem
        assert svc2.is_problem

        assert 2 == svc_cor.business_rule.get_state(self._sched.hosts, self._sched.services)
        timeperiod = self._sched.timeperiods[svc_cor.notification_period]
        assert False is svc_cor.notification_is_blocked_by_item(timeperiod,
                                                                self._sched.hosts,
                                                                self._sched.services,
                                                                'PROBLEM')


        now = time.time()
        cmd = "[%lu] ACKNOWLEDGE_SVC_PROBLEM;test_host_02;srv2;2;1;1;lausser;blablub" % (now)
        self._sched.run_external_command(cmd)
        assert True is svc2.problem_has_been_acknowledged

        self.scheduler_loop(1, [[svc_cor, None, None]])
        self.scheduler_loop(1, [[svc_cor, None, None]])

        assert True is svc_cor.notification_is_blocked_by_item(timeperiod,
                                                                    self._sched.hosts,
                                                                    self._sched.services,
                                                                    'PROBLEM')

    def test_bprule_smart_notifications_svc_ack_downtime(self):
        """BR smart notifications service downtime"""
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", "bp_rule_smart_notif")
        svc_cor.act_depend_of = []
        assert True is svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        assert True is svc_cor.business_rule_smart_notifications
        assert False is svc_cor.business_rule_downtime_as_ack

        dummy = self._sched.hosts.find_by_name("dummy")
        svc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc1.act_depend_of = []  # ignore the host dependency
        svc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc2.act_depend_of = []  # ignore the host dependency

        self.scheduler_loop(2, [
            [dummy, 0, 'UP dummy'],
            [svc1, 0, 'OK test_host_01/srv1'],
            [svc2, 2, 'CRITICAL test_host_02/srv2']])

        assert 2 == svc_cor.business_rule.get_state(self._sched.hosts,
                                                            self._sched.services)
        timeperiod = self._sched.timeperiods[svc_cor.notification_period]
        host = self._sched.hosts[svc_cor.host]
        assert False is svc_cor.notification_is_blocked_by_item(timeperiod,
                                                                     self._sched.hosts,
                                                                     self._sched.services,
                                                                     'PROBLEM')

        duration = 600
        now = time.time()
        # fixed downtime valid for the next 10 minutes
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_02;srv2;%d;%d;1;;%d;lausser;blablub" % (
            now, now, now + duration, duration
        )
        self._sched.run_external_command(cmd)

        self.scheduler_loop(1, [[svc_cor, None, None]])
        self.scheduler_loop(1, [[svc_cor, None, None]])
        assert svc2.scheduled_downtime_depth > 0

        assert False is svc_cor.notification_is_blocked_by_item(timeperiod,
                                                                     self._sched.hosts,
                                                                     self._sched.services,
                                                                     'PROBLEM')

        svc_cor.business_rule_downtime_as_ack = True

        self.scheduler_loop(1, [[svc_cor, None, None]])
        self.scheduler_loop(1, [[svc_cor, None, None]])

        assert True is svc_cor.notification_is_blocked_by_item(timeperiod,
                                                                    self._sched.hosts,
                                                                    self._sched.services,
                                                                    'PROBLEM')

    def test_bprule_smart_notifications_hst_ack_downtime(self):
        """BR smart notifications host downtime"""
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", "bp_rule_smart_notif")
        svc_cor.act_depend_of = []
        assert True is svc_cor.got_business_rule
        assert svc_cor.business_rule is not None
        assert True is svc_cor.business_rule_smart_notifications
        assert False is svc_cor.business_rule_downtime_as_ack

        dummy = self._sched.hosts.find_by_name("dummy")
        svc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        svc1.act_depend_of = []  # ignore the host dependency
        svc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "srv2")
        svc2.act_depend_of = []  # ignore the host dependency
        hst2 = self._sched.hosts.find_by_name("test_host_02")

        self.scheduler_loop(2, [
            [dummy, 0, 'UP dummy'],
            [svc1, 0, 'OK test_host_01/srv1'],
            [svc2, 2, 'CRITICAL test_host_02/srv2']])

        assert 2 == svc_cor.business_rule.get_state(self._sched.hosts,
                                                            self._sched.services)
        timeperiod = self._sched.timeperiods[svc_cor.notification_period]
        host = self._sched.hosts[svc_cor.host]
        assert False is svc_cor.notification_is_blocked_by_item(timeperiod,
                                                                     self._sched.hosts,
                                                                     self._sched.services,
                                                                     'PROBLEM')

        duration = 600
        now = time.time()
        # fixed downtime valid for the next 10 minutes
        cmd = "[%lu] SCHEDULE_HOST_DOWNTIME;test_host_02;%d;%d;1;;%d;lausser;blablub" % (
            now, now, now + duration, duration
        )
        self._sched.run_external_command(cmd)

        self.scheduler_loop(1, [[svc_cor, None, None]])
        self.scheduler_loop(1, [[svc_cor, None, None]])
        assert hst2.scheduled_downtime_depth > 0

        assert False is svc_cor.notification_is_blocked_by_item(timeperiod,
                                                                     self._sched.hosts,
                                                                     self._sched.services,
                                                                     'PROBLEM')

        svc_cor.business_rule_downtime_as_ack = True

        self.scheduler_loop(1, [[svc_cor, None, None]])
        self.scheduler_loop(1, [[svc_cor, None, None]])

        assert True is svc_cor.notification_is_blocked_by_item(timeperiod,
                                                                    self._sched.hosts,
                                                                    self._sched.services,
                                                                    'PROBLEM')

    def test_bprule_child_notification_options(self):
        svc_cor = self._sched.services.find_srv_by_name_and_hostname("dummy", "bp_rule_child_notif")
        svc_cor.act_depend_of = []
        assert True is svc_cor.got_business_rule
        assert svc_cor.business_rule is not None

        svc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        hst2 = self._sched.hosts.find_by_name("test_host_02")

        assert ['w', 'u', 'c', 'r', 's'] == svc1.notification_options
        assert ['d', 'x', 'r', 's'] == hst2.notification_options

if __name__ == '__main__':
    unittest.main()
