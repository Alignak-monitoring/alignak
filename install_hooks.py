#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
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
        pass
    elif 'linux' in sys.platform or 'sunos5' in sys.platform:
        data_files = data_files + "\netc/init.d = bin/init.d/*"
        data_files = data_files + "\netc/default = bin/default/alignak.in"
    elif 'bsd' in sys.platform or 'dragonfly' in sys.platform:
        data_files = data_files + "\netc/rc.d = bin/rc.d/*"
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
    default_paths = {
        'workdir': '/var/run/alignak',
        'logdir': '/var/log/alignak',
        # TODO: confirm is is unuseful...
        'modules_dir': '/var/lib/alignak/modules',
        'plugins_dir': '/var/libexec/alignak',

        'lock_file': '/var/run/alignak/arbiterd.pid',
        'local_log': '/var/log/alignak/arbiterd.log',
        'pidfile': '/var/run/alignak/arbiterd.pid',

        'pack_distribution_file': '/var/lib/alignak/pack_distribution.dat'
    }

    default_macros = {
        'LOGSDIR': '/var/log/alignak',
        'PLUGINSDIR': '/var/libexec/alignak',
    }

    default_ssl = {
        'ca_cert': '/etc/alignak/certs/ca.pem',
        'server_cert': '/etc/alignak/certs/server.cert',
        'server_key': '/etc/alignak/certs/server.key',
    }

    # Changing default user/group if root
    default_users = {}
    if getpass.getuser() == 'root':
        default_users['alignak_user'] = 'alignak'
        default_users['alignak_group'] = 'alignak'
        default_users['user'] = 'alignak'
        default_users['group'] = 'alignak'
        default_users['ALIGNAKUSER'] = 'alignak'
        default_users['ALIGNAKGROUP'] = 'alignak'
        default_users['HOME'] = '`getent passwd "$ALIGNAKUSER" | cut -d: -f 6`'

    # Prepare pattern for alignak.cfg
    pattern = "|".join(default_paths.keys())
    changing_path = re.compile("^(%s) *= *" % pattern)
    pattern = "|".join(default_users.keys())
    changing_user = re.compile("^#(%s) *= *" % pattern)
    pattern = "|".join(default_ssl.keys())
    changing_ssl = re.compile("^#(%s) *= *" % pattern)
    pattern = "|".join(default_macros.keys())
    changing_mac = re.compile(r"^\$(%s)\$ *= *" % pattern)

    # Fix resource paths
    alignak_file = os.path.join(
        config.install_dir, "etc", "alignak", "arbiter", "resource.d", "paths.cfg"
    )
    if not os.path.exists(alignak_file):
        print(
            "\n"
            "================================================================================\n"
            "==  The configuration file '%s' is missing.                                   ==\n"
            "================================================================================\n"
            % alignak_file
        )

    for line in fileinput.input(alignak_file, inplace=True):
        line = line.strip()
        mac_attr_name = changing_mac.match(line)
        if mac_attr_name:
            new_path = os.path.join(config.install_dir,
                                    default_macros[mac_attr_name.group(1)].strip("/"))
            print("$%s$=%s" % (mac_attr_name.group(1),
                             new_path))
        else:
            print(line)

    # Fix alignak.cfg
    alignak_file = os.path.join(config.install_dir, "etc", "alignak", "alignak.cfg")
    if not os.path.exists(alignak_file):
        print(
            "\n"
            "================================================================================\n"
            "==  The configuration file '%s' is missing.                                   ==\n"
            "================================================================================\n"
            % alignak_file
        )

    for line in fileinput.input(alignak_file, inplace=True):
        line = line.strip()
        path_attr_name = changing_path.match(line)
        user_attr_name = changing_user.match(line)
        ssl_attr_name = changing_ssl.match(line)
        if path_attr_name:
            new_path = os.path.join(config.install_dir,
                                    default_paths[path_attr_name.group(1)].strip("/"))
            print("%s=%s" % (path_attr_name.group(1),
                             new_path))
        elif user_attr_name:
            print("#%s=%s" % (user_attr_name.group(1),
                             default_users[user_attr_name.group(1)]))
        elif ssl_attr_name:
            new_path = os.path.join(config.install_dir,
                                    default_ssl[ssl_attr_name.group(1)].strip("/"))
            print("#%s=%s" % (ssl_attr_name.group(1),
                             new_path))
        else:
            print(line)

    # Handle daemons ini files
    for ini_file in ["arbiterd.ini", "brokerd.ini", "schedulerd.ini",
                     "pollerd.ini", "reactionnerd.ini", "receiverd.ini"]:
        # Prepare pattern for ini files
        daemon_name = ini_file.replace(".ini", "")
        default_paths['lock_file'] = '/var/run/alignak/%s.pid' % daemon_name
        default_paths['local_log'] = '/var/log/alignak/%s.log' % daemon_name
        default_paths['pidfile'] = '/var/run/alignak/%s.pid' % daemon_name
        pattern = "|".join(default_paths.keys())
        changing_path = re.compile("^(%s) *= *" % pattern)

        # Fix ini file
        alignak_file = os.path.join(config.install_dir, "etc", "alignak", "daemons", ini_file)
        if not os.path.exists(alignak_file):
            print(
                "\n"
                "================================================================================\n"
                "==  The configuration file '%s' is missing.                                   ==\n"
                "================================================================================\n"
                % alignak_file
            )

        for line in fileinput.input(alignak_file, inplace=True):
            line = line.strip()
            path_attr_name = changing_path.match(line)
            user_attr_name = changing_user.match(line)
            ssl_attr_name = changing_ssl.match(line)
            if path_attr_name:
                new_path = os.path.join(config.install_dir,
                                        default_paths[path_attr_name.group(1)].strip("/"))
                print("%s=%s" % (path_attr_name.group(1),
                                 new_path))
            elif user_attr_name:
                print("#%s=%s" % (user_attr_name.group(1),
                                 default_users[user_attr_name.group(1)]))
            elif ssl_attr_name:
                new_path = os.path.join(config.install_dir,
                                        default_ssl[ssl_attr_name.group(1)].strip("/"))
                print("#%s=%s" % (ssl_attr_name.group(1),
                                 new_path))
            else:
                print(line)

    # Handle default/alignak
    if 'linux' in sys.platform or 'sunos5' in sys.platform:
        old_name = os.path.join(config.install_dir, "etc", "default", "alignak.in")
        if not os.path.exists(old_name):
            print("\n"
                  "=======================================================================================================\n"
                  "==  The configuration file '%s' is missing.\n"
                  "=======================================================================================================\n"
                  % alignak_file)

        new_name = os.path.join(config.install_dir, "etc", "default", "alignak")
        try:
            os.rename(old_name, new_name)
        except OSError as e:
            print("\n"
                  "=======================================================================================================\n"
                  "==  The configuration file '%s' could not be renamed to '%s'.\n"
                  "==  The newly installed configuration will not be up-to-date.\n"
                  "=======================================================================================================\n"
                  % (old_name, new_name))

        default_paths = {
            'ETC': '/etc/alignak',
            'VAR': '/var/lib/alignak',
            'BIN': '/bin',
            'RUN': '/var/run/alignak',
            'LOG': '/var/log/alignak',
            'LIB': '/var/libexec/alignak',
        }
        pattern = "|".join(default_paths.keys())
        changing_path = re.compile("^(%s) *= *" % pattern)
        for line in fileinput.input(new_name,  inplace=True):
            line = line.strip()
            path_attr_name = changing_path.match(line)
            user_attr_name = changing_user.match(line)
            if path_attr_name:
                new_path = os.path.join(config.install_dir,
                                        default_paths[path_attr_name.group(1)].strip("/"))
                print("%s=%s" % (path_attr_name.group(1),
                                 new_path))
            elif user_attr_name:
                print("#%s=%s" % (user_attr_name.group(1),
                                 default_users[user_attr_name.group(1)]))

            else:
                print(line)

    # Alignak run script
    alignak_run = ''
    if 'win' in sys.platform:
        pass
    elif 'linux' in sys.platform or 'sunos5' in sys.platform:
        alignak_run = os.path.join(config.install_dir, "etc", "init.d", "alignak start")
    elif 'bsd' in sys.platform or 'dragonfly' in sys.platform:
        alignak_run = os.path.join(config.install_dir, "etc", "rc.d", "alignak start")

    # Alignak configuration root directory
    alignak_etc = os.path.join(config.install_dir, "etc", "alignak")

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
          "==   chown -R alignak:alignak /usr/local/var/run/alignak                      ==\n"
          "==   chown -R alignak:alignak /usr/local/var/log/alignak                      ==\n"
          "==   chown -R alignak:alignak /usr/local/var/libexec/alignak                  ==\n"
          "==                                                                            ==\n"
          "== -------------------------------------------------------------------------- ==\n"
          "==                                                                            ==\n"
          "== Please note that installing Alignak with the setup.py script is not the    ==\n"
          "== recommended way. You'd rather use the packaging built for your OS          ==\n"
          "== distribution that you can find here:                                       ==\n"
          "==   http://alignak-monitoring.github.io/download/                            ==\n"
          "==                                                                            ==\n"
          "================================================================================\n"
          % (alignak_run, alignak_etc, alignak_etc, alignak_etc)
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
