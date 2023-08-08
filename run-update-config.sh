#! /bin/sh

BACKUP_LABEL=`date '+%Y-%m-%d_%H-%M-%S'`
ansible-playbook -b -i hosts -f 20 update-config.yaml --extra-vars "ydb_config_backup=${BACKUP_LABEL}"
