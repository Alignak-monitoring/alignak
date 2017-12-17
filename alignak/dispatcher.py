# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2017: Alignak team, see AUTHORS.txt file for contributors
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
#     Guillaume Bour, guillaume@bour.cc
#     aviau, alexandre.viau@savoirfairelinux.com
#     Httqm, fournet.matthieu@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de

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
 This is the class of the dispatcher. Its role is to dispatch
 configurations to other elements like schedulers, reactionner,
 pollers, receivers and brokers. It is responsible for high availability part. If an
 element dies and the element type has a spare, it sends the config of the
 dead one to the spare
"""

import sys
import copy
import cPickle
import logging
import time
import random

from alignak.misc.serialization import serialize
from alignak.util import alive_then_spare_then_deads

logger = logging.getLogger(__name__)  # pylint: disable=C0103

# Always initialize random :)
random.seed()


class DispatcherError(Exception):
    """Exception raised for errors in the configuration dispatching.

    Attributes:
        msg  -- explanation of the error
    """

    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        """Exception to String"""
        return "Dispatcher error: %s" % (self.message)


class Dispatcher:
    """Dispatcher is in charge of sending configuration to other daemon.
    It has to handle spare, realms, poller tags etc.
    """

    def __init__(self, conf, arbiter_link):
        """Initialize the dispatcher

        Note that the arbiter param is an ArbiterLink, not an Arbiter daemon. Thus it is only
        an interface to the running Arbiter daemon...

        :param conf: the whole Alignak configuration as parsed by the Arbiter
        :type conf: Config
        :param arbiter_link: the link to the arbiter that parsed this configuration
        :type arbiter_link: ArbiterLink
        """
        if not arbiter_link or not hasattr(conf, 'parts'):
            raise DispatcherError("Dispatcher configuration problem: "
                                  "no valid arbiter link or configuration!")

        # Direct pointer to important elements for us
        self.arbiter_link = arbiter_link
        self.conf = conf
        logger.debug("Dispatcher configuration: %s / %s", self.arbiter_link, self.conf)

        logger.debug("Dispatcher realms configuration:")
        for realm in self.conf.realms:
            logger.debug("- %s", realm)
            for cfg_id in realm.parts:
                realm_config = realm.parts[cfg_id]
                print("Realm config: %s, flavor:%s, %s"
                      % (realm_config.uuid, getattr(realm_config, 'push_flavor', 'None'),
                         realm_config))

        logger.debug("Dispatcher satellites configuration:")
        for sat_type in ('arbiters', 'schedulers', 'reactionners',
                         'brokers', 'receivers', 'pollers'):
            setattr(self, sat_type, getattr(self.conf, sat_type))
            logger.debug("- %s", getattr(self, sat_type))
            for sat in getattr(self, sat_type):
                logger.debug("  . %s", sat)

            # for each satellite, we look if current arbiter have a specific
            # satellitemap value set for this satellite.
            # if so, we give this map to the satellite (used to build satellite URI later)
            if arbiter_link is None:
                continue

            for satellite in getattr(self, sat_type):
                satellite.set_arbiter_satellitemap(
                    arbiter_link.satellitemap.get(satellite.name, {}))

        self.dispatch_queue = {'schedulers': [], 'reactionners': [], 'brokers': [],
                               'pollers': [], 'receivers': []}

        # Add satellites in a list
        self.satellites = []
        self.satellites.extend(self.reactionners)
        self.satellites.extend(self.pollers)
        self.satellites.extend(self.brokers)
        self.satellites.extend(self.receivers)

        # all elements, including schedulers and satellites
        self.all_daemons_links = []
        self.all_daemons_links.extend(self.reactionners)
        self.all_daemons_links.extend(self.pollers)
        self.all_daemons_links.extend(self.brokers)
        self.all_daemons_links.extend(self.receivers)
        self.all_daemons_links.extend(self.schedulers)
        self.all_daemons_links.extend(self.arbiters)

        # Some flag about dispatch need or not
        self.dispatch_ok = False
        self.first_dispatch_done = False

        # Prepare the satellites confs
        for satellite in self.all_daemons_links:
            satellite.prepare_for_conf()

        # # Some properties must be given to satellites from global
        # # todo: This should not be necessary ! The pollers should have their own configuration!
        # # todo: indeed, this should be done for all the global alignak configuration parameters!!!
        # # configuration, like the max_plugins_output_length to pollers
        # parameters = {'max_plugins_output_length': self.conf.max_plugins_output_length}
        # for poller in self.pollers:
        #     poller.add_global_conf_parameters(parameters)
        #
        # # Reset need_conf for all schedulers.
        # for sched in self.schedulers:
        #     sched.need_conf = True
        # # Same for receivers
        # for rec in self.receivers:
        #     rec.need_conf = True

    def check_alive(self, test=False):
        """Check all daemons state (alive or not)
        and send them their configuration if necessary

        If test is True, do not really send

        :return: None
        """
        now = time.time()
        print("Dispatcher, check alive...")
        for daemon_link in self.all_daemons_links:
            # Not alive needs new need_conf
            # and spare too if they do not have already a conf
            if not daemon_link.update_infos(now, test=test):
                daemon_link.need_conf = True
            # print(" - %s manages: %s / %s"
            #       % (daemon_link.name, daemon_link.managed_confs,
            #          getattr(daemon_link, 'conf', None)))

        # Also check the spare arbiters
        for arbiter_link in self.arbiters:
            if arbiter_link != self.arbiter_link and arbiter_link.spare:
                if not arbiter_link.update_infos(now, test=test):
                    arbiter_link.need_conf = True

    def check_dispatch(self, test=False):
        """Check if all active items are still alive

        :return: None
        """
        if not self.arbiter_link:
            raise DispatcherError("Dispatcher configuration problem: no valid arbiter link!")

        # # Check if the other arbiters have a conf, but only if I am a master
        # for arbiter_link in self.arbiters:
        #     # If not me and I'm a master
        #     if arbiter_link != self.arbiter_link and not self.arbiter_link.spare:
        #         if not arbiter_link.have_conf(self.conf.magic_hash):
        #             if not hasattr(self.conf, 'spare_arbiter_conf'):
        #                 logger.critical('The arbiter tries to send a configuration but '
        #                              'it is not a MASTER one? Check your configuration!')
        #                 continue
        #             logger.info('Sending configuration to the arbiter: %s',
        # arbiter_link.get_name())
        #             arbiter_link.put_conf(self.conf.spare_arbiter_conf)
        #
        #         # Ok, it already has the conf. I remember that
        #         # it does not have to run, I'm still alive!
        #         arbiter_link.do_not_run()

        # We check for configuration parts to be dispatched on alive schedulers.
        # If not dispatched, we need a dispatch :) and if dispatched on a failed node,
        # remove the association, and need a new dispatch
        for realm in self.conf.realms:
            for cfg_id in realm.parts:
                conf_uuid = realm.parts[cfg_id].uuid
                push_flavor = realm.parts[cfg_id].push_flavor
                scheduler_link = realm.parts[cfg_id].assigned_to
                if scheduler_link is None:
                    if self.first_dispatch_done:
                        logger.info("Realm %s - Scheduler configuration %s is unmanaged!!",
                                    realm.name, conf_uuid)
                    self.dispatch_ok = False
                else:
                    logger.debug("Realm %s - Checking Scheduler %s configuration: %s",
                                 realm.name, scheduler_link.name, conf_uuid)
                    if not scheduler_link.alive:
                        self.dispatch_ok = False  # so we ask a new dispatching
                        logger.warning("Scheduler %s is expected to have the configuration "
                                       "'%s' but it is dead!", scheduler_link.name, conf_uuid)
                        if scheduler_link.conf:
                            scheduler_link.conf.assigned_to = None
                            scheduler_link.conf.is_assigned = False
                            scheduler_link.conf.push_flavor = 0
                        scheduler_link.push_flavor = 0
                        scheduler_link.conf = None

                    # Maybe the scheduler restarts, so it  is alive but without
                    # the conf we think it was managing so ask it what it is
                    # really managing, and if not, put the conf unassigned
                    if not scheduler_link.do_i_manage(conf_uuid, push_flavor):
                        self.dispatch_ok = False  # so we ask a new dispatching
                        logger.warning("Scheduler '%s' do not manage this configuration: %s, "
                                       "I am not happy.", scheduler_link.get_name(), conf_uuid)
                        if scheduler_link.conf:
                            scheduler_link.conf.assigned_to = None
                            scheduler_link.conf.is_assigned = False
                            scheduler_link.conf.push_flavor = 0
                        scheduler_link.push_flavor = 0
                        scheduler_link.need_conf = True
                        scheduler_link.conf = None

        self.check_dispatch_other_satellites()

    def check_dispatch_other_satellites(self):
        """
        Check the dispatch in other satellites: reactionner, poller, broker, receiver

        :return: None
        """
        some_satellites_are_missing = False
        # Maybe satellites are alive, but do not have a cfg yet.
        # I think so. It is not good. I ask a global redispatch for
        # the cfg_id I think is not correctly dispatched.
        for realm in self.conf.realms:
            for cfg_id in realm.parts:
                conf_uuid = realm.parts[cfg_id].uuid
                push_flavor = realm.parts[cfg_id].push_flavor
                try:
                    for sat_type in ('reactionner', 'poller', 'broker', 'receiver'):
                        # We must have the good number of satellite or we are not happy
                        # So we are sure to raise a dispatch every loop a satellite is missing
                        if (len(realm.to_satellites_managed_by[sat_type][conf_uuid]) <
                                realm.get_nb_of_must_have_satellites(sat_type)):
                            some_satellites_are_missing = True

                            # TODO: less violent! Must only resent to who need?
                            # must be caught by satellite who sees that
                            # it already has the conf and do nothing
                            self.dispatch_ok = False  # so we will redispatch all
                            realm.to_satellites_need_dispatch[sat_type][conf_uuid] = True
                            realm.to_satellites_managed_by[sat_type][conf_uuid] = []

                        for satellite in realm.to_satellites_managed_by[sat_type][conf_uuid]:
                            # Maybe the sat was marked as not alive, but still in
                            # to_satellites_managed_by. That means that a new dispatch
                            # is needed
                            # Or maybe it is alive but I thought that this satellite
                            # managed the conf and it doesn't.
                            # I ask a full redispatch of these cfg for both cases

                            if push_flavor == 0 and satellite.alive:
                                logger.warning('[%s] The %s %s manage a unmanaged configuration',
                                               realm.name, sat_type, satellite.name)
                                continue
                            if satellite.alive and (not satellite.reachable or
                                                    satellite.do_i_manage(conf_uuid, push_flavor)):
                                logger.warning('[%s] The %s %s is not reachable or it does '
                                               'not manage the correct configuration',
                                               realm.name, sat_type, satellite.name)
                                continue

                            logger.warning('[%s] The %s %s seems to be down, '
                                           'I must re-dispatch its role to someone else.',
                                           realm.name, sat_type, satellite.get_name())
                            self.dispatch_ok = False  # so we will redispatch all
                            realm.to_satellites_need_dispatch[sat_type][conf_uuid] = True
                            realm.to_satellites_managed_by[sat_type][conf_uuid] = []
                # At the first pass, there is no conf_id in to_satellites_managed_by
                except KeyError:
                    pass
        if some_satellites_are_missing:
            logger.warning("Some satellites are not available for the current configuration")

    def check_bad_dispatch(self, test=False):
        """Check if we have a bad dispatch
        For example : a spare started but the master was still alive
        We need ask the spare to wait a new conf

        :return: None
        """
        for daemon_link in self.satellites + list(self.schedulers):
            if hasattr(daemon_link, 'conf'):
                # If element has a conf, I do not care, it's a good dispatch
                # If dead: I do not ask it something, it won't respond..
                if daemon_link.conf is None and daemon_link.reachable:
                    if daemon_link.have_conf():
                        logger.warning("The element %s have a conf and should "
                                       "not have one! I ask it to idle now",
                                       daemon_link.get_name())
                        daemon_link.active = False
                        daemon_link.wait_new_conf()
                        # I do not care about order not send or not. If not,
                        # The next loop will resent it

        # I ask satellites which sched_id they manage. If I do not agree, I ask
        # them to remove it
        for satellite in self.satellites:
            sat_type = satellite.type
            if not satellite.reachable:
                continue
            cfg_ids = satellite.managed_confs  # what_i_managed()
            # I do not care about satellites that do nothing, they already
            # do what I want :)
            if not cfg_ids:
                continue
            id_to_delete = []
            for cfg_id in cfg_ids:
                # Ok, we search for realms that have the conf
                for realm in self.conf.realms:
                    if cfg_id in realm.parts:
                        conf_uuid = realm.parts[cfg_id].uuid
                        # Ok we've got the realm, we check its to_satellites_managed_by
                        # to see if reactionner is in. If not, we remove he sched_id for it
                        if satellite not in realm.to_satellites_managed_by[sat_type][conf_uuid]:
                            id_to_delete.append(cfg_id)
            # Maybe we removed all conf_id of this reactionner
            # We can put it idle, no active and wait_new_conf
            if len(id_to_delete) == len(cfg_ids):
                satellite.active = False
                logger.info("I ask %s to wait for a new conf", satellite.get_name())
                satellite.wait_new_conf()
            else:
                # It is not fully idle, just less cfg
                for r_id in id_to_delete:
                    logger.info("I ask %s to remove configuration %d",
                                satellite.get_name(), r_id)
                    satellite.remove_from_conf(id)

    def get_scheduler_ordered_list(self, realm):
        """Get sorted scheduler list for a specific realm

        List is ordered as: alive first, then spare (if any), then dead scheduler links

        :param realm: realm we want scheduler from
        :type realm: object
        :return: sorted scheduler list
        :rtype: list[alignak.objects.schedulerlink.SchedulerLink]
        """
        # get scheds, alive and no spare first
        scheduler_links = []
        for scheduler_link_uuid in realm.schedulers:
            # Update the scheduler instance id with the scheduler uuid
            # todo: what for???
            self.schedulers[scheduler_link_uuid].instance_id = scheduler_link_uuid
            scheduler_links.append(self.schedulers[scheduler_link_uuid])

        # Now we sort the schedulers so we take alive, then spare
        # then dead, but we do not care about them
        # todo: why do not care?
        scheduler_links.sort(alive_then_spare_then_deads)
        scheduler_links.reverse()  # pop is last, I need first
        return scheduler_links

    def prepare_dispatch(self, test=False):
        """
        Prepare dispatch, so prepare for each daemon (schedulers, brokers, receivers, reactionners,
        pollers)

        :return: None
        """
        if self.first_dispatch_done:
            logger.debug("Dispatching is already prepared...")
            return

    # Ok, we pass at least one time in dispatch, so now errors are True errors
        self.first_dispatch_done = True

        if self.dispatch_ok:
            logger.debug("Dispatching is already done...")
            return

        logger.debug("Preparing dispatch...")
        arbiters_cfg = {}
        for arbiter_link in self.arbiters:
            # If not me and I'm a master
            if arbiter_link != self.arbiter_link and not self.arbiter_link.spare:
                logger.debug("- arbiter to dispatch: %s", arbiter_link)
                arbiters_cfg[arbiter_link.uuid] = arbiter_link.give_satellite_cfg()
                logger.debug("  : %s", arbiters_cfg[arbiter_link.uuid])

        self.prepare_dispatch_schedulers(arbiters_cfg)

        for realm in self.conf.realms:
            logger.debug("A realm to dispatch: %s" % realm)
            for cfg in realm.parts.values():
                logger.debug("- cfg: %s", cfg)
                for sat_type in ('reactionner', 'poller', 'broker', 'receiver'):
                    self.prepare_dispatch_other_satellites(sat_type, realm, cfg, arbiters_cfg)

    def prepare_dispatch_schedulers(self, arbiters_cfg):
        """
        Prepare dispatch for schedulers

        :return: None
        """
        for realm in self.conf.realms:
            logger.info('[%s] Prepare schedulers dispatching', realm.name)
            # conf_to_dispatch is a list of configuration parts built when
            # the configuration is splitted into parts for the schedulers
            parts_to_dispatch = [cfg for cfg in realm.parts.values() if not cfg.is_assigned]

            # Now we get in scheds all scheduler of this realm and upper so
            schedulers = self.get_scheduler_ordered_list(realm)

            if len(parts_to_dispatch):
                logger.info('[%s] Dispatching schedulers ordered as: %s',
                            realm.name, ','.join([s.get_name() for s in schedulers]))
            else:
                logger.error('[%s] No configuration to dispatch for this realm', realm.name)
                continue

            # Only prepare the configuration for alive schedulers
            schedulers = [s for s in schedulers if s.alive]
            # If there is no alive schedulers, not good...
            if not schedulers:
                logger.error('[%s] There are no alive schedulers in this realm!', realm.name)
                continue

            for part in parts_to_dispatch:
                logger.info('[%s] Dispatching configuration %s', realm.name, part.uuid)

                # we need to loop until the configuration part is assigned
                # or no more scheduler is available
                while True:
                    try:
                        scheduler_link = schedulers.pop()
                    except IndexError:  # No more schedulers.. not good, no loop
                        # The configuration part do not need to be dispatched anymore
                        # todo: should be managed inside the Realm class!
                        for sat_type in ('reactionner', 'poller', 'broker', 'receiver'):
                            realm.to_satellites[sat_type][part.uuid] = None
                            realm.to_satellites_need_dispatch[sat_type][part.uuid] = False
                            realm.to_satellites_managed_by[sat_type][part.uuid] = []
                        break

                    if not scheduler_link.need_conf:
                        logger.info('[%s] The scheduler %s do not need any configuration, sorry',
                                    realm.name, scheduler_link.get_name())
                        continue

                    logger.info("[%s] Preparing configuration part '%s' for the scheduler '%s'",
                                realm.name, part.name, scheduler_link.name)
                    logger.debug("- [%s] hosts/services: %s / %s"
                                 % (realm.name, part.hosts, part.services))

                    # We give this configuration part a new 'flavor'
                    # todo: why a random? Using a hash would be better...
                    part.push_flavor = random.randint(1, 1000000)

                    scheduler_link.managed_confs = {part.uuid: part.push_flavor}
                    # todo: why is this necessary? Tmp removed!
                    # scheduler_link.conf = part
                    scheduler_link.push_flavor = part.push_flavor
                    scheduler_link.need_conf = False
                    scheduler_link.is_sent = False

                    scheduler_link.cfg.update({
                        # Global instance configuration
                        'alignak_name': part.alignak_name,
                        'instance_name': scheduler_link.name,
                        # 'instance_id': scheduler_link.uuid,
                        'conf_uuid': part.uuid,
                        'push_flavor': part.push_flavor,

                        'schedulers': {},
                        'arbiters': arbiters_cfg if scheduler_link.manage_arbiters else {},
                        'satellites': realm.get_links_for_a_scheduler(self.pollers,
                                                                      self.reactionners,
                                                                      self.brokers),

                        'conf_part': serialize(realm.parts[part.uuid]),

                        # todo: confirm it is interesting?
                        'override_conf': scheduler_link.get_override_configuration(),
                        # 'modules': scheduler_link.modules
                    })

                    # The configuration part is assigned to a scheduler
                    part.is_assigned = True
                    part.assigned_to = scheduler_link

                    # Dump the configuration part size
                    pickled_conf = cPickle.dumps(scheduler_link.cfg)
                    logger.info('[%s] scheduler configuration %s size: %d bytes',
                                realm.name, scheduler_link.name, sys.getsizeof(pickled_conf))

                    logger.info('[%s] configuration %s (%s) assigned to %s',
                                realm.name, part.uuid, part.push_flavor, scheduler_link.name)

                    # Now we generate the conf for satellites:
                    sat_cfg = scheduler_link.give_satellite_cfg()
                    for sat_type in ('reactionner', 'poller', 'broker', 'receiver'):
                        realm.to_satellites[sat_type][part.uuid] = sat_cfg
                        realm.to_satellites_need_dispatch[sat_type][part.uuid] = True
                        realm.to_satellites_managed_by[sat_type][part.uuid] = []

                    # Special case for the receiver because we need to send it the hosts list
                    hnames = [h.get_name() for h in part.hosts]
                    sat_cfg['hosts_names'] = hnames
                    realm.to_satellites['receiver'][part.uuid] = sat_cfg

                    # The configuration part is assigned to a scheduler, no need to go further ;)
                    break

        nb_missed = len([cfg for cfg in self.conf.parts.values() if not cfg.is_assigned])
        if nb_missed > 0:
            logger.warning("All configuration parts are not dispatched, %d are missing", nb_missed)
        else:
            logger.info("All configuration parts are assigned to schedulers :)")

        # Sched without conf in a dispatch ok are set to no need_conf
        # so they do not raise dispatch where no use
        for scheduler_link in self.schedulers.items.values():
            if scheduler_link.conf is None:
                # "so it do not ask anymore for conf"
                scheduler_link.need_conf = False

    def prepare_dispatch_other_satellites(self, sat_type, realm, part, arbiters_cfg):
        """
        Prepare dispatch of other satellites: reactionner, poller, broker and receiver

        :return:
        """

        if part.uuid not in realm.to_satellites_need_dispatch[sat_type]:
            return

        if not realm.to_satellites_need_dispatch[sat_type][part.uuid]:
            return

        # Get the list of the concerned satellites uuid (if alive and reachable)
        satellites = realm.get_potential_satellites_by_type(self.satellites, sat_type)
        if satellites:
            logger.info("[%s] Dispatching %s satellites ordered as: %s",
                        realm.name, sat_type, [s.name for s in satellites])
        else:
            logger.info("[%s] No %s satellites", realm.name, sat_type)

        # Now we dispatch cfg to every one ask for it
        nb_cfg_prepared = 0
        for sat_link in satellites:
            if nb_cfg_prepared >= realm.get_nb_of_must_have_satellites(sat_type):
                raise DispatcherError("Too much configuration parts prepared for the expected "
                                      "satellites count. This should never happen!")

            logger.info("[%s] Preparing configuration part '%s' for the %s: %s",
                        realm.name, part.name, sat_type, sat_link.name)
            sat_link.cfg.update({
                # Global instance configuration
                'alignak_name': part.alignak_name,
                'conf_uuid': part.uuid,
                'push_flavor': part.push_flavor,

                'schedulers': {part.uuid: realm.to_satellites[sat_type][part.uuid]},
                'arbiters': arbiters_cfg if sat_link.manage_arbiters else {}
            })

            # Brokers should have poller/reactionners links too
            if sat_type == "broker":
                sat_link.cfg.update({'satellites': realm.get_links_for_a_broker(
                    self.pollers, self.reactionners, self.receivers, self.conf.realms,
                    sat_link.manage_sub_realms)})

            # Dump the configuration part size
            pickled_conf = cPickle.dumps(sat_link.cfg)
            logger.info('[%s] %s %s configuration size: %d bytes',
                        realm.name, sat_type, sat_link.name, sys.getsizeof(pickled_conf))

            sat_link.managed_confs = {part.uuid: part.push_flavor}
            sat_link.conf = part
            sat_link.push_flavor = part.push_flavor
            sat_link.need_conf = False
            sat_link.is_sent = False

            nb_cfg_prepared += 1
            realm.to_satellites_managed_by[sat_type][part.uuid].append(sat_link)

            # I've got enough satellite, the next ones are considered unuseful!
            if nb_cfg_prepared == realm.get_nb_of_must_have_satellites(sat_type):
                logger.info("[%s] Ok, no more %s needed", realm.name, sat_type)
                realm.to_satellites_need_dispatch[sat_type][part.uuid] = False

    def dispatch(self, test=False):
        """
        Send configuration to satellites

        :return: None
        """
        if self.dispatch_ok:
            logger.debug("Dispatching is already done and ok...")
            return

        logger.info("Trying to send configuration to the satellites...")

        self.dispatch_ok = True

        for link in self.arbiters:
            # If not me and I'm a master
            if link != self.arbiter_link and not self.arbiter_link.spare:
                if link.need_conf:
                    raise DispatcherError("The arbiter link '%s' did not "
                                          "received a configuration!" % link.name)

                if link.is_sent:
                    logger.debug("Arbiter %s already sent!", link.name)
                    continue

                if not link.reachable:
                    logger.debug("Arbiter %s is not alive!", link.name)
                    continue

                logger.debug("Sending configuration to the arbiter %s", link.name)

                # ----------
                # Unit tests
                if test:
                    have_conf = False
                    if getattr(link, 'unit_test_pushed_configuration', None) is not None:
                        conf = link['unit_test_pushed_configuration']
                        have_conf = (conf['magic_hash'] == self.conf.magic_hash)
                    if not have_conf:
                        print('Sending configuration to the arbiter: %s: %s' % (link.name, link))
                        print('Dict: %s' % (link.__dict__))
                        setattr(link, 'unit_test_pushed_configuration', link.spare_arbiter_conf)

                    link.last_master_speak = time.time()
                    link.must_run = False
                    continue
                # ----------

                if not link.have_conf(self.conf.magic_hash):
                    if not hasattr(self.conf, 'spare_arbiter_conf'):
                        logger.critical("The arbiter tries to send a configuration but it "
                                        "is not a MASTER one? Check your configuration!")
                        continue
                    logger.debug('Sending configuration to the arbiter: %s', link.name)
                    link.is_sent = link.put_conf(link.spare_arbiter_conf)
                    if not link.is_sent:
                        # logger.warning("Configuration sending error for arbiter %s", link.name)
                        self.dispatch_ok = False
                    else:
                        logger.info("Configuration sent to the arbiter %s", link.name)

                # Ok, it already has the conf. I remember that
                # it does not have to run, I'm still alive!
                link.do_not_run()

        for link in self.schedulers:
            if link.is_sent:
                logger.debug("Scheduler %s already sent!", link.name)
                continue

            if not link.reachable:
                logger.debug("Scheduler %s is not alive!", link.name)
                continue

            logger.debug("Sending configuration to the scheduler %s", link.name)

            # ----------
            # Unit tests
            if test:
                setattr(link, 'unit_test_pushed_configuration', link.cfg)
                print("- sent: %s" % (link.cfg))
                link.is_sent = True
                continue
            # ----------

            link.is_sent = link.put_conf(link.cfg)
            if not link.is_sent:
                # logger.warning("Configuration sending error for scheduler %s", link.name)
                self.dispatch_ok = False
            else:
                logger.info("Configuration sent to the scheduler %s", link.name)

        for sat_type in ('reactionner', 'poller', 'broker', 'receiver'):
            for link in self.satellites:
                if link.is_sent:
                    logger.debug("%s %s already sent!", link.type, link.name)
                    continue

                if not link.reachable:
                    logger.debug("%s %s is not alive!", link.type, link.name)
                    continue

                logger.info("Sending configuration to %s '%s''", link.type, link.name)

                # ----------
                # Unit tests
                if test:
                    setattr(link, 'unit_test_pushed_configuration', link.cfg)
                    print("- sent: %s" % (link.cfg))
                    link.is_sent = True
                    continue
                # ----------

                link.is_sent = link.put_conf(link.cfg)
                if not link.is_sent:
                    # logger.warning("Configuration sending error for %s '%s'", sat_type, link.name)
                    self.dispatch_ok = False
                    continue
                # satellite_link.active = True

                logger.info('Configuration sent to %s %s', sat_type, link.get_name())
