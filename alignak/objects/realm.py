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
            StringProp(default=''),
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
        'unknown_higher_realms': ListProp(default=[]),
        'all_sub_members': ListProp(default=[]),
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

    def add_string_member(self, member):
        """Add a realm to all_sub_members attribute

        :param member: realm names to add
        :type member: list
        :return: None
        """
        self.all_sub_members.extend(member)

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

        return []

    def fill_realm_members_with_higher_realms(self, realms):
        """
        if we have higher_realms defined, fill realm_members of the realm with my realm_name

        :param realms: list of all realms objects
        :type realms: list
        :return: None
        """
        higher_realms = getattr(self, 'higher_realms', [])
        for realm_nane in higher_realms:
            realm = realms.find_by_name(realm_nane.strip())
            if realm is not None:
                if not hasattr(realm, 'realm_members'):
                    realm.realm_members = []
                realm.realm_members.append(self.realm_name)

    def get_realms_by_explosion(self, realms):
        """Get all members of this realm including members of sub-realms on multi-levels

        :param realms: realms list, used to look for a specific one
        :type realms: alignak.objects.realm.Realms
        :return: list of members and add realm to realm_members attribute
        :rtype: list
        """
        # The recursive part
        # rec_tag is set to False every HG we explode
        # so if True here, it must be a loop in HG
        # calls... not GOOD!
        if self.rec_tag:
            err = "Error: we've got a loop in realm definition %s" % self.get_name()
            self.configuration_errors.append(err)
            return None

        # Ok, not a loop, we tag it and continue
        self.rec_tag = True

        # we have yet exploded this realm
        if self.all_sub_members != []:
            return self.all_sub_members

        p_mbrs = self.get_realm_members()
        for p_mbr in p_mbrs:
            realm = realms.find_by_name(p_mbr.strip())
            if realm is not None:
                value = realm.get_realms_by_explosion(realms)
                if value is None:
                    # case loop problem
                    self.all_sub_members = []
                    self.realm_members = []
                    return None
                elif value:
                    self.add_string_member(value)
                self.add_string_member([realm.realm_name])
            else:
                self.add_string_unknown_member(p_mbr.strip())
        return self.all_sub_members

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
        for member in self.all_sub_members:
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
        Realm are links with all_sub_members
        It's filled with realm_members and higher_realms defined in configuration file

        It convert name with uuid of realm members

        :return: None
        """
        for realm in self.items.values():
            mbrs = realm.all_sub_members
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
                else:
                    realm.add_string_unknown_member(mbr)
            realm.all_sub_members = new_mbrs

    def explode(self):
        """Explode realms with each realm_members to fill all_sub_members property

        :return: None
        """
        for realm in self:
            realm.fill_realm_members_with_higher_realms(self)

        for realm in self:
            if hasattr(realm, 'realm_members') and realm.realm_members != []:
                # get_realms_by_explosion is a recursive
                # function, so we must tag hg so we do not loop
                for tmp_p in self:
                    tmp_p.rec_tag = False
                realm.get_realms_by_explosion(self)

        # We clean the tags
        for tmp_p in self.items.values():
            if hasattr(tmp_p, 'rec_tag'):
                del tmp_p.rec_tag

    def get_default(self, check=False):
        """Get the default realm

        :param check: check correctness if True
        :type check: bool
        :return: Default realm of Alignak configuration
        :rtype: alignak.objects.realm.Realm | None
        """
        found = []
        for realm in self:
            if getattr(realm, 'default', False):
                found.append(realm)

        if not found:
            # Retain as default realm the first realm in name alphabetical order
            found_names = sorted([r.get_name() for r in self])
            default_realm_name = found_names[0]
            default_realm = self.find_tpl_by_name(default_realm_name)
            default_realm.default = True
            found.append(default_realm)

            if check:
                msg = "No realm is defined as the default one! I set %s as the default realm" \
                      % (default_realm_name)
                self.configuration_errors.append(msg)

        default_realm = found[0]
        if len(found) > 1:
            # Retain as default realm the first so-called default realms in name alphabetical order
            found_names = sorted([r.get_name() for r in found])
            default_realm_name = found_names[0]
            default_realm = self.find_tpl_by_name(default_realm_name)

            # Set all found realms as non-default realms
            for realm in found:
                if realm.get_name() != default_realm_name:
                    realm.default = False

            if check:
                msg = "More than one realm is defined as the default one: %s. " \
                      "I set %s as the temporary default realm." \
                  % (','.join(found_names), default_realm_name)
                self.configuration_errors.append(msg)

        return default_realm

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

            # Generic loop to fill nb_* (counting) and fill potential_* attribute.
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
