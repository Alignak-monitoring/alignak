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

    def __init__(self, params=None, parsing=True):
        if params is None:
            params = {}

        for prop in ['execution_failure_criteria', 'notification_failure_criteria']:
            if prop in params:
                params[prop] = [p.replace('u', 'x') for p in params[prop]]
        super(Hostdependency, self).__init__(params, parsing=parsing)

    def get_name(self):
        """Get name based on dependent_host_name and host_name attributes
        Each attribute is substituted by 'unknown' if attribute does not exist

        :return: dependent_host_name/host_name
        :rtype: str
        """
        dependent_host_name = 'unknown'
        if getattr(self, 'dependent_host_name', None):
            dependent_host_name = getattr(
                getattr(self, 'dependent_host_name'), 'host_name', 'unknown'
            )
        host_name = 'unknown'
        if getattr(self, 'host_name', None):
            host_name = getattr(getattr(self, 'host_name'), 'host_name', 'unknown')
        return dependent_host_name + '/' + host_name


class Hostdependencies(Items):
    """Hostdependencies manage a list of Hostdependency objects, used for parsing configuration

    """
    inner_class = Hostdependency  # use for know what is in items

    def delete_hostsdep_by_id(self, ids):
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
        hstdep_to_remove = []

        # Then for every host create a copy of the dependency with just the host
        # because we are adding services, we can't just loop in it
        hostdeps = list(self.items.keys())
        for h_id in hostdeps:
            hostdep = self.items[h_id]
            # We explode first the dependent (son) part
            dephnames = []
            if hasattr(hostdep, 'dependent_hostgroup_name'):
                dephg_names = [n.strip() for n in hostdep.dependent_hostgroup_name.split(',')]
                for dephg_name in dephg_names:
                    dephg = hostgroups.find_by_name(dephg_name)
                    if dephg is None:
                        err = "ERROR: the hostdependency got " \
                              "an unknown dependent_hostgroup_name '%s'" % dephg_name
                        hostdep.add_error(err)
                        continue
                    dephnames.extend([m.strip() for m in dephg.get_hosts()])

            if hasattr(hostdep, 'dependent_host_name'):
                dephnames.extend([n.strip() for n in hostdep.dependent_host_name.split(',')])

            # Ok, and now the father part :)
            hnames = []
            if hasattr(hostdep, 'hostgroup_name'):
                hg_names = [n.strip() for n in hostdep.hostgroup_name.split(',')]
                for hg_name in hg_names:
                    hostgroup = hostgroups.find_by_name(hg_name)
                    if hostgroup is None:
                        err = "ERROR: the hostdependency got" \
                              " an unknown hostgroup_name '%s'" % hg_name
                        hostdep.add_error(err)
                        continue
                    hnames.extend([m.strip() for m in hostgroup.get_hosts()])

            if hasattr(hostdep, 'host_name'):
                hnames.extend([n.strip() for n in hostdep.host_name.split(',')])

            # Loop over all sons and fathers to get S*F host deps
            for dephname in dephnames:
                dephname = dephname.strip()
                for hname in hnames:
                    new_hd = hostdep.copy()
                    new_hd.dependent_host_name = dephname
                    new_hd.host_name = hname
                    self.add_item(new_hd)
            hstdep_to_remove.append(h_id)

        self.delete_hostsdep_by_id(hstdep_to_remove)

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
        self.linkify_hd_by_h(hosts)
        self.linkify_hd_by_tp(timeperiods)
        self.linkify_h_by_hd(hosts)

    def linkify_hd_by_h(self, hosts):
        """Replace dependent_host_name and host_name
        in host dependency by the real object

        :param hosts: host list, used to look for a specific one
        :type hosts: alignak.objects.host.Hosts
        :return: None
        """
        for hostdep in self:
            try:
                h_name = hostdep.host_name
                dh_name = hostdep.dependent_host_name
                host = hosts.find_by_name(h_name)
                if host is None:
                    err = "Error: the host dependency got a bad host_name definition '%s'" % h_name
                    hostdep.add_error(err)
                dephost = hosts.find_by_name(dh_name)
                if dephost is None:
                    err = "Error: the host dependency got " \
                          "a bad dependent_host_name definition '%s'" % dh_name
                    hostdep.add_error(err)
                if host:
                    hostdep.host_name = host.uuid
                if dephost:
                    hostdep.dependent_host_name = dephost.uuid
            except AttributeError as exp:
                err = "Error: the host dependency miss a property '%s'" % exp
                hostdep.add_error(err)

    def linkify_hd_by_tp(self, timeperiods):
        """Replace dependency_period by a real object in host dependency

        :param timeperiods: list of timeperiod, used to look for a specific one
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :return: None
        """
        for hostdep in self:
            try:
                tp_name = hostdep.dependency_period
                timeperiod = timeperiods.find_by_name(tp_name)
                if timeperiod:
                    hostdep.dependency_period = timeperiod.uuid
                else:
                    hostdep.dependency_period = ''
            except AttributeError as exp:  # pragma: no cover, simple protectionn
                logger.error("[hostdependency] fail to linkify by timeperiod: %s", exp)

    def linkify_h_by_hd(self, hosts):
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
            msg = "Loop detected while checking host dependencies"
            self.add_error(msg)
            state = False
            for item in self:
                for elem in loop:
                    if elem == item.host_name:
                        msg = "Host %s is parent host_name in dependency defined in %s" % (
                            item.host_name_string, item.imported_from
                        )
                        self.add_error(msg)
                    elif elem == item.dependent_host_name:
                        msg = "Host %s is child host_name in dependency defined in %s" % (
                            item.dependent_host_name_string, item.imported_from
                        )
                        self.add_error(msg)

        return super(Hostdependencies, self).is_correct() and state
