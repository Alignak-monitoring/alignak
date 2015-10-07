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
"""This module provide a specific HTTP interface for a Arbiter."""
import cherrypy
import json
import time

from alignak.log import logger
from alignak.http.generic_interface import GenericInterface
from alignak.util import jsonify_r


class ArbiterInterface(GenericInterface):
    """Interface for HA Arbiter. The Slave/Master arbiter can get /push conf

    """

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def have_conf(self, magic_hash):
        """Does the daemon got a configuration (internal) (HTTP GET)

        :param magic_hash: magic hash of configuration
        :type magic_hash: int
        :return: True if the arbiter has the specified conf, False otherwise
        :rtype: bool
        """
        # Beware, we got an str in entry, not an int
        magic_hash = int(magic_hash)
        # I've got a conf and a good one
        if self.app.cur_conf and self.app.cur_conf.magic_hash == magic_hash:
            return True
        else:  # I've no conf or a bad one
            return False

    @cherrypy.expose
    def put_conf(self, conf):
        """HTTP POST to the arbiter with the new conf (master send to slave)

        :param conf: pickled the new configuration
        :type conf:
        :return: None
        """
        with self.app.conf_lock:
            super(ArbiterInterface, self).put_conf(conf)
            self.app.must_run = False
    put_conf.method = 'POST'

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_config(self):
        """Get the managed configuration (internal) (HTTP GET)

        :return: Currently managed configuration
        :rtype: object
        """
        return self.app.conf

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def do_not_run(self):
        """Master tells to slave to not run (HTTP GET)
        Master will ignore this call

        :return: None
        """
        # If I'm the master, ignore the command
        if self.app.is_master:
            logger.debug("Received message to not run. "
                         "I am the Master, ignore and continue to run.")
        # Else, I'm just a spare, so I listen to my master
        else:
            logger.debug("Received message to not run. I am the spare, stopping.")
            self.app.last_master_speack = time.time()
            self.app.must_run = False

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def wait_new_conf(self):
        """Ask the daemon to wait a new conf.
        Reset cur_conf to wait new one

        :return: None
        """
        with self.app.conf_lock:
            self.app.cur_conf = None

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_satellite_list(self, daemon_type=''):
        """Get the satellite names sorted by type (HTTP GET)

        :param daemon_type: daemon type to filter
        :type daemon_type: str
        :return: dict with key *daemon_type* and value list of daemon name
        Example ::

         {'poller': ['Poller1', 'Poller2']}

        :rtype: dict
        """
        with self.app.conf_lock:
            res = {}
            for s_type in ['arbiter', 'scheduler', 'poller', 'reactionner', 'receiver',
                           'broker']:
                if daemon_type and daemon_type != s_type:
                    continue
                satellite_list = []
                res[s_type] = satellite_list
                daemon_name_attr = s_type + "_name"
                daemons = self.app.get_daemons(s_type)
                for dae in daemons:
                    if hasattr(dae, daemon_name_attr):
                        satellite_list.append(getattr(dae, daemon_name_attr))
            return res

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def what_i_managed(self):
        """Dummy call for the arbiter

        :return: {}, always
        :rtype: dict
        """
        return {}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_all_states(self):
        """Return all the data of satellites

        :return: dict containing satellites data
        Output looks like this ::

        {'arbiter' : [{'schedproperty1':'value1' ..}, {'pollerproperty1', 'value11' ..}, ..],
        'scheduler': [..],
        'poller': [..],
        'reactionner': [..],
        'receiver': [..],
         'broker: [..]'
        }

        :rtype: dict
        """
        res = {}
        for s_type in ['arbiter', 'scheduler', 'poller', 'reactionner', 'receiver',
                       'broker']:
            lst = []
            res[s_type] = lst
            for daemon in getattr(self.app.conf, s_type + 's'):
                cls = daemon.__class__
                env = {}
                all_props = [cls.properties, cls.running_properties]

                for props in all_props:
                    for prop in props:
                        if hasattr(daemon, prop):
                            val = getattr(daemon, prop)
                            if prop == "realm":
                                if hasattr(val, "realm_name"):
                                    env[prop] = val.realm_name
                            # give a try to a json able object
                            try:
                                json.dumps(val)
                                env[prop] = val
                            except Exception, exp:
                                logger.debug('%s', exp)
                lst.append(env)
        return res

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_objects_properties(self, table):
        """'Dump all objects of the type in
        [hosts, services, contacts, commands, hostgroups, servicegroups]

        :param table: table name
        :type table: str
        :return: list all properties of all objects
        :rtype: list
        """
        with self.app.conf_lock:
            logger.debug('ASK:: table= %s', str(table))
            objs = getattr(self.app.conf, table, None)
            logger.debug("OBJS:: %s", str(objs))
            if objs is None or len(objs) == 0:
                return []
            res = []
            for obj in objs:
                j_obj = jsonify_r(obj)
                res.append(j_obj)
            return res
