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
#     Dessai.Imrane, dessai.imrane@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Andreas Karfusehr, frescha@unitedseed.de
#     Jonathan GAULUPEAU, jonathan@gaulupeau.com
#     Frédéric MOHIER, frederic.mohier@ipmfrance.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Romain Forlot, rforlot@yahoo.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     David Gil, david.gil.marcos@gmail.com

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
datamanager module provide DataManager class :
a simple class providing accessor to various Alignak object"
Used by module such as Livestatus and Webui
"""

from alignak.util import safe_print
from alignak.misc.sorter import hst_srv_sort, last_state_change_earlier
from alignak.misc.filter import only_related_to

class DataManager(object):
    """
    DataManager provide a set of accessor to Alignak objects
    (host, services) through a regenerator object.
    """
    def __init__(self):
        self.rg = None

    def load(self, rg):
        """
        Set the regenerator attribute

        :param rg:
        :type rg: alignak.misc.regenerator.Regenerator
        :return: None
        """
        self.rg = rg

    def get_host(self, hname):
        """
        Get a specific host from Alignak

        :param hname: A host name (a casual string)
        :return: the Host object with host_name=hname
        :rtype: alignak.objects.host.Host
        """
        # UI will launch us names in str, we got unicode
        # in our rg, so we must manage it here
        hname = hname.decode('utf8', 'ignore')
        return self.rg.hosts.find_by_name(hname)

    def get_service(self, hname, sdesc):
        """
        :param hname: A host name (a casual string)
        :param sdesc: A service description (a casual string)
        :return: the Service object with host_name=hname and service_description=sdec
        :rtype: alignak.objects.service.Service
        """
        hname = hname.decode('utf8', 'ignore')
        sdesc = sdesc.decode('utf8', 'ignore')
        return self.rg.services.find_srv_by_name_and_hostname(hname, sdesc)

    def get_all_hosts_and_services(self):
        """
        Get all host and all service in a single list

        :return: A list containing all host and service
        :rtype: list
        """
        all = []
        all.extend(self.rg.hosts)
        all.extend(self.rg.services)
        return all

    def get_contact(self, name):
        """
        Get a specific contact

        :param name: A contact name (casual string)
        :return: the Contact object with contact_name=name
        :rtype: alignak.objects.contact.Contact
        """
        name = name.decode('utf8', 'ignore')
        return self.rg.contacts.find_by_name(name)

    def get_contactgroup(self, name):
        """
        Get a specific contact group

        :param name: A contactgroup name (casual string)
        :return: the Contact object with contactgroup_name=name
        :rtype: alignak.objects.contactgroup.Contactgroup
        """
        name = name.decode('utf8', 'ignore')
        return self.rg.contactgroups.find_by_name(name)

    def get_contacts(self):
        """
        Get all contacts

        :return: List of all contacts
        :rtype: list
        """
        return self.rg.contacts

    def get_hostgroups(self):
        """
        Get all hostgroups

        :return: List of all hostgroups
        :rtype: list
        """
        return self.rg.hostgroups

    def get_hostgroup(self, name):
        """
        Get a specific host group

        :param name: A hostgroup name (casual string)
        :return: the Contact object with hostgroup_name=name
        :rtype: alignak.objects.hostgroup.Hostgroup
        """
        return self.rg.hostgroups.find_by_name(name)

    def get_servicegroups(self):
        """
        Get all servicegroups

        :return: List of all servicegroups
        :rtype: list
        """
        return self.rg.servicegroups

    def get_servicegroup(self, name):
        """
        Get a specific service group

        :param name: A servicegroup name (casual string)
        :return: the Contact object with servicegroup_name=name
        :rtype: alignak.objects.servicegroup.Servicegroup
        """
        return self.rg.servicegroups.find_by_name(name)

    def get_hostgroups_sorted(self, selected=''):
        """
        Get hostgroups sorted by names, and zero size in the end
        if selected one, put it in the first place

        :param selected: A hostgroup name (casual string)
        :return: A sorted hostgroup list
        :rtype: list
        """
        r = []
        selected = selected.strip()

        hg_names = [hg.get_name() for hg in self.rg.hostgroups
                    if len(hg.members) > 0 and hg.get_name() != selected]
        hg_names.sort()
        hgs = [self.rg.hostgroups.find_by_name(n) for n in hg_names]
        hgvoid_names = [hg.get_name() for hg in self.rg.hostgroups
                        if len(hg.members) == 0 and hg.get_name() != selected]
        hgvoid_names.sort()
        hgvoids = [self.rg.hostgroups.find_by_name(n) for n in hgvoid_names]

        if selected:
            hg = self.rg.hostgroups.find_by_name(selected)
            if hg:
                r.append(hg)

        r.extend(hgs)
        r.extend(hgvoids)

        return r

    def get_hosts(self):
        """
        Get all hosts

        :return: List of all hosts
        :rtype: list
        """
        return self.rg.hosts

    def get_services(self):
        """
        Get all services

        :return: List of all services
        :rtype: list
        """
        return self.rg.services

    def get_schedulers(self):
        """
        Get all schedulers

        :return: List of all schedulers
        :rtype: list
        """
        return self.rg.schedulers

    def get_pollers(self):
        """
        Get all pollers

        :return: List of all pollers
        :rtype: list
        """
        return self.rg.pollers

    def get_brokers(self):
        """
        Get all brokers

        :return: List of all brokers
        :rtype: list
        """
        return self.rg.brokers

    def get_receivers(self):
        """
        Get all receivers

        :return: List of all receivers
        :rtype: list
        """
        return self.rg.receivers

    def get_reactionners(self):
        """
        Get all reactionners

        :return: List of all reactionners
        :rtype: list
        """
        return self.rg.reactionners

    def get_program_start(self):
        """
        Get program start time

        :return: Timestamp representing start time
        :rtype: int
        """
        for c in self.rg.configs.values():
            return c.program_start
        return None

    def get_realms(self):
        """
        Get all realms

        :return: List of all realms
        :rtype: list
        """
        return self.rg.realms

    def get_realm(self, r):
        # TODO : Remove this
        """
        Get a specific realm, but this will return None always

        :param name: A realm name (casual string)
        :return: the Realm object with realm_name=name (that's not true)
        :rtype: alignak.objects.realm.Realm
        """
        if r in self.rg.realms:
            return r
        return None

    def get_host_tags_sorted(self):
        """
        Get hosts tags sorted by names, and zero size in the end

        :return: list of hosts tags
        :rtype: list
        """
        r = []
        names = self.rg.tags.keys()
        names.sort()
        for n in names:
            r.append((n, self.rg.tags[n]))
        return r

    def get_hosts_tagged_with(self, tag):
        """
        Get hosts tagged with a specific tag

        :param name: A tag name (casual string)
        :return:  Hosts list with tag in host tags
        :rtype: alignak.objects.host.Host
        """
        r = []
        for h in self.get_hosts():
            if tag in h.get_host_tags():
                r.append(h)
        return r

    def get_service_tags_sorted(self):
        """
        Get services tags sorted by names, and zero size in the end

        :return: list of services tags
        :rtype: list
        """
        r = []
        names = self.rg.services_tags.keys()
        names.sort()
        for n in names:
            r.append((n, self.rg.services_tags[n]))
        return r

    def get_important_impacts(self):
        """
        Get hosts and services with :
        * not OK state
        * business impact > 2
        * is_impact flag true

        :return: list of host and services
        :rtype: list
        """
        res = []
        for s in self.rg.services:
            if s.is_impact and s.state not in ['OK', 'PENDING']:
                if s.business_impact > 2:
                    res.append(s)
        for h in self.rg.hosts:
            if h.is_impact and h.state not in ['UP', 'PENDING']:
                if h.business_impact > 2:
                    res.append(h)
        return res

    def get_all_problems(self, to_sort=True, get_acknowledged=False):
        """
        Get hosts and services with:

        * not OK state
        * is_impact flag false
        * Do not include acknowledged items by default
        * Sort items by default

        :param to_sort: if false, won't sort results
        :param get_acknowledged: if true will include acknowledged items
        :return: A list of host and service
        :rtype: list
        """
        res = []
        if not get_acknowledged:
            res.extend([s for s in self.rg.services
                        if s.state not in ['OK', 'PENDING'] and
                        not s.is_impact and not s.problem_has_been_acknowledged and
                        not s.host.problem_has_been_acknowledged])
            res.extend([h for h in self.rg.hosts
                        if h.state not in ['UP', 'PENDING'] and
                        not h.is_impact and not h.problem_has_been_acknowledged])
        else:
            res.extend([s for s in self.rg.services
                        if s.state not in ['OK', 'PENDING'] and not s.is_impact])
            res.extend([h for h in self.rg.hosts
                        if h.state not in ['UP', 'PENDING'] and not h.is_impact])

        if to_sort:
            res.sort(hst_srv_sort)
        return res

    def get_problems_time_sorted(self):
        """
        Get all problems with the most recent before

        :return: A list of host and service
        :rtype: list
        """
        pbs = self.get_all_problems(to_sort=False)
        pbs.sort(last_state_change_earlier)
        return pbs

    def get_all_impacts(self):
        """
        Get all non managed impacts

        :return: A list of host and service
        :rtype: list
        """
        res = []
        for s in self.rg.services:
            if s.is_impact and s.state not in ['OK', 'PENDING']:
                # If s is acked, pass
                if s.problem_has_been_acknowledged:
                    continue
                # We search for impacts that were NOT currently managed
                if sum(1 for p in s.source_problems
                       if not p.problem_has_been_acknowledged) > 0:
                    res.append(s)
        for h in self.rg.hosts:
            if h.is_impact and h.state not in ['UP', 'PENDING']:
                # If h is acked, pass
                if h.problem_has_been_acknowledged:
                    continue
                # We search for impacts that were NOT currently managed
                if sum(1 for p in h.source_problems
                       if not p.problem_has_been_acknowledged) > 0:
                    res.append(h)
        return res

    def get_nb_problems(self):
        """
        Get the number of problems (host or service)

        :return: An integer representing the number of non acknowledged problems
        """
        return len(self.get_all_problems(to_sort=False))

    def get_nb_all_problems(self, user):
        """
        Get the number of problems (host or service) including acknowledged ones for a specific user

        :param user: A contact (Ui user maybe) (casual string)
        :return: A list of host and service with acknowledged problem for contact=user
        """
        res = []
        res.extend([s for s in self.rg.services
                    if s.state not in ['OK', 'PENDING'] and not s.is_impact])
        res.extend([h for h in self.rg.hosts
                    if h.state not in ['UP', 'PENDING'] and not h.is_impact])
        return len(only_related_to(res, user))

    def get_nb_impacts(self):
        """
        Get the number of impacts (host or service)

        :return: An integer representing the number of impact items
        """
        return len(self.get_all_impacts())

    def get_nb_elements(self):
        """
        Get the number of hosts and services (sum)

        :return: An integer representing the number of items
        """
        return len(self.rg.services) + len(self.rg.hosts)

    def get_important_elements(self):
        """
        Get hosts and services with :
        * business impact > 2
        * 0 <= my_own_business_impact <= 2

        :return: list of host and services
        :rtype: list
        """
        res = []
        # We want REALLY important things, so business_impact > 2, but not just IT elements that are
        # root problems, so we look only for config defined my_own_business_impact value too
        res.extend([s for s in self.rg.services
                    if (s.business_impact > 2 and not 0 <= s.my_own_business_impact <= 2)])
        res.extend([h for h in self.rg.hosts
                    if (h.business_impact > 2 and not 0 <= h.my_own_business_impact <= 2)])
        print "DUMP IMPORTANT"
        for i in res:
            safe_print(i.get_full_name(), i.business_impact, i.my_own_business_impact)
        return res

    def get_overall_state(self):
        """
        Get the worst state of all hosts and service with:
        * business impact > 2
        * is_impact flag true
        * state_id equals 1 or 2 (warning or critical state)
        Used for aggregation

        :return: An integer between 0 and 2
        """
        h_states = [h.state_id for h in self.rg.hosts
                    if h.business_impact > 2 and h.is_impact and h.state_id in [1, 2]]
        s_states = [s.state_id for s in self.rg.services
                    if s.business_impact > 2 and s.is_impact and s.state_id in [1, 2]]
        print "get_overall_state:: hosts and services business problems", h_states, s_states
        if len(h_states) == 0:
            h_state = 0
        else:
            h_state = max(h_states)
        if len(s_states) == 0:
            s_state = 0
        else:
            s_state = max(s_states)
        # Ok, now return the max of hosts and services states
        return max(h_state, s_state)

    def get_overall_it_state(self):
        """
        Get the worst state of all hosts and services with:
        * is_impact flag true
        * state_id equals 1 or 2 (warning or critical state)
        Used for aggregation

        :return: An integer between 0 and 2
        """
        h_states = [h.state_id for h in self.rg.hosts if h.is_problem and h.state_id in [1, 2]]
        s_states = [s.state_id for s in self.rg.services if s.is_problem and s.state_id in [1, 2]]
        if len(h_states) == 0:
            h_state = 0
        else:
            h_state = max(h_states)
        if len(s_states) == 0:
            s_state = 0
        else:
            s_state = max(s_states)
        # Ok, now return the max of hosts and services states
        return max(h_state, s_state)

    # Get percent of all Services
    def get_per_service_state(self):
        """
        Get the percentage of services with :
        * is_impact flag false
        * not OK state

        :return: An integer representing the percentage of services fulfilling the above condition
        """
        all_services = self.rg.services
        problem_services = []
        problem_services.extend([s for s in self.rg.services
                                 if s.state not in ['OK', 'PENDING'] and not s.is_impact])
        if len(all_services) == 0:
            res = 0
        else:
            res = int(100 - (len(problem_services) * 100) / float(len(all_services)))
        return res

    def get_per_hosts_state(self):
        """
        Get the percentage of hosts with :
        * is_impact flag false
        * not OK state

        :return: An integer representing the percentage of hosts fulfilling the above condition
        """
        all_hosts = self.rg.hosts
        problem_hosts = []
        problem_hosts.extend([s for s in self.rg.hosts
                              if s.state not in ['UP', 'PENDING'] and not s.is_impact])
        if len(all_hosts) == 0:
            res = 0
        else:
            res = int(100 - (len(problem_hosts) * 100) / float(len(all_hosts)))
        return res

    def get_len_overall_state(self):
        """
        Get the number of hosts and services with:
        * business impact > 2
        * is_impact flag true
        * state_id equals 1 or 2 (warning or critical state)
        Used for aggregation

        :return: An integer representing the number of hosts and services
         fulfilling the above condition
        """
        h_states = [h.state_id for h in self.rg.hosts
                    if h.business_impact > 2 and h.is_impact and h.state_id in [1, 2]]
        s_states = [s.state_id for s in self.rg.services
                    if s.business_impact > 2 and s.is_impact and s.state_id in [1, 2]]
        print "get_len_overall_state:: hosts and services business problems", h_states, s_states
        # Just return the number of impacting elements
        return len(h_states) + len(s_states)

    def get_business_parents(self, obj, levels=3):
        """
        Get the dependencies tree of a specific host or service up to a specific dept
        Tree only include non OK state_id

        :param obj: host or service to start the recursion
        :type obj: alignak.objects.schedulingitem.SchedulingItem
        :param levels: maximum dept to process
        :type levels: int
        :return: A dict with the following structure
        ::
         
           { 'node': obj,
             'fathers': [
                         {'node': Host_Object1, fathers: [...]},
                         {'node': Host_Object2, fathers: [...]},
                        ]
           }
        
        :rtype: dict
        """
        res = {'node': obj, 'fathers': []}
        # if levels == 0:
        #     return res

        for i in obj.parent_dependencies:
            # We want to get the levels deep for all elements, but
            # go as far as we should for bad elements
            if levels != 0 or i.state_id != 0:
                par_elts = self.get_business_parents(i, levels=levels - 1)
                res['fathers'].append(par_elts)

        print "get_business_parents::Give elements", res
        return res

    def guess_root_problems(self, obj):
        """
        Get the list of services with :
        * a state_id != 0 (not OK state)
        * linked to the same host
        for a given service.

        :param obj: service we want to get non OK services linked to its host
        :type obj: alignak.objects.schedulingitem.SchedulingItem
        :return: A service list with state_id != 0
        :rtype: list
        """
        if obj.__class__.my_type != 'service':
            return []
        r = [s for s in obj.host.services if s.state_id != 0 and s != obj]
        return r

datamgr = DataManager()
