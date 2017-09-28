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
DIR="$(cd $(dirname "$0"); pwd)"

usage() {
    cat << END

Usage: $0 daemon_name

END
}

if [ $# -eq 0 ]; then
    echo "No daemon name in the command parameters"
    usage >&2
    exit 1
fi

DAEMON_NAME="$1"

# Replace - with _ in daemon name and uppercase the daemon name
DAEMON_NAME_VAR="${DAEMON_NAME/-/_}"
DAEMON_NAME_VAR=${DAEMON_NAME_VAR^^}

# Alignak.ini file name
echo "---"
if [ -z ${ALIGNAK_CONFIGURATION_INI} ]; then
   if [ ${ALIGNAKINI} ]; then
       echo "Alignak ini configuration file is defined in the environment"
       ALIGNAK_CONFIGURATION_INI="$ALIGNAKINI"
   else
       if [ -f "/usr/local/etc/alignak/alignak.ini" ]; then
           echo "Alignak ini configuration file found in /usr/local/etc/alignak folder"
           ALIGNAK_CONFIGURATION_INI="/usr/local/etc/alignak/alignak.ini"
       else
           if [ -f "/etc/alignak/alignak.ini" ]; then
               echo "Alignak ini configuration file found in /etc/alignak folder"
               ALIGNAK_CONFIGURATION_INI="/etc/alignak/alignak.ini"
           else
               ALIGNAK_CONFIGURATION_INI="$DIR/../etc/alignak.ini"
           fi
       fi
   fi
else
   if [ ! -f ${ALIGNAK_CONFIGURATION_INI} ]; then
       echo "Alignak ini configuration file not found in $ALIGNAK_CONFIGURATION_INI!"
       usage >&2
       exit 1
   fi
fi
echo "Alignak ini configuration file: $ALIGNAK_CONFIGURATION_INI"
echo "---"

# Get Alignak configuration and parse the result to declare environment variables
while IFS=';' read -ra VAR; do
    for v in "${VAR[@]}"; do
        eval "$v"
    done
done <<< "$(alignak-environment $ALIGNAK_CONFIGURATION_INI)"

# Get the daemon's variables names (only the name, not their values)
type_var="DAEMON_${DAEMON_NAME_VAR}_TYPE"
scr_var="alignak-${!type_var}"
dbg_var="DAEMON_${DAEMON_NAME_VAR}_DEBUGFILE"

if [ -z ${!type_var} ]; then
   echo "Required daemon ($DAEMON_NAME) not found in the Alignak environment!"
   exit 1
else
   echo "Found a configuration for the required daemon (${!type_var} - $DAEMON_NAME) in the Alignak environment"
fi


echo "---"
echo "Alignak daemon: $DAEMON_NAME"
echo "---"
echo "Alignak configuration file: $ALIGNAK_CONFIGURATION_CFG"
echo "Alignak extra configuration file: $ALIGNAK_CONFIGURATION_SPECIFICCFG"
echo "---"
echo "Daemon type: $type_var = ${!type_var}"
echo "Daemon script: $scr_var"
echo "---"

echo "---"
echo "Stopping the daemon: $DAEMON_NAME"
processes=${scr_var:0:15}
echo "Killing process(es) starting with: $processes"
pkill $processes
if [ $? -eq 0 ]; then
    echo "Killed"
else
    echo "Error when killing process(es): $processes"
fi
