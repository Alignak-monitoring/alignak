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

import os
import time

from alignak_test import (
    AlignakTest, time_hacker, unittest
)

from alignak.modulesmanager import ModulesManager
from alignak.objects.module import Module
from alignak.log import logger

modules_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'module_missing_imported_from_module_property')


class TestMissingimportedFrom(AlignakTest):

    def setUp(self):
        #logger.setLevel('DEBUG')
        self.setup_with_file(['etc/alignak_missing_imported_from_module_property.cfg'])

    # we are loading a module (dummy_arbiter) that is givving objects WITHOUT
    # setting imported_from. One host got a warning, and this can crash without the imported_from setting
    # in the arbiterdaemon part.
    def test_missing_imported_from(self):
        self.assertTrue(self.sched.conf.is_correct)
    


if __name__ == '__main__':
    unittest.main()
