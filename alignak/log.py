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
"""
This module provides logging facilities for Alignak:
- a main root logger for the running daemon
- a monitoring log logger

It defines a colored stream handler class to allow using colored log. Using this class is
as follows: alignak.log.ColorStreamHandler

It defines a CollectorHandler class that is used to easily capture the log events for the unit
tests.

It also defines a UTC time formatter usable as alignak.log.UTCFormatter

The setup_logger function initializes the daemon logger with the JSON provided configuration file.

The make_monitoring_log function emits a log to the monitoring log logger and returns a brok for
the Alignak broker.
"""
from __future__ import print_function

import os
import sys
import json
import time
import datetime
import logging
from logging import Handler, Formatter, StreamHandler
from logging.config import dictConfig as logger_dictConfig

from termcolor import cprint

from alignak.brok import Brok

# Default values for root logger
ALIGNAK_LOGGER_NAME = 'alignak'
ALIGNAK_LOGGER_LEVEL = logging.INFO

# Default values for monitoring logger
MONITORING_LOGGER_NAME = 'monitoring-log'


logger = logging.getLogger(ALIGNAK_LOGGER_NAME)  # pylint: disable=invalid-name
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
        except TypeError:  # pragma: no cover, simple protection
            self.handleError(record)


class ColorStreamHandler(StreamHandler):
    """
    This logging handler provides colored logs when logs are emitted to a tty.
    """
    def emit(self, record):
        colors = {'DEBUG': 'cyan', 'INFO': 'green',
                  'WARNING': 'yellow', 'CRITICAL': 'magenta', 'ERROR': 'red'}
        msg = self.format(record)
        try:
            if getattr(sys.stdout, 'isatty', False):
                cprint(msg, colors[record.levelname])
            else:
                print(msg)
        except UnicodeEncodeError:  # pragma: no cover, simple protection
            print(msg.encode('ascii', 'ignore'))
        except IOError:  # pragma: no cover, simple protection
            # May happen when process are closing
            pass
        except TypeError:  # pragma: no cover, simple protection
            self.handleError(record)


def setup_logger(logger_configuration_file, log_dir=None, process_name='', log_file=''):
    # pylint: disable=too-many-branches
    """
    Configure the provided logger
    - get and update the content of the Json configuration file
    - configure the logger with this file

    If a log_dir and process_name are provided, the format and filename in the configuration file
    are updated with the provided values if they contain the patterns %(logdir)s and %(daemon)s

    If no log_dir and process_name are provided, this function will truncate the log file
    defined in the configuration file.

    If a log file name is provided, it will override the default defined log file name.

    At first, this function checks if the logger is still existing and initialized to
    update the handlers and formatters. This mainly happens during the unit tests.

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
        if not process_name:
            break
        # Logger is already configured?
        if getattr(handler, '_name', None) == 'daemons':
            # Update the declared formats and file names with the process name
            # This is for unit tests purpose only: alignak_tests will be replaced
            # with the provided process name
            for hdlr in logger_.handlers:
                # print("- handler : %s (%s)" % (hdlr, hdlr.formatter._fmt))
                if 'alignak_tests' in hdlr.formatter._fmt:
                    formatter = logging.Formatter(hdlr.formatter._fmt.replace("alignak_tests",
                                                                              process_name))
                    hdlr.setFormatter(formatter)
                if getattr(hdlr, 'filename', None) and 'alignak_tests' in hdlr.filename:
                    hdlr.filename = hdlr.filename._fmt.replace("alignak_tests", process_name)
                #     print("- handler : %s (%s) -> %s" % (hdlr, hdlr.formatter._fmt,
                #                                          hdlr.filename))
                # else:
                #     print("- handler : %s (%s)" % (hdlr, hdlr.formatter._fmt))
            break
    else:
        if not logger_configuration_file or not os.path.exists(logger_configuration_file):
            print("The logger configuration file does not exist: %s" % logger_configuration_file)
            return

        with open(logger_configuration_file, 'rt') as _file:
            config = json.load(_file)
            truncate = False
            if not process_name and not log_dir:
                truncate = True
            if not process_name:
                process_name = 'alignak_tests'
            if not log_dir:
                log_dir = '/tmp'
            # Update the declared formats with the process name
            for formatter in config['formatters']:
                if 'format' not in config['formatters'][formatter]:
                    continue
                config['formatters'][formatter]['format'] = \
                    config['formatters'][formatter]['format'].replace("%(daemon)s", process_name)

            # Update the declared log file names with the log directory
            for hdlr in config['handlers']:
                if 'filename' not in config['handlers'][hdlr]:
                    continue
                if log_file and hdlr == 'daemons':
                    config['handlers'][hdlr]['filename'] = log_file
                else:
                    config['handlers'][hdlr]['filename'] = \
                        config['handlers'][hdlr]['filename'].replace("%(logdir)s", log_dir)
                config['handlers'][hdlr]['filename'] = \
                    config['handlers'][hdlr]['filename'].replace("%(daemon)s", process_name)
                if truncate and os.path.exists(config['handlers'][hdlr]['filename']):
                    with open(config['handlers'][hdlr]['filename'], "w") as file_log_file:
                        file_log_file.truncate()

        # Configure the logger, any error will raise an exception
        logger_dictConfig(config)


def set_log_console(log_level=logging.INFO):
    """Set the Alignak daemons logger have a console log handler.

    This is only used for the arbiter verify mode to add a console log handler.

    :param log_level: log level
    :return: n/a
    """
    # Change the logger and all its handlers log level
    logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
    logger_.setLevel(log_level)

    # Adding a console logger...
    csh = ColorStreamHandler(sys.stdout)
    csh.setFormatter(Formatter('[%(asctime)s] %(levelname)s: [%(name)s] %(message)s',
                               "%Y-%m-%d %H:%M:%S"))
    logger_.addHandler(csh)


def set_log_level(log_level=logging.INFO, handlers=None):
    """Set the Alignak logger log level. This is mainly used for the arbiter verify code to
    set the log level at INFO level whatever the configured log level is set.

    This is also used when changing the daemon log level thanks to the WS interface

    If an handlers name list is provided, all the handlers which name is in this list are
    concerned else only the `daemons` handler log level is changed.

    :param handlers: list of concerned handlers
    :type: list
    :param log_level: log level
    :return: n/a
    """
    # print("Setting log level: %s" % (log_level))
    # Change the logger and all its handlers log level
    logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
    logger_.setLevel(log_level)

    if handlers is not None:
        for handler in logger_.handlers:
            if getattr(handler, '_name', None) in handlers:
                handler.setLevel(log_level)


def get_log_level():
    """Get the Alignak logger log level. This is used when getting the daemon log level
    thanks to the WS interface

    :return: n/a
    """
    # Change the logger and all its handlers log level
    logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
    return logger_.log_level


def make_monitoring_log(level, message, timestamp=None, to_logger=False):
    """
    Function used to build the monitoring log.

    Emit a log message with the provided level to the monitoring log logger.
    Build a Brok typed as monitoring_log with the provided message

    When to_logger is True, the information is sent to the python logger, else a monitoring_log
    Brok is returned. The Brok is managed by the daemons to build an Event that will br logged
    by the Arbiter when it collects all the events.

    TODO: replace with dedicated brok for each event to log - really useful?

    :param level: log level as defined in logging
    :type level: str
    :param message: message to send to the monitoring log logger
    :type message: str
    :param to_logger: when set, send to the logger, else raise a brok
    :type to_logger: bool
    :param timestamp: if set, force the log event timestamp
    :return: a monitoring_log Brok
    :rtype: alignak.brok.Brok
    """
    level = level.lower()
    if level not in ['debug', 'info', 'warning', 'error', 'critical']:
        return False

    if to_logger:
        logging.getLogger(ALIGNAK_LOGGER_NAME).debug("Monitoring log: %s / %s", level, message)

        # Emit to our monitoring log logger
        message = message.replace('\r', '\\r')
        message = message.replace('\n', '\\n')
        logger_ = logging.getLogger(MONITORING_LOGGER_NAME)
        logging_function = getattr(logger_, level)
        try:
            message = message.decode('utf8', 'ignore')
        except UnicodeEncodeError:
            pass
        except AttributeError:
            # Python 3 raises an exception!
            pass

        if timestamp:
            st = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            logging_function(message, extra={'my_date': st})
        else:
            logging_function(message)

        return True

    # ... and returns a brok
    return Brok({'type': 'monitoring_log', 'data': {'level': level, 'message': message}})
