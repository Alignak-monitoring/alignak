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
import logging

from alignak.objects.item import Item, Items
from alignak.property import BoolProp, StringProp
from alignak.trigger_functions import OBJS, TRIGGER_FUNCTIONS, set_value

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Trigger(Item):
    """Trigger class provides a simple set of method to compile and execute a python file

    """
    my_type = 'trigger'

    properties = Item.properties.copy()
    properties.update({'trigger_name': StringProp(fill_brok=['full_status']),
                       'code_src': StringProp(default='', fill_brok=['full_status']),
                       })

    running_properties = Item.running_properties.copy()
    running_properties.update({'code_bin': StringProp(default=None),
                               'trigger_broker_raise_enabled': BoolProp(default=False)
                               })

    def __init__(self, params=None, parsing=True):
        if params is None:
            params = {}

        super(Trigger, self).__init__(params, parsing=parsing)
        if 'code_src' in params:
            self.compile()

    def serialize(self):
        res = super(Trigger, self).serialize()
        del res['code_bin']
        return res

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
        if self.code_src:
            self.code_bin = compile(self.code_src, "<irc>", "exec")

    def eval(self, ctx):
        """Execute the trigger

        :param ctx: host or service object
        :type ctx: alignak.objects.schedulingitem.SchedulingItem
        :return: None
        """
        # Ok we can declare for this trigger call our functions
        for (name, fun) in TRIGGER_FUNCTIONS.iteritems():
            locals()[name] = fun

        code = self.code_bin
        env = dict(locals())
        env["self"] = ctx
        del env["ctx"]
        try:
            exec code in env  # pylint: disable=W0122
        except Exception as err:  # pylint: disable=W0703
            set_value(ctx, "UNKNOWN: Trigger error: %s" % err, "", 3)
            logger.error('%s Trigger %s failed: %s ; '
                         '%s', ctx.host_name, self.trigger_name, err, traceback.format_exc())


class Triggers(Items):
    """Triggers class allowed to handle easily several Trigger objects

    """
    name_property = "trigger_name"
    inner_class = Trigger

    def load_file(self, path):
        """Load all trigger files (.trig) in the specified path (recursively)
        and create trigger objects

        :param path: path to start
        :type path: str
        :return: None
        """
        # Now walk for it
        for root, _, files in os.walk(path):
            for t_file in files:
                if re.search(r"\.trig$", t_file):
                    path = os.path.join(root, t_file)
                    try:
                        file_d = open(path, 'rU')
                        buf = file_d.read()
                        file_d.close()
                    except IOError, exp:
                        logger.error("Cannot open trigger file '%s' for reading: %s", path, exp)
                        # ok, skip this one
                        continue
                    self.create_trigger(buf, t_file[:-5])

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
        trigger = Trigger({'trigger_name': name, 'code_src': src})
        trigger.compile()
        # Ok, add it
        self[trigger.uuid] = trigger
        return trigger

    def compile(self):
        """Loop on triggers and call Trigger.compile()

        :return: None
        """
        for i in self:
            i.compile()

    @staticmethod
    def load_objects(conf):
        """Set hosts and services from conf as global var

        :param conf: alignak configuration
        :type conf: dict
        :return: None
        TODO: global statement may not be useful
        """
        OBJS['hosts'] = conf.hosts
        OBJS['services'] = conf.services
        OBJS['timeperiods'] = conf.timeperiods
        OBJS['macromodulations'] = conf.macromodulations
        OBJS['checkmodulations'] = conf.checkmodulations
        OBJS['checks'] = conf.checks
