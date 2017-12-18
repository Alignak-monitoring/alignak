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
#     aviau, alexandre.viau@savoirfairelinux.com
#     xkilian, fmikus@acktomic.com
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de

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
# This file is used to test reading and processing of config files
#
import time

from alignak_test import AlignakTest

from alignak.action import Action
from alignak.notification import Notification
from alignak.message import Message
from alignak.worker import Worker
from multiprocessing import Queue
from alignak.objects.contact import Contact


class TestWorkerTimeout(AlignakTest):
    def setUp(self):
        super(TestWorkerTimeout, self).setUp()

        # we have an external process, so we must un-fake time functions
        self.setup_with_file('cfg/cfg_check_worker_timeout.cfg')
        assert self.conf_is_correct

        # Our scheduler
        self._sched = self._scheduler

    def test_notification_timeout(self):
        """ Test timeout for notification sending
        
        :return: 
        """
        # Get a test service
        svc = self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0_timeout")

        # These queues connect a poller/reactionner with a worker
        to_queue = Queue()
        from_queue = Queue() #manager.list()
        control_queue = Queue()

        # This test script plays the role of the reactionner
        # Now we "fork" a worker
        w = Worker(1, to_queue, from_queue, 1)
        w.uuid = 1
        w.i_am_dying = False

        # We prepare a notification in the to_queue
        contact = Contact()
        contact.contact_name = "alignak"

        data = {
            'uuid': 1,
            'type': 'PROBLEM',
            'status': 'scheduled',
            'command': 'libexec/sleep_command.sh 7',
            'command_call': '',
            'ref': svc.uuid,
            'contact': '',
            't_to_go': 0.0
        }
        n = Notification(data)

        n.status = "queue"
        n.t_to_go = time.time()
        n.contact = contact
        n.timeout = 2
        n.env = {}
        n.exit_status = 0
        n.module_type = "fork"

        # Send the job to the worker
        msg = Message(_type='Do', data=n)
        to_queue.put(msg)

        # Now we simulate the Worker's work() routine. We can't call it
        # as w.work() because it is an endless loop
        w.checks = []
        w.returns_queue = from_queue
        w.slave_q = to_queue

        for i in xrange(1, 10):
            w.get_new_checks(to_queue, from_queue)
            # During the first loop the sleeping command is launched
            w.launch_new_checks()
            w.manage_finished_checks(from_queue)
            time.sleep(1)

        # The worker should have finished its job now, either correctly or with a timeout
        msg = from_queue.get()

        o = msg.get_data()
        self.assertEqual('timeout', o.status)
        self.assertEqual(3, o.exit_status)
        self.assertLess(o.execution_time, n.timeout+1)

        # Let us be a good poller and clean up
        to_queue.close()
        control_queue.close()

        # Now look what the scheduler says about this
        self._sched.actions[n.uuid] = n
        self._sched.put_results(o)
        self.show_logs()
        self.assert_any_log_match("Contact alignak service notification command "
                                  "'libexec/sleep_command.sh 7 ' timed out after 2 seconds")
