#! /usr/bin/env python

import shellvars
import pprint
dict = shellvars.get_vars('alignak.in')
print(dict)
# pprint(dict.__dict__)
# exit()

import os
import pprint
import subprocess
import shlex

command = shlex.split("bash -c 'set -a && source alignak.in && set +a && env'")

proc = subprocess.Popen(command, stdout = subprocess.PIPE)
for line in proc.stdout:
    (key, _, value) = line.partition("=")
    os.environ[key] = value

proc.communicate()

pprint.pprint(os.environ.__dict__)