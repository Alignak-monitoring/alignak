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
#     Grégory Starck, g.starck@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Jean Gabes, naparuba@gmail.com
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
This file is used to test the triggers
"""

from alignak_test import *
from alignak.objects.trigger import Trigger


class TestTriggers(AlignakTest):
    """
    This class tests the triggers
    """
    def setUp(self):
        """
        For each test load and check the configuration
        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_triggers.cfg')
        self.assertTrue(self.conf_is_correct)

        self.show_configuration_logs()
        # No error messages
        self.assertEqual(len(self.configuration_errors), 0)
        # No warning messages
        self.assertGreaterEqual(len(self.configuration_warnings), 2)
        self.assert_any_cfg_log_match(
            re.escape(
                "[host::test_host_trigger] 'trigger' property is not allowed"
            )
        )
        self.assert_any_cfg_log_match(
            re.escape(
                "[service::test_service_trigger] 'trigger' property is not allowed"
            )
        )

        # Our scheduler
        self._sched = self.schedulers['scheduler-master'].sched

    def test_ignored_inner_triggers(self):
        """ Test that inner host/service configured triggers are ignored """
        self.print_header()

        # Get host and service
        host = self._sched.hosts.find_by_name("test_host_trigger")
        host.checks_in_progress = []
        host.act_depend_of = []

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_service_trigger")
        svc.checks_in_progress = []
        svc.act_depend_of = []

        # Set host output / perfdata
        host.output = 'I am OK'
        host.perf_data = 'cpu=95%'

        # Set service output / perfdata
        svc.output = 'I am OK'
        svc.perf_data = 'cpu=95%'

        # Run the service triggers
        svc.eval_triggers(self._sched.triggers)

        # Despite the service has an internal trigger, this trigger did not run!
        self.assertEqual("I am OK", svc.output)
        self.assertEqual("cpu=95%", svc.perf_data)

        # Run the host triggers
        host.eval_triggers(self._sched.triggers)
        self.scheduler_loop(2, [])

        # Despite the host has an internal trigger, this trigger did not run!
        self.assertEqual("I am OK", host.output)
        self.assertEqual("cpu=95%", host.perf_data)

    def test_function_perfdata(self):
        """ Try to catch the perf_datas of self """
        self.print_header()

        # Get host and service
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                 "sample_perf_function")
        svc.checks_in_progress = []
        svc.act_depend_of = []

        # Set service output / perfdata
        svc.output = 'I am OK'
        svc.perf_data = 'cpu=95%'

        # Run the trigger:
        # It ends executing this code:
        #   cpu = perf("test_host_0/sample_perf_function", 'cpu')
        #   print "Found cpu:", cpu, type(cpu)
        #   if cpu >= 95:
        #       critical(self, 'not good! | cpu=%d%%' % cpu)
        #   print "Service should be have CRITICAL state"
        # -----
        # After execution the service should be in a CRITICAL state and its output is changed

        svc.eval_triggers(self._sched.triggers)
        self.assertEqual(len(svc.checks_in_progress), 1)

        # Fake the scheduler_loop function (run with an host check...)
        self.scheduler_loop(1, [[host, 0, 'Fake host output']])
        self.external_command_loop()

        # Service output/perfdata are modified by the trigger
        self.assertEqual("not good!", svc.output)
        self.assertEqual("cpu=95%", svc.perf_data)

    def test_function_perfs(self):
        """ Catch the perfdata of several services """
        self.print_header()

        # Get host and service
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "AVG-HTTP")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # ignore the router
        svc.event_handler_enabled = False

        # Four services have the same metric in their perfdata
        for i in xrange(1, 4):
            s = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "HTTP-" + str(i))
            s.output = 'Http ok'
            s.perf_data = 'time=%dms' % i

        # Run the trigger
        svc.eval_triggers(self._sched.triggers)

        self.scheduler_loop(4, [[host, 0, 'Fake host output']])
        print "Output", svc.output
        print "Perf_Data", svc.perf_data

        # Service output/perfdata are modified by the trigger
        # Note the avg_time metric that is an average of the 4 other services time metric
        self.assertEqual("OK all is green", svc.output)
        self.assertEqual("avg_time=2ms", svc.perf_data)

    def test_function_custom(self):
        """ Try to catch the custom variables """
        self.print_header()

        # Get host and service
        host = self._sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0",
                                                                 "sample_custom_function")
        svc.checks_in_progress = []
        svc.act_depend_of = []

        # Set service output / perfdata
        svc.output = 'Nb users?'
        svc.perf_data = 'users=6'

        # Run the trigger
        svc.eval_triggers(self._sched.triggers)

        self.scheduler_loop(4, [[host, 0, 'Fake host output']])
        print "Output", svc.output
        print "Perf_Data", svc.perf_data
        self.assertEqual("OK all is green, my host is gnulinux", svc.output)
        self.assertEqual("users=12", svc.perf_data)

    def test_trig_file_loading(self):
        """ Test trigger files (*.trig) loading """
        # Get host and service
        host = self._sched.hosts.find_by_name("test_host_trigger2")
        host.checks_in_progress = []
        host.act_depend_of = []

        t = self.arbiter.conf.triggers.find_by_name('simple_cpu')
        self.assertIn(t.uuid, host.triggers)

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "cpu_too_high_ter")
        svc.checks_in_progress = []
        svc.act_depend_of = []

        t = self.arbiter.conf.triggers.find_by_name('simple_cpu')
        self.assertIn(t.uuid, svc.triggers)

        # Set service output / perfdata
        svc.output = 'I am OK'
        svc.perf_data = 'cpu=95%'

        # Run the service triggers
        svc.eval_triggers(self._sched.triggers)

        self.scheduler_loop(2, [])
        self.external_command_loop()

        self.assertEqual("not good!", svc.output)
        self.assertEqual("cpu=95", svc.perf_data)

        # Set service output / perfdata
        svc.output = 'I am OK'
        svc.perf_data = 'cpu=80%'

        # Run the service triggers
        svc.eval_triggers(self._sched.triggers)

        self.scheduler_loop(2, [])
        self.external_command_loop()

        self.assertEqual("not that bad!", svc.output)
        self.assertEqual("cpu=80", svc.perf_data)

        # Set service output / perfdata
        svc.output = 'I am OK'
        svc.perf_data = 'cpu=60%'

        # Run the service triggers
        svc.eval_triggers(self._sched.triggers)

        self.scheduler_loop(2, [])
        self.external_command_loop()

        self.assertEqual("Ok!", svc.output)
        self.assertEqual("cpu=60", svc.perf_data)

        # Set host output / perfdata
        host.output = 'I am OK'
        host.perf_data = 'cpu=95%'

        # Run the host triggers
        host.eval_triggers(self._sched.triggers)

        self.scheduler_loop(2, [])
        self.external_command_loop()

        self.assertEqual("not good!", host.output)
        self.assertEqual("cpu=95", host.perf_data)

        # Set host output / perfdata
        host.output = 'I am OK'
        host.perf_data = 'cpu=80%'

        # Run the host triggers
        host.eval_triggers(self._sched.triggers)

        self.scheduler_loop(2, [])
        self.external_command_loop()

        self.assertEqual("not that bad!", host.output)
        self.assertEqual("cpu=80", host.perf_data)

        # Set host output / perfdata
        host.output = 'I am OK'
        host.perf_data = 'cpu=70%'

        # Run the host triggers
        host.eval_triggers(self._sched.triggers)

        self.scheduler_loop(2, [])
        self.external_command_loop()

        self.assertEqual("Ok!", host.output)
        self.assertEqual("cpu=70", host.perf_data)

    def test_simple_triggers(self):
        """ Test the simple triggers """
        self.print_header()

        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        code = '''r = self.get_name()'''.replace(r'\n', '\n').replace(r'\t', '\t')
        t = Trigger({'trigger_name': 'none', 'code_src': code})
        t.compile()
        r = t.eval(svc)

        code = '''self.output = "New check output" '''.replace(r'\n', '\n').replace(r'\t', '\t')
        t = Trigger({'trigger_name': 'none', 'code_src': code})
        t.compile()
        r = t.eval(svc)
        self.assertEqual("New check output", svc.output)

        code = '''self.output = "New check output"
self.perf_data = "New check performance data"
'''.replace(r'\n', '\n').replace(r'\t', '\t')
        t = Trigger({'trigger_name': 'none', 'code_src': code})
        t.compile()
        r = t.eval(svc)
        self.assertEqual("New check output", svc.output)
        self.assertEqual("New check performance data", svc.perf_data)



if __name__ == '__main__':
    AlignakTest.main()
