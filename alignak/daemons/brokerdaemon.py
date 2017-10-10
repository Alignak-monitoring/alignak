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

import os
import sys
import time
import traceback
import threading
import logging

from multiprocessing import active_children

# pylint: disable=wildcard-import,unused-wildcard-import
# This import, despite not used, is necessary to include all Alignak objects modules
from alignak.objects import *
from alignak.misc.serialization import unserialize, AlignakClassLookupException
from alignak.satellite import BaseSatellite
from alignak.property import PathProp, IntegerProp, StringProp
from alignak.util import sort_by_ids
from alignak.stats import statsmgr
from alignak.http.client import HTTPClientException, HTTPClientConnectionException, \
    HTTPClientTimeoutException
from alignak.http.broker_interface import BrokerInterface

logger = logging.getLogger(__name__)  # pylint: disable=C0103


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
            IntegerProp(default=7772)
    })

    def __init__(self, **kwargs):
        """Broker daemon initialisation

        :param kwargs: command line arguments
        """
        super(Broker, self).__init__(kwargs.get('daemon_name', 'Default-broker'), **kwargs)

        # Our arbiters
        self.arbiters = {}

        # Our pollers, reactionners and receivers
        self.pollers = {}
        self.reactionners = {}
        self.receivers = {}

        # Modules are load one time
        self.have_modules = False

        # Can have a queue of external_commands given by modules
        # will be processed by arbiter
        self.external_commands = []

        # All broks to manage
        self.broks = []  # broks to manage
        # broks raised this turn and that needs to be put in self.broks
        self.broks_internal_raised = []
        # broks raised by the arbiters, we need a lock so the push can be in parallel
        # to our current activities and won't lock the arbiter
        self.arbiter_broks = []
        self.arbiter_broks_lock = threading.RLock()

        self.timeout = 1.0

        self.http_interface = BrokerInterface(self)

    def add(self, elt):  # pragma: no cover, seems not to be used
        """Add an element to the broker lists

        Original comment : Schedulers have some queues. We can simplify the call by adding
          elements into the proper queue just by looking at their type  Brok -> self.broks
          TODO: better tag ID?
          External commands -> self.external_commands

        TODO: is it useful?

        :param elt: object to add
        :type elt: object
        :return: None
        """
        cls_type = elt.__class__.my_type
        if cls_type == 'brok':
            # We tag the broks with our instance_id
            elt.instance_id = self.instance_id
            self.broks_internal_raised.append(elt)
            statsmgr.counter('broks.added', 1)
            return
        elif cls_type == 'externalcommand':
            self.external_commands.append(elt)
            statsmgr.counter('external-commands.added', 1)
        # Maybe we got a Message from the modules, it's way to ask something
        # like from now a full data from a scheduler for example.
        elif cls_type == 'message':
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
                logger.warning("The mod %s raise an exception: %s, "
                               "I'm tagging it to restart later", module.get_name(), str(exp))
                logger.exception(exp)
                self.modules_manager.set_to_restart(module)

    def get_internal_broks(self):
        """Get all broks from self.broks_internal_raised and append them to self.broks


        :return: None
        """
        statsmgr.gauge('get-new-broks-count.broker', len(self.broks_internal_raised))
        # Add the broks to our global list
        self.broks.extend(self.broks_internal_raised)
        self.broks_internal_raised = []

    def get_arbiter_broks(self):
        """We will get in the broks list the broks from the arbiters,
        but as the arbiter_broks list can be push by arbiter without Global lock,
        we must protect this with he list lock

        :return: None
        """
        with self.arbiter_broks_lock:
            statsmgr.gauge('get-new-broks-count.arbiter', len(self.arbiter_broks))
            # Add the broks to our global list
            self.broks.extend(self.arbiter_broks)
            self.arbiter_broks = []

    def get_new_broks(self, s_type='scheduler'):
        """Get new broks from daemon defined in type parameter

        :param s_type: type of object
        :type s_type: str
        :return: None
        """
        # Get the good links tab for looping..
        links = self.get_links_of_type(s_type)
        if links is None:
            logger.debug('Type unknown for connection! %s', s_type)
            return

        # We check for new check in each schedulers and put
        # the result in new_checks
        for s_id in links:
            logger.debug("Getting broks from %s", links[s_id]['name'])
            link = links[s_id]
            logger.debug("Link: %s", link)
            if not link['active']:
                logger.debug("The %s '%s' is not active, "
                             "do not get broks from its connection!", s_type, link['name'])
                continue

            if link['con'] is None:
                if not self.daemon_connection_init(s_id, s_type=s_type):
                    if link['connection_attempt'] <= link['max_failed_connections']:
                        logger.warning("The connection for the %s '%s' cannot be established, "
                                       "it is not possible to get broks from this daemon.",
                                       s_type, link['name'])
                    else:
                        logger.error("The connection for the %s '%s' cannot be established, "
                                     "it is not possible to get broks from this daemon.",
                                     s_type, link['name'])
                    continue

            try:
                _t0 = time.time()
                tmp_broks = link['con'].get('get_broks', {'bname': self.name}, wait='long')
                try:
                    tmp_broks = unserialize(tmp_broks, True)
                except AlignakClassLookupException as exp:  # pragma: no cover,
                    # simple protection
                    logger.error('Cannot un-serialize data received from "get_broks" call: %s',
                                 exp)
                    continue
                if tmp_broks:
                    logger.debug("Got %d Broks from %s in %s",
                                 len(tmp_broks), link['name'], time.time() - _t0)
                statsmgr.gauge('get-new-broks-count.%s' % (link['name']), len(tmp_broks.values()))
                statsmgr.timer('get-new-broks-time.%s' % (link['name']), time.time() - _t0)
                for brok in tmp_broks.values():
                    brok.instance_id = link['instance_id']

                # Add the broks to our global list
                self.broks.extend(tmp_broks.values())
            except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
                logger.warning("[%s] %s", link['name'], str(exp))
                link['con'] = None
                return
            except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
                logger.warning("Connection timeout with the %s '%s' when getting broks: %s",
                               s_type, link['name'], str(exp))
                link['con'] = None
                return
            except HTTPClientException as exp:  # pragma: no cover, simple protection
                logger.error("Error with the %s '%s' when getting broks: %s",
                             s_type, link['name'], str(exp))
                link['con'] = None
                return
            # scheduler must not have checks
            #  What the F**k? We do not know what happened,
            # so.. bye bye :)
            except Exception as exp:  # pylint: disable=broad-except
                logger.exception(exp)
                sys.exit(1)

    def get_retention_data(self):  # pragma: no cover, useful?
        """Get all broks

        TODO: using retention in the broker is dangerous and
        do not seem of any utility with Alignak

        :return: broks container
        :rtype: object
        """
        return self.broks

    def restore_retention_data(self, data):  # pragma: no cover, useful?
        """Add data to broks container

        TODO: using retention in the arbiter is dangerous and
        do not seem of any utility with Alignak

        :param data: broks to add
        :type data: list
        :return: None
        """
        self.broks.extend(data)

    def do_stop(self):
        """Stop all children of this process

        :return: None
        """
        act = active_children()
        for child in act:
            child.terminate()
            child.join(1)
        super(Broker, self).do_stop()

    def setup_new_conf(self):  # pylint: disable=R0915,R0912
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
            print("Broker - New configuration for: %s / %s" % (self.type, self.name))
            logger.info("[%s] Received a new configuration", self.name)

            # self_conf is our own configuration from the alignak environment
            self_conf = self.cur_conf['self_conf']

            # Get our satellites links
            for link_type in ['pollers', 'reactionners', 'receivers']:
                if link_type in self.cur_conf:
                    logger.error("[%s] Missing %s in the configuration!", self.name, link_type)
                    continue
                for sat_uuid in self.cur_conf['satellites'][link_type]:
                    my_satellites = getattr(self, link_type)
                    # Must look if we already had a configuration and save our broks
                    already_got = sat_uuid in my_satellites
                    if already_got:
                        broks = my_satellites[sat_uuid]['broks']
                        running_id = my_satellites[sat_uuid]['running_id']
                    else:
                        broks = {}
                        running_id = 0
                    new_link = self.cur_conf[link_type][sat_uuid]
                    my_satellites[sat_uuid] = new_link

                    # replacing sattelite address and port by those defined in satellitemap
                    if new_link['name'] in self_conf.get('satellitemap', {}):
                        new_link = dict(new_link)  # make a copy
                        new_link.update(self_conf.get('satellitemap', {})[new_link['name']])

                    # todo: why not using a SatteliteLink object?
                    proto = 'http'
                    if new_link['use_ssl']:
                        proto = 'https'
                    uri = '%s://%s:%s/' % (proto, new_link['address'], new_link['port'])
                    my_satellites[sat_uuid]['uri'] = uri

                    my_satellites[sat_uuid]['broks'] = broks
                    my_satellites[sat_uuid]['instance_id'] = 0
                    my_satellites[sat_uuid]['running_id'] = running_id
                    my_satellites[sat_uuid]['con'] = None
                    my_satellites[sat_uuid]['last_connection'] = 0
                    my_satellites[sat_uuid]['connection_attempt'] = 0
                    my_satellites[sat_uuid]['max_failed_connections'] = 3

                logger.debug("We have our %s: %s", link_type, my_satellites)
                logger.info("We have our %s:", link_type)
                for link in my_satellites.values():
                    logger.info(" - %s ", link['name'])

            if not self.have_modules:
                self.modules = self_conf['modules']
                self.have_modules = True

                # Ok now start, or restart them!
                # Set modules, init them and start external ones
                self.do_load_modules(self.modules)
                # and start external modules too
                self.modules_manager.start_external_instances()

            # Initialize connection with all our satellites
            for sat_link in self.get_all_links():
                print("Initialize connection with: %s" % sat_link)
                self.daemon_connection_init(sat_link.uuid, s_type=sat_link.type)

    def clean_previous_run(self):
        """Clean all (when we received new conf)

        :return: None
        """
        # Clean all satellites relations
        self.pollers.clear()
        self.reactionners.clear()
        self.receivers.clear()
        self.schedulers.clear()
        self.arbiters.clear()

        # Clean our internal objects
        self.broks = self.broks[:]
        self.broks_internal_raised = self.broks_internal_raised[:]
        with self.arbiter_broks_lock:
            self.arbiter_broks = self.arbiter_broks[:]
        self.external_commands = self.external_commands[:]

        # And now modules
        # self.have_modules = False
        # self.modules_manager.clear_instances()

    def get_stats_struct(self):
        """Get information of modules (internal and external) and add metrics of them

        :return: dictionary with state of all modules (internal and external)
        :rtype: dict
        :return: None
        """
        now = int(time.time())
        # call the daemon one
        res = super(Broker, self).get_stats_struct()
        res.update({'name': self.name, 'type': 'broker'})
        metrics = res['metrics']
        # metrics specific
        metrics.append('broker.%s.external-commands.queue %d %d' % (
            self.name, len(self.external_commands), now))
        metrics.append('broker.%s.broks.queue %d %d' % (self.name, len(self.broks), now))
        return res

    def do_loop_turn(self):
        """Loop use to:
         * check if modules are alive, if not restart them
         * add broks to queue of each modules

         :return: None
        """
        logger.debug("Begin Loop: still some old unmanaged broks (%d)", len(self.broks))
        if self.broks:
            statsmgr.gauge('unmanaged.broks', len(self.broks))

        # Begin to clean modules
        self.check_and_del_zombie_modules()

        # Now we check if we received a new configuration - no sleep time, we will sleep later...
        self.watch_for_new_conf()
        if self.new_conf:
            self.setup_new_conf()

        # Maybe the last loop we did raised some broks internally
        self.get_internal_broks()

        # Also reap broks sent from the arbiters
        self.get_arbiter_broks()

        # Now get broks from our distant daemons
        for _type in ['scheduler', 'poller', 'reactionner', 'receiver']:
            self.get_new_broks(s_type=_type)

        # Sort the brok list by id
        self.broks.sort(sort_by_ids)

        # Get the list of broks not yet sent to our external modules
        _t0 = time.time()
        broks_to_send = [brok for brok in self.broks if getattr(brok, 'to_be_sent', True)]
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

        # We must add new broks at the end of the list, so we reverse the list
        self.broks.reverse()

        # Make the internal modules manage the broks
        start = time.time()
        while self.broks:
            now = time.time()
            # Do not 'manage' more than 1s, we must get new broks
            # every 1s
            if now - start > 1:
                logger.warning("Did not managed all my broks, remaining %d broks...",
                               len(self.broks))
                break

            brok = self.broks.pop()
            if self.modules_manager.get_internal_instances():
                self.manage_brok(brok)
                # Make a very short pause to avoid overloading
                self.make_a_pause(0.01, check_time_change=False)
            else:
                if getattr(brok, 'to_be_sent', False):
                    self.broks.append(brok)

        # Maybe our external modules raised 'objects', so get them
        if self.get_objects_from_from_queues():
            statsmgr.gauge('got.external-commands', len(self.external_commands))
            statsmgr.gauge('got.broks', len(self.broks))

        # Maybe we do not have something to do, so we wait a little
        # TODO: redone the diff management....
        if not self.broks:
            while self.timeout > 0:
                begin = time.time()
                self.watch_for_new_conf(1.0)
                end = time.time()
                self.timeout = self.timeout - (end - begin)
            self.timeout = 1.0

        # Say to modules it's a new tick :)
        self.hook_point('tick')

    def main(self):
        """Main function, will loop forever

        :return: None
        """
        try:
            self.setup_alignak_logger()

            # Look if we are enabled or not. If ok, start the daemon mode
            self.look_for_early_exit()

            logger.info("[Broker] Using working directory: %s", os.path.abspath(self.workdir))

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

            # Restore retention data
            self.hook_point('load_retention')

            # Now the main loop
            self.do_mainloop()

        except Exception:
            self.print_unrecoverable(traceback.format_exc())
            raise
