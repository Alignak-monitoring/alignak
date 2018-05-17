#!/usr/bin/env bash
#
# Copyright (C) 2015-2018: Alignak team, see AUTHORS.txt file for contributors
#
# This file is part of Alignak.
#
# Alignak is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Alignak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Alignak.  If not, see <http://www.gnu.org/licenses/>.

echo 'pycodestyle ...'
pycodestyle --max-line-length=100 --exclude='*.pyc' alignak/*
if [ $? -ne 0 ]; then
    echo "pycodestyle not compliant"
    exit
fi
echo 'pylint ...'
pylint --rcfile=.pylintrc -r no alignak
if [ $? -ne 0 ]; then
    echo "pylint not compliant"
    exit
fi
echo 'pep157 ...'
pep257 --select=D300 alignak
if [ $? -ne 0 ]; then
    echo "pep257 not compliant"
    exit
fi

echo 'tests ...'
cd test
pytest --verbose --durations=10 --no-print-logs --cov=alignak --cov-report term-missing --cov-config .coveragerc test_*.py || travis_terminate 1;
cd ..
