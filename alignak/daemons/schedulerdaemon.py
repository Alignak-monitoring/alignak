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
from alignak.property import PathProp, IntegerProp, StringProp
from alignak.satellite import BaseSatellite
from alignak.stats import statsmgr

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Alignak(BaseSatellite):
    """Scheduler class. Referenced as "app" in most Interface

    """

    properties = BaseSatellite.properties.copy()
    properties.update({
        'daemon_type':
            StringProp(default='scheduler'),
        'pidfile':
            PathProp(default='schedulerd.pid'),
        'port':
            IntegerProp(default=7768),
        'local_log':
            PathProp(default='schedulerd.log'),
    })

    def __init__(self, config_file, is_daemon, do_replace, debug, debug_file):

        BaseSatellite.__init__(self, 'scheduler', config_file, is_daemon, do_replace, debug,
                               debug_file)

        self.http_interface = SchedulerInterface(self)
        self.sched = Scheduler(self)

        self.must_run = True

        # Now the interface
        self.uri = None
        self.uri2 = None

        # And possible links for satellites
        # from now only pollers
        self.pollers = {}
        self.reactionners = {}
        self.brokers = {}

    def compensate_system_time_change(self, difference, timeperiods):
        """Compensate a system time change of difference for all hosts/services/checks/notifs

        :param difference: difference in seconds
        :type difference: int
        :return: None
        """
        logger.warning("A system time change of %d has been detected. Compensating...", difference)
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
        logger.info("process %d received a signal: %s", os.getpid(), str(sig))
        # If we got USR1, just dump memory
        if sig == signal.SIGUSR1:
            self.sched.need_dump_memory = True
        elif sig == signal.SIGUSR2:  # usr2, dump objects
            self.sched.need_objects_dump = True
        else:  # if not, die :)
            self.sched.die()
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
        logger.info("New configuration loaded")
        self.sched.run()

    def setup_new_conf(self):
        """Setup new conf received for scheduler

        :return: None
        """
        with self.conf_lock:
            self.clean_previous_run()
            new_c = self.new_conf
            logger.warning("Sending us a configuration %s", new_c['push_flavor'])
            conf_raw = new_c['conf']
            override_conf = new_c['override_conf']
            modules = new_c['modules']
            satellites = new_c['satellites']
            instance_name = new_c['instance_name']

            # Ok now we can save the retention data
            if hasattr(self.sched, 'conf'):
                self.sched.update_retention_file(forced=True)

            # horay, we got a name, we can set it in our stats objects
            statsmgr.register(instance_name, 'scheduler',
                              statsd_host=new_c['statsd_host'], statsd_port=new_c['statsd_port'],
                              statsd_prefix=new_c['statsd_prefix'],
                              statsd_enabled=new_c['statsd_enabled'])

            t00 = time.time()
            try:
                conf = unserialize(conf_raw)
            except AlignakClassLookupException as exp:
                logger.error('Cannot un-serialize configuration received from arbiter: %s', exp)
            logger.debug("Conf received at %d. Un-serialized in %d secs", t00, time.time() - t00)
            self.new_conf = None

            if 'scheduler_name' in new_c:
                name = new_c['scheduler_name']
            else:
                name = instance_name
            self.name = name

            # Set my own process title
            self.set_proctitle(self.name)

            # Tag the conf with our data
            self.conf = conf
            self.conf.push_flavor = new_c['push_flavor']
            self.conf.instance_name = instance_name
            self.conf.skip_initial_broks = new_c['skip_initial_broks']
            self.conf.accept_passive_unknown_check_results = \
                new_c['accept_passive_unknown_check_results']

            self.cur_conf = conf
            self.override_conf = override_conf
            self.modules = unserialize(modules, True)
            self.satellites = satellites

            # Now We create our pollers, reactionners and brokers
            for sat_type in ['pollers', 'reactionners', 'brokers']:
                if sat_type not in satellites:
                    continue
                for sat_id in satellites[sat_type]:
                    # Must look if we already have it
                    sats = getattr(self, sat_type)
                    sat = satellites[sat_type][sat_id]

                    sats[sat_id] = sat

                    if sat['name'] in override_conf['satellitemap']:
                        sat = dict(sat)  # make a copy
                        sat.update(override_conf['satellitemap'][sat['name']])

                    proto = 'http'
                    if sat['use_ssl']:
                        proto = 'https'
                    uri = '%s://%s:%s/' % (proto, sat['address'], sat['port'])

                    sats[sat_id]['uri'] = uri
                    sats[sat_id]['last_connection'] = 0
                    setattr(self, sat_type, sats)
                logger.debug("We have our %s: %s ", sat_type, satellites[sat_type])
                logger.info("We have our %s:", sat_type)
                for daemon in satellites[sat_type].values():
                    logger.info(" - %s ", daemon['name'])

            # First mix conf and override_conf to have our definitive conf
            for prop in self.override_conf:
                val = self.override_conf[prop]
                setattr(self.conf, prop, val)

            if self.conf.use_timezone != '':
                logger.debug("Setting our timezone to %s", str(self.conf.use_timezone))
                os.environ['TZ'] = self.conf.use_timezone
                time.tzset()

            self.do_load_modules(self.modules)

            logger.info("Loading configuration.")
            self.conf.explode_global_conf()  # pylint: disable=E1101

            # we give sched it's conf
            self.sched.reset()
            self.sched.load_conf(self.conf)
            self.sched.load_satellites(self.pollers, self.reactionners, self.brokers)

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
            ecm = ExternalCommandManager(self.conf, 'applyer', self.sched)

            # Scheduler needs to know about this external command manager to use it if necessary
            self.sched.set_external_commands_manager(ecm)
            # Update External Commands Manager
            self.sched.external_commands_manager.accept_passive_unknown_check_results = \
                self.sched.conf.accept_passive_unknown_check_results

            # We clear our schedulers managed (it's us :) )
            # and set ourselves in it
            self.schedulers = {self.conf.uuid: self.sched}  # pylint: disable=E1101

            # Ok now we can load the retention data
            self.sched.retention_load()

            # Create brok new conf
            brok = Brok({'type': 'new_conf', 'data': {}})
            self.sched.add_brok(brok)

    def what_i_managed(self):
        """Get my managed dict (instance id and push_flavor)

        :return: dict containing instance_id key and push flavor value
        :rtype: dict
        """
        if hasattr(self, 'conf'):
            return {self.conf.uuid: self.conf.push_flavor}  # pylint: disable=E1101
        else:
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

            self.do_daemon_init_and_start()

            self.load_modules_manager(self.name)

            self.uri = self.http_daemon.uri
            logger.info("[Scheduler] General interface is at: %s", self.uri)

            self.do_mainloop()
        except Exception:
            self.print_unrecoverable(traceback.format_exc())
            raise
