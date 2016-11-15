#!/usr/bin/env python
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

import git
import re
import json
import os


def safe_dump(contrib_d):
    with open("all_contrib.json", "w+") as fh:
        fh.write(json.dumps(contrib_d))


def read_input(kind, kind_list):
    while True:
        value = raw_input("Please select %s by referring to its index in the list : 1 to %d or delete for further removal"
                          % (kind, len(kind_list)))
        if value == "delete":
            return "TODELETE"

        try:
            value = int(value) - 1
            return kind_list[value]
        except ValueError:
            print("Bad value : '%s'. Please specify an integer within a range or 'delete'" % value)


def find_real_id(names, contrib_d):
    results = set()
    for name in names:
        if name in contrib_d:
            results.add((name, contrib_d[name]["real_email"]))
            continue

        for rname, infos in contrib_d.items():
            if name.decode("utf8") in infos["aliases"]:
                results.add((rname, infos["real_email"]))
                break

    return results


def gen_partial_header(contrib_l):
    authors = []
    for name, email in contrib_l:
        authors.append("#     %s, %s\n" % (name, email))
    return authors


def regen_file(pfile, authors):
    buff = []
    in_auth = False
    with open(pfile) as fh:
        for line in fh:
            if re.search(r"#  Copyright \(C\) 2009-201[0-9]:$", line):
                in_auth = True
                buff.append(line)
                buff.extend(authors)
            elif re.search(r"#  This file is part of Shinken.$", line):
                buff.append("\n")
                buff.append(line)
                in_auth = False
            elif re.search(r"# -\*- coding: utf-8 -\*-$", line):
                pass  # Will insert coding at the end in line 2
            elif not in_auth:
                buff.append(line)

    if re.search(r"\.py$", pfile):
        buff.insert(1, "# -*- coding: utf-8 -*-\n")

    with open(pfile, "w+") as fh:
        for line in buff:
            try:
                fh.write(line.encode("utf8"))
            except:
                fh.write(line)


def get_all_contrib(all_logs):
    contrib_dict = {}
    email_d = {}
    name_d = {}


    for line in all_logs.splitlines():
        ename = None
        lname = None
        name, email = line.split("~~~")

        # Is this name mentioned with another email?
        if email in email_d:
            ename = email_d[email]

        # Is this name mentioned previously and linked to another one?
        if name in name_d:
            lname = name_d[name]

        # We found the name twice and it is not linked to the same name
        # We need to "merge" entries
        if ename is not None and lname is not None and ename != lname:
            contrib_dict[ename]["aliases"] = contrib_dict[ename]["aliases"].union(contrib_dict[lname]["aliases"])
            contrib_dict[ename]["emails"] = contrib_dict[ename]["emails"].union(contrib_dict[lname]["emails"])

            for lemail in contrib_dict[lname]["emails"]:
                email_d[lemail] = ename
            for lalias in contrib_dict[ename]["aliases"]:
                name_d[lalias] = ename
            del contrib_dict[lname]

        # We only found the name in email dict and there is nothing in the global dict
        # Add the name we found to the list
        elif name not in contrib_dict and ename is not None:
            contrib_dict[ename]["aliases"].add(name)
            name_d[name] = ename

        # We only found the name in name dict and there is nothing in the global dict
        elif name not in contrib_dict and lname is not None:
            contrib_dict[lname]["emails"].add(email)
            email_d[email] = lname

        # We found nothing and there is nothing in the global dict
        # Simple addition
        elif name not in contrib_dict:
            contrib_dict[name] = {"aliases": set((name, )), "emails": set((email, ))}
            email_d[email] = name
            name_d[name] = name

        # We already have this name
        # Add email to set
        # Update the name in email dict to be the real one
        else:
            contrib_dict[name]["emails"].add(email)
            email_d[email] = name

    return contrib_dict


def set_primary_id(contrib_d, interactive):
    new_dict = {}

    for name, infos in contrib_d.items():
        infos["aliases"] = list(infos["aliases"])
        infos["emails"] = list(infos["emails"])

        if len(infos["aliases"]) > 1 and interactive:
            real_name = read_input("aliases", infos["aliases"])
        else:
            real_name = infos["aliases"][0]

        if len(infos["emails"]) > 1 and interactive:
            real_email = read_input("emails", infos["emails"])
        else:
            real_email = infos["emails"][0]

        new_dict[real_name] = {"real_email": real_email,
                               "aliases": infos["aliases"],
                               "emails": infos["emails"]}

    return new_dict


def gen_header(repository, contrib_d):
    root = os.path.abspath(os.path.dirname(__file__) + "/../")
    last_commit = "64b0734e41527838c42d79abb4677c2c0965329a"
    for inode in os.walk(root):
        f_list = inode[2]
        for pyfile in f_list:
            if re.search(".*\.py", pyfile):
                contrib_list = []
                previous_path = re.sub("%s/alignak" % root, "shinken", inode[0])
                previous_file = re.sub("alignak", "shinken", pyfile)
                contrib_list = repository.git.log("%s" % last_commit,
                                                  "--format=%an",
                                                  "--",
                                                  previous_path + "/" + previous_file).splitlines()

                print "====" * 15, "\nFILE:%s/%s\n" % (inode[0], pyfile), "====" * 15, "\n"
                regen_file("%s/%s" % (inode[0], pyfile),
                           gen_partial_header(find_real_id(contrib_list, contrib_d)))
                print "====" * 15, "\n"
                if previous_file == []:
                    print "---------" * 30


if __name__ == "__main__":
    repo = git.repo.Repo(".")
    load = True

    if load:
        full_dict = json.load(open("all_contrib.json"))
    else:
        logs = repo.git.log("--format='%an~~~%ae'")
        full_dict = set_primary_id(get_all_contrib(logs), False)
        safe_dump(full_dict)

    gen_header(repo, full_dict)