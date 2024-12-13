#! /bin/sh

. ./run-active-options.sh

set +e
set +u

if [ -z "$1" ]; then
  ${RUN_ANSIBLE} rolling-dynamic.yaml
else
  ${RUN_ANSIBLE} rolling-dynamic.yaml --extra-vars "ydb_dbname=$1"
fi
