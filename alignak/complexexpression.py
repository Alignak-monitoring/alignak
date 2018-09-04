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
#     aviau, alexandre.viau@savoirfairelinux.com
#     Jean Gabes, naparuba@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr

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
This module provides ComplexExpressionNode and ComplexExpressionFactory used for parsing
expression (business rules)
"""
from alignak.util import strip_and_uniq
from alignak.dependencynode import DependencyNode


class ComplexExpressionNode(object):
    """
    ComplexExpressionNode is a node class for complex_expression(s)
    """
    def __init__(self):
        self.operand = None
        self.sons = []
        self.configuration_errors = []
        self.not_value = False
        # If leaf, the content will be the hostgroup or hosts
        # that are selected with this node
        self.leaf = False
        self.content = None

    def __str__(self):  # pragma: no cover
        if not self.leaf:
            return "Op:'%s' Leaf:%s Sons:'[%s] IsNot:%s'" % \
                   (self.operand, self.leaf, ','.join([str(s) for s in self.sons]), self.not_value)

        return 'IS LEAF %s' % self.content

    def resolve_elements(self):
        """Get element of this node recursively
        Compute rules with OR or AND rule then NOT rules.

        :return: set of element
        :rtype: set
        """
        # If it's a leaf, we just need to dump a set with the content of the node
        if self.leaf:
            if not self.content:
                return set()

            return set(self.content)

        # first got the not ones in a list, and the other in the other list
        not_nodes = [s for s in self.sons if s.not_value]
        positiv_nodes = [s for s in self.sons if not s.not_value]  # ok a not not is hard to read..

        # By default we are using a OR rule
        if not self.operand:
            self.operand = '|'

        res = set()

        # The operand will change the positiv loop only
        i = 0
        for node in positiv_nodes:
            node_members = node.resolve_elements()
            if self.operand == '|':
                res = res.union(node_members)
            elif self.operand == '&':
                # The first elements of an AND rule should be used
                if i == 0:
                    res = node_members
                else:
                    res = res.intersection(node_members)
            i += 1

        # And we finally remove all NOT elements from the result
        for node in not_nodes:
            node_members = node.resolve_elements()
            res = res.difference(node_members)
        return res

    def is_valid(self):
        """
        Check if all leaves are correct (no error)

        :return: True if correct, else False
        :rtype: bool
        TODO: Fix this function and use it.
        DependencyNode should be ComplexExpressionNode
        Should return true on a leaf
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


class ComplexExpressionFactory(object):
    """ComplexExpressionFactory provides complex expression parsing functions

    """
    def __init__(self, ctx='hostgroups', grps=None, all_elements=None):
        self.ctx = ctx
        self.grps = grps
        self.all_elements = all_elements

    def eval_cor_pattern(self, pattern):  # pylint:disable=too-many-branches
        """Parse and build recursively a tree of ComplexExpressionNode from pattern

        :param pattern: pattern to parse
        :type pattern: str
        :return: root node of parsed tree
        :type: alignak.complexexpression.ComplexExpressionNode
        """
        pattern = pattern.strip()
        complex_node = False

        # Look if it's a complex pattern (with rule) or
        # if it's a leaf of it, like a host/service
        for char in '()+&|,':
            if char in pattern:
                complex_node = True

        node = ComplexExpressionNode()

        # if it's a single expression like !linux or production
        # (where "linux" and "production" are hostgroup names)
        # we will get the objects from it and return a leaf node
        if not complex_node:
            # If it's a not value, tag the node and find
            # the name without this ! operator
            if pattern.startswith('!'):
                node.not_value = True
                pattern = pattern[1:]

            node.operand = self.ctx
            node.leaf = True
            obj, error = self.find_object(pattern)
            if obj is not None:
                node.content = obj
            else:
                node.configuration_errors.append(error)
            return node

        in_par = False
        tmp = ''
        stacked_par = 0
        for char in pattern:
            if char in (',', '|'):
                # Maybe we are in a par, if so, just stack it
                if in_par:
                    tmp += char
                else:
                    # Oh we got a real cut in an expression, if so, cut it
                    tmp = tmp.strip()
                    node.operand = '|'
                    if tmp != '':
                        son = self.eval_cor_pattern(tmp)
                        node.sons.append(son)
                    tmp = ''

            elif char in ('&', '+'):
                # Maybe we are in a par, if so, just stack it
                if in_par:
                    tmp += char
                else:
                    # Oh we got a real cut in an expression, if so, cut it
                    tmp = tmp.strip()
                    node.operand = '&'
                    if tmp != '':
                        son = self.eval_cor_pattern(tmp)
                        node.sons.append(son)
                    tmp = ''

            elif char == '(':
                stacked_par += 1

                in_par = True
                tmp = tmp.strip()
                # Maybe we just start a par, but we got some things in tmp
                # that should not be good in fact !
                if stacked_par == 1 and tmp != '':
                    # TODO : real error
                    print("ERROR : bad expression near", tmp)
                    continue

                # If we are already in a par, add this (
                # but not if it's the first one so
                if stacked_par > 1:
                    tmp += char

            elif char == ')':
                stacked_par -= 1

                if stacked_par < 0:
                    # TODO : real error
                    print("Error : bad expression near", tmp, "too much ')'")
                    continue

                if stacked_par == 0:
                    tmp = tmp.strip()
                    son = self.eval_cor_pattern(tmp)
                    node.sons.append(son)
                    in_par = False
                    # OK now clean the tmp so we start clean
                    tmp = ''
                    continue

                # ok here we are still in a huge par, we just close one sub one
                tmp += char
            # Maybe it's a classic character, if so, continue
            else:
                tmp += char

        # Be sure to manage the trainling part when the line is done
        tmp = tmp.strip()
        if tmp != '':
            son = self.eval_cor_pattern(tmp)
            node.sons.append(son)

        return node

    def find_object(self, pattern):
        """Get a list of host corresponding to the pattern regarding the context

        :param pattern: pattern to find
        :type pattern: str
        :return: Host list matching pattern (hostgroup name, template, all)
        :rtype: list[alignak.objects.host.Host]
        """
        obj = None
        error = None
        pattern = pattern.strip()

        if pattern == '*':
            obj = [h.host_name for h in list(self.all_elements.items.values())
                   if getattr(h, 'host_name', '') != '' and not h.is_tpl()]
            return obj, error

        # Ok a more classic way

        if self.ctx == 'hostgroups':
            # Ok try to find this hostgroup
            hgr = self.grps.find_by_name(pattern)
            # Maybe it's an known one?
            if not hgr:
                error = "Error : cannot find the %s of the expression '%s'" % (self.ctx, pattern)
                return hgr, error
            # Ok the group is found, get the elements!
            elts = hgr.get_hosts()
            elts = strip_and_uniq(elts)

            # Maybe the hostgroup memebrs is '*', if so expand with all hosts
            if '*' in elts:
                elts.extend([h.host_name for h in list(self.all_elements.items.values())
                             if getattr(h, 'host_name', '') != '' and not h.is_tpl()])
                # And remove this strange hostname too :)
                elts.remove('*')
            return elts, error

        obj = self.grps.find_hosts_that_use_template(pattern)

        return obj, error
