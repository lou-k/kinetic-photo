ARG PYTHON_VERSION="3.11.2"
FROM python:${PYTHON_VERSION}-slim-buster

WORKDIR /root

# Install the server package from source
COPY ./src /tmp/kinetic_server/src
COPY setup.cfg /tmp/kinetic_server/
COPY pyproject.toml /tmp/kinetic_server/
COPY MANIFEST.in /tmp/kinetic_server/
RUN cd /tmp/kinetic_server && \
    pip install . && \
    rm -rf /tmp/kinetic_server

COPY config.yml /etc/kinetic-photo/server/config.yml
RUN mkdir /var/kinetic-photo/