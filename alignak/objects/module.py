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
import warnings
from alignak.objects.item import Item, Items

from alignak.property import StringProp, ListProp

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Module(Item):
    """
    Class to manage a module
    """
    my_type = 'module'

    properties = Item.properties.copy()
    properties.update({
        'name':
            StringProp(default='unset'),
        'type':
            ListProp(default=['unset'], split_on_coma=True),
        'daemon':
            StringProp(default='unset'),
        'python_name':
            StringProp(),
        # Old "deprecated" property - replaced with name
        # 'module_alias':
        #     StringProp(),
        # Old "deprecated" property - replaced with type
        # 'module_types':
        #     ListProp(default=[''], split_on_coma=True),
        # Do not manage modules having modules
        # 'modules':
        #     ListProp(default=[''], split_on_coma=True)
    })

    macros = {}

    def __init__(self, params=None, parsing=True):
        super(Module, self).__init__(params, parsing=parsing)

        self.fill_default()

        # Remove extra Item base class properties...
        for prop in ['customs', 'plus', 'downtimes', 'old_properties',
                     'configuration_errors', 'configuration_warnings']:
            if getattr(self, prop, None):
                delattr(self, prop)

    def __repr__(self):
        return '<%r %r, module: %r, type(s): %r />' % \
               (self.__class__.__name__, self.name, self.python_name, self.type)
    __str__ = __repr__

    @property
    def module_alias(self):
        """Getter for module_alias, maintain compatibility with older modules

        :return: self.name
        """
        return self.name

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
        return module_type in self.module_types


class Modules(Items):
    """
    Class to manage list of modules
    Modules is used to group all Module
    """
    name_property = "name"
    inner_class = Module

    def linkify(self):
        """Link modules

        :return: None
        """
        warnings.warn("Linking modules to modules (%s) is not managed by Alignak.".format(s=self),
                      DeprecationWarning, stacklevel=2)
        pass
