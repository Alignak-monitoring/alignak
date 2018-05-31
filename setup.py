#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

long_description = "Python Alignak"
try:
    with open('README.rst') as f:
        long_description = f.read()
except IOError:
    pass

# Define the list of requirements with specified versions
requirements = [
    # Still needing future for the CarbonIFace lib and some other stuff (queues, ...)
    # Needing six for python 2.7/3 compatibility
    'future==0.16.0',
    'six==1.11.0',

    # Alignak supports the most recent CherryPy
    'CherryPy==15.0.0',

    # Requests to communicate between the daemons
    'requests==2.18.4',

    # importlib is used to import modules used by the daemons
    'importlib' if sys.version_info <= (2,7) else '',

    # Colored console log
    'termcolor==1.1.0',

    # Set process titles
    'setproctitle==1.1.10',

    # ujson is used for the internal objects serialization
    'ujson==1.35',

    # numpy for date and percentile computation - needs a compiler on the installation target system!
    # Comment to use an internal implementation of percentile function
    'numpy==1.14.3',

    # SSL between the daemons
    # This requirement is only a requirement if you intend to use SLL for the inter-daemons
    # communication. As such, to avoid installing this library per default, commenting this line!
    # Uncomment or `pip install pyopenssl` if SSL must be used between the Alignak daemons
    # pyopenssl

    # configparser is used to parse command line of the daemons
    'configparser' if sys.version_info <= (2,7) else '',
    # docopt is used by the alignak_environment script
    'docopt==0.6.2',

    # Use psutil for daemons memory monitoring (env ALIGNAK_DAEMONS_MONITORING)
    # Use psutil for scheduler ALIGNAK_LOG_MONITORING
    # Use psutil for launching daemons from the Arbiter
    'psutil==5.4.5'
]

# Better to use exec to load the VERSION from alignak/version.py
# so to not have to import the alignak package:
with open(os.path.join('alignak', 'version.py')) as fh:
    ns = {}
    exec(fh.read(), ns)
    VERSION = ns['VERSION']

# Get default configuration files recursively
data_files = [
    ('share/alignak', ['requirements.txt']),
    ('share/alignak', ['bin/post-install.sh'])
]
for dir in ['./etc', './bin/manpages/manpages', './bin/rc.d', './bin/systemd']:
    for subdir, dirs, files in os.walk(dir):
        # Configuration directory
        target = os.path.join('share/alignak', subdir)
        package_files = [os.path.join(subdir, file) for file in files]
        if package_files:
            data_files.append((target, package_files))

setup(
    name='alignak',
    version=VERSION,
    description='Alignak is a monitoring framework compatible with Nagios configuration and plugins',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/alignak-monitoring/alignak',
    download_url='https://github.com/Alignak-monitoring/alignak/archive/master.tar.gz',
    license='GNU Affero General Public License',
    author="Alignak Team",
    author_email="contact@alignak.net",

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Customer Service',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Operating System :: POSIX :: BSD :: FreeBSD',
        'Topic :: System',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Networking :: Monitoring',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='python monitoring nagios shinken',

    project_urls={
        'Presentation': 'http://alignak.net',
        'Documentation': 'http://docs.alignak.net/en/latest/',
        'Source': 'https://github.com/alignak-monitoring/alignak/',
        'Tracker': 'https://github.com/alignak-monitoring/alignak/issues',
        'Contributions': 'https://github.com/alignak-monitoring-contrib/'
    },

    # Package data
    packages=find_packages(exclude=['contrib', 'dev', 'doc', 'test', 'test_load']),
    include_package_data=True,

    # Where to install distributed files
    data_files=data_files,

    # Unzip Egg
    zip_safe=False,
    platforms='any',

    # Dependencies (if some) ...
    install_requires=[
        # Do not set specific versions - for development purposes, use the most recent versions
        # More about this: https://packaging.python.org/discussions/
        # install-requires-vs-requirements/#install-requires-vs-requirements-files
        'future',
        'six',
        'importlib' if sys.version_info <= (2,7) else '',
        'CherryPy',
        'requests',
        'termcolor',
        'setproctitle',
        'ujson',
        'numpy',
        'docopt',
        'psutil'
    ],
    dependency_links=[
        # Use the standard PyPi repository
        "https://pypi.python.org/simple/",
    ],

    # Entry points (if some) ...
    entry_points={
        "console_scripts": [
            "alignak = alignak.bin.alignak_environment:main",
            "alignak-arbiter = alignak.bin.alignak_arbiter:main",
            "alignak-broker = alignak.bin.alignak_broker:main",
            "alignak-receiver = alignak.bin.alignak_receiver:main",
            "alignak-reactionner = alignak.bin.alignak_reactionner:main",
            "alignak-poller = alignak.bin.alignak_poller:main",
            "alignak-scheduler = alignak.bin.alignak_scheduler:main"
        ]
    }
)
