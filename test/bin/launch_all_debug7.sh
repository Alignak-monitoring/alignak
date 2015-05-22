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
echo $DIR

# Prepare the launch by cleaning var/log directories
. $DIR/../../bin/preparedev


# Schedulers
$DIR/../../bin/launch_scheduler_debug.sh
$DIR/test_stack2/launch_scheduler2_debug.sh

# pollers
$DIR/../../bin/launch_poller_debug.sh
$DIR/test_stack2/launch_poller2_debug.sh

# reactionners
$DIR/../../bin/launch_reactionner_debug.sh
$DIR/test_stack2/launch_reactionner2_debug.sh

# brokers
$DIR/../../bin/launch_broker_debug.sh
$DIR/test_stack2/launch_broker2_debug.sh

# One receiver
$DIR/../../bin/launch_receiver_debug.sh

# From now only one arbtier
$DIR/launch_arbiter7_debug.sh


