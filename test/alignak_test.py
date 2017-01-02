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

import sys
from sys import __stdout__
from functools import partial

import time
import datetime
import os
import string
import re
import random
import copy
import locale
import socket

import unittest2 as unittest

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
from logging import ERROR

from alignak_tst_utils import safe_print

# Modules are by default on the ../modules
myself = os.path.abspath(__file__)


#############################################################################
# We overwrite the functions time() and sleep()
# This way we can modify sleep() so that it immediately returns although
# for a following time() it looks like thee was actually a delay.
# This massively speeds up the tests.


class TimeHacker(object):

    def __init__(self):
        self.my_offset = 0
        self.my_starttime = time.time()
        self.my_oldtime = time.time
        self.original_time_time = time.time
        self.original_time_sleep = time.sleep
        self.in_real_time = True

    def my_time_time(self):
        return self.my_oldtime() + self.my_offset

    def my_time_sleep(self, delay):
        self.my_offset += delay

    def time_warp(self, duration):
        self.my_offset += duration

    def set_my_time(self):
        if self.in_real_time:
            time.time = self.my_time_time
            time.sleep = self.my_time_sleep
            self.in_real_time = False

# If external processes or time stamps for files are involved, we must
# revert the fake timing routines, because these externals cannot be fooled.
# They get their times from the operating system.
    def set_real_time(self):
        if not self.in_real_time:
            time.time = self.original_time_time
            time.sleep = self.original_time_sleep
            self.in_real_time = True


class Pluginconf(object):
    pass


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


class AlignakTest(unittest.TestCase):

    time_hacker = TimeHacker()
    maxDiff = None

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
        self.arbiter = Arbiter(None, [configuration_file], False, False, False, False,
                              '/tmp/arbiter.log', 'arbiter-master')

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
            print("Configuration warnings:")
            for msg in self.configuration_warnings:
                print(" - %s" % msg)
            self.configuration_errors = self.arbiter.conf.configuration_errors
            print("Configuration errors:")
            for msg in self.configuration_errors:
                print(" - %s" % msg)
            raise

        for arb in self.arbiter.conf.arbiters:
            if arb.get_name() == self.arbiter.arbiter_name:
                self.arbiter.myself = arb
        self.arbiter.dispatcher = Dispatcher(self.arbiter.conf, self.arbiter.myself)
        self.arbiter.dispatcher.prepare_dispatch()

        # Build schedulers dictionary with the schedulers involved in the configuration
        for scheduler in self.arbiter.dispatcher.schedulers:
            sched = Alignak([], False, False, True, '/tmp/scheduler.log')
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
            self.receivers[receiver.receiver_name] = receiver

        # Build reactionners dictionary with the reactionners involved in the configuration
        for reactionner in self.arbiter.dispatcher.reactionners:
            self.reactionners[reactionner.reactionner_name] = reactionner

        # Build brokers dictionary with the brokers involved in the configuration
        for broker in self.arbiter.dispatcher.brokers:
            self.brokers[broker.broker_name] = broker

    def add(self, b):
        if isinstance(b, Brok):
            self.broks[b.uuid] = b
            return
        if isinstance(b, ExternalCommand):
            self.schedulers['scheduler-master'].run_external_command(b.cmd_line)

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
                    fun()

    def external_command_loop(self):
        """
        Execute the scheduler actions for external commands.

        Yes, why not, but the scheduler si not an ECM 'dispatcher' but an 'applyer' ...

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
        self._sched = self.schedulers['scheduler-master'].sched

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
            safe_print(log)

        print "--- logs >>>----------------------------------"

    def show_actions(self):
        print "--- actions <<<----------------------------------"
        actions = sorted(self.schedulers['scheduler-master'].sched.actions.values(), key=lambda x: x.creation_time)
        for a in actions:
            if a.is_a == 'notification':
                item = self.schedulers['scheduler-master'].sched.find_item_by_id(a.ref)
                if item.my_type == "host":
                    ref = "host: %s" % item.get_name()
                else:
                    hst = self.schedulers['scheduler-master'].sched.find_item_by_id(item.host)
                    ref = "host: %s svc: %s" % (hst.get_name(), item.get_name())
                print "NOTIFICATION %s %s %s %s %s" % (a.uuid, ref, a.type,
                                                       time.asctime(time.localtime(a.t_to_go)),
                                                       a.status)
            elif a.is_a == 'eventhandler':
                print "EVENTHANDLER:", a
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
                         key=lambda x: x.creation_time)
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

    def xtest_conf_is_correct(self):
        self.print_header()
        self.assertTrue(self.conf.conf_is_correct)

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


ShinkenTest = AlignakTest

# Time hacking for every test!
time_hacker = AlignakTest.time_hacker

if __name__ == '__main__':
    unittest.main()