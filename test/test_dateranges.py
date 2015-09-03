#!/usr/bin/env python
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

"""This file is used to test dateranges

We make timestamp with time.mktime because timestamp not same is you are in timezone UTC or Paris
"""

from alignak_test import *
from alignak.objects.timeperiod import Timeperiod
from alignak.daterange import CalendarDaterange, StandardDaterange, MonthWeekDayDaterange, \
    MonthDateDaterange, WeekDayDaterange, MonthDayDaterange, find_day_by_weekday_offset, \
    find_day_by_offset
import alignak.util
import time
import datetime
import calendar
from freezegun import freeze_time


#@unittest.skipIf(True, """\
#Test fails with many dates, temporarily disabled until it's completely fixed
# """)
class TestDataranges(AlignakTest):

    def test_get_start_of_day(self):
        now = time.localtime()
        start = time.mktime((2015, 7, 26, 0, 0, 0, 0, 0, now.tm_isdst))
        timestamp = alignak.util.get_start_of_day(2015, 7, 26)
        self.assertEqual(start, timestamp)

    def test_get_end_of_day(self):
        now = time.localtime()
        start = time.mktime((2016, 8, 20, 23, 59, 59, 0, 0, now.tm_isdst))
        timestamp = alignak.util.get_end_of_day(2016, 8, 20)
        self.assertEqual(start, timestamp)

    def test_find_day_by_weekday_offset(self):
        ret = find_day_by_weekday_offset(2010, 7, 1, -1)
        self.assertEqual(27, ret)

    def test_find_day_by_offset(self):
        ret = find_day_by_offset(2015, 7, -1)
        self.assertEqual(31, ret)

        ret = find_day_by_offset(2015, 7, 10)
        self.assertEqual(10, ret)

    def test_calendardaterange_start_end_time(self):
        local_offset = time.timezone - 3600 * time.daylight  #TS below are for UTC
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

        caldate = CalendarDaterange(2015, 7, 26, 0, 0, 2016, 8, 20, 0, 0, 3, '')
        for date_now in data:
            with freeze_time(date_now, tz_offset=0):
                ret = caldate.get_start_and_end_time()
                print "* %s" % date_now
                self.assertEqual(data[date_now]['start'], ret[0])
                self.assertEqual(data[date_now]['end'], ret[1])

    def test_standarddaterange_start_end_time(self):
        local_offset = time.timezone - 3600 * time.daylight  #TS below are for UTC
        local_hour_offset = local_offset / 3600
        if local_hour_offset >= 0:
            local_hour_offset = "-%02d" % local_hour_offset
        else:
            local_hour_offset = "+%02d" % -local_hour_offset
        data = {}
        for x in xrange(1, 3):
            data['2015-07-%02d 01:50:00 %s' % (x, local_hour_offset)] = {
                'start': 1435881600 + local_offset,
                'end': 1435967999 + local_offset
            }
        for x in xrange(4, 10):
            data['2015-07-%02d 01:50:00 %s' % (x, local_hour_offset)] = {
                'start': 1436486400 + local_offset,
                'end': 1436572799 + local_offset
            }
        for x in xrange(11, 17):
            data['2015-07-%02d 01:50:00 %s' % (x, local_hour_offset)] = {
                'start': 1437091200 + local_offset,
                'end': 1437177599 + local_offset
            }

        # Time from next wednesday morning to next wednesday night
        caldate = StandardDaterange('friday', '00:00-24:00')
        for date_now in data:
            with freeze_time(date_now, tz_offset=0):
                ret = caldate.get_start_and_end_time()
                print "* %s" % date_now
                self.assertEqual(data[date_now]['start'], ret[0])
                self.assertEqual(data[date_now]['end'], ret[1])

    def test_MonthWeekDayDaterange_start_end_time(self):
        data = {}
        local_offset = time.timezone - 3600 * time.daylight  #TS below are for UTC
        local_hour_offset = local_offset / 3600
        if local_hour_offset >= 0:
            local_hour_offset = "-%02d" % local_hour_offset
        else:
            local_hour_offset = "+%02d" % -local_hour_offset
        for x in xrange(1, 31):
            data['2015-07-%02d 01:50:00 %s' % (x, local_hour_offset)] = {
                'start': 1436832000 + local_offset,
                'end': 1440201599 + local_offset
            }
        for x in xrange(1, 21):
            data['2015-08-%02d 01:50:00 %s' % (x, local_hour_offset)] = {
                'start': 1436832000 + local_offset,
                'end': 1440201599 + local_offset
            }

        for x in xrange(22, 31):
            data['2015-08-%02d 01:50:00 %s ' % (x, local_hour_offset)] = {
                'start': 1468281600 + local_offset,
                'end': 1471651199 + local_offset
            }

        # 2nd tuesday of July 2015 => 14
        # 3rd friday of August 2015 => 21
        # next : 2nd tuesday of July 2016 => 12
        # next  3rd friday of August 2016 => 19
        caldate = MonthWeekDayDaterange(2015, 7, 0, 1, 2,
                                        2015, 8, 0, 4, 3, 0, '')
        for date_now in data:
            with freeze_time(date_now, tz_offset=0):
                ret = caldate.get_start_and_end_time()
                print "* %s" % date_now
                self.assertEqual(data[date_now]['start'], ret[0])
                self.assertEqual(data[date_now]['end'], ret[1])

    def test_monthdatedaterange_start_end_time(self):
        local_offset = time.timezone - 3600 * time.daylight  #TS below are for UTC
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
        caldate = MonthDateDaterange(0, 7, 26, 0, 0,
                                     0, 8, 20, 0, 0, 0, '')
        for date_now in data:
            with freeze_time(date_now, tz_offset=0):
                ret = caldate.get_start_and_end_time()
                print "* %s" % date_now
                self.assertEqual(data[date_now]['start'], ret[0])
                self.assertEqual(data[date_now]['end'], ret[1])

    def test_weekdaydaterange_start_end_time(self):
        local_offset = time.timezone - 3600 * time.daylight  #TS below are for UTC
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
        caldate = WeekDayDaterange(0, 0, 0, 0, 2,
                                   0, 0, 0, 1, 3, 0, '')
        for date_now in data:
            with freeze_time(date_now, tz_offset=0):
                ret = caldate.get_start_and_end_time()
                print "* %s" % date_now
                self.assertEqual(data[date_now]['start'], ret[0])
                self.assertEqual(data[date_now]['end'], ret[1])

    def test_monthdaydaterange_start_end_time(self):
        local_offset = time.timezone - 3600 * time.daylight  #TS below are for UTC
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
        caldate = MonthDayDaterange(0, 0, 1, 0, 0,
                                    0, 0, 5, 0, 0, 0, '')
        for date_now in data:
            with freeze_time(date_now, tz_offset=0):
                ret = caldate.get_start_and_end_time()
                print "* %s" % date_now
                self.assertEqual(data[date_now]['start'], ret[0])
                self.assertEqual(data[date_now]['end'], ret[1])

    def test_monthdaydaterange_start_end_time_negative(self):
        local_offset = time.timezone - 3600 * time.daylight  #TS below are for UTC
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
        caldate = MonthDayDaterange(0, 0, -1, 0, 0,
                                    0, 0, 5, 0, 0, 0, '')
        for date_now in data:
            with freeze_time(date_now, tz_offset=0):
                ret = caldate.get_start_and_end_time()
                print "* %s" % date_now
                self.assertEqual(data[date_now]['start'], ret[0])
                self.assertEqual(data[date_now]['end'], ret[1])

    def test_standarddaterange_is_correct(self):
        # Time from next wednesday morning to next wednesday night
        caldate = StandardDaterange('wednesday', '00:00-24:00')
        self.assertTrue(caldate.is_correct())

    def test_monthweekdaydaterange_is_correct(self):
        # Time from next wednesday morning to next wednesday night
        caldate = MonthWeekDayDaterange(2015, 7, 0, 1, 2,
                                        2015, 8, 0, 4, 3, 0, '')
        self.assertTrue(caldate.is_correct())

    def test_resolve_daterange_case1(self):
        t = Timeperiod()
        entry = '2015-07-26 - 2016-08-20 / 3 00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(2015, t.dateranges[0].syear)
        self.assertEqual(7, t.dateranges[0].smon)
        self.assertEqual(26, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(0, t.dateranges[0].swday_offset)
        self.assertEqual(2016, t.dateranges[0].eyear)
        self.assertEqual(8, t.dateranges[0].emon)
        self.assertEqual(20, t.dateranges[0].emday)
        self.assertEqual(0, t.dateranges[0].ewday)
        self.assertEqual(0, t.dateranges[0].ewday_offset)
        self.assertEqual(3, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case2(self):
        t = Timeperiod()
        entry = '2015-07-26 / 7             00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(2015, t.dateranges[0].syear)
        self.assertEqual(7, t.dateranges[0].smon)
        self.assertEqual(26, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(0, t.dateranges[0].swday_offset)
        self.assertEqual(2015, t.dateranges[0].eyear)
        self.assertEqual(7, t.dateranges[0].emon)
        self.assertEqual(26, t.dateranges[0].emday)
        self.assertEqual(0, t.dateranges[0].ewday)
        self.assertEqual(0, t.dateranges[0].ewday_offset)
        self.assertEqual(7, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case3(self):
        t = Timeperiod()
        entry = '2015-07-26 - 2016-08-20    00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(2015, t.dateranges[0].syear)
        self.assertEqual(7, t.dateranges[0].smon)
        self.assertEqual(26, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(0, t.dateranges[0].swday_offset)
        self.assertEqual(2016, t.dateranges[0].eyear)
        self.assertEqual(8, t.dateranges[0].emon)
        self.assertEqual(20, t.dateranges[0].emday)
        self.assertEqual(0, t.dateranges[0].ewday)
        self.assertEqual(0, t.dateranges[0].ewday_offset)
        self.assertEqual(0, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case4(self):
        t = Timeperiod()
        entry = '2015-07-26  00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(2015, t.dateranges[0].syear)
        self.assertEqual(7, t.dateranges[0].smon)
        self.assertEqual(26, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(0, t.dateranges[0].swday_offset)
        self.assertEqual(2015, t.dateranges[0].eyear)
        self.assertEqual(7, t.dateranges[0].emon)
        self.assertEqual(26, t.dateranges[0].emday)
        self.assertEqual(0, t.dateranges[0].ewday)
        self.assertEqual(0, t.dateranges[0].ewday_offset)
        self.assertEqual(0, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case5(self):
        t = Timeperiod()
        entry = 'tuesday 1 october - friday 2 may / 6 00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(10, t.dateranges[0].smon)
        self.assertEqual(0, t.dateranges[0].smday)
        self.assertEqual(1, t.dateranges[0].swday)
        self.assertEqual(1, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(5, t.dateranges[0].emon)
        self.assertEqual(0, t.dateranges[0].emday)
        self.assertEqual(4, t.dateranges[0].ewday)
        self.assertEqual(2, t.dateranges[0].ewday_offset)
        self.assertEqual(6, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case6(self):
        t = Timeperiod()
        entry = 'monday 4 - thursday 3 / 2 00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(0, t.dateranges[0].smon)
        self.assertEqual(0, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(4, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(0, t.dateranges[0].emon)
        self.assertEqual(0, t.dateranges[0].emday)
        self.assertEqual(3, t.dateranges[0].ewday)
        self.assertEqual(3, t.dateranges[0].ewday_offset)
        self.assertEqual(2, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case7(self):
        t = Timeperiod()
        entry = 'march 4 - july 3 / 2 00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(3, t.dateranges[0].smon)
        self.assertEqual(4, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(0, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(7, t.dateranges[0].emon)
        self.assertEqual(3, t.dateranges[0].emday)
        self.assertEqual(0, t.dateranges[0].ewday)
        self.assertEqual(0, t.dateranges[0].ewday_offset)
        self.assertEqual(2, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case8(self):
        t = Timeperiod()
        entry = 'day 4 - day 3 / 2 00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(0, t.dateranges[0].smon)
        self.assertEqual(4, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(0, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(0, t.dateranges[0].emon)
        self.assertEqual(3, t.dateranges[0].emday)
        self.assertEqual(0, t.dateranges[0].ewday)
        self.assertEqual(0, t.dateranges[0].ewday_offset)
        self.assertEqual(2, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case9(self):
        t = Timeperiod()
        entry = 'friday 2 - 15 / 5             00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(0, t.dateranges[0].smon)
        self.assertEqual(0, t.dateranges[0].smday)
        self.assertEqual(4, t.dateranges[0].swday)
        self.assertEqual(2, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(0, t.dateranges[0].emon)
        self.assertEqual(0, t.dateranges[0].emday)
        self.assertEqual(4, t.dateranges[0].ewday)
        self.assertEqual(15, t.dateranges[0].ewday_offset)
        self.assertEqual(5, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case10(self):
        t = Timeperiod()
        entry = 'july 2 - 15 / 5             00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(7, t.dateranges[0].smon)
        self.assertEqual(2, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(0, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(7, t.dateranges[0].emon)
        self.assertEqual(15, t.dateranges[0].emday)
        self.assertEqual(0, t.dateranges[0].ewday)
        self.assertEqual(0, t.dateranges[0].ewday_offset)
        self.assertEqual(5, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case11(self):
        t = Timeperiod()
        entry = 'day 8 - 15 / 5             00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(0, t.dateranges[0].smon)
        self.assertEqual(8, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(0, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(0, t.dateranges[0].emon)
        self.assertEqual(15, t.dateranges[0].emday)
        self.assertEqual(0, t.dateranges[0].ewday)
        self.assertEqual(0, t.dateranges[0].ewday_offset)
        self.assertEqual(5, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case12(self):
        t = Timeperiod()
        entry = 'tuesday 3 july - friday 2 september 00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(7, t.dateranges[0].smon)
        self.assertEqual(0, t.dateranges[0].smday)
        self.assertEqual(1, t.dateranges[0].swday)
        self.assertEqual(3, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(9, t.dateranges[0].emon)
        self.assertEqual(0, t.dateranges[0].emday)
        self.assertEqual(4, t.dateranges[0].ewday)
        self.assertEqual(2, t.dateranges[0].ewday_offset)
        self.assertEqual(0, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case13(self):
        t = Timeperiod()
        entry = 'friday 1 - 3         00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(0, t.dateranges[0].smon)
        self.assertEqual(0, t.dateranges[0].smday)
        self.assertEqual(4, t.dateranges[0].swday)
        self.assertEqual(1, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(0, t.dateranges[0].emon)
        self.assertEqual(0, t.dateranges[0].emday)
        self.assertEqual(4, t.dateranges[0].ewday)
        self.assertEqual(3, t.dateranges[0].ewday_offset)
        self.assertEqual(0, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case14(self):
        t = Timeperiod()
        entry = 'july -10 - -1              00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(7, t.dateranges[0].smon)
        self.assertEqual(-10, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(0, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(7, t.dateranges[0].emon)
        self.assertEqual(-1, t.dateranges[0].emday)
        self.assertEqual(0, t.dateranges[0].ewday)
        self.assertEqual(0, t.dateranges[0].ewday_offset)
        self.assertEqual(0, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case15(self):
        t = Timeperiod()
        entry = 'day 1 - 15         00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(0, t.dateranges[0].smon)
        self.assertEqual(1, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(0, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(0, t.dateranges[0].emon)
        self.assertEqual(15, t.dateranges[0].emday)
        self.assertEqual(0, t.dateranges[0].ewday)
        self.assertEqual(0, t.dateranges[0].ewday_offset)
        self.assertEqual(0, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case16(self):
        t = Timeperiod()
        entry = 'monday 3 - thursday 4      00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(0, t.dateranges[0].smon)
        self.assertEqual(0, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(3, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(0, t.dateranges[0].emon)
        self.assertEqual(0, t.dateranges[0].emday)
        self.assertEqual(3, t.dateranges[0].ewday)
        self.assertEqual(4, t.dateranges[0].ewday_offset)
        self.assertEqual(0, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case17(self):
        t = Timeperiod()
        entry = 'april 10 - may 15          00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(4, t.dateranges[0].smon)
        self.assertEqual(10, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(0, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(5, t.dateranges[0].emon)
        self.assertEqual(15, t.dateranges[0].emday)
        self.assertEqual(0, t.dateranges[0].ewday)
        self.assertEqual(0, t.dateranges[0].ewday_offset)
        self.assertEqual(0, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case18(self):
        t = Timeperiod()
        entry = 'day 10 - day 15          00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(0, t.dateranges[0].smon)
        self.assertEqual(10, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(0, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(0, t.dateranges[0].emon)
        self.assertEqual(15, t.dateranges[0].emday)
        self.assertEqual(0, t.dateranges[0].ewday)
        self.assertEqual(0, t.dateranges[0].ewday_offset)
        self.assertEqual(0, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case19(self):
        t = Timeperiod()
        entry = 'tuesday 3 november        00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(11, t.dateranges[0].smon)
        self.assertEqual(0, t.dateranges[0].smday)
        self.assertEqual(1, t.dateranges[0].swday)
        self.assertEqual(3, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(11, t.dateranges[0].emon)
        self.assertEqual(0, t.dateranges[0].emday)
        self.assertEqual(1, t.dateranges[0].ewday)
        self.assertEqual(3, t.dateranges[0].ewday_offset)
        self.assertEqual(0, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case20(self):
        t = Timeperiod()
        entry = 'tuesday 3      00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(0, t.dateranges[0].smon)
        self.assertEqual(0, t.dateranges[0].smday)
        self.assertEqual(1, t.dateranges[0].swday)
        self.assertEqual(3, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(0, t.dateranges[0].emon)
        self.assertEqual(0, t.dateranges[0].emday)
        self.assertEqual(1, t.dateranges[0].ewday)
        self.assertEqual(3, t.dateranges[0].ewday_offset)
        self.assertEqual(0, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case21(self):
        t = Timeperiod()
        entry = 'may 3      00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(5, t.dateranges[0].smon)
        self.assertEqual(3, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(0, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(5, t.dateranges[0].emon)
        self.assertEqual(3, t.dateranges[0].emday)
        self.assertEqual(0, t.dateranges[0].ewday)
        self.assertEqual(0, t.dateranges[0].ewday_offset)
        self.assertEqual(0, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case22(self):
        t = Timeperiod()
        entry = 'day 3      00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual(0, t.dateranges[0].syear)
        self.assertEqual(0, t.dateranges[0].smon)
        self.assertEqual(3, t.dateranges[0].smday)
        self.assertEqual(0, t.dateranges[0].swday)
        self.assertEqual(0, t.dateranges[0].swday_offset)
        self.assertEqual(0, t.dateranges[0].eyear)
        self.assertEqual(0, t.dateranges[0].emon)
        self.assertEqual(3, t.dateranges[0].emday)
        self.assertEqual(0, t.dateranges[0].ewday)
        self.assertEqual(0, t.dateranges[0].ewday_offset)
        self.assertEqual(0, t.dateranges[0].skip_interval)
        self.assertEqual('00:00-24:00', t.dateranges[0].other)

    def test_resolve_daterange_case23(self):
        t = Timeperiod()
        entry = 'sunday 00:00-24:00'
        t.resolve_daterange(t.dateranges, entry)

        self.assertEqual('sunday', t.dateranges[0].day)


if __name__ == '__main__':
    unittest.main()
