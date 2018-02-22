=======================
Alignak collectd plugin
=======================

*Alignak project - modern Nagios compatible monitoring framework*

Alignak daemons have an HTTP json API that allows to get information about the daemons status. Especially, the arbiter daemon has an endpoint providing many useful data to be aware of the global Alignak framework status.

Thanks to `collectd <https://collectd.org/>`_, some metrics can be collected and provided to a graphite database.


Installation
------------

Install the `collectd <https://collectd.org/>`_ daemon on your system according to the project documentation.


Configuration
-------------

Alignak processes monitoring
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The running Alignak daemons may be monitored thanks to the `collectd processes` plugin.
::

    LoadPlugin processes

    ...

    <Plugin processes>
        ProcessMatch "alignak" "python2.7: alignak-.*"
        ProcessMatch "alignak-backend" "uwsgi --ini /my_configuration_root/etc/alignak-backend/uwsgi.ini"
        ProcessMatch "alignak-webui" "uwsgi --ini /my_configuration_root/etc/alignak-webui/uwsgi.ini"
    </Plugin>

Use a *ProcessMatch* directive to get the Alignak daemons processes. The former example is a valid example for an Alignak installation on a FreeBSD server.

The first *ProcessMatch* directive get all the launched Alignak daemons: processes which name starts with `python2.7: alignak-`

Grafana dashboard
-----------------

See the requirements file in the repository's root
