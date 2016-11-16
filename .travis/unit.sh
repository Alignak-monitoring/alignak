#!/bin/sh

set -ev

cd test
# Delete previously existing coverage results
coverage erase

# Declare a COVERAGE_PROCESS_START environment variable
# This variable is used to allow coverage tests in the Alignak daemons started processes
COVERAGE_PROCESS_START='.coveragerc'

# Run test suite with py.test running its coverage plugin
pytest --cov=alignak --cov-config .coveragerc test_*.py

# Report about coverage
coverage report -m
cd ..

