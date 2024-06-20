ARG REGISTRY=cds-harbor.rtplab.nimblestorage.com
FROM ${REGISTRY}/docker_proxy/library/python:3.10.7-slim-buster

ENV http_proxy "http://hpeproxy.its.hpecorp.net:443"
ENV https_proxy "http://hpeproxy.its.hpecorp.net:443"
ENV no_proxy "127.0.0.1,localhost,.nimblestorage.com,10.0.0.0/8,192.0.0.0/8,172.0.0.0/8,10.226.67.255,10.157.93.253,.pqaftc.hpe.com"

WORKDIR /Medusa

COPY . .

RUN apt-get update \
    && apt-get install iputils-ping -y \
    && apt-get install git -y \
    && apt-get install curl -y \
    && apt-get install wget -y \
    && apt-get install gcc -y \
    && apt-get install jq -y \
    && apt-get install unzip -y \
    && apt-get install zip -y

# Install RDS DB dependencies for Oracle DB
RUN chmod +x requirements_rds.sh
RUN ./requirements_rds.sh

# Install Python dependencies for the Medusa framework.
RUN pip3 install -r requirements_backup_and_recovery.txt --default-timeout=300
RUN pip3 install -r requirements_rds.txt --default-timeout=300
# To Install following package on your local environment, update github_username and github_access_token with your git username and access token
RUN pip3 install git+https://<github_username>:<github_access_token>@github.hpe.com/dcs-bristol/ms365-checksum-tool.git

RUN export LD_LIBRARY_PATH=/opt/oracle/instantclient_21_9
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_21_9
