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
#     aviau, alexandre.viau@savoirfairelinux.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Sebastien Coavoux, s.coavoux@free.fr
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

"""
This module provide Module and Modules classes used to manage internal and external modules
for each daemon
"""
import logging
from alignak.objects.item import Item, Items

from alignak.property import StringProp, ListProp, IntegerProp, BoolProp

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Module(Item):
    """
    Class to manage a module
    """
    my_type = 'module'

    properties = Item.properties.copy()
    properties.update({
        'name':
            StringProp(default=u'unset'),
        'type':
            StringProp(default=u'unset'),
        'daemon':
            StringProp(default=u'unset'),
        'python_name':
            StringProp(),

        'enabled':
            BoolProp(default=True),

        # Old "deprecated" property - replaced with name
        'module_alias':
            StringProp(),
        # Old "deprecated" property - replaced with type
        'module_types':
            ListProp(default=[u''], split_on_comma=True),
        # Allow a module to be related some other modules
        'modules':
            ListProp(default=[''], split_on_comma=True),

        # Module log level
        'log_level':
            StringProp(default=u'INFO'),

        # Local statsd daemon for collecting daemon metrics
        'statsd_host':
            StringProp(default=u'localhost'),
        'statsd_port':
            IntegerProp(default=8125),
        'statsd_prefix':
            StringProp(default=u'alignak'),
        'statsd_enabled':
            BoolProp(default=False)
    })

    macros = {}

    def __init__(self, params=None, parsing=True):
        # Must be declared in this function rather than as class variable. This because the
        # modules may have some properties that are not the same from one instance to another.
        # Other objects very often have the same properties... but not the modules!
        self.properties = Item.properties.copy()
        self.properties.update({
            'name':
                StringProp(default=u'unset'),
            'type':
                StringProp(default=u'unset'),
            'daemon':
                StringProp(default=u'unset'),
            'python_name':
                StringProp(),
            # Old "deprecated" property - replaced with name
            'module_alias':
                StringProp(),
            # Old "deprecated" property - replaced with type
            'module_types':
                ListProp(default=[''], split_on_comma=True),
            # Allow a module to be related some other modules
            'modules':
                ListProp(default=[''], split_on_comma=True),

            'enabled':
                BoolProp(default=True),

            # Module log level
            'log_level':
                StringProp(default=u'INFO'),

            # Local statsd daemon for collecting daemon metrics
            'statsd_host':
                StringProp(default=u'localhost'),
            'statsd_port':
                IntegerProp(default=8125),
            'statsd_prefix':
                StringProp(default=u'alignak'),
            'statsd_enabled':
                BoolProp(default=False)
        })

        # Manage the missing module name
        if params and 'name' not in params:
            if 'module_alias' in params:
                params['name'] = params['module_alias']
            else:
                params['name'] = "Unnamed"
        if params and 'module_alias' not in params:
            if 'name' in params:
                params['module_alias'] = params['name']
            else:
                params['module_alias'] = "Unnamed"

        super(Module, self).__init__(params, parsing=parsing)

        self.fill_default()

        # Remove extra Item base class properties...
        for prop in ['customs', 'plus', 'downtimes', 'old_properties',
                     'configuration_errors', 'configuration_warnings']:
            if getattr(self, prop, None):
                delattr(self, prop)

    def __repr__(self):  # pragma: no cover
        return '<%r %r, module: %r, type(s): %r />' % \
               (self.__class__.__name__, self.name, getattr(self, 'python_name', 'Unknown'),
                getattr(self, 'type', 'Unknown'))
    __str__ = __repr__

    def get_name(self):
        """
        Get name of module

        :return: Name of module
        :rtype: str
        """
        return getattr(self, 'name', self.module_alias)

    def get_types(self):
        """
        Get types of the module

        :return: Types of the module
        :rtype: str
        """
        return getattr(self, 'module_types', 'Untyped module')

    def is_a_module(self, module_type):
        """
        Is the module of the required type?

        :param module_type: module type to check
        :type: str
        :return: True / False
        """
        if hasattr(self, 'type'):
            return module_type in self.type
        return module_type in self.module_types

    def serialize(self):
        """A module may have some properties that are not defined in the class properties list.
        Serializing a module is the same as serializing an Item but we also also include all the
        existing properties that are not defined in the properties or running_properties
        class list.

        We must also exclude the reference to the daemon that loaded the module!
        """
        res = super(Module, self).serialize()

        cls = self.__class__
        for prop in self.__dict__:
            if prop in cls.properties or prop in cls.running_properties or prop in ['properties',
                                                                                    'my_daemon']:
                continue
            res[prop] = getattr(self, prop)

        return res


class Modules(Items):
    """
    Class to manage list of modules
    Modules is used to group all Module
    """
    name_property = "name"
    inner_class = Module

    def linkify(self):
        """Link a module to some other modules

        :return: None
        """
        self.linkify_s_by_plug()

    def linkify_s_by_plug(self):
        """Link a module to some other modules

        :return: None
        """
        for module in self:
            new_modules = []
            for related in getattr(module, 'modules', []):
                related = related.strip()
                if not related:
                    continue
                o_related = self.find_by_name(related)
                if o_related is not None:
                    new_modules.append(o_related.uuid)
                else:
                    self.add_error("the module '%s' for the module '%s' is unknown!"
                                   % (related, module.get_name()))
            module.modules = new_modules
