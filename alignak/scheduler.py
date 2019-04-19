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
from datetime import datetime
import os
import logging
import tempfile
import traceback
import queue
from collections import defaultdict
from six import string_types

from alignak.objects.item import Item
from alignak.macroresolver import MacroResolver

from alignak.action import ACT_STATUS_SCHEDULED, ACT_STATUS_POLLED, \
    ACT_STATUS_TIMEOUT, ACT_STATUS_ZOMBIE, ACT_STATUS_WAIT_CONSUME, \
    ACT_STATUS_WAIT_DEPEND, ACT_STATUS_WAITING_ME
from alignak.external_command import ExternalCommand
from alignak.check import Check
from alignak.notification import Notification
from alignak.eventhandler import EventHandler
from alignak.brok import Brok
from alignak.downtime import Downtime
from alignak.comment import Comment
from alignak.util import average_percentile
from alignak.stats import statsmgr
from alignak.misc.serialization import unserialize
from alignak.acknowledge import Acknowledge
from alignak.log import make_monitoring_log

# Multiplier for the maximum count of broks, checks and actions
MULTIPLIER_MAX_CHECKS = 5
MULTIPLIER_MAX_BROKS = 5
MULTIPLIER_MAX_ACTIONS = 5

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Scheduler(object):  # pylint: disable=R0902
    """Scheduler class. Mostly handle scheduling items (host service) to schedule checks
    raise alerts, manage downtimes, etc."""

    def __init__(self, scheduler_daemon):
        """Receives the daemon this Scheduler is attached to

        :param scheduler_daemon: schedulerdaemon
        :type scheduler_daemon: alignak.daemons.schedulerdaemon.Alignak
        """
        self.my_daemon = scheduler_daemon

        # The scheduling is on/off, default is False
        self.must_schedule = False

        # The actions results returned by satelittes or fetched from
        # passive satellites are stored in this queue
        self.waiting_results = queue.Queue()

        # Every N loop turns (usually seconds...) we call functions like consume, del zombies
        # etc. All of these functions are in recurrent_works with the tick count to run them.
        # So it must be an integer > 0
        # The order is important, so make key an integer index.
        # TODO: at load, change value by configuration one (like reaper time, etc)
        self.recurrent_works = {
            0: ('update_downtimes_and_comments',
                self.update_downtimes_and_comments, 1),
            1: ('schedule',
                self.schedule, 1),
            2: ('check_freshness',
                self.check_freshness, 10),
            3: ('consume_results',
                self.consume_results, 1),
            # now get the news actions (checks, notif) raised
            4: ('get_new_actions',
                self.get_new_actions, 1),
            5: ('scatter_master_notifications',
                self.scatter_master_notifications, 1),
            6: ('get_new_broks',
                self.get_new_broks, 1),  # and broks
            7: ('delete_zombie_checks',
                self.delete_zombie_checks, 1),
            8: ('delete_zombie_actions',
                self.delete_zombie_actions, 1),
            9: ('clean_caches',
                self.clean_caches, 1),
            10: ('update_retention',
                 self.update_retention, 3600),
            11: ('check_orphaned',
                 self.check_orphaned, 60),
            12: ('update_program_status',
                 self.update_program_status, 10),
            13: ('check_for_system_time_change',
                 self.my_daemon.check_for_system_time_change, 1),
            14: ('manage_internal_checks',
                 self.manage_internal_checks, 1),
            15: ('clean_queues',
                 self.clean_queues, 1),
            16: ('update_business_values',
                 self.update_business_values, 60),
            17: ('reset_topology_change_flag',
                 self.reset_topology_change_flag, 1),
            18: ('check_for_expire_acknowledge',
                 self.check_for_expire_acknowledge, 1),
            19: ('send_broks_to_modules',
                 self.send_broks_to_modules, 1),
            20: ('get_objects_from_from_queues',
                 self.get_objects_from_from_queues, 1),
            21: ('get_latency_average_percentile',
                 self.get_latency_average_percentile, 10),
        }

        # Statistics part
        # ---
        # Created items
        self.nb_checks = 0
        self.nb_internal_checks = 0
        self.nb_broks = 0
        self.nb_notifications = 0
        self.nb_event_handlers = 0
        self.nb_external_commands = 0

        # Launched checks - send to execution to poller/reactionner
        self.nb_checks_launched = 0
        self.nb_actions_launched = 0

        # Checks results received
        self.nb_checks_results = 0
        self.nb_checks_results_timeout = 0
        self.nb_checks_results_active = 0
        self.nb_checks_results_passive = 0
        self.nb_actions_results = 0
        self.nb_actions_results_timeout = 0

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

        # Temporary set. Will be updated with the configuration received from our Arbiter
        self.instance_id = 'uninstantiated'
        self.instance_name = self.my_daemon.name
        self.alignak_name = None

        # And a dummy push flavor
        self.push_flavor = 0

        # Our queues
        self.checks = {}
        self.actions = {}

        # self.program_start = int(time.time())
        self.program_start = self.my_daemon.program_start
        self.pushed_conf = None

        # Our external commands manager
        self.external_commands_manager = None

        # This scheduler has raised the initial broks
        self.raised_initial_broks = False

        self.need_dump_environment = False
        self.need_objects_dump = False

    @property
    def name(self):
        """Get the scheduler name

        Indeed, we return our suffixed daemon name

        :return:
        :rtype:
        """
        return "%s scheduler" % self.my_daemon.name

    def reset(self):
        # pylint: disable=not-context-manager
        """Reset scheduler::

        * Remove waiting results
        * Clear checks and actions lists

        :return: None
        """
        logger.info("Scheduling loop reset")
        with self.waiting_results.mutex:
            self.waiting_results.queue.clear()
        self.checks.clear()
        self.actions.clear()

    def all_my_hosts_and_services(self):
        """Create an iterator for all my known hosts and services

        :return: None
        """
        for what in (self.hosts, self.services):
            for item in what:
                yield item

    def load_conf(self, instance_id, instance_name, conf):
        """Load configuration received from Arbiter and pushed by our Scheduler daemon

        :param instance_name: scheduler instance name
        :type instance_name: str
        :param instance_id: scheduler instance id
        :type instance_id: str
        :param conf: configuration to load
        :type conf: alignak.objects.config.Config
        :return: None
        """
        self.pushed_conf = conf

        logger.info("loading my configuration (%s / %s):",
                    instance_id, self.pushed_conf.instance_id)
        logger.debug("Properties:")
        for key in sorted(self.pushed_conf.properties):
            logger.debug("- %s: %s", key, getattr(self.pushed_conf, key, []))
        logger.debug("Macros:")
        for key in sorted(self.pushed_conf.macros):
            logger.debug("- %s: %s", key, getattr(self.pushed_conf.macros, key, []))
        logger.debug("Objects types:")
        for _, _, strclss, _, _ in list(self.pushed_conf.types_creations.values()):
            if strclss in ['arbiters', 'schedulers', 'brokers',
                           'pollers', 'reactionners', 'receivers']:
                continue
            setattr(self, strclss, getattr(self.pushed_conf, strclss, []))
            # Internal statistics
            logger.debug("- %d %s", len(getattr(self, strclss)), strclss)
            statsmgr.gauge('configuration.%s' % strclss, len(getattr(self, strclss)))

        # We need reversed list for searching in the retention file read
        # todo: check what it is about...
        self.services.optimize_service_search(self.hosts)

        # Just deprecated
        # # Compile the triggers
        # if getattr(self, 'triggers', None):
        #     logger.info("compiling the triggers...")
        #     self.triggers.compile()
        #     self.triggers.load_objects(self)
        # else:
        #     logger.info("No triggers")

        # From the Arbiter configuration. Used for satellites to differentiate the schedulers
        self.alignak_name = self.pushed_conf.alignak_name
        self.instance_id = instance_id
        self.instance_name = instance_name

        self.push_flavor = getattr(self.pushed_conf, 'push_flavor', 'None')
        logger.info("Set my scheduler instance: %s - %s - %s",
                    self.instance_id, self.instance_name, self.push_flavor)

        # Tag our monitored hosts/services with our instance_id
        for item in self.all_my_hosts_and_services():
            item.instance_id = self.instance_id

    def update_recurrent_works_tick(self, conf):
        """Modify the tick value for the scheduler recurrent work

        A tick is an amount of loop of the scheduler before executing the recurrent work

        The provided configuration may contain some tick-function_name keys that contain
        a tick value to be updated. Those parameters are defined in the alignak environment file.

        Indeed this function is called with the Scheduler daemon object. Note that the ``conf``
        parameter may also be a dictionary.

        :param conf: the daemon link configuration to search in
        :type conf: alignak.daemons.schedulerdaemon.Alignak
        :return: None
        """
        for key in self.recurrent_works:
            (name, fun, _) = self.recurrent_works[key]
            if isinstance(conf, dict):
                new_tick = conf.get('tick_%s' % name, None)
            else:
                new_tick = getattr(conf, 'tick_%s' % name, None)

            if new_tick is not None:
                logger.debug("Requesting to change the default tick to %d for the action %s",
                             int(new_tick), name)
            else:
                continue
            # Update the default scheduler tick for this function
            try:
                new_tick = int(new_tick)
                logger.info("Changing the default tick to %d for the action %s", new_tick, name)
                self.recurrent_works[key] = (name, fun, new_tick)
            except ValueError:
                logger.warning("Changing the default tick for '%s' to '%s' failed!", new_tick, name)

    def start_scheduling(self):
        """Set must_schedule attribute to True - enable the scheduling loop

        :return: None
        """
        logger.info("Enabling the scheduling loop...")
        self.must_schedule = True

    def stop_scheduling(self):
        """Set must_schedule attribute to False - disable the scheduling loop

        :return: None
        """
        logger.info("Disabling the scheduling loop...")
        self.must_schedule = False

    def dump_objects(self):
        """Dump scheduler objects into a dump (temp) file

        :return: None
        """
        path = os.path.join(tempfile.gettempdir(),
                            'dump-obj-scheduler-%s-%d.json' % (self.name, int(time.time())))

        logger.info('Dumping scheduler objects to: %s', path)
        try:
            fd = open(path, 'wb')
            output = 'type:uuid:status:t_to_go:poller_tag:worker:command\n'
            fd.write(output.encode('utf-8'))
            for check in list(self.checks.values()):
                output = 'check:%s:%s:%s:%s:%s:%s\n' \
                         % (check.uuid, check.status, check.t_to_go, check.poller_tag,
                            check.command, check.my_worker)
                fd.write(output.encode('utf-8'))
            logger.info('- dumped checks')
            for action in list(self.actions.values()):
                output = '%s: %s:%s:%s:%s:%s:%s\n'\
                         % (action.__class__.my_type, action.uuid, action.status,
                            action.t_to_go, action.reactionner_tag, action.command,
                            action.my_worker)
                fd.write(output.encode('utf-8'))
            logger.info('- dumped actions')
            broks = []
            for broker in list(self.my_daemon.brokers.values()):
                for brok in broker.broks:
                    broks.append(brok)
            for brok in broks:
                output = 'BROK: %s:%s\n' % (brok.uuid, brok.type)
                fd.write(output.encode('utf-8'))
            logger.info('- dumped broks')
            fd.close()
            logger.info('Dumped')
        except OSError as exp:  # pragma: no cover, should never happen...
            logger.critical("Error when writing the objects dump file %s : %s", path, str(exp))

    def dump_config(self):
        """Dump scheduler configuration into a temporary file

        The dumped content is JSON formatted

        :return: None
        """
        path = os.path.join(tempfile.gettempdir(),
                            'dump-cfg-scheduler-%s-%d.json' % (self.name, int(time.time())))

        try:
            self.pushed_conf.dump(path)
        except (OSError, IndexError) as exp:  # pragma: no cover, should never happen...
            logger.critical("Error when writing the configuration dump file %s: %s",
                            path, str(exp))

    def run_external_commands(self, cmds):
        """Run external commands Arbiter/Receiver sent

        :param cmds: commands to run
        :type cmds: list
        :return: None
        """
        if not self.external_commands_manager:
            return

        try:
            _t0 = time.time()
            logger.debug("Scheduler '%s' got %d commands", self.name, len(cmds))
            for command in cmds:
                self.external_commands_manager.resolve_command(ExternalCommand(command))
            statsmgr.counter('external-commands.got.count', len(cmds))
            statsmgr.timer('external-commands.got.time', time.time() - _t0)
        except Exception as exp:  # pylint: disable=broad-except
            logger.warning("External command parsing error: %s", exp)
            logger.warning("Exception: %s / %s", str(exp), traceback.print_exc())
            for command in cmds:
                try:
                    command = command.decode('utf8', 'ignore')
                except UnicodeEncodeError:
                    pass
                except AttributeError:
                    pass

                logger.warning("Command: %s", command)

    def add_brok(self, brok, broker_uuid=None):
        """Add a brok into brokers list
        It can be for a specific one, all brokers or none (startup)

        :param brok: brok to add
        :type brok: alignak.brok.Brok
        :param broker_uuid: broker uuid for the brok
        :type broker_uuid: str
        :return: None
        """
        # We tag the brok with our instance_id
        brok.instance_id = self.instance_id
        if brok.type == 'monitoring_log':
            # The brok is a monitoring event
            with self.my_daemon.events_lock:
                self.my_daemon.events.append(brok)
            statsmgr.counter('events', 1)
            return

        if broker_uuid:
            if broker_uuid not in self.my_daemon.brokers:
                logger.info("Unknown broker: %s / %s!", broker_uuid, self.my_daemon.brokers)
                return
            broker_link = self.my_daemon.brokers[broker_uuid]
            logger.debug("Adding a brok %s for: %s", brok.type, broker_uuid)
            # it's just for one broker
            self.my_daemon.brokers[broker_link.uuid].broks.append(brok)
            self.nb_broks += 1
        else:
            logger.debug("Adding a brok %s to all brokers", brok.type)
            # add brok to all brokers
            for broker_link_uuid in self.my_daemon.brokers:
                logger.debug("- adding to %s", self.my_daemon.brokers[broker_link_uuid])
                self.my_daemon.brokers[broker_link_uuid].broks.append(brok)
                self.nb_broks += 1

    def add_notification(self, notification):
        """Add a notification into actions list

        :param notification: notification to add
        :type notification: alignak.notification.Notification
        :return: None
        """
        if notification.uuid in self.actions:
            logger.warning("Already existing notification: %s", notification)
            return

        logger.debug("Adding a notification: %s", notification)
        self.actions[notification.uuid] = notification
        self.nb_notifications += 1

        # A notification which is not a master one asks for a brok
        if notification.contact is not None:
            self.add(notification.get_initial_status_brok())

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
        logger.debug("Adding a check: %s", check)

        # Add a new check to the scheduler checks list
        self.checks[check.uuid] = check
        self.nb_checks += 1

        # Raise a brok to inform about a next check is to come ...
        # but only for items that are actively checked
        item = self.find_item_by_id(check.ref)
        if item.active_checks_enabled:
            self.add(item.get_next_schedule_brok())

    def add_event_handler(self, action):
        """Add a event handler into actions list

        :param action: event handler to add
        :type action: alignak.eventhandler.EventHandler
        :return: None
        """
        if action.uuid in self.actions:
            logger.info("Already existing event handler: %s", action)
            return

        self.actions[action.uuid] = action
        self.nb_event_handlers += 1

    def add_external_command(self, ext_cmd):
        """Resolve external command

        :param ext_cmd: extermal command to run
        :type ext_cmd: alignak.external_command.ExternalCommand
        :return: None
        """
        self.external_commands_manager.resolve_command(ext_cmd)
        self.nb_external_commands += 1

    def add(self, elt):
        """Generic function to add objects into the scheduler daemon internal lists::
        Brok -> self.broks
        Check -> self.checks
        Notification -> self.actions
        EventHandler -> self.actions

        For an ExternalCommand, tries to resolve the command

        :param elt: element to add
        :type elt:
        :return: None
        """
        if elt is None:
            return
        logger.debug("Adding: %s / %s", elt.my_type, elt.__dict__)
        fun = self.__add_actions.get(elt.__class__, None)
        if fun:
            fun(self, elt)
        else:
            logger.warning("self.add(): Unmanaged object class: %s (object=%r)", elt.__class__, elt)

    __add_actions = {
        Check:              add_check,
        Brok:               add_brok,
        Notification:       add_notification,
        EventHandler:       add_event_handler,
        ExternalCommand:    add_external_command,
    }

    def hook_point(self, hook_name):
        """Generic function to call modules methods if such method is avalaible

        :param hook_name: function name to call
        :type hook_name: str
        :return:None
        """
        self.my_daemon.hook_point(hook_name=hook_name, handle=self)

    def clean_queues(self):
        # pylint: disable=too-many-locals
        """Reduces internal list size to max allowed

        * checks and broks : 5 * length of hosts + services
        * actions : 5 * length of hosts + services + contacts

        :return: None
        """
        # If we set the interval at 0, we bail out
        if getattr(self.pushed_conf, 'tick_clean_queues', 0) == 0:
            logger.debug("No queues cleaning...")
            return

        max_checks = MULTIPLIER_MAX_CHECKS * (len(self.hosts) + len(self.services))
        max_broks = MULTIPLIER_MAX_BROKS * (len(self.hosts) + len(self.services))
        max_actions = MULTIPLIER_MAX_ACTIONS * len(self.contacts) * (len(self.hosts) +
                                                                     len(self.services))

        # For checks, it's not very simple:
        # For checks, they may be referred to their host/service
        # We do not just del them in the check list, but also in their service/host
        # We want id of lower than max_id - 2*max_checks
        self.nb_checks_dropped = 0
        if max_checks and len(self.checks) > max_checks:
            # keys does not ensure sorted keys. Max is slow but we have no other way.
            to_del_checks = [c for c in list(self.checks.values())]
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
        for broker_link in list(self.my_daemon.brokers.values()):
            if max_broks and len(broker_link.broks) > max_broks:
                logger.warning("I have to drop some broks (%d > %d) for the broker %s "
                               "..., sorry :(", len(broker_link.broks), max_broks, broker_link)

                kept_broks = sorted(broker_link.broks, key=lambda x: x.creation_time)
                # Delete the oldest broks to keep the max_broks most recent...
                # todo: is it a good choice !
                broker_link.broks = kept_broks[0:max_broks]

        self.nb_actions_dropped = 0
        if max_actions and len(self.actions) > max_actions:
            logger.warning("I have to del some actions (currently: %d, max: %d)..., sorry :(",
                           len(self.actions), max_actions)
            to_del_actions = [c for c in list(self.actions.values())]
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
        self.add(item.get_update_status_brok())

    def get_and_register_check_result_brok(self, item):
        """Get a check result brok for item and add it

        :param item: item to get brok from
        :type item: alignak.objects.schedulingitem.SchedulingItem
        :return: None
        """
        self.add(item.get_check_result_brok())

    def check_for_expire_acknowledge(self):
        """Iter over host and service and check if any acknowledgement has expired

        :return: None
        """
        for elt in self.all_my_hosts_and_services():
            elt.check_for_expire_acknowledge()

    def update_business_values(self):
        """Iter over host and service and update business_impact

        :return: None
        """
        for elt in self.all_my_hosts_and_services():
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
        for elt in self.all_my_hosts_and_services():
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
        """Generate children notifications from a master notification
        Also update notification number

        Master notification are raised when a notification must be sent out. They are not
        launched by reactionners (only children are) but they are used to build the
        children notifications.

        From one master notification, several children notifications may be built,
        indeed one per each contact...

        :return: None
        """
        now = time.time()
        # We only want the master scheduled notifications that are immediately launchable
        notifications = [a for a in self.actions.values()
                         if a.is_a == u'notification' and a.status == ACT_STATUS_SCHEDULED
                         and not a.contact and a.is_launchable(now)]
        if notifications:
            logger.debug("Scatter master notification: %d notifications",
                         len(notifications))
        for notification in notifications:
            logger.debug("Scheduler got a master notification: %s", notification)

            # This is a "master" notification created by an host/service.
            # We use it to create children notifications (for the contacts and
            # notification_commands) which are executed in the reactionner.
            item = self.find_item_by_id(notification.ref)
            children = []
            notification_period = None
            if getattr(item, 'notification_period', None) is not None:
                notification_period = self.timeperiods[item.notification_period]
            if not item.is_blocking_notifications(notification_period,
                                                  self.hosts, self.services,
                                                  notification.type, now):
                # If it is possible to send notifications
                # of this type at the current time, then create
                # a single notification for each contact of this item.
                children = item.scatter_notification(
                    notification, self.contacts, self.notificationways, self.timeperiods,
                    self.macromodulations, self.escalations,
                    self.find_item_by_id(getattr(item, "host", None))
                )
                for notif in children:
                    logger.debug(" - child notification: %s", notif)
                    notif.status = ACT_STATUS_SCHEDULED
                    # Add the notification to the scheduler objects
                    self.add(notif)

            # If we have notification_interval then schedule
            # the next notification (problems only)
            if notification.type == u'PROBLEM':
                # Update the ref notif number after raise the one of the notification
                if children:
                    # notif_nb of the master notification
                    # was already current_notification_number+1.
                    # If notifications were sent,
                    # then host/service-counter will also be incremented
                    item.current_notification_number = notification.notif_nb

                if item.notification_interval and notification.t_to_go is not None:
                    # We must continue to send notifications.
                    # Just leave it in the actions list and set it to "scheduled"
                    # and it will be found again later
                    # Ask the service/host to compute the next notif time. It can be just
                    # a.t_to_go + item.notification_interval*item.__class__.interval_length
                    # or maybe before because we have an
                    # escalation that need to raise up before
                    notification.t_to_go = item.get_next_notification_time(notification,
                                                                           self.escalations,
                                                                           self.timeperiods)

                    notification.notif_nb = item.current_notification_number + 1
                    logger.debug("Repeat master notification: %s", notification)
                else:
                    # Wipe out this master notification. It is a master one
                    item.remove_in_progress_notification(notification)
                    logger.debug("Remove master notification (no repeat): %s", notification)
            else:
                # Wipe out this master notification.
                logger.debug("Remove master notification (no more a problem): %s", notification)
                # We don't repeat recover/downtime/flap/etc...
                item.remove_in_progress_notification(notification)

    def get_to_run_checks(self, do_checks=False, do_actions=False,
                          poller_tags=None, reactionner_tags=None,
                          worker_name='none', module_types=None):
        # pylint: disable=too-many-branches
        """Get actions/checks for reactionner/poller

        Called by the poller to get checks (do_checks=True) and
        by the reactionner (do_actions=True) to get actions

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
        if not isinstance(module_types, list):
            module_types = [module_types]

        # If a poller wants its checks
        if do_checks:
            if self.checks:
                logger.debug("I have %d prepared checks", len(self.checks))

            for check in list(self.checks.values()):
                logger.debug("Check: %s (%s / %s)", check.uuid, check.poller_tag, check.module_type)

                if check.internal:
                    # Do not care about Alignak internally executed checks
                    continue

                #  If the command is untagged, and the poller too, or if both are tagged
                #  with same name, go for it
                # if do_check, call for poller, and so poller_tags by default is ['None']
                # by default poller_tag is 'None' and poller_tags is ['None']
                # and same for module_type, the default is the 'fork' type
                if check.poller_tag not in poller_tags:
                    logger.debug(" -> poller tag do not match")
                    continue
                if check.module_type not in module_types:
                    logger.debug(" -> module type do not match")
                    continue

                logger.debug(" -> : %s %s (%s)",
                             'worker' if not check.internal else 'internal',
                             check.status,
                             'now' if check.is_launchable(now) else 'not yet')
                if check._is_orphan and check.status == ACT_STATUS_SCHEDULED \
                        and os.getenv('ALIGNAK_LOG_CHECKS', None):
                    logger.info("--ALC-- orphan check: %s -> : %s %s (%s)",
                                check, 'worker' if not check.internal else 'internal',
                                check.status, 'now' if check.is_launchable(now) else 'not yet')

                # must be ok to launch, and not an internal one (business rules based)
                if check.status == ACT_STATUS_SCHEDULED and check.is_launchable(now):
                    logger.debug("Check to run: %s", check)
                    check.status = ACT_STATUS_POLLED
                    check.my_worker = worker_name
                    res.append(check)

                    # Stats
                    self.nb_checks_launched += 1

                    if 'ALIGNAK_LOG_ACTIONS' in os.environ:
                        if os.environ['ALIGNAK_LOG_ACTIONS'] == 'WARNING':
                            logger.warning("Check to run: %s", check)
                        else:
                            logger.info("Check to run: %s", check)

            if res:
                logger.debug("-> %d checks to start now", len(res))
            else:
                logger.debug("-> no checks to start now")

        # If a reactionner wants its actions
        if do_actions:
            if self.actions:
                logger.debug("I have %d prepared actions", len(self.actions))

            for action in list(self.actions.values()):
                logger.debug("Action: %s (%s / %s)",
                             action.uuid, action.reactionner_tag, action.module_type)

                if action.internal:
                    # Do not care about Alignak internally executed checks
                    continue

                is_master = (action.is_a == 'notification' and not action.contact)
                if is_master:
                    continue

                # if do_action, call the reactionner,
                # and so reactionner_tags by default is ['None']
                # by default reactionner_tag is 'None' and reactionner_tags is ['None'] too
                # So if not the good one, loop for next :)
                if action.reactionner_tag not in reactionner_tags:
                    logger.debug(" -> reactionner tag do not match")
                    continue

                # same for module_type
                if action.module_type not in module_types:
                    logger.debug(" -> module type do not match")
                    continue

                # And now look if we can launch or not :)
                logger.debug(" -> : worker %s (%s)",
                             action.status, 'now' if action.is_launchable(now) else 'not yet')
                if action._is_orphan and action.status == ACT_STATUS_SCHEDULED and \
                        os.getenv('ALIGNAK_LOG_CHECKS', None):
                    logger.info("--ALC-- orphan action: %s", action)

                if action.status == ACT_STATUS_SCHEDULED and action.is_launchable(now):
                    # This is for child notifications and eventhandlers
                    action.status = ACT_STATUS_POLLED
                    action.my_worker = worker_name
                    res.append(action)

                    # Stats
                    self.nb_actions_launched += 1

                    if 'ALIGNAK_LOG_ACTIONS' in os.environ:
                        if os.environ['ALIGNAK_LOG_ACTIONS'] == 'WARNING':
                            logger.warning("Action to run: %s", action)
                        else:
                            logger.info("Action to run: %s", action)

            if res:
                logger.debug("-> %d actions to start now", len(res))
            else:
                logger.debug("-> no actions to start now")

        return res

    def manage_results(self, action):  # pylint: disable=too-many-branches,too-many-statements
        """Get result from pollers/reactionners (actives ones)

        :param action: check / action / event handler to handle
        :type action:
        :return: None
        """
        logger.debug('manage_results: %s ', action)
        if action.is_a == 'notification':
            try:
                _ = self.actions[action.uuid]
            except KeyError as exp:  # pragma: no cover, simple protection
                # Cannot find notification - drop it
                logger.warning('manage_results:: get unknown notification : %s ', str(exp))
                for uuid in self.actions:
                    logger.debug('manage_results:: known action: %s ', self.actions[uuid])
                return

            # We will only see child notifications here
            try:
                timeout = False
                execution_time = 0
                if action.status == ACT_STATUS_TIMEOUT:
                    # Unfortunately the remove_in_progress_notification
                    # sets the status to zombie, so we need to save it here.
                    timeout = True
                    execution_time = action.execution_time

                # Add protection for strange charset
                try:
                    action.output = action.output.decode('utf8', 'ignore')
                except UnicodeDecodeError:
                    pass
                except AttributeError:
                    # Python 3 will raise an exception
                    pass

                self.actions[action.uuid].get_return_from(action)
                item = self.find_item_by_id(self.actions[action.uuid].ref)
                item.remove_in_progress_notification(action)
                self.actions[action.uuid].status = ACT_STATUS_ZOMBIE
                item.last_notification = int(action.check_time)

                # And we ask the item to update its state
                self.get_and_register_status_brok(item)

                # If we' ve got a problem with the notification, raise a Warning log
                if timeout:
                    contact = self.find_item_by_id(self.actions[action.uuid].contact)
                    item = self.find_item_by_id(self.actions[action.uuid].ref)

                    self.nb_actions_results_timeout += 1

                    logger.warning("Contact %s %s notification command '%s ' "
                                   "timed out after %.2f seconds",
                                   contact.contact_name,
                                   item.my_type,
                                   self.actions[action.uuid].command,
                                   execution_time)
                else:
                    self.nb_actions_results += 1

                    if action.exit_status != 0:
                        logger.warning("The notification command '%s' raised an error "
                                       "(exit code=%d): '%s'",
                                       action.command, action.exit_status, action.output)

            except (ValueError, AttributeError) as exp:  # pragma: no cover, simple protection
                # bad object, drop it
                logger.warning('manage_results:: got bad notification : %s ', str(exp))

        elif action.is_a == 'check':
            try:
                check = self.checks[action.uuid]
            except KeyError as exp:  # pragma: no cover, simple protection
                # Cannot find check - drop it
                logger.warning('manage_results:: get unknown check: %s ', action)
                for uuid in self.checks:
                    logger.debug('manage_results:: known check: %s ', self.checks[uuid])
                return

            try:
                if action.status == ACT_STATUS_TIMEOUT:
                    ref = self.find_item_by_id(check.ref)
                    action.long_output = action.output
                    action.output = "(%s %s check timed out)" % (ref.my_type, ref.get_full_name())
                    action.exit_status = self.pushed_conf.timeout_exit_status

                    self.nb_checks_results_timeout += 1

                    logger.warning("Timeout raised for '%s' (check command for the %s '%s'), "
                                   "check status code: %d, execution time: %d seconds",
                                   action.command, ref.my_type, ref.get_full_name(),
                                   action.exit_status, int(action.execution_time))
                else:
                    self.nb_checks_results += 1
                    if action.passive_check:
                        self.nb_checks_results_passive += 1
                    else:
                        self.nb_checks_results_active += 1

                        check.get_return_from(action)
                check.status = ACT_STATUS_WAIT_CONSUME
                if check._is_orphan and os.getenv('ALIGNAK_LOG_CHECKS', None):
                    logger.info("--ALC-- got a result for an orphan check: %s", check)

            except (ValueError, AttributeError) as exp:  # pragma: no cover, simple protection
                # bad object, drop it
                logger.warning('manage_results:: got bad check: %s ', str(exp))

        elif action.is_a == 'eventhandler':
            try:
                old_action = self.actions[action.uuid]
                old_action.status = ACT_STATUS_ZOMBIE
            except KeyError as exp:  # pragma: no cover, simple protection
                # cannot find old action
                # bad object, drop it
                logger.warning('manage_results:: get bad check: %s ', str(exp))
                return

            try:
                if action.status == ACT_STATUS_TIMEOUT:
                    _type = 'event handler'
                    if action.is_snapshot:
                        _type = 'snapshot'
                    ref = self.find_item_by_id(self.checks[action.uuid].ref)
                    logger.info("%s %s command '%s' timed out after %d seconds",
                                ref.__class__.my_type.capitalize(),  # pylint: disable=E1101
                                _type, self.actions[action.uuid].command,
                                int(action.execution_time))

                    self.nb_actions_results_timeout += 1
                else:
                    self.nb_actions_results += 1

                # If it's a snapshot we should get the output and export it
                if action.is_snapshot:
                    old_action.get_return_from(action)
                    s_item = self.find_item_by_id(old_action.ref)
                    self.add(s_item.get_snapshot_brok(old_action.output, old_action.exit_status))
            except (ValueError, AttributeError) as exp:  # pragma: no cover, simple protection
                # bad object, drop it
                logger.warning('manage_results:: got bad event handler: %s ', str(exp))

        else:  # pragma: no cover, simple protection, should not happen!
            logger.error("The received result type in unknown! %s", str(action.is_a))

    def push_actions_to_passive_satellites(self):
        """Send actions/checks to passive poller/reactionners

        :return: None
        """
        # We loop for our passive pollers or reactionners
        for satellites in [self.my_daemon.pollers, self.my_daemon.reactionners]:
            s_type = 'poller'
            if satellites is self.my_daemon.reactionners:
                s_type = 'reactionner'

            for link in [s for s in list(satellites.values()) if s.passive]:
                logger.debug("Try to send actions to the %s '%s'", s_type, link.name)

                # Get actions to execute
                lst = []
                if s_type == 'poller':
                    lst = self.get_to_run_checks(do_checks=True, do_actions=False,
                                                 poller_tags=link.poller_tags,
                                                 worker_name=link.name)
                elif s_type == 'reactionner':
                    lst = self.get_to_run_checks(do_checks=False, do_actions=True,
                                                 reactionner_tags=link.reactionner_tags,
                                                 worker_name=link.name)
                if not lst:
                    logger.debug("Nothing to do...")
                    continue

                logger.debug("Sending %d actions to the %s '%s'", len(lst), s_type, link.name)
                link.push_actions(lst, self.instance_id)

    def get_results_from_passive_satellites(self):
        #  pylint: disable=broad-except
        """Get actions/checks results from passive poller/reactionners

        :return: None
        """
        # We loop for our passive pollers or reactionners
        for satellites in [self.my_daemon.pollers, self.my_daemon.reactionners]:
            s_type = 'poller'
            if satellites is self.my_daemon.reactionners:
                s_type = 'reactionner'

            for link in [s for s in list(satellites.values()) if s.passive]:
                logger.debug("Trying to get results from the %s '%s'", s_type, link.name)

                results = link.get_results(self.instance_id)
                if results:
                    logger.debug("Got some results: %d results from %s", len(results), link.name)
                else:
                    logger.debug("-> no passive results from %s", link.name)
                    continue

                results = unserialize(results, no_load=True)
                if results:
                    logger.info("Received %d passive results from %s", len(results), link.name)

                for result in results:
                    logger.debug("-> result: %s", result)

                    # Append to the scheduler result queue
                    self.waiting_results.put(result)

    def manage_internal_checks(self):
        """Run internal checks

        :return: None
        """
        if os.getenv('ALIGNAK_MANAGE_INTERNAL', '1') != '1':
            return
        now = time.time()
        for chk in list(self.checks.values()):
            if not chk.internal:
                # Exclude checks that are not internal ones
                continue

            # Exclude checks that are not yet ready to launch
            if not chk.is_launchable(now) or chk.status not in [ACT_STATUS_SCHEDULED]:
                continue

            item = self.find_item_by_id(chk.ref)
            # Only if active checks are enabled
            if not item or not item.active_checks_enabled:
                # Ask to remove the check
                chk.status = ACT_STATUS_ZOMBIE
                continue
            logger.debug("Run internal check for %s", item)

            self.nb_internal_checks += 1

            # Execute internal check
            item.manage_internal_check(self.hosts, self.services, chk, self.hostgroups,
                                       self.servicegroups, self.macromodulations,
                                       self.timeperiods)
            # Ask to consume the check result
            chk.status = ACT_STATUS_WAIT_CONSUME

    def reset_topology_change_flag(self):
        """Set topology_change attribute to False in all hosts and services

        :return: None
        """
        for i in self.hosts:
            i.topology_change = False
        for i in self.services:
            i.topology_change = False

    def update_retention(self):
        """Call hook point 'save_retention'.
        Retention modules will write back retention (to file, db etc)

        :param forced: is update forced?
        :type forced: bool
        :return: None
        """
        # If we set the retention update to 0, we do not want to manage retention
        # If we are not forced (like at stopping)
        if self.pushed_conf.retention_update_interval == 0:
            logger.debug("Should have saved retention but it is not enabled")
            return

        _t0 = time.time()
        self.hook_point('save_retention')
        statsmgr.timer('hook.retention-save', time.time() - _t0)

        self.add(make_monitoring_log('INFO', 'RETENTION SAVE: %s' % self.my_daemon.name))
        logger.info('Retention data saved: %.2f seconds', time.time() - _t0)

    def retention_load(self, forced=False):
        """Call hook point 'load_retention'.
        Retention modules will read retention (from file, db etc)

        :param forced: is load forced?
        :type forced: bool
        :return: None
        """
        # If we set the retention update to 0, we do not want to manage retention
        # If we are not forced (like at stopping)
        if self.pushed_conf.retention_update_interval == 0 and not forced:
            logger.debug("Should have loaded retention but it is not enabled")
            return

        _t0 = time.time()
        self.hook_point('load_retention')
        statsmgr.timer('hook.retention-load', time.time() - _t0)

        self.add(make_monitoring_log('INFO', 'RETENTION LOAD: %s' % self.my_daemon.name))
        logger.info('Retention data loaded: %.2f seconds', time.time() - _t0)

    def log_initial_states(self):
        """Raise hosts and services initial status logs

        First, raise hosts status and then services. This to allow the events log
        to be a little sorted.

        :return: None
        """
        # Raise hosts initial status broks
        for elt in self.hosts:
            elt.raise_initial_state()

        # And then services initial status broks
        for elt in self.services:
            elt.raise_initial_state()

    def get_retention_data(self):  # pylint: disable=too-many-branches,too-many-statements
        # pylint: disable=too-many-locals
        """Get all hosts and services data to be sent to the retention storage.

        This function only prepares the data because a module is in charge of making
        the data survive to the scheduler restart.

        todo: Alignak scheduler creates two separate dictionaries: hosts and services
        It would be better to merge the services into the host dictionary!

        :return: dict containing host and service data
        :rtype: dict
        """
        retention_data = {
            'hosts': {}, 'services': {}
        }
        for host in self.hosts:
            h_dict = {}

            # Get the hosts properties and running properties
            properties = host.__class__.properties
            properties.update(host.__class__.running_properties)
            for prop, entry in list(properties.items()):
                if not entry.retention:
                    continue

                val = getattr(host, prop)
                # If a preparation function exists...
                prepare_retention = entry.retention_preparation
                if prepare_retention:
                    val = prepare_retention(host, val)
                h_dict[prop] = val

            retention_data['hosts'][host.host_name] = h_dict
        logger.info('%d hosts sent to retention', len(retention_data['hosts']))

        # Same for services
        for service in self.services:
            s_dict = {}

            # Get the services properties and running properties
            properties = service.__class__.properties
            properties.update(service.__class__.running_properties)
            for prop, entry in list(properties.items()):
                if not entry.retention:
                    continue

                val = getattr(service, prop)
                # If a preparation function exists...
                prepare_retention = entry.retention_preparation
                if prepare_retention:
                    val = prepare_retention(service, val)
                s_dict[prop] = val

            retention_data['services'][(service.host_name, service.service_description)] = s_dict
        logger.info('%d services sent to retention', len(retention_data['services']))

        return retention_data

    def restore_retention_data(self, data):
        """Restore retention data

        Data coming from retention will override data coming from configuration
        It is kinda confusing when you modify an attribute (external command) and it get saved
        by retention

        :param data: data from retention
        :type data: dict
        :return: None
        """
        if 'hosts' not in data:
            logger.warning("Retention data are not correct, no 'hosts' property!")
            return

        for host_name in data['hosts']:
            # We take the dict of our value to load
            host = self.hosts.find_by_name(host_name)
            if host is not None:
                self.restore_retention_data_item(data['hosts'][host_name], host)
        statsmgr.gauge('retention.hosts', len(data['hosts']))
        logger.info('%d hosts restored from retention', len(data['hosts']))

        # Same for services
        for (host_name, service_description) in data['services']:
            # We take our dict to load
            service = self.services.find_srv_by_name_and_hostname(host_name, service_description)
            if service is not None:
                self.restore_retention_data_item(data['services'][(host_name, service_description)],
                                                 service)
        statsmgr.gauge('retention.services', len(data['services']))
        logger.info('%d services restored from retention', len(data['services']))

    def restore_retention_data_item(self, data, item):
        # pylint: disable=too-many-branches, too-many-locals
        """
        Restore data in item

        :param data: retention data of the item
        :type data: dict
        :param item: host or service item
        :type item: alignak.objects.host.Host | alignak.objects.service.Service
        :return: None
        """
        # Manage the properties and running properties
        properties = item.__class__.properties
        properties.update(item.__class__.running_properties)
        for prop, entry in list(properties.items()):
            if not entry.retention:
                continue

            if prop not in data:
                continue

            # If a restoration function exists...
            restore_retention = entry.retention_restoration
            if restore_retention:
                setattr(item, prop, restore_retention(item, data[prop]))
            else:
                setattr(item, prop, data[prop])

        # Now manage all linked objects load from/ previous run
        for notification_uuid in item.notifications_in_progress:
            notification = item.notifications_in_progress[notification_uuid]
            # Update the notification referenced object
            notification['ref'] = item.uuid
            my_notification = Notification(params=notification)
            item.notifications_in_progress[notification_uuid] = my_notification

            # Add a notification in the scheduler actions
            self.add(my_notification)

        # todo: is it useful? We do not save/restore checks in the retention data...
        item.update_in_checking()

        # And also add downtimes and comments
        # Downtimes are in a list..
        for downtime_uuid in data['downtimes']:
            downtime = data['downtimes'][downtime_uuid]

            # Update the downtime referenced object
            downtime['ref'] = item.uuid
            my_downtime = Downtime(params=downtime)
            if downtime['comment_id']:
                if downtime['comment_id'] not in data['comments']:
                    downtime['comment_id'] = ''

            # case comment_id has comment dict instead uuid
            # todo: This should never happen! Why this code ?
            if 'uuid' in downtime['comment_id']:
                data['comments'].append(downtime['comment_id'])
                downtime['comment_id'] = downtime['comment_id']['uuid']
            item.add_downtime(my_downtime)

        # Comments are in a list..
        for comment_uuid in data['comments']:
            comment = data['comments'][comment_uuid]
            # Update the comment referenced object
            comment['ref'] = item.uuid
            item.add_comment(Comment(comment))

        if item.acknowledgement is not None:
            # Update the comment referenced object
            item.acknowledgement['ref'] = item.uuid
            item.acknowledgement = Acknowledge(item.acknowledgement)

        # Relink the notified_contacts as a set() of true contacts objects
        # if it was loaded from the retention, it's now a list of contacts
        # names
        new_notified_contacts = set()
        new_notified_contacts_ids = set()
        for contact_name in item.notified_contacts:
            contact = self.contacts.find_by_name(contact_name)
            if contact is not None:
                new_notified_contacts.add(contact_name)
                new_notified_contacts_ids.add(contact.uuid)
        item.notified_contacts = new_notified_contacts
        item.notified_contacts_ids = new_notified_contacts_ids

    def fill_initial_broks(self, broker_name):
        # pylint: disable=too-many-branches
        """Create initial broks for a specific broker

        :param broker_name: broker name
        :type broker_name: str
        :return: number of created broks
        """
        broker_uuid = None
        logger.debug("My brokers: %s", self.my_daemon.brokers)
        for broker_link in list(self.my_daemon.brokers.values()):
            logger.debug("Searching broker: %s", broker_link)
            if broker_name == broker_link.name:
                broker_uuid = broker_link.uuid
                logger.info("Filling initial broks for: %s (%s)", broker_name, broker_uuid)
                break
        else:
            if self.pushed_conf:
                # I am yet configured but I do not know this broker ! Something went wrong!!!
                logger.error("Requested initial broks for an unknown broker: %s", broker_name)
            else:
                logger.info("Requested initial broks for an unknown broker: %s", broker_name)
            return 0

        if self.my_daemon.brokers[broker_uuid].initialized:
            logger.warning("The broker %s still got its initial broks...", broker_name)
            return 0

        initial_broks_count = len(self.my_daemon.brokers[broker_uuid].broks)

        # First the program status
        brok = self.get_program_status_brok()
        self.add_brok(brok, broker_uuid)

        #  We can't call initial_status from all this types
        #  The order is important, service need host...
        initial_status_types = (self.timeperiods, self.commands,
                                self.contacts, self.contactgroups,
                                self.hosts, self.hostgroups,
                                self.services, self.servicegroups)

        self.pushed_conf.skip_initial_broks = getattr(self.pushed_conf, 'skip_initial_broks', False)
        logger.debug("Skipping initial broks? %s", str(self.pushed_conf.skip_initial_broks))
        if not self.pushed_conf.skip_initial_broks:
            #  We call initial_status from all this types
            #  The order is important, service need host...
            initial_status_types = (self.realms, self.timeperiods, self.commands,
                                    self.notificationways, self.contacts, self.contactgroups,
                                    self.hosts, self.hostgroups, self.hostdependencies,
                                    self.services, self.servicegroups, self.servicedependencies,
                                    self.escalations)

            for tab in initial_status_types:
                for item in tab:
                    # Awful! simply to get the group members property name... :(
                    # todo: replace this!
                    member_items = None
                    if hasattr(item, 'members'):
                        member_items = getattr(self, item.my_type.replace("group", "s"))
                    brok = item.get_initial_status_brok(member_items)
                    self.add_brok(brok, broker_uuid)

        # Add a brok to say that we finished all initial_pass
        brok = Brok({'type': 'initial_broks_done', 'data': {'instance_id': self.instance_id}})
        self.add_brok(brok, broker_uuid)

        final_broks_count = len(self.my_daemon.brokers[broker_uuid].broks)
        self.my_daemon.brokers[broker_uuid].initialized = True

        # Send the initial broks to our modules
        self.send_broks_to_modules()

        # We now have raised all the initial broks
        self.raised_initial_broks = True

        logger.info("Created %d initial broks for %s",
                    final_broks_count - initial_broks_count, broker_name)
        return final_broks_count - initial_broks_count

    def initial_program_status(self):
        """Create and add a program_status brok

        :return: None
        """
        self.add(self.get_program_status_brok(brok_type='program_status'))

    def update_program_status(self):
        """Create and add a update_program_status brok

        :return: None
        """
        self.add(self.get_program_status_brok(brok_type='update_program_status'))

    def get_program_status_brok(self, brok_type='program_status'):
        """Create a program status brok

        Initially builds the running properties and then, if initial status brok,
        get the properties from the Config class where an entry exist for the brok
        'full_status'

        :return: Brok with program status data
        :rtype: alignak.brok.Brok
        """
        # Get the running statistics
        data = {
            "is_running": True,
            "instance_id": self.instance_id,
            # "alignak_name": self.alignak_name,
            "instance_name": self.name,
            "last_alive": time.time(),
            "pid": os.getpid(),
            '_running': self.get_scheduler_stats(details=True),
            '_config': {},
            '_macros': {}
        }

        # Get configuration data from the pushed configuration
        cls = self.pushed_conf.__class__
        for prop, entry in list(cls.properties.items()):
            # Is this property intended for broking?
            if 'full_status' not in entry.fill_brok:
                continue
            data['_config'][prop] = self.pushed_conf.get_property_value_for_brok(
                prop, cls.properties)
            # data['_config'][prop] = getattr(self.pushed_conf, prop, entry.default)

        # Get the macros from the pushed configuration and try to resolve
        # the macros to provide the result in the status brok
        macro_resolver = MacroResolver()
        macro_resolver.init(self.pushed_conf)
        for macro_name in sorted(self.pushed_conf.macros):
            data['_macros'][macro_name] = \
                macro_resolver.resolve_simple_macros_in_string("$%s$" % macro_name,
                                                               [], None, None)

        logger.debug("Program status brok %s data: %s", brok_type, data)
        return Brok({'type': brok_type, 'data': data})

    def consume_results(self):  # pylint: disable=too-many-branches
        """Handle results waiting in waiting_results list.
        Check ref will call consume result and update their status

        :return: None
        """
        # All results are in self.waiting_results
        # We need to get them first
        queue_size = self.waiting_results.qsize()
        for _ in range(queue_size):
            self.manage_results(self.waiting_results.get())

        # Then we consume them
        for chk in list(self.checks.values()):
            if chk.status == ACT_STATUS_WAIT_CONSUME:
                logger.debug("Consuming: %s", chk)
                item = self.find_item_by_id(chk.ref)
                notification_period = None
                if getattr(item, 'notification_period', None) is not None:
                    notification_period = self.timeperiods[item.notification_period]

                dep_checks = item.consume_result(chk, notification_period, self.hosts,
                                                 self.services, self.timeperiods,
                                                 self.macromodulations, self.checkmodulations,
                                                 self.businessimpactmodulations,
                                                 self.resultmodulations, self.checks,
                                                 self.pushed_conf.log_active_checks and
                                                 not chk.passive_check)

                # # Raise the log only when the check got consumed!
                # # Else the item information are not up-to-date :/
                # if self.pushed_conf.log_active_checks and not chk.passive_check:
                #     item.raise_check_result()
                #
                for check in dep_checks:
                    logger.debug("-> raised a dependency check: %s", chk)
                    self.add(check)

        # loop to resolve dependencies
        have_resolved_checks = True
        while have_resolved_checks:
            have_resolved_checks = False
            # All 'finished' checks (no more dep) raise checks they depend on
            for chk in list(self.checks.values()):
                if chk.status == ACT_STATUS_WAITING_ME:
                    for dependent_checks in chk.depend_on_me:
                        # Ok, now dependent will no more wait
                        dependent_checks.depend_on.remove(chk.uuid)
                        have_resolved_checks = True
                    # REMOVE OLD DEP CHECK -> zombie
                    chk.status = ACT_STATUS_ZOMBIE

            # Now, reinteger dep checks
            for chk in list(self.checks.values()):
                if chk.status == ACT_STATUS_WAIT_DEPEND and not chk.depend_on:
                    item = self.find_item_by_id(chk.ref)
                    notification_period = None
                    if getattr(item, 'notification_period', None) is not None:
                        notification_period = self.timeperiods[item.notification_period]
                    dep_checks = item.consume_result(chk, notification_period, self.hosts,
                                                     self.services, self.timeperiods,
                                                     self.macromodulations, self.checkmodulations,
                                                     self.businessimpactmodulations,
                                                     self.resultmodulations, self.checks,
                                                     self.pushed_conf.log_active_checks and
                                                     not chk.passive_check)
                    for check in dep_checks:
                        self.add(check)

    def delete_zombie_checks(self):
        """Remove checks that have a zombie status (usually timeouts)

        :return: None
        """
        id_to_del = []
        for chk in list(self.checks.values()):
            if chk.status == ACT_STATUS_ZOMBIE:
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
        for act in list(self.actions.values()):
            if act.status == ACT_STATUS_ZOMBIE:
                id_to_del.append(act.uuid)
        # une petite tape dans le dos et tu t'en vas, merci...
        # *pat pat* GFTO, thks :)
        for a_id in id_to_del:
            del self.actions[a_id]  # ZANKUSEN!

    def update_downtimes_and_comments(self):
        # pylint: disable=too-many-branches
        """Iter over all hosts and services::

        TODO: add some unit tests for the maintenance period feature.

        * Update downtime status (start / stop) regarding maintenance period
        * Register new comments in comments list

        :return: None
        """
        broks = []
        now = time.time()

        # Check maintenance periods
        for elt in self.all_my_hosts_and_services():
            if not elt.maintenance_period:
                continue

            if elt.in_maintenance == -1:
                timeperiod = self.timeperiods[elt.maintenance_period]
                if timeperiod.is_time_valid(now):
                    start_dt = timeperiod.get_next_valid_time_from_t(now)
                    end_dt = timeperiod.get_next_invalid_time_from_t(start_dt + 1) - 1
                    data = {
                        'ref': elt.uuid, 'ref_type': elt.my_type, 'start_time': start_dt,
                        'end_time': end_dt, 'fixed': 1, 'trigger_id': '',
                        'duration': 0, 'author': "Alignak",
                        'comment': "This downtime was automatically scheduled by Alignak "
                                   "because of a maintenance period."
                    }
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
        for elt in self.all_my_hosts_and_services():
            for downtime in list(elt.downtimes.values()):
                if not downtime.can_be_deleted:
                    continue

                logger.debug("Downtime to delete: %s", downtime.__dict__)
                elt.del_downtime(downtime.uuid)
                broks.append(elt.get_update_status_brok())

        # Same for contact downtimes:
        for elt in self.contacts:
            for downtime in list(elt.downtimes.values()):
                if not downtime.can_be_deleted:
                    continue
                elt.del_downtime(downtime.uuid)
                broks.append(elt.get_update_status_brok())

        # Check start and stop times
        for elt in self.all_my_hosts_and_services():
            for downtime in list(elt.downtimes.values()):
                if downtime.real_end_time < now:
                    # this one has expired
                    broks.extend(downtime.exit(self.timeperiods, self.hosts, self.services))
                elif now >= downtime.start_time and downtime.fixed and not downtime.is_in_effect:
                    # this one has to start now
                    broks.extend(downtime.enter(self.timeperiods, self.hosts, self.services))
                    broks.append(self.find_item_by_id(downtime.ref).get_update_status_brok())

        for brok in broks:
            self.add(brok)

    def schedule(self, elements=None):
        """Iterate over all hosts and services and call schedule method
        (schedule next check)

        If elements is None all our hosts and services are scheduled for a check.

        :param elements: None or list of host / services to schedule
        :type elements: None | list
        :return: None
        """
        if not elements:
            elements = self.all_my_hosts_and_services()

        # ask for service and hosts their next check
        for elt in elements:
            logger.debug("Add check for: %s", elt)
            self.add(elt.schedule(self.hosts, self.services, self.timeperiods,
                                  self.macromodulations, self.checkmodulations, self.checks))

    def get_new_actions(self):
        """Call 'get_new_actions' hook point
        Iter over all hosts and services to add new actions in internal lists

        :return: None
        """
        _t0 = time.time()
        self.hook_point('get_new_actions')
        statsmgr.timer('hook.get-new-actions', time.time() - _t0)
        # ask for service and hosts their next check
        for elt in self.all_my_hosts_and_services():
            for action in elt.actions:
                logger.debug("Got a new action for %s: %s", elt, action)
                self.add(action)
            # We take all, we can clear it
            elt.actions = []

    def get_new_broks(self):
        """Iter over all hosts and services to add new broks in internal lists

        :return: None
        """
        # ask for service and hosts their broks waiting
        # be eaten
        for elt in self.all_my_hosts_and_services():
            for brok in elt.broks:
                self.add(brok)
            # We got all, clear item broks list
            elt.broks = []

        # Also fetch broks from contact (like contactdowntime)
        for contact in self.contacts:
            for brok in contact.broks:
                self.add(brok)
            # We got all, clear contact broks list
            contact.broks = []

    def check_freshness(self):
        """
        Iter over all hosts and services to check freshness if check_freshness enabled and
        passive_checks_enabled are set

        For the host items, the list of hosts to check contains hosts that:
        - have freshness check enabled
        - are not yet freshness expired
        - are only passively checked

        For the service items, the list of services to check contains services that:
        - do not depend upon an host that is freshness expired
        - have freshness check enabled
        - are not yet freshness expired
        - are only passively checked

        :return: None
        """
        # Get tick count
        # (_, _, tick) = self.recurrent_works['check_freshness']

        _t0 = time.time()
        now = int(_t0)

        items = []

        # May be self.ticks is not set (unit tests context!)
        ticks = getattr(self, 'ticks', self.pushed_conf.host_freshness_check_interval)
        if self.pushed_conf.check_host_freshness \
                and ticks % self.pushed_conf.host_freshness_check_interval == 0:
            # Freshness check is configured for hosts - get the list of concerned hosts:
            # host check freshness is enabled and the host is only passively checked
            hosts = [h for h in self.hosts if h.check_freshness and not h.freshness_expired and
                     h.passive_checks_enabled and not h.active_checks_enabled]
            statsmgr.gauge('freshness.hosts-count', len(hosts))
            items.extend(hosts)
            logger.debug("Freshness check is enabled for %d hosts", len(hosts))

            hosts = [h for h in self.hosts if h.check_freshness and h.freshness_expired]
            logger.debug("Freshness still expired for %d hosts", len(hosts))
            for h in hosts:
                h.last_chk = now
                self.add(h.get_check_result_brok())
                # Update check output with last freshness check time
                h.output = "Freshness period expired: %s, last updated: %s" % (
                    datetime.utcfromtimestamp(h.last_hard_state_change).strftime(
                        "%Y-%m-%d %H:%M:%S %Z"),
                    datetime.utcfromtimestamp(h.last_chk).strftime(
                        "%Y-%m-%d %H:%M:%S %Z"))
                logger.debug("Freshness still expired: %s / %s", h.get_name(), h.output)

        # May be self.ticks is not set (unit tests context!)
        ticks = getattr(self, 'ticks', self.pushed_conf.service_freshness_check_interval)
        if self.pushed_conf.check_service_freshness \
                and ticks % self.pushed_conf.service_freshness_check_interval == 0:
            # Freshness check is configured for services - get the list of concerned services:
            # service check freshness is enabled and the service is only passively checked and
            # the depending host is not freshness expired
            services = [s for s in self.services if not self.hosts[s.host].freshness_expired and
                        s.check_freshness and not s.freshness_expired and
                        s.passive_checks_enabled and not s.active_checks_enabled]
            statsmgr.gauge('freshness.services-count', len(services))
            items.extend(services)
            logger.debug("Freshness check is enabled for %d services", len(services))

            services = [s for s in self.services if not self.hosts[s.host].freshness_expired and
                        s.check_freshness and s.freshness_expired]
            logger.debug("Freshness still expired for %d services", len(services))
            for s in services:
                s.last_chk = now
                self.add(s.get_check_result_brok())
                # Update check output with last freshness check time
                s.output = "Freshness period expired: %s, last updated: %s" % (
                    datetime.utcfromtimestamp(s.last_hard_state_change).strftime(
                        "%Y-%m-%d %H:%M:%S %Z"),
                    datetime.utcfromtimestamp(s.last_chk).strftime(
                        "%Y-%m-%d %H:%M:%S %Z"))
                logger.debug("Freshness still expired: %s / %s", s.get_full_name(), s.output)

        statsmgr.timer('freshness.items-list', time.time() - _t0)

        if not items:
            logger.debug("No freshness enabled item.")
            return

        _t0 = time.time()
        raised_checks = 0
        for elt in items:
            chk = elt.do_check_freshness(self.hosts, self.services, self.timeperiods,
                                         self.macromodulations, self.checkmodulations,
                                         self.checks, _t0)
            if chk is not None:
                self.add(chk)
                self.waiting_results.put(chk)
                raised_checks += 1
        logger.info("Raised %d checks for freshness", raised_checks)
        statsmgr.gauge('freshness.raised-checks', raised_checks)
        statsmgr.timer('freshness.do-check', time.time() - _t0)

    def check_orphaned(self):
        """Check for orphaned checks/actions::

        * status == 'in_poller' and t_to_go < now - time_to_orphanage (300 by default)

        if so raise a warning log.

        :return: None
        """
        orphans_count = {}
        now = int(time.time())
        actions = list(self.checks.values()) + list(self.actions.values())
        for chk in actions:
            if chk.status not in [ACT_STATUS_POLLED]:
                continue

            time_to_orphanage = self.find_item_by_id(chk.ref).get_time_to_orphanage()
            if not time_to_orphanage:
                continue

            if chk.t_to_go > now - time_to_orphanage:
                continue

            logger.info("Orphaned %s (%d s / %s / %s) check for: %s (%s)",
                        chk.is_a, time_to_orphanage, chk.t_to_go, now,
                        self.find_item_by_id(chk.ref).get_full_name(), chk)
            chk._is_orphan = True
            chk.status = ACT_STATUS_SCHEDULED
            if chk.my_worker not in orphans_count:
                orphans_count[chk.my_worker] = 0
            orphans_count[chk.my_worker] += 1

        for sta_name in orphans_count:
            logger.warning("%d actions never came back for the satellite '%s'. "
                           "I reenable them for polling.",
                           orphans_count[sta_name], sta_name)

    def send_broks_to_modules(self):
        """Put broks into module queues
        Only broks without sent_to_externals to True are sent
        Only modules that ask for broks will get some

        :return: None
        """
        t00 = time.time()
        nb_sent = 0
        broks = []
        for broker_link in list(self.my_daemon.brokers.values()):
            for brok in broker_link.broks:
                if not getattr(brok, 'sent_to_externals', False):
                    brok.to_send = True
                    broks.append(brok)
        if not broks:
            return
        logger.debug("sending %d broks to modules...", len(broks))

        for mod in self.my_daemon.modules_manager.get_external_instances():
            logger.debug("Look for sending to module %s", mod.get_name())
            module_queue = mod.to_q
            if module_queue:
                to_send = [b for b in broks if mod.want_brok(b)]
                module_queue.put(to_send)
                nb_sent += len(to_send)

        # No more need to send them
        for broker_link in list(self.my_daemon.brokers.values()):
            for brok in broker_link.broks:
                if not getattr(brok, 'sent_to_externals', False):
                    brok.to_send = False
                    brok.sent_to_externals = True
        logger.debug("Time to send %d broks (after %d secs)", nb_sent, time.time() - t00)

    def get_objects_from_from_queues(self):
        """Same behavior than Daemon.get_objects_from_from_queues().

        :return:
        :rtype:
        """
        return self.my_daemon.get_objects_from_from_queues()

    def get_scheduler_stats(self, details=False):  # pylint: disable=unused-argument
        # pylint: disable=too-many-locals, too-many-branches
        """Get the scheduler statistics

        :return: A dict with the following structure
        ::

           { 'modules': [
                         {'internal': {'name': "MYMODULE1", 'state': 'ok'},
                         {'external': {'name': "MYMODULE2", 'state': 'stopped'},
                        ]
             'latency':  {'avg': lat_avg, 'min': lat_min, 'max': lat_max}
             'hosts': len(self.hosts),
             'services': len(self.services),
             'commands': [{'cmd': c, 'u_time': u_time, 's_time': s_time}, ...] (10 first)
             'livesynthesis': {...}
           }

        :rtype: dict
        """
        m_solver = MacroResolver()

        res = {
            '_freshness': int(time.time()),
            'counters': {},
            'latency': self.stats['latency'],
            'monitored_objects': {},
            'livesynthesis': {}
        }

        checks_status_counts = self.get_checks_status_counts()

        # Checks / actions counters
        for what in (u'actions', u'checks'):
            res['counters']['%s.count' % what] = len(getattr(self, what))
            for status in (u'scheduled', u'in_poller', u'zombie'):
                res['counters']['%s.%s' % (what, status)] = checks_status_counts[status]

        if self.pushed_conf:
            for _, _, strclss, _, _ in list(self.pushed_conf.types_creations.values()):
                # Internal statistics
                res['monitored_objects'][strclss] = len(getattr(self, strclss, []))

            # Scheduler live synthesis
            res['livesynthesis'] = {
                'hosts_total': m_solver._get_total_hosts(),
                'hosts_not_monitored': m_solver._get_total_hosts_not_monitored(),
                'hosts_up_hard': m_solver._get_total_hosts_up(u'HARD'),
                'hosts_up_soft': m_solver._get_total_hosts_up(u'SOFT'),
                'hosts_down_hard': m_solver._get_total_hosts_down(u'HARD'),
                'hosts_down_soft': m_solver._get_total_hosts_down(u'SOFT'),
                'hosts_unreachable_hard': m_solver._get_total_hosts_unreachable(u'HARD'),
                'hosts_unreachable_soft': m_solver._get_total_hosts_unreachable(u'SOFT'),

                'hosts_problems': m_solver._get_total_hosts_problems_unhandled(),
                'hosts_acknowledged': m_solver._get_total_hosts_problems_handled(),
                'hosts_in_downtime': m_solver._get_total_hosts_downtimed(),
                'hosts_flapping': m_solver._get_total_hosts_flapping(),

                'services_total': m_solver._get_total_services(),
                'services_not_monitored': m_solver._get_total_services_not_monitored(),
                'services_ok_hard': m_solver._get_total_services_ok(u'HARD'),
                'services_ok_soft': m_solver._get_total_services_ok(u'SOFT'),
                'services_warning_hard': m_solver._get_total_services_warning(u'HARD'),
                'services_warning_soft': m_solver._get_total_services_warning(u'SOFT'),
                'services_critical_hard': m_solver._get_total_services_critical(u'HARD'),
                'services_critical_soft': m_solver._get_total_services_critical(u'SOFT'),
                'services_unknown_hard': m_solver._get_total_services_unknown(u'HARD'),
                'services_unknown_soft': m_solver._get_total_services_unknown(u'SOFT'),
                'services_unreachable_hard': m_solver._get_total_services_unreachable(u'HARD'),
                'services_unreachable_soft': m_solver._get_total_services_unreachable(u'SOFT'),

                'services_problems': m_solver._get_total_services_problems_unhandled(),
                'services_acknowledged': m_solver._get_total_services_problems_handled(),
                'services_in_downtime': m_solver._get_total_services_downtimed(),
                'services_flapping': m_solver._get_total_services_flapping()
            }

            if details:
                # Hosts/services problems list
                all_problems = {}
                for item in self.hosts:
                    if item.state_type not in [u'HARD'] or item.state not in ['DOWN']:
                        continue

                    if item.is_problem and not item.problem_has_been_acknowledged:
                        all_problems[item.uuid] = {
                            'host': item.get_name(),
                            'service': None,
                            'state': item.state,
                            'state_type': item.state_type,
                            'output': item.output,
                            'last_state': item.last_state,
                            'last_state_type': item.last_state_type,
                            'last_state_update': item.last_state_update,
                            'last_state_change': item.last_state_change,
                            'last_hard_state_change': item.last_hard_state_change,
                            'last_hard_state': item.last_hard_state,
                        }

                for item in self.services:
                    if item.state_type not in [u'HARD'] or item.state not in ['WARNING',
                                                                              'CRITICAL']:
                        continue

                    if item.is_problem and not item.problem_has_been_acknowledged:
                        all_problems[item.uuid] = {
                            'host': item.host_name,
                            'service': item.get_name(),
                            'output': item.output,
                            'state': item.state,
                            'state_type': item.state_type,
                            'last_state': item.last_state,
                            'last_state_type': item.last_state_type,
                            'last_hard_state': item.last_hard_state,
                            'last_state_update': item.last_state_update,
                            'last_state_change': item.last_state_change,
                            'last_hard_state_change': item.last_hard_state_change,
                        }

                res['problems'] = all_problems

                all_commands = {}
                # Some checks statistics: user/system time
                for elt in self.all_my_hosts_and_services():
                    last_cmd = elt.last_check_command
                    if not last_cmd:
                        continue
                    cmd = os.path.split(last_cmd.split(' ', 1)[0])[1]
                    u_time = elt.u_time
                    s_time = elt.s_time
                    old_u_time, old_s_time = all_commands.get(cmd, (0.0, 0.0))
                    interval = elt.check_interval
                    if not interval:
                        interval = 1
                    old_u_time += u_time / interval
                    old_s_time += s_time / interval
                    all_commands[cmd] = (old_u_time, old_s_time)

                # Return all the commands
                res['commands'] = all_commands

        return res

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
        status and the values being the count of the checks in that status.

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
        for chk in checks.values():
            res[chk.status] += 1
        return res

    def find_item_by_id(self, object_id):
        """Get item based on its id or uuid

        :param object_id:
        :type object_id: int | str
        :return:
        :rtype: alignak.objects.item.Item | None
        """
        # Item id may be an item
        if isinstance(object_id, Item):
            return object_id

        # Item id should be a uuid string
        if not isinstance(object_id, string_types):
            logger.debug("Find an item by id, object_id is not int nor string: %s", object_id)
            return object_id

        for items in [self.hosts, self.services, self.actions, self.checks, self.hostgroups,
                      self.servicegroups, self.contacts, self.contactgroups]:
            if object_id in items:
                return items[object_id]

        # raise AttributeError("Item with id %s not found" % object_id)  # pragma: no cover,
        logger.error("Item with id %s not found", str(object_id))  # pragma: no cover,
        return None
        # simple protection this should never happen

    def before_run(self):
        """Initialize the scheduling process"""
        # Actions and checks counters
        self.nb_checks = 0
        self.nb_internal_checks = 0
        self.nb_checks_launched = 0
        self.nb_actions_launched = 0

        self.nb_checks_results = 0
        self.nb_checks_results_timeout = 0
        self.nb_checks_results_passive = 0
        self.nb_checks_results_active = 0

        self.nb_actions_results = 0
        self.nb_actions_results_timeout = 0
        self.nb_actions_results_passive = 0

        self.nb_broks_dropped = 0
        self.nb_checks_dropped = 0
        self.nb_actions_dropped = 0

        # Broks, notifications, ... counters
        self.nb_broks = 0
        self.nb_notifications = 0
        self.nb_event_handlers = 0
        self.nb_external_commands = 0

        self.ticks = 0

    def after_run(self):
        """After the scheduling process"""
        # We must save the retention at the quit BY OURSELVES
        # because our daemon will not be able to do it for us
        self.update_retention()

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
        if not self.must_schedule:
            logger.warning("#%d - scheduler is not active...",
                           self.my_daemon.loop_count)
            return
        # Increment ticks count
        self.ticks += 1

        loop_start_ts = time.time()
        # Do recurrent works like schedule, consume, delete_zombie_checks
        for i in self.recurrent_works:
            (name, fun, nb_ticks) = self.recurrent_works[i]
            # A 0 in the tick will just disable it
            if nb_ticks:
                if self.ticks % nb_ticks == 0:
                    # Call it and save the time spend in it
                    _t0 = time.time()
                    fun()
                    statsmgr.timer('loop.recurrent.%s' % name, time.time() - _t0)
        statsmgr.timer('loop.recurrent', time.time() - loop_start_ts)

        _ts = time.time()
        self.push_actions_to_passive_satellites()
        statsmgr.timer('loop.push_actions_to_passive_satellites', time.time() - _ts)
        _ts = time.time()
        self.get_results_from_passive_satellites()
        statsmgr.timer('loop.get_results_from_passive_satellites', time.time() - _ts)

        # Scheduler statistics
        # - broks / notifications counters
        if self.my_daemon.log_loop:
            logger.debug("Items (loop): broks: %d, notifications: %d, checks: %d, internal checks: "
                         "%d, event handlers: %d, external commands: %d",
                         self.nb_broks, self.nb_notifications, self.nb_checks,
                         self.nb_internal_checks, self.nb_event_handlers, self.nb_external_commands)
        statsmgr.gauge('activity.checks', self.nb_checks)
        statsmgr.gauge('activity.internal_checks', self.nb_internal_checks)
        statsmgr.gauge('activity.launched_checks', self.nb_checks_launched)
        statsmgr.gauge('activity.checks_results', self.nb_checks_results)
        statsmgr.gauge('activity.checks_results_timeout', self.nb_checks_results_timeout)
        statsmgr.gauge('activity.checks_results_active', self.nb_checks_results_active)
        statsmgr.gauge('activity.checks_results_passive', self.nb_checks_results_passive)

        statsmgr.gauge('activity.launched_actions', self.nb_actions_launched)
        statsmgr.gauge('activity.actions_results', self.nb_actions_results)
        statsmgr.gauge('activity.actions_results_timeout', self.nb_actions_results_timeout)

        statsmgr.gauge('activity.broks', self.nb_broks)
        statsmgr.gauge('activity.external_commands', self.nb_external_commands)
        statsmgr.gauge('activity.notifications', self.nb_notifications)
        statsmgr.gauge('activity.event_handlers', self.nb_event_handlers)

        if self.my_daemon.need_dump_environment:
            _ts = time.time()
            logger.debug('I must dump my memory...')
            self.my_daemon.dump_environment()
            self.my_daemon.need_dump_environment = False
            statsmgr.timer('loop.memory_dump', time.time() - _ts)

        if self.my_daemon.need_objects_dump:
            _ts = time.time()
            logger.debug('I must dump my objects...')
            self.dump_objects()
            self.dump_config()
            self.my_daemon.need_objects_dump = False
            statsmgr.timer('loop.objects_dump', time.time() - _ts)

        _ts = time.time()
        self.hook_point('scheduler_tick')
        statsmgr.timer('loop.hook-tick', time.time() - _ts)

        if self.my_daemon.log_loop:
            elapsed_time = time.time() - self.my_daemon.start_time
            logger.debug("Check average (total) = %d checks results, %.2f checks/s",
                         self.nb_checks, self.nb_checks / elapsed_time)
        if self.nb_checks_dropped > 0 \
                or self.nb_broks_dropped > 0 or self.nb_actions_dropped > 0:
            logger.warning("We dropped %d checks, %d broks and %d actions",
                           self.nb_checks_dropped, self.nb_broks_dropped, self.nb_actions_dropped)
            statsmgr.gauge('activity.broks_dropped', self.nb_broks_dropped)
            statsmgr.gauge('activity.checks_dropped', self.nb_checks_dropped)
            statsmgr.gauge('activity.actions_dropped', self.nb_actions_dropped)
            self.nb_checks_dropped = self.nb_broks_dropped = self.nb_actions_dropped = 0
