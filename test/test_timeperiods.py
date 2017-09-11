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
#
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Alexander Springer, alex.spri@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de

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

#
# This file is used to test timeperiods
#

from alignak_test import *
from alignak.objects.timeperiod import Timeperiod


class TestTimeperiods(AlignakTest):

    def test_timeperiod_no_daterange(self):
        """
        Test with a timeperiod have no daterange

        :return: None
        """
        self.print_header()
        now = time.time()

        timeperiod = Timeperiod()
        timeperiod.resolve_daterange(timeperiod.dateranges, '1999-01-28  00:00-24:00')
        t_next = timeperiod.get_next_valid_time_from_t(now)
        self.assertIsNone(t_next)

    def test_simple_timeperiod(self):
        """
        Test a timeperiod with one timerange

        :return: None
        """
        self.print_header()
        now = time.time()
        # Get the 12 of july 2010 at 15:00, monday
        july_the_12 = time.mktime(time.strptime("12 Jul 2010 15:00:00", "%d %b %Y %H:%M:%S"))
        print july_the_12

        timeperiod = Timeperiod()
        timeperiod.resolve_daterange(timeperiod.dateranges, 'tuesday 16:30-24:00')
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        print t_next
        self.assertEqual("Tue Jul 13 16:30:00 2010", t_next)

    def test_simple_with_multiple_time(self):
        """
        Test timeperiod with 2 ranges:
          * tuesday 00:00-07:00
          * tuesday 21:30-24:00

        :return: None
        """
        self.print_header()
        now = time.time()
        # Get the 12 of july 2010 at 15:00, monday
        july_the_12 = time.mktime(time.strptime("12 Jul 2010 15:00:00", "%d %b %Y %H:%M:%S"))
        print july_the_12

        # Then a simple same day
        print "Cheking validity for", time.asctime(time.localtime(july_the_12))
        timeperiod = Timeperiod()
        timeperiod.resolve_daterange(timeperiod.dateranges, 'tuesday 00:00-07:00,21:30-24:00')
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        print "RES:", t_next
        self.assertEqual("Tue Jul 13 00:00:00 2010", t_next)

        # Now ask about at 00:00 time?
        july_the_12 = time.mktime(time.strptime("12 Jul 2010 00:00:00", "%d %b %Y %H:%M:%S"))
        # Then a simple same day
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        print "Next?", t_next
        self.assertEqual("Tue Jul 13 00:00:00 2010", t_next)

    def test_get_invalid_time(self):
        """
        Test get next invalid time

        :return: None
        """
        self.print_header()
        timeperiod = Timeperiod()
        timeperiod.resolve_daterange(timeperiod.dateranges, 'monday 00:00-24:00')
        first_nov = int(time.mktime(time.strptime("1 Nov 2010 00:00:00", "%d %b %Y %H:%M:%S")))
        print first_nov
        end = timeperiod.get_next_invalid_time_from_t(first_nov)
        end = time.asctime(time.localtime(end))
        self.assertEqual("Tue Nov  2 00:00:00 2010", end)

        first_nov = int(time.mktime(time.strptime("2 Nov 2010 00:00:00", "%d %b %Y %H:%M:%S")))
        print first_nov
        end = timeperiod.get_next_invalid_time_from_t(first_nov)
        end = time.asctime(time.localtime(end))
        self.assertEqual("Tue Nov  2 00:00:00 2010", end)

    def test_get_invalid_time_with_exclude(self):
        """
        Test get next invalid time with exclude

        :return: None
        """
        self.print_header()
        timeperiod = Timeperiod()
        timeperiod.resolve_daterange(timeperiod.dateranges, 'monday 00:00-24:00')

        t2 = Timeperiod()
        t2.resolve_daterange(t2.dateranges, 'monday 08:30-21:00')
        timeperiod.exclude = [t2]

        first_nov = int(time.mktime(time.strptime("1 Nov 2010 00:00:00", "%d %b %Y %H:%M:%S")))
        print first_nov
        end = timeperiod.get_next_invalid_time_from_t(first_nov)
        end = time.asctime(time.localtime(end))
        self.assertEqual("Mon Nov  1 08:30:00 2010", end)

        second_nov = int(time.mktime(time.strptime("2 Nov 2010 00:00:00", "%d %b %Y %H:%M:%S")))
        print second_nov
        end = timeperiod.get_next_invalid_time_from_t(second_nov)
        end = time.asctime(time.localtime(end))
        self.assertEqual("Tue Nov  2 00:00:00 2010", end)

    def test_get_valid_time(self):
        """
        Test get next valid time

        :return: None
        """
        self.print_header()
        timeperiod = Timeperiod()
        timeperiod.resolve_daterange(timeperiod.dateranges, 'monday 00:00-24:00')
        first_nov = int(time.mktime(time.strptime("26 Oct 2010 00:00:00", "%d %b %Y %H:%M:%S")))
        print first_nov
        start = timeperiod.get_next_valid_time_from_t(first_nov)
        self.assertIsNotNone(start)
        start = time.asctime(time.localtime(start))
        self.assertEqual("Mon Nov  1 00:00:00 2010", start)

    def test_simple_with_multiple_time_multiple_days(self):
        """
        Test timeperiod with multiple daterange on multiple days:
          * monday 00:00-07:00
          * monday 21:30-24:00
          * tuesday 00:00-07:00
          * tuesday 21:30-24:00

        :return: None
        """
        self.print_header()
        now = time.time()
        # Get the 12 of july 2010 at 15:00, monday
        july_the_12 = time.mktime(time.strptime("12 Jul 2010 15:00:00", "%d %b %Y %H:%M:%S"))
        print july_the_12

        # Then a simple same day
        timeperiod = Timeperiod()
        print "Cheking validity for", time.asctime(time.localtime(july_the_12))
        timeperiod.resolve_daterange(timeperiod.dateranges, 'monday 00:00-07:00,21:30-24:00')
        timeperiod.resolve_daterange(timeperiod.dateranges, 'tuesday 00:00-07:00,21:30-24:00')
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        print "RES:", t_next
        self.assertEqual("Mon Jul 12 21:30:00 2010", t_next)

        # what about the next invalid?
        t_next_inv = timeperiod.get_next_invalid_time_from_t(july_the_12)
        t_next_inv = time.asctime(time.localtime(t_next_inv))
        print "RES:", t_next_inv
        self.assertEqual("Mon Jul 12 15:00:00 2010", t_next_inv)

        # what about a valid time and ask next invalid? Like at 22:00h?
        july_the_12 = time.mktime(time.strptime("12 Jul 2010 22:00:00", "%d %b %Y %H:%M:%S"))
        t_next_inv = timeperiod.get_next_invalid_time_from_t(july_the_12)
        t_next_inv = time.asctime(time.localtime(t_next_inv))
        print "RES:", t_next_inv #, t.is_time_valid(july_the_12)
        self.assertEqual("Tue Jul 13 07:00:01 2010", t_next_inv)

        # Now ask about at 00:00 time?
        july_the_12 = time.mktime(time.strptime("12 Jul 2010 00:00:00", "%d %b %Y %H:%M:%S"))
        print "Cheking validity for", time.asctime(time.localtime(july_the_12))
        # Then a simple same day
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        print "Next?", t_next
        self.assertEqual("Mon Jul 12 00:00:00 2010", t_next)

    def test_get_invalid_when_timeperiod_24x7(self):
        """
        Test get the next invalid time when timeperiod 24x7

        :return:
        """
        now = time.time()
        july_the_12 = time.mktime(time.strptime("12 Jul 2010 15:00:00", "%d %b %Y %H:%M:%S"))

        # Now look for the never case
        tp_all = Timeperiod()
        tp_all.resolve_daterange(tp_all.dateranges, 'monday 00:00-24:00')
        tp_all.resolve_daterange(tp_all.dateranges, 'tuesday 00:00-24:00')
        tp_all.resolve_daterange(tp_all.dateranges, 'wednesday 00:00-24:00')
        tp_all.resolve_daterange(tp_all.dateranges, 'thursday 00:00-24:00')
        tp_all.resolve_daterange(tp_all.dateranges, 'friday 00:00-24:00')
        tp_all.resolve_daterange(tp_all.dateranges, 'saturday 00:00-24:00')
        tp_all.resolve_daterange(tp_all.dateranges, 'sunday 00:00-24:00')
        t_next_inv = tp_all.get_next_invalid_time_from_t(july_the_12)
        t_next_inv = time.asctime(time.localtime(t_next_inv))
        print "RES:", t_next_inv #, t.is_time_valid(july_the_12)
        self.assertEqual('Tue Jul 19 00:00:00 2011', t_next_inv)

    def test_simple_timeperiod_with_exclude(self):
        """
        Test simple timeperiod with exclude periods

        :return: None
        """
        self.print_header()
        now = time.time()
        # Get the 12 of july 2010 at 15:00, monday
        july_the_12 = time.mktime(time.strptime("12 Jul 2010 15:00:00", "%d %b %Y %H:%M:%S"))
        print july_the_12

        # First a false test, no results
        timeperiod = Timeperiod()
        timeperiod.resolve_daterange(timeperiod.dateranges, '1999-01-28  00:00-24:00')
        t_next = timeperiod.get_next_valid_time_from_t(now)
        self.assertIs(None, t_next)

        # Then a simple same day
        timeperiod = Timeperiod()
        timeperiod.resolve_daterange(timeperiod.dateranges, 'tuesday 16:30-24:00')
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        print t_next
        self.assertEqual("Tue Jul 13 16:30:00 2010", t_next)

        # Now we add this timeperiod an exception
        t2 = Timeperiod()
        t2.timeperiod_name = ''
        t2.resolve_daterange(t2.dateranges, 'tuesday 08:30-21:00')
        timeperiod.exclude = [t2]
        # So the next will be after 16:30 and not before 21:00. So
        # It will be 21:00:01 (first second after invalid is valid)

        # we clean the cache of previous calc of t ;)
        timeperiod.cache = {}
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        print "T nxt with exclude:", t_next
        self.assertEqual("Tue Jul 13 21:00:01 2010", t_next)

    def test_dayweek_timeperiod_with_exclude(self):
        """
        test dayweek timeperiod with exclude

        :return: None
        """
        self.print_header()
        now = time.time()
        # Get the 12 of july 2010 at 15:00, monday
        july_the_12 = time.mktime(time.strptime("12 Jul 2010 15:00:00", "%d %b %Y %H:%M:%S"))

        # Then a simple same day
        timeperiod = Timeperiod()
        timeperiod.timeperiod_name = 'T1'
        timeperiod.resolve_daterange(timeperiod.dateranges, 'tuesday 2 16:30-24:00')
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        print "T next", t_next
        self.assertEqual("Tue Jul 13 16:30:00 2010", t_next)

        # Now we add this timeperiod an exception
        t2 = Timeperiod()
        t2.timeperiod_name = 'T2'
        t2.resolve_daterange(t2.dateranges, 'tuesday 00:00-23:58')
        timeperiod.exclude = [t2]
        # We are a bad boy: first time period want a tuesday
        # but exclude do not want it until 23:58. So next is 58 + 1 second :)
        timeperiod.cache = {}
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        self.assertEqual('Tue Jul 13 23:58:01 2010', t_next)

        t_exclude = t2.get_next_valid_time_from_t(july_the_12)
        t_exclude = time.asctime(time.localtime(t_exclude))
        self.assertEqual('Tue Jul 13 00:00:00 2010', t_exclude)

        t_exclude_inv = t2.get_next_invalid_time_from_t(july_the_12)
        t_exclude_inv = time.asctime(time.localtime(t_exclude_inv))
        self.assertEqual('Mon Jul 12 15:00:00 2010', t_exclude_inv)

    def test_mondayweek_timeperiod_with_exclude(self):
        """
        Test monday week timeperiod with exclude

        :return: None
        """
        self.print_header()
        now = time.time()
        # Get the 12 of july 2010 at 15:00, monday
        july_the_12 = time.mktime(time.strptime("12 Jul 2010 15:00:00", "%d %b %Y %H:%M:%S"))

        # Then a simple same day
        timeperiod = Timeperiod()
        timeperiod.timeperiod_name = 'T1'
        timeperiod.resolve_daterange(timeperiod.dateranges, 'tuesday 3 16:30-24:00')
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        self.assertEqual("Tue Jul 20 16:30:00 2010", t_next)

        # Now we add this timeperiod an exception
        # And a good one: from april (so before) to august (after), and full time.
        # But the 17 is a tuesday, but the 3 of august, so the next 3 tuesday is
        # ..... the Tue Sep 21 :) Yes, we should wait quite a lot :)
        t2 = Timeperiod()
        t2.timeperiod_name = 'T2'
        t2.resolve_daterange(t2.dateranges, 'april 1 - august 23 00:00-24:00')
        timeperiod.exclude = [t2]
        timeperiod.cache = {}
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        self.assertEqual('Tue Sep 21 16:30:00 2010', t_next)

        t_exclude_inv = t2.get_next_invalid_time_from_t(july_the_12)
        t_exclude_inv = time.asctime(time.localtime(t_exclude_inv))
        self.assertEqual('Tue Aug 24 00:00:00 2010', t_exclude_inv)

    def test_mondayweek_timeperiod_with_exclude_bis(self):
        """
        Test monday weeb timeperiod with exclude, version 2 :D

        :return: None
        """
        self.print_header()
        now = time.time()
        # Get the 12 of july 2010 at 15:00, monday
        july_the_12 = time.mktime(time.strptime("12 Jul 2010 15:00:00", "%d %b %Y %H:%M:%S"))

        # Then a funny daterange
        print "Testing daterange", 'tuesday -1 - monday 1  16:30-24:00'
        timerange = Timeperiod()
        timerange.timeperiod_name = 'T1'
        timerange.resolve_daterange(timerange.dateranges, 'tuesday -1 - monday 1  16:30-24:00')
        t_next = timerange.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        print "Next without exclude", t_next
        self.assertEqual("Tue Jul 27 16:30:00 2010", t_next)

        # Now we add this timeperiod an exception
        # And a good one: from april (so before) to august (after), and full time.
        # But the 27 is now not possible? So what next? Add a month!
        # last tuesday of august, the 31 :)
        t2 = Timeperiod()
        t2.timeperiod_name = 'T2'
        t2.resolve_daterange(t2.dateranges, 'april 1 - august 16 00:00-24:00')
        timerange.exclude = [t2]
        timerange.cache = {}
        t_next = timerange.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        self.assertEqual('Tue Aug 31 16:30:00 2010', t_next)

        t_exclude = t2.get_next_valid_time_from_t(july_the_12)
        t_exclude = time.asctime(time.localtime(t_exclude))
        self.assertEqual('Mon Jul 12 15:00:00 2010', t_exclude)

        t_exclude_inv = t2.get_next_invalid_time_from_t(july_the_12)
        t_exclude_inv = time.asctime(time.localtime(t_exclude_inv))
        self.assertEqual('Tue Aug 17 00:00:00 2010', t_exclude_inv)

    def test_mondayweek_timeperiod_with_exclude_and_multiple_daterange(self):
        """
        Test monday week timeperiod with exclude multiple dateranges

        :return: None
        """
        self.print_header()
        now = time.time()
        # Get the 12 of july 2010 at 15:00, monday
        july_the_12 = time.mktime(time.strptime("12 Jul 2010 15:00:00", "%d %b %Y %H:%M:%S"))

        # Then a funny daterange
        print "Testing daterange", 'tuesday -1 - monday 1  16:30-24:00'
        timeperiod = Timeperiod()
        timeperiod.timeperiod_name = 'T1'
        timeperiod.resolve_daterange(timeperiod.dateranges, 'tuesday -1 - monday 1  16:30-24:00')
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        print "Next without exclude", t_next
        self.assertEqual("Tue Jul 27 16:30:00 2010", t_next)

        # Now we add this timeperiod an exception
        # And a good one: from april (so before) to august (after), and full time.
        # But the 27 is nw not possible? So what next? Add a month!
        # But maybe it's not enough? :)
        # The without the 2nd exclude, it's the Tues Aug 31, but it's inside
        # saturday -1 - monday 1 because saturday -1 is the 28 august, so no.
        # in september saturday -1 is the 25, and tuesday -1 is 28, so still no
        # A month again! So now tuesday -1 is 26 and saturday -1 is 30. So ok
        # for this one! that was quite long isn't it?
        t2 = Timeperiod()
        t2.timeperiod_name = 'T2'
        t2.resolve_daterange(t2.dateranges, 'april 1 - august 16 00:00-24:00')
        t2.resolve_daterange(t2.dateranges, 'saturday -1 - monday 1  16:00-24:00')
        timeperiod.exclude = [t2]
        timeperiod.cache = {}
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        self.assertEqual('Tue Oct 26 16:30:00 2010', t_next)

        t_exclude_inv = t2.get_next_invalid_time_from_t(july_the_12)
        t_exclude_inv = time.asctime(time.localtime(t_exclude_inv))
        self.assertEqual('Tue Aug 17 00:00:00 2010', t_exclude_inv)

    def test_monweekday_timeperiod_with_exclude(self):
        """
        Test mon week day timeperiod with exclude

        :return: None
        """
        self.print_header()
        now = time.time()
        # Get the 12 of july 2010 at 15:00, monday
        july_the_12 = time.mktime(time.strptime("12 Jul 2010 15:00:00", "%d %b %Y %H:%M:%S"))

        # Then a funny daterange
        print "Testing daterange", 'tuesday -1 july - monday 1 september  16:30-24:00'
        timeperiod = Timeperiod()
        timeperiod.timeperiod_name = 'T1'
        timeperiod.resolve_daterange(timeperiod.dateranges,
                                     'tuesday -1 july - monday 1 september  16:30-24:00')
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        print "Next without exclude", t_next
        self.assertEqual("Tue Jul 27 16:30:00 2010", t_next)

        # Now we add this timeperiod an exception
        # and from april (before) to august monday 3 (monday 16 august),
        t2 = Timeperiod()
        t2.timeperiod_name = 'T2'
        t2.resolve_daterange(t2.dateranges, 'thursday 1 april - monday 3 august 00:00-24:00')
        timeperiod.exclude = [t2]
        timeperiod.cache = {}
        t_next = timeperiod.get_next_valid_time_from_t(july_the_12)
        t_next = time.asctime(time.localtime(t_next))
        self.assertEqual('Tue Aug 17 16:30:00 2010', t_next)

    def test_dayweek_exclusion_timeperiod(self):
        """
        Test week day timeperiod with exclusion

        :return: None
        """
        self.print_header()
        now = time.time()
        # Get the 13 of july 2010 at 15:00, tuesday
        july_the_13 = time.mktime(time.strptime("13 Jul 2010 15:00:00", "%d %b %Y %H:%M:%S"))
        print july_the_13

        # Now we add this timeperiod an exception
        timeperiod = Timeperiod()

        timeperiod.resolve_daterange(timeperiod.dateranges, 'monday 00:00-24:00')
        timeperiod.resolve_daterange(timeperiod.dateranges, 'tuesday 00:00-24:00')
        timeperiod.resolve_daterange(timeperiod.dateranges, 'wednesday 00:00-24:00')

        t2 = Timeperiod()
        t2.timeperiod_name = ''
        t2.resolve_daterange(t2.dateranges, 'tuesday 00:00-24:00')
        timeperiod.exclude = [t2]

        t_next = timeperiod.get_next_valid_time_from_t(july_the_13)
        t_next = time.asctime(time.localtime(t_next))
        print "T next", t_next
        self.assertEqual("Wed Jul 14 00:00:00 2010", t_next)

        july_the_12 = time.mktime(time.strptime("12 Jul 2010 15:00:00", "%d %b %Y %H:%M:%S"))
        t_inv = timeperiod.get_next_invalid_time_from_t(july_the_12)
        t_inv = time.asctime(time.localtime(t_inv))
        self.assertEqual('Tue Jul 13 00:00:00 2010', t_inv)

    def test_dayweek_exclusion_timeperiod_with_day_range(self):
        """
        Test day week timeperiod with exclude day range

        :return: None
        """
        self.print_header()
        # Get the 13 of july 2010 at 15:00, tuesday
        july_the_13 = time.mktime(time.strptime("13 Jul 2010 15:00:00", "%d %b %Y %H:%M:%S"))
        print july_the_13

        timeperiod = Timeperiod()
        timeperiod.resolve_daterange(timeperiod.dateranges, '2010-03-01 - 2020-03-01 00:00-24:00')

        # Now we add this timeperiod an exception
        t2 = Timeperiod()
        t2.timeperiod_name = ''
        t2.resolve_daterange(t2.dateranges, 'tuesday 00:00-24:00')
        timeperiod.exclude = [t2]

        t_next = timeperiod.get_next_valid_time_from_t(july_the_13)
        t_next = time.asctime(time.localtime(t_next))
        print "T next", t_next
        self.assertEqual("Wed Jul 14 00:00:00 2010", t_next)

    def test_issue_1385(self):
        """
        https://github.com/naparuba/shinken/issues/1385
        """
        self.print_header()
        tp = Timeperiod()
        tp.timeperiod_name = 'mercredi2-22-02'
        tp.resolve_daterange(tp.dateranges, 'wednesday 2              00:00-02:00,22:00-24:00')
        tp.resolve_daterange(tp.dateranges, 'thursday 2                00:00-02:00,22:00-24:00')

        valid_times = (
            (2014, 11, 12, 1, 0),  # second wednesday of november @ 01:00
            (2014, 11, 12, 23, 0),  # same @23:00
            (2014, 11, 13, 0, 0),  # second thursday @ 00:00
            # in december:
            (2014, 12, 10, 1, 0),  # second wednesday @ 01:00
            (2014, 12, 10, 23, 0),  # second wednesday @ 23:00
            (2014, 12, 11, 1, 0),  # second thursday @ 01:00
            (2014, 12, 11, 23, 0),  # second thursday @ 23:00
        )
        for valid in valid_times:
            dt = datetime.datetime(*valid)
            valid_tm = time.mktime(dt.timetuple())
            self.assertTrue(tp.is_time_valid(valid_tm))

        invalid_times = (
            (2014, 11, 12, 3, 0),  # second wednesday of november @ 03:00
            (2014, 11, 3, 1, 0),  # first wednesday ..
            (2014, 11, 4, 1, 0),  # first thursday
            (2014, 11, 17, 1, 0),  # third monday
            (2014, 11, 18, 1, 0),  # third tuesday
            # in december:
            (2014, 12, 5, 3, 0),  # first friday
            (2014, 12, 17, 1, 0),  # third wednesday
            (2014, 12, 18, 1, 0),  # third thursday
            (2014, 12, 24, 1, 0),  # fourth wednesday
            (2014, 12, 25, 1, 0),  # fourth thursday
            (2014, 12, 31, 1, 0),
        )
        for invalid in invalid_times:
            dt = datetime.datetime(*invalid)
            invalid_tm = time.mktime(dt.timetuple())
            self.assertFalse(tp.is_time_valid(invalid_tm))

    def test_timeperiod_multiple_monday(self):
        """
        Test with multiple monday

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_timeperiods.cfg')
        tp = self.schedulers['scheduler-master'].sched.timeperiods.find_by_name("us-holidays")
        self.assertEqual(7, len(tp.dateranges))
        mydateranges = []
        for daterange in tp.dateranges:
            mydateranges.append({
                'smon': daterange.smon,
                'smday': daterange.smday,
                'swday': daterange.swday,
                'swday_offset': daterange.swday_offset
            })
        ref = [
            {
                'smon': 1,
                'smday': 1,
                'swday': 0,
                'swday_offset': 0
            },
            {
                'smon': 5,
                'smday': 0,
                'swday': 0,
                'swday_offset': -1
            },
            {
                'smon': 7,
                'smday': 4,
                'swday': 0,
                'swday_offset': 0
            },
            {
                'smon': 9,
                'smday': 0,
                'swday': 0,
                'swday_offset': 1
            },
            {
                'smon': 11,
                'smday': 0,
                'swday': 3,
                'swday_offset': -1
            },
            {
                'smon': 12,
                'smday': 25,
                'swday': 0,
                'swday_offset': 0
            },
            {
                'smon': 7,
                'smday': 14,
                'swday': 0,
                'swday_offset': 0
            },
        ]
        self.assertItemsEqual(ref, mydateranges)

if __name__ == '__main__':
    unittest.main()
