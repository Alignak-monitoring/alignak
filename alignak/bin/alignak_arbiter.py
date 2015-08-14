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

"""
This is the class of the Arbiter. Its role is to read configuration,
cut it, and send it to other elements like schedulers, reactionners
or pollers. It is also responsible for the high avaibility feature.
For example, if a scheduler dies, it sends the late scheduler's conf
to another scheduler available.
It also reads orders form users (nagios.cmd) and sends them to schedulers.
"""

import os
import sys
import optparse


# We try to raise up recursion limit on
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


from alignak import __version__
from alignak.daemons.arbiterdaemon import Arbiter


def main():
    """Parse args and run main daemon function

    :return: None
    """
    parser = optparse.OptionParser(
        "%prog [options] -c configfile [-c additional_config_file]",
        version="%prog: " + __version__)
    parser.add_option('-c', '--config', action='append',
                      dest="config_files", metavar="CONFIG-FILE",
                      help=('Config file (your nagios.cfg). Multiple -c can be '
                            'used, it will be like if all files was just one'))
    parser.add_option('-d', '--daemon', action='store_true',
                      dest="is_daemon",
                      help="Run in daemon mode")
    parser.add_option('-r', '--replace', action='store_true',
                      dest="do_replace",
                      help="Replace previous running arbiter")
    parser.add_option('--debugfile', dest='debug_file',
                      help=("Debug file. Default: not used "
                            "(why debug a bug free program? :) )"))
    parser.add_option("-v", "--verify-config",
                      dest="verify_only", action="store_true",
                      help="Verify config file and exit")
    parser.add_option("-p", "--profile",
                      dest="profile",
                      help="Dump a profile file. Need the python cProfile librairy")
    parser.add_option("-a", "--analyse",
                      dest="analyse",
                      help="Dump an analyse statistics file, for support")
    parser.add_option("-m", "--migrate",
                      dest="migrate",
                      help="Migrate the raw configuration read from the arbiter to another "
                           "module. --> VERY EXPERIMENTAL!")
    parser.add_option("-n", "--name",
                      dest="arb_name",
                      help="Give the arbiter name to use. Optionnal, will use the hostaddress "
                           "if not provide to find it.")

    opts, args = parser.parse_args()

    if not opts.config_files:
        parser.error("Requires at least one config file (option -c/--config")
    if args:
        parser.error("Does not accept any argument. Use option -c/--config")

    # Protect for windows multiprocessing that will RELAUNCH all
    daemon = Arbiter(debug=opts.debug_file is not None, **opts.__dict__)
    if not opts.profile:
        daemon.main()
    else:
        # For perf tuning:
        import cProfile
        cProfile.run('''daemon.main()''', opts.profile)


if __name__ == '__main__':
    main()
