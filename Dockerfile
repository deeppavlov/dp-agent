FROM ubuntu:latest

RUN apt-get update -y --fix-missing && \
    apt-get install -y python3 python3-pip python3-dev build-essential git openssl

ENV PYTHONIOENCODING=utf-8
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONPATH "${PYTONPATH}:/dp-agent"

COPY requirements.txt /
RUN pip3 install -r requirements.txt

RUN mkdir dp-agent
WORKDIR /dp-agent
COPY . /dp-agent/.
VOLUME /dp-agent/core/config.yaml

ENTRYPOINT python3.6 core/run.py agent
    #CMD_STR = "python3.6 /dp-agent/core/run.py " && \
    #CMD_STR=$CMD_STR" "$MODE" " && \
    #if [ $MODE = "service" ]; then CMD_STR=$CMD_STR" -n "$SERVICE_NAME" "; fi && \
    #if [ ! -z $INSTANCE_ID ]; then CMD_STR=$CMD_STR; fi && \
    #python3.6 /dp-agent/run.py service -n $SERVICE_NAME --config $CONFIG_PATH