#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

"""
alignak-environment command line interface::

    Usage:
        alignak [-h|--help]
        alignak [-v|--verbose] <cfg_file>

    Options:
        -h, --help          Show this usage screen.
        -v, --verbose       Run in verbose mode (print information on the console output)

    Output:
        This script will parse the provided configuration file and it will output all the
        variables defined in this file as Linux/Unix shell export variables.

        As an example for a file as the default ./etc/alignak.ini, the script will output:
            export ALIGNAK_CONFIGURATION_DIST=/usr/local/
            export ALIGNAK_CONFIGURATION_DIST_BIN=/usr/local//bin
            export ALIGNAK_CONFIGURATION_DIST_ETC=/usr/local//etc/alignak
            export ALIGNAK_CONFIGURATION_DIST_VAR=/usr/local//var/lib/alignak
            export ALIGNAK_CONFIGURATION_DIST_RUN=/usr/local//var/run/alignak
            export ALIGNAK_CONFIGURATION_DIST_LOG=/usr/local//var/log/alignak
            export ALIGNAK_CONFIGURATION_CONFIG_NAME='Alignak global configuration'
            export ALIGNAK_CONFIGURATION_ALIGNAK_NAME='My Alignak'
            export ALIGNAK_CONFIGURATION_USER=alignak
            export ALIGNAK_CONFIGURATION_GROUP=alignak
            ...
            export DAEMON_ARBITER_MASTER_DIST=/usr/local/
            export DAEMON_ARBITER_MASTER_DIST_BIN=/usr/local//bin
            export DAEMON_ARBITER_MASTER_DIST_ETC=/usr/local//etc/alignak
            export DAEMON_ARBITER_MASTER_DIST_VAR=/usr/local//var/lib/alignak
            export DAEMON_ARBITER_MASTER_DIST_RUN=/usr/local//var/run/alignak
            export DAEMON_ARBITER_MASTER_DIST_LOG=/usr/local//var/log/alignak
            export DAEMON_ARBITER_MASTER_CONFIG_NAME='Alignak global configuration'
            export DAEMON_ARBITER_MASTER_ALIGNAK_NAME='My Alignak'
            export DAEMON_ARBITER_MASTER_USER=alignak
            export DAEMON_ARBITER_MASTER_GROUP=alignak
            ...
            export DAEMON_SCHEDULER_MASTER_DIST=/usr/local/
            export DAEMON_SCHEDULER_MASTER_DIST_BIN=/usr/local//bin
            ...
            export ALIGNAK_VERSION=1.0.0

        The export directives consider that shell variables must only contain [A-Za-z0-9_]
        in their name. All non alphanumeric characters are replaced with an underscore.
        The value of the variables is quoted to be shell-valid: escaped quotes, empty strings,...

        NOTE: this script manages the full Ini file format used by the Python ConfigParser:
        default section, variables interpolation

        NOTE: this script also adds the current Alignak version to the content of the
        configuration file

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

import configparser

from docopt import docopt, DocoptExit

from alignak.version import VERSION as __version__

SECTION_CONFIGURATION = "alignak-configuration"


class AlignakConfigParser(object):
    """
    Class to parse the Alignak main configuration file
    """

    def __init__(self, args=None):
        """
        Setup the configuration parser

        When used without args, it is considered as called by the Alignak daemon creation
        and the command line parser is not invoked.

        If called without args, it is considered as called from the command line and all the
         configuration file variables are output to the console with an 'export VARIABLE=value'
         format to be sourced to declare shell environment variables.

        :param args:
        """
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
        # pylint: disable=too-many-branches
        """
        Check if some extra configuration files are existing in an `alignak.d` sub directory
        near the found configuration file.

        Parse the Alignak configuration file(s)

        Exit the script if some errors are encountered.

        :return: True/False
        """
        # Search if some ini files existe in an alignak.d sub-directory
        sub_directory = 'alignak.d'
        dir_name = os.path.dirname(self.configuration_file)
        dir_name = os.path.join(dir_name, sub_directory)
        self.cfg_files = [self.configuration_file]
        if os.path.exists(dir_name):
            for root, _, walk_files in os.walk(dir_name, followlinks=True):
                for found_file in walk_files:
                    if not re.search(r"\.ini$", found_file):
                        continue
                    self.cfg_files.append(os.path.join(root, found_file))
        print("Loading configuration files: %s " % self.cfg_files)

        # Read and parse the found configuration files
        self.config = configparser.ConfigParser()
        try:
            self.config.read(self.cfg_files)
            if self.config._sections == {}:
                print("* bad formatted configuration file: %s " % self.configuration_file)
                if self.embedded:
                    raise ValueError
                sys.exit(2)

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
        except configparser.ParsingError as exp:
            print("* parsing error in config file : %s\n%s"
                  % (self.configuration_file, exp.message))
            if self.embedded:
                return False
            sys.exit(3)
        except configparser.InterpolationMissingOptionError as exp:
            print("* incorrect or missing variable: %s" % str(exp))
            if self.embedded:
                return False
            sys.exit(3)

        if self.verbose:
            print("Configuration file parsed correctly")

        return True

    def write(self, env_file):
        """
        Write the Alignak configuration to a file

        :param env_file: file name to dump the configuration
        :type env_file: str
        :return: True/False
        """
        try:
            with open(env_file, "w") as out_file:
                self.config.write(out_file)
        except Exception as exp:  # pylint: disable=broad-except
            print("Dumping environment file raised an error: %s. " % exp)

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

    def get_defaults(self):
        """
        Get all the parameters defined in the DEFAULT ini file section...

        :return: a dict containing the default parameters
        """
        return self.config.defaults()

    def get_legacy_cfg_files(self):
        """
        Get the Alignak monitored configuration files.

        :return: a dict containing the Alignak legacy configuration files
        """
        return self.get_alignak_configuration(legacy_cfg=True)

    def get_alignak_macros(self):
        """
        Get the Alignak macros.

        :return: a dict containing the Alignak macros
        """
        macros = self.get_alignak_configuration(macros=True)

        sections = self._search_sections('pack.')
        for name, _ in list(sections.items()):
            section_macros = self.get_alignak_configuration(section=name, macros=True)
            macros.update(section_macros)
        return macros

    def get_alignak_configuration(self, section=SECTION_CONFIGURATION,
                                  legacy_cfg=False, macros=False):
        """
        Get the Alignak configuration parameters. All the variables included in
        the SECTION_CONFIGURATION section except the variables starting with 'cfg'
        and the macros.

        If `lecagy_cfg` is True, this function only returns the variables included in
        the SECTION_CONFIGURATION section except the variables starting with 'cfg'

        If `macros` is True, this function only returns the variables included in
        the SECTION_CONFIGURATION section that are considered as macros

        :param section: name of the sectio nto search for
        :type section: str
        :param legacy_cfg: only get the legacy cfg declarations
        :type legacy_cfg: bool
        :param macros: only get the macros declarations
        :type macros: bool
        :return: a dict containing the Alignak configuration parameters
        """
        configuration = self._search_sections(section)
        if section not in configuration:
            return []
        for prop, _ in list(configuration[section].items()):
            # Only legacy configuration items
            if legacy_cfg:
                if not prop.startswith('cfg'):
                    configuration[section].pop(prop)
                continue
            # Only macro definitions
            if macros:
                if not prop.startswith('_') and not prop.startswith('$'):
                    configuration[section].pop(prop)
                continue
            # All values except legacy configuration and macros
            if prop.startswith('cfg') or prop.startswith('_') or prop.startswith('$'):
                configuration[section].pop(prop)

        return configuration[section]

    def get_daemons(self, daemon_name=None, daemon_type=None):
        """
        Get the daemons configuration parameters

        If name is provided, get the configuration for this daemon, else,
        If type is provided, get the configuration for all the daemons of this type, else
        get the configuration of all the daemons.

        :param daemon_name: the searched daemon name
        :param daemon_type: the searched daemon type
        :return: a dict containing the daemon(s) configuration parameters
        """
        if daemon_name is not None:
            sections = self._search_sections('daemon.%s' % daemon_name)
            if 'daemon.%s' % daemon_name in sections:
                return sections['daemon.' + daemon_name]
            return {}

        if daemon_type is not None:
            sections = self._search_sections('daemon.')
            for name, daemon in list(sections.items()):
                if 'type' not in daemon or not daemon['type'] == daemon_type:
                    sections.pop(name)
            return sections

        return self._search_sections('daemon.')

    def get_modules(self, name=None, daemon_name=None, names_only=True):
        """
        Get the modules configuration parameters

        If name is provided, get the configuration for this module, else,
        If daemon_name is provided, get the configuration for all the modules of this daemon, else
        get the configuration of all the modules.

        :param name: the searched module name
        :param daemon_name: the modules of this daemon
        :param names_only: if True only returns the modules names, else all the configuration data
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
                for module_name in section['modules'].split(','):
                    if names_only:
                        modules.append(module_name)
                    else:
                        modules.append(self.get_modules(name=module_name))
                return modules
            return []

        return self._search_sections('module.')


def main():
    """
    Main function
    """
    parsed_configuration = AlignakConfigParser()
    try:
        parsed_configuration.parse()
    except configparser.ParsingError as exp:
        print("Environment file parsing error: %s", exp)

    if parsed_configuration.export:
        # Export Alignak version
        print("export ALIGNAK_VERSION=%s" % (parsed_configuration.alignak_version))


if __name__ == '__main__':
    main()
