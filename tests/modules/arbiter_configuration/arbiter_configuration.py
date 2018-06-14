# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2018: Alignak contrib team, see AUTHORS.txt file for contributors
#
# This file is part of Alignak contrib projet.
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
This module is used to get configuration from alignak-backend with arbiter
"""


import os
import signal
import time
import json
import logging
from datetime import datetime

from alignak.basemodule import BaseModule
from alignak.external_command import ExternalCommand

from alignak_backend_client.client import Backend, BackendException

# Set the backend client library log to ERROR level
logging.getLogger("alignak_backend_client.client").setLevel(logging.ERROR)

logger = logging.getLogger('alignak.module')  # pylint: disable=invalid-name

# pylint: disable=C0103
properties = {
    'daemons': ['arbiter'],
    'type': 'backend_arbiter',
    'external': False,
    'phases': ['configuration'],
}


def get_instance(mod_conf):
    """
    Return a module instance for the modules manager

    :param mod_conf: the module properties as defined globally in this file
    :return:
    """
    logger.info("Give an instance of %s for alias: %s", mod_conf.python_name, mod_conf.module_alias)

    return AlignakBackendArbiter(mod_conf)


class AlignakBackendArbiter(BaseModule):
    # pylint: disable=too-many-public-methods
    """ This class is used to get configuration from alignak-backend
    """

    def __init__(self, mod_conf):
        """Module initialization

        mod_conf is a dictionary that contains:
        - all the variables declared in the module configuration file
        - a 'properties' value that is the module properties as defined globally in this file

        :param mod_conf: module configuration file as a dictionary
        """
        BaseModule.__init__(self, mod_conf)

        # pylint: disable=global-statement
        global logger
        logger = logging.getLogger('alignak.module.%s' % self.alias)

        logger.debug("inner properties: %s", self.__dict__)
        logger.debug("received configuration: %s", mod_conf.__dict__)

        self.my_arbiter = None

        self.bypass_verify_mode = int(getattr(mod_conf, 'bypass_verify_mode', 0)) == 1
        logger.info("bypass objects loading when Arbiter is in verify mode: %s",
                    self.bypass_verify_mode)

        self.verify_modification = int(getattr(mod_conf, 'verify_modification', 5))
        logger.info("configuration reload check period: %s minutes", self.verify_modification)

        self.action_check = int(getattr(mod_conf, 'action_check', 15))
        logger.info("actions check period: %s seconds", self.action_check)
        self.daemons_state = int(getattr(mod_conf, 'daemons_state', 60))
        logger.info("daemons state update period: %s seconds", self.daemons_state)
        self.next_check = 0
        self.next_action_check = 0
        self.next_daemons_state = 0

        # Configuration load/reload
        self.backend_date_format = "%a, %d %b %Y %H:%M:%S GMT"
        self.time_loaded_conf = datetime.utcnow().strftime(self.backend_date_format)
        self.configuration_reload_required = False
        self.configuration_reload_changelog = []

        self.configraw = {}
        self.highlevelrealm = {
            'level': 30000,
            'name': ''
        }
        self.daemonlist = {'arbiter': {}, 'scheduler': {}, 'poller': {}, 'reactionner': {},
                           'receiver': {}, 'broker': {}}
        self.config = {'commands': [],
                       'timeperiods': [],
                       'hosts': [],
                       'hostgroups': [],
                       'services': [],
                       'contacts': [],
                       'contactgroups': [],
                       'servicegroups': [],
                       'realms': [],
                       'hostdependencies': [],
                       'hostescalations': [],
                       'servicedependencies': [],
                       'serviceescalations': [],
                       'triggers': []}
        self.default_tp_always = None
        self.default_tp_never = None
        self.default_host_check_command = None
        self.default_service_check_command = None
        self.default_user = None

        self.alignak_configuration = {}

    # Common functions
    def do_loop_turn(self):
        """This function is called/used when you need a module with
        a loop function (and use the parameter 'external': True)
        """
        logger.info("In loop")
        time.sleep(1)

    def hook_read_configuration(self, arbiter):
        """Hook in arbiter used on configuration parsing start. This is useful to get our arbiter
        object and its parameters.

        :param arbiter: alignak.daemons.arbiterdaemon.Arbiter
        :type arbiter: object
        :return: None
        """
        self.my_arbiter = arbiter

    def get_alignak_configuration(self):
        """Get Alignak configuration from alignak-backend

        This function is an Arbiter hook called by the arbiter during its configuration loading.

        :return: alignak configuration parameters
        :rtype: dict
        """
        self.alignak_configuration = {}

        start_time = time.time()
        try:
            logger.info("Loading Alignak configuration...")
            self.alignak_configuration = {
                'name': 'my_alignak',
                'alias': 'Test alignak configuration',
                # Boolean fields
                'notifications_enabled': True,
                'flap_detection_enabled': False,
                # Commands fields
                'host_perfdata_command': 'None',
                'service_perfdata_command': None,
                'global_host_event_handler': 'check-host-alive',
                'global_service_event_handler': 'check_service',

                '_TEST1': 'Test an extra non declared field',
                'TEST2': 'One again - Test an extra non declared field',
                'TEST3': 'And again - Test an extra non declared field',

                '_updated': 123456789,
                '_realm': None,
                '_sub_realm': True
            }
        except BackendException as exp:
            logger.warning("Alignak backend is not available for reading configuration. "
                           "Backend communication error.")
            logger.debug("Exception: %s", exp)
            self.backend_connected = False
            return self.alignak_configuration

        self.time_loaded_conf = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

        now = time.time()
        logger.info("Alignak configuration loaded in %s seconds", (now - start_time))
        return self.alignak_configuration

    def hook_tick(self, arbiter):
        # pylint: disable=too-many-nested-blocks
        """Hook in arbiter used to check if configuration has changed in the backend since
        last configuration loaded

        :param arbiter: alignak.daemons.arbiterdaemon.Arbiter
        :type arbiter: object
        :return: None
        """
        if not self.backend_connected:
            self.getToken()
            if self.raise_backend_alert(errors_count=10):
                logger.warning("Alignak backend connection is not available. "
                               "Periodical actions are disabled: configuration change checking, "
                               "ack/downtime/forced check, and daemons state updates.")
                return

        try:
            now = int(time.time())
            if now > self.next_check:
                logger.info("Check if system configuration changed in the backend...")
                logger.debug("Now is: %s", datetime.utcnow().strftime(self.backend_date_format))
                logger.debug("Last configuration loading time is: %s", self.time_loaded_conf)
                # todo: we should find a way to declare in the backend schema
                # that a resource endpoint is concerned with this feature. Something like:
                #   'arbiter_reload_check': True,
                #   'schema': {...}
                logger.debug("Check if system configuration changed in the backend...")
                resources = [
                    'realm', 'command', 'timeperiod',
                    'usergroup', 'user',
                    'hostgroup', 'host', 'hostdependency', 'hostescalation',
                    'servicegroup', 'service', 'servicedependency', 'serviceescalation'
                ]
                self.configuration_reload_required = False
                for resource in resources:
                    ret = self.backend.get(resource, {'where': '{"_updated":{"$gte": "' +
                                                               self.time_loaded_conf + '"}}'})
                    if ret['_meta']['total'] > 0:
                        logger.info(" - backend updated resource: %s, count: %d",
                                    resource, ret['_meta']['total'])
                        self.configuration_reload_required = True
                        for updated in ret['_items']:
                            logger.debug("  -> updated: %s", updated)
                            exists = [log for log in self.configuration_reload_changelog
                                      if log['resource'] == resource and
                                      log['item']['_id'] == updated['_id'] and
                                      log['item']['_updated'] == updated['_updated']]
                            if not exists:
                                self.configuration_reload_changelog.append({"resource": resource,
                                                                            "item": updated})
                if self.configuration_reload_required:
                    logger.warning("Hey, we must reload configuration from the backend!")
                    try:
                        with open(arbiter.pidfile, 'r') as f:
                            arbiter_pid = f.readline()
                        os.kill(int(arbiter_pid), signal.SIGHUP)
                        message = "The configuration reload notification was " \
                                  "raised to the arbiter (pid=%s)." % arbiter_pid
                        self.configuration_reload_changelog.append({"resource": "backend-log",
                                                                    "item": {
                                                                        "_updated": now,
                                                                        "level": "INFO",
                                                                        "message": message
                                                                    }})
                        logger.error(message)
                    except IOError:
                        message = "The arbiter pid file (%s) is not available. " \
                                  "Configuration reload notification was not raised." \
                                  % arbiter.pidfile
                        self.configuration_reload_changelog.append({"resource": "backend-log",
                                                                    "item": {
                                                                        "_updated": now,
                                                                        "level": "ERROR",
                                                                        "message": message
                                                                    }})
                        logger.error(message)
                    except OSError:
                        message = "The arbiter pid (%s) stored in file (%s) is not for an " \
                                  "existing process. " \
                                  "Configuration reload notification was not raised." \
                                  % (arbiter_pid, arbiter.pidfile)
                        self.configuration_reload_changelog.append({"resource": "backend-log",
                                                                    "item": {
                                                                        "_updated": now,
                                                                        "level": "ERROR",
                                                                        "message": message
                                                                    }})
                        logger.error(message)
                else:
                    logger.debug("No changes found")
                self.next_check = now + (60 * self.verify_modification)
                logger.debug(
                    "next configuration reload check in %s seconds ---",
                    (self.next_check - now)
                )

            if now > self.next_action_check:
                logger.debug("Check if acknowledgements are required...")
                self.get_acknowledge(arbiter)
                logger.debug("Check if downtime scheduling are required...")
                self.get_downtime(arbiter)
                logger.debug("Check if re-checks are required...")
                self.get_forcecheck(arbiter)

                self.next_action_check = now + self.action_check
                logger.debug("next actions check in %s seconds ---",
                             (self.next_action_check - int(now)))

            if now > self.next_daemons_state:
                logger.debug("Update daemons state in the backend...")
                self.update_daemons_state(arbiter)

                self.next_daemons_state = now + self.daemons_state
                logger.debug(
                    "next update daemons state in %s seconds ---",
                    (self.next_daemons_state - int(now))
                )
        except Exception as exp:
            logger.warning("hook_tick exception: %s", str(exp))
            logger.debug("Exception: %s", exp)
