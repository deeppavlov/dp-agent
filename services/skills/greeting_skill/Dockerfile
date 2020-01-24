FROM python:3.7.4

RUN mkdir /src
COPY ./requirements.txt /src/requirements.txt
RUN pip install -r /src/requirements.txt

ARG SERVICE_NAME
ENV SERVICE_NAME ${SERVICE_NAME}

ARG SERVICE_PORT
ENV SERVICE_PORT ${SERVICE_PORT}

COPY . /src/
WORKDIR /src



CMD gunicorn --workers=2 server:app -b 0.0.0.0:${SERVICE_PORT} --reload
