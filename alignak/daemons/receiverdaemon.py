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
from alignak.http.client import HTTPEXCEPTIONS
from alignak.stats import statsmgr
from alignak.http.receiver_interface import ReceiverInterface

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Receiver(Satellite):
    """Receiver class. Referenced as "app" in most Interface

    """
    my_type = 'receiver'

    properties = Satellite.properties.copy()
    properties.update({
        'daemon_type':
            StringProp(default='receiver'),
        'pidfile':
            PathProp(default='receiverd.pid'),
        'port':
            IntegerProp(default=7773),
        'local_log':
            PathProp(default='receiverd.log'),
    })

    def __init__(self, config_file, is_daemon, do_replace, debug, debug_file):

        super(Receiver, self).__init__(
            'receiver', config_file, is_daemon, do_replace, debug, debug_file)

        # Our arbiters
        self.arbiters = {}

        # Our pollers and reactionners
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

        # Now create the external commands manager
        # We are a receiver: our role is to get and dispatch commands to the schedulers
        self.external_commands_manager = ExternalCommandManager(None, 'receiver', self)

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
            return
        elif cls_type == 'externalcommand':
            logger.debug("Queuing an external command: %s", str(ExternalCommand.__dict__))
            self.unprocessed_external_commands.append(elt)

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

    def manage_brok(self, brok):
        """Send brok to modules. Modules have to implement their own manage_brok function.
        They usually do if they inherits from basemodule
        REF: doc/receiver-modules.png (4-5)

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
        Implements specific setup for receiver

        :return: None
        """
        with self.conf_lock:
            conf = unserialize(self.new_conf, True)
            self.new_conf = None
            self.cur_conf = conf
            # Got our name from the globals
            if 'receiver_name' in conf['global']:
                name = conf['global']['receiver_name']
            else:
                name = 'Unnamed receiver'
            self.name = name
            # Set my own process title
            self.set_proctitle(self.name)
            # local statsd
            self.statsd_host = conf['global']['statsd_host']
            self.statsd_port = conf['global']['statsd_port']
            self.statsd_prefix = conf['global']['statsd_prefix']
            self.statsd_enabled = conf['global']['statsd_enabled']

            statsmgr.register(self.name, 'receiver',
                              statsd_host=self.statsd_host, statsd_port=self.statsd_port,
                              statsd_prefix=self.statsd_prefix, statsd_enabled=self.statsd_enabled)

            self.accept_passive_unknown_check_results = \
                conf['global']['accept_passive_unknown_check_results']
            # Update External Commands Manager
            self.external_commands_manager.accept_passive_unknown_check_results = \
                conf['global']['accept_passive_unknown_check_results']

            g_conf = conf['global']

            logger.info("[%s] Sending us a configuration", self.name)

            # If we've got something in the schedulers, we do not want it anymore
            self.host_assoc = {}
            for sched_id in conf['schedulers']:

                old_sched_id = self.get_previous_sched_id(conf['schedulers'][sched_id], sched_id)

                if old_sched_id:
                    logger.info("[%s] We already got the conf %s (%s)",
                                self.name, old_sched_id, name)
                    wait_homerun = self.schedulers[old_sched_id]['wait_homerun']
                    actions = self.schedulers[old_sched_id]['actions']
                    external_commands = self.schedulers[old_sched_id]['external_commands']
                    con = self.schedulers[old_sched_id]['con']
                    del self.schedulers[old_sched_id]

                sched = conf['schedulers'][sched_id]
                self.schedulers[sched_id] = sched

                self.push_host_names(sched_id, sched['hosts'])

                if sched['name'] in g_conf['satellitemap']:
                    sched.update(g_conf['satellitemap'][sched['name']])

                proto = 'http'
                if sched['use_ssl']:
                    proto = 'https'
                uri = '%s://%s:%s/' % (proto, sched['address'], sched['port'])

                self.schedulers[sched_id]['uri'] = uri
                if old_sched_id:
                    self.schedulers[sched_id]['wait_homerun'] = wait_homerun
                    self.schedulers[sched_id]['actions'] = actions
                    self.schedulers[sched_id]['external_commands'] = external_commands
                    self.schedulers[sched_id]['con'] = con
                else:
                    self.schedulers[sched_id]['wait_homerun'] = {}
                    self.schedulers[sched_id]['actions'] = {}
                    self.schedulers[sched_id]['external_commands'] = []
                    self.schedulers[sched_id]['con'] = None
                self.schedulers[sched_id]['running_id'] = 0
                self.schedulers[sched_id]['active'] = sched['active']
                self.schedulers[sched_id]['timeout'] = sched['timeout']
                self.schedulers[sched_id]['data_timeout'] = sched['data_timeout']

                # Do not connect if we are a passive satellite
                if not old_sched_id:
                    # And then we connect to it :)
                    self.pynag_con_init(sched_id)

            logger.debug("We have our schedulers: %s", self.schedulers)
            logger.info("We have our schedulers:")
            for daemon in self.schedulers.values():
                logger.info(" - %s ", daemon['name'])

            if not self.have_modules:
                self.modules = conf['global']['modules']
                self.have_modules = True

                self.do_load_modules(self.modules)
                # and start external modules too
                self.modules_manager.start_external_instances()

            # Set our giving timezone from arbiter
            use_timezone = conf['global']['use_timezone']
            if use_timezone != 'NOTSET':
                logger.info("Setting our timezone to %s", use_timezone)
                os.environ['TZ'] = use_timezone
                time.tzset()

    def push_external_commands_to_schedulers(self):
        """Send a HTTP request to the schedulers (POST /run_external_commands)
        with external command list.

        :return: None
        """
        if not self.unprocessed_external_commands:
            return

        commands_to_process = self.unprocessed_external_commands
        self.unprocessed_external_commands = []
        logger.debug("Commands: %s", commands_to_process)
        statsmgr.gauge('external-commands.pushed', len(self.unprocessed_external_commands))

        # Now get all external commands and put them into the
        # good schedulers
        for ext_cmd in commands_to_process:
            self.external_commands_manager.resolve_command(ext_cmd)
            logger.debug("Resolved command: %s", ext_cmd)

        # Now for all alive schedulers, send the commands
        for sched_id in self.schedulers:
            sched = self.schedulers[sched_id]
            extcmds = sched['external_commands']
            cmds = [extcmd.cmd_line for extcmd in extcmds]
            con = sched.get('con', None)
            sent = False
            if not con:
                logger.warning("The scheduler is not connected %s", sched)
                self.pynag_con_init(sched_id)
                con = sched.get('con', None)

            # If there are commands and the scheduler is alive
            if len(cmds) > 0 and con:
                logger.debug("Sending %d commands to scheduler %s", len(cmds), sched)
                try:
                    # con.run_external_commands(cmds)
                    con.post('run_external_commands', {'cmds': cmds})
                    sent = True
                # Not connected or sched is gone
                except (HTTPEXCEPTIONS, KeyError), exp:
                    logger.warning('manage_returns exception:: %s,%s ', type(exp), str(exp))
                    logger.warning("Connection problem to the scheduler %s: %s",
                                   sched, str(exp))
                    self.pynag_con_init(sched_id)
                    return
                except AttributeError, exp:  # the scheduler must  not be initialized
                    logger.debug('manage_returns exception:: %s,%s ', type(exp), str(exp))
                except Exception, exp:
                    logger.error("A satellite raised an unknown exception: %s (%s)", exp, type(exp))
                    raise

            # Whether we sent the commands or not, clean the scheduler list
            self.schedulers[sched_id]['external_commands'] = []

            # If we didn't sent them, add the commands to the arbiter list
            if not sent:
                for extcmd in extcmds:
                    self.external_commands.append(extcmd)

    def do_loop_turn(self):
        """Receiver daemon main loop

        :return: None
        """

        # Begin to clean modules
        self.check_and_del_zombie_modules()

        # Now we check if arbiter speak to us.
        # If so, we listen for it
        # When it push us conf, we reinit connections
        self.watch_for_new_conf(0.0)
        if self.new_conf:
            self.setup_new_conf()

        # Maybe external modules raised 'objects'
        # we should get them
        _t0 = time.time()
        self.get_objects_from_from_queues()
        statsmgr.timer('core.get-objects-from-queues', time.time() - _t0)

        _t0 = time.time()
        self.push_external_commands_to_schedulers()
        statsmgr.timer('core.push-external-commands', time.time() - _t0)

        # Maybe we do not have something to do, so we wait a little
        if len(self.broks) == 0:
            self.watch_for_new_conf(1.0)

    def main(self):
        """Main receiver function
        Init daemon and loop forever

        :return: None
        """
        try:
            self.setup_alignak_logger()

            # Look if we are enabled or not. If ok, start the daemon mode
            self.look_for_early_exit()

            self.do_daemon_init_and_start()

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
