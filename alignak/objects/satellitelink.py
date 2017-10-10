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
import time
import logging

from alignak.util import get_obj_name_two_args_and_void
from alignak.misc.serialization import unserialize, get_alignak_class, AlignakClassLookupException
from alignak.objects.item import Item, Items
from alignak.daemon import Daemon
from alignak.property import BoolProp, IntegerProp, FloatProp
from alignak.property import StringProp, ListProp, DictProp, AddrProp
from alignak.http.client import HTTPClient, HTTPClientException
from alignak.http.client import HTTPClientConnectionException, HTTPClientTimeoutException

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class SatelliteLink(Item):
    """SatelliteLink is a common Class for links between
    Arbiter and other satellites. Used by the Dispatcher object.

    """
    # Next value used for auto generated id
    _next_id = 1

    # All the class properties that are 'to_send' are stored in the 'global'
    # configuration to be pushed to the satellite when the configuration is dispatched
    properties = Item.properties.copy()
    # A SatelliteLink is an Item but it inherits from the properties of its related daemon
    properties.update(Daemon.properties.copy())
    properties.update({
        'instance_id':
            StringProp(),
        # A satellite link has the type/name of the daemon it is related to
        'name':
            StringProp(default='', fill_brok=['full_status']),
        # Address used by the other daemons
        'address':
            StringProp(default='localhost', fill_brok=['full_status']),
        'active':
            BoolProp(default=True, fill_brok=['full_status']),
        'timeout':
            IntegerProp(default=3, fill_brok=['full_status']),
        'data_timeout':
            IntegerProp(default=120, fill_brok=['full_status']),
        'check_interval':
            IntegerProp(default=60, fill_brok=['full_status']),
        'max_check_attempts':
            IntegerProp(default=3, fill_brok=['full_status']),
        # the number of failed attempt for the connection
        'max_failed_connections':
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
        'uri':
            StringProp(default=None),
        'reachable':    # Can be reached
            BoolProp(default=False, fill_brok=['full_status']),
        'alive':        # Is alive (ping response...)
            BoolProp(default=False, fill_brok=['full_status']),

        'running_id':   # The running identifier of my related daemon
            FloatProp(default=0, fill_brok=['full_status']),

        # the number of poll attempt from the arbiter dispatcher
        'attempt':
            IntegerProp(default=0, fill_brok=['full_status']),

        # the last connection attempt timestamp
        'last_connection':
            IntegerProp(default=0, fill_brok=['full_status']),
        # the number of failed attempt for the connection
        'connection_attempt':
            IntegerProp(default=0, fill_brok=['full_status']),

        'last_check':
            IntegerProp(default=0, fill_brok=['full_status']),
        'managed_confs':
            DictProp(default={}),
        'is_sent':
            BoolProp(default=False),
    })

    def __init__(self, params=None, parsing=True):
        super(SatelliteLink, self).__init__(params, parsing)

        # My interface context
        self.broks=[]
        self.external_commands={}
        self.actions={}
        self.wait_homerun={}

        if not parsing:
            print("No parsing: %s" % params)
            return

        # Create a new satellite link identifier
        self.instance_id = '%s_%d' % (self.__class__.__name__, self.__class__._next_id)
        self.__class__._next_id += 1

        self.fill_default()

        # Hack for ascending compatibility with Shinken configuration
        try:
            # We received a configuration with a 'name' property...
            if self.name:
                setattr(self, "%s_name" % self.type, self.name)
            else:
                # We received a configuration without a 'name' property... old form!
                setattr(self, 'name', getattr(self, "%s_name" % self.type))
        except KeyError as exp:
            print("We got an unnamed %s: %s" % (self.my_type, self.__dict__))
            setattr(self, 'name', getattr(self, "%s_name" % self.type))

        self.arb_satmap = {
            'address': getattr(self, 'address', None),
            'port': getattr(self, 'port', None)
        }

        self.cfg = {
            'self_conf': {},
            'schedulers': {},
            'arbiters': {}
        }

        # Create the link connection
        if not self.con:
            self.create_connection()

    def __repr__(self):
        return '<%s - %s/%s, address: %s//%s:%s, spare: %s />' \
               % (self.instance_id, self.type, self.name,
                  self.scheme, self.address, self.port, self.spare)
    __str__ = __repr__

    @property
    def scheme(self):
        """Daemon interface scheme

        :return: http or https if the daemon uses SSL
        :rtype: str
        """
        _scheme = 'http'
        if self.use_ssl:
            _scheme = 'https'
        return _scheme

    @staticmethod
    def get_a_satellite_link(sat_type, sat_dict):
        """Get a SatelliteLink object for a given satellite type and a dictionary

        :param sat_type: type of satellite
        :param sat_dict: satellite configuration data
        :return:
        """
        cls = get_alignak_class('alignak.objects.%slink.%sLink'
                                % (sat_type, sat_type.capitalize()))
        return cls(params=sat_dict, parsing=False)

    def set_arbiter_satellitemap(self, satellitemap):
        """
            arb_satmap is the satellites map in current context:
                - A SatelliteLink is owned by an Arbiter
                - arb_satmap attribute of a SatelliteLink is the map defined
                IN THE satellite configuration but for creating connections,
                we need to have the satellites map from the Arbiter point of view

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
        self.con = None
        self.uri = None

        # Create the HTTP client for the connection
        try:
            self.con = HTTPClient(address=self.arb_satmap['address'], port=self.arb_satmap['port'],
                                  timeout=self.timeout, data_timeout=self.data_timeout,
                                  use_ssl=self.use_ssl, strong_ssl=self.hard_ssl_name_check)
            self.uri = self.con.uri
            # Set the satellite as alive
            self.set_alive()
        except HTTPClientException as exp:
            logger.error("Error with '%s' when creating client: %s", self.name, str(exp))
            # Set the satellite as dead
            self.set_dead()

    def is_connection_try_too_close(self, delay=5):
        """Check if last_connection has been made very recently

        :param delay: minimum delay between two connection try
        :type delay: int
        :return: True if last connection has been made less than `delay` seconds
        :rtype: bool
        """
        if time.time() - self.last_connection < delay:
            return True
        return False

    def set_alive(self):
        """Set alive, reachable, and reset attempts.
        If we change state, raise a status brok update

        :return: None
        """
        was_alive = self.alive
        self.alive = True
        self.reachable = True
        self.attempt = 0

        # We came from dead to alive! We must propagate the good news
        if not was_alive:
            logger.info("Setting % satellite s as alive :)", self.name)
            brok = self.get_update_status_brok()
            self.broks.append(brok)

    def set_dead(self):
        """Set the satellite into dead state:
        If we change state, raise a status brok update

        :return:None
        """
        was_alive = self.alive
        self.alive = False
        self.reachable = False
        self.attempt = 0
        self.con = None

        # We are dead now! ! We must propagate the sad news
        if was_alive:
            logger.warning("Setting the satellite %s as dead :(", self.name)
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
        self.attempt = min(self.attempt + 1, self.max_check_attempts)

        logger.debug("Failed attempt to %s (%d/%d), reason: %s",
                       self.name, self.attempt, self.max_check_attempts, reason)
        # Don't need to warn again and again if the satellite is already dead
        # Only warn when it is alive
        if self.alive:
            logger.warning("Add failed attempt to %s (%d/%d), reason: %s",
                           self.name, self.attempt, self.max_check_attempts, reason)

        # check when we just go HARD (dead)
        if self.attempt >= self.max_check_attempts:
            self.set_dead()

    def put_conf(self, configuration):
        """Send the configuration to the satellite
        HTTP request to the satellite (POST / put_conf)

        :param configuration: The conf to send (data depend on the satellite)
        :type configuration:
        :return: None
        """
        if not self.reachable:
            logger.warning("Not reachable for put_conf: %s", self.name)
            return False

        try:
            self.con.post('put_conf', {'conf': configuration}, wait='long')
            return True
        except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
            logger.warning("[%s] Connection error when sending configuration: %s",
                           self.name, str(exp))
            self.add_failed_check_attempt(reason=str(exp))
            self.set_dead()
        except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
            logger.warning("[%s] Connection timeout when sending configuration: %s",
                           self.name, str(exp))
            self.add_failed_check_attempt(reason=str(exp))
        except HTTPClientException as exp:  # pragma: no cover, simple protection
            logger.error("[%s] Error when sending configuration: %s", self.name, str(exp))
            self.con = None
        except AttributeError as exp:  # pragma: no cover, simple protection
            # Connection is not created
            logger.error("[%s] put_conf - Connection does not exist!", self.name)

        return False

    def get_all_broks(self):
        """Get and clean all of our broks

        :return: list of all broks in the satellite
        :rtype: list
        """
        res = self.broks
        self.broks = []
        return res

    def update_infos(self, now, test=False):
        """Update satellite info each self.check_interval seconds
        so we smooth arbiter actions for just useful actions.
        Create update Brok

        If test is True, do not really ping the daemon

        :return: None
        """
        # First look if it's not too early to ping
        if (now - self.last_check) < self.check_interval:
            print("%s - too early to ping!" % self)
            return False

        self.last_check = now

        # We ping and update the managed list
        if test:
            self.set_alive()
        else:
            self.ping()
        if not self.alive:
            logger.info("Not alive for ping: %s", self.name)
            return False

        if self.attempt > 0:
            logger.info("Not responding to ping: %s (%d / %d)",
                        self.name, self.attempt, self.max_check_attempts)
            return False

        if test:
            self.managed_confs = {}
            if getattr(self, 'schedulers', None):
                # I am a simple satellite
                for (key, val) in self.schedulers.iteritems():
                    self.managed_confs[key] = val['push_flavor']
            elif getattr(self, 'conf', None):
                # I am a scheduler
                return {self.conf.uuid: self.conf.push_flavor}
        else:
            self.update_managed_conf()

        # Update the state of this element
        brok = self.get_update_status_brok()
        self.broks.append(brok)

    def ping(self):
        """Send a HTTP request to the satellite (GET /ping)
        Add failed attempt if an error occurs
        Otherwise, set alive this satellite

        :return: None
        """
        if self.con is None:
            self.create_connection()

        # If the connection failed to initialize, bail out
        if self.con is None:
            self.add_failed_check_attempt('no connection exist on ping')
            return

        logger.debug("Pinging %s", self.name)
        try:
            res = self.con.get('ping')

            # Should return us pong string
            if res == 'pong':
                self.set_alive()
                return True

            # This sould never happen! Except is the source code got modified!
            logger.warning("[%s] I responded '%s' to ping! WTF is it?", self.name, res)
            self.add_failed_check_attempt('ping / NOT pong')
        except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection error when pinging: %s" % str(exp))
            self.set_dead()
        except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection timeout when pinging: %s" % str(exp))
        except HTTPClientException as exp:
            self.add_failed_check_attempt("Error when pinging: %s" % str(exp))

        return False

    def get_running_id(self):
        """Send a HTTP request to the satellite (GET /get_running_id)
        Used to get the daemon running identifier

        :return: Boolean indicating if the running id changed
        :type: bool
        """
        if not self.reachable:
            logger.warning("Not reachable to get the running identifier: %s", self.name)
            return False
        former_running_id = self.running_id

        try:
            self.running_id = self.con.get('get_running_id')
        except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection error when getting "
                                          "the running id: %s" % str(exp))
            self.set_dead()
        except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection timeout when getting "
                                          "the running id: %s" % str(exp))
        except HTTPClientException as exp:
            self.add_failed_check_attempt("Error when getting "
                                          "the running id: %s" % str(exp))

        if former_running_id != self.running_id:
            logger.info("The %s / %s running identifier changed. "
                        "The daemon was certainly restarted!", self.type, self.name)

        return former_running_id != self.running_id

    def get_initial_broks(self, broker_name):
        """Send a HTTP request to the satellite (GET /fill_initial_broks)
        Used to build the initial broks for a broker connecting to a scheduler

        :param broker_name: the concerned broker name
        :type broker_name: str
        :return: Boolean indicating if the running id changed
        :type: bool
        """
        if not self.reachable:
            logger.warning("Not reachable to get the initial broks: %s", self.name)
            return False

        try:
            self.con.get('fill_initial_broks', {'bname': broker_name}, wait='long')
            return True
        except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection error when getting "
                                          "the initial broks: %s" % str(exp))
            self.set_dead()
        except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection timeout when getting "
                                          "the initial broks: %s" % str(exp))
        except HTTPClientException as exp:
            self.add_failed_check_attempt("Error when getting "
                                          "the initial broks: %s" % str(exp))

        return False

    def wait_new_conf(self):
        """Send a HTTP request to the satellite (GET /wait_new_conf)

        TODO: is it still useful, wait_new_conf is implemented in the
        HTTP interface of each daemon

        :return: True if wait new conf, otherwise False
        :rtype: bool
        """
        if not self.reachable:
            logger.debug("Not reachable for wait_new_conf: %s", self.name)
            return False

        try:
            logger.warning("Arbiter wants me to wait for a new configuration")
            self.con.get('wait_new_conf')
            return True
        except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection error when waiting new configuration: %s" 
                                          % str(exp))
            self.set_dead()
        except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection timeout when waiting new configuration: %s" 
                                          % str(exp))
        except HTTPClientException as exp:
            self.add_failed_check_attempt("Error when waiting new configuration: %s" 
                                          % str(exp))

        return False

    def have_conf(self, magic_hash=None):
        """Send a HTTP request to the satellite (GET /have_conf)
        Used to know if the satellite has a conf

        :param magic_hash: Config hash. Only used for HA arbiter communication
        :type magic_hash: int
        :return: Boolean indicating if the satellite has a (specific) configuration
        :type: bool
        """
        if not self.reachable:
            logger.warning("Not reachable for have_conf: %s", self.name)
            return False

        try:
            return self.con.get('have_conf', {'magic_hash': magic_hash})
        except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection error when testing "
                                          "if have a configuration: %s" % str(exp))
            self.set_dead()
        except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection timeout when testing "
                                          "if have a configuration: %s" % str(exp))
        except HTTPClientException as exp:
            self.add_failed_check_attempt("Error when testing "
                                          "if have a configuration: %s" % str(exp))

        return False

    def remove_from_conf(self, sched_id):
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
        if not self.reachable:
            logger.warning("Not reachable for remove_from_conf: %s", self.name)
            return

        try:
            self.con.get('remove_from_conf', {'sched_id': sched_id})
            # todo: do not handle the result to confirm?
            return True
        except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection error when removing from configuration: %s" % str(exp))
            self.set_dead()
        except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection timeout when removing from configuration: %s" % str(exp))
        except HTTPClientException as exp:
            self.add_failed_check_attempt("Error when removing from configuration: %s" % str(exp))

        return False

    def update_managed_conf(self):
        """Send a HTTP request to the satellite (GET /what_i_managed)
        and update managed_conf attribute with dict (cleaned)
        Set to {} on failure

        :return: None
        """
        self.managed_confs = {}

        if not self.reachable:
            logger.warning("Not reachable for update_managed_conf: %s", self.name)
            return

        try:
            res = self.con.get('what_i_managed')
            self.managed_confs = res
            # self.managed_confs = unserialize(str(res))
            return True
        except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection error when "
                                          "getting what I manage: %s" % str(exp))
            self.set_dead()
        except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection timeout when "
                                          "getting what I manage: %s" % str(exp))
        except HTTPClientException as exp:
            self.add_failed_check_attempt("Error when "
                                          "getting what I manage: %s" % str(exp))

        return False

    def do_i_manage(self, cfg_id, push_flavor):
        """Tell if the satellite is managing cfg_id with push_flavor

        :param cfg_id: config id
        :type cfg_id: int
        :param push_flavor: flavor id, random it generated at parsing
        :type push_flavor: int
        :return: True if the satellite has push_flavor in managed_confs[cfg_id]
        :rtype: bool
        """
        if self.managed_confs:
            logger.debug("My managed configurations:")
            for conf in self.managed_confs:
                logger.debug("- %s", conf)
        else:
            logger.debug("No managed configuration!")

        # If not even the cfg_id in the managed_conf, bail out
        if cfg_id not in self.managed_confs:
            logger.warning("I (%s) do not manage this configuration: %s", self.name, cfg_id)
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
        if not self.reachable:
            logger.warning("Not reachable for push_broks: %s", self.name)
            return False

        try:
            self.con.post('push_broks', {'broks': broks}, wait='long')
            return True
        except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection error when pushing broks: %s" % str(exp))
            self.set_dead()
        except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection timeout when pushing broks: %s" % str(exp))
        except HTTPClientException as exp:
            self.add_failed_check_attempt("Error when pushing broks: %s" % str(exp))

        return False

    def get_external_commands(self):
        """Send a HTTP request to the satellite (GET /ping)
        and THEN send a HTTP request to the satellite (GET /get_external_commands)
        Get external commands from satellite.
        Un-serialize data received.

        :return: External Command list on success, [] on failure
        :rtype: list
        """
        if not self.reachable:
            logger.warning("Not reachable for get_external_commands: %s", self.name)
            return []

        try:
            res = self.con.get('get_external_commands', wait='long')
            tab = unserialize(str(res))
            # Protect against bad return
            if not isinstance(tab, list):
                self.con = None
                return []
            return tab
        except HTTPClientConnectionException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection error when "
                                          "getting external commands: %s" % str(exp))
            self.set_dead()
        except HTTPClientTimeoutException as exp:  # pragma: no cover, simple protection
            self.add_failed_check_attempt("Connection timeout when "
                                          "getting external commands: %s" % str(exp))
        except HTTPClientException as exp:
            self.add_failed_check_attempt("Error when "
                                          "getting external commands: %s" % str(exp))
        except AlignakClassLookupException as exp:  # pragma: no cover, simple protection
            logger.error('Cannot un-serialize external commands received: %s', exp)

        return []

    def prepare_for_conf(self):
        """Initialize the pushed configuration dictionary
        with the inner properties that are to be propagated to the satellite link.

        :return: None
        """
        print("- preparing: %s" % self)
        self.cfg = {
            'self_conf': self.give_satellite_cfg(),
            'schedulers': {},
            'arbiters': {}
        }

        # # All the satellite link class properties that are 'to_send' are stored in the 'global'
        # # configuration to be pushed to the satellite when the configuration is dispatched
        # properties = self.__class__.properties
        # for prop, entry in properties.items():
        #     # Do not care of the to_send attribute... send all properties as such each
        #     # satellite link will get all its properties in the received configuration.
        #     # if entry.to_send:
        #     #     self.cfg['global'][prop] = getattr(self, prop)
        #     if hasattr(self, prop):
        #         self.cfg['self_conf'][prop] = getattr(self, prop)
        print("- prepared: %s" % self.cfg)

    def give_satellite_cfg(self):
        """Get the default information for a satellite.

        Overridden by the specific satellites links

        TODO: this should be replaced with an object serialization!

        :return: dictionary of information common to all the links
        :rtype: dict
        """
        return super(SatelliteLink, self).serialize()
        # return self.serialize()
        # return {'instance_id': self.instance_id,
        #         'type': self.type, 'name': self.name,
        #         'port': self.port, 'address': self.address,
        #         # 'uri': self.uri,
        #         'use_ssl': self.use_ssl, 'hard_ssl_name_check': self.hard_ssl_name_check,
        #         'timeout': self.timeout, 'data_timeout': self.data_timeout,
        #         'active': True, 'reachable': True,
        #         'current_attempt': self.attempt,
        #         'max_check_attempts': self.max_check_attempts
        #         }


class SatelliteLinks(Items):
    """Class to handle serveral SatelliteLink"""

    name_property = "name"
    inner_class = SatelliteLink

    def __repr__(self):
        return '<%r %d elements: %r/>' % \
               (self.__class__.__name__, len(self), ', '.join([s.name for s in self]))
    __str__ = __repr__

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
                    print("Daemon Manage sub realms: %s: %s" % (
                    satlink.name, getattr(satlink, 'manage_sub_realms', False)))
                    print("Manage sub realms: %s" % satlink.name)
                    for r_uuid in realm.all_sub_members:
                        getattr(realms[r_uuid], '%ss' % satlink.my_type).append(satlink.uuid)
            else:
                err = "The %s %s got a unknown realm '%s'" % \
                      (satlink.__class__.my_type, satlink.get_name(), r_name)
                satlink.add_error(err)
