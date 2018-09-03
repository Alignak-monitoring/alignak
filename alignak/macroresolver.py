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
#     Nicolas Dupeux, nicolas@dupeux.net
#     Gerhard Lausser, gerhard.lausser@consol.de
#     Grégory Starck, g.starck@gmail.com
#     Frédéric Pégé, frederic.pege@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Olivier Hanesse, olivier.hanesse@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de
#     David Gil, david.gil.marcos@gmail.com

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
This class resolve Macro in commands by looking at the macros list
in Class of elements. It gives a property that may be a callable or not.

It not callable, it's a simple property and we replace the macro with the property value.

If callable, it's a method that is called to get the value. For example, to
get the number of service in a host, you call a method to get the
len(host.services)
"""

import re
import time
import logging
import collections

from six import string_types

from alignak.borg import Borg

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class MacroResolver(Borg):
    """MacroResolver class is used to resolve macros (in command call). See above for details"""

    my_type = 'macroresolver'

    # Global macros
    macros = {
        'TOTALHOSTS':
            '_get_total_hosts',
        'TOTALHOSTSUP':
            '_get_total_hosts_up',
        'TOTALHOSTSDOWN':
            '_get_total_hosts_down',
        'TOTALHOSTSUNREACHABLE':
            '_get_total_hosts_unreachable',
        'TOTALHOSTSDOWNUNHANDLED':
            '_get_total_hosts_down_unhandled',
        'TOTALHOSTSUNREACHABLEUNHANDLED':
            '_get_total_hosts_unreachable_unhandled',
        'TOTALHOSTPROBLEMS':
            '_get_total_hosts_problems',
        'TOTALHOSTPROBLEMSUNHANDLED':
            '_get_total_hosts_problems_unhandled',
        'TOTALSERVICES':
            '_get_total_services',
        'TOTALSERVICESOK':
            '_get_total_services_ok',
        'TOTALSERVICESWARNING':
            '_get_total_services_warning',
        'TOTALSERVICESCRITICAL':
            '_get_total_services_critical',
        'TOTALSERVICESUNKNOWN':
            '_get_total_services_unknown',
        'TOTALSERVICESUNREACHABLE':
            '_get_total_services_unreachable',
        'TOTALSERVICESWARNINGUNHANDLED':
            '_get_total_services_warning_unhandled',
        'TOTALSERVICESCRITICALUNHANDLED':
            '_get_total_services_critical_unhandled',
        'TOTALSERVICESUNKNOWNUNHANDLED':
            '_get_total_services_unknown_unhandled',
        'TOTALSERVICEPROBLEMS':
            '_get_total_services_problems',
        'TOTALSERVICEPROBLEMSUNHANDLED':
            '_get_total_services_problems_unhandled',
        'LONGDATETIME':
            '_get_long_date_time',
        'SHORTDATETIME':
            '_get_short_date_time',
        'DATE':
            '_get_date',
        'TIME':
            '_get_time',
        'TIMET':
            '_get_timet',
        'PROCESSSTARTTIME':
            '_get_process_start_time',
        'EVENTSTARTTIME':
            '_get_events_start_time',
    }

    output_macros = [
        'HOSTOUTPUT',
        'HOSTPERFDATA',
        'HOSTACKAUTHOR',
        'HOSTACKCOMMENT',
        'SERVICEOUTPUT',
        'SERVICEPERFDATA',
        'SERVICEACKAUTHOR',
        'SERVICEACKCOMMENT'
    ]

    def init(self, conf):
        """Initialize MacroResolver instance with conf.
        Must be called at least once.

        :param conf: configuration to load
        :type conf: alignak.objects.Config
        :return: None
        """

        # For searching class and elements for on-demand
        # we need link to types
        self.my_conf = conf
        self.lists_on_demand = []
        self.hosts = self.my_conf.hosts
        # For special void host_name handling...
        self.host_class = self.hosts.inner_class
        self.lists_on_demand.append(self.hosts)
        self.services = self.my_conf.services
        self.contacts = self.my_conf.contacts
        self.lists_on_demand.append(self.contacts)
        self.hostgroups = self.my_conf.hostgroups
        self.lists_on_demand.append(self.hostgroups)
        self.commands = self.my_conf.commands
        self.servicegroups = self.my_conf.servicegroups
        self.lists_on_demand.append(self.servicegroups)
        self.contactgroups = self.my_conf.contactgroups
        self.lists_on_demand.append(self.contactgroups)
        self.illegal_macro_output_chars = self.my_conf.illegal_macro_output_chars
        self.env_prefix = self.my_conf.env_variables_prefix

    @staticmethod
    def _get_macros(chain):
        """Get all macros of a chain
        Cut '$' char and create a dict with the following structure::

        { 'MacroSTR1' : {'val': '', 'type': 'unknown'}
          'MacroSTR2' : {'val': '', 'type': 'unknown'}
        }

        :param chain: chain to parse
        :type chain: str
        :return: dict with macro parsed as key
        :rtype: dict
        """
        regex = re.compile(r'(\$)')
        elts = regex.split(chain)
        macros = {}
        in_macro = False
        for elt in elts:
            if elt == '$':
                in_macro = not in_macro
            elif in_macro:
                macros[elt] = {'val': '', 'type': 'unknown'}

        return macros

    def _get_value_from_element(self, elt, prop):
        # pylint: disable=too-many-return-statements
        """Get value from an element's property.

        the property may be a function to call.

        If the property is not resolved (because not implemented), this function will return 'n/a'

        :param elt: element
        :type elt: object
        :param prop: element property
        :type prop: str
        :return: getattr(elt, prop) or getattr(elt, prop)() (call)
        :rtype: str
        """
        args = None
        # We have args to provide to the function
        if isinstance(prop, tuple):
            prop, args = prop
        value = getattr(elt, prop, None)
        if value is None:
            return 'n/a'

        try:
            # If the macro is set to a list property
            if isinstance(value, list):
                # Return the list items, comma separated and bracketed
                return "[%s]" % ','.join(value)

            # If the macro is not set as a function to call
            if not isinstance(value, collections.Callable):
                return value

            # Case of a function call with no arguments
            if not args:
                return value()

            # Case where we need args to the function
            # ex : HOSTGROUPNAME (we need hostgroups)
            # ex : SHORTSTATUS (we need hosts and services if bp_rule)
            real_args = []
            for arg in args:
                real_args.append(getattr(self, arg, None))
            return value(*real_args)
        except AttributeError:
            # Commented because there are many unresolved macros and this log is spamming :/
            # # Raise a warning and return a strange value when macro cannot be resolved
            # warnings.warn(
            #     'Error when getting the property value for a macro: %s',
            #     MacroWarning, stacklevel=2)
            # Return a strange value when macro cannot be resolved
            return 'n/a'
        except UnicodeError:
            if isinstance(value, string_types):
                return str(value, 'utf8', errors='ignore')

            return 'n/a'

    def _delete_unwanted_caracters(self, chain):
        """Remove not wanted char from chain
        unwanted char are illegal_macro_output_chars attribute

        :param chain: chain to remove char from
        :type chain: str
        :return: chain cleaned
        :rtype: str
        """
        try:
            chain = chain.decode('utf8', 'replace')
        except UnicodeEncodeError:
            # If it is still encoded correctly, ignore...
            pass
        except AttributeError:
            # Python 3 will raise an exception because the line is still unicode
            pass
        for char in self.illegal_macro_output_chars:
            chain = chain.replace(char, '')
        return chain

    def get_env_macros(self, data):
        """Get all environment macros from data
        For each object in data ::

        * Fetch all macros in object.__class__.macros
        * Fetch all customs macros in o.custom

        :param data: data to get macro
        :type data:
        :return: dict with macro name as key and macro value as value
        :rtype: dict
        """
        env = {}

        for obj in data:
            cls = obj.__class__
            macros = cls.macros
            for macro in macros:
                if macro.startswith("USER"):
                    continue

                prop = macros[macro]
                value = self._get_value_from_element(obj, prop)
                env['%s%s' % (self.env_prefix, macro)] = value
            if hasattr(obj, 'customs'):
                # make NAGIOS__HOSTMACADDR from _MACADDR
                for cmacro in obj.customs:
                    new_env_name = '%s_%s%s' % (self.env_prefix,
                                                obj.__class__.__name__.upper(),
                                                cmacro[1:].upper())
                    env[new_env_name] = obj.customs[cmacro]

        return env

    def resolve_simple_macros_in_string(self, c_line, data, macromodulations, timeperiods,
                                        args=None):
        # pylint: disable=too-many-locals, too-many-branches, too-many-nested-blocks
        """Replace macro in the command line with the real value

        :param c_line: command line to modify
        :type c_line: str
        :param data: objects list, use to look for a specific macro
        :type data:
        :param macromodulations: the available macro modulations
        :type macromodulations: dict
        :param timeperiods: the available timeperiods
        :type timeperiods: dict
        :param args: args given to the command line, used to get "ARGN" macros.
        :type args:
        :return: command line with '$MACRO$' replaced with values
        :rtype: str
        """
        # Now we prepare the classes for looking at the class.macros
        data.append(self)  # For getting global MACROS
        if hasattr(self, 'my_conf'):
            data.append(self.my_conf)  # For USERN macros

        # we should do some loops for nested macros
        # like $USER1$ hiding like a ninja in a $ARG2$ Macro. And if
        # $USER1$ is pointing to $USER34$ etc etc, we should loop
        # until we reach the bottom. So the last loop is when we do
        # not still have macros :)
        still_got_macros = True
        nb_loop = 0
        while still_got_macros:
            nb_loop += 1
            # Ok, we want the macros in the command line
            macros = self._get_macros(c_line)

            # Put in the macros the type of macro for all macros
            self._get_type_of_macro(macros, data)

            # We can get out if we do not have macros this loop
            still_got_macros = False
            if macros:
                still_got_macros = True

            # Now we get values from elements
            for macro in macros:
                # If type ARGN, look at ARGN cutting
                if macros[macro]['type'] == 'ARGN' and args is not None:
                    macros[macro]['val'] = self._resolve_argn(macro, args)
                    macros[macro]['type'] = 'resolved'
                # If object type, get value from a property
                if macros[macro]['type'] == 'object':
                    obj = macros[macro]['object']
                    if obj not in data:
                        continue
                    prop = obj.macros[macro]
                    if not prop:
                        continue
                    macros[macro]['val'] = self._get_value_from_element(obj, prop)
                    # Now check if we do not have a 'output' macro. If so, we must
                    # delete all special characters that can be dangerous
                    if macro in self.output_macros:
                        logger.debug("-> macro from: %s, %s = %s", obj, macro, macros[macro])
                        macros[macro]['val'] = self._delete_unwanted_caracters(macros[macro]['val'])
                # If custom type, get value from an object custom variables
                if macros[macro]['type'] == 'CUSTOM':
                    cls_type = macros[macro]['class']
                    # Beware : only cut the first _HOST or _SERVICE or _CONTACT value,
                    # so the macro name can have it on it..
                    macro_name = re.split('_' + cls_type, macro, 1)[1].upper()
                    logger.debug(" ->: %s - %s", cls_type, macro_name)
                    # Ok, we've got the macro like MAC_ADDRESS for _HOSTMAC_ADDRESS
                    # Now we get the element in data that have the type HOST
                    # and we check if it got the custom value
                    for elt in data:
                        if not elt or elt.__class__.my_type.upper() != cls_type:
                            continue
                        logger.debug("   : for %s: %s", elt, elt.customs)
                        if not getattr(elt, 'customs'):
                            continue
                        if '_' + macro_name in elt.customs:
                            macros[macro]['val'] = elt.customs['_' + macro_name]
                        logger.debug("   : macro %s = %s", macro, macros[macro]['val'])

                        # Then look on the macromodulations, in reverse order, so
                        # the last defined will be the first applied
                        mms = getattr(elt, 'macromodulations', [])
                        for macromodulation_id in mms[::-1]:
                            macromodulation = macromodulations[macromodulation_id]
                            if not macromodulation.is_active(timeperiods):
                                continue
                            # Look if the modulation got the value,
                            # but also if it's currently active
                            if "_%s" % macro_name in macromodulation.customs:
                                macros[macro]['val'] = macromodulation.customs["_%s" % macro_name]
                # If on-demand type, get value from an dynamic provided data objects
                if macros[macro]['type'] == 'ONDEMAND':
                    macros[macro]['val'] = self._resolve_ondemand(macro, data)

            # We resolved all we can, now replace the macros in the command call
            for macro in macros:
                c_line = c_line.replace("$%s$" % macro, "%s" % (macros[macro]['val']))

            # A $$ means we want a $, it's not a macro!
            # We replace $$ by a big dirty thing to be sure to not misinterpret it
            c_line = c_line.replace("$$", "DOUBLEDOLLAR")

            if nb_loop > 32:  # too much loop, we exit
                still_got_macros = False

        # We now replace the big dirty token we made by only a simple $
        c_line = c_line.replace("DOUBLEDOLLAR", "$")

        return c_line.strip()

    def resolve_command(self, com, data, macromodulations, timeperiods):
        """Resolve command macros with data

        :param com: check / event handler or command call object
        :type com: object
        :param data: objects list, used to search for a specific macro (custom or object related)
        :type data:
        :return: command line with '$MACRO$' replaced with values
        :param macromodulations: the available macro modulations
        :type macromodulations: dict
        :param timeperiods: the available timeperiods
        :type timeperiods: dict
        :rtype: str
        """
        logger.debug("Resolving: macros in: %s, arguments: %s",
                     com.command.command_line, com.args)
        return self.resolve_simple_macros_in_string(com.command.command_line, data,
                                                    macromodulations, timeperiods,
                                                    args=com.args)

    @staticmethod
    def _get_type_of_macro(macros, objs):
        r"""Set macros types

        Example::

        ARG\d -> ARGN,
        HOSTBLABLA -> class one and set Host in class)
        _HOSTTOTO -> HOST CUSTOM MACRO TOTO
        SERVICESTATEID:srv-1:Load$ -> MACRO SERVICESTATEID of the service Load of host srv-1

        :param macros: macros list in a dictionary
        :type macros: dict
        :param objs: objects list, used to tag object macros
        :type objs: list
        :return: None
        """
        for macro in macros:
            # ARGN Macros
            if re.match(r'ARG\d', macro):
                macros[macro]['type'] = 'ARGN'
                continue
            # USERN macros
            # are managed in the Config class, so no
            # need to look that here
            elif re.match(r'_HOST\w', macro):
                macros[macro]['type'] = 'CUSTOM'
                macros[macro]['class'] = 'HOST'
                continue
            elif re.match(r'_SERVICE\w', macro):
                macros[macro]['type'] = 'CUSTOM'
                macros[macro]['class'] = 'SERVICE'
                # value of macro: re.split('_HOST', '_HOSTMAC_ADDRESS')[1]
                continue
            elif re.match(r'_CONTACT\w', macro):
                macros[macro]['type'] = 'CUSTOM'
                macros[macro]['class'] = 'CONTACT'
                continue
            # On demand macro
            elif len(macro.split(':')) > 1:
                macros[macro]['type'] = 'ONDEMAND'
                continue
            # OK, classical macro...
            for obj in objs:
                if macro in obj.macros:
                    macros[macro]['type'] = 'object'
                    macros[macro]['object'] = obj
                    continue

    @staticmethod
    # pylint: disable=inconsistent-return-statements
    def _resolve_argn(macro, args):
        """Get argument from macro name
        ie : $ARG3$ -> args[2]

        :param macro: macro to parse
        :type macro:
        :param args: args given to command line
        :type args:
        :return: argument at position N-1 in args table (where N is the int parsed)
        :rtype: None | str
        """
        # first, get the number of args
        _id = None
        matches = re.search(r'ARG(?P<id>\d+)', macro)
        if matches is not None:
            _id = int(matches.group('id')) - 1
            try:
                return args[_id]
            except IndexError:
                # Required argument not found, returns an empty string
                return ''
        return ''

    def _resolve_ondemand(self, macro, data):
        # pylint: disable=too-many-locals
        """Get on demand macro value

        If the macro cannot be resolved, this function will return 'n/a' rather than
        an empty string, this to alert the caller of a potential problem.

        :param macro: macro to parse
        :type macro:
        :param data: data to get value from
        :type data:
        :return: macro value
        :rtype: str
        """
        elts = macro.split(':')
        nb_parts = len(elts)
        macro_name = elts[0]
        # 3 parts for a service, 2 for all others types...
        if nb_parts == 3:
            val = ''
            (host_name, service_description) = (elts[1], elts[2])
            # host_name can be void, so it's the host in data
            # that is important. We use our self.host_class to
            # find the host in the data :)
            if host_name == '':
                for elt in data:
                    if elt is not None and elt.__class__ == self.host_class:
                        host_name = elt.host_name
            # Ok now we get service
            serv = self.services.find_srv_by_name_and_hostname(host_name, service_description)
            if serv is not None:
                cls = serv.__class__
                prop = cls.macros[macro_name]
                val = self._get_value_from_element(serv, prop)
                return val
        # Ok, service was easy, now hard part
        else:
            val = ''
            elt_name = elts[1]
            # Special case: elt_name can be void
            # so it's the host where it apply
            if elt_name == '':
                for elt in data:
                    if elt is not None and elt.__class__ == self.host_class:
                        elt_name = elt.host_name
            for od_list in self.lists_on_demand:
                cls = od_list.inner_class
                # We search our type by looking at the macro
                if macro_name in cls.macros:
                    prop = cls.macros[macro_name]
                    i = od_list.find_by_name(elt_name)
                    if i is not None:
                        val = self._get_value_from_element(i, prop)
                        # Ok we got our value :)
                        break
            return val

        # Return a strange value in this case rather than an empty string
        return 'n/a'

    @staticmethod
    def _get_long_date_time():
        """Get long date time

        Example : Fri 15 May 11:42:39 CEST 2009

        :return: long date local time
        :rtype: str
        TODO: Should be moved to util
        TODO: Should consider timezone
        """
        return time.strftime("%a %d %b %H:%M:%S %Z %Y").decode('UTF-8', 'ignore')

    @staticmethod
    def _get_short_date_time():
        """Get short date time

        Example : 10-13-2000 00:30:28

        :return: short date local time
        :rtype: str
        TODO: Should be moved to util
        TODO: Should consider timezone
        """
        return time.strftime("%d-%m-%Y %H:%M:%S")

    @staticmethod
    def _get_date():
        """Get date

        Example : 10-13-2000

        :return: local date
        :rtype: str
        TODO: Should be moved to util
        TODO: Should consider timezone
        """
        return time.strftime("%d-%m-%Y")

    @staticmethod
    def _get_time():
        """Get date time

        Example : 00:30:28

        :return: date local time
        :rtype: str
        TODO: Should be moved to util
        TODO: Should consider timezone
        """
        return time.strftime("%H:%M:%S")

    @staticmethod
    def _get_timet():
        """Get epoch time

        Example : 1437143291

        :return: timestamp
        :rtype: str
        TODO: Should be moved to util
        TODO: Should consider timezone
        """
        return str(int(time.time()))

    def _tot_hosts_by_state(self, state=None, state_type=None):
        """Generic function to get the number of host in the specified state

        :param state: state to filter on
        :type state: str
        :param state_type: state type to filter on (HARD, SOFT)
        :type state_type: str
        :return: number of host in state *state*
        :rtype: int
        """
        if state is None and state_type is None:
            return len(self.hosts)
        if state_type:
            return sum(1 for h in self.hosts if h.state == state and h.state_type == state_type)
        return sum(1 for h in self.hosts if h.state == state)

    def _tot_unhandled_hosts_by_state(self, state):
        """Generic function to get the number of unhandled problem hosts in the specified state

        :param state: state to filter on
        :type state:
        :return: number of host in state *state* and which are not acknowledged problems
        :rtype: int
        """
        return sum(1 for h in self.hosts if h.state == state and h.state_type == u'HARD' and
                   h.is_problem and not h.problem_has_been_acknowledged)

    def _get_total_hosts(self, state_type=None):
        """
        Get the number of hosts

        :return: number of hosts
        :rtype: int
        """
        return self._tot_hosts_by_state(None, state_type=state_type)

    def _get_total_hosts_up(self, state_type=None):
        """
        Get the number of hosts up

        :return: number of hosts
        :rtype: int
        """
        return self._tot_hosts_by_state(u'UP', state_type=state_type)

    def _get_total_hosts_down(self, state_type=None):
        """
        Get the number of hosts down

        :return: number of hosts
        :rtype: int
        """
        return self._tot_hosts_by_state(u'DOWN', state_type=state_type)

    def _get_total_hosts_down_unhandled(self):
        """
        Get the number of down hosts not handled

        :return: Number of hosts down and not handled
        :rtype: int
        """
        return self._tot_unhandled_hosts_by_state(u'DOWN')

    def _get_total_hosts_unreachable(self, state_type=None):
        """
        Get the number of hosts unreachable

        :return: number of hosts
        :rtype: int
        """
        return self._tot_hosts_by_state(u'UNREACHABLE', state_type=state_type)

    def _get_total_hosts_unreachable_unhandled(self):
        """
        Get the number of unreachable hosts not handled

        :return: Number of hosts unreachable and not handled
        :rtype: int
        """
        return self._tot_unhandled_hosts_by_state(u'UNREACHABLE')

    def _get_total_hosts_problems(self):
        """Get the number of hosts that are a problem

        :return: number of hosts with is_problem attribute True
        :rtype: int
        """
        return sum(1 for h in self.hosts if h.is_problem)

    def _get_total_hosts_problems_unhandled(self):
        """
        Get the number of host problems not handled

        :return: Number of hosts which are problems and not handled
        :rtype: int
        """
        return sum(1 for h in self.hosts if h.is_problem and not h.problem_has_been_acknowledged)

    def _get_total_hosts_problems_handled(self):
        """
        Get the number of host problems not handled

        :return: Number of hosts which are problems and not handled
        :rtype: int
        """
        return sum(1 for h in self.hosts if h.is_problem and h.problem_has_been_acknowledged)

    def _get_total_hosts_downtimed(self):
        """
        Get the number of host in a scheduled downtime

        :return: Number of hosts which are downtimed
        :rtype: int
        """
        return sum(1 for h in self.hosts if h.in_scheduled_downtime)

    def _get_total_hosts_not_monitored(self):
        """
        Get the number of host not monitored (active and passive checks disabled)

        :return: Number of hosts which are not monitored
        :rtype: int
        """
        return sum(1 for h in self.hosts if not h.active_checks_enabled and
                   not h.passive_checks_enabled)

    def _get_total_hosts_flapping(self):
        """
        Get the number of hosts currently flapping

        :return: Number of hosts which are not monitored
        :rtype: int
        """
        return sum(1 for h in self.hosts if h.is_flapping)

    def _tot_services_by_state(self, state=None, state_type=None):
        """Generic function to get the number of services in the specified state

        :param state: state to filter on
        :type state: str
        :param state_type: state type to filter on (HARD, SOFT)
        :type state_type: str
        :return: number of host in state *state*
        :rtype: int
        TODO: Should be moved
        """
        if state is None and state_type is None:
            return len(self.services)
        if state_type:
            return sum(1 for s in self.services if s.state == state and s.state_type == state_type)
        return sum(1 for s in self.services if s.state == state)

    def _tot_unhandled_services_by_state(self, state):
        """Generic function to get the number of unhandled problem services in the specified state

        :param state: state to filter on
        :type state:
        :return: number of service in state *state* and which are not acknowledged problems
        :rtype: int
        """
        return sum(1 for s in self.services if s.state == state and
                   s.is_problem and not s.problem_has_been_acknowledged)

    def _get_total_services(self, state_type=None):
        """
        Get the number of services

        :return: number of services
        :rtype: int
        """
        return self._tot_services_by_state(None, state_type=state_type)

    def _get_total_services_ok(self, state_type=None):
        """
        Get the number of services ok

        :return: number of services
        :rtype: int
        """
        return self._tot_services_by_state(u'OK', state_type=state_type)

    def _get_total_services_warning(self, state_type=None):
        """
        Get the number of services warning

        :return: number of services
        :rtype: int
        """
        return self._tot_services_by_state(u'WARNING', state_type=state_type)

    def _get_total_services_critical(self, state_type=None):
        """
        Get the number of services critical

        :return: number of services
        :rtype: int
        """
        return self._tot_services_by_state(u'CRITICAL', state_type=state_type)

    def _get_total_services_unknown(self, state_type=None):
        """
        Get the number of services unknown

        :return: number of services
        :rtype: int
        """
        return self._tot_services_by_state(u'UNKNOWN', state_type=state_type)

    def _get_total_services_unreachable(self, state_type=None):
        """
        Get the number of services unreachable

        :return: number of services
        :rtype: int
        """
        return self._tot_services_by_state(u'UNREACHABLE', state_type=state_type)

    def _get_total_services_warning_unhandled(self):
        """
        Get the number of warning services not handled

        :return: Number of services warning and not handled
        :rtype: int
        """
        return self._tot_unhandled_services_by_state(u'WARNING')

    def _get_total_services_critical_unhandled(self):
        """
        Get the number of critical services not handled

        :return: Number of services critical and not handled
        :rtype: int
        """
        return self._tot_unhandled_services_by_state(u'CRITICAL')

    def _get_total_services_unknown_unhandled(self):
        """
        Get the number of unknown services not handled

        :return: Number of services unknown and not handled
        :rtype: int
        """
        return self._tot_unhandled_services_by_state(u'UNKNOWN')

    def _get_total_services_problems(self):
        """Get the number of services that are a problem

        :return: number of services with is_problem attribute True
        :rtype: int
        """
        return sum(1 for s in self.services if s.is_problem)

    def _get_total_services_problems_unhandled(self):
        """Get the number of services that are a problem and that are not acknowledged

        :return: number of problem services which are not acknowledged
        :rtype: int
        """
        return sum(1 for s in self.services if s.is_problem and not s.problem_has_been_acknowledged)

    def _get_total_services_problems_handled(self):
        """
        Get the number of service problems not handled

        :return: Number of services which are problems and not handled
        :rtype: int
        """
        return sum(1 for s in self.services if s.is_problem and s.problem_has_been_acknowledged)

    def _get_total_services_downtimed(self):
        """
        Get the number of service in a scheduled downtime

        :return: Number of services which are downtimed
        :rtype: int
        """
        return sum(1 for s in self.services if s.in_scheduled_downtime)

    def _get_total_services_not_monitored(self):
        """
        Get the number of service not monitored (active and passive checks disabled)

        :return: Number of services which are not monitored
        :rtype: int
        """
        return sum(1 for s in self.services if not s.active_checks_enabled and
                   not s.passive_checks_enabled)

    def _get_total_services_flapping(self):
        """
        Get the number of services currently flapping

        :return: Number of services which are not monitored
        :rtype: int
        """
        return sum(1 for s in self.services if s.is_flapping)

    @staticmethod
    def _get_process_start_time():
        """DOES NOTHING ( Should get process start time)

        This function always returns 'n/a' to inform that it is not available

        :return: n/a always
        :rtype: str
        TODO: Implement this
        """
        return 'n/a'

    @staticmethod
    def _get_events_start_time():
        """DOES NOTHING ( Should get events start time)

        This function always returns 'n/a' to inform that it is not available

        :return: n/a always
        :rtype: str
        """
        return 'n/a'
