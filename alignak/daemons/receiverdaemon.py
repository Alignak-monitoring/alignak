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
import os
import time
import traceback
import logging
from multiprocessing import active_children

from alignak.misc.serialization import unserialize
from alignak.satellite import Satellite
from alignak.property import PathProp, IntegerProp, StringProp
from alignak.external_command import ExternalCommand, ExternalCommandManager
from alignak.http.client import HTTPClientException, HTTPClientConnectionException
from alignak.http.client import HTTPClientTimeoutException
from alignak.stats import statsmgr
from alignak.http.receiver_interface import ReceiverInterface

logger = logging.getLogger(__name__)  # pylint: disable=C0103


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

        # Our related daemons
        self.arbiters = {}
        self.pollers = {}
        self.reactionners = {}

        # Modules are load one time
        self.have_modules = False

        # Now an external commands manager and a list for the external_commands
        self.external_commands_manager = None
        self.external_commands = []
        # and the unprocessed one, a buffer
        self.unprocessed_external_commands = []

        self.host_assoc = {}
        self.accept_passive_unknown_check_results = False

        self.http_interface = ReceiverInterface(self)

    def add(self, elt):
        """Add an object to the receiver one
        Handles brok and externalcommand

        :param elt: object to add
        :type elt: object
        :return: None
        """
        cls_type = elt.__class__.my_type
        if cls_type == 'brok':
            # For brok, we TAG brok with our instance_id
            elt.instance_id = 0
            self.broks[elt.uuid] = elt
            statsmgr.counter('broks.added', 1)
            return
        elif cls_type == 'externalcommand':
            logger.debug("Queuing an external command: %s", str(ExternalCommand.__dict__))
            self.unprocessed_external_commands.append(elt)
            statsmgr.counter('external-commands.added', 1)

    def push_host_names(self, sched_id, hnames):
        """Link hostnames to scheduler id.
        Called by alignak.satellite.IForArbiter.push_host_names

        :param sched_id: scheduler id to link to
        :type sched_id: int
        :param hnames: host names list
        :type hnames: list
        :return: None
        """
        for h_name in hnames:
            self.host_assoc[h_name] = sched_id

    def get_sched_from_hname(self, hname):
        """Get scheduler linked to the given host_name

        :param hname: host_name we want the scheduler from
        :type hname: str
        :return: scheduler with id corresponding to the mapping table
        :rtype: dict
        """
        item = self.host_assoc.get(hname, None)
        sched = self.schedulers.get(item, None)
        return sched

    def manage_brok(self, brok):  # pragma: no cover, seems not to be used anywhere
        """Send brok to modules. Modules have to implement their own manage_brok function.
        They usually do if they inherits from basemodule
        REF: doc/receiver-modules.png (4-5)

        TODO: why should this daemon manage a brok? It is the brokers job!!!

        :param brok: brok to manage
        :type brok: alignak.brok.Brok
        :return: None
        """
        to_del = []
        # Call all modules if they catch the call
        for mod in self.modules_manager.get_internal_instances():
            try:
                mod.manage_brok(brok)
            except Exception, exp:  # pylint: disable=W0703
                logger.warning("The mod %s raise an exception: %s, I kill it",
                               mod.get_name(), str(exp))
                logger.warning("Exception type: %s", type(exp))
                logger.warning("Back trace of this kill: %s", traceback.format_exc())
                to_del.append(mod)
        # Now remove mod that raise an exception
        self.modules_manager.clear_instances(to_del)

    def do_stop(self):
        """Stop the Receiver
        Wait for children to stop and call super(Receiver, self).do_stop()

        :return: None
        """

        act = active_children()
        for child in act:
            child.terminate()
            child.join(1)
        super(Receiver, self).do_stop()

    def setup_new_conf(self):
        """Receiver custom setup_new_conf method

        This function calls the base satellite treatment and manages the configuration needed
        for a broker daemon:
        - get and configure its pollers, reactionners and receivers relation
        - configure the modules

        :return: None
        """
        # Execute the base class treatment...
        super(Receiver, self).setup_new_conf()

        # ...then our own specific treatment!
        with self.conf_lock:
            print("Receiver - New configuration for: %s / %s" % (self.type, self.name))
            logger.info("[%s] Received a new configuration", self.name)
            print("Receiver - My schedulers: %s" % self.schedulers)

            # self_conf is our own configuration from the alignak environment
            self_conf = self.cur_conf['self_conf']

            # If we've got something in the schedulers, we do not want it anymore
            # Beware that schedulers are not SchedulerLink objects
            # but only schedulers configuration!
            self.host_assoc = {}
            # For each scheduler, we received its managed hosts list
            for link_uuid in self.schedulers:
                # We received the hosts names for each scheduler
                print("Received hosts names: %s" % self.schedulers[link_uuid].hosts_names)
                self.push_host_names(link_uuid, self.schedulers[link_uuid].hosts_names)

            # Configure and start our modules
            if not self.have_modules:
                self.modules = self_conf['modules']
                self.have_modules = True

                self.do_load_modules(self.modules)
                # and start external modules too
                self.modules_manager.start_external_instances()

            # Now create the external commands manager
            # We are a receiver: our role is to get and dispatch commands to the schedulers
            self.external_commands_manager = \
                ExternalCommandManager(None, 'receiver', self,
                                       self_conf.get('accept_passive_unknown_check_results', False))

            # Initialize connection with all our satellites
            my_satellites = self.get_links_of_type(s_type=None)
            for sat_link in my_satellites:
                satellite = my_satellites[sat_link]
                print("Initialize connection with: %s" % satellite)
                self.daemon_connection_init(satellite.uuid, s_type=satellite.type)

    def push_external_commands_to_schedulers(self):
        """Send a HTTP request to the schedulers (POST /run_external_commands)
        with external command list.

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
                for scheduler_id in self.schedulers:
                    scheduler = self.schedulers[scheduler_id]
                    scheduler.external_commands.append(ext_cmd)

        # Now for all alive schedulers, send the commands
        pushed_commands = 0
        failed_commands = 0
        for scheduler_id in self.schedulers:
            scheduler = self.schedulers[scheduler_id]
            # TODO:  sched should be a SatelliteLink object and, thus, have a get_name() method
            # but sometimes when an exception is raised because the scheduler is not available
            # this is not True ... sched is a simple dictionary with a 'name' property!

            is_active = scheduler['active']
            if not is_active:
                logger.warning("The scheduler '%s' is not active, it is not possible to push "
                               "external commands from its connection!", scheduler['name'])
                return

            # If there are some commands for this scheduler...
            extcmds = scheduler['external_commands']
            cmds = [extcmd.cmd_line for extcmd in extcmds]
            if not cmds:
                logger.debug("The scheduler '%s' has no commands.", scheduler['name'])
                continue

            # ...and the scheduler is alive
            con = scheduler['con']
            if con is None:
                self.daemon_connection_init(scheduler_id, s_type='scheduler')

            if con is None:
                logger.warning("The connection for the scheduler '%s' cannot be established, it is "
                               "not possible to push external commands.", scheduler['name'])
                continue

            sent = False

            logger.debug("Sending %d commands to scheduler %s", len(cmds), scheduler['name'])
            try:
                con.post('run_external_commands', {'cmds': cmds})
                sent = True
            except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
                logger.warning("[%s] %s", scheduler['name'], str(exp))
                scheduler['con'] = None
                continue
            except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
                logger.warning("Connection timeout with the scheduler '%s' when "
                               "sending external commands: %s", scheduler['name'], str(exp))
                scheduler['con'] = None
                continue
            except HTTPClientException as exp:  # pragma: no cover, simple protection
                logger.error("Error with the scheduler '%s' when "
                             "sending external commands: %s", scheduler['name'], str(exp))
                scheduler['con'] = None
                continue
            except AttributeError as exp:  # pragma: no cover, simple protection
                logger.warning("The scheduler %s should not be initialized: %s",
                               scheduler['name'], str(exp))
                logger.exception(exp)
            except Exception as exp:  # pylint: disable=broad-except
                logger.exception("A satellite raised an unknown exception (%s): %s", type(exp), exp)
                raise

            # Whether we sent the commands or not, clean the scheduler list
            scheduler['external_commands'] = []

            # If we didn't sent them, add the commands to the arbiter list
            if sent:
                statsmgr.gauge('external-commands.pushed.%s' % scheduler['name'], len(cmds))
                pushed_commands = pushed_commands + len(cmds)
            else:
                statsmgr.gauge('external-commands.failed.%s' % scheduler['name'], len(cmds))
                failed_commands = failed_commands + len(cmds)
                for extcmd in extcmds:
                    self.external_commands.append(extcmd)

        statsmgr.gauge('external-commands.pushed.all', pushed_commands)
        statsmgr.gauge('external-commands.failed.all', failed_commands)

    def do_loop_turn(self):
        """Receiver daemon main loop

        :return: None
        """

        # Begin to clean modules
        self.check_and_del_zombie_modules()

        # Now we check if we received a new configuration - no sleep time, we will sleep later...
        self.watch_for_new_conf()
        if self.new_conf:
            self.setup_new_conf()

        # Maybe external modules raised 'objects'
        # we should get them
        _t0 = time.time()
        self.get_objects_from_from_queues()
        statsmgr.timer('core.get-objects-from-queues', time.time() - _t0)
        statsmgr.gauge('got.external-commands', len(self.unprocessed_external_commands))
        statsmgr.gauge('got.broks', len(self.broks))

        _t0 = time.time()
        self.push_external_commands_to_schedulers()
        statsmgr.timer('core.push-external-commands', time.time() - _t0)

        # Maybe we do not have something to do, so we wait a little
        # todo: check broks in the receiver ???
        if not self.broks:
            self.watch_for_new_conf(0.1)

    def main(self):
        """Main receiver function
        Init daemon and loop forever

        :return: None
        """
        try:
            self.setup_alignak_logger()

            # Look if we are enabled or not. If ok, start the daemon mode
            self.look_for_early_exit()

            # todo:
            # This function returns False if some problem is detected during initialization
            # (eg. communication port not free)
            # Perharps we should stop the initialization process and exit?
            if not self.do_daemon_init_and_start():
                return

            self.load_modules_manager(self.name)

            #  We wait for initial conf
            self.wait_for_initial_conf()
            if not self.new_conf:
                return
            self.setup_new_conf()

            # Now the main loop
            self.do_mainloop()

        except Exception:
            self.print_unrecoverable(traceback.format_exc())
            raise

    def get_stats_struct(self):
        """Get state of modules and create a scheme for stats data of daemon
        This may be overridden in subclasses

        :return: A dict with the following structure
        ::

           { 'metrics': ['%s.%s.external-commands.queue %d %d'],
             'version': VERSION,
             'name': self.name,
             'type': _type,
             'passive': self.passive,
             'modules':
                         {'internal': {'name': "MYMODULE1", 'state': 'ok'},
                         {'external': {'name': "MYMODULE2", 'state': 'stopped'},
                        ]
           }

        :rtype: dict
        """
        now = int(time.time())
        # call the daemon one
        res = super(Receiver, self).get_stats_struct()
        res.update({'name': self.name, 'type': 'receiver'})
        metrics = res['metrics']
        # metrics specific
        metrics.append('receiver.%s.external-commands.queue %d %d' % (
            self.name, len(self.external_commands), now))

        return res
