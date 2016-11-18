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

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Servicegroup(Itemgroup):
    """
    Class to manage a servicegroup
    A servicegroup is used to group services
    """
    name_property = "servicegroup_name"
    members_property = "members"
    groupmembers_property = "servicegroup_members"
    my_type = 'servicegroup'

    properties = Itemgroup.properties.copy()
    properties.update({
        # 'uuid':                 StringProp(default='', fill_brok=['full_status']),
        'servicegroup_name':
            StringProp(fill_brok=['full_status']),
        'servicegroup_members':
            ListProp(default=[], fill_brok=['full_status'], merging='join'),
        'notes':
            StringProp(default='', fill_brok=['full_status']),
        'notes_url':
            StringProp(default='', fill_brok=['full_status']),
        'action_url':
            StringProp(default='', fill_brok=['full_status']),
    })

    macros = {
        'SERVICEGROUPALIAS': 'alias',
        'SERVICEGROUPMEMBERS': 'get_members',
        'SERVICEGROUPNOTES': 'notes',
        'SERVICEGROUPNOTESURL': 'notes_url',
        'SERVICEGROUPACTIONURL': 'action_url'
    }

    def __init__(self, params=None, parsing=True, debug=False):

        if params is None:
            params = {}
        super(Servicegroup, self).__init__(params, parsing=parsing, debug=debug)

        logger.debug("SG %s %s, members: %s, group members: %s",
                     parsing, self.get_name(), self.get_members(), self.get_group_members())
        if parsing:
            # Manage the specific format of members property
            # List containing host_name,service_description for each service (h1,s1,h2,s2,...)
            # Transform this list to a list of strings: [h1/s1, h2/s2,...]
            seek = 0
            host_name = ''
            new_members = []
            for member in self.get_members():
                if seek % 2 == 0:
                    host_name = member
                else:
                    new_members.append("%s/%s" % (host_name, member))
                seek += 1

            if new_members:
                self.members = new_members
            logger.debug("SG %s, members: %s", self.get_name(), self.get_members())

    def get_services(self):
        """
        Get services of this servicegroup

        :return: list of services (members)
        :rtype: list
        """
        return self.get_members()

    def get_servicegroup_members(self):
        """
        Get list of members of this servicegroup

        :return: list of services
        :rtype: list | str
        """
        return self.get_group_members()

    def get_services_by_explosion(self, servicegroups, services):
        """
        Get direct services of this group and all services from the sub-groups.
        Append sub-groups members to the members of this group

        :param servicegroups: servicegroups object
        :type servicegroups: alignak.objects.servicegroup.Servicegroups
        :param services: services to explode
        :type services: alignak.objects.service.Services
        :return: return the list of members
        :rtype: list[alignak.objects.service.Service]
        """
        # First we tag the group so it will not be exploded again if one of its members calls it
        self.already_exploded = True

        # Now the recursive part
        # recursion_tag is set to False for every group we explode
        # so if is True here, it must be a loop in the groups links... not GOOD!
        if self.recursion_tag:
            err = "[%s::%s] got a loop in %s definition" % \
                  (self.my_type, self.get_name(), self.groupmembers_property)
            self.configuration_errors.append(err)
            return self.get_members()

        # Ok, not in a loop, we tag it and continue
        self.recursion_tag = True

        group_members = self.get_group_members()
        for group_member in group_members:
            servicegroup = servicegroups.find_by_name(group_member)
            if servicegroup is not None:
                members_uuid = servicegroup.get_services_by_explosion(servicegroups, services)
                if members_uuid:
                    new_members = []
                    for member_uuid in members_uuid:
                        if member_uuid in services:
                            new_members.append(services[member_uuid])
                    self.add_members(new_members)

        logger.debug("SG %s, after explosion members: %s", self.get_name(), self.get_members())
        return self.get_members()


class Servicegroups(Itemgroups):
    """
    Class to manage all servicegroups
    """
    inner_class = Servicegroup

    def linkify(self, hosts, services):
        """
        Link services with host

        :param hosts: hosts object
        :type hosts: object
        :param services: services object
        :type services: object
        :return: None
        """
        self.linkify_servicegroup_by_service(hosts, services)

    def linkify_servicegroup_by_service(self, hosts, services):
        """
        We just search for each host the id of the host
        and replace the name by the id

        TODO: very slow for high services, so search with host list, not service one

        :param hosts: hosts object
        :type hosts: alignak.objects.host.Hosts
        :param services: services object
        :type services: alignak.objects.service.Services
        :return: None
        """
        logger.debug("Linkify servicegroups and services")
        for servicegroup in self.items.values():
            members = servicegroup.get_services()
            logger.debug("- SG: %s, members: %s", servicegroup, members)
            # The new member list, in id
            new_members = []

            # Group members is an array of string formatted as is: host_name/service_descrption
            for member in members:
                member = member.strip()
                if member == '':  # void entry, skip this
                    continue
                elif member in services:
                    # We got a service uuid
                    logger.debug("SG: %s, found a service: %s", servicegroup, services[member])
                    new_members.append(member)

                    # Update the found service servicegroups property and make it uniquified
                    services[member].servicegroups.append(servicegroup.uuid)
                    services[member].servicegroups = list(set(services[member].servicegroups))
                elif '/' in member:
                    # We got a host_name/service_description string
                    host_name = member.split('/')[0]
                    service_description = member.split('/')[1]
                    service = services.find_srv_by_name_and_hostname(host_name, service_description)
                    if service is not None:
                        logger.debug("SG: %s, found a service: %s", servicegroup, service)
                        new_members.append(service.uuid)

                        # Update the found service servicegroups property and make it uniquified
                        service.servicegroups.append(servicegroup.uuid)
                        service.servicegroups = list(set(service.servicegroups))
                    else:
                        host = hosts.find_by_name(host_name)
                        if not (host and host.is_excluded_for_sdesc(service_description)):
                            # A not found host/service is stored in unknown_members
                            servicegroup.add_unknown_member("%s/%s" % (host_name,
                                                                       service_description))
                        elif host:
                            self.configuration_warnings.append(
                                'servicegroup %r : %s is excluded from the services of the host %s'
                                % (servicegroup, service_description, host_name)
                            )

            if new_members:
                new_members = list(set(new_members))
                logger.debug("SG: %s, new members: %s", servicegroup, new_members)

                # We update the group members
                servicegroup.members = new_members

    def add_group_member(self, service, servicegroup_name):
        """Add a service to a servicegroup.
        If the servicegroup does not exist it is created

        :param service: service unique identifier
        :type service: uuid
        :param servicegroup_name: servicegroup name
        :type servicegroup_name: str
        :return: None
        """
        servicegroup = self.find_by_name(servicegroup_name)
        if servicegroup is None:
            # Create the group if it does not yet exist
            print("Create SG: %s" % servicegroup_name)
            servicegroup = Servicegroup({'servicegroup_name': servicegroup_name,
                                         'members': [service.get_name()],
                                         'imported_from': 'inner'})
            logger.debug("Created a servicegroup declared in a service: %s / %s" %
                         (servicegroup_name, servicegroup.members))
            self.add_item(servicegroup)
        else:
            servicegroup.add_member(service)

    def explode(self, services):
        """
        Populate the members property with the group members and the members of the sub-groups

        :param services: services to explode
        :type services: alignak.objects.service.Services
        :return: None
        """
        for servicegroup in self.items.values():
            for groupmember in servicegroup.get_group_members():
                group = self.find_by_name(groupmember)
                if group is None:
                    continue
                if group.already_exploded:
                    continue

                # get_services_by_explosion is a recursive function, so we must
                # tag the groups to avoid looping indefinetely
                for groupmember in self.items.values():
                    groupmember.recursion_tag = False
                servicegroup.get_services_by_explosion(self, services)

        # Clean the recursion tag
        for servicegroup in self.items.values():
            if hasattr(servicegroup, 'recursion_tag'):
                del servicegroup.recursion_tag
