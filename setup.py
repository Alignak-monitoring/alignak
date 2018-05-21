#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

try:
    with open('README.rst') as f:
        long_description = f.read()
except IOError:
    try:
        import pypandoc
        long_description = pypandoc.convert('README.md', 'rst')
    except (IOError, ImportError):
        long_description = "Python Alignak"

# Better to use exec to load the VERSION from alignak/version.py
# so to not have to import the alignak package:
with open(os.path.join('alignak', 'version.py')) as fh:
    ns = {}
    exec(fh.read(), ns)
    VERSION = ns['VERSION']

# Get default configuration files recursively
data_files = []
for subdir, dirs, files in os.walk('./etc'):
    # Configuration directory
    target = os.path.join('etc/alignak', re.sub(r"^(%s\/|%s$)" % ('./etc', './etc'), "", subdir))

    package_files = [os.path.join(subdir, file) for file in files]
    if package_files:
        data_files.append((target, package_files))

setup(
    name='alignak',
    version=VERSION,
    url='https://github.com/alignak-monitoring/alignak',
    license='GNU Affero General Public License',
    author="Alignak Team",
    author_email="contact@alignak.net",
    description='Alignak is a monitoring framework compatible with Nagios configuration and plugins',
    long_description=long_description,

    # Package data
    packages=find_packages(),
    include_package_data=True,

    # Where to install distributed files
    data_files=data_files,

    # Unzip Egg
    zip_safe=False,
    platforms='any',

    # Dependencies (if some) ...
    install_requires=[
        'future', 'six', 'importlib' if sys.version_info <= (2,7) else '',
        'CherryPy', 'requests', 'termcolor', 'setproctitle',
        'ujson', 'numpy', 'docopt', 'psutil'
    ],
    dependency_links=[
        "https://pypi.python.org/simple/",
    ],

    # Entry points (if some) ...
    entry_points={
        "console_scripts": [
            "alignak-environment = alignak.bin.alignak_environment:main",
            "alignak-arbiter = alignak.bin.alignak_arbiter:main",
            "alignak-broker = alignak.bin.alignak_broker:main",
            "alignak-receiver = alignak.bin.alignak_receiver:main",
            "alignak-reactionner = alignak.bin.alignak_reactionner:main",
            "alignak-poller = alignak.bin.alignak_poller:main",
            "alignak-scheduler = alignak.bin.alignak_scheduler:main"
        ]
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Customer Service',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Networking :: Monitoring',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
