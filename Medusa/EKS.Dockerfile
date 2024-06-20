
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
    && apt-get install unzip -y \
    && apt-get install tar -y 

# install aws cli
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install

# install eksctl
RUN curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp \
    && mv /tmp/eksctl /usr/local/bin/

# install kubectl
RUN curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# install terraform
RUN curl -LO "https://releases.hashicorp.com/terraform/1.4.6/terraform_1.4.6_linux_amd64.zip" \
    && unzip terraform_1.4.6_linux_amd64.zip \
    && mv terraform /usr/local/bin/

# Install Python dependencies for the Medusa framework.
RUN pip3 install -r requirements_backup_and_recovery.txt --default-timeout=300
