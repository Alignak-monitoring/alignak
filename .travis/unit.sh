#!/bin/sh

set -ev

cd test
nosetests -xv --process-restartworker --processes=1 --process-timeout=300  --with-coverage --cover-package=alignak

(pkill -6 -f "alignak_-" || :)
nosetests --process-restartworker --processes=1 --process-timeout=300  --with-coverage --cover-package=alignak full_tst.py

# Combine coverage files
coverage combine
cd ..

