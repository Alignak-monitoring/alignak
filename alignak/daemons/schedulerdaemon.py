# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2015: Alignak team, see AUTHORS.txt file for contributors
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
import cPickle
from multiprocessing import process


from alignak.scheduler import Scheduler
from alignak.macroresolver import MacroResolver
from alignak.external_command import ExternalCommandManager
from alignak.daemon import Daemon
from alignak.http.scheduler_interface import SchedulerInterface
from alignak.property import PathProp, IntegerProp
from alignak.log import logger
from alignak.satellite import BaseSatellite
from alignak.stats import statsmgr


class Alignak(BaseSatellite):
    """Scheduler class. Referenced as "app" in most Interface

    """

    properties = BaseSatellite.properties.copy()
    properties.update({
        'pidfile':   PathProp(default='schedulerd.pid'),
        'port':      IntegerProp(default=7768),
        'local_log': PathProp(default='schedulerd.log'),
    })

    def __init__(self, config_file, is_daemon, do_replace, debug, debug_file, profile=''):

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

    def compensate_system_time_change(self, difference):
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
                ref = chk.ref
                new_t = max(0, t_to_go + difference)
                if ref.check_period is not None:
                    # But it's no so simple, we must match the timeperiod
                    new_t = ref.check_period.get_next_valid_time_from_t(new_t)
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
                ref = getattr(act, 'ref', None)
                new_t = max(0, t_to_go + difference)

                # Notification should be check with notification_period
                if act.is_a == 'notification':
                    if ref.notification_period:
                        # But it's no so simple, we must match the timeperiod
                        new_t = ref.notification_period.get_next_valid_time_from_t(new_t)
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
        logger.warning("%s > Received a SIGNAL %s", process.current_process(), sig)
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
            new_c = self.new_conf
            conf_raw = new_c['conf']
            override_conf = new_c['override_conf']
            modules = new_c['modules']
            satellites = new_c['satellites']
            instance_name = new_c['instance_name']
            push_flavor = new_c['push_flavor']
            skip_initial_broks = new_c['skip_initial_broks']
            accept_passive_unknown_chk_res = new_c['accept_passive_unknown_check_results']
            api_key = new_c['api_key']
            secret = new_c['secret']
            http_proxy = new_c['http_proxy']
            statsd_host = new_c['statsd_host']
            statsd_port = new_c['statsd_port']
            statsd_prefix = new_c['statsd_prefix']
            statsd_enabled = new_c['statsd_enabled']

            # horay, we got a name, we can set it in our stats objects
            statsmgr.register(self.sched, instance_name, 'scheduler',
                              api_key=api_key, secret=secret, http_proxy=http_proxy,
                              statsd_host=statsd_host, statsd_port=statsd_port,
                              statsd_prefix=statsd_prefix, statsd_enabled=statsd_enabled)

            t00 = time.time()
            conf = cPickle.loads(conf_raw)
            logger.debug("Conf received at %d. Unserialized in %d secs", t00, time.time() - t00)
            self.new_conf = None

            # Tag the conf with our data
            self.conf = conf
            self.conf.push_flavor = push_flavor
            self.conf.instance_name = instance_name
            self.conf.skip_initial_broks = skip_initial_broks
            self.conf.accept_passive_unknown_check_results = accept_passive_unknown_chk_res

            self.cur_conf = conf
            self.override_conf = override_conf
            self.modules = modules
            self.satellites = satellites
            # self.pollers = self.app.pollers

            if self.conf.human_timestamp_log:
                logger.set_human_format()

            # Now We create our pollers
            for pol_id in satellites['pollers']:
                # Must look if we already have it
                already_got = pol_id in self.pollers
                poll = satellites['pollers'][pol_id]
                self.pollers[pol_id] = poll

                if poll['name'] in override_conf['satellitemap']:
                    poll = dict(poll)  # make a copy
                    poll.update(override_conf['satellitemap'][poll['name']])

                proto = 'http'
                if poll['use_ssl']:
                    proto = 'https'
                uri = '%s://%s:%s/' % (proto, poll['address'], poll['port'])
                self.pollers[pol_id]['uri'] = uri
                self.pollers[pol_id]['last_connection'] = 0

            # Now We create our reactionners
            for reac_id in satellites['reactionners']:
                # Must look if we already have it
                already_got = reac_id in self.reactionners
                reac = satellites['reactionners'][reac_id]
                self.reactionners[reac_id] = reac

                if reac['name'] in override_conf['satellitemap']:
                    reac = dict(reac)  # make a copy
                    reac.update(override_conf['satellitemap'][reac['name']])

                proto = 'http'
                if poll['use_ssl']:
                    proto = 'https'
                uri = '%s://%s:%s/' % (proto, reac['address'], reac['port'])
                self.reactionners[reac_id]['uri'] = uri
                self.reactionners[reac_id]['last_connection'] = 0

            # First mix conf and override_conf to have our definitive conf
            for prop in self.override_conf:
                val = self.override_conf[prop]
                setattr(self.conf, prop, val)

            if self.conf.use_timezone != '':
                logger.debug("Setting our timezone to %s", str(self.conf.use_timezone))
                os.environ['TZ'] = self.conf.use_timezone
                time.tzset()

            if len(self.modules) != 0:
                logger.debug("I've got %s modules", str(self.modules))

            # TODO: if scheduler had previous modules instanciated it must clean them!
            self.modules_manager.set_modules(self.modules)
            self.do_load_modules()

            logger.info("Loading configuration.")
            self.conf.explode_global_conf()

            # we give sched it's conf
            self.sched.reset()
            self.sched.load_conf(self.conf)
            self.sched.load_satellites(self.pollers, self.reactionners)

            # We must update our Config dict macro with good value
            # from the config parameters
            self.sched.conf.fill_resource_macros_names_macros()
            # print "DBG: got macros", self.sched.conf.macros

            # Creating the Macroresolver Class & unique instance
            m_solver = MacroResolver()
            m_solver.init(self.conf)

            # self.conf.dump()
            # self.conf.quick_debug()

            # Now create the external commander
            # it's a applyer: it role is not to dispatch commands,
            # but to apply them
            ecm = ExternalCommandManager(self.conf, 'applyer')

            # Scheduler need to know about external command to
            # activate it if necessary
            self.sched.load_external_command(ecm)

            # External command need the sched because he can raise checks
            ecm.load_scheduler(self.sched)

            # We clear our schedulers managed (it's us :) )
            # and set ourself in it
            self.schedulers = {self.conf.instance_id: self.sched}

    def what_i_managed(self):
        """Get my managed dict (instance id and push_flavor)

        :return: dict containing instance_id key and push flavor value
        :rtype: dict
        """
        if hasattr(self, 'conf'):
            return {self.conf.instance_id: self.conf.push_flavor}
        else:
            return {}

    def main(self):
        """Main function for Scheduler, launch after the init::

        * Init daemon
        * Load module manager
        * Launch main loop
        * Catch any Exception that occurs

        :return: None
        """
        try:
            self.load_config_file()
            # Setting log level
            logger.setLevel(self.log_level)
            # Force the debug level if the daemon is said to start with such level
            if self.debug:
                logger.setLevel('DEBUG')

            self.look_for_early_exit()
            self.do_daemon_init_and_start()
            self.load_modules_manager()

            self.uri = self.http_daemon.uri
            logger.info("[scheduler] General interface is at: %s", self.uri)
            self.do_mainloop()
        except Exception, exp:
            self.print_unrecoverable(traceback.format_exc())
            raise
