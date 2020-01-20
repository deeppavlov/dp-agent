FROM python:3.7.4

RUN mkdir /src
COPY ./requirements.txt /src/requirements.txt
RUN pip install -r /src/requirements.txt

ARG SKILL_NAME
ENV SKILL_NAME ${SKILL_NAME}

ARG SKILL_PORT
ENV SKILL_PORT ${SKILL_PORT}

COPY . /src/
WORKDIR /src



CMD gunicorn --workers=2 server:app -b 0.0.0.0:${SKILL_PORT}
