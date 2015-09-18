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


class TestCreateLinkFromExtCmd(AlignakTest):

    def test_simple_host_link(self):
        now = int(time.time())
        h = self.sched.hosts.find_by_name('test_host_0')
        self.assertIsNot(h, None)
        h.act_depend_of = []
        r = self.sched.hosts.find_by_name('test_router_0')
        self.assertIsNot(r, None)
        r.act_depend_of = []
        e = ExternalCommandManager(self.conf, 'dispatcher')
        cmd = "[%lu] ADD_SIMPLE_HOST_DEPENDENCY;test_host_0;test_router_0" % now
        self.sched.run_external_command(cmd)
        self.assertTrue(h.is_linked_with_host(r))

        # Now we remove this link
        cmd = "[%lu] DEL_HOST_DEPENDENCY;test_host_0;test_router_0" % now
        self.sched.run_external_command(cmd)
        self.assertFalse(h.is_linked_with_host(r))



if __name__ == '__main__':
    unittest.main()
