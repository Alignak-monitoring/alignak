#!/bin/sh

set -ev

cd test

if [[ "$TRAVIS_PYTHON_VERSION" == "2.7" ]]; then
    # Run test suite with py.test running its coverage plugin
    # Dump the 10 slowest tests
    pytest --durations=10 --cov=alignak --cov-report term-missing --cov-config .coveragerc test_*.py
    # Report about coverage
    coverage report -m
else
    pytest --durations=10 test_*.py
fi

cd ..

