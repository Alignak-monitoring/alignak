#!/bin/bash

if [[ "$1" == "" ]]; then
    to_skip=$HOME
else
    to_skip=$1
fi

if [[ "$TRAVIS" == "true" ]]; then
    # Travis git clone repo in Alignak-monitoring/alignak
    locate -i alignak | grep -v "monitoring" | xargs rm -rf
else
    # use parameter (HOME if not)
    locate -i alignak | grep -v $to_skip | xargs rm -rf
fi

sudo updatedb
