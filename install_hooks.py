#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import sys
import re
import fileinput
import getpass
import pwd
import grp
"""
Functions used as hooks by the setup.py installation script
"""


def user_exists(user_name):
    """
    Returns True if the user 'user_name' exists
    :param login: user account login to check for
    :return:
    """
    try:
        pwd.getpwnam(user_name)
        return True
    except KeyError:
        return False


def group_exists(group_name):
    """
    Returns True if the group 'group_name' exists
    :param login: user group to check for
    :return:
    """
    try:
        grp.getgrnam(group_name)
        return True
    except KeyError:
        return False


def get_init_scripts(config):
    """
    Add init scripts in data_files for install.
    Called before installation starts.

    :param config: current setup configuration
    :return:
    """
    if 'win' in sys.platform:
        raise Exception("Not yet Windows ready, sorry. For more information, "
                        "see: https://github.com/Alignak-monitoring/alignak/issues/522")
    elif 'linux' in sys.platform or 'sunos5' in sys.platform:
        print("Installing Alignak on Linux: %s" % sys.platform)
    elif 'bsd' in sys.platform or 'dragonfly' in sys.platform:
        print("Installing Alignak on Unix: %s" % sys.platform)
    else:
        raise Exception("Unsupported platform: %s, sorry" % sys.platform)

    print("\n"
          "===================================================="
          "====================================================")
    print("Alignak installable directories/files: ")
    for line in config['files']['data_files'].split('\n'):
        if not line:
            continue
        line = line.strip().split('=')
        if not line[1]:
            print("will create directory: %s" % (line[0]))
        else:
            print("will copy: %s to %s" % (line[1], line[0]))
    print("===================================================="
          "====================================================\n")


def fix_alignak_cfg(config):
    """
    Fix paths, user and group in alignak.cfg and daemons/*.ini
    Called once all files are copied.

    The config.install_dir contains the python sys.prefix directory (most often: /usr/local)

    :param config:
    :return:
    """

    """
    Default Alignak configuration and directories are defined as is:
    """
    alignak_cfg = {
        'USER': 'alignak',
        'GROUP': 'alignak',
        'BIN': '/bin',
        'ETC': '/etc/alignak',
        'VAR': '/var/libexec/alignak',
        'RUN': '/var/run/alignak',
        'LOG': '/var/log/alignak'
    }
    pattern = "|".join(alignak_cfg.keys())
    # Search from start of line something like ETC=qsdqsdqsd
    changing_path = re.compile("^(%s) *= *" % pattern)

    # Read main Alignak configuration file (eg. /etc/default/alignak)
    # This file may exist on older installation... or for init.d start systems
    cfg_file_name = ''
    etc_default_alignak = os.path.join("etc", "default", "alignak")
    if 'package-python-staging' in config.install_dir:
        config.install_dir = re.sub(r"^/tmp/package-python-staging-[0-9a-f]+", "", config.install_dir)
    use_local_etc_default_alignak = os.path.join(config.install_dir, "etc", "default", "alignak")
    if os.path.exists(etc_default_alignak):
        cfg_file_name = etc_default_alignak
    if os.path.exists(use_local_etc_default_alignak):
        cfg_file_name = use_local_etc_default_alignak
    if cfg_file_name:
        print("Found Alignak shell configuration file: %s" % cfg_file_name)
        for line in open(cfg_file_name):
            line = line.strip()
            got_path = changing_path.match(line)
            if got_path:
                found = got_path.group(1)
                alignak_cfg[found] = os.path.join(
                    config.install_dir, alignak_cfg[found].strip("/")
                )
    else:
        print("No Alignak shell configuration file found.")
        for path in alignak_cfg:
            if path not in ['USER', 'GROUP']:
                alignak_cfg[path] = os.path.join(
                    config.install_dir, alignak_cfg[path].strip("/")
                )

    print("\n"
          "===================================================="
          "====================================================")
    print("Alignak installation directory: %s" % config.install_dir)
    print("===================================================="
          "====================================================\n")

    print("===================================================="
          "====================================================")
    print("Alignak main configuration directories: ")
    for path in alignak_cfg:
        if path not in ['USER', 'GROUP']:
            print(" %s = %s" % (path, alignak_cfg[path]))
    print("===================================================="
          "====================================================\n")

    print("===================================================="
          "====================================================")
    print("Alignak main configuration parameters: ")
    for path in alignak_cfg:
        if path in ['USER', 'GROUP']:
            print(" %s = %s" % (path, alignak_cfg[path]))
    print("===================================================="
          "====================================================\n")

    """
    Update monitoring objects configuration files
     - get all .cfg files in the etc/alignak folder
     - update the $LOG$=, $ETC$=,... macros with the real installation paths
    """
    pattern = "|".join(alignak_cfg.keys())
    # Search from start of line something like $ETC$=qsdqsdqsd
    changing_path = re.compile(r"^\$(%s)\$ *= *" % pattern)

    folder = os.path.join(alignak_cfg["ETC"])
    for root, dirs, files in os.walk(folder):
        for r_file in files:
            if not re.search(r"\.cfg$", r_file):
                continue

            # Handle resource paths file
            updated_file = os.path.join(root, r_file)
            print("Updating file: %s..." % updated_file)
            for line in fileinput.input(updated_file, inplace=True):
                line = line.strip()
                got_path = changing_path.match(line)
                if got_path:
                    print("$%s$=%s" % (got_path.group(1), alignak_cfg[got_path.group(1)]))
                else:
                    print(line)

    """
    Update alignak configuration file
     - get alignak.ini
     - update the LOG=, ETC=,... variables with the real installation paths
    """
    pattern = "|".join(alignak_cfg.keys())
    # Search from start of line something like ETC=qsdqsdqsd
    changing_path = re.compile(r"^(%s) *= *" % pattern)

    folder = os.path.join(alignak_cfg["ETC"])
    for root, dirs, files in os.walk(folder):
        for r_file in files:
            if not re.search(r"\.ini$", r_file):
                continue

            # Handle resource paths file
            updated_file = os.path.join(root, r_file)
            print("Updating file: %s..." % updated_file)
            for line in fileinput.input(updated_file, inplace=True):
                line = line.strip()
                got_path = changing_path.match(line)
                if got_path:
                    print("%s=%s" % (got_path.group(1), alignak_cfg[got_path.group(1)]))
                else:
                    print(line)

    """
    Update daemons configuration files
     - get all .ini files in the arbiter/daemons folder
     - update the LOG=, ETC=,... variables with the real installation paths
     - update the workdir, logdir and etcdir variables with the real installation paths
    """
    alignak_cfg.update({
        'workdir': alignak_cfg['RUN'],
        'logdir': alignak_cfg['LOG'],
        'etcdir': alignak_cfg['ETC']
    })
    pattern = "|".join(alignak_cfg.keys())
    changing_path = re.compile("^(%s) *= *" % pattern)

    folder = os.path.join(alignak_cfg["ETC"])
    for root, dirs, files in os.walk(folder):
        for r_file in files:
            if not re.search(r"\.ini$", r_file):
                continue

            # Handle resource paths file
            updated_file = os.path.join(root, r_file)
            print("Updating file: %s..." % updated_file)
            for line in fileinput.input(updated_file, inplace=True):
                line = line.strip()
                got_path = changing_path.match(line)
                if got_path:
                    print("%s=%s" % (got_path.group(1), alignak_cfg[got_path.group(1)]))
                else:
                    print(line)

    # Alignak configuration root directory
    alignak_etc = alignak_cfg["ETC"]

    # Add ENV vars only if we are in virtualenv
    # in order to get init scripts working
    if 'VIRTUAL_ENV' in os.environ:
        activate_file = os.path.join(os.environ.get("VIRTUAL_ENV"), 'bin', 'activate')
        try:
            afd = open(activate_file, 'r+')
        except Exception as exp:
            print(exp)
            raise Exception("Virtual environment error")

        env_config = ("""export PYTHON_EGG_CACHE=.\n"""
                      """export ALIGNAK_DEFAULT_FILE=%s/etc/default/alignak\n"""
                      % os.environ.get("VIRTUAL_ENV"))
        alignak_etc = "%s/etc/alignak" % os.environ.get("VIRTUAL_ENV")

        if afd.read().find(env_config) == -1:
            afd.write(env_config)
            print(
                "\n"
                "================================================================================\n"
                "==                                                                            ==\n"
                "==  You need to REsource env/bin/activate in order to set appropriate         ==\n"
                "== variables to use init scripts                                              ==\n"
                "==                                                                            ==\n"
                "================================================================================\n"
            )

    print("\n"
          "================================================================================\n"
          "==\n"
          "==  The installation succeded.\n"
          "==\n"
          "== -------------------------------------------------------------------------- ==\n"
          "==\n"
          "== You can run Alignak with the scripts located in the dev folder.\n"
          "==\n"
          "== The default installed configuration is located here:\n"
          "==   %s\n"
          "==\n"
          "== You will find more information about Alignak configuration here:\n"
          "==   http://alignak-doc.readthedocs.io/en/latest/04_configuration/index.html\n"
          "==\n"
          "== -------------------------------------------------------------------------- ==\n"
          "==\n"
          "== You should grant the write permissions on the configuration directory to \n"
          "== the user alignak:\n"
          "==   find %s -type f -exec chmod 664 {} +\n"
          "==   find %s -type d -exec chmod 775 {} +\n"
          "==\n"
          "== You should also grant ownership on those directories to the user alignak:\n"
          "==   chown -R alignak:alignak %s\n"
          "==   chown -R alignak:alignak %s\n"
          "==   chown -R alignak:alignak %s\n"
          "==\n"
          "== -------------------------------------------------------------------------- ==\n"
          "==\n"
          "== Please note that installing Alignak with the setup.py script is not the \n"
          "== recommended way for a production installation. You'd rather use the "
          "== packaging built for your OS distribution that you can find here:\n"
          "==   http://alignak-monitoring.github.io/download/\n"
          "==\n"
          "================================================================================\n"
          % (alignak_etc, alignak_etc, alignak_etc,
             alignak_cfg["RUN"], alignak_cfg["LOG"], alignak_cfg["VAR"])
          )

    # Check Alignak recommended user existence
    if not user_exists('alignak'):
        print(
            "\n"
            "================================================================================\n"
            "==                                                                            ==\n"
            "== The user account 'alignak' does not exist on your system.                  ==\n"
            "==                                                                            ==\n"
            "================================================================================\n"
        )

    if not group_exists('alignak'):
        print(
            "\n"
            "================================================================================\n"
            "==                                                                            ==\n"
            "== The user group 'alignak' does not exist on your system.                    ==\n"
            "==                                                                            ==\n"
            "================================================================================\n"
        )
