#! /bin/sh

. ./run-active-options.sh

set +e
set +u

if [ -z "$1" ]; then
  ${RUN_ANSIBLE} create-database.yaml
elif [ -z "$2" ]; then
  ${RUN_ANSIBLE} create-database.yaml --extra-vars "ydb_dbname=$1"
elif [ -z "$3" ]; then
  ${RUN_ANSIBLE} create-database.yaml --extra-vars "ydb_dbname=$1 ydb_default_groups=$2"
else
  ${RUN_ANSIBLE} create-database.yaml --extra-vars "ydb_dbname=$1 ydb_default_groups=$2 ydb_pool_kind=$3"
fi
