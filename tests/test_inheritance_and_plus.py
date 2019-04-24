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
#     Grégory Starck, g.starck@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Jean Gabes, naparuba@gmail.com
#     Alexander Springer, alex.spri@gmail.com
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

from pprint import pprint
from .alignak_test import *


class TestInheritanceAndPlus(AlignakTest):

    def setUp(self):
        super(TestInheritanceAndPlus, self).setUp()

    def test_inheritance(self):
        """Test properties inheritance
        """
        self.setup_with_file('cfg/cfg_inheritance.cfg')
        assert self.conf_is_correct
        self._sched = self._scheduler

        print("Hosts: ")
        pprint(self._sched.hosts.__dict__)

        print("Services: ")
        pprint(self._sched.services.__dict__)

        print("Contacts: ")
        pprint(self._sched.contacts.__dict__)

        # common objects
        tp_24x7 = self._sched.timeperiods.find_by_name("24x7")
        tp_none = self._sched.timeperiods.find_by_name("none")
        tp_work = self._sched.timeperiods.find_by_name("work")
        cgtest = self._sched.contactgroups.find_by_name("test_contact")
        cgadm = self._sched.contactgroups.find_by_name("admins")
        cmdsvc = self._sched.commands.find_by_name("check_service")
        cmdtest = self._sched.commands.find_by_name("dummy_command")

        # Checks we got the objects we need
        assert tp_24x7 is not None
        assert tp_work is not None
        assert cgtest is not None
        assert cgadm is not None
        assert cmdsvc is not None
        assert cmdtest is not None

        # Contacts
        c_admin = self._sched.contacts.find_by_name("admin")
        assert c_admin is not None
        # admin inherits from a generic-contact
        print(c_admin.tags)
        assert c_admin.tags == set(['generic-contact'])
        assert c_admin.email == 'alignak@localhost'
        assert c_admin.host_notifications_enabled is True
        assert c_admin.service_notifications_enabled is True

        c_not_notified = self._sched.contacts.find_by_name("no_notif")
        assert c_not_notified is not None
        # no_notif inherits from a not-notified
        print(c_not_notified.tags)
        assert c_not_notified.tags == set([u'generic-contact', u'not_notified'])
        assert c_not_notified.email == 'none'
        # TODO: uncomment!
        # Issue #1024 - contact templates inheritance
        assert c_not_notified.host_notifications_enabled is False
        assert c_not_notified.service_notifications_enabled is False

        # Hosts
        test_host_0 = self._sched.hosts.find_by_name("test_host_0")
        assert test_host_0 is not None
        test_router_0 = self._sched.hosts.find_by_name("test_router_0")
        assert test_router_0 is not None

        hst1 = self._sched.hosts.find_by_name("test_host_01")
        assert hst1 is not None
        assert hst1.tags == set(['generic-host', 'srv'])
        assert hst1.check_period == tp_none.uuid

        hst2 = self._sched.hosts.find_by_name("test_host_02")
        assert hst2 is not None
        assert hst2.check_period == tp_work.uuid

        # Services
        # svc1 = self._sched.services.find_by_name("test_host_01/srv-svc")
        # svc2 = self._sched.services.find_by_name("test_host_02/srv-svc")
        # assert svc1 is not None
        # assert svc2 is not None

        # Inherited services (through hostgroup property)
        # Those services are attached to all hosts of an hostgroup and they both
        # inherit from the srv-from-hostgroup template
        svc12 = self._sched.services.find_srv_by_name_and_hostname("test_host_01",
                                                                   "srv-from-hostgroup")
        assert svc12 is not None

        # business_impact inherited
        assert svc12.business_impact == 5
        # maintenance_period none inherited from the service template
        assert svc12.maintenance_period == tp_24x7.uuid

        assert svc12.use == ['generic-service']
        # Todo: explain why we do not have generic-service in tags ...
        assert svc12.tags == set([])

        svc22 = self._sched.services.find_srv_by_name_and_hostname("test_host_02",
                                                                   "srv-from-hostgroup")
        # business_impact inherited
        assert svc22.business_impact == 5
        # maintenance_period none inherited from the service template
        assert svc22.maintenance_period == tp_24x7.uuid

        assert svc22 is not None
        assert svc22.use == ['generic-service']
        assert svc22.tags == set([])
        # maintenance_period none inherited...
        assert svc22.maintenance_period == tp_24x7.uuid

        # Duplicate for each services (generic services for each host inheriting from srv template)
        svc1proc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "proc proc1")
        svc1proc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_01", "proc proc2")
        svc2proc1 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "proc proc1")
        svc2proc2 = self._sched.services.find_srv_by_name_and_hostname("test_host_02", "proc proc2")
        assert svc1proc1 is not None
        assert svc1proc2 is not None
        assert svc2proc1 is not None
        assert svc2proc2 is not None

    def test_inheritance_and_plus(self):
        """Test properties inheritance with + sign
        """
        self.setup_with_file('cfg/cfg_inheritance_and_plus.cfg')
        assert self.conf_is_correct
        self._sched = self._scheduler

        # Get the hostgroups
        servers = self._sched.hostgroups.find_by_name('servers')
        assert servers is not None
        linux = self._sched.hostgroups.find_by_name('linux')
        assert linux is not None
        dmz = self._sched.hostgroups.find_by_name('DMZ')
        assert dmz is not None
        mysql = self._sched.hostgroups.find_by_name('mysql')
        assert mysql is not None

        # Get the hosts
        host1 = self._sched.hosts.find_by_name("test-server1")
        host2 = self._sched.hosts.find_by_name("test-server2")

        # HOST 1 is using templates: linux-servers,dmz, so it should be in
        # the hostsgroups named "linux" AND "DMZ"
        assert len(host1.hostgroups) == 3
        assert servers.uuid in host1.hostgroups
        assert linux.uuid in host1.hostgroups
        assert dmz.uuid in host1.hostgroups
        assert mysql.uuid not in host1.hostgroups

        # HOST2 is using templates linux-servers,dmz and is hostgroups +mysql,
        # so it should be in all three hostgroups
        assert linux.uuid in host2.hostgroups
        assert dmz.uuid in host2.hostgroups
        assert mysql.uuid in host2.hostgroups

        # Get the servicegroups
        generic = self._sched.servicegroups.find_by_name('generic-sg')
        assert generic is not None
        another = self._sched.servicegroups.find_by_name('another-sg')
        assert another is not None

        # Get the service
        service = self._sched.services.find_srv_by_name_and_hostname("pack-host", 'CHILDSERV')
        assert service is not None

        # The service inherits from a template with a service group and it has
        # its own +servicegroup so it should be in both groups
        assert generic.uuid in service.servicegroups
        assert another.uuid in service.servicegroups

        # Get another service, built by host/service templates relation
        service = self._sched.services.find_srv_by_name_and_hostname('pack-host', 'CHECK-123')
        assert service is not None

        # The service should have inherited the custom variable `_CUSTOM_123` because custom
        # variables are always stored in upper case
        assert '_CUSTOM_123' in service.customs

