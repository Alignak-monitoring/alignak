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
#     andrewmcgilvray, a.mcgilvray@gmail.com
#     Guillaume Bour, guillaume@bour.cc
#     Alexandre Viau, alexandre@alexandreviau.net
#     Frédéric MOHIER, frederic.mohier@ipmfrance.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     xkilian, fmikus@acktomic.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Arthur Gautier, superbaloo@superbaloo.net
#     Sebastien Coavoux, s.coavoux@free.fr
#     Squiz, squiz@squiz.confais.org
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Gerhard Lausser, gerhard.lausser@consol.de

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
"""This module provides ExternalCommand and ExternalCommandManager classes
Used to process command sent by users

"""
# Because some arguments are really not used:
# pylint: disable=unused-argument
# Because it is easier to keep all the source code in the same file:
# pylint: disable=too-many-lines
# pylint: disable=too-many-public-methods
# Because sometimes we have many arguments
# pylint: disable=too-many-arguments

import logging
import time
import re
import collections

# This import, despite not used, is necessary to include all Alignak objects modules
# pylint: disable=wildcard-import,unused-wildcard-import
from alignak.action import ACT_STATUS_DONE, ACT_STATUS_TIMEOUT, ACT_STATUS_WAIT_CONSUME
from alignak.objects import *
from alignak.util import to_int, to_bool, split_semicolon
from alignak.downtime import Downtime
from alignak.contactdowntime import ContactDowntime
from alignak.comment import Comment
from alignak.log import make_monitoring_log
from alignak.eventhandler import EventHandler
from alignak.brok import Brok
from alignak.misc.common import DICT_MODATTR
from alignak.stats import statsmgr

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class ExternalCommand(object):
    """ExternalCommand class is only an object with a cmd_line attribute.
    All parsing and execution is done in manager

    """
    my_type = 'externalcommand'

    def __init__(self, cmd_line, timestamp=None):
        self.cmd_line = cmd_line
        try:
            self.cmd_line = self.cmd_line.decode('utf8', 'ignore')
        except UnicodeEncodeError:
            pass
        except AttributeError:
            # Python 3 will raise an exception
            pass
        self.creation_timestamp = timestamp or time.time()

    def serialize(self):
        """This function serializes into a simple dict object.
        It is used when transferring data to other daemons over the network (http)

        Here we directly return all attributes

        :return: json representation of a Brok
        :rtype: dict
        """
        return {"my_type": self.my_type, "cmd_line": self.cmd_line,
                "creation_timestamp": self.creation_timestamp}


class ExternalCommandManager(object):
    """ExternalCommandManager manages all external commands sent to Alignak.

    It basically parses arguments and executes the right function

    """

    commands = {
        'change_contact_modsattr':
            {'global': True, 'args': ['contact', None]},
        'change_contact_modhattr':
            {'global': True, 'args': ['contact', None]},
        'change_contact_modattr':
            {'global': True, 'args': ['contact', None]},
        'change_contact_host_notification_timeperiod':
            {'global': True, 'args': ['contact', 'time_period']},
        'add_svc_comment':
            {'global': False, 'args': ['service', 'obsolete', 'author', None]},
        'add_host_comment':
            {'global': False, 'args': ['host', 'obsolete', 'author', None]},
        'acknowledge_svc_problem':
            {'global': False, 'args': ['service', 'to_int', 'to_bool', 'obsolete', 'author', None]},
        'acknowledge_host_problem':
            {'global': False, 'args': ['host', 'to_int', 'to_bool', 'obsolete', 'author', None]},
        'acknowledge_svc_problem_expire':
            {'global': False, 'args': ['service', 'to_int', 'to_bool',
                                       'obsolete', 'to_int', 'author', None]},
        'acknowledge_host_problem_expire':
            {'global': False,
             'args': ['host', 'to_int', 'to_bool', 'obsolete', 'to_int', 'author', None]},
        'change_contact_svc_notification_timeperiod':
            {'global': True, 'args': ['contact', 'time_period']},
        'change_custom_contact_var':
            {'global': True, 'args': ['contact', None, None]},
        'change_custom_host_var':
            {'global': False, 'args': ['host', None, None]},
        'change_custom_svc_var':
            {'global': False, 'args': ['service', None, None]},
        'change_global_host_event_handler':
            {'global': True, 'args': ['command']},
        'change_global_svc_event_handler':
            {'global': True, 'args': ['command']},
        'change_host_check_command':
            {'global': False, 'args': ['host', 'command']},
        'change_host_check_timeperiod':
            {'global': False, 'args': ['host', 'time_period']},
        'change_host_event_handler':
            {'global': False, 'args': ['host', 'command']},
        'change_host_snapshot_command':
            {'global': False, 'args': ['host', 'command']},
        'change_host_modattr':
            {'global': False, 'args': ['host', 'to_int']},
        'change_max_host_check_attempts':
            {'global': False, 'args': ['host', 'to_int']},
        'change_max_svc_check_attempts':
            {'global': False, 'args': ['service', 'to_int']},
        'change_normal_host_check_interval':
            {'global': False, 'args': ['host', 'to_int']},
        'change_normal_svc_check_interval':
            {'global': False, 'args': ['service', 'to_int']},
        'change_retry_host_check_interval':
            {'global': False, 'args': ['host', 'to_int']},
        'change_retry_svc_check_interval':
            {'global': False, 'args': ['service', 'to_int']},
        'change_svc_check_command':
            {'global': False, 'args': ['service', 'command']},
        'change_svc_check_timeperiod':
            {'global': False, 'args': ['service', 'time_period']},
        'change_svc_event_handler':
            {'global': False, 'args': ['service', 'command']},
        'change_svc_snapshot_command':
            {'global': False, 'args': ['service', 'command']},
        'change_svc_modattr':
            {'global': False, 'args': ['service', 'to_int']},
        'change_svc_notification_timeperiod':
            {'global': False, 'args': ['service', 'time_period']},
        'delay_host_notification':
            {'global': False, 'args': ['host', 'to_int']},
        'delay_svc_notification':
            {'global': False, 'args': ['service', 'to_int']},
        'del_all_contact_downtimes':
            {'global': False, 'args': ['contact']},
        'del_all_host_comments':
            {'global': False, 'args': ['host']},
        'del_all_host_downtimes':
            {'global': False, 'args': ['host']},
        'del_all_svc_comments':
            {'global': False, 'args': ['service']},
        'del_all_svc_downtimes':
            {'global': False, 'args': ['service']},
        'del_contact_downtime':
            {'global': True, 'args': [None]},
        'del_host_comment':
            {'global': True, 'args': [None]},
        'del_host_downtime':
            {'global': True, 'args': [None]},
        'del_svc_comment':
            {'global': True, 'args': [None]},
        'del_svc_downtime':
            {'global': True, 'args': [None]},
        'disable_all_notifications_beyond_host':
            {'global': False, 'args': ['host']},
        'disable_contactgroup_host_notifications':
            {'global': True, 'args': ['contact_group']},
        'disable_contactgroup_svc_notifications':
            {'global': True, 'args': ['contact_group']},
        'disable_contact_host_notifications':
            {'global': True, 'args': ['contact']},
        'disable_contact_svc_notifications':
            {'global': True, 'args': ['contact']},
        'disable_event_handlers':
            {'global': True, 'args': []},
        'disable_failure_prediction':
            {'global': True, 'args': []},
        'disable_flap_detection':
            {'global': True, 'args': []},
        'disable_hostgroup_host_checks':
            {'global': True, 'args': ['host_group']},
        'disable_hostgroup_host_notifications':
            {'global': True, 'args': ['host_group']},
        'disable_hostgroup_passive_host_checks':
            {'global': True, 'args': ['host_group']},
        'disable_hostgroup_passive_svc_checks':
            {'global': True, 'args': ['host_group']},
        'disable_hostgroup_svc_checks':
            {'global': True, 'args': ['host_group']},
        'disable_hostgroup_svc_notifications':
            {'global': True, 'args': ['host_group']},
        'disable_host_and_child_notifications':
            {'global': False, 'args': ['host']},
        'disable_host_check':
            {'global': False, 'args': ['host']},
        'disable_host_event_handler':
            {'global': False, 'args': ['host']},
        'disable_host_flap_detection':
            {'global': False, 'args': ['host']},
        'disable_host_freshness_check':
            {'global': False, 'args': ['host']},
        'disable_host_freshness_checks':
            {'global': True, 'args': []},
        'disable_host_notifications':
            {'global': False, 'args': ['host']},
        'disable_host_svc_checks':
            {'global': False, 'args': ['host']},
        'disable_host_svc_notifications':
            {'global': False, 'args': ['host']},
        'disable_notifications':
            {'global': True, 'args': []},
        'disable_passive_host_checks':
            {'global': False, 'args': ['host']},
        'disable_passive_svc_checks':
            {'global': False, 'args': ['service']},
        'disable_performance_data':
            {'global': True, 'args': []},
        'disable_servicegroup_host_checks':
            {'global': True, 'args': ['service_group']},
        'disable_servicegroup_host_notifications':
            {'global': True, 'args': ['service_group']},
        'disable_servicegroup_passive_host_checks':
            {'global': True, 'args': ['service_group']},
        'disable_servicegroup_passive_svc_checks':
            {'global': True, 'args': ['service_group']},
        'disable_servicegroup_svc_checks':
            {'global': True, 'args': ['service_group']},
        'disable_servicegroup_svc_notifications':
            {'global': True, 'args': ['service_group']},
        'disable_service_flap_detection':
            {'global': False, 'args': ['service']},
        'disable_service_freshness_checks':
            {'global': True, 'args': []},
        'disable_svc_check':
            {'global': False, 'args': ['service']},
        'disable_svc_event_handler':
            {'global': False, 'args': ['service']},
        'disable_svc_flap_detection':
            {'global': False, 'args': ['service']},
        'disable_svc_freshness_check':
            {'global': False, 'args': ['service']},
        'disable_svc_notifications':
            {'global': False, 'args': ['service']},
        'enable_all_notifications_beyond_host':
            {'global': False, 'args': ['host']},
        'enable_contactgroup_host_notifications':
            {'global': True, 'args': ['contact_group']},
        'enable_contactgroup_svc_notifications':
            {'global': True, 'args': ['contact_group']},
        'enable_contact_host_notifications':
            {'global': True, 'args': ['contact']},
        'enable_contact_svc_notifications':
            {'global': True, 'args': ['contact']},
        'enable_event_handlers':
            {'global': True, 'args': []},
        'enable_failure_prediction':
            {'global': True, 'args': []},
        'enable_flap_detection':
            {'global': True, 'args': []},
        'enable_hostgroup_host_checks':
            {'global': True, 'args': ['host_group']},
        'enable_hostgroup_host_notifications':
            {'global': True, 'args': ['host_group']},
        'enable_hostgroup_passive_host_checks':
            {'global': True, 'args': ['host_group']},
        'enable_hostgroup_passive_svc_checks':
            {'global': True, 'args': ['host_group']},
        'enable_hostgroup_svc_checks':
            {'global': True, 'args': ['host_group']},
        'enable_hostgroup_svc_notifications':
            {'global': True, 'args': ['host_group']},
        'enable_host_and_child_notifications':
            {'global': False, 'args': ['host']},
        'enable_host_check':
            {'global': False, 'args': ['host']},
        'enable_host_event_handler':
            {'global': False, 'args': ['host']},
        'enable_host_flap_detection':
            {'global': False, 'args': ['host']},
        'enable_host_freshness_check':
            {'global': False, 'args': ['host']},
        'enable_host_freshness_checks':
            {'global': True, 'args': []},
        'enable_host_notifications':
            {'global': False, 'args': ['host']},
        'enable_host_svc_checks':
            {'global': False, 'args': ['host']},
        'enable_host_svc_notifications':
            {'global': False, 'args': ['host']},
        'enable_notifications':
            {'global': True, 'args': []},
        'enable_passive_host_checks':
            {'global': False, 'args': ['host']},
        'enable_passive_svc_checks':
            {'global': False, 'args': ['service']},
        'enable_performance_data':
            {'global': True, 'args': []},
        'enable_servicegroup_host_checks':
            {'global': True, 'args': ['service_group']},
        'enable_servicegroup_host_notifications':
            {'global': True, 'args': ['service_group']},
        'enable_servicegroup_passive_host_checks':
            {'global': True, 'args': ['service_group']},
        'enable_servicegroup_passive_svc_checks':
            {'global': True, 'args': ['service_group']},
        'enable_servicegroup_svc_checks':
            {'global': True, 'args': ['service_group']},
        'enable_servicegroup_svc_notifications':
            {'global': True, 'args': ['service_group']},
        'enable_service_freshness_checks':
            {'global': True, 'args': []},
        'enable_svc_check':
            {'global': False, 'args': ['service']},
        'enable_svc_event_handler':
            {'global': False, 'args': ['service']},
        'enable_svc_flap_detection':
            {'global': False, 'args': ['service']},
        'enable_svc_freshness_check':
            {'global': False, 'args': ['service']},
        'enable_svc_notifications':
            {'global': False, 'args': ['service']},
        'process_file':
            {'global': True, 'args': [None, 'to_bool']},
        'process_host_check_result':
            {'global': False, 'args': ['host', 'to_int', None]},
        'process_host_output':
            {'global': False, 'args': ['host', None]},
        'process_service_check_result':
            {'global': False, 'args': ['service', 'to_int', None]},
        'process_service_output':
            {'global': False, 'args': ['service', None]},
        'read_state_information':
            {'global': True, 'args': []},
        'remove_host_acknowledgement':
            {'global': False, 'args': ['host']},
        'remove_svc_acknowledgement':
            {'global': False, 'args': ['service']},
        'restart_program':
            {'global': True, 'internal': True, 'args': []},
        'reload_config':
            {'global': True, 'internal': True, 'args': []},
        'save_state_information':
            {'global': True, 'args': []},
        'schedule_and_propagate_host_downtime':
            {'global': False, 'args': ['host', 'to_int', 'to_int', 'to_bool',
                                       'to_int', 'to_int', 'author', None]},
        'schedule_and_propagate_triggered_host_downtime':
            {'global': False, 'args': ['host', 'to_int', 'to_int', 'to_bool',
                                       'to_int', 'to_int', 'author', None]},
        'schedule_contact_downtime':
            {'global': True, 'args': ['contact', 'to_int', 'to_int', 'author', None]},
        'schedule_forced_host_check':
            {'global': False, 'args': ['host', 'to_int']},
        'schedule_forced_host_svc_checks':
            {'global': False, 'args': ['host', 'to_int']},
        'schedule_forced_svc_check':
            {'global': False, 'args': ['service', 'to_int']},
        'schedule_hostgroup_host_downtime':
            {'global': True, 'args': ['host_group', 'to_int', 'to_int',
                                      'to_bool', None, 'to_int', 'author', None]},
        'schedule_hostgroup_svc_downtime':
            {'global': True, 'args': ['host_group', 'to_int', 'to_int', 'to_bool',
                                      None, 'to_int', 'author', None]},
        'schedule_host_check':
            {'global': False, 'args': ['host', 'to_int']},
        'schedule_host_downtime':
            {'global': False, 'args': ['host', 'to_int', 'to_int', 'to_bool',
                                       None, 'to_int', 'author', None]},
        'schedule_host_svc_checks':
            {'global': False, 'args': ['host', 'to_int']},
        'schedule_host_svc_downtime':
            {'global': False, 'args': ['host', 'to_int', 'to_int', 'to_bool',
                                       None, 'to_int', 'author', None]},
        'schedule_servicegroup_host_downtime':
            {'global': True, 'args': ['service_group', 'to_int', 'to_int', 'to_bool',
                                      None, 'to_int', 'author', None]},
        'schedule_servicegroup_svc_downtime':
            {'global': True, 'args': ['service_group', 'to_int', 'to_int', 'to_bool',
                                      None, 'to_int', 'author', None]},
        'schedule_svc_check':
            {'global': False, 'args': ['service', 'to_int']},
        'schedule_svc_downtime':
            {'global': False, 'args': ['service', 'to_int', 'to_int',
                                       'to_bool', None, 'to_int', 'author', None]},
        'send_custom_host_notification':
            {'global': False, 'args': ['host', 'to_int', 'author', None]},
        'send_custom_svc_notification':
            {'global': False, 'args': ['service', 'to_int', 'author', None]},
        'set_host_notification_number':
            {'global': False, 'args': ['host', 'to_int']},
        'set_svc_notification_number':
            {'global': False, 'args': ['service', 'to_int']},
        'shutdown_program':
            {'global': True, 'args': []},
        'start_accepting_passive_host_checks':
            {'global': True, 'args': []},
        'start_accepting_passive_svc_checks':
            {'global': True, 'args': []},
        'start_executing_host_checks':
            {'global': True, 'args': []},
        'start_executing_svc_checks':
            {'global': True, 'args': []},
        'stop_accepting_passive_host_checks':
            {'global': True, 'args': []},
        'stop_accepting_passive_svc_checks':
            {'global': True, 'args': []},
        'stop_executing_host_checks':
            {'global': True, 'args': []},
        'stop_executing_svc_checks':
            {'global': True, 'args': []},
        'launch_svc_event_handler':
            {'global': False, 'args': ['service']},
        'launch_host_event_handler':
            {'global': False, 'args': ['host']},
        # Now internal calls
        'add_simple_host_dependency':
            {'global': False, 'args': ['host', 'host']},
        'del_host_dependency':
            {'global': False, 'args': ['host', 'host']},
        'add_simple_poller':
            {'global': True, 'internal': True, 'args': [None, None, None, None]},
    }

    def __init__(self, conf, mode, daemon, accept_unknown=False):
        """
        The command manager is initialized with a `mode` parameter specifying what is to be done
        with the managed commands. If mode is:
        - applyer, the user daemon is a scheduler that will execute the command
        - dispatcher, the user daemon only dispatches the command to an applyer
        - receiver, the user daemon only receives commands, analyses and then dispatches
        them to the schedulers

        Note that the daemon parameter is really a Daemon object except for the scheduler where
        it is a Scheduler object!

        If `accept_passive_unknown_check_results` is True, then a Brok will be created even if
        passive checks are received for unknown host/service else a Warning log will be emitted..

        Note: the receiver mode has no configuration

        :param conf: current configuration
        :type conf: alignak.objects.Config
        :param mode: command manager mode
        :type mode: str
        :param daemon:
        :type daemon: alignak.Daemon
        :param accept_unknown: accept or not unknown passive checks results
        :type accept_unknown: bool
        """
        self.daemon = daemon
        self.mode = mode

        # If we got a conf...
        if self.mode == 'receiver':
            self.my_conf = {
                'log_external_commands': False,
                'schedulers': daemon.schedulers
            }
        else:
            self.my_conf = conf
            if conf:
                self.my_conf = conf
                self.hosts = conf.hosts
                self.services = conf.services
                self.contacts = conf.contacts
                self.hostgroups = conf.hostgroups
                self.commands = conf.commands
                self.servicegroups = conf.servicegroups
                self.contactgroups = conf.contactgroups
                self.timeperiods = conf.timeperiods

        self.cfg_parts = None
        if self.mode == 'dispatcher':
            self.cfg_parts = conf.parts

        self.accept_passive_unknown_check_results = accept_unknown

        # Will change for each command read, so if a command need it,
        # it can get it
        self.current_timestamp = 0

    def send_an_element(self, element):
        """Send an element (Brok, Comment,...) to our daemon

        Use the daemon `add` function if it exists, else raise an error log

        :param element: elementto be sent
        :type: alignak.Brok, or Comment, or Downtime, ...
        :return:
        """
        if hasattr(self.daemon, "add"):
            func = getattr(self.daemon, "add")
            if isinstance(func, collections.Callable):
                func(element)
                return

        logger.critical("External command or Brok could not be sent to any daemon!")

    def resolve_command(self, excmd):
        """Parse command and dispatch it (to schedulers for example) if necessary
        If the command is not global it will be executed.

        :param excmd: external command to handle
        :type excmd: alignak.external_command.ExternalCommand
        :return: result of command parsing. None for an invalid command.
        """
        # Maybe the command is invalid. Bailout
        try:
            command = excmd.cmd_line
        except AttributeError as exp:  # pragma: no cover, simple protection
            logger.warning("resolve_command, error with command %s", excmd)
            logger.exception("Exception: %s", exp)
            return None

        # Parse command
        command = command.strip()
        cmd = self.get_command_and_args(command, excmd)
        if cmd is None:
            return cmd

        # If we are a receiver, bail out here... do not try to execute the command
        if self.mode == 'receiver':
            return cmd

        if self.mode == 'applyer' and self.my_conf.log_external_commands:
            make_a_log = True
            # #912: only log an external command if it is not a passive check
            if self.my_conf.log_passive_checks and cmd['c_name'] \
                    in ['process_host_check_result', 'process_service_check_result']:
                # Do not log the command
                make_a_log = False

            if make_a_log:
                # I am a command dispatcher, notifies to my arbiter
                self.send_an_element(make_monitoring_log('info', 'EXTERNAL COMMAND: ' + command))

        if not cmd['global']:
            # Execute the command
            c_name = cmd['c_name']
            args = cmd['args']
            logger.debug("Execute command: %s %s", c_name, str(args))
            logger.debug("Command time measurement: %s (%d s)",
                         excmd.creation_timestamp, time.time() - excmd.creation_timestamp)
            statsmgr.timer('external-commands.latency', time.time() - excmd.creation_timestamp)
            getattr(self, c_name)(*args)
        else:
            # Send command to all our schedulers
            for scheduler_link in self.my_conf.schedulers:
                logger.debug("Preparing an external command '%s' for the scheduler %s",
                             excmd, scheduler_link.name)
                scheduler_link.pushed_commands.append(excmd.cmd_line)

        return cmd

    def search_host_and_dispatch(self, host_name, command, extcmd):
        # pylint: disable=too-many-branches
        """Try to dispatch a command for a specific host (so specific scheduler)
        because this command is related to a host (change notification interval for example)

        :param host_name: host name to search
        :type host_name: str
        :param command: command line
        :type command: str
        :param extcmd:  external command object (the object will be added to sched commands list)
        :type extcmd: alignak.external_command.ExternalCommand
        :return: None
        """
        logger.debug("Calling search_host_and_dispatch for %s", host_name)
        host_found = False

        # If we are a receiver, just look in the receiver
        if self.mode == 'receiver':
            logger.debug("Receiver is searching a scheduler for the external command %s %s",
                         host_name, command)
            scheduler_link = self.daemon.get_scheduler_from_hostname(host_name)
            if scheduler_link:
                host_found = True
                logger.debug("Receiver pushing external command to scheduler %s",
                             scheduler_link.name)
                scheduler_link.pushed_commands.append(extcmd)
            else:
                logger.warning("I did not found a scheduler for the host: %s", host_name)
        else:
            for cfg_part in list(self.cfg_parts.values()):
                if cfg_part.hosts.find_by_name(host_name) is not None:
                    logger.debug("Host %s found in a configuration", host_name)
                    if cfg_part.is_assigned:
                        host_found = True
                        scheduler_link = cfg_part.scheduler_link
                        logger.debug("Sending command to the scheduler %s", scheduler_link.name)
                        scheduler_link.push_external_commands([command])
                        # scheduler_link.my_daemon.external_commands.append(command)
                        break
                    else:
                        logger.warning("Problem: the host %s was found in a configuration, "
                                       "but this configuration is not assigned to any scheduler!",
                                       host_name)
        if not host_found:
            if self.accept_passive_unknown_check_results:
                brok = self.get_unknown_check_result_brok(command)
                if brok:
                    self.send_an_element(brok)
                else:
                    logger.warning("External command was received for the host '%s', "
                                   "but the host could not be found! Command is: %s",
                                   host_name, command)
            else:
                logger.warning("External command was received for host '%s', "
                               "but the host could not be found!", host_name)

    @staticmethod
    def get_unknown_check_result_brok(cmd_line):
        """Create unknown check result brok and fill it with command data

        :param cmd_line: command line to extract data
        :type cmd_line: str
        :return: unknown check result brok
        :rtype: alignak.objects.brok.Brok
        """
        match = re.match(
            r'^\[([0-9]{10})] PROCESS_(SERVICE)_CHECK_RESULT;'
            r'([^\;]*);([^\;]*);([^\;]*);([^\|]*)(?:\|(.*))?', cmd_line)
        if not match:
            match = re.match(
                r'^\[([0-9]{10})] PROCESS_(HOST)_CHECK_RESULT;'
                r'([^\;]*);([^\;]*);([^\|]*)(?:\|(.*))?', cmd_line)

        if not match:
            return None

        data = {
            'time_stamp': int(match.group(1)),
            'host_name': match.group(3),
        }

        if match.group(2) == 'SERVICE':
            data['service_description'] = match.group(4)
            data['return_code'] = match.group(5)
            data['output'] = match.group(6)
            data['perf_data'] = match.group(7)
        else:
            data['return_code'] = match.group(4)
            data['output'] = match.group(5)
            data['perf_data'] = match.group(6)

        return Brok({'type': 'unknown_%s_check_result' % match.group(2).lower(), 'data': data})

    def get_command_and_args(self, command, extcmd=None):
        # pylint: disable=too-many-return-statements, too-many-nested-blocks
        # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        """Parse command and get args

        :param command: command line to parse
        :type command: str
        :param extcmd: external command object (used to dispatch)
        :type extcmd: None | object
        :return: Dict containing command and arg ::

        {'global': False, 'c_name': c_name, 'args': args}

        :rtype: dict | None
        """
        # danger!!! passive check results with perfdata
        elts = split_semicolon(command)

        try:
            timestamp, c_name = elts[0].split()
        except ValueError as exp:
            splitted_command = elts[0].split()
            if len(splitted_command) == 1:
                # Assume no timestamp and only a command
                timestamp = "[%s]" % int(time.time())
                logger.warning("Missing timestamp in command '%s', using %s as a timestamp.",
                               elts[0], timestamp)
                c_name = elts[0].split()[0]
            else:
                logger.warning("Malformed command '%s'", command)
                # logger.exception("Malformed command exception: %s", exp)

                if self.my_conf and getattr(self.my_conf, 'log_external_commands', False):
                    # The command failed, make a monitoring log to inform
                    self.send_an_element(make_monitoring_log(
                        'error', "Malformed command: '%s'" % command))
                return None

        c_name = c_name.lower()

        # Is timestamp already an integer value?
        try:
            timestamp = int(timestamp)
        except ValueError as exp:
            # Else, remove enclosing characters: [], (), {}, ...
            timestamp = timestamp[1:-1]

        # Finally, check that the timestamp is really a timestamp
        try:
            self.current_timestamp = int(timestamp)
        except ValueError as exp:
            logger.warning("Malformed command '%s'", command)
            # logger.exception("Malformed command exception: %s", exp)

            if self.my_conf and getattr(self.my_conf, 'log_external_commands', False):
                # The command failed, make a monitoring log to inform
                self.send_an_element(make_monitoring_log(
                    'error', "Malformed command: '%s'" % command))
            return None

        if c_name not in ExternalCommandManager.commands:
            logger.warning("External command '%s' is not recognized, sorry", c_name)

            if self.my_conf and getattr(self.my_conf, 'log_external_commands', False):
                # The command failed, make a monitoring log to inform
                self.send_an_element(make_monitoring_log(
                    'error', "Command '%s' is not recognized, sorry" % command))
            return None

        # Split again based on the number of args we expect. We cannot split
        # on every ; because this character may appear in the perfdata of
        # passive check results.
        entry = ExternalCommandManager.commands[c_name]

        # Look if the command is purely internal (Alignak) or not
        internal = False
        if 'internal' in entry and entry['internal']:
            internal = True

        numargs = len(entry['args'])
        if numargs and 'service' in entry['args']:
            numargs += 1
        elts = split_semicolon(command, numargs)

        logger.debug("mode= %s, global= %s", self.mode, str(entry['global']))
        if self.mode in ['dispatcher', 'receiver'] and entry['global']:
            if not internal:
                logger.debug("Command '%s' is a global one, we resent it to all schedulers", c_name)
                return {'global': True, 'cmd': command}

        args = []
        i = 1
        in_service = False
        tmp_host = ''
        obsolete_arg = 0
        try:
            for elt in elts[1:]:
                try:
                    elt = elt.decode('utf8', 'ignore')
                except AttributeError:
                    # Python 3 will raise an error...
                    pass
                except UnicodeEncodeError:
                    pass
                logger.debug("Searching for a new arg: %s (%d)", elt, i)
                val = elt.strip()
                if val.endswith('\n'):
                    val = val[:-1]

                logger.debug("For command arg: %s", val)

                if not in_service:
                    type_searched = entry['args'][i - 1]

                    if type_searched == 'host':
                        if self.mode == 'dispatcher' or self.mode == 'receiver':
                            self.search_host_and_dispatch(val, command, extcmd)
                            return None
                        host = self.hosts.find_by_name(val)
                        if host is None:
                            if self.accept_passive_unknown_check_results:
                                brok = self.get_unknown_check_result_brok(command)
                                if brok:
                                    self.daemon.add_brok(brok)
                            else:
                                logger.warning("A command was received for the host '%s', "
                                               "but the host could not be found!", val)
                            return None

                        args.append(host)

                    elif type_searched == 'contact':
                        contact = self.contacts.find_by_name(val)
                        if contact is not None:
                            args.append(contact)

                    elif type_searched == 'time_period':
                        timeperiod = self.timeperiods.find_by_name(val)
                        if timeperiod is not None:
                            args.append(timeperiod)

                    elif type_searched == 'obsolete':
                        obsolete_arg += 1

                    elif type_searched == 'to_bool':
                        args.append(to_bool(val))

                    elif type_searched == 'to_int':
                        args.append(to_int(val))

                    elif type_searched in ('author', None):
                        args.append(val)

                    elif type_searched == 'command':
                        command = self.commands.find_by_name(val)
                        if command is not None:
                            # the find will be redone by
                            # the commandCall creation, but != None
                            # is useful so a bad command will be caught
                            args.append(val)

                    elif type_searched == 'host_group':
                        hostgroup = self.hostgroups.find_by_name(val)
                        if hostgroup is not None:
                            args.append(hostgroup)

                    elif type_searched == 'service_group':
                        servicegroup = self.servicegroups.find_by_name(val)
                        if servicegroup is not None:
                            args.append(servicegroup)

                    elif type_searched == 'contact_group':
                        contactgroup = self.contactgroups.find_by_name(val)
                        if contactgroup is not None:
                            args.append(contactgroup)

                    # special case: service are TWO args host;service, so one more loop
                    # to get the two parts
                    elif type_searched == 'service':
                        in_service = True
                        tmp_host = elt.strip()
                        if tmp_host[-1] == '\n':
                            tmp_host = tmp_host[:-1]
                        if self.mode == 'dispatcher':
                            self.search_host_and_dispatch(tmp_host, command, extcmd)
                            return None

                    i += 1
                else:
                    in_service = False
                    srv_name = elt
                    if srv_name[-1] == '\n':
                        srv_name = srv_name[:-1]
                    # If we are in a receiver, bailout now.
                    if self.mode == 'receiver':
                        self.search_host_and_dispatch(tmp_host, command, extcmd)
                        return None

                    serv = self.services.find_srv_by_name_and_hostname(tmp_host, srv_name)
                    if serv is None:
                        if self.accept_passive_unknown_check_results:
                            brok = self.get_unknown_check_result_brok(command)
                            self.send_an_element(brok)
                        else:
                            logger.warning("A command was received for the service '%s' on "
                                           "host '%s', but the service could not be found!",
                                           srv_name, tmp_host)
                        return None

                    args.append(serv)

        except IndexError as exp:
            logger.warning("Sorry, the arguments for the command '%s' are not correct")
            logger.exception("Arguments parsing exception: %s", exp)

            if self.my_conf and self.my_conf.log_external_commands:
                # The command failed, make a monitoring log to inform
                self.send_an_element(make_monitoring_log(
                    'error', "Arguments are not correct for the command: '%s'" % command))
        else:
            if len(args) == (len(entry['args']) - obsolete_arg):
                return {'global': False, 'c_name': c_name, 'args': args}

            logger.warning("Sorry, the arguments for the command '%s' are not correct (%s)",
                           command, (args))

            if self.my_conf and self.my_conf.log_external_commands:
                # The command failed, make a monitoring log to inform
                self.send_an_element(make_monitoring_log(
                    'error', "Arguments are not correct for the command: '%s'" % command))
        return None

    @staticmethod
    def change_contact_modsattr(contact, value):
        """Change contact modified service attribute value
        Format of the line that triggers function call::

        CHANGE_CONTACT_MODSATTR;<contact_name>;<value>

        :param contact: contact to edit
        :type contact: alignak.objects.contact.Contact
        :param value: new value to set
        :type value: str
        :return: None
        """
        # todo: deprecate this
        contact.modified_service_attributes = int(value)

    @staticmethod
    def change_contact_modhattr(contact, value):
        """Change contact modified host attribute value
        Format of the line that triggers function call::

        CHANGE_CONTACT_MODHATTR;<contact_name>;<value>

        :param contact: contact to edit
        :type contact: alignak.objects.contact.Contact
        :param value: new value to set
        :type value:str
        :return: None
        """
        # todo: deprecate this
        contact.modified_host_attributes = int(value)

    @staticmethod
    def change_contact_modattr(contact, value):
        """Change contact modified attribute value
        Format of the line that triggers function call::

        CHANGE_CONTACT_MODATTR;<contact_name>;<value>

        :param contact: contact to edit
        :type contact: alignak.objects.contact.Contact
        :param value: new value to set
        :type value: str
        :return: None
        """
        # todo: deprecate this
        contact.modified_attributes = int(value)

    def change_contact_host_notification_timeperiod(self, contact, notification_timeperiod):
        """Change contact host notification timeperiod value
        Format of the line that triggers function call::

        CHANGE_CONTACT_HOST_NOTIFICATION_TIMEPERIOD;<contact_name>;<notification_timeperiod>

        :param contact: contact to edit
        :type contact: alignak.objects.contact.Contact
        :param notification_timeperiod: timeperiod to set
        :type notification_timeperiod: alignak.objects.timeperiod.Timeperiod
        :return: None
        """
        # todo: deprecate this
        contact.modified_host_attributes |= DICT_MODATTR["MODATTR_NOTIFICATION_TIMEPERIOD"].value
        contact.host_notification_period = notification_timeperiod
        self.daemon.get_and_register_status_brok(contact)

    def add_svc_comment(self, service, author, comment):
        """Add a service comment
        Format of the line that triggers function call::

        ADD_SVC_COMMENT;<host_name>;<service_description>;<persistent:obsolete>;<author>;<comment>

        :param service: service to add the comment
        :type service: alignak.objects.service.Service
        :param author: author name
        :type author: str
        :param comment: text comment
        :type comment: str
        :return: None
        """
        data = {
            'author': author, 'comment': comment, 'comment_type': 2, 'entry_type': 1, 'source': 1,
            'expires': False, 'ref': service.uuid
        }
        comm = Comment(data)
        service.add_comment(comm)
        # todo: create and send a brok for service comment
        try:
            brok = make_monitoring_log('info', "SERVICE COMMENT: %s;%s;%s;%s"
                                       % (self.hosts[service.host].get_name(),
                                          service.get_name(),
                                          str(author, 'utf-8'), str(comment, 'utf-8')))
        except TypeError:
            brok = make_monitoring_log('info', "SERVICE COMMENT: %s;%s;%s;%s"
                                       % (self.hosts[service.host].get_name(),
                                          service.get_name(), author, comment))

        self.send_an_element(brok)

    def add_host_comment(self, host, author, comment):
        """Add a host comment
        Format of the line that triggers function call::

        ADD_HOST_COMMENT;<host_name>;<persistent:obsolete>;<author>;<comment>

        :param host: host to add the comment
        :type host: alignak.objects.host.Host
        :param author: author name
        :type author: str
        :param comment: text comment
        :type comment: str
        :return: None
        """
        data = {
            'author': author, 'comment': comment, 'comment_type': 1, 'entry_type': 1, 'source': 1,
            'expires': False, 'ref': host.uuid
        }
        comm = Comment(data)
        host.add_comment(comm)
        # todo: create and send a brok for host comment
        try:
            brok = make_monitoring_log('info', "HOST COMMENT: %s;%s;%s"
                                       % (host.get_name(),
                                          str(author, 'utf-8'), str(comment, 'utf-8')))
        except TypeError:
            brok = make_monitoring_log('info', "HOST COMMENT: %s;%s;%s"
                                       % (host.get_name(), author, comment))

        self.send_an_element(brok)

    def acknowledge_svc_problem(self, service, sticky, notify, author, comment):
        """Acknowledge a service problem
        Format of the line that triggers function call::

        ACKNOWLEDGE_SVC_PROBLEM;<host_name>;<service_description>;<sticky>;<notify>;
        <persistent:obsolete>;<author>;<comment>

        :param service: service to acknowledge the problem
        :type service: alignak.objects.service.Service
        :param sticky: if sticky == 2, the acknowledge will remain until the service returns to an
        OK state else the acknowledge will be removed as soon as the service state changes
        :param notify: if to 1, send a notification
        :type notify: integer
        :param author: name of the author or the acknowledge
        :type author: str
        :param comment: comment (description) of the acknowledge
        :type comment: str
        :return: None
        """
        notification_period = None
        if getattr(service, 'notification_period', None) is not None:
            notification_period = self.daemon.timeperiods[service.notification_period]
        service.acknowledge_problem(notification_period, self.hosts, self.services, sticky,
                                    notify, author, comment)

    def acknowledge_host_problem(self, host, sticky, notify, author, comment):
        """Acknowledge a host problem
        Format of the line that triggers function call::

        ACKNOWLEDGE_HOST_PROBLEM;<host_name>;<sticky>;<notify>;<persistent:obsolete>;<author>;
        <comment>

        :param host: host to acknowledge the problem
        :type host: alignak.objects.host.Host
        :param sticky: if sticky == 2, the acknowledge will remain until the host returns to an
        UP state else the acknowledge will be removed as soon as the host state changes
        :type sticky: integer
        :param notify: if to 1, send a notification
        :type notify: integer
        :param author: name of the author or the acknowledge
        :type author: str
        :param comment: comment (description) of the acknowledge
        :type comment: str
        :return: None
        TODO: add a better ACK management
        """
        notification_period = None
        if getattr(host, 'notification_period', None) is not None:
            notification_period = self.daemon.timeperiods[host.notification_period]
        host.acknowledge_problem(notification_period, self.hosts, self.services, sticky,
                                 notify, author, comment)

    def acknowledge_svc_problem_expire(self, service, sticky, notify, end_time, author, comment):
        """Acknowledge a service problem with expire time for this acknowledgement
        Format of the line that triggers function call::

        ACKNOWLEDGE_SVC_PROBLEM_EXPIRE;<host_name>;<service_description>;<sticky>;<notify>;
        <persistent:obsolete>;<end_time>;<author>;<comment>

        :param service: service to acknowledge the problem
        :type service: alignak.objects.service.Service
        :param sticky: acknowledge will be always present is host return in UP state
        :type sticky: integer
        :param notify: if to 1, send a notification
        :type notify: integer
        :param end_time: end (timeout) of this acknowledge in seconds(timestamp) (0 to never end)
        :type end_time: int
        :param author: name of the author or the acknowledge
        :type author: str
        :param comment: comment (description) of the acknowledge
        :type comment: str
        :return: None
        """
        notification_period = None
        if getattr(service, 'notification_period', None) is not None:
            notification_period = self.daemon.timeperiods[service.notification_period]
        service.acknowledge_problem(notification_period, self.hosts, self.services, sticky,
                                    notify, author, comment, end_time=end_time)

    def acknowledge_host_problem_expire(self, host, sticky, notify, end_time, author, comment):
        """Acknowledge a host problem with expire time for this acknowledgement
        Format of the line that triggers function call::

        ACKNOWLEDGE_HOST_PROBLEM_EXPIRE;<host_name>;<sticky>;<notify>;<persistent:obsolete>;
        <end_time>;<author>;<comment>

        :param host: host to acknowledge the problem
        :type host: alignak.objects.host.Host
        :param sticky: acknowledge will be always present is host return in UP state
        :type sticky: integer
        :param notify: if to 1, send a notification
        :type notify: integer
        :param end_time: end (timeout) of this acknowledge in seconds(timestamp) (0 to never end)
        :type end_time: int
        :param author: name of the author or the acknowledge
        :type author: str
        :param comment: comment (description) of the acknowledge
        :type comment: str
        :return: None
        TODO: add a better ACK management
        """
        notification_period = None
        if getattr(host, 'notification_period', None) is not None:
            notification_period = self.daemon.timeperiods[host.notification_period]
        host.acknowledge_problem(notification_period, self.hosts, self.services, sticky,
                                 notify, author, comment, end_time=end_time)

    def change_contact_svc_notification_timeperiod(self, contact, notification_timeperiod):
        """Change contact service notification timeperiod value
        Format of the line that triggers function call::

        CHANGE_CONTACT_SVC_NOTIFICATION_TIMEPERIOD;<contact_name>;<notification_timeperiod>

        :param contact: contact to edit
        :type contact: alignak.objects.contact.Contact
        :param notification_timeperiod: timeperiod to set
        :type notification_timeperiod: alignak.objects.timeperiod.Timeperiod
        :return: None
        """
        contact.modified_service_attributes |= \
            DICT_MODATTR["MODATTR_NOTIFICATION_TIMEPERIOD"].value
        contact.service_notification_period = notification_timeperiod
        self.daemon.get_and_register_status_brok(contact)

    def change_custom_contact_var(self, contact, varname, varvalue):
        """Change custom contact variable
        Format of the line that triggers function call::

        CHANGE_CUSTOM_CONTACT_VAR;<contact_name>;<varname>;<varvalue>

        :param contact: contact to edit
        :type contact: alignak.objects.contact.Contact
        :param varname: variable name to change
        :type varname: str
        :param varvalue: variable new value
        :type varvalue: str
        :return: None
        """
        if varname.upper() in contact.customs:
            contact.modified_attributes |= DICT_MODATTR["MODATTR_CUSTOM_VARIABLE"].value
            contact.customs[varname.upper()] = varvalue
            self.daemon.get_and_register_status_brok(contact)

    def change_custom_host_var(self, host, varname, varvalue):
        """Change custom host variable
        Format of the line that triggers function call::

        CHANGE_CUSTOM_HOST_VAR;<host_name>;<varname>;<varvalue>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :param varname: variable name to change
        :type varname: str
        :param varvalue: variable new value
        :type varvalue: str
        :return: None
        """
        if varname.upper() in host.customs:
            host.modified_attributes |= DICT_MODATTR["MODATTR_CUSTOM_VARIABLE"].value
            host.customs[varname.upper()] = varvalue
            self.daemon.get_and_register_status_brok(host)

    def change_custom_svc_var(self, service, varname, varvalue):
        """Change custom service variable
        Format of the line that triggers function call::

        CHANGE_CUSTOM_SVC_VAR;<host_name>;<service_description>;<varname>;<varvalue>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :param varname: variable name to change
        :type varvalue: str
        :param varvalue: variable new value
        :type varname: str
        :return: None
        """
        if varname.upper() in service.customs:
            service.modified_attributes |= DICT_MODATTR["MODATTR_CUSTOM_VARIABLE"].value
            service.customs[varname.upper()] = varvalue
            self.daemon.get_and_register_status_brok(service)

    def change_global_host_event_handler(self, event_handler_command):
        """DOES NOTHING (should change global host event handler)
        Format of the line that triggers function call::

        CHANGE_GLOBAL_HOST_EVENT_HANDLER;<event_handler_command>

        :param event_handler_command: new event handler
        :type event_handler_command:
        :return: None
        TODO: DICT_MODATTR["MODATTR_EVENT_HANDLER_COMMAND"].value
        """
        logger.warning("The external command 'CHANGE_GLOBAL_HOST_EVENT_HANDLER' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'CHANGE_GLOBAL_HOST_EVENT_HANDLER: this command is not implemented!'))

    def change_global_svc_event_handler(self, event_handler_command):
        """DOES NOTHING (should change global service event handler)
        Format of the line that triggers function call::

        CHANGE_GLOBAL_SVC_EVENT_HANDLER;<event_handler_command>

        :param event_handler_command: new event handler
        :type event_handler_command:
        :return: None
        TODO: DICT_MODATTR["MODATTR_EVENT_HANDLER_COMMAND"].value
        """
        logger.warning("The external command 'CHANGE_GLOBAL_SVC_EVENT_HANDLER' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'CHANGE_GLOBAL_SVC_EVENT_HANDLER: this command is not implemented!'))

    def change_host_check_command(self, host, check_command):
        """Modify host check command
        Format of the line that triggers function call::

        CHANGE_HOST_CHECK_COMMAND;<host_name>;<check_command>

        :param host: host to modify check command
        :type host: alignak.objects.host.Host
        :param check_command: command line
        :type check_command:
        :return: None
        """
        host.modified_attributes |= DICT_MODATTR["MODATTR_CHECK_COMMAND"].value
        data = {"commands": self.commands, "call": check_command, "poller_tag": host.poller_tag}
        host.change_check_command(data)
        self.daemon.get_and_register_status_brok(host)

    def change_host_check_timeperiod(self, host, timeperiod):
        """Modify host check timeperiod
        Format of the line that triggers function call::

        CHANGE_HOST_CHECK_TIMEPERIOD;<host_name>;<timeperiod>

        :param host: host to modify check timeperiod
        :type host: alignak.objects.host.Host
        :param timeperiod: timeperiod object
        :type timeperiod: alignak.objects.timeperiod.Timeperiod
        :return: None
        """
        host.modified_attributes |= DICT_MODATTR["MODATTR_CHECK_TIMEPERIOD"].value
        host.check_period = timeperiod
        self.daemon.get_and_register_status_brok(host)

    def change_host_event_handler(self, host, event_handler_command):
        """Modify host event handler
        Format of the line that triggers function call::

        CHANGE_HOST_EVENT_HANDLER;<host_name>;<event_handler_command>

        :param host: host to modify event handler
        :type host: alignak.objects.host.Host
        :param event_handler_command: event handler command line
        :type event_handler_command:
        :return: None
        """
        host.modified_attributes |= DICT_MODATTR["MODATTR_EVENT_HANDLER_COMMAND"].value
        data = {"commands": self.commands, "call": event_handler_command}
        host.change_event_handler(data)
        self.daemon.get_and_register_status_brok(host)

    def change_host_snapshot_command(self, host, snapshot_command):
        """Modify host snapshot command
        Format of the line that triggers function call::

        CHANGE_HOST_SNAPSHOT_COMMAND;<host_name>;<event_handler_command>

        :param host: host to modify snapshot command
        :type host: alignak.objects.host.Host
        :param snapshot_command: snapshot command command line
        :type snapshot_command:
        :return: None
        """
        host.modified_attributes |= DICT_MODATTR["MODATTR_EVENT_HANDLER_COMMAND"].value
        data = {"commands": self.commands, "call": snapshot_command}
        host.change_snapshot_command(data)
        self.daemon.get_and_register_status_brok(host)

    def change_host_modattr(self, host, value):
        """Change host modified attributes
        Format of the line that triggers function call::

        CHANGE_HOST_MODATTR;<host_name>;<value>

        For boolean attributes, toggles the service attribute state (enable/disable)
        For non boolean attribute, only indicates that the corresponding attribute is to be saved
        in the retention.

        Value can be:
        MODATTR_NONE                            0
        MODATTR_NOTIFICATIONS_ENABLED           1
        MODATTR_ACTIVE_CHECKS_ENABLED           2
        MODATTR_PASSIVE_CHECKS_ENABLED          4
        MODATTR_EVENT_HANDLER_ENABLED           8
        MODATTR_FLAP_DETECTION_ENABLED          16
        MODATTR_PERFORMANCE_DATA_ENABLED        64
        MODATTR_EVENT_HANDLER_COMMAND           256
        MODATTR_CHECK_COMMAND                   512
        MODATTR_NORMAL_CHECK_INTERVAL           1024
        MODATTR_RETRY_CHECK_INTERVAL            2048
        MODATTR_MAX_CHECK_ATTEMPTS              4096
        MODATTR_FRESHNESS_CHECKS_ENABLED        8192
        MODATTR_CHECK_TIMEPERIOD                16384
        MODATTR_CUSTOM_VARIABLE                 32768
        MODATTR_NOTIFICATION_TIMEPERIOD         65536

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :param value: new value to set
        :type value: str
        :return: None
        """
        # todo: deprecate this
        # We need to change each of the needed attributes.
        previous_value = host.modified_attributes
        changes = int(value)

        # For all boolean and non boolean attributes
        for modattr in ["MODATTR_NOTIFICATIONS_ENABLED", "MODATTR_ACTIVE_CHECKS_ENABLED",
                        "MODATTR_PASSIVE_CHECKS_ENABLED", "MODATTR_EVENT_HANDLER_ENABLED",
                        "MODATTR_FLAP_DETECTION_ENABLED", "MODATTR_PERFORMANCE_DATA_ENABLED",
                        "MODATTR_FRESHNESS_CHECKS_ENABLED",
                        "MODATTR_EVENT_HANDLER_COMMAND", "MODATTR_CHECK_COMMAND",
                        "MODATTR_NORMAL_CHECK_INTERVAL", "MODATTR_RETRY_CHECK_INTERVAL",
                        "MODATTR_MAX_CHECK_ATTEMPTS", "MODATTR_FRESHNESS_CHECKS_ENABLED",
                        "MODATTR_CHECK_TIMEPERIOD", "MODATTR_CUSTOM_VARIABLE",
                        "MODATTR_NOTIFICATION_TIMEPERIOD"]:
            if changes & DICT_MODATTR[modattr].value:
                # Toggle the concerned service attribute
                setattr(host, DICT_MODATTR[modattr].attribute, not
                        getattr(host, DICT_MODATTR[modattr].attribute))

        host.modified_attributes = previous_value ^ changes

        # And we need to push the information to the scheduler.
        self.daemon.get_and_register_status_brok(host)

    def change_max_host_check_attempts(self, host, check_attempts):
        """Modify max host check attempt
        Format of the line that triggers function call::

        CHANGE_MAX_HOST_CHECK_ATTEMPTS;<host_name>;<check_attempts>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :param check_attempts: new value to set
        :type check_attempts: int
        :return: None
        """
        host.modified_attributes |= DICT_MODATTR["MODATTR_MAX_CHECK_ATTEMPTS"].value
        host.max_check_attempts = check_attempts
        if host.state_type == u'HARD' and host.state == u'UP' and host.attempt > 1:
            host.attempt = host.max_check_attempts
        self.daemon.get_and_register_status_brok(host)

    def change_max_svc_check_attempts(self, service, check_attempts):
        """Modify max service check attempt
        Format of the line that triggers function call::

        CHANGE_MAX_SVC_CHECK_ATTEMPTS;<host_name>;<service_description>;<check_attempts>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :param check_attempts: new value to set
        :type check_attempts: int
        :return: None
        """
        service.modified_attributes |= DICT_MODATTR["MODATTR_MAX_CHECK_ATTEMPTS"].value
        service.max_check_attempts = check_attempts
        if service.state_type == u'HARD' and service.state == u'OK' and service.attempt > 1:
            service.attempt = service.max_check_attempts
        self.daemon.get_and_register_status_brok(service)

    def change_normal_host_check_interval(self, host, check_interval):
        """Modify host check interval
        Format of the line that triggers function call::

        CHANGE_NORMAL_HOST_CHECK_INTERVAL;<host_name>;<check_interval>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :param check_interval: new value to set
        :type check_interval:
        :return: None
        """
        host.modified_attributes |= DICT_MODATTR["MODATTR_NORMAL_CHECK_INTERVAL"].value
        old_interval = host.check_interval
        host.check_interval = check_interval
        # If there were no regular checks (interval=0), then schedule
        # a check immediately.
        if old_interval == 0 and host.checks_enabled:
            host.schedule(self.daemon.hosts, self.daemon.services,
                          self.daemon.timeperiods, self.daemon.macromodulations,
                          self.daemon.checkmodulations, self.daemon.checks,
                          force=False, force_time=int(time.time()))
        self.daemon.get_and_register_status_brok(host)

    def change_normal_svc_check_interval(self, service, check_interval):
        """Modify service check interval
        Format of the line that triggers function call::

        CHANGE_NORMAL_SVC_CHECK_INTERVAL;<host_name>;<service_description>;<check_interval>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :param check_interval: new value to set
        :type check_interval:
        :return: None
        """
        service.modified_attributes |= DICT_MODATTR["MODATTR_NORMAL_CHECK_INTERVAL"].value
        old_interval = service.check_interval
        service.check_interval = check_interval
        # If there were no regular checks (interval=0), then schedule
        # a check immediately.
        if old_interval == 0 and service.checks_enabled:
            service.schedule(self.daemon.hosts, self.daemon.services,
                             self.daemon.timeperiods, self.daemon.macromodulations,
                             self.daemon.checkmodulations, self.daemon.checks,
                             force=False, force_time=int(time.time()))
        self.daemon.get_and_register_status_brok(service)

    def change_retry_host_check_interval(self, host, check_interval):
        """Modify host retry interval
        Format of the line that triggers function call::

        CHANGE_RETRY_HOST_CHECK_INTERVAL;<host_name>;<check_interval>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :param check_interval: new value to set
        :type check_interval:
        :return: None
        """
        host.modified_attributes |= DICT_MODATTR["MODATTR_RETRY_CHECK_INTERVAL"].value
        host.retry_interval = check_interval
        self.daemon.get_and_register_status_brok(host)

    def change_retry_svc_check_interval(self, service, check_interval):
        """Modify service retry interval
        Format of the line that triggers function call::

        CHANGE_RETRY_SVC_CHECK_INTERVAL;<host_name>;<service_description>;<check_interval>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :param check_interval: new value to set
        :type check_interval:
        :return: None
        """
        service.modified_attributes |= DICT_MODATTR["MODATTR_RETRY_CHECK_INTERVAL"].value
        service.retry_interval = check_interval
        self.daemon.get_and_register_status_brok(service)

    def change_svc_check_command(self, service, check_command):
        """Modify service check command
        Format of the line that triggers function call::

        CHANGE_SVC_CHECK_COMMAND;<host_name>;<service_description>;<check_command>

        :param service: service to modify check command
        :type service: alignak.objects.service.Service
        :param check_command: command line
        :type check_command:
        :return: None
        """
        service.modified_attributes |= DICT_MODATTR["MODATTR_CHECK_COMMAND"].value
        data = {"commands": self.commands, "call": check_command, "poller_tag": service.poller_tag}
        service.change_check_command(data)
        self.daemon.get_and_register_status_brok(service)

    def change_svc_check_timeperiod(self, service, check_timeperiod):
        """Modify service check timeperiod
        Format of the line that triggers function call::

        CHANGE_SVC_CHECK_TIMEPERIOD;<host_name>;<service_description>;<check_timeperiod>

        :param service: service to modify check timeperiod
        :type service: alignak.objects.service.Service
        :param check_timeperiod: timeperiod object
        :type check_timeperiod: alignak.objects.timeperiod.Timeperiod
        :return: None
        """
        service.modified_attributes |= DICT_MODATTR["MODATTR_CHECK_TIMEPERIOD"].value
        service.check_period = check_timeperiod
        self.daemon.get_and_register_status_brok(service)

    def change_svc_event_handler(self, service, event_handler_command):
        """Modify service event handler
        Format of the line that triggers function call::

        CHANGE_SVC_EVENT_HANDLER;<host_name>;<service_description>;<event_handler_command>

        :param service: service to modify event handler
        :type service: alignak.objects.service.Service
        :param event_handler_command: event handler command line
        :type event_handler_command:
        :return: None
        """
        service.modified_attributes |= DICT_MODATTR["MODATTR_EVENT_HANDLER_COMMAND"].value
        data = {"commands": self.commands, "call": event_handler_command}
        service.change_event_handler(data)
        self.daemon.get_and_register_status_brok(service)

    def change_svc_snapshot_command(self, service, snapshot_command):
        """Modify host snapshot command
        Format of the line that triggers function call::

        CHANGE_HOST_SNAPSHOT_COMMAND;<host_name>;<event_handler_command>

        :param service: service to modify snapshot command
        :type service: alignak.objects.service.Service
        :param snapshot_command: snapshot command command line
        :type snapshot_command:
        :return: None
        """
        service.modified_attributes |= DICT_MODATTR["MODATTR_EVENT_HANDLER_COMMAND"].value
        data = {"commands": self.commands, "call": snapshot_command}
        service.change_snapshot_command(data)
        self.daemon.get_and_register_status_brok(service)

    def change_svc_modattr(self, service, value):
        """Change service modified attributes
        Format of the line that triggers function call::

        CHANGE_SVC_MODATTR;<host_name>;<service_description>;<value>

        For boolean attributes, toggles the service attribute state (enable/disable)
        For non boolean attribute, only indicates that the corresponding attribute is to be saved
        in the retention.

        Value can be:
        MODATTR_NONE                            0
        MODATTR_NOTIFICATIONS_ENABLED           1
        MODATTR_ACTIVE_CHECKS_ENABLED           2
        MODATTR_PASSIVE_CHECKS_ENABLED          4
        MODATTR_EVENT_HANDLER_ENABLED           8
        MODATTR_FLAP_DETECTION_ENABLED          16
        MODATTR_PERFORMANCE_DATA_ENABLED        64
        MODATTR_EVENT_HANDLER_COMMAND           256
        MODATTR_CHECK_COMMAND                   512
        MODATTR_NORMAL_CHECK_INTERVAL           1024
        MODATTR_RETRY_CHECK_INTERVAL            2048
        MODATTR_MAX_CHECK_ATTEMPTS              4096
        MODATTR_FRESHNESS_CHECKS_ENABLED        8192
        MODATTR_CHECK_TIMEPERIOD                16384
        MODATTR_CUSTOM_VARIABLE                 32768
        MODATTR_NOTIFICATION_TIMEPERIOD         65536

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :param value: new value to set / unset
        :type value: str
        :return: None
        """
        # todo: deprecate this
        # We need to change each of the needed attributes.
        previous_value = service.modified_attributes
        changes = int(value)

        # For all boolean and non boolean attributes
        for modattr in ["MODATTR_NOTIFICATIONS_ENABLED", "MODATTR_ACTIVE_CHECKS_ENABLED",
                        "MODATTR_PASSIVE_CHECKS_ENABLED", "MODATTR_EVENT_HANDLER_ENABLED",
                        "MODATTR_FLAP_DETECTION_ENABLED", "MODATTR_PERFORMANCE_DATA_ENABLED",
                        "MODATTR_FRESHNESS_CHECKS_ENABLED",
                        "MODATTR_EVENT_HANDLER_COMMAND", "MODATTR_CHECK_COMMAND",
                        "MODATTR_NORMAL_CHECK_INTERVAL", "MODATTR_RETRY_CHECK_INTERVAL",
                        "MODATTR_MAX_CHECK_ATTEMPTS", "MODATTR_FRESHNESS_CHECKS_ENABLED",
                        "MODATTR_CHECK_TIMEPERIOD", "MODATTR_CUSTOM_VARIABLE",
                        "MODATTR_NOTIFICATION_TIMEPERIOD"]:
            if changes & DICT_MODATTR[modattr].value:
                # Toggle the concerned service attribute
                setattr(service, DICT_MODATTR[modattr].attribute, not
                        getattr(service, DICT_MODATTR[modattr].attribute))

        service.modified_attributes = previous_value ^ changes

        # And we need to push the information to the scheduler.
        self.daemon.get_and_register_status_brok(service)

    def change_svc_notification_timeperiod(self, service, notification_timeperiod):
        """Change service notification timeperiod
        Format of the line that triggers function call::

        CHANGE_SVC_NOTIFICATION_TIMEPERIOD;<host_name>;<service_description>;
        <notification_timeperiod>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :param notification_timeperiod: timeperiod to set
        :type notification_timeperiod: alignak.objects.timeperiod.Timeperiod
        :return: None
        """
        service.modified_attributes |= DICT_MODATTR["MODATTR_NOTIFICATION_TIMEPERIOD"].value
        service.notification_period = notification_timeperiod
        self.daemon.get_and_register_status_brok(service)

    def delay_host_notification(self, host, notification_time):
        """Modify host first notification delay
        Format of the line that triggers function call::

        DELAY_HOST_NOTIFICATION;<host_name>;<notification_time>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :param notification_time: new value to set
        :type notification_time:
        :return: None
        """
        host.first_notification_delay = notification_time
        self.daemon.get_and_register_status_brok(host)

    def delay_svc_notification(self, service, notification_time):
        """Modify service first notification delay
        Format of the line that triggers function call::

        DELAY_SVC_NOTIFICATION;<host_name>;<service_description>;<notification_time>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :param notification_time: new value to set
        :type notification_time:
        :return: None
        """
        service.first_notification_delay = notification_time
        self.daemon.get_and_register_status_brok(service)

    def del_all_contact_downtimes(self, contact):
        """Delete all contact downtimes
        Format of the line that triggers function call::

        DEL_ALL_CONTACT_DOWNTIMES;<contact_name>

        :param contact: contact to edit
        :type contact: alignak.objects.contact.Contact
        :return: None
        """
        for downtime in contact.downtimes:
            self.del_contact_downtime(downtime)

    @staticmethod
    def del_all_host_comments(host):
        """Delete all host comments
        Format of the line that triggers function call::

        DEL_ALL_HOST_COMMENTS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        comments = list(host.comments.keys())
        for uuid in comments:
            host.del_comment(uuid)

    def del_all_host_downtimes(self, host):
        """Delete all host downtimes
        Format of the line that triggers function call::

        DEL_ALL_HOST_DOWNTIMES;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        for downtime in host.downtimes:
            self.del_host_downtime(downtime)

    @staticmethod
    def del_all_svc_comments(service):
        """Delete all service comments
        Format of the line that triggers function call::

        DEL_ALL_SVC_COMMENTS;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        comments = list(service.comments.keys())
        for uuid in comments:
            service.del_comment(uuid)

    def del_all_svc_downtimes(self, service):
        """Delete all service downtime
        Format of the line that triggers function call::

        DEL_ALL_SVC_DOWNTIMES;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        for downtime in service.downtimes:
            self.del_svc_downtime(downtime)

    def del_contact_downtime(self, downtime_id):
        """Delete a contact downtime
        Format of the line that triggers function call::

        DEL_CONTACT_DOWNTIME;<downtime_id>

        :param downtime_id: downtime id to delete
        :type downtime_id: int
        :return: None
        """
        for item in self.daemon.contacts:
            if downtime_id in item.downtimes:
                item.downtimes[downtime_id].cancel(self.daemon.contacts)
                break
        else:
            self.send_an_element(make_monitoring_log(
                'warning', 'DEL_CONTACT_DOWNTIME: downtime id: %s does not exist '
                           'and cannot be deleted.' % downtime_id))

    def del_host_comment(self, comment_id):
        """Delete a host comment
        Format of the line that triggers function call::

        DEL_HOST_COMMENT;<comment_id>

        :param comment_id: comment id to delete
        :type comment_id: int
        :return: None
        """
        for item in self.daemon.hosts:
            if comment_id in item.comments:
                item.del_comment(comment_id)
                break
        else:
            self.send_an_element(make_monitoring_log(
                'warning', 'DEL_HOST_COMMENT: comment id: %s does not exist '
                           'and cannot be deleted.' % comment_id))

    def del_host_downtime(self, downtime_id):
        """Delete a host downtime
        Format of the line that triggers function call::

        DEL_HOST_DOWNTIME;<downtime_id>

        :param downtime_id: downtime id to delete
        :type downtime_id: int
        :return: None
        """
        broks = []
        for item in self.daemon.hosts:
            if downtime_id in item.downtimes:
                broks.extend(item.downtimes[downtime_id].cancel(self.daemon.timeperiods,
                                                                self.daemon.hosts,
                                                                self.daemon.services))
                break
        else:
            self.send_an_element(make_monitoring_log(
                'warning', 'DEL_HOST_DOWNTIME: downtime id: %s does not exist '
                           'and cannot be deleted.' % downtime_id))
        for brok in broks:
            self.send_an_element(brok)

    def del_svc_comment(self, comment_id):
        """Delete a service comment
        Format of the line that triggers function call::

        DEL_SVC_COMMENT;<comment_id>

        :param comment_id: comment id to delete
        :type comment_id: int
        :return: None
        """
        for svc in self.daemon.services:
            if comment_id in svc.comments:
                svc.del_comment(comment_id)
                break
        else:
            self.send_an_element(make_monitoring_log(
                'warning', 'DEL_SVC_COMMENT: comment id: %s does not exist '
                           'and cannot be deleted.' % comment_id))

    def del_svc_downtime(self, downtime_id):
        """Delete a service downtime
        Format of the line that triggers function call::

        DEL_SVC_DOWNTIME;<downtime_id>

        :param downtime_id: downtime id to delete
        :type downtime_id: int
        :return: None
        """
        broks = []
        for svc in self.daemon.services:
            if downtime_id in svc.downtimes:
                broks.extend(svc.downtimes[downtime_id].cancel(self.daemon.timeperiods,
                                                               self.daemon.hosts,
                                                               self.daemon.services))
                break
        else:
            self.send_an_element(make_monitoring_log(
                'warning', 'DEL_SVC_DOWNTIME: downtime id: %s does not exist '
                           'and cannot be deleted.' % downtime_id))
        for brok in broks:
            self.send_an_element(brok)

    def disable_all_notifications_beyond_host(self, host):
        """DOES NOTHING (should disable notification beyond a host)
        Format of the line that triggers function call::

        DISABLE_ALL_NOTIFICATIONS_BEYOND_HOST;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        TODO: Implement it
        """
        logger.warning("The external command 'DISABLE_ALL_NOTIFICATIONS_BEYOND_HOST' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'DISABLE_ALL_NOTIFICATIONS_BEYOND_HOST: this command is not implemented!'))

    def disable_contactgroup_host_notifications(self, contactgroup):
        """Disable host notifications for a contactgroup
        Format of the line that triggers function call::

        DISABLE_CONTACTGROUP_HOST_NOTIFICATIONS;<contactgroup_name>

        :param contactgroup: contactgroup to disable
        :type contactgroup: alignak.objects.contactgroup.Contactgroup
        :return: None
        """
        for contact_id in contactgroup.get_contacts():
            self.disable_contact_host_notifications(self.daemon.contacts[contact_id])

    def disable_contactgroup_svc_notifications(self, contactgroup):
        """Disable service notifications for a contactgroup
        Format of the line that triggers function call::

        DISABLE_CONTACTGROUP_SVC_NOTIFICATIONS;<contactgroup_name>

        :param contactgroup: contactgroup to disable
        :type contactgroup: alignak.objects.contactgroup.Contactgroup
        :return: None
        """
        for contact_id in contactgroup.get_contacts():
            self.disable_contact_svc_notifications(self.daemon.contacts[contact_id])

    def disable_contact_host_notifications(self, contact):
        """Disable host notifications for a contact
        Format of the line that triggers function call::

        DISABLE_CONTACT_HOST_NOTIFICATIONS;<contact_name>

        :param contact: contact to disable
        :type contact: alignak.objects.contact.Contact
        :return: None
        """
        if contact.host_notifications_enabled:
            contact.modified_attributes |= DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            contact.host_notifications_enabled = False
            self.daemon.get_and_register_status_brok(contact)

    def disable_contact_svc_notifications(self, contact):
        """Disable service notifications for a contact
        Format of the line that triggers function call::

        DISABLE_CONTACT_SVC_NOTIFICATIONS;<contact_name>

        :param contact: contact to disable
        :type contact: alignak.objects.contact.Contact
        :return: None
        """
        if contact.service_notifications_enabled:
            contact.modified_attributes |= DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            contact.service_notifications_enabled = False
            self.daemon.get_and_register_status_brok(contact)

    def disable_event_handlers(self):
        """Disable event handlers (globally)
        Format of the line that triggers function call::

        DISABLE_EVENT_HANDLERS

        :return: None
        """
        # todo: #783 create a dedicated brok for global parameters
        if self.my_conf.enable_event_handlers:
            self.my_conf.modified_attributes |= DICT_MODATTR["MODATTR_EVENT_HANDLER_ENABLED"].value
            self.my_conf.enable_event_handlers = False
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def disable_flap_detection(self):
        """Disable flap detection (globally)
        Format of the line that triggers function call::

        DISABLE_FLAP_DETECTION

        :return: None
        """
        # todo: #783 create a dedicated brok for global parameters
        if self.my_conf.enable_flap_detection:
            self.my_conf.modified_attributes |= DICT_MODATTR["MODATTR_FLAP_DETECTION_ENABLED"].value
            self.my_conf.enable_flap_detection = False
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()
            # Is need, disable flap state for hosts and services
            for service in self.my_conf.services:
                if service.is_flapping:
                    service.is_flapping = False
                    service.flapping_changes = []
                    self.daemon.get_and_register_status_brok(service)
            for host in self.my_conf.hosts:
                if host.is_flapping:
                    host.is_flapping = False
                    host.flapping_changes = []
                    self.daemon.get_and_register_status_brok(host)

    def disable_hostgroup_host_checks(self, hostgroup):
        """Disable host checks for a hostgroup
        Format of the line that triggers function call::

        DISABLE_HOSTGROUP_HOST_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to disable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host_id in hostgroup.get_hosts():
            if host_id in self.daemon.hosts:
                self.disable_host_check(self.daemon.hosts[host_id])

    def disable_hostgroup_host_notifications(self, hostgroup):
        """Disable host notifications for a hostgroup
        Format of the line that triggers function call::

        DISABLE_HOSTGROUP_HOST_NOTIFICATIONS;<hostgroup_name>

        :param hostgroup: hostgroup to disable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host_id in hostgroup.get_hosts():
            if host_id in self.daemon.hosts:
                self.disable_host_notifications(self.daemon.hosts[host_id])

    def disable_hostgroup_passive_host_checks(self, hostgroup):
        """Disable host passive checks for a hostgroup
        Format of the line that triggers function call::

        DISABLE_HOSTGROUP_PASSIVE_HOST_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to disable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host_id in hostgroup.get_hosts():
            if host_id in self.daemon.hosts:
                self.disable_passive_host_checks(self.daemon.hosts[host_id])

    def disable_hostgroup_passive_svc_checks(self, hostgroup):
        """Disable service passive checks for a hostgroup
        Format of the line that triggers function call::

        DISABLE_HOSTGROUP_PASSIVE_SVC_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to disable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host_id in hostgroup.get_hosts():
            if host_id in self.daemon.hosts:
                for service_id in self.daemon.hosts[host_id].services:
                    if service_id in self.daemon.services:
                        self.disable_passive_svc_checks(self.daemon.services[service_id])

    def disable_hostgroup_svc_checks(self, hostgroup):
        """Disable service checks for a hostgroup
        Format of the line that triggers function call::

        DISABLE_HOSTGROUP_SVC_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to disable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host_id in hostgroup.get_hosts():
            if host_id in self.daemon.hosts:
                for service_id in self.daemon.hosts[host_id].services:
                    if service_id in self.daemon.services:
                        self.disable_svc_check(self.daemon.services[service_id])

    def disable_hostgroup_svc_notifications(self, hostgroup):
        """Disable service notifications for a hostgroup
        Format of the line that triggers function call::

        DISABLE_HOSTGROUP_SVC_NOTIFICATIONS;<hostgroup_name>

        :param hostgroup: hostgroup to disable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host_id in hostgroup.get_hosts():
            if host_id in self.daemon.hosts:
                for service_id in self.daemon.hosts[host_id].services:
                    if service_id in self.daemon.services:
                        self.disable_svc_notifications(self.daemon.services[service_id])

    def disable_host_and_child_notifications(self, host):
        """DOES NOTHING (Should disable host notifications and its child)
        Format of the line that triggers function call::

        DISABLE_HOST_AND_CHILD_NOTIFICATIONS;<host_name

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        logger.warning("The external command 'DISABLE_HOST_AND_CHILD_NOTIFICATIONS' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'DISABLE_HOST_AND_CHILD_NOTIFICATIONS: this command is not implemented!'))

    def disable_host_check(self, host):
        """Disable checks for a host
        Format of the line that triggers function call::

        DISABLE_HOST_CHECK;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if host.active_checks_enabled:
            host.modified_attributes |= DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            host.disable_active_checks(self.daemon.checks)
            self.daemon.get_and_register_status_brok(host)

    def disable_host_event_handler(self, host):
        """Disable event handlers for a host
        Format of the line that triggers function call::

        DISABLE_HOST_EVENT_HANDLER;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if host.event_handler_enabled:
            host.modified_attributes |= DICT_MODATTR["MODATTR_EVENT_HANDLER_ENABLED"].value
            host.event_handler_enabled = False
            self.daemon.get_and_register_status_brok(host)

    def disable_host_flap_detection(self, host):
        """Disable flap detection for a host
        Format of the line that triggers function call::

        DISABLE_HOST_FLAP_DETECTION;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if host.flap_detection_enabled:
            host.modified_attributes |= DICT_MODATTR["MODATTR_FLAP_DETECTION_ENABLED"].value
            host.flap_detection_enabled = False
            # Maybe the host was flapping, if so, stop flapping
            if host.is_flapping:
                host.is_flapping = False
                host.flapping_changes = []
            self.daemon.get_and_register_status_brok(host)

    def disable_host_freshness_check(self, host):
        """Disable freshness check for a host
        Format of the line that triggers function call::

        DISABLE_HOST_FRESHNESS_CHECK;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if host.check_freshness:
            host.modified_attributes |= DICT_MODATTR["MODATTR_FRESHNESS_CHECKS_ENABLED"].value
            host.check_freshness = False
            self.daemon.get_and_register_status_brok(host)

    def disable_host_freshness_checks(self):
        """Disable freshness checks (globally)
        Format of the line that triggers function call::

        DISABLE_HOST_FRESHNESS_CHECKS

        :return: None
        """
        if self.my_conf.check_host_freshness:
            self.my_conf.modified_attributes |= \
                DICT_MODATTR["MODATTR_FRESHNESS_CHECKS_ENABLED"].value
            self.my_conf.check_host_freshness = False
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def disable_host_notifications(self, host):
        """Disable notifications for a host
        Format of the line that triggers function call::

        DISABLE_HOST_NOTIFICATIONS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if host.notifications_enabled:
            host.modified_attributes |= DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            host.notifications_enabled = False
            self.daemon.get_and_register_status_brok(host)

    def disable_host_svc_checks(self, host):
        """Disable service checks for a host
        Format of the line that triggers function call::

        DISABLE_HOST_SVC_CHECKS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        for service_id in host.services:
            if service_id in self.daemon.services:
                self.disable_svc_check(self.daemon.services[service_id])
                self.daemon.get_and_register_status_brok(self.daemon.services[service_id])

    def disable_host_svc_notifications(self, host):
        """Disable services notifications for a host
        Format of the line that triggers function call::

        DISABLE_HOST_SVC_NOTIFICATIONS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        for service_id in host.services:
            if service_id in self.daemon.services:
                self.disable_svc_notifications(self.daemon.services[service_id])
                self.daemon.get_and_register_status_brok(self.daemon.services[service_id])

    def disable_notifications(self):
        """Disable notifications (globally)
        Format of the line that triggers function call::

        DISABLE_NOTIFICATIONS

        :return: None
        """
        # todo: #783 create a dedicated brok for global parameters
        if self.my_conf.enable_notifications:
            self.my_conf.modified_attributes |= DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            self.my_conf.enable_notifications = False
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def disable_passive_host_checks(self, host):
        """Disable passive checks for a host
        Format of the line that triggers function call::

        DISABLE_PASSIVE_HOST_CHECKS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if host.passive_checks_enabled:
            host.modified_attributes |= DICT_MODATTR["MODATTR_PASSIVE_CHECKS_ENABLED"].value
            host.passive_checks_enabled = False
            self.daemon.get_and_register_status_brok(host)

    def disable_passive_svc_checks(self, service):
        """Disable passive checks for a service
        Format of the line that triggers function call::

        DISABLE_PASSIVE_SVC_CHECKS;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if service.passive_checks_enabled:
            service.modified_attributes |= DICT_MODATTR["MODATTR_PASSIVE_CHECKS_ENABLED"].value
            service.passive_checks_enabled = False
            self.daemon.get_and_register_status_brok(service)

    def disable_performance_data(self):
        """Disable performance data processing (globally)
        Format of the line that triggers function call::

        DISABLE_PERFORMANCE_DATA

        :return: None
        """
        # todo: #783 create a dedicated brok for global parameters
        if self.my_conf.process_performance_data:
            self.my_conf.modified_attributes |= \
                DICT_MODATTR["MODATTR_PERFORMANCE_DATA_ENABLED"].value
            self.my_conf.process_performance_data = False
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def disable_servicegroup_host_checks(self, servicegroup):
        """Disable host checks for a servicegroup
        Format of the line that triggers function call::

        DISABLE_SERVICEGROUP_HOST_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to disable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service_id in servicegroup.get_services():
            if service_id in self.daemon.services:
                host_id = self.daemon.services[service_id].host
                self.disable_host_check(self.daemon.hosts[host_id])

    def disable_servicegroup_host_notifications(self, servicegroup):
        """Disable host notifications for a servicegroup
        Format of the line that triggers function call::

        DISABLE_SERVICEGROUP_HOST_NOTIFICATIONS;<servicegroup_name>

        :param servicegroup: servicegroup to disable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service_id in servicegroup.get_services():
            if service_id in self.daemon.services:
                host_id = self.daemon.services[service_id].host
                self.disable_host_notifications(self.daemon.hosts[host_id])

    def disable_servicegroup_passive_host_checks(self, servicegroup):
        """Disable passive host checks for a servicegroup
        Format of the line that triggers function call::

        DISABLE_SERVICEGROUP_PASSIVE_HOST_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to disable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service_id in servicegroup.get_services():
            if service_id in self.daemon.services:
                host_id = self.daemon.services[service_id].host
                self.disable_passive_host_checks(self.daemon.hosts[host_id])

    def disable_servicegroup_passive_svc_checks(self, servicegroup):
        """Disable passive service checks for a servicegroup
        Format of the line that triggers function call::

        DISABLE_SERVICEGROUP_PASSIVE_SVC_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to disable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service_id in servicegroup.get_services():
            self.disable_passive_svc_checks(self.daemon.services[service_id])

    def disable_servicegroup_svc_checks(self, servicegroup):
        """Disable service checks for a servicegroup
        Format of the line that triggers function call::

        DISABLE_SERVICEGROUP_SVC_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to disable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service_id in servicegroup.get_services():
            self.disable_svc_check(self.daemon.services[service_id])

    def disable_servicegroup_svc_notifications(self, servicegroup):
        """Disable service notifications for a servicegroup
        Format of the line that triggers function call::

        DISABLE_SERVICEGROUP_SVC_NOTIFICATIONS;<servicegroup_name>

        :param servicegroup: servicegroup to disable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service_id in servicegroup.get_services():
            self.disable_svc_notifications(self.daemon.services[service_id])

    def disable_service_flap_detection(self, service):
        """Disable flap detection for a service
        Format of the line that triggers function call::

        DISABLE_SERVICE_FLAP_DETECTION;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if service.flap_detection_enabled:
            service.modified_attributes |= DICT_MODATTR["MODATTR_FLAP_DETECTION_ENABLED"].value
            service.flap_detection_enabled = False
            # Maybe the service was flapping, if so, stop flapping
            if service.is_flapping:
                service.is_flapping = False
                service.flapping_changes = []
            self.daemon.get_and_register_status_brok(service)

    def disable_svc_freshness_check(self, service):
        """Disable freshness check for a service
        Format of the line that triggers function call::

        DISABLE_SERVICE_FRESHNESS_CHECK;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if service.check_freshness:
            service.modified_attributes |= DICT_MODATTR["MODATTR_FRESHNESS_CHECKS_ENABLED"].value
            service.check_freshness = False
            self.daemon.get_and_register_status_brok(service)

    def disable_service_freshness_checks(self):
        """Disable service freshness checks (globally)
        Format of the line that triggers function call::

        DISABLE_SERVICE_FRESHNESS_CHECKS

        :return: None
        """
        if self.my_conf.check_service_freshness:
            self.my_conf.modified_attributes |= \
                DICT_MODATTR["MODATTR_FRESHNESS_CHECKS_ENABLED"].value
            self.my_conf.check_service_freshness = False
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def disable_svc_check(self, service):
        """Disable checks for a service
        Format of the line that triggers function call::

        DISABLE_SVC_CHECK;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if service.active_checks_enabled:
            service.disable_active_checks(self.daemon.checks)
            service.modified_attributes |= \
                DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            self.daemon.get_and_register_status_brok(service)

    def disable_svc_event_handler(self, service):
        """Disable event handlers for a service
        Format of the line that triggers function call::

        DISABLE_SVC_EVENT_HANDLER;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if service.event_handler_enabled:
            service.modified_attributes |= \
                DICT_MODATTR["MODATTR_EVENT_HANDLER_ENABLED"].value
            service.event_handler_enabled = False
            self.daemon.get_and_register_status_brok(service)

    def disable_svc_flap_detection(self, service):
        """Disable flap detection for a service
        Format of the line that triggers function call::

        DISABLE_SVC_FLAP_DETECTION;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        self.disable_service_flap_detection(service)

    def disable_svc_notifications(self, service):
        """Disable notifications for a service
        Format of the line that triggers function call::

        DISABLE_SVC_NOTIFICATIONS;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if service.notifications_enabled:
            service.modified_attributes |= \
                DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            service.notifications_enabled = False
            self.daemon.get_and_register_status_brok(service)

    def enable_all_notifications_beyond_host(self, host):
        """DOES NOTHING (should enable notification beyond a host)
        Format of the line that triggers function call::

        ENABLE_ALL_NOTIFICATIONS_BEYOND_HOST;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        TODO: Implement it
        """
        logger.warning("The external command 'ENABLE_ALL_NOTIFICATIONS_BEYOND_HOST' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'ENABLE_ALL_NOTIFICATIONS_BEYOND_HOST: this command is not implemented!'))

    def enable_contactgroup_host_notifications(self, contactgroup):
        """Enable host notifications for a contactgroup
        Format of the line that triggers function call::

        ENABLE_CONTACTGROUP_HOST_NOTIFICATIONS;<contactgroup_name>

        :param contactgroup: contactgroup to enable
        :type contactgroup: alignak.objects.contactgroup.Contactgroup
        :return: None
        """
        for contact_id in contactgroup.get_contacts():
            self.enable_contact_host_notifications(self.daemon.contacts[contact_id])

    def enable_contactgroup_svc_notifications(self, contactgroup):
        """Enable service notifications for a contactgroup
        Format of the line that triggers function call::

        ENABLE_CONTACTGROUP_SVC_NOTIFICATIONS;<contactgroup_name>

        :param contactgroup: contactgroup to enable
        :type contactgroup: alignak.objects.contactgroup.Contactgroup
        :return: None
        """
        for contact_id in contactgroup.get_contacts():
            self.enable_contact_svc_notifications(self.daemon.contacts[contact_id])

    def enable_contact_host_notifications(self, contact):
        """Enable host notifications for a contact
        Format of the line that triggers function call::

        ENABLE_CONTACT_HOST_NOTIFICATIONS;<contact_name>

        :param contact: contact to enable
        :type contact: alignak.objects.contact.Contact
        :return: None
        """
        if not contact.host_notifications_enabled:
            contact.modified_attributes |= \
                DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            contact.host_notifications_enabled = True
            self.daemon.get_and_register_status_brok(contact)

    def enable_contact_svc_notifications(self, contact):
        """Enable service notifications for a contact
        Format of the line that triggers function call::

        DISABLE_CONTACT_SVC_NOTIFICATIONS;<contact_name>

        :param contact: contact to enable
        :type contact: alignak.objects.contact.Contact
        :return: None
        """
        if not contact.service_notifications_enabled:
            contact.modified_attributes |= \
                DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            contact.service_notifications_enabled = True
            self.daemon.get_and_register_status_brok(contact)

    def enable_event_handlers(self):
        """Enable event handlers (globally)
        Format of the line that triggers function call::

        ENABLE_EVENT_HANDLERS

        :return: None
        """
        # todo: #783 create a dedicated brok for global parameters
        if not self.my_conf.enable_event_handlers:
            self.my_conf.modified_attributes |= \
                DICT_MODATTR["MODATTR_EVENT_HANDLER_ENABLED"].value
            self.my_conf.enable_event_handlers = True
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def enable_flap_detection(self):
        """Enable flap detection (globally)
        Format of the line that triggers function call::

        ENABLE_FLAP_DETECTION

        :return: None
        """
        # todo: #783 create a dedicated brok for global parameters
        if not self.my_conf.enable_flap_detection:
            self.my_conf.modified_attributes |= \
                DICT_MODATTR["MODATTR_FLAP_DETECTION_ENABLED"].value
            self.my_conf.enable_flap_detection = True
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def enable_hostgroup_host_checks(self, hostgroup):
        """Enable host checks for a hostgroup
        Format of the line that triggers function call::

        ENABLE_HOSTGROUP_HOST_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to enable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host_id in hostgroup.get_hosts():
            if host_id in self.daemon.hosts:
                self.enable_host_check(self.daemon.hosts[host_id])

    def enable_hostgroup_host_notifications(self, hostgroup):
        """Enable host notifications for a hostgroup
        Format of the line that triggers function call::

        ENABLE_HOSTGROUP_HOST_NOTIFICATIONS;<hostgroup_name>

        :param hostgroup: hostgroup to enable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host_id in hostgroup.get_hosts():
            if host_id in self.daemon.hosts:
                self.enable_host_notifications(self.daemon.hosts[host_id])

    def enable_hostgroup_passive_host_checks(self, hostgroup):
        """Enable host passive checks for a hostgroup
        Format of the line that triggers function call::

        ENABLE_HOSTGROUP_PASSIVE_HOST_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to enable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host_id in hostgroup.get_hosts():
            if host_id in self.daemon.hosts:
                self.enable_passive_host_checks(self.daemon.hosts[host_id])

    def enable_hostgroup_passive_svc_checks(self, hostgroup):
        """Enable service passive checks for a hostgroup
        Format of the line that triggers function call::

        ENABLE_HOSTGROUP_PASSIVE_SVC_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to enable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host_id in hostgroup.get_hosts():
            if host_id in self.daemon.hosts:
                for service_id in self.daemon.hosts[host_id].services:
                    if service_id in self.daemon.services:
                        self.enable_passive_svc_checks(self.daemon.services[service_id])

    def enable_hostgroup_svc_checks(self, hostgroup):
        """Enable service checks for a hostgroup
        Format of the line that triggers function call::

        ENABLE_HOSTGROUP_SVC_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to enable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host_id in hostgroup.get_hosts():
            if host_id in self.daemon.hosts:
                for service_id in self.daemon.hosts[host_id].services:
                    if service_id in self.daemon.services:
                        self.enable_svc_check(self.daemon.services[service_id])

    def enable_hostgroup_svc_notifications(self, hostgroup):
        """Enable service notifications for a hostgroup
        Format of the line that triggers function call::

        ENABLE_HOSTGROUP_SVC_NOTIFICATIONS;<hostgroup_name>

        :param hostgroup: hostgroup to enable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host_id in hostgroup.get_hosts():
            if host_id in self.daemon.hosts:
                for service_id in self.daemon.hosts[host_id].services:
                    if service_id in self.daemon.services:
                        self.enable_svc_notifications(self.daemon.services[service_id])

    def enable_host_and_child_notifications(self, host):
        """DOES NOTHING (Should enable host notifications and its child)
        Format of the line that triggers function call::

        ENABLE_HOST_AND_CHILD_NOTIFICATIONS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        logger.warning("The external command 'ENABLE_HOST_AND_CHILD_NOTIFICATIONS' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'ENABLE_HOST_AND_CHILD_NOTIFICATIONS: this command is not implemented!'))

    def enable_host_check(self, host):
        """Enable checks for a host
        Format of the line that triggers function call::

        ENABLE_HOST_CHECK;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if not host.active_checks_enabled:
            host.active_checks_enabled = True
            host.modified_attributes |= \
                DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            self.daemon.get_and_register_status_brok(host)

    def enable_host_event_handler(self, host):
        """Enable event handlers for a host
        Format of the line that triggers function call::

        ENABLE_HOST_EVENT_HANDLER;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if not host.event_handler_enabled:
            host.modified_attributes |= \
                DICT_MODATTR["MODATTR_EVENT_HANDLER_ENABLED"].value
            host.event_handler_enabled = True
            self.daemon.get_and_register_status_brok(host)

    def enable_host_flap_detection(self, host):
        """Enable flap detection for a host
        Format of the line that triggers function call::

        ENABLE_HOST_FLAP_DETECTION;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if not host.flap_detection_enabled:
            host.modified_attributes |= \
                DICT_MODATTR["MODATTR_FLAP_DETECTION_ENABLED"].value
            host.flap_detection_enabled = True
            self.daemon.get_and_register_status_brok(host)

    def enable_host_freshness_check(self, host):
        """Enable freshness check for a host
        Format of the line that triggers function call::

        ENABLE_HOST_FRESHNESS_CHECK;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if not host.check_freshness:
            host.modified_attributes |= DICT_MODATTR["MODATTR_FRESHNESS_CHECKS_ENABLED"].value
            host.check_freshness = True
            self.daemon.get_and_register_status_brok(host)

    def enable_host_freshness_checks(self):
        """Enable freshness checks (globally)
        Format of the line that triggers function call::

        ENABLE_HOST_FRESHNESS_CHECKS

        :return: None
        """
        if not self.my_conf.check_host_freshness:
            self.my_conf.modified_attributes |= \
                DICT_MODATTR["MODATTR_FRESHNESS_CHECKS_ENABLED"].value
            self.my_conf.check_host_freshness = True
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def enable_host_notifications(self, host):
        """Enable notifications for a host
        Format of the line that triggers function call::

        ENABLE_HOST_NOTIFICATIONS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if not host.notifications_enabled:
            host.modified_attributes |= \
                DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            host.notifications_enabled = True
            self.daemon.get_and_register_status_brok(host)

    def enable_host_svc_checks(self, host):
        """Enable service checks for a host
        Format of the line that triggers function call::

        ENABLE_HOST_SVC_CHECKS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        for service_id in host.services:
            if service_id in self.daemon.services:
                self.enable_svc_check(self.daemon.services[service_id])
                self.daemon.get_and_register_status_brok(self.daemon.services[service_id])

    def enable_host_svc_notifications(self, host):
        """Enable services notifications for a host
        Format of the line that triggers function call::

        ENABLE_HOST_SVC_NOTIFICATIONS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        for service_id in host.services:
            if service_id in self.daemon.services:
                self.enable_svc_notifications(self.daemon.services[service_id])
                self.daemon.get_and_register_status_brok(self.daemon.services[service_id])

    def enable_notifications(self):
        """Enable notifications (globally)
        Format of the line that triggers function call::

        ENABLE_NOTIFICATIONS

        :return: None
        """
        # todo: #783 create a dedicated brok for global parameters
        if not self.my_conf.enable_notifications:
            self.my_conf.modified_attributes |= \
                DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            self.my_conf.enable_notifications = True
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def enable_passive_host_checks(self, host):
        """Enable passive checks for a host
        Format of the line that triggers function call::

        ENABLE_PASSIVE_HOST_CHECKS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if not host.passive_checks_enabled:
            host.modified_attributes |= \
                DICT_MODATTR["MODATTR_PASSIVE_CHECKS_ENABLED"].value
            host.passive_checks_enabled = True
            self.daemon.get_and_register_status_brok(host)

    def enable_passive_svc_checks(self, service):
        """Enable passive checks for a service
        Format of the line that triggers function call::

        ENABLE_PASSIVE_SVC_CHECKS;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if not service.passive_checks_enabled:
            service.modified_attributes |= \
                DICT_MODATTR["MODATTR_PASSIVE_CHECKS_ENABLED"].value
            service.passive_checks_enabled = True
            self.daemon.get_and_register_status_brok(service)

    def enable_performance_data(self):
        """Enable performance data processing (globally)
        Format of the line that triggers function call::

        ENABLE_PERFORMANCE_DATA

        :return: None
        """
        if not self.my_conf.process_performance_data:
            self.my_conf.modified_attributes |= \
                DICT_MODATTR["MODATTR_PERFORMANCE_DATA_ENABLED"].value
            self.my_conf.process_performance_data = True
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def enable_servicegroup_host_checks(self, servicegroup):
        """Enable host checks for a servicegroup
        Format of the line that triggers function call::

        ENABLE_SERVICEGROUP_HOST_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to enable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service_id in servicegroup.get_services():
            if service_id in self.daemon.services:
                host_id = self.daemon.services[service_id].host
                self.enable_host_check(self.daemon.hosts[host_id])

    def enable_servicegroup_host_notifications(self, servicegroup):
        """Enable host notifications for a servicegroup
        Format of the line that triggers function call::

        ENABLE_SERVICEGROUP_HOST_NOTIFICATIONS;<servicegroup_name>

        :param servicegroup: servicegroup to enable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service_id in servicegroup.get_services():
            if service_id in self.daemon.services:
                host_id = self.daemon.services[service_id].host
                self.enable_host_notifications(self.daemon.hosts[host_id])

    def enable_servicegroup_passive_host_checks(self, servicegroup):
        """Enable passive host checks for a servicegroup
        Format of the line that triggers function call::

        ENABLE_SERVICEGROUP_PASSIVE_HOST_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to enable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service_id in servicegroup.get_services():
            if service_id in self.daemon.services:
                host_id = self.daemon.services[service_id].host
                self.enable_passive_host_checks(self.daemon.hosts[host_id])

    def enable_servicegroup_passive_svc_checks(self, servicegroup):
        """Enable passive service checks for a servicegroup
        Format of the line that triggers function call::

        ENABLE_SERVICEGROUP_PASSIVE_SVC_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to enable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service_id in servicegroup.get_services():
            self.enable_passive_svc_checks(self.daemon.services[service_id])

    def enable_servicegroup_svc_checks(self, servicegroup):
        """Enable service checks for a servicegroup
        Format of the line that triggers function call::

        ENABLE_SERVICEGROUP_SVC_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to enable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service_id in servicegroup.get_services():
            self.enable_svc_check(self.daemon.services[service_id])

    def enable_servicegroup_svc_notifications(self, servicegroup):
        """Enable service notifications for a servicegroup
        Format of the line that triggers function call::

        ENABLE_SERVICEGROUP_SVC_NOTIFICATIONS;<servicegroup_name>

        :param servicegroup: servicegroup to enable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service_id in servicegroup.get_services():
            self.enable_svc_notifications(self.daemon.services[service_id])

    def enable_service_freshness_checks(self):
        """Enable service freshness checks (globally)
        Format of the line that triggers function call::

        ENABLE_SERVICE_FRESHNESS_CHECKS

        :return: None
        """
        if not self.my_conf.check_service_freshness:
            self.my_conf.modified_attributes |= \
                DICT_MODATTR["MODATTR_FRESHNESS_CHECKS_ENABLED"].value
            self.my_conf.check_service_freshness = True
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def enable_svc_check(self, service):
        """Enable checks for a service
        Format of the line that triggers function call::

        ENABLE_SVC_CHECK;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if not service.active_checks_enabled:
            service.modified_attributes |= \
                DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            service.active_checks_enabled = True
            self.daemon.get_and_register_status_brok(service)

    def enable_svc_event_handler(self, service):
        """Enable event handlers for a service
        Format of the line that triggers function call::

        ENABLE_SVC_EVENT_HANDLER;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if not service.event_handler_enabled:
            service.modified_attributes |= \
                DICT_MODATTR["MODATTR_EVENT_HANDLER_ENABLED"].value
            service.event_handler_enabled = True
            self.daemon.get_and_register_status_brok(service)

    def enable_svc_freshness_check(self, service):
        """Enable freshness check for a service
        Format of the line that triggers function call::

        ENABLE_SERVICE_FRESHNESS_CHECK;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if not service.check_freshness:
            service.modified_attributes |= DICT_MODATTR["MODATTR_FRESHNESS_CHECKS_ENABLED"].value
            service.check_freshness = True
            self.daemon.get_and_register_status_brok(service)

    def enable_svc_flap_detection(self, service):
        """Enable flap detection for a service
        Format of the line that triggers function call::

        ENABLE_SVC_FLAP_DETECTION;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if not service.flap_detection_enabled:
            service.modified_attributes |= \
                DICT_MODATTR["MODATTR_FLAP_DETECTION_ENABLED"].value
            service.flap_detection_enabled = True
            self.daemon.get_and_register_status_brok(service)

    def enable_svc_notifications(self, service):
        """Enable notifications for a service
        Format of the line that triggers function call::

        ENABLE_SVC_NOTIFICATIONS;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if not service.notifications_enabled:
            service.modified_attributes |= \
                DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            service.notifications_enabled = True
            self.daemon.get_and_register_status_brok(service)

    def process_file(self, file_name, delete):
        """DOES NOTHING (should process a file)
        Format of the line that triggers function call::

        PROCESS_FILE;<file_name>;<delete>

        :param file_name:  file to process
        :type file_name: str
        :param delete: delete after processing
        :type delete:
        :return: None
        """
        logger.warning("The external command 'PROCESS_FILE' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'PROCESS_FILE: this command is not implemented!'))

    def process_host_check_result(self, host, status_code, plugin_output):
        """Process host check result
        Format of the line that triggers function call::

        PROCESS_HOST_CHECK_RESULT;<host_name>;<status_code>;<plugin_output>

        :param host: host to process check to
        :type host: alignak.objects.host.Host
        :param status_code: exit code of plugin
        :type status_code: int
        :param plugin_output: plugin output
        :type plugin_output: str
        :return: None
        TODO: say that check is PASSIVE
        """
        now = time.time()
        cls = host.__class__

        # If globally disabled OR host disabled, do not launch..
        if not cls.accept_passive_checks or not host.passive_checks_enabled:
            return

        try:
            plugin_output = plugin_output.decode('utf8', 'ignore')
            logger.debug('%s > Passive host check plugin output: %s',
                         host.get_full_name(), plugin_output)
        except AttributeError:
            # Python 3 will raise an exception
            pass
        except UnicodeError:
            pass

        # Maybe the check is just too old, if so, bail out!
        if self.current_timestamp < host.last_chk:
            logger.debug('%s > Passive host check is too old (%.2f seconds). '
                         'Ignoring, check output: %s',
                         host.get_full_name(), self.current_timestamp < host.last_chk,
                         plugin_output)
            return

        chk = host.launch_check(now, self.hosts, self.services, self.timeperiods,
                                self.daemon.macromodulations, self.daemon.checkmodulations,
                                self.daemon.checks, force=True)
        # We will not have a check if an host/service is checked but it has no defined check_command
        if not chk:
            return

        # Now we 'transform the check into a result'
        # So exit_status, output and status is eaten by the host
        chk.exit_status = status_code
        chk.get_outputs(plugin_output, host.max_plugins_output_length)
        chk.status = ACT_STATUS_WAIT_CONSUME
        chk.check_time = self.current_timestamp  # we are using the external command timestamps
        # Set the corresponding host's check type to passive
        chk.set_type_passive()
        # self.daemon.nb_check_received += 1
        self.send_an_element(chk)
        # Ok now this result will be read by the scheduler the next loop

        # raise a passive check log only if needed
        if self.my_conf.log_passive_checks:
            log_level = 'info'
            if status_code == 1:  # DOWN
                log_level = 'error'
            if status_code == 2:  # UNREACHABLE
                log_level = 'warning'
            self.send_an_element(make_monitoring_log(
                log_level, 'PASSIVE HOST CHECK: %s;%d;%s;%s;%s' % (
                    host.get_name(), status_code, chk.output, chk.long_output, chk.perf_data)))

    def process_host_output(self, host, plugin_output):
        """Process host output
        Format of the line that triggers function call::

        PROCESS_HOST_OUTPUT;<host_name>;<plugin_output>

        :param host: host to process check to
        :type host: alignak.objects.host.Host
        :param plugin_output: plugin output
        :type plugin_output: str
        :return: None
        """
        self.process_host_check_result(host, host.state_id, plugin_output)

    def process_service_check_result(self, service, return_code, plugin_output):
        """Process service check result
        Format of the line that triggers function call::

        PROCESS_SERVICE_CHECK_RESULT;<host_name>;<service_description>;<return_code>;<plugin_output>

        :param service: service to process check to
        :type service: alignak.objects.service.Service
        :param return_code: exit code of plugin
        :type return_code: int
        :param plugin_output: plugin output
        :type plugin_output: str
        :return: None
        """
        now = time.time()
        cls = service.__class__

        # If globally disabled OR service disabled, do not launch..
        if not cls.accept_passive_checks or not service.passive_checks_enabled:
            return

        try:
            plugin_output = plugin_output.decode('utf8', 'ignore')
            logger.debug('%s > Passive service check plugin output: %s',
                         service.get_full_name(), plugin_output)
        except AttributeError:
            # Python 3 will raise an exception
            pass
        except UnicodeError:
            pass

        # Maybe the check is just too old, if so, bail out!
        if self.current_timestamp < service.last_chk:
            logger.debug('%s > Passive service check is too old (%d seconds). '
                         'Ignoring, check output: %s',
                         service.get_full_name(), self.current_timestamp < service.last_chk,
                         plugin_output)
            return

        # Create a check object from the external command
        chk = service.launch_check(now, self.hosts, self.services, self.timeperiods,
                                   self.daemon.macromodulations, self.daemon.checkmodulations,
                                   self.daemon.checks, force=True)
        # Should not be possible to not find the check, but if so, don't crash
        if not chk:
            logger.error('%s > Passive service check failed. None check launched !?',
                         service.get_full_name())
            return

        # Now we 'transform the check into a result'
        # So exit_status, output and status is eaten by the service
        chk.exit_status = return_code
        chk.get_outputs(plugin_output, service.max_plugins_output_length)

        logger.debug('%s > Passive service check output: %s',
                     service.get_full_name(), chk.output)

        chk.status = ACT_STATUS_WAIT_CONSUME
        chk.check_time = self.current_timestamp  # we are using the external command timestamps
        # Set the corresponding service's check type to passive
        chk.set_type_passive()
        # self.daemon.nb_check_received += 1
        self.send_an_element(chk)
        # Ok now this result will be read by the scheduler the next loop

        # raise a passive check log only if needed
        if self.my_conf.log_passive_checks:
            log_level = 'info'
            if return_code == 1:  # WARNING
                log_level = 'warning'
            if return_code == 2:  # CRITICAL
                log_level = 'error'
            self.send_an_element(make_monitoring_log(
                log_level, 'PASSIVE SERVICE CHECK: %s;%s;%d;%s;%s;%s' % (
                    self.hosts[service.host].get_name(), service.get_name(),
                    return_code, chk.output, chk.long_output, chk.perf_data)))

    def process_service_output(self, service, plugin_output):
        """Process service output
        Format of the line that triggers function call::

        PROCESS_SERVICE_OUTPUT;<host_name>;<service_description>;<plugin_output>

        :param service: service to process check to
        :type service: alignak.objects.service.Service
        :param plugin_output: plugin output
        :type plugin_output: str
        :return: None
        """
        self.process_service_check_result(service, service.state_id, plugin_output)

    def read_state_information(self):
        """Request to load the live state from the retention storage
        Format of the line that triggers function call::

        READ_STATE_INFORMATION

        :return: None
        """
        logger.warning("The external command 'READ_STATE_INFORMATION' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'READ_STATE_INFORMATION: this command is not implemented!'))

    @staticmethod
    def remove_host_acknowledgement(host):
        """Remove an acknowledgment on a host
        Format of the line that triggers function call::

        REMOVE_HOST_ACKNOWLEDGEMENT;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        host.unacknowledge_problem()

    @staticmethod
    def remove_svc_acknowledgement(service):
        """Remove an acknowledgment on a service
        Format of the line that triggers function call::

        REMOVE_SVC_ACKNOWLEDGEMENT;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        service.unacknowledge_problem()

    def restart_program(self):
        """Restart Alignak
        Format of the line that triggers function call::

        RESTART_PROGRAM

        :return: None
        """
        restart_cmd = self.commands.find_by_name('restart-alignak')
        if not restart_cmd:
            logger.error("Cannot restart Alignak : missing command named"
                         " 'restart-alignak'. Please add one")
            return
        restart_cmd_line = restart_cmd.command_line
        logger.warning("RESTART command : %s", restart_cmd_line)

        # Ok get an event handler command that will run in 15min max
        e_handler = EventHandler({'command': restart_cmd_line, 'timeout': 900})
        # Ok now run it
        e_handler.execute()
        # And wait for the command to finish
        while e_handler.status not in [ACT_STATUS_DONE, ACT_STATUS_TIMEOUT]:
            e_handler.check_finished(64000)

        log_level = 'info'
        if e_handler.status == ACT_STATUS_TIMEOUT or e_handler.exit_status != 0:
            logger.error("Cannot restart Alignak : the 'restart-alignak' command failed with"
                         " the error code '%d' and the text '%s'.",
                         e_handler.exit_status, e_handler.output)
            log_level = 'error'
        # Ok here the command succeed, we can now wait our death
        self.send_an_element(make_monitoring_log(log_level, "RESTART: %s" % (e_handler.output)))

    def reload_config(self):
        """Reload Alignak configuration
        Format of the line that triggers function call::

        RELOAD_CONFIG

        :return: None
        """
        reload_cmd = self.commands.find_by_name('reload-alignak')
        if not reload_cmd:
            logger.error("Cannot restart Alignak : missing command"
                         " named 'reload-alignak'. Please add one")
            return
        reload_cmd_line = reload_cmd.command_line
        logger.warning("RELOAD command : %s", reload_cmd_line)

        # Ok get an event handler command that will run in 15min max
        e_handler = EventHandler({'command': reload_cmd_line, 'timeout': 900})
        # Ok now run it
        e_handler.execute()
        # And wait for the command to finish
        while e_handler.status not in [ACT_STATUS_DONE, ACT_STATUS_TIMEOUT]:
            e_handler.check_finished(64000)

        log_level = 'info'
        if e_handler.status == ACT_STATUS_TIMEOUT or e_handler.exit_status != 0:
            logger.error("Cannot reload Alignak configuration: the 'reload-alignak' command failed"
                         " with the error code '%d' and the text '%s'.",
                         e_handler.exit_status, e_handler.output)
            log_level = 'error'
        # Ok here the command succeed, we can now wait our death
        self.send_an_element(make_monitoring_log(log_level, "RELOAD: %s" % (e_handler.output)))

    def save_state_information(self):
        """Request to save the live state to the retention
        Format of the line that triggers function call::

        SAVE_STATE_INFORMATION

        :return: None
        """
        logger.warning("The external command 'SAVE_STATE_INFORMATION' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'SAVE_STATE_INFORMATION: this command is not implemented!'))

    def schedule_and_propagate_host_downtime(self, host, start_time, end_time,
                                             fixed, trigger_id, duration, author, comment):
        """DOES NOTHING (Should create host downtime and start it?)
        Format of the line that triggers function call::

        SCHEDULE_AND_PROPAGATE_HOST_DOWNTIME;<host_name>;<start_time>;<end_time>;
        <fixed>;<trigger_id>;<duration>;<author>;<comment>

        :return: None
        """
        logger.warning("The external command 'SCHEDULE_AND_PROPAGATE_HOST_DOWNTIME' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'SCHEDULE_AND_PROPAGATE_HOST_DOWNTIME: this command is not implemented!'))

    def schedule_and_propagate_triggered_host_downtime(self, host, start_time, end_time, fixed,
                                                       trigger_id, duration, author, comment):
        """DOES NOTHING (Should create triggered host downtime and start it?)
        Format of the line that triggers function call::

        SCHEDULE_AND_PROPAGATE_TRIGGERED_HOST_DOWNTIME;<host_name>;<start_time>;<end_time>;<fixed>;
        <trigger_id>;<duration>;<author>;<comment>

        :return: None
        """
        logger.warning("The external command 'SCHEDULE_AND_PROPAGATE_TRIGGERED_HOST_DOWNTIME' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'SCHEDULE_AND_PROPAGATE_TRIGGERED_HOST_DOWNTIME: '
                       'this command is not implemented!'))

    def schedule_contact_downtime(self, contact, start_time, end_time, author, comment):
        """Schedule contact downtime
        Format of the line that triggers function call::

        SCHEDULE_CONTACT_DOWNTIME;<contact_name>;<start_time>;<end_time>;<author>;<comment>

        :param contact: contact to put in downtime
        :type contact: alignak.objects.contact.Contact
        :param start_time: downtime start time
        :type start_time: int
        :param end_time: downtime end time
        :type end_time: int
        :param author: downtime author
        :type author: str
        :param comment: text comment
        :type comment: str
        :return: None
        """
        data = {'ref': contact.uuid, 'start_time': start_time,
                'end_time': end_time, 'author': author, 'comment': comment}
        cdt = ContactDowntime(data)
        contact.add_downtime(cdt)
        self.daemon.get_and_register_status_brok(contact)

    def schedule_forced_host_check(self, host, check_time):
        """Schedule a forced check on a host
        Format of the line that triggers function call::

        SCHEDULE_FORCED_HOST_CHECK;<host_name>;<check_time>

        :param host: host to check
        :type host: alignak.object.host.Host
        :param check_time: time to check
        :type check_time: int
        :return: None
        """
        host.schedule(self.daemon.hosts, self.daemon.services,
                      self.daemon.timeperiods, self.daemon.macromodulations,
                      self.daemon.checkmodulations, self.daemon.checks,
                      force=True, force_time=check_time)
        self.daemon.get_and_register_status_brok(host)

    def schedule_forced_host_svc_checks(self, host, check_time):
        """Schedule a forced check on all services of a host
        Format of the line that triggers function call::

        SCHEDULE_FORCED_HOST_SVC_CHECKS;<host_name>;<check_time>

        :param host: host to check
        :type host: alignak.object.host.Host
        :param check_time: time to check
        :type check_time: int
        :return: None
        """
        for service_id in host.services:
            service = self.daemon.services[service_id]
            self.schedule_forced_svc_check(service, check_time)
            self.daemon.get_and_register_status_brok(service)

    def schedule_forced_svc_check(self, service, check_time):
        """Schedule a forced check on a service
        Format of the line that triggers function call::

        SCHEDULE_FORCED_SVC_CHECK;<host_name>;<service_description>;<check_time>

        :param service: service to check
        :type service: alignak.object.service.Service
        :param check_time: time to check
        :type check_time: int
        :return: None
        """
        service.schedule(self.daemon.hosts, self.daemon.services,
                         self.daemon.timeperiods, self.daemon.macromodulations,
                         self.daemon.checkmodulations, self.daemon.checks,
                         force=True, force_time=check_time)
        self.daemon.get_and_register_status_brok(service)

    def schedule_hostgroup_host_downtime(self, hostgroup, start_time, end_time, fixed,
                                         trigger_id, duration, author, comment):
        """Schedule a downtime for each host of a hostgroup
        Format of the line that triggers function call::

        SCHEDULE_HOSTGROUP_HOST_DOWNTIME;<hostgroup_name>;<start_time>;<end_time>;
        <fixed>;<trigger_id>;<duration>;<author>;<comment>

        :param hostgroup: hostgroup to schedule
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :param start_time: downtime start time
        :type start_time:
        :param end_time: downtime end time
        :type end_time:
        :param fixed: is downtime fixed
        :type fixed:
        :param trigger_id: downtime id that triggered this one
        :type trigger_id: str
        :param duration: downtime duration
        :type duration: int
        :param author: downtime author
        :type author: str
        :param comment: downtime comment
        :type comment: str
        :return: None
        """
        for host_id in hostgroup.get_hosts():
            if host_id in self.daemon.hosts:
                host = self.daemon.hosts[host_id]
                self.schedule_host_downtime(host, start_time, end_time, fixed,
                                            trigger_id, duration, author, comment)

    def schedule_hostgroup_svc_downtime(self, hostgroup, start_time, end_time, fixed,
                                        trigger_id, duration, author, comment):
        """Schedule a downtime for each service of each host of a hostgroup
        Format of the line that triggers function call::

        SCHEDULE_HOSTGROUP_SVC_DOWNTIME;;<hostgroup_name>;<start_time>;<end_time>;<fixed>;
        <trigger_id>;<duration>;<author>;<comment>

        :param hostgroup: hostgroup to schedule
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :param start_time: downtime start time
        :type start_time:
        :param end_time: downtime end time
        :type end_time:
        :param fixed: is downtime fixed
        :type fixed:
        :param trigger_id: downtime id that triggered this one
        :type trigger_id: str
        :param duration: downtime duration
        :type duration: int
        :param author: downtime author
        :type author: str
        :param comment: downtime comment
        :type comment: str
        :return: None
        """
        for host_id in hostgroup.get_hosts():
            if host_id in self.daemon.hosts:
                host = self.daemon.hosts[host_id]
                for service_id in host.services:
                    service = self.daemon.services[service_id]
                    self.schedule_svc_downtime(service, start_time, end_time, fixed,
                                               trigger_id, duration, author, comment)

    def schedule_host_check(self, host, check_time):
        """Schedule a check on a host
        Format of the line that triggers function call::

        SCHEDULE_HOST_CHECK;<host_name>;<check_time>

        :param host: host to check
        :type host: alignak.object.host.Host
        :param check_time: time to check
        :type check_time:
        :return: None
        """
        host.schedule(self.daemon.hosts, self.daemon.services,
                      self.daemon.timeperiods, self.daemon.macromodulations,
                      self.daemon.checkmodulations, self.daemon.checks,
                      force=False, force_time=check_time)
        self.daemon.get_and_register_status_brok(host)

    def schedule_host_downtime(self, host, start_time, end_time, fixed,
                               trigger_id, duration, author, comment):
        """Schedule a host downtime
        Format of the line that triggers function call::

        SCHEDULE_HOST_DOWNTIME;<host_name>;<start_time>;<end_time>;<fixed>;
        <trigger_id>;<duration>;<author>;<comment>

        :param host: host to schedule downtime
        :type host: alignak.object.host.Host
        :param start_time: downtime start time
        :type start_time:
        :param end_time: downtime end time
        :type end_time:
        :param fixed: is downtime fixed
        :type fixed: bool
        :param trigger_id: downtime id that triggered this one
        :type trigger_id: str
        :param duration: downtime duration
        :type duration: int
        :param author: downtime author
        :type author: str
        :param comment: downtime comment
        :type comment: str
        :return: None
        """
        data = {'ref': host.uuid, 'ref_type': host.my_type, 'start_time': start_time,
                'end_time': end_time, 'fixed': fixed, 'trigger_id': trigger_id,
                'duration': duration, 'author': author, 'comment': comment}
        downtime = Downtime(data)
        downtime.add_automatic_comment(host)
        host.add_downtime(downtime)

        self.daemon.get_and_register_status_brok(host)
        if trigger_id not in ('', 0):
            for item in self.daemon.hosts:
                if trigger_id in item.downtimes:
                    host.downtimes[trigger_id].trigger_me(downtime.uuid)

    def schedule_host_svc_checks(self, host, check_time):
        """Schedule a check on all services of a host
        Format of the line that triggers function call::

        SCHEDULE_HOST_SVC_CHECKS;<host_name>;<check_time>

        :param host: host to check
        :type host: alignak.object.host.Host
        :param check_time: time to check
        :type check_time:
        :return: None
        """
        for service_id in host.services:
            service = self.daemon.services[service_id]
            self.schedule_svc_check(service, check_time)
            self.daemon.get_and_register_status_brok(service)

    def schedule_host_svc_downtime(self, host, start_time, end_time, fixed,
                                   trigger_id, duration, author, comment):
        """Schedule a service downtime for each service of an host
        Format of the line that triggers function call::

        SCHEDULE_HOST_SVC_DOWNTIME;<host_name>;<start_time>;<end_time>;
        <fixed>;<trigger_id>;<duration>;<author>;<comment>

        :param host: host to schedule downtime
        :type host: alignak.object.host.Host
        :param start_time: downtime start time
        :type start_time:
        :param end_time: downtime end time
        :type end_time:
        :param fixed: is downtime fixed
        :type fixed: bool
        :param trigger_id: downtime id that triggered this one
        :type trigger_id: str
        :param duration: downtime duration
        :type duration: int
        :param author: downtime author
        :type author: str
        :param comment: downtime comment
        :type comment: str
        :return: None
        """
        for serv in host.services:
            self.schedule_svc_downtime(serv, start_time, end_time, fixed,
                                       trigger_id, duration, author, comment)

    def schedule_servicegroup_host_downtime(self, servicegroup, start_time, end_time,
                                            fixed, trigger_id, duration, author, comment):
        """Schedule a host downtime for each host of services in a servicegroup
        Format of the line that triggers function call::

        SCHEDULE_SERVICEGROUP_HOST_DOWNTIME;<servicegroup_name>;<start_time>;<end_time>;<fixed>;
        <trigger_id>;<duration>;<author>;<comment>

        :param servicegroup: servicegroup to schedule downtime
        :type servicegroup: alignak.object.servicegroup.Servicegroup
        :param start_time: downtime start time
        :type start_time:
        :param end_time: downtime end time
        :type end_time:
        :param fixed: is downtime fixed
        :type fixed: bool
        :param trigger_id: downtime id that triggered this one
        :type trigger_id: str
        :param duration: downtime duration
        :type duration: int
        :param author: downtime author
        :type author: str
        :param comment: downtime comment
        :type comment: str
        :return: None
        """
        for host in [s.host for s in servicegroup.get_services()]:
            self.schedule_host_downtime(host, start_time, end_time, fixed,
                                        trigger_id, duration, author, comment)

    def schedule_servicegroup_svc_downtime(self, servicegroup, start_time, end_time,
                                           fixed, trigger_id, duration, author, comment):
        """Schedule a service downtime for each service of a servicegroup
        Format of the line that triggers function call::

        SCHEDULE_SERVICEGROUP_SVC_DOWNTIME;<servicegroup_name>;<start_time>;<end_time>;
        <fixed>;<trigger_id>;<duration>;<author>;<comment>

        :param servicegroup: servicegroup to schedule downtime
        :type servicegroup: alignak.object.servicegroup.Servicegroup
        :param start_time: downtime start time
        :type start_time:
        :param end_time: downtime end time
        :type end_time:
        :param fixed: is downtime fixed
        :type fixed: bool
        :param trigger_id: downtime id that triggered this one
        :type trigger_id: str
        :param duration: downtime duration
        :type duration: int
        :param author: downtime author
        :type author: str
        :param comment: downtime comment
        :type comment: str
        :return: None
        """
        for serv in servicegroup.get_services():
            self.schedule_svc_downtime(serv, start_time, end_time, fixed,
                                       trigger_id, duration, author, comment)

    def schedule_svc_check(self, service, check_time):
        """Schedule a check on a service
        Format of the line that triggers function call::

        SCHEDULE_SVC_CHECK;<host_name>;<service_description>;<check_time>

        :param service: service to check
        :type service: alignak.object.service.Service
        :param check_time: time to check
        :type check_time:
        :return: None
        """
        service.schedule(self.daemon.hosts, self.daemon.services,
                         self.daemon.timeperiods, self.daemon.macromodulations,
                         self.daemon.checkmodulations, self.daemon.checks,
                         force=False, force_time=check_time)
        self.daemon.get_and_register_status_brok(service)

    def schedule_svc_downtime(self, service, start_time, end_time, fixed,
                              trigger_id, duration, author, comment):
        """Schedule a service downtime
        Format of the line that triggers function call::

        SCHEDULE_SVC_DOWNTIME;<host_name>;<service_description><start_time>;<end_time>;
        <fixed>;<trigger_id>;<duration>;<author>;<comment>

        :param service: service to check
        :type service: alignak.object.service.Service
        :param start_time: downtime start time
        :type start_time:
        :param end_time: downtime end time
        :type end_time:
        :param fixed: is downtime fixed
        :type fixed: bool
        :param trigger_id: downtime id that triggered this one
        :type trigger_id: int
        :param duration: downtime duration
        :type duration: int
        :param author: downtime author
        :type author: str
        :param comment: downtime comment
        :type comment: str
        :return: None
        """
        data = {'ref': service.uuid, 'ref_type': service.my_type, 'start_time': start_time,
                'end_time': end_time, 'fixed': fixed, 'trigger_id': trigger_id,
                'duration': duration, 'author': author, 'comment': comment}
        downtime = Downtime(data)
        downtime.add_automatic_comment(service)
        service.add_downtime(downtime)
        self.daemon.get_and_register_status_brok(service)
        if trigger_id not in ('', 0):
            for item in self.daemon.services:
                if trigger_id in item.downtimes:
                    service.downtimes[trigger_id].trigger_me(downtime.uuid)

    def send_custom_host_notification(self, host, options, author, comment):
        """DOES NOTHING (Should send a custom notification)
        Format of the line that triggers function call::

        SEND_CUSTOM_HOST_NOTIFICATION;<host_name>;<options>;<author>;<comment>

        :param host: host to send notif for
        :type host: alignak.object.host.Host
        :param options: notification options
        :type options:
        :param author: notification author
        :type author: str
        :param comment: notification text
        :type comment: str
        :return: None
        """
        logger.warning("The external command 'SEND_CUSTOM_HOST_NOTIFICATION' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'SEND_CUSTOM_HOST_NOTIFICATION: this command is not implemented!'))

    def send_custom_svc_notification(self, service, options, author, comment):
        """DOES NOTHING (Should send a custom notification)
        Format of the line that triggers function call::

        SEND_CUSTOM_SVC_NOTIFICATION;<host_name>;<service_description>;<options>;<author>;<comment>>

        :param service: service to send notif for
        :type service: alignak.object.service.Service
        :param options: notification options
        :type options:
        :param author: notification author
        :type author: str
        :param comment: notification text
        :type comment: str
        :return: None
        """
        logger.warning("The external command 'SEND_CUSTOM_SVC_NOTIFICATION' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'SEND_CUSTOM_SVC_NOTIFICATION: this command is not implemented!'))

    def set_host_notification_number(self, host, notification_number):
        """DOES NOTHING (Should set host notification number)
        Format of the line that triggers function call::

        SET_HOST_NOTIFICATION_NUMBER;<host_name>;<notification_number>

        :param host: host to edit
        :type host: alignak.object.host.Host
        :param notification_number: new value to set
        :type notification_number:
        :return: None
        """
        logger.warning("The external command 'SET_HOST_NOTIFICATION_NUMBER' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'SET_HOST_NOTIFICATION_NUMBER: this command is not implemented!'))

    def set_svc_notification_number(self, service, notification_number):
        """DOES NOTHING (Should set host notification number)
        Format of the line that triggers function call::

        SET_SVC_NOTIFICATION_NUMBER;<host_name>;<service_description>;<notification_number>

        :param service: service to edit
        :type service: alignak.object.service.Service
        :param notification_number: new value to set
        :type notification_number:
        :return: None
        """
        logger.warning("The external command 'SET_SVC_NOTIFICATION_NUMBER' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'SET_SVC_NOTIFICATION_NUMBER: this command is not implemented!'))

    def shutdown_program(self):
        """DOES NOTHING (Should shutdown Alignak)
        Format of the line that triggers function call::

        SHUTDOWN_PROGRAM

        :return: None
        """
        logger.warning("The external command 'SHUTDOWN_PROGRAM' "
                       "is not currently implemented in Alignak. If you really need it, "
                       "request for its implementation in the project repository: "
                       "https://github.com/Alignak-monitoring/alignak")
        self.send_an_element(make_monitoring_log(
            'warning', 'SHUTDOWN_PROGRAM: this command is not implemented!'))

    def start_accepting_passive_host_checks(self):
        """Enable passive host check submission (globally)
        Format of the line that triggers function call::

        START_ACCEPTING_PASSIVE_HOST_CHECKS

        :return: None
        """
        # todo: #783 create a dedicated brok for global parameters
        if not self.my_conf.accept_passive_host_checks:
            self.my_conf.modified_attributes |= DICT_MODATTR["MODATTR_PASSIVE_CHECKS_ENABLED"].value
            self.my_conf.accept_passive_host_checks = True
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def start_accepting_passive_svc_checks(self):
        """Enable passive service check submission (globally)
        Format of the line that triggers function call::

        START_ACCEPTING_PASSIVE_SVC_CHECKS

        :return: None
        """
        # todo: #783 create a dedicated brok for global parameters
        if not self.my_conf.accept_passive_service_checks:
            self.my_conf.modified_attributes |= DICT_MODATTR["MODATTR_PASSIVE_CHECKS_ENABLED"].value
            self.my_conf.accept_passive_service_checks = True
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def start_executing_host_checks(self):
        """Enable host check execution (globally)
        Format of the line that triggers function call::

        START_EXECUTING_HOST_CHECKS

        :return: None
        """
        # todo: #783 create a dedicated brok for global parameters
        if not self.my_conf.execute_host_checks:
            self.my_conf.modified_attributes |= DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            self.my_conf.execute_host_checks = True
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def start_executing_svc_checks(self):
        """Enable service check execution (globally)
        Format of the line that triggers function call::

        START_EXECUTING_SVC_CHECKS

        :return: None
        """
        # todo: #783 create a dedicated brok for global parameters
        if not self.my_conf.execute_service_checks:
            self.my_conf.modified_attributes |= DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            self.my_conf.execute_service_checks = True
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def stop_accepting_passive_host_checks(self):
        """Disable passive host check submission (globally)
        Format of the line that triggers function call::

        STOP_ACCEPTING_PASSIVE_HOST_CHECKS

        :return: None
        """
        if self.my_conf.accept_passive_host_checks:
            self.my_conf.modified_attributes |= DICT_MODATTR["MODATTR_PASSIVE_CHECKS_ENABLED"].value
            self.my_conf.accept_passive_host_checks = False
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def stop_accepting_passive_svc_checks(self):
        """Disable passive service check submission (globally)
        Format of the line that triggers function call::

        STOP_ACCEPTING_PASSIVE_SVC_CHECKS

        :return: None
        """
        if self.my_conf.accept_passive_service_checks:
            self.my_conf.modified_attributes |= DICT_MODATTR["MODATTR_PASSIVE_CHECKS_ENABLED"].value
            self.my_conf.accept_passive_service_checks = False
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def stop_executing_host_checks(self):
        """Disable host check execution (globally)
        Format of the line that triggers function call::

        STOP_EXECUTING_HOST_CHECKS

        :return: None
        """
        if self.my_conf.execute_host_checks:
            self.my_conf.modified_attributes |= DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            self.my_conf.execute_host_checks = False
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def stop_executing_svc_checks(self):
        """Disable service check execution (globally)
        Format of the line that triggers function call::

        STOP_EXECUTING_SVC_CHECKS

        :return: None
        """
        if self.my_conf.execute_service_checks:
            self.my_conf.modified_attributes |= DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            self.my_conf.execute_service_checks = False
            self.my_conf.explode_global_conf()
            self.daemon.update_program_status()

    def launch_svc_event_handler(self, service):
        """Launch event handler for a service
        Format of the line that triggers function call::

        LAUNCH_SVC_EVENT_HANDLER;<host_name>;<service_description>

        :param service: service to execute the event handler
        :type service: alignak.objects.service.Service
        :return: None
        """
        service.get_event_handlers(self.hosts, self.daemon.macromodulations,
                                   self.daemon.timeperiods, ext_cmd=True)

    def launch_host_event_handler(self, host):
        """Launch event handler for a service
        Format of the line that triggers function call::

        LAUNCH_HOST_EVENT_HANDLER;<host_name>

        :param host: host to execute the event handler
        :type host: alignak.objects.host.Host
        :return: None
        """
        host.get_event_handlers(self.hosts, self.daemon.macromodulations, self.daemon.timeperiods,
                                ext_cmd=True)
