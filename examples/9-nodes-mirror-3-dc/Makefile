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
	--mount type=bind,src=${PWD},dst=/home/user/project \
	$(image) /bin/bash
.PHONY: run
