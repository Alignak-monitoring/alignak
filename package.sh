#!/bin/sh

set -ev

echo "Installing fpm..."
gem install --no-ri --no-rdoc fpm

echo "Building packages for branch $1, python version $2"

# Get Alignak version
version=`python -c "from alignak import __version__;print(__version__)"`

name = "Alignak"
version_date=`date "+%Y-%m-%d%"`

# Debian
if [ "$1" = "master" ]; then
   # Updating deploy script for Alignak stable version
   sed -i -e "s|\"sed_version_name\"|\"${version}\"|g" .bintray.json
   sed -i -e "s|\"sed_version_name\"|\"Stable version\"|g" .bintray.json
   sed -i -e "s|\"sed_version_released\"|\"${version_date}\"|g" .bintray.json

   # Stable repo
   sed -i -e s/alignak_deb-testing/alignak_deb-stable/g .bintray.json
elif [ "$1" = "develop" ]; then
   # Updating deploy script for Alignak develop version
   sed -i -e "s|\"sed_version_name\"|\"${version date}\"|g" .bintray.json
   sed -i -e "s|\"sed_version_name\"|\"Development version\"|g" .bintray.json
   sed -i -e "s|\"sed_version_released\"|\"${version_date}\"|g" .bintray.json
else
   # Updating deploy script for any other branch / tag
   sed -i -e "s|\"sed_version_name\"|\"$1\"|g" .bintray.json
   sed -i -e "s|\"sed_version_name\"|\"Branch $1 version\"|g" .bintray.json
   sed -i -e "s|\"sed_version_released\"|\"${version_date}\"|g" .bintray.json
fi

# Run fpm:
# - verbose mode to have information
# - from python to deb packages, for all
fpm --verbose -s python -t deb -p "./bin" -a all \
   --licence AGPL
   --vendor "Alignak Team (contact@alignak.net)" \
   --maintainer "Alignak Team (contact@alignak.net)" \
   --python-scripts-executable "/usr/bin/python" \
   --python-install-lib "/usr/lib/python2.7/dist-packages" \
   --python-install-data '/usr/local' \
   --python-install-bin '/usr/local/bin' \
   --python-disable-dependency pyopenssl \
   --python-disable-dependency termcolor \
   --python-disable-dependency CherryPy \
   --depends python-cherrypy3 \
   --depends python-openssl \
   --depends python-termcolor \
   --deb-systemd ./bin/systemd/alignak-arbiter@.service \
   --deb-systemd ./bin/systemd/alignak-broker@.service \
   --deb-systemd ./bin/systemd/alignak-poller@.service \
   --deb-systemd ./bin/systemd/alignak-reactionner@.service \
   --deb-systemd ./bin/systemd/alignak-receiver@.service \
   --deb-systemd ./bin/systemd/alignak-scheduler@.service \
   --deb-systemd ./bin/systemd/alignak.service \
   --deb-no-default-config-files ./setup.py
