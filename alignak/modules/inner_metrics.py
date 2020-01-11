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
This module is used to manage checks results performance data
"""

import os
import re
import time
import logging
import traceback

from alignak.misc.carboniface import CarbonIface
from alignak.misc.perfdata import PerfDatas, sanitize_name
from alignak.basemodule import BaseModule

# pylint: disable=invalid-name
influxdb_lib = False
try:
    from influxdb import InfluxDBClient
    influxdb_lib = True
except ImportError:
    pass

logger = logging.getLogger(__name__)

# pylint: disable=invalid-name
properties = {
    'daemons': ['broker'],
    'type': 'metrics',
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

    return InnerMetrics(mod_conf)


class InnerMetrics(BaseModule):  # pylint: disable=too-many-instance-attributes
    """
    This class is used to store/restore retention data
    """

    def __init__(self, mod_conf):  # pylint: disable=too-many-branches
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
        logger.debug("received configuration: %s", mod_conf.__dict__)

        logger.info("loaded by the %s '%s'", self.my_daemon.type, self.my_daemon.name)

        # Output file target
        self.output_file = getattr(mod_conf, 'output_file', '')
        if 'ALIGNAK_HOSTS_STATS_FILE' in os.environ:
            self.output_file = os.environ['ALIGNAK_HOSTS_STATS_FILE']

        # Graphite / InfluxDB targets
        self.graphite_enabled = (getattr(mod_conf, 'graphite_enabled', '0') != '0')
        if isinstance(getattr(mod_conf, 'graphite_enabled', '0'), bool):
            self.graphite_enabled = getattr(mod_conf, 'graphite_enabled')
        self.influxdb_enabled = (getattr(mod_conf, 'influxdb_enabled', '0') != '0')
        if isinstance(getattr(mod_conf, 'influxdb_enabled', '0'), bool):
            self.influxdb_enabled = getattr(mod_conf, 'influxdb_enabled')
        if self.influxdb_enabled and not influxdb_lib:
            logger.info("Sending metrics to InfluxDB is enabled but the influxdb Python "
                        "library is not installed. You should 'pip install influxdb'! "
                        "As of now, sending to influxdb is disabled.")
            self.influxdb_enabled = False
        logger.info("targets configuration: graphite: %s, influxdb: %s, file: %s",
                    self.graphite_enabled, self.influxdb_enabled, self.output_file)
        if self.output_file:
            logger.warning("Storing metrics in an output file is configured. Do not forget "
                           "to regularly clean this file to avoid important disk usage!")

        self.enabled = getattr(mod_conf, 'enabled', '0') != '0'
        if isinstance(getattr(mod_conf, 'enabled', '0'), bool):
            self.enabled = getattr(mod_conf, 'enabled')

        if not self.output_file and not self.graphite_enabled and not self.influxdb_enabled:
            logger.warning("The metrics sending module is enabled but no target is defined. You "
                           "should set one of the 'output_file', or 'graphite_enabled' or "
                           "'influxdb_enabled' parameter to specify where the metrics "
                           "must be pushed! As of now, the module is disabled.")
            self.enabled = False

        # Hosts and services internal cache
        # - contain the hosts and services names and specific parameters
        # - updated with the initial hosts/services status broks
        self.hosts_cache = {}
        self.services_cache = {}

        # Do not ignore unknown hosts/services. If set, this parameter will make the module
        # ignore the provided broks until the initial status broks are received
        # Then the module will only manage metrics if hosts/services are known in the internal cache
        self.ignore_unknown = getattr(mod_conf, 'ignore_unknown', '1') == '1'
        if isinstance(getattr(mod_conf, 'ignore_unknown', '0'), bool):
            self.ignore_unknown = getattr(mod_conf, 'ignore_unknown')
        logger.info("ignoring unknown: %s", self.ignore_unknown)

        # Separate performance data multiple values
        self.multiple_values = re.compile(r'_(\d+)$')

        # Internal metrics cache
        self.my_metrics = []
        self.metrics_flush_count = int(getattr(mod_conf, 'metrics_flush_count', '256'))
        self.last_failure = 0
        self.metrics_flush_pause = int(os.getenv('ALIGNAK_STATS_FLUSH_PAUSE', '10'))
        self.log_metrics_flush_pause = False

        # Specific filter for host and services names for Graphite
        self.illegal_char_hostname = re.compile(r'[^a-zA-Z0-9_\-]')

        # Graphite target
        self.graphite_host = getattr(mod_conf, 'graphite_host', 'localhost')
        self.graphite_port = int(getattr(mod_conf, 'graphite_port', '2004'))
        self.carbon = None
        logger.info("graphite host/port: %s:%d", self.graphite_host, self.graphite_port)
        # optional prefix / suffix in graphite for Alignak data source
        self.graphite_data_source = \
            sanitize_name(getattr(mod_conf, 'graphite_data_source', ''))
        self.graphite_prefix = getattr(mod_conf, 'graphite_prefix', '')
        self.realms_prefix = (getattr(mod_conf, 'realms_prefix', '0') != '0')
        if isinstance(getattr(mod_conf, 'realms_prefix', '0'), bool):
            self.realms_prefix = getattr(mod_conf, 'realms_prefix')
        logger.info("graphite prefix: %s, realm prefix: %s, data source: %s",
                    self.graphite_prefix, self.realms_prefix, self.graphite_data_source)

        if self.graphite_enabled and not self.graphite_host:
            logger.warning("Graphite host name is not set, no metrics will be sent to Graphite!")
            self.graphite_enabled = False

        # InfluxDB target
        self.influxdb_host = getattr(mod_conf, 'influxdb_host', 'localhost')
        self.influxdb_port = int(getattr(mod_conf, 'influxdb_port', '8086'))
        self.influxdb_database = getattr(mod_conf, 'influxdb_database', 'alignak')

        # Default is empty - do not used authenticated connection
        self.influxdb_username = getattr(mod_conf, 'influxdb_username', '')
        self.influxdb_password = getattr(mod_conf, 'influxdb_password', '')

        # Default is empty - do not use a specific retention
        self.influxdb_retention_name = \
            getattr(mod_conf, 'influxdb_retention_name', '')
        self.influxdb_retention_duration = \
            getattr(mod_conf, 'influxdb_retention_duration', 'INF')
        self.influxdb_retention_replication = \
            getattr(mod_conf, 'influxdb_retention_replication', '1')
        self.influx = None
        logger.info("influxdb host/port: %s:%d", self.influxdb_host, self.influxdb_port)
        logger.info("influxdb database: %s, retention: %s:%s:%s",
                    self.influxdb_database, self.influxdb_retention_name,
                    self.influxdb_retention_duration, self.influxdb_retention_replication)
        # optional tags list in influxdb for Alignak data source
        self.influxdb_tags = getattr(mod_conf, 'influxdb_tags', None)
        if self.influxdb_tags:
            tags_list = {}
            tags = self.influxdb_tags.split(',')
            for tag in tags:
                if '=' in tag:
                    tag = tag.split('=')
                    tags_list[tag[0]] = tag[1]
            if tags_list:
                self.influxdb_tags = tags_list
        logger.info("influxdb tags: %s", self.influxdb_tags)

        if self.influxdb_enabled and not self.influxdb_host:
            logger.warning("InfluxDB host name is not set, no metrics will be sent to InfluxDB!")
            self.influxdb_enabled = False

        # Used to reset check time into the scheduled time.
        # Carbon/graphite does not like latency data and creates blanks in graphs
        # Every data with "small" latency will be considered create at scheduled time
        self.ignore_latency_limit = int(getattr(mod_conf, 'ignore_latency_limit', '0'))
        if self.ignore_latency_limit < 0:
            self.ignore_latency_limit = 0

        # service name to use for host check
        self.hostcheck = sanitize_name(getattr(mod_conf, 'host_check', 'hostcheck'))

        # Send warning, critical, min, max
        self.send_warning = bool(getattr(mod_conf, 'send_warning', False))
        logger.info("send warning metrics: %d", self.send_warning)
        self.send_critical = bool(getattr(mod_conf, 'send_critical', False))
        logger.info("send critical metrics: %d", self.send_critical)
        self.send_min = bool(getattr(mod_conf, 'send_min', False))
        logger.info("send min metrics: %d", self.send_min)
        self.send_max = bool(getattr(mod_conf, 'send_max', False))
        logger.info("send max metrics: %d", self.send_max)

        if not self.enabled:
            logger.warning("inner metrics module is loaded but is not enabled.")
            return
        logger.info("metrics module is loaded and enabled")

    def init(self):  # pylint: disable=too-many-branches
        """Called by the daemon broker to initialize the module"""
        if not self.enabled:
            logger.info(" the module is disabled.")
            return True

        connections = False
        try:
            connections = self.test_connection()
        except Exception as exp:  # pylint: disable=broad-except
            logger.error("initialization, test connection failed. Error: %s", str(exp))

        if self.influxdb_enabled:
            try:
                # Check that configured TSDB is existing, else creates...
                dbs = self.influx.get_list_database()
                for db in dbs:
                    if db.get('name') == self.influxdb_database:
                        logger.info("the database %s is existing.", self.influxdb_database)
                        break
                else:
                    # Create the database
                    logger.info("creating database %s...", self.influxdb_database)
                    self.influx.create_database(self.influxdb_database)

                # Check that configured TSDB retention is existing, else creates...
                if self.influxdb_retention_name:
                    rps = self.influx.get_list_retention_policies()
                    for rp in rps:
                        if rp.get('name') == self.influxdb_retention_name:
                            logger.info("the retention policy %s is existing.",
                                        self.influxdb_retention_name)
                            break
                    else:
                        # Create a retention policy for this database
                        logger.info("creating database retention policy: %s - %s - %s...",
                                    self.influxdb_retention_name, self.influxdb_retention_duration,
                                    self.influxdb_retention_replication)
                        self.influx.create_retention_policy(
                            self.influxdb_retention_name, self.influxdb_retention_duration,
                            self.influxdb_retention_replication, database=self.influxdb_database)

                # Check that configured TSDB user is existing, else creates...
                if self.influxdb_username:
                    users = self.influx.get_list_users()
                    for user in users:
                        if user.get('user') == self.influxdb_username:
                            logger.info("the user %s is existing.",
                                        self.influxdb_username)
                            break
                    else:
                        # Create a retention policy for this database
                        logger.info("creating user: %s...", self.influxdb_username)
                        self.influx.create_user(self.influxdb_username, self.influxdb_password,
                                                admin=False)

                connections = connections or True
            except Exception as exp:  # pylint: disable=broad-except
                logger.error("InfluxDB, DB initialization failed. Error: %s", str(exp))

        return connections

    def test_connection(self):
        """Called to test the connection

        Returns True if all configured targets are ok
        :return: bool
        """
        if not self.enabled:
            return False

        connections = False
        if self.output_file:
            logger.info("testing storage to %s ...", self.output_file)
            try:
                with open(self.output_file, 'a') as fp:
                    fp.write("%s;%s;%s\n" % (int(time.time()), 'connection-test', int(time.time())))
            except Exception as exp:  # pylint: disable=broad-except
                logger.error("File output test, error: %s", str(exp))
            else:
                connections = connections or True
                logger.info("Ok")

        if self.influxdb_enabled:
            logger.info("testing connection to InfluxDB %s:%d ...",
                        self.influxdb_host, self.influxdb_port)

            if not self.influx:
                self.influx = InfluxDBClient(host=self.influxdb_host, port=self.influxdb_port,
                                             database=self.influxdb_database,
                                             username=self.influxdb_username,
                                             password=self.influxdb_password)

            try:
                # Check that connection is correct
                version = self.influx.ping()
                logger.info("connected, InfluxDB version %s", version)
            except Exception as exp:  # pylint: disable=broad-except
                logger.error("InfluxDB test, error: %s", str(exp))
            else:
                connections = connections or True

        if self.graphite_enabled:
            logger.info("testing connection to Graphite %s:%d ...",
                        self.graphite_host, self.graphite_port)

            if not self.carbon:
                self.carbon = CarbonIface(self.graphite_host, self.graphite_port)

            carbon_data = [
                ('.'.join([self.graphite_prefix, 'connection-test']),
                 ('connection-test', int(time.time())))
            ]
            self.carbon.add_data_list(carbon_data)
            if self.carbon.send_data():
                connections = connections or True
                logger.info("Ok")
            else:
                logger.error("Ko")

        return connections

    # Common functions
    def do_loop_turn(self):
        """This function is called/used when you need a module with
        a loop function (and use the parameter 'external': True)
        """
        logger.info("In loop...")
        time.sleep(1)

    def get_metrics_from_perfdata(self, service, perf_data):
        """Decode the performance data to build a metrics list"""
        result = []
        metrics = PerfDatas(perf_data)

        for metric in metrics:
            logger.debug("service: %s, metric: %s (%s)", service, metric, metric.__dict__)

            if metric.name in ['time']:
                metric.name = "duration"
            name = sanitize_name(metric.name)
            name = self.multiple_values.sub(r'.\1', name)
            if not name:
                continue

            # get metric value and its thresholds values if they exist
            name_value = {
                name: metric.value,
                'uom_' + name: metric.uom
            }

            # Get or ignore extra values depending upon module configuration
            if metric.warning and self.send_warning:
                name_value[name + '_warn'] = metric.warning

            if metric.critical and self.send_critical:
                name_value[name + '_crit'] = metric.critical

            if metric.min and self.send_min:
                name_value[name + '_min'] = metric.min

            if metric.max and self.send_max:
                name_value[name + '_max'] = metric.max

            for key, value in name_value.items():
                result.append((key, value, metric.uom))

        logger.debug("Metrics: %s - %s", service, result)
        return result

    @property
    def metrics_count(self):
        """
        Number of internal stored metrics
        :return:
        """
        return len(self.my_metrics)

    def flush(self, log=False):  # pylint:disable=too-many-branches, too-many-nested-blocks
        """Send inner stored metrics to the configured Graphite or InfluxDB

        Returns False if the sending failed with a warning log if log parameter is set

        :param log: to log information or not
        :type log: bool

        :return: bool
        """
        if not self.my_metrics:
            logger.debug("Flushing - no metrics to send")
            return True

        now = int(time.time())
        if self.last_failure and self.last_failure + self.metrics_flush_pause > now:
            if not self.log_metrics_flush_pause:
                logger.warning("Flush paused on connection error (last failed: %d). "
                               "Inner stored metric: %d. Trying to send...",
                               self.last_failure, self.metrics_count)
                self.log_metrics_flush_pause = True
                if not self.test_connection():
                    return False

        metrics_sent = False
        metrics_saved = False

        # Flushing to Graphite
        if self.graphite_enabled:
            try:
                logger.debug("Flushing %d metrics to Graphite/carbon", self.metrics_count)

                carbon_data = []
                for metric in self.my_metrics:
                    # Get path
                    path = metric['tags']['path']
                    for name, value in metric['fields'].items():
                        carbon_data.append(
                            ('.'.join([self.graphite_prefix, '.'.join([path, name])]),
                             (metric['time'], value)))
                self.carbon.add_data_list(carbon_data)
                if self.carbon.send_data():
                    metrics_sent = True
                else:
                    if log:
                        logger.warning("Failed sending metrics to Graphite/carbon. "
                                       "Inner stored metric: %d", self.metrics_count)
                if self.log_metrics_flush_pause:
                    logger.warning("Metrics flush restored. "
                                   "Remaining stored metric: %d", self.metrics_count)
                self.last_failure = 0
                self.log_metrics_flush_pause = False
            except Exception as exp:  # pylint: disable=broad-except
                if not self.log_metrics_flush_pause:
                    logger.warning("Failed sending metrics to Graphite/carbon: %s:%d. "
                                   "Inner stored metrics count: %d.",
                                   self.graphite_host, self.graphite_port, self.metrics_count)
                    logger.warning("Exception: %s / %s", str(exp), traceback.print_exc())
                else:
                    logger.warning("Flush paused on connection error (last failed: %d). "
                                   "Inner stored metric: %d. Trying to send...",
                                   self.last_failure, self.metrics_count)

                self.last_failure = now
                return False

        # Flushing to InfluxDB
        # pylint: disable=too-many-nested-blocks
        if self.influxdb_enabled:
            try:
                logger.debug("Flushing %d metrics to InfluxDB", self.metrics_count)

                for metric in self.my_metrics:
                    metric['time'] *= 1000000000
                    for name, value in metric['fields'].items():
                        if name.startswith('uom_'):
                            continue
                        # Force set float values
                        if not isinstance(value, float):
                            try:
                                value = float(value)
                            except Exception:  # pylint: disable=broad-except
                                pass
                            metric['fields'][name] = value

                    if self.influxdb_tags is not None and isinstance(self.influxdb_tags, dict):
                        metric['tags'].update(self.influxdb_tags)

                # Write data to InfluxDB
                metrics_sent = self.influx.write_points(self.my_metrics)

                if self.log_metrics_flush_pause:
                    logger.warning("Metrics flush restored. "
                                   "Remaining stored metric: %d", self.metrics_count)
                self.last_failure = 0
                self.log_metrics_flush_pause = False
            except Exception as exp:  # pylint: disable=broad-except
                logger.warning("*** Exception: %s", str(exp))
                if not self.log_metrics_flush_pause:
                    logger.warning("Failed sending metrics to InfluxDB: %s:%d. "
                                   "Inner stored metrics count: %d.",
                                   self.influxdb_host, self.influxdb_port, self.metrics_count)
                    logger.warning("Exception: %s", str(exp))
                else:
                    logger.warning("Flush paused on connection error (last failed: %d). "
                                   "Inner stored metric: %d. Trying to send...",
                                   self.last_failure, self.metrics_count)

                self.last_failure = now
                return False

        if self.output_file:
            try:
                logger.debug("Storing %d metrics to %s", self.metrics_count, self.output_file)
                with open(self.output_file, 'a') as fp:
                    for metric in self.my_metrics:
                        # Get path
                        path = metric['tags']['path']
                        for name, value in metric['fields'].items():
                            fp.write("%s;%s;%s\n" % (metric['time'], '.'.join((path, name)), value))
                metrics_saved = True

            except Exception as exp:  # pylint: disable=broad-except
                logger.warning("Failed writing to a file: %s. "
                               "Inner stored metrics count: %d\n Exception: %s",
                               self.output_file, self.metrics_count, str(exp))
                return False

        if ((self.graphite_host or self.influxdb_host) and metrics_sent) or \
                (self.output_file and metrics_saved):
            self.my_metrics = []

        return True

    def send_to_tsdb(self, realm, host, service, metrics, ts, path):
        """Send performance data to time series database

        Indeed this function stores metrics in the internal cache and checks if the flushing
        is necessary and then flushes.

        :param realm: concerned realm
        :type: string
        :param host: concerned host
        :type: string
        :param service: concerned service
        :type: string
        :param metrics: list of metrics couple (name, value)
        :type: list
        :param ts: timestamp
        :type: int
        :param path: full path (eg. Graphite) for the received metrics
        :type: string
        """
        if ts is None:
            ts = int(time.time())

        data = {
            "measurement": service,
            "tags": {
                "host": host,
                "service": service,
                "realm": '.'.join(realm) if isinstance(realm, list) else realm,
                "path": path
            },
            "time": ts,
            "fields": {}
        }

        if path is not None:
            data['tags'].update({"path": path})

        for metric, value, _ in metrics:
            data['fields'].update({metric: value})

        # Flush if necessary
        logger.debug("Metrics data: %s", data)
        self.my_metrics.append(data)

        if self.metrics_count >= self.metrics_flush_count:
            # self.carbon.add_data_list(self.my_metrics)
            self.flush()

    def manage_initial_service_status_brok(self, b):
        """Prepare the known services cache"""
        host_name = b.data['host_name']
        service_description = b.data['service_description']
        service_id = host_name+"/"+service_description
        logger.debug("got initial service status: %s", service_id)

        if host_name not in self.hosts_cache:
            logger.error("initial service status, host is unknown: %s.", service_id)
            return

        self.services_cache[service_id] = {
        }
        if 'customs' in b.data:
            self.services_cache[service_id]['_GRAPHITE_POST'] = \
                sanitize_name(b.data['customs'].get('_GRAPHITE_POST', None))

        logger.debug("initial service status received: %s", service_id)

    def manage_initial_host_status_brok(self, b):
        """Prepare the known hosts cache"""
        host_name = b.data['host_name']
        logger.debug("got initial host status: %s", host_name)

        self.hosts_cache[host_name] = {
            'realm_name':
                sanitize_name(b.data.get('realm_name', b.data.get('realm', 'All'))),
        }
        if 'customs' in b.data:
            self.hosts_cache[host_name]['_GRAPHITE_PRE'] = \
                sanitize_name(b.data['customs'].get('_GRAPHITE_PRE', None))
            self.hosts_cache[host_name]['_GRAPHITE_GROUP'] = \
                sanitize_name(b.data['customs'].get('_GRAPHITE_GROUP', None))
        logger.debug("initial host status received: %s", host_name)

    def manage_service_check_result_brok(self, b):  # pylint: disable=too-many-branches
        """A service check result brok has just arrived ..."""
        host_name = b.data.get('host_name', None)
        service_description = b.data.get('service_description', None)
        if not host_name or not service_description:
            return
        service_id = host_name+"/"+service_description
        logger.debug("service check result: %s", service_id)

        # If host and service initial status broks have not been received, ignore ...
        if not self.ignore_unknown and host_name not in self.hosts_cache:
            logger.warning("received service check result for an unknown host: %s", service_id)
            return
        if service_id not in self.services_cache and not self.ignore_unknown:
            logger.warning("received service check result for an unknown service: %s", service_id)
            return

        # Decode received metrics
        metrics = self.get_metrics_from_perfdata(service_description, b.data['perf_data'])
        if not metrics:
            logger.debug("no metrics to send ...")
            return

        # If checks latency is ignored
        if self.ignore_latency_limit >= b.data['latency'] > 0:
            check_time = int(b.data['last_chk']) - int(b.data['latency'])
        else:
            check_time = int(b.data['last_chk'])

        # Custom hosts variables
        hname = sanitize_name(host_name)
        if host_name in self.hosts_cache:
            if self.hosts_cache[host_name].get('_GRAPHITE_GROUP', None):
                hname = ".".join((self.hosts_cache[host_name].get('_GRAPHITE_GROUP'), hname))

            if self.hosts_cache[host_name].get('_GRAPHITE_PRE', None):
                hname = ".".join((self.hosts_cache[host_name].get('_GRAPHITE_PRE'), hname))

        # Custom services variables
        desc = sanitize_name(service_description)
        if service_id in self.services_cache:
            if self.services_cache[service_id].get('_GRAPHITE_POST', None):
                desc = ".".join((desc, self.services_cache[service_id].get('_GRAPHITE_POST', None)))

        # Graphite data source
        if self.graphite_data_source:
            path = '.'.join((hname, self.graphite_data_source, desc))
        else:
            path = '.'.join((hname, desc))

        # Realm as a prefix
        if self.realms_prefix and self.hosts_cache[host_name].get('realm_name', None):
            path = '.'.join((self.hosts_cache[host_name].get('realm_name'), path))

        realm_name = None
        if host_name in self.hosts_cache:
            realm_name = self.hosts_cache[host_name].get('realm_name', None)

        # Send metrics
        self.send_to_tsdb(realm_name, host_name, service_description, metrics, check_time, path)

    def manage_host_check_result_brok(self, b):  # pylint: disable=too-many-branches
        """An host check result brok has just arrived..."""
        host_name = b.data.get('host_name', None)
        if not host_name:
            return
        logger.debug("host check result: %s", host_name)

        # If host initial status brok has not been received, ignore ...
        if host_name not in self.hosts_cache and not self.ignore_unknown:
            logger.warning("received host check result for an unknown host: %s", host_name)
            return

        # Decode received metrics
        metrics = self.get_metrics_from_perfdata('host_check', b.data['perf_data'])
        if not metrics:
            logger.debug("no metrics to send ...")
            return

        # If checks latency is ignored
        if self.ignore_latency_limit >= b.data['latency'] > 0:
            check_time = int(b.data['last_chk']) - int(b.data['latency'])
        else:
            check_time = int(b.data['last_chk'])

        # Custom hosts variables
        hname = sanitize_name(host_name)
        if host_name in self.hosts_cache:
            if self.hosts_cache[host_name].get('_GRAPHITE_GROUP', None):
                hname = ".".join((self.hosts_cache[host_name].get('_GRAPHITE_GROUP'), hname))

            if self.hosts_cache[host_name].get('_GRAPHITE_PRE', None):
                hname = ".".join((self.hosts_cache[host_name].get('_GRAPHITE_PRE'), hname))

        # Graphite data source
        if self.graphite_data_source:
            path = '.'.join((hname, self.graphite_data_source))
            if self.hostcheck:
                path = '.'.join((hname, self.graphite_data_source, self.hostcheck))
        else:
            path = '.'.join((hname, self.hostcheck))

        # Realm as a prefix
        if self.realms_prefix and self.hosts_cache[host_name].get('realm_name', None):
            path = '.'.join((self.hosts_cache[host_name].get('realm_name'), path))

        realm_name = None
        if host_name in self.hosts_cache:
            realm_name = self.hosts_cache[host_name].get('realm_name', None)

        # Send metrics
        self.send_to_tsdb(realm_name, host_name, self.hostcheck, metrics, check_time, path)
