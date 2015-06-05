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

'''
 This class is the application that launches checks
 The poller listens to the Arbiter for the configuration sent through
 the given port as first argument.
 The configuration sent by the arbiter specifies from which schedulers the
 poller will take its checks.
 When the poller is already launched and has its own conf, it keeps on
 listening the arbiter (one a timeout)
 In case the arbiter has a new conf to send, the poller forget its old
 schedulers (and the associated checks) and take the new ones instead.
'''

import sys
import os
import optparse

try:
    from alignak.bin import VERSION
    import alignak
except ImportError:
    # If importing alignak fails, try to load from current directory
    # or parent directory to support running without installation.
    # Submodules will then be loaded from there, too.
    import imp
    imp.load_module('alignak',
                    *imp.find_module('alignak',
                                     [os.path.realpath("."),
                                      os.path.realpath(".."),
                                      os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])),
                                                   "..")]))
    import alignak
    # Ok we should add the alignak root directory to our sys.path so our sons
    # will be able to use the alignak import without problems
    alignak_root_path = os.path.dirname(os.path.dirname(alignak.__file__))
    os.environ['PYTHONPATH'] = os.path.join(os.environ.get('PYTHONPATH', ''), alignak_root_path)


from alignak.daemons.pollerdaemon import Poller
from alignak.bin import VERSION


# Protect for windows multiprocessing that will RELAUNCH all
def main():
    parser = optparse.OptionParser(
        "%prog [options]", version="%prog " + VERSION)
    parser.add_option('-c', '--config',
                      dest="config_file", metavar="INI-CONFIG-FILE",
                      help='Config file')
    parser.add_option('-d', '--daemon', action='store_true',
                      dest="is_daemon",
                      help="Run in daemon mode")
    parser.add_option('-r', '--replace', action='store_true',
                      dest="do_replace",
                      help="Replace previous running poller")
    parser.add_option('--debugfile', dest='debug_file',
                      help=("Debug file. Default: not used "
                            "(why debug a bug free program? :) )"))
    parser.add_option("-p", "--profile",
                      dest="profile",
                      help="Dump a profile file. Need the python cProfile librairy")

    opts, args = parser.parse_args()
    if args:
        parser.error("Does not accept any argument.")

    daemon = Poller(debug=opts.debug_file is not None, **opts.__dict__)
    if not opts.profile:
        daemon.main()
    else:
        # For perf tuning:
        import cProfile
        cProfile.run('''daemon.main()''', opts.profile)


if __name__ == '__main__':
    main()
