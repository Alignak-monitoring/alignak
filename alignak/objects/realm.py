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

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

# It change from hostgroup Class because there is no members
# properties, just the realm_members that we rewrite on it.


class Realm(Itemgroup):
    """Realm class is used to implement realm.
    It is basically a group of Hosts assigned to a specific Scheduler/Poller
    (other daemon are optional)

    """
    my_type = 'realm'

    properties = Itemgroup.properties.copy()
    properties.update({
        'realm_name':
            StringProp(default=u'', fill_brok=['full_status']),
        'name':
            StringProp(default=u'', fill_brok=['full_status']),
        'alias':
            StringProp(fill_brok=['full_status']),
        'realm_members':
            ListProp(default=[], split_on_comma=True),
        'higher_realms':
            ListProp(default=[], split_on_comma=True),
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
        # Realm level in the realms hierarchy
        'level':
            IntegerProp(default=-1),
        # All the sub realms (children and grand-children)
        'all_sub_members':
            ListProp(default=[]),
        'all_sub_members_names':
            ListProp(default=[]),
    })

    macros = {
        'REALMNAME': 'realm_name',
        'REALMMEMBERS': 'realm_members',
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

    def __repr__(self):  # pragma: no cover
        res = '<%r %r (%d)' % (self.__class__.__name__, self.get_name(), self.level)
        if not self.realm_members:
            res = res + ', no sub-realms'
        else:
            res = res + ', %d sub-realms: %r' \
                        % (len(self.realm_members), ', '.join([str(s) for s in self.realm_members]))
            if not self.all_sub_members_names:
                res = res + ', no sub-sub-realms'
            else:
                res = res + ', %d sub-sub-realms: %r' \
                            % (len(self.all_sub_members_names),
                               ', '.join([str(s) for s in self.all_sub_members_names]))
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
        return getattr(self, 'realm_name', 'unset')

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

    def get_realms_by_explosion(self, realms):
        """Get all members of this realm including members of sub-realms on multi-levels

        :param realms: realms list, used to look for a specific one
        :type realms: alignak.objects.realm.Realms
        :return: list of members and add realm to realm_members attribute
        :rtype: list
        """
        # If rec_tag is already set, then we detected a loop in the realms hierarchy!
        if getattr(self, 'rec_tag', False):
            self.add_error("Error: there is a loop in the realm definition %s" % self.get_name())
            return None

        # Ok, not in a loop, we tag the realm and parse its members
        self.rec_tag = True

        # Order realm members list by name
        self.realm_members = sorted(self.realm_members)
        for member in self.realm_members:
            realm = realms.find_by_name(member)
            if not realm:
                self.add_string_unknown_member(member)
                continue

            children = realm.get_realms_by_explosion(realms)
            if children is None:
                # We got a loop in our children definition
                self.all_sub_members = []
                self.realm_members = []
                return None

        # Return the list of all unique members
        return self.all_sub_members

    def set_level(self, level, realms):
        """Set the realm level in the realms hierarchy

        :return: None
        """
        # print("- set: %s (%s)" % (self.get_name(), self.uuid))
        self.level = level
        self.all_sub_members = []
        self.all_sub_members_names = []
        for child in sorted(self.realm_members):
            child = realms.find_by_name(child)
            if child:
                self.all_sub_members.append(child.uuid)
                self.all_sub_members_names.append(child.get_name())
                grand_children = child.set_level(self.level + 1, realms)
                for grand_child in grand_children:
                    if grand_child in self.all_sub_members_names:
                        # print("Already %s" % grand_child)
                        continue
                    self.all_sub_members_names.append(grand_child)
                    grand_child = realms.find_by_name(grand_child)
                    if grand_child:
                        self.all_sub_members.append(grand_child.uuid)
        # print("-> : %s" % self.all_sub_members)
        # print("-> : %s" % self.all_sub_members_names)
        return self.all_sub_members_names

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

    def __repr__(self):  # pragma: no cover
        res = []
        for realm in self:
            res.append('%s %s' % ('+' * realm.level, realm.get_name()))
        return '\n'.join(res)
    __str__ = __repr__

    def linkify(self):
        """Links sub-realms (parent / son)
        Realms are linked to all their sub realms whatever the level

        Set the realm level according to the realm position in the hierarchy

        :return: None
        """
        for realm in self:
            realm.all_sub_members_names = realm.all_sub_members

            # The new member list (uuid list)
            new_members = []
            for member in realm.all_sub_members:
                # if member in self:
                #     # We have a uuid here not a name
                #     new_members.append(member)
                #     continue
                new_member = self.find_by_name(member)
                if new_member is not None:
                    new_members.append(new_member.uuid)
                # else:
                #     realm.add_string_unknown_member(member)
            # List of all unique members
            realm.all_sub_members = new_members
            # realm.all_sub_members = list(set(new_members))
            # realm.all_sub_members_uuid = new_members

        # Set realm level, from the highest level realms...
        for realm in self:
            for tmp_realm in self:
                # Ignore if it is me...
                if tmp_realm == realm:
                    continue
                # Ignore if I am a sub realm of another realm
                if realm.get_name() in tmp_realm.realm_members:
                    break
            else:
                # This realm is not in the children of any realm
                realm.level = 0
                realm.set_level(0, self)

    def explode(self):
        """Explode realms with each realm_members and higher_realms to get all the
        realms sub realms.

        :return: None
        """
        # Manage higher realms where defined
        for realm in [tmp_realm for tmp_realm in self if tmp_realm.higher_realms]:
            for parent in realm.higher_realms:
                higher_realm = self.find_by_name(parent)
                if higher_realm:
                    # Add the realm to its parent realm members
                    higher_realm.realm_members.append(realm.get_name())

        for realm in self:
            # Set a recursion tag to protect against loop
            for tmp_realm in self:
                tmp_realm.rec_tag = False
            realm.get_realms_by_explosion(self)

        # Clean the recursion tag
        for tmp_realm in self:
            del tmp_realm.rec_tag

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
                self.add_error("No realm is defined as the default one! "
                               "I set %s as the default realm" % (default_realm_name))

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
                self.add_warning("More than one realm is defined as the default one: %s. "
                                 "I set %s as the default realm."
                                 % (','.join(found_names), default_realm_name))

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
