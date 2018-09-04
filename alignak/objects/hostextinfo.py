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
# along with Alignak.  If not, see <http://www.gnu.org  /licenses/>.
#
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     aviau, alexandre.viau@savoirfairelinux.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Romain Forlot, rforlot@yahoo.com

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

""" This is the main class for the Host ext info. In fact it's mainly
about the configuration part. Parameters are merged in Hosts so it's
no use in running part
"""


from alignak.objects.item import Item, Items
from alignak.objects.genericextinfo import GenericExtInfo

from alignak.autoslots import AutoSlots
from alignak.property import StringProp


class HostExtInfo(GenericExtInfo):
    """HostExtInfo class is made to handle some parameters of SchedulingItem::

    * notes
    * notes_url
    * icon_image
    * icon_image_alt

    TODO: Is this class really necessary?

    """
    # AutoSlots create the __slots__ with properties and
    # running_properties names
    __metaclass__ = AutoSlots

    my_type = 'hostextinfo'

    properties = Item.properties.copy()
    properties.update({
        'host_name':
            StringProp(),
        'notes':
            StringProp(default=u''),
        'notes_url':
            StringProp(default=u''),
        'icon_image':
            StringProp(default=u''),
        'icon_image_alt':
            StringProp(default=u''),
        'vrml_image':
            StringProp(default=u''),
        'statusmap_image':
            StringProp(default=u''),

        # No slots for this 2 because begin property by a number seems bad
        # it's stupid!
        '2d_coords':
            StringProp(default=u'', no_slots=True),
        '3d_coords':
            StringProp(default=u'', no_slots=True),
    })

    # Hosts macros and prop that give the information
    # the prop can be callable or not
    macros = {
        'HOSTNAME': 'host_name',
        'HOSTNOTESURL': 'notes_url',
        'HOSTNOTES': 'notes',
    }


class HostsExtInfo(Items):
    """HostsExtInfo manage HostExtInfo and propagate properties (listed before)
    into Hosts if necessary

    """
    name_property = "host_name"
    inner_class = HostExtInfo

    def merge(self, hosts):
        """Merge extended host information into services

        :param hosts: hosts list, to look for a specific one
        :type hosts: alignak.objects.host.Hosts
        :return: None
        """
        for extinfo in self:
            host_name = extinfo.get_name()
            host = hosts.find_by_name(host_name)
            if host is not None:
                # Fusion
                self.merge_extinfo(host, extinfo)

    @staticmethod
    def merge_extinfo(host, extinfo):
        """Merge extended host information into a host

        :param host: the host to edit
        :type host: alignak.objects.host.Host
        :param extinfo: the external info we get data from
        :type extinfo: alignak.objects.hostextinfo.HostExtInfo
        :return: None
        """
        # Note that 2d_coords and 3d_coords are never merged, so not usable !
        properties = ['notes', 'notes_url', 'icon_image', 'icon_image_alt',
                      'vrml_image', 'statusmap_image']
        # host properties have precedence over hostextinfo properties
        for prop in properties:
            if getattr(host, prop) == '' and getattr(extinfo, prop) != '':
                setattr(host, prop, getattr(extinfo, prop))
