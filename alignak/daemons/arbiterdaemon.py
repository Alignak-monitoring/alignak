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
This module provie Arbiter class used to run a arbiter daemon
"""
import sys
import os
import time
import traceback
import socket
import cStringIO
import cPickle
import json

from alignak.objects.config import Config
from alignak.external_command import ExternalCommandManager
from alignak.dispatcher import Dispatcher
from alignak.daemon import Daemon
from alignak.log import logger
from alignak.stats import statsmgr
from alignak.brok import Brok
from alignak.external_command import ExternalCommand
from alignak.property import BoolProp
from alignak.http.arbiter_interface import ArbiterInterface


class Arbiter(Daemon):
    """Arbiter class. Referenced as "app" in most Interface

    """

    def __init__(self, config_files, is_daemon, do_replace, verify_only, debug,
                 debug_file, profile=None, analyse=None, migrate=None, arb_name=''):

        super(Arbiter, self).__init__('arbiter', config_files[0], is_daemon, do_replace,
                                      debug, debug_file)

        self.config_files = config_files
        self.verify_only = verify_only
        self.analyse = analyse
        self.migrate = migrate
        self.arb_name = arb_name

        self.broks = {}
        self.is_master = False
        self.myself = None

        self.nb_broks_send = 0

        # Now tab for external_commands
        self.external_commands = []

        self.fifo = None

        # Used to work out if we must still be alive or not
        self.must_run = True

        self.http_interface = ArbiterInterface(self)
        self.conf = Config()

    def add(self, b):
        """Generic function to add objects to queues.
        Only manage Broks and ExternalCommand

        :param b: objects to add
        :type b: alignak.brok.Brok | alignak.external_command.ExternalCommand
        :return: None
        """
        if isinstance(b, Brok):
            self.broks[b._id] = b
        elif isinstance(b, ExternalCommand):
            self.external_commands.append(b)
        else:
            logger.warning('Cannot manage object type %s (%s)', type(b), b)

    def push_broks_to_broker(self):
        """Send all broks from arbiter internal list to broker

        :return: None
        """
        for brk in self.conf.brokers:
            # Send only if alive of course
            if brk.manage_arbiters and brk.alive:
                is_send = brk.push_broks(self.broks)
                if is_send:
                    # They are gone, we keep none!
                    self.broks.clear()

    def get_external_commands_from_satellites(self):
        """Get external commands from all other satellites

        :return: None
        """
        sat_lists = [self.conf.brokers, self.conf.receivers,
                     self.conf.pollers, self.conf.reactionners]
        for lst in sat_lists:
            for sat in lst:
                # Get only if alive of course
                if sat.alive:
                    new_cmds = sat.get_external_commands()
                    for new_cmd in new_cmds:
                        self.external_commands.append(new_cmd)

    def get_broks_from_satellitelinks(self):
        """Get broks from my internal satellitelinks (satellite status)

        :return: None
        TODO: Why satellitelink obj have broks and not the app itself?
        """
        tabs = [self.conf.brokers, self.conf.schedulers,
                self.conf.pollers, self.conf.reactionners,
                self.conf.receivers]
        for tab in tabs:
            for sat in tab:
                new_broks = sat.get_all_broks()
                for brok in new_broks:
                    self.add(brok)

    def get_initial_broks_from_satellitelinks(self):
        """Get initial broks from my internal satellitelinks (satellite status)

        :return: None
        """
        tabs = [self.conf.brokers, self.conf.schedulers,
                self.conf.pollers, self.conf.reactionners,
                self.conf.receivers]
        for tab in tabs:
            for sat in tab:
                brok = sat.get_initial_status_brok()
                self.add(brok)

    def load_external_command(self, ecm):
        """Set external_command attribute to the external command manager
        and fifo attribute to a new fifo fd

        :param ecm: External command manager to set
        :type ecm: alignak.external_command.ExternalCommandManager
        :return: None
        TODO: Is fifo useful?
        """
        self.external_command = ecm
        self.fifo = ecm.open()

    def get_daemon_links(self, daemon_type):
        """Get the name of arbiter link (here arbiters)

        :param daemon_type: daemon type
        :type daemon_type: str
        :return: named used to stroke this deamon type links
        :rtype: str
        """
        # the attribute name to get these differs for schedulers and arbiters
        return daemon_type + 's'

    def load_config_file(self):
        """Load main configuration file (alignak.cfg)::

        * Read all files given in the -c parameters
        * Read all .cfg files in  cfg_dir
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
        logger.info("Loading configuration")
        # REF: doc/alignak-conf-dispatching.png (1)
        buf = self.conf.read_config(self.config_files)
        raw_objects = self.conf.read_config_buf(buf)

        logger.debug("Opening local log file")

        # First we need to get arbiters and modules
        # so we can ask them for objects
        self.conf.create_objects_for_type(raw_objects, 'arbiter')
        self.conf.create_objects_for_type(raw_objects, 'module')

        self.conf.early_arbiter_linking()

        # Search which Arbiterlink I am
        for arb in self.conf.arbiters:
            if arb.is_me(self.arb_name):
                arb.need_conf = False
                self.myself = arb
                self.is_master = not self.myself.spare
                if self.is_master:
                    logger.info("I am the master Arbiter: %s", arb.get_name())
                else:
                    logger.info("I am a spare Arbiter: %s", arb.get_name())
                # export this data to our statsmgr object :)
                api_key = getattr(self.conf, 'api_key', '')
                secret = getattr(self.conf, 'secret', '')
                http_proxy = getattr(self.conf, 'http_proxy', '')
                statsd_host = getattr(self.conf, 'statsd_host', 'localhost')
                statsd_port = getattr(self.conf, 'statsd_port', 8125)
                statsd_prefix = getattr(self.conf, 'statsd_prefix', 'alignak')
                statsd_enabled = getattr(self.conf, 'statsd_enabled', False)
                statsmgr.register(self, arb.get_name(), 'arbiter',
                                  api_key=api_key, secret=secret, http_proxy=http_proxy,
                                  statsd_host=statsd_host, statsd_port=statsd_port,
                                  statsd_prefix=statsd_prefix, statsd_enabled=statsd_enabled)

                # Set myself as alive ;)
                self.myself.alive = True
            else:  # not me
                arb.need_conf = True

        if not self.myself:
            sys.exit("Error: I cannot find my own Arbiter object, I bail out. \
                     To solve it, please change the host_name parameter in \
                     the object Arbiter in the file alignak-specific.cfg. \
                     With the value %s \
                     Thanks." % socket.gethostname())

        logger.info("My own modules: " + ','.join([m.get_name() for m in self.myself.modules]))

        self.modules_dir = getattr(self.conf, 'modules_dir', '')

        # Ok it's time to load the module manager now!
        self.load_modules_manager()
        # we request the instances without them being *started*
        # (for those that are concerned ("external" modules):
        # we will *start* these instances after we have been daemonized (if requested)
        self.modules_manager.set_modules(self.myself.modules)
        self.do_load_modules()

        # Call modules that manage this read configuration pass
        self.hook_point('read_configuration')

        # Call modules get_objects() to load new objects from them
        # (example modules: glpi, mongodb, dummy_arbiter)
        self.load_modules_configuration_objects(raw_objects)

        # Resume standard operations ###
        self.conf.create_objects(raw_objects)

        # Maybe conf is already invalid
        if not self.conf.conf_is_correct:
            sys.exit("***> One or more problems was encountered "
                     "while processing the config files...")

        # Manage all post-conf modules
        self.hook_point('early_configuration')

        # Ok here maybe we should stop because we are in a pure migration run
        if self.migrate:
            logger.info("Migration MODE. Early exiting from configuration relinking phase")
            return

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

        # Overrides sepecific service instaces properties
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

        # Correct conf?
        self.conf.is_correct()

        # Maybe some elements where not wrong, so we must clean if possible
        self.conf.clean()

        # If the conf is not correct, we must get out now
        # if not self.conf.conf_is_correct:
        #    sys.exit("Configuration is incorrect, sorry, I bail out")

        # REF: doc/alignak-conf-dispatching.png (2)
        logger.info("Cutting the hosts and services into parts")
        self.confs = self.conf.cut_into_parts()

        # The conf can be incorrect here if the cut into parts see errors like
        # a realm with hosts and not schedulers for it
        if not self.conf.conf_is_correct:
            self.conf.show_errors()
            err = "Configuration is incorrect, sorry, I bail out"
            logger.error(err)
            sys.exit(err)

        logger.info('Things look okay - No serious problems were detected '
                    'during the pre-flight check')

        # Clean objects of temporary/unnecessary attributes for live work:
        self.conf.clean()

        # Exit if we are just here for config checking
        if self.verify_only:
            sys.exit(0)

        if self.analyse:
            self.launch_analyse()
            sys.exit(0)

        # Some properties need to be "flatten" (put in strings)
        # before being send, like realms for hosts for example
        # BEWARE: after the cutting part, because we stringify some properties
        self.conf.prepare_for_sending()

        # Ok, here we must check if we go on or not.
        # TODO: check OK or not
        self.log_level = self.conf.log_level
        self.use_local_log = self.conf.use_local_log
        self.local_log = self.conf.local_log
        self.pidfile = os.path.abspath(self.conf.lock_file)
        self.idontcareaboutsecurity = self.conf.idontcareaboutsecurity
        self.user = self.conf.alignak_user
        self.group = self.conf.alignak_group
        self.daemon_enabled = self.conf.daemon_enabled
        self.daemon_thread_pool_size = self.conf.daemon_thread_pool_size

        self.accept_passive_unknown_check_results = BoolProp.pythonize(
            getattr(self.myself, 'accept_passive_unknown_check_results', '0')
        )

        # If the user sets a workdir, lets use it. If not, use the
        # pidfile directory
        if self.conf.workdir == '':
            self.workdir = os.path.abspath(os.path.dirname(self.pidfile))
        else:
            self.workdir = self.conf.workdir

        #  We need to set self.host & self.port to be used by do_daemon_init_and_start
        self.host = self.myself.address
        self.port = self.myself.port

        logger.info("Configuration Loaded")

    def load_modules_configuration_objects(self, raw_objects):
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
            if hasattr(inst, 'get_objects'):
                _t0 = time.time()
                try:
                    objs = inst.get_objects()
                except Exception, exp:
                    logger.error("Instance %s raised an exception %s. Log and continue to run",
                                 inst.get_name(), str(exp))
                    output = cStringIO.StringIO()
                    traceback.print_exc(file=output)
                    logger.error("Back trace of this remove: %s", output.getvalue())
                    output.close()
                    continue
                statsmgr.incr('hook.get-objects', time.time() - _t0)
                types_creations = self.conf.types_creations
                for type_c in types_creations:
                    (cls, clss, prop, dummy) = types_creations[type_c]
                    if prop in objs:
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

    def launch_analyse(self):
        """Print the number of objects we have for each type.

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

    def go_migrate(self):
        """Migrate configuration

        :return: None
        TODO: Remove it
        """
        print "***********" * 5
        print "WARNING : this feature is NOT supported in this version!"
        print "***********" * 5

        migration_module_name = self.migrate.strip()
        mig_mod = self.conf.modules.find_by_name(migration_module_name)
        if not mig_mod:
            print "Cannot find the migration module %s. Please configure it" % migration_module_name
            sys.exit(2)

        print self.modules_manager.instances
        # Ok now all we need is the import module
        self.modules_manager.set_modules([mig_mod])
        self.do_load_modules()
        print self.modules_manager.instances
        if len(self.modules_manager.instances) == 0:
            print "Error during the initialization of the import module. Bailing out"
            sys.exit(2)
        print "Configuration migrating in progress..."
        mod = self.modules_manager.instances[0]
        fun = getattr(mod, 'import_objects', None)
        if not fun or not callable(fun):
            print "Import module is missing the import_objects function. Bailing out"
            sys.exit(2)

        objs = {}
        types = ['hosts', 'services', 'commands', 'timeperiods', 'contacts']
        for o_type in types:
            print "New type", o_type
            objs[o_type] = []
            for items in getattr(self.conf, o_type):
                dct = items.get_raw_import_values()
                if dct:
                    objs[o_type].append(dct)
            fun(objs)
        # Ok we can exit now
        sys.exit(0)

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
            # Setting log level
            logger.setLevel('INFO')
            # Force the debug level if the daemon is said to start with such level
            if self.debug:
                logger.setLevel('DEBUG')

            # Log will be broks
            for line in self.get_header():
                logger.info(line)

            self.load_config_file()
            logger.setLevel(self.log_level)
            # Maybe we are in a migration phase. If so, we will bailout here
            if self.migrate:
                self.go_migrate()

            # Look if we are enabled or not. If ok, start the daemon mode
            self.look_for_early_exit()
            self.do_daemon_init_and_start()

            # ok we are now fully daemonized (if requested)
            # now we can start our "external" modules (if any):
            self.modules_manager.start_external_instances()

            # Ok now we can load the retention data
            self.hook_point('load_retention')

            # And go for the main loop
            self.do_mainloop()
        except SystemExit, exp:
            # With a 2.4 interpreter the sys.exit() in load_config_file
            # ends up here and must be handled.
            sys.exit(exp.code)
        except Exception, exp:
            self.print_unrecoverable(traceback.format_exc())
            raise

    def setup_new_conf(self):
        """ Setup a new conf received from a Master arbiter.

        :return: None
        """
        with self.conf_lock:
            conf = self.new_conf
            if not conf:
                return
            conf = cPickle.loads(conf)
            self.new_conf = None
            self.cur_conf = conf
            self.conf = conf
            for arb in self.conf.arbiters:
                if (arb.address, arb.port) == (self.host, self.port):
                    self.myself = arb
                    arb.is_me = lambda x: True  # we now definitively know who we are, just keep it.
                else:
                    arb.is_me = lambda x: False  # and we know who we are not, just keep it.

    def do_loop_turn(self):
        """Loop turn for Arbiter
        If master, run, else wait for master death

        :return: None
        """
        # If I am a spare, I wait for the master arbiter to send me
        # true conf.
        if self.myself.spare:
            logger.debug("I wait for master")
            self.wait_for_master_death()

        if self.must_run:
            # Main loop
            self.run()

    def wait_for_master_death(self):
        """Wait for a master timeout and take the lead if necessary

        :return: None
        """
        logger.info("Waiting for master death")
        timeout = 1.0
        self.last_master_speack = time.time()

        # Look for the master timeout
        master_timeout = 300
        for arb in self.conf.arbiters:
            if not arb.spare:
                master_timeout = arb.check_interval * arb.max_check_attempts
        logger.info("I'll wait master for %d seconds", master_timeout)

        while not self.interrupted:
            # This is basically sleep(timeout) and returns 0, [], int
            # We could only paste here only the code "used" but it could be
            # harder to maintain.
            _, _, tcdiff = self.handle_requests(timeout)
            # if there was a system Time Change (tcdiff) then we have to adapt last_master_speak:
            if self.new_conf:
                self.setup_new_conf()
            if tcdiff:
                self.last_master_speack += tcdiff
            sys.stdout.write(".")
            sys.stdout.flush()

            # Now check if master is dead or not
            now = time.time()
            if now - self.last_master_speack > master_timeout:
                logger.info("Arbiter Master is dead. The arbiter %s take the lead",
                            self.myself.get_name())
                for arb in self.conf.arbiters:
                    if not arb.spare:
                        arb.alive = False
                self.must_run = True
                break

    def push_external_commands_to_schedulers(self):
        """Send external commands to schedulers

        :return: None
        """
        # Now get all external commands and put them into the
        # good schedulers
        for ext_cmd in self.external_commands:
            self.external_command.resolve_command(ext_cmd)

        # Now for all alive schedulers, send the commands
        for sched in self.conf.schedulers:
            cmds = sched.external_commands
            if len(cmds) > 0 and sched.alive:
                logger.debug("Sending %d commands to scheduler %s", len(cmds), sched.get_name())
                sched.run_external_commands(cmds)
            # clean them
            sched.external_commands = []

    def check_and_log_tp_activation_change(self):
        """Raise log for timeperiod change (useful for debug)

        :return: None
        """
        for timeperiod in self.conf.timeperiods:
            timeperiod.check_and_log_activation_change()

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
        for arb in self.conf.arbiters:
            if arb.is_me(self.arb_name):
                self.myself = arb

        if self.conf.human_timestamp_log:
            logger.set_human_format()
        logger.info("Begin to dispatch configurations to satellites")
        self.dispatcher = Dispatcher(self.conf, self.myself)
        self.dispatcher.check_alive()
        self.dispatcher.check_dispatch()
        # REF: doc/alignak-conf-dispatching.png (3)
        self.dispatcher.dispatch()

        # Now we can get all initial broks for our satellites
        self.get_initial_broks_from_satellitelinks()

        suppl_socks = None

        # Now create the external commander. It's just here to dispatch
        # the commands to schedulers
        ecm = ExternalCommandManager(self.conf, 'dispatcher')
        ecm.load_arbiter(self)
        self.external_command = ecm

        logger.debug("Run baby, run...")
        timeout = 1.0

        while self.must_run and not self.interrupted:
            # This is basically sleep(timeout) and returns 0, [], int
            # We could only paste here only the code "used" but it could be
            # harder to maintain.
            _ = self.handle_requests(timeout, suppl_socks)

            # Timeout
            timeout = 1.0  # reset the timeout value

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
            statsmgr.incr('core.check-alive', time.time() - _t0)

            _t0 = time.time()
            self.dispatcher.check_dispatch()
            statsmgr.incr('core.check-dispatch', time.time() - _t0)

            # REF: doc/alignak-conf-dispatching.png (3)
            _t0 = time.time()
            self.dispatcher.dispatch()
            statsmgr.incr('core.dispatch', time.time() - _t0)

            _t0 = time.time()
            self.dispatcher.check_bad_dispatch()
            statsmgr.incr('core.check-bad-dispatch', time.time() - _t0)

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
            statsmgr.incr('core.push-external-commands', time.time() - _t0)

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

    def get_retention_data(self):
        """Get data for retention

        :return: broks and external commands in a dict
        :rtype: dict
        """
        res = {
            'broks': self.broks,
            'external_commands': self.external_commands
        }
        return res

    def restore_retention_data(self, data):
        """Restore data from retention (broks, and external commands)

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
             'version': __version__,
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
        res.update({'name': self.myself.get_name(), 'type': 'arbiter'})
        res['hosts'] = len(self.conf.hosts)
        res['services'] = len(self.conf.services)
        metrics = res['metrics']
        # metrics specific
        metrics.append('arbiter.%s.external-commands.queue %d %d' %
                       (self.myself.get_name(), len(self.external_commands), now))

        return res
