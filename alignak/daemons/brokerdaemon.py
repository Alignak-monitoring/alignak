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
#     David Moreau Simard, dmsimard@iweb.com
#     Peter Woodman, peter@shortbus.org
#     Guillaume Bour, guillaume@bour.cc
#     foomip, nelsondcp@gmail.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Arthur Gautier, superbaloo@superbaloo.net
#     Sebastien Coavoux, s.coavoux@free.fr
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     ning.xie, ning.xie@qunar.com
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
This module provide Broker class used to run a broker daemon
"""

import time
import traceback
import threading
import logging

# from multiprocessing import active_children
#
# pylint: disable=wildcard-import,unused-wildcard-import
# This import, despite not used, is necessary to include all Alignak objects modules
from alignak.objects import *
from alignak.misc.serialization import unserialize, AlignakClassLookupException
from alignak.satellite import BaseSatellite
from alignak.property import IntegerProp, StringProp, BoolProp
from alignak.stats import statsmgr
from alignak.http.broker_interface import BrokerInterface
from alignak.objects.satellitelink import SatelliteLink, LinkError
from alignak.brok import Brok
from alignak.external_command import ExternalCommand
from alignak.message import Message

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Broker(BaseSatellite):
    """
    Class to manage a Broker daemon
    A Broker is used to get data from Scheduler and send them to modules. These modules in most
    cases export to other software, databases...
    """
    properties = BaseSatellite.properties.copy()
    properties.update({
        'type':
            StringProp(default='broker'),
        'port':
            IntegerProp(default=7772),
        'got_initial_broks':
            BoolProp(default=False)

    })

    def __init__(self, **kwargs):
        """Broker daemon initialisation

        :param kwargs: command line arguments
        """
        super(Broker, self).__init__(kwargs.get('daemon_name', 'Default-broker'), **kwargs)

        # Our schedulers and arbiters are initialized in the base class

        # Our pollers, reactionners and receivers
        self.pollers = {}
        self.reactionners = {}
        self.receivers = {}

        # Modules are load one time
        self.have_modules = False

        # All broks to manage
        self.external_broks = []  # broks to manage

        # broks raised internally by the broker
        self.internal_broks = []
        # broks raised by the arbiters, we need a lock so the push can be in parallel
        # to our current activities and won't lock the arbiter
        self.arbiter_broks = []
        self.arbiter_broks_lock = threading.RLock()

        self.timeout = 1.0

        self.http_interface = BrokerInterface(self)

    def add(self, elt):
        """Generic function to add objects to the daemon internal lists.
        Manage Broks, External commands and Messages (from modules queues)

        :param elt: object to add
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
        # Maybe we got a Message from the modules, it's way to ask something
        # like from now a full data from a scheduler for example.
        elif isinstance(elt, Message):
            # We got a message, great!
            logger.debug(str(elt.__dict__))
            if elt.get_type() == 'NeedData':
                data = elt.get_data()
                # Full instance id means: I got no data for this scheduler
                # so give me all dumb-ass!
                if 'full_instance_id' in data:
                    c_id = data['full_instance_id']
                    source = elt.source
                    logger.info('The module %s is asking me to get all initial data '
                                'from the scheduler %d',
                                source, c_id)
                    # so we just reset the connection and the running_id,
                    # it will just get all new things
                    try:
                        self.schedulers[c_id]['con'] = None
                        self.schedulers[c_id]['running_id'] = 0
                    except KeyError:  # maybe this instance was not known, forget it
                        logger.warning("the module %s ask me a full_instance_id "
                                       "for an unknown ID (%d)!", source, c_id)
            # Maybe a module tells me that it's dead, I must log its last words...
            if elt.get_type() == 'ICrash':
                data = elt.get_data()
                logger.error('the module %s just crash! Please look at the traceback:',
                             data['name'])
                logger.error(data['trace'])

            statsmgr.counter('message.added', 1)
            # The module death will be looked for elsewhere and restarted.

    def manage_brok(self, brok):
        """Get a brok.
        We put brok data to the modules

        :param brok: object with data
        :type brok: object
        :return: None
        """
        # Unserialize the brok before consuming it
        brok.prepare()

        for module in self.modules_manager.get_internal_instances():
            try:
                _t0 = time.time()
                module.manage_brok(brok)
                statsmgr.timer('manage-broks.internal.%s' % module.get_name(), time.time() - _t0)
            except Exception as exp:  # pylint: disable=broad-except
                logger.warning("The module %s raised an exception: %s, "
                               "I'm tagging it to restart later", module.get_name(), str(exp))
                logger.exception(exp)
                self.modules_manager.set_to_restart(module)

    def get_internal_broks(self):
        """Get all broks from self.broks_internal_raised and append them to our broks
        to manage

        :return: None
        """
        statsmgr.gauge('get-new-broks-count.broker', len(self.internal_broks))
        # Add the broks to our global list
        self.external_broks.extend(self.internal_broks)
        self.internal_broks = []

    def get_arbiter_broks(self):
        """Get the broks from the arbiters,
        but as the arbiter_broks list can be push by arbiter without Global lock,
        we must protect this with a lock

        TODO: really? check this arbiter behavior!

        :return: None
        """
        with self.arbiter_broks_lock:
            statsmgr.gauge('get-new-broks-count.arbiter', len(self.arbiter_broks))
            # Add the broks to our global list
            self.external_broks.extend(self.arbiter_broks)
            self.arbiter_broks = []

    def get_new_broks(self):
        """Get new broks from our satellites

        :return: None
        """
        for satellites in [self.schedulers, self.pollers, self.reactionners, self.receivers]:
            for satellite_link in list(satellites.values()):
                logger.debug("Getting broks from %s", satellite_link)

                _t0 = time.time()
                try:
                    tmp_broks = satellite_link.get_broks(self.name)
                except LinkError:
                    logger.warning("Daemon %s connection failed, I could not get the broks!",
                                   satellite_link)
                else:
                    if tmp_broks:
                        logger.debug("Got %d Broks from %s in %s",
                                     len(tmp_broks), satellite_link.name, time.time() - _t0)
                        statsmgr.gauge('get-new-broks-count.%s'
                                       % (satellite_link.name), len(tmp_broks))
                        statsmgr.timer('get-new-broks-time.%s'
                                       % (satellite_link.name), time.time() - _t0)
                        for brok in tmp_broks:
                            brok.instance_id = satellite_link.instance_id

                        # Add the broks to our global list
                        self.external_broks.extend(tmp_broks)

    # def do_stop(self):
    #     """Stop all children of this process
    #
    #     :return: None
    #     """
    #     # my_active_children = active_children()
    #     # for child in my_active_children:
    #     #     child.terminate()
    #     #     child.join(1)
    #     super(Broker, self).do_stop()

    def setup_new_conf(self):
        # pylint: disable=too-many-branches, too-many-locals
        """Broker custom setup_new_conf method

        This function calls the base satellite treatment and manages the configuration needed
        for a broker daemon:
        - get and configure its pollers, reactionners and receivers relation
        - configure the modules

        :return: None
        """
        # Execute the base class treatment...
        super(Broker, self).setup_new_conf()

        # ...then our own specific treatment!
        with self.conf_lock:
            # # self_conf is our own configuration from the alignak environment
            # self_conf = self.cur_conf['self_conf']
            self.got_initial_broks = False

            # Now we create our pollers, reactionners and receivers
            for link_type in ['pollers', 'reactionners', 'receivers']:
                if link_type not in self.cur_conf['satellites']:
                    logger.error("No %s in the configuration!", link_type)
                    continue

                my_satellites = getattr(self, link_type, {})
                received_satellites = self.cur_conf['satellites'][link_type]
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
                    new_link = SatelliteLink.get_a_satellite_link(link_type[:-1],
                                                                  rs_conf)
                    my_satellites[new_link.uuid] = new_link
                    logger.info("I got a new %s satellite: %s", link_type[:-1], new_link)

                    new_link.running_id = running_id
                    new_link.external_commands = external_commands
                    new_link.broks = broks
                    new_link.wait_homerun = wait_homerun
                    new_link.actions = actions

                    # Replace satellite address and port by those defined in satellite_map
                    # todo: check if it is really necessary! Add a unit test for this
                    # Not sure about this because of the daemons/satellites configuration
                    # if new_link.name in self_conf.get('satellite_map', {}):
                    #     new_link = dict(new_link)  # make a copy
                    #     new_link.update(self_conf.get('satellite_map', {})[new_link.name])

            if not self.have_modules:
                try:
                    self.modules = unserialize(self.cur_conf['modules'], no_load=True)
                except AlignakClassLookupException as exp:  # pragma: no cover, simple protection
                    logger.error('Cannot un-serialize modules configuration '
                                 'received from arbiter: %s', exp)
                if self.modules:
                    logger.info("I received some modules configuration: %s", self.modules)
                    self.have_modules = True

                    # Ok now start, or restart them!
                    # Set modules, init them and start external ones
                    self.do_load_modules(self.modules)
                    # and start external modules too
                    self.modules_manager.start_external_instances()
                else:
                    logger.info("I do not have modules")

            # Initialize connection with my schedulers first
            logger.info("Initializing connection with my schedulers:")
            my_satellites = self.get_links_of_type(s_type='scheduler')
            for satellite in list(my_satellites.values()):
                logger.info("- %s/%s", satellite.type, satellite.name)
                if not self.daemon_connection_init(satellite):
                    logger.error("Satellite connection failed: %s", satellite)

            # Initialize connection with all our satellites
            logger.info("Initializing connection with my satellites:")
            for sat_type in ['arbiter', 'reactionner', 'poller', 'receiver']:
                my_satellites = self.get_links_of_type(s_type=sat_type)
                for satellite in list(my_satellites.values()):
                    logger.info("- %s/%s", satellite.type, satellite.name)
                    if not self.daemon_connection_init(satellite):
                        logger.error("Satellite connection failed: %s", satellite)

        # Now I have a configuration!
        self.have_conf = True

    def clean_previous_run(self):
        """Clean all (when we received new conf)

        :return: None
        """
        # Execute the base class treatment...
        super(Broker, self).clean_previous_run()

        # Clean all satellites relations
        self.pollers.clear()
        self.reactionners.clear()
        self.receivers.clear()

        # Clean our internal objects
        self.external_broks = self.external_broks[:]
        self.internal_broks = self.internal_broks[:]
        with self.arbiter_broks_lock:
            self.arbiter_broks = self.arbiter_broks[:]
        self.external_commands = self.external_commands[:]

        # And now modules
        # self.have_modules = False
        # self.modules_manager.clear_instances()

    def do_loop_turn(self):
        # pylint: disable=too-many-branches
        """Loop used to:
         * get initial status broks
         * check if modules are alive, if not restart them
         * get broks from ourself, the arbiters and our satellites
         * add broks to the queue of each external module
         * manage broks with each internal module

         If the internal broks management is longer than 0.8 seconds, postpone to hte next
         loop turn to avoid overloading the broker daemon.

         :return: None
        """
        if not self.got_initial_broks:
            # Asking initial broks from my schedulers
            my_satellites = self.get_links_of_type(s_type='scheduler')
            for satellite in list(my_satellites.values()):
                logger.info("Asking my initial broks from '%s'", satellite.name)
                _t0 = time.time()
                try:
                    my_initial_broks = satellite.get_initial_broks(self.name)
                    statsmgr.timer('broks.initial.%s.time' % satellite.name, time.time() - _t0)
                    if not my_initial_broks:
                        logger.info("No initial broks were raised, "
                                    "my scheduler is not yet ready...")
                        return

                    self.got_initial_broks = True
                    logger.debug("Got %d initial broks from '%s'",
                                 my_initial_broks, satellite.name)
                    statsmgr.gauge('broks.initial.%s.count' % satellite.name, my_initial_broks)
                except LinkError as exp:
                    logger.warning("Scheduler connection failed, I could not get initial broks!")

        logger.debug("Begin Loop: still some old broks to manage (%d)", len(self.external_broks))
        if self.external_broks:
            statsmgr.gauge('unmanaged.broks', len(self.external_broks))

        # Try to see if one of my module is dead, and restart previously dead modules
        self.check_and_del_zombie_modules()

        # Call modules that manage a starting tick pass
        _t0 = time.time()
        self.hook_point('tick')
        statsmgr.timer('hook.tick', time.time() - _t0)

        # Maybe the last loop we did raised some broks internally
        self.get_internal_broks()

        # Also reap broks sent from the arbiters
        self.get_arbiter_broks()

        # Now get broks from our distant daemons
        self.get_new_broks()

        # Get the list of broks not yet sent to our external modules
        _t0 = time.time()
        broks_to_send = [brok for brok in self.external_broks if getattr(brok, 'to_be_sent', True)]
        statsmgr.gauge('get-new-broks-count.to_send', len(broks_to_send))

        # Send the broks to all external modules to_q queue so they can get the whole packet
        # beware, the sub-process/queue can be die/close, so we put to restart the whole module
        # instead of killing ourselves :)
        for module in self.modules_manager.get_external_instances():
            try:
                _t00 = time.time()
                queue_size = module.to_q.qsize()
                statsmgr.gauge('queues.external.%s.to.size' % module.get_name(), queue_size)
                module.to_q.put(broks_to_send)
                statsmgr.timer('queues.external.%s.to.put' % module.get_name(), time.time() - _t00)
            except Exception as exp:  # pylint: disable=broad-except
                # first we must find the modules
                logger.warning("Module %s queue exception: %s, I'm tagging it to restart later",
                               module.get_name(), str(exp))
                logger.exception(exp)
                self.modules_manager.set_to_restart(module)

        # No more need to send them
        for brok in broks_to_send:
            brok.to_be_sent = False
        logger.debug("Time to send %s broks (%d secs)", len(broks_to_send), time.time() - _t0)

        # Make the internal modules manage the broks
        start = time.time()
        while self.external_broks:
            now = time.time()
            # Do not 'manage' more than 0.8s, we must get new broks almost every second
            if now - start > 0.8:
                logger.info("I did not managed all my broks, remaining %d broks...",
                            len(self.external_broks))
                break

            # Get the first brok in the list
            brok = self.external_broks.pop(0)
            if self.modules_manager.get_internal_instances():
                self.manage_brok(brok)
                # Make a very short pause to avoid overloading
                self.make_a_pause(0.01, check_time_change=False)
            else:
                if getattr(brok, 'to_be_sent', False):
                    self.external_broks.append(brok)

        # Maybe our external modules raised 'objects', so get them
        if self.get_objects_from_from_queues():
            statsmgr.gauge('external-commands.got.count', len(self.external_commands))
            statsmgr.gauge('broks.got.count', len(self.external_broks))

    def get_daemon_stats(self, details=False):
        """Increase the stats provided by the Daemon base class

        :return: stats dictionary
        :rtype: dict
        """
        # Call the base Daemon one
        res = super(Broker, self).get_daemon_stats(details=details)

        res.update({'name': self.name, 'type': self.type})

        counters = res['counters']
        counters['broks-external'] = len(self.external_broks)
        counters['broks-internal'] = len(self.internal_broks)
        counters['broks-arbiter'] = len(self.arbiter_broks)
        counters['satellites.pollers'] = len(self.pollers)
        counters['satellites.reactionners'] = len(self.reactionners)
        counters['satellites.receivers'] = len(self.receivers)

        return res

    def main(self):
        """Main function, will loop forever

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

                # Restore retention data
                self.hook_point('load_retention')

                # Now the main loop
                self.do_main_loop()
                logger.info("Exited from the main loop.")

            self.request_stop()
        except Exception:  # pragma: no cover, this should never happen indeed ;)
            self.exit_on_exception(traceback.format_exc())
            raise
