FROM python:2.7

MAINTAINER Frédéric Mohier

ENV DEBIAN_FRONTEND noninteractive

# Fix container timezone
RUN ln -fs /usr/share/zoneinfo/Europe/Paris /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# Install base required packages
RUN apt-get update

RUN apt-get install -y --no-install-recommends \
    nagios-plugins \
    nagios-nrpe-plugin \
    nginx \
    python-pip

RUN apt-get autoremove && apt-get clean

# Location for the git repositories
RUN mkdir -p /repos

# Get the Alignak repository on develop branch
RUN cd /repos && \
    git clone https://github.com/alignak-monitoring/alignak && \
    cd alignak && \
    git checkout daemon_log_level && \
    pip install -r requirements.txt && \
    pip install .

# Get the Shinken / Alignak Web UI
RUN mkdir /usr/local/lib/python2.7/site-packages/alignak_webui
RUN cd /repos && \
    git clone https://github.com/mohierf/mod-webui && \
    cd mod-webui && \
    git checkout python3 && \
    pip install -r requirements.txt && \
    pip install .

# RUN pip install bottle pycurl pymongo arrow

# RUN apt-get install -y --no-install-recommends python-bottle python-pycurl python-pymongo

# For the Web UI modules
RUN mkdir -p /var/lib/shinken/modules

# Define some environment variables
ENV ALIGNAK_GROUP "alignak"
ENV ALIGNAK_USER  "alignak"

# Create alignak system user/group for Alignak application#
# Note that the group is set a gid (1024), this to allow easy sharing with the doker host
ARG ALIGNAK_SHARE_ID=1024
RUN groupadd --system --gid $ALIGNAK_SHARE_ID $ALIGNAK_GROUP
RUN useradd --system $ALIGNAK_USER --uid $ALIGNAK_SHARE_ID --gid $ALIGNAK_SHARE_ID

# Create a share directory
ARG ALIGNAK_SHARE_DIR=/alignak
RUN mkdir -p $ALIGNAK_SHARE_DIR

## Create a configuration directory
#ARG ALIGNAK_ETC_DIR=/alignak/etc
#RUN mkdir -p $ALIGNAK_ETC_DIR
#
## Create a log directory
#ARG ALIGNAK_LOG_DIR=/alignak/log
#RUN mkdir -p $ALIGNAK_LOG_DIR
#
## Create a working directory
#ARG ALIGNAK_RUN_DIR=/alignak/run
#RUN mkdir -p $ALIGNAK_RUN_DIR

RUN chown $ALIGNAK_USER:$ALIGNAK_GROUP $ALIGNAK_SHARE_DIR
RUN chmod -R 775 $ALIGNAK_SHARE_DIR

# Define some environment variables
ENV ALIGNAK_GROUP "alignak"
ENV ALIGNAK_USER  "alignak"

# Create alignak system user/group for Alignak application#
# Note that the group is set a gid (1024), this to allow easy sharing with the doker host
ARG ALIGNAK_SHARE_ID=1024
RUN groupadd --system --gid $ALIGNAK_SHARE_ID $ALIGNAK_GROUP
RUN useradd --system $ALIGNAK_USER --uid $ALIGNAK_SHARE_ID --gid $ALIGNAK_SHARE_ID

# Create a share directory
ARG ALIGNAK_SHARE_DIR=/alignak
RUN mkdir -p $ALIGNAK_SHARE_DIR

## Create a configuration directory
#ARG ALIGNAK_ETC_DIR=/alignak/etc
#RUN mkdir -p $ALIGNAK_ETC_DIR
#
## Create a log directory
#ARG ALIGNAK_LOG_DIR=/alignak/log
#RUN mkdir -p $ALIGNAK_LOG_DIR
#
## Create a working directory
#ARG ALIGNAK_RUN_DIR=/alignak/run
#RUN mkdir -p $ALIGNAK_RUN_DIR

RUN chown $ALIGNAK_USER:$ALIGNAK_GROUP $ALIGNAK_SHARE_DIR
RUN chmod -R 775 $ALIGNAK_SHARE_DIR

USER $ALIGNAK_USER

## Install shinken modules from shinken.io
#RUN chown -R $ALIGNAK_USER:$ALIGNAK_GROUP /etc/shinken/ && \
#    su - shinken -c 'shinken --init' && \
#    su - shinken -c 'shinken install graphite2' && \
#    su - shinken -c 'shinken install ui-graphite2'
#
# Run the arbiter in check mode for the configuration in the Alignak directory
CMD ["alignak-arbiter", "-V", "-e", "/repos/alignak/etc/alignak.ini" ]