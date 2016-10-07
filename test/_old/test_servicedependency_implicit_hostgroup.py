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

from alignak_test import *


class TestServiceDepAndGroups(AlignakTest):
    def setUp(self):
        self.setup_with_file(['etc/alignak_servicedependency_implicit_hostgroup.cfg'])

    def test_implicithostgroups(self):
        #
        # Config is not correct because of a wrong relative path
        # in the main config file
        #
        print "Get the hosts and services"
        now = time.time()
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc_postfix = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "POSTFIX")
        self.assertIsNot(svc_postfix, None)

        svc_snmp = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "SNMP")
        self.assertIsNot(svc_snmp, None)

        svc_cpu = self.sched.services.find_srv_by_name_and_hostname("test_router_0", "CPU")
        self.assertIsNot(svc_cpu, None)

        svc_snmp2 = self.sched.services.find_srv_by_name_and_hostname("test_router_0", "SNMP")
        self.assertIsNot(svc_snmp2, None)

        self.assertIn(svc_snmp2.uuid, [c[0] for c in svc_postfix.act_depend_of])
        self.assertIn(svc_snmp.uuid, [c[0] for c in svc_postfix.act_depend_of])
        self.assertIn(svc_snmp2.uuid, [c[0] for c in svc_cpu.act_depend_of])
        self.assertIn(svc_snmp.uuid, [c[0] for c in svc_cpu.act_depend_of])

        svc.act_depend_of = []  # no hostchecks on critical checkresults

    def test_implicithostnames(self):
        #
        # Config is not correct because of a wrong relative path
        # in the main config file
        #
        print "Get the hosts and services"
        now = time.time()
        svc_postfix = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "POSTFIX_BYSSH")
        self.assertIsNot(svc_postfix, None)

        svc_ssh = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "SSH")
        self.assertIsNot(svc_ssh, None)

        svc_cpu = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "CPU_BYSSH")
        self.assertIsNot(svc_cpu, None)

        self.assertIn(svc_ssh.uuid, [c[0] for c in svc_postfix.act_depend_of])
        self.assertIn(svc_ssh.uuid, [c[0] for c in svc_cpu.act_depend_of])



if __name__ == '__main__':
    unittest.main()
