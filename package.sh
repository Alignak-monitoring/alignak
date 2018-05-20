#!/bin/sh

# --------------------------------------------------------------------------------
# This script is building packages for Alignak thanks to the fpm
# application (https://github.com/jordansissel/fpm)
# -----
# This script updates the .bintray.json file to update:
# - the target repo, replacing sed_version_repo with the appropriate
#  repository name: alignak-deb-testing or alignak-deb-stable
# - the version name, description and release date, replacing
#  sed_version_name, sed_version_desc and sed_version_released
# -----
# Using this script and fpm requires:
# sudo apt-get install ruby ruby-dev rubygems build-essential
# -----
# Command line parameters:
# git branch name:
# - master will build a stable version (alignak_deb-stable repository)
#   -> python-alignak_x.x.x_all.deb
# - develop will build a develop version (alignak_deb-testing repository)
#   -> python-alignak_x.x.x-dev_all.deb
# - any other will build a develop named version ((alignak_deb-testing repository))
#   -> python-alignak_x.x.x-dev-my_branch_all.deb
# python version:
# - 2.7, 3.5 (default)
# package type:
# - deb (default), rpm, freebsd, apk, pacman, ...
# Indeed all the package types supported by fpm
# --------------------------------------------------------------------------------
set -ev

# Parse command line arguments
# Default is branch develop, python 3.5
git_branch=$1
python_version=$2
output_type=$3
if [ $# -eq 0 ]; then
   git_branch="develop"
   python_version="3.5"
   output_type="deb"
fi
if [ $# -eq 1 ]; then
   python_version="3.5"
   output_type="deb"
fi
if [ $# -eq 2 ]; then
   output_type="deb"
fi

echo "Installing fpm..."
gem install --no-ri --no-rdoc fpm

echo "Building ${output_type} package for branch ${git_branch}, python version ${python_version}"

# Python prefix
python_prefix="python3"
if [ "${python_version}" = "2.7" ]; then
   python_prefix="python"
fi

# Package information
version=`python -c "from alignak import __version__;print(__version__)"`
version_date=`date "+%Y-%m-%d%"`

if [ "${git_branch}" = "master" ]; then
   # Updating deploy script for Alignak stable version
   sed -i -e "s|\"sed_version_name\"|\"${version}\"|g" .bintray.json
   sed -i -e "s|\"sed_version_name\"|\"Stable version\"|g" .bintray.json
   sed -i -e "s|\"sed_version_released\"|\"${version_date}\"|g" .bintray.json

   # Stable repo
   sed -i -e "s/sed_version_repo/alignak_deb-stable/g" .bintray.json
elif [ "${git_branch}" = "develop" ]; then
   # Updating deploy script for Alignak develop version
   sed -i -e "s|\"sed_version_name\"|\"${version_date}\"|g" .bintray.json
   sed -i -e "s|\"sed_version_name\"|\"Development version\"|g" .bintray.json
   sed -i -e "s|\"sed_version_released\"|\"${version_date}\"|g" .bintray.json

   # Testing repo
   sed -i -e "s/sed_version_repo/alignak_deb-testing/g" .bintray.json

   # Version
   version="${version}-dev"
else
   # Updating deploy script for any other branch / tag
   sed -i -e "s|\"sed_version_name\"|\"$1\"|g" .bintray.json
   sed -i -e "s|\"sed_version_name\"|\"Branch $1 version\"|g" .bintray.json
   sed -i -e "s|\"sed_version_released\"|\"${version_date}\"|g" .bintray.json

   # Version
   version="${version}-dev_${git_branch}"
fi

# Run fpm:
# - verbose mode to have information
# - from python to deb packages, for all architectures
# Use python dependencies - all Alignak python packages
# are packaged in the main distros so it will use the
# distro packages rather than the python one
# Use the python version as a prefix for the package name
fpm \
   --force \
   --input-type python \
   --output-type ${output_type} \
   --package "./bin" \
   --architecture all \
   --license AGPL \
   --version ${version} \
   --vendor "Alignak Team (contact@alignak.net)" \
   --maintainer "Alignak Team (contact@alignak.net)" \
   --python-package-name-prefix "${python_prefix}" \
   --python-scripts-executable "/usr/bin/python" \
   --python-install-lib "/usr/lib/python${python_version}/dist-packages" \
   --python-install-data '/usr/local' \
   --python-install-bin '/usr/local/bin' \
   --python-dependencies \
   --deb-systemd ./bin/systemd/alignak-arbiter@.service \
   --deb-systemd ./bin/systemd/alignak-broker@.service \
   --deb-systemd ./bin/systemd/alignak-poller@.service \
   --deb-systemd ./bin/systemd/alignak-reactionner@.service \
   --deb-systemd ./bin/systemd/alignak-receiver@.service \
   --deb-systemd ./bin/systemd/alignak-scheduler@.service \
   --deb-systemd ./bin/systemd/alignak.service \
   --deb-no-default-config-files \
   ./setup.py
