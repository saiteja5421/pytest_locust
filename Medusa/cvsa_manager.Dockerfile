ARG REGISTRY=cds-harbor.rtplab.nimblestorage.com
FROM ${REGISTRY}/docker_proxy/library/python:3.10.6-slim-buster

WORKDIR /Medusa

COPY . .

# 1. Install system dependencies for the Docker entrypoint.
# `curl` is required by the `cvsa_manager_docker_entrypoint.sh`.
RUN apt update && apt install -y curl
RUN apt install -y build-essential

# 2. Install python dependencies for the Medusa framework.
RUN pip3 install -r requirements_backup_and_recovery.txt

ENTRYPOINT ["/Medusa/cvsa_manager_docker_entrypoint.sh"]
