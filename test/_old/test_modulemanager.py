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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     aviau, alexandre.viau@savoirfairelinux.com
#     Grégory Starck, g.starck@gmail.com
#     Alexander Springer, alex.spri@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de

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
import sys

from alignak_test import (
    AlignakTest, time_hacker, unittest
)

from alignak.modulesmanager import ModulesManager
from alignak.objects.module import Module


class TestModuleManager(AlignakTest):

    def setUp(self):
        self.setup_with_file([])
        time_hacker.set_real_time()

    # Try to see if the module manager can manage modules
    def test_modulemanager(self):
        mod = Module({'module_alias': 'mod-example', 'python_name': 'alignak_module_example'})
        self.modulemanager = ModulesManager('broker', None)
        self.modulemanager.load_and_init([mod])
        # And start external ones, like our LiveStatus
        self.modulemanager.start_external_instances()
        print "I correctly loaded the modules: %s " % ([inst.get_name() for inst in self.modulemanager.instances])

        print "*** First kill ****"
        # Now I will try to kill the livestatus module
        ls = self.modulemanager.instances[0]
        " :type: alignak.basemodule.BaseModule "
        ls.kill()
        time.sleep(0.1)
        print "Check alive?"
        print "Is alive?", ls.process.is_alive()
        # Should be dead
        self.assertFalse(ls.process.is_alive())
        self.modulemanager.check_alive_instances()
        self.modulemanager.try_to_restart_deads()

        # In fact it's too early, so it won't do it

        # Here the inst should still be dead
        print "Is alive?", ls.process.is_alive()
        self.assertFalse(ls.process.is_alive())

        # So we lie
        ls.last_init_try = -5
        self.modulemanager.check_alive_instances()
        self.modulemanager.try_to_restart_deads()

        # In fact it's too early, so it won't do it

        # Here the inst should be alive again
        print "Is alive?", ls.process.is_alive()
        self.assertTrue(ls.process.is_alive())

        # should be nothing more in to_restart of
        # the module manager
        self.assertEqual([], self.modulemanager.to_restart)

        # Now we look for time restart so we kill it again
        ls.kill()
        time.sleep(0.2)
        self.assertFalse(ls.process.is_alive())

        # Should be too early
        self.modulemanager.check_alive_instances()
        self.modulemanager.try_to_restart_deads()
        print "Is alive or not", ls.process.is_alive()
        self.assertFalse(ls.process.is_alive())
        # We lie for the test again
        ls.last_init_try = -5
        self.modulemanager.check_alive_instances()
        self.modulemanager.try_to_restart_deads()

        # Here the inst should be alive again
        print "Is alive?", ls.process.is_alive()
        self.assertTrue(ls.process.is_alive())

        # And we clear all now
        print "Ask to die"
        self.modulemanager.stop_all()
        print "Died"


if __name__ == '__main__':
    unittest.main()
