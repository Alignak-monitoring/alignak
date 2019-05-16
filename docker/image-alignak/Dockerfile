FROM python:3.6

LABEL maintainer="Frédéric Mohier (frederic.mohier@alignak.net)"

LABEL alignak.image_type="Generic"

ENV DEBIAN_FRONTEND noninteractive

# Force container timezone
RUN ln -fs /usr/share/zoneinfo/Europe/Paris /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# Install base required packages
RUN apt-get update

RUN apt-get install -y --no-install-recommends \
    nagios-plugins \
    nagios-nrpe-plugin \
    nagios-snmp-plugins \
    python3-pip

RUN apt-get autoremove && apt-get clean

RUN pip3 install --upgrade pip setuptools

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

# Create alignak system user/group for Alignak application#
# Note that the group is set a gid (1024), this to allow easy sharing with the doker host
ARG ALIGNAK_SHARE_ID=1024
RUN groupadd --system --gid $ALIGNAK_SHARE_ID $ALIGNAK_GROUP
RUN useradd --system $ALIGNAK_USER --uid $ALIGNAK_SHARE_ID --gid $ALIGNAK_SHARE_ID

# Create a share directory and set proper credentials
ARG ALIGNAK_SHARE_DIR=/alignak
RUN mkdir -p $ALIGNAK_SHARE_DIR
RUN chown $ALIGNAK_USER:$ALIGNAK_GROUP $ALIGNAK_SHARE_DIR
RUN chmod -R 775 $ALIGNAK_SHARE_DIR

# Run as the newly created user
#USER $ALIGNAK_USER

# Default is to run the Alignak arbiter in check mode for the default shipped configuration
CMD ["alignak-arbiter", "-V", "-e", "/repos/alignak/etc/alignak.ini" ]