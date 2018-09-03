#!/bin/sh
echo "Hi, I'm for testing only. Please do not use me directly, really | Hip=99% Hop=34mm"
if [ -n "$2" ]; then
  SLEEP=$2
else
  SLEEP=1
fi
sleep $SLEEP
if [ -n "$1" ]; then
    exit $1
else
    exit 3
fi
