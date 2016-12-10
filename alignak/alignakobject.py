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
""" This module contains only a common class for all object created in Alignak: AlignakObject.
"""
from __future__ import print_function
import uuid
import warnings
from copy import copy
from alignak.property import Property, SetProp, StringProp


class AlignakObject(object):
    """This class provides a generic way to instantiate alignak objects.
    Attributes are set dynamically, whether we un-serialize them create them at run / parsing time

    """

    name_property = 'uuid'
    my_type = 'unset'

    properties = {'uuid': StringProp()}
    running_properties = {}
    macros = {}

    def __init__(self, params=None, parsing=True, debug=False):  # pylint: disable=W0613
        """Initialize an Alignak base object

        This method will create and set an object uuid if none exists. If no uuid still exists
        then the object is considered as a fresh new object and all the properties are initialized
        else the properties initialization step is skipped.

        Properties initialization is done by creating a new attribute for each item defined in
        the `properties`, `running_properties` and ` macros` dictionaries. The newly created
        attribute is valued with the default value for the corresponding entry. If no default value
        is defined then the attribute is set as None.

        If some parameters are provided, the object attributes are updated with the corresponding
        parameters value even if those attributes do not exist previously.

        If debug is set, then this method will print information about the object properties

        The parsing parameter indicates that the object is created from the configuration. As such,
        if a property exists in the parameters the corresponding Property has its
        `configuration_set` property set to True, else it remains False. This to allow knowing if
        a property has been valued as default or from the configuration.

        :param debug: print debug information about the object properties
        :param params: parameters used to create the object
        :param parsing: if True, initial creation, else, object unserialization
        """
        if params is None:
            params = {}

        if debug:
            print('AlignakObject __init__: %s, %d params' %
                  (self.__class__, len(params)))
            print('AlignakObject __init__: %s, params list: %s' %
                  (self.__class__, [key for key in params]))
            print('AlignakObject __init__: %s, %d properties' %
                  (self.__class__, len(self.properties)))
            print('AlignakObject __init__: %s, properties list: %s' %
                  (self.__class__, [key for key in self.properties]))
            print('AlignakObject __init__: %d running properties' %
                  len(getattr(self, "running_properties", {})))
            print('AlignakObject __init__: %s, running properties list: %s' %
                  (self.__class__, [key for key in self.running_properties]))

        # Fresh new object or object update/unserialization?
        if parsing:
            self.uuid = uuid.uuid4().hex

        # Create attributes for class properties, running properties and macros (to be confirmed?)
        object_properties = {}
        object_properties.update(getattr(self.__class__, "properties", {}))
        object_properties.update(getattr(self.__class__, "running_properties", {}))
        # object_properties.update(getattr(self, "macros", {}))
        index = 0
        for key, value in params.iteritems():
            index = index + 1

            if hasattr(self, key):
                if debug:
                    print('AlignakObject __init__: %s still exists (%s)' %
                          (key, getattr(self, key)))
                continue

            if key in object_properties and isinstance(object_properties[key], SetProp):
                setattr(self, key, set(value))
            else:
                setattr(self, key, value)

            if debug:
                print("%c %3d: %s = %s" %
                      ('!' if key not in object_properties else ' ',
                       index, key, getattr(self, key, 'not_set')))

        if getattr(self, 'uuid', None) is None:
            # Alert about missing object uuid
            warnings.warn("Object do not have an uuid! %s" % self, RuntimeWarning, stacklevel=2)
            print("Problem with an object %s, no uuid in: %s!" % (self.my_type, self.__dict__))
            self.uuid = uuid.uuid4().hex

        # Fill default values for unset running properties
        # Default values for properties are set-up later in the initialization process...
        self.fill_default(which_properties="running_properties")

        if debug:
            print('AlignakObject __init__: %s, %d attributes' %
                  (self.__class__, len(self.__dict__)))
            print('AlignakObject __init__: %s, attributes list: %s' %
                  (self.__class__, [key for key in self.__dict__]))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def serialize(self, filtered_fields=None):
        """This function serializes into a simple dict object.
        It is used when transferring data to other daemons over the network (http)

        This function simply exports attributes declared in the `properties` and
        `running_properties` of the object.

        All fields which name is defined in the filter list are excluded from the serialization.

        :param filtered_fields: list of filtered fields
        :rtype: list
        :return: Dictionary containing key and value from properties
        :rtype: dict
        """
        res = {}
        all_props = {}
        all_props.update(getattr(self.__class__, "properties", {}))
        all_props.update(getattr(self.__class__, "running_properties", {}))

        for prop in all_props:
            if filtered_fields and prop in filtered_fields:
                continue
            if hasattr(self, prop):
                if isinstance(all_props[prop], SetProp):
                    res[prop] = list(getattr(self, prop))
                else:
                    res[prop] = getattr(self, prop)

        return res

    def fill_default(self, which_properties="properties"):
        """
        Define properties with default value if they are not yet defined

        :param which_properties: default is to set default value for the properties but
        it may be used for the running_properties
        :return: None
        """
        all_props = getattr(self.__class__, which_properties, {})

        for prop, entry in all_props.items():
            if not hasattr(self, prop) and entry.has_default:
                default_value = all_props[prop].pythonize(entry.default)
                if hasattr(entry.default, '__iter__'):
                    setattr(self, prop, copy(default_value))
                else:
                    setattr(self, prop, default_value)
