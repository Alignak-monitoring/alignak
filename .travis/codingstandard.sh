#!/bin/sh

set -ev

pep8 --max-line-length=100 --exclude='*.pyc' alignak/*
unset PYTHONWARNINGS
pylint --rcfile=.pylintrc -r no alignak
export PYTHONWARNINGS=all
pep257 --select=D300 alignak
