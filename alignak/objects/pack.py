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
#     aviau, alexandre.viau@savoirfairelinux.com
#     Philippe Pépos Petitclerc, ppepos@users.noreply.github.com
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

"""
This module provide Pack and Packs classes used to define 'group' of configurations
"""

import os
import re
try:
    import json
except ImportError:
    json = None  # pylint: disable=C0103

from alignak.objects.item import Item, Items
from alignak.property import StringProp
from alignak.log import logger


class Pack(Item):
    """
    Class to manage a Pack
    A Pack contain multiple configuration files (like all checks for os 'FreeBSD')
    """
    _id = 1  # zero is always special in database, so we do not take risk here
    my_type = 'pack'

    properties = Item.properties.copy()
    properties.update({'pack_name': StringProp(fill_brok=['full_status'])})

    running_properties = Item.running_properties.copy()
    running_properties.update({'macros': StringProp(default={})})

    # For debugging purpose only (nice name)
    def get_name(self):
        """
        Get the name of the pack

        :return: the pack name string or 'UnnamedPack'
        :rtype: str
        """
        try:
            return self.pack_name
        except AttributeError:
            return 'UnnamedPack'


class Packs(Items):
    """
    Class to manage all Pack
    """
    name_property = "pack_name"
    inner_class = Pack

    def load_file(self, path):
        """
        Load files in path parameter to load all configuration files with extension .pack
        of the pack

        :param path: Path where file of pack are
        :type path: str
        :return: None
        """
        # Now walk for it
        for root, dirs, files in os.walk(path):
            for p_file in files:
                if re.search(r"\.pack$", p_file):
                    path = os.path.join(root, p_file)
                    try:
                        file_d = open(path, 'rU')
                        buf = file_d.read()
                        file_d.close()
                    except IOError, exp:
                        logger.error("Cannot open pack file '%s' for reading: %s", path, exp)
                        # ok, skip this one
                        continue
                    self.create_pack(buf, p_file[:-5])

    def create_pack(self, buf, name):
        """
        Create pack with data from configuration file

        :param buf: buffer
        :type buf: str
        :param name: name of file
        :type name: str
        :return: None
        """
        if not json:
            logger.warning("[Pack] cannot load the pack file '%s': missing json lib", name)
            return
        # Ok, go compile the code
        try:
            json_dump = json.loads(buf)
            if 'name' not in json_dump:
                logger.error("[Pack] no name in the pack '%s'", name)
                return
            pack = Pack({})
            pack.pack_name = json_dump['name']
            pack.description = json_dump.get('description', '')
            pack.macros = json_dump.get('macros', {})
            pack.templates = json_dump.get('templates', [pack.pack_name])
            pack.path = json_dump.get('path', 'various/')
            pack.doc_link = json_dump.get('doc_link', '')
            pack.services = json_dump.get('services', {})
            pack.commands = json_dump.get('commands', [])
            if not pack.path.endswith('/'):
                pack.path += '/'
            # Ok, add it
            self[pack._id] = pack
        except ValueError, exp:
            logger.error("[Pack] error in loading pack file '%s': '%s'", name, exp)
