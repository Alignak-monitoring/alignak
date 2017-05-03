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
#     David Moreau Simard, dmsimard@iweb.com
#     Andrew McGilvray, amcgilvray@kixeye.com
#     Guillaume Bour, guillaume@bour.cc
#     Alexandre Viau, alexandre@alexandreviau.net
#     Frédéric Vachon, fredvac@gmail.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     xkilian, fmikus@acktomic.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Zoran Zaric, zz@zoranzaric.de
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Daniel Hokka Zakrisson, daniel@hozac.com
#     Grégory Starck, g.starck@gmail.com
#     Alexander Springer, alex.spri@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     david hannequin, david.hannequin@gmail.com
#     Romain Forlot, rforlot@yahoo.com

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
This module provides abstraction for creating daemon in Alignak
"""
# pylint: disable=R0904
from __future__ import print_function
import os
import errno
import sys
import time
import signal
import select
import ConfigParser
import threading
import logging
from Queue import Empty
from multiprocessing.managers import SyncManager

try:
    from pwd import getpwnam, getpwuid
    from grp import getgrnam, getgrall, getgrgid

    def get_cur_user():
        """Wrapper for getpwuid

        :return: user name
        :rtype: str
        """
        return getpwuid(os.getuid()).pw_name

    def get_cur_group():
        """Wrapper for getgrgid

        :return: group name
        :rtype: str
        """
        return getgrgid(os.getgid()).gr_name

    def get_all_groups():  # pragma: no cover, not used in the testing environment...
        """Wrapper for getgrall

        :return: all groups
        :rtype: list
        """
        return getgrall()
except ImportError, exp:  # pragma: no cover, not for unit tests...
    # Like in Windows system
    # temporary workaround:
    def get_cur_user():
        """Fake getpwuid

        :return: alignak
        :rtype: str
        """
        return "alignak"

    def get_cur_group():
        """Fake getgrgid

        :return: alignak
        :rtype: str
        """
        return "alignak"

    def get_all_groups():
        """Fake getgrall

        :return: []
        :rtype: list
        """
        return []

from alignak.log import setup_logger, get_logger_fds
from alignak.http.daemon import HTTPDaemon, InvalidWorkDir, PortNotFree
from alignak.stats import statsmgr
from alignak.modulesmanager import ModulesManager
from alignak.property import StringProp, BoolProp, PathProp, ConfigPathProp, IntegerProp, \
    LogLevelProp
from alignak.misc.common import setproctitle
from alignak.version import VERSION

logger = logging.getLogger(__name__)  # pylint: disable=C0103

IS_PY26 = sys.version_info[:2] < (2, 7)

# #########################   DAEMON PART    ###############################
# The standard I/O file descriptors are redirected to /dev/null by default.
REDIRECT_TO = getattr(os, "devnull", "/dev/null")

UMASK = 027


class InvalidPidFile(Exception):
    """Exception raised when a pid file is invalid"""
    pass


DEFAULT_WORK_DIR = './'


# pylint: disable=R0902
class Daemon(object):
    """Class providing daemon level call for Alignak
        TODO: Consider clean this code and use standard libs
    """

    properties = {
        'daemon_type':
            StringProp(default='unknown'),
        # workdir is relative to $(dirname "$0"/..)
        # where "$0" is the path of the file being executed,
        # in python normally known as:
        #
        #  os.path.join( os.getcwd(), sys.argv[0] )
        #
        # as returned once the daemon is started.
        'workdir':
            PathProp(default=DEFAULT_WORK_DIR),
        'logdir':
            PathProp(default=DEFAULT_WORK_DIR),
        'etcdir':
            PathProp(default=DEFAULT_WORK_DIR),
        'host':
            StringProp(default='0.0.0.0'),
        'user':
            StringProp(default=get_cur_user()),
        'group':
            StringProp(default=get_cur_group()),
        'use_ssl':
            BoolProp(default=False),
        'server_key':
            StringProp(default='etc/certs/server.key'),
        'ca_cert':
            StringProp(default=''),
        'server_dh':
            StringProp(default=''),
        'server_cert':
            StringProp(default='etc/certs/server.cert'),
        'use_local_log':
            BoolProp(default=True),
        'human_timestamp_log':
            BoolProp(default=True),
        'human_date_format':
            StringProp(default='%Y-%m-%d %H:%M:%S %Z'),
        'log_level':
            LogLevelProp(default='INFO'),
        'log_rotation_when':
            StringProp(default='midnight'),
        'log_rotation_interval':
            IntegerProp(default=1),
        'log_rotation_count':
            IntegerProp(default=7),
        'local_log':
            StringProp(default='/usr/local/var/log/arbiter.log'),
        'hard_ssl_name_check':
            BoolProp(default=False),
        'idontcareaboutsecurity':
            BoolProp(default=False),
        'daemon_enabled':
            BoolProp(default=True),
        'spare':
            BoolProp(default=False),
        'max_queue_size':
            IntegerProp(default=0),
        'daemon_thread_pool_size':
            IntegerProp(default=8),
    }

    def __init__(self, name, config_file, is_daemon, do_replace, debug, debug_file):
        """

        :param name:
        :param config_file:
        :param is_daemon:
        :param do_replace:
        :param debug:
        :param debug_file:
        """
        self.check_shm()

        self.name = name
        self.config_file = config_file
        self.is_daemon = is_daemon
        self.do_replace = do_replace
        self.debug = debug
        self.debug_file = debug_file
        self.interrupted = False
        self.pidfile = None

        if self.debug:
            print("Daemon %s is in debug mode" % self.name)

        if self.is_daemon:
            print("Daemon %s is in daemon mode" % self.name)

        # Track time
        now = time.time()
        self.program_start = now
        self.t_each_loop = now  # used to track system time change
        self.sleep_time = 0.0  # used to track the time we wait

        self.http_thread = None
        self.http_daemon = None

        self.new_conf = None
        self.cur_conf = None
        self.conf_lock = threading.RLock()
        self.lock = threading.RLock()

        # Flag to know if we need to dump memory or not
        self.need_dump_memory = False

        # Flag to dump objects or not
        self.need_objects_dump = False

        # Flag to reload configuration
        self.need_config_reload = False

        # Keep a trace of the file descriptors allocated by the logger
        self.local_log_fds = None

        # Put in queue some debug output we will raise
        # when we will be in daemon
        self.debug_output = []

        # We will initialize the Manager() when we load modules
        # and be really forked()
        self.sync_manager = None

        os.umask(UMASK)
        self.set_exit_handler()

        # Fill the properties
        properties = self.__class__.properties
        for prop, entry in properties.items():
            setattr(self, prop, entry.pythonize(entry.default))

    # At least, lose the local log file if needed
    def do_stop(self):
        """Execute the stop of this daemon:
         - Stop the http thread and join it
         - Close the http socket
         - Shutdown the manager
         - Stop and join all started "modules"

        :return: None
        """
        logger.info("Stopping %s...", self.name)

        if self.http_daemon:
            logger.info("Shutting down http_daemon...")
            self.http_daemon.request_stop()

        if self.http_thread:
            logger.info("Joining http_thread...")
            # Add a timeout to join so that we can manually quit
            self.http_thread.join(timeout=15)
            if self.http_thread.is_alive():
                logger.warning("http_thread failed to terminate. Calling _Thread__stop")
                try:
                    self.http_thread._Thread__stop()  # pylint: disable=E1101
                except Exception:  # pylint: disable=W0703
                    pass
            self.http_thread = None

        if self.http_daemon:
            self.http_daemon = None

        if self.sync_manager:
            logger.info("Shutting down manager...")
            self.sync_manager.shutdown()
            self.sync_manager = None

        # Maybe the modules manager is not even created!
        if getattr(self, 'modules_manager', None):
            # We save what we can but NOT for the scheduler
            # because the current sched object is a dummy one
            # and the old one has already done it!
            if not hasattr(self, 'sched'):
                self.hook_point('save_retention')
            # And we quit
            logger.info('Stopping all modules...')
            self.modules_manager.stop_all()

    def request_stop(self):  # pragma: no cover, not used during test because of sys.exit !
        """Remove pid and stop daemon

        :return: None
        """
        self.unlink()
        self.do_stop()

        logger.info("Stopped %s.", self.name)
        sys.exit(0)

    def look_for_early_exit(self):
        """Stop the daemon if it is not enabled

        :return: None
        """
        if not self.daemon_enabled:
            logger.info('This daemon is disabled in configuration. Bailing out')
            self.request_stop()

    def do_loop_turn(self):
        """Abstract method for daemon loop turn.
        It must be overridden by class inheriting from Daemon

        :return: None
        """
        raise NotImplementedError()

    def do_mainloop(self):
        """ Main loop for alignak daemon (except scheduler)

        :return: None
        """
        while True:
            self.do_loop_turn()
            # If ask us to dump memory, do it
            if self.need_dump_memory:
                logger.debug('Dumping memory')
                self.dump_memory()
                self.need_dump_memory = False
            if self.need_objects_dump:
                logger.debug('Dumping objects')
                self.need_objects_dump = False
            if self.need_config_reload:
                logger.debug('Ask for configuration reloading')
                return
            # Maybe we ask us to die, if so, do it :)
            if self.interrupted:
                break
        self.request_stop()

    def do_load_modules(self, modules):
        """Wrapper for calling load_and_init method of modules_manager attribute

        :param modules: list of modules that should be loaded by the daemon
        :return: None
        """
        logger.info("Loading modules...")

        loading_result = self.modules_manager.load_and_init(modules)
        if loading_result:
            if self.modules_manager.instances:
                logger.info("I correctly loaded my modules: [%s]",
                            ','.join([inst.get_name() for inst in self.modules_manager.instances]))
            else:
                logger.info("I do not have any module")
        else:
            logger.error("Errors were encountered when checking and loading modules:")
            for msg in self.modules_manager.configuration_errors:
                logger.error(msg)

        if len(self.modules_manager.configuration_warnings):
            for msg in self.modules_manager.configuration_warning:
                logger.warning(msg)

    def add(self, elt):
        """ Abstract method for adding brok
         It is overridden in subclasses of Daemon

        :param elt: element to add
        :type elt:
        :return: None
        """
        pass

    @staticmethod
    def dump_memory():
        """ Try to dump memory
        Does not really work :/

        :return: None
        TODO: Clean this
        """
        try:
            from guppy import hpy

            logger.info("I dump my memory, it can take a while")
            heap = hpy()
            logger.info(heap.heap())
        except ImportError:
            logger.warning('I do not have the module guppy for memory dump, please install it')

    def load_modules_manager(self, daemon_name):
        """Instantiate Modulesmanager and load the SyncManager (multiprocessing)

        :return: None
        """
        self.modules_manager = ModulesManager(daemon_name, self.sync_manager,
                                              max_queue_size=getattr(self, 'max_queue_size', 0))

    def change_to_workdir(self):
        """Change working directory to working attribute

        :return: None
        """
        logger.info("Changing working directory to: %s", self.workdir)
        self.workdir = os.path.abspath(self.workdir)
        try:
            os.chdir(self.workdir)
        except Exception, exp:
            raise InvalidWorkDir(exp)
        self.debug_output.append("Successfully changed to workdir: %s" % (self.workdir))
        logger.info("Using working directory: %s", os.path.abspath(self.workdir))

    def unlink(self):
        """Remove the daemon's pid file

        :return: None
        """
        logger.debug("Unlinking %s", self.pidfile)
        try:
            os.unlink(self.pidfile)
        except OSError, exp:
            logger.error("Got an error unlinking our pidfile: %s", exp)

    @staticmethod
    def check_shm():
        """ Check /dev/shm right permissions

        :return: None
        """
        import stat
        shm_path = '/dev/shm'
        if os.name == 'posix' and os.path.exists(shm_path):
            # We get the access rights, and we check them
            mode = stat.S_IMODE(os.lstat(shm_path)[stat.ST_MODE])
            if not mode & stat.S_IWUSR or not mode & stat.S_IRUSR:
                logger.critical("The directory %s is not writable or readable."
                                "Please make it read writable: %s", shm_path, shm_path)
                sys.exit(2)

    def __open_pidfile(self, write=False):
        """Open pid file in read or write mod

        :param write: boolean to open file in write mod (true = write)
        :type write: bool
        :return: None
        """
        # if problem on opening or creating file it'll be raised to the caller:
        try:
            pid = os.path.abspath(self.pidfile)
            self.debug_output.append("Opening pid file: %s" % pid)
            # Windows do not manage the rw+ mode,
            # so we must open in read mode first, then reopen it write mode...
            if not write and os.path.exists(pid):
                self.fpid = open(pid, 'r+')
            else:  # If it doesn't exist too, we create it as void
                self.fpid = open(pid, 'w+')
        except Exception as err:
            raise InvalidPidFile(err)

    def check_parallel_run(self):
        """Check (in pid file) if there isn't already a daemon running.
        If yes and do_replace: kill it.
        Keep in self.fpid the File object to the pid file. Will be used by writepid.

        :return: None
        """
        # TODO: other daemon run on nt
        if os.name == 'nt':  # pragma: no cover, not currently tested with Windows...
            logger.warning("The parallel daemon check is not available on Windows")
            self.__open_pidfile(write=True)
            return

        # First open the pid file in open mode
        self.__open_pidfile()
        try:
            pid_var = self.fpid.readline().strip(' \r\n')
            if pid_var:
                pid = int(pid_var)
                logger.info("Found an existing pid: '%s'", pid_var)
            else:
                logger.debug("Not found an existing pid: %s", self.pidfile)
                return
        except (IOError, ValueError) as err:
            logger.warning("pidfile is empty or has an invalid content: %s", self.pidfile)
            return

        if pid == os.getpid():
            return

        try:
            logger.info("Killing process: '%s'", pid)
            os.kill(pid, 0)
        except Exception as err:  # pylint: disable=W0703
            # consider any exception as a stale pidfile.
            # this includes :
            #  * PermissionError when a process with same pid exists but is executed by another user
            #  * ProcessLookupError: [Errno 3] No such process
            logger.info("Stale pidfile exists (%s), Reusing it.", err)
            return

        if not self.do_replace:
            raise SystemExit("valid pidfile exists (pid=%s) and not forced to replace. Exiting."
                             % pid)

        self.debug_output.append("Replacing previous instance %d" % pid)
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGQUIT)
        except os.error as err:
            if err.errno != errno.ESRCH:
                raise

        self.fpid.close()
        # TODO: give some time to wait that previous instance finishes?
        time.sleep(1)
        # we must also reopen the pid file in write mode
        # because the previous instance should have deleted it!!
        self.__open_pidfile(write=True)

    def write_pid(self, pid=None):
        """ Write pid to pidfile

        :param pid: pid of the process
        :type pid: None | int
        :return: None
        """
        if pid is None:
            pid = os.getpid()
        self.fpid.seek(0)
        self.fpid.truncate()
        self.fpid.write("%d" % (pid))
        self.fpid.close()
        del self.fpid  # no longer needed

    @staticmethod
    def close_fds(skip_close_fds):
        """Close all the process file descriptors.
        Skip the descriptors present in the skip_close_fds list

        :param skip_close_fds: list of fd to skip
        :type skip_close_fds: list
        :return: None
        """
        # First we manage the file descriptor, because debug file can be
        # relative to pwd
        import resource
        maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if maxfd == resource.RLIM_INFINITY:
            maxfd = 1024

        # Iterate through and close all file descriptors.
        for file_d in range(0, maxfd):
            if file_d in skip_close_fds:
                logger.debug("Do not close fd: %s", file_d)
                continue
            try:
                os.close(file_d)
            except OSError:  # ERROR, fd wasn't open to begin with (ignored)
                pass

    def daemonize(self, skip_close_fds=None):  # pragma: no cover, not for unit tests...
        """Go in "daemon" mode: close unused fds, redirect stdout/err,
        chdir, umask, fork-setsid-fork-writepid
        Do the double fork to properly go daemon

        :param skip_close_fds: list of fd to keep open
        :type skip_close_fds: list
        :return: None
        """
        logger.info("Daemonizing...")

        if skip_close_fds is None:
            skip_close_fds = []

        self.debug_output.append("Redirecting stdout and stderr as necessary..")
        if self.debug:
            fdtemp = os.open(self.debug_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
        else:
            fdtemp = os.open(REDIRECT_TO, os.O_RDWR)

        # We close all fd but what we need:
        self.close_fds(skip_close_fds + [self.fpid.fileno(), fdtemp])

        os.dup2(fdtemp, 1)  # standard output (1)
        os.dup2(fdtemp, 2)  # standard error (2)

        # Now the fork/setsid/fork..
        try:
            pid = os.fork()
        except OSError, err:
            raise Exception("%s [%d]" % (err.strerror, err.errno))

        if pid != 0:
            # In the father: we check if our child exit correctly
            # it has to write the pid of our future little child..
            def do_exit(sig, frame):  # pylint: disable=W0613
                """Exit handler if wait too long during fork

                :param sig: signal
                :param frame: current frame
                :return: None
                """
                logger.error("Timeout waiting child while it should have quickly returned ;"
                             "something weird happened")
                os.kill(pid, 9)
                sys.exit(1)
            # wait the child process to check its return status:
            signal.signal(signal.SIGALRM, do_exit)
            signal.alarm(3)  # forking & writing a pid in a file should be rather quick..
            # if it's not then something wrong can already be on the way so let's wait max
            # 3 secs here.
            pid, status = os.waitpid(pid, 0)
            if status != 0:
                logger.error("Something weird happened with/during second fork: status= %s", status)
            os._exit(status != 0)

        # halfway to daemonize..
        os.setsid()
        try:
            pid = os.fork()
        except OSError as err:
            raise Exception("%s [%d]" % (err.strerror, err.errno))
        if pid != 0:
            # we are the last step and the real daemon is actually correctly created at least.
            # we have still the last responsibility to write the pid of the daemon itself.
            self.write_pid(pid)
            os._exit(0)

        self.fpid.close()
        del self.fpid
        self.pid = os.getpid()
        self.debug_output.append("We are now fully daemonized :) pid=%d" % self.pid)
        # We can now output some previously silenced debug output
        logger.info("Printing stored debug messages prior to our daemonization")
        for stored in self.debug_output:
            logger.info(stored)
        del self.debug_output

    # The Manager is a sub-process, so we must be sure it won't have
    # a socket of your http server alive
    @staticmethod
    def _create_manager():
        """Instantiate and start a SyncManager

        :return: the manager
        :rtype: multiprocessing.managers.SyncManager
        """
        manager = SyncManager(('127.0.0.1', 0))
        manager.start()
        return manager

    def do_daemon_init_and_start(self):
        """Main daemon function.
        Clean, allocates, initializes and starts all necessary resources to go in daemon mode.

        :param daemon_name: daemon instance name (eg. arbiter-master). If not provided, only the
        daemon name (eg. arbiter) will be used for the process title
        :type daemon_name: str
        :return: False if the HTTP daemon can not be initialized, else True
        """
        self.set_proctitle()
        self.change_to_user_group()
        self.change_to_workdir()
        self.check_parallel_run()
        if not self.setup_communication_daemon():
            return False

        if self.is_daemon:
            # Do not close the local_log file too if it's open
            if self.local_log_fds:
                self.daemonize(skip_close_fds=self.local_log_fds)
            else:
                self.daemonize()
        else:
            self.write_pid()

        logger.info("Creating synchronization manager...")
        self.sync_manager = self._create_manager()
        logger.info("Created")

        logger.info("Starting http_daemon thread..")
        self.http_thread = threading.Thread(None, self.http_daemon_thread, 'http_thread')
        self.http_thread.daemon = True
        self.http_thread.start()
        logger.info("HTTP daemon thread started")

        return True

    def setup_communication_daemon(self):
        """ Setup HTTP server daemon to listen
        for incoming HTTP requests from other Alignak daemons

        :return: True if initialization is ok, else False
        """
        if hasattr(self, 'use_ssl'):  # "common" daemon
            ssl_conf = self
        else:
            ssl_conf = self.conf     # arbiter daemon..

        use_ssl = ssl_conf.use_ssl
        ca_cert = ssl_cert = ssl_key = server_dh = None

        # The SSL part
        if use_ssl:
            ssl_cert = os.path.abspath(str(ssl_conf.server_cert))
            if not os.path.exists(ssl_cert):
                logger.error('Error : the SSL certificate %s is missing (server_cert).'
                             'Please fix it in your configuration', ssl_cert)
                sys.exit(2)

            if str(ssl_conf.server_dh) != '':
                server_dh = os.path.abspath(str(ssl_conf.server_dh))
                logger.info("Using ssl dh cert file: %s", server_dh)

            if str(ssl_conf.ca_cert) != '':
                ca_cert = os.path.abspath(str(ssl_conf.ca_cert))
                logger.info("Using ssl ca cert file: %s", ca_cert)

            ssl_key = os.path.abspath(str(ssl_conf.server_key))
            if not os.path.exists(ssl_key):
                logger.error('Error : the SSL key %s is missing (server_key).'
                             'Please fix it in your configuration', ssl_key)
                sys.exit(2)
            logger.info("Using ssl server cert/key files: %s/%s", ssl_cert, ssl_key)

            if ssl_conf.hard_ssl_name_check:
                logger.info("Enabling hard SSL server name verification")

        # Let's create the HTTPDaemon, it will be exec after
        # pylint: disable=E1101
        try:
            self.http_daemon = HTTPDaemon(self.host, self.port, self.http_interface,
                                          use_ssl, ca_cert, ssl_key,
                                          ssl_cert, server_dh, self.daemon_thread_pool_size)
        except PortNotFree as exp:
            logger.error('The HTTP daemon port is not free...')
            logger.exception('The HTTP daemon port is not free: %s', exp)
            return False

        return True

    @staticmethod
    def get_socks_activity(socks, timeout):
        """ Global loop part : wait for socket to be ready

        :param socks: a socket file descriptor list
        :type socks:
        :param timeout: timeout to read from fd
        :type timeout: int
        :return: A list of socket file descriptor ready to read
        :rtype: list
        """
        # some os are not managing void socks list, so catch this
        # and just so a simple sleep instead
        if socks == []:
            time.sleep(timeout)
            return []
        try:
            ins, _, _ = select.select(socks, [], [], timeout)
        except select.error, err:
            errnum, _ = err
            if errnum == errno.EINTR:
                return []
            raise
        return ins

    def check_and_del_zombie_modules(self):
        """Check alive instance and try to restart the dead ones

        :return: None
        """
        # Active children make a join with every one, useful :)
        self.modules_manager.check_alive_instances()
        # and try to restart previous dead :)
        self.modules_manager.try_to_restart_deads()

    def find_uid_from_name(self):
        """Wrapper for getpwnam : get the uid of user attribute

        :return: Uid of user attribute
        :rtype: str | None
        """
        try:
            return getpwnam(self.user)[2]
        except KeyError:
            logger.error("The user %s is unknown", self.user)
            return None

    def find_gid_from_name(self):
        """Wrapper for getgrnam : get the uid of user attribute

        :return: Uid of user attribute
        :rtype: str | None
        """
        try:
            return getgrnam(self.group)[2]
        except KeyError:
            logger.error("The group %s is unknown", self.group)
            return None

    def change_to_user_group(self, insane=None):
        """ Change to user of the running program.
        If change failed we sys.exit(2)

        :param insane: boolean to allow running as root
        :type insane: bool
        :return: None
        """
        if insane is None:
            insane = not self.idontcareaboutsecurity

        # TODO: change user on nt
        if os.name == 'nt':
            logger.warning("You can't change user on this system")
            return

        if (self.user == 'root' or self.group == 'root') and not insane:
            logger.error("You want the application run under the root account?")
            logger.error("I do not agree with it. If you really want it, put:")
            logger.error("idontcareaboutsecurity=yes")
            logger.error("in the config file")
            logger.error("Exiting")
            sys.exit(2)

        uid = self.find_uid_from_name()
        gid = self.find_gid_from_name()

        if uid is None or gid is None:
            logger.error("uid or gid is none. Exiting")
            sys.exit(2)

        # Maybe the os module got the initgroups function. If so, try to call it.
        # Do this when we are still root
        if hasattr(os, 'initgroups'):
            logger.info('Trying to initialize additional groups for the daemon')
            try:
                os.initgroups(self.user, gid)
            except OSError, err:
                logger.warning('Cannot call the additional groups setting with initgroups (%s)',
                               err.strerror)
        elif hasattr(os, 'setgroups'):
            # Else try to call the setgroups if it exists...
            groups = [gid] + \
                     [group.gr_gid for group in get_all_groups() if self.user in group.gr_mem]
            try:
                os.setgroups(groups)
            except OSError, err:
                logger.warning('Cannot call the additional groups setting with setgroups (%s)',
                               err.strerror)
        try:
            # First group, then user :)
            os.setregid(gid, gid)
            os.setreuid(uid, uid)
        except OSError, err:
            logger.error("cannot change user/group to %s/%s (%s [%d]). Exiting",
                         self.user, self.group, err.strerror, err.errno)
            sys.exit(2)

    def load_config_file(self):
        """ Parse daemon configuration file

        Parse self.config_file and get all its variables.
        If some properties need a pythonization, do it.
        Use default values for the properties if some are missing in the config_file
        Ensure full path in variables

        :return: None
        """
        # Note: do not use logger into this function because it is not yet initialized ;)
        print("Loading daemon configuration file (%s)..." % self.config_file)

        properties = self.__class__.properties
        if self.config_file is not None:
            config = ConfigParser.ConfigParser()
            config.read(self.config_file)
            if config._sections == {}:
                logger.error("Bad or missing config file: %s ", self.config_file)
                sys.exit(2)
            try:
                for (key, value) in config.items('daemon'):
                    if key in properties:
                        value = properties[key].pythonize(value)
                    setattr(self, key, value)
            except ConfigParser.InterpolationMissingOptionError as err:
                err = str(err)
                wrong_variable = err.split('\n')[3].split(':')[1].strip()
                logger.error("Incorrect or missing variable '%s' in config file : %s",
                             wrong_variable, self.config_file)
                sys.exit(2)

            # Some paths can be relative. We must have a full path having for reference the
            # configuration file
            self.relative_paths_to_full(os.path.dirname(self.config_file))
        else:
            print("No daemon configuration file specified, using defaults parameters")

        # Now fill all defaults where missing parameters
        for prop, entry in properties.items():
            if not hasattr(self, prop):
                value = entry.pythonize(entry.default)
                setattr(self, prop, value)

    def relative_paths_to_full(self, reference_path):
        """Set a full path from a relative one with the config file as reference
        TODO: This should be done in pythonize method of Properties.
        TODO: @mohierf: why not doing this directly in load_config_file?
        TODO: No property defined for the daemons is a ConfigPathProp ... ;)
        This function is completely unuseful as is !!!

        :param reference_path: reference path for reading full path
        :type reference_path: str
        :return: None
        """
        properties = self.__class__.properties
        for prop, entry in properties.items():
            if isinstance(entry, ConfigPathProp):
                path = getattr(self, prop)
                if not os.path.isabs(path):
                    new_path = os.path.join(reference_path, path)
                    path = new_path
                setattr(self, prop, path)

    def manage_signal(self, sig, frame):  # pylint: disable=W0613
        """Manage signals caught by the daemon
        signal.SIGUSR1 : dump_memory
        signal.SIGUSR2 : dump_object (nothing)
        signal.SIGTERM, signal.SIGINT : terminate process

        :param sig: signal caught by daemon
        :type sig: str
        :param frame: current stack frame
        :type frame:
        :return: None
        """
        logger.info("process %d received a signal: %s", os.getpid(), str(sig))
        if sig == signal.SIGUSR1:  # if USR1, ask a memory dump
            self.need_dump_memory = True
        elif sig == signal.SIGUSR2:  # if USR2, ask objects dump
            self.need_objects_dump = True
        elif sig == signal.SIGHUP:  # if HUP, reload configuration in arbiter
            self.need_config_reload = True
        else:  # Ok, really ask us to die :)
            self.interrupted = True

    def set_exit_handler(self):
        """Set the signal handler to manage_signal (defined in this class)
        Only set handlers for signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGUSR2

        :return: None
        """
        func = self.manage_signal
        if os.name == "nt":
            try:
                import win32api
                win32api.SetConsoleCtrlHandler(func, True)
            except ImportError:
                version = ".".join([str(i) for i in sys.version_info[:2]])
                raise Exception("pywin32 not installed for Python " + version)
        else:
            for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1,
                        signal.SIGUSR2, signal.SIGHUP):
                signal.signal(sig, func)

    # pylint: disable=no-member
    def set_proctitle(self, daemon_name=None):
        """Set the proctitle of the daemon

        :param daemon_name: daemon instance name (eg. arbiter-master). If not provided, only the
        daemon name (eg. arbiter) will be used for the process title
        :type daemon_name: str
        :return: None
        """
        if daemon_name:
            setproctitle("alignak-%s %s" % (self.daemon_type, daemon_name))
            if hasattr(self, 'modules_manager'):
                self.modules_manager.set_daemon_name(daemon_name)
        else:
            setproctitle("alignak-%s" % self.daemon_type)

    def get_header(self):
        """ Get the log file header

        :return: A string list containing project name, daemon name, version, licence etc.
        :rtype: list
        """
        return ["-----",
                "Alignak %s - %s daemon" % (VERSION, self.name),
                "Copyright (c) 2015-2016: Alignak Team",
                "License: AGPL",
                "-----"]

    def http_daemon_thread(self):
        """Main function of the http daemon thread will loop forever unless we stop the root daemon

        :return: None
        """
        logger.info("HTTP main thread running")
        # The main thing is to have a pool of X concurrent requests for the http_daemon,
        # so "no_lock" calls can always be directly answer without having a "locked" version to
        # finish
        try:
            self.http_daemon.run()
        except PortNotFree as exp:
            print("Exception: %s" % str(exp))
            logger.exception('The HTTP daemon port is not free: %s', exp)
            raise exp
        except Exception as exp:  # pylint: disable=W0703
            logger.exception('The HTTP daemon failed with the error %s, exiting', str(exp))
            raise exp
        logger.info("HTTP main thread exiting")

    def handle_requests(self, timeout, suppl_socks=None):
        """ Wait up to timeout to handle the requests.
        If suppl_socks is given it also looks for activity on that list of fd.

        :param timeout: timeout to wait for activity
        :type timeout: float
        :param suppl_socks: list of fd to wait for activity
        :type suppl_socks: None | list
        :return:Returns a 3-tuple:
        * If timeout: first arg is 0, second is [], third is possible system time change value
        *  If not timeout (== some fd got activity):
            - first arg is elapsed time since wait,
            - second arg is sublist of suppl_socks that got activity.
            - third arg is possible system time change value, or 0 if no change
        :rtype: tuple
        """
        if suppl_socks is None:
            suppl_socks = []
        before = time.time()
        socks = []
        if suppl_socks:
            socks.extend(suppl_socks)

        # Ok give me the socks that moved during the timeout max
        ins = self.get_socks_activity(socks, timeout)
        # Ok now get back the global lock!
        tcdiff = self.check_for_system_time_change()
        before += tcdiff
        # Increase our sleep time for the time go in select
        self.sleep_time += time.time() - before
        if len(ins) == 0:  # trivial case: no fd activity:
            return 0, [], tcdiff
        # HERE WAS THE HTTP, but now it's managed in an other thread
        # for sock in socks:
        #    if sock in ins and sock not in suppl_socks:
        #        ins.remove(sock)
        # Track in elapsed the WHOLE time, even with handling requests
        elapsed = time.time() - before
        if elapsed == 0:  # we have done a few instructions in 0 second exactly!? quantum computer?
            elapsed = 0.01  # but we absolutely need to return!= 0 to indicate that we got activity
        return elapsed, ins, tcdiff

    def check_for_system_time_change(self):
        """
        Check if our system time change. If so, change our

        :return: 0 if the difference < 900, difference else
        :rtype: int
        TODO: Duplicate of alignak.worker.Worker.check_for_system_time_change
        """
        now = time.time()
        difference = now - self.t_each_loop

        # If we have more than 15 min time change, we need to compensate it
        if abs(difference) > 900:
            if hasattr(self, "sched"):
                self.compensate_system_time_change(difference,
                                                   self.sched.timeperiods)  # pylint: disable=E1101
            else:
                self.compensate_system_time_change(difference, None)
        else:
            difference = 0

        self.t_each_loop = now

        return difference

    def compensate_system_time_change(self, difference, timeperiods):  # pylint: disable=R0201,W0613
        """Default action for system time change. Actually a log is done

        :return: None
        """

        logger.warning('A system time change of %s has been detected.  Compensating...', difference)

    def wait_for_initial_conf(self, timeout=1.0):
        """Wait conf from arbiter.
        Basically sleep 1.0 and check if new_conf is here

        :param timeout: timeout to wait from socket read
        :type timeout: int
        :return: None
        TODO: Clean this
        """
        logger.info("Waiting for initial configuration")
        # Arbiter do not already set our have_conf param
        while not self.new_conf and not self.interrupted:
            # This is basically sleep(timeout) and returns 0, [], int
            # We could only paste here only the code "used" but it could be
            # harder to maintain.
            _ = self.handle_requests(timeout)
            sys.stdout.write(".")
            sys.stdout.flush()

    def hook_point(self, hook_name):
        """Used to call module function that may define a hook function
        for hook_name

        :param hook_name: function name we may hook in module
        :type hook_name: str
        :return: None
        """
        _t0 = time.time()
        for inst in self.modules_manager.instances:
            full_hook_name = 'hook_' + hook_name
            if hasattr(inst, full_hook_name):
                fun = getattr(inst, full_hook_name)
                try:
                    fun(self)
                except Exception as exp:  # pylint: disable=W0703
                    logger.warning('The instance %s raised an exception %s. I disabled it,'
                                   'and set it to restart later', inst.get_name(), str(exp))
                    logger.exception('Exception %s', exp)
                    self.modules_manager.set_to_restart(inst)
        statsmgr.timer('core.hook.%s' % hook_name, time.time() - _t0)

    def get_retention_data(self):  # pylint: disable=R0201
        """Basic function to get retention data,
        Maybe be overridden by subclasses to implement real get

        :return: A list of Alignak object (scheduling items)
        :rtype: list
        """
        return []

    # Save, to get back all data
    def restore_retention_data(self, data):
        """Basic function to save retention data,
        Maybe be overridden by subclasses to implement real save

        :return: None
        """
        pass

    def get_stats_struct(self):
        """Get state of modules and create a scheme for stats data of daemon
        This may be overridden in subclasses

        :return: A dict with the following structure
        ::
            {
                'metrics': [],
                'version': VERSION,
                'name': '',
                'type': '',
                'modules': {
                    'internal': {'name': "MYMODULE1", 'state': 'ok'},
                    'external': {'name': "MYMODULE2", 'state': 'stopped'},
                }
            }

        :rtype: dict

        """
        res = {
            'metrics': [], 'version': VERSION, 'name': self.name, 'type': self.daemon_type,
            'modules': {
                'internal': {}, 'external': {}
            }
        }
        modules = res['modules']

        # first get data for all internal modules
        for mod in self.modules_manager.get_internal_instances():
            mname = mod.get_name()
            state = {True: 'ok', False: 'stopped'}[(mod not in self.modules_manager.to_restart)]
            env = {'name': mname, 'state': state}
            modules['internal'][mname] = env
        # Same but for external ones
        for mod in self.modules_manager.get_external_instances():
            mname = mod.get_name()
            state = {True: 'ok', False: 'stopped'}[(mod not in self.modules_manager.to_restart)]
            env = {'name': mname, 'state': state}
            modules['external'][mname] = env

        return res

    @staticmethod
    def print_unrecoverable(trace):
        """Log generic message when getting an unrecoverable error

        :param trace: stack trace of the Exception
        :type trace:
        :return: None
        """
        logger.critical("I got an unrecoverable error. I have to exit.")
        logger.critical("You can get help at https://github.com/Alignak-monitoring/alignak")
        logger.critical("If you think this is a bug, create a new issue including as much "
                        "details as possible (version, configuration, ...")
        logger.critical("-----")
        logger.critical("Back trace of the error: %s", trace)

    def get_objects_from_from_queues(self):
        """ Get objects from "from" queues and add them.

        :return: True if we got some objects, False otherwise.
        :rtype: bool
        """
        had_some_objects = False
        for queue in self.modules_manager.get_external_from_queues():
            if queue is not None:
                while True:
                    try:
                        obj = queue.get(block=False)
                    except (Empty, IOError, EOFError) as err:
                        if not isinstance(err, Empty):
                            logger.error("An external module queue got a problem '%s'", str(exp))
                        break
                    else:
                        had_some_objects = True
                        self.add(obj)
        return had_some_objects

    def setup_alignak_logger(self, reload_configuration=True):
        """ Setup alignak logger:
        - load the daemon configuration file
        - configure the global daemon handler (root logger)
        - log the daemon Alignak header
        - log the damon configuration parameters

        :param reload_configuration: Load configuration file if True,
        else it uses current parameters
        :type: bool
        :return: None
        """
        if reload_configuration:
            # Load the daemon configuration file
            self.load_config_file()

        # Force the debug level if the daemon is said to start with such level
        log_level = self.log_level
        if self.debug:
            log_level = 'DEBUG'

        # Set the human timestamp log if required
        human_log_format = getattr(self, 'human_timestamp_log', False)

        # Register local log file if required
        if getattr(self, 'use_local_log', False):
            try:
                # pylint: disable=E1101
                setup_logger(None, level=log_level, human_log=human_log_format,
                             log_console=True, log_file=self.local_log,
                             when=self.log_rotation_when, interval=self.log_rotation_interval,
                             backup_count=self.log_rotation_count,
                             human_date_format=self.human_date_format)
            except IOError, exp:
                logger.error("Opening the log file '%s' failed with '%s'", self.local_log, exp)
                sys.exit(2)
            logger.debug("Using the local log file '%s'", self.local_log)
            self.local_log_fds = get_logger_fds(None)
        else:
            setup_logger(None, level=log_level, human_log=human_log_format,
                         log_console=True, log_file=None)
            logger.warning("No local log file")

        logger.debug("Alignak daemon logger configured")

        # Log daemon header
        for line in self.get_header():
            logger.info(line)

        logger.info("My configuration: ")
        for prop, _ in self.properties.items():
            logger.info(" - %s=%s", prop, getattr(self, prop, 'Not found!'))
