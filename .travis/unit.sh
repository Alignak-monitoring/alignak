#!/bin/sh

set -ev

cd test
# Delete previously existing coverage results
coverage erase

# Run all the unit tests
nosetests -xv --process-restartworker --processes=1 --process-timeout=300  --with-coverage --cover-package=alignak

# Combine coverage files
coverage combine
cd ..

