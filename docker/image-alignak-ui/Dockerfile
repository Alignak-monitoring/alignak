ARG ALIGNAK_IMAGE_TAG

FROM alignak/alignak:${ALIGNAK_IMAGE_TAG}

ARG ALIGNAK_IMAGE_TAG

ENV ALIGNAK_IMAGE_TAG $ALIGNAK_IMAGE_TAG

LABEL maintainer="Frédéric Mohier (frederic.mohier@alignak.net)" \
      alignak.image_type="UI" \
      alignak.image.version=$ALIGNAK_IMAGE_TAG \
      alignak.python.version=$PYTHON_BASE_VERSION

ENV DEBIAN_FRONTEND noninteractive

# Run as the root user
USER root

RUN apt-get install -y --no-install-recommends \
    nginx \
    supervisor

RUN apt-get autoremove && apt-get clean

#RUN pip3 install --upgrade pip setuptools

# Location for the git repositories
RUN mkdir -p /repos

# Location for the external Shinken modules
RUN mkdir -p /shinken_modules

# Get the Shinken / Alignak Web UI
RUN pwd
ARG SHINKEN_WEBUI_VERSION
RUN cd /repos && \
    git clone https://github.com/mohierf/mod-webui && \
    cd mod-webui && \
    git checkout ${SHINKEN_WEBUI_VERSION} && \
    pip3 install -r requirements.txt

# Shoud be installable, but :/
#    pip3 install .
RUN cd /repos && \
    cd mod-webui && ls -alht && \
    mkdir -p /shinken_modules/alignak_webui && \
    cp -R module/* /shinken_modules/alignak_webui/

# Get the Shinken / Alignak Web UI Graphite extension module
RUN cd /repos && \
    git clone https://github.com/mohierf/mod-ui-graphite && \
    cd mod-ui-graphite && \
    git checkout develop && \
    pip3 install -r requirements.txt

# Shoud be installable, but :/
#    pip3 install .
# Note that this module is installable with pip install but we copy as for the main Web UI !
RUN cd /repos && \
    cd mod-ui-graphite && ls -alht && \
    mkdir -p /shinken_modules/alignak_webui_graphite && \
    cp -R alignak_webui_graphite/* /shinken_modules/alignak_webui_graphite/

# Define some environment variables
ENV ALIGNAK_GROUP "alignak"
ENV ALIGNAK_USER  "alignak"

# Run as the newly created user
#USER $ALIGNAK_USER

# Copy the Nginx global conf
COPY nginx.conf /etc/nginx/
# Copy the Flask Nginx site conf
COPY alignak-webui.conf /etc/nginx/conf.d/
# Custom Supervisord config
COPY supervisord.conf /etc/supervisord.conf

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]