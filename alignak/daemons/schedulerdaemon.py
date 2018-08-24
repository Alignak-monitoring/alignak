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
#     Guillaume Bour, guillaume@bour.cc
#     aviau, alexandre.viau@savoirfairelinux.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Olivier Hanesse, olivier.hanesse@gmail.com
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
This module provide Alignak which is the main scheduling daemon class
"""

import time
import traceback
import logging
import threading

from alignak.misc.serialization import unserialize, AlignakClassLookupException
from alignak.scheduler import Scheduler
from alignak.macroresolver import MacroResolver
from alignak.brok import Brok
from alignak.external_command import ExternalCommandManager
from alignak.stats import statsmgr
from alignak.http.scheduler_interface import SchedulerInterface
from alignak.property import IntegerProp, StringProp
from alignak.satellite import BaseSatellite
from alignak.objects.satellitelink import SatelliteLink

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Alignak(BaseSatellite):
    # pylint: disable=too-many-instance-attributes
    """Scheduler class. Referenced as "app" in most Interface

    """

    properties = BaseSatellite.properties.copy()
    properties.update({
        'type':
            StringProp(default='scheduler'),
        'port':
            IntegerProp(default=7768)
    })

    def __init__(self, **kwargs):
        """Scheduler daemon initialisation

        :param kwargs: command line arguments
        """
        super(Alignak, self).__init__(kwargs.get('daemon_name', 'Default-scheduler'), **kwargs)

        self.http_interface = SchedulerInterface(self)
        self.sched = Scheduler(self)

        # stats part
        # --- copied from scheduler.py
        self.nb_pulled_checks = 0
        self.nb_pulled_actions = 0
        # self.nb_checks_send = 0

        self.nb_pushed_checks = 0
        self.nb_pushed_actions = 0

        self.nb_pulled_broks = 0
        # ---

        # And possible links for satellites
        self.brokers = {}
        self.pollers = {}
        self.reactionners = {}
        self.receivers = {}

        # This because it is the Satellite that has thes properties and I am a Satellite
        # todo: change this?
        # Broks are stored in each broker link, not locally
        # self.broks = []
        self.broks_lock = threading.RLock()

        # Modules are only loaded one time
        self.have_modules = False

        self.first_scheduling = False

    def get_broks(self, broker_name):
        """Send broks to a specific broker

        :param broker_name: broker name to send broks
        :type broker_name: str
        :greturn: dict of brok for this broker
        :rtype: dict[alignak.brok.Brok]
        """
        logger.debug("Broker %s requests my broks list", broker_name)
        res = []
        if not broker_name:
            return res

        for broker_link in list(self.brokers.values()):
            if broker_name == broker_link.name:
                for brok in sorted(broker_link.broks, key=lambda x: x.creation_time):
                    # Only provide broks that did not yet sent to our external modules
                    if getattr(brok, 'sent_to_externals', False):
                        res.append(brok)
                        brok.got = True
                broker_link.broks = [b for b in broker_link.broks if not getattr(b, 'got', False)]
                logger.debug("Providing %d broks to %s", len(res), broker_name)
                break
        else:
            logger.warning("Got a brok request from an unknown broker: %s", broker_name)

        return res

    def compensate_system_time_change(self, difference):  # pragma: no cover,
        # pylint: disable=too-many-branches
        # not with unit tests
        """Compensate a system time change of difference for all hosts/services/checks/notifs

        :param difference: difference in seconds
        :type difference: int
        :return: None
        """
        super(Alignak, self).compensate_system_time_change(difference)

        # We only need to change some value
        self.program_start = max(0, self.program_start + difference)

        if not hasattr(self.sched, "conf"):
            # Race condition where time change before getting conf
            return

        # Then we compensate all host/services
        for host in self.sched.hosts:
            host.compensate_system_time_change(difference)
        for serv in self.sched.services:
            serv.compensate_system_time_change(difference)

        # Now all checks and actions
        for chk in list(self.sched.checks.values()):
            # Already launch checks should not be touch
            if chk.status == u'scheduled' and chk.t_to_go is not None:
                t_to_go = chk.t_to_go
                ref = self.sched.find_item_by_id(chk.ref)
                new_t = max(0, t_to_go + difference)
                timeperiod = self.sched.timeperiods[ref.check_period]
                if timeperiod is not None:
                    # But it's no so simple, we must match the timeperiod
                    new_t = timeperiod.get_next_valid_time_from_t(new_t)
                # But maybe no there is no more new value! Not good :(
                # Say as error, with error output
                if new_t is None:
                    chk.state = u'waitconsume'
                    chk.exit_status = 2
                    chk.output = '(Error: there is no available check time after time change!)'
                    chk.check_time = time.time()
                    chk.execution_time = 0
                else:
                    chk.t_to_go = new_t
                    ref.next_chk = new_t

        # Now all checks and actions
        for act in list(self.sched.actions.values()):
            # Already launch checks should not be touch
            if act.status == u'scheduled':
                t_to_go = act.t_to_go

                #  Event handler do not have ref
                ref_id = getattr(act, 'ref', None)
                new_t = max(0, t_to_go + difference)

                # Notification should be check with notification_period
                if act.is_a == u'notification':
                    ref = self.sched.find_item_by_id(ref_id)
                    if ref.notification_period:
                        # But it's no so simple, we must match the timeperiod
                        notification_period = self.sched.timeperiods[ref.notification_period]
                        new_t = notification_period.get_next_valid_time_from_t(new_t)
                    # And got a creation_time variable too
                    act.creation_time += difference

                # But maybe no there is no more new value! Not good :(
                # Say as error, with error output
                if new_t is None:
                    act.state = 'waitconsume'
                    act.exit_status = 2
                    act.output = '(Error: there is no available check time after time change!)'
                    act.check_time = time.time()
                    act.execution_time = 0
                else:
                    act.t_to_go = new_t

    def do_before_loop(self):
        """Stop the scheduling process"""
        if self.sched:
            self.sched.stop_scheduling()

    def do_loop_turn(self):
        """Scheduler loop turn

        Simply run the Alignak scheduler loop

        This is called when a configuration got received by the scheduler daemon. As of it,
        check if the first scheduling has been done... and manage this.

        :return: None
        """
        if not self.first_scheduling:
            # Ok, now all is initialized, we can make the initial broks
            logger.info("First scheduling launched")
            _t0 = time.time()
            # Program start brok
            self.sched.initial_program_status()
            # First scheduling
            self.sched.schedule()
            statsmgr.timer('first_scheduling', time.time() - _t0)
            logger.info("First scheduling done")

            # Connect to our passive satellites if needed
            for satellite in [s for s in list(self.pollers.values()) if s.passive]:
                if not self.daemon_connection_init(satellite):
                    logger.error("Passive satellite connection failed: %s", satellite)

            for satellite in [s for s in list(self.reactionners.values()) if s.passive]:
                if not self.daemon_connection_init(satellite):
                    logger.error("Passive satellite connection failed: %s", satellite)

            # Ticks are for recurrent function call like consume, del zombies etc
            self.sched.ticks = 0
            self.first_scheduling = True

        # Each loop turn, execute the daemon specific treatment...
        # only if the daemon has a configuration to manage
        if self.sched.pushed_conf:
            # If scheduling is not yet enabled, enable scheduling
            if not self.sched.must_schedule:
                self.sched.start_scheduling()
                self.sched.before_run()
            self.sched.run()
        else:
            logger.warning("#%d - No monitoring configuration to scheduler...",
                           self.loop_count)

    def get_managed_configurations(self):
        """Get the configurations managed by this scheduler

        The configuration managed by a scheduler is the self configuration got
        by the scheduler during the dispatching.

        :return: a dict of scheduler links with instance_id as key and
        hash, push_flavor and configuration identifier as values
        :rtype: dict
        """
        # for scheduler_link in list(self.schedulers.values()):
        #     res[scheduler_link.instance_id] = {
        #         'hash': scheduler_link.hash,
        #         'push_flavor': scheduler_link.push_flavor,
        #         'managed_conf_id': scheduler_link.managed_conf_id
        #     }

        res = {}
        if self.sched.pushed_conf and self.cur_conf and 'instance_id' in self.cur_conf:
            res[self.cur_conf['instance_id']] = {
                'hash': self.cur_conf['hash'],
                'push_flavor': self.cur_conf['push_flavor'],
                'managed_conf_id': self.cur_conf['managed_conf_id']
            }
        logger.debug("Get managed configuration: %s", res)
        return res

    def setup_new_conf(self):
        # pylint: disable=too-many-statements, too-many-branches, too-many-locals
        """Setup new conf received for scheduler

        :return: None
        """
        # Execute the base class treatment...
        super(Alignak, self).setup_new_conf()

        # ...then our own specific treatment!
        with self.conf_lock:
            # self_conf is our own configuration from the alignak environment
            self_conf = self.cur_conf['self_conf']
            if 'conf_part' not in self.cur_conf:
                self.cur_conf['conf_part'] = None
            conf_part = self.cur_conf['conf_part']

            # Ok now we can save the retention data
            if self.sched.pushed_conf is not None:
                self.sched.update_retention()

            # Get the monitored objects configuration
            t00 = time.time()
            received_conf_part = None
            try:
                received_conf_part = unserialize(conf_part)
                assert received_conf_part is not None
            except AssertionError as exp:
                # This to indicate that no configuration is managed by this scheduler...
                logger.warning("No managed configuration received from arbiter")
            except AlignakClassLookupException as exp:  # pragma: no cover
                # This to indicate that the new configuration is not managed...
                self.new_conf = {
                    "_status": "Cannot un-serialize configuration received from arbiter",
                    "_error": str(exp)
                }
                logger.error(self.new_conf)
                logger.error("Back trace of the error:\n%s", traceback.format_exc())
                return
            except Exception as exp:  # pylint: disable=broad-except
                # This to indicate that the new configuration is not managed...
                self.new_conf = {
                    "_status": "Cannot un-serialize configuration received from arbiter",
                    "_error": str(exp)
                }
                logger.error(self.new_conf)
                self.exit_on_exception(exp, str(self.new_conf))

            # if not received_conf_part:
            #     return

            logger.info("Monitored configuration %s received at %d. Un-serialized in %d secs",
                        received_conf_part, t00, time.time() - t00)
            logger.info("Scheduler received configuration : %s", received_conf_part)

            # Now we create our pollers, reactionners and brokers
            for link_type in ['pollers', 'reactionners', 'brokers']:
                if link_type not in self.cur_conf['satellites']:
                    logger.error("Missing %s in the configuration!", link_type)
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

                    # Replacing the satellite address and port by those defined in satellite_map
                    if new_link.name in self.cur_conf['override_conf'].get('satellite_map', {}):
                        override_conf = self.cur_conf['override_conf']
                        overriding = override_conf.get('satellite_map')[new_link.name]
                        logger.warning("Do not override the configuration for: %s, with: %s. "
                                       "Please check whether this is necessary!",
                                       new_link.name, overriding)

            # First mix conf and override_conf to have our definitive conf
            for prop in getattr(self.cur_conf, 'override_conf', []):
                logger.debug("Overriden: %s / %s ", prop, getattr(received_conf_part, prop, None))
                logger.debug("Overriding: %s / %s ", prop, self.cur_conf['override_conf'])
                setattr(received_conf_part, prop, self.cur_conf['override_conf'].get(prop, None))

            # Scheduler modules
            if not self.have_modules:
                try:
                    logger.debug("Modules configuration: %s", self.cur_conf['modules'])
                    self.modules = unserialize(self.cur_conf['modules'], no_load=True)
                except AlignakClassLookupException as exp:  # pragma: no cover, simple protection
                    logger.error('Cannot un-serialize modules configuration '
                                 'received from arbiter: %s', exp)
                if self.modules:
                    logger.debug("I received some modules configuration: %s", self.modules)
                    self.have_modules = True

                    self.do_load_modules(self.modules)
                    # and start external modules too
                    self.modules_manager.start_external_instances()
                else:
                    logger.info("I do not have modules")

            if received_conf_part:
                logger.info("Loading configuration...")

                # Propagate the global parameters to the configuration items
                received_conf_part.explode_global_conf()

                # We give the configuration to our scheduler
                self.sched.reset()
                self.sched.load_conf(self.cur_conf['instance_id'],
                                     self.cur_conf['instance_name'],
                                     received_conf_part)

                # Once loaded, the scheduler has an inner pushed_conf object
                logger.info("Loaded: %s", self.sched.pushed_conf)

                # Update the scheduler ticks according to the daemon configuration
                self.sched.update_recurrent_works_tick(self)

                # We must update our pushed configuration macros with correct values
                # from the configuration parameters
                # self.sched.pushed_conf.fill_resource_macros_names_macros()

                # Creating the Macroresolver Class & unique instance
                m_solver = MacroResolver()
                m_solver.init(received_conf_part)

                # Now create the external commands manager
                # We are an applyer: our role is not to dispatch commands, but to apply them
                ecm = ExternalCommandManager(received_conf_part, 'applyer', self.sched,
                                             self_conf.get('accept_passive_unknown_check_results',
                                                           False))

                # Scheduler needs to know about this external command manager to use it if necessary
                self.sched.external_commands_manager = ecm

                # Ok now we can load the retention data
                self.sched.retention_load()

                # Log hosts/services initial states
                self.sched.log_initial_states()

            # Create brok new conf
            brok = Brok({'type': 'new_conf', 'data': {}})
            self.sched.add_brok(brok)

            # Initialize connection with all our satellites
            logger.info("Initializing connection with my satellites:")
            my_satellites = self.get_links_of_type(s_type='')
            for satellite in list(my_satellites.values()):
                logger.info("- : %s/%s", satellite.type, satellite.name)
                if not self.daemon_connection_init(satellite):
                    logger.error("Satellite connection failed: %s", satellite)

            if received_conf_part:
                # Enable the scheduling process
                logger.info("Loaded: %s", self.sched.pushed_conf)
                self.sched.start_scheduling()

        # Now I have a configuration!
        self.have_conf = True

    def clean_previous_run(self):
        """Clean variables from previous configuration

        :return: None
        """
        # Execute the base class treatment...
        super(Alignak, self).clean_previous_run()

        # Clean all lists
        self.pollers.clear()
        self.reactionners.clear()
        self.brokers.clear()

    def get_daemon_stats(self, details=False):
        """Increase the stats provided by the Daemon base class

        :return: stats dictionary
        :rtype: dict
        """
        # Call the base Daemon one
        res = super(Alignak, self).get_daemon_stats(details=details)

        res.update({'name': self.name, 'type': self.type, 'monitored_objects': {}})

        counters = res['counters']

        # Satellites counters
        counters['brokers'] = len(self.brokers)
        counters['pollers'] = len(self.pollers)
        counters['reactionners'] = len(self.reactionners)
        counters['receivers'] = len(self.receivers)

        if not self.sched:
            return res

        # # Hosts/services problems counters
        # m_solver = MacroResolver()
        # counters['hosts_problems'] = m_solver._get_total_host_problems()
        # counters['hosts_unhandled_problems'] = m_solver._get_total_host_problems_unhandled()
        # counters['services_problems'] = m_solver._get_total_service_problems()
        # counters['services_unhandled_problems'] = m_solver._get_total_service_problems_unhandled()

        # Get statistics from the scheduler
        scheduler_stats = self.sched.get_scheduler_stats(details=details)
        res['counters'].update(scheduler_stats['counters'])
        scheduler_stats.pop('counters')
        res.update(scheduler_stats)

        return res

    def get_monitoring_problems(self):
        """Get the current scheduler livesynthesis

        :return: live synthesis and problems dictionary
        :rtype: dict
        """
        res = {}
        if not self.sched:
            return res

        # Get statistics from the scheduler
        scheduler_stats = self.sched.get_scheduler_stats(details=True)
        if 'livesynthesis' in scheduler_stats:
            res['livesynthesis'] = scheduler_stats['livesynthesis']
        if 'problems' in scheduler_stats:
            res['problems'] = scheduler_stats['problems']

        return res

    def main(self):
        """Main function for Scheduler, launch after the init::

        * Init daemon
        * Load module manager
        * Launch main loop
        * Catch any Exception that occurs

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

                # On main loop exit, call the scheduler after run process
                self.sched.after_run()

            self.request_stop()
        except Exception:  # pragma: no cover, this should never happen indeed ;)
            self.exit_on_exception(traceback.format_exc())
            raise
