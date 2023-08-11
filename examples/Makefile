SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:

image = ydb-platform-example:latest

build:
	docker build -t $(image) .
.PHONY: build

run:
	docker run \
	-ti \
	--rm \
	--network host \
	--name ydb-appliance-ansible \
	--mount type=bind,src=${PWD}/project,dst=/opt/project \
	$(image) /bin/bash
.PHONY: run
