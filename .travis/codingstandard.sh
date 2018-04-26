#!/bin/sh

set -ev

# Static code analysis
# -- pycodestyle (former pep8)
# Exclude the dictconfig.py vendor file
pycodestyle --max-line-length=100 --exclude='*.pyc,alignak/misc/dictconfig.py' alignak/*
# -- pylint
unset PYTHONWARNINGS
pylint --rcfile=.pylintrc -r no alignak
export PYTHONWARNINGS=all
# -- pep257
pep257 --select=D300 alignak
