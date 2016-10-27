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
from alignak.property import PathProp, IntegerProp
from alignak.util import sort_by_ids
from alignak.stats import statsmgr
from alignak.http.client import HTTPClient, HTTPEXCEPTIONS
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
        'pidfile':   PathProp(default='brokerd.pid'),
        'port':      IntegerProp(default=7772),
        'local_log': PathProp(default='brokerd.log'),
    })

    def __init__(self, config_file, is_daemon, do_replace, debug, debug_file):

        super(Broker, self).__init__('broker', config_file, is_daemon, do_replace, debug,
                                     debug_file)

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

    def add(self, elt):
        """Add elt to this broker

        Original comment : Schedulers have some queues. We can simplify the call by adding
          elements into the proper queue just by looking at their type  Brok -> self.broks
          TODO: better tag ID?
          External commands -> self.external_commands

        :param elt: object to add
        :type elt: object
        :return: None
        """
        cls_type = elt.__class__.my_type
        if cls_type == 'brok':
            # For brok, we TAG brok with our instance_id
            elt.instance_id = 0
            self.broks_internal_raised.append(elt)
            return
        elif cls_type == 'externalcommand':
            self.external_commands.append(elt)
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
            # Maybe a module tells me that it's dead, I must log it's last words...
            if elt.get_type() == 'ICrash':
                data = elt.get_data()
                logger.error('the module %s just crash! Please look at the traceback:',
                             data['name'])
                logger.error(data['trace'])

                # The module death will be looked for elsewhere and restarted.

    def get_links_from_type(self, d_type):
        """If d_type parameter is in list, return this object linked, else None

        :param d_type: name of object
        :type d_type: str
        :return: return the object linked
        :rtype: alignak.objects.satellitelink.SatelliteLinks
        """
        s_type = {'scheduler': self.schedulers,
                  'arbiter': self.arbiters,
                  'poller': self.pollers,
                  'reactionner': self.reactionners,
                  'receiver': self.receivers
                  }
        if d_type in s_type:
            return s_type[d_type]
        return None

    @staticmethod
    def is_connection_try_too_close(elt):
        """Check if last_connection has been made very recently

        :param elt: list with last_connection property
        :type elt: list
        :return: True if last connection has been made less than 5 seconds
        :rtype: bool
        """
        now = time.time()
        last_connection = elt['last_connection']
        if now - last_connection < 5:
            return True
        return False

    def pynag_con_init(self, _id, i_type='scheduler'):
        """Wrapper function for the real function do_
        just for timing the connection

        :param _id: id
        :type _id: int
        :param i_type: type of item
        :type i_type: str
        :return: do_pynag_con_init return always True, so we return always True
        :rtype: bool
        """
        _t0 = time.time()
        res = self.do_pynag_con_init(_id, i_type)
        statsmgr.incr('con-init.%s' % i_type, time.time() - _t0)
        return res

    def do_pynag_con_init(self, s_id, i_type='scheduler'):
        """Initialize or re-initialize connection with scheduler or arbiter if type == arbiter

        :param s_id: s_id
        :type s_id: int
        :param i_type: type of item
        :type i_type: str
        :return: None
        """
        # Get the good links tab for looping..
        links = self.get_links_from_type(i_type)
        if links is None:
            logger.debug('Type unknown for connection! %s', i_type)
            return

        # default timeout for daemons like pollers/reactionners/...
        timeout = 3
        data_timeout = 120

        if i_type == 'scheduler':
            # If sched is not active, I do not try to init
            # it is just useless
            is_active = links[s_id]['active']
            if not is_active:
                return
            # schedulers also got real timeout to respect
            timeout = links[s_id]['timeout']
            data_timeout = links[s_id]['data_timeout']

        # If we try to connect too much, we slow down our tests
        if self.is_connection_try_too_close(links[s_id]):
            return

        # Ok, we can now update it
        links[s_id]['last_connection'] = time.time()

        # DBG: print "Init connection with", links[s_id]['uri']
        running_id = links[s_id]['running_id']
        # DBG: print "Running id before connection", running_id
        uri = links[s_id]['uri']
        try:
            con = links[s_id]['con'] = HTTPClient(uri=uri,
                                                  strong_ssl=links[s_id]['hard_ssl_name_check'],
                                                  timeout=timeout, data_timeout=data_timeout)
        except HTTPEXCEPTIONS, exp:
            # But the multiprocessing module is not compatible with it!
            # so we must disable it immediately after
            logger.info("Connection problem to the %s %s: %s",
                        i_type, links[s_id]['name'], str(exp))
            links[s_id]['con'] = None
            return

        try:
            new_run_id = con.get('get_running_id')
            new_run_id = float(new_run_id)
            # data transfer can be longer

            # The schedulers have been restarted: it has a new run_id.
            # So we clear all verifs, they are obsolete now.
            if new_run_id != running_id:
                logger.debug("[%s] New running s_id for the %s %s: %s (was %s)",
                             self.name, i_type, links[s_id]['name'], new_run_id, running_id)
                links[s_id]['broks'].clear()
                # we must ask for a new full broks if
                # it's a scheduler
                if i_type == 'scheduler':
                    logger.debug("[%s] I ask for a broks generation to the scheduler %s",
                                 self.name, links[s_id]['name'])
                    con.get('fill_initial_broks', {'bname': self.name}, wait='long')
            # Ok all is done, we can save this new running s_id
            links[s_id]['running_id'] = new_run_id
        except HTTPEXCEPTIONS, exp:
            logger.info("Connection problem to the %s %s: %s",
                        i_type, links[s_id]['name'], str(exp))
            links[s_id]['con'] = None
            return
        except KeyError, exp:
            logger.info("the %s '%s' is not initialized: %s", i_type, links[s_id]['name'], str(exp))
            links[s_id]['con'] = None
            traceback.print_stack()
            return

        logger.info("Connection OK to the %s %s", i_type, links[s_id]['name'])

    def manage_brok(self, brok):
        """Get a brok.
        We put brok data to the modules

        :param brok: object with data
        :type brok: object
        :return: None
        """
        # Call all modules if they catch the call
        for mod in self.modules_manager.get_internal_instances():
            try:
                mod.manage_brok(brok)
            except Exception, exp:  # pylint: disable=W0703
                logger.debug(str(exp.__dict__))
                logger.warning("The mod %s raise an exception: %s, I'm tagging it to restart later",
                               mod.get_name(), str(exp))
                logger.warning("Exception type: %s", type(exp))
                logger.warning("Back trace of this kill: %s", traceback.format_exc())
                self.modules_manager.set_to_restart(mod)

    def add_broks_to_queue(self, broks):
        """ Add broks to global queue

        :param broks: some items
        :type broks: object
        :return: None
        """
        # Ok now put in queue broks to be managed by
        # internal modules
        self.broks.extend(broks)

    def interger_internal_broks(self):
        """Get all broks from self.broks_internal_raised and we put them in self.broks

        :return: None
        """
        self.add_broks_to_queue(self.broks_internal_raised)
        self.broks_internal_raised = []

    def interger_arbiter_broks(self):
        """We will get in the broks list the broks from the arbiters,
        but as the arbiter_broks list can be push by arbiter without Global lock,
        we must protect this with he list lock

        :return: None
        """
        with self.arbiter_broks_lock:
            self.add_broks_to_queue(self.arbiter_broks)
            self.arbiter_broks = []

    def get_new_broks(self, i_type='scheduler'):
        """Get new broks from daemon defined in type parameter

        :param i_type: type of object
        :type i_type: str
        :return: None
        """
        # Get the good links tab for looping..
        links = self.get_links_from_type(i_type)
        if links is None:
            logger.debug('Type unknown for connection! %s', i_type)
            return

        # We check for new check in each schedulers and put
        # the result in new_checks
        for sched_id in links:
            try:
                con = links[sched_id]['con']
                if con is not None:  # None = not initialized
                    t00 = time.time()
                    tmp_broks = con.get('get_broks', {'bname': self.name}, wait='long')
                    try:
                        tmp_broks = unserialize(tmp_broks, True)
                    except AlignakClassLookupException as exp:
                        logger.error('Cannot un-serialize data received from "get_broks" call: %s',
                                     exp)
                        continue
                    logger.debug("%s Broks get in %s", len(tmp_broks), time.time() - t00)
                    for brok in tmp_broks.values():
                        brok.instance_id = links[sched_id]['instance_id']
                    # Ok, we can add theses broks to our queues
                    self.add_broks_to_queue(tmp_broks.values())

                else:  # no con? make the connection
                    self.pynag_con_init(sched_id, i_type=i_type)
            # Ok, con is not known, so we create it
            except KeyError, exp:
                logger.debug("Key error for get_broks : %s", str(exp))
                self.pynag_con_init(sched_id, i_type=i_type)
            except HTTPEXCEPTIONS, exp:
                logger.warning("Connection problem to the %s %s: %s",
                               i_type, links[sched_id]['name'], str(exp))
                links[sched_id]['con'] = None
            # scheduler must not #be initialized
            except AttributeError, exp:
                logger.warning("The %s %s should not be initialized: %s",
                               i_type, links[sched_id]['name'], str(exp))
            # scheduler must not have checks
            #  What the F**k? We do not know what happened,
            # so.. bye bye :)
            except Exception, err:  # pylint: disable=W0703
                logger.error(str(err))
                logger.error(traceback.format_exc())
                sys.exit(1)

    def get_retention_data(self):
        """Get all broks

        :return: broks container
        :rtype: object
        """
        return self.broks

    def restore_retention_data(self, data):
        """Add data to broks container

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
        """Parse new configuration and initialize all required

        :return: None
        """
        with self.conf_lock:
            conf = unserialize(self.new_conf, True)
            self.new_conf = None
            self.cur_conf = conf
            # Got our name from the globals
            g_conf = conf['global']
            if 'broker_name' in g_conf:
                name = g_conf['broker_name']
            else:
                name = 'Unnamed broker'
            self.name = name
            # local statsd
            self.statsd_host = g_conf['statsd_host']
            self.statsd_port = g_conf['statsd_port']
            self.statsd_prefix = g_conf['statsd_prefix']
            self.statsd_enabled = g_conf['statsd_enabled']

            # We got a name so we can update the logger and the stats global objects
            statsmgr.register(name, 'broker',
                              statsd_host=self.statsd_host, statsd_port=self.statsd_port,
                              statsd_prefix=self.statsd_prefix, statsd_enabled=self.statsd_enabled)

            logger.debug("[%s] Sending us configuration %s", self.name, conf)

            # If we've got something in the schedulers, we do not
            # want it anymore
            # self.schedulers.clear()
            for sched_id in conf['schedulers']:
                # Must look if we already have it to do not overdie our broks

                old_sched_id = self.get_previous_sched_id(conf['schedulers'][sched_id], sched_id)

                if old_sched_id:
                    logger.info("[%s] We already got the conf %s (%s)",
                                self.name, old_sched_id, name)
                    broks = self.schedulers[old_sched_id]['broks']
                    running_id = self.schedulers[old_sched_id]['running_id']
                    del self.schedulers[old_sched_id]
                else:
                    broks = {}
                    running_id = 0
                sched = conf['schedulers'][sched_id]
                self.schedulers[sched_id] = sched

                # replacing scheduler address and port by those defined in satellitemap
                if sched['name'] in g_conf['satellitemap']:
                    sched = dict(sched)  # make a copy
                    sched.update(g_conf['satellitemap'][sched['name']])
                proto = 'http'
                if sched['use_ssl']:
                    proto = 'https'
                uri = '%s://%s:%s/' % (proto, sched['address'], sched['port'])
                self.schedulers[sched_id]['uri'] = uri

                self.schedulers[sched_id]['broks'] = broks
                self.schedulers[sched_id]['instance_id'] = sched['instance_id']
                self.schedulers[sched_id]['running_id'] = running_id
                self.schedulers[sched_id]['active'] = sched['active']
                self.schedulers[sched_id]['last_connection'] = 0
                self.schedulers[sched_id]['timeout'] = sched['timeout']
                self.schedulers[sched_id]['data_timeout'] = sched['data_timeout']

            logger.debug("We have our schedulers: %s", self.schedulers)
            logger.info("We have our schedulers:")
            for daemon in self.schedulers.values():
                logger.info(" - %s ", daemon['name'])

            # Now get arbiter
            for arb_id in conf['arbiters']:
                # Must look if we already have it
                already_got = arb_id in self.arbiters
                if already_got:
                    broks = self.arbiters[arb_id]['broks']
                else:
                    broks = {}
                arb = conf['arbiters'][arb_id]
                self.arbiters[arb_id] = arb

                # replacing arbiter address and port by those defined in satellitemap
                if arb['name'] in g_conf['satellitemap']:
                    arb = dict(arb)  # make a copy
                    arb.update(g_conf['satellitemap'][arb['name']])

                proto = 'http'
                if arb['use_ssl']:
                    proto = 'https'
                uri = '%s://%s:%s/' % (proto, arb['address'], arb['port'])
                self.arbiters[arb_id]['uri'] = uri

                self.arbiters[arb_id]['broks'] = broks
                self.arbiters[arb_id]['instance_id'] = 0  # No use so all to 0
                self.arbiters[arb_id]['running_id'] = 0
                self.arbiters[arb_id]['last_connection'] = 0

                # We do not connect to the arbiter. Connection hangs

            logger.debug("We have our arbiters: %s ", self.arbiters)
            logger.info("We have our arbiters:")
            for daemon in self.arbiters.values():
                logger.info(" - %s ", daemon['name'])

            # Now for pollers
            for pol_id in conf['pollers']:
                # Must look if we already have it
                already_got = pol_id in self.pollers
                if already_got:
                    broks = self.pollers[pol_id]['broks']
                    running_id = self.pollers[pol_id]['running_id']
                else:
                    broks = {}
                    running_id = 0
                poll = conf['pollers'][pol_id]
                self.pollers[pol_id] = poll

                # replacing poller address and port by those defined in satellitemap
                if poll['name'] in g_conf['satellitemap']:
                    poll = dict(poll)  # make a copy
                    poll.update(g_conf['satellitemap'][poll['name']])

                proto = 'http'
                if poll['use_ssl']:
                    proto = 'https'

                uri = '%s://%s:%s/' % (proto, poll['address'], poll['port'])
                self.pollers[pol_id]['uri'] = uri

                self.pollers[pol_id]['broks'] = broks
                self.pollers[pol_id]['instance_id'] = 0  # No use so all to 0
                self.pollers[pol_id]['running_id'] = running_id
                self.pollers[pol_id]['last_connection'] = 0

            logger.debug("We have our pollers: %s", self.pollers)
            logger.info("We have our pollers:")
            for daemon in self.pollers.values():
                logger.info(" - %s ", daemon['name'])

            # Now reactionners
            for rea_id in conf['reactionners']:
                # Must look if we already have it
                already_got = rea_id in self.reactionners
                if already_got:
                    broks = self.reactionners[rea_id]['broks']
                    running_id = self.reactionners[rea_id]['running_id']
                else:
                    broks = {}
                    running_id = 0

                reac = conf['reactionners'][rea_id]
                self.reactionners[rea_id] = reac

                # replacing reactionner address and port by those defined in satellitemap
                if reac['name'] in g_conf['satellitemap']:
                    reac = dict(reac)  # make a copy
                    reac.update(g_conf['satellitemap'][reac['name']])

                proto = 'http'
                if reac['use_ssl']:
                    proto = 'https'
                uri = '%s://%s:%s/' % (proto, reac['address'], reac['port'])
                self.reactionners[rea_id]['uri'] = uri

                self.reactionners[rea_id]['broks'] = broks
                self.reactionners[rea_id]['instance_id'] = 0  # No use so all to 0
                self.reactionners[rea_id]['running_id'] = running_id
                self.reactionners[rea_id]['last_connection'] = 0

            logger.debug("We have our reactionners: %s", self.reactionners)
            logger.info("We have our reactionners:")
            for daemon in self.reactionners.values():
                logger.info(" - %s ", daemon['name'])

            # Now receivers
            for rec_id in conf['receivers']:
                # Must look if we already have it
                already_got = rec_id in self.receivers
                if already_got:
                    broks = self.receivers[rec_id]['broks']
                    running_id = self.receivers[rec_id]['running_id']
                else:
                    broks = {}
                    running_id = 0

                rec = conf['receivers'][rec_id]
                self.receivers[rec_id] = rec

                # replacing reactionner address and port by those defined in satellitemap
                if rec['name'] in g_conf['satellitemap']:
                    rec = dict(rec)  # make a copy
                    rec.update(g_conf['satellitemap'][rec['name']])

                proto = 'http'
                if rec['use_ssl']:
                    proto = 'https'
                uri = '%s://%s:%s/' % (proto, rec['address'], rec['port'])
                self.receivers[rec_id]['uri'] = uri

                self.receivers[rec_id]['broks'] = broks
                self.receivers[rec_id]['instance_id'] = 0  # No use so all to 0
                self.receivers[rec_id]['running_id'] = running_id
                self.receivers[rec_id]['last_connection'] = 0

            logger.debug("We have our receivers: %s", self.receivers)
            logger.info("We have our receivers:")
            for daemon in self.receivers.values():
                logger.info(" - %s ", daemon['name'])

            if not self.have_modules:
                self.modules = conf['global']['modules']
                self.have_modules = True

                # Ok now start, or restart them!
                # Set modules, init them and start external ones
                self.do_load_modules(self.modules)
                self.modules_manager.start_external_instances()

            # Set our giving timezone from arbiter
            use_timezone = conf['global']['use_timezone']
            if use_timezone != 'NOTSET':
                logger.info("Setting our timezone to %s", use_timezone)
                os.environ['TZ'] = use_timezone
                time.tzset()

            # Connection init with Schedulers
            for sched_id in self.schedulers:
                self.pynag_con_init(sched_id, i_type='scheduler')

            for pol_id in self.pollers:
                self.pynag_con_init(pol_id, i_type='poller')

            for rea_id in self.reactionners:
                self.pynag_con_init(rea_id, i_type='reactionner')

    def clean_previous_run(self):
        """Clean all (when we received new conf)

        :return: None
        """
        # Clean all lists
        self.schedulers.clear()
        self.pollers.clear()
        self.reactionners.clear()
        self.broks = self.broks[:]
        self.broks_internal_raised = self.broks_internal_raised[:]
        with self.arbiter_broks_lock:
            self.arbiter_broks = self.arbiter_broks[:]
        self.external_commands = self.external_commands[:]

        # And now modules
        self.have_modules = False
        self.modules_manager.clear_instances()

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
        logger.debug("Begin Loop: managing old broks (%d)", len(self.broks))

        # Dump modules Queues size
        insts = [inst for inst in self.modules_manager.instances if inst.is_external]
        for inst in insts:
            try:
                logger.debug("External Queue len (%s): %s", inst.get_name(), inst.to_q.qsize())
            except Exception, exp:  # pylint: disable=W0703
                logger.debug("External Queue len (%s): Exception! %s", inst.get_name(), exp)

        # Begin to clean modules
        self.check_and_del_zombie_modules()

        # Maybe the arbiter ask us to wait for a new conf
        # If true, we must restart all...
        if self.cur_conf is None:
            # Clean previous run from useless objects
            # and close modules
            self.clean_previous_run()

            self.wait_for_initial_conf()
            # we may have been interrupted or so; then
            # just return from this loop turn
            if not self.new_conf:
                return
            self.setup_new_conf()

        # Now we check if arbiter speak to us.
        # If so, we listen for it
        # When it pushes conf to us, we reinit connections
        self.watch_for_new_conf(0.0)
        if self.new_conf:
            self.setup_new_conf()

        # Maybe the last loop we raised some broks internally
        # we should integrate them in broks
        self.interger_internal_broks()
        # Also reap broks sent from the arbiters
        self.interger_arbiter_broks()

        # Main job, go get broks in our distant daemons
        types = ['scheduler', 'poller', 'reactionner', 'receiver']
        for _type in types:
            _t0 = time.time()
            # And from schedulers
            self.get_new_broks(i_type=_type)
            statsmgr.incr('get-new-broks.%s' % _type, time.time() - _t0)

        # Sort the brok list by id
        self.broks.sort(sort_by_ids)

        # and for external queues
        # REF: doc/broker-modules.png (3)
        # We put to external queues broks that was not already send
        t00 = time.time()
        # We are sending broks as a big list, more efficient than one by one
        ext_modules = self.modules_manager.get_external_instances()
        to_send = [brok for brok in self.broks if getattr(brok, 'need_send_to_ext', True)]

        # Send our pack to all external modules to_q queue so they can get the whole packet
        # beware, the sub-process/queue can be die/close, so we put to restart the whole module
        # instead of killing ourselves :)
        for mod in ext_modules:
            try:
                mod.to_q.put(to_send)
            except Exception, exp:  # pylint: disable=W0703
                # first we must find the modules
                logger.debug(str(exp.__dict__))
                logger.warning("The mod %s queue raise an exception: %s, "
                               "I'm tagging it to restart later",
                               mod.get_name(), str(exp))
                logger.warning("Exception type: %s", type(exp))
                logger.warning("Back trace of this kill: %s", traceback.format_exc())
                self.modules_manager.set_to_restart(mod)

        # No more need to send them
        for brok in to_send:
            brok.need_send_to_ext = False
        statsmgr.incr('core.put-to-external-queue', time.time() - t00)
        logger.debug("Time to send %s broks (%d secs)", len(to_send), time.time() - t00)

        # We must had new broks at the end of the list, so we reverse the list
        self.broks.reverse()

        start = time.time()
        while len(self.broks) != 0:
            now = time.time()
            # Do not 'manage' more than 1s, we must get new broks
            # every 1s
            if now - start > 1:
                break

            brok = self.broks.pop()
            # Ok, we can get the brok, and doing something with it
            # REF: doc/broker-modules.png (4-5)
            # We un serialize the brok before consume it
            brok.prepare()
            _t0 = time.time()
            self.manage_brok(brok)
            statsmgr.incr('core.manage-brok', time.time() - _t0)

            nb_broks = len(self.broks)

            # Ok we manage brok, but we still want to listen to arbiter
            self.watch_for_new_conf(0.0)

            # if we got new broks here from arbiter, we should break the loop
            # because such broks will not be managed by the
            # external modules before this loop (we pop them!)
            if len(self.broks) != nb_broks:
                break

        # Maybe external modules raised 'objects'
        # we should get them
        self.get_objects_from_from_queues()

        # Maybe we do not have something to do, so we wait a little
        # TODO: redone the diff management....
        if len(self.broks) == 0:
            while self.timeout > 0:
                begin = time.time()
                self.watch_for_new_conf(1.0)
                end = time.time()
                self.timeout = self.timeout - (end - begin)
            self.timeout = 1.0

            # print "get new broks watch new conf 1: end", len(self.broks)

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

            self.do_daemon_init_and_start()

            self.load_modules_manager()

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
