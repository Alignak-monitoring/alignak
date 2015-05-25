#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  Copyright (C) 2015-2015: Alignak team, see AUTHORS.txt file for contributors
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

import sys
import inspect
import warnings


def deprecation(msg, stacklevel=4):
    warnings.warn(msg, DeprecationWarning, stacklevel=stacklevel)


def make_deprecated_daemon_link(new_module):
    stack = inspect.stack()
    full_mod_name = stack[1][0].f_locals['__name__']
    mod_name = full_mod_name.split('.')[-1]
    deprecation(
        "{fullname} is deprecated module path ; "
        "{name} must now be imported from alignak.objects.{name}"
        " ; please update your code accordingly".format(name=mod_name, fullname=full_mod_name)
    )
    sys.modules[full_mod_name] = new_module
