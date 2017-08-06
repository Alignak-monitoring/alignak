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
import logging
import sys
import time
import traceback
import socket
import cStringIO
import json

import subprocess

from alignak.misc.serialization import unserialize, AlignakClassLookupException
from alignak.objects.config import Config
from alignak.macroresolver import MacroResolver
from alignak.external_command import ExternalCommandManager
from alignak.dispatcher import Dispatcher
from alignak.daemon import Daemon
from alignak.stats import statsmgr
from alignak.brok import Brok
from alignak.external_command import ExternalCommand
from alignak.property import BoolProp, PathProp, IntegerProp, StringProp
from alignak.http.arbiter_interface import ArbiterInterface

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Arbiter(Daemon):  # pylint: disable=R0902
    """
    Arbiter class. Referenced as "app" in most Interface

    Class to manage the Arbiter daemon.
    The Arbiter is the one that rules them all...
    """
    properties = Daemon.properties.copy()
    properties.update({
        'daemon_type':
            StringProp(default='arbiter'),
        'pidfile':
            PathProp(default='arbiterd.pid'),
        'port':
            IntegerProp(default=7770),
        'local_log':
            PathProp(default='arbiterd.log'),
    })

    # pylint: disable=too-many-arguments
    def __init__(self, config_file, monitoring_files, is_daemon, do_replace, verify_only, debug,
                 debug_file, alignak_name, analyse=None,
                 port=None, local_log=None, daemon_name=None):
        self.daemon_name = 'arbiter'
        if daemon_name:
            self.daemon_name = daemon_name

        super(Arbiter, self).__init__(self.daemon_name, config_file, is_daemon, do_replace,
                                      debug, debug_file, port, local_log)

        self.config_files = monitoring_files
        self.verify_only = verify_only
        self.analyse = analyse
        self.arbiter_name = alignak_name
        self.alignak_name = None

        self.broks = {}
        self.is_master = False
        self.myself = None

        self.nb_broks_send = 0

        # Now an external commands manager and a list for the external_commands
        self.external_commands_manager = None
        self.external_commands = []

        # Used to work out if we must still be alive or not
        self.must_run = True

        self.http_interface = ArbiterInterface(self)
        self.conf = Config()

    def add(self, elt):
        """Generic function to add objects to queues.
        Only manage Broks and ExternalCommand

        #Todo: does the arbiter still needs to manage external commands

        :param elt: objects to add
        :type elt: alignak.brok.Brok | alignak.external_command.ExternalCommand
        :return: None
        """
        if isinstance(elt, Brok):
            self.broks[elt.uuid] = elt
        elif isinstance(elt, ExternalCommand):  # pragma: no cover, useful?
            # todo: does the arbiter will still manage external commands? It is the receiver job!
            self.external_commands.append(elt)
        else:
            logger.warning('Cannot manage object type %s (%s)', type(elt), elt)

    def push_broks_to_broker(self):
        """Send all broks from arbiter internal list to broker

        :return: None
        """
        for broker in self.conf.brokers:
            # Send only if alive of course
            if broker.manage_arbiters and broker.alive:
                is_sent = broker.push_broks(self.broks)
                if is_sent:
                    # They are gone, we keep none!
                    self.broks.clear()

    def get_external_commands_from_satellites(self):  # pragma: no cover, useful?
        """Get external commands from all other satellites

        TODO: does the arbiter will still manage external commands? It is the receiver job!

        :return: None
        """
        for satellites in [self.conf.brokers, self.conf.receivers,
                           self.conf.pollers, self.conf.reactionners]:
            for satellite in satellites:
                # Get only if alive of course
                if satellite.alive:
                    external_commands = satellite.get_external_commands()
                    for external_command in external_commands:
                        self.external_commands.append(external_command)

    def get_broks_from_satellitelinks(self):
        """Get broks from my internal satellitelinks (satellite status)

        :return: None
        TODO: Why satellitelink obj have broks and not the app itself?
        """
        for satellites in [self.conf.brokers, self.conf.schedulers,
                           self.conf.pollers, self.conf.reactionners, self.conf.receivers]:
            for satellite in satellites:
                new_broks = satellite.get_all_broks()
                for brok in new_broks:
                    logger.debug("Satellite '%s' brok: %s", satellite, brok)
                    self.add(brok)

    def get_initial_broks_from_satellitelinks(self):
        """Get initial broks from my internal satellitelinks (satellite status)

        :return: None
        """
        for satellites in [self.conf.brokers, self.conf.schedulers,
                           self.conf.pollers, self.conf.reactionners, self.conf.receivers]:
            for satellite in satellites:
                brok = satellite.get_initial_status_brok()
                logger.debug("Satellite '%s' initial brok: %s", satellite, brok)
                self.add(brok)

    @staticmethod
    def get_daemon_links(daemon_type):  # pragma: no cover, not used anywhere
        """Get the name of arbiter link (here arbiters)

        TODO: use or remove this function!

        :param daemon_type: daemon type
        :type daemon_type: str
        :return: named used to stroke this deamon type links
        :rtype: str
        """
        # the attribute name to get these differs for schedulers and arbiters
        return daemon_type + 's'

    # pylint: disable=too-many-branches
    def load_monitoring_config_file(self):  # pylint: disable=R0915
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

        :return: None
        """
        if self.verify_only:
            # Force the global logger at INFO level
            alignak_logger = logging.getLogger("alignak")
            alignak_logger.setLevel(logging.INFO)
            logger.info("Arbiter is in configuration check mode")
            logger.info("-----")

        logger.info("Loading configuration")
        # REF: doc/alignak-conf-dispatching.png (1)
        buf = self.conf.read_config(self.config_files)
        raw_objects = self.conf.read_config_buf(buf)
        # Maybe conf is already invalid
        if not self.conf.conf_is_correct:
            err = "***> One or more problems was encountered while processing the config files..."
            logger.error(err)
            # Display found warnings and errors
            self.conf.show_errors()
            sys.exit(err)

        logger.info("I correctly loaded the configuration files")
        self.alignak_name = getattr(self.conf, "alignak_name", self.arbiter_name)
        logger.info("Configuration for Alignak: %s", self.alignak_name)

        # First we need to get arbiters and modules
        # so we can ask them for objects
        self.conf.create_objects_for_type(raw_objects, 'arbiter')
        self.conf.create_objects_for_type(raw_objects, 'module')

        self.conf.early_arbiter_linking()

        # Search which arbiter I am in the arbiters list
        for arbiter in self.conf.arbiters:
            if arbiter.get_name() in ['Default-Arbiter', self.arbiter_name]:
                logger.info("I found myself in the configuration: %s", arbiter.get_name())
                # Arbiter is master one
                arbiter.need_conf = False
                self.myself = arbiter
                self.is_master = not self.myself.spare
                if self.is_master:
                    logger.info("I am the master Arbiter: %s", arbiter.get_name())
                else:
                    logger.info("I am a spare Arbiter: %s", arbiter.get_name())
                # export this data to our statsmgr object :)
                statsd_host = getattr(self.conf, 'statsd_host', 'localhost')
                statsd_port = getattr(self.conf, 'statsd_port', 8125)
                statsd_prefix = getattr(self.conf, 'statsd_prefix', 'alignak')
                statsd_enabled = getattr(self.conf, 'statsd_enabled', False)
                statsmgr.register(arbiter.get_name(), 'arbiter',
                                  statsd_host=statsd_host, statsd_port=statsd_port,
                                  statsd_prefix=statsd_prefix, statsd_enabled=statsd_enabled)

                # Set myself as alive ;)
                self.myself.alive = True
            else:  # not me
                # Arbiter is not me!
                logger.info("Found another arbiter in the configuration: %s", arbiter.get_name())
                arbiter.need_conf = True

        if not self.myself:
            sys.exit("Error: I cannot find my own Arbiter object (%s), I bail out. "
                     "To solve this, please change the arbiter_name parameter in "
                     "the arbiter configuration file (certainly arbiter-master.cfg) "
                     "with the value '%s'."
                     " Thanks." % (self.arbiter_name, socket.gethostname()))

        # Whether I am a spare arbiter, I will parse the whole configuration. This may be useful
        # if the master fails before sending its configuration to me!

        # Ok it's time to load the module manager now!
        self.load_modules_manager(self.myself.get_name())
        # we request the instances without them being *started*
        # (for those that are concerned ("external" modules):
        # we will *start* these instances after we have been daemonized (if requested)
        self.do_load_modules(self.myself.modules)

        if not self.is_master:
            logger.info("I am not the master arbiter, I stop parsing the configuration")
            return

        # Call modules that manage this read configuration pass
        self.hook_point('read_configuration')

        # Call modules get_alignak_configuration() to load Alignak configuration parameters
        # (example modules: alignak_backend)
        self.load_modules_alignak_configuration()

        # Call modules get_objects() to load new objects from them
        # (example modules: alignak_backend)
        self.load_modules_configuration_objects(raw_objects)

        # Resume standard operations
        self.conf.create_objects(raw_objects)

        # Maybe conf is already invalid
        if not self.conf.conf_is_correct:
            err = "***> One or more problems was encountered while processing the config files..."
            logger.error(err)
            # Display found warnings and errors
            self.conf.show_errors()
            sys.exit(err)

        # Manage all post-conf modules
        self.hook_point('early_configuration')

        # Load all file triggers
        self.conf.load_triggers()

        # Create Template links
        self.conf.linkify_templates()

        # All inheritances
        self.conf.apply_inheritance()

        # Explode between types
        self.conf.explode()

        # Implicit inheritance for services
        self.conf.apply_implicit_inheritance()

        # Fill default values
        self.conf.fill_default()

        # Remove templates from config
        self.conf.remove_templates()

        # Overrides specific service instances properties
        self.conf.override_properties()

        # Linkify objects to each other
        self.conf.linkify()

        # applying dependencies
        self.conf.apply_dependencies()

        # Hacking some global parameters inherited from Nagios to create
        # on the fly some Broker modules like for status.dat parameters
        # or nagios.log one if there are none already available
        self.conf.hack_old_nagios_parameters()

        # Raise warning about currently unmanaged parameters
        if self.verify_only:
            self.conf.warn_about_unmanaged_parameters()

        # Explode global conf parameters into Classes
        self.conf.explode_global_conf()

        # set our own timezone and propagate it to other satellites
        self.conf.propagate_timezone_option()

        # Look for business rules, and create the dep tree
        self.conf.create_business_rules()
        # And link them
        self.conf.create_business_rules_dependencies()

        # Warn about useless parameters in Alignak
        if self.verify_only:
            self.conf.notice_about_useless_parameters()

        # Manage all post-conf modules
        self.hook_point('late_configuration')

        # Configuration is correct?
        self.conf.is_correct()

        # Maybe some elements were not wrong, so we must clean if possible
        self.conf.clean()

        # Dump Alignak macros
        macro_resolver = MacroResolver()
        macro_resolver.init(self.conf)

        logger.info("Alignak global macros:")
        for macro_name in sorted(self.conf.macros):
            macro_value = macro_resolver.resolve_simple_macros_in_string("$%s$" % macro_name, [],
                                                                         None, None)
            logger.info("- $%s$ = %s", macro_name, macro_value)

        # If the conf is not correct, we must get out now (do not try to split the configuration)
        if not self.conf.conf_is_correct:  # pragma: no cover, not with unit tests.
            err = "Configuration is incorrect, sorry, I bail out"
            logger.error(err)
            # Display found warnings and errors
            self.conf.show_errors()
            sys.exit(err)

        # REF: doc/alignak-conf-dispatching.png (2)
        logger.info("Splitting hosts and services into parts")
        self.confs = self.conf.cut_into_parts()

        # The conf can be incorrect here if the cut into parts see errors like
        # a realm with hosts and no schedulers for it
        if not self.conf.conf_is_correct:  # pragma: no cover, not with unit tests.
            err = "Configuration is incorrect, sorry, I bail out"
            logger.error(err)
            # Display found warnings and errors
            self.conf.show_errors()
            sys.exit(err)

        # Clean objects of temporary/unnecessary attributes for live work:
        self.conf.clean()

        logger.info("Things look okay - "
                    "No serious problems were detected during the pre-flight check")

        # Exit if we are just here for config checking
        if self.verify_only:
            if self.conf.missing_daemons:
                logger.warning("Some missing daemons were detected in the parsed configuration.")

            logger.info("Arbiter checked the configuration")
            # Display found warnings and errors
            self.conf.show_errors()
            sys.exit(0)

        if self.analyse:  # pragma: no cover, not used currently (see #607)
            self.launch_analyse()
            sys.exit(0)

        # Some errors like a realm with hosts and no schedulers for it may imply to run new daemons
        if self.conf.missing_daemons:
            logger.info("Trying to handle the missing daemons...")
            if not self.manage_missing_daemons():
                err = "Some detected as missing daemons did not started correctly. " \
                      "Sorry, I bail out"
                logger.error(err)
                # Display found warnings and errors
                self.conf.show_errors()
                sys.exit(err)

        # Some properties need to be "flatten" (put in strings)
        # before being sent, like realms for hosts for example
        # BEWARE: after the cutting part, because we stringify some properties
        self.conf.prepare_for_sending()

        # Ignore daemon configuration parameters (port, log, ...) in the monitoring configuration
        # It's better to use daemon default parameters rather than those found in the monitoring
        # configuration (if some are found because they should not be there)...

        self.accept_passive_unknown_check_results = BoolProp.pythonize(
            getattr(self.myself, 'accept_passive_unknown_check_results', '0')
        )

        #  We need to set self.host & self.port to be used by do_daemon_init_and_start
        self.host = self.myself.address
        self.port = self.myself.port

        logger.info("Configuration Loaded")

        # Still a last configuration check because some things may have changed when
        # we prepared the configuration for sending
        if not self.conf.conf_is_correct:
            err = "Configuration is incorrect, sorry, I bail out"
            logger.error(err)
            # Display found warnings and errors
            self.conf.show_errors()
            sys.exit(err)

        # Display found warnings and errors
        self.conf.show_errors()

    def manage_missing_daemons(self):
        """Manage the list of detected missing daemons

         If the daemon does not in exist `my_satellites`, then:
          - prepare daemon start arguments (port, name and log file)
          - start the daemon
          - make sure it started correctly

        :return: True if all daemons are running, else False
        """
        result = True
        # Parse the list of the missing daemons and try to run the corresponding processes
        satellites = [self.conf.schedulers, self.conf.pollers, self.conf.brokers]
        self.my_satellites = {}
        for satellites_list in satellites:
            daemons_class = satellites_list.inner_class
            for daemon in self.conf.missing_daemons:
                if daemon.__class__ != daemons_class:
                    continue

                daemon_type = getattr(daemon, 'my_type', None)
                daemon_log_folder = getattr(self.conf, 'daemons_log_folder', '/tmp')
                daemon_arguments = getattr(self.conf, 'daemons_arguments', '')
                daemon_name = daemon.get_name()

                if daemon_name in self.my_satellites:
                    logger.info("Daemon '%s' is still running.", daemon_name)
                    continue

                args = ["alignak-%s" % daemon_type, "--name", daemon_name,
                        "--port", str(daemon.port),
                        "--local_log", "%s/%s.log" % (daemon_log_folder, daemon_name)]
                if daemon_arguments:
                    args.append(daemon_arguments)
                logger.info("Trying to launch daemon: %s...", daemon_name)
                logger.info("... with arguments: %s", args)
                self.my_satellites[daemon_name] = subprocess.Popen(args)
                logger.info("%s launched (pid=%d)",
                            daemon_name, self.my_satellites[daemon_name].pid)

                # Wait at least one second for a correct start...
                time.sleep(1)

                ret = self.my_satellites[daemon_name].poll()
                if ret is not None:
                    logger.error("*** %s exited on start!", daemon_name)
                    for line in iter(self.my_satellites[daemon_name].stdout.readline, b''):
                        logger.error(">>> " + line.rstrip())
                    for line in iter(self.my_satellites[daemon_name].stderr.readline, b''):
                        logger.error(">>> " + line.rstrip())
                    result = False
                else:
                    logger.info("%s running (pid=%d)",
                                daemon_name, self.my_satellites[daemon_name].pid)
        return result

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
        for inst in self.modules_manager.instances:
            # TODO : clean
            if not hasattr(inst, 'get_objects'):
                return

            _t0 = time.time()
            try:
                objs = inst.get_objects()
            except Exception, exp:  # pylint: disable=W0703
                logger.error("Module %s get_objects raised an exception %s. "
                             "Log and continue to run", inst.get_name(), str(exp))
                output = cStringIO.StringIO()
                traceback.print_exc(file=output)
                logger.error("Back trace of this remove: %s", output.getvalue())
                output.close()
                continue
            statsmgr.timer('core.hook.get_objects', time.time() - _t0)
            types_creations = self.conf.types_creations
            for type_c in types_creations:
                (_, _, prop, dummy) = types_creations[type_c]
                if prop not in objs:
                    logger.warning("Did not get '%s' objects from module %s", prop, inst.get_name())
                    continue
                for obj in objs[prop]:
                    # test if raw_objects[k] are already set - if not, add empty array
                    if type_c not in raw_objects:
                        raw_objects[type_c] = []
                    # put the imported_from property if the module is not already setting
                    # it so we know where does this object came from
                    if 'imported_from' not in obj:
                        obj['imported_from'] = 'module:%s' % inst.get_name()
                    # now append the object
                    raw_objects[type_c].append(obj)
                logger.debug("Added %i objects to %s from module %s",
                             len(objs[prop]), type_c, inst.get_name())

    def load_modules_alignak_configuration(self):  # pragma: no cover, not yet with unit tests.
        """Load Alignak configuration from the arbiter modules
        If module implements get_alignak_configuration, call this function

        :param raw_objects: raw objects we got from reading config files
        :type raw_objects: dict
        :return: None
        """
        alignak_cfg = {}
        # Ask configured modules if they got configuration for us
        for inst in self.modules_manager.instances:
            if not hasattr(inst, 'get_alignak_configuration'):
                return

            _t0 = time.time()
            try:
                logger.info("Getting Alignak global configuration from module '%s'",
                            inst.get_name())
                cfg = inst.get_alignak_configuration()
                alignak_cfg.update(cfg)
            except Exception, exp:  # pylint: disable=W0703
                logger.error("Module get_alignak_configuration %s raised an exception %s. "
                             "Log and continue to run", inst.get_name(), str(exp))
                output = cStringIO.StringIO()
                traceback.print_exc(file=output)
                logger.error("Back trace of this remove: %s", output.getvalue())
                output.close()
                continue
            statsmgr.timer('core.hook.get_alignak_configuration', time.time() - _t0)

        params = []
        if alignak_cfg:
            logger.info("Got Alignak global configuration:")
            for key, value in alignak_cfg.iteritems():
                logger.info("- %s = %s", key, value)
                # properties starting with an _ character are "transformed" to macro variables
                if key.startswith('_'):
                    key = '$' + key[1:].upper()
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

    def launch_analyse(self):  # pragma: no cover, not used currently (see #607)
        """ Dump the number of objects we have for each type to a JSON formatted file

        :return: None
        """
        logger.info("We are doing an statistic analysis on the dump file %s", self.analyse)
        stats = {}
        types = ['hosts', 'services', 'contacts', 'timeperiods', 'commands', 'arbiters',
                 'schedulers', 'pollers', 'reactionners', 'brokers', 'receivers', 'modules',
                 'realms']
        for o_type in types:
            lst = getattr(self.conf, o_type)
            number = len(lst)
            stats['nb_' + o_type] = number
            logger.info("Got %s for %s", number, o_type)

        max_srv_by_host = max(len(h.services) for h in self.conf.hosts)
        logger.info("Max srv by host %s", max_srv_by_host)
        stats['max_srv_by_host'] = max_srv_by_host

        file_d = open(self.analyse, 'w')
        state = json.dumps(stats)
        logger.info("Saving stats data to a file %s", state)
        file_d.write(state)
        file_d.close()

    def main(self):
        """Main arbiter function::

        * Set logger
        * Log Alignak headers
        * Init daemon
        * Launch modules
        * Load retention
        * Do mainloop

        :return: None
        """
        try:
            # Configure the logger
            self.setup_alignak_logger()

            # Load monitoring configuration files
            self.load_monitoring_config_file()

            # Look if we are enabled or not. If ok, start the daemon mode
            self.look_for_early_exit()
            self.do_daemon_init_and_start()

            # Set my own process title
            self.set_proctitle(self.myself.get_name())

            # ok we are now fully daemonized (if requested)
            # now we can start our "external" modules (if any):
            self.modules_manager.start_external_instances()

            # Ok now we can load the retention data
            self.hook_point('load_retention')

            # And go for the main loop
            self.do_mainloop()
            if self.need_config_reload:
                logger.info('Reloading configuration')
                self.unlink()
                self.do_stop()
            else:
                self.request_stop()

        except SystemExit as exp:
            # With a 2.4 interpreter the sys.exit() in load_config_file
            # ends up here and must be handled.
            sys.exit(exp.code)
        except Exception, exp:
            self.print_unrecoverable(traceback.format_exc())
            raise

    def setup_new_conf(self):
        """ Setup a new configuration received from a Master arbiter.

        Todo: perharps we should not accept the configuration or raise an error if we do not
        find our own configuration data in the data. Thus this should never happen...
        :return: None
        """
        with self.conf_lock:
            if not self.new_conf:
                logger.warning("Should not be here - I already got a configuration")
                return
            logger.info("I received a new configuration from my master")
            try:
                conf = unserialize(self.new_conf)
            except AlignakClassLookupException as exp:
                logger.exception('Cannot un-serialize received configuration: %s', exp)
                return

            logger.info("Got new configuration #%s", getattr(conf, 'magic_hash', '00000'))

            logger.info("I am: %s", self.arbiter_name)
            # This is my new configuration now ...
            self.cur_conf = conf
            self.conf = conf
            # Ready to get a new one ...
            self.new_conf = None
            for arb in self.conf.arbiters:
                if arb.get_name() in ['Default-Arbiter', self.arbiter_name]:
                    self.myself = arb

                    self.accept_passive_unknown_check_results = BoolProp.pythonize(
                        getattr(self.myself, 'accept_passive_unknown_check_results', '0')
                    )

                    logger.info("I found myself in the configuration")

    def do_loop_turn(self):
        """Loop turn for Arbiter
        If master, run, else wait for master death

        :return: None
        """
        # If I am a spare, I wait for the master arbiter to send me
        # true conf.
        if not self.is_master:
            logger.info("Waiting for master...")
            self.wait_for_master_death()

        if self.must_run and not self.interrupted:
            # Main loop
            self.run()

    def wait_for_master_death(self):
        """Wait for a master timeout and take the lead if necessary

        :return: None
        """
        logger.info("Waiting for master death")
        timeout = 1.0
        self.last_master_ping = time.time()

        # Look for the master timeout
        master_timeout = 300
        for arb in self.conf.arbiters:
            if not arb.spare:
                master_timeout = arb.check_interval * arb.max_check_attempts
        logger.info("I'll wait master for %d seconds", master_timeout)

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
                logger.info("Arbiter Master is dead. The arbiter %s take the lead",
                            self.myself.get_name())
                for arbiter in self.conf.arbiters:
                    if not arbiter.spare:
                        arbiter.alive = False
                self.must_run = True
                break

    def push_external_commands_to_schedulers(self):
        """Send external commands to schedulers

        :return: None
        """
        # Now get all external commands and put them into the
        # good schedulers
        for external_command in self.external_commands:
            self.external_commands_manager.resolve_command(external_command)

        # Now for all alive schedulers, send the commands
        for scheduler in self.conf.schedulers:
            cmds = scheduler.external_commands
            if cmds and scheduler.alive:
                logger.debug("Sending %d commands to scheduler %s", len(cmds), scheduler.get_name())
                scheduler.run_external_commands(cmds)
            # clean them
            scheduler.external_commands = []

    def check_and_log_tp_activation_change(self):
        """Raise log for timeperiod change (useful for debug)

        :return: None
        """
        for timeperiod in self.conf.timeperiods:
            brok = timeperiod.check_and_log_activation_change()
            if brok:
                self.add(brok)

    def run(self):
        """Run Arbiter daemon ::

        * Dispatch conf
        * Get initial brok from links
        * Load external command manager
        * Principal loop (send broks, external command, re dispatch etc.)

        :return:None
        """
        # Before running, I must be sure who am I
        # The arbiters change, so we must re-discover the new self.me
        for arbiter in self.conf.arbiters:
            if arbiter.get_name() in ['Default-Arbiter', self.arbiter_name]:
                self.myself = arbiter
                logger.info("I am the arbiter: %s", self.myself.arbiter_name)

        logger.info("Begin to dispatch configuration to the satellites")

        self.dispatcher = Dispatcher(self.conf, self.myself)
        self.dispatcher.check_alive()
        self.dispatcher.check_dispatch()
        # REF: doc/alignak-conf-dispatching.png (3)
        self.dispatcher.prepare_dispatch()
        self.dispatcher.dispatch()
        logger.info("Configuration has been dispatched to the satellites")

        # Now we can get all initial broks for our satellites
        self.get_initial_broks_from_satellitelinks()

        # Now create the external commands manager
        # We are a dispatcher: our role is to dispatch commands to the schedulers
        self.external_commands_manager = ExternalCommandManager(self.conf, 'dispatcher', self)
        # Update External Commands Manager
        self.external_commands_manager.accept_passive_unknown_check_results = \
            self.accept_passive_unknown_check_results

        logger.debug("Run baby, run...")
        timeout = 1.0

        while self.must_run and not self.interrupted and not self.need_config_reload:
            # Make a pause and check if the system time changed
            self.make_a_pause(timeout)

            # Try to see if one of my module is dead, and
            # try to restart previously dead modules :)
            self.check_and_del_zombie_modules()

            # Call modules that manage a starting tick pass
            self.hook_point('tick')

            # Look for logging timeperiods activation change (active/inactive)
            self.check_and_log_tp_activation_change()

            # Now the dispatcher job
            _t0 = time.time()
            self.dispatcher.check_alive()
            statsmgr.timer('core.check-alive', time.time() - _t0)

            _t0 = time.time()
            self.dispatcher.check_dispatch()
            statsmgr.timer('core.check-dispatch', time.time() - _t0)

            # REF: doc/alignak-conf-dispatching.png (3)
            _t0 = time.time()
            self.dispatcher.prepare_dispatch()
            self.dispatcher.dispatch()
            statsmgr.timer('core.dispatch', time.time() - _t0)

            _t0 = time.time()
            self.dispatcher.check_bad_dispatch()
            statsmgr.timer('core.check-bad-dispatch', time.time() - _t0)

            # Now get things from our module instances
            self.get_objects_from_from_queues()

            # Maybe our satellites links raise new broks. Must reap them
            self.get_broks_from_satellitelinks()

            # One broker is responsible for our broks,
            # we must give him our broks
            self.push_broks_to_broker()
            self.get_external_commands_from_satellites()
            # self.get_external_commands_from_receivers()
            # send_conf_to_schedulers()

            if self.nb_broks_send != 0:
                logger.debug("Nb Broks send: %d", self.nb_broks_send)
            self.nb_broks_send = 0

            _t0 = time.time()
            self.push_external_commands_to_schedulers()
            statsmgr.timer('core.push-external-commands', time.time() - _t0)

            # It's sent, do not keep them
            # TODO: check if really sent. Queue by scheduler?
            self.external_commands = []

            # If asked to dump my memory, I will do it
            if self.need_dump_memory:
                self.dump_memory()
                self.need_dump_memory = False

    def get_daemons(self, daemon_type):
        """Returns the daemons list defined in our conf for the given type

        :param daemon_type: deamon type needed
        :type daemon_type: str
        :return: attribute value if exist
        :rtype: str | None
        """
        # shouldn't the 'daemon_types' (whatever it is above) be always present?
        return getattr(self.conf, daemon_type + 's', None)

    def get_retention_data(self):  # pragma: no cover, useful?
        """Get data for retention

        TODO: using retention in the arbiter is dangerous and
        do not seem of any utility with Alignak

        :return: broks and external commands in a dict
        :rtype: dict
        """
        res = {
            'broks': self.broks,
            'external_commands': self.external_commands
        }
        return res

    def restore_retention_data(self, data):  # pragma: no cover, useful?
        """Restore data from retention (broks, and external commands)

        TODO: using retention in the arbiter is dangerous and
        do not seem of any utility with Alignak

        :param data: data to restore
        :type data: dict
        :return: None
        """
        broks = data['broks']
        external_commands = data['external_commands']
        self.broks.update(broks)
        self.external_commands.extend(external_commands)

    def get_stats_struct(self):
        """Get state of modules and create a scheme for stats data of daemon

        :return: A dict with the following structure
        ::

           { 'metrics': ['arbiter.%s.external-commands.queue %d %d'],
             'version': VERSION,
             'name': self.name,
             'type': 'arbiter',
             'hosts': len(self.conf.hosts)
             'services': len(self.conf.services)
             'modules':
                         {'internal': {'name': "MYMODULE1", 'state': 'ok'},
                         {'external': {'name': "MYMODULE2", 'state': 'stopped'},
                        ]
           }

        :rtype: dict
        """
        now = int(time.time())
        # call the daemon one
        res = super(Arbiter, self).get_stats_struct()
        res.update({
            'name': self.myself.get_name() if self.myself else self.name, 'type': 'arbiter'
        })
        res['hosts'] = 0
        res['services'] = 0
        if self.conf:
            res['hosts'] = len(getattr(self.conf, 'hosts', {}))
            res['services'] = len(getattr(self.conf, 'services', {}))
        metrics = res['metrics']
        # metrics specific
        metrics.append('arbiter.%s.external-commands.queue %d %d' %
                       (self.myself.get_name() if self.myself else self.name,
                        len(self.external_commands), now))

        return res
