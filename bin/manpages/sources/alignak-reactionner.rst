===================
alignak-reactionner
===================

--------------------------
Alignak reactionner daemon
--------------------------

:Author:            Alignak Team
:Date:              2018-08-20
:Version:           2.0.0
:Manual section:    8
:Manual group:      Alignak commands


SYNOPSIS
========

    **alignak-reactionner** -n reactionner-name -e alignak-configuration-file

DESCRIPTION
===========

Alignak reactionner daemon.

The **alignak-reactionner** daemon is similar to the alignak-poller but it handles actions
such as notifications and event-handlers from the schedulers rather than checks.

OPTIONS
=======

    usage: alignak-reactionner [-h] -n DAEMON_NAME [-c CONFIG_FILE] [-d] [-r]
                               [-vv] [-v] [-o HOST] [-p PORT] [-l LOG_FILENAME]
                               [-i PID_FILENAME] -e ENV_FILE

    Alignak daemon launching

    optional arguments:
      -h, --help            show this help message and exit
      -n DAEMON_NAME, --name DAEMON_NAME
                            Daemon unique name. Must be unique for the same daemon
                            type.
      -c CONFIG_FILE, --config CONFIG_FILE
                            Daemon configuration file. Deprecated parameter, do
                            not use it anymore!
      -d, --daemon          Run as a daemon. Fork the launched process and
                            daemonize.
      -r, --replace         Replace previous running daemon if any pid file is
                            found.
      -vv, --debug          Set log level to debug mode (DEBUG)
      -v, --verbose         Set log level to verbose mode (INFO)
      -o HOST, --host HOST  Host interface used by the daemon. Default is 0.0.0.0
                            (all interfaces).
      -p PORT, --port PORT  Port used by the daemon. Default is set according to
                            the daemon type.
      -l LOG_FILENAME, --log_file LOG_FILENAME
                            File used for the daemon log. Set as empty to disable
                            log file.
      -i PID_FILENAME, --pid_file PID_FILENAME
                            File used to store the daemon pid
      -e ENV_FILE, --environment ENV_FILE
                            Alignak global environment file. This file defines all
                            the daemons of this Alignak instance and their
                            configuration. Each daemon configuration is defined in
                            a specifc section of this file.
