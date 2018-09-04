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

from alignak.property import StringProp, ListProp, BoolProp

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Hostgroup(Itemgroup):
    """
    Class to manage a group of host
    A Hostgroup is used to manage a group of hosts
    """
    my_type = 'hostgroup'
    members_property = "members"
    group_members_property = "hostgroup_members"

    properties = Itemgroup.properties.copy()
    properties.update({
        'hostgroup_name':
            StringProp(fill_brok=['full_status']),
        'alias':
            StringProp(default=u'', fill_brok=['full_status']),
        'hostgroup_members':
            ListProp(default=[], fill_brok=['full_status'], merging='join', split_on_comma=True),
        'notes':
            StringProp(default=u'', fill_brok=['full_status']),
        'notes_url':
            StringProp(default=u'', fill_brok=['full_status']),
        'action_url':
            StringProp(default=u'', fill_brok=['full_status']),

        # Realm stuff
        'realm':
            StringProp(default=u'', fill_brok=['full_status']),
    })

    # properties set only for running purpose
    running_properties = Itemgroup.running_properties.copy()
    running_properties.update({
        # Realm stuff
        'realm_name':
            StringProp(default=u''),
        'got_default_realm':
            BoolProp(default=False),
    })

    macros = {
        'HOSTGROUPNAME': 'hostgroup_name',
        'HOSTGROUPALIAS': 'alias',
        'HOSTGROUPMEMBERS': 'members',
        'HOSTGROUPGROUPMEMBERS': 'hostgroup_members',
        'HOSTGROUPNOTES':  'notes',
        'HOSTGROUPNOTESURL': 'notes_url',
        'HOSTGROUPACTIONURL': 'action_url',
        'HOSTGROUPREALM': 'realm_name'
    }

    def get_name(self):
        """Get the group name"""
        return getattr(self, 'hostgroup_name', 'Unnamed')

    def get_hosts(self):
        """Get the hosts of the group

        :return: list of hosts
        :rtype: list
        """
        return super(Hostgroup, self).get_members()

    def get_hostgroup_members(self):
        """Get the groups members of the group

        :return: list of hosts
        :rtype: list
        """
        return getattr(self, 'hostgroup_members', [])

    def get_hosts_by_explosion(self, hostgroups):
        # pylint: disable=access-member-before-definition
        """
        Get hosts of this group

        :param hostgroups: Hostgroup object
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :return: list of hosts of this group
        :rtype: list
        """
        # First we tag the hg so it will not be explode
        # if a son of it already call it
        self.already_exploded = True

        # Now the recursive part
        # rec_tag is set to False every HG we explode
        # so if True here, it must be a loop in HG
        # calls... not GOOD!
        if self.rec_tag:
            logger.error("[hostgroup::%s] got a loop in hostgroup definition", self.get_name())
            return self.get_hosts()

        # Ok, not a loop, we tag it and continue
        self.rec_tag = True

        hg_mbrs = self.get_hostgroup_members()
        for hg_mbr in hg_mbrs:
            hostgroup = hostgroups.find_by_name(hg_mbr.strip())
            if hostgroup is not None:
                value = hostgroup.get_hosts_by_explosion(hostgroups)
                if value is not None:
                    self.add_members(value)

        return self.get_hosts()


class Hostgroups(Itemgroups):
    """
    Class to manage list of Hostgroup
    Hostgroups is used to regroup all Hostgroup
    """
    name_property = "hostgroup_name"
    inner_class = Hostgroup

    def add_member(self, host_name, hostgroup_name):
        """Add a host string to a hostgroup member
        if the host group do not exist, create it

        :param host_name: host name
        :type host_name: str
        :param hostgroup_name:hostgroup name
        :type hostgroup_name: str
        :return: None
        """
        hostgroup = self.find_by_name(hostgroup_name)
        if not hostgroup:
            hostgroup = Hostgroup({'hostgroup_name': hostgroup_name,
                                   'alias': hostgroup_name,
                                   'members': host_name})
            self.add(hostgroup)
        else:
            hostgroup.add_members(host_name)

    def get_members_of_group(self, gname):
        """Get all members of a group which name is given in parameter

        :param gname: name of the group
        :type gname: str
        :return: list of the hosts in the group
        :rtype: list[alignak.objects.host.Host]
        """
        hostgroup = self.find_by_name(gname)
        if hostgroup:
            return hostgroup.get_hosts()
        return []

    def linkify(self, hosts=None, realms=None):
        """Link hostgroups with hosts and realms

        :param hosts: all Hosts
        :type hosts: alignak.objects.host.Hosts
        :param realms: all Realms
        :type realms: alignak.objects.realm.Realms
        :return: None
        """
        self.linkify_hostgroups_hosts(hosts)
        self.linkify_hostgroups_realms_hosts(realms, hosts)

    def linkify_hostgroups_hosts(self, hosts):
        """We just search for each hostgroup the id of the hosts
        and replace the names by the found identifiers

        :param hosts: object Hosts
        :type hosts: alignak.objects.host.Hosts
        :return: None
        """
        for hostgroup in self:
            members = hostgroup.get_hosts()
            # The new members identifiers list
            new_members = []
            for member in members:
                # member is an host name
                member = member.strip()
                if not member:  # void entry, skip this
                    continue

                if member == '*':
                    # All the hosts identifiers list
                    new_members.extend(list(hosts.items.keys()))
                else:
                    host = hosts.find_by_name(member)
                    if host is not None:
                        new_members.append(host.uuid)
                        if hostgroup.uuid not in host.hostgroups:
                            host.hostgroups.append(hostgroup.uuid)
                    else:
                        hostgroup.add_unknown_members(member)

            # Make members unique
            new_members = list(set(new_members))

            # We find the id, we replace the names
            hostgroup.replace_members(new_members)

    def linkify_hostgroups_realms_hosts(self, realms, hosts):
        # pylint: disable=too-many-locals, too-many-nested-blocks, too-many-branches
        """Link between an hostgroup and a realm is already done in the configuration parsing
        function that defines and checks the default satellites, realms, hosts and hosts groups
        consistency.

        This function will only raise some alerts if hosts groups and hosts that are contained
        do not belong the same realm !

        :param realms: object Realms
        :type realms: alignak.objects.realm.Realms
        :param hosts: object Realms
        :type hosts: alignak.objects.host.Hosts
        :return: None
        """
        for hostgroup in self:
            logger.debug("Hostgroup: %s in the realm: %s", hostgroup, hostgroup.realm)
            hostgroup_realm_name = hostgroup.realm
            if hostgroup.realm not in realms:
                realm = realms.find_by_name(hostgroup.realm)
                if not realm:
                    continue
                hostgroup.realm = realm.uuid
            else:
                hostgroup_realm_name = realms[hostgroup.realm].get_name()

            hostgroup_hosts_errors = []
            hostgroup_new_realm_name = None
            hostgroup_new_realm_failed = False
            for host_uuid in hostgroup:
                if host_uuid not in hosts:
                    continue
                host = hosts[host_uuid]
                host_realm_name = host.realm
                if host.realm not in realms:
                    host_realm = realms.find_by_name(host.realm)
                    if not host_realm:
                        # Host realm is unknown, an error will be raised elsewhere!
                        continue
                else:
                    host_realm_name = realms[host.realm].get_name()

                if host.got_default_realm:
                    # If the host got a default realm it means that no realm is specifically
                    # declared for this host. Thus it can inherit its realm from the one of its
                    # hostgroup :)
                    logger.debug("- apply the realm %s to the host %s from a hostgroup rule (%s)",
                                 hostgroup_realm_name, host.get_name(), hostgroup.get_name())
                    host.realm = hostgroup.realm
                else:
                    # If the host has a realm that is specifically declared then it must the same
                    # as its hostgroup one!
                    if host.realm != hostgroup.realm:
                        # If the hostgroup had a specified realm
                        if not hostgroup.got_default_realm:
                            # raise an error !
                            hostgroup.add_error(
                                "host %s (realm: %s) is not in the same realm than its "
                                "hostgroup %s (realm: %s)"
                                % (host.get_name(), host_realm_name,
                                   hostgroup.get_name(), hostgroup_realm_name))
                        else:
                            # Temporary log an error...
                            hostgroup_hosts_errors.append(
                                "host %s (realm: %s) is not in the same realm than its "
                                "hostgroup %s (realm: %s)"
                                % (host.get_name(), host_realm_name,
                                   hostgroup.get_name(), hostgroup_realm_name))

                            if not hostgroup_new_realm_name or \
                                    hostgroup_new_realm_name == host_realm_name:
                                # Potential new host group realm
                                hostgroup_new_realm_name = host_realm_name
                            else:
                                # It still exists a candidate realm for the hostgroup,
                                # raise an error !
                                hostgroup.add_error("hostgroup %s got the default realm but it has "
                                                    "some hosts that are from different realms: "
                                                    "%s and %s. The realm cannot be adjusted!"
                                                    % (hostgroup.get_name(),
                                                       hostgroup_new_realm_name,
                                                       host_realm_name))
                                hostgroup_new_realm_failed = True
                                break

            if hostgroup_new_realm_name is None:
                # Do not change the hostgroup realm, it is not possible,
                # so raise the host individual errors!
                for error in hostgroup_hosts_errors:
                    hostgroup.add_error(error)
            elif hostgroup_new_realm_name:
                if not hostgroup_new_realm_failed:
                    # Change the hostgroup realm to suit its hosts
                    hostgroup.add_warning("hostgroup %s gets the realm of its hosts: %s"
                                          % (hostgroup.get_name(), hostgroup_new_realm_name))
                    hostgroup_new_realm = realms.find_by_name(hostgroup_new_realm_name)
                    hostgroup.realm = hostgroup_new_realm.uuid

    def explode(self):
        """
        Fill members with hostgroup_members

        :return: None
        """
        # We do not want a same hostgroup to be exploded again and again
        # so we tag it
        for tmp_hg in list(self.items.values()):
            tmp_hg.already_exploded = False

        for hostgroup in list(self.items.values()):
            if hostgroup.already_exploded:
                continue

            # get_hosts_by_explosion is a recursive
            # function, so we must tag hg so we do not loop
            for tmp_hg in list(self.items.values()):
                tmp_hg.rec_tag = False
            hostgroup.get_hosts_by_explosion(self)

        # We clean the tags
        for tmp_hg in list(self.items.values()):
            if hasattr(tmp_hg, 'rec_tag'):
                del tmp_hg.rec_tag
            del tmp_hg.already_exploded
