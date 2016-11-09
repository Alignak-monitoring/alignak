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
#     Alexandre Viau, alexandre@alexandreviau.net
#     aviau, alexandre.viau@savoirfairelinux.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Romain Forlot, rforlot@yahoo.com
#     Christophe SIMON, christophe.simon@dailymotion.com

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
"""This module provides Realm and Realms classes that
implements realm for Alignak. Basically used for parsing.

"""
import copy
import logging
from alignak.objects.item import Item
from alignak.objects.itemgroup import Itemgroup, Itemgroups
from alignak.property import BoolProp, StringProp, DictProp, ListProp

logger = logging.getLogger(__name__)  # pylint: disable=C0103

# It change from hostgroup Class because there is no members
# properties, just the realm_members that we rewrite on it.


class Realm(Itemgroup):
    """Realm class is used to implement realm. It is basically a set of Host or Service
    assigned to a specific set of Scheduler/Poller (other daemon are optional)

    """
    my_type = 'realm'

    properties = Itemgroup.properties.copy()
    properties.update({
        'uuid':
            StringProp(default='', fill_brok=['full_status']),
        'realm_name':
            StringProp(fill_brok=['full_status']),
        'alias':
            StringProp(fill_brok=['full_status']),
        # No status_broker_name because it put hosts, not host_name
        'realm_members':
            ListProp(default=[], split_on_coma=True),
        'higher_realms':
            ListProp(default=[], split_on_coma=True),
        'default':
            BoolProp(default=False),
    })

    running_properties = Item.running_properties.copy()
    running_properties.update({
        'serialized_confs': DictProp(default={}),
        'unknown_higher_realms': ListProp(default=[])
    })

    macros = {
        'REALMNAME': 'realm_name',
        'REALMMEMBERS': 'members',
    }

    potential_pollers = []
    potential_reactionners = []
    potential_brokers = []
    potential_receivers = []

    def get_name(self):
        """Accessor to realm_name attribute

        :return: realm name
        :rtype: str
        """
        return self.realm_name

    def get_realms(self):
        """
        Get list of members of this realm

        :return: list of realm (members)
        :rtype: list
        TODO: Duplicate of get_realm_members
        """
        return self.realm_members

    def add_string_member(self, member):
        """Add a realm to realm_members attribute

        :param member: realm name to add
        :type member:
        :return: None
        TODO : Clean this self.members != self.realm_members?
        """
        self.realm_members.append(member)

    def add_string_unknown_higher(self, member):
        """
        Add new entry(member) to unknown higher realms list

        :param member: member name
        :type member: str
        :return: None
        """
        add_fun = list.extend if isinstance(member, list) else list.append
        if not self.unknown_higher_realms:
            self.unknown_higher_realms = []
        add_fun(self.unknown_higher_realms, member)

    def get_realm_members(self):
        """
        Get list of members of this realm

        :return: list of realm (members)
        :rtype: list
        """
        # TODO: consistency: a Realm instance should always have its real_members defined,
        if hasattr(self, 'realm_members'):
            # more over it should already be decoded/parsed to its final type:
            # a list of strings (being the names of the members)
            return [r.strip() for r in self.realm_members]
        else:
            return []

    def get_realms_by_explosion(self, realms):
        """Get all members of this realm including members of sub-realms

        :param realms: realms list, used to look for a specific one
        :type realms: alignak.objects.realm.Realms
        :return: list of members and add realm to realm_members attribute
        :rtype: list
        TODO: Clean this function that silently edit realm_members.
        """
        # First we tag the hg so it will not be explode
        # if a son of it already call it
        self.already_explode = True

        # Now the recursive part
        # rec_tag is set to False every HG we explode
        # so if True here, it must be a loop in HG
        # calls... not GOOD!
        if self.rec_tag:
            err = "Error: we've got a loop in realm definition %s" % self.get_name()
            self.configuration_errors.append(err)
            if hasattr(self, 'members'):
                return self.members
            else:
                return []

        # Ok, not a loop, we tag it and continue
        self.rec_tag = True

        p_mbrs = self.get_realm_members()
        for p_mbr in p_mbrs:
            realm = realms.find_by_name(p_mbr.strip())
            if realm is not None:
                value = realm.get_realms_by_explosion(realms)
                if len(value) > 0:
                    self.add_string_member(value)

        if hasattr(self, 'members'):
            return self.members
        else:
            return []

    def get_all_subs_satellites_by_type(self, sat_type, realms):
        """Get all satellites of the wanted type in this realm recursively

        :param sat_type: satellite type wanted (scheduler, poller ..)
        :type sat_type:
        :param realms: all realms
        :type realms: list of realm object
        :return: list of satellite in this realm
        :rtype: list
        TODO: Make this generic
        """
        res = copy.copy(getattr(self, sat_type))
        for member in self.realm_members:
            tmps = realms[member].get_all_subs_satellites_by_type(sat_type, realms)
            for mem in tmps:
                res.append(mem)
        return res

    def get_satellites_by_type(self, s_type):
        """Generic function to access one of the satellite attribute
        ie : self.pollers, self.reactionners ...

        :param s_type: satellite type wanted
        :type s_type: str
        :return: self.*type*s
        :rtype: list
        """

        if hasattr(self, s_type + 's'):
            return getattr(self, s_type + 's')
        else:
            logger.debug("[realm] do not have this kind of satellites: %s", s_type)
            return []

    def get_potential_satellites_by_type(self, s_type):
        """Generic function to access one of the potential satellite attribute
        ie : self.potential_pollers, self.potential_reactionners ...

        :param s_type: satellite type wanted
        :type s_type: str
        :return: self.potential_*type*s
        :rtype: list
        """
        if hasattr(self, 'potential_' + s_type + 's'):
            return getattr(self, 'potential_' + s_type + 's')
        else:
            logger.debug("[realm] do not have this kind of satellites: %s", s_type)
            return []

    def get_nb_of_must_have_satellites(self, s_type):
        """Generic function to access one of the number satellite attribute
        ie : self.nb_pollers, self.nb_reactionners ...

        :param s_type: satellite type wanted
        :type s_type: str
        :return: self.nb_*type*s
        :rtype: int
        """
        if hasattr(self, 'nb_' + s_type + 's'):
            return getattr(self, 'nb_' + s_type + 's')
        else:
            logger.debug("[realm] do not have this kind of satellites: %s", s_type)
            return 0

    def fill_broker_with_poller_reactionner_links(self, broker, pollers, reactionners, receivers,
                                                  realms):
        """Fill brokerlink object with satellite data

        :param broker: broker link we want to fill
        :type broker: alignak.objects.brokerlink.Brokerlink
        :param pollers: pollers
        :type pollers:
        :param reactionners: reactionners
        :type reactionners:
        :param receivers: receivers
        :type receivers:
        :param realms: realms
        :type realms:
        :return: None
        """

        # TODO: find a better name...
        # TODO: and if he goes active?
        # First we create/void theses links
        broker.cfg['pollers'] = {}
        broker.cfg['reactionners'] = {}
        broker.cfg['receivers'] = {}

        # First our own level
        for poller_id in self.pollers:
            poller = pollers[poller_id]
            cfg = poller.give_satellite_cfg()
            broker.cfg['pollers'][poller.uuid] = cfg

        for reactionner_id in self.reactionners:
            reactionner = reactionners[reactionner_id]
            cfg = reactionner.give_satellite_cfg()
            broker.cfg['reactionners'][reactionner.uuid] = cfg

        for receiver_id in self.receivers:
            receiver = receivers[receiver_id]
            cfg = receiver.give_satellite_cfg()
            broker.cfg['receivers'][receiver.uuid] = cfg

        # Then sub if we must to it
        if broker.manage_sub_realms:
            # Now pollers
            for poller_id in self.get_all_subs_satellites_by_type('pollers', realms):
                poller = pollers[poller_id]
                cfg = poller.give_satellite_cfg()
                broker.cfg['pollers'][poller.uuid] = cfg

            # Now reactionners
            for reactionner_id in self.get_all_subs_satellites_by_type('reactionners', realms):
                reactionner = reactionners[reactionner_id]
                cfg = reactionner.give_satellite_cfg()
                broker.cfg['reactionners'][reactionner.uuid] = cfg

            # Now receivers
            for receiver_id in self.get_all_subs_satellites_by_type('receivers', realms):
                receiver = receivers[receiver_id]
                cfg = receiver.give_satellite_cfg()
                broker.cfg['receivers'][receiver.uuid] = cfg

    def get_satellites_links_for_scheduler(self, pollers, reactionners, brokers):
        """Get a configuration dict with pollers, reactionners and brokers data for scheduler

        :return: dict containing pollers, reactionners and brokers config (key is satellite id)
        :rtype: dict
        """

        # First we create/void theses links
        cfg = {
            'pollers': {},
            'reactionners': {},
            'brokers': {},
        }

        # First our own level
        for poller_id in self.pollers:
            poller = pollers[poller_id]
            config = poller.give_satellite_cfg()
            cfg['pollers'][poller.uuid] = config

        for reactionner_id in self.reactionners:
            reactionner = reactionners[reactionner_id]
            config = reactionner.give_satellite_cfg()
            cfg['reactionners'][reactionner.uuid] = config

        for broker_id in self.brokers:
            broker = brokers[broker_id]
            config = broker.give_satellite_cfg()
            cfg['brokers'][broker.uuid] = config

        return cfg


class Realms(Itemgroups):
    """Realms manage a list of Realm objects, used for parsing configuration

    """
    name_property = "realm_name"  # is used for finding hostgroups
    inner_class = Realm

    def get_members_by_name(self, pname):
        """Get realm_members for a specific realm

        :param pname: realm name
        :type: str
        :return: list of realm members
        :rtype: list
        """
        realm = self.find_by_name(pname)
        if realm is None:
            return []
        return realm.get_realms()

    def linkify(self):
        """Links sub-realms (parent / son),
        add new realm_members,
        and init each realm following attributes ::

        * pollers      : []
        * schedulers   : []
        * reactionners.: []
        * brokers:     : []
        * receivers:   : []
        * packs:       : []
        * confs:       : {}

        :return: None
        """
        self.linkify_p_by_p()

        # prepare list of satellites and confs
        for realm in self:
            realm.pollers = []
            realm.schedulers = []
            realm.reactionners = []
            realm.brokers = []
            realm.receivers = []
            realm.packs = []
            realm.confs = {}

    def linkify_p_by_p(self):
        """Links sub-realms (parent / son)
        Realm are links with two properties : realm_members and higher_realms
        Each of them can be manually specified by the user.
        For each entry in one of this two, a parent/son realm has to be edited also

        Example : A realm foo with realm_members == [bar].
        foo will be added into bar.higher_realms.


        :return: None
        """
        for realm in self.items.values():
            mbrs = realm.get_realm_members()
            # The new member list, in id
            new_mbrs = []
            for mbr in mbrs:
                if mbr in self:
                    # We have a uuid here not a name
                    new_mbrs.append(mbr)
                    continue
                new_mbr = self.find_by_name(mbr)
                if new_mbr is not None:
                    new_mbrs.append(new_mbr.uuid)
                    # We need to recreate the list, otherwise we will append
                    # to a global list. Default value and mutable are not a good mix
                    if new_mbr.higher_realms == []:
                        new_mbr.higher_realms = []
                    new_mbr.higher_realms.append(realm.uuid)
                else:
                    realm.add_string_unknown_member(mbr)
            # Add son ids into parent
            realm.realm_members = new_mbrs

            # Now linkify the higher member, this variable is populated
            # by user or during the previous loop (from another realm)
            new_highers = []
            for higher in realm.higher_realms:
                if higher in self:
                    # We have a uuid here not a name
                    new_highers.append(higher)
                    continue
                new_higher = self.find_by_name(higher)
                if new_higher is not None:
                    new_highers.append(new_higher.uuid)
                    # We need to recreate the list, otherwise we will append
                    # to a global list. Default value and mutable are not a good mix
                    if new_higher.realm_members == []:
                        new_higher.realm_members = []
                    # Higher realm can also be specifiec manually so we
                    # need to add the son realm into members of the higher one
                    new_higher.realm_members.append(realm.uuid)
                else:
                    realm.add_string_unknown_higher(higher)

            realm.higher_realms = new_highers

    def explode(self):
        """Explode realms with each realm_members

        :return: None
        """
        # We do not want a same hg to be explode again and again
        # so we tag it
        for tmp_p in self.items.values():
            tmp_p.already_explode = False
        for realm in self:
            if hasattr(realm, 'realm_members') and not realm.already_explode:
                # get_hosts_by_explosion is a recursive
                # function, so we must tag hg so we do not loop
                for tmp_p in self:
                    tmp_p.rec_tag = False
                realm.get_realms_by_explosion(self)

        # We clean the tags
        for tmp_p in self.items.values():
            if hasattr(tmp_p, 'rec_tag'):
                del tmp_p.rec_tag
            del tmp_p.already_explode

    def get_default(self):
        """Get the default realm

        :return: Default realm of Alignak configuration
        :rtype: alignak.objects.realm.Realm | None
        """
        for realm in self:
            if getattr(realm, 'default', False):
                return realm
        return None

    def prepare_for_satellites_conf(self, satellites):
        """Init the following attributes for each realm::

        * to_satellites (with *satellite type* keys)
        * to_satellites_need_dispatch (with *satellite type* keys)
        * to_satellites_managed_by (with *satellite type* keys)
        * nb_*satellite type*s
        * self.potential_*satellite type*s

        (satellite type are reactionner, poller, broker and receiver)

        :param satellites: saletellites objects (broker, reactionner, poller, receiver)
        :type satellites: tuple
        :return: None
        """
        for realm in self:
            realm.to_satellites = {
                'reactionner': {},
                'poller': {},
                'broker': {},
                'receiver': {}
            }

            realm.to_satellites_need_dispatch = {
                'reactionner': {},
                'poller': {},
                'broker': {},
                'receiver': {}
            }

            realm.to_satellites_managed_by = {
                'reactionner': {},
                'poller': {},
                'broker': {},
                'receiver': {}
            }

            # Generic loop to fil nb_* (counting) and fill potential_* attribute.
            # Counting is not that difficult but as it's generic, getattr and setattr are required
            for i, sat in enumerate(["reactionner", "poller", "broker", "receiver"]):
                setattr(realm, "nb_%ss" % sat, 0)  # Init nb_TYPE at 0
                setattr(realm, 'potential_%ss' % sat, [])  # Init potential_TYPE at []
                # We get potential TYPE at realm level first
                for elem_id in getattr(realm, "%ss" % sat):  # For elem in realm.TYPEs
                    elem = satellites[i][elem_id]  # Get the realm TYPE object
                    if not elem.spare:
                        # Generic increment : realm.nb_TYPE += 1
                        setattr(realm, "nb_%ss" % sat, getattr(realm, "nb_%ss" % sat) + 1)
                    # Append elem to realm.potential_TYPE
                    getattr(realm, 'potential_%ss' % sat).append(elem.uuid)

                # Now we look for potential_TYPE in higher realm
                # if the TYPE manage sub realm then it's a potential TYPE
                # We also need to count TYPE
                # TODO: Change higher realm type because we are falsely looping on all higher realms
                # higher_realms is usually of len 1 (no sense to have 2 higher realms)
                high_realm = realm
                above_realm = None
                while getattr(high_realm, "higher_realms", []):
                    for r_id in high_realm.higher_realms:
                        above_realm = self[r_id]
                        for elem_id in getattr(above_realm, "%ss" % sat):
                            elem = satellites[i][elem_id]
                            if not elem.spare and elem.manage_sub_realms:
                                setattr(realm, "nb_%ss" % sat, getattr(realm, "nb_%ss" % sat) + 1)
                            if elem.manage_sub_realms:
                                getattr(realm, 'potential_%ss' % sat).append(elem.uuid)

                    high_realm = above_realm

            line = "%s: (in/potential) (schedulers:%d) (pollers:%d/%d)" \
                   " (reactionners:%d/%d) (brokers:%d/%d) (receivers:%d/%d)" % \
                (realm.get_name(),
                 len(realm.schedulers),
                 realm.nb_pollers, len(realm.potential_pollers),
                 realm.nb_reactionners, len(realm.potential_reactionners),
                 realm.nb_brokers, len(realm.potential_brokers),
                 realm.nb_receivers, len(realm.potential_receivers)
                 )
            logger.info(line)

    def fill_potential_satellites_by_type(self, sat_type, realm, satellites):
        """Edit potential_*sat_type* attribute to get potential satellite from upper level realms

        :param sat_type: satellite type wanted
        :type sat_type: str
        :param realm: the realm we want to fill potential attribute
        :type realm: alignak.objects.realm.Realm
        :param satellites: items corresponding to the wanted type
        :type satellites: alignak.objects.item.Items
        :return: None
        """
        setattr(realm, 'potential_%s' % sat_type, [])
        for elem_id in getattr(realm, sat_type):
            elem = satellites[elem_id]
            getattr(realm, 'potential_%s' % sat_type).append(elem.uuid)

        # Now we look for potential_TYPE in higher realm
        # if the TYPE manage sub realm then it's a potential TYPE
        # We also need to count TYPE
        # TODO: Change higher realm type because we are falsely looping on all higher realms
        # higher_realms is usually of len 1 (no sense to have 2 higher realms)
        high_realm = realm
        above_realm = None
        while getattr(high_realm, "higher_realms", []):
            for r_id in high_realm.higher_realms:
                above_realm = self[r_id]
                for elem_id in getattr(above_realm, "%s" % sat_type):
                    elem = satellites[elem_id]
                    if not elem.spare and elem.manage_sub_realms:
                        setattr(realm, "nb_%s" % sat_type, getattr(realm, "nb_%s" % sat_type) + 1)
                    if elem.manage_sub_realms:
                        getattr(realm, 'potential_%s' % sat_type).append(elem.uuid)

            high_realm = above_realm
