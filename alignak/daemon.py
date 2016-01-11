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
from __future__ import print_function
import os
import errno
import sys
import time
import signal
import select
import ConfigParser
import threading
from Queue import Empty
from multiprocessing.managers import SyncManager


from alignak.http.daemon import HTTPDaemon, InvalidWorkDir
from alignak.log import logger
from alignak.stats import statsmgr
from alignak.modulesmanager import ModulesManager
from alignak.property import StringProp, BoolProp, PathProp, ConfigPathProp, IntegerProp, \
    LogLevelProp
from alignak.misc.common import setproctitle


try:
    import pwd
    import grp
    from pwd import getpwnam
    from grp import getgrnam, getgrall

    def get_cur_user():
        """Wrapper for getpwuid

        :return: user name
        :rtype: str
        """
        return pwd.getpwuid(os.getuid()).pw_name

    def get_cur_group():
        """Wrapper for getgrgid

        :return: group name
        :rtype: str
        """
        return grp.getgrgid(os.getgid()).gr_name

    def get_all_groups():
        """Wrapper for getgrall

        :return: all groups
        :rtype: list
        """
        return getgrall()
except ImportError, exp:  # Like in nt system
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


IS_PY26 = sys.version_info[:2] < (2, 7)

# #########################   DAEMON PART    ###############################
# The standard I/O file descriptors are redirected to /dev/null by default.
REDIRECT_TO = getattr(os, "devnull", "/dev/null")

UMASK = 027
from alignak.version import VERSION


class InvalidPidFile(Exception):
    """Exception raise when a pid file is invalid"""
    pass


DEFAULT_WORK_DIR = '/var/run/alignak/'
DEFAULT_LIB_DIR = '/var/lib/alignak/'


class Daemon(object):
    """Class providing daemon level call for Alignak
        TODO: Consider clean this code and use standard libs
    """

    properties = {
        # workdir is relative to $(dirname "$0"/..)
        # where "$0" is the path of the file being executed,
        # in python normally known as:
        #
        #  os.path.join( os.getcwd(), sys.argv[0] )
        #
        # as returned once the daemon is started.
        'workdir':       PathProp(default=DEFAULT_WORK_DIR),
        'host':          StringProp(default='0.0.0.0'),
        'user':          StringProp(default=get_cur_user()),
        'group':         StringProp(default=get_cur_group()),
        'use_ssl':       BoolProp(default=False),
        'server_key':     StringProp(default='etc/certs/server.key'),
        'ca_cert':       StringProp(default='etc/certs/ca.pem'),
        'server_cert':   StringProp(default='etc/certs/server.cert'),
        'use_local_log': BoolProp(default=True),
        'log_level':     LogLevelProp(default='WARNING'),
        'hard_ssl_name_check':    BoolProp(default=False),
        'idontcareaboutsecurity': BoolProp(default=False),
        'daemon_enabled': BoolProp(default=True),
        'spare':         BoolProp(default=False),
        'max_queue_size': IntegerProp(default=0),
        'daemon_thread_pool_size': IntegerProp(default=8),
    }

    def __init__(self, name, config_file, is_daemon, do_replace, debug, debug_file):

        self.check_shm()

        self.name = name
        self.config_file = config_file
        self.is_daemon = is_daemon
        self.do_replace = do_replace
        self.debug = debug
        self.debug_file = debug_file
        self.interrupted = False
        self.pidfile = None

        # Track time
        now = time.time()
        self.program_start = now
        self.t_each_loop = now  # used to track system time change
        self.sleep_time = 0.0  # used to track the time we wait

        self.http_thread = None
        self.http_daemon = None

        # Log init
        # self.log = logger
        # self.log.load_obj(self)
        # pylint: disable=E1101
        logger.load_obj(self)

        self.new_conf = None  # used by controller to push conf
        self.cur_conf = None
        self.conf_lock = threading.RLock()
        self.lock = threading.RLock()

        # Flag to know if we need to dump memory or not
        self.need_dump_memory = False

        # Flag to dump objects or not
        self.need_objects_dump = False

        # Flag to reload configuration
        self.need_config_reload = False

        # Keep a trace of the local_log file desc if needed
        self.local_log_fd = None

        # Put in queue some debug output we will raise
        # when we will be in daemon
        self.debug_output = []

        # We will initialize the Manager() when we load modules
        # and be really forked()
        self.manager = None

        os.umask(UMASK)
        self.set_exit_handler()

    # At least, lose the local log file if needed
    def do_stop(self):
        """Execute the stop of this daemon:
         - Stop the http thread and join it
         - Close the http socket
         - Shutdown the manager
         - Stop and join all started "modules"

        :return: None
        """
        logger.info("%s : Doing stop ..", self)

        if self.http_daemon:
            logger.info("Shutting down http_daemon ..")
            self.http_daemon.request_stop()

        if self.http_thread:
            logger.info("Joining http_thread ..")
            # Add a timeout to join so that we can manually quit
            self.http_thread.join(timeout=15)
            if self.http_thread.is_alive():
                logger.warning("http_thread failed to terminate. Calling _Thread__stop")
                try:
                    self.http_thread._Thread__stop()
                except Exception:
                    pass
            self.http_thread = None

        if self.http_daemon:
            self.http_daemon = None

        if self.manager:
            logger.info("Shutting down manager ..")
            self.manager.shutdown()
            self.manager = None

        # Maybe the modules manager is not even created!
        if getattr(self, 'modules_manager', None):
            # We save what we can but NOT for the scheduler
            # because the current sched object is a dummy one
            # and the old one has already done it!
            if not hasattr(self, 'sched'):
                self.hook_point('save_retention')
            # And we quit
            logger.info('Stopping all modules')
            self.modules_manager.stop_all()

        logger.info("%s : All stop done.", self)

    def request_stop(self):
        """Remove pid and stop daemon

        :return: None
        """
        self.unlink()
        self.do_stop()
        # Brok facilities are no longer available simply print the message to STDOUT
        print("Stopping daemon. Exiting")
        sys.exit(0)

    def look_for_early_exit(self):
        """Stop the daemon if it is not enabled

        :return: None
        """
        if not self.daemon_enabled:
            logger.info('This daemon is disabled in configuration. Bailing out')
            self.request_stop()

    def do_loop_turn(self):
        """Abstract method for deamon loop turn.
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
                self.dump_memory()
                self.need_dump_memory = False
            if self.need_objects_dump:
                logger.debug('Dumping objects')
                self.need_objects_dump = False
            if self.need_config_reload:
                logger.debug('Reloading configuration')
                self.need_config_reload = False
            # Maybe we ask us to die, if so, do it :)
            if self.interrupted:
                break
        self.request_stop()

    def do_load_modules(self, mod_confs):
        """Wrapper for calling load_and_init method of modules_manager attribute

        :return: None
        """
        self.modules_manager.load_and_init(mod_confs)
        logger.info("I correctly loaded the modules: [%s]",
                    ','.join([inst.get_name() for inst in self.modules_manager.instances]))

    def add(self, elt):
        """ Abstract method for adding brok
         It is overridden in subclasses of Daemon

        :param elt: element to add
        :type elt:
        :return: None
        """
        pass

    def dump_memory(self):
        """Try to dump memory
        Does not really work :/

        :return: None
        TODO: Clean this
        """
        logger.info("I dump my memory, it can take a minute")
        try:
            from guppy import hpy
            heap = hpy()
            logger.info(heap.heap())
        except ImportError:
            logger.warning('I do not have the module guppy for memory dump, please install it')

    def load_config_file(self):
        """Parse config file and ensure full path in variables

        :return: None
        """
        self.parse_config_file()
        if self.config_file is not None:
            # Some paths can be relatives. We must have a full path by taking
            # the config file by reference
            self.relative_paths_to_full(os.path.dirname(self.config_file))

    def load_modules_manager(self):
        """Instanciate Modulesmanager and load the SyncManager (multiprocessing)

        :return: None
        """
        self.modules_manager = ModulesManager(self.name, self.manager,
                                              max_queue_size=getattr(self, 'max_queue_size', 0))

    def change_to_workdir(self):
        """Change working directory to working attribute

        :return: None
        """
        self.workdir = os.path.abspath(self.workdir)
        try:
            os.chdir(self.workdir)
        except Exception, exp:
            raise InvalidWorkDir(exp)
        self.debug_output.append("Successfully changed to workdir: %s" % (self.workdir))

    def unlink(self):
        """Remove the daemon's pid file

        :return: None
        """
        logger.debug("Unlinking %s", self.pidfile)
        try:
            os.unlink(self.pidfile)
        except Exception, exp:
            logger.error("Got an error unlinking our pidfile: %s", exp)

    def register_local_log(self):
        """Open local log file for logging purpose

        :return: None
        """
        # The arbiter doesn't have such attribute
        if hasattr(self, 'use_local_log') and self.use_local_log:
            try:
                # self.local_log_fd = self.log.register_local_log(self.local_log)
                self.local_log_fd = logger.register_local_log(self.local_log)
            except IOError, exp:
                logger.error("Opening the log file '%s' failed with '%s'", self.local_log, exp)
                sys.exit(2)
            logger.info("Using the local log file '%s'", self.local_log)

    def check_shm(self):
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
        if os.name == 'nt':
            logger.warning("The parallel daemon check is not available on nt")
            self.__open_pidfile(write=True)
            return

        # First open the pid file in open mode
        self.__open_pidfile()
        try:
            pid = int(self.fpid.readline().strip(' \r\n'))
        except Exception as err:
            logger.info("Stale pidfile exists at %s (%s). Reusing it.", err, self.pidfile)
            return

        try:
            os.kill(pid, 0)
        except Exception as err:  # consider any exception as a stale pidfile.
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

    def close_fds(self, skip_close_fds):
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
                continue
            try:
                os.close(file_d)
            except OSError:  # ERROR, fd wasn't open to begin with (ignored)
                pass

    def daemonize(self, skip_close_fds=None):
        """Go in "daemon" mode: close unused fds, redirect stdout/err,
        chdir, umask, fork-setsid-fork-writepid
        Do the double fork to properly go daemon

        :param skip_close_fds: list of fd to keep open
        :type skip_close_fds: list
        :return: None
        """
        if skip_close_fds is None:
            skip_close_fds = tuple()

        self.debug_output.append("Redirecting stdout and stderr as necessary..")
        if self.debug:
            fdtemp = os.open(self.debug_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
        else:
            fdtemp = os.open(REDIRECT_TO, os.O_RDWR)

        # We close all fd but what we need:
        self.close_fds(skip_close_fds + (self.fpid.fileno(), fdtemp))

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
            def do_exit(sig, frame):
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
        self.set_proctitle()

    # The Manager is a sub-process, so we must be sure it won't have
    # a socket of your http server alive
    @staticmethod
    def _create_manager():
        """Instanciate and start a SyncManager

        :return: the manager
        :rtype: multiprocessing.managers.SyncManager
        """
        manager = SyncManager(('127.0.0.1', 0))
        manager.start()
        return manager

    def do_daemon_init_and_start(self, fake=False):
        """Main daemon function.
        Clean, allocates, initializes and starts all necessary resources to go in daemon mode.

        :param fake: use for test to do not launch runonly feature, like the stats reaper thread.
        :type fake: bool
        :return: None
        """
        self.change_to_user_group()
        self.change_to_workdir()
        self.check_parallel_run()
        self.setup_communication_daemon()

        # Setting log level
        logger.setLevel(self.log_level)
        # Force the debug level if the daemon is said to start with such level
        if self.debug:
            logger.setLevel('DEBUG')

        # Then start to log all in the local file if asked so
        self.register_local_log()
        if self.is_daemon:
            # Do not close the local_log file too if it's open
            if self.local_log_fd:
                self.daemonize(skip_close_fds=(self.local_log_fd,))
        else:
            self.write_pid()

        logger.info("Creating manager ..")
        self.manager = self._create_manager()
        logger.info("done.")

        # We can start our stats thread but after the double fork() call and if we are not in
        # a test launch (time.time() is hooked and will do BIG problems there)
        if not fake:
            statsmgr.launch_reaper_thread()

        logger.info("Now starting http_daemon thread..")
        self.http_thread = threading.Thread(None, self.http_daemon_thread, 'http_thread')
        self.http_thread.daemon = True
        self.http_thread.start()

    def setup_communication_daemon(self):
        """ Setup HTTP server daemon to listen
        for incoming HTTP requests from other Alignak daemons

        :return: None
        """
        if hasattr(self, 'use_ssl'):  # "common" daemon
            ssl_conf = self
        else:
            ssl_conf = self.conf     # arbiter daemon..

        use_ssl = ssl_conf.use_ssl
        ca_cert = ssl_cert = ssl_key = ''

        # The SSL part
        if use_ssl:
            ssl_cert = os.path.abspath(str(ssl_conf.server_cert))
            if not os.path.exists(ssl_cert):
                logger.error('Error : the SSL certificate %s is missing (server_cert).'
                             'Please fix it in your configuration', ssl_cert)
                sys.exit(2)
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
        self.http_daemon = HTTPDaemon(self.host, self.port, self.http_interface,
                                      use_ssl, ca_cert, ssl_key,
                                      ssl_cert, self.daemon_thread_pool_size)

    def get_socks_activity(self, socks, timeout):
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
        except KeyError, exp:
            logger.error("The user %s is unknown", self.user)
            return None

    def find_gid_from_name(self):
        """Wrapper for getgrnam : get the uid of user attribute

        :return: Uid of user attribute
        :rtype: str | None
        """
        try:
            return getgrnam(self.group)[2]
        except KeyError, exp:
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

    def parse_config_file(self):
        """Parse self.config_file and get all properties in it.
        If some properties need a pythonization, we do it.
        Also put default value in the properties if some are missing in the config_file

        :return: None
        """
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
            except ConfigParser.InterpolationMissingOptionError, err:
                err = str(err)
                wrong_variable = err.split('\n')[3].split(':')[1].strip()
                logger.error("Incorrect or missing variable '%s' in config file : %s",
                             wrong_variable, self.config_file)
                sys.exit(2)
        else:
            logger.warning("No config file specified, use defaults parameters")
        # Now fill all defaults where missing parameters
        for prop, entry in properties.items():
            if not hasattr(self, prop):
                value = entry.pythonize(entry.default)
                setattr(self, prop, value)

    def relative_paths_to_full(self, reference_path):
        """Set a full path from a relative one with che config file as reference
        TODO: This should be done in pythonize method of Properties.

        :param reference_path: reference path for reading full path
        :type reference_path: str
        :return: None
        """
        # print "Create relative paths with", reference_path
        properties = self.__class__.properties
        for prop, entry in properties.items():
            if isinstance(entry, ConfigPathProp):
                path = getattr(self, prop)
                if not os.path.isabs(path):
                    new_path = os.path.join(reference_path, path)
                    # print "DBG: changing", entry, "from", path, "to", new_path
                    path = new_path
                setattr(self, prop, path)
                # print "Setting %s for %s" % (path, prop)

    def manage_signal(self, sig, frame):
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
        logger.debug("I'm process %d and I received signal %s", os.getpid(), str(sig))
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

    def set_proctitle(self):
        """Set the proctitle of the daemon

        :return: None
        """
        setproctitle("alignak-%s" % self.name)

    def get_header(self):
        """Get the log file header

        :return: A string list containing project name, version, licence etc.
        :rtype: list
        """
        return ["Alignak %s" % VERSION,
                "Copyright (c) 2015-2015:",
                "Alignak Team",
                "License: AGPL"]

    def print_header(self):
        """Log headers generated in get_header()

        :return: None
        """
        for line in self.get_header():
            logger.info(line)

    def http_daemon_thread(self):
        """Main fonction of the http daemon thread will loop forever unless we stop the root daemon

        :return: None
        """
        logger.info("HTTP main thread: I'm running")
        # The main thing is to have a pool of X concurrent requests for the http_daemon,
        # so "no_lock" calls can always be directly answer without having a "locked" version to
        # finish
        try:
            self.http_daemon.run()
        except Exception, exp:
            logger.exception('The HTTP daemon failed with the error %s, exiting', str(exp))
            raise exp

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

        # Ok give me the socks taht moved during the timeout max
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
            self.compensate_system_time_change(difference)
        else:
            difference = 0

        self.t_each_loop = now

        return difference

    def compensate_system_time_change(self, difference):
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
        """Used to call module function that may define a hook fonction
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
                except Exception as exp:
                    logger.warning('The instance %s raised an exception %s. I disabled it,'
                                   'and set it to restart later', inst.get_name(), str(exp))
                    self.modules_manager.set_to_restart(inst)
        statsmgr.incr('core.hook.%s' % hook_name, time.time() - _t0)

    def get_retention_data(self):
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

           { 'metrics': [],
             'version': VERSION,
             'name': '',
             'modules':
                         {'internal': {'name': "MYMODULE1", 'state': 'ok'},
                         {'external': {'name': "MYMODULE2", 'state': 'stopped'},
                        ]
           }

        :rtype: dict

        """
        res = {'metrics': [], 'version': VERSION, 'name': '', 'type': '', 'modules':
               {'internal': {}, 'external': {}}}
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
        logger.critical("If you think this is a bug, create a new ticket including"
                        "details mentioned in the README")
        logger.critical("Back trace of the error: %s", trace)

    def get_objects_from_from_queues(self):
        """ Get objects from "from" queues and add them.

        :return: True if we got some objects, False otherwise.
        :rtype: bool
        """
        had_some_objects = False
        for queue in self.modules_manager.get_external_from_queues():
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
