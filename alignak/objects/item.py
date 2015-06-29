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
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Guillaume Bour, guillaume@bour.cc
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Arthur Gautier, superbaloo@superbaloo.net
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Jan Ulferts, jan.ulferts@xing.com
#     Grégory Starck, g.starck@gmail.com
#     Alexander Springer, alex.spri@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Christophe Simon, geektophe@gmail.com
#     Romain Forlot, rforlot@yahoo.com
#     Christophe SIMON, christophe.simon@dailymotion.com

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
This class is a base class for nearly all configuration
elements like service, hosts or contacts.
"""
import time
import cPickle  # for hashing compute
import itertools

# Try to import md5 function
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from copy import copy

from alignak.commandcall import CommandCall
from alignak.property import (StringProp, ListProp, BoolProp,
                              IntegerProp, ToGuessProp, PythonizeError)
from alignak.brok import Brok
from alignak.util import strip_and_uniq, is_complex_expr
from alignak.acknowledge import Acknowledge
from alignak.comment import Comment
from alignak.log import logger
from alignak.complexexpression import ComplexExpressionFactory
from alignak.graph import Graph


class Item(object):
    """
    Class to manage an item
    An Item is the base of many objects of Alignak. So it define common properties,
    common functions.
    """
    properties = {
        'imported_from':            StringProp(default='unknown'),
        'use':                      ListProp(default=None, split_on_coma=True),
        'name':                     StringProp(default=''),
        'definition_order':         IntegerProp(default=100),
        # TODO: find why we can't uncomment this line below.
        'register':                 BoolProp(default=True),
    }

    running_properties = {
        # All errors and warning raised during the configuration parsing
        # and that will raised real warning/errors during the is_correct
        'configuration_warnings':   ListProp(default=[]),
        'configuration_errors':     ListProp(default=[]),
        # We save all template we asked us to load from
        'tags': ListProp(default=set(), fill_brok=['full_status']),
    }

    macros = {
    }

    def __init__(self, params={}):
        # We have our own id of My Class type :)
        # use set attr for going into the slots
        # instead of __dict__ :)
        cls = self.__class__
        self.id = cls.id
        cls.id += 1

        self.customs = {}  # for custom variables
        self.plus = {}  # for value with a +

        self.init_running_properties()
        # [0] = +  -> new key-plus
        # [0] = _  -> new custom entry in UPPER case
        for key in params:
            # We want to create instance of object with the good type.
            # Here we've just parsed config files so everything is a list.
            # We use the pythonize method to get the good type.
            try:
                if key in self.properties:
                    val = self.properties[key].pythonize(params[key])
                elif key in self.running_properties:
                    warning = "using a the running property %s in a config file" % key
                    self.configuration_warnings.append(warning)
                    val = self.running_properties[key].pythonize(params[key])
                elif hasattr(self, 'old_properties') and key in self.old_properties:
                    val = self.properties[self.old_properties[key]].pythonize(params[key])
                elif key.startswith('_'):  # custom macro, not need to detect something here
                    _t = params[key]
                    # If it's a string, directly use this
                    if isinstance(_t, basestring):
                        val = _t
                    # aa list for a custom macro is not managed (conceptually invalid)
                    # so take the first defined
                    elif isinstance(_t, list) and len(_t) > 0:
                        val = _t[0]
                    # not a list of void? just put void string so
                    else:
                        val = ''
                else:
                    warning = "Guessing the property %s type because it is not in %s object properties" % \
                              (key, cls.__name__)
                    self.configuration_warnings.append(warning)
                    val = ToGuessProp.pythonize(params[key])
            except (PythonizeError, ValueError) as expt:
                err = "Error while pythonizing parameter '%s': %s" % (key, expt)
                self.configuration_errors.append(err)
                continue

            # checks for attribute value special syntax (+ or _)
            # we can have '+param' or ['+template1' , 'template2']
            if isinstance(val, str) and len(val) >= 1 and val[0] == '+':
                err = "A + value for a single string is not handled"
                self.configuration_errors.append(err)
                continue

            if (isinstance(val, list) and
                    len(val) >= 1 and
                    isinstance(val[0], unicode) and
                    len(val[0]) >= 1 and
                    val[0][0] == '+'):
                # Special case: a _MACRO can be a plus. so add to plus
                # but upper the key for the macro name
                val[0] = val[0][1:]
                if key[0] == "_":

                    self.plus[key.upper()] = val  # we remove the +
                else:
                    self.plus[key] = val   # we remove the +
            elif key[0] == "_":
                if isinstance(val, list):
                    err = "no support for _ syntax in multiple valued attributes"
                    self.configuration_errors.append(err)
                    continue
                custom_name = key.upper()
                self.customs[custom_name] = val
            else:
                setattr(self, key, val)


    def compact_unique_attr_value(self, val):
        """
        Get value of first element of list if val is a list

        :param val: simple value (string, integer...) or list
        :type val: list or other (string, integer...)
        :return: value
        :rtype: str
        """
        if isinstance(val, list):
            if len(val) > 1:
                return val
            elif len(val) == 0:
                return ''
            else:
                return val[0]
        else:
            return val

    def init_running_properties(self):
        """
        Init the running_properties.
        Each instance have own property.
        """
        for prop, entry in self.__class__.running_properties.items():
            # Copy is slow, so we check type
            # Type with __iter__ are list or dict, or tuple.
            # Item need it's own list, so we copy
            val = entry.default
            if hasattr(val, '__iter__'):
                setattr(self, prop, copy(val))
            else:
                setattr(self, prop, val)
            # each instance to have his own running prop!

    def copy(self):
        """
        Get a copy of this item but with a new id

        :return: copy of this object with a new id
        :rtype: object
        """
        cls = self.__class__
        i = cls({})  # Dummy item but with it's own running properties
        for prop in cls.properties:
            if hasattr(self, prop):
                val = getattr(self, prop)
                setattr(i, prop, val)
        # Also copy the customs tab
        i.customs = copy(self.customs)
        # And tags/templates
        if hasattr(self, "tags"):
            i.tags = copy(self.tags)
        if hasattr(self, "templates"):
            i.templates = copy(self.templates)
        return i

    def clean(self):
        """
        Clean properties only need when initilize & configure
        """
        for name in ('imported_from', 'use', 'plus', 'templates',):
            try:
                delattr(self, name)
            except AttributeError:
                pass

    def get_name(self):
        """
        Get the name of the item

        :return: the object name string
        :rtype: str
        """
        return getattr(self, 'name', "unknown")

    def __str__(self):
        cls_name = self.__class__.__name__
        return '<%s "name"=%r />' % (cls_name, self.get_name())

    __repr__ = __str__

    def is_tpl(self):
        """
        Check if this object is a template

        :return: True if is a template, else False
        :rtype: bool
        """
        return not getattr(self, "register", True)

    def fill_default(self):
        """
        Define properties with default value when not defined
        """
        cls = self.__class__

        for prop, entry in cls.properties.items():
            if not hasattr(self, prop) and entry.has_default:
                setattr(self, prop, entry.default)

    def load_global_conf(cls, conf):
        """
        Load configuration of parent object

        :param cls: parent object
        :type cls: object
        :param conf: current object (child)
        :type conf: object
        """
        for prop, entry in conf.properties.items():
            # If we have a class_inherit, and the arbiter really send us it
            # if 'class_inherit' in entry and hasattr(conf, prop):
            if hasattr(conf, prop):
                for (cls_dest, change_name) in entry.class_inherit:
                    if cls_dest == cls:  # ok, we've got something to get
                        value = getattr(conf, prop)
                        if change_name is None:
                            setattr(cls, prop, value)
                        else:
                            setattr(cls, change_name, value)

    # Make this method a classmethod
    load_global_conf = classmethod(load_global_conf)

    def get_templates(self):
        """
        Get list of templates this object use

        :return: list of templates
        :rtype: list
        """
        use = getattr(self, 'use', '')
        if isinstance(use, list):
            return [n.strip() for n in use if n.strip()]
        else:
            return [n.strip() for n in use.split(',') if n.strip()]

    def get_property_by_inheritance(self, prop):
        """
        Get the property asked in parameter to this object or from defined templates of this
        object

        :param prop: name of property
        :type prop: str
        :return: Value of property of this object or of a template
        :rtype: str or None
        """
        if prop == 'register':
            return None  # We do not inherit from register

        # If I have the prop, I take mine but I check if I must
        # add a plus property
        if hasattr(self, prop):
            value = getattr(self, prop)
            # Manage the additive inheritance for the property,
            # if property is in plus, add or replace it
            # Template should keep the '+' at the beginning of the chain
            if self.has_plus(prop):
                value.insert(0, self.get_plus_and_delete(prop))
                if self.is_tpl():
                    value = list(value)
                    value.insert(0, '+')
            return value
        # Ok, I do not have prop, Maybe my templates do?
        # Same story for plus
        # We reverse list, so that when looking for properties by inheritance,
        # the least defined template wins (if property is set).
        for i in self.templates:
            value = i.get_property_by_inheritance(prop)

            if value is not None and value != []:
                # If our template give us a '+' value, we should continue to loop
                still_loop = False
                if isinstance(value, list) and value[0] == '+':
                    # Templates should keep their + inherited from their parents
                    if not self.is_tpl():
                        value = list(value)
                        value = value[1:]
                    still_loop = True

                # Maybe in the previous loop, we set a value, use it too
                if hasattr(self, prop):
                    # If the current value is strong, it will simplify the problem
                    if not isinstance(value, list) and value[0] == '+':
                        # In this case we can remove the + from our current
                        # tpl because our value will be final
                        new_val = list(getattr(self, prop))
                        new_val.extend(value[1:])
                        value = new_val
                    else:  # If not, se should keep the + sign of need
                        new_val = list(getattr(self, prop))
                        new_val.extend(value)
                        value = new_val


                # Ok, we can set it
                setattr(self, prop, value)

                # If we only got some '+' values, we must still loop
                # for an end value without it
                if not still_loop:
                    # And set my own value in the end if need
                    if self.has_plus(prop):
                        value = list(value)
                        value = list(getattr(self, prop))
                        value.extend(self.get_plus_and_delete(prop))
                        # Template should keep their '+'
                        if self.is_tpl() and not value[0] == '+':
                            value.insert(0, '+')
                        setattr(self, prop, value)
                    return value

        # Maybe templates only give us + values, so we didn't quit, but we already got a
        # self.prop value after all
        template_with_only_plus = hasattr(self, prop)

        # I do not have endingprop, my templates too... Maybe a plus?
        # warning: if all my templates gave me '+' values, do not forgot to
        # add the already set self.prop value
        if self.has_plus(prop):
            if template_with_only_plus:
                value = list(getattr(self, prop))
                value.extend(self.get_plus_and_delete(prop))
            else:
                value = self.get_plus_and_delete(prop)
            # Template should keep their '+' chain
            # We must say it's a '+' value, so our son will now that it must
            # still loop
            if self.is_tpl() and value != [] and not value[0] == '+':
                value.insert(0, '+')

            setattr(self, prop, value)
            return value

        # Ok so in the end, we give the value we got if we have one, or None
        # Not even a plus... so None :)
        return getattr(self, prop, None)

    def get_customs_properties_by_inheritance(self):
        """
        Get custom properties from the templates defined in this object

        :return: list of custom properties
        :rtype: list
        """
        for i in self.templates:
            tpl_cv = i.get_customs_properties_by_inheritance()
            if tpl_cv is not {}:
                for prop in tpl_cv:
                    if prop not in self.customs:
                        value = tpl_cv[prop]
                    else:
                        value = self.customs[prop]
                    if self.has_plus(prop):
                        value.insert(0, self.get_plus_and_delete(prop))
                        # value = self.get_plus_and_delete(prop) + ',' + value
                    self.customs[prop] = value
        for prop in self.customs:
            value = self.customs[prop]
            if self.has_plus(prop):
                value.insert(0, self.get_plus_and_delete(prop))
                self.customs[prop] = value
        # We can get custom properties in plus, we need to get all
        # entires and put
        # them into customs
        cust_in_plus = self.get_all_plus_and_delete()
        for prop in cust_in_plus:
            self.customs[prop] = cust_in_plus[prop]
        return self.customs


    def has_plus(self, prop):
        """
        Check if self.plus list have this property

        :param prop: property to check
        :type prop: str
        :return: True is self.plus have this property, else False
        :rtype: bool
        """
        try:
            self.plus[prop]
        except KeyError:
            return False
        return True


    def get_all_plus_and_delete(self):
        """
        Get all self.plus items of list. We copy it, delete the original and return the copy list

        :return: list of self.plus
        :rtype: list
        """
        res = {}
        props = self.plus.keys()  # we delete entries, so no for ... in ...
        for prop in props:
            res[prop] = self.get_plus_and_delete(prop)
        return res


    def get_plus_and_delete(self, prop):
        """
        get a copy of the property (parameter) in self.plus, delete the original and return the
        value of copy

        :param prop: a property
        :type prop: str
        :return: return the value of the property
        :rtype: str
        """
        val = self.plus[prop]
        del self.plus[prop]
        return val


    def is_correct(self):
        """
        Check if this object is correct

        :return: True if it's correct, else False
        :rtype: bool
        """
        state = True
        properties = self.__class__.properties

        # Raised all previously saw errors like unknown contacts and co
        if self.configuration_errors != []:
            state = False
            for err in self.configuration_errors:
                logger.error("[item::%s] %s", self.get_name(), err)

        for prop, entry in properties.items():
            if not hasattr(self, prop) and entry.required:
                logger.warning("[item::%s] %s property is missing", self.get_name(), prop)
                state = False

        return state


    def old_properties_names_to_new(self):
        """
        This function is used by service and hosts to transform Nagios2 parameters to Nagios3
        ones, like normal_check_interval to check_interval. There is a old_parameters tab
        in Classes that give such modifications to do.
        """
        old_properties = getattr(self.__class__, "old_properties", {})
        for old_name, new_name in old_properties.items():
            # Ok, if we got old_name and NO new name,
            # we switch the name
            if hasattr(self, old_name) and not hasattr(self, new_name):
                value = getattr(self, old_name)
                setattr(self, new_name, value)
                delattr(self, old_name)

    def get_raw_import_values(self):
        """
        Get properties => values of this object

        :return: dictionnary of properties => values
        :rtype: dict
        """
        r = {}
        properties = self.__class__.properties.keys()
        # Register is not by default in the properties
        if 'register' not in properties:
            properties.append('register')

        for prop in properties:
            if hasattr(self, prop):
                v = getattr(self, prop)
                # print prop, ":", v
                r[prop] = v
        return r


    def add_downtime(self, downtime):
        """
        Add a downtime in this object

        :param downtime: a Downtime object
        :type downtime: object
        """
        self.downtimes.append(downtime)

    def del_downtime(self, downtime_id):
        """
        Delete a downtime in this object

        :param downtime_id: id of the downtime to delete
        :type downtime_id: int
        """
        d_to_del = None
        for dt in self.downtimes:
            if dt.id == downtime_id:
                d_to_del = dt
                dt.can_be_deleted = True
        if d_to_del is not None:
            self.downtimes.remove(d_to_del)

    def add_comment(self, comment):
        """
        Add a comment to this object

        :param comment: a Comment object
        :type comment: object
        """
        self.comments.append(comment)

    def del_comment(self, comment_id):
        """
        Delete a comment in this object

        :param comment_id: id of the comment to delete
        :type comment_id: int
        """
        c_to_del = None
        for c in self.comments:
            if c.id == comment_id:
                c_to_del = c
                c.can_be_deleted = True
        if c_to_del is not None:
            self.comments.remove(c_to_del)

    def acknowledge_problem(self, sticky, notify, persistent, author, comment, end_time=0):
        """
        Add an acknowledge

        :param sticky: acknowledge will be always present is host return in UP state
        :type sticky: integer
        :param notify: if to 1, send a notification
        :type notify: integer
        :param persistent: if 1, keep this acknowledge when Alignak restart
        :type persistent: integer
        :param author: name of the author or the acknowledge
        :type author: str
        :param comment: comment (description) of the acknowledge
        :type comment: str
        :param end_time: end (timeout) of this acknowledge in seconds(timestamp) (0 to never end)
        :type end_time: int
        """
        if self.state != self.ok_up:
            if notify:
                self.create_notifications('ACKNOWLEDGEMENT')
            self.problem_has_been_acknowledged = True
            if sticky == 2:
                sticky = True
            else:
                sticky = False
            a = Acknowledge(self, sticky, notify, persistent, author, comment, end_time=end_time)
            self.acknowledgement = a
            if self.my_type == 'host':
                comment_type = 1
            else:
                comment_type = 2
            c = Comment(self, persistent, author, comment,
                        comment_type, 4, 0, False, 0)
            self.add_comment(c)
            self.broks.append(self.get_update_status_brok())

    def check_for_expire_acknowledge(self):
        """
        If have acknowledge and is expired, delete it
        """
        if (self.acknowledgement and
                self.acknowledgement.end_time != 0 and
                self.acknowledgement.end_time < time.time()):
            self.unacknowledge_problem()

    def unacknowledge_problem(self):
        """
        Remove the acknowledge, reset the flag. The comment is deleted except if the acknowledge
        is defined to be persistent
        """
        if self.problem_has_been_acknowledged:
            logger.debug("[item::%s] deleting acknowledge of %s",
                         self.get_name(),
                         self.get_dbg_name())
            self.problem_has_been_acknowledged = False
            # Should not be deleted, a None is Good
            self.acknowledgement = None
            # del self.acknowledgement
            # find comments of non-persistent ack-comments and delete them too
            for c in self.comments:
                if c.entry_type == 4 and not c.persistent:
                    self.del_comment(c.id)
            self.broks.append(self.get_update_status_brok())

    def unacknowledge_problem_if_not_sticky(self):
        """
        Remove the acknowledge if it is not sticky
        """
        if hasattr(self, 'acknowledgement') and self.acknowledgement is not None:
            if not self.acknowledgement.sticky:
                self.unacknowledge_problem()

    def prepare_for_conf_sending(self):
        """
        Flatten some properties tagged by the 'conf_send_preparation' because
        they are too 'linked' to be send like that (like realms)
        """
        cls = self.__class__

        for prop, entry in cls.properties.items():
            # Is this property need preparation for sending?
            if entry.conf_send_preparation is not None:
                f = entry.conf_send_preparation
                if f is not None:
                    val = f(getattr(self, prop))
                    setattr(self, prop, val)

        if hasattr(cls, 'running_properties'):
            for prop, entry in cls.running_properties.items():
                # Is this property need preparation for sending?
                if entry.conf_send_preparation is not None:
                    f = entry.conf_send_preparation
                    if f is not None:
                        val = f(getattr(self, prop))
                        setattr(self, prop, val)

    def get_property_value_for_brok(self, prop, tab):
        """
        Get the property of an object and brok_transformation if needed and return the value

        :param prop: property name
        :type prop: str
        :param tab: object with all properties of an object
        :type tab: object
        :return: value of the property original or brok converted
        :rtype: str
        """
        entry = tab[prop]
        # Get the current value, or the default if need
        value = getattr(self, prop, entry.default)

        # Apply brok_transformation if need
        # Look if we must preprocess the value first
        pre_op = entry.brok_transformation
        if pre_op is not None:
            value = pre_op(self, value)

        return value

    def fill_data_brok_from(self, data, brok_type):
        """
        Add properties to 'data' parameter with properties of this object when 'brok_type'
        parameter is defined in fill_brok of these properties

        :param data: object to fill
        :type data: object
        :param brok_type: name of brok_type
        :type brok_type: var
        """
        cls = self.__class__
        # Now config properties
        for prop, entry in cls.properties.items():
            # Is this property intended for broking?
            if brok_type in entry.fill_brok:
                data[prop] = self.get_property_value_for_brok(prop, cls.properties)

        # Maybe the class do not have running_properties
        if hasattr(cls, 'running_properties'):
            # We've got prop in running_properties too
            for prop, entry in cls.running_properties.items():
                # if 'fill_brok' in cls.running_properties[prop]:
                if brok_type in entry.fill_brok:
                    data[prop] = self.get_property_value_for_brok(prop, cls.running_properties)

    def get_initial_status_brok(self):
        """
        Create initial brok

        :return: Brok object
        :rtype: object
        """
        data = {'id': self.id}
        self.fill_data_brok_from(data, 'full_status')
        return Brok('initial_' + self.my_type + '_status', data)

    def get_update_status_brok(self):
        """
        Create update brok

        :return: Brok object
        :rtype: object
        """
        data = {'id': self.id}
        self.fill_data_brok_from(data, 'full_status')
        return Brok('update_' + self.my_type + '_status', data)

    def get_check_result_brok(self):
        """
        Create check_result brok

        :return: Brok object
        :rtype: object
        """
        data = {}
        self.fill_data_brok_from(data, 'check_result')
        return Brok(self.my_type + '_check_result', data)

    def get_next_schedule_brok(self):
        """
        Create next_schedule (next check) brok

        :return: Brok object
        :rtype: object
        """
        data = {}
        self.fill_data_brok_from(data, 'next_schedule')
        return Brok(self.my_type + '_next_schedule', data)

    def get_snapshot_brok(self, snap_output, exit_status):
        """
        Create snapshot (check_result type) brok

        :param snap_output: value of output
        :type snap_output: str
        :param exit_status: status of exit
        :type exit_status: integer
        :return: Brok object
        :rtype: object
        """
        data = {
            'snapshot_output':      snap_output,
            'snapshot_time':        int(time.time()),
            'snapshot_exit_status': exit_status,
        }
        self.fill_data_brok_from(data, 'check_result')
        return Brok(self.my_type + '_snapshot', data)

    def linkify_one_command_with_commands(self, commands, prop):
        """
        Link a command

        :param commands: object commands
        :type commands: object
        :param prop: property name
        :type prop: str
        """
        if hasattr(self, prop):
            command = getattr(self, prop).strip()
            if command != '':
                if hasattr(self, 'poller_tag'):
                    cmdCall = CommandCall(commands, command,
                                          poller_tag=self.poller_tag)
                elif hasattr(self, 'reactionner_tag'):
                    cmdCall = CommandCall(commands, command,
                                          reactionner_tag=self.reactionner_tag)
                else:
                    cmdCall = CommandCall(commands, command)
                setattr(self, prop, cmdCall)
            else:
                setattr(self, prop, None)

    def explode_trigger_string_into_triggers(self, triggers):
        """
        Add trigger to triggers if exist

        :param triggers: trigger object
        :type triggers: object
        """
        src = getattr(self, 'trigger', '')
        if src:
            # Change on the fly the characters
            src = src.replace(r'\n', '\n').replace(r'\t', '\t')
            t = triggers.create_trigger(src,
                                        'inner-trigger-' + self.__class__.my_type + str(self.id))
            if t:
                # Maybe the trigger factory give me a already existing trigger,
                # so my name can be dropped
                self.triggers.append(t.get_name())

    def linkify_with_triggers(self, triggers):
        """
        Link with triggers

        :param triggers: Triggers object
        :type triggers: object
        """
        # Get our trigger string and trigger names in the same list
        self.triggers.extend([self.trigger_name])
        # print "I am linking my triggers", self.get_full_name(), self.triggers
        new_triggers = []
        for tname in self.triggers:
            if tname == '':
                continue
            t = triggers.find_by_name(tname)
            if t:
                setattr(t, 'trigger_broker_raise_enabled', self.trigger_broker_raise_enabled)
                new_triggers.append(t)
            else:
                self.configuration_errors.append('the %s %s does have a unknown trigger_name '
                                                 '"%s"' % (self.__class__.my_type,
                                                           self.get_full_name(),
                                                           tname))
        self.triggers = new_triggers

    def dump(self):
        """
        Dump properties

        :return: dictionnary with properties
        :rtype: dict
        """
        dmp = {}
        for prop in self.properties.keys():
            if not hasattr(self, prop):
                continue
            attr = getattr(self, prop)
            if isinstance(attr, list) and attr and isinstance(attr[0], Item):
                dmp[prop] = [i.dump() for i in attr]
            elif isinstance(attr, Item):
                dmp[prop] = attr.dump()
            elif attr:
                dmp[prop] = getattr(self, prop)
        return dmp

    def _get_name(self):
        """
        Get the name of the object

        :return: the object name string
        :rtype: str
        """
        if hasattr(self, 'get_name'):
            return self.get_name()
        name = getattr(self, 'name', None)
        host_name = getattr(self, 'host_name', None)
        return '%s(host_name=%s)' % (name or 'no-name', host_name or '')



class Items(object):
    """
    Class to manage all Item
    """
    def __init__(self, items, index_items=True):
        self.items = {}
        self.name_to_item = {}
        self.templates = {}
        self.name_to_template = {}
        self.configuration_warnings = []
        self.configuration_errors = []
        self.add_items(items, index_items)

    def get_source(self, item):
        """
        Get source, so with what system we import this item

        :param item: item object
        :type item: object
        :return: name of the source
        :rtype: str
        """
        source = getattr(item, 'imported_from', None)
        if source:
            return " in %s" % source
        else:
            return ""

    def add_items(self, items, index_items):
        """
        Add items to template if is template, else add in item list

        :param items: items list to add
        :type items: object
        :param index_items: Flag indicating if the items should be indexed on the fly.
        :type index_items: bool
        """
        for i in items:
            if i.is_tpl():
                self.add_template(i)
            else:
                self.add_item(i, index_items)

    def manage_conflict(self, item, name, partial=False):
        """
        Cheks if an object holding the same name already exists in the index.

        If so, it compares their definition order: the lowest definition order
        is kept. If definiton order equal, an error is risen.Item

        The method returns the item that should be added after it has decided
        which one should be kept.

        If the new item has precedence over the New existing one, the
        existing is removed for the new to replace it.

        :param item: object to check for conflict
        :type item: object
        :param name: name of the object
        :type name: str
        :return: 'item' parameter modified
        :rtype: object
        """
        if item.is_tpl():
            existing = self.name_to_template[name]
        elif partial:
            existing = self.name_to_partial[name]
        else:
            existing = self.name_to_item[name]
        existing_prio = getattr(
            existing,
            "definition_order",
            existing.properties["definition_order"].default)
        item_prio = getattr(
            item,
            "definition_order",
            item.properties["definition_order"].default)
        if existing_prio < item_prio:
            # Existing item has lower priority, so it has precedence.
            return existing
        elif existing_prio > item_prio:
            # New item has lower priority, so it has precedence.
            # Existing item will be deleted below
            pass
        else:
            # Don't know which one to keep, lastly defined has precedence
            objcls = getattr(self.inner_class, "my_type", "[unknown]")
            mesg = "duplicate %s name %s%s, using lastly defined. You may " \
                   "manually set the definition_order parameter to avoid " \
                   "this message." % \
                   (objcls, name, self.get_source(item))
            item.configuration_warnings.append(mesg)
        if item.is_tpl():
            self.remove_template(existing)
        else:
            self.remove_item(existing)
        return item

    def add_template(self, tpl):
        """
        Add and index a template into the `templates` container.

        :param tpl: The template to add
        :type tpl: object
        """
        tpl = self.index_template(tpl)
        self.templates[tpl.id] = tpl

    def index_template(self, tpl):
        """
        Indexes a template by `name` into the `name_to_template` dictionnary.

        :param tpl: The template to index
        :type tpl: object
        """
        objcls = self.inner_class.my_type
        name = getattr(tpl, 'name', '')
        if not name:
            mesg = "a %s template has been defined without name%s%s" % \
                   (objcls, tpl.imported_from, self.get_source(tpl))
            tpl.configuration_errors.append(mesg)
        elif name in self.name_to_template:
            tpl = self.manage_conflict(tpl, name)
        self.name_to_template[name] = tpl
        return tpl

    def remove_template(self, tpl):
        """
        Removes and un-index a template from the `templates` container.

        :param tpl: The template to remove
        :type tpl: object
        """
        try:
            del self.templates[tpl.id]
        except KeyError:
            pass
        self.unindex_template(tpl)

    def unindex_template(self, tpl):
        """
        Unindex a template from the `templates` container.

        :param tpl: The template to un-index
        :type tpl: object
        """
        name = getattr(tpl, 'name', '')
        try:
            del self.name_to_template[name]
        except KeyError:
            pass

    def add_item(self, item, index=True):
        """
        Add an item into our containers, and index it depending on the `index` flag.

        :param item: object to add
        :type item: object
        :param index: Flag indicating if the item should be indexed
        :type index: bool
        """
        name_property = getattr(self.__class__, "name_property", None)
        if index is True and name_property:
            item = self.index_item(item)
        self.items[item.id] = item

    def remove_item(self, item):
        """
        Remove (and un-index) an object

        :param item: object to remove
        :type item: object
        """
        self.unindex_item(item)
        self.items.pop(item.id, None)

    def index_item(self, item):
        """
        Indexe an item into our `name_to_item` dictionary.
        If an object holding the same item's name/key already exists in the index
        then the conflict is managed by the `manage_conflict` method.

        :param item: item to index
        :type item: object
        :return: item modified
        :rtype: object
        """
        # TODO: simplify this function (along with its opposite: unindex_item)
        # it's too complex for what it does.
        # more over:
        # There are cases (in unindex_item) where some item is tried to be removed
        # from name_to_item while it's not present in it !
        # so either it wasn't added or it was added with another key or the item key changed
        # between the index and unindex calls..
        #  -> We should simply not have to call unindex_item() with a non-indexed item !
        name_property = getattr(self.__class__, "name_property", None)
        # if there is no 'name_property' set(it is None), then the following getattr() will
        # "hopefully" evaluates to '',
        # unless some(thing|one) have setattr(item, None, 'with_something'),
        # which would be rather odd :
        name = getattr(item, name_property, '')
        if not name:
            objcls = self.inner_class.my_type
            mesg = "a %s item has been defined without %s%s" % \
                   (objcls, name_property, self.get_source(item))
            item.configuration_errors.append(mesg)
        elif name in self.name_to_item:
            item = self.manage_conflict(item, name)
        self.name_to_item[name] = item
        return item

    def unindex_item(self, item):
        """
        Un-index an item from our name_to_item dict.
        :param item: the item to un-index
        :type item: object
        """
        name_property = getattr(self.__class__, "name_property", None)
        if name_property is None:
            return
        self.name_to_item.pop(getattr(item, name_property, ''), None)

    def __iter__(self):
        return self.items.itervalues()

    def __len__(self):
        return len(self.items)

    def __delitem__(self, key):
        try:
            self.unindex_item(self.items[key])
            del self.items[key]
        except KeyError:  # we don't want it, we do not have it. All is perfect
            pass

    def __setitem__(self, key, value):
        self.items[key] = value
        name_property = getattr(self.__class__, "name_property", None)
        if name_property:
            self.index_item(value)

    def __getitem__(self, key):
        return self.items[key]

    def __contains__(self, key):
        return key in self.items

    def find_by_name(self, name):
        """
        Find an item by name

        :param name: name of item
        :type name: str
        :return: name of the item
        :rtype: str or None
        """
        return self.name_to_item.get(name, None)


    def find_by_filter(self, filters):
        """
        Find items by filters

        :param filters: list of filters
        :type filters: list
        :return: list of items
        :rtype: list
        """
        items = []
        for i in self:
            failed = False
            for f in filters:
                if not f(i):
                    failed = True
                    break
            if failed is False:
                items.append(i)
        return items

    def prepare_for_sending(self):
        """
        flatten some properties
        """
        for i in self:
            i.prepare_for_conf_sending()

    def old_properties_names_to_new(self):
        """
        Convert old Nagios2 names to Nagios3 new names
        """
        for i in itertools.chain(self.items.itervalues(),
                                 self.templates.itervalues()):
            i.old_properties_names_to_new()

    def pythonize(self):
        """
        Pythonize items
        """
        for id in self.items:
            self.items[id].pythonize()

    def find_tpl_by_name(self, name):
        """
        Find template by name

        :param name: name of template
        :type name: str
        :return: name of template found
        :rtype: str or None
        """
        return self.name_to_template.get(name, None)

    def get_all_tags(self, item):
        """
        Get all tags of an item

        :param item: an item
        :type item: object
        :return: list of tags
        :rtype: list
        """
        all_tags = item.get_templates()

        for t in item.templates:
            all_tags.append(t.name)
            all_tags.extend(self.get_all_tags(t))
        return list(set(all_tags))


    def linkify_item_templates(self, item):
        """
        Link templates

        :param item: an item
        :type item: object
        """
        tpls = []
        tpl_names = item.get_templates()

        for name in tpl_names:
            t = self.find_tpl_by_name(name)
            if t is None:
                # TODO: Check if this should not be better to report as an error ?
                self.configuration_warnings.append("%s %r use/inherit from an unknown template "
                                                   "(%r) ! Imported from: "
                                                   "%s" % (type(item).__name__,
                                                           item._get_name(),
                                                           name,
                                                           item.imported_from))
            else:
                if t is item:
                    self.configuration_errors.append(
                        '%s %r use/inherits from itself ! Imported from: '
                        '%s' % (type(item).__name__,
                                item._get_name(),
                                item.imported_from))
                else:
                    tpls.append(t)
        item.templates = tpls

    def linkify_templates(self):
        """
        Link all templates, and create the template graph too
        """
        # First we create a list of all templates
        for i in itertools.chain(self.items.itervalues(),
                                 self.templates.itervalues()):
            self.linkify_item_templates(i)
        for i in self:
            i.tags = self.get_all_tags(i)

    def is_correct(self):
        """
        Check if all items are correct (no error)

        :return: True if correct, else False
        :rtype: bool
        """
        # we are ok at the beginning. Hope we still ok at the end...
        r = True
        # Some class do not have twins, because they do not have names
        # like servicedependencies
        twins = getattr(self, 'twins', None)
        if twins is not None:
            # Ok, look at no twins (it's bad!)
            for id in twins:
                i = self.items[id]
                logger.warning("[items] %s.%s is duplicated from %s",
                               i.__class__.my_type,
                               i.get_name(),
                               getattr(i, 'imported_from', "unknown source"))

        # Then look if we have some errors in the conf
        # Juts print warnings, but raise errors
        for err in self.configuration_warnings:
            logger.warning("[items] %s", err)

        for err in self.configuration_errors:
            logger.error("[items] %s", err)
            r = False

        # Then look for individual ok
        for i in self:
            # Alias and display_name hook hook
            prop_name = getattr(self.__class__, 'name_property', None)
            if prop_name and not hasattr(i, 'alias') and hasattr(i, prop_name):
                setattr(i, 'alias', getattr(i, prop_name))
            if prop_name and getattr(i, 'display_name', '') == '' and hasattr(i, prop_name):
                setattr(i, 'display_name', getattr(i, prop_name))

            # Now other checks
            if not i.is_correct():
                n = getattr(i, 'imported_from', "unknown source")
                logger.error("[items] In %s is incorrect ; from %s", i.get_name(), n)
                r = False

        return r

    def remove_templates(self):
        """
        Remove templates
        """
        del self.templates

    def clean(self):
        """
        Request to remove the unnecessary attributes/others from our items
        """
        for i in self:
            i.clean()
        Item.clean(self)

    def fill_default(self):
        """
        Define properties for each items with default value when not defined
        """
        for i in self:
            i.fill_default()

    def __str__(self):
        return '<%s nbr_elements=%s nbr_templates=%s />' % (
            self.__class__.__name__, len(self), len(self.name_to_template))

    __repr__ = __str__

    def apply_partial_inheritance(self, prop):
        """
        Define property with inherance value of the property

        :param prop: property
        :type prop: str
        """

        for i in itertools.chain(self.items.itervalues(),
                                 self.templates.itervalues()):
            i.get_property_by_inheritance(prop)
            # If a "null" attribute was inherited, delete it
            try:
                if getattr(i, prop) == 'null':
                    delattr(i, prop)
            except AttributeError:
                pass

    def apply_inheritance(self):
        """
        For all items and templates inherite properties and custom variables.
        """
        # We check for all Class properties if the host has it
        # if not, it check all host templates for a value
        cls = self.inner_class
        for prop in cls.properties:
            self.apply_partial_inheritance(prop)
        for i in itertools.chain(self.items.itervalues(),
                                 self.templates.itervalues()):
            i.get_customs_properties_by_inheritance()

    def linkify_with_contacts(self, contacts):
        """
        Link items with contacts items

        :param contacts: all contacts object
        :type contacts: object
        """
        for i in self:
            if hasattr(i, 'contacts'):
                contacts_tab = strip_and_uniq(i.contacts)
                new_contacts = []
                for c_name in contacts_tab:
                    if c_name != '':
                        c = contacts.find_by_name(c_name)
                        if c is not None:
                            new_contacts.append(c)
                        # Else: Add in the errors tab.
                        # will be raised at is_correct
                        else:
                            err = "the contact '%s' defined for '%s' is unknown" % (c_name,
                                                                                    i.get_name())
                            i.configuration_errors.append(err)
                # Get the list, but first make elements uniq
                i.contacts = list(set(new_contacts))

    def linkify_with_escalations(self, escalations):
        """
        Link with escalations

        :param escalations: all escalations object
        :type escalations: object
        """
        for i in self:
            if hasattr(i, 'escalations'):
                escalations_tab = strip_and_uniq(i.escalations)
                new_escalations = []
                for es_name in [e for e in escalations_tab if e != '']:
                    es = escalations.find_by_name(es_name)
                    if es is not None:
                        new_escalations.append(es)
                    else:  # Escalation not find, not good!
                        err = "the escalation '%s' defined for '%s' is unknown" % (es_name,
                                                                                   i.get_name())
                        i.configuration_errors.append(err)
                i.escalations = new_escalations

    def linkify_with_resultmodulations(self, resultmodulations):
        """
        Link items with resultmodulations items

        :param resultmodulations: all resultmodulations object
        :type resultmodulations: object
        """
        for i in self:
            if hasattr(i, 'resultmodulations'):
                resultmodulations_tab = strip_and_uniq(i.resultmodulations)
                new_resultmodulations = []
                for rm_name in resultmodulations_tab:
                    rm = resultmodulations.find_by_name(rm_name)
                    if rm is not None:
                        new_resultmodulations.append(rm)
                    else:
                        err = ("the result modulation '%s' defined on the %s "
                               "'%s' do not exist" % (rm_name, i.__class__.my_type, i.get_name()))
                        i.configuration_warnings.append(err)
                        continue
                i.resultmodulations = new_resultmodulations

    def linkify_with_business_impact_modulations(self, business_impact_modulations):
        """
        Link items with business impact objects

        :param business_impact_modulations: all business impacts object
        :type business_impact_modulations: object
        """
        for i in self:
            if hasattr(i, 'business_impact_modulations'):
                business_impact_modulations_tab = strip_and_uniq(i.business_impact_modulations)
                new_business_impact_modulations = []
                for rm_name in business_impact_modulations_tab:
                    rm = business_impact_modulations.find_by_name(rm_name)
                    if rm is not None:
                        new_business_impact_modulations.append(rm)
                    else:
                        err = ("the business impact modulation '%s' defined on the %s "
                               "'%s' do not exist" % (rm_name, i.__class__.my_type, i.get_name()))
                        i.configuration_errors.append(err)
                        continue
                i.business_impact_modulations = new_business_impact_modulations

    def explode_contact_groups_into_contacts(self, item, contactgroups):
        """
        Get all contacts of contact_groups and put them in contacts container

        :param item: item where have contact_groups property
        :type item: object
        :param contactgroups: all contactgroups object
        :type contactgroups: object
        """
        if hasattr(item, 'contact_groups'):
            # TODO : See if we can remove this if
            if isinstance(item.contact_groups, list):
                cgnames = item.contact_groups
            else:
                cgnames = item.contact_groups.split(',')
            cgnames = strip_and_uniq(cgnames)
            for cgname in cgnames:
                cg = contactgroups.find_by_name(cgname)
                if cg is None:
                    err = "The contact group '%s' defined on the %s '%s' do " \
                          "not exist" % (cgname, item.__class__.my_type,
                                         item.get_name())
                    item.configuration_errors.append(err)
                    continue
                cnames = contactgroups.get_members_by_name(cgname)
                # We add contacts into our contacts
                if cnames != []:
                    if hasattr(item, 'contacts'):
                        item.contacts.extend(cnames)
                    else:
                        item.contacts = cnames

    def linkify_with_timeperiods(self, timeperiods, prop):
        """
        Link items with timeperiods items

        :param timeperiods: all timeperiods object
        :type timeperiods: object
        :param prop: property name
        :type prop: str
        """
        for i in self:
            if hasattr(i, prop):
                tpname = getattr(i, prop).strip()
                # some default values are '', so set None
                if tpname == '':
                    setattr(i, prop, None)
                    continue

                # Ok, get a real name, search for it
                tp = timeperiods.find_by_name(tpname)
                # If not found, it's an error
                if tp is None:
                    err = ("The %s of the %s '%s' named "
                           "'%s' is unknown!" % (prop, i.__class__.my_type, i.get_name(), tpname))
                    i.configuration_errors.append(err)
                    continue
                # Got a real one, just set it :)
                setattr(i, prop, tp)

    def create_commandcall(self, prop, commands, command):
        """
        Create commandCall object with command

        :param prop: property
        :type prop: str
        :param commands: all commands
        :type commands: object
        :param command: a command object
        :type command: object
        :return: a commandCall object
        :rtype: object
        """
        comandcall = dict(commands=commands, call=command)
        if hasattr(prop, 'enable_environment_macros'):
            comandcall['enable_environment_macros'] = prop.enable_environment_macros

        if hasattr(prop, 'poller_tag'):
            comandcall['poller_tag'] = prop.poller_tag
        elif hasattr(prop, 'reactionner_tag'):
            comandcall['reactionner_tag'] = prop.reactionner_tag

        return CommandCall(**comandcall)

    def linkify_one_command_with_commands(self, commands, prop):
        """
        Link a command to a property

        :param commands: commands object
        :type commands: object
        :param prop: property name
        :type prop: str
        """
        for i in self:
            if hasattr(i, prop):
                command = getattr(i, prop).strip()
                if command != '':
                    cmdCall = self.create_commandcall(i, commands, command)

                    # TODO: catch None?
                    setattr(i, prop, cmdCall)
                else:

                    setattr(i, prop, None)

    def linkify_command_list_with_commands(self, commands, prop):
        """
        Link a command list (commands with , between) in real CommandCalls

        :param commands: commands object
        :type commands: object
        :param prop: property name
        :type prop: str
        """
        for i in self:
            if hasattr(i, prop):
                coms = strip_and_uniq(getattr(i, prop))
                com_list = []
                for com in coms:
                    if com != '':
                        cmdCall = self.create_commandcall(i, commands, com)
                        # TODO: catch None?
                        com_list.append(cmdCall)
                    else:  # TODO: catch?
                        pass
                setattr(i, prop, com_list)

    def linkify_with_triggers(self, triggers):
        """
        Link triggers

        :param triggers: triggers object
        :type triggers: object
        """
        for i in self:
            i.linkify_with_triggers(triggers)

    def linkify_with_checkmodulations(self, checkmodulations):
        """
        Link checkmodulation object

        :param checkmodulations: checkmodulations object
        :type checkmodulations: object
        """
        for i in self:
            if not hasattr(i, 'checkmodulations'):
                continue
            new_checkmodulations = []
            for cw_name in i.checkmodulations:
                cw = checkmodulations.find_by_name(cw_name)
                if cw is not None:
                    new_checkmodulations.append(cw)
                else:
                    err = ("The checkmodulations of the %s '%s' named "
                           "'%s' is unknown!" % (i.__class__.my_type, i.get_name(), cw_name))
                    i.configuration_errors.append(err)
            # Get the list, but first make elements uniq
            i.checkmodulations = new_checkmodulations


    def linkify_with_macromodulations(self, macromodulations):
        """
        Link macromodulations

        :param macromodulations: macromodulations object
        :type macromodulations: object
        """
        for i in self:
            if not hasattr(i, 'macromodulations'):
                continue
            new_macromodulations = []
            for cw_name in i.macromodulations:
                cw = macromodulations.find_by_name(cw_name)
                if cw is not None:
                    new_macromodulations.append(cw)
                else:
                    err = ("The macromodulations of the %s '%s' named "
                           "'%s' is unknown!" % (i.__class__.my_type, i.get_name(), cw_name))
                    i.configuration_errors.append(err)
            # Get the list, but first make elements uniq
            i.macromodulations = new_macromodulations

    def linkify_s_by_plug(self, modules):
        """
        Link modules

        :param modules: modules object (all modules)
        :type modules: object
        """
        for s in self:
            new_modules = []
            for plug_name in s.modules:
                plug_name = plug_name.strip()
                # don't tread void names
                if plug_name == '':
                    continue

                plug = modules.find_by_name(plug_name)
                if plug is not None:
                    new_modules.append(plug)
                else:
                    err = "Error: the module %s is unknown for %s" % (plug_name, s.get_name())
                    s.configuration_errors.append(err)
            s.modules = new_modules

    def evaluate_hostgroup_expression(self, expr, hosts, hostgroups, look_in='hostgroups'):
        """
        Evaluate hostgroup expression

        :param expr: an expression
        :type expr: str
        :param hosts: hosts object (all hosts)
        :type hosts: object
        :param hostgroups: hostgroups object (all hostgroups)
        :type hostgroups: object
        :param look_in: item name where search
        :type look_in: str
        :return: return list of hostgroups
        :rtype: list
        """
        # Maybe exp is a list, like numerous hostgroups entries in a service, link them
        if isinstance(expr, list):
            expr = '|'.join(expr)
        # print "\n"*10, "looking for expression", expr
        if look_in == 'hostgroups':
            f = ComplexExpressionFactory(look_in, hostgroups, hosts)
        else:  # templates
            f = ComplexExpressionFactory(look_in, hosts, hosts)
        expr_tree = f.eval_cor_pattern(expr)

        # print "RES of ComplexExpressionFactory"
        # print expr_tree

        # print "Try to resolve the Tree"
        set_res = expr_tree.resolve_elements()
        # print "R2d2 final is", set_res

        # HOOK DBG
        return list(set_res)

    def get_hosts_from_hostgroups(self, hgname, hostgroups):
        """
        Get hosts of hostgroups

        :param hgname: hostgroup name
        :type hgname: str
        :param hostgroups: hostgroups object (all hostgroups)
        :type hostgroups: object
        :return: list of hosts
        :rtype: list
        """
        if not isinstance(hgname, list):
            hgname = [e.strip() for e in hgname.split(',') if e.strip()]

        host_names = []

        for name in hgname:
            hg = hostgroups.find_by_name(name)
            if hg is None:
                raise ValueError("the hostgroup '%s' is unknown" % hgname)
            mbrs = [h.strip() for h in hg.get_hosts() if h.strip()]
            host_names.extend(mbrs)
        return host_names

    def explode_host_groups_into_hosts(self, item, hosts, hostgroups):
        """
        Get all hosts of hostgroups and add all in host_name container

        :param item: the item object
        :type item: object
        :param hosts: hosts object
        :type hosts: object
        :param hostgroups: hostgroups object
        :type hostgroups: object
        """
        hnames_list = []
        # Gets item's hostgroup_name
        hgnames = getattr(item, "hostgroup_name", '')

        # Defines if hostgroup is a complex expression
        # Expands hostgroups
        if is_complex_expr(hgnames):
            hnames_list.extend(self.evaluate_hostgroup_expression(
                item.hostgroup_name, hosts, hostgroups))
        elif hgnames:
            try:
                hnames_list.extend(
                    self.get_hosts_from_hostgroups(hgnames, hostgroups))
            except ValueError, e:
                item.configuration_errors.append(str(e))

        # Expands host names
        hname = getattr(item, "host_name", '')
        hnames_list.extend([n.strip() for n in hname.split(',') if n.strip()])
        hnames = set()

        for h in hnames_list:
            # If the host start with a !, it's to be removed from
            # the hostgroup get list
            if h.startswith('!'):
                hst_to_remove = h[1:].strip()
                try:
                    hnames.remove(hst_to_remove)
                except KeyError:
                    pass
            elif h == '*':
                [hnames.add(h.host_name) for h in hosts.items.itervalues()
                 if getattr(h, 'host_name', '')]
            # Else it's a host to add, but maybe it's ALL
            else:
                hnames.add(h)

        item.host_name = ','.join(hnames)

    def explode_trigger_string_into_triggers(self, triggers):
        """
        Get al trigger in triggers and manage them

        :param triggers: triggers object
        :type triggers: object
        """
        for i in self:
            i.explode_trigger_string_into_triggers(triggers)

    def no_loop_in_parents(self, attr1, attr2):
        """
        Find loop in dependencies.
        For now, used with the following attributes :
        :(self, parents):
            host dependencies from host object
        :(host_name, dependent_host_name):\
            host dependencies from hostdependencies object
        :(service_description, dependent_service_description):
            service dependencies from servicedependencies object

        :param attr1: attribute name
        :type attr1: str
        :param attr2: attribute name
        :type attr2: str
        :return: True if no loop, else false
        :rtype: bool
        """
        # Ok, we say "from now, no loop :) "
        r = True

        # Create parent graph
        parents = Graph()

        # Start with all items as nodes
        for item in self:
            # Hack to get self here. Used when looping on host and host parent's
            if attr1 == "self":
                obj = item          # obj is a host/service [list]
            else:
                obj = getattr(item, attr1, None)
            if obj is not None:
                if isinstance(obj, list):
                    for sobj in obj:
                        parents.add_node(sobj)
                else:
                    parents.add_node(obj)

        # And now fill edges
        for item in self:
            if attr1 == "self":
                obj1 = item
            else:
                obj1 = getattr(item, attr1, None)
            obj2 = getattr(item, attr2, None)
            if obj2 is not None:
                if isinstance(obj2, list):
                    for sobj2 in obj2:
                        if isinstance(obj1, list):
                            for sobj1 in obj1:
                                parents.add_edge(sobj1, sobj2)
                        else:
                            parents.add_edge(obj1, sobj2)
                else:
                    if isinstance(obj1, list):
                        for sobj1 in obj1:
                            parents.add_edge(sobj1, obj2)
                    else:
                        parents.add_edge(obj1, obj2)

        # Now get the list of all item in a loop
        items_in_loops = parents.loop_check()

        # and raise errors about it
        for item in items_in_loops:
            logger.error("The %s object '%s'  is part of a circular parent/child chain!",
                         item.my_type,
                         item.get_name())
            r = False

        return r
