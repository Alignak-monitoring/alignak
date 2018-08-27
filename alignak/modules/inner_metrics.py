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

from alignak.misc.carboniface import CarbonIface
from alignak.misc.perfdata import PerfDatas
from alignak.stats import Stats
from alignak.basemodule import BaseModule

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

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

        # Hosts and services internal cache
        # Do not ignore unknown hosts/services. If set, this parameter will make the module
        # ignore the provided broks until the initial status broks are received
        self.ignore_unknown = getattr(mod_conf, 'ignore_unknown', '1') == '1'
        logger.info("ignoring unknown: %s", self.ignore_unknown)
        if isinstance(getattr(mod_conf, 'ignore_unknown', '0'), bool):
            self.ignore_unknown = getattr(mod_conf, 'ignore_unknown')
        logger.info("ignoring unknown: %s", self.ignore_unknown)
        self.hosts_cache = {}
        self.services_cache = {}

        # Separate performance data multiple values
        self.multival = re.compile(r'_(\d+)$')

        # Graphite socket connection and cache management
        # self.con = None
        # Graphite connection
        self.outer_stats = Stats()

        # Graphite connection
        self.carbon = None
        self.my_metrics = []
        self.metrics_flush_count = int(getattr(mod_conf, 'metrics_flush_count', '64'))

        # Specific filter to allow metrics to include '.' for Graphite
        self.illegal_char_metric = re.compile(r'[^a-zA-Z0-9_.\-]')

        # Specific filter for host and services names for Graphite
        self.illegal_char_hostname = re.compile(r'[^a-zA-Z0-9_\-]')

        self.host = getattr(mod_conf, 'graphite_host', 'localhost')
        self.port = int(getattr(mod_conf, 'graphite_port', '2004'))
        self.prefix = getattr(mod_conf, 'graphite_prefix', '')
        logger.info("graphite host/port: %s:%d, prefix: %s, flush every %d metrics",
                    self.host, self.port, self.prefix, self.metrics_flush_count)
        if not self.host:
            logger.warning("Graphite host name is not set, no metrics will be sent to Graphite!")

        self.output_file = getattr(mod_conf, 'output_file', '')
        if 'ALIGNAK_HOSTS_STATS_FILE' in os.environ:
            self.output_file = os.environ['ALIGNAK_HOSTS_STATS_FILE']
        if self.output_file:
            logger.info("output file: %s", self.output_file)

        # Used to reset check time into the scheduled time.
        # Carbon/graphite does not like latency data and creates blanks in graphs
        # Every data with "small" latency will be considered create at scheduled time
        self.ignore_latency_limit = int(getattr(mod_conf, 'ignore_latency_limit', '0'))
        if self.ignore_latency_limit < 0:
            self.ignore_latency_limit = 0

        # service name to use for host check
        self.hostcheck = getattr(mod_conf, 'hostcheck', '')

        # optional "sub-folder" in graphite for Alignak data source
        self.graphite_data_source = \
            self.illegal_char_metric.sub('_', getattr(mod_conf, 'graphite_data_source', ''))
        logger.info("graphite data source: %s", self.graphite_data_source)

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

    def init(self):
        """Called by the daemon broker to initialize the module"""
        logger.info("[metrics] initializing connection to %s:%d ...", self.host, self.port)

        # Configure our Stats manager
        self.carbon = CarbonIface(self.host, self.port)
        self.my_metrics.append(('.'.join([self.prefix, 'connection-test']),
                                (int(time.time()), int(time.time()))))
        self.carbon.add_data_list(self.my_metrics)
        self.flush(log=True)
        return self.outer_stats.connect(self.alias, 'outer', host=self.host, port=self.port,
                                        prefix='test', enabled=True)

    # Common functions
    def do_loop_turn(self):
        """This function is called/used when you need a module with
        a loop function (and use the parameter 'external': True)
        """
        logger.info("[Inner Retention] In loop")
        time.sleep(1)

    def get_metric_and_value(self, service, perf_data):
        """Decode the performance data to build a metrics list"""
        result = []
        metrics = PerfDatas(perf_data)

        for metric in metrics:
            logger.debug(" service: %s, metric: %s", service, metric)
            # if service in self.filtered_metrics:
            #     if e.name in self.filtered_metrics[service]:
            #         logger.debug(" Ignore metric '%s' for filtered service: %s",
            #                      e.name, service)
            #         continue

            name = self.illegal_char_metric.sub('_', metric.name)
            name = self.multival.sub(r'.\1', name)

            # get metric value and its thresholds values if they exist
            name_value = {name: metric.value}
            if name_value[name] == '':
                continue

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
                result.append((key, value))

        logger.debug("Metrics: %s - %s", service, result)
        return result

    @property
    def metrics_count(self):
        """
        Number of internal stored metrics
        :return:
        """
        return len(self.my_metrics)

    def flush(self, log=False):
        """Send inner stored metrics to the defined Graphite

        Returns False if the sending failed with a warning log if log parameter is set

        :return: bool
        """
        if not self.my_metrics:
            logger.debug("Flushing - no metrics to send")
            return True

        metrics_sent = False
        metrics_saved = False
        if self.host:
            try:
                logger.debug("Flushing %d metrics to Graphite/carbon", self.metrics_count)
                if self.carbon.send_data():
                    metrics_sent = True
                else:
                    if log:
                        logger.warning("Failed sending metrics to Graphite/carbon. "
                                       "Inner stored metric: %d", self.metrics_count)
            except Exception as exp:  # pylint: disable=broad-except
                logger.warning("Failed sending metrics to Graphite/carbon: %s:%d. "
                               "Inner stored metrics count: %d\n Exception: %s",
                               self.host, self.port, self.metrics_count, str(exp))
                return False

        if self.output_file:
            try:
                logger.debug("Storing %d metrics to %s", self.metrics_count, self.output_file)
                with open(self.output_file, 'a') as fp:
                    for metric_name, metric_value in self.my_metrics:
                        fp.write("%s;%s;%s\n" % (metric_value[0], metric_name, metric_value[1]))
                metrics_saved = True

            except Exception as exp:  # pylint: disable=broad-except
                logger.warning("Failed writing to a file: %s. "
                               "Inner stored metrics count: %d\n Exception: %s",
                               self.output_file, self.metrics_count, str(exp))
                return False

        if (self.host and metrics_sent) or (self.output_file and metrics_saved):
            self.my_metrics = []

        return True

    def send_to_graphite(self, metric, value, ts=None):
        """
        Inner store a new metric and flush to Graphite if the flush threshold is reached.

        If no timestamp is provided, get the current time for the metric timestam.

        :param metric: metric name in dotted format
        :type metric: str
        :param value:
        :type value: float
        :param ts: metric timestamp
        :type ts: int
        """
        # Manage Graphite part
        if not self.carbon:
            return

        if ts is None:
            ts = int(time.time())

        self.my_metrics.append(('.'.join([self.prefix, metric]), (ts, value)))
        if self.metrics_count >= self.metrics_flush_count:
            self.carbon.add_data_list(self.my_metrics)
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

        self.services_cache[service_id] = {}
        if b.data.get('customs', None):
            if '_GRAPHITE_POST' in b.data['customs']:
                self.services_cache[service_id]['_GRAPHITE_POST'] = \
                    b.data['customs']['_GRAPHITE_POST']

        logger.debug("initial service status received: %s", service_id)

    def manage_initial_host_status_brok(self, b):
        """Prepare the known hosts cache"""
        host_name = b.data['host_name']
        logger.debug("got initial host status: %s", host_name)

        self.hosts_cache[host_name] = {}
        if b.data.get('customs', None):
            if '_GRAPHITE_PRE' in b.data['customs']:
                self.hosts_cache[host_name]['_GRAPHITE_PRE'] = \
                    b.data['customs']['_GRAPHITE_PRE']
            if '_GRAPHITE_GROUP' in b.data['customs']:
                self.hosts_cache[host_name]['_GRAPHITE_GROUP'] = \
                    b.data['customs']['_GRAPHITE_GROUP']

        logger.debug("initial host status received: %s", host_name)

    def manage_service_check_result_brok(self, b):  # pylint: disable=too-many-branches
        """A service check result brok has just arrived ..."""
        host_name = b.data['host_name']
        service_description = b.data['service_description']
        service_id = host_name+"/"+service_description
        logger.debug(" service check result: %s", service_id)

        # If host and service initial status brokes have not been received, ignore ...
        if not self.ignore_unknown and host_name not in self.hosts_cache:
            logger.warning(" received service check result for an unknown host: %s", service_id)
            return
        if not self.ignore_unknown and service_id not in self.services_cache:
            logger.warning(" received service check result for an unknown service: %s", service_id)
            return

        # Decode received metrics
        couples = self.get_metric_and_value(service_description, b.data['perf_data'])
        if not couples:
            logger.debug(" no metrics to send ...")
            return

        # Custom hosts variables
        hname = self.illegal_char_hostname.sub('_', host_name)
        if host_name in self.hosts_cache:
            if '_GRAPHITE_GROUP' in self.hosts_cache[host_name]:
                hname = ".".join((self.hosts_cache[host_name]['_GRAPHITE_GROUP'], hname))

            if '_GRAPHITE_PRE' in self.hosts_cache[host_name]:
                hname = ".".join((self.hosts_cache[host_name]['_GRAPHITE_PRE'], hname))

        # Custom services variables
        desc = self.illegal_char_hostname.sub('_', service_description)
        if service_id in self.services_cache:
            if '_GRAPHITE_POST' in self.services_cache[service_id]:
                desc = ".".join((desc, self.services_cache[service_id]['_GRAPHITE_POST']))

        # Checks latency
        if self.ignore_latency_limit >= b.data['latency'] > 0:
            check_time = int(b.data['last_chk']) - int(b.data['latency'])
        else:
            check_time = int(b.data['last_chk'])

        # Graphite data source
        if self.graphite_data_source:
            path = '.'.join((hname, self.graphite_data_source, desc))
        else:
            path = '.'.join((hname, desc))

        for metric, value in couples:
            self.send_to_graphite('%s.%s' % (path, metric), value, check_time)

    def manage_host_check_result_brok(self, b):
        """An host check result brok has just arrived..."""
        host_name = b.data['host_name']
        logger.debug(" host check result: %s", host_name)

        # If host initial status brok has not been received, ignore ...
        if not self.ignore_unknown and host_name not in self.hosts_cache:
            logger.warning(" received host check result for an unknown host: %s", host_name)
            return

        # Decode received metrics
        couples = self.get_metric_and_value('host_check', b.data['perf_data'])
        if not couples:
            logger.debug(" no metrics to send ...")
            return

        # Custom hosts variables
        hname = self.illegal_char_hostname.sub('_', host_name)
        if host_name in self.hosts_cache:
            if '_GRAPHITE_GROUP' in self.hosts_cache[host_name]:
                hname = ".".join((self.hosts_cache[host_name]['_GRAPHITE_GROUP'], hname))

            if '_GRAPHITE_PRE' in self.hosts_cache[host_name]:
                hname = ".".join((self.hosts_cache[host_name]['_GRAPHITE_PRE'], hname))

        if self.hostcheck:
            hname = '.'.join((hname, self.hostcheck))

        # If checks latency is ignored
        if self.ignore_latency_limit >= b.data['latency'] > 0:
            check_time = int(b.data['last_chk']) - int(b.data['latency'])
        else:
            check_time = int(b.data['last_chk'])

        # Graphite data source
        if self.graphite_data_source:
            path = '.'.join((hname, self.graphite_data_source))
            if self.hostcheck:
                path = '.'.join((hname, self.graphite_data_source, self.hostcheck))
        else:
            path = hname

        for metric, value in couples:
            self.send_to_graphite('%s.%s' % (path, metric), value, check_time)
