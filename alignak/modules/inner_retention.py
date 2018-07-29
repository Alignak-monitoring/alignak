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
This module is used to manage retention in a json file
"""

import os
import time
import tempfile
import json
import logging

from alignak.stats import Stats
from alignak.basemodule import BaseModule

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

# pylint: disable=invalid-name
properties = {
    'daemons': ['scheduler'],
    'type': 'retention',
    'external': False,
    'phases': ['running'],
}


def get_instance(mod_conf):
    """
    Return a module instance for the modules manager

    :param mod_conf: the module properties as defined globally in this file
    :return:
    """
    logger.info("Giving an instance of %s for alias: %s",
                mod_conf.python_name, mod_conf.module_alias)

    return InnerRetention(mod_conf)


class InnerRetention(BaseModule):
    """
    This class is used to store/restore retention data
    """

    def __init__(self, mod_conf):
        """Module initialization

        mod_conf is a dictionary that contains:
        - all the variables declared in the module configuration
        - a 'properties' value that is the module properties as defined globally in this file

        :param mod_conf: module configuration file as a dictionary
        """
        BaseModule.__init__(self, mod_conf)

        # pylint: disable=global-statement
        global logger
        logger = logging.getLogger('alignak.module.%s' % self.alias)
        logger.setLevel(getattr(mod_conf, 'log_level', logging.INFO))

        logger.debug("inner properties: %s", self.__dict__)
        logger.info("received configuration: %s", mod_conf.__dict__)

        logger.info("loaded by the %s '%s'", self.my_daemon.type, self.my_daemon.name)

        stats_host = getattr(mod_conf, 'statsd_host', 'localhost')
        stats_port = int(getattr(mod_conf, 'statsd_port', '8125'))
        stats_prefix = getattr(mod_conf, 'statsd_prefix', 'alignak')
        statsd_enabled = (getattr(mod_conf, 'statsd_enabled', '0') != '0')
        if isinstance(getattr(mod_conf, 'statsd_enabled', '0'), bool):
            statsd_enabled = getattr(mod_conf, 'statsd_enabled')
        graphite_enabled = (getattr(mod_conf, 'graphite_enabled', '0') != '0')
        if isinstance(getattr(mod_conf, 'graphite_enabled', '0'), bool):
            graphite_enabled = getattr(mod_conf, 'graphite_enabled')
        logger.info("StatsD configuration: %s:%s, prefix: %s, enabled: %s, graphite: %s",
                    stats_host, stats_port, stats_prefix, statsd_enabled, graphite_enabled)

        self.statsmgr = Stats()
        # Configure our Stats manager
        if not graphite_enabled:
            self.statsmgr.register(self.alias, 'module',
                                   statsd_host=stats_host, statsd_port=stats_port,
                                   statsd_prefix=stats_prefix, statsd_enabled=statsd_enabled)
        else:
            self.statsmgr.connect(self.alias, 'module',
                                  host=stats_host, port=stats_port,
                                  prefix=stats_prefix, enabled=True)

        self.enabled = getattr(mod_conf, 'enabled', '0') != '0'
        if isinstance(getattr(mod_conf, 'enabled', '0'), bool):
            self.enabled = getattr(mod_conf, 'enabled')

        self.retention_file = getattr(mod_conf, 'retention_file', None)
        if not self.enabled:
            logger.warning("inner retention module is loaded but is not enabled.")
            return

        if not self.retention_file:
            self.retention_file = os.path.join(tempfile.gettempdir(), 'alignak-retention-%s.json')
        if '%s' in self.retention_file:
            self.retention_file = self.retention_file % self.my_daemon.name

        logger.info("inner retention module, enabled: %s, retention file: %s",
                    self.enabled, self.retention_file)

    # Common functions
    def do_loop_turn(self):
        """This function is called/used when you need a module with
        a loop function (and use the parameter 'external': True)
        """
        logger.info("[Inner Retention] In loop")
        time.sleep(1)

    def hook_load_retention(self, scheduler):
        """Load retention data from a file

        :param scheduler: scheduler instance of alignak
        :type scheduler: object
        :return: None
        """
        if not self.enabled:
            logger.warning("Alignak retention module is not enabled."
                           "Loading objects state is not possible.")
            return None

        all_data = {'hosts': {}, 'services': {}}

        if not os.path.isfile(self.retention_file):
            logger.info("The configured state retention file (%s) does not exist. "
                        "Loading objects state is not available.", self.retention_file)
            return None

        # Get data from the retention file
        try:
            start_time = time.time()

            try:
                logger.info('Loading retention data from: %s', self.retention_file)
                with open(self.retention_file, "r") as fd:
                    response = json.load(fd)
                logger.info('Loaded')
            except json.JSONDecodeError as exp:  # pragma: no cover, should never happen...
                logger.warning("Error when loading retention data from %s", self.retention_file)
                logger.exception(exp)
            else:
                for host in response.values():
                    hostname = host['name']
                    service_key = 'services'
                    if 'retention_services' in host:
                        service_key = 'retention_services'
                    if service_key in host:
                        for service in host[service_key]:
                            all_data['services'][(host['name'], service)] = \
                                host[service_key][service]
                    all_data['hosts'][hostname] = host

                logger.info('%d hosts loaded from retention', len(all_data['hosts']))
                self.statsmgr.counter('retention-load.hosts', len(all_data['hosts']))
                logger.info('%d services loaded from retention', len(all_data['services']))
                self.statsmgr.counter('retention-load.services', len(all_data['services']))
                self.statsmgr.timer('retention-load.time', time.time() - start_time)

                # Restore the scheduler objects
                scheduler.restore_retention_data(all_data)
                logger.info("Retention data loaded in %s seconds", (time.time() - start_time))
        except Exception as exp:  # pylint: disable=broad-except
            logger.warning("Retention load failed: %s", exp)
            logger.exception(exp)
            return False

        return True

    def hook_save_retention(self, scheduler):
        """Save retention data to a Json formated file

        :param scheduler: scheduler instance of alignak
        :type scheduler: object
        :return: None
        """
        if not self.enabled:
            logger.warning("Alignak retention module is not enabled."
                           "Saving objects state is not possible.")
            return None

        try:
            start_time = time.time()

            # Get retention data from the scheduler
            data_to_save = scheduler.get_retention_data()
            if not data_to_save:
                logger.warning("Alignak retention data to save are not containing any information.")
                return None

            # Move services data to their respective hosts dictionary
            # Alignak scheduler do not merge the services into the host dictionary!
            for host_name in data_to_save['hosts']:
                data_to_save['hosts'][host_name]['services'] = {}
                data_to_save['hosts'][host_name]['name'] = host_name
            for host_name, service_description in data_to_save['services']:
                data_to_save['hosts'][host_name]['services'][service_description] = \
                    data_to_save['services'][(host_name, service_description)]

            try:
                logger.info('Saving retention data to: %s', self.retention_file)
                with open(self.retention_file, "w") as fd:
                    fd.write(json.dumps(data_to_save['hosts'],
                                        indent=2, separators=(',', ': '), sort_keys=True))

                logger.info('Saved')
            except Exception as exp:  # pylint: disable=broad-except
                # pragma: no cover, should never happen...
                logger.warning("Error when saving retention data to %s", self.retention_file)
                logger.exception(exp)

            logger.info('%d hosts saved in retention', len(data_to_save['hosts']))
            self.statsmgr.counter('retention-save.hosts', len(data_to_save['hosts']))
            logger.info('%d services saved in retention', len(data_to_save['services']))
            self.statsmgr.counter('retention-save.services', len(data_to_save['services']))
            self.statsmgr.timer('retention-save.time', time.time() - start_time)

            logger.info("Retention data saved in %s seconds", (time.time() - start_time))
        except Exception as exp:  # pylint: disable=broad-except
            self.enabled = False
            logger.warning("Retention save failed: %s", exp)
            logger.exception(exp)
            return False

        return True
