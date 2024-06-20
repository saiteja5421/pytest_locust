FROM python:3.10-slim-buster

ENV http_proxy "http://hpeproxy.its.hpecorp.net:443"
ENV https_proxy "http://hpeproxy.its.hpecorp.net:443"
ENV no_proxy "127.0.0.1,localhost,.nimblestorage.com,10.0.0.0/8,192.0.0.0/8,172.0.0.0/8,10.226.67.255,10.157.93.69"
ENV NO_PROXY "127.0.0.1,localhost,.nimblestorage.com,10.0.0.0/8,192.0.0.0/8,172.0.0.0/8,10.226.67.255,10.157.93.69"
ENV PYTHONPATH "${PYTHONPATH}:/workspaces/Squid/"


COPY requirements.txt /tmp/ 
COPY requirements_backup_and_recovery.txt /tmp/

RUN cd /tmp

RUN apt-get update \
    && apt-get install iputils-ping -y \
    && apt-get install git -y \
    && apt-get install curl -y \
    && apt-get install jq -y \
    && apt-get install build-essential -y

RUN pip3 install -r /tmp/requirements.txt \
    && pip3 install -r /tmp/requirements_backup_and_recovery.txt

WORKDIR /Squid/


