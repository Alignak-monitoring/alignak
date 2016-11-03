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
#
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com

#  This file is part of Shinken.
#
#  Shinken is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Shinken is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Shinken.  If not, see <http://www.gnu.org/licenses/>.

"""
This file is to be imported by every Alignak service component:
Arbiter, Scheduler, etc. It just checks for the main requirement of
Alignak.
"""


import sys
from alignak.notification import Notification
from alignak.eventhandler import EventHandler
from alignak.check import Check
from alignak.downtime import Downtime
from alignak.contactdowntime import ContactDowntime
from alignak.comment import Comment
from alignak.objects.module import Module
from ._deprecated_VERSION import DeprecatedAlignakBin


# Make sure people are using Python 2.6 or higher
# This is the canonical python version check
if sys.version_info < (2, 6):
    sys.exit("Alignak requires as a minimum Python 2.6.x, sorry")
elif sys.version_info >= (3,):
    sys.exit("Alignak is not yet compatible with Python 3.x, sorry")

# in order to have available any attribute/value assigned in this module namespace,
# this MUST be the last statement of this module:
sys.modules[__name__] = DeprecatedAlignakBin(__name__, globals())
