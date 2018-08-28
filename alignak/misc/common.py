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
"""
This module is used for common variables in Alignak.
Previously some of those variables were linked to a specific class which made no sense.
"""
import signal
from collections import namedtuple

try:
    from setproctitle import setproctitle  # pylint: disable=unused-import
except ImportError as err:  # pragma: no cover, setproctitle is in the requirements.txt
    def setproctitle(title):
        """
        Return the name of the process
        :param title: name of process
        :type title: str
        :return: None
        """
        # Do nothing...
        return title

# Friendly names for the system signals
SIGNALS_TO_NAMES_DICT = dict((k, v) for v, k in reversed(sorted(signal.__dict__.items()))
                             if v.startswith('SIG') and not v.startswith('SIG_'))

ModAttr = namedtuple('ModAttr', ['modattr', 'attribute', 'value'])

DICT_MODATTR = {
    "MODATTR_NONE": ModAttr("MODATTR_NONE", "", 0),
    "MODATTR_NOTIFICATIONS_ENABLED":
        ModAttr("MODATTR_NOTIFICATIONS_ENABLED", "notifications_enabled", 1),
    "notifications_enabled": ModAttr("MODATTR_NOTIFICATIONS_ENABLED", "notifications_enabled", 1),
    "MODATTR_ACTIVE_CHECKS_ENABLED":
        ModAttr("MODATTR_ACTIVE_CHECKS_ENABLED", "active_checks_enabled", 2),
    "active_checks_enabled": ModAttr("MODATTR_ACTIVE_CHECKS_ENABLED", "active_checks_enabled", 2),
    "MODATTR_PASSIVE_CHECKS_ENABLED":
        ModAttr("MODATTR_PASSIVE_CHECKS_ENABLED", "passive_checks_enabled", 4),
    "passive_checks_enabled":
        ModAttr("MODATTR_PASSIVE_CHECKS_ENABLED", "passive_checks_enabled", 4),
    "MODATTR_EVENT_HANDLER_ENABLED":
        ModAttr("MODATTR_EVENT_HANDLER_ENABLED", "event_handler_enabled", 8),
    "event_handler_enabled": ModAttr("MODATTR_EVENT_HANDLER_ENABLED", "event_handler_enabled", 8),
    "MODATTR_FLAP_DETECTION_ENABLED":
        ModAttr("MODATTR_FLAP_DETECTION_ENABLED", "flap_detection_enabled", 16),
    "flap_detection_enabled":
        ModAttr("MODATTR_FLAP_DETECTION_ENABLED", "flap_detection_enabled", 16),
    "MODATTR_PERFORMANCE_DATA_ENABLED":
        ModAttr("MODATTR_PERFORMANCE_DATA_ENABLED", "process_performance_data", 64),
    "process_performance_data":
        ModAttr("MODATTR_PERFORMANCE_DATA_ENABLED", "process_performance_data", 64),
    "MODATTR_EVENT_HANDLER_COMMAND": ModAttr("MODATTR_EVENT_HANDLER_COMMAND", "event_handler", 256),
    "event_handler": ModAttr("MODATTR_EVENT_HANDLER_COMMAND", "event_handler", 256),
    "MODATTR_CHECK_COMMAND": ModAttr("MODATTR_CHECK_COMMAND", "check_command", 512),
    "check_command": ModAttr("MODATTR_CHECK_COMMAND", "check_command", 512),
    "MODATTR_NORMAL_CHECK_INTERVAL":
        ModAttr("MODATTR_NORMAL_CHECK_INTERVAL", "check_interval", 1024),
    "check_interval": ModAttr("MODATTR_NORMAL_CHECK_INTERVAL", "check_interval", 1024),
    "MODATTR_RETRY_CHECK_INTERVAL": ModAttr("MODATTR_RETRY_CHECK_INTERVAL", "retry_interval", 2048),
    "retry_interval": ModAttr("MODATTR_RETRY_CHECK_INTERVAL", "retry_interval", 2048),
    "MODATTR_MAX_CHECK_ATTEMPTS": ModAttr("MODATTR_MAX_CHECK_ATTEMPTS", "max_check_attempts", 4096),
    "max_check_attempts": ModAttr("MODATTR_MAX_CHECK_ATTEMPTS", "max_check_attempts", 4096),
    "MODATTR_FRESHNESS_CHECKS_ENABLED":
        ModAttr("MODATTR_FRESHNESS_CHECKS_ENABLED", "check_freshness", 8192),
    "check_freshness": ModAttr("MODATTR_FRESHNESS_CHECKS_ENABLED", "check_freshness", 8192),
    "MODATTR_CHECK_TIMEPERIOD": ModAttr("MODATTR_CHECK_TIMEPERIOD", "check_period", 16384),
    "check_period": ModAttr("MODATTR_CHECK_TIMEPERIOD", "check_period", 16384),
    "MODATTR_CUSTOM_VARIABLE": ModAttr("MODATTR_CUSTOM_VARIABLE", "customs", 32768),
    "custom_variable": ModAttr("MODATTR_CUSTOM_VARIABLE", "customs", 32768),
    "MODATTR_NOTIFICATION_TIMEPERIOD":
        ModAttr("MODATTR_NOTIFICATION_TIMEPERIOD", "notification_period", 65536),
    "notification_period": ModAttr("MODATTR_NOTIFICATION_TIMEPERIOD", "notification_period", 65536),

}
