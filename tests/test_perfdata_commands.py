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
 This file is used to test acknowledge of problems
"""

import time

from alignak.objects import SchedulingItem
from alignak.commandcall import CommandCall

from .alignak_test import AlignakTest


class TestPerfdataCommands(AlignakTest):
    """
    This class tests the perfomance data commands that can be attached to hosts or services
    """
    def setUp(self):
        super(TestPerfdataCommands, self).setUp()
        self.setup_with_file('cfg/cfg_perfdata_commands.cfg')
        assert self.conf_is_correct

    def test_service_perfdata_command(self):
        """
        Test the service performance data command
        :return:
        """
        self._sched = self._scheduler

        # We want an event handler (the perfdata command) to be put in the actions dict
        # after we got a service check
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        #--------------------------------------------------------------
        # initialize host/service state
        #--------------------------------------------------------------
        # Check we have a real command, not only a string
        assert isinstance(svc.__class__.perfdata_command, CommandCall)

        # Get a service check with perfdata
        self.scheduler_loop(1, [[svc, 0, 'OK | percent=99%']])

        # The event handler is raised to be launched
        self.assert_actions_count(1)
        self.assert_actions_match(0, '/submit_service_result', 'command')
        self.show_and_clear_actions()

        # Now, disable the perfdata management
        cmd = "[%lu] DISABLE_PERFORMANCE_DATA" % int(time.time())
        self._sched.run_external_commands([cmd])

        # Get a service check with perfdata
        self.scheduler_loop(1, [[svc, 0, 'OK | percent=99%']])

        # No actions
        self.assert_actions_count(0)

    def test_host_perfdata_command(self):
        """
        Test the service performance data command
        :return:
        """
        self._sched = self._scheduler

        # We want an event handler (the perfdata command) to be put in the actions dict
        # after we got a service check
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        #--------------------------------------------------------------
        # initialize host/service state
        #--------------------------------------------------------------
        # Check we have a real command, not only a string
        assert isinstance(host.perfdata_command, CommandCall)

        # Get a host check with perfdata
        self.scheduler_loop(1, [[host, 0, 'UP | percent=99%']])

        # The event handler is raised to be launched
        self.assert_actions_count(1)
        self.assert_actions_match(0, '/submit_host_result', 'command')
        self.show_and_clear_actions()

        # Now, disable the perfdata management
        cmd = "[%lu] DISABLE_PERFORMANCE_DATA" % int(time.time())
        self._sched.run_external_commands([cmd])

        # Get a host check with perfdata
        self.scheduler_loop(1, [[host, 0, 'UP | percent=99%']])

        # No actions
        self.assert_actions_count(0)

    def test_multiline_perfdata(self):
        """
        Test with performance data on several lignes
        :return:
        """
        self._sched = self._scheduler

        # We want an event handler (the perfdata command) to be put in the actions dict
        # after we got a service check
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        #--------------------------------------------------------------
        # initialize host/service state
        #--------------------------------------------------------------
        # Check we have a real command, not only a string
        assert isinstance(svc.perfdata_command, CommandCall)

        # Get a service check with perfdata
        output = """  DISK OK - free space: / 3326 MB (56%);    |   /=2643MB;5948;5958;0;5968
/ 15272 MB (77%);
/boot 68 MB (69%);
/home 69357 MB (27%);
/var/log 819 MB (84%);    | /boot=68MB;88;93;0;98
/home=69357MB;253404;253409;0;253414
/var/log=818MB;970;975;0;980
        """
        # Simulate a check executino
        self.fake_check(svc, 0, output)
        # Consume simulated check
        self.scheduler_loop(1, [])

        assert isinstance(svc, SchedulingItem)
        print("Actions", self._sched.actions)
        print('Output', svc.output)
        print('Long output', svc.long_output)
        print('Performance data', svc.perf_data)

        # Note that the check output is stripped
        assert svc.output == 'DISK OK - free space: / 3326 MB (56%);'
        # The check long output is also stripped
        assert svc.long_output == '/ 15272 MB (77%);\n' \
                                          '/boot 68 MB (69%);\n' \
                                          '/home 69357 MB (27%);\n' \
                                          '/var/log 819 MB (84%);'
        # And the performance data are also stripped
        assert svc.perf_data == '/=2643MB;5948;5958;0;5968 ' \
                                        '/boot=68MB;88;93;0;98 ' \
                                        '/home=69357MB;253404;253409;0;253414 ' \
                                        '/var/log=818MB;970;975;0;980'

        # The event handler is raised to be launched
        self.assert_actions_count(1)
        self.assert_actions_match(0, '/submit_service_result', 'command')
        self.show_and_clear_actions()
