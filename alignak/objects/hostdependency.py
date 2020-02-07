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
"""This module provides Hostdependency and Hostdependencies classes that
implements dependencies between hosts. Basically used for parsing.

"""
import logging
from alignak.objects.item import Item, Items
from alignak.property import BoolProp, StringProp, ListProp

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Hostdependency(Item):
    """Hostdependency class is a simple implementation of host dependency as
    defined in a monitoring context (dependency period, notification_failure_criteria ..)

    """
    my_type = 'hostdependency'
    my_name_property = "host_relation"
    my_index_property = "host_relation"

    properties = Item.properties.copy()
    properties.update({
        'dependent_host_name':
            StringProp(),
        'dependent_hostgroup_name':
            StringProp(default=''),
        'host_name':
            StringProp(),
        'hostgroup_name':
            StringProp(default=''),
        'inherits_parent':
            BoolProp(default=False),
        'execution_failure_criteria':
            ListProp(default=['n'], split_on_comma=True),
        'notification_failure_criteria':
            ListProp(default=['n'], split_on_comma=True),
        'dependency_period':
            StringProp(default='')
    })

    def __init__(self, params, parsing=True):
        # Update default options
        for prop in ['execution_failure_criteria', 'notification_failure_criteria']:
            if prop in params:
                params[prop] = [p.replace('u', 'x') for p in params[prop]]
        super(Hostdependency, self).__init__(params, parsing=parsing)

    # def __str__(self):  # pragma: no cover
    #     return '<Hostdependency %s %s, uuid=%s, use: %s />' \
    #            % ('template' if self.is_a_template() else '', self.get_full_name(), self.uuid,
    #               getattr(self, 'use', None))
    # __repr__ = __str__

    @property
    def host_relation(self):
        """Unique key for a host dependency

        :return: Tuple with host_name and dependent_host_name
        :rtype: tuple
        """
        return "{}->{}".format(getattr(self, 'host_name', 'unknown'),
                               getattr(self, 'dependent_host_name', 'independant'))

    def get_full_name(self):
        """Get name based on dependent_host_name and host_name attributes
        Each attribute is replaced with 'unknown' if attribute is not set

        :return: dependent_host_name/host_name
        :rtype: str
        """
        if self.is_a_template():
            return self.get_name()
        return "{}->{}".format(getattr(self, 'host_name', 'unknown'),
                               getattr(self, 'dependent_host_name', 'independant'))


class Hostdependencies(Items):
    """Hostdependencies manage a list of Hostdependency objects, used for parsing configuration

    """
    inner_class = Hostdependency

    def delete_host_dep_by_id(self, ids):
        """Delete a list of hostdependency

        :param ids: ids list to delete
        :type ids: list
        :return: None
        """
        for h_id in ids:
            del self[h_id]

    def explode(self, hostgroups):
        # pylint: disable=too-many-locals
        """Explode all host dependency for each member of hostgroups
        Each member of dependent hostgroup or hostgroup in dependency have to get a copy of
        host dependencies (quite complex to parse)

        :param hostgroups: used to look for hostgroup
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :return: None
        """
        # The "old" dependencies will be removed. All dependencies with
        # more than one host or a host group will be in it
        to_be_removed = []

        # Then for every host create a copy of the dependency with just the host
        # because we are adding services, we can't just loop in it
        for host_dep_id in list(self.items.keys()):
            host_dep = self.items[host_dep_id]

            # We explode first the dependent hosts (sons) part
            son_hosts = []
            if getattr(host_dep, 'dependent_hostgroup_name', ''):
                hg_names = [g.strip() for g in host_dep.dependent_hostgroup_name.split(',')]
                for hg_name in hg_names:
                    hostgroup = hostgroups.find_by_name(hg_name)
                    if hostgroup is None:
                        host_dep.add_error("A hostdependency got an unknown "
                                           "dependent_hostgroup_name '%s'" % hg_name)
                        continue
                    son_hosts.extend([m.strip() for m in hostgroup.get_hosts()])

            if getattr(host_dep, 'dependent_host_name', ''):
                son_hosts.extend([h.strip() for h in host_dep.dependent_host_name.split(',')])

            # Ok, and now the depending hosts (self and parents) part :)
            father_hosts = []
            if getattr(host_dep, 'hostgroup_name', ''):
                hg_names = [g.strip() for g in host_dep.hostgroup_name.split(',')]
                for hg_name in hg_names:
                    hostgroup = hostgroups.find_by_name(hg_name)
                    if hostgroup is None:
                        host_dep.add_error("A hostdependency got an unknown "
                                           "hostgroup_name '%s'" % hg_name)
                        continue
                    father_hosts.extend([m.strip() for m in hostgroup.get_hosts()])

            if getattr(host_dep, 'host_name', ''):
                father_hosts.extend([h.strip() for h in host_dep.host_name.split(',')])

            # Loop over all sons and fathers to get S*F host deps
            for dep_hname in son_hosts:
                dep_hname = dep_hname.strip()
                for host_name in father_hosts:
                    new_hd = host_dep.copy()
                    new_hd.dependent_host_name = dep_hname
                    new_hd.host_name = host_name
                    new_hd.definition_order = 1
                    self.add_item(new_hd)
                to_be_removed.append(host_dep_id)

        self.delete_host_dep_by_id(to_be_removed)

    def linkify(self, hosts, timeperiods):
        """Create link between objects::

         * hostdependency -> host
         * hostdependency -> timeperiods

        :param hosts: hosts to link
        :type hosts: alignak.objects.host.Hosts
        :param timeperiods: timeperiods to link
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: None
        """
        self.linkify_host_dep_by_host(hosts)
        self.linkify_host_dep_by_timeperiod(timeperiods)
        self.linkify_host_by_host_dep(hosts)

    def linkify_host_dep_by_host(self, hosts):
        """Replace dependent_host_name and host_name
        in host dependency by the real object

        :param hosts: host list, used to look for a specific one
        :type hosts: alignak.objects.host.Hosts
        :return: None
        """
        for host_dep in self:
            host_name = getattr(host_dep, 'host_name', '')
            if host_name:
                host = hosts.find_by_name(host_name)
                if host is None:
                    host_dep.add_error("got a bad host_name definition '%s'" % host_name)
                if host:
                    host_dep.host_name = host.uuid

            dep_host_name = getattr(host_dep, 'dependent_host_name', '')
            if dep_host_name:
                dep_host = hosts.find_by_name(dep_host_name)
                if dep_host is None:
                    host_dep.add_error("got a bad dependent_host_name definition '%s'"
                                       % dep_host_name)
                if dep_host:
                    host_dep.dependent_host_name = dep_host.uuid

    def linkify_host_dep_by_timeperiod(self, timeperiods):
        """Replace dependency_period by a real object in host dependency

        :param timeperiods: list of timeperiod, used to look for a specific one
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: None
        """
        for host_dep in self:
            try:
                timeperiod_name = getattr(host_dep, 'dependency_period', '')
                if timeperiod_name:
                    timeperiod = timeperiods.find_by_name(timeperiod_name)
                    if timeperiod is None:
                        host_dep.add_error("got a bad dependency_period definition '%s'"
                                           % timeperiod_name)

                    if timeperiod:
                        host_dep.dependency_period = timeperiod.uuid
            except AttributeError as exp:  # pragma: no cover, simple protectionn
                logger.error("[hostdependency] fail to linkify by timeperiod: %s", exp)

    def linkify_host_by_host_dep(self, hosts):
        """Add dependency in host objects
        :param hosts: hosts list
        :type hosts: alignak.objects.host.Hosts

        :return: None
        """
        for hostdep in self:
            # Only used for debugging purpose when loops are detected
            setattr(hostdep, "host_name_string", "undefined")
            setattr(hostdep, "dependent_host_name_string", "undefined")

            # if the host dep conf is bad, pass this one
            if getattr(hostdep, 'host_name', None) is None or\
                    getattr(hostdep, 'dependent_host_name', None) is None:
                continue

            if hostdep.host_name not in hosts or hostdep.dependent_host_name not in hosts:
                continue

            hosts.add_act_dependency(hostdep.dependent_host_name, hostdep.host_name,
                                     hostdep.notification_failure_criteria,
                                     getattr(hostdep, 'dependency_period', ''),
                                     hostdep.inherits_parent)

            hosts.add_chk_dependency(hostdep.dependent_host_name, hostdep.host_name,
                                     hostdep.execution_failure_criteria,
                                     getattr(hostdep, 'dependency_period', ''),
                                     hostdep.inherits_parent)

            # Only used for debugging purpose when loops are detected
            setattr(hostdep, "host_name_string", hosts[hostdep.host_name].get_name())
            setattr(hostdep, "dependent_host_name_string",
                    hosts[hostdep.dependent_host_name].get_name())

    def is_correct(self):
        """Check if this object configuration is correct ::

        * Check our own specific properties
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """
        state = True

        # Internal checks before executing inherited function...
        loop = self.no_loop_in_parents("host_name", "dependent_host_name")
        if loop:
            self.add_error("Loop detected while checking host dependencies:")
            state = False
            for item in self:
                for elem in loop:
                    if elem == item.host_name:
                        self.add_error("- host %s is a parent host_name in dependency defined in %s"
                                       % (item.host_name_string, item.imported_from))
                    elif elem == item.dependent_host_name:
                        self.add_error("- host %s is a child host_name in dependency defined in %s"
                                       % (item.dependent_host_name_string, item.imported_from))

        return super(Hostdependencies, self).is_correct() and state
