#!/bin/sh

# --------------------------------------------------------------------------------
# This script is doing the post-install processing for Alignak application:
# - checking and creating alignak:alignak user account
# - installing the python dependencies for Alignak.
# -----
# Command line parameters may be used to change the default 'alignak'
# user account and the default '/usr/local' prefix
# --------------------------------------------------------------------------------
# Default is to use an alignak account
ACCOUNT=$1
# Default is to use /usr/local prefix
PREFIX=$2
# Parse command line arguments
if [ $# -eq 0 ]; then
    ACCOUNT="alignak"
    PREFIX="/usr/local"
fi
if [ $# -eq 1 ]; then
   # Yum installer calls the post-installation script with "1"
   # for an initial installation oe "2" for an upgrade
   if [ "$1" -eq "1" ]; then
       ACCOUNT="alignak"
       PREFIX="/usr/local"
   fi
   if [ "$1" -eq "2" ]; then
       ACCOUNT="alignak"
       PREFIX="/usr/local"
   fi
    PREFIX="/usr/local"
fi

echo "-----"
echo "Alignak post-install"
echo "User account: $ACCOUNT"
echo "Installation prefix: $PREFIX"
echo "-----"

echo "Detecting OS platform"
platform='unknown'
unamestr=`uname`
echo "-> system is: $unamestr"
if [ "$unamestr" = 'Linux' ]; then
   platform='linux'
elif [ "$unamestr" = 'FreeBSD' ]; then
   platform='freebsd'
fi
echo "-> found ${platform}"

echo "Checking / creating '$ACCOUNT' user and users group"
if id "$ACCOUNT" >/dev/null 2>&1; then
   echo "User $ACCOUNT still exists"
else
   echo "User $ACCOUNT does not exist, trying to create..."
   if [ "$platform" = 'linux' ]; then
      ## Create user and group
      echo "Creating '$ACCOUNT' user and users group"
      useradd $ACCOUNT --system --no-create-home --user-group -c "Alignak daemons user"
   elif [ "$platform" = 'freebsd' ]; then
      ## Create user and group
      echo "Creating '$ACCOUNT' user and users group"
      pw adduser $ACCOUNT -d /nonexistent -s /usr/sbin/nologin -c "Alignak daemons user"
   fi
fi

echo "Detecting Python version"
pyver=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:1])))') 2> /dev/null
if [ $? -eq 0 ]
then
    pyver=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))') 2> /dev/null
    echo "Python 3 ($pyver) detected"
    exe_pip=$(pip3 --version) 2> /dev/null
    if [ $? -eq 0 ]
    then
        echo "Installing python 3 packages dependencies from requirements.txt..."
        sudo pip3 install -r $PREFIX/share/alignak/requirements.txt
        echo "Installed."
    else
        echo "pip3 is not available. You can install it by typing: sudo apt install python3-pip"
        echo "You can then run: sudo $PREFIX/share/alignak/python3-post-install.sh"
        exit 1
    fi
else
    echo "Python 3 is not installed, exiting."
    exit 1
fi

echo "Creating some necessary directories"
mkdir -p $PREFIX/var/run/alignak
chown -R $ACCOUNT:$ACCOUNT $PREFIX/var/run/alignak
chmod -R 775 $PREFIX/var/run/alignak
echo "$ACCOUNT user and members of its group $ACCOUNT are granted 775 on $PREFIX/var/run/alignak"
mkdir -p $PREFIX/var/log/alignak
chown -R $ACCOUNT:$ACCOUNT $PREFIX/var/log/alignak
echo "$ACCOUNT user and members of its group $ACCOUNT are granted 775 on $PREFIX/var/log/alignak"
chmod -R 775 $PREFIX/var/log/alignak
echo "Add your own user account as a member of $ACCOUNT group to run daemons from your shell!"
echo "Created."

echo "Installing log rotation script"
cp $PREFIX/share/alignak/alignak-log-rotate /etc/logrotate.d/alignak
echo "Installed."
