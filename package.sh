#!/bin/sh

# --------------------------------------------------------------------------------
# This script is building packages for Alignak thanks to the fpm
# application (https://github.com/jordansissel/fpm).
# -----
# Using this script and fpm requires:
# sudo apt-get install ruby ruby-dev rubygems build-essential
#  sudo gem install --no-ri --no-rdoc fpm
# -----
# This script updates the .bintray-*.json file to update:
# - the target repo, replacing sed_version_repo with the appropriate
#  repository name: alignak-deb-testing or alignak-deb-stable
# - the version name, description and release date, replacing
#  sed_version_name, sed_version_desc and sed_version_released
# -----
# Command line parameters:
# - git branch name:
# - master will build a stable version (alignak_deb-stable repository)
#   -> python-alignak_x.x.x_all.deb
# - develop will build a develop version (alignak_deb-testing repository)
#   -> python-alignak_x.x.x-dev_all.deb
# - any other will build a develop named version (alignak_deb-testing repository)
#   -> python-alignak_x.x.x-mybranch_all.deb
#
# Note that it is not recommended to use anything else than alphabetic characters in the
# branch name according to the debian version name policy! Else, the package will not even
# install on the system!
#
# - python version:
#   2.7, 3.5 (default)
#
# - package type:
#   deb (default), rpm, freebsd, apk, pacman, ...
# Indeed all the package types supported by fpm
# --------------------------------------------------------------------------------
#set -ev

# Parse command line arguments
# Default is branch develop, python 3.5
git_branch=$1
python_version=$2
input_type="python"
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

# Python prefix - no more used but kept for compatibility
python_prefix="python3"
if [ "${python_version}" = "2.7" ]; then
   python_prefix="python"
fi

# Package information - no more python-prefix but kept for compatibility
pkg_name="alignak"
if [ "${python_version}" = "2.7" ]; then
   pkg_name="alignak"
fi
pkg_description="Alignak, modern Nagios compatible monitoring framework"
pkg_url="http://alignak.net"
pkg_team="Alignak Team (contact@alignak.net)"

version=`python -c "from alignak import __version__;print(__version__)"`
version_date=`date "+%Y-%m-%d"`

if [ "${git_branch}" = "master" ]; then
   # Updating deploy script for Alignak stable version
   sed -i -e "s|\"sed_version_name\"|\"${version}\"|g" .bintray-${output_type}.json
   sed -i -e "s|\"sed_version_desc\"|\"Stable version\"|g" .bintray-${output_type}.json
   sed -i -e "s|\"sed_version_released\"|\"${version_date}\"|g" .bintray-${output_type}.json

   # Stable repo
   if [ "${output_type}" = "deb" ]; then
      sed -i -e "s/sed_version_repo/alignak-deb-stable/g" .bintray-${output_type}.json
   else
      sed -i -e "s/sed_version_repo/alignak-rpm-stable/g" .bintray-${output_type}.json
   fi
elif [ "${git_branch}" = "develop" ]; then
   # Updating deploy script for Alignak develop version
   sed -i -e "s|\"sed_version_name\"|\"${version_date}\"|g" .bintray-${output_type}.json
   sed -i -e "s|\"sed_version_desc\"|\"Development version\"|g" .bintray-${output_type}.json
   sed -i -e "s|\"sed_version_released\"|\"${version_date}\"|g" .bintray-${output_type}.json

   # Testing repo
   if [ "${output_type}" = "deb" ]; then
      sed -i -e "s/sed_version_repo/alignak-deb-testing/g" .bintray-${output_type}.json
   else
      sed -i -e "s/sed_version_repo/alignak-rpm-testing/g" .bintray-${output_type}.json
   fi

   # Version
   version="${version}-dev"
else
   # Updating deploy script for any other branch / tag
   sed -i -e "s|\"sed_version_name\"|\"$1\"|g" .bintray-${output_type}.json
   sed -i -e "s|\"sed_version_desc\"|\"Branch $1 version\"|g" .bintray-${output_type}.json
   sed -i -e "s|\"sed_version_released\"|\"${version_date}\"|g" .bintray-${output_type}.json

   # Testing repo
   if [ "${output_type}" = "deb" ]; then
      sed -i -e "s/sed_version_repo/alignak-deb-testing/g" .bintray-${output_type}.json
   else
      sed -i -e "s/sed_version_repo/alignak-rpm-testing/g" .bintray-${output_type}.json
   fi

   # Version
   version="${version}-${git_branch}"
fi

# Run fpm:
# Add --verbose for a verbose (very...) mode to have more information
# - from python to deb packages, for all architectures
# Use python dependencies - all Alignak python packages
# are packaged in the main distros so it will use the
# distro packages rather than the python one
echo "Running fpm..."
if [ "${output_type}" = "deb" ]; then
   fpm \
      --force \
      --input-type ${input_type} \
      --output-type ${output_type} \
      --package "./bin" \
      --architecture all \
      --license AGPL \
      --version ${version} \
      --name "${pkg_name}" \
      --description "${pkg_description}" \
      --url "${pkg_url}" \
      --vendor "${pkg_team}" \
      --maintainer "${pkg_team}" \
      --python-scripts-executable "/usr/bin/python" \
      --python-install-lib "/usr/lib/python${python_version}/dist-packages" \
      --python-install-data '/usr/local' \
      --python-install-bin '/usr/local/bin' \
      --no-python-dependencies \
      --after-install './bin/post-install.sh' \
      --deb-no-default-config-files \
      --deb-systemd ./bin/systemd/alignak-arbiter@.service \
      --deb-systemd ./bin/systemd/alignak-broker@.service \
      --deb-systemd ./bin/systemd/alignak-poller@.service \
      --deb-systemd ./bin/systemd/alignak-reactionner@.service \
      --deb-systemd ./bin/systemd/alignak-receiver@.service \
      --deb-systemd ./bin/systemd/alignak-scheduler@.service \
      --deb-systemd ./bin/systemd/alignak.service \
      --deb-no-default-config-files \
      ./setup.py
elif [ "${output_type}" = "rpm" ]; then
   fpm \
      --force \
      --input-type ${input_type} \
      --output-type ${output_type} \
      --package "./bin" \
      --architecture all \
      --license AGPL \
      --version ${version} \
      --name "${pkg_name}" \
      --description "${pkg_description}" \
      --url "${pkg_url}" \
      --vendor "${pkg_team}" \
      --maintainer "${pkg_team}" \
      --python-scripts-executable "/usr/bin/python" \
      --python-install-lib "/usr/lib/python${python_version}/dist-packages" \
      --python-install-data '/usr/local' \
      --python-install-bin '/usr/local/bin' \
      --python-dependencies \
      --after-install './bin/post-install.sh' \
      ./setup.py
else
   fpm \
      --force \
      --input-type ${input_type} \
      --output-type ${output_type} \
      --package "./bin" \
      --architecture all \
      --license AGPL \
      --version ${version} \
      --name "${pkg_name}" \
      --description "${pkg_description}" \
      --url "${pkg_url}" \
      --vendor "${pkg_team}" \
      --maintainer "${pkg_team}" \
      --python-scripts-executable "/usr/bin/python" \
      --python-install-lib "/usr/lib/python${python_version}/dist-packages" \
      --python-install-data '/usr/local' \
      --python-install-bin '/usr/local/bin' \
      --python-dependencies \
      ./setup.py
fi