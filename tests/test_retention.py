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

import os
import time
import json
import pprint
from .alignak_test import AlignakTest

from alignak.misc.serialization import unserialize


class TestRetention(AlignakTest):
    """
    This class test retention
    """
    def setUp(self):
        super(TestRetention, self).setUp()


    def test_default_is_disabled_retention(self):
        """ Test that default configuration is retention disabled

        :return: None
        """
        self.setup_with_file('cfg/cfg_default.cfg')
        # Default configuration has no retention configured
        assert self._scheduler.pushed_conf.retention_update_interval == 0

        expected_logs = [
        ]
        self.check_monitoring_events_log(expected_logs)

    def test_retention_enabled(self):
        """ Test that when retention is enabled whe have a log

        :return: None
        """
        self.setup_with_file('cfg/cfg_default_retention.cfg')
        # Default configuration has no retention configured
        assert self._scheduler.pushed_conf.retention_update_interval == 5

        self.scheduler_loop(5, [])
        time.sleep(1)

        expected_logs = [
            ('info', 'RETENTION LOAD: scheduler-master'),
            # ('info', 'CURRENT HOST STATE: test_router_0;UP;HARD;1;UP and OK'),
            # ('error', 'CURRENT HOST STATE: test_host_0;DOWN;HARD;3;DOWN!'),
            # ('warning', 'CURRENT SERVICE STATE: test_host_0;test_ok_0;UNREACHABLE;HARD;0;'),
            # ('info', 'HOST DOWNTIME ALERT: test_host_0;STOPPED; Host has exited from a period of scheduled downtime'),
            # ('info', 'HOST NOTIFICATION: test_contact;test_host_0;DOWNTIMEEND (DOWN);1;notify-host;DOWN!'),
        ]
        self.check_monitoring_events_log(expected_logs, assert_length=False)

    def test_scheduler_retention(self):
        """ Test save and restore retention data

        :return: None
        """
        # Delete a potential existing retention file...
        if os.path.exists('/tmp/test_host_0.json'):
            os.remove('/tmp/test_host_0.json')
        if os.path.exists('/tmp/test_router_0.json'):
            os.remove('/tmp/test_router_0.json')

        self.setup_with_file('cfg/cfg_default_retention.cfg')
        self.show_logs()
        # Retention is configured
        assert self._scheduler.pushed_conf.retention_update_interval == 5
        # assert self._scheduler.pushed_conf.tick_update_retention == 5

        router = self._scheduler.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.event_handler_enabled = False

        host = self._scheduler.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[router, 0, 'UP and OK']])
        self.scheduler_loop(3, [[host, 2, 'DOWN!']])
        time.sleep(1.0)
        self.scheduler_loop(1)
        # time.sleep(1.0)
        # self.scheduler_loop(1)

        assert host.state_type == 'HARD'
        assert host.state == 'DOWN'
        assert svc.state_type == 'HARD'
        assert svc.state == 'UNREACHABLE'   # Because it is impacted by its host which is DOWN

        now = int(time.time())
        # Scheduler a downtime for the host
        excmd = '[%d] SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;1200;test_contact;My downtime' \
                % (now, now, now + 1200)
        self._scheduler.run_external_commands([excmd])
        self.external_command_loop()
        time.sleep(1.0)
        expected_logs = [
            ("info", "RETENTION LOAD: scheduler-master"),
            ('info', 'CURRENT HOST STATE: test_router_0;UP;HARD;0;'),
            ('info', 'CURRENT HOST STATE: test_host_0;UP;HARD;0;'),
            ('info', 'CURRENT SERVICE STATE: test_host_0;test_ok_0;OK;HARD;0;'),
            ("info", "ACTIVE HOST CHECK: test_router_0;UP;0;UP and OK"),
            ("error", "ACTIVE HOST CHECK: test_host_0;DOWN;0;DOWN!"),
            ("error", "HOST ALERT: test_host_0;DOWN;SOFT;1;DOWN!"),
            ("error", "ACTIVE HOST CHECK: test_host_0;DOWN;1;DOWN!"),
            ("error", "HOST ALERT: test_host_0;DOWN;SOFT;2;DOWN!"),
            ("error", "ACTIVE HOST CHECK: test_host_0;DOWN;2;DOWN!"),
            ("error", "HOST ALERT: test_host_0;DOWN;HARD;3;DOWN!"),
            ("error", "HOST NOTIFICATION: test_contact;test_host_0;DOWN;1;notify-host;DOWN!"),
            ("info", "EXTERNAL COMMAND: [%s] SCHEDULE_HOST_DOWNTIME;test_host_0;%s;%s;1;0;1200;test_contact;My downtime" % (now, now, now + 1200)),
            ("info", "HOST DOWNTIME ALERT: test_host_0;STARTED; Host has entered a period of scheduled downtime"),
            ("info", "HOST ACKNOWLEDGE ALERT: test_host_0;STARTED; Host problem has been acknowledged"),
            ("info", "SERVICE ACKNOWLEDGE ALERT: test_host_0;test_ok_0;STARTED; Service problem has been acknowledged"),
            ("info", "HOST NOTIFICATION: test_contact;test_host_0;DOWNTIMESTART (DOWN);1;notify-host;DOWN!")
        ]
        self.check_monitoring_events_log(expected_logs)
        # The host is DOWN and downtimed...

        host_notifications = []
        print("Notifications:")
        for notification_uuid, notification in host.notifications_in_progress.items():
            print("- %s" % (notification))
            host_notifications.append(notification)
        # Master notification
        # Notification for host problem
        # Notification for host downtime
        assert 3 == len(host.notifications_in_progress)

        host_comments = []
        host_comment_id = None
        print("Comments (host):")
        for comm_uuid, comment in host.comments.items():
            print("- %s" % (comment))
            host_comments.append(comment.comment)
            if comment.entry_type == 4:
                host_comment_id = comment.uuid
        # Comment for host problem
        # Comment for host ack because of the downtime
        assert 2 == len(host.comments)

        service_comments = []
        service_comment_id = None
        print("Comments (service):")
        for comm_uuid, comment in svc.comments.items():
            print("- %s" % (comment))
            service_comments.append(comment.comment)
            if comment.entry_type == 4:
                service_comment_id = comment.uuid
        # Comment for svc ack because of the host downtime
        assert 1 == len(svc.comments)

        assert True == host.problem_has_been_acknowledged
        assert host.acknowledgement.__dict__ == {
            'uuid': host.acknowledgement.uuid,
            'author': 'Alignak',
            'comment': 'Acknowledged because of an host downtime',
            'ref': host.uuid,
            'sticky': True,
            'end_time': 0,
            'notify': 1,
            "comment_id": host_comment_id
        }

        assert True == svc.problem_has_been_acknowledged
        assert svc.acknowledgement.__dict__ == {
            "uuid": svc.acknowledgement.uuid,
            "author": "Alignak",
            "comment": "Acknowledged because of an host downtime",
            "ref": svc.uuid,
            "sticky": False,
            "end_time": 0,
            "notify": True,
            "comment_id": service_comment_id
        }

        # Prepare retention data to be stored
        retention = self._scheduler.get_retention_data()

        assert 'hosts' in retention
        assert 'services' in retention
        print('Hosts retention:')
        for host_name in retention['hosts']:
            print('- %s' % host_name)
        assert len(retention['hosts']) == 2

        print('Services retention:')
        for host_name, service_description in retention['services']:
            print('- %s - %s' % (host_name, service_description))
        assert len(retention['services']) == 1

        print('Services retention:')
        for service in retention['services']:
            print('- %s / %s' % (service[0], service[1]))
        assert len(retention['services']) == 1

        # Test if it can be JSON dumped (serialization...)
        print('Hosts retention:')
        for host_name in retention['hosts']:
            try:
                # print('- %s:' % host_name)
                # pprint.pprint(retention['hosts'][host_name], indent=3)
                t = json.dumps(retention['hosts'][host_name])
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

        self._scheduler.update_recurrent_works_tick({'tick_update_retention': 1})

        # Test that after get retention nothing got broken
        self.scheduler_loop(1, [[host, 2, 'DOWN!']])
        time.sleep(0.1)
        expected_logs += [
            ("info", "RETENTION SAVE: scheduler-master"),
            ("error", "ACTIVE HOST CHECK: test_host_0;DOWN;3;DOWN!"),
        ]
        self.check_monitoring_events_log(expected_logs)
        self.show_logs()
        assert os.path.exists('/tmp/test_host_0.json')
        with open('/tmp/test_host_0.json', "r") as fd:
            retention_check = json.load(fd)
        pprint.pprint(retention_check)
        assert 'name' in retention_check
        assert retention_check['name'] == 'test_host_0'
        assert os.path.exists('/tmp/test_router_0.json')

        # ************** test the restoration of retention ************** #
        # new conf
        self.setup_with_file('cfg/cfg_default_retention.cfg')

        expected_logs = [
            ('info', 'RETENTION LOAD: scheduler-master'),
        ]
        self.check_monitoring_events_log(expected_logs)

        hostn = self._scheduler.hosts.find_by_name("test_host_0")
        hostn.checks_in_progress = []
        hostn.act_depend_of = []  # ignore the router
        hostn.event_handler_enabled = False

        svcn = self._scheduler.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svcn.checks_in_progress = []
        svcn.act_depend_of = []  # no hostchecks on critical checkresults

        # Host and service should be restored with the former states
        assert hostn.state_type == 'HARD'
        assert hostn.state == 'DOWN'
        assert svcn.state_type == 'HARD'
        assert svcn.state == 'UNREACHABLE'

        assert hostn.last_state == 'DOWN'
        assert svcn.last_state == 'PENDING' # Never tested!

        # Not the same identifier
        assert host.uuid != hostn.uuid

        self.scheduler_loop(1, [[hostn, 0, 'UP'], [svcn, 1, 'WARNING']])
        time.sleep(1.0)
        self.scheduler_loop(1)

        expected_logs += [
            ('info', 'CURRENT HOST STATE: test_router_0;UP;HARD;1;UP and OK'),
            ('error', 'CURRENT HOST STATE: test_host_0;DOWN;HARD;3;DOWN!'),
            ('warning', 'CURRENT SERVICE STATE: test_host_0;test_ok_0;UNREACHABLE;HARD;0;'),
            ('warning', 'ACTIVE SERVICE CHECK: test_host_0;test_ok_0;WARNING;0;WARNING'),
            ('info', 'SERVICE ACKNOWLEDGE ALERT: test_host_0;test_ok_0;EXPIRED; Service problem acknowledge expired'),
            ('warning', 'SERVICE ALERT: test_host_0;test_ok_0;WARNING;HARD;0;WARNING'),
            ('warning', 'SERVICE EVENT HANDLER: test_host_0;test_ok_0;WARNING;HARD;0;eventhandler'),
            ('info', 'ACTIVE HOST CHECK: test_host_0;UP;3;UP'),
            ('info', 'HOST ACKNOWLEDGE ALERT: test_host_0;EXPIRED; Host problem acknowledge expired'),
            ('info', 'HOST ALERT: test_host_0;UP;HARD;3;UP'),
        ]
        self.check_monitoring_events_log(expected_logs)

        assert 2 == len(hostn.comments)
        assert 2 == len(hostn.notifications_in_progress)

        # check downtimes (only for host and not for service)
        print("Host downtimes: ")
        for downtime in host.downtimes:
            print('- %s' % (downtime))
        print("HostN downtimes: ")
        for downtime in hostn.downtimes:
            print('- %s' % (downtime))
        assert list(host.downtimes) == list(hostn.downtimes)
        for down_uuid, downtime in hostn.downtimes.items():
            assert 'My downtime' == downtime.comment

        # check notifications
        print("Host notifications: ")
        for notif_uuid in host.notifications_in_progress:
            print('- %s / %s' % (notif_uuid, host.notifications_in_progress[notif_uuid]))
        print("HostN notifications: ")
        for notif_uuid in hostn.notifications_in_progress:
            print('- %s / %s' % (notif_uuid, hostn.notifications_in_progress[notif_uuid]))
        for notif_uuid, notification in hostn.notifications_in_progress.items():
            print(notif_uuid, notification)
            if notif_uuid not in host.notifications_in_progress:
                continue
            assert host.notifications_in_progress[notif_uuid].command == \
                   notification.command
            assert host.notifications_in_progress[notif_uuid].t_to_go == \
                             notification.t_to_go
        # Notifications: host ack, service ack, host downtime
        assert 2 == len(hostn.notifications_in_progress)

        # check comments for host
        assert len(host.comments) == len(hostn.comments)
        commentshn = []
        for comm_uuid, comment in hostn.comments.items():
            commentshn.append(comment.comment)
        # Compare sorted comments because dictionairies are not ordered
        assert sorted(host_comments) == sorted(commentshn)

        # check comments for service
        assert len(svc.comments) == len(svcn.comments)
        commentssn = []
        for comm_uuid, comment in svcn.comments.items():
            commentssn.append(comment.comment)
        assert service_comments == commentssn

        # check notified_contacts
        assert isinstance(hostn.notified_contacts, set)
        assert isinstance(svcn.notified_contacts, set)
        assert set([self._scheduler.contacts.find_by_name("test_contact").uuid]) == \
               hostn.notified_contacts_ids
