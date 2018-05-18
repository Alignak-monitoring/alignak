===============
alignak-arbiter
===============

----------------------
Alignak arbiter daemon
----------------------

:Author:            Alignak Team
:Date:              2018-05-21
:Version:           1.1.0
:Manual section:    8
:Manual group:      Alignak commands


SYNOPSIS
========

  **alignak-arbiter** -n arbiter-name -e alignak-configuration-file
  **alignak-arbiter** -V -e alignak-configuration-file

DESCRIPTION
===========

Alignak arbiter daemon

The **alignak-arbiter** daemon reads the configuration, divides it into parts
(N schedulers = N parts), and distributes the configuration to the appropriate
Alignak daemons.

It checks the daemons status and report the Alignak statistics.

Additionally, it manages the high availability features: if a particular daemon dies,
it re-routes the configuration managed by this failed  daemon to the configured spare.
There can only be one active arbiter in the architecture.


OPTIONS
=======

    $ alignak-arbiter -h
    usage: alignak-arbiter [-h] [-v] [-a MONITORING_FILES] [-V] [-k ALIGNAK_NAME] [-n DAEMON_NAME] [-d] [-r] [-o HOST] [-p PORT] [-l LOG_FILENAME] [-i PID_FILENAME] -e ENV_FILE

    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         show program's version number and exit
      -a MONITORING_FILES, --arbiter MONITORING_FILES
                            Monitored configuration file(s). This option is still
                            available but is is preferable to declare the
                            monitored objects files in the alignak-configuration
                            section of the environment file specified with the -e
                            option.Multiple -a can be used, and they will be
                            concatenated to make a global configuration file.
      -V, --verify-config   Verify the configuration file(s) and exit
      -k ALIGNAK_NAME, --alignak-name ALIGNAK_NAME
                            Set the name of the Alignak instance. If not set, the
                            arbiter name will be used in place. Note that if an
                            alignak_name variable is defined in the configuration,
                            it will overwrite this parameter.For a spare arbiter,
                            this parameter must contain its name!
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
