#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

from alignak_test import AlignakTest


class TestConfig(AlignakTest):

    def setUp(self):
        pass # force no setUp for this class.

    def test_bad_template_use_itself(self):
        self.setup_with_file(['etc/bad_template_use_itself.cfg'])
        self.assertIn(u"Host u'bla' use/inherits from itself ! Imported from: etc/bad_template_use_itself.cfg:1",
                      self.conf.hosts.configuration_errors)

    def test_bad_host_use_undefined_template(self):
        self.setup_with_file(['etc/bad_host_use_undefined_template.cfg'])
        self.assertIn(u"Host u'bla' use/inherit from an unknown template (u'undefined') ! Imported from: etc/bad_host_use_undefined_template.cfg:2",
                      self.conf.hosts.configuration_warnings)
