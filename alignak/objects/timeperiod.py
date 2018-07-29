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
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Dessai.Imrane, dessai.imrane@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Guillaume Bour, guillaume@bour.cc
#     aviau, alexandre.viau@savoirfairelinux.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Olivier Hanesse, olivier.hanesse@gmail.com
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

# Calendar date
# -------------
#  '(\d{4})-(\d{2})-(\d{2}) - (\d{4})-(\d{2})-(\d{2}) / (\d+) ([0-9:, -]+)'
#   => len = 8  => CALENDAR_DATE
#
#  '(\d{4})-(\d{2})-(\d{2}) / (\d+) ([0-9:, -]+)'
#   => len = 5 => CALENDAR_DATE
#
#  '(\d{4})-(\d{2})-(\d{2}) - (\d{4})-(\d{2})-(\d{2}) ([0-9:, -]+)'
#   => len = 7 => CALENDAR_DATE
#
#  '(\d{4})-(\d{2})-(\d{2}) ([0-9:, -]+)'
#   => len = 4 => CALENDAR_DATE
#
# Month week day
# --------------
#  '([a-z]*) (\d+) ([a-z]*) - ([a-z]*) (\d+) ([a-z]*) / (\d+) ([0-9:, -]+)'
#  => len = 8 => MONTH WEEK DAY
#  e.g.: wednesday 1 january - thursday 2 july / 3
#
#  '([a-z]*) (\d+) - ([a-z]*) (\d+) / (\d+) ([0-9:, -]+)' => len = 6
#  e.g.: february 1 - march 15 / 3 => MONTH DATE
#  e.g.: monday 2 - thursday 3 / 2 => WEEK DAY
#  e.g.: day 2 - day 6 / 3 => MONTH DAY
#
#  '([a-z]*) (\d+) - (\d+) / (\d+) ([0-9:, -]+)' => len = 6
#  e.g.: february 1 - 15 / 3 => MONTH DATE
#  e.g.: thursday 2 - 4 => WEEK DAY
#  e.g.: day 1 - 4 => MONTH DAY
#
#  '([a-z]*) (\d+) ([a-z]*) - ([a-z]*) (\d+) ([a-z]*) ([0-9:, -]+)' => len = 7
#  e.g.: wednesday 1 january - thursday 2 july => MONTH WEEK DAY
#
#  '([a-z]*) (\d+) - (\d+) ([0-9:, -]+)' => len = 7
#  e.g.: thursday 2 - 4 => WEEK DAY
#  e.g.: february 1 - 15 / 3 => MONTH DATE
#  e.g.: day 1 - 4 => MONTH DAY
#
#  '([a-z]*) (\d+) - ([a-z]*) (\d+) ([0-9:, -]+)' => len = 5
#  e.g.: february 1 - march 15  => MONTH DATE
#  e.g.: monday 2 - thursday 3  => WEEK DAY
#  e.g.: day 2 - day 6  => MONTH DAY
#
#  '([a-z]*) (\d+) ([0-9:, -]+)' => len = 3
#  e.g.: february 3 => MONTH DATE
#  e.g.: thursday 2 => WEEK DAY
#  e.g.: day 3 => MONTH DAY
#
#  '([a-z]*) (\d+) ([a-z]*) ([0-9:, -]+)' => len = 4
#  e.g.: thursday 3 february => MONTH WEEK DAY
#
#  '([a-z]*) ([0-9:, -]+)' => len = 6
#  e.g.: thursday => normal values
#
# Types: CALENDAR_DATE
#        MONTH WEEK DAY
#        WEEK DAY
#        MONTH DATE
#        MONTH DAY
#

"""
This module provide Timeperiod class used to define time periods to do
action or not if we are in right period
"""

import logging
import time
import re

from alignak.objects.item import Item, Items

from alignak.daterange import Daterange, CalendarDaterange
from alignak.daterange import StandardDaterange, MonthWeekDayDaterange
from alignak.daterange import MonthDateDaterange, WeekDayDaterange
from alignak.daterange import MonthDayDaterange
from alignak.property import IntegerProp, StringProp, ListProp, BoolProp
from alignak.log import make_monitoring_log
from alignak.misc.serialization import get_alignak_class
from alignak.util import merge_periods

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Timeperiod(Item):
    """
    Class to manage a timeperiod
    A timeperiod is defined with range time (hours) of week to do action
    and add day exceptions (like non working days)
    """
    my_type = 'timeperiod'

    properties = Item.properties.copy()
    properties.update({
        'timeperiod_name':
            StringProp(fill_brok=['full_status']),
        'alias':
            StringProp(default=u'', fill_brok=['full_status']),
        'use':
            ListProp(default=[]),
        'register':
            IntegerProp(default=1),

        # These are needed if a broker module calls methods on timeperiod objects
        'dateranges':
            ListProp(default=[], fill_brok=['full_status']),
        'exclude':
            ListProp(default=[], fill_brok=['full_status']),
        'unresolved':
            ListProp(default=[], fill_brok=['full_status']),
        'invalid_entries':
            ListProp(default=[], fill_brok=['full_status']),
        'is_active':
            BoolProp(default=False),
        'activated_once':
            BoolProp(default=False),
    })
    running_properties = Item.running_properties.copy()

    def __init__(self, params=None, parsing=True):

        if params is None:
            params = {}

        # Get standard params
        standard_params = dict(
            [(k, v) for k, v in list(params.items()) if k in self.__class__.properties])
        # Get timeperiod params (monday, tuesday, ...)
        timeperiod_params = dict([(k, v) for k, v in list(params.items())
                                  if k not in self.__class__.properties])

        if 'dateranges' in standard_params and isinstance(standard_params['dateranges'], list) \
                and standard_params['dateranges'] \
                and isinstance(standard_params['dateranges'][0], dict):
            new_list = []
            for elem in standard_params['dateranges']:
                cls = get_alignak_class(elem['__sys_python_module__'])
                if cls:
                    new_list.append(cls(elem['content']))
            # We recreate the object
            self.dateranges = new_list
            # And remove prop, to prevent from being overridden
            del standard_params['dateranges']
        # Handle standard params
        super(Timeperiod, self).__init__(params=standard_params, parsing=parsing)
        self.cache = {}  # For tuning purpose only
        self.invalid_cache = {}  # same but for invalid search

        # We use the uuid presence to assume we are reserializing
        if 'uuid' in params:
            self.uuid = params['uuid']
        else:
            # Initial creation here, uuid already created in super
            self.unresolved = []
            self.dateranges = []
            self.exclude = []
            self.invalid_entries = []
            self.is_active = False
            self.activated_once = False

            # Handle timeperiod params
            for key, value in list(timeperiod_params.items()):
                if isinstance(value, list):
                    if value:
                        value = value[-1]
                    else:
                        value = ''
                self.unresolved.append(key + ' ' + value)

    def serialize(self):
        """This function serialize into a simple dict object.
        It is used when transferring data to other daemons over the network (http)

        Here we directly return all attributes

        :return: json representation of a Timeperiod
        :rtype: dict
        """
        res = super(Timeperiod, self).serialize()

        res['dateranges'] = []
        for elem in self.dateranges:
            res['dateranges'].append({'__sys_python_module__': "%s.%s" % (elem.__module__,
                                                                          elem.__class__.__name__),
                                      'content': elem.serialize()})

        return res

    def get_name(self):
        """
        Get the name of the timeperiod

        :return: the timeperiod name string
        :rtype: str
        """
        return getattr(self, 'timeperiod_name', 'unknown_timeperiod')

    def get_raw_import_values(self):  # pragma: no cover, deprecation
        """
        Get some properties of timeperiod (timeperiod is a bit different
        from classic item)

        TODO: never called anywhere, still useful?

        :return: a dictionnary of some properties
        :rtype: dict
        """
        properties = ['timeperiod_name', 'alias', 'use', 'register']
        res = {}
        for prop in properties:
            if hasattr(self, prop):
                val = getattr(self, prop)
                res[prop] = val
        # Now the unresolved one. The only way to get ride of same key things is to put
        # directly the full value as the key
        for other in self.unresolved:
            res[other] = ''
        return res

    def is_time_valid(self, timestamp):
        """
        Check if a time is valid or not

        :return: time is valid or not
        :rtype: bool
        """
        if hasattr(self, 'exclude'):
            for daterange in self.exclude:
                if daterange.is_time_valid(timestamp):
                    return False
        for daterange in self.dateranges:
            if daterange.is_time_valid(timestamp):
                return True
        return False

    # will give the first time > t which is valid
    def get_min_from_t(self, timestamp):
        """
        Get the first time > timestamp which is valid

        :param timestamp: number of seconds
        :type timestamp: int
        :return: number of seconds
        :rtype: int
        TODO: not used, so delete it
        """
        mins_incl = []
        for daterange in self.dateranges:
            mins_incl.append(daterange.get_min_from_t(timestamp))
        return min(mins_incl)

    # will give the first time > t which is not valid
    def get_not_in_min_from_t(self, first):
        """

        :return: None
        TODO: not used, so delete it
        """
        pass

    def find_next_valid_time_from_cache(self, timestamp):
        """
        Get the next valid time from cache

        :param timestamp: number of seconds
        :type timestamp: int
        :return: Nothing or time in seconds
        :rtype: None or int
        """
        try:
            return self.cache[timestamp]
        except KeyError:
            return None

    def find_next_invalid_time_from_cache(self, timestamp):
        """
        Get the next invalid time from cache

        :param timestamp: number of seconds
        :type timestamp: int
        :return: Nothing or time in seconds
        :rtype: None or int
        """
        try:
            return self.invalid_cache[timestamp]
        except KeyError:
            return None

    def check_and_log_activation_change(self):
        """
        Will look for active/un-active change of timeperiod.
        In case it change, we log it like:
        [1327392000] TIMEPERIOD TRANSITION: <name>;<from>;<to>

        States of is_active:
        -1: default value when start
        0: when timeperiod end
        1: when timeperiod start

        :return: None or a brok if TP changed
        """
        now = int(time.time())

        was_active = self.is_active
        self.is_active = self.is_time_valid(now)

        # If we got a change, log it!
        if self.is_active != was_active:
            _from = 0
            _to = 0
            # If it's the start, get a special value for was
            if not self.activated_once:
                _from = -1
                self.activated_once = True
            if was_active:
                _from = 1
            if self.is_active:
                _to = 1

            # Now raise the log
            brok = make_monitoring_log(
                'info', 'TIMEPERIOD TRANSITION: %s;%d;%d' % (self.get_name(), _from, _to)
            )
            return brok
        return None

    def clean_cache(self):
        """
        Clean cache with entries older than now because not used in future ;)

        :return: None
        """
        now = int(time.time())
        t_to_del = []
        for timestamp in self.cache:
            if timestamp < now:
                t_to_del.append(timestamp)
        for timestamp in t_to_del:
            del self.cache[timestamp]

        # same for the invalid cache
        t_to_del = []
        for timestamp in self.invalid_cache:
            if timestamp < now:
                t_to_del.append(timestamp)
        for timestamp in t_to_del:
            del self.invalid_cache[timestamp]

    def get_next_valid_time_from_t(self, timestamp):
        # pylint: disable=too-many-branches
        """
        Get next valid time. If it's in cache, get it, otherwise define it.
        The limit to find it is 1 year.

        :param timestamp: number of seconds
        :type timestamp: int or float
        :return: Nothing or time in seconds
        :rtype: None or int
        """
        timestamp = int(timestamp)
        original_t = timestamp

        res_from_cache = self.find_next_valid_time_from_cache(timestamp)
        if res_from_cache is not None:
            return res_from_cache

        still_loop = True

        # Loop for all minutes...
        while still_loop:
            local_min = None

            # Ok, not in cache...
            dr_mins = []

            for daterange in self.dateranges:
                dr_mins.append(daterange.get_next_valid_time_from_t(timestamp))

            s_dr_mins = sorted([d for d in dr_mins if d is not None])

            for t01 in s_dr_mins:
                if not self.exclude and still_loop:
                    # No Exclude so we are good
                    local_min = t01
                    still_loop = False
                else:
                    for timeperiod in self.exclude:
                        if not timeperiod.is_time_valid(t01) and still_loop:
                            # OK we found a date that is not valid in any exclude timeperiod
                            local_min = t01
                            still_loop = False

            if local_min is None:
                # Looking for next invalid date
                exc_mins = []
                if s_dr_mins != []:
                    for timeperiod in self.exclude:
                        exc_mins.append(timeperiod.get_next_invalid_time_from_t(s_dr_mins[0]))

                s_exc_mins = sorted([d for d in exc_mins if d is not None])

                if s_exc_mins != []:
                    local_min = s_exc_mins[0]

            if local_min is None:
                still_loop = False
            else:
                timestamp = local_min
                # No loop more than one year
                if timestamp > original_t + 3600 * 24 * 366 + 1:
                    still_loop = False
                    local_min = None

        # Ok, we update the cache...
        self.cache[original_t] = local_min
        return local_min

    def get_next_invalid_time_from_t(self, timestamp):
        # pylint: disable=too-many-branches
        """
        Get the next invalid time

        :param timestamp: timestamp in seconds (of course)
        :type timestamp: int or float
        :return: timestamp of next invalid time
        :rtype: int or float
        """
        timestamp = int(timestamp)
        original_t = timestamp

        dr_mins = []
        for daterange in self.dateranges:
            timestamp = original_t
            cont = True
            while cont:
                start = daterange.get_next_valid_time_from_t(timestamp)
                if start is not None:
                    end = daterange.get_next_invalid_time_from_t(start)
                    dr_mins.append((start, end))
                    timestamp = end
                else:
                    cont = False
                if timestamp > original_t + (3600 * 24 * 365):
                    cont = False
        periods = merge_periods(dr_mins)

        # manage exclude periods
        dr_mins = []
        for exclude in self.exclude:
            for daterange in exclude.dateranges:
                timestamp = original_t
                cont = True
                while cont:
                    start = daterange.get_next_valid_time_from_t(timestamp)
                    if start is not None:
                        end = daterange.get_next_invalid_time_from_t(start)
                        dr_mins.append((start, end))
                        timestamp = end
                    else:
                        cont = False
                    if timestamp > original_t + (3600 * 24 * 365):
                        cont = False
        if not dr_mins:
            periods_exclude = []
        else:
            periods_exclude = merge_periods(dr_mins)

        if len(periods) >= 1:
            # if first valid period is after original timestamp, the first invalid time
            # is the original timestamp
            if periods[0][0] > original_t:
                return original_t
            # check the first period + first period of exclude
            if len(periods_exclude) >= 1:
                if periods_exclude[0][0] < periods[0][1]:
                    return periods_exclude[0][0]
            return periods[0][1]
        return original_t

    def is_correct(self):
        """Check if this object configuration is correct ::

        * Check if dateranges of timeperiod are valid
        * Call our parent class is_correct checker

        :return: True if the configuration is correct, otherwise False if at least one daterange
        is not correct
        :rtype: bool
        """
        state = True
        for daterange in self.dateranges:
            good = daterange.is_correct()
            if not good:
                self.add_error("[timeperiod::%s] invalid daterange '%s'"
                               % (self.get_name(), daterange))
            state &= good

        # Warn about non correct entries
        for entry in self.invalid_entries:
            self.add_error("[timeperiod::%s] invalid entry '%s'" % (self.get_name(), entry))

        return super(Timeperiod, self).is_correct() and state

    def __str__(self):  # pragma: no cover
        """
        Get readable object

        :return: this object in readable format
        :rtype: str
        """
        string = ''
        string += str(self.__dict__) + '\n'
        for elt in self.dateranges:
            string += str(elt)
            (start, end) = elt.get_start_and_end_time()
            start = time.asctime(time.localtime(start))
            end = time.asctime(time.localtime(end))
            string += "\nStart and end:" + str((start, end))
        string += '\nExclude'
        for elt in self.exclude:
            string += str(elt)

        return string

    def resolve_daterange(self, dateranges, entry):
        # pylint: disable=too-many-return-statements,too-many-statements,
        # pylint: disable=too-many-branches,too-many-locals
        """
        Try to solve dateranges (special cases)

        :param dateranges: dateranges
        :type dateranges: list
        :param entry: property of timeperiod
        :type entry: string
        :return: None
        """
        res = re.search(
            r'(\d{4})-(\d{2})-(\d{2}) - (\d{4})-(\d{2})-(\d{2}) / (\d+)[\s\t]*([0-9:, -]+)', entry
        )
        if res is not None:
            (syear, smon, smday, eyear, emon, emday, skip_interval, other) = res.groups()
            data = {'syear': syear, 'smon': smon, 'smday': smday, 'swday': 0,
                    'swday_offset': 0, 'eyear': eyear, 'emon': emon, 'emday': emday,
                    'ewday': 0, 'ewday_offset': 0, 'skip_interval': skip_interval,
                    'other': other}
            dateranges.append(CalendarDaterange(data))
            return

        res = re.search(r'(\d{4})-(\d{2})-(\d{2}) / (\d+)[\s\t]*([0-9:, -]+)', entry)
        if res is not None:
            (syear, smon, smday, skip_interval, other) = res.groups()
            eyear = syear
            emon = smon
            emday = smday
            data = {'syear': syear, 'smon': smon, 'smday': smday, 'swday': 0,
                    'swday_offset': 0, 'eyear': eyear, 'emon': emon, 'emday': emday,
                    'ewday': 0, 'ewday_offset': 0, 'skip_interval': skip_interval,
                    'other': other}
            dateranges.append(CalendarDaterange(data))
            return

        res = re.search(
            r'(\d{4})-(\d{2})-(\d{2}) - (\d{4})-(\d{2})-(\d{2})[\s\t]*([0-9:, -]+)', entry
        )
        if res is not None:
            (syear, smon, smday, eyear, emon, emday, other) = res.groups()
            data = {'syear': syear, 'smon': smon, 'smday': smday, 'swday': 0,
                    'swday_offset': 0, 'eyear': eyear, 'emon': emon, 'emday': emday,
                    'ewday': 0, 'ewday_offset': 0, 'skip_interval': 0,
                    'other': other}
            dateranges.append(CalendarDaterange(data))
            return

        res = re.search(r'(\d{4})-(\d{2})-(\d{2})[\s\t]*([0-9:, -]+)', entry)
        if res is not None:
            (syear, smon, smday, other) = res.groups()
            eyear = syear
            emon = smon
            emday = smday
            data = {'syear': syear, 'smon': smon, 'smday': smday, 'swday': 0,
                    'swday_offset': 0, 'eyear': eyear, 'emon': emon, 'emday': emday,
                    'ewday': 0, 'ewday_offset': 0, 'skip_interval': 0,
                    'other': other}
            dateranges.append(CalendarDaterange(data))
            return

        res = re.search(
            r'([a-z]*) ([\d-]+) ([a-z]*) - ([a-z]*) ([\d-]+) ([a-z]*) / (\d+)[\s\t]*([0-9:, -]+)',
            entry
        )
        if res is not None:
            (swday, swday_offset, smon, ewday,
             ewday_offset, emon, skip_interval, other) = res.groups()
            smon_id = Daterange.get_month_id(smon)
            emon_id = Daterange.get_month_id(emon)
            swday_id = Daterange.get_weekday_id(swday)
            ewday_id = Daterange.get_weekday_id(ewday)
            data = {'syear': 0, 'smon': smon_id, 'smday': 0, 'swday': swday_id,
                    'swday_offset': swday_offset, 'eyear': 0, 'emon': emon_id, 'emday': 0,
                    'ewday': ewday_id, 'ewday_offset': ewday_offset, 'skip_interval': skip_interval,
                    'other': other}
            dateranges.append(MonthWeekDayDaterange(data))
            return

        res = re.search(r'([a-z]*) ([\d-]+) - ([a-z]*) ([\d-]+) / (\d+)[\s\t]*([0-9:, -]+)', entry)
        if res is not None:
            (t00, smday, t01, emday, skip_interval, other) = res.groups()
            if t00 in Daterange.weekdays and t01 in Daterange.weekdays:
                swday = Daterange.get_weekday_id(t00)
                ewday = Daterange.get_weekday_id(t01)
                swday_offset = smday
                ewday_offset = emday
                data = {'syear': 0, 'smon': 0, 'smday': 0, 'swday': swday,
                        'swday_offset': swday_offset, 'eyear': 0, 'emon': 0, 'emday': 0,
                        'ewday': ewday, 'ewday_offset': ewday_offset,
                        'skip_interval': skip_interval, 'other': other}
                dateranges.append(WeekDayDaterange(data))
                return

            if t00 in Daterange.months and t01 in Daterange.months:
                smon = Daterange.get_month_id(t00)
                emon = Daterange.get_month_id(t01)
                data = {'syear': 0, 'smon': smon, 'smday': smday, 'swday': 0, 'swday_offset': 0,
                        'eyear': 0, 'emon': emon, 'emday': emday, 'ewday': 0, 'ewday_offset': 0,
                        'skip_interval': skip_interval, 'other': other}
                dateranges.append(MonthDateDaterange(data))
                return

            if t00 == 'day' and t01 == 'day':
                data = {'syear': 0, 'smon': 0, 'smday': smday, 'swday': 0, 'swday_offset': 0,
                        'eyear': 0, 'emon': 0, 'emday': emday, 'ewday': 0, 'ewday_offset': 0,
                        'skip_interval': skip_interval, 'other': other}
                dateranges.append(MonthDayDaterange(data))
                return

        res = re.search(r'([a-z]*) ([\d-]+) - ([\d-]+) / (\d+)[\s\t]*([0-9:, -]+)', entry)
        if res is not None:
            (t00, smday, emday, skip_interval, other) = res.groups()
            if t00 in Daterange.weekdays:
                swday = Daterange.get_weekday_id(t00)
                swday_offset = smday
                ewday = swday
                ewday_offset = emday
                data = {'syear': 0, 'smon': 0, 'smday': 0, 'swday': swday,
                        'swday_offset': swday_offset, 'eyear': 0, 'emon': 0, 'emday': 0,
                        'ewday': ewday, 'ewday_offset': ewday_offset,
                        'skip_interval': skip_interval, 'other': other}
                dateranges.append(WeekDayDaterange(data))
                return

            if t00 in Daterange.months:
                smon = Daterange.get_month_id(t00)
                emon = smon
                data = {'syear': 0, 'smon': smon, 'smday': smday, 'swday': 0, 'swday_offset': 0,
                        'eyear': 0, 'emon': emon, 'emday': emday, 'ewday': 0, 'ewday_offset': 0,
                        'skip_interval': skip_interval, 'other': other}
                dateranges.append(MonthDateDaterange(data))
                return

            if t00 == 'day':
                data = {'syear': 0, 'smon': 0, 'smday': smday, 'swday': 0, 'swday_offset': 0,
                        'eyear': 0, 'emon': 0, 'emday': emday, 'ewday': 0, 'ewday_offset': 0,
                        'skip_interval': skip_interval, 'other': other}
                dateranges.append(MonthDayDaterange(data))
                return

        res = re.search(
            r'([a-z]*) ([\d-]+) ([a-z]*) - ([a-z]*) ([\d-]+) ([a-z]*) [\s\t]*([0-9:, -]+)', entry
        )
        if res is not None:
            (swday, swday_offset, smon, ewday, ewday_offset, emon, other) = res.groups()
            smon_id = Daterange.get_month_id(smon)
            emon_id = Daterange.get_month_id(emon)
            swday_id = Daterange.get_weekday_id(swday)
            ewday_id = Daterange.get_weekday_id(ewday)
            data = {'syear': 0, 'smon': smon_id, 'smday': 0, 'swday': swday_id,
                    'swday_offset': swday_offset, 'eyear': 0, 'emon': emon_id, 'emday': 0,
                    'ewday': ewday_id, 'ewday_offset': ewday_offset, 'skip_interval': 0,
                    'other': other}
            dateranges.append(MonthWeekDayDaterange(data))
            return

        res = re.search(r'([a-z]*) ([\d-]+) - ([\d-]+)[\s\t]*([0-9:, -]+)', entry)
        if res is not None:
            (t00, smday, emday, other) = res.groups()
            if t00 in Daterange.weekdays:
                swday = Daterange.get_weekday_id(t00)
                swday_offset = smday
                ewday = swday
                ewday_offset = emday
                data = {'syear': 0, 'smon': 0, 'smday': 0, 'swday': swday,
                        'swday_offset': swday_offset, 'eyear': 0, 'emon': 0, 'emday': 0,
                        'ewday': ewday, 'ewday_offset': ewday_offset, 'skip_interval': 0,
                        'other': other}
                dateranges.append(WeekDayDaterange(data))
                return

            if t00 in Daterange.months:
                smon = Daterange.get_month_id(t00)
                emon = smon
                data = {'syear': 0, 'smon': smon, 'smday': smday, 'swday': 0,
                        'swday_offset': 0, 'eyear': 0, 'emon': emon, 'emday': emday,
                        'ewday': 0, 'ewday_offset': 0, 'skip_interval': 0,
                        'other': other}
                dateranges.append(MonthDateDaterange(data))
                return

            if t00 == 'day':
                data = {'syear': 0, 'smon': 0, 'smday': smday, 'swday': 0,
                        'swday_offset': 0, 'eyear': 0, 'emon': 0, 'emday': emday,
                        'ewday': 0, 'ewday_offset': 0, 'skip_interval': 0,
                        'other': other}
                dateranges.append(MonthDayDaterange(data))
                return

        res = re.search(r'([a-z]*) ([\d-]+) - ([a-z]*) ([\d-]+)[\s\t]*([0-9:, -]+)', entry)
        if res is not None:
            (t00, smday, t01, emday, other) = res.groups()
            if t00 in Daterange.weekdays and t01 in Daterange.weekdays:
                swday = Daterange.get_weekday_id(t00)
                ewday = Daterange.get_weekday_id(t01)
                swday_offset = smday
                ewday_offset = emday
                data = {'syear': 0, 'smon': 0, 'smday': 0, 'swday': swday,
                        'swday_offset': swday_offset, 'eyear': 0, 'emon': 0, 'emday': 0,
                        'ewday': ewday, 'ewday_offset': ewday_offset, 'skip_interval': 0,
                        'other': other}
                dateranges.append(WeekDayDaterange(data))
                return

            if t00 in Daterange.months and t01 in Daterange.months:
                smon = Daterange.get_month_id(t00)
                emon = Daterange.get_month_id(t01)
                data = {'syear': 0, 'smon': smon, 'smday': smday, 'swday': 0,
                        'swday_offset': 0, 'eyear': 0, 'emon': emon, 'emday': emday,
                        'ewday': 0, 'ewday_offset': 0, 'skip_interval': 0,
                        'other': other}
                dateranges.append(MonthDateDaterange(data))
                return

            if t00 == 'day' and t01 == 'day':
                data = {'syear': 0, 'smon': 0, 'smday': smday, 'swday': 0,
                        'swday_offset': 0, 'eyear': 0, 'emon': 0, 'emday': emday,
                        'ewday': 0, 'ewday_offset': 0, 'skip_interval': 0,
                        'other': other}
                dateranges.append(MonthDayDaterange(data))
                return

        res = re.search(r'([a-z]*) ([\d-]+) ([a-z]*)[\s\t]*([0-9:, -]+)', entry)
        if res is not None:
            (t00, t02, t01, other) = res.groups()
            if t00 in Daterange.weekdays and t01 in Daterange.months:
                swday = Daterange.get_weekday_id(t00)
                smon = Daterange.get_month_id(t01)
                emon = smon
                ewday = swday
                ewday_offset = t02
                data = {'syear': 0, 'smon': smon, 'smday': 0, 'swday': swday,
                        'swday_offset': t02, 'eyear': 0, 'emon': emon, 'emday': 0,
                        'ewday': ewday, 'ewday_offset': ewday_offset, 'skip_interval': 0,
                        'other': other}
                dateranges.append(MonthWeekDayDaterange(data))
                return
            if not t01:
                if t00 in Daterange.weekdays:
                    swday = Daterange.get_weekday_id(t00)
                    swday_offset = t02
                    ewday = swday
                    ewday_offset = swday_offset
                    data = {'syear': 0, 'smon': 0, 'smday': 0, 'swday': swday,
                            'swday_offset': swday_offset, 'eyear': 0, 'emon': 0, 'emday': 0,
                            'ewday': ewday, 'ewday_offset': ewday_offset, 'skip_interval': 0,
                            'other': other}
                    dateranges.append(WeekDayDaterange(data))
                    return
                if t00 in Daterange.months:
                    smon = Daterange.get_month_id(t00)
                    emon = smon
                    emday = t02
                    data = {'syear': 0, 'smon': smon, 'smday': t02, 'swday': 0,
                            'swday_offset': 0, 'eyear': 0, 'emon': emon, 'emday': emday,
                            'ewday': 0, 'ewday_offset': 0, 'skip_interval': 0,
                            'other': other}
                    dateranges.append(MonthDateDaterange(data))
                    return
                if t00 == 'day':
                    emday = t02
                    data = {'syear': 0, 'smon': 0, 'smday': t02, 'swday': 0,
                            'swday_offset': 0, 'eyear': 0, 'emon': 0, 'emday': emday,
                            'ewday': 0, 'ewday_offset': 0, 'skip_interval': 0,
                            'other': other}
                    dateranges.append(MonthDayDaterange(data))
                    return

        res = re.search(r'([a-z]*)[\s\t]+([0-9:, -]+)', entry)
        if res is not None:
            (t00, other) = res.groups()
            if t00 in Daterange.weekdays:
                day = t00
                data = {'day': day, 'other': other}
                dateranges.append(StandardDaterange(data))
                return
        logger.info("[timeentry::%s] no match for %s", self.get_name(), entry)
        self.invalid_entries.append(entry)

    def apply_inheritance(self):
        """
        Inherite no properties and no custom variables for timeperiod

        :return: None
        """
        pass

    def explode(self):
        """
        Try to resolve all unresolved elements

        :return: None
        """
        for entry in self.unresolved:
            self.resolve_daterange(self.dateranges, entry)
        self.unresolved = []

    def linkify(self, timeperiods):
        """
        Will make timeperiod in exclude with id of the timeperiods

        :param timeperiods: Timeperiods object
        :type timeperiods:
        :return: None
        """
        new_exclude = []
        if hasattr(self, 'exclude') and self.exclude != []:
            logger.debug("[timeentry::%s] have excluded %s", self.get_name(), self.exclude)
            excluded_tps = self.exclude
            for tp_name in excluded_tps:
                timepriod = timeperiods.find_by_name(tp_name.strip())
                if timepriod is not None:
                    new_exclude.append(timepriod.uuid)
                else:
                    msg = "[timeentry::%s] unknown %s timeperiod" % (self.get_name(), tp_name)
                    self.add_error(msg)
        self.exclude = new_exclude

    def check_exclude_rec(self):
        # pylint: disable=access-member-before-definition
        """
        Check if this timeperiod is tagged

        :return: if tagged return false, if not true
        :rtype: bool
        """
        if self.rec_tag:
            msg = "[timeentry::%s] is in a loop in exclude parameter" % (self.get_name())
            self.add_error(msg)
            return False
        self.rec_tag = True
        for timeperiod in self.exclude:
            timeperiod.check_exclude_rec()
        return True

    def fill_data_brok_from(self, data, brok_type):
        """
        Add timeperiods from brok

        :param data: timeperiod dictionnary
        :type data: dict
        :param brok_type: brok type
        :type brok_type: string
        :return: None
        """
        cls = self.__class__
        # Now config properties
        for prop, entry in list(cls.properties.items()):
            # Is this property intended for broking?
            # if 'fill_brok' in entry:
            if brok_type in entry.fill_brok:
                if hasattr(self, prop):
                    data[prop] = getattr(self, prop)
                elif entry.has_default:
                    data[prop] = entry.default


class Timeperiods(Items):
    """
    Class to manage all timeperiods
    A timeperiod is defined with range time (hours) of week to do action
    and add day exceptions (like non working days)
    """

    name_property = "timeperiod_name"
    inner_class = Timeperiod

    def explode(self):
        """
        Try to resolve each timeperiod

        :return: None
        """
        for t_id in self.items:
            timeperiod = self.items[t_id]
            timeperiod.explode()

    def linkify(self):
        """
        Check exclusion for each timeperiod

        :return: None
        """
        for t_id in self.items:
            timeperiod = self.items[t_id]
            timeperiod.linkify(self)

    def get_unresolved_properties_by_inheritance(self, timeperiod):
        """
        Fill full properties with template if needed for the
        unresolved values (example: sunday ETCETC)
        :return: None
        """
        # Ok, I do not have prop, Maybe my templates do?
        # Same story for plus
        for i in timeperiod.templates:
            template = self.templates[i]
            timeperiod.unresolved.extend(template.unresolved)

    def apply_inheritance(self):
        """
        The only interesting property to inherit is exclude

        :return: None
        """
        self.apply_partial_inheritance('exclude')
        for i in self:
            self.get_customs_properties_by_inheritance(i)

        # And now apply inheritance for unresolved properties
        # like the dateranges in fact
        for timeperiod in self:
            self.get_unresolved_properties_by_inheritance(timeperiod)

    def is_correct(self):
        """
        check if each properties of timeperiods are valid

        :return: True if is correct, otherwise False
        :rtype: bool
        """
        valid = True
        # We do not want a same hg to be explode again and again
        # so we tag it
        for timeperiod in list(self.items.values()):
            timeperiod.rec_tag = False

        for timeperiod in list(self.items.values()):
            for tmp_tp in list(self.items.values()):
                tmp_tp.rec_tag = False
            valid = timeperiod.check_exclude_rec() and valid

        # We clean the tags and collect the warning/erro messages
        for timeperiod in list(self.items.values()):
            del timeperiod.rec_tag

            # Now other checks
            if not timeperiod.is_correct():
                valid = False
                source = getattr(timeperiod, 'imported_from', "unknown source")
                msg = "Configuration in %s::%s is incorrect; from: %s" % (
                    timeperiod.my_type, timeperiod.get_name(), source
                )
                self.add_error(msg)

            self.configuration_errors += timeperiod.configuration_errors
            self.configuration_warnings += timeperiod.configuration_warnings

        # And check all timeperiods for correct (sunday is false)
        for timeperiod in self:
            valid = timeperiod.is_correct() and valid

        return valid
