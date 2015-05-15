#!/bin/bash

DIR=$(cd $(dirname "$0"); pwd)
BIN=$DIR"/../../bin"
ETC=$DIR"/../../etc"
DEBUG_PATH="/tmp/arbiter.debug"

# needed because arbiter doesn't have a default 'workdir' "properties" attribute:
cd "$DIR/../../var"
echo "Launching Arbiter (that read configuration and dispatch it) in debug mode to the file $DEBUG_PATH"
$BIN/alignak-arbiter -d -c $ETC/../test/etc/test_stack2/alignak.cfg -c $ETC/../test/etc/test_stack2/alignak-specific-ha-only.cfg --debug $DEBUG_PATH
