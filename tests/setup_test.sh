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

# Create alignak user/group for test purpose
sudo addgroup --system alignak
sudo adduser --system alignak --ingroup alignak

# Create alignak default directories
sudo mkdir -p /usr/local/var/log/alignak/monitoring-log
sudo mkdir -p /usr/local/var/run/alignak

# Install application AND tests requirements :
pip install --upgrade -r tests/requirements.txt
pip install -e .
