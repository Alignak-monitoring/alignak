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
"""
 This file is used to test poller tags
"""
from alignak_test import AlignakTest


class TestPollerTag(AlignakTest):
    """This class tests the poller tag  of check
    """
    def setUp(self):
        """
        For each test load and check the configuration
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_poller_tag.cfg')
        self.assertTrue(self.conf_is_correct)

        # Our scheduler
        self._sched = self.schedulers['scheduler-master'].sched

        # Our pollers
        #print self._sched.pollers
        #self._pollerm = self._sched.pollers['poller-master']
        #self._pollern = self._sched.pollers['poller-north']
        #self._pollers = self._sched.pollers['poller-south']

        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertEqual(len(self.configuration_warnings), 0)

    def test_poller_tag_command(self):
        """We have a command defined with poller_tag: north

        :return:None
        """
        self.print_header()
        host = self._sched.hosts.find_by_name("test_host_pt_01")
        self.external_command_loop()
        checks = self.schedulers['scheduler-master'].sched.checks.values()
        mycheck = self._sched.checks[host.checks_in_progress[0]]
        assert mycheck.poller_tag == 'north'

    def test_poller_tag_host(self):
        """We have a host with a poller_tag: south

        :return: None
        """
        self.print_header()
        host = self._sched.hosts.find_by_name("test_host_pt_02")
        self.external_command_loop()
        checks = self.schedulers['scheduler-master'].sched.checks.values()
        mycheck = self._sched.checks[host.checks_in_progress[0]]
        assert mycheck.poller_tag == 'south'

    def test_poller_tag_host_command(self):
        """We have a command with poller_tag: north
        and a host with poller_tag: south

        :return: None
        """
        self.print_header()
        host = self._sched.hosts.find_by_name("test_host_pt_03")
        self.external_command_loop()
        checks = self.schedulers['scheduler-master'].sched.checks.values()
        mycheck = self._sched.checks[host.checks_in_progress[0]]
        assert mycheck.poller_tag == 'south'

    def test_poller_tag_service(self):
        """We have a service with a poller_tag: north

        :return: None
        """
        self.print_header()
        svc = self._sched.services.find_srv_by_name_and_hostname("test_router_0", "test_ok_pt_01")
        svc.checks_in_progress = []
        svc.act_depend_of = []
        self.external_command_loop()
        checks = self.schedulers['scheduler-master'].sched.checks.values()
        mycheck = self._sched.checks[svc.checks_in_progress[0]]
        assert mycheck.poller_tag == 'north'

    def test_poller_tag_service_command(self):
        """We have a service with a poller_tag: south
        and a command with poller_tag: north

        :return: None
        """
        self.print_header()
        svc = self._sched.services.find_srv_by_name_and_hostname("test_router_0", "test_ok_pt_02")
        svc.checks_in_progress = []
        svc.act_depend_of = []
        self.external_command_loop()
        checks = self.schedulers['scheduler-master'].sched.checks.values()
        mycheck = self._sched.checks[svc.checks_in_progress[0]]
        assert mycheck.poller_tag == 'south'

    def test_poller_tag_service_host(self):
        """We have a service with a poller_tag: north
        and a host with poller_tag: south

        :return: None
        """
        self.print_header()
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_pt_02", "test_ok_pt_03")
        svc.checks_in_progress = []
        svc.act_depend_of = []
        self.external_command_loop()
        checks = self.schedulers['scheduler-master'].sched.checks.values()
        mycheck = self._sched.checks[svc.checks_in_progress[0]]
        assert mycheck.poller_tag == 'north'

    def test_poller_master_get_checks(self):
        """Test function get right checks based on the poller_tag: None (it's the default tag)

        :return: None
        """
        self.print_header()
        self.external_command_loop()
        for check in self._sched.checks.values():
            check.t_to_go = 0
        checks = self._sched.get_to_run_checks(do_checks=True, poller_tags=['None'],
                                               module_types=['fork'])
        print checks
        assert len(checks) == 3
        for check in checks:
            assert check.poller_tag == 'None'

    def test_poller_north_get_checks(self):
        """Test function get right checks based on the poller_tag: north

        :return: None
        """
        self.print_header()
        self.external_command_loop()
        for check in self._sched.checks.values():
            check.t_to_go = 0
        checks = self._sched.get_to_run_checks(do_checks=True, poller_tags=['north'],
                                               module_types=['fork'])
        print checks
        assert len(checks) == 3
        for check in checks:
            assert check.poller_tag == 'north'

    def test_poller_south_get_checks(self):
        """
        Test function get right checks based on the poller_tag: south

        :return: None
        """
        self.print_header()
        self.external_command_loop()
        for check in self._sched.checks.values():
            check.t_to_go = 0
        checks = self._sched.get_to_run_checks(do_checks=True, poller_tags=['south'],
                                               module_types=['fork'])
        print checks
        assert len(checks) == 4
        for check in checks:
            assert check.poller_tag == 'south'


if __name__ == '__main__':
    AlignakTest.main()
