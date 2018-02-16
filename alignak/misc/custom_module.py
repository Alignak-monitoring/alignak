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
#  Copyright (C) 2015-2015:
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr

"""This module provides CustomModule class. Used to customize a module namespace

"""
from types import ModuleType


# pylint: disable=super-on-old-class,too-few-public-methods
class CustomModule(ModuleType):
    """Custom module that can be used to customize a module namespace,

    example usage:

    >>> import sys
    >>> assert __name__ == 'custom_module'  # required for the import after
    >>> class MyCustomModule(CustomModule):
    ...     count = 0
    ...     @property
    ...     def an_attribute(self):
    ...         self.count += 1
    ...         return "hey ! I'm a module attribute but also a property !"
    >>> sys.modules[__name__] = MyCustomModule(__name__, globals())

    # then, in another module:
    >>> import custom_module
    >>> assert custom_module.count == 0
    >>> custom_module.an_attribute
    "hey ! I'm a module attribute but also a property !"
    >>> assert custom_module.count == 1
    """

    def __init__(self, name, orig_mod_globals):
        super(CustomModule, self).__init__(name)
        self.__dict__.update(**orig_mod_globals)
