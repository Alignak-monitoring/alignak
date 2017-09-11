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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Gerhard Lausser, gerhard.lausser@consol.de

"""
 This file is used to test hosts maintenance_period that will produce a downtime.
"""

import time
from datetime import datetime, timedelta
from alignak.misc.serialization import unserialize
from alignak.downtime import Downtime
from alignak.objects.timeperiod import Timeperiod

from alignak_test import AlignakTest, unittest

class TestMaintenancePeriod(AlignakTest):
    """
    This class tests the maintenance_period
    """
    def setUp(self):
        """
        For each test load and check the configuration
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')
        assert self.conf_is_correct

        # Our scheduler
        self._sched = self.schedulers['scheduler-master'].sched

        # Our broker
        self._broker = self._sched.brokers['broker-master']

        # No error messages
        assert len(self.configuration_errors) == 0
        # No warning messages
        assert len(self.configuration_warnings) == 0

    def test_maintenance_period_host(self):
        """Test a host enter in maintenance_period
        
        :return: None
        """
        self.print_header()
        # Get the host
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []
        # Not any downtime yet !
        assert host.downtimes == {}

        # Make the host be UP
        self.scheduler_loop(1, [[host, 0, 'UP']])

        # we created a new timeperiod from now -5 minutes to now + 55 minutes
        begin = datetime.now() - timedelta(minutes=5)
        end = datetime.now() + timedelta(minutes=55)

        h_begin = format(begin, '%H:%M')
        if format(begin, '%H') == '23' and format(begin, '%M') >= 55:
            h_begin = '00:00'
        h_end = format(end, '%H:%M')
        end = end - timedelta(seconds=int(format(end, '%S')))
        timestamp_end = int(time.mktime(end.timetuple()))

        data = {
            'timeperiod_name': 'maintenance',
            'sunday': h_begin + '-' + h_end,
            'monday': h_begin + '-' + h_end,
            'tuesday': h_begin + '-' + h_end,
            'wednesday': h_begin + '-' + h_end,
            'thursday': h_begin + '-' + h_end,
            'friday': h_begin + '-' + h_end,
            'saturday': h_begin + '-' + h_end
        }
        timeperiod = Timeperiod(data)
        timeperiod.explode()
        self.schedulers['scheduler-master'].sched.timeperiods[timeperiod.uuid] = timeperiod
        host.maintenance_period = timeperiod.uuid

        # Make the host be UP again
        self.scheduler_loop(1, [[host, 0, 'UP']])

        assert 1 == len(host.downtimes)
        # The host is still in a downtime period
        assert host.in_scheduled_downtime
        downtime = host.downtimes.values()[0]
        assert downtime.fixed
        assert downtime.is_in_effect
        assert not downtime.can_be_deleted
        assert downtime.end_time == timestamp_end
        assert downtime.comment == 'This downtime was automatically scheduled by Alignak because ' \
                                   'of a maintenance period.'

if __name__ == '__main__':
    unittest.main()
