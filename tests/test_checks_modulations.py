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
#     Jean Gabes, naparuba@gmail.com
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

"""
 This file is used to test checks modulations
"""

import time
from .alignak_test import AlignakTest


class TestCheckModulations(AlignakTest):

    def setUp(self):
        super(TestCheckModulations, self).setUp()
        self.setup_with_file('./cfg/cfg_checks_modulations.cfg')
        assert self.conf_is_correct

    def test_checks_modulated_host_and_service(self):
        """ Check modulation for an host and its service """
        # Get the host
        host = self._scheduler.hosts.find_by_name("modulated_host")
        assert host is not None
        assert host.check_command is not None

        # Get the check modulation
        mod = self._scheduler.checkmodulations.find_by_name("MODULATION")
        assert mod is not None
        assert mod.get_name() == "MODULATION"
        # Modulation is known by the host
        assert mod.uuid in host.checkmodulations
        # Modulation check command is not the same as the host one
        assert mod.get_check_command(self._scheduler.timeperiods, time.time()) is not host.check_command

        # Get the host service
        svc = self._scheduler.services.find_srv_by_name_and_hostname("modulated_host",
                                                                 "modulated_service")

        # Service is going CRITICAL/HARD ... this forces an host check!
        self.scheduler_loop(1, [[svc, 2, 'BAD']])
        assert len(host.checks_in_progress) == 1
        for c in host.checks_in_progress:
            assert 'plugins/nothing VALUE' == self._scheduler.checks[c].command

        assert len(svc.checks_in_progress) == 1
        for c in svc.checks_in_progress:
            assert 'plugins/nothing VALUE' == self._scheduler.checks[c].command
