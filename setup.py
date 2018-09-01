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
def read_requirements(filename='requirements.txt'):
    """Reads the list of requirements from given file.

    :param filename: Filename to read the requirements from.
                     Uses ``'requirements.txt'`` by default.

    :return: Requirments as list of strings.
    """
    # allow for some leeway with the argument
    if not filename.startswith('requirements'):
        filename = 'requirements-' + filename
    if not os.path.splitext(filename)[1]:
        filename += '.txt'  # no extension, add default

    def valid_line(line):
        line = line.strip()
        return line and not any(line.startswith(p) for p in ('#', '-'))

    def extract_requirement(line):
        egg_eq = '#egg='
        if egg_eq in line:
            _, requirement = line.split(egg_eq, 1)
            return requirement
        return line

    with open(filename) as f:
        lines = f.readlines()
        return list(map(extract_requirement, filter(valid_line, lines)))
requirements = read_requirements()

# Better to use exec to load the VERSION from alignak/version.py
# so to not have to import the alignak package:
with open(os.path.join('alignak', 'version.py')) as fh:
    ns = {}
    exec(fh.read(), ns)
    VERSION = ns['VERSION']

# Get default configuration files recursively
data_files = [
    ('share/alignak', ['requirements.txt']),
    ('share/alignak', ['bin/python-post-install.sh',
                       'bin/python3-post-install.sh',
                       'bin/alignak-log-rotate',
                       'contrib/images/alignak.ico',
                       'contrib/images/alignak_128x128.png',
                       'contrib/images/alignak_blue_logo.png',
                       'contrib/images/alignak_white_logo.png'])
]
for dir in ['etc', 'bin/manpages/manpages', 'bin/rc.d', 'bin/systemd', 'bin/systemV']:
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
    packages=find_packages(exclude=['contrib', 'dev', 'doc', 'tests', 'tests_integ']),
    include_package_data=True,

    # Where to install distributed files
    data_files=data_files,

    # Unzip Egg
    zip_safe=False,
    platforms='any',

    # Dependencies...
    install_requires=requirements,
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
