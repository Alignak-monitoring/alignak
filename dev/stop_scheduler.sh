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

DAEMON_TYPE="scheduler"
if [ $# -eq 0 ]; then
    DAEMON_NAME="${DAEMON_TYPE}-master"
else
    # Make parameter as lowercase for daemon name
    DAEMON_NAME="${1,,}"
fi
"$DIR/_stop_daemon.sh" $@ -a "$DAEMON_NAME"
