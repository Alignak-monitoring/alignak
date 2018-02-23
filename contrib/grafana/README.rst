===============
Alignak Grafana
===============

Alignak daemons have an HTTP json API that allows to get information about the daemons status. Especially, the arbiter daemon has an endpoint providing many useful data to be aware of the global Alignak framework status.

Thanks to `collectd <https://collectd.org/>`_, some metrics can be easily collected and provided to a graphite database. Then a smart Grafana dashboard allows to have a nice interface to monitor you Alignak instance :)


Configuration
-------------

Alignak inner statistics
~~~~~~~~~~~~~~~~~~~~~~~~

Defining the ``ALIGNAK_DAEMON_MONITORING`` environment variable will make each Alignak daemon add some debug log to inform about its own CPU and memory consumption.

On each activity loop end, if the report period is happening, the daemon gets its current cpu and memory information from the OS and log these information formatted as a Nagios plugin output with performance data. The default report period is set to 10 loop turn (eg. 10 seconds). As such, each 10 loop turn, there is a cpu/memory log. If then environment variable contains an integer value, this value will define the log period in loop count. Defining ``ALIGNAK_DAEMON_MONITORING`` with ``5`` will make a log each 5 loop turn.

If Alignak is configured to notify its inner statistics to a StatsD daemon, the collected metrics will also be sent to StatsD.

An example Grafana dashboard is available in the same directory as this doc file to view the Alignak daemons collected metrics.

.. image:: grafana-alignak-daemons.png


If this feature is enabled a Grafana Dashboard
::

    LoadPlugin processes

    ...

    <Plugin processes>
        ProcessMatch "alignak" "python: alignak-.*"
        ProcessMatch "alignak-backend" "uwsgi --ini /my_configuration_root/etc/alignak-backend/uwsgi.ini"
        ProcessMatch "alignak-webui" "uwsgi --ini /my_configuration_root/etc/alignak-webui/uwsgi.ini"
    </Plugin>


Alignak daemons monitoring
~~~~~~~~~~~~~~~~~~~~~~~~~~

Defining the ``ALIGNAK_DAEMON_MONITORING`` environment variable will make each Alignak daemon add some debug log to inform about its own CPU and memory consumption.

On each activity loop end, if the report period is happening, the daemon gets its current cpu and memory information from the OS and log these information formatted as a Nagios plugin output with performance data. The default report period is set to 10 loop turn (eg. 10 seconds). As such, each 10 loop turn, there is a cpu/memory log. If then environment variable contains an integer value, this value will define the log period in loop count. Defining ``ALIGNAK_DAEMON_MONITORING`` with ``5`` will make a log each 5 loop turn.

If Alignak is configured to notify its inner statistics to a StatsD daemon, the collected metrics will also be sent to StatsD.

An example Grafana dashboard is available in the same directory as this doc file to view the Alignak daemons collected metrics.

.. image:: grafana-alignak-daemons.png

