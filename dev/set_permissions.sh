#!/bin/bash

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

## Same procedure as the one done in the debian installation
## Create user and group
echo "Checking / creating 'alignak' user and users group"
# Note: if the user exists, it's properties won't be changed (gid, home, shell)
adduser  --quiet --system --home /var/lib/alignak --no-create-home --group alignak || true

## Create nagios group
echo "Checking / creating 'nagios' users group"
addgroup --system nagios || true

## Add alignak to nagios group
id -Gn alignak |grep -E '(^|[[:blank:]])nagios($|[[:blank:]])' >/dev/null ||
    echo "Adding user 'alignak' to the nagios users group"
    adduser alignak nagios

## Create directories with proper permissions
for i in /usr/local/etc/alignak /usr/local/var/run/alignak /usr/local/var/log/alignak /usr/local/var/lib/alignak /usr/local/var/libexec/alignak
do
    mkdir -p $i
    echo "Setting 'alignak' ownership on: $i"
    chown -R alignak:alignak $i
done

echo "Setting file permissions on: /usr/local/etc/alignak"
find /usr/local/etc/alignak -type f -exec chmod 664 {} +
find /usr/local/etc/alignak -type d -exec chmod 775 {} +

echo "Terminated"
