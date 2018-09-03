# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines

#
# Because some functions are sometimes called without all arguments!
# These are mainly brok_transformation functions that are called with the concerned
# object as first parameter (usually self)
# pylint: disable=unused-argument

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
#     xkilian, fmikus@acktomic.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Squiz, squiz@squiz.confais.org
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Gerhard Lausser, gerhard.lausser@consol.de
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
"""This module provide a lot of utility functions.
You can find functions for time management, type management (pythonization),
macros solving, sorting, parsing, file handling, filters.

"""
import re
import json
import argparse
import logging

# pylint: disable=unused-import
NUMPY = True
try:
    # use numpy if installed
    import numpy as np
    from numpy import percentile
except ImportError:  # pragma: no cover
    import math
    import functools
    NUMPY = False

    # Replace the numpy percentile function!
    def percentile(n, percent, key=lambda x: x):
        # pylint: disable=invalid-name
        """
        Find the percentile of a list of values.

        @parameter N - is a list of values. Note N MUST BE already sorted.
        @parameter percent - a float value from 0.0 to 1.0.
        @parameter key - optional key function to compute value from each element of N.

        @return - the percentile of the values
        """
        if not n:
            return None
        if percent > 1:
            percent = percent / 100
        k = (len(n)-1) * percent
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return key(n[int(k)])
        d0 = key(n[int(f)]) * (c-k)
        d1 = key(n[int(c)]) * (k-f)
        return d0+d1


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


# ########## Strings #############
def split_semicolon(line, maxsplit=None):
    r"""Split a line on semicolons characters but not on the escaped semicolons

    :param line: line to split
    :type line: str
    :param maxsplit: maximal number of split (if None, no limit)
    :type maxsplit: None | int
    :return: split line
    :rtype: list

    >>> split_semicolon('a,b;c;;g')
    ['a,b', 'c', '', 'g']

    >>> split_semicolon('a,b;c;;g', 2)
    ['a,b', 'c', ';g']

    >>> split_semicolon(r'a,b;c\;;g', 2)
    ['a,b', 'c;', 'g']
    """
    # Split on ';' character
    split_line = line.split(';')

    split_line_size = len(split_line)

    # if maxsplit is not specified, we set it to the number of part
    if maxsplit is None or maxsplit < 0:
        maxsplit = split_line_size

    # Join parts  to the next one, if ends with a '\'
    # because we mustn't split if the semicolon is escaped
    i = 0
    while i < split_line_size - 1:

        # for each part, check if its ends with a '\'
        ends = split_line[i].endswith('\\')

        if ends:
            # remove the last character '\'
            split_line[i] = split_line[i][:-1]

        # append the next part to the current if it is not the last and the current
        # ends with '\' or if there is more than maxsplit parts
        if (ends or i >= maxsplit) and i < split_line_size - 1:

            split_line[i] = ";".join([split_line[i], split_line[i + 1]])

            # delete the next part
            del split_line[i + 1]
            split_line_size -= 1

        # increase i only if we don't have append because after append the new
        # string can end with '\'
        else:
            i += 1

    return split_line


def jsonify_r(obj):  # pragma: no cover, not for unit tests...
    # pylint: disable=too-many-branches
    """Convert an object into json (recursively on attribute)

    :param obj: obj to jsonify
    :type obj: object
    :return: json representation of obj
    :rtype: dict
    """
    res = {}
    cls = obj.__class__
    if not hasattr(cls, 'properties'):
        try:
            json.dumps(obj)
            return obj
        except TypeError:
            return None
    properties = list(cls.properties.keys())
    if hasattr(cls, 'running_properties'):
        properties += list(cls.running_properties.keys())
    for prop in properties:
        if not hasattr(obj, prop):
            continue
        val = getattr(obj, prop)
        # Maybe the property is not jsonable
        try:
            if isinstance(val, set):
                val = list(val)
            if isinstance(val, list):
                val = sorted(val)
            json.dumps(val)
            res[prop] = val
        except TypeError:
            if isinstance(val, list):
                lst = []
                for subval in val:
                    o_type = getattr(subval.__class__, 'my_type', '')
                    if o_type == 'CommandCall':
                        try:
                            lst.append(subval.call)
                        except AttributeError:  # pragma: no cover, should not happen...
                            pass
                        continue
                    if o_type and hasattr(subval, o_type + '_name'):
                        lst.append(getattr(subval, o_type + '_name'))
                    else:
                        pass
                res[prop] = lst
            else:
                o_type = getattr(val.__class__, 'my_type', '')
                if o_type == 'CommandCall':
                    try:
                        res[prop] = val.call
                    except AttributeError:  # pragma: no cover, should not happen...
                        pass
                    continue
                if o_type and hasattr(val, o_type + '_name'):
                    res[prop] = getattr(val, o_type + '_name')
    return res


# ################################## TIME ##################################
def format_t_into_dhms_format(timestamp):
    """ Convert an amount of second into day, hour, min and sec

    :param timestamp: seconds
    :type timestamp: int
    :return: 'Ad Bh Cm Ds'
    :rtype: str

    >>> format_t_into_dhms_format(456189)
    '5d 6h 43m 9s'

    >>> format_t_into_dhms_format(3600)
    '0d 1h 0m 0s'

    """
    mins, timestamp = divmod(timestamp, 60)
    hour, mins = divmod(mins, 60)
    day, hour = divmod(hour, 24)
    return '%sd %sh %sm %ss' % (day, hour, mins, timestamp)


def merge_periods(data):
    """
    Merge periods to have better continous periods.
    Like 350-450, 400-600 => 350-600

    :param data: list of periods
    :type data: list
    :return: better continous periods
    :rtype: list
    """
    # sort by start date
    newdata = sorted(data, key=lambda drange: drange[0])
    end = 0
    for period in newdata:
        if period[0] != end and period[0] != (end - 1):
            end = period[1]

    # dat = np.array(newdata)
    dat = newdata
    new_intervals = []
    cur_start = None
    cur_end = None
    for (dt_start, dt_end) in dat:
        if cur_end is None:
            cur_start = dt_start
            cur_end = dt_end
            continue
        else:
            if cur_end >= dt_start:
                # merge, keep existing cur_start, extend cur_end
                cur_end = dt_end
            else:
                # new interval, save previous and reset current to this
                new_intervals.append((cur_start, cur_end))
                cur_start = dt_start
                cur_end = dt_end
    # make sure final interval is saved
    new_intervals.append((cur_start, cur_end))
    return new_intervals


# ################################ Pythonization ###########################
def to_int(val):
    """Convert val to int (or raise Exception)

    :param val: value to convert
    :type val:
    :return: int(float(val))
    :rtype: int
    """
    try:
        return int(val)
    except ValueError:
        return int(float(val))


def to_float(val):
    """Convert val to float (or raise Exception)

    :param val: value to convert
    :type val:
    :return: float(val)
    :rtype: float
    """
    return float(val)


def to_char(val):
    """Get first character of val (or raise Exception)

    :param val: value we get head
    :type val:
    :return: val[0]
    :rtype: str
    """
    return val[0]


def to_split(val, split_on_comma=True):
    """Try to split a string with comma separator.
    If val is already a list return it
    If we don't have to split just return [val]
    If split gives only [''] empty it

    :param val: value to split
    :type val:
    :param split_on_comma:
    :type split_on_comma: bool
    :return: split value on comma
    :rtype: list

    >>> to_split('a,b,c')
    ['a', 'b', 'c']

    >>> to_split('a,b,c', False)
    ['a,b,c']

    >>> to_split(['a,b,c'])
    ['a,b,c']

    >>> to_split('')
    []
    """
    if isinstance(val, list):
        return val
    if not split_on_comma:
        return [val]
    val = val.split(',')
    if val == ['']:
        val = []
    return val


def list_split(val, split_on_comma=True):
    """Try to split each member of a list with comma separator.
    If we don't have to split just return val

    :param val: value to split
    :type val:
    :param split_on_comma:
    :type split_on_comma: bool
    :return: list with members split on comma
    :rtype: list

    >>> list_split(['a,b,c'], False)
    ['a,b,c']

    >>> list_split(['a,b,c'])
    ['a', 'b', 'c']

    >>> list_split('')
    []

    """
    if not split_on_comma:
        return val
    new_val = []
    for subval in val:
        # This may happen when re-serializing
        if isinstance(subval, list):
            continue
        new_val.extend(subval.split(','))
    return new_val


def to_best_int_float(val):
    """Get best type for value between int and float

    :param val: value
    :type val:
    :return: int(float(val)) if int(float(val)) == float(val), else float(val)
    :rtype: int | float

    >>> to_best_int_float("20.1")
    20.1

    >>> to_best_int_float("20.0")
    20

    >>> to_best_int_float("20")
    20
    """
    integer = int(float(val))
    flt = float(val)
    # If the f is a .0 value,
    # best match is int
    if integer == flt:
        return integer
    return flt


def to_bool(val):
    """Convert value to bool

    Because bool('0') = true, so...

    :param val: value to convert
    :type val:
    :return: True if val == '1' or val == 'on' or val == 'true' or val == 'True', else False
    :rtype: bool
    """
    return val in ['1', 'on', 'true', 'True']


def from_bool_to_string(boolean):  # pragma: no cover, to be deprecated?
    """Convert a bool to a string representation

    :param boolean: bool to convert
    :type boolean: bool
    :return: if boolean '1' ,else '0'
    :rtype: str
    """
    if boolean:
        return '1'

    return '0'


def from_bool_to_int(boolean):  # pragma: no cover, to be deprecated?
    """Convert a bool to a int representation

    :param boolean: bool to convert
    :type boolean: bool
    :return: if boolean 1 ,else 0
    :rtype: int
    """
    if boolean:
        return 1

    return 0


def from_list_to_split(val):  # pragma: no cover, to be deprecated?
    """Convert list into a comma separated string

    :param val: value to convert
    :type val:
    :return: comma separated string
    :rtype: str
    """
    val = ','.join(['%s' % v for v in val])
    return val


def from_float_to_int(val):  # pragma: no cover, to be deprecated?
    """Convert float to int

    :param val: value to convert
    :type val: float
    :return: int(val)
    :rtype: int
    """
    val = int(val)
    return val


# Functions for brok_transformations
# They take 2 parameters: ref, and a value
# ref is the item like a service, and value
# if the value to preprocess

def brok_last_time(ref, val):
    """Convert float to int

    :param ref: Not used
    :type ref:
    :param val: value to convert
    :type val: float
    :return: int(val)
    :rtype: int
    """
    return int(val)


def to_list_string_of_names(ref, tab):  # pragma: no cover, to be deprecated?
    """Convert list into a comma separated list of element name

    :param ref: Not used
    :type ref:
    :param tab: list to parse
    :type tab: list
    :return: comma separated string of names
    :rtype: str
    """
    return ",".join([e.get_name() for e in tab])


# Functions for retention storage / restoration
def from_set_to_list(ref, tab):
    """Convert set into a list

    Used for the retention store

    :param ref: Not used
    :type ref:
    :param tab: list to parse
    :type tab: list
    :return: list of names
    :rtype: list
    """
    return list(tab)


def from_list_to_set(ref, tab):
    """Convert list to a set

    Used for the retention restore

    :param ref: Not used
    :type ref:
    :param tab: list to parse
    :type tab: list
    :return: list of names
    :rtype: list
    """
    return set(tab)


def to_serialized(ref, the_data):
    """Serialize the property

    Used for the retention store

    :param ref: Not used
    :type ref:
    :param the_data: dictionary to convert
    :type the_data: dict
    :return: serialized data
    :rtype: dict
    """
    if not the_data:
        return {}
    if not getattr(the_data, 'serialize', None):
        return the_data
    return the_data.serialize()


def from_serialized(ref, the_data):
    """Unserialize the element

    Used for the retention store

    :param ref: Not used
    :type ref:
    :param the_data: dictionary to convert
    :type the_data: dict
    :return: serialized data
    :rtype: dict
    """
    if not the_data:
        return {}
    if not getattr(the_data, 'unserialize', None):
        return the_data
    return the_data.unserialize()


def dict_to_serialized_dict(ref, the_dict):
    """Serialize the list of elements to a dictionary

    Used for the retention store

    :param ref: Not used
    :type ref:
    :param the_dict: dictionary to convert
    :type the_dict: dict
    :return: dict of serialized
    :rtype: dict
    """
    result = {}
    for elt in list(the_dict.values()):
        if not getattr(elt, 'serialize', None):
            continue
        result[elt.uuid] = elt.serialize()
    return result


def list_to_serialized(ref, the_list):
    """Serialize the list of elements

    Used for the retention store

    :param ref: Not used
    :type ref:
    :param the_list: dictionary to convert
    :type the_list: dict
    :return: dict of serialized
    :rtype: dict
    """
    result = []
    for elt in the_list:
        if not getattr(elt, 'serialize', None):
            continue
        result.append(elt.serialize())
    return result


def to_name_if_possible(ref, value):  # pragma: no cover, to be deprecated?
    """Try to get value name (call get_name method)

    :param ref: Not used
    :type ref:
    :param value: value to name
    :type value: str
    :return: name or ''
    :rtype: str
    """
    if value:
        return value.get_name()
    return ''


def to_hostnames_list(ref, tab):  # pragma: no cover, to be deprecated?
    """Convert Host list into a list of  host_name

    :param ref: Not used
    :type ref:
    :param tab: Host list
    :type tab: list[alignak.objects.host.Host]
    :return: host_name list
    :rtype: list
    """
    res = []
    for host in tab:
        if hasattr(host, 'host_name'):
            res.append(host.host_name)
    return res


def to_svc_hst_distinct_lists(ref, tab):  # pragma: no cover, to be deprecated?
    """create a dict with 2 lists::

    * services: all services of the tab
    * hosts: all hosts of the tab

    :param ref: Not used
    :type ref:
    :param tab: list of Host and Service
    :type tab: list
    :return: dict with hosts and services names
    :rtype: dict
    """
    res = {'hosts': [], 'services': []}
    for elem in tab:
        cls = elem.__class__
        name = elem.get_full_name()
        if cls.my_type == 'service':
            res['services'].append(name)
        else:
            res['hosts'].append(name)
    return res


def get_obj_name_two_args_and_void(obj, value):
    """Get value name (call get_name) if not a string

    :param obj: Not used
    :type obj: object
    :param value: value to name
    :type value:
    :return: value name
    :rtype: str
    """
    try:
        return value.get_name()
    except AttributeError:
        return ''


def unique_value(val):
    """Get last element of a value if it is a list else returns the value

    Used in parsing, if we set several time a parameter we only take the last one

    :param val: val to edit
    :type val:
    :return: single value
    :rtype: str
    """
    return val if not isinstance(val, list) else val[-1]


# ##################### Sorting ################
def master_then_spare(data):
    """Return the provided satellites list sorted as:
        - alive first,
        - then spare
        - then dead
        satellites.

    :param data: the SatelliteLink list
    :type data: list
    :return: sorted list
    :rtype: list
    """
    master = []
    spare = []
    for sdata in data:
        if sdata.spare:
            spare.append(sdata)
        else:
            master.append(sdata)
    rdata = []
    rdata.extend(master)
    rdata.extend(spare)
    return rdata


def sort_by_number_values(x00, y00):  # pragma: no cover, looks like not used!
    """Compare x00, y00 base on number of values

    :param x00: first elem to compare
    :type x00: list
    :param y00: second elem to compare
    :type y00: list
    :return: x00 > y00 (-1) if len(x00) > len(y00), x00 == y00 (0) if id equals, x00 < y00 (1) else
    :rtype: int
    """
    if len(x00) < len(y00):
        return 1
    if len(x00) > len(y00):
        return -1
    # So is equal
    return 0


# ##################### Statistics ################
def average_percentile(values):
    """
    Get the average, min percentile (5%) and
    max percentile (95%) of a list of values.

    :param values: list of value to compute
    :type values: list
    :return: tuple containing average, min and max value
    :rtype: tuple
    """
    if not values:
        return None, None, None

    value_avg = round(float(sum(values)) / len(values), 2)
    value_max = round(percentile(values, 95), 2)
    value_min = round(percentile(values, 5), 2)
    return value_avg, value_min, value_max


# #################### Cleaning ##############
def strip_and_uniq(tab):
    """Strip every element of a list and keep a list of ordered unique values

    :param tab: list to strip
    :type tab: list
    :return: stripped list with unique values
    :rtype: list
    """
    _list = []
    for elt in tab:
        val = elt.strip()
        if val and val not in _list:
            _list.append(val)
    return _list


# ################### Pattern change application (mainly for host) #######
class KeyValueSyntaxError(ValueError):
    """Syntax error on a duplicate_foreach value"""


KEY_VALUES_REGEX = re.compile(
    '^'
    # should not be necessary, cause what we get is already stripped:
    # r"\s*"
    r'(?P<key>[^$]+?)'   # key, composed of anything but a $, optionally followed by some spaces
    r'\s*'
    r'(?P<values>' +     # optional values, composed of a bare '$(something)$' zero or more times
    (
        r'(?:\$\([^)]+?\)\$\s*)*'
    ) +
    r')\s*'   # followed by optional values, which are composed of ..
    '$'
)

VALUE_REGEX = re.compile(
    r'\$\(([^)]+)\)\$'
)

RANGE_REGEX = re.compile(
    r'^'
    r'(?P<before>[^\[]*)'
    r'(?:\['
    r'(?P<from>\d+)'
    r'-'
    r'(?P<to>\d+)'
    r'(?:/(?P<step>\d+))?'
    r'\])?'
    r'(?P<after>.*)'
    r'$')


def expand_ranges(value):
    """
    :param str value: The value to be "expanded".
    :return: A generator to yield the different resulting values from expanding
             the eventual ranges present in the input value.

    >>> tuple(expand_ranges("Item [1-3] - Bla"))
    ('Item 1 - Bla', 'Item 2 - Bla', 'Item 3 - Bla')
    >>> tuple(expand_ranges("X[1-10/2]Y"))
    ('X1Y', 'X3Y', 'X5Y', 'X7Y', 'X9Y')
    >>> tuple(expand_ranges("[1-6/2] [1-3]"))
    ('1 1', '1 2', '1 3', '3 1', '3 2', '3 3', '5 1', '5 2', '5 3')
    """
    match_dict = RANGE_REGEX.match(value).groupdict()  # the regex is supposed to always match..
    before = match_dict['before']
    after = match_dict['after']
    from_value = match_dict['from']
    if from_value is None:
        yield value
    else:
        # we have a [x-y] range
        from_value = int(from_value)
        to_value = int(match_dict['to']) + 1  # y is inclusive
        step = int(match_dict['step'] or 1)
        for idx in range(from_value, to_value, step):
            # yield "%s%s%s" % (before, idx, after)
            for sub_val in expand_ranges("%s%s%s" % (before, idx, after)):
                yield sub_val


def generate_key_value_sequences(entry, default_value):
    """Parse a key value config entry (used in duplicate foreach)

    If we have a key that look like [X-Y] we will expand it into Y-X+1 keys

    :param str entry: The config line to be parsed.
    :param str default_value: The default value to be used when none is available.
    :return: a generator yielding dicts with 'KEY' & 'VALUE' & 'VALUE1' keys,
             with eventual others 'VALUEx' (x 1 -> N) keys.

    >>> rsp = list(generate_key_value_sequences("var$(/var)$,root $(/)$"))
    >>> import pprint
    >>> pprint.pprint(rsp)
    [{'KEY': 'var', 'VALUE': '/var', 'VALUE1': '/var'},
     {'KEY': 'root', 'VALUE': '/', 'VALUE1': '/'}]
    """
    no_one_yielded = True
    for value in entry.split(','):
        value = value.strip()
        if not value:
            continue
        full_match = KEY_VALUES_REGEX.match(value)
        if full_match is None:
            raise KeyValueSyntaxError("%r is an invalid key(-values) pattern" % value)
        key = full_match.group(1)
        tmp = {'KEY': key}
        values = full_match.group(2)
        if values:  # there is, at least, one value provided
            for idx, value_match in enumerate(VALUE_REGEX.finditer(values), 1):
                tmp['VALUE%s' % idx] = value_match.group(1)
        else:  # no value provided for this key, use the default provided:
            tmp['VALUE1'] = default_value
        tmp['VALUE'] = tmp['VALUE1']  # alias from VALUE -> VALUE1
        for subkey in expand_ranges(key):
            current = tmp.copy()
            current['KEY'] = subkey
            yield current
            no_one_yielded = False
    if no_one_yielded:
        raise KeyValueSyntaxError('At least one key must be present')


# ####################### Services/hosts search filters  #######################
# Filters used in services or hosts find_by_filter method
# Return callback functions which are passed host or service instances, and
# should return a boolean value that indicates if the instance matched the
# filter
def filter_any(ref):
    """Filter for host
    Filter nothing

    :param name: name to filter
    :type name: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(items):
        """Inner filter for host. Accept all"""
        return True

    return inner_filter


def filter_none(ref):
    """Filter for host
    Filter all

    :return: Filter
    :rtype: bool
    """

    def inner_filter(items):
        """Inner filter for host. Accept nothing"""
        return False

    return inner_filter


def filter_host_by_name(name):
    """Filter for host
    Filter on name

    :param name: name to filter
    :type name: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(items):
        """Inner filter for host. Accept if host_name == name"""
        host = items["host"]
        if host is None:
            return False
        return host.host_name == name

    return inner_filter


def filter_host_by_regex(regex):
    """Filter for host
    Filter on regex

    :param regex: regex to filter
    :type regex: str
    :return: Filter
    :rtype: bool
    """
    host_re = re.compile(regex)

    def inner_filter(items):
        """Inner filter for host. Accept if regex match host_name"""
        host = items["host"]
        if host is None:
            return False
        return host_re.match(host.host_name) is not None

    return inner_filter


def filter_host_by_group(group):
    """Filter for host
    Filter on group

    :param group: group name to filter
    :type group: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(items):
        """Inner filter for host. Accept if group in host.hostgroups"""
        host = items["host"]
        if host is None:
            return False
        return group in [items["hostgroups"][g].hostgroup_name for g in host.hostgroups]

    return inner_filter


def filter_host_by_tag(tpl):
    """Filter for host
    Filter on tag

    :param tpl: tag to filter
    :type tpl: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(items):
        """Inner filter for host. Accept if tag in host.tags"""
        host = items["host"]
        if host is None:
            return False
        return tpl in [t.strip() for t in host.tags]

    return inner_filter


def filter_service_by_name(name):
    """Filter for service
    Filter on name

    :param name: name to filter
    :type name: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(items):
        """Inner filter for service. Accept if service_description == name"""
        service = items["service"]
        if service is None:
            return False
        return service.service_description == name

    return inner_filter


def filter_service_by_regex_name(regex):
    """Filter for service
    Filter on regex

    :param regex: regex to filter
    :type regex: str
    :return: Filter
    :rtype: bool
    """
    host_re = re.compile(regex)

    def inner_filter(items):
        """Inner filter for service. Accept if regex match service_description"""
        service = items["service"]
        if service is None:
            return False
        return host_re.match(service.service_description) is not None

    return inner_filter


def filter_service_by_host_name(host_name):
    """Filter for service
    Filter on host_name

    :param host_name: host_name to filter
    :type host_name: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(items):
        """Inner filter for service. Accept if service.host.host_name == host_name"""
        service = items["service"]
        host = items["hosts"][service.host]
        if service is None or host is None:
            return False
        return host.host_name == host_name

    return inner_filter


def filter_service_by_regex_host_name(regex):
    """Filter for service
    Filter on regex host_name

    :param regex: regex to filter
    :type regex: str
    :return: Filter
    :rtype: bool
    """
    host_re = re.compile(regex)

    def inner_filter(items):
        """Inner filter for service. Accept if regex match service.host.host_name"""
        service = items["service"]
        host = items["hosts"][service.host]
        if service is None or host is None:
            return False
        return host_re.match(host.host_name) is not None

    return inner_filter


def filter_service_by_hostgroup_name(group):
    """Filter for service
    Filter on hostgroup

    :param group: hostgroup to filter
    :type group: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(items):
        """Inner filter for service. Accept if hostgroup in service.host.hostgroups"""
        service = items["service"]
        host = items["hosts"][service.host]
        if service is None or host is None:
            return False
        return group in [items["hostgroups"][g].hostgroup_name for g in host.hostgroups]

    return inner_filter


def filter_service_by_host_tag_name(tpl):
    """Filter for service
    Filter on tag

    :param tpl: tag to filter
    :type tpl: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(items):
        """Inner filter for service. Accept if tpl in service.host.tags"""
        service = items["service"]
        host = items["hosts"][service.host]
        if service is None or host is None:
            return False
        return tpl in [t.strip() for t in host.tags]

    return inner_filter


def filter_service_by_servicegroup_name(group):
    """Filter for service
    Filter on group

    :param group: group to filter
    :type group: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(items):
        """Inner filter for service. Accept if group in service.servicegroups"""
        service = items["service"]
        if service is None:
            return False
        return group in [items["servicegroups"][g].servicegroup_name for g in service.servicegroups]

    return inner_filter


def filter_host_by_bp_rule_label(label):
    """Filter for host
    Filter on label

    :param label: label to filter
    :type label: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(items):
        """Inner filter for host. Accept if label in host.labels"""
        host = items["host"]
        if host is None:
            return False
        return label in host.labels

    return inner_filter


def filter_service_by_host_bp_rule_label(label):
    """Filter for service
    Filter on label

    :param label: label to filter
    :type label: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(items):
        """Inner filter for service. Accept if label in service.host.labels"""
        service = items["service"]
        host = items["hosts"][service.host]
        if service is None or host is None:
            return False
        return label in host.labels

    return inner_filter


def filter_service_by_bp_rule_label(label):
    """Filter for service
    Filter on label

    :param label: label to filter
    :type label: str
    :return: Filter
    :rtype: bool
    """
    def inner_filter(items):
        """Inner filter for service. Accept if label in service.labels"""
        service = items["service"]
        if service is None:
            return False
        return label in service.labels

    return inner_filter


def is_complex_expr(expr):
    """Check if expression in complex

    :param expr: expression to parse
    :type expr: str
    :return: True if '(', ')', '&', '|', '!' or '*' are in expr
    :rtype: bool
    """
    for char in '()&|!*':
        if char in expr:
            return True
    return False


# ####################### Command line arguments parsing #######################
def parse_daemon_args(arbiter=False):
    """Generic parsing function for daemons

    All daemons:
        '-n', "--name": Set the name of the daemon to pick in the configuration files.
        This allows an arbiter to find its own configuration in the whole Alignak configuration
        Using this parameter is mandatory for all the daemons except for the arbiter
        (defaults to arbiter-master). If several arbiters are existing in the
        configuration this will allow to determine which one is the master/spare.
        The spare arbiter must be launched with this parameter!

        '-e', '--environment': Alignak environment file - the most important and mandatory
        parameter to define the name of the alignak.ini configuration file

        '-c', '--config': Daemon configuration file (ini file) - deprecated!
        '-d', '--daemon': Run as a daemon
        '-r', '--replace': Replace previous running daemon
        '-f', '--debugfile': File to dump debug logs.

        These parameters allow to override the one defined in the Alignak configuration file:
            '-o', '--host': interface the daemon will listen to
            '-p', '--port': port the daemon will listen to

            '-l', '--log_file': set the daemon log file name
            '-i', '--pid_file': set the daemon pid file name

    Arbiter only:
            "-a", "--arbiter": Monitored configuration file(s),
            (multiple -a can be used, and they will be concatenated to make a global configuration
            file) - Note that this parameter is not necessary anymore
            "-V", "--verify-config": Verify configuration file(s) and exit



    :param arbiter: Do we parse args for arbiter?
    :type arbiter: bool
    :return: args
    """
    parser = argparse.ArgumentParser(description="Alignak daemon launching",
                                     epilog="And that's it!")
    if arbiter:
        parser.add_argument('-a', '--arbiter', action='append',
                            dest='legacy_cfg_files',
                            help='Legacy configuration file(s). '
                                 'This option is still available but is is preferable to declare '
                                 'the Nagios-like objects files in the alignak-configuration '
                                 'section of the environment file specified with the -e option.'
                                 'Multiple -a can be used to include several configuration files.')

        parser.add_argument('-V', '--verify-config', dest='verify_only', action='store_true',
                            help='Verify the configuration file(s) and exit')

        parser.add_argument('-k', '--alignak-name', dest='alignak_name',
                            default='My Alignak',
                            help='Set the name of the Alignak instance. If not set, the arbiter '
                                 'name will be used in place. Note that if an alignak_name '
                                 'variable is defined in the configuration, it will overwrite '
                                 'this parameter. '
                                 'For a spare arbiter, this parameter must contain its name!')
        parser.add_argument('-n', '--name', dest='daemon_name',
                            default='arbiter-master',
                            help='Daemon unique name. Must be unique for the same daemon type.')
    else:
        parser.add_argument('-n', '--name', dest='daemon_name', required=True,
                            help='Daemon unique name. Must be unique for the same daemon type.')

    parser.add_argument('-c', '--config', dest='config_file',
                        help='Daemon configuration file. '
                             'Deprecated parameter, do not use it anymore!')

    parser.add_argument('-d', '--daemon', dest='is_daemon', default=False, action='store_true',
                        help='Run as a daemon. Fork the launched process and daemonize.')

    parser.add_argument('-r', '--replace', dest='do_replace', default=False, action='store_true',
                        help='Replace previous running daemon if any pid file is found.')

    parser.add_argument('-vv', '--debug', dest='debug', default=False, action='store_true',
                        help='Set log level to debug mode (DEBUG)')

    parser.add_argument('-v', '--verbose', dest='verbose', default=False, action='store_true',
                        help='Set log level to verbose mode (INFO)')

    parser.add_argument('-o', '--host', dest='host',
                        help='Host interface used by the daemon. '
                             'Default is 0.0.0.0 (all interfaces).')

    parser.add_argument('-p', '--port', dest='port',
                        help='Port used by the daemon. '
                             'Default is set according to the daemon type.')

    parser.add_argument('-l', '--log_file', dest='log_filename',
                        help='File used for the daemon log. Set as empty to disable log file.')

    parser.add_argument('-i', '--pid_file', dest='pid_filename',
                        help='File used to store the daemon pid')

    parser.add_argument('-e', '--environment', dest='env_file', required=True,
                        default='../../etc/alignak.ini',
                        help='Alignak global environment file. '
                             'This file defines all the daemons of this Alignak '
                             'instance and their configuration. Each daemon configuration '
                             'is defined in a specifc section of this file.')

    # parser.add_argument('env_file',
    #                     help='Alignak global environment file. '
    #                          'This file defines all the daemons of this Alignak '
    #                          'instance and their configuration. Each daemon configuration '
    #                          'is defined in a specifc section of this file.')

    return parser.parse_args()
