#!/bin/sh

set -ev

cd test
# Delete previously existing coverage results
coverage erase

# Run test suite with py.test running its coverage plugin
# Verbose mode to have the test list
# Dump the 10 slowest tests
pytest --durations=10 --cov=alignak --cov-report term-missing --cov-config .coveragerc test_*.py

# Report about coverage
coverage report -m
cd ..

