#!/usr/bin/env python
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
# This file is used to test host- and service-downtimes.
#

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


import alignak
from alignak.objects.config import Config
from alignak.objects.command import Command
from alignak.objects.module import Module

from alignak.dispatcher import Dispatcher
from alignak.log import logger
from alignak.scheduler import Scheduler
from alignak.macroresolver import MacroResolver
from alignak.external_command import ExternalCommandManager, ExternalCommand
from alignak.check import Check
from alignak.message import Message
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


class __DUMMY:
    def add(self, obj):
        pass

logger.load_obj(__DUMMY())
logger.setLevel(ERROR)

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


class AlignakTest(unittest.TestCase):

    time_hacker = TimeHacker()
    maxDiff = None

    if sys.version_info < (2, 7):
        def assertRegex(self, *args, **kwargs):
            return self.assertRegexpMatches(*args, **kwargs)

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
        self.schedulers = []
        self.brokers = []
        self.arbiter = None
        self.conf_is_correct = False
        self.configuration_warnings = []
        self.configuration_errors = []

        self.arbiter = Arbiter([configuration_file], False, False, False, False,
                              '/tmp/arbiter.log', 'arbiter-master')

        try:
            self.arbiter.load_config_file()
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

        for broker in self.arbiter.conf.brokers:
            self.brokers.append(broker)

        for arb in self.arbiter.conf.arbiters:
            if arb.get_name() == self.arbiter.config_name:
                self.arbiter.myself = arb
        self.arbiter.dispatcher = Dispatcher(self.arbiter.conf, self.arbiter.myself)
        self.arbiter.dispatcher.prepare_dispatch()

        for scheduler in self.arbiter.dispatcher.schedulers:
            sched = Alignak([], False, False, True, '/tmp/scheduler.log')
            # logger.setLevel('DEBUG')
            sched.load_modules_manager()
            sched.new_conf = scheduler.conf_package
            if sched.new_conf:
                sched.setup_new_conf()
            self.schedulers.append(sched)

    def add(self, b):
        if isinstance(b, Brok):
            self.broks[b.uuid] = b
            return
        if isinstance(b, ExternalCommand):
            self.schedulers[0].run_external_command(b.cmd_line)

    def fake_check(self, ref, exit_status, output="OK"):
        # print "fake", ref
        now = time.time()
        check = ref.schedule(self.schedulers[0].sched.hosts, self.schedulers[0].sched.services, self.schedulers[0].sched.timeperiods,
                             self.schedulers[0].sched.macromodulations, self.schedulers[0].sched.checkmodulations,
                             self.schedulers[0].sched.checks, force=True)
        # now checks are schedule and we get them in
        # the action queue
        # check = ref.actions.pop()
        self.schedulers[0].sched.add(check)  # check is now in sched.checks[]
        # check = self.schedulers[0].sched.checks[ref.checks_in_progress[0]]

        # Allows to force check scheduling without setting its status nor
        # output. Useful for manual business rules rescheduling, for instance.
        if exit_status is None:
            return

        # fake execution
        check.check_time = now

        # and lie about when we will launch it because
        # if not, the schedule call for ref
        # will not really reschedule it because there
        # is a valid value in the future
        ref.next_chk = now - 0.5

        check.get_outputs(output, 9000)
        check.exit_status = exit_status
        check.execution_time = 0.001
        check.status = 'waitconsume'
        self.schedulers[0].sched.waiting_results.put(check)

    def scheduler_loop(self, count, items, reset_checks=True):
        """
        Manage scheduler checks

        !!!!!!!!!! This function is to be replaced by the scheduler_loop_new !!!!!!!!!!


        @verified
        :param count: number of checks to pass
        :type count: int
        :param items: list of list [[object, exist_status, output]]
        :type items: list
        :return: None
        """
        if reset_checks:
            self.schedulers[0].sched.checks = {}
        for num in range(count):
            for item in items:
                (obj, exit_status, output) = item
                obj.next_chk = time.time()
                chk = obj.launch_check(obj.next_chk,
                                       self.schedulers[0].sched.hosts,
                                       self.schedulers[0].sched.services,
                                       self.schedulers[0].sched.timeperiods,
                                       self.schedulers[0].sched.macromodulations,
                                       self.schedulers[0].sched.checkmodulations,
                                       self.schedulers[0].sched.checks,
                                       force=False)
                self.schedulers[0].sched.add_check(chk)
                # update the check to add the result
                chk.set_type_active()
                chk.output = output
                chk.exit_status = exit_status
                self.schedulers[0].sched.waiting_results.put(chk)
            for i in self.schedulers[0].sched.recurrent_works:
                (name, fun, nb_ticks) = self.schedulers[0].sched.recurrent_works[i]
                if nb_ticks == 1:
                    fun()

    def scheduler_loop_new(self, count, items):
        """
        Manage scheduler checks

        !!!!!!!!!! This function will replace the scheduler_loop !!!!!!!!!!

        @verified

        :param count: number of checks to pass
        :type count: int
        :param items: list of list [[object, exist_status, output]]
        :type items: list
        :return: None
        """
        for num in range(count):
            for item in items:
                (obj, exit_status, output) = item
                if len(obj.checks_in_progress) == 0:
                    for i in self.schedulers[0].sched.recurrent_works:
                        (name, fun, nb_ticks) = self.schedulers[0].sched.recurrent_works[i]
                        if nb_ticks == 1:
                            fun()
                self.assertGreater(len(obj.checks_in_progress), 0)
                chk = self.schedulers[0].sched.checks[obj.checks_in_progress[0]]
                chk.set_type_active()
                chk.output = output
                chk.exit_status = exit_status
                self.schedulers[0].sched.waiting_results.put(chk)

            for i in self.schedulers[0].sched.recurrent_works:
                (name, fun, nb_ticks) = self.schedulers[0].sched.recurrent_works[i]
                if nb_ticks == 1:
                    fun()

    def external_command_loop(self):
        """
        Execute the scheduler actions for external commands.

        @verified
        :return:
        """
        for i in self.schedulers[0].sched.recurrent_works:
            (name, fun, nb_ticks) = self.schedulers[0].sched.recurrent_works[i]
            if nb_ticks == 1:
                fun()

    def old_scheduler_loop(self, count, reflist, do_sleep=False, sleep_time=61, verbose=True,
                           nointernal=False):
        for ref in reflist:
            (obj, exit_status, output) = ref
            obj.checks_in_progress = []
        for loop in range(1, count + 1):
            if verbose is True:
                print "processing check", loop
            for ref in reflist:
                (obj, exit_status, output) = ref
                obj.update_in_checking()
                self.fake_check(obj, exit_status, output)
            if not nointernal:
                self.schedulers[0].sched.manage_internal_checks()

            self.schedulers[0].sched.consume_results()
            self.schedulers[0].sched.get_new_actions()
            self.schedulers[0].sched.get_new_broks()
            self.schedulers[0].sched.scatter_master_notifications()
            self.worker_loop(verbose)
            for ref in reflist:
                (obj, exit_status, output) = ref
                obj.checks_in_progress = []
                obj.update_in_checking()
            self.schedulers[0].sched.update_downtimes_and_comments()
            #time.sleep(ref.retry_interval * 60 + 1)
            if do_sleep:
                time.sleep(sleep_time)

    def worker_loop(self, verbose=True):
        self.schedulers[0].sched.delete_zombie_checks()
        self.schedulers[0].sched.delete_zombie_actions()
        checks = self.schedulers[0].sched.get_to_run_checks(True, False, worker_name='tester')
        actions = self.schedulers[0].sched.get_to_run_checks(False, True, worker_name='tester')
        # print "------------ worker loop checks ----------------"
        # print checks
        # print "------------ worker loop actions ----------------"
        if verbose is True:
            self.show_actions()
        # print "------------ worker loop new ----------------"
        for a in actions:
            a.status = 'inpoller'
            a.check_time = time.time()
            a.exit_status = 0
            self.schedulers[0].sched.put_results(a)
        if verbose is True:
            self.show_actions()
        # print "------------ worker loop end ----------------"

    def show_logs(self, scheduler=False):
        """
        Show logs from the Arbiter. Get the Arbiter broks list an filter to
        display only the 'log' type broks
        If 'scheduler' is True, then uses the scheduler's broks list.

        @verified
        :param scheduler:
        :return:
        """
        print "--- logs <<<----------------------------------"
        broks = self.arbiter.broks
        if scheduler:
            broks = self.schedulers[0].sched.broks

        for brok in sorted(broks.values(), lambda x, y: cmp(x.uuid, y.uuid)):
            if brok.type == 'log':
                brok.prepare()
                safe_print("LOG: ", brok.data['log'])

        print "--- logs >>>----------------------------------"

    def show_actions(self):
        print "--- actions <<<----------------------------------"
        actions = sorted(self.schedulers[0].sched.actions.values(), key=lambda x: x.creation_time)
        for a in actions:
            if a.is_a == 'notification':
                item = self.scheduler.sched.find_item_by_id(a.ref)
                if item.my_type == "host":
                    ref = "host: %s" % item.get_name()
                else:
                    hst = self.scheduler.sched.find_item_by_id(item.host)
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

        for check in self.schedulers[0].sched.checks.values():
            print("- %s" % check)
        print "--- checks >>>--------------------------------"

    def show_and_clear_logs(self, scheduler=False):
        """
        Prints and then delete the current Arbiter logs
        If 'scheduler' is True, then uses the scheduler's broks list.

        @verified
        :return:
        """
        self.show_logs(scheduler=scheduler)
        self.clear_logs(scheduler=scheduler)

    def show_and_clear_actions(self):
        self.show_actions()
        self.clear_actions()

    def count_logs(self, scheduler=False):
        """
        Count the log lines in the Arbiter broks.
        If 'scheduler' is True, then uses the scheduler's broks list.

        @verified
        :return:
        """
        broks = self.arbiter.broks
        if scheduler:
            broks = self.schedulers[0].sched.broks

        return len([b for b in broks.values() if b.type == 'log'])

    def count_actions(self):
        """
        Count the actions in the scheduler's actions.

        @verified
        :return:
        """
        return len(self.schedulers[0].sched.actions.values())

    def clear_logs(self, scheduler=False):
        """
        Remove the 'log' broks from the current Arbiter broks list
        If 'scheduler' is True, then uses the scheduler's broks list.

        @verified
        :return:
        """
        broks = self.arbiter.broks
        if scheduler:
            broks = self.schedulers[0].sched.broks

        id_to_del = []
        for b in broks.values():
            if b.type == 'log':
                id_to_del.append(b.uuid)
        for id in id_to_del:
            del broks[id]

    def clear_actions(self):
        """
        Clear the actions in the scheduler's actions.

        @verified
        :return:
        """
        self.schedulers[0].sched.actions = {}

    def assert_actions_count(self, number):
        """
        Check the number of actions

        @verified

        :param number: number of actions we must have
        :type number: int
        :return: None
        """
        print("Actions: %s" % self.schedulers[0].sched.actions)
        actions = sorted(self.schedulers[0].sched.actions.values(), key=lambda x: x.creation_time)
        self.assertEqual(number, len(self.schedulers[0].sched.actions),
                         "Not found expected number of actions:\nactions_logs=[[[\n%s\n]]]" %
                         ('\n'.join('\t%s = creation: %s, is_a: %s, type: %s, status: %s, planned: %s, '
                                    'command: %s' %
                                    (idx, b.creation_time, b.is_a, b.type, b.status, b.t_to_go, b.command)
                                    for idx, b in enumerate(actions))))

    def assert_actions_match(self, index, pattern, field):
        """
        Check if pattern verified in field(property) name of the action with index in action list

        @verified

        :param index: index number of actions list
        :type index: int
        :param pattern: pattern to verify is in the action
        :type pattern: str
        :param field: name of the field (property) of the action
        :type field: str
        :return: None
        """
        regex = re.compile(pattern)
        actions = sorted(self.schedulers[0].sched.actions.values(), key=lambda x: x.creation_time)
        myaction = actions[index]
        self.assertTrue(regex.search(getattr(myaction, field)),
                        "Not found a matching patternin actions:\nindex=%s field=%s pattern=%r\n"
                        "action_line=creation: %s, is_a: %s, type: %s, status: %s, planned: %s, "
                        "command: %s" % (
                            index, field, pattern, myaction.creation_time, myaction.is_a,
                            myaction.type, myaction.status, myaction.t_to_go, myaction.command))

    def assert_log_match(self, index, pattern, scheduler=False):
        """
        Search if the log with the index number has the pattern in the Arbiter logs.

        If 'scheduler' is True, then uses the scheduler's broks list.

        :param index: index number
        :type index: int
        :param pattern: string to search in log
        :type pattern: str
        :return: None
        """
        broks = self.arbiter.broks
        if scheduler:
            broks = self.schedulers[0].sched.broks

        regex = re.compile(pattern)
        log_num = 1

        found = False
        for brok in broks.values():
            if brok.type == 'log':
                brok.prepare()
                if index == log_num:
                    if regex.search(brok.data['log']):
                        found = True
                log_num += 1
        self.assertTrue(found,
                        "Not found a matching log line in broks:\nindex=%s pattern=%r\n"
                        "broks_logs=[[[\n%s\n]]]" % (
                            index, pattern, '\n'.join('\t%s=%s' % (idx, b.strip())
                                                      for idx, b in enumerate((b.data['log']
                                                                               for b in broks.values()
                                                                               if b.type == 'log'),
                                                                              1))))

    def assert_checks_count(self, number):
        """
        Check the number of actions

        @verified

        :param number: number of actions we must have
        :type number: int
        :return: None
        """
        checks = sorted(self.schedulers[0].sched.checks.values(), key=lambda x: x.creation_time)
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
        checks = sorted(self.schedulers[0].sched.checks.values(), key=lambda x: x.creation_time)
        mycheck = checks[index]
        self.assertTrue(regex.search(getattr(mycheck, field)),
                        "Not found a matching pattern in checks:\nindex=%s field=%s pattern=%r\n"
                        "check_line=creation: %s, is_a: %s, type: %s, status: %s, planned: %s, "
                        "command: %s" % (
                            index, field, pattern, mycheck.creation_time, mycheck.is_a,
                            mycheck.type, mycheck.status, mycheck.t_to_go, mycheck.command))

    def _any_check_match(self, pattern, field, assert_not):
        """
        Search if any chek matches the requested pattern

        @verified
        :param pattern:
        :param field to search with pattern:
        :param assert_not:
        :return:
        """
        regex = re.compile(pattern)
        checks = sorted(self.schedulers[0].sched.checks.values(), key=lambda x: x.creation_time)
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

    def _any_log_match(self, pattern, assert_not, scheduler=False):
        """
        Search if any log in the Arbiter logs matches the requested pattern
        If 'scheduler' is True, then uses the scheduler's broks list.

        @verified
        :param pattern:
        :param assert_not:
        :return:
        """
        regex = re.compile(pattern)
        broks = self.arbiter.broks
        if scheduler:
            broks = self.schedulers[0].sched.broks

        for brok in broks.values():
            if brok.type == 'log':
                brok.prepare()
                if re.search(regex, brok.data['log']):
                    self.assertTrue(not assert_not,
                                    "Found matching log line:\n"
                                    "pattern = %r\nbrok log = %r" % (pattern, brok.data['log']))
                    return
        logs = [brok.data['log'] for brok in broks.values() if brok.type == 'log']
        self.assertTrue(assert_not, "No matching log line found:\n"
                                    "pattern = %r\n" "logs broks = %r" % (pattern, logs))

    def assert_any_log_match(self, pattern, scheduler=False):
        """
        Assert if any log (Arbiter or Scheduler if True) matches the pattern

        @verified
        :param pattern:
        :param scheduler:
        :return:
        """
        self._any_log_match(pattern, assert_not=False)

    def assert_no_log_match(self, pattern, scheduler=False):
        """
        Assert if no log (Arbiter or Scheduler if True) matches the pattern

        @verified
        :param pattern:
        :param scheduler:
        :return:
        """
        self._any_log_match(pattern, assert_not=True)

    def get_log_match(self, pattern):
        regex = re.compile(pattern)
        res = []
        broks = self.broks
        if hasattr(self, "schedulers") and self.schedulers and hasattr(self.schedulers[0], "sched"):
            broks = self.schedulers[0].sched.broks

        for brok in broks:
            if brok.type == 'log':
                if re.search(regex, brok.data['log']):
                    res.append(brok.data['log'])
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