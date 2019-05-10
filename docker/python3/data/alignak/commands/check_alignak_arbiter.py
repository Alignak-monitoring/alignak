#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
check_alignak command line interface::

    Usage:
        check_alignak [-h]
        check_alignak [-V]
        check_alignak [-v]
                      [-a url] [-u username] [-p password]

    Options:
        -h, --help                  Show this screen.
        -V, --version               Show application version.
        -v, --verbose               Run in verbose mode (more info to display)
        -a, --alignak url           Specify Arbiter backend URL [default: http://127.0.0.1:7770]
        -u, --username=username     Backend login username [default: admin]
        -p, --password=password     Backend login password [default: admin]

    Exit code:
        0 if all Alignak satellites are ok
        1 if some satellites are not alive, but not yet considered as dead
        2 if one or more satellite is dead

        3 for any running problem

    Note: username and passwork options are ignored currently.
"""
from __future__ import print_function

import json
import logging
import requests

from docopt import docopt, DocoptExit

# Configure logger
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(message)s')

logger = logging.getLogger('check_alignak')
logger.setLevel('INFO')
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Use the same version as the main alignak backend
__version__ = "1.0.0"


class AlignakStatus(object):
    """Class to interface the Alignak Arbiter to get status information"""

    def __init__(self):
        # Get command line parameters
        args = None
        try:
            args = docopt(__doc__, version=__version__)
        except DocoptExit as exp:
            print("Command line parsing error:\n%s." % (exp))
            exit(3)

        # Verbose mode
        self.verbose = False
        if args['--verbose']:
            logger.setLevel('DEBUG')
            self.verbose = True

        # Alignak Backend URL
        self.alignak = None
        self.alignak_url = args['--alignak']
        logger.debug("Alignak URL: %s", self.alignak_url)

        # Backend authentication
        self.username = args['--username']
        self.password = args['--password']
        logger.debug("Backend login with credentials: %s/%s", self.username, self.password)

    def initialize(self):
        """Login on Alignak arbiter with username and password

        :return: None
        """
        try:
            self.alignak = requests.Session()
            raw_data = self.alignak.get("%s/" % self.alignak_url)
            data = json.loads(raw_data.content)
            logger.debug("Alignak arbiter identity: %s", data)
        except Exception as exp:
            logger.error("Alignak arbiter is not available: %s", exp)
            return 2

        return 0


    def status(self):
        """Get Alignak arbiter status

        :return: None
        """
        try:
            status = 0
            long_output = []
            raw_data = self.alignak.get("%s/status" % self.alignak_url)
            data = json.loads(raw_data.content)
            logger.debug("Alignak is %s: %s", data['livestate']['state'], data['livestate']['output'])
            output = "Alignak is %s: %s" % (data['livestate']['state'], data['livestate']['output'])
            for satellite in data['services']:
                state = satellite['livestate']['state'].lower()
                logger.debug("-: %s / %s / %s", satellite['name'], state, satellite['livestate']['output'])
                long_output.append("'%s' is %s: %s" % (satellite['name'], state, satellite['livestate']['output']))
                if state == 'warning':
                    status = 1
                elif state == 'critical':
                    status = 2
                elif state != 'ok':
                    status = 3
            if long_output:
                logger.info("%s\n%s", output, '\n'.join(long_output))
            else:
                logger.info(output)
        except Exception as exp:
            logger.error("Alignak arbiter is not available: %s", exp)
            return 2

        return status


def main():
    """
    Main function
    """
    alignak = AlignakStatus()
    exit_code = alignak.initialize()
    if exit_code:
        exit(exit_code)

    logger.debug("check_alignak, version: %s", __version__)
    logger.debug("~~~~~~~~~~~~~~~~~~~~~~~~~~")

    exit_code = alignak.status()
    exit(exit_code)


if __name__ == "__main__":  # pragma: no cover
    main()
