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
# pylint: disable=too-many-lines
# pylint: disable=too-many-public-methods
from __future__ import print_function
import time
import itertools
import warnings
import logging

from copy import copy

from alignak.property import StringProp, ListProp, BoolProp, SetProp, DictProp
from alignak.property import IntegerProp, ToGuessProp, PythonizeError
from alignak.alignakobject import AlignakObject
from alignak.brok import Brok
from alignak.util import strip_and_uniq, is_complex_expr
from alignak.complexexpression import ComplexExpressionFactory
from alignak.graph import Graph

logger = logging.getLogger(__name__)  # pylint: disable=C0103


class Item(AlignakObject):
    """
    Class to manage an item
    An Item is the base of many objects of Alignak. So it define common properties,
    common functions.
    """

    name_property = 'name'

    properties = AlignakObject.properties.copy()
    properties.update({
        # From which file the item is imported
        'imported_from':
            StringProp(default='unknown'),
        # Item templates list
        'use':
            ListProp(default=[]),
        # Template name
        'name':
            StringProp(default='unnamed'),
        'alias':
            StringProp(default='', fill_brok=['full_status']),
        'display_name':
            StringProp(default='', fill_brok=['full_status']),
        # True for an object, False for a template
        'register':
            BoolProp(default=True),
        # Item priority if defined several times (the lowest first)
        'definition_order':
            IntegerProp(default=100),
    })

    running_properties = {
        # True if the object configuration is correct, False if errors are detected
        'conf_is_correct':
            BoolProp(default=True),
        # All errors and warning raised during the configuration parsing
        'configuration_warnings':
            ListProp(default=[]),
        'configuration_errors':
            ListProp(default=[]),
        # We save all template we asked us to load from
        'tags':
            SetProp(default=[], fill_brok=['full_status']),
        # We save our customs variables
        'customs':
            DictProp(default={}, fill_brok=['full_status']),
        # # We save our plus (+) properties
        'plus':
            DictProp(default={}, fill_brok=['full_status']),
    }

    old_properties = {}

    macros = {}

    my_type = 'item'
    ok_up = ''

    def __init__(self, params=None, parsing=True, debug=False):  # pylint: disable=too-many-branches
        """Initialize an Alignak Item

        If parsing is True, then the item is initially created from the Alignak monitoring
        configuration files, else, the object is created from an existing object

        :param debug: print debug information about the object properties
        :param params: parameters used to create the object
        :param parsing: if True, initial creation, else, object unserialization
        """
        # Always call initialization of the base AlignakObject
        super(Item, self).__init__(params, parsing=parsing, debug=debug)
        if not parsing:
            return

        cls = self.__class__

        # Parse provided parameters
        if params is None:
            params = {}
        for key in params:
            # We want to create instance of object with the good type.
            # Here we've just parsed config files so everything is a list.
            # We use the pythonize method to get the good type.
            try:
                if key in self.properties:
                    val = self.properties[key].pythonize(params[key])
                elif key in self.running_properties and parsing:
                    # Alert about using running properties on object unserialization
                    self.add_error("[%s:%s] using the running property '%s' in a config file" %
                                   (self.my_type, self.get_name(), key), is_warning=True)
                    val = self.running_properties[key].pythonize(params[key])
                elif hasattr(self, 'old_properties') and key in self.old_properties:
                    val = self.properties[self.old_properties[key]].pythonize(params[key])
                elif key.startswith('_'):  # custom macro, not need to detect something here
                    macro = params[key]
                    # If it's a string, directly use this
                    if isinstance(macro, basestring):
                        val = macro
                    # a list for a custom macro is not managed (conceptually invalid)
                    # so take the first defined
                    elif isinstance(macro, list) and len(macro) > 0:
                        val = macro[0]
                    # not a list of void? just put void string so
                    else:
                        val = ''
                else:
                    self.add_error("Guessing the property %s type because "
                                   "it is not in %s object properties" %
                                   (key, cls.__name__), is_warning=True)
                    self.properties[key] = ToGuessProp(default='')
                    val = ToGuessProp.pythonize(params[key])
            except (PythonizeError, ValueError) as expt:
                self.add_error("Error while pythonizing parameter '%s': %s" % (key, expt))
                continue

            # checks for attribute value special syntax (+ or _)
            # we can have '+param' or ['+template1' , 'template2']
            if isinstance(val, str) and len(val) >= 1 and val[0] == '+':
                self.add_error("A + value for a single string is not handled")
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
                    self.add_error("no support for _ syntax in multiple valued attributes")
                    continue
                custom_name = key.upper()
                self.customs[custom_name] = val
            else:
                setattr(self, key, val)
        if debug:
            print('Item __init__: %s, %d attributes' %
                  (self.__class__, len(self.__dict__)))
            print('Item __init__: %s, attributes list: %s' %
                  (self.__class__, [key for key in self.__dict__]))

        # Initialize unset properties with their default value
        self.fill_default()

    def __str__(self):
        return '<%s "name"=%r />' % (self.__class__.__name__, self.get_name())

    __repr__ = __str__

    def copy(self):
        """
        Get a copy of this item but with a new id

        :return: copy of this object with a new id
        :rtype: object
        """
        cls = self.__class__
        i = cls({})  # Dummy item but with it's own running properties
        for prop in cls.properties:
            if hasattr(self, prop) and prop != 'uuid':  # TODO: Fix it
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
        Clean properties only need when initialize & configure

        :return: None
        """
        for name in ('imported_from', 'use', 'plus', 'templates',):
            try:
                delattr(self, name)
            except AttributeError:
                pass

    def get_name(self):
        """
        Get the name of the item.

        Use the class variable name_property to get the object name. Returns `Unnamed type`
        if the name is not defined.

        :return: the object name string
        :rtype: str
        """
        if self.is_tpl():
            return getattr(self, 'name', "unnamed")
        name_property = getattr(self.__class__, "name_property", 'not_existing')
        return getattr(self, name_property, "unnamed")

    def is_tpl(self):
        """
        Check if this object is a template

        :return: True if is a template, else False
        :rtype: bool
        """
        return not getattr(self, "register", True)

    def serialize(self, filtered_fields=None):
        """Call the base AlignakObject serialize method

        Filter the configuration_warnings and configuration_errors field

        :return: Dictionary containing key and value from properties, running_properties and macros
        :rtype: dict
        """
        logger.debug("Serializing: %s / %s", self.my_type, self.get_name())
        # if self.my_type == 'servicegroup':
        #     print("SG %s (%s), serialize: %s" % (self.get_name(), self.uuid, self.__dict__))
        return super(Item, self).serialize(filtered_fields=['configuraion_is_correct',
                                                            'configuration_warnings',
                                                            'configuration_errors'])

    def add_errors(self, messages, is_warning=False):
        """Add several error messages in the configuration errors list

        :param messages: list of strings
        :type messages: list
        :param is_warning: error message is a simple warning
        :type is_warning: bool
        :return: None
        """
        for error in messages:
            self.add_error(error, is_warning=is_warning)

    def add_error(self, message, is_warning=False):
        """Add an error message in the configuration errors list

         If is_warning is set, the error message is  added to
         the warnings list

         The configuration is set as incorrect if it is still correct
         and we store an error message

        :param message: error
        :type message: str
        :param is_warning: error message is a simple warning
        :type is_warning: bool
        :return: None
        """
        if is_warning:
            logger.debug("Got a configuration warning: %s", message)
            self.configuration_warnings.append(message)
        else:
            logger.debug("Got a configuration error: %s", message)
            self.conf_is_correct = False
            self.configuration_errors.append(message)

    @classmethod
    def load_global_conf(cls, conf):
        """
        Load configuration of parent object

        :param cls: parent object
        :type cls: object
        :param conf: current object (child)
        :type conf: object
        :return: None
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

    def get_templates(self):
        """
        Get list of templates this object use

        :return: list of templates
        :rtype: list
        """
        return [n.strip() for n in getattr(self, 'use', []) if n.strip()]

        # use = getattr(self, 'use', '')
        # if isinstance(use, list):
        #     return [n.strip() for n in use if n.strip()]
        # else:
        #     return [n.strip() for n in use.split(',') if n.strip()]

    def has_plus(self, prop):
        """
        Check if self.plus list have this property

        :param prop: property to check
        :type prop: str
        :return: True is self.plus have this property, otherwise False
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

        This function:
        - checks if the required properties are defined, ignoring special_properties if some exist
        - logs the previously found warnings and errors

        :return: True if it's correct, otherwise False
        :rtype: bool
        """
        properties = self.__class__.properties

        # Set alias and display_name if not defined
        # Todo: should be moved elsewhere, no?
        name_property = getattr(self.__class__, 'name_property', None)
        if name_property and not getattr(self, 'alias', ''):
            setattr(self, 'alias', self.get_name())
        if name_property and not getattr(self, 'display_name', ''):
            setattr(self, 'display_name', self.get_name())

        for prop, entry in properties.items():
            if hasattr(self, 'special_properties') and prop in getattr(self, 'special_properties'):
                continue
            if not hasattr(self, prop) and entry.required:
                self.add_error("[%s::%s] %s property is missing" %
                               (self.my_type, self.get_name(), prop))

        return self.conf_is_correct

    def old_properties_names_to_new(self):
        """
        This function is used by service and hosts to transform Nagios2 parameters to Nagios3
        ones, like normal_check_interval to check_interval. There is a old_parameters tab
        in Classes that give such modifications to do.

        :return: None
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

        :return: dictionary of properties => values
        :rtype: dict
        """
        warnings.warn("Access to deprecated function Item::get_raw_import_values",
                      DeprecationWarning, stacklevel=2)

        # res = {}
        # properties = self.__class__.properties.keys()
        # # Register is not by default in the properties
        # if 'register' not in properties:
        #     properties.append('register')
        #
        # for prop in properties:
        #     if hasattr(self, prop):
        #         val = getattr(self, prop)
        #         res[prop] = val
        # return res

    def add_downtime(self, downtime):
        """
        Add a downtime in this object

        :param downtime: a Downtime object
        :type downtime: object
        :return: None
        """
        self.downtimes.append(downtime)

    def del_downtime(self, downtime_id, downtimes):
        """
        Delete a downtime in this object

        :param downtime_id: id of the downtime to delete
        :type downtime_id: int
        :return: None
        """
        d_to_del = None
        for d_id in self.downtimes:
            if d_id == downtime_id:
                downtime = downtimes[d_id]
                d_to_del = d_id
                downtime.can_be_deleted = True
        if d_to_del is not None:
            self.downtimes.remove(d_to_del)

    def add_comment(self, comment):
        """
        Add a comment to this object

        :param comment: a Comment object
        :type comment: object
        :return: None
        """
        self.comments.append(comment)

    def del_comment(self, comment_id, comments):
        """
        Delete a comment in this object

        :param comment_id: id of the comment to delete
        :type comment_id: int
        :return: None
        """
        c_to_del = None
        for comm_id in self.comments:
            if comm_id == comment_id:
                comm = comments[comm_id]
                c_to_del = comm_id
                comm.can_be_deleted = True
        if c_to_del is not None:
            self.comments.remove(c_to_del)

    def prepare_for_conf_sending(self):
        """
        Flatten some properties tagged by the 'conf_send_preparation' because
        they are too 'linked' to be send like that (like realms)

        :return: None
        """
        cls = self.__class__

        for prop, entry in cls.properties.items():
            # Is this property need preparation for sending?
            if entry.conf_send_preparation is not None:
                fun = entry.conf_send_preparation
                if fun is not None:
                    val = fun(getattr(self, prop))
                    setattr(self, prop, val)

        if hasattr(cls, 'running_properties'):
            for prop, entry in cls.running_properties.items():
                # Is this property need preparation for sending?
                if entry.conf_send_preparation is not None:
                    fun = entry.conf_send_preparation
                    if fun is not None:
                        val = fun(getattr(self, prop))
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
        :return: None
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
        data = {'uuid': self.uuid}
        self.fill_data_brok_from(data, 'full_status')
        return Brok({'type': 'initial_' + self.my_type + '_status', 'data': data})

    def get_update_status_brok(self):
        """
        Create update brok

        :return: Brok object
        :rtype: object
        """
        data = {'uuid': self.uuid}
        self.fill_data_brok_from(data, 'full_status')
        return Brok({'type': 'update_' + self.my_type + '_status', 'data': data})

    def get_check_result_brok(self):
        """
        Create check_result brok

        :return: Brok object
        :rtype: object
        """
        data = {}
        self.fill_data_brok_from(data, 'check_result')
        return Brok({'type': self.my_type + '_check_result', 'data': data})

    def get_next_schedule_brok(self):
        """
        Create next_schedule (next check) brok

        :return: Brok object
        :rtype: object
        """
        data = {}
        self.fill_data_brok_from(data, 'next_schedule')
        return Brok({'type': self.my_type + '_next_schedule', 'data': data})

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
            'snapshot_output': snap_output,
            'snapshot_time': int(time.time()),
            'snapshot_exit_status': exit_status,
        }
        self.fill_data_brok_from(data, 'check_result')
        return Brok({'type': self.my_type + '_snapshot', 'data': data})

    def dump(self, dfile=None):  # pylint: disable=W0613
        """
        Dump properties

        :return: dictionary with properties
        :rtype: dict
        """
        dmp = {}
        for prop in self.properties:
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

    def get_full_name(self):
        """Accessor to name attribute

        :return: name
        :rtype: str
        """
        return self.name


class Items(object):
    """
    Class to manage all Item
    """
    inner_class = Item

    def __init__(self, items, index_items=True, parsing=True):
        """Initialize an Alignak Items list

        If parsing is True, then the list is initially created from the Alignak monitoring
        configuration files, else, the list is created from an existing list

        :param items: items to create the list with
        :param index_items: if True, index the items of the list
        :param parsing: if True, initial creation, else, object unserialization
        """
        self.items = {}
        self.name_to_item = {}
        self.templates = {}
        self.name_to_template = {}
        self.conf_is_correct = True
        self.configuration_warnings = []
        self.configuration_errors = []

        if parsing:
            logger.debug("Creating %s", self.__class__)
            self.add_items(items, index_items)
        else:
            logger.debug("Unserializing: %s", self.__class__)
            # We are un-serializing
            for item in items.values():
                new_object = self.inner_class(item, parsing=False)
                self.add_item(new_object, index=index_items)

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
        """Get a specific objects for Items dict.
        Ie : a host in the Hosts dict, a service in the Service dict etc.

        :param key: object uuid
        :type key: str
        :return: The wanted object
        :rtype: alignak.object.item.Item
        """
        return self.items[key] if key else None

    def __contains__(self, key):
        return key in self.items

    def __str__(self):
        return '<%s, %d %s, %d templates />' % \
               (self.__class__.__name__, len(self), self.inner_class.my_type,
                len(self.name_to_template))

    __repr__ = __str__

    def fill_default(self, which_properties="properties"):
        """
        Call default properties filling for each item

        :param which_properties: default is to set default value for the properties but
        it may be used for the running_properties
        :return: None
        """
        for item in self:
            item.fill_default(which_properties=which_properties)

    def add_items(self, items, index_items):
        """
        Add items to template if is template, else add in item list

        :param items: items list to add
        :type items: object
        :param index_items: Flag indicating if the items should be indexed on the fly.
        :type index_items: bool
        :return: None
        """
        for item in items:
            if item.is_tpl():
                self.add_template(item)
            else:
                self.add_item(item, index_items)

    def manage_conflict(self, item, name):
        """
        Checks if an object holding the same name already exists in the index.

        If so, it compares their definition order: the lowest definition order
        is kept. If definition order equal, an error is risen.Item

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
        else:
            existing = self.name_to_item[name]
        if existing == item:
            return item

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
            message = "duplicate %s name %s, from: %s, using lastly defined. " \
                      "You may manually set the definition_order parameter " \
                      "to avoid this message." % \
                      (objcls, name, item.imported_from)
            item.configuration_warnings.append(message)
        if item.is_tpl():
            self.remove_template(existing)
        else:
            self.remove_item(existing)
        return item

    def add_template(self, template):
        """
        Add and index a template into the `templates` container.

        :param template: The template to add
        :type template: object
        :return: None
        """
        # If the item to add is not named, set its uuid as its name
        if not template.get_name():
            name_property = getattr(self.inner_class, 'name_property', 'name')
            setattr(template, name_property, template.uuid)

        template = self.index_template(template)
        self.templates[template.uuid] = template

    def index_template(self, template):
        """
        Indexes a template by `name` into the `name_to_template` dictionary.

        :param template: The template to index
        :type template: object
        :return: None
        """
        name = getattr(template, 'name', 'unnamed')
        if name == 'unnamed':
            template.add_error("a %s template has been defined without name, from: %s" %
                               (self.inner_class.my_type, template.imported_from))
        elif name in self.name_to_template:
            template = self.manage_conflict(template, name)

        logger.debug("Index %s template: %s / %s", self.inner_class, template.uuid, name)
        self.name_to_template[name] = template
        return template

    def remove_template(self, tpl):
        """
        Removes and un-index a template from the `templates` container.

        :param tpl: The template to remove
        :type tpl: object
        :return: None
        """
        try:
            del self.templates[tpl.uuid]
        except KeyError:
            pass
        self.unindex_template(tpl)

    def unindex_template(self, tpl):
        """
        Unindex a template from the `templates` container.

        :param tpl: The template to un-index
        :type tpl: object
        :return: None
        """
        name = getattr(tpl, 'name', '')
        logger.debug("Unindex %s template: %s / %s", self.inner_class, tpl.uuid, name)
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
        :return: None
        """
        # If the item to add is not named, set its uuid as its name
        if not item.get_name():
            name_property = getattr(self.inner_class, 'name_property', 'name')
            setattr(item, name_property, item.uuid)

        if index:
            item = self.index_item(item)
        logger.debug("Add item to list: %s / %s", item.uuid, item)

        self.items[item.uuid] = item

    def remove_item(self, item):
        """
        Remove (and un-index) an object

        :param item: object to remove
        :type item: object
        :return: None
        """
        logger.debug("Remove item from list: %s / %s", item.uuid, item)

        self.unindex_item(item)
        self.items.pop(item.uuid, None)

    def index_item(self, item):
        """
        Index an item into our `name_to_item` dictionary.
        If an object holding the same item's name/key already exists in the index
        then the conflict is managed by the `manage_conflict` method.

        :param item: item to index
        :type item: object
        :return: item modified
        :rtype: object
        """
        name = item.get_name()
        name_property = getattr(self.__class__.inner_class, "name_property", None)
        if name == 'unnamed':
            item.add_error("a %s item has been defined without %s, from: %s" %
                           (self.inner_class.my_type, name_property,
                            getattr(item, 'imported_from', 'unknown')))
            name = item.uuid
        elif name in self.name_to_item:
            item = self.manage_conflict(item, name)

        logger.debug("Index %s (%s): %s / %s", self.inner_class, name_property, item.uuid, name)
        self.name_to_item[name] = item
        return item

    def unindex_item(self, item):
        """
        Un-index an item from our name_to_item dict.
        :param item: the item to un-index
        :type item: object
        :return: None
        """
        name_property = getattr(self.__class__, "name_property", None)
        if name_property is None:
            return
        name = getattr(item, name_property, '')
        logger.debug("Unindex %s: %s / %s", self.inner_class, item.uuid, name)
        self.name_to_item.pop(name, None)

    def find_by_name(self, name):
        """
        Find an item by name

        :param name: name of item
        :type name: str
        :return: item
        :rtype: alignak.objects.item.Item
        """
        return self.name_to_item.get(name, None)

    def prepare_for_sending(self):
        """
        flatten some properties

        :return: None
        """
        for i in self:
            i.prepare_for_conf_sending()

    def old_properties_names_to_new(self):
        """
        Convert old Nagios2 names to Nagios3 new names

        :return: None
        """
        for item in itertools.chain(self.items.itervalues(), self.templates.itervalues()):
            item.old_properties_names_to_new()

    def find_tpl_by_name(self, name):
        """
        Find template by name

        :param name: name of template
        :type name: str
        :return: name of template found
        :rtype: str | None
        """
        return self.name_to_template.get(name, None)

    def get_all_tags(self, item):
        """
        Get all tags of an item

        :param item: an item
        :type item: Item
        :return: list of tags
        :rtype: list
        """
        all_tags = item.get_templates()

        for template_id in item.templates:
            template = self.templates[template_id]
            all_tags.append(template.name)
            all_tags.extend(self.get_all_tags(template))
        return list(set(all_tags))

    def linkify_item_templates(self, item):
        """
        Link templates

        :param item: an item
        :type item: Item
        :return: None
        """
        templates = []
        template_names = item.get_templates()

        for template_name in template_names:
            template = self.find_tpl_by_name(template_name)
            if template is None:
                # TODO: Check if this should not be better to report as an error ?
                item.add_error("%s %s use/inherit from an unknown template: %s ! from: %s" %
                               (item.my_type, item.get_name(), template_name,
                                item.imported_from), is_warning=True)
            else:
                if template is item:
                    item.add_error("%s %s use/inherits from itself ! from: %s" %
                                   (item.my_type, item._get_name(), item.imported_from))
                else:
                    templates.append(template.uuid)
        item.templates = templates

    def linkify_templates(self):
        """
        Link all templates, and create the template graph too

        :return: None
        """
        # First we create a list of all templates
        for item in itertools.chain(self.items.itervalues(), self.templates.itervalues()):
            self.linkify_item_templates(item)
        for item in self:
            item.tags = self.get_all_tags(item)

    def is_correct(self):
        """
        Check if the items list configuration is correct ::

        * check if duplicate items exist in the list and warn about this
        * set alias and display_name property for each item in the list if they do not exist
        * check each item in the list
        * log all previous warnings
        * log all previous errors

        :return: True if the configuration is correct, otherwise False
        :rtype: bool
        """
        self.conf_is_correct = True

        # Some class do not have twins, because they do not have names like servicedependencies
        twins = getattr(self, 'twins', None)
        if twins is not None:
            # Ok, look at no twins (it's bad!)
            for t_id in twins:
                item = self.items[t_id]
                valid = False
                item.add_error("[items] %s.%s is duplicated from %s" %
                               (item.__class__.my_type, item.get_name(), item.imported_from),
                               is_warning=True)

        # Check individual items before setting the global items list errors and warnings
        for item in self:
            # Now other checks
            if not item.is_correct():
                self.conf_is_correct = False
                item.add_error("Configuration in %s::%s is incorrect; from: %s" %
                               (item.my_type, item.get_name(), item.imported_from))

            # Cumulate my items configuration messages
            if item.configuration_errors:
                self.configuration_errors += item.configuration_errors
            if item.configuration_warnings:
                self.configuration_warnings += item.configuration_warnings

        # # Log all previously sawn warnings
        # if self.configuration_warnings:
        #     for message in self.configuration_warnings:
        #         logger.warning("[items] %s", message)
        #
        # # Raise all previously sawn errors
        # if self.configuration_errors:
        #     valid = False
        #     for message in self.configuration_errors:
        #         logger.error("[items] %s", message)

        return self.conf_is_correct

    def remove_templates(self):
        """
        Remove templates

        :return: None
        """
        del self.templates

    def clean(self):
        """
        Request to remove the unnecessary attributes/others from our items

        :return: None
        """
        for item in self:
            item.clean()
        Item.clean(self)

    def serialize(self):
        """This function serialize items into a simple dict object.
        It is used when transferring data to other daemons over the network (http)

        Here is the generic function that simply serialize each item of the items object

        :return: Dictionary containing item's uuid as key and item as value
        :rtype: dict
        """
        logger.debug("Serializing items: %s", self.inner_class.my_type)
        res = {}
        for key, item in self.items.iteritems():
            res[key] = item.serialize()
        return res

    def apply_partial_inheritance(self, prop):
        """
        Define property with inheritance value of the property

        :param prop: property
        :type prop: str
        :return: None
        """
        # Update items properties with templates inherited values
        for item in self.items.values():
            debug = False
            # To help debugging properties inheritance, I leave this code that may help others ;)
            # Set the property name and uncomment those lines to activate debug prints
            # for the templates properties inheritance
            # if item.my_type == 'host' and prop == 'initial_state':
            #     debug = True
            inherited_value = self.get_property_by_inheritance(item, prop, debug=debug)
            if inherited_value is not None:
                # Inheritance has not been blocked, then update the property value
                setattr(item, prop, inherited_value)

    def apply_inheritance(self):
        """
        For all items and templates inherit properties and custom variables.

        :return: None
        """
        # We check for all Class properties if the item has it
        # if not, it check all host templates for a value
        cls = self.inner_class
        for prop in cls.properties:
            self.apply_partial_inheritance(prop)
        for item in itertools.chain(self.items.itervalues(), self.templates.itervalues()):
            self.get_customs_properties_by_inheritance(item)

    def linkify_with_contacts(self, contacts):
        """
        Link items with contacts items

        :param contacts: all contacts object
        :type contacts: object
        :return: None
        """
        for item in self:
            if getattr(item, 'contacts', None):
                new_contacts = []
                for contact_name in set(item.contacts):
                    if contact_name != '':
                        contact = contacts.find_by_name(contact_name)
                        logger.debug("Found contact for %s: %s", item, contact_name)
                        if contact is not None:
                            new_contacts.append(contact.uuid)
                        else:
                            item.add_error("the contact '%s' defined for '%s' is unknown" %
                                           (contact_name, item.get_name()))
                # Get the list, but first make elements uniq
                item.contacts = list(set(new_contacts))

    def linkify_with_escalations(self, escalations):
        """
        Link with escalations

        :param escalations: all escalations object
        :type escalations: object
        :return: None
        """
        for item in self:
            if hasattr(item, 'escalations'):
                # escalations_tab = strip_and_uniq(item.escalations)
                new_escalations = []
                for escalation_name in [e for e in item.escalations if e != '']:
                    escalation = escalations.find_by_name(escalation_name)
                    if escalation is not None:
                        new_escalations.append(escalation.uuid)
                    else:
                        self.add_error("the escalation '%s' defined for '%s' is unknown" %
                                       (escalation_name, item.get_name()))
                item.escalations = new_escalations

    def linkify_with_resultmodulations(self, resultmodulations):
        """
        Link items with resultmodulations items

        Todo: this function should be in the SchedulingItem class

        :param resultmodulations: all resultmodulations object
        :type resultmodulations: object
        :return: None
        """
        for item in self:
            if item.resultmodulations:
                resultmodulations_tab = strip_and_uniq(item.resultmodulations)
                new_resultmodulations = []
                for rm_name in resultmodulations_tab:
                    resultmod = resultmodulations.find_by_name(rm_name)
                    if resultmod is not None:
                        new_resultmodulations.append(resultmod.uuid)
                    else:
                        err = "the result modulation '%s' defined on the %s '%s' do not exist" % \
                              (rm_name, item.__class__.my_type, item.get_name())
                        item.configuration_warnings.append(err)
                        continue
                item.resultmodulations = new_resultmodulations

    def linkify_with_business_impact_modulations(self, business_impact_modulations):
        """
        Link items with business impact objects

        Todo: this function should be in the SchedulingItem class

        :param business_impact_modulations: all business impacts object
        :type business_impact_modulations: object
        :return: None
        """
        for item in self:
            if item.business_impact_modulations:
                business_impact_modulations_tab = strip_and_uniq(item.business_impact_modulations)
                new_business_impact_modulations = []
                for bim_name in business_impact_modulations_tab:
                    bi_modulation = business_impact_modulations.find_by_name(bim_name)
                    if bi_modulation is not None:
                        new_business_impact_modulations.append(bi_modulation.uuid)
                    else:
                        err = ("the business impact modulation '%s' defined on the %s "
                               "'%s' do not exist" %
                               (bim_name, item.__class__.my_type, item.get_name()))
                        item.configuration_warnings.append(err)
                        continue
                item.business_impact_modulations = new_business_impact_modulations

    @staticmethod
    def explode_contact_groups_into_contacts(item, contactgroups):
        """
        Get all contacts of contact_groups and put them in contacts container

        :param item: item where have contact_groups property
        :type item: object
        :param contactgroups: all contactgroups object
        :type contactgroups: object
        :return: None
        """
        if hasattr(item, 'contact_groups'):
            # TODO : See if we can remove this if
            if isinstance(item.contact_groups, list):
                contactgroups_names = item.contact_groups
            else:
                contactgroups_names = item.contact_groups.split(',')
            contactgroups_names = set(contactgroups_names)
            for contactgroup_name in contactgroups_names:
                contactgroup = contactgroups.find_by_name(contactgroup_name)
                if contactgroup is None:
                    item.add_error("The contact group '%s' defined on the %s '%s' do not exist" %
                                   (contactgroup_name, item.__class__.my_type, item.get_name()))
                    continue
                cnames = contactgroups.get_members_of(contactgroup_name)
                # We add contacts into our contacts
                if cnames:
                    if getattr(item, 'contacts', None):
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
        :return: None
        """
        for item in self:
            if hasattr(item, prop) and getattr(item, prop, None):
                timeperiod_name = getattr(item, prop).strip()
                logger.debug("TP %s for %s: %s", prop, item, timeperiod_name)
                # some default values are '', so set None
                if timeperiod_name == '':
                    setattr(item, prop, '')
                    continue

                # Ok, get a real name, search for it
                timeperiod = timeperiods.find_by_name(timeperiod_name)
                if timeperiod is None:
                    item.add_error(("The %s of the %s '%s' named '%s' is unknown!" %
                                    (prop, item.__class__.my_type, item.get_name(),
                                     timeperiod_name)))
                    continue
                # Got a real one, just set it :)
                setattr(item, prop, timeperiod.uuid)

    def linkify_with_triggers(self, triggers):
        """
        Link triggers

        :param triggers: triggers object
        :type triggers: object
        :return: None
        """
        for i in self:
            i.linkify_with_triggers(triggers)

    def linkify_with_checkmodulations(self, checkmodulations):
        """
        Link checkmodulation object

        :param checkmodulations: checkmodulations object
        :type checkmodulations: object
        :return: None
        """
        for item in self:
            if not hasattr(item, 'checkmodulations'):
                continue
            new_checkmodulations = []
            for modulation_name in item.checkmodulations:
                checkmodulation = checkmodulations.find_by_name(modulation_name)
                if checkmodulation is not None:
                    new_checkmodulations.append(checkmodulation.uuid)
                else:
                    item.add_error("The checkmodulation of the %s '%s' named '%s' is unknown!" %
                                   (item.__class__.my_type, item.get_name(), modulation_name))

            item.checkmodulations = new_checkmodulations

    def linkify_with_macromodulations(self, macromodulations):
        """
        Link macromodulations

        :param macromodulations: macromodulations object
        :type macromodulations: object
        :return: None
        """
        for item in self:
            if not hasattr(item, 'macromodulations'):
                continue
            new_macromodulations = []
            for modulation_name in item.macromodulations:
                macromodulation = macromodulations.find_by_name(modulation_name)
                if macromodulation is not None:
                    new_macromodulations.append(macromodulation.uuid)
                else:
                    item.add_error("The macromodulations of the %s '%s' named '%s' is unknown!" %
                                   (item.__class__.my_type, item.get_name(), modulation_name))

            item.macromodulations = new_macromodulations

    def linkify_with_modules(self, modules):
        """
        Link modules

        :param modules: modules object (all modules)
        :type modules: object
        :return: None
        """
        for item in self:
            new_modules = []
            for module_name in item.modules:
                module = modules.find_by_name(module_name)
                if module is not None:
                    new_modules.append(module)
                else:
                    item.add_error("the module %s is unknown for %s"
                                   % (module_name, item.get_name()))
            item.modules = new_modules

    @staticmethod
    def evaluate_hostgroup_expression(expr, hosts, hostgroups, look_in='hostgroups'):
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
        if look_in == 'hostgroups':
            node = ComplexExpressionFactory(look_in, hostgroups, hosts)
        else:  # templates
            node = ComplexExpressionFactory(look_in, hosts, hosts)
        expr_tree = node.eval_cor_pattern(expr)

        set_res = expr_tree.resolve_elements()

        return list(set_res)

    @staticmethod
    def get_hosts_from_hostgroups(hgname, hostgroups):
        """
        Get hosts of hostgroups

        :param hgname: hostgroup name
        :type hgname: str
        :param hostgroups: hostgroups object (all hostgroups)
        :type hostgroups: object
        :return: list of hosts names
        :rtype: list
        """
        if not isinstance(hgname, list):
            hgname = [e.strip() for e in hgname.split(',') if e.strip()]

        host_names = []

        for name in hgname:
            hostgroup = hostgroups.find_by_name(name)
            if hostgroup is None:
                raise ValueError("the hostgroup '%s' is unknown" % hgname)
            mbrs = [h.strip() for h in hostgroup.get_hosts() if h.strip()]
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
        :return: None
        """
        hnames_list = []
        # Gets item's hostgroup_name
        hgnames = getattr(item, "hostgroup_name", '')

        # Defines if hostgroup is a complex expression
        # Expands hostgroups
        if is_complex_expr(hgnames):
            hnames_list.extend(self.evaluate_hostgroup_expression(item.hostgroup_name,
                                                                  hosts, hostgroups))
        elif hgnames:
            try:
                hnames_list.extend(self.get_hosts_from_hostgroups(hgnames, hostgroups))
            except ValueError, err:
                item.add_error(str(err))

        # Expands host names
        hname = getattr(item, "host_name", '')
        hnames_list.extend([n.strip() for n in hname.split(',') if n.strip()])
        hnames = set()

        for host in hnames_list:
            # If the host start with a !, it's to be removed from
            # the hostgroup get list
            if host.startswith('!'):
                hst_to_remove = host[1:].strip()
                try:
                    hnames.remove(hst_to_remove)
                except KeyError:
                    pass
            elif host == '*':
                hnames.update([host.host_name for host in hosts.items.itervalues()
                              if getattr(host, 'host_name', '')])
            # Else it's a host to add, but maybe it's ALL
            else:
                hnames.add(host)

        item.host_name = ','.join(hnames)

    def explode_trigger_string_into_triggers(self, triggers):
        """
        Get al trigger in triggers and manage them

        :param triggers: triggers object
        :type triggers: object
        :return: None
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
        :return: list
        :rtype: list
        """
        # Ok, we say "from now, no loop :) "
        # in_loop = []

        # Create parent graph
        parents = Graph()

        # Start with all items as nodes
        for item in self:
            # Hack to get self here. Used when looping on host and host parent's
            if attr1 == "self":
                obj = item.uuid          # obj is a host/service [list]
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
                obj1 = item.uuid
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

        return parents.loop_check()

    def get_property_by_inheritance(self, obj, prop, debug=False, level=1):
        # pylint: disable=too-many-branches
        """Gets the required property from the defined templates of the concerned object

        This function creates an ordered list with the values of the required property
        defined in the object templates hierarchy and, as such, it is called recursively
        (a template can also have one or more templates).

        If the value got from a template is different from the current one, it is added
        to the templates values list.

        If a template returns a 'null' string value, it indicates that the inheritance
        is blocked and no more template search is processed.

        If the templates values list is empty, the function returns None (no inheritance).

        Else, the list is parsed with the following rules:
            - the first non-specific value of the list is returned to the caller.
            - if the list item is a list, this list items are parsed
            - if the item contains a '+' sign as first character, it indicates a
            cumulation instead of a replacement

        :param obj: name of property
        :type obj: alignak.objects.Item
        :param prop: name of the property
        :type prop: str
        :return: new value for the property,
                 None if nothing to inherit from.
                 'null' is inheritance is blocked
        :rtype: str or None
        """
        if prop in ['register', 'uuid', 'imported_from']:
            # We do not inherit from those properties
            return None

        # Get the current object property value
        current_value = getattr(obj, prop, None)
        property_class = obj.properties[prop].__class__
        default_value = obj.properties[prop].default
        i_am_a_template = obj.is_tpl()

        if debug and level == 1:
            print("-----")
        if debug:
            indent = "+" * (level)
            print('%s inheritance: %s, %s = %s (%s, default: %s)' %
                  (indent, obj.get_name(), prop, getattr(obj, prop, None),
                   property_class, default_value))

        cumulated_value = False
        if property_class == ListProp:
            if current_value is None:
                current_value = []
            elif current_value and current_value[0] and current_value[0][0] == '+':
                # If my current value is a list with the first element having a '+' sign,
                # I will cumulate with my templates (if any...)
                cumulated_value = True

        # If the object uses some templates, we will get the values defined in the templates
        templates = getattr(obj, 'templates', [])
        template_values = []
        for template_id in templates:
            template = self.templates[template_id]
            template_value = self.get_property_by_inheritance(template, prop,
                                                              debug=debug, level=level + 1)
            if template_value is None:
                continue
            if template_value == 'null':
                # Blocked inheritance
                break
            if template_value != current_value:
                template_values.append(template_value)

        # Parse the templates values list
        inherited_value = None
        if property_class == ListProp:
            inherited_value = []

        for template_value in template_values:
            if property_class != ListProp:
                # Use most recent value from the templates (as such, the first one...)
                inherited_value = template_value
                break

            # If we have a list property, check if we need to cumulate values
            if debug:
                print("%s inheritance, got a list: %s" % (indent, template_value))
            for inner_template_value in template_value:
                if not inner_template_value:
                    continue

                inherited_value.append(inner_template_value)

                # if inner_template_value[0] != '+':
                #     break

                cumulated_value = True
                if debug:
                    print("%s inheritance, I must cumulate" % (indent))
        if debug:
            if inherited_value not in (None, []):
                print("%s inheritance (%s/%s), I have: '%s' and I got: '%s' from my templates" %
                      (indent, obj.get_name(), prop, current_value, inherited_value))
            else:
                print("%s inheritance (%s/%s), I have: '%s' and I "
                      "did not get anything from my templates" %
                      (indent, obj.get_name(), prop, current_value))

        if cumulated_value:
            # Cumulate my value with my template value and remove '+' sign
            saved_value = current_value
            current_value = []
            if i_am_a_template:
                # Do not remove '+' from my current value
                for value in saved_value:
                    if not value:
                        continue
                    current_value.append(value)
            else:
                # For an object include the current value in inherited value to remove '+' sign
                inherited_value = inherited_value + saved_value

            # Remove '+' from my inherited value(s)
            for value in inherited_value:
                if not value:
                    continue
                if value[0] == '+':
                    current_value.append(value[1:])
                else:
                    current_value.append(value)
            current_value = list(set(current_value))
            if debug:
                print("%s inheritance (%s/%s), I changed value for: '%s'" %
                      (indent, obj.get_name(), prop, current_value))
        elif inherited_value not in (None, [], default_value):
            if current_value is None or current_value == default_value:
                # Only update from my template value if I have an undefined or default value
                current_value = inherited_value
                if debug:
                    print("%s inheritance (%s/%s), I changed value for: '%s'" %
                          (indent, obj.get_name(), prop, current_value))

        return current_value

    def get_customs_properties_by_inheritance(self, obj, debug=False, level=1):
        """
        Get custom properties from the templates defined in this object

        :return: list of custom properties
        :rtype: list
        """
        if debug and level == 1:
            print("-----")
        if debug:
            indent = "+" * (level)
            print('%s customs inheritance: %s, %s' %
                  (indent, obj.my_type, obj.get_name()))

        for template_uuid in obj.templates:
            template = self.templates[template_uuid]
            template_customs = self.get_customs_properties_by_inheritance(template,
                                                                          debug=debug,
                                                                          level=level + 1)
            if debug:
                indent = "+" * (level)
                print('%s template customs: %s, %s: %s' %
                      (indent, obj.my_type, obj.get_name(), template_customs))
            if template_customs is not {}:
                for prop in template_customs:
                    if prop not in obj.customs:
                        value = template_customs[prop]
                    else:
                        value = obj.customs[prop]
                    if obj.has_plus(prop):
                        value.insert(0, obj.get_plus_and_delete(prop))
                    obj.customs[prop] = value

        if debug:
            indent = "+" * (level)
            print('%s object customs: %s, %s: %s' %
                  (indent, obj.my_type, obj.get_name(), obj.customs))
        for prop in obj.customs:
            value = obj.customs[prop]
            if obj.has_plus(prop):
                value.insert(0, obj.get_plus_and_delete(prop))
                obj.customs[prop] = value

        # We can have custom properties in plus, we need to get and put them into customs
        customs_in_plus = obj.get_all_plus_and_delete()
        for prop in customs_in_plus:
            obj.customs[prop] = customs_in_plus[prop]

        if debug:
            indent = "+" * (level)
            print('%s object customs: %s, %s: %s' %
                  (indent, obj.my_type, obj.get_name(), obj.customs))
        return obj.customs
