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
 This is the Dispatcher class. Its role is to prepare the Alignak configuration to get
 dispatched to the Alignak satellites like schedulers, reactionners, pollers, receivers
 and brokers. It is responsible for high availability part.
 If an element dies and the element type has a spare, it sends the config of the
 dead one to the spare one.
"""

import sys
import hashlib
import json
import pickle
import logging
import time
import random

from alignak.misc.serialization import serialize
from alignak.util import master_then_spare
from alignak.objects.satellitelink import LinkError

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

# Always initialize random :)
random.seed()


class DispatcherError(Exception):
    """Exception raised for errors in the configuration dispatching.

    Attributes:
        msg  -- explanation of the error
    """

    def __init__(self, msg):
        super(DispatcherError, self).__init__()
        self.message = msg

    def __str__(self):  # pragma: no cover
        """Exception to String"""
        return "Dispatcher error: %s" % (self.message)


class Dispatcher(object):
    """Dispatcher is in charge of sending configuration to other daemon.
    It has to handle spare, realms, poller tags etc.
    """

    def __init__(self, conf, arbiter_link):
        # pylint: disable=too-many-branches
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

        self.arbiters = []
        self.schedulers = []
        self.reactionners = []
        self.pollers = []
        self.brokers = []
        self.receivers = []

        # List the satellites that are not configured
        self.not_configured = []

        # Direct pointer to important elements for us
        self.arbiter_link = arbiter_link
        self.alignak_conf = conf
        logger.debug("Dispatcher configuration: %s / %s", self.arbiter_link, self.alignak_conf)

        logger.info("Dispatcher realms configuration:")
        for realm in self.alignak_conf.realms:
            logger.info("- %s:", realm.name)
            for cfg_part in list(realm.parts.values()):
                logger.info("  .%s (%s), flavor:%s, %s",
                            cfg_part.instance_id, cfg_part.uuid, cfg_part.push_flavor, cfg_part)

        logger.debug("Dispatcher satellites configuration:")
        for sat_type in ['arbiters', 'schedulers', 'reactionners',
                         'brokers', 'receivers', 'pollers']:
            setattr(self, sat_type, getattr(self.alignak_conf, sat_type))

            # for each satellite, we look if current arbiter have a specific
            # satellite map value set for this satellite.
            # if so, we give this map to the satellite (used to build satellite URI later)
            for satellite in getattr(self, sat_type):
                logger.debug("  . %s", satellite)
                satellite.set_arbiter_satellite_map(
                    self.arbiter_link.satellite_map.get(satellite.name, {}))

        logger.info("Dispatcher arbiters/satellites map:")
        for sat_type in ['arbiters', 'schedulers', 'reactionners',
                         'brokers', 'receivers', 'pollers']:
            for satellite in getattr(self, sat_type):
                logger.info("- %s: %s", satellite.name, satellite.uri)

        for link in self.get_satellites_list('arbiters'):
            # If not me and a spare arbiter...
            if link == self.arbiter_link:
                # I exclude myself from the dispatching, I have my configuration ;)
                continue

            # WTF, there is another master in my configuration!!!
            if not link.spare:
                raise DispatcherError("There is more than one master arbiter (%s) in "
                                      "the configuration. This is not acceptable!" % arbiter_link)

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

        # All daemon links initially need to have a configuration
        for daemon_link in self.all_daemons_links:
            # We do not need a configuration :)
            if daemon_link == self.arbiter_link:
                continue
            daemon_link.need_conf = True

        # Some flag about dispatch needed or not
        self.dispatch_ok = False
        self.new_to_dispatch = False
        self.first_dispatch_done = False

        self.stop_request_sent = False

        # Prepare the satellites configurations
        for satellite in self.all_daemons_links:
            satellite.prepare_for_conf()

    def check_reachable(self, forced=False, test=False):
        # pylint: disable=too-many-branches
        """Check all daemons state (reachable or not)

        If test parameter is True, do not really send but simulate only for testing purpose...

        The update_infos function returns None when no ping has been executed
        (too early...), or True / False according to the real ping and get managed
        configuration result. So, if the result is None, consider as not valid,
        else compute the global result...

        :return: True if all daemons are reachable
        """
        all_ok = True
        self.not_configured = []
        for daemon_link in self.all_daemons_links:
            if daemon_link == self.arbiter_link:
                # I exclude myself from the polling, sure I am reachable ;)
                continue

            if not daemon_link.active:
                # I exclude the daemons that are not active
                continue

            # ----------
            if test:
                # print("*** unit tests - setting %s as alive" % daemon_link.name)
                # Set the satellite as alive
                daemon_link.set_alive()
                daemon_link.running_id = time.time()
                # daemon_link.cfg_managed = {}
                # continue
            # ----------
            # Force the daemon communication only if a configuration is prepared
            result = False
            try:
                result = daemon_link.update_infos(forced=(forced or self.new_to_dispatch),
                                                  test=test)
            except LinkError:
                logger.warning("Daemon connection failed, I could not get fresh information.")

            if result is not False:
                if result is None:
                    # Come back later ... too recent daemon connection!
                    continue

                if result:
                    # Got a managed configuration
                    logger.debug("The %s '%s' manages %s",
                                 daemon_link.type, daemon_link.name, daemon_link.cfg_managed)
                    if not self.first_dispatch_done:
                        # I just (re)started the arbiter
                        self.not_configured.append(daemon_link)
                else:
                    # No managed configuration - a new dispatching is necessary but only
                    # if we already dispatched a configuration
                    # Probably a freshly restarted daemon ;)
                    logger.debug("The %s %s do not have a configuration",
                                 daemon_link.type, daemon_link.name)
                    # the daemon is not yet configured
                    self.not_configured.append(daemon_link)
                    daemon_link.configuration_sent = False
            else:
                # Got a timeout !
                self.not_configured.append(daemon_link)

        if self.not_configured and self.new_to_dispatch and not self.first_dispatch_done:
            logger.info("Dispatcher, these daemons are not configured: %s, "
                        "and a configuration is ready to dispatch, run the dispatching...",
                        ','.join(d.name for d in self.not_configured))
            self.dispatch_ok = False
            self.dispatch(test=test)

        elif self.not_configured and self.first_dispatch_done:
            logger.info("Dispatcher, these daemons are not configured: %s, "
                        "and a configuration has yet been dispatched dispatch, "
                        "a new dispatch is required...",
                        ','.join(d.name for d in self.not_configured))
            self.dispatch_ok = False
            # Avoid exception because dispatch is not accepted!
            self.new_to_dispatch = True
            self.first_dispatch_done = False
            self.dispatch(test=test)

        return all_ok

    def check_status_and_get_events(self):
        # pylint: disable=too-many-branches
        """Get all the daemons status


        :return: Dictionary with all the daemons returned information
        :rtype: dict
        """
        statistics = {}
        events = []
        for daemon_link in self.all_daemons_links:
            if daemon_link == self.arbiter_link:
                # I exclude myself from the polling, sure I am reachable ;)
                continue

            if not daemon_link.active:
                # I exclude the daemons that are not active
                continue

            try:
                # Do not get the details to avoid overloading the communication
                daemon_link.statistics = daemon_link.get_daemon_stats(details=False)
                if daemon_link.statistics:
                    daemon_link.statistics['_freshness'] = int(time.time())
                    statistics[daemon_link.name] = daemon_link.statistics
                    logger.debug("Daemon %s statistics: %s",
                                 daemon_link.name, daemon_link.statistics)
            except LinkError:
                logger.warning("Daemon connection failed, I could not get statistics.")

            try:
                got = daemon_link.get_events()
                if got:
                    events.extend(got)
                    logger.debug("Daemon %s has %d events: %s", daemon_link.name, len(got), got)
            except LinkError:
                logger.warning("Daemon connection failed, I could not get events.")

        return events

    def check_dispatch(self):  # pylint: disable=too-many-branches
        """Check that all active satellites have a configuration dispatched

        A DispatcherError exception is raised if no configuration is dispatched!

        :return: None
        """
        if not self.arbiter_link:
            raise DispatcherError("Dispatcher configuration problem: no valid arbiter link!")

        if not self.first_dispatch_done:
            raise DispatcherError("Dispatcher cannot check the dispatching, "
                                  "because no configuration is dispatched!")

        # We check for configuration parts to be dispatched on alive schedulers.
        # If not dispatched, we need a dispatch :) and if dispatched on a failed node,
        # remove the association, and need a new dispatch
        self.dispatch_ok = True
        some_satellites_are_missing = False

        # Get fresh information about the satellites
        logger.info("Getting fresh information")
        self.check_reachable(forced=True)

        logger.info("Checking realms dispatch:")
        for realm in self.alignak_conf.realms:
            logger.info("- realm %s:", realm.name)
            for cfg_part in list(realm.parts.values()):
                logger.info("  .configuration %s", cfg_part)

                # This should never happen, logically!
                if not cfg_part.scheduler_link:
                    self.dispatch_ok = False
                    logger.error("    not managed by any scheduler!")
                    continue

                logger.debug("    checking scheduler %s configuration: %s",
                             cfg_part.scheduler_link.name, cfg_part.instance_id)

                # Maybe the scheduler restarts, so it is alive but without
                # the expected configuration; set the configuration part as unmanaged
                # and ask for a new configuration dispatch
                if not cfg_part.scheduler_link.manages(cfg_part):
                    # We ask for a new dispatching
                    self.dispatch_ok = False
                    if cfg_part.scheduler_link.cfg_managed is None:
                        logger.warning("    %s not yet !.",
                                       cfg_part.scheduler_link.name)
                    else:
                        logger.warning("    the assigned scheduler %s does not manage the "
                                       "configuration; asking for a new configuration dispatch.",
                                       cfg_part.scheduler_link.name)
                    cfg_part.scheduler_link.cfg_to_manage = None
                    cfg_part.scheduler_link.push_flavor = ''
                    cfg_part.scheduler_link.hash = ''
                    cfg_part.scheduler_link.need_conf = True

                for sat_type in ('reactionner', 'poller', 'broker', 'receiver'):
                    logger.debug("    checking %ss configuration", sat_type)
                    # We must have the correct number of satellites or we are not happy
                    # So we are sure to raise a dispatch every loop a satellite is missing
                    if (len(realm.to_satellites_managed_by[sat_type][cfg_part.instance_id]) <
                            realm.get_nb_of_must_have_satellites(sat_type)):
                        some_satellites_are_missing = True

                        logger.warning("    missing %s satellites: %s / %s!", sat_type,
                                       realm.to_satellites_managed_by[sat_type][
                                           cfg_part.instance_id],
                                       realm.get_nb_of_must_have_satellites(sat_type))

                        # TODO: less violent! Must only resend to the one needing?
                        # must be caught by satellite who sees that
                        # it already has the conf and do nothing
                        self.dispatch_ok = False  # so we will redispatch all
                        realm.to_satellites_need_dispatch[sat_type][cfg_part.instance_id] = True
                        realm.to_satellites_managed_by[sat_type][cfg_part.instance_id] = []

                    for satellite in realm.to_satellites_managed_by[sat_type][cfg_part.instance_id]:
                        # Maybe the sat was marked as not alive, but still in
                        # to_satellites_managed_by. That means that a new dispatch
                        # is needed
                        # Or maybe it is alive but I thought that this satellite
                        # managed the conf and it doesn't.
                        # I ask a full redispatch of these cfg for both cases

                        if not satellite.reachable:
                            logger.info("    the %s %s is not reachable; "
                                        "assuming a correct configuration dispatch.",
                                        sat_type, satellite.name)
                            continue
                        # if not cfg_part.push_flavor:
                        #     logger.warning("    the %s %s manages an unmanaged configuration; "
                        #                    "asking for a new configuration dispatch.",
                        #                    sat_type, satellite.name)
                        if not satellite.manages(cfg_part):
                            logger.warning("    the %s %s does not manage "
                                           "the correct configuration; "
                                           "asking for a new configuration dispatch.",
                                           sat_type, satellite.name)
                            self.dispatch_ok = False
                            realm.to_satellites_need_dispatch[sat_type][cfg_part.instance_id] = True
                            realm.to_satellites_managed_by[sat_type][cfg_part.instance_id] = []

        if some_satellites_are_missing:
            logger.warning("Some satellites are not available for the current configuration")

        return self.dispatch_ok

    def get_satellites_list(self, sat_type):
        """Get a sorted satellite list: master then spare

        :param sat_type: type of the required satellites (arbiters, schedulers, ...)
        :type sat_type: str
        :return: sorted satellites list
        :rtype: list[alignak.objects.satellitelink.SatelliteLink]
        """
        satellites_list = []
        if sat_type in ['arbiters', 'schedulers', 'reactionners',
                        'brokers', 'receivers', 'pollers']:
            for satellite in getattr(self, sat_type):
                satellites_list.append(satellite)
            satellites_list = master_then_spare(satellites_list)

        return satellites_list

    def get_scheduler_ordered_list(self, realm):
        """Get sorted scheduler list for a specific realm

        List is ordered as: alive first, then spare (if any), then dead scheduler links

        :param realm: realm we want scheduler from
        :type realm: alignak.objects.realm.Realm
        :return: sorted scheduler list
        :rtype: list[alignak.objects.schedulerlink.SchedulerLink]
        """
        # Get the schedulers for the required realm
        scheduler_links = []
        for scheduler_link_uuid in realm.schedulers:
            scheduler_links.append(self.schedulers[scheduler_link_uuid])

        # Now we sort the schedulers so we take alive, then spare, then dead,
        alive = []
        spare = []
        deads = []
        for sdata in scheduler_links:
            if sdata.alive and not sdata.spare:
                alive.append(sdata)
            elif sdata.alive and sdata.spare:
                spare.append(sdata)
            else:
                deads.append(sdata)
        scheduler_links = []
        scheduler_links.extend(alive)
        scheduler_links.extend(spare)
        scheduler_links.extend(deads)

        scheduler_links.reverse()  # I need to pop the list, so reverse the list...
        return scheduler_links

    def prepare_dispatch(self):
        # pylint:disable=too-many-branches, too-many-statements, too-many-locals
        """
        Prepare dispatch, so prepare for each daemon (schedulers, brokers, receivers, reactionners,
        pollers)

        This function will only prepare something if self.new_to_dispatch is False
        It will reset the first_dispatch_done flag

        A DispatcherError exception is raised if a configuration is already prepared! Unset the
        new_to_dispatch flag before calling!

        :return: None
        """
        if self.new_to_dispatch:
            raise DispatcherError("A configuration is already prepared!")

        # So we are preparing a new dispatching...
        self.new_to_dispatch = True
        self.first_dispatch_done = False

        # Update Alignak name for all the satellites
        for daemon_link in self.all_daemons_links:
            daemon_link.cfg.update({'alignak_name': self.alignak_conf.alignak_name})

        logger.info("Preparing realms dispatch:")

        # Prepare the arbiters configuration
        master_arbiter_cfg = arbiters_cfg = {}
        for arbiter_link in self.get_satellites_list('arbiters'):
            # # If not me and not a spare arbiter...
            # if arbiter_link == self.arbiter_link:
            #     # I exclude myself from the dispatching, I have my configuration ;)
            #     continue

            if not arbiter_link.active:
                # I exclude the daemons that are not active
                continue

            arbiter_cfg = arbiter_link.cfg
            arbiter_cfg.update({
                'managed_hosts_names': [h.get_name() for h in self.alignak_conf.hosts],
                'modules': serialize(arbiter_link.modules, True),

                'managed_conf_id': self.alignak_conf.instance_id,
                'push_flavor': ''
            })

            # Hash the configuration
            cfg_string = json.dumps(arbiter_cfg, sort_keys=True).encode('utf-8')
            arbiter_cfg['hash'] = hashlib.sha1(cfg_string).hexdigest()

            # Update the arbiters list, but do not include the whole conf
            arbiters_cfg[arbiter_link.uuid] = arbiter_cfg['self_conf']

            # Not for the master arbiter...
            if arbiter_link != self.arbiter_link:
                arbiter_cfg.update({
                    'arbiters': master_arbiter_cfg,
                    'whole_conf': self.alignak_conf.spare_arbiter_conf,
                })

                # Hash the whole configuration
                try:
                    s_conf_part = json.dumps(arbiter_cfg, sort_keys=True).encode('utf-8')
                except UnicodeDecodeError:
                    pass
                arbiter_cfg['hash'] = hashlib.sha1(s_conf_part).hexdigest()

            # Dump the configuration part size
            pickled_conf = pickle.dumps(arbiter_cfg)
            logger.info('   arbiter configuration size: %d bytes', sys.getsizeof(pickled_conf))

            # The configuration is assigned to the arbiter
            # todo: perhaps this should be done in the realms (like schedulers and satellites)?
            arbiter_link.cfg = arbiter_cfg
            arbiter_link.cfg_to_manage = self.alignak_conf
            arbiter_link.push_flavor = arbiter_cfg['push_flavor']
            arbiter_link.hash = arbiter_cfg['hash']
            arbiter_link.need_conf = False
            arbiter_link.configuration_sent = False

            # If not me and not a spare arbiter...
            if arbiter_link == self.arbiter_link:
                # The master arbiter configuration for the other satellites
                master_arbiter_cfg = {self.arbiter_link.uuid: arbiter_cfg['self_conf']}

            logger.info('   arbiter configuration prepared for %s', arbiter_link.name)

        # main_realm = self.alignak_conf.realms.find_by_name('All')
        # all_realms = main_realm.all_sub_members
        # for realm_uuid in all_realms:
        #     realm = self.alignak_conf.realms[realm_uuid]
        #     logger.info("- realm %s: %s", realm_uuid, realm)

        for realm in self.alignak_conf.realms:
            logger.info("- realm %s: %d configuration part(s)", realm.name, len(realm.parts))

            # parts_to_dispatch is a list of configuration parts built when
            # the configuration is split into parts for the realms and their schedulers
            # Only get the parts that are not yet assigned to a scheduler
            parts_to_dispatch = [cfg for cfg in list(realm.parts.values()) if not cfg.is_assigned]
            if not parts_to_dispatch:
                logger.info('  no configuration to dispatch for this realm!')
                continue

            logger.info(" preparing the dispatch for schedulers:")

            # Now we get all the schedulers of this realm and upper
            schedulers = self.get_scheduler_ordered_list(realm)
            schedulers = realm.get_potential_satellites_by_type(
                self.get_satellites_list('schedulers'), 'scheduler')
            if not schedulers:
                logger.error('  no available schedulers in this realm (%s)!', realm)
                continue
            logger.info("  realm schedulers: %s",
                        ','.join([s.get_name() for s in schedulers]))

            for cfg_part in parts_to_dispatch:
                logger.info("  .assigning configuration part %s (%s), name:%s",
                            cfg_part.instance_id, cfg_part.uuid, cfg_part.config_name)

                # we need to loop until the configuration part is assigned to a scheduler
                # or no more scheduler is available
                while True:
                    try:
                        scheduler_link = schedulers.pop()
                    except IndexError:  # No more schedulers.. not good, no loop
                        # The configuration part do not need to be dispatched anymore
                        # todo: should be managed inside the Realm class!
                        for sat_type in ('reactionner', 'poller', 'broker', 'receiver'):
                            realm.to_satellites[sat_type][cfg_part.instance_id] = None
                            realm.to_satellites_need_dispatch[sat_type][cfg_part.instance_id] = \
                                False
                            realm.to_satellites_managed_by[sat_type][cfg_part.instance_id] = []
                        break

                    if not scheduler_link.need_conf:
                        logger.info('[%s] The scheduler %s do not need any configuration, sorry',
                                    realm.name, scheduler_link.name)
                        continue

                    logger.debug("   preparing configuration part '%s' for the scheduler '%s'",
                                 cfg_part.instance_id, scheduler_link.name)
                    logger.debug("   - %d hosts, %d services",
                                 len(cfg_part.hosts), len(cfg_part.services))

                    # Serialization and hashing
                    s_conf_part = serialize(realm.parts[cfg_part.instance_id])
                    try:
                        s_conf_part = s_conf_part.encode('utf-8')
                    except UnicodeDecodeError:
                        pass
                    cfg_part.push_flavor = hashlib.sha1(s_conf_part).hexdigest()

                    # We generate the scheduler configuration for the satellites:
                    # ---
                    sat_scheduler_cfg = scheduler_link.give_satellite_cfg()
                    sat_scheduler_cfg.update({
                        'managed_hosts_names': [h.get_name() for h in cfg_part.hosts],

                        'managed_conf_id': cfg_part.instance_id,
                        'push_flavor': cfg_part.push_flavor
                    })
                    # Generate a configuration hash
                    cfg_string = json.dumps(sat_scheduler_cfg, sort_keys=True).encode('utf-8')
                    sat_scheduler_cfg['hash'] = hashlib.sha1(cfg_string).hexdigest()

                    logger.debug(' satellite scheduler configuration: %s', sat_scheduler_cfg)
                    for sat_type in ('reactionner', 'poller', 'broker', 'receiver'):
                        realm.to_satellites[sat_type][cfg_part.instance_id] = sat_scheduler_cfg
                        realm.to_satellites_need_dispatch[sat_type][cfg_part.instance_id] = True
                        realm.to_satellites_managed_by[sat_type][cfg_part.instance_id] = []
                    # ---

                    scheduler_link.cfg.update({
                        # Global instance configuration
                        'instance_id': scheduler_link.instance_id,
                        'instance_name': scheduler_link.name,

                        'schedulers': {scheduler_link.uuid: sat_scheduler_cfg},
                        'arbiters': arbiters_cfg if scheduler_link.manage_arbiters else {},
                        'satellites': realm.get_links_for_a_scheduler(self.pollers,
                                                                      self.reactionners,
                                                                      self.brokers),

                        'modules': serialize(scheduler_link.modules, True),

                        'conf_part': serialize(realm.parts[cfg_part.instance_id]),
                        'managed_conf_id': cfg_part.instance_id,
                        'push_flavor': cfg_part.push_flavor,

                        'override_conf': scheduler_link.get_override_configuration()
                    })

                    # Hash the whole configuration
                    cfg_string = json.dumps(scheduler_link.cfg, sort_keys=True).encode('utf-8')
                    scheduler_link.cfg['hash'] = hashlib.sha1(cfg_string).hexdigest()

                    # Dump the configuration part size
                    pickled_conf = pickle.dumps(scheduler_link.cfg)
                    logger.info("   scheduler configuration size: %d bytes",
                                sys.getsizeof(pickled_conf))
                    logger.info("   scheduler satellites:")
                    satellites = realm.get_links_for_a_scheduler(self.pollers,
                                                                 self.reactionners,
                                                                 self.brokers)
                    for sat_type in satellites:
                        logger.info("   - %s", sat_type)
                        for sat_link_uuid in satellites[sat_type]:
                            satellite = satellites[sat_type][sat_link_uuid]
                            logger.info("   %s", satellite['name'])

                    # The configuration part is assigned to a scheduler
                    cfg_part.is_assigned = True
                    cfg_part.scheduler_link = scheduler_link
                    scheduler_link.cfg_to_manage = cfg_part
                    scheduler_link.push_flavor = cfg_part.push_flavor
                    scheduler_link.hash = scheduler_link.cfg['hash']
                    scheduler_link.need_conf = False
                    scheduler_link.configuration_sent = False

                    logger.info('   configuration %s (%s) assigned to %s',
                                cfg_part.instance_id, cfg_part.push_flavor, scheduler_link.name)

                    # The configuration part is assigned to a scheduler, no need to go further ;)
                    break

            logger.info(" preparing the dispatch for satellites:")
            for cfg_part in list(realm.parts.values()):
                logger.info("  .configuration part %s (%s), name:%s",
                            cfg_part.instance_id, cfg_part.uuid, cfg_part.config_name)
                for sat_type in ('reactionner', 'poller', 'broker', 'receiver'):
                    if cfg_part.instance_id not in realm.to_satellites_need_dispatch[sat_type]:
                        logger.debug("   nothing to dispatch for %ss", sat_type)
                        return

                    if not realm.to_satellites_need_dispatch[sat_type][cfg_part.instance_id]:
                        logger.debug("   no need to dispatch to %ss", sat_type)
                        return

                    # Get the list of the concerned satellites
                    satellites = realm.get_potential_satellites_by_type(self.satellites, sat_type)
                    if satellites:
                        logger.info("  realm %ss: %s",
                                    sat_type, ','.join([s.get_name() for s in satellites]))
                    else:
                        logger.info("   no %s satellites", sat_type)

                    # Now we dispatch cfg to every one ask for it
                    nb_cfg_prepared = 0
                    for sat_link in satellites:
                        if not sat_link.active:
                            # I exclude the daemons that are not active
                            continue

                        if nb_cfg_prepared > realm.get_nb_of_must_have_satellites(sat_type):
                            logger.warning("Too much configuration parts prepared "
                                           "for the expected satellites count. "
                                           "Realm: %s, satellite: %s - prepared: %d out of %d",
                                           realm.name, sat_link.name, nb_cfg_prepared,
                                           realm.get_nb_of_must_have_satellites(sat_type))
                            # Fred - 2018-07-20 - temporary disable this error raising!
                            # raise DispatcherError("Too much configuration parts prepared "
                            #                       "for the expected satellites count. "
                            #                       "This should never happen!")

                        logger.info("   preparing configuration part '%s' for the %s '%s'",
                                    cfg_part.instance_id, sat_type, sat_link.name)

                        sat_link.cfg.update({
                            # Global instance configuration
                            'arbiters': arbiters_cfg if sat_link.manage_arbiters else {},
                            'modules': serialize(sat_link.modules, True),
                            'managed_conf_id': 'see_my_schedulers',
                        })
                        sat_link.cfg['schedulers'].update({
                            cfg_part.uuid: realm.to_satellites[sat_type][cfg_part.instance_id]})

                        # Brokers should have pollers and reactionners links too
                        if sat_type == "broker":
                            sat_link.cfg.update({'satellites': realm.get_links_for_a_broker(
                                self.pollers, self.reactionners, self.receivers,
                                self.alignak_conf.realms, sat_link.manage_sub_realms)})

                        # Hash the whole configuration
                        cfg_string = json.dumps(sat_link.cfg, sort_keys=True).encode('utf-8')
                        sat_link.cfg['hash'] = hashlib.sha1(cfg_string).hexdigest()

                        # Dump the configuration part size
                        pickled_conf = pickle.dumps(sat_link.cfg)
                        logger.info('   %s configuration size: %d bytes',
                                    sat_type, sys.getsizeof(pickled_conf))

                        # The configuration part is assigned to a satellite
                        sat_link.cfg_to_manage = cfg_part
                        sat_link.push_flavor = cfg_part.push_flavor
                        sat_link.hash = sat_link.cfg['hash']
                        sat_link.need_conf = False
                        sat_link.configuration_sent = False

                        logger.info('   configuration %s (%s) assigned to %s',
                                    cfg_part.instance_id, cfg_part.push_flavor, sat_link.name)

                        nb_cfg_prepared += 1
                        realm.to_satellites_managed_by[sat_type][
                            cfg_part.instance_id].append(sat_link)

                        # I've got enough satellite, the next ones are considered unuseful!
                        if nb_cfg_prepared == realm.get_nb_of_must_have_satellites(sat_type):
                            logger.info("   no more %s needed in this realm.", sat_type)
                            realm.to_satellites_need_dispatch[sat_type][
                                cfg_part.instance_id] = False

        nb_missed = len([cfg for cfg in list(
            self.alignak_conf.parts.values()) if not cfg.is_assigned])
        if nb_missed > 0:
            logger.warning("Some configuration parts are not dispatched, %d are missing", nb_missed)
        else:
            logger.info("All configuration parts are assigned "
                        "to schedulers and their satellites :)")

        # Schedulers without a configuration in a dispatch ok do not need a configuration
        # so they do not raise dispatching errors if they are not used
        for scheduler_link in self.schedulers:
            if not scheduler_link.cfg_to_manage:
                # "so it do not ask anymore for conf"
                logger.warning('The scheduler %s do not need a configuration!', scheduler_link.name)
                scheduler_link.need_conf = False

    def dispatch(self, test=False):  # pylint: disable=too-many-branches
        """
        Send configuration to satellites

        :return: None
        """
        if not self.new_to_dispatch:
            raise DispatcherError("Dispatcher cannot dispatch, "
                                  "because no configuration is prepared!")

        if self.first_dispatch_done:
            raise DispatcherError("Dispatcher cannot dispatch, "
                                  "because the configuration is still dispatched!")

        if self.dispatch_ok:
            logger.info("Dispatching is already done and ok...")
            return

        logger.info("Trying to send configuration to the satellites...")

        self.dispatch_ok = True

        # todo: the 3 loops hereunder may be factorized
        for link in self.arbiters:
            # If not me and a spare arbiter...
            if link == self.arbiter_link:
                # I exclude myself from the dispatching, I have my configuration ;)
                continue

            if not link.active:
                # I exclude the daemons that are not active
                continue

            if not link.spare:
                # Do not dispatch to a master arbiter!
                continue

            if link.configuration_sent:
                logger.debug("Arbiter %s already sent!", link.name)
                continue

            if not link.reachable:
                logger.debug("Arbiter %s is not reachable to receive its configuration",
                             link.name)
                continue

            logger.info("Sending configuration to the arbiter %s", link.name)
            logger.debug("- %s", link.cfg)

            link.put_conf(link.cfg, test=test)
            link.configuration_sent = True

            logger.info("- sent")

            # Now that the spare arbiter has a configuration, tell him it must not run,
            # because I'm not dead ;)
            link.do_not_run()

        for link in self.schedulers:
            if link.configuration_sent:
                logger.debug("Scheduler %s already sent!", link.name)
                continue

            if not link.active:
                # I exclude the daemons that are not active
                continue

            if not link.reachable:
                logger.debug("Scheduler %s is not reachable to receive its configuration",
                             link.name)
                continue

            logger.info("Sending configuration to the scheduler %s", link.name)
            logger.debug("- %s", link.cfg)

            link.put_conf(link.cfg, test=test)
            link.configuration_sent = True

            logger.info("- sent")

        for link in self.satellites:
            if link.configuration_sent:
                logger.debug("%s %s already sent!", link.type, link.name)
                continue

            if not link.active:
                # I exclude the daemons that are not active
                continue

            if not link.reachable:
                logger.warning("%s %s is not reachable to receive its configuration",
                               link.type, link.name)
                continue

            logger.info("Sending configuration to the %s %s", link.type, link.name)
            logger.debug("- %s", link.cfg)

            link.put_conf(link.cfg, test=test)
            link.configuration_sent = True

            logger.info("- sent")

        if self.dispatch_ok:
            # Newly prepared configuration got dispatched correctly
            self.new_to_dispatch = False
            self.first_dispatch_done = True

    def stop_request(self, stop_now=False):
        """Send a stop request to all the daemons

        :param stop_now: stop now or go to stop wait mode
        :type stop_now: bool
        :return: True if all daemons are reachable
        """
        all_ok = True
        for daemon_link in self.all_daemons_links:
            logger.debug("Stopping: %s (%s)", daemon_link, stop_now)
            if daemon_link == self.arbiter_link:
                # I exclude myself from the process, I know we are going to stop ;)
                continue

            if not daemon_link.active:
                # I exclude the daemons that are not active
                continue

            # Send a stop request to the daemon
            try:
                stop_ok = daemon_link.stop_request(stop_now=stop_now)
            except LinkError:
                stop_ok = True
                logger.warning("Daemon stop request failed, %s probably stopped!", daemon_link)

            all_ok = all_ok and stop_ok

            daemon_link.stopping = True

        self.stop_request_sent = all_ok
        return self.stop_request_sent
