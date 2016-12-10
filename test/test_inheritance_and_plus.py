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

from alignak_test import *


class TestInheritanceAndPlus(AlignakTest):

    def setUp(self):
        self.setup_with_file('cfg/cfg_inheritance_and_plus.cfg')
        assert self.conf_is_correct
        self._sched = self.schedulers['scheduler-master'].sched

    def test_inheritance_and_plus(self):
        """Test properties inheritance with + sign
        """
        # Get the hostgroups
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
        assert len(host1.hostgroups) == 2
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


if __name__ == '__main__':
    unittest.main()
