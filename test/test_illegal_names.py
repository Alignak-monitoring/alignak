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
#     Jean Gabes, naparuba@gmail.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Grégory Starck, g.starck@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     Sebastien Coavoux, s.coavoux@free.fr

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
This file test illegal characters in configuration

"""

from alignak_test import AlignakTest


class TestConfig(AlignakTest):
    """
    This class test illegal characters in configuration
    """
    # setUp is inherited from AlignakTest

    def test_illegal_character_in_names(self):
        """ Test illegal characters in host_name

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        illegal_characts = self.arbiter.conf.illegal_object_name_chars
        print "Illegal caracters: %s" % illegal_characts
        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        # should be correct
        assert host.is_correct()

        # Now change the name with incorrect caract
        for charact in illegal_characts:
            host.host_name = 'test_host_0' + charact
            # and Now I want an incorrect here
            assert False == host.is_correct()

        # test special cases manually to be sure
        for charact in ['!']:
            host.host_name = 'test_host_0' + charact
            # and Now I want an incorrect here
            assert False == host.is_correct()
