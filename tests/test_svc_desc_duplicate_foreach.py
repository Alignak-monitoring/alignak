#!/usr/bin/env python
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
#  Copyright (C) 2012:
#     Hartmut Goebel <h.goebel@crazy-compilers.com>
#

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
Test service definition duplicate for each ...
"""

import pytest
from .alignak_test import AlignakTest
from alignak.util import generate_key_value_sequences, KeyValueSyntaxError


class TestServiceDescriptionDuplicateForEach(AlignakTest):

    def setUp(self):
        super(TestServiceDescriptionDuplicateForEach, self).setUp()

        self.setup_with_file('cfg/cfg_service_description_duplicate_foreach.cfg')
        self._sched = self._scheduler

    def test_simple_get_key_value_sequence(self):
        rsp = list(generate_key_value_sequences("1", "default42"))
        expected = [
            {'VALUE': 'default42', 'VALUE1': 'default42', 'KEY': '1'},
        ]
        assert expected == rsp

    def test_not_simple_get_key_value_sequence(self):
        rsp = list(generate_key_value_sequences("1  $(val1)$, 2 $(val2)$ ", "default42"))
        expected = [
            {'VALUE': 'val1', 'VALUE1': 'val1', 'KEY': '1'},
            {'VALUE': 'val2', 'VALUE1': 'val2', 'KEY': '2'},
        ]
        assert expected == rsp

    def test_all_duplicate_ok(self):
        host = self._sched.hosts.find_by_name("my_host")
        services_desc = set(self._sched.services[s].service_description for s in host.services)
        expected = set(['Generated Service %s' % i for i in range(1, 4)])
        assert expected == services_desc

    def test_complex(self):
        rsp = list(generate_key_value_sequences('Unit [1-6] Port [0-46]$(80%!90%)$,Unit [1-6] Port 47$(80%!90%)$', ''))
        assert 288 == len(rsp)

    def test_syntax_error_bad_empty_value(self):
        generator = generate_key_value_sequences('', '')
        with pytest.raises(KeyValueSyntaxError) as ctx:
            list(generator)
        assert ctx.value.args[0] == "At least one key must be present"

    def test_syntax_error_bad_empty_value_with_comma(self):
        generator = generate_key_value_sequences(',', '')
        with pytest.raises(KeyValueSyntaxError) as ctx:
            list(generator)
        assert ctx.value.args[0] == "At least one key must be present"

    def test_syntax_error_bad_value(self):
        generator = generate_key_value_sequences("key $(but bad value: no terminating dollar sign)", '')
        with pytest.raises(KeyValueSyntaxError) as ctx:
            list(generator)
        assert ctx.value.args[0] == "\'key $(but bad value: no terminating dollar sign)\' " \
                                        "is an invalid key(-values) pattern"







