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
#     Jean Gabes, naparuba@gmail.com
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
""" This module provides ModulesContext class that allow Alignak module
to load other module.
This will become deprecated with namespace in Alignak
and keep for backward compatibility with Shinken.

"""
import os
import sys


from alignak.modulesmanager import ModulesManager


class ModulesContext(object):
    """ModulesContext class is used to load modules in Alignak
    from modules_dir defined in configuration

    """
    def __init__(self):
        self.modules_dir = None

    def set_modulesdir(self, modulesdir):
        """Setter for modulesdir attribute

        :param modulesdir: value to set
        :type modulesdir: srt
        :return: None
        """
        self.modules_dir = modulesdir

    def get_modulesdir(self):
        """Getter for modulesdir attribute

        :return: folder of modules
        :rtype: str
        """
        return self.modules_dir

    def get_module(self, mod_name):
        """Get and load a module

        :param mod_name: module name to get
        :type mod_name: str
        :return: module
        :rtype: object
        """
        if self.modules_dir and self.modules_dir not in sys.path:
            sys.path.append(self.modules_dir)
        if self.modules_dir:
            mod_dir = os.path.join(self.modules_dir, mod_name)
        else:
            mod_dir = None
        # to keep it back-compatible with previous Alignak module way,
        # we first try with "import `mod_name`.module" and if we succeed
        # then that's the one to actually use:
        mod = ModulesManager.try_best_load('.module', mod_name)
        if mod:
            return mod
        # otherwise simply try new and old style:
        return ModulesManager.try_load(mod_name, mod_dir)

# pylint: disable=C0103
modulesctx = ModulesContext()
