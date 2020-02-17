ARG PYTHON_BASE_VERSION

FROM python:${PYTHON_BASE_VERSION}

ARG PYTHON_BASE_VERSION
ARG ALIGNAK_IMAGE_TAG

ENV ALIGNAK_IMAGE_TAG $ALIGNAK_IMAGE_TAG
ENV PYTHON_BASE_VERSION $PYTHON_BASE_VERSION

LABEL maintainer="Frédéric Mohier (frederic.mohier@alignak.net)" \
      alignak.image_type="Generic" \
      alignak.image.version=$ALIGNAK_IMAGE_TAG \
      alignak.python.version=$PYTHON_BASE_VERSION

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

# Get the Alignak repository on develop branch
ARG ALIGNAK_GIT_REPO=alignak-monitoring/alignak
ARG ALIGNAK_GIT_BRANCH=develop
RUN cd /repos && \
    git clone https://github.com/$ALIGNAK_GIT_REPO && \
    cd alignak && \
    git checkout $ALIGNAK_GIT_BRANCH && \
    pip3 install -r requirements.txt && \
    pip3 install .

# Define some environment variables
ENV ALIGNAK_GROUP "alignak"
ENV ALIGNAK_USER  "alignak"

# Create alignak system user/group for Alignak application
# Note that the group is set a gid (1024), this to allow easy sharing with the Docker host
ARG ALIGNAK_SHARE_ID=1024
RUN groupadd --system --gid $ALIGNAK_SHARE_ID $ALIGNAK_GROUP
RUN useradd --system $ALIGNAK_USER --uid $ALIGNAK_SHARE_ID --gid $ALIGNAK_SHARE_ID

# Create the shared directory if it does not exist and set proper credentials
ARG ALIGNAK_SHARE_DIR=/alignak
RUN mkdir -p $ALIGNAK_SHARE_DIR
RUN chown $ALIGNAK_USER:$ALIGNAK_GROUP $ALIGNAK_SHARE_DIR
RUN chmod -R 775 $ALIGNAK_SHARE_DIR

# Run as the newly created user
#USER $ALIGNAK_USER

# Run the arbiter in check mode for the configuration in the Alignak directory
CMD ["alignak-arbiter", "-V", "-e", "/alignak/etc/alignak.ini" ]
