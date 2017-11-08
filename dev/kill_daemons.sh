#!/usr/bin/env bash

for f in /user/local/var/run/alignak/*.pid ; do
    pkill -F "$f";
done

