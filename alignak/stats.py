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
#     Grégory Starck, g.starck@gmail.com
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr

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

"""This module allows to export Alignak internal metrics to a statsd server.

The register function allows an Alignak daemon to register some metrics and the
expected behavior (sends to StatsD server and/or build an internal brok).

As such it:

- registers the StatsD connexion parameters
- tries to establish a connection if the StatsD sending is enabled
- creates an inner dictionary for the registered metrics

If some environment variables exist the metrics will be logged to a file in append mode:
    'ALIGNAK_STATS_FILE'
        the file name
    'ALIGNAK_STATS_FILE_LINE_FMT'
        defaults to [#date#] #counter# #value# #uom#\n'
    'ALIGNAK_STATS_FILE_DATE_FMT'
        defaults to '%Y-%m-%d %H:%M:%S'
        date is UTC
        if configured as an empty string, the date will be output as a UTC timestamp

Every time a metric is updated thanks to the provided functions, the inner dictionary
is updated according to keep the last value, the minimum/maximum values, to update an
internal count of each update and to sum the collected values.
**Todo**: Interest of this feature is to be proven ;)

The `timer` function sends a timer value to the StatsD registered server and
creates an internal brok.

..note: the `incr` function simply calls the `timer` function and is kept for compatibility.

The `counter` function sends a counter value to the StatsD registered server and
creates an internal brok.

The `gauge` function sends a gauge value to the StatsD registered server and
creates an internal brok.

-----
NOTE: this statistics dictionary is an old version that needs to be updated !
-----
Alignak daemons statistics dictionary:

* scheduler: (some more exist but hereunder are the main metrics)
    - configuration objects count (gauge)
        - configuration.hosts
        - configuration.services
        - configuration.hostgroups
        - configuration.servicegroups
        - configuration.contacts
        - configuration.contactgroups
        - configuration.timeperiods
        - configuration.commands
        - configuration.notificationways
        - configuration.escalations

    - retention objects count (gauge)
        - retention.hosts
        - retention.services

    - scheduler load (gauge):
        - load.sleep
        - load.average
        - load.load

    - scheduler checks (gauge)
        - checks.total
        - checks.scheduled
        - checks.in_poller
        - checks.zombie
        - actions.notifications

    - first_scheduling (timer) - for the first scheduling on start
    - push_actions_to_passives_satellites (timer) - duration to push actions to
                                                    passive satellites
    - get_actions_from_passives_satellites (timer) - duration to get results from
                                                     passive satellites
    - loop.whole (timer) - for the scheduler complete loop
    - loop.%s (timer) -  for each scheduler recurrent work in the loop, where %s can be:
            update_downtimes_and_comments
            schedule
            check_freshness
            consume_results
            get_new_actions
            scatter_master_notifications
            get_new_broks
            delete_zombie_checks
            delete_zombie_actions
            clean_caches
            update_retention
            check_orphaned
            update_program_status
            check_for_system_time_change
            manage_internal_checks
            clean_queues
            update_business_values
            reset_topology_change_flags
            check_for_expire_acknowledge
            send_broks_to_modules
            get_objects_from_from_queues
            get_latency_average_percentile

* satellite (poller, reactionner):
    - con-init.scheduler (timer) - for the scheduler connection duration
    - core.get-new-actions (timer) - duration to get the new actions to execute from the scheduler
    - core.manage-returns (timer) - duration to send back to the scheduler the results of
                                    executed actions
    - core.worker-%s.queue-size (gauge) - size of the actions queue for each satellite worker
    - core.wait-ratio (timer) - time waiting for lanched actions to finish
    - core.wait-arbiter (timer) - time waiting for arbiter configuration

* all daemons:
    - core.hook.%s (timer) - duration spent in each hook function provided by a module

* arbiter:
    - core.hook.get_objects (timer) - duration spent in the get_objects hook function provided
                                      by a module
    - core.check-alive (timer) - duration to check that alignak daemons are alive
    - core.check-dispatch (timer) - duration to check that the configuration is correctly
                                    dispatched
    - core.dispatch (timer) - duration to dispatch the configuration to the daemons
    - core.check-bad-dispatch (timer) - duration to confirm that the configuration is
                                        correctly dispatched
    - core.push-external-commands (timer) - duration to push the external commands to the
                                            schedulers

* receiver:
    - external-commands.pushed (gauge) - number of external commands pushed to schedulers
    - core.get-objects-from-queues (timer) - duration to get the objects from modules queues
    - core.push-external-commands (timer) - duration to push the external commands to the
                                            schedulers

* broker:
    - con-init.%s (timer) - for the %s daemon connection duration
    - get-new-broks.%s (timer) - duration to get new broks from other daemons, where %s can
                                 be: arbiter, scheduler, poller, reactionner, receiver or broker
                                 broker is used for self generated broks
    - core.put-to-external-queue (timer) - duration to send broks to external modules
    - core.put-to-external-queue.%s (timer) - duration to send broks to each external module,
                                              where %s is the external module alias
    - core.manage-broks (timer) - duration to manage broks with internal modules
    - core.manage-broks.%s (timer) - duration to manage broks with each internal module,
                                     where %s is the internal module alias

"""

import os
import sys
import time
import datetime
import socket
import logging

from alignak.brok import Brok
if sys.version_info >= (2, 7):
    from alignak.misc.carboniface import CarbonIface

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Stats(object):
    # pylint: disable=too-many-instance-attributes
    """Stats class to export data into a statsd format

    This class allows to send metrics to a StatsD server using UDP datagrams.
    Same behavior as::

        echo "foo:1|c" | nc -u -w0 127.0.0.1 8125

    With the Graphite option, this class stores the metrics in an inner list and
    flushes the metrics to a Graphite instance when the flush method is called.

    """
    def __init__(self):
        # Our daemon type and name
        self.name = ''
        # This attribute is not used, but I keep ascending compatibility with former interface!
        self._type = None

        # Our known statistics
        self.stats = {}

        # local statsd part
        self.statsd_host = None
        self.statsd_port = None
        self.statsd_prefix = None
        self.statsd_enabled = None

        # local broks part
        self.broks_enabled = None

        # Statsd daemon parameters
        self.statsd_sock = None
        self.statsd_addr = None

        # Graphite connection
        self.carbon = None
        self.my_metrics = []
        self.metrics_flush_count = 64

        # File part
        self.stats_file = None
        self.file_d = None
        if 'ALIGNAK_STATS_FILE' in os.environ:
            self.stats_file = os.environ['ALIGNAK_STATS_FILE']
        self.line_fmt = '[#date#] #counter# #value# #uom#\n'
        if 'ALIGNAK_STATS_FILE_LINE_FMT' in os.environ:
            self.line_fmt = os.environ['ALIGNAK_STATS_FILE_LINE_FMT']
        self.date_fmt = '%Y-%m-%d %H:%M:%S'
        if 'ALIGNAK_STATS_FILE_DATE_FMT' in os.environ:
            self.date_fmt = os.environ['ALIGNAK_STATS_FILE_DATE_FMT']

    @property
    def metrics_count(self):
        """
        Number of internal stored metrics
        :return:
        """
        return len(self.my_metrics)

    def __repr__(self):  # pragma: no cover
        return '<StatsD report to %r:%r, enabled: %r />' \
               % (self.statsd_host, self.statsd_port, self.statsd_enabled)
    __str__ = __repr__

    def register(self, name, _type, statsd_host='localhost', statsd_port=8125,
                 statsd_prefix='alignak', statsd_enabled=False, broks_enabled=False):
        """Init instance with real values

        :param name: daemon name
        :type name: str
        :param _type: daemon type
        :type _type:
        :param statsd_host: host to post data
        :type statsd_host: str
        :param statsd_port: port to post data
        :type statsd_port: int
        :param statsd_prefix: prefix to add to metric
        :type statsd_prefix: str
        :param statsd_enabled: bool to enable statsd
        :type statsd_enabled: bool
        :param broks_enabled: bool to enable broks sending
        :type broks_enabled: bool
        :return: None
        """
        self.name = name
        # This attribute is not used, but I keep ascending compatibility with former interface!
        self._type = _type

        # local statsd part
        self.statsd_host = statsd_host
        self.statsd_port = int(statsd_port)
        self.statsd_prefix = statsd_prefix
        self.statsd_enabled = statsd_enabled

        # local broks part
        self.broks_enabled = broks_enabled

        logger.debug("StatsD configuration for %s - %s:%s, prefix: %s, "
                     "enabled: %s, broks: %s, file: %s",
                     self.name, self.statsd_host, self.statsd_port,
                     self.statsd_prefix, self.statsd_enabled, self.broks_enabled,
                     self.stats_file)

        if self.statsd_enabled and self.statsd_host is not None and self.statsd_host != 'None':
            logger.info("Sending %s statistics to: %s:%s, prefix: %s",
                        self.name, self.statsd_host, self.statsd_port, self.statsd_prefix)
            if self.load_statsd():
                logger.info('Alignak internal statistics are sent to StatsD.')
            else:
                logger.info('StatsD server is not available.')

        if self.stats_file:
            try:
                self.file_d = open(self.stats_file, 'a')
                logger.info("Alignak internal statistics are written in the file %s",
                            self.stats_file)
            except OSError as exp:  # pragma: no cover, should never happen...
                logger.exception("Error when opening the file '%s' : %s", self.stats_file, exp)
                self.file_d = None

        return self.statsd_enabled

    def load_statsd(self):
        """Create socket connection to statsd host

        Note that because of the UDP protocol used by StatsD, if no server is listening the
        socket connection will be accepted anyway :)

        :return: True if socket got created else False and an exception log is raised
        """
        if not self.statsd_enabled:
            logger.info('Stats reporting is not enabled, connection is not allowed')
            return False

        if self.statsd_enabled and self.carbon:
            self.my_metrics.append(('.'.join([self.statsd_prefix, self.name, 'connection-test']),
                                    (int(time.time()), int(time.time()))))
            self.carbon.add_data_list(self.my_metrics)
            self.flush(log=True)
        else:
            try:
                logger.info('Trying to contact StatsD server...')
                self.statsd_addr = (socket.gethostbyname(self.statsd_host.encode('utf-8')),
                                    self.statsd_port)
                self.statsd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            except (socket.error, socket.gaierror) as exp:
                logger.warning('Cannot create StatsD socket: %s', exp)
                return False
            except Exception as exp:  # pylint: disable=broad-except
                logger.exception('Cannot create StatsD socket (other): %s', exp)
                return False

            logger.info('StatsD server contacted')
        return True

    def connect(self, name, _type, host='localhost', port=2003,
                prefix='alignak', enabled=False, broks_enabled=False):
        """Init instance with real values for a graphite/carbon connection

        :param name: daemon name
        :type name: str
        :param _type: daemon type
        :type _type:
        :param host: host to post data
        :type host: str
        :param port: port to post data
        :type port: int
        :param prefix: prefix to add to metric
        :type prefix: str
        :param enabled: bool to enable statsd
        :type enabled: bool
        :param broks_enabled: bool to enable broks sending
        :type broks_enabled: bool
        :return: None
        """
        self.name = name
        # This attribute is not used, but I keep ascending compatibility with former interface!
        self._type = _type

        # local graphite/carbon part
        self.statsd_host = host
        try:
            self.statsd_port = int(port)
        except ValueError:
            self.statsd_port = 2003
        self.statsd_prefix = prefix
        self.statsd_enabled = enabled

        # local broks part
        self.broks_enabled = broks_enabled

        logger.debug("Graphite/carbon configuration for %s - %s:%s, prefix: %s, "
                     "enabled: %s, broks: %s, file: %s",
                     self.name, self.statsd_host, self.statsd_port,
                     self.statsd_prefix, self.statsd_enabled, self.broks_enabled,
                     self.stats_file)

        if self.statsd_enabled and self.statsd_host is not None and self.statsd_host != 'None':
            logger.info("Sending %s statistics to: %s:%s, prefix: %s",
                        self.name, self.statsd_host, self.statsd_port, self.statsd_prefix)

            self.carbon = CarbonIface(self.statsd_host, self.statsd_port)
            logger.info('Alignak internal statistics will be sent to Graphite.')

        return self.statsd_enabled

    def flush(self, log=False):
        """Send inner stored metrics to the defined Graphite

        Returns False if the sending failed with a warning log if log parameter is set

        :return: bool
        """
        if not self.my_metrics:
            logger.debug("Flushing - no metrics to send")
            return True

        try:
            logger.debug("Flushing %d metrics to Graphite/carbon", self.metrics_count)
            if self.carbon.send_data():
                self.my_metrics = []
            else:
                if log:
                    logger.warning("Failed sending metrics to Graphite/carbon. "
                                   "Inner stored metric: %d", self.metrics_count)
                return False
        except Exception as exp:  # pylint: disable=broad-except
            logger.warning("Failed sending metrics to Graphite/carbon. Inner stored metric: %d",
                           self.metrics_count)
            logger.warning("Exception: %s", str(exp))
            return False
        return True

    def send_to_graphite(self, metric, value):
        """
        Inner store a new metric and flush to Graphite if the flush threshold is reached
        :param metric:
        :param value:
        :return:
        """
        # Manage Graphite part
        if self.statsd_enabled and self.carbon:
            self.my_metrics.append(('.'.join([self.statsd_prefix, self.name, metric]),
                                    (int(time.time()), value)))
            if self.metrics_count >= self.metrics_flush_count:
                self.carbon.add_data_list(self.my_metrics)
                self.flush()

    def timer(self, key, value):
        """Set a timer value

        If the inner key does not exist is is created

        :param key: timer to update
        :type key: str
        :param value: time value (in seconds)
        :type value: float
        :return: An alignak_stat brok if broks are enabled else None
        """
        _min, _max, count, _sum = self.stats.get(key, (None, None, 0, 0))
        count += 1
        _sum += value
        if _min is None or value < _min:
            _min = value
        if _max is None or value > _max:
            _max = value
        self.stats[key] = (_min, _max, count, _sum)

        # Manage local statsd part
        if self.statsd_enabled and self.statsd_sock:
            # beware, we are sending ms here, timer is in seconds
            packet = '%s.%s.%s:%d|ms' % (self.statsd_prefix, self.name, key, value * 1000)
            packet = packet.encode('utf-8')
            # Do not log because it is spamming the log file, but leave this code in place
            # for it may be restored easily if more tests are necessary... ;)
            # logger.info("Sending data: %s", packet)
            try:
                self.statsd_sock.sendto(packet, self.statsd_addr)
            except (socket.error, socket.gaierror):
                pass
                # cannot send? ok not a huge problem here and we cannot
                # log because it will be far too verbose :p

        # Manage Graphite part
        if self.statsd_enabled and self.carbon:
            self.send_to_graphite(key, value)

        # Manage file part
        if self.statsd_enabled and self.file_d:
            packet = self.line_fmt
            if not self.date_fmt:
                date = "%s" % time.time()
            else:
                date = datetime.datetime.utcnow().strftime(self.date_fmt)
            packet = packet.replace("#date#", date)
            packet = packet.replace("#counter#", '%s.%s.%s' % (self.statsd_prefix, self.name, key))
            # beware, we are sending ms here, timer is in seconds
            packet = packet.replace("#value#", '%d' % (value * 1000))
            packet = packet.replace("#uom#", 'ms')
            # Do not log because it is spamming the log file, but leave this code in place
            # for it may be restored easily if more tests are necessary... ;)
            # logger.debug("Writing data: %s", packet)
            try:
                self.file_d.write(packet)
            except IOError:
                logger.warning("Could not write to the file: %s", packet)

        if self.broks_enabled:
            logger.debug("alignak stat brok: %s = %s", key, value)
            return Brok({'type': 'alignak_stat',
                         'data': {
                             'type': 'timer',
                             'metric': '%s.%s.%s' % (self.statsd_prefix, self.name, key),
                             'value': value * 1000,
                             'uom': 'ms'
                         }})

        return None

    def counter(self, key, value):
        """Set a counter value

        If the inner key does not exist is is created

        :param key: counter to update
        :type key: str
        :param value: counter value
        :type value: float
        :return: An alignak_stat brok if broks are enabled else None
        """
        _min, _max, count, _sum = self.stats.get(key, (None, None, 0, 0))
        count += 1
        _sum += value
        if _min is None or value < _min:
            _min = value
        if _max is None or value > _max:
            _max = value
        self.stats[key] = (_min, _max, count, _sum)

        # Manage local statsd part
        if self.statsd_enabled and self.statsd_sock:
            # beware, we are sending ms here, timer is in seconds
            packet = '%s.%s.%s:%d|c' % (self.statsd_prefix, self.name, key, value)
            packet = packet.encode('utf-8')
            # Do not log because it is spamming the log file, but leave this code in place
            # for it may be restored easily if more tests are necessary... ;)
            # logger.info("Sending data: %s", packet)
            try:
                self.statsd_sock.sendto(packet, self.statsd_addr)
            except (socket.error, socket.gaierror):
                pass
                # cannot send? ok not a huge problem here and we cannot
                # log because it will be far too verbose :p

        # Manage Graphite part
        if self.statsd_enabled and self.carbon:
            self.send_to_graphite(key, value)

        # Manage file part
        if self.statsd_enabled and self.file_d:
            packet = self.line_fmt
            if not self.date_fmt:
                date = "%s" % time.time()
            else:
                date = datetime.datetime.utcnow().strftime(self.date_fmt)
            packet = packet.replace("#date#", date)
            packet = packet.replace("#counter#", '%s.%s.%s' % (self.statsd_prefix, self.name, key))
            packet = packet.replace("#value#", '%d' % value)
            packet = packet.replace("#uom#", 'c')
            # Do not log because it is spamming the log file, but leave this code in place
            # for it may be restored easily if more tests are necessary... ;)
            # logger.debug("Writing data: %s", packet)
            try:
                self.file_d.write(packet)
            except IOError:
                logger.warning("Could not write to the file: %s", packet)

        if self.broks_enabled:
            logger.debug("alignak stat brok: %s = %s", key, value)
            return Brok({'type': 'alignak_stat',
                         'data': {
                             'type': 'counter',
                             'metric': '%s.%s.%s' % (self.statsd_prefix, self.name, key),
                             'value': value,
                             'uom': 'c'
                         }})

        return None

    def gauge(self, key, value):
        """Set a gauge value

        If the inner key does not exist is is created

        :param key: gauge to update
        :type key: str
        :param value: counter value
        :type value: float
        :return: An alignak_stat brok if broks are enabled else None
        """
        _min, _max, count, _sum = self.stats.get(key, (None, None, 0, 0))
        count += 1
        _sum += value
        if _min is None or value < _min:
            _min = value
        if _max is None or value > _max:
            _max = value
        self.stats[key] = (_min, _max, count, _sum)

        # Manage local statsd part
        if self.statsd_enabled and self.statsd_sock:
            # beware, we are sending ms here, timer is in seconds
            packet = '%s.%s.%s:%d|g' % (self.statsd_prefix, self.name, key, value)
            packet = packet.encode('utf-8')
            # Do not log because it is spamming the log file, but leave this code in place
            # for it may be restored easily if more tests are necessary... ;)
            # logger.info("Sending data: %s", packet)
            try:
                self.statsd_sock.sendto(packet, self.statsd_addr)
            except (socket.error, socket.gaierror):
                pass
                # cannot send? ok not a huge problem here and we cannot
                # log because it will be far too verbose :p

        # Manage file part
        if self.statsd_enabled and self.file_d:
            packet = self.line_fmt
            if not self.date_fmt:
                date = "%s" % time.time()
            else:
                date = datetime.datetime.utcnow().strftime(self.date_fmt)
            packet = packet.replace("#date#", date)
            packet = packet.replace("#counter#", '%s.%s.%s' % (self.statsd_prefix, self.name, key))
            packet = packet.replace("#value#", '%d' % value)
            packet = packet.replace("#uom#", 'g')
            # Do not log because it is spamming the log file, but leave this code in place
            # for it may be restored easily if more tests are necessary... ;)
            # logger.debug("Writing data: %s", packet)
            try:
                self.file_d.write(packet)
            except IOError:
                logger.warning("Could not write to the file: %s", packet)

        # Manage Graphite part
        if self.statsd_enabled and self.carbon:
            self.send_to_graphite(key, value)

        if self.broks_enabled:
            logger.debug("alignak stat brok: %s = %s", key, value)
            return Brok({'type': 'alignak_stat',
                         'data': {
                             'type': 'gauge',
                             'metric': '%s.%s.%s' % (self.statsd_prefix, self.name, key),
                             'value': value,
                             'uom': 'g'
                         }})

        return None


# pylint: disable=invalid-name
statsmgr = Stats()
