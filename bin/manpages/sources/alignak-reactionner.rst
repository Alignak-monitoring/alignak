===================
alignak-reactionner
===================

--------------------------
Alignak reactionner daemon
--------------------------

:Author:            Alignak Team
:Date:              2018-05-21
:Version:           1.1.0
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

    $ alignak-reactionner -h
    usage: alignak-reactionner [-h] [-v] -n DAEMON_NAME [-d] [-r] [-o HOST] [-p PORT] [-l LOG_FILENAME] [-i PID_FILENAME] -e ENV_FILE

    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         show program's version number and exit
      -n DAEMON_NAME, --name DAEMON_NAME
                            Daemon unique name. Must be unique for the same daemon
                            type.
      -d, --daemon          Run as a daemon. Fork the launched process and
                            daemonize.
      -r, --replace         Replace previous running daemon if any pid file is
                            found.
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
