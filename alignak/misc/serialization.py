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
"""
This module provide object serialization for Alignak objects. It basically converts objects to json
"""
import sys
import json
import collections
from alignak.property import NONE_OBJECT

# try:
#     import ujson as json
# except ImportError:
#     import json
#


def default_serialize(obj):
    """JSON serializer for objects not serializable by default json code"""

    # if isinstance(obj, set):  # pragma: no cover, should not have any set in the data!
    #     # Transform a set to a list
    #     return list(obj)
    #
    if hasattr(obj, "serialize") and isinstance(obj.serialize, collections.Callable):
        res = {
            '__sys_python_module__': "%s.%s" % (obj.__class__.__module__,
                                                obj.__class__.__name__),
            'content': obj.serialize(no_json=True, printing=False)
        }
        return res

    if obj is NONE_OBJECT:
        return "None"

    print("-> no serializer for %s: %s" % (type(obj), obj))

    return {
        'type': type(obj),
        'object': obj
    }


def serialize(obj, no_json=True, printing=False, name=''):
    """
    Serialize an object.

    Returns a dict with the following structure ::
       {'__sys_python_module__': "%s.%s" % (o_cls.__module__, o_cls.__name__)
       'content' : obj.serialize()}

    Returns a dict containing an `_error` property if a MemoryError happens during the
    object serialization. See #369.

    :param obj: the object to serialize
    :type obj: alignak.objects.item.Item | dict | list | str
    :param no_json: if True return dict, otherwise return a json
    :type no_json: bool
    :param printing: if True, console prints some information to help debugging
    :type printing: bool
    :param name: the name of the object
    :type name: str

    :return: dict or json dumps dict with the following structure ::

       {'__sys_python_module__': "%s.%s" % (o_cls.__module__, o_cls.__name__)
       'content' : obj.serialize()}
    :rtype: dict | str
    """
    if printing:
        print("Serialize %s (%s): %s" % (name, 'no json' if no_json else 'as json', obj))

    res = obj
    if hasattr(obj, "serialize") and isinstance(obj.serialize, collections.Callable):
        if printing:
            print("-> calling %s serialize %s" % (obj.__class__.__name__,
                                                  'no json' if no_json else 'as json'))
        res = {
            '__sys_python_module__': "%s.%s" % (obj.__class__.__module__,
                                                obj.__class__.__name__),
            'content': obj.serialize(no_json=no_json, printing=printing)
        }

    elif isinstance(obj, (list, set)):
        res = [serialize(item, no_json=no_json, printing=printing) for item in obj]

    if no_json:
        if isinstance(obj, dict):
            if printing:
                print("no json dict object.")
            res = {}
            for key in obj:
                res[key] = serialize(obj[key], no_json=no_json, printing=printing)

        if printing:
            print("no json ->: %s" % res)
        return res

    result = None
    try:
        result = json.dumps(res, ensure_ascii=False, default=default_serialize)
    except MemoryError:
        result = json.dumps(
            {'_error': 'Not enough memory on this computer to correctly manage '
                       'Alignak objects serialization! Sorry for this, '
                       'please log an issue in the project repository.'})

    if printing:
        print("json ->: %s" % result)
    return result


def unserialize(j_obj, no_json=True, printing=False):
    """
    Un-serialize object. If we have __sys_python_module__ we try to safely get the alignak class
    Then we re-instantiate the alignak object

    :param j_obj: json object, dict
    :type j_obj: str (before loads)
    :param no_json: if True, j_obj is a dict, otherwise it's a json and need loads it
    :type no_json: bool
    :param printing: if True, console prints some information to help debugging
    :type printing: bool
    :return: un-serialized object
    """
    if printing:
        print("Un-serialize (%s): %s" % ('as a dict' if no_json else 'as json', type(j_obj)))

    if not j_obj:
        return j_obj

    data = j_obj
    if not no_json:
        if printing:
            print("json ->: %s" % j_obj)
        data = json.loads(j_obj)
        if printing:
            print("-> restored data: %s" % data)
        return data

    if isinstance(data, dict):
        if '__sys_python_module__' in data:
            cls = get_alignak_class(data['__sys_python_module__'])
            # todo: Awful hack for external commands ... need to be refactored!
            if data['__sys_python_module__'] in ['alignak.external_command.ExternalCommand']:
                return cls(data['content']['cmd_line'], data['content']['creation_timestamp'])

            if printing:
                print("-> restoring object: %s" % data['__sys_python_module__'])
            content = unserialize(data['content'], no_json=no_json, printing=printing)
            if printing:
                print("-> restored content: %s" % content)
            return cls(content, parsing=False)

        data_dict = {}
        # for key, value in list(data.items()):
        #     data_dict[key] = unserialize(value, no_json=no_json)
        for key in data:
            data_dict[key] = unserialize(data[key], no_json=no_json, printing=False)
        if printing:
            print("  -> restoring a dict: %s" % data_dict)
        return data_dict

    if isinstance(data, list):
        return [unserialize(item, True) for item in data]

    if printing:
        print("-> restored data: %s" % data)
    return data


def get_alignak_class(python_path):
    """ Get the alignak class the in safest way I could imagine.
    Return None if (cumulative conditions) ::

    * the module does not start with alignak
    * above is false and the module is not is sys.modules
    * above is false and the module does not have the wanted class
    * above is false and the class is not a ClassType

    :param python_path:
    :type python_path: str
    :return: alignak class
    :raise AlignakClassLookupException
    """
    a_module, a_class = python_path.rsplit('.', 1)

    if not a_module.startswith('alignak'):  # pragma: no cover - should never happen!
        raise AlignakClassLookupException("Can't recreate object in module: %s. "
                                          "Not an Alignak module" % a_module)

    if a_module not in sys.modules:  # pragma: no cover - should never happen!
        raise AlignakClassLookupException("Can't recreate object in unknown module: %s. "
                                          "No such Alignak module. "
                                          "Alignak versions may mismatch" % a_module)

    pymodule = sys.modules[a_module]

    if not hasattr(pymodule, a_class):  # pragma: no cover - should never happen!
        raise AlignakClassLookupException("Can't recreate object %s in %s module. "
                                          "Module does not have this attribute. "
                                          "Alignak versions may mismatch" % (a_class, a_module))

    # Awful hack for external commands ... need to be refactored!
    if a_class not in ['ExternalCommand']:
        if not isinstance(getattr(pymodule, a_class), type):  # pragma: no cover - protection
            raise AlignakClassLookupException("Can't recreate object %s in %s module. "
                                              "This type is not a class" % (a_class, a_module))

    return getattr(pymodule, a_class)


class AlignakClassLookupException(Exception):
    """Class for exceptions occurring in get_alignak_class from alignak.misc.serialization

    """
    pass
