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
#     andrewmcgilvray, a.mcgilvray@gmail.com
#     Frédéric MOHIER, frederic.mohier@ipmfrance.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Olivier Hanesse, olivier.hanesse@gmail.com
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
This module provide Regenerator class used in
several Alignak modules to manage and regenerate objects
"""
import time

# Import all objects we will need
from alignak.objects.host import Host, Hosts
from alignak.objects.hostgroup import Hostgroup, Hostgroups
from alignak.objects.service import Service, Services
from alignak.objects.servicegroup import Servicegroup, Servicegroups
from alignak.objects.contact import Contact, Contacts
from alignak.objects.contactgroup import Contactgroup, Contactgroups
from alignak.objects.notificationway import NotificationWay, NotificationWays
from alignak.objects.timeperiod import Timeperiod, Timeperiods
from alignak.objects.command import Command, Commands
from alignak.objects.config import Config
from alignak.objects.schedulerlink import SchedulerLink, SchedulerLinks
from alignak.objects.reactionnerlink import ReactionnerLink, ReactionnerLinks
from alignak.objects.pollerlink import PollerLink, PollerLinks
from alignak.objects.brokerlink import BrokerLink, BrokerLinks
from alignak.objects.receiverlink import ReceiverLink, ReceiverLinks
from alignak.util import safe_print
from alignak.message import Message


class Regenerator(object):
    """
    Class for a Regenerator.
    It gets broks, and "regenerate" real objects from them
    """
    def __init__(self):

        # Our Real datas
        self.configs = {}
        self.hosts = Hosts([])
        self.services = Services([])
        self.notificationways = NotificationWays([])
        self.contacts = Contacts([])
        self.hostgroups = Hostgroups([])
        self.servicegroups = Servicegroups([])
        self.contactgroups = Contactgroups([])
        self.timeperiods = Timeperiods([])
        self.commands = Commands([])
        self.schedulers = SchedulerLinks([])
        self.pollers = PollerLinks([])
        self.reactionners = ReactionnerLinks([])
        self.brokers = BrokerLinks([])
        self.receivers = ReceiverLinks([])
        # From now we only look for realms names
        self.realms = set()
        self.tags = {}
        self.services_tags = {}

        # And in progress one
        self.inp_hosts = {}
        self.inp_services = {}
        self.inp_hostgroups = {}
        self.inp_servicegroups = {}
        self.inp_contactgroups = {}

        # Do not ask for full data resent too much
        self.last_need_data_send = time.time()

        # Flag to say if our data came from the scheduler or not
        # (so if we skip *initial* broks)
        self.in_scheduler_mode = False

        # The Queue where to launch message, will be fill from the broker
        self.from_q = None

    def load_external_queue(self, from_q):
        """
        Load an external queue for sending messages
        Basically a from_q setter method.

        :param from_q: queue to set
        :type from_q: multiprocessing.Queue or Queue.Queue
        :return: None
        """
        self.from_q = from_q

    def load_from_scheduler(self, sched):
        """
        Load data from a scheduler

        :param sched: the scheduler obj
        :type sched: alignak.scheduler.Scheduler
        :return: None
        """
        # Ok, we are in a scheduler, so we will skip some useless
        # steps
        self.in_scheduler_mode = True

        # Go with the data creation/load
        conf = sched.conf
        # Simulate a drop conf
        brok = sched.get_program_status_brok()
        brok.prepare()
        self.manage_program_status_brok(brok)

        # Now we will lie and directly map our objects :)
        print "Regenerator::load_from_scheduler"
        self.hosts = conf.hosts
        self.services = conf.services
        self.notificationways = conf.notificationways
        self.contacts = conf.contacts
        self.hostgroups = conf.hostgroups
        self.servicegroups = conf.servicegroups
        self.contactgroups = conf.contactgroups
        self.timeperiods = conf.timeperiods
        self.commands = conf.commands
        # We also load the realm
        for host in self.hosts:
            self.realms.add(host.realm)
            break

    def want_brok(self, brok):
        """
        Function to tell whether we need a specific type of brok or not.
        Return always true if not in scheduler mode

        :param brok: The brok to check
        :type brok: alignak.objects.brok.Brok
        :return: A boolean meaning that we this brok
        :rtype: bool
        """
        if self.in_scheduler_mode:
            return brok.type not in ['program_status', 'initial_host_status',
                                     'initial_hostgroup_status', 'initial_service_status',
                                     'initial_servicegroup_status', 'initial_contact_status',
                                     'initial_contactgroup_status', 'initial_timeperiod_status',
                                     'initial_command_status']
        # Ok you are wondering why we don't add initial_broks_done?
        # It's because the LiveSTatus modules need this part to do internal things.
        # But don't worry, the vanilla regenerator will just skip it in all_done_linking :D

        # Not in don't want? so want! :)
        return True

    def manage_brok(self, brok):
        """Look for a manager function for a brok, and call it

        :param brok:
        :type brok: object
        :return:
        :rtype:
        """
        manage = getattr(self, 'manage_' + brok.type + '_brok', None)
        # If we can and want it, got for it :)
        if manage and self.want_brok(brok):
            return manage(brok)

    def update_element(self, item, data):
        """
        Update object attibute with value contained in data keys

        :param item: A alignak object
        :type item: alignak.object.Item
        :param data: the dict containing attribute to update
        :type data: dict
        :return: None
        """
        for prop in data:
            setattr(item, prop, data[prop])

    def all_done_linking(self, inst_id):
        """
        Link all data (objects) in a specific instance

        :param inst_id: Instance id from a config object
        :type inst_id: int
        :return: None
        """

        # In a scheduler we are already "linked" so we can skip this
        if self.in_scheduler_mode:
            safe_print("Regenerator: We skip the all_done_linking phase "
                       "because we are in a scheduler")
            return

        start = time.time()
        safe_print("In ALL Done linking phase for instance", inst_id)
        # check if the instance is really defined, so got ALL the
        # init phase
        if inst_id not in self.configs.keys():
            safe_print("Warning: the instance %d is not fully given, bailout" % inst_id)
            return

        # Try to load the in progress list and make them available for
        # finding
        try:
            inp_hosts = self.inp_hosts[inst_id]
            inp_hostgroups = self.inp_hostgroups[inst_id]
            inp_contactgroups = self.inp_contactgroups[inst_id]
            inp_services = self.inp_services[inst_id]
            inp_servicegroups = self.inp_servicegroups[inst_id]
        except Exception, exp:
            print "Warning all done: ", exp
            return

        # Link HOSTGROUPS with hosts
        for hostgroup in inp_hostgroups:
            new_members = []
            for (i, hname) in hostgroup.members:
                host = inp_hosts.find_by_name(hname)
                if host:
                    new_members.append(host)
            hostgroup.members = new_members

        # Merge HOSTGROUPS with real ones
        for inphg in inp_hostgroups:
            hgname = inphg.hostgroup_name
            hostgroup = self.hostgroups.find_by_name(hgname)
            # If hte hostgroup already exist, just add the new
            # hosts into it
            if hostgroup:
                hostgroup.members.extend(inphg.members)
            else:  # else take the new one
                self.hostgroups.add_item(inphg)

        # Now link HOSTS with hostgroups, and commands
        for host in inp_hosts:
            # print "Linking %s groups %s" % (h.get_name(), h.hostgroups)
            new_hostgroups = []
            for hgname in host.hostgroups.split(','):
                hgname = hgname.strip()
                hostgroup = self.hostgroups.find_by_name(hgname)
                if hostgroup:
                    new_hostgroups.append(hostgroup)
            host.hostgroups = new_hostgroups

            # Now link Command() objects
            self.linkify_a_command(host, 'check_command')
            self.linkify_a_command(host, 'event_handler')

            # Now link timeperiods
            self.linkify_a_timeperiod_by_name(host, 'notification_period')
            self.linkify_a_timeperiod_by_name(host, 'check_period')
            self.linkify_a_timeperiod_by_name(host, 'maintenance_period')

            # And link contacts too
            self.linkify_contacts(host, 'contacts')

            # Linkify tags
            for tag in host.tags:
                if tag not in self.tags:
                    self.tags[tag] = 0
                self.tags[tag] += 1

            # We can really declare this host OK now
            self.hosts.add_item(host)

        # Link SERVICEGROUPS with services
        for servicegroup in inp_servicegroups:
            new_members = []
            for (i, sname) in servicegroup.members:
                if i not in inp_services:
                    continue
                serv = inp_services[i]
                new_members.append(serv)
            servicegroup.members = new_members

        # Merge SERVICEGROUPS with real ones
        for inpsg in inp_servicegroups:
            sgname = inpsg.servicegroup_name
            servicegroup = self.servicegroups.find_by_name(sgname)
            # If the servicegroup already exist, just add the new
            # services into it
            if servicegroup:
                servicegroup.members.extend(inpsg.members)
            else:  # else take the new one
                self.servicegroups.add_item(inpsg)

        # Now link SERVICES with hosts, servicesgroups, and commands
        for serv in inp_services:
            new_servicegroups = []
            for sgname in serv.servicegroups.split(','):
                sgname = sgname.strip()
                servicegroup = self.servicegroups.find_by_name(sgname)
                if servicegroup:
                    new_servicegroups.append(servicegroup)
            serv.servicegroups = new_servicegroups

            # Now link with host
            hname = serv.host_name
            serv.host = self.hosts.find_by_name(hname)
            if serv.host:
                serv.host.services.append(serv)

            # Now link Command() objects
            self.linkify_a_command(serv, 'check_command')
            self.linkify_a_command(serv, 'event_handler')

            # Now link timeperiods
            self.linkify_a_timeperiod_by_name(serv, 'notification_period')
            self.linkify_a_timeperiod_by_name(serv, 'check_period')
            self.linkify_a_timeperiod_by_name(serv, 'maintenance_period')

            # And link contacts too
            self.linkify_contacts(serv, 'contacts')

            # Linkify services tags
            for tag in serv.tags:
                if tag not in self.services_tags:
                    self.services_tags[tag] = 0
                self.services_tags[tag] += 1

            # We can really declare this host OK now
            self.services.add_item(serv, index=True)

        # Add realm of theses hosts. Only the first is useful
        for host in inp_hosts:
            self.realms.add(host.realm)
            break

        # Now we can link all impacts/source problem list
        # but only for the new ones here of course
        for host in inp_hosts:
            self.linkify_dict_srv_and_hosts(host, 'impacts')
            self.linkify_dict_srv_and_hosts(host, 'source_problems')
            self.linkify_host_and_hosts(host, 'parents')
            self.linkify_host_and_hosts(host, 'childs')
            self.linkify_dict_srv_and_hosts(host, 'parent_dependencies')
            self.linkify_dict_srv_and_hosts(host, 'child_dependencies')

        # Now services too
        for serv in inp_services:
            self.linkify_dict_srv_and_hosts(serv, 'impacts')
            self.linkify_dict_srv_and_hosts(serv, 'source_problems')
            self.linkify_dict_srv_and_hosts(serv, 'parent_dependencies')
            self.linkify_dict_srv_and_hosts(serv, 'child_dependencies')

        # Linking TIMEPERIOD exclude with real ones now
        for timeperiod in self.timeperiods:
            new_exclude = []
            for ex in timeperiod.exclude:
                exname = ex.timeperiod_name
                tag = self.timeperiods.find_by_name(exname)
                if tag:
                    new_exclude.append(tag)
            timeperiod.exclude = new_exclude

        # Link CONTACTGROUPS with contacts
        for contactgroup in inp_contactgroups:
            new_members = []
            for (i, cname) in contactgroup.members:
                contact = self.contacts.find_by_name(cname)
                if contact:
                    new_members.append(contact)
            contactgroup.members = new_members

        # Merge contactgroups with real ones
        for inpcg in inp_contactgroups:
            cgname = inpcg.contactgroup_name
            contactgroup = self.contactgroups.find_by_name(cgname)
            # If the contactgroup already exist, just add the new
            # contacts into it
            if contactgroup:
                contactgroup.members.extend(inpcg.members)
                contactgroup.members = list(set(contactgroup.members))
            else:  # else take the new one
                self.contactgroups.add_item(inpcg)

        safe_print("ALL LINKING TIME" * 10, time.time() - start)

        # clean old objects
        del self.inp_hosts[inst_id]
        del self.inp_hostgroups[inst_id]
        del self.inp_contactgroups[inst_id]
        del self.inp_services[inst_id]
        del self.inp_servicegroups[inst_id]

    def linkify_a_command(self, obj, prop):
        """
        Replace the command_name by the command object in obj.prop

        :param obj: A host or a service
        :type obj: alignak.objects.schedulingitem.SchedulingItem
        :param prop: an attribute to replace ("check_command" or "event_handler")
        :type prop: str
        :return: None
        """
        commandcall = getattr(obj, prop, None)
        # if the command call is void, bypass it
        if not commandcall:
            setattr(obj, prop, None)
            return
        cmdname = commandcall.command
        command = self.commands.find_by_name(cmdname)
        commandcall.command = command

    def linkify_commands(self, obj, prop):
        """
        Replace the command_name by the command object in obj.prop

        :param obj: A notification way object
        :type obj: alignak.objects.notificationway.NotificationWay
        :param prop: an attribute to replace
                     ('host_notification_commands' or 'service_notification_commands')
        :type prop: str
        :return: None
        """
        commandcalls = getattr(obj, prop, None)
        if not commandcalls:
            # If do not have a command list, put a void list instead
            setattr(obj, prop, [])
            return

        for commandcall in commandcalls:
            cmdname = commandcall.command
            command = self.commands.find_by_name(cmdname)
            commandcall.command = command

    def linkify_a_timeperiod(self, obj, prop):
        """
        Replace the timeperiod_name by the timeperiod object in obj.prop

        :param obj: A notification way object
        :type obj: alignak.objects.notificationway.NotificationWay
        :param prop: an attribute to replace
                     ('host_notification_period' or 'service_notification_period')
        :type prop: str
        :return: None
        """
        raw_timeperiod = getattr(obj, prop, None)
        if not raw_timeperiod:
            setattr(obj, prop, None)
            return
        tpname = raw_timeperiod.timeperiod_name
        timeperiod = self.timeperiods.find_by_name(tpname)
        setattr(obj, prop, timeperiod)

    def linkify_a_timeperiod_by_name(self, obj, prop):
        """
        Replace the timeperiod_name by the timeperiod object in obj.prop

        :param obj: A host or a service
        :type obj: alignak.objects.SchedulingItem
        :param prop: an attribute to replace
                     ('notification_period' or 'check_period')
        :type prop: str
        :return: None
        """
        tpname = getattr(obj, prop, None)
        if not tpname:
            setattr(obj, prop, None)
            return
        timeperiod = self.timeperiods.find_by_name(tpname)
        setattr(obj, prop, timeperiod)

    def linkify_contacts(self, obj, prop):
        """
        Replace the contact_name by the contact object in obj.prop

        :param obj: A host or a service
        :type obj: alignak.objects.SchedulingItem
        :param prop: an attribute to replace ('contacts')
        :type prop: str
        :return: None
        """
        contacts = getattr(obj, prop)

        if not contacts:
            return

        new_v = []
        for cname in contacts:
            contact = self.contacts.find_by_name(cname)
            if contact:
                new_v.append(contact)
        setattr(obj, prop, new_v)

    def linkify_dict_srv_and_hosts(self, obj, prop):
        """
        Replace the dict with host and service name by the host or service object in obj.prop

        :param obj: A host or a service
        :type obj: alignak.objects.SchedulingItem
        :param prop: an attribute to replace
            ('impacts', 'source_problems', 'parent_dependencies' or 'child_dependencies'))
        :type prop: str
        :return: None
        """
        problems = getattr(obj, prop)

        if not problems:
            setattr(obj, prop, [])

        new_v = []
        # print "Linkify Dict SRV/Host", v, obj.get_name(), prop
        for name in problems['services']:
            elts = name.split('/')
            hname = elts[0]
            sdesc = elts[1]
            serv = self.services.find_srv_by_name_and_hostname(hname, sdesc)
            if serv:
                new_v.append(serv)
        for hname in problems['hosts']:
            host = self.hosts.find_by_name(hname)
            if host:
                new_v.append(host)
        setattr(obj, prop, new_v)

    def linkify_host_and_hosts(self, obj, prop):
        """
        Replace the host_name by the host object in obj.prop

        :param obj: A host or a service
        :type obj: alignak.objects.SchedulingItem
        :param prop: an attribute to replace
            (''parents' 'childs')
        :type prop: str
        :return: None
        """
        hosts = getattr(obj, prop)

        if not hosts:
            setattr(obj, prop, [])

        new_v = []
        for hname in hosts:
            host = self.hosts.find_by_name(hname)
            if host:
                new_v.append(host)
        setattr(obj, prop, new_v)

###############
# Brok management part
###############

    def before_after_hook(self, brok, obj):
        """
        This can be used by derived classes to compare the data in the brok
        with the object which will be updated by these data. For example,
        it is possible to find out in this method whether the state of a
        host or service has changed.
        """
        pass

#######
# INITIAL PART
#######

    def manage_program_status_brok(self, brok):
        """
        Manage program_status brok : Reset objects for the given config id

        :param brok: Brok containing new config
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        c_id = data['instance_id']
        safe_print("Regenerator: Creating config:", c_id)

        # We get a real Conf object ,adn put our data
        conf = Config()
        self.update_element(conf, data)

        # Clean all in_progress things.
        # And in progress one
        self.inp_hosts[c_id] = Hosts([])
        self.inp_services[c_id] = Services([])
        self.inp_hostgroups[c_id] = Hostgroups([])
        self.inp_servicegroups[c_id] = Servicegroups([])
        self.inp_contactgroups[c_id] = Contactgroups([])

        # And we save it
        self.configs[c_id] = conf

        # Clean the old "hard" objects

        # We should clean all previously added hosts and services
        safe_print("Clean hosts/service of", c_id)
        to_del_h = [h for h in self.hosts if h.instance_id == c_id]
        to_del_srv = [s for s in self.services if s.instance_id == c_id]

        safe_print("Cleaning host:%d srv:%d" % (len(to_del_h), len(to_del_srv)))
        # Clean hosts from hosts and hostgroups
        for host in to_del_h:
            safe_print("Deleting", host.get_name())
            del self.hosts[host._id]

        # Now clean all hostgroups too
        for hostgroup in self.hostgroups:
            safe_print("Cleaning hostgroup %s:%d" % (hostgroup.get_name(), len(hostgroup.members)))
            # Exclude from members the hosts with this inst_id
            hostgroup.members = [host for host in hostgroup.members if host.instance_id != c_id]
            safe_print("Len after", len(hostgroup.members))

        for serv in to_del_srv:
            safe_print("Deleting", serv.get_full_name())
            del self.services[serv._id]

        # Now clean service groups
        for servicegroup in self.servicegroups:
            servicegroup.members = [s for s in servicegroup.members if s.instance_id != c_id]

    def manage_initial_host_status_brok(self, brok):
        """
        Manage initial_host_status brok : Update host object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        hname = data['host_name']
        inst_id = data['instance_id']

        # Try to get the inp progress Hosts
        try:
            inp_hosts = self.inp_hosts[inst_id]
        except Exception, exp:  # not good. we will cry in theprogram update
            print "Not good!", exp
            return
        # safe_print("Creating a host: %s in instance %d" % (hname, inst_id))

        host = Host({})
        self.update_element(host, data)

        # We need to rebuild Downtime and Comment relationship
        for dtc in host.downtimes + host.comments:
            dtc.ref = host

        # Ok, put in in the in progress hosts
        inp_hosts[host._id] = host

    def manage_initial_hostgroup_status_brok(self, brok):
        """
        Manage initial_hostgroup_status brok : Update hostgroup object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        hgname = data['hostgroup_name']
        inst_id = data['instance_id']

        # Try to get the inp progress Hostgroups
        try:
            inp_hostgroups = self.inp_hostgroups[inst_id]
        except Exception, exp:  # not good. we will cry in theprogram update
            print "Not good!", exp
            return

        safe_print("Creating a hostgroup: %s in instance %d" % (hgname, inst_id))

        # With void members
        hostgroup = Hostgroup([])

        # populate data
        self.update_element(hostgroup, data)

        # We will link hosts into hostgroups later
        # so now only save it
        inp_hostgroups[hostgroup._id] = hostgroup

    def manage_initial_service_status_brok(self, brok):
        """
        Manage initial_service_status brok : Update service object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        hname = data['host_name']
        sdesc = data['service_description']
        inst_id = data['instance_id']

        # Try to get the inp progress Hosts
        try:
            inp_services = self.inp_services[inst_id]
        except Exception, exp:  # not good. we will cry in theprogram update
            print "Not good!", exp
            return
        # safe_print("Creating a service: %s/%s in instance %d" % (hname, sdesc, inst_id))

        serv = Service({})
        self.update_element(serv, data)

        # We need to rebuild Downtime and Comment relationship
        for dtc in serv.downtimes + serv.comments:
            dtc.ref = serv

        # Ok, put in in the in progress hosts
        inp_services[serv._id] = serv

    def manage_initial_servicegroup_status_brok(self, brok):
        """
        Manage initial_servicegroup_status brok : Update servicegroup object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        sgname = data['servicegroup_name']
        inst_id = data['instance_id']

        # Try to get the inp progress Hostgroups
        try:
            inp_servicegroups = self.inp_servicegroups[inst_id]
        except Exception, exp:  # not good. we will cry in theprogram update
            print "Not good!", exp
            return

        safe_print("Creating a servicegroup: %s in instance %d" % (sgname, inst_id))

        # With void members
        servicegroup = Servicegroup([])

        # populate data
        self.update_element(servicegroup, data)

        # We will link hosts into hostgroups later
        # so now only save it
        inp_servicegroups[servicegroup._id] = servicegroup

    def manage_initial_contact_status_brok(self, brok):
        """
        Manage initial_contact_status brok : Update contact object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        cname = data['contact_name']
        safe_print("Contact with data", data)
        contact = self.contacts.find_by_name(cname)
        if contact:
            self.update_element(contact, data)
        else:
            safe_print("Creating Contact:", cname)
            contact = Contact({})
            self.update_element(contact, data)
            self.contacts.add_item(contact)

        # Delete some useless contact values
        del contact.host_notification_commands
        del contact.service_notification_commands
        del contact.host_notification_period
        del contact.service_notification_period

        # Now manage notification ways too
        # Same than for contacts. We create or
        # update
        nws = contact.notificationways
        safe_print("Got notif ways", nws)
        new_notifways = []
        for cnw in nws:
            nwname = cnw.notificationway_name
            notifway = self.notificationways.find_by_name(nwname)
            if not notifway:
                safe_print("Creating notif way", nwname)
                notifway = NotificationWay([])
                self.notificationways.add_item(notifway)
            # Now update it
            for prop in NotificationWay.properties:
                if hasattr(cnw, prop):
                    setattr(notifway, prop, getattr(cnw, prop))
            new_notifways.append(notifway)

            # Linking the notification way
            # With commands
            self.linkify_commands(notifway, 'host_notification_commands')
            self.linkify_commands(notifway, 'service_notification_commands')

            # Now link timeperiods
            self.linkify_a_timeperiod(notifway, 'host_notification_period')
            self.linkify_a_timeperiod(notifway, 'service_notification_period')

        contact.notificationways = new_notifways

    def manage_initial_contactgroup_status_brok(self, brok):
        """
        Manage initial_contactgroup_status brok : Update contactgroup object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        cgname = data['contactgroup_name']
        inst_id = data['instance_id']

        # Try to get the inp progress Contactgroups
        try:
            inp_contactgroups = self.inp_contactgroups[inst_id]
        except Exception, exp:  # not good. we will cry in theprogram update
            print "Not good!", exp
            return

        safe_print("Creating an contactgroup: %s in instance %d" % (cgname, inst_id))

        # With void members
        contactgroup = Contactgroup([])

        # populate data
        self.update_element(contactgroup, data)

        # We will link contacts into contactgroups later
        # so now only save it
        inp_contactgroups[contactgroup._id] = contactgroup

    def manage_initial_timeperiod_status_brok(self, brok):
        """
        Manage initial_timeperiod_status brok : Update timeperiod object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        # print "Creating timeperiod", data
        tpname = data['timeperiod_name']

        timeperiod = self.timeperiods.find_by_name(tpname)
        if timeperiod:
            # print "Already existing timeperiod", tpname
            self.update_element(timeperiod, data)
        else:
            # print "Creating Timeperiod:", tpname
            timeperiod = Timeperiod({})
            self.update_element(timeperiod, data)
            self.timeperiods.add_item(timeperiod)

    def manage_initial_command_status_brok(self, brok):
        """
        Manage initial_command_status brok : Update command object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        cname = data['command_name']

        command = self.commands.find_by_name(cname)
        if command:
            # print "Already existing command", cname, "updating it"
            self.update_element(command, data)
        else:
            # print "Creating a new command", cname
            command = Command({})
            self.update_element(command, data)
            self.commands.add_item(command)

    def manage_initial_scheduler_status_brok(self, brok):
        """
        Manage initial_scheduler_status brok : Update scheduler object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        scheduler_name = data['scheduler_name']
        print "Creating Scheduler:", scheduler_name, data
        sched = SchedulerLink({})
        print "Created a new scheduler", sched
        self.update_element(sched, data)
        print "Updated scheduler"
        # print "CMD:", c
        self.schedulers[scheduler_name] = sched
        print "scheduler added"

    def manage_initial_poller_status_brok(self, brok):
        """
        Manage initial_poller_status brok : Update poller object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        poller_name = data['poller_name']
        print "Creating Poller:", poller_name, data
        poller = PollerLink({})
        print "Created a new poller", poller
        self.update_element(poller, data)
        print "Updated poller"
        # print "CMD:", c
        self.pollers[poller_name] = poller
        print "poller added"

    def manage_initial_reactionner_status_brok(self, brok):
        """
        Manage initial_reactionner_status brok : Update reactionner object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        reactionner_name = data['reactionner_name']
        print "Creating Reactionner:", reactionner_name, data
        reac = ReactionnerLink({})
        print "Created a new reactionner", reac
        self.update_element(reac, data)
        print "Updated reactionner"
        # print "CMD:", c
        self.reactionners[reactionner_name] = reac
        print "reactionner added"

    def manage_initial_broker_status_brok(self, brok):
        """
        Manage initial_broker_status brok : Update broker object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        broker_name = data['broker_name']
        print "Creating Broker:", broker_name, data
        broker = BrokerLink({})
        print "Created a new broker", broker
        self.update_element(broker, data)
        print "Updated broker"
        # print "CMD:", c
        self.brokers[broker_name] = broker
        print "broker added"

    def manage_initial_receiver_status_brok(self, brok):
        """
        Manage initial_receiver_status brok : Update receiver object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        receiver_name = data['receiver_name']
        print "Creating Receiver:", receiver_name, data
        receiver = ReceiverLink({})
        print "Created a new receiver", receiver
        self.update_element(receiver, data)
        print "Updated receiver"
        # print "CMD:", c
        self.receivers[receiver_name] = receiver
        print "receiver added"

    def manage_initial_broks_done_brok(self, brok):
        """
        Manage initial_broks_done brok : Call all_done_linking with the instance_id in the brok

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        inst_id = brok.data['instance_id']
        print "Finish the configuration of instance", inst_id
        self.all_done_linking(inst_id)


#################
# Status Update part
#################

    def manage_update_program_status_brok(self, brok):
        """
        Manage update_program_status brok : Update config object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        c_id = data['instance_id']

        # If we got an update about an unknown instance, cry and ask for a full
        # version!
        if c_id not in self.configs.keys():
            # Do not ask data too quickly, very dangerous
            # one a minute
            if time.time() - self.last_need_data_send > 60 and self.from_q is not None:
                print "I ask the broker for instance id data:", c_id
                msg = Message(_id=0, _type='NeedData', data={'full_instance_id': c_id})
                self.from_q.put(msg)
                self.last_need_data_send = time.time()
            return

        # Ok, good conf, we can update it
        conf = self.configs[c_id]
        self.update_element(conf, data)

    def manage_update_host_status_brok(self, brok):
        """
        Manage update_host_status brok : Update host object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        # There are some properties that should not change and are already linked
        # so just remove them
        clean_prop = ['check_command', 'hostgroups',
                      'contacts', 'notification_period', 'contact_groups',
                      'check_period', 'event_handler',
                      'maintenance_period', 'realm', 'customs', 'escalations']

        # some are only use when a topology change happened
        toplogy_change = brok.data['topology_change']
        if not toplogy_change:
            other_to_clean = ['childs', 'parents', 'child_dependencies', 'parent_dependencies']
            clean_prop.extend(other_to_clean)

        data = brok.data
        for prop in clean_prop:
            del data[prop]

        hname = data['host_name']
        host = self.hosts.find_by_name(hname)

        if host:
            self.before_after_hook(brok, host)
            self.update_element(host, data)

            # We can have some change in our impacts and source problems.
            self.linkify_dict_srv_and_hosts(host, 'impacts')
            self.linkify_dict_srv_and_hosts(host, 'source_problems')

            # If the topology change, update it
            if toplogy_change:
                print "Topology change for", host.get_name(), host.parent_dependencies
                self.linkify_host_and_hosts(host, 'parents')
                self.linkify_host_and_hosts(host, 'childs')
                self.linkify_dict_srv_and_hosts(host, 'parent_dependencies')
                self.linkify_dict_srv_and_hosts(host, 'child_dependencies')

            # Relink downtimes and comments
            for dtc in host.downtimes + host.comments:
                dtc.ref = host

    def manage_update_service_status_brok(self, brok):
        """
        Manage update_service_status brok : Update service object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        # There are some properties that should not change and are already linked
        # so just remove them
        clean_prop = ['check_command', 'servicegroups',
                      'contacts', 'notification_period', 'contact_groups',
                      'check_period', 'event_handler',
                      'maintenance_period', 'customs', 'escalations']

        # some are only use when a topology change happened
        toplogy_change = brok.data['topology_change']
        if not toplogy_change:
            other_to_clean = ['child_dependencies', 'parent_dependencies']
            clean_prop.extend(other_to_clean)

        data = brok.data
        for prop in clean_prop:
            del data[prop]

        hname = data['host_name']
        sdesc = data['service_description']
        serv = self.services.find_srv_by_name_and_hostname(hname, sdesc)
        if serv:
            self.before_after_hook(brok, serv)
            self.update_element(serv, data)

            # We can have some change in our impacts and source problems.
            self.linkify_dict_srv_and_hosts(serv, 'impacts')
            self.linkify_dict_srv_and_hosts(serv, 'source_problems')

            # If the topology change, update it
            if toplogy_change:
                self.linkify_dict_srv_and_hosts(serv, 'parent_dependencies')
                self.linkify_dict_srv_and_hosts(serv, 'child_dependencies')

            # Relink downtimes and comments with the service
            for dtc in serv.downtimes + serv.comments:
                dtc.ref = serv

    def manage_update_broker_status_brok(self, brok):
        """
        Manage update_broker_status brok : Update broker object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        broker_name = data['broker_name']
        try:
            broker = self.brokers[broker_name]
            self.update_element(broker, data)
        except Exception:
            pass

    def manage_update_receiver_status_brok(self, brok):
        """
        Manage update_receiver_status brok : Update receiver object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        receiver_name = data['receiver_name']
        try:
            receiver = self.receivers[receiver_name]
            self.update_element(receiver, data)
        except Exception:
            pass

    def manage_update_reactionner_status_brok(self, brok):
        """
        Manage update_reactionner_status brok : Update reactionner object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        reactionner_name = data['reactionner_name']
        try:
            reactionner = self.reactionners[reactionner_name]
            self.update_element(reactionner, data)
        except Exception:
            pass

    def manage_update_poller_status_brok(self, brok):
        """
        Manage update_poller_status brok : Update poller object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        poller_name = data['poller_name']
        try:
            poller = self.pollers[poller_name]
            self.update_element(poller, data)
        except Exception:
            pass

    def manage_update_scheduler_status_brok(self, brok):
        """
        Manage update_scheduler_status brok : Update scheduler object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        scheduler_name = data['scheduler_name']
        try:
            scheduler = self.schedulers[scheduler_name]
            self.update_element(scheduler, data)
            # print "S:", s
        except Exception:
            pass


#################
# Check result and schedule part
#################
    def manage_host_check_result_brok(self, brok):
        """
        Manage host_check_result brok : Update host object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        hname = data['host_name']

        host = self.hosts.find_by_name(hname)
        if host:
            self.before_after_hook(brok, host)
            self.update_element(host, data)

    def manage_host_next_schedule_brok(self, brok):
        """
        Manage initial_timeperiod_status brok : Same as manage_host_check_result_brok

        :return: None
        """
        self.manage_host_check_result_brok(brok)

    def manage_service_check_result_brok(self, brok):
        """
        Manage service_check_result brok : Update service object

        :param brok: Brok containing new data
        :type brok: alignak.objects.brok.Brok
        :return: None
        """
        data = brok.data
        hname = data['host_name']
        sdesc = data['service_description']
        serv = self.services.find_srv_by_name_and_hostname(hname, sdesc)
        if serv:
            self.before_after_hook(brok, serv)
            self.update_element(serv, data)

    def manage_service_next_schedule_brok(self, brok):
        """
        Manage service_next_schedule brok : Same as manage_service_check_result_brok
        A service check update have just arrived, we UPDATE data info with this

        :return: None
        """
        self.manage_service_check_result_brok(brok)
