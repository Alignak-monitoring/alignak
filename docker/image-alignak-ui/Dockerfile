FROM alignak/alignak:0.0.1

MAINTAINER Frédéric Mohier (frederic.mohier@alignak.net)

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get install -y --no-install-recommends \
    nginx \
    python3-pip \
    python3-dev \
    supervisor

RUN apt-get autoremove && apt-get clean

RUN pip3 install --upgrade pip setuptools

# Location for the git repositories
RUN mkdir -p /repos

# Get the Shinken / Alignak Web UI
RUN cd /repos && \
    git clone https://github.com/mohierf/mod-webui && \
    cd mod-webui && \
    git checkout python3 && \
    pip3 install -r requirements.txt && \
    pip3 install .

# Get the Shinken / Alignak Web UI Graphite extension module
RUN cd /repos && \
    git clone https://github.com/mohierf/mod-ui-graphite && \
    cd mod-ui-graphite && \
    git checkout alignak-python3 && \
    pip3 install -r requirements.txt && \
    pip3 install .

# Copy the Nginx global conf
COPY nginx.conf /etc/nginx/
# Copy the Flask Nginx site conf
COPY alignak-webui.conf /etc/nginx/conf.d/
# Custom Supervisord config
COPY supervisord.conf /etc/supervisord.conf

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]