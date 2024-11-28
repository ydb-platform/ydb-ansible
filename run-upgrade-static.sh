#! /bin/sh

. ./run-active-options.sh
${RUN_ANSIBLE_PARALLEL} upgrade-static.yaml
