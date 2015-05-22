.. _thebasics/update:

===============
Update Alignak 
===============

Whatever the way you used to install the previous version of Alignak, you should use the same to update. Otherwise juste start from scratch a new Alignak install.

As mentioned in the :ref:`installation page <gettingstarted/installations/alignak-installation>`, 1.X and 2.0 have big differences.

.. warning:: Don't forget to backup your alignak configuration before updating!

Update can be done by following (more or less) those steps :

 * Create the new paths for Alignak (if you don't want new paths then you will have to edit Alignak configuration)

::

  mkdir /etc/alignak /var/lib/alignak/ /var/run/alignak /var/log/alignak
  chown alignak:alignak /etc/alignak /var/lib/alignak/ /var/run/alignak /var/log/alignak


* Install Alignak by following the installation instructions

* Copy your previous Alignak configuration to the new path

::

  cp -pr /usr/local/alignak/etc/<your_config_dir> /etc/alignak/


* Copy the modules directory to the new one

::

  cp -pr /usr/local/alignak/alignak/modules /var/lib/alignak/


* Edit the Alignak configuration to match you need. Basically you will need to remove the default alignak configuration of daemons and put the previous one. Alignak-specific is now split into several files.
  Be carful with the ini ones, you may **merge** them if you modified them. Careful to put the right *cfg_dir* statement in the alignak.cfg.


.. important::  Modules directories have changed a lot in Alignak 2.0. If you copy paste the previous one it will work  **BUT** you may have trouble if you use Alignak CLI.
   
