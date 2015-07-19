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

"""alignak.satellitelink is deprecated. Please use alignak.objects.satellitelink now."""

from alignak.old_daemon_link import deprecation, make_deprecated
"""TODO: make_deprecated is not found"""

deprecation(__doc__)

from alignak.objects.satellitelink import (
    SatelliteLink,
    SatelliteLinks,
)

SatelliteLink = make_deprecated(SatelliteLink)
SatelliteLinks = make_deprecated(SatelliteLinks)
