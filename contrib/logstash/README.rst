================
Alignak Logstash
================

Alignak monitoring log is easily parsable thanks to logstash to store all the monitoring events into an Elasticsearch database. Logstash is a powerful and easy to use log parser... and Kibana alllows to easily build dashboards from the data collected ;)


Installation
------------

Install the `logstash parser <https://www.elastic.co/fr/products/logstash/>`_ daemon on your system according to the project documentation.

A `logstash.conf` example file is available in the same directory as this doc file.

Configuration
-------------

Copy the `logstash.conf` in the logstash configuration directory (eg. */usr/local/etc/logstash*) and copy the *patterns* directory of this repository in the same place.

Update the `logstash.conf` according to your configuration. Some important updates:
- the date inserted in each log is formatted according to the logger configuration. Often it is an ISO date yyyy-mm-dd hh:mm:ss but you may have set this date as a unix timestamp. Update the patterns and the `logstash.conf` accordingly
- the elasticsearch URL must be updated to connect your own ES cluster

Collected information
---------------------

Daemons log
~~~~~~~~~~~

The logstash parser is able to analyse the Alignak daemons log files. Extracted information are:
- alignak.timestamp
- alignak.log_level
- alignak.daemon
- alignak.source
- alignak.message

Monitoring log
~~~~~~~~~~~~~~

