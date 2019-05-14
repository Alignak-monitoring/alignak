FROM python:3.6

MAINTAINER Frédéric Mohier

ENV DEBIAN_FRONTEND noninteractive

# Fix container timezone
RUN ln -fs /usr/share/zoneinfo/Europe/Paris /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

RUN apt-get update

# Install base required packages
RUN apt-get install -y --no-install-recommends \
    nagios-plugins \
    nagios-nrpe-plugin \
    nagios-snmp-plugins \
    python3-pip

RUN apt-get autoremove && apt-get clean

# Location for the git repositories
RUN mkdir -p /repos

# Get the Alignak repository on develop branch
RUN cd /repos && \
    git clone https://github.com/alignak-monitoring/alignak && \
    cd alignak && \
    git checkout develop && \
    pip3 install -r requirements.txt && \
    pip3 install .

# Define some environment variables
ENV ALIGNAK_GROUP "alignak"
ENV ALIGNAK_USER  "alignak"

# Create alignak system user/group for Alignak application
# Note that the group is set a gid (1024), this to allow easy sharing with the doker host
ARG ALIGNAK_SHARE_ID=1024
RUN groupadd --system --gid $ALIGNAK_SHARE_ID $ALIGNAK_GROUP
RUN useradd --system $ALIGNAK_USER --uid $ALIGNAK_SHARE_ID --gid $ALIGNAK_SHARE_ID

# Create a share directory
ARG ALIGNAK_SHARE_DIR=/alignak
RUN mkdir -p $ALIGNAK_SHARE_DIR

RUN chown -R $ALIGNAK_USER:$ALIGNAK_GROUP $ALIGNAK_SHARE_DIR
RUN chmod -R 775 $ALIGNAK_SHARE_DIR

CMD ["alignak-arbiter", "-V", "-e", "/repos/alignak/etc/alignak.ini" ]