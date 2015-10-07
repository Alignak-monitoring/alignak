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
#     Dessai.Imrane, dessai.imrane@gmail.com
#     xkilian, fmikus@acktomic.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Alexander Springer, alex.spri@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Gerhard Lausser, gerhard.lausser@consol.de

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
"""This module provide Daterange and Timerange classes used to create Timeperiod in Alignak
"""
import time
import calendar
import re

from alignak.util import get_sec_from_morning, get_day, get_start_of_day, get_end_of_day
from alignak.log import logger


def find_day_by_weekday_offset(year, month, weekday, offset):
    """Get the day number based on a date and offset

    :param year: date year
    :type year: int
    :param month: date month
    :type month: int
    :param weekday: date week day
    :type weekday: int
    :param offset: offset (-1 is last, 1 is first etc)
    :type offset: int
    :return: day number in the month
    :rtype: int

    >>> find_day_by_weekday_offset(2010, 7, 1, -1)
    27
    """
    # thanks calendar :)
    cal = calendar.monthcalendar(year, month)

    # If we ask for a -1 day, just reverse cal
    if offset < 0:
        offset = abs(offset)
        cal.reverse()

    # ok go for it
    nb_found = 0
    try:
        for i in xrange(0, offset + 1):
            # in cal 0 mean "there are no day here :)"
            if cal[i][weekday] != 0:
                nb_found += 1
            if nb_found == offset:
                return cal[i][weekday]
        return None
    except Exception:
        return None


def find_day_by_offset(year, month, offset):
    """Get the month day based on date and offset

    :param year: date year
    :type year: int
    :param month: date month
    :type month: int
    :param offset: offset in day to compute (usually negative)
    :type offset: int
    :return: day number in the month
    :rtype: int

    >>> find_day_by_offset(2015, 7, -1)
    31
    """
    (_, days_in_month) = calendar.monthrange(year, month)
    if offset >= 0:
        return min(offset, days_in_month)
    else:
        return max(1, days_in_month + offset + 1)


class Timerange(object):
    """Timerange class provides parsing facilities for time range declaration

    """

    def __init__(self, entry):
        """Entry is like 00:00-24:00

        :param entry: time range entry
        :return: Timerange instance
        :rtype: object
        """
        pattern = r'(\d\d):(\d\d)-(\d\d):(\d\d)'
        matches = re.match(pattern, entry)
        self.is_valid = matches is not None
        if self.is_valid:
            self.hstart, self.mstart, self.hend, self.mend = [int(g) for g in matches.groups()]

    def __str__(self):
        return str(self.__dict__)

    def get_sec_from_morning(self):
        """Get Timerange start time in seconds (from midnight)

        :return: amount of seconds from midnight
        :rtype: int
        """
        return self.hstart * 3600 + self.mstart * 60

    def get_first_sec_out_from_morning(self):
        """Get the first second (from midnight) where we are out of the timerange

        :return: seconds from midnight where timerange is not effective
        :rtype: int
        """
        # If start at 0:0, the min out is the end
        if self.hstart == 0 and self.mstart == 0:
            return self.hend * 3600 + self.mend * 60
        return 0

    def is_time_valid(self, timestamp):
        """Check if time is valid for this Timerange

        :param timestamp: time to check
        :type timestamp: int
        :return: True if time is valid (in interval), False otherwise
        :rtype: bool
        """
        sec_from_morning = get_sec_from_morning(timestamp)
        return (self.is_valid and
                self.hstart * 3600 + self.mstart * 60 <=
                sec_from_morning <=
                self.hend * 3600 + self.mend * 60)

    def is_correct(self):
        """Getter for is_valid attribute

        :return: True if Timerange is valid, False otherwise
        :rtype: bool
        """
        return self.is_valid


class AbstractDaterange(object):
    """AbstractDaterange class provides functions to deal with a range of dates
    It is subclassed for more granularity (weekday, month ...)
    """

    def __str__(self):
        # TODO: What's the point of returning '' always
        return ''  # str(self.__dict__)

    def is_correct(self):
        """Check if each timerange of this datarange is correct

        :return: True if timerange are correct, False otherwise
        :rtype: bool
        """
        for timerange in self.timeranges:
            if not timerange.is_correct():
                return False
        return True

    @classmethod
    def get_month_id(cls, month):
        """Get month id from month name

        :param month: month name
        :type month: str
        :return: month id
        :rtype: int

        >>> Daterange.get_month_id("july")
        7
        """
        return Daterange.months[month]

    @classmethod
    def get_month_by_id(cls, month_id):
        """Get month name from month id

        :param month_id: month id
        :type month_id: int
        :return: month name
        :rtype: str

        >>> Daterange.get_month_by_id(7)
        'july'
        """
        return Daterange.rev_months[month_id]

    @classmethod
    def get_weekday_id(cls, weekday):
        """Get weekday id from weekday name

        :param weekday: weekday name
        :type weekday: str
        :return: weekday id
        :rtype: int

        >>> Daterange.get_weekday_id("monday")
        0
        """
        return Daterange.weekdays[weekday]

    @classmethod
    def get_weekday_by_id(cls, weekday_id):
        """Get weekday name from weekday id

        :param weekday_id: weekday id
        :type weekday_id: int
        :return: weekday name
        :rtype: int

        >>> Daterange.get_weekday_by_id(5)
        'saturday'
        """
        return Daterange.rev_weekdays[weekday_id]

    def get_start_and_end_time(self, ref=None):
        """Generic function to get start time and end time

        :param ref: time in seconds
        :type ref: int
        :return: None
        """
        logger.warning("Calling function get_start_and_end_time which is not implemented")
        raise NotImplementedError()

    def is_time_valid(self, timestamp):
        """Check if time is valid for one of the timerange.

        :param timestamp: time to check
        :type timestamp: int
        :return: True if one of the timerange is valid for t, False otherwise
        :rtype: bool
        """
        # print "****Look for time valid for", time.asctime(time.localtime(t))
        if self.is_time_day_valid(timestamp):
            # print "is time day valid"
            for timerange in self.timeranges:
                # print tr, "is valid?", tr.is_time_valid(t)
                if timerange.is_time_valid(timestamp):
                    # print "return True"
                    return True
        return False

    def get_min_sec_from_morning(self):
        """Get the first second from midnight where a timerange is effective

        :return: smallest amount of second from midnight of all timerange
        :rtype: int
        """
        mins = []
        for timerange in self.timeranges:
            mins.append(timerange.get_sec_from_morning())
        return min(mins)

    def get_min_sec_out_from_morning(self):
        """Get the first second (from midnight) where we are out of a timerange

        :return: smallest seconds from midnight of all timerange where it is not effective
        :rtype: int
        """
        mins = []
        for timerange in self.timeranges:
            mins.append(timerange.get_first_sec_out_from_morning())
        return min(mins)

    def get_min_from_t(self, timestamp):
        """Get next time from t where a timerange is valid (withing range)

        :param timestamp: base time to look for the next one
        :return: time where a timerange is valid
        :rtype: int
        """
        if self.is_time_valid(timestamp):
            return timestamp
        t_day_epoch = get_day(timestamp)
        tr_mins = self.get_min_sec_from_morning()
        return t_day_epoch + tr_mins

    def is_time_day_valid(self, timestamp):
        """Check if t is within start time and end time of the DateRange

        :param timestamp: time to check
        :type timestamp: int
        :return: True if t in range, False otherwise
        :rtype: bool
        """
        (start_time, end_time) = self.get_start_and_end_time(timestamp)
        if start_time <= timestamp <= end_time:
            return True
        else:
            return False

    def is_time_day_invalid(self, timestamp):
        """Check if t is out of start time and end time of the DateRange

        :param timestamp: time to check
        :type timestamp: int
        :return: False if t in range, True otherwise
        :rtype: bool
        TODO: Remove this function. Duplication
        """
        (start_time, end_time) = self.get_start_and_end_time(timestamp)
        if start_time <= timestamp <= end_time:
            return False
        else:
            return True

    def get_next_future_timerange_valid(self, timestamp):
        """Get the next valid timerange (next timerange start in timeranges attribute)

        :param timestamp: base time
        :type timestamp: int
        :return: next time when a timerange is valid
        :rtype: None | int
        """
        # print "Look for get_next_future_timerange_valid for t", t, time.asctime(time.localtime(t))
        sec_from_morning = get_sec_from_morning(timestamp)
        starts = []
        for timerange in self.timeranges:
            tr_start = timerange.hstart * 3600 + timerange.mstart * 60
            if tr_start >= sec_from_morning:
                starts.append(tr_start)
        if starts != []:
            return min(starts)
        else:
            return None

    def get_next_future_timerange_invalid(self, timestamp):
        """Get next invalid time for timeranges

        :param timestamp: time to check
        :type timestamp: int
        :return: next time when a timerange is not valid
        :rtype: None | int
        TODO: Looks like this function is buggy, start time should not be
        included in returned values
        """
        # print 'Call for get_next_future_timerange_invalid from ', time.asctime(time.localtime(t))
        sec_from_morning = get_sec_from_morning(timestamp)
        # print 'sec from morning', sec_from_morning
        ends = []
        for timerange in self.timeranges:
            tr_start = timerange.hstart * 3600 + timerange.mstart * 60
            if tr_start >= sec_from_morning:
                ends.append(tr_start)
            tr_end = timerange.hend * 3600 + timerange.mend * 60
            if tr_end >= sec_from_morning:
                ends.append(tr_end)
        # print "Ends:", ends
        # Remove the last second of the day for 00->24h"
        if 86400 in ends:
            ends.remove(86400)
        if ends != []:
            return min(ends)
        else:
            return None

    def get_next_valid_day(self, timestamp):
        """Get next valid day for timerange

        :param timestamp: time we compute from
        :type timestamp: int
        :return: timestamp of the next valid day (midnight) in LOCAL time.
        :rtype: int | None
        """
        if self.get_next_future_timerange_valid(timestamp) is None:
            # this day is finish, we check for next period
            (start_time, end_time) = self.get_start_and_end_time(get_day(timestamp) + 86400)
        else:
            (start_time, end_time) = self.get_start_and_end_time(timestamp)

        if timestamp <= start_time:
            return get_day(start_time)

        if self.is_time_day_valid(timestamp):
            return get_day(timestamp)
        return None

    def get_next_valid_time_from_t(self, timestamp):
        """Get next valid time for time range

        :param timestamp: time we compute from
        :type timestamp: int
        :return: timestamp of the next valid time (LOCAL TIME)
        :rtype: int | None
        """
        # print "\tDR Get next valid from:", time.asctime(time.localtime(t))
        # print "DR Get next valid from:", t
        if self.is_time_valid(timestamp):
            return timestamp

        # print "DR Get next valid from:", time.asctime(time.localtime(t))
        # First we search fot the day of t
        t_day = self.get_next_valid_day(timestamp)

        # print "DR: T next valid day", time.asctime(time.localtime(t_day))

        # We search for the min of all tr.start > sec_from_morning
        # if it's the next day, use a start of the day search for timerange
        if timestamp < t_day:
            sec_from_morning = self.get_next_future_timerange_valid(t_day)
        else:  # t is in this day, so look from t (can be in the evening or so)
            sec_from_morning = self.get_next_future_timerange_valid(timestamp)
        # print "DR: sec from morning", sec_from_morning

        if sec_from_morning is not None:
            if t_day is not None and sec_from_morning is not None:
                return t_day + sec_from_morning

        # Then we search for the next day of t
        # The sec will be the min of the day
        timestamp = get_day(timestamp) + 86400
        t_day2 = self.get_next_valid_day(timestamp)
        sec_from_morning = self.get_next_future_timerange_valid(t_day2)
        if t_day2 is not None and sec_from_morning is not None:
            return t_day2 + sec_from_morning
        else:
            # I'm not find any valid time
            return None

    def get_next_invalid_day(self, timestamp):
        """Get next day where timerange is not active

        :param timestamp: time we compute from
        :type timestamp: int
        :return: timestamp of the next invalid day (midnight) in LOCAL time.
        :rtype: int | None
        """
        # print "Look in", self.__dict__
        # print 'DR: get_next_invalid_day for', time.asctime(time.localtime(t))
        if self.is_time_day_invalid(timestamp):
            # print "EARLY RETURN"
            return timestamp

        next_future_timerange_invalid = self.get_next_future_timerange_invalid(timestamp)
        # print "next_future_timerange_invalid:", next_future_timerange_invalid

        # If today there is no more unavailable timerange, search the next day
        if next_future_timerange_invalid is None:
            # print 'DR: get_next_future_timerange_invalid is None'
            # this day is finish, we check for next period
            (start_time, end_time) = self.get_start_and_end_time(get_day(timestamp))
        else:
            # print 'DR: get_next_future_timerange_invalid is',
            # print time.asctime(time.localtime(next_future_timerange_invalid))
            (start_time, end_time) = self.get_start_and_end_time(timestamp)

        # (start_time, end_time) = self.get_start_and_end_time(t)

        # print "START", time.asctime(time.localtime(start_time)),
        # print "END", time.asctime(time.localtime(end_time))
        # The next invalid day can be t day if there a possible
        # invalid time range (timerange is not 00->24
        if next_future_timerange_invalid is not None:
            if start_time <= timestamp <= end_time:
                # print "Early Return next invalid day:", time.asctime(time.localtime(get_day(t)))
                return get_day(timestamp)
            if start_time >= timestamp:
                # print "start_time >= t:", time.asctime(time.localtime(get_day(start_time)))
                return get_day(start_time)
        else:
            # Else, there is no possibility than in our start_time<->end_time we got
            # any invalid time (full period out). So it's end_time+1 sec (tomorrow of end_time)
            return get_day(end_time + 1)

        return None

    def get_next_invalid_time_from_t(self, timestamp):
        """Get next invalid time for time range

        :param timestamp: time we compute from
        :type timestamp: int
        :return: timestamp of the next invalid time (LOCAL TIME)
        :rtype: int
        """
        if not self.is_time_valid(timestamp):
            return timestamp

        # First we search fot the day of t
        t_day = self.get_next_invalid_day(timestamp)
        # print "FUCK NEXT DAY", time.asctime(time.localtime(t_day))

        # We search for the min of all tr.start > sec_from_morning
        # if it's the next day, use a start of the day search for timerange
        if timestamp < t_day:
            sec_from_morning = self.get_next_future_timerange_invalid(t_day)
        else:  # t is in this day, so look from t (can be in the evening or so)
            sec_from_morning = self.get_next_future_timerange_invalid(timestamp)
        # print "DR: sec from morning", sec_from_morning

        # tr can't be valid, or it will be return at the beginning
        # sec_from_morning = self.get_next_future_timerange_invalid(t)

        # Ok we've got a next invalid day and a invalid possibility in
        # timerange, so the next invalid is this day+sec_from_morning
        # print "T_day", t_day, "Sec from morning", sec_from_morning
        if t_day is not None and sec_from_morning is not None:
            return t_day + sec_from_morning + 1

        # We've got a day but no sec_from_morning: the timerange is full (0->24h)
        # so the next invalid is this day at the day_start
        if t_day is not None and sec_from_morning is None:
            return t_day

        # Then we search for the next day of t
        # The sec will be the min of the day
        timestamp = get_day(timestamp) + 86400
        t_day2 = self.get_next_invalid_day(timestamp)
        sec_from_morning = self.get_next_future_timerange_invalid(t_day2)
        if t_day2 is not None and sec_from_morning is not None:
            return t_day2 + sec_from_morning + 1

        if t_day2 is not None and sec_from_morning is None:
            return t_day2
        else:
            # I'm not find any valid time
            return None


class Daterange(AbstractDaterange):
    """Daterange  subclasses AbstractDaterange and
    instantiates Timerange objects
    """

    weekdays = {  # NB : 0 based : 0 == monday
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    months = {  # NB : 1 based : 1 == january..
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5,
        'june': 6, 'july': 7, 'august': 8, 'september': 9,
        'october': 10, 'november': 11, 'december': 12
    }
    rev_weekdays = dict((v, k) for k, v in weekdays.items())
    rev_months = dict((v, k) for k, v in months.items())

    def __init__(self, syear, smon, smday, swday, swday_offset,
                 eyear, emon, emday, ewday, ewday_offset, skip_interval, other):
        """

        :param syear: start year
        :type syear: int
        :param smon: start month
        :type smon: int
        :param smday: start day (number)
        :type smday: int
        :param swday: start day (week day id)
        :type swday: int
        :param swday_offset: offset in the month (1 is first, -1 last)
        :type swday_offset: int
        :param eyear: end year
        :type eyear: int
        :param emon: end month
        :type emon: int
        :param emday: end day
        :type emday: int
        :param ewday: end day (week day id)
        :type ewday: int
        :param ewday_offset: offset in the month (1 is first, -1 last)
        :type ewday_offset: int
        :param skip_interval: interval to skip ( /3 => every 3 days)
        :type skip_interval: str
        :param other: other timerange
        :type other:
        :return: None
        """
        super(Daterange, self).__init__()
        self.syear = int(syear)
        self.smon = int(smon)
        self.smday = int(smday)
        self.swday = int(swday)
        self.swday_offset = int(swday_offset)
        self.eyear = int(eyear)
        self.emon = int(emon)
        self.emday = int(emday)
        self.ewday = int(ewday)
        self.ewday_offset = int(ewday_offset)
        self.skip_interval = int(skip_interval)
        self.other = other
        self.timeranges = []

        for timeinterval in other.split(','):
            self.timeranges.append(Timerange(timeinterval.strip()))


class CalendarDaterange(Daterange):
    """CalendarDaterange is for calendar entry (YYYY-MM-DD - YYYY-MM-DD)

    """
    def get_start_and_end_time(self, ref=None):
        """Specific function to get start time and end time for CalendarDaterange

        :param ref: time in seconds
        :type ref: int
        :return: tuple with start and end time
        :rtype: tuple
        """
        start_time = get_start_of_day(self.syear, int(self.smon), self.smday)
        end_time = get_end_of_day(self.eyear, int(self.emon), self.emday)
        return (start_time, end_time)


class StandardDaterange(AbstractDaterange):
    """StandardDaterange is for standard entry (weekday - weekday)

    """
    def __init__(self, day, other):
        """
        Init of StandardDaterange

        :param day: one of Daterange.weekdays
        :type day: str
        :param other:
        :type other: str
        :return: None
        """
        self.other = other
        self.timeranges = []

        for timeinterval in other.split(','):
            self.timeranges.append(Timerange(timeinterval.strip()))
        self.day = day

    def is_correct(self):
        """Check if the Daterange is correct : weekdays are valid

        :return: True if weekdays are valid, False otherwise
        :rtype: bool
        """
        valid = self.day in Daterange.weekdays
        if not valid:
            logger.error("Error: %s is not a valid day", self.day)
        # Check also if Daterange is correct.
        valid &= super(StandardDaterange, self).is_correct()
        return valid

    def get_start_and_end_time(self, ref=None):
        """Specific function to get start time and end time for StandardDaterange

        :param ref: time in seconds
        :type ref: int
        :return: tuple with start and end time
        :rtype: tuple
        """
        now = time.localtime(ref)
        self.syear = now.tm_year
        self.month = now.tm_mon
        # month_start_id = now.tm_mon
        # month_start = Daterange.get_month_by_id(month_start_id)
        self.wday = now.tm_wday
        day_id = Daterange.get_weekday_id(self.day)
        today_morning = get_start_of_day(now.tm_year, now.tm_mon, now.tm_mday)
        tonight = get_end_of_day(now.tm_year, now.tm_mon, now.tm_mday)
        day_diff = (day_id - now.tm_wday) % 7
        return (today_morning + day_diff * 86400, tonight + day_diff * 86400)


class MonthWeekDayDaterange(Daterange):
    """MonthWeekDayDaterange is for month week day entry (weekday DD month - weekday DD month)

    """

    def is_correct(self):
        """Check if the Daterange is correct : weekdays are valid

        :return: True if weekdays are valid, False otherwise
        :rtype: bool
        """
        valid = True
        valid &= self.swday in xrange(7)
        if not valid:
            logger.error("Error: %s is not a valid day", self.swday)

        valid &= self.ewday in xrange(7)
        if not valid:
            logger.error("Error: %s is not a valid day", self.ewday)

        return valid

    def get_start_and_end_time(self, ref=None):
        """Specific function to get start time and end time for MonthWeekDayDaterange

        :param ref: time in seconds
        :type ref: int | None
        :return: tuple with start and end time
        :rtype: tuple
        """
        now = time.localtime(ref)

        if self.syear == 0:
            self.syear = now.tm_year
        day_start = find_day_by_weekday_offset(self.syear, self.smon, self.swday, self.swday_offset)
        start_time = get_start_of_day(self.syear, self.smon, day_start)

        if self.eyear == 0:
            self.eyear = now.tm_year
        day_end = find_day_by_weekday_offset(self.eyear, self.emon, self.ewday, self.ewday_offset)
        end_time = get_end_of_day(self.eyear, self.emon, day_end)

        now_epoch = time.mktime(now)
        if start_time > end_time:  # the period is between years
            if now_epoch > end_time:  # check for next year
                day_end = find_day_by_weekday_offset(self.eyear + 1,
                                                     self.emon, self.ewday, self.ewday_offset)
                end_time = get_end_of_day(self.eyear + 1, self.emon, day_end)
            else:
                # it s just that the start was the last year
                day_start = find_day_by_weekday_offset(self.syear - 1,
                                                       self.smon, self.swday, self.swday_offset)
                start_time = get_start_of_day(self.syear - 1, self.smon, day_start)
        else:
            if now_epoch > end_time:
                # just have to check for next year if necessary
                day_start = find_day_by_weekday_offset(self.syear + 1,
                                                       self.smon, self.swday, self.swday_offset)
                start_time = get_start_of_day(self.syear + 1, self.smon, day_start)
                day_end = find_day_by_weekday_offset(self.eyear + 1,
                                                     self.emon, self.ewday, self.ewday_offset)
                end_time = get_end_of_day(self.eyear + 1, self.emon, day_end)

        return (start_time, end_time)


class MonthDateDaterange(Daterange):
    """MonthDateDaterange is for month and day entry (month DD - month DD)

    """
    def get_start_and_end_time(self, ref=None):
        """Specific function to get start time and end time for MonthDateDaterange

        :param ref: time in seconds
        :type ref: int
        :return: tuple with start and end time
        :rtype: tuple
        """
        now = time.localtime(ref)
        if self.syear == 0:
            self.syear = now.tm_year
        day_start = find_day_by_offset(self.syear, self.smon, self.smday)
        start_time = get_start_of_day(self.syear, self.smon, day_start)

        if self.eyear == 0:
            self.eyear = now.tm_year
        day_end = find_day_by_offset(self.eyear, self.emon, self.emday)
        end_time = get_end_of_day(self.eyear, self.emon, day_end)

        now_epoch = time.mktime(now)
        if start_time > end_time:  # the period is between years
            if now_epoch > end_time:
                # check for next year
                day_end = find_day_by_offset(self.eyear + 1, self.emon, self.emday)
                end_time = get_end_of_day(self.eyear + 1, self.emon, day_end)
            else:
                # it s just that start was the last year
                day_start = find_day_by_offset(self.syear - 1, self.smon, self.emday)
                start_time = get_start_of_day(self.syear - 1, self.smon, day_start)
        else:
            if now_epoch > end_time:
                # just have to check for next year if necessary
                day_start = find_day_by_offset(self.syear + 1, self.smon, self.smday)
                start_time = get_start_of_day(self.syear + 1, self.smon, day_start)
                day_end = find_day_by_offset(self.eyear + 1, self.emon, self.emday)
                end_time = get_end_of_day(self.eyear + 1, self.emon, day_end)

        return (start_time, end_time)


class WeekDayDaterange(Daterange):
    """WeekDayDaterange is for month week day entry (weekday offset  - weekday offset)

    """
    def get_start_and_end_time(self, ref=None):
        """Specific function to get start time and end time for WeekDayDaterange

        :param ref: time in seconds
        :type ref: int
        :return: tuple with start and end time
        :rtype: tuple
        """
        now = time.localtime(ref)

        # If no year, it's our year
        if self.syear == 0:
            self.syear = now.tm_year
        month_start_id = now.tm_mon
        day_start = find_day_by_weekday_offset(self.syear,
                                               month_start_id, self.swday, self.swday_offset)
        start_time = get_start_of_day(self.syear, month_start_id, day_start)

        # Same for end year
        if self.eyear == 0:
            self.eyear = now.tm_year
        month_end_id = now.tm_mon
        day_end = find_day_by_weekday_offset(self.eyear, month_end_id, self.ewday,
                                             self.ewday_offset)
        end_time = get_end_of_day(self.eyear, month_end_id, day_end)

        # Maybe end_time is before start. So look for the
        # next month
        if start_time > end_time:
            month_end_id += 1
            if month_end_id > 12:
                month_end_id = 1
                self.eyear += 1
            day_end = find_day_by_weekday_offset(self.eyear,
                                                 month_end_id, self.ewday, self.ewday_offset)
            end_time = get_end_of_day(self.eyear, month_end_id, day_end)

        now_epoch = time.mktime(now)
        # But maybe we look not enought far. We should add a month
        if end_time < now_epoch:
            month_end_id += 1
            month_start_id += 1
            if month_end_id > 12:
                month_end_id = 1
                self.eyear += 1
            if month_start_id > 12:
                month_start_id = 1
                self.syear += 1
            # First start
            day_start = find_day_by_weekday_offset(self.syear,
                                                   month_start_id, self.swday, self.swday_offset)
            start_time = get_start_of_day(self.syear, month_start_id, day_start)
            # Then end
            day_end = find_day_by_weekday_offset(self.eyear,
                                                 month_end_id, self.ewday, self.ewday_offset)
            end_time = get_end_of_day(self.eyear, month_end_id, day_end)

        return (start_time, end_time)


class MonthDayDaterange(Daterange):
    """MonthDayDaterange is for month week day entry (day DD - DD)

    """
    def get_start_and_end_time(self, ref=None):
        """Specific function to get start time and end time for MonthDayDaterange

        :param ref: time in seconds
        :type ref: int
        :return: tuple with start and end time
        :rtype: tuple
        """
        now = time.localtime(ref)
        if self.syear == 0:
            self.syear = now.tm_year
        month_start_id = now.tm_mon
        day_start = find_day_by_offset(self.syear, month_start_id, self.smday)
        start_time = get_start_of_day(self.syear, month_start_id, day_start)

        if self.eyear == 0:
            self.eyear = now.tm_year
        month_end_id = now.tm_mon
        day_end = find_day_by_offset(self.eyear, month_end_id, self.emday)
        end_time = get_end_of_day(self.eyear, month_end_id, day_end)

        now_epoch = time.mktime(now)

        if start_time > end_time:
            month_start_id -= 1
            if month_start_id < 1:
                month_start_id = 12
                self.syear -= 1
        day_start = find_day_by_offset(self.syear, month_start_id, self.smday)
        start_time = get_start_of_day(self.syear, month_start_id, day_start)

        if end_time < now_epoch:
            month_end_id += 1
            month_start_id += 1
            if month_end_id > 12:
                month_end_id = 1
                self.eyear += 1
            if month_start_id > 12:
                month_start_id = 1
                self.syear += 1

            # For the start
            day_start = find_day_by_offset(self.syear, month_start_id, self.smday)
            start_time = get_start_of_day(self.syear, month_start_id, day_start)

            # For the end
            day_end = find_day_by_offset(self.eyear, month_end_id, self.emday)
            end_time = get_end_of_day(self.eyear, month_end_id, day_end)

        return (start_time, end_time)
