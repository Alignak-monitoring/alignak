import os
import sys
import re
import fileinput
import getpass


def get_init_scripts(config):
    """ Add init scripts in data_files for install """
    data_files = config['files']['data_files']
    if 'win' in sys.platform:
        pass
    elif 'linux' in sys.platform or 'sunos5' in sys.platform:
        data_files = data_files + "\netc/init.d = bin/init.d/*"
        data_files = data_files + "\netc/default = bin/default/alignak.in"
    elif 'bsd' in sys.platform or 'dragonfly' in sys.platform:
        data_files = data_files + "\nusr/local/etc/rc.d = bin/rc.d/*"
    else:
        raise "Unsupported platform, sorry"
        data_files = []
    config['files']['data_files'] = data_files


def fix_alignak_cfg(config):
    """ Fix paths, user and group in alignak.cfg and daemons/*.ini """
    default_paths = {
        'lock_file': '/var/run/alignak/arbiterd.pid',
        'local_log': '/var/log/alignak/arbiterd.log',
        'pidfile': '/var/run/alignak/arbiterd.pid',
        'workdir': '/var/run/alignak',
        'pack_distribution_file': '/var/lib/alignak/pack_distribution.dat',
        'modules_dir': '/var/lib/alignak/modules',
        'ca_cert': '/etc/alignak/certs/ca.pem',
        'server_cert': '/etc/alignak/certs/server.cert',
        'server_key': '/etc/alignak/certs/server.key',
        'logdir': '/var/log/alignak',
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
        default_users['HOME'] = '`grep ^$ALIGNAKUSER: /etc/passwd | cut -d: -f 6`'

    # Prepare pattern for alignak.cfg
    pattern = "|".join(default_paths.keys())
    changing_path = re.compile("^(%s) *= *" % pattern)
    pattern = "|".join(default_users.keys())
    changing_user = re.compile("^#(%s) *= *" % pattern)
    # Fix alignak.cfg
    alignak_cfg_path = os.path.join(config.install_dir,
                                    "etc",
                                    "alignak",
                                    "alignak.cfg")

    for line in fileinput.input(alignak_cfg_path, inplace=True):
        line = line.strip()
        path_attr_name = changing_path.match(line)
        user_attr_name = changing_user.match(line)
        if path_attr_name:
            new_path = os.path.join(config.install_dir,
                                    default_paths[path_attr_name.group(1)].strip("/"))
            print("%s=%s" % (path_attr_name.group(1),
                             new_path))
        elif user_attr_name:
            print("%s=%s" % (user_attr_name.group(1),
                             default_users[user_attr_name.group(1)]))
        else:
            print(line)

    # Handle daemons ini files
    for ini_file in ["brokerd.ini", "schedulerd.ini", "pollerd.ini",
                     "reactionnerd.ini", "receiverd.ini"]:
        # Prepare pattern for ini files
        daemon_name = ini_file.strip(".ini")
        default_paths['lock_file'] = '/var/run/alignak/%s.pid' % daemon_name
        default_paths['local_log'] = '/var/log/alignak/%s.log' % daemon_name
        default_paths['pidfile'] = '/var/run/alignak/%s.pid' % daemon_name
        pattern = "|".join(default_paths.keys())
        changing_path = re.compile("^(%s) *= *" % pattern)
        # Fix ini file
        alignak_cfg_path = os.path.join(config.install_dir,
                                        "etc",
                                        "alignak",
                                        "daemons",
                                        ini_file)
        for line in fileinput.input(alignak_cfg_path, inplace=True):
            line = line.strip()
            path_attr_name = changing_path.match(line)
            user_attr_name = changing_user.match(line)
            if path_attr_name:
                new_path = os.path.join(config.install_dir,
                                        default_paths[path_attr_name.group(1)].strip("/"))
                print("%s=%s" % (path_attr_name.group(1),
                                 new_path))
            elif user_attr_name:
                print("%s=%s" % (user_attr_name.group(1),
                                 default_users[user_attr_name.group(1)]))
            else:
                print(line)

    # Handle default/alignak
    if 'linux' in sys.platform or 'sunos5' in sys.platform:
        old_name = os.path.join(config.install_dir, "etc", "default", "alignak.in")
        new_name = os.path.join(config.install_dir, "etc", "default", "alignak")
        os.rename(old_name, new_name)
        default_paths = {
            'ETC': '/etc/alignak',
            'VAR': '/var/lib/alignak',
            'BIN': '/bin',
            'RUN': '/var/run/alignak',
            'LOG': '/var/log/alignak',
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
                print("%s=%s" % (user_attr_name.group(1),
                                 default_users[user_attr_name.group(1)]))

            else:
                print(line)

    # Add ENV vars only if we are in virtualenv
    # in order to get init scripts working
    if 'VIRTUAL_ENV' in os.environ:
        activate_file = os.path.join(os.environ.get("VIRTUAL_ENV"), 'bin', 'activate')
        try:
            afd = open(activate_file, 'r+')
        except Exception as exp:
            print(exp)
        env_config = ("""export PYTHON_EGG_CACHE=.\n"""
                      """export ALIGNAK_DEFAULT_FILE=%s/etc/default/alignak\n"""
                      % os.environ.get("VIRTUAL_ENV"))
        if afd.read().find(env_config) == -1:
            afd.write(env_config)
            print("\n"
                  "=======================================================================================================\n"
                  "==                                                                                                   ==\n"
                  "==  You need to REsource env/bin/activate in order to set appropriate variables to use init scripts  ==\n"
                  "==                                                                                                   ==\n"
                  "=======================================================================================================\n"
                  )

    if getpass.getuser() == 'root':
        print("\n"
              "=======================================================================================================\n"
              "==                                                                                                   ==\n"
              "==  Don't forget to create user and group 'alignak' or change daemons configuration                  ==\n"
              "==                                                                                                   ==\n"
              "=======================================================================================================\n"
              )

