FROM python:3.6

LABEL maintainer="Frédéric Mohier (frederic.mohier@alignak.net)"

LABEL alignak.image_type="Generic"

ENV DEBIAN_FRONTEND noninteractive

# Force container timezone
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

RUN pip3 install --upgrade pip setuptools

# Location for the git repositories
RUN mkdir -p /repos

ARG ALIGNAK_GIT_REPO=alignak-monitoring/alignak
# Get the Alignak repository on develop branch
RUN echo https://github.com/$ALIGNAK_GIT_REPO
RUN cd /repos && \
    git clone https://github.com/$ALIGNAK_GIT_REPO && \
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

ENV ALIGNAK_SHARE_DIR=$ALIGNAK_SHARE_DIR
COPY ./entrypoint.sh /entrypoint.sh
RUN chown $ALIGNAK_USER:$ALIGNAK_GROUP /entrypoint.sh
RUN chmod 500 /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
# Run the arbiter in check mode for the configuration in the Alignak directory
CMD ["alignak-arbiter", "-V", "-e", "/repos/alignak/etc/alignak.ini" ]
