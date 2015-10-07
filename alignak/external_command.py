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
import os
import time
import re

from alignak.util import to_int, to_bool, split_semicolon
from alignak.downtime import Downtime
from alignak.contactdowntime import ContactDowntime
from alignak.comment import Comment
from alignak.commandcall import CommandCall
from alignak.log import logger, naglog_result
from alignak.objects.pollerlink import PollerLink
from alignak.eventhandler import EventHandler
from alignak.brok import Brok
from alignak.misc.common import DICT_MODATTR


class ExternalCommand:
    """ExternalCommand class is only an object with a cmd_line attribute.
    All parsing and execution is done in manager

    """
    my_type = 'externalcommand'

    def __init__(self, cmd_line):
        self.cmd_line = cmd_line


class ExternalCommandManager:
    """ExternalCommandManager class managed all external command sent to Alignak
    It basically parses arguments and execute the right function

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
            {'global': False, 'args': ['service', 'to_bool', 'author', None]},
        'add_host_comment':
            {'global': False, 'args': ['host', 'to_bool', 'author', None]},
        'acknowledge_svc_problem':
            {'global': False, 'args': ['service', 'to_int', 'to_bool', 'to_bool', 'author', None]},
        'acknowledge_host_problem':
            {'global': False, 'args': ['host', 'to_int', 'to_bool', 'to_bool', 'author', None]},
        'acknowledge_svc_problem_expire':
            {'global': False, 'args': ['service', 'to_int', 'to_bool',
                                       'to_bool', 'to_int', 'author', None]},
        'acknowledge_host_problem_expire':
            {'global': False,
             'args': ['host', 'to_int', 'to_bool', 'to_bool', 'to_int', 'author', None]},
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
        'change_svc_modattr':
            {'global': False, 'args': ['service', 'to_int']},
        'change_svc_notification_timeperiod':
            {'global': False, 'args': ['service', 'time_period']},
        'delay_host_notification':
            {'global': False, 'args': ['host', 'to_int']},
        'delay_svc_notification':
            {'global': False, 'args': ['service', 'to_int']},
        'del_all_host_comments':
            {'global': False, 'args': ['host']},
        'del_all_host_downtimes':
            {'global': False, 'args': ['host']},
        'del_all_svc_comments':
            {'global': False, 'args': ['service']},
        'del_all_svc_downtimes':
            {'global': False, 'args': ['service']},
        'del_contact_downtime':
            {'global': True, 'args': ['to_int']},
        'del_host_comment':
            {'global': True, 'args': ['to_int']},
        'del_host_downtime':
            {'global': True, 'args': ['to_int']},
        'del_svc_comment':
            {'global': True, 'args': ['to_int']},
        'del_svc_downtime':
            {'global': True, 'args': ['to_int']},
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
                                      'to_bool', 'to_int', 'to_int', 'author', None]},
        'schedule_hostgroup_svc_downtime':
            {'global': True, 'args': ['host_group', 'to_int', 'to_int', 'to_bool',
                                      'to_int', 'to_int', 'author', None]},
        'schedule_host_check':
            {'global': False, 'args': ['host', 'to_int']},
        'schedule_host_downtime':
            {'global': False, 'args': ['host', 'to_int', 'to_int', 'to_bool',
                                       'to_int', 'to_int', 'author', None]},
        'schedule_host_svc_checks':
            {'global': False, 'args': ['host', 'to_int']},
        'schedule_host_svc_downtime':
            {'global': False, 'args': ['host', 'to_int', 'to_int', 'to_bool',
                                       'to_int', 'to_int', 'author', None]},
        'schedule_servicegroup_host_downtime':
            {'global': True, 'args': ['service_group', 'to_int', 'to_int', 'to_bool',
                                      'to_int', 'to_int', 'author', None]},
        'schedule_servicegroup_svc_downtime':
            {'global': True, 'args': ['service_group', 'to_int', 'to_int', 'to_bool',
                                      'to_int', 'to_int', 'author', None]},
        'schedule_svc_check':
            {'global': False, 'args': ['service', 'to_int']},
        'schedule_svc_downtime': {'global': False, 'args': ['service', 'to_int', 'to_int',
                                                            'to_bool', 'to_int', 'to_int',
                                                            'author', None]},
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
        'start_obsessing_over_host':
            {'global': False, 'args': ['host']},
        'start_obsessing_over_host_checks':
            {'global': True, 'args': []},
        'start_obsessing_over_svc':
            {'global': False, 'args': ['service']},
        'start_obsessing_over_svc_checks':
            {'global': True, 'args': []},
        'stop_accepting_passive_host_checks':
            {'global': True, 'args': []},
        'stop_accepting_passive_svc_checks':
            {'global': True, 'args': []},
        'stop_executing_host_checks':
            {'global': True, 'args': []},
        'stop_executing_svc_checks':
            {'global': True, 'args': []},
        'stop_obsessing_over_host':
            {'global': False, 'args': ['host']},
        'stop_obsessing_over_host_checks':
            {'global': True, 'args': []},
        'stop_obsessing_over_svc':
            {'global': False, 'args': ['service']},
        'stop_obsessing_over_svc_checks':
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

    def __init__(self, conf, mode):
        self.mode = mode
        if conf:
            self.conf = conf
            self.hosts = conf.hosts
            self.services = conf.services
            self.contacts = conf.contacts
            self.hostgroups = conf.hostgroups
            self.commands = conf.commands
            self.servicegroups = conf.servicegroups
            self.contactgroups = conf.contactgroups
            self.timeperiods = conf.timeperiods
            self.pipe_path = conf.command_file

        self.fifo = None
        self.cmd_fragments = ''
        if self.mode == 'dispatcher':
            self.confs = conf.confs
        # Will change for each command read, so if a command need it,
        # it can get it
        self.current_timestamp = 0

    def load_scheduler(self, scheduler):
        """Setter for scheduler attribute

        :param scheduler: scheduler to set
        :type scheduler: object
        :return: None
        """
        self.sched = scheduler

    def load_arbiter(self, arbiter):
        """Setter for arbiter attribute

        :param arbiter: arbiter to set
        :type arbiter: object
        :return: None
        """
        self.arbiter = arbiter

    def load_receiver(self, receiver):
        """Setter for receiver attribute

        :param receiver: receiver to set
        :type receiver: object
        :return: None
        """
        self.receiver = receiver

    def open(self):
        """Create if necessary and open a pipe
        (Won't work under Windows)

        :return: pipe file descriptor
        :rtype: file
        """
        # At the first open del and create the fifo
        if self.fifo is None:
            if os.path.exists(self.pipe_path):
                os.unlink(self.pipe_path)

            if not os.path.exists(self.pipe_path):
                os.umask(0)
                try:
                    os.mkfifo(self.pipe_path, 0660)
                    open(self.pipe_path, 'w+', os.O_NONBLOCK)
                except OSError, exp:
                    self.error("Pipe creation failed (%s): %s" % (self.pipe_path, str(exp)))
                    return None
        self.fifo = os.open(self.pipe_path, os.O_NONBLOCK)
        return self.fifo

    def get(self):
        """Get external commands from fifo

        :return: external commands
        :rtype: list[alignak.external_command.ExternalCommand]
        """
        buf = os.read(self.fifo, 8096)
        res = []
        fullbuf = len(buf) == 8096 and True or False
        # If the buffer ended with a fragment last time, prepend it here
        buf = self.cmd_fragments + buf
        buflen = len(buf)
        self.cmd_fragments = ''
        if fullbuf and buf[-1] != '\n':
            # The buffer was full but ends with a command fragment
            res.extend([ExternalCommand(s) for s in (buf.split('\n'))[:-1] if s])
            self.cmd_fragments = (buf.split('\n'))[-1]
        elif buflen:
            # The buffer is either half-filled or full with a '\n' at the end.
            res.extend([ExternalCommand(s) for s in buf.split('\n') if s])
        else:
            # The buffer is empty. We "reset" the fifo here. It will be
            # re-opened in the main loop.
            os.close(self.fifo)
        return res

    def resolve_command(self, excmd):
        """Parse command and dispatch it (to sched for example) if necessary
        If the command is not global it will be executed.

        :param excmd: external command to handle
        :type excmd: alignak.external_command.ExternalCommand
        :return: None
        """
        # Maybe the command is invalid. Bailout
        try:
            command = excmd.cmd_line
        except AttributeError, exp:
            logger.debug("resolve_command:: error with command %s: %s", excmd, exp)
            return

        # Strip and get utf8 only strings
        command = command.strip()

        # Only log if we are in the Arbiter
        if self.mode == 'dispatcher' and self.conf.log_external_commands:
            # Fix #1263
            # logger.info('EXTERNAL COMMAND: ' + command.rstrip())
            naglog_result('info', 'EXTERNAL COMMAND: ' + command.rstrip())
        res = self.get_command_and_args(command, excmd)

        # If we are a receiver, bail out here
        if self.mode == 'receiver':
            return

        if res is not None:
            is_global = res['global']
            if not is_global:
                c_name = res['c_name']
                args = res['args']
                logger.debug("Got commands %s %s", c_name, str(args))
                getattr(self, c_name)(*args)
            else:
                command = res['cmd']
                self.dispatch_global_command(command)

    def search_host_and_dispatch(self, host_name, command, extcmd):
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
            logger.info("Receiver looking a scheduler for the external command %s %s",
                        host_name, command)
            sched = self.receiver.get_sched_from_hname(host_name)
            if sched:
                host_found = True
                logger.debug("Receiver found a scheduler: %s", sched)
                logger.info("Receiver pushing external command to scheduler %s", sched)
                sched['external_commands'].append(extcmd)
        else:
            for cfg in self.confs.values():
                if cfg.hosts.find_by_name(host_name) is not None:
                    logger.debug("Host %s found in a configuration", host_name)
                    if cfg.is_assigned:
                        host_found = True
                        sched = cfg.assigned_to
                        logger.debug("Sending command to the scheduler %s", sched.get_name())
                        # sched.run_external_command(command)
                        sched.external_commands.append(command)
                        break
                    else:
                        logger.warning("Problem: a configuration is found, but is not assigned!")
        if not host_found:
            if getattr(self, 'receiver',
                       getattr(self, 'arbiter', None)).accept_passive_unknown_check_results:
                brok = self.get_unknown_check_result_brok(command)
                getattr(self, 'receiver', getattr(self, 'arbiter', None)).add(brok)
            else:
                logger.warning("Passive check result was received for host '%s', "
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

        brok = Brok('unknown_%s_check_result' % match.group(2).lower(), data)

        return brok

    def dispatch_global_command(self, command):
        """Send command to scheduler, it's a global one

        :param command: command to send
        :type command: alignak.external_command.ExternalCommand
        :return: None
        """
        for sched in self.conf.schedulers:
            logger.debug("Sending a command '%s' to scheduler %s", command, sched)
            if sched.alive:
                # sched.run_external_command(command)
                sched.external_commands.append(command)

    def get_command_and_args(self, command, extcmd=None):
        """Parse command and get args

        :param command: command line to parse
        :type command: str
        :param extcmd: external command object (used to dispatch)
        :type extcmd: None | object
        :return: Dict containing command and arg ::

        {'global': False, 'c_name': c_name, 'args': args}

        :rtype: dict | None
        """
        # safe_print("Trying to resolve", command)
        command = command.rstrip()
        elts = split_semicolon(command)  # danger!!! passive checkresults with perfdata
        part1 = elts[0]

        elts2 = part1.split(' ')
        # print "Elts2:", elts2
        if len(elts2) != 2:
            logger.debug("Malformed command '%s'", command)
            return None
        timestamp = elts2[0]
        # Now we will get the timestamps as [123456]
        if not timestamp.startswith('[') or not timestamp.endswith(']'):
            logger.debug("Malformed command '%s'", command)
            return None
        # Ok we remove the [ ]
        timestamp = timestamp[1:-1]
        try:  # is an int or not?
            self.current_timestamp = to_int(timestamp)
        except ValueError:
            logger.debug("Malformed command '%s'", command)
            return None

        # Now get the command
        c_name = elts2[1].lower()

        # safe_print("Get command name", c_name)
        if c_name not in ExternalCommandManager.commands:
            logger.debug("Command '%s' is not recognized, sorry", c_name)
            return None

        # Split again based on the number of args we expect. We cannot split
        # on every ; because this character may appear in the perfdata of
        # passive check results.
        entry = ExternalCommandManager.commands[c_name]

        # Look if the command is purely internal or not
        internal = False
        if 'internal' in entry and entry['internal']:
            internal = True

        numargs = len(entry['args'])
        if numargs and 'service' in entry['args']:
            numargs += 1
        elts = split_semicolon(command, numargs)

        logger.debug("mode= %s, global= %s", self.mode, str(entry['global']))
        if self.mode == 'dispatcher' and entry['global']:
            if not internal:
                logger.debug("Command '%s' is a global one, we resent it to all schedulers", c_name)
                return {'global': True, 'cmd': command}

        # print "Is global?", c_name, entry['global']
        # print "Mode:", self.mode
        # print "This command have arguments:", entry['args'], len(entry['args'])

        args = []
        i = 1
        in_service = False
        tmp_host = ''
        try:
            for elt in elts[1:]:
                logger.debug("Searching for a new arg: %s (%d)", elt, i)
                val = elt.strip()
                if val.endswith('\n'):
                    val = val[:-1]

                logger.debug("For command arg: %s", val)

                if not in_service:
                    type_searched = entry['args'][i - 1]
                    # safe_print("Search for a arg", type_searched)

                    if type_searched == 'host':
                        if self.mode == 'dispatcher' or self.mode == 'receiver':
                            self.search_host_and_dispatch(val, command, extcmd)
                            return None
                        host = self.hosts.find_by_name(val)
                        if host is not None:
                            args.append(host)
                        elif self.conf.accept_passive_unknown_check_results:
                            brok = self.get_unknown_check_result_brok(command)
                            self.sched.add_brok(brok)

                    elif type_searched == 'contact':
                        contact = self.contacts.find_by_name(val)
                        if contact is not None:
                            args.append(contact)

                    elif type_searched == 'time_period':
                        timeperiod = self.timeperiods.find_by_name(val)
                        if timeperiod is not None:
                            args.append(timeperiod)

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
                        contactgroup = self.contact_groups.find_by_name(val)
                        if contactgroup is not None:
                            args.append(contactgroup)

                    # special case: service are TWO args host;service, so one more loop
                    # to get the two parts
                    elif type_searched == 'service':
                        in_service = True
                        tmp_host = elt.strip()
                        # safe_print("TMP HOST", tmp_host)
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

                    # safe_print("Got service full", tmp_host, srv_name)
                    serv = self.services.find_srv_by_name_and_hostname(tmp_host, srv_name)
                    if serv is not None:
                        args.append(serv)
                    elif self.conf.accept_passive_unknown_check_results:
                        brok = self.get_unknown_check_result_brok(command)
                        self.sched.add_brok(brok)
                    else:
                        logger.warning(
                            "A command was received for service '%s' on host '%s', "
                            "but the service could not be found!", srv_name, tmp_host)

        except IndexError:
            logger.debug("Sorry, the arguments are not corrects")
            return None
        # safe_print('Finally got ARGS:', args)
        if len(args) == len(entry['args']):
            # safe_print("OK, we can call the command", c_name, "with", args)
            return {'global': False, 'c_name': c_name, 'args': args}
            # f = getattr(self, c_name)
            # apply(f, args)
        else:
            logger.debug("Sorry, the arguments are not corrects (%s)", str(args))
            return None

    def change_contact_modsattr(self, contact, value):
        """Change contact modified service attribute value
        Format of the line that triggers function call::

        CHANGE_CONTACT_MODSATTR;<contact_name>;<value>

        :param contact: contact to edit
        :type contact: alignak.objects.contact.Contact
        :param value: new value to set
        :type value: str
        :return: None
        """
        contact.modified_service_attributes = long(value)

    def change_contact_modhattr(self, contact, value):
        """Change contact modified host attribute value
        Format of the line that triggers function call::

        CHANGE_CONTACT_MODHATTR;<contact_name>;<value>

        :param contact: contact to edit
        :type contact: alignak.objects.contact.Contact
        :param value: new value to set
        :type value:str
        :return: None
        """
        contact.modified_host_attributes = long(value)

    def change_contact_modattr(self, contact, value):
        """Change contact modified attribute value
        Format of the line that triggers function call::

        CHANGE_CONTACT_MODATTR;<contact_name>;<value>

        :param contact: contact to edit
        :type contact: alignak.objects.contact.Contact
        :param value: new value to set
        :type value: str
        :return: None
        """
        contact.modified_attributes = long(value)

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
        contact.modified_host_attributes |= DICT_MODATTR["MODATTR_NOTIFICATION_TIMEPERIOD"].value
        contact.host_notification_period = notification_timeperiod
        self.sched.get_and_register_status_brok(contact)

    def add_svc_comment(self, service, persistent, author, comment):
        """Add a service comment
        Format of the line that triggers function call::

        ADD_SVC_COMMENT;<host_name>;<service_description>;<persistent>;<author>;<comment>

        :param service: service to add the comment
        :type service: alignak.objects.service.Service
        :param persistent: is comment persistent (for reboot) or not
        :type persistent: bool
        :param author: author name
        :type author: str
        :param comment: text comment
        :type comment: str
        :return: None
        """
        comm = Comment(service, persistent, author, comment, 2, 1, 1, False, 0)
        service.add_comment(comm)
        self.sched.add(comm)

    def add_host_comment(self, host, persistent, author, comment):
        """Add a host comment
        Format of the line that triggers function call::

        ADD_HOST_COMMENT;<host_name>;<persistent>;<author>;<comment>

        :param host: host to add the comment
        :type host: alignak.objects.host.Host
        :param persistent: is comment persistent (for reboot) or not
        :type persistent: bool
        :param author: author name
        :type author: str
        :param comment: text comment
        :type comment: str
        :return: None
        """
        comm = Comment(host, persistent, author, comment, 1, 1, 1, False, 0)
        host.add_comment(comm)
        self.sched.add(comm)

    def acknowledge_svc_problem(self, service, sticky, notify, persistent, author, comment):
        """Acknowledge a service problem
        Format of the line that triggers function call::

        ACKNOWLEDGE_SVC_PROBLEM;<host_name>;<service_description>;<sticky>;<notify>;<persistent>;
        <author>;<comment>

        :param service: service to acknowledge the problem
        :type service: alignak.objects.service.Service
        :param sticky: acknowledge will be always present is host return in UP state
        :type sticky: integer
        :param notify: if to 1, send a notification
        :type notify: integer
        :param persistent: if 1, keep this acknowledge when Alignak restart
        :type persistent: integer
        :param author: name of the author or the acknowledge
        :type author: str
        :param comment: comment (description) of the acknowledge
        :type comment: str
        :return: None
        """
        service.acknowledge_problem(sticky, notify, persistent, author, comment)

    def acknowledge_host_problem(self, host, sticky, notify, persistent, author, comment):
        """Acknowledge a host problem
        Format of the line that triggers function call::

        ACKNOWLEDGE_HOST_PROBLEM;<host_name>;<sticky>;<notify>;<persistent>;<author>;<comment>

        :param host: host to acknowledge the problem
        :type host: alignak.objects.host.Host
        :param sticky: acknowledge will be always present is host return in UP state
        :type sticky: integer
        :param notify: if to 1, send a notification
        :type notify: integer
        :param persistent: if 1, keep this acknowledge when Alignak restart
        :type persistent: integer
        :param author: name of the author or the acknowledge
        :type author: str
        :param comment: comment (description) of the acknowledge
        :type comment: str
        :return: None
        TODO: add a better ACK management
        """
        host.acknowledge_problem(sticky, notify, persistent, author, comment)

    def acknowledge_svc_problem_expire(self, service, sticky, notify,
                                       persistent, end_time, author, comment):
        """Acknowledge a service problem with expire time for this acknowledgement
        Format of the line that triggers function call::

        ACKNOWLEDGE_SVC_PROBLEM;<host_name>;<service_description>;<sticky>;<notify>;<persistent>;
        <end_time>;<author>;<comment>

        :param service: service to acknowledge the problem
        :type service: alignak.objects.service.Service
        :param sticky: acknowledge will be always present is host return in UP state
        :type sticky: integer
        :param notify: if to 1, send a notification
        :type notify: integer
        :param persistent: if 1, keep this acknowledge when Alignak restart
        :type persistent: integer
        :param end_time: end (timeout) of this acknowledge in seconds(timestamp) (0 to never end)
        :type end_time: int
        :param author: name of the author or the acknowledge
        :type author: str
        :param comment: comment (description) of the acknowledge
        :type comment: str
        :return: None
        """
        service.acknowledge_problem(sticky, notify, persistent, author, comment, end_time=end_time)

    def acknowledge_host_problem_expire(self, host, sticky, notify,
                                        persistent, end_time, author, comment):
        """Acknowledge a host problem with expire time for this acknowledgement
        Format of the line that triggers function call::

        ACKNOWLEDGE_HOST_PROBLEM;<host_name>;<sticky>;<notify>;<persistent>;<end_time>;
        <author>;<comment>

        :param host: host to acknowledge the problem
        :type host: alignak.objects.host.Host
        :param sticky: acknowledge will be always present is host return in UP state
        :type sticky: integer
        :param notify: if to 1, send a notification
        :type notify: integer
        :param persistent: if 1, keep this acknowledge when Alignak restart
        :type persistent: integer
        :param end_time: end (timeout) of this acknowledge in seconds(timestamp) (0 to never end)
        :type end_time: int
        :param author: name of the author or the acknowledge
        :type author: str
        :param comment: comment (description) of the acknowledge
        :type comment: str
        :return: None
        TODO: add a better ACK management
        """
        host.acknowledge_problem(sticky, notify, persistent, author, comment, end_time=end_time)

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
        self.sched.get_and_register_status_brok(contact)

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
        contact.modified_attributes |= DICT_MODATTR["MODATTR_CUSTOM_VARIABLE"].value
        contact.customs[varname.upper()] = varvalue

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
        host.modified_attributes |= DICT_MODATTR["MODATTR_CUSTOM_VARIABLE"].value
        host.customs[varname.upper()] = varvalue

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
        service.modified_attributes |= DICT_MODATTR["MODATTR_CUSTOM_VARIABLE"].value
        service.customs[varname.upper()] = varvalue

    def change_global_host_event_handler(self, event_handler_command):
        """DOES NOTHING (should change global host event handler)
        Format of the line that triggers function call::

        CHANGE_GLOBAL_HOST_EVENT_HANDLER;<event_handler_command>

        :param event_handler_command: new event handler
        :type event_handler_command:
        :return: None
        TODO: DICT_MODATTR["MODATTR_EVENT_HANDLER_COMMAND"].value
        """
        pass

    def change_global_svc_event_handler(self, event_handler_command):
        """DOES NOTHING (should change global service event handler)
        Format of the line that triggers function call::

        CHANGE_GLOBAL_SVC_EVENT_HANDLER;<event_handler_command>

        :param event_handler_command: new event handler
        :type event_handler_command:
        :return: None
        TODO: DICT_MODATTR["MODATTR_EVENT_HANDLER_COMMAND"].value
        """
        pass

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
        host.check_command = CommandCall(self.commands, check_command, poller_tag=host.poller_tag)
        self.sched.get_and_register_status_brok(host)

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
        self.sched.get_and_register_status_brok(host)

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
        host.event_handler = CommandCall(self.commands, event_handler_command)
        self.sched.get_and_register_status_brok(host)

    def change_host_modattr(self, host, value):
        """Change host modified attributes
        Format of the line that triggers function call::

        CHANGE_HOST_MODATTR;<host_name>;<value>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :param value: new value to set
        :type value: str
        :return: None
        """
        host.modified_attributes = long(value)

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
        if host.state_type == 'HARD' and host.state == 'UP' and host.attempt > 1:
            host.attempt = host.max_check_attempts
        self.sched.get_and_register_status_brok(host)

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
        if service.state_type == 'HARD' and service.state == 'OK' and service.attempt > 1:
            service.attempt = service.max_check_attempts
        self.sched.get_and_register_status_brok(service)

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
            host.schedule(force=False, force_time=int(time.time()))
        self.sched.get_and_register_status_brok(host)

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
            service.schedule(force=False, force_time=int(time.time()))
        self.sched.get_and_register_status_brok(service)

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
        self.sched.get_and_register_status_brok(host)

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
        self.sched.get_and_register_status_brok(service)

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
        service.check_command = CommandCall(self.commands, check_command,
                                            poller_tag=service.poller_tag)
        self.sched.get_and_register_status_brok(service)

    def change_svc_check_timeperiod(self, service, check_timeperiod):
        """Modify service check timeperiod
        Format of the line that triggers function call::

        CHANGE_SVC_CHECK_TIMEPERIOD;<host_name>;<service_description>;<check_timeperiod>

        :param service: service to modify check timeperiod
        :type service: alignak.objects.service.Service
        :param timeperiod: timeperiod object
        :type timeperiod: alignak.objects.timeperiod.Timeperiod
        :return: None
        """
        service.modified_attributes |= DICT_MODATTR["MODATTR_CHECK_TIMEPERIOD"].value
        service.check_period = check_timeperiod
        self.sched.get_and_register_status_brok(service)

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
        service.event_handler = CommandCall(self.commands, event_handler_command)
        self.sched.get_and_register_status_brok(service)

    def change_svc_modattr(self, service, value):
        """Change service modified attributes
        Format of the line that triggers function call::

        CHANGE_SVC_MODATTR;<host_name>;<service_description>;<value>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :param value: new value to set
        :type value: str
        :return: None
        """
        # This is not enough.
        # We need to also change each of the needed attributes.
        previous_value = service.modified_attributes
        future_value = long(value)
        changes = future_value ^ previous_value

        for modattr in [
                "MODATTR_NOTIFICATIONS_ENABLED", "MODATTR_ACTIVE_CHECKS_ENABLED",
                "MODATTR_PASSIVE_CHECKS_ENABLED", "MODATTR_EVENT_HANDLER_ENABLED",
                "MODATTR_FLAP_DETECTION_ENABLED", "MODATTR_PERFORMANCE_DATA_ENABLED",
                "MODATTR_OBSESSIVE_HANDLER_ENABLED", "MODATTR_FRESHNESS_CHECKS_ENABLED"]:
            if changes & DICT_MODATTR[modattr].value:
                logger.info("[CHANGE_SVC_MODATTR] Reset %s", modattr)
                setattr(service, DICT_MODATTR[modattr].attribute, not
                        getattr(service, DICT_MODATTR[modattr].attribute))

        # TODO : Handle not boolean attributes.
        # ["MODATTR_EVENT_HANDLER_COMMAND",
        # "MODATTR_CHECK_COMMAND", "MODATTR_NORMAL_CHECK_INTERVAL",
        # "MODATTR_RETRY_CHECK_INTERVAL",
        # "MODATTR_MAX_CHECK_ATTEMPTS", "MODATTR_FRESHNESS_CHECKS_ENABLED",
        # "MODATTR_CHECK_TIMEPERIOD", "MODATTR_CUSTOM_VARIABLE", "MODATTR_NOTIFICATION_TIMEPERIOD"]

        service.modified_attributes = future_value

        # And we need to push the information to the scheduler.
        self.sched.get_and_register_status_brok(service)

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
        self.sched.get_and_register_status_brok(service)

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
        self.sched.get_and_register_status_brok(host)

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
        self.sched.get_and_register_status_brok(service)

    def del_all_host_comments(self, host):
        """Delete all host comments
        Format of the line that triggers function call::

        DEL_ALL_HOST_COMMENTS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        for comm in host.comments:
            self.del_host_comment(comm._id)

    def del_all_host_downtimes(self, host):
        """Delete all host downtimes
        Format of the line that triggers function call::

        DEL_ALL_HOST_DOWNTIMES;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        for downtime in host.downtimes:
            self.del_host_downtime(downtime._id)

    def del_all_svc_comments(self, service):
        """Delete all service comments
        Format of the line that triggers function call::

        DEL_ALL_SVC_COMMENTS;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        for comm in service.comments:
            self.del_svc_comment(comm._id)

    def del_all_svc_downtimes(self, service):
        """Delete all service downtime
        Format of the line that triggers function call::

        DEL_ALL_SVC_DOWNTIMES;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        for downtime in service.downtimes:
            self.del_svc_downtime(downtime._id)

    def del_contact_downtime(self, downtime_id):
        """Delete a contact downtime
        Format of the line that triggers function call::

        DEL_CONTACT_DOWNTIME;<downtime_id>

        :param downtime_id: downtime id to delete
        :type downtime_id: int
        :return: None
        """
        if downtime_id in self.sched.contact_downtimes:
            self.sched.contact_downtimes[downtime_id].cancel()

    def del_host_comment(self, comment_id):
        """Delete a host comment
        Format of the line that triggers function call::

        DEL_HOST_COMMENT;<comment_id>

        :param comment_id: comment id to delete
        :type comment_id: int
        :return: None
        """
        if comment_id in self.sched.comments:
            self.sched.comments[comment_id].can_be_deleted = True

    def del_host_downtime(self, downtime_id):
        """Delete a host downtime
        Format of the line that triggers function call::

        DEL_HOST_DOWNTIME;<downtime_id>

        :param downtime_id: downtime id to delete
        :type downtime_id: int
        :return: None
        """
        if downtime_id in self.sched.downtimes:
            self.sched.downtimes[downtime_id].cancel()

    def del_svc_comment(self, comment_id):
        """Delete a service comment
        Format of the line that triggers function call::

        DEL_SVC_COMMENT;<comment_id>

        :param comment_id: comment id to delete
        :type comment_id: int
        :return: None
        """
        if comment_id in self.sched.comments:
            self.sched.comments[comment_id].can_be_deleted = True

    def del_svc_downtime(self, downtime_id):
        """Delete a service downtime
        Format of the line that triggers function call::

        DEL_SVC_DOWNTIME;<downtime_id>

        :param downtime_id: downtime id to delete
        :type downtime_id: int
        :return: None
        """
        if downtime_id in self.sched.downtimes:
            self.sched.downtimes[downtime_id].cancel()

    def disable_all_notifications_beyond_host(self, host):
        """DOES NOTHING (should disable notification beyond a host)
        Format of the line that triggers function call::

        DISABLE_ALL_NOTIFICATIONS_BEYOND_HOST;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        TODO: Implement it
        """
        pass

    def disable_contactgroup_host_notifications(self, contactgroup):
        """Disable host notifications for a contactgroup
        Format of the line that triggers function call::

        DISABLE_CONTACTGROUP_HOST_NOTIFICATIONS;<contactgroup_name>

        :param contactgroup: contactgroup to disable
        :type contactgroup: alignak.objects.contactgroup.Contactgroup
        :return: None
        """
        for contact in contactgroup:
            self.disable_contact_host_notifications(contact)

    def disable_contactgroup_svc_notifications(self, contactgroup):
        """Disable service notifications for a contactgroup
        Format of the line that triggers function call::

        DISABLE_CONTACTGROUP_SVC_NOTIFICATIONS;<contactgroup_name>

        :param contactgroup: contactgroup to disable
        :type contactgroup: alignak.objects.contactgroup.Contactgroup
        :return: None
        """
        for contact in contactgroup:
            self.disable_contact_svc_notifications(contact)

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
            self.sched.get_and_register_status_brok(contact)

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
            self.sched.get_and_register_status_brok(contact)

    def disable_event_handlers(self):
        """Disable event handlers (globally)
        Format of the line that triggers function call::

        DISABLE_EVENT_HANDLERS

        :return: None
        """
        if self.conf.enable_event_handlers:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_EVENT_HANDLER_ENABLED"].value
            self.conf.enable_event_handlers = False
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def disable_failure_prediction(self):
        """Disable failure prediction (globally)
        Format of the line that triggers function call::

        DISABLE_FAILURE_PREDICTION

        :return: None
        """
        if self.conf.enable_failure_prediction:
            self.conf.modified_attributes |= \
                DICT_MODATTR["MODATTR_FAILURE_PREDICTION_ENABLED"].value
            self.conf.enable_failure_prediction = False
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def disable_flap_detection(self):
        """Disable flap detection (globally)
        Format of the line that triggers function call::

        DISABLE_FLAP_DETECTION

        :return: None
        """
        if self.conf.enable_flap_detection:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_FLAP_DETECTION_ENABLED"].value
            self.conf.enable_flap_detection = False
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()
            # Is need, disable flap state for hosts and services
            for service in self.conf.services:
                if service.is_flapping:
                    service.is_flapping = False
                    service.flapping_changes = []
                    self.sched.get_and_register_status_brok(service)
            for host in self.conf.hosts:
                if host.is_flapping:
                    host.is_flapping = False
                    host.flapping_changes = []
                    self.sched.get_and_register_status_brok(host)

    def disable_hostgroup_host_checks(self, hostgroup):
        """Disable host checks for a hostgroup
        Format of the line that triggers function call::

        DISABLE_HOSTGROUP_HOST_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to disable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host in hostgroup:
            self.disable_host_check(host)

    def disable_hostgroup_host_notifications(self, hostgroup):
        """Disable host notifications for a hostgroup
        Format of the line that triggers function call::

        DISABLE_HOSTGROUP_HOST_NOTIFICATIONS;<hostgroup_name>

        :param hostgroup: hostgroup to disable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host in hostgroup:
            self.disable_host_notifications(host)

    def disable_hostgroup_passive_host_checks(self, hostgroup):
        """Disable host passive checks for a hostgroup
        Format of the line that triggers function call::

        DISABLE_HOSTGROUP_PASSIVE_HOST_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to disable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host in hostgroup:
            self.disable_passive_host_checks(host)

    def disable_hostgroup_passive_svc_checks(self, hostgroup):
        """Disable service passive checks for a hostgroup
        Format of the line that triggers function call::

        DISABLE_HOSTGROUP_PASSIVE_SVC_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to disable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host in hostgroup:
            for service in host.services:
                self.disable_passive_svc_checks(service)

    def disable_hostgroup_svc_checks(self, hostgroup):
        """Disable service checks for a hostgroup
        Format of the line that triggers function call::

        DISABLE_HOSTGROUP_SVC_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to disable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host in hostgroup:
            for service in host.services:
                self.disable_svc_check(service)

    def disable_hostgroup_svc_notifications(self, hostgroup):
        """Disable service notifications for a hostgroup
        Format of the line that triggers function call::

        DISABLE_HOSTGROUP_SVC_NOTIFICATIONS;<hostgroup_name>

        :param hostgroup: hostgroup to disable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host in hostgroup:
            for service in host.services:
                self.disable_svc_notifications(service)

    def disable_host_and_child_notifications(self, host):
        """DOES NOTHING (Should disable host notifications and its child)
        Format of the line that triggers function call::

        DISABLE_HOST_AND_CHILD_NOTIFICATIONS;<host_name

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        pass

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
            host.disable_active_checks()
            self.sched.get_and_register_status_brok(host)

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
            self.sched.get_and_register_status_brok(host)

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
            self.sched.get_and_register_status_brok(host)

    def disable_host_freshness_checks(self):
        """Disable freshness checks (globally)
        Format of the line that triggers function call::

        DISABLE_HOST_FRESHNESS_CHECKS

        :return: None
        """
        if self.conf.check_host_freshness:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_FRESHNESS_CHECKS_ENABLED"].value
            self.conf.check_host_freshness = False
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

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
            self.sched.get_and_register_status_brok(host)

    def disable_host_svc_checks(self, host):
        """Disable service checks for a host
        Format of the line that triggers function call::

        DISABLE_HOST_SVC_CHECKS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        for serv in host.services:
            self.disable_svc_check(serv)

    def disable_host_svc_notifications(self, host):
        """Disable services notifications for a host
        Format of the line that triggers function call::

        DISABLE_HOST_SVC_NOTIFICATIONS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        for serv in host.services:
            self.disable_svc_notifications(serv)
            self.sched.get_and_register_status_brok(serv)

    def disable_notifications(self):
        """Disable notifications (globally)
        Format of the line that triggers function call::

        DISABLE_NOTIFICATIONS

        :return: None
        """
        if self.conf.enable_notifications:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            self.conf.enable_notifications = False
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

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
            self.sched.get_and_register_status_brok(host)

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
            self.sched.get_and_register_status_brok(service)

    def disable_performance_data(self):
        """Disable performance data processing (globally)
        Format of the line that triggers function call::

        DISABLE_PERFORMANCE_DATA

        :return: None
        """
        if self.conf.process_performance_data:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_PERFORMANCE_DATA_ENABLED"].value
            self.conf.process_performance_data = False
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def disable_servicegroup_host_checks(self, servicegroup):
        """Disable host checks for a servicegroup
        Format of the line that triggers function call::

        DISABLE_SERVICEGROUP_HOST_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to disable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service in servicegroup:
            self.disable_host_check(service.host)

    def disable_servicegroup_host_notifications(self, servicegroup):
        """Disable host notifications for a servicegroup
        Format of the line that triggers function call::

        DISABLE_SERVICEGROUP_HOST_NOTIFICATIONS;<servicegroup_name>

        :param servicegroup: servicegroup to disable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service in servicegroup:
            self.disable_host_notifications(service.host)

    def disable_servicegroup_passive_host_checks(self, servicegroup):
        """Disable passive host checks for a servicegroup
        Format of the line that triggers function call::

        DISABLE_SERVICEGROUP_PASSIVE_HOST_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to disable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service in servicegroup:
            self.disable_passive_host_checks(service.host)

    def disable_servicegroup_passive_svc_checks(self, servicegroup):
        """Disable passive service checks for a servicegroup
        Format of the line that triggers function call::

        DISABLE_SERVICEGROUP_PASSIVE_SVC_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to disable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service in servicegroup:
            self.disable_passive_svc_checks(service)

    def disable_servicegroup_svc_checks(self, servicegroup):
        """Disable service checks for a servicegroup
        Format of the line that triggers function call::

        DISABLE_SERVICEGROUP_SVC_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to disable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service in servicegroup:
            self.disable_svc_check(service)

    def disable_servicegroup_svc_notifications(self, servicegroup):
        """Disable service notifications for a servicegroup
        Format of the line that triggers function call::

        DISABLE_SERVICEGROUP_SVC_NOTIFICATIONS;<servicegroup_name>

        :param servicegroup: servicegroup to disable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service in servicegroup:
            self.disable_svc_notifications(service)

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
            self.sched.get_and_register_status_brok(service)

    def disable_service_freshness_checks(self):
        """Disable service freshness checks (globally)
        Format of the line that triggers function call::

        DISABLE_SERVICE_FRESHNESS_CHECKS

        :return: None
        """
        if self.conf.check_service_freshness:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_FRESHNESS_CHECKS_ENABLED"].value
            self.conf.check_service_freshness = False
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def disable_svc_check(self, service):
        """Disable checks for a service
        Format of the line that triggers function call::

        DISABLE_SVC_CHECK;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if service.active_checks_enabled:
            service.disable_active_checks()
            service.modified_attributes |= DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            self.sched.get_and_register_status_brok(service)

    def disable_svc_event_handler(self, service):
        """Disable event handlers for a service
        Format of the line that triggers function call::

        DISABLE_SVC_EVENT_HANDLER;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if service.event_handler_enabled:
            service.modified_attributes |= DICT_MODATTR["MODATTR_EVENT_HANDLER_ENABLED"].value
            service.event_handler_enabled = False
            self.sched.get_and_register_status_brok(service)

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
            service.modified_attributes |= DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            service.notifications_enabled = False
            self.sched.get_and_register_status_brok(service)

    def enable_all_notifications_beyond_host(self, host):
        """DOES NOTHING (should enable notification beyond a host)
        Format of the line that triggers function call::

        ENABLE_ALL_NOTIFICATIONS_BEYOND_HOST;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        TODO: Implement it
        """
        pass

    def enable_contactgroup_host_notifications(self, contactgroup):
        """Enable host notifications for a contactgroup
        Format of the line that triggers function call::

        ENABLE_CONTACTGROUP_HOST_NOTIFICATIONS;<contactgroup_name>

        :param contactgroup: contactgroup to enable
        :type contactgroup: alignak.objects.contactgroup.Contactgroup
        :return: None
        """
        for contact in contactgroup:
            self.enable_contact_host_notifications(contact)

    def enable_contactgroup_svc_notifications(self, contactgroup):
        """Enable service notifications for a contactgroup
        Format of the line that triggers function call::

        ENABLE_CONTACTGROUP_SVC_NOTIFICATIONS;<contactgroup_name>

        :param contactgroup: contactgroup to enable
        :type contactgroup: alignak.objects.contactgroup.Contactgroup
        :return: None
        """
        for contact in contactgroup:
            self.enable_contact_svc_notifications(contact)

    def enable_contact_host_notifications(self, contact):
        """Enable host notifications for a contact
        Format of the line that triggers function call::

        ENABLE_CONTACT_HOST_NOTIFICATIONS;<contact_name>

        :param contact: contact to enable
        :type contact: alignak.objects.contact.Contact
        :return: None
        """
        if not contact.host_notifications_enabled:
            contact.modified_attributes |= DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            contact.host_notifications_enabled = True
            self.sched.get_and_register_status_brok(contact)

    def enable_contact_svc_notifications(self, contact):
        """Enable service notifications for a contact
        Format of the line that triggers function call::

        DISABLE_CONTACT_SVC_NOTIFICATIONS;<contact_name>

        :param contact: contact to enable
        :type contact: alignak.objects.contact.Contact
        :return: None
        """
        if not contact.service_notifications_enabled:
            contact.modified_attributes |= DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            contact.service_notifications_enabled = True
            self.sched.get_and_register_status_brok(contact)

    def enable_event_handlers(self):
        """Enable event handlers (globally)
        Format of the line that triggers function call::

        ENABLE_EVENT_HANDLERS

        :return: None
        """
        if not self.conf.enable_event_handlers:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_EVENT_HANDLER_ENABLED"].value
            self.conf.enable_event_handlers = True
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def enable_failure_prediction(self):
        """Enable failure prediction (globally)
        Format of the line that triggers function call::

        ENABLE_FAILURE_PREDICTION

        :return: None
        """
        if not self.conf.enable_failure_prediction:
            self.conf.modified_attributes |= \
                DICT_MODATTR["MODATTR_FAILURE_PREDICTION_ENABLED"].value
            self.conf.enable_failure_prediction = True
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def enable_flap_detection(self):
        """Enable flap detection (globally)
        Format of the line that triggers function call::

        ENABLE_FLAP_DETECTION

        :return: None
        """
        if not self.conf.enable_flap_detection:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_FLAP_DETECTION_ENABLED"].value
            self.conf.enable_flap_detection = True
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def enable_hostgroup_host_checks(self, hostgroup):
        """Enable host checks for a hostgroup
        Format of the line that triggers function call::

        ENABLE_HOSTGROUP_HOST_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to enable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host in hostgroup:
            self.enable_host_check(host)

    def enable_hostgroup_host_notifications(self, hostgroup):
        """Enable host notifications for a hostgroup
        Format of the line that triggers function call::

        ENABLE_HOSTGROUP_HOST_NOTIFICATIONS;<hostgroup_name>

        :param hostgroup: hostgroup to enable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host in hostgroup:
            self.enable_host_notifications(host)

    def enable_hostgroup_passive_host_checks(self, hostgroup):
        """Enable host passive checks for a hostgroup
        Format of the line that triggers function call::

        ENABLE_HOSTGROUP_PASSIVE_HOST_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to enable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host in hostgroup:
            self.enable_passive_host_checks(host)

    def enable_hostgroup_passive_svc_checks(self, hostgroup):
        """Enable service passive checks for a hostgroup
        Format of the line that triggers function call::

        ENABLE_HOSTGROUP_PASSIVE_SVC_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to enable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host in hostgroup:
            for service in host.services:
                self.enable_passive_svc_checks(service)

    def enable_hostgroup_svc_checks(self, hostgroup):
        """Enable service checks for a hostgroup
        Format of the line that triggers function call::

        ENABLE_HOSTGROUP_SVC_CHECKS;<hostgroup_name>

        :param hostgroup: hostgroup to enable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host in hostgroup:
            for service in host.services:
                self.enable_svc_check(service)

    def enable_hostgroup_svc_notifications(self, hostgroup):
        """Enable service notifications for a hostgroup
        Format of the line that triggers function call::

        ENABLE_HOSTGROUP_SVC_NOTIFICATIONS;<hostgroup_name>

        :param hostgroup: hostgroup to enable
        :type hostgroup: alignak.objects.hostgroup.Hostgroup
        :return: None
        """
        for host in hostgroup:
            for service in host.services:
                self.enable_svc_notifications(service)

    def enable_host_and_child_notifications(self, host):
        """DOES NOTHING (Should enable host notifications and its child)
        Format of the line that triggers function call::

        ENABLE_HOST_AND_CHILD_NOTIFICATIONS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        pass

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
            host.modified_attributes |= DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            self.sched.get_and_register_status_brok(host)

    def enable_host_event_handler(self, host):
        """Enable event handlers for a host
        Format of the line that triggers function call::

        ENABLE_HOST_EVENT_HANDLER;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if not host.event_handler_enabled:
            host.modified_attributes |= DICT_MODATTR["MODATTR_EVENT_HANDLER_ENABLED"].value
            host.event_handler_enabled = True
            self.sched.get_and_register_status_brok(host)

    def enable_host_flap_detection(self, host):
        """Enable flap detection for a host
        Format of the line that triggers function call::

        ENABLE_HOST_FLAP_DETECTION;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if not host.flap_detection_enabled:
            host.modified_attributes |= DICT_MODATTR["MODATTR_FLAP_DETECTION_ENABLED"].value
            host.flap_detection_enabled = True
            self.sched.get_and_register_status_brok(host)

    def enable_host_freshness_checks(self):
        """Enable freshness checks (globally)
        Format of the line that triggers function call::

        ENABLE_HOST_FRESHNESS_CHECKS

        :return: None
        """
        if not self.conf.check_host_freshness:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_FRESHNESS_CHECKS_ENABLED"].value
            self.conf.check_host_freshness = True
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def enable_host_notifications(self, host):
        """Enable notifications for a host
        Format of the line that triggers function call::

        ENABLE_HOST_NOTIFICATIONS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if not host.notifications_enabled:
            host.modified_attributes |= DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            host.notifications_enabled = True
            self.sched.get_and_register_status_brok(host)

    def enable_host_svc_checks(self, host):
        """Enable service checks for a host
        Format of the line that triggers function call::

        ENABLE_HOST_SVC_CHECKS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        for serv in host.services:
            self.enable_svc_check(serv)

    def enable_host_svc_notifications(self, host):
        """Enable services notifications for a host
        Format of the line that triggers function call::

        ENABLE_HOST_SVC_NOTIFICATIONS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        for serv in host.services:
            self.enable_svc_notifications(serv)
            self.sched.get_and_register_status_brok(serv)

    def enable_notifications(self):
        """Enable notifications (globally)
        Format of the line that triggers function call::

        ENABLE_NOTIFICATIONS

        :return: None
        """
        if not self.conf.enable_notifications:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            self.conf.enable_notifications = True
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def enable_passive_host_checks(self, host):
        """Enable passive checks for a host
        Format of the line that triggers function call::

        ENABLE_PASSIVE_HOST_CHECKS;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        if not host.passive_checks_enabled:
            host.modified_attributes |= DICT_MODATTR["MODATTR_PASSIVE_CHECKS_ENABLED"].value
            host.passive_checks_enabled = True
            self.sched.get_and_register_status_brok(host)

    def enable_passive_svc_checks(self, service):
        """Enable passive checks for a service
        Format of the line that triggers function call::

        ENABLE_PASSIVE_SVC_CHECKS;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if not service.passive_checks_enabled:
            service.modified_attributes |= DICT_MODATTR["MODATTR_PASSIVE_CHECKS_ENABLED"].value
            service.passive_checks_enabled = True
            self.sched.get_and_register_status_brok(service)

    def enable_performance_data(self):
        """Enable performance data processing (globally)
        Format of the line that triggers function call::

        ENABLE_PERFORMANCE_DATA

        :return: None
        """
        if not self.conf.process_performance_data:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_PERFORMANCE_DATA_ENABLED"].value
            self.conf.process_performance_data = True
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def enable_servicegroup_host_checks(self, servicegroup):
        """Enable host checks for a servicegroup
        Format of the line that triggers function call::

        ENABLE_SERVICEGROUP_HOST_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to enable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service in servicegroup:
            self.enable_host_check(service.host)

    def enable_servicegroup_host_notifications(self, servicegroup):
        """Enable host notifications for a servicegroup
        Format of the line that triggers function call::

        ENABLE_SERVICEGROUP_HOST_NOTIFICATIONS;<servicegroup_name>

        :param servicegroup: servicegroup to enable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service in servicegroup:
            self.enable_host_notifications(service.host)

    def enable_servicegroup_passive_host_checks(self, servicegroup):
        """Enable passive host checks for a servicegroup
        Format of the line that triggers function call::

        ENABLE_SERVICEGROUP_PASSIVE_HOST_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to enable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service in servicegroup:
            self.enable_passive_host_checks(service.host)

    def enable_servicegroup_passive_svc_checks(self, servicegroup):
        """Enable passive service checks for a servicegroup
        Format of the line that triggers function call::

        ENABLE_SERVICEGROUP_PASSIVE_SVC_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to enable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service in servicegroup:
            self.enable_passive_svc_checks(service)

    def enable_servicegroup_svc_checks(self, servicegroup):
        """Enable service checks for a servicegroup
        Format of the line that triggers function call::

        ENABLE_SERVICEGROUP_SVC_CHECKS;<servicegroup_name>

        :param servicegroup: servicegroup to enable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service in servicegroup:
            self.enable_svc_check(service)

    def enable_servicegroup_svc_notifications(self, servicegroup):
        """Enable service notifications for a servicegroup
        Format of the line that triggers function call::

        ENABLE_SERVICEGROUP_SVC_NOTIFICATIONS;<servicegroup_name>

        :param servicegroup: servicegroup to enable
        :type servicegroup: alignak.objects.servicegroup.Servicegroup
        :return: None
        """
        for service in servicegroup:
            self.enable_svc_notifications(service)

    def enable_service_freshness_checks(self):
        """Enable service freshness checks (globally)
        Format of the line that triggers function call::

        ENABLE_SERVICE_FRESHNESS_CHECKS

        :return: None
        """
        if not self.conf.check_service_freshness:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_FRESHNESS_CHECKS_ENABLED"].value
            self.conf.check_service_freshness = True
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def enable_svc_check(self, service):
        """Enable checks for a service
        Format of the line that triggers function call::

        ENABLE_SVC_CHECK;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if not service.active_checks_enabled:
            service.modified_attributes |= DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            service.active_checks_enabled = True
            self.sched.get_and_register_status_brok(service)

    def enable_svc_event_handler(self, service):
        """Enable event handlers for a service
        Format of the line that triggers function call::

        ENABLE_SVC_EVENT_HANDLER;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if not service.event_handler_enabled:
            service.modified_attributes |= DICT_MODATTR["MODATTR_EVENT_HANDLER_ENABLED"].value
            service.event_handler_enabled = True
            self.sched.get_and_register_status_brok(service)

    def enable_svc_flap_detection(self, service):
        """Enable flap detection for a service
        Format of the line that triggers function call::

        ENABLE_SVC_FLAP_DETECTION;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if not service.flap_detection_enabled:
            service.modified_attributes |= DICT_MODATTR["MODATTR_FLAP_DETECTION_ENABLED"].value
            service.flap_detection_enabled = True
            self.sched.get_and_register_status_brok(service)

    def enable_svc_notifications(self, service):
        """Enable notifications for a service
        Format of the line that triggers function call::

        ENABLE_SVC_NOTIFICATIONS;<host_name>;<service_description>

        :param service: service to edit
        :type service: alignak.objects.service.Service
        :return: None
        """
        if not service.notifications_enabled:
            service.modified_attributes |= DICT_MODATTR["MODATTR_NOTIFICATIONS_ENABLED"].value
            service.notifications_enabled = True
            self.sched.get_and_register_status_brok(service)

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
        pass

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
        # raise a PASSIVE check only if needed
        if self.conf.log_passive_checks:
            naglog_result(
                'info', 'PASSIVE HOST CHECK: %s;%d;%s'
                % (host.get_name().decode('utf8', 'ignore'),
                   status_code, plugin_output.decode('utf8', 'ignore'))
            )
        now = time.time()
        cls = host.__class__
        # If globally disable OR locally, do not launch
        if cls.accept_passive_checks and host.passive_checks_enabled:
            # Maybe the check is just too old, if so, bail out!
            if self.current_timestamp < host.last_chk:
                return

            chk = host.launch_check(now, force=True)
            # Should not be possible to not find the check, but if so, don't crash
            if not chk:
                logger.error('%s > Passive host check failed. None check launched !?',
                             host.get_full_name())
                return
            # Now we 'transform the check into a result'
            # So exit_status, output and status is eaten by the host
            chk.exit_status = status_code
            chk.get_outputs(plugin_output, host.max_plugins_output_length)
            chk.status = 'waitconsume'
            chk.check_time = self.current_timestamp  # we are using the external command timestamps
            # Set the corresponding host's check_type to passive=1
            chk.set_type_passive()
            self.sched.nb_check_received += 1
            # Ok now this result will be read by scheduler the next loop

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
        # raise a PASSIVE check only if needed
        if self.conf.log_passive_checks:
            naglog_result('info', 'PASSIVE SERVICE CHECK: %s;%s;%d;%s'
                          % (service.host.get_name().decode('utf8', 'ignore'),
                             service.get_name().decode('utf8', 'ignore'),
                             return_code, plugin_output.decode('utf8', 'ignore')))
        now = time.time()
        cls = service.__class__
        # If globally disable OR locally, do not launch
        if cls.accept_passive_checks and service.passive_checks_enabled:
            # Maybe the check is just too old, if so, bail out!
            if self.current_timestamp < service.last_chk:
                return

            chk = service.launch_check(now, force=True)
            # Should not be possible to not find the check, but if so, don't crash
            if not chk:
                logger.error('%s > Passive service check failed. None check launched !?',
                             service.get_full_name())
                return
            # Now we 'transform the check into a result'
            # So exit_status, output and status is eaten by the service
            chk.exit_status = return_code
            chk.get_outputs(plugin_output, service.max_plugins_output_length)
            chk.status = 'waitconsume'
            chk.check_time = self.current_timestamp  # we are using the external command timestamps
            # Set the corresponding service's check_type to passive=1
            chk.set_type_passive()
            self.sched.nb_check_received += 1
            # Ok now this result will be reap by scheduler the next loop

    def process_service_output(self, service, plugin_output):
        """Process service output
        Format of the line that triggers function call::

        PROCESS_SERVICE_CHECK_RESULT;<host_name>;<service_description>;<plugin_output>

        :param service: service to process check to
        :type service: alignak.objects.service.Service
        :param plugin_output: plugin output
        :type plugin_output: str
        :return: None
        """
        self.process_service_check_result(service, service.state_id, plugin_output)

    def read_state_information(self):
        """DOES NOTHING (What it is supposed to do?)
        Format of the line that triggers function call::

        READ_STATE_INFORMATION

        :return: None
        """
        pass

    def remove_host_acknowledgement(self, host):
        """Remove an acknowledgment on a host
        Format of the line that triggers function call::

        REMOVE_HOST_ACKNOWLEDGEMENT;<host_name>

        :param host: host to edit
        :type host: alignak.objects.host.Host
        :return: None
        """
        host.unacknowledge_problem()

    def remove_svc_acknowledgement(self, service):
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
        e_handler = EventHandler(restart_cmd_line, timeout=900)
        # Ok now run it
        e_handler.execute()
        # And wait for the command to finish
        while e_handler.status not in ('done', 'timeout'):
            e_handler.check_finished(64000)
        if e_handler.status == 'timeout' or e_handler.exit_status != 0:
            logger.error("Cannot restart Alignak : the 'restart-alignak' command failed with"
                         " the error code '%d' and the text '%s'.",
                         e_handler.exit_status, e_handler.output)
            return
        # Ok here the command succeed, we can now wait our death
        naglog_result('info', "%s" % (e_handler.output))

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
        e_handler = EventHandler(reload_cmd_line, timeout=900)
        # Ok now run it
        e_handler.execute()
        # And wait for the command to finish
        while e_handler.status not in ('done', 'timeout'):
            e_handler.check_finished(64000)
        if e_handler.status == 'timeout' or e_handler.exit_status != 0:
            logger.error("Cannot reload Alignak configuration: the 'reload-alignak' command failed"
                         " with the error code '%d' and the text '%s'.",
                         e_handler.exit_status, e_handler.output)
            return
        # Ok here the command succeed, we can now wait our death
        naglog_result('info', "%s" % (e_handler.output))

    def save_state_information(self):
        """DOES NOTHING (What it is supposed to do?)
        Format of the line that triggers function call::

        SAVE_STATE_INFORMATION

        :return: None
        """
        pass

    def schedule_and_propagate_host_downtime(self, host, start_time, end_time,
                                             fixed, trigger_id, duration, author, comment):
        """DOES NOTHING (Should create host downtime and start it?)
        Format of the line that triggers function call::

        SCHEDULE_AND_PROPAGATE_HOST_DOWNTIME;<host_name>;<start_time>;<end_time>;
        <fixed>;<trigger_id>;<duration>;<author>;<comment>

        :return: None
        """
        pass

    def schedule_and_propagate_triggered_host_downtime(self, host, start_time, end_time, fixed,
                                                       trigger_id, duration, author, comment):
        """DOES NOTHING (Should create triggered host downtime and start it?)
        Format of the line that triggers function call::

        SCHEDULE_AND_PROPAGATE_TRIGGERED_HOST_DOWNTIME;<host_name>;<start_time>;<end_time>;<fixed>;
        <trigger_id>;<duration>;<author>;<comment>

        :return: None
        """
        pass

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
        cdt = ContactDowntime(contact, start_time, end_time, author, comment)
        contact.add_downtime(cdt)
        self.sched.add(cdt)
        self.sched.get_and_register_status_brok(contact)

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
        host.schedule(force=True, force_time=check_time)
        self.sched.get_and_register_status_brok(host)

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
        for serv in host.services:
            self.schedule_forced_svc_check(serv, check_time)
            self.sched.get_and_register_status_brok(serv)

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
        service.schedule(force=True, force_time=check_time)
        self.sched.get_and_register_status_brok(service)

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
        :type trigger_id: int
        :param duration: downtime duration
        :type duration: int
        :param author: downtime author
        :type author: str
        :param comment: downtime comment
        :type comment: str
        :return: None
        """
        for host in hostgroup:
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
        :type trigger_id: int
        :param duration: downtime duration
        :type duration: int
        :param author: downtime author
        :type author: str
        :param comment: downtime comment
        :type comment: str
        :return: None
        """
        for host in hostgroup:
            for serv in host.services:
                self.schedule_svc_downtime(serv, start_time, end_time, fixed,
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
        host.schedule(force=False, force_time=check_time)
        self.sched.get_and_register_status_brok(host)

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
        :type trigger_id: int
        :param duration: downtime duration
        :type duration: int
        :param author: downtime author
        :type author: str
        :param comment: downtime comment
        :type comment: str
        :return: None
        """
        downtime = Downtime(host, start_time, end_time, fixed, trigger_id, duration, author,
                            comment)
        host.add_downtime(downtime)
        self.sched.add(downtime)
        self.sched.get_and_register_status_brok(host)
        if trigger_id != 0 and trigger_id in self.sched.downtimes:
            self.sched.downtimes[trigger_id].trigger_me(downtime)

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
        for serv in host.services:
            self.schedule_svc_check(serv, check_time)
            self.sched.get_and_register_status_brok(serv)

    def schedule_host_svc_downtime(self, host, start_time, end_time, fixed,
                                   trigger_id, duration, author, comment):
        """Schedule a service downtime for each service of a host
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
        :type trigger_id: int
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
        :type trigger_id: int
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
        :type trigger_id: int
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
        service.schedule(force=False, force_time=check_time)
        self.sched.get_and_register_status_brok(service)

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
        downtime = Downtime(service, start_time, end_time, fixed, trigger_id, duration, author,
                            comment)
        service.add_downtime(downtime)
        self.sched.add(downtime)
        self.sched.get_and_register_status_brok(service)
        if trigger_id != 0 and trigger_id in self.sched.downtimes:
            self.sched.downtimes[trigger_id].trigger_me(downtime)

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
        pass

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
        pass

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
        pass

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
        pass

    def shutdown_program(self):
        """DOES NOTHING (Should shutdown Alignak)
        Format of the line that triggers function call::

        SHUTDOWN_PROGRAM

        :return: None
        """
        pass

    def start_accepting_passive_host_checks(self):
        """Enable passive host check submission (globally)
        Format of the line that triggers function call::

        START_ACCEPTING_PASSIVE_HOST_CHECKS

        :return: None
        """
        if not self.conf.accept_passive_host_checks:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_PASSIVE_CHECKS_ENABLED"].value
            self.conf.accept_passive_host_checks = True
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def start_accepting_passive_svc_checks(self):
        """Enable passive service check submission (globally)
        Format of the line that triggers function call::

        START_ACCEPTING_PASSIVE_SVC_CHECKS

        :return: None
        """
        if not self.conf.accept_passive_service_checks:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_PASSIVE_CHECKS_ENABLED"].value
            self.conf.accept_passive_service_checks = True
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def start_executing_host_checks(self):
        """Enable host check execution (globally)
        Format of the line that triggers function call::

        START_EXECUTING_HOST_CHECKS

        :return: None
        """
        if not self.conf.execute_host_checks:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            self.conf.execute_host_checks = True
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def start_executing_svc_checks(self):
        """Enable service check execution (globally)
        Format of the line that triggers function call::

        START_EXECUTING_SVC_CHECKS

        :return: None
        """
        if not self.conf.execute_service_checks:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            self.conf.execute_service_checks = True
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def start_obsessing_over_host(self, host):
        """Enable obsessing over host for a host
        Format of the line that triggers function call::

        START_OBSESSING_OVER_HOST;<host_name>

        :param host: host to obsess over
        :type host: alignak.objects.host.Host
        :return: None
        """
        if not host.obsess_over_host:
            host.modified_attributes |= DICT_MODATTR["MODATTR_OBSESSIVE_HANDLER_ENABLED"].value
            host.obsess_over_host = True
            self.sched.get_and_register_status_brok(host)

    def start_obsessing_over_host_checks(self):
        """Enable obssessing over host check (globally)
        Format of the line that triggers function call::

        START_OBSESSING_OVER_HOST_CHECKS

        :return: None
        """
        if not self.conf.obsess_over_hosts:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_OBSESSIVE_HANDLER_ENABLED"].value
            self.conf.obsess_over_hosts = True
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def start_obsessing_over_svc(self, service):
        """Enable obssessing over service for a service
        Format of the line that triggers function call::

        START_OBSESSING_OVER_SVC;<host_name>;<service_description>

        :param service: service to obssess over
        :type service: alignak.objects.service.Service
        :return: None
        """
        if not service.obsess_over_service:
            service.modified_attributes |= DICT_MODATTR["MODATTR_OBSESSIVE_HANDLER_ENABLED"].value
            service.obsess_over_service = True
            self.sched.get_and_register_status_brok(service)

    def start_obsessing_over_svc_checks(self):
        """Enable obssessing over service check (globally)
        Format of the line that triggers function call::

        START_OBSESSING_OVER_SVC_CHECKS

        :return: None
        """
        if not self.conf.obsess_over_services:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_OBSESSIVE_HANDLER_ENABLED"].value
            self.conf.obsess_over_services = True
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def stop_accepting_passive_host_checks(self):
        """Disable passive host check submission (globally)
        Format of the line that triggers function call::

        STOP_ACCEPTING_PASSIVE_HOST_CHECKS

        :return: None
        """
        if self.conf.accept_passive_host_checks:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_PASSIVE_CHECKS_ENABLED"].value
            self.conf.accept_passive_host_checks = False
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def stop_accepting_passive_svc_checks(self):
        """Disable passive service check submission (globally)
        Format of the line that triggers function call::

        STOP_ACCEPTING_PASSIVE_SVC_CHECKS

        :return: None
        """
        if self.conf.accept_passive_service_checks:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_PASSIVE_CHECKS_ENABLED"].value
            self.conf.accept_passive_service_checks = False
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def stop_executing_host_checks(self):
        """Disable host check execution (globally)
        Format of the line that triggers function call::

        STOP_EXECUTING_HOST_CHECKS

        :return: None
        """
        if self.conf.execute_host_checks:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            self.conf.execute_host_checks = False
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def stop_executing_svc_checks(self):
        """Disable service check execution (globally)
        Format of the line that triggers function call::

        STOP_EXECUTING_SVC_CHECKS

        :return: None
        """
        if self.conf.execute_service_checks:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_ACTIVE_CHECKS_ENABLED"].value
            self.conf.execute_service_checks = False
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def stop_obsessing_over_host(self, host):
        """Disable obsessing over host for a host
        Format of the line that triggers function call::

        STOP_OBSESSING_OVER_HOST;<host_name>

        :param host: host to obsess over
        :type host: alignak.objects.host.Host
        :return: None
        """
        if host.obsess_over_host:
            host.modified_attributes |= DICT_MODATTR["MODATTR_OBSESSIVE_HANDLER_ENABLED"].value
            host.obsess_over_host = False
            self.sched.get_and_register_status_brok(host)

    def stop_obsessing_over_host_checks(self):
        """Disable obssessing over host check (globally)
        Format of the line that triggers function call::

        STOP_OBSESSING_OVER_HOST_CHECKS

        :return: None
        """
        if self.conf.obsess_over_hosts:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_OBSESSIVE_HANDLER_ENABLED"].value
            self.conf.obsess_over_hosts = False
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def stop_obsessing_over_svc(self, service):
        """Disable obssessing over service for a service
        Format of the line that triggers function call::

        STOP_OBSESSING_OVER_SVC;<host_name>;<service_description>

        :param service: service to obssess over
        :type service: alignak.objects.service.Service
        :return: None
        """
        if service.obsess_over_service:
            service.modified_attributes |= DICT_MODATTR["MODATTR_OBSESSIVE_HANDLER_ENABLED"].value
            service.obsess_over_service = False
            self.sched.get_and_register_status_brok(service)

    def stop_obsessing_over_svc_checks(self):
        """Disable obssessing over service check (globally)
        Format of the line that triggers function call::

        STOP_OBSESSING_OVER_SVC_CHECKS

        :return: None
        """
        if self.conf.obsess_over_services:
            self.conf.modified_attributes |= DICT_MODATTR["MODATTR_OBSESSIVE_HANDLER_ENABLED"].value
            self.conf.obsess_over_services = False
            self.conf.explode_global_conf()
            self.sched.get_and_register_update_program_status_brok()

    def launch_svc_event_handler(self, service):
        """Launch event handler for a service
        Format of the line that triggers function call::

        LAUNCH_SVC_EVENT_HANDLER;<host_name>;<service_description>

        :param service: service to execute the event handler
        :type service: alignak.objects.service.Service
        :return: None
        """
        service.get_event_handlers(externalcmd=True)

    def launch_host_event_handler(self, host):
        """Launch event handler for a service
        Format of the line that triggers function call::

        LAUNCH_HOST_EVENT_HANDLER;<host_name>

        :param host: host to execute the event handler
        :type host: alignak.objects.host.Host
        :return: None
        """
        host.get_event_handlers(externalcmd=True)

    def add_simple_host_dependency(self, son, father):
        """Add a host dependency between son and father
        Format of the line that triggers function call::

        ADD_SIMPLE_HOST_DEPENDENCY;<host_name>;<host_name>

        :param son: son of dependency
        :type son: alignak.objects.host.Host
        :param father: father of dependency
        :type father: alignak.objects.host.Host
        :return: None
        """
        if not son.is_linked_with_host(father):
            logger.debug("Doing simple link between %s and %s", son.get_name(), father.get_name())
            # Flag them so the modules will know that a topology change
            # happened
            son.topology_change = True
            father.topology_change = True
            # Now do the work
            # Add a dep link between the son and the father
            son.add_host_act_dependency(father, ['w', 'u', 'd'], None, True)
            self.sched.get_and_register_status_brok(son)
            self.sched.get_and_register_status_brok(father)

    def del_host_dependency(self, son, father):
        """Delete a host dependency between son and father
        Format of the line that triggers function call::

        DEL_SIMPLE_HOST_DEPENDENCY;<host_name>;<host_name>

        :param son: son of dependency
        :type son: alignak.objects.host.Host
        :param father: father of dependency
        :type father: alignak.objects.host.Host
        :return: None
        """
        if son.is_linked_with_host(father):
            logger.debug("Removing simple link between %s and %s",
                         son.get_name(), father.get_name())
            # Flag them so the modules will know that a topology change
            # happened
            son.topology_change = True
            father.topology_change = True
            # Now do the work
            son.del_host_act_dependency(father)
            self.sched.get_and_register_status_brok(son)
            self.sched.get_and_register_status_brok(father)

    def add_simple_poller(self, realm_name, poller_name, address, port):
        """Add a poller
        Format of the line that triggers function call::

        ADD_SIMPLE_POLLER;realm_name;poller_name;address;port

        :param realm_name: realm for the new poller
        :type realm_name: str
        :param poller_name: new poller name
        :type poller_name: str
        :param address: new poller address
        :type address: str
        :param port: new poller port
        :type port: int
        :return: None
        """
        logger.debug("I need to add the poller (%s, %s, %s, %s)",
                     realm_name, poller_name, address, port)

        # First we look for the realm
        realm = self.conf.realms.find_by_name(realm_name)
        if realm is None:
            logger.debug("Sorry, the realm %s is unknown", realm_name)
            return

        logger.debug("We found the realm: %s", str(realm))
        # TODO: backport this in the config class?
        # We create the PollerLink object
        params = {'poller_name': poller_name, 'address': address, 'port': port}
        poll = PollerLink(params)
        poll.fill_default()
        poll.prepare_for_conf()
        parameters = {'max_plugins_output_length': self.conf.max_plugins_output_length}
        poll.add_global_conf_parameters(parameters)
        self.arbiter.conf.pollers[poll._id] = poll
        self.arbiter.dispatcher.elements.append(poll)
        self.arbiter.dispatcher.satellites.append(poll)
        realm.pollers.append(poll)
        realm.count_pollers()
        realm.fill_potential_satellites_by_type('pollers')
        logger.debug("Poller %s added", poller_name)
        logger.debug("Potential %s", str(realm.get_potential_satellites_by_type('poller')))
