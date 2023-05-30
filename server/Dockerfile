ARG PYTHON_VERSION="3.11.2"
FROM python:${PYTHON_VERSION}-slim-buster

WORKDIR /root

# Install the server package from source
COPY . /tmp/kinetic_server
RUN cd /tmp/kinetic_server && \
    pip install . && \
    rm -rf /tmp/kinetic_server