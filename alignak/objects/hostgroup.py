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

from alignak.property import StringProp, ListProp

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Hostgroup(Itemgroup):
    """
    Class to manage a group of host
    A Hostgroup is used to manage a group of hosts
    """
    my_type = 'hostgroup'

    properties = Itemgroup.properties.copy()
    properties.update({
        # 'uuid':
        #     StringProp(fill_brok=['full_status']),
        'hostgroup_name':
            StringProp(fill_brok=['full_status']),
        'alias':
            StringProp(fill_brok=['full_status']),
        'hostgroup_members':
            ListProp(default=[], fill_brok=['full_status'], merging='join', split_on_comma=True),
        'notes':
            StringProp(default=u'', fill_brok=['full_status']),
        'notes_url':
            StringProp(default=u'', fill_brok=['full_status']),
        'action_url':
            StringProp(default=u'', fill_brok=['full_status']),
        'realm':
            StringProp(default=u'', fill_brok=['full_status']),
    })

    macros = {
        'HOSTGROUPALIAS':     'alias',
        'HOSTGROUPMEMBERS':   'members',
        'HOSTGROUPNOTES':     'notes',
        'HOSTGROUPNOTESURL':  'notes_url',
        'HOSTGROUPACTIONURL': 'action_url'
    }

    def get_name(self):
        """
        Get name of group

        :return: Name of hostgroup
        :rtype: str
        """
        return self.hostgroup_name

    def get_hosts(self):
        """
        Get list of hosts of this group

        :return: list of hosts
        :rtype: list
        """
        if getattr(self, 'members', None) is not None:
            return self.members

        return []

    def get_hostgroup_members(self):
        """
        Get list of groups members of this hostgroup

        :return: list of hosts
        :rtype: list
        """
        if hasattr(self, 'hostgroup_members'):
            return self.hostgroup_members

        return []

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
                    self.add_string_member(value)

        return self.get_hosts()


class Hostgroups(Itemgroups):
    """
    Class to manage list of Hostgroup
    Hostgroups is used to regroup all Hostgroup
    """
    name_property = "hostgroup_name"  # is used for finding hostgroups
    inner_class = Hostgroup

    def get_members_by_name(self, gname):
        """
        Get all members by name given in parameter

        :param hgname: name of members
        :type hgname: str
        :return: list of hosts with this name
        :rtype: list
        """
        hostgroup = self.find_by_name(gname)
        if hostgroup is None:
            return []
        return hostgroup.get_hosts()

    def linkify(self, hosts=None, realms=None):
        """
        Make link of hosts / realms

        :param hosts: object Hosts
        :type hosts: alignak.objects.hostgroup.Hostgroups
        :param realms: object Realms
        :type realms: alignak.objects.realm.Realms
        :return: None
        """
        self.linkify_hg_by_hst(hosts)
        self.linkify_hg_by_realms(realms, hosts)

    def linkify_hg_by_hst(self, hosts):
        """
        We just search for each hostgroup the id of the hosts
        and replace the name by the id

        :param hosts: object Hosts
        :type hosts: object
        :return: None
        """
        for hostgroup in self:
            mbrs = hostgroup.get_hosts()
            # The new member list, in id
            new_mbrs = []
            for mbr in mbrs:
                mbr = mbr.strip()  # protect with strip at the beginning so don't care about spaces
                if mbr == '':  # void entry, skip this
                    continue
                elif mbr == '*':
                    new_mbrs.extend(list(hosts.items.keys()))
                else:
                    host = hosts.find_by_name(mbr)
                    if host is not None:
                        new_mbrs.append(host.uuid)
                        host.hostgroups.append(hostgroup.uuid)
                        # and be sure we are uniq in it
                        host.hostgroups = list(set(host.hostgroups))
                    else:
                        hostgroup.add_string_unknown_member(mbr)

            # Make members uniq
            new_mbrs = list(set(new_mbrs))

            # We find the id, we replace the names
            hostgroup.replace_members(new_mbrs)

    def linkify_hg_by_realms(self, realms, hosts):
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
                hostgroup.add_error(err)
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
                        hostgroup.add_warning("[hostgroups] host %s is not in the same realm "
                                              "than its hostgroup %s"
                                              % (host.get_name(), hostgroup.get_name()))

    def add_member(self, hname, hgname):
        """
        Add a host string to a hostgroup member
        if the host group do not exist, create it

        :param hname: host name
        :type hname: str
        :param hgname:hostgroup name
        :type hgname: str
        :return: None
        """
        hostgroup = self.find_by_name(hgname)
        # if the id do not exist, create the hg
        if hostgroup is None:
            hostgroup = Hostgroup({'hostgroup_name': hgname, 'alias': hgname, 'members': hname})
            self.add(hostgroup)
        else:
            hostgroup.add_string_member(hname)

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
            if hasattr(hostgroup, 'hostgroup_members') and not hostgroup.already_exploded:
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
