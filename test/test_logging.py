#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016: Alignak team, see AUTHORS.txt file for contributors
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
#  Copyright (C) 2012:
#     Hartmut Goebel <h.goebel@crazy-compilers.com>
#

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
Test alignak.logging
"""

import time
import logging
import os.path
import pytest
from datetime import datetime

from logging import DEBUG, INFO, WARNING, Formatter
from alignak.log import setup_logger

from alignak_test import AlignakTest, CollectorHandler


class TestLogging(AlignakTest):

    def setUp(self):
        # By default get alignak logger and setup to Info level and add collector
        self.logger = logging.getLogger("alignak")
        self.logger.handlers = []

        # Add collector for test purpose.
        collector_h = CollectorHandler()
        collector_h.setFormatter(Formatter('[%(created)i] %(levelname)s: [%(name)s] %(message)s'))
        self.logger.addHandler(collector_h)
        self.assertEqual(len(self.logger.handlers), 1)

        self.logger.setLevel(INFO)

    def test_default_logger_values(self):
        """ Test default logger values

        :return:
        """
        assert self.logger.level == INFO
        assert self.logger.name == "alignak"
        test_logger = logging.getLogger("alignak.test.name")
        assert test_logger.parent is not None
        assert test_logger.parent == self.logger

    def test_drop_low_level_msg(self):
        """ Drop low level messages

        :return:
        """
        self.logger.debug("This message will not be emitted")
        self.assert_no_log_match("This message will not be emitted")

    def test_change_level_and_get_msg(self):
        """ Test change log level

        :return:
        """
        self.logger.setLevel(DEBUG)
        self.logger.debug("This message is emitted in DEBUG")
        self.assert_any_log_match("This message is emitted in DEBUG")

    def test_log_and_change_level(self):
        """ Test change log level 2

        :return:
        """
        self.logger.info("This message will be collected")
        self.logger.setLevel(WARNING)
        self.logger.info("This message won't be collected")
        self.assert_any_log_match("This message will be collected")
        self.assert_no_log_match("This message won't be collected")

    @pytest.mark.skip("Deprecated - new logger configuration")
    def test_log_config_console(self):
        """ Default logger setup updates root logger and adds a console handler

        :return:
        """
        # No console handler
        my_logger = setup_logger(None, log_console=False)
        assert my_logger == self.logger
        assert my_logger.level == INFO
        assert my_logger.name == "alignak"
        assert len(my_logger.handlers) == 1

        # With console handler
        my_logger = setup_logger(None)
        assert my_logger == self.logger
        assert my_logger.level == INFO
        assert my_logger.name == "alignak"
        assert len(my_logger.handlers) == 2

        # Only append one console handler but update the logger level if required
        my_logger = setup_logger(None, level=DEBUG)
        assert my_logger.level == DEBUG
        assert len(my_logger.handlers) == 2
        # Back to INFO (default level value)
        my_logger = setup_logger(None, log_console=True)
        assert my_logger.level == INFO
        assert len(my_logger.handlers) == 2

        msg = "test message"
        self.logger.info(msg)
        self.assert_any_log_match('[\[0-9\]*] INFO: \[%s\] %s' % (self.logger.name, msg))

    @pytest.mark.skip("Deprecated - new logger configuration")
    def test_log_config_human_date(self):
        """ Default logger setup uses a timestamp date format, a human date can be used instead

        :return:
        """
        # With console handler and human date
        my_logger = setup_logger(None, human_log=True, human_date_format=u'%Y-%m-%d %H:%M:%S')
        assert my_logger == self.logger
        assert my_logger.level == INFO
        assert my_logger.name == "alignak"
        assert len(my_logger.handlers) == 2

    @pytest.mark.skip("Deprecated - new logger configuration")
    def test_log_config_file(self):
        """ Logger setup allows to update alignak root logger with a timed rotating file handler

        :return:
        """
        my_logger = setup_logger(None, log_file='./test.log')
        assert my_logger == self.logger
        assert my_logger.level == INFO
        assert my_logger.name == "alignak"
        assert len(my_logger.handlers) == 3
        assert os.path.exists('./test.log')

        # Only append one file handler if file used is the same
        my_logger = setup_logger(None, log_file='./test.log')
        assert my_logger == self.logger
        assert my_logger.level == INFO
        assert my_logger.name == "alignak"
        assert len(my_logger.handlers) == 3

        # Only append one file handler if file used is the same
        my_logger = setup_logger(None, log_file=os.path.abspath('./test.log'))
        assert len(my_logger.handlers) == 3

        # Only append one file handler if file used is the same
        my_logger = setup_logger(None, log_file=os.path.abspath('./test2.log'))
        assert len(my_logger.handlers) == 4
        assert os.path.exists('./test2.log')

    def test_log_utf8(self):
        """ Log as UTF8 format

        :return:
        """
        stuff = 'h\351h\351'  # Latin Small Letter E with acute in Latin-1
        self.logger.info(stuff)
        sutf8 = u'I love myself $£¤'  # dollar, pound, currency
        self.logger.info(sutf8)
        s = unichr(40960) + u'abcd' + unichr(1972)
        self.logger.info(s)

    def test_log_format(self):
        """ Log string format

        :return:
        """
        msg = "Message"
        self.logger.info(msg)
        self.assert_any_log_match('[\[0-9\]*] INFO: \[%s\] %s' % (self.logger.name, msg))
