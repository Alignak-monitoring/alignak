#!/usr/bin/env bash
#
# Copyright (C) 2015-2016: Alignak team, see AUTHORS.txt file for contributors
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

set -e

THIS_PATH=$(dirname "$0")
BASE_PATH=$(dirname "$THIS_PATH")

cd $BASE_PATH

pip install --upgrade pip

# install prog AND tests requirements :
pip install -e .
pip install alignak-setup
pip install --upgrade -r test/requirements.txt

pyversion=$(python -c "import sys; print(''.join(map(str, sys.version_info[:2])))")
if test -e "test/requirements.py${pyversion}.txt"
then
    pip install -r "test/requirements.py${pyversion}.txt"
fi
