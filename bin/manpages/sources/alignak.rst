=======
alignak
=======

----------------------------
Alignak monitoring framework
----------------------------

:Author:            Alignak Team
:Date:              2018-08-20
:Version:           2.0.0
:Manual section:    8
:Manual group:      Alignak commands


DESCRIPTION
===========

Alignak is a monitoring application made of several daemons which features may be extended thanks to modules. Each daemon type has its own role in the monitoring process.

Arbiter
-------

The **Arbiter** (see man alignak-scheduler(8)) daemon role:

   * Loading the Alignak own configuration (daemons, behavior, ...)

   * Loading the monitored system objects configuration (hosts, services, contacts, ...), loaded from Nagios legacy configuration files or from the Alignak backend database

   * Dispatching the whole framework configuration to the other daemons

   * Managing daemons connections and monitoring the state of the other daemons

   * Forwarding failed daemons configuration to spare daemons

   * Receiving external commands

   * Collecting the monitoring events log

   * Reporting Alignak state

There can have only one active Arbiter, other arbiters (if they exist in the configuration) are acting as standby spares.


Scheduler
---------

The **Scheduler** (see man alignak-scheduler(8)) daemon role:

    * scheduling the checks to launch

    * determines action to execute (notifications, acknowledges, ...)

    * dispatches the checks and actions to execute to the pollers and reactionners

There can have many schedulers for load-balancing; each scheduler is managing its own hosts list.


Poller
------

The **Poller** (see man alignak-poller(8)) runs the active checks required by the **Scheduler**.

There can have many pollers for load-balancing.


Receiver
--------

The **Receiver** (see man alignak-receiver(8)) daemon receives the passive checks and external commands.

There can have many receivers for load-balancing.

Broker
------

The **Broker** (see man alignak-broker(8)) daemon gets all the broks from the other daemons. It propagates the events to its specialized modules (eg. Alignak backend database storage, ...)

There can have many brokers for load-balancing.


Reactionner
-----------

The **Reactionner** (see man alignak-reactionner(8)) daemon runs the event handlers and sends the notifications to the users.

There can have many reactionners for load-balancing.

REPORTING BUGS
==============
Report all bugs in the project issues tracker <https://github.com/Alignak-monitoring/alignak/issues>

COPYRIGHT
=========
Copyright (c) 2015-2018: Alignak team
Alignak is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
License GPLv3+: <http://gnu.org/licenses/gpl.html>.

SEE ALSO
========
alignak-arbiter(8), alignak-scheduler(8), alignak-broker(8), alignak-poller(8), alignak-reactionner(8), alignak-receiver(8)

Full documentation at: <http://docs.alignak.net>