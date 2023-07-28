#! /bin/sh
# Set up the initial YDB admin password.

set +e
set +u

DB_ENDPOINT=grpcs://"$1":2135
DB_DOMAIN=/{{ ydb_domain }}
CAFILE={{ ydb_dir }}/certs/ca.crt
PASSFILE={{ ydb_dir }}/certs/secret

LD_LIBRARY_PATH={{ ydb_dir }}/lib
export LD_LIBRARY_PATH

PATH={{ ydb_dir }}/bin:$PATH
export PATH

set -e
set -u

. ${PASSFILE}
YDB_PASSWORD_JSON=`echo -n ${YDB_PASSWORD} | jq -R -s '.'`
ydb --ca-file ${CAFILE} -e ${DB_ENDPOINT} -d ${DB_DOMAIN} --user root --no-password \
  yql -s 'DECLARE $password AS Utf8; ALTER USER root PASSWORD '${YDB_PASSWORD_JSON}';'

# End Of File