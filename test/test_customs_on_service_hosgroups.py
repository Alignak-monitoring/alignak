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
# This file is used to test reading and processing of config files
#

from alignak_test import AlignakTest


class TestCustomsonservicehosgroups(AlignakTest):
    """
    Class for testing custom macros on service hostgroups
    """


    def setUp(self):
        self.setup_with_file('cfg/cfg_customs_on_service_hosgroups.cfg')
        self._sched = self._scheduler

    # We look for 3 services: on defined as direct on 1 hosts, on other
    # on 2 hsots, and a last one on a hostgroup
    def test_check_for_custom_copy_on_serice_hostgroups(self):
        """
        Test custom macros on service hostgroups
        """
        # The one host service
        svc_one_host = self._sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                          "test_on_1_host")
        assert svc_one_host is not None
        # The 2 hosts service(s)
        svc_two_hosts_1 = self._sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                             "test_on_2_hosts")
        assert svc_two_hosts_1 is not None
        svc_two_hosts_2 = self._sched.services.find_srv_by_name_and_hostname("test_router_0",
                                                                             "test_on_2_hosts")
        assert svc_two_hosts_2 is not None
        # Then the one defined on a hostgroup
        svc_on_group = self._sched.services.find_srv_by_name_and_hostname("test_router_0",
                                                                          "test_on_group")
        assert svc_on_group is not None

        # Each one should have customs
        assert 'custvalue' == svc_one_host.customs['_CUSTNAME']
        assert 'custvalue' == svc_two_hosts_1.customs['_CUSTNAME']
        assert 'custvalue' == svc_two_hosts_2.customs['_CUSTNAME']
        assert 'custvalue' == svc_on_group.customs['_CUSTNAME']


if __name__ == '__main__':
    unittest2.main()
