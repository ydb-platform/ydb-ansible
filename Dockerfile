# pull base image
FROM alpine:3.19

ARG ANSIBLE_CORE_VERSION
ARG ANSIBLE_VERSION
ARG ANSIBLE_LINT
ENV ANSIBLE_CORE_VERSION "2.17.4"
ENV ANSIBLE_VERSION "10.4.0"
ENV ANSIBLE_LINT "24.9.2"

# Labels.
LABEL maintainer="elabpro@yandex-team.ru" \
    org.label-schema.schema-version="1.0" \
    org.label-schema.build-date=$BUILD_DATE \
    org.label-schema.vcs-ref=$VCS_REF \
    org.label-schema.name="elabpro/ydb-ansible" \
    org.label-schema.description="Ansible inside Docker" \
    org.label-schema.url="https://github.com/elabpro/ydb-ansible" \
    org.label-schema.vcs-url="https://github.com/elabpro/ydb-ansible" \
    org.label-schema.vendor="YDB Platform" \
    org.label-schema.docker.cmd="docker run --rm -it -v $(pwd):/ansible ~/.ssh/id_rsa:/root/id_rsa ydb-ansible"

RUN apk --no-cache add \
        sudo \
        python3\
        py3-pip \
        openssl \
        ca-certificates \
        sshpass \
        openssh-client \
        rsync \
        git && \
    apk --no-cache add --virtual build-dependencies \
        python3-dev \
        libffi-dev \
        musl-dev \
        gcc \
        cargo \
        build-base && \
    rm -rf /usr/lib/python3.11/EXTERNALLY-MANAGED && \
    pip3 install --upgrade pip wheel && \
    pip3 install --upgrade cryptography cffi && \
    pip3 install ansible-core==${ANSIBLE_CORE_VERSION} && \
    pip3 install ansible==${ANSIBLE_VERSION} && \
    pip3 install --ignore-installed ansible-lint==${ANSIBLE_LINT} && \
    pip3 install mitogen jmespath && \
    apk del build-dependencies && \
    rm -rf /var/cache/apk/* && \
    rm -rf /root/.cache/pip && \
    rm -rf /root/.cargo

RUN mkdir /ansible && \
    mkdir -p /etc/ansible && \
    echo 'localhost' > /etc/ansible/hosts

WORKDIR /ansible
COPY entrypoint.sh /entrypoint.sh

RUN ansible-galaxy collection install git+https://github.com/ydb-platform/ydb-ansible.git

CMD [ "ansible-playbook", "--version" ]


