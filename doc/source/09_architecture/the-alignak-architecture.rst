.. _architecture/the-alignak-architecture:

=====================
Alignak Architecture 
=====================


Summary 
========

Alignak's architecture has been designed according to the Unix Way: one tool, one task. Alignak has an architecture where each part is isolated and connects to the others via standard interfaces. Alignak is based on a HTTP backend. This makes building a highly available or distributed monitoring architectures quite easy.

  * Alignak gets data IN

    * passively
    * actively
    * Networked API

  * Alignak acts on the data

    * Correlation
    * Event suppression
    * Event handlers
    * Adding new poller daemons
    * Runtime interaction

  * Alignak gets data OUT

    * Networked API
    * Notifications
    * Logging
    * Web/Mobile Frontend (via API and Native WebUI)
    * Metrics databases

  * Alignak manages configurations

    * Discovery manager SkonfUI
    * Multi-level discovery engine
    * Configuration Packs (commands, config templates, graph templates, etc.)
    * Text file management via configuration engines (cfengine, chef, puppet, salt)


Alignak innovative features 
============================

Learn more about the :ref:`innovative features of Alignak <about/alignak-innovative-features>`.


Alignak data acquisition for monitoring 
========================================

Alignak needs plugins to actually gather data. There exists `**thousands** of plugins for every conceivable application`_. Alignak packages the configurations necessary to use common plugins in :ref:`Packs <contributing/create-and-push-packs>`. Plugins themselves need to be installed by the administrator of the monitoring solution(Alignak will install some common ones for you). This is a great strength and flexibility of Alignak, but also an administrative responsibility to download and install the necessary plugins.


Architecture diagram with all daemons illustrated 
==================================================

.. image:: /_static/images///official/images/alignak-architecture.png
   :scale: 90 %


Alignak Daemon roles 
=====================

    * :ref:`Arbiter <configobjects/arbiter>`: The arbiter daemon reads the configuration, divides it into parts (N schedulers = N parts), and distributes them to the appropriate Alignak daemons. Additionally, it manages the high availability features: if a particular daemon dies, it re-routes the configuration managed by this failed daemon to the configured spare. Finally, it can receive input from users (such as external commands from nagios.cmd) or passive check results and routes them to the appropriate daemon. Passive check results are forwarded to the Scheduler responsible for the check. There can only be one active arbiter with other arbiters acting as hot standby spares in the architecture.

      * Modules for data collection: :ref:`NSCA <nsca_daemon_module>`, :ref:`TSCA <tsca_daemon_module>`, :ref:`Ws_arbiter <ws_daemon_module>` (web service)
      * Modules for configuration data storage: MongoDB
      * Modules for status retention: PickleRententionArbiter
      * Modules for configuration import: MySQLImport, :ref:`GLPI <gpli_import_module>`, :ref:`Landscape(Ubuntu) <landscape_import_module>`
      * Modules for configuration modification: :ref:`vmware autolinking <vmware_arbiter_module>`, :ref:`IP_Tag <ip_tag_module>`,  and other task specific modules


    * :ref:`Scheduler <configobjects/scheduler>`: The scheduler daemon manages the dispatching of checks and actions to the poller and reactionner daemons respectively. The scheduler daemon is also responsible for processing the check result queue, analyzing the results, doing correlation and following up actions accordingly (if a service is down, ask for a host check). It does not launch checks or notifications. It just keeps a queue of pending checks and notifications for other daemons of the architecture (like pollers or reactionners). This permits distributing load equally across many pollers. There can be many schedulers for load-balancing or hot standby roles. :ref:`Status persistence is achieved using a retention module <distributed_retention_modules>`.

      * Modules for status retention: pickle, nagios, memcache, redis and MongoDB are available.


    * :ref:`Poller <configobjects/poller>`: The poller daemon launches check plugins as requested by schedulers. When the check is finished it returns the result to the schedulers. Pollers can be tagged for specialized checks (ex. Windows versus Unix, customer A versus customer B, DMZ) There can be many pollers for load-balancing or hot standby spare roles.

      * Module for data acquisition: :ref:`NRPE Module <packages/setup-nrpe-booster-module>`
      * Module for data acquisition: CommandFile (Used for check_mk integration which depends on the nagios.cmd named pipe )
      * Module for data acquisition: :ref:`SnmpBooster <packages/snmp/setup>` (NEW)


    * :ref:`Reactionner <configobjects/reactionner>`: The reactionner daemon issues notifications and launches event_handlers. This centralizes communication channels with external systems in order to simplify SMTP authorizations or RSS feed sources (only one for all hosts/services). There can be many reactionners for load-balancing and spare roles

      * Module for external communications: :ref:`AndroidSMS <advanced/sms-with-android>`

    * :ref:`Broker <configobjects/broker>`: The broker daemon exports and manages data from schedulers.  The broker uses modules exclusively to get the job done. The main method of interacting with Alignak is through the Livestatus API. Learn how to :ref:`configure the Broker modules <packages/the-broker-modules>`.

      * Modules for the Livestatus API - live state, status retention and history:  SQLite (default), MongoDB (experimental)
      * Module for centralizing Alignak logs: Simple-log (flat file)
      * Modules for data retention: Pickle , ToNdodb_Mysql, ToNdodb_Oracle, <del>couchdb</del> 
      * Modules for exporting data: Graphite-Perfdata, NPCDMOD(PNP4Nagios), raw_tcp(Splunk), Syslog
      * Modules for the Alignak WebUI: GRAPHITE_UI, PNP_UI. Trending and data visualization.
      * Modules for compatibility/migration: Service-Perfdata, Host-Perfdata and Status-Dat 


    * **Receiver** (optional): The receiver daemon receives passive check data and serves as a distributed command buffer. There can be many receivers for load-balancing and hot standby spare roles. The receiver can also use modules to accept data from different protocols. Anyone serious about using passive check results should use a receiver to ensure that check data does not go through the Arbiter (which may be busy doing administrative tasks) and is forwarded directly to the appropriate Scheduler daemon(s).

      * Module for passive data collection: :ref:`NSCA <nsca_daemon_module>`, :ref:`TSCA <tsca_daemon_module>`, :ref:`Ws_arbiter (web service) <ws_daemon_module>`

.. tip::  The various daemons can be run on a single server for small deployments or split on different hardware for larger deployments as performance or availability requirements dictate. For larger deployments, running multiple Schedulers is recommended, even if they are on the same server. Consult :ref:`planning a large scale Alignak deployment <advanced/scaling-alignak>` for more information.


Learn more about the Alignak Distributed Architecture 
======================================================

The Alignak distributed architecture, more features explained.

  * :ref:`Smart and automatic load balancing <advanced/distributed#the_smart_and_automatic_load_balancing>`
  * :ref:`High availability <advanced/distributed#the_high_availability>`
  * :ref:`Specialized Pollers <advanced/distributed#poller_tag>`
  * :ref:`Advanced architectures: Realms <advanced/distributed#realms>`

If you are just starting out, you can continue on with the next tutorial, which will help you :ref:`Configure a web front-end <integration/index>`.


Planning a large scale Alignak deployment 
==========================================

If you wish to plan a large scale installation of Alignak, you can consult the :ref:`Scaling Alignak <advanced/scaling-alignak>` reference.

This is essential to avoid making time consuming mistakes and aggravation.


.. _**thousands** of plugins for every conceivable application: http://exchange.nagios.org/directory/Plugins
