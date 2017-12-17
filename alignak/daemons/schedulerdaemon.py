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

import os
import signal
import time
import traceback
import logging

from alignak.misc.serialization import unserialize, AlignakClassLookupException
from alignak.scheduler import Scheduler
from alignak.macroresolver import MacroResolver
from alignak.brok import Brok
from alignak.external_command import ExternalCommandManager
from alignak.daemon import Daemon
from alignak.http.scheduler_interface import SchedulerInterface
from alignak.property import IntegerProp, StringProp
from alignak.satellite import BaseSatellite
from alignak.objects.satellitelink import SatelliteLink

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Alignak(BaseSatellite):
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
        super(BaseSatellite, self).__init__(kwargs.get('daemon_name',
                                                       'Default-scheduler'), **kwargs)

        self.http_interface = SchedulerInterface(self)
        self.sched = Scheduler(self)

        self.must_run = True

        # Now the interface
        # self.uri = None
        # self.uri2 = None

        # stats part
        # --- copied from scheduler.py
        self.nb_pulled_checks = 0
        self.nb_pulled_actions = 0
        # self.nb_checks_send = 0

        self.nb_pushed_checks = 0
        self.nb_pushed_actions = 0

        self.nb_broks_send = 0
        self.nb_pulled_broks = 0
        # ---

        # And possible links for satellites
        self.arbiters = {}
        self.brokers = {}
        self.pollers = {}
        self.reactionners = {}
        self.receivers = {}

        # Modules are only loaded one time
        self.have_modules = False

    def compensate_system_time_change(self, difference, timeperiods):  # pragma: no cover,
        # not with unit tests
        """Compensate a system time change of difference for all hosts/services/checks/notifs

        :param difference: difference in seconds
        :type difference: int
        :return: None
        """
        super(BaseSatellite, self).compensate_system_time_change(difference, timeperiods)

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
        for chk in self.sched.checks.values():
            # Already launch checks should not be touch
            if chk.status == 'scheduled' and chk.t_to_go is not None:
                t_to_go = chk.t_to_go
                ref = self.sched.find_item_by_id(chk.ref)
                new_t = max(0, t_to_go + difference)
                timeperiod = timeperiods[ref.check_period]
                if timeperiod is not None:
                    # But it's no so simple, we must match the timeperiod
                    new_t = timeperiod.get_next_valid_time_from_t(new_t)
                # But maybe no there is no more new value! Not good :(
                # Say as error, with error output
                if new_t is None:
                    chk.state = 'waitconsume'
                    chk.exit_status = 2
                    chk.output = '(Error: there is no available check time after time change!)'
                    chk.check_time = time.time()
                    chk.execution_time = 0
                else:
                    chk.t_to_go = new_t
                    ref.next_chk = new_t

        # Now all checks and actions
        for act in self.sched.actions.values():
            # Already launch checks should not be touch
            if act.status == 'scheduled':
                t_to_go = act.t_to_go

                #  Event handler do not have ref
                ref_id = getattr(act, 'ref', None)
                new_t = max(0, t_to_go + difference)

                # Notification should be check with notification_period
                if act.is_a == 'notification':
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

    def manage_signal(self, sig, frame):
        """Manage signals caught by the daemon
        signal.SIGUSR1 : dump_memory
        signal.SIGUSR2 : dump_object (nothing)
        signal.SIGTERM, signal.SIGINT : terminate process

        :param sig: signal caught by daemon
        :type sig: str
        :param frame: current stack frame
        :type frame:
        :return: None
        TODO: Refactor with Daemon one
        """
        logger.info("scheduler process %d received a signal: %s", os.getpid(), str(sig))
        # If we got USR1, just dump memory
        if sig == signal.SIGUSR1:
            self.sched.need_dump_memory = True
        elif sig == signal.SIGUSR2:  # usr2, dump objects
            self.sched.need_objects_dump = True
        else:  # if not, die :)
            logger.info("scheduler process %d is dying...", os.getpid())
            self.sched.stop_scheduling()
            self.must_run = False
            Daemon.manage_signal(self, sig, frame)

    def do_loop_turn(self):
        """Scheduler loop turn
        Basically wait initial conf and run

        :return: None
        """
        # Ok, now the conf
        self.wait_for_initial_conf()
        if not self.new_conf:
            return
        logger.info("New configuration received")
        self.setup_new_conf()
        logger.info("[%s] New configuration loaded, scheduling for Alignak: %s",
                    self.name, self.sched.alignak_name)
        self.sched.run()

    def setup_new_conf(self):  # pylint: disable=too-many-statements
        """Setup new conf received for scheduler

        :return: None
        """
        # Execute the base class treatment...
        super(Alignak, self).setup_new_conf()

        # ...then our own specific treatment!
        with self.conf_lock:
            print("Scheduler - New configuration for: %s / %s" % (self.type, self.name))
            logger.info("[%s] Received a new configuration", self.name)

            # self_conf is our own configuration from the alignak environment
            self_conf = self.cur_conf['self_conf']
            conf_part = self.cur_conf['conf_part']

            # Ok now we can save the retention data
            if getattr(self.sched, 'conf', None) is not None:
                self.sched.update_retention(forced=True)

            # Get the monitored objects configuration
            t00 = time.time()
            try:
                self.conf = unserialize(conf_part)
            except AlignakClassLookupException as exp:  # pragma: no cover, simple protection
                logger.error('Cannot un-serialize configuration received from arbiter: %s', exp)
            logger.info("Conf received at %d. Un-serialized in %d secs", t00, time.time() - t00)

            # Now we create our pollers, reactionners and brokers
            for link_type in ['pollers', 'reactionners', 'brokers']:
                if link_type not in self.cur_conf['satellites']:
                    logger.error("[%s] Missing %s in the configuration!", self.name, link_type)
                    print("***[%s] Missing %s in the configuration!!!" % (self.name, link_type))
                    continue

                received_satellites = self.cur_conf['satellites'][link_type]
                logger.debug("[%s] - received %s: %s", self.name, link_type, received_satellites)
                my_satellites = getattr(self, link_type)
                print("My %s satellites: %s" % (link_type, my_satellites))
                print("My %s received satellites:" % (link_type))
                for link_uuid in received_satellites:
                    print("- %s / %s" % (link_uuid, received_satellites[link_uuid]))
                    logger.debug("[%s] - my current %s: %s", self.name, link_type, my_satellites)
                    # Must look if we already had a configuration and save our broks
                    already_got = received_satellites.get('_id') in my_satellites
                    broks = {}
                    actions = {}
                    wait_homerun = {}
                    external_commands = {}
                    running_id = 0
                    if already_got:
                        print("Already got!")
                        # Save some information
                        running_id = my_satellites[link_uuid].running_id
                        (broks, actions,
                         wait_homerun, external_commands) = link.get_and_clear_context()
                        # Delete the former link
                        del my_satellites[link_uuid]

                    # My new satellite link...
                    new_link = SatelliteLink.get_a_satellite_link(
                        link_type[:-1], received_satellites[link_uuid])
                    my_satellites[link_uuid] = new_link
                    print("My new %s satellite: %s" % (link_type, new_link))

                    new_link.running_id = running_id
                    new_link.external_commands = external_commands
                    new_link.broks = broks
                    new_link.wait_homerun = wait_homerun
                    new_link.actions = actions

                    # Replacing the satellite address and port by those defined in satellitemap
                    if new_link.name in self.cur_conf['override_conf'].get('satellitemap', {}):
                        override_conf = self.cur_conf['override_conf']
                        overriding = override_conf.get('satellitemap')[new_link.name]
                        logger.warning("Do not override the configuration for: %s, with: %s. "
                                       "Please check whether this is necessary!",
                                       new_link.name, overriding)
                        # satellite = dict(satellite)  # make a copy
                        # satellite_object.update(self.cur_conf['override_conf'].
                        # get('satellitemap', {})[satellite_object.name])

                logger.debug("We have our %s: %s", link_type, my_satellites)
                logger.info("We have our %s:", link_type)
                print("We have our %s" % link_type)
                for sat_link in my_satellites.values():
                    logger.info(" - %s, %s", sat_link.name, sat_link.address)
                    print(" - %s, %s" % (sat_link.name, sat_link))

            # First mix conf and override_conf to have our definitive conf
            for prop in self.cur_conf['override_conf']:
                print("Overriding: %s / %s " % (prop, self.cur_conf['override_conf']))
                setattr(self.conf, prop, self.cur_conf['override_conf'].get(prop, None))

            # Scheduler modules
            if not self.have_modules:
                self.modules = self_conf['modules']
                print("I received some modules configuration: %s" % self_conf)
                print("I received some modules configuration: %s" % self.modules)
                self.have_modules = True

                self.do_load_modules(self.modules)
                # and start external modules too
                self.modules_manager.start_external_instances()

            logger.info("Loading configuration...")
            print("Loading configuration: %s" % self.conf)
            # Propagate the global parameters to the configuration items
            self.conf.explode_global_conf()

            # we give sched it's conf
            self.sched.reset()
            self.sched.load_conf(self.conf)
            self.sched.load_satellites(self.pollers, self.reactionners, self.brokers)

            # Update the scheduler ticks according to the configuration
            self.sched.update_recurrent_works_tick(self_conf)

            # We must update our Config dict macro with good value
            # from the config parameters
            self.sched.conf.fill_resource_macros_names_macros()

            # Creating the Macroresolver Class & unique instance
            m_solver = MacroResolver()
            m_solver.init(self.conf)

            # self.conf.dump()
            # self.conf.quick_debug()

            # Now create the external commands manager
            # We are an applyer: our role is not to dispatch commands, but to apply them
            ecm = ExternalCommandManager(self.conf, 'applyer', self,
                                         self_conf.get('accept_passive_unknown_check_results',
                                                       False))

            # Scheduler needs to know about this external command manager to use it if necessary
            self.sched.set_external_commands_manager(ecm)

            # We update our managed schedulers, say it's us :)
            self.schedulers = {self.cur_conf['conf_uuid']: self.sched}

            # Ok now we can load the retention data
            self.sched.retention_load()

            # Create brok new conf
            brok = Brok({'type': 'new_conf', 'data': {}})
            self.sched.add_brok(brok)

            # Initialize connection with all our satellites
            my_satellites = self.get_links_of_type(s_type=None)
            for sat_link in my_satellites:
                satellite = my_satellites[sat_link]
                print("Initialize connection with: %s" % satellite)
                self.daemon_connection_init(satellite.uuid, s_type=satellite.type)

    def what_i_managed(self):
        # pylint: disable=no-member
        """Get my managed dict (instance id and push_flavor)

        :return: dict containing instance_id key and push flavor value
        :rtype: dict
        """
        if getattr(self, 'conf', None) is not None:
            return {self.conf.uuid: self.conf.push_flavor}  # pylint: disable=E1101

        return {}

    def clean_previous_run(self):
        """Clean variables from previous configuration

        :return: None
        """
        # Clean all lists
        self.pollers.clear()
        self.reactionners.clear()
        self.brokers.clear()

    def main(self):
        """Main function for Scheduler, launch after the init::

        * Init daemon
        * Load module manager
        * Launch main loop
        * Catch any Exception that occurs

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

            self.load_modules_manager()

            # self.uri = self.http_daemon.uri
            # logger.info("[Scheduler] General interface is at: %s", self.uri)

            self.do_mainloop()
        except Exception:
            self.print_unrecoverable(traceback.format_exc())
            raise
