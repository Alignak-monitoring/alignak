.. _gettingstarted/installations/alignak-env-setup:

================================
Configure Alignak for Production
================================

If you have installed Alignak with packages, they should be production-ready. Otherwise, you should do the following steps to ensure everything is fine.


Enable Alignak at boot
=======================

This depend on your Linux distribution (actually it's related to the init mechanism : upstart, systemd, sysv ..) you may use one of the following tool.

Systemd
--------

This enable Alignak service on a systemd base OS. Note that a Alignak service can be used to start all service.

::

  for i in arbiter poller reactionner scheduler broker receiver; do
  systemctl enable alignak-$i.service;
  done


RedHat / CentOS
----------------

This enable Alignak service on a RedHat/CentOS. Note that a Alignak service can be used to start all service.

::

  chkconfig alignak on


Debian / Ubuntu
----------------

This enable Alignak service on a Debian/Ubuntu.

::

  update-rc.d alignak defaults


Start Alignak
==============

This also depend on the OS you are running. You can start Alignak with one of the following:

::

  /etc/init.d/alignak start
  service alignak start
  systemctl start alignak


Configure Alignak for Sandbox
==============================

If you want to try Alignak and keep a simple configuration you may not need to have Alignak enabled at boot.
In this case you can just start Alignak with the simple shell script provided into the sources.

::

  ./bin/launch_all.sh


You will have Alignak Core working. No module are loaded for now. You need to install some with the :ref:`command line interface <alignak_cli>`


Configure Alignak for Development
==================================

If you are willing to edit Alignak source code, you should have chosen the third installation method.
In this case you have currently the whole source code in a directory.

The first thing to do is edit the **etc/alignak.cfg** and change the alignak user and group (you can comment the line). You don't need a alignak user do you?
Just run alignak as the current user, creating user is for real alignak setup :)

To manually launch Alignak do the following :

::

   ./bin/alignak-scheduler -c /etc/alignak/daemons/schedulerd.ini -d
   ./bin/alignak-poller -c /etc/alignak/daemons/pollerd.ini -d
   ./bin/alignak-broker -c /etc/alignak/daemons/brokerd.ini -d
   ./bin/alignak-reactionner -c /etc/alignak/daemons/reactionnerd.ini -d
   ./bin/alignak-arbiter -c /etc/alignak/alignak.cfg -d
   ./bin/alignak-receiver -c /etc/alignak/daemons/receiverd.ini -d

