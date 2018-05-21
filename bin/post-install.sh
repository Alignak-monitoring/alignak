#!/bin/sh

# --------------------------------------------------------------------------------
# This script is doing the post-install processins for Alignak application:
# - installing the python dependencies for Alignak.
# -----
#
# --- -----------------------------------------------------------------------------
#set -ev

echo "Installing python packages dependencies from requirements.txt..."
sudo pip install -r /usr/local/share/alignak/requirements.txt
echo "Installed."