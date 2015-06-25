#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2015-2015: Alignak team, see AUTHORS.txt file for contributors
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


from itemgroup import Itemgroup, Itemgroups

from alignak.util import get_obj_name
from alignak.property import StringProp, IntegerProp
from alignak.log import logger


class Hostgroup(Itemgroup):
    """
    Class to manage a group of host
    A Hostgroup is used to manage a group of hosts
    """
    id = 1  # zero is always a little bit special... like in database
    my_type = 'hostgroup'

    properties = Itemgroup.properties.copy()
    properties.update({
        'id':             IntegerProp(default=0, fill_brok=['full_status']),
        'hostgroup_name': StringProp(fill_brok=['full_status']),
        'alias':          StringProp(fill_brok=['full_status']),
        'notes':          StringProp(default='', fill_brok=['full_status']),
        'notes_url':      StringProp(default='', fill_brok=['full_status']),
        'action_url':     StringProp(default='', fill_brok=['full_status']),
        'realm':          StringProp(default='', fill_brok=['full_status'],
                                     conf_send_preparation=get_obj_name),
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
        else:
            return []

    def get_hostgroup_members(self):
        """
        Get hostgroup members

        :return: list of hosts
        :rtype: list
        """
        if self.has('hostgroup_members'):
            return [m.strip() for m in self.hostgroup_members.split(',')]
        else:
            return []

    def get_hosts_by_explosion(self, hostgroups):
        """
        Get hosts of this group

        :param hostgroups: Hostgroup object
        :type hostgroups: object
        :return: list of hosts of this group
        :rtype: list
        """
        # First we tag the hg so it will not be explode
        # if a son of it already call it
        self.already_explode = True

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
            hg = hostgroups.find_by_name(hg_mbr.strip())
            if hg is not None:
                value = hg.get_hosts_by_explosion(hostgroups)
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

    def get_members_by_name(self, hgname):
        """
        Get all members by name given in parameter

        :param hgname: name of members
        :type hgname: str
        :return: list of hosts with this name
        :rtype: list
        """
        hg = self.find_by_name(hgname)
        if hg is None:
            return []
        return hg.get_hosts()


    def linkify(self, hosts=None, realms=None):
        """
        Make link of hosts / realms

        :param hosts: object Hosts
        :type hosts: object
        :param realms: object Realms
        :type realms: object
        """
        self.linkify_hg_by_hst(hosts)
        self.linkify_hg_by_realms(realms)


    def linkify_hg_by_hst(self, hosts):
        """
        We just search for each hostgroup the id of the hosts
        and replace the name by the id

        :param hosts: object Hosts
        :type hosts: object
        """
        for hg in self:
            mbrs = hg.get_hosts()
            # The new member list, in id
            new_mbrs = []
            for mbr in mbrs:
                mbr = mbr.strip()  # protect with strip at the begining so don't care about spaces
                if mbr == '':  # void entry, skip this
                    continue
                elif mbr == '*':
                    new_mbrs.extend(hosts)
                else:
                    h = hosts.find_by_name(mbr)
                    if h is not None:
                        new_mbrs.append(h)
                    else:
                        hg.add_string_unknown_member(mbr)

            # Make members uniq
            new_mbrs = list(set(new_mbrs))

            # We find the id, we replace the names
            hg.replace_members(new_mbrs)

            # Now register us in our members
            for h in hg.members:
                h.hostgroups.append(hg)
                # and be sure we are uniq in it
                h.hostgroups = list(set(h.hostgroups))

    def linkify_hg_by_realms(self, realms):
        """
        More than an explode function, but we need to already
        have members so... Will be really linkify just after
        And we explode realm in ours members, but do not override
        a host realm value if it's already set

        :param realms: object Realms
        :type realms: object
        """
        # Now we explode the realm value if we've got one
        # The group realm must not override a host one (warning?)
        for hg in self:
            if not hasattr(hg, 'realm'):
                continue

            # Maybe the value is void?
            if not hg.realm.strip():
                continue

            r = realms.find_by_name(hg.realm.strip())
            if r is not None:
                hg.realm = r
                logger.debug("[hostgroups] %s is in %s realm", hg.get_name(), r.get_name())
            else:
                err = "the hostgroup %s got an unknown realm '%s'" % (hg.get_name(), hg.realm)
                hg.configuration_errors.append(err)
                hg.realm = None
                continue

            for h in hg:
                if h is None:
                    continue
                if h.realm is None or h.got_default_realm:  # default value not hasattr(h, 'realm'):
                    logger.debug("[hostgroups] apply a realm %s to host %s from a hostgroup "
                                 "rule (%s)", hg.realm.get_name(), h.get_name(), hg.get_name())
                    h.realm = hg.realm
                else:
                    if h.realm != hg.realm:
                        logger.warning("[hostgroups] host %s it not in the same realm than it's "
                                       "hostgroup %s", h.get_name(), hg.get_name())

    def add_member(self, hname, hgname):
        """
        Add a host string to a hostgroup member
        if the host group do not exist, create it

        :param hname: host name
        :type hname: str
        :param hgname:hostgroup name
        :type hgname: str
        """
        hg = self.find_by_name(hgname)
        # if the id do not exist, create the hg
        if hg is None:
            hg = Hostgroup({'hostgroup_name': hgname, 'alias': hgname, 'members': hname})
            self.add(hg)
        else:
            hg.add_string_member(hname)

    def explode(self):
        """
        Fill members with hostgroup_members
        """
        # We do not want a same hg to be explode again and again
        # so we tag it
        for tmp_hg in self.items.values():
            tmp_hg.already_explode = False
        for hg in self.items.values():
            if hg.has('hostgroup_members') and not hg.already_explode:
                # get_hosts_by_explosion is a recursive
                # function, so we must tag hg so we do not loop
                for tmp_hg in self.items.values():
                    tmp_hg.rec_tag = False
                hg.get_hosts_by_explosion(self)

        # We clean the tags
        for tmp_hg in self.items.values():
            if hasattr(tmp_hg, 'rec_tag'):
                del tmp_hg.rec_tag
            del tmp_hg.already_explode
