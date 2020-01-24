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
""" This module contains only a common class for all object created in Alignak: AlignakObject.
"""

import uuid
from copy import copy


def get_a_new_object_id():
    """
    Get a new Alignak object identifier. Uses the uuid version 1 generator

    :rtype uuid: bytes
    :return: uuid
    """
    return str(uuid.uuid4())


class AlignakObject(object):
    """This class provides a generic way to instantiate alignak objects.
    Attributes are serialized dynamically, whether we un-serialize
    them create them at run / parsing time

    """

    properties = {}
    macros = {}

    def __init__(self, params=None, parsing=True):  # pylint: disable=unused-argument
        """
        If parsing is True, then the objects are created from an initial configuration
        read by the Alignak arbiter else the objects are restored from a previously
        serialized instance sent by the arbiter to another daemon.

        This function checks the object uuid in the following manner:
        - in parsing mode, this function simply creates an object uuid
        - in non parsing mode, this function restore the object attributes from the provided params

        :param params: initialization parameters
        :type params: dict
        :param parsing: configuration parsing phase
        :type parsing: bool
        """
        if parsing:
            # Do not manage anything in the properties, it is the job of the Item __init__ function
            if not hasattr(self, 'uuid'):
                self.uuid = get_a_new_object_id()
            return

        # Fill the default if we are not parsing a configuration.
        # This will define some probable missing properties
        self.fill_default()

        if params is None:
            # Object is created without any parameters
            return

        if 'uuid' not in params:
            self.uuid = get_a_new_object_id()

        all_props = {}
        all_props.update(getattr(self, "properties", {}))
        all_props.update(getattr(self, "running_properties", {}))

        for key, value in params.items():
            setattr(self, key, value)

    def serialize(self, no_json=True, printing=False):
        """This function serializes into a simple dictionary object.

        It is used when transferring data to other daemons over the network (http)

        Here is the generic function that simply export attributes declared in the
        properties dictionary of the object.

        :return: Dictionary containing key and value from properties
        :rtype: dict
        """
        # uuid is not in *_properties
        res = {
            'uuid': self.uuid
        }
        for prop in self.__class__.properties:
            if not hasattr(self, prop):
                continue

            res[prop] = getattr(self, prop)

        return res

    def fill_default(self):
        """
        Define the object properties with a default value when the property is not yet defined

        :return: None
        """
        for prop, entry in self.__class__.properties.items():
            if hasattr(self, prop):
                continue
            if not hasattr(entry, 'default'):
                continue
            if not entry.has_default:
                continue

            if hasattr(entry.default, '__iter__'):
                setattr(self, prop, copy(entry.default))
            else:
                setattr(self, prop, entry.default)
