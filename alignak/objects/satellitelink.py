# -*- coding: utf-8 -*-
# pylint:disable=too-many-public-methods

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

import os
import logging
import time

from alignak.util import get_obj_name_two_args_and_void
from alignak.misc.serialization import unserialize, get_alignak_class
from alignak.objects.item import Item, Items
from alignak.property import BoolProp, IntegerProp, FloatProp
from alignak.property import StringProp, ListProp, DictProp, AddrProp
from alignak.http.client import HTTPClient, HTTPClientException, HTTPClientDataException
from alignak.http.client import HTTPClientConnectionException, HTTPClientTimeoutException

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class LinkError(Exception):
    """Exception raised for errors with the satellite links.

    Attributes:
        msg  -- explanation of the error
    """

    def __init__(self, msg):
        super(LinkError, self).__init__(msg)
        logger.error(msg)
        self.msg = msg

    def __str__(self):  # pragma: no cover
        """Exception to String"""
        return "Satellite link error: %s" % self.msg


class SatelliteLink(Item):
    # pylint: disable=too-many-instance-attributes
    """SatelliteLink is a common Class for links between
    Arbiter and other satellites. Used by the Dispatcher object.

    """
    # Next value used for auto generated instance_id
    _next_id = 1

    # All the class properties that are 'to_send' are stored in the 'global'
    # configuration to be pushed to the satellite when the configuration is dispatched
    properties = Item.properties.copy()
    properties.update({
        'instance_id':
            StringProp(to_send=True),

        # When this property is set, the Arbiter will launch the corresponding daemon
        'alignak_launched':
            BoolProp(default=False, fill_brok=['full_status'], to_send=True),
        # This property is set by the Arbiter when it detects that this daemon
        # is needed but not declared in the configuration
        'missing_daemon':
            BoolProp(default=False, fill_brok=['full_status']),

        # Sent to the satellites and used to check the managed configuration
        # Those are not to_send=True because they are updated by the configuration Dispatcher
        # and set when the daemon receives its configuration
        'managed_conf_id':
            StringProp(default=u''),
        'push_flavor':
            StringProp(default=u''),
        'hash':
            StringProp(default=u''),

        # A satellite link has the type/name of the daemon it is related to
        'type':
            StringProp(default=u'', fill_brok=['full_status'], to_send=True),
        'name':
            StringProp(default=u'', fill_brok=['full_status'], to_send=True),

        # Listening interface and address used by the other daemons
        'host':
            StringProp(default=u'0.0.0.0', to_send=True),
        'address':
            StringProp(default=u'127.0.0.1', fill_brok=['full_status'], to_send=True),
        'active':
            BoolProp(default=True, fill_brok=['full_status'], to_send=True),
        'short_timeout':
            IntegerProp(default=3, fill_brok=['full_status'], to_send=True),
        'long_timeout':
            IntegerProp(default=120, fill_brok=['full_status'], to_send=True),

        # the delay (seconds) between two ping retries
        'ping_period':
            IntegerProp(default=5),

        # The maximum number of retries before setting the daemon as dead
        'max_check_attempts':
            IntegerProp(default=3, fill_brok=['full_status']),

        # For a spare daemon link
        'spare':
            BoolProp(default=False, fill_brok=['full_status'], to_send=True),
        'spare_check_interval':
            IntegerProp(default=5, fill_brok=['full_status']),
        'spare_max_check_attempts':
            IntegerProp(default=3, fill_brok=['full_status']),

        'manage_sub_realms':
            BoolProp(default=True, fill_brok=['full_status'], to_send=True),
        'manage_arbiters':
            BoolProp(default=False, fill_brok=['full_status'], to_send=True),
        'modules':
            ListProp(default=[''], split_on_comma=True),
        'polling_interval':
            IntegerProp(default=5, fill_brok=['full_status'], to_send=True),
        'use_timezone':
            StringProp(default=u'NOTSET', to_send=True),
        'realm':
            StringProp(default=u'', fill_brok=['full_status'],
                       brok_transformation=get_obj_name_two_args_and_void),
        'realm_name':
            StringProp(default=u''),
        'satellite_map':
            DictProp(default={}, elts_prop=AddrProp, to_send=True, override=True),
        'use_ssl':
            BoolProp(default=False, fill_brok=['full_status'], to_send=True),
        'hard_ssl_name_check':
            BoolProp(default=True, fill_brok=['full_status'], to_send=True),
        'passive':
            BoolProp(default=False, fill_brok=['full_status'], to_send=True),
    })

    running_properties = Item.running_properties.copy()
    running_properties.update({
        'con':
            StringProp(default=None),
        'uri':
            StringProp(default=None),

        'reachable':    # Can be reached - assumed True as default ;)
            BoolProp(default=False, fill_brok=['full_status']),
        'alive':        # Is alive (attached process s launched...)
            BoolProp(default=False, fill_brok=['full_status']),
        'valid':        # Is valid (the daemon is the expected one)
            BoolProp(default=False, fill_brok=['full_status']),
        'need_conf':    # The daemon needs to receive a configuration
            BoolProp(default=True, fill_brok=['full_status']),
        'have_conf':    # The daemon has received a configuration
            BoolProp(default=False, fill_brok=['full_status']),

        'stopping':     # The daemon is requested to stop
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
        'cfg_managed':
            DictProp(default=None),
        'cfg_to_manage':
            DictProp(default={}),
        'configuration_sent':
            BoolProp(default=False),
        'statistics':
            DictProp(default={}),
    })

    def __init__(self, params=None, parsing=True):
        """Initialize a SatelliteLink

        If parsing is True, we are initializing from a configuration, else we are initializing
        from a copy of another satellite link data. This is used when the daemons receive their
        configuration from the arbiter.

        When initializing from an arbiter configuration, an instance_id property must exist else
        a LinkError exception is raised!

        If a satellite_map property exists in the provided parameters, it will update
        the default existing one
        """
        super(SatelliteLink, self).__init__(params, parsing)

        logger.debug("Initialize a %s, params: %s", self.__class__.__name__, params)

        # My interface context
        self.broks = []
        self.actions = {}
        self.wait_homerun = {}
        self.pushed_commands = []

        self.init_running_properties()

        if parsing:
            # Create a new satellite link identifier
            self.instance_id = u'%s_%d' % (self.__class__.__name__, self.__class__._next_id)
            self.__class__._next_id += 1
        elif 'instance_id' not in params:
            raise LinkError("When not parsing a configuration, "
                            "an instance_id must exist in the provided parameters")

        self.fill_default()

        # Hack for ascending compatibility with Shinken configuration
        try:
            # We received a configuration with a 'name' property...
            if self.name:
                setattr(self, "%s_name" % self.type, self.name)
            else:
                # We received a configuration without a 'name' property... old form!
                if getattr(self, "%s_name" % self.type, None):
                    setattr(self, 'name', getattr(self, "%s_name" % self.type))
                else:
                    self.name = "Unnamed %s" % self.type
                    setattr(self, "%s_name" % self.type, self.name)
        except KeyError:
            setattr(self, 'name', getattr(self, "%s_name" % self.type))

        # Initialize our satellite map, and update if required
        self.set_arbiter_satellite_map(params.get('satellite_map', {}))

        self.cfg = {
            'self_conf': {},
            'schedulers': {},
            'arbiters': {}
        }

        # Create the daemon connection
        self.create_connection()

    def __repr__(self):  # pragma: no cover
        return '<%s - %s/%s, %s//%s:%s, rid: %s, spare: %s, realm: %s, sub-realms: %s, ' \
               'managing: %s (%s) />' \
               % (self.instance_id, self.type, self.name,
                  self.scheme, self.address, self.port, self.running_id,
                  self.spare, self.realm, self.manage_sub_realms,
                  self.managed_conf_id, self.push_flavor)
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
        cls = get_alignak_class('alignak.objects.%slink.%sLink' % (sat_type, sat_type.capitalize()))
        return cls(params=sat_dict, parsing=False)

    def get_livestate(self):
        """Get the SatelliteLink live state.

        The live state is a tuple information containing a state identifier and a message, where:
            state is:
            - 0 for an up and running satellite
            - 1 if the satellite is not reachale
            - 2 if the satellite is dead
            - 3 else (not active)

        :return: tuple
        """
        livestate = 0
        if self.active:
            if not self.reachable:
                livestate = 1
            elif not self.alive:
                livestate = 2
        else:
            livestate = 3

        livestate_output = "%s/%s is %s" % (self.type, self.name, [
            "up and running.",
            "warning because not reachable.",
            "critical because not responding.",
            "not active by configuration."
        ][livestate])

        return (livestate, livestate_output)

    def set_arbiter_satellite_map(self, satellite_map=None):
        """
            satellite_map is the satellites map in current context:
                - A SatelliteLink is owned by an Arbiter
                - satellite_map attribute of a SatelliteLink is the map defined
                IN THE satellite configuration but for creating connections,
                we need to have the satellites map from the Arbiter point of view

        :return: None
        """
        self.satellite_map = {
            'address': self.address, 'port': self.port,
            'use_ssl': self.use_ssl, 'hard_ssl_name_check': self.hard_ssl_name_check
        }
        if satellite_map:
            self.satellite_map.update(satellite_map)

    def get_and_clear_context(self):
        """Get and clean all of our broks, actions, external commands and homerun

        :return: list of all broks of the satellite link
        :rtype: list
        """
        res = (self.broks, self.actions, self.wait_homerun, self.pushed_commands)
        self.broks = []
        self.actions = {}
        self.wait_homerun = {}
        self.pushed_commands = []
        return res

    def get_and_clear_broks(self):
        """Get and clean all of our broks

        :return: list of all broks of the satellite link
        :rtype: list
        """
        res = self.broks
        self.broks = []
        return res

    def prepare_for_conf(self):
        """Initialize the pushed configuration dictionary
        with the inner properties that are to be propagated to the satellite link.

        :return: None
        """
        logger.debug("- preparing: %s", self)
        self.cfg = {
            'self_conf': self.give_satellite_cfg(),
            'schedulers': {},
            'arbiters': {}
        }
        logger.debug("- prepared: %s", self.cfg)

    def give_satellite_cfg(self):
        """Get the default information for a satellite.

        Overridden by the specific satellites links

        :return: dictionary of information common to all the links
        :rtype: dict
        """
        # All the satellite link class properties that are 'to_send' are stored in a
        # dictionary to be pushed to the satellite when the configuration is dispatched
        res = {}
        properties = self.__class__.properties
        for prop, entry in list(properties.items()):
            if hasattr(self, prop) and entry.to_send:
                res[prop] = getattr(self, prop)
        return res

    def give_satellite_json(self):
        """Get the json information for a satellite.

        This to provide information that will be exposed by a daemon on its HTTP interface.

        :return: dictionary of information common to all the links
        :rtype: dict
        """
        daemon_properties = ['type', 'name', 'uri', 'spare', 'configuration_sent',
                             'realm_name', 'manage_sub_realms',
                             'active', 'reachable', 'alive', 'passive',
                             'last_check', 'polling_interval', 'max_check_attempts']

        (livestate, livestate_output) = self.get_livestate()
        res = {
            "livestate": livestate,
            "livestate_output": livestate_output
        }
        for sat_prop in daemon_properties:
            res[sat_prop] = getattr(self, sat_prop, 'not_yet_defined')
        return res

    def manages(self, cfg_part):
        """Tell if the satellite is managing this configuration part

        The managed configuration is formed as a dictionary indexed on the link instance_id:
         {
            u'SchedulerLink_1': {
                u'hash': u'4d08630a3483e1eac7898e7a721bd5d7768c8320',
                u'push_flavor': u'4d08630a3483e1eac7898e7a721bd5d7768c8320',
                u'managed_conf_id': [u'Config_1']
            }
        }

        Note that the managed configuration is a string array rather than a simple string...
        no special for this reason, probably due to the serialization when the configuration is
        pushed :/

        :param cfg_part: configuration part as prepare by the Dispatcher
        :type cfg_part: Conf
        :return: True if the satellite manages this configuration
        :rtype: bool
        """
        logger.debug("Do I (%s/%s) manage: %s, my managed configuration(s): %s",
                     self.type, self.name, cfg_part, self.cfg_managed)

        # If we do not yet manage a configuration
        if not self.cfg_managed:
            logger.info("I (%s/%s) do not manage (yet) any configuration!", self.type, self.name)
            return False

        # Check in the schedulers list configurations
        for managed_cfg in list(self.cfg_managed.values()):
            # If not even the cfg_id in the managed_conf, bail out
            if managed_cfg['managed_conf_id'] == cfg_part.instance_id \
                    and managed_cfg['push_flavor'] == cfg_part.push_flavor:
                logger.debug("I do manage this configuration: %s", cfg_part)
                break
        else:
            logger.warning("I (%s/%s) do not manage this configuration: %s",
                           self.type, self.name, cfg_part)
            return False

        return True

    def create_connection(self):
        """Initialize HTTP connection with a satellite (con attribute) and
        set its uri attribute

        This is called on the satellite link initialization

        :return: None
        """
        # Create the HTTP client for the connection
        try:
            self.con = HTTPClient(address=self.satellite_map['address'],
                                  port=self.satellite_map['port'],
                                  short_timeout=self.short_timeout, long_timeout=self.long_timeout,
                                  use_ssl=self.satellite_map['use_ssl'],
                                  strong_ssl=self.satellite_map['hard_ssl_name_check'])
            self.uri = self.con.uri
        except HTTPClientException as exp:
            # logger.error("Error with '%s' when creating client: %s", self.name, str(exp))
            # Set the satellite as dead
            self.set_dead()
            raise LinkError("Error with '%s' when creating client: %s" % (self.name, str(exp)))

    def set_alive(self):
        """Set alive, reachable, and reset attempts.
        If we change state, raise a status brok update

        alive, means the daemon is prenset in the system
        reachable, means that the HTTP connection is valid

        With this function we confirm that the daemon is reachable and, thus, we assume it is alive!

        :return: None
        """
        was_alive = self.alive
        self.alive = True
        self.reachable = True
        self.attempt = 0

        # We came from dead to alive! We must propagate the good news
        if not was_alive:
            logger.info("Setting %s satellite as alive :)", self.name)
            self.broks.append(self.get_update_status_brok())

    def set_dead(self):
        """Set the satellite into dead state:
        If we change state, raise a status brok update

        :return:None
        """
        was_alive = self.alive
        self.alive = False
        self.reachable = False
        self.attempt = 0
        # We will have to create a new connection...
        self.con = None

        # We are dead now! We must propagate the sad news...
        if was_alive and not self.stopping:
            logger.warning("Setting the satellite %s as dead :(", self.name)
            self.broks.append(self.get_update_status_brok())

    def add_failed_check_attempt(self, reason=''):
        """Set the daemon as unreachable and add a failed attempt
        if we reach the maximum attempts, set the daemon as dead

        :param reason: the reason of adding an attempts (stack trace sometimes)
        :type reason: str
        :return: None
        """
        self.reachable = False
        self.attempt = self.attempt + 1

        logger.debug("Failed attempt for %s (%d/%d), reason: %s",
                     self.name, self.attempt, self.max_check_attempts, reason)
        # Don't need to warn again and again if the satellite is already dead
        # Only warn when it is alive
        if self.alive:
            if not self.stopping:
                logger.warning("Add failed attempt for %s (%d/%d) - %s",
                               self.name, self.attempt, self.max_check_attempts, reason)
            else:
                logger.info("Stopping... failed attempt for %s (%d/%d) - also probably stopping",
                            self.name, self.attempt, self.max_check_attempts)

        # If we reached the maximum attempts, set the daemon as dead
        if self.attempt >= self.max_check_attempts:
            if not self.stopping:
                logger.warning("Set %s as dead, too much failed attempts (%d), last problem is: %s",
                               self.name, self.max_check_attempts, reason)
            else:
                logger.info("Stopping... set %s as dead, too much failed attempts (%d)",
                            self.name, self.max_check_attempts)

            self.set_dead()

    def valid_connection(*outer_args, **outer_kwargs):
        # pylint: disable=unused-argument, no-method-argument
        """Check if the daemon connection is established and valid"""
        def decorator(func):  # pylint: disable=missing-docstring
            def decorated(*args, **kwargs):  # pylint: disable=missing-docstring
                # outer_args and outer_kwargs are the decorator arguments
                # args and kwargs are the decorated function arguments
                link = args[0]
                if not link.con:
                    raise LinkError("The connection is not created for %s" % link.name)
                if not link.running_id:
                    raise LinkError("The connection is not initialized for %s" % link.name)

                return func(*args, **kwargs)
            return decorated
        return decorator

    def communicate(*outer_args, **outer_kwargs):
        # pylint: disable=unused-argument, no-method-argument
        """Check if the daemon connection is authorized and valid"""
        def decorator(func):  # pylint: disable=missing-docstring
            def decorated(*args, **kwargs):  # pylint: disable=missing-docstring
                # outer_args and outer_kwargs are the decorator arguments
                # args and kwargs are the decorated function arguments
                fn_name = func.__name__
                link = args[0]
                if not link.alive:
                    logger.warning("%s is not alive for %s", link.name, fn_name)
                    return None

                try:
                    if not link.reachable:
                        raise LinkError("The %s %s is not reachable" % (link.type, link.name))

                    logger.debug("[%s] Calling: %s, %s, %s", link.name, fn_name, args, kwargs)
                    return func(*args, **kwargs)
                except HTTPClientConnectionException as exp:
                    # A Connection error is raised when the daemon connection cannot be established
                    # No way with the configuration parameters!
                    if not link.stopping:
                        logger.warning("A daemon (%s/%s) that we must be related with "
                                       "cannot be connected: %s", link.type, link.name, exp)
                    else:
                        logger.info("Stopping... daemon (%s/%s) cannot be connected. "
                                    "It is also probably stopping or yet stopped.",
                                    link.type, link.name)
                    link.set_dead()
                except (LinkError, HTTPClientTimeoutException) as exp:
                    link.add_failed_check_attempt("Connection timeout "
                                                  "with '%s': %s" % (fn_name, str(exp)))
                    return False
                except HTTPClientDataException as exp:
                    # A Data error is raised when the daemon HTTP reponse is not 200!
                    # No way with the communication if some problems exist in the daemon interface!
                    # Abort all
                    err = "Some daemons that we must be related with " \
                          "have some interface problems. Sorry, I bail out"
                    logger.error(err)
                    os.sys.exit(err)
                except HTTPClientException as exp:
                    link.add_failed_check_attempt("Error with '%s': %s" % (fn_name, str(exp)))

                return None

            return decorated
        return decorator

    @communicate()
    def get_running_id(self):
        """Send a HTTP request to the satellite (GET /identity)
        Used to get the daemon running identifier that allows to know if the daemon got restarted

        This is called on connection initialization or re-connection

        If the daemon is notreachable, this function will raise an exception and the caller
        will receive a False as return

        :return: Boolean indicating if the running id was received
        :type: bool
        """
        former_running_id = self.running_id

        logger.info("  get the running identifier for %s %s.", self.type, self.name)
        # An exception is raised in this function if the daemon is not reachable
        self.running_id = self.con.get('identity')
        if isinstance(self.running_id, dict):
            self.running_id = self.running_id['running_id']

        if former_running_id == 0:
            if self.running_id:
                logger.info("  -> got: %s.", self.running_id)
                former_running_id = self.running_id

        # If the daemon has just started or has been restarted: it has a new running_id.
        if former_running_id != self.running_id:
            if former_running_id:
                logger.info("  -> The %s %s running identifier changed: %s. "
                            "The daemon was certainly restarted!",
                            self.type, self.name, self.running_id)
            # So we clear all verifications, they are obsolete now.
            logger.info("The running id of the %s %s changed (%s), "
                        "we must clear its context.",
                        self.type, self.name, self.running_id)
            (_, _, _, _) = self.get_and_clear_context()

        # Set the daemon as alive
        self.set_alive()

        return True

    @valid_connection()
    @communicate()
    def stop_request(self, stop_now=False):
        """Send a stop request to the daemon

        :param stop_now: stop now or go to stop wait mode
        :type stop_now: bool
        :return: the daemon response (True)
        """
        logger.debug("Sending stop request to %s, stop now: %s", self.name, stop_now)

        res = self.con.get('stop_request', {'stop_now': '1' if stop_now else '0'})
        return res

    @valid_connection()
    @communicate()
    def update_infos(self, forced=False, test=False):
        """Update satellite info each self.polling_interval seconds
        so we smooth arbiter actions for just useful actions.

        Raise a satellite update status Brok

        If forced is True, then ignore the ping period. This is used when the configuration
        has not yet been dispatched to the Arbiter satellites.

        If test is True, do not really ping the daemon (useful for the unit tests only)

        :param forced: ignore the ping smoothing
        :type forced: bool
        :param test:
        :type test: bool
        :return:
        None if the last request is too recent,
        False if a timeout was raised during the request,
        else the managed configurations dictionary
        """
        logger.debug("Update informations, forced: %s", forced)

        # First look if it's not too early to ping
        now = time.time()
        if not forced and self.last_check and self.last_check + self.polling_interval > now:
            logger.debug("Too early to ping %s, ping period is %ds!, last check: %d, now: %d",
                         self.name, self.polling_interval, self.last_check, now)
            return None

        self.get_conf(test=test)

        # Update the daemon last check timestamp
        self.last_check = time.time()

        # Update the state of this element
        self.broks.append(self.get_update_status_brok())

        return self.cfg_managed

    @valid_connection()
    @communicate()
    def get_daemon_stats(self, details=False):
        """Send a HTTP request to the satellite (GET /get_daemon_stats)

        :return: Daemon statistics
        :rtype: dict
        """
        logger.debug("Get daemon statistics for %s, %s %s", self.name, self.alive, self.reachable)
        return self.con.get('stats%s' % ('?details=1' if details else ''))

    @valid_connection()
    @communicate()
    def get_initial_broks(self, broker_name):
        """Send a HTTP request to the satellite (GET /_initial_broks)

        Used to build the initial broks for a broker connecting to a scheduler

        :param broker_name: the concerned broker name
        :type broker_name: str
        :return: Boolean indicating if the running id changed
        :type: bool
        """
        logger.debug("Getting initial broks for %s, %s %s", self.name, self.alive, self.reachable)
        return self.con.get('_initial_broks', {'broker_name': broker_name}, wait=True)

    @valid_connection()
    @communicate()
    def wait_new_conf(self):
        """Send a HTTP request to the satellite (GET /wait_new_conf)

        :return: True if wait new conf, otherwise False
        :rtype: bool
        """
        logger.debug("Wait new configuration for %s, %s %s", self.name, self.alive, self.reachable)
        return self.con.get('_wait_new_conf')

    @valid_connection()
    @communicate()
    def put_conf(self, configuration, test=False):
        """Send the configuration to the satellite
        HTTP request to the satellite (POST /push_configuration)

        If test is True, store the configuration internally

        :param configuration: The conf to send (data depend on the satellite)
        :type configuration:
        :return: None
        """
        logger.debug("Sending configuration to %s, %s %s", self.name, self.alive, self.reachable)
        # ----------
        if test:
            setattr(self, 'unit_test_pushed_configuration', configuration)
            # print("*** unit tests - sent configuration %s: %s" % (self.name, configuration))
            return True
        # ----------

        return self.con.post('_push_configuration', {'conf': configuration}, wait=True)

    @valid_connection()
    @communicate()
    def has_a_conf(self, magic_hash=None):  # pragma: no cover
        """Send a HTTP request to the satellite (GET /have_conf)
        Used to know if the satellite has a conf

        :param magic_hash: Config hash. Only used for HA arbiter communication
        :type magic_hash: int
        :return: Boolean indicating if the satellite has a (specific) configuration
        :type: bool
        """
        logger.debug("Have a configuration for %s, %s %s", self.name, self.alive, self.reachable)
        self.have_conf = self.con.get('_have_conf', {'magic_hash': magic_hash})
        return self.have_conf

    @valid_connection()
    @communicate()
    def get_conf(self, test=False):
        """Send a HTTP request to the satellite (GET /managed_configurations)
        and update the cfg_managed attribute with the new information
        Set to {} on failure

        the managed configurations are a dictionary which keys are the scheduler link instance id
        and the values are the push_flavor

        If test is True, returns the unit test internally stored configuration

        Returns False if a timeout is raised

        :return: see @communicate, or the managed configuration
        """
        logger.debug("Get managed configuration for %s, %s %s",
                     self.name, self.alive, self.reachable)
        # ----------
        if test:
            self.cfg_managed = {}
            self.have_conf = True
            logger.debug("Get managed configuration test ...")
            if getattr(self, 'unit_test_pushed_configuration', None) is not None:
                # Note this is a dict not a SatelliteLink object !
                for scheduler_link in self.unit_test_pushed_configuration['schedulers'].values():
                    self.cfg_managed[scheduler_link['instance_id']] = {
                        'hash': scheduler_link['hash'],
                        'push_flavor': scheduler_link['push_flavor'],
                        'managed_conf_id': scheduler_link['managed_conf_id']
                    }
            # print("*** unit tests - get managed configuration %s: %s"
            #       % (self.name, self.cfg_managed))
        # ----------
        else:
            self.cfg_managed = self.con.get('managed_configurations')
            logger.debug("My (%s) fresh managed configuration: %s", self.name, self.cfg_managed)

        self.have_conf = (self.cfg_managed != {})

        return self.cfg_managed

    @valid_connection()
    @communicate()
    def push_broks(self, broks):
        """Send a HTTP request to the satellite (POST /push_broks)
        Send broks to the satellite

        :param broks: Brok list to send
        :type broks: list
        :return: True on success, False on failure
        :rtype: bool
        """
        logger.debug("[%s] Pushing %d broks", self.name, len(broks))
        return self.con.post('_push_broks', {'broks': broks}, wait=True)

    @valid_connection()
    @communicate()
    def push_actions(self, actions, scheduler_instance_id):
        """Post the actions to execute to the satellite.
        Indeed, a scheduler post its checks to a poller and its actions to a reactionner.

        :param actions: Action list to send
        :type actions: list
        :param scheduler_instance_id: Scheduler instance identifier
        :type scheduler_instance_id: uuid
        :return: True on success, False on failure
        :rtype: bool
        """
        logger.debug("Pushing %d actions from %s", len(actions), scheduler_instance_id)
        return self.con.post('_push_actions', {'actions': actions,
                                               'scheduler_instance_id': scheduler_instance_id},
                             wait=True)

    @valid_connection()
    @communicate()
    def push_results(self, results, scheduler_name):
        """Send a HTTP request to the satellite (POST /put_results)
        Send actions results to the satellite

        :param results: Results list to send
        :type results: list
        :param scheduler_name: Scheduler name
        :type scheduler_name: uuid
        :return: True on success, False on failure
        :rtype: bool
        """
        logger.debug("Pushing %d results", len(results))
        result = self.con.post('put_results', {'results': results, 'from': scheduler_name},
                               wait=True)
        return result

    @valid_connection()
    @communicate()
    def push_external_commands(self, commands):
        """Send a HTTP request to the satellite (POST /r_un_external_commands)
        to send the external commands to the satellite

        :param results: Results list to send
        :type results: list
        :return: True on success, False on failure
        :rtype: bool
        """
        logger.debug("Pushing %d external commands", len(commands))
        return self.con.post('_run_external_commands', {'cmds': commands}, wait=True)

    @valid_connection()
    @communicate()
    def get_external_commands(self):
        """Send a HTTP request to the satellite (GET /_external_commands) to
        get the external commands from the satellite.

        :return: External Command list on success, [] on failure
        :rtype: list
        """
        res = self.con.get('_external_commands', wait=False)
        logger.debug("Got %d external commands from %s: %s", len(res), self.name, res)
        return unserialize(res, True)

    @valid_connection()
    @communicate()
    def get_broks(self, broker_name):
        """Send a HTTP request to the satellite (GET /_broks)
        Get broks from the satellite.
        Un-serialize data received.

        :param broker_name: the concerned broker link
        :type broker_name: BrokerLink
        :return: Broks list on success, [] on failure
        :rtype: list
        """
        res = self.con.get('_broks', {'broker_name': broker_name}, wait=False)
        logger.debug("Got broks from %s: %s", self.name, res)
        return unserialize(res, True)

    @valid_connection()
    @communicate()
    def get_events(self):
        """Send a HTTP request to the satellite (GET /_events)
        Get monitoring events from the satellite.

        :return: Broks list on success, [] on failure
        :rtype: list
        """
        res = self.con.get('_events', wait=False)
        logger.debug("Got events from %s: %s", self.name, res)
        return unserialize(res, True)

    @valid_connection()
    def get_results(self, scheduler_instance_id):
        """Send a HTTP request to the satellite (GET /_results)
        Get actions results from satellite (only passive satellites expose this method.

        :param scheduler_instance_id: scheduler instance identifier
        :type scheduler_instance_id: str
        :return: Results list on success, [] on failure
        :rtype: list
        """
        res = self.con.get('_results', {'scheduler_instance_id': scheduler_instance_id}, wait=True)
        logger.debug("Got %d results from %s: %s", len(res), self.name, res)
        return res

    @valid_connection()
    def get_actions(self, params):
        """Send a HTTP request to the satellite (GET /_checks)
        Get actions from the scheduler.
        Un-serialize data received.

        :param params: the request parameters
        :type params: str
        :return: Actions list on success, [] on failure
        :rtype: list
        """
        res = self.con.get('_checks', params, wait=True)
        logger.debug("Got checks to execute from %s: %s", self.name, res)
        return unserialize(res, True)


class SatelliteLinks(Items):
    """Class to handle serveral SatelliteLink"""

    name_property = "name"
    inner_class = SatelliteLink

    def __repr__(self):  # pragma: no cover
        return '<%r %d elements: %r/>' % \
               (self.__class__.__name__, len(self), ', '.join([s.name for s in self]))
    __str__ = __repr__

    def linkify(self, modules):
        """Link modules and Satellite links

        :param modules: Module object list
        :type modules: alignak.objects.module.Modules
        :return: None
        """
        logger.debug("Linkify %s with %s", self, modules)
        self.linkify_s_by_module(modules)
