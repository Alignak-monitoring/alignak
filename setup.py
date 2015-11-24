#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import setuptools
import pwd


# Fix for debian 7 python that raise error on at_exit at the end of setup.py
# (cf http://bugs.python.org/issue15881)
try:
    import multiprocessing  # pylint: disable=W0611
except ImportError:
    pass


# Better to use exec to load the VERSION from alignak/bin/__init__
# so to not have to import the alignak package:
VERSION = "unknown"
ver_file = os.path.join('alignak', 'version.py')
with open(ver_file) as fh:
    exec(fh.read())

os.environ['PBR_VERSION'] = VERSION


setuptools.setup(
    setup_requires=['pbr'],
    version=VERSION,
    packages=['alignak', 'alignak.modules'],
    namespace_packages=['alignak', 'alignak.modules'],
    pbr=True,
)

try:
    uid = pwd.getpwnam("alignak").pw_uid
    os.chown('/usr/local/var/run/alignak', uid, -1)
    os.chown('/usr/local/var/log/alignak', uid, -1)
except:
    print "[Warning] alignak username not exist!"
