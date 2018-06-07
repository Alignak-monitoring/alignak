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
#
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Nicolas Dupeux, nicolas@dupeux.net

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

# For the Alignak application, I try to respect
# The Zen of Python, by Tim Peters. It's just some
# very goods ideas that make Python programming very fun
# and efficient. If it's good for Python, it must be good for
# Alignak. :)
#
#
#
# Beautiful is better than ugly.
# Explicit is better than implicit.
# Simple is better than complex.
# Complex is better than complicated.
# Flat is better than nested.
# Sparse is better than dense.
# Readability counts.
# Special cases aren't special enough to break the rules.
# Although practicality beats purity.
# Errors should never pass silently.
# Unless explicitly silenced.
# In the face of ambiguity, refuse the temptation to guess.
# There should be one-- and preferably only one --obvious way to do it.
# Although that way may not be obvious at first unless you're Dutch.
# Now is better than never.
# Although never is often better than *right* now.
# If the implementation is hard to explain, it's a bad idea.
# If the implementation is easy to explain, it may be a good idea.
# Namespaces are one honking great idea -- let's do more of those!

"""
 This class is the application in charge of scheduling
 The scheduler listens to the Arbiter for the configuration sent through
 the given port as first argument.
 The configuration sent by the arbiter specifies which checks and actions
 the scheduler must schedule, and a list of reactionners and pollers
 to execute them
 When the scheduler is already launched and has its own conf, it keeps on
 listening the arbiter
 In case the arbiter has a new conf to send, the scheduler is stopped
 and a new one is created.
"""

import sys
import traceback

from alignak.daemons.schedulerdaemon import Alignak
from alignak.util import parse_daemon_args


def main():
    """Parse args and run main daemon function

    :return: None
    """
    try:
        args = parse_daemon_args()
        daemon = Alignak(**args.__dict__)
        daemon.main()
    except Exception as exp:  # pylint: disable=broad-except
        sys.stderr.write("*** Daemon exited because: %s" % str(exp))
        traceback.print_exc()
        exit(1)


if __name__ == '__main__':
    main()
