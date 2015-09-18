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
#     Grégory Starck, g.starck@gmail.com
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe SIMON, christophe.simon@dailymotion.com

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
# This file is used to test multi valued attribute feature.
#

import re
from alignak_test import unittest, AlignakTest


class TestMultiVuledAttributes(AlignakTest):

    def setUp(self):
        self.setup_with_file(['etc/alignak_multi_attribute.cfg'])

    def test_multi_valued_attributes(self):
        hst1 = self.sched.hosts.find_by_name("test_host_01")
        srv1 = self.sched.services.find_srv_by_name_and_hostname("test_host_01", "srv1")
        self.assertIsNot(hst1, None)
        self.assertIsNot(srv1, None)

        # inherited parameter
        self.assertIs(True, hst1.active_checks_enabled)
        self.assertIs(True, srv1.active_checks_enabled)

        # non list parameter (only the last value set should remain)
        self.assertEqual(3, hst1.max_check_attempts)
        self.assertEqual(3, srv1.max_check_attempts)

        # list parameter (all items should appear in the order they are defined)
        self.assertEqual(set([u'd', u'f', u'1', u's', u'r', u'u']), set(hst1.notification_options))

        self.assertEqual(set([u'c', u'f', u'1', u's', u'r', u'u', u'w']),
                         set(srv1.notification_options))



if __name__ == '__main__':
    unittest.main()
