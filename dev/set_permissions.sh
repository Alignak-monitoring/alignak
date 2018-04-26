#!/bin/bash

#
# Copyright (C) 2015-2017: Alignak team, see AUTHORS.txt file for contributors
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

# Default is alignak account
ACCOUNT=$1
# Default is /usr/local account
PREFIX=$2
# Parse command line arguments
if [ $# -eq 0 ]; then
    ACCOUNT="alignak"
    PREFIX="/usr/local"

fi
if [ $# -eq 1 ]; then
    PREFIX="/usr/local"

fi

## Create user and group
echo "Checking / creating '$ACCOUNT' user and users group"
id -u $ACCOUNT &>/dev/null || useradd $ACCOUNT --system --no-create-home --user-group

## Create nagios group
echo "Checking / creating 'nagios' users group"
getent group nagios || groupadd nagios

## Add user to nagios group
id -Gn $ACCOUNT |grep -E '(^|[[:blank:]])nagios($|[[:blank:]])' >/dev/null ||
   echo "Adding user '$ACCOUNT' to the nagios users group"
   usermod -a -G nagios $ACCOUNT

## Create directories with proper permissions
for i in $PREFIX/etc/alignak $PREFIX/var/run/alignak $PREFIX/var/log/alignak $PREFIX/var/lib/alignak $PREFIX/var/libexec/alignak
do
    mkdir -p $i
    echo "Setting '$ACCOUNT' ownership on: $i"
    chown -R $ACCOUNT:$ACCOUNT $i

    echo "Setting file permissions on: $i"
    find $i -type f -exec chmod 664 {} +
    find $i -type d -exec chmod 775 {} +
done

### Set permissions on alignak-backend settings
if [ -d "$PREFIX/etc/alignak-backend" ]; then
   echo "Setting '$ACCOUNT' ownership on $PREFIX/etc/alignak-backend"
   chown -R $ACCOUNT:$ACCOUNT $PREFIX/etc/alignak-backend

   echo "Setting file permissions on: $PREFIX/etc/alignak-backend"
   find $PREFIX/etc/alignak-backend -type f -exec chmod 664 {} +
   find $PREFIX/etc/alignak-backend -type d -exec chmod 775 {} +
fi
### Set permissions on alignak-backend log directory
if [ -d "$PREFIX/var/log/alignak-backend" ]; then
   echo "Setting '$ACCOUNT' ownership on $PREFIX/var/log/alignak-backend"
   chown -R $ACCOUNT:$ACCOUNT $PREFIX/var/log/alignak-backend

   echo "Setting file permissions on: $PREFIX/var/log/alignak-backend"
   find $PREFIX/var/log/alignak-backend -type f -exec chmod 664 {} +
   find $PREFIX/var/log/alignak-backend -type d -exec chmod 775 {} +
fi

### Set permissions on alignak-webui settings
if [ -d "$PREFIX/etc/alignak-webui" ]; then
   echo "Setting '$ACCOUNT' ownership on $PREFIX/etc/alignak-webui"
   chown -R $ACCOUNT:$ACCOUNT $PREFIX/etc/alignak-webui
   
   echo "Setting file permissions on: $PREFIX/etc/alignak-webui"
   find $PREFIX/etc/alignak-webui -type f -exec chmod 664 {} +
   find $PREFIX/etc/alignak-webui -type d -exec chmod 775 {} +
fi
### Set permissions on alignak-webui log directory
if [ -d "$PREFIX/var/log/alignak-webui" ]; then
   echo "Setting '$ACCOUNT' ownership on $PREFIX/var/log/alignak-webui"
   chown -R $ACCOUNT:$ACCOUNT $PREFIX/var/log/alignak-webui
   
   echo "Setting file permissions on: $PREFIX/var/log/alignak-webui"
   find $PREFIX/var/log/alignak-webui -type f -exec chmod 664 {} +
   find $PREFIX/var/log/alignak-webui -type d -exec chmod 775 {} +
fi

echo "Terminated"
