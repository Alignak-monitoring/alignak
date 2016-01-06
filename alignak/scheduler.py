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
import time
import os
import cStringIO
import tempfile
import traceback
import cPickle
import threading
from collections import defaultdict

from alignak.external_command import ExternalCommand
from alignak.check import Check
from alignak.notification import Notification
from alignak.eventhandler import EventHandler
from alignak.brok import Brok
from alignak.downtime import Downtime
from alignak.contactdowntime import ContactDowntime
from alignak.comment import Comment
from alignak.acknowledge import Acknowledge
from alignak.log import logger
from alignak.util import average_percentile
from alignak.load import Load
from alignak.http.client import HTTPClient, HTTPEXCEPTIONS
from alignak.stats import statsmgr
from alignak.misc.common import DICT_MODATTR


class Scheduler(object):
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

        # protect this uniq list
        self.waiting_results_lock = threading.RLock()
        self.waiting_results = []  # satellites returns us results
        # and to not wait for them, we put them here and
        # use them later

        # Every N seconds we call functions like consume, del zombies
        # etc. All of theses functions are in recurrent_works with the
        # every tick to run. So must be an integer > 0
        # The order is important, so make key an int.
        # TODO: at load, change value by configuration one (like reaper time, etc)
        self.recurrent_works = {
            0: ('update_downtimes_and_comments', self.update_downtimes_and_comments, 1),
            1: ('schedule', self.schedule, 1),  # just schedule
            2: ('consume_results', self.consume_results, 1),  # incorporate checks and dependencies

            # now get the news actions (checks, notif) raised
            3: ('get_new_actions', self.get_new_actions, 1),
            4: ('get_new_broks', self.get_new_broks, 1),  # and broks
            5: ('scatter_master_notifications', self.scatter_master_notifications, 1),
            6: ('delete_zombie_checks', self.delete_zombie_checks, 1),
            7: ('delete_zombie_actions', self.delete_zombie_actions, 1),
            # 3: (self.delete_unwanted_notifications, 1),
            8: ('check_freshness', self.check_freshness, 10),
            9: ('clean_caches', self.clean_caches, 1),
            10: ('update_retention_file', self.update_retention_file, 3600),
            11: ('check_orphaned', self.check_orphaned, 60),
            # For NagVis like tools: update our status every 10s
            12: ('get_and_register_update_program_status_brok',
                 self.get_and_register_update_program_status_brok, 10),
            # Check for system time change. And AFTER get new checks
            # so they are changed too.
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
        }

        # stats part
        self.nb_checks_send = 0
        self.nb_actions_send = 0
        self.nb_broks_send = 0
        self.nb_check_received = 0

        # Log init
        # pylint: disable=E1101
        logger.load_obj(self)

        self.instance_id = 0  # Temporary set. Will be erase later

        # Ours queues
        self.checks = {}
        self.actions = {}
        self.downtimes = {}
        self.contact_downtimes = {}
        self.comments = {}
        self.broks = {}

        # Some flags
        self.has_full_broks = False  # have a initial_broks in broks queue?
        self.need_dump_memory = False  # set by signal 1
        self.need_objects_dump = False  # set by signal 2

        # And a dummy push flavor
        self.push_flavor = 0

        # Now fake initialize for our satellites
        self.brokers = {}
        self.pollers = {}
        self.reactionners = {}

    def reset(self):
        """Reset scheduler::

        * Remove waiting results
        * Clear check, actions, downtimes, comments, broks lists

        :return: None
        """
        self.must_run = True
        with self.waiting_results_lock:
            del self.waiting_results[:]
        for obj in self.checks, self.actions, self.downtimes,\
                self.contact_downtimes, self.comments,\
                self.broks, self.brokers:
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

        :param conf: configuration to laod
        :type conf: alignak.objects.config.Config
        :return: None
        """
        self.program_start = int(time.time())
        self.conf = conf
        self.hostgroups = conf.hostgroups
        self.services = conf.services
        # We need reversed list for search in the retention
        # file read
        self.services.optimize_service_search(conf.hosts)
        self.hosts = conf.hosts

        self.notificationways = conf.notificationways
        self.checkmodulations = conf.checkmodulations
        self.macromodulations = conf.macromodulations
        self.contacts = conf.contacts
        self.contactgroups = conf.contactgroups
        self.servicegroups = conf.servicegroups
        self.timeperiods = conf.timeperiods
        self.commands = conf.commands
        self.triggers = conf.triggers
        self.triggers.compile()
        self.triggers.load_objects(self)

        # self.status_file = StatusFile(self)
        #  External status file
        # From Arbiter. Use for Broker to differentiate schedulers
        self.instance_id = conf.instance_id
        # Tag our hosts with our instance_id
        for host in self.hosts:
            host.instance_id = conf.instance_id
        for serv in self.services:
            serv.instance_id = conf.instance_id
        # self for instance_name
        self.instance_name = conf.instance_name
        # and push flavor
        self.push_flavor = conf.push_flavor

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
            (name, fun, old_tick) = self.recurrent_works[key]
            if name == f_name:
                logger.debug("Changing the tick to %d for the function %s", new_tick, name)
                self.recurrent_works[key] = (name, fun, new_tick)

    def load_satellites(self, pollers, reactionners):
        """Setter for pollers and reactionners attributes

        :param pollers: pollers value to set
        :type pollers:
        :param reactionners: reactionners value to set
        :type reactionners:
        :return: None
        """
        self.pollers = pollers
        self.reactionners = reactionners

    def die(self):
        """Set must_run attribute to False

        :return: None
        """
        self.must_run = False

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
                         (chk._id, chk.status, chk.t_to_go, chk.poller_tag, chk.command, chk.worker)
                file_h.write(string)
            for act in self.actions.values():
                string = '%s: %s:%s:%s:%s:%s:%s\n' % \
                    (act.__class__.my_type.upper(), act._id, act.status,
                     act.t_to_go, act.reactionner_tag, act.command, act.worker)
                file_h.write(string)
            for brok in self.broks.values():
                string = 'BROK: %s:%s\n' % (brok._id, brok.type)
                file_h.write(string)
            file_h.close()
        except Exception, exp:
            logger.error("Error in writing the dump file %s : %s", path, str(exp))

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
        except Exception, exp:
            logger.error("Error in writing the dump file %s : %s", path, str(exp))

    def load_external_command(self, ecm):
        """Setter for external_command attribute

        :param ecm: new value
        :type ecm: alignak.external_command.ExternalCommandManager
        :return: None
        """
        self.external_command = ecm

    def run_external_commands(self, cmds):
        """Run external commands Arbiter/Receiver sent

        :param cmds: commands to run
        :type cmds: list
        :return: None
        """
        for command in cmds:
            self.run_external_command(command)

    def run_external_command(self, command):
        """Run a single external command

        :param command: command line to run
        :type command: str
        :return: None
        """
        logger.debug("scheduler resolves command '%s'", command)
        ext_cmd = ExternalCommand(command)
        self.external_command.resolve_command(ext_cmd)

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
        # Maybe it's just for one broker
        if bname:
            broks = self.brokers[bname]['broks']
            broks[brok._id] = brok
        else:
            # If there are known brokers, give it to them
            if len(self.brokers) > 0:
                # Or maybe it's for all
                for bname in self.brokers:
                    broks = self.brokers[bname]['broks']
                    broks[brok._id] = brok
            else:  # no brokers? maybe at startup for logs
                # we will put in global queue, that the first broker
                # connection will get all
                self.broks[brok._id] = brok

    def add_notification(self, notif):
        """Add a notification into actions list

        :param notif: notification to add
        :type notif: alignak.notification.Notification
        :return: None
        """
        self.actions[notif._id] = notif
        # A notification ask for a brok
        if notif.contact is not None:
            brok = notif.get_initial_status_brok()
            self.add(brok)

    def add_check(self, check):
        """Add a check into checks list

        :param check: check to add
        :type check: alignak.check.Check
        :return: None
        """
        self.checks[check._id] = check
        # A new check means the host/service changes its next_check
        # need to be refreshed
        brok = check.ref.get_next_schedule_brok()
        self.add(brok)

    def add_eventhandler(self, action):
        """Add a event handler into actions list

        :param action: event handler to add
        :type action: alignak.eventhandler.EventHandler
        :return: None
        """
        # print "Add an event Handler", elt._id
        self.actions[action._id] = action

    def add_downtime(self, downtime):
        """Add a downtime into downtimes list

        :param downtime: downtime to add
        :type downtime: alignak.downtime.Downtime
        :return: None
        """
        self.downtimes[downtime._id] = downtime
        if downtime.extra_comment:
            self.add_comment(downtime.extra_comment)

    def add_contactdowntime(self, contact_dt):
        """Add a contact downtime into contact_downtimes list

        :param contact_dt: contact downtime to add
        :type contact_dt: alignak.contactdowntime.ContactDowntime
        :return: None
        """
        self.contact_downtimes[contact_dt._id] = contact_dt

    def add_comment(self, comment):
        """Add a comment into comments list

        :param comment: comment to add
        :type comment: alignak.comment.Comment
        :return: None
        """
        self.comments[comment._id] = comment
        brok = comment.ref.get_update_status_brok()
        self.add(brok)

    def add_externalcommand(self, ext_cmd):
        """Resolve external command

        :param ext_cmd: extermal command to run
        :type excmd: alignak.external_command.ExternalCommand
        :return: None
        """
        self.external_command.resolve_command(ext_cmd)

    def add(self, elt):
        """Generic function to add objects into scheduler internal lists::

        Brok -> self.broks
        Check -> self.checks
        Notification -> self.actions
        Downtime -> self.downtimes
        ContactDowntime -> self.contact_downtimes

        :param elt: element to add
        :type elt:
        :return: None
        """
        fun = self.__add_actions.get(elt.__class__, None)
        if fun:
            # print("found action for %s: %s" % (elt.__class__.__name__, f.__name__))
            fun(self, elt)
        else:
            logger.warning(
                "self.add(): Unmanaged object class: %s (object=%r)",
                elt.__class__, elt
            )

    __add_actions = {
        Check:              add_check,
        Brok:               add_brok,
        Notification:       add_notification,
        EventHandler:       add_eventhandler,
        Downtime:           add_downtime,
        ContactDowntime:    add_contactdowntime,
        Comment:            add_comment,
        ExternalCommand:    add_externalcommand,
    }

    def hook_point(self, hook_name):
        """Generic function to call modules methods if such method is avalaible

        :param hook_name: function name to call
        :type hook_name: str
        :return:None
        TODO: find a way to merge this and the version in daemon.py
        """
        for inst in self.sched_daemon.modules_manager.instances:
            full_hook_name = 'hook_' + hook_name
            logger.debug("hook_point: %s: %s %s",
                         inst.get_name(), str(hasattr(inst, full_hook_name)), hook_name)

            if hasattr(inst, full_hook_name):
                fun = getattr(inst, full_hook_name)
                try:
                    fun(self)
                except Exception, exp:
                    logger.error("The instance %s raise an exception %s."
                                 "I disable it and set it to restart it later",
                                 inst.get_name(), str(exp))
                    output = cStringIO.StringIO()
                    traceback.print_exc(file=output)
                    logger.error("Exception trace follows: %s", output.getvalue())
                    output.close()
                    self.sched_daemon.modules_manager.set_to_restart(inst)

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
        if len(self.checks) > max_checks:
            # keys does not ensure sorted keys. Max is slow but we have no other way.
            id_max = max(self.checks.keys())
            to_del_checks = [c for c in self.checks.values() if c._id < id_max - max_checks]
            nb_checks_drops = len(to_del_checks)
            if nb_checks_drops > 0:
                logger.info("I have to del some checks (%d)..., sorry", nb_checks_drops)
            for chk in to_del_checks:
                c_id = chk._id
                elt = chk.ref
                # First remove the link in host/service
                elt.remove_in_progress_check(chk)
                # Then in dependent checks (I depend on, or check
                # depend on me)
                for dependent_checks in chk.depend_on_me:
                    dependent_checks.depend_on.remove(chk._id)
                for c_temp in chk.depend_on:
                    c_temp.depen_on_me.remove(chk)
                del self.checks[c_id]  # Final Bye bye ...
        else:
            nb_checks_drops = 0

        # For broks and actions, it's more simple
        # or brosk, manage global but also all brokers queue
        b_lists = [self.broks]
        for (bname, elem) in self.brokers.iteritems():
            b_lists.append(elem['broks'])
        for broks in b_lists:
            if len(broks) > max_broks:
                id_max = max(broks.keys())
                id_to_del_broks = [c_id for c_id in broks if c_id < id_max - max_broks]
                nb_broks_drops = len(id_to_del_broks)
                for c_id in id_to_del_broks:
                    del broks[c_id]
            else:
                nb_broks_drops = 0

        if len(self.actions) > max_actions:
            id_max = max(self.actions.keys())
            id_to_del_actions = [c_id for c_id in self.actions if c_id < id_max - max_actions]
            nb_actions_drops = len(id_to_del_actions)
            for c_id in id_to_del_actions:
                # Remember to delete reference of notification in service/host
                act = self.actions[c_id]
                if act.is_a == 'notification':
                    act.ref.remove_in_progress_notification(act)
                del self.actions[c_id]
        else:
            nb_actions_drops = 0

        if nb_checks_drops != 0 or nb_broks_drops != 0 or nb_actions_drops != 0:
            logger.warning("We drop %d checks, %d broks and %d actions",
                           nb_checks_drops, nb_broks_drops, nb_actions_drops)

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

    def del_downtime(self, dt_id):
        """Delete a downtime

        :param dt_id: downtime id to delete
        :type dt_id: int
        :return: None
        """
        if dt_id in self.downtimes:
            self.downtimes[dt_id].ref.del_downtime(dt_id)
            del self.downtimes[dt_id]

    def del_contact_downtime(self, dt_id):
        """Delete a contact downtime

        :param dt_id: contact downtime id to delete
        :type dt_id: int
        :return: None
        """
        if dt_id in self.contact_downtimes:
            self.contact_downtimes[dt_id].ref.del_downtime(dt_id)
            del self.contact_downtimes[dt_id]

    def del_comment(self, c_id):
        """Delete a comment

        :param c_id: comment id to delete
        :type c_id: int
        :return: None
        """
        if c_id in self.comments:
            self.comments[c_id].ref.del_comment(c_id)
            del self.comments[c_id]

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
                elt.update_business_impact_value()
                new = elt.business_impact
                # Ok, the business_impact change, we can update the broks
                if new != was:
                    # print "The elements", i.get_name(), "change it's business_impact value"
                    self.get_and_register_status_brok(elt)

        # When all impacts and classic elements are updated,
        # we can update problems (their value depend on impacts, so
        # they must be done after)
        for elt in self.iter_hosts_and_services():
            # We first update impacts and classic elements
            if elt.is_problem:
                was = elt.business_impact
                elt.update_business_impact_value()
                new = elt.business_impact
                # Maybe one of the impacts change it's business_impact to a high value
                # and so ask for the problem to raise too
                if new != was:
                    # print "The elements", i.get_name(),
                    # print "change it's business_impact value from", was, "to", new
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
                if not act.contact:
                    # This is a "master" notification created by create_notifications.
                    # It wont sent itself because it has no contact.
                    # We use it to create "child" notifications (for the contacts and
                    # notification_commands) which are executed in the reactionner.
                    item = act.ref
                    childnotifications = []
                    if not item.notification_is_blocked_by_item(act.type, now):
                        # If it is possible to send notifications
                        # of this type at the current time, then create
                        # a single notification for each contact of this item.
                        childnotifications = item.scatter_notification(act)
                        for notif in childnotifications:
                            notif.status = 'scheduled'
                            self.add(notif)  # this will send a brok

                    # If we have notification_interval then schedule
                    # the next notification (problems only)
                    if act.type == 'PROBLEM':
                        # Update the ref notif number after raise the one of the notification
                        if len(childnotifications) != 0:
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
                            act.t_to_go = item.get_next_notification_time(act)

                            act.notif_nb = item.current_notification_number + 1
                            act.status = 'scheduled'
                        else:
                            # Wipe out this master notification. One problem notification is enough.
                            item.remove_in_progress_notification(act)
                            self.actions[act._id].status = 'zombie'

                    else:
                        # Wipe out this master notification.
                        # We don't repeat recover/downtime/flap/etc...
                        item.remove_in_progress_notification(act)
                        self.actions[act._id].status = 'zombie'

    def get_to_run_checks(self, do_checks=False, do_actions=False,
                          poller_tags=['None'], reactionner_tags=['None'],
                          worker_name='none', module_types=['fork']
                          ):
        """Get actions/checks for reactionner/poller
        Called by poller to get checks
        Can get checks and actions (notifications and co)

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

        # If poller want to do checks
        if do_checks:
            for chk in self.checks.values():
                #  If the command is untagged, and the poller too, or if both are tagged
                #  with same name, go for it
                # if do_check, call for poller, and so poller_tags by default is ['None']
                # by default poller_tag is 'None' and poller_tags is ['None']
                # and same for module_type, the default is the 'fork' type
                if chk.poller_tag in poller_tags and chk.module_type in module_types:
                    # must be ok to launch, and not an internal one (business rules based)
                    if chk.status == 'scheduled' and chk.is_launchable(now) and not chk.internal:
                        chk.status = 'inpoller'
                        chk.worker = worker_name
                        # We do not send c, because it is a link (c.ref) to
                        # host/service and poller do not need it. It only
                        # need a shell with id, command and defaults
                        # parameters. It's the goal of copy_shell
                        res.append(chk.copy_shell())

        # If reactionner want to notify too
        if do_actions:
            for act in self.actions.values():
                is_master = (act.is_a == 'notification' and not act.contact)

                if not is_master:
                    # if do_action, call the reactionner,
                    # and so reactionner_tags by default is ['None']
                    # by default reactionner_tag is 'None' and reactionner_tags is ['None'] too
                    # So if not the good one, loop for next :)
                    if act.reactionner_tag not in reactionner_tags:
                        continue

                    # same for module_type
                    if act.module_type not in module_types:
                        continue

                # And now look for can launch or not :)
                if act.status == 'scheduled' and act.is_launchable(now):
                    if not is_master:
                        # This is for child notifications and eventhandlers
                        act.status = 'inpoller'
                        act.worker = worker_name
                        new_a = act.copy_shell()
                        res.append(new_a)
        return res

    def put_results(self, action):
        """Get result from pollers/reactionners (actives ones)

        :param action: check / action / eventhandler to handle
        :type action:
        :return: None
        """
        if action.is_a == 'notification':
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

                self.actions[action._id].get_return_from(action)
                item = self.actions[action._id].ref
                item.remove_in_progress_notification(action)
                self.actions[action._id].status = 'zombie'
                item.last_notification = action.check_time

                # And we ask the item to update it's state
                self.get_and_register_status_brok(item)

                # If we' ve got a problem with the notification, raise a Warning log
                if timeout:
                    logger.warning("Contact %s %s notification command '%s ' "
                                   "timed out after %d seconds",
                                   self.actions[action._id].contact.contact_name,
                                   self.actions[action._id].ref.__class__.my_type,
                                   self.actions[action._id].command,
                                   int(execution_time))
                elif action.exit_status != 0:
                    logger.warning("The notification command '%s' raised an error "
                                   "(exit code=%d): '%s'",
                                   action.command, action.exit_status, action.output)

            except KeyError, exp:  # bad number for notif, not that bad
                logger.warning('put_results:: get unknown notification : %s ', str(exp))

            except AttributeError, exp:  # bad object, drop it
                logger.warning('put_results:: get bad notification : %s ', str(exp))
        elif action.is_a == 'check':
            try:
                if action.status == 'timeout':
                    action.output = "(%s Check Timed Out)" %\
                                    self.checks[action._id].ref.__class__.my_type.capitalize()
                    action.long_output = action.output
                    action.exit_status = self.conf.timeout_exit_status
                self.checks[action._id].get_return_from(action)
                self.checks[action._id].status = 'waitconsume'
            except KeyError, exp:
                pass

        elif action.is_a == 'eventhandler':
            try:
                old_action = self.actions[action._id]
                old_action.status = 'zombie'
            except KeyError:  # cannot find old action
                return
            if action.status == 'timeout':
                _type = 'event handler'
                if action.is_snapshot:
                    _type = 'snapshot'
                logger.warning("%s %s command '%s ' timed out after %d seconds",
                               self.actions[action._id].ref.__class__.my_type.capitalize(),
                               _type,
                               self.actions[action._id].command,
                               int(action.execution_time))

            # If it's a snapshot we should get the output an export it
            if action.is_snapshot:
                old_action.get_return_from(action)
                brok = old_action.ref.get_snapshot_brok(old_action.output, old_action.exit_status)
                self.add(brok)
        else:
            logger.error("The received result type in unknown! %s", str(action.is_a))

    def get_links_from_type(self, s_type):
        """Get poller link or reactionner link depending on the wanted type

        :param s_type: type we want
        :type s_type: str
        :return: links wanted
        :rtype: alignak.objects.pollerlink.PollerLinks |
                alignak.objects.reactionnerlink.ReactionnerLinks | None
        """
        t_dict = {'poller': self.pollers, 'reactionner': self.reactionners}
        if s_type in t_dict:
            return t_dict[s_type]
        return None

    def is_connection_try_too_close(self, elt):
        """Check if last connection was too early for element

        :param elt: element to check
        :type elt:
        :return: True if  now - last_connection < 5, False otherwise
        :rtype: bool
        """
        now = time.time()
        last_connection = elt['last_connection']
        if now - last_connection < 5:
            return True
        return False

    def pynag_con_init(self, s_id, s_type='poller'):
        """Init or reinit connection to a poller or reactionner
        Used for passive daemons

        :param s_id: daemon s_id to connect to
        :type s_id: int
        :param s_type: daemon type to connect to
        :type s_type: str
        :return: None
        """
        # Get good links tab for looping..
        links = self.get_links_from_type(s_type)
        if links is None:
            logger.debug("Unknown '%s' type for connection!", s_type)
            return

        # We want only to initiate connections to the passive
        # pollers and reactionners
        passive = links[s_id]['passive']
        if not passive:
            return

        # If we try to connect too much, we slow down our tests
        if self.is_connection_try_too_close(links[s_id]):
            return

        # Ok, we can now update it
        links[s_id]['last_connection'] = time.time()

        logger.debug("Init connection with %s", links[s_id]['uri'])

        uri = links[s_id]['uri']
        try:
            links[s_id]['con'] = HTTPClient(uri=uri, strong_ssl=links[s_id]['hard_ssl_name_check'])
            con = links[s_id]['con']
        except HTTPEXCEPTIONS, exp:
            logger.warning("Connection problem to the %s %s: %s",
                           s_type, links[s_id]['name'], str(exp))
            links[s_id]['con'] = None
            return

        try:
            # initial ping must be quick
            con.get('ping')
        except HTTPEXCEPTIONS, exp:
            logger.warning("Connection problem to the %s %s: %s",
                           s_type, links[s_id]['name'], str(exp))
            links[s_id]['con'] = None
            return
        except KeyError, exp:
            logger.warning("The %s '%s' is not initialized: %s",
                           s_type, links[s_id]['name'], str(exp))
            links[s_id]['con'] = None
            return

        logger.info("Connection OK to the %s %s", s_type, links[s_id]['name'])

    def push_actions_to_passives_satellites(self):
        """Send actions/checks to passive poller/reactionners

        :return: None
        """
        # We loop for our passive pollers or reactionners
        for poll in self.pollers.values():
            if not poll['passive']:
                continue
            logger.debug("I will send actions to the poller %s", str(poll))
            con = poll['con']
            poller_tags = poll['poller_tags']
            if con is not None:
                # get actions
                lst = self.get_to_run_checks(True, False, poller_tags, worker_name=poll['name'])
                try:
                    # initial ping must be quick
                    logger.debug("Sending %s actions", len(lst))
                    con.post('push_actions', {'actions': lst, 'sched_id': self.instance_id})
                    self.nb_checks_send += len(lst)
                except HTTPEXCEPTIONS, exp:
                    logger.warning("Connection problem to the %s %s: %s",
                                   type, poll['name'], str(exp))
                    poll['con'] = None
                    return
                except KeyError, exp:
                    logger.warning("The %s '%s' is not initialized: %s",
                                   type, poll['name'], str(exp))
                    poll['con'] = None
                    return
            else:  # no connection? try to reconnect
                self.pynag_con_init(poll['instance_id'], s_type='poller')

        # TODO:factorize
        # We loop for our passive reactionners
        for poll in self.reactionners.values():
            if not poll['passive']:
                continue
            logger.debug("I will send actions to the reactionner %s", str(poll))
            con = poll['con']
            reactionner_tags = poll['reactionner_tags']
            if con is not None:
                # get actions
                lst = self.get_to_run_checks(False, True,
                                             reactionner_tags=reactionner_tags,
                                             worker_name=poll['name'])
                try:
                    # initial ping must be quick
                    logger.debug("Sending %d actions", len(lst))
                    con.post('push_actions', {'actions': lst, 'sched_id': self.instance_id})
                    self.nb_checks_send += len(lst)
                except HTTPEXCEPTIONS, exp:
                    logger.warning("Connection problem to the %s %s: %s",
                                   type, poll['name'], str(exp))
                    poll['con'] = None
                    return
                except KeyError, exp:
                    logger.warning("The %s '%s' is not initialized: %s",
                                   type, poll['name'], str(exp))
                    poll['con'] = None
                    return
            else:  # no connection? try to reconnect
                self.pynag_con_init(poll['instance_id'], s_type='reactionner')

    def get_actions_from_passives_satellites(self):
        """Get actions/checks results from passive poller/reactionners

        :return: None
        """
        # We loop for our passive pollers
        for poll in [p for p in self.pollers.values() if p['passive']]:
            logger.debug("I will get actions from the poller %s", str(poll))
            con = poll['con']
            poller_tags = poll['poller_tags']
            if con is not None:
                try:
                    # initial ping must be quick
                    # Before ask a call that can be long, do a simple ping to be sure it is alive
                    con.get('ping')
                    results = con.get('get_returns', {'sched_id': self.instance_id}, wait='long')
                    try:
                        results = str(results)
                    except UnicodeEncodeError:  # ascii not working, switch to utf8 so
                        # if not eally utf8 will be a real problem
                        results = results.encode("utf8", 'ignore')
                        # and data will be invalid, socatch by the pickle.

                    # now go the cpickle pass, and catch possible errors from it
                    try:
                        results = cPickle.loads(results)
                    except Exception, exp:
                        logger.error('Cannot load passive results from satellite %s : %s',
                                     poll['name'], str(exp))
                        continue

                    nb_received = len(results)
                    self.nb_check_received += nb_received
                    logger.debug("Received %d passive results", nb_received)
                    for result in results:
                        result.set_type_passive()
                    with self.waiting_results_lock:
                        self.waiting_results.extend(results)
                except HTTPEXCEPTIONS, exp:
                    logger.warning("Connection problem to the %s %s: %s",
                                   type, poll['name'], str(exp))
                    poll['con'] = None
                    continue
                except KeyError, exp:
                    logger.warning("The %s '%s' is not initialized: %s",
                                   type, poll['name'], str(exp))
                    poll['con'] = None
                    continue
            else:  # no connection, try reinit
                self.pynag_con_init(poll['instance_id'], s_type='poller')

        # We loop for our passive reactionners
        for poll in [poll for poll in self.reactionners.values() if poll['passive']]:
            logger.debug("I will get actions from the reactionner %s", str(poll))
            con = poll['con']
            reactionner_tags = poll['reactionner_tags']
            if con is not None:
                try:
                    # initial ping must be quick
                    # Before ask a call that can be long, do a simple ping to be sure it is alive
                    con.get('ping')
                    results = con.get('get_returns', {'sched_id': self.instance_id}, wait='long')
                    results = cPickle.loads(str(results))
                    nb_received = len(results)
                    self.nb_check_received += nb_received
                    logger.debug("Received %d passive results", nb_received)
                    for result in results:
                        result.set_type_passive()
                    with self.waiting_results_lock:
                        self.waiting_results.extend(results)
                except HTTPEXCEPTIONS, exp:
                    logger.warning("Connection problem to the %s %s: %s",
                                   type, poll['name'], str(exp))
                    poll['con'] = None
                    return
                except KeyError, exp:
                    logger.warning("The %s '%s' is not initialized: %s",
                                   type, poll['name'], str(exp))
                    poll['con'] = None
                    return
            else:  # no connection, try reinit
                self.pynag_con_init(poll['instance_id'], s_type='reactionner')

    def manage_internal_checks(self):
        """Run internal checks

        :return: None
        """
        now = time.time()
        for chk in self.checks.values():
            # must be ok to launch, and not an internal one (business rules based)
            if chk.internal and chk.status == 'scheduled' and chk.is_launchable(now):
                chk.ref.manage_internal_check(self.hosts, self.services, chk)
                # it manage it, now just ask to consume it
                # like for all checks
                chk.status = 'waitconsume'

    def get_broks(self, bname):
        """Send broks to a specific broker

        :param bname: broker name to send broks
        :type bname: str
        :return: list of brok for this broker
        :rtype: list[alignak.brok.Brok]
        """
        # If we are here, we are sure the broker entry exists
        res = self.brokers[bname]['broks']
        # They are gone, we keep none!
        self.brokers[bname]['broks'] = {}

        # Also put in the result the possible first log broks if so
        res.update(self.broks)
        # and clean the global broks too now
        self.broks.clear()

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

        :param forced: if update forced?
        :type forced: bool
        :return: None
        """
        self.hook_point('load_retention')

    def get_retention_data(self):
        """Get all host and service data in order to store it after
        The module is in charge of that

        :return: dict containing host and service data
        :rtype: dict
        """
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
            all_data['hosts'][host.host_name] = h_dict

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
            all_data['services'][(serv.host.host_name, serv.service_description)] = s_dict
        return all_data

    def restore_retention_data(self, data):
        """Restore retention data

        Data coming from retention will override data coming from configuration
        It is kinda confusing when you modify an attribute (external command) and it get saved
        by retention

        :param data:
        :type data:
        :return: None
        """

        ret_hosts = data['hosts']
        for ret_h_name in ret_hosts:
            # We take the dict of our value to load
            h_dict = data['hosts'][ret_h_name]
            host = self.hosts.find_by_name(ret_h_name)
            if host is not None:
                # First manage all running properties
                running_properties = host.__class__.running_properties
                for prop, entry in running_properties.items():
                    if entry.retention:
                        # Maybe the saved one was not with this value, so
                        # we just bypass this
                        if prop in h_dict:
                            setattr(host, prop, h_dict[prop])
                # Ok, some are in properties too (like active check enabled
                # or not. Will OVERRIDE THE CONFIGURATION VALUE!
                properties = host.__class__.properties
                for prop, entry in properties.items():
                    if entry.retention:
                        # Maybe the saved one was not with this value, so
                        # we just bypass this
                        if prop in h_dict:
                            setattr(host, prop, h_dict[prop])
                # Now manage all linked objects load from previous run
                for notif in host.notifications_in_progress.values():
                    notif.ref = host
                    self.add(notif)
                    # Also raises the action id, so do not overlap ids
                    notif.assume_at_least_id(notif._id)
                host.update_in_checking()
                # And also add downtimes and comments
                for downtime in host.downtimes:
                    downtime.ref = host
                    if hasattr(downtime, 'extra_comment'):
                        downtime.extra_comment.ref = host
                    else:
                        downtime.extra_comment = None
                    # raises the downtime id to do not overlap
                    Downtime._id = max(Downtime._id, downtime._id + 1)
                    self.add(downtime)
                for comm in host.comments:
                    comm.ref = host
                    self.add(comm)
                    # raises comment id to do not overlap ids
                    Comment._id = max(Comment._id, comm._id + 1)
                if host.acknowledgement is not None:
                    host.acknowledgement.ref = host
                    # Raises the id of future ack so we don't overwrite
                    # these one
                    Acknowledge._id = max(Acknowledge._id, host.acknowledgement._id + 1)
                # Relink the notified_contacts as a set() of true contacts objects
                # it it was load from the retention, it's now a list of contacts
                # names
                if 'notified_contacts' in h_dict:
                    new_notified_contacts = set()
                    for cname in host.notified_contacts:
                        comm = self.contacts.find_by_name(cname)
                        # Maybe the contact is gone. Skip it
                        if comm:
                            new_notified_contacts.add(comm)
                    host.notified_contacts = new_notified_contacts

        # SAme for services
        ret_services = data['services']
        for (ret_s_h_name, ret_s_desc) in ret_services:
            # We take our dict to load
            s_dict = data['services'][(ret_s_h_name, ret_s_desc)]
            serv = self.services.find_srv_by_name_and_hostname(ret_s_h_name, ret_s_desc)

            if serv is not None:
                # Load the major values from running properties
                running_properties = serv.__class__.running_properties
                for prop, entry in running_properties.items():
                    if entry.retention:
                        # Maybe the saved one was not with this value, so
                        # we just bypass this
                        if prop in s_dict:
                            setattr(serv, prop, s_dict[prop])
                # And some others from properties dict too
                properties = serv.__class__.properties
                for prop, entry in properties.items():
                    if entry.retention:
                        # Maybe the saved one was not with this value, so
                        # we just bypass this
                        if prop in s_dict:
                            setattr(serv, prop, s_dict[prop])
                # Ok now manage all linked objects
                for notif in serv.notifications_in_progress.values():
                    notif.ref = serv
                    self.add(notif)
                    # Also raises the action id, so do not overlap id
                    notif.assume_at_least_id(notif._id)
                serv.update_in_checking()
                # And also add downtimes and comments
                for downtime in serv.downtimes:
                    downtime.ref = serv
                    if hasattr(downtime, 'extra_comment'):
                        downtime.extra_comment.ref = serv
                    else:
                        downtime.extra_comment = None
                    # raises the downtime id to do not overlap
                    Downtime._id = max(Downtime._id, downtime._id + 1)
                    self.add(downtime)
                for comm in serv.comments:
                    comm.ref = serv
                    self.add(comm)
                    # raises comment id to do not overlap ids
                    Comment._id = max(Comment._id, comm._id + 1)
                if serv.acknowledgement is not None:
                    serv.acknowledgement.ref = serv
                    # Raises the id of future ack so we don't overwrite
                    # these one
                    Acknowledge._id = max(Acknowledge._id, serv.acknowledgement._id + 1)
                # Relink the notified_contacts as a set() of true contacts objects
                # it it was load from the retention, it's now a list of contacts
                # names
                if 'notified_contacts' in s_dict:
                    new_notified_contacts = set()
                    for cname in serv.notified_contacts:
                        comm = self.contacts.find_by_name(cname)
                        # Maybe the contact is gone. Skip it
                        if comm:
                            new_notified_contacts.add(comm)
                    serv.notified_contacts = new_notified_contacts

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
        brok = Brok('clean_all_my_instance_id', {'instance_id': self.instance_id})
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
        brok = Brok('initial_broks_done', {'instance_id': self.instance_id})
        self.add_brok(brok, bname)

        # We now have all full broks
        self.has_full_broks = True

        logger.info("[%s] Created %d initial Broks for broker %s",
                    self.instance_name, len(self.brokers[bname]['broks']), bname)

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
        data = {"is_running": 1,
                "instance_id": self.instance_id,
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
                "global_host_event_handler": self.conf.global_host_event_handler,
                'global_service_event_handler': self.conf.global_service_event_handler,
                'check_external_commands': self.conf.check_external_commands,
                'check_service_freshness': self.conf.check_service_freshness,
                'check_host_freshness': self.conf.check_host_freshness,
                'command_file': self.conf.command_file
                }
        brok = Brok('program_status', data)
        return brok

    def consume_results(self):
        """Handle results waiting in waiting_results list.
        Check ref will call consume result and update their status

        :return: None
        """
        # All results are in self.waiting_results
        # We need to get them first
        with self.waiting_results_lock:
            waiting_results = self.waiting_results
            self.waiting_results = []

        for chk in waiting_results:
            self.put_results(chk)

        # Then we consume them
        # print "**********Consume*********"
        for chk in self.checks.values():
            if chk.status == 'waitconsume':
                item = chk.ref
                item.consume_result(chk)

        # All 'finished' checks (no more dep) raise checks they depends on
        for chk in self.checks.values():
            if chk.status == 'havetoresolvedep':
                for dependent_checks in chk.depend_on_me:
                    # Ok, now dependent will no more wait c
                    dependent_checks.depend_on.remove(chk._id)
                # REMOVE OLD DEP CHECK -> zombie
                chk.status = 'zombie'

        # Now, reinteger dep checks
        for chk in self.checks.values():
            if chk.status == 'waitdep' and len(chk.depend_on) == 0:
                item = chk.ref
                item.consume_result(chk)

    def delete_zombie_checks(self):
        """Remove checks that have a zombie status (usually timeouts)

        :return: None
        """
        # print "**********Delete zombies checks****"
        id_to_del = []
        for chk in self.checks.values():
            if chk.status == 'zombie':
                id_to_del.append(chk._id)
        # une petite tape dans le dos et tu t'en vas, merci...
        # *pat pat* GFTO, thks :)
        for c_id in id_to_del:
            del self.checks[c_id]  # ZANKUSEN!

    def delete_zombie_actions(self):
        """Remove actions that have a zombie status (usually timeouts)

        :return: None
        """
        # print "**********Delete zombies actions****"
        id_to_del = []
        for act in self.actions.values():
            if act.status == 'zombie':
                id_to_del.append(act._id)
        # une petite tape dans le dos et tu t'en vas, merci...
        # *pat pat* GFTO, thks :)
        for a_id in id_to_del:
            del self.actions[a_id]  # ZANKUSEN!

    def update_downtimes_and_comments(self):
        """Iter over all hosts and services::

        * Update downtime status (start / stop) regarding maintenance period
        * Register new comments in comments list

        :return: None
        """
        broks = []
        now = time.time()

        # Look for in objects comments, and look if we already got them
        for elt in self.iter_hosts_and_services():
            for comm in elt.comments:
                if comm._id not in self.comments:
                    self.comments[comm._id] = comm

        # Check maintenance periods
        for elt in self.iter_hosts_and_services():
            if elt.maintenance_period is None:
                continue

            if elt.in_maintenance is None:
                if elt.maintenance_period.is_time_valid(now):
                    start_dt = elt.maintenance_period.get_next_valid_time_from_t(now)
                    end_dt = elt.maintenance_period.get_next_invalid_time_from_t(start_dt + 1) - 1
                    downtime = Downtime(elt, start_dt, end_dt, 1, 0, 0,
                                        "system",
                                        "this downtime was automatically scheduled"
                                        "through a maintenance_period")
                    elt.add_downtime(downtime)
                    self.add(downtime)
                    self.get_and_register_status_brok(elt)
                    elt.in_maintenance = downtime._id
            else:
                if elt.in_maintenance not in self.downtimes:
                    # the main downtimes has expired or was manually deleted
                    elt.in_maintenance = None

        #  Check the validity of contact downtimes
        for elt in self.contacts:
            for downtime in elt.downtimes:
                downtime.check_activation()

        # A loop where those downtimes are removed
        # which were marked for deletion (mostly by dt.exit())
        for downtime in self.downtimes.values():
            if downtime.can_be_deleted is True:
                ref = downtime.ref
                self.del_downtime(downtime._id)
                broks.append(ref.get_update_status_brok())

        # Same for contact downtimes:
        for downtime in self.contact_downtimes.values():
            if downtime.can_be_deleted is True:
                ref = downtime.ref
                self.del_contact_downtime(downtime._id)
                broks.append(ref.get_update_status_brok())

        # Downtimes are usually accompanied by a comment.
        # An exiting downtime also invalidates it's comment.
        for comm in self.comments.values():
            if comm.can_be_deleted is True:
                ref = comm.ref
                self.del_comment(comm._id)
                broks.append(ref.get_update_status_brok())

        # Check start and stop times
        for downtime in self.downtimes.values():
            if downtime.real_end_time < now:
                # this one has expired
                broks.extend(downtime.exit())  # returns downtimestop notifications
            elif now >= downtime.start_time and downtime.fixed and not downtime.is_in_effect:
                # this one has to start now
                broks.extend(downtime.enter())  # returns downtimestart notifications
                broks.append(downtime.ref.get_update_status_brok())

        for brok in broks:
            self.add(brok)

    def schedule(self):
        """Iter over all hosts and services and call schedule method
        (schedule next check)

        :return: None
        """
        # ask for service and hosts their next check
        for elt in self.iter_hosts_and_services():
            elt.schedule()

    def get_new_actions(self):
        """Call 'get_new_actions' hook point
        Iter over all hosts and services to add new actions in internal lists

        :return: None
        """
        self.hook_point('get_new_actions')
        # ask for service and hosts their next check
        for elt in self.iter_hosts_and_services():
            for act in elt.actions:
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

    def check_freshness(self):
        """Iter over all hosts and services to check freshness

        :return: None
        """
        # print "********** Check freshness******"
        for elt in self.iter_hosts_and_services():
            chk = elt.do_check_freshness()
            if chk is not None:
                self.add(chk)

    def check_orphaned(self):
        """Check for orphaned checks/actions::

        * status == 'inpoller' and t_to_go < now - time_to_orphanage (300 by default)

        if so raise a logger warning

        :return: None
        """
        worker_names = {}
        now = int(time.time())
        for chk in self.checks.values():
            time_to_orphanage = chk.ref.get_time_to_orphanage()
            if time_to_orphanage:
                if chk.status == 'inpoller' and chk.t_to_go < now - time_to_orphanage:
                    chk.status = 'scheduled'
                    if chk.worker not in worker_names:
                        worker_names[chk.worker] = 1
                        continue
                    worker_names[chk.worker] += 1
        for act in self.actions.values():
            time_to_orphanage = act.ref.get_time_to_orphanage()
            if time_to_orphanage:
                if act.status == 'inpoller' and act.t_to_go < now - time_to_orphanage:
                    act.status = 'scheduled'
                    if act.worker not in worker_names:
                        worker_names[act.worker] = 1
                        continue
                    worker_names[act.worker] += 1

        for w_id in worker_names:
            logger.warning("%d actions never came back for the satellite '%s'."
                           "I reenable them for polling", worker_names[w_id], w_id)

    def send_broks_to_modules(self):
        """Put broks into module queues
        Only broks without sent_to_sched_externals to True are sent
        Only modules that ask for broks will get some

        :return: None
        """
        t00 = time.time()
        nb_sent = 0
        for mod in self.sched_daemon.modules_manager.get_external_instances():
            logger.debug("Look for sending to module %s", mod.get_name())
            queue = mod.to_q
            to_send = [b for b in self.broks.values()
                       if not getattr(b, 'sent_to_sched_externals', False) and mod.want_brok(b)]
            queue.put(to_send)
            nb_sent += len(to_send)

        # No more need to send them
        for brok in self.broks.values():
            brok.sent_to_sched_externals = True
        logger.debug("Time to send %s broks (after %d secs)", nb_sent, time.time() - t00)

    def get_objects_from_from_queues(self):
        """Same behavior than Daemon.get_objects_from_from_queues().

        :return:
        :rtype:
        """
        return self.sched_daemon.get_objects_from_from_queues()

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
        for chk in checks.itervalues():
            res[chk.status] += 1
        return res

    def get_stats_struct(self):
        """Get state of modules and create a scheme for stats data of daemon

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

        # Get a overview of the latencies with just
        # a 95 percentile view, but lso min/max values
        latencies = [s.latency for s in self.services]
        lat_avg, lat_min, lat_max = average_percentile(latencies)
        res['latency'] = (0.0, 0.0, 0.0)
        if lat_avg:
            res['latency'] = {'avg': lat_avg, 'min': lat_min, 'max': lat_max}

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

        for what in ('downtimes', 'comments'):
            metrics.append('scheduler.%s.%s %d %d' % (
                self.instance_name, what, len(getattr(self, what)), now))

        if lat_min:
            metrics.append('scheduler.%s.latency.min %f %d' % (self.instance_name, lat_min, now))
            metrics.append('scheduler.%s.latency.avg %f %d' % (self.instance_name, lat_avg, now))
            metrics.append('scheduler.%s.latency.max %f %d' % (self.instance_name, lat_max, now))

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
        # takethe first 10 ones for the put
        res['commands'] = stats[:10]
        return res

    def run(self):
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
        self.schedule()
        logger.info("[%s] First scheduling done", self.instance_name)

        # Now connect to the passive satellites if needed
        for p_id in self.pollers:
            self.pynag_con_init(p_id, s_type='poller')

        for r_id in self.reactionners:
            self.pynag_con_init(r_id, s_type='reactionner')

        # Ticks are for recurrent function call like consume
        # del zombies etc
        ticks = 0
        timeout = 1.0  # For the select

        gogogo = time.time()

        # We must reset it if we received a new conf from the Arbiter.
        # Otherwise, the stat check average won't be correct
        self.nb_check_received = 0

        self.load_one_min = Load(initial_value=1)
        logger.debug("First loop at %d", time.time())
        while self.must_run:
            # print "Loop"
            # Before answer to brokers, we send our broks to modules
            # Ok, go to send our broks to our external modules
            # self.send_broks_to_modules()

            # This is basically sleep(timeout) and returns 0, [], int
            # We could only paste here only the code "used" but it could be
            # harder to maintain.
            _ = self.sched_daemon.handle_requests(timeout)

            self.load_one_min.update_load(self.sched_daemon.sleep_time)

            # load of the scheduler is the percert of time it is waiting
            load = min(100, 100.0 - self.load_one_min.get_load() * 100)
            logger.debug("Load: (sleep) %.2f (average: %.2f) -> %d%%",
                         self.sched_daemon.sleep_time, self.load_one_min.get_load(), load)

            self.sched_daemon.sleep_time = 0.0

            # Timeout or time over
            ticks += 1

            # Do recurrent works like schedule, consume
            # delete_zombie_checks
            for i in self.recurrent_works:
                (name, fun, nb_ticks) = self.recurrent_works[i]
                # A 0 in the tick will just disable it
                if nb_ticks != 0:
                    if ticks % nb_ticks == 0:
                        # Call it and save the time spend in it
                        _t0 = time.time()
                        fun()
                        statsmgr.incr('loop.%s' % name, time.time() - _t0)

            # DBG: push actions to passives?
            self.push_actions_to_passives_satellites()
            self.get_actions_from_passives_satellites()

            # stats
            nb_scheduled = nb_inpoller = nb_zombies = 0
            for chk in self.checks.itervalues():
                if chk.status == 'scheduled':
                    nb_scheduled += 1
                elif chk.status == 'inpoller':
                    nb_inpoller += 1
                elif chk.status == 'zombie':
                    nb_zombies += 1
            nb_notifications = len(self.actions)

            logger.debug("Checks: total %s, scheduled %s,"
                         "inpoller %s, zombies %s, notifications %s",
                         len(self.checks), nb_scheduled, nb_inpoller, nb_zombies, nb_notifications)

            # Get a overview of the latencies with just
            # a 95 percentile view, but lso min/max values
            latencies = [s.latency for s in self.services]
            lat_avg, lat_min, lat_max = average_percentile(latencies)
            if lat_avg is not None:
                logger.debug("Latency (avg/min/max): %.2f/%.2f/%.2f", lat_avg, lat_min, lat_max)

            # print "Notifications:", nb_notifications
            now = time.time()

            if self.nb_checks_send != 0:
                logger.debug("Nb checks/notifications/event send: %s", self.nb_checks_send)
            self.nb_checks_send = 0
            if self.nb_broks_send != 0:
                logger.debug("Nb Broks send: %s", self.nb_broks_send)
            self.nb_broks_send = 0

            time_elapsed = now - gogogo
            logger.debug("Check average = %d checks/s", int(self.nb_check_received / time_elapsed))

            if self.need_dump_memory:
                self.sched_daemon.dump_memory()
                self.need_dump_memory = False

            if self.need_objects_dump:
                logger.debug('I need to dump my objects!')
                self.dump_objects()
                self.dump_config()
                self.need_objects_dump = False

            self.hook_point('scheduler_tick')

        # WE must save the retention at the quit BY OURSELF
        # because our daemon will not be able to do it for us
        self.update_retention_file(True)
