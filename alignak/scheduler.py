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
#     aviau, alexandre.viau@savoirfairelinux.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Dessai.Imrane, dessai.imrane@gmail.com
#     Romain THERRAT, romain42@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Guillaume Bour, guillaume@bour.cc
#     Grégory Starck, g.starck@gmail.com
#     Thibault Cohen, titilambert@gmail.com
#     Christophe Simon, geektophe@gmail.com
#     andrewmcgilvray, a.mcgilvray@gmail.com
#     Pradeep Jindal, praddyjindal@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Andreas Paul, xorpaul@gmail.com
#     Samuel Milette-Lacombe, samuel.milette-lacombe@savoirfairelinux.com
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Arthur Gautier, superbaloo@superbaloo.net
#     Christophe SIMON, christophe.simon@dailymotion.com

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
"""This module provides Scheduler class.
It is used to schedule checks, create broks for monitoring event,
handle downtime, problems / acknowledgment etc.
The major part of monitoring "intelligence" is in this module.

"""
# pylint: disable=C0302
# pylint: disable=R0904
import time
import os
import cStringIO
import logging
import tempfile
import traceback
from Queue import Queue
from collections import defaultdict

from alignak.external_command import ExternalCommand
from alignak.check import Check
from alignak.notification import Notification
from alignak.eventhandler import EventHandler
from alignak.brok import Brok
from alignak.downtime import Downtime
from alignak.comment import Comment
from alignak.util import average_percentile
from alignak.load import Load
from alignak.http.client import HTTPClientException, HTTPClientConnectionException, \
    HTTPClientTimeoutException
from alignak.stats import statsmgr
from alignak.misc.common import DICT_MODATTR
from alignak.misc.serialization import unserialize, AlignakClassLookupException
from alignak.acknowledge import Acknowledge
from alignak.log import make_monitoring_log

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Scheduler(object):  # pylint: disable=R0902
    """Scheduler class. Mostly handle scheduling items (host service) to schedule check
    raise alert, enter downtime etc."""

    def __init__(self, scheduler_daemon):
        """
        :param scheduler_daemon: schedulerdaemon
        :type scheduler_daemon: alignak.daemons.schedulerdaemon.Alignak
        :return: None
        """
        self.sched_daemon = scheduler_daemon
        # When set to false by us, we die and arbiter launch a new Scheduler
        self.must_run = True

        # protect this unique list
        # The actions results returned by satelittes or fetched from
        # passive satellites are store in this queue
        self.waiting_results = Queue()  # satellites returns us results

        self.log_loop = 'TEST_LOG_LOOP' in os.environ

        # Every N seconds we call functions like consume, del zombies
        # etc. All of theses functions are in recurrent_works with the
        # every tick to run. So must be an integer > 0
        # The order is important, so make key an int.
        # TODO: at load, change value by configuration one (like reaper time, etc)
        self.recurrent_works = {
            0: ('update_downtimes_and_comments', self.update_downtimes_and_comments, 1),
            1: ('schedule', self.schedule, 1),  # just schedule
            2: ('check_freshness', self.check_freshness, 10),
            3: ('consume_results', self.consume_results, 1),  # incorporate checks and dependencies

            # now get the news actions (checks, notif) raised
            4: ('get_new_actions', self.get_new_actions, 1),
            5: ('scatter_master_notifications', self.scatter_master_notifications, 1),
            6: ('get_new_broks', self.get_new_broks, 1),  # and broks
            7: ('delete_zombie_checks', self.delete_zombie_checks, 1),
            8: ('delete_zombie_actions', self.delete_zombie_actions, 1),
            9: ('clean_caches', self.clean_caches, 1),
            10: ('update_retention_file', self.update_retention_file, 3600),
            11: ('check_orphaned', self.check_orphaned, 60),
            # For NagVis like tools: update our status every 10s
            12: ('get_and_register_update_program_status_brok',
                 self.get_and_register_update_program_status_brok, 10),
            # Check for system time change. And AFTER get new checks so they are changed too.
            13: ('check_for_system_time_change', self.sched_daemon.check_for_system_time_change, 1),
            # launch if need all internal checks
            14: ('manage_internal_checks', self.manage_internal_checks, 1),
            # clean some times possible overridden Queues, to do not explode in memory usage
            # every 1/4 of hour
            15: ('clean_queues', self.clean_queues, 1),
            # Look for new business_impact change by modulation every minute
            16: ('update_business_values', self.update_business_values, 60),
            # Reset the topology change flag if need
            17: ('reset_topology_change_flag', self.reset_topology_change_flag, 1),
            18: ('check_for_expire_acknowledge', self.check_for_expire_acknowledge, 1),
            19: ('send_broks_to_modules', self.send_broks_to_modules, 1),
            20: ('get_objects_from_from_queues', self.get_objects_from_from_queues, 1),
            # If change the number of get_latency_average_percentile in recurrent_works, change it
            # in the function get_latency_average_percentile()
            21: ('get_latency_average_percentile', self.get_latency_average_percentile, 10),
        }

        # stats part
        # Counters for the actions part: checks, event handlers and notifications
        # For each action type (check, event_handler or notification, store several counters:
        #  - the launched actions (launched), the actions that timed out (timeout) and the
        # actions that executed within the time (executed). For the correctly executed actions,
        # each action status has its own counter in the results dict: scheduled, done, ...
        # For each action type, the counters are replicated:
        #  - loop: for the current scheduling loop. The counters are reset on each loop end
        #  - total: since the scheduler start
        #  - active: the part of the total that are handled with active pollers/reactionners
        #  - passive: the part of the total that are handled with passive pollers/reactionners
        self.counters = {
            "check": {
                "total": {
                    "launched": 0, "timeout": 0, "executed": 0, "results": {"total": 0}
                },
                "loop": {
                    "launched": 0, "timeout": 0, "executed": 0, "results": {"total": 0}
                },
                "active": {
                    "launched": 0, "timeout": 0, "executed": 0, "results": {"total": 0}
                },
                "passive": {
                    "launched": 0, "timeout": 0, "executed": 0, "results": {"total": 0}
                },
            },
            "eventhandler": {
                "total": {
                    "launched": 0, "timeout": 0, "executed": 0, "results": {"total": 0}
                },
                "loop": {
                    "launched": 0, "timeout": 0, "executed": 0, "results": {"total": 0}
                },
                "active": {
                    "launched": 0, "timeout": 0, "executed": 0, "results": {"total": 0}
                },
                "passive": {
                    "launched": 0, "timeout": 0, "executed": 0, "results": {"total": 0}
                },
            },
            "notification": {
                "total": {
                    "launched": 0, "timeout": 0, "executed": 0, "results": {"total": 0}
                },
                "loop": {
                    "launched": 0, "timeout": 0, "executed": 0, "results": {"total": 0}
                },
                "active": {
                    "launched": 0, "timeout": 0, "executed": 0, "results": {"total": 0}
                },
                "passive": {
                    "launched": 0, "timeout": 0, "executed": 0, "results": {"total": 0}
                },
            }
        }
        self.nb_checks_launched = 0
        self.nb_checks_launched_passive = 0
        self.nb_actions_launched = 0
        self.nb_actions_launched_passive = 0

        self.nb_checks = 0
        self.nb_checks_total = 0
        self.nb_broks = 0
        self.nb_broks_total = 0
        self.nb_internal_checks = 0
        self.nb_internal_checks_total = 0
        self.nb_notifications = 0
        self.nb_notifications_total = 0
        self.nb_event_handlers = 0
        self.nb_event_handlers_total = 0
        self.nb_external_commands = 0
        self.nb_external_commands_total = 0

        # Checks results received
        self.nb_checks_results = 0
        self.nb_checks_results_timeout = 0
        self.nb_checks_results_passive = 0
        self.nb_actions_results = 0
        self.nb_actions_results_timeout = 0
        self.nb_actions_results_passive = 0

        # Dropped elements
        self.nb_checks_dropped = 0
        self.nb_broks_dropped = 0
        self.nb_actions_dropped = 0

        self.stats = {
            'latency': {
                'avg': 0.0,
                'min': 0.0,
                'max': 0.0
            }
        }

        # Temporary set. Will be updated with received configuration
        self.instance_id = 0

        # Ours queues
        self.checks = {}
        self.actions = {}

        # Our external commands manager
        self.external_commands_manager = None

        # Some flags
        self.has_full_broks = False  # have a initial_broks in broks queue?
        self.need_dump_memory = False  # set by signal 1
        self.need_objects_dump = False  # set by signal 2

        # And a dummy push flavor
        self.push_flavor = 0

        # Alignak instance name
        self.alignak_name = None

        # Now fake initialize for our satellites
        self.brokers = {}
        self.pollers = {}
        self.reactionners = {}

    def reset(self):
        # pylint: disable=not-context-manager
        """Reset scheduler::

        * Remove waiting results
        * Clear check, actions, broks lists

        :return: None
        """
        self.must_run = True
        # self.interrupted = False

        with self.waiting_results.mutex:  # pylint: disable=not-context-manager
            self.waiting_results.queue.clear()
        for obj in self.checks, self.actions, self.brokers:
            obj.clear()

    def iter_hosts_and_services(self):
        """Create an iterator for hosts and services

        :return: None
        """
        for what in (self.hosts, self.services):
            for elt in what:
                yield elt

    def load_conf(self, conf):
        """Load configuration received from Arbiter

        :param conf: configuration to load
        :type conf: alignak.objects.config.Config
        :return: None
        """
        self.program_start = int(time.time())
        self.conf = conf

        logger.debug("[%s] loading my configuration:", conf.instance_name)
        logger.debug("Properties:")
        for key in sorted(self.conf.properties):
            logger.debug("- %s: %s", key, getattr(self.conf, key, []))
        logger.debug("Macros:")
        for key in sorted(self.conf.macros):
            logger.debug("- %s: %s", key, getattr(self.conf.macros, key, []))
        logger.debug("Objects types:")
        for key in sorted(self.conf.types_creations):
            logger.debug("- %s: %s", key, getattr(self.conf.types_creations, key, []))

        self.hostgroups = conf.hostgroups
        self.services = conf.services
        # We need reversed list for search in the retention
        # file read
        self.services.optimize_service_search(conf.hosts)
        self.hosts = conf.hosts

        self.notificationways = conf.notificationways
        self.checkmodulations = conf.checkmodulations
        self.macromodulations = conf.macromodulations
        self.businessimpactmodulations = conf.businessimpactmodulations
        self.resultmodulations = conf.resultmodulations
        self.contacts = conf.contacts
        self.contactgroups = conf.contactgroups
        self.servicegroups = conf.servicegroups
        self.timeperiods = conf.timeperiods
        self.commands = conf.commands
        self.triggers = conf.triggers
        self.triggers.compile()
        self.triggers.load_objects(self)
        self.escalations = conf.escalations

        # Internal statistics
        statsmgr.gauge('configuration.hosts', len(self.hosts))
        statsmgr.gauge('configuration.services', len(self.services))
        statsmgr.gauge('configuration.hostgroups', len(self.hostgroups))
        statsmgr.gauge('configuration.servicegroups', len(self.servicegroups))
        statsmgr.gauge('configuration.contacts', len(self.contacts))
        statsmgr.gauge('configuration.contactgroups', len(self.contactgroups))
        statsmgr.gauge('configuration.timeperiods', len(self.timeperiods))
        statsmgr.gauge('configuration.commands', len(self.commands))
        statsmgr.gauge('configuration.notificationways', len(self.notificationways))
        statsmgr.gauge('configuration.escalations', len(self.escalations))

        # From the Arbiter configuration. Used for satellites to differentiate the schedulers
        self.instance_id = conf.uuid
        logger.info("Set my instance id as '%s'", self.instance_id)
        # Tag our hosts with our instance_id
        for host in self.hosts:
            host.instance_id = conf.instance_id
        for serv in self.services:
            serv.instance_id = conf.instance_id
        # self for instance_name
        self.instance_name = conf.instance_name
        # and push flavor
        self.push_flavor = conf.push_flavor
        # and Alignak instance name
        self.alignak_name = conf.alignak_name

        # Update our hosts/services freshness threshold
        if self.conf.check_host_freshness and self.conf.host_freshness_check_interval >= 0:
            for host in self.hosts:
                if host.freshness_threshold == -1:
                    host.freshness_threshold = self.conf.host_freshness_check_interval
            for service in self.services:
                if service.freshness_threshold == -1:
                    service.freshness_threshold = self.conf.service_freshness_check_interval

        # Now we can update our 'ticks' for special calls
        # like the retention one, etc
        self.update_recurrent_works_tick('update_retention_file',
                                         self.conf.retention_update_interval * 60)
        self.update_recurrent_works_tick('clean_queues', self.conf.cleaning_queues_interval)

    def update_recurrent_works_tick(self, f_name, new_tick):
        """Modify the tick value for a recurrent work
        A tick is an amount of loop of the scheduler before executing the recurrent work

        :param f_name: recurrent work name
        :type f_name: str
        :param new_tick: new value
        :type new_tick: str
        :return: None
        """
        for key in self.recurrent_works:
            (name, fun, _) = self.recurrent_works[key]
            if name == f_name:
                logger.debug("Changing the tick to %d for the function %s", new_tick, name)
                self.recurrent_works[key] = (name, fun, new_tick)

    def load_satellites(self, pollers, reactionners, brokers):
        """Setter for pollers, reactionners and brokers attributes

        :param pollers: pollers value to set
        :type pollers:
        :param reactionners: reactionners value to set
        :type reactionners:
        :param brokers: brokers value to set
        :type brokers:
        :return: None
        """
        self.pollers = pollers
        self.reactionners = reactionners
        for broker in brokers.values():
            self.brokers[broker['name']] = {'broks': {}, 'has_full_broks': False,
                                            'initialized': False}

    def die(self):
        """Set must_run attribute to False

        :return: None
        """
        logger.debug("Asking me to die...")
        self.must_run = False
        # self.sched_daemon.interrupted = True

    def dump_objects(self):
        """Dump scheduler objects into a dump (temp) file

        :return: None
        """
        temp_d = tempfile.gettempdir()
        path = os.path.join(temp_d, 'scheduler-obj-dump-%d' % time.time())
        logger.info('Opening the DUMP FILE %s', path)
        try:
            file_h = open(path, 'w')
            file_h.write('Scheduler DUMP at %d\n' % time.time())
            for chk in self.checks.values():
                string = 'CHECK: %s:%s:%s:%s:%s:%s\n' % \
                         (chk.uuid, chk.status, chk.t_to_go,
                          chk.poller_tag, chk.command, chk.worker_id)
                file_h.write(string)
            for act in self.actions.values():
                string = '%s: %s:%s:%s:%s:%s:%s\n' % \
                    (act.__class__.my_type.upper(), act.uuid, act.status,
                     act.t_to_go, act.reactionner_tag, act.command, act.worker_id)
                file_h.write(string)
            broks = {}
            for broker in self.brokers.values():
                for brok_uuid in broker['broks']:
                    broks[brok_uuid] = broker['broks'][brok_uuid]
            for brok in broks.values():
                string = 'BROK: %s:%s\n' % (brok.uuid, brok.type)
                file_h.write(string)
            file_h.close()
        except OSError as exp:  # pragma: no cover, should never happen...
            logger.critical("Error when writing the objects dump file %s : %s", path, str(exp))

    def dump_config(self):
        """Dump scheduler config into a dump (temp) file

        :return: None
        """
        temp_d = tempfile.gettempdir()
        path = os.path.join(temp_d, 'scheduler-conf-dump-%d' % time.time())
        logger.info('Opening the DUMP FILE %s', path)
        try:
            file_h = open(path, 'w')
            file_h.write('Scheduler config DUMP at %d\n' % time.time())
            self.conf.dump(file_h)
            file_h.close()
        except (OSError, IndexError) as exp:  # pragma: no cover, should never happen...
            logger.critical("Error when writing the config dump file %s : %s", path, str(exp))

    def set_external_commands_manager(self, ecm):
        """Setter for external_command_manager attribute

        :param ecm: new value
        :type ecm: alignak.external_command.ExternalCommandManager
        :return: None
        """
        self.external_commands_manager = ecm

    def run_external_commands(self, cmds):
        """Run external commands Arbiter/Receiver sent

        :param cmds: commands to run
        :type cmds: list
        :return: None
        """
        _t0 = time.time()
        logger.debug("Scheduler '%s' got %d commands", self.instance_name, len(cmds))
        for command in cmds:
            self.run_external_command(command)
        statsmgr.timer('core.run_external_commands', time.time() - _t0)

    def run_external_command(self, command):
        """Run a single external command

        :param command: command line to run
        :type command: str
        :return: None
        """
        logger.debug("Scheduler '%s' resolves command '%s'", self.instance_name, command)
        ext_cmd = ExternalCommand(command)
        self.external_commands_manager.resolve_command(ext_cmd)

    def add_brok(self, brok, bname=None):
        """Add a brok into brokers list
        It can be for a specific one, all brokers or none (startup)

        :param brok: brok to add
        :type brok: alignak.brok.Brok
        :param bname: broker name for the brok
        :type bname: str
        :return: None
        """
        # For brok, we TAG brok with our instance_id
        brok.instance_id = self.instance_id
        self.nb_broks += 1
        if bname:
            # it's just for one broker
            self.brokers[bname]['broks'][brok.uuid] = brok
        else:
            # add brok to all brokers
            for name in self.brokers:
                self.brokers[name]['broks'][brok.uuid] = brok

    def add_notification(self, notif):
        """Add a notification into actions list

        :param notif: notification to add
        :type notif: alignak.notification.Notification
        :return: None
        """
        if notif.uuid in self.actions:
            logger.debug("Already existing notification: %s", notif)
            return

        self.actions[notif.uuid] = notif
        self.nb_notifications += 1

        # A notification ask for a brok
        if notif.contact is not None:
            brok = notif.get_initial_status_brok()
            self.add(brok)

    def add_check(self, check):
        """Add a check into the scheduler checks list

        :param check: check to add
        :type check: alignak.check.Check
        :return: None
        """
        if check is None:
            return
        if check.uuid in self.checks:
            logger.debug("Already existing check: %s", check)
            return

        self.checks[check.uuid] = check

        self.nb_checks += 1

        # A new check means the host/service changes its next_check
        # need to be refreshed
        # TODO swich to uuid. Not working for simple id are we 1,2,3.. in host and services
        # Commented to fix #789
        brok = self.find_item_by_id(check.ref).get_next_schedule_brok()
        self.add(brok)

    def add_eventhandler(self, action):
        """Add a event handler into actions list

        :param action: event handler to add
        :type action: alignak.eventhandler.EventHandler
        :return: None
        """
        if action.uuid in self.actions:
            logger.debug("Already existing eventhandler: %s", action)
            return

        self.actions[action.uuid] = action
        self.nb_event_handlers += 1

    def add_externalcommand(self, ext_cmd):
        """Resolve external command

        :param ext_cmd: extermal command to run
        :type ext_cmd: alignak.external_command.ExternalCommand
        :return: None
        """
        self.external_commands_manager.resolve_command(ext_cmd)
        self.nb_external_commands += 1

    def add(self, elt):
        """Generic function to add objects into scheduler internal lists::

        Brok -> self.brokers
        Check -> self.checks
        Notification -> self.actions

        :param elt: element to add
        :type elt:
        :return: None
        """
        if elt is None:
            return
        logger.debug("Add: %s / %s", elt.my_type, elt.__dict__)
        fun = self.__add_actions.get(elt.__class__, None)
        if fun:
            fun(self, elt)
        else:
            logger.warning("self.add(): Unmanaged object class: %s (object=%r)", elt.__class__, elt)

    __add_actions = {
        Check:              add_check,
        Brok:               add_brok,
        Notification:       add_notification,
        EventHandler:       add_eventhandler,
        ExternalCommand:    add_externalcommand,
    }

    def hook_point(self, hook_name):
        """Generic function to call modules methods if such method is avalaible

        :param hook_name: function name to call
        :type hook_name: str
        :return:None
        TODO: find a way to merge this and the version in daemon.py
        """
        _t0 = time.time()
        for inst in self.sched_daemon.modules_manager.instances:
            full_hook_name = 'hook_' + hook_name
            logger.debug("hook_point: %s: %s %s",
                         inst.get_name(), str(hasattr(inst, full_hook_name)), hook_name)

            if hasattr(inst, full_hook_name):
                fun = getattr(inst, full_hook_name)
                try:
                    fun(self)
                # pylint: disable=W0703
                except Exception as exp:  # pragma: no cover, never happen during unit tests...
                    logger.error("The instance %s raise an exception %s."
                                 "I disable it and set it to restart it later",
                                 inst.get_name(), str(exp))
                    output = cStringIO.StringIO()
                    traceback.print_exc(file=output)
                    logger.error("Exception trace follows: %s", output.getvalue())
                    output.close()
                    self.sched_daemon.modules_manager.set_to_restart(inst)
        statsmgr.timer('core.hook.%s' % hook_name, time.time() - _t0)

    def clean_queues(self):
        """Reduces internal list size to max allowed

        * checks and broks : 5 * length of hosts + services
        * actions : 5 * length of hosts + services + contacts

        :return: None
        """
        # if we set the interval at 0, we bail out
        if self.conf.cleaning_queues_interval == 0:
            return

        max_checks = 5 * (len(self.hosts) + len(self.services))
        max_broks = 5 * (len(self.hosts) + len(self.services))
        max_actions = 5 * len(self.contacts) * (len(self.hosts) + len(self.services))

        # For checks, it's not very simple:
        # For checks, they may be referred to their host/service
        # We do not just del them in the check list, but also in their service/host
        # We want id of lower than max_id - 2*max_checks
        self.nb_checks_dropped = 0
        if len(self.checks) > max_checks:
            # keys does not ensure sorted keys. Max is slow but we have no other way.
            to_del_checks = [c for c in self.checks.values()]
            to_del_checks.sort(key=lambda x: x.creation_time)
            to_del_checks = to_del_checks[:-max_checks]
            self.nb_checks_dropped = len(to_del_checks)
            if to_del_checks:
                logger.warning("I have to drop some checks (%d)..., sorry :(",
                               self.nb_checks_dropped)
            for chk in to_del_checks:
                c_id = chk.uuid
                items = getattr(self, chk.ref_type + 's')
                elt = items[chk.ref]
                # First remove the link in host/service
                elt.remove_in_progress_check(chk)
                # Then in dependent checks (I depend on, or check
                # depend on me)
                for dependent_checks in chk.depend_on_me:
                    dependent_checks.depend_on.remove(chk.uuid)
                for c_temp in chk.depend_on:
                    c_temp.depend_on_me.remove(chk)
                del self.checks[c_id]  # Final Bye bye ...

        # For broks and actions, it's more simple
        # or broks, manage global but also all brokers
        self.nb_broks_dropped = 0
        for broker in self.brokers.values():
            if len(broker['broks']) > max_broks:
                logger.warning("I have to drop some broks (%d)..., sorry :(", len(broker['broks']))
                to_del_broks = [c for c in broker['broks'].values()]
                to_del_broks.sort(key=lambda x: x.creation_time)
                to_del_broks = to_del_broks[:-max_broks]
                self.nb_broks_dropped = len(to_del_broks)
                for brok in to_del_broks:
                    del broker['broks'][brok.uuid]

        self.nb_actions_dropped = 0
        if len(self.actions) > max_actions:
            logger.warning("I have to del some actions (currently: %d, max: %d)..., sorry :(",
                           len(self.actions), max_actions)
            to_del_actions = [c for c in self.actions.values()]
            to_del_actions.sort(key=lambda x: x.creation_time)
            to_del_actions = to_del_actions[:-max_actions]
            self.nb_actions_dropped = len(to_del_actions)
            for act in to_del_actions:
                if act.is_a == 'notification':
                    self.find_item_by_id(act.ref).remove_in_progress_notification(act)
                del self.actions[act.uuid]

    def clean_caches(self):
        """Clean timperiods caches

        :return: None
        """
        for timeperiod in self.timeperiods:
            timeperiod.clean_cache()

    def get_and_register_status_brok(self, item):
        """Get a update status brok for item and add it

        :param item: item to get brok from
        :type item: alignak.objects.item.Item
        :return: None
        """
        brok = item.get_update_status_brok()
        self.add(brok)

    def get_and_register_check_result_brok(self, item):
        """Get a check result brok for item and add it

        :param item: item to get brok from
        :type item: alignak.objects.schedulingitem.SchedulingItem
        :return: None
        """
        brok = item.get_check_result_brok()
        self.add(brok)

    def check_for_expire_acknowledge(self):
        """Iter over host and service and check if any acknowledgement has expired

        :return: None
        """
        for elt in self.iter_hosts_and_services():
            elt.check_for_expire_acknowledge()

    def update_business_values(self):
        """Iter over host and service and update business_impact

        :return: None
        """
        for elt in self.iter_hosts_and_services():
            if not elt.is_problem:
                was = elt.business_impact
                elt.update_business_impact_value(self.hosts, self.services,
                                                 self.timeperiods, self.businessimpactmodulations)
                new = elt.business_impact
                # Ok, the business_impact change, we can update the broks
                if new != was:
                    self.get_and_register_status_brok(elt)

        # When all impacts and classic elements are updated,
        # we can update problems (their value depend on impacts, so
        # they must be done after)
        for elt in self.iter_hosts_and_services():
            # We first update impacts and classic elements
            if elt.is_problem:
                was = elt.business_impact
                elt.update_business_impact_value(self.hosts, self.services,
                                                 self.timeperiods, self.businessimpactmodulations)
                new = elt.business_impact
                # Maybe one of the impacts change it's business_impact to a high value
                # and so ask for the problem to raise too
                if new != was:
                    self.get_and_register_status_brok(elt)

    def scatter_master_notifications(self):
        """Generate children notifications from master notifications
        Also update notification number
        Master notification are not launched by reactionners, only children ones

        :return: None
        """
        now = time.time()
        for act in self.actions.values():
            # We only want notifications
            if act.is_a != 'notification':
                continue
            if act.status == 'scheduled' and act.is_launchable(now):
                logger.debug("Scheduler got a master notification: %s", repr(act))
                if not act.contact:
                    logger.debug("No contact for this notification")
                    # This is a "master" notification created by create_notifications.
                    # It wont sent itself because it has no contact.
                    # We use it to create "child" notifications (for the contacts and
                    # notification_commands) which are executed in the reactionner.
                    item = self.find_item_by_id(act.ref)
                    childnotifs = []
                    notif_period = self.timeperiods.items.get(item.notification_period, None)
                    if not item.notification_is_blocked_by_item(notif_period, self.hosts,
                                                                self.services, act.type,
                                                                t_wished=now):
                        # If it is possible to send notifications
                        # of this type at the current time, then create
                        # a single notification for each contact of this item.
                        childnotifs = item.scatter_notification(
                            act, self.contacts, self.notificationways, self.timeperiods,
                            self.macromodulations, self.escalations,
                            self.find_item_by_id(getattr(item, "host", None))
                        )
                        for notif in childnotifs:
                            logger.debug(" - child notification: %s", notif)
                            notif.status = 'scheduled'
                            self.add(notif)  # this will send a brok

                    # If we have notification_interval then schedule
                    # the next notification (problems only)
                    if act.type == 'PROBLEM':
                        # Update the ref notif number after raise the one of the notification
                        if childnotifs:
                            # notif_nb of the master notification
                            # was already current_notification_number+1.
                            # If notifications were sent,
                            # then host/service-counter will also be incremented
                            item.current_notification_number = act.notif_nb

                        if item.notification_interval != 0 and act.t_to_go is not None:
                            # We must continue to send notifications.
                            # Just leave it in the actions list and set it to "scheduled"
                            # and it will be found again later
                            # Ask the service/host to compute the next notif time. It can be just
                            # a.t_to_go + item.notification_interval*item.__class__.interval_length
                            # or maybe before because we have an
                            # escalation that need to raise up before
                            act.t_to_go = item.get_next_notification_time(act, self.escalations,
                                                                          self.timeperiods)

                            act.notif_nb = item.current_notification_number + 1
                            logger.debug("Repeat master notification: %s", str(act))
                            act.status = 'scheduled'
                        else:
                            # Wipe out this master notification. One problem notification is enough.
                            item.remove_in_progress_notification(act)
                            logger.debug("Remove master notification (no repeat): %s", str(act))
                            act.status = 'zombie'

                    else:
                        # Wipe out this master notification.
                        logger.debug("Remove master notification (no repeat): %s", str(act))
                        # We don't repeat recover/downtime/flap/etc...
                        item.remove_in_progress_notification(act)
                        act.status = 'zombie'

    def get_to_run_checks(self, do_checks=False, do_actions=False,
                          poller_tags=None, reactionner_tags=None,
                          worker_name='none', module_types=None):
        """Get actions/checks for reactionner/poller

        Can get checks and actions (notifications and co)

        Called by the poller to get checks and by the reactionner to get actions

        :param do_checks: do we get checks ?
        :type do_checks: bool
        :param do_actions: do we get actions ?
        :type do_actions: bool
        :param poller_tags: poller tags to filter
        :type poller_tags: list
        :param reactionner_tags: reactionner tags to filter
        :type reactionner_tags: list
        :param worker_name: worker name to fill check/action (to remember it)
        :type worker_name: str
        :param module_types: module type to filter
        :type module_types: list
        :return: Check/Action list with poller/reactionner tags matching and module type matching
        :rtype: list
        """
        res = []
        now = time.time()

        if poller_tags is None:
            poller_tags = ['None']
        if reactionner_tags is None:
            reactionner_tags = ['None']
        if module_types is None:
            module_types = ['fork']

        # If a poller wants its checks
        if do_checks:
            logger.debug("%d checks for poller tags: %s and module types: %s",
                         len(self.checks), poller_tags, module_types)
            for chk in self.checks.values():
                logger.debug("Check: %s (%s / %s)", chk.uuid, chk.poller_tag, chk.module_type)
                #  If the command is untagged, and the poller too, or if both are tagged
                #  with same name, go for it
                # if do_check, call for poller, and so poller_tags by default is ['None']
                # by default poller_tag is 'None' and poller_tags is ['None']
                # and same for module_type, the default is the 'fork' type
                if chk.poller_tag not in poller_tags:
                    logger.debug(" -> poller tag do not match")
                    continue
                if chk.module_type not in module_types:
                    logger.debug(" -> module type do not match")
                    continue

                logger.debug(" -> : %s %s (%s)",
                             'worker' if not chk.internal else 'internal',
                             chk.status,
                             'now' if chk.is_launchable(now) else 'not yet')
                # must be ok to launch, and not an internal one (business rules based)
                if chk.status == 'scheduled' and chk.is_launchable(now) and not chk.internal:
                    logger.debug("Check to run: %s", chk)
                    chk.status = 'inpoller'
                    chk.worker_id = worker_name
                    res.append(chk)

                    self.nb_checks_launched += 1

                    self.counters["check"]["total"]["launched"] += 1
                    self.counters["check"]["loop"]["launched"] += 1
                    self.counters["check"]["active"]["launched"] += 1

            if res:
                logger.debug("-> %d checks to start now", len(res))
            else:
                logger.debug("-> no checks to start now")

        # If a reactionner wants its actions
        if do_actions:
            logger.debug("%d actions for reactionner tags: %s", len(self.actions), reactionner_tags)
            for act in self.actions.values():
                is_master = (act.is_a == 'notification' and not act.contact)
                logger.debug("Action: %s (%s / %s)", act.uuid, act.reactionner_tag, act.module_type)

                if not is_master:
                    # if do_action, call the reactionner,
                    # and so reactionner_tags by default is ['None']
                    # by default reactionner_tag is 'None' and reactionner_tags is ['None'] too
                    # So if not the good one, loop for next :)
                    if act.reactionner_tag not in reactionner_tags:
                        logger.error(" -> reactionner tag do not match")
                        continue

                    # same for module_type
                    if act.module_type not in module_types:
                        logger.error(" -> module type do not match")
                        continue

                # And now look if we can launch or not :)
                logger.debug(" -> : worker %s (%s)",
                             act.status, 'now' if act.is_launchable(now) else 'not yet')
                if act.status == 'scheduled' and act.is_launchable(now):
                    if not is_master:
                        # This is for child notifications and eventhandlers
                        act.status = 'inpoller'
                        act.worker_id = worker_name
                        res.append(act)

                        self.nb_actions_launched += 1

                        self.counters[act.is_a]["total"]["launched"] += 1
                        self.counters[act.is_a]["loop"]["launched"] += 1
                        self.counters[act.is_a]["active"]["launched"] += 1

            if res:
                logger.info("-> %d actions to start now", len(res))
            else:
                logger.debug("-> no actions to start now")

        return res

    def put_results(self, action):  # pylint: disable=too-many-branches,too-many-statements
        """Get result from pollers/reactionners (actives ones)

        :param action: check / action / eventhandler to handle
        :type action:
        :return: None
        """
        logger.debug('put_results: %s ', action)
        if action.is_a == 'notification':
            try:
                _ = self.actions[action.uuid]
            except KeyError as exp:  # pragma: no cover, simple protection
                # Cannot find notification - drop it
                logger.warning('put_results:: get unknown notification : %s ', str(exp))
                return

            # We will only see childnotifications here
            try:
                timeout = False
                if action.status == 'timeout':
                    # Unfortunately the remove_in_progress_notification
                    # sets the status to zombie, so we need to save it here.
                    timeout = True
                    execution_time = action.execution_time

                # Add protection for strange charset
                if isinstance(action.output, str):
                    action.output = action.output.decode('utf8', 'ignore')

                self.actions[action.uuid].get_return_from(action)
                item = self.find_item_by_id(self.actions[action.uuid].ref)
                item.remove_in_progress_notification(action)
                self.actions[action.uuid].status = 'zombie'
                item.last_notification = action.check_time

                # And we ask the item to update it's state
                self.get_and_register_status_brok(item)

                self.counters[action.is_a]["total"]["results"]["total"] += 1
                if action.status not in \
                        self.counters[action.is_a]["total"]["results"]:
                    self.counters[action.is_a]["total"]["results"][action.status] = 0
                self.counters[action.is_a]["total"]["results"][action.status] += 1

                self.counters[action.is_a]["loop"]["results"]["total"] += 1
                if action.status not in \
                        self.counters[action.is_a]["loop"]["results"]:
                    self.counters[action.is_a]["loop"]["results"][action.status] = 0
                self.counters[action.is_a]["loop"]["results"][action.status] += 1

                # If we' ve got a problem with the notification, raise a Warning log
                if timeout:
                    contact = self.find_item_by_id(self.actions[action.uuid].contact)
                    item = self.find_item_by_id(self.actions[action.uuid].ref)

                    self.nb_actions_results_timeout += 1
                    self.counters[action.is_a]["total"]["timeout"] += 1
                    self.counters[action.is_a]["loop"]["timeout"] += 1

                    logger.warning("Contact %s %s notification command '%s ' "
                                   "timed out after %d seconds",
                                   contact.contact_name,
                                   item.my_type,
                                   self.actions[action.uuid].command,
                                   int(execution_time))
                else:
                    self.nb_actions_results += 1
                    self.counters[action.is_a]["total"]["executed"] += 1
                    self.counters[action.is_a]["loop"]["executed"] += 1

                    if action.exit_status != 0:
                        logger.warning("The notification command '%s' raised an error "
                                       "(exit code=%d): '%s'",
                                       action.command, action.exit_status, action.output)

            except AttributeError as exp:  # pragma: no cover, simple protection
                # bad object, drop it
                logger.warning('put_results:: get bad notification : %s ', str(exp))
        elif action.is_a == 'check':
            try:
                self.checks[action.uuid]
            except KeyError as exp:  # pragma: no cover, simple protection
                # Cannot find check - drop it
                logger.warning('put_results:: get unknown check : %s ', str(exp))
                return

            try:
                self.counters[action.is_a]["total"]["results"]["total"] += 1
                if action.status not in \
                        self.counters[action.is_a]["total"]["results"]:
                    self.counters[action.is_a]["total"]["results"][action.status] = 0
                self.counters[action.is_a]["total"]["results"][action.status] += 1

                self.counters[action.is_a]["loop"]["results"]["total"] += 1
                if action.status not in \
                        self.counters[action.is_a]["loop"]["results"]:
                    self.counters[action.is_a]["loop"]["results"][action.status] = 0
                self.counters[action.is_a]["loop"]["results"][action.status] += 1

                if action.status == 'timeout':
                    ref = self.find_item_by_id(self.checks[action.uuid].ref)
                    action.output = "(%s %s check timed out)" % (
                        ref.my_type, ref.get_full_name()
                    )  # pylint: disable=E1101
                    action.long_output = action.output
                    action.exit_status = self.conf.timeout_exit_status

                    self.nb_checks_results_timeout += 1
                    self.counters[action.is_a]["total"]["timeout"] += 1
                    self.counters[action.is_a]["loop"]["timeout"] += 1

                    logger.warning("Timeout raised for '%s' (check command for the %s '%s'), "
                                   "check status code: %d, execution time: %d seconds",
                                   action.command, ref.my_type, ref.get_full_name(),
                                   action.exit_status, int(action.execution_time))
                else:
                    self.nb_checks_results += 1
                    self.counters[action.is_a]["total"]["executed"] += 1
                    self.counters[action.is_a]["loop"]["executed"] += 1

                self.checks[action.uuid].get_return_from(action)
                self.checks[action.uuid].status = 'waitconsume'
            except ValueError as exp:  # pragma: no cover, simple protection
                # bad object, drop it
                logger.warning('put_results:: get bad check: %s ', str(exp))

        elif action.is_a == 'eventhandler':
            try:
                old_action = self.actions[action.uuid]
                old_action.status = 'zombie'
            except KeyError as exp:  # pragma: no cover, simple protection
                # cannot find old action
                # bad object, drop it
                logger.warning('put_results:: get bad check: %s ', str(exp))
                return

            self.counters[action.is_a]["total"]["results"]["total"] += 1
            if action.status not in \
                    self.counters[action.is_a]["total"]["results"]:
                self.counters[action.is_a]["total"]["results"][action.status] = 0
            self.counters[action.is_a]["total"]["results"][action.status] += 1

            self.counters[action.is_a]["loop"]["results"]["total"] += 1
            if action.status not in \
                    self.counters[action.is_a]["loop"]["results"]:
                self.counters[action.is_a]["loop"]["results"][action.status] = 0
            self.counters[action.is_a]["loop"]["results"][action.status] += 1

            if action.status == 'timeout':
                _type = 'event handler'
                if action.is_snapshot:
                    _type = 'snapshot'
                ref = self.find_item_by_id(self.checks[action.uuid].ref)
                logger.info("%s %s command '%s' timed out after %d seconds",
                            ref.__class__.my_type.capitalize(),  # pylint: disable=E1101
                            _type, self.actions[action.uuid].command, int(action.execution_time))

                self.nb_checks_results_timeout += 1
                self.counters[action.is_a]["total"]["timeout"] += 1
                self.counters[action.is_a]["loop"]["timeout"] += 1
            else:
                self.nb_checks_results += 1
                self.counters[action.is_a]["total"]["executed"] += 1
                self.counters[action.is_a]["loop"]["executed"] += 1

            # If it's a snapshot we should get the output and export it
            if action.is_snapshot:
                old_action.get_return_from(action)
                s_item = self.find_item_by_id(old_action.ref)
                brok = s_item.get_snapshot_brok(old_action.output, old_action.exit_status)
                self.add(brok)
        else:  # pragma: no cover, simple protection, should not happen!
            logger.error("The received result type in unknown! %s", str(action.is_a))

    def push_actions_to_passives_satellites(self):
        """Send actions/checks to passive poller/reactionners

        :return: None
        """
        # We loop for our passive pollers or reactionners
        for satellites in [self.pollers, self.reactionners]:
            s_type = 'poller'
            if satellites is self.reactionners:
                s_type = 'reactionner'

            for link in [p for p in satellites.values() if p['passive']]:
                logger.debug("Try to send actions to the %s '%s'", s_type, link['name'])

                if link['con'] is None:
                    if not self.sched_daemon.daemon_connection_init(link['instance_id'],
                                                                    s_type=s_type):
                        if link['connection_attempt'] <= link['max_failed_connections']:
                            logger.warning("The connection for the %s '%s' cannot be established, "
                                           "it is not possible to get actions for this %s.",
                                           s_type, link['name'], s_type)
                        else:
                            logger.error("The connection for the %s '%s' cannot be established, "
                                         "it is not possible to get actions for this %s.",
                                         s_type, link['name'], s_type)
                        continue

                # Get actions to execute
                lst = []
                if s_type == 'poller':
                    lst = self.get_to_run_checks(do_checks=True, do_actions=False,
                                                 poller_tags=link['poller_tags'],
                                                 worker_name=link['name'])
                elif s_type == 'reactionner':
                    lst = self.get_to_run_checks(do_checks=False, do_actions=True,
                                                 reactionner_tags=link['reactionner_tags'],
                                                 worker_name=link['name'])
                if not lst:
                    logger.debug("Nothing to do...")
                    continue

                try:
                    logger.info("Sending %d actions to the %s '%s'", len(lst), s_type, link['name'])
                    link['con'].post('push_actions', {'actions': lst, 'sched_id': self.instance_id})
                    if s_type == 'poller':
                        self.nb_checks_launched += len(lst)
                        self.nb_checks_launched_passive += len(lst)
                    if s_type == 'reactionner':
                        self.nb_actions_launched += len(lst)
                        self.nb_actions_launched_passive += len(lst)
                except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
                    logger.warning("Connection error with the %s '%s' when pushing actions: %s",
                                   s_type, link['name'], str(exp))
                    link['con'] = None
                except HTTPClientTimeoutException as exp:
                    logger.warning("Connection timeout with the %s '%s' when pushing actions: %s",
                                   s_type, link['name'], str(exp))
                    link['con'] = None
                except HTTPClientException as exp:  # pragma: no cover, simple protection
                    logger.error("Connection error with the %s '%s' when pushing actions: %s",
                                 s_type, link['name'], str(exp))
                    link['con'] = None
                except KeyError as exp:  # pragma: no cover, simple protection
                    logger.warning("push_actions: The %s '%s' is not initialized: %s",
                                   s_type, link['name'], str(exp))
                    link['con'] = None

    def get_actions_from_passives_satellites(self):
        #  pylint: disable=W0703
        """Get actions/checks results from passive poller/reactionners

        :return: None
        """
        # We loop for our passive pollers or reactionners
        for satellites in [self.pollers, self.reactionners]:
            s_type = 'poller'
            if satellites is self.reactionners:
                s_type = 'reactionner'

            for link in [p for p in satellites.values() if p['passive']]:
                logger.debug("Try to get results from the %s '%s'", s_type, link['name'])

                if link['con'] is None:
                    if not self.sched_daemon.daemon_connection_init(link['instance_id'],
                                                                    s_type=s_type):
                        if link['connection_attempt'] <= link['max_failed_connections']:
                            logger.warning("The connection for the %s '%s' cannot be established, "
                                           "it is not possible to get results for this %s.",
                                           s_type, link['name'], s_type)
                        else:
                            logger.error("The connection for the %s '%s' cannot be established, "
                                         "it is not possible to get results for this %s.",
                                         s_type, link['name'], s_type)
                        continue

                try:
                    results = link['con'].get('get_returns', {'sched_id': self.instance_id},
                                              wait='long')
                    if results:
                        who_sent = link['name']
                        logger.debug("Got some results: %d results from %s", len(results), who_sent)
                    else:
                        logger.debug("-> no passive results from %s", link['name'])
                        continue

                    results = unserialize(results, no_load=True)
                    if results:
                        logger.info("Received %d passive results from %s",
                                    len(results), link['name'])
                    self.nb_checks_results += len(results)

                    for result in results:
                        logger.debug("-> result: %s", result)
                        result.set_type_passive()

                        # Update scheduler counters
                        self.counters[result.is_a]["total"]["results"]["total"] += 1
                        if result.status not in self.counters[result.is_a]["total"]["results"]:
                            self.counters[result.is_a]["total"]["results"][result.status] = 0
                        self.counters[result.is_a]["total"]["results"][result.status] += 1
                        self.counters[result.is_a]["active"]["results"]["total"] += 1
                        if result.status not in self.counters[result.is_a]["active"]["results"]:
                            self.counters[result.is_a]["active"]["results"][result.status] = 0
                        self.counters[result.is_a]["active"]["results"][result.status] += 1

                        # Append to the scheduler result queue
                        self.waiting_results.put(result)
                except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
                    logger.warning("Connection error with the %s '%s' when pushing results: %s",
                                   s_type, link['name'], str(exp))
                    link['con'] = None
                except HTTPClientTimeoutException as exp:
                    logger.warning("Connection timeout with the %s '%s' when pushing results: %s",
                                   s_type, link['name'], str(exp))
                    link['con'] = None
                except HTTPClientException as exp:  # pragma: no cover, simple protection
                    logger.error("Error with the %s '%s' when pushing results: %s",
                                 s_type, link['name'], str(exp))
                    link['con'] = None
                except KeyError as exp:  # pragma: no cover, simple protection
                    logger.warning("get_actions: The %s '%s' is not initialized: %s",
                                   s_type, link['name'], str(exp))
                    link['con'] = None
                except AlignakClassLookupException as exp:  # pragma: no cover, simple protection
                    logger.error('Cannot un-serialize passive results from satellite %s : %s',
                                 link['name'], exp)
                except Exception as exp:  # pragma: no cover, simple protection
                    logger.error('Cannot load passive results from satellite %s : %s',
                                 link['name'], str(exp))
                    logger.exception(exp)

    def manage_internal_checks(self):
        """Run internal checks

        :return: None
        """
        now = time.time()
        for chk in self.checks.values():
            # must be ok to launch, and not an internal one (business rules based)
            if chk.internal and chk.status == 'scheduled' and chk.is_launchable(now):
                self.nb_internal_checks += 1
                self.counters["check"]["total"]["results"]["total"] += 1
                if "internal" not in self.counters["check"]["total"]["results"]:
                    self.counters["check"]["total"]["results"]["internal"] = 0
                self.counters["check"]["total"]["results"]["internal"] += 1

                self.counters["check"]["loop"]["results"]["total"] += 1
                if "internal" not in self.counters["check"]["loop"]["results"]:
                    self.counters["check"]["loop"]["results"]["internal"] = 0
                self.counters["check"]["loop"]["results"]["internal"] += 1

                item = self.find_item_by_id(chk.ref)
                # Only if active checks are enabled
                if item.active_checks_enabled:
                    item.manage_internal_check(self.hosts, self.services, chk, self.hostgroups,
                                               self.servicegroups, self.macromodulations,
                                               self.timeperiods)
                # it manage it, now just ask to consume it
                # like for all checks
                chk.status = 'waitconsume'

    def get_broks(self, bname):
        """Send broks to a specific broker

        :param bname: broker name to send broks
        :type bname: str
        :greturn: dict of brok for this broker
        :rtype: dict[alignak.brok.Brok]
        """
        to_send = [b for b in self.brokers[bname]['broks'].values()
                   if getattr(b, 'sent_to_sched_externals', False)]

        res = {}
        for brok in to_send:
            res[brok.uuid] = brok
            del self.brokers[bname]['broks'][brok.uuid]
        return res

    def reset_topology_change_flag(self):
        """Set topology_change attribute to False in all hosts and services

        :return: None
        """
        for i in self.hosts:
            i.topology_change = False
        for i in self.services:
            i.topology_change = False

    def update_retention_file(self, forced=False):
        """Call hook point 'save_retention'.
        Retention modules will write back retention (to file, db etc)

        :param forced: if update forced?
        :type forced: bool
        :return: None
        """
        # If we set the update to 0, we do not want of this
        # if we do not forced (like at stopping)
        if self.conf.retention_update_interval == 0 and not forced:
            return

        self.hook_point('save_retention')

    def retention_load(self):
        """Call hook point 'load_retention'.
        Retention modules will read retention (from file, db etc)

        :return: None
        """
        self.hook_point('load_retention')

    def get_retention_data(self):  # pylint: disable=R0912,too-many-statements
        """Get all host and service data in order to store it after
        The module is in charge of that

        :return: dict containing host and service data
        :rtype: dict
        """
        brok = make_monitoring_log('INFO', 'RETENTION SAVE: %s' % self.instance_name)
        self.add(brok)
        # We create an all_data dict with list of useful retention data dicts
        # of our hosts and services
        all_data = {'hosts': {}, 'services': {}}
        for host in self.hosts:
            h_dict = {}
            running_properties = host.__class__.running_properties
            for prop, entry in running_properties.items():
                if entry.retention:
                    val = getattr(host, prop)
                    # Maybe we should "prepare" the data before saving it
                    # like get only names instead of the whole objects
                    fun = entry.retention_preparation
                    if fun:
                        val = fun(host, val)
                    h_dict[prop] = val
            # and some properties are also like this, like
            # active checks enabled or not
            properties = host.__class__.properties
            for prop, entry in properties.items():
                if entry.retention:
                    val = getattr(host, prop)
                    # Maybe we should "prepare" the data before saving it
                    # like get only names instead of the whole objects
                    fun = entry.retention_preparation
                    if fun:
                        val = fun(host, val)
                    h_dict[prop] = val
            # manage special properties: the Notifications
            if 'notifications_in_progress' in h_dict and h_dict['notifications_in_progress'] != {}:
                notifs = {}
                for notif_uuid, notification in h_dict['notifications_in_progress'].iteritems():
                    notifs[notif_uuid] = notification.serialize()
                h_dict['notifications_in_progress'] = notifs
            # manage special properties: the downtimes
            downtimes = []
            if 'downtimes' in h_dict and h_dict['downtimes'] != {}:
                for downtime in h_dict['downtimes'].values():
                    downtimes.append(downtime.serialize())
            h_dict['downtimes'] = downtimes
            # manage special properties: the acknowledges
            if 'acknowledgement' in h_dict and h_dict['acknowledgement'] is not None:
                h_dict['acknowledgement'] = h_dict['acknowledgement'].serialize()
            # manage special properties: the comments
            comments = []
            if 'comments' in h_dict and h_dict['comments'] != {}:
                for comment in h_dict['comments'].values():
                    comments.append(comment.serialize())
            h_dict['comments'] = comments
            # manage special properties: the notified_contacts
            if 'notified_contacts' in h_dict and h_dict['notified_contacts'] != []:
                ncontacts = []
                for contact_uuid in h_dict['notified_contacts']:
                    ncontacts.append(self.contacts[contact_uuid].get_name())
                h_dict['notified_contacts'] = ncontacts
            all_data['hosts'][host.host_name] = h_dict
        logger.info('%d hosts sent to retention', len(all_data['hosts']))

        # Same for services
        for serv in self.services:
            s_dict = {}
            running_properties = serv.__class__.running_properties
            for prop, entry in running_properties.items():
                if entry.retention:
                    val = getattr(serv, prop)
                    # Maybe we should "prepare" the data before saving it
                    # like get only names instead of the whole objects
                    fun = entry.retention_preparation
                    if fun:
                        val = fun(serv, val)
                    s_dict[prop] = val

            # We consider the service ONLY if it has modified attributes.
            # If not, then no non-running attributes will be saved for this service.
            if serv.modified_attributes > 0:
                # Same for properties, like active checks enabled or not
                properties = serv.__class__.properties

                for prop, entry in properties.items():
                    # We save the value only if the attribute
                    # is selected for retention AND has been modified.
                    if entry.retention and \
                            not (prop in DICT_MODATTR and
                                 not DICT_MODATTR[prop].value & serv.modified_attributes):
                        val = getattr(serv, prop)
                        # Maybe we should "prepare" the data before saving it
                        # like get only names instead of the whole objects
                        fun = entry.retention_preparation
                        if fun:
                            val = fun(serv, val)
                        s_dict[prop] = val
            # manage special properties: the notifications
            if 'notifications_in_progress' in s_dict and s_dict['notifications_in_progress'] != {}:
                notifs = {}
                for notif_uuid, notification in s_dict['notifications_in_progress'].iteritems():
                    notifs[notif_uuid] = notification.serialize()
                s_dict['notifications_in_progress'] = notifs
            # manage special properties: the downtimes
            downtimes = []
            if 'downtimes' in s_dict and s_dict['downtimes'] != {}:
                for downtime in s_dict['downtimes'].values():
                    downtimes.append(downtime.serialize())
            s_dict['downtimes'] = downtimes
            # manage special properties: the acknowledges
            if 'acknowledgement' in s_dict and s_dict['acknowledgement'] is not None:
                s_dict['acknowledgement'] = s_dict['acknowledgement'].serialize()
            # manage special properties: the comments
            comments = []
            if 'comments' in s_dict and s_dict['comments'] != {}:
                for comment in s_dict['comments'].values():
                    comments.append(comment.serialize())
            s_dict['comments'] = comments
            # manage special properties: the notified_contacts
            if 'notified_contacts' in s_dict and s_dict['notified_contacts'] != []:
                ncontacts = []
                for contact_uuid in s_dict['notified_contacts']:
                    ncontacts.append(self.contacts[contact_uuid].get_name())
                s_dict['notified_contacts'] = ncontacts
            all_data['services'][(serv.host_name, serv.service_description)] = s_dict
        logger.info('%d services sent to retention', len(all_data['services']))

        return all_data

    def restore_retention_data(self, data):
        """Restore retention data

        Data coming from retention will override data coming from configuration
        It is kinda confusing when you modify an attribute (external command) and it get saved
        by retention

        :param data: data from retention
        :type data: dict
        :return: None
        """
        brok = make_monitoring_log('INFO', 'RETENTION LOAD: %s' % self.instance_name)
        self.add(brok)

        ret_hosts = data['hosts']
        for ret_h_name in ret_hosts:
            # We take the dict of our value to load
            host = self.hosts.find_by_name(ret_h_name)
            if host is not None:
                self.restore_retention_data_item(data['hosts'][ret_h_name], host)
        statsmgr.gauge('retention.hosts', len(ret_hosts))
        logger.info('%d hosts restored from retention', len(ret_hosts))

        # Same for services
        ret_services = data['services']
        for (ret_s_h_name, ret_s_desc) in ret_services:
            # We take our dict to load
            s_dict = data['services'][(ret_s_h_name, ret_s_desc)]
            serv = self.services.find_srv_by_name_and_hostname(ret_s_h_name, ret_s_desc)

            if serv is not None:
                self.restore_retention_data_item(s_dict, serv)
        statsmgr.gauge('retention.services', len(ret_services))
        logger.info('%d services restored from retention', len(ret_services))

    def restore_retention_data_item(self, data, item):
        """
        restore data in item

        :param data: retention data of the item
        :type data: dict
        :param item: host or service item
        :type item: alignak.objects.host.Host | alignak.objects.service.Service
        :return: None
        """
        # First manage all running properties
        running_properties = item.__class__.running_properties
        for prop, entry in running_properties.items():
            if entry.retention:
                # Maybe the saved one was not with this value, so
                # we just bypass this
                if prop in data and prop not in ['downtimes', 'comments']:
                    setattr(item, prop, data[prop])
        # Ok, some are in properties too (like active check enabled
        # or not. Will OVERRIDE THE CONFIGURATION VALUE!
        properties = item.__class__.properties
        for prop, entry in properties.items():
            if entry.retention:
                # Maybe the saved one was not with this value, so
                # we just bypass this
                if prop in data:
                    setattr(item, prop, data[prop])
        # Now manage all linked objects load from/ previous run
        for notif_uuid, notif in item.notifications_in_progress.iteritems():
            notif['ref'] = item.uuid
            mynotif = Notification(params=notif)
            self.add(mynotif)
            item.notifications_in_progress[notif_uuid] = mynotif
        item.update_in_checking()
        # And also add downtimes and comments
        for down in data['downtimes']:
            if down['uuid'] not in item.downtimes:
                down['ref'] = item.uuid
                # case comment_id has comment dict instead uuid
                if 'uuid' in down['comment_id']:
                    data['comments'].append(down['comment_id'])
                    down['comment_id'] = down['comment_id']['uuid']
                item.add_downtime(Downtime(down))
        if item.acknowledgement is not None:
            item.acknowledgement = Acknowledge(item.acknowledgement)
            item.acknowledgement.ref = item.uuid
        # Relink the notified_contacts as a set() of true contacts objects
        # if it was loaded from the retention, it's now a list of contacts
        # names
        for comm in data['comments']:
            comm['ref'] = item.uuid
            item.add_comment(Comment(comm))
        new_notified_contacts = set()
        for cname in item.notified_contacts:
            comm = self.contacts.find_by_name(cname)
            # Maybe the contact is gone. Skip it
            if comm is not None:
                new_notified_contacts.add(comm.uuid)
        item.notified_contacts = new_notified_contacts

    def fill_initial_broks(self, bname, with_logs=False):
        """Create initial broks for a specific broker

        :param bname: broker name
        :type bname: str
        :param with_logs: tell if we write a log line for hosts/services
               initial states
        :type with_logs: bool
        :return: None
        """
        # First a Brok for delete all from my instance_id
        brok = Brok({'type': 'clean_all_my_instance_id', 'data': {'instance_id': self.instance_id}})
        self.add_brok(brok, bname)

        # first the program status
        brok = self.get_program_status_brok()
        self.add_brok(brok, bname)

        #  We can't call initial_status from all this types
        #  The order is important, service need host...
        initial_status_types = (self.timeperiods, self.commands,
                                self.contacts, self.contactgroups,
                                self.hosts, self.hostgroups,
                                self.services, self.servicegroups)

        self.conf.skip_initial_broks = getattr(self.conf, 'skip_initial_broks', False)
        logger.debug("Skipping initial broks? %s", str(self.conf.skip_initial_broks))
        if not self.conf.skip_initial_broks:
            for tab in initial_status_types:
                for item in tab:
                    if hasattr(item, 'members'):
                        member_items = getattr(self, item.my_type.replace("group", "s"))
                        brok = item.get_initial_status_brok(member_items)
                    else:
                        brok = item.get_initial_status_brok()
                    self.add_brok(brok, bname)

        # Only raises the all logs at the scheduler startup
        if with_logs:
            # Ask for INITIAL logs for services and hosts
            for item in self.hosts:
                item.raise_initial_state()
            for item in self.services:
                item.raise_initial_state()

        # Add a brok to say that we finished all initial_pass
        brok = Brok({'type': 'initial_broks_done', 'data': {'instance_id': self.instance_id}})
        self.add_brok(brok, bname)

        # We now have all full broks
        self.has_full_broks = True

        logger.info("[%s] Created %d initial Broks for broker %s",
                    self.instance_name, len(self.brokers[bname]['broks']), bname)
        self.brokers[bname]['initialized'] = True
        self.send_broks_to_modules()

    def get_and_register_program_status_brok(self):
        """Create and add a program_status brok

        :return: None
        """
        brok = self.get_program_status_brok()
        self.add(brok)

    def get_and_register_update_program_status_brok(self):
        """Create and add a update_program_status brok

        :return: None
        """
        brok = self.get_program_status_brok()
        brok.type = 'update_program_status'
        self.add(brok)

    def get_program_status_brok(self):
        """Create a program status brok

        :return: Brok with program status data
        :rtype: alignak.brok.Brok
        TODO: GET REAL VALUES
        """
        now = int(time.time())
        # todo: some information in this brok are unuseful: last_log_rotation, command_file
        # Some others are unaccurate: last_command_check, modified_host_attributes,
        # modified_service_attributes
        # I do not remove yet because some modules may use them?
        data = {
            "is_running": 1,
            "instance_id": self.instance_id,
            "alignak_name": self.alignak_name,
            "instance_name": self.instance_name,
            "last_alive": now,
            "interval_length": self.conf.interval_length,
            "program_start": self.program_start,
            "pid": os.getpid(),
            "daemon_mode": 1,
            "last_command_check": now,
            "last_log_rotation": now,
            "notifications_enabled": self.conf.enable_notifications,
            "active_service_checks_enabled": self.conf.execute_service_checks,
            "passive_service_checks_enabled": self.conf.accept_passive_service_checks,
            "active_host_checks_enabled": self.conf.execute_host_checks,
            "passive_host_checks_enabled": self.conf.accept_passive_host_checks,
            "event_handlers_enabled": self.conf.enable_event_handlers,
            "flap_detection_enabled": self.conf.enable_flap_detection,
            "failure_prediction_enabled": 0,
            "process_performance_data": self.conf.process_performance_data,
            "obsess_over_hosts": self.conf.obsess_over_hosts,
            "obsess_over_services": self.conf.obsess_over_services,
            "modified_host_attributes": 0,
            "modified_service_attributes": 0,
            "global_host_event_handler": self.conf.global_host_event_handler.get_name()
            if self.conf.global_host_event_handler else '',
            'global_service_event_handler': self.conf.global_service_event_handler.get_name()
            if self.conf.global_service_event_handler else '',

            # Flapping
            "enable_flap_detection": self.conf.enable_flap_detection,
            "flap_history": self.conf.flap_history,
            "low_host_flap_threshold": self.conf.low_host_flap_threshold,
            "low_service_flap_threshold": self.conf.low_service_flap_threshold,
            "high_host_flap_threshold": self.conf.high_host_flap_threshold,
            "high_service_flap_threshold": self.conf.high_service_flap_threshold,

            # Stats
            "statsd_enabled": self.conf.statsd_enabled,
            "statsd_host": self.conf.statsd_host,
            "statsd_port": self.conf.statsd_port,
            "statsd_prefix": self.conf.statsd_prefix,
        }
        logger.debug("Program status brok data: %s", data)
        brok = Brok({'type': 'program_status', 'data': data})
        return brok

    def consume_results(self):
        """Handle results waiting in waiting_results list.
        Check ref will call consume result and update their status

        :return: None
        """
        # All results are in self.waiting_results
        # We need to get them first
        queue_size = self.waiting_results.qsize()
        for _ in xrange(queue_size):
            self.put_results(self.waiting_results.get())

        # Then we consume them
        for chk in self.checks.values():
            if chk.status == 'waitconsume':
                item = self.find_item_by_id(chk.ref)

                notif_period = self.timeperiods.items.get(item.notification_period, None)
                depchks = item.consume_result(chk, notif_period, self.hosts, self.services,
                                              self.timeperiods, self.macromodulations,
                                              self.checkmodulations, self.businessimpactmodulations,
                                              self.resultmodulations, self.triggers, self.checks)

                for dep in depchks:
                    self.add(dep)

                if self.conf.log_active_checks and not chk.passive_check:
                    item.raise_check_result()

        # loop to resolve dependencies
        have_resolved_checks = True
        while have_resolved_checks:
            have_resolved_checks = False
            # All 'finished' checks (no more dep) raise checks they depend on
            for chk in self.checks.values():
                if chk.status == 'havetoresolvedep':
                    for dependent_checks in chk.depend_on_me:
                        # Ok, now dependent will no more wait
                        dependent_checks.depend_on.remove(chk.uuid)
                        have_resolved_checks = True
                    # REMOVE OLD DEP CHECK -> zombie
                    chk.status = 'zombie'

            # Now, reinteger dep checks
            for chk in self.checks.values():
                if chk.status == 'waitdep' and not chk.depend_on:
                    item = self.find_item_by_id(chk.ref)
                    notif_period = self.timeperiods.items.get(item.notification_period, None)
                    depchks = item.consume_result(chk, notif_period, self.hosts, self.services,
                                                  self.timeperiods, self.macromodulations,
                                                  self.checkmodulations,
                                                  self.businessimpactmodulations,
                                                  self.resultmodulations, self.triggers,
                                                  self.checks)
                    for dep in depchks:
                        self.add(dep)

    def delete_zombie_checks(self):
        """Remove checks that have a zombie status (usually timeouts)

        :return: None
        """
        id_to_del = []
        for chk in self.checks.values():
            if chk.status == 'zombie':
                id_to_del.append(chk.uuid)
        # une petite tape dans le dos et tu t'en vas, merci...
        # *pat pat* GFTO, thks :)
        for c_id in id_to_del:
            del self.checks[c_id]  # ZANKUSEN!

    def delete_zombie_actions(self):
        """Remove actions that have a zombie status (usually timeouts)

        :return: None
        """
        id_to_del = []
        for act in self.actions.values():
            if act.status == 'zombie':
                id_to_del.append(act.uuid)
        # une petite tape dans le dos et tu t'en vas, merci...
        # *pat pat* GFTO, thks :)
        for a_id in id_to_del:
            del self.actions[a_id]  # ZANKUSEN!

    def update_downtimes_and_comments(self):
        """Iter over all hosts and services::

        TODO: add some unit tests for the maintenance period feature.

        * Update downtime status (start / stop) regarding maintenance period
        * Register new comments in comments list

        :return: None
        """
        broks = []
        now = time.time()

        # Check maintenance periods
        for elt in self.iter_hosts_and_services():
            if elt.maintenance_period == '':
                continue

            if elt.in_maintenance == -1:
                timeperiod = self.timeperiods[elt.maintenance_period]
                if timeperiod.is_time_valid(now):
                    start_dt = timeperiod.get_next_valid_time_from_t(now)
                    end_dt = timeperiod.get_next_invalid_time_from_t(start_dt + 1) - 1
                    data = {'ref': elt.uuid, 'ref_type': elt.my_type, 'start_time': start_dt,
                            'end_time': end_dt, 'fixed': 1, 'trigger_id': '',
                            'duration': 0, 'author': "Alignak",
                            'comment': "This downtime was automatically scheduled by Alignak "
                                       "because of a maintenance period."}
                    downtime = Downtime(data)
                    self.add(downtime.add_automatic_comment(elt))
                    elt.add_downtime(downtime)
                    self.add(downtime)
                    self.get_and_register_status_brok(elt)
                    elt.in_maintenance = downtime.uuid
            else:
                if elt.in_maintenance not in elt.downtimes:
                    # the main downtimes has expired or was manually deleted
                    elt.in_maintenance = -1

        #  Check the validity of contact downtimes
        for elt in self.contacts:
            for downtime_id in elt.downtimes:
                downtime = elt.downtimes[downtime_id]
                downtime.check_activation(self.contacts)

        # A loop where those downtimes are removed
        # which were marked for deletion (mostly by dt.exit())
        for elt in self.iter_hosts_and_services():
            for downtime in elt.downtimes.values():
                if downtime.can_be_deleted is True:
                    logger.info("Downtime to delete: %s", downtime.__dict__)
                    ref = self.find_item_by_id(downtime.ref)
                    elt.del_downtime(downtime.uuid)
                    broks.append(ref.get_update_status_brok())

        # Same for contact downtimes:
        for elt in self.contacts:
            for downtime in elt.downtimes.values():
                if downtime.can_be_deleted is True:
                    ref = self.find_item_by_id(downtime.ref)
                    elt.del_downtime(downtime.uuid)
                    broks.append(ref.get_update_status_brok())

        # Check start and stop times
        for elt in self.iter_hosts_and_services():
            for downtime in elt.downtimes.values():
                if downtime.real_end_time < now:
                    # this one has expired
                    broks.extend(downtime.exit(self.timeperiods, self.hosts, self.services))
                elif now >= downtime.start_time and downtime.fixed and not downtime.is_in_effect:
                    # this one has to start now
                    broks.extend(downtime.enter(self.timeperiods, self.hosts, self.services))
                    broks.append(self.find_item_by_id(downtime.ref).get_update_status_brok())

        for brok in broks:
            self.add(brok)

    def schedule(self, elems=None):
        """Iter over all hosts and services and call schedule method
        (schedule next check)

        :param elems: None or list of host / services to schedule
        :type elems: None | list
        :return: None
        """
        if not elems:
            elems = self.iter_hosts_and_services()

        # ask for service and hosts their next check
        for elt in elems:
            logger.debug("Add check for: %s", elt)
            self.add_check(elt.schedule(self.hosts, self.services, self.timeperiods,
                                        self.macromodulations, self.checkmodulations, self.checks))

    def get_new_actions(self):
        """Call 'get_new_actions' hook point
        Iter over all hosts and services to add new actions in internal lists

        :return: None
        """
        self.hook_point('get_new_actions')
        # ask for service and hosts their next check
        for elt in self.iter_hosts_and_services():
            for act in elt.actions:
                logger.debug("Got a new action for %s: %s", elt, act)
                self.add(act)
            # We take all, we can clear it
            elt.actions = []

    def get_new_broks(self):
        """Iter over all hosts and services to add new broks in internal lists

        :return: None
        """
        # ask for service and hosts their broks waiting
        # be eaten
        for elt in self.iter_hosts_and_services():
            for brok in elt.broks:
                self.add(brok)
            # We take all, we can clear it
            elt.broks = []

        # Also fetch broks from contact (like contactdowntime)
        for contact in self.contacts:
            for brok in contact.broks:
                self.add(brok)
            contact.broks = []

    def check_freshness(self):
        """
        Iter over all hosts and services to check freshness if check_freshness enabled and
        passive_checks_enabled are set

        :return: None
        """
        items = []
        if self.conf.check_host_freshness:
            # Freshness check configured for hosts
            items.extend(self.hosts)
        if self.conf.check_service_freshness:
            # Freshness check configured for services
            items.extend(self.services)

        for elt in items:
            if elt.check_freshness and elt.passive_checks_enabled:
                chk = elt.do_check_freshness(self.hosts, self.services, self.timeperiods,
                                             self.macromodulations, self.checkmodulations,
                                             self.checks)
                if chk is not None:
                    self.add(chk)
                    self.waiting_results.put(chk)

    def check_orphaned(self):
        """Check for orphaned checks/actions::

        * status == 'inpoller' and t_to_go < now - time_to_orphanage (300 by default)

        if so raise a warning log.

        :return: None
        """
        orphans_count = {}
        now = int(time.time())
        for chk in self.checks.values():
            if chk.status == 'inpoller':
                time_to_orphanage = self.find_item_by_id(chk.ref).get_time_to_orphanage()
                if time_to_orphanage:
                    if chk.t_to_go < now - time_to_orphanage:
                        logger.info("Orphaned check (%d s / %s / %s) check for: %s (%s)",
                                    time_to_orphanage, chk.t_to_go, now,
                                    self.find_item_by_id(chk.ref).get_full_name(), chk)
                        chk.status = 'scheduled'
                        if chk.worker_id not in orphans_count:
                            orphans_count[chk.worker_id] = 0
                        orphans_count[chk.worker_id] += 1
        for act in self.actions.values():
            if act.status == 'inpoller':
                time_to_orphanage = self.find_item_by_id(act.ref).get_time_to_orphanage()
                if time_to_orphanage:
                    if act.t_to_go < now - time_to_orphanage:
                        logger.info("Orphaned action (%d s / %s / %s) action for: %s (%s)",
                                    time_to_orphanage, act.t_to_go, now,
                                    self.find_item_by_id(act.ref).get_full_name(), act)
                        act.status = 'scheduled'
                        if act.worker_id not in orphans_count:
                            orphans_count[act.worker_id] = 0
                        orphans_count[act.worker_id] += 1

        for sta_name in orphans_count:
            logger.warning("%d actions never came back for the satellite '%s'. "
                           "I reenable them for polling.",
                           orphans_count[sta_name], sta_name)

    def send_broks_to_modules(self):
        """Put broks into module queues
        Only broks without sent_to_sched_externals to True are sent
        Only modules that ask for broks will get some

        :return: None
        """
        t00 = time.time()
        nb_sent = 0
        broks = {}
        for broker in self.brokers.values():
            for brok in broker['broks'].values():
                if not getattr(brok, 'sent_to_sched_externals', False):
                    broks[brok.uuid] = brok

        for mod in self.sched_daemon.modules_manager.get_external_instances():
            logger.debug("Look for sending to module %s", mod.get_name())
            queue = mod.to_q
            if queue is not None:
                to_send = [b for b in broks.values() if mod.want_brok(b)]
                queue.put(to_send)
                nb_sent += len(to_send)

        # No more need to send them
        for brok in broks.values():
            for broker in self.brokers.values():
                if brok.uuid in broker['broks']:
                    broker['broks'][brok.uuid].sent_to_sched_externals = True
        logger.debug("Time to send %s broks (after %d secs)", nb_sent, time.time() - t00)

    def get_objects_from_from_queues(self):
        """Same behavior than Daemon.get_objects_from_from_queues().

        :return:
        :rtype:
        """
        return self.sched_daemon.get_objects_from_from_queues()

    def get_latency_average_percentile(self):
        """
        Get a overview of the latencies with just a 95 percentile + min/max values

        :return: None
        """
        (_, _, time_interval) = self.recurrent_works[21]
        last_time = time.time() - time_interval
        latencies = [s.latency for s in self.services if s.last_chk > last_time]
        lat_avg, lat_min, lat_max = average_percentile(latencies)
        if lat_avg is not None:
            self.stats['latency']['avg'] = lat_avg
            self.stats['latency']['min'] = lat_min
            self.stats['latency']['max'] = lat_max
            logger.debug("Latency (avg/min/max): %.2f/%.2f/%.2f", lat_avg, lat_min, lat_max)

    def get_checks_status_counts(self, checks=None):
        """ Compute the counts of the different checks status and
        return it as a defaultdict(int) with the keys being the different
        statutes and the value being the count of the checks in that status.

        :checks: None or the checks you want to count their statuses.
                 If None then self.checks is used.

        :param checks: NoneType | dict
        :type checks: None | dict
        :return:
        :rtype: defaultdict(int)
        """
        if checks is None:
            checks = self.checks

        res = defaultdict(int)
        res["total"] = len(checks)
        for chk in checks.itervalues():
            res[chk.status] += 1
        return res

    def find_item_by_id(self, o_id):
        """Get item based on its id or uuid

        :param o_id:
        :type o_id: int | str
        :return:
        :rtype: alignak.objects.item.Item | None
        """
        # TODO: Use uuid instead of id, because all obj have the same id (1,2,3)
        # TODO: Ensure minimal list of objects in chain.
        if not o_id:
            return None

        # Temporary fix. To remove when all obj have uuids
        if not isinstance(o_id, int) and not isinstance(o_id, basestring):
            return o_id

        for items in [self.hosts, self.services, self.actions, self.checks, self.hostgroups,
                      self.servicegroups, self.contacts, self.contactgroups]:
            if o_id in items:
                return items[o_id]

        raise Exception("Item with id %s not found" % o_id)  # pragma: no cover,
        # simple protection this should never happen

    def get_stats_struct(self):  # pragma: no cover, seems never called!
        """Get state of modules and create a scheme for stats data of daemon

        TODO: confirm this method is useful because it is never called during the tests!

        :return: A dict with the following structure
        ::

           { 'metrics': ['scheduler.%s.checks.%s %d %d', 'scheduler.%s.%s.queue %d %d',
                         'scheduler.%s.%s %d %d', 'scheduler.%s.latency.min %f %d',
                         'scheduler.%s.latency.avg %f %d', 'scheduler.%s.latency.max %f %d'],
             'version': VERSION,
             'name': instance_name,
             'type': 'scheduler',
             'modules': [
                         {'internal': {'name': "MYMODULE1", 'state': 'ok'},
                         {'external': {'name': "MYMODULE2", 'state': 'stopped'},
                        ]
             'latency':  {'avg': lat_avg, 'min': lat_min, 'max': lat_max}
             'host': len(self.hosts),
             'services': len(self.services),
             'commands': [{'cmd': c, 'u_time': u_time, 's_time': s_time}, ...] (10 first)
           }

        :rtype: dict
        """
        now = int(time.time())

        res = self.sched_daemon.get_stats_struct()
        res.update({'name': self.instance_name, 'type': 'scheduler'})

        res['latency'] = self.stats['latency']

        res['hosts'] = len(self.hosts)
        res['services'] = len(self.services)
        # metrics specific
        metrics = res['metrics']

        checks_status_counts = self.get_checks_status_counts()

        for status in ('scheduled', 'inpoller', 'zombie'):
            metrics.append('scheduler.%s.checks.%s %d %d' % (
                self.instance_name,
                status,
                checks_status_counts[status],
                now))

        for what in ('actions', 'broks'):
            metrics.append('scheduler.%s.%s.queue %d %d' % (
                self.instance_name, what, len(getattr(self, what)), now))

        metrics.append('scheduler.%s.latency.min %f %d' % (self.instance_name,
                                                           res['latency']['min'], now))
        metrics.append('scheduler.%s.latency.avg %f %d' % (self.instance_name,
                                                           res['latency']['avg'], now))
        metrics.append('scheduler.%s.latency.max %f %d' % (self.instance_name,
                                                           res['latency']['max'], now))

        all_commands = {}
        # compute some stats
        for elt in self.iter_hosts_and_services():
            last_cmd = elt.last_check_command
            if not last_cmd:
                continue
            interval = elt.check_interval
            if interval == 0:
                interval = 1
            cmd = os.path.split(last_cmd.split(' ', 1)[0])[1]
            u_time = elt.u_time
            s_time = elt.s_time
            old_u_time, old_s_time = all_commands.get(cmd, (0.0, 0.0))
            old_u_time += u_time / interval
            old_s_time += s_time / interval
            all_commands[cmd] = (old_u_time, old_s_time)
        # now sort it
        stats = []
        for (cmd, elem) in all_commands.iteritems():
            u_time, s_time = elem
            stats.append({'cmd': cmd, 'u_time': u_time, 's_time': s_time})

        def p_sort(e01, e02):
            """Compare elems by u_time param

            :param e01: first elem to compare
            :param e02: second elem to compare
            :return: 1 if e01['u_time'] > e02['u_time'], -1 if e01['u_time'] < e02['u_time'], else 0
            """
            if e01['u_time'] > e02['u_time']:
                return 1
            if e01['u_time'] < e02['u_time']:
                return -1
            return 0
        stats.sort(p_sort)
        # take the first 10 ones for the put
        res['commands'] = stats[:10]
        return res

    def run(self):  # pylint: disable=too-many-locals, too-many-statements, too-many-branches
        """Main scheduler function::

        * Load retention
        * Call 'pre_scheduler_mod_start' hook point
        * Start modules
        * Schedule first checks
        * Init connection with pollers/reactionners
        * Run main loop

            * Do recurrent works
            * Push/Get actions to passive satellites
            * Update stats
            * Call 'scheduler_tick' hook point

        * Save retention (on quit)

        :return: None
        """
        # Then we see if we've got info in the retention file
        self.retention_load()

        # Finally start the external modules now we got our data
        self.hook_point('pre_scheduler_mod_start')
        self.sched_daemon.modules_manager.start_external_instances(late_start=True)

        # Ok, now all is initialized, we can make the initial broks
        logger.info("[%s] First scheduling launched", self.instance_name)
        _t1 = time.time()
        # Program start brok
        self.get_and_register_program_status_brok()
        # First scheduling
        self.schedule()
        statsmgr.timer('first_scheduling', time.time() - _t1)
        logger.info("[%s] First scheduling done", self.instance_name)

        # Now connect to the passive satellites if needed
        for s_id in self.pollers:
            if not self.pollers[s_id]['passive']:
                continue
            self.sched_daemon.daemon_connection_init(s_id, 'poller')

        for s_id in self.reactionners:
            if not self.reactionners[s_id]['passive']:
                continue
            self.sched_daemon.daemon_connection_init(s_id, 'reactionner')

        # Ticks are for recurrent function call like consume, del zombies etc
        ticks = 0

        # Increased on each loop turn
        loop_count = 0
        # Last loop duration
        loop_duration = 0
        # For the scheduler pause duration
        pause_duration = 0.5
        logger.info("Scheduler pause duration: %.2f", pause_duration)
        # For the scheduler maximum expected loop duration
        maximum_loop_duration = 1.0
        logger.info("Scheduler maximum expected loop duration: %.2f", maximum_loop_duration)

        # Scheduler start timestamp
        sch_start_ts = time.time()
        elapsed_time = 0

        # We must reset it if we received a new conf from the Arbiter.
        # Otherwise, the stat check average won't be correct

        # Actions and checks counters
        self.nb_checks_total = 0
        self.nb_checks_launched = 0
        self.nb_checks_launched_passive = 0

        self.nb_actions_total = 0
        self.nb_actions_launched = 0
        self.nb_actions_launched_passive = 0

        self.nb_checks_results_total = 0
        self.nb_checks_results = 0
        self.nb_checks_results_passive = 0

        self.nb_actions_results_total = 0
        self.nb_actions_results = 0
        self.nb_actions_results_passive = 0
        self.nb_checks_dropped = 0

        # Broks, notifications, ... counters
        self.nb_broks_total = 0
        self.nb_broks = 0
        self.nb_internal_checks = 0
        self.nb_internal_checks_total = 0
        self.nb_notifications_total = 0
        self.nb_notifications = 0
        self.nb_event_handlers_total = 0
        self.nb_event_handlers = 0
        self.nb_external_commands_total = 0
        self.nb_external_commands = 0

        self.load_one_min = Load(initial_value=1)
        logger.info("[%s] starting scheduler loop: %.2f", self.instance_name, sch_start_ts)
        while self.must_run:
            # Scheduler load
            # fixme: measuring the scheduler load with this method is a non-sense ...
            # self.load_one_min.update_load(self.sched_daemon.sleep_time)
            # load = min(100, 100.0 - self.load_one_min.get_load() * 100)
            # logger.info("Load: (sleep) %.2f (average: %.2f) -> %d%%",
            #             self.sched_daemon.sleep_time, self.load_one_min.get_load(), load)
            # statsmgr.gauge('load.sleep', self.sched_daemon.sleep_time)
            # statsmgr.gauge('load.average', self.load_one_min.get_load())
            # statsmgr.gauge('load.load', load)

            # Increment loop count
            loop_count += 1
            if self.log_loop:
                logger.debug("--- %d", loop_count)

            # Increment ticks count
            ticks += 1

            loop_start_ts = time.time()
            # Do recurrent works like schedule, consume, delete_zombie_checks
            for i in self.recurrent_works:
                (name, fun, nb_ticks) = self.recurrent_works[i]
                # A 0 in the tick will just disable it
                if nb_ticks != 0:
                    if ticks % nb_ticks == 0:
                        # Call it and save the time spend in it
                        _t0 = time.time()
                        fun()
                        statsmgr.timer('loop.recurrent.%s' % name, time.time() - _t0)
            statsmgr.timer('loop.recurrent', time.time() - loop_start_ts)

            _ts = time.time()
            self.push_actions_to_passives_satellites()
            statsmgr.timer('loop.push_actions_to_passives_satellites', time.time() - _ts)
            _ts = time.time()
            self.get_actions_from_passives_satellites()
            statsmgr.timer('loop.get_actions_from_passives_satellites', time.time() - _ts)

            # Scheduler statistics
            # - broks / notifications counters
            if self.log_loop:
                logger.debug("Items (loop): broks: %d, notifications: %d, checks: %d, internal "
                             "checks: %d, event handlers: %d, external commands: %d",
                             self.nb_broks, self.nb_notifications, self.nb_checks,
                             self.nb_internal_checks, self.nb_event_handlers,
                             self.nb_external_commands)
            statsmgr.gauge('checks', self.nb_checks)
            statsmgr.gauge('broks', self.nb_broks)
            statsmgr.gauge('internal_checks', self.nb_internal_checks)
            statsmgr.gauge('notifications', self.nb_notifications)
            statsmgr.gauge('event_handlers', self.nb_event_handlers)
            statsmgr.gauge('external_commands', self.nb_external_commands)
            self.nb_checks_total += self.nb_checks
            self.nb_broks_total += self.nb_broks
            self.nb_internal_checks_total += self.nb_internal_checks
            self.nb_notifications_total += self.nb_notifications
            self.nb_event_handlers_total += self.nb_event_handlers
            self.nb_external_commands_total += self.nb_external_commands
            if self.log_loop:
                logger.debug("Items (total): broks: %d, notifications: %d, checks: %d, internal "
                             "checks: %d, event handlers: %d, external commands: %d",
                             self.nb_broks_total, self.nb_notifications_total, self.nb_checks_total,
                             self.nb_internal_checks_total, self.nb_event_handlers_total,
                             self.nb_external_commands_total)
            # Reset on each loop
            # self.nb_checks = 0 not yet for this one!
            self.nb_broks = 0
            self.nb_internal_checks = 0
            self.nb_notifications = 0
            self.nb_event_handlers = 0
            self.nb_external_commands = 0

            # - checks / actions counters
            for action_type in self.counters:
                for action_group in ['total', 'active', 'passive', 'loop']:
                    # Actions launched
                    statsmgr.gauge('actions.%s.%s.launched'
                                   % (action_type, action_group),
                                   self.counters[action_type][action_group]["launched"])
                    # Actions timed out
                    statsmgr.gauge('actions.%s.%s.timeout'
                                   % (action_type, action_group),
                                   self.counters[action_type][action_group]["timeout"])
                    # Actions executed within time
                    statsmgr.gauge('actions.%s.%s.executed'
                                   % (action_type, action_group),
                                   self.counters[action_type][action_group]["executed"])

                    # Reset loop counters
                    if action_group == 'loop' and self.log_loop:
                        logger.debug("Actions '%s/%s': launched: %d, timeout: %d, executed: %d",
                                     action_type, action_group,
                                     self.counters[action_type][action_group]["launched"],
                                     self.counters[action_type][action_group]["timeout"],
                                     self.counters[action_type][action_group]["executed"])

                        self.counters[action_type][action_group]["launched"] = 0
                        self.counters[action_type][action_group]["timeout"] = 0
                        self.counters[action_type][action_group]["executed"] = 0

                    # Reset loop counters
                    if action_group == 'total' and self.log_loop:
                        logger.debug("Actions '%s/%s': launched: %d, timeout: %d, executed: %d",
                                     action_type, action_group,
                                     self.counters[action_type][action_group]["launched"],
                                     self.counters[action_type][action_group]["timeout"],
                                     self.counters[action_type][action_group]["executed"])

                    # Actions results
                    dump_result = "Results '%s/%s': " % (action_type, action_group)
                    for result in self.counters[action_type][action_group]["results"]:
                        my_result = self.counters[action_type][action_group]["results"][result]
                        statsmgr.gauge('actions.%s.%s.result.%s'
                                       % (action_type, action_group, result), my_result)
                        dump_result += "%s: %d, " % (result, my_result)
                    if action_group in ['loop', 'total'] and self.log_loop:
                        logger.debug(dump_result)

            # - current state - this should perharps be removed because the checks status got
            # already pushed to the stats with the previous treatment?
            checks_status = defaultdict(int)
            checks_status["total"] = len(self.checks)
            for chk in self.checks.itervalues():
                checks_status[chk.status] += 1
            dump_result = "Checks count (loop): "
            for status, count in checks_status.iteritems():
                dump_result += "%s: %d, " % (status, count)
                statsmgr.gauge('checks.%s' % status, count)
            if self.log_loop:
                logger.debug(dump_result)

            if self.need_dump_memory:
                _ts = time.time()
                logger.debug('I must dump my memory...')
                self.sched_daemon.dump_memory()
                self.need_dump_memory = False
                statsmgr.timer('loop.memory_dump', time.time() - _ts)

            if self.need_objects_dump:
                _ts = time.time()
                logger.debug('I must dump my objects...')
                self.dump_objects()
                self.dump_config()
                self.need_objects_dump = False
                statsmgr.timer('loop.objects_dump', time.time() - _ts)

            _ts = time.time()
            self.hook_point('scheduler_tick')
            statsmgr.timer('loop.hook-tick', time.time() - _ts)

            loop_end_ts = time.time()
            loop_duration = loop_end_ts - loop_start_ts

            pause = maximum_loop_duration - loop_duration
            if loop_duration > maximum_loop_duration:
                logger.warning("The scheduler loop exceeded the maximum expected loop "
                               "duration: %.2f. The last loop needed %.2f seconds to execute. "
                               "You should update your configuration to reduce the load on "
                               "this scheduler.", maximum_loop_duration, loop_duration)
                # Make a very very short pause ...
                pause = 0.1

            # Pause the scheduler execution to avoid too much load on the system
            logger.debug("Before pause: sleep time: %s", pause)
            work, time_changed = self.sched_daemon.make_a_pause(pause)
            logger.debug("After pause: %.2f / %.2f, sleep time: %.2f",
                         work, time_changed, self.sched_daemon.sleep_time)
            if work > pause_duration:
                logger.warning("Too much work during the pause (%.2f out of %.2f)! "
                               "The scheduler should rest for a while... but one need to change "
                               "its code for this. Please log an issue in the project repository;",
                               work, pause_duration)
                pause_duration += 0.1
            self.sched_daemon.sleep_time = 0.0

            # And now, the whole average time spent
            elapsed_time = loop_end_ts - sch_start_ts
            if self.log_loop:
                logger.debug("Elapsed time, current loop: %.2f, from start: %.2f (%d loops)",
                             loop_duration, elapsed_time, loop_count)
            statsmgr.gauge('loop.count', loop_count)
            statsmgr.timer('loop.duration', loop_duration)
            statsmgr.timer('run.duration', elapsed_time)
            if self.log_loop:
                logger.debug("Check average (loop) = %d checks results, %.2f checks/s",
                             self.nb_checks, self.nb_checks / loop_duration)
                logger.debug("Check average (total) = %d checks results, %.2f checks/s",
                             self.nb_checks_total, self.nb_checks_total / elapsed_time)
            self.nb_checks = 0

            if self.nb_checks_dropped > 0 \
                    or self.nb_broks_dropped > 0 or self.nb_actions_dropped > 0:
                logger.warning("We dropped %d checks, %d broks and %d actions",
                               self.nb_checks_dropped, self.nb_broks_dropped,
                               self.nb_actions_dropped)

            if self.log_loop:
                logger.debug("+++ %d", loop_count)

        logger.info("[%s] stopping scheduler loop: started: %.2f, elapsed time: %.2f seconds",
                    self.instance_name, sch_start_ts, elapsed_time)

        # We must save the retention at the quit BY OURSELVES
        # because our daemon will not be able to do it for us
        self.update_retention_file(True)
