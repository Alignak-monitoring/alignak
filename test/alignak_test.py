#!/usr/bin/env python
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

"""
    This file contains classes and utilities for Alignak tests modules
"""

import os
import sys

import time
import string
import re
import locale

import unittest2

import logging
from logging import Handler

import alignak
from alignak.log import DEFAULT_FORMATTER_NAMED, ROOT_LOGGER_NAME
from alignak.objects.config import Config
from alignak.objects.command import Command
from alignak.objects.module import Module

from alignak.dispatcher import Dispatcher
from alignak.scheduler import Scheduler
from alignak.macroresolver import MacroResolver
from alignak.external_command import ExternalCommandManager, ExternalCommand
from alignak.check import Check
from alignak.message import Message
from alignak.misc.serialization import serialize, unserialize
from alignak.objects.arbiterlink import ArbiterLink
from alignak.objects.schedulerlink import SchedulerLink
from alignak.objects.pollerlink import PollerLink
from alignak.objects.reactionnerlink import ReactionnerLink
from alignak.objects.brokerlink import BrokerLink
from alignak.objects.satellitelink import SatelliteLink
from alignak.notification import Notification
from alignak.modulesmanager import ModulesManager
from alignak.basemodule import BaseModule

from alignak.brok import Brok
from alignak.misc.common import DICT_MODATTR

from alignak.daemons.schedulerdaemon import Alignak
from alignak.daemons.brokerdaemon import Broker
from alignak.daemons.arbiterdaemon import Arbiter
from alignak.daemons.receiverdaemon import Receiver

class CollectorHandler(Handler):
    """
    This log handler collecting all emitted log.

    Used for tet purpose (assertion)
    """

    def __init__(self):
        Handler.__init__(self, logging.DEBUG)
        self.collector = []

    def emit(self, record):
        try:
            msg = self.format(record)
            self.collector.append(msg)
        except TypeError:
            self.handleError(record)


class AlignakTest(unittest2.TestCase):

    if sys.version_info < (2, 7):
        def assertRegex(self, *args, **kwargs):
            return self.assertRegexpMatches(*args, **kwargs)

    def setup_logger(self):
        """
        Setup a log collector
        :return:
        """
        self.logger = logging.getLogger("alignak")

        # Add collector for test purpose.
        collector_h = CollectorHandler()
        collector_h.setFormatter(DEFAULT_FORMATTER_NAMED)
        self.logger.addHandler(collector_h)

    def files_update(self, files, replacements):
        """Update files content with the defined replacements

        :param files: list of files to parse and replace
        :param replacements: list of values to replace
        :return:
        """
        for filename in files:
            lines = []
            with open(filename) as infile:
                for line in infile:
                    for src, target in replacements.iteritems():
                        line = line.replace(src, target)
                    lines.append(line)
            with open(filename, 'w') as outfile:
                for line in lines:
                    outfile.write(line)

    def setup_with_file(self, configuration_file):
        """
        Load alignak with defined configuration file

        If the configuration loading fails, a SystemExit exception is raised to the caller.

        The conf_is_correct property indicates if the configuration loading succeeded or failed.

        The configuration errors property contains a list of the error message that are normally
        logged as ERROR by the arbiter.

        @verified

        :param configuration_file: path + file name of the main configuration file
        :type configuration_file: str
        :return: None
        """
        self.broks = {}
        self.schedulers = {}
        self.brokers = {}
        self.pollers = {}
        self.receivers = {}
        self.reactionners = {}
        self.arbiter = None
        self.conf_is_correct = False
        self.configuration_warnings = []
        self.configuration_errors = []

        # Add collector for test purpose.
        self.setup_logger()

        # Initialize the Arbiter with no daemon configuration file
        configuration_dir = os.path.dirname(configuration_file)
        self.env_file = os.path.join(configuration_dir, 'alignak.ini')
        args = {
            'env_file': self.env_file,
            'alignak_name': 'arbiter-master', 'daemon_name': None,
            'daemon_enabled': False, 'do_replace': False, 'is_daemon': False,
            'config_file': None, 'debug': False, 'debug_file': None,
            'monitoring_files': [configuration_file],
            'local_log': '/tmp/arbiter.log', 'verify_only': False, 'port': None
        }
        self.arbiter = Arbiter(**args)

        try:
            # The following is copy paste from setup_alignak_logger
            # The only difference is that keep logger at INFO level to gather messages
            # This is needed to assert later on logs we received.
            self.logger.setLevel(logging.INFO)
            # Force the debug level if the daemon is said to start with such level
            if self.arbiter.debug:
                self.logger.setLevel(logging.DEBUG)

            # Log will be broks
            for line in self.arbiter.get_header():
                self.logger.info(line)

            self.arbiter.load_monitoring_config_file()

            # If this assertion does not match, then there is a bug in the arbiter :)
            self.assertTrue(self.arbiter.conf.conf_is_correct)
            self.conf_is_correct = True
            self.configuration_warnings = self.arbiter.conf.configuration_warnings
            self.configuration_errors = self.arbiter.conf.configuration_errors
        except SystemExit:
            self.configuration_warnings = self.arbiter.conf.configuration_warnings
            self.configuration_errors = self.arbiter.conf.configuration_errors
            self.show_configuration_logs()
            raise

        for arb in self.arbiter.conf.arbiters:
            if arb.get_name() == self.arbiter.arbiter_name:
                self.arbiter.myself = arb
        self.arbiter.dispatcher = Dispatcher(self.arbiter.conf, self.arbiter.myself)
        self.arbiter.dispatcher.prepare_dispatch()

        # Build schedulers dictionary with the schedulers involved in the configuration
        for scheduler in self.arbiter.dispatcher.schedulers:
            args = {
                'env_file': self.env_file,
                'alignak_name': 'arbiter-master', 'daemon_name': None,
                'daemon_enabled': False, 'do_replace': False, 'is_daemon': False,
                'config_file': None, 'debug': False, 'debug_file': None,
                'local_log': '/tmp/scheduler.log', 'port': None
            }
            sched = Alignak(**args)
            sched.load_modules_manager(scheduler.name)
            sched.new_conf = scheduler.conf_package
            if sched.new_conf:
                sched.setup_new_conf()
            self.schedulers[scheduler.scheduler_name] = sched

        # Build pollers dictionary with the pollers involved in the configuration
        for poller in self.arbiter.dispatcher.pollers:
            self.pollers[poller.poller_name] = poller

        # Build receivers dictionary with the receivers involved in the configuration
        for receiver in self.arbiter.dispatcher.receivers:
            print("Receiver: %s" % receiver)
            self.receivers[receiver.receiver_name] = receiver

        # Build reactionners dictionary with the reactionners involved in the configuration
        for reactionner in self.arbiter.dispatcher.reactionners:
            self.reactionners[reactionner.reactionner_name] = reactionner

        # Build brokers dictionary with the brokers involved in the configuration
        for broker in self.arbiter.dispatcher.brokers:
            self.brokers[broker.broker_name] = broker

        # Initialize the Receiver with no daemon configuration file
        args = {
            'env_file': self.env_file,
            'alignak_name': 'arbiter-master', 'daemon_name': None,
            'daemon_enabled': False, 'do_replace': False, 'is_daemon': False,
            'config_file': None, 'debug': False, 'debug_file': None,
            'local_log': '/tmp/receiver.log', 'port': None
        }
        self.receiver = Receiver(**args)
        # if self.arbiter.dispatcher.satellites:
        #     some_receivers = False
        #     for satellite in self.arbiter.dispatcher.satellites:
        #         if satellite.get_my_type() == 'receiver':
        #             # self.receiver.load_modules_manager(satellite.name)
        #             self.receiver.modules_manager = \
        #                 ModulesManager('receiver', self.receiver.sync_manager,
        #                                max_queue_size=getattr(self, 'max_queue_size', 0))
        #
        #             self.receiver.new_conf = satellite.cfg
        #             if self.receiver.new_conf:
        #                 self.receiver.setup_new_conf()

        # Initialize the broker with no daemon configuration file
        args = {
            'env_file': self.env_file,
            'alignak_name': 'arbiter-master', 'daemon_name': None,
            'daemon_enabled': False, 'do_replace': False, 'is_daemon': False,
            'config_file': None, 'debug': False, 'debug_file': None,
            'local_log': '/tmp/broker.log', 'port': None
        }
        self.broker = Broker(**args)

        # External commands manager default mode; default is tha pplyer (scheduler) mode
        self.ecm_mode = 'applyer'

        # Now we create an external commands manager in dispatcher mode
        self.arbiter.external_commands_manager = ExternalCommandManager(self.arbiter.conf,
                                                                        'dispatcher',
                                                                        self.arbiter,
                                                                        accept_unknown=True)

        # Now we get the external commands manager of our scheduler
        self.eca = None
        if 'scheduler-master' in self.schedulers:
            self._sched = self.schedulers['scheduler-master'].sched
            self.eca = self.schedulers['scheduler-master'].sched.external_commands_manager

        # Now we create an external commands manager in receiver mode
        self.ecr = ExternalCommandManager(None, 'receiver', self.receiver,
                                          accept_unknown=True)
        self.receiver.external_commands_manager = self.ecr

        # and an external commands manager in dispatcher mode
        self.ecd = ExternalCommandManager(self.arbiter.conf, 'dispatcher', self.arbiter,
                                          accept_unknown=True)

    def fake_check(self, ref, exit_status, output="OK"):
        """
        Simulate a check execution and result
        :param ref: host/service concerned by the check
        :param exit_status: check exit status code (0, 1, ...).
               If set to None, the check is simply scheduled but not "executed"
        :param output: check output (output + perf data)
        :return:
        """

        now = time.time()
        check = ref.schedule(self.schedulers['scheduler-master'].sched.hosts,
                             self.schedulers['scheduler-master'].sched.services,
                             self.schedulers['scheduler-master'].sched.timeperiods,
                             self.schedulers['scheduler-master'].sched.macromodulations,
                             self.schedulers['scheduler-master'].sched.checkmodulations,
                             self.schedulers['scheduler-master'].sched.checks,
                             force=True, force_time=None)
        # now the check is scheduled and we get it in the action queue
        self.schedulers['scheduler-master'].sched.add(check)  # check is now in sched.checks[]

        # Allows to force check scheduling without setting its status nor output.
        # Useful for manual business rules rescheduling, for instance.
        if exit_status is None:
            return

        # fake execution
        check.check_time = now

        # and lie about when we will launch it because
        # if not, the schedule call for ref
        # will not really reschedule it because there
        # is a valid value in the future
        ref.next_chk = now - 0.5

        # Max plugin output is default to 8192
        check.get_outputs(output, 8192)
        check.exit_status = exit_status
        check.execution_time = 0.001
        check.status = 'waitconsume'

        # Put the check result in the waiting results for the scheduler ...
        self.schedulers['scheduler-master'].sched.waiting_results.put(check)

    def scheduler_loop(self, count, items, mysched=None):
        """
        Manage scheduler checks

        @verified

        :param count: number of checks to pass
        :type count: int
        :param items: list of list [[object, exist_status, output]]
        :type items: list
        :param mysched: The scheduler
        :type mysched: None | object
        :return: None
        """
        if mysched is None:
            mysched = self.schedulers['scheduler-master']

        macroresolver = MacroResolver()
        macroresolver.init(mysched.conf)

        for num in range(count):
            for item in items:
                (obj, exit_status, output) = item
                if len(obj.checks_in_progress) == 0:
                    for i in mysched.sched.recurrent_works:
                        (name, fun, nb_ticks) = mysched.sched.recurrent_works[i]
                        if nb_ticks == 1:
                            fun()
                self.assertGreater(len(obj.checks_in_progress), 0)
                chk = mysched.sched.checks[obj.checks_in_progress[0]]
                chk.set_type_active()
                chk.check_time = time.time()
                chk.wait_time = 0.0001
                chk.last_poll = chk.check_time
                chk.output = output
                chk.exit_status = exit_status
                mysched.sched.waiting_results.put(chk)

            for i in mysched.sched.recurrent_works:
                (name, fun, nb_ticks) = mysched.sched.recurrent_works[i]
                if nb_ticks == 1:
                    # print("Execute: %s" % fun)
                    fun()

    def manage_freshness_check(self, count=1, mysched=None):
        """Run the scheduler loop for freshness_check

        :param count: number of scheduler loop turns
        :type count: int
        :param mysched: a specific scheduler to get used
        :type mysched: None | object
        :return: n/a
        """
        if mysched is None:
            mysched = self.schedulers['scheduler-master']

        # Check freshness on each scheduler tick
        mysched.sched.update_recurrent_works_tick('check_freshness', 1)

        checks = []
        for num in range(count):
            for i in mysched.sched.recurrent_works:
                (name, fun, nb_ticks) = mysched.sched.recurrent_works[i]
                if nb_ticks == 1:
                    fun()
                if name == 'check_freshness':
                    checks = sorted(mysched.sched.checks.values(),
                                    key=lambda x: x.creation_time)
                    checks = [chk for chk in checks if chk.freshness_expired]
        return len(checks)

    def manage_external_command(self, external_command, run=True):
        """Manage an external command.

        :return: result of external command resolution
        """
        ext_cmd = ExternalCommand(external_command)
        if self.ecm_mode == 'applyer':
            res = None
            self._scheduler.run_external_command(external_command)
            self.external_command_loop()
        if self.ecm_mode == 'dispatcher':
            res = self.ecd.resolve_command(ext_cmd)
            if res and run:
                self.arbiter.broks = {}
                self.arbiter.add(ext_cmd)
                self.arbiter.push_external_commands_to_schedulers()
                # Our scheduler
                self._scheduler = self.schedulers['scheduler-master'].sched
                # Our broker
                self._broker = self._scheduler.brokers['broker-master']
                for brok in self.arbiter.broks:
                    print("Brok: %s : %s" % (brok, self.arbiter.broks[brok]))
                    self._broker['broks'][brok] = self.arbiter.broks[brok]
        if self.ecm_mode == 'receiver':
            res = self.ecr.resolve_command(ext_cmd)
            if res and run:
                self.receiver.broks = {}
                self.receiver.add(ext_cmd)
                self.receiver.push_external_commands_to_schedulers()
                # Our scheduler
                self._scheduler = self.schedulers['scheduler-master'].sched
                # Our broker
                self._broker = self._scheduler.brokers['broker-master']
                for brok in self.receiver.broks:
                    print("Brok: %s : %s" % (brok, self.receiver.broks[brok]))
                    self._broker.broks[brok] = self.receiver.broks[brok]
        return res

    def external_command_loop(self):
        """Execute the scheduler actions for external commands.

        The scheduler is not an ECM 'dispatcher' but an 'applyer' ... so this function is on
        the external command execution side of the problem.

        @verified
        :return:
        """
        for i in self.schedulers['scheduler-master'].sched.recurrent_works:
            (name, fun, nb_ticks) = self.schedulers['scheduler-master'].sched.recurrent_works[i]
            if nb_ticks == 1:
                fun()
        self.assert_no_log_match("External command Brok could not be sent to any daemon!")

    def worker_loop(self, verbose=True):
        self.schedulers['scheduler-master'].sched.delete_zombie_checks()
        self.schedulers['scheduler-master'].sched.delete_zombie_actions()
        checks = self.schedulers['scheduler-master'].sched.get_to_run_checks(True, False, worker_name='tester')
        actions = self.schedulers['scheduler-master'].sched.get_to_run_checks(False, True, worker_name='tester')
        if verbose is True:
            self.show_actions()
        for a in actions:
            a.status = 'inpoller'
            a.check_time = time.time()
            a.exit_status = 0
            self.schedulers['scheduler-master'].sched.put_results(a)
        if verbose is True:
            self.show_actions()

    def launch_internal_check(self, svc_br):
        """ Launch an internal check for the business rule service provided """
        # Launch an internal check
        now = time.time()
        self._sched.add(svc_br.launch_check(now - 1, self._sched.hosts, self._sched.services,
                                            self._sched.timeperiods, self._sched.macromodulations,
                                            self._sched.checkmodulations, self._sched.checks))
        c = svc_br.actions[0]
        self.assertEqual(True, c.internal)
        self.assertTrue(c.is_launchable(now))

        # ask the scheduler to launch this check
        # and ask 2 loops: one to launch the check
        # and another to get the result
        self.scheduler_loop(2, [])

        # We should not have the check anymore
        self.assertEqual(0, len(svc_br.actions))

    def show_logs(self, scheduler=False):
        """
        Show logs. Get logs collected by the collector handler and print them

        @verified
        :param scheduler:
        :return:
        """
        print "--- logs <<<----------------------------------"
        collector_h = [hand for hand in self.logger.handlers
                       if isinstance(hand, CollectorHandler)][0]
        for log in collector_h.collector:
            self.safe_print(log)

        print "--- logs >>>----------------------------------"

    def show_actions(self):
        """"Show the inner actions"""
        self._scheduler = self.schedulers['scheduler-master'].sched

        macroresolver = MacroResolver()
        macroresolver.init(self._scheduler.conf)

        print "--- actions <<<----------------------------------"
        actions = sorted(self._scheduler.actions.values(), key=lambda x: (x.t_to_go, x.creation_time))
        for action in actions:
            print("Time to launch action: %s, creation: %s" % (action.t_to_go, action.creation_time))
            if action.is_a == 'notification':
                item = self._scheduler.find_item_by_id(action.ref)
                if item.my_type == "host":
                    ref = "host: %s" % item.get_name()
                else:
                    hst = self._scheduler.find_item_by_id(item.host)
                    ref = "svc: %s/%s" % (hst.get_name(), item.get_name())
                print "NOTIFICATION %s (%s - %s) [%s], created: %s for '%s': %s" \
                      % (action.type, action.uuid, action.status, ref,
                         time.asctime(time.localtime(action.t_to_go)), action.contact_name, action.command)
            elif action.is_a == 'eventhandler':
                print "EVENTHANDLER:", action
            else:
                print "ACTION:", action
        print "--- actions >>>----------------------------------"

    def show_checks(self):
        """
        Show checks from the scheduler
        :return:
        """
        print "--- checks <<<--------------------------------"
        checks = sorted(self.schedulers['scheduler-master'].sched.checks.values(), key=lambda x: x.creation_time)
        for check in checks:
            print("- %s" % check)
        print "--- checks >>>--------------------------------"

    def show_and_clear_logs(self):
        """
        Prints and then deletes the current logs stored in the log collector

        @verified
        :return:
        """
        self.show_logs()
        self.clear_logs()

    def show_and_clear_actions(self):
        self.show_actions()
        self.clear_actions()

    def count_logs(self):
        """
        Count the log lines in the Arbiter broks.
        If 'scheduler' is True, then uses the scheduler's broks list.

        @verified
        :return:
        """
        collector_h = [hand for hand in self.logger.handlers
                       if isinstance(hand, CollectorHandler)][0]
        return len(collector_h.collector)

    def count_actions(self):
        """
        Count the actions in the scheduler's actions.

        @verified
        :return:
        """
        return len(self.schedulers['scheduler-master'].sched.actions.values())

    def clear_logs(self):
        """
        Remove all the logs stored in the logs collector

        @verified
        :return:
        """
        collector_h = [hand for hand in self.logger.handlers
                       if isinstance(hand, CollectorHandler)][0]
        collector_h.collector = []

    def clear_actions(self):
        """
        Clear the actions in the scheduler's actions.

        @verified
        :return:
        """
        self.schedulers['scheduler-master'].sched.actions = {}

    def assert_actions_count(self, number):
        """
        Check the number of actions

        @verified

        :param number: number of actions we must have
        :type number: int
        :return: None
        """
        actions = []
        # I do this because sort take too times
        if number != len(self.schedulers['scheduler-master'].sched.actions):
            actions = sorted(self.schedulers['scheduler-master'].sched.actions.values(),
                             key=lambda x: x.creation_time)
        self.assertEqual(number, len(self.schedulers['scheduler-master'].sched.actions),
                         "Not found expected number of actions:\nactions_logs=[[[\n%s\n]]]" %
                         ('\n'.join('\t%s = creation: %s, is_a: %s, type: %s, status: %s, '
                                    'planned: %s, command: %s' %
                                    (idx, b.creation_time, b.is_a, b.type,
                                     b.status, b.t_to_go, b.command)
                                    for idx, b in enumerate(actions))))

    def assert_actions_match(self, index, pattern, field):
        """
        Check if pattern verified in field(property) name of the action with index in action list

        @verified

        :param index: index in the actions list. If index is -1, all the actions in the list are
        searched for a matching pattern
        :type index: int
        :param pattern: pattern to verify is in the action
        :type pattern: str
        :param field: name of the field (property) of the action
        :type field: str
        :return: None
        """
        regex = re.compile(pattern)
        actions = sorted(self.schedulers['scheduler-master'].sched.actions.values(),
                         key=lambda x: (x.t_to_go, x.creation_time))
        if index != -1:
            myaction = actions[index]
            self.assertTrue(regex.search(getattr(myaction, field)),
                            "Not found a matching pattern in actions:\n"
                            "index=%s field=%s pattern=%r\n"
                            "action_line=creation: %s, is_a: %s, type: %s, "
                            "status: %s, planned: %s, command: %s" % (
                                index, field, pattern, myaction.creation_time, myaction.is_a,
                                myaction.type, myaction.status, myaction.t_to_go, myaction.command))
            return

        for myaction in actions:
            if regex.search(getattr(myaction, field)):
                return

        self.assertTrue(False,
                        "Not found a matching pattern in actions:\nfield=%s pattern=%r\n" %
                        (field, pattern))

    def assert_log_match(self, pattern, index=None):
        """
        Search if the log with the index number has the pattern in the Arbiter logs.

        If index is None, then all the collected logs are searched for the pattern

        Logs numbering starts from 0 (the oldest stored log line)

        This function assert on the search result. As of it, if no log is found with th search
        criteria an assertion is raised and the test stops on error.

        :param pattern: string to search in log
        :type pattern: str
        :param index: index number
        :type index: int
        :return: None
        """
        self.assertIsNotNone(pattern, "Searched pattern can not be None!")

        collector_h = [hand for hand in self.logger.handlers
                       if isinstance(hand, CollectorHandler)][0]

        regex = re.compile(pattern)
        log_num = 0

        found = False
        for log in collector_h.collector:
            if index is None:
                if regex.search(log):
                    found = True
                    break
            elif index == log_num:
                if regex.search(log):
                    found = True
                    break
            log_num += 1

        self.assertTrue(found,
                        "Not found a matching log line in logs:\nindex=%s pattern=%r\n"
                        "logs=[[[\n%s\n]]]" % (
                            index, pattern, '\n'.join('\t%s=%s' % (idx, b.strip())
                                                      for idx, b in enumerate(collector_h.collector)
                                                      )
                            )
                        )

    def assert_checks_count(self, number):
        """
        Check the number of actions

        @verified

        :param number: number of actions we must have
        :type number: int
        :return: None
        """
        checks = sorted(self.schedulers['scheduler-master'].sched.checks.values(), key=lambda x: x.creation_time)
        self.assertEqual(number, len(checks),
                         "Not found expected number of checks:\nchecks_logs=[[[\n%s\n]]]" %
                         ('\n'.join('\t%s = creation: %s, is_a: %s, type: %s, status: %s, planned: %s, '
                                    'command: %s' %
                                    (idx, b.creation_time, b.is_a, b.type, b.status, b.t_to_go, b.command)
                                    for idx, b in enumerate(checks))))

    def assert_checks_match(self, index, pattern, field):
        """
        Check if pattern verified in field(property) name of the check with index in check list

        @verified

        :param index: index number of checks list
        :type index: int
        :param pattern: pattern to verify is in the check
        :type pattern: str
        :param field: name of the field (property) of the check
        :type field: str
        :return: None
        """
        regex = re.compile(pattern)
        checks = sorted(self.schedulers['scheduler-master'].sched.checks.values(), key=lambda x: x.creation_time)
        mycheck = checks[index]
        self.assertTrue(regex.search(getattr(mycheck, field)),
                        "Not found a matching pattern in checks:\nindex=%s field=%s pattern=%r\n"
                        "check_line=creation: %s, is_a: %s, type: %s, status: %s, planned: %s, "
                        "command: %s" % (
                            index, field, pattern, mycheck.creation_time, mycheck.is_a,
                            mycheck.type, mycheck.status, mycheck.t_to_go, mycheck.command))

    def _any_check_match(self, pattern, field, assert_not):
        """
        Search if any check matches the requested pattern

        @verified
        :param pattern:
        :param field to search with pattern:
        :param assert_not:
        :return:
        """
        regex = re.compile(pattern)
        checks = sorted(self.schedulers['scheduler-master'].sched.checks.values(),
                        key=lambda x: x.creation_time)
        for check in checks:
            if re.search(regex, getattr(check, field)):
                self.assertTrue(not assert_not,
                                "Found check:\nfield=%s pattern=%r\n"
                                "check_line=creation: %s, is_a: %s, type: %s, status: %s, "
                                "planned: %s, command: %s" % (
                                    field, pattern, check.creation_time, check.is_a,
                                    check.type, check.status, check.t_to_go, check.command)
                                )
                return
        self.assertTrue(assert_not, "No matching check found:\n"
                                    "pattern = %r\n" "checks = %r" % (pattern, checks))

    def assert_any_check_match(self, pattern, field):
        """
        Assert if any check matches the pattern

        @verified
        :param pattern:
        :param field to search with pattern:
        :return:
        """
        self._any_check_match(pattern, field, assert_not=False)

    def assert_no_check_match(self, pattern, field):
        """
        Assert if no check matches the pattern

        @verified
        :param pattern:
        :param field to search with pattern:
        :return:
        """
        self._any_check_match(pattern, field, assert_not=True)

    def _any_log_match(self, pattern, assert_not):
        """
        Search if any log in the Arbiter logs matches the requested pattern
        If 'scheduler' is True, then uses the scheduler's broks list.

        @verified
        :param pattern:
        :param assert_not:
        :return:
        """
        regex = re.compile(pattern)

        collector_h = [hand for hand in self.logger.handlers
                       if isinstance(hand, CollectorHandler)][0]

        for log in collector_h.collector:
            if re.search(regex, log):
                self.assertTrue(not assert_not,
                                "Found matching log line:\n"
                                "pattern = %r\nbrok log = %r" % (pattern, log))
                return

        self.assertTrue(assert_not, "No matching log line found:\n"
                                    "pattern = %r\n" "logs broks = %r" % (pattern,
                                                                          collector_h.collector))

    def assert_any_log_match(self, pattern):
        """
        Assert if any log (Arbiter or Scheduler if True) matches the pattern

        @verified
        :param pattern:
        :param scheduler:
        :return:
        """
        self._any_log_match(pattern, assert_not=False)

    def assert_no_log_match(self, pattern):
        """
        Assert if no log (Arbiter or Scheduler if True) matches the pattern

        @verified
        :param pattern:
        :param scheduler:
        :return:
        """
        self._any_log_match(pattern, assert_not=True)

    def _any_brok_match(self, pattern, level, assert_not):
        """
        Search if any brok message in the Scheduler broks matches the requested pattern and
        requested level

        @verified
        :param pattern:
        :param assert_not:
        :return:
        """
        regex = re.compile(pattern)

        monitoring_logs = []
        for brok in self._sched.brokers['broker-master']['broks'].itervalues():
            if brok.type == 'monitoring_log':
                data = unserialize(brok.data)
                monitoring_logs.append((data['level'], data['message']))
                if re.search(regex, data['message']) and (level is None or data['level'] == level):
                    self.assertTrue(not assert_not, "Found matching brok:\n"
                                    "pattern = %r\nbrok message = %r" % (pattern, data['message']))
                    return

        self.assertTrue(assert_not, "No matching brok found:\n"
                                    "pattern = %r\n" "brok message = %r" % (pattern,
                                                                            monitoring_logs))

    def assert_any_brok_match(self, pattern, level=None):
        """
        Search if any brok message in the Scheduler broks matches the requested pattern and
        requested level

        @verified
        :param pattern:
        :param scheduler:
        :return:
        """
        self._any_brok_match(pattern, level, assert_not=False)

    def assert_no_brok_match(self, pattern, level=None):
        """
        Search if no brok message in the Scheduler broks matches the requested pattern and
        requested level

        @verified
        :param pattern:
        :param scheduler:
        :return:
        """
        self._any_brok_match(pattern, level, assert_not=True)

    def get_log_match(self, pattern):
        regex = re.compile(pattern)
        res = []
        collector_h = [hand for hand in self.logger.handlers
                       if isinstance(hand, CollectorHandler)][0]

        for log in collector_h.collector:
            if re.search(regex, log):
                res.append(log)
        return res

    def print_header(self):
        print "\n" + "#" * 80 + "\n" + "#" + " " * 78 + "#"
        print "#" + string.center(self.id(), 78) + "#"
        print "#" + " " * 78 + "#\n" + "#" * 80 + "\n"

    def show_configuration_logs(self):
        """
        Prints the configuration logs

        @verified
        :return:
        """
        print("Configuration warnings:")
        for msg in self.configuration_warnings:
            print(" - %s" % msg)
        print("Configuration errors:")
        for msg in self.configuration_errors:
            print(" - %s" % msg)

    def _any_cfg_log_match(self, pattern, assert_not):
        """
        Search a pattern in configuration log (warning and error)

        @verified
        :param pattern:
        :return:
        """
        regex = re.compile(pattern)

        cfg_logs = self.configuration_warnings + self.configuration_errors

        for log in cfg_logs:
            if re.search(regex, log):
                self.assertTrue(not assert_not,
                                "Found matching log line:\n"
                                "pattern = %r\nlog = %r" % (pattern, log))
                return

        self.assertTrue(assert_not, "No matching log line found:\n"
                                    "pattern = %r\n" "logs = %r" % (pattern, cfg_logs))

    def assert_any_cfg_log_match(self, pattern):
        """
        Assert if any configuration log matches the pattern

        @verified
        :param pattern:
        :return:
        """
        self._any_cfg_log_match(pattern, assert_not=False)

    def assert_no_cfg_log_match(self, pattern):
        """
        Assert if no configuration log matches the pattern

        @verified
        :param pattern:
        :return:
        """
        self._any_cfg_log_match(pattern, assert_not=True)

    def guess_sys_stdout_encoding(self):
        ''' Return the best guessed encoding to be used for printing on sys.stdout. '''
        return (
               getattr(sys.stdout, 'encoding', None)
            or getattr(sys.__stdout__, 'encoding', None)
            or locale.getpreferredencoding()
            or sys.getdefaultencoding()
            or 'ascii'
        )

    def safe_print(self, *args, **kw):
        """" "print" args to sys.stdout,
        If some of the args aren't unicode then convert them first to unicode,
            using keyword argument 'in_encoding' if provided (else default to UTF8)
            and replacing bad encoded bytes.
        Write to stdout using 'out_encoding' if provided else best guessed encoding,
            doing xmlcharrefreplace on errors.
        """
        in_bytes_encoding = kw.pop('in_encoding', 'UTF-8')
        out_encoding = kw.pop('out_encoding', self.guess_sys_stdout_encoding())
        if kw:
            raise ValueError('unhandled named/keyword argument(s): %r' % kw)
        #
        make_in_data_gen = lambda: ( a if isinstance(a, unicode)
                                    else
                                unicode(str(a), in_bytes_encoding, 'replace')
                            for a in args )

        possible_codings = ( out_encoding, )
        if out_encoding != 'ascii':
            possible_codings += ( 'ascii', )

        for coding in possible_codings:
            data = u' '.join(make_in_data_gen()).encode(coding, 'xmlcharrefreplace')
            try:
                sys.stdout.write(data)
                break
            except UnicodeError as err:
                # there might still have some problem with the underlying sys.stdout.
                # it might be a StringIO whose content could be decoded/encoded in this same process
                # and have encode/decode errors because we could have guessed a bad encoding with it.
                # in such case fallback on 'ascii'
                if coding == 'ascii':
                    raise
                sys.stderr.write('Error on write to sys.stdout with %s encoding: err=%s\nTrying with ascii' % (
                    coding, err))
        sys.stdout.write(b'\n')


if __name__ == '__main__':
    unittest2.main()