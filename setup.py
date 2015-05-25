#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys
import re
try:
    import pwd
    import grp
except ImportError:
    # don't expect to have this on windows :)
    pwd = grp = None
import fileinput
import stat

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...

try:
    from setuptools import setup
    from setuptools import find_packages
except:
    sys.exit("Error: missing python-setuptools library")
    
from itertools import chain
import optparse
import itertools
from glob import glob

from distutils.dir_util import mkpath

try:
    python_version = sys.version_info
except:
    python_version = (1, 5)
if python_version < (2, 6):
    sys.exit("Alignak require as a minimum Python 2.6.x, sorry")
elif python_version >= (3,):
    sys.exit("Alignak is not yet compatible with Python3k, sorry")



package_data = ['*.py', 'modules/*.py', 'modules/*/*.py']

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def ensure_dir_exist(f):
    dirname = os.path.dirname(f)
    if not os.path.exists(dirname):
        os.makedirs(dirname)


def generate_default_alignak_file():
    # The default file must have good values for the directories:
    # etc, var and where to push scripts that launch the app.
    templatefile = "bin/default/alignak.in"
    build_base = 'build'
    outfile = os.path.join(build_base, "bin/default/alignak")

    #print('generating %s from %s', outfile, templatefile)

    mkpath(os.path.dirname(outfile))
    
    bin_path = default_paths['bin']

    # Read the template file
    f = open(templatefile)
    buf = f.read()
    f.close
    # substitute
    buf = buf.replace("$ETC$", default_paths['etc'])
    buf = buf.replace("$VAR$", default_paths['var'])
    buf = buf.replace("$RUN$", default_paths['run'])
    buf = buf.replace("$LOG$", default_paths['log'])
    buf = buf.replace("$SCRIPTS_BIN$", bin_path)
    # write out the new file
    f = open(outfile, "w")
    f.write(buf)
    f.close()


def update_file_with_string(infilename, outfilename, matches, new_strings):
    f = open(infilename)
    buf = f.read()
    f.close()
    for match, new_string in zip(matches, new_strings):
        buf = re.sub(match, new_string, buf)
    f = open(outfilename, "w")
    f.write(buf)
    f.close()


def append_file_with(infilename, outfilename, append_string):
    f = open(infilename)
    buf = f.read()
    f.close()
    ensure_dir_exist(outfilename)
    f = open(outfilename, "w")
    f.write(buf)
    f.write('\n')
    f.write(append_string)
    f.close()


def recursive_chown(path, uid, gid, owner, group):
    print("Changing owner of %s to %s:%s" % (path, owner, group))
    os.chown(path, uid, gid)
    if os.path.isdir(path):
        for dirname, dirs, files in os.walk(path):
            for path in itertools.chain(dirs, files):
                path = os.path.join(dirname, path)
                os.chown(path, uid, gid)


            
def get_uid(user_name):
    try:
        return pwd.getpwnam(user_name)[2]
    except KeyError, exp:
        return None
    

def get_gid(group_name):
    try:
        return grp.getgrnam(group_name)[2]
    except KeyError, exp:
        return None


# Do a chmod -R +x
def _chmodplusx(d):
    if not os.path.exists(d):
        print "warn: _chmodplusx missing dir", d
        return
    if os.path.isdir(d):
        for item in os.listdir(d):
            p = os.path.join(d, item)
            if os.path.isdir(p):
                _chmodplusx(p)
            else:
                st = os.stat(p)
                os.chmod(p, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    else:
        st = os.stat(d)
        os.chmod(d, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


parser = optparse.OptionParser(
    "%prog [options]", version="%prog ")
parser.add_option('--root',
                  dest="proot", metavar="ROOT",
                  help='Root dir to install, usefull only for packagers')
parser.add_option('--upgrade', '--update',
                  dest="upgrade", action='store_true',
                  help='Only upgrade')
parser.add_option('--owner',
                  dest="owner", metavar="OWNER",
                  help='User to install with, default alignak')
parser.add_option('--group',
                  dest="group", metavar="GROUP",
                  help='Group to install with, default alignak')
parser.add_option('--install-scripts',
                  dest="install_scripts",
                  help='Path to install the alignak-* scripts')
parser.add_option('--skip-build',
                  dest="skip_build", action='store_true',
                  help='skipping build')
parser.add_option('-O', type="int",
                  dest="optimize",
                  help='skipping build')
parser.add_option('--record',
                  dest="record",
                  help='File to save writing files. Used by pip install only')
parser.add_option('--single-version-externally-managed',
                  dest="single_version", action='store_true',
                  help='I really dont know, this option is for pip only')


old_error = parser.error
def _error (msg):
    print 'Parser error', msg
parser.error = _error
opts, args = parser.parse_args()
# reenable the errors for later use
parser.error = old_error

root = opts.proot or ''

# We try to see if we are in a full install or an update process
is_update = False
# Try to import shinekn but not the local one. If avialable, we are in 
# and upgrade phase, not a classic install
try:
    if '.' in sys.path:
        sys.path.remove('.')
    if os.path.abspath('.') in sys.path:
        sys.path.remove(os.path.abspath('.'))
    if '' in sys.path:
        sys.path.remove('')
    import alignak
    is_update = True
    print "Previous Alignak lib detected (%s)" % alignak.__file__
except ImportError:
    pass

if '--update' in args or opts.upgrade or '--upgrade' in args:
    print "Alignak Lib Updating process only"
    if 'update' in args:
        sys.argv.remove('update')
        sys.argv.insert(1, 'install')
    if '--update' in args:
        sys.argv.remove('--update')
    if '--upgrade' in args:
        sys.argv.remove('--upgrade')
    
    print "Alignak Lib Updating process only"
    is_update = True


is_install = False
if 'install' in args:
    is_install = True


install_scripts = opts.install_scripts or ''

user = opts.owner or 'alignak'
group = opts.group or 'alignak'

# Maybe the user is unknown, but we are in a "classic" install, if so, bail out
if is_install and not root and not is_update and pwd and not opts.skip_build:
    uid = get_uid(user)
    gid = get_gid(group)

    if uid is None or gid is None:
        print "Error: the user/group %s/%s is unknown. Please create it first 'useradd %s'" % (user,group, user)
        sys.exit(2)
    
    

# setup() will warn about unknown parameter we already managed
# to delete them
deleting_args = ['--owner', '--group', '--skip-build']

to_del = []
for a in deleting_args:
    for av in sys.argv:
        if av.startswith(a):
            idx = sys.argv.index(av)
            print "AV,", av, "IDX", idx
            to_del.append(idx)
            # We can have --owner=alignak or --owner alignak, if so del also the
            # next one
            if '=' not in av:
                to_del.append(idx + 1)

to_del.sort()
to_del.reverse()
for idx in to_del:
    sys.argv.pop(idx)



# compute scripts
scripts = [ s for s in glob('bin/alignak*') if not s.endswith('.py')]

# Define files
if 'win' in sys.platform:
    default_paths = {
        'bin':      install_scripts or "c:\\alignak\\bin",
        'var':      "c:\\alignak\\var",
        'share':    "c:\\alignak\\var\\share",
        'etc':      "c:\\alignak\\etc",
        'log':      "c:\\alignak\\var",
        'run':      "c:\\alignak\\var",
        'libexec':  "c:\\alignak\\libexec",
        }
    data_files = []
elif 'linux' in sys.platform or 'sunos5' in sys.platform:
    default_paths = {
        'bin':     install_scripts or "/usr/bin",
        'var':     "/var/lib/alignak/",
        'share':   "/var/lib/alignak/share",
        'etc':     "/etc/alignak",
        'run':     "/var/run/alignak",
        'log':     "/var/log/alignak",
        'libexec': "/var/lib/alignak/libexec",
        }
    data_files = [
        (
            os.path.join('/etc', 'init.d'),
            ['bin/init.d/alignak',
             'bin/init.d/alignak-arbiter',
             'bin/init.d/alignak-broker',
             'bin/init.d/alignak-receiver',
             'bin/init.d/alignak-poller',
             'bin/init.d/alignak-reactionner',
             'bin/init.d/alignak-scheduler',
             ]
            )
        ]

    if is_install:
        # warning: The default file will be generated a bit later
        data_files.append(
            (os.path.join('/etc', 'default',),
             ['build/bin/default/alignak']
             ))
elif 'bsd' in sys.platform or 'dragonfly' in sys.platform:
    default_paths = {
        'bin':     install_scripts or "/usr/local/bin",
        'var':     "/usr/local/libexec/alignak",
        'share':   "/usr/local/share/alignak",
        'etc':     "/usr/local/etc/alignak",
        'run':     "/var/run/alignak",
        'log':     "/var/log/alignak",
        'libexec': "/usr/local/libexec/alignak/plugins",
                     }
    data_files = [
        (
            '/usr/local/etc/rc.d',
            ['bin/rc.d/alignak-arbiter',
             'bin/rc.d/alignak-broker',
             'bin/rc.d/alignak-receiver',
             'bin/rc.d/alignak-poller',
             'bin/rc.d/alignak-reactionner',
             'bin/rc.d/alignak-scheduler',
             ]
            )
        ]
else:
    raise "Unsupported platform, sorry"
    data_files = []

# Change paths if need
#if root:
#    for (k,v) in default_paths.iteritems():
#        default_paths[k] = os.path.join(root, v[1:])


# Beware to install scripts in the bin dir
data_files.append( (default_paths['bin'], scripts) )
# Only some platform are managed by the init.d scripts
if is_install and ('linux' in sys.platform or 'sunos5' in sys.platform):
    generate_default_alignak_file()


if not is_update:
    ## get all files + under-files in etc/ except daemons folder
    daemonsini = []
    for path, subdirs, files in os.walk('etc'):
        if len(files) == 0:
            data_files.append( (os.path.join(default_paths['etc'], re.sub(r"^(etc\/|etc$)", "", path)), []) )
        for name in files:
            if name == 'alignak.cfg':
                continue
            if 'daemons' in path:
                daemonsini.append(os.path.join(path, name))
            else:
                data_files.append( (os.path.join(default_paths['etc'], re.sub(r"^(etc\/|etc$)", "", path)), 
                                    [os.path.join(path, name)]) )

if os.name != 'nt' and not is_update:
    for _file in daemonsini:
        inifile = _file
        outname = os.path.join('build', _file)
        # force the user setting as it's not set by default
        append_file_with(inifile, outname, "modules_dir=%s\nuser=%s\ngroup=%s\n" % (
                os.path.join(default_paths['var'], 'modules'),
                user, group))
        data_files.append( (os.path.join(default_paths['etc'], 'daemons'),
                            [outname]) )

    # And update the alignak.cfg file for all /usr/local/alignak/var
    # value with good one
    for name in ['alignak.cfg']:
        inname = os.path.join('etc', name)
        outname = os.path.join('build', name)
        print('updating path in %s', outname)
        
        ## but we HAVE to set the alignak_user & alignak_group to thoses requested:
        update_file_with_string(inname, outname,
                                ["alignak_user=\w+", "alignak_group=\w+", "workdir=.+", "lock_file=.+", "local_log=.+", "modules_dir=.+", "pack_distribution_file=.+"],
                                ["alignak_user=%s" % user,
                                 "alignak_group=%s" % group,
                                 "workdir=%s" % default_paths['var'],
                                 "lock_file=%s/arbiterd.pid" % default_paths['run'],
                                 "local_log=%s/arbiterd.log" % default_paths['log'],
                                "modules_dir=%s" % os.path.join(default_paths['var'], 'modules'),
                                "pack_distribution_file=%s" % os.path.join(default_paths['var'], 'pack_distribution.dat')],
                                )
        data_files.append( (default_paths['etc'], [outname]) )



# Modules, doc, inventory and cli are always installed
paths = ('modules', 'doc', 'inventory', 'cli')
for path, subdirs, files in chain.from_iterable(os.walk(patho) for patho in paths):
    for name in files:
        data_files.append( (os.path.join(default_paths['var'], path), [os.path.join(path, name)]))
	
for path, subdirs, files in os.walk('share'):
    for name in files:
        data_files.append( (os.path.join(default_paths['share'], re.sub(r"^(share\/|share$)", "", path)), 
                            [os.path.join(path, name)]) )

for path, subdirs, files in os.walk('libexec'):
    for name in files:
        data_files.append( (os.path.join(default_paths['libexec'], re.sub(r"^(libexec\/|libexec$)", "", path)), 
                            [os.path.join(path, name)]) )

data_files.append( (default_paths['run'], []) )
data_files.append( (default_paths['log'], []) )


# Note: we do not add the "scripts" entry in the setup phase because we need to generate the 
# default/alignak file with the bin path before run the setup phase, and it's not so
# easy to do in a clean and easy way

not_allowed_options = ['--upgrade', '--update']
for o in not_allowed_options:
    if o in sys.argv:
        sys.argv.remove(o)

required_pkgs = []
setup(
    name="Alignak",
    version="2.4",
    packages=find_packages(),
    package_data={'': package_data},
    description="Alignak is a monitoring framework compatible with Nagios and Shinken configuration and plugins",
    long_description=read('README.rst'),
    author="Gabes Jean",
    author_email="naparuba@gmail.com",
    license="GNU Affero General Public License",
    url="http://www.github.com/Alignak-monitoring",
    zip_safe=False,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Networking :: Monitoring',
    ],
    install_requires=[
        required_pkgs
        ],

    extras_require={
        'setproctitle': ['setproctitle']
        },

    data_files = data_files,
)


# if root is set, it's for package, so NO chown
if pwd and not root and is_install:
    # assume a posix system
    uid = get_uid(user)
    gid = get_gid(group)

    if uid is not None and gid is not None:
        # recursivly changing permissions for etc/alignak and var/lib/alignak
        for c in ['etc', 'run', 'log', 'var', 'libexec']:
            p = default_paths[c]
            recursive_chown(p, uid, gid, user, group)
        # Also change the rights of the alignak- scripts
        for s in scripts:
            bs = os.path.basename(s)
            recursive_chown(os.path.join(default_paths['bin'], bs), uid, gid, user, group)
            _chmodplusx( os.path.join(default_paths['bin'], bs) )
        _chmodplusx(default_paths['libexec'])

    # If not exists, won't raise an error there
    _chmodplusx('/etc/init.d/alignak')
    for d in ['scheduler', 'broker', 'receiver', 'reactionner', 'poller', 'arbiter']:
        _chmodplusx('/etc/init.d/alignak-'+d)

try:
    import pycurl
except ImportError:
    print "Warning: missing python-pycurl lib, you MUST install it before launch the alignak daemons"

try:
    import cherrypy
except ImportError:
    print "Notice: for better performances for the daemons communication, you should install the python-cherrypy3 lib"

print "Alignak setup done"
