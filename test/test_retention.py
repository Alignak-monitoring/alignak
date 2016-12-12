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
"""
This file test retention
"""

import time
import json
from alignak_test import AlignakTest


class Testretention(AlignakTest):
    """
    This class test retention
    """

    def test_scheduler_retention(self):
        """ Test restore retention data

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_default.cfg')

        host = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = []  # ignore the router
        host.event_handler_enabled = False

        svc = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
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
                % (now, now + 120, now + 1200)
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()

        # Acknowledge service
        excmd = '[%d] ACKNOWLEDGE_SVC_PROBLEM;test_host_0;test_ok_0;2;1;1;Big brother;' \
                'Acknowledge service' % time.time()
        self.schedulers['scheduler-master'].sched.run_external_command(excmd)
        self.external_command_loop()
        assert True == svc.problem_has_been_acknowledged

        comments = []
        for comm_uuid, comment in self.schedulers['scheduler-master'].sched.comments.iteritems():
            comments.append(comment.comment)

        retention = self.schedulers['scheduler-master'].sched.get_retention_data()

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
        for service in retention['services']:
            try:
                t = json.dumps(retention['services'][service])
            except Exception as err:
                assert False, 'Json dumps impossible: %s' % str(err)

        # Test after get retention not have broken something
        self.scheduler_loop(1, [[host, 2, 'DOWN'], [svc, 2, 'CRITICAL']])
        time.sleep(0.1)

        h_dict = {
            'last_time_unreachable': 0, 'last_problem_id': 0, 'check_type': 0, 'in_scheduled_downtime_during_last_check': False, 'last_perf_data': u'', 'last_event_id': 0, 'process_perf_data': True, 'in_hard_unknown_reach_phase': False, 'problem_has_been_acknowledged': False, 'current_notification_number': 1, 'flapping_changes': [True, False, False], 'should_be_scheduled': 1, 'acknowledgement_type': 1, 'last_notification': 0.0, 'check_flapping_recovery_notification': True, 'active_checks_enabled': True, 'last_state': 'DOWN', 'latency': 0, 'passive_checks_enabled': True, 'state_before_hard_unknown_reach_phase': u'UP', 'current_event_id': 2, 'last_state_type': 'SOFT', 'last_hard_state_change': 1481525615, 'last_time_up': 0, 'was_in_hard_unknown_reach_phase': False, 'next_chk': 1481525632, 'percent_state_change': 4.1000000000000005,


            'downtimes': [
                {'comment': 'My downtime', 'entry_time': 1481525615, 'activate_me': [], 'uuid': '3ddaf8a793e14c269ee173c71f03bf6e', 'author': 'test_contact', 'start_time': 1481525735,

                 'comment_id': {
                     'comment': 'This host has been scheduled for fixed downtime from 2016-12-12 07:55:35 to 2016-12-12 08:13:35. Notifications for the host will not be sent out during that time period.', 'entry_time': 1481525615, 'comment_type': 1, 'author': '(Alignak)', 'entry_type': 2, 'can_be_deleted': False, 'expires': False, 'persistent': False, 'source': 0, 'expire_time': 0, 'ref': u'e2c43584811d4d97a3af92e73f04ddea'},

                 'trigger_id': '0', 'has_been_triggered': False, 'real_end_time': 1481526815, 'is_in_effect': False, 'duration': 1080, 'ref_type': 'host', 'fixed': True, 'ref': u'e2c43584811d4d97a3af92e73f04ddea', 'can_be_deleted': False, 'end_time': 1481526815}],

            'comments': [{'comment': 'This host has been scheduled for fixed downtime from 2016-12-12 07:55:35 to 2016-12-12 08:13:35. Notifications for the host will not be sent out during that time period.', 'entry_time': 1481525615, 'comment_type': 1, 'author': '(Alignak)', 'entry_type': 2, 'can_be_deleted': False, 'expires': False, 'persistent': False, 'source': 0, 'expire_time': 0, 'ref': u'e2c43584811d4d97a3af92e73f04ddea'}],


            'notifications_in_progress': {'ab029355b93d40a9822036ebf12ec0b4': {'reason_type': 1, 'ack_data': '', 'creation_time': 1481525615.038309, 'command_call': None, 'reactionner_tag': 'None', 's_time': 0.0, 'notification_type': 0, 'contact_name': '', 'end_time': 0, 'type': 'PROBLEM', 'exit_status': 3, 'check_time': 0, 'escalated': False, 'state': 0, 'u_time': 0.0, 'env': {}, 'notif_nb': 2, 'enable_environment_macros': False, 'ack_author': '', 'status': 'scheduled', 'execution_time': 0.0, 'start_time': 0, 'worker': 'none', 't_to_go': 1481525675, 'module_type': 'fork', '_in_timeout': False, 'sched_id': 0, 'uuid': 'ab029355b93d40a9822036ebf12ec0b4', 'service_description': '', 'ref': u'e2c43584811d4d97a3af92e73f04ddea', 'is_a': 'notification', 'contact': None, 'command': 'VOID', 'host_name': u'test_host_0', 'timeout': 30, 'output': '', 'already_start_escalations': []}, '54c84bc7b74046b8be79d5766c41c815': {'reason_type': 1, 'ack_data': '', 'creation_time': 1481525615.050009, 'command_call': {'module_type': u'fork', 'uuid': u'8c3e0d4fcd844ab9a9e923704822b496', 'late_relink_done': False, 'args': [], 'poller_tag': u'', 'reactionner_tag': u'', 'valid': True, 'call': u'notify-host', 'timeout': -1, 'command': {'command_name': u'notify-host', 'use': [], 'display_name': u'notify-host', 'conf_is_correct': True, 'definition_order': 100, 'poller_tag': u'None', 'register': True, 'command_line': u'$USER1$/notifier.pl --hostname $HOSTNAME$ --notificationtype $NOTIFICATIONTYPE$ --hoststate $HOSTSTATE$ --hostoutput $HOSTOUTPUT$ --longdatetime $LONGDATETIME$ --hostattempt $HOSTATTEMPT$ --hoststatetype $HOSTSTATETYPE$', 'name': u'unnamed', 'alias': u'notify-host', 'reactionner_tag': u'None', 'module_type': u'fork', 'imported_from': u'cfg/default/commands.cfg:9', 'timeout': -1, 'plus': {}, 'customs': {}, 'enable_environment_macros': False, 'tags': [], 'uuid': u'7841bb07d0fb406ebd183cb513bf7bfe'}, 'enable_environment_macros': False}, 'reactionner_tag': u'', 's_time': 0.0, 'notification_type': 0, 'contact_name': u'test_contact', 'end_time': 0, 'type': 'PROBLEM', 'exit_status': 3, 'check_time': 0, 'escalated': False, 'state': 0, 'u_time': 0.0, 'env': {'NAGIOS_TOTALSERVICESUNKNOWN': u'0', 'NAGIOS_LONGHOSTOUTPUT': u'', 'NAGIOS_HOSTDURATIONSEC': u'0', 'NAGIOS_HOSTDISPLAYNAME': u'test_host_0', 'NAGIOS_DATE': u'12-12-2016', 'NAGIOS_TOTALHOSTPROBLEMS': u'1', 'NAGIOS_CONTACTPAGER': u'none', 'NAGIOS_HOSTNOTIFICATIONNUMBER': u'1', 'NAGIOS_HOSTACKAUTHOR': u'', 'NAGIOS_LASTHOSTUNREACHABLE': u'0', 'NAGIOS_CONTACTADDRESS1': u'none', 'NAGIOS_MAINCONFIGFILE': u'/home/alignak/alignak/test/cfg/cfg_default.cfg', 'NAGIOS_CONTACTGROUPNAMES': u'another_contact_test,test_contact', 'NAGIOS_HOSTACTIONURL': u'/alignak/pnp/index.php?host=$HOSTNAME$', 'NAGIOS_TOTALHOSTSUNREACHABLEUNHANDLED': u'0', 'NAGIOS_CONTACTNAME': u'test_contact', 'NAGIOS_SERVICENOTIFICATIONID': u'54c84bc7b74046b8be79d5766c41c815', 'NAGIOS_TOTALHOSTSERVICESUNKNOWN': u'0', 'NAGIOS_MAXHOSTATTEMPTS': u'3', 'NAGIOS_ADMINEMAIL': 'n/a', 'NAGIOS_SERVICENOTIFICATIONNUMBER': u'1', 'NAGIOS_HOSTEVENTID': u'2', 'NAGIOS_PREFIX': u'', 'NAGIOS_HOSTSTATE': u'DOWN', 'NAGIOS_HOSTALIAS': u'up_0', 'NAGIOS_LOGFILE': 'n/a', 'NAGIOS_LASTHOSTEVENTID': u'0', 'NAGIOS_HOSTDURATION': u'00h 00m 00s', u'NAGIOS__CONTACTVAR1': u'10', 'NAGIOS_TOTALHOSTSUP': u'1', 'NAGIOS_HOSTADDRESS': u'127.0.0.1', 'NAGIOS_HOSTPROBLEMID': u'2', 'NAGIOS_TOTALSERVICESUNKNOWNUNHANDLED': u'0', 'NAGIOS_HOSTDOWNTIME': u'0', 'NAGIOS_TOTALHOSTSDOWNUNHANDLED': u'1', 'NAGIOS_SERVICEPERFDATAFILE': 'n/a', 'NAGIOS_SHORTDATETIME': u'12-12-2016 07:53:35', 'NAGIOS_PROCESSSTARTTIME': u'n/a', 'NAGIOS_TOTALSERVICESOK': u'0', 'NAGIOS_TOTALSERVICEPROBLEMSUNHANDLED': u'0', 'NAGIOS_SHORTSTATUS': u'D', 'NAGIOS_TOTALHOSTSDOWN': u'1', 'NAGIOS_CONTACTGROUPNAME': u'another_contact_test', 'NAGIOS_TOTALSERVICEPROBLEMS': u'0', u'NAGIOS__HOSTOSLICENSE': u'gpl', 'NAGIOS_TOTALSERVICESWARNINGUNHANDLED': u'0', 'NAGIOS_TOTALHOSTPROBLEMSUNHANDLED': u'1', 'NAGIOS_HOSTEXECUTIONTIME': u'0.0', 'NAGIOS_HOSTACKAUTHORALIAS': u'', 'NAGIOS_NOTIFICATIONTYPE': u'PROBLEM', 'NAGIOS_HOSTPERFDATA': u'', 'NAGIOS_NOTIFICATIONRECIPIENTS': 'n/a', 'NAGIOS_TOTALHOSTSERVICESCRITICAL': u'1', 'NAGIOS_LONGDATETIME': u'Mon 12 Dec 07:53:35 CET 2016', 'NAGIOS_CONTACTADDRESS6': u'none', 'NAGIOS_CONTACTADDRESS4': u'none', 'NAGIOS_CONTACTADDRESS5': u'none', 'NAGIOS_CONTACTADDRESS2': u'none', 'NAGIOS_CONTACTADDRESS3': u'none', 'NAGIOS_LASTHOSTSTATECHANGE': u'1481525614.8', 'NAGIOS_HOSTNOTES': u'', 'NAGIOS_CONTACTALIAS': u'test_contact_alias', 'NAGIOS_HOSTPERCENTCHANGE': u'4.1', 'NAGIOS_EVENTSTARTTIME': u'n/a', 'NAGIOS_NOTIFICATIONISESCALATED': u'False', 'NAGIOS_TOTALSERVICESCRITICALUNHANDLED': u'0', 'NAGIOS_TEMPPATH': 'n/a', 'NAGIOS_NOTIFICATIONAUTHOR': 'n/a', 'NAGIOS_LASTHOSTCHECK': u'1481525615', 'NAGIOS_LASTHOSTUP': u'0', 'NAGIOS_FULLNAME': u'test_host_0', 'NAGIOS_HOSTATTEMPT': u'3', 'NAGIOS_TOTALHOSTSUNREACHABLE': u'0', 'NAGIOS_DOWNTIMEDATAFILE': 'n/a', 'NAGIOS_LASTHOSTPERFDATA': u'', 'NAGIOS_STATUS': u'DOWN', 'NAGIOS_LASTHOSTDOWN': u'1481525615', 'NAGIOS_HOSTREALM': u'All', 'NAGIOS_HOSTGROUPNAMES': u'allhosts,hostgroup_01,up', 'NAGIOS_ADMINPAGER': 'n/a', 'NAGIOS_LASTHOSTSTATE': u'DOWN', 'NAGIOS_LASTHOSTSTATEID': u'0', 'NAGIOS_CONTACTEMAIL': u'nobody@localhost', u'NAGIOS__CONTACTVAR2': u'text', 'NAGIOS_NOTIFICATIONCOMMENT': 'n/a', 'NAGIOS_HOSTNOTESURL': u'/alignak/wiki/doku.php/$HOSTNAME$', 'NAGIOS_STATUSDATAFILE': 'n/a', 'NAGIOS_HOSTACKCOMMENT': u'', 'NAGIOS_HOSTNAME': u'test_host_0', 'NAGIOS_TOTALHOSTSERVICESWARNING': u'0', 'NAGIOS_TIME': u'07:53:35', 'NAGIOS_HOSTACKAUTHORNAME': u'', 'NAGIOS_HOSTSTATEID': u'1', 'NAGIOS_HOSTOUTPUT': u'DOWN', 'NAGIOS_TOTALHOSTSERVICES': u'1', 'NAGIOS_TOTALSERVICESWARNING': u'0', 'NAGIOS_HOSTBUSINESSIMPACT': u'2', 'NAGIOS_TOTALHOSTSERVICESOK': u'0', u'NAGIOS__HOSTOSTYPE': u'gnulinux', 'NAGIOS_NOTIFICATIONAUTHORNAME': 'n/a', 'NAGIOS_LASTHOSTPROBLEMID': u'0', 'NAGIOS_HOSTNOTIFICATIONID': u'54c84bc7b74046b8be79d5766c41c815', 'NAGIOS_HOSTGROUPNAME': u'All Hosts', 'NAGIOS_HOSTLATENCY': u'0', 'NAGIOS_TIMET': u'1481525615', 'NAGIOS_HOSTCHECKCOMMAND': u'check-host-alive-parent!up!$HOSTSTATE:test_router_0$', 'NAGIOS_NOTIFICATIONAUTHORALIAS': 'n/a', 'NAGIOS_TOTALSERVICESCRITICAL': u'1', 'NAGIOS_HOSTSNAPSHOTCOMMAND': 'n/a', 'NAGIOS_HOSTSTATETYPE': u'HARD'}, 'notif_nb': 1, 'enable_environment_macros': False, 'ack_author': '', 'status': 'scheduled', 'execution_time': 0.0, 'start_time': 0, 'worker': 'none', 't_to_go': 1481525615, 'module_type': 'fork', '_in_timeout': False, 'sched_id': 0, 'uuid': '54c84bc7b74046b8be79d5766c41c815', 'service_description': '', 'ref': u'e2c43584811d4d97a3af92e73f04ddea', 'is_a': 'notification', 'contact': u'2b8f6c0e92874fc8b8f71eadbf8681b7', 'command': u'/notifier.pl --hostname test_host_0 --notificationtype PROBLEM --hoststate DOWN --hostoutput DOWN --longdatetime Mon 12 Dec 07:53:35 CET 2016 --hostattempt 3 --hoststatetype HARD', 'host_name': u'test_host_0', 'timeout': 30, 'output': '', 'already_start_escalations': []}}, 'state': 'DOWN', 'last_chk': 1481525615, 'current_notification_id': 0, 'last_state_id': 0, 'event_handler_enabled': False, 'start_time': 0, 'has_been_checked': 1, 'pending_flex_downtime': 0, 'last_state_update': 1481525615.038105, 'execution_time': 0.0, 'last_snapshot': 0, 'notifications_enabled': True, 'return_code': 2, 'output': u'DOWN', 'state_type': 'HARD', 'in_maintenance': -1, 'is_flapping': False, 'notified_contacts': [u'test_contact'], 'flapping_comment_id': 0, 'obsess_over_host': False, 'early_timeout': 0, 'in_scheduled_downtime': False, 'attempt': 3, 'acknowledgement': None, 'scheduled_downtime_depth': 0, 'state_type_id': 1, 'last_state_change': 1481525614.801228, 'last_time_down': 1481525615, 'flap_detection_enabled': True, 'modified_attributes': 0, 'long_output': u'', 'duration_sec': 0.2368769645690918, 'current_problem_id': 2, 'end_time': 0, 'timeout': 0, 'last_hard_state': 'DOWN', 'state_id': 1, 'last_hard_state_id': 1, 'perf_data': u''}

        # ************** test the restoration of retention ************** #
        # new conf
        self.setup_with_file('cfg/cfg_default.cfg')
        hostn = self.schedulers['scheduler-master'].sched.hosts.find_by_name("test_host_0")
        hostn.checks_in_progress = []
        hostn.act_depend_of = []  # ignore the router
        hostn.event_handler_enabled = False

        svcn = self.schedulers['scheduler-master'].sched.services.find_srv_by_name_and_hostname(
            "test_host_0", "test_ok_0")
        # To make tests quicker we make notifications send very quickly
        svcn.notification_interval = 0.001
        svcn.checks_in_progress = []
        svcn.act_depend_of = []  # no hostchecks on critical checkresults

        self.scheduler_loop(1, [[hostn, 0, 'UP'], [svcn, 1, 'WARNING']])
        time.sleep(0.1)
        assert 0 == len(self.schedulers['scheduler-master'].sched.comments)
        assert 0 == len(hostn.notifications_in_progress)

        self.schedulers['scheduler-master'].sched.restore_retention_data(retention)

        assert hostn.last_state == 'DOWN'
        assert svcn.last_state == 'CRITICAL'

        assert host.uuid != hostn.uuid

        # check downtime
        assert host.downtimes == hostn.downtimes
        for down_uuid, downtime in self.schedulers['scheduler-master'].sched.downtimes.iteritems():
            assert 'My downtime' == downtime.comment

        # check notifications
        assert 2 == len(hostn.notifications_in_progress)
        for notif_uuid, notification in hostn.notifications_in_progress.iteritems():
            assert host.notifications_in_progress[notif_uuid].command == \
                             notification.command
            assert host.notifications_in_progress[notif_uuid].t_to_go == \
                             notification.t_to_go

        # check comments
        assert 2 == len(self.schedulers['scheduler-master'].sched.comments)
        commentsn = []
        for comm_uuid, comment in self.schedulers['scheduler-master'].sched.comments.iteritems():
            commentsn.append(comment.comment)
        assert comments == commentsn

        # check notified_contacts
        assert isinstance(hostn.notified_contacts, set)
        assert isinstance(svcn.notified_contacts, set)
        assert set([self.schedulers['scheduler-master'].sched.contacts.find_by_name("test_contact").uuid]) == \
                         hostn.notified_contacts

        # acknowledge
        assert True == svcn.problem_has_been_acknowledged

