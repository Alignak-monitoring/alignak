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
#     Guillaume Bour, guillaume@bour.cc
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe Simon, geektophe@gmail.com
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

"""
This module provide Servicegroup and Servicegroups classes used to group services
"""
import logging

from alignak.property import StringProp, ListProp
from .itemgroup import Itemgroup, Itemgroups

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Servicegroup(Itemgroup):
    """
    Class to manage a servicegroup
    A servicegroup is used to group services
    """
    my_type = 'servicegroup'
    members_property = "members"
    group_members_property = "servicegroup_members"

    properties = Itemgroup.properties.copy()
    properties.update({
        'servicegroup_name':
            StringProp(fill_brok=['full_status']),
        'alias':
            StringProp(default=u'', fill_brok=['full_status']),
        'servicegroup_members':
            ListProp(default=[], fill_brok=['full_status'], merging='join', split_on_comma=True),
        'notes':
            StringProp(default=u'', fill_brok=['full_status']),
        'notes_url':
            StringProp(default=u'', fill_brok=['full_status']),
        'action_url':
            StringProp(default=u'', fill_brok=['full_status']),
    })

    macros = {
        'SERVICEGROUPNAME': 'servicegroup_name',
        'SERVICEGROUPALIAS': 'alias',
        'SERVICEGROUPMEMBERS': 'members',
        'SERVICEGROUPNOTES': 'notes',
        'SERVICEGROUPNOTESURL': 'notes_url',
        'SERVICEGROUPACTIONURL': 'action_url'
    }

    def get_name(self):
        """Get the group name"""
        return getattr(self, 'servicegroup_name', 'Unnamed')

    def get_services(self):
        """Get the services of the group

        :return: list of services (members)
        :rtype: list
        """
        return super(Servicegroup, self).get_members()

    def get_servicegroup_members(self):
        """Get the groups members of the group

        :return: list of services
        :rtype: list | str
        """
        return getattr(self, 'servicegroup_members', [])

    def get_services_by_explosion(self, servicegroups):
        # pylint: disable=access-member-before-definition
        """
        Get all services of this servicegroup and add it in members container

        :param servicegroups: servicegroups object
        :type servicegroups: alignak.objects.servicegroup.Servicegroups
        :return: return empty string or list of members
        :rtype: str or list
        """
        # First we tag the hg so it will not be explode
        # if a son of it already call it
        self.already_exploded = True

        # Now the recursive part
        # rec_tag is set to False every HG we explode
        # so if True here, it must be a loop in HG
        # calls... not GOOD!
        if self.rec_tag:
            logger.error("[servicegroup::%s] got a loop in servicegroup definition",
                         self.get_name())
            if hasattr(self, 'members'):
                return self.members

            return ''
        # Ok, not a loop, we tag it and continue
        self.rec_tag = True

        sg_mbrs = self.get_servicegroup_members()
        for sg_mbr in sg_mbrs:
            servicegroup = servicegroups.find_by_name(sg_mbr.strip())
            if servicegroup is not None:
                value = servicegroup.get_services_by_explosion(servicegroups)
                if value is not None:
                    self.add_members(value)

        if hasattr(self, 'members'):
            return self.members

        return ''


class Servicegroups(Itemgroups):
    """
    Class to manage all servicegroups
    """
    name_property = "servicegroup_name"
    inner_class = Servicegroup

    def add_member(self, service_name, servicegroup_name):
        """Add a member (service) to this servicegroup

        :param service_name: member (service) name
        :type service_name: str
        :param servicegroup_name: servicegroup name
        :type servicegroup_name: str
        :return: None
        """
        servicegroup = self.find_by_name(servicegroup_name)
        if not servicegroup:
            servicegroup = Servicegroup({'servicegroup_name': servicegroup_name,
                                         'alias': servicegroup_name,
                                         'members': service_name})
            self.add(servicegroup)
        else:
            servicegroup.add_members(service_name)

    def get_members_of_group(self, gname):
        """Get all members of a group which name is given in parameter

        :param gname: name of the group
        :type gname: str
        :return: list of the services in the group
        :rtype: list[alignak.objects.service.Service]
        """
        hostgroup = self.find_by_name(gname)
        if hostgroup:
            return hostgroup.get_services()
        return []

    def linkify(self, hosts, services):
        """
        Link services with host

        :param hosts: hosts object
        :type hosts: alignak.objects.host.Hosts
        :param services: services object
        :type services: alignak.objects.service.Services
        :return: None
        """
        self.linkify_servicegroups_services(hosts, services)

    def linkify_servicegroups_services(self, hosts, services):
        """
        We just search for each host the id of the host
        and replace the name by the id
        TODO: very slow for high services, so search with host list,
        not service one

        :param hosts: hosts object
        :type hosts: alignak.objects.host.Hosts
        :param services: services object
        :type services: alignak.objects.service.Services
        :return: None
        """
        for servicegroup in self:
            mbrs = servicegroup.get_services()
            # The new member list, in id
            new_mbrs = []
            seek = 0
            host_name = ''
            if len(mbrs) == 1 and mbrs[0] != '':
                servicegroup.add_unknown_members('%s' % mbrs[0])

            for mbr in mbrs:
                if not mbr:
                    continue
                if seek % 2 == 0:
                    host_name = mbr.strip()
                else:
                    service_desc = mbr.strip()
                    find = services.find_srv_by_name_and_hostname(host_name, service_desc)
                    if find is not None:
                        new_mbrs.append(find.uuid)
                    else:
                        host = hosts.find_by_name(host_name)
                        if not (host and host.is_excluded_for_sdesc(service_desc)):
                            servicegroup.add_unknown_members('%s,%s' % (host_name, service_desc))
                        elif host:
                            self.add_warning('servicegroup %r : %s is excluded from the '
                                             'services of the host %s'
                                             % (servicegroup, service_desc, host_name))
                seek += 1

            # Make members uniq
            new_mbrs = list(set(new_mbrs))

            # We find the id, we replace the names
            servicegroup.replace_members(new_mbrs)
            for srv_id in servicegroup.members:
                serv = services[srv_id]
                serv.servicegroups.append(servicegroup.uuid)
                # and make this uniq
                serv.servicegroups = list(set(serv.servicegroups))

    def explode(self):
        """
        Get services and put them in members container

        :return: None
        """
        # We do not want a same service group to be exploded again and again
        # so we tag it
        for tmp_sg in list(self.items.values()):
            tmp_sg.already_exploded = False

        for servicegroup in list(self.items.values()):
            if servicegroup.already_exploded:
                continue

            # get_services_by_explosion is a recursive
            # function, so we must tag hg so we do not loop
            for tmp_sg in list(self.items.values()):
                tmp_sg.rec_tag = False
            servicegroup.get_services_by_explosion(self)

        # We clean the tags
        for tmp_sg in list(self.items.values()):
            if hasattr(tmp_sg, 'rec_tag'):
                del tmp_sg.rec_tag
            del tmp_sg.already_exploded
