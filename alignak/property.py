# -*- coding: utf-8 -*-
# -*- mode: python ; coding: utf-8 -*-
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
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Guillaume Bour, guillaume@bour.cc
#     Frédéric Vachon, fredvac@gmail.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Romain Forlot, rforlot@yahoo.com
#     Christophe SIMON, christophe.simon@dailymotion.com

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
"""This module provides property classes.
It is used during configuration parsing to ensure attribute type in objects.
Each class implements a pythonize method that cast data into the wanted type.

"""
import re
import logging
from alignak.util import to_float, to_split, to_char, to_int, unique_value, list_split

__all__ = ('UnusedProp', 'BoolProp', 'IntegerProp', 'FloatProp',
           'CharProp', 'StringProp', 'ListProp', 'DictProp',
           'FULL_STATUS', 'CHECK_RESULT')

# Suggestion
# Is this useful? see above
__author__ = "Hartmut Goebel <h.goebel@goebel-consult.de>"
__copyright__ = "Copyright 2010-2011 by Hartmut Goebel <h.goebel@goebel-consult.de>"
__licence__ = "GNU Affero General Public License version 3 (AGPL v3)"

FULL_STATUS = 'full_status'
CHECK_RESULT = 'check_result'

NONE_OBJECT = object()


class Property(object):
    # pylint: disable=too-many-instance-attributes
    """Baseclass of all properties.

    Same semantic for all subclasses (except UnusedProp): The property
    is required if, and only if, the default value is `None`.

    """

    def __init__(self, default=NONE_OBJECT, class_inherit=None,  # pylint: disable=R0913
                 unmanaged=False, _help='', no_slots=False,
                 fill_brok=None, brok_transformation=None, retention=False,
                 retention_preparation=None, retention_restoration=None, to_send=False,
                 override=False, managed=True, split_on_comma=True,
                 keep_empty=False, merging='uniq', special=False):
        # pylint: disable=too-many-locals
        """
        `default`:
            the default value to be used if this property is not set.
            If default is None, this property is required.

        `class_inherit`:
            List of 2-tuples, (Service, 'blabla'): must set this property to the
            Service class with name blabla. if (Service, None): must set this property
            to the Service class with same name

        `unmanaged`: ....

        `help`: usage text

        `no_slots`:
            do not take this property for __slots__

        `fill_brok`:
            if set, send to broker. There are two categories:
                FULL_STATUS for initial and update status,
                CHECK_RESULT for check results

        `retention`:
            if set, the property will be saved in the retention files
        `retention_preparation`:
            function name, if set, this function will be called with the property before
            saving the date to the retention
        `retention_restoration`:
            function name, if set, this function will be called with the restored retention data

        `split_on_comma`:
            indicates that list property value should not be split on comma delimiter
            (values may contain commas that we want to keep).

        Only for the initial call:

        brok_transformation: if set, will call the function with the
                     value of the property when flattening
                     data is necessary (like realm_name instead of
                     the realm object).

        override: for scheduler, if the property must override the
                     value of the configuration we send it

        managed: property that is managed in Nagios but not in Alignak

        merging: for merging properties, should we take only one or we can
                     link with ,

        special: Is this property "special" : need a special management
        see is_correct function in host and service

        """

        self.default = default
        self.has_default = (default is not NONE_OBJECT)
        self.required = not self.has_default
        self.class_inherit = class_inherit or []
        self.help = _help or ''
        self.unmanaged = unmanaged
        self.no_slots = no_slots
        self.fill_brok = fill_brok or []
        self.brok_transformation = brok_transformation
        self.retention = retention
        self.retention_preparation = retention_preparation
        self.retention_restoration = retention_restoration
        self.to_send = to_send
        self.override = override
        self.managed = managed
        self.unused = False
        self.merging = merging
        self.split_on_comma = split_on_comma
        self.keep_empty = keep_empty
        self.special = special

    def __repr__(self):  # pragma: no cover
        return '<Property %r, default: %r />' % (self.__class__, self.default)
    __str__ = __repr__

    def pythonize(self, val):  # pylint: disable=no-self-use
        """Generic pythonize method

        :param val: value to python
        :type val:
        :return: the value itself
        :rtype:
        """
        return val


class UnusedProp(Property):
    """A unused Property. These are typically used by Nagios but
    no longer useful/used by Alignak.

    This is just to warn the user that the option he uses is no more used
    in Alignak.

    """

    def __init__(self, text=None):
        """Create a new Unused property

        Since this property is not used, there is no use for other
        parameters than 'text'.
       'text' a some usage text if present, will print it to explain
        why it's no more useful

        :param text:
        :type text: None | str
        :return: None
        """
        super(UnusedProp, self).__init__(default=NONE_OBJECT,
                                         class_inherit=[],
                                         managed=True)

        if text is None:
            text = ("This parameter is no longer useful in the "
                    "Alignak architecture.")
        self.text = text
        self.unused = True


class BoolProp(Property):
    """A Boolean Property.

    Boolean values are currently case insensitively defined as 0,
    false, no, off for False, and 1, true, yes, on for True).
    """
    def pythonize(self, val):
        """Convert value into a boolean

        :param val: value to convert
        :type val: bool, int, str
        :return: boolean corresponding to value ::

        {'1': True, 'yes': True, 'true': True, 'on': True,
         '0': False, 'no': False, 'false': False, 'off': False}

        :rtype: bool
        """
        __boolean_states__ = {'1': True, 'yes': True, 'true': True, 'on': True,
                              '0': False, 'no': False, 'false': False, 'off': False}

        if isinstance(val, bool):
            return val
        val = unique_value(val).lower()
        if val in list(__boolean_states__.keys()):
            return __boolean_states__[val]

        raise PythonizeError("Cannot convert '%s' to a boolean value" % val)


class IntegerProp(Property):
    """Integer property"""

    def pythonize(self, val):
        """Convert value into an integer::

        * If value is a list, try to take the last element
        * Then call float(int(val))

        :param val: value to convert
        :type val:
        :return: integer corresponding to value
        :rtype: int
        """
        return to_int(unique_value(val))


class FloatProp(Property):
    """Float property"""

    def pythonize(self, val):
        """Convert value into a float::

        * If value is a list, try to take the last element
        * Then call float(val)

        :param val: value to convert
        :type val:
        :return: float corresponding to value
        :rtype: float
        """
        return to_float(unique_value(val))


class CharProp(Property):
    """One character string property"""

    def pythonize(self, val):
        """Convert value into a char ::

        * If value is a list try, to take the last element
        * Then take the first char of val (first elem)

        :param val: value to convert
        :type val:
        :return: char corresponding to value
        :rtype: str
        """
        return to_char(unique_value(val))


class StringProp(Property):
    """String property"""

    def pythonize(self, val):
        """Convert value into a string::

        * If value is a list, try to take the last element

        :param val: value to convert
        :type val:
        :return: str corresponding to value
        :rtype: str
        """
        return unique_value(val).strip()


class PathProp(StringProp):
    """ A string property representing a "running" (== VAR) file path """


class ConfigPathProp(StringProp):
    """ A string property representing a config file path """


class ListProp(Property):
    """List property"""

    def pythonize(self, val):
        """Convert value into a list::

        * split value (or each element if value is a list) on coma char
        * strip split values

        :param val: value to convert
        :type val: str
        :return: list corresponding to value
        :rtype: list
        """
        if isinstance(val, list):
            return [s.strip() if hasattr(s, "strip") else s
                    for s in list_split(val, self.split_on_comma)
                    if hasattr(s, "strip") and s.strip() != '' or self.keep_empty]

        return [s.strip() if hasattr(s, "strip") else s
                for s in to_split(val, self.split_on_comma)
                if hasattr(s, "strip") and s.strip() != '' or self.keep_empty]


class SetProp(ListProp):
    """ Set property
    """
    def pythonize(self, val):
        """Convert value into a set

        * Simply convert to a set the value return by pythonize from ListProp

        :param val: value to convert
        :type val: str
        :return: set corresponding to the value
        :rtype: set
        """
        return set(super(SetProp, self).pythonize(val))


class LogLevelProp(StringProp):
    """ A string property representing a logging level """

    def pythonize(self, val):
        """Convert value into a log level property::

        * If value is a list, try to take the last element
        * get logging level base on the value

        :param val: value to convert
        :type val:
        :return: log level corresponding to value
        :rtype: str
        """
        return logging.getLevelName(unique_value(val))


class DictProp(Property):
    """Dict property

    """
    # pylint: disable=keyword-arg-before-vararg
    def __init__(self, elts_prop=None, *args, **kwargs):
        """Dictionary of values.
             If elts_prop is not None, must be a Property subclass
             All dict values will be casted as elts_prop values when pythonized

            elts_prop = Property of dict members
        """
        super(DictProp, self).__init__(*args, **kwargs)

        if elts_prop is not None and not issubclass(elts_prop, Property):
            raise TypeError("DictProp constructor only accept Property"
                            "sub-classes as elts_prop parameter")
        self.elts_prop = None

        if elts_prop is not None:
            self.elts_prop = elts_prop()

    def pythonize(self, val):
        """Convert value into a dict::

        * If value is a list, try to take the last element
        * split "key=value" string and convert to { key:value }

        :param val: value to convert
        :type val:
        :return: log level corresponding to value
        :rtype: str
        """
        val = unique_value(val)

        def split(keyval):
            """Split key-value string into (key,value)

            :param keyval: key value string
            :return: key, value
            :rtype: tuple
            """
            matches = re.match(r"^\s*([^\s]+)\s*=\s*([^\s]+)\s*$", keyval)
            if matches is None:
                raise ValueError

            return (
                matches.group(1),
                # >2.4 only. we keep it for later. m.group(2) if self.elts_prop is None
                # else self.elts_prop.pythonize(m.group(2))
                (self.elts_prop.pythonize(matches.group(2)),
                 matches.group(2))[self.elts_prop is None]
            )

        if val is None:
            return dict()

        if self.elts_prop is None:
            return val

        # val is in the form "key1=addr:[port],key2=addr:[port],..."
        return dict([split(kv) for kv in to_split(val)])


class AddrProp(Property):
    """Address property (host + port)"""

    def pythonize(self, val):
        """Convert value into a address ip format::

        * If value is a list, try to take the last element
        * match ip address and port (if available)

        :param val: value to convert
        :type val:
        :return: address/port corresponding to value
        :rtype: dict
        """
        val = unique_value(val)
        matches = re.match(r"^([^:]*)(?::(\d+))?$", val)
        if matches is None:
            raise ValueError

        addr = {'address': matches.group(1)}
        if matches.group(2) is not None:
            addr['port'] = int(matches.group(2))

        return addr


class ToGuessProp(Property):
    """Unknown property encountered while parsing"""

    def pythonize(self, val):
        """If value is a single list element just return the element
        does nothing otherwise

        :param val: value to convert
        :type val:
        :return: converted value
        :rtype:
        """
        if isinstance(val, list) and len(set(val)) == 1:
            # If we have a list with a unique value just use it
            return val[0]

        # Well, can't choose to remove something.
        return val


class IntListProp(ListProp):
    """Integer List property"""
    def pythonize(self, val):
        """Convert value into a integer list::

        * Try to convert into a list
        * Convert each element into a int

        :param val: value to convert
        :type val:
        :return: integer list corresponding to value
        :rtype: list[int]
        """
        val = super(IntListProp, self).pythonize(val)
        try:
            return [int(e) for e in val]
        except ValueError as value_except:
            raise PythonizeError(str(value_except))


class PythonizeError(Exception):
    """Simple Exception raise during pythonize call

    """
    pass
