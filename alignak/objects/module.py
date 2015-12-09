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

from alignak.objects.item import Item, Items

from alignak.property import StringProp, ListProp
from alignak.util import strip_and_uniq
from alignak.log import logger


class Module(Item):
    """
    Class to manage a module
    """
    _id = 1  # zero is always special in database, so we do not take risk here
    my_type = 'module'

    properties = Item.properties.copy()
    properties.update({
        'module_alias': StringProp(),
        'python_name': StringProp(),
        'modules': ListProp(default=[''], split_on_coma=True),
    })

    macros = {}

    # For debugging purpose only (nice name)
    def get_name(self):
        """
        Get name of module

        :return: Name of module
        :rtype: str
        """
        return self.module_alias

    def __repr__(self):
        return '<module module=%s alias=%s />' % (self.python_name, self.module_alias)

    __str__ = __repr__


class Modules(Items):
    """
    Class to manage list of Module
    Modules is used to regroup all Module
    """
    name_property = "module_alias"
    inner_class = Module

    def linkify(self):
        """
        Link modules

        :return: None
        """
        self.linkify_s_by_plug()

    def linkify_s_by_plug(self):
        """
        Link modules

        :return: None
        """
        for module in self:
            new_modules = []
            mods = strip_and_uniq(module.modules)
            for plug_name in mods:
                plug_name = plug_name.strip()

                # don't read void names
                if plug_name == '':
                    continue

                # We are the modules, we search them :)
                plug = self.find_by_name(plug_name)
                if plug is not None:
                    new_modules.append(plug)
                else:
                    err = "[module] unknown %s module from %s" % (plug_name, module.get_name())
                    logger.error(err)
                    module.configuration_errors.append(err)
            module.modules = new_modules

    def explode(self):
        """
        Explode but not explode because this function is empty

        :return: None
        """
        pass
