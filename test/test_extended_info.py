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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Nicolas Dupeux, nicolas@dupeux.net
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
This file is used to test the host/service extended information
"""
from alignak_test import AlignakTest


class TestHostExtended(AlignakTest):

    def setUp(self):
        super(TestHostExtended, self).setUp()

        self.setup_with_file('cfg/extended/extended_info.cfg')
        assert self.conf_is_correct
        self._sched = self._scheduler

    def test_extended_host_information(self):
        """ Host extended information """
        # Get hosts and services
        host = self._sched.hosts.find_by_name("host_A")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        self.scheduler_loop(2, [
            [host, 0, 'UP | value1=1 value2=2']
        ])
        assert 'UP' == host.state
        assert 'HARD' == host.state_type

        assert 'host.png' == host.icon_image
        assert 'Alt for icon.png' == host.icon_image_alt
        assert 'Notes' == host.notes
        # This parameter is already defined in the host, thus it is not overloaded by the one
        # in the hostextinfo definition
        assert '/alignak/wiki/doku.php/$HOSTNAME$' == host.notes_url
        assert 'vrml.png' == host.vrml_image
        assert 'map.png' == host.statusmap_image
        # Not implemented, see #574
        # self.assertEqual('1', host['2d_coords'])
        # self.assertEqual('2', host['3d_coords'])

    def test_extended_service_information(self):
        """ Service extended information """
        # Get hosts and services
        host = self._sched.hosts.find_by_name("host_A")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._sched.services.find_srv_by_name_and_hostname("host_A", "svc_A")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(2, [
            [svc, 0, 'OK']
        ])
        assert 'OK' == svc.state
        assert 'HARD' == svc.state_type

        assert 'service.png' == svc.icon_image
        assert 'Alt for service.png' == svc.icon_image_alt
        assert 'Notes for a service' == svc.notes
        assert 'http://Notes_url/service' == svc.notes_url
