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

from alignak.objects import Service
from alignak.objects import Servicegroup
from alignak_test import AlignakTest


class TestServiceGroup(AlignakTest):
    """
    This class tests the servicegroups
    """

    def test_servicegroup(self):
        """ Default configuration service groups

        Default configuration has no loading problems ... as of it servicegroups are parsed
        correctly
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        assert self.schedulers['scheduler-master'].conf.conf_is_correct

    def test_look_for_alias(self):
        """ Services groups alias

        Default configuration has no loading problems ... as such servicegroups are parsed correctly
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/servicegroup/alignak_groups_with_no_alias.cfg')
        assert self.schedulers['Default-Scheduler'].conf.conf_is_correct

        #  Found a servicegroup named NOALIAS
        sg = self.schedulers['Default-Scheduler'].sched.servicegroups.find_by_name("NOALIAS")
        assert isinstance(sg, Servicegroup)
        assert sg.get_name() == "NOALIAS"
        assert sg.alias == "NOALIAS"

    def test_servicegroup_members(self):
        """ Test if members are linked from group

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/servicegroup/alignak_servicegroup_members.cfg')
        assert self.schedulers['scheduler-master'].conf.conf_is_correct
        
        self._sched = self.schedulers['scheduler-master'].sched

        #  Found a servicegroup named allhosts_and_groups
        sg = self._sched.servicegroups.find_by_name("allservices_and_groups")
        assert isinstance(sg, Servicegroup)
        assert sg.get_name() == "allservices_and_groups"

        assert len(self._sched.servicegroups.get_members_of("allservices_and_groups")) == 1

        assert len(sg.get_services()) == 1

        assert len(sg.get_servicegroup_members()) == 4

    def test_members_servicegroup(self):
        """ Test if group is linked from the member

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/servicegroup/alignak_servicegroup_members.cfg')
        assert self.schedulers['scheduler-master'].conf.conf_is_correct
        self._sched = self.schedulers['scheduler-master'].sched

        #  Found a servicegroup named allhosts_and_groups
        sg = self._sched.servicegroups.find_by_name("allservices_and_groups")
        assert isinstance(sg, Servicegroup)
        assert sg.get_name() == "allservices_and_groups"

        assert len(self._sched.servicegroups.get_members_of("allservices_and_groups")) == 1

        assert len(sg.get_services()) == 1
        print("List servicegroup services:")
        for service_id in sg.members:
            print("Service id: %s (%s)" % (service_id, self._sched.services))
            service = self._sched.services[service_id]
            print("Service: %s" % service)
            assert isinstance(service, Service)

            if service.get_name() == 'test_ok_0':
                assert len(service.get_servicegroups()) == 4
                for group_id in service.servicegroups:
                    group = self._sched.servicegroups[group_id]
                    print("Group: %s" % group)
                    assert group.get_name() in [
                        'ok', 'servicegroup_01', 'servicegroup_02', 'allservices_and_groups'
                    ]

        assert len(sg.get_servicegroup_members()) == 4
        print("List servicegroup groups:")
        for group in sg.get_servicegroup_members():
            print("Group: %s" % group)
            assert group in [
                'servicegroup_01', 'servicegroup_02', 'servicegroup_03', 'servicegroup_04'
            ]

    def test_servicegroup_with_no_service(self):
        """ Allow servicegroups with no services

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/servicegroup/alignak_servicegroup_no_service.cfg')
        assert self.schedulers['scheduler-master'].conf.conf_is_correct

        self._sched = self.schedulers['scheduler-master'].sched

        # Found a servicegroup named void
        sg = self._sched.servicegroups.find_by_name("void")
        assert isinstance(sg, Servicegroup)
        assert sg.get_name() == "void"

        assert len(self._sched.servicegroups.get_members_of("void")) == 0

        print("Services: %s" % sg.get_servicegroup_members())
        assert len(sg.get_servicegroup_members()) == 0

        print("Services: %s" % sg.get_services())
        assert len(sg.get_services()) == 0

    def test_servicegroup_with_space(self):
        """ Test that servicegroups can have a name with spaces

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        assert self.schedulers['scheduler-master'].conf.conf_is_correct
        self._sched = self.schedulers['scheduler-master'].sched

        self.nb_servicegroups = len(self._sched.servicegroups)

        self.setup_with_file('cfg/servicegroup/alignak_servicegroup_with_space.cfg')
        assert self.schedulers['scheduler-master'].conf.conf_is_correct
        self._sched = self.schedulers['scheduler-master'].sched

        # Two more groups than the former default configuration
        assert len(self._sched.servicegroups) == self.nb_servicegroups + 2

        assert self._sched.servicegroups.find_by_name("test_With Spaces").get_name() == \
               "test_With Spaces"
        assert self._sched.servicegroups.get_members_of("test_With Spaces") is not []

        assert self._sched.servicegroups.find_by_name("test_With another Spaces").get_name() == \
            "test_With another Spaces"
        assert self._sched.servicegroups.get_members_of("test_With another Spaces") is not []

    def test_servicegroups_generated(self):
        """ Test that servicegroups can be built from service definition

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/servicegroup/alignak_servicegroups_generated.cfg')
        assert self.schedulers['scheduler-master'].conf.conf_is_correct
        self._sched = self.schedulers['scheduler-master'].sched

        self.nb_servicegroups = len(self._sched.servicegroups)

        sgs = []
        for name in ["MYSVCGP", "MYSVCGP2", "MYSVCGP3", "MYSVCGP4"]:
            sg = self._sched.servicegroups.find_by_name(name)
            assert sg is not None
            print("SG: %s, members: %s" % (sg, sg.get_members()))
            sgs.append(sg)

        svc3 = self._sched.services.find_srv_by_name_and_hostname("fake host", "fake svc3")
        svc4 = self._sched.services.find_srv_by_name_and_hostname("fake host", "fake svc4")
        print sgs[0].get_members()
        assert svc3.uuid in sgs[0].members
        assert svc3.uuid in sgs[1].members
        assert svc4.uuid in sgs[2].members
        assert svc4.uuid in sgs[3].members

        assert sgs[0].uuid in svc3.servicegroups
        assert sgs[1].uuid in svc3.servicegroups
        assert sgs[2].uuid in svc4.servicegroups
        assert sgs[3].uuid in svc4.servicegroups
