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

import logging
import time
import random

from alignak.util import alive_then_spare_then_deads

logger = logging.getLogger(__name__)  # pylint: disable=C0103

# Always initialize random :)
random.seed()


class Dispatcher:
    """Dispatcher is in charge of sending configuration to other daemon.
    It has to handle spare, realms, poller tags etc.
    """

    def __init__(self, conf, arbiter):
        """
        Load all elements, set them as not assigned
        and add them to elements, so loop will be easier :)

        :param conf: the monitoring configuration to get dispatched
        :type conf alignak.objects.Config
        :param arbiter: the arbiter that will dispatch the configuration
        :type arbiter: alignak.daemons.Arbiter
        """
        self.arbiter = arbiter

        # Pointer to the whole conf
        self.conf = conf
        logger.debug("Dispatcher __init__: %s / %s", self.arbiter, self.conf)

        self.realms = conf.realms

        # Direct pointer to important elements for us
        for sat_type in ('arbiters', 'schedulers', 'reactionners',
                         'brokers', 'receivers', 'pollers'):
            setattr(self, sat_type, getattr(self.conf, sat_type))

            # for each satellite, we look if current arbiter has a specific
            # satellitemap value set for this satellite.
            # if so, we give this map to the satellite (used to build satellite URI later)
            if arbiter is None:
                continue

            for satellite in getattr(self, sat_type):
                sat_name = satellite.get_name()
                satellite.set_arbiter_satellitemap(arbiter.satellitemap.get(sat_name, {}))

        self.dispatch_queue = {'schedulers': [], 'reactionners': [],
                               'brokers': [], 'pollers': [], 'receivers': []}
        self.elements = []  # all elements, sched and satellites
        self.satellites = []  # only satellites not schedulers

        # Initialize configuration parts
        for cfg in self.conf.parts.values():
            cfg.is_assigned = False
            cfg.assigned_to = None
            cfg.push_flavor = 0

        # Add satellites in the good lists
        self.elements.extend(self.schedulers)

        # Others are in 2 lists
        self.elements.extend(self.reactionners)
        self.satellites.extend(self.reactionners)
        self.elements.extend(self.pollers)
        self.satellites.extend(self.pollers)
        self.elements.extend(self.brokers)
        self.satellites.extend(self.brokers)
        self.elements.extend(self.receivers)
        self.satellites.extend(self.receivers)

        # Some flag about dispatch needed or not
        self.dispatch_ok = False
        self.first_dispatch_done = False

        # Prepare the satellites confs
        logger.info("Dispatcher satellites: %s" % self.satellites)
        for satellite in self.satellites:
            satellite.prepare_for_conf()

        # Some properties must be given to satellites from global
        # configuration, like the max_plugins_output_length to pollers
        parameters = {'max_plugins_output_length': self.conf.max_plugins_output_length}
        for poller in self.pollers:
            poller.add_global_conf_parameters(parameters)

        # Reset need_conf for all schedulers.
        for sched in self.schedulers:
            sched.need_conf = True
        # Same for receivers
        for rec in self.receivers:
            rec.need_conf = True

    def check_alive(self):
        """Check all daemons state (alive or not)
        and send conf if necessary

        :return: None
        """
        now = time.time()
        for elt in self.elements:
            elt.update_infos(now)

            # Not alive needs new need_conf
            # and spare too if they do not have already a conf
            # REF: doc/alignak-scheduler-lost.png (1)
            if not elt.alive or hasattr(elt, 'conf') and elt.conf is None:
                elt.need_conf = True

        for arb in self.arbiters:
            # If not me, but not the master too
            if arb != self.arbiter and arb.spare:
                arb.update_infos(now)

    def check_dispatch(self):
        """Check if all active items are still alive

        :return: None
        """
        # Check if the other arbiter has a conf, but only if I am a master
        for arb in self.arbiters:
            # If not me and I'm a master
            if self.arbiter and arb != self.arbiter and not self.arbiter.spare:
                if not arb.have_conf(self.conf.magic_hash):
                    logger.info('Sending configuration #%s to arbiter: %s',
                                self.conf.magic_hash, arb.get_name())
                    is_sent = arb.put_conf(self.conf.whole_conf_pack)
                    arb.is_sent = is_sent
                    if not is_sent:
                        logger.warning('Configuration sending error to arbiter: %s',
                                       arb.get_name())
                    else:
                        arb.active = True
                        # Remind it that WE are the master here!
                        arb.do_not_run()
                        logger.info('Configuration sent to arbiter: %s', arb.get_name())
                else:
                    # Ok, it already has the conf. I remember that
                    # it does not have to run, I'm still alive!
                    logger.debug("Do not send configuration")
                    arb.do_not_run()

        # We check for confs to be dispatched on alive schedulers. If not dispatched, need
        # dispatch :) and if dispatch on a failed node, remove the association, and need a new
        # dispatch
        for realm in self.realms:
            # Todo: Spare arbiter fails else...
            if not hasattr(realm, 'confs'):
                continue
            for cfg_id in realm.confs:
                conf_uuid = realm.confs[cfg_id].uuid
                push_flavor = realm.confs[cfg_id].push_flavor
                sched = realm.confs[cfg_id].assigned_to
                if sched is None:
                    if self.first_dispatch_done:
                        logger.info("Scheduler configuration %s is unmanaged!!", conf_uuid)
                    self.dispatch_ok = False
                else:
                    if not sched.alive:
                        self.dispatch_ok = False  # so we ask a new dispatching
                        logger.warning("Scheduler %s had the configuration %s but is dead, "
                                       "I am not happy.", sched.get_name(), conf_uuid)
                        sched.conf.assigned_to = None
                        sched.conf.is_assigned = False
                        sched.conf.push_flavor = 0
                        sched.push_flavor = 0
                        sched.conf = None
                    # Maybe the scheduler restarts, so is alive but without
                    # the conf we think it was managing so ask it what it is
                    # really managing, and if not, put the conf unassigned
                    if not sched.do_i_manage(conf_uuid, push_flavor):
                        self.dispatch_ok = False  # so we ask a new dispatching
                        logger.warning("Scheduler %s did not managed its configuration %s, "
                                       "I am not happy.", sched.get_name(), conf_uuid)
                        if sched.conf:
                            sched.conf.assigned_to = None
                            sched.conf.is_assigned = False
                            sched.conf.push_flavor = 0
                        sched.push_flavor = 0
                        sched.need_conf = True
                        sched.conf = None

        self.check_dispatch_other_satellites()

    def check_dispatch_other_satellites(self):
        """
        Check the dispatch in other satellites: reactionner, poller, broker, receiver

        :return: None
        """
        # Maybe satellites are alive, but do not have a cfg yet.
        # I think so. It is not good. I ask a global redispatch for
        # the cfg_id I think is not correctly dispatched.
        for realm in self.realms:
            # Todo: Spare arbiter fails else...
            if not hasattr(realm, 'confs'):
                continue
            for cfg_id in realm.confs:
                conf_uuid = realm.confs[cfg_id].uuid
                push_flavor = realm.confs[cfg_id].push_flavor
                try:
                    for sat_type in ('reactionner', 'poller', 'broker', 'receiver'):
                        # We must have the good number of satellite or we are not happy
                        # So we are sure to raise a dispatch every loop a satellite is missing
                        if (len(realm.to_satellites_managed_by[sat_type][conf_uuid]) <
                                realm.get_nb_of_must_have_satellites(sat_type)):
                            logger.warning("Missing satellite %s for configuration %s:",
                                           sat_type, conf_uuid)

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
                            # Or maybe it is alive but I thought that this reactionner
                            # managed the conf and it doesn't.
                            # I ask a full redispatch of these cfg for both cases

                            if push_flavor == 0 and satellite.alive:
                                logger.warning('[%s] The %s %s manage a unmanaged configuration',
                                               realm.get_name(), sat_type, satellite.get_name())
                                continue
                            if satellite.alive and (not satellite.reachable or
                                                    satellite.do_i_manage(conf_uuid, push_flavor)):
                                continue

                            logger.warning('[%s] The %s %s seems to be down, '
                                           'I must re-dispatch its role to someone else.',
                                           realm.get_name(), sat_type, satellite.get_name())
                            self.dispatch_ok = False  # so we will redispatch all
                            realm.to_satellites_need_dispatch[sat_type][conf_uuid] = True
                            realm.to_satellites_managed_by[sat_type][conf_uuid] = []
                # At the first pass, there is no conf_id in to_satellites_managed_by
                except KeyError:
                    pass

    def check_bad_dispatch(self):
        """Check if we have a bad dispatch
        For example : a spare started but the master was still alive
        We need ask the spare to wait a new conf

        :return: None
        """
        for elt in self.elements:
            if hasattr(elt, 'conf'):
                # If element has a conf, I do not care, it's a good dispatch
                # If dead: I do not ask it something, it won't respond..
                if elt.conf is None and elt.reachable:
                    if elt.have_conf():
                        logger.warning("The element %s have a conf and should "
                                       "not have one! I ask it to idle now",
                                       elt.get_name())
                        elt.active = False
                        elt.wait_new_conf()
                        # I do not care about order not send or not. If not,
                        # The next loop will resent it

        # I ask satellites which sched_id they manage. If I do not agree, I ask
        # them to remove it
        for satellite in self.satellites:
            sat_type = satellite.get_my_type()
            if not satellite.reachable:
                continue
            cfg_ids = satellite.managed_confs  # what_i_managed()
            # I do not care about satellites that do nothing, they already
            # do what I want :)
            if len(cfg_ids) == 0:
                continue
            id_to_delete = []
            for cfg_id in cfg_ids:
                # Ok, we search for realms that have the conf
                for realm in self.realms:
                    # Todo: Spare arbiter fails else...
                    if not hasattr(realm, 'confs'):
                        continue
                    if cfg_id in realm.confs:
                        conf_uuid = realm.confs[cfg_id].uuid
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

        :param realm: realm we want scheduler from
        :type realm: object
        :return: sorted scheduler list
        :rtype: list[alignak.objects.schedulerlink.SchedulerLink]
        """
        # get scheds, alive and no spare first
        scheds = []
        for sched_id in realm.schedulers:
            scheds.append(self.schedulers[sched_id])

        # now the spare scheds of higher realms
        # they are after the sched of realm, so
        # they will be used after the spare of
        # the realm
        for higher_r_id in realm.higher_realms:
            higher_r = self.realms[higher_r_id]
            for sched_id in higher_r.schedulers:
                sched = self.schedulers[sched_id]
                if sched.spare:
                    scheds.append(sched)

        # Now we sort the scheds so we take master, then spare
        # the dead, but we do not care about them
        scheds.sort(alive_then_spare_then_deads)
        scheds.reverse()  # pop is last, I need first

        return scheds

    def prepare_dispatch(self):
        """
        Prepare dispatch, so prepare for each daemon (schedulers, brokers, receivers, reactionners,
        pollers)

        :return: None
        """
        # Ok, we pass at least one time in dispatch, so now errors are True errors
        self.first_dispatch_done = True

        if self.dispatch_ok:
            return

        self.prepare_dispatch_schedulers()

        arbiters_cfg = {}
        for arb in self.arbiters:
            arbiters_cfg[arb.uuid] = arb.give_satellite_cfg()

        for realm in self.realms:
            # Todo: Spare arbiter fails else...
            if not hasattr(realm, 'confs'):
                continue

            for cfg in realm.confs.values():
                for sat_type in ('reactionner', 'poller', 'broker', 'receiver'):
                    self.prepare_dispatch_other_satellites(sat_type, realm, cfg, arbiters_cfg)

    def prepare_dispatch_schedulers(self):
        """
        Prepare dispatch for schedulers

        :return: None
        """
        nb_conf = 0

        for realm in self.realms:
            # Todo: Spare arbiter fails else...
            if not hasattr(realm, 'confs'):
                continue

            conf_to_dispatch = [cfg for cfg in realm.confs.values() if not cfg.is_assigned]

            # Now we get all schedulers of this realm and upper
            schedulers = self.get_scheduler_ordered_list(realm)

            # prepare configuration only for alive schedulers
            schedulers = [s for s in schedulers if s.alive]

            logger.info('[%s] Prepare scheduler dispatching %d/%d configurations',
                        realm.get_name(), len(conf_to_dispatch), len(schedulers))
            logger.info('[%s] Dispatching schedulers ordered as: %s',
                        realm.get_name(), ','.join([s.get_name() for s in schedulers]))

            nb_conf = len(conf_to_dispatch)
            if nb_conf <= 0:
                logger.warning("[%s] No available schedulers for dispatching the configuration :(",
                               realm.get_name())
                return

            for realm_conf in conf_to_dispatch:
                logger.info('[%s] Preparing configuration #%s (%s)',
                            realm.get_name(), realm_conf.magic_hash, realm_conf.uuid)

                # If there is no alive schedulers, not good...
                if len(schedulers) == 0:
                    logger.warning('[%s] There are no alive schedulers in this realm!',
                                   realm.get_name())
                    break

                # we need to loop until the conf is assigned
                # or when there are no more schedulers available
                while True:
                    try:
                        scheduler = schedulers.pop()
                    except IndexError:  # No more schedulers.. not good, no loop
                        # need_loop = False
                        # The conf does not need to be dispatched
                        cfg_id = realm_conf.uuid
                        for sat_type in ('reactionner', 'poller', 'broker', 'receiver'):
                            realm.to_satellites[sat_type][cfg_id] = None
                            realm.to_satellites_need_dispatch[sat_type][cfg_id] = False
                            realm.to_satellites_managed_by[sat_type][cfg_id] = []
                        break

                    logger.info('[%s] Preparing configuration for the scheduler %s (%s)',
                                realm.get_name(), scheduler.get_name(),
                                'spare' if scheduler.spare else 'master')
                    if not scheduler.need_conf:
                        logger.info('[%s] The scheduler %s do not need any configuration, sorry',
                                    realm.get_name(), scheduler.get_name())
                        continue

                    # We give this configuration a new 'flavor'
                    realm_conf.push_flavor = random.randint(1, 1000000)
                    satellites = realm.get_satellites_links_for_scheduler(self.pollers,
                                                                          self.reactionners,
                                                                          self.brokers)
                    conf_package = {
                        'conf': realm.serialized_confs[realm_conf.uuid],
                        'override_conf': scheduler.get_override_configuration(),
                        # Todo: should be serialized, no?
                        'modules': scheduler.modules,
                        'satellites': satellites,
                        'instance_name': scheduler.scheduler_name,
                        'push_flavor': realm_conf.push_flavor,
                        'skip_initial_broks': scheduler.skip_initial_broks,
                        'accept_passive_unknown_check_results':
                            scheduler.accept_passive_unknown_check_results,
                        # local statsd
                        # Todo: really necessary? To be confirmed ...
                        'statsd_host': self.conf.statsd_host,
                        'statsd_port': self.conf.statsd_port,
                        'statsd_prefix': self.conf.statsd_prefix,
                        'statsd_enabled': self.conf.statsd_enabled,
                    }

                    # We update all data for this scheduler
                    scheduler.managed_confs = {realm_conf.uuid: realm_conf.push_flavor}
                    scheduler.conf = realm_conf
                    scheduler.conf_package = conf_package
                    scheduler.push_flavor = realm_conf.push_flavor
                    scheduler.need_conf = False
                    scheduler.is_sent = False
                    realm_conf.is_assigned = True
                    realm_conf.assigned_to = scheduler
                    logger.debug('[%s] configuration for the scheduler %s: %s / %s',
                                 realm.get_name(), scheduler.get_name(),
                                 scheduler.conf.uuid, scheduler.conf.get_name())

                    # Now we generate the conf for satellites:
                    cfg_id = realm_conf.uuid
                    sat_cfg = scheduler.give_satellite_cfg()
                    for sat_type in ('reactionner', 'poller', 'broker', 'receiver'):
                        realm.to_satellites[sat_type][cfg_id] = sat_cfg
                        realm.to_satellites_need_dispatch[sat_type][cfg_id] = True
                        realm.to_satellites_managed_by[sat_type][cfg_id] = []

                    # Special case for receiver because we need to send it the hosts list
                    hnames = [h.get_name() for h in realm_conf.hosts]
                    sat_cfg['hosts'] = hnames
                    realm.to_satellites['receiver'][cfg_id] = sat_cfg

                    # The config is prepared for a scheduler, no need to check another scheduler
                    break

        nb_missed = len([cfg for cfg in self.conf.parts.values() if not cfg.is_assigned])
        if nb_missed > 0:
            logger.warning("All schedulers configurations (%d) are not dispatched, %d are missing",
                           nb_conf, nb_missed)
        else:
            logger.info("All schedulers configurations (%d) are dispatched :)", nb_conf)

        # Scheduler without configuration in a dispatch are set to no need_conf
        # so they do not raise dispatch where no use
        for scheduler in self.schedulers.items.values():
            if scheduler.conf is None:
                # "so it do not ask anymore for conf"
                scheduler.need_conf = False

    def prepare_dispatch_other_satellites(self, sat_type, realm, cfg, arbiters_cfg):
        """
        Prepare dispatch of other satellites: reactionner, poller, broker and receiver

        :return:
        """

        if not realm.to_satellites_need_dispatch[sat_type][cfg.uuid]:
            logger.info("[%s] No satellites dispatch needed for this realm", realm.get_name())
            return

        # make copies of potential satellites list for sort
        satellites = []
        for sat_id in realm.get_potential_satellites_by_type(sat_type):
            sat = getattr(self, "%ss" % sat_type)[sat_id]
            if sat.alive and sat.reachable:
                logger.info("[%s] satellite %s is reachable",
                            realm.get_name(), sat.get_name())
                satellites.append(sat)
            else:
                logger.warning("[%s] satellite %s is not reachable",
                               realm.get_name(), sat.get_name())

        if not satellites:
            logger.warning("[%s] no %s satellites available for dispatch",
                           realm.get_name(), sat_type)
            return

        satellite_string = "[%s] Dispatching %s satellites ordered as: " % (
            realm.get_name(), sat_type)
        for sat in satellites:
            satellite_string += '%s (spare:%s), ' % (sat.get_name(), str(sat.spare))
        logger.info(satellite_string)

        conf_uuid = cfg.uuid
        # Now we dispatch cfg to every one ask for it
        nb_cfg_prepared = 0
        for sat in satellites:
            # Todo: Remove this test, because the number of satellites per type in a realm
            # do not take care of the spare daemons
            # if nb_cfg_prepared >= realm.get_nb_of_must_have_satellites(sat_type):
            #     logger.warning("Already prepared enough satellites: %d / %s",
            #                    nb_cfg_prepared, sat_type)
            #     continue
            sat.cfg['schedulers'][conf_uuid] = realm.to_satellites[sat_type][conf_uuid]
            if sat.manage_arbiters:
                sat.cfg['arbiters'] = arbiters_cfg

            # Brokers should have poller/reactionners links too
            if sat_type == "broker":
                realm.fill_broker_with_poller_reactionner_links(sat,
                                                                self.pollers,
                                                                self.reactionners,
                                                                self.receivers,
                                                                self.realms)
            sat.active = False
            sat.is_sent = False

            sat.known_conf_managed_push(conf_uuid, cfg.push_flavor)

            nb_cfg_prepared += 1
            realm.to_satellites_managed_by[sat_type][conf_uuid].append(sat)

        # I've got enough satellite, the next ones are considered spares
        if nb_cfg_prepared == realm.get_nb_of_must_have_satellites(sat_type):
            logger.info("[%s] OK, no more %s needed", realm.get_name(), sat_type)
            realm.to_satellites_need_dispatch[sat_type][conf_uuid] = False

    def dispatch(self):
        """
        Send configuration to satellites

        :return: None
        """
        if self.dispatch_ok:
            return

        self.dispatch_ok = True
        for scheduler in self.schedulers:
            if scheduler.is_sent:
                continue
            start = time.time()
            logger.info('Sending configuration to scheduler %s', scheduler.get_name())
            is_sent = False
            if scheduler.reachable:
                is_sent = scheduler.put_conf(scheduler.conf_package)
            else:
                logger.warning("Scheduler %s is not reachable", scheduler.get_name())

            logger.debug("Conf is sent in %d", time.time() - start)
            if not is_sent:
                logger.warning('Configuration not sent to scheduler %s', scheduler.get_name())
                self.dispatch_ok = False
            else:
                logger.info('Configuration sent to scheduler %s (%s)',
                            scheduler.get_name(), time.time() - start)
                scheduler.is_sent = True

        for sat_type in ('reactionner', 'poller', 'broker', 'receiver'):
            for satellite in self.satellites:
                if satellite.get_my_type() == sat_type:
                    if satellite.is_sent:
                        continue
                    start = time.time()
                    logger.info('Sending configuration to %s %s', sat_type, satellite.get_name())
                    satellite.is_sent = False
                    if satellite.reachable:
                        satellite.is_sent = satellite.put_conf(satellite.cfg)
                    else:
                        logger.warning("%s %s is not reachable", sat_type, satellite.get_name())
                    if not satellite.is_sent:
                        logger.warning('Configuration not sent to %s %s',
                                       sat_type, satellite.get_name())
                        self.dispatch_ok = False
                        continue
                    satellite.active = True

                    logger.info('Configuration sent to %s %s (%s)',
                                sat_type, satellite.get_name(), time.time() - start)
