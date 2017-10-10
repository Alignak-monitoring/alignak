#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

"""
alignak-environment command line interface::

    Usage:
        alignak-environment [-h]
        alignak-environment [-v] <cfg_file>

    Options:
        -h, --help          Show this usage screen.
        -v, --verbose       Run in verbose mode (print information on the console output)

    Output:
        This script will parse the provided configuration file and it will output all the
        variables defined in this file as Linux/Unix shell export variables.

        As an example for a file as the default ./etc/alignak-realm2.ini, the script will output:
            export ALIGNAK_VERSION=1.0.0
            export ALIGNAK_CONFIGURATION_DIST_BIN=../alignak/bin
            export ALIGNAK_CONFIGURATION_DIST_ETC=../etc
            export ALIGNAK_CONFIGURATION_DIST_VAR=/tmp
            export ALIGNAK_CONFIGURATION_DIST_RUN=/tmp
            export ALIGNAK_CONFIGURATION_DIST_LOG=/tmp
            export ALIGNAK_CONFIGURATION_USER=alignak
            export ALIGNAK_CONFIGURATION_GROUP=alignak
            export ALIGNAK_CONFIGURATION_WORKDIR=/tmp
            export ALIGNAK_CONFIGURATION_LOGDIR=/tmp
            export ALIGNAK_CONFIGURATION_ETCDIR=../etc
            export ALIGNAK_CONFIGURATION_USE_SSL=0
            export ALIGNAK_CONFIGURATION_HARD_SSL_NAME_CHECK=0
            export ALIGNAK_CONFIGURATION_CA_CERT=../etc/certs/ca.pem
            export ALIGNAK_CONFIGURATION_SERVER_CERT=../etc/certs/server.crt
            export ALIGNAK_CONFIGURATION_SERVER_KEY=../etc/certs/server.key
            export ALIGNAK_CONFIGURATION_SERVER_DH=../etc/certs/server.pem
            export ALIGNAK_CONFIGURATION_NAME=daemon
            export ALIGNAK_CONFIGURATION_PORT=10000
            export ALIGNAK_CONFIGURATION_PIDFILE=/tmp/daemon.pid
            export ALIGNAK_CONFIGURATION_LOCAL_LOG=/tmp/daemon.log
            export ALIGNAK_CONFIGURATION_MAX_QUEUE_SIZE=0
            export ALIGNAK_CONFIGURATION_CFG=../etc/alignak.cfg
            export ALIGNAK_CONFIGURATION_CFG2=''
            export DAEMON_ARBITER_MASTER_DIST_BIN=../alignak/bin
            export DAEMON_ARBITER_MASTER_DIST_ETC=../etc
            export DAEMON_ARBITER_MASTER_DIST_VAR=/tmp
            export DAEMON_ARBITER_MASTER_DIST_RUN=/tmp
            export DAEMON_ARBITER_MASTER_DIST_LOG=/tmp
            export DAEMON_ARBITER_MASTER_USER=alignak
            export DAEMON_ARBITER_MASTER_GROUP=alignak
            export DAEMON_ARBITER_MASTER_WORKDIR=/tmp
            export DAEMON_ARBITER_MASTER_LOGDIR=/tmp
            export DAEMON_ARBITER_MASTER_ETCDIR=../etc
            export DAEMON_ARBITER_MASTER_USE_SSL=0
            export DAEMON_ARBITER_MASTER_HARD_SSL_NAME_CHECK=0
            export DAEMON_ARBITER_MASTER_CA_CERT=../etc/certs/ca.pem
            export DAEMON_ARBITER_MASTER_SERVER_CERT=../etc/certs/server.crt
            export DAEMON_ARBITER_MASTER_SERVER_KEY=../etc/certs/server.key
            export DAEMON_ARBITER_MASTER_SERVER_DH=../etc/certs/server.pem
            export DAEMON_ARBITER_MASTER_NAME=arbiter-master
            export DAEMON_ARBITER_MASTER_PORT=7770
            export DAEMON_ARBITER_MASTER_PIDFILE=/tmp/arbiter-master.pid
            export DAEMON_ARBITER_MASTER_LOCAL_LOG=/tmp/arbiter-master.log
            export DAEMON_ARBITER_MASTER_MAX_QUEUE_SIZE=0
            export DAEMON_ARBITER_MASTER_DAEMON=alignak-arbiter
            export DAEMON_SCHEDULER_MASTER_DIST_BIN=../alignak/bin
            export DAEMON_SCHEDULER_MASTER_DIST_ETC=../etc
            export DAEMON_SCHEDULER_MASTER_DIST_VAR=/tmp
            export DAEMON_SCHEDULER_MASTER_DIST_RUN=/tmp
            export DAEMON_SCHEDULER_MASTER_DIST_LOG=/tmp
            export DAEMON_SCHEDULER_MASTER_USER=alignak
            export DAEMON_SCHEDULER_MASTER_GROUP=alignak
            export DAEMON_SCHEDULER_MASTER_WORKDIR=/tmp
            export DAEMON_SCHEDULER_MASTER_LOGDIR=/tmp
            export DAEMON_SCHEDULER_MASTER_ETCDIR=../etc
            export DAEMON_SCHEDULER_MASTER_USE_SSL=0
            export DAEMON_SCHEDULER_MASTER_HARD_SSL_NAME_CHECK=0
            export DAEMON_SCHEDULER_MASTER_CA_CERT=../etc/certs/ca.pem
            export DAEMON_SCHEDULER_MASTER_SERVER_CERT=../etc/certs/server.crt
            export DAEMON_SCHEDULER_MASTER_SERVER_KEY=../etc/certs/server.key
            export DAEMON_SCHEDULER_MASTER_SERVER_DH=../etc/certs/server.pem
            export DAEMON_SCHEDULER_MASTER_NAME=scheduler-master
            export DAEMON_SCHEDULER_MASTER_PORT=7768
            export DAEMON_SCHEDULER_MASTER_PIDFILE=/tmp/scheduler-master.pid
            export DAEMON_SCHEDULER_MASTER_LOCAL_LOG=/tmp/scheduler-master.log
            export DAEMON_SCHEDULER_MASTER_MAX_QUEUE_SIZE=0
            export DAEMON_SCHEDULER_MASTER_DAEMON=alignak-scheduler
            export DAEMON_POLLER_MASTER_DIST_BIN=../alignak/bin
            export DAEMON_POLLER_MASTER_DIST_ETC=../etc
            export DAEMON_POLLER_MASTER_DIST_VAR=/tmp
            export DAEMON_POLLER_MASTER_DIST_RUN=/tmp
            export DAEMON_POLLER_MASTER_DIST_LOG=/tmp
            export DAEMON_POLLER_MASTER_USER=alignak
            export DAEMON_POLLER_MASTER_GROUP=alignak
            export DAEMON_POLLER_MASTER_WORKDIR=/tmp
            export DAEMON_POLLER_MASTER_LOGDIR=/tmp
            export DAEMON_POLLER_MASTER_ETCDIR=../etc
            export DAEMON_POLLER_MASTER_USE_SSL=0
            export DAEMON_POLLER_MASTER_HARD_SSL_NAME_CHECK=0
            export DAEMON_POLLER_MASTER_CA_CERT=../etc/certs/ca.pem
            export DAEMON_POLLER_MASTER_SERVER_CERT=../etc/certs/server.crt
            export DAEMON_POLLER_MASTER_SERVER_KEY=../etc/certs/server.key
            export DAEMON_POLLER_MASTER_SERVER_DH=../etc/certs/server.pem
            export DAEMON_POLLER_MASTER_NAME=poller-master
            export DAEMON_POLLER_MASTER_PORT=7771
            export DAEMON_POLLER_MASTER_PIDFILE=/tmp/poller-master.pid
            export DAEMON_POLLER_MASTER_LOCAL_LOG=/tmp/poller-master.log
            export DAEMON_POLLER_MASTER_MAX_QUEUE_SIZE=0
            export DAEMON_POLLER_MASTER_DAEMON=alignak-poller
            export DAEMON_REACTIONNER_MASTER_DIST_BIN=../alignak/bin
            export DAEMON_REACTIONNER_MASTER_DIST_ETC=../etc
            export DAEMON_REACTIONNER_MASTER_DIST_VAR=/tmp
            export DAEMON_REACTIONNER_MASTER_DIST_RUN=/tmp
            export DAEMON_REACTIONNER_MASTER_DIST_LOG=/tmp
            export DAEMON_REACTIONNER_MASTER_USER=alignak
            export DAEMON_REACTIONNER_MASTER_GROUP=alignak
            export DAEMON_REACTIONNER_MASTER_WORKDIR=/tmp
            export DAEMON_REACTIONNER_MASTER_LOGDIR=/tmp
            export DAEMON_REACTIONNER_MASTER_ETCDIR=../etc
            export DAEMON_REACTIONNER_MASTER_USE_SSL=0
            export DAEMON_REACTIONNER_MASTER_HARD_SSL_NAME_CHECK=0
            export DAEMON_REACTIONNER_MASTER_CA_CERT=../etc/certs/ca.pem
            export DAEMON_REACTIONNER_MASTER_SERVER_CERT=../etc/certs/server.crt
            export DAEMON_REACTIONNER_MASTER_SERVER_KEY=../etc/certs/server.key
            export DAEMON_REACTIONNER_MASTER_SERVER_DH=../etc/certs/server.pem
            export DAEMON_REACTIONNER_MASTER_NAME=reactionner-master
            export DAEMON_REACTIONNER_MASTER_PORT=7769
            export DAEMON_REACTIONNER_MASTER_PIDFILE=/tmp/reactionner-master.pid
            export DAEMON_REACTIONNER_MASTER_LOCAL_LOG=/tmp/reactionner-master.log
            export DAEMON_REACTIONNER_MASTER_MAX_QUEUE_SIZE=0
            export DAEMON_REACTIONNER_MASTER_DAEMON=alignak-reactionner
            export DAEMON_BROKER_MASTER_DIST_BIN=../alignak/bin
            export DAEMON_BROKER_MASTER_DIST_ETC=../etc
            export DAEMON_BROKER_MASTER_DIST_VAR=/tmp
            export DAEMON_BROKER_MASTER_DIST_RUN=/tmp
            export DAEMON_BROKER_MASTER_DIST_LOG=/tmp
            export DAEMON_BROKER_MASTER_USER=alignak
            export DAEMON_BROKER_MASTER_GROUP=alignak
            export DAEMON_BROKER_MASTER_WORKDIR=/tmp
            export DAEMON_BROKER_MASTER_LOGDIR=/tmp
            export DAEMON_BROKER_MASTER_ETCDIR=../etc
            export DAEMON_BROKER_MASTER_USE_SSL=0
            export DAEMON_BROKER_MASTER_HARD_SSL_NAME_CHECK=0
            export DAEMON_BROKER_MASTER_CA_CERT=../etc/certs/ca.pem
            export DAEMON_BROKER_MASTER_SERVER_CERT=../etc/certs/server.crt
            export DAEMON_BROKER_MASTER_SERVER_KEY=../etc/certs/server.key
            export DAEMON_BROKER_MASTER_SERVER_DH=../etc/certs/server.pem
            export DAEMON_BROKER_MASTER_NAME=broker-master
            export DAEMON_BROKER_MASTER_PORT=7772
            export DAEMON_BROKER_MASTER_PIDFILE=/tmp/broker-master.pid
            export DAEMON_BROKER_MASTER_LOCAL_LOG=/tmp/broker-master.log
            export DAEMON_BROKER_MASTER_MAX_QUEUE_SIZE=100000
            export DAEMON_BROKER_MASTER_DAEMON=alignak-broker
            export DAEMON_RECEIVER_MASTER_DIST_BIN=../alignak/bin
            export DAEMON_RECEIVER_MASTER_DIST_ETC=../etc
            export DAEMON_RECEIVER_MASTER_DIST_VAR=/tmp
            export DAEMON_RECEIVER_MASTER_DIST_RUN=/tmp
            export DAEMON_RECEIVER_MASTER_DIST_LOG=/tmp
            export DAEMON_RECEIVER_MASTER_USER=alignak
            export DAEMON_RECEIVER_MASTER_GROUP=alignak
            export DAEMON_RECEIVER_MASTER_WORKDIR=/tmp
            export DAEMON_RECEIVER_MASTER_LOGDIR=/tmp
            export DAEMON_RECEIVER_MASTER_ETCDIR=../etc
            export DAEMON_RECEIVER_MASTER_USE_SSL=0
            export DAEMON_RECEIVER_MASTER_HARD_SSL_NAME_CHECK=0
            export DAEMON_RECEIVER_MASTER_CA_CERT=../etc/certs/ca.pem
            export DAEMON_RECEIVER_MASTER_SERVER_CERT=../etc/certs/server.crt
            export DAEMON_RECEIVER_MASTER_SERVER_KEY=../etc/certs/server.key
            export DAEMON_RECEIVER_MASTER_SERVER_DH=../etc/certs/server.pem
            export DAEMON_RECEIVER_MASTER_NAME=receiver-master
            export DAEMON_RECEIVER_MASTER_PORT=7773
            export DAEMON_RECEIVER_MASTER_PIDFILE=/tmp/receiver-master.pid
            export DAEMON_RECEIVER_MASTER_LOCAL_LOG=/tmp/receiver-master.log
            export DAEMON_RECEIVER_MASTER_MAX_QUEUE_SIZE=0
            export DAEMON_RECEIVER_MASTER_DAEMON=alignak-receiver
            export MODULE_BACKEND_ARBITER_DIST_BIN=../alignak/bin
            export MODULE_BACKEND_ARBITER_DIST_ETC=../etc
            export MODULE_BACKEND_ARBITER_DIST_VAR=/tmp
            export MODULE_BACKEND_ARBITER_DIST_RUN=/tmp
            export MODULE_BACKEND_ARBITER_DIST_LOG=/tmp
            export MODULE_BACKEND_ARBITER_USER=alignak
            export MODULE_BACKEND_ARBITER_GROUP=alignak
            export MODULE_BACKEND_ARBITER_WORKDIR=/tmp
            export MODULE_BACKEND_ARBITER_LOGDIR=/tmp
            export MODULE_BACKEND_ARBITER_ETCDIR=../etc
            export MODULE_BACKEND_ARBITER_USE_SSL=0
            export MODULE_BACKEND_ARBITER_HARD_SSL_NAME_CHECK=0
            export MODULE_BACKEND_ARBITER_CA_CERT=../etc/certs/ca.pem
            export MODULE_BACKEND_ARBITER_SERVER_CERT=../etc/certs/server.crt
            export MODULE_BACKEND_ARBITER_SERVER_KEY=../etc/certs/server.key
            export MODULE_BACKEND_ARBITER_SERVER_DH=../etc/certs/server.pem
            export MODULE_BACKEND_ARBITER_NAME=daemon
            export MODULE_BACKEND_ARBITER_PORT=10000
            export MODULE_BACKEND_ARBITER_PIDFILE=/tmp/daemon.pid
            export MODULE_BACKEND_ARBITER_LOCAL_LOG=/tmp/daemon.log
            export MODULE_BACKEND_ARBITER_MAX_QUEUE_SIZE=0
            export MODULE_BACKEND_ARBITER_PROCESS=alignak-arbiter
            export MODULE_BACKEND_ARBITER_DAEMON=alignak-arbiter
            export MODULE_BACKEND_ARBITER_CFG=../etc/daemons/arbiterd.ini
            export MODULE_BACKEND_ARBITER_DEBUGFILE=/tmp/arbiter-debug.log

        The export directives consider that shell variables must only contain [A-Za-z0-9_]
        in their name. All non alphanumeric characters are replaced with an underscore.
        The value of the variables is quoted to be shell-valid: escaped quotes, empty strings,...

        NOTE: this script manages the full Ini file format used by the Python ConfigParser:
        default section, variables interpolation

        NOTE: this script also adds the current Alignak version

    Use cases:
        Displays this usage screen
            alignak-environment (-h | --help)

        Parse Alignak configuration file and define environment variables
            cfg_file ../etc/alignak-realm2.ini

        Parse Alignak configuration file and define environment variables and print information
            cfg_file -v ../etc/alignak-realm2.ini

        Exit code:
            0 if required operation succeeded
            1 if the required file does not exist
            2 if the required file is not correctly formatted
            3 if interpolation variables are not correctly declared/used in the configuration file

            64 if command line parameters are not used correctly
"""
from __future__ import print_function

import os
import sys
import re

from pipes import quote as cmd_quote

import ConfigParser

from docopt import docopt, DocoptExit

from alignak.version import VERSION as __version__

SECTION_CONFIGURATION = "alignak-configuration"

class AlignakConfigParser(object):
    """
    Class to parse the Alignak main configuration file
    """

    def __init__(self, args=None):
        # Alignak version as a property
        self.alignak_version = __version__

        self.export = False
        self.embedded = True

        if args is None:
            # Get command line parameters
            try:
                args = docopt(__doc__)
            except DocoptExit as exp:
                print("Command line parsing error:\n%s." % (exp))
                exit(64)

            # Used as an independent script
            self.embedded = False
            # Print export commands for the calling shell
            self.export = True

        # Verbose
        self.verbose = False
        if '--verbose' in args and args['--verbose']:
            print("Alignak environment parser:")
            print("- verbose mode is On")
            self.verbose = True

        # Get the targeted item
        self.configuration_file = args['<cfg_file>']
        if self.verbose:
            print("- configuration file name: %s" % self.configuration_file)
        if self.configuration_file is None:
            print("* missing configuration file name. Please provide a configuration "
                  "file name in the command line parameters")
            if self.embedded:
                raise ValueError
            exit(64)
        self.configuration_file = os.path.abspath(self.configuration_file)
        if not os.path.exists(self.configuration_file):
            print("* required configuration file does not exist: %s" % self.configuration_file)
            if self.embedded:
                raise ValueError
            exit(1)

    def parse(self):
        """
        Parse the Alignak configuration file

        Exit the script if some errors are encountered.

        :return: None
        """
        self.config = ConfigParser.ConfigParser()
        self.config.read(self.configuration_file)
        if self.config._sections == {}:
            print("* bad formatted configuration file: %s " % self.configuration_file)
            if self.embedded:
                raise ValueError
            sys.exit(2)

        try:
            for section in self.config.sections():
                if self.verbose:
                    print("- section: %s" % section)
                for (key, value) in self.config.items(section):
                    inner_property = "%s.%s" % (section, key)

                    # Set object property
                    setattr(self, inner_property, value)

                    # Set environment variable
                    os.environ[inner_property] = value

                    if self.verbose:
                        print("  %s = %s" % (inner_property, value))

                    if self.export:
                        # Allowed shell variables may only contain: [a-zA-z0-9_]
                        inner_property = re.sub('[^0-9a-zA-Z]+', '_', inner_property)
                        inner_property = inner_property.upper()
                        print("export %s=%s" % (inner_property, cmd_quote(value)))
        except ConfigParser.InterpolationMissingOptionError as err:
            err = str(err)
            wrong_variable = err.split('\n')[3].split(':')[1].strip()
            print("* incorrect or missing variable '%s' in config file : %s" %
                  (wrong_variable, self.configuration_file))
            if self.embedded:
                return False
            sys.exit(3)

        if self.verbose:
            print("Configuration file parsed correctly")

    def _search_sections(self, searched_sections=''):
        """
        Search sections in the configuration which name starts with the provided search criteria
        :param searched_sections:
        :return: a dict containing the found sections and their parameters
        """
        found_sections = {}
        # Get the daemons related properties
        for section in self.config.sections():
            if not section.startswith(searched_sections):
                continue

            if section not in found_sections:
                found_sections.update({section: {'imported_from': self.configuration_file}})
            for (key, value) in self.config.items(section):
                found_sections[section].update({key: value})
        return found_sections

    def get_monitored_configuration(self):
        """
        Get the Alignak monitored configuration parameters

        :return: a dict containing the Alignak configuration files
        """
        configuration = self._search_sections(SECTION_CONFIGURATION)
        if SECTION_CONFIGURATION not in configuration:
            return []
        for prop, value in configuration[SECTION_CONFIGURATION].items():
            if not prop.startswith('cfg'):
                configuration[SECTION_CONFIGURATION].pop(prop)
        return configuration[SECTION_CONFIGURATION]

    def get_alignak_configuration(self):
        """
        Get the Alignak global parameters. Indeed all the parameters defined in the DEFAULT
        ini file section...

        :return: a dict containing the Alignak parameters
        """
        return self.config.defaults()

    def get_daemons(self, name=None, type=None):
        """
        Get the daemons configuration parameters

        If name is provided, get the configuration for this daemon, else,
        If type is provided, get the configuration for all the daemons of this type, else
        get the configuration of all the daemons.

        :param name: the searched daemon name
        :param type: the searched daemon type
        :return: a dict containing the daemon(s) configuration parameters
        """
        if name is not None:
            sections = self._search_sections('daemon.' + name)
            if 'daemon.' + name in sections:
                return sections['daemon.' + name]
            return {}

        if type is not None:
            sections = self._search_sections('daemon.')
            for name, daemon in sections.items():
                if 'type' not in daemon or not daemon['type'] == type:
                    sections.pop(name)
            return sections

        return self._search_sections('daemon.')

    def get_modules(self, name=None, daemon_name=None):
        """
        Get the modules configuration parameters

        If name is provided, get the configuration for this module, else,
        If daemon_name is provided, get the configuration for all the modules of this daemon, else
        get the configuration of all the modules.

        :param name: the searched module name
        :param daemon_name: the modules of this daemon
        :return: a dict containing the module(s) configuration parameters
        """
        if name is not None:
            sections = self._search_sections('module.' + name)
            if 'module.' + name in sections:
                return sections['module.' + name]
            return {}

        if daemon_name is not None:
            section = self.get_daemons(daemon_name)
            if 'modules' in section and section['modules']:
                modules = []
                for module in section['modules'].split(','):
                    modules.append(self.get_modules(module))
            return []

        return self._search_sections('module.')

def main():
    """
    Main function
    """
    parsed_configuration = AlignakConfigParser()
    parsed_configuration.parse()

    if parsed_configuration.export:
        # Export Alignak version
        print("export ALIGNAK_VERSION=%s" % (parsed_configuration.alignak_version))


if __name__ == '__main__':
    main()
