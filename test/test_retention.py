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
This file test retention
"""

import time
import json
from .alignak_test import AlignakTest

from alignak.misc.serialization import unserialize


class TestRetention(AlignakTest):
    """
    This class test retention
    """
    def setUp(self):
        super(TestRetention, self).setUp()


    def test_scheduler_retention(self):
        """ Test restore retention data

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svc.notification_interval = 0.001
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)
        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        now = time.time()
        # downtime host
        excmd = '[%d] SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;1200;test_contact;My downtime' \
                % (now, now, now + 1200)
        time.sleep(1)
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()

        # # Acknowledge service
        # No more necessary because scheduling a downtime for an host acknowledges its services
        # excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;' \
        #         'Acknowledge service' % time.time()
        # self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        # self.external_command_loop()

        commentsh = []
        ack_comment_uuid = ''
        for comm_uuid, comment in host.comments.items():
            commentsh.append(comment.comment)

        commentss = []
        for comm_uuid, comment in svc.comments.items():
            commentss.append(comment.comment)
            if comment.entry_type == 4:
                ack_comment_uuid = comment.uuid

        assert True == svc.problem_has_been_acknowledged
        assert svc.acknowledgement.__dict__ == {
            "comment": "Acknowledged because of an host downtime",
            "uuid": svc.acknowledgement.uuid,
            "ref": svc.uuid,
            "author": "Alignak",
            "sticky": False,
            "end_time": 0,
            "notify": True,
            "comment_id": ack_comment_uuid
        }

        retention = self._scheduler.get_retention_data()

        assert 'hosts' in retention
        assert 'services' in retention
        assert len(retention['hosts']) == 2
        assert len(retention['services']) == 1

        # Test if can json.dumps (serialize)
        for hst in retention['hosts']:
            try:
                t = json.dumps(retention['hosts'][hst])
            except Exception as err:
                assert False, 'Json dumps impossible: %s' % str(err)
            assert "notifications_in_progress" in t
            assert "downtimes" in t
            assert "acknowledgement" in t

        for service in retention['services']:
            try:
                t = json.dumps(retention['services'][service])
            except Exception as err:
                assert False, 'Json dumps impossible: %s' % str(err)
            assert "notifications_in_progress" in t
            assert "downtimes" in t
            assert "acknowledgement" in t

        # Test after get retention not have broken something
        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        # ************** test the restoration of retention ************** #
        # new conf
        self.setup_with_file('cfg/cfg_default.cfg')
        hostn = self._scheduler.hosts.find_by_name("test_host_0")
        hostn.checks_in_progress = []
        hostn.act_depend_of = []  # ignore the router
        hostn.event_handler_enabled = False

        svcn = self._scheduler.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svcn.notification_interval = 0.001
        svcn.checks_in_progress = []
        svcn.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[hostn, 0, 'UP'], [svcn, 1, 'WARNING']])
        time.sleep(0.1)
        assert 0 == len(hostn.comments)
        assert 0 == len(hostn.notifications_in_progress)

        self._main_broker.broks = {}
        self._scheduler.restore_retention_data(retention)

        assert hostn.last_state == 'DOWN'
        assert svcn.last_state == 'CRITICAL'

        assert host.uuid != hostn.uuid

        # check downtimes (only for host and not for service)
        assert list(host.downtimes) == list(hostn.downtimes)
        for down_uuid, downtime in hostn.downtimes.items():
            assert 'My downtime' == downtime.comment

        # check notifications
        for notif_uuid, notification in hostn.notifications_in_progress.items():
            assert host.notifications_in_progress[notif_uuid].command == \
                             notification.command
            assert host.notifications_in_progress[notif_uuid].t_to_go == \
                             notification.t_to_go
        # Notifications: host ack, service ack, host downtime
        assert 3 == len(hostn.notifications_in_progress)

        # check comments for host
        assert len(host.comments) == len(hostn.comments)
        commentshn = []
        for comm_uuid, comment in hostn.comments.items():
            commentshn.append(comment.comment)
        # Compare sorted comments because dictionairies are not ordered
        assert sorted(commentsh) == sorted(commentshn)

        # check comments for service
        assert len(svc.comments) == len(svcn.comments)
        commentssn = []
        for comm_uuid, comment in svcn.comments.items():
            commentssn.append(comment.comment)
        assert commentss == commentssn

        # check notified_contacts
        assert isinstance(hostn.notified_contacts, set)
        assert isinstance(svcn.notified_contacts, set)
        assert set([self._scheduler.contacts.find_by_name("test_contact").uuid]) == \
                         hostn.notified_contacts

        # No brok for monitoring logs...
        # # Retention load monitoring log
        # # We got 'monitoring_log' broks for logging to the monitoring logs...
        # monitoring_logs = []
        # for brok in self._main_broker.broks.values():
        #     if brok.type == 'monitoring_log':
        #         data = unserialize(brok.data)
        #         monitoring_logs.append((data['level'], data['message']))
        #
        # expected_logs = [
        #     (u'info', u'RETENTION LOAD: scheduler-master scheduler')
        # ]
        # for log_level, log_message in expected_logs:
        #     assert (log_level, log_message) in monitoring_logs
