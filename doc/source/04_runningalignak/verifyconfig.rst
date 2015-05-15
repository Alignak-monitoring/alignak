.. _runningalignak/verifyconfig:

=============================
Verifying Your Configuration 
=============================

Every time you modify your :ref:`Configuration <configuration/config>`, you should run a sanity check on them. It is important to do this before you (re)start Alignak, as Alignak will shut down if your configuration contains errors.

.. note:: In recent Alignak versions, an alignak reload will check your configuration before restarting the arbiter: /etc/init.d/alignak reload


How to verify the configuration 
================================

In order to verify your configuration, run Alignak-arbiter with the "-v" command line option like so:

::

  linux:~ # /usr/bin/alignak-arbiter -v -c /etc/alignak/alignak.cfg
  
If you've forgotten to enter some critical data or misconfigured things, Alignak will spit out a warning or error message that should point you to the location of the problem. Error messages generally print out the line in the configuration file that seems to be the source of the problem. On errors, Alignak will exit the pre-flight check. If you get any error messages you'll need to go and edit your configuration files to remedy the problem. Warning messages can generally be safely ignored, since they are only recommendations and not requirements.


Important caveats 
==================

1. Alignak will not check the syntax of module variables
2. Alignak will not check the validity of data passed to modules
3. Alignak will NOT notify you if you mistyped an expected variable, it will treat it as a custom variable.
4. Alignak sometimes uses variables that expect lists, the order of items in lists is important, check the relevant documentation


How to apply your changes 
==========================

Once you've verified your configuration files and fixed any errors you can go ahead and reload or :ref:`(re)start Alignak <runningalignak/startstop>`.

