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

""" This is the main class for the Service ext info. In fact it's mainly
about the configuration part. Parameters are merged in Service so it's
no use in running part
"""


from alignak.objects.item import Item, Items
from alignak.objects.genericextinfo import GenericExtInfo

from alignak.autoslots import AutoSlots
from alignak.property import StringProp


class ServiceExtInfo(GenericExtInfo):
    """ServiceExtInfo class is made to handle some parameters of SchedulingItem::

    * notes
    * notes_url
    * icon_image
    * icon_image_alt

    TODO: Is this class really necessary?

    """
    # AutoSlots create the __slots__ with properties and
    # running_properties names
    __metaclass__ = AutoSlots

    my_type = 'serviceextinfo'

    # properties defined by configuration
    # *required: is required in conf
    # *default: default value if no set in conf
    # *pythonize: function to call when transforming string to python object
    # *fill_brok: if set, send to broker. there are two categories:
    #   full_status for initial and update status, check_result for check results
    # *no_slots: do not take this property for __slots__
    #  Only for the initial call
    # conf_send_preparation: if set, will pass the property to this function. It's used to "flatten"
    #  some dangerous properties like realms that are too 'linked' to be send like that.
    # brok_transformation: if set, will call the function with the value of the property
    #  the major times it will be to flatten the data (like realm_name instead of the realm object).
    properties = Item.properties.copy()
    properties.update({
        'host_name':
            StringProp(),
        'service_description':
            StringProp(),
        'notes':
            StringProp(default=u''),
        'notes_url':
            StringProp(default=u''),
        'icon_image':
            StringProp(default=u''),
        'icon_image_alt':
            StringProp(default=u''),
    })

    # Hosts macros and prop that give the information
    # the prop can be callable or not
    macros = {
        'SERVICEDESC': 'service_description',
        'SERVICEACTIONURL': 'action_url',
        'SERVICENOTESURL': 'notes_url',
        'SERVICENOTES': 'notes'
    }


class ServicesExtInfo(Items):
    """ServicesExtInfo manage ServiceExtInfo and propagate properties (listed before)
    into Services if necessary

    """
    name_property = "host_name"
    inner_class = ServiceExtInfo

    def merge(self, services):
        """Merge extended host information into services

        :param services: services list, to look for a specific one
        :type services: alignak.objects.service.Services
        :return: None
        """
        for extinfo in self:
            if hasattr(extinfo, 'register') and not getattr(extinfo, 'register'):
                # We don't have to merge template
                continue
            hosts_names = extinfo.get_name().split(",")
            for host_name in hosts_names:
                serv = services.find_srv_by_name_and_hostname(host_name,
                                                              extinfo.service_description)
                if serv is not None:
                    # Fusion
                    self.merge_extinfo(serv, extinfo)

    @staticmethod
    def merge_extinfo(service, extinfo):
        """Merge extended host information into a service

        :param service: the service to edit
        :type service: alignak.objects.service.Service
        :param extinfo: the external info we get data from
        :type extinfo: alignak.objects.serviceextinfo.ServiceExtInfo
        :return: None
        """
        properties = ['notes', 'notes_url', 'icon_image', 'icon_image_alt']
        # service properties have precedence over serviceextinfo properties
        for prop in properties:
            if getattr(service, prop) == '' and getattr(extinfo, prop) != '':
                setattr(service, prop, getattr(extinfo, prop))
