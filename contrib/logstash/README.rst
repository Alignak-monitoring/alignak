================
Alignak Logstash
================

Alignak monitoring events log is easily parsable thanks to logstash to store all the monitoring events into an Elasticsearch database or any other...). Logstash is a powerful and easy to use log parser... and Kibana allows to easily build dashboards from the data collected ;)


Installation
------------

Install the `logstash parser <https://www.elastic.co/fr/products/logstash/>`_ daemon on your system according to the project documentation.

A `logstash.conf` example file is available in the same directory as this doc file.

Configuration
-------------

Copy the `logstash.conf` in the logstash configuration directory (eg. */etc/logstash*) and copy the *patterns* directory of this repository in the same place.

Update the `logstash.conf` according to your configuration. Some important updates:
- the date inserted in each log is formatted according to the logger configuration. Often it is an ISO date yyyy-mm-dd hh:mm:ss but you may have set this date as a unix timestamp. Update the patterns and the `logstash.conf` accordingly
- the elasticsearch URL must be updated to connect your own ES cluster

Using an output plugin for MongoDB allows to get Alignak events log in a MongoDB collection::

   # Install the output plugin for MongoDB
   $ sudo /usr/share/logstash/bin/logstash-plugin install logstash-output-mongodb
   Validating logstash-output-mongodb
   Installing logstash-output-mongodb
   Installation successful


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

All the monitoring events are extracted from the monitoring events log and pushed to the output plugins defined in the logstash.conf file: elasticsearch and / or mongodb. Default is to push to elasticsearch; you can uncomment to push the parsed log to a Mongo database.
