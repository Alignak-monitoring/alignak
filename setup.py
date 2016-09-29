#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import setuptools


# Fix for debian 7 python that raise error on at_exit at the end of setup.py
# (cf http://bugs.python.org/issue15881 + http://bugs.python.org/msg170215)
try:
    import multiprocessing  # pylint: disable=W0611
except ImportError:
    pass


# Better to use exec to load the VERSION from alignak/version.py
# so to not have to import the alignak package:
with open(os.path.join('alignak', 'version.py')) as fh:
    ns = {}
    exec(fh.read(), ns)
    VERSION = ns['VERSION']

os.environ['PBR_VERSION'] = VERSION

# Ask pbr to not generate AUTHORS file if environment variable does not require it
if not os.environ.get('SKIP_GENERATE_AUTHORS'):
    os.environ['SKIP_GENERATE_AUTHORS'] = '1'

# Ask pbr to not generate ChangeLog file if environment variable does not require it
if not os.environ.get('SKIP_WRITE_GIT_CHANGELOG'):
    os.environ['SKIP_WRITE_GIT_CHANGELOG'] = '1'

setuptools.setup(
    setup_requires=['pbr'],
    version=VERSION,
    pbr=True,
)
