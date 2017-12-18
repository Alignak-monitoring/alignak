# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2017: Alignak team, see AUTHORS.txt file for contributors
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
"""
This module provides logging facilities for Alignak:
- a main root logger for the running daemon
- a monitoring log logger

It defines a colored stream handler class to allow using colored log. Using this class is
as follows: alignak.log.ColorStreamHandler

It also defines a UTC time formatter usable as alignak.log.UTCFormatter

The setup_logger function initializes the daemon logger with the JSON provided configuration file.

The make_monitoring_log function emits a log to the monitoring log logger and returns a brok for
the Alignak broker.
"""
import sys
import json
import time

import logging
from logging import Handler, StreamHandler

from termcolor import cprint

from alignak.brok import Brok

if sys.version_info < (2, 7):
    from alignak.misc.dictconfig import dictConfig as logger_dictConfig
else:
    from logging.config import dictConfig as logger_dictConfig

# Default values for root logger
ALIGNAK_LOGGER_NAME = 'alignak'
ALIGNAK_LOGGER_LEVEL = logging.INFO

# Default values for monitoring logger
MONITORING_LOGGER_NAME = 'monitoring-log'


logging.basicConfig(filename='/tmp/alignak.log', level=logging.DEBUG)

logger = logging.getLogger(ALIGNAK_LOGGER_NAME)  # pylint: disable=C0103
logger.setLevel(ALIGNAK_LOGGER_LEVEL)


class UTCFormatter(logging.Formatter):
    """This logging formatter converts the log date/time to UTC"""
    converter = time.gmtime


class CollectorHandler(Handler):
    """
    This logging handler collects all the emitted logs in an inner list.

    Note: This s only used for unit tests purpose
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


class ColorStreamHandler(StreamHandler):
    """
    This logging handler provides colored logs when logs are emitted to a tty.
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            colors = {'DEBUG': 'cyan', 'INFO': 'magenta',
                      'WARNING': 'yellow', 'CRITICAL': 'magenta', 'ERROR': 'red'}
            cprint(msg, colors[record.levelname])
        except UnicodeEncodeError:
            print msg.encode('ascii', 'ignore')
        except IOError:
            # May happen when process are closing
            pass
        except TypeError:
            self.handleError(record)


def setup_logger(logger_configuration_file, log_dir=None, process_name='', log_file=''):
    """
    Configure the provided logger
    - get and update the content of the Json configuration file
    - configure the logger with this file

    If a log_dir and process_name are provided, the format and filename in the configuration file
    are updated with the provided values if they contain the patterns %(logdir)s and %(daemon)s

    If a log file name is provide, it will override the default defined log file name.

    :param logger_configuration_file: Python Json logger configuration file
    :rtype logger_configuration_file: str
    :param log_dir: default log directory to update the defined logging handlers
    :rtype log_dir: str
    :param process_name: process name to update the defined logging formatters
    :rtype process_name: str
    :param log_file: log file name to update the defined log file
    :rtype log_file: str
    :return: None
    """
    logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
    for handler in logger_.handlers:
        if getattr(handler, '_name', None) == 'daemons':
            # Already configured... exit
            print("Alignak logger is already configured, handlers:")
            # Update the declared formats with the process name
            for handler in logger_.handlers:
                print("- handler: %s" % handler._name)
                if process_name and 'NOTSET' in handler.formatter._fmt:
                    handler.formatter._fmt = handler.formatter._fmt.replace("NOTSET", process_name)
            break
    else:
        print("Initializing Alignak logger (%s)..." % logger_configuration_file)
        with open(logger_configuration_file, 'rt') as _file:
            config = json.load(_file)
            if not process_name:
                process_name = 'NOTSET'
            if not log_dir:
                log_dir = '/tmp'
            # Update the declared formats with the process name
            for formatter in config['formatters']:
                if 'format' not in config['formatters'][formatter]:
                    continue
                config['formatters'][formatter]['format'] = \
                    config['formatters'][formatter]['format'].replace("%(daemon)s", process_name)

            # Update the declared log file names with the log directory
            for handler in config['handlers']:
                if 'filename' not in config['handlers'][handler]:
                    continue
                if log_file:
                    config['handlers'][handler]['filename'] = log_file
                else:
                    config['handlers'][handler]['filename'] = \
                        config['handlers'][handler]['filename'].replace("%(logdir)s", log_dir)
                config['handlers'][handler]['filename'] = \
                    config['handlers'][handler]['filename'].replace("%(daemon)s", process_name)

        # Configure the logger, any error will raise an exception
        logger_dictConfig(config)
        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        print("Logger: %s" % logger_)
        for handler in logger_.handlers:
            print("- handler: %s" % handler._name)


def get_logger_fds(logger_):
    """
    Get the file descriptors used by the logger

    :param logger_: logger object to configure. If None, configure the root logger
    :return: list of file descriptors
    """
    if logger_ is None:
        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)

    fds = []
    for handler in logger_.handlers:
        try:
            fds.append(handler.stream.fileno())
        except AttributeError:
            # If a log handler do not have a stream...
            pass

    return fds


def make_monitoring_log(level, message):
    """
    Function used to build the monitoring log.

    Emit a log message with the provided level to the monitoring log logger.
    Build a Brok typed as monitoring_log with the provided message

    TODO: replace with dedicated brok for each event to log - really useful?

    :param level: log level as defined in logging
    :param message: message to send to the monitoring log logger
    :return:
    """
    logging.getLogger(ALIGNAK_LOGGER_NAME).debug("Monitoring log: %s / %s", level, message)
    level = level.lower()
    if level not in ['debug', 'info', 'warning', 'error', 'critical']:
        return False

    # Emit to our monitoring log logger
    message = message.replace('\r', '\\r')
    message = message.replace('\n', '\\n')
    logger_ = logging.getLogger(MONITORING_LOGGER_NAME)
    logging_function = getattr(logger_, level)
    try:
        message = message.decode('utf8', 'ignore')
    except UnicodeEncodeError:
        pass

    logging_function(message)

    # ... and returns a brok
    return Brok({'type': 'monitoring_log', 'data': {'level': level, 'message': message}})
