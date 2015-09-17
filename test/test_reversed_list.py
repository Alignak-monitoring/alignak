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

from alignak_test import AlignakTest, unittest
from alignak.misc.regenerator import Regenerator
from alignak.brok import Brok


class TestReversedList(AlignakTest):
    def setUp(self):
        self.setup_with_file(["etc/alignak_service_withhost_exclude.cfg"])

    def test_reversed_list(self):
        """ Test to ensure new conf is properly merge with different servicegroup definition
        The first conf has all its servicegroup defined servicegroups.cfg and services.cfg
        The second conf has both, so that servicegroups defined ins services.cfg are genretaed by Alignak
        This lead to another generated id witch should be handled properly when regenerating reversed list / merging
        servicegroups definition
        """

        sg = self.sched.servicegroups.find_by_name('servicegroup_01')
        prev_id = sg._id

        reg = Regenerator()
        data = {"instance_id": 0}
        b = Brok('program_status', data)
        b.prepare()
        reg.manage_program_status_brok(b)
        reg.all_done_linking(0)


        self.setup_with_file(["etc/alignak_reversed_list.cfg"])

        reg.all_done_linking(0)

        #for service in self.sched.servicegroups:
        #    assert(service.servicegroup_name in self.sched.servicegroups.reversed_list.keys())
        #    assert(service._id == self.sched.servicegroups.reversed_list[service.servicegroup_name])

        sg = self.sched.servicegroups.find_by_name('servicegroup_01')
        assert(prev_id != sg._id)

        for sname in [u'servicegroup_01', u'ok', u'flap', u'unknown', u'random',
                      u'servicegroup_02', u'servicegroup_03', u'warning', u'critical',
                      u'servicegroup_04', u'servicegroup_05', u'pending', u'mynewgroup']:
            sg = self.sched.servicegroups.find_by_name(sname)
            assert(sname is not None)



if __name__ == '__main__':
    unittest.main()
