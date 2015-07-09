===================================
Presentation of the Alignak project
===================================

Welcome to the Alignak project.

.. image:: https://api.travis-ci.org/Alignak-monitoring/alignak.svg?branch=develop
  :target: https://travis-ci.org/Alignak-monitoring/alignak
.. image:: https://coveralls.io/repos/Alignak-monitoring/alignak/badge.svg?branch=develop
  :target: https://coveralls.io/r/Alignak-monitoring/alignak


Alignak is a modern - almost 100% Nagios compatible - monitoring framework,
written in Python.
Its main goal is to give users a flexible architecture for
their monitoring system that is designed to scale to large environments.

Alignak is backwards-compatible with the Nagios configuration standard
and plugins. It works on any operating system and architecture that
supports Python, which includes Windows, GNU/Linux and FreeBSD.

Alignak is licensed under the Gnu Affero General Public Licence version 3 (AGPLv3).
Unless specified by another header, this licence apply to all files in this repository 

Requirements
============

See the `Documentation`__ 

__ https://alignak.readthedocs.org/en/latest/02_gettingstarted/installations/alignak-installation.html#requirements

There are mandatory and conditional requirements for the installation
methods which are described below.


Installing Alignak
==================

See the `Documentation`__ 

__ https://alignak.readthedocs.org/en/latest/02_gettingstarted/installations/alignak-installation.html



Update
------

Launch::

  python setup.py install

It will only update the alignak lib and scripts, but won't touch your current configuration


Running
-------

Alignak is installed with `init.d` scripts, enables them at boot time and starts them right after the install process ends. Based on your linux distro you only need to do:

  chkconfig --add alignak
  chkconfig alignak on

or ::

  update-rc.d alignak defaults 20



Where is the configuration?
===========================

The configuration is in the directory, `/etc/alignak`.


Where are the logs?
===================

Logs are in /var/log/alignak
(what did you expect?)


I got a bug, how to launch the daemons in debug mode?
=====================================================

You only need to launch:

  /etc/init.d/alignak -d start

Debug logs will be based on the log directory (/var/log/alignak)


I switched from Nagios, do I need to change my existing Nagios configuration?
=============================================================================

No, there is no need to change the existing configuration - unless
you want to add some new hosts and services. Once you are comfortable
with Alignak you can start to use its unique and powerful features.


Learn more about how to use and configure Alignak
=================================================

Jump to the Alignak documentation__.

__ https://alignak.readthedocs.org/en/latest/


If you find a bug
================================

Bugs are tracked in the `issue list on GitHub`__ . Always search for existing issues before filing a new one (use the search field at the top of the page).
When filing a new bug, please remember to include:

*	A helpful title - use descriptive keywords in the title and body so others can find your bug (avoiding duplicates).
*	Steps to reproduce the problem, with actual vs. expected results
*	Alignak version (or if you're pulling directly from the Git repo, your current commit SHA - use git rev-parse HEAD)
*	OS version
*	If the problem happens with specific code, link to test files (`gist.github.com`__  is a great place to upload code).
*	Screenshots are very helpful if you're seeing an error message or a UI display problem. (Just drag an image into the issue description field to include it).

__ https://github.com/Alignak-monitoring/alignak/issues/
__ https://gist.github.com/



Install Alignak as python lib
=============================

In a virtualenv ::

  virtualenv env
  source env/bin/activate
  python setup.py install_lib
  python -c 'from alignak.bin import VERSION; print(VERSION)'

Or directly on your system ::

  sudo python setup.py install_lib
  python -c 'from alignak.bin import VERSION; print(VERSION)'


Get Alignak dev environment
===========================


To setup Alignak dev environment::

  virtualenv env
  source env/bin/activate
  python setup.py develop
  python setup.py install_data

If you want to use init scripts in your virtualenv you have to REsource ``activate``::

  source env/bin/activate


Folders
-------

env/etc: Configuration folder

env/var/lib/alignak/modules: Modules folder

env/var/log/alignak: Logs folder

env/var/run/alignak: Pid files folder

Launch daemons
--------------

With binaries
~~~~~~~~~~~~~

Arbiter::

  alignak-arbiter -c env/etc/alignak/alignak.cfg

Broker::

  alignak-broker -c env/etc/alignak/daemons/brokerd.ini

Scheduler::

  alignak-scheduler -c env/etc/alignak/daemons/schedulerd.ini

Poller::

  alignak-poller -c env/etc/alignak/daemons/pollerd.ini

Reactionner::

  alignak-reactionner -c env/etc/alignak/daemons/reactionnerd.ini

Receiver::

  alignak-receiver -c env/etc/alignak/daemons/receiverd.ini


With init scripts
~~~~~~~~~~~~~~~~~

Arbiter::

  env/etc/init.d/alignak-arbiter start

Broker::

  env/etc/init.d/alignak-broker start

Scheduler::

  env/etc/init.d/alignak-scheduler start

Poller::

  env/etc/init.d/alignak-poller start

Reactionner::

  env/etc/init.d/alignak-reactionner start

Receiver::

  env/etc/init.d/alignak-receiver start





.. image:: https://badges.gitter.im/Join%20Chat.svg
   :alt: Join the chat at https://gitter.im/Alignak-monitoring/alignak
   :target: https://gitter.im/Alignak-monitoring/alignak?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge
