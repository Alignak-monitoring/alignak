=================
alignak-scheduler
=================

------------------------
Alignak scheduler daemon
------------------------

:Author:            Michael Leinartas,
                    Arthur Gautier,
                    David Hannequin,
                    Thibault Cohen
:Date:              2014-04-24
:Version:           2.0.1
:Manual section:    8
:Manual group:      Alignak commands


SYNOPSIS
========

  **alignak-scheduler** [-dr] [-c *CONFIGFILE*] [--debugfile *DEBUGFILE*]

DESCRIPTION
===========

Alignak scheduler daemon.

The **alignak-scheduler** manages the dispatching of checks and actions sent to alignak-reactionner and alignak-poller based on configuration sent to it by alignak-arbiter.

OPTIONS
=======

  -c INI-CONFIG-FILE, --config=INI-CONFIG-FILE  Config file
  -d, --daemon                                  Run in daemon mode
  -r, --replace                                 Replace previous running scheduler
  -h, --help                                    Show this help message
  --version                                     Show program's version number 
  --debugfile=DEBUGFILE                         Enable debug logging to *DEBUGFILE*
  -p PROFILE, --profile=PROFILE                 Dump a profile file. Need the python cProfile librairy

