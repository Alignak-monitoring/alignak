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
#
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     Jean Gabes, naparuba@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
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

"""
Test alignak.property
"""


import alignak
from alignak.property import NONE_OBJECT

from alignak_test import AlignakTest, unittest



class PropertyTests:
    """Common tests for all property classes"""

    def setUp(self):
        pass

    def test_no_default_value(self):
        p = self.prop_class()
        self.assertIs(p.default, NONE_OBJECT)
        self.assertFalse(p.has_default)
        self.assertTrue(p.required)

    def test_default_value(self):
        default_value = object()
        p = self.prop_class(default=default_value)
        self.assertIs(p.default, default_value)
        self.assertTrue(p.has_default)
        self.assertFalse(p.required)

    def test_fill_brok(self):
        p = self.prop_class()
        self.assertNotIn('full_status', p.fill_brok)
        p = self.prop_class(default='0', fill_brok=['full_status'])
        self.assertIn('full_status', p.fill_brok)

    def test_unused(self):
        p = self.prop_class()
        self.assertFalse(p.unused)


#AlignakTest

class TestBoolProp(PropertyTests, AlignakTest):
    """Test the BoolProp class"""

    prop_class = alignak.property.BoolProp

    def test_pythonize(self):
        p = self.prop_class()
        # allowed strings for `True`
        self.assertEqual(p.pythonize("1"), True)
        self.assertEqual(p.pythonize("yes"), True)
        self.assertEqual(p.pythonize("true"), True)
        self.assertEqual(p.pythonize("on"), True)
        self.assertEqual(p.pythonize(["off", "on"]), True)
        # allowed strings for `False`
        self.assertEqual(p.pythonize("0"), False)
        self.assertEqual(p.pythonize("no"), False)
        self.assertEqual(p.pythonize("false"), False)
        self.assertEqual(p.pythonize("off"), False)
        self.assertEqual(p.pythonize(["on", "off"]), False)



class TestIntegerProp(PropertyTests, AlignakTest):
    """Test the IntegerProp class"""

    prop_class = alignak.property.IntegerProp

    def test_pythonize(self):
        p = self.prop_class()
        self.assertEqual(p.pythonize("1"), 1)
        self.assertEqual(p.pythonize("0"), 0)
        self.assertEqual(p.pythonize("1000.33"), 1000)
        self.assertEqual(p.pythonize(["2000.66", "1000.33"]), 1000)


class TestFloatProp(PropertyTests, AlignakTest):
    """Test the FloatProp class"""

    prop_class = alignak.property.FloatProp

    def test_pythonize(self):
        p = self.prop_class()
        self.assertEqual(p.pythonize("1"), 1.0)
        self.assertEqual(p.pythonize("0"), 0.0)
        self.assertEqual(p.pythonize("1000.33"), 1000.33)
        self.assertEqual(p.pythonize(["2000.66", "1000.33"]), 1000.33)


class TestStringProp(PropertyTests, AlignakTest):
    """Test the StringProp class"""

    prop_class = alignak.property.StringProp

    def test_pythonize(self):
        p = self.prop_class()
        self.assertEqual(p.pythonize("1"), "1")
        self.assertEqual(p.pythonize("yes"), "yes")
        self.assertEqual(p.pythonize("0"), "0")
        self.assertEqual(p.pythonize("no"), "no")
        self.assertEqual(p.pythonize(["yes", "no"]), "no")


class TestCharProp(PropertyTests, AlignakTest):
    """Test the CharProp class"""

    prop_class = alignak.property.CharProp

    def test_pythonize(self):
        p = self.prop_class()
        self.assertEqual(p.pythonize("c"), "c")
        self.assertEqual(p.pythonize("cxxxx"), "c")
        self.assertEqual(p.pythonize(["bxxxx", "cxxxx"]), "c")
        # this raises IndexError. is this intented?
        ## self.assertEqual(p.pythonize(""), "")


class TestPathProp(TestStringProp):
    """Test the PathProp class"""

    prop_class = alignak.property.PathProp

    # As of now, PathProp is a subclass of StringProp without any
    # relevant change. So no further tests are implemented here.


class TestConfigPathProp(TestStringProp):
    """Test the ConfigPathProp class"""

    prop_class = alignak.property.ConfigPathProp

    # As of now, ConfigPathProp is a subclass of StringProp without
    # any relevant change. So no further tests are implemented here.


class TestListProp(PropertyTests, AlignakTest):
    """Test the ListProp class"""

    prop_class = alignak.property.ListProp

    def test_pythonize(self):
        p = self.prop_class()
        self.assertEqual(p.pythonize(""), [])
        self.assertEqual(p.pythonize("1,2,3"), ["1", "2", "3"])
        # Default is to split on coma for list also.
        self.assertEquals(p.pythonize(["1,2,3", "4,5,6"]), ["1","2","3", "4","5","6"])

    def test_pythonize_nosplit(self):
        p = self.prop_class(split_on_coma=False)
        self.assertEqual(p.pythonize(""), [])
        self.assertEqual(p.pythonize("1,2,3"), ["1,2,3"])
        # Default is to split on coma for list also.
        self.assertEquals(p.pythonize(["1,2,3", "4,5,6"]), ["1,2,3", "4,5,6"])



class TestLogLevelProp(PropertyTests, AlignakTest):
    """Test the LogLevelProp class"""

    prop_class = alignak.property.LogLevelProp

    def test_pythonize(self):
        p = self.prop_class()
        self.assertEqual(p.pythonize("NOTSET"), 0)
        self.assertEqual(p.pythonize("DEBUG"), 10)
        self.assertEqual(p.pythonize("INFO"), 20)
        self.assertEqual(p.pythonize("WARN"), 30)
        self.assertEqual(p.pythonize("WARNING"), 30)
        self.assertEqual(p.pythonize("ERROR"), 40)
        ## 'FATAL' is not defined in std-module `logging._levelNames`
        #self.assertEqual(p.pythonize("FATAL"), 50)
        self.assertEqual(p.pythonize("CRITICAL"), 50)
        self.assertEqual(p.pythonize(["NOTSET", "CRITICAL"]), 50)


## :todo: fix DictProp error if no `elts_prop` are passed
## class TestDictProp(PropertyTests, AlignakTest):
##     """Test the DictProp class"""
##
##     prop_class = alignak.property.DictProp
##
##     def test_pythonize(self):
##         p = self.prop_class()
##         self.assertEqual(p.pythonize(""), "")


class TestAddrProp(PropertyTests, AlignakTest):
    """Test the AddrProp class"""

    prop_class = alignak.property.AddrProp

    def test_pythonize_with_IPv4_addr(self):
        p = self.prop_class()
        self.assertEqual(p.pythonize("192.168.10.11:445"),
                         {'address': "192.168.10.11",
                          'port': 445})
        # no colon, no port
        self.assertEqual(p.pythonize("192.168.10.11"),
                         {'address': "192.168.10.11"})
        # colon but no port number
        self.assertRaises(ValueError, p.pythonize, "192.168.10.11:")
        # only colon, no addr, no port number
        self.assertRaises(ValueError, p.pythonize, ":")
        # no address, only port number
        self.assertEqual(p.pythonize(":445"),
                         {'address': "",
                          'port': 445})

    def test_pythonize_with_hostname(self):
        p = self.prop_class()
        self.assertEqual(p.pythonize("host_123:445"),
                         {'address': "host_123",
                          'port': 445})
        # no colon, no port
        self.assertEqual(p.pythonize("host_123"),
                         {'address': "host_123"})
        # colon but no port number
        self.assertRaises(ValueError, p.pythonize, "host_123:")
        # only colon, no addr, no port number
        self.assertRaises(ValueError, p.pythonize, ":")
        # no address, only port number
        self.assertEqual(p.pythonize(":445"),
                         {'address': "",
                          'port': 445})
        self.assertEqual(p.pythonize([":444", ":445"]),
                         {'address': "",
                          'port': 445})

    # :fixme: IPv6 addresses are no tested since they are not parsed
    # correcly


if __name__ == '__main__':
    unittest.main()
