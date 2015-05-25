#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  Copyright (C) 2015-2015: Alignak team, see AUTHORS.txt file for contributors
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

from __future__ import absolute_import

import sys

# importlib was introduced in 2.7. It is also available as a backport
if sys.version_info[:2] < (2, 7):
    try:  # try to import the system-wide backported module
        from importlib import *
    except ImportError:  # load our bundled backported module
        from ._importlib import *
else:
    from importlib import *
