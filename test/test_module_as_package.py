#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

from os.path import abspath, dirname, join

from alignak_test import unittest, AlignakTest

from alignak.objects.module import Module
from alignak.modulesmanager import ModulesManager



modules_dir = join(dirname(abspath(__file__)), 'test_module_as_package')

class TestModuleManager_And_Packages(AlignakTest):
    ''' Test to make sure that we correctly import alignak modules.
    '''

    def test_conflicting_modules(self):

        # prepare 2 modconfs:
        modconfA = Module({'module_name': 'whatever', 'module_type': 'modA'})
        modconfB = Module({'module_name': '42',       'module_type': 'modB'})

        mods = (modconfA, modconfB)

        mm = self.modulemanager = ModulesManager('broker', modules_dir, mods)
        mm.load_and_init()

        modA = None
        modB = None
        for mod in mm.imported_modules:
            if mod.__package__ == 'modA':
                modA = mod
            elif mod.__package__ == 'modB':
                modB = mod

            if mod.properties['type'].startswith("mod"):
                self.assertEqual(mod.expected_helpers_X, mod.helpers.X)
        self.assertIsNotNone(modA)
        self.assertIsNotNone(modB)
        self.assertNotEqual(modA.helpers.X, modB.helpers.X)



if __name__ == '__main__':
    unittest.main()

