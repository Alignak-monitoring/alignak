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
#     aviau, alexandre.viau@savoirfairelinux.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Gerhard Lausser, gerhard.lausser@consol.de

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
 This file is used to test actions
"""

import os
import sys
import time

from alignak_test import AlignakTest, unittest, time_hacker
from alignak.action import Action


class TestAction(AlignakTest):
    def setUp(self):
        # Create and test an action object
        a = Action()
        assert a.env == {}
        assert a.timeout == 10
        assert a.exit_status == 3

        time_hacker.set_real_time()

    def wait_finished(self, a, size=8012):
        start = time.time()
        while True:
            # Do the job
            if a.status == 'launched':
                a.check_finished(size)
                time.sleep(0.01)
            if a.status != 'launched':
                return
            # 20s timeout
            if time.time() - start > 20:
                print "Timeout: 20s!"
                return

    def test_action(self):
        """ Test simple action execution

        :return: None
        """
        self.print_header()

        a = Action()

        if os.name == 'nt':
            a.command = r'libexec\\dummy_command.cmd'
        else:
            a.command = "libexec/dummy_command.sh"

        assert a.got_shell_characters() == False

        # Run the action script
        a.execute()
        assert 'launched' == a.status

        # Wait action execution end
        self.wait_finished(a)
        assert 0 == a.exit_status
        assert 'done' == a.status
        assert "Hi, I'm for testing only. Please do not use me directly, really" == a.output
        assert "" == a.long_output
        assert "Hip=99% Bob=34mm" == a.perf_data

    def test_echo_environment_variables(self):
        """ Test echo environment variables

        :return: None
        """
        self.print_header()

        a = Action()
        a.command = "echo $ALIGNAK_TEST_VARIABLE"

        assert 'ALIGNAK_TEST_VARIABLE' not in a.get_local_environnement()
        a.env = {'ALIGNAK_TEST_VARIABLE': 'is now existing and defined'}
        assert 'ALIGNAK_TEST_VARIABLE' in a.get_local_environnement()
        assert a.get_local_environnement()['ALIGNAK_TEST_VARIABLE'] == 'is now existing and defined'

        # Execute action
        a.execute()
        self.wait_finished(a)
        assert a.output == 'is now existing and defined'

    def test_grep_for_environment_variables(self):
        """ Test grep for environment variables

        :return: None
        """
        self.print_header()

        a = Action()
        a.command = "/usr/bin/env | grep ALIGNAK_TEST_VARIABLE"

        assert 'ALIGNAK_TEST_VARIABLE' not in a.get_local_environnement()
        a.env = {'ALIGNAK_TEST_VARIABLE': 'is now existing and defined'}
        assert 'ALIGNAK_TEST_VARIABLE' in a.get_local_environnement()
        assert a.get_local_environnement()['ALIGNAK_TEST_VARIABLE'] == 'is now existing and defined'

        # Execute action
        a.execute()
        self.wait_finished(a)
        assert a.output == 'ALIGNAK_TEST_VARIABLE=is now existing and defined'

    def test_environment_variables(self):
        """ Test environment variables

        :return: None
        """
        self.print_header()

        class ActionWithoutPerfData(Action):
            def get_outputs(self, out, max_len):
                """ For testing only... 
                Do not cut the outputs into perf_data to avoid problems with enviroment 
                containing a dash like in `LESSOPEN=|/usr/bin/lesspipe.sh %s`
                """
                self.output = out

        a = ActionWithoutPerfData()
        a.command = "/usr/bin/env"

        assert 'ALIGNAK_TEST_VARIABLE' not in a.get_local_environnement()
        a.env = {'ALIGNAK_TEST_VARIABLE': 'is now existing and defined'}
        assert False == a.got_shell_characters()
        assert 'ALIGNAK_TEST_VARIABLE' in a.get_local_environnement()
        assert a.get_local_environnement()['ALIGNAK_TEST_VARIABLE'] == 'is now existing and defined'

        # Run the action script
        a.execute()
        assert 'launched' == a.status

        # Wait action execution end and set the max output we want for the command
        self.wait_finished(a, size=20*1024)
        
        searched_env_found = False
        for line in a.output.splitlines():
            if line == 'ALIGNAK_TEST_VARIABLE=is now existing and defined':
                searched_env_found = True
        assert searched_env_found

    def test_noshell_bang_command(self):
        """ Test no shebang in the command script

        Some commands are shell without bangs! (like in Centreon...)
        We can detect it in the launch, and it should be managed

        :return: None
        """
        self.print_header()

        a = Action()
        a.command = "libexec/dummy_command_nobang.sh"
        assert False == a.got_shell_characters()
        a.execute()

        # Run the action script
        a.execute()
        assert 'launched' == a.status

        # Wait action execution end
        self.wait_finished(a)
        assert 0 == a.exit_status
        assert 'done' == a.status
        assert "Hi, I'm for testing only. Please do not use me directly, really" == a.output
        assert "" == a.long_output
        assert "Hip=99% Bob=34mm" == a.perf_data

    def test_got_shell_characters(self):
        """ Test shell characters in the command (&>...)

        :return: None
        """
        self.print_header()

        a = Action()
        a.command = "libexec/dummy_command_nobang.sh && echo finished ok"

        assert True == a.got_shell_characters()

        # Run the action script
        a.execute()
        assert 'launched' == a.status

        # Wait action execution end
        self.wait_finished(a)
        assert 0 == a.exit_status
        assert 'done' == a.status
        assert "Hi, I'm for testing only. Please do not use me directly, really" == a.output
        assert "finished ok\n" == a.long_output
        assert "Hip=99% Bob=34mm" == a.perf_data

    def test_got_pipe_shell_characters(self):
        """ Test pipe shell character in the command

        :return: None
        """
        self.print_header()

        a = Action()
        a.command = "libexec/dummy_command_nobang.sh | grep 'I will not match this search!'"
        assert True == a.got_shell_characters()

        # Run the action script
        a.execute()
        assert 'launched' == a.status

        # Wait action execution end
        self.wait_finished(a)
        assert 1 == a.exit_status
        assert 'done' == a.status
        assert "" == a.output
        assert "" == a.long_output
        assert "" == a.perf_data

    def test_got_unclosed_quote(self):
        """ Test unclosed quote in the command

        :return: None
        """
        self.print_header()

        # https://github.com/naparuba/shinken/issues/155
        a = Action()
        a.command = "libexec/dummy_command_nobang.sh -a 'wwwwzzzzeeee"


        # Run the action script
        a.execute()
        if sys.version_info < (2, 7):
            # cygwin: /bin/sh: -c: line 0: unexpected EOF while looking for matching'
            # ubuntu: /bin/sh: Syntax error: Unterminated quoted string
            print("Status: %s" % a.status)
            print("Output: %s" % a.output)
            print("Exit code: %s" % a.exit_status)

            # Do not wait for end because it did not really started ...
            # Todo: Python 2.6 different behavior ... but it will be deprecated soon,
            # so do not care with this now
            assert 'launched' == a.status
            assert "" == a.output
            assert 3 == a.exit_status
        else:
            # Do not wait for end because it did not really started ...
            assert 'done' == a.status
            assert 'Not a valid shell command: No closing quotation' == a.output
            assert 3 == a.exit_status

    # We got problems on LARGE output, more than 64K in fact.
    # We try to solve it with the fcntl and non blocking read
    # instead of "communicate" mode. So here we try to get a 100K
    # output. Should NOT be in a timeout
    def test_huge_output(self):
        """ Test huge output

        :return: None
        """
        self.print_header()

        # Set max output length
        max_output_length = 131072

        a = Action()
        a.timeout = 5

        if os.name == 'nt':
            a.command = r"""python -c 'print "A"*%d'""" % max_output_length
            # Todo: As of now, it fails on Windows:(
            return
        else:
            a.command = r"""python -u -c 'print "."*%d'""" % max_output_length

        ###
        ### 1 - output is less than the max output
        ###
        # Run the action script
        a.execute()
        assert 'launched' == a.status

        # Wait action execution end and set the max output we want for the command
        self.wait_finished(a, size=max_output_length + 1)
        assert 0 == a.exit_status
        assert 'done' == a.status
        assert "."*max_output_length == a.output
        assert "" == a.long_output
        assert "" == a.perf_data

        ###
        ### 2 - output is equal to the max output
        ###
        # Run the action script
        a.execute()
        assert 'launched' == a.status

        # Wait action execution end and set the max output we want for the command
        self.wait_finished(a, size=max_output_length)
        assert 0 == a.exit_status
        assert 'done' == a.status
        assert "."*max_output_length == a.output
        assert "" == a.long_output
        assert "" == a.perf_data

        ###
        ### 3 - output is more than the max output
        ###
        # Run the action script
        a.execute()
        assert 'launched' == a.status

        # Wait action execution end and set the max output we want for the command
        self.wait_finished(a, size=max_output_length - 10)
        assert 0 == a.exit_status
        assert 'done' == a.status
        assert "."*(max_output_length - 10) == a.output
        assert "" == a.long_output
        assert "" == a.perf_data

    def test_execve_fail_with_utf8(self):
        """ Test execve fail with utf8

        :return: None
        """
        self.print_header()

        a = Action()
        a.command = u"/bin/echo Wiadomo\u015b\u0107"

        # Run the action script
        a.execute()
        assert 'launched' == a.status

        # Wait action execution end and set the max output we want for the command
        self.wait_finished(a)
        assert 0 == a.exit_status
        assert 'done' == a.status
        assert u"Wiadomo\u015b\u0107" == a.output
        assert "" == a.long_output
        assert "" == a.perf_data

    def test_non_zero_exit_status_empty_output_but_non_empty_stderr(self):
        """ Test catch stdout and stderr

        :return: None
        """
        self.print_header()

        a = Action()
        a.command = "echo Output to stderr >&2 ; exit 1"

        # Run the action script
        a.execute()
        assert 'launched' == a.status

        # Wait action execution end and set the max output we want for the command
        self.wait_finished(a)
        assert 1 == a.exit_status
        assert 'done' == a.status
        assert "Output to stderr" == a.output
        assert "" == a.long_output
        assert "" == a.perf_data


if __name__ == '__main__':
    unittest.main()
