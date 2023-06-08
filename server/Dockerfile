ARG PYTHON_VERSION="3.11.2"
FROM python:${PYTHON_VERSION}-slim-buster

WORKDIR /root

RUN apt-get update && \
    apt-get install -y build-essential ffmpeg libmagic1 && \
    rm -rf /var/cache/apt /var/lib/apt/lists

# Install the server package from source
COPY ./src /tmp/kinetic_server/src
COPY setup.cfg /tmp/kinetic_server/
COPY pyproject.toml /tmp/kinetic_server/
COPY MANIFEST.in /tmp/kinetic_server/
RUN cd /tmp/kinetic_server && \
    pip install . && \
    rm -rf /tmp/kinetic_server

COPY config.yml /etc/kinetic-photo/server/config.yml
RUN mkdir -p /var/kinetic-photo/server/
CMD [ \
    "uwsgi", \
    "--socket", "0.0.0.0:8080", \
    "--protocol", "http", \
    "--wsgi", "kinetic_server.wsgi:app" ]