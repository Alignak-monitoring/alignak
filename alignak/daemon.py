# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines
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
# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines
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
import json
import resource
import socket
import signal
from copy import copy
import threading
import logging
import tempfile
import warnings
import traceback
from queue import Empty, Full
from multiprocessing.managers import SyncManager

import configparser
import collections
import psutil

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

from alignak.log import setup_logger, set_log_level
from alignak.http.daemon import HTTPDaemon, PortNotFree
from alignak.stats import statsmgr
from alignak.modulesmanager import ModulesManager
from alignak.property import StringProp, BoolProp, PathProp
from alignak.property import IntegerProp, FloatProp, LogLevelProp, ListProp
from alignak.misc.common import setproctitle, SIGNALS_TO_NAMES_DICT
from alignak.version import VERSION

from alignak.bin.alignak_environment import AlignakConfigParser


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

# #########################   DAEMON PART    ###############################
# Recommended (default) umask for a daemonized process is 0. Former Alignak one was 027...
# UMASK = 027
UMASK = 0

# This default value is used to declare the properties that are Path properties
# During the daemon initialization, this value is replaced with the real daemon working directory
# and it will be overloaded with the value defined in the daemon configuration or launch parameters
DEFAULT_WORK_DIR = '/'


class EnvironmentFile(Exception):
    """Exception raised when the Alignak environment file is missing or corrupted"""

    def __init__(self, msg):
        Exception.__init__(self, msg)


# pylint: disable=R0902
class Daemon(object):
    """Class providing daemon level call for Alignak
    """

    properties = {
        'type':
            StringProp(default=u'unknown'),
        'daemon':
            StringProp(default=u'unknown'),
        'name':
            StringProp(),
        # Alignak main configuration file
        'env_filename':
            StringProp(default=u''),

        'log_loop':         # Set True to log the daemon loop activity
            BoolProp(default=False),

        'pid_filename':
            StringProp(default=u''),

        # Daemon directories
        'etcdir':   # /usr/local/etc/alignak
            PathProp(default=DEFAULT_WORK_DIR),
        'workdir':  # /usr/local/var/run/alignak
            PathProp(default=DEFAULT_WORK_DIR),
        'vardir':   # /usr/local/var/lib/alignak
            PathProp(default=DEFAULT_WORK_DIR),
        'logdir':   # /usr/local/var/log/alignak
            PathProp(default=DEFAULT_WORK_DIR),
        'bindir':   # Default is empty
            PathProp(default=''),

        # Interface the daemon will listen to
        'host':
            StringProp(default=u'127.0.0.1'),
        # Address the daemon will be reachable on
        'address':
            StringProp(default=u'127.0.0.1'),
        # Server hostname
        'host_name':
            StringProp(default=u'localhost'),

        # Credentials the daemon will fork to
        'user':
            StringProp(default=get_cur_user()),
        'group':
            StringProp(default=get_cur_group()),

        'use_ssl':
            BoolProp(default=False),
        # Not used currently
        'hard_ssl_name_check':
            BoolProp(default=False),
        'server_cert':
            StringProp(default=u'etc/certs/server.cert'),
        'server_key':
            StringProp(default=u'etc/certs/server.key'),
        'ca_cert':
            StringProp(default=u''),
        # Not used currently
        'server_dh':
            StringProp(default=u''),

        # Deprecated in favor of logger_configuration
        # 'human_timestamp_log':
        #     BoolProp(default=True),
        # 'human_date_format':
        #     StringProp(default='%Y-%m-%d %H:%M:%S %Z'),
        # 'log_level':
        #     LogLevelProp(default='INFO'),
        # 'log_rotation_when':
        #     StringProp(default='midnight'),
        # 'log_rotation_interval':
        #     IntegerProp(default=1),
        # 'log_rotation_count':
        #     IntegerProp(default=7),
        'logger_configuration':
            StringProp(default=u'./alignak-logger.json'),
        # Override log file name - default is to not override
        'log_filename':
            StringProp(default=u''),
        # Override log level - default is to not change anything
        'log_level':
            StringProp(default=u''),
        # Set True to include cherrypy logs in the daemon log file
        'log_cherrypy':
            BoolProp(default=False),
        'favicon':
            PathProp(default=''),

        'idontcareaboutsecurity':
            BoolProp(default=False),
        'do_replace':
            BoolProp(default=False),
        'is_daemon':
            BoolProp(default=False),
        'active':
            BoolProp(default=True),
        'spare':
            BoolProp(default=False),
        'max_queue_size':
            IntegerProp(default=0),
        'thread_pool_size':
            IntegerProp(default=32),
        'debug':
            BoolProp(default=False),
        'verbose':
            BoolProp(default=False),

        # Daemon start time
        'start_time':
            FloatProp(default=0.0),

        'pause_duration':
            FloatProp(default=0.5),
        'maximum_loop_duration':
            FloatProp(default=1.0),

        # Daemon modules
        'modules':
            ListProp(default=[]),

        # Alignak will report its status to its monitor
        # Interface is the same as the Alignak WS module PATCH/host
        'alignak_monitor':
            StringProp(default=u''),
        'alignak_monitor_period':
            IntegerProp(default=60),
        'alignak_monitor_username':
            StringProp(default=u''),
        'alignak_monitor_password':
            StringProp(default=u''),

        # Local statsd daemon for collecting daemon metrics
        'statsd_host':
            StringProp(default=u'localhost'),
        'statsd_port':
            IntegerProp(default=8125),
        'statsd_prefix':
            StringProp(default=u'alignak'),
        'statsd_enabled':
            BoolProp(default=False),
        # Use Graphite/carbon connection instead of StatsD
        'graphite_enabled':
            BoolProp(default=False),
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
        self.legacy_cfg_files = []
        self.modules_manager = None

        # First, do we debug?
        self.debug = False
        if 'debug' in kwargs and kwargs['debug']:
            self.debug = kwargs['debug']
        # First, do we verbose?
        self.verbose = False
        if 'verbose' in kwargs and kwargs['verbose']:
            self.verbose = kwargs['verbose']
        # Used to track debug, info warnings that will be logged once the logger is effective
        self.pre_log = []

        # I got my name
        self.name = name
        self.host_name = socket.getfqdn()
        self.address = '127.0.0.1'

        # Check if /dev/shm exists and usable...
        self.check_shm()

        self.pre_log.append(("DEBUG",
                             "Daemon '%s' initial working directory: %s"
                             % (self.name, os.getcwd())))

        # I define my default properties
        # Same as the Item.fill_default()... but I am not in this object hierarchy!
        my_properties = self.__class__.properties
        for prop, entry in list(my_properties.items()):
            if getattr(self, prop, None) is not None:
                #  Still initialized...
                continue
            # Set absolute paths for our paths
            if isinstance(my_properties[prop], PathProp):
                if entry.default == DEFAULT_WORK_DIR:
                    setattr(self, prop, os.getcwd())
                else:
                    if not entry.default:
                        setattr(self, prop, '')
                    else:
                        setattr(self, prop, os.path.abspath(entry.pythonize(entry.default)))
            else:
                if hasattr(entry.default, '__iter__'):
                    setattr(self, prop, copy(entry.default))
                else:
                    setattr(self, prop, entry.pythonize(entry.default))

        # Configuration file name in environment
        if os.environ.get('ALIGNAK_CONFIGURATION_FILE'):
            kwargs['env_file'] = os.path.abspath(os.environ.get('ALIGNAK_CONFIGURATION_FILE'))
            print("Alignak environment file from system environment: %s" % kwargs['env_file'])

        # I must have an Alignak environment file
        if 'env_file' not in kwargs:
            self.exit_on_error("Alignak environment file is missing or corrupted", exit_code=1)

        if kwargs['env_file']:
            self.env_filename = kwargs['env_file']
            if self.env_filename != os.path.abspath(self.env_filename):
                self.env_filename = os.path.abspath(self.env_filename)
            # print("Daemon '%s' is started with an environment file: %s"
            #       % (self.name, self.env_filename))
            self.pre_log.append(("INFO",
                                 "Daemon '%s' is started with an environment file: %s"
                                 % (self.name, self.env_filename)))

            # Read Alignak environment file
            args = {'<cfg_file>': self.env_filename, '--verbose': self.debug}
            configuration_dir = os.path.dirname(self.env_filename)
            try:
                self.alignak_env = AlignakConfigParser(args)
                self.alignak_env.parse()

                legacy_cfg_files = self.alignak_env.get_legacy_cfg_files()
                if legacy_cfg_files:
                    for prop, value in list(self.alignak_env.get_legacy_cfg_files().items()):
                        self.pre_log.append(("DEBUG",
                                             "Found Alignak monitoring "
                                             "configuration parameter, %s = %s" % (prop, value)))
                        # Ignore empty value
                        if not value:
                            continue

                        # Make the path absolute
                        if not os.path.isabs(value):
                            value = os.path.abspath(os.path.join(configuration_dir, value))
                        self.legacy_cfg_files.append(value)
                if self.type == 'arbiter' and not self.legacy_cfg_files:
                    self.pre_log.append(("WARNING",
                                         "No Nagios-like legacy configuration files configured."))
                    self.pre_log.append(("WARNING",
                                         "If you need some, edit the 'alignak.ini' configuration "
                                         "file to declare one or more 'cfg=' variables."))

                my_configuration = list(self.alignak_env.get_daemons(daemon_name=self.name).items())
                for prop, value in my_configuration:
                    self.pre_log.append(("DEBUG",
                                         " found daemon parameter, %s = %s" % (prop, value)))
                    if getattr(self, prop, None) is None:
                        # For an undeclared property, store the value as a string
                        setattr(self, prop, value)
                        self.pre_log.append(("DEBUG", " -> setting %s = %s" % (prop, value)))
                    elif isinstance(getattr(self, prop), collections.Callable):
                        # For a declared property, that match a self function name
                        self.exit_on_error("Variable %s cannot be defined as a property because "
                                           "it exists a callable function with the same name!"
                                           % prop, exit_code=1)
                    else:
                        # For a declared property, cast the read value
                        current_prop = getattr(self, prop)
                        setattr(self, prop, my_properties[prop].pythonize(value))
                        self.pre_log.append(("DEBUG", " -> updating %s = %s to %s"
                                             % (prop, current_prop, getattr(self, prop))))
                if not my_configuration:
                    self.pre_log.append(("WARNING",
                                         "No defined configuration for the daemon: %s. "
                                         % self.name))

                    # todo: why doing this? It is quite tricky to configure daemon if it  does not
                    # have its own configuration section, perhaps removing this should be fine!
                    # self.pre_log.append(("DEBUG",
                    #                      "No defined configuration for the daemon: %s. "
                    #                      "Using the 'alignak-configuration' section "
                    #                      "variables as parameters for the daemon:" % self.name))
                    #
                    # # Set the global Alignak configuration parameters
                    # # as the current daemon properties
                    # self.pre_log.append(("INFO",
                    #                      "Get alignak configuration to configure the daemon..."))
                    # alignak_configuration = self.alignak_env.get_alignak_configuration()
                    # if alignak_configuration:
                    #     for prop, value in list(alignak_configuration.items()):
                    #         if prop in ['name'] or prop.startswith('_'):
                    #             self.pre_log.append(("DEBUG",
                    #                                  "- ignoring '%s' variable." % prop))
                    #             continue
                    #         if prop in self.properties:
                    #             entry = self.properties[prop]
                    #             setattr(self, prop, entry.pythonize(value))
                    #         else:
                    #             setattr(self, prop, value)
                    #         print("Daemon %s, prop: %s = %s" % (self.name, prop, value))
                    #         self.pre_log.append(("DEBUG",
                    #                              "- setting '%s' as %s" % (prop,
                    # getattr(self, prop))))

            except configparser.ParsingError as exp:
                self.exit_on_exception(EnvironmentFile(exp.message))
            except Exception as exp:  # pylint: disable=broad-except
                print("Daemon '%s' did not correctly read Alignak environment file: %s"
                      % (self.name, args['<cfg_file>']))
                print("Exception: %s\n%s" % (exp, traceback.format_exc()))
                self.exit_on_exception(EnvironmentFile("Exception: %s" % (exp)))

        # Stop me if it I am disabled in the configuration
        if not self.active:
            self.exit_ok(message="This daemon is disabled in Alignak configuration. Exiting.",
                         exit_code=0)

        # And perhaps some old parameters from the initial command line!
        if 'config_file' in kwargs and kwargs['config_file']:  # pragma: no cover, simple log
            warnings.warn(
                "Using daemon configuration file is now deprecated. The daemon -c parameter "
                "should not be used anymore in favor the -e environment file parameter.",
                DeprecationWarning, stacklevel=2)
            raise EnvironmentFile("Using daemon configuration file is now deprecated. "
                                  "The daemon -c command line parameter should not be "
                                  "used anymore in favor the -e environment file parameter.")

        if 'is_daemon' in kwargs and kwargs['is_daemon']:
            self.is_daemon = BoolProp().pythonize(kwargs['is_daemon'])
        if 'do_replace' in kwargs and kwargs['do_replace']:
            self.do_replace = BoolProp().pythonize(kwargs['do_replace'])
        if 'debug' in kwargs and kwargs['debug']:
            self.debug = BoolProp().pythonize('1')
        if 'verbose' in kwargs and kwargs['verbose']:
            self.verbose = BoolProp().pythonize('1')

        if 'host' in kwargs and kwargs['host']:
            self.host = StringProp().pythonize(kwargs['host'])
        if 'port' in kwargs and kwargs['port']:
            try:
                self.port = int(kwargs['port'])
                print("Daemon '%s' is started with an overidden port number: %d"
                      % (self.name, self.port))
            except ValueError:
                pass

        # Running user/group in environment
        if os.environ.get('ALIGNAK_USER'):
            self.user = os.environ.get('ALIGNAK_USER')
            print("Alignak user from system environment: %s" % self.user)
        if os.environ.get('ALIGNAK_GROUP'):
            self.group = os.environ.get('ALIGNAK_GROUP')
            print("Alignak group from system environment: %s" % self.group)

        if self.debug:
            print("Daemon '%s' is in debug mode" % self.name)

        if self.is_daemon:
            print("Daemon '%s' is in daemon mode" % self.name)

        self.uid = None
        try:
            self.uid = getpwnam(self.user).pw_uid
        except KeyError:
            logger.error("The required user %s is unknown", self.user)

        self.gid = None
        try:
            self.gid = getgrnam(self.group).gr_gid
        except KeyError:
            logger.error("The required group %s is unknown", self.group)

        if self.uid is None or self.gid is None:
            self.exit_on_error("Configured user/group (%s/%s) are not valid."
                               % (self.user, self.group), exit_code=3)

        # Alignak logger configuration file
        if os.getenv('ALIGNAK_LOGGER_CONFIGURATION', None):
            self.logger_configuration = os.getenv('ALIGNAK_LOGGER_CONFIGURATION', None)
        if self.logger_configuration != os.path.abspath(self.logger_configuration):
            if self.logger_configuration == './alignak-logger.json':
                self.logger_configuration = os.path.join(os.path.dirname(self.env_filename),
                                                         self.logger_configuration)
            else:
                self.logger_configuration = os.path.abspath(self.logger_configuration)
        print("Daemon '%s' logger configuration file: %s" % (self.name, self.logger_configuration))

        # # Make my paths properties be absolute paths
        # for prop, entry in list(my_properties.items()):
        #     # Set absolute paths for
        #     if isinstance(my_properties[prop], PathProp):
        #         setattr(self, prop, os.path.abspath(getattr(self, prop)))

        # Log file...
        self.log_filename = PathProp().pythonize("%s.log" % self.name)
        self.log_filename = os.path.abspath(os.path.join(self.logdir, self.log_filename))
        if 'log_filename' in kwargs and kwargs['log_filename']:
            self.log_filename = PathProp().pythonize(kwargs['log_filename'].strip())
            # Make it an absolute path file in the log directory
            if self.log_filename != os.path.abspath(self.log_filename):
                if self.log_filename:
                    self.log_filename = os.path.abspath(os.path.join(self.logdir,
                                                                     self.log_filename))
                else:
                    self.use_log_file = False
                    print("Daemon '%s' will not log to a file: %s" % (self.name))
            else:
                self.logdir = os.path.dirname(self.log_filename)
            print("Daemon '%s' is started with an overridden log file: %s"
                  % (self.name, self.log_filename))

        # Check the log directory (and create if it does not exist)
        self.check_dir(os.path.dirname(self.log_filename))

        # Specific monitoring log directory
        # self.check_dir(os.path.join(os.path.dirname(self.log_filename), 'monitoring-log'))

        if 'log_filename' not in kwargs or not kwargs['log_filename']:
            # Log file name is not overridden, the logger will use the configured default one
            if self.log_cherrypy:
                self.log_cherrypy = self.log_filename
                print("Daemon '%s' is started with CherryPy log enabled: %s"
                      % (self.name, self.log_cherrypy))
            else:
                self.log_cherrypy = None
            self.log_filename = ''

        # pid file is stored in the working directory
        self.pid = os.getpid()
        self.pid_filename = PathProp().pythonize("%s.pid" % self.name)
        self.pid_filename = os.path.abspath(os.path.join(self.workdir, self.pid_filename))
        if 'pid_filename' in kwargs and kwargs['pid_filename']:
            self.pid_filename = PathProp().pythonize(kwargs['pid_filename'].strip())
            # Make it an absolute path file in the pid directory
            if self.pid_filename != os.path.abspath(self.pid_filename):
                self.pid_filename = os.path.abspath(os.path.join(self.workdir, self.pid_filename))
            self.workdir = os.path.dirname(self.pid_filename)
            print("Daemon working directory: %s" % self.workdir)
        print("Daemon '%s' pid file: %s" % (self.name, self.pid_filename))
        self.pre_log.append(("INFO",
                             "Daemon '%s' pid file: %s" % (self.name, self.pid_filename)))

        # Self daemon monitoring (cpu, memory)
        self.daemon_monitoring = False
        self.daemon_monitoring_period = 10
        if 'ALIGNAK_DAEMON_MONITORING' in os.environ:
            self.daemon_monitoring = True
            try:
                self.daemon_monitoring_period = int(os.environ.get('ALIGNAK_DAEMON_MONITORING',
                                                                   '10'))
            except ValueError:  # pragma: no cover, simple protection
                pass
        if self.daemon_monitoring:
            print("Daemon '%s' self monitoring is enabled, reporting every %d loop count."
                  % (self.name, self.daemon_monitoring_period))

        # Configure our Stats manager
        if not self.graphite_enabled:
            statsmgr.register(self.name, self.type,
                              statsd_host=self.statsd_host, statsd_port=self.statsd_port,
                              statsd_prefix=self.statsd_prefix, statsd_enabled=self.statsd_enabled)
        else:
            statsmgr.connect(self.name, self.type,
                             host=self.statsd_host, port=self.statsd_port,
                             prefix=self.statsd_prefix, enabled=True)

        # Track time
        now = time.time()
        self.program_start = now
        self.t_each_loop = now  # used to track system time change
        self.sleep_time = 0.0  # used to track the time we wait

        self.interrupted = False
        self.will_stop = False

        self.http_thread = None
        self.http_daemon = None
        # Semaphore for the HTTP interface
        self.lock = threading.RLock()

        # Configuration dispatch
        # when self.new_conf is not empty, the arbiter sent a new configuration to manage
        self.new_conf = {}
        # when self.cur_conf is not None or empty, the daemon has received and manages a
        # configuration from the arbiter
        self.have_conf = False
        self.cur_conf = {}
        # Specific Semaphore for the configuration
        self.conf_lock = threading.RLock()

        # Flag to know if we need to dump memory or not
        self.need_dump_environment = False

        # Flag to dump objects or not
        self.need_objects_dump = False

        # Flag to reload configuration
        self.need_config_reload = False

        # Increased on each loop turn
        self.loop_count = None

        # Daemon start timestamp
        self.start_time = None

        # Log loop turns if environment variable is set
        if 'ALIGNAK_LOG_LOOP' in os.environ:
            self.log_loop = 'ALIGNAK_LOG_LOOP' in os.environ

        # Activity information log period (every activity_log_period loop, raise a log)
        try:
            self.activity_log_period = int(os.getenv('ALIGNAK_LOG_ACTIVITY', '3600'))
        except ValueError:  # pragma: no cover, simple protection
            self.activity_log_period = 0

        # We will initialize the Manager() when we load modules
        # and are really forked
        self.sync_manager = None

        self.set_signal_handler()

    def __repr__(self):  # pragma: no cover
        return '<Daemon %r/%r, listening on %r:%r:%d />' % \
               (self.type, self.name, self.scheme, self.host, self.port)
    __str__ = __repr__

    @property
    def pidfile(self):
        """Return the pid file name - make it compatible with old implementation

        :return: pid_filename property
        :rtype: str
        """
        return self.pid_filename

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

    def check_dir(self, dirname):
        """Check and create directory

        :param dirname: file name
        :type dirname; str

        :return: None
        """
        try:
            os.makedirs(dirname)
            dir_stat = os.stat(dirname)
            print("Created the directory: %s, stat: %s" % (dirname, dir_stat))
            if not dir_stat.st_uid == self.uid:
                os.chown(dirname, self.uid, self.gid)
                os.chmod(dirname, 0o775)
                dir_stat = os.stat(dirname)
                print("Changed directory ownership and permissions: %s, stat: %s"
                      % (dirname, dir_stat))

            self.pre_log.append(("DEBUG",
                                 "Daemon '%s' directory %s checking... "
                                 "User uid: %s, directory stat: %s."
                                 % (self.name, dirname, os.getuid(), dir_stat)))

            self.pre_log.append(("INFO",
                                 "Daemon '%s' directory %s did not exist, I created it. "
                                 "I set ownership for this directory to %s:%s."
                                 % (self.name, dirname, self.user, self.group)))
        except OSError as exp:
            if exp.errno == errno.EEXIST and os.path.isdir(dirname):
                # Directory still exists...
                pass
            else:
                self.pre_log.append(("ERROR",
                                     "Daemon directory '%s' did not exist, "
                                     "and I could not create. Exception: %s"
                                     % (dirname, exp)))
                self.exit_on_error("Daemon directory '%s' did not exist, "
                                   "and I could not create.'. Exception: %s"
                                   % (dirname, exp), exit_code=3)

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

        if self.sync_manager:
            logger.info("Shutting down synchronization manager...")
            self.sync_manager.shutdown()
            self.sync_manager = None

        # Maybe the modules manager is not even created!
        if self.modules_manager:
            logger.info("Shutting down modules manager...")
            self.modules_manager.stop_all()

        # todo: daemonize the process thanks to CherryPy plugin
        if self.http_daemon:
            logger.info("Shutting down HTTP daemon...")
            if self.http_daemon.cherrypy_thread:
                self.http_daemon.stop()
            self.http_daemon = None

        # todo: daemonize the process thanks to CherryPy plugin
        if self.http_thread:
            logger.info("Checking HTTP thread...")
            # Let a few seconds to exit
            self.http_thread.join(timeout=3)
            if self.http_thread.is_alive():  # pragma: no cover, should never happen...
                logger.warning("HTTP thread did not terminated. Force stopping the thread..")
                # try:
                #     self.http_thread._Thread__stop()  # pylint: disable=E1101
                # except Exception as exp:  # pylint: disable=broad-except
                #     print("Exception: %s" % exp)
            else:
                logger.debug("HTTP thread exited")
            self.http_thread = None

    def request_stop(self, message='', exit_code=0):
        """Remove pid and stop daemon

        :return: None
        """
        # Log an error message if exit code is not 0
        # Force output to stderr
        if exit_code:
            if message:
                logger.error(message)
                try:
                    sys.stderr.write(message)
                except Exception:  # pylint: disable=broad-except
                    pass
            logger.error("Sorry, I bail out, exit code: %d", exit_code)
            try:
                sys.stderr.write("Sorry, I bail out, exit code: %d" % exit_code)
            except Exception:  # pylint: disable=broad-except
                pass
        else:
            if message:
                logger.info(message)

        self.unlink()
        self.do_stop()

        logger.info("Stopped %s.", self.name)
        sys.exit(exit_code)

    def get_links_of_type(self, s_type=''):
        """Return the `s_type` satellite list (eg. schedulers)

        If s_type is None, returns a dictionary of all satellites, else returns the dictionary
        of the s_type satellites

        The returned dict is indexed with the satellites uuid.

        :param s_type: satellite type
        :type s_type: str
        :return: dictionary of satellites
        :rtype: dict
        """
        satellites = {
            'arbiter': getattr(self, 'arbiters', []),
            'scheduler': getattr(self, 'schedulers', []),
            'broker': getattr(self, 'brokers', []),
            'poller': getattr(self, 'pollers', []),
            'reactionner': getattr(self, 'reactionners', []),
            'receiver': getattr(self, 'receivers', [])
        }
        if not s_type:
            result = {}
            for sat_type in satellites:
                # if sat_type == self.type:
                #     continue
                for sat_uuid in satellites[sat_type]:
                    result[sat_uuid] = satellites[sat_type][sat_uuid]
            return result
        if s_type in satellites:
            return satellites[s_type]

        return None

    def daemon_connection_init(self, s_link, set_wait_new_conf=False):
        """Initialize a connection with the daemon for the provided satellite link

        Initialize the connection (HTTP client) to the daemon and get its running identifier.
        Returns True if it succeeds else if any error occur or the daemon is inactive
        it returns False.

        Assume the daemon should be reachable because we are initializing the connection...
        as such, force set the link reachable property

        If set_wait_new_conf is set, the daemon is requested to wait a new configuration if
         we get a running identifier. This is used by the arbiter when a new configuration
         must be dispatched

        NB: if the daemon is configured as passive, or if it is a daemon link that is
        inactive then it returns False without trying a connection.

        :param s_link: link of the daemon to connect to
        :type s_link: SatelliteLink
        :param set_wait_new_conf: if the daemon must got the wait new configuration state
        :type set_wait_new_conf: bool
        :return: True if the connection is established, else False
        """
        logger.debug("Daemon connection initialization: %s %s", s_link.type, s_link.name)

        # If the link is not not active, I do not try to initialize the connection, just useless ;)
        if not s_link.active:
            logger.warning("%s '%s' is not active, do not initialize its connection!",
                           s_link.type, s_link.name)
            return False

        # Create the daemon connection
        s_link.create_connection()

        # Get the connection running identifier - first client / server communication
        logger.debug("[%s] Getting running identifier for '%s'", self.name, s_link.name)
        # Assume the daemon should be alive and reachable
        # because we are initializing the connection...
        s_link.alive = True
        s_link.reachable = True
        got_a_running_id = None
        for _ in range(0, s_link.max_check_attempts):
            got_a_running_id = s_link.get_running_id()
            if got_a_running_id:
                s_link.last_connection = time.time()
                if set_wait_new_conf:
                    s_link.wait_new_conf()
                break
            time.sleep(0.3)

        return got_a_running_id

    def setup_new_conf(self):
        """Setup the new configuration received from Arbiter
        :return: None
        """
        raise NotImplementedError()

    def do_loop_turn(self):
        """Abstract method for daemon loop turn.
        It must be overridden by all classes inheriting from Daemon

        :return: None
        """
        raise NotImplementedError()

    def do_before_loop(self):  # pylint: disable=no-self-use
        """Called before the main daemon loop.

        :return: None
        """
        logger.debug("Nothing to do before the main loop")

    def do_main_loop(self):
        # pylint: disable=too-many-branches, too-many-statements, too-many-locals
        """Main loop for an Alignak daemon

        :return: None
        """
        # Increased on each loop turn
        if self.loop_count is None:
            self.loop_count = 0

        # Daemon start timestamp
        if self.start_time is None:
            self.start_time = time.time()

        # For the pause duration
        logger.info("pause duration: %.2f", self.pause_duration)

        # For the maximum expected loop duration
        logger.info("maximum expected loop duration: %.2f", self.maximum_loop_duration)

        # Treatments before starting the main loop...
        self.do_before_loop()

        elapsed_time = 0

        logger.info("starting main loop: %.2f", self.start_time)
        while not self.interrupted:
            loop_start_ts = time.time()

            # Maybe someone said we will stop...
            if self.will_stop and not self.type == 'arbiter':
                logger.debug("death-wait mode... waiting for death")
                _, _ = self.make_a_pause(1.0)
                continue

            # Increment loop count
            self.loop_count += 1
            if self.log_loop:
                logger.debug("--- %d", self.loop_count)

            # Maybe the arbiter pushed a new configuration...
            if self.watch_for_new_conf(timeout=0.05):
                logger.info("I got a new configuration...")
                # Manage the new configuration
                self.setup_new_conf()

            # Trying to restore our related daemons lost connections
            for satellite in list(self.get_links_of_type(s_type='').values()):
                # Not for configuration disabled satellites
                if not satellite.active:
                    continue
                if not satellite.alive and not satellite.passive:
                    logger.info("Trying to restore connection for %s/%s...",
                                satellite.type, satellite.name)
                    if self.daemon_connection_init(satellite):
                        logger.info("Connection restored")

            # Each loop turn, execute the daemon specific treatment...
            # only if the daemon has a configuration to manage
            if self.have_conf:
                _ts = time.time()
                self.do_loop_turn()
                statsmgr.timer('loop-turn', time.time() - _ts)
            else:
                logger.info("+++ loop %d, I do not have a configuration", self.loop_count)

            if self.daemon_monitoring and (self.loop_count % self.daemon_monitoring_period == 1):
                perfdatas = []
                my_process = psutil.Process()
                with my_process.oneshot():
                    perfdatas.append("num_threads=%d" % my_process.num_threads())
                    statsmgr.counter("system.num_threads", my_process.num_threads())
                    # perfdatas.append("num_ctx_switches=%d" % my_process.num_ctx_switches())
                    perfdatas.append("num_fds=%d" % my_process.num_fds())
                    statsmgr.counter("system.num_fds", my_process.num_fds())
                    # perfdatas.append("num_handles=%d" % my_process.num_handles())
                    perfdatas.append("create_time=%d" % my_process.create_time())
                    perfdatas.append("cpu_num=%d" % my_process.cpu_num())
                    statsmgr.counter("system.cpu_num", my_process.cpu_num())
                    perfdatas.append("cpu_usable=%d" % len(my_process.cpu_affinity()))
                    statsmgr.counter("system.cpu_usable", len(my_process.cpu_affinity()))
                    perfdatas.append("cpu_percent=%.2f%%" % my_process.cpu_percent())
                    statsmgr.counter("system.cpu_percent", my_process.cpu_percent())

                    cpu_times_percent = my_process.cpu_times()
                    for key in cpu_times_percent._fields:
                        perfdatas.append("cpu_%s_time=%.2fs" % (key,
                                                                getattr(cpu_times_percent, key)))
                        statsmgr.counter("system.cpu_%s_time" % key,
                                         getattr(cpu_times_percent, key))

                    memory = my_process.memory_full_info()
                    for key in memory._fields:
                        perfdatas.append("mem_%s=%db" % (key, getattr(memory, key)))
                        statsmgr.counter("system.mem_%s" % key, getattr(memory, key))

                    logger.debug("Daemon %s (%s), pid=%s, ppid=%s, status=%s, cpu/memory|%s",
                                 self.name, my_process.name(), my_process.pid, my_process.ppid(),
                                 my_process.status(), " ".join(perfdatas))

            if self.activity_log_period and (self.loop_count % self.activity_log_period == 1):
                logger.info("Daemon %s is living: loop #%s ;)", self.name, self.loop_count)

            # Maybe the arbiter pushed a new configuration...
            if self.watch_for_new_conf(timeout=0.05):
                logger.warning("The arbiter pushed a new configuration... ")

            # Loop end
            loop_end_ts = time.time()
            loop_duration = loop_end_ts - loop_start_ts

            pause = self.maximum_loop_duration - loop_duration
            if loop_duration > self.maximum_loop_duration:
                logger.warning("The %s %s loop exceeded the maximum expected loop duration (%.2f). "
                               "The last loop needed %.2f seconds to execute. "
                               "You should try to reduce the load on this %s.",
                               self.type, self.name, self.maximum_loop_duration,
                               loop_duration, self.type)
                # Make a very very short pause ...
                pause = 0.01

            # Pause the daemon execution to avoid too much load on the system
            logger.debug("Before pause: timeout: %s", pause)
            work, time_changed = self.make_a_pause(pause)
            logger.debug("After pause: %.2f / %.2f, sleep time: %.2f",
                         work, time_changed, self.sleep_time)
            if work > self.pause_duration:
                logger.warning("Too much work during the pause (%.2f out of %.2f)! "
                               "The daemon should rest for a while... but one need to change "
                               "its code for this. Please log an issue in the project repository!",
                               work, self.pause_duration)
                # self.pause_duration += 0.1
            statsmgr.timer('sleep-time', self.sleep_time)
            self.sleep_time = 0.0

            # And now, the whole average time spent
            elapsed_time = loop_end_ts - self.start_time
            if self.log_loop:
                logger.debug("Elapsed time, current loop: %.2f, from start: %.2f (%d loops)",
                             loop_duration, elapsed_time, self.loop_count)
            statsmgr.gauge('loop-count', self.loop_count)
            statsmgr.timer('run-duration', elapsed_time)

            # Maybe someone said we will stop...
            if self.will_stop:
                if self.type == 'arbiter':
                    self.will_stop = False
                else:
                    logger.info("The arbiter said we will stop soon - go to death-wait mode")

            # Maybe someone asked us to die, if so, do it :)
            if self.interrupted:
                logger.info("Someone asked us to stop now")
                continue

            # If someone asked us a configuration reloading
            if self.need_config_reload and self.type == 'arbiter':
                logger.warning("Someone requested a configuration reload")
                logger.info("Exiting daemon main loop")
                return

            # If someone asked us to dump memory, do it
            if self.need_dump_environment:
                logger.debug('Dumping memory')
                self.dump_environment()
                self.need_dump_environment = False
        logger.info("stopped main loop: %.2f", time.time())

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
            for msg in self.modules_manager.configuration_warnings:
                logger.warning(msg)
        statsmgr.gauge('modules.count', len(modules))
        statsmgr.timer('modules.load-time', time.time() - _ts)

    def add(self, elt):
        """ Abstract method for adding brok, external commands, messages, ...
         It is overridden in subclasses (Satellite) of Daemon

        :param elt: element to add
        :type elt:
        :return: None
        """
        pass

    def dump_environment(self):
        """ Try to dump memory

        Not currently implemented feature

        :return: None
        """
        # Dump the Alignak configuration to a temporary ini file
        path = os.path.join(tempfile.gettempdir(),
                            'dump-env-%s-%s-%d.ini' % (self.type, self.name, int(time.time())))

        try:
            with open(path, "w") as out_file:
                self.alignak_env.write(out_file)
        except Exception as exp:  # pylint: disable=broad-except
            logger.error("Dumping daemon environment raised an error: %s. ", exp)

    def load_modules_manager(self):
        """Instantiate the daemon ModulesManager and load the SyncManager (multiprocessing)

        :param daemon_name: daemon name
        :type elt: str
        :return: None
        """
        self.modules_manager = ModulesManager(self)

    def change_to_workdir(self):
        """Change working directory to working attribute

        :return: None
        """
        logger.info("Changing working directory to: %s", self.workdir)

        self.check_dir(self.workdir)
        try:
            os.chdir(self.workdir)
        except OSError as exp:
            self.exit_on_error("Error changing to working directory: %s. Error: %s. "
                               "Check the existence of %s and the %s/%s account "
                               "permissions on this directory."
                               % (self.workdir, str(exp), self.workdir, self.user, self.group),
                               exit_code=3)
        self.pre_log.append(("INFO", "Using working directory: %s" % os.path.abspath(self.workdir)))

    def unlink(self):
        """Remove the daemon's pid file

        :return: None
        """
        logger.debug("Unlinking %s", self.pid_filename)
        try:
            os.unlink(self.pid_filename)
        except OSError as exp:
            logger.debug("Got an error unlinking our pid file: %s", exp)

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
                print("The directory %s is not writable or readable."
                      "Please make it read writable: %s" % (shm_path, shm_path))
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
        except Exception as exp:  # pylint: disable=broad-except
            self.exit_on_error("Error opening pid file: %s. Error: %s. "
                               "Check the %s:%s account permissions to write this file."
                               % (self.pid_filename, str(exp), self.user, self.group), exit_code=3)

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
            logger.warning("PID file is empty or has an invalid content: %s", self.pid_filename)
            return

        if pid == os.getpid():
            self.pid = pid
            return

        try:
            logger.debug("Testing if the process is running: '%s'", pid)
            os.kill(pid, 0)
        except OSError:
            # consider any exception as a stale pid file.
            # this includes :
            #  * PermissionError when a process with same pid exists but is executed by another user
            #  * ProcessLookupError: [Errno 3] No such process
            self.pre_log.append(("DEBUG", "No former instance to replace"))
            logger.info("A stale pid file exists, reusing the same file")
            return

        if not self.do_replace:
            self.exit_on_error("A valid pid file still exists (pid=%s) and "
                               "I am not allowed to replace. Exiting!" % pid, exit_code=3)

        self.pre_log.append(("DEBUG", "Replacing former instance: %d" % pid))
        try:
            pgid = os.getpgid(pid)
            # SIGQUIT to terminate and dump core
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

    def write_pid(self, pid):
        """ Write pid to the pid file

        :param pid: pid of the process
        :type pid: None | int
        :return: None
        """
        self.fpid.seek(0)
        self.fpid.truncate()
        self.fpid.write("%d" % pid)
        self.fpid.close()
        del self.fpid  # no longer needed

    def close_fds(self, skip_close_fds):  # pragma: no cover, not with unit tests...
        """Close all the process file descriptors.
        Skip the descriptors present in the skip_close_fds list

        :param skip_close_fds: list of file descriptor to preserve from closing
        :type skip_close_fds: list
        :return: None
        """
        # First we manage the file descriptor, because debug file can be
        # relative to pwd
        max_fds = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if max_fds == resource.RLIM_INFINITY:
            max_fds = 1024
        self.pre_log.append(("DEBUG", "Maximum file descriptors: %d" % max_fds))

        # Iterate through and close all file descriptors.
        for file_d in range(0, max_fds):
            if file_d in skip_close_fds:
                self.pre_log.append(("INFO", "Do not close fd: %s" % file_d))
                continue
            try:
                os.close(file_d)
            except OSError:  # ERROR, fd wasn't open to begin with (ignored)
                pass

    def daemonize(self):  # pragma: no cover, not for unit tests...
        """Go in "daemon" mode: close unused fds, redirect stdout/err,
        chdir, umask, fork-setsid-fork-writepid
        Do the double fork to properly go daemon

        This is 'almost' as recommended by PEP3143 but it would be better to rewrite this
        daemonization thanks to the python-daemon library!

        :return: None
        """
        self.pre_log.append(("INFO", "Daemonizing..."))
        print("Daemonizing %s..." % self.name)

        # Set umask
        os.umask(UMASK)

        # Close all file descriptors except the one we need
        self.pre_log.append(("DEBUG", "Closing file descriptors..."))
        preserved_fds = [1, 2, self.fpid.fileno()]
        if os.getenv('ALIGNAK_DO_NOT_PRESERVE_STDOUT', None):
            preserved_fds = [self.fpid.fileno()]
        if self.debug:
            # Do not close stdout nor stderr
            preserved_fds.extend([1, 2])
        self.close_fds(preserved_fds)

        # Now the double fork magic (fork/setsid/fork)
        def fork_then_exit_parent(level, error_message):
            """ Fork a child process, then exit the parent process.
                :param error_message: Message for the exception in case of a
                    detach failure.
                :return: ``None``.
                :raise Exception: If the fork fails.
                """
            try:
                pid = os.fork()
                if pid > 0:
                    if level == 2:
                        # When forking the grandchild, write our own pid
                        self.write_pid(pid)
                    os._exit(0)
            except OSError as exc:
                raise Exception("Fork error: %s [%d], exception: %s"
                                % (error_message, exc.errno, str(exc)))

        fork_then_exit_parent(level=1, error_message="Failed first fork")
        os.setsid()
        fork_then_exit_parent(level=2, error_message="Failed second fork")

        self.pid = os.getpid()
        self.pre_log.append(("INFO", "We are now fully daemonized :) pid=%d" % self.pid))

        return True

    @staticmethod
    def _create_manager():
        """Instantiate and start a SyncManager

        :return: the manager
        :rtype: multiprocessing.managers.SyncManager
        """
        manager = SyncManager(('127.0.0.1', 0))
        manager.start()
        return manager

    def do_daemon_init_and_start(self, set_proc_title=True):
        """Main daemon function.
        Clean, allocates, initializes and starts all necessary resources to go in daemon mode.

        The set_proc_title parameter is mainly useful for the Alignak unit tests.
        This to avoid changing the test process name!

        :param set_proc_title: if set (default), the process title is changed to the daemon name
        :type set_proc_title: bool
        :return: False if the HTTP daemon can not be initialized, else True
        """
        if set_proc_title:
            self.set_proctitle(self.name)

        # Change to configured user/group account
        self.change_to_user_group()

        # Change the working directory
        self.change_to_workdir()

        # Check if I am still running
        self.check_parallel_run()

        # If we must daemonize, let's do it!
        if self.is_daemon:
            if not self.daemonize():
                logger.error("I could not daemonize myself :(")
                return False
        else:
            # Else, I set my own pid as the reference one
            self.write_pid(os.getpid())

        # # TODO: check if really necessary!
        # # -------
        # # Set ownership on some default log files. It may happen that these default
        # # files are owned by a privileged user account
        # try:
        #     for log_file in ['alignak.log', 'alignak-events.log']:
        #         if os.path.exists('/tmp/%s' % log_file):
        #             with open('/tmp/%s' % log_file, "w") as file_log_file:
        #                 os.fchown(file_log_file.fileno(), self.uid, self.gid)
        #         if os.path.exists('/tmp/monitoring-log/%s' % log_file):
        #             with open('/tmp/monitoring-log/%s' % log_file, "w") as file_log_file:
        #                 os.fchown(file_log_file.fileno(), self.uid, self.gid)
        # except Exception as exp:  # pylint: disable=broad-except
        #     #  pragma: no cover
        #     print("Could not set default log files ownership, exception: %s" % str(exp))

        # Configure the daemon logger
        self.setup_alignak_logger()

        # Setup the Web Services daemon
        if not self.setup_communication_daemon():
            logger.error("I could not setup my communication daemon :(")
            return False

        # Creating synchonisation manager (inter-daemon queues...)
        self.sync_manager = self._create_manager()

        # Setup our modules manager
        self.load_modules_manager()

        # Start the CherryPy server through a detached thread
        logger.info("Starting http_daemon thread")
        # pylint: disable=bad-thread-instantiation
        self.http_thread = threading.Thread(target=self.http_daemon_thread,
                                            name='%s-http_thread' % self.name)
        # Setting the thread as a daemon allows to Ctrl+C to kill the main daemon
        self.http_thread.daemon = True
        self.http_thread.start()
        # time.sleep(1)
        logger.info("HTTP daemon thread started")

        return True

    def setup_communication_daemon(self):
        # pylint: disable=no-member
        """ Setup HTTP server daemon to listen
        for incoming HTTP requests from other Alignak daemons

        :return: True if initialization is ok, else False
        """
        ca_cert = ssl_cert = ssl_key = server_dh = None

        # The SSL part
        if self.use_ssl:
            ssl_cert = os.path.abspath(self.server_cert)
            if not os.path.exists(ssl_cert):
                self.exit_on_error("The configured SSL server certificate file '%s' "
                                   "does not exist." % ssl_cert, exit_code=2)
            logger.info("Using SSL server certificate: %s", ssl_cert)

            ssl_key = os.path.abspath(self.server_key)
            if not os.path.exists(ssl_key):
                self.exit_on_error("The configured SSL server key file '%s' "
                                   "does not exist." % ssl_key, exit_code=2)
            logger.info("Using SSL server key: %s", ssl_key)

            if self.server_dh:
                server_dh = os.path.abspath(self.server_dh)
                logger.info("Using ssl dh cert file: %s", server_dh)
                self.exit_on_error("Sorry, but using a DH configuration "
                                   "is not currently supported!", exit_code=2)

            if self.ca_cert:
                ca_cert = os.path.abspath(self.ca_cert)
                logger.info("Using ssl ca cert file: %s", ca_cert)

            if self.hard_ssl_name_check:
                logger.info("Enabling hard SSL server name verification")

        # Let's create the HTTPDaemon, it will be started later
        # pylint: disable=E1101
        try:
            logger.info('Setting up HTTP daemon (%s:%d), %d threads',
                        self.host, self.port, self.thread_pool_size)
            self.http_daemon = HTTPDaemon(self.host, self.port, self.http_interface,
                                          self.use_ssl, ca_cert, ssl_key,
                                          ssl_cert, server_dh, self.thread_pool_size,
                                          self.log_cherrypy, self.favicon)
        except PortNotFree:
            logger.error('The HTTP daemon port (%s:%d) is not free...', self.host, self.port)
            return False

        except Exception as exp:  # pylint: disable=broad-except
            print('Setting up HTTP daemon, exception: %s', str(exp))
            logger.exception('Setting up HTTP daemon, exception: %s', str(exp))
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

    def change_to_user_group(self):
        """ Change to configured user/group for the running program.
        If user/group are not valid, we exit with code 1
        If change failed we exit with code 2

        :return: None
        """
        # TODO: change user on nt
        if os.name == 'nt':  # pragma: no cover, no Windows implementation currently
            logger.warning("You can't change user on this system")
            return

        if (self.user == 'root' or self.group == 'root') and not self.idontcareaboutsecurity:
            logger.error("You want the application to run with the root account credentials? "
                         "It is not a safe configuration!")
            logger.error("If you really want it, set: 'idontcareaboutsecurity=1' "
                         "in the configuration file")
            self.exit_on_error("You want the application to run with the root account credentials? "
                               "It is not a safe configuration! If you really want it, "
                               "set: 'idontcareaboutsecurity=1' in the configuration file.",
                               exit_code=3)

        uid = None
        try:
            uid = getpwnam(self.user).pw_uid
        except KeyError:
            logger.error("The required user %s is unknown", self.user)

        gid = None
        try:
            gid = getgrnam(self.group).gr_gid
        except KeyError:
            logger.error("The required group %s is unknown", self.group)

        if uid is None or gid is None:
            self.exit_on_error("Configured user/group (%s/%s) are not valid."
                               % (self.user, self.group), exit_code=1)

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
            self.exit_on_error("Cannot change user/group to %s/%s (%s [%d]). Exiting..."
                               % (self.user, self.group, err.strerror, err.errno), exit_code=3)

    def manage_signal(self, sig, frame):  # pylint: disable=unused-argument
        """Manage signals caught by the daemon
        signal.SIGUSR1 : dump_environment
        signal.SIGUSR2 : dump_object (nothing)
        signal.SIGTERM, signal.SIGINT : terminate process

        :param sig: signal caught by daemon
        :type sig: str
        :param frame: current stack frame
        :type frame:
        :return: None
        """
        logger.info("received a signal: %s", SIGNALS_TO_NAMES_DICT[sig])
        if sig == signal.SIGUSR1:  # if USR1, ask a memory dump
            self.need_dump_environment = True
        elif sig == signal.SIGUSR2:  # if USR2, ask objects dump
            self.need_objects_dump = True
        elif sig == signal.SIGHUP:  # if HUP, reload the monitoring configuration
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
        if sigs is None:
            sigs = (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGUSR2, signal.SIGHUP)

        func = self.manage_signal
        if os.name == "nt":  # pragma: no cover, no Windows implementation currently
            try:
                import win32api
                win32api.SetConsoleCtrlHandler(func, True)
            except ImportError:
                version = ".".join([str(i) for i in sys.version_info[:2]])
                raise Exception("pywin32 not installed for Python " + version)
        else:
            # Only some signals are managed...
            for sig in sigs:
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

    def get_header(self, configuration=False):
        """Get the log file header

        If configuration is True, this returns the daemon configuration

        :return: A string list containing project name, daemon name, version, licence etc.
        :rtype: list
        """
        header = ["-----",
                  "Alignak %s - %s daemon" % (VERSION, self.name),
                  "Copyright (c) 2015-2018: Alignak Team",
                  "License: AGPL",
                  "-----",
                  "My pid: %s" % self.pid]

        if configuration:
            header = ["My configuration: "]
            for prop, _ in sorted(self.properties.items()):
                header.append(" - %s=%s" % (prop, getattr(self, prop)))

        return header

    def http_daemon_thread(self):
        """Main function of the http daemon thread will loop forever unless we stop the root daemon

        The main thing is to have a pool of X concurrent requests for the http_daemon,
        so "no_lock" calls can always be directly answer without having a "locked" version to
        finish. This is achieved thanks to the CherryPy thread pool.

        This function is threaded to be detached from the main process as such it will not block
        the process main loop..
        :return: None
        """
        logger.debug("HTTP thread running")
        try:
            # This function is a blocking function serving HTTP protocol
            self.http_daemon.run()
        except PortNotFree as exp:
            logger.exception('The HTTP daemon port is not free: %s', exp)
            raise
        except Exception as exp:  # pylint: disable=broad-except
            self.exit_on_exception(exp)
        logger.debug("HTTP thread exiting")

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
        """
        now = time.time()
        difference = now - self.t_each_loop

        # If we have more than 15 min time change, we need to compensate it
        # todo: confirm that 15 minutes is a good choice...
        if abs(difference) > 900:
            self.compensate_system_time_change(difference)
        else:
            difference = 0

        self.t_each_loop = now

        return difference

    def compensate_system_time_change(self, difference):
        # pylint: disable=no-self-use, no-member
        """Default action for system time change. Actually a log is done

        :param difference: in seconds
        :type difference: int

        :return: None
        """
        logger.warning('A system time change of %d seconds has been detected. Compensating...',
                       int(difference))

    def wait_for_initial_conf(self, timeout=1.0):
        """Wait initial configuration from the arbiter.
        Basically sleep 1.0 and check if new_conf is here

        :param timeout: timeout to wait
        :type timeout: int
        :return: None
        """
        logger.info("Waiting for initial configuration")
        # Arbiter do not already set our have_conf param
        _ts = time.time()
        while not self.new_conf and not self.interrupted:
            # Make a pause and check if the system time changed
            _, _ = self.make_a_pause(timeout, check_time_change=True)

        if not self.interrupted:
            logger.info("Got initial configuration, waited for: %.2f seconds", time.time() - _ts)
            statsmgr.timer('configuration.initial', time.time() - _ts)
        else:
            logger.info("Interrupted before getting the initial configuration")

    def wait_for_new_conf(self, timeout=1.0):
        """Wait for a new configuration from the arbiter.
        Basically the same as waiting for an initial configuration (wait_for_initial_conf)

        :param timeout: timeout to wait
        :type timeout: int
        :return: None
        """
        logger.info("Waiting for a new configuration")
        # Arbiter do not already set our have_conf param
        _ts = time.time()
        while not self.new_conf and not self.interrupted:
            # Make a pause and check if the system time changed
            _, _ = self.make_a_pause(timeout, check_time_change=True)

        if not self.interrupted:
            logger.info("Got the new configuration, waited for: %.2f", time.time() - _ts)
            statsmgr.timer('configuration.new', time.time() - _ts)
        else:
            logger.info("Interrupted before getting the new configuration")

    def watch_for_new_conf(self, timeout=0):
        """Check if a new configuration was sent to the daemon

        This function is called on each daemon loop turn. Basically it is a sleep...

        If a new configuration was posted, this function returns True

        :param timeout: timeout to wait. Default is no wait time.
        :type timeout: float
        :return: None
        """
        logger.debug("Watching for a new configuration, timeout: %s", timeout)
        self.make_a_pause(timeout=timeout, check_time_change=False)
        return any(self.new_conf)

    def hook_point(self, hook_name, handle=None):
        """Used to call module function that may define a hook function for hook_name

        Available hook points:
        - `tick`, called on each daemon loop turn
        - `save_retention`; called by the scheduler when live state
            saving is to be done
        - `load_retention`; called by the scheduler when live state
            restoring is necessary (on restart)
        - `get_new_actions`; called by the scheduler before adding the actions to be executed
        - `early_configuration`; called by the arbiter when it begins parsing the configuration
        - `read_configuration`; called by the arbiter when it read the configuration
        - `late_configuration`; called by the arbiter when it finishes parsing the configuration

        As a default, the `handle` parameter provided to the hooked function is the
        caller Daemon object. The scheduler will provide its own instance when it call this
        function.

        :param hook_name: function name we may hook in module
        :type hook_name: str
        :param handle: parameter to provide to the hook function
        :type: handle: alignak.Satellite
        :return: None
        """
        full_hook_name = 'hook_' + hook_name
        for module in self.modules_manager.instances:
            _ts = time.time()
            if not hasattr(module, full_hook_name):
                continue

            fun = getattr(module, full_hook_name)
            try:
                fun(handle if handle is not None else self)
            # pylint: disable=broad-except
            except Exception as exp:  # pragma: no cover, never happen during unit tests...
                logger.warning('The instance %s raised an exception %s. I disabled it,'
                               ' and set it to restart later', module.name, str(exp))
                logger.exception('Exception %s', exp)
                self.modules_manager.set_to_restart(module)
            else:
                statsmgr.timer('hook.%s.%s' % (hook_name, module.name), time.time() - _ts)

    def get_retention_data(self):  # pylint: disable=no-self-use
        """Basic function to get retention data,
        Maybe be overridden by subclasses to implement real get

        TODO: only the scheduler is retention capable. To be removed!

        :return: A list of Alignak object (scheduling items)
        :rtype: list
        """
        return []

    def restore_retention_data(self, data):
        """Basic function to save retention data,
        Maybe be overridden by subclasses to implement real save

        TODO: only the scheduler is retention capable. To be removed!

        :return: None
        """
        pass

    def get_id(self, details=False):  # pylint: disable=unused-argument
        """Get daemon identification information

        :return: A dict with the following structure
        ::
            {
                "alignak": selfAlignak instance name
                "type": daemon type
                "name": daemon name
                "version": Alignak version
            }

        :rtype: dict
        """
        # Modules information
        res = {
            "alignak": getattr(self, 'alignak_name', 'unknown'),
            "type": getattr(self, 'type', 'unknown'),
            "name": getattr(self, 'name', 'unknown'),
            "version": VERSION
        }
        return res

    def get_daemon_stats(self, details=False):  # pylint: disable=unused-argument
        """Get state of modules and create a scheme for stats data of daemon
        This may be overridden in subclasses (and it is...)

        :return: A dict with the following structure
        ::
            {
                'modules': {
                    'internal': {'name': "MYMODULE1", 'state': 'ok'},
                    'external': {'name': "MYMODULE2", 'state': 'stopped'},
                },
                And some extra information, see the source code below...
            }

        These information are completed with the data provided by the get_id function
        which provides the daemon identification

        :rtype: dict
        """
        res = self.get_id()
        res.update({
            "program_start": self.program_start,
            "spare": self.spare,
            'counters': {},
            'metrics': [],
            'modules': {
                'internal': {}, 'external': {}
            }
        })

        # Modules information
        modules = res['modules']
        counters = res['counters']
        counters['modules'] = len(self.modules_manager.instances)
        # first get data for all internal modules
        for instance in self.modules_manager.get_internal_instances():
            state = {True: 'ok', False: 'stopped'}[(instance
                                                    not in self.modules_manager.to_restart)]
            modules['internal'][instance.name] = {'name': instance.name, 'state': state}
        # Same but for external ones
        for instance in self.modules_manager.get_external_instances():
            state = {True: 'ok', False: 'stopped'}[(instance
                                                    not in self.modules_manager.to_restart)]
            modules['internal'][instance.name] = {'name': instance.name, 'state': state}

        return res

    def exit_ok(self, message, exit_code=None):
        """Log a message and exit

        :param exit_code: if not None, exit with the provided value as exit code
        :type exit_code: int
        :param message: message for the exit reason
        :type message: str
        :return: None
        """
        logger.info("Exiting...")
        if message:
            logger.info("-----")
            logger.error("Exit message: %s", message)
            logger.info("-----")

        self.request_stop()

        if exit_code is not None:
            exit(exit_code)

    def exit_on_error(self, message, exit_code=1):
        # pylint: disable=no-self-use
        """Log generic message when getting an error and exit

        :param exit_code: if not None, exit with the provided value as exit code
        :type exit_code: int
        :param message: message for the exit reason
        :type message: str
        :return: None
        """
        log = "I got an unrecoverable error. I have to exit."
        if message:
            log += "\n-----\nError message: %s" % message
            print("Error message: %s" % message)
        log += "-----\n"
        log += "You can get help at https://github.com/Alignak-monitoring/alignak\n"
        log += "If you think this is a bug, create a new issue including as much " \
               "details as possible (version, configuration,...)"
        if exit_code is not None:
            exit(exit_code)

    def exit_on_exception(self, raised_exception, message='', exit_code=99):
        """Log generic message when getting an unrecoverable error

        :param raised_exception: raised Exception
        :type raised_exception: Exception
        :param message: message for the exit reason
        :type message: str
        :param exit_code: exit with the provided value as exit code
        :type exit_code: int
        :return: None
        """
        self.exit_on_error(message=message, exit_code=None)

        logger.critical("-----\nException: %s\nBack trace of the error:\n%s",
                        str(raised_exception), traceback.format_exc())

        exit(exit_code)

    def get_objects_from_from_queues(self):
        """ Get objects from "from" queues and add them.

        :return: True if we got something in the queue, False otherwise.
        :rtype: bool
        """
        _t0 = time.time()
        had_some_objects = False
        for module in self.modules_manager.get_external_instances():
            queue = module.from_q
            if not queue:
                continue
            while True:
                queue_size = queue.qsize()
                if queue_size:
                    statsmgr.gauge('queues.from.%s.count' % module.get_name(), queue_size)
                try:
                    obj = queue.get_nowait()
                except Full:
                    logger.warning("Module %s from queue is full", module.get_name())
                except Empty:
                    break
                except (IOError, EOFError) as exp:
                    logger.warning("Module %s from queue is no more available: %s",
                                   module.get_name(), str(exp))
                except Exception as exp:  # pylint: disable=broad-except
                    logger.error("An external module queue got a problem '%s'", str(exp))
                else:
                    had_some_objects = True
                    self.add(obj)
        statsmgr.timer('queues.time', time.time() - _t0)

        return had_some_objects

    def setup_alignak_logger(self):
        """ Setup alignak logger:
        - with the daemon log configuration properties
        - configure the global daemon handler (root logger)
        - log the daemon Alignak header

        - configure the global Alignak monitoring log

        This function is called very early on daemon start. The daemon is not yet forked and
        may still run with a high privileged user account. This is why, the log file ownership
        may be set accordingly to the running user account.

        :return: None
        """
        # Configure the daemon logger
        try:
            # Make sure that the log directory is existing
            self.check_dir(self.logdir)
            setup_logger(logger_configuration_file=self.logger_configuration,
                         log_dir=self.logdir, process_name=self.name,
                         log_file=self.log_filename)
            if self.debug:
                # Force the global logger at DEBUG level
                set_log_level('DEBUG')
                logger.info("-----")
                logger.info("Daemon log level set to a minimum of DEBUG")
                logger.info("-----")
            elif self.verbose:
                # Force the global logger at INFO level
                set_log_level('INFO')
                logger.info("-----")
                logger.info("Daemon log level set to a minimum of INFO")
                logger.info("-----")
        except Exception as exp:  # pylint: disable=broad-except
            print("***** %s - exception when setting-up the logger: %s" % (self.name, exp))
            self.exit_on_exception(exp, message="Logger configuration error!")

        logger.debug("Alignak daemon logger configured")

        for line in self.get_header():
            logger.info("- %s", line)

        # Log daemon configuration
        for line in self.get_header(configuration=True):
            logger.debug("- %s", line)

        # We can now output some previously silenced debug output
        if self.pre_log:
            logger.debug("--- Start - Log prior to our configuration:")
            for level, message in self.pre_log:
                fun_level = level.lower()
                getattr(logger, fun_level)("- %s", message)
                # if level.lower() == "debug":
                #     logger.debug(message)
                # elif level.lower() == "info":
                #     logger.info(message)
                # elif level.lower() == "warning":
                #     logger.warning(message)
            logger.debug("--- Stop - Log prior to our configuration")
