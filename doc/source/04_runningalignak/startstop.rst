.. _runningalignak/startstop:

===============================
 Starting and Stopping Alignak 
===============================

There's more than one way to start, stop, and restart Alignak. Here are some of the more common ones...

In recent Alignak versions, you can use the init script to reload Alignak: your configuration will be checked before restarting the arbiter.

Always make sure you :ref:`verify your configuration <runningalignak/verifyconfig>` before you (re)start Alignak.


Starting Alignak 
=================

- Init Script: The easiest way to start the Alignak daemon is by using the init script like so:

::

  linux:~ # /etc/rc.d/init.d/alignak start
  
- Manually: You can start the Alignak daemon manually with the "-d" command line option like so:

::

  linux:~ # /usr/bin/alignak/alignak-scheduler -d -c /etc/alignak/daemons/schedulerd.ini
  linux:~ # /usr/bin/alignak/alignak-poller -d -c /etc/alignak/daemons/pollerd.ini
  linux:~ # /usr/bin/alignak/alignak-reactionner -d -c /etc/alignak/daemons/reactionnerd.ini
  linux:~ # /usr/bin/alignak/alignak-broker -d -c /etc/alignak/daemons/brokerd.ini
  linux:~ # /usr/bin/alignak/alignak-arbiter -d -c /etc/alignak/alignak.cfg
  
.. important::  Enabling debugging output under windows requires changing registry values associated with Alignak


Restarting Alignak 
===================

Restarting/reloading is nececessary when you modify your configuration files and want those changes to take effect.

- Init Script: The easiest way to restart the Alignak daemon is by using the init script like so:

::

  linux:~ # /etc/rc.d/init.d/alignak restart

- Manually: You can restart the Alignak process by sending it a SIGTERM signal like so:

::

  linux:~ # kill <configobjects/arbiter_pid>
  linux:~ # /usr/bin/alignak-arbiter -d -c /etc/alignak/alignak.cfg


Stopping Alignak 
=================

- Init Script: The easiest way to stop the Alignak daemons is by using the init script like so:

::

  linux:~ # /etc/rc.d/init.d/alignak stop
  
- Manually: You can stop the Alignak process by sending it a SIGTERM signal like so:

::

  linux:~ # kill <configobjects/arbiter_pid> <configobjects/scheduler_pid> <configobjects/poller_pid> <configobjects/reactionner_pid> <configobjects/broker_pid>
  
