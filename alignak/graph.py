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
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de

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
"""This modules provide Graph class. Used to check for loop into dependencies

"""


class Graph(object):

    """Graph is a class to make graph things like DFS checks or accessibility
    Why use an atomic bomb when a little hammer is enough?
    Graph are oriented.

    """

    def __init__(self):
        self.nodes = {}

    def add_node(self, node):
        """Create the node key into the mode dict with [] value

        :param node: node to add
        :type node: object
        :return: None
        """
        self.nodes[node] = {"dfs_loop_status": "", "sons": []}

    def add_nodes(self, nodes):
        """Add several nodes into the nodes dict

        :param nodes: nodes to add
        :type nodes: object
        :return: None
        """
        for node in nodes:
            self.add_node(node)

    def add_edge(self, from_node, to_node):
        """Add edge between two node
        The edge is oriented

        :param from_node: node where edge starts
        :type from_node: object
        :param to_node: node where edge ends
        :type to_node: object
        :return: None
        """
        # Maybe to_node is unknown
        if to_node not in self.nodes:
            self.add_node(to_node)

        try:
            self.nodes[from_node]["sons"].append(to_node)
        # If from_node does not exist, add it with its son
        except KeyError:
            self.nodes[from_node] = {"dfs_loop_status": "", "sons": [to_node]}

    def loop_check(self):
        """Check if we have a loop in the graph

        :return: Nodes in loop
        :rtype: list
        """
        in_loop = []
        # Add the tag for dfs check
        for node in list(self.nodes.values()):
            node['dfs_loop_status'] = 'DFS_UNCHECKED'

        # Now do the job
        for node_id, node in self.nodes.items():
            # Run the dfs only if the node has not been already done */
            if node['dfs_loop_status'] == 'DFS_UNCHECKED':
                self.dfs_loop_search(node_id)
            # If LOOP_INSIDE, must be returned
            if node['dfs_loop_status'] == 'DFS_LOOP_INSIDE':
                in_loop.append(node_id)

        # Remove the tag
        for node in list(self.nodes.values()):
            del node['dfs_loop_status']

        return in_loop

    def dfs_loop_search(self, root):
        """Main algorithm to look for loop.
        It tags nodes and find ones stuck in loop.

        * Init all nodes with DFS_UNCHECKED value
        * DFS_TEMPORARY_CHECKED means we found it once
        * DFS_OK : this node (and all sons) are fine
        * DFS_NEAR_LOOP : One problem was found in of of the son
        * DFS_LOOP_INSIDE : This node is part of a loop

        :param root: Root of the dependency tree
        :type root:
        :return: None
        """
        # Make the root temporary checked
        self.nodes[root]['dfs_loop_status'] = 'DFS_TEMPORARY_CHECKED'

        # We are scanning the sons
        for child in self.nodes[root]["sons"]:
            child_status = self.nodes[child]['dfs_loop_status']
            # If a child is not checked, check it
            if child_status == 'DFS_UNCHECKED':
                self.dfs_loop_search(child)
                child_status = self.nodes[child]['dfs_loop_status']

            # If a child has already been temporary checked, it's a problem,
            # loop inside, and its a checked status
            if child_status == 'DFS_TEMPORARY_CHECKED':
                self.nodes[child]['dfs_loop_status'] = 'DFS_LOOP_INSIDE'
                self.nodes[root]['dfs_loop_status'] = 'DFS_LOOP_INSIDE'

            # If a child has already been temporary checked, it's a problem, loop inside
            if child_status in ('DFS_NEAR_LOOP', 'DFS_LOOP_INSIDE'):
                # if a node is known to be part of a loop, do not let it be less
                if self.nodes[root]['dfs_loop_status'] != 'DFS_LOOP_INSIDE':
                    self.nodes[root]['dfs_loop_status'] = 'DFS_NEAR_LOOP'
                # We've already seen this child, it's a problem
                self.nodes[child]['dfs_loop_status'] = 'DFS_LOOP_INSIDE'

        # If root have been modified, do not set it OK
        # A node is OK if and only if all of its children are OK
        # if it does not have a child, goes ok
        if self.nodes[root]['dfs_loop_status'] == 'DFS_TEMPORARY_CHECKED':
            self.nodes[root]['dfs_loop_status'] = 'DFS_OK'

    def get_accessibility_packs(self):
        """Get accessibility packs of the graph:
        in one pack element are related in a way. Between packs, there is no relation at all.
        TODO: Make it work for directional graph too
        Because for now, edge must be father->son AND son->father

        :return: packs of nodes
        :rtype: list
        """
        packs = []
        # Add the tag for dfs check
        for node in list(self.nodes.values()):
            node['dfs_loop_status'] = 'DFS_UNCHECKED'

        for node_id, node in self.nodes.items():
            # Run the dfs only if the node is not already done */
            if node['dfs_loop_status'] == 'DFS_UNCHECKED':
                packs.append(self.dfs_get_all_childs(node_id))

        # Remove the tag
        for node in list(self.nodes.values()):
            del node['dfs_loop_status']

        return packs

    def dfs_get_all_childs(self, root):
        """Recursively get all sons of this node

        :param root: node to get sons
        :type root:
        :return: sons
        :rtype: list
        """
        self.nodes[root]['dfs_loop_status'] = 'DFS_CHECKED'

        ret = set()
        # Me
        ret.add(root)
        # And my sons
        ret.update(self.nodes[root]['sons'])

        for child in self.nodes[root]['sons']:
            # I just don't care about already checked children
            if self.nodes[child]['dfs_loop_status'] == 'DFS_UNCHECKED':
                ret.update(self.dfs_get_all_childs(child))

        return list(ret)
