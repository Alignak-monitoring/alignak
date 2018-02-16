# -*- coding: utf-8 -*-

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

""" This is the main class for the generic ext info. In fact it's mainly
about the configuration part. Parameters are merged in Host or Service so it's
no use in running part
"""
from alignak.objects.item import Item


class GenericExtInfo(Item):
    """GenericExtInfo class is made to handle some parameters of SchedulingItem::

    * notes
    * notes_url
    * icon_image
    * icon_image_alt

    """

#######
#                   __ _                       _   _
#                  / _(_)                     | | (_)
#   ___ ___  _ __ | |_ _  __ _ _   _ _ __ __ _| |_ _  ___  _ __
#  / __/ _ \| '_ \|  _| |/ _` | | | | '__/ _` | __| |/ _ \| '_ \
# | (_| (_) | | | | | | | (_| | |_| | | | (_| | |_| | (_) | | | |
#  \___\___/|_| |_|_| |_|\__, |\__,_|_|  \__,_|\__|_|\___/|_| |_|
#                         __/ |
#                        |___/
######

    def get_name(self):
        """Accessor to host_name attribute or name if first not defined

        :return: host name, use to search the host to merge
        :rtype: str
        """
        return getattr(self, 'host_name', getattr(self, 'name', 'UNKNOWN'))
