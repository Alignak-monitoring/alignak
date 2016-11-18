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

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Servicedependency(Item):
    """Servicedependency class is a simple implementation of service dependency as
    defined in a monitoring context (dependency period, notification_failure_criteria ..)

    """
    name_property = "dependency_name"
    my_type = "servicedependency"

    # F is dep of D
    # host_name                      Host B
    #       service_description             Service D
    #       dependent_host_name             Host C
    #       dependent_service_description   Service F
    #       execution_failure_criteria      o
    #       notification_failure_criteria   w,u
    #       inherits_parent         1
    #       dependency_period       24x7

    properties = Item.properties.copy()
    properties.update({
        'dependent_host_name':
            StringProp(default=''),
        'dependent_hostgroup_name':
            StringProp(default=''),
        'dependent_service_description':
            StringProp(default=''),
        'host_name':
            StringProp(default=''),
        'hostgroup_name':
            StringProp(default=''),
        'service_description':
            StringProp(default=''),
        'inherits_parent':
            BoolProp(default=False),
        'execution_failure_criteria':
            ListProp(default=['n']),
        'notification_failure_criteria':
            ListProp(default=['n']),
        'dependency_period':
            StringProp(default=''),
        'explode_hostgroup':
            BoolProp(default=False)
    })

    @property
    def dependency_name(self):
        """Build a name for a service dependency

        :return: Tuple with host_name and service_description for service and dependent service
        :rtype: tuple
        """
        return (getattr(self, 'dependent_host_name', 'undefined') + '/' +
                getattr(self, 'dependent_service_description', 'undefined') + '..' +
                getattr(self, 'host_name', 'undefined') + '/' +
                getattr(self, 'service_description', 'undefined'))


class Servicedependencies(Items):
    """Servicedependencies manage a list of Servicedependency objects,
       used for parsing configuration

    """
    inner_class = Servicedependency  # use for know what is in items

    def delete_servicesdep_by_id(self, ids):
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
        prop = {
            'dependent_host_name': dep_host_name,
            'dependent_service_description': dep_service_description,
            'host_name': par_host_name,
            'service_description': par_service_description,
            'notification_failure_criteria': 'u,c,w',
            'inherits_parent': '1',
        }
        servicedep = Servicedependency(prop)
        self.add_item(servicedep)

    def explode_hostgroup(self, service_dependency, hostgroups):
        """Explode a service dependency for each member of hostgroup

        :param service_dependency: service dependency to explode
        :type service_dependency: alignak.objects.servicedependency.Servicedependency
        :param hostgroups: used to find hostgroup objects
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :return:None
        """
        # We will create a service dependency for each host part of the host group

        # First get services
        snames = [d.strip() for d in service_dependency.service_description.split(',')]

        # And dep services
        dep_snames = [d.strip() for d in
                      service_dependency.dependent_service_description.split(',')]

        # Now for each host into hostgroup we will create a service dependency object
        hg_names = [n.strip() for n in service_dependency.hostgroup_name.split(',')]
        for hg_name in hg_names:
            hostgroup = hostgroups.find_by_name(hg_name)
            if hostgroup is None:
                err = "the servicedependency %s got an unknown hostgroup_name '%s'" % \
                      (service_dependency.get_name(), hg_name)
                self.configuration_errors.append(err)
                continue
            hnames = []
            hnames.extend([m.strip() for m in hostgroup.get_hosts()])
            for hname in hnames:
                for dep_sname in dep_snames:
                    for sname in snames:
                        new_sd = service_dependency.copy()
                        new_sd.host_name = hname
                        new_sd.service_description = sname
                        new_sd.dependent_host_name = hname
                        new_sd.dependent_service_description = dep_sname
                        self.add_item(new_sd)

    def explode(self, hostgroups):
        """Explode all service dependency for each member of hostgroups
        Each member of dependent hostgroup or hostgroup in dependency have to get a copy of
        service dependencies (quite complex to parse)

        :param hostgroups: used to look for hostgroup
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :return: None
        """
        # The "old" services will be removed. All services with
        # more than one host or a host group will be in it
        srvdep_to_remove = []

        # Then for every host create a copy of the service with just the host
        # because we are adding services, we can't just loop in it
        service_dependencies = self.items.keys()
        for s_id in service_dependencies:
            service_dependency = self.items[s_id]

            # First case: we only have to propagate the services dependencies to the all the hosts
            # of some hostgroups
            # Either a specific property is defined (Alignak) or no dependent hosts groups
            # is defined
            if getattr(service_dependency, 'explode_hostgroup', None) is None or \
                    (getattr(service_dependency, 'hostgroup_name', '') and
                        not getattr(service_dependency, 'dependent_hostgroup_name', '')):
                self.explode_hostgroup(service_dependency, hostgroups)
                srvdep_to_remove.append(s_id)
                continue

            # Get the list of all FATHER hosts and service dependenciess
            hnames = []
            if getattr(service_dependency, 'hostgroup_name', None):
                hg_names = [n.strip() for n in service_dependency.hostgroup_name.split(',')]
                hg_names = [hg_name.strip() for hg_name in hg_names]
                for hg_name in hg_names:
                    hostgroup = hostgroups.find_by_name(hg_name)
                    if hostgroup is None:
                        err = "the servicedependency %s got an unknown " \
                              "hostgroup_name '%s'" % \
                              (service_dependency.get_name(), hg_name)
                        self.configuration_errors.append(err)
                        continue
                    hnames.extend([m.strip() for m in hostgroup.get_hosts()])

            if not getattr(service_dependency, 'host_name'):
                service_dependency.host_name = ''

            if service_dependency.host_name != '':
                hnames.extend([n.strip() for n in service_dependency.host_name.split(',')])
            snames = [d.strip() for d in service_dependency.service_description.split(',')]
            couples = []
            for hname in hnames:
                for sname in snames:
                    couples.append((hname.strip(), sname.strip()))

            if not getattr(service_dependency, 'dependent_hostgroup_name') \
                    and getattr(service_dependency, 'hostgroup_name'):
                service_dependency.dependent_hostgroup_name = service_dependency.hostgroup_name

            # Now the dependent part (the sons)
            dep_hnames = []
            if getattr(service_dependency, 'dependent_hostgroup_name', None):
                hg_names = [n.strip() for n in
                            service_dependency.dependent_hostgroup_name.split(',')]
                hg_names = [hg_name.strip() for hg_name in hg_names]
                for hg_name in hg_names:
                    hostgroup = hostgroups.find_by_name(hg_name)
                    if hostgroup is None:
                        err = "the servicedependency %s got an unknown " \
                              "dependent_hostgroup_name '%s'" % \
                              (service_dependency.get_name(), hg_name)
                        self.configuration_errors.append(err)
                        continue
                    dep_hnames.extend([m.strip() for m in hostgroup.get_hosts()])

            if not getattr(service_dependency, 'dependent_host_name'):
                service_dependency.dependent_host_name = \
                    getattr(service_dependency, 'host_name', '')

            if service_dependency.dependent_host_name != '':
                dep_hnames.extend([n.strip() for n in
                                   service_dependency.dependent_host_name.split(',')])
            dep_snames = [d.strip() for d in
                          service_dependency.dependent_service_description.split(',')]
            dep_couples = []
            for dep_hname in dep_hnames:
                for dep_sname in dep_snames:
                    dep_couples.append((dep_hname.strip(), dep_sname.strip()))

            # Create the new service deps from all of this.
            for (dep_hname, dep_sname) in dep_couples:  # the sons, like HTTP
                for (hname, sname) in couples:  # the fathers, like MySQL
                    new_sd = service_dependency.copy()
                    new_sd.host_name = hname
                    new_sd.service_description = sname
                    new_sd.dependent_host_name = dep_hname
                    new_sd.dependent_service_description = dep_sname
                    self.add_item(new_sd)
                # Ok so we can remove the old one
                srvdep_to_remove.append(s_id)

        self.delete_servicesdep_by_id(srvdep_to_remove)

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
        self.linkify_servicedependency_by_service(hosts, services)
        self.linkify_servicedependency_by_timeperiod(timeperiods)
        self.linkify_service_by_servicedependency(services)

    def linkify_servicedependency_by_service(self, hosts, services):
        """Replace dependent_service_description and service_description
        in service dependency by the real object

        :param hosts: host list, used to look for a specific one
        :type hosts: alignak.objects.host.Hosts
        :param services: service list to look for a specific one
        :type services: alignak.objects.service.Services
        :return: None
        """
        to_del = []
        for servicedep in self:
            try:
                s_name = servicedep.dependent_service_description
                hst_name = servicedep.dependent_host_name

                # The new member list, in id
                serv = services.find_srv_by_name_and_hostname(hst_name, s_name)
                if serv is None:
                    host = hosts.find_by_name(hst_name)
                    if not (host and host.is_excluded_for_sdesc(s_name)):
                        self.configuration_errors.append("Service %s not found for host %s" %
                                                         (s_name, hst_name))
                    elif host:
                        self.configuration_warnings.append("Service %s is excluded from host %s ; "
                                                           "removing this servicedependency as "
                                                           "it is unusuable." % (s_name, hst_name))
                    to_del.append(servicedep)
                    continue
                servicedep.dependent_service_description = serv.uuid

                s_name = servicedep.service_description
                hst_name = servicedep.host_name

                # The new member list, in id
                serv = services.find_srv_by_name_and_hostname(hst_name, s_name)
                if serv is None:
                    host = hosts.find_by_name(hst_name)
                    if not (host and host.is_excluded_for_sdesc(s_name)):
                        self.configuration_errors.append("Service %s not found for host %s" %
                                                         (s_name, hst_name))
                    elif host:
                        self.configuration_warnings.append("Service %s is excluded from host %s ; "
                                                           "removing this servicedependency as "
                                                           "it is unusuable." % (s_name, hst_name))
                    to_del.append(servicedep)
                    continue
                servicedep.service_description = serv.uuid

            except AttributeError as err:
                logger.error("[servicedependency] fail to linkify by service %s: %s",
                             servicedep, err)
                to_del.append(servicedep)

        for servicedep in to_del:
            self.remove_item(servicedep)

    def linkify_servicedependency_by_timeperiod(self, timeperiods):
        """Replace dependency_period by a real object in service dependency

        :param timeperiods: list of timeperiod, used to look for a specific one
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: None
        """
        for servicedep in self:
            try:
                tp_name = servicedep.dependency_period
                timeperiod = timeperiods.find_by_name(tp_name)
                if timeperiod:
                    servicedep.dependency_period = timeperiod.uuid
                else:
                    # Todo: specif a TP!
                    servicedep.dependency_period = ''
            except AttributeError, exp:
                logger.error("[servicedependency] fail to linkify by timeperiods: %s", exp)

    def linkify_service_by_servicedependency(self, services):
        """Add dependency in service objects

        :return: None
        """
        for servicedep in self:

            if getattr(servicedep, 'service_description', None) is None or\
                    getattr(servicedep, 'dependent_service_description', None) is None:
                continue

            services.add_act_dependency(servicedep.dependent_service_description,
                                        servicedep.service_description,
                                        servicedep.notification_failure_criteria,
                                        getattr(servicedep, 'dependency_period', ''),
                                        servicedep.inherits_parent)

            services.add_chk_dependency(servicedep.dependent_service_description,
                                        servicedep.service_description,
                                        servicedep.execution_failure_criteria,
                                        getattr(servicedep, 'dependency_period', ''),
                                        servicedep.inherits_parent)

            # Only used for debugging purpose when loops are detected
            setattr(servicedep, "service_description_string",
                    services[servicedep.service_description].get_name())
            setattr(servicedep, "dependent_service_description_string",
                    services[servicedep.dependent_service_description].get_name())

    def is_correct(self):
        """Check if this servicedependency configuration is correct ::

        * Check our own specific properties
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """

        # Internal checks before executing inherited function...
        loop = self.no_loop_in_parents("service_description", "dependent_service_description")
        if len(loop) > 0:
            self.add_error("Loop detected while checking service dependencies")
            for item in self:
                for elem in loop:
                    if elem == item.service_description:
                        self.add_error("Service %s is parent service_description in "
                                       "dependency defined in %s" %
                                       (item.service_description_string, item.imported_from))
                    elif elem == item.dependent_service_description:
                        self.add_error("Service %s is child service_description in "
                                       "dependency defined in %s" %
                                       (item.dependent_service_description_string,
                                        item.imported_from))

        return super(Servicedependencies, self).is_correct() and self.conf_is_correct
