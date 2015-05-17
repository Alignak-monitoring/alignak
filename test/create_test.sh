#!/bin/bash
#
# Copyright (C) 2015-2015: Alignak team, see AUTHORS.txt file for contributors
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

NAME=$1
echo "Creating a test from dummy with 1 router, one host and 1 service to " $1

cp test_dummy.py test_$1.py
cp etc/alignak_1r_1h_1s.cfg etc/alignak_$1.cfg
cp -r etc/1r_1h_1s etc/$1
sed "s/1r_1h_1s/$1/" etc/alignak_$1.cfg -i
sed "s/1r_1h_1s/$1/" test_$1.py -i

echo "Test creation succeed"
