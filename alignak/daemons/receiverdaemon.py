# -*- coding: utf-8 -*-
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
#     xkilian, fmikus@acktomic.com
#     Peter Woodman, peter@shortbus.org
#     Guillaume Bour, guillaume@bour.cc
#     Alexandre Viau, alexandre@alexandreviau.net
#     aviau, alexandre.viau@savoirfairelinux.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
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
This module provide Receiver class used to run a receiver daemon
"""
import time
import traceback
import logging

from alignak.brok import Brok
from alignak.objects.satellitelink import LinkError
from alignak.misc.serialization import unserialize, AlignakClassLookupException
from alignak.satellite import Satellite
from alignak.property import IntegerProp, StringProp
from alignak.external_command import ExternalCommand, ExternalCommandManager
from alignak.stats import statsmgr
from alignak.http.generic_interface import GenericInterface

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Receiver(Satellite):
    """Receiver class. Referenced as "app" in most Interface

    """
    my_type = 'receiver'

    properties = Satellite.properties.copy()
    properties.update({
        'type':
            StringProp(default='receiver'),
        'port':
            IntegerProp(default=7773)
    })

    def __init__(self, **kwargs):
        """Receiver daemon initialisation

        :param kwargs: command line arguments
        """
        super(Receiver, self).__init__(kwargs.get('daemon_name', 'Default-receiver'), **kwargs)

        # Our schedulers and arbiters are initialized in the base class

        # Our related daemons
        # self.pollers = {}
        # self.reactionners = {}

        # Modules are load one time
        self.have_modules = False

        # Now an external commands manager and a list for the external_commands
        self.external_commands_manager = None

        # and the unprocessed one, a buffer
        self.unprocessed_external_commands = []

        self.accept_passive_unknown_check_results = False

        self.http_interface = GenericInterface(self)

    def add(self, elt):
        """Generic function to add objects to the daemon internal lists.
        Manage Broks, External commands

        :param elt: object to add
        :type elt: alignak.AlignakObject
        :return: None
        """
        # todo: fix this ... external commands are returned as a dictionary!!!
        if isinstance(elt, dict) and 'my_type' in elt and elt['my_type'] == "externalcommand":
            logger.warning("Queuing a dictionary external command: %s", elt)
            elt = ExternalCommand(elt['cmd_line'], elt['creation_timestamp'])

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
            logger.debug("Queuing an external command: %s", str(ExternalCommand.__dict__))
            self.unprocessed_external_commands.append(elt)
            statsmgr.counter('external-commands.added', 1)

    def setup_new_conf(self):
        """Receiver custom setup_new_conf method

        This function calls the base satellite treatment and manages the configuration needed
        for a receiver daemon:
        - get and configure its satellites
        - configure the modules

        :return: None
        """
        # Execute the base class treatment...
        super(Receiver, self).setup_new_conf()

        # ...then our own specific treatment!
        with self.conf_lock:
            # self_conf is our own configuration from the alignak environment
            self_conf = self.cur_conf['self_conf']

            # Configure and start our modules
            if not self.have_modules:
                try:
                    self.modules = unserialize(self.cur_conf['modules'], no_load=True)
                except AlignakClassLookupException as exp:  # pragma: no cover, simple protection
                    logger.error('Cannot un-serialize modules configuration '
                                 'received from arbiter: %s', exp)
                if self.modules:
                    logger.info("I received some modules configuration: %s", self.modules)
                    self.have_modules = True

                    self.do_load_modules(self.modules)
                    # and start external modules too
                    self.modules_manager.start_external_instances()
                else:
                    logger.info("I do not have modules")

            # Now create the external commands manager
            # We are a receiver: our role is to get and dispatch commands to the schedulers
            self.external_commands_manager = \
                ExternalCommandManager(None, 'receiver', self,
                                       self_conf.get('accept_passive_unknown_check_results', False))

            # Initialize connection with all our satellites
            logger.info("Initializing connection with my satellites:")
            my_satellites = self.get_links_of_type(s_type='')
            for satellite in list(my_satellites.values()):
                logger.info("- : %s/%s", satellite.type, satellite.name)
                if not self.daemon_connection_init(satellite):
                    logger.error("Satellite connection failed: %s", satellite)

        # Now I have a configuration!
        self.have_conf = True

    def get_external_commands_from_arbiters(self):
        """Get external commands from our arbiters

        As of now, only the arbiter are requested to provide their external commands that
        the receiver will push to all the known schedulers to make them being executed.

        :return: None
        """
        for arbiter_link_uuid in self.arbiters:
            link = self.arbiters[arbiter_link_uuid]

            if not link.active:
                logger.debug("The arbiter '%s' is not active, it is not possible to get "
                             "its external commands!", link.name)
                continue

            try:
                logger.debug("Getting external commands from: %s", link.name)
                external_commands = link.get_external_commands()
                if external_commands:
                    logger.debug("Got %d commands from: %s", len(external_commands), link.name)
                else:
                    # Simple protection against None value
                    external_commands = []
                for external_command in external_commands:
                    self.add(external_command)
            except LinkError:
                logger.warning("Arbiter connection failed, I could not get external commands!")
            except Exception as exp:  # pylint: disable=broad-except
                logger.error("Arbiter connection failed, I could not get external commands!")
                logger.exception("Exception: %s", exp)

    def push_external_commands_to_schedulers(self):
        """Push received external commands to the schedulers

        :return: None
        """
        if not self.unprocessed_external_commands:
            return

        # Those are the global external commands
        commands_to_process = self.unprocessed_external_commands
        self.unprocessed_external_commands = []
        logger.debug("Commands: %s", commands_to_process)

        # Now get all external commands and put them into the good schedulers
        logger.debug("Commands to process: %d commands", len(commands_to_process))
        for ext_cmd in commands_to_process:
            cmd = self.external_commands_manager.resolve_command(ext_cmd)
            logger.debug("Resolved command: %s, result: %s", ext_cmd.cmd_line, cmd)
            if cmd and cmd['global']:
                # Send global command to all our schedulers
                for scheduler_link_uuid in self.schedulers:
                    self.schedulers[scheduler_link_uuid].pushed_commands.append(ext_cmd)

        # Now for all active schedulers, send the commands
        count_pushed_commands = 0
        count_failed_commands = 0
        for scheduler_link_uuid in self.schedulers:
            link = self.schedulers[scheduler_link_uuid]

            if not link.active:
                logger.debug("The scheduler '%s' is not active, it is not possible to push "
                             "external commands to its connection!", link.name)
                continue

            # If there are some commands for this scheduler...
            commands = [ext_cmd.cmd_line for ext_cmd in link.pushed_commands]
            if not commands:
                logger.debug("The scheduler '%s' has no commands.", link.name)
                continue

            logger.debug("Sending %d commands to scheduler %s", len(commands), link.name)
            sent = []
            try:
                sent = link.push_external_commands(commands)
            except LinkError:
                logger.warning("Scheduler connection failed, I could not push external commands!")

            # Whether we sent the commands or not, clean the scheduler list
            link.pushed_commands = []

            # If we didn't sent them, add the commands to the arbiter list
            if sent:
                statsmgr.gauge('external-commands.pushed.%s' % link.name, len(commands))
                count_pushed_commands = count_pushed_commands + len(commands)
            else:
                count_failed_commands = count_failed_commands + len(commands)
                statsmgr.gauge('external-commands.failed.%s' % link.name, len(commands))
                # Kepp the not sent commands... for a next try
                self.external_commands.extend(commands)

        statsmgr.gauge('external-commands.pushed.all', count_pushed_commands)
        statsmgr.gauge('external-commands.failed.all', count_failed_commands)

    def do_loop_turn(self):
        """Receiver daemon main loop

        :return: None
        """

        # Begin to clean modules
        self.check_and_del_zombie_modules()

        # Maybe the arbiter pushed a new configuration...
        if self.watch_for_new_conf(timeout=0.05):
            logger.info("I got a new configuration...")
            # Manage the new configuration
            self.setup_new_conf()

        # Maybe external modules raised 'objects'
        # we should get them
        _t0 = time.time()
        self.get_objects_from_from_queues()
        statsmgr.timer('core.get-objects-from-queues', time.time() - _t0)

        # Get external commands from the arbiters...
        _t0 = time.time()
        self.get_external_commands_from_arbiters()
        statsmgr.timer('external-commands.got.time', time.time() - _t0)
        statsmgr.gauge('external-commands.got.count', len(self.unprocessed_external_commands))

        _t0 = time.time()
        self.push_external_commands_to_schedulers()
        statsmgr.timer('external-commands.pushed.time', time.time() - _t0)

        # Say to modules it's a new tick :)
        _t0 = time.time()
        self.hook_point('tick')
        statsmgr.timer('hook.tick', time.time() - _t0)

    def get_daemon_stats(self, details=False):
        """Increase the stats provided by the Daemon base class

        :return: stats dictionary
        :rtype: dict
        """
        # Call the base Daemon one
        res = super(Receiver, self).get_daemon_stats(details=details)

        res.update({'name': self.name, 'type': self.type})

        counters = res['counters']
        counters['external-commands'] = len(self.external_commands)
        counters['external-commands-unprocessed'] = len(self.unprocessed_external_commands)

        return res

    def main(self):
        """Main receiver function
        Init daemon and loop forever

        :return: None
        """
        try:
            # Start the daemon mode
            if not self.do_daemon_init_and_start():
                self.exit_on_error(message="Daemon initialization error", exit_code=3)

            #  We wait for initial conf
            self.wait_for_initial_conf()
            if self.new_conf:
                # Setup the received configuration
                self.setup_new_conf()

                # Now the main loop
                self.do_main_loop()
                logger.info("Exited from the main loop.")

            self.request_stop()
        except Exception:  # pragma: no cover, this should never happen indeed ;)
            self.exit_on_exception(traceback.format_exc())
            raise
