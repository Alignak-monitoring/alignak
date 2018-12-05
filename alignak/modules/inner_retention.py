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
This module is used to manage retention in json files
"""

import os
import re
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

    def __init__(self, mod_conf):  # pylint: disable=too-many-branches
        """Module initialization

        mod_conf is a dictionary that contains:
        - all the variables declared in the module configuration
        - a 'properties' value that is the module properties as defined globally in this file

        If some environment variables exist the metrics they will take precedence over the
        configuration parameters
            'ALIGNAK_RETENTION_DIR'
                the retention files directory
            'ALIGNAK_RETENTION_FILE'
                the retention unique file for the current scheduler

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
        if not self.enabled:
            logger.warning("inner retention module is loaded but is not enabled.")
            return

        self.retention_dir = getattr(mod_conf, 'retention_dir', None)
        if os.getenv('ALIGNAK_RETENTION_DIR', None):
            self.retention_dir = os.getenv('ALIGNAK_RETENTION_DIR', None)
        if not self.retention_dir:
            self.retention_dir = tempfile.gettempdir()
        if '%s' in self.retention_dir:
            self.retention_dir = self.retention_dir % self.my_daemon.name

        self.retention_file = getattr(mod_conf, 'retention_file', None)
        logger.info("inner retention module, retention file: %s", self.retention_file)
        if os.getenv('ALIGNAK_RETENTION_FILE', None):
            self.retention_file = os.getenv('ALIGNAK_RETENTION_FILE', None)
        if self.retention_file is None:
            self.retention_file = os.path.join(self.retention_dir, 'alignak-retention-%s.json')
        if '%s' in self.retention_file:
            self.retention_file = self.retention_file % self.my_daemon.name

        logger.info("inner retention module, enabled: %s, retention dir: %s, retention file: %s",
                    self.enabled, self.retention_dir, self.retention_file)

        if not self.retention_file:
            logger.info("The retention file is set as an empty file. The module will "
                        "create a file for each host in the retention directory.")
        else:
            logger.info("The retention file is set as a unique scheduler file. "
                        "The module will create one file for each scheduler "
                        "with all hosts in the retention directory.")

    # Common functions
    def do_loop_turn(self):
        """This function is called/used when you need a module with
        a loop function (and use the parameter 'external': True)
        """
        logger.info("[Inner Retention] In loop")
        time.sleep(1)

    def hook_load_retention(self, scheduler):  # pylint: disable=too-many-locals, too-many-branches
        """Load retention data from a file

        :param scheduler: scheduler instance of alignak
        :type scheduler: object
        :return: None
        """
        if not self.enabled:
            logger.warning("Alignak retention module is not enabled."
                           "Loading objects state is not possible.")
            return None

        if self.retention_file and not os.path.isfile(self.retention_file):
            logger.info("The configured state retention file (%s) does not exist. "
                        "Loading objects state is not available.", self.retention_file)
            return None

        if self.retention_dir and not os.path.isdir(self.retention_dir):
            logger.info("The configured state retention directory (%s) does not exist. "
                        "Loading objects state is not available.", self.retention_dir)
            return None

        all_data = {'hosts': {}, 'services': {}}

        retention_files = []
        if self.retention_file:
            retention_files = [self.retention_file]
        else:
            if self.retention_dir:
                for root, _, walk_files in os.walk(self.retention_dir, followlinks=True):
                    for found_file in walk_files:
                        if not re.search(r"\.json$", found_file):
                            continue
                        retention_files.append(os.path.join(root, found_file))
        logger.debug("Loading retention files: %s ", retention_files)
        if retention_files:
            logger.info("Loading retention data from %d files", len(retention_files))

        start_time = time.time()

        for retention_file in retention_files:
            # Get data from the retention files
            try:
                logger.debug('Loading data from: %s', retention_file)
                with open(retention_file, "r") as fd:
                    response = json.load(fd)

                if not isinstance(response, list):
                    response = [response]

                # Is looks like a list of host dictionaries ?
                if isinstance(response[0], dict) and 'name' in response[0]:
                    logger.debug('Loaded: %s', response)
                else:
                    logger.info("Supposed retention file %s is not correctly encoded! Got: %s",
                                retention_file, response[0])
                    continue
            except Exception as exp:  # pylint: disable=broad-except
                # pragma: no cover, should never happen...
                logger.warning("Error when loading retention data from %s", retention_file)
                logger.exception(exp)
            else:
                for host in response:
                    hostname = host['name']
                    service_key = 'services'
                    if 'retention_services' in host:
                        service_key = 'retention_services'
                    if service_key in host:
                        for service in host[service_key]:
                            all_data['services'][(host['name'], service)] = \
                                host[service_key][service]
                    all_data['hosts'][hostname] = host
                    logger.debug('- loaded: %s', host)

        try:
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
                if not self.retention_file:
                    logger.info('Saving retention data to: %s', self.retention_dir)
                    for host_name in data_to_save['hosts']:
                        file_name = os.path.join(self.retention_dir,
                                                 self.retention_file,
                                                 "%s.json" % host_name)
                        with open(file_name, "w") as fd:
                            fd.write(json.dumps(data_to_save['hosts'][host_name],
                                                indent=2, separators=(',', ': '),
                                                sort_keys=True))
                        logger.debug('- saved: %s', file_name)
                    logger.info('Saved')
                else:
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
