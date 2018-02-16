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
#  Copyright (C) 2009-2014:
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     aviau, alexandre.viau@savoirfairelinux.com
#     Grégory Starck, g.starck@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Romain Forlot, rforlot@yahoo.com

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
The objects package contains the definition of the classes for the different objects
 that can be declared in configuration files.
 """


from alignak.objects.item import Item, Items
from alignak.objects.timeperiod import Timeperiod, Timeperiods
from alignak.objects.schedulingitem import SchedulingItem
from alignak.objects.service import Service, Services
from alignak.objects.command import Command, Commands
from alignak.objects.config import Config
from alignak.objects.resultmodulation import Resultmodulation, Resultmodulations
from alignak.objects.escalation import Escalation, Escalations
from alignak.objects.serviceescalation import Serviceescalation, Serviceescalations
from alignak.objects.hostescalation import Hostescalation, Hostescalations
from alignak.objects.host import Host, Hosts
from alignak.objects.hostgroup import Hostgroup, Hostgroups
from alignak.objects.realm import Realm, Realms
from alignak.objects.contact import Contact, Contacts
from alignak.objects.contactgroup import Contactgroup, Contactgroups
from alignak.objects.notificationway import NotificationWay, NotificationWays
from alignak.objects.servicegroup import Servicegroup, Servicegroups
from alignak.objects.servicedependency import Servicedependency, Servicedependencies
from alignak.objects.hostdependency import Hostdependency, Hostdependencies
from alignak.objects.module import Module, Modules
from alignak.objects.businessimpactmodulation import Businessimpactmodulation, \
    Businessimpactmodulations
from alignak.objects.macromodulation import MacroModulation, MacroModulations
