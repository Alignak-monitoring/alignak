import re
import copy


class Node:
    def __init__(self, name, fromfile, parents=None, sons=None):
        self.name = name
        if parents is None:
            parents = []
        self.parents = parents
        if sons is None:
            sons = []
        self.sons = sons
        self.fromfile = fromfile

    def __str__(self):
        return self.name

    def print_sons(self):
        for son in self.sons:
            print son.name + ", "

    def print_parents(self):
        for parent in self.parents:
            print parent.name + ", "

    def is_leaf(self):
        return self.sons == []

    def is_root(self):
        return self.parents == []


def split_class(line):
    return re.search("class ([a-zA-Z]*)\(?([a-zA-Z]*)\)?", line).groups()


def print_name(graphs):

    path_map = {'Exception': '__builtin__', 'ModuleType': 'types'}
    unwanted_graph = ["DB"]
    output = ""
    for graph, nodes in graphs.items():
        if len(nodes) <= 2 or graph in unwanted_graph:
            continue
        #output += "Graph : %s | " % graph
        output += "Graph %s :\n\n.. inheritance-diagram::" % graph
        for node in nodes:
            #output += "Node :  %s; file : %s, " % (node.name, node.fromfile)
            path = node.fromfile.replace('.py', '')
            path = path.replace('.', 'alignak')
            path = path.replace('/', '.')
            if path.startswith("Unknown"):
                path = path.replace('Unknown', path_map[graph])
            output += " %s.%s " % (path, node.name)
        #output += '\n' + "========" * 10 + '\n'
        output += '\n   :parts: 3\n\n'
    print output


def add_node_from_name(graphs, cname, fromfile, parent):
    for graph, nodes in graphs.items():
        for nod in nodes:
            if nod.name == parent:
                #print "Adding node : %s with parents : %s into graph %s" % (cname, nod.name, graph)
                n = Node(cname, fromfile, [nod])
                nod.sons.append(n)
                graphs[graph].append(n)
                return True
    return False


def append_recur(glist, n_to_add):
    for node in n_to_add.sons:
        glist.append(node)
        append_recur(glist, node)


def add_node(graphs, n_to_add, fromfile, parent):
    for graph in graphs:
        for node in graphs[graph]:
            if node.name == parent:
                #print "Inserting node : %s with parents : %s into graph %s" % (n_to_add.name, node.name, graph)
                n_to_add.fromfile = fromfile
                n_to_add.parents.append(node)
                node.sons.append(n_to_add)
                graphs[graph].append(n_to_add)
                append_recur(graphs[graph], n_to_add)
                return True
    return False


def main():
    # TODO: FIX Unknown case
    # grep "^ *class "  alignak/* -r
    grep_file = open("/tmp/input")
    graphs = {}
    for line in grep_file.readlines():
        #print "Parsing '%s'" % line
        fromfile, defc = line.split(':')[:2]
        cname, parent = split_class(defc)
        if cname == "object":
            continue
        #print "Got class : %s, parent :%s" % (cname, parent)
        if (parent == '' or parent == "object") and cname not in graphs.keys():
            #print "Creating %s" % cname
            graphs[cname] = [Node(cname, fromfile)]
        # Node badly created
        elif (parent != '' and parent != "object") and cname in graphs.keys():
            if not add_node(graphs, graphs[cname][0], fromfile, parent):
                graphs[cname][0].fromfile = fromfile
                graphs[parent] = graphs[cname]
                graphs[parent].insert(0, Node(parent, "Unknown", [], [graphs[cname][0]]))
            #print "Deleting name : %s" % cname
            del graphs[cname]

        elif parent == "object" and cname in graphs.keys():
            graphs[cname][0].parents = [Node("object", "Unknown")]
            graphs[cname][0].fromfile = fromfile
        elif not add_node_from_name(graphs, cname, fromfile, parent):
            #print "parent not found : %s, class : %s" % (parent, cname)
            root = Node(parent, "Unknown", [], [])
            son = Node(cname, fromfile, [root])
            root.sons.append(son)
            if parent == "object":
                graphs[cname] = [son]
            else:
                graphs[parent] = [root, son]

    print "Diagrams\n--------\n"
    print_name(graphs)


class Tree:

    def __init__(self, root, sons=[]):
        self.root = Node(root, [], sons)

    def get_node(self, name):
        return self.get_node_r(name, self.root)

    def get_node_r(self, name, root):
        import pdb; pdb.set_trace()
        if name == root.name:
            return root

        for son in root.sons:
            return self.get_node_r(name, son)


if __name__ == "__main__":
    main()
