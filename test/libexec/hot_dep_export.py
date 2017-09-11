#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

import os
import sys
try:
    import json
except ImportError:
    # For old Python version, load
    # simple json (it can be hard json?! It's 2 functions guy!)
    try:
        import simplejson as json
    except ImportError:
        print "Error: you need the json or simplejson module for this script"
        sys.exit(0)

print "Argv", sys.argv

# Case 1 mean host0 is the father of host1
if sys.argv[1] == 'case1':
    d = [[["host", "test_host_0"], ["host", "test_host_1"]]]
if sys.argv[1] == 'case2':
    d = [[["host", "test_host_2"], ["host", "test_host_1"]]]

f = open(sys.argv[2], 'wb')
f.write(json.dumps(d))
f.close()
