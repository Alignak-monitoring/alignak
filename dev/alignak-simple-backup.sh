#!/bin/sh

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
# -----------------------------------------------------------------------------
# Thanks to @spea1 for contributing to this script
# -----------------------------------------------------------------------------
#
#  ./alignak-simple-backup.sh will save the main Alignak configuration directories
# to dated tar.gz files in the alignak-backup directory of the current user home
# directory.
#  You can start this script with a command line parameter to specify another directory
# than the default one
# -----------------------------------------------------------------------------


# Default is a sub-directory in the current user home directory
ALIGNAK_BACKUP_DIR=$1
# Parse command line arguments
if [ $# -eq 0 ]; then
   ALIGNAK_BACKUP_DIR=~/alignak-backup
fi

if [ ! -d "$ALIGNAK_BACKUP_DIR" ]; then
   mkdir -p $ALIGNAK_BACKUP_DIR
fi
echo "Back-up directory: $ALIGNAK_BACKUP_DIR"

NOW=$(date +"%y%m%d-%H%M%S")

### Backup alignak settings
if [ -d "/usr/local/etc/alignak" ]; then
   echo "Backing-up /usr/local/etc/alignak..."
   cd /usr/local/etc/alignak
   tar czf $ALIGNAK_BACKUP_DIR/$NOW-alignak.tar.gz .
fi

### Backup alignak-backend settings
if [ -d "/usr/local/etc/alignak-backend" ]; then
   echo "Backing-up /usr/local/etc/alignak-backend..."
   cd /usr/local/etc/alignak-backend
   tar czf $ALIGNAK_BACKUP_DIR/$NOW-alignak-backend.tar.gz .
fi

### Backup alignak-webui settings
if [ -d "/usr/local/etc/alignak-webui" ]; then
   echo "Backing-up /usr/local/etc/alignak-webui..."
   cd /usr/local/etc/alignak-webui
   tar czf $ALIGNAK_BACKUP_DIR/$NOW-alignak-webui.tar.gz .
fi

## Backup alignak-libexec directory
if [ -d "/usr/local/var/libexec/alignak" ]; then
   echo "Backing-up /usr/local/etc/alignak libexec..."
   cd /usr/local/var/libexec/alignak
   tar czf $ALIGNAK_BACKUP_DIR/$NOW-alignak-libexec.tar.gz .
fi

echo "Terminated"
