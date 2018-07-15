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
import collections

try:
    import ujson as json
except ImportError:
    import json


def serialize(obj, no_dump=False):
    """
    Serialize an object.

    Returns a dict containing an `_error` property if a MemoryError happens during the
    object serialization. See #369.

    :param obj: the object to serialize
    :type obj: alignak.objects.item.Item | dict | list | str
    :param no_dump: if True return dict, otherwise return a json
    :type no_dump: bool
    :return: dict or json dumps dict with the following structure ::

       {'__sys_python_module__': "%s.%s" % (o_cls.__module__, o_cls.__name__)
       'content' : obj.serialize()}
    :rtype: dict | str
    """
    # print("Serialize (%s): %s" % (no_dump, obj))

    if hasattr(obj, "serialize") and isinstance(obj.serialize, collections.Callable):
        o_dict = {
            '__sys_python_module__': "%s.%s" % (obj.__class__.__module__, obj.__class__.__name__),
            'content': obj.serialize()
        }

    elif isinstance(obj, dict):
        o_dict = {}
        for key, value in list(obj.items()):
            o_dict[key] = serialize(value, True)

    elif isinstance(obj, (list, set)):
        o_dict = [serialize(item, True) for item in obj]

    else:
        o_dict = obj

    if no_dump:
        return o_dict

    result = None
    try:
        result = json.dumps(o_dict, ensure_ascii=False)
    except MemoryError:
        return {'_error': 'Not enough memory on this computer to correctly manage Alignak '
                          'objects serialization! '
                          'Sorry for this, please log an issue in the project repository.'}

    return result


def unserialize(j_obj, no_load=False):
    """
    Un-serialize object. If we have __sys_python_module__ we try to safely get the alignak class
    Then we re-instantiate the alignak object

    :param j_obj: json object, dict
    :type j_obj: str (before loads)
    :param no_load: if True, j_obj is a dict, otherwise it's a json and need loads it
    :type no_load: bool
    :return: un-serialized object
    """
    if not j_obj:
        return j_obj
    # print("Unserialize (%s): %s" % (no_load, j_obj))

    if no_load:
        data = j_obj
    else:
        data = json.loads(j_obj)

    if isinstance(data, dict):
        if '__sys_python_module__' in data:
            cls = get_alignak_class(data['__sys_python_module__'])
            # Awful hack for external commands ... need to be refactored!
            if data['__sys_python_module__'] in ['alignak.external_command.ExternalCommand']:
                return cls(data['content']['cmd_line'], data['content']['creation_timestamp'])

            return cls(data['content'], parsing=False)

        data_dict = {}
        for key, value in list(data.items()):
            data_dict[key] = unserialize(value, True)
        return data_dict

    if isinstance(data, list):
        return [unserialize(item, True) for item in data]

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
    a_module, a_class = python_path.rsplit('.', 1)

    if not a_module.startswith('alignak'):  # pragma: no cover - should never happen!
        raise AlignakClassLookupException("Can't recreate object in module: %s. "
                                          "Not an Alignak module" % a_module)

    if a_module not in sys.modules:  # pragma: no cover - should never happen!
        raise AlignakClassLookupException("Can't recreate object in unknown module: %s. "
                                          "No such Alignak module. Alignak versions may mismatch" %
                                          a_module)

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
