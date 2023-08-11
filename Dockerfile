FROM cr.yandex/mirror/ubuntu:22.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -yqq update && \
    apt-get -yqq upgrade && \
    apt-get -yqq install \
    openssh-client \
    rsync \
    dnsutils telnet netcat-openbsd iputils-ping \
    tcpdump strace net-tools \
    lsof tmux \
    jq vim less \
    psmisc traceroute \
    iftop dstat \
    sysstat fping \
    htop atop \
    socat iproute2 \
    curl wget \
    python3-pip \
    sshpass \
    git \
    locales

RUN locale-gen en_US.UTF-8
RUN localectl set-locale en_US.UTF-8
RUN dpkg-reconfigure locales

RUN mkdir -p /opt/ansible_collections/ydb_platform/ydb
WORKDIR /opt/ansible_collections/ydb_platform/ydb

COPY requirements.txt ./requirements.txt
RUN pip3 install -r ./requirements.txt

COPY requirements.yaml ./requirements.yaml
RUN ansible-galaxy install -r ./requirements.yaml

RUN mkdir -p ~/.ssh && \
    echo 'Host *' >> ~/.ssh/config && \
    echo '    StrictHostKeyChecking no' >> ~/.ssh/config

ENV PYTHONDONTWRITEBYTECODE 1
RUN echo 'export PYTHONDONTWRITEBYTECODE=1' > /etc/profile.d/10-python.sh

RUN git config --global --add safe.directory /opt
