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


class TestNoHostCheck(AlignakTest):

    def setUp(self):
        self.setup_with_file(['etc/alignak_not_execute_host_check.cfg'])

    # We must look taht host checks are disable, and services ones are running
    def test_no_host_check(self):
        #
        # Config is not correct because of a wrong relative path
        # in the main config file
        #
        print "Get the hosts and services"
        now = time.time()
        host = self.sched.hosts.find_by_name("test_host_0")
        print host.checks_in_progress
        self.assertEqual(0, len(host.checks_in_progress))
        #
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        print svc.checks_in_progress
        self.assertNotEqual(len(svc.checks_in_progress), 0)

        # Now launch passive checks
        cmd = "[%lu] PROCESS_HOST_CHECK_RESULT;test_host_0;1;bobo" % now
        self.sched.run_external_command(cmd)

        self.scheduler_loop(2, [])

        print "Output", host.output
        self.assertEqual('bobo', host.output)

        # Now disable passive host check
        cmd = "[%lu] STOP_ACCEPTING_PASSIVE_HOST_CHECKS" % now
        self.sched.run_external_command(cmd)

        # And now run a new command
        cmd = "[%lu] PROCESS_HOST_CHECK_RESULT;test_host_0;1;bobo2" % now
        self.sched.run_external_command(cmd)

        self.scheduler_loop(2, [])

        # This should NOT change this time
        print "Output", host.output
        self.assertEqual('bobo', host.output)



if __name__ == '__main__':
    unittest.main()
