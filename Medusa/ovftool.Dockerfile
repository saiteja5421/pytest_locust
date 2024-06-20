FROM python:3.9-slim-buster

WORKDIR /Medusa

COPY . .

ENV http_proxy "http://hpeproxy.its.hpecorp.net:443"
ENV https_proxy "http://hpeproxy.its.hpecorp.net:443"
ENV no_proxy "127.0.0.1,localhost,.nimblestorage.com"

RUN apt update && \
	apt install -y wget libncursesw5

RUN wget http://cxo-lin-126.cxo.storage.hpecorp.net/ovftool/ovftool-4.4.3-18663434.tar.gz && \
	tar -xvf ovftool-4.4.3-18663434.tar.gz && \
	chmod +x ./VMware-ovftool-4.4.3-18663434-lin.x86_64.bundle && \
	yes | env PAGER=cat ./VMware-ovftool-4.4.3-18663434-lin.x86_64.bundle --console && \
	rm -f VMware-ovftool-4.3.0-7948156-lin.x86_64.bundle ovftool-4.4.3-18663434.tar.gz

RUN pip3 install -r requirements_backup_and_recovery.txt