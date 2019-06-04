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
"""
This file test the comments (acknowledge, downtimes...).
"""

import time
from .alignak_test import AlignakTest


class TestComments(AlignakTest):
    """
    This class test the comments (acknowledge, downtimes...).
    """
    def setUp(self):
        super(TestComments, self).setUp()
        self.setup_with_file('cfg/cfg_default.cfg',
                             dispatching=True)

    def test_host_acknowledge(self):
        """Test add / delete comment for acknowledge on host

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert host.state == "DOWN"
        assert host.state_type == "SOFT"
        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert host.state == "DOWN"
        assert host.state_type == "SOFT"
        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        time.sleep(0.1)
        assert host.state == "DOWN"
        assert host.state_type == "HARD"

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM;{1};{2};{3};{4};{5};{6}\n".\
            format(int(now), host.host_name, 2, 0, 1, 'darth vader', 'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        # time.sleep(0.1)

        assert host.problem_has_been_acknowledged
        # we must have a comment
        assert len(host.comments) == 1

        # Test with a new acknowledge, will replace previous
        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM;{1};{2};{3};{4};{5};{6}\n".\
            format(int(now), host.host_name, 2, 0, 1, 'darth vader', 'normal new process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        # time.sleep(0.1)

        # we must have a comment
        assert len(host.comments) == 1
        for comment_id in host.comments:
            assert host.comments[comment_id].comment == 'normal new process'

        self.scheduler_loop(1, [[host, 0, 'UP']])
        # time.sleep(0.1)

        # we must have no comment (the comment must be deleted like the acknowledge)
        assert not host.problem_has_been_acknowledged
        assert len(host.comments) == 0

    def test_host_acknowledge_expire(self):
        """Test add / delete comment for acknowledge on host with expire

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        # time.sleep(0.1)
        assert "DOWN" == host.state
        assert "SOFT" == host.state_type

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_HOST_PROBLEM_EXPIRE;{1};{2};{3};{4};{5};{6};{7}\n".\
            format(int(now), host.host_name, 2, 0, 1, int(now) + 3, 'darth vader', 'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        # time.sleep(0.1)

        assert host.problem_has_been_acknowledged
        # we must have a comment
        assert len(host.comments) == 1

        time.sleep(3)
        self.scheduler_loop(1, [[host, 2, 'DOWN']])
        # time.sleep(0.1)

        # we must have no comment (the comment must be deleted like the acknowledge)
        assert not host.problem_has_been_acknowledged
        assert len(host.comments) == 0

    def test_service_acknowledge(self):
        """Test add / delete comment for acknowledge on service

        :return: None
        """
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0",
                                                                              "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults
        svc.max_check_attempts = 3

        self.scheduler_loop(1, [[host, 0, 'UP'], [svc, 0, 'OK']])
        # time.sleep(0.1)

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        # time.sleep(0.1)
        assert "WARNING" == svc.state
        assert "SOFT" == svc.state_type

        now = time.time()
        cmd = "[{0}] ACKNOWLEDGE_SVC_PROBLEM;{1};{2};{3};{4};{5};{6};{7}\n". \
            format(int(now), host.host_name, svc.service_description, 2, 0, 1, 'darth vader',
                   'normal process')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[svc, 1, 'WARNING']])
        # time.sleep(0.1)

        assert svc.problem_has_been_acknowledged
        # we must have a comment
        assert len(svc.comments) == 1

        self.scheduler_loop(1, [[svc, 0, 'OK']])
        # time.sleep(0.1)

        # we must have no comment (the comment must be deleted like the acknowledge)
        assert not svc.problem_has_been_acknowledged
        assert len(svc.comments) == 0

    def test_host_downtime(self):
        pass

    def test_host_comment(self):
        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        self.scheduler_loop(1, [[host, 0, 'UP']])
        # time.sleep(0.1)

        now = time.time()
        cmd = "[{0}] ADD_HOST_COMMENT;{1};{2};{3};{4}\n". \
            format(int(now), host.host_name, 1, 'darth vader', 'nice comment')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[host, 0, 'UP']])
        # time.sleep(0.1)

        # we must have a comment
        assert len(host.comments) == 1

        # comment number 2
        now = time.time()
        cmd = "[{0}] ADD_HOST_COMMENT;{1};{2};{3};{4}\n". \
            format(int(now), host.host_name, 1, 'emperor', 'nice comment yes')
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[host, 0, 'UP']])
        # time.sleep(0.1)

        assert len(host.comments) == 2

        # del all comments of the host
        now = time.time()
        cmd = "[{0}] DEL_ALL_HOST_COMMENTS;{1}\n". \
            format(int(now), host.host_name)
        self._scheduler.run_external_commands([cmd])

        self.scheduler_loop(1, [[host, 0, 'UP']])
        # time.sleep(0.1)

        assert len(host.comments) == 0
