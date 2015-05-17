.. _gettingstarted/installations/alignak-installation:

=====================================
10 Minutes Alignak Installation Guide 
=====================================


Summary 
=======

By following this tutorial, in 10 minutes you will have the core monitoring system for your network.

The very first step is to verify that your server meets the :ref:`requirements <gettingstarted/installations/alignak-installation#requirements>`, the installation script will try to meet all requirements automatically.
   
You can get familiar with the :ref:`Alignak Architecture <architecture/the-alignak-architecture>` now, or after the installation. This will explain the software components and how they fit together.

  * Installation : :ref:`GNU/Linux & Unix <gettingstarted/installations/alignak-installation#gnu_linux_unix>`
  * Installation : :ref:`Windows <gettingstarted/installations/alignak-installation#windows_installation>`

Ready? Let's go!


.. _gettingstarted/installations/alignak-installation#requirements:

Requirements
============

Mandatory Requirements
----------------------

* `Python`_ 2.6 or higher (2.7 will get higher performance)
* `python-pycurl`_ Python package for Alignak daemon communication
* `setuptools`_ or `distribute` Python package for installation


Conditional Requirements
------------------------

* `Python`_ 2.7 is required for developers to run the test suite, alignak/test/
* `python-cherrypy3`_ (recommended) enhanceddaemons communications, especially in HTTPS mode
* `Monitoring Plugins`_ (recommended) provides a set of plugins to monitor host (Alignak uses check_icmp by default install).
  Monitoring plugins are available on most linux distributions (nagios-plugins package)


.. _gettingstarted/installations/alignak-installation#gnu_linux_unix:

.. warning::  Do not mix installation methods! If you wish to change method, use the uninstaller from the chosen method THEN install using the alternate method.


GNU/Linux & Unix Installation 
=============================

Method 1: Pip
-------------

Alignak 2.4 is available on Pypi : https://pypi.python.org/pypi/Alignak/2.4
You can download the tarball and execute the setup.py or just use the pip command to install it automatically.


::

  apt-get install python-pip python-pycurl
  adduser alignak
  pip install alignak


Method 2: Packages 
-------------------

For now the 2.4 packages are not available, but the community is working hard for it! Packages are simple, easy to update and clean.
Packages should be available on Debian/Ubuntu and Fedora/RH/CentOS soon (basically  *.deb* and  *.rpm*).


Method 3: Installation from sources 
------------------------------------

Download last stable `Alignak tarball`_ archive (or get the latest `git snapshot`_) and extract it somewhere:

::

  adduser alignak
  wget http://www.
  tar -xvzf alignak-2.4.tar.gz
  cd alignak-2.4
  python setup.py install


Alignak 2.X uses LSB path. If you want to stick to one directory installation you can of course.
Default paths are the following:

 * **/etc/alignak** for configuration files
 * **/var/lib/alignak** for alignak modules, retention files...
 * **/var/log/alignak** for log files
 * **/var/run/alignak** for pid files


.. _gettingstarted/installations/alignak-installation#windows_installation:


Windows Installation 
====================

For 2.X+ the executable installer may not be provided. Consequently, installing Alignak on a Windows may be manual with setup.py.
Steps are basically the same as on Linux (Python install etc.) but in windows environment it's always a bit tricky.


.. _Python: http://www.python.org/download/
.. _python-cherrypy3: http://www.cherrypy.org/
.. _Monitoring Plugins: https://www.monitoring-plugins.org/
.. _python-pycurl: http://pycurl.sourceforge.net/
.. _setuptools: http://pypi.python.org/pypi/setuptools/
.. _git snapshot: https://github.com/naparuba/alignak/tarball/master
.. _Alignak tarball: http://www.
.. _install.d/README: https://github.com/Alignak-monitoring/alignak/blob/master/install.d/README

