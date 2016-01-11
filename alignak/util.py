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
import time
import re
import sys
import os
import json
import numpy as np

from alignak.macroresolver import MacroResolver
from alignak.log import logger

try:
    SAFE_STDOUT = (sys.stdout.encoding == 'UTF-8')
except Exception, exp:
    logger.error('Encoding detection error= %s', exp)
    SAFE_STDOUT = False


# ########## Strings #############
def safe_print(*args):
    """Try to print strings, but if there is an utf8 error, go in simple ascii mode
    (Like if the terminal do not have en_US.UTF8 as LANG for example)

    :param args: args to print
    :type args:
    :return: None
    """
    lst = []
    for arg in args:
        # If we got an str, go in unicode, and if we cannot print
        # utf8, go in ascii mode
        if isinstance(arg, str):
            if SAFE_STDOUT:
                string = unicode(arg, 'utf8', errors='ignore')
            else:
                string = arg.decode('ascii', 'replace').encode('ascii', 'replace').\
                    decode('ascii', 'replace')
            lst.append(string)
        # Same for unicode, but skip the unicode pass
        elif isinstance(arg, unicode):
            if SAFE_STDOUT:
                string = arg
            else:
                string = arg.encode('ascii', 'replace')
            lst.append(string)
        # Other types can be directly convert in unicode
        else:
            lst.append(unicode(arg))
    # Ok, now print it :)
    print u' '.join(lst)


def split_semicolon(line, maxsplit=None):
    r"""Split a line on semicolons characters but not on the escaped semicolons

    :param line: line to split
    :type line: str
    :param maxsplit: maximum of split to dot
    :type maxsplitL int
    :return: splitted line
    :rtype: list

    >>> split_semicolon('a,b;c;;g')
    ['a,b', 'c', '', 'g']

    >>> split_semicolon('a,b;c;;g', 2)
    ['a,b', 'c', ';g']

    >>> split_semicolon(r'a,b;c\;;g', 2)
    ['a,b', 'c;', 'g']
    """
    # Split on ';' character
    splitted_line = line.split(';')

    splitted_line_size = len(splitted_line)

    # if maxsplit is not specified, we set it to the number of part
    if maxsplit is None or 0 > maxsplit:
        maxsplit = splitted_line_size

    # Join parts  to the next one, if ends with a '\'
    # because we mustn't split if the semicolon is escaped
    i = 0
    while i < splitted_line_size - 1:

        # for each part, check if its ends with a '\'
        ends = splitted_line[i].endswith('\\')

        if ends:
            # remove the last character '\'
            splitted_line[i] = splitted_line[i][:-1]

        # append the next part to the current if it is not the last and the current
        # ends with '\' or if there is more than maxsplit parts
        if (ends or i >= maxsplit) and i < splitted_line_size - 1:

            splitted_line[i] = ";".join([splitted_line[i], splitted_line[i + 1]])

            # delete the next part
            del splitted_line[i + 1]
            splitted_line_size -= 1

        # increase i only if we don't have append because after append the new
        # string can end with '\'
        else:
            i += 1

    return splitted_line


def jsonify_r(obj):
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
        except Exception, exp:
            return None
    properties = cls.properties.keys()
    if hasattr(cls, 'running_properties'):
        properties += cls.running_properties.keys()
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
        except Exception, exp:
            if isinstance(val, list):
                lst = []
                for subval in val:
                    o_type = getattr(subval.__class__, 'my_type', '')
                    if o_type == 'CommandCall':
                        try:
                            lst.append(subval.call)
                        except Exception:
                            pass
                        continue
                    if o_type and hasattr(subval, o_type + '_name'):
                        lst.append(getattr(subval, o_type + '_name'))
                    else:
                        pass
                        # print "CANNOT MANAGE OBJECT", _t, type(_t), t
                res[prop] = lst
            else:
                o_type = getattr(val.__class__, 'my_type', '')
                if o_type == 'CommandCall':
                    try:
                        res[prop] = val.call
                    except Exception:
                        pass
                    continue
                if o_type and hasattr(val, o_type + '_name'):
                    res[prop] = getattr(val, o_type + '_name')
                # else:
                #    print "CANNOT MANAGE OBJECT", v, type(v), t
    return res

# ################################## TIME ##################################


def get_end_of_day(year, month_id, day):
    """Get the timestamp of the end (local) of a specific day

    :param year: date year
    :type year: int
    :param month_id: date month (int)
    :type month_id: int
    :param day: date day
    :type day: int
    :return: timestamp
    :rtype: int

    TODO: Missing timezone
    """
    end_time = (year, month_id, day, 23, 59, 59, 0, 0, -1)
    end_time_epoch = time.mktime(end_time)
    return end_time_epoch


def print_date(timestamp):
    """Get date (local) in asc format from timestamp

    example : 'Thu Jan  1 01:00:00 1970' (for timestamp=0 in a EUW server)

    :param timestamp: timestamp
    :type timestamp; int
    :return: formatted time
    :rtype: int
    TODO: Missing timezone
    """
    return time.asctime(time.localtime(timestamp))


def get_day(timestamp):
    """Get timestamp of the beginning of the day (local) given by timestamp

    :param timestamp: time to get day from
    :type timestamp: int
    :return: timestamp
    :rtype: int
    TODO: Missing timezone
    """
    return int(timestamp - get_sec_from_morning(timestamp))


def get_wday(timestamp):
    """Get week day from date

    :param timestamp: timestamp date
    :type timestamp: int
    :return: weekday (0-6)
    :rtype: int
    TODO: Missing timezone
    """
    t_lt = time.localtime(timestamp)
    return t_lt.tm_wday


def get_sec_from_morning(timestamp):
    """Get the numbers of seconds elapsed since the beginning of the day (local) given by timestamp

    :param timestamp: time to get amount of second from
    :type timestamp: int
    :return: timestamp
    :rtype: int
    TODO: Missing timezone
    """
    t_lt = time.localtime(timestamp)
    return t_lt.tm_hour * 3600 + t_lt.tm_min * 60 + t_lt.tm_sec


def get_start_of_day(year, month_id, day):
    """Get the timestamp of the beginning (local) of a specific day

    :param year: date year
    :type year: int
    :param month_id: date month (int)
    :type month_id: int
    :param day: date day
    :type day: int
    :return: timestamp
    :rtype: float

    TODO: Missing timezone
    """
    start_time = (year, month_id, day, 00, 00, 00, 0, 0, -1)
    try:
        start_time_epoch = time.mktime(start_time)
    except OverflowError:
        # Windows mktime sometimes crashes on (1970, 1, 1, ...)
        start_time_epoch = 0.0

    return start_time_epoch


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


# ################################ Pythonization ###########################
def to_int(val):
    """Convert val to int (or raise Exception)

    :param val: value to convert
    :type val:
    :return: int(float(val))
    :rtype: int
    """
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


def to_split(val, split_on_coma=True):
    """Try to split a string with comma separator.
    If val is already a list return it
    If we don't have to split just return [val]
    If split gives only [''] empty it

    :param val: value to split
    :type val:
    :param split_on_coma:
    :type split_on_coma: bool
    :return: splitted value on comma
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
    if not split_on_coma:
        return [val]
    val = val.split(',')
    if val == ['']:
        val = []
    return val


def list_split(val, split_on_coma=True):
    """Try to split a each member of a list with comma separator.
    If we don't have to split just return val

    :param val: value to split
    :type val:
    :param split_on_coma:
    :type split_on_coma: bool
    :return: list with splitted member on comma
    :rtype: list

    >>> list_split(['a,b,c'], False)
    ['a,b,c']

    >>> list_split(['a,b,c'])
    ['a', 'b', 'c']

    >>> list_split('')
    []

    """
    if not split_on_coma:
        return val
    new_val = []
    for subval in val:
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


# bool('0') = true, so...
def to_bool(val):
    """Convert value to bool

    :param val: value to convert
    :type val:
    :return: True if val == '1' or val == 'on' or val == 'true' or val == 'True', else False
    :rtype: bool
    """
    if val == '1' or val == 'on' or val == 'true' or val == 'True':
        return True
    else:
        return False


def from_bool_to_string(boolean):
    """Convert a bool to a string representation

    :param boolean: bool to convert
    :type boolean: bool
    :return: if boolean '1' ,else '0'
    :rtype: str
    """
    if boolean:
        return '1'
    else:
        return '0'


def from_bool_to_int(boolean):
    """Convert a bool to a int representation

    :param boolean: bool to convert
    :type boolean: bool
    :return: if boolean 1 ,else 0
    :rtype: int
    """
    if boolean:
        return 1
    else:
        return 0


def from_list_to_split(val):
    """Convert list into a comma separated string

    :param val: value to convert
    :type val:
    :return: comma separated string
    :rtype: str
    """
    val = ','.join(['%s' % v for v in val])
    return val


def from_float_to_int(val):
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

def to_list_string_of_names(ref, tab):
    """Convert list into a comma separated list of element name

    :param ref: Not used
    :type ref:
    :param tab: list to parse
    :type tab: list
    :return: comma separated string of names
    :rtype: str
    """
    return ",".join([e.get_name() for e in tab])


def to_list_of_names(ref, tab):
    """Convert list into a list of element name

    :param ref: Not used
    :type ref:
    :param tab: list to parse
    :type tab: list
    :return: list of names
    :rtype: list
    """
    return [e.get_name() for e in tab]


def to_name_if_possible(ref, value):
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


def to_hostnames_list(ref, tab):
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


def to_svc_hst_distinct_lists(ref, tab):
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


def expand_with_macros(ref, value):
    """Expand the value with macros from the
       host/service ref before brok it

    :param ref: host or service
    :type ref:
    :param value: value to expand macro
    :type value:
    :return: value with macro replaced
    :rtype:
    """
    return MacroResolver().resolve_simple_macros_in_string(value, ref.get_data_for_checks())


def get_obj_name(obj):
    """Get object name (call get_name) if not a string

    :param obj: obj we wan the name
    :type obj: object
    :return: object name
    :rtype: str
    """
    # Maybe we do not have a real object but already a string. If so
    # return the string
    if isinstance(obj, basestring):
        return obj
    return obj.get_name()


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


def get_obj_full_name(obj):
    """Wrapepr to call obj.get_full_name or obj.get_name

    :param obj: object name
    :type obj: object
    :return: object name
    :rtype: str
    """
    try:
        return obj.get_full_name()
    except Exception:
        return obj.get_name()


def get_customs_keys(dic):
    """Get a list of keys of the custom dict
    without the first char

    Used for macros (_name key)

    :param dic: dict to parse
    :type dic: dict
    :return: list of keys
    :rtype: list
    """
    return [k[1:] for k in dic.keys()]


def get_customs_values(dic):
    """Wrapper for values() method

    :param dic: dict
    :type dic: dict
    :return: dic.values
    :rtype:
    TODO: Remove it?
    """
    return dic.values()


def unique_value(val):
    """Get last elem of val if it is a list
    Else return val
    Used in parsing, if we set several time a parameter we only take the last one

    :param val: val to edit
    :type val:
    :return: single value
    :rtype: str
    TODO: Raise erro/warning instead of silently removing something
    """
    if isinstance(val, list):
        if val:
            return val[-1]
        else:
            return ''
    else:
        return val


# ##################### Sorting ################
def scheduler_no_spare_first(x00, y00):
    """Compare two satellite link based on spare attribute(scheduler usually)

    :param x00: first link to compare
    :type x00:
    :param y00: second link to compare
    :type y00:
    :return: x00 > y00 (1) if x00.spare and not y00.spare,
             x00 == y00 (0) if both spare,
             x00 < y00 (-1) else
    :rtype: int
    """
    if x00.spare and not y00.spare:
        return 1
    elif x00.spare and y00.spare:
        return 0
    else:
        return -1


def alive_then_spare_then_deads(sat1, sat2):
    """Compare two satellite link
    based on alive attribute then spare attribute

    :param sat1: first link to compare
    :type sat1:
    :param sat2: second link to compare
    :type sat2:
    :return: sat1 > sat2 (1) if sat1 alive and not sat2 or both alive but sat1 not spare
             sat1 == sat2 (0) if both alive and spare
             sat1 < sat2 (-1) else
    :rtype: int
    """
    if sat1.alive == sat2.alive and sat1.spare == sat2.spare:
        return 0
    if not sat2.alive or (sat2.alive and sat2.spare and sat1.alive):
        return -1
    return 1


def sort_by_ids(x00, y00):
    """Compare x00, y00 base on their id

    :param x00: first elem to compare
    :type x00: int
    :param y00: second elem to compare
    :type y00: int
    :return: x00 > y00 (1) if x00._id > y00._id, x00 == y00 (0) if id equals, x00 < y00 (-1) else
    :rtype: int
    """
    if x00._id < y00._id:
        return -1
    if x00._id > y00._id:
        return 1
    # So is equal
    return 0


def average_percentile(values):
    """
    Get the average, min percentile (5%) and
    max percentile (95%) of a list of values.

    :param values: list of value to compute
    :type values: list
    :return: tuple containing average, min and max value
    :rtype: tuple
    """
    length = len(values)

    if length == 0:
        return None, None, None

    value_avg = round(float(sum(values)) / length, 1)
    # pylint: disable=E1101
    value_max = round(np.percentile(values, 95), 1)
    value_min = round(np.percentile(values, 5), 1)
    return value_avg, value_min, value_max


# #################### Cleaning ##############
def strip_and_uniq(tab):
    """Strip every element of a list and keep unique values

    :param tab: list to strip
    :type tab: list
    :return: stripped list with unique values
    :rtype: list
    """
    new_tab = set()
    for elt in tab:
        val = elt.strip()
        if val != '':
            new_tab.add(val)
    return list(new_tab)


# ################### Pattern change application (mainly for host) #######

class KeyValueSyntaxError(ValueError):
    """Syntax error on a duplicate_foreach value"""

KEY_VALUES_REGEX = re.compile(
    '^'
    # should not be necessary, cause what we get is already stripped:
    # r"\s*"
    r'(?P<key>[^$]+?)'   # key, composed of anything but a $, optionally followed by some spaces
    r'\s*'
    r'(?P<values>'       # optional values, composed of a bare '$(something)$' zero or more times
    + (
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


# ############################## Files management #######################

def expect_file_dirs(root, path):
    """We got a file like /tmp/toto/toto2/bob.png And we want to be sure the dir
    /tmp/toto/toto2/ will really exists so we can copy it. Try to make if  needed

    :param root: root directory
    :type root: str
    :param path: path to verify
    :type path: str
    :return: True on success, False otherwise
    :rtype: bool
    """
    dirs = os.path.normpath(path).split('/')
    dirs = [d for d in dirs if d != '']
    # We will create all directory until the last one
    # so we are doing a mkdir -p .....
    # TODO: and windows????
    tmp_dir = root
    for directory in dirs:
        path = os.path.join(tmp_dir, directory)
        logger.info('Verify the existence of file %s', path)
        if not os.path.exists(path):
            try:
                os.mkdir(path)
            except Exception:
                return False
        tmp_dir = path
    return True


# ####################### Services/hosts search filters  #######################
# Filters used in services or hosts find_by_filter method
# Return callback functions which are passed host or service instances, and
# should return a boolean value that indicates if the inscance mached the
# filter
def filter_any(name):
    """Filter for host
    Filter nothing

    :param name: name to filter
    :type name: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(host):
        """Inner filter for host. Accept all"""
        return True

    return inner_filter


def filter_none(name):
    """Filter for host
    Filter all

    :param name: name to filter
    :type name: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(host):
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

    def inner_filter(host):
        """Inner filter for host. Accept if host_name == name"""
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

    def inner_filter(host):
        """Inner filter for host. Accept if regex match host_name"""
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

    def inner_filter(host):
        """Inner filter for host. Accept if group in host.hostgroups"""
        if host is None:
            return False
        return group in [g.hostgroup_name for g in host.hostgroups]

    return inner_filter


def filter_host_by_tag(tpl):
    """Filter for host
    Filter on tag

    :param tpl: tag to filter
    :type tpl: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(host):
        """Inner filter for host. Accept if tag in host.tags"""
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

    def inner_filter(service):
        """Inner filter for service. Accept if service_description == name"""
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

    def inner_filter(service):
        """Inner filter for service. Accept if regex match service_description"""
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

    def inner_filter(service):
        """Inner filter for service. Accept if service.host.host_name == host_name"""
        if service is None or service.host is None:
            return False
        return service.host.host_name == host_name

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

    def inner_filter(service):
        """Inner filter for service. Accept if regex match service.host.host_name"""
        if service is None or service.host is None:
            return False
        return host_re.match(service.host.host_name) is not None

    return inner_filter


def filter_service_by_hostgroup_name(group):
    """Filter for service
    Filter on hostgroup

    :param group: hostgroup to filter
    :type group: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(service):
        """Inner filter for service. Accept if hostgroup in service.host.hostgroups"""
        if service is None or service.host is None:
            return False
        return group in [g.hostgroup_name for g in service.host.hostgroups]

    return inner_filter


def filter_service_by_host_tag_name(tpl):
    """Filter for service
    Filter on tag

    :param tpl: tag to filter
    :type tpl: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(service):
        """Inner filter for service. Accept if tpl in service.host.tags"""
        if service is None or service.host is None:
            return False
        return tpl in [t.strip() for t in service.host.tags]

    return inner_filter


def filter_service_by_servicegroup_name(group):
    """Filter for service
    Filter on group

    :param group: group to filter
    :type group: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(service):
        """Inner filter for service. Accept if group in service.servicegroups"""
        if service is None:
            return False
        return group in [g.servicegroup_name for g in service.servicegroups]

    return inner_filter


def filter_host_by_bp_rule_label(label):
    """Filter for host
    Filter on label

    :param label: label to filter
    :type label: str
    :return: Filter
    :rtype: bool
    """

    def inner_filter(host):
        """Inner filter for host. Accept if label in host.labels"""
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

    def inner_filter(service):
        """Inner filter for service. Accept if label in service.host.labels"""
        if service is None or service.host is None:
            return False
        return label in service.host.labels

    return inner_filter


def filter_service_by_bp_rule_label(label):
    """Filter for service
    Filter on label

    :param label: label to filter
    :type label: str
    :return: Filter
    :rtype: bool
    """
    def inner_filter(service):
        """Inner filter for service. Accept if label in service.labels"""
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
