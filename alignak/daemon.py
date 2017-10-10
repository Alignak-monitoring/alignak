# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines
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
# pylint: disable=too-many-public-methods, unused-import
from __future__ import print_function
import os
import errno
import sys
import time
import signal
from copy import copy
import select
import ConfigParser
import threading
import logging
import warnings
import traceback
from Queue import Empty, Full
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
except ImportError as exp:  # pragma: no cover, not for unit tests...
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
from alignak.http.daemon import HTTPDaemon, PortNotFree
from alignak.stats import statsmgr
from alignak.modulesmanager import ModulesManager
from alignak.property import StringProp, BoolProp, PathProp, ConfigPathProp, IntegerProp, \
    LogLevelProp, ListProp
from alignak.misc.common import setproctitle
from alignak.version import VERSION

from alignak.bin.alignak_environment import AlignakConfigParser

if 'ALIGNAK_DAEMONS_MONITORING' in os.environ:
    import psutil


# Friendly names for the system signals
SIGNALS_TO_NAMES_DICT = dict((k, v) for v, k in reversed(sorted(signal.__dict__.items()))
                             if v.startswith('SIG') and not v.startswith('SIG_'))

logger = logging.getLogger(__name__)  # pylint: disable=C0103

# #########################   DAEMON PART    ###############################
# The standard I/O file descriptors are redirected to /dev/null by default.
REDIRECT_TO = getattr(os, "devnull", "/dev/null")

UMASK = 027


class EnvironmentFile(Exception):
    """Exception raised when the Alignak environment file is missing or corrupted"""

    def __init__(self, msg=None):
        if not msg:
            msg = "Alignak environment file is missing or corrupted"
        Exception.__init__(self, msg)


class InvalidWorkingDir(Exception):
    """Exception raised when daemon working directory is invalid"""

    def __init__(self, msg=None):
        if not msg:
            msg = "Invalid working directory"
        Exception.__init__(self, msg)


class InvalidPidFile(Exception):
    """Exception raised when a pid file is invalid"""

    def __init__(self, msg=None):
        if not msg:
            msg = "Invalid PID file"
        Exception.__init__(self, msg)

# This default value is used to declare the properties that are Path properties
# During the daemon initialization, this value is replaced with the real daemon working directory
# and it will be overloaded with the value defined in the daemon configuration or launch parameters
DEFAULT_WORK_DIR = './'


# pylint: disable=R0902
class Daemon(object):
    """Class providing daemon level call for Alignak
        TODO: Consider clean this code and use standard libs
    """

    properties = {
        'type':
            StringProp(default='unknown'),
        'daemon':
            StringProp(default='unknown'),
        'name':
            StringProp(),
        'env_filename':
            StringProp(default=''),
        'use_log_file':
            BoolProp(default=True),
        'log_filename':
            StringProp(default=''),
        'pid_filename':
            StringProp(default=''),
        'etcdir':   # /usr/local/etc/alignak
            PathProp(default=DEFAULT_WORK_DIR),
        # 'rundir':   # /usr/local/var/run/alignak
        #     PathProp(default=DEFAULT_WORK_DIR),
        'workdir':  # /usr/local/var/run/alignak
            PathProp(default=DEFAULT_WORK_DIR),
        'vardir':   # /usr/local/var/lib/alignak
            PathProp(default=DEFAULT_WORK_DIR),
        'logdir':# /usr/local/var/log/alignak
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
        # 'pidfile':
        #     StringProp(default=''),
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
        'hard_ssl_name_check':
            BoolProp(default=False),
        'idontcareaboutsecurity':
            BoolProp(default=False),
        'do_replace':
            BoolProp(default=False),
        'is_daemon':
            BoolProp(default=False),
        'daemon_enabled':
            BoolProp(default=True),
        'spare':
            BoolProp(default=False),
        'max_queue_size':
            IntegerProp(default=0),
        'daemon_thread_pool_size':
            IntegerProp(default=8),
        'debug':
            BoolProp(default=False),
        'debug_file':
            StringProp(default=None),
        'debug_output':
            ListProp(default=[]),
        'monitoring_config_files':
            ListProp(default=[]),

        # Local statsd daemon for collecting daemon metrics
        'statsd_host':
            StringProp(default='localhost'),
        'statsd_port':
            IntegerProp(default=8125),
        'statsd_prefix':
            StringProp(default='alignak'),
        'statsd_enabled':
            BoolProp(default=False)
    }

    def __init__(self, name, **kwargs):
        # pylint: disable=too-many-branches, too-many-statements, no-member
        """Daemon initialization

        The daemon name exist in kwargs ['daemon_name'] which is the one
        provided on the command line. It is set by the 'ame' parameter which must be provided
        by the sub class.

        :param kwargs: list of key/value pairs from the daemon command line and configuration
        """
        self.alignak_env = None
        self.monitoring_config_files = None
        self.modules_manager = None

        # First, do we debug?
        self.debug = False
        if 'debug' in kwargs and kwargs['debug']:
            self.debug = kwargs['debug']
        # Used to track debug, info warnings that will be logged once the logger is effective
        self.pre_log = []

        # I got my name
        self.name = name

        # Check if /dev/shm exists and usable...
        self.check_shm()

        self.pre_log.append(("DEBUG",
                             "Daemon '%s' initial working directory: %s"
                             % (self.name, os.getcwd())))

        # I define my default properties
        # Same as the Item.fill_default()... but I am not in this object hierarchy!
        my_properties = self.__class__.properties
        for prop, entry in my_properties.items():
            if getattr(self, prop, None) is not None:
                #  Still initialized...
                continue
            # Set absolute paths for our paths
            if isinstance(my_properties[prop], PathProp):
                if entry.default == DEFAULT_WORK_DIR:
                    setattr(self, prop, os.getcwd())
                else:
                    setattr(self, prop, os.path.abspath(entry.pythonize(entry.default)))
            else:
                if hasattr(entry.default, '__iter__'):
                    setattr(self, prop, copy(entry.default))
                else:
                    setattr(self, prop, entry.pythonize(entry.default))

        # Self daemon monitoring (cpu, memory)
        self.daemon_monitoring = False
        self.daemon_monitoring_period = 10
        if 'ALIGNAK_DAEMONS_MONITORING' in os.environ:
            self.daemon_monitoring = True
            if os.environ['ALIGNAK_DAEMONS_MONITORING']:
                try:
                    self.daemon_monitoring_period = int(os.environ['ALIGNAK_DAEMONS_MONITORING'])
                except ValueError:
                    pass
        if self.daemon_monitoring:
            logger.info("Daemon '%s' self monitoring is enabled, reporting every %d loop count.",
                        self.name, self.daemon_monitoring_period)

        # I almost certainly got an Alignak environment file
        if 'env_file' not in kwargs:
            raise EnvironmentFile

        self.env_filename = kwargs['env_file']
        if self.env_filename != os.path.abspath(self.env_filename):
            self.env_filename = os.path.abspath(self.env_filename)
        print("Daemon '%s' is started with an environment file: %s"
              % (self.name, self.env_filename))
        self.pre_log.append(("DEBUG",
                             "Daemon '%s' is started with an environment file: %s"
                             % (self.name, self.env_filename)))

        # Read Alignak environment file
        args = {'<cfg_file>': self.env_filename, '--verbose': self.debug}
        configuration_dir = os.path.dirname(self.env_filename)
        try:
            self.alignak_env = AlignakConfigParser(args)
            self.alignak_env.parse()

            for prop, value in self.alignak_env.get_monitored_configuration().items():
                print(" found Alignak monitoring configuration parameter, %s = %s" % (prop, value))
                self.pre_log.append(("DEBUG",
                                     " found Alignak monitoring "
                                     "configuration parameter, %s = %s" % (prop, value)))
                print(prop, value)
                # Ignore empty value
                if not value:
                    continue

                # Make the path absolute
                if not os.path.isabs(value):
                    value = os.path.abspath(os.path.join(configuration_dir, value))
                self.monitoring_config_files.append(value)

            for prop, value in self.alignak_env.get_daemons(name=self.name).items():
                self.pre_log.append(("DEBUG",
                                     " found daemon parameter, %s = %s" % (prop, value)))
                if getattr(self, prop, None) is None:
                    # For an undeclared property, store the value as a string
                    setattr(self, prop, value)
                    self.pre_log.append(("DEBUG", " -> setting %s = %s" % (prop, value)))
                elif callable(getattr(self, prop)):
                    # For a declared property, that match a self function name
                    raise EnvironmentFile("Variable %s cannot be defined as a property because "
                                          "it exists a callable function with the same name!"
                                          % prop)
                else:
                    # For a declared property, cast the read value
                    current_prop = getattr(self, prop)
                    setattr(self, prop, my_properties[prop].pythonize(value))
                    self.pre_log.append(("DEBUG", " -> updating %s = %s to %s"
                                         % (prop, current_prop, getattr(self, prop))))

        except ValueError as exp:
            print("Daemon '%s' did not correctly read Alignak environment file: %s"
                  % (self.name, args['<cfg_file>']))
            print("Exception: %s\n%s" % (exp, traceback.format_exc()))
            raise EnvironmentFile("Exception: %s" % (exp))

        # And perhaps some other parameters from the initial command line
        if 'config_file' in kwargs and kwargs['config_file']:
            warnings.warn(
                "Using daemon configuration file is now deprecated. The daemon -c parameter "
                "should not be used anymore in favor the -e environment file parameter.",
                DeprecationWarning, stacklevel=2)
            raise EnvironmentFile("Using daemon configuration file is now deprecated. "
                                  "The daemon -c command line parameter should not be "
                                  "used anymore in favor the -e environment file parameter.")

        if 'daemon_enabled' in kwargs:
            self.daemon_enabled = BoolProp().pythonize(kwargs['daemon_enabled'])
        if 'is_daemon' in kwargs:
            self.is_daemon = BoolProp().pythonize(kwargs['is_daemon'])
        if 'do_replace' in kwargs:
            self.do_replace = BoolProp().pythonize(kwargs['do_replace'])
        if 'debug' in kwargs:
            self.debug = BoolProp().pythonize(kwargs['debug'])
        if 'debug_file' in kwargs and kwargs['debug_file']:
            self.debug_file = PathProp().pythonize(kwargs['debug_file'])

        if 'host' in kwargs and kwargs['host']:
            self.host = StringProp().pythonize(kwargs['host'])
        if 'port' in kwargs and kwargs['port']:
            try:
                self.port = int(kwargs['port'])
                print("Daemon '%s' is started with an overidden port number: %d"
                      % (self.name, self.port))
            except ValueError:
                pass

        if self.debug:
            print("Daemon '%s' is in debug mode" % self.name)

        if self.is_daemon:
            print("Daemon '%s' is in daemon mode" % self.name)

        # Make my paths properties be absolute paths
        for prop, entry in my_properties.items():
            # Set absolute paths for
            if isinstance(my_properties[prop], PathProp):
                setattr(self, prop, os.path.abspath(getattr(self, prop)))

        # Log file...
        self.log_filename = PathProp().pythonize("%s.log" % self.name)
        self.log_filename = os.path.abspath(os.path.join(self.logdir, self.log_filename))

        if 'log_filename' in kwargs and kwargs['log_filename']:
            self.log_filename = PathProp().pythonize(kwargs['log_filename'])
            # Make it an absolute path file in the log directory
            if self.log_filename != os.path.abspath(self.log_filename):
                if self.log_filename:
                    self.log_filename = os.path.abspath(os.path.join(self.logdir, self.log_filename))
                    print("Daemon '%s' is started with an overidden log file: %s"
                          % (self.name, self.log_filename))
                else:
                    self.use_log_file = False
                    print("Daemon '%s' will not log to a file: %s" % (self.name))

        dirname = os.path.dirname(self.log_filename)
        try:
            os.makedirs(dirname)
            print("Daemon '%s' log directory did not exist, I created: %s" % (self.name, dirname))
            self.pre_log.append(("WARNING",
                                 "Daemon '%s' log directory did not exist, I created: %s"
                                 % (self.name, dirname)))
        except OSError as exp:
            if exp.errno == errno.EEXIST and os.path.isdir(dirname):
                # Directory still exists...
                pass
            else:
                self.pre_log.append(("ERROR",
                                     "Daemon '%s' log directory did not exist, "
                                      "and I could not create: %s. Exception: %s" 
                                      % (self.name, dirname, exp)))
                raise EnvironmentFile("Daemon '%s' log directory did not exist, "
                                      "and I could not create: '%s'. Exception: %s"
                                      % (self.name, dirname, exp))

        # pid file is stored in the working directory
        self.pid = 0
        self.pid_filename = PathProp().pythonize("%s.pid" % self.name)
        self.pid_filename = os.path.abspath(os.path.join(self.workdir, self.pid_filename))
        if 'pid_filename' in kwargs and kwargs['pid_filename']:
            self.pid_filename = PathProp().pythonize(kwargs['pid_filename'])
            # Make it an absolute path file in the pid directory
            if self.pid_filename != os.path.abspath(self.pid_filename):
                self.pid_filename = os.path.abspath(os.path.join(self.workdir, self.pid_filename))
            print("Daemon '%s' is started with an overidden pid file: %s" 
                  % (self.name, self.pid_filename))

        dirname = os.path.dirname(self.pid_filename)
        try:
            os.makedirs(dirname)
            print("Daemon '%s' pid directory did not exist, I created: %s" % (self.name, dirname))
            self.pre_log.append(("WARNING",
                                 "Daemon '%s' pid directory did not exist, I created: %s"
                                 % (self.name, dirname)))
        except OSError as exp:
            if exp.errno == errno.EEXIST and os.path.isdir(dirname):
                # Directory still exists...
                pass
            else:
                self.pre_pid.append(("ERROR",
                                     "Daemon '%s' pid directory did not exist, "
                                      "and I could not create: %s. Exception: %s" 
                                      % (self.name, dirname, exp)))
                raise EnvironmentFile("Daemon '%s' pid directory did not exist, "
                                      "and I could not create: %s. Exception: %s" 
                                      % (self.name, dirname, exp))

        # Track time
        now = time.time()
        self.program_start = now
        self.t_each_loop = now  # used to track system time change
        self.sleep_time = 0.0  # used to track the time we wait

        self.interrupted = False

        self.http_thread = None
        self.http_daemon = None

        # Configuration dispatch
        self.new_conf = None
        self.cur_conf = None
        self.conf_lock = threading.RLock()
        # self.lock = threading.RLock()

        # Flag to know if we need to dump memory or not
        self.need_dump_memory = False

        # Flag to dump objects or not
        self.need_objects_dump = False

        # Flag to reload configuration
        self.need_config_reload = False

        # Track the file descriptors allocated by the logger
        self.local_log_fds = None

        # Log loop turns if environment variable is set
        self.log_loop = 'TEST_LOG_LOOP' in os.environ

        # Activity information log period (every activity_log_period loop, raise a log)
        self.activity_log_period = int(os.getenv('ALIGNAK_ACTIVITY_LOG', 600))

        # Put in queue some debug output we will raise
        # when we will be in daemon
        self.debug_output = []

        # We will initialize the Manager() when we load modules
        # and are really forked
        self.sync_manager = None

        os.umask(UMASK)
        self.set_signal_handler()

    def __repr__(self):
        return '<Daemon %r/%r, listening on %r:%r:%d />' % \
               (self.type, self.name, self.scheme, self.host, self.port)
    __str__ = __repr__

    @property
    def scheme(self):
        """Daemon interface scheme

        :return: http or https if the daemon uses SSL
        :rtype: str
        """
        _scheme = 'http'
        if self.use_ssl:
            _scheme = 'https'
        return _scheme

    # At least, lose the local log file if needed
    def do_stop(self):
        """Execute the stop of this daemon:
         - request the daemon to stop
         - request the http thread to stop, else force stop the thread
         - Close the http socket
         - Shutdown the manager
         - Stop and join all started "modules"

        :return: None
        """
        logger.info("Stopping %s...", self.name)

        if self.http_daemon:
            logger.info("Shutting down the HTTP daemon...")
            self.http_daemon.request_stop()

        if self.http_thread:
            logger.debug("Joining HTTP thread...")
            # Add a timeout to join so that we can manually quit
            self.http_thread.join(timeout=15)
            if self.http_thread.is_alive():  # pragma: no cover, should never happen...
                logger.warning("http_thread failed to terminate. Calling _Thread__stop")
                try:
                    self.http_thread._Thread__stop()  # pylint: disable=E1101
                except Exception:  # pylint: disable=W0703
                    pass
            self.http_thread = None

        if self.http_daemon:
            self.http_daemon = None

        if self.sync_manager:
            logger.info("Shutting down synchronization manager...")
            self.sync_manager.shutdown()
            self.sync_manager = None

        # Maybe the modules manager is not even created!
        if self.modules_manager:
            # todo: clean this!
            # We save what we can but NOT for the scheduler
            # because the current sched object is a dummy one
            # and the old one has already done it!
            # todo: I comment this code because it looks unuseful !
            # Only the scheduler needs retention module, the other daemons
            # do not store anything in retention. Retention is to be removed from other daemons!
            # if not hasattr(self, 'sched'):
            #     self.hook_point('save_retention')

            # And we quit
            logger.info('Shutting down modules...')
            self.modules_manager.stop_all()

    def request_stop(self):  # pragma: no cover, not used during test because of sys.exit !
        """Remove pid and stop daemon

        :return: None
        """
        _ts = time.time()
        self.unlink()
        self.do_stop()
        statsmgr.timer('stop-delay', time.time() - _ts)

        logger.info("Stopped %s.", self.name)
        sys.exit(0)

    def look_for_early_exit(self):
        """Stop the daemon if it is not enabled

        :return: None
        """
        if not self.daemon_enabled:
            logger.info('This daemon is disabled in Alignak configuration. Bailing out')
            self.request_stop()

    def do_loop_turn(self):
        """Abstract method for daemon loop turn.
        It must be overridden by all classes inheriting from Daemon

        :return: None
        """
        raise NotImplementedError()

    def do_mainloop(self):
        """Main loop for an Alignak daemon

        :return: None
        """
        # Increased on each loop turn
        self.loop_count = 0
        while True:
            # Increment loop count
            self.loop_count += 1
            if self.log_loop:
                logger.debug("[%s] --- %d", self.name, self.loop_count)
            _ts = time.time()
            self.do_loop_turn()

            # If someone asked us to dump memory, do it
            if self.need_dump_memory:
                logger.debug('Dumping memory')
                self.dump_memory()
                self.need_dump_memory = False
            if self.need_objects_dump:
                logger.debug('Dumping objects')
                self.need_objects_dump = False

            statsmgr.timer('loop-turn', time.time() - _ts)
            if self.log_loop:
                logger.debug("[%s] +++ %d", self.name, self.loop_count)

            # If someone asked us a configuration reloading
            if self.need_config_reload:
                logger.debug('Ask for configuration reloading')
                return

            if self.daemon_monitoring and (self.loop_count % self.daemon_monitoring_period == 1):
                perfdatas = []
                my_process = psutil.Process()
                with my_process.oneshot():
                    perfdatas.append("num_threads=%d" % my_process.num_threads())
                    statsmgr.counter("num_threads", my_process.num_threads())
                    # perfdatas.append("num_ctx_switches=%d" % my_process.num_ctx_switches())
                    perfdatas.append("num_fds=%d" % my_process.num_fds())
                    # perfdatas.append("num_handles=%d" % my_process.num_handles())
                    perfdatas.append("create_time=%d" % my_process.create_time())
                    perfdatas.append("cpu_num=%d" % my_process.cpu_num())
                    statsmgr.counter("cpu_num", my_process.cpu_num())
                    perfdatas.append("cpu_usable=%d" % len(my_process.cpu_affinity()))
                    statsmgr.counter("cpu_usable", len(my_process.cpu_affinity()))
                    perfdatas.append("cpu_percent=%.2f%%" % my_process.cpu_percent())
                    statsmgr.counter("cpu_percent", my_process.cpu_percent())

                    cpu_times_percent = my_process.cpu_times()
                    for key in cpu_times_percent._fields:
                        perfdatas.append("cpu_%s_time=%.2fs" % (key,
                                                                getattr(cpu_times_percent, key)))
                        statsmgr.counter("cpu_%s_time" % key, getattr(cpu_times_percent, key))

                    memory = my_process.memory_full_info()
                    for key in memory._fields:
                        perfdatas.append("mem_%s=%db" % (key, getattr(memory, key)))
                        statsmgr.counter("mem_%s" % key, getattr(memory, key))

                    logger.debug("Daemon %s (%s), pid=%s, ppid=%s, status=%s, cpu/memory|%s",
                                 self.name, my_process.name(), my_process.pid, my_process.ppid(),
                                 my_process.status(), " ".join(perfdatas))

            if self.activity_log_period and (self.loop_count % self.activity_log_period == 1):
                logger.info("Daemon %s is alive", self.name)

            if self.log_loop:
                logger.debug("[%s] +++ %d", self.name, self.loop_count)
            # Maybe we ask us to die, if so, do it :)
            if self.interrupted:
                logger.info("[%s] Someone asked us to stop", self.name)
                break
        self.request_stop()

    def do_load_modules(self, modules):
        """Wrapper for calling load_and_init method of modules_manager attribute

        :param modules: list of modules that should be loaded by the daemon
        :return: None
        """
        _ts = time.time()
        logger.info("Loading modules...")

        if self.modules_manager.load_and_init(modules):
            if self.modules_manager.instances:
                logger.info("I correctly loaded my modules: [%s]",
                            ','.join([inst.name for inst in self.modules_manager.instances]))
            else:
                logger.info("I do not have any module")
        else:  # pragma: no cover, not with unit tests...
            logger.error("Errors were encountered when checking and loading modules:")
            for msg in self.modules_manager.configuration_errors:
                logger.error(msg)

        if self.modules_manager.configuration_warnings:  # pragma: no cover, not tested
            for msg in self.modules_manager.configuration_warning:
                logger.warning(msg)
        statsmgr.timer('modules-loading', time.time() - _ts)

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

        Not currently implemented feature

        :return: None
        """
        logger.warning("Dumping daemon memory is not implemented. "
                       "If you really need this feature, please log "
                       "an issue in the project repository;)")

    def load_modules_manager(self, daemon_name):
        """Instantiate Modulesmanager and load the SyncManager (multiprocessing)

        :param daemon_name: daemon name
        :type elt: str
        :return: None
        """
        self.modules_manager = ModulesManager(self, self.sync_manager,
                                              max_queue_size=getattr(self, 'max_queue_size', 0))

    def change_to_workdir(self):
        """Change working directory to working attribute

        :return: None
        """
        self.workdir = os.path.abspath(self.workdir)
        logger.info("Changing working directory to: %s", self.workdir)
        try:
            os.chdir(self.workdir)
        except Exception, exp:
            raise InvalidWorkingDir(exp)
        self.pre_log.append(("INFO", "Using working directory: %s" % os.path.abspath(self.workdir)))

    def unlink(self):
        """Remove the daemon's pid file

        :return: None
        """
        logger.debug("Unlinking %s", self.pid_filename)
        try:
            os.unlink(self.pid_filename)
        except OSError as exp:
            logger.error("Got an error unlinking our pid file: %s", exp)

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
            self.pre_log.append(("DEBUG",
                                 "Opening %s pid file: %s" % ('existing' if
                                                              os.path.exists(self.pid_filename)
                                                              else 'missing', self.pid_filename)))
            # Windows do not manage the rw+ mode,
            # so we must open in read mode first, then reopen it write mode...
            if not write and os.path.exists(self.pid_filename):
                self.fpid = open(self.pid_filename, 'r+')
            else:
                # If it doesn't exist too, we create it as void
                self.fpid = open(self.pid_filename, 'w+')
        except Exception as err:
            print("Exception: %s" % err)
            raise InvalidPidFile(err)

    def check_parallel_run(self):  # pragma: no cover, not with unit tests...
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
                logger.info("Found an existing pid (%s): '%s'", self.pid_filename, pid_var)
            else:
                logger.debug("Not found an existing pid: %s", self.pid_filename)
                return
        except (IOError, ValueError) as err:
            logger.warning("pidfile is empty or has an invalid content: %s", self.pid_filename)
            return

        if pid == os.getpid():
            self.pid = pid
            return

        try:
            logger.info("Killing process: '%s'", pid)
            os.kill(pid, 0)
        except Exception as err:  # pylint: disable=W0703
            # consider any exception as a stale pid file.
            # this includes :
            #  * PermissionError when a process with same pid exists but is executed by another user
            #  * ProcessLookupError: [Errno 3] No such process
            logger.info("Stale pid file exists (%s), Reusing it.", err)
            return

        if not self.do_replace:
            raise SystemExit("valid pidfile exists (pid=%s) and not forced to replace. Exiting."
                             % pid)

        self.pre_log.append(("DEBUG", "Replacing previous instance: %d" % pid))
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
        """ Write pid to the pid file

        :param pid: pid of the process
        :type pid: None | int
        :return: None
        """
        if pid is None:
            self.pid = os.getpid()
        self.fpid.seek(0)
        self.fpid.truncate()
        self.fpid.write("%d" % (self.pid))
        self.fpid.close()
        del self.fpid  # no longer needed

    @staticmethod
    def close_fds(skip_close_fds):  # pragma: no cover, not with unit tests...
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

        self.pre_log.append(("DEBUG", "Redirecting stdout and stderr as necessary."))
        if self.debug and self.debug_file:
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
        self.pre_log.append(("DEBUG", "We are now fully daemonized :) pid=%d" % self.pid))

    # The Manager is a sub-process, so we must be sure it won't have
    # a socket of our http server alive
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
        self.set_proctitle(self.name)
        self.change_to_user_group()
        self.change_to_workdir()
        self.check_parallel_run()
        if not self.setup_communication_daemon():
            logger.error("I could not setup my communication daemon...")
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
        except PortNotFree:
            logger.error('The HTTP daemon port (%s:%d) is not free...', self.host, self.port)
            # logger.exception('The HTTP daemon port is not free: %s', exp)
            return False

        return True

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
        except KeyError:  # pragma: no cover, should not happen...
            logger.error("The user %s is unknown", self.user)
            return None

    def find_gid_from_name(self):
        """Wrapper for getgrnam : get the uid of user attribute

        :return: Uid of user attribute
        :rtype: str | None
        """
        try:
            return getgrnam(self.group)[2]
        except KeyError:  # pragma: no cover, should not happen
            logger.error("The group %s is unknown", self.group)
            return None

    def change_to_user_group(self, insane=None):
        """ Change to user of the running program.
        If change failed we sys.exit(2)

        :param insane: boolean to allow running as root (True to allow)
        :type insane: bool
        :return: None
        """
        if insane is None:
            insane = self.idontcareaboutsecurity

        # TODO: change user on nt
        if os.name == 'nt':  # pragma: no cover, no Windows implementation currently
            logger.warning("You can't change user on this system")
            return

        if (self.user == 'root' or self.group == 'root') and not insane:  # pragma: no cover
            logger.error("You want the application run under the root account?")
            logger.error("I do not agree with it. If you really want it, put:")
            logger.error("idontcareaboutsecurity=1")
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
        logger.info('Trying to initialize additional groups for the daemon')
        if hasattr(os, 'initgroups'):
            try:
                os.initgroups(self.user, gid)
            except OSError as err:
                logger.warning('Cannot call the additional groups setting with initgroups: %s',
                               err.strerror)
        elif hasattr(os, 'setgroups'):  # pragma: no cover, not with unit tests on Travis
            # Else try to call the setgroups if it exists...
            groups = [gid] + \
                     [group.gr_gid for group in get_all_groups() if self.user in group.gr_mem]
            try:
                os.setgroups(groups)
            except OSError as err:
                logger.warning('Cannot call the additional groups setting with setgroups: %s',
                               err.strerror)
        try:
            # First group, then user :)
            os.setregid(gid, gid)
            os.setreuid(uid, uid)
        except OSError as err:  # pragma: no cover, not with unit tests...
            logger.error("Cannot change user/group to %s/%s (%s [%d]). Exiting...",
                         self.user, self.group, err.strerror, err.errno)
            sys.exit(2)

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
        logger.info("process '%s' (pid=%d) received a signal: %s",
                    self.name, os.getpid(), SIGNALS_TO_NAMES_DICT[sig])
        if sig == signal.SIGUSR1:  # if USR1, ask a memory dump
            self.need_dump_memory = True
        elif sig == signal.SIGUSR2:  # if USR2, ask objects dump
            self.need_objects_dump = True
        elif sig == signal.SIGHUP:  # if HUP, reload configuration in arbiter
            self.need_config_reload = True
        else:  # Ok, really ask us to die :)
            logger.info("request to stop the daemon")
            self.interrupted = True

    def set_signal_handler(self, sigs=None):
        """Set the signal handler to manage_signal (defined in this class)

        Only set handlers for:
        - signal.SIGTERM, signal.SIGINT
        - signal.SIGUSR1, signal.SIGUSR2
        - signal.SIGHUP

        :return: None
        """
        func = self.manage_signal
        if os.name == "nt":  # pragma: no cover, no Windows implementation currently
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

    set_exit_handler = set_signal_handler

    def set_proctitle(self, daemon_name=None):
        """Set the proctitle of the daemon

        :param daemon_name: daemon instance name (eg. arbiter-master). If not provided, only the
        daemon type (eg. arbiter) will be used for the process title
        :type daemon_name: str
        :return: None
        """
        logger.debug("Setting my process name: %s", daemon_name)
        if daemon_name:
            setproctitle("alignak-%s %s" % (self.type, daemon_name))
            if self.modules_manager:
                self.modules_manager.set_daemon_name(daemon_name)
        else:
            setproctitle("alignak-%s" % self.type)

    def get_header(self):
        """Get the log file header

        :return: A string list containing project name, daemon name, version, licence etc.
        :rtype: list
        """
        header = ["-----",
                  "Alignak %s - %s daemon" % (VERSION, self.name),
                  "Copyright (c) 2015-2017: Alignak Team",
                  "License: AGPL",
                  "-----",
                  "My pid: %s" % self.pid,
                  "My configuration: "]

        for prop, _ in sorted(self.properties.items()):
            header.append(" - %s=%s" % (prop, getattr(self, prop)))

        return header

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
            # print("Exception: %s" % str(exp))
            # logger.exception('The HTTP daemon port is not free: %s', exp)
            raise
        except Exception as exp:  # pylint: disable=W0703
            logger.exception('The HTTP daemon failed with the error %s, exiting', str(exp))
            raise
        logger.info("HTTP main thread exiting")

    def make_a_pause(self, timeout=0.0001, check_time_change=True):
        """ Wait up to timeout and check for system time change.

        This function checks if the system time changed since the last call. If so,
        the difference is returned to the caller.
        The duration of this call is removed from the timeout. If this duration is
        greater than the required timeout, no sleep is executed and the extra time
        is returned to the caller

        If the required timeout was overlapped, then the first return value will be
        greater than the required timeout.

        If the required timeout is null, then the timeout value is set as a very short time
        to keep a nice behavior to the system CPU ;)

        :param timeout: timeout to wait for activity
        :type timeout: float
        :param check_time_change: True (default) to check if the system time changed
        :type check_time_change: bool
        :return:Returns a 2-tuple:
        * first value is the time spent for the time change check
        * second value is the time change difference
        :rtype: tuple
        """
        if timeout == 0:
            timeout = 0.0001

        if not check_time_change:
            # Time to sleep
            time.sleep(timeout)
            self.sleep_time += timeout
            return 0, 0

        # Check is system time changed
        before = time.time()
        time_changed = self.check_for_system_time_change()
        after = time.time()
        elapsed = after - before

        if elapsed > timeout:
            return elapsed, time_changed
        # Time to sleep
        time.sleep(timeout - elapsed)

        # Increase our sleep time for the time we slept
        before += time_changed
        self.sleep_time += time.time() - before

        return elapsed, time_changed

    def check_for_system_time_change(self):
        """Check if our system time change. If so, change our

        :return: 0 if the difference < 900, difference else
        :rtype: int
        TODO: Duplicate of alignak.worker.Worker.check_for_system_time_change
        """
        now = time.time()
        difference = now - self.t_each_loop

        # If we have more than 15 min time change, we need to compensate it
        # todo: confirm that 15 minutes is a good choice...
        if abs(difference) > 900:  # pragma: no cover, not with unit tests...
            self.compensate_system_time_change(
                difference,
                self.sched.timeperiods if hasattr(self, "sched") else None)
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
        """Wait initial configuration from the arbiter.
        Basically sleep 1.0 and check if new_conf is here

        :param timeout: timeout to wait from socket read
        :type timeout: int
        :return: None
        """
        logger.info("Waiting for initial configuration")
        # Arbiter do not already set our have_conf param
        _ts = time.time()
        while not self.new_conf and not self.interrupted:
            # Make a pause and check if the system time changed
            _, _ = self.make_a_pause(timeout, check_time_change=True)
            # sys.stdout.write(".")
            # sys.stdout.flush()
        if not self.interrupted:
            logger.info("Got initial configuration, waited for: %.2f", time.time() - _ts)
            statsmgr.timer('initial-configuration', time.time() - _ts)
        else:
            logger.info("Interrupted before getting the initial configuration")

    def hook_point(self, hook_name):
        """Used to call module function that may define a hook function
        for hook_name

        :param hook_name: function name we may hook in module
        :type hook_name: str
        :return: None
        """
        for module in self.modules_manager.instances:
            _ts = time.time()
            full_hook_name = 'hook_' + hook_name
            if hasattr(module, full_hook_name):
                fun = getattr(module, full_hook_name)
                try:
                    fun(self)
                except Exception as exp:  # pylint: disable=W0703
                    logger.warning('The instance %s raised an exception %s. I disabled it,'
                                   'and set it to restart later', module.name, str(exp))
                    logger.exception('Exception %s', exp)
                    self.modules_manager.set_to_restart(module)
                else:
                    statsmgr.timer('core.hook.%s.%s' % (module.name, hook_name), time.time() - _ts)

    def get_retention_data(self):  # pylint: disable=R0201
        """Basic function to get retention data,
        Maybe be overridden by subclasses to implement real get

        :return: A list of Alignak object (scheduling items)
        :rtype: list
        """
        return []

    def restore_retention_data(self, data):
        """Basic function to save retention data,
        Maybe be overridden by subclasses to implement real save

        :return: None
        """
        pass

    def get_stats_struct(self):
        """Get state of modules and create a scheme for stats data of daemon
        This may be overridden in subclasses (and it is...)

        NOTE: This is overriden by all the daemons but it is never called anywhere. Inherited
         from the shinken.io implementation in Shinken!

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
            'metrics': [], 'version': VERSION, 'name': self.name, 'type': self.type,
            'modules': {
                'internal': {}, 'external': {}
            }
        }
        modules = res['modules']

        # first get data for all internal modules
        for instance in self.modules_manager.get_internal_instances():
            state = {True: 'ok', False: 'stopped'}[(instance not in self.modules_manager.to_restart)]
            env = {'name': instance.name, 'state': state}
            modules['internal'][instance.name] = env
        # Same but for external ones
        for instance in self.modules_manager.get_external_instances():
            state = {True: 'ok', False: 'stopped'}[(instance not in self.modules_manager.to_restart)]
            env = {'name': instance.name, 'state': state}
            modules['external'][instance.name] = env

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
        for module in self.modules_manager.get_external_instances():
            queue = module.from_q
            if not queue:
                continue
            while True:
                start = time.time()
                queue_size = queue.qsize()
                if queue_size:
                    statsmgr.gauge('queues.external.%s.from.size' % module.get_name(), queue_size)
                try:
                    obj = queue.get_nowait()
                except Full:
                    logger.warning("Module %s from queue is full", module.get_name())
                except Empty:
                    logger.debug("Module %s from queue is full", module.get_name())
                    break
                except (IOError, EOFError) as exp:
                    logger.warning("Module %s from queue is no more available: %s",
                                   module.get_name(), str(exp))
                except Exception as exp:  # pylint: disable=W0703
                    logger.error("An external module queue got a problem '%s'", str(exp))
                else:
                    had_some_objects = True
                    statsmgr.timer('queues.external.%s.from.get' % module.get_name(),
                                   time.time() - start)
                    self.add(obj)

        return had_some_objects

    def setup_alignak_logger(self):
        """ Setup alignak logger:
        - with the daemon log configuration properties
        - configure the global daemon handler (root logger)
        - log the daemon Alignak header

        :return: None
        """
        # Force the debug level if the daemon is said to start with such level
        log_level = self.log_level
        if self.debug:
            log_level = 'DEBUG'

        # Set the human timestamp log if required
        human_log_format = getattr(self, 'human_timestamp_log', False)

        # Register local log file if required
        if self.use_log_file:
            try:
                # pylint: disable=E1101
                setup_logger(None, level=log_level, human_log=human_log_format,
                             log_console=True, log_file=self.log_filename,
                             when=self.log_rotation_when, interval=self.log_rotation_interval,
                             backup_count=self.log_rotation_count,
                             human_date_format=self.human_date_format)
            except IOError as exp:  # pragma: no cover, not with unit tests...
                logger.error("Opening the log file '%s' failed with '%s'", self.log_filename, exp)
                sys.exit(2)
            logger.debug("Using the local log file '%s'", self.log_filename)
            self.local_log_fds = get_logger_fds(None)
        else:  # pragma: no cover, not with unit tests...
            setup_logger(None, level=log_level, human_log=human_log_format,
                         log_console=True, log_file=None)
            logger.warning("No local log file")

        logger.debug("Alignak daemon logger configured")

        # Log daemon header
        for line in self.get_header():
            logger.info(line)

        # We can now output some previously silenced debug output
        if self.pre_log:
            logger.debug("--- Messages stored prior to our configuration:")
            for level, message in self.pre_log:
                if level.lower() == "debug":
                    logger.debug("--- %s", message)
                elif level.lower() == "info":
                    logger.info("--- %s", message)
                elif level.lower() == "warning":
                    logger.warning("--- %s", message)
            logger.debug("---")
