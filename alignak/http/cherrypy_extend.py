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
"""This module provide extension functions for Cherrypy
in order to parse specific HTTP content type
See http://cherrypy.readthedocs.org/en/latest/pkg/cherrypy.html#module-cherrypy._cpreqbody
for details about custom processors in Cherrypy
"""
import json
import zlib

import cherrypy
from cherrypy._cpcompat import ntou

from alignak.misc.serialization import unserialize, AlignakClassLookupException


def zlib_processor(entity):  # pragma: no cover, not used in the testing environment...
    """Read application/zlib data and put content into entity.params for later use.

    :param entity: cherrypy entity
    :type entity: cherrypy._cpreqbody.Entity
    :return: None
    """
    if not entity.headers.get(ntou("Content-Length"), ntou("")):
        raise cherrypy.HTTPError(411)

    body = entity.fp.read()
    try:
        body = zlib.decompress(body)
    except zlib.error:
        raise cherrypy.HTTPError(400, 'Invalid zlib data')
    try:
        raw_params = json.loads(body)
    except ValueError:
        raise cherrypy.HTTPError(400, 'Invalid JSON document in zlib data')

    try:
        params = {}
        for key, value in list(raw_params.items()):
            params[key] = unserialize(value.encode("utf8"))
    except TypeError:
        raise cherrypy.HTTPError(400, 'Invalid serialized data in JSON document')
    except AlignakClassLookupException as exp:
        cherrypy.HTTPError(400, 'Cannot un-serialize data received: %s' % exp)

    # Now that all values have been successfully parsed and decoded,
    # apply them to the entity.params dict.
    for key, value in list(params.items()):
        if key in entity.params:
            if not isinstance(entity.params[key], list):
                entity.params[key] = [entity.params[key]]
            entity.params[key].append(value)
        else:
            entity.params[key] = value
