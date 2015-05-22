.. _advanced/checkscheduling:

===================================
 Service and Host Check Scheduling 
===================================


The scheduling 
===============

The scheduling of Alignak is quite simple. The first scheduling take care of the max_service_check_spread and max_host_check_spread so the time of the first schedule will be in the 

::

 start+max_*_check_spread*interval_length (60s in general) 

if the check_timeperiod agree with it.

.. note::  Alignak do not take care about Nagios \*_inter_check_delay_method : this is always 's' (smart) because other options are just useless for nearly everyone. And it also do not use the \*_interleave_factor too.

Nagios make a average of service by host to make it's dispatch of checks in the first check window. Alignak use a random way of doing it : the check is between t=now and t=min(t from next timeperiod, max_*_check_spread), but in a random way. So you will will have the better distribution of checks in this period, instead of the nagios one where hosts with differents number of services can be agresively checks.

After this first scheduling, the time for the next check is just t_check+check_interval if the timepriod is agree for it (or just the next time available in the timeperiod). In the future, a little random value (like few seconds) will be add for such cases.


.. _advanced/unused-nagios-parameters#use_aggressive_host_checking:

Aggressive Host Checking Option (Unused) 
========================================

======== ==================================
Format:  use_aggressive_host_checking=<0/1>
Example: use_aggressive_host_checking=0    
======== ==================================

Nagios tries to be smart about how and when it checks the status of hosts. In general, disabling this option will allow Nagios to make some smarter decisions and check hosts a bit faster. Enabling this option will increase the amount of time required to check hosts, but may improve reliability a bit. Unless you have problems with Nagios not recognizing that a host recovered, I would suggest not enabling this option.

  * 0 = Don't use aggressive host checking (default)
  * 1 = Use aggressive host checking

