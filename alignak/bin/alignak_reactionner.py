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

"""
 This class is an application that launches actions like
 notifications or event handlers
 The reactionner listens to the Arbiter for the configuration sent through
 the given port as first argument.
 The configuration sent by the arbiter specifies from which schedulers the
 will take actions.
 When the reactionner is already launched and has its own conf, it keeps
 on listening the arbiter (one a timeout)
 In case the arbiter has a new conf to send, the reactionner forget its old
 schedulers (and the associated actions) and take the new ones instead.
"""

import optparse

from alignak.daemons.reactionnerdaemon import Reactionner
from alignak.version import VERSION


def main():
    """Parse args and run main daemon function

    :return: None
    """
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
                      help="Replace previous running reactionner")
    parser.add_option('--debugfile', dest='debug_file',
                      help=("Debug file. Default: not used "
                            "(why debug a bug free program? :) )"))
    parser.add_option("-p", "--profile",
                      dest="profile",
                      help="Dump a profile file. Need the python cProfile librairy")

    opts, args = parser.parse_args()
    if args:
        parser.error("Does not accept any argument.")

    daemon = Reactionner(debug=opts.debug_file is not None, **opts.__dict__)
    daemon.main()


if __name__ == '__main__':
    main()
