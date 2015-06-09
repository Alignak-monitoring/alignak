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
        c = sched.conf
        # Simulate a drop conf
        b = sched.get_program_status_brok()
        b.prepare()
        self.manage_program_status_brok(b)

        # Now we will lie and directly map our objects :)
        print "Regenerator::load_from_scheduler"
        self.hosts = c.hosts
        self.services = c.services
        self.notificationways = c.notificationways
        self.contacts = c.contacts
        self.hostgroups = c.hostgroups
        self.servicegroups = c.servicegroups
        self.contactgroups = c.contactgroups
        self.timeperiods = c.timeperiods
        self.commands = c.commands
        # We also load the realm
        for h in self.hosts:
            self.realms.add(h.realm)
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
        """
        Look for a manager function for a brok, and call it
        """
        manage = getattr(self, 'manage_' + brok.type + '_brok', None)
        # If we can and want it, got for it :)
        if manage and self.want_brok(brok):
            return manage(brok)


    def update_element(self, e, data):
        """
        Update object attibute with value contained in data keys

        :param e: A alignak object
        :type e: alignak.object.Item
        :param data: the dict containing attribute to update
        :type data: dict
        :return: None
        """
        for prop in data:
            setattr(e, prop, data[prop])


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
        for hg in inp_hostgroups:
            new_members = []
            for (i, hname) in hg.members:
                h = inp_hosts.find_by_name(hname)
                if h:
                    new_members.append(h)
            hg.members = new_members

        # Merge HOSTGROUPS with real ones
        for inphg in inp_hostgroups:
            hgname = inphg.hostgroup_name
            hg = self.hostgroups.find_by_name(hgname)
            # If hte hostgroup already exist, just add the new
            # hosts into it
            if hg:
                hg.members.extend(inphg.members)
            else:  # else take the new one
                self.hostgroups.add_item(inphg)

        # Now link HOSTS with hostgroups, and commands
        for h in inp_hosts:
            # print "Linking %s groups %s" % (h.get_name(), h.hostgroups)
            new_hostgroups = []
            for hgname in h.hostgroups.split(','):
                hgname = hgname.strip()
                hg = self.hostgroups.find_by_name(hgname)
                if hg:
                    new_hostgroups.append(hg)
            h.hostgroups = new_hostgroups

            # Now link Command() objects
            self.linkify_a_command(h, 'check_command')
            self.linkify_a_command(h, 'event_handler')

            # Now link timeperiods
            self.linkify_a_timeperiod_by_name(h, 'notification_period')
            self.linkify_a_timeperiod_by_name(h, 'check_period')
            self.linkify_a_timeperiod_by_name(h, 'maintenance_period')

            # And link contacts too
            self.linkify_contacts(h, 'contacts')

            # Linkify tags
            for t in h.tags:
                if t not in self.tags:
                    self.tags[t] = 0
                self.tags[t] += 1

            # We can really declare this host OK now
            self.hosts.add_item(h)

        # Link SERVICEGROUPS with services
        for sg in inp_servicegroups:
            new_members = []
            for (i, sname) in sg.members:
                if i not in inp_services:
                    continue
                s = inp_services[i]
                new_members.append(s)
            sg.members = new_members


        # Merge SERVICEGROUPS with real ones
        for inpsg in inp_servicegroups:
            sgname = inpsg.servicegroup_name
            sg = self.servicegroups.find_by_name(sgname)
            # If the servicegroup already exist, just add the new
            # services into it
            if sg:
                sg.members.extend(inpsg.members)
            else:  # else take the new one
                self.servicegroups.add_item(inpsg)

        # Now link SERVICES with hosts, servicesgroups, and commands
        for s in inp_services:
            new_servicegroups = []
            for sgname in s.servicegroups.split(','):
                sgname = sgname.strip()
                sg = self.servicegroups.find_by_name(sgname)
                if sg:
                    new_servicegroups.append(sg)
            s.servicegroups = new_servicegroups

            # Now link with host
            hname = s.host_name
            s.host = self.hosts.find_by_name(hname)
            if s.host:
                s.host.services.append(s)

            # Now link Command() objects
            self.linkify_a_command(s, 'check_command')
            self.linkify_a_command(s, 'event_handler')

            # Now link timeperiods
            self.linkify_a_timeperiod_by_name(s, 'notification_period')
            self.linkify_a_timeperiod_by_name(s, 'check_period')
            self.linkify_a_timeperiod_by_name(s, 'maintenance_period')

            # And link contacts too
            self.linkify_contacts(s, 'contacts')

            # Linkify services tags
            for t in s.tags:
                if t not in self.services_tags:
                    self.services_tags[t] = 0
                self.services_tags[t] += 1

            # We can really declare this host OK now
            self.services.add_item(s, index=True)


        # Add realm of theses hosts. Only the first is useful
        for h in inp_hosts:
            self.realms.add(h.realm)
            break

        # Now we can link all impacts/source problem list
        # but only for the new ones here of course
        for h in inp_hosts:
            self.linkify_dict_srv_and_hosts(h, 'impacts')
            self.linkify_dict_srv_and_hosts(h, 'source_problems')
            self.linkify_host_and_hosts(h, 'parents')
            self.linkify_host_and_hosts(h, 'childs')
            self.linkify_dict_srv_and_hosts(h, 'parent_dependencies')
            self.linkify_dict_srv_and_hosts(h, 'child_dependencies')


        # Now services too
        for s in inp_services:
            self.linkify_dict_srv_and_hosts(s, 'impacts')
            self.linkify_dict_srv_and_hosts(s, 'source_problems')
            self.linkify_dict_srv_and_hosts(s, 'parent_dependencies')
            self.linkify_dict_srv_and_hosts(s, 'child_dependencies')

        # Linking TIMEPERIOD exclude with real ones now
        for tp in self.timeperiods:
            new_exclude = []
            for ex in tp.exclude:
                exname = ex.timeperiod_name
                t = self.timeperiods.find_by_name(exname)
                if t:
                    new_exclude.append(t)
            tp.exclude = new_exclude

        # Link CONTACTGROUPS with contacts
        for cg in inp_contactgroups:
            new_members = []
            for (i, cname) in cg.members:
                c = self.contacts.find_by_name(cname)
                if c:
                    new_members.append(c)
            cg.members = new_members

        # Merge contactgroups with real ones
        for inpcg in inp_contactgroups:
            cgname = inpcg.contactgroup_name
            cg = self.contactgroups.find_by_name(cgname)
            # If the contactgroup already exist, just add the new
            # contacts into it
            if cg:
                cg.members.extend(inpcg.members)
                cg.members = list(set(cg.members))
            else:  # else take the new one
                self.contactgroups.add_item(inpcg)

        safe_print("ALL LINKING TIME" * 10, time.time() - start)

        # clean old objects
        del self.inp_hosts[inst_id]
        del self.inp_hostgroups[inst_id]
        del self.inp_contactgroups[inst_id]
        del self.inp_services[inst_id]
        del self.inp_servicegroups[inst_id]


    def linkify_a_command(self, o, prop):
        """
        Replace the command_name by the command object in o.prop

        :param o: A host or a service
        :type o: alignak.objects.schedulingitem.SchedulingItem
        :param prop: an attribute to replace ("check_command" or "event_handler")
        :return: None
        """
        cc = getattr(o, prop, None)
        # if the command call is void, bypass it
        if not cc:
            setattr(o, prop, None)
            return
        cmdname = cc.command
        c = self.commands.find_by_name(cmdname)
        cc.command = c

    def linkify_commands(self, o, prop):
        """
        Replace the command_name by the command object in o.prop

        :param o: A notification way object
        :type o: alignak.objects.notificationway.NotificationWay
        :param prop: an attribute to replace
                     ('host_notification_commands' or 'service_notification_commands')
        :return: None
        """
        v = getattr(o, prop, None)
        if not v:
            # If do not have a command list, put a void list instead
            setattr(o, prop, [])
            return

        for cc in v:
            cmdname = cc.command
            c = self.commands.find_by_name(cmdname)
            cc.command = c

    def linkify_a_timeperiod(self, o, prop):
        """
        Replace the timeperiod_name by the timeperiod object in o.prop

        :param o: A notification way object
        :type o: alignak.objects.notificationway.NotificationWay
        :param prop: an attribute to replace
                     ('host_notification_period' or 'service_notification_period')
        :return: None
        """
        t = getattr(o, prop, None)
        if not t:
            setattr(o, prop, None)
            return
        tpname = t.timeperiod_name
        tp = self.timeperiods.find_by_name(tpname)
        setattr(o, prop, tp)

    def linkify_a_timeperiod_by_name(self, o, prop):
        """
        Replace the timeperiod_name by the timeperiod object in o.prop

        :param o: A host or a service
        :type o: alignak.objects.SchedulingItem
        :param prop: an attribute to replace
                     ('notification_period' or 'check_period')
        :return: None
        """
        tpname = getattr(o, prop, None)
        if not tpname:
            setattr(o, prop, None)
            return
        tp = self.timeperiods.find_by_name(tpname)
        setattr(o, prop, tp)

    def linkify_contacts(self, o, prop):
        """
        Replace the contact_name by the contact object in o.prop

        :param o: A host or a service
        :type o: alignak.objects.SchedulingItem
        :param prop: an attribute to replace ('contacts')
        :return: None
        """
        v = getattr(o, prop)

        if not v:
            return

        new_v = []
        for cname in v:
            c = self.contacts.find_by_name(cname)
            if c:
                new_v.append(c)
        setattr(o, prop, new_v)

    def linkify_dict_srv_and_hosts(self, o, prop):
        """
        Replace the dict with host and service name by the host or service object in o.prop

        :param o: A host or a service
        :type o: alignak.objects.SchedulingItem
        :param prop: an attribute to replace
            ('impacts', 'source_problems', 'parent_dependencies' or 'child_dependencies'))
        :return: None
        """
        v = getattr(o, prop)

        if not v:
            setattr(o, prop, [])

        new_v = []
        # print "Linkify Dict SRV/Host", v, o.get_name(), prop
        for name in v['services']:
            elts = name.split('/')
            hname = elts[0]
            sdesc = elts[1]
            s = self.services.find_srv_by_name_and_hostname(hname, sdesc)
            if s:
                new_v.append(s)
        for hname in v['hosts']:
            h = self.hosts.find_by_name(hname)
            if h:
                new_v.append(h)
        setattr(o, prop, new_v)

    def linkify_host_and_hosts(self, o, prop):
        """
        Replace the host_name by the host object in o.prop

        :param o: A host or a service
        :type o: alignak.objects.SchedulingItem
        :param prop: an attribute to replace
            (''parents' 'childs')
        :return: None
        """
        v = getattr(o, prop)

        if not v:
            setattr(o, prop, [])

        new_v = []
        for hname in v:
            h = self.hosts.find_by_name(hname)
            if h:
                new_v.append(h)
        setattr(o, prop, new_v)

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

    def manage_program_status_brok(self, b):
        """
        Manage program_status brok : Reset objects for the given config id

        :param b: Brok containing new config
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        c_id = data['instance_id']
        safe_print("Regenerator: Creating config:", c_id)

        # We get a real Conf object ,adn put our data
        c = Config()
        self.update_element(c, data)

        # Clean all in_progress things.
        # And in progress one
        self.inp_hosts[c_id] = Hosts([])
        self.inp_services[c_id] = Services([])
        self.inp_hostgroups[c_id] = Hostgroups([])
        self.inp_servicegroups[c_id] = Servicegroups([])
        self.inp_contactgroups[c_id] = Contactgroups([])

        # And we save it
        self.configs[c_id] = c

        # Clean the old "hard" objects

        # We should clean all previously added hosts and services
        safe_print("Clean hosts/service of", c_id)
        to_del_h = [h for h in self.hosts if h.instance_id == c_id]
        to_del_srv = [s for s in self.services if s.instance_id == c_id]

        safe_print("Cleaning host:%d srv:%d" % (len(to_del_h), len(to_del_srv)))
        # Clean hosts from hosts and hostgroups
        for h in to_del_h:
            safe_print("Deleting", h.get_name())
            del self.hosts[h.id]

        # Now clean all hostgroups too
        for hg in self.hostgroups:
            safe_print("Cleaning hostgroup %s:%d" % (hg.get_name(), len(hg.members)))
            # Exclude from members the hosts with this inst_id
            hg.members = [h for h in hg.members if h.instance_id != c_id]
            safe_print("Len after", len(hg.members))

        for s in to_del_srv:
            safe_print("Deleting", s.get_full_name())
            del self.services[s.id]

        # Now clean service groups
        for sg in self.servicegroups:
            sg.members = [s for s in sg.members if s.instance_id != c_id]


    def manage_initial_host_status_brok(self, b):
        """
        Manage initial_host_status brok : Update host object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        hname = data['host_name']
        inst_id = data['instance_id']

        # Try to get the inp progress Hosts
        try:
            inp_hosts = self.inp_hosts[inst_id]
        except Exception, exp:  # not good. we will cry in theprogram update
            print "Not good!", exp
            return
        # safe_print("Creating a host: %s in instance %d" % (hname, inst_id))

        h = Host({})
        self.update_element(h, data)

        # We need to rebuild Downtime and Comment relationship
        for dtc in h.downtimes + h.comments:
            dtc.ref = h

        # Ok, put in in the in progress hosts
        inp_hosts[h.id] = h


    def manage_initial_hostgroup_status_brok(self, b):
        """
        Manage initial_hostgroup_status brok : Update hostgroup object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
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
        hg = Hostgroup([])

        # populate data
        self.update_element(hg, data)

        # We will link hosts into hostgroups later
        # so now only save it
        inp_hostgroups[hg.id] = hg


    def manage_initial_service_status_brok(self, b):
        """
        Manage initial_service_status brok : Update service object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
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

        s = Service({})
        self.update_element(s, data)

        # We need to rebuild Downtime and Comment relationship
        for dtc in s.downtimes + s.comments:
            dtc.ref = s

        # Ok, put in in the in progress hosts
        inp_services[s.id] = s


    def manage_initial_servicegroup_status_brok(self, b):
        """
        Manage initial_servicegroup_status brok : Update servicegroup object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
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
        sg = Servicegroup([])

        # populate data
        self.update_element(sg, data)

        # We will link hosts into hostgroups later
        # so now only save it
        inp_servicegroups[sg.id] = sg


    def manage_initial_contact_status_brok(self, b):
        """
        Manage initial_contact_status brok : Update contact object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        cname = data['contact_name']
        safe_print("Contact with data", data)
        c = self.contacts.find_by_name(cname)
        if c:
            self.update_element(c, data)
        else:
            safe_print("Creating Contact:", cname)
            c = Contact({})
            self.update_element(c, data)
            self.contacts.add_item(c)

        # Delete some useless contact values
        del c.host_notification_commands
        del c.service_notification_commands
        del c.host_notification_period
        del c.service_notification_period

        # Now manage notification ways too
        # Same than for contacts. We create or
        # update
        nws = c.notificationways
        safe_print("Got notif ways", nws)
        new_notifways = []
        for cnw in nws:
            nwname = cnw.notificationway_name
            nw = self.notificationways.find_by_name(nwname)
            if not nw:
                safe_print("Creating notif way", nwname)
                nw = NotificationWay([])
                self.notificationways.add_item(nw)
            # Now update it
            for prop in NotificationWay.properties:
                if hasattr(cnw, prop):
                    setattr(nw, prop, getattr(cnw, prop))
            new_notifways.append(nw)

            # Linking the notification way
            # With commands
            self.linkify_commands(nw, 'host_notification_commands')
            self.linkify_commands(nw, 'service_notification_commands')

            # Now link timeperiods
            self.linkify_a_timeperiod(nw, 'host_notification_period')
            self.linkify_a_timeperiod(nw, 'service_notification_period')

        c.notificationways = new_notifways


    def manage_initial_contactgroup_status_brok(self, b):
        """
        Manage initial_contactgroup_status brok : Update contactgroup object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
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
        cg = Contactgroup([])

        # populate data
        self.update_element(cg, data)

        # We will link contacts into contactgroups later
        # so now only save it
        inp_contactgroups[cg.id] = cg


    def manage_initial_timeperiod_status_brok(self, b):
        """
        Manage initial_timeperiod_status brok : Update timeperiod object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        # print "Creating timeperiod", data
        tpname = data['timeperiod_name']

        tp = self.timeperiods.find_by_name(tpname)
        if tp:
            # print "Already existing timeperiod", tpname
            self.update_element(tp, data)
        else:
            # print "Creating Timeperiod:", tpname
            tp = Timeperiod({})
            self.update_element(tp, data)
            self.timeperiods.add_item(tp)


    def manage_initial_command_status_brok(self, b):
        """
        Manage initial_command_status brok : Update command object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        cname = data['command_name']

        c = self.commands.find_by_name(cname)
        if c:
            # print "Already existing command", cname, "updating it"
            self.update_element(c, data)
        else:
            # print "Creating a new command", cname
            c = Command({})
            self.update_element(c, data)
            self.commands.add_item(c)


    def manage_initial_scheduler_status_brok(self, b):
        """
        Manage initial_scheduler_status brok : Update scheduler object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        scheduler_name = data['scheduler_name']
        print "Creating Scheduler:", scheduler_name, data
        sched = SchedulerLink({})
        print "Created a new scheduler", sched
        self.update_element(sched, data)
        print "Updated scheduler"
        # print "CMD:", c
        self.schedulers[scheduler_name] = sched
        print "scheduler added"


    def manage_initial_poller_status_brok(self, b):
        """
        Manage initial_poller_status brok : Update poller object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        poller_name = data['poller_name']
        print "Creating Poller:", poller_name, data
        poller = PollerLink({})
        print "Created a new poller", poller
        self.update_element(poller, data)
        print "Updated poller"
        # print "CMD:", c
        self.pollers[poller_name] = poller
        print "poller added"


    def manage_initial_reactionner_status_brok(self, b):
        """
        Manage initial_reactionner_status brok : Update reactionner object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        reactionner_name = data['reactionner_name']
        print "Creating Reactionner:", reactionner_name, data
        reac = ReactionnerLink({})
        print "Created a new reactionner", reac
        self.update_element(reac, data)
        print "Updated reactionner"
        # print "CMD:", c
        self.reactionners[reactionner_name] = reac
        print "reactionner added"


    def manage_initial_broker_status_brok(self, b):
        """
        Manage initial_broker_status brok : Update broker object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        broker_name = data['broker_name']
        print "Creating Broker:", broker_name, data
        broker = BrokerLink({})
        print "Created a new broker", broker
        self.update_element(broker, data)
        print "Updated broker"
        # print "CMD:", c
        self.brokers[broker_name] = broker
        print "broker added"


    def manage_initial_receiver_status_brok(self, b):
        """
        Manage initial_receiver_status brok : Update receiver object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        receiver_name = data['receiver_name']
        print "Creating Receiver:", receiver_name, data
        receiver = ReceiverLink({})
        print "Created a new receiver", receiver
        self.update_element(receiver, data)
        print "Updated receiver"
        # print "CMD:", c
        self.receivers[receiver_name] = receiver
        print "receiver added"



    def manage_initial_broks_done_brok(self, b):
        """
        Manage initial_broks_done brok : Call all_done_linking with the instance_id in the brok

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        inst_id = b.data['instance_id']
        print "Finish the configuration of instance", inst_id
        self.all_done_linking(inst_id)


#################
# Status Update part
#################

    def manage_update_program_status_brok(self, b):
        """
        Manage update_program_status brok : Update config object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        c_id = data['instance_id']

        # If we got an update about an unknown instance, cry and ask for a full
        # version!
        if c_id not in self.configs.keys():
            # Do not ask data too quickly, very dangerous
            # one a minute
            if time.time() - self.last_need_data_send > 60 and self.from_q is not None:
                print "I ask the broker for instance id data:", c_id
                msg = Message(id=0, type='NeedData', data={'full_instance_id': c_id})
                self.from_q.put(msg)
                self.last_need_data_send = time.time()
            return

        # Ok, good conf, we can update it
        c = self.configs[c_id]
        self.update_element(c, data)


    def manage_update_host_status_brok(self, b):
        """
        Manage update_host_status brok : Update host object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        # There are some properties that should not change and are already linked
        # so just remove them
        clean_prop = ['check_command', 'hostgroups',
                      'contacts', 'notification_period', 'contact_groups',
                      'check_period', 'event_handler',
                      'maintenance_period', 'realm', 'customs', 'escalations']

        # some are only use when a topology change happened
        toplogy_change = b.data['topology_change']
        if not toplogy_change:
            other_to_clean = ['childs', 'parents', 'child_dependencies', 'parent_dependencies']
            clean_prop.extend(other_to_clean)

        data = b.data
        for prop in clean_prop:
            del data[prop]

        hname = data['host_name']
        h = self.hosts.find_by_name(hname)

        if h:
            self.before_after_hook(b, h)
            self.update_element(h, data)

            # We can have some change in our impacts and source problems.
            self.linkify_dict_srv_and_hosts(h, 'impacts')
            self.linkify_dict_srv_and_hosts(h, 'source_problems')

            # If the topology change, update it
            if toplogy_change:
                print "Topology change for", h.get_name(), h.parent_dependencies
                self.linkify_host_and_hosts(h, 'parents')
                self.linkify_host_and_hosts(h, 'childs')
                self.linkify_dict_srv_and_hosts(h, 'parent_dependencies')
                self.linkify_dict_srv_and_hosts(h, 'child_dependencies')

            # Relink downtimes and comments
            for dtc in h.downtimes + h.comments:
                dtc.ref = h


    def manage_update_service_status_brok(self, b):
        """
        Manage update_service_status brok : Update service object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        # There are some properties that should not change and are already linked
        # so just remove them
        clean_prop = ['check_command', 'servicegroups',
                      'contacts', 'notification_period', 'contact_groups',
                      'check_period', 'event_handler',
                      'maintenance_period', 'customs', 'escalations']

        # some are only use when a topology change happened
        toplogy_change = b.data['topology_change']
        if not toplogy_change:
            other_to_clean = ['child_dependencies', 'parent_dependencies']
            clean_prop.extend(other_to_clean)

        data = b.data
        for prop in clean_prop:
            del data[prop]

        hname = data['host_name']
        sdesc = data['service_description']
        s = self.services.find_srv_by_name_and_hostname(hname, sdesc)
        if s:
            self.before_after_hook(b, s)
            self.update_element(s, data)

            # We can have some change in our impacts and source problems.
            self.linkify_dict_srv_and_hosts(s, 'impacts')
            self.linkify_dict_srv_and_hosts(s, 'source_problems')

            # If the topology change, update it
            if toplogy_change:
                self.linkify_dict_srv_and_hosts(s, 'parent_dependencies')
                self.linkify_dict_srv_and_hosts(s, 'child_dependencies')

            # Relink downtimes and comments with the service
            for dtc in s.downtimes + s.comments:
                dtc.ref = s


    def manage_update_broker_status_brok(self, b):
        """
        Manage update_broker_status brok : Update broker object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        broker_name = data['broker_name']
        try:
            s = self.brokers[broker_name]
            self.update_element(s, data)
        except Exception:
            pass


    def manage_update_receiver_status_brok(self, b):
        """
        Manage update_receiver_status brok : Update receiver object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        receiver_name = data['receiver_name']
        try:
            s = self.receivers[receiver_name]
            self.update_element(s, data)
        except Exception:
            pass


    def manage_update_reactionner_status_brok(self, b):
        """
        Manage update_reactionner_status brok : Update reactionner object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        reactionner_name = data['reactionner_name']
        try:
            s = self.reactionners[reactionner_name]
            self.update_element(s, data)
        except Exception:
            pass


    def manage_update_poller_status_brok(self, b):
        """
        Manage update_poller_status brok : Update poller object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        poller_name = data['poller_name']
        try:
            s = self.pollers[poller_name]
            self.update_element(s, data)
        except Exception:
            pass


    def manage_update_scheduler_status_brok(self, b):
        """
        Manage update_scheduler_status brok : Update scheduler object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        scheduler_name = data['scheduler_name']
        try:
            s = self.schedulers[scheduler_name]
            self.update_element(s, data)
            # print "S:", s
        except Exception:
            pass


#################
# Check result and schedule part
#################
    def manage_host_check_result_brok(self, b):
        """
        Manage host_check_result brok : Update host object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        hname = data['host_name']

        h = self.hosts.find_by_name(hname)
        if h:
            self.before_after_hook(b, h)
            self.update_element(h, data)


    def manage_host_next_schedule_brok(self, b):
        """
        Manage initial_timeperiod_status brok : Same as manage_host_check_result_brok
        """
        self.manage_host_check_result_brok(b)


    def manage_service_check_result_brok(self, b):
        """
        Manage service_check_result brok : Update service object

        :param b: Brok containing new data
        :type b: alignak.objects.brok.Brok
        :return: None
        """
        data = b.data
        hname = data['host_name']
        sdesc = data['service_description']
        s = self.services.find_srv_by_name_and_hostname(hname, sdesc)
        if s:
            self.before_after_hook(b, s)
            self.update_element(s, data)


    # A service check update have just arrived, we UPDATE data info with this
    def manage_service_next_schedule_brok(self, b):
        """
        Manage service_next_schedule brok : Same as manage_service_check_result_brok
        """
        self.manage_service_check_result_brok(b)
