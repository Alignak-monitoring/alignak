#!/bin/sh
NOW=$(date +"%Y-%m-%d %H-%M-%S")
if [ -n "$5" ]; then
   SLEEP=$5
else
   SLEEP=0
fi
if [ -n "$4" ]; then
   MSG=$4
else
   MSG=""
fi
if [ -n "$3" ]; then
   STATE=$3
else
   STATE=3
fi
echo "$NOW - Hi, checking $1/$2, $MSG -> exit=$STATE | Sleep=$SLEEP" >> /tmp/checks.log

sleep $SLEEP
echo "Hi, checking $1/$2, $MSG -> exit=$STATE | Sleep=$SLEEP"
exit $STATE