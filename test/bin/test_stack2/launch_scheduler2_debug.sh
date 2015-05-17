#!/bin/bash
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

DIR=$(cd $(dirname "$0"); pwd)
BIN=$DIR"/../../../bin"
ETC=$DIR"/../../../test/etc/test_stack2"
DEBUG_PATH="/tmp/scheduler-2.debug"

echo "Launching Scheduler (that do scheduling only) in debug mode to the file $DEBUG_PATH"
$BIN/alignak-scheduler -d -c $ETC/schedulerd-2.ini --debug $DEBUG_PATH
