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
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Christophe Simon, geektophe@gmail.com
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
This module provide Hostgroup and Hostgroups class used to manage host groups
"""

import logging
from alignak.objects.itemgroup import Itemgroup, Itemgroups
from alignak.objects.host import Host

from alignak.util import get_obj_name
from alignak.property import StringProp, ListProp

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Hostgroup(Itemgroup):
    """
    Class to manage a group of host
    A Hostgroup is used to manage a group of hosts

    Class variable are explained in the Itemgroup base class
    """
    name_property = "hostgroup_name"
    members_class = Host
    members_property = "members"
    groupmembers_property = "hostgroup_members"
    my_type = 'hostgroup'

    properties = Itemgroup.properties.copy()
    properties.update({
        'hostgroup_name':
            StringProp(fill_brok=['full_status']),
        'hostgroup_members':
            ListProp(default=[], fill_brok=['full_status'], merging='join'),
        'notes':
            StringProp(default='', fill_brok=['full_status']),
        'notes_url':
            StringProp(default='', fill_brok=['full_status']),
        'action_url':
            StringProp(default='', fill_brok=['full_status']),
        'realm':
            StringProp(default='', fill_brok=['full_status'], conf_send_preparation=get_obj_name),
    })

    macros = {
        'HOSTGROUPALIAS':     'alias',
        'HOSTGROUPMEMBERS':   'get_members',
        'HOSTGROUPNOTES':     'notes',
        'HOSTGROUPNOTESURL':  'notes_url',
        'HOSTGROUPACTIONURL': 'action_url'
    }

    def get_hosts(self):
        """
        Get list of hosts of this group

        :return: list of hosts uuid
        :rtype: list
        """
        return self.get_members()

    def get_hostgroup_members(self):
        """
        Get list of groups members of this hostgroup

        :return: list of hosts
        :rtype: list
        """
        return self.get_group_members()

    def get_hosts_by_explosion(self, hostgroups, hosts):
        """
        Get direct hosts of this group and all hosts from the sub-groups
        Append sub-groups members to the members of this group

        :param hostgroups: Hostgroups object
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :param hosts: hosts to explode
        :type hosts: alignak.objects.host.Hosts
        :return: return the list of members
        :rtype: list[alignak.objects.host.Host]
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
            hostgroup = hostgroups.find_by_name(group_member)
            if hostgroup is not None:
                members_uuid = hostgroup.get_hosts_by_explosion(hostgroups, hosts)
                if members_uuid:
                    new_members = []
                    for member_uuid in members_uuid:
                        if member_uuid in hosts:
                            new_members.append(hosts[member_uuid])
                    self.add_members(new_members)

        return self.get_members()


class Hostgroups(Itemgroups):
    """
    Class to manage list of Hostgroup
    Hostgroups is used to regroup all Hostgroup
    """
    inner_class = Hostgroup

    def linkify(self, hosts=None, realms=None):
        """
        Make link of hosts / realms

        :param hosts: object Hosts
        :type hosts: alignak.objects.hostgroup.Hostgroups
        :param realms: object Realms
        :type realms: alignak.objects.realm.Realms
        :return: None
        """
        self.linkify_hostgroup_by_host(hosts)
        self.linkify_hostgroup_by_realms(realms, hosts)

    def linkify_hostgroup_by_host(self, hosts):
        """
        We just search for each hostgroup the id of the hosts
        and replace the name by the id

        :param hosts: object Hosts
        :type hosts: object
        :return: None
        """
        logger.debug("Linkify hostgroups and hosts")
        for hostgroup in self:
            members = hostgroup.get_hosts()
            logger.debug("- HG: %s, members: %s", hostgroup, members)
            # The new member list, in id

            new_members = []
            for member in members:
                member = member.strip()
                if member == '':  # void entry, skip this
                    continue
                elif member == '*':
                    new_members.extend(hosts.items.keys())
                elif member in hosts:
                    # We got an host uuid
                    logger.debug("HG: %s, found an host: %s", hostgroup, hosts[member])
                    new_members.append(member)

                    # Update the found host hostgroups property and make it uniquified
                    hosts[member].hostgroups.append(hostgroup.uuid)
                    hosts[member].hostgroups = list(set(hosts[member].hostgroups))
                else:
                    host = hosts.find_by_name(member)
                    if host is not None:
                        new_members.append(host.uuid)
                        logger.debug("HG: %s, found a member: %s", hostgroup, member)

                        # Update the found host hostgroups property and make it unique
                        host.hostgroups.append(hostgroup.uuid)
                        host.hostgroups = list(set(host.hostgroups))
                    else:
                        hostgroup.add_unknown_member(member)

            if new_members:
                # Make members uniq
                new_members = list(set(new_members))
                logger.debug("HG: %s, new members: %s", hostgroup, new_members)

                # We update the group members
                hostgroup.members = new_members

    def linkify_hostgroup_by_realms(self, realms, hosts):
        """
        More than an explode function, but we need to already
        have members so... Will be really linkify just after
        And we explode realm in ours members, but do not override
        a host realm value if it's already set

        :param realms: object Realms
        :type realms: object
        :return: None
        """
        # Now we explode the realm value if we've got one
        # The group realm must not override a host one (warning?)
        for hostgroup in self:
            if not hasattr(hostgroup, 'realm'):
                continue

            # Maybe the value is void?
            if not hostgroup.realm.strip():
                continue

            realm = realms.find_by_name(hostgroup.realm.strip())
            if realm is not None:
                hostgroup.realm = realm.uuid
                logger.debug("[hostgroups] %s is in %s realm",
                             hostgroup.get_name(), realm.get_name())
            else:
                err = "the hostgroup %s got an unknown realm '%s'" % \
                      (hostgroup.get_name(), hostgroup.realm)
                hostgroup.configuration_errors.append(err)
                hostgroup.realm = None
                continue

            for host_id in hostgroup:
                if host_id not in hosts:
                    continue
                host = hosts[host_id]
                if host.realm == '' or host.got_default_realm:  # default not hasattr(h, 'realm'):
                    logger.debug("[hostgroups] apply a realm %s to host %s from a hostgroup "
                                 "rule (%s)", realms[hostgroup.realm].get_name(),
                                 host.get_name(), hostgroup.get_name())
                    host.realm = hostgroup.realm
                else:
                    if host.realm != hostgroup.realm:
                        msg = "[hostgroups] host %s is not in the same realm " \
                              "than its hostgroup %s" % (host.get_name(), hostgroup.get_name())
                        hostgroup.configuration_warnings.append(msg)

    def add_group_member(self, host, hostgroup_name):
        """Add an host to a hostgroup.
        If the hostgroup does not exist it is created

        :param host: host item
        :type host: alignak.objects.host.Host
        :param hostgroup_name:hostgroup name
        :type hostgroup_name: str
        :return: None
        """
        hostgroup = self.find_by_name(hostgroup_name)
        if hostgroup is None:
            # Create the group if it does not yet exist
            hostgroup = Hostgroup({'hostgroup_name': hostgroup_name,
                                   'members': [host.get_name()],
                                   'imported_from': 'inner'})
            self.add_item(hostgroup)
        else:
            hostgroup.add_member(host)

    def explode(self, hosts):
        """
        Populate the members property with the group members and the members of the sub-groups

        :param hosts: hosts to explode
        :type hosts: alignak.objects.host.Hosts
        :return: None
        """
        for hostgroup in self.items.values():
            for groupmember in hostgroup.get_group_members():
                group = self.find_by_name(groupmember)
                if group is None:
                    continue
                if group.already_exploded:
                    continue

                # get_hosts_by_explosion is a recursive function, so we must
                # tag the groups to avoid looping infinetely
                for groupmember in self.items.values():
                    groupmember.recursion_tag = False
                hostgroup.get_hosts_by_explosion(self, hosts)

        # Clean the recursion tag
        for group in self.items.values():
            if hasattr(group, 'recursion_tag'):
                del group.recursion_tag
