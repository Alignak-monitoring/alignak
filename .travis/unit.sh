#!/bin/sh

set -ev

cd test
# Delete previously existing coverage results
coverage erase

# Run test suite with py.test running its coverage plugin
pytest --cov=alignak --cov-config .coveragerc test_*.py

# Report about coverage
coverage report -m
cd ..

