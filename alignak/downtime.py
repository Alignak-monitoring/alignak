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
#     xkilian, fmikus@acktomic.com
#     Romain LE DISEZ, romain.git@ledisez.net
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
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
"""This modules provides Downtime class, used to implements downtime monitoring concept.
See detailed concepts below

"""
import time
from alignak.comment import Comment
from alignak.property import BoolProp, IntegerProp, StringProp
from alignak.brok import Brok
from alignak.alignakobject import AlignakObject


DOWNTIME_FIXED_MESSAGE = u"This %s has been scheduled for fixed downtime from %s to %s. " \
                         u"Notifications for the %s will not be sent out for this time period."
DOWNTIME_FLEXIBLE_MESSAGE = u"This %s has been scheduled for flexible downtime starting between " \
                            u"%s and %s and lasting for a period of %d hours and %d minutes. " \
                            u"Notifications for the %s will not be sent out for this time period."


class Downtime(AlignakObject):
    """ Schedules downtime for a specified service. If the "fixed" argument is set
    to one (1), downtime will start and end at the times specified by the
    "start" and "end" arguments.
    Otherwise, downtime will begin between the "start" and "end" times and last
    for "duration" seconds. The "start" and "end" arguments are specified
    in time_t format (seconds since the UNIX epoch). The specified service
    downtime can be triggered by another downtime entry if the "trigger_id"
    is set to the ID of another scheduled downtime entry.
    Set the "trigger_id" argument to zero (0) if the downtime for the
    specified service should not be triggered by another downtime entry.

    """

    my_type = 'downtime'
    properties = {
        'activate_me':
            StringProp(default=u''),
        'entry_time':
            IntegerProp(default=0, fill_brok=['full_status']),
        'fixed':
            BoolProp(default=True, fill_brok=['full_status']),
        'start_time':
            IntegerProp(default=0, fill_brok=['full_status']),
        'duration':
            IntegerProp(default=0, fill_brok=['full_status']),
        'trigger_id':
            StringProp(default=u''),
        'end_time':
            IntegerProp(default=0, fill_brok=['full_status']),
        'real_end_time':
            IntegerProp(default=0),
        'author':
            StringProp(default=u'Alignak', fill_brok=['full_status']),
        'comment':
            StringProp(default=u''),
        'is_in_effect':
            BoolProp(default=False),
        'has_been_triggered':
            BoolProp(default=False),
        'can_be_deleted':
            BoolProp(default=False),
        'ref':
            StringProp(default=u'unset'),
        'ref_type':
            StringProp(default=u'unset'),
        'comment_id':
            StringProp(default=u''),
    }

    def __init__(self, params, parsing=False):
        creating = 'uuid' not in params

        super(Downtime, self).__init__(params, parsing=parsing)

        self.fill_default()

        if creating:
            self.activate_me = []  # The other downtimes i need to activate
            self.entry_time = int(time.time())
            if self.trigger_id not in ['', '0']:  # triggered plus fixed makes no sense
                self.fixed = False
            if self.fixed:
                self.duration = self.end_time - self.start_time
            # This is important for flexible downtimes. Here start_time and
            # end_time mean: in this time interval it is possible to trigger
            # the beginning of the downtime which lasts for duration.
            # Later, when a non-ok event happens, real_end_time will be
            # recalculated from now+duration
            # end_time will be displayed in the web interface, but real_end_time
            # is used internally
            self.real_end_time = self.end_time
            self.is_in_effect = False

            self.has_been_triggered = False  # another downtime has triggered me
            self.can_be_deleted = False

    def __str__(self):  # pragma: no cover
        if self.is_in_effect is True:
            active = "active"
        else:
            active = "inactive"
        if self.fixed is True:
            d_type = "fixed"
        else:
            d_type = "flexible"
        return "%s %s Downtime id=%s %s - %s" % (
            active, d_type, self.uuid, time.ctime(self.start_time), time.ctime(self.end_time))

    def trigger_me(self, other_downtime):
        """Wrapper to activate_me.append function
        Used to add another downtime to activate

        :param other_downtime: other downtime to activate/cancel
        :type other_downtime:
        :return: None
        """
        self.activate_me.append(other_downtime)

    def in_scheduled_downtime(self):
        """Getter for is_in_effect attribute

        :return: True if downtime is in effect, False otherwise
        :rtype: bool
        """
        return self.is_in_effect

    def enter(self, timeperiods, hosts, services):
        """Set ref in scheduled downtime and raise downtime log entry (start)

        :param hosts: hosts objects to get item ref
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects to get item ref
        :type services: alignak.objects.service.Services
        :return: broks
        :rtype: list of broks
        """
        if self.ref in hosts:
            item = hosts[self.ref]
        else:
            item = services[self.ref]
        broks = []
        self.is_in_effect = True
        if self.fixed is False:
            now = time.time()
            self.real_end_time = now + self.duration
        item.scheduled_downtime_depth += 1
        item.in_scheduled_downtime = True
        if item.scheduled_downtime_depth == 1:
            item.raise_enter_downtime_log_entry()
            notification_period = None
            if getattr(item, 'notification_period', None) is not None:
                notification_period = timeperiods[item.notification_period]
            # Notification author data
            # todo: note that alias and name are not implemented yet
            author_data = {
                'author': self.author, 'author_name': u'Not available',
                'author_alias': u'Not available', 'author_comment': self.comment
            }
            item.create_notifications('DOWNTIMESTART', notification_period, hosts, services,
                                      author_data=author_data)
            if self.ref in hosts:
                broks.append(self.get_raise_brok(item.get_name()))

                # For an host, acknowledge the host problem (and its services problems)
                # Acknowledge the host with a sticky ack and notifications
                # The acknowledge will expire at the same time as the downtime end
                item.acknowledge_problem(notification_period, hosts, services, 2, 1, "Alignak",
                                         "Acknowledged because of an host downtime")
            else:
                broks.append(self.get_raise_brok(item.host_name, item.get_name()))
        for downtime_id in self.activate_me:
            for host in hosts:
                if downtime_id in host.downtimes:
                    downtime = host.downtimes[downtime_id]
                    broks.extend(downtime.enter(timeperiods, hosts, services))
            for service in services:
                if downtime_id in service.downtimes:
                    downtime = service.downtimes[downtime_id]
                    broks.extend(downtime.enter(timeperiods, hosts, services))
        return broks

    def exit(self, timeperiods, hosts, services):
        """Remove ref in scheduled downtime and raise downtime log entry (exit)

        :param hosts: hosts objects to get item ref
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects to get item ref
        :type services: alignak.objects.service.Services
        :return: [], always | None
        :rtype: list
        """
        if self.ref in hosts:
            item = hosts[self.ref]
        else:
            item = services[self.ref]

        broks = []
        # If not is_in_effect means that ot was probably a flexible downtime which was
        # not triggered. In this case, nothing special to do...
        if self.is_in_effect is True:
            # This was a fixed or a flexible+triggered downtime
            self.is_in_effect = False
            item.scheduled_downtime_depth -= 1
            if item.scheduled_downtime_depth == 0:
                item.raise_exit_downtime_log_entry()
                notification_period = timeperiods[item.notification_period]
                # Notification author data
                # todo: note that alias and name are not implemented yet
                author_data = {
                    'author': self.author, 'author_name': u'Not available',
                    'author_alias': u'Not available', 'author_comment': self.comment
                }
                item.create_notifications(u'DOWNTIMEEND', notification_period, hosts, services,
                                          author_data=author_data)
                item.in_scheduled_downtime = False
                if self.ref in hosts:
                    broks.append(self.get_expire_brok(item.get_name()))
                else:
                    broks.append(self.get_expire_brok(item.host_name, item.get_name()))

        item.del_comment(self.comment_id)
        self.can_be_deleted = True

        # when a downtime ends and the concerned item was a problem
        # a notification should be sent with the next critical check

        # So we should set a flag here which informs the consume_result function
        # to send a notification
        item.in_scheduled_downtime_during_last_check = True
        return broks

    def cancel(self, timeperiods, hosts, services):
        """Remove ref in scheduled downtime and raise downtime log entry (cancel)

        :param hosts: hosts objects to get item ref
        :type hosts: alignak.objects.host.Hosts
        :param services: services objects to get item ref
        :type services: alignak.objects.service.Services
        :return: [], always
        :rtype: list
        """
        if self.ref in hosts:
            item = hosts[self.ref]
        else:
            item = services[self.ref]
        broks = []
        self.is_in_effect = False
        item.scheduled_downtime_depth -= 1
        if item.scheduled_downtime_depth == 0:
            item.raise_cancel_downtime_log_entry()
            item.in_scheduled_downtime = False
            if self.ref in hosts:
                broks.append(self.get_expire_brok(item.get_name()))
            else:
                broks.append(self.get_expire_brok(item.host_name, item.get_name()))
        self.del_automatic_comment(item)
        self.can_be_deleted = True
        item.in_scheduled_downtime_during_last_check = True
        # Nagios does not notify on canceled downtimes
        # res.extend(self.ref.create_notifications('DOWNTIMECANCELLED'))
        # Also cancel other downtimes triggered by me
        for downtime in self.activate_me:
            broks.extend(downtime.cancel(timeperiods, hosts, services))
        return broks

    def add_automatic_comment(self, ref):
        """Add comment on ref for downtime

        :param ref: the host/service we want to link a comment to
        :type ref: alignak.objects.schedulingitem.SchedulingItem

        :return: None
        """
        if self.fixed is True:
            text = (DOWNTIME_FIXED_MESSAGE % (ref.my_type,
                                              time.strftime("%Y-%m-%d %H:%M:%S",
                                                            time.localtime(self.start_time)),
                                              time.strftime("%Y-%m-%d %H:%M:%S",
                                                            time.localtime(self.end_time)),
                                              ref.my_type))
        else:
            hours, remainder = divmod(self.duration, 3600)
            minutes, _ = divmod(remainder, 60)
            text = (DOWNTIME_FLEXIBLE_MESSAGE % (ref.my_type,
                                                 time.strftime("%Y-%m-%d %H:%M:%S",
                                                               time.localtime(self.start_time)),
                                                 time.strftime("%Y-%m-%d %H:%M:%S",
                                                               time.localtime(self.end_time)),
                                                 hours, minutes, ref.my_type))

        data = {
            'comment': text,
            'comment_type': 1 if ref.my_type == 'host' else 2,
            'entry_type': 2,
            'source': 0,
            'expires': False,
            'ref': ref.uuid
        }
        comment = Comment(data)
        self.comment_id = comment.uuid
        ref.comments[comment.uuid] = comment
        return comment

    def del_automatic_comment(self, item):
        """Remove automatic comment on ref previously created

        :param item: item service or host
        :type item: object
        :return: None
        """
        item.del_comment(self.comment_id)
        self.comment_id = ''

    def fill_data_brok_from(self, data, brok_type):
        """Fill data with info of item by looking at brok_type
        in props of properties or running_properties

        :param data: data to fill
        :type data:
        :param brok_type: type of brok
        :type brok_type: str
        :return: None
        TODO: Duplicate from Notification.fill_data_brok_from
        """
        cls = self.__class__
        # Now config properties
        for prop, entry in list(cls.properties.items()):
            if hasattr(prop, 'fill_brok'):
                if brok_type in entry['fill_brok']:
                    data[prop] = getattr(self, prop)

    def get_raise_brok(self, host_name, service_name=''):
        """Get a start downtime brok

        :param host_name: host concerned by the downtime
        :type host_name
        :param service_name: service concerned by the downtime
        :type service_name
        :return: brok with wanted data
        :rtype: alignak.brok.Brok
        """
        data = self.serialize()
        data['host'] = host_name
        if service_name != '':
            data['service'] = service_name

        return Brok({'type': 'downtime_raise', 'data': data})

    def get_expire_brok(self, host_name, service_name=''):
        """Get an expire downtime brok

        :param host_name: host concerned by the downtime
        :type host_name
        :param service_name: service concerned by the downtime
        :type service_name
        :return: brok with wanted data
        :rtype: alignak.brok.Brok
        """
        data = self.serialize()
        data['host'] = host_name
        if service_name != '':
            data['service'] = service_name

        return Brok({'type': 'downtime_expire', 'data': data})
