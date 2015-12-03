"""
This file is used to get all dynamic properties to add in pylint rc file to ignore these
fields
"""

import sys
import inspect
import fileinput
from alignak.objects import *

clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)

properties = ['REQUEST' ,'acl_users', 'aq_parent']

for name, obj in clsmembers:
    if hasattr(obj, 'properties'):
        for p in obj.properties:
            properties.append(p)
    if hasattr(obj, 'running_properties'):
        for p in obj.running_properties:
            properties.append(p)

unique_prop = list(set(properties))

print unique_prop

for line in fileinput.input(['../.pylintrc'], inplace=True):
    if line.strip().startswith('generated-members='):
        line = 'generated-members=%s\n' % ','.join(unique_prop)
    sys.stdout.write(line)
