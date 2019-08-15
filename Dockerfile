FROM ubuntu:18.04

RUN apt-get update -y --fix-missing && \
    apt-get install -y python3 python3-pip python3-dev build-essential git openssl

ENV PYTHONIOENCODING=utf-8
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

RUN mkdir dp-agent
WORKDIR /dp-agent
COPY . /dp-agent/.

RUN pip3 install -r requirements.txt && \
    python3 setup.py develop

VOLUME /dp-agent/config.yaml

CMD if [ -z $CONFIG ] || [ $CONFIG = "" ]; then CONFIG="/dp-agent/config.yaml"; fi && \
    if [ ! -f $CONFIG ]; then CONFIG="/dp-agent/core/config.yaml"; fi && \
    ARG_SERVICE="" ; if [ ! -z $SERVICE_NAME ]; then ARG_SERVICE="-n "$SERVICE_NAME; fi && \
    ARG_INSTANCE="" ; if [ ! -z $INSTANCE_ID ]; then ARG_INSTANCE="-i "$INSTANCE_ID; fi && \
    python3 /dp-agent/core/run.py $MODE --config $CONFIG $ARG_SERVICE $ARG_INSTANCE
