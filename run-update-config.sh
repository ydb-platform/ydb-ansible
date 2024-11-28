#! /bin/sh

. ./run-active-options.sh
BACKUP_LABEL=`date '+%Y-%m-%d_%H-%M-%S'`
${RUN_ANSIBLE_PARALLEL} update-config.yaml --extra-vars "ydb_config_backup=${BACKUP_LABEL}"
