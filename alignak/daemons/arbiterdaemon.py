# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines, too-many-public-methods
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
#     cedef, cedef@cassio.pe
#     Guillaume Bour, guillaume@bour.cc
#     foomip, nelsondcp@gmail.com
#     Frédéric MOHIER, frederic.mohier@ipmfrance.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     xkilian, fmikus@acktomic.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     David GUENAULT, david.guenault@gmail.com
#     Arthur Gautier, superbaloo@superbaloo.net
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe Simon, geektophe@gmail.com
#     David Durieux, d.durieux@siprossii.com
#     Jean Gabes, naparuba@gmail.com
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Romain Forlot, rforlot@yahoo.com
#     Christophe SIMON, christophe.simon@dailymotion.com

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
This module provide Arbiter class used to run a arbiter daemon
"""
import os
import logging
import sys
import time
import signal
import traceback
import socket
import io
import threading
from datetime import datetime
from collections import deque

import psutil


from alignak.log import make_monitoring_log, set_log_level, set_log_console
from alignak.misc.common import SIGNALS_TO_NAMES_DICT
from alignak.misc.serialization import unserialize, AlignakClassLookupException
from alignak.objects.config import Config
from alignak.macroresolver import MacroResolver
from alignak.external_command import ExternalCommandManager
from alignak.dispatcher import Dispatcher
from alignak.daemon import Daemon
from alignak.stats import statsmgr
from alignak.brok import Brok
from alignak.external_command import ExternalCommand
from alignak.property import IntegerProp, StringProp, ListProp
from alignak.http.arbiter_interface import ArbiterInterface
from alignak.objects.satellitelink import SatelliteLink
from alignak.monitor import MonitorConnection


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Arbiter(Daemon):  # pylint: disable=R0902
    """
    Arbiter class. Referenced as "app" in most Interface

    Class to manage the Arbiter daemon.
    The Arbiter is the one that rules them all...
    """
    properties = Daemon.properties.copy()
    properties.update({
        'type':
            StringProp(default='arbiter'),
        'port':
            IntegerProp(default=7770),
        'legacy_cfg_files':
            ListProp(default=[]),
    })

    def __init__(self, **kwargs):
        """Arbiter daemon initialisation

        :param kwargs: command line arguments
        """
        # The monitored objects configuration files
        self.legacy_cfg_files = []
        # My daemons...
        self.daemons_last_check = 0
        self.daemons_last_reachable_check = 0
        self.my_daemons = {}

        # My report monitor interface and status
        self.my_monitor = None
        self.my_status = 0

        super(Arbiter, self).__init__(kwargs.get('daemon_name', 'Default-Arbiter'), **kwargs)

        # Our schedulers and arbiters are initialized in the base class

        # Specific arbiter command line parameters
        if 'legacy_cfg_files' in kwargs and kwargs['legacy_cfg_files']:
            logger.warning(
                "Using daemon configuration file is now deprecated. The arbiter daemon -a "
                "parameter should not be used anymore. Use the -e environment file "
                "parameter to provide a global Alignak configuration file. "
                "** Note that this feature is not removed because it is still used "
                "for the unit tests of the Alignak framework! If some monitoring files are "
                "present in the command line parameters, they will supersede the ones "
                "declared in the environment configuration file.")
            # Monitoring files in the arguments extend the ones defined
            # in the environment configuration file
            self.legacy_cfg_files.extend(kwargs['legacy_cfg_files'])
            logger.warning("Got some configuration files: %s", self.legacy_cfg_files)
        # if not self.legacy_cfg_files:
        #     sys.exit("The Alignak environment file is not existing "
        #              "or do not define any monitoring configuration files. "
        #              "The arbiter can not start correctly.")

        # Make sure the configuration files are not repeated...
        my_cfg_files = []
        for cfg_file in self.legacy_cfg_files:
            logger.debug("- configuration file: %s / %s", cfg_file, os.path.abspath(cfg_file))
            if os.path.abspath(cfg_file) not in my_cfg_files:
                my_cfg_files.append(os.path.abspath(cfg_file))
        self.legacy_cfg_files = my_cfg_files

        self.verify_only = False
        if 'verify_only' in kwargs and kwargs['verify_only']:
            self.verify_only = kwargs.get('verify_only', False)
        self.alignak_name = self.name
        if 'alignak_name' in kwargs and kwargs['alignak_name']:
            self.alignak_name = kwargs['alignak_name']
        self.arbiter_name = self.alignak_name

        # Dump system health, defaults to report every 5 loop count
        self.system_health = False
        self.system_health_period = 5
        if 'ALIGNAK_SYSTEM_MONITORING' in os.environ:
            self.system_health = True
            try:
                self.system_health_period = int(os.environ.get('ALIGNAK_SYSTEM_MONITORING', '5'))
            except ValueError:  # pragma: no cover, simple protection
                pass

        # This because it is the Satellite that has these properties and I am a Daemon
        # todo: change this?
        # My own broks
        self.broks = []
        self.broks_lock = threading.RLock()
        # My own monitoring events
        self.events = []
        self.events_lock = threading.RLock()
        # Queue to keep the recent events
        self.recent_events = None

        self.is_master = False
        self.link_to_myself = None
        self.instance_id = None

        # Now an external commands manager and a list for the external_commands
        self.external_commands_manager = None
        self.external_commands = []
        self.external_commands_lock = threading.RLock()

        # Used to check if we must still run or not - only for a spare arbiter
        self.must_run = True

        # Did we received a kill signal
        self.kill_request = False
        self.kill_timestamp = 0

        # All dameons connection are valid
        self.all_connected = False

        # Configuration loading / reloading
        self.need_config_reload = False
        self.loading_configuration = False

        self.http_interface = ArbiterInterface(self)
        self.conf = Config()

    def add(self, elt):
        """Generic function to add objects to the daemon internal lists.
        Manage Broks, External commands

        :param elt: objects to add
        :type elt: alignak.AlignakObject
        :return: None
        """
        if isinstance(elt, Brok):
            # For brok, we tag the brok with our instance_id
            elt.instance_id = self.instance_id
            if elt.type == 'monitoring_log':
                # The brok is a monitoring event
                with self.events_lock:
                    self.events.append(elt)
                statsmgr.counter('events', 1)
            else:
                with self.broks_lock:
                    self.broks.append(elt)
            statsmgr.counter('broks.added', 1)
        elif isinstance(elt, ExternalCommand):
            logger.debug("Queuing an external command '%s'", str(elt.__dict__))
            with self.external_commands_lock:
                self.external_commands.append(elt)
                statsmgr.counter('external-commands.added', 1)
        else:  # pragma: no cover, simple dev alerting
            logger.error('Do not manage object type %s (%s)', type(elt), elt)

    def get_managed_configurations(self):  # pylint: disable=no-self-use
        """Get the configuration managed by this arbiter

        This is used by the master arbiter to get information from its spare arbiter

        :return: a dict of arbiter links (only one) with instance_id as key and
        hash, push_flavor and configuration identifier as values
        :rtype: dict
        """
        res = {}
        # Todo: improve this for an arbiter spare
        # for arbiter_link in self.conf.arbiters:
        #     if arbiter_link == self.link_to_myself:
        #         # Not myself ;)
        #         continue
        #     res[arbiter_link.instance_id] = {
        #         'hash': arbiter_link.hash,
        #         'push_flavor': arbiter_link.push_flavor,
        #         'managed_conf_id': arbiter_link.managed_conf_id
        #     }
        logger.debug("Get managed configuration: %s", res)
        return res

    def push_broks_to_broker(self):  # pragma: no cover - not used!
        """Send all broks from arbiter internal list to broker

        The arbiter get some broks and then pushes them to all the brokers.

        :return: None
        """
        someone_is_concerned = False
        sent = False
        for broker_link in self.conf.brokers:
            # Send only if the broker is concerned...
            if not broker_link.manage_arbiters:
                continue

            someone_is_concerned = True
            if broker_link.reachable:
                logger.debug("Sending %d broks to the broker %s", len(self.broks), broker_link.name)
                if broker_link.push_broks(self.broks):
                    statsmgr.counter('broks.pushed.count', len(self.broks))
                    sent = True

        if not someone_is_concerned or sent:
            # No one is anymore interested with...
            del self.broks[:]

    def push_external_commands_to_schedulers(self):  # pragma: no cover - not used!
        """Send external commands to schedulers

        :return: None
        """
        # Now get all external commands and push them to the schedulers
        for external_command in self.external_commands:
            self.external_commands_manager.resolve_command(external_command)

        # Now for all reachable schedulers, send the commands
        sent = False
        for scheduler_link in self.conf.schedulers:
            ext_cmds = scheduler_link.external_commands
            if ext_cmds and scheduler_link.reachable:
                logger.debug("Sending %d commands to the scheduler %s",
                             len(ext_cmds), scheduler_link.name)
                if scheduler_link.push_external_commands(ext_cmds):
                    statsmgr.counter('external-commands.pushed.count', len(ext_cmds))
                    sent = True
            if sent:
                # Clean the pushed commands
                scheduler_link.external_commands.clear()

    def get_external_commands(self):
        """Get the external commands

        :return: External commands list
        :rtype: list
        """
        res = self.external_commands
        logger.debug("Get and clear external commands list: %s", res)
        self.external_commands = []
        return res

    def get_broks_from_satellites(self):  # pragma: no cover - not used!
        """Get broks from my all internal satellite links

        The arbiter get the broks from ALL the known satellites

        :return: None
        """
        for satellites in [self.conf.brokers, self.conf.schedulers,
                           self.conf.pollers, self.conf.reactionners, self.conf.receivers]:
            for satellite in satellites:
                # Get only if reachable...
                if not satellite.reachable:
                    continue
                logger.debug("Getting broks from: %s", satellite.name)
                new_broks = satellite.get_and_clear_broks()
                if new_broks:
                    logger.debug("Got %d broks from: %s", len(new_broks), satellite.name)
                for brok in new_broks:
                    self.add(brok)

    def get_initial_broks_from_satellites(self):
        """Get initial broks from my internal satellite links

        :return: None
        """
        for satellites in [self.conf.brokers, self.conf.schedulers,
                           self.conf.pollers, self.conf.reactionners, self.conf.receivers]:
            for satellite in satellites:
                # Get only if reachable...
                if not satellite.reachable:
                    continue
                logger.debug("Getting initial brok from: %s", satellite.name)
                brok = satellite.get_initial_status_brok()
                logger.debug("Satellite '%s' initial brok: %s", satellite.name, brok)
                self.add(brok)

    def load_monitoring_config_file(self, clean=True):
        # pylint: disable=too-many-branches,too-many-statements, too-many-locals
        """Load main configuration file (alignak.cfg)::

        * Read all files given in the -c parameters
        * Read all .cfg files in cfg_dir
        * Read all files in cfg_file
        * Create objects (Arbiter, Module)
        * Set HTTP links info (ssl etc)
        * Load its own modules
        * Execute read_configuration hook (for arbiter modules)
        * Create all objects (Service, Host, Realms ...)
        * "Compile" configuration (Linkify, explode, apply inheritance, fill default values ...)
        * Cut conf into parts and prepare it for sending

        The clean parameter is useful to load a configuration without removing the properties
        only used to parse the configuration and create the objects. Some utilities (like
        alignak-backend-import script) may need to avoid the cleaning ;)

        :param clean: set True to clean the created items
        :type clean: bool

        :return: None
        """
        self.loading_configuration = True
        _t_configuration = time.time()

        if self.verify_only:
            # Force adding a console handler to the Alignak logger
            set_log_console(logging.INFO if not self.debug else logging.DEBUG)
            # Force the global logger at INFO level
            set_log_level(logging.INFO if not self.debug else logging.DEBUG)
            logger.info("-----")
            logger.info("Arbiter is in configuration check mode")
            logger.info("Arbiter log level got increased to a minimum of INFO")
            logger.info("-----")

        # Maybe we do not have environment file
        # if not self.alignak_env:
        #     self.exit_on_error("*** No Alignak environment file. Exiting...", exit_code=2)
        # else:
        #     logger.info("Environment file: %s", self.env_filename)
        if self.legacy_cfg_files:
            logger.info("Loading monitored system configuration from legacy files: %s",
                        self.legacy_cfg_files)
        else:
            logger.info("No legacy file(s) configured for monitored system configuration")

        # Alignak global environment file
        # -------------------------------
        # Here we did not yet read the Alignak configuration file (except for the Arbiter daemon
        # configuration.
        # We must get the Alignak macros and global configuration parameters
        # ---------------------
        # Manage Alignak macros; this before loading the legacy configuration files
        # with their own potential macros
        # ---------------------
        macros = []
        # Get the macros / variables declared in the Alignak environment (alignak.ini) file!
        if self.alignak_env:
            # The properties defined in the alignak.cfg file are not yet set! So we set the one
            # got from the environment
            logger.info("Getting Alignak macros...")
            alignak_macros = self.alignak_env.get_alignak_macros()
            if alignak_macros:
                # Remove the leading and trailing underscores
                for key in sorted(alignak_macros.keys()):
                    value = alignak_macros[key]
                    if key[0] == '_' or key[0] == '$':
                        key = key[1:]
                    if key[-1] == '_' or key[-1] == '$':
                        key = key[:-1]
                    # Create an old legacy macro format
                    macros.append('$%s$=%s' % (key.upper(), value))
                    logger.debug("- Alignak macro '$%s$' = %s", key.upper(), value)

            # and then the global configuration.
            # The properties defined in the alignak.cfg file are not yet set! So we set the one
            # got from the appropriate section of the Alignak environment file
            logger.info("Getting Alignak configuration...")
            alignak_configuration = self.alignak_env.get_alignak_configuration()
            if alignak_configuration:
                for key in sorted(alignak_configuration.keys()):
                    value = alignak_configuration[key]
                    if key.startswith('_'):
                        # Ignore configuration variables prefixed with _
                        continue
                    if key in self.conf.properties:
                        entry = self.conf.properties[key]
                        setattr(self.conf, key, entry.pythonize(value))
                    else:
                        setattr(self.conf, key, value)
                    logger.debug("- setting '%s' as %s", key, getattr(self.conf, key))
                logger.info("Got Alignak global configuration")

        self.alignak_name = getattr(self.conf, "alignak_name", self.name)
        logger.info("Configuration for Alignak: %s", self.alignak_name)

        if macros:
            self.conf.load_params(macros)

        # Here we got the macros and alignak configuration variables from the
        # alignak.ini configuration!
        # The self Config object is now initialized with the global Alignak variables.

        # We can now read and parse the legacy configuration files (if any...)
        raw_objects = self.conf.read_config_buf(
            self.conf.read_legacy_cfg_files(self.legacy_cfg_files,
                                            self.alignak_env.cfg_files if self.alignak_env
                                            else None)
        )

        if self.alignak_name != getattr(self.conf, "alignak_name", self.name):
            self.alignak_name = getattr(self.conf, "alignak_name", self.name)
            logger.warning("Alignak name changed from the legacy Cfg files: %s", self.alignak_name)

        # Maybe conf is already invalid
        if not self.conf.conf_is_correct:
            self.conf.show_errors()
            self.request_stop("*** One or more problems were encountered while "
                              "processing the configuration (first check)...", exit_code=1)

        if self.legacy_cfg_files:
            logger.info("I correctly loaded the legacy configuration files")

        # Hacking some global parameters inherited from Nagios to create
        # on the fly some Broker modules like for status.dat parameters
        # or nagios.log one if there are none already available
        if 'module' not in raw_objects:
            raw_objects['module'] = []
        extra_modules = self.conf.hack_old_nagios_parameters()
        if extra_modules:
            logger.info("Some inner modules were configured for Nagios legacy parameters")
            for _, module in extra_modules:
                raw_objects['module'].append(module)
        logger.debug("Extra modules: %s", extra_modules)

        # Alignak global environment file
        # -------------------------------
        # Here we got the monitored system configuration from the legacy configuration files
        # We must overload this configuration for the daemons and modules with the configuration
        # declared in the Alignak environment (alignak.ini) file!
        if self.alignak_env:
            # Update the daemons legacy configuration if not complete
            for daemon_type in ['arbiter', 'scheduler', 'broker',
                                'poller', 'reactionner', 'receiver']:
                if daemon_type not in raw_objects:
                    raw_objects[daemon_type] = []

            # Get all the Alignak daemons from the configuration
            logger.info("Getting daemons configuration...")
            some_daemons = False
            for daemon_name, daemon_cfg in list(self.alignak_env.get_daemons().items()):
                logger.info("Got a daemon configuration for %s", daemon_name)
                if 'type' not in daemon_cfg:
                    self.conf.add_error("Ignoring daemon with an unknown type: %s" % daemon_name)
                    continue
                some_daemons = True
                daemon_type = daemon_cfg['type']
                daemon_name = daemon_cfg['name']
                logger.info("- got a %s named %s, spare: %s",
                            daemon_type, daemon_name, daemon_cfg.get('spare', False))

                # If this daemon is found in the legacy configuration, replace this
                new_cfg_daemons = []
                for cfg_daemon in raw_objects[daemon_type]:
                    if cfg_daemon.get('name', 'unset') == daemon_name \
                            or cfg_daemon.get("%s_name" % daemon_type,
                                              'unset') == [daemon_name]:
                        logger.info("  updating daemon Cfg file configuration")
                    else:
                        new_cfg_daemons.append(cfg_daemon)
                new_cfg_daemons.append(daemon_cfg)
                raw_objects[daemon_type] = new_cfg_daemons

            logger.debug("Checking daemons configuration:")
            some_legacy_daemons = False
            for daemon_type in ['arbiter', 'scheduler', 'broker',
                                'poller', 'reactionner', 'receiver']:
                for cfg_daemon in raw_objects[daemon_type]:
                    some_legacy_daemons = True
                    if 'name' not in cfg_daemon:
                        cfg_daemon['name'] = cfg_daemon['%s_name' % daemon_type]

                    cfg_daemon['modules'] = \
                        self.alignak_env.get_modules(daemon_name=cfg_daemon['name'])
                    for module_daemon_type, module in extra_modules:
                        if module_daemon_type == daemon_type:
                            cfg_daemon['modules'].append(module['name'])
                            logger.info("- added an Alignak inner module '%s' to the %s: %s",
                                        module['name'], daemon_type, cfg_daemon['name'])
                    logger.debug("- %s / %s: ", daemon_type, cfg_daemon['name'])
                    logger.debug("  %s", cfg_daemon)
            if not some_legacy_daemons:
                logger.debug("- No legacy configured daemons.")
            else:
                logger.info("- some dameons are configured in legacy Cfg files. "
                            "You should update the configuration with the new Alignak "
                            "configuration file.")
            if not some_daemons and not some_legacy_daemons:
                logger.info("- No configured daemons.")

            # and then get all modules from the configuration
            logger.info("Getting modules configuration...")
            if 'module' in raw_objects and raw_objects['module']:
                # Manage the former parameters module_alias and module_types
                # - replace with name and type
                for module_cfg in raw_objects['module']:
                    if 'module_alias' not in module_cfg and 'name' not in module_cfg:
                        self.conf.add_error("Module declared without any 'name' or 'module_alias'")
                        continue
                    else:
                        if 'name' not in module_cfg:
                            module_cfg['name'] = module_cfg['module_alias']
                            module_cfg.pop('module_alias')

                    if 'module_types' in module_cfg and 'type' not in module_cfg:
                        module_cfg['type'] = module_cfg['module_types']
                        module_cfg.pop('module_types')
                    logger.debug("Module cfg %s params: %s", module_cfg['name'], module_cfg)

            for _, module_cfg in list(self.alignak_env.get_modules().items()):
                logger.info("- got a module %s, type: %s",
                            module_cfg.get('name', 'unset'), module_cfg.get('type', 'untyped'))
                # If this module is found in the former Cfg files, replace the former configuration
                for cfg_module in raw_objects['module']:
                    if cfg_module.get('name', 'unset') == [module_cfg['name']]:
                        logger.info("  updating module Cfg file configuration")
                        cfg_module = module_cfg
                        logger.info("Module %s updated parameters: %s",
                                    module_cfg['name'], module_cfg)
                        break
                else:
                    raw_objects['module'].append(module_cfg)
                    logger.debug("Module env %s params: %s", module_cfg['name'], module_cfg)
            if 'module' in raw_objects and not raw_objects['module']:
                logger.info("- No configured modules.")

        # Create objects for our arbiters and modules
        self.conf.early_create_objects(raw_objects)

        # Check that an arbiter link exists and create the appropriate relations
        # If no arbiter exists, create one with the provided data
        params = {}
        if self.alignak_env:
            params = self.alignak_env.get_alignak_configuration()
        self.conf.early_arbiter_linking(self.name, params)

        # Search which arbiter I am in the arbiter links list
        for lnk_arbiter in self.conf.arbiters:
            logger.debug("I have an arbiter in my configuration: %s", lnk_arbiter.name)
            if lnk_arbiter.name != self.name:
                # Arbiter is not me!
                logger.info("I found another arbiter (%s) in my (%s) configuration",
                            lnk_arbiter.name, self.name)
                # And this arbiter needs to receive a configuration
                lnk_arbiter.need_conf = True
                continue

            logger.info("I found myself in the configuration: %s", lnk_arbiter.name)
            if self.link_to_myself is None:
                # I update only if it does not yet exist (first configuration load)!
                # I will not change myself because I am simply reloading a configuration ;)
                self.link_to_myself = lnk_arbiter
                self.link_to_myself.instance_id = self.name
                self.link_to_myself.push_flavor = ''.encode('utf-8')
                # self.link_to_myself.hash = self.conf.hash
            # Set myself as alive ;)
            self.link_to_myself.set_alive()

            # We consider that this arbiter is a master one...
            self.is_master = not self.link_to_myself.spare
            if self.is_master:
                logger.info("I am the master Arbiter.")
            else:
                logger.info("I am a spare Arbiter.")

            # ... and that this arbiter do not need to receive a configuration
            lnk_arbiter.need_conf = False

        if not self.link_to_myself:
            self.conf.show_errors()
            self.request_stop("Error: I cannot find my own configuration (%s), I bail out. "
                              "To solve this, please change the arbiter name parameter in "
                              "the Alignak configuration file (certainly alignak.ini) "
                              "with the value '%s'."
                              " Thanks." % (self.name, socket.gethostname()), exit_code=1)

        # Whether I am a spare arbiter, I will parse the whole configuration. This may be useful
        # if the master fails before sending its configuration to me!
        # An Arbiter which is not a master one will not go further...
        # todo: is it a good choice?:
        # 1/ why reading all the configuration files stuff?
        # 2/ why not loading configuration data from the modules?
        # -> Indeed, here, only the main configuration has been fetched by the arbiter.
        # Perharps, loading only the alignak.ini would be enough for a spare arbiter.
        # And it will make it simpler to configure...
        if not self.is_master:
            logger.info("I am not the master arbiter, I stop parsing the configuration")
            self.loading_configuration = False
            return

        # We load our own modules
        self.do_load_modules(self.link_to_myself.modules)

        # Call modules that manage this read configuration pass
        _ts = time.time()
        self.hook_point('read_configuration')
        statsmgr.timer('hook.read_configuration', time.time() - _ts)

        # Call modules get_alignak_configuration() to load Alignak configuration parameters
        # todo: re-enable this feature if it is really needed. It is a bit tricky to manage
        # configuration from our own configuration file and from an external source :(
        # (example modules: alignak_backend)
        # _t0 = time.time()
        # self.load_modules_alignak_configuration()
        # statsmgr.timer('core.hook.get_alignak_configuration', time.time() - _t0)

        # Call modules get_objects() to load new objects our own modules
        # (example modules: alignak_backend)
        self.load_modules_configuration_objects(raw_objects)

        # Create objects for all the configuration
        self.conf.create_objects(raw_objects)

        # Maybe configuration is already invalid
        if not self.conf.conf_is_correct:
            self.conf.show_errors()
            self.request_stop("*** One or more problems were encountered while processing "
                              "the configuration (second check)...", exit_code=1)

        # Manage all post-conf modules
        self.hook_point('early_configuration')

        # Here we got all our Alignak configuration and the monitored system configuration
        # from the legacy configuration files and extra modules.
        logger.info("Preparing configuration...")

        # Create Template links
        self.conf.linkify_templates()

        # All inheritances
        self.conf.apply_inheritance()

        # Explode between types
        self.conf.explode()

        # Implicit inheritance for services
        self.conf.apply_implicit_inheritance()

        # Fill default values for all the configuration objects
        self.conf.fill_default_configuration()

        # Remove templates from config
        self.conf.remove_templates()

        # Overrides specific service instances properties
        self.conf.override_properties()

        # Linkify objects to each other
        self.conf.linkify()

        # applying dependencies
        self.conf.apply_dependencies()

        # Raise warning about currently unmanaged parameters
        if self.verify_only:
            self.conf.warn_about_unmanaged_parameters()

        # Explode global configuration parameters into Classes
        self.conf.explode_global_conf()

        # set our own timezone and propagate it to other satellites
        self.conf.propagate_timezone_option()

        # Look for business rules, and create the dep tree
        self.conf.create_business_rules()
        # And link them
        self.conf.create_business_rules_dependencies()

        # Set my own parameters from the loaded configuration
        # Last monitoring events
        self.recent_events = deque(maxlen=int(os.environ.get('ALIGNAK_EVENTS_LOG_COUNT',
                                                             self.conf.events_log_count)))

        # Manage all post-conf modules
        self.hook_point('late_configuration')

        # Configuration is correct?
        logger.info("Checking configuration...")
        self.conf.is_correct()

        # Clean objects of temporary/unnecessary attributes for live work:
        if clean:
            logger.info("Cleaning configuration objects...")
            self.conf.clean()

        # Dump Alignak macros
        logger.debug("Alignak global macros:")

        macro_resolver = MacroResolver()
        macro_resolver.init(self.conf)
        for macro_name in sorted(self.conf.macros):
            macro_value = macro_resolver.resolve_simple_macros_in_string("$%s$" % macro_name, [],
                                                                         None, None)
            logger.debug("- $%s$ = %s", macro_name, macro_value)
        statsmgr.timer('configuration.loading', time.time() - _t_configuration)

        # REF: doc/alignak-conf-dispatching.png (2)
        logger.info("Splitting configuration...")
        self.conf.cut_into_parts()
        # Here, the self.conf.parts exist
        # And the realms have some 'packs'

        # Check if all the configuration daemons will be available
        if not self.daemons_start(run_daemons=False):
            self.conf.show_errors()
            self.request_stop("*** Alignak will not be able to manage the configured daemons. "
                              "Check and update your configuration!", exit_code=1)

        # Some properties need to be prepared (somehow "flatten"...) before being sent,
        # This to prepare the configuration that will be sent to our spare arbiter (if any)
        self.conf.prepare_for_sending()
        statsmgr.timer('configuration.spliting', time.time() - _t_configuration)
        # Here, the self.conf.spare_arbiter_conf exist

        # Still a last configuration check because some things may have changed when
        # we cut the configuration into parts (eg. hosts and realms consistency) and
        # when we prepared the configuration for sending
        if not self.conf.conf_is_correct:  # pragma: no cover, not with unit tests.
            self.conf.show_errors()
            self.request_stop("Configuration is incorrect, sorry, I bail out", exit_code=1)

        logger.info("Things look okay - "
                    "No serious problems were detected during the pre-flight check")

        # Exit if we are just here for config checking
        if self.verify_only:
            logger.info("Arbiter %s checked the configuration", self.name)
            if self.conf.missing_daemons:
                logger.warning("Some missing daemons were detected in the parsed configuration. "
                               "Nothing to worry about, but you should define them, "
                               "else Alignak will use its default configuration.")

            # Display found warnings and errors
            self.conf.show_errors()
            self.request_stop()

        del raw_objects

        # Display found warnings and errors
        self.conf.show_errors()

        # Now I have a configuration!
        self.have_conf = True
        self.loading_configuration = False
        statsmgr.timer('configuration.available', time.time() - _t_configuration)

    def load_modules_configuration_objects(self, raw_objects):  # pragma: no cover,
        # not yet with unit tests.
        """Load configuration objects from arbiter modules
        If module implements get_objects arbiter will call it and add create
        objects

        :param raw_objects: raw objects we got from reading config files
        :type raw_objects: dict
        :return: None
        """
        # Now we ask for configuration modules if they
        # got items for us
        for instance in self.modules_manager.instances:
            logger.debug("Getting objects from the module: %s", instance.name)
            if not hasattr(instance, 'get_objects'):
                logger.debug("The module '%s' do not provide any objects.", instance.name)
                return

            try:
                logger.info("Getting Alignak monitored configuration objects from module '%s'",
                            instance.name)
                got_objects = instance.get_objects()
            except Exception as exp:  # pylint: disable=broad-except
                logger.exception("Module %s get_objects raised an exception %s. "
                                 "Log and continue to run.", instance.name, exp)
                continue

            if not got_objects:
                logger.warning("The module '%s' did not provided any objects.", instance.name)
                return

            types_creations = self.conf.types_creations
            for o_type in types_creations:
                (_, _, prop, _, _) = types_creations[o_type]
                if prop in ['arbiters', 'brokers', 'schedulers',
                            'pollers', 'reactionners', 'receivers', 'modules']:
                    continue
                if prop not in got_objects:
                    logger.warning("Did not get any '%s' objects from %s", prop, instance.name)
                    continue
                for obj in got_objects[prop]:
                    # test if raw_objects[k] are already set - if not, add empty array
                    if o_type not in raw_objects:
                        raw_objects[o_type] = []
                    # Update the imported_from property if the module did not set
                    if 'imported_from' not in obj:
                        obj['imported_from'] = 'module:%s' % instance.name
                    # Append to the raw objects
                    raw_objects[o_type].append(obj)
                logger.debug("Added %i %s objects from %s",
                             len(got_objects[prop]), o_type, instance.name)

    def load_modules_alignak_configuration(self):  # pragma: no cover, not yet with unit tests.
        """Load Alignak configuration from the arbiter modules
        If module implements get_alignak_configuration, call this function

        :param raw_objects: raw objects we got from reading config files
        :type raw_objects: dict
        :return: None
        """
        alignak_cfg = {}
        # Ask configured modules if they got configuration for us
        for instance in self.modules_manager.instances:
            if not hasattr(instance, 'get_alignak_configuration'):
                return

            try:
                logger.info("Getting Alignak global configuration from module '%s'", instance.name)
                cfg = instance.get_alignak_configuration()
                alignak_cfg.update(cfg)
            except Exception as exp:  # pylint: disable=broad-except
                logger.error("Module %s get_alignak_configuration raised an exception %s. "
                             "Log and continue to run", instance.name, str(exp))
                output = io.StringIO()
                traceback.print_exc(file=output)
                logger.error("Back trace of this remove: %s", output.getvalue())
                output.close()
                continue

        params = []
        if alignak_cfg:
            logger.info("Got Alignak global configuration:")
            for key, value in sorted(alignak_cfg.items()):
                logger.info("- %s = %s", key, value)
                # properties starting with an _ character are "transformed" to macro variables
                if key.startswith('_'):
                    key = '$' + key[1:].upper() + '$'
                # properties valued as None are filtered
                if value is None:
                    continue
                # properties valued as None string are filtered
                if value == 'None':
                    continue
                # properties valued as empty strings are filtered
                if value == '':
                    continue
                # set properties as legacy Shinken configuration files
                params.append("%s=%s" % (key, value))
            self.conf.load_params(params)

    def request_stop(self, message='', exit_code=0):
        """Stop the Arbiter daemon

        :return: None
        """
        # Only a master arbiter can stop the daemons
        if self.is_master:
            # Stop the daemons
            self.daemons_stop(timeout=self.conf.daemons_stop_timeout)

        # Request the daemon stop
        super(Arbiter, self).request_stop(message, exit_code)

    def start_daemon(self, satellite):
        """Manage the list of detected missing daemons

         If the daemon does not in exist `my_daemons`, then:
          - prepare daemon start arguments (port, name and log file)
          - start the daemon
          - make sure it started correctly

        :param satellite: the satellite for which a daemon is to be started
        :type satellite: SatelliteLink

        :return: True if the daemon started correctly
        """
        logger.info("  launching a daemon for: %s/%s...", satellite.type, satellite.name)

        # The daemon startup script location may be defined in the configuration
        daemon_script_location = getattr(self.conf, 'daemons_script_location', self.bindir)
        if not daemon_script_location:
            daemon_script_location = "alignak-%s" % satellite.type
        else:
            daemon_script_location = "%s/alignak-%s" % (daemon_script_location, satellite.type)

        # Some extra arguments may be defined in the Alignak configuration
        daemon_arguments = getattr(self.conf, 'daemons_arguments', '')

        args = [daemon_script_location,
                "--name", satellite.name,
                "--environment", self.env_filename,
                "--host", str(satellite.host),
                "--port", str(satellite.port)]
        if daemon_arguments:
            args.append(daemon_arguments)
        logger.info("  ... with some arguments: %s", args)
        try:
            process = psutil.Popen(args, stdin=None, stdout=None, stderr=None)
            # A brief pause...
            time.sleep(0.1)
        except Exception as exp:  # pylint: disable=broad-except
            logger.error("Error when launching %s: %s", satellite.name, exp)
            logger.error("Command: %s", args)
            return False

        logger.info("  %s launched (pid=%d, gids=%s)",
                    satellite.name, process.pid, process.gids())

        # My satellites/daemons map
        self.my_daemons[satellite.name] = {
            'satellite': satellite,
            'process': process
        }
        return True

    def daemons_start(self, run_daemons=True):
        """Manage the list of the daemons in the configuration

        Check if the daemon needs to be started by the Arbiter.

        If so, starts the daemon if `run_daemons` is True

        :param run_daemons: run the daemons or make a simple check
        :type run_daemons: bool

        :return: True if all daemons are running, else False. always True for a simple check
        """
        result = True

        if run_daemons:
            logger.info("Alignak configured daemons start:")
        else:
            logger.info("Alignak configured daemons check:")

        # Parse the list of the missing daemons and try to run the corresponding processes
        for satellites_list in [self.conf.arbiters, self.conf.receivers, self.conf.reactionners,
                                self.conf.pollers, self.conf.brokers, self.conf.schedulers]:
            for satellite in satellites_list:
                logger.info("- found %s, to be launched: %s, address: %s",
                            satellite.name, satellite.alignak_launched, satellite.uri)

                if satellite == self.link_to_myself:
                    # Ignore myself ;)
                    continue

                if satellite.address not in ['127.0.0.1', 'localhost']:
                    logger.error("Alignak is required to launch a daemon for %s %s "
                                 "but the satelitte is defined on an external address: %s",
                                 satellite.type, satellite.name, satellite.address)
                    result = False
                    continue

                if not run_daemons:
                    # When checking, ignore the daemon launch part...
                    continue

                if not satellite.alignak_launched:
                    logger.debug("Alignak will not launch '%s'")
                    continue

                if not satellite.active:
                    logger.warning("- daemon '%s' is declared but not set as active, "
                                   "do not start...", satellite.name)
                    continue

                if satellite.name in self.my_daemons:
                    logger.warning("- daemon '%s' is already running", satellite.name)
                    continue

                started = self.start_daemon(satellite)
                result = result and started
        return result

    def daemons_check(self):
        """Manage the list of Alignak launched daemons

         Check if the daemon process is running

        :return: True if all daemons are running, else False
        """
        # First look if it's not too early to ping
        start = time.time()
        if self.daemons_last_check \
                and self.daemons_last_check + self.conf.daemons_check_period > start:
            logger.debug("Too early to check daemons, check period is %.2f seconds",
                         self.conf.daemons_check_period)
            return True

        logger.debug("Alignak launched daemons check")
        result = True

        procs = [psutil.Process()]
        for daemon in list(self.my_daemons.values()):
            # Get only the daemon (not useful for its children processes...)
            # procs = daemon['process'].children()
            procs.append(daemon['process'])
            for proc in procs:
                try:
                    logger.debug("Process %s is %s", proc.name(), proc.status())
                    # logger.debug("Process listening:", proc.name(), proc.status())
                    # for connection in proc.connections():
                    #     l_addr, l_port = connection.laddr if connection.laddr else ('', 0)
                    #     r_addr, r_port = connection.raddr if connection.raddr else ('', 0)
                    #     logger.debug("- %s:%s <-> %s:%s, %s", l_addr, l_port, r_addr, r_port,
                    #                  connection.status)
                    # Reset the daemon connection if it got broked...
                    if not daemon['satellite'].con:
                        if self.daemon_connection_init(daemon['satellite']):
                            # Set my satellite as alive :)
                            daemon['satellite'].set_alive()
                except psutil.NoSuchProcess:
                    pass
                except psutil.AccessDenied:
                    # Probably stopping...
                    if not self.will_stop and proc == daemon['process']:
                        logger.warning("Daemon %s/%s is not running!",
                                       daemon['satellite'].type, daemon['satellite'].name)
                        logger.debug("Access denied - Process %s is %s", proc.name(), proc.status())
                        if not self.start_daemon(daemon['satellite']):
                            # Set my satellite as dead :(
                            daemon['satellite'].set_dead()
                            result = False
                        else:
                            logger.info("I restarted %s/%s",
                                        daemon['satellite'].type, daemon['satellite'].name)
                            logger.info("Pausing %.2f seconds...", 0.5)
                            time.sleep(0.5)
                    else:
                        logger.info("Child process %s is %s", proc.name(), proc.status())

        # Set the last check as now
        self.daemons_last_check = start

        logger.debug("Checking daemons duration: %.2f seconds", time.time() - start)

        return result

    def daemons_stop(self, timeout=30, kill_children=False):
        """Stop the Alignak daemons

         Iterate over the self-launched daemons and their children list to send a TERM
         Wait for daemons to terminate and then send a KILL for those that are not yet stopped

         As a default behavior, only the launched daemons are killed, not their children.
         Each daemon will manage its children killing

        :param timeout: delay to wait before killing a daemon
        :type timeout: int

        :param kill_children: also kill the children (defaults to False)
        :type kill_children: bool

        :return: True if all daemons stopped
        """
        def on_terminate(proc):
            """Process termination callback function"""
            logger.debug("process %s terminated with exit code %s", proc.pid, proc.returncode)

        result = True

        if self.my_daemons:
            logger.info("Alignak self-launched daemons stop:")

            start = time.time()
            for daemon in list(self.my_daemons.values()):
                # Terminate the daemon and its children process
                procs = []
                if kill_children:
                    procs = daemon['process'].children()
                procs.append(daemon['process'])
                for process in procs:
                    try:
                        logger.info("- terminating process %s", process.name())
                        process.terminate()
                    except psutil.AccessDenied:
                        logger.warning("Process %s is %s", process.name(), process.status())

            procs = []
            for daemon in list(self.my_daemons.values()):
                # Stop the daemon and its children process
                if kill_children:
                    procs = daemon['process'].children()
                procs.append(daemon['process'])
            _, alive = psutil.wait_procs(procs, timeout=timeout, callback=on_terminate)
            if alive:
                # Kill processes
                for process in alive:
                    logger.warning("Process %s did not stopped, trying to kill", process.name())
                    process.kill()
                _, alive = psutil.wait_procs(alive, timeout=timeout, callback=on_terminate)
                if alive:
                    # give up
                    for process in alive:
                        logger.warning("process %s survived SIGKILL; giving up", process.name())
                        result = False

            logger.debug("Stopping daemons duration: %.2f seconds", time.time() - start)

        return result

    def daemons_reachability_check(self):
        """Manage the list of Alignak launched daemons

         Check if the daemon process is running

        :return: True if all daemons are running, else False
        """
        # First look if it's not too early to ping
        start = time.time()
        if self.daemons_last_reachable_check and \
                self.daemons_last_reachable_check + self.conf.daemons_check_period > start:
            logger.debug("Too early to check daemons reachability, check period is %.2f seconds",
                         self.conf.daemons_check_period)
            return True

        _t0 = time.time()
        logger.debug("Alignak daemons reachability check")
        result = self.dispatcher.check_reachable()
        statsmgr.timer('dispatcher.check-alive', time.time() - _t0)

        _t0 = time.time()
        logger.debug("Alignak daemons status get")
        events = self.dispatcher.check_status_and_get_events()
        duration = time.time() - _t0
        statsmgr.timer('dispatcher.check-status', duration)
        logger.debug("Getting daemons status duration: %.2f seconds", duration)

        # Send the collected events to the Alignak logger
        for event in events:
            event.prepare()
            make_monitoring_log(event.data['level'], event.data['message'],
                                timestamp=event.creation_time, to_logger=True)

            # Add to the recent events for the WS endpoint
            event.data['timestamp'] = event.creation_time
            event.data['date'] = datetime.fromtimestamp(event.creation_time).\
                strftime(self.conf.events_date_format)
            event.data.pop('instance_id')
            self.recent_events.append(event.data)

        # Set the last check as now
        self.daemons_last_reachable_check = start

        logger.debug("Checking daemons reachability duration: %.2f seconds", time.time() - start)

        return result

    def setup_new_conf(self):
        # pylint: disable=too-many-locals
        """ Setup a new configuration received from a Master arbiter.

        TODO: perharps we should not accept the configuration or raise an error if we do not
        find our own configuration data in the data. Thus this should never happen...
        :return: None
        """
        # Execute the base class treatment...
        super(Arbiter, self).setup_new_conf()

        with self.conf_lock:
            logger.info("I received a new configuration from my master")

            # Get the new configuration
            self.cur_conf = self.new_conf
            # self_conf is our own configuration from the alignak environment
            # Arbiters do not have this property in the received configuration because
            # they already loaded a configuration on daemon load
            self_conf = self.cur_conf.get('self_conf', None)
            if not self_conf:
                self_conf = self.conf

            # whole_conf contains the full configuration load by my master
            whole_conf = self.cur_conf['whole_conf']

            logger.debug("Received a new configuration, containing:")
            for key in self.cur_conf:
                logger.debug("- %s: %s", key, self.cur_conf[key])
            logger.debug("satellite self configuration part: %s", self_conf)

            # Update Alignak name
            self.alignak_name = self.cur_conf['alignak_name']
            logger.info("My Alignak instance: %s", self.alignak_name)

            # This to indicate that the new configuration got managed...
            self.new_conf = {}

            # Get the whole monitored objects configuration
            t00 = time.time()
            try:
                received_conf_part = unserialize(whole_conf)
            except AlignakClassLookupException as exp:  # pragma: no cover, simple protection
                # This to indicate that the new configuration is not managed...
                self.new_conf = {
                    "_status": "Cannot un-serialize configuration received from arbiter"
                }
                logger.error(self.new_conf['_status'])
                logger.error("Back trace of the error:\n%s", traceback.format_exc())
                return
            except Exception as exp:  # pylint: disable=broad-except
                # This to indicate that the new configuration is not managed...
                self.new_conf = {
                    "_status": "Cannot un-serialize configuration received from arbiter"
                }
                logger.error(self.new_conf['_status'])
                logger.error(self.new_conf)
                self.exit_on_exception(exp, self.new_conf)
            logger.info("Monitored configuration %s received at %d. Un-serialized in %d secs",
                        received_conf_part, t00, time.time() - t00)

            # Now we create our arbiters and schedulers links
            my_satellites = getattr(self, 'arbiters', {})
            received_satellites = self.cur_conf['arbiters']
            for link_uuid in received_satellites:
                rs_conf = received_satellites[link_uuid]
                logger.debug("- received %s - %s: %s", rs_conf['instance_id'],
                             rs_conf['type'], rs_conf['name'])

                # Must look if we already had a configuration and save our broks
                already_got = rs_conf['instance_id'] in my_satellites
                broks = []
                actions = {}
                wait_homerun = {}
                external_commands = {}
                running_id = 0
                if already_got:
                    logger.warning("I already got: %s", rs_conf['instance_id'])
                    # Save some information
                    running_id = my_satellites[link_uuid].running_id
                    (broks, actions,
                     wait_homerun, external_commands) = \
                        my_satellites[link_uuid].get_and_clear_context()
                    # Delete the former link
                    del my_satellites[link_uuid]

                # My new satellite link...
                new_link = SatelliteLink.get_a_satellite_link('arbiter', rs_conf)
                my_satellites[new_link.uuid] = new_link
                logger.info("I got a new arbiter satellite: %s", new_link)

                new_link.running_id = running_id
                new_link.external_commands = external_commands
                new_link.broks = broks
                new_link.wait_homerun = wait_homerun
                new_link.actions = actions

                # # replacing satellite address and port by those defined in satellite_map
                # if new_link.name in self_conf.satellite_map:
                #     overriding = self_conf.satellite_map[new_link.name]
                #     # satellite = dict(satellite)  # make a copy
                #     # new_link.update(self_conf.get('satellite_map', {})[new_link.name])
                #     logger.warning("Do not override the configuration for: %s, with: %s. "
                #                    "Please check whether this is necessary!",
                #                    new_link.name, overriding)

            # for arbiter_link in received_conf_part.arbiters:
            #     logger.info("I have arbiter links in my configuration: %s", arbiter_link.name)
            #     if arbiter_link.name != self.name and not arbiter_link.spare:
            #         # Arbiter is not me!
            #         logger.info("I found my master arbiter in the configuration: %s",
            #                     arbiter_link.name)
            #         continue
            #
            #     logger.info("I found myself in the received configuration: %s", arbiter_link.name)
            #     self.link_to_myself = arbiter_link
            #     # We received a configuration s we are not a master !
            #     self.is_master = False
            #     self.link_to_myself.spare = True
            #     # Set myself as alive ;)
            #     self.link_to_myself.set_alive()

        # Now I have a configuration!
        self.have_conf = True

    def wait_for_master_death(self):
        """Wait for a master timeout and take the lead if necessary

        :return: None
        """
        logger.info("Waiting for master death")
        timeout = 1.0
        self.last_master_ping = time.time()

        master_timeout = 300
        for arbiter_link in self.conf.arbiters:
            if not arbiter_link.spare:
                master_timeout = \
                    arbiter_link.spare_check_interval * arbiter_link.spare_max_check_attempts
        logger.info("I'll wait master death for %d seconds", master_timeout)

        while not self.interrupted:
            # Make a pause and check if the system time changed
            _, tcdiff = self.make_a_pause(timeout)
            # If there was a system time change then we have to adapt last_master_ping:
            if tcdiff:
                self.last_master_ping += tcdiff

            if self.new_conf:
                self.setup_new_conf()

            sys.stdout.write(".")
            sys.stdout.flush()

            # Now check if master is dead or not
            now = time.time()
            if now - self.last_master_ping > master_timeout:
                logger.info("Arbiter Master is dead. The arbiter %s takes the lead!",
                            self.link_to_myself.name)
                for arbiter_link in self.conf.arbiters:
                    if not arbiter_link.spare:
                        arbiter_link.alive = False
                self.must_run = True
                break

    def check_and_log_tp_activation_change(self):
        """Raise log for timeperiod change (useful for debug)

        :return: None
        """
        for timeperiod in self.conf.timeperiods:
            brok = timeperiod.check_and_log_activation_change()
            if brok:
                self.add(brok)

    def manage_signal(self, sig, frame):
        """Manage signals caught by the process
        Specific behavior for the arbiter when it receives a sigkill or sigterm

        :param sig: signal caught by the process
        :type sig: str
        :param frame: current stack frame
        :type frame:
        :return: None
        """
        # Request the arbiter to stop
        if sig in [signal.SIGINT, signal.SIGTERM]:
            logger.info("received a signal: %s", SIGNALS_TO_NAMES_DICT[sig])
            self.kill_request = True
            self.kill_timestamp = time.time()
            logger.info("request to stop in progress")
        else:
            Daemon.manage_signal(self, sig, frame)

    def configuration_dispatch(self, not_configured=None):
        """Monitored configuration preparation and dispatch

        :return: None
        """
        if not not_configured:
            self.dispatcher = Dispatcher(self.conf, self.link_to_myself)
            # I set my own dispatched configuration as the provided one...
            # because I will not push a configuration to myself :)
            self.cur_conf = self.conf

            # Loop for the first configuration dispatching, if the first dispatch fails, bail out!
            # Without a correct configuration, Alignak daemons will not run correctly
            first_connection_try_count = 0
            logger.info("Connecting to my satellites...")
            while True:
                first_connection_try_count += 1

                # Initialize connection with all our satellites
                self.all_connected = True
                for satellite in self.dispatcher.all_daemons_links:
                    if satellite == self.link_to_myself:
                        continue
                    if not satellite.active:
                        continue
                    connected = self.daemon_connection_init(satellite, set_wait_new_conf=True)
                    logger.debug("  %s is %s", satellite, connected)
                    self.all_connected = self.all_connected and connected

                if self.all_connected:
                    logger.info("- satellites connection #%s is ok", first_connection_try_count)
                    break
                else:
                    logger.warning("- satellites connection #%s is not correct; "
                                   "let's give another chance after %d seconds...",
                                   first_connection_try_count,
                                   self.link_to_myself.polling_interval)
                    if first_connection_try_count >= 3:
                        self.request_stop("All the daemons connections could not be established "
                                          "despite %d tries! "
                                          "Sorry, I bail out!" % first_connection_try_count,
                                          exit_code=4)
                    time.sleep(self.link_to_myself.polling_interval)

            # Now I have a connection with all the daemons I need to contact them,
            # check they are alive and ready to run
            _t0 = time.time()
            self.all_connected = self.dispatcher.check_reachable()
            statsmgr.timer('dispatcher.check-alive', time.time() - _t0)

            _t0 = time.time()
            # Preparing the configuration for dispatching
            logger.info("Preparing the configuration for dispatching...")
            self.dispatcher.prepare_dispatch()
            statsmgr.timer('dispatcher.prepare-dispatch', time.time() - _t0)
            logger.info("- configuration is ready to dispatch")

        # Loop for the first configuration dispatching, if the first dispatch fails, bail out!
        # Without a correct configuration, Alignak daemons will not run correctly
        first_dispatch_try_count = 0
        logger.info("Dispatching the configuration to my satellites...")
        while True:
            first_dispatch_try_count += 1

            # Check reachable - if a configuration is prepared, this will force the
            # daemons communication, and the dispatching will be launched
            _t0 = time.time()
            logger.info("- configuration dispatching #%s...", first_dispatch_try_count)
            self.dispatcher.check_reachable(forced=True)
            statsmgr.timer('dispatcher.dispatch', time.time() - _t0)

            # Make a pause to let our satellites get ready...
            pause = max(1, max(self.conf.daemons_dispatch_timeout, len(self.my_daemons) * 0.5))
            # pause = len(self.my_daemons) * 0.2
            logger.info("- pausing %d seconds...", pause)
            time.sleep(pause)

            _t0 = time.time()
            logger.info("- checking configuration dispatch...")
            # Checking the dispatch is accepted
            self.dispatcher.check_dispatch()
            statsmgr.timer('dispatcher.check-dispatch', time.time() - _t0)
            if self.dispatcher.dispatch_ok:
                logger.info("- configuration dispatching #%s is ok", first_dispatch_try_count)
                break
            else:
                logger.warning("- configuration dispatching #%s is not correct; "
                               "let's give another chance...", first_dispatch_try_count)
                if first_dispatch_try_count >= 3:
                    self.request_stop("The configuration could not be dispatched despite %d tries! "
                                      "Sorry, I bail out!" % first_connection_try_count,
                                      exit_code=4)

    def do_before_loop(self):
        """Called before the main daemon loop.

        :return: None
        """
        logger.info("I am the arbiter: %s", self.link_to_myself.name)

        # If I am a spare, I do not have anything to do here...
        if not self.is_master:
            logger.debug("Waiting for my master death...")
            return

        # Arbiter check if some daemons need to be started
        if not self.daemons_start(run_daemons=True):
            self.request_stop(message="Some Alignak daemons did not started correctly.",
                              exit_code=4)

        if not self.daemons_check():
            self.request_stop(message="Some Alignak daemons cannot be checked.",
                              exit_code=4)

        # Make a pause to let our started daemons get ready...
        pause = max(1, max(self.conf.daemons_start_timeout, len(self.my_daemons) * 0.5))
        if pause:
            logger.info("Pausing %.2f seconds...", pause)
            time.sleep(pause)

        # Prepare and dispatch the monitored configuration
        self.configuration_dispatch()

        # Now we can get all initial broks for our satellites
        _t0 = time.time()
        self.get_initial_broks_from_satellites()
        statsmgr.timer('broks.get-initial', time.time() - _t0)

        # Now create the external commands manager
        # We are a dispatcher: our role is to dispatch commands to the schedulers
        self.external_commands_manager = ExternalCommandManager(
            self.conf, 'dispatcher', self, self.conf.accept_passive_unknown_check_results)

    def do_loop_turn(self):
        # pylint: disable=too-many-branches, too-many-statements, too-many-locals
        """Loop turn for Arbiter

        If not a master daemon, wait for my master death...
        Else, run:
        * Check satellites are alive
        * Check and dispatch (if needed) the configuration
        * Get broks and external commands from the satellites
        * Push broks and external commands to the satellites

        :return: None
        """
        # If I am a spare, I only wait for the master arbiter to die...
        if not self.is_master:
            logger.debug("Waiting for my master death...")
            self.wait_for_master_death()
            return

        if self.loop_count % self.alignak_monitor_period == 1:
            self.get_alignak_status(details=True)

        # Maybe an external process requested Alignak stop...
        if self.kill_request:
            logger.info("daemon stop mode ...")
            if not self.dispatcher.stop_request_sent:
                logger.info("entering daemon stop mode, time before exiting: %s",
                            self.conf.daemons_stop_timeout)
                self.dispatcher.stop_request()
            if time.time() > self.kill_timestamp + self.conf.daemons_stop_timeout:
                logger.info("daemon stop mode delay reached, immediate stop")
                self.dispatcher.stop_request(stop_now=True)
                time.sleep(1)
                self.interrupted = True
                logger.info("exiting...")

        if not self.kill_request:
            # Main loop treatment
            # Try to see if one of my module is dead, and restart previously dead modules
            self.check_and_del_zombie_modules()

            # Call modules that manage a starting tick pass
            _t0 = time.time()
            self.hook_point('tick')
            statsmgr.timer('hook.tick', time.time() - _t0)

            # Look for logging timeperiods activation change (active/inactive)
            self.check_and_log_tp_activation_change()

            # Check that my daemons are alive
            if not self.daemons_check():
                if self.conf.daemons_failure_kill:
                    self.request_stop(message="Some Alignak daemons cannot be checked.",
                                      exit_code=4)
                else:
                    logger.warning("Should have killed my children if "
                                   "'daemons_failure_kill' were set!")

            # Now the dispatcher job - check if all daemons are reachable and have a configuration
            if not self.daemons_reachability_check():
                logger.warning("A new configuration dispatch is required!")

                # Prepare and dispatch the monitored configuration
                self.configuration_dispatch(self.dispatcher.not_configured)

            # Now get things from our module instances
            _t0 = time.time()
            self.get_objects_from_from_queues()
            statsmgr.timer('get-objects-from-queues', time.time() - _t0)

            # Maybe our satellites raised new broks. Reap them...
            _t0 = time.time()
            self.get_broks_from_satellites()
            statsmgr.timer('broks.got.time', time.time() - _t0)

            # One broker is responsible for our broks, we give him our broks
            _t0 = time.time()
            self.push_broks_to_broker()
            statsmgr.timer('broks.pushed.time', time.time() - _t0)

            # # We push our external commands to our schedulers...
            # _t0 = time.time()
            # self.push_external_commands_to_schedulers()
            # statsmgr.timer('external-commands.pushed.time', time.time() - _t0)

        if self.system_health and (self.loop_count % self.system_health_period == 1):
            perfdatas = []
            cpu_count = psutil.cpu_count()
            perfdatas.append("'cpu_count'=%d" % cpu_count)
            logger.debug("  . cpu count: %d", cpu_count)

            cpu_percents = psutil.cpu_percent(percpu=True)
            cpu = 1
            for percent in cpu_percents:
                perfdatas.append("'cpu_%d_percent'=%.2f%%" % (cpu, percent))
                cpu += 1

            cpu_times_percent = psutil.cpu_times_percent(percpu=True)
            cpu = 1
            for cpu_times_percent in cpu_times_percent:
                logger.debug("  . cpu time percent: %s", cpu_times_percent)
                for key in cpu_times_percent._fields:
                    perfdatas.append(
                        "'cpu_%d_%s_percent'=%.2f%%" % (cpu, key,
                                                        getattr(cpu_times_percent, key)))
                cpu += 1

            logger.info("%s cpu|%s", self.name, " ".join(perfdatas))

            perfdatas = []
            disk_partitions = psutil.disk_partitions(all=False)
            for disk_partition in disk_partitions:
                logger.debug("  . disk partition: %s", disk_partition)

                disk = getattr(disk_partition, 'mountpoint')
                disk_usage = psutil.disk_usage(disk)
                logger.debug("  . disk usage: %s", disk_usage)
                for key in disk_usage._fields:
                    if 'percent' in key:
                        perfdatas.append("'disk_%s_percent_used'=%.2f%%"
                                         % (disk, getattr(disk_usage, key)))
                    else:
                        perfdatas.append("'disk_%s_%s'=%dB"
                                         % (disk, key, getattr(disk_usage, key)))

            logger.info("%s disks|%s", self.name, " ".join(perfdatas))

            perfdatas = []
            virtual_memory = psutil.virtual_memory()
            logger.debug("  . memory: %s", virtual_memory)
            for key in virtual_memory._fields:
                if 'percent' in key:
                    perfdatas.append("'mem_percent_used_%s'=%.2f%%"
                                     % (key, getattr(virtual_memory, key)))
                else:
                    perfdatas.append("'mem_%s'=%dB"
                                     % (key, getattr(virtual_memory, key)))

            swap_memory = psutil.swap_memory()
            logger.debug("  . memory: %s", swap_memory)
            for key in swap_memory._fields:
                if 'percent' in key:
                    perfdatas.append("'swap_used_%s'=%.2f%%"
                                     % (key, getattr(swap_memory, key)))
                else:
                    perfdatas.append("'swap_%s'=%dB"
                                     % (key, getattr(swap_memory, key)))

            logger.info("%s memory|%s", self.name, " ".join(perfdatas))

    def get_daemon_stats(self, details=False):  # pylint: disable=too-many-branches
        """Increase the stats provided by the Daemon base class

        :return: stats dictionary
        :rtype: dict
        """
        now = int(time.time())
        # Call the base Daemon one
        res = super(Arbiter, self).get_daemon_stats(details=details)

        res.update({
            'name': self.link_to_myself.get_name() if self.link_to_myself else self.name,
            'type': self.type,
            'daemons_states': {}
        })

        if details:
            res['monitoring_objects'] = {}

            for _, _, strclss, _, _ in list(self.conf.types_creations.values()):
                if strclss in ['hostescalations', 'serviceescalations']:
                    logger.debug("Ignoring count for '%s'...", strclss)
                    continue

                objects_list = getattr(self.conf, strclss, [])
                res['monitoring_objects'][strclss] = {
                    'count': len(objects_list)
                }
                res['monitoring_objects'][strclss].update({'items': []})

                try:
                    dump_list = sorted(objects_list, key=lambda k: k.get_name())
                except AttributeError:  # pragma: no cover, simple protection
                    dump_list = objects_list

                # Dump at DEBUG level because some tests break with INFO level, and it is not
                # really necessary to have information about each object ;
                for cur_obj in dump_list:
                    if strclss == 'services':
                        res['monitoring_objects'][strclss]['items'].append(cur_obj.get_full_name())
                    else:
                        res['monitoring_objects'][strclss]['items'].append(cur_obj.get_name())

        # Arbiter counters, including the loaded configuration objects and the dispatcher data
        counters = res['counters']
        counters['external-commands'] = len(self.external_commands)
        counters['broks'] = len(self.broks)
        for _, _, strclss, _, _ in list(self.conf.types_creations.values()):
            if strclss in ['hostescalations', 'serviceescalations']:
                logger.debug("Ignoring count for '%s'...", strclss)
                continue

            objects_list = getattr(self.conf, strclss, [])
            counters[strclss] = len(objects_list)

        # Configuration dispatch counters
        if getattr(self, "dispatcher", None):
            for sat_type in ('arbiters', 'schedulers', 'reactionners',
                             'brokers', 'receivers', 'pollers'):
                counters["dispatcher.%s" % sat_type] = len(getattr(self.dispatcher, sat_type))

        # Report our daemons states, but only if a dispatcher exists
        if getattr(self, 'dispatcher', None):
            # Daemon properties that we are interested in
            res['daemons_states'] = {}
            for satellite in self.dispatcher.all_daemons_links:
                if satellite == self.link_to_myself:
                    continue
                # Get the information to be published for a satellite
                res['daemons_states'][satellite.name] = satellite.give_satellite_json()

            res['livestate'] = {
                "timestamp": now,
                "daemons": {}
            }
            state = 0
            for satellite in self.dispatcher.all_daemons_links:
                if satellite == self.link_to_myself:
                    continue

                livestate = 0
                if satellite.active:
                    if not satellite.reachable:
                        livestate = 1
                    elif not satellite.alive:
                        livestate = 2
                    state = max(state, livestate)
                else:
                    livestate = 3

                res['livestate']['daemons'][satellite.name] = livestate
            res['livestate'].update({
                "state": state,
                "output": [
                    "all daemons are up and running.",
                    "warning because some daemons are not reachable.",
                    "critical because some daemons not responding."
                ][state],
                # "long_output": "Long output...",
                # "perf_data": "'counter'=1"
            })

        return res

    def get_monitoring_problems(self):
        """Get the schedulers satellites problems list

        :return: problems dictionary
        :rtype: dict
        """
        res = self.get_id()
        res['problems'] = {}

        # Report our schedulers information, but only if a dispatcher exists
        if getattr(self, 'dispatcher', None) is None:
            return res

        for satellite in self.dispatcher.all_daemons_links:
            if satellite.type not in ['scheduler']:
                continue
            if not satellite.active:
                continue

            if satellite.statistics and 'problems' in satellite.statistics:
                res['problems'][satellite.name] = {
                    '_freshness': satellite.statistics['_freshness'],
                    'problems': satellite.statistics['problems']
                }

        return res

    def get_livesynthesis(self):
        """Get the schedulers satellites live synthesis

        :return: compiled livesynthesis dictionary
        :rtype: dict
        """
        res = self.get_id()
        res['livesynthesis'] = {
            '_overall': {
                '_freshness': int(time.time()),
                'livesynthesis': {
                    'hosts_total': 0,
                    'hosts_not_monitored': 0,
                    'hosts_up_hard': 0,
                    'hosts_up_soft': 0,
                    'hosts_down_hard': 0,
                    'hosts_down_soft': 0,
                    'hosts_unreachable_hard': 0,
                    'hosts_unreachable_soft': 0,
                    'hosts_problems': 0,
                    'hosts_acknowledged': 0,
                    'hosts_in_downtime': 0,
                    'hosts_flapping': 0,
                    'services_total': 0,
                    'services_not_monitored': 0,
                    'services_ok_hard': 0,
                    'services_ok_soft': 0,
                    'services_warning_hard': 0,
                    'services_warning_soft': 0,
                    'services_critical_hard': 0,
                    'services_critical_soft': 0,
                    'services_unknown_hard': 0,
                    'services_unknown_soft': 0,
                    'services_unreachable_hard': 0,
                    'services_unreachable_soft': 0,
                    'services_problems': 0,
                    'services_acknowledged': 0,
                    'services_in_downtime': 0,
                    'services_flapping': 0,
                }
            }
        }

        # Report our schedulers information, but only if a dispatcher exists
        if getattr(self, 'dispatcher', None) is None:
            return res

        for satellite in self.dispatcher.all_daemons_links:
            if satellite.type not in ['scheduler']:
                continue
            if not satellite.active:
                continue

            if 'livesynthesis' in satellite.statistics:
                # Scheduler detailed live synthesis
                res['livesynthesis'][satellite.name] = {
                    '_freshness': satellite.statistics['_freshness'],
                    'livesynthesis': satellite.statistics['livesynthesis']
                }
                # Cumulated live synthesis
                for prop in res['livesynthesis']['_overall']['livesynthesis']:
                    if prop in satellite.statistics['livesynthesis']:
                        res['livesynthesis']['_overall']['livesynthesis'][prop] += \
                            satellite.statistics['livesynthesis'][prop]

        return res

    def get_alignak_status(self, details=False):
        # pylint: disable=too-many-locals, too-many-branches
        """Push the alignak overall state as a passive check

        Build all the daemons overall state as a passive check that can be notified
        to the Alignak WS

        The Alignak Arbiter is considered as an host which services are all the Alignak
        running daemons. An Alignak daemon is considered as a service of an Alignak host.

        As such, it reports its status as a passive service check formatted as defined for
        the Alignak WS module (see http://alignak-module-ws.readthedocs.io)

        :return: A dict with the following structure
        ::
        {
            'name': 'type and name of the daemon',
            'livestate': {
                'state': "ok",
                'output': "state message",
                'long_output': "state message - longer ... if any",
                'perf_data': "daemon metrics (if any...)"
            }
            "services": {
                "daemon-1": {
                    'name': 'type and name of the daemon',
                    'livestate': {
                        'state': "ok",
                        'output': "state message",
                        'long_output': "state message - longer ... if any",
                        'perf_data': "daemon metrics (if any...)"
                    }
                }
                .../...
                "daemon-N": {
                    'name': 'type and name of the daemon',
                    'livestate': {
                        'state': "ok",
                        'output': "state message",
                        'long_output': "state message - longer ... if any",
                        'perf_data': "daemon metrics (if any...)"
                    }
                }
            }
        }

        :rtype: dict

        """
        now = int(time.time())

        # Get the arbiter statistics
        inner_stats = self.get_daemon_stats(details=details)

        res = {
            "name": inner_stats['alignak'],
            "template": {
                "_templates": ["alignak", "important"],
                "alias": inner_stats['alignak'],
                "active_checks_enabled": False,
                "passive_checks_enabled": True,
                "notes": ''
            },
            "variables": {
            },
            "livestate": {
                "timestamp": now,
                "state": "unknown",
                "output": "",
                "long_output": "",
                "perf_data": ""
            },
            "services": []
        }
        if details:
            res = {
                "name": inner_stats['alignak'],
                "template": {
                    "_templates": ["alignak", "important"],
                    "alias": inner_stats['alignak'],
                    "active_checks_enabled": False,
                    "passive_checks_enabled": True,
                    "notes": ''
                },
                "variables": {
                },
                "livestate": {
                    "timestamp": now,
                    "state": "unknown",
                    "output": "",
                    "long_output": "",
                    "perf_data": ""
                },
                "services": []
            }

        # Create self arbiter service - I am now considered as a service for my Alignak monitor!
        if 'livestate' in inner_stats:
            livestate = inner_stats['livestate']
            res['services'].append({
                "name": inner_stats['name'],
                "livestate": {
                    "timestamp": now,
                    "state": ["ok", "warning", "critical", "unknown"][livestate['state']],
                    "output": livestate['output'],
                    "long_output": livestate['long_output'] if 'long_output' in livestate else "",
                    "perf_data": livestate['perf_data'] if 'perf_data' in livestate else ""
                }
            })

        # Alignak performance data are:
        # 1/ the monitored items counters
        if 'counters' in inner_stats:
            metrics = []
            my_counters = [strclss for _, _, strclss, _, _ in
                           list(self.conf.types_creations.values())
                           if strclss not in ['hostescalations', 'serviceescalations']]
            for counter in inner_stats['counters']:
                # Only the arbiter created objects...
                if counter not in my_counters:
                    continue
                metrics.append("'%s'=%d" % (counter, inner_stats['counters'][counter]))
            res['livestate']['perf_data'] = ' '.join(metrics)

        # Report the arbiter daemons states, but only if they exist...
        if 'daemons_states' in inner_stats:
            state = 0
            long_output = []
            for daemon_id in sorted(inner_stats['daemons_states']):
                daemon = inner_stats['daemons_states'][daemon_id]
                res['services'].append({
                    "name": daemon_id,
                    "livestate": {
                        "timestamp": now,
                        "name": "%s_%s" % (daemon['type'], daemon['name']),
                        "state": ["ok", "warning", "critical", "unknown"][daemon['livestate']],
                        "output": [
                            u"daemon is alive and reachable.",
                            u"daemon is not reachable.",
                            u"daemon is not alive."
                        ][daemon['livestate']],
                        "long_output": "Realm: %s (%s). Listening on: %s"
                                       % (daemon['realm_name'], daemon['manage_sub_realms'],
                                          daemon['uri']),
                        "perf_data": "last_check=%.2f" % daemon['last_check']
                    }
                })
                state = max(state, daemon['livestate'])
                long_output.append(
                    "%s - %s" % (daemon_id, [u"daemon is alive and reachable.",
                                             u"daemon is not reachable.",
                                             u"daemon is not alive."][daemon['livestate']]))

            res['livestate'].update({
                "state": "up",  # Always Up ;)
                "output": [
                    u"All my daemons are up and running.",
                    u"Some of my daemons are not reachable.",
                    u"Some of my daemons are not responding!"
                ][state],
                "long_output": '\n'.join(long_output)
            })
            log_level = 'info'
            if state == 1:  # DOWN
                log_level = 'error'
            if state == 2:  # UNREACHABLE
                log_level = 'warning'
            if self.conf.log_alignak_checks or state > 0:
                self.add(make_monitoring_log(log_level, 'ALIGNAK CHECK;%s;%d;%s;%s' % (
                    self.alignak_name, state, res['livestate']['output'],
                    res['livestate']['long_output']
                )))
            if self.my_status != state:
                self.my_status = state
                self.add(make_monitoring_log(log_level, 'ALIGNAK ALERT;%s;%d;%s;%s' % (
                    self.alignak_name, state, res['livestate']['output'],
                    res['livestate']['long_output']
                )))

        if self.alignak_monitor:
            logger.debug("Pushing Alignak passive check to %s: %s", self.alignak_monitor, res)

            if self.my_monitor is None:
                self.my_monitor = MonitorConnection(self.alignak_monitor)

            if not self.my_monitor.authenticated:
                self.my_monitor.login(self.alignak_monitor_username,
                                      self.alignak_monitor_password)

            result = self.my_monitor.patch('host', res)
            logger.debug("Monitor reporting result: %s", result)
        else:
            logger.debug("No configured Alignak monitor to receive: %s", res)

        return res

    def main(self):
        """Main arbiter function::

        * Set logger
        * Init daemon
        * Launch modules
        * Endless main process loop

        :return: None
        """
        try:
            # Start the daemon
            if not self.do_daemon_init_and_start():
                self.exit_on_error(message="Daemon initialization error", exit_code=3)

            # Load monitoring configuration files
            self.load_monitoring_config_file()

            # Set my own process title
            self.set_proctitle(self.name)

            # Now we can start our "external" modules (if any):
            self.modules_manager.start_external_instances()

            # Now we can load the retention data
            self.hook_point('load_retention')

            # And go for the main loop
            while True:
                self.do_main_loop()
                logger.info("Exited from the main loop.")

                # Exiting the main loop because of a configuration reload
                if not self.need_config_reload:
                    # If no configuration reload is required, stop the arbiter daemon
                    self.request_stop()
                else:
                    # Loop if a configuration reload is raised while
                    # still reloading the configuration
                    while self.need_config_reload:
                        # Clear the former configuration
                        self.need_config_reload = False
                        self.link_to_myself = None
                        self.conf = Config()
                        # Load monitoring configuration files
                        _ts = time.time()
                        logger.warning('--- Reloading configuration...')
                        self.load_monitoring_config_file()
                        duration = int(time.time() - _ts)
                        self.add(make_monitoring_log('info', 'CONFIGURATION RELOAD;%d' % duration))
                        logger.warning('--- Configuration reloaded, %d seconds', duration)

                        # Make a pause to let our satellites get ready...
                        pause = max(1, self.conf.daemons_new_conf_timeout)
                        if pause:
                            logger.info("Pausing %.2f seconds...", pause)
                            time.sleep(pause)

        except Exception as exp:  # pragma: no cover, this should never happen indeed ;)
            # Only a master arbiter can stop the daemons
            if self.is_master:
                # Stop the daemons
                self.daemons_stop(timeout=self.conf.daemons_stop_timeout)
            self.exit_on_exception(raised_exception=exp)
            raise
