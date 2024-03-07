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

RUN useradd -m user

COPY requirements.txt /home/user/project/requirements.txt
RUN pip3 install -r /home/user/project/requirements.txt

COPY requirements.yaml /home/user/project/requirements.yaml
RUN ANSIBLE_COLLECTIONS_PATH=/usr/share/ansible/collections ansible-galaxy install -r /home/user/project/requirements.yaml

RUN mkdir -p /home/user/.ssh && \
    echo 'Host *' >> /home/user/.ssh/config && \
    echo '    StrictHostKeyChecking no' >> /home/user/.ssh/config && \
    echo '    UserKnownHostsFile /dev/null' >> /home/user/.ssh/config

COPY . /home/user/project/

RUN echo 'eval `ssh-agent`' >> /home/user/.bashrc

RUN echo 'ssh-add files/ssh_key' >> /home/user/.bashrc

RUN chown -R user:user /home/user

WORKDIR /home/user/project

USER user
