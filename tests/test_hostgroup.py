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

"""
This file contains the test for the hostgroups objects
"""

import time

from alignak.objects import Host
from alignak.objects import Hostgroup
from .alignak_test import AlignakTest
import pytest


class TestHostGroup(AlignakTest):
    """
    This class tests the hostgroups
    """
    def setUp(self):
        super(TestHostGroup, self).setUp()

    def test_hostgroup(self):
        """
        Default configuration has no loading problems ... as of it hostgroups are parsed correctly
        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

    def test_multiple_hostgroup_definition(self):
        """
        No error when the same group is defined twice in an host/service or
        when a host/service is defined twice in a group
        :return: None
        """
        self.setup_with_file('cfg/hostgroup/multiple_hostgroup.cfg')

        print("Get the hosts and services")
        host = self._scheduler.hosts.find_by_name("will crash")
        assert host is not None
        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "will crash", "Crash")
        assert svc is not None

        grp = self._scheduler.hostgroups.find_by_name("hg-sample")
        assert grp is not None
        assert host.uuid in grp.members

        grp = self._scheduler.servicegroups.find_by_name("Crashed")
        assert grp is not None
        assert svc.uuid in grp.members

    def test_multiple_not_hostgroup_definition(self):
        """
        No error when the same group is defined twice in an host/service
        :return: None
        """
        self.setup_with_file('cfg/hostgroup/multiple_not_hostgroup.cfg')

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "hst_in_BIG", "THE_SERVICE")
        assert svc is not None

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "hst_in_IncludeLast", "THE_SERVICE")
        assert svc is not None

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "hst_in_NotOne", "THE_SERVICE")
        # Not present!
        assert svc is None

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "hst_in_NotTwo", "THE_SERVICE")
        # Not present!
        assert svc is None

    def test_bad_hostgroup(self):
        """ Test bad hostgroups in the configuration
        :return: None
        """
        with pytest.raises(SystemExit):
            self.setup_with_file('cfg/cfg_bad_hostgroup.cfg')

        # Configuration is not ok
        assert self.conf_is_correct == False

        # 5 error messages, bad hostgroup member
        assert len(self.configuration_errors) == 5
        # No warning messages
        assert len(self.configuration_warnings) == 0
        # Error is an unknown member in a group (\ escape the [ and ' ...)
        self.assert_any_cfg_log_match(
            "\[hostgroup::allhosts_bad\] as hostgroup, got unknown member \'BAD_HOST\'"
        )
        self.assert_any_cfg_log_match(
            "Configuration in hostgroup::allhosts_bad is incorrect; from: "
        )
        self.assert_any_cfg_log_match(
            "the hostgroup allhosts_bad_realm got an unknown realm \'Unknown\'"
        )
        self.assert_any_cfg_log_match(
            "Configuration in hostgroup::allhosts_bad_realm is incorrect; from: "
        )
        self.assert_any_cfg_log_match(
            "hostgroups configuration is incorrect!"
        )

    def test_look_for_alias(self):
        """ Hostgroups alias
        :return: None
        """
        self.setup_with_file('cfg/hostgroup/alignak_groups_with_no_alias.cfg')

        #  Found a hostgroup named NOALIAS
        hg = self._scheduler.hostgroups.find_by_name("NOALIAS")
        assert isinstance(hg, Hostgroup)
        assert hg.get_name() == "NOALIAS"
        assert hg.alias == "NOALIAS"

    def test_hostgroup_members(self):
        """ Test if members are linked from group

        :return: None
        """
        self.setup_with_file('cfg/hostgroup/alignak_hostgroup_members.cfg')

        #  Found a hostgroup named allhosts_and_groups
        hg = self._scheduler.hostgroups.find_by_name("allhosts_and_groups")
        assert isinstance(hg, Hostgroup)
        assert hg.get_name() == "allhosts_and_groups"

        assert len(self._scheduler.hostgroups.get_members_of_group("allhosts_and_groups")) == \
            2

        assert len(hg.hostgroup_members) == 4
        assert len(hg.get_hostgroup_members()) == 4

        assert len(hg.get_hosts()) == 2

    def test_members_hostgroup(self):
        """ Test if group is linked from the member
        :return: None
        """
        self.setup_with_file('cfg/hostgroup/alignak_hostgroup_members.cfg')

        #  Found a hostgroup named allhosts_and_groups
        hg = self._scheduler.hostgroups.find_by_name("allhosts_and_groups")
        assert isinstance(hg, Hostgroup)
        assert hg.get_name() == "allhosts_and_groups"

        assert len(self._scheduler.hostgroups.get_members_of_group("allhosts_and_groups")) == 2

        assert len(hg.get_hosts()) == 2
        print("List hostgroup hosts:")
        for host_id in hg.members:
            host = self._scheduler.hosts[host_id]
            print(("Host: %s" % host))
            assert isinstance(host, Host)

            if host.get_name() == 'test_router_0':
                assert len(host.get_hostgroups()) == 3
                for group_id in host.hostgroups:
                    group = self._scheduler.hostgroups[group_id]
                    print(("Group: %s" % group))
                    assert group.get_name() in [
                        'router', 'allhosts', 'allhosts_and_groups'
                    ]

            if host.get_name() == 'test_host_0':
                assert len(host.get_hostgroups()) == 4
                for group_id in host.hostgroups:
                    group = self._scheduler.hostgroups[group_id]
                    print(("Group: %s" % group))
                    assert group.get_name() in [
                        'allhosts', 'allhosts_and_groups', 'up', 'hostgroup_01'
                    ]

        assert len(hg.get_hostgroup_members()) == 4
        print("List hostgroup groups:")
        for group in hg.get_hostgroup_members():
            print(("Group: %s" % group))
            assert group in [
                'hostgroup_01', 'hostgroup_02', 'hostgroup_03', 'hostgroup_04'
            ]

    def test_hostgroup_with_no_host(self):
        """ Allow hostgroups with no hosts
        :return: None
        """
        self.setup_with_file('cfg/hostgroup/alignak_hostgroup_no_host.cfg')

        # Found a hostgroup named void
        hg = self._scheduler.hostgroups.find_by_name("void")
        assert isinstance(hg, Hostgroup)
        assert hg.get_name() == "void"

        assert len(self._scheduler.hostgroups.get_members_of_group("void")) == 0

        assert len(hg.get_hostgroup_members()) == 0

        assert len(hg.get_hosts()) == 0

    def test_hostgroup_with_space(self):
        """ Test that hostgroups can have a name with spaces
        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')
        self.nb_hostgroups = len(self._scheduler.hostgroups)

        self.setup_with_file('cfg/hostgroup/alignak_hostgroup_with_space.cfg')

        # Two more groups than the default configuration
        assert len(self._scheduler.hostgroups) == self.nb_hostgroups + 2

        assert self._scheduler.hostgroups.find_by_name("test_With Spaces").get_name() == \
               "test_With Spaces"
        assert self._scheduler.hostgroups.get_members_of_group(
                "test_With Spaces"
            ) is not \
            []

        assert self._scheduler.hostgroups.find_by_name("test_With another Spaces").get_name() == \
            "test_With another Spaces"
        assert self._scheduler.hostgroups.get_members_of_group(
                "test_With another Spaces"
            ) is not \
            []

    def test_service_hostgroup(self):
        """Test hosts services inherited from a hostgroups property in service definition

        :return: None
        """
        self.setup_with_file('cfg/hostgroup/hostgroups_from_service.cfg')

        #  Search a hostgroup named tcp_hosts
        hg = self._scheduler.hostgroups.find_by_name("tcp_hosts")
        assert isinstance(hg, Hostgroup)
        print((hg.__dict__))

        assert len(self._scheduler.hostgroups.get_members_of_group("tcp_hosts")) == 3

        assert len(hg.members) == 3
        assert len(hg.hostgroup_members) == 0

        assert len(hg.get_hosts()) == 3
        print("Hostgroup hosts:")
        for host_id in hg.members:
            host = self._scheduler.hosts[host_id]
            print(("- host: %s" % host.get_name()))
            assert len(host.services) > 0
            for service_uuid in host.services:
                service = self._scheduler.services[service_uuid]
                print(("  has a service: %s" % service.get_name()))
                assert 'TCP' == service.get_name()
