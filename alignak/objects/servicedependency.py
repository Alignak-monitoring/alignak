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
#     Arthur Gautier, superbaloo@superbaloo.net
#     aviau, alexandre.viau@savoirfairelinux.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Grégory Starck, g.starck@gmail.com
#     Alexander Springer, alex.spri@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Romain Forlot, rforlot@yahoo.com
#     Romain THERRAT, romain42@gmail.com

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
"""This module provides Servicedependency and Servicedependencies classes that
implements dependencies between services. Basically used for parsing.

"""
import logging
from alignak.property import BoolProp, StringProp, ListProp

from .item import Item, Items

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Servicedependency(Item):
    """Servicedependency class is a simple implementation of service dependency as
    defined in a monitoring context (dependency period, notification_failure_criteria ..)

    """
    my_type = "servicedependency"
    my_name_property = "service_relation"
    my_index_property = "service_relation"

    properties = Item.properties.copy()
    properties.update({
        'dependent_host_name':
            StringProp(),
        'dependent_hostgroup_name':
            StringProp(default=''),
        'dependent_service_description':
            StringProp(),
        'host_name':
            StringProp(),
        'hostgroup_name':
            StringProp(default=''),
        'service_description':
            StringProp(),
        'inherits_parent':
            BoolProp(default=False),
        'execution_failure_criteria':
            ListProp(default=['n'], split_on_comma=True),
        'notification_failure_criteria':
            ListProp(default=['n'], split_on_comma=True),
        'dependency_period':
            StringProp(default=''),
        'explode_hostgroup':
            BoolProp(default=False)
    })

    # def __str__(self):  # pragma: no cover
    #     return '<Servicedependency %s %s, uuid=%s, use: %s />' \
    #            % ('template' if self.is_a_template() else '', self.get_full_name(), self.uuid,
    #               getattr(self, 'use', None))
    # __repr__ = __str__

    @property
    def service_relation(self):
        """Unique key for a service dependency

        :return: Tuple with host_name/service and dependent_host_name/service
        :rtype: tuple
        """
        return "{}/{}->{}/{}".format(getattr(self, 'host_name', 'unknown'),
                                     getattr(self, 'service_description', 'unknown'),
                                     getattr(self, 'dependent_host_name', 'independant'),
                                     getattr(self, 'dependent_service_description', 'unknown'))

    def get_full_name(self):
        """Get name based on 4 class attributes
        Each attribute is replaced with 'unknown' if attribute is not set

        :return: dependent_host_name/dependent_service_description..host_name/service_description
        :rtype: str
        """
        if self.is_a_template():
            return self.get_name()
        return "{}/{}->{}/{}".format(getattr(self, 'host_name', 'unknown'),
                                     getattr(self, 'service_description', 'unknown'),
                                     getattr(self, 'dependent_host_name', 'independant'),
                                     getattr(self, 'dependent_service_description', 'unknown'))


class Servicedependencies(Items):
    """Servicedependencies manage a list of Servicedependency objects,
       used for parsing configuration

    """
    inner_class = Servicedependency

    def delete_svc_dep_by_id(self, ids):
        """Delete a list of servicedependency

        :param ids: ids list to delete
        :type ids: list
        :return: None
        """
        for s_id in ids:
            del self[s_id]

    def add_service_dependency(self, dep_host_name, dep_service_description,
                               par_host_name, par_service_description):
        """Instantiate and add a Servicedependency object to the items dict::

        * notification criteria is "u,c,w"
        * inherits_parent is True

        :param dep_host_name: dependent host name
        :type dep_host_name: str
        :param dep_service_description: dependent service description
        :type dep_service_description: str
        :param par_host_name: host name
        :type par_host_name: str
        :param par_service_description: service description
        :type par_service_description: str
        :return: None
        """
        # We create a "standard" service_dep
        params = {
            'host_name': par_host_name,
            'service_description': par_service_description,
            'dependent_host_name': dep_host_name,
            'dependent_service_description': dep_service_description,
            'notification_failure_criteria': 'u,c,w',
            'inherits_parent': '1'
        }
        self.add_item(Servicedependency(params))

    def explode_hostgroup(self, svc_dep, hostgroups):
        # pylint: disable=too-many-locals
        """Explode a service dependency for each member of hostgroup

        :param svc_dep: service dependency to explode
        :type svc_dep: alignak.objects.servicedependency.Servicedependency
        :param hostgroups: used to find hostgroup objects
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :return:None
        """
        # We will create a service dependency for each host part of the host group

        # First get services
        snames = [d.strip() for d in svc_dep.service_description.split(',')]

        # And dep services
        dep_snames = [d.strip() for d in svc_dep.dependent_service_description.split(',')]

        # Now for each host into hostgroup we will create a service dependency object
        hg_names = [n.strip() for n in svc_dep.hostgroup_name.split(',')]
        for hg_name in hg_names:
            hostgroup = hostgroups.find_by_name(hg_name)
            if hostgroup is None:
                err = "ERROR: the servicedependecy got an unknown hostgroup_name '%s'" % hg_name
                self.add_error(err)
                continue
            hnames = []
            hnames.extend([m.strip() for m in hostgroup.get_hosts()])
            for hname in hnames:
                for dep_sname in dep_snames:
                    for sname in snames:
                        new_sd = svc_dep.copy()
                        new_sd.host_name = hname
                        new_sd.service_description = sname
                        new_sd.dependent_host_name = hname
                        new_sd.dependent_service_description = dep_sname
                        self.add_item(new_sd)

    def explode(self, hostgroups):
        # pylint: disable=too-many-locals, too-many-branches
        """Explode all service dependency for each member of hostgroups
        Each member of dependent hostgroup or hostgroup in dependency have to get a copy of
        service dependencies (quite complex to parse)

        :param hostgroups: used to look for hostgroup
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :return: None
        """
        # The "old" services will be removed. All services with
        # more than one host or a host group will be in it
        to_be_removed = []

        # Then for every host create a copy of the service with just the host
        # because we are adding services, we can't just loop in it
        for svc_dep_id in list(self.items.keys()):
            svc_dep = self.items[svc_dep_id]

            # First case: we only have to propagate the services dependencies to
            # all the hosts of some hostgroups
            # Either a specific property is defined (Shinken/Alignak) or
            # no dependent hosts groups is defined
            if getattr(svc_dep, 'explode_hostgroup', '0') == '1' or \
                    (hasattr(svc_dep, 'hostgroup_name') and
                     not hasattr(svc_dep, 'dependent_hostgroup_name')):
                self.explode_hostgroup(svc_dep, hostgroups)
                to_be_removed.append(svc_dep_id)
                continue

            # Get the list of all FATHER hosts and service dependencies
            father_hosts = []
            if getattr(svc_dep, 'host_name', ''):
                father_hosts.extend([h.strip() for h in svc_dep.host_name.split(',')])

            if getattr(svc_dep, 'hostgroup_name', ''):
                hg_names = [g.strip() for g in svc_dep.hostgroup_name.split(',')]
                for hg_name in hg_names:
                    hostgroup = hostgroups.find_by_name(hg_name)
                    if hostgroup is None:
                        hostgroup.add_error("A servicedependecy got an unknown "
                                            "hostgroup_name '%s'" % hg_name)
                        continue
                    father_hosts.extend([m.strip() for m in hostgroup.get_hosts()])

            services = []
            if getattr(svc_dep, 'service_description', ''):
                services = [s.strip() for s in svc_dep.service_description.split(',')]

            couples = []
            for host_name in father_hosts:
                for service_description in services:
                    couples.append((host_name, service_description))

            if not hasattr(svc_dep, 'dependent_hostgroup_name') \
                    and hasattr(svc_dep, 'hostgroup_name'):
                svc_dep.dependent_hostgroup_name = svc_dep.hostgroup_name

            # Now the dependent part (the sons)
            son_hosts = []
            if getattr(svc_dep, 'dependent_hostgroup_name', ''):
                hg_names = [g.strip() for g in svc_dep.dependent_hostgroup_name.split(',')]
                for hg_name in hg_names:
                    hostgroup = hostgroups.find_by_name(hg_name)
                    if hostgroup is None:
                        hostgroup.add_error("A servicedependecy got an unknown "
                                            "dependent_hostgroup_name '%s'" % hg_name)
                        continue
                    son_hosts.extend([m.strip() for m in hostgroup.get_hosts()])

            if not hasattr(svc_dep, 'dependent_host_name'):
                svc_dep.dependent_host_name = getattr(svc_dep, 'host_name', '')
            if getattr(svc_dep, 'dependent_host_name', ''):
                son_hosts.extend([h.strip() for h in svc_dep.dependent_host_name.split(',')])

            dep_snames = [s.strip() for s in svc_dep.dependent_service_description.split(',')]
            dep_couples = []
            for dep_hname in son_hosts:
                for dep_sname in dep_snames:
                    dep_couples.append((dep_hname.strip(), dep_sname.strip()))

            # Create the new service dependencies from all this stuff
            for (dep_hname, dep_sname) in dep_couples:  # the sons, like HTTP
                for (host_name, service_description) in couples:  # the fathers, like MySQL
                    new_sd = svc_dep.copy()
                    new_sd.host_name = host_name
                    new_sd.service_description = service_description
                    new_sd.dependent_host_name = dep_hname
                    new_sd.dependent_service_description = dep_sname
                    self.add_item(new_sd)
                # Ok so we can remove the old one
                to_be_removed.append(svc_dep_id)

        self.delete_svc_dep_by_id(to_be_removed)

    def linkify(self, hosts, services, timeperiods):
        """Create link between objects::

         * servicedependency -> host
         * servicedependency -> service
         * servicedependency -> timeperiods

        :param hosts: hosts to link
        :type hosts: alignak.objects.host.Hosts
        :param services: services to link
        :type services: alignak.objects.service.Services
        :param timeperiods: timeperiods to link
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: None
        """
        self.linkify_svc_dep_by_service(hosts, services)
        self.linkify_svc_dep_by_timeperiod(timeperiods)
        self.linkify_service_by_svc_dep(services)

    def linkify_svc_dep_by_service(self, hosts, services):
        """Replace dependent_service_description and service_description
        in service dependency by the real object

        :param hosts: host list, used to look for a specific one
        :type hosts: alignak.objects.host.Hosts
        :param services: service list to look for a specific one
        :type services: alignak.objects.service.Services
        :return: None
        """
        to_del = []
        for svc_dep in self:
            try:
                s_name = svc_dep.dependent_service_description
                hst_name = svc_dep.dependent_host_name

                # The new member list, in id
                service = services.find_srv_by_name_and_hostname(hst_name, s_name)
                if service is None:
                    host = hosts.find_by_name(hst_name)
                    if not (host and host.is_excluded_for_sdesc(s_name)):
                        self.add_error("Service %s not found for host %s" % (s_name, hst_name))
                    elif host:
                        self.add_warning("Service %s is excluded from host %s ; "
                                         "removing this service dependency as it's unusable."
                                         % (s_name, hst_name))
                    to_del.append(svc_dep)
                    continue
                svc_dep.dependent_service_description = service.uuid

                s_name = svc_dep.service_description
                hst_name = svc_dep.host_name

                # The new member list, in id
                service = services.find_srv_by_name_and_hostname(hst_name, s_name)
                if service is None:
                    host = hosts.find_by_name(hst_name)
                    if not (host and host.is_excluded_for_sdesc(s_name)):
                        self.add_error("Service %s not found for host %s" % (s_name, hst_name))
                    elif host:
                        self.add_warning("Service %s is excluded from host %s ; "
                                         "removing this service dependency as it's unusable."
                                         % (s_name, hst_name))
                    to_del.append(svc_dep)
                    continue
                svc_dep.service_description = service.uuid

            except AttributeError as err:
                logger.error("[servicedependency] fail to linkify by service %s: %s",
                             svc_dep, err)
                to_del.append(svc_dep)

        for svc_dep in to_del:
            self.remove_item(svc_dep)

    def linkify_svc_dep_by_timeperiod(self, timeperiods):
        """Replace dependency_period by a real object in service dependency

        :param timeperiods: list of timeperiod, used to look for a specific one
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: None
        """
        for svc_dep in self:
            try:
                svc_dep.dependency_period = ''
                timeperiod = timeperiods.find_by_name(svc_dep.dependency_period)
                if timeperiod:
                    svc_dep.dependency_period = timeperiod.uuid
            except AttributeError as exp:
                logger.error("[servicedependency] fail to linkify by timeperiods: %s", exp)

    def linkify_service_by_svc_dep(self, services):
        """Add dependency in service objects

        :return: None
        """
        for svc_dep in self:
            # Only used for debugging purpose when loops are detected
            setattr(svc_dep, "service_description_string", "undefined")
            setattr(svc_dep, "dependent_service_description_string", "undefined")

            if getattr(svc_dep, 'service_description', None) is None:
                continue

            if getattr(svc_dep, 'dependent_service_description', None) is None:
                continue

            services.add_act_dependency(svc_dep.dependent_service_description,
                                        svc_dep.service_description,
                                        svc_dep.notification_failure_criteria,
                                        getattr(svc_dep, 'dependency_period', '24x7'),
                                        svc_dep.inherits_parent)

            services.add_chk_dependency(svc_dep.dependent_service_description,
                                        svc_dep.service_description,
                                        svc_dep.execution_failure_criteria,
                                        getattr(svc_dep, 'dependency_period', '24x7'),
                                        svc_dep.inherits_parent)

            # Only used for debugging purpose when loops are detected
            setattr(svc_dep, "service_description_string",
                    services[svc_dep.service_description].get_name())
            setattr(svc_dep, "dependent_service_description_string",
                    services[svc_dep.dependent_service_description].get_name())

    def is_correct(self):
        """Check if this servicedependency configuration is correct ::

        * Check our own specific properties
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """
        state = True

        # Internal checks before executing inherited function...
        loop = self.no_loop_in_parents("service_description", "dependent_service_description")
        if loop:
            self.add_error("Loop detected while checking service dependencies:")
            state = False
            for item in self:
                for elem in loop:
                    if elem == item.service_description:
                        self.add_error("- service %s is a parent service_description "
                                       "in dependency defined in %s"
                                       % (item.service_description_string,
                                          item.imported_from))
                    elif elem == item.dependent_service_description:
                        self.add_error("- service %s is a child service_description "
                                       "in dependency defined in %s"
                                       % (item.dependent_service_description_string,
                                          item.imported_from))

        return super(Servicedependencies, self).is_correct() and state
