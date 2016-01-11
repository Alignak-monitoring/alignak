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
#     Frédéric Vachon, fredvac@gmail.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Christophe Simon, geektophe@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Gerhard Lausser, gerhard.lausser@consol.de
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
This module provides DependencyNode and DependencyNodeFactory used for parsing
expression (business rules)
"""
import re
from alignak.util import filter_any, filter_none
from alignak.util import filter_host_by_name, filter_host_by_regex, filter_host_by_group,\
    filter_host_by_tag
from alignak.util import filter_service_by_name
from alignak.util import filter_service_by_regex_name
from alignak.util import filter_service_by_regex_host_name
from alignak.util import filter_service_by_host_name
from alignak.util import filter_service_by_bp_rule_label
from alignak.util import filter_service_by_hostgroup_name
from alignak.util import filter_service_by_host_tag_name
from alignak.util import filter_service_by_servicegroup_name
from alignak.util import filter_host_by_bp_rule_label
from alignak.util import filter_service_by_host_bp_rule_label


class DependencyNode(object):
    """
    DependencyNode is a node class for business_rule expression(s)
    """
    def __init__(self):
        self.operand = None
        self.sons = []
        # Of: values are a triple OK,WARN,CRIT
        self.of_values = ('0', '0', '0')
        self.is_of_mul = False
        self.configuration_errors = []
        self.not_value = False

    def __str__(self):
        return "Op:'%s' Val:'%s' Sons:'[%s]' IsNot:'%s'" % (self.operand, self.of_values,
                                                            ','.join([str(s) for s in self.sons]),
                                                            self.not_value)

    def get_reverse_state(self, state):
        """Do a symmetry around 1 of the state ::

        * 0 -> 2
        * 1 -> 1
        * 2 -> 0
        * else -> else

        :param state: state to reverse
        :type state: int
        :return: Integer from 0 to 2 (usually)
        :rtype: int
        """
        # Warning is still warning
        if state == 1:
            return 1
        if state == 0:
            return 2
        if state == 2:
            return 0
        # should not go here...
        return state

    def get_state(self):
        """Get node state by looking recursively over sons and applying operand

        :return: Node state
        :rtype: int
        """
        # print "Ask state of me", self

        # If we are a host or a service, wee just got the host/service
        # hard state
        if self.operand in ['host', 'service']:
            return self.get_simple_node_state()
        else:
            return self.get_complex_node_state()

    def get_simple_node_state(self):
        """Get node state, simplest case ::

        * Handle not value (revert) for host and service node
        * Return 2 instead of 1 for host

        :return: 0, 1 or 2
        :rtype: int
        TODO: Why return 1 when not 0 instead of 2 ?
        """
        state = self.sons[0].last_hard_state_id
        # print "Get the hard state (%s) for the object %s" % (state, self.sons[0].get_name())
        # Make DOWN look as CRITICAL (2 instead of 1)
        if self.operand == 'host' and state == 1:
            state = 2
        # Maybe we are a NOT node, so manage this
        if self.not_value:
            # We inverse our states
            if self.operand == 'host' and state == 1:
                return 0
            if self.operand == 'host' and state == 0:
                return 1
            # Critical -> OK
            if self.operand == 'service' and state == 2:
                return 0
            # OK -> CRITICAL (warning is untouched)
            if self.operand == 'service' and state == 0:
                return 2
        return state

    def get_complex_node_state(self):
        """Get state, handle AND, OR, X of aggregation.

        :return: 0, 1 or 2
        :rtype: int
        """
        if self.operand == '|':
            return self.get_complex_or_node_state()

        elif self.operand == '&':
            return self.get_complex_and_node_state()

        #  It's an Xof rule
        else:
            return self.get_complex_xof_node_state()

    def get_complex_or_node_state(self):
        """Get state , handle OR aggregation ::

           * Get the best state (min of sons)
           * Revert if it's a not node

        :return: 0, 1 or 2
        :rtype: int
        """
        # First we get the state of all our sons
        states = [s.get_state() for s in self.sons]
        # Next we calculate the best state
        best_state = min(states)
        # Then we handle eventual not value
        if self.not_value:
            return self.get_reverse_state(best_state)
        return best_state

    def get_complex_and_node_state(self):
        """Get state , handle AND aggregation ::

           * Get the worst state. 2 or max of sons (3 <=> UNKNOWN < CRITICAL <=> 2)
           * Revert if it's a not node

        :return: 0, 1 or 2
        :rtype: int
        """
        # First we get the state of all our sons
        states = [s.get_state() for s in self.sons]
        # Next we calculate the worst state
        if 2 in states:
            worst_state = 2
        else:
            worst_state = max(states)
        # Then we handle eventual not value
        if self.not_value:
            return self.get_reverse_state(worst_state)
        return worst_state

    def get_complex_xof_node_state(self):
        """Get state , handle X of aggregation ::

           * Count the number of OK, WARNING, CRITICAL
           * Try too apply, in this order, Critical, Warning, OK rule
           * Return the code for first match (2, 1, 0)
           * If no rule apply, return OK for simple X of and worst state for multiple X of

        :return: 0, 1 or 2
        :rtype: int
        TODO: Looks like the last if does the opposite of what the comment says
        """
        # First we get the state of all our sons
        states = [s.get_state() for s in self.sons]

        # We search for OK, WARN or CRIT applications
        # And we will choice between them
        nb_search_ok = self.of_values[0]
        nb_search_warn = self.of_values[1]
        nb_search_crit = self.of_values[2]

        # We look for each application
        nb_sons = len(states)
        nb_ok = nb_warn = nb_crit = 0
        for state in states:
            if state == 0:
                nb_ok += 1
            elif state == 1:
                nb_warn += 1
            elif state == 2:
                nb_crit += 1

        # print "NB:", nb_ok, nb_warn, nb_crit

        def get_state_for(nb_tot, nb_real, nb_search):
            """Check if there is enough value to apply this rule

            :param nb_tot: total number of value
            :type nb_tot: int
            :param nb_real: number of value that apply for this rule
            :type nb_real: int
            :param nb_search: max value to apply this rule (can be a percent)
            :type nb_search: int
            :return: True if the rule is effective (roughly nb_real > nb_search), False otherwise
            :rtype: bool
            """
            if nb_search.endswith('%'):
                nb_search = int(nb_search[:-1])
                if nb_search < 0:
                    # nb_search is negative, so +
                    nb_search = max(100 + nb_search, 0)
                apply_for = float(nb_real) / nb_tot * 100 >= nb_search
            else:
                nb_search = int(nb_search)
                if nb_search < 0:
                    # nb_search is negative, so +
                    nb_search = max(nb_tot + nb_search, 0)
                apply_for = nb_real >= nb_search
            return apply_for

        ok_apply = get_state_for(nb_sons, nb_ok, nb_search_ok)
        warn_apply = get_state_for(nb_sons, nb_warn + nb_crit, nb_search_warn)
        crit_apply = get_state_for(nb_sons, nb_crit, nb_search_crit)

        # print "What apply?", ok_apply, warn_apply, crit_apply

        # return the worst state that apply
        if crit_apply:
            if self.not_value:
                return self.get_reverse_state(2)
            return 2

        if warn_apply:
            if self.not_value:
                return self.get_reverse_state(1)
            return 1

        if ok_apply:
            if self.not_value:
                return self.get_reverse_state(0)
            return 0

        # Maybe even OK is not possible, if so, it depends if the admin
        # ask a simple form Xof: or a multiple one A,B,Cof:
        # the simple should give OK, the mult should give the worst state
        if self.is_of_mul:
            # print "Is mul, send 0"
            if self.not_value:
                return self.get_reverse_state(0)
            return 0
        else:
            # print "not mul, return worst", worse_state
            if 2 in states:
                worst_state = 2
            else:
                worst_state = max(states)
            if self.not_value:
                return self.get_reverse_state(worst_state)
            return worst_state

    def list_all_elements(self):
        """Get all host/service in our node and below

        :return: list of hosts/services
        :rtype: list
        """
        res = []

        # We are a host/service
        if self.operand in ['host', 'service']:
            return [self.sons[0]]

        for son in self.sons:
            res.extend(son.list_all_elements())

        # and uniq the result
        return list(set(res))

    def switch_zeros_of_values(self):
        """If we are a of: rule, we can get some 0 in of_values,
           if so, change them with NB sons instead

        :return: None
        """
        nb_sons = len(self.sons)
        # Need a list for assignment
        self.of_values = list(self.of_values)
        for i in [0, 1, 2]:
            if self.of_values[i] == '0':
                self.of_values[i] = str(nb_sons)
        self.of_values = tuple(self.of_values)

    def is_valid(self):
        """Check if all leaves are correct (no error)

        :return: True if correct, otherwise False
        :rtype: bool
        """

        valid = True
        if not self.sons:
            valid = False
        else:
            for son in self.sons:
                if isinstance(son, DependencyNode) and not son.is_valid():
                    self.configuration_errors.extend(son.configuration_errors)
                    valid = False
        return valid


class DependencyNodeFactory(object):
    """DependencyNodeFactory provides dependency node parsing functions

    """

    host_flags = "grlt"
    service_flags = "grl"

    def __init__(self, bound_item):
        self.bound_item = bound_item

    def eval_cor_pattern(self, pattern, hosts, services, running=False):
        """Parse and build recursively a tree of DependencyNode from pattern

        :param pattern: pattern to parse
        :type pattern: str
        :param hosts: hosts list, used to find a specific host
        :type hosts: alignak.objects.host.Host
        :param services: services list, used to find a specific service
        :type services: alignak.objects.service.Service
        :param running: rules are evaluated at run time and parsing. True means runtime
        :type running: bool
        :return: root node of parsed tree
        :rtype: alignak.dependencynode.DependencyNode
        """
        pattern = pattern.strip()
        # print "***** EVAL ", pattern
        complex_node = False

        # Look if it's a complex pattern (with rule) or
        # if it's a leaf ofit, like a host/service
        for char in '()&|':
            if char in pattern:
                complex_node = True

        # If it's a simple node, evaluate it directly
        if complex_node is False:
            return self.eval_simple_cor_pattern(pattern, hosts, services, running)
        else:
            return self.eval_complex_cor_pattern(pattern, hosts, services, running)

    def eval_xof_pattern(self, node, pattern):
        """Parse a X of pattern
        * Set is_of_mul attribute
        * Set of_values attribute

        :param node: node to edit
        :type node:
        :param pattern: line to match
        :type pattern: str
        :return: end of the line (without X of :)
        :rtype: str
        """
        xof_pattern = r"^(-?\d+%?),*(-?\d*%?),*(-?\d*%?) *of: *(.+)"
        regex = re.compile(xof_pattern)
        matches = regex.search(pattern)
        if matches is not None:
            # print "Match the of: thing N=", m.groups()
            node.operand = 'of:'
            groups = matches.groups()
            # We can have a Aof: rule, or a multiple A,B,Cof: rule.
            mul_of = (groups[1] != u'' and groups[2] != u'')
            # If multi got (A,B,C)
            if mul_of:
                node.is_of_mul = True
                node.of_values = (groups[0], groups[1], groups[2])
            else:  # if not, use A,0,0, we will change 0 after to put MAX
                node.of_values = (groups[0], '0', '0')
            pattern = matches.groups()[3]
        return pattern

    def eval_complex_cor_pattern(self, pattern, hosts, services, running=False):
        """Parse and build recursively a tree of DependencyNode from a complex pattern

        :param pattern: pattern to parse
        :type pattern: str
        :param hosts: hosts list, used to find a specific host
        :type hosts: alignak.objects.host.Host
        :param services: services list, used to find a specific service
        :type services: alignak.objects.service.Service
        :param running: rules are evaluated at run time and parsing. True means runtime
        :type running: bool
        :return: root node of parsed tree
        :rtype: alignak.dependencynode.DependencyNode
        """
        node = DependencyNode()
        pattern = self.eval_xof_pattern(node, pattern)

        in_par = False
        tmp = ''
        son_is_not = False  # We keep is the next son will be not or not
        stacked_par = 0
        for char in pattern:
            if char == '(':
                stacked_par += 1
                # print "INCREASING STACK TO", stacked_par

                in_par = True
                tmp = tmp.strip()
                # Maybe we just start a par, but we got some things in tmp
                # that should not be good in fact !
                if stacked_par == 1 and tmp != '':
                    # TODO : real error
                    print "ERROR : bad expression near", tmp
                    continue

                # If we are already in a par, add this (
                # but not if it's the first one so
                if stacked_par > 1:
                    tmp += char

            elif char == ')':
                # print "Need closeing a sub expression?", tmp
                stacked_par -= 1

                if stacked_par < 0:
                    # TODO : real error
                    print "Error : bad expression near", tmp, "too much ')'"
                    continue

                if stacked_par == 0:
                    # print "THIS is closing a sub compress expression", tmp
                    tmp = tmp.strip()
                    son = self.eval_cor_pattern(tmp, hosts, services, running)
                    # Maybe our son was notted
                    if son_is_not:
                        son.not_value = True
                        son_is_not = False
                    node.sons.append(son)
                    in_par = False
                    # OK now clean the tmp so we start clean
                    tmp = ''
                    continue

                # ok here we are still in a huge par, we just close one sub one
                tmp += char

            # Expressions in par will be parsed in a sub node after. So just
            # stack pattern
            elif in_par:
                tmp += char

            # Until here, we're not in par

            # Manage the NOT for an expression. Only allow ! at the beginning
            # of a host or a host,service expression.
            elif char == '!':
                tmp = tmp.strip()
                if tmp and tmp[0] != '!':
                    print "Error : bad expression near", tmp, "wrong position for '!'"
                    continue
                # Flags next node not state
                son_is_not = True
                # DO NOT keep the c in tmp, we consumed it

            # print "MATCHING", c, pattern
            elif char == '&' or char == '|':
                # Oh we got a real cut in an expression, if so, cut it
                # print "REAL & for cutting"
                tmp = tmp.strip()
                # Look at the rule viability
                if node.operand is not None and node.operand != 'of:' and char != node.operand:
                    # Should be logged as a warning / info? :)
                    return None

                if node.operand != 'of:':
                    node.operand = char
                if tmp != '':
                    # print "Will analyse the current str", tmp
                    son = self.eval_cor_pattern(tmp, hosts, services, running)
                    # Maybe our son was notted
                    if son_is_not:
                        son.not_value = True
                        son_is_not = False
                    node.sons.append(son)
                tmp = ''

            # Maybe it's a classic character or we're in par, if so, continue
            else:
                tmp += char

        # Be sure to manage the trainling part when the line is done
        tmp = tmp.strip()
        if tmp != '':
            # print "Managing trainling part", tmp
            son = self.eval_cor_pattern(tmp, hosts, services, running)
            # Maybe our son was notted
            if son_is_not:
                son.not_value = True
                son_is_not = False
            # print "4end I've %s got new sons" % pattern , o
            node.sons.append(son)

        # We got our nodes, so we can update 0 values of of_values
        # with the number of sons
        node.switch_zeros_of_values()

        return node

    def eval_simple_cor_pattern(self, pattern, hosts, services, running=False):
        """Parse and build recursively a tree of DependencyNode from a simple pattern

        :param pattern: pattern to parse
        :type pattern: str
        :param hosts: hosts list, used to find a specific host
        :type hosts: alignak.objects.host.Host
        :param services: services list, used to find a specific service
        :type services: alignak.objects.service.Service
        :param running: rules are evaluated at run time and parsing. True means runtime
        :type running: bool
        :return: root node of parsed tree
        :rtype: alignak.dependencynode.DependencyNode
        """
        node = DependencyNode()
        pattern = self.eval_xof_pattern(node, pattern)

        # print "Try to find?", pattern
        # If it's a not value, tag the node and find
        # the name without this ! operator
        if pattern.startswith('!'):
            node.not_value = True
            pattern = pattern[1:]
        # Is the pattern an expression to be expanded?
        if re.search(r"^([%s]+|\*):" % self.host_flags, pattern) or \
                re.search(r",\s*([%s]+:.*|\*)$" % self.service_flags, pattern):
            # o is just extracted its attributes, then trashed.
            son = self.expand_expression(pattern, hosts, services, running)
            if node.operand != 'of:':
                node.operand = '&'
            node.sons.extend(son.sons)
            node.configuration_errors.extend(son.configuration_errors)
            node.switch_zeros_of_values()
        else:
            node.operand = 'object'
            obj, error = self.find_object(pattern, hosts, services)
            if obj is not None:
                # Set host or service
                # pylint: disable=E1101
                node.operand = obj.__class__.my_type
                node.sons.append(obj)
            else:
                if running is False:
                    node.configuration_errors.append(error)
                else:
                    # As business rules are re-evaluated at run time on
                    # each scheduling loop, if the rule becomes invalid
                    # because of a badly written macro modulation, it
                    # should be notified upper for the error to be
                    # displayed in the check output.
                    raise Exception(error)
        return node

    def find_object(self, pattern, hosts, services):
        """Find object from pattern

        :param pattern: text to search (host1,service1)
        :type pattern: str
        :param hosts: hosts list, used to find a specific host
        :type hosts: alignak.objects.host.Host
        :param services: services list, used to find a specific service
        :type services: alignak.objects.service.Service
        :return: tuple with Host or Service object and error
        :rtype: tuple
        """
        # print "Finding object", pattern
        obj = None
        error = None
        is_service = False
        # h_name, service_desc are , separated
        elts = pattern.split(',')
        host_name = elts[0].strip()
        # If host_name is empty, use the host_name the business rule is bound to
        if not host_name:
            host_name = self.bound_item.host_name
        # Look if we have a service
        if len(elts) > 1:
            is_service = True
            service_description = elts[1].strip()
        if is_service:
            obj = services.find_srv_by_name_and_hostname(host_name, service_description)
            if not obj:
                error = "Business rule uses unknown service %s/%s"\
                        % (host_name, service_description)
        else:
            obj = hosts.find_by_name(host_name)
            if not obj:
                error = "Business rule uses unknown host %s" % (host_name,)
        return obj, error

    def expand_expression(self, pattern, hosts, services, running=False):
        """Expand a host or service expression into a dependency node tree
        using (host|service)group membership, regex, or labels as item selector.

        :param pattern: pattern to parse
        :type pattern: str
        :param hosts: hosts list, used to find a specific host
        :type hosts: alignak.objects.host.Host
        :param services: services list, used to find a specific service
        :type services: alignak.objects.service.Service
        :param running: rules are evaluated at run time and parsing. True means runtime
        :type running: bool
        :return: root node of parsed tree
        :rtype: alignak.dependencynode.DependencyNode
        """
        error = None
        node = DependencyNode()
        node.operand = '&'
        elts = [e.strip() for e in pattern.split(',')]
        # If host_name is empty, use the host_name the business rule is bound to
        if not elts[0]:
            elts[0] = self.bound_item.host_name
        filters = []
        # Looks for hosts/services using appropriate filters
        try:
            if len(elts) > 1:
                # We got a service expression
                host_expr, service_expr = elts
                filters.extend(self.get_srv_host_filters(host_expr))
                filters.extend(self.get_srv_service_filters(service_expr))
                items = services.find_by_filter(filters)
            else:
                # We got a host expression
                host_expr = elts[0]
                filters.extend(self.get_host_filters(host_expr))
                items = hosts.find_by_filter(filters)
        except re.error, regerr:
            error = "Business rule uses invalid regex %s: %s" % (pattern, regerr)
        else:
            if not items:
                error = "Business rule got an empty result for pattern %s" % pattern

        # Checks if we got result
        if error:
            if running is False:
                node.configuration_errors.append(error)
            else:
                # As business rules are re-evaluated at run time on
                # each scheduling loop, if the rule becomes invalid
                # because of a badly written macro modulation, it
                # should be notified upper for the error to be
                # displayed in the check output.
                raise Exception(error)
            return node

        # Creates dependency node subtree
        for item in items:
            # Creates a host/service node
            son = DependencyNode()
            son.operand = item.__class__.my_type
            son.sons.append(item)
            # Appends it to wrapping node
            node.sons.append(son)

        node.switch_zeros_of_values()
        return node

    def get_host_filters(self, expr):
        """Generates host filter list corresponding to the expression ::

        * '*' => any
        * 'g' => group filter
        * 'r' => regex name filter
        * 'l' => bp rule label filter
        * 't' => tag  filter
        * '' => none filter
        * No flag match => host name filter

        :param expr: expression to parse
        :type expr: str
        :return: filter list
        :rtype: list
        """
        if expr == "*":
            return [filter_any]
        match = re.search(r"^([%s]+):(.*)" % self.host_flags, expr)

        if match is None:
            return [filter_host_by_name(expr)]
        flags, expr = match.groups()
        if "g" in flags:
            return [filter_host_by_group(expr)]
        elif "r" in flags:
            return [filter_host_by_regex(expr)]
        elif "l" in flags:
            return [filter_host_by_bp_rule_label(expr)]
        elif "t" in flags:
            return [filter_host_by_tag(expr)]
        else:
            return [filter_none]

    def get_srv_host_filters(self, expr):
        """Generates service filter list corresponding to the expression ::

        * '*' => any
        * 'g' => hostgroup filter
        * 'r' => host regex name filter
        * 'l' => host bp rule label filter
        * 't' => tag  filter
        * '' => none filter
        * No flag match => host name filter

        :param expr: expression to parse
        :type expr: str
        :return: filter list
        :rtype: list
        """
        if expr == "*":
            return [filter_any]
        match = re.search(r"^([%s]+):(.*)" % self.host_flags, expr)
        if match is None:
            return [filter_service_by_host_name(expr)]
        flags, expr = match.groups()

        if "g" in flags:
            return [filter_service_by_hostgroup_name(expr)]
        elif "r" in flags:
            return [filter_service_by_regex_host_name(expr)]
        elif "l" in flags:
            return [filter_service_by_host_bp_rule_label(expr)]
        elif "t" in flags:
            return [filter_service_by_host_tag_name(expr)]
        else:
            return [filter_none]

    def get_srv_service_filters(self, expr):
        """Generates service filter list corresponding to the expression ::

        * '*' => any
        * 'g' => servicegroup filter
        * 'r' => service regex name filter
        * 'l' => service bp rule label filter
        * 't' => tag  filter
        * '' => none filter
        * No flag match => service name filter

        :param expr: expression to parse
        :type expr: str
        :return: filter list
        :rtype: list
        """
        if expr == "*":
            return [filter_any]
        match = re.search(r"^([%s]+):(.*)" % self.service_flags, expr)
        if match is None:
            return [filter_service_by_name(expr)]
        flags, expr = match.groups()

        if "g" in flags:
            return [filter_service_by_servicegroup_name(expr)]
        elif "r" in flags:
            return [filter_service_by_regex_name(expr)]
        elif "l" in flags:
            return [filter_service_by_bp_rule_label(expr)]
        else:
            return [filter_none]
