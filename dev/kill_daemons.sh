#!/usr/bin/env bash

# -----------------------------------------------------------------------------
#  This script  will send a KILL signal to all the Alignak daemons
# -----------------------------------------------------------------------------

for f in /user/local/var/run/alignak/*.pid ; do
    pkill -F "$f";
done

