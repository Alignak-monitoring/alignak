#!/usr/bin/env python
#
# Copyright (C) 2009-2011:
#    Denis GERMAIN, dt.germain@gmail.com
#    Gabes Jean, naparuba@gmail.com
#    Gerhard Lausser, Gerhard.Lausser@consol.de
#    Gregory Starck, g.starck@gmail.com
#    Hartmut Goebel, h.goebel@goebel-consult.de
#    David GUENAULT, david.guenault@gmail.com
#
# You should have received a copy of the GNU Affero General Public License
# along with this plugin.  If not, see <http://www.gnu.org/licenses/>.
"""
check_alignak_daemon.py:
    This check is getting daemons state from a arbiter connection.
"""

import os
import socket
from optparse import OptionParser
import requests
from requests import exceptions
import json
import sys

# Exit statuses recognized by Nagios and thus by Shinken/Alignak
OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3

daemon_types = ['arbiter', 'broker', 'scheduler', 'poller', 'reactionner', 'receiver']



def ping(host=None, port=None, proto="http", timeout=1):
    uri = "%s://%s:%s/identity" % (proto, host, port)
    try:
        result = requests.get(uri, timeout=timeout)
        data = json.loads(result.content)
        if 'type' in data and 'name' in data:
            message = {"message": "%s named %s is alive", "status": True}
        else:
            message = {"message": "Invalid response to identity request: %s" % result.text, "status": False}
    except requests.exceptions.ConnectionError:
        message = { "message":"Connection error", "status":False }
    except requests.exceptions.Timeout:
        message = { "message":"Timeout", "status":False }

    return message

def get_status(host=None, port=None, proto="http", daemon_name=None, timeout=1):
    uri = "%s://%s:%s/status" % (proto, host, port)
    try:
        result = requests.get(uri, timeout=timeout).json()
    except requests.exceptions.ConnectionError:
        message = { "message":"Connection error", "status":False }
    except requests.exceptions.HTTPError as exp:
        message = {"message": "HTTP Error: %s" % exp, "status": False}
    except requests.exceptions.Timeout:
        message = { "message":"Timeout", "status":False }
    except Exception as exp:
        message = {"message": "Exception: %s" % exp, "status": False}
    else:
        data = False

        # result['livestate'] is the overal Alignak live state
        # result['services'] is individual daemon status
        for daemon in result['services']:
            if daemon['name'] == daemon_name:
                data = daemon
                break

        if not data:
            message = { "message":"Daemon (%s) not found" % daemon_name, "status":False, "data":data }
        else:
            message = { "message":"OK", "status":True, "data":data }

    return message



if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option('-a', '--hostnames', dest='hostnames', default='127.0.0.1')
    parser.add_option('-p', '--portnumber', dest='portnum', default=7770, type=int)
    parser.add_option('-s', '--ssl', action="store_true", dest='ssl', default=False)
    parser.add_option('-t', '--target', dest='target',default='',type=str)
    parser.add_option('-T', '--timeout', dest='timeout', default=1, type=float)


    # Retrieving options
    options, args = parser.parse_args()
    options.helpme = False

    if options.ssl:
        proto = "https"
    else:
        proto = "http"

    # first we ping the arbiters unless we find one alive
    if "," in options.hostnames:
        hostnames = options.hostnames.split(",")
    else:
        hostnames = [ options.hostnames ]

    hostname = None
    for h in hostnames:
        result = ping(host=h, port=options.portnum, proto=proto, timeout=options.timeout)
        if result["status"]:
            hostname = h
            break

    if not hostname:
        # no arbiter are alive !
        print "CRITICAL : No arbiter reachable !"
        if result and result.get('message', None):
            print "\n%s" % result['message']
        sys.exit(CRITICAL)

    # Check for required option target
    if not getattr(options, 'target'):
        print ('CRITICAL - target is not specified; '
               'You must specify the daemon name type you want to check!')
        parser.print_help()
        sys.exit(CRITICAL)
    elif options.target not in daemon_types:
        print 'CRITICAL - target', options.target, 'is not a Shinken daemon!'
        parser.print_help()
        sys.exit(CRITICAL)

    # get daemons status (target = daemon type, daemon = daemon name)
    result = get_status(host=hostname, port=options.portnum, proto=proto, daemon_name=options.target, timeout=options.timeout)
    if not "status" in result.keys() or not result["status"]:
        print "Error : ", result["message"]
        sys.exit(UNKNOWN)
    else:
        # specific daemon name
        if result["data"]["alive"]:
            print "[OK] %s %s is alive" % (options.target, options.daemon)
            sys.exit(OK)
        else:
            print "[CRITICAL] %s %s is dead" % (options.target, options.daemon)
            sys.exit(CRITICAL)


