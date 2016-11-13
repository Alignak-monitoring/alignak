#!/bin/sh

set -ev

mv test/.coverage .
coveralls debug
echo "Submitting coverage results to coveralls.io..."
coveralls -v --rcfile=test/.coveragerc
echo "Submitted"
