#!/usr/bin/env python
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
This file is used to test dateranges

We make timestamp with time.mktime because timestamp not same is you are in timezone UTC or Paris
"""
# pylint: disable=R0904

import time
import pytest
from freezegun import freeze_time
from alignak_test import AlignakTest
from alignak.objects.timeperiod import Timeperiod
from alignak.daterange import CalendarDaterange, StandardDaterange, MonthWeekDayDaterange, \
    MonthDateDaterange, WeekDayDaterange, MonthDayDaterange, find_day_by_weekday_offset, \
    find_day_by_offset
import alignak.util


class TestDateRanges(AlignakTest):
    """
    This class test dataranges
    """

    def test_get_start_of_day(self):
        """ Test function get_start_of_day and return the timestamp of begin of day

        :return: None
        """
        now = time.localtime()
        start = time.mktime((2015, 7, 26, 0, 0, 0, 0, 0, now.tm_isdst))
        timestamp = alignak.util.get_start_of_day(2015, 7, 26)
        # time.timezone is the offset related of the current timezone of the system
        print("Start: %s, timestamp: %s")
        assert start == (timestamp - time.timezone)

    @pytest.mark.skip("To be completed... because the start test do not pass locally!")
    def test_get_start_of_day_tz_aware(self):
        """ Test function get_start_of_day and return the timestamp of begin of day

        :return: None
        """
        now = time.localtime()
        tz_shift = time.timezone
        dst = now.tm_isdst
        print("Now: %s, timezone: %s, DST: %s" % (now, tz_shift, dst))
        start = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, 0, 0, 0, 0, 0, -1))
        print("Start: %s" % start)
        # Alignak returns the start of day ts in local time
        timestamp = alignak.util.get_start_of_day(now.tm_year, now.tm_mon, now.tm_mday)
        print("Timestamp: %s" % timestamp)
        # time.timezone is the offset related of the current timezone of the system
        assert start == (timestamp - time.timezone)

    def test_get_end_of_day(self):
        """ Test function get_end_of_day and return the timestamp of end of day

        :return: None
        """
        now = time.localtime()
        start = time.mktime((2016, 8, 20, 23, 59, 59, 0, 0, now.tm_isdst))
        timestamp = alignak.util.get_end_of_day(2016, 8, 20)
        print("Start: %s, timestamp: %s")
        # time.timezone is the offset related of the current timezone of the system
        assert start == (timestamp - time.timezone)

    def test_find_day_by_weekday_offset(self):
        """ Test function find_day_by_weekday_offset to get day number.
        In this case, 1 = thuesday and -1 = last thuesday of July 2010, so it's the 27 july 2010

        :return: None
        """
        ret = find_day_by_weekday_offset(2010, 7, 1, -1)
        assert 27 == ret

    def test_find_day_by_offset(self):
        """ Test function find_day_by_offset to get the day with offset.
        In this case, the last day number of july, so the 31th

        :return: None
        """
        ret = find_day_by_offset(2015, 7, -1)
        assert 31 == ret

        ret = find_day_by_offset(2015, 7, 10)
        assert 10 == ret

    def test_calendardaterange_start_end_time(self):
        """ Test CalendarDaterange.get_start_and_end_time to get start and end date of date range

        :return: None
        """
        local_offset = time.timezone - 3600 * time.daylight  # TS below are for UTC
        local_hour_offset = local_offset / 3600
        if local_hour_offset >= 0:
            local_hour_offset = "-%02d" % local_hour_offset
        else:
            local_hour_offset = "+%02d" % -local_hour_offset
        data = {
            '2015-07-20 01:50:00 %s' % local_hour_offset: {
                'start': 1437868800 + local_offset,
                'end': 1471737599 + local_offset
            },
            '2015-07-26 01:50:00 %s' % local_hour_offset: {
                'start': 1437868800 + local_offset,
                'end': 1471737599 + local_offset
            },
            '2016-01-01 01:50:00 %s' % local_hour_offset: {
                'start': 1437868800 + local_offset,
                'end': 1471737599 + local_offset
            },
            '2016-08-21 01:50:00 %s' % local_hour_offset: {
                'start': 1437868800 + local_offset,
                'end': 1471737599 + local_offset
            },
        }
        params = {'syear': 2015, 'smon': 7, 'smday': 26, 'swday': 0,
                  'swday_offset': 0, 'eyear': 2016, 'emon': 8, 'emday': 20,
                  'ewday': 0, 'ewday_offset': 0, 'skip_interval': 3,
                  'other': ''}
        caldate = CalendarDaterange(params)
        for date_now in data:
            with freeze_time(date_now, tz_offset=0):
                ret = caldate.get_start_and_end_time()
                print "* %s" % date_now
                assert data[date_now]['start'] == ret[0]
                assert data[date_now]['end'] == ret[1]

    def test_standarddaterange_start_end_time(self):
        """ Test StandardDaterange.get_start_and_end_time to get start and end date of date range

        :return: None
        """
        local_offset = time.timezone - 3600 * time.daylight  # TS below are for UTC
        local_hour_offset = local_offset / 3600
        if local_hour_offset >= 0:
            local_hour_offset = "-%02d" % local_hour_offset
        else:
            local_hour_offset = "+%02d" % -local_hour_offset
        data = {}
        for num in xrange(1, 3):
            data['2015-07-%02d 01:50:00 %s' % (num, local_hour_offset)] = {
                'start': 1435881600 + local_offset,
                'end': 1435967999 + local_offset
            }
        for num in xrange(4, 10):
            data['2015-07-%02d 01:50:00 %s' % (num, local_hour_offset)] = {
                'start': 1436486400 + local_offset,
                'end': 1436572799 + local_offset
            }
        for num in xrange(11, 17):
            data['2015-07-%02d 01:50:00 %s' % (num, local_hour_offset)] = {
                'start': 1437091200 + local_offset,
                'end': 1437177599 + local_offset
            }

        # Time from next wednesday morning to next wednesday night
        caldate = StandardDaterange({'day': 'friday', 'other': '00:00-24:00'})
        for date_now in data:
            with freeze_time(date_now, tz_offset=0):
                ret = caldate.get_start_and_end_time()
                print "* %s" % date_now
                assert data[date_now]['start'] == ret[0]
                assert data[date_now]['end'] == ret[1]

    def test_monthweekdaydaterange_start_end_time(self):
        """ Test MonthWeekDayDaterange.get_start_and_end_time to get start and end date of date range

        :return: None
        """
        data = {}
        local_offset = time.timezone - 3600 * time.daylight  # TS below are for UTC
        local_hour_offset = local_offset / 3600
        if local_hour_offset >= 0:
            local_hour_offset = "-%02d" % local_hour_offset
        else:
            local_hour_offset = "+%02d" % -local_hour_offset
        for num in xrange(1, 31):
            data['2015-07-%02d 01:50:00 %s' % (num, local_hour_offset)] = {
                'start': 1436832000 + local_offset,
                'end': 1440201599 + local_offset
            }
        for num in xrange(1, 21):
            data['2015-08-%02d 01:50:00 %s' % (num, local_hour_offset)] = {
                'start': 1436832000 + local_offset,
                'end': 1440201599 + local_offset
            }

        for num in xrange(22, 31):
            data['2015-08-%02d 01:50:00 %s ' % (num, local_hour_offset)] = {
                'start': 1468281600 + local_offset,
                'end': 1471651199 + local_offset
            }

        # 2nd tuesday of July 2015 => 14
        # 3rd friday of August 2015 => 21
        # next : 2nd tuesday of July 2016 => 12
        # next  3rd friday of August 2016 => 19
        params = {'syear': 2015, 'smon': 7, 'smday': 0, 'swday': 1, 'swday_offset': 2,
                  'eyear': 2015, 'emon': 8, 'emday': 0, 'ewday': 4, 'ewday_offset': 3,
                  'skip_interval': 0, 'other': ''}
        caldate = MonthWeekDayDaterange(params)
        for date_now in data:
            with freeze_time(date_now, tz_offset=0):
                ret = caldate.get_start_and_end_time()
                print "* %s" % date_now
                assert data[date_now]['start'] == ret[0]
                assert data[date_now]['end'] == ret[1]

    def test_monthdatedaterange_start_end_time(self):
        """ Test MonthDateDaterange.get_start_and_end_time to get start and end date of date range

        :return: None
        """
        local_offset = time.timezone - 3600 * time.daylight  # TS below are for UTC
        local_hour_offset = local_offset / 3600
        if local_hour_offset >= 0:
            local_hour_offset = "-%02d" % local_hour_offset
        else:
            local_hour_offset = "+%02d" % -local_hour_offset
        data = {
            '2015-07-20 01:50:00 %s' % local_hour_offset: {
                'start': 1437868800 + local_offset,
                'end': 1440115199 + local_offset
            },
            '2015-07-26 01:50:00 %s' % local_hour_offset: {
                'start': 1437868800 + local_offset,
                'end': 1440115199 + local_offset
            },
            '2015-08-28 01:50:00 %s' % local_hour_offset: {
                'start': 1469491200 + local_offset,
                'end': 1471737599 + local_offset
            },
            '2016-01-01 01:50:00 %s' % local_hour_offset: {
                'start': 1469491200 + local_offset,
                'end': 1471737599 + local_offset
            },
        }
        params = {'syear': 0, 'smon': 7, 'smday': 26, 'swday': 0, 'swday_offset': 0,
                  'eyear': 0, 'emon': 8, 'emday': 20, 'ewday': 0, 'ewday_offset': 0,
                  'skip_interval': 0, 'other': ''}
        caldate = MonthDateDaterange(params)
        for date_now in data:
            with freeze_time(date_now, tz_offset=0):
                ret = caldate.get_start_and_end_time()
                print "* %s" % date_now
                assert data[date_now]['start'] == ret[0]
                assert data[date_now]['end'] == ret[1]

    def test_weekdaydaterange_start_end_time(self):
        """ Test WeekDayDaterange.get_start_and_end_time to get start and end date of date range

        :return: None
        """
        local_offset = time.timezone - 3600 * time.daylight  # TS below are for UTC
        local_hour_offset = local_offset / 3600
        if local_hour_offset >= 0:
            local_hour_offset = "-%02d" % local_hour_offset
        else:
            local_hour_offset = "+%02d" % -local_hour_offset
        data = {
            '2015-07-07 01:50:00 %s' % local_hour_offset: {
                'start': 1436745600 + local_offset,
                'end': 1437523199 + local_offset
            },
            '2015-07-20 01:50:00 %s' % local_hour_offset: {
                'start': 1436745600 + local_offset,
                'end': 1437523199 + local_offset
            },
            '2015-07-24 01:50:00 %s' % local_hour_offset: {
                'start': 1439164800 + local_offset,
                'end': 1439942399 + local_offset
            },
            '2015-08-02 01:50:00 %s' % local_hour_offset: {
                'start': 1439164800 + local_offset,
                'end': 1439942399 + local_offset
            },
        }
        # second monday - third tuesday
        params = {'syear': 0, 'smon': 0, 'smday': 0, 'swday': 0, 'swday_offset': 2,
                  'eyear': 0, 'emon': 0, 'emday': 0, 'ewday': 1, 'ewday_offset': 3,
                  'skip_interval': 0, 'other': ''}
        caldate = WeekDayDaterange(params)
        for date_now in data:
            with freeze_time(date_now, tz_offset=0):
                ret = caldate.get_start_and_end_time()
                print "* %s" % date_now
                assert data[date_now]['start'] == ret[0]
                assert data[date_now]['end'] == ret[1]

    def test_monthdaydaterange_start_end_time(self):
        """ Test MonthDayDaterange.get_start_and_end_time to get start and end date of date range

        :return: None
        """
        local_offset = time.timezone - 3600 * time.daylight  # TS below are for UTC
        local_hour_offset = local_offset / 3600
        if local_hour_offset >= 0:
            local_hour_offset = "-%02d" % local_hour_offset
        else:
            local_hour_offset = "+%02d" % -local_hour_offset
        data = {
            '2015-07-07 01:50:00 %s' % local_hour_offset: {
                'start': 1438387200 + local_offset,
                'end': 1438819199 + local_offset
            },
            '2015-07-31 01:50:00 %s' % local_hour_offset: {
                'start': 1438387200 + local_offset,
                'end': 1438819199 + local_offset
            },
            '2015-08-05 01:50:00 %s' % local_hour_offset: {
                'start': 1438387200 + local_offset,
                'end': 1438819199 + local_offset
            },
            '2015-08-06 01:50:00 %s' % local_hour_offset: {
                'start': 1441065600 + local_offset,
                'end': 1441497599 + local_offset
            },
        }

        # day -1 - 5 00:00-10:00
        params = {'syear': 0, 'smon': 0, 'smday': 1, 'swday': 0, 'swday_offset': 0,
                  'eyear': 0, 'emon': 0, 'emday': 5, 'ewday': 0, 'ewday_offset': 0,
                  'skip_interval': 0, 'other': ''}
        caldate = MonthDayDaterange(params)
        for date_now in data:
            with freeze_time(date_now, tz_offset=0):
                ret = caldate.get_start_and_end_time()
                print "* %s" % date_now
                assert data[date_now]['start'] == ret[0]
                assert data[date_now]['end'] == ret[1]

    def test_monthdaydaterange_start_end_time_negative(self):
        """ Test MonthDayDaterange.get_start_and_end_time to get start and end date of date range with
        negative values

        :return: None
        """
        local_offset = time.timezone - 3600 * time.daylight  # TS below are for UTC
        local_hour_offset = local_offset / 3600
        if local_hour_offset >= 0:
            local_hour_offset = "-%02d" % local_hour_offset
        else:
            local_hour_offset = "+%02d" % -local_hour_offset
        data = {
            '2015-07-07 01:50:00 %s' % local_hour_offset: {
                'start': 1438300800 + local_offset,
                'end': 1438819199 + local_offset
            },
            '2015-07-31 01:50:00 %s' % local_hour_offset: {
                'start': 1438300800 + local_offset,
                'end': 1438819199 + local_offset
            },
            '2015-08-01 01:50:00 %s' % local_hour_offset: {
                'start': 1438300800 + local_offset,
                'end': 1438819199 + local_offset
            },
            '2015-08-05 01:50:00 %s' % local_hour_offset: {
                'start': 1438300800 + local_offset,
                'end': 1438819199 + local_offset
            },
            '2015-08-06 01:50:00 %s' % local_hour_offset: {
                'start': 1440979200 + local_offset,
                'end': 1441497599 + local_offset
            },
        }

        # day -1 - 5 00:00-10:00
        params = {'syear': 0, 'smon': 0, 'smday': -1, 'swday': 0, 'swday_offset': 0,
                  'eyear': 0, 'emon': 0, 'emday': 5, 'ewday': 0, 'ewday_offset': 0,
                  'skip_interval': 0, 'other': ''}
        caldate = MonthDayDaterange(params)
        for date_now in data:
            with freeze_time(date_now, tz_offset=0):
                ret = caldate.get_start_and_end_time()
                print "* %s" % date_now
                assert data[date_now]['start'] == ret[0]
                assert data[date_now]['end'] == ret[1]

    def test_standarddaterange_is_correct(self):
        """ Test if time from next wednesday morning to next wednesday night is correct

        :return: None
        """
        caldate = StandardDaterange({'day': 'wednesday', 'other': '00:00-24:00'})
        assert caldate.is_correct()

    def test_monthweekdaydaterange_is_correct(self):
        """ Test if time from next wednesday morning to next wednesday night is correct

        :return: None
        """
        params = {'syear': 2015, 'smon': 7, 'smday': 0, 'swday': 1, 'swday_offset': 2,
                  'eyear': 2015, 'emon': 8, 'emday': 0, 'ewday': 4, 'ewday_offset': 3,
                  'skip_interval': 0, 'other': ''}
        caldate = MonthWeekDayDaterange(params)
        assert caldate.is_correct()

    def test_resolve_daterange_case1(self):
        """ Test resolve daterange, case 1

        :return: None
        """
        timeperiod = Timeperiod()
        entry = '2015-07-26 - 2016-08-20 / 3 00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 2015 == timeperiod.dateranges[0].syear
        assert 7 == timeperiod.dateranges[0].smon
        assert 26 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 0 == timeperiod.dateranges[0].swday_offset
        assert 2016 == timeperiod.dateranges[0].eyear
        assert 8 == timeperiod.dateranges[0].emon
        assert 20 == timeperiod.dateranges[0].emday
        assert 0 == timeperiod.dateranges[0].ewday
        assert 0 == timeperiod.dateranges[0].ewday_offset
        assert 3 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case2(self):
        """ Test resolve daterange, case 2

        :return: None
        """
        timeperiod = Timeperiod()
        entry = '2015-07-26 / 7             00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 2015 == timeperiod.dateranges[0].syear
        assert 7 == timeperiod.dateranges[0].smon
        assert 26 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 0 == timeperiod.dateranges[0].swday_offset
        assert 2015 == timeperiod.dateranges[0].eyear
        assert 7 == timeperiod.dateranges[0].emon
        assert 26 == timeperiod.dateranges[0].emday
        assert 0 == timeperiod.dateranges[0].ewday
        assert 0 == timeperiod.dateranges[0].ewday_offset
        assert 7 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case3(self):
        """ Test resolve daterange, case 3

        :return: None
        """
        timeperiod = Timeperiod()
        entry = '2015-07-26 - 2016-08-20    00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 2015 == timeperiod.dateranges[0].syear
        assert 7 == timeperiod.dateranges[0].smon
        assert 26 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 0 == timeperiod.dateranges[0].swday_offset
        assert 2016 == timeperiod.dateranges[0].eyear
        assert 8 == timeperiod.dateranges[0].emon
        assert 20 == timeperiod.dateranges[0].emday
        assert 0 == timeperiod.dateranges[0].ewday
        assert 0 == timeperiod.dateranges[0].ewday_offset
        assert 0 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case4(self):
        """ Test resolve daterange, case 4

        :return: None
        """
        timeperiod = Timeperiod()
        entry = '2015-07-26  00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 2015 == timeperiod.dateranges[0].syear
        assert 7 == timeperiod.dateranges[0].smon
        assert 26 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 0 == timeperiod.dateranges[0].swday_offset
        assert 2015 == timeperiod.dateranges[0].eyear
        assert 7 == timeperiod.dateranges[0].emon
        assert 26 == timeperiod.dateranges[0].emday
        assert 0 == timeperiod.dateranges[0].ewday
        assert 0 == timeperiod.dateranges[0].ewday_offset
        assert 0 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case5(self):
        """ Test resolve daterange, case 5

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'tuesday 1 october - friday 2 may / 6 00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 10 == timeperiod.dateranges[0].smon
        assert 0 == timeperiod.dateranges[0].smday
        assert 1 == timeperiod.dateranges[0].swday
        assert 1 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 5 == timeperiod.dateranges[0].emon
        assert 0 == timeperiod.dateranges[0].emday
        assert 4 == timeperiod.dateranges[0].ewday
        assert 2 == timeperiod.dateranges[0].ewday_offset
        assert 6 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case6(self):
        """ Test resolve daterange, case 6

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'monday 4 - thursday 3 / 2 00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 0 == timeperiod.dateranges[0].smon
        assert 0 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 4 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 0 == timeperiod.dateranges[0].emon
        assert 0 == timeperiod.dateranges[0].emday
        assert 3 == timeperiod.dateranges[0].ewday
        assert 3 == timeperiod.dateranges[0].ewday_offset
        assert 2 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case7(self):
        """ Test resolve daterange, case 7

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'march 4 - july 3 / 2 00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 3 == timeperiod.dateranges[0].smon
        assert 4 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 0 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 7 == timeperiod.dateranges[0].emon
        assert 3 == timeperiod.dateranges[0].emday
        assert 0 == timeperiod.dateranges[0].ewday
        assert 0 == timeperiod.dateranges[0].ewday_offset
        assert 2 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case8(self):
        """ Test resolve daterange, case 8

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'day 4 - day 3 / 2 00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 0 == timeperiod.dateranges[0].smon
        assert 4 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 0 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 0 == timeperiod.dateranges[0].emon
        assert 3 == timeperiod.dateranges[0].emday
        assert 0 == timeperiod.dateranges[0].ewday
        assert 0 == timeperiod.dateranges[0].ewday_offset
        assert 2 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case9(self):
        """ Test resolve daterange, case 9

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'friday 2 - 15 / 5             00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 0 == timeperiod.dateranges[0].smon
        assert 0 == timeperiod.dateranges[0].smday
        assert 4 == timeperiod.dateranges[0].swday
        assert 2 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 0 == timeperiod.dateranges[0].emon
        assert 0 == timeperiod.dateranges[0].emday
        assert 4 == timeperiod.dateranges[0].ewday
        assert 15 == timeperiod.dateranges[0].ewday_offset
        assert 5 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case10(self):
        """ Test resolve daterange, case 10

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'july 2 - 15 / 5             00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 7 == timeperiod.dateranges[0].smon
        assert 2 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 0 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 7 == timeperiod.dateranges[0].emon
        assert 15 == timeperiod.dateranges[0].emday
        assert 0 == timeperiod.dateranges[0].ewday
        assert 0 == timeperiod.dateranges[0].ewday_offset
        assert 5 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case11(self):
        """ Test resolve daterange, case 11

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'day 8 - 15 / 5             00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 0 == timeperiod.dateranges[0].smon
        assert 8 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 0 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 0 == timeperiod.dateranges[0].emon
        assert 15 == timeperiod.dateranges[0].emday
        assert 0 == timeperiod.dateranges[0].ewday
        assert 0 == timeperiod.dateranges[0].ewday_offset
        assert 5 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case12(self):
        """ Test resolve daterange, case 12

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'tuesday 3 july - friday 2 september 00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 7 == timeperiod.dateranges[0].smon
        assert 0 == timeperiod.dateranges[0].smday
        assert 1 == timeperiod.dateranges[0].swday
        assert 3 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 9 == timeperiod.dateranges[0].emon
        assert 0 == timeperiod.dateranges[0].emday
        assert 4 == timeperiod.dateranges[0].ewday
        assert 2 == timeperiod.dateranges[0].ewday_offset
        assert 0 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case13(self):
        """ Test resolve daterange, case 13

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'friday 1 - 3         00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 0 == timeperiod.dateranges[0].smon
        assert 0 == timeperiod.dateranges[0].smday
        assert 4 == timeperiod.dateranges[0].swday
        assert 1 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 0 == timeperiod.dateranges[0].emon
        assert 0 == timeperiod.dateranges[0].emday
        assert 4 == timeperiod.dateranges[0].ewday
        assert 3 == timeperiod.dateranges[0].ewday_offset
        assert 0 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case14(self):
        """ Test resolve daterange, case 14

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'july -10 - -1              00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 7 == timeperiod.dateranges[0].smon
        assert -10 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 0 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 7 == timeperiod.dateranges[0].emon
        assert -1 == timeperiod.dateranges[0].emday
        assert 0 == timeperiod.dateranges[0].ewday
        assert 0 == timeperiod.dateranges[0].ewday_offset
        assert 0 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case15(self):
        """ Test resolve daterange, case 15

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'day 1 - 15         00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 0 == timeperiod.dateranges[0].smon
        assert 1 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 0 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 0 == timeperiod.dateranges[0].emon
        assert 15 == timeperiod.dateranges[0].emday
        assert 0 == timeperiod.dateranges[0].ewday
        assert 0 == timeperiod.dateranges[0].ewday_offset
        assert 0 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case16(self):
        """ Test resolve daterange, case 16

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'monday 3 - thursday 4      00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 0 == timeperiod.dateranges[0].smon
        assert 0 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 3 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 0 == timeperiod.dateranges[0].emon
        assert 0 == timeperiod.dateranges[0].emday
        assert 3 == timeperiod.dateranges[0].ewday
        assert 4 == timeperiod.dateranges[0].ewday_offset
        assert 0 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case17(self):
        """ Test resolve daterange, case 17

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'april 10 - may 15          00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 4 == timeperiod.dateranges[0].smon
        assert 10 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 0 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 5 == timeperiod.dateranges[0].emon
        assert 15 == timeperiod.dateranges[0].emday
        assert 0 == timeperiod.dateranges[0].ewday
        assert 0 == timeperiod.dateranges[0].ewday_offset
        assert 0 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case18(self):
        """ Test resolve daterange, case 18

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'day 10 - day 15          00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 0 == timeperiod.dateranges[0].smon
        assert 10 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 0 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 0 == timeperiod.dateranges[0].emon
        assert 15 == timeperiod.dateranges[0].emday
        assert 0 == timeperiod.dateranges[0].ewday
        assert 0 == timeperiod.dateranges[0].ewday_offset
        assert 0 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case19(self):
        """ Test resolve daterange, case 19

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'tuesday 3 november        00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 11 == timeperiod.dateranges[0].smon
        assert 0 == timeperiod.dateranges[0].smday
        assert 1 == timeperiod.dateranges[0].swday
        assert 3 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 11 == timeperiod.dateranges[0].emon
        assert 0 == timeperiod.dateranges[0].emday
        assert 1 == timeperiod.dateranges[0].ewday
        assert 3 == timeperiod.dateranges[0].ewday_offset
        assert 0 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case20(self):
        """ Test resolve daterange, case 20

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'tuesday 3      00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 0 == timeperiod.dateranges[0].smon
        assert 0 == timeperiod.dateranges[0].smday
        assert 1 == timeperiod.dateranges[0].swday
        assert 3 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 0 == timeperiod.dateranges[0].emon
        assert 0 == timeperiod.dateranges[0].emday
        assert 1 == timeperiod.dateranges[0].ewday
        assert 3 == timeperiod.dateranges[0].ewday_offset
        assert 0 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case21(self):
        """ Test resolve daterange, case 21

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'may 3      00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 5 == timeperiod.dateranges[0].smon
        assert 3 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 0 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 5 == timeperiod.dateranges[0].emon
        assert 3 == timeperiod.dateranges[0].emday
        assert 0 == timeperiod.dateranges[0].ewday
        assert 0 == timeperiod.dateranges[0].ewday_offset
        assert 0 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case22(self):
        """ Test resolve daterange, case 22

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'day 3      00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 0 == timeperiod.dateranges[0].syear
        assert 0 == timeperiod.dateranges[0].smon
        assert 3 == timeperiod.dateranges[0].smday
        assert 0 == timeperiod.dateranges[0].swday
        assert 0 == timeperiod.dateranges[0].swday_offset
        assert 0 == timeperiod.dateranges[0].eyear
        assert 0 == timeperiod.dateranges[0].emon
        assert 3 == timeperiod.dateranges[0].emday
        assert 0 == timeperiod.dateranges[0].ewday
        assert 0 == timeperiod.dateranges[0].ewday_offset
        assert 0 == timeperiod.dateranges[0].skip_interval
        assert '00:00-24:00' == timeperiod.dateranges[0].other

    def test_resolve_daterange_case23(self):
        """ Test resolve daterange, case 23

        :return: None
        """
        timeperiod = Timeperiod()
        entry = 'sunday 00:00-24:00'
        timeperiod.resolve_daterange(timeperiod.dateranges, entry)

        assert 'sunday' == timeperiod.dateranges[0].day
