.. _integration/integration:

======================
 Integration Overview 
======================


Introduction 
=============

One of the reasons that Alignak is such a popular monitoring application is the fact that it can be easily integrated into your existing infrastructure. There are several methods of integrating Alignak with the management software you're already using and you can monitor almost any type of new or custom hardware, service, or application that you might have.


Integration Points 
===================

.. important::  This diagram is deprecated and illustrates legacy Nagios. Which has nothing to do with the new architecture. eck.


.. image:: /_static/images///official/images/integrationoverview.png
   :scale: 90 %


To monitor new hardware, services, or applications, check out the docs on:

  * :ref:`Nagios Plugins <thebasics/plugins>`
  * :ref:`Nagios Plugin API <development/pluginapi>`
  * :ref:`Passive Checks <thebasics/passivechecks>`
  * :ref:`Event Handlers <advanced/eventhandlers>`

   It is also possible to use Alignak Poller daemon modules or Receiver daemon modules to provide daemonized high performance acquisition. Consult the Alignak architecture to learn more about poller modules. There are existing poller modules that can be usd as examples to further extend Alignak.
  
To get data into Nagios from external applications, check out the docs on:

  * :ref:`Passive Checks <thebasics/passivechecks>`
  * :ref:`External Commands <advanced/extcommands>`

To send status, performance, or notification information from Alignak to external applications, there are two typical paths. Through the Reactionner daemon which executes event handlers and modules or through the Broker daemon. The broker daemon provides access to all internal Alignak objects and state information. Thi data can be accessed through the Livestatus API. The data can also be forwarded by broker modules. Check out the docs on:

  * :ref:`Broker modules <the_broker_modules>`
  * :ref:`Event Handlers <advanced/eventhandlers>`
  * :ref:`OCSP <configuration/configmain-advanced#ocsp_command>` and :ref:`OCHP <configuration/configmain-advanced#ochp_command>` Commands
  * :ref:`Performance Data <advanced/perfdata>`
  * :ref:`Notifications <thebasics/notifications>`


Integration Examples 
=====================

I've documented some examples on how to integrate Alignak with external applications:

  * :ref:`TCP Wrappers Integration <integration/tcpwrappers>` (security alerts)
  * :ref:`SNMP Trap Integration <integration/snmptrap>` (Arcserve backup job status)

