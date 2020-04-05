#!/bin/sh

# Script to generate all the daemon scripts from the template

for svc in broker poller reactionner receiver scheduler arbiter; do
    dname=$svc-master
    # For some reason you can't go over 15 characters in a daemon name
    if [ $svc = reactionner ] ; then
        dname=reaction-master
    fi
    if [ $svc = scheduler ] ; then
        dname=schedule-master
    fi
    sed s/%SERVICE%/$svc/ service-template | sed s/%DAEMONNAME%/$dname/ > alignak-$svc
done
