#!/bin/sh

set -ev

# To get coverage data with relative paths and not absolute we have to
# execute coveralls from the base directory of the project,
# So we need to move the .coverage file here :
mv test/.coverage .
# In cas of any broken coverage report, one can use the debug mode
# coveralls debug
echo "Submitting coverage results to coveralls.io..."
coveralls -v --rcfile=test/.coveragerc
echo "Submitted"
