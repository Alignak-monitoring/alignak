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
import psutil

# For readinf files in non-blocking mode.
# This only works from now on Unix systems
try:
    import fcntl
except ImportError:
    fcntl = None

from alignak.alignakobject import AlignakObject
from alignak.property import BoolProp, IntegerProp, FloatProp, StringProp, DictProp


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

__all__ = ('Action', )

VALID_EXIT_STATUS = (0, 1, 2, 3)

ACT_STATUS_SCHEDULED = u'scheduled'
ACT_STATUS_LAUNCHED = u'launched'
ACT_STATUS_POLLED = u'in_poller'
ACT_STATUS_QUEUED = u'queued'
ACT_STATUS_WAIT_DEPEND = u'wait_dependent'
ACT_STATUS_WAITING_ME = u'wait_me'
ACT_STATUS_TIMEOUT = u'timeout'
ACT_STATUS_DONE = u'done'
ACT_STATUS_ZOMBIE = u'zombie'
ACT_STATUS_WAIT_CONSUME = u'wait_consume'
ACTION_VALID_STATUS = [ACT_STATUS_SCHEDULED, ACT_STATUS_LAUNCHED,
                       ACT_STATUS_POLLED, ACT_STATUS_QUEUED, ACT_STATUS_WAIT_DEPEND,
                       ACT_STATUS_DONE, ACT_STATUS_TIMEOUT,
                       ACT_STATUS_WAIT_CONSUME, ACT_STATUS_ZOMBIE]

ONLY_COPY_PROP = ('uuid', 'status', 'command', 't_to_go', 'timeout', 'env',
                  'module_type', 'execution_time', 'u_time', 's_time')

SHELLCHARS = ('!', '$', '^', '&', '*', '(', ')', '~', '[', ']',
              '|', '{', '}', ';', '<', '>', '?', '`')


def no_block_read(output):
    """Try to read a file descriptor in a non blocking mode

    If the fcntl is available (unix only) we try to read in a
    asynchronous mode, so we won't block the PIPE at 64K buffer
    (deadlock...)

    :param output: file or socket to read from
    :type output: file
    :return: data read from fd
    :rtype: str
    """
    _buffer = ""
    if not fcntl:
        return _buffer

    o_fd = output.fileno()
    o_fl = fcntl.fcntl(o_fd, fcntl.F_GETFL)
    fcntl.fcntl(o_fd, fcntl.F_SETFL, o_fl | os.O_NONBLOCK)
    try:
        _buffer = output.read()
    except Exception:  # pylint: disable=broad-except
        pass

    return _buffer


class ActionError(Exception):
    """Exception raised for errors when executing actions

    Attributes:
        msg  -- explanation of the error
    """

    def __init__(self, msg):
        super(ActionError, self).__init__()
        self.message = msg

    def __str__(self):  # pragma: no cover
        """Exception to String"""
        return "Action error: %s" % self.message


class ActionBase(AlignakObject):
    # pylint: disable=too-many-instance-attributes
    """
    This abstract class is used to have a common base for both actions (event handlers and
    notifications) and checks.

    The Action may be on internal one if it does require to use a Worker process to run the
    action because the Scheduler is able to resolve the action by itseld.

    This class is specialized according to the running OS. Currently, only Linux/Unix like OSes
    are tested
    """
    process = None

    properties = {
        'is_a':
            StringProp(default=u''),
        'type':
            StringProp(default=u''),
        'internal':
            BoolProp(default=False),
        'creation_time':
            FloatProp(default=0.0),
        '_in_timeout':
            BoolProp(default=False),
        'status':
            StringProp(default=ACT_STATUS_SCHEDULED),
        'exit_status':
            IntegerProp(default=3),
        'output':
            StringProp(default=u'', fill_brok=['full_status']),
        'long_output':
            StringProp(default=u'', fill_brok=['full_status']),
        'perf_data':
            StringProp(default=u'', fill_brok=['full_status']),
        't_to_go':
            FloatProp(default=0.0),
        'check_time':
            IntegerProp(default=0),
        'last_poll':
            IntegerProp(default=0),
        'execution_time':
            FloatProp(default=0.0),
        'wait_time':
            FloatProp(default=0.001),
        'u_time':
            FloatProp(default=0.0),
        's_time':
            FloatProp(default=0.0),
        'reactionner_tag':
            StringProp(default=u'None'),
        'env':
            DictProp(default={}),
        'module_type':
            StringProp(default=u'fork', fill_brok=['full_status']),
        'my_worker':
            StringProp(default=u'none'),
        'command':
            StringProp(default=''),
        'timeout':
            IntegerProp(default=10),
        'ref':
            StringProp(default=u'unset'),
        'ref_type':
            StringProp(default=u'unset'),
        'my_scheduler':
            StringProp(default=u'unassigned'),
    }

    def __init__(self, params=None, parsing=False):
        super(ActionBase, self).__init__(params, parsing=parsing)

        # Set a creation time only if not provided
        if not params or 'creation_time' not in params:
            self.creation_time = time.time()
        # Set actions log only if not provided
        if not params or 'log_actions' not in params:
            self.log_actions = 'ALIGNAK_LOG_ACTIONS' in os.environ

        # Fill default parameters
        self.fill_default()

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
            local_env[local_var] = self.env[local_var]
        return local_env

    def execute(self):
        """Start this action command in a subprocess.

        :raise: ActionError
            'toomanyopenfiles' if too many opened files on the system
            'no_process_launched' if arguments parsing failed
            'process_launch_failed': if the process launch failed

        :return: reference to the started process
        :rtype: psutil.Process
        """
        self.status = ACT_STATUS_LAUNCHED
        self.check_time = time.time()
        self.wait_time = 0.0001
        self.last_poll = self.check_time

        # Get a local env variables with our additional values
        self.local_env = self.get_local_environnement()

        # Initialize stdout and stderr.
        self.stdoutdata = ''
        self.stderrdata = ''

        logger.debug("Launch command: '%s', ref: %s, timeout: %s",
                     self.command, self.ref, self.timeout)
        if self.log_actions:
            if os.environ['ALIGNAK_LOG_ACTIONS'] == 'WARNING':
                logger.warning("Launch command: '%s'", self.command)
            else:
                logger.info("Launch command: '%s'", self.command)

        return self._execute()  # OS specific part

    def get_outputs(self, out, max_plugins_output_length):
        """Get check outputs from single output (split perfdata etc).

        Updates output, perf_data and long_output attributes.

        :param out: output data of a check
        :type out: str
        :param max_output: max plugin data length
        :type max_output: int
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
        try:
            self.output = self.output.decode('utf8', 'ignore')
        except UnicodeEncodeError:
            pass
        except AttributeError:
            pass

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

        logger.debug("Command result for '%s': %d, %s", self.command, self.exit_status, self.output)

        if self.log_actions:
            if os.environ['ALIGNAK_LOG_ACTIONS'] == 'WARNING':
                logger.warning("Check result for '%s': %d, %s",
                               self.command, self.exit_status, self.output)
                if self.perf_data:
                    logger.warning("Performance data for '%s': %s", self.command, self.perf_data)
            else:
                logger.info("Check result for '%s': %d, %s",
                            self.command, self.exit_status, self.output)
                if self.perf_data:
                    logger.info("Performance data for '%s': %s", self.command, self.perf_data)

    def check_finished(self, max_plugins_output_length):
        # pylint: disable=too-many-branches
        """Handle action if it is finished (get stdout, stderr, exit code...)

        :param max_plugins_output_length: max plugin data length
        :type max_plugins_output_length: int
        :return: None
        """
        self.last_poll = time.time()

        _, _, child_utime, child_stime, _ = os.times()

        # Not yet finished...
        if self.process.poll() is None:
            # We must wait, but checks are variable in time so we do not wait the same
            # for a little check or a long ping. So we do like TCP: slow start with a very
            # shot time (0.0001 s) increased *2 but do not wait more than 0.5 s.
            self.wait_time = min(self.wait_time * 2, 0.5)
            now = time.time()
            # This log is really spamming... uncomment if you really need this information :)
            # logger.debug("%s - Process pid=%d is still alive", now, self.process.pid)

            # Get standard outputs in non blocking mode from the process streams
            stdout = no_block_read(self.process.stdout)
            stderr = no_block_read(self.process.stderr)

            try:
                self.stdoutdata += stdout.decode("utf-8")
                self.stderrdata += stderr.decode("utf-8")
            except AttributeError:
                pass

            if (now - self.check_time) > self.timeout:
                logger.warning("Process pid=%d spent too much time: %.2f seconds",
                               self.process.pid, now - self.check_time)
                self._in_timeout = True
                self._kill()
                self.status = ACT_STATUS_TIMEOUT
                self.execution_time = now - self.check_time
                self.exit_status = 3

                if self.log_actions:
                    if os.environ['ALIGNAK_LOG_ACTIONS'] == 'WARNING':
                        logger.warning("Action '%s' exited on timeout (%d s)",
                                       self.command, self.timeout)
                    else:
                        logger.info("Action '%s' exited on timeout (%d s)",
                                    self.command, self.timeout)

                # Do not keep the process objcet
                del self.process

                # Replace stdout with stderr if stdout is empty
                self.stdoutdata = self.stdoutdata.strip()
                if not self.stdoutdata:
                    self.stdoutdata = self.stderrdata

                # Now grep what we want in the output
                self.get_outputs(self.stdoutdata, max_plugins_output_length)

                # We can clean the useless properties now
                del self.stdoutdata
                del self.stderrdata

                # Get the user and system time
                _, _, n_child_utime, n_child_stime, _ = os.times()
                self.u_time = n_child_utime - child_utime
                self.s_time = n_child_stime - child_stime

                return
            return

        logger.debug("Process pid=%d exited with %d", self.process.pid, self.process.returncode)

        if fcntl:
            # Get standard outputs in non blocking mode from the process streams
            stdout = no_block_read(self.process.stdout)
            stderr = no_block_read(self.process.stderr)
        else:
            # Get standard outputs from the communicate function
            (stdout, stderr) = self.process.communicate()

        try:
            self.stdoutdata += stdout.decode("utf-8")
            self.stderrdata += stderr.decode("utf-8")
        except AttributeError:
            pass

        self.exit_status = self.process.returncode
        if self.log_actions:
            if os.environ['ALIGNAK_LOG_ACTIONS'] == 'WARNING':
                logger.warning("Action '%s' exited with code %d", self.command, self.exit_status)
            else:
                logger.info("Action '%s' exited with code %d",
                            self.command, self.exit_status)

        # We do not need the process now
        del self.process

        # check for bad syntax in command line:
        if (self.stderrdata.find('sh: -c: line 0: unexpected EOF') >= 0 or
                (self.stderrdata.find('sh: -c: ') >= 0 and
                 self.stderrdata.find(': Syntax') >= 0 or
                 self.stderrdata.find('Syntax error: Unterminated quoted string') >= 0)):
            logger.warning("Bad syntax in command line!")
            # Very, very ugly. But subprocess._handle_exitstatus does
            # not see a difference between a regular "exit 1" and a
            # bailing out shell. Strange, because strace clearly shows
            # a difference. (exit_group(1) vs. exit_group(257))
            self.stdoutdata = self.stdoutdata + self.stderrdata
            self.exit_status = 3

        # Make sure that exit code is a valid exit code
        if self.exit_status not in VALID_EXIT_STATUS:
            self.exit_status = 3

        # Replace stdout with stderr if stdout is empty
        self.stdoutdata = self.stdoutdata.strip()
        if not self.stdoutdata:
            self.stdoutdata = self.stderrdata

        # Now grep what we want in the output
        self.get_outputs(self.stdoutdata, max_plugins_output_length)

        # We can clean the useless properties now
        del self.stdoutdata
        del self.stderrdata

        self.status = ACT_STATUS_DONE
        self.execution_time = time.time() - self.check_time

        # Also get the system and user times
        _, _, n_child_utime, n_child_stime, _ = os.times()
        self.u_time = n_child_utime - child_utime
        self.s_time = n_child_stime - child_stime

    def copy_shell__(self, new_i):
        """Create all attributes listed in 'ONLY_COPY_PROP' and return `self` with these attributes.

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
        return any(c in SHELLCHARS for c in self.command)

    def _execute(self, force_shell=False):
        """Execute action in a subprocess

        :return: None
        """
        pass

    def _kill(self):
        """Kill the action and close fds
        :return: None
        """
        pass


# OS specific "_execute" & "_kill" functions are defined inside the "Action" class
# definition:
#
if os.name != 'nt':

    class Action(ActionBase):
        """Action class for *NIX systems

        """
        properties = ActionBase.properties.copy()

        def _execute(self, force_shell=sys.version_info < (2, 7)):
            """Execute the action command in a subprocess

            :raise: ActionError
                'toomanyopenfiles' if too many opened files on the system
                'no_process_launched' if arguments parsing failed
                'process_launch_failed': if the process launch failed

            :return: reference to the started process
            :rtype: psutil.Process
            """
            # If the command line got shell characters, we should start in a shell mode.
            force_shell |= self.got_shell_characters()
            logger.debug("Action execute, force shell: %s", force_shell)

            # 2.7 and higher Python version need a list of arguments for the started command
            cmd = self.command
            if not force_shell:
                # try:
                #     command = self.command.encode('utf8')
                # except AttributeError:
                #     print("Exception !")
                #     # Python 3 will raise an exception because the line is still unicode
                #     command = self.command
                #     pass
                #
                try:
                    cmd = shlex.split(self.command)
                except Exception as exp:  # pylint: disable=broad-except
                    self.output = 'Not a valid shell command: ' + str(exp)
                    self.exit_status = 3
                    self.status = ACT_STATUS_DONE
                    self.execution_time = time.time() - self.check_time
                    raise ActionError('no_process_launched')
            logger.debug("Action execute, cmd: %s", cmd)

            # The preexec_fn=os.setsid is set to give sons a same
            # process group. See
            # http://www.doughellmann.com/PyMOTW/subprocess/ for
            # detail about this.
            try:
                self.process = psutil.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                            close_fds=True, shell=force_shell,
                                            env=self.local_env, preexec_fn=os.setsid)

                logger.debug("Action execute, process: %s", self.process.pid)
            except OSError as exp:
                logger.error("Fail launching command: %s, force shell: %s, OSError: %s",
                             self.command, force_shell, exp)
                # Maybe it's just a shell we try to exec. So we must retry
                if (not force_shell and exp.errno == 8 and exp.strerror == 'Exec format error'):
                    logger.info("Retrying with forced shell...")
                    return self._execute(True)

                self.output = str(exp)
                self.exit_status = 2
                self.status = ACT_STATUS_DONE
                self.execution_time = time.time() - self.check_time

                # Maybe we run out of file descriptor. It's not good at all!
                if exp.errno == 24 and exp.strerror == 'Too many open files':
                    raise ActionError('toomanyopenfiles')

                raise ActionError('process_launch_failed')
            except Exception as exp:  # pylint: disable=broad-except
                logger.error("Fail launching command: %s, force shell: %s, exception: %s",
                             self.command, force_shell, exp)
                raise ActionError('process_launch_failed')

            # logger.info("- %s launched (pid=%d, gids=%s)",
            #             self.process.name(), self.process.pid, self.process.gids())

            return self.process

        def _kill(self):
            """Kill the action process and close fds

            :return: None
            """
            logger.debug("Action kill, cmd: %s", self.process.pid)

            # We kill a process group because we launched them with
            # preexec_fn=os.setsid and so we can launch a whole kill
            # tree instead of just the first one
            os.killpg(self.process.pid, signal.SIGKILL)

            # Try to force close the descriptors, because python seems to have problems with them
            for file_d in [self.process.stdout, self.process.stderr]:
                try:
                    file_d.close()
                except Exception as exp:  # pylint: disable=broad-except
                    logger.error("Exception when stopping command: %s %s", self.command, exp)


else:  # pragma: no cover, not currently tested with Windows...

    import ctypes  # pylint: disable=C0411,C0413

    class Action(ActionBase):
        """Action class for Windows systems

        """

        properties = ActionBase.properties.copy()

        def _execute(self, force_shell=False):
            """Execute action in a subprocess

            :return: None
            """
            # 2.7 and higher Python version need a list of args for cmd
            try:
                cmd = shlex.split(self.command)
            except Exception as exp:  # pylint: disable=W0703
                self.output = 'Not a valid shell command: ' + exp.__str__()
                self.exit_status = 3
                self.status = ACT_STATUS_DONE
                self.execution_time = time.time() - self.check_time
                return

            try:
                self.process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    env=self.local_env, shell=True)
            except WindowsError as exp:  # pylint: disable=E0602
                logger.info("We kill the process: %s %s", exp, self.command)
                self.status = ACT_STATUS_TIMEOUT
                self.execution_time = time.time() - self.check_time

        def _kill(self):
            """Wrapped to call TerminateProcess

            :return: None
            TODO: This look like python2.5 style. Maybe we change that.
            """
            # pylint: disable=E1101
            ctypes.windll.kernel32.TerminateProcess(int(self.process._handle), -1)
