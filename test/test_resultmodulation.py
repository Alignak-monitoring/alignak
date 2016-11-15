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
#     Zoran Zaric, zz@zoranzaric.de
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
This file is used to test result modulations
"""

from alignak_test import AlignakTest, unittest


class TestResultModulation(AlignakTest):
    def setUp(self):
        self.setup_with_file('cfg/cfg_result_modulation.cfg')
        assert self.conf_is_correct

        # Our scheduler
        self._sched = self.schedulers['scheduler-master'].sched

    def test_service_resultmodulation(self):
        """ Test result modulations """
        self.print_header()

        # Get the host
        host = self._sched.hosts.find_by_name("test_host_0")
        assert host is not None
        host.checks_in_progress = []
        host.act_depend_of = []
        assert len(host.resultmodulations) == 0

        # Get the host modulated service
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                 "test_ok_0_resmod")
        assert svc is not None
        svc.checks_in_progress = []
        svc.act_depend_of = []
        assert len(svc.resultmodulations) == 1

        # Get the result modulations
        mod = self._sched.resultmodulations.find_by_name("critical_is_warning")
        assert mod is not None
        assert mod.get_name() == "critical_is_warning"
        assert mod.is_active(self._sched.timeperiods)
        assert mod.uuid in svc.resultmodulations

        # The host is UP
        # The service is going CRITICAL/HARD ...
        self.scheduler_loop(3, [
            [host, 0, 'UP'],
            [svc, 2, 'BAD | value1=0 value2=0']
        ])
        # The service has a result modulation. So CRITICAL is transformed as WARNING.
        self.assertEqual('WARNING', svc.state)
        self.assertEqual('HARD', svc.state_type)

        # Even after a second run
        self.scheduler_loop(3, [
            [host, 0, 'UP'],
            [svc, 2, 'BAD | value1=0 value2=0']
        ])
        # The service has a result modulation. So CRITICAL is transformed as WARNING.
        self.assertEqual('WARNING', svc.state)
        self.assertEqual('HARD', svc.state_type)

        # Without the resultmodulations, we should have the usual behavior
        svc.resultmodulations = []
        self.scheduler_loop(3, [
            [host, 0, 'UP'],
            [svc, 2, 'BAD | value1=0 value2=0']
        ])
        self.assertEqual('CRITICAL', svc.state)
        self.assertEqual('HARD', svc.state_type)

    def test_inherited_modulation(self):
        """ Test inherited host/service result modulations
         Resultmodulation is a implicit inherited parameter and router defines it,
         but not test_router_0_resmod/test_ok_0_resmod.

         Despite this service should also be impacted
        """
        self.print_header()

        # Get the router
        router = self._sched.hosts.find_by_name("test_router_0_resmod")
        router.checks_in_progress = []
        router.act_depend_of = []
        assert router is not None
        assert len(router.resultmodulations) == 1

        # Get the service
        svc2 = self._sched.services.find_srv_by_name_and_hostname("test_router_0_resmod",
                                                                  "test_ok_0_resmod")
        assert svc2 is not None
        svc2.checks_in_progress = []
        svc2.act_depend_of = []
        assert len(svc2.resultmodulations) == 1
        assert router.resultmodulations == svc2.resultmodulations

        # Get the result modulations
        mod = self._sched.resultmodulations.find_by_name("critical_is_warning")
        assert mod is not None
        assert mod.get_name() == "critical_is_warning"
        assert mod.is_active(self._sched.timeperiods)
        assert mod.uuid in svc2.resultmodulations

        # The router is UP
        # The service is going CRITICAL/HARD ...
        self.scheduler_loop(3, [
            [router, 0, 'UP'],
            [svc2, 2, 'BAD | value1=0 value2=0']
        ])
        # The service has a result modulation. So CRITICAL is transformed as WARNING.
        self.assertEqual('WARNING', svc2.state)
        self.assertEqual('HARD', svc2.state_type)


if __name__ == '__main__':
    unittest.main()
