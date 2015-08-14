#!/usr/bin/env python
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
 listening the arbiter (one a timeout)
 In case the arbiter has a new conf to send, the scheduler is stopped
 and a new one is created.
"""
import os
import sys
import optparse


# We try to raise up recusion limit on
# but we don't have resource module on windows
if os.name != 'nt':
    import resource
    # All the pickle will ask for a lot of recursion, so we must make
    # sure to set it at a high value. The maximum recursion depth depends
    # on the Python version and the process limit "stack size".
    # The factors used were acquired by testing a broad range of installations
    STACKSIZE_SOFT, _ = resource.getrlimit(3)
    if sys.version_info < (3,):
        sys.setrecursionlimit(int(STACKSIZE_SOFT * 1.9 + 3200))
    else:
        sys.setrecursionlimit(int(STACKSIZE_SOFT * 2.4 + 3200))


from alignak.daemons.schedulerdaemon import Alignak
from alignak import __version__


def main():
    """Parse args and run main daemon function

    :return: None
    """
    parser = optparse.OptionParser(
        "%prog [options]", version="%prog " + __version__)
    parser.add_option('-c', '--config',
                      dest="config_file", metavar="INI-CONFIG-FILE",
                      help='Config file')
    parser.add_option('-d', '--daemon', action='store_true',
                      dest="is_daemon",
                      help="Run in daemon mode")
    parser.add_option('-r', '--replace', action='store_true',
                      dest="do_replace",
                      help="Replace previous running scheduler")
    parser.add_option('--debugfile', dest='debug_file',
                      help=("Debug file. Default: not used "
                            "(why debug a bug free program? :) )"))
    parser.add_option("-p", "--profile",
                      dest="profile",
                      help="Dump a profile file. Need the python cProfile librairy")

    opts, args = parser.parse_args()
    if args:
        parser.error("Does not accept any argument.")

    daemon = Alignak(debug=opts.debug_file is not None, **opts.__dict__)
    if not opts.profile:
        daemon.main()
    else:
        # For perf running:
        import cProfile
        cProfile.run('''daemon.main()''', opts.profile)


if __name__ == '__main__':
    main()
