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
in Class of elements. It give a property that call be callable or not.
It not callable, it's a simple property and replace the macro with the value
If callable, it's a method that is called to get the value. for example, to
get the number of service in a host, you call a method to get the
len(host.services)
"""

import re
import time
import warnings

from alignak.borg import Borg


class MacroResolver(Borg):
    """MacroResolver class is used to resolve macros (in command call). See above for details"""

    my_type = 'macroresolver'

    # Global macros
    macros = {
        'TOTALHOSTSUP':
            '_get_total_hosts_up',
        'TOTALHOSTSDOWN':
            '_get_total_hosts_down',
        'TOTALHOSTSUNREACHABLE':
            '_get_total_hosts_unreachable',
        'TOTALHOSTSDOWNUNHANDLED':
            '_get_total_hosts_unhandled',
        'TOTALHOSTSUNREACHABLEUNHANDLED':
            '_get_total_hosts_unreachable_unhandled',
        'TOTALHOSTPROBLEMS':
            '_get_total_host_problems',
        'TOTALHOSTPROBLEMSUNHANDLED':
            '_get_total_host_problems_unhandled',
        'TOTALSERVICESOK':
            '_get_total_service_ok',
        'TOTALSERVICESWARNING':
            '_get_total_services_warning',
        'TOTALSERVICESCRITICAL':
            '_get_total_services_critical',
        'TOTALSERVICESUNKNOWN':
            '_get_total_services_unknown',
        'TOTALSERVICESWARNINGUNHANDLED':
            '_get_total_services_warning_unhandled',
        'TOTALSERVICESCRITICALUNHANDLED':
            '_get_total_services_critical_unhandled',
        'TOTALSERVICESUNKNOWNUNHANDLED':
            '_get_total_services_unknown_unhandled',
        'TOTALSERVICEPROBLEMS':
            '_get_total_service_problems',
        'TOTALSERVICEPROBLEMSUNHANDLED':
            '_get_total_service_problems_unhandled',
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
        """Init macroresolver instance with conf.
        Must be called once.

        :param conf: conf to load
        :type conf:
        :return: None
        """

        # For searching class and elements for on-demand
        # we need link to types
        self.conf = conf
        self.lists_on_demand = []
        self.hosts = conf.hosts
        # For special void host_name handling...
        self.host_class = self.hosts.inner_class
        self.lists_on_demand.append(self.hosts)
        self.services = conf.services
        self.contacts = conf.contacts
        self.lists_on_demand.append(self.contacts)
        self.hostgroups = conf.hostgroups
        self.lists_on_demand.append(self.hostgroups)
        self.commands = conf.commands
        self.servicegroups = conf.servicegroups
        self.lists_on_demand.append(self.servicegroups)
        self.contactgroups = conf.contactgroups
        self.lists_on_demand.append(self.contactgroups)
        self.illegal_macro_output_chars = conf.illegal_macro_output_chars

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
        # if chain in self.cache:
        #    return self.cache[chain]

        regex = re.compile(r'(\$)')
        elts = regex.split(chain)
        macros = {}
        in_macro = False
        for elt in elts:
            if elt == '$':
                in_macro = not in_macro
            elif in_macro:
                macros[elt] = {'val': '', 'type': 'unknown'}

        # self.cache[chain] = macros
        if '' in macros:
            del macros['']
        return macros

    def _get_value_from_element(self, elt, prop):
        """Get value from a element's property
        the property may be a function to call.

        :param elt: element
        :type elt: object
        :param prop: element property
        :type prop: str
        :return: getattr(elt, prop) or getattr(elt, prop)() (call)
        :rtype: str
        """
        try:
            arg = None
            # We have args to provide to the function
            if isinstance(prop, tuple):
                prop, arg = prop
            value = getattr(elt, prop)
            if callable(value):
                if arg:
                    return unicode(value(getattr(self, arg, None)))
                else:
                    return unicode(value())
            else:
                return unicode(value)
        except AttributeError:
            # Todo: there is too much macros that are not resolved that this log is spamming :/
            # # Raise a warning and return a strange value when macro cannot be resolved
            # warnings.warn(
            #     'Error when getting the property value for a macro: %s',
            #     MacroWarning, stacklevel=2)
            # Return a strange value when macro cannot be resolved
            return 'XxX'
        except UnicodeError:
            if isinstance(value, str):
                return unicode(value, 'utf8', errors='ignore')
            else:
                return 'XxX'

    def _delete_unwanted_caracters(self, chain):
        """Remove not wanted char from chain
        unwanted char are illegal_macro_output_chars attribute

        :param chain: chain to remove char from
        :type chain: str
        :return: chain cleaned
        :rtype: str
        """
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
                    break

                prop = macros[macro]
                value = self._get_value_from_element(obj, prop)
                env['NAGIOS_%s' % macro] = value
            if hasattr(obj, 'customs'):
                # make NAGIOS__HOSTMACADDR from _MACADDR
                for cmacro in obj.customs:
                    new_env_name = 'NAGIOS__' + obj.__class__.__name__.upper() + cmacro[1:].upper()
                    env[new_env_name] = obj.customs[cmacro]

        return env

    def resolve_simple_macros_in_string(self, c_line, data, macromodulations, timeperiods,
                                        args=None):
        """Replace macro in the command line with the real value

        :param c_line: command line to modify
        :type c_line: str
        :param data: objects list, use to look for a specific macro
        :type data:
        :param args: args given to the command line, used to get "ARGN" macros.
        :type args:
        :return: command line with '$MACRO$' replaced with values
        :rtype: str
        """
        # Now we prepare the classes for looking at the class.macros
        data.append(self)  # For getting global MACROS
        if hasattr(self, 'conf'):
            data.append(self.conf)  # For USERN macros

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

            # We can get out if we do not have macros this loop
            still_got_macros = (len(macros) != 0)

            # Put in the macros the type of macro for all macros
            self._get_type_of_macro(macros, data)
            # Now we get values from elements
            for macro in macros:
                # If type ARGN, look at ARGN cutting
                if macros[macro]['type'] == 'ARGN' and args is not None:
                    macros[macro]['val'] = self._resolve_argn(macro, args)
                    macros[macro]['type'] = 'resolved'
                # If object type, get value from a property
                if macros[macro]['type'] == 'object':
                    obj = macros[macro]['object']
                    for elt in data:
                        if elt is None or elt != obj:
                            continue
                        prop = obj.macros[macro]
                        macros[macro]['val'] = self._get_value_from_element(elt, prop)
                        # Now check if we do not have a 'output' macro. If so, we must
                        # delete all special characters that can be dangerous
                        if macro in self.output_macros:
                            macros[macro]['val'] = \
                                self._delete_unwanted_caracters(macros[macro]['val'])
                # If custom type, get value from an object custom variables
                if macros[macro]['type'] == 'CUSTOM':
                    cls_type = macros[macro]['class']
                    # Beware : only cut the first _HOST or _SERVICE or _CONTACT value,
                    # so the macro name can have it on it..
                    macro_name = re.split('_' + cls_type, macro, 1)[1].upper()
                    # Ok, we've got the macro like MAC_ADDRESS for _HOSTMAC_ADDRESS
                    # Now we get the element in data that have the type HOST
                    # and we check if it got the custom value
                    for elt in data:
                        if not elt or elt.__class__.my_type.upper() != cls_type:
                            continue
                        if not getattr(elt, 'customs'):
                            continue
                        if macro_name in elt.customs:
                            macros[macro]['val'] = elt.customs[macro_name]
                        # Then look on the macromodulations, in reverse order, so
                        # the last to set, will be the first to have. (yes, don't want to play
                        # with break and such things sorry...)
                        mms = getattr(elt, 'macromodulations', [])
                        for macromod_id in mms[::-1]:
                            macromod = macromodulations[macromod_id]
                            # Look if the modulation got the value,
                            # but also if it's currently active
                            if '_' + macro_name in macromod.customs and \
                                    macromod.is_active(timeperiods):
                                macros[macro]['val'] = macromod.customs['_' + macro_name]
                # If on-demand type, get value from an dynamic provided data objects
                if macros[macro]['type'] == 'ONDEMAND':
                    macros[macro]['val'] = self._resolve_ondemand(macro, data)

            # We resolved all we can, now replace the macros in the command call
            for macro in macros:
                c_line = c_line.replace('$' + macro + '$', macros[macro]['val'])

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
        :param data: objects list, use to look for a specific macro
        :type data:
        :return: command line with '$MACRO$' replaced with values
        :rtype: str
        """
        c_line = com.command.command_line
        return self.resolve_simple_macros_in_string(c_line, data, macromodulations, timeperiods,
                                                    args=com.args)

    @staticmethod
    def _get_type_of_macro(macros, objs):
        r"""Set macros types

        Example::

        ARG\d -> ARGN,
        HOSTBLABLA -> class one and set Host in class)
        _HOSTTOTO -> HOST CUSTOM MACRO TOTO
        SERVICESTATEID:srv-1:Load$ -> MACRO SERVICESTATEID of the service Load of host srv-1

        :param macros: macros list
        :type macros: list[str]
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
                return ''

    def _resolve_ondemand(self, macro, data):
        """Get on demand macro value

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
        # Len 3 == service, 2 = all others types...
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
        return ''

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

    def _tot_hosts_by_state(self, state):
        """Generic function to get the number of host in the specified state

        :param state: state to filter on
        :type state:
        :return: number of host in state *state*
        :rtype: int
        TODO: Should be moved
        """
        return sum(1 for h in self.hosts if h.state == state)

    def _get_total_hosts_up(self):
        """
        Get the number of hosts up

        :return: number of hosts
        :rtype: int
        """
        return self._tot_hosts_by_state('UP')

    def _get_total_hosts_down(self):
        """
        Get the number of hosts down

        :return: number of hosts
        :rtype: int
        """
        return self._tot_hosts_by_state('DOWN')

    def _get_total_hosts_unreachable(self):
        """
        Get the number of hosts unreachable

        :return: number of hosts
        :rtype: int
        """
        return self._tot_hosts_by_state('UNREACHABLE')

    @staticmethod
    def _get_total_hosts_unreachable_unhandled():
        """DOES NOTHING( Should get the number of unreachable hosts not handled)

        :return: 0 always
        :rtype: int
        TODO: Implement this
        """
        return 0

    def _get_total_hosts_problems(self):
        """Get the number of hosts that are a problem

        :return: number of hosts with is_problem attribute True
        :rtype: int
        """
        return sum(1 for h in self.hosts if h.is_problem)

    @staticmethod
    def _get_total_hosts_problems_unhandled():
        """DOES NOTHING( Should get the number of host problems not handled)

        :return: 0 always
        :rtype: int
        TODO: Implement this
        """
        return 0

    def _tot_services_by_state(self, state):
        """Generic function to get the number of service in the specified state

        :param state: state to filter on
        :type state:
        :return: number of service in state *state*
        :rtype: int
        TODO: Should be moved
        """
        return sum(1 for s in self.services if s.state == state)

    def _get_total_service_ok(self):
        """
        Get the number of services ok

        :return: number of services
        :rtype: int
        """
        return self._tot_services_by_state('OK')

    def _get_total_service_warning(self):
        """
        Get the number of services warning

        :return: number of services
        :rtype: int
        """
        return self._tot_services_by_state('WARNING')

    def _get_total_service_critical(self):
        """
        Get the number of services critical

        :return: number of services
        :rtype: int
        """
        return self._tot_services_by_state('CRITICAL')

    def _get_total_service_unknown(self):
        """
        Get the number of services unknown

        :return: number of services
        :rtype: int
        """
        return self._tot_services_by_state('UNKNOWN')

    @staticmethod
    def _get_total_services_warning_unhandled():
        """DOES NOTHING (Should get the number of warning services not handled)

        :return: 0 always
        :rtype: int
        TODO: Implement this
        """
        return 0

    @staticmethod
    def _get_total_services_critical_unhandled():
        """DOES NOTHING (Should get the number of critical services not handled)

        :return: 0 always
        :rtype: int
        TODO: Implement this
        """
        return 0

    @staticmethod
    def _get_total_services_unknown_unhandled():
        """DOES NOTHING (Should get the number of unknown services not handled)

        :return: 0 always
        :rtype: int
        TODO: Implement this
        """
        return 0

    def _get_total_service_problems(self):
        """Get the number of services that are a problem

        :return: number of services with is_problem attribute True
        :rtype: int
        """
        return sum(1 for s in self.services if s.is_problem)

    @staticmethod
    def _get_total_service_problems_unhandled():
        """DOES NOTHING (Should get the number of service problems not handled)

        :return: 0 always
        :rtype: int
        TODO: Implement this
        """
        return 0

    @staticmethod
    def _get_process_start_time():
        """DOES NOTHING ( Should get process start time)

        :return: 0 always
        :rtype: int
        TODO: Implement this
        """
        return 0

    @staticmethod
    def _get_events_start_time():
        """DOES NOTHING ( Should get events start time)

        :return: 0 always
        :rtype: int
        TODO: Implement this
        """
        return 0
