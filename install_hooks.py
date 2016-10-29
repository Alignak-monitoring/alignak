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
    data_files = config['files']['data_files']
    if 'win' in sys.platform:
        raise Exception("Not yet Windows ready, sorry. For more information, "
                        "see: https://github.com/Alignak-monitoring/alignak/issues/522")
    elif 'linux' in sys.platform or 'sunos5' in sys.platform:
        data_files = data_files + "\nalignak/bin/etc/init.d = bin/init.d/*"
        data_files = data_files + "\nalignak/bin/etc/default = bin/default/alignak.in"
    elif 'bsd' in sys.platform or 'dragonfly' in sys.platform:
        data_files = data_files + "\nalignak/bin/etc/rc.d = bin/rc.d/*"
        data_files = data_files + "\nalignak/bin/etc/default = bin/default/alignak.in"
    else:
        raise Exception("Unsupported platform, sorry")

    config['files']['data_files'] = data_files

    for line in config['files']['data_files'].split('\n'):
        line = line.strip().split('=')
        print("Installable directories/files: %s" % line)


def fix_alignak_cfg(config):
    """
    Fix paths, user and group in alignak.cfg and daemons/*.ini
    Called one all files are copied.

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
        'ETC': '/alignak/etc',
        'RUN': '/alignak/run',
        'LOG': '/alignak/log',
        'INIT': '/alignak/bin',
        'LIBEXEC': '/alignak/libexec',
        'PLUGINSDIR': '/alignak/libexec'
    }
    pattern = "|".join(alignak_cfg.keys())
    # Search from start of line something like ETC=qsdqsdqsd
    changing_path = re.compile("^(%s) *= *" % pattern)

    # Handle main Alignak configuration file (eg. /etc/default/alignak)
    old_name = os.path.join(config.install_dir, "alignak", "alignak.in")

    for line in fileinput.input(old_name, inplace=True):
        line = line.strip()
        got_path = changing_path.match(line)
        if got_path:
            found = got_path.group(1)
            alignak_cfg[found] = os.path.join(
                config.install_dir, alignak_cfg[found].strip("/")
            )
            print("%s=%s" % (got_path.group(1), alignak_cfg[found]))
        else:
            print(line)

    new_name1 = os.path.join(config.install_dir, "alignak", "alignak")
    new_name2 = os.path.join(config.install_dir, "alignak", "bin", "etc", "default", "alignak")
    shutil.copy(old_name, new_name1)
    shutil.move(old_name, new_name2)

    print("\n"
          "===================================================="
          "====================================================")
    print("Alignak installation directory: %s" % config.install_dir)
    print("===================================================="
          "====================================================\n")

    print("\n"
          "===================================================="
          "====================================================")
    print("Alignak main configuration directories: ")
    for path in alignak_cfg:
        print(" %s = %s" % (path, alignak_cfg[path]))
    print("===================================================="
          "====================================================\n")

    """
    Update resource files
     - get all .cfg files in the /usr/local/etc/alignak/arbiter/resource.d folder
     - update the $LOG$=, $ETC$=,... macros with the real installation paths
    """
    pattern = "|".join(alignak_cfg.keys())
    # Search from start of line something like ETC=qsdqsdqsd
    changing_path = re.compile("^(%s) *= *" % pattern)

    resource_folder = os.path.join(alignak_cfg["ETC"], "arbiter", "resource.d")
    for _, _, files in os.walk(resource_folder):
        for r_file in files:
            if not re.search(r"\.cfg$", r_file):
                continue

            # Handle resource paths file
            resource_file = os.path.join(resource_folder, r_file)
            for line in fileinput.input(resource_file, inplace=True):
                line = line.strip()
                got_path = changing_path.match(line)
                if got_path:
                    print("%s=%s" % (got_path.group(1), alignak_cfg[got_path.group(1)]))
                else:
                    print(line)

    """
    Update daemons configuration files
     - get all .ini files in the /usr/local/etc/alignak/arbiter/resource.d folder
     - update the $LOGSDIR$, $ETCDIR$ and $PLUGINSDIR$ macros with the real installation paths
    """
    default_paths = {
        'workdir': 'RUN',
        'logdir': 'LOG',
        'etcdir': 'ETC',
        'pluginsdir': 'LIBEXEC'
    }
    pattern = "|".join(default_paths.keys())
    changing_path = re.compile("^(%s) *= *" % pattern)

    daemons_folder = os.path.join(alignak_cfg["ETC"], "daemons")
    for _, _, files in os.walk(daemons_folder):
        for d_file in files:
            if not re.search(r"\.ini", d_file):
                continue

            # Handle daemon configuration file
            daemon_file = os.path.join(daemons_folder, d_file)
            for line in fileinput.input(daemon_file, inplace=True):
                line = line.strip()
                got_path = changing_path.match(line)
                if got_path:
                    print("%s=%s" % (got_path.group(1), alignak_cfg[default_paths[got_path.group(1)]]))
                else:
                    print(line)

    """
    Get default run scripts and configuration location
    """
    # Alignak run script
    alignak_run = ''
    if 'win' in sys.platform:
        raise Exception("Not yet Windows ready, sorry. For more information, "
                        "see: https://github.com/Alignak-monitoring/alignak/issues/522")
    elif 'linux' in sys.platform or 'sunos5' in sys.platform:
        alignak_run = os.path.join(config.install_dir,
                                   "alignak", "bin", "etc", "init.d", "alignak start")
    elif 'bsd' in sys.platform or 'dragonfly' in sys.platform:
        alignak_run = os.path.join(config.install_dir,
                                   "alignak", "bin", "etc", "rc.d", "alignak start")

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
        alignak_run = "%s/etc/init.d alignak start" % os.environ.get("VIRTUAL_ENV")

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
          "==                                                                            ==\n"
          "==  The installation succeded.                                                ==\n"
          "==                                                                            ==\n"
          "== -------------------------------------------------------------------------- ==\n"
          "==                                                                            ==\n"
          "== You can run Alignak with:                                                  ==\n"
          "==   %s\n"
          "==                                                                            ==\n"
          "== The default installed configuration is located here:                       ==\n"
          "==   %s\n"
          "==                                                                            ==\n"
          "== You will find more information about Alignak configuration here:           ==\n"
          "==   http://alignak-doc.readthedocs.io/en/latest/04_configuration/index.html  ==\n"
          "==                                                                            ==\n"
          "== -------------------------------------------------------------------------- ==\n"
          "==                                                                            ==\n"
          "== You should grant the write permissions on the configuration directory to   ==\n"
          "== the user alignak:                                                          ==\n"
          "==   find %s -type f -exec chmod 664 {} +\n"
          "==   find %s -type d -exec chmod 775 {} +\n"
          "== -------------------------------------------------------------------------- ==\n"
          "==                                                                            ==\n"
          "== You should also grant ownership on those directories to the user alignak:  ==\n"
          "==   chown -R alignak:alignak %s\n"
          "==   chown -R alignak:alignak %s\n"
          "==   chown -R alignak:alignak %s\n"
          "==                                                                            ==\n"
          "== -------------------------------------------------------------------------- ==\n"
          "==                                                                            ==\n"
          "== Please note that installing Alignak with the setup.py script is not the    ==\n"
          "== recommended way. You'd rather use the packaging built for your OS          ==\n"
          "== distribution that you can find here:                                       ==\n"
          "==   http://alignak-monitoring.github.io/download/                            ==\n"
          "==                                                                            ==\n"
          "================================================================================\n"
          % (alignak_run, alignak_etc, alignak_etc, alignak_etc,
             alignak_cfg["RUN"], alignak_cfg["LOG"], alignak_cfg["LIBEXEC"])
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
