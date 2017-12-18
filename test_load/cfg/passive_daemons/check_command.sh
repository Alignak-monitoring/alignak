#!/bin/sh
NOW=$(date +"%Y-%m-%d %H-%M-%S")
if [ -n "$4" ]; then
   SLEEP=$4
else
   SLEEP=0
fi
if [ -n "$3" ]; then
   STATE=$3
else
   STATE=3
fi
echo "$NOW - Hi, checking $1/$2 -> exit=$STATE | Sleep=$SLEEP" >> /tmp/checks.log

sleep $SLEEP
echo "Hi, checking $1/$2 -> exit=$STATE | Sleep=$SLEEP"
exit $STATE