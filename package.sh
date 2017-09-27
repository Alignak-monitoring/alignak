#!/bin/sh

set -ev

cd ..
git clone https://github.com/Alignak-monitoring/alignak-packaging.git
sed -i -e 's/\/usr\/bin/\/usr\/local\/bin/g' alignak-packaging/alignak/systemd/*
sed -i -e 's/ \/etc\/alignak/ \/usr\/local\/etc\/alignak/g' alignak-packaging/alignak/systemd/*
cd alignak

gem install fpm

# Debian

if [ "$1" = "master" ]; then
   if [ "$2" = "2.7" ]; then
     fpm --debug -s python --python-scripts-executable "/usr/bin/python" --python-install-lib "/usr/lib/python2.7/dist-packages" -t deb -a all --python-disable-dependency pyopenssl --python-disable-dependency termcolor --python-disable-dependency CherryPy -d python-cherrypy3 -d python-openssl -d python-termcolor --deb-systemd ../alignak-packaging/alignak/systemd/alignak-arbiter.service --deb-systemd ../alignak-packaging/alignak/systemd/alignak-broker.service --deb-systemd ../alignak-packaging/alignak/systemd/alignak-poller.service --deb-systemd ../alignak-packaging/alignak/systemd/alignak-reactionner.service --deb-systemd ../alignak-packaging/alignak/systemd/alignak-receiver.service --deb-systemd ../alignak-packaging/alignak/systemd/alignak-scheduler.service --deb-systemd ../alignak-packaging/alignak/systemd/alignak.service --deb-no-default-config-files --python-install-data '/usr/local' --python-install-bin '/usr/local/bin' ./setup.py
     version=`python -c "from alignak import __version__;print(__version__)"`
   fi
   sed -i -e "s|\"dev\"|\"${version}\"|g" .bintray.json
   sed -i -e s/alignak_deb-testing/alignak_deb-stable/g .bintray.json
elif [ "$1" = "develop" ]; then
   DEVVERSION=`date "+%Y%m%d%H%M%S"`
   if [ "$2" = "2.7" ]; then
     fpm --debug -s python --python-scripts-executable "/usr/bin/python" --python-install-lib "/usr/lib/python2.7/dist-packages" -t deb -a all -v $DEVVERSION-dev --python-disable-dependency pyopenssl --python-disable-dependency termcolor --python-disable-dependency CherryPy -d python-cherrypy3 -d python-openssl -d python-termcolor --deb-systemd ../alignak-packaging/alignak/systemd/alignak-arbiter.service --deb-systemd ../alignak-packaging/alignak/systemd/alignak-broker.service --deb-systemd ../alignak-packaging/alignak/systemd/alignak-poller.service --deb-systemd ../alignak-packaging/alignak/systemd/alignak-reactionner.service --deb-systemd ../alignak-packaging/alignak/systemd/alignak-receiver.service --deb-systemd ../alignak-packaging/alignak/systemd/alignak-scheduler.service --deb-systemd ../alignak-packaging/alignak/systemd/alignak.service --deb-no-default-config-files --python-install-data '/usr/local' --python-install-bin '/usr/local/bin' ./setup.py
   fi
fi
