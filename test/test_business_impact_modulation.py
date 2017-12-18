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


class TestBusinessImpactModulation(AlignakTest):

    def setUp(self):
        super(TestBusinessImpactModulation, self).setUp()
        self.setup_with_file('cfg/cfg_businesssimpact_modulation.cfg')
        assert self.conf_is_correct

        # Our scheduler
        self._sched = self._scheduler

    def test_business_impact_modulation(self):
        """ Tests business impact modulation """
        # Get our criticity (BI) modulation
        cm = self._sched.businessimpactmodulations.find_by_name('CritMod')
        assert cm is not None
        assert cm.get_name() == "CritMod"
        assert cm.business_impact == 5

        # Get our service
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_00")
        assert cm.uuid in svc.business_impact_modulations
        # Service BI is defined as 2 but the BI modulation makes it be 5!
        assert svc.business_impact == 5


if __name__ == '__main__':
    AlignakTest.main()
