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
#     David Moreau Simard, dmsimard@iweb.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr

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
This module provides an abstraction layer for communications between Alignak daemons
Used by the Arbiter
"""
import logging

from alignak.util import get_obj_name_two_args_and_void
from alignak.misc.serialization import unserialize, AlignakClassLookupException
from alignak.objects.item import Item, Items
from alignak.property import BoolProp, IntegerProp, StringProp, ListProp, DictProp, AddrProp
from alignak.http.client import HTTPClient, HTTPEXCEPTIONS

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class SatelliteLink(Item):
    """SatelliteLink is a common Class for links between
    Arbiter and other satellites. Used by the Dispatcher object.

    """

    properties = Item.properties.copy()
    properties.update({
        'address':
            StringProp(default='localhost', fill_brok=['full_status']),
        'timeout':
            IntegerProp(default=3, fill_brok=['full_status']),
        'data_timeout':
            IntegerProp(default=120, fill_brok=['full_status']),
        'check_interval':
            IntegerProp(default=60, fill_brok=['full_status']),
        'max_check_attempts':
            IntegerProp(default=3, fill_brok=['full_status']),
        'spare':
            BoolProp(default=False, fill_brok=['full_status']),
        'manage_sub_realms':
            BoolProp(default=False, fill_brok=['full_status']),
        'manage_arbiters':
            BoolProp(default=False, fill_brok=['full_status'], to_send=True),
        'modules':
            ListProp(default=[''], to_send=True, split_on_coma=True),
        'polling_interval':
            IntegerProp(default=1, fill_brok=['full_status'], to_send=True),
        'use_timezone':
            StringProp(default='NOTSET', to_send=True),
        'realm':
            StringProp(default='', fill_brok=['full_status'],
                       brok_transformation=get_obj_name_two_args_and_void),
        'realm_name':
            StringProp(default=''),
        'satellitemap':
            DictProp(default={}, elts_prop=AddrProp, to_send=True, override=True),
        'use_ssl':
            BoolProp(default=False, fill_brok=['full_status']),
        'hard_ssl_name_check':
            BoolProp(default=True, fill_brok=['full_status']),
        'passive':
            BoolProp(default=False, fill_brok=['full_status'], to_send=True),
    })

    running_properties = Item.running_properties.copy()
    running_properties.update({
        'con':
            StringProp(default=None),
        'alive':
            BoolProp(default=True, fill_brok=['full_status']),
        'broks':
            StringProp(default=[]),

        # the number of failed attempt
        'attempt':
            StringProp(default=0, fill_brok=['full_status']),

        # can be network ask or not (dead or check in timeout or error)
        'reachable':
            BoolProp(default=True, fill_brok=['full_status']),
        'last_check':
            IntegerProp(default=0, fill_brok=['full_status']),
        'managed_confs':
            StringProp(default={}),
        'is_sent':
            BoolProp(default=False),
    })

    def __init__(self, *args, **kwargs):
        super(SatelliteLink, self).__init__(*args, **kwargs)

        self.arb_satmap = {'address': '0.0.0.0', 'port': 0}
        if hasattr(self, 'address'):
            self.arb_satmap['address'] = self.address
        if hasattr(self, 'port'):
            try:
                self.arb_satmap['port'] = int(self.port)
            except ValueError:  # pragma: no cover, simple protection
                logger.error("Satellite port must be an integer: %s", self.port)

    def get_name(self):
        """Get the name of the link based on its type
        if *mytype*_name is an attribute then returns self.*mytype*_name.
        otherwise returns "Unnamed *mytype*"
        Example : self.poller_name or "Unnamed poller"

        :return: String corresponding to the link name
        :rtype: str
        """
        return getattr(self,
                       "{0}_name".format(self.get_my_type()),
                       "Unnamed {0}".format(self.get_my_type()))

    def set_arbiter_satellitemap(self, satellitemap):
        """
            arb_satmap is the satellitemap in current context:
                - A SatelliteLink is owned by an Arbiter
                - satellitemap attribute of SatelliteLink is the map
                  defined IN THE satellite configuration
                  but for creating connections, we need the have the satellitemap of the Arbiter

        :return: None
        """
        self.arb_satmap = {'address': self.address, 'port': self.port, 'use_ssl': self.use_ssl,
                           'hard_ssl_name_check': self.hard_ssl_name_check}
        self.arb_satmap.update(satellitemap)

    def create_connection(self):
        """Initialize HTTP connection with a satellite (con attribute) and
        set uri attribute

        :return: None
        """
        self.con = HTTPClient(address=self.arb_satmap['address'], port=self.arb_satmap['port'],
                              timeout=self.timeout, data_timeout=self.data_timeout,
                              use_ssl=self.use_ssl,
                              strong_ssl=self.hard_ssl_name_check
                              )
        self.uri = self.con.uri

    def put_conf(self, conf):
        """Send the conf (serialized) to the satellite
        HTTP request to the satellite (POST / put_conf)

        :param conf: The conf to send (data depend on the satellite)
        :type conf:
        :return: None
        """
        if self.con is None:
            self.create_connection()

        # Maybe the connection was not ok, bail out
        if not self.con:
            return False

        try:
            self.con.post('put_conf', {'conf': conf}, wait='long')
            return True
        except IOError as exp:  # pragma: no cover, simple protection
            self.con = None
            logger.error("IOError for %s: %s", self.get_name(), str(exp))
            return False
        except HTTPEXCEPTIONS as exp:
            self.con = None
            # logger.error("Failed sending configuration: %s", str(exp))
            return False

    def get_all_broks(self):
        """Get and clean all of our broks

        :return: list of all broks in the satellite
        :rtype: list
        """
        res = self.broks
        self.broks = []
        return res

    def set_alive(self):
        """Set alive, reachable, and reset attempts.
        If we change state, raise a status brok update

        :return: None
        """
        was_alive = self.alive
        self.alive = True
        self.attempt = 0
        self.reachable = True

        # We came from dead to alive
        # so we must add a brok update
        if not was_alive:
            brok = self.get_update_status_brok()
            self.broks.append(brok)

    def set_dead(self):
        """Set the satellite into dead state:

        * Alive -> False
        * con -> None

        Create an update Brok

        :return:None
        """
        was_alive = self.alive
        self.alive = False
        self.con = None

        # We are dead now. Must raise
        # a brok to say it
        if was_alive:
            logger.warning("Setting the satellite %s to a dead state.", self.get_name())
            brok = self.get_update_status_brok()
            self.broks.append(brok)

    def add_failed_check_attempt(self, reason=''):
        """Go in reachable=False and add a failed attempt
        if we reach the max, go dead

        :param reason: the reason of adding an attempts (stack trace sometimes)
        :type reason: str
        :return: None
        """
        self.reachable = False
        self.attempt += 1
        self.attempt = min(self.attempt, self.max_check_attempts)
        # Don't need to warn again and again if the satellite is already dead
        if self.alive:
            logger.warning("Add failed attempt to %s (%d/%d) %s",
                           self.get_name(), self.attempt, self.max_check_attempts, reason)

        # check when we just go HARD (dead)
        if self.attempt == self.max_check_attempts:
            self.set_dead()

    def update_infos(self, now):
        """Update satellite info each self.check_interval seconds
        so we smooth arbiter actions for just useful actions.
        Create update Brok

        :return: None
        """
        # First look if it's not too early to ping
        if (now - self.last_check) < self.check_interval:
            return

        self.last_check = now

        # We ping and update the managed list
        self.ping()
        if not self.alive or self.attempt > 0:
            return

        self.update_managed_list()

        # Update the state of this element
        brok = self.get_update_status_brok()
        self.broks.append(brok)

    def known_conf_managed_push(self, cfg_id, push_flavor):
        """The elements just got a new conf_id, we put it in our list
         because maybe the satellite is too busy to answer now

        :param cfg_id: config id
        :type cfg_id: int
        :param push_flavor: push_flavor we pushed earlier to the satellite
        :type push_flavor: int
        :return: None
        """
        self.managed_confs[cfg_id] = push_flavor

    def ping(self):
        """Send a HTTP request to the satellite (GET /ping)
        Add failed attempt if an error occurs
        Otherwise, set alive this satellite

        :return: None
        """
        logger.debug("Pinging %s", self.get_name())
        try:
            if self.con is None:
                self.create_connection()
            logger.debug(" (%s)", self.uri)

            # If the connection failed to initialize, bail out
            if self.con is None:
                self.add_failed_check_attempt()
                return

            res = self.con.get('ping')

            # Should return us pong string
            if res == 'pong':
                self.set_alive()
            else:
                self.add_failed_check_attempt()
        except HTTPEXCEPTIONS, exp:
            self.add_failed_check_attempt(reason=str(exp))

    def wait_new_conf(self):  # pragma: no cover, no more used
        """Send a HTTP request to the satellite (GET /wait_new_conf)

        TODO: is it still useful, wait_new_conf is implemented in the
        HTTP interface of each daemon

        :return: True if wait new conf, otherwise False
        :rtype: bool
        """
        if self.con is None:
            self.create_connection()
        try:
            logger.warning("Arbiter wants me to wait for a new configuration")
            self.con.get('wait_new_conf')
            return True
        except HTTPEXCEPTIONS:
            self.con = None
            return False

    def have_conf(self, magic_hash=None):
        """Send a HTTP request to the satellite (GET /have_conf)
        Used to know if the satellite has a conf

        :param magic_hash: Config hash. Only used for HA arbiter communication
        :type magic_hash: int
        :return: Boolean indicating if the satellite has a (specific) configuration
        :type: bool
        """
        if self.con is None:
            self.create_connection()

        # If the connection failed to initialize, bail out
        if self.con is None:
            return False

        try:
            if magic_hash is None:
                res = self.con.get('have_conf')
            else:
                res = self.con.get('have_conf', {'magic_hash': magic_hash})
            if not isinstance(res, bool):
                return False
            return res
        except HTTPEXCEPTIONS:
            self.con = None
            return False

    def remove_from_conf(self, sched_id):  # pragma: no cover, no more used
        """Send a HTTP request to the satellite (GET /remove_from_conf)
        Tell a satellite to remove a scheduler from conf

        TODO: is it still useful, remove_from_conf is implemented in the HTTP
        interface of each daemon

        :param sched_id: scheduler id to remove
        :type sched_id: int
        :return: True on success, False on failure, None if can't connect
        :rtype: bool | None
        TODO: Return False instead of None
        """
        if self.con is None:
            self.create_connection()

        # If the connection failed to initialize, bail out
        if self.con is None:
            return

        try:
            self.con.get('remove_from_conf', {'sched_id': sched_id})
            return True
        except HTTPEXCEPTIONS:
            self.con = None
            return False

    def update_managed_list(self):
        """Send a HTTP request to the satellite (GET /what_i_managed)
        and update managed_conf attribute with dict (cleaned)
        Set to {} on failure

        :return: None
        """
        if self.con is None:
            self.create_connection()

        # If the connection failed to initialize, bail out
        if self.con is None:
            self.managed_confs = {}
            return

        try:
            tab = self.con.get('what_i_managed')

            # Protect against bad return
            if not isinstance(tab, dict):
                self.con = None
                self.managed_confs = {}
                return

            # Ok protect against json that is changing keys as string instead of int
            tab_cleaned = {}
            for (key, val) in tab.iteritems():
                try:
                    tab_cleaned[key] = val
                except ValueError:  # pragma: no cover, simple protection
                    # TODO: make it a log?
                    print "[%s] What I managed: Got exception: bad what_i_managed returns" % \
                          self.get_name(), tab
            # We can update our list now
            self.managed_confs = tab_cleaned
        except HTTPEXCEPTIONS, exp:  # pragma: no cover, simple protection
            # TODO: make it a log?
            print "EXCEPTION IN what_i_managed", str(exp)
            # A timeout is not a crime, put this case aside
            # TODO : fix the timeout part?
            self.con = None
            print "[%s] What I managed: Got exception: %s %s %s" % \
                  (self.get_name(), exp, type(exp), exp.__dict__)
            self.managed_confs = {}

    def do_i_manage(self, cfg_id, push_flavor):
        """Tell if the satellite is managing cfg_id with push_flavor

        :param cfg_id: config id
        :type cfg_id: int
        :param push_flavor: flavor id, random it generated at parsing
        :type push_flavor: int
        :return: True if the satellite has push_flavor in managed_confs[cfg_id]
        :rtype: bool
        """
        # If not even the cfg_id in the managed_conf, bail out
        if cfg_id not in self.managed_confs:
            return False
        # maybe it's in but with a false push_flavor. check it :)
        return self.managed_confs[cfg_id] == push_flavor

    def push_broks(self, broks):
        """Send a HTTP request to the satellite (GET /ping)
        and THEN Send a HTTP request to the satellite (POST /push_broks)
        Send broks to the satellite
        The first ping ensure the satellite is there to avoid a big timeout

        :param broks: Brok list to send
        :type broks: list
        :return: True on success, False on failure
        :rtype: bool
        """
        if self.con is None:
            self.create_connection()

        # If the connection failed to initialize, bail out
        if self.con is None:
            return False

        try:
            self.con.post('push_broks', {'broks': broks}, wait='long')
            return True
        except HTTPEXCEPTIONS:
            self.con = None
            return False

    def get_external_commands(self):
        """Send a HTTP request to the satellite (GET /ping)
        and THEN send a HTTP request to the satellite (GET /get_external_commands)
        Get external commands from satellite.
        Un-serialize data received.

        :return: External Command list on success, [] on failure
        :rtype: list
        """
        if self.con is None:
            self.create_connection()

        # If the connection failed to initialize, bail out
        if self.con is None:
            return []

        try:
            tab = self.con.get('get_external_commands', wait='long')
            tab = unserialize(str(tab))
            # Protect against bad return
            if not isinstance(tab, list):
                self.con = None
                return []
            return tab
        except HTTPEXCEPTIONS:  # pragma: no cover, simple protection
            self.con = None
            return []
        except AttributeError:  # pragma: no cover, simple protection
            self.con = None
            return []
        except AlignakClassLookupException as exp:  # pragma: no cover, simple protection
            logger.error('Cannot un-serialize external commands received: %s', exp)

    def prepare_for_conf(self):
        """Init cfg dict attribute with __class__.properties
        and extra __class__ attribute
        (like __init__ could do with an object)

        :return: None
        """
        self.cfg = {'global': {}, 'schedulers': {}, 'arbiters': {}}
        properties = self.__class__.properties
        for prop, entry in properties.items():
            if entry.to_send:
                self.cfg['global'][prop] = getattr(self, prop)
        cls = self.__class__
        # Also add global values
        self.cfg['global']['statsd_host'] = cls.statsd_host
        self.cfg['global']['statsd_port'] = cls.statsd_port
        self.cfg['global']['statsd_prefix'] = cls.statsd_prefix
        self.cfg['global']['statsd_enabled'] = cls.statsd_enabled

    def add_global_conf_parameters(self, params):
        """Add some extra params in cfg dict attribute.
        Some attributes are in the global configuration

        :param params: dict to update cfg with
        :type params: dict
        :return: None
        """
        for prop in params:
            self.cfg['global'][prop] = params[prop]

    def get_my_type(self):
        """Get the satellite type. Accessor to __class__.mytype
        ie : poller, scheduler, receiver, broker, arbiter or reactionner

        :return: Satellite type
        :rtype: str
        """
        return self.__class__.my_type

    def give_satellite_cfg(self):
        """Get a configuration for this satellite.
        Not used by Scheduler and Arbiter (overridden)

        :return: Configuration for satellite
        :rtype: dict
        """
        return {'port': self.port,
                'address': self.address,
                'use_ssl': self.use_ssl,
                'hard_ssl_name_check': self.hard_ssl_name_check,
                'name': self.get_name(),
                'instance_id': self.uuid,
                'active': True,
                'passive': self.passive,
                'poller_tags': getattr(self, 'poller_tags', []),
                'reactionner_tags': getattr(self, 'reactionner_tags', [])
                }


class SatelliteLinks(Items):
    """Class to handle serveral SatelliteLink"""

    # name_property = "name"
    # inner_class = SchedulerLink

    def linkify(self, realms, modules):
        """Link realms and modules in all SatelliteLink
        (Link a real Realm / Module python object to the SatelliteLink attribute)

        :param realms: Realm object list
        :type realms: list
        :param modules: Module object list
        :type modules: list
        :return: None
        """
        self.linkify_s_by_p(realms)
        self.linkify_s_by_plug(modules)

    def linkify_s_by_p(self, realms):
        """Link realms in all SatelliteLink

        :param realms: Realm object list
        :type realms: list
        :return: None
        """
        for satlink in self:
            r_name = satlink.realm.strip()
            # If no realm name, take the default one
            if r_name == '':
                realm = realms.get_default()
            else:  # find the realm one
                realm = realms.find_by_name(r_name)
            # Check if what we get is OK or not
            if realm is not None:
                satlink.realm = realm.uuid
                satlink.realm_name = realm.get_name()
                getattr(realm, '%ss' % satlink.my_type).append(satlink.uuid)
                # case SatelliteLink has manage_sub_realms
                if getattr(satlink, 'manage_sub_realms', False):
                    for r_uuid in realm.all_sub_members:
                        getattr(realms[r_uuid], '%ss' % satlink.my_type).append(satlink.uuid)
            else:
                err = "The %s %s got a unknown realm '%s'" % \
                      (satlink.__class__.my_type, satlink.get_name(), r_name)
                satlink.configuration_errors.append(err)
