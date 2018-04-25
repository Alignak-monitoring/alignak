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

"""
This is the class of the Arbiter. Its role is to read configuration,
cut it, and send it to other elements like schedulers, reactionners
or pollers. It is also responsible for the high availability feature.
For example, if a scheduler dies, it sends the late scheduler's conf
to another scheduler available.
It also reads orders form users (nagios.cmd) and sends them to schedulers.
"""
from __future__ import print_function

from alignak.daemons.arbiterdaemon import Arbiter
from alignak.util import parse_daemon_args


def main():
    """Parse args and run main daemon function

    :return: None
    """
    try:
        args = parse_daemon_args(True)

        # Protect for windows multiprocessing that will RELAUNCH all
        while True:
            daemon = Arbiter(debug=args.debug_file is not None, **args.__dict__)
            daemon.main()
            if not daemon.need_config_reload:
                break
            daemon = None
    except Exception as exp:  # pylint: disable=broad-except
        print(("*** Daemon exited because: %s" % str(exp)))
        exit(1)


if __name__ == '__main__':
    main()
