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
#  Copyright (C) 2009-2014:
#     Jean Gabes, naparuba@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Romain Forlot, rforlot@yahoo.com
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
This modules provides class for the Poller daemon
"""
from alignak.satellite import Satellite
from alignak.property import PathProp, IntegerProp, StringProp


class Poller(Satellite):
    """Poller class. Referenced as "app" in most Interface

    """
    do_checks = True    # I do checks
    do_actions = False  # but no actions
    my_type = 'poller'

    properties = Satellite.properties.copy()
    properties.update({
        'daemon_type':
            StringProp(default='poller'),
        'pidfile':
            PathProp(default='pollerd.pid'),
        'port':
            IntegerProp(default=7771),
        'local_log':
            PathProp(default='pollerd.log'),
    })

    def __init__(self, config_file, is_daemon, do_replace, debug, debug_file,
                 port=None, local_log=None, daemon_name=None):
        self.daemon_name = 'poller'
        if daemon_name:
            self.daemon_name = daemon_name

        super(Poller, self).__init__(self.daemon_name, config_file, is_daemon, do_replace,
                                     debug, debug_file, port, local_log)
