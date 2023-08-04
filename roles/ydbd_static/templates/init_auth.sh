#! /bin/sh
# Initialize or reconfigure YDB storage.

set +e
set +u

DB_ENDPOINT=grpcs://"$1":2135
DB_DOMAIN=/{{ ydb_domain }}
CAFILE={{ ydb_dir }}/certs/ca.crt
CONFIG={{ ydb_dir }}/cfg/ydbd-config-static.yaml
TOKEN={{ ydb_dir }}/home/ydbd-token-file
PASSFILE={{ ydb_dir }}/certs/secret

LD_LIBRARY_PATH={{ ydb_dir }}/lib
export LD_LIBRARY_PATH

PATH={{ ydb_dir }}/bin:$PATH
export PATH

set -e
set -u

if [ -f ${PASSFILE} ]; then
  # Username and password are passed in file for reconfiguration.
  . ${PASSFILE}
  ydb --ca-file ${CAFILE} -e ${DB_ENDPOINT} -d ${DB_DOMAIN} \
    auth get-token -f > ${TOKEN}
else
  # Initial cluster setup with empty password
  ydb --ca-file ${CAFILE} -e ${DB_ENDPOINT} -d ${DB_DOMAIN} \
    --user root --no-password auth get-token -f > ${TOKEN}
fi
trap "rm -f ${TOKEN}" EXIT

# End Of File