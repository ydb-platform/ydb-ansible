SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:

image = ydb-platform-creator-ee:latest

build:
	docker build -t $(image) .
.PHONY: build

run:
	docker run \
	-ti \
	--rm \
	--network host \
	--mount type=bind,src=${PWD},dst=/opt \
	--mount type=bind,src=/var/run/libvirt/libvirt-sock,dst=/var/run/libvirt/libvirt-sock \
	$(image) /bin/bash
.PHONY: run

test:
	python3 -m unittest discover -v tests/unit
.PHONY: test
