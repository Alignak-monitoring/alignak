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

import time
import os
import re
try:
    import json
except ImportError:
    json = None

from alignak.objects.item import Item, Items
from alignak.property import StringProp
from alignak.log import logger


class Pack(Item):
    """
    Class to manage a Pack
    A Pack contain multiple configuration files (like all checks for os 'FreeBSD')
    """
    id = 1  # zero is always special in database, so we do not take risk here
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
        """
        # Now walk for it
        for root, dirs, files in os.walk(path):
            for file in files:
                if re.search("\.pack$", file):
                    p = os.path.join(root, file)
                    try:
                        fd = open(p, 'rU')
                        buf = fd.read()
                        fd.close()
                    except IOError, exp:
                        logger.error("Cannot open pack file '%s' for reading: %s", p, exp)
                        # ok, skip this one
                        continue
                    self.create_pack(buf, file[:-5])

    def create_pack(self, buf, name):
        """
        Create pack with data from configuration file

        :param buf: buffer
        :type buf: str
        :param name: name of file
        :type name: str
        """
        if not json:
            logger.warning("[Pack] cannot load the pack file '%s': missing json lib", name)
            return
        # Ok, go compile the code
        try:
            d = json.loads(buf)
            if 'name' not in d:
                logger.error("[Pack] no name in the pack '%s'", name)
                return
            p = Pack({})
            p.pack_name = d['name']
            p.description = d.get('description', '')
            p.macros = d.get('macros', {})
            p.templates = d.get('templates', [p.pack_name])
            p.path = d.get('path', 'various/')
            p.doc_link = d.get('doc_link', '')
            p.services = d.get('services', {})
            p.commands = d.get('commands', [])
            if not p.path.endswith('/'):
                p.path += '/'
            # Ok, add it
            self[p.id] = p
        except ValueError, exp:
            logger.error("[Pack] error in loading pack file '%s': '%s'", name, exp)
