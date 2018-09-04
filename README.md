# Presentation of the Alignak project

*Alignak - modern Nagios compatible monitoring framework*


[![Master branch build status](https://img.shields.io/travis/Alignak-monitoring/alignak/master.svg?label=master)](https://travis-ci.org/Alignak-monitoring/alignak/branches)
[![Develop branch build status](https://img.shields.io/travis/Alignak-monitoring/alignak/develop.svg?label=develop)](https://github.com/Alignak-monitoring/alignak)
[![Develop branch code quality](https://landscape.io/github/Alignak-monitoring/alignak/develop/landscape.svg?style=flat)](https://landscape.io/github/Alignak-monitoring/alignak/develop)
[![Develop branch code coverage](https://img.shields.io/codecov/c/github/codecov/example-python/master.svg)](https://codecov.io/gh/Alignak-monitoring/alignak/branch/develop)

[![Read the Docs (stable)](https://img.shields.io/readthedocs/pip/stable.svg?label=doc-stable)](http://docs.alignak.net/en/master/)
[![Read the Docs (develop)](https://img.shields.io/readthedocs/pip/stable.svg?label=doc-develop)](http://docs.alignak.net/en/develop/)
[![Join the chat #alignak on freenode.net](https://img.shields.io/badge/IRC-%23alignak-1e72ff.svg?style=flat)](http://webchat.freenode.net/?channels=%23alignak)
[![Gitter](https://badges.gitter.im/Alignak-monitoring/alignak.svg)](https://gitter.im/Alignak-monitoring/alignak?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

[![License AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](http://www.gnu.org/licenses/agpl-3.0)


Alignak Project
---------------

[Alignak](http://www.alignak.net) is an open source monitoring framework written in Python under the terms of the [GNU Affero General Public License](http://www.gnu.org/licenses/agpl.txt).

Its main goal is to give users a flexible and complete solution for their monitoring system. Alignak is designed to scale to large and heterogeneous environments.

The project started in 2015 with a fork of the Shinken project. Since the project creation, we achieved a huge code documentation and cleaning, we tested the application in several environments and developed some new features.


The main idea when developing Alignak is the flexibility which is our definition of framework. We target the following goals:

   * Easy to install: we will always deliver packages (OS and Python) installation.
      You can install Alignak with OS packages, Python PIP apckages or *setup.py* directly..

   * Easy for new users: this documentation should help you to discover Alignak.
      This documentation shows simple use-cases and helps building more complex configurations.

   * Easy to migrate from Nagios: Nagios flat-files configuration and plugins will work with Alignak.
      We try to keep as much as possible an ascending compatibility with former Nagios configuration...

   * Multi-platform: python is available in a lot of Operating Systems.
      We try to write generic code to keep this possible. However, Linux and FreeBSD are the most tested OSes so far.
      As of now, Alignak is tested with Python 2.7, 3.5 and 3.6 versions but will work with Pypy in the future.

   * UTF-8 compliant: whatever you language, we take care of it.
      We are testing Alignak I/O with several languages and take care of localization.

   * Independent from other monitoring solution:
      Alignak is a framework that can integrate with other applications through standard interfaces.
      Flexibility first!

   * Flexible: in an architecture point of view.
      Alignak may be distributed across several servers, datacenters to suit the monitoring needs and constrints.
      It is our scalability wish!

   * Easy to contribute: contribution has to be an easy process.
      Alignak follow pycodestyle (former pep8), pylint and pep257 coding standards to ease code readability.
      Step by step help to contribute to the project can be found in the documentation.

This is basically what Alignak is made of. May be add the *keep it simple* Linux principle and it's perfect.

There is nothing we don't want, we consider every features / ideas. Feel free to join [by mail](mailto:contact@alignak.net) or on [the IRC #alignak channel](http://webchat.freenode.net/?channels=%23alignak) to discuss or ask for more information

Documentation
-------------

[Alignak Web Site ](http://www.alignak.net) includes much documentation and introduces the Alignak main features, such as the Backend, the WebUI, the desktop Applet, the tight integration with timeseries databases, ...

Alignak project has [an online documentation site](http://alignak-monitoring.github.io/documentation/). We try to have as much documentation as possible and to keep this documentation simple and understandable. For sure the documentation is not yet complete, but you can help us ;)

Click on one of the docs badges on this page to browse the documentation.


Requirements
------------

See the requirements file in the repository's root


Installing Alignak
------------------

Alignak Deb / Rpm packaging is built thanks to the bintray service. Get the package for your Linux distribution on our [packages repositories](https://bintray.com/alignak).

See the [installation documentation](https://alignak-doc.readthedocs.org/en/latest/02_installation/index.html) for more information on the different installation possibilities offered by Alignak.
