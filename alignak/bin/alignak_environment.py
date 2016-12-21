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
set_alignak_env command line interface::

    Usage:
        set_alignak_env [-h]
        set_alignak_env [-v] <cfg_file>

    Options:
        -h, --help          Show this usage screen.
        -v, --verbose       Run in verbose mode (print information on the console output)

    Output:
        This script will parse the provided configuration file and it will output all the
        variables defined in this file as Linux/Unix shell export variables.

        As an example for a file containing:
            [DEFAULT]
            BIN=../alignak/bin
            ETC=.
            VAR=/tmp/alignak
            RUN=/tmp/alignak
            LOG=/tmp/alignak

            [alignak-configuration]
            # Alignak main configuration file
            CFG=%(ETC)s/alignak.cfg
            # Alignak secondary configuration file (none as a default)
            SPECIFICCFG=

            [broker-master]
            ### BROKER PART ###
            CFG=%(ETC)s/daemons/brokerd.ini
            DAEMON=%(BIN)s/alignak-broker
            PID=%(RUN)s/brokerd.pid
            DEBUGFILE=%(LOG)s/broker-debug.log

        The script will output:
            export ALIGNAK_CONFIGURATION_BIN=../alignak/bin;
            export ALIGNAK_CONFIGURATION_ETC=.;
            export ALIGNAK_CONFIGURATION_VAR=/tmp/alignak;
            export ALIGNAK_CONFIGURATION_RUN=/tmp/alignak;
            export ALIGNAK_CONFIGURATION_LOG=/tmp/alignak;
            export ALIGNAK_CONFIGURATION_CFG=./alignak.cfg;
            export ALIGNAK_CONFIGURATION_SPECIFICCFG='';
            export BROKER_MASTER_BIN=../alignak/bin;
            export BROKER_MASTER_ETC=.;
            export BROKER_MASTER_VAR=/tmp/alignak;
            export BROKER_MASTER_RUN=/tmp/alignak;
            export BROKER_MASTER_LOG=/tmp/alignak;
            export BROKER_MASTER_CFG=./daemons/brokerd.ini;
            export BROKER_MASTER_DAEMON=../alignak/bin/alignak-broker;
            export BROKER_MASTER_PID=/tmp/alignak/brokerd.pid;
            export BROKER_MASTER_DEBUGFILE=/tmp/alignak/broker-debug.log;

        The export directives consider that shell variables must only contain [A-Za-z0-9_]
        in their name. All non alphanumeric characters are replaced with an underscore.
        The value of the variables is quoted to be shell-valid: escaped quotes, empty strings,...

        NOTE: this script manages the full Ini file format used by the Python ConfigParser:
        default section, variables interpolation

    Use cases:
        Displays this usage screen
            set_alignak_env (-h | --help)

        Parse Alignak configuration files and define environment variables
            cfg_file ../etc/alignak.ini

        Parse Alignak configuration files and define environment variables and print information
            cfg_file -v ../etc/alignak.ini

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

from docopt import docopt, DocoptExit

import ConfigParser

from alignak.version import VERSION as __version__


class AlignakConfigParser(object):
    """
    Class to parse the Alignak main configuration file
    """

    def __init__(self):
        # Get command line parameters
        args = None
        try:
            args = docopt(__doc__)
        except DocoptExit as exp:
            print("Command line parsing error:\n%s." % (exp))
            exit(64)

        # Alignak version as a property
        self.alignak_version = __version__

        # Print export commands for calling shell
        self.export = True

        # Verbose
        self.verbose = False
        if '--verbose' in args and args['--verbose']:
            print("Verbose mode is On")
            self.verbose = True

        # Get the targeted item
        self.configuration_file = args['<cfg_file>']
        if self.verbose:
            print("Configuration file name: %s" % self.configuration_file)
        if self.configuration_file is None:
            print("Missing configuration file name. Please provide a configuration "
                  "file name in the command line parameters")
            exit(64)
        self.configuration_file = os.path.abspath(self.configuration_file)
        if not os.path.exists(self.configuration_file):
            print("Required configuration file does not exist: %s" % self.configuration_file)
            exit(1)

    def parse(self):
        """
        Parse the Alignak configuration file

        Exit the script if some errors are encountered.

        :return: None
        """
        config = ConfigParser.ConfigParser()
        config.read(self.configuration_file)
        if config._sections == {}:
            print("Bad formatted configuration file: %s " % self.configuration_file)
            sys.exit(2)

        try:
            for section in config.sections():
                if self.verbose:
                    print("Section: %s" % section)
                for (key, value) in config.items(section):
                    property = "%s.%s" % (section, key)

                    # Set object property
                    setattr(self, property, value)

                    # Set environment variable
                    os.environ[property] = value

                    if self.verbose:
                        print(" %s = %s" % (property, value))

                    if self.export:
                        # Allowed shell variables may only contain: [a-zA-z0-9_]
                        property = re.sub('[^0-9a-zA-Z]+', '_', property)
                        property = property.upper()
                        print("export %s=%s" % (property, cmd_quote(value)))
        except ConfigParser.InterpolationMissingOptionError as err:
            err = str(err)
            wrong_variable = err.split('\n')[3].split(':')[1].strip()
            print("Incorrect or missing variable '%s' in config file : %s"%
                  (wrong_variable, self.configuration_file))
            sys.exit(3)

        if self.verbose:
            print("Configuration file parsed correctly")


def main():
    """
    Main function
    """
    bc = AlignakConfigParser()
    bc.parse()

    if bc.export:
        # Export Alignak version
        print("export ALIGNAK_VERSION=%s" % (bc.alignak_version))

if __name__ == '__main__':
    main()
