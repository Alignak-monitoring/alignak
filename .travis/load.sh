#!/bin/sh

set -ev

cd test_load
# Delete previously existing coverage results
coverage erase

# Setup test environment
./setup_test.sh

# Run test suite with py.test running its coverage plugin
pytest -v --cov=alignak --cov-config .coveragerc test_*.py

# Report about coverage
coverage report -m
cd ..
