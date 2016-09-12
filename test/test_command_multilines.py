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
This file test command in multilines
"""

from alignak_test import AlignakTest


class TestCommandMultilines(AlignakTest):
    """
    This class test load command in multilines
    """

    def test_multilines(self):
        """
        Test load command with multiple lines

        :return: None
        """
        self.print_header()
        self.setup_with_file('cfg/cfg_command_multilines.cfg')

        conf_state = self.arbiter.conf.conf_is_correct
        self.assertTrue(conf_state)

        command = self.schedulers[0].sched.commands.find_by_name("host-notify-by-email-html")
        reference = '/usr/bin/printf "%b" "MIME-Version: 1.0 \n' \
                    'Content-Type: text/html \n' \
                    'Content-Disposition: inline \n' \
                    'From: email@example.com \n' \
                    'To: $CONTACTEMAIL$ \n' \
                    'Subject: $HOSTALIAS$ is $HOSTSTATE$ (HOST $NOTIFICATIONTYPE$) \n' \
                    '<html><head><meta http-equiv=\\"Content-Type\\" content=\\"text/html\\">' \
                    '<style type=\\"text/css\\"> ' \
                    '		  body, td {text-align: center} \n' \
                    '		  table {margin: 0px auto} \n' \
                    '		  table {width: 500px} \n' \
                    '		  table {border: 1px solid black} \n' \
                    '		  td.customer {background-color: #004488} \n' \
                    '		  td.customer {color: white} \n' \
                    '		  td.customer {font-size: 12pt} \n' \
                    '		  th {white-space: nowrap} \n' \
                    '		  th, td.output {text-align: left} \n' \
                    '		  tr.even th {background-color: #D9D9D9} \n' \
                    '		  tr.even td, tr.odd th {background-color: #F2F2F2} \n' \
                    '		  tr.odd td {background-color: white} \n' \
                    '		  td.ACKNOWLEDGEMENT {background-color: blue} \n' \
                    '		  td.PROBLEM {background-color: red} \n' \
                    '		  td.RECOVERY {background-color: green} \n' \
                    '		  span.WARNING, span.UNKNOWN {color: orange} \n' \
                    '		  span.CRITICAL, span.DOWN, span.UNREACHABLE {color: red} \n' \
                    '		  span.OK, span.UP {color: green} \n' \
                    '		  td.output {padding: 15px 10px} \n' \
                    '</style> ' \
                    '<title>$HOSTALIAS$ is $HOSTSTATE$ (HOST $NOTIFICATIONTYPE$)</title>' \
                    '</head> \n' \
                    '<body><table> ' \
                    '	      <tr><td colspan=2 class=$NOTIFICATIONTYPE$>' \
                    '<b>HOST $NOTIFICATIONTYPE$</b></td></tr> ' \
                    '	      <tr class=odd><th>Host:</th><td><b>$HOSTALIAS$</b></td></tr> ' \
                    '	      <tr class=even><th>Host State:</th><td><span class=$HOSTSTATE$>' \
                    '<b>$HOSTSTATE$</b></span> <i>for</i> $HOSTDURATION$</td></tr> ' \
                    '	      <tr class=odd><th>Host IP:</th><td>$HOSTADDRESS$</td></tr> ' \
                    '	      <tr class=even><th>Date, Time:</th><td>$LONGDATETIME$</td></tr> ' \
                    '	      <tr><td colspan=2 class=output><i><p>$HOSTOUTPUT$</p>' \
                    '<p>$LONGHOSTOUTPUT$</p></i></td></tr> ' \
                    '	      <tr><td colspan=2 class=output><p>$HOSTACTIONURL$</p></td></tr>' \
                    '	      <tr><td colspan=2 class=customer><b>OUR COMPANY</b></td></tr> ' \
                    '</table></body></html>" | sendmail -v -t'
        reference = reference.replace('\n', '\\n')
        print command.command_line
        print '-----------------------'
        print reference
        self.assertEqual(command.command_line, reference)
