FROM hub.docker.hpecorp.net/atlas-qa/e2e-catalyst-gw-mgr:latest

RUN apt-get update && \
    apt-get -qy full-upgrade && \
    apt-get install -qy openssh-server && \
    apt-get install -qy openjdk-11-jdk && \
    apt-get install -qy diffutils jq && \
    apt-get -qy autoremove && \
    sed -i 's|session    required     pam_loginuid.so|session    optional     pam_loginuid.so|g' /etc/pam.d/sshd && \
    mkdir -p /var/run/sshd && \
    adduser --disabled-password --gecos "" jenkins && \
    echo "jenkins:jenkins" | chpasswd

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
