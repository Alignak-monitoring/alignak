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

    properties = Itemgroup.properties.copy()
    properties.update({
        # 'uuid':
        #     StringProp(fill_brok=['full_status']),
        'servicegroup_name':
            StringProp(fill_brok=['full_status']),
        'alias':
            StringProp(fill_brok=['full_status']),
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
        'SERVICEGROUPALIAS':     'alias',
        'SERVICEGROUPMEMBERS':   'members',
        'SERVICEGROUPNOTES':     'notes',
        'SERVICEGROUPNOTESURL':  'notes_url',
        'SERVICEGROUPACTIONURL': 'action_url'
    }

    def get_services(self):
        """
        Get services of this servicegroup

        :return: list of services (members)
        :rtype: list
        """
        if getattr(self, 'members', None) is not None:
            return self.members

        return []

    def get_name(self):
        """
        Get list of groups members of this servicegroup

        :return: the servicegroup name string
        :rtype: str
        """
        return self.servicegroup_name

    def get_servicegroup_members(self):
        """
        Get list of members of this servicegroup

        :return: list of services
        :rtype: list | str
        """
        if hasattr(self, 'servicegroup_members'):
            return self.servicegroup_members

        return []

    def get_services_by_explosion(self, servicegroups):
        # pylint: disable=access-member-before-definition
        """
        Get all services of this servicegroup and add it in members container

        :param servicegroups: servicegroups object
        :type servicegroups: object
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
                    self.add_string_member(value)

        if hasattr(self, 'members'):
            return self.members

        return ''


class Servicegroups(Itemgroups):
    """
    Class to manage all servicegroups
    """
    name_property = "servicegroup_name"  # is used for finding servicegroup
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
        self.linkify_sg_by_srv(hosts, services)

    def linkify_sg_by_srv(self, hosts, services):
        """
        We just search for each host the id of the host
        and replace the name by the id
        TODO: very slow for high services, so search with host list,
        not service one

        :param hosts: hosts object
        :type hosts: object
        :param services: services object
        :type services: object
        :return: None
        """
        for servicegroup in self:
            mbrs = servicegroup.get_services()
            # The new member list, in id
            new_mbrs = []
            seek = 0
            host_name = ''
            if len(mbrs) == 1 and mbrs[0] != '':
                servicegroup.add_string_unknown_member('%s' % mbrs[0])

            for mbr in mbrs:
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
                            servicegroup.add_string_unknown_member('%s,%s' %
                                                                   (host_name, service_desc))
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

    def add_member(self, cname, sgname):
        """
        Add a member (service) to this servicegroup

        :param cname: member (service) name
        :type cname: str
        :param sgname: servicegroup name
        :type sgname: str
        :return: None
        """
        svcgp = self.find_by_name(sgname)
        # if the id do not exist, create the cg
        if svcgp is None:
            svcgp = Servicegroup({'servicegroup_name': sgname, 'alias': sgname, 'members': cname})
            self.add(svcgp)
        else:
            svcgp.add_string_member(cname)

    def explode(self):
        """
        Get services and put them in members container

        :return: None
        """
        # We do not want a same service group to be exploded again and again
        # so we tag it
        for servicegroup in list(self.items.values()):
            servicegroup.already_exploded = False

        for servicegroup in list(self.items.values()):
            if hasattr(servicegroup, 'servicegroup_members') and not \
                    servicegroup.already_exploded:
                # get_services_by_explosion is a recursive
                # function, so we must tag hg so we do not loop
                for sg2 in list(self.items.values()):
                    sg2.rec_tag = False
                servicegroup.get_services_by_explosion(self)

        # We clean the tags
        for servicegroup in list(self.items.values()):
            try:
                del servicegroup.rec_tag
            except AttributeError:
                pass
            del servicegroup.already_exploded
