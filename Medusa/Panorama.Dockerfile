FROM python:3.9-slim-buster

ENV http_proxy "http://hpeproxy.its.hpecorp.net:443"
ENV https_proxy "http://hpeproxy.its.hpecorp.net:443"
ENV no_proxy "127.0.0.1,localhost,.nimblestorage.com,10.0.0.0/8,192.0.0.0/8,172.0.0.0/8,10.226.67.255,10.157.93.253,.pqaftc.hpe.com,ftcpqa.hpe.com"


COPY panorama.requirements.txt requirements_backup_and_recovery.txt requirements_dev.txt /tmp/

RUN apt update \
    && apt install iputils-ping -y \
    && apt install default-jdk -y \
    && apt install curl -y \
    && apt install jq -y \
    && apt install python3-tk -y


RUN pip3 install -r /tmp/requirements_backup_and_recovery.txt \
    && pip3 install -r /tmp/panorama.requirements.txt 


WORKDIR /Medusa
