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
# pylint: disable=C0302
# pylint: disable=R0904
import time
import itertools
import logging

from copy import copy, deepcopy
from six import string_types

from alignak.alignakobject import get_a_new_object_id
from alignak.misc.serialization import serialize

from alignak.property import (StringProp, ListProp, BoolProp, SetProp, DictProp,
                              IntegerProp, ToGuessProp, PythonizeError)

from alignak.alignakobject import AlignakObject
from alignak.brok import Brok
from alignak.util import strip_and_uniq, is_complex_expr, dict_to_serialized_dict
from alignak.complexexpression import ComplexExpressionFactory
from alignak.graph import Graph

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Item(AlignakObject):
    """Class to manage an item

    An Item is the base of many objects of Alignak. So it defines properties that are common
    to all the objects:
    - name
    - register: it is a real object (True) or a template definition (False)
    - imported_from: source configuration file or backend
    - use: templates which this object inherits from
    - definition_order: priority if the same object is defined several times
    - tags: the information tags attached to an object
        Note: some tags are automatically set on an object when it uses some templates.

    And some configuration parsing information:
    - conf_is_correct: whether configuration is correct or not
    - configuration_warnings: list of configuration parsing warning log
    - configuration_errors: list of configuration parsing error log

    common functions.
    """
    properties = AlignakObject.properties.copy()
    properties.update({
        'name':
            StringProp(default=u''),
        'imported_from':
            StringProp(default=u'unknown'),
        'use':
            ListProp(default=[], split_on_comma=True),
        'definition_order':
            IntegerProp(default=100),
        'register':
            BoolProp(default=True)
    })

    running_properties = {
        # All errors and warning raised during the configuration parsing
        # and that will raise real warning/errors during the configuration correctness check
        'conf_is_correct':
            BoolProp(default=True),
        'configuration_warnings':
            ListProp(default=[]),
        'configuration_errors':
            ListProp(default=[]),

        # We save all templates we asked us to load from
        'tags':
            SetProp(default=set(), fill_brok=['full_status']),

        # used by host, service and contact
        # todo: conceptually this should be moved to the SchedulingItem and Contact objects...
        'downtimes':
            DictProp(default={}, fill_brok=['full_status'],
                     retention=True, retention_preparation=dict_to_serialized_dict),
    }

    macros = {
    }

    my_type = ''
    ok_up = ''

    def __init__(self, params=None, parsing=True):
        # pylint: disable=too-many-branches
        # Comment this to avoid too verbose log!
        # logger.debug("Initializing a %s with %s", self.my_type, params)
        if not parsing:
            # Unserializing an existing object
            # todo: Why not initializing the running properties in this case?
            super(Item, self).__init__(params, parsing)
            logger.debug("Restore %s: %s (%s)", self.__class__.my_type, self.uuid, self.get_name())
            return

        super(Item, self).__init__(params, parsing)
        # The new Alignak object unique identifier is set by the base AlignakObject class...
        logger.debug("New %s: %s", self.__class__.my_type, self.uuid)

        # For custom variables
        if not hasattr(self, 'customs'):
            self.customs = {}
        # For values with a +
        if not hasattr(self, 'plus'):
            self.plus = {}
        if not hasattr(self, 'old_properties'):
            self.old_properties = {}

        self.init_running_properties()
        # [0] = +  -> new key-plus
        # [0] = _  -> new custom entry in UPPER case
        if params is None:
            params = {}
        for key in params:
            # We want to create instance of object with the good type.
            # Here we've just parsed config files so everything is a string or a list.
            # We use the pythonize method to get the good type.
            try:
                if key in self.properties:
                    val = self.properties[key].pythonize(params[key])
                elif key in self.running_properties:
                    self.add_warning("using the running property '%s' in the configuration. "
                                     "This is accepted but not recommended!" % key)
                    val = self.running_properties[key].pythonize(params[key])
                elif hasattr(self, 'old_properties') and key in self.old_properties:
                    self.add_warning("using an old Nagios property '%s' in the configuration. "
                                     "This is accepted but not recommended!" % key)
                    val = self.properties[self.old_properties[key]].pythonize(params[key])
                elif key.startswith('_'):  # custom macro, not need to detect something here
                    macro = params[key]
                    # If it's a string, directly use this
                    if isinstance(macro, string_types):
                        val = macro
                    # a list for a custom macro is not managed (conceptually invalid)
                    # so take the first defined
                    elif isinstance(macro, list) and macro:
                        val = macro[0]
                    # not a list of void? just put void string so
                    else:
                        # For #972, a debug log is enough for such an information,
                        # a configuration warning is too much
                        val = "%s" % macro
                        logger.debug("%s, set the no-string macro property '%s' as '%s'",
                                     self.get_full_name(), key, val)
                    # After this a macro is always containing a string value!
                else:
                    # logger.debug("Guessing the property '%s' type because it "
                    #              "is not in %s object properties", key, self.__class__.__name__)
                    val = ToGuessProp().pythonize(params[key])
                    logger.debug("Set the property '%s' type as %s", key, type(val))
            except (PythonizeError, ValueError) as expt:
                self.add_error("Error while pythonizing parameter '%s': %s" % (key, expt))
                continue

            # checks for attribute value special syntax (+ or _)
            # we can have '+param' or ['+template1' , 'template2']
            if isinstance(val, string_types) and len(val) >= 1 and val[0] == '+':
                self.add_error("A + value for a single string (%s) is not handled" % key)
                continue

            if (isinstance(val, list) and
                    len(val) >= 1 and
                    isinstance(val[0], string_types) and
                    len(val[0]) >= 1 and
                    val[0][0] == '+'):
                # We manage a list property which first element is a string that starts with +
                val[0] = val[0][1:]
                self.plus[key] = val   # we remove the +
            elif key[0] == "_":
                # Except for some specific configuration variables
                # _dist prefixed variables are reserved for Alignak directories
                if not key.startswith('_dist'):
                    custom_name = key.upper()
                    self.customs[custom_name] = val
            else:
                setattr(self, key, val)

        # Change Nagios2 names to Nagios3 ones (before using them)
        self.old_properties_names_to_new()

    # Simply moved all the __ functions near the initialization
    def __str__(self):  # pragma: no cover
        return '<%s name=%s />' % (self.__class__.__name__, self.get_name())
    __repr__ = __str__

    def init_running_properties(self):
        """
        Initialize the running_properties.
        Each instance have own property.

        :return: None
        """
        for prop, entry in list(self.__class__.running_properties.items()):
            val = entry.default
            # Make a copy of the value for complex iterable types
            # As such, each instance has its own copy and not a simple reference
            setattr(self, prop, copy(val) if isinstance(val, (set, list, dict)) else val)

    def copy(self):
        """
        Get a copy of this item but with a new id

        :return: copy of this object with a new id
        :rtype: object
        """
        # New dummy item with it's own running properties
        copied_item = self.__class__({})
        # Now, copy the properties
        for prop in self.__class__.properties:
            if prop in ['uuid']:
                continue
            val = getattr(self, prop, None)
            if val:
                setattr(copied_item, prop, val)

        # Also copy some running properties
        # The custom variables
        if hasattr(self, "customs"):
            copied_item.customs = copy(self.customs)
        # And tags/templates
        if hasattr(self, "tags"):
            copied_item.tags = copy(self.tags)
        if hasattr(self, "templates"):
            copied_item.templates = copy(self.templates)

        return copied_item

    def clean(self):
        """
        Clean properties only needed for initialization and configuration

        :return: None
        """
        for prop in ('imported_from', 'use', 'plus', 'templates', 'register'):
            try:
                delattr(self, prop)
            except AttributeError:
                pass
        for prop in ('configuration_warnings', 'configuration_errors'):
            try:
                if getattr(self, prop, None) is not None and not getattr(self, prop):
                    delattr(self, prop)
            except AttributeError:
                pass

    def get_name(self):
        """
        Get the name of the item

        TODO: never called anywhere, still useful?

        :return: the object name string
        :rtype: str
        """
        return getattr(self, 'name', "unknown")

    def is_tpl(self):
        """
        Check if this object is a template

        :return: True if is a template, else False
        :rtype: bool
        """
        return not getattr(self, "register", True)

    def serialize(self):
        """This function serialize into a simple dict object.
        It is used when transferring data to other daemons over the network (http)

        Here is the generic function that simply export attributes declared in the
        properties dictionary and the running_properties of the object.

        :return: Dictionary containing key and value from properties and running_properties
        :rtype: dict
        """
        cls = self.__class__
        # id is not in *_properties
        res = {'uuid': self.uuid}
        for prop in cls.properties:
            if hasattr(self, prop) and getattr(self, prop, None) is not None:
                res[prop] = serialize(getattr(self, prop), True)
        for prop in cls.running_properties:
            if hasattr(self, prop) and getattr(self, prop, None) is not None:
                res[prop] = serialize(getattr(self, prop), True)

        return res

    @classmethod
    def load_global_conf(cls, global_configuration):
        """
        Apply global Alignak configuration.

        Some objects inherit some properties from the global configuration if they do not
        define their own value. E.g. the global 'accept_passive_service_checks' is inherited
        by the services as 'accept_passive_checks'

        :param cls: parent object
        :type cls: object
        :param global_configuration: current object (child)
        :type global_configuration: object
        :return: None
        """
        logger.debug("Propagate global parameter for %s:", cls)
        for prop, entry in global_configuration.properties.items():
            # If some global managed configuration properties have a class_inherit clause,
            if not entry.managed or not getattr(entry, 'class_inherit'):
                continue
            for (cls_dest, change_name) in entry.class_inherit:
                if cls_dest == cls:  # ok, we've got something to get
                    value = getattr(global_configuration, prop)
                    logger.debug("- global parameter %s=%s -> %s=%s",
                                 prop, getattr(global_configuration, prop),
                                 change_name, value)
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
        use = getattr(self, 'use', '')
        if isinstance(use, list):
            return [n.strip() for n in use if n.strip()]

        return [n.strip() for n in use.split(',') if n.strip()]

    def has_plus(self, prop):
        """
        Check if self.plus list have this property

        :param prop: property to check
        :type prop: str
        :return: True is self.plus has this property, otherwise False
        :rtype: bool
        """
        return prop in self.plus
        # try:
        #     self.plus[prop]
        # except KeyError:
        #     return False
        # return True

    def get_all_plus_and_delete(self):
        """
        Get all self.plus items of list. We copy it, delete the original and return the copy list

        :return: list of self.plus
        :rtype: list
        """
        res = {}
        props = list(self.plus.keys())  # we delete entries, so no for ... in ...
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

    def add_error(self, txt):
        """Add a message in the configuration errors list so we can print them
         all in one place

         Set the object configuration as not correct

        :param txt: error message
        :type txt: str
        :return: None
        """
        self.configuration_errors.append(txt)
        self.conf_is_correct = False

    def add_warning(self, txt):
        """Add a message in the configuration warnings list so we can print them
         all in one place

        :param txt: warning message
        :type txt: str
        :return: None
        """
        self.configuration_warnings.append(txt)

    def is_correct(self):
        """
        Check if this object is correct

        This function:
        - checks if the required properties are defined, ignoring special_properties if some exist
        - logs the previously found warnings and errors

        :return: True if it's correct, otherwise False
        :rtype: bool
        """
        state = self.conf_is_correct
        properties = self.__class__.properties

        for prop, entry in list(properties.items()):
            if hasattr(self, 'special_properties') and prop in getattr(self, 'special_properties'):
                continue
            if not hasattr(self, prop) and entry.required:
                msg = "[%s::%s] %s property is missing" % (self.my_type, self.get_name(), prop)
                self.add_error(msg)

        state = state & self.conf_is_correct
        return state

    def old_properties_names_to_new(self):
        """
        This function is used by service and hosts to transform Nagios2 parameters to Nagios3
        ones, like normal_check_interval to check_interval. There is a old_parameters tab
        in Classes that give such modifications to do.

        :return: None
        """
        old_properties = getattr(self.__class__, "old_properties", {})
        for old_name, new_name in list(old_properties.items()):
            # Ok, if we got old_name and NO new name,
            # we switch the name
            if hasattr(self, old_name) and not hasattr(self, new_name):
                value = getattr(self, old_name)
                setattr(self, new_name, value)
                delattr(self, old_name)

    def get_raw_import_values(self):  # pragma: no cover, never used
        """
        Get properties => values of this object

        TODO: never called anywhere, still useful?

        :return: dictionary of properties => values
        :rtype: dict
        """
        res = {}
        properties = list(self.__class__.properties.keys())
        # Register is not by default in the properties
        if 'register' not in properties:
            properties.append('register')

        for prop in properties:
            if hasattr(self, prop):
                val = getattr(self, prop)
                res[prop] = val
        return res

    def add_downtime(self, downtime):
        """
        Add a downtime in this object

        :param downtime: a Downtime object
        :type downtime: object
        :return: None
        """
        self.downtimes[downtime.uuid] = downtime

    def del_downtime(self, downtime_id):
        """
        Delete a downtime in this object

        :param downtime_id: id of the downtime to delete
        :type downtime_id: int
        :return: None
        """
        if downtime_id in self.downtimes:
            self.downtimes[downtime_id].can_be_deleted = True
            del self.downtimes[downtime_id]

    def add_comment(self, comment):
        """
        Add a comment to this object

        :param comment: a Comment object
        :type comment: object
        :return: None
        """
        self.comments[comment.uuid] = comment

    def del_comment(self, comment_id):
        """
        Delete a comment in this object

        :param comment_id: id of the comment to delete
        :type comment_id: int
        :return: None
        """
        if comment_id in self.comments:
            del self.comments[comment_id]

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
        # Configuration properties
        for prop, entry in list(cls.properties.items()):
            # Is this property intended for broking?
            if brok_type in entry.fill_brok:
                data[prop] = self.get_property_value_for_brok(prop, cls.properties)

        # And the running properties
        if hasattr(cls, 'running_properties'):
            # We've got prop in running_properties too
            for prop, entry in list(cls.running_properties.items()):
                # if 'fill_brok' in cls.running_properties[prop]:
                if brok_type in entry.fill_brok:
                    data[prop] = self.get_property_value_for_brok(prop, cls.running_properties)

    def get_initial_status_brok(self, extra=None):
        """
        Create an initial status brok

        :param extra: some extra information to be added in the brok data
        :type extra: dict
        :return: Brok object
        :rtype: alignak.Brok
        """
        data = {'uuid': self.uuid}
        self.fill_data_brok_from(data, 'full_status')
        if extra:
            data.update(extra)
        return Brok({'type': 'initial_' + self.my_type + '_status', 'data': data})

    def get_new_brok(self, name):
        """
        Create a new item brok

        :param name: name of the new object
        :type name: str
        :return: Brok object
        :rtype: alignak.Brok
        """
        return Brok({'type': 'new_' + self.my_type, 'data': {'uuid': self.uuid, 'name': name}})

    def get_update_status_brok(self):
        """
        Create an update item brok

        :return: Brok object
        :rtype: alignak.Brok
        """
        data = {'uuid': self.uuid}
        self.fill_data_brok_from(data, 'full_status')
        return Brok({'type': 'update_' + self.my_type + '_status', 'data': data})

    def get_check_result_brok(self):
        """
        Create check_result brok

        :return: Brok object
        :rtype: alignak.Brok
        """
        data = {'uuid': self.uuid}
        self.fill_data_brok_from(data, 'check_result')
        return Brok({'type': self.my_type + '_check_result', 'data': data})

    def get_next_schedule_brok(self):
        """
        Create next_schedule (next check) brok

        :return: Brok object
        :rtype: alignak.Brok
        """
        data = {'uuid': self.uuid}
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
        :rtype: alignak.Brok
        """
        data = {
            'uuid': self.uuid,
            'snapshot_output': snap_output,
            'snapshot_time': int(time.time()),
            'snapshot_exit_status': exit_status,
        }
        self.fill_data_brok_from(data, 'check_result')
        return Brok({'type': self.my_type + '_snapshot', 'data': data})

    def dump(self, dump_file_name=None):  # pragma: no cover, never called
        # pylint: disable=unused-argument
        """
        Dump Item object properties

        :return: dictionary with properties
        :rtype: dict
        """
        dump = {}
        for prop in self.properties:
            if not hasattr(self, prop):
                continue
            attr = getattr(self, prop)
            if isinstance(attr, list) and attr and isinstance(attr[0], Item):
                dump[prop] = [i.dump() for i in attr]
            elif isinstance(attr, Item):
                dump[prop] = attr.dump()
            elif attr:
                dump[prop] = getattr(self, prop)
        return dump

    def _get_name(self):
        """Get the name of the object

        :return: the object name string
        :rtype: str
        """
        return self.get_name()

    def get_full_name(self):
        """Accessor to name attribute

        :return: name
        :rtype: str
        """
        return getattr(self, 'name', 'unnamed')


class Items(object):
    """
    Class to manage all Item
    """

    inner_class = Item

    def __init__(self, items, index_items=True, parsing=True):
        self.items = {}
        self.name_to_item = {}
        self.templates = {}
        self.name_to_template = {}
        self.configuration_warnings = []
        self.configuration_errors = []

        # We are un-serializing
        if isinstance(items, dict):
            for item in list(items.values()):
                self.add_item(self.inner_class(item, parsing=parsing))
        else:
            # We are creating new items from the configuration
            self.add_items(items, index_items)

    def __repr__(self):  # pragma: no cover
        # Build a sorted list of unicode elements name or uuid, this to make it easier to compare ;)
        dump_list = sorted([str(item.get_name()
                                if isinstance(item, Item) else item) for item in self])
        return '<%r, %d elements: %r/>' % (self.__class__.__name__, len(self), dump_list)
    __str__ = __repr__

    def __iter__(self):
        return iter(list(self.items.values()))

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

    def add_error(self, txt):
        """Add a message in the configuration errors list so we can print them
         all in one place

         Set the object configuration as not correct

        :param txt: error message
        :type txt: str
        :return: None
        """
        self.configuration_errors.append(txt)
        self.conf_is_correct = False

    def add_warning(self, txt):
        """Add a message in the configuration warnings list so we can print them
         all in one place

        :param txt: warning message
        :type txt: str
        :return: None
        """
        self.configuration_warnings.append(txt)

    def add_items(self, items, index_items):
        """
        Add items to template if is template, else add in item list

        :param items: items list to add
        :type items: alignak.objects.item.Items
        :param index_items: Flag indicating if the items should be indexed on the fly.
        :type index_items: bool
        :return: None
        """
        count_templates = 0
        count_items = 0
        generated_items = []
        for item in items:
            if item.is_tpl():
                self.add_template(item)
                count_templates = count_templates + 1
            else:
                new_items = self.add_item(item, index_items)
                count_items = count_items + max(1, len(new_items))
                if new_items:
                    generated_items.extend(new_items)
        if count_templates:
            logger.info('    indexed %d template(s)', count_templates)
        if count_items:
            logger.info('    created %d.', count_items)

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
        :type item: alignak.objects.item.Item
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
        if existing_prio > item_prio:
            # New item has lower priority, so it has precedence.
            # Existing item will be deleted below
            pass
        else:
            # Don't know which one to keep, lastly defined has precedence
            objcls = getattr(self.inner_class, "my_type", "[unknown]")
            mesg = "duplicate %s '%s', from: '%s' and '%s', using lastly defined. " \
                   "You may manually set the definition_order parameter to avoid this message." \
                   % (objcls, name, item.imported_from, existing.imported_from)
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
        :type tpl: alignak.objects.item.Item
        :return: None
        """
        tpl = self.index_template(tpl)
        self.templates[tpl.uuid] = tpl

    def index_template(self, tpl):
        """
        Indexes a template by `name` into the `name_to_template` dictionary.

        :param tpl: The template to index
        :type tpl: alignak.objects.item.Item
        :return: None
        """
        objcls = self.inner_class.my_type
        name = getattr(tpl, 'name', '')
        if not name:
            mesg = "a %s template has been defined without name, from: %s" % \
                   (objcls, tpl.imported_from)
            tpl.add_error(mesg)
        elif name in self.name_to_template:
            tpl = self.manage_conflict(tpl, name)
        self.name_to_template[name] = tpl
        logger.debug("Indexed a %s template: %s, uses: %s",
                     tpl.my_type, name, getattr(tpl, 'use', 'Nothing'))
        return tpl

    def remove_template(self, tpl):
        """
        Removes and un-index a template from the `templates` container.

        :param tpl: The template to remove
        :type tpl: alignak.objects.item.Item
        :return: None
        """
        try:
            del self.templates[tpl.uuid]
        except KeyError:  # pragma: no cover, simple protection
            pass
        self.unindex_template(tpl)

    def unindex_template(self, tpl):
        """
        Unindex a template from the `templates` container.

        :param tpl: The template to un-index
        :type tpl: alignak.objects.item.Item
        :return: None
        """
        name = getattr(tpl, 'name', '')
        try:
            del self.name_to_template[name]
        except KeyError:  # pragma: no cover, simple protection
            pass

    def add_item(self, item, index=True):
        # pylint: disable=too-many-branches
        """
        Add an item into our containers, and index it depending on the `index` flag.

        :param item: object to add
        :type item: alignak.objects.item.Item
        :param index: Flag indicating if the item should be indexed
        :type index: bool
        :return: the new items created
        :rtype list
        """
        name_property = getattr(self.__class__, "name_property", None)

        # Check if some hosts are to be self-generated...
        generated_hosts = []
        if name_property:
            name = getattr(item, getattr(self.__class__, "name_property", None), None)
            if name and '[' in name and ']' in name:
                # We can create several objects from the same configuration!
                pattern = name[name.find("[")+1:name.find("]")]
                if '-' in pattern:
                    logger.debug("Found an host with a patterned name: %s", pattern)
                    # pattern is format-min-max
                    # format is optional
                    limits = pattern.split('-')
                    fmt = "%d"
                    min_v = 1
                    max_v = 1
                    if len(limits) == 3:
                        fmt = limits[2]
                        new_name = name.replace('[%s-%s-%s]' % (limits[0], limits[1], fmt), '***')
                    else:
                        new_name = name.replace('[%s-%s]' % (limits[0], limits[1]), '***')
                    try:
                        min_v = int(limits[0])
                    except ValueError:
                        pass
                    try:
                        max_v = int(limits[1])
                    except ValueError:
                        pass

                    for idx in range(min_v, max_v + 1):
                        logger.debug("- cloning host: %s", new_name.replace('***', fmt % idx))
                        new_host = deepcopy(item)
                        new_host.uuid = get_a_new_object_id()
                        new_host.host_name = new_name.replace('***', fmt % idx)
                        generated_hosts.append(new_host)

        if generated_hosts:
            for new_host in generated_hosts:
                if index is True:
                    new_host = self.index_item(new_host)
                self.items[new_host.uuid] = new_host
            logger.info("    cloned %d hosts from %s", len(generated_hosts), item.get_name())
        else:
            if index is True and name_property:
                item = self.index_item(item)
            self.items[item.uuid] = item

        return generated_hosts

    def remove_item(self, item):
        """
        Remove (and un-index) an object

        :param item: object to remove
        :type item: alignak.objects.item.Item
        :return: None
        """
        self.unindex_item(item)
        self.items.pop(item.uuid, None)

    def index_item(self, item):
        """
        Index an item into our `name_to_item` dictionary.
        If an object holding the same item's name/key already exists in the index
        then the conflict is managed by the `manage_conflict` method.

        :param item: item to index
        :type item: alignak.objects.item.Item
        :return: item modified
        :rtype: object
        """
        name_property = getattr(self.__class__, "name_property", None)
        if name_property is None:
            return None
        name = getattr(item, name_property, None)
        if name is None:
            item.add_error("a %s item has been defined without %s, from: %s"
                           % (self.inner_class.my_type, name_property, item.imported_from))
        elif name in self.name_to_item:
            item = self.manage_conflict(item, name)
        self.name_to_item[name] = item
        return item

    def unindex_item(self, item):
        """
        Un-index an item from our name_to_item dict.
        :param item: the item to un-index
        :type item: alignak.objects.item.Item
        :return: None
        """
        name_property = getattr(self.__class__, "name_property", None)
        if name_property is None:
            return
        name = getattr(item, name_property, None)
        if name is None:
            return
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

    def old_properties_names_to_new(self):  # pragma: no cover, never called
        """Convert old Nagios2 names to Nagios3 new names

        TODO: still useful?

        :return: None
        """
        for i in itertools.chain(iter(list(self.items.values())),
                                 iter(list(self.templates.values()))):
            i.old_properties_names_to_new()

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
        :type item: alignak.objects.item.Item
        :return: None
        """
        tpls = []
        tpl_names = item.get_templates()

        for name in tpl_names:
            template = self.find_tpl_by_name(name)
            if template is None:
                # TODO: Check if this should not be better to report as an error ?
                self.add_warning(
                    "%s %s use/inherit from an unknown template: %s ! from: %s" % (
                        type(item).__name__, item.get_name(), name, item.imported_from
                    )
                )
            else:
                if template is item:
                    self.add_error(
                        "%s %s use/inherits from itself ! from: %s" % (
                            type(item).__name__, item._get_name(), item.imported_from
                        )
                    )
                else:
                    tpls.append(template.uuid)
        item.templates = tpls

    def linkify_templates(self):
        """
        Link all templates, and create the template graph too

        :return: None
        """
        # First we create a list of all templates
        for i in itertools.chain(iter(list(self.items.values())),
                                 iter(list(self.templates.values()))):
            self.linkify_item_templates(i)
        for i in self:
            i.tags = self.get_all_tags(i)

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
        # we are ok at the beginning. Hope we are still ok at the end...
        valid = True

        # Better check individual items before displaying the global items list errors and warnings
        for i in self:
            # Alias and display_name hook hook
            prop_name = getattr(self.__class__, 'name_property', None)
            if prop_name and not getattr(i, 'alias', '') and hasattr(i, prop_name):
                setattr(i, 'alias', getattr(i, prop_name))
            if prop_name and getattr(i, 'display_name', '') and hasattr(i, prop_name):
                setattr(i, 'display_name', getattr(i, prop_name))

            # Now other checks
            if not i.is_correct():
                valid = False
                i.add_error("Configuration in %s::%s is incorrect; from: %s"
                            % (i.my_type, i.get_name(), i.imported_from))

            if i.configuration_errors:
                self.configuration_errors += i.configuration_errors
            if i.configuration_warnings:
                self.configuration_warnings += i.configuration_warnings

        # Raise all previous warnings
        if self.configuration_warnings:
            for msg in self.configuration_warnings:
                logger.warning("[items] %s", msg)

        # Raise all previous errors
        if self.configuration_errors:
            valid = False
            for msg in self.configuration_errors:
                logger.error("[items] %s", msg)

        return valid

    def remove_templates(self):
        """
        Remove templates

        :return: None
        """
        del self.templates

    def clean(self):
        """
        Clean the list items

        :return: None
        """
        for i in self:
            i.clean()

    def fill_default(self):
        """
        Define properties for each items with default value when not defined

        :return: None
        """
        for i in self:
            i.fill_default()

    def serialize(self):
        """This function serialize items into a simple dict object.
        It is used when transferring data to other daemons over the network (http)

        Here is the generic function that simply serialize each item of the items object

        :return: Dictionary containing item's uuid as key and item as value
        :rtype: dict
        """
        res = {}
        for key, item in list(self.items.items()):
            res[key] = item.serialize()
        return res

    def apply_partial_inheritance(self, prop):
        """
        Define property with inheritance value of the property

        :param prop: property
        :type prop: str
        :return: None
        """
        for i in itertools.chain(iter(list(self.items.values())),
                                 iter(list(self.templates.values()))):
            self.get_property_by_inheritance(i, prop)
            # If a "null" attribute was inherited, delete it
            try:
                if getattr(i, prop) == 'null':
                    delattr(i, prop)
            except AttributeError:  # pragma: no cover, simple protection
                pass

    def apply_inheritance(self):
        """
        For all items and templates inherit properties and custom variables.

        :return: None
        """
        # We check for all Class properties if the host has it
        # if not, it check all host templates for a value
        cls = self.inner_class
        for prop in cls.properties:
            self.apply_partial_inheritance(prop)
        for i in itertools.chain(iter(list(self.items.values())),
                                 iter(list(self.templates.values()))):
            self.get_customs_properties_by_inheritance(i)

    def linkify_with_contacts(self, contacts):
        """
        Link items with contacts items

        :param contacts: all contacts object
        :type contacts: alignak.objects.contact.Contacts
        :return: None
        """
        for i in self:
            if not hasattr(i, 'contacts'):
                continue

            links_list = strip_and_uniq(i.contacts)
            new = []
            for name in [e for e in links_list if e]:
                contact = contacts.find_by_name(name)
                if contact is not None and contact.uuid not in new:
                    new.append(contact.uuid)
                else:
                    i.add_error("the contact '%s' defined for '%s' is unknown"
                                % (name, i.get_name()))

            i.contacts = new

    def linkify_with_escalations(self, escalations):
        """
        Link with escalations

        :param escalations: all escalations object
        :type escalations: alignak.objects.escalation.Escalations
        :return: None
        """
        for i in self:
            if not hasattr(i, 'escalations'):
                continue

            links_list = strip_and_uniq(i.escalations)
            new = []
            for name in [e for e in links_list if e]:
                escalation = escalations.find_by_name(name)
                if escalation is not None and escalation.uuid not in new:
                    new.append(escalation.uuid)
                else:
                    i.add_error("the escalation '%s' defined for '%s' is unknown"
                                % (name, i.get_name()))

            i.escalations = new

    def linkify_with_resultmodulations(self, resultmodulations):
        """
        Link items with resultmodulations items

        :param resultmodulations: all resultmodulations object
        :type resultmodulations: alignak.resultmodulation.Resultmodulations
        :return: None
        """
        for i in self:
            if not hasattr(i, 'resultmodulations'):
                continue

            links_list = strip_and_uniq(i.resultmodulations)
            new = []
            for name in [e for e in links_list if e]:
                modulation = resultmodulations.find_by_name(name)
                if modulation is not None and modulation.uuid not in new:
                    new.append(modulation.uuid)
                else:
                    i.add_error("the result modulation '%s' defined on the %s "
                                "'%s' do not exist" % (name, i.__class__.my_type, i.get_name()))

            i.resultmodulations = new

    def linkify_with_business_impact_modulations(self, business_impact_modulations):
        """
        Link items with business impact objects

        :param business_impact_modulations: all business impacts object
        :type business_impact_modulations: alignak.objects.businessmodulation.Businessmodulations
        :return: None
        """
        for i in self:
            if not hasattr(i, 'business_impact_modulations'):
                continue

            links_list = strip_and_uniq(i.business_impact_modulations)
            new = []
            for name in [e for e in links_list if e]:
                modulation = business_impact_modulations.find_by_name(name)
                if modulation is not None and modulation.uuid not in new:
                    new.append(modulation.uuid)
                else:
                    i.add_error("the business impact modulation '%s' "
                                "defined on the %s '%s' do not exist"
                                % (name, i.__class__.my_type, i.get_name()))

                new.append(modulation.uuid)
            i.business_impact_modulations = new

    @staticmethod
    def explode_contact_groups_into_contacts(item, contactgroups):
        """
        Get all contacts of contact_groups and put them in contacts container

        :param item: item where have contact_groups property
        :type item: object
        :param contactgroups: all contactgroups object
        :type contactgroups: alignak.objects.contactgroup.Contactgroups
        :return: None
        """
        if not hasattr(item, 'contact_groups'):
            return

        # TODO : See if we can remove this if
        if isinstance(item.contact_groups, list):
            cgnames = item.contact_groups
        else:
            cgnames = item.contact_groups.split(',')
        cgnames = strip_and_uniq(cgnames)
        for cgname in cgnames:
            contactgroup = contactgroups.find_by_name(cgname)
            if not contactgroup:
                item.add_error("The contact group '%s' defined on the %s '%s' do not exist"
                               % (cgname, item.__class__.my_type, item.get_name()))
                continue
            cnames = contactgroups.get_members_of_group(cgname)
            # We add contacts into our contacts
            if cnames:
                if hasattr(item, 'contacts'):
                    # Fix #1054 - bad contact explosion
                    # item.contacts.extend(cnames)
                    item.contacts = item.contacts + cnames
                else:
                    item.contacts = cnames

    def linkify_with_timeperiods(self, timeperiods, prop):
        """
        Link items with timeperiods items

        :param timeperiods: all timeperiods object
        :type timeperiods: alignak.objects.timeperiod.Timeperiods
        :param prop: property name
        :type prop: str
        :return: None
        """
        for i in self:
            if not hasattr(i, prop):
                continue

            tpname = getattr(i, prop).strip()
            # some default values are '', so set None
            if not tpname:
                setattr(i, prop, '')
                continue

            # Ok, get a real name, search for it
            timeperiod = timeperiods.find_by_name(tpname)
            if timeperiod is None:
                i.add_error("The %s of the %s '%s' named '%s' is unknown!"
                            % (prop, i.__class__.my_type, i.get_name(), tpname))
                continue

            setattr(i, prop, timeperiod.uuid)

    def linkify_with_checkmodulations(self, checkmodulations):
        """
        Link checkmodulation object

        :param checkmodulations: checkmodulations object
        :type checkmodulations: alignak.objects.checkmodulation.Checkmodulations
        :return: None
        """
        for i in self:
            if not hasattr(i, 'checkmodulations'):
                continue

            links_list = strip_and_uniq(i.checkmodulations)
            new = []
            for name in [e for e in links_list if e]:
                modulation = checkmodulations.find_by_name(name)
                if modulation is not None and modulation.uuid not in new:
                    new.append(modulation.uuid)
                else:
                    i.add_error("The checkmodulations of the %s '%s' named "
                                "'%s' is unknown!" % (i.__class__.my_type, i.get_name(), name))

            i.checkmodulations = new

    def linkify_with_macromodulations(self, macromodulations):
        """
        Link macromodulations

        :param macromodulations: macromodulations object
        :type macromodulations: alignak.objects.macromodulation.Macromodulations
        :return: None
        """
        for i in self:
            if not hasattr(i, 'macromodulations'):
                continue

            links_list = strip_and_uniq(i.macromodulations)
            new = []
            for name in [e for e in links_list if e]:
                modulation = macromodulations.find_by_name(name)
                if modulation is not None and modulation.uuid not in new:
                    new.append(modulation.uuid)
                else:
                    i.add_error("The macromodulations of the %s '%s' named "
                                "'%s' is unknown!" % (i.__class__.my_type, i.get_name(), name))

            i.macromodulations = new

    def linkify_s_by_module(self, modules):
        """
        Link modules to items

        :param modules: Modules object (list of all the modules found in the configuration)
        :type modules: alignak.objects.module.Modules
        :return: None
        """
        for i in self:

            links_list = strip_and_uniq(i.modules)
            new = []
            for name in [e for e in links_list if e]:
                module = modules.find_by_name(name)
                if module is not None and module.uuid not in new:
                    new.append(module)
                else:
                    i.add_error("Error: the module %s is unknown for %s" % (name, i.get_name()))

            i.modules = new

    @staticmethod
    def evaluate_hostgroup_expression(expr, hosts, hostgroups, look_in='hostgroups'):
        """
        Evaluate hostgroup expression

        :param expr: an expression
        :type expr: str
        :param hosts: hosts object (all hosts)
        :type hosts: alignak.objects.host.Hosts
        :param hostgroups: hostgroups object (all hostgroups)
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
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

        # HOOK DBG
        return list(set_res)

    @staticmethod
    def get_hosts_from_hostgroups(hgname, hostgroups):
        """
        Get hosts of hostgroups

        :param hgname: hostgroup name
        :type hgname: str
        :param hostgroups: hostgroups object (all hostgroups)
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :return: list of hosts
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
        :type item: alignak.objects.item.Item
        :param hosts: hosts object
        :type hosts: alignak.objects.host.Hosts
        :param hostgroups: hostgroups object
        :type hostgroups: alignak.objects.hostgroup.Hostgroups
        :return: None
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
            except ValueError as err:  # pragma: no cover, simple protection
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
                hnames.update([host.host_name for host
                               in hosts.items.values() if getattr(host, 'host_name', '')])
            # Else it's a host to add, but maybe it's ALL
            else:
                hnames.add(host)

        item.host_name = ','.join(hnames)

    def no_loop_in_parents(self, attr1, attr2):
        # pylint: disable=too-many-branches
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
        # pylint: disable=too-many-nested-blocks
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

    def get_property_by_inheritance(self, obj, prop):
        # pylint: disable=too-many-branches
        """
        Get the property asked in parameter to this object or from defined templates of this
        object

        :param obj: the oject to search the property
        :type obj: alignak.objects.item.Item
        :param prop: name of property
        :type prop: str
        :return: Value of property of this object or of a template
        :rtype: str or None
        """
        if prop == 'register':
            return None  # We do not inherit from register

        # If I have the prop, I take mine but I check if I must
        # add a plus property
        if hasattr(obj, prop):
            value = getattr(obj, prop)
            # Manage the additive inheritance for the property,
            # if property is in plus, add or replace it
            # Template should keep the '+' at the beginning of the chain
            if obj.has_plus(prop):
                value.insert(0, obj.get_plus_and_delete(prop))
                if obj.is_tpl():
                    value = list(value)
                    value.insert(0, '+')
            return value
        # Ok, I do not have prop, Maybe my templates do?
        # Same story for plus
        # We reverse list, so that when looking for properties by inheritance,
        # the least defined template wins (if property is set).
        for t_id in obj.templates:
            template = self.templates[t_id]
            value = self.get_property_by_inheritance(template, prop)

            if value is not None and value != []:
                # If our template give us a '+' value, we should continue to loop
                still_loop = False
                if isinstance(value, list) and value[0] == '+':
                    # Templates should keep their + inherited from their parents
                    if not obj.is_tpl():
                        value = list(value)
                        value = value[1:]
                    still_loop = True

                # Maybe in the previous loop, we set a value, use it too
                if hasattr(obj, prop):
                    # If the current value is strong, it will simplify the problem
                    if not isinstance(value, list) and value[0] == '+':
                        # In this case we can remove the + from our current
                        # tpl because our value will be final
                        new_val = list(getattr(obj, prop))
                        new_val.extend(value[1:])
                        value = new_val
                    else:  # If not, se should keep the + sign of need
                        new_val = list(getattr(obj, prop))
                        new_val.extend(value)
                        value = new_val

                # Ok, we can set it
                setattr(obj, prop, value)

                # If we only got some '+' values, we must still loop
                # for an end value without it
                if not still_loop:
                    # And set my own value in the end if need
                    if obj.has_plus(prop):
                        value = list(getattr(obj, prop))
                        value.extend(obj.get_plus_and_delete(prop))
                        # Template should keep their '+'
                        if obj.is_tpl() and value[0] != '+':
                            value.insert(0, '+')
                        setattr(obj, prop, value)
                    return value

        # Maybe templates only give us + values, so we didn't quit, but we already got a
        # self.prop value after all
        template_with_only_plus = hasattr(obj, prop)

        # I do not have endingprop, my templates too... Maybe a plus?
        # warning: if all my templates gave me '+' values, do not forgot to
        # add the already set self.prop value
        if obj.has_plus(prop):
            if template_with_only_plus:
                value = list(getattr(obj, prop))
                value.extend(obj.get_plus_and_delete(prop))
            else:
                value = obj.get_plus_and_delete(prop)
            # Template should keep their '+' chain
            # We must say it's a '+' value, so our son will now that it must
            # still loop
            if obj.is_tpl() and value != [] and value[0] != '+':
                value.insert(0, '+')

            setattr(obj, prop, value)
            return value

        # Ok so in the end, we give the value we got if we have one, or None
        # Not even a plus... so None :)
        return getattr(obj, prop, None)

    def get_customs_properties_by_inheritance(self, obj):
        """
        Get custom properties from the templates defined in this object

        :param obj: the oject to search the property
        :type obj: alignak.objects.item.Item
        :return: list of custom properties
        :rtype: list
        """
        for t_id in obj.templates:
            template = self.templates[t_id]
            tpl_cv = self.get_customs_properties_by_inheritance(template)
            if tpl_cv:
                for prop in tpl_cv:
                    if prop not in obj.customs:
                        value = tpl_cv[prop]
                    else:
                        value = obj.customs[prop]
                    if obj.has_plus(prop):
                        value.insert(0, obj.get_plus_and_delete(prop))
                        # value = self.get_plus_and_delete(prop) + ',' + value
                    obj.customs[prop] = value
        for prop in obj.customs:
            value = obj.customs[prop]
            if obj.has_plus(prop):
                value.insert(0, obj.get_plus_and_delete(prop))
                obj.customs[prop] = value
        # We can get custom properties in plus, we need to get all
        # entires and put
        # them into customs
        cust_in_plus = obj.get_all_plus_and_delete()
        for prop in cust_in_plus:
            obj.customs[prop] = cust_in_plus[prop]
        return obj.customs
