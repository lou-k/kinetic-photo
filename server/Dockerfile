ARG PYTHON_VERSION="3.11.2"
FROM python:${PYTHON_VERSION}-slim-buster

WORKDIR /root

# Install python requirements
COPY Pipfile /tmp/
RUN pip install pipenv==2022.12.19 && \
    cd /tmp && \
    pipenv lock && \
    pipenv requirements > /tmp/requirements.txt && \
    pip install -r /tmp/requirements.txt && \
    pipenv --clear && \
    pip cache purge 

# Install the server package from source
COPY . /tmp/kinetic_server
RUN cd /tmp/kinetic_server && \
    pip install . && \
    rm -rf /tmp/kinetic_server