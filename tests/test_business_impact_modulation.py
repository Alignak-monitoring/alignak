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

from .alignak_test import *


class TestBusinessImpactModulation(AlignakTest):

    def setUp(self):
        super(TestBusinessImpactModulation, self).setUp()
        self.setup_with_file('cfg/cfg_businesssimpact_modulation.cfg',
                             dispatching=True)
        assert self.conf_is_correct

    def test_business_impact_modulation(self):
        """ Tests business impact modulation """
        # Get our scheduler BI modulations
        bi_modulation = self._scheduler.businessimpactmodulations.find_by_name('CritMod')
        assert bi_modulation is not None
        assert bi_modulation.get_name() == "CritMod"
        assert bi_modulation.business_impact == 5

        # Get our service
        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_00")
        assert bi_modulation.uuid in svc.business_impact_modulations
        # Service BI is defined as 2
        assert svc.business_impact == 2

        # Default scheduler loop updates the BI every 60 loop turns
        # Update business impact on each scheduler tick
        self._scheduler.update_recurrent_works_tick({'tick_update_business_values': 1})
        self.scheduler_loop(2, [])
        # Service BI is defined as 2 but the BI modulation makes it be 5!
        assert svc.business_impact == 5
