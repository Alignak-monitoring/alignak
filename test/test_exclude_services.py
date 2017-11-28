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
#     Christophe Simon, geektophe@gmail.com
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


from functools import partial

from alignak_test import AlignakTest


class TestExcludeServices(AlignakTest):
    """
    This class test service exclude / service include feature
    """

    def setUp(self):
        self.setup_with_file('cfg/cfg_exclude_include_services.cfg')
        self._sched = self.schedulers['scheduler-master'].sched

    def test_exclude_services(self):
        """
        Test service_excludes statement in host
        """

        hst1 = self._sched.hosts.find_by_name("test_host_01")
        hst2 = self._sched.hosts.find_by_name("test_host_02")

        assert [] == hst1.service_excludes
        assert ["srv-svc11", "srv-svc21", "proc proc1"] == hst2.service_excludes

        Find = self._sched.services.find_srv_by_name_and_hostname

        # All services should exist for test_host_01
        find = partial(Find, 'test_host_01')
        for svc in (
            'srv-svc11', 'srv-svc12',
            'srv-svc21', 'srv-svc22',
            'proc proc1', 'proc proc2',
        ):
            assert find(svc) is not None

        # Half the services only should exist for test_host_02
        find = partial(Find, 'test_host_02')
        for svc in ('srv-svc12', 'srv-svc22', 'proc proc2', ):
            assert find(svc) is not None, "%s not found" % svc

        for svc in ('srv-svc11', 'srv-svc21', 'proc proc1', ):
            assert find(svc) is None, "%s found" % svc


    def test_service_includes(self):
        """
        Test service_includes statement in host
        """ 

        Find = self._sched.services.find_srv_by_name_and_hostname
        find = partial(Find, 'test_host_03')

        for svc in ('srv-svc11', 'proc proc2', 'srv-svc22'):
            assert find(svc) is not None, "%s not found" % svc

        for svc in ('srv-svc12', 'srv-svc21', 'proc proc1'):
            assert find(svc) is None, "%s found" % svc


if __name__ == '__main__':
    AlignakTest.main()
