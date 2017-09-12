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

# Default is alignak account
ACCOUNT=$1
# Parse command line arguments
if [ $# -eq 0 ]; then
    ACCOUNT="alignak"
fi

## Same procedure as the one done in the debian installation
## Create user and group
echo "Checking / creating '$ACCOUNT' user and users group"
# Note: if the user exists, its properties won't be changed (gid, home, shell)
adduser --quiet --system --home /var/lib/$ACCOUNT --no-create-home --group $ACCOUNT || true

## Create nagios group
echo "Checking / creating 'nagios' users group"
addgroup --system nagios || true

## Add user to nagios group
id -Gn $ACCOUNT |grep -E '(^|[[:blank:]])nagios($|[[:blank:]])' >/dev/null ||
   echo "Adding user '$ACCOUNT' to the nagios users group"
   adduser $ACCOUNT nagios

## Create directories with proper permissions
for i in /usr/local/etc/alignak /usr/local/var/run/alignak /usr/local/var/log/alignak /usr/local/var/lib/alignak /usr/local/var/libexec/alignak
do
   mkdir -p $i
   echo "Setting '$ACCOUNT' ownership on: $i"
   chown -R $ACCOUNT:$ACCOUNT $i
done

echo "Setting file permissions on: /usr/local/etc/alignak"
find /usr/local/etc/alignak -type f -exec chmod 664 {} +
find /usr/local/etc/alignak -type d -exec chmod 775 {} +

### Set permissions on alignak-backend settings
if [ -d "/usr/local/etc/alignak-backend" ]; then
   echo "Setting '$ACCOUNT' ownership on /usr/local/etc/alignak-backend"
   chown -R $ACCOUNT:$ACCOUNT /usr/local/etc/alignak-backend
   
   echo "Setting file permissions on: /usr/local/etc/alignak-backend"
   find /usr/local/etc/alignak-backend -type f -exec chmod 664 {} +
   find /usr/local/etc/alignak-backend -type d -exec chmod 775 {} +
fi
### Set permissions on alignak-backend log directory
if [ -d "/usr/local/var/log/alignak-backend" ]; then
   echo "Setting '$ACCOUNT' ownership on /usr/local/var/log/alignak-backend"
   chown -R $ACCOUNT:$ACCOUNT /usr/local/var/log/alignak-backend
   
   echo "Setting file permissions on: /usr/local/var/log/alignak-backend"
   find /usr/local/var/log/alignak-backend -type f -exec chmod 664 {} +
   find /usr/local/var/log/alignak-backend -type d -exec chmod 775 {} +
fi

### Set permissions on alignak-webui settings
if [ -d "/usr/local/etc/alignak-webui" ]; then
   echo "Setting '$ACCOUNT' ownership on /usr/local/etc/alignak-webui"
   chown -R $ACCOUNT:$ACCOUNT /usr/local/etc/alignak-webui
   
   echo "Setting file permissions on: /usr/local/etc/alignak-webui"
   find /usr/local/etc/alignak-webui -type f -exec chmod 664 {} +
   find /usr/local/etc/alignak-webui -type d -exec chmod 775 {} +
fi
### Set permissions on alignak-webui log directory
if [ -d "/usr/local/var/log/alignak-webui" ]; then
   echo "Setting '$ACCOUNT' ownership on /usr/local/var/log/alignak-webui"
   chown -R $ACCOUNT:$ACCOUNT /usr/local/var/log/alignak-webui
   
   echo "Setting file permissions on: /usr/local/var/log/alignak-webui"
   find /usr/local/var/log/alignak-webui -type f -exec chmod 664 {} +
   find /usr/local/var/log/alignak-webui -type d -exec chmod 775 {} +
fi

echo "Terminated"
