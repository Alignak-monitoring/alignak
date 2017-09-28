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
# Default is no debug
DEBUG_MODE="0"
# Default is to not replace a former daemon
REPLACE="--replace"
# Default is to daemonize
DAEMONIZE="--daemon"
# Default is running mode - do not only verify the configuration
VERIFY_MODE="0"

usage() {
    cat << END

Usage: $0 [-h|--help] [-v|--version] [-d|--debug] [-a|--arbiter] [-n|--no-daemon] [-V|--verify] daemon_name

 -h (--help)        display this message
 -v (--version)     display alignak version
 -d (--debug)       start requested daemon in debug mode
 -e (--environment) Alignak environment file
                    If not provided, the script will search an ALIGNAKINI environment variable
                    else in /usr/local/etc/alignak/alignak.ini
                    else in /etc/alignak/alignak.ini
 -r (--no-replace)  do not replace an existing daemon (if valid pid file exists)
 -n (--no-daemon)   start requested daemon in console mode (do not daemonize)
 -V (--verify)      start requested daemon in verify mode (only for the arbiter)
                    This option will raise an error if the the daemon is not an arbiter.

END
}

# Parse command line arguments
if [ $# -eq 0 ]; then
    usage >&2
    exit 1
fi

while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -h|--help)
    usage >&1
    exit 0
    ;;
    -d|--debug)
    DEBUG_MODE="1"
    shift
    ;;
    -e|--environment)
    ALIGNAK_CONFIGURATION_INI="$2"
    shift
    ;;
    -n|--no-daemon)
    DAEMONIZE=""
    shift
    ;;
    -r|--no-replace)
    REPLACE=""
    shift
    ;;
    -V|--verify)
    VERIFY_MODE="1"
    shift
    ;;
    *)
    DAEMON_NAME="$key"
    shift
    ;;
esac
done

# Check daemon name is provided
if [ -z ${DAEMON_NAME} ]; then
    echo "No daemon name in the command parameters"
    usage >&2
    exit 1
fi

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

if [ -z ${ALIGNAK_CONFIGURATION_CFG} ]; then
   if [ ${ALIGNAKCFG} ]; then
      echo "Alignak main configuration file is defined in the environment"
      ALIGNAK_CONFIGURATION_CFG="$ALIGNAKCFG"
   fi
fi

if [ -z ${ALIGNAK_CONFIGURATION_CFG2} ]; then
   if [ ${ALIGNAKCFG2} ]; then
       echo "Alignak specific configuration file is defined in the environment"
       ALIGNAK_CONFIGURATION_CFG2="$CFG2"
   fi
fi

echo "---"
echo "Alignak daemon: $DAEMON_NAME $DAEMON_ARBITER_MASTER_TYPE"
echo "---"
echo "Alignak configuration file: $ALIGNAK_CONFIGURATION_CFG"
echo "Alignak extra configuration file: $ALIGNAK_CONFIGURATION_CFG2"
echo "---"
echo "Daemon type: $type_var = ${!type_var}"
echo "Daemon script: $scr_var = ${!scr_var}"
echo "Daemon debug file: $dbg_var = ${!dbg_var}"
echo "---"
echo "Daemon console mode: $DAEMONIZE"
echo "Daemon replace mode: $REPLACE"
echo "---"

# Default is a simple daemon (no monitoring configuration file)
ARBITER_MODE="0"
if [ "${!type_var}" = "arbiter" ]; then
    ARBITER_MODE="1"
fi

DEBUG_FILE=""
if [ "$DEBUG_MODE" = "1" ]; then
    DEBUG_FILE="--debugfile ${!dbg_var}"
    echo "Launching the daemon: $DAEMON_NAME in debug mode, log: ${!dbg_var}"
fi

MONITORING_CONFIG_FILES="--arbiter ${ALIGNAK_CONFIGURATION_CFG}"
if [ ! "$ALIGNAK_CONFIGURATION_CFG2" = "" ]; then
    MONITORING_CONFIG_FILES="--arbiter ${ALIGNAK_CONFIGURATION_CFG} --arbiter ${ALIGNAK_CONFIGURATION_CFG2}"
fi


if [ "$ARBITER_MODE" = "1" ]; then
    if [ "$VERIFY_MODE" = "1" ]; then
        echo "Launching the daemon: $DAEMON_NAME in verify mode, configuration: ${MONITORING_CONFIG_FILES}"
#        "$scr_var" -e $ALIGNAK_CONFIGURATION_INI --verify-config $MONITORING_CONFIG_FILES $DEBUG_FILE $DAEMONIZE $REPLACE
    else
        echo "Launching the daemon: $DAEMON_NAME in arbiter mode, configuration: ${MONITORING_CONFIG_FILES}"
#        "$scr_var" -e $ALIGNAK_CONFIGURATION_INI $MONITORING_CONFIG_FILES $DEBUG_FILE $DAEMONIZE $REPLACE
    fi
else
    echo "Launching the daemon: $DAEMON_NAME"
    "$scr_var" -e $ALIGNAK_CONFIGURATION_INI $DEBUG_FILE $DAEMONIZE $REPLACE
fi
