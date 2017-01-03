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
DIR="$(cd $(dirname "$0"); pwd)"
# Default is no debug
DEBUG_MODE="0"
# Default is no configuration file for the daemons
CONFIG_MODE="0"
# Default is to daemonize
DAEMONIZE="--daemon"
# Default is a simple daemon (no monitoring configuration file)
ARBITER_MODE="0"
# Default is running mode - do not only verify the configuration
VERIFY_MODE="0"

usage() {
    cat << END

Usage: $0 [-h|--help] [-v|--version] [-d|--debug] [-a|--arbiter] [-n|--no-daemon] [-V|--verify] daemon_name

 -h (--help)        display this message
 -v (--version)     display alignak version
 -d (--debug)       start requested daemon in debug mode
 -c (--config)      start requested daemon with its configuration file
                    Default is to start with no configuration file to use the default daemon parameters
                    The pid and log files are stored in the current working directory
                    When using this option, check the directories declared in its configuration file
 -n (--no-daemon)   start requested daemon in console mode (do not daemonize)
 -a (--arbiter)     start requested daemon in arbiter mode
                    This option adds the monitoring configuration file(s) on the command line
                    This option will raise an error if the the daemon is not an arbiter.
 -V (--verify)      start requested daemon in verify mode (only for the arbiter)
                    This option will raise an error if the the daemon is not an arbiter.

END
}

# Parse command line arguments
if [ $# -eq 0 ]; then
    usage >&2
    exit 1
fi

for i in "$@"
do
case $i in
    -h|--help)
    usage >&1
    exit 0
    ;;
    -d|--debug)
    DEBUG_MODE="1"
    shift
    ;;
    -a|--arbiter)
    ARBITER_MODE="1"
    shift
    ;;
    -c|--config)
    CONFIG_MODE="1"
    shift
    ;;
    -n|--no-daemon)
    DAEMONIZE=""
    shift
    ;;
    -V|--verify)
    VERIFY_MODE="1"
    shift
    ;;
    *)
    DAEMON_NAME="$i"
    shift
    ;;
esac
done

# Get the daemon's variables names (only the name, not the value)
scr_var="${DAEMON_NAME}_DAEMON"
cfg_var="${DAEMON_NAME}_CFG"
dbg_var="${DAEMON_NAME}_DEBUGFILE"

# Get Alignak configuration and parse the result to declare environment variables
while IFS=';' read -ra VAR; do
    for v in "${VAR[@]}"; do
        eval "$v"
    done
done <<< "$($DIR/../alignak/bin/alignak_environment.py ../etc/alignak.ini)"

echo "---"
echo "Alignak daemon: $DAEMON_NAME"
echo "---"
echo "Alignak configuration file: $ALIGNAK_CONFIGURATION_CFG"
echo "Alignak extra configuration file: $ALIGNAK_CONFIGURATION_SPECIFICCFG"
echo "---"
echo "Daemon script: $scr_var = ${!scr_var}"
echo "Daemon configuration: $cfg_var = ${!cfg_var}"
echo "Daemon debug file: $dbg_var = ${!dbg_var}"
echo "---"

DEBUG_FILE=""
if [ "$DEBUG_MODE" = "1" ]; then
    DEBUG_FILE="--debugfile ${!dbg_var}"
    echo "Launching the daemon: $DAEMON_NAME in debug mode, log: ${!dbg_var}"
fi

CONFIG_FILE=""
if [ "$CONFIG_MODE" = "1" ]; then
    CONFIG_FILE="--config ${!cfg_var}"
    echo "Launching the daemon: $DAEMON_NAME with configuration file: ${!cfg_var}"
fi

MONITORING_CONFIG_FILES="--arbiter ${ALIGNAK_CONFIGURATION_CFG}"
if [ ! "$ALIGNAK_CONFIGURATION_SPECIFICCFG" = "" ]; then
    MONITORING_CONFIG_FILES="--arbiter ${ALIGNAK_CONFIGURATION_CFG} --arbiter ${ALIGNAK_CONFIGURATION_SPECIFICCFG}"
fi

if [ "$ARBITER_MODE" = "1" ]; then
    if [ "$VERIFY_MODE" = "1" ]; then
        echo "Launching the daemon: $DAEMON_NAME in verify mode, configuration: ${MONITORING_CONFIG_FILES}"
        "${!scr_var}" --verify-config $CONFIG_FILE $MONITORING_CONFIG_FILES $DEBUG_FILE $DAEMONIZE
    else
        echo "Launching the daemon: $DAEMON_NAME in arbiter mode, configuration: ${MONITORING_CONFIG_FILES}"
        "${!scr_var}" $CONFIG_FILE $MONITORING_CONFIG_FILES $DEBUG_FILE $DAEMONIZE
    fi
else
    echo "Launching the daemon: $DAEMON_NAME"
    "${!scr_var}" $CONFIG_FILE $DEBUG_FILE $DAEMONIZE
fi
