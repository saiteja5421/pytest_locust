ARG REGISTRY=cds-harbor.rtplab.nimblestorage.com
FROM ${REGISTRY}/docker_proxy/library/python:3.10.7-slim-buster

WORKDIR /Medusa

COPY . .

# Install system dependencies for the Docker entrypoint.
RUN apt-get update \
    && apt-get install iputils-ping -y \
    && apt-get install git -y \
    && apt-get install curl -y \
    && apt-get install wget -y \
    && apt-get install gcc -y \
    && apt-get install zip -y \
    && apt-get install unzip -y \
    && apt-get install jq -y \
    && apt-get install sshpass \
    && apt-get install build-essential -y

# Install RDS DB dependencies for MariaDB and Oracle DB
RUN chmod +x requirements_rds.sh
RUN ./requirements_rds.sh

# Install Python dependencies for the Medusa framework.
RUN pip3 install -r requirements_backup_and_recovery.txt --default-timeout=300
RUN pip3 install -r requirements_rds.txt --default-timeout=300

RUN export LD_LIBRARY_PATH=/opt/oracle/instantclient_21_9
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_21_9

ENTRYPOINT ["/Medusa/medusa_backup_and_recovery_entrypoint.sh"]
