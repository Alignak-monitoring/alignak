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
check_shinken2.py:
    This check is getting daemons state from a arbiter connection.
"""

import os
import socket
from optparse import OptionParser
import requests
from requests import exceptions
import json
import sys

# Exit statuses recognized by Nagios and thus by Shinken
OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3

daemon_types = ['arbiter', 'broker', 'scheduler', 'poller', 'reactionner', 'receiver']



def ping(host=None, port=None, proto="http", timeout=1):
    uri = "%s://%s:%s/ping" % (proto, host, port)
    try:
        result = requests.get(uri, timeout=timeout)
        if result.text == "\"pong\"":
            message = { "message":"pong", "status":True }
        else:
            message = { "message":"Invalid response to ping (%s)" % result.text, "status":False }
    except requests.exceptions.ConnectionError:
        message = { "message":"Connection error", "status":False }
    except requests.exceptions.Timeout:
        message = { "message":"Timeout", "status":False }

    return message    

def get_status(host=None, port=None, proto="http", target=None, daemon=None, timeout=1):
    uri = "%s://%s:%s/get-all-states" % (proto, host, port)
    try:
        result = requests.get(uri, timeout=timeout).json()
    except requests.exceptions.ConnectionError:
        message = { "message":"Connection error", "status":False }
    except requests.exceptions.Timeout:
        message = { "message":"Timeout", "status":False }
    finally:
        if target in result.keys():
            data = result[target]
        else:
            data = False

        if daemon:
            found = False
            for d in data:
                if d["%s_name" % target] == daemon:
                    found = True
                    break

            if found:
                data = d
            else:
                data = False


        if not data:
            message = { "message":"Target or Daemon not found", "status":False, "data":data }
        else:
            message = { "message":"OK", "status":True, "data":data }

    return message
 
def get_all_status(host=None, port=None, proto="http", timeout=1):
    uri = "%s://%s:%s/get-all-states" % (proto, host, port)
    try:
        result = requests.get(uri, timeout=timeout).json()
    except requests.exceptions.ConnectionError:
        message = { "message":"Connection error", "status":False }
    except requests.exceptions.Timeout:
        message = { "message":"Timeout", "status":False }
    finally:

        print "From :", host
        print

        print "+%s+" % (106*"-")
        print "| {:^20} | {:^20} | {:^15} | {:^19} | {:^8} | {:^7} |".format("TYPE","NAME","STATUS","REALM","ATTEMPTS","SPARE")
        print "+%s+" % (106*"-")
        for key,data in result.iteritems():
            for daemon in data:

                attempts = "%s/%s" % (daemon["attempt"],daemon["max_check_attempts"])

                if not daemon["alive"]:
                    alive= "dead"
                else:
                    if daemon["attempt"] > 0:
                        alive = "retry"
                    else:
                        alive= "alive"

                if daemon["spare"]:
                    spare = "X"
                else:
                    spare = " "

                if "realm" in daemon.keys():
                    realm = daemon["realm"]
                else:
                    realm = ""

                print "| {:20} | {:20} | {:^15} | {:19} | {:^8} | {:^7} |".format(key,daemon["%s_name" % key], alive, realm, attempts, spare)
        print "+%s+" % (106*"-")



if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option('-a', '--hostnames', dest='hostnames', default='127.0.0.1')
    parser.add_option('-p', '--portnumber', dest='portnum', default=7770, type=int)
    parser.add_option('-s', '--ssl', action="store_true", dest='ssl', default=False)
    parser.add_option('-t', '--target', dest='target',default=False,type=str)
    parser.add_option('-d', '--daemonname', dest='daemon', default='')
    parser.add_option('-T', '--timeout', dest='timeout', default=1, type=float)
    parser.add_option('-v', '--verbose', action="store_true", dest='verbose', default=False)


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

    hostname = False

    for h in hostnames:
        result = ping(host=h, port=options.portnum, proto=proto, timeout=options.timeout)
        if result["status"]:
            hostname = h
            break

    if not hostname:
        # no arbiter are alive !
        print "CRITICAL : No arbiter reachable !" 
        sys.exit(CRITICAL)

    # detailled output and no more
    if options.verbose:
        get_all_status(host=hostname, port=options.portnum, proto=proto, timeout=options.timeout)
        sys.exit(OK)

    # Check for required option target
    if not getattr(options, 'target'):
        print ('CRITICAL - target is not specified; '
               'You must specify which daemon type you want to check!')
        parser.print_help()
        sys.exit(CRITICAL)
    elif options.target not in daemon_types:
        print 'CRITICAL - target', options.target, 'is not a Shinken daemon!'
        parser.print_help()
        sys.exit(CRITICAL)



    # get daemons status (target = daemon type, daemon = daemon name)
    result = get_status(host=hostname, port=options.portnum, proto=proto, target=options.target, daemon = options.daemon, timeout=options.timeout)
    if not "status" in result.keys() or not result["status"]:
        print "Error : ", result["message"]
        sys.exit(UNKNOWN)
    else:
        if type(result["data"]) is list:
            # multiple daemons
            dead = []
            alive = []
            for d in result["data"]:
                if d["alive"]:
                    alive.append(d["%s_name" % options.target])
                else:
                    dead.append(d["%s_name" % options.target])

            if len(dead) > 0:
                print "[CRITICAL] The following %s(s) daemon(s) are dead : %s " % (options.target, ",".join(set(dead)))
                sys.exit(CRITICAL)
            else:
                print "[OK] all %s daemons are alive" % options.target
        else:
            # specific daemon name
            if result["data"]["alive"]:
                print "[OK] %s %s is alive" % (options.target, options.daemon)
                sys.exit(OK)
            else:
                print "[CRITICAL] %s %s is dead" % (options.target, options.daemon)
                sys.exit(CRITICAL)


