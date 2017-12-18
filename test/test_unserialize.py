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
"""
This file test unserialisation of data
"""

from alignak_test import AlignakTest
from alignak.misc.serialization import unserialize


class TestUnserialize(AlignakTest):
    """
    This class test the unserialize process
    """
    def setUp(self):
        super(TestUnserialize, self).setUp()

    def test_unserialize_notif(self):
        """ Test unserialize notifications

        :return: None
        """
        var = '''
        {"98a76354619746fa8e6d2637a5ef94cb": {
            "content": {
                "reason_type": 1, "exit_status": 3, "creation_time":1468522950.2828259468,
                "command_call": {
                    "args": [], "call": "notify-service",
                    "command": {
                        "command_line": "$USER1$\/notifier.pl
                                         --hostname $HOSTNAME$
                                         --servicedesc $SERVICEDESC$
                                         --notificationtype $NOTIFICATIONTYPE$
                                         --servicestate $SERVICESTATE$
                                         --serviceoutput $SERVICEOUTPUT$
                                         --longdatetime $LONGDATETIME$
                                         --serviceattempt $SERVICEATTEMPT$
                                         --servicestatetype $SERVICESTATETYPE$",
                        "command_name": "notify-service",
                        "configuration_errors":[],
                        "configuration_warnings":[],
                        "enable_environment_macros": false,
                        "id": "487aa432ddf646079ec6c07803333eac",
                        "imported_from": "cfg\/default\/commands.cfg:14",
                        "macros":{}, "module_type": "fork", "my_type":"command",
                        "ok_up":"", "poller_tag": "None",
                        "properties":{
                            "use":{
                                "brok_transformation": null,
                                "class_inherit": [],
                                "conf_send_preparation": null,
                                "default":[],
                                "fill_brok":[],
                                "has_default":true,
                                "help":"",
                                "keep_empty":false,
                                "managed":true,
                                "merging":"uniq",
                                "no_slots":false,
                                "override":false,
                                "required":false,
                                "retention":false,
                                "retention_preparation":null,
                                "special":false,
                                "split_on_coma":true,
                                "to_send":false,
                                "unmanaged":false,
                                "unused":false},
                            "name":{
                                "brok_transformation":null,
                                "class_inherit":[],
                                "conf_send_preparation":null,
                                "default":"",
                                "fill_brok":[],
                                "has_default":true,
                                "help":"",
                                "keep_empty":false,
                                "managed":true,
                                "merging":"uniq",
                                "no_slots":false,
                                "override":false,
                                "required":false,
                                "retention":false,
                                "retention_preparation":null,
                                "special":false,
                                "split_on_coma":true,
                                "to_send":false,
                                "unmanaged":false,
                                "unused":false},
                            },
                        "reactionner_tag":"None",
                        "running_properties":{
                            "configuration_errors":{
                                "brok_transformation":null,
                                "class_inherit":[],
                                "conf_send_preparation":null,
                                "default":[],"fill_brok":[],
                                "has_default":true,"help":"","keep_empty":false,
                                "managed":true,"merging":"uniq","no_slots":false,"override":false,
                                "required":false,"retention":false,"retention_preparation":null,
                                "special":false,"split_on_coma":true,"to_send":false,
                                "unmanaged":false,"unused":false},
                            },
                        "tags":[],
                        "timeout":-1,
                        "uuid":"487aa432ddf646079ec6c07803333eac"},
                    "enable_environment_macros":false,
                    "late_relink_done":false,
                    "macros":{},
                    "module_type":"fork",
                    "my_type":"CommandCall",
                    "poller_tag":"None",
                    "properties":{},
                    "reactionner_tag":"None",
                    "timeout":-1,
                    "uuid":"cfcaf0fc232b4f59a7d8bb5bd1d83fef",
                    "valid":true},
                "escalated":false,
                "reactionner_tag":"None",
                "s_time":0.0,
                "notification_type":0,
                "contact_name":"test_contact",
                "type":"PROBLEM",
                "uuid":"98a76354619746fa8e6d2637a5ef94cb",
                "check_time":0,"ack_data":"",
                "state":0,"u_time":0.0,
                "env":{
                    "NAGIOS_SERVICEDOWNTIME":"0",
                    "NAGIOS_TOTALSERVICESUNKNOWN":"",
                    "NAGIOS_LONGHOSTOUTPUT":"",
                    "NAGIOS_HOSTDURATIONSEC":"1468522950",
                    "NAGIOS_HOSTDISPLAYNAME":"test_host_0",
                    },
                "notif_nb":1,"_in_timeout":false,"enable_environment_macros":false,
                "host_name":"test_host_0",
                "status":"scheduled",
                "execution_time":0.0,"start_time":0,"worker":"none","t_to_go":1468522950,
                "module_type":"fork","service_description":"test_ok_0","sched_id":0,"ack_author":"",
                "ref":"272e89c1de854bad85987a7583e6c46b",
                "is_a":"notification",
                "contact":"4e7c4076c372457694684bdd5ba47e94",
                "command":"\/notifier.pl --hostname test_host_0 --servicedesc test_ok_0
                          --notificationtype PROBLEM --servicestate CRITICAL
                          --serviceoutput CRITICAL --longdatetime Thu 14 Jul 21:02:30 CEST 2016
                          --serviceattempt 2 --servicestatetype HARD",
                "end_time":0,"timeout":30,"output":"",
                "already_start_escalations":[]},
            "__sys_python_module__":"alignak.notification.Notification"
            }
        }

        '''
        unserialize(var)
        assert True

    def test_unserialize_check(self):
        """ Test unserialize checks

        :return: None
        """
        var = '''
        {"content":
                   {"check_type":0,"exit_status":3,"creation_time":1469152287.6731250286,
                    "reactionner_tag":"None","s_time":0.0,
                    "uuid":"5f1b16fa809c43379822c7acfe789660","check_time":0,"long_output":"",
                    "state":0,"internal":false,"u_time":0.0,"env":{},"depend_on_me":[],
                    "ref":"1fe5184ea05d439eb045399d26ed3337","from_trigger":false,
                    "status":"scheduled","execution_time":0.0,"worker":"none","t_to_go":1469152290,
                    "module_type":"echo","_in_timeout":false,"dependency_check":false,"type":"",
                    "depend_on":[],"is_a":"check","poller_tag":"None","command":"_echo",
                    "timeout":30,"output":"","perf_data":""},
               "__sys_python_module__":"alignak.check.Check"
        }
        '''

        unserialize(var)
        assert True
