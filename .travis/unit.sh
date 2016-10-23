#!/bin/sh

set -ev

cd test
nosetests -xv --process-restartworker --processes=1 --process-timeout=300  --with-coverage --cover-package=alignak
coverage combine

(pkill -6 -f "alignak_-" || :)
python full_tst.py
cd ..

