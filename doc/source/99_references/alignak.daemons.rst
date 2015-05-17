

daemons Package
===============

Diagrams
--------

Simple Daemon class diagram :

.. inheritance-diagram:: alignak.daemon.Daemon
                         alignak.daemons.arbiterdaemon.Arbiter alignak.satellite.BaseSatellite
                         alignak.daemons.brokerdaemon.Broker  alignak.daemons.schedulerdaemon.Alignak  alignak.satellite.Satellite
                         alignak.daemons.pollerdaemon.Poller  alignak.daemons.receiverdaemon.Receiver  alignak.daemons.reactionnerdaemon.Reactionner
   :parts: 3



Simple Interface class diagram :

.. inheritance-diagram:: alignak.daemon.Interface
                         alignak.daemons.receiverdaemon.IStats  alignak.daemons.brokerdaemon.IStats  alignak.daemons.schedulerdaemon.IChecks
                         alignak.daemons.schedulerdaemon.IBroks  alignak.daemons.schedulerdaemon.IStats  alignak.daemons.arbiterdaemon.IForArbiter
                         alignak.satellite.IForArbiter  alignak.satellite.ISchedulers  alignak.satellite.IBroks  alignak.satellite.IStats
   :parts: 3

Package
-------

:mod:`daemons` Package
----------------------

.. automodule:: alignak.daemons
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`arbiterdaemon` Module
---------------------------

.. automodule:: alignak.daemons.arbiterdaemon
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`brokerdaemon` Module
--------------------------

.. automodule:: alignak.daemons.brokerdaemon
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`pollerdaemon` Module
--------------------------

.. automodule:: alignak.daemons.pollerdaemon
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`reactionnerdaemon` Module
-------------------------------

.. automodule:: alignak.daemons.reactionnerdaemon
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`receiverdaemon` Module
----------------------------

.. automodule:: alignak.daemons.receiverdaemon
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`schedulerdaemon` Module
-----------------------------

.. automodule:: alignak.daemons.schedulerdaemon
    :members:
    :undoc-members:
    :show-inheritance:

