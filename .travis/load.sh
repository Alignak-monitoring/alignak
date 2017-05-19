#!/bin/sh

set -ev

cd test_load

# Run test suite with py.test (no coverage plugin)
pytest -v test_*.py

cd ..

