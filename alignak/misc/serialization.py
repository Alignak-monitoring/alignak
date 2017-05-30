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
"""
This module provide object serialization for Alignak objects. It basically converts objects to json
"""
import sys

try:
    import ujson as json
except ImportError:
    import json


def serialize(obj, no_dump=False):
    """
    Serialize an object.

    :param obj: the object to serialize
    :type obj: alignak.objects.item.Item | dict | list | str
    :param no_dump: if True return dict, otherwise return a json
    :type no_dump: bool
    :return: dict or json dumps dict with the following structure ::

       {'__sys_python_module__': "%s.%s" % (o_cls.__module__, o_cls.__name__)
       'content' : obj.serialize()}
    :rtype: dict | str
    """
    if hasattr(obj, "serialize") and callable(obj.serialize):
        o_cls = obj.__class__
        o_dict = {'__sys_python_module__': '', 'content': {}}
        o_dict['content'] = obj.serialize()
        o_dict['__sys_python_module__'] = "%s.%s" % (o_cls.__module__, o_cls.__name__)

    elif isinstance(obj, dict):
        o_dict = {}
        for key, value in obj.iteritems():
            o_dict[key] = serialize(value, True)

    elif isinstance(obj, (list, set)):
        o_dict = [serialize(item, True) for item in obj]

    else:
        o_dict = obj

    if no_dump:
        return o_dict

    return json.dumps(o_dict, ensure_ascii=False)


def unserialize(j_obj, no_load=False):
    """
    Un-serialize object. If we have __sys_python_module__ we try to safely get the alignak class
    Then we re-instantiate the alignak object

    :param j_obj: json object, dict
    :type j_obj: str (before loads)
    :param no_load: if True, j_obj is a dict, otherwize it's a json and need loads it
    :type no_load: bool
    :return: un-serialized object
    """

    if no_load:
        data = j_obj
    else:
        data = json.loads(j_obj)

    if isinstance(data, dict):
        if '__sys_python_module__' in data:
            cls = get_alignak_class(data['__sys_python_module__'])
            if cls is None:
                return {}
            return cls(data['content'], parsing=False)

        else:
            data_dict = {}
            for key, value in data.iteritems():
                data_dict[key] = unserialize(value, True)
            return data_dict

    elif isinstance(data, list):
        return [unserialize(item, True) for item in data]
    else:
        return data


def get_alignak_class(python_path):
    """ Get the alignak class the in safest way I could imagine.
    Return None if (cumulative conditions) ::

    * the module does not start with alignak
    * above is false and the module is not is sys.modules
    * above is false and the module does not have the wanted class
    * above is false and the class in not a ClassType

    :param python_path:
    :type python_path: str
    :return: alignak class
    :raise AlignakClassLookupException
    """
    module, a_class = python_path.rsplit('.', 1)

    if not module.startswith('alignak'):
        raise AlignakClassLookupException("Can't recreate object in module: %s. "
                                          "Not an Alignak module" % module)

    if module not in sys.modules:
        raise AlignakClassLookupException("Can't recreate object in unknown module: %s. "
                                          "No such Alignak module. Alignak versions may mismatch" %
                                          module)

    pymodule = sys.modules[module]

    if not hasattr(pymodule, a_class):
        raise AlignakClassLookupException("Can't recreate object %s in %s module. "
                                          "Module does not have this attribute. "
                                          "Alignak versions may mismatch" % (a_class, module))

    if not isinstance(getattr(pymodule, a_class), type):
        raise AlignakClassLookupException("Can't recreate object %s in %s module. "
                                          "This type is not a class" % (a_class, module))

    return getattr(pymodule, a_class)


class AlignakClassLookupException(Exception):
    """Class for exceptions occurring in get_alignak_class from alignak.misc.serialization

    """
    pass
