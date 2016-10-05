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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Guillaume Bour, guillaume@bour.cc
#     xkilian, fmikus@acktomic.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Zoran Zaric, zz@zoranzaric.de
#     Jan Ulferts, jan.ulferts@xing.com
#     Grégory Starck, g.starck@gmail.com
#     Frédéric Pégé, frederic.pege@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Olivier Hanesse, olivier.hanesse@gmail.com
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
"""
This module provides logging facilities for Alignak.
There is a custom log handler that creates broks for every log emitted with level < debug
"""
import logging
import sys
import os
import stat
from logging import Handler, Formatter, StreamHandler, NOTSET, FileHandler  # pylint: disable=C0412
from logging.handlers import TimedRotatingFileHandler  # pylint: disable=C0412

from termcolor import cprint


HUMAN_TIMESTAMP_LOG = False

# Default UTC date formatting is: '%a, %d %b %Y %H:%M:%S %Z'
HUMAN_TIMESTAMP_FORMAT = '%a, %d %b %Y %H:%M:%S %Z'
# Former date formatting was: '%a %b %d %H:%M:%S %Y'
# HUMAN_TIMESTAMP_FORMAT = '%a %b %d %H:%M:%S %Y'

# Default log formatter (no human timestamp)
DEFAULT_FORMATTER = Formatter('[%(created)i] %(levelname)s: %(message)s')
DEFAULT_FORMATTER_NAMED = Formatter('[%(created)i] %(levelname)s: [%(name)s] %(message)s')

# Human timestamped log formatter
HUMAN_FORMATTER = Formatter('[%(asctime)s] %(levelname)s: %(message)s', HUMAN_TIMESTAMP_FORMAT)
HUMAN_FORMATTER_NAMED = Formatter('[%(asctime)s] %(levelname)s: [%(name)s] %(message)s',
                                  HUMAN_TIMESTAMP_FORMAT)

# Nagios log formatter
NAGIOS_FORMATTER = Formatter('[%(created)i] %(message)s')

# Time rotation for file logger
ROTATION_WHEN = 'midnight'
ROTATION_INTERVAL = 1
ROTATION_COUNT = 5

# Use a global log stack to store logs emitted before the logger get fully configured
LOG_STACK = []


class BrokHandler(Handler):
    """
    This log handler is forwarding log messages as broks to the broker.

    Only messages of level higher than DEBUG are send to other
    satellite to not risk overloading them.
    """

    def __init__(self, broker):
        # Only messages of level INFO or higher are passed on to the
        # broker. Other handlers have a different level.
        Handler.__init__(self, logging.INFO)
        self._broker = broker

    def emit(self, record):
        try:
            msg = self.format(record)
            # Needed otherwise import loop (log -> brok -> serialization)
            from alignak.brok import Brok
            brok = Brok({'type': 'log', 'data': {'log': msg + '\n'}})
            self._broker.add(brok)
        except TypeError:
            self.handleError(record)


class ColorStreamHandler(StreamHandler):
    """
    This log handler provides colored logs when logs are emitted to a tty.
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            colors = {'DEBUG': 'cyan', 'INFO': 'magenta',
                      'WARNING': 'yellow', 'CRITICAL': 'magenta', 'ERROR': 'red'}
            cprint(msg, colors[record.levelname])
        except UnicodeEncodeError:
            print msg.encode('ascii', 'ignore')
        except TypeError:
            self.handleError(record)


class Log(logging.Logger):
    """
    Alignak logger class, wrapping access to Python logging standard library.
    See : https://docs.python.org/2/howto/logging.html#logging-flow for more detail about
    how log are handled"""

    def __init__(self, name="Alignak", level=NOTSET, log_set=False):
        logging.Logger.__init__(self, name, level)
        self.log_set = log_set

    def setLevel(self, level):
        """ Set level of logger and handlers.
        The logger need the lowest level (see link above)

        :param level: logger/handler level
        :type level: int
        :return: None
        """
        if not isinstance(level, int):
            level = getattr(logging, level, None)
            if not level or not isinstance(level, int):
                raise TypeError('log level must be an integer')
        # Not very useful, all we have to do is no to set the level > info for the brok handler
        self.level = min(level, logging.INFO)
        # Only set level to file and/or console handler
        for handler in self.handlers:
            if isinstance(handler, BrokHandler):
                continue
            handler.setLevel(level)

    def load_obj(self, obj, name_=None):
        """ We load the object where we will put log broks
        with the 'add' method

        :param obj: object instance
        :type obj: object
        :param name_: name of object
        :type name_: str | None
        :return: None
        """
        __brokhandler__ = BrokHandler(obj)
        if name_ is not None or self.name is not None:
            if name_ is not None:
                self.name = name_
            # We need to set the same format than all other handlers
            for handler in self.handlers:
                handler.setFormatter(DEFAULT_FORMATTER_NAMED)
            __brokhandler__.setFormatter(DEFAULT_FORMATTER_NAMED)
        else:
            __brokhandler__.setFormatter(DEFAULT_FORMATTER)
        self.addHandler(__brokhandler__)

    def register_local_log(self, path, level=None, purge_buffer=True):
        """The alignak logging wrapper can write to a local file if needed
        and return the file descriptor so we can avoid to
        close it.

        Add logging to a local log-file.

        The file will be rotated once a day

        :param path: path of log
        :type path: str
        :param level: level of log
        :type level: None | int
        :param purge_buffer: True if want purge the buffer, otherwise False
        :type purge_buffer: bool
        :return:
        """
        # Apply the human timestamp to this newly created handler
        global HUMAN_TIMESTAMP_LOG  # pylint: disable=W0602

        self.log_set = True
        # Todo : Create a config var for backup count
        if os.path.exists(path) and not stat.S_ISREG(os.stat(path).st_mode):
            # We don't have a regular file here. Rotate may fail
            # It can be one of the stat.S_IS* (FIFO? CHR?)
            handler = FileHandler(path)
        else:
            handler = TimedRotatingFileHandler(path,  # pylint: disable=R0204
                                               when=ROTATION_WHEN,
                                               interval=ROTATION_INTERVAL,
                                               backupCount=ROTATION_COUNT)
        if level is not None:
            if not isinstance(level, int):
                level = getattr(logging, level, None)
            handler.setLevel(level)
        if self.name is not None:
            handler.setFormatter(HUMAN_TIMESTAMP_LOG and
                                 HUMAN_FORMATTER_NAMED or DEFAULT_FORMATTER_NAMED)
        else:
            handler.setFormatter(HUMAN_TIMESTAMP_LOG and
                                 HUMAN_FORMATTER or DEFAULT_FORMATTER)

        self.addHandler(handler)

        # Ok now unstack all previous logs
        if purge_buffer:
            self._destack()

        # Todo : Do we need this now we use logging?
        return handler.stream.fileno()

    def set_human_format(self, human=True):
        """
        Set the output as human format.

        If the optional parameter `human` is False, the timestamps format
        will be reset to the default format.

        :param human: True if want timestamp in human format, otherwise False
        :type human: bool
        :return: None
        """
        global HUMAN_TIMESTAMP_LOG  # pylint: disable=W0603
        HUMAN_TIMESTAMP_LOG = bool(human)

        # Apply/Remove the human format to all handlers except the brok one.
        for handler in self.handlers:
            if isinstance(handler, BrokHandler):
                continue

            if self.name is not None:
                handler.setFormatter(HUMAN_TIMESTAMP_LOG and
                                     HUMAN_FORMATTER_NAMED or DEFAULT_FORMATTER_NAMED)
            else:
                handler.setFormatter(HUMAN_TIMESTAMP_LOG and
                                     HUMAN_FORMATTER or DEFAULT_FORMATTER)

    def _stack(self, level, args, kwargs):
        """
        Stack logs until we open a log file so we will be able to flush them
        Stack max 500 logs (no memory leak please...)

        :param level: level log
        :type level: int
        :param args: arguments
        :type args:
        :param kwargs:
        :type kwargs:
        :return: None
        """
        if self.log_set:
            return

        global LOG_STACK  # pylint: disable=W0602,W0603
        LOG_STACK.append((level, args, kwargs))
        if len(LOG_STACK) > 500:
            LOG_STACK = LOG_STACK[2:]

    def _destack(self):
        """
        DIRTY HACK : log should be always written to a file.
        we are opening a log file, flush all the logs now

        :return: None
        """
        global LOG_STACK  # pylint: disable=W0602,W0603

        logger.debug("Begin - Dump stored logs")
        for (level, args, kwargs) in LOG_STACK:
            fun = getattr(logging.Logger, level, None)
            if fun is None:
                self.warning('Missing level for a log? %s', level)
                continue
            fun(self, *args, **kwargs)
        LOG_STACK = []
        logger.debug("End - Dump stored logs")

    def debug(self, *args, **kwargs):
        self._stack('debug', args, kwargs)
        logging.Logger.debug(self, *args, **kwargs)

    def info(self, *args, **kwargs):
        self._stack('info', args, kwargs)
        logging.Logger.info(self, *args, **kwargs)

    def warning(self, *args, **kwargs):
        self._stack('warning', args, kwargs)
        logging.Logger.warning(self, *args, **kwargs)

    def error(self, *args, **kwargs):
        self._stack('error', args, kwargs)
        logging.Logger.error(self, *args, **kwargs)


# --- create the main logger ---
logging.setLoggerClass(Log)
# pylint: disable=C0103
logger = logging.getLogger('alignak')  # pylint: disable=C0103
if hasattr(sys.stdout, 'isatty'):
    CSH = ColorStreamHandler(sys.stdout)
    if logger.name is not None:
        CSH.setFormatter(DEFAULT_FORMATTER_NAMED)
    else:
        CSH.setFormatter(DEFAULT_FORMATTER)
    logger.addHandler(CSH)


def naglog_result(level, result):
    """
    Function used for Nagios compatibility. We set the format properly for this call only.

    Dirty Hack to keep the old format, we should have another logger and
    use one for Alignak logs and another for monitoring data
    """
    prev_formatters = []
    for handler in logger.handlers:
        prev_formatters.append(handler.formatter)
        handler.setFormatter(NAGIOS_FORMATTER)

    log_fun = getattr(logger, level)

    if log_fun:
        log_fun(result)

    for index, handler in enumerate(logger.handlers):
        handler.setFormatter(prev_formatters[index])
