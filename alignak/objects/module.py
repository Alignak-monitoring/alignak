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

from alignak.property import StringProp, ListProp
from alignak.util import strip_and_uniq

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Module(Item):
    """
    Class to manage a module
    """
    my_type = 'module'

    properties = Item.properties.copy()
    properties.update({
        'python_name':
            StringProp(),
        'module_alias':
            StringProp(),
        'module_types':
            ListProp(default=[''], split_on_coma=True),
        'modules':
            ListProp(default=[''], split_on_coma=True)
    })

    macros = {}

    def __init__(self, params=None, parsing=True):
        super(Module, self).__init__(params, parsing=parsing)

        # Remove extra Item base class properties...
        for prop in ['customs', 'plus', 'downtimes', 'old_properties',
                     'configuration_errors', 'configuration_warnings']:
            if getattr(self, prop, None):
                delattr(self, prop)

    # For debugging purpose only (nice name)
    def get_name(self):
        """
        Get name of module

        self.fill_default()

        if 'name' not in params:
            self.name = self.get_name()

    def __repr__(self):
        return '<%r %r, module: %r, alias: %r />' % \
               (self.__class__.__name__, self.name, self.python_name, self.module_alias)
    __str__ = __repr__

    # def get_name(self):
    #     """
    #     Get name of module
    #
    #     :return: Name of module
    #     :rtype: str
    #     """
    #     return getattr(self, 'module_alias', 'Unnamed module')

    def get_types(self):
        """
        Get name of module

        :return: Name of module
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
    name_property = "module_alias"
    inner_class = Module

    def linkify(self):
        """Link modules

        :return: None
        """
        pass
        # self.linkify_s_by_plug()

    # def linkify_s_by_plug(self, modules=None):
    #     """
    #     Link modules
    #
    #     :return: None
    #     """
    #     for module in self:
    #         new_modules = []
    #         mods = strip_and_uniq(module.modules)
    #         for plug_name in mods:
    #             plug_name = plug_name.strip()
    #
    #             # don't read void names
    #             if plug_name == '':
    #                 continue
    #
    #             # We are the modules, we search them :)
    #             plug = self.find_by_name(plug_name)
    #             if plug is not None:
    #                 new_modules.append(plug)
    #             else:
    #                 err = "[module] unknown %s module from %s" % (plug_name, module.get_name())
    #                 module.add_error(err)
    #         module.modules = new_modules

    # def explode(self):
    #     """
    #     Explode but not explode because this function is empty
    #
    #     :return: None
    #     """
    #     pass
