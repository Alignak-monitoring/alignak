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
This file is used to test the complex hostgroups
"""

from alignak_test import AlignakTest


class TestComplexHostgroups(AlignakTest):

    def setUp(self):
        super(TestComplexHostgroups, self).setUp()
        self.setup_with_file('cfg/hostgroup/complex_hostgroups.cfg')
        assert self.conf_is_correct

        # Our scheduler
        self._sched = self._scheduler

    def get_svc(self):
        return self._sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")

    def find_service(self, name, desc):
        return self._sched.services.find_srv_by_name_and_hostname(name, desc)

    def find_host(self, name):
        return self._sched.hosts.find_by_name(name)

    def find_hostgroup(self, name):
        return self._sched.hostgroups.find_by_name(name)

    def dump_hosts(self, svc):
        for h in svc.host_name:
            print h

    # check if service exist in hst, but NOT in others
    def service_defined_only_on(self, service_description, hosts):
        """
        Check if the service named as service_description exists on the hosts and
        not on the other scheduler hosts

        :param service_description: service to search for
        :param hosts: list of expected hosts
        :return:
        """
        result = True
        # Exists on the listed hosts
        for host in hosts:
            svc = self.find_service(host.host_name, service_description)
            if svc is None:
                print "Error: the host %s is missing service %s!!" % (host.host_name,
                                                                      service_description)
                result = False

        # Do not exist on the other hosts
        for host in self._sched.hosts:
            if host not in hosts:
                svc = self.find_service(host.host_name, service_description)
                if svc is not None:
                    print "Error: the host %s got the service %s!!" % (host.host_name,
                                                                       service_description)
                    result = False
        return result

    def test_complex_hostgroups(self):
        """
        Test a complex hostgroup definition
        :return:
        """
        # Get all our hosts
        test_linux_web_prod_0 = self.find_host('test_linux_web_prod_0')
        assert test_linux_web_prod_0 is not None
        test_linux_web_qual_0 = self.find_host('test_linux_web_qual_0')
        assert test_linux_web_qual_0 is not None
        test_win_web_prod_0 = self.find_host('test_win_web_prod_0')
        assert test_win_web_prod_0 is not None
        test_win_web_qual_0 = self.find_host('test_win_web_qual_0')
        assert test_win_web_qual_0 is not None
        test_linux_file_prod_0 = self.find_host('test_linux_file_prod_0')
        assert test_linux_file_prod_0 is not None

        hg_linux = self.find_hostgroup('linux')
        assert hg_linux is not None
        hg_web = self.find_hostgroup('web')
        assert hg_web is not None
        hg_win = self.find_hostgroup('win')
        assert hg_win is not None
        hg_file = self.find_hostgroup('file')
        assert hg_file is not None

        # Hostgroup linux has 3 hosts
        assert hg_linux.get_name() == "linux"
        assert len(hg_linux.get_hosts()) == 3
        # Expected hosts are in this group
        assert test_linux_web_prod_0.uuid in hg_linux.members
        assert test_linux_web_qual_0.uuid in hg_linux.members
        assert test_linux_file_prod_0.uuid in hg_linux.members
        for host in hg_linux:
            assert self._sched.hosts[host].get_name() in ['test_linux_web_prod_0',
                                                          'test_linux_web_qual_0',
                                                          'test_linux_file_prod_0']

        # First the service defined for the hostgroup: linux
        assert self.service_defined_only_on('linux_0', [test_linux_web_prod_0,
                                                        test_linux_web_qual_0,
                                                        test_linux_file_prod_0])

        # Then a service defined for the hostgroups: linux,web
        assert self.service_defined_only_on('linux_web_0', [test_linux_web_prod_0,
                                                            test_linux_web_qual_0,
                                                            test_linux_file_prod_0,
                                                            test_win_web_prod_0,
                                                            test_win_web_qual_0])

        # The service defined for the hostgroup: linux&web
        assert self.service_defined_only_on('linux_AND_web_0', [test_linux_web_prod_0,
                                                                test_linux_web_qual_0])

        # The service defined for the hostgroup: linux|web
        assert self.service_defined_only_on('linux_OR_web_0', [test_linux_web_prod_0,
                                                               test_linux_web_qual_0,
                                                               test_win_web_prod_0,
                                                               test_win_web_qual_0,
                                                               test_linux_file_prod_0])

        # The service defined for the hostgroup: (linux|web),file
        assert self.service_defined_only_on('linux_OR_web_PAR_file0', [test_linux_web_prod_0,
                                                                       test_linux_web_qual_0,
                                                                       test_win_web_prod_0,
                                                                       test_win_web_qual_0,
                                                                       test_linux_file_prod_0,
                                                                       test_linux_file_prod_0])

        # The service defined for the hostgroup: (linux|web)&prod
        assert self.service_defined_only_on('linux_OR_web_PAR_AND_prod0', [test_linux_web_prod_0,
                                                                           test_win_web_prod_0,
                                                                           test_linux_file_prod_0])

        # The service defined for the hostgroup: (linux|web)&(*&!prod)
        assert self.service_defined_only_on(
            'linux_OR_web_PAR_AND_NOT_prod0', [test_linux_web_qual_0, test_win_web_qual_0])

        # The service defined for the hostgroup with a minus sign in its name
        assert self.service_defined_only_on('name-with-minus-in-it', [test_linux_web_prod_0])

        # The service defined for the hostgroup: (linux|web)&(prod), except an host
        assert self.service_defined_only_on(
            'linux_OR_web_PAR_AND_prod0_AND_NOT_test_linux_file_prod_0', [test_linux_web_prod_0,
                                                                          test_win_web_prod_0])

        # The service defined for the hostgroup: win&((linux|web)&prod), except an host
        assert self.service_defined_only_on(
            'WINDOWS_AND_linux_OR_web_PAR_AND_prod0_AND_NOT_test_linux_file_prod_0', [
                test_win_web_prod_0])


if __name__ == '__main__':
    AlignakTest.main()
