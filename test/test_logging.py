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
import unittest
import alignak.log

from logging import DEBUG, INFO, WARNING
from alignak.log import naglog_result, HUMAN_TIMESTAMP_LOG

from alignak_test import AlignakTest, CollectorHandler


class TestLogging(AlignakTest):

    def setUp(self):
        # By default get alignak logger and setup to Info level and add collector
        self.logger = logging.getLogger("alignak")
        # Add collector for test purpose.
        collector_h = CollectorHandler()
        collector_h.setFormatter(self.logger.handlers[0].formatter)  # Need to copy format
        self.logger.addHandler(collector_h)
        self.logger.setLevel('INFO')

    def test_setting_and_unsetting_human_timestamp_format(self):
        # :hack: alignak.log.human_timestamp_log is a global variable
        self.assertEqual(alignak.log.HUMAN_TIMESTAMP_LOG, False)
        self.logger.set_human_format(True)
        self.assertEqual(alignak.log.HUMAN_TIMESTAMP_LOG, True)
        self.logger.set_human_format(False)
        self.assertEqual(alignak.log.HUMAN_TIMESTAMP_LOG, False)
        self.logger.set_human_format(True)
        self.assertEqual(alignak.log.HUMAN_TIMESTAMP_LOG, True)

    def test_default_logger_values(self):
        self.assertEqual(self.logger.level, INFO)
        self.assertEqual(self.logger.name, "alignak")
        test_logger = logging.getLogger("alignak.test.name")
        self.assertIsNotNone(test_logger.parent)
        self.assertEqual(test_logger.parent, self.logger)

    def test_drop_low_level_msg(self):
        self.logger.debug("This message will not be emitted")
        self.assert_no_log_match("This message will not be emitted")

    def test_change_level_and_get_msg(self):
        self.logger.setLevel(DEBUG)
        self.logger.debug("This message is emitted in DEBUG")
        self.assert_any_log_match("This message is emitted in DEBUG")

    def test_log_and_change_level(self):
        self.logger.info("This message will be collected")
        self.logger.setLevel(WARNING)
        self.logger.info("This message won't be collected")
        self.assert_any_log_match("This message will be collected")
        self.assert_no_log_match("This message won't be collected")

    def test_log_format(self):
        msg = "Message"
        self.logger.info(msg)
        self.assert_any_log_match('[\[0-9\]*] INFO: \[%s\] %s' % (self.logger.name, msg))
        naglog_result("info", msg)
        self.assert_any_log_match('\[[0-9]*\] %s' % msg)
        naglog_result("info", msg + "2")
        self.assert_no_log_match('\[[0-9]*\] INFO: \[%s\] %s2' % (self.logger.name, msg))
        self.logger.set_human_format(True)
        self.logger.info(msg + "3")
        logs = self.get_log_match('\[.*\] INFO: \[%s\] %s3' % (self.logger.name, msg))
        human_time = logs[0].split(']')[0][1:]
        # Will raise a ValueError if strptime fails
        self.assertIsNotNone(time.strptime(human_time, '%a %b %d %H:%M:%S %Y'))
        self.logger.set_human_format(False)

if __name__ == '__main__':
    unittest.main()
