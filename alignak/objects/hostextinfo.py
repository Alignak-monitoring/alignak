# -*- coding: utf-8 -*-

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

from alignak.autoslots import AutoSlots
from alignak.property import StringProp


class HostExtInfo(Item):
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

    _id = 1  # zero is reserved for host (primary node for parents)
    my_type = 'hostextinfo'

    # properties defined by configuration
    # *required: is required in conf
    # *default: default value if no set in conf
    # *pythonize: function to call when transforming string to python object
    # *fill_brok: if set, send to broker.
    #             there are two categories:
    #                   full_status for initial and update status, check_result for check results
    # *no_slots: do not take this property for __slots__
    #  Only for the initial call
    # conf_send_preparation: if set, will pass the property to this function. It's used to "flatten"
    #  some dangerous properties like realms that are too 'linked' to be send like that.
    # brok_transformation: if set, will call the function with the value of the property
    #  the major times it will be to flatten the data (like realm_name instead of the realm object).
    properties = Item.properties.copy()
    properties.update({
        'host_name':            StringProp(),
        'notes':                StringProp(default=''),
        'notes_url':            StringProp(default=''),
        'icon_image':           StringProp(default=''),
        'icon_image_alt':       StringProp(default=''),
        'vrml_image':           StringProp(default=''),
        'statusmap_image':      StringProp(default=''),

        # No slots for this 2 because begin property by a number seems bad
        # it's stupid!
        '2d_coords':            StringProp(default='', no_slots=True),
        '3d_coords':            StringProp(default='', no_slots=True),
    })

    # Hosts macros and prop that give the information
    # the prop can be callable or not
    macros = {
        'HOSTNAME':          'host_name',
        'HOSTNOTESURL':      'notes_url',
        'HOSTNOTES':         'notes',
    }

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

    def is_correct(self):
        """
        Check if this object is correct

        :return: True, always.
        :rtype: bool
        TODO: Clean this function
        """
        state = True
        cls = self.__class__

        return state

    def get_name(self):
        """Accessor to host_name attribute or name if first not defined

        :return: host name or name
        :rtype: str
        TODO: Clean this function
        """
        if not self.is_tpl():
            try:
                return self.host_name
            except AttributeError:  # outch, no hostname
                return 'UNNAMEDHOST'
        else:
            try:
                return self.name
            except AttributeError:  # outch, no name for this template
                return 'UNNAMEDHOSTTEMPLATE'

    def get_dbg_name(self):
        """Get the host name for debugging (host_name)

        :return: service extinfo  host name
        :rtype: str
        TODO: Remove this function, get_name is doing it
        """
        return self.host_name

    def get_full_name(self):
        """Get the full name for debugging (host_name)

        :return: service extinfo  host name
        :rtype: str
        TODO: Remove this function, get_name is doing it
        """
        return self.host_name


class HostsExtInfo(Items):
    """HostsExtInfo manage HostExtInfo and propagate properties (listed before)
    into Hosts if necessary

    """
    name_property = "host_name"  # use for the search by name
    inner_class = HostExtInfo  # use for know what is in items

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
                # FUUUUUUUUUUsion
                self.merge_extinfo(host, extinfo)

    def merge_extinfo(self, host, extinfo):
        """Merge extended host information into a host

        :param host: the host to edit
        :type hosts: alignak.objects.host.Host
        :param extinfo: the external info we get data from
        :type extinfo: alignak.objects.hostextinfo.HostExtInfo
        :return: None
        """
        properties = ['notes',
                      'notes_url',
                      'icon_image',
                      'icon_image_alt',
                      'vrml_image',
                      'statusmap_image']
        # host properties have precedence over hostextinfo properties
        for prop in properties:
            if getattr(host, prop) == '' and getattr(extinfo, prop) != '':
                setattr(host, prop, getattr(extinfo, prop))
