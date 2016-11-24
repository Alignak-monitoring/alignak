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
#     Guillaume Bour, guillaume@bour.cc
#     Frédéric Vachon, fredvac@gmail.com
#     Frédéric MOHIER, frederic.mohier@ipmfrance.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Zoran Zaric, zz@zoranzaric.de
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     aurelien, aurelien.baudet@swid.fr
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

"""This module provides a system-independent Action class. Action class is used
for handling check and notification execution (handle output, execute process, kill process..)

"""
import logging
import os
import time
import shlex
import sys
import subprocess
import signal

# Try to read in non-blocking mode, from now this only from now on
# Unix systems
try:
    import fcntl  # pylint: disable=C0103
except ImportError:
    fcntl = None  # pylint: disable=C0103

from alignak.property import BoolProp, IntegerProp, FloatProp
from alignak.property import StringProp, DictProp
from alignak.alignakobject import AlignakObject

logger = logging.getLogger(__name__)  # pylint: disable=C0103

__all__ = ('Action', )

VALID_EXIT_STATUS = (0, 1, 2, 3)

ONLY_COPY_PROP = ('uuid', 'status', 'command', 't_to_go', 'timeout',
                  'env', 'module_type', 'execution_time', 'u_time', 's_time')

SHELLCHARS = ('!', '$', '^', '&', '*', '(', ')', '~', '[', ']',
                   '|', '{', '}', ';', '<', '>', '?', '`')


def no_block_read(output):
    """Try to read a file descriptor in a non blocking mode

    :param output: file or socket to read from
    :type output: file
    :return: data read from fd
    :rtype: str
    """
    o_fd = output.fileno()
    o_fl = fcntl.fcntl(o_fd, fcntl.F_GETFL)
    fcntl.fcntl(o_fd, fcntl.F_SETFL, o_fl | os.O_NONBLOCK)
    try:
        return output.read()
    except Exception:  # pylint: disable=W0703
        return ''


class ActionBase(AlignakObject):
    """
    This abstract class is used just for having a common id for both
    actions and checks.
    """
    process = None

    properties = {
        'is_a':
            StringProp(default=''),
        'type':
            StringProp(default=''),
        'creation_time':
            FloatProp(default=0.0),
        '_in_timeout':
            BoolProp(default=False),
        'status':
            StringProp(default='scheduled'),
        'exit_status':
            IntegerProp(default=3),
        'output':
            StringProp(default='', fill_brok=['full_status']),
        't_to_go':
            FloatProp(default=0.0),
        'check_time':
            IntegerProp(default=0),
        'execution_time':
            FloatProp(default=0.0),
        'u_time':
            FloatProp(default=0.0),
        's_time':
            FloatProp(default=0.0),
        'reactionner_tag':
            StringProp(default='None'),
        'env':
            DictProp(default={}),
        'module_type':
            StringProp(default='fork', fill_brok=['full_status']),
        'worker':
            StringProp(default='none'),
        'command':
            StringProp(),
        'timeout':
            IntegerProp(default=10),
        'ref':
            StringProp(default=''),
    }

    def __init__(self, params=None, parsing=True):
        super(ActionBase, self).__init__(params, parsing=parsing)

        # Set a creation time only if not provided
        if not params or 'creation_time' not in params:
            self.creation_time = time.time()
        # Set actions log only if not provided
        if not params or 'log_actions' not in params:
            self.log_actions = 'TEST_LOG_ACTIONS' in os.environ

        # Fill default parameters
        self.fill_default()

    def set_type_active(self):
        """Dummy function, only useful for checks"""
        pass

    def set_type_passive(self):
        """Dummy function, only useful for checks"""
        pass

    def get_local_environnement(self):
        """
        Mix the environment and the environment variables into a new local
        environment dictionary

        Note: We cannot just update the global os.environ because this
        would effect all other checks.

        :return: local environment variables
        :rtype: dict
        """
        # Do not use copy.copy() here, as the resulting copy still
        # changes the real environment (it is still a os._Environment
        # instance).
        local_env = os.environ.copy()
        for local_var in self.env:
            local_env[local_var] = self.env[local_var].encode('utf8')
        return local_env

    def execute(self):
        """Start this action command. The command will be executed in a
        subprocess.

        :return: None or str 'toomanyopenfiles'
        :rtype: None | str
        """
        self.status = 'launched'
        self.check_time = time.time()
        self.wait_time = 0.0001
        self.last_poll = self.check_time
        # Get a local env variables with our additional values
        self.local_env = self.get_local_environnement()

        # Initialize stdout and stderr. we will read them in small parts
        # if the fcntl is available
        self.stdoutdata = ''
        self.stderrdata = ''

        logger.debug("Launch command: '%s'", self.command)
        if self.log_actions:
            logger.info("Launch command: '%s'", self.command)

        return self.execute__()  # OS specific part

    def get_outputs(self, out, max_plugins_output_length):
        """Get outputs from single output (split perfdata etc).
        Edit output, perf_data and long_output attributes.

        :param out: output data of a check
        :type out: str
        :param max_plugins_output_length: max plugin data length
        :type max_plugins_output_length: int
        :return: None
        """
        # Squeeze all output after max_plugins_output_length
        out = out[:max_plugins_output_length]
        # manage escaped pipes
        out = out.replace(r'\|', '___PROTECT_PIPE___')
        # Then cuts by lines
        elts = out.split('\n')
        # For perf data
        elts_line1 = elts[0].split('|')

        # First line before | is output, strip it
        self.output = elts_line1[0].strip().replace('___PROTECT_PIPE___', '|')
        self.output = self.output.decode('utf8', 'ignore')

        # Init perfdata as empty
        self.perf_data = ''
        # After | it is perfdata, strip it
        if len(elts_line1) > 1:
            self.perf_data = elts_line1[1].strip().replace('___PROTECT_PIPE___', '|')

        # Now manage others lines. Before the | it's long_output
        # And after it's all perf_data, \n joined
        long_output = []
        in_perfdata = False
        for line in elts[1:]:
            # if already in perfdata, direct append
            if in_perfdata:
                self.perf_data += ' ' + line.strip().replace('___PROTECT_PIPE___', '|')
            else:  # not already in perf_data, search for the | part :)
                elts = line.split('|', 1)
                # The first part will always be long_output
                long_output.append(elts[0].strip().replace('___PROTECT_PIPE___', '|'))
                if len(elts) > 1:
                    in_perfdata = True
                    self.perf_data += ' ' + elts[1].strip().replace('___PROTECT_PIPE___', '|')

        # long_output is all non output and performance data, joined with \n
        self.long_output = '\n'.join(long_output)
        # Get sure the performance data are stripped
        self.perf_data = self.perf_data.strip()

        logger.debug("Command result for '%s': %d, %s",
                     self.command, self.exit_status, self.output)
        if self.log_actions:
            logger.info("Check result for '%s': %d, %s",
                           self.command, self.exit_status, self.output)

    def check_finished(self, max_plugins_output_length):
        """Handle action if it is finished (get stdout, stderr, exit code...)

        :param max_plugins_output_length: max plugin data length
        :type max_plugins_output_length: int
        :return: None
        """
        # We must wait, but checks are variable in time
        # so we do not wait the same for an little check
        # than a long ping. So we do like TCP: slow start with *2
        # but do not wait more than 0.1s.
        self.last_poll = time.time()

        _, _, child_utime, child_stime, _ = os.times()
        if self.process.poll() is None:
            # polling every 1/2 s ... for a timeout in seconds, this is enough
            self.wait_time = min(self.wait_time * 2, 0.5)
            now = time.time()

            # If the fcntl is available (unix) we try to read in a
            # asynchronous mode, so we won't block the PIPE at 64K buffer
            # (deadlock...)
            if fcntl:
                self.stdoutdata += no_block_read(self.process.stdout)
                self.stderrdata += no_block_read(self.process.stderr)

            if (now - self.check_time) > self.timeout:
                self.kill__()
                self.status = 'timeout'
                self.execution_time = now - self.check_time
                self.exit_status = 3
                # Do not keep a pointer to the process
                del self.process
                # Get the user and system time
                _, _, n_child_utime, n_child_stime, _ = os.times()
                self.u_time = n_child_utime - child_utime
                self.s_time = n_child_stime - child_stime
                if self.log_actions:
                    logger.info("Check for '%s' exited on timeout (%d s)",
                                   self.command, self.timeout)
                return
            return

        # Get standards outputs from the communicate function if we do
        # not have the fcntl module (Windows, and maybe some special
        # unix like AIX)
        if not fcntl:
            (self.stdoutdata, self.stderrdata) = self.process.communicate()
        else:
            # The command was to quick and finished even before we can
            # polled it first. So finish the read.
            self.stdoutdata += no_block_read(self.process.stdout)
            self.stderrdata += no_block_read(self.process.stderr)

        self.exit_status = self.process.returncode
        if self.log_actions:
            logger.info("Check for '%s' exited with return code %d",
                           self.command, self.exit_status)

        # we should not keep the process now
        del self.process

        if (  # check for bad syntax in command line:
            'sh: -c: line 0: unexpected EOF while looking for matching' in self.stderrdata or
            ('sh: -c:' in self.stderrdata and ': Syntax' in self.stderrdata) or
            'Syntax error: Unterminated quoted string' in self.stderrdata
        ):
            # Very, very ugly. But subprocess._handle_exitstatus does
            # not see a difference between a regular "exit 1" and a
            # bailing out shell. Strange, because strace clearly shows
            # a difference. (exit_group(1) vs. exit_group(257))
            self.stdoutdata = self.stdoutdata + self.stderrdata
            self.exit_status = 3

        if self.exit_status not in VALID_EXIT_STATUS:
            self.exit_status = 3

        if not self.stdoutdata.strip():
            self.stdoutdata = self.stderrdata

        # Now grep what we want in the output
        self.get_outputs(self.stdoutdata, max_plugins_output_length)

        # We can clean the useless properties now
        del self.stdoutdata
        del self.stderrdata

        self.status = 'done'
        self.execution_time = time.time() - self.check_time
        # Also get the system and user times
        _, _, n_child_utime, n_child_stime, _ = os.times()
        self.u_time = n_child_utime - child_utime
        self.s_time = n_child_stime - child_stime

    def copy_shell__(self, new_i):
        """Copy all attributes listed in 'only_copy_prop' from `self` to
        `new_i`.

        :param new_i: object to
        :type new_i: object
        :return: object with new properties added
        :rtype: object
        """
        for prop in ONLY_COPY_PROP:
            setattr(new_i, prop, getattr(self, prop))
        return new_i

    def got_shell_characters(self):
        """Check if the command_attribute (command line) has shell characters
        Shell characters are : '!', '$', '^', '&', '*', '(', ')', '~', '[', ']',
                               '|', '{', '}', ';', '<', '>', '?', '`'

        :return: True if one shell character is found, False otherwise
        :rtype: bool
        """
        for character in SHELLCHARS:
            if character in self.command:
                return True
        return False

    def execute__(self, force_shell=False):
        """Execute action in a subprocess

        :return: None
        """
        pass

    def kill__(self):
        """Kill the action and close fds
        :return: None
        """
        pass

# OS specific "execute__" & "kill__" are defined by "Action" class
# definition:
#

if os.name != 'nt':

    class Action(ActionBase):
        """Action class for *NIX systems

        """

        properties = ActionBase.properties.copy()

        def execute__(self, force_shell=sys.version_info < (2, 7)):
            """Execute action in a subprocess

            :return: None or str 'toomanyopenfiles'
            TODO: Clean this
            """
            # We allow direct launch only for 2.7 and higher version
            # because if a direct launch crash, under this the file handles
            # are not releases, it's not good.

            # If the command line got shell characters, we should go
            # in a shell mode. So look at theses parameters
            force_shell |= self.got_shell_characters()

            # 2.7 and higher Python version need a list of args for cmd
            # and if not force shell (if, it's useless, even dangerous)
            # 2.4->2.6 accept just the string command
            if sys.version_info < (2, 7) or force_shell:
                cmd = self.command.encode('utf8', 'ignore')
            else:
                try:
                    cmd = shlex.split(self.command.encode('utf8', 'ignore'))
                except Exception, exp:  # pylint: disable=W0703
                    self.output = 'Not a valid shell command: ' + exp.__str__()
                    self.exit_status = 3
                    self.status = 'done'
                    self.execution_time = time.time() - self.check_time
                    return

            # Now: GO for launch!
            # logger.debug("Launching: %s" % (self.command.encode('utf8', 'ignore')))

            # The preexec_fn=os.setsid is set to give sons a same
            # process group. See
            # http://www.doughellmann.com/PyMOTW/subprocess/ for
            # detail about this.
            try:
                self.process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    close_fds=True, shell=force_shell, env=self.local_env,
                    preexec_fn=os.setsid)
            except OSError, exp:
                logger.error("Fail launching command: %s %s %s",
                             self.command, exp, force_shell)
                # Maybe it's just a shell we try to exec. So we must retry
                if (not force_shell and exp.errno == 8 and
                        exp.strerror == 'Exec format error'):
                    return self.execute__(True)
                self.output = exp.__str__()
                self.exit_status = 2
                self.status = 'done'
                self.execution_time = time.time() - self.check_time

                # Maybe we run out of file descriptor. It's not good at all!
                if exp.errno == 24 and exp.strerror == 'Too many open files':
                    return 'toomanyopenfiles'

        def kill__(self):
            """Kill the action and close fds

            :return: None
            """
            # We kill a process group because we launched them with
            # preexec_fn=os.setsid and so we can launch a whole kill
            # tree instead of just the first one
            os.killpg(self.process.pid, signal.SIGKILL)
            # Try to force close the descriptors, because python seems to have problems with them
            for file_d in [self.process.stdout, self.process.stderr]:
                try:
                    file_d.close()
                except Exception:  # pylint: disable=W0703
                    pass


else:  # pragma: no cover, not currently tested with Windows...

    import ctypes  # pylint: disable=C0411,C0413

    class Action(ActionBase):
        """Action class for Windows systems

        """

        properties = ActionBase.properties.copy()

        def execute__(self, force_shell=False):
            """Execute action in a subprocess

            :return: None
            """
            # 2.7 and higher Python version need a list of args for cmd
            # 2.4->2.6 accept just the string command
            if sys.version_info < (2, 7):
                cmd = self.command
            else:
                try:
                    cmd = shlex.split(self.command.encode('utf8', 'ignore'))
                except Exception, exp:  # pylint: disable=W0703
                    self.output = 'Not a valid shell command: ' + exp.__str__()
                    self.exit_status = 3
                    self.status = 'done'
                    self.execution_time = time.time() - self.check_time
                    return

            try:
                self.process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    env=self.local_env, shell=True)
            except WindowsError, exp:  # pylint: disable=E0602
                logger.info("We kill the process: %s %s", exp, self.command)
                self.status = 'timeout'
                self.execution_time = time.time() - self.check_time

        def kill__(self):
            """Wrapped to call TerminateProcess

            :return: None
            TODO: This look like python2.5 style. Maybe we change that.
            """
            # pylint: disable=E1101
            ctypes.windll.kernel32.TerminateProcess(int(self.process._handle), -1)
