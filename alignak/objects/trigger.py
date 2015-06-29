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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Guillaume Bour, guillaume@bour.cc
#     aviau, alexandre.viau@savoirfairelinux.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Romain Forlot, rforlot@yahoo.com

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
"""This module provides Trigger and Triggers classes.
Triggers are python files executed after the Scheduler has received a check result
Typical use is for passive results. This allows passive check data to be modified if necessary

"""
import os
import re
import traceback

from alignak.objects.item import Item, Items
from alignak.property import BoolProp, StringProp
from alignak.log import logger
from alignak.trigger_functions import objs, trigger_functions, set_value


class Trigger(Item):
    """Trigger class provides a simple set of method to compile and execute a python file

    """
    id = 1  # zero is always special in database, so we do not take risk here
    my_type = 'trigger'

    properties = Item.properties.copy()
    properties.update({'trigger_name': StringProp(fill_brok=['full_status']),
                       'code_src': StringProp(default='', fill_brok=['full_status']),
                       })

    running_properties = Item.running_properties.copy()
    running_properties.update({'code_bin': StringProp(default=None),
                               'trigger_broker_raise_enabled': BoolProp(default=False)
                               })

    def get_name(self):
        """Accessor to trigger_name attribute

        :return: trigger name
        :rtype: str
        """
        try:
            return self.trigger_name
        except AttributeError:
            return 'UnnamedTrigger'

    def compile(self):
        """Compile the trigger

        :return: None
        """
        self.code_bin = compile(self.code_src, "<irc>", "exec")

    def eval(myself, ctx):
        """Execute the trigger

        :param myself: self object but self will be use after exec (locals)
        :param ctx: host or service object
        :type ctx: alignak.objects.schedulingitem.SchedulingItem
        :return: None
        """
        self = ctx

        # Ok we can declare for this trigger call our functions
        for (n, f) in trigger_functions.iteritems():
            locals()[n] = f

        code = myself.code_bin  # Comment? => compile(myself.code_bin, "<irc>", "exec")
        try:
            exec code in dict(locals())
        except Exception as err:
            set_value(self, "UNKNOWN: Trigger error: %s" % err, "", 3)
            logger.error('%s Trigger %s failed: %s ; '
                         '%s' % (self.host_name, myself.trigger_name, err, traceback.format_exc()))


    def __getstate__(self):
        return {'trigger_name': self.trigger_name,
                'code_src': self.code_src,
                'trigger_broker_raise_enabled': self.trigger_broker_raise_enabled}

    def __setstate__(self, d):
        self.trigger_name = d['trigger_name']
        self.code_src = d['code_src']
        self.trigger_broker_raise_enabled = d['trigger_broker_raise_enabled']


class Triggers(Items):
    """Triggers class allowed to handle easily several Trigger objects

    """
    name_property = "trigger_name"
    inner_class = Trigger

    def load_file(self, path):
        """Load all trigger files (.trig) in the specified path (recursively)
        and create trigger objects

        :param path: path to start
        :return: None
        """
        # Now walk for it
        for root, dirs, files in os.walk(path):
            for file in files:
                if re.search("\.trig$", file):
                    p = os.path.join(root, file)
                    try:
                        fd = open(p, 'rU')
                        buf = fd.read()
                        fd.close()
                    except IOError, exp:
                        logger.error("Cannot open trigger file '%s' for reading: %s", p, exp)
                        # ok, skip this one
                        continue
                    self.create_trigger(buf, file[:-5])

    def create_trigger(self, src, name):
        """Create a trigger with source and name

        :param src: python code source
        :type src: str
        :param name: trigger name
        :type name: str
        :return: new trigger object
        :rtype: alignak.objects.trigger.Trigger
        """
        # Ok, go compile the code
        t = Trigger({'trigger_name': name, 'code_src': src})
        t.compile()
        # Ok, add it
        self[t.id] = t
        return t

    def compile(self):
        """Loop on triggers and call Trigger.compile()

        :return: None
        """
        for i in self:
            i.compile()

    def load_objects(self, conf):
        """Set hosts and services from conf as global var

        :param conf: alignak configuration
        :type conf: dict
        :return: None
        TODO: global statement may not be useful
        """
        global objs
        objs['hosts'] = conf.hosts
        objs['services'] = conf.services
