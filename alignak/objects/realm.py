# -*- coding: utf-8 -*-

#
# Copyright (C) 2015-2017: Alignak team, see AUTHORS.txt file for contributors
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
from alignak.property import BoolProp, StringProp, DictProp, ListProp, IntegerProp

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
        'realm_name':
            StringProp(default='', fill_brok=['full_status']),
        'name':
            StringProp(default='', fill_brok=['full_status']),
        'alias':
            StringProp(default=''),
        # No status_broker_name because it put hosts, not host_name
        'realm_members':
            ListProp(default=[], split_on_coma=True),
        'higher_realms':
            ListProp(default=[], split_on_coma=True),
        'default':
            BoolProp(default=False),
        'passively_checked_hosts':
            BoolProp(default=None),
        'actively_checked_hosts':
            BoolProp(default=None),
    })

    running_properties = Item.running_properties.copy()
    running_properties.update({
        # Those lists contain only the uuid of the satellite link, not the whole object!
        'arbiters':
            ListProp(default=[]),
        'schedulers':
            ListProp(default=[]),
        'brokers':
            ListProp(default=[]),
        'pollers':
            ListProp(default=[]),
        'reactionners':
            ListProp(default=[]),
        'receivers':
            ListProp(default=[]),
        'potential_brokers':
            ListProp(default=[]),
        'potential_pollers':
            ListProp(default=[]),
        'potential_reactionners':
            ListProp(default=[]),
        'potential_receivers':
            ListProp(default=[]),
        # Once configuration is prepared, the count of the hosts in the realm
        'hosts_count':
            IntegerProp(default=0),
        'packs':
            DictProp(default={}),
        'parts':
            DictProp(default={}),
        'unknown_higher_realms':
            ListProp(default=[]),
        'all_sub_members':
            ListProp(default=[]),
    })

    macros = {
        'REALMNAME': 'realm_name',
        'REALMMEMBERS': 'members',
    }

    def __init__(self, params=None, parsing=True):
        super(Realm, self).__init__(params, parsing)

        self.fill_default()

        # Define a packs list for the configuration preparation
        self.packs = []
        # Once the configuration got prepared, packs becomes a dictionary!
        # packs is a dictionary indexed with the configuration part
        # number and containing the list of hosts

        # List of satellites related to the realm
        self.to_satellites = {
            'reactionner': {},
            'poller': {},
            'broker': {},
            'receiver': {}
        }

        # List of satellites that need a configuration dispatch
        self.to_satellites_need_dispatch = {
            'reactionner': {},
            'poller': {},
            'broker': {},
            'receiver': {}
        }

        # List of satellites with their managed configuration
        self.to_satellites_managed_by = {
            'reactionner': {},
            'poller': {},
            'broker': {},
            'receiver': {}
        }

        # Attributes depending of the satellite type
        for sat_type in ['arbiter', 'scheduler', 'reactionner', 'poller', 'broker', 'receiver']:
            setattr(self, "nb_%ss" % sat_type, 0)
            setattr(self, 'potential_%ss' % sat_type, [])

    def __repr__(self):
        res = '<%r %r' % (self.__class__.__name__, self.get_name())
        if not self.members:
            res = res + ', no members'
        else:
            res = res + ', %d members: %r' \
                        % (len(self.members), ', '.join([str(s) for s in self.members]))
        if not self.hosts_count:
            res = res + ', no hosts'
        else:
            res = res + ', %d hosts' % self.hosts_count
        if not getattr(self, 'parts', None):
            res = res + ', no parts'
        else:
            res = res + ', %d parts' % len(self.parts)
        if not getattr(self, 'packs', None):
            res = res + ', no packs'
        else:
            res = res + ', %d packs' % len(self.packs)
        return res + '/>'
    __str__ = __repr__

    @property
    def name(self):
        """Get the realm name"""
        return self.get_name()

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
        print("Realm, add sub member: %s" % member)
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

    def prepare_for_satellites_conf(self, satellites):
        """Update the following attributes of a realm::

        * to_satellites (with *satellite type* keys)
        * to_satellites_need_dispatch (with *satellite type* keys)
        * to_satellites_managed_by (with *satellite type* keys)
        * nb_*satellite type*s
        * self.potential_*satellite type*s

        (satellite type are reactionner, poller, broker and receiver)

        :param satellites: list of SatelliteLink objects
        :type satellites: SatelliteLink list
        :return: None
        """
        # Generic loop to fill nb_* (counting) and fill potential_* attribute.
        # Counting is not that difficult but as it's generic, getattr and setattr are required
        for sat_type in ["reactionner", "poller", "broker", "receiver"]:
            # We get potential TYPE at realm level first
            for sat_link_uuid in getattr(self, "%ss" % sat_type):
                for sat_link in satellites:
                    if sat_link_uuid != sat_link.uuid:
                        continue
                    # Found our declared satellite in the provided satellites
                    if not sat_link.spare:
                        # Generic increment : realm.nb_TYPE += 1
                        setattr(self, "nb_%ss" % sat_type, getattr(self, "nb_%ss" % sat_type) + 1)
                    # Append elem to realm.potential_TYPE
                    getattr(self, 'potential_%ss' % sat_type).append(sat_link.uuid)
                    break
                else:
                    logger.error("Satellite %s declared in the realm %s not found "
                                 "in the configuration satellites!", sat_link_uuid, self.name)

        logger.info(" Realm %s: (in/potential) (schedulers:%d) (pollers:%d/%d) "
                    "(reactionners:%d/%d) (brokers:%d/%d) (receivers:%d/%d)", self.name,
                    len(self.schedulers),
                    self.nb_pollers, len(self.potential_pollers),
                    self.nb_reactionners, len(self.potential_reactionners),
                    self.nb_brokers, len(self.potential_brokers),
                    self.nb_receivers, len(self.potential_receivers))

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
            self.add_error("Error: there is a loop in the realm definition %s" % self.get_name())
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

        logger.debug("[realm %s] do not have this kind of satellites: %s", self.name, s_type)
        return []

    def get_potential_satellites_by_type(self, satellites, s_type, reachable=True):
        """Generic function to access one of the potential satellite attribute
        ie : self.potential_pollers, self.potential_reactionners ...

        :param satellites: list of SatelliteLink objects
        :type satellites: SatelliteLink list
        :param s_type: satellite type wanted
        :type s_type: str
        :param reachable: only the reachable satellites
        :type reachable: bool
        :return: self.potential_*type*s
        :rtype: list
        """
        if not hasattr(self, 'potential_' + s_type + 's'):
            logger.debug("[realm %s] do not have this kind of satellites: %s", self.name, s_type)
            return []

        matching_satellites = []
        for sat_link_uuid in getattr(self, 'potential_' + s_type + 's'):
            for sat_link in satellites:
                if sat_link_uuid != sat_link.uuid:
                    continue

                if not reachable or (reachable and sat_link.reachable):
                    matching_satellites.append(sat_link)
                break

        logger.debug("- potential %ss: %s", s_type, matching_satellites)
        return matching_satellites

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

        logger.debug("[realm %s] do not have this kind of satellites: %s", self.name, s_type)
        return 0

    def get_links_for_a_broker(self, pollers, reactionners, receivers, realms,
                               manage_sub_realms=False):
        """Get a configuration dictionary with pollers, reactionners and receivers links
        for a broker

        :param pollers: pollers
        :type pollers:
        :param reactionners: reactionners
        :type reactionners:
        :param receivers: receivers
        :type receivers:
        :param realms: realms
        :type realms:
        :param manage_sub_realms:
        :type manage_sub_realms: True if the borker manages sub realms

        :return: dict containing pollers, reactionners and receivers links (key is satellite id)
        :rtype: dict
        """

        # Create void satellite links
        cfg = {
            'pollers': {},
            'reactionners': {},
            'receivers': {},
        }

        # Our self.daemons are only identifiers... that we use to fill the satellite links
        for poller_id in self.pollers:
            poller = pollers[poller_id]
            cfg['pollers'][poller.uuid] = poller.give_satellite_cfg()

        for reactionner_id in self.reactionners:
            reactionner = reactionners[reactionner_id]
            cfg['reactionners'][reactionner.uuid] = reactionner.give_satellite_cfg()

        for receiver_id in self.receivers:
            receiver = receivers[receiver_id]
            cfg['receivers'][receiver.uuid] = receiver.give_satellite_cfg()

        # If the broker manages sub realms, fill the satellite links...
        if manage_sub_realms:
            # Now pollers
            for poller_id in self.get_all_subs_satellites_by_type('pollers', realms):
                poller = pollers[poller_id]
                cfg['pollers'][poller.uuid] = poller.give_satellite_cfg()

            # Now reactionners
            for reactionner_id in self.get_all_subs_satellites_by_type('reactionners', realms):
                reactionner = reactionners[reactionner_id]
                cfg['reactionners'][reactionner.uuid] = reactionner.give_satellite_cfg()

            # Now receivers
            for receiver_id in self.get_all_subs_satellites_by_type('receivers', realms):
                receiver = receivers[receiver_id]
                cfg['receivers'][receiver.uuid] = receiver.give_satellite_cfg()

        return cfg

    def get_links_for_a_scheduler(self, pollers, reactionners, brokers):
        """Get a configuration dictionary with pollers, reactionners and brokers links
        for a scheduler

        :return: dict containing pollers, reactionners and brokers links (key is satellite id)
        :rtype: dict
        """

        # Create void satellite links
        cfg = {
            'pollers': {},
            'reactionners': {},
            'brokers': {},
        }

        # Our self.daemons are only identifiers... that we use to fill the satellite links
        try:
            for poller_id in self.pollers:
                poller = pollers[poller_id]
                cfg['pollers'][poller.uuid] = poller.give_satellite_cfg()

            for reactionner_id in self.reactionners:
                reactionner = reactionners[reactionner_id]
                cfg['reactionners'][reactionner.uuid] = reactionner.give_satellite_cfg()

            for broker_id in self.brokers:
                broker = brokers[broker_id]
                cfg['brokers'][broker.uuid] = broker.give_satellite_cfg()
        except Exception as exp:  # pylint: disable=broad-except
            logger.exception("realm.get_links_for_a_scheduler: %s", exp)

        return cfg


class Realms(Itemgroups):
    """Realms manage a list of Realm objects, used for parsing configuration

    """
    name_property = "realm_name"  # is used for finding realms
    inner_class = Realm

    def linkify(self):
        """Links sub-realms (parent / son),
        add new realm_members,

        :return: None
        """
        self.linkify_p_by_p()

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
                self.add_error(msg)

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
                self.add_warning(msg)

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
        logger.info("Realms satellites:")
        for realm in self:
            realm.prepare_for_satellites_conf(satellites)
