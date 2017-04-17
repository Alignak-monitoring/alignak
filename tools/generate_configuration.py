#!/usr/bin/env python
#
# Copyright (C) 2015-2015:
#
# This file is part of Demetra.
#
# Demetra is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Demetra is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Demetra.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import getopt
import string
import random

def main(argv):
    hosts = 0
    services = 10
    try:
        opts, args = getopt.getopt(argv,"h:",["hosts=","services="])
    except getopt.GetoptError:
        print 'generate_configuration.py --hosts <inputfile> --services <outputfile>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'generate_configuration.py --hosts <inputfile> --services <outputfile>'
            sys.exit()
        elif opt in ("--hosts"):
            hosts = int(arg)
        elif opt in ("--services"):
            services = int(arg)
    print 'Number of hosts is', hosts
    print 'number of services per host is', services

    etc_path = "/etc/shinken"
    if 'win' in sys.platform:
        etc_path = "c:\\shinken\\etc"
    elif 'bsd' in sys.platform or 'dragonfly' in sys.platform:
        etc_path = "/usr/local/etc/shinken"

    # clean hosts and servcies folder
    filelist = [ f for f in os.listdir(etc_path + '/hosts/') if f.endswith(".cfg") ]
    for f in filelist:
        os.remove(etc_path + '/hosts/' + f)
    filelist = [ f for f in os.listdir(etc_path + '/services/') if f.endswith(".cfg") ]
    for f in filelist:
        os.remove(etc_path + '/services/' + f)

    for x in xrange(0, hosts):
        name = ''.join(random.SystemRandom().choice(string.ascii_lowercase) for _ in range(40))

        f = open(etc_path + '/hosts/' + name + '.cfg', 'w')
        f.write(('define host{\n'
        '   use                     generic-host\n'
        '   contact_groups          admins\n'
        '   host_name               ' + name + '\n'
        '   address                 127.0.0.1\n'
        '   }'))
        f.close()

        for s in xrange(0, services):
            f = open(etc_path + '/services/' + name + '.cfg', 'a')
            f.write(('define service{\n'
            '   service_description             service' + str(s) + '\n'
            '   use                             generic-service\n'
            '   host_name                       ' + name + '\n'
            '   check_command                   check_ping\n'
            '   register                        1\n'
            '   }\n'))
            f.close()

if __name__ == "__main__":
   main(sys.argv[1:])
