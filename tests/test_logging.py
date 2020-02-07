#!/usr/bin/env python
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

"""
Test alignak.logging
"""

import re
import time
import logging
import os.path
import pytest
from datetime import datetime

from logging import DEBUG, INFO, WARNING, Formatter
from alignak.log import setup_logger, set_log_level, set_log_console, ALIGNAK_LOGGER_NAME

from .alignak_test import AlignakTest, CollectorHandler


class TestLogging(AlignakTest):

    def setUp(self):
        super(TestLogging, self).setUp()

        # By default get alignak logger and setup to Info level and add collector
        self.logger = logging.getLogger(ALIGNAK_LOGGER_NAME)
        # Default is 3 handlers are available
        self.assertEqual(len(self.logger.handlers), 3)

        # Specific for unit tests ... else the log collector is not enabled at this level
        self.set_unit_tests_logger_level(logging.DEBUG)

    def test_default_logger_values(self):
        """ Test default logger values

        :return:
        """
        # Use a logger included in the default Alignak logger hierarchy
        test_logger = logging.getLogger("alignak.test.name")
        set_log_level(logging.WARNING)
        assert test_logger.parent == self.logger_

        test_logger.debug("Debug log")
        test_logger.info("Info log")
        test_logger.warning("Warning log")
        test_logger.error("Error log")
        test_logger.critical("Critical log")

        self.show_logs()

        self.assert_no_log_match(
            re.escape(u"Debug log")
        )
        self.assert_no_log_match(
            re.escape(u"Info log")
        )
        self.assert_any_log_match(
            re.escape(u"Warning log")
        )
        self.assert_any_log_match(
            re.escape(u"Error log")
        )
        self.assert_any_log_match(
            re.escape(u"Critical log")
        )
        self.show_logs()

    def test_change_level_and_get_msg(self):
        """ Test change log level

        :return:
        """
        # Use the default unit tests logger
        set_log_level(logging.DEBUG)
        self.clear_logs()
        self.logger_.debug("This message is emitted in DEBUG")
        self.assert_any_log_match("This message is emitted in DEBUG")

        set_log_level(logging.INFO)
        self.clear_logs()
        self.logger_.debug("This message will not be emitted")
        self.assert_no_log_match("This message will not be emitted")

        set_log_level(logging.WARNING)
        self.clear_logs()
        self.logger_.debug("This message will not be emitted")
        self.assert_no_log_match("This message will not be emitted")
        self.logger_.info("This message will not be emitted")
        self.assert_no_log_match("This message will not be emitted")

    def test_log_and_change_level(self):
        """ Test change log level 2

        :return:
        """
        # Use the default unit tests logger
        set_log_level(logging.INFO)
        self.logger_.info("This message will be collected")
        set_log_level(logging.WARNING)
        self.logger_.info("This message won't be collected")

        self.show_logs()

        self.assert_any_log_match("This message will be collected")
        self.assert_no_log_match("This message won't be collected")

    def test_log_utf8(self):
        """ Log as UTF8 format

        :return:
        """
        set_log_level(logging.INFO)

        # Some special characters
        # dollar, pound, currency, accented French
        self.logger.info(u"I love myself $£¤ éàçèùè")

        # A russian text
        self.logger.info(u"На берегу пустынных волн")

        # A chines text
        self.logger.info(u"新年快乐")

        self.show_logs()


class TestLogging2(AlignakTest):

    def setUp(self):
        print("No setup")

    def tearDown(self):
        print("No tear down")

    def test_set_console_existing(self):
        # Use the default unit tests logger
        logger_configuration_file = os.path.join(os.getcwd(), './etc/alignak-logger.json')
        print("Logger configuration file: %s" % logger_configuration_file)
        self._set_console_log(logger_configuration_file)

    def test_set_console(self):
        # Use the no console unit tests logger
        logger_configuration_file = os.path.join(os.getcwd(),
                                                 './etc/no_console_alignak-logger.json')
        print("Logger configuration file: %s" % logger_configuration_file)
        self._set_console_log(logger_configuration_file)

    def _set_console_log(self, logger_configuration_file):
        """Set console logger for Alignak arbiter verify mode"""
        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for hdlr in logger_.handlers:
            if getattr(hdlr, 'filename', None):
                print("- handler : %s - %s (%s) -> %s" % (hdlr.level, hdlr, hdlr.formatter._fmt,
                                                          hdlr.filename))
            else:
                print("- handler : %s - %s (%s)" % (hdlr.level, hdlr, hdlr.formatter._fmt))

        print("--///--")

        setup_logger(logger_configuration_file, log_dir=None, process_name='', log_file='')
        self.logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        set_log_level(logging.INFO)

        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for hdlr in logger_.handlers:
            if getattr(hdlr, 'filename', None):
                print("- handler : %s - %s (%s) -> %s" % (hdlr.level, hdlr, hdlr.formatter._fmt,
                                                          hdlr.filename))
            else:
                print("- handler : %s - %s (%s)" % (hdlr.level, hdlr, hdlr.formatter._fmt))

        # Log message
        self.logger_.info("Message")
        self.show_logs()

        set_log_console(logging.WARNING)

        # Log message
        self.logger_.info("Message")
        self.show_logs()

        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for hdlr in logger_.handlers:
            if getattr(hdlr, 'filename', None):
                print("- handler : %s - %s (%s) -> %s" % (hdlr.level, hdlr, hdlr.formatter._fmt,
                                                          hdlr.filename))
            else:
                print("- handler : %s - %s (%s)" % (hdlr.level, hdlr, hdlr.formatter._fmt))


class TestLogging3(AlignakTest):

    def setUp(self):
        # Clear logs and reset the logger
        self.clear_logs()
        # Remove all existing handlers (if some!)
        # Former existing configuration
        self.logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        self.logger_.handlers = []

    def tearDown(self):
        print("No tear down")

    def test_log_format(self):
        """ Log string format

        :return:
        """
        # Use the default unit tests logger
        # Configure the logger with a daemon name

        # Former existing configuration
        self.logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        assert not self.logger_.handlers

        logger_configuration_file = os.path.join(os.getcwd(), './etc/alignak-logger.json')
        setup_logger(logger_configuration_file, log_dir=None,
                     process_name='process_name', log_file='')

        # Newly configured configuration
        self.logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        print("Logger new handlers:")
        for handler in self.logger_.handlers:
            print("- handler %s: %s (%s)"
                  % (getattr(handler, '_name', None), handler, handler.formatter._fmt))

        set_log_level(logging.INFO)
        msg = "Message"
        self.logger_.info(msg)
        self.show_logs()
        # The logger default format is including 'alignak_tests.'
        # Now the get process_name in place of alignak_tests!
        # [2020-01-26 09:48:38] INFO: [process_name.alignak] Message
        self.assert_any_log_match('[\[0-9\]*] INFO: \[process_name.%s\] %s'
                                  % (self.logger_.name, msg))

        # Configure the logger with a daemon name
        logger_configuration_file = os.path.join(os.getcwd(), './etc/alignak-logger.json')
        setup_logger(logger_configuration_file, log_dir=None,
                     process_name='process_name', log_file='')
        self.logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)

        print("Logger configuration: ")
        logger_ = logging.getLogger(ALIGNAK_LOGGER_NAME)
        for hdlr in logger_.handlers:
            if getattr(hdlr, 'filename', None) and 'alignak_tests' in hdlr.filename:
                print("- handler : %s (%s) -> %s" % (hdlr, hdlr.formatter._fmt, hdlr.filename))
            else:
                print("- handler : %s (%s)" % (hdlr, hdlr.formatter._fmt))

        set_log_level(logging.INFO)
        msg2 = "Message 2"
        self.logger_.info(msg2)
        self.show_logs()
        # The logger default format is including 'alignak_tests.'
        # Now the get process_name in place of alignak_tests!
        self.assert_any_log_match('[\[0-9\]*] INFO: \[process_name.%s\] %s'
                                  % (self.logger_.name, msg))
        self.assert_any_log_match('[\[0-9\]*] INFO: \[process_name.%s\] %s'
                                  % (self.logger_.name, msg2))
