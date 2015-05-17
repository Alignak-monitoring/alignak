#!/bin/sh
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

sudo rm -fr /usr/local/lib/python2.*/dist-packages/Alignak-*-py2.6.egg
sudo rm -fr /usr/local/lib/python2.*/dist-packages/alignak
sudo rm -fr /usr/local/bin/alignak-*
sudo rm -fr /usr/bin/alignak-*
sudo rm -fr /etc/alignak
sudo rm -fr /etc/init.d/alignak*
sudo rm -fr /var/lib/alignak
sudo rm -fr /var/run/alignak
sudo rm -fr /var/log/alignak
sudo rm -fr /etc/default/alignak

sudo rm -fr build dist Alignak.egg-info
rm -fr test/var/*.pid
rm -fr var/*.debug
rm -fr var/archives/*
rm -fr var/*.log*
rm -fr var/*.pid
rm -fr var/service-perfdata
rm -fr var/*.dat
rm -fr var/*.profile
rm -fr var/*.cache
rm -fr var/rw/*cmd
#rm -fr /tmp/retention.dat
rm -fr /tmp/*debug
rm -fr test/tmp/livelogs*
rm -fr bin/default/alignak

# Then kill remaining processes
# first ask a easy kill, to let them close their sockets!
killall python2.6 2> /dev/null
killall python 2> /dev/null
killall /usr/bin/python 2> /dev/null

# I give them 2 sec to close
sleep 3

# Ok, now I'm really angry if there is still someboby alive :)
sudo killall -9 python2.6 2> /dev/null
sudo killall -9 python 2> /dev/null
sudo killall -9 /usr/bin/python 2> /dev/null

echo ""
