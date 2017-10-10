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
"""
This file test the cleaning queue in scheduler
"""

import time
from alignak_test import AlignakTest


class TestSchedulerCleanQueue(AlignakTest):
    """
    This class test the cleaning queue in scheduler
    """

    def test_clean_broks(self):
        """ Test clean broks in scheduler

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        # Define clean queue each time for the test
        self._scheduler.update_recurrent_works_tick({'clean_queues': 1000})

        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 0, 'OK']])
        time.sleep(0.1)
        brok_limit = 5 * (len(self._scheduler.hosts) +
                          len(self._scheduler.services))
        brok_limit += 1
        assert len(self._scheduler.broks) < brok_limit

        for _ in xrange(0, 10):
            self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 1, 'WARNING']])
            time.sleep(0.1)
            self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 0, 'OK']])
            time.sleep(0.1)
        assert len(self._scheduler.broks) > brok_limit
        self._scheduler.update_recurrent_works_tick('clean_queues', 1)
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 1, 'WARNING']])
        assert len(self._scheduler.broks) <= brok_limit

    def test_clean_checks(self):
        """ Test clean checks in scheduler

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.event_handler_enabled = False

        # Define clean queue each time for the test
        self._scheduler.update_recurrent_works_tick({'clean_queues': 1})

        self._scheduler.update_recurrent_works_tick('delete_zombie_checks', 1000)

        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 0, 'OK']])
        time.sleep(0.1)
        check_limit = 5 * (len(self._scheduler.hosts) +
                           len(self._scheduler.services))
        check_limit += 1
        assert len(self._scheduler.checks) < check_limit

        for _ in xrange(0, (check_limit + 10)):
            host.next_chk = time.time()
            chk = host.launch_check(host.next_chk,
                                    self._scheduler.hosts,
                                    self._scheduler.services,
                                    self._scheduler.timeperiods,
                                    self._scheduler.macromodulations,
                                    self._scheduler.checkmodulations,
                                    self._scheduler.checks,
                                    force=False)
            self._scheduler.add_check(chk)
            time.sleep(0.1)
        assert len(self._scheduler.checks) > check_limit
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 1, 'WARNING']])
        assert len(self._scheduler.checks) <= check_limit

    def test_clean_actions(self):
        """ Test clean actions in scheduler (like notifications)

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        # Define clean queue each time for the test
        self._scheduler.update_recurrent_works_tick({'clean_queues': 1000})
        self._scheduler.update_recurrent_works_tick({'delete_zombie_actions': 1000})

        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 0, 'OK']])
        time.sleep(0.1)
        action_limit = 5 * (len(self._scheduler.hosts) +
                            len(self._scheduler.services))
        action_limit += 1
        assert len(self._scheduler.actions) < action_limit

        for _ in xrange(0, 10):
            self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 1, 'WARNING']])
            time.sleep(0.1)
            self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 0, 'OK']])
            time.sleep(0.1)
        assert len(self._scheduler.actions) > action_limit
        self._scheduler.update_recurrent_works_tick({'clean_queues': 1})
        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 1, 'WARNING']])
        assert len(self._scheduler.actions) <= action_limit
