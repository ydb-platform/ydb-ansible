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
    git

RUN mkdir /opt/project
WORKDIR /opt/project

COPY requirements.txt /opt/project/requirements.txt
RUN pip3 install -r /opt/project/requirements.txt

COPY requirements.yaml /opt/project/requirements.yaml
RUN echo bla
RUN ansible-galaxy install -r /opt/project/requirements.yaml

COPY . /opt/project/
