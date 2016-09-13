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

"""
This file test all cases of eventhandler
"""

import time

from alignak.objects import Host
from alignak.objects import Hostgroup
from alignak_test import AlignakTest


class TestHostDependency(AlignakTest):
    """
    This class tests the hostdependency
    """

    def test_hostdependencies(self):
        """
        Default configuration has no loading problems ... as of it hosts
        dependencies are parsed correctly
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        self.assertTrue(self.schedulers[0].conf.conf_is_correct)

    def test_hostdep_simple(self):
        """
        test_host_1 dependes upon test_host_0
        test_router_0 is parent of test_host_1
        all the hosts in flap group dependes upon test_host_0
        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/hostdependency/alignak_hostdep_with_no_depname.cfg')
        self.assertTrue(self.schedulers[0].conf.conf_is_correct)

        print("Get the hosts and services")
        test_router_0 = self.schedulers[0].sched.hosts.find_by_name("test_router_0")
        self.assertIsNotNone(test_router_0)
        print("test_router_0 is: %s" % test_router_0.uuid)
        print("test_router_0 'parents': %s" % test_router_0.act_depend_of)
        print("test_router_0 'children': %s" % test_router_0.act_depend_of_me)

        test_host_0 = self.schedulers[0].sched.hosts.find_by_name("test_host_0")
        self.assertIsNotNone(test_host_0)
        print("test_host_0 is: %s" % test_host_0.uuid)
        print("test_host_0 'parents': %s" % test_host_0.act_depend_of)
        print("test_host_0 'children': %s" % test_host_0.act_depend_of_me)

        svc_0 = self.schedulers[0].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0"
        )

        test_host_1 = self.schedulers[0].sched.hosts.find_by_name("test_host_1")
        self.assertIsNotNone(test_host_1)
        print("test_host_1 is: %s" % test_host_1.uuid)
        print("test_host_1 'parents': %s" % test_host_1.act_depend_of)
        print("test_host_1 'children': %s" % test_host_1.act_depend_of_me)

        # test_router_0 is a dependency of test_host_0 and test_host_1
        self.assertEqual(len(test_router_0.act_depend_of_me), 2)
        for link in test_router_0.act_depend_of_me:
            item_id = link[0]
            self.assertIn(item_id, [test_host_0.uuid, test_host_1.uuid])

        # test_host_0 depends upon test_router_0
        self.assertEqual(len(test_host_0.act_depend_of), 1)
        for link in test_host_0.act_depend_of:
            item_id = link[0]
            self.assertIn(item_id, [test_router_0.uuid])

        # test_host_0 is a dependency of test_host_1 and of a service
        self.assertEqual(len(test_host_0.act_depend_of_me), 2)
        for link in test_host_0.act_depend_of_me:
            item_id = link[0]
            self.assertIn(item_id, [test_host_1.uuid, svc_0.uuid])

        # test_host_1 depends upon test_host_0 and test_router_0
        self.assertEqual(len(test_host_1.act_depend_of), 2)
        for link in test_host_1.act_depend_of:
            item_id = link[0]
            self.assertIn(item_id, [test_host_0.uuid, test_router_0.uuid])

    def test_hostdep_complex(self):
        """
        test_host_1 dependes upon test_host_0
        test_router_0 is parent of test_host_1
        all the hosts in flap group dependes upon test_host_0
        :return:
        """
        self.print_header()
        self.setup_with_file('cfg/hostdependency/alignak_hostdep_with_multiple_names.cfg')
        self.assertTrue(self.schedulers[0].conf.conf_is_correct)

        for n in ['svn1', 'svn2', 'svn3', 'svn4', 'nas1', 'nas2', 'nas3']:
            host = globals()[n] = self.schedulers[0].sched.hosts.find_by_name(n)
            self.assertIsNotNone(host)

        # We check that nas3 is a father of svn4, the simple case
        self.assertIn(nas3.uuid, [e[0] for e in svn4.act_depend_of])

        # Now the more complex one
        for son in [svn1, svn2, svn3]:
            for father in [nas1, nas2]:
                print 'Checking if', father.get_name(), 'is the father of', son.get_name()
                print son.act_depend_of
                for e in son.act_depend_of:
                    print self.schedulers[0].sched.find_item_by_id(e[0]).get_name()
                self.assertIn(father.uuid, [e[0] for e in son.act_depend_of])

