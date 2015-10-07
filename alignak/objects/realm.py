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

from alignak.objects.item import Item
from alignak.objects.itemgroup import Itemgroup, Itemgroups
from alignak.property import BoolProp, IntegerProp, StringProp, DictProp, ListProp
from alignak.log import logger

# It change from hostgroup Class because there is no members
# properties, just the realm_members that we rewrite on it.


class Realm(Itemgroup):
    """Realm class is used to implement realm. It is basically a set of Host or Service
    assigned to a specific set of Scheduler/Poller (other daemon are optional)

    """
    _id = 1  # zero is always a little bit special... like in database
    my_type = 'realm'

    properties = Itemgroup.properties.copy()
    properties.update({
        '_id':            IntegerProp(default=0, fill_brok=['full_status']),
        'realm_name':    StringProp(fill_brok=['full_status']),
        # No status_broker_name because it put hosts, not host_name
        'realm_members': ListProp(default=[], split_on_coma=True),
        'higher_realms': ListProp(default=[], split_on_coma=True),
        'default':       BoolProp(default=False),
        'broker_complete_links':       BoolProp(default=False),
        # 'alias': {'required':  True, 'fill_brok': ['full_status']},
        # 'notes': {'required': False, 'default':'', 'fill_brok': ['full_status']},
        # 'notes_url': {'required': False, 'default':'', 'fill_brok': ['full_status']},
        # 'action_url': {'required': False, 'default':'', 'fill_brok': ['full_status']},
    })

    running_properties = Item.running_properties.copy()
    running_properties.update({
        'serialized_confs': DictProp(default={}),
    })

    macros = {
        'REALMNAME': 'realm_name',
        'REALMMEMBERS': 'members',
    }

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

    def get_all_subs_satellites_by_type(self, sat_type):
        """Get all satellites of the wated type in this realm recursively

        :param sat_type: satelitte type wanted (scheduler, poller ..)
        :type sat_type:
        :return: list of satellite in this realm
        :rtype: list
        TODO: Make this generic
        """
        res = copy.copy(getattr(self, sat_type))
        for member in self.realm_members:
            tmps = member.get_all_subs_satellites_by_type(sat_type)
            for mem in tmps:
                res.append(mem)
        return res

    def count_reactionners(self):
        """ Set the number of reactionners in this realm.

        :return: None
        TODO: Make this generic
        """
        self.nb_reactionners = 0
        for reactionner in self.reactionners:
            if not reactionner.spare:
                self.nb_reactionners += 1
        for realm in self.higher_realms:
            for reactionner in realm.reactionners:
                if not reactionner.spare and reactionner.manage_sub_realms:
                    self.nb_reactionners += 1

    def count_pollers(self):
        """ Set the number of pollers in this realm.

        :return: None
        """
        self.nb_pollers = 0
        for poller in self.pollers:
            if not poller.spare:
                self.nb_pollers += 1
        for realm in self.higher_realms:
            for poller in realm.pollers:
                if not poller.spare and poller.manage_sub_realms:
                    self.nb_pollers += 1

    def count_brokers(self):
        """ Set the number of brokers in this realm.

        :return: None
        TODO: Make this generic
        """
        self.nb_brokers = 0
        for broker in self.brokers:
            if not broker.spare:
                self.nb_brokers += 1
        for realm in self.higher_realms:
            for broker in realm.brokers:
                if not broker.spare and broker.manage_sub_realms:
                    self.nb_brokers += 1

    def count_receivers(self):
        """ Set the number of receivers in this realm.

        :return: None
        TODO: Make this generic
        """
        self.nb_receivers = 0
        for receiver in self.receivers:
            if not receiver.spare:
                self.nb_receivers += 1
        for realm in self.higher_realms:
            for receiver in realm.receivers:
                if not receiver.spare and receiver.manage_sub_realms:
                    self.nb_receivers += 1

    def get_satellties_by_type(self, s_type):
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

    def fill_potential_satellites_by_type(self, sat_type):
        """Edit potential_*sat_type* attribute to get potential satellite from upper level realms

        :param sat_type: satellite type wanted
        :type sat_type: str
        :return: None
        """
        setattr(self, 'potential_%s' % sat_type, [])
        for satellite in getattr(self, sat_type):
            getattr(self, 'potential_%s' % sat_type).append(satellite)
        for realm in self.higher_realms:
            for satellite in getattr(realm, sat_type):
                if satellite.manage_sub_realms:
                    getattr(self, 'potential_%s' % sat_type).append(satellite)

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

    # Fill dict of realms for managing the satellites confs
    def prepare_for_satellites_conf(self):
        """Init the following attributes::

        * to_satellites (with *satellite type* keys)
        * to_satellites_need_dispatch (with *satellite type* keys)
        * to_satellites_managed_by (with *satellite type* keys)
        * nb_*satellite type*s
        * self.potential_*satellite type*s

        (satellite type are reactionner, poller, broker and receiver)

        :return: None
        """
        self.to_satellites = {
            'reactionner': {},
            'poller': {},
            'broker': {},
            'receiver': {}
        }

        self.to_satellites_need_dispatch = {
            'reactionner': {},
            'poller': {},
            'broker': {},
            'receiver': {}
        }

        self.to_satellites_managed_by = {
            'reactionner': {},
            'poller': {},
            'broker': {},
            'receiver': {}
        }

        self.count_reactionners()
        self.fill_potential_satellites_by_type('reactionners')
        self.count_pollers()
        self.fill_potential_satellites_by_type('pollers')
        self.count_brokers()
        self.fill_potential_satellites_by_type('brokers')
        self.count_receivers()
        self.fill_potential_satellites_by_type('receivers')

        line = "%s: (in/potential) (schedulers:%d) (pollers:%d/%d)" \
               " (reactionners:%d/%d) (brokers:%d/%d) (receivers:%d/%d)" % \
            (self.get_name(),
             len(self.schedulers),
             self.nb_pollers, len(self.potential_pollers),
             self.nb_reactionners, len(self.potential_reactionners),
             self.nb_brokers, len(self.potential_brokers),
             self.nb_receivers, len(self.potential_receivers)
             )
        logger.info(line)

    def fill_broker_with_poller_reactionner_links(self, broker):
        """Fill brokerlink object with satellite data

        :param broker: broker link we want to fill
        :type broker: alignak.objects.brokerlink.Brokerlink
        :return: None
        """

        # TODO: find a better name...
        # TODO: and if he goes active?
        # First we create/void theses links
        broker.cfg['pollers'] = {}
        broker.cfg['reactionners'] = {}
        broker.cfg['receivers'] = {}

        # First our own level
        for poller in self.pollers:
            cfg = poller.give_satellite_cfg()
            broker.cfg['pollers'][poller._id] = cfg

        for reactionner in self.reactionners:
            cfg = reactionner.give_satellite_cfg()
            broker.cfg['reactionners'][reactionner._id] = cfg

        for receiver in self.receivers:
            cfg = receiver.give_satellite_cfg()
            broker.cfg['receivers'][receiver._id] = cfg

        # Then sub if we must to it
        if broker.manage_sub_realms:
            # Now pollers
            for poller in self.get_all_subs_satellites_by_type('pollers'):
                cfg = poller.give_satellite_cfg()
                broker.cfg['pollers'][poller._id] = cfg

            # Now reactionners
            for reactionner in self.get_all_subs_satellites_by_type('reactionners'):
                cfg = reactionner.give_satellite_cfg()
                broker.cfg['reactionners'][reactionner._id] = cfg

            # Now receivers
            for receiver in self.get_all_subs_satellites_by_type('receivers'):
                cfg = receiver.give_satellite_cfg()
                broker.cfg['receivers'][receiver._id] = cfg

    def get_satellites_links_for_scheduler(self):
        """Get a configuration dict with pollers and reactionners data

        :return: dict containing pollers and reactionners config (key is satellite id)
        :rtype: dict
        """

        # First we create/void theses links
        cfg = {
            'pollers': {},
            'reactionners': {}
        }

        # First our own level
        for poller in self.pollers:
            config = poller.give_satellite_cfg()
            cfg['pollers'][poller._id] = config

        for reactionner in self.reactionners:
            config = reactionner.give_satellite_cfg()
            cfg['reactionners'][reactionner._id] = config

        # print "***** Preparing a satellites conf for a scheduler", cfg
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
        and add new realm_members

        :return: None
        """
        for realm in self.items.values():
            mbrs = realm.get_realm_members()
            # The new member list, in id
            new_mbrs = []
            for mbr in mbrs:
                new_mbr = self.find_by_name(mbr)
                if new_mbr is not None:
                    new_mbrs.append(new_mbr)
                else:
                    realm.add_string_unknown_member(mbr)
            # We find the id, we replace the names
            realm.realm_members = new_mbrs

        # Now put higher realm in sub realms
        # So after they can
        for realm in self.items.values():
            realm.higher_realms = []

        for realm in self.items.values():
            self.recur_higer_realms(realm, realm.realm_members)

    def recur_higer_realms(self, parent_r, sons):
        """Add sub-realms (parent / son)

        :param parent_r: parent realm
        :type parent_r: alignak.objects.realm.Realm
        :param sons: sons realm
        :type sons: list[alignak.objects.realm.Realm]
        :return: None
        """
        for sub_p in sons:
            sub_p.higher_realms.append(parent_r)
            # and call for our sons too
            self.recur_higer_realms(parent_r, sub_p.realm_members)

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

    def prepare_for_satellites_conf(self):
        """Wrapper to loop over each reach and call Realm.prepare_for_satellites_conf()

        :return: None
        """
        for realm in self:
            realm.prepare_for_satellites_conf()
